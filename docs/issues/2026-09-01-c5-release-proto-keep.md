# 2026-09-01 — Task 076 / C5 B1: Release R8 收缩 protobuf-lite 反射字段修复

> Worker: task076 (herdr pane)。Brief: `docs/orchestration/tasks/076-release-proto-keep-fix.md`。
> 起源: task075 Release crash-loop（85×FATAL 单签名，
> `docs/issues/2026-09-01-c5-dual-runtime-gate.md` Route B / B-Step 4）。

## 背景与冻结证据（task075 已取证，采信）

```
java.lang.NoSuchFieldException: No field educationViewedTimestampMillis_
in class Lcom/android/wm/shell/desktopmode/education/data/WindowingEducationProto;
  at com.google.protobuf.MessageSchema.reflectField
```

- 我方 release APK `classes2.dex`：proto 字段本体被 R8 shrink（仅剩 const-string 字面量）
- 我方 debug `classes21.dex`：字段 + accessor 全在
- Soong stock `classes3.dex`：字段在、accessor 同被删（Soong R8 版本行为差异）
- 机制：protobuf-lite 生成类以字符串常量把字段名交给运行时 `MessageSchema.reflectField`
  反射（`GeneratedMessageLite.hashCode` 路径触发）；accessor 被 R8 死码消除后字段失去
  唯一 Java 引用 → 字段被 shrink → `NoSuchFieldException`

## AOSP 17 侧 keep 先例调研（本任务 P2 输入）

| 来源 | 规则 | 形态 |
|---|---|---|
| `packages/modules/Permission/PermissionController/proguard.flags` L32-36 | `-keepclassmembers class * extends com.google.protobuf.GeneratedMessageLite { *** get*(); *** set*(***); *** has*(); }` | keep **accessor**（注释："for proto names for Proto.toString"） |
| `art/libartservice/service/proguard.flags` | 同上 accessor 形态（jarjar 命名空间），注释 "Proto field names are used by MessageLiteToString.toString through reflection" | keep accessor |
| `frameworks/base/packages/SystemUI/proguard_common.flags` | **无任何 protobuf keep**（与本项目 `app/proguard_common.flags` 逐字节一致，已 diff 验证） | — |
| brief 引用的 `system/core/rootdir/etc/proguard.flags` 参考行 | 17 检出中该文件无此行；`grep -rn GeneratedMessageLite --include='*.flags'` 全仓仅命中上述两处 + cronet/protobuf 源码列表 | `<fields>` 形态出处未能证实 |

## P1 — 根因现场确认 + 范围审计（完成）

方法：dexdump（build-tools 37.0.0）解析 debug（`a8bab0f6…`，193,890,789 B）/ release
（`7fadce6d…`，45,030,130 B）两 APK 全部 dex，枚举 proto 基类直系子类，逐类比对
静态/实例字段集（脚本 `/tmp/task076_proto_forensics.py`，只读取证）。

### 范围结论（决定性）

| 基类 | debug 类数 | release 存活 | 存活类实例字段损失 |
|---|---:|---:|---|
| `GeneratedMessageLite`（message）+ `$Builder` | 472 | 26（13 message + 13 Builder） | **13/13 message 类全部有损** |
| nano（`MessageNano`/`ExtendableMessageNano`） + `AbstractMessageLite`/`MicroMessage` 直系 | 17 | 9 | **0**（实例字段全平齐） |

- **受影响全集 = 13 个 lite message 类**，全部位于 `com.android.wm.shell.{apptoweb,
desktopmode.data.persistence, desktopmode.education}.data/persistence}`（即 16 时代
batch 4B 补入 WindowManager-Shell AAR 的 lite-proto 族）：
  `AppToWebProto`、`AppToWebUserRepository`、`Desktop`、`DesktopPersistentRepositories`、
  `DesktopRepositoryState`、`DesktopTask`、`PackageState`、`PreservedDisplay`、`Rect`、
  `RectF`、`WindowingEducationProto`、`WindowingEducationProto$AppHandleEducation`、
  `WindowingEducationProto$AppToWebEducation`（均 classes2.dex）
- 472→26 的 446 个整类移除均为未被引用的死码（settingslib graph/spa、protobuf
  well-known types 等），无反射路径 → 不属于缺陷
- `WindowingEducationProto` 实例字段 9→3：丢失 `educationViewedTimestampMillis_`、
  `appHandleHint{Used,Viewed}TimestampMillis_`、`enter/exitDesktopModeHintViewedTimestampMillis_`、
  `featureUsedTimestampMillis_`；静态丢 8 个 `*FieldNumber` 常量
