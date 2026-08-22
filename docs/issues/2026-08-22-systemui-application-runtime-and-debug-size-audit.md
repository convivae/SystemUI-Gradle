# SystemUI Application/runtime and Debug APK size root-cause audit

## Background

Task 050 produced a Debug APK and deployed it byte-identically to the dedicated API 37 emulator. After a clean userdata scan, Android attempted to instantiate `com.android.systemui.SystemUIApplication`, then failed inside its constructor at `Trace.registerWithPerfetto()`.

The user rejected a call-site `try/catch` because it treats the observed exception rather than proving whether the Gradle APK preserves AOSP's complete `android_app SystemUI` packaging, platform privilege, hidden-API, and `SystemUI-core` semantics. The user also questioned why the Debug APK is about 163.6 MB while the emulator SystemUI is about 49.8 MB and the current Release APK is about 28.6 MB.

## Questions to answer

1. Is `SystemUIApplication.java` present, compiled through `:SystemUI-core`, packaged into the Debug APK, selected by the packaged manifest, loaded by PackageManager, and entered at runtime?
2. Does Gradle's source/dependency topology faithfully reproduce AOSP `android_app "SystemUI"` → `SystemUI-core`, despite `:app` containing no Java/Kotlin source?
3. Is the current fatal caused by an absent application class, an absent runtime method, hidden-API enforcement, signing/domain differences, package flags, a platform/source revision mismatch, or a combination? Which layer first diverges from AOSP?
4. Which AOSP `Android.bp` app properties are behaviorally required at runtime, and which are currently represented or missing in Gradle/manifest/signing/image deployment?
5. What exact ZIP entry families account for the Debug APK's size, and how do Debug, Release, and the original emulator SystemUI APK differ?
6. What are at least three coherent solution families, their prerequisites, risks, and verification gates? A source-level `try/catch` is explicitly rejected and must not be recommended.

## Investigation policy

- Primary sources only: current project files/artifacts, AOSP source/Soong implementation, APK bytes, and retained/read-only device evidence.
- No source, resource, manifest, Gradle, SDK, artifact, emulator, userdata, or device mutation.
- No Gradle build.
- Read-only ADB (`getprop`, `dumpsys`, `pm path`, `stat`, `sha256sum`, `logcat -d`, and `adb pull` into `/tmp/task051-*`) is permitted if the dedicated emulator remains online.
- Findings belong in `docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md`.

## Required evidence

- AOSP `Android.bp` app/core dependency and relevant platform/privilege/hidden-API/signing properties.
- Gradle project dependency and APK packaging evidence.
- Packaged manifest application and component-factory names.
- DEX descriptors and, where needed, bytecode/call-site evidence for `SystemUIApplication`.
- Fresh PackageManager metadata and complete first fatal chain.
- Compile-time versus runtime `android.os.Trace` availability/access evidence, distinguishing missing member from hidden-API denial.
- Reproducible compressed/uncompressed ZIP size table for all three APKs, plus largest entry groups and DEX/class counts.

## Status

Research Worker dispatch approved directly by the user on 2026-08-22. No implementation is approved.

**Result (2026-08-22, Task 051 worker)**: investigation complete, report at
`docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md`.

Evidence summary:

- Assembly chain proven faithful end-to-end: `SystemUIApplication.java:87` (identical in AOSP and
  project) → compiled through `:SystemUI-core` → packaged in the frozen Debug APK
  (`classes7.dex` descriptor `Lcom/android/systemui/SystemUIApplication;`, constructor bytecode
  `invoke-static Landroid/os/Trace;.registerWithPerfetto:()V`) → packaged manifest FQN correct →
  post-wipe PackageManager scan selected it → constructor entered and failed at line 87.
- Post-wipe root cause **proven**: hidden-API denial. The Gradle build reproduces neither Soong
  `platform_apis: true` (→ `android:usesNonSdkApi="true"` injected by `manifest_fixer.py`) nor
  `certificate: "platform"` in the "target build's platform key" sense; on the Google image
  `isAllowedToUseHiddenApis()` fails all branches → `hiddenApiEnforcementPolicy=2` → first
  constructor call (`Trace.registerWithPerfetto`, @hide, domain=platform, api=blocked) denied →
  `NoSuchMethodError` crash loop (1,578 paired occurrences in retained logs). The runtime member
  is present-but-blocked (exists in runtime `framework.jar` and SysUISdk), not absent.
- The earlier `SystemUIApplicationImpl` CNF (18:33) was stale-PackageManager-metadata only: the
  original Google image's manifest declares that refactored class name; cleared by wipe-data.
- Debug APK 163,561,195 B = expected debug composition: 82.1% uncompressed un-minified DEX
  (24 files, 77,342 class defs vs Release 15,683 / original 38,372) + 25.3 MB unshrunk
  `resources.arsc`. No duplicate packaging; ZIP integrity verified. Not a correctness blocker.
- Four solution families documented (manifest hidden-API contract / platform signing domain /
  revision metadata parity / optimized debug variant), all explicitly NOT APPROVED; call-site
  `try/catch` explicitly rejected.
- `Gradle: NOT RUN`, `Mutations: NONE`. One flagged uncertainty: post-wipe dumpsys `signatures:`
  hashCode display anomaly vs apksigner cert ground truth (does not affect the classification).

Open decision for the user: choose among the NOT APPROVED solution families (recommended order:
Family A manifest contract first).
