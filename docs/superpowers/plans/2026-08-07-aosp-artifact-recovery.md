# AOSP Artifact Recovery and APK Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:systematic-debugging for each transform/build failure and superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Prerequisite:** 完成 `docs/superpowers/plans/2026-08-07-post-topology-correctness.md` 并把其 commit 合入当前工作分支；本计划从该计划记录的新 core first-failure 开始。

**Goal:** 用原始、R-clean 的直接 AAR 逐个恢复 WifiTrackerLib、iconloader、SettingsLib、WindowManager-Shell，消除源码/prebuilt 重复类，随后验证 manifest merge，并把构建推进到真实 `:app:assembleDebug` 证据或需要用户裁决的明确 blocker。

**Architecture:** 四个库都属于 SystemUI 外部且含资源的 AOSP 产物，因此先用 `libs/aars/*.aar` + Gradle file dependency 直接消费。AAR 的 `classes.jar` 只取对应 Soong `javac/*.jar`，资源从 BP 声明的原始 AOSP `res` 复制，manifest/R.txt 从对应 Soong target 取得；禁止合入 `busybox/R.jar`、禁止使用 fat `turbine-combined` 代替主代码、禁止修改资源。如果直接 AAR 被证实因依赖解析冲突而不可用，才另写 issue 并切换到本地 Maven AAR。

**Tech Stack:** Python 3 `zipfile`/`unittest`、AOSP Soong intermediates、Gradle/AGP 9.2、AAPT2、SysUISdk、Android APK Analyzer (`unzip`/`apkanalyzer` when available)。

## Non-Negotiable Constraints

- 不创建 Java/Kotlin stub，不恢复 `PluginProtectorStub.kt`。
- 不修改、删除、合并、去重或重写 AOSP 原始资源。
- 不运行当前 `tools/gen_aar_maven.py`；其中 R.jar 合并和 resource rewrite 是已确认失败实验。
- `classes.jar` 中不得有任何 `*/R.class` 或 `*/R$*.class`。
- Maven 只是交付方式；只有直接 AAR 的冲突已由日志证明后才允许切换。
- 不使用 `flatDir`。
- 不使用 `turbine-combined` fat JAR 直接进入 APK；它只可用于依赖调查。
- WindowManager-Shell artifact 中不得再包含任何 `com/android/systemui/**` 类。
- 每次只切换一个 artifact；每次切换后单独运行 transform/compile 证据。
- 遇到 `PluginProtector` 时停止并询问用户；本计划不决定 KAPT/KSP/bridge。
- 任何缺类先回查对应 `Android.bp` 的 `static_libs`/`libs`；按官方 Maven、AOSP JAR、AOSP AAR分类恢复，禁止源码复制。

## Canonical Artifact Inputs

| Artifact | Code JAR | Resource root | Manifest | R.txt |
|---|---|---|---|---|
| WifiTrackerLib | `out/soong/.intermediates/frameworks/opt/net/wifi/libs/WifiTrackerLib/WifiTrackerLib/android_common/javac/WifiTrackerLib.jar` | `frameworks/opt/net/wifi/libs/WifiTrackerLib/res` | `.../WifiTrackerLib/android_common/manifest_fixer/AndroidManifest.xml` | `.../WifiTrackerLibRes/android_common/R.txt` |
| iconloader | `out/soong/.intermediates/frameworks/libs/systemui/iconloaderlib/iconloader/android_common/javac/iconloader.jar` | `frameworks/libs/systemui/iconloaderlib/res` | `.../iconloader/android_common/manifest_fixer/AndroidManifest.xml` | `.../iconloader/android_common/R.txt` |
| SettingsLib | `out/soong/.intermediates/frameworks/base/packages/SettingsLib/SettingsLib/android_common/javac/SettingsLib.jar` | `frameworks/base/packages/SettingsLib/res` | `.../SettingsLib/android_common/manifest_fixer/AndroidManifest.xml` | `.../SettingsLib/android_common/R.txt` |
| WindowManager-Shell | `out/soong/.intermediates/frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/javac/WindowManager-Shell.jar` | `frameworks/base/libs/WindowManager/Shell/res` | `.../WindowManager-Shell/android_common/manifest_fixer/AndroidManifest.xml` | `.../WindowManager-Shell/android_common/R.txt` |

