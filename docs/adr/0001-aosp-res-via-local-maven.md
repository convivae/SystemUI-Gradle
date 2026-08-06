# ADR 0001: AOSP res 来源优先级——AAR 先直接引入，冲突后才用 local Maven

**状态**: 已接受；2026-08-06 按用户指令修订

> 历史决策曾写成“所有含 res 的 AOSP 库必须经 local Maven 引入”。2026-08-06 用户明确更正：
> **先直接引入 AAR 验证；只有确认 AAR-AAR、AAR-jar 或传递依赖冲突后，才用脚本生成本地 Maven AAR。**

## 上下文

SystemUI 编译大量依赖 AOSP res（drawable/string/layout/dimen 等）。遇到 res 缺失时，常见错误做法：

1. Agent 在 `app/src/main/res/` 凭空写一个同名 `R.string.foo` “解决”编译错误
2. 未验证实际冲突，直接把所有含 res 的库经脚本重打成本地 Maven AAR，导致产物来源和冲突原因不透明
3. 把 Maven 当成与 AAR 并列的第四种依赖产物，混淆了“产物类型”和“交付渠道”

参考项目 `CarSystemUIGradle` 的真实演进是：手工复制资源（易漏）→ flatDir AAR（资源合并/R 生成不完整）→ 在**出现问题后**使用本地 Maven AAR，借 Gradle/AAPT2 标准依赖解析解决。

## 决策

### 1. Maven 不是第四种依赖产物

- 本项目依赖形态是：SystemUI 源码、jar、AAR
- `libs/maven/` 是 **AAR 的本地 Maven 交付仓库**，仓内应是 AAR + POM
- `google()` / `mavenCentral()` 是上游第三方库的公网获取渠道

### 2. res 缺失处理优先级（严格顺序）

1. **AOSP SystemUI 源码**（规则 S 优先）
   - `SystemUI-core/res{,-keyguard,-product}/` 等必须与 AOSP 1:1 对齐（规则 C）
2. **AOSP 编译产物（非 SystemUI）**
   - 无 res 的纯代码库 → `libs/<name>.jar`
   - 有 res 的库 → **先以 AAR 直接引入**，不预先运行 `gen_aar_maven.py`
3. **验证冲突**
   - AAR-AAR 资源/类是否重复
   - AAR-jar 是否有重复类
   - 传递依赖、循环/重复依赖是否导致解析或资源合并冲突
4. **确认冲突后才启用本地 Maven AAR**
   - 先在 `docs/issues/` 记录具体冲突、来源、复现命令和处理方案
   - 再用 `tools/gen_aar_maven.py` 清理冲突类/资源、生成 AAR + POM，安装到 `libs/maven/`
   - 通过 `maven { url = uri("${rootProject.projectDir}/libs/maven") }` 引入
5. **标准上游库**
   - androidx/Compose/material/lottie 等直接使用 Google Maven / Maven Central 官方坐标
   - 不下载后再手工打成本地 jar/AAR；官方版本实在不能满足 AOSP 源码时，先记录、核对 `Android.bp`，再与用户讨论
6. ❌ **不允许** Agent 在 res/ 下生成同名资源绕过编译错误

### 3. 不默认使用 flatDir

参考项目已验证 flatDir AAR 的资源虽然可能进入 `merged.dir`，但 R 文件未正确生成、资源合并不完整。当前“直接 AAR”指 Gradle file dependency 等直接方式，不代表重新采用 flatDir 作为默认仓库。

## 为什么发生冲突后使用 local Maven AAR

本地 Maven 提供标准模块元数据和依赖图，Gradle/AGP 可按正常 AAR 依赖流程执行：

- 传递依赖解析
- 版本/重复依赖选择
- AAR transform
- AAPT2 资源合并
- POM 元数据管理

`gen_aar_maven.py` 可在生成阶段清理**已经确认**的重复类/资源；Gradle 在消费阶段再按依赖图处理跨 AAR 关系。脚本不是所有 AAR 的默认入口，而是实际冲突发生后的处理工具。

## 副作用 / 约束

- `gen_aar_maven.py` 的 `AOSP_ROOT` 必须指向 `/home/conv/myspace/aosp/`
- 新增脚本配置前必须先有可复现的直接 AAR 冲突记录
- `libs/maven/` 中不得长期保留 jar；纯代码产物应放 `libs/`
- 旧生成 AAR、无用 AAR、违反来源规则的 AAR 必须在依赖清理阶段删除
- AOSP 重编后，只刷新实际使用且已确认需要 local Maven 的 AAR

## 参考

- `CarSystemUIGradle/docs/GRADLE_MIGRATION.md` 问题七、问题八
- `CarSystemUIGradle/docs/DEPENDENCIES.md`
- `docs/architecture/2026-08-06-reference-project-rationale.md`
- AGENTS.md §1.1、§1.5、§1.8
