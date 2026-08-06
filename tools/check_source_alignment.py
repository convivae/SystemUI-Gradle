#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 SystemUI-Gradle 项目的源码文件与 AOSP 源码的对齐情况。

依据（见 AGENTS.md）：
  - 规则 S：AOSP packages/SystemUI 下 SystemUI 自有代码一律源码复制（source module）
  - 规则 C：代码/aidl/res 必须"不漏不多"——与 AOSP 对应目录逐一对齐
  - 规则 B / ADR 0003：模块划分、源码目录以 AOSP Android.bp 为唯一标准
  - 规则 F：framework（非 SystemUI）代码不源码复制（本脚本只检查 SystemUI 自有源码模块）

输出两类问题：
  [MISSING]  AOSP 有、项目未放到正确位置（漏的）
  [EXTRA]    项目有、AOSP 对应模块没有（多的 / 放错地方）
             其中若该文件在 AOSP 其它源码模块中存在 → 标记为 [MISPLACED]（放错模块）

用法：
    python3 tools/check_source_alignment.py            # 全量检查（源码 + res）
    python3 tools/check_source_alignment.py --no-res   # 只检查源码
    python3 tools/check_source_alignment.py --summary  # 只看汇总数字
"""

import argparse
import os
import sys
from collections import defaultdict, namedtuple
from pathlib import Path

# ─────────────────────────────────────────────────────────────────────────────
# 路径
# ─────────────────────────────────────────────────────────────────────────────
AOSP_ROOT = Path("/home/conv/myspace/aosp/frameworks/base/packages/SystemUI")
PROJECT_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")

# 不参与比对的目录/文件（构建产物、IDE、VCS 等）
EXCLUDE_DIR_PARTS = {"build", ".gradle", ".git", ".idea", "out", "generated"}
EXCLUDE_SUFFIXES = {".iml", ".class"}

# 源码扩展名（kt/java/aidl/proto/logtags）
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
    recursive=False 时只枚举直接子文件（对应 bp 的 srcs: ["*.kt"] 非递归写法）。"""
    out = {}
    if not root.exists():
        return out
    if recursive:
        iterator = root.rglob("*")
    else:
        iterator = (p for p in root.iterdir())
    for p in iterator:
        if not p.is_file():
            continue
        if _is_excluded(p):
            continue
        if suffixes is None or p.suffix in suffixes:
            out[str(p.relative_to(root))] = p
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 模块映射表（源自 AOSP Android.bp，见 docs/adr/0003-app-module-aligns-aosp-bp.md）
# 字段：
#   aosp_subdirs     —— AOSP SystemUI 下相对目录列表（多个目录编译进同一模块时合并为一个期望集）
#   project_module   —— 对应项目模块名
#   project_src_root —— 项目模块内源码根目录（相对模块）；尾路径需与 AOSP 侧对齐
#   exclude_tails    —— 比对时从【两侧】排除的相对路径尾
#   recursive        —— 是否递归枚举（False 对应 bp 的 srcs: ["*.kt"] 非递归写法）
#   note             —— 说明
# ─────────────────────────────────────────────────────────────────────────────
Mapping = namedtuple("Mapping", ["aosp_subdirs", "project_module", "project_src_root",
                                 "exclude_tails", "exclude_prefixes", "recursive", "note"])


def M(aosp_subdirs, project_module, project_src_root, exclude_tails=None,
      exclude_prefixes=None, recursive=True, note=""):
    return Mapping(aosp_subdirs, project_module, project_src_root,
                   exclude_tails or [], exclude_prefixes or [], recursive, note)


# surfaceeffects 属独立 SystemUIShaderLib（PlatformAnimationLib exclude_srcs），项目无此模块
SURFACEEFFECTS_PREFIX = "com/android/systemui/surfaceeffects/"


def _filter_tails(tails, exclude_tails, exclude_prefixes):
    """按精确尾 + 前缀过滤。"""
    out = set()
    for t in tails:
        if t in exclude_tails:
            continue
        if any(t.startswith(p) for p in exclude_prefixes):
            continue
        out.add(t)
    return out


