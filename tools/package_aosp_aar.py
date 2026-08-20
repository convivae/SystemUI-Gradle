#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
严格直接-AAR 打包器：把 AOSP Soong 的 javac + kotlin JAR 与原始 res 字节合并为一个 AAR。

规则（见 AGENTS.md 规则 R / ADR 0001）：
  - 只合并显式指定的 javac 和 kotlin JAR；
  - 跳过目录 entry，仅允许重复 META-INF/MANIFEST.MF；
  - 其余任何重复 entry → DuplicateEntryError；
  - 拒绝 basename 为 R.class 或以 R$ 开头的输入类（AGP 会从 res/R.txt 重新生成 R）；
  - res/ 字节级复制，不编辑；
  - AndroidManifest.xml 与 R.txt 原样复制；
  - 写出确定性 ZIP（entry 名排序）；
  - 不生成 POM，不触碰 libs/maven/。

默认产物：libs/aars/animationlib.aar
"""

import argparse
import sys
import zipfile
from io import BytesIO
from pathlib import Path

AOSP_ROOT = Path("/home/conv/myspace/aosp")
SOONG_DIR = AOSP_ROOT / "out/soong/.intermediates"

ANIMATIONLIB_DIR = AOSP_ROOT / "frameworks/libs/systemui/animationlib"
ANIMATIONLIB_SOONG = SOONG_DIR / "frameworks/libs/systemui/animationlib/animationlib/android_common"

TRACEUR_DIR = AOSP_ROOT / "packages/apps/Traceur"
TRACEUR_SOONG = SOONG_DIR / "packages/apps/Traceur"

DEFAULT_OUTPUT = Path("libs/aars/animationlib.aar")

def _discover_settingslib_code_jars() -> list:
    """自动发现 SettingsLib 主 target + 全部 static_libs 子模块的 javac JAR。

    Soong 的 android_library static_libs 是独立编译单元，javac JAR 只含主 target
    的类。static_libs 子模块的类在 dex 阶段合并进最终 APK。为模拟此语义，
    需把主 target 与所有 static_libs 子模块的 javac JAR 合并到 classes.jar。
    """
    base = SOONG_DIR / "frameworks/base/packages/SettingsLib"
    jars = []
    for jar in sorted(base.rglob("*/android_common/javac/*.jar")):
        s = str(jar)
        if "turbine" in s or "aconfig" in s or "flags_lib" in s:
            continue
        jars.append(jar)
    return jars


# Declarative artifact configs（canonical inputs，见 artifact-recovery 计划）
CONFIGS = {
    "animationlib": {
        "code": [ANIMATIONLIB_SOONG / "javac" / "animationlib.jar",
                 ANIMATIONLIB_SOONG / "kotlin" / "animationlib.jar"],
        "res": [ANIMATIONLIB_DIR / "res"],
        "manifest": ANIMATIONLIB_DIR / "AndroidManifest.xml",
        "rtxt": ANIMATIONLIB_SOONG / "R.txt",
        "output": "libs/aars/animationlib.aar",
    },
    "WifiTrackerLib": {
        "code": [SOONG_DIR / "frameworks/opt/net/wifi/libs/WifiTrackerLib/WifiTrackerLib/android_common/javac/WifiTrackerLib.jar"],
        "res": [AOSP_ROOT / "frameworks/opt/net/wifi/libs/WifiTrackerLib/res"],
        "manifest": AOSP_ROOT / "frameworks/opt/net/wifi/libs/WifiTrackerLib/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/opt/net/wifi/libs/WifiTrackerLib/WifiTrackerLibRes/android_common/R.txt",
        "output": "libs/aars/WifiTrackerLib.aar",
    },
    "iconloader": {
        # javac JAR (59 Java classes) + kotlin JAR (16 Kotlin classes, 如 ThemedBitmap/
        # IconThemeController/mono.ThemedIconDrawable) 合并（先例：WM-Shell javac+kotlin）
        "code": [
            SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader/android_common/javac/iconloader.jar",
            SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader/android_common/kotlin/iconloader.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/libs/systemui/iconloaderlib/res"],
        "manifest": AOSP_ROOT / "frameworks/libs/systemui/iconloaderlib/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader/android_common/R.txt",
        "output": "libs/aars/iconloader.aar",
    },
    "SettingsLib": {
        # 主 target + 全部 static_libs 子模块 javac JAR（780 classes）
        # Task 040：追加两个 owning Kotlin 产物——主 SettingsLib Kotlin（372 类，
        # 含 RestrictedPreferenceHelperProvider 等）+ DeviceStateRotationLock Kotlin
        # （1 类 PosturesHelper，主 SettingsLib 的 direct static_libs）→ 1153 类。
        # Theme 的 Kotlin 代码归 SettingsLibSettingsTheme AAR，不得并入。
        "code": _discover_settingslib_code_jars() + [
            SOONG_DIR / "frameworks/base/packages/SettingsLib/SettingsLib/android_common/kotlin/SettingsLib.jar",
            SOONG_DIR / "frameworks/base/packages/SettingsLib/DeviceStateRotationLock/"
                       "SettingsLibDeviceStateRotationLock/android_common/kotlin/"
                       "SettingsLibDeviceStateRotationLock.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/SettingsLib/android_common/R.txt",
        "output": "libs/aars/SettingsLib.aar",
    },
    "WindowManager-Shell": {
        # javac JAR (Java classes) + kotlin JAR (Kotlin classes, 如 HasWMComponent) 合并；
        # Task 037：再并入两个 proto static_libs 的 Soong javac 产物（bp L188-189）——
        # nano proto（bp L138, 4 类）+ lite proto（bp L148, 36 类），共 1888 类
        "code": [
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/javac/WindowManager-Shell.jar",
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/kotlin/WindowManager-Shell.jar",
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell-proto/android_common/javac/WindowManager-Shell-proto.jar",
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell-lite-proto/android_common/javac/WindowManager-Shell-lite-proto.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/base/libs/WindowManager/Shell/res"],
        "manifest": AOSP_ROOT / "frameworks/base/libs/WindowManager/Shell/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/R.txt",
        "output": "libs/aars/WindowManager-Shell.aar",
        "exclude_prefixes": [
            "com/android/wm/shell/shared/IFocusTransitionListener",
            "com/android/wm/shell/shared/IHomeTransitionListener",
            "com/android/wm/shell/shared/IShellTransitions",
        ],
        "reject_sysui": True,
    },
    "WindowManager-Shell-shared": {
        # WM-Shell 的 static_libs 子模块(ShellTransitions/TransitionUtil/PhysicsAnimator 等)
        # javac JAR (Java classes) + kotlin JAR (Kotlin classes, Soong 命名是 kotlin/ 不是 kotlinc/) 合并
        "code": [
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/shared/WindowManager-Shell-shared/android_common/javac/WindowManager-Shell-shared.jar",
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/shared/WindowManager-Shell-shared/android_common/kotlin/WindowManager-Shell-shared.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/base/libs/WindowManager/Shell/shared/res"],
        "manifest": AOSP_ROOT / "frameworks/base/libs/WindowManager/Shell/shared/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/shared/WindowManager-Shell-shared/android_common/R.txt",
        "output": "libs/aars/WindowManager-Shell-shared.aar",
        "reject_sysui": True,
    },
    "LowLightDreamLib": {
        # frameworks/base/libs/dream/lowlight：TruncatedInterpolator 等在 kotlin JAR
        "code": [
            SOONG_DIR / "frameworks/base/libs/dream/lowlight/LowLightDreamLib/android_common/javac/LowLightDreamLib.jar",
            SOONG_DIR / "frameworks/base/libs/dream/lowlight/LowLightDreamLib/android_common/kotlin/LowLightDreamLib.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/base/libs/dream/lowlight/res"],
        "manifest": AOSP_ROOT / "frameworks/base/libs/dream/lowlight/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/libs/dream/lowlight/LowLightDreamLib/android_common/R.txt",
        "output": "libs/aars/LowLightDreamLib.aar",
        "reject_sysui": True,
    },
    "SettingsLibColor": {
        # SettingsLib/Color：res-only 模块（无 srcs），package com.android.settingslib.color
        # 47 个 color 资源（settingslib_color_blue400 等），被 SettingsLibIllustrationPreference 依赖
        # SystemUI 源码 SideFpsOverlayViewModel.kt 直接引用 com.android.settingslib.color.R
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/Color/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/Color/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/Color/SettingsLibColor/android_common/R.txt",
        "output": "libs/aars/SettingsLibColor.aar",
    },
    "SettingsLibSettingsTheme": {
        # SettingsLib/SettingsTheme：独立 Soong android_library target（res + src）。
        # Task 040：加入 owning Kotlin 产物（15 类，含 GroupSectionDividerMixin/
        # SettingsThemeHelper），代码归本 AAR 交付，不得并入主 SettingsLib AAR；
        # res 补齐 SettingsTheme/res 资源（89 个同路径文件不得与 SettingsLib/res 合并，
        # 保持 Soong target 边界，Task 013）
        "code": [
            SOONG_DIR / "frameworks/base/packages/SettingsLib/SettingsTheme/"
                       "SettingsLibSettingsTheme/android_common/kotlin/"
                       "SettingsLibSettingsTheme.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/SettingsTheme/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/SettingsTheme/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/SettingsTheme/SettingsLibSettingsTheme/android_common/R.txt",
        "output": "libs/aars/SettingsLibSettingsTheme.aar",
    },
    # ↓↓↓ Task 015（B2 可达性最小集）：7 个 SettingsLib per-target res-only AAR。
    # 代码类已由 SettingsLib.aar 的 static_libs javac 合并交付，这里只补各自 res；
    # AAR 经 SettingsLib POM 传递依赖接线（ADR 0005），consumer 不新增依赖行。
    "SettingsLibSelectorWithWidgetPreference": {
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/SelectorWithWidgetPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/SelectorWithWidgetPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/SelectorWithWidgetPreference/SettingsLibSelectorWithWidgetPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibSelectorWithWidgetPreference.aar",
    },
    "SettingsLibRestrictedLockUtils": {
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/RestrictedLockUtils/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/RestrictedLockUtils/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/RestrictedLockUtils/SettingsLibRestrictedLockUtils/android_common/R.txt",
        "output": "libs/aars/SettingsLibRestrictedLockUtils.aar",
    },
    "SettingsLibActionButtonsPreference": {
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/ActionButtonsPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/ActionButtonsPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/ActionButtonsPreference/SettingsLibActionButtonsPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibActionButtonsPreference.aar",
    },
    "SettingsLibProgressBar": {
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/ProgressBar/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/ProgressBar/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/ProgressBar/SettingsLibProgressBar/android_common/R.txt",
        "output": "libs/aars/SettingsLibProgressBar.aar",
    },
    "SettingsLibTwoTargetPreference": {
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/TwoTargetPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/TwoTargetPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/TwoTargetPreference/SettingsLibTwoTargetPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibTwoTargetPreference.aar",
    },
    "SettingsLibLayoutPreference": {
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/LayoutPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/LayoutPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/LayoutPreference/SettingsLibLayoutPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibLayoutPreference.aar",
    },
    "SettingsLibAdaptiveIcon": {
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/AdaptiveIcon/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/AdaptiveIcon/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/AdaptiveIcon/SettingsLibAdaptiveIcon/android_common/R.txt",
        "output": "libs/aars/SettingsLibAdaptiveIcon.aar",
    },
    "setupcompat": {
        # external/setupcompat android_library（含 res；AOSP SettingsLib 经 setupdesign→setupcompat
        # 传递获得 compile classpath）。package com.google.android.setupcompat；
        # WizardManagerHelper.SETTINGS_SECURE_USER_SETUP_COMPLETE / isUserSetupComplete 等。
        "code": [SOONG_DIR / "external/setupcompat/setupcompat/android_common/javac/setupcompat.jar"],
        "res": [AOSP_ROOT / "external/setupcompat/main/res"],
        "manifest": AOSP_ROOT / "external/setupcompat/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "external/setupcompat/setupcompat/android_common/R.txt",
        "output": "libs/aars/setupcompat.aar",
    },
    # ↓↓↓ Task 038（R8 Batch 4C）：Traceur 双 AAR（直接 AAR，ADR 0001）。
    # 依据 packages/apps/Traceur/Android.bp：SystemUI-core static_libs 含
    # TraceurCommon + Traceur-res； retiring libs/TraceurCommon.jar / libs/traceur-res-R.jar。
    "TraceurCommon": {
        # android_library "TraceurCommon"（srcs src_common）+ static_libs
        # perfetto_config_java_protos（并入 proto static_libs，先例：WM-Shell Task 037）：
        # 15 类（com/android/traceur/）∪ 625 类（perfetto/protos/）= 640 类不相交并集。
        # 无 res；manifest AndroidManifest-common.xml 合并 CONTROL_UI_TRACING 等 5 权限
        # （AOSP 靠它把权限并进 SystemUI APK，故必须 AAR 交付而非纯 jar）；R.txt 为 Soong 空表。
        "code": [
            TRACEUR_SOONG / "TraceurCommon/android_common/javac/TraceurCommon.jar",
            SOONG_DIR / "external/perfetto/perfetto_config_java_protos/android_common/javac/perfetto_config_java_protos.jar",
        ],
        "res": [],
        "manifest": TRACEUR_DIR / "AndroidManifest-common.xml",
        "rtxt": TRACEUR_SOONG / "TraceurCommon/android_common/R.txt",
        "output": "libs/aars/TraceurCommon.aar",
    },
    "Traceur-res": {
        # android_library "Traceur-res"（res-only，use_resource_processor）：
        # 105 个 res 文件，namespace com.android.traceur.res；
        # 类由 AGP 从 R.txt 重新生成（R$array/R$string 等，旧 traceur-res-R.jar 退役）。
        "code": [],
        "res": [TRACEUR_DIR / "res"],
        "manifest": TRACEUR_DIR / "AndroidManifest-res.xml",
        "rtxt": TRACEUR_SOONG / "Traceur-res/android_common/R.txt",
        "output": "libs/aars/Traceur-res.aar",
    },
}


class DuplicateEntryError(RuntimeError):
    """两个输入 JAR 出现非 MANIFEST 的重复 entry。"""
    pass


def _is_r_class(name: str) -> bool:
    basename = name.rsplit("/", 1)[-1]
    return basename == "R.class" or basename.startswith("R$")


FIXED_ZIP_TIME = (1980, 1, 1, 0, 0, 0)


def _zip_info(name: str) -> zipfile.ZipInfo:
    """固定 timestamp/metadata 的 ZipInfo，保证重复打包字节一致。"""
    info = zipfile.ZipInfo(name, FIXED_ZIP_TIME)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _write_entry(archive: zipfile.ZipFile, name: str, data: bytes) -> None:
    """用固定 metadata 写入一个 ZIP entry，不依赖输入 JAR 的原始 timestamp。"""
    archive.writestr(_zip_info(name), data)


def merge_code_jars(jars, output: Path) -> None:
    """合并多个 JAR 到 output。跳过目录 entry 与重复 MANIFEST；拒绝 R.class；其余重复报错。"""
    seen = {}
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as out:
        for jar in jars:
            jar = Path(jar)
            with zipfile.ZipFile(jar) as z:
                for info in z.infolist():
                    name = info.filename
                    if name.endswith("/"):
                        continue  # 目录 entry
                    if _is_r_class(name):
                        raise DuplicateEntryError(
                            f"拒绝 R 类 entry: {name}（来自 {jar}）；AGP 会从 res/R.txt 重新生成 R")
                    if name == "META-INF/MANIFEST.MF":
                        if name in seen:
                            continue  # 仅允许重复 MANIFEST，保留第一份
                        seen[name] = jar
                        _write_entry(out, name, z.read(info))
                        continue
                    if name in seen:
                        raise DuplicateEntryError(
                            f"重复 entry: {name}（{seen[name]} 与 {jar}）")
                    seen[name] = jar
                    _write_entry(out, name, z.read(info))


def copy_resource_tree(source: Path, destination: Path) -> None:
    """字节级复制 res 树。"""
    source = Path(source)
    destination = Path(destination)
    for p in sorted(source.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(source)
        dst = destination / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(p.read_bytes())


def assemble_aar(code_jars, res_dirs, manifest: Path, rtxt: Path, output: Path,
                  reject_prefixes=None, exclude_prefixes=None) -> None:
    """组装最终 AAR：classes.jar（合并 code JAR）+ res/ + AndroidManifest.xml + R.txt。

    :param code_jars: code JAR 路径列表
    :param res_dirs: res root 路径或路径列表（多 root 时检测重复相对路径）
    :param reject_prefixes: 额外拒绝的类名前缀列表（如 WM-Shell 拒绝 com/android/systemui/）
    :param exclude_prefixes: 由 sibling artifact 负责交付、需要从本 AAR 省略的类名前缀
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    reject_prefixes = reject_prefixes or []
    exclude_prefixes = exclude_prefixes or []
    # 合并 code JAR 到内存 classes.jar
    merged = BytesIO()
    seen = set()
    with zipfile.ZipFile(merged, "w", zipfile.ZIP_DEFLATED) as mw:
        for jar in code_jars:
            jar = Path(jar)
            if not jar.exists():
                raise FileNotFoundError(f"缺少 code JAR: {jar}")
            with zipfile.ZipFile(jar) as z:
                for info in z.infolist():
                    name = info.filename
                    if name.endswith("/"):
                        continue  # 目录 entry
                    if _is_r_class(name):
                        raise DuplicateEntryError(
                            f"拒绝 R 类 entry: {name}（来自 {jar}）")
                    if any(name.startswith(p) for p in reject_prefixes):
                        raise DuplicateEntryError(
                            f"拒绝禁止前缀的类: {name}（来自 {jar}）；前缀 {reject_prefixes}")
                    if any(name.startswith(p) for p in exclude_prefixes):
                        continue
                    if name == "META-INF/MANIFEST.MF":
                        if name in seen:
                            continue
                        seen.add(name)
                        _write_entry(mw, name, z.read(info))
                        continue
                    if name in seen:
                        raise DuplicateEntryError(f"重复 entry: {name}（来自 {jar}）")
                    seen.add(name)
                    _write_entry(mw, name, z.read(info))
    classes_bytes = merged.getvalue()

    # 收集 res entries（多 root 时检测重复相对路径）
    res_entries = []  # (name, data)
    res_seen = set()
    if isinstance(res_dirs, (str, Path)):
        res_dirs = [res_dirs]
    for res_dir in res_dirs:
        res_dir = Path(res_dir)
        if not res_dir.exists():
            raise FileNotFoundError(f"缺少 res 目录: {res_dir}")
        for p in sorted(res_dir.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(res_dir)).replace("\\", "/")
            entry_name = f"res/{rel}"
            if entry_name in res_seen:
                raise DuplicateEntryError(
                    f"重复 res entry: {entry_name}（来自 {res_dir}）")
            res_seen.add(entry_name)
            res_entries.append((entry_name, p.read_bytes()))

    manifest = Path(manifest)
    rtxt = Path(rtxt)
    if not manifest.exists():
        raise FileNotFoundError(f"缺少 manifest: {manifest}")
    if not rtxt.exists():
        raise FileNotFoundError(f"缺少 R.txt: {rtxt}")

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as aar:
        entries = [
            ("classes.jar", classes_bytes),
            ("AndroidManifest.xml", manifest.read_bytes()),
            ("R.txt", rtxt.read_bytes()),
        ] + res_entries
        for name, data in sorted(entries, key=lambda e: e[0]):
            _write_entry(aar, name, data)


