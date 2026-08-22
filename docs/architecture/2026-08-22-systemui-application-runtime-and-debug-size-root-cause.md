# SystemUIApplication runtime root cause and Debug APK size audit (Task 051)

> Date: 2026-08-22 · Worker: Task 051 (docs-only, read-only)
> Spec: `docs/issues/2026-08-22-systemui-application-runtime-and-debug-size-audit.md`
> Plan: `docs/superpowers/plans/2026-08-22-systemui-application-runtime-and-debug-size-audit.md`
> Frozen artifact verified: Debug APK SHA-256
> `4d8240fdbbc144dfeb69b43dc3e5ad3911762afc90a8f83e07434d0669f78997`
> (re-verified at start of investigation and against the live on-device file; see §8).
>
> `Gradle: NOT RUN` — no Gradle task was invoked for this audit.
> `Mutations: NONE` — no source, resource, manifest, Gradle, SDK, AOSP, artifact,
> emulator, AVD, userdata, or device file was created or modified. Read-only ADB
> (`getprop`, `dumpsys`, `pm path`, `sha256sum`, `stat`) was used against the proven
> dedicated AVD `sysui-gradle-task049-debug-20260822-120226` (`ro.kernel.qemu=1`,
> API 37) after an identity gate. All scratch data lives under `/tmp/task051-*`.

---

## 1. Executive summary

1. The **complete assembly chain is faithful**: `SystemUIApplication.java` (AOSP line 87 =
   project line 87, byte-identical call `Trace.registerWithPerfetto()`) is compiled through
   `:SystemUI-core`, packaged into the frozen Debug APK (`classes7.dex`, descriptor
   `Lcom/android/systemui/SystemUIApplication;`, superclass `Landroid/app/Application;`,
   constructor bytecode `invoke-static {}, Landroid/os/Trace;.registerWithPerfetto:()V`),
   selected by the packaged manifest (`android:name="com.android.systemui.SystemUIApplication"`),
   loaded by PackageManager after the post-wipe fresh scan, and **entered at runtime** —
   the crash happens *inside* the constructor at line 87, which proves instantiation began.
2. The **first true divergence is not code packaging; it is the app-to-platform contract**.
   Soong's `platform_apis: true` adds `android:usesNonSdkApi="true"` to the packaged
   manifest via `manifest_fixer.py`, and `certificate: "platform"` means "the platform key
   of the target build". The Gradle build reproduces neither: the packaged manifest has no
   `usesNonSdkApi` attribute, and the APK is signed with the repo's AOSP platform testkey,
   which is not this Google image's platform key. Result: `isAllowedToUseHiddenApis()`
   fails on all three branches → `hiddenApiEnforcementPolicy=2 (ENABLED)` → the very first
   hidden-API call in the application constructor is denied → `NoSuchMethodError` crash loop.
3. The `Trace.registerWithPerfetto()` **member is present-but-blocked, not absent**:
   it exists in the runtime framework (`framework.jar!classes3.dex`) and in compile-time
   SysUISdk (`javap` shows `public static void registerWithPerfetto();`). The runtime log
   line is explicit: `api=blocked … domain=app … denied`.
4. The **163.6 MB Debug APK is expected debug composition, not a correctness blocker and
   not duplicate packaging**: 82% is uncompressed DEX from the un-minified 77,342-class
   closure (24 DEX files), plus a 25.3 MB unshrunk `resources.arsc`. Release (28.6 MB,
   15,683 classes) and the Soong-optimized original (49.8 MB, 38,372 classes) confirm the
   delta is R8 shrinking + resource shrinking + Soong optimization, all disabled in debug.
5. **All solution families below are NOT APPROVED** — they are presented for user
   discussion only. A source-level call-site `try/catch` is explicitly rejected (§7.5).

---

## 2. AOSP intent — what `android_app "SystemUI"` actually guarantees

`frameworks/base/packages/SystemUI/Android.bp` (lines 957–984):

```bp
android_app {
    name: "SystemUI",
    defaults: ["platform_app_defaults", "SystemUI_optimized_defaults", "wmshell_defaults"],
    static_libs: ["SystemUI-core"],
    resource_dirs: [],
    use_resource_processor: true,
    platform_apis: true,
    system_ext_specific: true,
    certificate: "platform",
    privileged: true,
    kotlincflags: ["-Xjvm-default=all"],
    dxflags: ["--multi-dex"],
    optimize: { proguard_flags_files: ["proguard.flags"] },
    required: ["privapp_whitelist_com.android.systemui"],
}
```