SOURCE_MAPPINGS = [
    # SystemUI-core (Android.bp:423) srcs: src/** + compose/features/src/** + compose/facade/enabled/src/**
    # 三个 AOSP 目录编译进同一 SystemUI-core，项目侧合并到 SystemUI-core/src，故合并为一个期望集
    M(["src", "compose/features/src", "compose/facade/enabled/src"], "SystemUI-core", "src",
      note="SystemUI-core src+compose/features+compose/facade (Android.bp:425-431)"),
    M(["src-debug"], "SystemUI-core", "src-debug", note="DebugJavaFiles (filegroup)"),
    M(["src-release"], "SystemUI-core", "src-release", note="ReleaseJavaFiles (filegroup)"),

    # SystemUISharedLib (shared/Android.bp)
    M(["shared/src"], "SystemUI-shared", "src", note="SystemUISharedLib src/**"),
    # SystemUISharedLib-Keyguard (shared/keyguard/Android.bp)
    M(["shared/keyguard/src"], "SystemUI-shared-keyguard", "src/main/java", note="SystemUISharedLib-Keyguard"),
    # BiometricsSharedLib (shared/biometrics/Android.bp)
    M(["shared/biometrics/src"], "SystemUI-shared-biometrics", "src/main/java", note="BiometricsSharedLib"),

    # PlatformAnimationLib (animation/Android.bp) srcs: animation/src/** 但 exclude surfaceeffects/**
    # surfaceeffects 属独立 SystemUIShaderLib（项目无此模块，单独报告）
    M(["animation/src"], "SystemUI-animation", "src",
      exclude_prefixes=[SURFACEEFFECTS_PREFIX],
      note="PlatformAnimationLib src/** (excl surfaceeffects)"),

    # PlatformAnimationLib-core/-server (animation/lib/Android.bp)
    M(["animation/lib/src"], "SystemUI-animationlib", "src/main/java", note="PlatformAnimationLib-core/server"),

    # SystemUICustomizationLib (customization/Android.bp)
    M(["customization/src"], "SystemUI-customization", "src", note="SystemUICustomizationLib"),

    # SystemUICommon (common/Android.bp)
    M(["common/src"], "SystemUI-common", "src/main/java", note="SystemUICommon"),
    # SystemUILogLib (log/Android.bp)
    M(["log/src"], "SystemUI-log", "src/main/java", note="SystemUILogLib"),
    # SystemUIUnfoldLib (unfold/Android.bp)
    M(["unfold/src"], "SystemUI-unfold", "src", note="SystemUIUnfoldLib"),

    # SystemUIPluginLib (plugin/Android.bp): plugin/src/** + plugin/bcsmartspace/src/**（合并进同一模块）
    M(["plugin/src", "plugin/bcsmartspace/src"], "SystemUI-plugin", "src/main/java",
      ["com/android/systemui/PluginProtectorStub.kt"], note="SystemUIPluginLib src+bcsmartspace"),
    # PluginAnnotationLib + PluginCoreLib (plugin_core/Android.bp)
    M(["plugin_core/src"], "SystemUI-plugin-core", "src/main/java", note="PluginCoreLib + PluginAnnotationLib"),

    # PlatformComposeCore (compose/core/Android.bp)
    M(["compose/core/src"], "SystemUI-compose-core", "src/main/java", note="PlatformComposeCore"),
    # PlatformComposeSceneTransitionLayout (compose/scene/Android.bp)
    M(["compose/scene/src"], "SystemUI-compose-scene", "src/main/java", note="PlatformComposeSceneTransitionLayout"),

    # kairos (utils/kairos/Android.bp)
    M(["utils/kairos/src"], "SystemUI-utils-kairos", "src/main/java", note="kairos"),
    # SystemUI-shared-utils (utils/Android.bp) —— 项目侧归属待核，全局搜索定位
    M(["utils/src"], "SystemUI-common", None, note="SystemUI-shared-utils utils/src/** (项目侧归属待核)"),
]

# Pods 模块（pods/Android.bp 下的子模块）。
# 关键：AOSP pods 子目录路径已含包名（如 pods/com/android/systemui/dagger），
# 故项目源码根也需带上包名，使两侧"尾路径"对齐（尾=相对各自主根的路径）。
# retail 父目录 bp 用 srcs: ["*.kt"] 非递归，data/domain 是独立子模块，故父目录 recursive=False。
SOURCE_MAPPINGS.extend([
    M(["pods/com/android/systemui/dagger"], "SystemUI-pods-dagger",
      "src/main/java/com/android/systemui/dagger", recursive=True, note="pods: dagger (**/*.java|kt)"),
    M(["pods/com/android/systemui/util/settings"], "SystemUI-pods-settings",
      "src/main/java/com/android/systemui/util/settings", recursive=True, note="pods: util/settings"),
    M(["pods/com/android/systemui/retail"], "SystemUI-pods-retail",
      "src/main/java/com/android/systemui/retail", recursive=False, note="pods: retail (*.kt 非递归)"),
    M(["pods/com/android/systemui/retail/data"], "SystemUI-pods-retail-data-impl",
      "src/main/java/com/android/systemui/retail/data", recursive=True, note="pods: retail/data"),
    M(["pods/com/android/systemui/retail/domain"], "SystemUI-pods-retail-domain-impl",
      "src/main/java/com/android/systemui/retail/domain", recursive=True, note="pods: retail/domain"),
])

