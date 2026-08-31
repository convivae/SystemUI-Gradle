# Task 077 — C5 部署通道：B3 镜像侧 super 留余量（复刻 16 耐久形态）

**Phase**: C（B3 决策落地）
**起源**: task075 结论——/data scratch 运行态可行但 reboot 后 AOSP 启动清理删空 → 17 emu64x 缺 16 时代的 super 余粮
**优先级**: 高（C5 双 runtime 门持久部署通道的唯一一劳永逸解法）

---

## 背景与目标

- **16 时代机制**（task075 已溯源）：super 物理大小固定 → 16 system 装完仍留出 261MB 余量 → 首次 `disable-verity` 时 fs_mgr `CreateDynamicScratch` 把全部余量切给 scratch 逻辑分区（f2fs）→ **super 内的逻辑分区，first-stage 自然可映射 → 耐久** → 164MB debug APK 放得下、部署持久
- **17 现状**：super 几乎被灌满 → 动态 scratch 只剩 87MB / 可用 40MB（163MB→194MB 的 17 debug 更放不进）
- **goal**：给 17 emu64x image 增加 super 余量（目标 ≥ 512MB，参考 16 的 261MB + 安全富余），重建镜像 → 16 形态的"原生耐久部署"能力在 17 重现

## P1 诊断（screening，<30 分钟）
1. **定位 super 大小/余量的配置点**（只改一个，不扩散）：
   - `device/generic/goldfish/board/emu64x/BoardConfig.mk`（及 emu64a 同目录对照）里的 `BOARD_SUPER_PARTITION_SIZE`；17 vs 16 是否变了
   - 各子分区 `BOARD_*_PARTITION_SIZE` 是否自 16 增长（挤占 super 空间）
   - `PRODUCT_VIRTUAL_AB_*` / virtual A/B 相关的 overhead 是否吞掉余量
   - **用 git log 对照 16→17 配置变化**（AOSP 树是完整 git fetch；示例：`cd /home/conv/myspace/aosp/device/generic/goldfish && git log --oneline --all -- board/emu64x/ | head -30`）
2. **量化当前缺口**：`lpdump --slot=0 super*` 或 `dmctl dump` 读 super metadata，确认当前 free bytes 精确值
3. 输出：你定下来的**单行改动方案**（预改验证 → 我批准后执行重建）

## P2 重建 + 验收
1. 改动 + **完整 AOSP 增量构建**（切勿全量 dist：`lunch emu64x-userdebug` 后 `m -j$(nproc)`），产物目标：`out/target/product/emu64x/system*.img/vbmeta`/`super*`
2. 按 runbook `docs/issues/2026-08-26-emulator-relaunch-runbook.md` 重建实例（`adp kill-server` → 走完整流程）
3. **验收全链**：
   - 模拟器在新镜像下 boot 完成（`boot_completed=1`，verified state normal）
   - `disable-verity` → reboot → 观察 `/mnt/scratch` 大小 ≥ 512MB
   - **耐久验证**：把任意 ≥50MB 文件放到 overlay（示例：重绑临对 tmp SystemUI.apk 副本到 /system_ext/priv-app/SystemUI）→ `reboot` → 重验 sha 持存（不是 stock）
   - verifybootstate=orange；dmesg 无新 FATAL
4. **不做 runtime 门**（runtime 验证由 chief 合并后统一收尾）

## 纪律
- **AOSP tree 只允许改动一行 config**（重拨 16 形态），但须：
  - 每一次改动构成 git 独立 commit（含完整原因记录）
  - 同一时间只允许一处 pending 改动；完成或回滚后才允许下一处
  - 不顺手修其他任何配置——一次只解一个问题
- 构建 OOM 时先试 `m -j8`；再退 `-j4`；如实报告
- 模拟器 boot 卡 > 90 秒 → 停报；不要用 `-wipe-data` 绕过（该 flag 在本项目禁用，它会掩盖真实问题）
- issue 文档每 phase 完即落盘（防上下文压缩）
- **不 push**（任何 repo），chief 复核
- **产物留痕**：super.img sha、lpdump 快照、config diff、build log 关键行全部记录到 issue

## 产出
1. 单行改动 config diff（含 commit hash 和理由）
2. 重建后的 super.img sha + `lpdump` 余量证据
3. 耐久部署验证记录（跨重启 sha 持存）
4. runbook 何时失效的更新说明（若 runbook 需更新）
5. issue `docs/issues/2026-09-01-c5-emulator-super-slack.md` 全量记录 + 简报
