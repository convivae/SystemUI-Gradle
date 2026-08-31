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

from aosp_paths import aosp_root

# Single AOSP root source (user rule 2026-08-25): tools/aosp_paths.py resolves
# the default and the AOSP_ROOT env override; --aosp-root rebuilds every
# derived constant below (see configure_aosp_root).
AOSP_ROOT = aosp_root()
SOONG_DIR = AOSP_ROOT / "out/soong/.intermediates"

ANIMATIONLIB_DIR = AOSP_ROOT / "frameworks/libs/systemui/animationlib"
ANIMATIONLIB_SOONG = SOONG_DIR / "frameworks/libs/systemui/animationlib/animationlib/android_common"

TRACEUR_DIR = AOSP_ROOT / "packages/apps/Traceur"
TRACEUR_SOONG = SOONG_DIR / "packages/apps/Traceur"

DEFAULT_OUTPUT = Path("libs/aars/animationlib.aar")

def _discover_settingslib_code_jars() -> list:
    """自动发现 SettingsLib 主 target + 全部 static_libs 子模块的 javac JAR，
    以及同一模块的 Kotlin 半边（Task 074 / C4c：AOSP-17 混合 Kotlin/Java 模块
    的 Kotlin 类在 android_common/kotlin/，16 时代 discovery 只并 javac，
    漏掉 BannerAnimationHelper/ResolutionAnimator 等 59 类，R8 闭包报缺）。

    Soong 的 android_library static_libs 是独立编译单元，javac JAR 只含
    Java 源产物、kotlin JAR 只含 Kotlin 源产物，dex 阶段合并进最终 APK。
    为模拟此语义，需把每个模块的 javac + kotlin JAR 都合并到 classes.jar。
    kotlin-only 模块（SettingsTheme/Spa/Metadata 等，无 javac 目录）
    天然不入 discovery —— Theme Kotlin 归 SettingsLibSettingsTheme AAR（既有纪律）。
    """
    base = SOONG_DIR / "frameworks/base/packages/SettingsLib"
    jars = []
    for jar in sorted(base.rglob("*/android_common/javac/*.jar")):
        s = str(jar)
        if "turbine" in s or "aconfig" in s or "flags_lib" in s:
            continue
        jars.append(jar)
        # 同模块 Kotlin 半边（零重叠实测：7 个混合模块 javac∩kotlin = 0）
        kotlin_jar = jar.parent.parent / "kotlin" / jar.name
        if kotlin_jar.is_file():
            jars.append(kotlin_jar)
    return jars