所有相对 AOSP 路径以 `/home/conv/myspace/aosp/` 为根。WifiTrackerLib 主 target 的 `resource_dirs: []`，其资源 owner 是 `WifiTrackerLibRes`，所以只对 R.txt/resource root 使用 Res target；代码和 manifest 仍取主 target。

---

### Task 1: Record the Post-Correctness Baseline and Artifact Inventory

**Files:**
- Create: `docs/issues/2026-08-07-aosp-artifact-recovery.md`
- Modify: this plan's checkboxes/results

- [ ] **Step 1: Create the issue before artifact changes**

issue 必须包含：背景、四个 artifact 当前交付位置、当前 core first-failure、执行步骤、错误数演变、待解决问题。

- [ ] **Step 2: Capture current dependency consumers**

Run:

```bash
rg -n 'WindowManager-Shell\.jar|systemui\.(settingslib|iconloader|wmshell|wifitrackerlib)' \
  --glob '*.kts' . | tee /tmp/aosp-artifact-consumers.before.txt
./gradlew :SystemUI-core:dependencies \
  --configuration debugCompileClasspath --console=plain \
  > /tmp/core-debugCompileClasspath.before.txt
```

- [ ] **Step 3: Audit current AARs for embedded R and SystemUI classes**

Run a read-only Python ZIP scan over every `libs/maven/com/android/systemui/*/*/*.aar` and record for each:

- number of `.class` entries;
- number and names of R classes;
- number and package prefixes of `com/android/systemui/**` classes.

Expected current evidence:

- SettingsLib: R classes present;
- iconloader: R classes present;
- WindowManager-Shell: R classes and 179 `com/android/systemui/**` classes present;
- WifiTrackerLib: no R class in current classes.jar.

- [ ] **Step 4: Commit evidence only**

```bash
git add docs/issues/2026-08-07-aosp-artifact-recovery.md \
  docs/superpowers/plans/2026-08-07-aosp-artifact-recovery.md
git commit -m "docs: establish AOSP artifact recovery baseline"
```

---

### Task 2: Extend the Strict Direct-AAR Packager

**Files:**
- Modify: `tools/package_aosp_aar.py`
- Modify: `tools/tests/test_package_aosp_aar.py`
- Generate: `libs/aars/WifiTrackerLib.aar`
- Generate: `libs/aars/iconloader.aar`
- Generate: `libs/aars/SettingsLib.aar`
- Generate: `libs/aars/WindowManager-Shell.aar`
- Modify: `docs/issues/2026-08-07-aosp-artifact-recovery.md`

**Interfaces:**
- Consumes: canonical inputs table above.
- Produces: four byte-deterministic direct AARs with code, raw resources, manifest, R.txt, and no R classes.

- [ ] **Step 1: Add config/provenance tests before implementation**

Add one test case per artifact asserting its configured code JAR/resource/manifest/R.txt paths match the canonical table. Add tests asserting:

- absent input fails with `FileNotFoundError`;
- every code JAR containing R fails before output is replaced;
- duplicate resource relative paths fail instead of merging/overwriting;
- repeated packaging bytes are identical;
- WindowManager-Shell output contains no `com/android/systemui/**` class.

Run focused tests and confirm the four-config tests fail because only animationlib is currently supported.

- [ ] **Step 2: Add declarative configs without general resource discovery**

Extend the CLI choices to:

```text
animationlib
WifiTrackerLib
iconloader
SettingsLib
WindowManager-Shell
```

Each config must list exact code JAR, exact resource root(s), exact manifest, exact R.txt, and output path. Do not use recursive `find_res_dirs()` because it can accidentally include tests or static dependency resources.

- [ ] **Step 3: Preserve raw resource bytes and reject collisions**

For each listed root, copy files to `res/<relative-path>` in sorted order. If two roots produce the same AAR entry, raise `DuplicateEntryError`. Do not parse XML and do not remove version-qualified resources.

- [ ] **Step 4: Enforce code ownership**