- 其余 12 类丢 `bitField0_`（部分类）+ 全部 `*FieldNumber` 静态常量
- Builder 子类自身 0 字段（lite builder 无自有字段，字段在 message 实例上）
- **nano 层零实例字段损失**（仅丢被内联的静态常量/`_emptyArray`）——`-keepnames
  class com.android.**.nano.** { *; }` 现状已够；与 Soong stock 行为一致
- 根因三层：① protobuf-lite 生成类把字段名编入运行时 info 表（数据保留）但字段本体
  是 Java 引用语义；② R8 死码消除删除未被调用的 accessor 后字段失去唯一引用被 shrink；
  ③ `-allowaccessmodification` 下反射 `getDeclaredField` 在字段缺失时抛
  `NoSuchFieldException` → 85×FATAL crash-loop（wmshell.hashCode 链，DataStore 读路径触发）

## P2 — keep 规则设计（已实施）

### 落盘 diff（`app/proguard_common.flags`，ShellProtoLogGroup 块后新增）

```proguard
-keepclassmembers class * extends com.google.protobuf.GeneratedMessageLite {
    <fields>;
}
```

### 设计论证（为何最小）

1. **形态选择：`<fields>` vs accessor（AOSP PermissionController/art 先例形态）**
   - accessor 形态（`*** get*(); set*; has*`）会把方法体字节码全部拉回来，
     再连带字段（被 accessor 引用）——严格大于 `<fields>` 形态
   - `<fields>` 只保留字段声明本身；accessor 保持可删
   - **端态与 Soong stock 精确一致**：stock dex 同样是“字段在、accessor 删”且设备
     健康（task075 取证）——即反射只需字段，accessor 本就是死码
2. **作用域选择：基类通配 vs 包名枚举**
   - `class * extends com.google.protobuf.GeneratedMessageLite` 按基类匹配，
     `keepclassmembers` 不会复活已被整类移除的死类（446 个未引用类不受影响）
   - 实际生效面 = release 存活的 13 个 message 类（全部在 wm.shell lite-proto 族），
     不逐包枚举，未来新 proto 族自动覆盖且无需扩规则
3. **Builder 不加规则**：取证证实 lite Builder 子类自身 0 字段（字段在 message 实例上）
4. **不加 `-dontwarn`/不改其他 flags**：无 missing-rules 变化诉求

## P3 — 构建验证（进行中）

### 环境事故记录（如实）

1. 首次双杀后 clean+assembleRelease：Gradle daemon（16g heap，RSS 16.3–19.6G）被
   kernel OOM-kill。排查发现两个共存问题：
   - **双杀模式盲区**：`pkill -f 'KotlinCompile[D]aemon'` 匹配不到 AGP builtInKotlin
     的 Kotlin daemon（进程 cmdline 为 `kotlin-daemon-embeddable` jar 启动，无
     `KotlinCompileDaemon` 字样）——需补 `pkill -f kotlin-daemon-embeddable`
   - **并发 AOSP 构建**：task077（B3，emu64x 镜像重建）同时在跑 `m -j8`，
     soong_build analysis 阶段单进程 RSS 达 20G，与 16g Gradle daemon 在 30G 宿主机上
     互为 OOM 受害者（journal：18:13/18:16/18:20/18:21 四杀，双方各死两次）
2. 处置：不杀别人构建；等待 soong analysis 阶段过去（ninja 执行期内存友好）后再
   用与基线（7fadce6d）完全相同的构建参数重建，保持确定性口径。旧产物已备份
   `/tmp/task076-forensics/old-{release,debug}.apk`。
3. **pkill 自杀陷阱（后来才破案）**：`pkill -9 -f 'kotlin-daemon-embeddable'` 的模式
   会匹配到自身 bash 命令行（cmdline 内含该字符串）把自己杀掉——两次“构建”
   实际根本没跑起来。正确写法用括号技巧 `pkill -9 -f 'kotlin-daemon-[e]mbeddable'`。

### 稳定构建协议（30G 宿主机，16g Gradle daemon + builtInKotlin）

**两阶段法**（已三次验证稳定）——单次 `clean+assembleRelease` 会在 R8 阶段输掉内存
竞速：编译期 Kotlin daemon 膨胀至 7–12G 且 idle 不归还，R8 起步 2 秒内 Gradle daemon
冲到 18G+，双双触顶 OOM：

