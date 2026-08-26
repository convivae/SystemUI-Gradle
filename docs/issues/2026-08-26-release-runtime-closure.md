# 2026-08-26 — Release runtime closure on emulator-5554 (Task 060)

## Verdict

**RELEASE_RUNTIME_FAIL — runtime phase.** Build blocker resolved (chief-approved Option A);
deployed Release APK **crash-loops at startup** with a novel, fully-classified R8 failure:

> **Root cause: R8 obfuscation divergence.** AGP `isMinifyEnabled = true` runs R8 full mode
> **with obfuscation**; AOSP's Soong build runs SystemUI R8 with **`-dontobfuscate`**
> (`build/soong/java/dex.go:545-548` — `obfuscate` defaults to false and
> `SystemUI_optimized_defaults` does not enable it). With obfuscation on,
> `DumpManager.registerDumpable(getClass().getSimpleName(), this)` — called from
> `NavigationModeController`, `OverviewProxyService`, `SysuiColorExtractor`, `QSImpl`,
> `ScreenLifecycle`, `WakefulnessLifecycle`, `LeakDetector`, `HotspotControllerImpl`, etc. —
> returns the **obfuscated** simple name. 39 distinct classes in the APK are obfuscated to
> simple name `a` (different packages), including several dumpable registrants, so the
> second registrant hits `IllegalArgumentException("'a' is already registered")` and
> SystemUI crash-loops from boot.

Device restored to the known-good Debug baseline `e8aad131…` (verified, stable, healthy).

Per the chief's dispatch directive ("any different failure class → stop and report"), the
fix for this second failure was **NOT applied** — it is a build-config change (obfuscation
policy), not the approved aconfig-annotation family.

## Recommended next action (NOT executed — needs chief/user decision)

Align Release R8 with AOSP semantics by disabling obfuscation while keeping
shrink+optimize+resource-shrink. Concretely, add ONE line to `app/proguard_gradle.flags`
(same Gradle-native adapter file as the aconfig suppressions):

```proguard
-dontobfuscate
```

Rationale: AOSP SystemUI's optimized build is precisely shrink+optimize+shrink_resources
with `-dontobfuscate` (Soong `SystemUI_optimized_defaults` + dex.go default). Keeping names
also preserves `getClass().getSimpleName()`-keyed dump registration, proto-log class names,
and stack-trace readability, and removes an entire class of reflection/name-keyed hazards
(Debug was unaffected because debug does not minify). Cost: APK stays larger (~32.1 MB →
slightly larger). The mapping.txt/mapping.prt artifacts then become shrink/optimize-only.

Alternative (not recommended): keep obfuscation and add `-keepnames` for every
dumpable-registrant + name-keyed surface — diverges from AOSP and is fragile.

## Phase 1 (pre-approval): build blocker — RESOLVED

### Step 1 — Preflight (all green)

| Check | Command | Result |
|---|---|---|
| Single device | `adb devices -l` | only `emulator-5554` (emu64x) |
| Emulator | `getprop ro.kernel.qemu` | `1` |
| Verity/overlay | `getprop ro.boot.veritymode`; `su 0 mount` | overlay mounts on /system and /system_ext **active** (the post-disable-verity deployment mechanism; verity must stay disabled) |
| Device APK | `su 0 sha256sum …/SystemUI.apk` | `e8aad131e85bab59922b6d28ca6cb2fdbf4ddd531b64a38a7ef168503546e427` == Debug baseline |
| Rollback: debug APK | `sha256sum app/build/outputs/apk/debug/app-debug.apk` | `e8aad131…46e427` ✓ (163,896,493 B) |
| Rollback: stock backup | `sha256sum …/stock-backup/SystemUI.apk` | `dd1ff45acdf82700897a4adc587f67ff3f4f626d6ef240c6d75f1544f194b837` ✓ |
| Solo Gradle | `ps aux \| grep gradle` | Android Studio daemon idle, no active build |

### Build blocker: R8 missing class (fixed via approved Option A)

First `:app:assembleRelease` attempts failed in two stages:

