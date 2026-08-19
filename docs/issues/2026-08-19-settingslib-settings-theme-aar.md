# Task 013 — SettingsLibSettingsTheme AAR 资源闭包

## 背景

Task 012 已将 AGP `androidprv` namespace 错误从 20 降至 0。当前
`:app:processDebugResources` 首个失败层为：

```text
resource drawable/settingslib_switch_track not found
resource drawable/settingslib_switch_thumb not found
```

两个资源来自 AOSP：

- `frameworks/base/packages/SettingsLib/SettingsTheme/res/drawable-v31/settingslib_switch_track.xml`
- `frameworks/base/packages/SettingsLib/SettingsTheme/res/drawable-v31/settingslib_switch_thumb.xml`
- `settingslib_switch_track` 另有 `drawable-v34` 变体

`SettingsLibSettingsTheme` 是真实 Soong `android_library`，定义于
`SettingsLib/SettingsTheme/Android.bp`。多个 SettingsLib 子模块通过
`static_libs` 消费它；SystemUI 自有 `res/values/styles.xml` 也引用上述 drawable。

## 根因与方案

当前 `libs/aars/SettingsLib.aar` 只打包 `SettingsLib/res`。不能把
`SettingsTheme/res` 直接作为第二个 raw resource root 合并进同一 AAR：两棵树有
89 个同相对路径 XML（主要是 values locale 文件），现有严格打包器会正确拒绝；
覆盖或自行合并 XML 会破坏原始 AOSP 资源字节和规则 R。

采用与 Soong target 一致的独立 res-only AAR：

- artifact：`SettingsLibSettingsTheme`
- group/name/version：`com.android.systemui:SettingsLibSettingsTheme:1.0.0`
- raw res：完整复制 `SettingsLib/SettingsTheme/res`，不修改字节
- manifest：原始 `SettingsTheme/AndroidManifest.xml`
- R.txt：Soong `SettingsLibSettingsTheme/android_common/R.txt`
- consumer：`:SystemUI-res` 使用 catalog alias 显式 `api(...)`

这是 tier ② AOSP 含资源产物；不存在对应的未 fork 公网 Maven 产物。沿用已确认存在资源依赖冲突后的本地 Maven AAR 交付机制，不引入新版本。

## 用户授权

用户于 2026-08-19 明确批准继续重新打包 SettingsLib/SettingsTheme 资源。该授权覆盖：

- 新增上述 AOSP AAR 和本地 Maven AAR/POM；
- 在 version catalog 新增固定 `1.0.0` alias（不升级任何版本）；
- 在 `SystemUI-res/build.gradle.kts` 增加资源依赖；
- 不授权修改任何 `SystemUI-*/res*/**` 或 AOSP 源文件。

## 实施步骤

1. TDD：先为 config、完整文件集、字节一致性、Maven 注册写失败测试。
2. 在 `tools/package_aosp_aar.py` 注册 res-only `SettingsLibSettingsTheme`。
3. 在 `tools/install_aar_to_maven.py` 注册固定本地坐标。
4. 生成并提交 direct AAR 与 local Maven AAR/POM。
5. 新增 catalog alias，并从 `:SystemUI-res` 显式接入。
6. 运行全部 Python tests、artifact provenance 校验及 clean resource link。
7. 若 resource link 通过，运行 `:app:assembleDebug`；若暴露新层，只记录首个失败任务和首批错误，不扩大 Task 013 范围。

## 验收

- Python tests 全部 `OK`，数量大于 131。
- AAR 中 `res/**` 文件集与 AOSP SettingsTheme `res/**` 完全一致，逐文件字节一致。
- direct AAR 和 local Maven AAR SHA-256 相同。
- `:app:processDebugResources` 不再报告两个 `settingslib_switch_*` 缺失；目标为命令 exit 0 且输出含 `BUILD SUCCESSFUL`。
- 没有修改任何 `SystemUI-*/src/**`、`SystemUI-*/res*/**`、AOSP 文件、版本号或模块边界。

## 错误数演变

| 检查点 | 结果 |
|---|---|
| Task 012 后 | androidprv 0；SettingsLib switch drawable 缺失 2 类 |
| Task 013 后 | 待执行 |

## 待解决问题

- Task 013 完成后按真实 `:app:assembleDebug` 输出决定下一层；不得预判 APK 已生成。
