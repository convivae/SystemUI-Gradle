# Post-Topology Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 修复 13-module 审查中不需要产品裁决的确定问题，使 common/compose/plugin 隔离编译得到可信结果，并把 core 推进到新的第一真实 blocker。

**Architecture:** 保持现有 13-module 边界和 AOSP 源码/res 字节不变，只修复 Gradle classpath、官方 Maven 依赖和 Python 验证工具。Plugin processor 的 Kotlin 标注处理以及四个大型 AOSP AAR 的恢复不在本计划中；本计划完成后用新的 first-failure 证据编写独立 artifact-recovery 计划。

**Tech Stack:** Python 3 `unittest`/`zipfile`、Gradle 9.5、AGP 9.2、Kotlin 2.1/AGP embedded compiler、JDK 21、SysUISdk、AndroidX Maven artifacts。

## Global Constraints

- 用户明确指令优先于本计划；冲突时停止并询问用户。
- 禁止创建 Java/Kotlin stub，禁止恢复 `PluginProtectorStub.kt`。
- 禁止修改、生成或重写任何 AOSP SystemUI `res/` 文件。
- SystemUI 源码/AIDL/res 必须继续与 AOSP owner 和字节内容对齐。
- 非 SystemUI 代码不得源码复制；AndroidX 依赖必须使用官方 Maven 坐标。
- 不使用 KAPT；本计划不重写 `ProtectedPluginProcessor` 为 KSP。
- 不修改 `libs/maven/`，不运行 `tools/gen_aar_maven.py`。
- 不把 `framework.jar` 注入 KotlinCompile 全局 classpath。
- 错误数只作诊断；任何失败都记录首个 task 和完整错误，不修改 AOSP 源码来掩盖。
- 每个 Task 开始前确认 `git status --short`，不得覆盖其他人的未提交修改。
- 执行环境应使用隔离 worktree；若使用当前目录，先取得用户授权。

---

### Task 1: Fix Multi-Root Source Alignment False Negatives

**Files:**
- Modify: `tools/check_source_alignment.py:226-244`
- Modify: `tools/tests/test_check_source_alignment.py`
- Modify: `docs/issues/2026-08-07-post-topology-review.md`

**Interfaces:**
- Consumes: `run_source_check(mappings, aosp_root, project_root, suffixes)` 与 `build_aosp_index(...)`。
- Produces: 对同一 relative tail 的每个合法物理 source root 独立检查；合法 release 副本不能掩盖缺失的 debug 副本。

- [ ] **Step 1: Add the failing duplicate-tail test**

在 `tools/tests/test_check_source_alignment.py` 末尾新增：

```python
class TestDuplicateTailAcrossExpectedRoots(unittest.TestCase):
    def test_missing_one_of_two_valid_roots_is_reported(self):
        mappings = [
            csa.M(["src-debug"], "Core", "src-debug"),
            csa.M(["src-release"], "Core", "src-release"),
        ]
        tail = Path("com/android/systemui/flags/FlagsFactory.kt")
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            aosp = root / "aosp"
            project = root / "project"
            for variant, body in (("src-debug", b"debug"), ("src-release", b"release")):
                path = aosp / variant / tail
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(body)
            release = project / "Core/src-release" / tail
            release.parent.mkdir(parents=True, exist_ok=True)
            release.write_bytes(b"release")

            result = csa.run_source_check(mappings, aosp, project)

            self.assertEqual([item[3] for item in result["missing"]], [str(tail)])
            self.assertEqual(result["misplaced"], [])
            self.assertEqual(result["extra"], [])
```

- [ ] **Step 2: Run the test and confirm the current false negative**

Run:

```bash
python3 -m unittest \
  tools.tests.test_check_source_alignment.TestDuplicateTailAcrossExpectedRoots -v
```

Expected: FAIL because `result["missing"]` is empty.

- [ ] **Step 3: Restrict missing suppression to genuinely misplaced locations**

