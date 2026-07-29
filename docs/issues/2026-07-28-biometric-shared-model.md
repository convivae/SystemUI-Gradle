# Stage 3: 补齐 biometrics/shared/model 核心领域类型 (2026-07-28)

> 承接 compose/core 顶层文件（741→724）。本次错误数 **724 → 142 (−582)**。

## TL;DR

移植时漏了 `biometrics/shared/model` 的 **9 个核心领域类型**，它们被整个生物识别子系统
广泛引用，缺失导致大面积级联 unresolved。补齐后 **724 → 142（−582）**，单次最大降幅。

## 根因

`SystemUI-core/src/.../biometrics/shared/model/` 只有 5 个文件（AuthenticationReason/
AuthenticationState/DisplayRotation/LottieCallback/SensorLocation），漏了 AOSP
`shared/biometrics/src/.../shared/model/` 的 9 个：

| 文件 | 提供 |
|------|------|
| BiometricModalities.kt | `asBiometricModality` 等 |
| BiometricModality.kt | BiometricModality 枚举 |
| BiometricUserInfo.kt | BiometricUserInfo |
| FingerprintSensor.kt | FingerprintSensor |
| FingerprintSensorType.kt | `toSensorType` |
| LockoutMode.kt | LockoutMode |
| PromptKind.kt | PromptKind |
| SensorStrength.kt | `toSensorStrength` |
| UdfpsOverlayParams.kt | UdfpsOverlayParams |

这些是 BiometricModalities/PromptKind/SensorStrength/LockoutMode 等**基础类型**，
被 domain/interactor/ui/viewmodel 数百处引用 → 缺失时级联爆炸。

## 解决方案（AGENTS §1：复制 AOSP 源码）

```bash
cp aosp/.../shared/biometrics/src/.../shared/model/{BiometricModalities,BiometricModality,
   BiometricUserInfo,FingerprintSensor,FingerprintSensorType,LockoutMode,PromptKind,
   SensorStrength,UdfpsOverlayParams}.kt SystemUI-core/src/.../biometrics/shared/model/
```
这 9 文件只依赖标准 Compose/kotlin/android + 自引用，无外部新依赖。

## 错误数演变
| 时点 | 错误数 |
|------|--------|
| compose/core 顶层文件后 | 724 |
| + 9 个 biometric model 文件 | **142** |

生物识别 unresolved（asBiometricModality/toSensorStrength/toSensorType）归零。
