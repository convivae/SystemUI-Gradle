#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 SystemUI-Gradle 项目的源码/资源与 AOSP 的对齐情况（内容感知 + 目标 owner 感知）。

依据（见 AGENTS.md）：
  - 规则 S：AOSP packages/SystemUI 下 SystemUI 自有代码一律源码复制（source module）
  - 规则 C：代码/aidl/res 必须"不漏不多"——与 AOSP 对应目录逐一对齐（含字节级内容）
  - 规则 B / ADR 0003 决策 1：源码 owner 和依赖语义对齐 BP，Gradle module 不与 target 1:1
  - 规则 F：framework（非 SystemUI）代码不源码复制（本脚本只检查 SystemUI 自有源码模块）

目标 13-module 拓扑的 owner 映射见 SOURCE_MAPPINGS / RES_MAPPINGS。
每个 AOSP source root 一条映射；同一 Gradle module 可有多条映射（不同 source root）。

输出问题类别：
  [MISSING]   AOSP 有、项目未放到任何位置（漏的）
  [MISPLACED] 项目有、但放错 owner（不同 module 或同一 module 的不同 source root）
  [EXTRA]     项目有、AOSP 全无（真正多余）
  [MODIFIED]  相对路径相同但字节不同（被擅改）
  [RES-*]     资源对应类别

用法：
    python3 tools/check_source_alignment.py            # 全量检查（源码 + res）
    python3 tools/check_source_alignment.py --no-res   # 只检查源码
    python3 tools/check_source_alignment.py --summary  # 只看汇总数字
    python3 tools/check_source_alignment.py --strict   # 任一 missing/misplaced/extra/modified 时退出 1
