# 2026-08-26 — Release runtime closure on emulator-5554 (Task 060)

## Verdict

**RELEASE_RUNTIME_FAIL — blocked at BUILD step (runtime gate never reached).**

Root cause (fully classified, evidence below):

> **R8 missing class `com.android.aconfig.annotations.AssumeFalseForR8`** — a CLASS-retained,
> build/optimizer-only aconfig annotation referenced (as `RuntimeInvisibleAnnotations` on 6
> flag methods) by `com.android.window.flags.FeatureFlags` inside `libs/systemui-aconfig-flags.jar`.
> The annotation exists only on the **compile** classpath (SysUISdk `android.jar`), not in any
> runtime JAR/AAR, so R8 full mode (which resolves only the runtime classpath) aborts.

This is the **exact sibling of the Task 043/044 `AssumeTrueForR8` case** (user-approved
option A, 2026-08-21, `app/proguard_gradle.flags`), surfacing now because the referencing
classes entered the APK runtime closure **after** task 045's green Release build:

- Task 045 green: `:app:assembleRelease` exit 0, R8 missing refs 0 — 2026-08-21
- `df1ea62f` (2026-08-24, task 054 follow-up): `libs/window-flags.jar` wired into
  `:SystemUI-core` — first introduction of `com.android.window.flags.FeatureFlags`
  (byte-identical Soong `window-aconfig-java.jar`) into the runtime closure
- `e69b9bc7` (2026-08-25, task 057): 14 flags JARs merged into `libs/systemui-aconfig-flags.jar`
- Tasks 054–058 were **Debug-runtime-driven**; Release/R8 was never re-run in that window
  (the window-flags closure doc `2026-08-24-window-flags-runtime-closure.md` only analyzed
  the no-R8 debug case). Task 060 is the first Release build since, and it exposes the new ref.

Per the brief's authority ("working tree read-only; build outputs / report / one log line
only") and the Task 044 precedent (the identical one-line suppression required **explicit
user approval**), **no fix was applied**. Device was never touched and remains on the known
good Debug APK.

## Recommended next action (NOT executed — needs chief/user approval)

Add exactly one line to `app/proguard_gradle.flags` (Task 044 option-A pattern, same file,
same boundaries — no wildcards, no keep/assume rules, no annotation class injection):

```proguard
-dontwarn com.android.aconfig.annotations.AssumeFalseForR8
```

Then re-run `:app:assembleRelease` and resume the task 060 gate (deploy → PID stability →
FATAL scan → StatusBar). If approved, expected remaining runtime risk profile is unchanged
(the suppression only ignores an unresolved annotation *descriptor*; annotations have no
runtime behavior, classified in Task 043).

## Step 1 — Preflight (all green)

| Check | Command | Result |
|---|---|---|
| Single device | `adb devices -l` | only `emulator-5554` (emu64x) |
| Emulator | `getprop ro.kernel.qemu` | `1` |
| Verity/overlay | `getprop ro.boot.veritymode`; `su 0 mount` | `enforcing` (irrelevant — the post-disable-verity **overlay mounts on /system and /system_ext are active**, which is the mechanism that permits APK deployment; verity must stay disabled) |
| Device APK | `su 0 sha256sum /system_ext/priv-app/SystemUI/SystemUI.apk` | `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427` == Debug baseline |
| Rollback: debug APK | `sha256sum app/build/outputs/apk/debug/app-debug.apk` | `e8aad131…46e427` ✓ (163,896,493 B) |
| Rollback: stock backup | `sha256sum …/task053…/stock-backup/SystemUI.apk` | `dd1ff45acdf82700897a4adc587f67ff3f4f626d6ef240c6d75f1544f194b837` ✓ |
| Solo Gradle | `ps aux | grep gradle` | Android Studio daemon idle (0.0% CPU), no active build |

## Step 2 — Build attempts

### Attempt 1 — `./gradlew :app:assembleRelease --console=plain`

```
FAILURE: Gradle build daemon disappeared unexpectedly
(it may have been killed or may have crashed)
```

### Attempt 2 (brief-prescribed retry) — `--max-workers=4`

Same failure: daemon disappeared.

Kernel evidence (`journalctl -k`):

```
Aug 25 23:59:32 kernel: Out of memory: Killed process 3989710 (feishu) …
Aug 25 23:59:39 kernel: Out of memory: Killed process 3990432 (java)  anon-rss:5518792kB …
Aug 26 00:02:34 kernel: Out of memory: Killed process 4005569 (java)  anon-rss:9890140kB …
```

