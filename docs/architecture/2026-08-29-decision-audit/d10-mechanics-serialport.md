# D10 — mechanics×2 jar、SerialPortAccessDialog AAR（task073 P1，commit `e6c59677`）

status: done
判读: **符合**（例行的规则 F/tier② 落地核验，无特殊争议）

## 事实

| 产物 | AOSP 源 | soong target | res? | 交付形态 | consumer |
|---|---|---|---|---|---|
| `libs/mechanics.jar`（190 类） | `frameworks/libs/systemui/mechanics` | `mechanics`（android_library） | 无 | plain JAR | `:SystemUI-core` |
| `libs/mechanics-compose.jar`（23 类） | `frameworks/libs/systemui/mechanics/compose` | `mechanics-compose` | 无 | plain JAR | `:SystemUI-core` |
| `libs/aars/SerialPortAccessDialog.aar`（30+ locale strings） | `frameworks/base/libs/serial/accessdialog` | `SerialPortAccessDialog` | 有（全 locale res/values-*/strings.xml） | 直接 AAR（files()） | `:SystemUI-core` |

## 证据链

- 三者均为 `frameworks/**` 下产物（**非** `packages/SystemUI`）→ 规则 F/tier②，产物交付（非源码模块）。
- 17 SystemUI-core bp static_libs 列出 `SerialPortAccessDialog`、`mechanics` / `mechanics-compose`（d05 的 17 bp L550-575 段与本审计 grep 均确认）。
- mechanics / mechanics-compose 的 bp 无 `resource_dirs:`（compose bp 全文确认 21 行无 res）符
  合 "无资源→JAR" 的三层策略。
- SerialPortAccessDialog manifest 含 `<activity>` + MANAGE_SERIAL_PORTS permission，theme 引用
  SystemUI-res 的 style——manifest 必须合并进 app → 必须 AAR。
- jar 类数实测：190/23；SerialPort AAR 含 30+ locale res/values-*/strings.xml。
- AGP 单 namespace：mechanics 无 res+无 R 消费（纯代码） → jar 无碍；SerialPort 有 res → AAR。
- 三者单 consumer（仅 `:SystemUI-core`）→ Task 059 例外直接引入（AAR）/libs 根（JAR），
  均无 maven/catalog。SPEC 注释见 `tools/package_aosp_aar.py`“SerialPortAccessDialog”段。

## 备选路径

1. mechanics ×2 以 AAR 交付：无 res，不值 AAR 开销；否。
2. SerialPort 以 JAR 交付：丢 manifest/permission 合并 → app manifest 缺 activity+permission，
   运行期正确性缺失（permission/activity 不注册）；否。
3. 全部入 maven/catalog：多 consumer 才是时候；单 consumer 下有 E2 先例 → 不选。

## 判读与建议

判读：**符合**——三者形态严格按 tier② 的 res 有无划分，与 bp 结构与 manifest 内容直接对照可核。
无返工建议。

## 开放问题

- 无。
</content>
