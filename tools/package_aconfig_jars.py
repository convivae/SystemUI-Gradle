#!/usr/bin/env python3
"""Package complete aconfig runtime JARs from their owning Soong javac outputs.

Every artifact is a byte-identical copy of an AOSP ``android_common/javac``
JAR that must contain exactly the five generated runtime classes
(CustomFeatureFlags, FakeFeatureFlagsImpl, FeatureFlags, FeatureFlagsImpl,
Flags) under its configured package. turbine outputs and any other class
layout are rejected.
"""
from pathlib import Path
import argparse
import shutil
import zipfile

from aosp_paths import soong_intermediates

AOSP_INTERMEDIATES = soong_intermediates()

RUNTIME_CLASS_NAMES = frozenset(
    (
        "CustomFeatureFlags",
        "FakeFeatureFlagsImpl",
        "FeatureFlags",
        "FeatureFlagsImpl",
        "Flags",
    )
)


def _soong(path: str) -> Path:
    return AOSP_INTERMEDIATES / path


# name -> (owning Soong javac source, destination, runtime package)
CONFIGS = {
    # Task 055 batch: the 11 residual aconfig runtime-closure hazards found by
    # the APK prescan in task 054. Each owning java_aconfig_library lives in
    # frameworks/base/AconfigFlags.bp (framework-minus-apex-aconfig-java-defaults,
    # i.e. the device only carries the hidden_from_bootclasspath JarJar twin);
    # the base-variant android_common/javac JAR (backing API
    # PlatformAconfigPackageInternal, verified on the device bootclasspath)
    # is packaged byte-identically.
    "smartspace-flags": (
        _soong(
            "frameworks/base/android.app.smartspace.flags-aconfig-java/"
            "android_common/javac/"
            "android.app.smartspace.flags-aconfig-java.jar"
        ),
        Path("libs/smartspace-flags.jar"),
        "android.app.smartspace.flags",
    ),
    "content-pm-flags": (
        _soong(
            "frameworks/base/android.content.pm.flags-aconfig-java/"
            "android_common/javac/"
            "android.content.pm.flags-aconfig-java.jar"
        ),
        Path("libs/content-pm-flags.jar"),
        "android.content.pm",
    ),
    "biometrics-flags": (
        _soong(
            "frameworks/base/android.hardware.biometrics.flags-aconfig-java/"
            "android_common/javac/"
            "android.hardware.biometrics.flags-aconfig-java.jar"
        ),
        Path("libs/biometrics-flags.jar"),
        "android.hardware.biometrics",
    ),
    "usb-flags": (
        _soong(
            "frameworks/base/android.hardware.usb.flags-aconfig-java/"
            "android_common/javac/"
            "android.hardware.usb.flags-aconfig-java.jar"
        ),
        Path("libs/usb-flags.jar"),
        "android.hardware.usb.flags",
    ),
    "net-platform-flags": (
        _soong(
            "frameworks/base/android.net.platform.flags-aconfig-java/"
            "android_common/javac/"
            "android.net.platform.flags-aconfig-java.jar"
        ),
        Path("libs/net-platform-flags.jar"),
        "android.net.platform.flags",
    ),
    "permission-flags": (
        _soong(
            "frameworks/base/android.permission.flags-aconfig-java/"
            "android_common/javac/"
            "android.permission.flags-aconfig-java.jar"
        ),
        Path("libs/permission-flags.jar"),
        "android.permission.flags",
    ),
    "provider-flags": (
        _soong(
            "frameworks/base/android.provider.flags-aconfig-java/"
            "android_common/javac/"
            "android.provider.flags-aconfig-java.jar"
        ),
        Path("libs/provider-flags.jar"),
        "android.provider",
    ),
    "security-flags": (
        _soong(
            "frameworks/base/android.security.flags-aconfig-java/"
            "android_common/javac/"
            "android.security.flags-aconfig-java.jar"
        ),
        Path("libs/security-flags.jar"),
        "android.security",
    ),
    "service-controls-flags": (
        _soong(
            "frameworks/base/android.service.controls.flags-aconfig-java/"
            "android_common/javac/"
            "android.service.controls.flags-aconfig-java.jar"
        ),
        Path("libs/service-controls-flags.jar"),
        "android.service.controls.flags",
    ),
    "service-notification-flags": (
        _soong(
            "frameworks/base/android.service.notification.flags-aconfig-java/"
            "android_common/javac/"
            "android.service.notification.flags-aconfig-java.jar"
        ),
        Path("libs/service-notification-flags.jar"),
        "android.service.notification",
    ),
    "quickaccesswallet-flags": (
        _soong(
            "frameworks/base/android.service.quickaccesswallet.flags-aconfig-java/"
            "android_common/javac/"
            "android.service.quickaccesswallet.flags-aconfig-java.jar"
        ),
        Path("libs/quickaccesswallet-flags.jar"),
        "android.service.quickaccesswallet",
    ),
    "systemui-shared-flags": (
        _soong(
            "frameworks/libs/systemui/aconfig/"
            "com_android_systemui_shared_flags_lib/android_common/javac/"
            "com_android_systemui_shared_flags_lib.jar"
        ),
        Path("libs/systemui-shared-flags.jar"),
        "com.android.systemui.shared",
    ),
    "wifi-flags": (
        _soong(
            "packages/modules/Wifi/flags/wifi_aconfig_flags_lib/"
            "android_common/javac/wifi_aconfig_flags_lib.jar"
        ),
        Path("libs/wifi-flags.jar"),
        "com.android.wifi.flags",
    ),
    "wm-shell-flags": (
        _soong(
            "frameworks/base/libs/WindowManager/Shell/aconfig/"
            "com_android_wm_shell_flags_lib/android_common/javac/"
            "com_android_wm_shell_flags_lib.jar"
        ),
        Path("libs/wm-shell-flags.jar"),
        "com.android.wm.shell",
    ),
    "window-flags": (
        _soong(
            "frameworks/base/com.android.window.flags.window-aconfig-java/"
            "android_common/javac/"
            "com.android.window.flags.window-aconfig-java.jar"
        ),
        Path("libs/window-flags.jar"),
        "com.android.window.flags",
    ),
    "device-state-feature-flags": (
        _soong(
            "frameworks/base/android.hardware.devicestate.feature.flags-aconfig-java/"
            "android_common/javac/"
            "android.hardware.devicestate.feature.flags-aconfig-java.jar"
        ),
        Path("libs/device-state-feature-flags.jar"),
        "android.hardware.devicestate.feature.flags",
    ),
    "android-os-flags": (
        _soong(
            "frameworks/base/android.os.flags-aconfig-java/"
            "android_common/javac/"
            "android.os.flags-aconfig-java.jar"
        ),
        Path("libs/android-os-flags.jar"),
        "android.os",
    ),
    "systemui-flags": (
        _soong(
            "frameworks/base/packages/SystemUI/aconfig/"
            "com_android_systemui_flags_lib/android_common/javac/"
            "com_android_systemui_flags_lib.jar"
        ),
        Path("libs/systemui-flags.jar"),
        "com.android.systemui",
    ),
    "notification-flags": (
        _soong(
            "frameworks/base/services/core/java/com/android/server/"
            "notification/notification_flags_lib/android_common/javac/"
            "notification_flags_lib.jar"
        ),
        Path("libs/notification-flags.jar"),
        "com.android.server.notification",
    ),
    "launcher3-flags": (
        _soong(
            "packages/apps/Launcher3/aconfig/"
            "com_android_launcher3_flags_lib/android_common/javac/"
            "com_android_launcher3_flags_lib.jar"
        ),
        Path("libs/launcher3-flags.jar"),
        "com.android.launcher3",
    ),
    "settingslib-widget-flags": (
        _soong(
            "frameworks/base/packages/SettingsLib/IllustrationPreference/"
            "settingslib_illustrationpreference_flags_lib/"
            "android_common/javac/"
            "settingslib_illustrationpreference_flags_lib.jar"
        ),
        Path("libs/settingslib-widget-flags.jar"),
        "com.android.settingslib.widget.flags",
    ),
    "settingslib-selector-flags": (
        _soong(
            "frameworks/base/packages/SettingsLib/"
            "SelectorWithWidgetPreference/"
            "settingslib_selectorwithwidgetpreference_flags_lib/"
            "android_common/javac/"
            "settingslib_selectorwithwidgetpreference_flags_lib.jar"
        ),
        Path("libs/settingslib-selector-flags.jar"),
        "com.android.settingslib.widget.selectorwithwidgetpreference.flags",
    ),
}