"""

import argparse
import sys
from collections import defaultdict, namedtuple
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 路径
# ─────────────────────────────────────────────────────────────────────────────
AOSP_ROOT = Path("/home/conv/myspace/aosp/frameworks/base/packages/SystemUI")
PROJECT_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")

EXCLUDE_DIR_PARTS = {"build", ".gradle", ".git", ".idea", "out", "generated"}
EXCLUDE_SUFFIXES = {".iml", ".class"}
SOURCE_SUFFIXES = {".kt", ".java", ".aidl", ".proto", ".logtags"}


def _is_excluded(p: Path) -> bool:
    parts = set(p.parts)
    if parts & EXCLUDE_DIR_PARTS:
        return True
    if p.suffix in EXCLUDE_SUFFIXES:
        return True
    return False


def walk_source(root: Path, suffixes, recursive=True):
    """枚举 root 下指定扩展名的文件，返回 {相对路径(str): 绝对路径(Path)}。
    suffixes=None 表示所有文件（用于 res）。"""
    out = {}
    if not root.exists():
        return out
    iterator = root.rglob("*") if recursive else (p for p in root.iterdir())
    for p in iterator:
        if not p.is_file():
            continue
        if _is_excluded(p):
            continue
        if suffixes is None or p.suffix in suffixes:
            out[str(p.relative_to(root))] = p
    return out


def _filter_tails(tails, exclude_tails, exclude_prefixes):
    out = set()
    for t in tails:
        if t in exclude_tails:
            continue
        if any(t.startswith(p) for p in exclude_prefixes):
            continue
        out.add(t)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 模块映射表：每个 AOSP source root 一条映射，指向目标 13-module 的物理 source root。
# ─────────────────────────────────────────────────────────────────────────────
Mapping = namedtuple("Mapping", ["aosp_subdirs", "project_module", "project_src_root",
                                 "exclude_tails", "exclude_prefixes", "recursive", "note"])


def M(aosp_subdirs, project_module, project_src_root, exclude_tails=None,
      exclude_prefixes=None, recursive=True, note=""):
    return Mapping(aosp_subdirs, project_module, project_src_root,
                   exclude_tails or [], exclude_prefixes or [], recursive, note)


SOURCE_MAPPINGS = [
    # SystemUI-core: src + src-debug + src-release + compose/features + compose/facade/enabled + pods
    M(["src"], "SystemUI-core", "src", note="SystemUI-core src"),
    M(["src-debug"], "SystemUI-core", "src-debug", note="DebugJavaFiles"),
    M(["src-release"], "SystemUI-core", "src-release", note="ReleaseJavaFiles"),
    M(["compose/features/src"], "SystemUI-core", "compose/features/src"),
    M(["compose/facade/enabled/src"], "SystemUI-core", "compose/facade/enabled/src"),
    M(["pods"], "SystemUI-core", "pods", note="全部 pods 生产源码"),

    # SystemUI-common: Common + Log + shared-utils 合并
    M(["common/src"], "SystemUI-common", "common/src", note="SystemUICommon"),
    M(["log/src"], "SystemUI-common", "log/src", note="SystemUILogLib"),
    M(["utils/src"], "SystemUI-common", "utils/src", note="SystemUI-shared-utils"),

    # SystemUI-animation: PlatformAnimationLib + Shader(surfaceeffects) 合并
    M(["animation/src"], "SystemUI-animation", "src", note="PlatformAnimationLib + Shader"),

    # SystemUI-plugin-core: PluginCoreLib runtime API（JVM）
    M(["plugin_core/src"], "SystemUI-plugin-core", "src", note="PluginCoreLib"),

    # SystemUI-plugin-processor: PluginAnnotationProcessor（build-time，JVM）
    M(["plugin_core/processor/src"], "SystemUI-plugin-processor", "src",
      note="PluginAnnotationProcessor"),

    # SystemUI-plugin: SystemUIPluginLib runtime（含 bcsmartspace）；排除 BP 不编译的 stub
    M(["plugin/src"], "SystemUI-plugin", "src",
      exclude_tails=["com/android/systemui/plugins/PluginProtectorStub.kt"],
      note="SystemUIPluginLib (excl PluginProtectorStub)"),
    M(["plugin/bcsmartspace/src"], "SystemUI-plugin", "bcsmartspace/src", note="bcsmartspace"),

    # SystemUI-unfold
    M(["unfold/src"], "SystemUI-unfold", "src", note="SystemUIUnfoldLib"),

    # SystemUI-customization
    M(["customization/src"], "SystemUI-customization", "src", note="SystemUICustomizationLib"),

    # SystemUI-shared: SystemUISharedLib + keyguard child 合并
    M(["shared/src"], "SystemUI-shared", "src", note="SystemUISharedLib"),
    M(["shared/keyguard/src"], "SystemUI-shared", "keyguard/src", note="SystemUISharedLib-Keyguard"),

    # SystemUI-shared-biometrics: 独立 R namespace
    M(["shared/biometrics/src"], "SystemUI-shared-biometrics", "src", note="BiometricsSharedLib"),

    # SystemUI-compose: Compose Core + Scene 合并
    M(["compose/core/src"], "SystemUI-compose", "core/src", note="PlatformComposeCore"),
    M(["compose/scene/src"], "SystemUI-compose", "scene/src", note="PlatformComposeSceneTransitionLayout"),
]

# 不进源码 module 的 AOSP 根（kairos test-only、animation/lib 非 SystemUI）：
#   utils/kairos/src, animation/lib/src —— 不在 SOURCE_MAPPINGS 中，故不会被检查，也不会被当作 misplaced 目标。

APP_TOP_FILES = {
    "AndroidManifest.xml": "app/src/main/AndroidManifest.xml",
    "proguard.flags": "app/proguard.flags",
    "proguard_common.flags": "app/proguard_common.flags",
    "proguard_kotlin.flags": "app/proguard_kotlin.flags",
}

RES_MAPPINGS = [
    ("res", "SystemUI-res/res"),
    ("res-keyguard", "SystemUI-res/res-keyguard"),
    ("res-product", "SystemUI-res/res-product"),
    ("shared/res", "SystemUI-shared/res"),
    ("shared/biometrics/res", "SystemUI-shared-biometrics/res"),
    ("animation/res", "SystemUI-animation/res"),
    ("customization/res", "SystemUI-customization/res"),
]


# ─────────────────────────────────────────────────────────────────────────────
# 纯函数（可单测）
# ─────────────────────────────────────────────────────────────────────────────
def diff_pair(aosp_files, proj_files):
    """比较两个 {tail: Path} 字典，返回 (missing, extra, modified_tails)。
    modified = 两侧都有但字节不同。"""
    aosp_set = set(aosp_files)
    proj_set = set(proj_files)
    missing = sorted(aosp_set - proj_set)
    extra = sorted(proj_set - aosp_set)
    modified = []
    for tail in sorted(aosp_set & proj_set):
        if aosp_files[tail].read_bytes() != proj_files[tail].read_bytes():
            modified.append(tail)
    return missing, extra, modified


def build_aosp_index(mappings, aosp_root, suffixes=SOURCE_SUFFIXES):
    """{tail: [(module, src_root, aosp_sub), ...]} 用于 misplaced 判定（root-aware）。"""
    idx = defaultdict(list)
    for m in mappings:
        for aosp_sub in m.aosp_subdirs:
            files = walk_source(aosp_root / aosp_sub, suffixes, recursive=m.recursive)
            for tail in _filter_tails(set(files), m.exclude_tails, m.exclude_prefixes):
                idx[tail].append((m.project_module, m.project_src_root, aosp_sub))
    return idx


def find_tail_locations(tail, mappings, project_root, suffixes=SOURCE_SUFFIXES):
    """全局搜索 tail 在项目里的所有出现位置，返回 [(module, src_root, path), ...]。"""
    hits = []
    for m in mappings:
        root = project_root / m.project_module / m.project_src_root
        cand = root / tail
        if cand.is_file() and not _is_excluded(cand):
            hits.append((m.project_module, m.project_src_root, cand))
    return hits


def classify_extra(tail, actual_loc, aosp_idx):
    """actual_loc = (module, src_root)。
    返回 ('misplaced', (exp_module, exp_src_root), aosp_sub) 或 ('extra', None, None)。"""
    for (mod, sroot, asub) in aosp_idx.get(tail, []):
        if (mod, sroot) != actual_loc:
            return ('misplaced', (mod, sroot), asub)
    return ('extra', None, None)


def run_source_check(mappings, aosp_root, project_root, suffixes=SOURCE_SUFFIXES):
    """对一组映射运行对齐检查，返回 {missing, misplaced, extra, modified}。"""
    aosp_idx = build_aosp_index(mappings, aosp_root, suffixes)
    missing, misplaced, extra, modified = [], [], [], []
    for m in mappings:
        aosp_files = {}
        for aosp_sub in m.aosp_subdirs:
            aosp_files.update(walk_source(aosp_root / aosp_sub, suffixes, recursive=m.recursive))
        proot = project_root / m.project_module / m.project_src_root
        proj_files = walk_source(proot, suffixes, recursive=m.recursive)
        aosp_tails = _filter_tails(set(aosp_files), m.exclude_tails, m.exclude_prefixes)
        proj_tails = _filter_tails(set(proj_files), m.exclude_tails, m.exclude_prefixes)
        loc = (m.project_module, m.project_src_root)

        for tail in sorted(aosp_tails - proj_tails):
            # 该 tail 在 AOSP 下的全部合法 owner（module, src_root）集合。
            # 只有出现在不在该集合的位置才算 MISPLACED；
            # 合法的另一个 root（如 src-release 存在但 src-debug 缺失）不能掩盖 MISSING。
            expected_locs = {
                (module, src_root)
                for module, src_root, _aosp_sub in aosp_idx.get(tail, [])
            }
            misplaced_elsewhere = [
                (module, src_root)
                for module, src_root, _path in find_tail_locations(
                    tail, mappings, project_root, suffixes)
                if (module, src_root) not in expected_locs
            ]
            if misplaced_elsewhere:
                continue  # 由错误位置所属映射的 extra 阶段报告 MISPLACED
            missing.append((m.aosp_subdirs[0], m.project_module, m.project_src_root, tail, m.note))

        for tail in sorted(aosp_tails & proj_tails):
            if aosp_files[tail].read_bytes() != proj_files[tail].read_bytes():
                modified.append((m.project_module, m.project_src_root, tail, aosp_files[tail], proj_files[tail]))

        for tail in sorted(proj_tails - aosp_tails):
            actual_path = proj_files[tail]
            kind, exp_loc, aosp_sub = classify_extra(tail, loc, aosp_idx)
            if kind == "misplaced":
                misplaced.append((m.project_module, m.project_src_root, tail, actual_path,
                                  exp_loc[0], exp_loc[1], aosp_sub))
            else:
                extra.append((m.project_module, m.project_src_root, tail, actual_path))
    return {"missing": missing, "misplaced": misplaced, "extra": extra, "modified": modified}


def run_res_check(res_mappings, aosp_root, project_root):
    missing, extra, modified = [], [], []
    for aosp_sub, proj_rel in res_mappings:
        aosp_files = walk_source(aosp_root / aosp_sub, None)
        proj_files = walk_source(project_root / proj_rel, None)
        aosp_set, proj_set = set(aosp_files), set(proj_files)
        for tail in sorted(aosp_set - proj_set):
            missing.append((aosp_sub, proj_rel, tail))
        for tail in sorted(proj_set - aosp_set):
            extra.append((aosp_sub, proj_rel, tail))
        for tail in sorted(aosp_set & proj_set):
            if aosp_files[tail].read_bytes() != proj_files[tail].read_bytes():
                modified.append((aosp_sub, proj_rel, tail))
    return {"missing": missing, "extra": extra, "modified": modified}


def check_app_entry():
    """检查 android_app 顶层文件（manifest/proguard）位置 + 入口类不应在 :app 重复。"""
    issues = []
    for aosp_top, proj_rel in APP_TOP_FILES.items():
        if (AOSP_ROOT / aosp_top).exists() and not (PROJECT_ROOT / proj_rel).exists():
            issues.append(("APP-MISSING", aosp_top, proj_rel, "android_app 引用的顶层文件缺失"))
    for entry in ("SystemUIApplication.java", "SystemUIService.java"):
        dup = PROJECT_ROOT / "app" / "src" / "main" / "java" / "com" / "android" / "systemui" / entry
        if dup.exists():
            issues.append(("APP-DUP", str(dup).replace(str(PROJECT_ROOT) + "/", ""),
                           f"SystemUI-core/src/com/android/systemui/{entry}",
                           "入口类按 bp 属于 :SystemUI-core，:app 不应有副本"))
    return issues


# ─────────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="检查 SystemUI 源码/资源与 AOSP 对齐")
    ap.add_argument("--no-res", action="store_true", help="跳过 res 检查")
    ap.add_argument("--summary", action="store_true", help="只输出汇总数字")
    ap.add_argument("--strict", action="store_true",
                    help="任一 missing/misplaced/extra/modified 时退出 1")
    args = ap.parse_args()

    if not AOSP_ROOT.exists():
        return f"AOSP 根目录不存在: {AOSP_ROOT}"
    if not PROJECT_ROOT.exists():
        return f"项目根目录不存在: {PROJECT_ROOT}"

    print(f"# SystemUI 源码/资源对齐检查\n")
    print(f"AOSP : {AOSP_ROOT}")
    print(f"项目 : {PROJECT_ROOT}\n")

    src = run_source_check(SOURCE_MAPPINGS, AOSP_ROOT, PROJECT_ROOT)
    app = check_app_entry()
    res = run_res_check(RES_MAPPINGS, AOSP_ROOT, PROJECT_ROOT) if not args.no_res \
        else {"missing": [], "extra": [], "modified": []}

    print("=" * 78)
    print("【源码 (kt/java/aidl/proto/logtags) 汇总】")
    print("=" * 78)
    print(f"  [MISSING]   AOSP 有、项目缺（漏的）          : {len(src['missing'])}")
    print(f"  [MISPLACED] 项目有、但放错 owner              : {len(src['misplaced'])}")
    print(f"  [EXTRA]     项目有、AOSP 全无（真正多余）      : {len(src['extra'])}")
    print(f"  [MODIFIED]  路径相同但字节不同（被擅改）        : {len(src['modified'])}")
    print(f"  [APP]       :app 入口/顶层文件问题            : {len(app)}")
    if not args.no_res:
        print(f"  [RES-MISS]  res 漏的                         : {len(res['missing'])}")
        print(f"  [RES-EXTRA] res 多的                         : {len(res['extra'])}")
        print(f"  [RES-MODIFIED] res 字节不同                  : {len(res['modified'])}")
    print()

    if args.summary:
        if args.strict and (src["missing"] or src["misplaced"] or src["extra"] or src["modified"]
                            or app or res["missing"] or res["extra"] or res["modified"]):
            return 1
        return 0

    def _short(p):
        return str(p).replace(str(PROJECT_ROOT) + "/", "")

    if src["missing"]:
        print("=" * 78)
        print(f"【MISSING】AOSP 有、项目未放到正确位置（共 {len(src['missing'])}）")
        print("=" * 78)
        by_mod = defaultdict(list)
        for aosp_sub, mod, sroot, tail, note in src["missing"]:
            by_mod[(mod, sroot)].append((aosp_sub, tail, note))
        for (mod, sroot) in sorted(by_mod):
            print(f"\n  ▶ {mod}/{sroot}")
            for aosp_sub, tail, note in sorted(by_mod[(mod, sroot)]):
                print(f"      - {aosp_sub}/{tail}   [{note}]")

    if src["misplaced"]:
        print("\n" + "=" * 78)
        print(f"【MISPLACED】放错 owner（共 {len(src['misplaced'])}）")
        print("=" * 78)
        for act_mod, act_sr, tail, actual, exp_mod, exp_sr, aosp_sub in sorted(src["misplaced"], key=lambda x: x[2]):
            print(f"  - {act_mod}/{act_sr}/{tail}  (实际: {_short(actual)})")
            print(f"      → 应在 :{exp_mod}/{exp_sr}  (AOSP: {aosp_sub}/{tail})")

    if src["extra"]:
        print("\n" + "=" * 78)
        print(f"【EXTRA】AOSP 全无、项目多余（共 {len(src['extra'])}）")
        print("=" * 78)
        by_mod = defaultdict(list)
        for mod, sroot, tail, actual in src["extra"]:
            by_mod[(mod, sroot)].append((tail, actual))
        for (mod, sroot) in sorted(by_mod):
            print(f"\n  ▶ {mod}/{sroot}")
            for tail, actual in sorted(by_mod[(mod, sroot)]):
                print(f"      - {tail}  ({_short(actual)})")

    if src["modified"]:
        print("\n" + "=" * 78)
        print(f"【MODIFIED】路径相同但字节不同（共 {len(src['modified'])}）")
        print("=" * 78)
        by_mod = defaultdict(list)
        for mod, sroot, tail, aosp_p, proj_p in src["modified"]:
            by_mod[(mod, sroot)].append((tail, aosp_p, proj_p))
        for (mod, sroot) in sorted(by_mod):
            print(f"\n  ▶ {mod}/{sroot}")
            for tail, aosp_p, proj_p in sorted(by_mod[(mod, sroot)]):
                print(f"      - {tail}")

    if app:
        print("\n" + "=" * 78)
        print(f"【APP】android_app 入口文件（共 {len(app)}）")
        print("=" * 78)
        for kind, aosp_rel, proj_rel, msg in app:
            print(f"  - [{kind}] {aosp_rel} → {proj_rel}   {msg}")

    if not args.no_res and (res["missing"] or res["extra"] or res["modified"]):
        print("\n" + "=" * 78)
        print("【RES】资源对齐")
        print("=" * 78)
        if res["missing"]:
            print(f"\n  漏的 (共 {len(res['missing'])})：")
            by_dir = defaultdict(list)
            for aosp_sub, proj_rel, tail in res["missing"]:
                by_dir[aosp_sub].append(tail)
            for aosp_sub in sorted(by_dir):
                print(f"    ▶ {aosp_sub}")
                for tail in sorted(by_dir[aosp_sub])[:30]:
                    print(f"        - {tail}")
                if len(by_dir[aosp_sub]) > 30:
                    print(f"        ... 还有 {len(by_dir[aosp_sub]) - 30} 个")
        if res["extra"]:
            print(f"\n  多的 (共 {len(res['extra'])})：")
            by_dir = defaultdict(list)
            for aosp_sub, proj_rel, tail in res["extra"]:
                by_dir[proj_rel].append(tail)
            for proj_rel in sorted(by_dir):
                print(f"    ▶ {proj_rel}")
                for tail in sorted(by_dir[proj_rel])[:30]:
                    print(f"        - {tail}")
                if len(by_dir[proj_rel]) > 30:
                    print(f"        ... 还有 {len(by_dir[proj_rel]) - 30} 个")
        if res["modified"]:
            print(f"\n  字节不同 (共 {len(res['modified'])})：")
            by_dir = defaultdict(list)
            for aosp_sub, proj_rel, tail in res["modified"]:
                by_dir[proj_rel].append(tail)
            for proj_rel in sorted(by_dir):
                print(f"    ▶ {proj_rel}")
                for tail in sorted(by_dir[proj_rel])[:30]:
                    print(f"        - {tail}")

    print("\n" + "=" * 78)
    print("完成。")

    if args.strict and (src["missing"] or src["misplaced"] or src["extra"] or src["modified"]
                        or app or res["missing"] or res["extra"] or res["modified"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