在 `run_source_check()` 中，把“只要别处存在就跳过”的逻辑改为按该 tail 的合法 owner 集合判断：

```python
expected_locs = {
    (module, src_root)
    for module, src_root, _aosp_sub in aosp_idx.get(tail, [])
}
misplaced_elsewhere = [
    (module, src_root)
    for module, src_root, _path in find_tail_locations(
        tail, mappings, project_root, suffixes
    )
    if (module, src_root) not in expected_locs
]
if misplaced_elsewhere:
    continue  # 由错误位置所属映射的 extra 阶段报告 MISPLACED
missing.append((m.aosp_subdirs[0], m.project_module,
                m.project_src_root, tail, m.note))
```

不要把合法的另一个 expected root 当成 misplaced，也不要改变字节级 MODIFIED 判断。

- [ ] **Step 4: Run focused and full alignment tests**

Run:

```bash
python3 -m unittest tools.tests.test_check_source_alignment -v
python3 tools/check_source_alignment.py --strict
```

Expected: tests PASS；当前真实项目 strict exit 0。

- [ ] **Step 5: Record and commit**

在 review issue 的 Phase A 记录测试命令和结果，然后：

```bash
git add tools/check_source_alignment.py \
  tools/tests/test_check_source_alignment.py \
  docs/issues/2026-08-07-post-topology-review.md
git commit -m "fix: validate duplicate source tails per root"
```

---

### Task 2: Make Generated AAR and JAR Artifacts Byte-Deterministic

**Files:**
- Modify: `tools/package_aosp_aar.py`
- Modify: `tools/package_compilelib_jars.py`
- Modify: `tools/tests/test_package_aosp_aar.py`
- Create: `tools/tests/test_package_compilelib_jars.py`
- Regenerate: `libs/aars/animationlib.aar`
- Regenerate: `libs/compilelib-debug.jar`
- Regenerate: `libs/compilelib-release.jar`
- Modify: `docs/issues/2026-08-07-post-topology-review.md`

**Interfaces:**
- Consumes: existing AOSP Soong code JARs/resources and compilelib Java files.
- Produces: identical bytes and SHA-256 when the same input is packaged twice.

- [ ] **Step 1: Add a failing deterministic AAR test**

在 `TestAssembleAar` 中复用临时输入，连续调用两次 `assemble_aar(...)`，并断言：

```python
self.assertEqual(first.read_bytes(), second.read_bytes())
```

两个输出之间暂停至少 2 秒，确保当前 ZIP timestamp 行为会暴露：

```python
import time
# ... first assemble
time.sleep(2)
# ... second assemble
```

Run:

```bash
python3 -m unittest \
  tools.tests.test_package_aosp_aar.TestAssembleAar.test_repeated_builds_are_byte_identical -v
```

Expected: FAIL，两个 AAR bytes 不同。

- [ ] **Step 2: Add a failing deterministic compilelib JAR test**

创建 `tools/tests/test_package_compilelib_jars.py`，动态导入脚本并使用临时 `Compile.java`：

```python
class TestCompilelibJarDeterminism(unittest.TestCase):
    def test_repeated_builds_are_byte_identical(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            src = root / "Compile.java"
            src.write_text(
                "package com.android.systemui.util; "
                "public final class Compile { public static final boolean IS_DEBUG = true; }",
                encoding="utf-8",
            )
            first = root / "first.jar"
            second = root / "second.jar"
            module._compile_one(src, first)
            time.sleep(2)
            module._compile_one(src, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
```

Run:

```bash
python3 -m unittest tools.tests.test_package_compilelib_jars -v
```

Expected: FAIL。

- [ ] **Step 3: Introduce one normalized ZIP entry writer in each focused script**

两个脚本都使用以下固定 metadata；不要依赖输入 JAR 的原始 timestamp：

```python
FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    archive.writestr(_zip_info(name), data)
```

将所有 `writestr(info, data)` 和 `writestr(name, data)` 替换为 `_write_entry(...)`。保持：

