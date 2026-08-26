# 模拟器重启 Runbook（主机重启后恢复 same-tree x86_64 运行环境）

> **背景**：2026-08-26 宿主机重启，`/tmp` 被清空，acloud goldfish 实例（含 userdata、
> overlay、部署的 APK）整体蒸发。本文档是重建整套运行环境的完整、已验证流程。
> 原始环境建于 2026-08-24（task 053），2026-08-26 由 chief 按本文档重建并验证。

## 关键事实（先说结论）

1. **实例目录在 `/tmp/acloud_gf_temp/local-goldfish-instance-1/`**——宿主机重启即丢失，
   部署态（overlay APK、disable-verity 状态、userdata）随之清零。**重启后等于全新设备**。
2. **镜像本体在 AOSP out/ 树**（持久）：`/home/conv/myspace/aosp/out/target/product/emu64x/`
   （`system-qemu.img`、`userdata-qemu.img`、`super.img` 等），重启后仍在。
3. **不需要 acloud**：`acloud create` 的 Cuttlefish preflight 缺陷仍在；直接调
   prebuilt emulator 即可（acloud 源码 `goldfish_local_image_local_instance.py`
   `_StartEmulatorProcess` 揭示了全部必要参数）。
4. **三个环境变量缺一不可**：
   - `ANDROID_PRODUCT_OUT=<emu64x>` — 镜像目录
   - `ANDROID_BUILD_TOP=/home/conv/myspace/aosp` — **缺了它 emulator 报
     "system directory could not be found"**（2026-08-26 实测踩坑）
   - `ANDROID_TMP=<instance dir>` — AVD 运行时信息目录
5. **`-stdouterr-file` 与 `-logcat-output` 的目标文件必须预先 `touch`**——
   emulator 不会自己创建 `-stdouterr-file`（acloud 代码注释明说），缺了直接退：
   `cannot open .../kernel.log`。
6. **`VerifiedBootParams.textproto` 不要追加 `verifiedbootstate=orange`**：
   该文件会被 AOSP 重构建重新生成；2026-08-26 实测追加后 bootconfig 报
   `Value is redefined at 1715` 且 kernel 在 `Run /init` 处反复重启（boot loop）。
   恢复 `.bak-non-mixed` 备份后立即正常。且实测 `ro.boot.verifiedbootstate=orange`
   **本来就是镜像自带属性**（userdebug eng 构建），无需 textproto 注入。
   （若文件状态不明：`cp VerifiedBootParams.textproto.bak-non-mixed VerifiedBootParams.textproto`）
7. **启动后 verity 是 enabled**（全新 userdata）→ 部署 APK 前必须走一遍
   `disable-verity` 链（见下）。

## 启动步骤（已验证，2026-08-26）

前置：当前 shell 需在 `kvm` 组（`id` 含 `991(kvm)`；持久成员已配置，新登录即生效，
**不需要 sudo**）。磁盘 ≥10 GiB；内存：模拟器常驻 ~4.5 GiB RSS，注意全机预算。

```bash
# 1. 重建实例目录并预创建日志文件（关键，见事实 5）
mkdir -p /tmp/acloud_gf_temp/local-goldfish-instance-1
touch /tmp/acloud_gf_temp/local-goldfish-instance-1/kernel.log \
      /tmp/acloud_gf_temp/local-goldfish-instance-1/logcat.txt

# 2. 启动（建议在独立终端/herdr tab 中前台运行；bash 工具后台拉起会随 shell 退出死掉）
cd /tmp/acloud_gf_temp/local-goldfish-instance-1
ANDROID_PRODUCT_OUT=/home/conv/myspace/aosp/out/target/product/emu64x \
ANDROID_BUILD_TOP=/home/conv/myspace/aosp \
ANDROID_TMP=/tmp/acloud_gf_temp/local-goldfish-instance-1 \
/home/conv/myspace/aosp/prebuilts/android-emulator/linux-x86_64/emulator \
  -verbose -show-kernel -read-only -writable-system \
  -ports 5554,5555 \
  -logcat-output /tmp/acloud_gf_temp/local-goldfish-instance-1/logcat.txt \
  -stdouterr-file /tmp/acloud_gf_temp/local-goldfish-instance-1/kernel.log \
  -no-window
```

herdr 启动方式（本项目实际使用）：

```bash
herdr tab create --workspace w2 --cwd /tmp/acloud_gf_temp/local-goldfish-instance-1 --label emulator
herdr pane run <pane> "<上面整条命令>"
```

```bash
# 3. 等待并验证（~1-2 分钟；kernel 阶段 logcat.txt 为 0 行是正常的）
adb -s emulator-5554 wait-for-device
adb -s emulator-5554 shell getprop sys.boot_completed   # 等到 1
adb -s emulator-5554 shell 'getprop ro.kernel.qemu; getprop ro.build.fingerprint; getprop ro.boot.verifiedbootstate'
# 期望: 1 / Android/sdk_phone64_x86_64/emu64x:Baklava/MAIN/eng.conv:userdebug/test-keys / orange
```

**健康判据**：qemu 进程 CPU 100%+ 是正常启动态；kernel.log 时间戳持续推进、
`Run /init` 只出现一次。若 `Run /init` 反复出现（时间戳归零重写）= boot loop，
先查 bootconfig `redefined` 报错（见事实 6）。

## 启动后恢复部署（fresh userdata 必走）

```bash
adb -s emulator-5554 root
adb -s emulator-5554 disable-verity
adb -s emulator-5554 reboot
adb -s emulator-5554 wait-for-device && sleep 10
adb -s emulator-5554 root
adb -s emulator-5554 shell 'su 0 mount -o remount,rw /system_ext'
# 之后按标准 staged 部署规程（push → staged cp → sha 门禁 → 原子 mv → 权限 → 清缓存 → reboot）
# 见 PITFALLS §14 与 docs/issues/2026-08-25-debug-runtime-pass-gate-suite.md
```

## 回退/排障速查

| 症状 | 原因 | 处置 |
|---|---|---|
| `system directory could not be found` | 缺 `ANDROID_BUILD_TOP` | 补环境变量 |
| `cannot open .../kernel.log` | `-stdouterr-file` 目标不存在 | 先 `touch` |
| kernel 反复 `Run /init` + bootconfig `redefined` | textproto 被追加了重复参数 | 恢复 `.bak-non-mixed` |
| bash 工具后台启动后进程消失 | 工具 shell 退出带走子进程 | 用 herdr tab 前台跑 |
| 重启后部署的 APK 没了 | `/tmp` 实例蒸发 + verity 回 enabled | 按"恢复部署"重走 |
| 画面查看 | headless 无窗口 | `scrcpy -s emulator-5554` |