# 最终 APK/优化文件 → :app。AndroidManifest-res.xml 属于 SystemUI-res，
# 当前项目是否建立独立 :SystemUI-res module 仍待结构审查，不能误判为 app 必需文件。
APP_TOP_FILES = {
    "AndroidManifest.xml": "app/src/main/AndroidManifest.xml",
    "proguard.flags": "app/proguard.flags",
    "proguard_common.flags": "app/proguard_common.flags",
    "proguard_kotlin.flags": "app/proguard_kotlin.flags",
}

# 资源目录映射（规则 C：res 1:1 对齐）。项目侧全部归入 SystemUI-core。
RES_MAPPINGS = [
    ("res", "SystemUI-core/res"),
    ("res-keyguard", "SystemUI-core/res-keyguard"),
    ("res-product", "SystemUI-core/res-product"),
    ("shared/res", "SystemUI-shared/res"),
    ("shared/biometrics/res", "SystemUI-shared-biometrics/src/main/res"),
    ("animation/res", "SystemUI-animation/res"),
    ("customization/res", "SystemUI-customization/res"),
    ("animation/lib/res", "SystemUI-animationlib/src/main/res"),
]


# ─────────────────────────────────────────────────────────────────────────────
# 全局 AOSP 源码索引：tail -> [(aosp_subdir, project_module), ...]
# 用于判断"项目里的多余文件"是否其实是放错模块（在别的 AOSP 模块里存在）
# ─────────────────────────────────────────────────────────────────────────────
def build_aosp_global_index():
    idx = defaultdict(list)
    for m in SOURCE_MAPPINGS:
        for aosp_sub in m.aosp_subdirs:
            adir = AOSP_ROOT / aosp_sub
            files = walk_source(adir, SOURCE_SUFFIXES, recursive=m.recursive)
            for tail in files:
                idx[tail].append((aosp_sub, m.project_module))
    return idx


def project_source_root(module: str, src_root: str):
    if src_root is None:
        return None
    return PROJECT_ROOT / module / src_root


def find_tail_in_project(tail: str, aosp_global_index):
    """全局搜索某个 tail 在项目里的所有出现位置（跨所有源码模块）。"""
    hits = []
    for m in SOURCE_MAPPINGS:
        root = project_source_root(m.project_module, m.project_src_root)
        if root is None:
            continue
        cand = root / tail
        if cand.is_file() and not _is_excluded(cand):
            hits.append((m.project_module, cand))
    return hits


# ─────────────────────────────────────────────────────────────────────────────
# 主检查
# ─────────────────────────────────────────────────────────────────────────────
def check_source_mappings(aosp_global_index, summary_only=False):
    missing = []      # (aosp_sub, mod, tail, note)
    misplaced = []    # (mod, tail, actual_path, should_be_mod, should_be_aosp_sub)
    truly_extra = []  # (mod, tail, actual_path)

    for m in SOURCE_MAPPINGS:
        # 合并多个 AOSP 源码目录为一个期望集（同一模块编译多个目录的情况）
        aosp_files = {}
        for aosp_sub in m.aosp_subdirs:
            adir = AOSP_ROOT / aosp_sub
            aosp_files.update(walk_source(adir, SOURCE_SUFFIXES, recursive=m.recursive))

        if m.project_src_root is None:
            # 全局搜索型映射：只报"漏的"（AOSP 有、项目哪里都找不到）
            aosp_tails = _filter_tails(aosp_files, m.exclude_tails, m.exclude_prefixes)
            for tail in aosp_tails:
                if not find_tail_in_project(tail, aosp_global_index):
                    missing.append((m.aosp_subdirs[0], m.project_module, tail, m.note))
            continue

        proot_path = project_source_root(m.project_module, m.project_src_root)
        proj_files = walk_source(proot_path, SOURCE_SUFFIXES, recursive=m.recursive)

        # exclude_tails / exclude_prefixes 从两侧排除（如 app 入口类、surfaceeffects）
        aosp_tails = _filter_tails(aosp_files, m.exclude_tails, m.exclude_prefixes)
        proj_tails = _filter_tails(proj_files, m.exclude_tails, m.exclude_prefixes)

        # 漏的：AOSP 有、项目该模块没有
        for tail in sorted(aosp_tails - proj_tails):
            elsewhere = find_tail_in_project(tail, aosp_global_index)
            elsewhere_other = [mm for (mm, _p) in elsewhere if mm != m.project_module]
            if elsewhere_other:
                # 在别的项目模块里找到了 → 不算漏，算"放错模块"，在 extra 阶段会报
                continue
            missing.append((m.aosp_subdirs[0], m.project_module, tail, m.note))

        # 多的：项目该模块有、AOSP 该模块期望集没有
        for tail in sorted(proj_tails - aosp_tails):
            actual = proj_files[tail]
            candidates = aosp_global_index.get(tail, [])
            other = [(s, mm) for (s, mm) in candidates if mm != m.project_module]
            if other:
                s, mm = other[0]
                misplaced.append((m.project_module, tail, actual, mm, s))
            else:
                truly_extra.append((m.project_module, tail, actual))

    return missing, misplaced, truly_extra