- entry 名排序；
- 重复 entry 检测；
- R.class 拒绝；
- res/ 与 manifest/R.txt 内容字节不变。

- [ ] **Step 4: Run packaging tests**

Run:

```bash
python3 -m unittest \
  tools.tests.test_package_aosp_aar \
  tools.tests.test_package_compilelib_jars -v
python3 -m py_compile \
  tools/package_aosp_aar.py \
  tools/package_compilelib_jars.py \
  tools/tests/test_package_aosp_aar.py \
  tools/tests/test_package_compilelib_jars.py
```

Expected: all PASS。

- [ ] **Step 5: Regenerate tracked artifacts and prove reproducibility**

Run:

```bash
python3 tools/package_aosp_aar.py animationlib --output libs/aars/animationlib.aar
python3 tools/package_compilelib_jars.py
sha256sum libs/aars/animationlib.aar \
  libs/compilelib-debug.jar libs/compilelib-release.jar > /tmp/artifacts.first.sha256
sleep 2
python3 tools/package_aosp_aar.py animationlib --output libs/aars/animationlib.aar
python3 tools/package_compilelib_jars.py
sha256sum libs/aars/animationlib.aar \
  libs/compilelib-debug.jar libs/compilelib-release.jar > /tmp/artifacts.second.sha256
diff -u /tmp/artifacts.first.sha256 /tmp/artifacts.second.sha256
unzip -t libs/aars/animationlib.aar
unzip -t libs/compilelib-debug.jar
unzip -t libs/compilelib-release.jar
```

Expected: hash diff 无输出；三个 archive integrity check 通过。

- [ ] **Step 6: Record and commit**

```bash
git add tools/package_aosp_aar.py tools/package_compilelib_jars.py \
  tools/tests/test_package_aosp_aar.py \
  tools/tests/test_package_compilelib_jars.py \
  libs/aars/animationlib.aar \
  libs/compilelib-debug.jar libs/compilelib-release.jar \
  docs/issues/2026-08-07-post-topology-review.md
git commit -m "fix: make packaged AOSP artifacts deterministic"
```

---

### Task 3: Give the JVM Common Module the SysUISdk Compile API

**Files:**
- Modify: `SystemUI-common/build.gradle.kts:24-36`
- Modify: `docs/issues/2026-08-07-post-topology-review.md`

**Interfaces:**
- Consumes: `${ANDROID_HOME}/platforms/android-SysUISdk/android.jar` and existing `framework.jar`.
- Produces: JVM `:SystemUI-common` can resolve `android.icu.text.SimpleDateFormat` without becoming an Android library.

- [ ] **Step 1: Verify the required class provenance**

Run:

```bash
SDK_JAR="${ANDROID_HOME:-/home/conv/Android/Sdk}/platforms/android-SysUISdk/android.jar"
test -f "$SDK_JAR"
unzip -l "$SDK_JAR" | grep 'android/icu/text/SimpleDateFormat.class'
if unzip -l libs/framework.jar | grep -q 'android/icu/text/SimpleDateFormat.class'; then
  echo 'unexpected: framework.jar contains android.icu SimpleDateFormat' >&2
  exit 1
fi
```

Expected: class exists only in SysUISdk android.jar。

- [ ] **Step 2: Capture the red compile result**

Run:

```bash
./gradlew :SystemUI-common:compileKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/common-before-sysuisdk.log
```

Expected: non-zero with unresolved `android.icu` / `SimpleDateFormat`。

- [ ] **Step 3: Add a module-local compileOnly SysUISdk android.jar**

在 `SystemUI-common/build.gradle.kts` 顶层定义：

```kotlin
val sysUiSdkDir = providers.environmentVariable("ANDROID_HOME")
    .orElse("/home/conv/Android/Sdk")
val sysUiAndroidJar = sysUiSdkDir.map {
    "$it/platforms/android-SysUISdk/android.jar"
}
```

在 `dependencies` 中加入：

