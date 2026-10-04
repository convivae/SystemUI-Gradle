# 13-Module Source Topology Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将当前 22 个 Gradle module 收敛为已审定的 13-module 拓扑，使 SystemUI 生产源码、AIDL、资源和 build-time processor 各有唯一真实 owner，并删除 BP 1:1 脚手架与非 SystemUI 违规源码。

**Architecture:** 保留资源 namespace、多消费者、依赖方向和构建工具链形成的深边界；把 Common/Log/Utils、Animation/Shader、Shared/Keyguard、Compose Core/Scene 和 pods 内部切片分别合并。所有 `packages/SystemUI` 生产源码从 AOSP 对应 source root 原样同步，非 SystemUI animationlib/compilelib 先生成直接 AAR/JAR；SettingsLib/iconloader/WM Shell/WifiTrackerLib 的既有 AAR transform 阻塞不在本计划内修复。

**Tech Stack:** Gradle 9.5、AGP 9.2、Kotlin 2.1/AGP embedded Kotlin 2.2.10、KSP、Python 3、AOSP Soong 中间产物、Android AAR/JAR。

## Global Constraints

- 用户明确规则 P：禁止创建 Java/Kotlin stub；`PluginProtectorStub.kt` 不能作为 annotation processor 的替代方案。
- 规则 S/C：进入 SystemUI 生产图的 Java/Kotlin/AIDL/res 必须来自 `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/`，文件集合与内容不漏不多且只有一个 owner。
- 规则 F：`frameworks/libs/systemui/**` 等非 `packages/SystemUI` 源码不得复制进源码 module；无资源使用 JAR，含资源使用 AAR。
- 规则 R：不得创建、改写、合并、去重 AOSP `res/` 文件；AAR 必须保留资源字节内容。
- AAR 先直接引入；只有确认直接 AAR 存在冲突后才安装到 `libs/maven/`。
- `tools/` 下只新增 Python 脚本，不新增 shell 脚本。
- `:app` 只直接依赖 `:SystemUI-core`；入口类继续属于 core。
- 错误数只是诊断；本计划以 owner 对齐、依赖图和 artifact provenance 为验收依据。
- 本计划不宣称修复 SettingsLib/iconloader/WindowManager-Shell/WifiTrackerLib 的重复 R transform，也不宣称最终 APK 成功。
- 每个 commit 前运行该任务列出的验证，并在对应 issue 中如实记录是否编译及结果。

---

## Target File Structure

```text
app/                               # APK 壳，无源码
SystemUI-core/
├── src/                           # AOSP src/
├── src-debug/                     # AOSP src-debug/
├── src-release/                   # AOSP src-release/
├── compose/features/src/          # AOSP compose/features/src/
├── compose/facade/enabled/src/    # AOSP compose/facade/enabled/src/
└── pods/                          # AOSP pods/ 全部生产源码，保持 AOSP 相对路径
SystemUI-res/
├── res/
├── res-keyguard/
├── res-product/
└── AndroidManifest.xml            # Gradle 等价 manifest，namespace 由 DSL 提供
SystemUI-common/
├── common/src/
├── log/src/
└── utils/src/
SystemUI-animation/
├── src/                           # 完整 animation/src，含 surfaceeffects
└── res/
SystemUI-plugin-core/src/
SystemUI-plugin-processor/
├── src/
└── resources/META-INF/services/
SystemUI-plugin/
├── src/
└── bcsmartspace/src/
SystemUI-unfold/src/
SystemUI-customization/{src,res}/
SystemUI-shared/
├── src/
├── keyguard/src/
└── res/
SystemUI-shared-biometrics/{src,res}/
SystemUI-compose/
├── core/src/
└── scene/src/
libs/aars/animationlib.aar
libs/compilelib-debug.jar
libs/compilelib-release.jar
```

最终 `settings.gradle.kts` 只 include：

```kotlin
include(":app")
include(":SystemUI-core")
include(":SystemUI-res")
include(":SystemUI-common")
include(":SystemUI-animation")
include(":SystemUI-plugin-core")
include(":SystemUI-plugin-processor")
include(":SystemUI-plugin")
include(":SystemUI-unfold")
include(":SystemUI-customization")
include(":SystemUI-shared")
include(":SystemUI-shared-biometrics")
include(":SystemUI-compose")
```

---

### Task 1: Synchronize Architecture Policy and Checkpoint the Approved Design

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/adr/0003-app-module-aligns-aosp-bp.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/PLAN.md`
- Modify: `docs/issues/2026-08-06-module-consolidation-plan.md`
- Commit existing: `docs/architecture/2026-08-06-module-structure-audit.md`
- Commit existing: `docs/issues/2026-08-06-gradle-module-boundary-research.md`
- Commit this plan: `docs/superpowers/plans/2026-08-06-13-module-source-topology.md`

**Interfaces:**
- Consumes: approved module decisions in `docs/architecture/2026-08-06-module-structure-audit.md`.
- Produces: one policy definition of Rule B: BP controls source ownership/dependency semantics; Gradle module boundaries follow real seams, not target count.

- [ ] **Step 1: Amend ADR 0003 decision 1**

Replace the BP 1:1 module table with these binding statements:

```markdown
### 决策 1：源码 owner 和依赖语义对齐 BP，Gradle module 不与 target 1:1

