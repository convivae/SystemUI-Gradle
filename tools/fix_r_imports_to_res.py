#!/usr/bin/env python3
"""
fix_r_imports_to_res.py — DEPRECATED 暂不启用 — 将 com.android.systemui.R 改回 AOSP 的 com.android.systemui.res.R

**状态 (2026-07-30)**: 暂不启用 (deprecated)。运行后短期错误数从 66 上升至 78，因为
AGP 默认把 R 类生成在 `namespace` 下 (`com.android.systemui.R`)，改成 import `com.android.systemui.res.R`
后部分 R 字段不可见。我们需要先解决 AGP 生成 R 类到 res 子包的问题后，才能安全启用本脚本。

AOSP SystemUI 用 `import com.android.systemui.res.R` (即 res 子包)，共 523 处。
我们 Gradle 改造时错误统一改为 `import com.android.systemui.R`，共 1062 处。

策略：把所有 com.android.systemui.R 改回 com.android.systemui.res.R (1:1 对齐 AOSP)

注意：
- 不改 com.android.settingslib.R / com.android.internal.R / com.android.traceur.res.R
- 同时处理 alias 形式 (import com.android.systemui.R as XxxR)
- 同时处理全限定形式 (com.android.systemui.R.string.X → com.android.systemui.res.R.string.X)

启用方法：
    1. 解决 AGP 把 R 类生成到 com.android.systemui.res (而非 com.android.systemui):
       - 方案 A: AGP namespace 改成 "com.android.systemui.res"
         (问题: 依赖方期望 namespace 是 com.android.systemui)
       - 方案 B: 使用 AGP transformGeneratedRClasses API 把生成的 R 字节码重写到 res 子包
       - 方案 C: 用 buildSrc 自定义 R 生成 task
    2. 运行 `python3 tools/fix_r_imports_to_res.py`
    3. 验证 `grep -r "import com.android.systemui.R$" SystemUI-core/src/` 返回 0
"""

import re
from pathlib import Path

PROJECT_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")

def fix_file(file_path):
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    original = content

    # import com.android.systemui.R  -> import com.android.systemui.res.R
    # 同时处理 alias 形式: import com.android.systemui.R as XxxR
    content = re.sub(
        r"^import\s+com\.android\.systemui\.R(\s+as\s+\w+)?\s*$",
        lambda m: "import com.android.systemui.res.R" + (m.group(1) if m.group(1) else ""),
        content,
        flags=re.MULTILINE,
    )

    # 完全限定引用 com.android.systemui.R.X.Y → com.android.systemui.res.R.X.Y
    # （AOSP 风格；项目已统一用 import 别名但有些保留全限定）
    content = re.sub(
        r"com\.android\.systemui\.R(\.(?:string|array|drawable|layout|color|dimen|id|style|integer|bool|attr|plurals|raw|menu|xml|font|anim|interpolator|mipmap))",
        r"com.android.systemui.res.R\1",
        content,
    )

    if content != original:
        file_path.write_text(content, encoding="utf-8")
        return True
    return False


def main():
    # 处理 SystemUI-core/src + SystemUI-core/src-debug + SystemUI-core/src-release
    core_src = PROJECT_ROOT / "SystemUI-core" / "src"
    fixed_count = 0
    total_count = 0

    for f in core_src.rglob("*"):
        if f.suffix in (".kt", ".java"):
            total_count += 1
            if fix_file(f):
                fixed_count += 1

    print(f"Total files scanned: {total_count}")
    print(f"Files modified: {fixed_count}")


if __name__ == "__main__":
    main()