The packager must reject all R classes for every artifact. For WindowManager-Shell it must also reject any class under `com/android/systemui/`; the selected `javac/WindowManager-Shell.jar` should naturally satisfy this. Do not filter a fat JAR after the fact—select the clean javac output.

- [ ] **Step 5: Generate and inspect all four AARs**

Run:

```bash
for lib in WifiTrackerLib iconloader SettingsLib WindowManager-Shell; do
  python3 tools/package_aosp_aar.py "$lib" --output "libs/aars/$lib.aar"
  unzip -t "libs/aars/$lib.aar"
done
python3 -m unittest tools.tests.test_package_aosp_aar -v
```

Run a ZIP assertion that fails if any nested classes.jar contains R; additionally fail if WM Shell contains `com/android/systemui/`.

- [ ] **Step 6: Prove deterministic output**

Generate all four twice with a 2-second delay and compare `sha256sum` files. Expected: no diff.

- [ ] **Step 7: Commit packager and direct AARs**

```bash
git add tools/package_aosp_aar.py tools/tests/test_package_aosp_aar.py \
  libs/aars/WifiTrackerLib.aar libs/aars/iconloader.aar \
  libs/aars/SettingsLib.aar libs/aars/WindowManager-Shell.aar \
  docs/issues/2026-08-07-aosp-artifact-recovery.md
git commit -m "build: package strict AOSP direct AARs"
```

---

### Task 3: Switch WifiTrackerLib to the Direct AAR

**Files:**
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `docs/issues/2026-08-07-aosp-artifact-recovery.md`

- [ ] **Step 1: Replace only WifiTrackerLib coordinate**

Replace:

```kotlin
implementation(libs.systemui.wifitrackerlib)
```

with:

```kotlin
implementation(files("${rootProject.projectDir}/libs/aars/WifiTrackerLib.aar"))
```

Do not change the other three artifacts.

- [ ] **Step 2: Run resource transform and core compile**

```bash
./gradlew :SystemUI-core:processDebugResources --rerun-tasks --console=plain \
  2>&1 | tee /tmp/wifitracker-direct-aar-resources.log
./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/wifitracker-direct-aar-compile.log
```

Success criterion: no WifiTrackerLib duplicate R transform/class error. A later unrelated failure is acceptable and must be recorded.

- [ ] **Step 3: Handle only evidence-backed missing dependencies**

If compile reports a missing WifiTrackerLib static dependency, locate it in `WifiTrackerLib/Android.bp` and classify:

- AndroidX lifecycle/core/annotation → official Maven dependency;
- Wifi flags → AOSP generated JAR;
- SettingsLibHelpUtils → SettingsLib recovery task, not copied source.

Do not use turbine-combined as the fix.

- [ ] **Step 4: Commit**

```bash
git add SystemUI-core/build.gradle.kts \
  docs/issues/2026-08-07-aosp-artifact-recovery.md
git commit -m "build: consume WifiTrackerLib direct AAR"
```

---

### Task 4: Switch iconloader to the Direct AAR

**Files:**
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `docs/issues/2026-08-07-aosp-artifact-recovery.md`

- [ ] Replace only `implementation(libs.systemui.iconloader)` with `implementation(files("${rootProject.projectDir}/libs/aars/iconloader.aar"))`.
- [ ] Run `:SystemUI-core:processDebugResources` and `:SystemUI-core:compileDebugKotlin` separately with `--rerun-tasks` and tee logs.
- [ ] Confirm no `com/android/launcher3/icons/R*` duplicate-class error.
- [ ] If launcher flags are missing, recover the existing AOSP generated flags JAR or its already-declared official/AOSP dependency; do not put launcher source in a SystemUI module.
- [ ] Record result and commit as `build: consume iconloader direct AAR`.

---

### Task 5: Switch SettingsLib to the Direct AAR and Remove Main-Class Duplication

**Files:**
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `SystemUI-res/build.gradle.kts`
- Possibly modify: SettingsLib-specific JAR declarations proven redundant by class audit
- Modify: `docs/issues/2026-08-07-aosp-artifact-recovery.md`

- [ ] **Step 1: Switch both consumers atomically**

Replace core and res usages of `libs.systemui.settingslib` with the same direct file AAR path:

