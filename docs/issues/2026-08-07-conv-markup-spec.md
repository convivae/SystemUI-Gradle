# CONV 标记规范（AOSP 源码改动追溯）

**日期**：2026-08-07
**状态**：已确定（经 grilling 对齐）
**关联 ADR**：[0004](../adr/0004-conv-markup-and-alignment-discipline.md)

## 背景

core 编译首个失败为 `:SystemUI-res:packageDebugResources`——AOSP `res-product/values/strings.xml` 用 `product="tv"`/`product="default"` 属性区分设备变体，Soong 理解但 AAPT2 不支持，把多变体当 default 重复（`Found item ... more than one time`，涉及 ~40 个 locale 目录）。

参考项目 `CarSystemUIGradle` 用 Python regex 直接删除非 default 变体。用户要求本项目：① 改动可追溯可撤回；② 不直接删除，用注释包裹；③ 打标记。经 grilling 对齐后确定本规范。

## 标记规范

### 操作符

| 操作符 | 语义 | 实现 |
|--------|------|------|
| `CONV_ADD` | 新增本项目定制代码 | 直接写新行，BEGIN/END 块包裹 |
| `CONV_DEL` | 删除（注释掉）AOSP 原行 | 原行用注释语法包裹，不删字节 |
| `CONV_MOD` | 修改 AOSP 原行 | 原行注释掉 + 写新行 |

固定格式：`CONV_XXX BEGIN: reason` / `CONV_XXX END`。

### kt/java 语法（`//` 默认，`/* */` 可选）

```kotlin
// CONV_ADD BEGIN: 新增定制逻辑
val customFoo = CustomBar()
// CONV_ADD END

// CONV_MOD BEGIN: 把 private 改为 internal，Gradle Dagger 可见性
// private val foo: Bar = ...
val foo: Bar = ...
// CONV_MOD END

// CONV_DEL BEGIN: 移除废弃字段
// val deprecated: String = "x"
// CONV_DEL END
```

MOD 注释原行默认 `//` 行注释（撤回删整行最干净）；原行很长或多行可选 `/* */` 块注释。

### XML 语法（必须 `<!-- -->`，不能 `<! ...>`）

```xml
<!-- CONV_ADD BEGIN: 新增产品定制资源 -->
<string name="custom_string">...</string>
<!-- CONV_ADD END -->

<!-- CONV_MOD BEGIN: 私有样式改公开 -->
<!-- <style name="Foo" parent="@*android:style/Bar"/> -->
<style name="Foo" parent="@android:style/Bar"/>
<!-- CONV_MOD END -->

<!-- CONV_DEL BEGIN: 移除 tv 变体，AAPT2 不支持 product 属性 -->
<!-- <string name="x" product="tv">...</string> -->
<!-- CONV_DEL END -->
```

**关键约束**：XML 注释必须 `<!-- ... -->`。`<!CONV_ADD...>` 会让 AAPT2 严格解析器报 `not well-formed`（已实测验证）。BEGIN 标记行、被注释原行、END 标记行是三个独立 `<!-- -->` 注释，AAPT2 全部当注释忽略。

### reason 字段

- `BEGIN` 行唯一可选字段，**非必填**
- `END` 行**不带 reason**
- 关联 issue/ADR 时写进 reason 文字（如 `// CONV_MOD BEGIN: 修 dagger 可见性，见 docs/issues/...`）

## 豁免范围（不打标记）

| 项 | 理由 |
|----|------|
| import 语句 | 配置非逻辑，写注释反而乱 |
| package 声明 | 文件级声明，属配置 |
| 文件级注解（`@file:JvmName` 等） | 文件级元数据，属配置 |
| 整文件自写 | 无 AOSP 对照，打标无意义 |
| Gradle 文件（`*.kts`/`*.toml`/settings/properties） | 非 AOSP 源码 |

**"整文件自写"判定**：以"该文件在 AOSP 对应目录是否存在"为唯一依据（用 `check_source_alignment.py` AOSP 镜像路径判定），不靠主观判断。

## 顺序铁律

必须先跑 `check_source_alignment.py` 达全模块 **MISSING/MISPLACED/EXTRA 全 0**，确认"不漏不多不错位"后，才允许动 AOSP 源码打 CONV 标记。绝不在对齐未干净时边改边对齐（否则"漏/多/错位"与"授权改动"混淆，后期无法维护）。

## 工具职责

`check_source_alignment.py --strict` 只卡 **MISSING/MISPLACED/EXTRA**，不卡 MODIFIED：
- MODIFIED 仍报告（列文件清单），不影响 exit code
- "是否擅改"靠人工对账：MODIFIED 清单 ↔ issue CONV 记录逐条核对
- 无 CONV 标记的字节改动 = 违规擅改，必须回滚

## 规则 R 受控出口

规则 R 由"禁止擅改 res"细化为"**禁止无 CONV 标记地擅改 res/src**"。带 CONV 标记的改动是受控例外。

## 整文件自写需审核

原则上不创建新代码/资源文件（所有文件应来自 AOSP）。确需创建（非 Gradle 文件）时须放特定路径 + 用户审核。Gradle 文件不受此约束。

## 嵌套边界（已知约束）

XML 注释不能含 `--`、不能嵌套 `<!-- -->`；kt/java 的 `/* */` 不能嵌套。遇到需注释掉已含注释的原码时，按规则 H 停止并询问用户。

## 首个应用案例：product variant

阶段二将用 Python 脚本（符合 ADR 0002）批量给 `res-product/` 下非 default product 变体加 CONV_DEL 块，注释掉 `product="tv"`/`product="tablet"`/`product="device"` 的 string，保留 `product="default"`。

## 待办

- [x] ADR 0004 已写
- [x] 本 issue 已写
- [x] 改 `check_source_alignment.py`：strict 不卡 MODIFIED（两处）
- [x] 改 `test_check_source_alignment.py`：加 MODIFIED 不卡 strict 测试
- [x] 更新 AGENTS.md 规则 R 措辞 + 引用 ADR 0004
- [x] 更新 HANDOFF / CURRENT_STATE 引用 ADR 0004
- [x] 跑对齐确认仍 0/0/0/0（27 tests PASS，strict exit 0）
- [ ] 阶段二：product variant 首个 CONV_DEL 应用