- `Android.bp` 是生产 source roots、资源 owner、static/libs/plugins 语义的唯一依据。
- Soong target 是编译图节点；多个内部 target 可合入一个 Gradle module。
- 独立 Gradle module 只由 R namespace、多消费者、外部 API、处理器/AIDL工具链或防止依赖环证明。
- 目标模块图以 `docs/architecture/2026-08-06-module-structure-audit.md` 的 13-module 清单为准。
```

Keep the existing app/core entry-class and manifest decisions, but remove claims that `SystemUILogLib`, keyguard child, Compose Scene, pods, or every `android_library` must each map to a project module.

- [ ] **Step 2: Synchronize AGENTS/HANDOFF/CURRENT_STATE/PLAN**

Use the same exact target list from this plan. Update:

- `AGENTS.md` §1.9 and §3.1;
- `HANDOFF.md` rules, project tree, stale animationlib section and next action;
- `CURRENT_STATE.md` leading status block;
- `PLAN.md` leading warning and stage overview.

State explicitly that animationlib is non-SystemUI and must become AAR, kairos is test-only for this APK graph, and current build remains blocked before Kotlin compilation.

- [ ] **Step 3: Verify policy consistency**

Run:

```bash
rg -n 'BP 1:1|bp 1:1|必须严格对应|animationlib 源码化|SystemUI-log.*独立' \
  AGENTS.md docs/adr/0003-app-module-aligns-aosp-bp.md docs/HANDOFF.md \
  docs/CURRENT_STATE.md docs/PLAN.md
```

Expected: no active policy requires one Gradle module per Soong target; historical statements are either removed or marked obsolete.

Run:

```bash
python3 - <<'PY'
from pathlib import Path
files = [
    Path("AGENTS.md"),
    Path("docs/adr/0003-app-module-aligns-aosp-bp.md"),
    Path("docs/HANDOFF.md"),
]
required = ["13", "SystemUI-res", "SystemUI-plugin-processor", "SystemUI-compose"]
for path in files:
    text = path.read_text()
    missing = [word for word in required if word not in text]
    assert not missing, (path, missing)
print("policy target list: PASS")
PY

git diff --check
```

Expected: both commands exit 0.

- [ ] **Step 4: Record build status**

Append to `docs/issues/2026-08-06-module-consolidation-plan.md`:

```markdown
## 政策同步验证

- 未运行源码编译；本任务仅同步架构政策。
- `git diff --check`：通过。
- 当前构建阻塞仍为既有 AAR transform 重复 R 类。
```

- [ ] **Step 5: Commit the architecture checkpoint**

```bash
git add .
git commit -m "docs: adopt 13-module SystemUI topology"
```

---

### Task 2: Make Source Alignment Content-Aware and Target-Owner-Aware

**Files:**
- Modify: `tools/check_source_alignment.py`
- Create: `tools/tests/test_check_source_alignment.py`
- Modify: `docs/issues/2026-08-06-module-consolidation-plan.md`

**Interfaces:**
- Consumes: target physical roots in “Target File Structure”.
- Produces: `SOURCE_MAPPINGS`, `RES_MAPPINGS`, `--strict`, and content mismatch categories used by every later task.

- [ ] **Step 1: Write mapping tests that fail against the old script**

Create `tools/tests/test_check_source_alignment.py` with `unittest` and dynamic import of `tools/check_source_alignment.py`. Assert:

```python
EXPECTED_OWNERS = {
    "SystemUI-core",
    "SystemUI-common",
    "SystemUI-animation",
    "SystemUI-plugin-core",
    "SystemUI-plugin-processor",
    "SystemUI-plugin",
    "SystemUI-unfold",
    "SystemUI-customization",
    "SystemUI-shared",
    "SystemUI-shared-biometrics",
    "SystemUI-compose",
}

FORBIDDEN_OWNERS = {
    "SystemUI-log",
    "SystemUI-animationlib",
    "SystemUI-utils-kairos",
    "SystemUI-compose-core",
    "SystemUI-compose-scene",
    "SystemUI-shared-keyguard",
    "SystemUI-proto",
    "SystemUI-pods-dagger",
    "SystemUI-pods-retail",
    "SystemUI-pods-data",
    "SystemUI-pods-domain",
    "SystemUI-pods-settings",
}
```

The tests must also assert that resource roots `res`, `res-keyguard`, and `res-product` map to `SystemUI-res`, that matching relative paths with different bytes are reported as modified, and that a file present under the wrong source root of the **same Gradle module** is reported as misplaced.

- [ ] **Step 2: Run the tests and confirm the old mapping fails**

```bash
python3 -m unittest tools.tests.test_check_source_alignment -v
```

Expected: FAIL because the current mapping still contains forbidden owners and has no content mismatch detection.

- [ ] **Step 3: Replace mappings with final physical owners**

Define one mapping per AOSP source root instead of flattening multiple roots into one destination:

```python
SOURCE_MAPPINGS = [
    M(["src"], "SystemUI-core", "src", note="SystemUI-core src"),
    M(["src-debug"], "SystemUI-core", "src-debug", note="DebugJavaFiles"),
    M(["src-release"], "SystemUI-core", "src-release", note="ReleaseJavaFiles"),
    M(["compose/features/src"], "SystemUI-core", "compose/features/src"),
    M(["compose/facade/enabled/src"], "SystemUI-core", "compose/facade/enabled/src"),
    M(["common/src"], "SystemUI-common", "common/src"),
    M(["log/src"], "SystemUI-common", "log/src"),
    M(["utils/src"], "SystemUI-common", "utils/src"),
    M(["animation/src"], "SystemUI-animation", "src"),
    M(["plugin_core/src"], "SystemUI-plugin-core", "src"),
    M(["plugin_core/processor/src"], "SystemUI-plugin-processor", "src"),
    M(["plugin/src"], "SystemUI-plugin", "src",
      exclude_tails=["com/android/systemui/plugins/PluginProtectorStub.kt"]),
    M(["plugin/bcsmartspace/src"], "SystemUI-plugin", "bcsmartspace/src"),
    M(["unfold/src"], "SystemUI-unfold", "src"),
    M(["customization/src"], "SystemUI-customization", "src"),
    M(["shared/src"], "SystemUI-shared", "src"),
    M(["shared/keyguard/src"], "SystemUI-shared", "keyguard/src"),
    M(["shared/biometrics/src"], "SystemUI-shared-biometrics", "src"),
    M(["compose/core/src"], "SystemUI-compose", "core/src"),
    M(["compose/scene/src"], "SystemUI-compose", "scene/src"),
    M(["pods"], "SystemUI-core", "pods"),
]