def check_shader_lib():
    """SystemUIShaderLib（surfaceeffects）是独立 AOSP 模块；项目无对应模块，单独报告。"""
    adir = AOSP_ROOT / "animation/src" / SURFACEEFFECTS_PREFIX.rstrip("/")
    aosp_files = walk_source(adir, SOURCE_SUFFIXES)
    # 项目里是否任何位置有 surfaceeffects 文件
    proj_total = 0
    proj_locs = []
    for m in SOURCE_MAPPINGS:
        if m.project_src_root is None:
            continue
        root = project_source_root(m.project_module, m.project_src_root)
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.is_file() and SURFACEEFFECTS_PREFIX in str(p.relative_to(root)).replace("\\", "/"):
                proj_total += 1
                proj_locs.append(str(p).replace(str(PROJECT_ROOT) + "/", ""))
    return list(aosp_files.keys()), proj_total, proj_locs


def check_app_entry():
    """检查 android_app 顶层文件（manifest/proguard）是否在 :app 正确位置。

    入口类 SystemUIApplication/SystemUIService 按 AOSP bp 属于 SystemUI-core 的
    src/**/*.java（android_app 无独立 srcs），由 core 源码映射正常检查。
    同时检查 :app/src/main/java/ 下不应有入口类副本（避免重复）。
    """
    issues = []
    # 顶层文件（manifest + proguard）
    for aosp_top, proj_rel in APP_TOP_FILES.items():
        aosp_f = AOSP_ROOT / aosp_top
        proj_f = PROJECT_ROOT / proj_rel
        if aosp_f.exists() and not proj_f.exists():
            issues.append(("APP-MISSING", aosp_top, proj_rel, "android_app 引用的顶层文件缺失"))
    # 入口类不应在 :app 重复（应在 :SystemUI-core）
    for entry in ("SystemUIApplication.java", "SystemUIService.java"):
        dup = PROJECT_ROOT / "app" / "src" / "main" / "java" / "com" / "android" / "systemui" / entry
        if dup.exists():
            issues.append(("APP-DUP", str(dup).replace(str(PROJECT_ROOT) + "/", ""),
                           f"SystemUI-core/src/com/android/systemui/{entry}",
                           "入口类按 bp 属于 :SystemUI-core，:app 不应有副本"))
    return issues


def check_res(summary_only=False):
    missing = []
    extra = []
    for aosp_sub, proj_rel in RES_MAPPINGS:
        adir = AOSP_ROOT / aosp_sub
        proot = PROJECT_ROOT / proj_rel
        aosp_files = walk_source(adir, None)  # 所有 res 文件
        proj_files = walk_source(proot, None)
        for tail in sorted(set(aosp_files) - set(proj_files)):
            missing.append((aosp_sub, proj_rel, tail))
        for tail in sorted(set(proj_files) - set(aosp_files)):
            extra.append((aosp_sub, proj_rel, tail))
    return missing, extra


