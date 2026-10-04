# SystemUI Application/runtime and Debug APK size audit plan

> **For agentic workers:** This is a documentation-only investigation plan. No implementation subtask may modify product code, build configuration, SDK state, AOSP state, emulator images, userdata, or devices.

**Goal:** Identify the first true root cause of the fresh SystemUI application fatal and the Debug APK size difference without using a rejected `try/catch` symptom fix.

**Architecture:** Compare four independently measured layers: AOSP intent, Gradle assembly, packaged APK/manifest/DEX bytes, and runtime PackageManager/class-loading behavior. Classify the first divergence before proposing solution families.

**Tech Stack:** AOSP `Android.bp`, Gradle/AGP, APK/DEX inspection, `apkanalyzer`/`aapt`, `javap`, `zipinfo`, SHA-256, ADB read-only commands, retained `/tmp/task050-*` evidence.

**Spec:** `docs/issues/2026-08-22-systemui-application-runtime-and-debug-size-audit.md`

## Global Constraints

- Documentation-only; no Gradle build, source/resource/manifest edit, dependency change, emulator/device mutation, or SDK/AOSP mutation.
- `try/catch NoSuchMethodError` is explicitly rejected and must not be proposed as a final recommendation.
- Cite exact present paths, command outputs, hashes, descriptors, or AOSP implementation lines.
- Read-only device inspection and `adb pull` into `/tmp/task051-*` are allowed; `adb` mutations, clears, reboots, and pushes are forbidden.
- The final document must separate measured facts, likely root cause, rejected explanations, and solution families.

---

### Task 1: Establish AOSP intent

**Files:**
- Read: `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/Android.bp`
- Read: `/home/conv/myspace/aosp/build/soong/java/app.go` and related Soong sources
- Create: final architecture document only

- [ ] Extract the exact `android_app "SystemUI"` stanza and its `static_libs`/`libs`/resource/manifest/platform/privilege properties.
- [ ] Extract `android_library "SystemUI-core"` scope and entry-class ownership.
- [ ] Trace Soong behavior for `platform_apis`, signing, system/privileged-app placement, hidden API packages/access, and usesNonSdkApi-related flags. Cite implementation/source lines.
- [ ] Record which behaviors are expected from the platform runtime versus APK bytes alone.

Acceptance: report section contains exact AOSP citations and a table mapping each behavior to APK/manifest, signing, system placement, package flag, or platform implementation.

### Task 2: Establish Gradle assembly facts

**Files:**
- Read: `settings.gradle.kts`, `app/build.gradle.kts`, `SystemUI-core/build.gradle.kts`, root `build.gradle.kts`
- Read: frozen Task 050 manifest and APK artifacts in the Worker worktree
- Read: retained Task 050 manifest-to-DEX evidence

- [ ] Prove or disprove `:app` → `:SystemUI-core` program-code contribution with current Gradle files and final DEX evidence.
- [ ] Prove whether `com.android.systemui.SystemUIApplication` exists in the final Debug DEX and where its constructor call to `Trace.registerWithPerfetto()` is emitted.
- [ ] Prove packaged manifest `<application>` and `android:appComponentFactory` names.
- [ ] Identify whether the original 91-entry static manifest closure test verified exact application/factory names, only component names, or a looser criterion.
- [ ] Explain why `:app` having no own source is not by itself evidence of missing code, using actual APK bytes and AOSP parity.

Acceptance: a single “assembly chain” table links AOSP source file → module artifact/dependency → DEX descriptor → manifest reference → PackageManager class name, each with evidence.

### Task 3: Establish runtime classification

**Files:**
- Read: `/tmp/task050-evidence/*postwipe*`, `/tmp/task050-evidence/logcat-postwipe-snapshot.txt`
- Read: current device read-only state if online
- Read: SysUISdk and runtime framework evidence

- [ ] Extract the complete first post-wipe fatal chain, including hidden-API lines preceding the NoSuchMethodError.
- [ ] Extract fresh PackageManager package/application metadata: class name if exposed, code path, package flags, target SDK, signing, shared user, usesNonSdkApi/hidden API enforcement indicators.
- [ ] Compare compile-time SysUISdk `android.os.Trace` with the runtime emulator framework. State whether the member is absent from runtime or present-but-blocked, and prove that classification.
- [ ] Distinguish application-class instantiation success from constructor failure.
- [ ] List every candidate first root cause and eliminate each one with evidence until one first divergence remains.

Acceptance: report says exactly which of “missing SystemUIApplication”, “runtime missing method”, “hidden-API denial”, “signature/domain mismatch”, and “stale PackageManager metadata” is proven or disproven.

### Task 4: Debug APK size audit

**Files:**
- Read: frozen Debug APK, main Release APK, original emulator SystemUI APK backup/on-device APK
- Create: temporary `/tmp/task051-*` data only

- [ ] For each APK, produce compressed and uncompressed totals by top-level ZIP directory and extension family, plus total DEX count/class count where feasible.
- [ ] Identify the largest 30 entries/groups in Debug and compare with original/Release.
- [ ] Explain the Debug/Release difference using actual entries, not assumptions.
- [ ] Explain whether 163 MB is a correctness blocker, expected debug artifact composition, duplicate packaging symptom, or something else.
- [ ] Cross-check APK installability and compression/alignment facts relevant to system-image placement.

Acceptance: report contains one reproducible size table and one ordered size-driver table with exact byte totals and SHA-256 values.

### Task 5: Solution families and decision matrix

**Files:**
- Create: `docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md`

- [ ] Present at least three coherent solution families that address the proven first root cause.
- [ ] Include at least: runtime/image/platform-source alignment, package signing/domain/hidden-API alignment, and build/platform revision alignment if supported by evidence. Add others only if evidence supports them.
- [ ] For each family list prerequisites, project-rule impact, expected first change, validation command/device evidence, risks, and what it does not solve.
- [ ] Explicitly mark source call-site `try/catch` as rejected and explain what it would obscure.
- [ ] Recommend an order of investigation/experiments, but do not claim product approval.

Acceptance: decision matrix is complete and contains no implementation change.