# Declarative artifact configs（canonical inputs，见 artifact-recovery 计划）
def _build_configs() -> dict:
    """Build the declarative artifact configs from the current path constants.

    Called once at import for the default (aosp_paths-resolved) root and
    again by ``configure_aosp_root`` when ``--aosp-root`` is given; the dict
    literal resolves SOONG_DIR/AOSP_ROOT/... at call time, so a rebound
    global is picked up automatically.
    """
    return {
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
        # AOSP-17: source-tree AndroidManifest.xml was deleted upstream (bp has no
        # manifest line); use Soong's generated manifest instead. Task 073 fix:
        # use WifiTrackerLibRes's manifest (package com.android.wifitrackerlib =
        # the R namespace HotspotTile etc. reference), NOT the code module's
        # .nores package (AGP generates the AAR's R class from this package).
        "manifest": SOONG_DIR / "frameworks/opt/net/wifi/libs/WifiTrackerLib/WifiTrackerLibRes/android_common/GeneratedManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/opt/net/wifi/libs/WifiTrackerLib/WifiTrackerLibRes/android_common/R.txt",
        "output": "libs/aars/WifiTrackerLib.aar",
    },
    "iconloader": {
        # AOSP-17 restructure: iconloaderlib split into "iconloader"
        # (src_full_lib — 2 Java facades IconFactory/SimpleIconCache) and
        # "iconloader_base" (src/ — Java + Kotlin + res + R.txt). The consumer
        # closure needs all three implementation JARs merged:
        # iconloader/javac (3) + iconloader_base/javac (21) +
        # iconloader_base/kotlin (120) = 144 disjoint classes.
        # Note: iconloader/android_common/kotlin/ does not exist in 17.
        "code": [
            SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader/android_common/javac/iconloader.jar",
            SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader_base/android_common/javac/iconloader_base.jar",
            SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader_base/android_common/kotlin/iconloader_base.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/libs/systemui/iconloaderlib/res"],
        "manifest": AOSP_ROOT / "frameworks/libs/systemui/iconloaderlib/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/libs/systemui/iconloaderlib/iconloader_base/android_common/R.txt",
        "output": "libs/aars/iconloader.aar",
    },
    "SettingsLib": {
        # 主 target + 全部 static_libs 子模块的 javac + Kotlin JAR
        # （AOSP-17: 34 javac JAR 884 类 + 7 个混合模块 Kotlin 半边 59 类
        # + 主 SettingsLib Kotlin 488 类 = 1431 类。Task 074 / C4c：
        # per-target Kotlin 半边为 R8 闭包新增——BannerAnimationHelper/
        # ResolutionAnimator 等。AOSP-17：DeviceStateRotationLock 已 Kotlin→Java
        # 重写，其 13 类（含 PosturesHelper）由 discovery 的 javac JAR 交付。
        # Theme 的 Kotlin 代码归 SettingsLibSettingsTheme AAR，不得并入
        # （kotlin-only 模块无 javac 目录，discovery 天然排除）。
        "code": _discover_settingslib_code_jars(),
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/SettingsLib/android_common/R.txt",
        "output": "libs/aars/SettingsLib.aar",
    },
    "WindowManager-Shell": {
        # javac JAR (Java classes) + kotlin JAR (Kotlin classes, 如 HasWMComponent) 合并；
        # AOSP-17: 上游删除了 WindowManager-Shell-proto (nano) target——proto/protolog 类
        # （ProtoLogController、ProtoLogImpl 等）已并入主 javac/kotlin jar；lite-proto
        # static_lib 的 Soong javac 产物仍单独交付（bp L148），共 1423+1632+69=3124 类
        "code": [
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/javac/WindowManager-Shell.jar",
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/kotlin/WindowManager-Shell.jar",
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell-lite-proto/android_common/javac/WindowManager-Shell-lite-proto.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/base/libs/WindowManager/Shell/res"],
        "manifest": AOSP_ROOT / "frameworks/base/libs/WindowManager/Shell/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/R.txt",
        "output": "libs/aars/WindowManager-Shell.aar",
        # AOSP-16 时代这些 shared AIDL 类由 WindowManager-Shell-shared 交付，从主 AAR
        # 剔除；17 主 jar 已不含这三类（实测），前缀保留为防御性 no-op。
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
        # Task 073（C4b）：17 bp 把 shared AIDL 接口拆入 WindowManager-Shell-shared-aidls
        # static_libs（IShellTransitions / AnimatedSurface / IHomeTransitionListener /
        # IFocusTransitionListener / IOverviewOverlayLeashInvalidationCallback），
        # main jar 不含它们（animation 模块 ActivityTransitionAnimator import 报缺）；
        # 并入 aidls javac jar 补齐闭包（bp static_libs 语义，TraceurCommon 先例）。
        # 类集变化 → 本地 maven 坐标 2.0.0 → 2.0.1（install_aar_to_maven.py 同步升）。
        "code": [
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/shared/WindowManager-Shell-shared/android_common/javac/WindowManager-Shell-shared.jar",
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/shared/WindowManager-Shell-shared/android_common/kotlin/WindowManager-Shell-shared.jar",
            SOONG_DIR / "frameworks/base/libs/WindowManager/Shell/shared/WindowManager-Shell-shared-aidls/android_common/javac/WindowManager-Shell-shared-aidls.jar",
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
    # ↓↓↓ Task 040（R8 Batch 4D）：10 个新增 SettingsLib per-target res-only AAR。
    # 各自拥有真实 AOSP 资源（共 346 文件）与独立 R namespace；代码类已由
    # SettingsLib.aar 合并交付，这里只补各自 res；AAR 经 SettingsLib POM 传递
    # 依赖接线（ADR 0005），consumer 不新增依赖行。
    "SettingsLibMainSwitchPreference": {
        # namespace com.android.settingslib.widget.mainswitch；22 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/MainSwitchPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/MainSwitchPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/MainSwitchPreference/SettingsLibMainSwitchPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibMainSwitchPreference.aar",
    },
    "SettingsLibAppPreference": {
        # namespace com.android.settingslib.widget.preference.app；91 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/AppPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/AppPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/AppPreference/SettingsLibAppPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibAppPreference.aar",
    },
    "SettingsLibBannerMessagePreference": {
        # namespace com.android.settingslib.widget.preference.banner；96 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/BannerMessagePreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/BannerMessagePreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/BannerMessagePreference/SettingsLibBannerMessagePreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibBannerMessagePreference.aar",
    },
    "SettingsLibBarChartPreference": {
        # namespace com.android.settingslib.widget.preference.barchart；6 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/BarChartPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/BarChartPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/BarChartPreference/SettingsLibBarChartPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibBarChartPreference.aar",
    },
    "SettingsLibButtonPreference": {
        # namespace com.android.settingslib.widget.preference.button；23 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/ButtonPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/ButtonPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/ButtonPreference/SettingsLibButtonPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibButtonPreference.aar",
    },
    "SettingsLibFooterPreference": {
        # namespace com.android.settingslib.widget.preference.footer；91 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/FooterPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/FooterPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/FooterPreference/SettingsLibFooterPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibFooterPreference.aar",
    },
    "SettingsLibIllustrationPreference": {
        # namespace com.android.settingslib.widget.preference.illustration；6 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/IllustrationPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/IllustrationPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/IllustrationPreference/SettingsLibIllustrationPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibIllustrationPreference.aar",
    },
    "SettingsLibSliderPreference": {
        # namespace com.android.settingslib.widget.preference.slider；5 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/SliderPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/SliderPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/SliderPreference/SettingsLibSliderPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibSliderPreference.aar",
    },
    "SettingsLibUsageProgressBarPreference": {
        # namespace com.android.settingslib.widget.preference.usage；1 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/UsageProgressBarPreference/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/UsageProgressBarPreference/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/UsageProgressBarPreference/SettingsLibUsageProgressBarPreference/android_common/R.txt",
        "output": "libs/aars/SettingsLibUsageProgressBarPreference.aar",
    },
    "SettingsLibSettingsSpinner": {
        # namespace com.android.settingslib.widget.spinner；5 个 res 文件
        "code": [],
        "res": [AOSP_ROOT / "frameworks/base/packages/SettingsLib/SettingsSpinner/res"],
        "manifest": AOSP_ROOT / "frameworks/base/packages/SettingsLib/SettingsSpinner/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/packages/SettingsLib/SettingsSpinner/SettingsLibSettingsSpinner/android_common/R.txt",
        "output": "libs/aars/SettingsLibSettingsSpinner.aar",
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
    # ↓↓↓ Task 072（C4 接线）：dynamiccolors（17 SystemUI-res bp static_libs L425）。
    # frameworks/libs/systemui/dynamiccolors：res-only android_library（无 srcs），
    # namespace com.android.systemui.dynamiccolors；提供 materialColor* 色板
    # （SystemUI-res 17 的 styles.xml/colors.xml/drawable-night 直接引用）。
    # 规则 F tier②（非 SystemUI 自有代码）；单 consumer（:SystemUI-res）→
    # 直接 AAR（Task 059 例外，不入本地 maven、不进 catalog）。
    "dynamiccolors": {
        "code": [],
        "res": [AOSP_ROOT / "frameworks/libs/systemui/dynamiccolors/res"],
        "manifest": AOSP_ROOT / "frameworks/libs/systemui/dynamiccolors/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/libs/systemui/dynamiccolors/dynamiccolors/android_common/R.txt",
        "output": "libs/aars/dynamiccolors.aar",
    },
    # ↓↓↓ Task 073（C4b 编译闭环）：personalcontext_ace_visualizer（17 SystemUI-core bp
    # static_libs；SystemUI-17 源码 import com.android.personalcontext.ace.visualizer.{compat,connector}.*
    # 与 common.wrappers.wrap）。规则 F tier② AAR（frameworks/libs/systemui/ace，非 SystemUI 自有代码）。
    # code = visualizer Kotlin jar + personalcontext_ace_common Kotlin jar 合并
    #（bp static_libs 闭包，TraceurCommon 先例；两 jar 互不相交已验证，common 无 res/
    # 无 R 引用，其 EmbeddedScrollEvent 同名覆盖 ace_common_embeddedscroll）。
    # KSP 输出（ksp-classes.jar）为空，Kotlin jar 即完整类集。单 consumer（:SystemUI-core）
    # → 直接 AAR（Task 059 例外），不入本地 maven、不进 catalog。
    "personalcontext_ace_visualizer": {
        "code": [
            SOONG_DIR / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/visualizer/"
            "personalcontext_ace_visualizer/android_common/kotlin/personalcontext_ace_visualizer.jar",
            # Task 073 fix: javac jar carries the dagger-generated companion
            # @Provides factories (PersonalContextModuleVisualizer_Companion_*
            # 19 classes) — the Kotlin jar alone misses them and the
            # application Dagger component cannot resolve its imports.
            SOONG_DIR / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/visualizer/"
            "personalcontext_ace_visualizer/android_common/javac/personalcontext_ace_visualizer.jar",
            SOONG_DIR / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/common/"
            "personalcontext_ace_common/android_common/kotlin/personalcontext_ace_common.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/visualizer/res"],
        "manifest": AOSP_ROOT / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/visualizer/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/visualizer/"
        "personalcontext_ace_visualizer/android_common/R.txt",
        "output": "libs/aars/personalcontext_ace_visualizer.aar",
    },
    # ↓↓↓ Task 073：personalcontext_ace_client（visualizer bp static_libs 闭包成员，
    # 自有 R namespace com.android.personalcontext.ace.client——clientsdk/compat/res 的
    # declare-styleable/id，AceEmbeddedSurfaceViewCompat 引用 client R），与 visualizer
    # 拆两个 AAR 交付（单一 AAR 无法承载两个 R namespace；ADR 0001 同族多 namespace 先例）。
    # 262 类（含 ClientActionInsight，visualizer 公有签名引用）。单 consumer（:SystemUI-core）
    # → 直接 AAR。
    "personalcontext_ace_client": {
        "code": [
            SOONG_DIR / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/client/"
            "personalcontext_ace_client/android_common/kotlin/personalcontext_ace_client.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/client/clientsdk/compat/res"],
        "manifest": AOSP_ROOT / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/client/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/libs/systemui/ace/src/com/android/personalcontext/ace/client/"
        "personalcontext_ace_client/android_common/R.txt",
        "output": "libs/aars/personalcontext_ace_client.aar",
    },
    # ↓↓↓ Task 073：SerialPortAccessDialog（17 SystemUI-core bp static_libs；
    # frameworks/base/libs/serial/accessdialog，规则 F tier② AAR 含 res）。
    # 4 kt（AccessDialogHelper/Activity、SerialAccessManager/Impl）+ 全 locale strings res，
    # 自有 R namespace com.android.serial.accessdialog；manifest 携带 activity 声明 +
    # MANAGE_SERIAL_PORTS 权限（必须 AAR 交付以并入 app manifest）。注意 manifest 的
    # android:theme="@style/Theme.SystemUI.Dialog.Alert" 引用 SystemUI-res 资源
    #（bp static_libs: SystemUI-res），Gradle 侧由 app 合并资源解析。单 consumer（:SystemUI-core）
    # → 直接 AAR。
    "SerialPortAccessDialog": {
        "code": [
            SOONG_DIR / "frameworks/base/libs/serial/accessdialog/SerialPortAccessDialog/"
            "android_common/kotlin/SerialPortAccessDialog.jar",
        ],
        "res": [AOSP_ROOT / "frameworks/base/libs/serial/accessdialog/res"],
        "manifest": AOSP_ROOT / "frameworks/base/libs/serial/accessdialog/AndroidManifest.xml",
        "rtxt": SOONG_DIR / "frameworks/base/libs/serial/accessdialog/SerialPortAccessDialog/"
        "android_common/R.txt",
        "output": "libs/aars/SerialPortAccessDialog.aar",
    },
    }


CONFIGS = _build_configs()


def configure_aosp_root(root: Path) -> None:
    """Re-point every derived path constant and CONFIGS at another AOSP tree."""
    global AOSP_ROOT, SOONG_DIR, ANIMATIONLIB_DIR, ANIMATIONLIB_SOONG
    global TRACEUR_DIR, TRACEUR_SOONG, CONFIGS
    AOSP_ROOT = Path(root)
    SOONG_DIR = AOSP_ROOT / "out/soong/.intermediates"
    ANIMATIONLIB_DIR = AOSP_ROOT / "frameworks/libs/systemui/animationlib"
    ANIMATIONLIB_SOONG = (
        SOONG_DIR / "frameworks/libs/systemui/animationlib/animationlib/android_common"
    )
    TRACEUR_DIR = AOSP_ROOT / "packages/apps/Traceur"
    TRACEUR_SOONG = SOONG_DIR / "packages/apps/Traceur"
    CONFIGS = _build_configs()


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
    ap.add_argument("--aosp-root", type=Path, default=None,
                   help="AOSP 树根路径（默认走 tools/aosp_paths.py 单一来源；"
                        "亦可用 AOSP_ROOT 环境变量覆盖）")
    args = ap.parse_args()

    if args.aosp_root is not None:
        configure_aosp_root(args.aosp_root)

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