1. **Two Gradle daemon OOM kills** (kernel OOM killer; host 30 GiB RAM, swap 8/8 GiB full,
   idle Kotlin compile daemon holding 8.3 GiB RSS; `journalctl -k` evidence in git history
   of this report). Brief-prescribed `--max-workers=4` retry also OOM'd. Mitigation: stopped
   idle Kotlin/AS daemons → 19 GiB free.
2. Real failure: `R8: Missing class com.android.aconfig.annotations.AssumeFalseForR8
   (referenced from: boolean com.android.window.flags.FeatureFlags.appCompatRefactoring()
   and 5 other contexts)` — CLASS-retained, build/optimizer-only aconfig annotation present
   only on the compile classpath (SysUISdk android.jar), referenced via
   `RuntimeInvisibleAnnotations` by `com.android.window.flags.FeatureFlags` in
   `libs/systemui-aconfig-flags.jar` (entered runtime closure via window-flags wiring
   `df1ea62f` + 14-jar merge `e69b9bc7`, 2026-08-24/25 — after task 045's green Release of
   2026-08-21; Release never re-run in between). Exact sibling of Task 043/044
   `AssumeTrueForR8` (user-approved option A, `app/proguard_gradle.flags`).

**Chief decision (user-approved 2026-08-25): Option A** — authorized editing
`app/proguard_gradle.flags`, adding exactly `-dontwarn
com.android.aconfig.annotations.AssumeFalseForR8` (exact FQN, no wildcards, no keeps),
header comment updated minimally (same-family instance, task 055 window-flags jar origin,
CLASS retention, never runtime-resolved).

After the edit (and re-freeing a respawned 10.6 GiB Kotlin daemon):

```
./gradlew :app:assembleRelease --console=plain --max-workers=4
BUILD SUCCESSFUL in 2m 8s  (380 actionable tasks: 13 executed, 367 up-to-date)
```

No new missing classes of the aconfig family (or any other) appeared — batch authority
unused.

## Phase 2 (post-fix): static sanity, deploy, runtime gate

### Step 3 — Static sanity (all green)

Release APK: 32,100,023 B (≈30.6 MiB), sha256
`50d4df86e171eba346621b8015cf80a09709602a1a92bb35c7bdcb7b555bd193`.

| Check | Release | Debug | Match |
|---|---|---|---|
| `unzip -t` | CLEAN | — | ✓ |
| apksigner verify | `Verifies`, v2 scheme **true** (v1/v3 false), 1 signer | v2 same | ✓ |
| Cert SHA-256 | `c8a2e9bccf597c2fb6dc66bee293fc13f2fc47ec77bc6b2b0d52c11f51192ab8` (CN=Android platform test cert) | identical | ✓ |
| package | `com.android.systemui` | same | ✓ |
| targetSdk | 35 | 35 | ✓ |
| `sharedUserId` | `android.uid.systemui` | same | ✓ |
| `appComponentFactory` | `.PhoneSystemUIAppComponentFactory` | same | ✓ |

### Step 4 — Deploy (proven procedure, executed exactly)

```
adb push → /data/local/tmp/SystemUI-rel.apk          (sha256 match, 32,100,023 B)
su 0 mount -o remount,rw /system_ext                 (task-058 documented step)
su 0 cp …/SystemUI.apk.new && sync                   (staged copy sha256 match — no ENOSPC)
su 0 mv …/SystemUI.apk.new → SystemUI.apk            (atomic same-dir replace)
chown root:root; chmod 0644; chcon u:object_r:system_file:s0
rm -rf oat/; rm dalvik-cache *systemui*; sync
on-device sha256 = 50d4df86… == build hash          (verified BEFORE restart) ✓
reboot → sys.boot_completed=1 in ~40 s
post-boot on-device sha256 = 50d4df86… (survived reboot) ✓
```

### Step 5 — Runtime health gate: **FAIL**

- SystemUI process **crash-looping**: `pidof com.android.systemui` returned a new PID at
  every 30 s sample (7421 → 10059 → 12169 → … → 27055 over 10 samples; initial post-boot
  PID 6363 also churned).
- `logcat -b crash -d`: **1290 FATAL EXCEPTION** lines, all the same signature:

```
java.lang.RuntimeException: Unable to create service com.android.systemui.SystemUIService
  (and KeyguardService)
Caused by: java.lang.IllegalArgumentException: 'a' is already registered
  at he4.g(...)                    → com.android.systemui.dump.DumpManager.registerDumpable
  at he4.h(...)                    → DumpManager (overload)
  at com.android.systemui.navigationbar.a.<init>(...:63)
                                   → NavigationModeController.<init> (AOSP line 114:
                                     dumpManager.registerDumpable(getClass().getSimpleName(), this))
  … Dagger provider chain …
  at com.android.systemui.SystemUIService.onCreate(...)
```

- `dumpsys window windows`: **no StatusBar / NotificationShade window** (SystemUI never
  reached UI). Bonus QS-panel step not applicable.

### Step 6 — Failure protocol: root-cause classification

Classification (brief taxonomy): **not** missing keep, **not** reflection entry, **not**
resource shrink, **not** aconfig — it is an **R8 obfuscation semantic divergence** between
AGP and AOSP Soong:

1. Soong (`build/soong/java/dex.go:545-548`): `if !Bool(opt.Obfuscate) { r8Flags =
   append(r8Flags, "-dontobfuscate") }` — obfuscation is opt-in; SystemUI's
   `SystemUI_optimized_defaults` (Android.bp:935-950) sets `optimize/shrink/shrink_resources
   = true` but **not** `obfuscate` → AOSP's shipped SystemUI R8 is shrink+optimize only,
   **names preserved**.
2. AGP `isMinifyEnabled = true` (our release block, per approved Task 030 R1+R2 alignment)
   enables R8 with obfuscation by default → 39 classes renamed to simple name `a`
   (mapping.txt: `grep -cE "\.a:$"` = 39), including dumpable registrants
   `NavigationModeController`, `OverviewProxyService`, `CommandQueue`, etc.
3. `DumpManager.registerDumpable` keys dumpables by the passed name;
   `canAssignToNameLocked` throws on duplicates (DumpManager.kt:95-101). With obfuscated
   simple names colliding ("a" vs "a"), the second registrant aborts SystemUIService
   creation → persistent crash loop (both SystemUIService and KeyguardService entry paths
   hit the same Dagger subgraph).

Debug is unaffected because the debug build type does not minify — this is exactly the
Release-only risk surface task 060 exists to catch.

### Device restoration (executed, verified)

Standard procedure with `app-debug.apk`: force-stop → push (sha match) → remount rw →
staged cp (sha match, no ENOSPC) → atomic mv → root:root 0644 u:object_r:system_file:s0 →
oat/dalvik-cache cleared → on-device sha256 = `e8aad131…` before restart → reboot.

Post-restore verification: `sys.boot_completed=1` (~15 s); on-device sha256 `e8aad131…`;
PID 829 stable across 3×30 s; crash buffer 0 FATAL; `Taskbar` + `NotificationShade`
windows present; 44 SystemUI service references alive. Device back at known-good baseline.

## Timeline

| Time (2026-08-25/26) | Event |
|---|---|
| 23:57 | Preflight green; first build attempt OOM-killed |
| 00:02 | `--max-workers=4` retry OOM-killed; journalctl confirms kernel OOM |
| 00:05 | Idle 8.3 GiB Kotlin daemon stopped; attempt 3 exposes `AssumeFalseForR8` missing ref |
| 00:25 | Phase-1 report committed (`27f254e5`); halt for approval |
| 00:15+ | Chief approval received; flags edited; 10.6 GiB respawned Kotlin daemon stopped |
| 00:16 | `BUILD SUCCESSFUL in 2m 8s` |
| 00:17–00:19 | Static sanity green; Release deployed, on-device sha verified pre-restart |
| 00:20 | Reboot; SystemUI crash-loops (1290 FATAL, `'a' is already registered`) |
| 00:21–00:26 | 10×30 s PID sampling documents instability; crash stack deobfuscated via mapping.txt |
| 00:26–00:30 | Debug APK restored; device verified healthy at e8aad131 |
| 00:35 | Report updated; commit (local only) |