`android_library "SystemUI-core"` owns all Java/Kotlin sources including
`src/com/android/systemui/SystemUIApplication.java` (it is inside the `src/**/*.java` glob;
rule B/ADR 0003 keeps it in `:SystemUI-core`). The `android_app` has **no `srcs` of its
own** — all program code arrives through `static_libs: ["SystemUI-core"]`.

| AOSP property | Delivery mechanism (Soong/platform) | Expected runtime behavior | Where it must come from |
|---|---|---|---|
| `static_libs: ["SystemUI-core"]` | Soong merges library classes into the app DEX | All SystemUI classes present in APK DEX | APK bytes (Gradle: `:app` → `implementation(project(":SystemUI-core"))`) |
| `platform_apis: true` | `build/soong/java/app.go:661-665`: `usePlatformAPI := platform_apis` → `a.aapt.usesNonSdkApis`; `build/soong/scripts/manifest_fixer.py:188-205` (`add_uses_non_sdk_api`) injects `android:usesNonSdkApi="true"` into `<application>` at link time | `ApplicationInfo.usesNonSdkApi() == true` → hidden API allowed for this system app | Packaged manifest attribute (APK bytes) |
| `certificate: "platform"` | Signed at build time with **the platform key of the target build** (same key as framework) | `isSignedWithPlatformKey()` → hidden API allowed regardless of `usesNonSdkApi` | APK signature |
| `system_ext_specific: true` + `privileged: true` | Installed at `/system_ext/priv-app/` → `ScanPackageUtils.java:957-962` sets `SCAN_AS_SYSTEM_EXT`/`SCAN_AS_PRIVILEGED` | `SYSTEM`, `SYSTEM_EXT`, `PRIVILEGED` flags; privileged permissions from `privapp_whitelist` | Image placement (deployment), not APK bytes |
| `required: ["privapp_whitelist_com.android.systemui"]` | XML on `/system_ext/etc/sysconfig` or `/etc/permissions` | Grants signature\|privileged permissions | Image placement |
| Manifest `<application android:name=".SystemUIApplication" android:appComponentFactory=".PhoneSystemUIAppComponentFactory">` (`AndroidManifest.xml:398,411-412`) | Soong manifest fixer + aapt2 link; relative names resolve against the Soong package (`com.android.systemui`) | PM instantiates `com.android.systemui.SystemUIApplication` | Packaged manifest |
| `optimize` + `SystemUI_optimized_defaults` | R8/proguard optimization in non-eng builds | Optimized APK (~49.8 MB on the image) | Build type behavior |
| platform version injection | Soong stamps `versionCode`/`minSdk`/`targetSdk` from the platform (image shows 37/37/37) | Metadata parity with platform | Packaged manifest |

Runtime check chain (AOSP primary sources):

- `frameworks/base/core/java/android/content/pm/ApplicationInfo.java:2507-2534`:
  `isAllowedToUseHiddenApis()` = platform-signed **OR** (system/updated-system **AND**
  (`usesNonSdkApi()` **OR** hidden-API allowlisted)); `getHiddenApiEnforcementPolicy()`
  returns `DISABLED(0)` if allowed, else `ENABLED(2)` by default.
- `frameworks/base/services/core/java/com/android/server/pm/ScanPackageUtils.java:963-971`:
  `setSignedWithPlatformKey(...)` compares the package's signing details with the
  **platform package (`android`, i.e. framework-res)** signatures.
- `frameworks/base/services/core/java/com/android/server/am/ProcessList.java:2003-2016`:
  the policy is folded into zygote `runtimeFlags` for every process start → ART hidden-API
  domain enforcement.

---

## 3. Assembly chain — AOSP source → Gradle module → DEX → manifest → PM → constructor