```kotlin
compileOnly(files(sysUiAndroidJar))
```

保留现有 `framework.jar` module dependency；不要修改 root `KotlinCompile` classpath，不要把 Common 改成 Android library。

- [ ] **Step 4: Compile Common**

Run:

```bash
./gradlew :SystemUI-common:compileKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/common-after-sysuisdk.log
```

Expected: `:SystemUI-common:compileKotlin` exit 0。若出现新的 duplicate/conflicting Android class 错误，停止 Task，保留日志并询问用户是否改为用 SysUISdk android.jar 替换 module-local framework.jar；不要擅自切换 module 类型。

- [ ] **Step 5: Record and commit**

```bash
git add SystemUI-common/build.gradle.kts \
  docs/issues/2026-08-07-post-topology-review.md
git commit -m "build: expose SysUISdk APIs to SystemUI common"
```

---

### Task 4: Restore the Correct Core Animation Dependency to Compose

**Files:**
- Modify: `gradle/libs.versions.toml`
- Modify: `SystemUI-compose/build.gradle.kts:59-80`
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/issues/2026-08-06-module-consolidation-plan.md`
- Modify: `docs/issues/2026-08-07-post-topology-review.md`

**Interfaces:**
- Consumes: official Maven artifact `androidx.core:core-animation:1.0.0`.
- Produces: `androidx.core.animation.Interpolator` is directly visible to `:SystemUI-compose`.

- [ ] **Step 1: Confirm the artifact contains the required class**

Run:

```bash
./gradlew :SystemUI-animation:dependencies \
  --configuration debugCompileClasspath --console=plain \
  2>&1 | tee /tmp/animation-deps.log
grep 'androidx.core:core-animation:1.0.0' /tmp/animation-deps.log
```

Expected: dependency is already resolved for animation, proving the official artifact/version is available。

- [ ] **Step 2: Capture the red Compose compile result**

Run:

```bash
./gradlew :SystemUI-compose:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/compose-before-core-animation.log
```

Expected: non-zero with unresolved/inaccessible `androidx.core.animation.Interpolator`。

- [ ] **Step 3: Add the version-catalog entry and direct dependency**

在 `gradle/libs.versions.toml` 增加：

```toml
androidx-core-animation = { module = "androidx.core:core-animation", version = "1.0.0" }
```

在 `SystemUI-compose/build.gradle.kts` 的 AndroidX 依赖中增加：

```kotlin
implementation(libs.androidx.core.animation)
```

保留 `core-ktx`；不要改 `Easings.kt` 源码。

- [ ] **Step 4: Compile Compose and inspect dependency resolution**

Run:

```bash
./gradlew :SystemUI-compose:dependencies \
  --configuration debugCompileClasspath --console=plain \
  | grep 'androidx.core:core-animation'
./gradlew :SystemUI-compose:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/compose-after-core-animation.log
```

Expected: classpath 包含 `core-animation:1.0.0`，Compose compile exit 0 或推进到一个新的、与 Interpolator 不同的真实错误。若出现新错误，原样记录，不修改 AOSP Compose 源码。

- [ ] **Step 5: Correct all active documentation**

把 active state/handoff/issue 中的“缺 `androidx.core:core`”统一改为“缺 `androidx.core:core-animation:1.0.0`”，并写入本次实际编译结果。

- [ ] **Step 6: Commit**

```bash
git add gradle/libs.versions.toml SystemUI-compose/build.gradle.kts \
  docs/CURRENT_STATE.md docs/HANDOFF.md \
  docs/issues/2026-08-06-module-consolidation-plan.md \
  docs/issues/2026-08-07-post-topology-review.md
