#!/usr/bin/env python3
"""为 src/ 中每个多出文件找出它在 AOSP 的真实物理位置。

策略：扫描 AOSP 整个 frameworks/base/packages/SystemUI/ 树，对每个 .kt/.java/.aidl/.proto
按其完整相对路径建立 index；然后对每个 extras（按文件名）查找 AOSP 哪里有该文件。

按 bp_dir + 包路径给出最具体匹配。

输出 CSV：relpath, aosp_full_path, aosp_bp_module, gradle_target。
"""
from __future__ import annotations

import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_aosp_src_parity import CORE_DIR, DEFAULT_AOSP_ROOT  # type: ignore

AOSP_ROOT = DEFAULT_AOSP_ROOT

SOURCE_EXTS = (".kt", ".java", ".aidl", ".proto")


def collect_aosp_index() -> dict[str, list[Path]]:
    """Index all AOSP source files by filename.

    Returns: filename → list of full paths in AOSP.
    """
    idx: dict[str, list[Path]] = defaultdict(list)
    for p in AOSP_ROOT.rglob("*"):
        if p.is_file() and p.suffix in SOURCE_EXTS:
            idx[p.name].append(p)
    return idx


def parse_bp_modules() -> list[dict]:
    """Parse all Android.bp and return modules with srcs globs and bp dir.

    Resolves filegroup references so that indirect srcs like
    ":PlatformComposeSceneTransitionLayout-srcs" are expanded into their
    underlying file globs.
    """
    import re

    raw_blocks: list[dict] = []
    for bp in sorted(AOSP_ROOT.rglob("Android.bp")):
        text = bp.read_text()
        bp_path = str(bp.parent.relative_to(AOSP_ROOT))
        for m in re.finditer(
            r'(java_library|java_library_static|android_library|filegroup)\s*\{([^}]*)\}',
            text, re.DOTALL,
        ):
            body = m.group(2)
            n = re.search(r'name:\s*"([^"]+)"', body)
            if not n:
                continue
            srcs_match = re.search(r'srcs:\s*\[([^\]]*)\]', body, re.DOTALL)
            srcs = re.findall(r'"([^"]+)"', srcs_match.group(1)) if srcs_match else []
            raw_blocks.append({
                "type": m.group(1),
                "name": n.group(1),
                "bp_path": bp_path,
                "srcs": srcs,
            })

    # Build filegroup name → file globs (resolved against bp_path of that block)
    fg: dict[str, list[str]] = {}
    for blk in raw_blocks:
        if blk["type"] != "filegroup":
            continue
        paths: list[str] = []
        for s in blk["srcs"]:
            if s.startswith(":") or s.startswith("/"):
                continue
            if blk["bp_path"] in (".", ""):
                paths.append(s)
            else:
                paths.append(f"{blk['bp_path']}/{s}")
        fg[blk["name"]] = paths

    # Build modules with resolved srcs
    modules: list[dict] = []
    for blk in raw_blocks:
        if blk["type"] not in ("java_library", "java_library_static", "android_library"):
            continue
        resolved: list[str] = []
        for s in blk["srcs"]:
            if s.startswith("/"):
                continue
            if s.startswith(":"):
                # filegroup reference — inline
                resolved.extend(fg.get(s[1:], []))
            else:
                if blk["bp_path"] in (".", ""):
                    resolved.append(s)
                else:
                    resolved.append(f"{blk['bp_path']}/{s}")
        if not resolved:
            continue
        modules.append({
            "name": blk["name"],
            "type": blk["type"],
            "bp_path": blk["bp_path"],
            "srcs_globs": resolved,
        })
    return modules


def match_module_by_glob(aosp_full_relpath: str, modules: list[dict]) -> dict | None:
    """Match an AOSP-relative file path to its owning bp module.

    Longest fixed prefix wins (most specific).
    """
    candidates = []
    for m in modules:
        for g in m["srcs_globs"]:
            # Quick check: does the file path start with the fixed prefix?
            fixed = []
            for p in g.split("/"):
                if p == "**" or "*" in p:
                    break
                fixed.append(p)
            prefix = "/".join(fixed)
            if prefix and aosp_full_relpath.startswith(prefix + "/"):
                specificity = len(prefix)
                candidates.append((specificity, m, g))
            elif not prefix:
                pass
    if not candidates:
        return None
    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def bp_path_to_gradle(bp_path: str, bp_name: str) -> str:
    """Convert AOSP bp dir + name to Gradle module name.

    Naming convention: SystemUI-<bp_path>-<bp_name>
    For top-level (bp_path = '.'): SystemUI-<bp_name>

    Special: when there is exactly ONE module in a bp dir (like compose/scene),
    we omit the bp_name suffix to avoid noise.
    """
    if bp_path in (".", ""):
        return f"SystemUI-{bp_name}"
    return f"SystemUI-{bp_path.replace('/', '-')}-{bp_name}"


