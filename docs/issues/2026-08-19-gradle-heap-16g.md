# 2026-08-19 Gradle daemon heap 提到 16G 并实证（Task 024）

## 背景

默认 `org.gradle.jvmargs=-Xmx4g` 的 daemon 在 core javac 阶段 OOM
（Task 002/003/004 三次记录），此前 worker 用 CLI `-Xmx12g --no-daemon` 规避。
用户 2026-08-19 批准将 heap 提到 16G，并要求实证默认配置下不再 OOM。

机器：30GB RAM / 12 核。

## 变更

- `gradle.properties`：`org.gradle.jvmargs=-Xmx4g -Dfile.encoding=UTF-8`
  → `org.gradle.jvmargs=-Xmx16g -Dfile.encoding=UTF-8`（仅此一处，其他条目不动）

## 操作步骤与验证协议

1. `free -g` 基线（改动前）：

   ```
                 total        used        free      shared  buff/cache  available
   Mem:              30          15           6           0           9          15
   Swap:              7           3           4
   ```

   （nproc = 12）

2. 修改 `gradle.properties` jvmargs 行（见上）。
3. `./gradlew --stop` 停掉旧 daemon，确保新 daemon 读到新配置。
4. `./gradlew :app:clean :app:assembleDebug`（不加任何 `-Dorg.gradle.jvmargs`，
   不用 `--no-daemon`）——结果见下文"构建结果"。
5. 可选复验：`:SystemUI-core:compileDebugJavaWithJavac --rerun-tasks`（历史 OOM 点）。
6. `python3 -m unittest discover -s tools/tests -p 'test_*.py'`（148 基线）。

## 构建结果

### 主验证：`./gradlew :app:clean :app:assembleDebug`（默认配置）

- 先执行 `./gradlew --stop`（1 Daemon stopped），确保新 daemon 读到 16G 配置
- 命令未加任何 `-Dorg.gradle.jvmargs` 覆盖、未用 `--no-daemon`
- 输出尾部（真实粘贴）：

  ```
  > Task :SystemUI-core:compileDebugJavaWithJavac
  warning: unknown enum constant Client.MODULE_LIBRARIES
    reason: class file for android.annotation.SystemApi$Client not found
  ...
  > Task :app:dexBuilderDebug
  > Task :app:mergeDebugJavaResource
  > Task :app:mergeProjectDexDebug
  > Task :SystemUI-core:bundleLibRuntimeToDirDebug
  > Task :app:mergeLibDexDebug
  > Task :app:packageDebug
  > Task :app:createDebugApkListingFileRedirect
  > Task :app:assembleDebug

  BUILD SUCCESSFUL in 2m 54s
  217 actionable tasks: 216 executed, 1 up-to-date
  ```

- 全程无 `OutOfMemoryError`、无 `GC overhead limit exceeded`
- APK 实际产出：`app/build/outputs/apk/debug/app-debug.apk`（158,775,460 bytes）

### 复验：历史 OOM 点 `--rerun-tasks`

`./gradlew :SystemUI-core:compileDebugJavaWithJavac --rerun-tasks`：

```
BUILD SUCCESSFUL in 1m 35s
91 actionable tasks: 91 executed
```

无 OOM。（历史 OOM 均发生在 core javac 阶段，此任务重跑通过。）

## 工具测试

`python3 -m unittest discover -s tools/tests -p 'test_*.py'`：

```
Ran 148 tests in 33.576s
OK
```

## 结论

- `gradle.properties` daemon heap 4g → 16g 后，默认配置（无 CLI 覆盖、无 `--no-daemon`）
  下 `:app:clean :app:assembleDebug` BUILD SUCCESSFUL 且产出真实 APK，
  core javac 历史 OOM 点 `--rerun-tasks` 复验亦通过。
- Task 002/003/004 记录的默认 4g OOM 问题至此解除，后续 worker 不再需要
  `-Xmx12g --no-daemon` CLI 规避。
- 本次运行还顺带确认 `:app:assembleDebug` 已不再被 AGENTS.md §4.2 记录的
  SettingsLib switch drawable 缺失阻塞（其他 task 已先行修复，本 task 未触及）。

## 待解决问题

- 无（本 task 范围内）。构建尾部 Gradle 提示可考虑启用 configuration cache，
  属后续优化选项，不在本 brief 范围。