RES_MAPPINGS = [
    ("res", "SystemUI-res/res"),
    ("res-keyguard", "SystemUI-res/res-keyguard"),
    ("res-product", "SystemUI-res/res-product"),
    ("shared/res", "SystemUI-shared/res"),
    ("shared/biometrics/res", "SystemUI-shared-biometrics/res"),
    ("animation/res", "SystemUI-animation/res"),
    ("customization/res", "SystemUI-customization/res"),
]
```

Do not include `utils/kairos` or `animation/lib` because neither enters the production `SystemUI-core` graph. Remove `SURFACEEFFECTS_PREFIX`, `check_shader_lib()` and the independent shader summary: surfaceeffects is now part of the complete animation mapping.

Make global lookup root-aware: index and search hits must carry `(aosp_subdir, project_module, project_src_root)`, not only the module name. A file found under a different source root of the same module is still misplaced.

- [ ] **Step 4: Add byte-content verification and strict exit status**

For every path in both expected and actual sets, compare `Path.read_bytes()`. Add `[MODIFIED]` and `[RES-MODIFIED]` counts. Add:

```python
ap.add_argument("--strict", action="store_true",
                help="任一 missing/misplaced/extra/modified 时退出 1")
```

Return 1 when `--strict` and any source/resource/app count is non-zero; invoke with `sys.exit(main())`.

- [ ] **Step 5: Run tests and establish the expected red migration baseline**

```bash
python3 -m unittest tools.tests.test_check_source_alignment -v
python3 -m py_compile tools/check_source_alignment.py tools/tests/test_check_source_alignment.py
python3 tools/check_source_alignment.py --summary --strict; test $? -eq 1
```

Expected: unit tests PASS; real alignment exits 1 because module migration has not run yet.

- [ ] **Step 6: Commit the alignment contract**

Record the red count summary in the issue, then:

```bash
git add .
git commit -m "tools: model final SystemUI source owners"
```

---

### Task 3: Consolidate Common, Log, and Shared Utils

**Files:**
- Rewrite: `SystemUI-common/build.gradle.kts`
- Replace source tree: `SystemUI-common/{common,log,utils}/src/`
- Delete: `SystemUI-common/src/`
- Delete: `SystemUI-log/`
- Modify: `SystemUI-plugin/build.gradle.kts`
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `settings.gradle.kts`

**Interfaces:**
- Consumes: AOSP `common/src`, `log/src`, `utils/src`.
- Produces: JVM source module `:SystemUI-common` exposing Common/Log/Utils classes to plugin and core.

- [ ] **Step 1: Sync the three AOSP roots exactly**

```bash
AOSP=/home/conv/myspace/aosp/frameworks/base/packages/SystemUI
rm -rf SystemUI-common/src SystemUI-common/common SystemUI-common/log SystemUI-common/utils
mkdir -p SystemUI-common/common SystemUI-common/log SystemUI-common/utils
cp -a "$AOSP/common/src" SystemUI-common/common/src
cp -a "$AOSP/log/src" SystemUI-common/log/src
cp -a "$AOSP/utils/src" SystemUI-common/utils/src
```

- [ ] **Step 2: Convert common to a JVM source module**

Use `java-library` plus `libs.plugins.kotlin.jvm`; configure Java and Kotlin source roots to the same three directories and JVM 21. Dependencies:

```kotlin
dependencies {
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))
    api(libs.kotlinx.coroutines.core)
    implementation(libs.errorprone.annotations)
    compileOnly(libs.androidx.annotation)
}
```

No Android manifest, namespace, Android resources, or `com.android.library` plugin remains.

- [ ] **Step 3: Rewire consumers and remove the old module**

- In plugin, replace `implementation(project(":SystemUI-log"))` with `api(project(":SystemUI-common"))`.
- In core, keep one `implementation(project(":SystemUI-common"))` and remove `:SystemUI-log`.
- Remove `include(":SystemUI-log")` and delete `SystemUI-log/`.

- [ ] **Step 4: Verify the isolated module**

```bash
./gradlew :SystemUI-common:compileKotlin --console=plain
python3 tools/check_source_alignment.py --summary
```

Expected: common Kotlin compilation exits 0; Common/Log/Utils no longer appear missing or misplaced.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "refactor: consolidate SystemUI common sources"
```

---

### Task 4: Package animationlib as a Direct AAR and Merge Shader Sources

**Files:**
- Create: `tools/package_aosp_aar.py`
- Create: `tools/tests/test_package_aosp_aar.py`
- Create generated artifact: `libs/aars/animationlib.aar`
- Modify: `SystemUI-animation/build.gradle.kts`
- Replace: `SystemUI-animation/src/`, `SystemUI-animation/res/`
- Modify: `SystemUI-customization/build.gradle.kts`
- Modify: `SystemUI-compose-core/build.gradle.kts` temporarily until Task 6 replaces it
- Delete: `SystemUI-animationlib/`
- Delete: `libs/animationlib.jar`
- Modify: `settings.gradle.kts`

**Interfaces:**
- Consumes:
  - AOSP `frameworks/libs/systemui/animationlib` source resources;
  - Soong `android_common/javac/animationlib.jar` and `android_common/kotlin/animationlib.jar`.