def main() -> int:
    # Build AOSP index
    idx = collect_aosp_index()
    print(f"AOSP source files indexed: {sum(len(v) for v in idx.values())}", file=sys.stderr)

    # Collect our extras
    our_src = set()
    base = CORE_DIR / "src"
    for p in base.rglob("*"):
        if p.is_file() and p.suffix in SOURCE_EXTS:
            rel = p.relative_to(base).as_posix()
            our_src.add(rel)

    aosp_src = set()
    base2 = AOSP_ROOT / "src"
    for p in base2.rglob("*"):
        if p.is_file() and p.suffix in SOURCE_EXTS:
            rel = p.relative_to(base2).as_posix()
            aosp_src.add(rel)

    extras = sorted(our_src - aosp_src)
    print(f"extras in our src/: {len(extras)}", file=sys.stderr)

    modules = parse_bp_modules()

    rows = []
    unmatched = []
    for rel in extras:
        filename = Path(rel).name
        candidates = idx.get(filename, [])
        # 仅保留 source files 类型匹配
        candidates = [
            c for c in candidates
            if c.suffix == Path(rel).suffix
        ]
        if not candidates:
            unmatched.append(rel)
            continue

        # 排序：偏好类名完全一致 + 路径前缀匹配
        # 取 aosp 相对路径
        def score(c: Path) -> tuple:
            aosp_rel = c.relative_to(AOSP_ROOT).as_posix()
            # 偏好：包名（不含文件）相同
            our_pkg = "/".join(rel.split("/")[:-1])
            aosp_pkg = "/".join(aosp_rel.split("/")[:-1])
            # 包名末尾段数匹配得高分
            our_segments = our_pkg.split("/")
            aosp_segments = aosp_pkg.split("/")
            common = 0
            for a, b in zip(reversed(our_segments), reversed(aosp_segments)):
                if a == b:
                    common += 1
                else:
                    break
            # 偏好：basename 前面不含 _test 等
            return (-common, len(aosp_rel))

        candidates.sort(key=score)
        best = candidates[0]
        aosp_rel = best.relative_to(AOSP_ROOT).as_posix()

        m = match_module_by_glob(aosp_rel, modules)
        if m is None:
            unmatched.append(rel)
            continue

        gradle = bp_path_to_gradle(m["bp_path"], m["name"])
        rows.append({
            "relpath": rel,
            "aosp_full_path": aosp_rel,
            "aosp_bp_dir": m["bp_path"],
            "aosp_module": m["name"],
            "gradle_target": gradle,
        })

    # 输出 CSV
    csv_path = Path(__file__).resolve().parent.parent / "docs" / "extras-file-mapping.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[
            "relpath", "aosp_full_path", "aosp_bp_dir", "aosp_module", "gradle_target"
        ])
        w.writeheader()
        for r in sorted(rows, key=lambda r: (r["gradle_target"], r["relpath"])):
            w.writerow(r)

    # 汇总
    by_module = {}
    for r in rows:
        by_module.setdefault(r["gradle_target"], 0)
        by_module[r["gradle_target"]] += 1

    print(f"已映射 {len(rows)}/{len(extras)} 个文件", file=sys.stderr)
    print(f"未匹配 {len(unmatched)} 个", file=sys.stderr)
    print(f"输出: {csv_path}", file=sys.stderr)
    print()
    print("--- 目标 Gradle 模块文件数统计 ---")
    for k in sorted(by_module, key=lambda x: -by_module[x]):
        print(f"  {k:65s} {by_module[k]}")

    if unmatched:
        print()
        print(f"--- 未匹配 {len(unmatched)} 个文件（前 30） ---")
        for u in unmatched[:30]:
            print(f"  {u}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
