# ADR 0005 — 本地 Maven POM 携带传递依赖（SettingsLib 资源闭包）

## 状态

Accepted（2026-08-19，用户明确指示）

## 背景

- 此前约定（CHARTER Part 3）：`libs/maven/` 下的 POM 全部是**无依赖骨架**，Soong
  `static_libs` 传递关系在 Gradle 侧一律显式接线。
- Task 013/014 证明 SettingsLib 的完整资源闭包 = 33 个 res-owning Soong target
  （1512 文件、101 组同相对路径），无法在单一 AAR 中合规合并（规则 R）。
- 参考项目（CarSystemUIGradle）的单一合并 AAR 依赖内容改写/删除，本项目不采用。
- 用户 2026-08-19 明确指示：采用 **per-target AAR + POM 传递依赖**，本地 AAR 统一由
  `libs/maven/` 管理。

## 决策

1. `tools/install_aar_to_maven.py` 的 `ARTIFACTS` 支持可选 `deps` 字段；POM 模板按需渲染
   `<dependencies>`。**仅 SettingsLib 闭包**的 POM 携带传递边；其余 artifact 保持骨架。
2. POM 依赖边机械镜像 AOSP `Android.bp` 的 `static_libs`（含依赖 Soong 默认
   `resource_dirs=["res"]` 的 target），不凭记忆增删。
3. 每个 res-owning 子 target 一个 res-only AAR（byte-exact res + 原始 manifest + Soong
   `R.txt`），坐标 `com.android.systemui:<SoongTargetName>:1.0.0`。
4. consumer（`:SystemUI-res`）只保留 `api(libs.systemui.settingslib)`；Task 013 的显式
   `api(libs.systemui.settingslib.theme)` 改为经 POM 传递获得。
5. `gradle/libs.versions.toml` 为全部本地 AAR 保留 catalog alias 作为统一注册表
   （未被 build 文件直接引用的 alias 仅作登记）。

## 后果

- CHARTER Part 3 的"POM 是 dependency-free 骨架"表述更新为：默认骨架；SettingsLib 闭包例外，
  其 POM 边由 Android.bp 机械生成。
- consumer 接口变深（1 个依赖覆盖 33 target）；闭包增删 target 只需改打包/安装配置与 POM。
- 回滚 = 删除新增 AAR/alias/依赖边；Task 013 的 SettingsTheme AAR 原样保留。
- 其余本地 AAR（WifiTrackerLib、iconloader、WM-Shell 等）POM 不变。

## 备选

- 方案 A 单一合并 AAR：违反规则 R（参考项目实证），否决。
- 方案 C per-target + consumer 显式依赖：研究推荐，但用户选择 B；B 的接口深度更优，
  代价（POM 语义升级）由本 ADR 显式接受。