- Produces: direct AAR with merged code JAR, original resource bytes, `R.txt`, and no precompiled R classes.

- [ ] **Step 1: Write failing AAR packager tests**

Tests must create temporary Java/Kotlin JARs and a resource directory, then assert:

1. both input classes appear in AAR `classes.jar`;
2. resource bytes are unchanged;
3. `R.class`/`R$*.class` input entries are rejected;
4. duplicate non-directory JAR entries raise `DuplicateEntryError`;
5. no POM or Maven repository is generated.

Run:

```bash
python3 -m unittest tools.tests.test_package_aosp_aar -v
```

Expected: FAIL because the packager does not exist.

- [ ] **Step 2: Implement the strict direct-AAR packager**

`tools/package_aosp_aar.py` must expose:

```python
class DuplicateEntryError(RuntimeError):
    pass

def merge_code_jars(jars: list[Path], output: Path) -> None: ...
def copy_resource_tree(source: Path, destination: Path) -> None: ...
def build_animationlib(output: Path) -> None: ...
```

Rules enforced in code:

- merge only the explicit javac and Kotlin jars;
- skip directory entries and duplicate `META-INF/MANIFEST.MF` only;
- fail on every other duplicate entry;
- fail if any input class basename is `R.class` or starts with `R$`;
- copy `frameworks/libs/systemui/animationlib/res/` byte-for-byte;
- copy AOSP `AndroidManifest.xml` and Soong `R.txt` without editing;
- write a deterministic ZIP with sorted entry names;
- default CLI output is `libs/aars/animationlib.aar`;
- do not touch `libs/maven/`.

- [ ] **Step 3: Verify tests and produce the AAR**

```bash
python3 -m unittest tools.tests.test_package_aosp_aar -v
python3 -m py_compile tools/package_aosp_aar.py tools/tests/test_package_aosp_aar.py
python3 tools/package_aosp_aar.py animationlib --output libs/aars/animationlib.aar
unzip -t libs/aars/animationlib.aar
python3 - <<'PY'
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile
p = Path("libs/aars/animationlib.aar")
with ZipFile(p) as aar:
    assert "res/values/ids.xml" in aar.namelist()
    with ZipFile(BytesIO(aar.read("classes.jar"))) as classes:
        names = set(classes.namelist())
        assert "com/android/app/animation/Animations.class" in names
        assert "com/android/app/animation/Interpolators.class" in names
        assert not any(n.rsplit("/", 1)[-1] == "R.class" or
                       n.rsplit("/", 1)[-1].startswith("R$") for n in names)
print("animationlib AAR: PASS")
PY
```

Expected: all commands exit 0.

- [ ] **Step 4: Sync the complete animation owner**

```bash
AOSP=/home/conv/myspace/aosp/frameworks/base/packages/SystemUI
rm -rf SystemUI-animation/src SystemUI-animation/res
cp -a "$AOSP/animation/src" SystemUI-animation/src
cp -a "$AOSP/animation/res" SystemUI-animation/res
```

This intentionally includes all 22 surfaceeffects files in the same module.

- [ ] **Step 5: Rewire animationlib consumers**

Use direct file AAR:

```kotlin
api(files("${rootProject.projectDir}/libs/aars/animationlib.aar"))
```

Apply it in animation and customization; use `implementation(files(...))` in the temporary compose-core script. Remove all references to `libs/animationlib.jar` and `project(":SystemUI-animationlib")`. Remove the module from settings and delete its directory and old JAR.

- [ ] **Step 6: Verify owner and dependency shape**

```bash
./gradlew :SystemUI-animation:compileDebugKotlin --console=plain
python3 tools/check_source_alignment.py --summary
rg -n 'SystemUI-animationlib|libs/animationlib\.jar' --glob '!docs/**' . && exit 1 || true
```

Expected: animation compile exits 0; 54 animation source files have the animation owner; no active build file references the deleted module/JAR.

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "refactor: merge shader and package animationlib AAR"
```

---

### Task 5: Consolidate Shared and Keyguard while Preserving Biometrics R

**Files:**
- Replace: `SystemUI-shared/src/`, `SystemUI-shared/res/`
- Create: `SystemUI-shared/keyguard/src/`
- Modify: `SystemUI-shared/build.gradle.kts`
- Replace: `SystemUI-shared-biometrics/src/`, `SystemUI-shared-biometrics/res/`
- Create: `SystemUI-shared-biometrics/AndroidManifest.xml`
- Replace: `SystemUI-customization/src/`, `SystemUI-customization/res/`
- Modify: `SystemUI-customization/build.gradle.kts`
- Replace: `SystemUI-unfold/src/`
- Modify: `SystemUI-unfold/build.gradle.kts`
- Delete: `libs/shared-uncaught-handler.jar`
- Modify: `SystemUI-shared-biometrics/build.gradle.kts`
- Delete: `SystemUI-shared-keyguard/`
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `settings.gradle.kts`

**Interfaces:**
- Consumes: AOSP shared, keyguard child, biometrics source/resource roots.
- Produces: `:SystemUI-shared` with two source roots and `api(:SystemUI-shared-biometrics)` preserving both R namespaces.

- [ ] **Step 1: Sync source/resource roots exactly**

```bash
AOSP=/home/conv/myspace/aosp/frameworks/base/packages/SystemUI
rm -rf SystemUI-shared/src SystemUI-shared/res SystemUI-shared/keyguard
cp -a "$AOSP/shared/src" SystemUI-shared/src
cp -a "$AOSP/shared/res" SystemUI-shared/res
mkdir -p SystemUI-shared/keyguard
cp -a "$AOSP/shared/keyguard/src" SystemUI-shared/keyguard/src