def main():
    ap = argparse.ArgumentParser(description="检查 SystemUI 源码与 AOSP 对齐")
    ap.add_argument("--no-res", action="store_true", help="跳过 res 检查")
    ap.add_argument("--summary", action="store_true", help="只输出汇总数字")
    args = ap.parse_args()

    if not AOSP_ROOT.exists():
        sys.exit(f"AOSP 根目录不存在: {AOSP_ROOT}")
    if not PROJECT_ROOT.exists():
        sys.exit(f"项目根目录不存在: {PROJECT_ROOT}")

    print(f"# SystemUI 源码对齐检查\n")
    print(f"AOSP : {AOSP_ROOT}")
    print(f"项目 : {PROJECT_ROOT}\n")

    aosp_idx = build_aosp_global_index()
    missing, misplaced, truly_extra = check_source_mappings(aosp_idx)
    app_issues = check_app_entry()
    shader_aosp, shader_proj_count, shader_proj_locs = check_shader_lib()

    print("=" * 78)
    print("【源码 (kt/java/aidl/proto/logtags) 汇总】")
    print("=" * 78)
    print(f"  [MISSING]   AOSP 有、项目缺（漏的）          : {len(missing)}")
    print(f"  [MISPLACED] 项目有、但放错模块（应在他处）    : {len(misplaced)}")
    print(f"  [EXTRA]     项目有、AOSP 全无（真正多余）    : {len(truly_extra)}")
    print(f"  [APP]       :app 入口/顶层文件问题           : {len(app_issues)}")
    print(f"  [SHADER]    SystemUIShaderLib(独立模块)      : AOSP {len(shader_aosp)} 个 / 项目 {shader_proj_count} 个（项目无独立 shader 模块）")

    res_missing = res_extra = 0
    if not args.no_res:
        res_missing, res_extra = check_res()
        print(f"  [RES-MISS]  res 漏的                         : {len(res_missing)}")
        print(f"  [RES-EXTRA] res 多的                         : {len(res_extra)}")
    print()

    if args.summary:
        return

    # ── MISSING 明细 ──
    if missing:
        print("=" * 78)
        print(f"【MISSING】AOSP 有、项目未放到正确位置（共 {len(missing)}）")
        print("=" * 78)
        by_mod = defaultdict(list)
        for aosp_sub, mod, tail, note in missing:
            by_mod[mod].append((aosp_sub, tail, note))
        for mod in sorted(by_mod):
            print(f"\n  ▶ {mod}")
            for aosp_sub, tail, note in sorted(by_mod[mod]):
                print(f"      - {aosp_sub}/{tail}   [{note}]")

    # ── MISPLACED 明细 ──
    if misplaced:
        print("\n" + "=" * 78)
        print(f"【MISPLACED】放错模块（共 {len(misplaced)}）")
        print("=" * 78)
        for mod, tail, actual, should_mod, should_sub in sorted(misplaced):
            short = str(actual).replace(str(PROJECT_ROOT) + "/", "")
            print(f"  - {short}")
            print(f"      → 应在 :{should_mod}  (AOSP: {should_sub}/{tail})")

    # ── TRULY EXTRA 明细 ──
    if truly_extra:
        print("\n" + "=" * 78)
        print(f"【EXTRA】AOSP 全无、项目多余（共 {len(truly_extra)}）")
        print("=" * 78)
        by_mod = defaultdict(list)
        for mod, tail, actual in truly_extra:
            by_mod[mod].append((tail, actual))
        for mod in sorted(by_mod):
            print(f"\n  ▶ {mod}")
            for tail, actual in sorted(by_mod[mod]):
                short = str(actual).replace(str(PROJECT_ROOT) + "/", "")
                print(f"      - {short}")

    # ── APP 明细 ──
    if app_issues:
        print("\n" + "=" * 78)
        print(f"【APP】android_app 入口文件（共 {len(app_issues)}）")
        print("=" * 78)
        for kind, aosp_rel, proj_rel, msg in app_issues:
            print(f"  - [{kind}] {aosp_rel} → {proj_rel}   {msg}")

    # ── RES 明细 ──
    if not args.no_res and (res_missing or res_extra):
        print("\n" + "=" * 78)
        print("【RES】资源对齐")
        print("=" * 78)
        if res_missing:
            print(f"\n  漏的 (共 {len(res_missing)})：")
            by_dir = defaultdict(list)
            for aosp_sub, proj_rel, tail in res_missing:
                by_dir[aosp_sub].append(tail)
            for aosp_sub in sorted(by_dir):
                print(f"    ▶ {aosp_sub} → {dict(RES_MAPPINGS).get(aosp_sub)}")
                for tail in sorted(by_dir[aosp_sub])[:30]:
                    print(f"        - {tail}")
                if len(by_dir[aosp_sub]) > 30:
                    print(f"        ... 还有 {len(by_dir[aosp_sub]) - 30} 个")
        if res_extra:
            print(f"\n  多的 (共 {len(res_extra)})：")
            by_dir = defaultdict(list)
            for aosp_sub, proj_rel, tail in res_extra:
                by_dir[proj_rel].append(tail)
            for proj_rel in sorted(by_dir):
                print(f"    ▶ {proj_rel}")
                for tail in sorted(by_dir[proj_rel])[:30]:
                    print(f"        - {tail}")
                if len(by_dir[proj_rel]) > 30:
                    print(f"        ... 还有 {len(by_dir[proj_rel]) - 30} 个")

    print("\n" + "=" * 78)
    print("完成。")


if __name__ == "__main__":
    main()
