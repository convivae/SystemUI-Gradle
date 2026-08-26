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

# Destination of the deterministic union merge of the framework exportable-aconfig
# hidden-twin family (user decision 2026-08-25, option M, task 057).
MERGED_FRAMEWORK_JAR = Path("libs/systemui-aconfig-flags.jar")

# The Soong javac outputs already use this fixed timestamp; keep it for the merge.
_MERGE_FIXED_DATETIME = (2008, 1, 1, 0, 0, 0)

#: Config names that make up the framework exportable-aconfig hidden-twin family
#: (tasks 053/054/055). Their Soong javac sources merge deterministically into
#: MERGED_FRAMEWORK_JAR; the per-jar five-class validator still runs per source.
FRAMEWORK_FAMILY = frozenset(
    (
        # tasks 053/054
        "window-flags",
        "device-state-feature-flags",
        "android-os-flags",
        # task 055 batch
        "smartspace-flags",
        "content-pm-flags",
        "biometrics-flags",
        "usb-flags",
        "net-platform-flags",
        "permission-flags",
        "provider-flags",
        "security-flags",
        "service-controls-flags",
        "service-notification-flags",
        "quickaccesswallet-flags",
    )
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


#: SettingsLib aconfig runtime whose owning Soong module has no javac output
#: in the build (only turbine artifacts exist; task 064). The kept libs/
#: baseline jar was hand-built on 2026-07-29 from the same turbine-combined
#: classes with a JDK jar-tool wrapper; it is compileOnly wiring, so turbine
#: stub bodies are acceptable. ``repack_baseline_stub_jar`` reproduces the
#: baseline bytes exactly from the turbine source.
TURBINE_BASELINE_CONFIGS = {
    "settingslib-flags": (
        _soong(
            "frameworks/base/aconfig_settingslib_flags_java_lib/"
            "android_common/turbine-combined/"
            "aconfig_settingslib_flags_java_lib.jar"
        ),
        Path("libs/settingslib-flags.jar"),
        "com.android.settingslib.flags",
    ),
}

#: Manifest bytes of the 2026-07-29 hand-built baseline jar (JDK 25 jar tool).
_BASELINE_MANIFEST = b"Manifest-Version: 1.0\r\nCreated-By: 25.0.2 (Oracle Corporation)\r\n\r\n"

#: Entry timestamp the jar tool stamped on the manifest and directory
#: entries of the baseline jar.
_BASELINE_WRAPPER_DATETIME = (2026, 7, 29, 1, 37, 0)

#: Name -> (owning Soong javac source, destination, runtime package)
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
    # Task 064 (regeneration gap closure): the two remaining javac-backed
    # aconfig runtime jars that were hand-copied in 2026-07.
    "settingslib-media-flags": (
        _soong(
            "frameworks/base/packages/SettingsLib/settingslib_media_flags_lib/"
            "android_common/javac/settingslib_media_flags_lib.jar"
        ),
        Path("libs/settingslib-media-flags.jar"),
        "com.android.settingslib.media.flags",
    ),
    "device-state-flags": (
        _soong(
            "frameworks/base/services/foldables/devicestateprovider/src/com/"
            "android/server/policy/feature/device_state_flags_lib/"
            "android_common/javac/device_state_flags_lib.jar"
        ),
        Path("libs/device-state-flags.jar"),
        "com.android.server.policy.feature.flags",
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


def _dos_datetime(when: tuple[int, int, int, int, int, int]) -> tuple[int, int]:
    """DOS zip (time, date) pair for a ``(y, m, d, h, mi, s)`` tuple."""
    year, month, day, hour, minute, second = when
    dos_time = (second // 2) | (minute << 5) | (hour << 11)
    dos_date = ((year - 1980) << 9) | (month << 5) | day
    return dos_time, dos_date


def _jar_tool_zip_bytes(entries: list[tuple[str, tuple[int, int, int, int, int, int], int, bytes]]) -> bytes:
    """Serialize ``entries`` in the exact byte format of a JDK ``jar`` tool run.

    ``entries`` is a list of ``(name, date_time, method, payload)``. The layout
    replicates what ``java.util.zip.ZipOutputStream`` (as driven by the jar
    tool) produces, verified byte-for-byte against the 2026-07-29 baseline
    ``libs/settingslib-flags.jar`` (task 064):

    * local file headers carry the UTF-8 flag (0x800); deflated entries add
      the data-descriptor flag (0x808) and write crc/sizes only in a
      signature-prefixed trailing data descriptor;
    * the first local header (and only it) carries the 4-byte 0xCAFE dummy
      extra field the JDK reserves for zip64 promotion;
    * the central directory uses DOS (FAT) as the host system and zero
      external attributes;
    * deflated streams are zlib level 6, matching the JDK default.
    """
    import struct
    import zlib

    body = bytearray()
    central = bytearray()
    offset = 0
    for index, (name, when, method, payload) in enumerate(entries):
        dos_time, dos_date = _dos_datetime(when)
        if method == zipfile.ZIP_DEFLATED:
            compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
            compressed = compressor.compress(payload) + compressor.flush()
        else:
            compressed = payload
        crc = zlib.crc32(payload) & 0xFFFFFFFF
        version = 20 if method == zipfile.ZIP_DEFLATED else 10
        flags = 0x808 if method == zipfile.ZIP_DEFLATED else 0x800
        name_bytes = name.encode("utf-8")
        extra = b"\xfe\xca\x00\x00" if index == 0 else b""
        if method == zipfile.ZIP_DEFLATED:
            body += struct.pack(
                "<IHHHHHIIIHH", 0x04034B50, version, flags, method,
                dos_time, dos_date, 0, 0, 0, len(name_bytes), len(extra),
            )
            body += name_bytes + extra + compressed
            body += struct.pack(
                "<IIII", 0x08074B50, crc, len(compressed), len(payload)
            )
        else:
            body += struct.pack(
                "<IHHHHHIIIHH", 0x04034B50, version, flags, method,
                dos_time, dos_date, crc, len(compressed), len(payload),
                len(name_bytes), len(extra),
            )
            body += name_bytes + extra + compressed
        central += struct.pack(
            "<IHHHHHHIIIHHHHHII", 0x02014B50, version, version, flags, method,
            dos_time, dos_date, crc, len(compressed), len(payload),
            len(name_bytes), len(extra), 0, 0, 0, 0, offset,
        )
        central += name_bytes + extra
        offset = len(body)
    body += central
    body += struct.pack(
        "<IHHHHIIH", 0x06054B50, 0, 0, len(entries), len(entries),
        len(central), offset, 0,
    )
    return bytes(body)


def repack_baseline_stub_jar(source: Path, destination: Path, runtime_package: str) -> None:
    """Rebuild a hand-made baseline stub JAR from a Soong turbine source.

    Used only for aconfig runtime modules whose javac output does not exist in
    the build (``aconfig_settingslib_flags_java_lib`` is consumed purely via
    turbine by the framework). The kept baseline jar wraps the identical
    turbine classes in a JDK jar-tool zip; this function reproduces those
    bytes deterministically so the baseline stays regenerable. The five-class
    runtime validation still applies; the module-level turbine guard is
    deliberately overridden here because the baseline itself carries turbine
    stub bodies and the jar is compileOnly wiring.
    """
    source = Path(source)
    destination = Path(destination)
    if not source.is_file() or not zipfile.is_zipfile(source):
        raise FileNotFoundError(f"missing or invalid AOSP JAR: {source}")
    validate_runtime_jar(source, runtime_package)
    with zipfile.ZipFile(source) as archive:
        classes = [
            (info.filename, info.date_time, zipfile.ZIP_DEFLATED,
             archive.read(info.filename))
            for info in archive.infolist()
            if not info.is_dir()
        ]
    if any(name == "META-INF/MANIFEST.MF" for name, _, _, _ in classes):
        raise ValueError(f"turbine source unexpectedly carries a manifest: {source}")
    prefix = runtime_package.replace(".", "/") + "/"
    directories = []
    seen: set[str] = set()
    for name, _, _, _ in classes:
        parts = name.split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            directory = "/".join(parts[:depth]) + "/"
            if directory not in seen:
                seen.add(directory)
                directories.append(directory)
    entries = [("META-INF/", _BASELINE_WRAPPER_DATETIME, zipfile.ZIP_STORED, b"")]
    entries.append(
        ("META-INF/MANIFEST.MF", _BASELINE_WRAPPER_DATETIME,
         zipfile.ZIP_DEFLATED, _BASELINE_MANIFEST)
    )
    entries += [
        (directory, _BASELINE_WRAPPER_DATETIME, zipfile.ZIP_STORED, b"")
        for directory in directories
    ]
    entries += classes
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    temporary.write_bytes(_jar_tool_zip_bytes(entries))
    temporary.replace(destination)


def merge_sources(items: list[tuple[str, Path, str]], destination: Path) -> None:
    """Deterministically merge aconfig runtime JARs into one union JAR.

    ``items`` is a list of ``(name, source, runtime_package)`` triples. Each source
    is validated with the five-class runtime rule, then merged under these rules:

    * ``.class`` / ``.uau`` (any payload) pathnames must be unique across sources;
      ANY overlap fails loudly, even if the bytes would be identical, because a
      duplicated class path means a wrong owning module.
    * ``META-INF/MANIFEST.MF`` is structural: it is carried once and must be
      byte-identical across sources (diverging manifests fail loudly).
    * Directory entries are unioned (no semantic payload).
    * Output entries (dirs and files) are written in lexicographic order with a
      fixed timestamp, fixed compression level and explicit attributes, so two
      runs over the same inputs produce identical bytes.
    """
    destination = Path(destination)
    payload: dict[str, bytes] = {}
    directories: set[str] = set()
    manifest: bytes | None = None
    for name, source, runtime_package in items:
        source = Path(source)
        if "turbine" in source.parts:
            raise ValueError(f"runtime JAR must not come from turbine: {source}")
        if not source.is_file() or not zipfile.is_zipfile(source):
            raise FileNotFoundError(f"missing or invalid AOSP JAR: {source}")
        validate_runtime_jar(source, runtime_package)
        with zipfile.ZipFile(source) as archive:
            for info in archive.infolist():
                if info.is_dir():
                    directories.add(info.filename)
                    continue
                data = archive.read(info.filename)
                if info.filename == "META-INF/MANIFEST.MF":
                    if manifest is None:
                        manifest = data
                    elif manifest != data:
                        raise ValueError(
                            f"diverging META-INF/MANIFEST.MF while merging {name}"
                        )
                    continue
                if info.filename in payload:
                    raise ValueError(
                        f"colliding entry {info.filename} across merge sources "
                        f"(second sighting from {name})"
                    )
                payload[info.filename] = data
    if manifest is None:
        manifest = b"Manifest-Version: 1.0\r\n\r\n"
    payload["META-INF/MANIFEST.MF"] = manifest
    directories.add("META-INF/")

    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with zipfile.ZipFile(
        temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for entry in sorted(directories | set(payload)):
            info = zipfile.ZipInfo(entry, _MERGE_FIXED_DATETIME)
            if entry.endswith("/"):
                info.external_attr = (0o755 << 16) | 0x10
                archive.writestr(info, b"")
            else:
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o644 << 16
                archive.writestr(info, payload[entry])
    temporary.replace(destination)


def merge_framework_family(destination: Path = MERGED_FRAMEWORK_JAR) -> None:
    """Merge the 14 framework-family Soong javac sources into one JAR."""
    items = [
        (name, CONFIGS[name][0], CONFIGS[name][2])
        for name in sorted(FRAMEWORK_FAMILY)
    ]
    merge_sources(items, destination)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package concrete AOSP aconfig JARs")
    parser.add_argument(
        "artifact",
        nargs="?",
        choices=sorted(set(CONFIGS) | set(TURBINE_BASELINE_CONFIGS)),
        help="single artifact to package (backward-compatible positional)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="package every configured artifact: one merged framework-family jar "
        "plus each non-family jar, in sorted order",
    )
    parser.add_argument(
        "--merge-framework",
        action="store_true",
        help="deterministically merge the framework-family sources into "
        f"{MERGED_FRAMEWORK_JAR}",
    )
    args = parser.parse_args()
    selected = int(bool(args.all)) + int(bool(args.merge_framework)) + int(
        bool(args.artifact)
    )
    if selected != 1:
        parser.error("pass exactly one of: a single artifact, --all, --merge-framework")
    if args.merge_framework or args.all:
        merge_framework_family()
        print(f"framework-family merge: {len(FRAMEWORK_FAMILY)} sources -> "
              f"{MERGED_FRAMEWORK_JAR}")
    names = (
        sorted(
            name
            for name in set(CONFIGS) | set(TURBINE_BASELINE_CONFIGS)
            if name not in FRAMEWORK_FAMILY
        )
        if args.all
        else ([args.artifact] if args.artifact else [])
    )
    for name in names:
        if name in TURBINE_BASELINE_CONFIGS:
            source, destination, runtime_package = TURBINE_BASELINE_CONFIGS[name]
            repack_baseline_stub_jar(source, destination, runtime_package)
        else:
            source, destination, runtime_package = CONFIGS[name]
            copy_jar(source, destination, runtime_package)
        print(f"{name}: {source} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
