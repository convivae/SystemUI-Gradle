# WifiTrackerLib aar 过期 → 更新 (2026-07-28)

## 现象
`HotspotNetworkEntry` / `activeWifiEntries` / `disableScanning` 等 unresolved（约 22 处）。

## 根因
`libs/maven/.../WifiTrackerLib-1.0.0.aar` 里的 `classes.jar` 是 2026-07-19 生成的旧版，
缺这些新 API。AOSP `out/` 之后已重编译，含新 API。

## 解决方案
用 AOSP javac 产物替换 aar 内 `classes.jar`（保留 res/R.txt/manifest）：
```bash
NEWJAR=aosp/out/soong/.intermediates/frameworks/opt/net/wifi/libs/WifiTrackerLib/\
WifiTrackerLib/android_common/javac/WifiTrackerLib.jar
cp "$NEWJAR" /tmp/classes.jar && (cd /tmp && zip -q "<aar绝对路径>" classes.jar)
```
等价于重跑 `python3 tools/gen_aar_maven.py`（因 AOSP out 已是新版）。

## 可复现性
`libs/maven/` 被 .gitignore 忽略（本地产物）。可复现路径 = **重跑 gen_aar_maven.py**。
本次手动替换的结果与重跑脚本一致（都取当前 AOSP out 的 javac jar）。

## 错误数
275（297 → 275，−22）。无新增 unresolved 符号类型。