git commit -m "build: add Compose core animation dependency"
```

---

### Task 5: Restore Plugin Compose Runtime Dependency

**Files:**
- Modify: `SystemUI-plugin/build.gradle.kts:52-71`
- Modify: `docs/issues/2026-08-07-post-topology-review.md`

**Interfaces:**
- Consumes: official Maven artifact `androidx.compose.runtime:runtime:1.8.3`.
- Produces: `TileDetailsViewModel.kt` can resolve `androidx.compose.runtime.Composable`; processor behavior remains unchanged.

- [ ] **Step 1: Prove the runtime is currently absent**

Run:

```bash
./gradlew :SystemUI-plugin:dependencies \
  --configuration debugCompileClasspath --console=plain \
  2>&1 | tee /tmp/plugin-deps-before-runtime.log
if grep -q 'androidx.compose.runtime:runtime' /tmp/plugin-deps-before-runtime.log; then
  echo 'unexpected: Compose runtime already present' >&2
  exit 1
fi
```

Expected: grep 找不到 Compose runtime。

- [ ] **Step 2: Add the direct runtime dependency**

在 Plugin 的 AndroidX 依赖区加入：

```kotlin
implementation("androidx.compose.runtime:runtime:1.8.3")
```

不要加入 KAPT、不要修改 processor 源码、不要生成 `PluginProtector` 副本。

- [ ] **Step 3: Verify classpath and compile Plugin**

Run:

```bash
./gradlew :SystemUI-plugin:dependencies \
  --configuration debugCompileClasspath --console=plain \
  | grep 'androidx.compose.runtime:runtime'
./gradlew :SystemUI-plugin:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/plugin-after-runtime.log
```

Expected: classpath 包含 runtime；Plugin Kotlin compile exit 0。processor 仍不会看到 Kotlin annotations，这不是本 Task 的失败。

- [ ] **Step 4: Confirm no fake generated output or stub appeared**

Run:

```bash
! test -e SystemUI-plugin/src/com/android/systemui/plugins/PluginProtectorStub.kt
find SystemUI-plugin/build/generated -type f -name 'PluginProtector.java' -print
```

Expected: stub 不存在；当前 javac-only processor 仍不生成 `PluginProtector.java`。

- [ ] **Step 5: Record and commit**

```bash
git add SystemUI-plugin/build.gradle.kts \
  docs/issues/2026-08-07-post-topology-review.md