```kotlin
files("${rootProject.projectDir}/libs/aars/SettingsLib.aar")
```

Use `implementation(...)` in core and `api(...)` in res, preserving current visibility semantics.

- [ ] **Step 2: Audit SettingsLib supplemental JAR overlap**

Compare classes in `SettingsLib.aar!/classes.jar` with:

- `libs/SettingsLib-full.jar`;
- `libs/SettingsLib-javac.jar`.

If either supplemental JAR contains any class already in the AAR, it cannot remain wholesale on compile classpath. Record counts and exact package prefixes.

- [ ] **Step 3: Remove redundant main-code supplements**

Remove `SettingsLib-javac.jar` when its main classes are provided by direct AAR. Do not delete a supplemental static-dependency JAR unless the audit proves all required classes have another owner. If `SettingsLib-full.jar` is a fat combined artifact, stop and create a focused extraction subtask that keeps only AOSP SettingsLib child-module classes and rejects AndroidX/third-party/main SettingsLib duplicates.

The extraction must be a deterministic Python tool with tests; manual `zip -d` is not acceptable.

- [ ] **Step 4: Verify resources and compile**

```bash
./gradlew :SystemUI-res:processDebugResources --rerun-tasks --console=plain \
  2>&1 | tee /tmp/settingslib-direct-aar-resources.log
./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/settingslib-direct-aar-compile.log
```

Success criterion: no `com/android/settingslib/R*` duplicate transform. Missing SettingsLib child classes must be traced to named BP static libs, not solved by resource edits.

- [ ] **Step 5: Commit SettingsLib recovery**

Use commit message `build: consume SettingsLib direct AAR` and include any tested deterministic child-module JAR tool/artifact created by Step 3.

---

### Task 6: Switch WindowManager-Shell and Eliminate Fat Prebuilt Duplicates

**Files:**
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `SystemUI-animation/build.gradle.kts`
- Modify: `SystemUI-shared/build.gradle.kts`
- Modify: `app/build.gradle.kts`
- Delete only after no consumers: `libs/WindowManager-Shell.jar`
- Modify: `docs/issues/2026-08-07-aosp-artifact-recovery.md`

- [ ] **Step 1: Confirm clean direct AAR ownership**

Assert:

- no R class in `WindowManager-Shell.aar!/classes.jar`;
- no `com/android/systemui/**` class;
- WM Shell public classes used by project sources are present.

- [ ] **Step 2: Replace core runtime artifact**

Replace `implementation(libs.systemui.wmshell)` with direct AAR. Remove core's separate `compileOnly(libs/WindowManager-Shell.jar)` only in the same change so there is one WM Shell code owner.

- [ ] **Step 3: Replace compile-only consumers**

For `:SystemUI-animation` and `:SystemUI-shared`, replace the fat JAR compileOnly dependency with compileOnly on the clean direct AAR. Remove the app dependency because app has no source and must only directly depend on core.

- [ ] **Step 4: Prove no Gradle consumer remains and delete the fat JAR**

```bash
if rg -n 'libs/WindowManager-Shell\.jar' --glob '*.kts' .; then
  echo 'fat WMShell JAR still consumed' >&2
  exit 1
fi
git rm libs/WindowManager-Shell.jar
```

- [ ] **Step 5: Run module and core verification**

```bash
./gradlew \
  :SystemUI-animation:compileDebugKotlin \
  :SystemUI-shared:compileDebugKotlin \
  --rerun-tasks --console=plain \
  2>&1 | tee /tmp/wmshell-direct-aar-upstreams.log
./gradlew :SystemUI-core:processDebugResources --rerun-tasks --console=plain \
  2>&1 | tee /tmp/wmshell-direct-aar-resources.log
./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/wmshell-direct-aar-core.log
```

Success criterion: no WM Shell R duplicate and no duplicate `com.android.systemui.animation` class. If javac JAR lacks a named WM Shell static library class, recover that named dependency according to BP; never return to the fat JAR.

- [ ] **Step 6: Commit**

```bash
git add SystemUI-core/build.gradle.kts SystemUI-animation/build.gradle.kts \
  SystemUI-shared/build.gradle.kts app/build.gradle.kts \
  docs/issues/2026-08-07-aosp-artifact-recovery.md
git commit -m "build: replace fat WM Shell prebuilt with direct AAR"
```