## Open questions for chief/user

1. Approve `-dontobfuscate` in `app/proguard_gradle.flags` (AOSP-alignment fix, one line)?
   If approved, re-run assembleRelease → redeploy → re-gate; expected to clear this crash
   class entirely (all name-keyed registrations become safe again).
2. Environment (recurring): heavy Release builds on this host require stopping idle
   Kotlin/AS daemons first (three daemon OOM kills across this task's builds).

---

## Round 3 (Task 060b) — second crash captured and fully classified: R8 horizontal class merging

**Worker**: task060b (forensics-only; no Gradle, no builds, no source edits).
**APK under test**: `app-release.apk` sha256 `90c412d8c86fafc42ea1233474d2da9f2e3823ca0806b1ead822bb4e1c0f64fa`
(the `-dontobfuscate` build from Round 2's approved fix).

### Preflight (all green)

| Check | Result |
|---|---|
| `adb devices` | only `emulator-5554` |
| On-device sha | `e8aad131…` (Debug baseline, PID 833 healthy) ✓ expected |
| Release APK sha | `90c412d8…` ✓ matches brief |
| Host memory | 30 GiB total, 18 GiB available (swap 7.7/8.0 GiB used — noted, bounded logcat capture only) |

### Deployment

Proven staged procedure: push → remount,rw → staged `cp` → **sha gate `90c412d8…` MATCH** →
atomic mv → root:root 0644 `u:object_r:system_file:s0` → oat/dalvik-cache cleared → reboot →
`sys.boot_completed=1`.

### Loop evidence

- Crash buffer after boot+75 s: **195 FATAL EXCEPTION instances** (00:53:58 → 00:56:03+,
  new PID every ~0.65 s; PID churn re-confirmed by `pidof` sampling: empty → 17891 → 21216).
- **Signature dedup: all 195 instances are ONE crash signature** — no alternating distinct
  crashes. Two *entry services* surface it (`SystemUIService` first instance PID 826 @00:53:58;
  `KeyguardService` for later instances, PID 7037+), but both onCreate paths funnel into the
  same `startServicesIfNeeded` registration loop — same root cause.

### Full first FATAL instance (verbatim, PID 826, 00:53:58.465)

```text
FATAL EXCEPTION: main
Process: com.android.systemui, PID: 826
java.lang.RuntimeException: Unable to create service com.android.systemui.SystemUIService: java.lang.IllegalArgumentException: 'com.android.systemui.CoreStartable$Nop' is already registered
	at android.app.ActivityThread.handleCreateService(ActivityThread.java:5170)
	at android.app.ActivityThread.-$$Nest$mhandleCreateService(Unknown Source:0)
	at android.app.ActivityThread$H.handleMessage(ActivityThread.java:2569)
	at android.os.Handler.dispatchMessage(Handler.java:110)
	at android.os.Looper.loopOnce(Looper.java:239)
	at android.os.Looper.loop(Looper.java:328)
	at android.app.ActivityThread.main(ActivityThread.java:8956)
	at java.lang.reflect.Method.invoke(Native Method)
	at com.android.internal.os.RuntimeInit$MethodAndArgsCaller.run(RuntimeInit.java:593)
	at com.android.internal.os.ZygoteInit.main(ZygoteInit.java:932)
Caused by: java.lang.IllegalArgumentException: 'com.android.systemui.CoreStartable$Nop' is already registered
	at com.android.systemui.dump.DumpManager.registerDumpable(r8-map-id-f2ccef4bf99c013e76a0286e41e7ecd3b8df7af1dbc6f6b21573a8e2a9660ef5:52)
	at com.android.systemui.dump.DumpManager.registerCriticalDumpable(r8-map-id-f2ccef4bf99c013e76a0286e41e7ecd3b8df7af1dbc6f6b21573a8e2a9660ef5:3)
	at com.android.systemui.SystemUIApplication.startServicesIfNeeded(r8-map-id-f2ccef4bf99c013e76a0286e41e7ecd3b8df7af1dbc6f6b21573a8e2a9660ef5:409)
	at com.android.systemui.SystemUIApplication.startSystemUserServicesIfNeeded(r8-map-id-f2ccef4bf99c013e76a0286e41e7ecd3b8df7af1dbc6f6b21573a8e2a9660ef5:65)
	at com.android.systemui.SystemUIService.onCreate(r8-map-id-f2ccef4bf99c013e76a0286e41e7ecd3b8df7af1dbc6f6b21573a8e2a9660ef5:10)
	at android.app.ActivityThread.handleCreateService(ActivityThread.java:5157)
	... 9 more
```

(Original `/tmp/r3_crash_buffer.txt` capture — 4096 lines, 195 FATALs — was lost when the host
rebooted at ~08:47; the above was captured before the reboot and is preserved verbatim here.
The 195-instance/one-signature count was verified pre-reboot via
`grep -c "FATAL EXCEPTION"` and message-level `sort | uniq` over the full buffer.)

### Name-reality check: -dontobfuscate IS working

All class names in the stack are **real** (`com.android.systemui.dump.DumpManager`,
`SystemUIApplication.startServicesIfNeeded`, …) — no single-letter names. The
`r8-map-id-…` source-file suffixes are R8's normal mapping-id retention for unobfuscated
builds. Round 2's obfuscation collision ("'a' is already registered") is fully cleared.

### Root cause: R8 **horizontal class merging** (the second, distinct R8 divergence)

Not obfuscation (fixed), not a missing shrink-keep (all classes present), not init-order.
It is R8 full-mode **optimization merging structurally-identical classes**, which breaks
DumpManager's name-keyed registration:

1. **Registration key is the runtime class name.**
   `DumpManager.kt:47-48` — `registerCriticalDumpable(module)` →
   `registerCriticalDumpable(module::class.java.name, module)`;
   `DumpManager.kt:109-110` same for the normal variant.
2. **Duplicate name allowed only for the same instance.**
   `DumpManager.kt:162-166` — `canAssignToNameLocked` returns true only if
   `existingDumpable == null || newDumpable == existingDumpable`; otherwise
   `DumpManager.kt:101` throws `IllegalArgumentException("'$name' is already registered")`.
3. **Three identity-distinct instances exist at runtime, all CoreStartables:**
   - `CoreStartable.NOP` — a shared singleton (`CoreStartable.java:75`), returned by ~20
     feature-flag-off `@Provides`/`@Binds` methods (`StatusBarPhoneModule.kt:92,97,150,164,178,218`,
     `DisplayModule.kt:87,101`, `StatusBarModule.kt:97,131`, etc.);
   - `NoOpCoreStartable()` — a fresh instance (`NoOpCoreStartable.kt:21`,
     provided at `NotificationStatsLoggerModule.kt:145`);
   - `FeatureFlagsReleaseStartable` — a fresh instance with constructor side effects
     (`FeatureFlagsReleaseStartable.kt:29-38`, bound via its own `@IntoMap @ClassKey` module).
   All are iterated by `SystemUIApplication.startServicesIfNeeded`
   (`SystemUIApplication.java:371-381`; `isDumpCritical()` defaults true, `CoreStartable.java:64-66`)
   and each is passed to `registerCriticalDumpable(service)`.
4. **R8 merged the latter two classes INTO `CoreStartable$Nop`.** mapping.txt
   (`app/build/outputs/mapping/release/mapping.txt:499557-499565`) — the
   `com.android.systemui.CoreStartable$Nop -> com.android.systemui.CoreStartable$Nop:` entry
   contains synthesized members:
   ```text
   1:1:void start():79:79 -> start$com$android$systemui$CoreStartable$Nop
   1:1:void com.android.systemui.NoOpCoreStartable.start():21:21 -> start$com$android$systemui$NoOpCoreStartable
   1:1:void com.android.systemui.flags.FeatureFlagsReleaseStartable.start():40:40 -> start$com$android$systemui$flags$FeatureFlagsReleaseStartable
   ```
   and neither `NoOpCoreStartable` nor `FeatureFlagsReleaseStartable` has its own top-level
   mapping entry — they were merged away (their Dagger factories still exist and still
   construct instances, now of runtime class `CoreStartable$Nop`).
5. **Collision.** After the merge, the NOP singleton, the NoOpCoreStartable instance and the
   FeatureFlagsReleaseStartable instance are *distinct objects sharing one runtime class
   name*. The first `registerCriticalDumpable` stores key
   `com.android.systemui.CoreStartable$Nop`; the next distinct instance fails
   `canAssignToNameLocked` → `IllegalArgumentException` → service creation fails →
   process death → persistent ~0.65 s crash loop. (Note: the ~20 NOP-singleton returns alone
   would NOT crash — `canAssignToNameLocked` permits same-instance re-registration. The
   crash requires the merged distinct instances, which is why this never reproduces in
   Debug: debug does not minify, so no merging occurs.)

**Why AOSP doesn't hit this (hypothesis, not verified)**: AOSP's own
`proguard.flags`/`proguard_common.flags`/`proguard_kotlin.flags` contain **no** keep rules for
these classes either, yet AOSP-built SystemUI doesn't crash-loop. Most plausible explanations:
(a) AOSP's bundled R8 (`prebuilts/r8`) is a different version from AGP 9.3.1's R8 and its
horizontal-class-merging pass doesn't merge these (or bails on classes whose names are used
via `getClass().getName()` semantics differently); (b) the Soong R8 pipeline applies different
optimization flags. Verifying would require inspecting AOSP's prebuilts/r8 version vs ours —
left as the recommended next diagnostic for the chief.

### Classification (brief taxonomy)

**Optimization (class-merging) breaking identity-sensitive, name-keyed registration —
a keep-rule gap in our Gradle proguard config, distinct from Round 2's obfuscation divergence.**
Round 2 = R8 renaming collision; Round 3 = R8 merging collision. Both are
"AGP R8 ≠ Soong R8 semantics" family, but the fixes differ.

### Recommended fix (NOT applied — outside worker authority)

Add targeted keeps to `app/proguard_gradle.flags` (same file as the approved
`-dontobfuscate`/`-dontwarn` entries):

```proguard
# R8 horizontal class merging collapses identity-distinct CoreStartables into one
# runtime class; DumpManager registers dumpables by class name and rejects distinct
# instances sharing a name. Keep these classes un-merged (task 060b round-3 crash).
-keep class com.android.systemui.CoreStartable$Nop { *; }
-keep class com.android.systemui.NoOpCoreStartable { *; }
-keep class com.android.systemui.flags.FeatureFlagsReleaseStartable { *; }
```

Note `-keepnames` is NOT sufficient — renaming is already off; only `-keep` prevents merging.
A broader `-keep class * implements com.android.systemui.CoreStartable { *; }` would close the
whole collision class (any two merged CoreStartable implementations would collide the same
way) at higher APK-size cost. Recommended next diagnostic before/after the fix: grep the new
mapping.txt for CoreStartable implementations lacking their own top-level entry, to confirm
no other merge targets lurk (1822 `R8$$REMOVED$$CLASS` entries exist; only these three are
implicated by the stack).

### Device restoration: BLOCKED (host reboot incident)

The host rebooted at ~08:47 (uptime 2h16m at 11:03), killing the emulator process and wiping
`/tmp` AFTER all crash evidence above was captured. `adb devices` shows no device; the
emulator relaunch procedure (acloud/emulator launcher, per task 053/054 infrastructure) is
outside this forensics brief's authority → **escalated to chief**. The Debug baseline APK
(`e8aad131…`) restore procedure is ready to execute as soon as the device is back; note the
emulator was killed while the round-3 Release APK was still deployed, so whichever relaunch
path is used must be followed by the standard Debug restore (push → sha gate → atomic mv →
perms → cache clear → reboot → verify) before any other device work.

### Verdict

Task 060b acceptance: **PASS** (full round-3 crash stack captured verbatim with cause chain;
single-signature loop documented; name-reality check done; root cause classified with
file:line + mapping.txt evidence). Release verdict remains **RELEASE_RUNTIME_FAIL** —
round 3 is a new, distinct failure (class merging), fix pending chief/user approval.