rm -rf SystemUI-shared-biometrics/src SystemUI-shared-biometrics/res
cp -a "$AOSP/shared/biometrics/src" SystemUI-shared-biometrics/src
cp -a "$AOSP/shared/biometrics/res" SystemUI-shared-biometrics/res

rm -rf SystemUI-customization/src SystemUI-customization/res SystemUI-unfold/src
cp -a "$AOSP/customization/src" SystemUI-customization/src
cp -a "$AOSP/customization/res" SystemUI-customization/res
cp -a "$AOSP/unfold/src" SystemUI-unfold/src
```

- [ ] **Step 2: Configure sourceSets and internal static edges**

Shared main sourceSet uses `src` and `keyguard/src` for Java/Kotlin, `src` for AIDL, and `res` for resources. Internal BP static dependencies become:

```kotlin
api(project(":SystemUI-shared-biometrics"))
api(project(":SystemUI-animation"))
api(project(":SystemUI-plugin-core"))
api(project(":SystemUI-plugin"))
api(project(":SystemUI-unfold"))
```

Keep existing non-SystemUI JAR dependencies unchanged in this plan; their final AAR/JAR decomposition belongs to the artifact-recovery plan.

Biometrics uses source root `src`, resource root `res`, namespace `com.android.systemui.shared.biometrics`, and this AGP-compatible empty manifest:

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" />
```

Customization uses Java/Kotlin/AIDL root `src`, resource root `res`, `buildFeatures.aidl = true`, and exactly these internal edges:

```kotlin
api(project(":SystemUI-animation"))
api(project(":SystemUI-plugin-core"))
api(project(":SystemUI-plugin"))
api(project(":SystemUI-unfold"))
```

Remove its old `:SystemUI-log` and `:SystemUI-shared` edges. Keep unfold's existing AIDL/KSP build configuration while replacing its source bytes from AOSP.

- [ ] **Step 3: Remove the keyguard module and wrong core edges**

Remove `:SystemUI-shared-keyguard` from settings and delete its directory. Remove core direct dependencies on biometrics, keyguard and unfold; those are exposed through shared/customization.

Remove `shared-uncaught-handler.jar` from shared/core and delete the JAR: after exact source resync it would duplicate `UncaughtExceptionPreHandlerManager`. If the source then fails on the libcore-hidden `Thread.setUncaughtExceptionPreHandler`, record that SDK/core-library gap for the artifact/SDK plan rather than restoring the prebuilt duplicate.

- [ ] **Step 4: Verify ownership**

```bash
python3 tools/check_source_alignment.py --summary
./gradlew :SystemUI-shared-biometrics:compileDebugKotlin --console=plain
```

