# Task 040 Brief — R8 Runtime Batch 4D: SettingsLib Closure（81→7）

> **执行模式 / Authority**: `redline-gated`, self-commit, never push
> **Reports To**: main-worktree chief architect
> **必读顺序**: worker-contract → `AGENTS.md` → `docs/orchestration/CHARTER.md`
> → 本 brief → `docs/issues/2026-08-20-r8-runtime-batch4d-settingslib.md`
> → `docs/superpowers/plans/2026-08-20-r8-runtime-batch4d-settingslib.md`
> 开始工作前输出完整 `CONTRACT:` 块。

## Authority and pre-approved red-line boundary

用户已于 2026-08-20 明确批准：

- `SettingsLib` 本地 Maven AAR `1.0.0→1.0.1`；
- `SettingsLibSettingsTheme` 本地 Maven AAR `1.0.0→1.0.1`；
- 10 个指定 per-target res-owning AAR 初始 `1.0.0`；
- 主 SettingsLib POM 从 7 条扩展到 17 条真实 static dependency edges；
- 删除被主 AAR 取代的 `libs/SettingsLib-full.jar` 及其唯一 `compileOnly` 引用。

以上是本 brief 内唯一预批准的 dependency/artifact 红线。任何其他版本、模块、资源或依赖
变化必须输出 `REDLINE:` 并停止。

## Goal

把缺失的 SettingsLib program classes 和 10 个真实资源 namespace 以 owner-correct、
byte-exact、确定性的 AAR/POM 闭包交付，使 debug 保持成功，fresh R8 精确 **81→7**：
恰移除 74 个 `com.android.settingslib.*` refs，新增 0。

## Allowed Paths

### Implementation and tests

- `tools/package_aosp_aar.py`
- `tools/tests/test_package_aosp_aar.py`
- `tools/install_aar_to_maven.py`
- `tools/tests/test_install_aar_to_maven.py`
- `SystemUI-core/build.gradle.kts`（仅删除 `SettingsLib-full.jar` 注释和 compileOnly 行）
- `gradle/libs.versions.toml`（仅主/Theme 两个已批准版本及 10 个新 alias）
- `libs/SettingsLib-full.jar`（删除）

### AAR outputs

- `libs/aars/SettingsLib.aar`
- `libs/aars/SettingsLibSettingsTheme.aar`
- `libs/aars/SettingsLibMainSwitchPreference.aar`
- `libs/aars/SettingsLibAppPreference.aar`
- `libs/aars/SettingsLibBannerMessagePreference.aar`
- `libs/aars/SettingsLibBarChartPreference.aar`
- `libs/aars/SettingsLibButtonPreference.aar`
- `libs/aars/SettingsLibFooterPreference.aar`
- `libs/aars/SettingsLibIllustrationPreference.aar`
- `libs/aars/SettingsLibSliderPreference.aar`
- `libs/aars/SettingsLibUsageProgressBarPreference.aar`
- `libs/aars/SettingsLibSettingsSpinner.aar`

### Local Maven outputs

- `libs/maven/com/android/systemui/SettingsLib/`（删 `1.0.0/`，建 `1.0.1/`）
- `libs/maven/com/android/systemui/SettingsLibSettingsTheme/`（删 `1.0.0/`，建 `1.0.1/`）
- `libs/maven/com/android/systemui/SettingsLibMainSwitchPreference/`
- `libs/maven/com/android/systemui/SettingsLibAppPreference/`
- `libs/maven/com/android/systemui/SettingsLibBannerMessagePreference/`
- `libs/maven/com/android/systemui/SettingsLibBarChartPreference/`
- `libs/maven/com/android/systemui/SettingsLibButtonPreference/`
- `libs/maven/com/android/systemui/SettingsLibFooterPreference/`
- `libs/maven/com/android/systemui/SettingsLibIllustrationPreference/`
- `libs/maven/com/android/systemui/SettingsLibSliderPreference/`
- `libs/maven/com/android/systemui/SettingsLibUsageProgressBarPreference/`
- `libs/maven/com/android/systemui/SettingsLibSettingsSpinner/`

### Evidence

- `docs/issues/2026-08-20-r8-runtime-batch4d-settingslib.md`（只追加真实实施证据）

## Forbidden Paths and actions