| Step | Evidence (measured) |
|---|---|
| AOSP source | `frameworks/base/packages/SystemUI/src/com/android/systemui/SystemUIApplication.java:87` calls `Trace.registerWithPerfetto()` in the constructor |
| Project source (1:1) | `SystemUI-core/src/com/android/systemui/SystemUIApplication.java:87` — identical call, same line; no CONV modification involved |
| Gradle assembly | `app/build.gradle.kts`: `implementation(project(":SystemUI-core"))` is the only project dependency (mirrors `static_libs: ["SystemUI-core"]`); `:app` has **no source by design** (rule B/ADR 0003: the AOSP `android_app` has no `srcs`) |
| DEX packaging | Frozen Debug APK contains 24 DEX files, **77,342 class defs**; `classes7.dex` contains descriptor `Lcom/android/systemui/SystemUIApplication;` (dexdump: `source_file_idx: 11836 (SystemUIApplication.java)`, superclass `Landroid/app/Application;`) |
| Constructor bytecode | `classes7.dex` dexdump: `invoke-static {}, Landroid/os/Trace;.registerWithPerfetto:()V // method@02b1` guarded by the `isSubprocess()` check — emitted exactly as in source |
| Packaged manifest | `frozen-debug-manifest.xml:689` `android:name="com.android.systemui.SystemUIApplication"`; `:702` `android:appComponentFactory=".PhoneSystemUIAppComponentFactory"`; binary `packaged-manifest.txt:464` confirms the FQN |
| Manifest→DEX closure | Task 050 static closure gate: pre-fix `95 entry classes (present=16 missing=79)` — all missing were namespace-expanded `com.android.systemui.app.*` FQNs; post-fix `present=93 alias=2 missing=0 RESULT=PASS` (exact application/factory/entry FQNs, not a looser criterion) |
| PackageManager | Post-wipe fresh scan (lastUpdateTime 2026-08-22 18:37:13) selected the packaged application name; process `com.android.systemui` started as persistent shared-user `android.uid.systemui` (uid 10201) |
| Constructor entry | Crash stack: `at com.android.systemui.SystemUIApplication.<init>(SystemUIApplication.java:87)` — instantiation began and failed **inside** the constructor |

**Why an empty `:app/src` is not evidence of missing code**: the AOSP `android_app` itself
contributes no sources; every class arrives from `SystemUI-core`'s static closure, and the
77,342-class DEX plus the descriptor-level `SystemUIApplication` proof above close that
question with bytes, not inference.

---

## 4. Runtime classification — every candidate, proven or disproven

### 4.1 Timeline of the two distinct fatals

| Time (2026-08-22) | Event | Evidence |
|---|---|---|
| ~13:05–13:09 | Task 050 image surgery places frozen Debug APK at `/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk`; PM metadata still from the original scan | `first-fatal-full.txt` context; Task 050 log |
| 18:33:04 | **Fatal #1**: `ClassNotFoundException: com.android.systemui.application.impl.SystemUIApplicationImpl` | `first-fatal-full.txt` (38 lines) |
| ~18:37:13 | `wipe-data` → fresh PackageManager scan of our APK: `versionCode=0 minSdk=35 targetSdk=35`, `hiddenApiEnforcementPolicy=2`, `usesNonSdkApi=false`, `lastUpdateTime=18:37:13` | `dumpsys-package-afterwipe.txt:291-312` |
| 18:37:57+ | **Fatal #2 (persistent loop)**: hidden-API denial then `NoSuchMethodError: registerWithPerfetto` at `SystemUIApplication.java:87`; **1,578 occurrences** in the retained post-wipe log | `logcat-postwipe-full.txt` (grep counts: 1578/1578) |
| 2026-08-22 (today) | On-device APK still byte-identical to the frozen Debug APK; package state unchanged | live `adb shell sha256sum` → `4d8240fd…`; `dumpsys` re-run in this audit |

Fatal #1's `SystemUIApplicationImpl` comes from the **original Google image's own manifest**
(aapt2 xmltree of `original-SystemUIGoogle.apk`:
`android:name="com.android.systemui.application.impl.SystemUIApplicationImpl"`), a Google
Android 17 refactor that does not exist in our AOSP checkout (checkout has
`SystemUIApplication`). The image had our APK, but stale PM metadata still named the
original's application class, which is absent from our DEX → CNF.

### 4.2 Candidate-by-candidate verdict