Expected: biometrics compile exits 0; shared/keyguard, biometrics, customization and unfold mappings report no missing/misplaced/modified files. A full shared compile may still expose the pre-existing hidden `Thread`/Dagger dependency problem; record it without restoring a source stub.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "refactor: consolidate SystemUI shared sources"
```

---

### Task 6: Merge Compose Core and Scene into One Module

**Files:**
- Create: `SystemUI-compose/build.gradle.kts`
- Create: `SystemUI-compose/AndroidManifest.xml`
- Create: `SystemUI-compose/core/src/` from AOSP
- Create: `SystemUI-compose/scene/src/` from AOSP
- Delete: `SystemUI-compose-core/`
- Delete: `SystemUI-compose-scene/`
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `settings.gradle.kts`

**Interfaces:**
- Consumes: all dependencies currently split across compose-core and compose-scene.
- Produces: `:SystemUI-compose` with one Compose compiler configuration and `api(:SystemUI-animation)`.

- [ ] **Step 1: Create exact source roots**

```bash
AOSP=/home/conv/myspace/aosp/frameworks/base/packages/SystemUI
rm -rf SystemUI-compose
mkdir -p SystemUI-compose/core SystemUI-compose/scene
cp -a "$AOSP/compose/core/src" SystemUI-compose/core/src
cp -a "$AOSP/compose/scene/src" SystemUI-compose/scene/src
```

- [ ] **Step 2: Create the combined Android/Compose module**

Use namespace `com.android.compose`, compileSdk `SysUISdk`, JVM 21, Kotlin Compose plugin, and both roots in Java/Kotlin sourceSets. Union the existing Maven dependencies without duplicate coordinates. Internal dependency:

```kotlin
api(project(":SystemUI-animation"))
implementation(files("${rootProject.projectDir}/libs/aars/animationlib.aar"))
implementation(files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar"))
```

Use this Gradle-adaptation manifest because both AOSP manifests are empty namespace carriers and AGP manages namespace in DSL:

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" />
```

- [ ] **Step 3: Replace old project edges**

Core gets one `implementation(project(":SystemUI-compose"))`. Remove both old includes/direct dependencies and delete old directories.

- [ ] **Step 4: Verify**

```bash
./gradlew :SystemUI-compose:compileDebugKotlin --console=plain
python3 tools/check_source_alignment.py --summary
```

Expected: compose compile exits 0; all 27 core and 50 scene files have one owner and byte-match AOSP.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "refactor: consolidate Platform Compose sources"
```

---

### Task 7: Create the SystemUI Resource Namespace Module

**Files:**
- Create: `SystemUI-res/build.gradle.kts`
- Create: `SystemUI-res/AndroidManifest.xml`
- Create: `SystemUI-res/{res,res-keyguard,res-product}/`
- Delete from core: `SystemUI-core/{res,res-keyguard,res-product}/`
- Delete: `app/src/main/AndroidManifest-res.xml`
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: `settings.gradle.kts`

**Interfaces:**
- Consumes: exact AOSP SystemUI resource trees and shared/customization resource dependencies.
- Produces: `com.android.systemui.res.R` without modifying any source import or resource file.

- [ ] **Step 1: Copy resources from AOSP, not from the current project copy**

```bash
AOSP=/home/conv/myspace/aosp/frameworks/base/packages/SystemUI
rm -rf SystemUI-res
mkdir -p SystemUI-res
cp -a "$AOSP/res" SystemUI-res/res
cp -a "$AOSP/res-keyguard" SystemUI-res/res-keyguard
cp -a "$AOSP/res-product" SystemUI-res/res-product
rm -rf SystemUI-core/res SystemUI-core/res-keyguard SystemUI-core/res-product
rm -f app/src/main/AndroidManifest-res.xml
```

- [ ] **Step 2: Create the resource-only Android library**

Use namespace `com.android.systemui.res`, no Java/Kotlin source roots, and:

```kotlin
sourceSets {
    getByName("main") {
        res.srcDirs("res-product", "res-keyguard", "res")
        manifest.srcFile("AndroidManifest.xml")
    }
}

dependencies {
    api(project(":SystemUI-shared"))
    api(project(":SystemUI-customization"))
    api(libs.systemui.settingslib)
    api(libs.androidx.leanback)
    api(libs.androidx.slice.core)
    api(libs.androidx.slice.view)
}
```

Use an AGP-compatible manifest preserving the empty-application semantics of AOSP `AndroidManifest-res.xml` while moving the package into `namespace`:

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application />
</manifest>
```

Do not alter any file under the three `res*` directories.

- [ ] **Step 3: Rewire core**

Remove core `res.srcDirs(...)`, add `implementation(project(":SystemUI-res"))`, and include `:SystemUI-res` in settings.

- [ ] **Step 4: Verify resource bytes and R import ownership**

```bash
python3 tools/check_source_alignment.py --summary
python3 - <<'PY'
from pathlib import Path
A = Path("/home/conv/myspace/aosp/frameworks/base/packages/SystemUI")
P = Path("SystemUI-res")
for name in ("res", "res-keyguard", "res-product"):
    af = {p.relative_to(A / name): p.read_bytes() for p in (A / name).rglob("*") if p.is_file()}
    pf = {p.relative_to(P / name): p.read_bytes() for p in (P / name).rglob("*") if p.is_file()}
    assert af == pf, name
print("SystemUI resources: byte-identical")
PY
```

Expected: exact resource comparison exits 0. Do not require `processDebugResources` to pass yet because the existing SettingsLib AAR duplicate-R transform is outside this plan.

- [ ] **Step 5: Commit**

```bash
git add .
git commit -m "refactor: isolate SystemUI resource namespace"
```

---

### Task 8: Fold Pods into Core and Remove Non-Production/Generated Scaffolds

**Files:**
- Create exact roots under: `SystemUI-core/compose/` and `SystemUI-core/pods/`
- Modify: `SystemUI-core/build.gradle.kts`
- Modify: root `build.gradle.kts`
- Modify: `settings.gradle.kts`
- Delete: `SystemUI-utils-kairos/`
- Delete: `SystemUI-proto/`
- Delete: `SystemUI-pods-dagger/`
- Delete: `SystemUI-pods-retail/`
- Delete: `SystemUI-pods-data/`
- Delete: `SystemUI-pods-domain/`
- Delete: `SystemUI-pods-settings/`
- Delete: `SystemUI-pods-retail-data-impl/`
- Delete: `SystemUI-pods-retail-domain-impl/`
- Remove by exact core resync: `SystemUI-core/src/com/android/systemui/util/Compile.java`
- Create: `tools/package_compilelib_jars.py`
- Create: `libs/compilelib-debug.jar`
- Create: `libs/compilelib-release.jar`

**Interfaces:**
- Consumes: core BP source roots, pods source tree, AOSP compilelib debug/release Java sources, existing generated `SystemUI-proto.jar`.
- Produces: one core owner for private pods and variant-correct compilelib JAR dependencies.

- [ ] **Step 1: Resync all core-owned roots exactly**

```bash
AOSP=/home/conv/myspace/aosp/frameworks/base/packages/SystemUI
rm -rf SystemUI-core/src SystemUI-core/src-debug SystemUI-core/src-release \
       SystemUI-core/compose SystemUI-core/pods
cp -a "$AOSP/src" SystemUI-core/src
cp -a "$AOSP/src-debug" SystemUI-core/src-debug
cp -a "$AOSP/src-release" SystemUI-core/src-release
mkdir -p SystemUI-core/compose/features SystemUI-core/compose/facade/enabled
cp -a "$AOSP/compose/features/src" SystemUI-core/compose/features/src
cp -a "$AOSP/compose/facade/enabled/src" SystemUI-core/compose/facade/enabled/src
mkdir -p SystemUI-core/pods
rsync -a --prune-empty-dirs \
  --include='*/' --include='*.java' --include='*.kt' --include='*.aidl' --exclude='*' \
  "$AOSP/pods/" SystemUI-core/pods/
```

This removes the copied non-SystemUI `Compile.java` automatically because it does not exist in AOSP `packages/SystemUI/src`.

- [ ] **Step 2: Package compilelib debug/release JARs without copying source into a module**

`tools/package_compilelib_jars.py` must compile these two external AOSP files independently with JDK 21 and package deterministic JARs:

```text
frameworks/libs/systemui/compilelib/src-debug/com/android/systemui/util/Compile.java
frameworks/libs/systemui/compilelib/src-release/com/android/systemui/util/Compile.java
```

CLI output:

```text
libs/compilelib-debug.jar
libs/compilelib-release.jar
```

The script must use a temporary directory, invoke `javac --release 21`, include only `Compile.class`, and remove the temporary directory. Verify:

```bash
python3 tools/package_compilelib_jars.py
unzip -t libs/compilelib-debug.jar
unzip -t libs/compilelib-release.jar
javap -classpath libs/compilelib-debug.jar -verbose com.android.systemui.util.Compile | rg 'ConstantValue: int 1'
javap -classpath libs/compilelib-release.jar -verbose com.android.systemui.util.Compile | rg 'ConstantValue: int 0'
```

Expected: debug and release bytecode return different AOSP constants; both archives pass integrity checks.

- [ ] **Step 3: Configure core sourceSets and variant dependencies**

Main Java/Kotlin roots:

```kotlin
java.srcDirs(
    "src",
    "compose/features/src",
    "compose/facade/enabled/src",
    "pods",
)
aidl.srcDirs("src")
```

Variant dependencies:

```kotlin
debugImplementation(files("${rootProject.projectDir}/libs/compilelib-debug.jar"))
releaseImplementation(files("${rootProject.projectDir}/libs/compilelib-release.jar"))
implementation(files("${rootProject.projectDir}/libs/SystemUI-proto.jar"))
```

Keep exactly one `SystemUI-proto.jar` dependency and no `project(":SystemUI-proto")`.

- [ ] **Step 4: Replace the internal project dependency block**

Core project dependencies become exactly:

```kotlin
implementation(project(":SystemUI-res"))
implementation(project(":SystemUI-animation"))
implementation(project(":SystemUI-common"))
implementation(project(":SystemUI-customization"))
implementation(project(":SystemUI-plugin"))
implementation(project(":SystemUI-shared"))
implementation(project(":SystemUI-compose"))
```

No direct project dependency remains on plugin-core, unfold, biometrics, keyguard, kairos, proto, pods, or deleted compose modules.

- [ ] **Step 5: Remove obsolete modules and includes**

Delete all directories listed in this task and remove their settings entries. Remove the now-invalid global Kairos opt-in compiler flag from root `build.gradle.kts`. Do not delete `utils/kairos` from the AOSP checkout; it is simply outside this APK production graph.

- [ ] **Step 6: Verify ownership and configuration**

```bash
python3 tools/check_source_alignment.py --summary
./gradlew projects --console=plain
rg -n 'SystemUI-(utils-kairos|proto|pods-|shared-keyguard|compose-core|compose-scene)' \
  settings.gradle.kts SystemUI-*/build.gradle.kts && exit 1 || true
```

Expected: Gradle project configuration exits 0; deleted project names have no active build references.

- [ ] **Step 7: Commit**

```bash
git add .
git commit -m "refactor: fold SystemUI private sources into core"
```

---

### Task 9: Restore the Plugin Annotation Processor Boundary

**Files:**
- Replace: `SystemUI-plugin-core/src/`
- Replace: `SystemUI-plugin/{src,bcsmartspace/src}/`
- Create: `SystemUI-plugin-processor/build.gradle.kts`
- Create: `SystemUI-plugin-processor/src/`
- Create: `SystemUI-plugin-processor/resources/META-INF/services/javax.annotation.processing.Processor`
- Rewrite: `SystemUI-plugin-core/build.gradle.kts`
- Create: `SystemUI-plugin/build.gradle.kts`
- Create: `SystemUI-plugin/AndroidManifest.xml`
- Modify: `gradle/libs.versions.toml`
- Modify: `app/build.gradle.kts`
- Modify: `settings.gradle.kts`
- Delete inactive: `SystemUI-plugin/src/main/com/`

**Interfaces:**
- Consumes: AOSP plugin runtime/core/processor sources.
- Produces: runtime plugin API without `PluginProtectorStub.kt`, plus build-time processor generating `PluginProtector`.

- [ ] **Step 1: Sync AOSP roots and remove the production-excluded stub**

```bash
AOSP=/home/conv/myspace/aosp/frameworks/base/packages/SystemUI
rm -rf SystemUI-plugin-core/src SystemUI-plugin/src SystemUI-plugin/bcsmartspace \
       SystemUI-plugin-processor
cp -a "$AOSP/plugin_core/src" SystemUI-plugin-core/src
mkdir -p SystemUI-plugin SystemUI-plugin-processor SystemUI-plugin/bcsmartspace
cp -a "$AOSP/plugin/src" SystemUI-plugin/src
cp -a "$AOSP/plugin/bcsmartspace/src" SystemUI-plugin/bcsmartspace/src
cp -a "$AOSP/plugin_core/processor/src" SystemUI-plugin-processor/src
rm SystemUI-plugin/src/com/android/systemui/plugins/PluginProtectorStub.kt
```

The alignment mapping excludes the stub because BP excludes it from production.

- [ ] **Step 2: Convert plugin-core to a JVM source library**

Use `java-library` + Kotlin JVM, source root `src`, JVM 21, compileOnly framework.jar/AndroidX annotations, and Kotlin stdlib. It must not have Android resources or a manifest.

- [ ] **Step 3: Create the processor JVM module and service descriptor**

Processor dependencies:

```kotlin
implementation(project(":SystemUI-plugin-core"))
compileOnly("com.google.auto.service:auto-service-annotations:1.1.1")
implementation(libs.kotlin.stdlib)
```

Create `resources/META-INF/services/javax.annotation.processing.Processor` containing exactly:

```text
com.android.systemui.plugins.processor.ProtectedPluginProcessor
```

Configure the JVM main resource source set with `resources` so the descriptor is packaged into the processor JAR. This file is Gradle packaging metadata equivalent to Soong `auto_service_plugin`; it is not a stub implementation.

- [ ] **Step 4: Enable KAPT only on plugin and wire the processor**

Add catalog plugin:

```toml
kotlin-kapt = { id = "org.jetbrains.kotlin.kapt", version.ref = "kotlin" }
```

Plugin module applies it and uses this AGP-compatible empty manifest:

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" />
```

Its dependencies are:

```kotlin
kapt(project(":SystemUI-plugin-processor"))
api(project(":SystemUI-plugin-core"))
api(project(":SystemUI-animation"))
api(project(":SystemUI-common"))
```

Source roots are `src` and `bcsmartspace/src`. Do not include the stub. Remove `id("kotlin-kapt")` from `:app`: app has no source or processor and must remain a thin APK shell.

- [ ] **Step 5: Verify processor discovery and generated output**

```bash
./gradlew :SystemUI-plugin:clean :SystemUI-plugin:compileDebugKotlin --console=plain
find SystemUI-plugin/build/generated -type f \
  \( -name 'PluginProtector.java' -o -name '*Protected*.java' \) -print | sort
```

Expected: compile exits 0 and generated Java output includes `PluginProtector.java`.

If KAPT fails under the active AGP/Kotlin combination, stop this task, record the complete stack trace in `docs/issues/2026-08-06-module-consolidation-plan.md`, and ask the user before selecting another compiler/toolchain. Do not re-add `PluginProtectorStub.kt`.

- [ ] **Step 6: Verify exact ownership and commit**

```bash
python3 tools/check_source_alignment.py --summary
unzip -p SystemUI-plugin-processor/build/libs/*.jar \
  META-INF/services/javax.annotation.processing.Processor
```

Expected service output is exactly the processor class plus newline.

```bash
git add .
git commit -m "build: restore SystemUI plugin processor"
```

---

### Task 10: Finalize the 13-Module Graph and Alignment Checkpoint

**Files:**
- Modify: `settings.gradle.kts`
- Modify: all retained `SystemUI-*/build.gradle.kts` as needed for final internal edges
- Modify: `docs/issues/2026-08-06-module-consolidation-plan.md`
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/HANDOFF.md`

**Interfaces:**
- Consumes: Tasks 1–9.
- Produces: exact 13-module settings graph, source/res alignment green, and an honest handoff before AAR recovery.

- [ ] **Step 1: Replace settings includes with the exact target list**

Use the 13-line block at the top of this plan. Remove all BP 1:1 scaffold comments.

- [ ] **Step 2: Assert the internal dependency graph**

Run a Python assertion over retained build scripts:

```bash
python3 - <<'PY'
from pathlib import Path
import re
settings = Path("settings.gradle.kts").read_text()
mods = re.findall(r'include\("(:[^"]+)"\)', settings)
expected = [
    ":app", ":SystemUI-core", ":SystemUI-res", ":SystemUI-common",
    ":SystemUI-animation", ":SystemUI-plugin-core",
    ":SystemUI-plugin-processor", ":SystemUI-plugin", ":SystemUI-unfold",
    ":SystemUI-customization", ":SystemUI-shared",
    ":SystemUI-shared-biometrics", ":SystemUI-compose",
]
assert mods == expected, (mods, expected)
assert len(mods) == len(set(mods)) == 13
print("13-module settings graph: PASS")
PY
```

- [ ] **Step 3: Run source/resource alignment as the primary acceptance test**

```bash
python3 -m unittest discover -s tools/tests -v
python3 -m py_compile tools/*.py tools/tests/*.py
python3 tools/check_source_alignment.py --strict
```

Expected: all tests pass and strict alignment exits 0 with zero missing, misplaced, extra, modified, resource missing/extra/modified counts.

- [ ] **Step 4: Run Gradle configuration and isolated module evidence**

```bash
./gradlew projects --console=plain
./gradlew \
  :SystemUI-common:compileKotlin \
  :SystemUI-animation:compileDebugKotlin \
  :SystemUI-shared-biometrics:compileDebugKotlin \
  :SystemUI-compose:compileDebugKotlin \
  :SystemUI-plugin:compileDebugKotlin \
  --console=plain
```

Expected: configuration succeeds and isolated modules compile. If an actual dependency/API mismatch appears, record it by module and do not alter AOSP source to hide it.

- [ ] **Step 5: Capture the known core build boundary**

Run once because the result is useful evidence:

```bash
./gradlew :SystemUI-core:compileDebugKotlin --console=plain \
  2>&1 | tee /tmp/systemui-core-after-topology.log
```

Expected current outcome: either the existing AAR transform duplicate-R error remains, or the build advances to a later real error. Record the first failing task and exact exception; do not claim Kotlin success unless the task actually exits 0.

- [ ] **Step 6: Update state and handoff**

Record:

- final 13 modules;
- source/res strict alignment result;
- each isolated compile result;
- core’s actual first blocker;
- next work item: a separate direct-AAR/JAR ownership and transform-recovery plan;
- `:app:assembleDebug` was not run unless core compilation unexpectedly succeeds and a full build has evidence value.

- [ ] **Step 7: Final checkpoint commit**

```bash
git add .
git commit -m "refactor: establish 13-module SystemUI topology"
```

---

## Out of Scope and Next Plan

After this plan, create `docs/superpowers/plans/2026-08-06-aosp-artifact-recovery.md` from fresh artifact evidence. That plan must separately cover:

- removal of the failed `R.jar` merge in `tools/gen_aar_maven.py`;
- direct SettingsLib/iconloader/WindowManager-Shell/WifiTrackerLib AAR generation;
- authoritative class ownership to avoid AAR + full JAR duplicates;
- deletion of historical local Maven or prebuilt artifacts only after dependency reports prove them unused;
- `processDebugMainManifest`, core Kotlin baseline, and final `:app:assembleDebug`.

This separation prevents the source-topology checkpoint from depending on an unresolved AAR packaging design.
