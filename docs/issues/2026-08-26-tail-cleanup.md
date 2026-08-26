# 2026-08-26 — 尾账清理：fix_r_imports 复判删除 + install_keystore.sh → .py

> Task 067 worker day record (rule D). 两个独立尾账，一个任务内完成。
> AOSP tree: `/home/conv/myspace/aosp`. 不跑 Gradle；`uv run pytest tools/tests/ -q` 为验证。

## 背景

Task 062 工具脚本审计留下两个尾账：

1. `tools/fix_r_imports_to_res.py` — 审计判 **UNCERTAIN**（自声明 disabled，等 R-namespace
   梳理后复判）。Task 063 明确将其排除在删除范围外，保留待复判。
2. `tools/install_keystore.sh` — 审计判 **KEEP-with-fix**（ADR 0002 .sh→.py 转换欠账）。

Task 067（用户 2026-08-26 批准）一次性收掉这两个尾账。

## 工作项 1：fix_r_imports_to_res.py 复判 + 删除

### 脚本前提（来自其 docstring）

> AOSP SystemUI 用 `import com.android.systemui.res.R`（res 子包），共 523 处。
> 我们 Gradle 改造时错误统一改为 `import com.android.systemui.R`，共 1062 处。
> 策略：把所有 `com.android.systemui.R` 改回 `com.android.systemui.res.R`（1:1 对齐 AOSP）。

脚本自 2026-07-30 起声明 DEPRECATED/disabled（运行后错误数 66→78，因 AGP R 类生成在
`namespace` 下导致部分 R 字段不可见），从未被启用。

### 复判验证（独立交叉印证，非重复 check_source_alignment）

**1. R import 分布直接对比（项目源码 vs AOSP）**

```bash
# AOSP src
grep -rh "^import com\.android\.systemui\.res\.R"  /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/src/ | wc -l  → 922
grep -rhE "^import com\.android\.systemui\.R$"     .../aosp/.../src/ | wc -l  → 0   # "wrong" form
grep -rhE "^import com\.android\.systemui\.R\s+as" .../aosp/.../src/ | wc -l  → 0   # alias form

# PROJECT SystemUI-core/src
grep -rh "^import com\.android\.systemui\.res\.R"  SystemUI-core/src/ | wc -l  → 922
grep -rhE "^import com\.android\.systemui\.R$"     SystemUI-core/src/ | wc -l  → 0
grep -rhE "^import com\.android\.systemui\.R\s+as" SystemUI-core/src/ | wc -l  → 0
```

**结论**：项目源码与 AOSP 的 R import 分布**完全一致**（922 / 0 / 0 三项全等）。
脚本前提（"项目有 1062 处 wrong-form `import com.android.systemui.R` 待修"）**已被证伪**——
零处 wrong-form import 存在。源码已按规则 S/C 1:1 对齐 AOSP，覆盖了任何早期 wrong-form。

**2. check_source_alignment.py 权威汇总（交叉印证）**

```bash
python3 tools/check_source_alignment.py --summary
```

输出（节选）：
```
[MISSING]   ... : 0
[MISPLACED] ... : 0
[EXTRA]     ... : 0
[MODIFIED]  ... : 1   # 源码（pre-existing，与 R import 无关——直接 grep 计数全等）
[RES-MISS]  ... : 0
[RES-EXTRA] ... : 0
[RES-MODIFIED] ... : 86
```

MISSING/MISPLACED/EXTRA = 0/0/0（brief 所指 "0-0-0"）→ 源码文件集完整且 owner 正确，
隐含 R import 已对齐。1 个 MODIFIED 源码文件与 R import 无关（若为 R import 差异，上述
直接 grep 计数不会全等）。86 RES-MODIFIED 为资源字节差异，与本脚本无关。

**3. 脚本无其他消费者**

```bash
grep -rn "fix_r_imports" --include="*.md" --include="*.py" --include="*.sh" --include="*.kts" --include="*.toml" .
```

