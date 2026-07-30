#!/usr/bin/env bash
# scripts/check-aosp-src-parity.sh
# 严格 1:1 比对 SystemUI-Gradle src/ vs AOSP frameworks/base/packages/SystemUI/
# 规则 S：bp 1:1 对齐
#
# 输出：
#   - 三个 source set（src/、src-debug/、src-release/）各自主集 vs AOSP 同名集
#   - 缺/多/重名
#   - 跨 source set 误放（src/debug 出现同一文件）
#
# 跑法：
#   bash scripts/check-aosp-src-parity.sh

set -euo pipefail

GRADLE_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AOSP_ROOT="${AOSP_ROOT:-/home/conv/myspace/aosp/frameworks/base/packages/SystemUI}"
CORE_DIR="$GRADLE_ROOT/SystemUI-core"

# 检查 AOSP 树存在
if [[ ! -d "$AOSP_ROOT" ]]; then
    echo "fatal: AOSP root not found: $AOSP_ROOT" >&2
    echo "  set AOSP_ROOT env var to override" >&2
    exit 1
fi

# 收集 .kt / .java / .aidl / .proto（含包名完整路径）
collect_files() {
    local root="$1"
    local subpath="$2"  # 源目录名，如 src / src-debug / src-release
    if [[ -d "$root/$subpath" ]]; then
        find "$root/$subpath" \
            \( -name "*.kt" -o -name "*.java" -o -name "*.aidl" -o -name "*.proto" \) \
            -print 2>/dev/null
    fi
}

# 报告输出
echo "================================================================================"
echo "AOSP src 1:1 alignment check"
echo "  GRADLE: $GRADLE_ROOT"
echo "  AOSP:   $AOSP_ROOT"
echo "  CORE:   $CORE_DIR"
echo "================================================================================"

# 每一行：kind(GRADLE/AOSP)  subpath(debug/release)  relpath  basename
emit() {
    printf '%s\t%s\t%s\n' "$1" "$2" "$3"
}

tmpdir=$(mktemp -d)
trap "rm -rf $tmpdir" EXIT

for sub in src src-debug src-release; do
    out_aosp="$tmpdir/aosp-$sub.tsv"
    out_our="$tmpdir/our-$sub.tsv"

    # AOSP 路径
    collect_files "$AOSP_ROOT" "$sub" | awk -F"$AOSP_ROOT/$sub/" -v sub="$sub" '{print "AOSP\t"sub"\t"$2}' | LC_ALL=C sort > "$out_aosp"
    # 我们路径
    collect_files "$CORE_DIR" "$sub" | awk -F"$CORE_DIR/$sub/" -v sub="$sub" '{print "OURS\t"sub"\t"$2}' | LC_ALL=C sort > "$out_our"

    echo ""
    echo "### $sub/ ###"
    echo "  AOSP files: $(wc -l < "$out_aosp")"
    echo "  OURS files: $(wc -l < "$out_our")"

    # 第 3 列联集 (relpath) 用于差集
    aosp_set="$tmpdir/aosp-$sub.set"
    our_set="$tmpdir/our-$sub.set"
    cut -f3 "$out_aosp" > "$aosp_set"
    cut -f3 "$out_our" > "$our_set"

    # 1) 我们有，AOSP 没有（多出）
    echo ""
    echo "  --- 多出 (ours has, AOSP doesn't) — 数量: $(comm -23 "$our_set" "$aosp_set" | wc -l) ---"
    comm -23 "$our_set" "$aosp_set" | head -50

    # 2) AOSP 有，我们没有（缺少）
    echo ""
    echo "  --- 缺少 (AOSP has, we don't) — 数量: $(comm -13 "$our_set" "$aosp_set" | wc -l) ---"
    comm -13 "$our_set" "$aosp_set" | head -50
done

# 跨 source set 误放检查
echo ""
echo "================================================================================"
echo "Cross source-set overlap (logical bug: same file in src/ AND src-debug/)"
echo "================================================================================"
overlap_out="$tmpdir/overlap.tsv"
> "$overlap_out"
for sub1 in src src-debug; do
    for sub2 in src src-debug; do
        if [[ "$sub1" < "$sub2" ]]; then
            set1="$tmpdir/our-$sub1.set"
            set2="$tmpdir/our-$sub2.set"
            if [[ -f "$set1" && -f "$set2" ]]; then
                comm -12 "$set1" "$set2" | while read -r f; do
                    printf '%s (in src + src-debug)\n' "$f"
                done
            fi
        fi
    done
done

# 复用 R 类资源扫描（resources.arsc 引用）
echo ""
echo "================================================================================"
echo "Resource layout parity (res/ vs AOSP res/)"
echo "================================================================================"
for ressub in res res-keyguard res-product; do
    aosp_res="$AOSP_ROOT/$ressub"
    our_res="$CORE_DIR/$ressub"
    if [[ -d "$aosp_res" && -d "$our_res" ]]; then
        aosp_n=$(find "$aosp_res" -type f 2>/dev/null | wc -l)
        our_n=$(find "$our_res" -type f 2>/dev/null | wc -l)
        echo "$ressub/ → AOSP $aosp_n files / ours $our_n files"
    fi
done

echo ""
echo "================================================================================"
echo "Done.  Diff outputs above.  Always run again after fixing."
echo "================================================================================"