```bash
# 阶段 A：编译（~3m15s）
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew clean \
    :app:mergeReleaseJavaResource :app:expandReleaseArtProfileWildcards \
    --console=plain --max-workers=4
pkill -9 -f 'kotlin-daemon-[e]mbeddable'   # 释放 7-12G，编译已全部完成，安全可复活
# 阶段 B：R8 + 打包（~4m）
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 ./gradlew :app:assembleRelease \
    --console=plain --max-workers=4
```

### 构建记录

| # | 方式 | 结果 | whole-file sha256 | content-sha（剥 SDKP） | 大小 |
|---|---|---|---|---|---|
| 1 | 单次 clean+assemble（R8 起点杀 Kotlin daemon 成功） | 7m26s ✅ | `0baccfb3…`（APK 已被后续 clean 删除，未留存） | — | 45,046,514 |
| 2 | 单次 clean+assemble（同上） | 7m11s ✅ | `2d6f27ec…` | `2a5e372f…` | 45,046,514 |
| 3 | 两阶段 | 3m14s+4m04s ✅ | `d7c1bdf…` | `2a5e372f…` | 45,046,514 |
| 4 | 两阶段 | 3m18s+4m30s ✅ | `f389bd45…` | `2a5e372f…` | 45,046,514 |

（#2/#3/#4 产物备份于 `/tmp/task076-forensics/release-build{2,3,4}.apk`）

### 验收 1：新 vs 旧 release APK 差异只在 keep 成员（非偶然）✅

全类结构 diff（22,451→22,455 类，dexdump 逐类字段集比对，脚本
`/tmp/task076_release_diff.py`，报告 `/tmp/task076-forensics/old-vs-new.txt`）：

- **类集差异**：无删除；仅 +4 类：`AbstractMessageLite`、`Internal$IntList`、
  `Internal$ProtobufList`、`Parser`——全部是 keep 字段的**声明类型**（旧包里被 R8
  折叠/持化为优化子类型，现在随字段保留而回归）
- **结构差异 17/22,455 类**，且全部是 keep 规则的级联效果：
  - 13 个 lite message 类：字段全量回归（`*FieldNumber` 静态 + `bitField0_` + 全部
    数据字段），访问标志回到源码的 private（0x2），字段类型回到声明类型
    （如 `IntArrayList`→`Internal$IntList`、oneof `GeneratedMessageLite`→`Object`）
  - 4 个 protobuf runtime 类（`GeneratedMessageLite` super 回到 `AbstractMessageLite`、
    `MessageSchema`/`MessageSetSchema`/`RawMessageInfo` 的 `defaultInstance` 字段类型
    随之回迁）——R8 不再能折叠 GML 继承链的必然结果
- **其余 22,438 类零结构变化**：改动面 = keep 规则效果且仅此，非偶然

### 验收 2：release 三相点与 debug 一致 ✅

（脚本 `/tmp/task076_proto_forensics.py`，报告 `/tmp/task076-forensics/report-after-fix.txt`）

- 13 个 lite message 类 **inst/static 字段计数与 debug 完全平齐**（例：
  `WindowingEducationProto` 9→9 inst、10→10 static，含全部
  `*_FIELD_NUMBER` 与 `bitField0_`）
- per-class member diff 中 lite 族差异归零；仅剩 7 个 nano 类的静态常量差异
  （实例字段全平齐，与 Soong stock 行为一致，无反射风险）
- release-only proto 类：无

### 验收 3：clean 两次逐字节复现 → **字面不可满足，根因已查明（上游 AGP）**

三次 clean 构建 whole-file sha 各不同，但 zip 条目（3,488 个）**逐字节全同**
（内容/顺序/时间戳/CRC/压缩参数），差异 100% 集中在 APK Signing Block 内 ID
`0x504b4453`（"SDKP"）的 13,349 字节块：

- **写入者**：AGP `SdkDependencyDataGeneratorTask`（`ApplicationTaskManager.kt` L237，
  `!debuggable` 才挂接——这解释了 task075 debug APK 能 byte-复现）→ 经
  `apkzlib SigningExtension.onOutputZipEntriesWritten` →
  `SigningBlockUtils.addToSigningBlock(block, sdkDependencyData, 0x504B4453)` 插入
- **内容**：SDK 依赖元数据（protobuf）先 deflate 再用 **Tink ECIES 混合加密**
  （硬编码 Google 公钥，context `SDK_DEPENDENCY_INFO`）。**ECIES 每次加密用随机
  临时密钥，密文必然不同**——任何 AGP release APK 整文件 sha 都不可能复现
