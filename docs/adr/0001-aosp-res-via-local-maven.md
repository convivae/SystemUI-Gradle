# ADR 0001: AOSP res 必须经 local maven 引入，禁止 Agent 生成同名 res

## 上下文

SystemUI 编译大量依赖 AOSP res（drawable/string/layout/dimen 等）。
遇到 res 缺失时，常见错误做法：

1. Agent 在 `app/src/main/res/` 凭空写一个同名 `R.string.foo` "解决" 编译错误
2. 把 aar 直接 `flatDir { dirs("libs/aar") }` 引入，多个 aar 间资源名冲突导致构建失败

## 决策

**res 缺失处理优先级（严格顺序）：**

1. **AOSP 源码**（规则 S 优先）：SystemUI 自有的 res 在 `SystemUI-core/res{, -keyguard, -product}/`，必须与 AOSP 1:1 对齐（规则 C）
2. **AOSP 编译产物**（规则 ② jar/aar）：
   - 无 res 的纯代码库 → `libs/<name>.jar`
   - 有 res 的库 → 经 `tools/gen_aar_maven.py` **打包成本地 maven aar**，放 `libs/maven/com/android/systemui/<name>/1.0.0/`，在 `settings.gradle.kts` 通过 `maven { url = uri("${rootProject.projectDir}/libs/maven") }` 引入
3. **公网 maven**（规则 ③）：androidx/material/lottie 等
4. ❌ **不允许** Agent 在 res/ 下生成同名资源 "绕过" 编译错误
5. ❌ **不允许** Agent 用 flatDir 引入 aar

## 为什么 local maven 而非 flatDir aar

**Gradle 对 aar 资源冲突的处理**：

- **flatDir aar**：所有 aar 的 res 文件被收集到 `merged.dir`，同名资源直接覆盖（后者覆盖前者，不可预测）；AAPT2 报 "duplicate resource"
- **local maven aar**：Gradle 解析依赖时**构建依赖图**，识别同一 `groupId:artifactId:version`，自动按依赖顺序合并资源

**双保险**：

- `tools/gen_aar_maven.py` 在生成阶段用 `remove_duplicate_resources()` 跨文件去重
- Gradle 在引入阶段用依赖图去重

两者互补，缺一不可：脚本防止同 aar 内重复，Gradle 防止跨 aar 重复。

## 副作用 / 约束

- `gen_aar_maven.py` 的 `AOSP_ROOT` 必须指向当前 AOSP out 目录（参考项目指向 `/home/conv/myspace/rom/jkc-A/...`，本项目指向 `/home/conv/myspace/aosp/`）
- 新加 aar 必须改 `gen_aar_maven.py` 的 `AAR_CONFIGS` 列表 + `libs.versions.toml` 的 plugin id
- 每次 AOSP 重编后，需要重跑 `python3 tools/gen_aar_maven.py` 刷新

## 参考

- `CarSystemUIGradle/tools/gen_aar_maven.py`（参考实现，已复制到本项目 `tools/gen_aar_maven.py`）
- AGENTS.md §1.5 规则 S（Source-first） + §1.7 规则 F（framework 走 SDK/jar）
- `docs/issues/2026-07-29-completeness-audit.md` §3.1（命名空间/合并问题的根因）