引用全部为文档/审计记录，**无代码消费者**（无 .py/.kts/.toml 调用）：
- `tools/fix_r_imports_to_res.py` 自身 docstring（随脚本删除）
- `docs/superpowers/plans/2026-08-06-soong-gradle-apk-policy-checkpoint.md:101`（唯一活动指令性引用 → 加"已删除"注记）
- `docs/orchestration/log.md:270`（orchestration 日志，append-only 历史，不动）
- `docs/orchestration/tasks/063-*.md:19`（task 063 brief，历史，不动）
- `docs/architecture/2026-08-26-tools-scripts-inventory-audit.md`（task 062 审计快照，历史记录，不动；其 UNCERTAIN 判定由本任务复判终结）
- `docs/issues/2026-08-26-libs-artifact-inventory-audit.md:66`（同日审计 issue，历史，不动）

### 操作

- 删除 `tools/fix_r_imports_to_res.py`
- `docs/superpowers/plans/2026-08-06-soong-gradle-apk-policy-checkpoint.md:101` 加
  `# 已删除 (task 067, 2026-08-26)` 注记（不改写历史内容）

## 工作项 2：install_keystore.sh → install_keystore.py

### 现状（.sh 命令链）

`tools/install_keystore.sh` 把 AOSP `build/target/product/security/platform.pk8` +
`platform.x509.pem` 转成 `keystore/platform.keystore`（tracked，app debug/release 签名消费）：

1. `openssl pkcs8 -inform DER -nocrypt -in platform.pk8 -out platform.key.pem`（pk8 DER → PEM 私钥）
2. `cp -f platform.x509.pem platform.crt.pem`（已是 PEM，复制以统一命名）
3. `openssl pkcs12 -export -in platform.crt.pem -inkey platform.key.pem -out platform.p12 -password pass:android -name AndroidDebugKey`
4. `keytool -importkeystore -deststorepass android -destkeystore platform.keystore -srckeystore platform.p12 -srcstoretype PKCS12 -srcstorepass android`
5. `rm -f` 清理中间产物（仅保留 .keystore）

### 转换

- 新建 `tools/install_keystore.py`，逻辑等价：
  - openssl/keytool 经 `subprocess.run([...], check=True)`（ADR 0002 迁写原则）
  - step 2 的 `cp -f` 用 `shutil.copyfile`（Python 原生，非 openssl/keytool 链，更干净；产物字节等价）
  - 路径用 `pathlib.Path`
  - `--aosp-root` 默认走 `tools/aosp_paths.py`（用户单源规则）；security dir = `aosp_root/build/target/product/security`
  - `--key-name`（默认 `platform`，对应 .sh 的 `KEY_NAME`）
  - `--dest`（默认 `<project>/keystore`，对应 .sh 的 `SCRIPT_DIR/../keystore`）
  - 错误用异常（FileNotFoundError），不用 `set -e`
  - 幂等：重跑覆盖输出（与 .sh 一致）
- 删除 `tools/install_keystore.sh`
- `app/build.gradle.kts:50` 注释 `// tools/install_keystore.sh.` → `// tools/install_keystore.py.`
  （删除 .sh 后该注释指向已删文件；一字之改的准确性修正，直接由本次删除引起，非 scope 扩展；
  非 red-line 区——非 source/res、非 rule 文件、非 version matrix、非 module boundary、非 build bypass）
- 更新 `docs/adr/0002-tools-scripts-only-python.md` 欠账记录（install_keystore.sh → 已转换 task 067）
- 新增 `tools/tests/test_install_keystore.py`：参数解析 + aosp_paths 集成 + 命令链结构 +
  缺失输入文件报错（不强求覆盖 openssl 链本身，仿 `test_package_compilelib_jars.py` 模式）

### 验证（keystore 内含时间戳，逐字节一致不必然成立）

纪律：**不得覆盖** `keystore/platform.keystore`（tracked 基准）。生成到临时目录对比：

1. `python3 tools/install_keystore.py --dest /tmp/ks067` 生成新 keystore
2. `keytool -list -keystore` 对比新旧：条目数、alias、证书 SHA-256 指纹必须一致
3. 证书指纹一致即通过；若碰巧逐字节一致，如实记录

## 验证结果

### 工作项 1（fix_r_imports 删除）