- v2 签名 pair（RSA，确定性）与 verity padding（全零）在三次构建中**逐字节相同**
- **content-sha**（剥离 SDKP 后对全文件重新求 sha，脚本 `/tmp/content_sha.py`）：
  #2/#3/#4 三连一致 `2a5e372f0db662cdb64d2e5bfa092272ee33091f99b8932eec39b6ffdd454fee`
- **呈报决策点（chief）**：AGP 开关 `android.includeDependencyInfoInApks=false`
  （`BooleanOption.kt` L148，默认 true）可彻底移除该块获得整文件可复现 + APK 减重
  ~13KB，但属 gradle.properties 仓库改动，超出本 brief 允许的改动面（仅
  proguard_common.flags + docs），未擅动，留待决策

### 验收 4：体积守门 ✅

新 release APK 45,046,514 B vs 旧 45,030,130 B：**+16,384 B（+0.036%）**，
≪10% 停工线（阈值 ~49,533,143 B）

## P4 — 交付（待）

## 待解决问题

1. **运行时验证**：按 brief P3-3 不做设备验证，依赖 task077 B3 完成后统一 runtime
   门（85×FATAL 是否归零需上机确认；反射路径字段已平齐，理论闭环）
2. **SDKP 块复现性决策**：见验收 3 呈报——`android.includeDependencyInfoInApks`
   开关是否关闭，需 chief 决策（影响：整文件 sha 可复现性 + ~13KB 体积 vs Play
   依赖元数据上报）
3. 旧 release APK（`7fadce6d…`）的 SDKP 块同为随机密文，其整文件 sha 同样不可
   复现——task075 时代若做过 release 级复现实验应重新解读（只做过 debug，无矛盾）

---

## 附录：取证/复现工具源码（防 /tmp 丢失；亦备份于 /tmp/task076-forensics/）

### A1. `content_sha.py` — 剥离 SDKP 随机块后的内容级 sha（复现性 gate 量具）

```python
#!/usr/bin/env python3
"""Content-level sha: strips the AGP SDK-dependency (Tink ECIES, random) pair
(id 0x504b4453 'SDKP') from the APK Signing Block; keeps everything else."""
import hashlib
import struct
import sys

def content_sha(path):
    raw = open(path, "rb").read()
    m = raw.rfind(b"APK Sig Block 42")
    if m < 0:
        return hashlib.sha256(raw).hexdigest(), "no-signing-block"
    size2 = struct.unpack("<Q", raw[m-8:m])[0]
    sig = struct.pack("<Q", size2)
    pos = raw.rfind(sig, 0, m-8)
    off, end = pos + 8, m - 8
    out = bytearray(raw[:pos])  # zip entries up to size1
    while off < end:
        (sz,) = struct.unpack("<Q", raw[off:off+8])
        bid = struct.unpack("<I", raw[off+8:off+12])[0]
        if bid != 0x504b4453:  # keep v2 sig, verity padding, others
            out += raw[off:off+8+sz]
        off += 8 + sz
    out += raw[m-8:]  # size2 + magic + CD + EOCD
    return hashlib.sha256(bytes(out)).hexdigest(), "sdkp-stripped"

for p in sys.argv[1:]:
    h, mode = content_sha(p)
    print(f"{h}  {mode}  {p}")
```

### A2. Signing Block pair 枚举（诊断 SDKP 块的通用三行法）

```python
import struct
raw = open(path, "rb").read()
m = raw.rfind(b"APK Sig Block 42")
size2 = struct.unpack("<Q", raw[m-8:m])[0]
pos = raw.rfind(struct.pack("<Q", size2), 0, m-8)  # size1
off, end = pos + 8, m - 8
while off < end:
    (sz,) = struct.unpack("<Q", raw[off:off+8])
    bid = struct.unpack("<I", raw[off+8:off+12])[0]
    print(f"pair id 0x{bid:08x} len {sz-4}")
    off += 8 + sz
```

### A3. proto 字段取证 / 全类结构 diff 脚本

`/tmp/task076_proto_forensics.py`（debug vs release proto 类逐类字段集比对，输出
per-class diff + FULL member table）与 `/tmp/task076_release_diff.py`（old vs new
release APK 全 22k+ 类 super/静态/实例字段集 diff）逻辑已完整记录于上文 P1/P3 各节，
核心均为 dexdump 文本解析：`Class descriptor` / `Superclass` / `Static fields` /
`Instance fields` 段落 → `(name, type, access)` 三元组集合比对。APK 输入路径与
备份产物均在 `/tmp/task076-forensics/`（old-release.apk = 7fadce6d…、
old-debug.apk = a8bab0f6…、release-build{2,3,4}.apk）。