Host state at the time: 30 GiB RAM, **swap 8/8 GiB full**, idle Kotlin compile daemon
holding **8.3 GiB RSS**. Mitigation (within authority — process management, not tree
mutation): stopped the idle Kotlin daemon (`kill 3961538`; Gradle respawns it on demand)
→ 19 GiB available. Kotlin daemon + emulator together starve R8 full mode on this host;
**future heavy Release builds on this machine should stop idle Kotlin/AS daemons first.**

### Attempt 3 — after freeing memory, `--max-workers=4`

Daemon survived; real failure surfaced:

```
ERROR: Missing classes detected while running R8. Please add the missing classes or apply
additional keep rules that are generated in …/mapping/release/missing_rules.txt.
ERROR: R8: Missing class com.android.aconfig.annotations.AssumeFalseForR8
       (referenced from: boolean com.android.window.flags.FeatureFlags.appCompatRefactoring()
        and 5 other contexts)
Caused by: com.android.tools.r8.internal.j: Missing class
   com.android.aconfig.annotations.AssumeFalseForR8 …
Execution failed for task ':app:minifyReleaseWithR8'
BUILD FAILED in 1m 54s
```

AGP-generated `missing_rules.txt`:

```
-dontwarn com.android.aconfig.annotations.AssumeFalseForR8
```

No Release APK produced (`app/build/outputs/apk/release/` absent). Steps 3–5 (static
sanity, deploy, runtime gate) not reached.

## Root-cause evidence chain

1. **Referencing class lives in the runtime closure**: `unzip -l libs/systemui-aconfig-flags.jar`
   contains `com/android/window/flags/FeatureFlags.class` (28 flags classes total in the jar).
2. **Bytecode-level annotation reference** (`javap -v` on the extracted class):

   ```
   #17 = Utf8  Lcom/android/aconfig/annotations/AssumeFalseForR8;
   …
   RuntimeInvisibleAnnotations:
     0: #17()   com.android.aconfig.annotations.AssumeFalseForR8
     1: #8()    com.android.aconfig.annotations.AconfigFlagAccessor
     2: #9()    android.compat.annotation.UnsupportedAppUsage
   ```

   R8 reports 6 contexts = the 6 flag methods carrying this annotation in that one class.
3. **Annotation class is compile-classpath-only**: present in SysUISdk `android.jar` /
   `core-for-system-modules.jar`; **absent from every jar/AAR in `libs/` and `libs/maven/`**
   (full scan). R8 resolves only runtime inputs → missing class.
4. **Why task 045 was green**: the window flags classes (`df1ea62f`, 2026-08-24) and the
   14-jar merge (`e69b9bc7`, 2026-08-25) postdate task 045's 2026-08-21 verification; no
   Release build ran in between.
5. **Precedent classification**: Task 043 reclassified `AssumeTrueForR8` (same annotation
   family, same generator, then referenced from `com.android.wifi.flags.FeatureFlags`) as a
   build/optimizer-only CLASS-retained signature with no APK runtime behavior; Task 044
   (user-approved option A) closed it with a single exact-FQN `-dontwarn` in
   `app/proguard_gradle.flags`. `AssumeFalseForR8` is the false-valued sibling generated by
   the same aconfig pipeline.

Classification answer to the brief's taxonomy: **aconfig assumption** (not missing keep, not
reflection entry, not resource shrink).

## Device end-state (restoration check)

Never deployed; no restoration needed. Final verification:

```
e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427  /system_ext/priv-app/SystemUI/SystemUI.apk
```

Device remains at the known-good Debug baseline, overlay intact, verity disabled.

## Timeline

| Time (2026-08-25/26) | Event |
|---|---|
| 23:57 | Preflight started; all checks green |
| 23:59 | Build attempt 1: daemon OOM-killed |
| 00:02 | Attempt 2 (`--max-workers=4`): daemon OOM-killed again |
| 00:05 | journalctl confirms kernel OOM kills; idle Kotlin daemon (8.3 GiB) stopped |
| 00:07 | Attempt 3: daemon survives, R8 missing-class failure surfaces |
| 00:10–00:20 | Evidence chain collected (javap, jar scans, git archaeology) |
| 00:25 | Report written; device re-verified at e8aad131; halt for approval |

## Open questions for chief/user

1. Approve the one-line `AssumeFalseForR8` dontwarn (Task 044 pattern)? If yes, task 060
   (or a follow-up task) can resume at step 2 and complete the runtime gate.
2. Environment note: heavy Release builds require ~10+ GiB free; idle Kotlin/AS daemons
   should be stopped first (two daemon losses this session, feishu also OOM-killed).
