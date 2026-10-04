# ADR 0004: AOSP 源码改动标记规范（CONV）与对齐纪律

**状态**：已接受；2026-08-07 与用户经 grilling 对齐后确定

## 上下文

本项目以 AOSP `frameworks/base/packages/SystemUI/` 源码为唯一来源（规则 S/C/F/R）。在 Gradle 构建中，AOSP 源码/资源有时**无法直接消费**——典型场景是 AOSP `res-product` 用 `product="tv"`/`product="tablet"`/`product="device"`/`product="default"` 属性区分设备变体，Soong 的资源处理器理解该属性，但 **AAPT2 不支持**，把多个变体当 default 重复，报 `Found item ... more than one time`。

参考项目 `CarSystemUIGradle` 的处理方式是**用 Python regex 直接删除**非 default 变体（见 `docs/GRADLE_MIGRATION.md:395-413`）。但本项目规则 R 明确"禁止擅改 res 文件"，且用户要求：

1. **改动可追溯、可撤回**——一眼分辨"AOSP 原码 vs 后加代码"
2. **不直接删除**——原内容以注释形式保留在文件里
3. **打标记**而非偷偷改——每个改动都有书面凭证

同时，`tools/check_source_alignment.py` 的字节级 `diff_pair()` 无法区分"偷偷擅改"和"带标记的授权改动"——字节一变就报 MODIFIED。若让 strict 继续卡 MODIFIED，打标后就无法当回归门禁用。

本 ADR 解决两件事：(1) AOSP 源码改动的标记规范；(2) 对齐工具的职责边界与改动纪律。

## 决策

### 决策 1：CONV 标记规范

本项目所有对 **AOSP 源码**（src/aidl/res/AndroidManifest/Android.bp 等）的改动必须用 `CONV` 前缀的三件套标记：

| 操作符 | 语义 | 实现 |
|--------|------|------|
| `CONV_ADD` | 新增本项目定制代码 | 直接写新行，用 BEGIN/END 块包裹 |
| `CONV_DEL` | 删除（注释掉）AOSP 原行 | 原行用所在语言注释语法包裹，不真正删字节 |
| `CONV_MOD` | 修改 AOSP 原行 | 原行注释掉 + 写新行 |

块标记固定格式：`CONV_XXX BEGIN: reason` / `CONV_XXX END`。

**核心理念**：AOSP 源码的每一处改动都可追溯、可撤回；一看代码就知道改了哪些地方、哪是 AOSP 原码、哪是后加的。本项目自己写的代码不打标记，随便写。

### 决策 2：各文件类型的注释语法

**kt/java**（`//` 行注释为默认，`/* */` 块注释可选）：

```kotlin
// CONV_ADD BEGIN: 新增定制逻辑
val customFoo = CustomBar()
// CONV_ADD END

// CONV_MOD BEGIN: 把 private 改为 internal，Gradle Dagger 可见性
// private val foo: Bar = ...
val foo: Bar = ...
// CONV_MOD END

// CONV_DEL BEGIN: 移除不再需要的字段
// val deprecated: String = "x"
// CONV_DEL END
```

MOD 注释原行默认用 `//` 行注释（每行加 `//`，撤回时删整行最干净）；原行很长或想保持块整洁时可选 `/* */` 块注释。

**XML**（必须用 `<!-- -->`，不能用 `<! ...>`）：

```xml
<!-- CONV_ADD BEGIN: 新增产品定制资源 -->
<string name="custom_string">...</string>
<!-- CONV_ADD END -->

<!-- CONV_MOD BEGIN: 把私有样式改为公开 -->
<!-- <style name="Foo" parent="@*android:style/Bar"/> -->
<style name="Foo" parent="@android:style/Bar"/>
<!-- CONV_MOD END -->

<!-- CONV_DEL BEGIN: 移除 tv 变体，AAPT2 不支持 product 属性 -->
<!-- <string name="x" product="tv">...</string> -->
<!-- CONV_DEL END -->
```

**关键约束**：XML 注释必须是 `<!-- ... -->`（`<!` 后只能跟 `--`/`DOCTYPE`/`[CDATA[`，否则 AAPT2 严格 XML 解析器报 `not well-formed`）。BEGIN 标记行、被注释的原行、END 标记行是**三个独立的 `<!-- -->` 注释**，AAPT2 把三行都当注释忽略。

### 决策 3：reason 字段与 END

- `BEGIN` 行唯一可选字段是 `reason`，**非必填**（可写 `// CONV_ADD BEGIN` 或 `// CONV_ADD BEGIN: 说明文字`）
- `END` 行**不带 reason**（固定 `// CONV_XXX END`）
- 需关联 issue/ADR 时，写进 reason 文字本身（如 `// CONV_MOD BEGIN: 修 dagger 可见性，见 docs/issues/...`）

### 决策 4：豁免范围

以下改动**不需要**打 CONV 标记：

| 项 | 理由 |
|----|------|
| import 语句 | import 只调整顺序/增删，属配置非逻辑，写注释反而乱 |
| package 声明 | 文件级声明，改动罕见且语义属配置 |
| 文件级注解（`@file:JvmName`、`@file:Suppress` 等） | 文件级元数据，改动属配置非逻辑 |
| 整文件自写 | 全文件无 AOSP 对照，打标无意义 |
| Gradle 文件（`*.kts`/`*.toml`/settings/properties） | 不是 AOSP 源码，归属本项目构建配置 |

