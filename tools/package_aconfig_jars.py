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

AOSP_INTERMEDIATES = Path(
    "/home/conv/myspace/aosp/out/soong/.intermediates"
)

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
    parser.add_argument("artifact", choices=sorted(CONFIGS))
    args = parser.parse_args()
    source, destination, runtime_package = CONFIGS[args.artifact]
    copy_jar(source, destination, runtime_package)
    print(f"{args.artifact}: {source} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
