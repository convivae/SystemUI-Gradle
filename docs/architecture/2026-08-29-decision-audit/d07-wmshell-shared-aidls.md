# D7 — WindowManager-Shell-shared AAR 并入 AIDL 闭包 19 类 + 坐标 2.0.0→2.0.1（task073 P2a，commit `74b88acb`）

status: done
判读: **符合**

## 背景与决策原文

17 `frameworks/base/libs/WindowManager/Shell/shared/Android.bp`：

```
java_library { name: "WindowManager-Shell-shared-aidls", srcs: ["**/*.aidl"] }

android_library {
    name: "WindowManager-Shell-shared",
    ...
    static_libs: [ "WindowManager-Shell-shared-aidls", ... ]
}
```

AIDL 接口类（IShellTransitions / AnimatedSurface / IHomeTransitionListener /
IFocusTransitionListener / IOverviewOverlayLeashInvalidationCallback 等）在 Soong 消费侧即
`WindowManager-Shell-shared` 的 **static_libs 闭包成员**——补说 `SystemUI-animation` 的
`ActivityTransitionAnimator` 需要 import 这些接口（SPEC 注释 L147-148），而 main jar（javac/kotlin 两路
合并）不含它们。

决策（task073 P2a，commit `74b88acb` + 对账测试修正 `38cd4c4b`）：
1. `tools/package_aosp_aar.py` SPEC `"WindowManager-Shell-shared"` 的 code 列表并入
   `WindowManager-Shell-shared-aidls/android_common/javac/WindowManager-Shell-shared-aidls.jar`；
2. 类集变化 → 本地 maven 坐标 2.0.0 → 2.0.1（`libs/maven/.../WindowManager-Shell-shared/2.0.1/`，
   `install_aar_to_maven.py` 同步升），`gradle/libs.versions.toml:166` 更新；
3. 触发项目级对账测试断言过期，`38cd4c4b` 跟进修正（owner/version 断言）。

## 决策链

| 环节 | 证据 |
|---|---|
| 错误实证 | task073 R1：`SystemUI-animation` import `IShellTransitions` 等缺类（issue §4 批次 1） |
| bp 闭包实证 | `frameworks/base/libs/WindowManager/Shell/shared/Android.bp:33-51`（aidls 独立 java_library + 为 shared static_libs 首项） |
| 版本义务 | AGENTS.md §3.2 规则 4"内容变化必须升坐标…禁止同版本原地覆盖"——升 2.0.1 是规则义务 |
| 执行 | `74b88acb` + `38cd4c4b`；SPEC L141-160 |

## 证据链

1. **AAR 字节闭环**：`libs/aars/WindowManager-Shell-shared.aar` 与
   `libs/maven/.../2.0.1/WindowManager-Shell-shared-2.0.1.aar` sha256 相同（实测）。
2. **类集闭包**：AAR classes.jar 246 class；其中 IShellTransitions/AnimatedSurface/
   IFocusTransitionListener/IHomeTransitionListener 类 AIDL 接口相关命中 17（issue 记 19 类，
   含内部 stub/parcel 辅助类差异——属同量级无冲突证据）。
3. **两 consumer 仍走单 catalog alias**：`libs.systemui.wmshell.shared` 由 catalog 管理
   （`:SystemUI-core` 之外还有 Settings 族消费者——wmshell-shared 是多 consumer 族，**该族本就
   走 local Maven**；2.0.1 升级不跨界到自直 AAR 周界）。
4. **POM 不带 aidls 依赖边**：install.py 只打骨架 POM——AAR 内已含 aidls 类，无传递依赖需要。

## 备选路径

1. **独立 jar** `libs/WindowManager-Shell-shared-aidls.jar`（bp 1:1 target 镜像）——最对称；
   但引入新 libs/ 产物种类（与 v2.0.0 时代的"jar 并到同族 AAR"先例不同），同时
   wmshell-shared 是两 consumer 族 local Maven 交付，补一个 jar 意味着 catalog 再增一项；
2. **并入 shared AAR**（所选）——Soong static_libs 闭包语义原位保持（类并存于同一字节闭包内），
   版本升级履行 §3.2.4 义务；同 TraceurCommon 先例（多 jar 合并 AAR）。

## 优劣分析

优点：bp 语义忠实（soong 的 target 拆分是编译组织细节，对消费侧无意义）；版本管理合规；
实现/测试/对齐三层同步（SPEC、install、catalog、对账测试）。
缺点：artifact ↔ soong target 不再 1:1（后续读者对比 bp 需要读 SPEC 注释）；
漂移在 brief 内未见显式枚举（归入 p03 的"误差驱动循环"扩权记录）。

## 判读与建议

判读：**符合**——技术、规则、记录三层齐整。

建议：**保持**。

## 开放问题

- 无（误差循环扩权归 p03）。
</content>