- 所有 `SystemUI-*/src/**`、`SystemUI-*/res*/**`、AOSP 源树和 live SysUISdk
- `SystemUI-res/build.gradle.kts`、其他 build files、`settings.gradle.kts`
- `AGENTS.md`、`docs/adr/**`、`docs/orchestration/CHARTER.md`、`docs/CURRENT_STATE.md`
- 任何未列出的 `libs/aars/**`、`libs/maven/**`、JAR 或 catalog alias/version
- stub、R-only JAR、手写/生成资源、资源合并/改写、keep、dontwarn、`@Suppress`、源码排除、关闭检查
- 把 Theme 代码放进主 SettingsLib AAR，或把 10 个子 target 资源合进主 AAR
- B1–B4、`AssumeTrueForR8`、release signing/shrinkResources 后续工作
- push；worker 只做英文 focused commits

## Required execution order

1. Fresh pre-change R8，保存并机械断言 81 total / 74 SettingsLib / 7 other。
2. TDD program closure：先红；主 1153 类、Theme 15 类、零重叠；再实现和重打包。
3. TDD ten resource AARs：先红；346 个 byte-exact res、空 classes.jar；再实现和重打包。
4. TDD Maven wiring：先红；2 个 `1.0.1`、10 个 `1.0.0`、17 条 AOSP-ordered POM edges；再实现、安装和删除 full JAR。
5. 全套 tests → deterministic rebuild → serialized debug hard gate → APK 74/74 defined → fresh R8 exact delta。
6. 追加 issue 证据、`git diff --check`、英文 commits、终态 `HANDOFF:`。

## Acceptance

全部必须真实满足：

1. `python3 -m unittest discover -s tools/tests -p 'test_*.py' -v` → exit 0，179 baseline + 新测试全部 `OK`。
2. 主 AAR classes.jar = **1153** 精确 class union；Theme = **15**；二者交集 0；指定 owner classes 正确。
3. 10 个新 res-only AAR 的 source res 计数为 `22,91,96,6,23,91,6,5,1,5`，总计 **346**；逐字节一致、空 classes.jar。
4. 12 个变化/新增 AAR 两次打包 `cmp` 全部 exit 0。
5. main/Theme 只剩 `1.0.1`；10 新 target 为 `1.0.0`；主 POM 恰 17 edges，子 POM 无 dependencies；Maven AAR 与 `libs/aars` byte-identical。
6. `libs/SettingsLib-full.jar` 不存在；`rg 'SettingsLib-full.jar' --glob '!docs/**'` 无功能引用。
7. `set -o pipefail; ./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug --console=plain -Dorg.gradle.workers.max=4 | tee ...` → real Gradle exit 0、`BUILD SUCCESSFUL`。
8. pre-change 的 74 个 SettingsLib missing targets 在 debug APK 中 `DEFINED=74 MISSING=0`。
9. fresh `:app:minifyReleaseWithR8 --rerun-tasks` 预期 Gradle exit 1，但 missing set 必须：before 81、after 7、removed 恰 74 SettingsLib、added 0、after 无 SettingsLib、`AssumeTrueForR8` 保留。
10. 变更仅限 Allowed Paths；`git diff --check` 无输出；issue 记录真实命令/退出码/哈希/计数；worker 未 push。

## REDLINE conditions

以下任一出现立即停止，不尝试绕过：

- baseline 不是 81/74/7；
- ��� 1153、Theme 15、零重叠任一不成立；
- 资源 entry 不漏不多不改或 namespace owner 不成立；
- 新依赖/重复类/资源冲突导致 debug 失败；
- R8 after 不是 7、removed 不等于原 74 SettingsLib、added 非空，或浮出任何新 missing ref；
- 需要修改 Forbidden Paths、其他版本、模块边界、源文件、资源文件或构建规则；
- 所有合规方案失败。

## Completion report

成功时 terminal-final 必须输出：

```text
HANDOFF:
- done: <program/resource/Maven closure and full-JAR retirement>
- verified: <real tests, hashes, debug exit, APK 74/74, R8 81→7 evidence>
- remaining: <the seven deferred refs, or exact blocker>
```

红线时输出 `REDLINE:`，包含已验证事实、未提交 diff 状态和建议；禁止自行扩 scope。