| Candidate | Verdict | Direct evidence |
|---|---|---|
| Missing `SystemUIApplication` class | **DISPROVEN** | Descriptor present in `classes7.dex` (dexdump); manifest FQN correct; post-fix closure PASS; constructor was entered (stack shows `<init>` line 87) |
| Stale PackageManager metadata | **PROVEN for fatal #1 only**; cleared by the wipe | 18:33 CNF names the *original image's* application class (`SystemUIApplicationImpl`, proven from original APK manifest) while our DEX was installed; after wipe the class name switched to our real `SystemUIApplication` |
| Runtime member absence (`registerWithPerfetto` not in framework) | **DISPROVEN** | Runtime log itself states the declaration site: `declaration of 'android.os.Trace' appears in /system/framework/framework.jar!classes3.dex`; compile-time `javap` on SysUISdk `android.jar` shows `public static void registerWithPerfetto();`. `NoSuchMethodError` is the VM's *linking-time manifestation of denial*, not physical absence |
| **Hidden-API denial** | **PROVEN — the post-wipe root cause** | Log line: `hiddenapi: Accessing hidden method Landroid/os/Trace;->registerWithPerfetto()V (runtime_flags=0, domain=platform, api=blocked) from /system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk!classes7.dex (domain=app, TargetSdkVersion=35) using linking: denied`, immediately preceding each `NoSuchMethodError` (1,578 paired occurrences) |
| Signing/domain mismatch | **PROVEN as the enabling condition** | `dumpsys` post-wipe: `hiddenApiEnforcementPolicy=2`, `usesNonSdkApi=false`; by `ApplicationInfo.isAllowedToUseHiddenApis()` this is only reachable when not platform-signed, not usesNonSdkApi, and not allowlisted. apksigner ground truth: our APK cert SHA-256 `c8a2e9bc…` (AOSP platform testkey) vs original image cert `301aa3cb…` (Google platform key) — different keys |
| Source/runtime revision mismatch | **PROVEN as a separate, non-causal divergence** | Google image (fingerprint `emu64xa:17/CE2A.260420.019/15611780`) uses the `SystemUIApplicationImpl` refactor absent from our AOSP checkout; metadata divergence `versionCode=0/min=35/target=35` (ours) vs `37/37/37` (Soong-injected). Neither causes the current crash: the crash is the denied hidden-API call, and hidden-API enforcement applies to targetSdk ≥ 28 regardless of 35 vs 37 |

### 4.3 First-divergence / root-cause statement (direct evidence vs uncertainty)

