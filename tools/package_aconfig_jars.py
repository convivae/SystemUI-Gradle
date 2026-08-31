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
#:
#: AOSP-17 (Task 071): the family shrank 14 -> 12. Upstream renamed the
#: android.security.flags / android.service.quickaccesswallet.flags packages
#: (flags now live directly under android.security / android.service.
#: quickaccesswallet), so the old runtime packages no longer exist anywhere
#: in the 17 tree and SystemUI-17 has zero imports of them — both members
#: were dropped (precedent: motiontoollib removal).
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
        "service-controls-flags",
        "service-notification-flags",
    )
)

#: AOSP-17 (Task 071): six family members whose standalone
#: ``android_common/javac`` outputs no longer exist — Soong compiles their
#: public runtime classes directly into the framework-minus-apex aggregate,
#: whose javac action is sharded (``framework.jar0``..``framework.jarN``;
#: worker-shard indices are NOT stable across rebuilds, so the shard owning
#: a package is discovered by validated content scan, never pinned).
#: ``extract_aggregate_subset`` pulls the exact five-class subset (real
#: Soong bytes; nothing is synthesized) for the union merge.
AGGREGATE_JAVAC_DIR = AOSP_INTERMEDIATES / (
    "frameworks/base/framework-minus-apex/android_common/javac"
)
AGGREGATE_FAMILY = frozenset(
    (
        "smartspace-flags",
        "usb-flags",
        "net-platform-flags",
        "permission-flags",
        "service-controls-flags",
        "device-state-feature-flags",
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
    #
    # AOSP-17 (Task 071): the six AGGREGATE_FAMILY members below no longer
    # have standalone android_common/javac outputs (Soong compiles them into
    # the sharded framework-minus-apex javac aggregate); their "source" field
    # points at the shard directory and the real bytes are extracted via
    # extract_aggregate_subset(). Two further 16-era members were dropped
    # upstream (renamed packages, zero SystemUI-17 imports):
    # security-flags and quickaccesswallet-flags.
    "smartspace-flags": (
        AGGREGATE_JAVAC_DIR,
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
        AGGREGATE_JAVAC_DIR,
        Path("libs/usb-flags.jar"),
        "android.hardware.usb.flags",
    ),
    "net-platform-flags": (
        AGGREGATE_JAVAC_DIR,
        Path("libs/net-platform-flags.jar"),
        "android.net.platform.flags",
    ),
    "permission-flags": (
        AGGREGATE_JAVAC_DIR,
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
    # AOSP-17 (Task 071): security-flags entry removed upstream — the
    # .aconfig package was renamed from android.security.flags to
    # android.security; the old package exists nowhere in the 17 tree and
    # SystemUI-17 does not import it.
    "service-controls-flags": (
        AGGREGATE_JAVAC_DIR,
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
    # AOSP-17 (Task 071): quickaccesswallet-flags entry removed upstream —
    # the .aconfig package was renamed from
    # android.service.quickaccesswallet.flags to
    # android.service.quickaccesswallet; the old package exists nowhere in
    # the 17 tree and SystemUI-17 does not import it.
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
        AGGREGATE_JAVAC_DIR,
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
    # AOSP-17 (Task 071): settingslib-selector-flags entry removed upstream —
    # SettingsLib/SelectorWithWidgetPreference no longer declares an aconfig
    # flags lib (its Android.bp has no flags static_lib), and SystemUI-17 has
    # zero imports of the package. libs/settingslib-selector-flags.jar is no
    # longer produced; the gradle dependency line is retired in C4.
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
    # Task 072 (C4 wiring, 2026-08-28): uilatencystats flags. 17 SystemUI-core
    # bp static_libs includes uilatencystats_flags_core_java_lib
    # (frameworks/base/AconfigFlags.bp L218, aconfig_declarations
    # "uilatencystats_flags" in services/core uilatencystats/Android.bp).
    # SystemUI-17 keyguard sources import android.uilatencystats.
    # UiLatencyStatsManager (framework class); the runtime Flags classes live
    # under com.android.server.ui_latency_stats (five-class set verified).
    "uilatencystats-flags": (
        _soong(
            "frameworks/base/uilatencystats_flags_core_java_lib/"
            "android_common/javac/uilatencystats_flags_core_java_lib.jar"
        ),
        Path("libs/uilatencystats-flags.jar"),
        "com.android.server.ui_latency_stats",
    ),
    # Task 074 (C4c release/R8 closure, 2026-09-01): am-flags. 17
    # WindowManager-Shell-defaults static_libs L127 links am_flags_lib
    # (aconfig_declarations "am_flags",
    # services/core/java/com/android/server/am/Android.bp:15, package
    # com.android.server.am); WM-Shell AAR bytecode references
    # com.android.server.am.Flags (DesktopTaskChangeListener.addTask etc.),
    # so the five-class runtime set is dexed into the APK closure.
    "am-flags": (
        _soong(
            "frameworks/base/services/core/java/com/android/server/am/"
            "am_flags_lib/android_common/javac/am_flags_lib.jar"
        ),
        Path("libs/am-flags.jar"),
        "com.android.server.am",
    ),
    # Task 074 (C4c release/R8 closure, 2026-09-01): settingstheme-flags.
    # SettingsLibSettingsTheme bp static_libs
    # aconfig_settingstheme_exported_flags_java_lib (declaration
    # SettingsTheme/aconfig/settingstheme.aconfig, package
    # com.android.settingslib.widget.theme.flags, is_exported); the Theme
    # AAR's Kotlin classes (SettingsThemeHelper.isExpressiveDesignEnabled)
    # reference the Flags class at R8 time.
    "settingstheme-flags": (
        _soong(
            "frameworks/base/aconfig_settingstheme_exported_flags_java_lib/"
            "android_common/javac/"
            "aconfig_settingstheme_exported_flags_java_lib.jar"
        ),
        Path("libs/settingstheme-flags.jar"),
        "com.android.settingslib.widget.theme.flags",
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


def extract_aggregate_subset(runtime_package: str, destination: Path) -> Path:
    """Extract the validated five-class subset for a package from the shards.

    AOSP-17 (Task 071): six framework-family aconfig modules no longer
    produce standalone ``android_common/javac`` outputs — Soong compiles their
    public runtime classes directly into the framework-minus-apex aggregate,
    whose javac action is sharded (``framework.jar0``..``framework.jarN``).
    Shard indices are worker artifacts and NOT stable across rebuilds, so the
    shard owning ``runtime_package`` is discovered by content scan: entries
    under the package prefix must appear in exactly one shard and must form
    exactly the expected five-class runtime set (plus optional ``.uau`` and
    directory entries). Any ambiguity, missing class, or extra class fails
    loudly — nothing is synthesized, only real Soong bytes are carried over.

    Writes a deterministic interim JAR to ``destination`` (fixed timestamp,
    sorted entries) that satisfies ``validate_runtime_jar`` like any
    module-owning source.
    """
    import re

    prefix = runtime_package.replace(".", "/") + "/"
    expected = {f"{prefix}{name}.class" for name in RUNTIME_CLASS_NAMES}
    shards = sorted(
        (
            path
            for path in AGGREGATE_JAVAC_DIR.glob("framework.jar*")
            if re.fullmatch(r"framework\.jar\d+", path.name)
        ),
        key=lambda path: int(path.name[len("framework.jar") :]),
    )
    if not shards:
        raise FileNotFoundError(
            f"missing framework-minus-apex javac shards under {AGGREGATE_JAVAC_DIR}"
        )
    contributing: dict[str, dict[str, bytes]] = {}
    for shard in shards:
        with zipfile.ZipFile(shard) as archive:
            entries = {
                name: archive.read(name)
                for name in archive.namelist()
                if name.startswith(prefix)
            }
        if not entries:
            continue
        if len(contributing) > 0:
            raise ValueError(
                f"package {runtime_package} is split across aggregate shards "
                f"({sorted(contributing)} and {shard}); refusing ambiguous input"
            )
        contributing[shard.name] = entries
    if not contributing:
        raise FileNotFoundError(
            f"no framework-minus-apex javac shard contains package "
            f"{runtime_package}"
        )
    payload = next(iter(contributing.values()))
    classes = {name for name in payload if name.endswith(".class")}
    if classes != expected:
        raise ValueError(
            f"unexpected runtime class set in aggregate shard for package "
            f"{runtime_package}: missing={sorted(expected - classes)} "
            f"extra={sorted(classes - expected)}"
        )

    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(
        destination, "w", zipfile.ZIP_DEFLATED, compresslevel=9
    ) as archive:
        for name in sorted(payload):
            info = zipfile.ZipInfo(name, _MERGE_FIXED_DATETIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload[name])
    return destination


def merge_framework_family(destination: Path = MERGED_FRAMEWORK_JAR) -> None:
    """Merge the framework-family Soong javac sources into one JAR.

    AOSP-17 (Task 071): AGGREGATE_FAMILY members contribute via
    ``extract_aggregate_subset`` (validated five-class subsets of the
    framework-minus-apex javac shards); the remaining members keep their
    module-owning javac sources.
    """
    import tempfile

    items = []
    with tempfile.TemporaryDirectory() as tmp:
        for name in sorted(FRAMEWORK_FAMILY):
            source, _destination, runtime_package = CONFIGS[name]
            if name in AGGREGATE_FAMILY:
                source = extract_aggregate_subset(
                    runtime_package, Path(tmp) / f"{name}.jar"
                )
            items.append((name, source, runtime_package))
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
        elif name in AGGREGATE_FAMILY:
            # AOSP-17 (Task 071): aggregate members have no standalone javac
            # JAR; deliver the validated five-class subset extracted from the
            # framework-minus-apex javac shards.
            source, destination, runtime_package = CONFIGS[name]
            extract_aggregate_subset(runtime_package, destination)
        else:
            source, destination, runtime_package = CONFIGS[name]
            copy_jar(source, destination, runtime_package)
        print(f"{name}: {source} -> {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