def build_artifact(name: str, output: Path = None) -> None:
    """按 CONFIGS 打包指定 artifact 为直接 AAR。"""
    if name not in CONFIGS:
        raise ValueError(f"未知 artifact: {name}；可选: {list(CONFIGS)}")
    cfg = CONFIGS[name]
    output = Path(output) if output else Path(cfg["output"])
    reject_prefixes = ["com/android/systemui/"] if cfg.get("reject_sysui") else []
    assemble_aar(cfg["code"], cfg["res"], cfg["manifest"], cfg["rtxt"], output,
                 reject_prefixes=reject_prefixes,
                 exclude_prefixes=cfg.get("exclude_prefixes", []))
    print(f"{name} AAR → {output} ({output.stat().st_size} bytes)")


def build_animationlib(output: Path = DEFAULT_OUTPUT) -> None:
    """打包 animationlib AAR（向后兼容）。"""
    build_artifact("animationlib", output)


def main():
    ap = argparse.ArgumentParser(description="打包 AOSP 库为直接 AAR")
    ap.add_argument("lib", nargs="?", choices=list(CONFIGS),
                   help="要打包的库（省略时配合 --all 打包全部）")
    ap.add_argument("--output", default=None, help="输出 AAR 路径（默认用 config）")
    ap.add_argument("--all", action="store_true", help="打包 CONFIGS 中所有库")
    args = ap.parse_args()

    if args.all:
        for name in CONFIGS:
            build_artifact(name, None)
        return 0

    if not args.lib:
        ap.error("需要指定 lib 或 --all")
    build_artifact(args.lib, Path(args.output) if args.output else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