def validate_runtime_jar(source: Path, runtime_package: str) -> None:
    """Require exactly the five runtime classes under runtime_package."""
    prefix = runtime_package.replace(".", "/") + "/"
    expected = {f"{prefix}{name}.class" for name in RUNTIME_CLASS_NAMES}
    with zipfile.ZipFile(source) as archive:
        actual = {
            entry
            for entry in archive.namelist()
            if entry.endswith(".class")
        }
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise ValueError(
            f"unexpected runtime class set in {source} for package "
            f"{runtime_package}: missing={missing} extra={extra}"
        )


def copy_jar(source: Path, destination: Path, runtime_package: str) -> None:
    source = Path(source)
    destination = Path(destination)
    if "turbine" in source.parts:
        raise ValueError(f"runtime JAR must not come from turbine: {source}")
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise FileNotFoundError(f"missing or invalid AOSP JAR: {source}")
    validate_runtime_jar(source, runtime_package)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    shutil.copyfile(source, temporary)
    temporary.replace(destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package concrete AOSP aconfig JARs")
    parser.add_argument(
        "artifact",
        nargs="?",
        choices=sorted(CONFIGS),
        help="single artifact to package (backward-compatible positional)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="package every configured artifact in sorted order",
    )
    args = parser.parse_args()
    if args.all and args.artifact:
        parser.error("pass either a single artifact or --all, not both")
    if not args.all and not args.artifact:
        parser.error("pass a single artifact or --all")
    names = sorted(CONFIGS) if args.all else [args.artifact]
    for name in names:
        source, destination, runtime_package = CONFIGS[name]
        copy_jar(source, destination, runtime_package)
        print(f"{name}: {source} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
