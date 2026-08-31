# Task 076 — C5 修复：Release R8 收缩 protobuf 反射字段（16 时代报警剧）

**Phase**: C（B1 决策落地）
**起源**: task075 Release crash-loop（85×FATAL 单签名）
**优先级**: 高（当前唯一已知运行时缺陷）

---

## 证据基础（已冻结）

```
java.lang.NoSuchFieldException: No field educationViewedTimestampMillis_
in class Lcom/android/wm/shell/desktopmode/education/data/WindowingEducationProto;
  at com.google.protobuf.MessageSchema.reflectField
```
- 出现位置：我方 release APK `classes2.dex`
- 对照：Soong stock `classes3.dex` **有**；我方 `classes21.dex`（debug）**有**
- 诊断（task075 issue `docs/issues/2026-09-01-c5-dual-runtime-gate.md`）：R8 死码消除 protobuf-lite 生成类的 getter/setter，反射字段随之被收缩；Soong 不做 minify 所以没事
- C4c 移交清单第 4 条已预警此类

## 任务

### P1 根因现场确认 + 范围审计
1. 确认 `WindowingEducationProto` 的全部 getter/setter/字段在 release 中的缺失集合（与 debug 对比带出完整差异清单）
2. **不要只修这一个字段**——枚举 **release APK 中所有 protobuf-lite 生成类**（继承 `GeneratedMessageLite`），逐一比对 release vs debug 的成员收缩差异，带出受影响 proto 全集（可能不止 wmshell education）
3. 机械取证工具可复用 task053 `dex_bytecode_forensics`；可用 `javap`/`dexdump` 对 release APK

### P2 最小 keep 规则设计 + 落盘
- 原则：**按基类/包空间最小化 keep，反对宽膨胀**
- 起点：AOSP `system/core/rootdir/etc/proguard.flags`（参考行：`-keepclassmembers class * extends com.google.protobuf.GeneratedMessageLite { <fields>; }`）与 16 时代 task060/061（release keep 修复先例，查 `docs/issues/2026-08-20-release-r8-alignment-decisions.md` 和 commit 历史）
- 落点：`app/proguard_common.flags`（构建共享）
- 落盘后必须通过：
  - `com.android.wm.shell.**Proto` 全字段在 release APK 中对 debug 平齐
  - 后续所有层级 proto 类（Traceur?/wmshell?/packagemanager?）**零差异**枚举

### P3 验证
1. `./gradlew :app:assembleRelease --rerun-tasks`（R8 双杀 daemon 前奏：**先 `pkill -9 -f 'Gradle[D]aemon'; pkill -9 -f 'KotlinCompile[D]aemon'`**）
2. 验收：
   - 新 release APK 与旧 APK 的差别**只在**新增 keep 保留的成员（非偶然）
   - clean **两次** sha 逐字节复现
   - **release 三相点与 debug 一致**：Debug=所有字段；Release（新）= 同字段集
3. **不做设备验证**（依赖 task077 B3 完成后统一 runtime 门）

### P4 文档 + 交付
- issue：`docs/issues/2026-09-01-c5-release-proto-keep.md`
  - 根因三层诊断；受影响 proto 全清单；keep 规则设计 + 为何最小；规则落点；验证结果
- commit scope：`app/proguard_common.flags`、`docs/issues/`、本 brief（**只 add 自己的路径**，先 `git status` 核对）
- 简报 + commit-hash

## 纪律

- **不改 src/res**——规则增删是唯一允许改动；如果真正需要改 src（极不可能），先停工呈我
- **不 push**，chief 复核后 push
- 构建前双杀 daemon（OOM 预防）
- 如果 keep 规则意外导致 build size 大幅膨胀（>10% 的 v release APK），停工呈我
- issue 文档每个 P 阶段完成后立即更新（防上下文压缩）

## 交付清单
1. 修复的 keep 规则（`app/proguard_common.flags` diff）
2. 受影响 proto 全清单 + release vs debug 字段对比证据
3. clean 两次 build 北斗状 sha（确认无偶然性）
4. brief 交付核对清单全项 ✅
