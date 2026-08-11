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
        "code": [SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader/android_common/javac/iconloader.jar"],
        "res": [AOSP_ROOT / "frameworks/libs/systemui/iconloaderlib/res"],
        "manifest": AOSP_ROOT / "frameworks/libs/systemui/iconloaderlib/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader/android_common/R.txt",
        "output": "libs/aars/iconloader.aar",
    },
    "SettingsLib": {
        # 主 target + 全部 static_libs 子模块 javac JAR（780 classes，0 重复）
        "code": _discover_settingslib_code_jars(),
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/SettingsLib/android_common/R.txt",
        "output": "libs/aars/SettingsLib.aar",
    },
    "WindowManager-Shell": {
        "code": [SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/javac/WindowManager-Shell.jar"],
        "res": [AOSP_ROOT / "frameworks/base/libs/WindowManager/Shell/res"],
        "manifest": AOSP_ROOT / "frameworks/base/libs/WindowManager/Shell/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/R.txt",
        "output": "libs/aars/WindowManager-Shell.aar",
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
                  reject_prefixes=None) -> None:
    """组装最终 AAR：classes.jar（合并 code JAR）+ res/ + AndroidManifest.xml + R.txt。

    :param code_jars: code JAR 路径列表
    :param res_dirs: res root 路径或路径列表（多 root 时检测重复相对路径）
    :param reject_prefixes: 额外拒绝的类名前缀列表（如 WM-Shell 拒绝 com/android/systemui/）
    """
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    reject_prefixes = reject_prefixes or []
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
                 reject_prefixes=reject_prefixes)
    print(f"{name} AAR → {output} ({output.stat().st_size} bytes)")


def build_animationlib(output: Path = DEFAULT_OUTPUT) -> None:
    """打包 animationlib AAR（向后兼容）。"""
    build_artifact("animationlib", output)


def main():
    ap = argparse.ArgumentParser(description="打包 AOSP 库为直接 AAR")
    ap.add_argument("lib", choices=list(CONFIGS), help="要打包的库")
    ap.add_argument("--output", default=None, help="输出 AAR 路径（默认用 config）")
    args = ap.parse_args()
    build_artifact(args.lib, Path(args.output) if args.output else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
