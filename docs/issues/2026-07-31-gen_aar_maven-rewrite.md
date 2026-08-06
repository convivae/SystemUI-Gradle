# gen_aar_maven.py 改写：修复 aar 无 R 类根因

> **2026-08-06 更正（重要）**：本文最初的根因判断不成立。AGP 会根据 prebuilt AAR 的 `res/` 和 `R.txt` 为依赖生成 R API；把 `busybox/R.jar` 再合入 AAR 的 `classes.jar` 会与 AGP transform 生成的 R 类重复，当前实际报错为 `already contains entry '.../R.class'`。因此本文和对应脚本应视为**失败实验/待回滚中间态**，不能作为最终方案。保留本文是为了记录为何当前 checkpoint 暂时无法构建；下一步应撤销 R 合并逻辑，恢复直接 AAR，并单独诊断原始 R 可见性问题。

**日期**: 2026-08-03
**关联**: 桶 #1 `Unresolved reference 'R'`（~30 错误，占当前 78 错误的 ~38%）

---

## 1. 背景

当前 `:SystemUI-core:compileDebugKotlin` 78 个错误，其中最大一桶是 `Unresolved reference 'R'`，集中在 20 个 `import com.android.settingslib.R` 的源文件（AOSP 原样如此 import）。

排查发现 `libs/maven/.../SettingsLib-1.0.0.aar` 的 `classes.jar` **不含任何 `com.android.settingslib.R` 类**：
```
$ unzip -l classes.jar | grep "settingslib/R"
(empty)
```
AGP 消费 prebuilt aar 时不会替上游生成 R 类 → 消费方 `import com.android.settingslib.R` 找不到符号 → unresolved。

## 2. 根因（双重）

### 2.1 脚本照抄参考项目，未适配本项目

`tools/gen_aar_maven.py` 与 `CarSystemUIGradle/tools/gen_aar_maven.py` **只差一行 `AOSP_ROOT`**，其余 100% 相同：

- `AAR_CONFIGS` 里 5 个 `car-ui-lib` / `car-uxr-client-lib` / `car-assist-client-lib` / `CarNotificationLib` / `car-qc-lib` 配置全是 Car 项目专用，本项目根本不消费。
- Car 项目消费方不写 `import com.android.settingslib.R`，所以 aar 无 R 类不影响它；**本项目 SystemUI 源码 AOSP 原样有 20 处**这么 import，必须 aar 含 R 类。

### 2.2 clean_jar() 主动删除 R.class

脚本 `clean_jar()` 第 311-314 行：
```python
for r_class in extract_dir.rglob("R.class"):
    r_class.unlink()
for r_inner in extract_dir.rglob("R$*.class"):
    r_inner.unlink()
```
即便源 jar 含 R 类也会被删掉。

### 2.3 源 jar 选错（javac.jar 不含 R 类）

`find_jar_source()` 优先取 `combined/{name}.jar`，次取 `javac/{name}.jar`。但 AOSP soong 把 R 类生成在 **`busybox/R.jar`**，`javac/SettingsLib.jar` 本就不含 R 类：

```
frameworks/base/packages/SettingsLib/SettingsLib/android_common/
├── javac/SettingsLib.jar        ← 不含 R 类
├── turbine-combined/SettingsLib.jar ← 不含 R 类
└── busybox/R.jar                ← 15 个 com.android.settingslib.R*.class 在这
```

四份保留 aar 的 `busybox/R.jar` 全部存在（已验证）：
- `frameworks/base/packages/SettingsLib/SettingsLib`
- `frameworks/libs/systemui/iconloaderlib/iconloader`
- `frameworks/base/libs/WindowManager/Shell/WindowManager-Shell`
- `frameworks/opt/net/wifi/libs/WifiTrackerLib/WifiTrackerLib`

## 3. 改写方案

| 项 | 旧 | 新 |
|----|----|-----|
| `AAR_CONFIGS` | 9 个（4 本项目 + 5 car-*） | 4 个（删 5 car-*） |
| `find_jar_source` | 仅返回 `combined`/`javac` jar | 返回主 jar + 单独取 `busybox/R.jar` |
| `clean_jar` | 删 `R.class` / `R$*.class` | **保留** R 类；合并 `busybox/R.jar` 的 R 类进 `classes.jar` |
| 其余（res 合并、去重、COMMON_PACKAGES_TO_REMOVE、maven 安装、POM 生成） | — | 不变 |

## 4. 验证

- 改写后跑脚本，验证每个 aar 的 `classes.jar` 含本 namespace 的 `R.class` + `R$*.class`。
- 跑 `./gradlew :SystemUI-core:compileDebugKotlin`，确认桶 #1 的 `Unresolved reference 'R'`（settingslib）清零，错误数从 78 下降。
- 同步删 `libs/maven` 里残留的 car-* 产物（如有）。

## 5. 风险

- **iconloader / WindowManager-Shell / WifiTrackerLib 消费方目前没报 R unresolved**：说明这些 aar 此前即使无 R 类也没被消费 R（可能消费方写的是全限定 `com.android.systemui.R` 而非 aar 的 namespace）。补上 R 类是"恢复 AOSP 正确形态"，不会引入新错误（R 类只是补齐字段可见性）。
- **COMMON_PACKAGES_TO_REMOVE 保留**：仍删 androidx/kotlin/dagger 等（防止与 maven 版本依赖重复），不影响 R 类（R 类在 `com/android/<lib>/R`，不在删除列表）。
