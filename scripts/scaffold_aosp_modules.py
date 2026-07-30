#!/usr/bin/env python3
"""Phase A: 为 AOSP bp 1:1 子模块生成脚手架。

生成每个模块的：
  - src/main/AndroidManifest.xml
  - build.gradle.kts

只生成脚手架（空 src/main 目录），不移动文件。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

GRADLE_ROOT = Path("/home/conv/myspace/SystemUI-Gradle")


# 13 个新子模块
# 字段：
#   gradle_name:         Gradle 子模块名
#   type:                android_library | java_library
#   namespace:           Android namespace
#   bp_path:             AOSP bp 路径
#   aosp_module:         AOSP module name
#   src_subdir:          在我们 gradle 子模块里，文件应放在 src/main/ 下哪个子目录
#                        （空=直接 src/main/java 或 src/main/kotlin，默认 java）
#   compile_only:        compileOnly 依赖列表
#   implementation:      implementation 依赖列表

MODULES = [
    # kairos — AOSP java_library "kairos"
    {
        "gradle_name": "SystemUI-utils-kairos",
        "type": "android_library",  # 兼容现有结构（java-library 也行，但保持一致用 android.library）
        "namespace": "com.android.systemui.kairos",
        "bp_path": "utils/kairos",
        "aosp_module": "kairos",
        "description": "Kairos FRP library",
        "dependencies": [
            ('implementation', "libs.kotlin.stdlib"),
            ('implementation', "libs.kotlinx.coroutines.core"),
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
        ],
    },
    # PlatformComposeCore — android_library
    {
        "gradle_name": "SystemUI-compose-core",
        "type": "android_library",
        "namespace": "com.android.compose",
        "bp_path": "compose/core",
        "aosp_module": "PlatformComposeCore",
        "description": "Platform Compose Core (Animation, theme, gesture, modifiers)",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('implementation', "libs.androidx.annotation"),
            ('implementation', "libs.kotlin.stdlib"),
            ('implementation', "libs.kotlinx.coroutines.core"),
            # androidx.core 1.13+ 提供 WindowInsetsControllerCompat
            ('implementation', "androidx.core:core-ktx:1.13.1"),
            # WindowSizeClass.kt 用 androidx.window.layout.WindowMetricsCalculator
            ('implementation', "androidx.window:window:1.3.0"),
            # material3-window-size-class: WindowSizeClass.calculateFromSize()
            ('implementation', "androidx.compose.material3:material3-window-size-class:1.3.1"),
            ('implementation', "androidx.compose.runtime:runtime:1.7.5"),
            ('implementation', "androidx.compose.foundation:foundation:1.7.5"),
            ('implementation', "androidx.compose.ui:ui:1.7.5"),
            ('implementation', "androidx.compose.ui:ui-graphics:1.7.5"),
            ('implementation', "androidx.compose.animation:animation:1.7.5"),
            ('implementation', "androidx.compose.animation:animation-graphics:1.7.5"),
            ('implementation', "androidx.compose.material3:material3:1.3.1"),
            ('implementation', "androidx.compose.material:material-icons-core:1.7.5"),
            ('implementation', "androidx.compose.material:material-icons-extended:1.7.5"),
            ('implementation', "androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7"),
            # Interpolator / InterpolatorsAndroidX (com.android.app.animation.*) 来自 animationlib
            ('implementation', 'project(":SystemUI-animationlib")'),
            # Expandable / TransitionAnimator (com.android.systemui.animation.*) 来自 animation
            ('implementation', 'project(":SystemUI-animation")'),
            # androidx.savedstate: 来自 androidx.savedstate.core
            ('implementation', "androidx.savedstate:savedstate-ktx:1.2.1"),
            # tracinglib-platform: com.android.app.tracing.traceSection
            ('implementation', 'files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar")'),
            ('implementation', "androidx.tracing:tracing:1.2.0"),
        ],
    },
    # PlatformComposeSceneTransitionLayout — android_library
    {
        "gradle_name": "SystemUI-compose-scene",
        "type": "android_library",
        "namespace": "com.android.compose.animation.scene",
        "bp_path": "compose/scene",
        "aosp_module": "PlatformComposeSceneTransitionLayout",
        "description": "Platform Compose SceneTransitionLayout",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('implementation', "libs.androidx.annotation"),
            ('implementation', "libs.kotlin.stdlib"),
            ('implementation', "libs.kotlinx.coroutines.core"),
            # Compose 基础
            ('implementation', "androidx.compose.runtime:runtime:1.7.5"),
            ('implementation', "androidx.compose.foundation:foundation:1.7.5"),
            ('implementation', "androidx.compose.ui:ui:1.7.5"),
            ('implementation', "androidx.compose.ui:ui-graphics:1.7.5"),
            ('implementation', "androidx.compose.animation:animation:1.7.5"),
            ('implementation', "androidx.compose.animation:animation-graphics:1.7.5"),
            ('implementation', "androidx.compose.material3:material3:1.3.1"),
            # activity-compose: BackEventCompat / PredictiveBackHandler
            ('implementation', "androidx.activity:activity-compose:1.9.3"),
            # 内部依赖：thenIf / modifiers / drawInContainer 等扩展
            ('implementation', 'project(":SystemUI-compose-core")'),
        ],
    },
    # BiometricsSharedLib — android_library
    {
        "gradle_name": "SystemUI-shared-biometrics",
        "type": "android_library",
        "namespace": "com.android.systemui.shared.biometrics",
        "bp_path": "shared/biometrics",
        "aosp_module": "BiometricsSharedLib",
        "description": "Biometrics Shared Library (Udfps, PromptKind, etc.)",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('implementation', "libs.kotlin.stdlib"),
        ],
    },
    # SystemUISharedLib-Keyguard — android_library
    {
        "gradle_name": "SystemUI-shared-keyguard",
        "type": "android_library",
        "namespace": "com.android.keyguard",
        "bp_path": "shared/keyguard",
        "aosp_module": "SystemUISharedLib-Keyguard",
        "description": "Keyguard shared library (PinShapeInput, BasePasswordTextView)",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('implementation', "libs.androidx.annotation"),
        ],
    },
    # SystemUI-proto (顶层)
    # 注：AOSP SystemUI-proto 是 java_library（非 android_library），源含多个包路径
    #     我们用 java-library 避免 namespace 限制
    {
        "gradle_name": "SystemUI-proto",
        "type": "java_library",
        "namespace": None,
        "bp_path": ".",
        "aosp_module": "SystemUI-proto",
        "description": "SystemUI protobuf.nano generated classes (Flags, etc.)",
        "dependencies": [
            ('implementation', "libs.kotlin.stdlib"),
        ],
        "is_java_library": True,
    },
    # pods/com/android/systemui/dagger (api) — java_library
    {
        "gradle_name": "SystemUI-pods-dagger",
        "type": "android_library",
        "namespace": "com.android.systemui.dagger",
        "bp_path": "pods/com/android/systemui/dagger",
        "aosp_module": "api",
        "description": "Dagger qualifiers (Application, Background, Main, etc.)",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('compileOnly', "libs.dagger"),
            ('implementation', "libs.androidx.annotation"),
            ('implementation', "libs.kotlin.stdlib"),
        ],
    },
    # pods/com/android/systemui/retail (impl) — java_library
    {
        "gradle_name": "SystemUI-pods-retail",
        "type": "android_library",
        "namespace": "com.android.systemui.retail",
        "bp_path": "pods/com/android/systemui/retail",
        "aosp_module": "impl",
        "description": "Retail mode impl (RetailModeModule)",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('implementation', "libs.dagger"),
            ('implementation', "libs.kotlin.stdlib"),
            ('implementation', "libs.kotlinx.coroutines.core"),
            # retail:impl 依赖 data:api+impl 和 domain:api+impl
            ('implementation', 'project(":SystemUI-pods-data")'),
            ('implementation', 'project(":SystemUI-pods-domain")'),
        ],
    },
    # pods/com/android/systemui/retail/data (api+impl 合并)
    {
        "gradle_name": "SystemUI-pods-data",
        "type": "android_library",
        "namespace": "com.android.systemui.retail.data",
        "bp_path": "pods/com/android/systemui/retail/data",
        "aosp_module": "api+impl",
        "description": "Retail data (api+impl 合并)",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('implementation', "libs.kotlin.stdlib"),
            ('implementation', "libs.kotlinx.coroutines.core"),
            ('implementation', "libs.kotlinx.coroutines.android"),
            ('implementation', "libs.dagger"),
            # tracinglib-platform 提供 traceSection
            ('implementation', 'files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar")'),
            # 内部 common 工具（conflatedCallbackFlow 等）
            ('implementation', 'project(":SystemUI-common")'),
            # AnyThread / WorkerThread / Background / Main
            ('implementation', 'project(":SystemUI-pods-dagger")'),
            # GlobalSettings / SecureSettings
            ('implementation', 'project(":SystemUI-pods-settings")'),
        ],
    },
    # pods/com/android/systemui/retail/domain (api+impl 合并)
    {
        "gradle_name": "SystemUI-pods-domain",
        "type": "android_library",
        "namespace": "com.android.systemui.retail.domain",
        "bp_path": "pods/com/android/systemui/retail/domain",
        "aosp_module": "api+impl",
        "description": "Retail domain (api+impl 合并)",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('implementation', "libs.kotlin.stdlib"),
            ('implementation', "libs.kotlinx.coroutines.core"),
            ('implementation', "libs.kotlinx.coroutines.android"),
            ('implementation', 'project(":SystemUI-pods-data")'),
            # SysUISingleton / Inject 在 :SystemUI-pods-dagger
            ('implementation', 'project(":SystemUI-pods-dagger")'),
            ('implementation', "libs.dagger"),
            # tracinglib-platform 提供 traceSection
            ('implementation', 'files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar")'),
        ],
    },
    # pods/com/android/systemui/util/settings (api)
    {
        "gradle_name": "SystemUI-pods-settings",
        "type": "android_library",
        "namespace": "com.android.systemui.util.settings",
        "bp_path": "pods/com/android/systemui/util/settings",
        "aosp_module": "api",
        "description": "Settings pod API (GlobalSettings, SecureSettings, etc.)",
        "dependencies": [
            ('compileOnly', 'files("${rootProject.projectDir}/libs/framework.jar")'),
            ('implementation', "libs.kotlin.stdlib"),
            ('implementation', "libs.kotlinx.coroutines.core"),
            ('implementation', "libs.kotlinx.coroutines.android"),
            ('implementation', "libs.androidx.annotation"),
            ('implementation', "libs.dagger"),  # for javax.inject
            # conflatedCallbackFlow 在 SystemUI-common
            ('implementation', 'project(":SystemUI-common")'),
            # AnyThread / WorkerThread / Background / Main 在 :SystemUI-pods-dagger
            ('implementation', 'project(":SystemUI-pods-dagger")'),
            # tracinglib-platform 提供 traceSection
            ('implementation', 'files("${rootProject.projectDir}/libs/prebuilts/tracinglib-platform.jar")'),
            # systemui-flags: SettingsProxyExt 用 Flags.something()
            ('implementation', 'files("${rootProject.projectDir}/libs/systemui-flags.jar")'),
        ],
    },
]


def render_module(m: dict) -> str:
    """Render build.gradle.kts content for a module."""
    is_java_lib = m.get("is_java_library", False)
    lines = []
    lines.append("// GENERATED by scripts/scaffold_aosp_modules.py — AOSP bp 1:1")
    lines.append(f"// AOSP bp module: {m['aosp_module']} (bp path: {m['bp_path']})")
    lines.append(f"// {m['description']}")
    lines.append("")

    if is_java_lib:
        lines.append("plugins {")
        lines.append('    alias(libs.plugins.kotlin.jvm)')
        lines.append("}")
        lines.append("")
        lines.append("java {")
        lines.append("    sourceCompatibility = JavaVersion.VERSION_21")
        lines.append("    targetCompatibility = JavaVersion.VERSION_21")
        lines.append("}")
        lines.append("")
        lines.append("kotlin {")
        lines.append("    jvmToolchain(21)")
        lines.append("}")
        lines.append("")
        lines.append("dependencies {")
        already_has_framework = any(
            cfg == "compileOnly" and "framework.jar" in expr
            for cfg, expr in m["dependencies"]
        )
        if not already_has_framework:
            lines.append('    // Framework APIs - provided by system at runtime')
            lines.append('    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))')
        for cfg, expr in m["dependencies"]:
            lines.append(f"    {cfg}({expr})")
        lines.append("}")
        lines.append("")
        return "\n".join(lines)

    # android_library 形式
    lines.append("plugins {")
    lines.append("    alias(libs.plugins.android.library)")
    lines.append("    alias(libs.plugins.kotlin.android)")
    lines.append("}")
    lines.append("")
    lines.append("android {")
    lines.append(f'    namespace = "{m["namespace"]}"')
    lines.append('    compileSdkPreview = "SysUISdk"')
    lines.append("")
    lines.append("    defaultConfig {")
    lines.append("        minSdk = 32")
    lines.append("    }")
    lines.append("")
    lines.append("    sourceSets {")
    lines.append('        getByName("main") {')
    lines.append('            java.srcDirs("src/main/java")')
    lines.append('            manifest.srcFile("src/main/AndroidManifest.xml")')
    lines.append("        }")
    lines.append("    }")
    lines.append("")
    lines.append("    compileOptions {")
    lines.append("        sourceCompatibility = JavaVersion.VERSION_21")
    lines.append("        targetCompatibility = JavaVersion.VERSION_21")
    lines.append("    }")
    lines.append("")
    lines.append("    kotlin {")
    lines.append("        jvmToolchain(21)")
    lines.append("    }")
    lines.append("")
    lines.append("    lint {")
    lines.append("        abortOnError = false")
    lines.append("    }")
    lines.append("")
    # 加 opt-in 给 PlatformComposeCore / Scene 模块用
    if m["gradle_name"] in ("SystemUI-compose-core", "SystemUI-compose-scene"):
        lines.append("    // Platform Compose 含 Experimental API（OverscrollEffect / AnimatedContent 等）")
        lines.append("    kotlinOptions {")
        lines.append("        freeCompilerArgs = freeCompilerArgs + listOf(")
        lines.append('            "-opt-in=androidx.compose.foundation.ExperimentalFoundationApi",')
        lines.append('            "-opt-in=androidx.compose.animation.ExperimentalAnimationApi",')
        lines.append('            "-opt-in=androidx.compose.animation.core.ExperimentalAnimationSpecApi",')
        lines.append('            "-opt-in=androidx.compose.material3.ExperimentalMaterial3Api",')
        lines.append('            "-opt-in=androidx.compose.material3.windowsizeclass.ExperimentalMaterial3WindowSizeClassApi",')
        lines.append("        )")
        lines.append("    }")
    lines.append("}")
    lines.append("")
    lines.append("dependencies {")
    already_has_framework = False
    for cfg, expr in m["dependencies"]:
        if expr.startswith("libs."):
            lines.append(f"    {cfg}({expr})")
        elif expr.startswith("project("):
            lines.append(f"    {cfg}({expr})")
        elif expr.startswith("files("):
            lines.append(f"    {cfg}({expr})")
        else:
            # bare maven coordinate like "androidx.window:window:1.3.0" → 加双引号
            lines.append(f'    {cfg}("{expr}")')
        # 检查 framework
        if cfg == "compileOnly" and "framework.jar" in expr:
            already_has_framework = True
    if not already_has_framework:
        lines.append('    // Framework APIs - provided by system at runtime')
        lines.append('    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


ANDROID_MANIFEST_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<!-- GENERATED by scripts/scaffold_aosp_modules.py — AOSP bp 1:1 -->
<!-- AOSP bp module: {aosp_module} (bp path: {bp_path}) -->
<!-- {description} -->
<manifest xmlns:android="http://schemas.android.com/apk/res/android" />
"""


def main() -> int:
    for m in MODULES:
        mod_dir = GRADLE_ROOT / m["gradle_name"]
        is_java_lib = m.get("is_java_library", False)

        if is_java_lib:
            # java-library: 无 AndroidManifest、无 android 块
            src_main = mod_dir / "src" / "main"
            java_dir = src_main / "java"
            java_dir.mkdir(parents=True, exist_ok=True)
        else:
            src_main = mod_dir / "src" / "main"
            java_dir = src_main / "java"
            java_dir.mkdir(parents=True, exist_ok=True)

            manifest = src_main / "AndroidManifest.xml"
            if not manifest.exists():
                manifest.write_text(ANDROID_MANIFEST_TEMPLATE.format(**m))

        gradle_file = mod_dir / "build.gradle.kts"
        if not gradle_file.exists():
            gradle_file.write_text(render_module(m))
            print(f"created: {gradle_file}")
        else:
            print(f"skipped (exists): {gradle_file}")

    print()
    print(f"Total modules scaffolded: {len(MODULES)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())