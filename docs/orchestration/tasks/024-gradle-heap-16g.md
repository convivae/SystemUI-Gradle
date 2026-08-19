# Task 024 — Gradle daemon heap 提到 16G 并实证

## Goal

`gradle.properties` 的 `org.gradle.jvmargs=-Xmx4g` 提到 `-Xmx16g`（用户 2026-08-19 批准），
并**实际构建验证默认配置下不再 OOM**。

背景：默认 4g daemon 在 core javac 阶段 OOM（Task 002/003/004 三次记录），
此前 worker 用 CLI `-Xmx12g --no-daemon` 规避。机器 30GB RAM / 12 核。

## 变更

- `gradle.properties`：`org.gradle.jvmargs=-Xmx4g -Dfile.encoding=UTF-8`
  → `org.gradle.jvmargs=-Xmx16g -Dfile.encoding=UTF-8`（仅此一处）
- issue 文档记录

## 验证协议（关键：不得用 CLI 覆盖，必须测默认值）

1. 记录 `free -g` 基线；
2. **先 `pkill -f GradleDaemon` 或 `./gradlew --stop`**，确保新 daemon 读到新配置；
3. `./gradlew :app:clean :app:assembleDebug`（不加任何 `-Dorg.gradle.jvmargs`，不用
   `--no-daemon`）——BUILD SUCCESSFUL 且全程无 OOM/GC overhead 错误；
4. 可选复验：`./gradlew :SystemUI-core:compileDebugJavaWithJavac --rerun-tasks`（历史 OOM 点）；
5. `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK（148 基线）；
6. 若仍 OOM：如实记录并 REDLINE 报告（不要擅自换其他参数组合）。

## Non-goals

- 不动其他 gradle.properties 条目；
- 不动 daemon 并行度、`--no-daemon` 等其他构建实践。

## Allowed Paths

- `gradle.properties`（仅 jvmargs 行）
- `docs/issues/2026-08-19-gradle-heap-16g.md`（新建）
- `docs/orchestration/tasks/024-gradle-heap-16g.md`（本文件勾选）

## Forbidden Paths

其它一切。

## Acceptance

- `:app:assembleDebug` BUILD SUCCESSFUL（默认配置，真实输出粘贴）
- 148 工具测试 OK
- issue 含 free 基线、构建输出尾部、结论

## Report

完成后汇报：commit、验证输出、issue 更新、HANDOFF 块。