git commit -m "build: restore plugin Compose runtime"
```

---

### Task 6: Establish the Post-Topology Build Boundary and Handoff

**Files:**
- Modify: `docs/issues/2026-08-07-post-topology-review.md`
- Modify: `docs/CURRENT_STATE.md`
- Modify: `docs/HANDOFF.md`
- Modify: `docs/PLAN.md`
- Modify: this plan's checkboxes/results

**Interfaces:**
- Consumes: Tasks 1–5 and unchanged 13-module graph.
- Produces: verified isolated compile results, the actual first core blocker, and an accurate handoff for the artifact-recovery phase.

- [ ] **Step 1: Run all Python verification**

Run:

```bash
python3 -m py_compile tools/*.py tools/tests/*.py
python3 -m unittest discover -s tools/tests -v
python3 tools/check_source_alignment.py --strict
```

Expected: all exit 0；source/res counts remain zero。

- [ ] **Step 2: Reassert the 13-module graph**

Run:

```bash
./gradlew projects --console=plain
python3 - <<'PY'
from pathlib import Path
import re
mods = re.findall(r'include\("(:[^"]+)"\)', Path("settings.gradle.kts").read_text())
expected = [
    ":app", ":SystemUI-core", ":SystemUI-res", ":SystemUI-common",
    ":SystemUI-animation", ":SystemUI-plugin-core",
    ":SystemUI-plugin-processor", ":SystemUI-plugin", ":SystemUI-unfold",
    ":SystemUI-customization", ":SystemUI-shared",
    ":SystemUI-shared-biometrics", ":SystemUI-compose",
]
assert mods == expected, (mods, expected)
print("13-module settings graph: PASS")
PY
```

Expected: Gradle configuration and assertion pass。

- [ ] **Step 3: Run isolated compile evidence**

Run each command separately so failures are attributable：

```bash
./gradlew :SystemUI-common:compileKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/post-topology-common.log
./gradlew :SystemUI-compose:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/post-topology-compose.log
./gradlew :SystemUI-plugin:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/post-topology-plugin.log
./gradlew :SystemUI-shared:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/post-topology-shared.log
```

Expected:

- Common 不再报 android.icu；
- Compose 不再报 `androidx.core.animation.Interpolator`；
- Plugin 不再报缺 `Composable`；
- Shared 很可能推进到 `PluginProtector` 或其他新的真实错误。

任何新错误都记录首个 failing task 和首个完整异常，不新增 stub。

- [ ] **Step 4: Capture core's new first boundary**

Run:

```bash
./gradlew :SystemUI-core:compileDebugKotlin --rerun-tasks --console=plain \
  2>&1 | tee /tmp/systemui-core-post-topology-correctness.log
```

Expected: 命令可能失败；本步骤的成功标准是日志明确显示修复后的第一真实 blocker。若进入 AAR transform duplicate-R，则记录具体 artifact、task 和 duplicate class；若先到 `PluginProtector`，按规则 H 停止并询问用户。

- [ ] **Step 5: Audit active prebuilt/source duplicate classes before artifact recovery**

运行一个只读 Python 扫描，至少确认 `libs/WindowManager-Shell.jar` 与 `:SystemUI-animation` 的重叠类数量和样例，并把输出写入 review issue。扫描不得修改 JAR/AAR。

同时记录以下现存 artifact 消费位置：

```bash
rg -n 'WindowManager-Shell\.jar|systemui\.(settingslib|iconloader|wmshell|wifitrackerlib)' \
  --glob '*.kts' .
```

- [ ] **Step 6: Rewrite active handoff sections to current facts**

更新文档时必须：

- HANDOFF 的 libs/tree 删除已不存在的 `animationlib.jar`；
- HANDOFF 的 core tree 不再列已迁出的 `res*`；
- 把“Task 1–10 全部完成”改成“拓扑迁移完成，功能验收部分完成”；
- 写入 Tasks 1–5 的实际命令和结果；
- 写入 core 新的 first blocker；
- 明确 PluginProtector 仍需用户裁决；
- 把下一计划命名为 `docs/superpowers/plans/2026-08-07-aosp-artifact-recovery.md`；
- 如本轮未运行 `:app:assembleDebug`，明确写“未运行”。

- [ ] **Step 7: Verify documentation and commit checkpoint**

Run:

```bash
rg -n '缺 `androidx.core:core`|animationlib\.jar|资源待迁出|拓扑实施中' \
  docs/HANDOFF.md docs/CURRENT_STATE.md docs/PLAN.md
git diff --check
git status --short
```

Expected: active 文档不再包含这些错误状态；`git diff --check` 通过。

Commit:

```bash
git add docs/issues/2026-08-07-post-topology-review.md \
  docs/CURRENT_STATE.md docs/HANDOFF.md docs/PLAN.md \
  docs/superpowers/plans/2026-08-07-post-topology-correctness.md
git commit -m "docs: record post-topology build boundary"
```

---

## Out of Scope and Mandatory Follow-Up

本计划完成后，按实际 core first-failure 校准并执行：

```text
docs/superpowers/plans/2026-08-07-aosp-artifact-recovery.md
```

该计划逐个处理 SettingsLib、iconloader、WindowManager-Shell、WifiTrackerLib，遵循“直接 AAR 先验证；确认冲突后才用本地 Maven”，并包含源码/prebuilt 重复类检查。执行前必须用 Phase A 新证据更新其 baseline；不得在没有该证据时批量重打四个 artifact。

Plugin processor 不纳入 artifact-recovery。遇到 `PluginProtector` 时必须询问用户是否授权 KSP 等价实现；在此之前继续保持显式 blocker。

最终成功证据只能是：

```bash
./gradlew :app:assembleDebug --console=plain
```

exit 0 且实际 APK 文件存在。