- **R import 分布直接对比**：AOSP src 与项目 `SystemUI-core/src` 均为
  `922` × `import com.android.systemui.res.R` / `0` × wrong-form / `0` × alias ——
  三项全等。脚本前提（1062 处 wrong-form 待修）证伪。
- **check_source_alignment.py --summary**：MISSING/MISPLACED/EXTRA = 0/0/0（交叉印证）。
  1 MODIFIED 源码 + 86 RES-MODIFIED 为 pre-existing 字节差异，与 R import 无关
  （若为 R import 差异，直接 grep 计数不会全等）。
- **无代码消费者**：grep 全仓 `fix_r_imports` 仅文档/审计引用，无 .py/.kts/.toml 调用。
- **操作**：`git rm tools/fix_r_imports_to_res.py`；plan doc 第 101 行加
  `# 已删除 (task 067, 2026-08-26)` 注记（历史内容不改写）。

### 工作项 2（install_keystore.sh → .py）

- **新脚本**：`tools/install_keystore.py`，`python3 -m py_compile` OK。
- **逻辑等价验证**（生成到 `/tmp/ks067`，**未覆盖** tracked 基准）：

  | 属性 | tracked (.sh, Jul 16) | new (.py, Aug 26) | 一致 |
|---|---|---|---|
| Keystore type | PKCS12 | PKCS12 | ✅ |
| Entry count | 1 | 1 | ✅ |
| Alias | androiddebugkey | androiddebugkey | ✅ |
| Entry type | PrivateKeyEntry | PrivateKeyEntry | ✅ |
| Cert SHA-256 | C8:A2:E9:BC:...:2A:B8 | C8:A2:E9:BC:...:2A:B8 | ✅ |
| Cert SHA-1 | 27:19:6E:...:3D:FA | 27:19:6E:...:3D:FA | ✅ |
| Serial | b3998086d056cffa | b3998086d056cffa | ✅ |

  证书 SHA-256 指纹**完全一致** → 通过。仅 embedded creation date 不同
  （Jul 16 vs Aug 26）→ 文件字节在 byte 119 处差异（sha256 不同），如 brief 预期。
  tracked `keystore/platform.keystore` 未动（sha256 仍 `2d322007...`）。
  注：实际产物为 PKCS12（keytool 现代默认），与 tracked 基准一致；.sh docstring
  的 "JKS" 措辞为历史 stale，新 .py docstring 已更正为 PKCS12。
- **删除**：`git rm tools/install_keystore.sh`。
- **app/build.gradle.kts:50**：注释 `// tools/install_keystore.sh.` →
  `// tools/install_keystore.py.`（删除 .sh 后该注释指向已删文件；一字之改的准确性
  修正，直接由本次删除引起；非 red-line 区）。
- **ADR 0002**：欠账记录更新为 "install_keystore.sh 已转换为 install_keystore.py
  （Task 067），原 .sh 已删除"。
- **测试**：`tools/tests/test_install_keystore.py`（6 用例：security_dir override/env、
  build_command_chain 3 命令顺序与参数、无 cp、缺失输入报 FileNotFoundError 且不调
  openssl、默认 dest 路径）。

### 全量测试

```bash
uv run pytest tools/tests/ -q
→ 282 passed, 4 warnings, 102 subtests passed in 70.35s
```

4 warnings 均为 pre-existing（test_build_sysuisdk / test_package_aconfig_jars 的
zipfile duplicate-name 检测，与本任务无关）。本任务新增 6 用例全绿。

### Gradle

未运行（本任务不触碰构建输入；brief 明确 "不跑 Gradle"）。

## 待解决 / 范围外

- `docs/architecture/2026-08-26-tools-scripts-inventory-audit.md` 仍把 fix_r_imports 列为
  UNCERTAIN（task 062 审计快照，历史记录，本任务不动）。其复判结论已由本 issue 记录。
  若 chief 希望同步更新该审计快照的 verdict，可作为后续小任务。
- `docs/orchestration/log.md` / `docs/orchestration/tasks/063-*.md` 等历史引用不动（append-only / 历史 brief）。