**Direct evidence**: The Gradle build faithfully reproduces the app→core *code* chain
(§3) but does not reproduce two Soong `android_app` platform-contract properties:
`platform_apis: true` (→ missing `android:usesNonSdkApi="true"` in the packaged manifest)
and `certificate: "platform"` in its Soong meaning of "target build's platform key" (→
signed with the repo AOSP testkey, which this Google image does not recognize). On this
image the app is privileged/system_ext but fails `isAllowedToUseHiddenApis()` on every
branch, so hidden-API enforcement is ENABLED (policy=2), and the *first statement of the
application constructor* — `Trace.registerWithPerfetto()`, a `@hide` blocked-list,
domain=platform API called from domain=app — is denied at linking, producing the
`NoSuchMethodError` crash loop. The original image's SystemUI proves the contract works
when either Soong property is present: the original is *not* signed with this image's
platform key either (its dumpsys signature hashCode `b4addb29` differs from the platform
package `android`'s `d5d02e`), yet it runs with `policy=0` because Soong injected
`usesNonSdkApi=true`.

**Unresolved uncertainty (explicit)**: the post-wipe dumpsys `signatures:` line displays
the *same* hashCode (`b4addb29`) as the pre-wipe original despite apksigner proving the
APK bytes on disk are ours with a different certificate. This display-level anomaly could
not be resolved without parsing the APK Signing Block (V2/V3-only signatures are invisible
to `keytool`). It does not affect the classification: policy=2, `usesNonSdkApi=false`, and
the explicit denial log line are direct, independent evidence of the enforcement path.

---

## 5. Debug APK size audit (three APKs, reproducible)

Method: `python3` + `zipfile` over the three APKs; per-entry compressed/uncompressed
sizes, family aggregation, DEX header `class_defs` count; script and raw output retained
at `/tmp/task051-evidence/size-audit.txt`. `unzip -t` on the frozen Debug APK: "No errors
detected in compressed data" (installability/ZIP integrity).

### 5.1 Size table

| APK | File size (B) | SHA-256 | Entries | DEX files | DEX bytes (uncomp) | Class defs | resources.arsc | res/* (comp) | lib/* |
|---|---|---|---|---|---|---|---|---|---|
| Gradle Debug (frozen, Task 050) | 163,561,195 | `4d8240fdbbc144dfeb69b43dc3e5ad3911762afc90a8f83e07434d0669f78997` | 5,242 | 24 | 134,153,384 | 77,342 | 25,324,648 | 2,923,839 | 64,996 |
| Gradle Release (main) | 28,600,808 | `cd4b885e283361e3b29ada68c288ca120514e98c276b8925ad7e4606d23ba374` | 3,384 | 2 | 12,900,832 | 15,683 | 13,187,532 | 67,954 | 64,996 |
| Emulator original SystemUIGoogle | 49,841,504 | `a6340f94dc027dc396a891b2ddb78997a9470e863e1f35cbb9568e6edfb01304` | 3,724 | 3 | 25,965,832 | 38,372 | 15,497,824 | 2,173,053 | 4,275,808 |

### 5.2 Ordered size drivers (Debug vs everything else)

1. **Un-minified DEX: 134.15 MB = 82.1% of the Debug APK** (24 files, 77,342 classes).
   Debug disables R8 minify/shrink; the full closure (13 source modules + SettingsLib
   1,153 classes + WM-Shell 1,888 + Traceur 640 + SettingsLib per-target AARs +
   androidx/Compose/Dagger/kotlin-stdlib + aconfig classes) is retained with complete
   debug info. Release after R8: 12.9 MB / 15,683 classes. The Soong-optimized Google
   build: 25.97 MB / 38,372 classes. Ratio Debug:Release ≈ 10.4× in DEX bytes.
2. **DEX stored uncompressed** (`compress_size == file_size` for every DEX entry; same
   storage convention as the original APK). Largest entries: `classes.dex` 41.2 MB,
   `classes19.dex` 17.0 MB, `classes20.dex` 10.3 MB, `classes21.dex` 9.4 MB,
   `classes22.dex` 9.1 MB.
3. **Unshrunk `resources.arsc`: 25.3 MB** vs 13.2 MB in Release (Release actually ran
   `optimizeReleaseResources` + `convertShrunkResourcesToBinaryRelease`; Debug does not).
4. **No duplicate-packaging symptom**: entry names are unique; the family totals sum to
   the file size; the class count is consistent with the known full dependency closure;
   `unzip -t` passes. 163.6 MB is **expected debug artifact composition**, not a
   correctness blocker. It was only ever a *deployment* obstacle for the small
   remount-overlay scratch (Task 049 ENOSPC), which Task 050's direct image surgery
   already solved.

### 5.3 Debug vs Release vs original interpretation

| Difference | Explanation (from actual entries) |
|---|---|
| Debug 163.6 MB vs Release 28.6 MB | R8 code shrinking (77,342→15,683 classes) + resource shrinking (25.3→13.2 MB arsc; 5,027→248 res entries) |
| Debug 163.6 MB vs original 49.8 MB | Soong's `SystemUI_optimized_defaults` optimizes the shipped build (38,372 classes, 3 DEX); Google build also carries 4.3 MB native libs (`libtensorflowlite_jni.so` 2.7 MB etc.) our build lacks |
| Original smaller arsc+res than ours | Google's optimized resource shrinking vs our debug's full unshrunk resource table |

---

## 6. Solution families (all NOT APPROVED — for user discussion only)

### Family A — Reproduce the Soong `platform_apis` manifest contract (hidden API alignment)

**Content**: inject `android:usesNonSdkApi="true"` on `<application>` at **build time**
(e.g. AGP manifest merger attribute / overlay), exactly mirroring what
`build/soong/scripts/manifest_fixer.py:add_uses_non_sdk_api` does for
`platform_apis: true` — the AOSP source manifest stays untouched, like Soong's own
link-time injection.
**Prerequisites**: user authorization (manifest-level change is red-line adjacent);
verify aapt2 link accepts the attribute in our pipeline.
**Expected first change**: packaged debug/release manifest gains the attribute.
**Validation gate**: rebuild Debug → `aapt2 dump xmltree` shows `usesNonSdkApi=true` →
push to the dedicated AVD → `dumpsys package com.android.systemui` shows
`usesNonSdkApi=true`, `hiddenApiEnforcementPolicy=0` → reboot → no `hiddenapi … denied`
line → `SystemUIApplication` constructs past line 87.
**Evidence it works on this image**: the original SystemUIGoogle is *not* signed with the
image's platform key (different signature hashCode from the `android` platform package)
yet runs with policy=0 purely via Soong's injected `usesNonSdkApi=true`.
**Risks**: none to AOSP source (build-time injection); must not be used to mask other
divergences.
**Does not solve**: versionCode/targetSdk metadata parity; platform-signature domain;
Debug APK size.
**Status: NOT APPROVED.**

### Family B — Platform signing/domain alignment (same-tree AOSP image)

**Content**: run the APK on an emulator image **built from our own AOSP tree** (the same
tree whose `out/` produced framework.jar/SysUISdk), where the repo platform testkey *is*
the platform key; `isSignedWithPlatformKey()` then holds and policy=0 regardless of the
manifest attribute.
**Prerequisites**: building an AOSP emulator system image (heavy; hours/days of build);
the disposable-AVD authority model of Task 050 extends naturally.
**Expected first change**: no product change; a deployment/environment change.
**Validation gate**: on the self-built image, `dumpsys` shows policy=0 without
`usesNonSdkApi`; SystemUI boots and passes the Task 050 UI-stability gates.
**Risks**: infrastructure cost; image availability; also removes the
`SystemUIApplicationImpl` revision divergence by construction (same tree).
**Does not solve**: Debug APK size; behavior on Google-built images (our testkey is
not Google's key there — on such images Family A is the only lever).
**Status: NOT APPROVED.**

### Family C — Build/platform revision metadata parity

**Content**: reproduce Soong's platform version stamping — `versionCode=37`,
`minSdk=37`, `targetSdk=37` — and record the Google-image `SystemUIApplicationImpl`
refactor as a known upstream divergence of our AOSP checkout revision.
**Prerequisites**: user authorization for `defaultConfig` changes (rule B adjacency).
**Expected first change**: `app/build.gradle.kts` defaultConfig parity.
**Validation gate**: packaged manifest shows 37/37/37; `dumpsys` post-deploy matches the
original's metadata fields.
**Risks**: low; but **not causal** for the current crash (enforcement applies at
targetSdk ≥ 28; 35 vs 37 changes nothing) — this is hygiene, not a fix.
**Does not solve**: the hidden-API denial by itself; size.
**Status: NOT APPROVED.**

### Family D — Debug size composition (optimized debug variant)

**Content**: introduce a build-type/variant that applies the AOSP
`SystemUI_optimized_defaults` semantics to a deployable debug artifact (R8 minify +
resource shrinking), moving the deployable APK from 163.6 MB toward the original's
~49.8 MB class of size.
**Prerequisites**: user decision (affects debug-loop ergonomics: slower builds, obfuscated
stack traces — though `proguard.flags`/mapping retention applies); rule I judgment.
**Expected first change**: new variant config only; no AOSP source change.
**Validation gate**: `:app:assemble<Variant>` size table reproduced below 60 MB;
Task 050 static closure gate still PASS on the optimized artifact.
**Risks**: debuggability loss; does not address runtime at all.
**Does not solve**: the crash; only the deployment footprint.
**Status: NOT APPROVED.**

### 7.5 Rejected: source-level call-site `try/catch`

Wrapping `Trace.registerWithPerfetto()` in `try/catch (NoSuchMethodError)` is **rejected**.
It would (1) treat the VM's denial signal as the defect instead of the platform-contract
divergence proven in §4; (2) leave every other hidden-API call site in SystemUI (thousands
of @hide references across the codebase) equally broken — the crash would simply move to
the next denied call; (3) obscure the missing Soong semantics (`platform_apis`,
`certificate`) that this audit was requested to prove or disprove. It is symptom
suppression, not a root-cause fix.

### Recommended order of investigation (no approval implied)

1. Family A (smallest, directly evidenced by the original's policy=0 on this image);
2. Family C metadata parity in the same discussion;
3. Family B and Family D as separate user decisions (infra cost vs debug ergonomics).

---

## 8. Verification commands and outputs (this audit)

- `sha256sum /home/conv/myspace/SystemUI-Gradle-wt-050/app/build/outputs/apk/debug/app-debug.apk`
  → `4d8240fdbbc144dfeb69b43dc3e5ad3911762afc90a8f83e07434d0669f78997` (matches frozen value; gate PASS)
- Live identity gate: `adb shell getprop ro.kernel.qemu` → `1`; AVD name →
  `sysui-gradle-task049-debug-20260822-120226`; `pm path com.android.systemui` →
  `/system_ext/priv-app/SystemUIGoogle/SystemUIGoogle.apk`;
  `adb shell sha256sum <path>` → `4d8240fd…` (on-device bytes still ours)
- Evidence greps (counts): post-wipe full log contains 1,578 `SystemUIApplication`
  instantiate failures and 1,578 matching hidden-API denial lines; 0 occurrences of the
  `SystemUIApplicationImpl` CNF in the post-wipe log (it belongs to the pre-wipe snapshot).
- `apksigner verify --print-certs` (three APKs): digests recorded in §4.2/§5.1.
- Size audit: `/tmp/task051-evidence/size-audit.txt` (script inline, output retained).
- `unzip -t` frozen Debug APK → "No errors detected in compressed data".

`Gradle: NOT RUN`. `Mutations: NONE`.
