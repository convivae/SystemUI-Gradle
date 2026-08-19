# Task 026 — 依赖来源审计：官方 Maven 可用性排查 + 逐个试替换（不落盘）

## Goal

执行用户的依赖优先级原则（2026-08-19 明确）：**官方 Maven > 本地 jar > 本地 Maven AAR**。
对 `libs/` 全部产物逐一核查是否有公网官方坐标（Google Maven / Maven Central），
对候选项在 worktree 内**逐个试替换并构建验证**，产出决策矩阵报告。
**试验性替换全部 revert，最终 commit 只含报告。**

## 盘点范围

- `libs/*.jar`（31 个）+ `libs/prebuilts/*.jar`（1 个）；
- `libs/maven/` 全部 AAR（16 个 artifact）；
- 每个产物：`unzip -l` 看包名 → 判断 AOSP 特有还是上游第三方 → 查官方 Maven metadata：
  - `https://dl.google.com/dl/android/maven2/<group>/<artifact>/maven-metadata.xml`
  - `https://repo1.maven.org/maven2/<group>/<artifact>/maven-metadata.xml`

## 已知重点嫌疑（先查）

| 产物 | 疑似官方坐标 |
|---|---|
| `zxing-core.jar` | `com.google.zxing:core` |
| `libprotobuf-java-nano.jar` | `com.google.protobuf.nano:protobuf-javanano` |
| `keepanno-annotations.jar` | `com.android.tools.r8:keepanno-annotations` |
| `dynamicanimation-1.1.0-alpha04.jar` | `androidx.dynamicanimation:dynamicanimation` |
| `setupcompat.aar`（maven 仓） | `com.google.android.setupcompat:setupcompat`（很可能不在公网） |

其余（framework.jar、aconfig flags、SystemUI-* 自有产物、SettingsLib 家族、
WM-Shell、WifiTrackerLib、iconloader、animationlib、monet、android.car 等）
预判为 AOSP 特有，但**也要给出验证证据**（查过公网确认不存在），不许只写"预判"。

## 试替换协议（每个候选）

1. `git grep` 找消费点（哪个 build.gradle.kts 引用了它）；
2. 修改为官方坐标（catalog 加版本 + build 文件换行）；
3. 跑**受影响模块**的编译 + 若涉及 core/app 则 `:app:assembleDebug`；
4. 记录：官方版本 vs 本地版本差异、编译结果、API 差异导致的错误；
5. **`git checkout` 还原**，再试下一个；
6. 版本选择原则：与本地 jar 内容最接近的官方版本（可比 class 列表/API），
   或公网最新 stable——两者都记录。

## Non-goals

- 不在最终 commit 中替换任何依赖（报告驱动，用户批准后另行落地）；
- 不动源码、res、SysUISdk；
- 不为"能编译"而修改 AOSP 源码适配官方版本（适配成本如实记录即可）。

## Allowed Paths

- `docs/architecture/2026-08-20-official-maven-audit.md`（新建，最终报告）
- `docs/orchestration/tasks/026-official-maven-audit.md`（本文件勾选）
- 试验期可临时改 `gradle/libs.versions.toml` 与相关 build.gradle.kts，**必须全部 revert**

## Forbidden Paths

最终 commit 不得含以上临时改动之外的任何文件。源码/res/libs 产物一律不动。

## Acceptance

- 报告含：48 个产物（32 jar + 16 AAR）逐一的判定表（官方坐标存在性 + 证据 URL）、
  候选试替换矩阵（替换后构建结果）、落地建议分批清单；
- `python3 -m unittest discover -s tools/tests -p 'test_*.py'` OK；
- 最终 `git status` 除报告/brief 外干净（所有试验改动已 revert）；
- 英文 commit；不 push。

## Report

完成后汇报：commit、候选清单摘要、试替换通过率、新发现、HANDOFF 块。