**"整文件自写"判定**：以"该文件在 AOSP 对应目录里是否存在"为唯一依据（用 `check_source_alignment.py` 的 AOSP 镜像路径判定），**不靠主观"像不像 AOSP 风格"**。AOSP 有对应文件 → 是 AOSP 源码，改动要打标；AOSP 无对应文件 → 整文件自写，不打标。

### 决策 5：整文件自写需审核

本项目原则上不创建新代码/资源文件——所有文件都应来自 AOSP 源码。确需创建新文件时（**非 Gradle 文件**），须：
1. 放在特定路径（不与 AOSP 源码目录混淆）
2. 经用户审核

Gradle 文件（`build.gradle.kts`/`libs.versions.toml`/`settings.gradle.kts` 等）的创建与修改不受此约束。

### 决策 6：顺序铁律（改动纪律）

**必须先跑 `check_source_alignment.py` 达到全模块 MISSING/MISPLACED/EXTRA 全 0，确认"源码不漏不多不错位"后，才允许动 AOSP 源码打 CONV 标记。** 绝不在对齐未干净时边改边对齐。

理由：打标会改变文件字节，若在对齐未干净时打标，"漏/多/错位"和"已授权改动"会混在一起，无法分辨，后期维护不了。

### 决策 7：规则 R 受控出口

规则 R 由"禁止擅改 res"细化为"**禁止无 CONV 标记地擅改 res/src**"。带 CONV 标记的改动是受控例外，靠：
1. issue 文档（记录改动清单与原因）
2. 对齐 MODIFIED 清单（工具列出哪些文件字节变了）

双重记录，逐条对账。无 CONV 标记的字节改动 = 违规擅改，必须回滚。

### 决策 8：对齐工具职责收敛

`tools/check_source_alignment.py` 的 `--strict` 模式**只卡 MISSING/MISPLACED/EXTRA**，不再卡 MODIFIED：

- MODIFIED 仍报告（列文件清单），但不影响 exit code
- "是否擅改"靠人工对账：MODIFIED 文件清单 ↔ issue 里的 CONV 记录，逐条核对有没有标记
- 工具只负责客观判断"漏/多/错位"，"是否擅改"由人工 + CONV 标记 + issue 三方保证

理由：工具做字节级 diff 无法区分"偷偷擅改"和"授权改动"；与其复杂化工具去解析注释语法，不如把"是否擅改"交给人工对账，工具保持简单。

### 决策 9：首个应用案例

product variant 处理（删除 res-product 下非 default 的 product 变体）是 CONV_DEL 的首个应用案例。用 Python 脚本（符合 ADR 0002）批量加 CONV_DEL 块，注释掉非 default 变体，不真正删除字节。

## 副作用 / 约束

- `check_source_alignment.py` 需修改 `--strict` 判定逻辑（两处），从 strict 条件中移除 `src["modified"]` 和 `res["modified"]`，MODIFIED 仍报告
- `tools/tests/test_check_source_alignment.py` 需加测试验证"MODIFIED>0 时 strict 仍 exit 0"
- AGENTS.md 规则 R 措辞升级为"禁止无标记擅改"，并引用本 ADR
- HANDOFF / CURRENT_STATE 需引用本 ADR
- 本 ADR 不修改规则 P/S/C/F/B 的核心条款；规则 C 的"不漏不多"靠工具 MISSING/MISPLACED/EXTRA 保证，字节级 MODIFIED 改由人工对账
- CONV 标记不能嵌套：XML 注释不能含 `--`、不能嵌套 `<!-- -->`；kt/java 的 `/* */` 不能嵌套。遇到需注释掉已含注释的原码时，按规则 H 停止并询问用户
- 打标后的对齐结果：MODIFIED 清单与 issue CONV 记录必须逐条对账，无标记的改动必须回滚

## 决策状态

- 标记规范、顺序铁律、工具职责：已确定
- product variant 首例应用：待阶段二执行（先完成阶段一规范落地）
- 后续遇到需注释掉已含注释的原码、或需创建新文件时：按规则 H 停止并询问用户

## 参考

- AGENTS.md §1.3 规则 R（res 不得擅改）→ 本 ADR 细化为"禁止无标记擅改"
- AGENTS.md §1.6 规则 C（不漏不多）→ 靠工具 MISSING/MISPLACED/EXTRA 保证
- AGENTS.md §2.5 规则 H（求助于用户）→ 遇标记嵌套/创建新文件时触发
- ADR 0002（tools 脚本必须 Python）→ product variant 处理脚本须 Python
- ADR 0003（模块对齐 BP）→ 模块结构基线
- `tools/check_source_alignment.py` → 对齐工具（strict 逻辑待改）
- 参考项目 `CarSystemUIGradle/docs/GRADLE_MIGRATION.md:395-413` → 参考项目用直接删除（本项目改用 CONV_DEL 注释）
- 参考项目 `JD MOD`/`JD ADD` 标记 → 命名灵感来源（本项目改用 `CONV`）
- `docs/issues/2026-08-07-conv-markup-spec.md` → 规范全文与示例