---

### Task 7: Remove Obsolete Local-Maven Coordinates Only After Verification

**Files:**
- Modify: `gradle/libs.versions.toml`
- Modify: `docs/issues/2026-08-07-aosp-artifact-recovery.md`
- Delete when unreferenced: four obsolete `libs/maven/com/android/systemui/...` AAR/POM directories

- [ ] Search the entire repository for the four catalog aliases and Maven coordinates.
- [ ] Remove only aliases with zero Gradle consumers.
- [ ] Confirm no POM transitive dependency is still relied upon by comparing before/after `debugCompileClasspath`; restore explicit official/AOSP dependencies rather than retaining an accidental POM edge.
- [ ] Delete the four obsolete local-Maven artifact directories after direct AAR verification; do not delete unrelated flags or SystemUISharedLib entries in this Task.
- [ ] Run `./gradlew projects`, `:SystemUI-res:processDebugResources`, and core compile.
- [ ] Commit as `chore: remove obsolete local AOSP AAR coordinates`.

---

### Task 8: Validate Manifest Merge Semantics

**Files:**
- Modify only if evidence requires: `app/build.gradle.kts` or manifest source-set wiring
- Do not modify AOSP manifest content to suppress merge errors
- Modify: `docs/issues/2026-08-07-aosp-artifact-recovery.md`

- [ ] Run:

```bash
./gradlew :app:processDebugMainManifest --rerun-tasks --console=plain \
  2>&1 | tee /tmp/systemui-manifest-merge.log
```

- [ ] Locate the actual merged manifest under `app/build/intermediates/merged_manifest*/debug/**/AndroidManifest.xml`.
- [ ] Compare semantic properties with AOSP `frameworks/base/packages/SystemUI/AndroidManifest.xml`: application name, sharedUserId, coreApp, persistent/directBootAware flags, SystemUIService components, permissions, providers/receivers/services and exported values.
- [ ] Confirm `SystemUIApplication` and `SystemUIService` class files remain owned by `:SystemUI-core`; do not move them into app.
- [ ] Treat the project source manifest's omitted `package=` as acceptable only if merged package/namespace is `com.android.systemui`.
- [ ] Record merge report path and semantic differences. If consuming raw AOSP resources requires modifying an AOSP resource file, stop and ask the user.
- [ ] Commit only evidence-backed Gradle wiring changes.

---

### Task 9: Run Final Core and APK Evidence Gates

**Files:**
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/PLAN.md`
- Modify: `docs/issues/2026-08-07-aosp-artifact-recovery.md`

- [ ] Run all Python tests and strict source alignment.
- [ ] Run `./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks --console=plain` and save complete log.
- [ ] If the first blocker is `PluginProtector`, stop and ask the user to choose the processor direction. Do not continue by adding a generated/stub file.
- [ ] If core compiles, run:

```bash
./gradlew :app:assembleDebug --rerun-tasks --console=plain \
  2>&1 | tee /tmp/systemui-assemble-debug.log
```

- [ ] On success, assert an APK exists under `app/build/outputs/apk/debug/`, run `unzip -t`, inspect manifest with available Android SDK tools, and confirm `com/android/systemui/SystemUIApplication.class` and `SystemUIService.class` are packaged through core.
- [ ] Scan APK/class inputs for duplicate classes and confirm no old local-Maven AAR or fat WM Shell JAR remains on runtime classpath.
- [ ] Update active docs with exact commands, exit codes, artifact path and unresolved blockers. Never state APK success when assemble did not exit 0.
- [ ] Run `git diff --check` and commit as `docs: record AOSP artifact recovery boundary`.

## Completion Criteria

This plan is complete only when either:

1. all four direct AARs pass transform without embedded R/source duplicates, manifest merge succeeds, `:app:assembleDebug` exits 0 and the APK is inspected; or
2. execution stops at an explicit rule-H user decision (most likely PluginProtector), with all earlier artifact tasks verified and the exact blocker documented.

A lower Kotlin error count by itself is not a completion criterion.
