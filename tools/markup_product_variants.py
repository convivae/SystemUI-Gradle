#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给 res-product 下 AOSP product variant 资源加 CONV_DEL 标记。

背景（见 docs/issues/2026-08-07-product-variant-conv-del.md、ADR 0004）：
  AOSP res-product/values/strings.xml 用 product="tv"/"tablet"/"device"/"default"
  区分设备变体。Soong 理解，AAPT2 不支持，把多变体当 default 重复。

本脚本把 product="tv"/"tablet"/"device" 的 <string> 行用 CONV_DEL 块注释掉
（三段独立 <!-- -->，AAPT2 全部当注释忽略），保留 product="default"。
原行以注释文本保留，可追溯可撤回（见 ADR 0004）。

用法：
    python3 tools/markup_product_variants.py           # 默认处理 SystemUI-res/res-product
    python3 tools/markup_product_variants.py --dry-run  # 只打印将改的文件，不写
    python3 tools/markup_product_variants.py --root <dir>  # 指定其他根
"""

import argparse
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = PROJECT_ROOT / "SystemUI-res" / "res-product"

# 匹配非 default 的 product 变体 <string ...>...</string> 块（可单行或多行）
# product 值为 tv/tablet/device，不匹配 default
# 用 DOTALL 让 . 匹配换行，处理多行 string（含 <xliff:g> 子元素）
# 多行标签内不含 <!-- --> 子注释（已验证），故 .*? 不会跨坏嵌套注释
NON_DEFAULT_PRODUCT_RE = re.compile(
    r'^([ \t]*)<string(?=\s)(?=[^>]*\bproduct="(?:tv|tablet|device)")(.*?)>.*?</string>[ \t]*\n',
    re.MULTILINE | re.DOTALL,
)

REASON = "移除非 default product 变体，AAPT2 不支持 product 属性（见 docs/issues/2026-08-07-product-variant-conv-del.md）"

# 避免重复标记：检测某行是否已在 CONV_DEL BEGIN/END 块内
# 简化检测：如果上一非空行是 CONV_DEL BEGIN 或本行已被 <!-- 包裹，则跳过
CONV_DEL_BEGIN_RE = re.compile(r'<!--\s*CONV_DEL BEGIN')
COMMENTED_STRING_RE = re.compile(r'<!--\s*<string\b')


def mark_string_line(match):
    """把一个 <string product="tv|tablet|device">...</string> 行转成 CONV_DEL 块。

    输入：re.Match，group(1)=缩进
    输出：三段 <!-- --> 注释（BEGIN 标记 / 原行注释 / END 标记），保持原缩进
    """
    indent = match.group(1)
    original_line = match.group(0).rstrip("\n")  # 原始整行（去末尾换行）
    return (
        f'{indent}<!-- CONV_DEL BEGIN: {REASON} -->\n'
        f'{indent}<!-- {original_line.strip()} -->\n'
        f'{indent}<!-- CONV_DEL END -->\n'
    )


def is_already_marked(content, match_start):
    """判断 match_start 处的 <string 是否已被 CONV_DEL 包裹（避免重复标记）。

    检查：从 match_start 向前回溯到上一个非空行，若该行是 CONV_DEL BEGIN，
    或本行已被 <!-- 注释，则视为已标记。
    """
    # 本行是否已被 <!-- 包裹
    prefix = content[:match_start].rsplit("\n", 1)[-1] if match_start > 0 else ""
    if "<!--" in prefix and "<string" in prefix:
        # 同一行 <!-- <string ... 说明已注释
        return True
    # 找上一个非空行
    before = content[:match_start].rstrip()
    if not before:
        return False
    lines = before.split("\n")
    for line in reversed(lines):
        stripped = line.strip()
        if not stripped:
            continue
        if CONV_DEL_BEGIN_RE.search(stripped):
            return True
        # 遇到非 BEGIN 的非空行就停（不是 CONV_DEL 块内）
        return False
    return False


def transform_content(content):
    """对单个文件内容做 CONV_DEL 转换。返回 (new_content, changed_count)。

    幂等：已标记的非 default 变体不会重复标记。
    """
    changed = 0
    out_parts = []
    last = 0
    for m in NON_DEFAULT_PRODUCT_RE.finditer(content):
        if is_already_marked(content, m.start()):
            continue
        out_parts.append(content[last:m.start()])
        out_parts.append(mark_string_line(m))
        last = m.end()
        changed += 1
    out_parts.append(content[last:])
    return "".join(out_parts), changed


def process_root(root, dry_run=False):
    """处理 root 下所有 .xml 文件。返回 (total_files, total_changed, details)。"""
    total_files = 0
    total_changed = 0
    details = []
    for xml_file in sorted(root.rglob("*.xml")):
        original = xml_file.read_text(encoding="utf-8")
        new_content, changed = transform_content(original)
        if changed == 0:
            continue
        total_files += 1
        total_changed += changed
        rel = xml_file.relative_to(root)
        details.append((str(rel), changed))
        if not dry_run:
            xml_file.write_text(new_content, encoding="utf-8")
    return total_files, total_changed, details


def main():
    ap = argparse.ArgumentParser(description="给 res-product 的非 default product 变体加 CONV_DEL 标记")
    ap.add_argument("--root", default=str(DEFAULT_ROOT),
                    help=f"要处理的根目录（默认 {DEFAULT_ROOT}）")
    ap.add_argument("--dry-run", action="store_true", help="只打印将改的文件，不写")
    args = ap.parse_args()

    root = Path(args.root)
    if not root.exists():
        return f"根目录不存在: {root}"

    total_files, total_changed, details = process_root(root, dry_run=args.dry_run)

    print(f"根目录: {root}")
    print(f"修改文件数: {total_files}")
    print(f"注释行数: {total_changed}")
    if details:
        print("\n明细:")
        for rel, n in details[:20]:
            print(f"  {rel}: {n} 处")
        if len(details) > 20:
            print(f"  ... 还有 {len(details) - 20} 个文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
