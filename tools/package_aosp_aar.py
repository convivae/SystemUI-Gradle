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
ANIMATIONLIB_DIR = AOSP_ROOT / "frameworks/libs/systemui/animationlib"
SOONG_DIR = (AOSP_ROOT / "out/soong/.intermediates/frameworks/libs/systemui/animationlib"
             "/animationlib/android_common")

ANIMATIONLIB_JAVAC_JAR = SOONG_DIR / "javac" / "animationlib.jar"
ANIMATIONLIB_KOTLIN_JAR = SOONG_DIR / "kotlin" / "animationlib.jar"
ANIMATIONLIB_R_TXT = SOONG_DIR / "R.txt"

DEFAULT_OUTPUT = Path("libs/aars/animationlib.aar")


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


def assemble_aar(code_jars, res_dir: Path, manifest: Path, rtxt: Path, output: Path) -> None:
    """组装最终 AAR：classes.jar（合并 code JAR）+ res/ + AndroidManifest.xml + R.txt。"""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    # 合并 code JAR 到内存 classes.jar
    merged = BytesIO()
    seen = set()
    with zipfile.ZipFile(merged, "w", zipfile.ZIP_DEFLATED) as mw:
        for jar in code_jars:
            with zipfile.ZipFile(jar) as z:
                for info in z.infolist():
                    name = info.filename
                    if name.endswith("/"):
                        continue  # 目录 entry
                    if _is_r_class(name):
                        raise DuplicateEntryError(
                            f"拒绝 R 类 entry: {name}（来自 {jar}）")
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

    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as aar:
        entries = [
            ("classes.jar", classes_bytes),
            ("AndroidManifest.xml", Path(manifest).read_bytes()),
            ("R.txt", Path(rtxt).read_bytes()),
        ]
        res_dir = Path(res_dir)
        for p in sorted(res_dir.rglob("*")):
            if p.is_file():
                rel = p.relative_to(res_dir)
                entries.append((f"res/{rel}".replace("\\", "/"), p.read_bytes()))
        for name, data in sorted(entries, key=lambda e: e[0]):
            _write_entry(aar, name, data)


def build_animationlib(output: Path = DEFAULT_OUTPUT) -> None:
    """打包 animationlib AAR（AOSP javac + kotlin JAR + 原始 res + R.txt）。"""
    jars = [ANIMATIONLIB_JAVAC_JAR, ANIMATIONLIB_KOTLIN_JAR]
    for j in jars:
        if not j.exists():
            raise FileNotFoundError(f"缺少 Soong 产物: {j}")
    res = ANIMATIONLIB_DIR / "res"
    manifest = ANIMATIONLIB_DIR / "AndroidManifest.xml"
    rtxt = ANIMATIONLIB_R_TXT
    assemble_aar(jars, res, manifest, rtxt, output)
    print(f"animationlib AAR → {output} ({output.stat().st_size} bytes)")


def main():
    ap = argparse.ArgumentParser(description="打包 AOSP 库为直接 AAR")
    ap.add_argument("lib", choices=["animationlib"], help="要打包的库")
    ap.add_argument("--output", default=str(DEFAULT_OUTPUT), help="输出 AAR 路径")
    args = ap.parse_args()
    if args.lib == "animationlib":
        build_animationlib(Path(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
