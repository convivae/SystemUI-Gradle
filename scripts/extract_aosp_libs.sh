#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Read paths from local.properties
if [[ ! -f "$PROJECT_DIR/local.properties" ]]; then
    echo "ERROR: local.properties not found. Copy local.properties.template and fill in your paths."
    exit 1
fi

AOSP_DIR=$(grep "^aosp.dir=" "$PROJECT_DIR/local.properties" | cut -d= -f2-)
AOSP_OUT_DIR=$(grep "^aosp.out.dir=" "$PROJECT_DIR/local.properties" | cut -d= -f2-)

if [[ -z "$AOSP_DIR" || -z "$AOSP_OUT_DIR" ]]; then
    echo "ERROR: aosp.dir and aosp.out.dir must be set in local.properties"
    exit 1
fi

LIBS_DIR="$PROJECT_DIR/libs"
mkdir -p "$LIBS_DIR"

echo "AOSP source: $AOSP_DIR"
echo "AOSP output: $AOSP_OUT_DIR"
echo "Target dir:  $LIBS_DIR"
echo ""

# Framework JARs (compileOnly — not bundled in APK)
FRAMEWORK_JARS=(
    "system/framework/framework.jar"
    "system/framework/services.jar"
)

# Prebuilt libraries from soong intermediates
find_sojar() {
    local name="$1"
    local soong_dir="$AOSP_OUT_DIR/soong/.intermediates"

    # Try common paths
    local candidates=(
        "$soong_dir/frameworks/base/packages/SystemUI/$name/android_common/combined/$name.jar"
        "$soong_dir/frameworks/base/packages/SystemUI/$name/android_common/turbine-combined/$name.jar"
        "$soong_dir/frameworks/libs/systemui/$name/android_common/combined/$name.jar"
        "$soong_dir/frameworks/libs/systemui/$name/android_common/turbine-combined/$name.jar"
        "$soong_dir/frameworks/base/libs/WindowManager/Shell/$name/android_common/combined/$name.jar"
        "$soong_dir/frameworks/base/libs/WindowManager/Shell/$name/android_common/turbine-combined/$name.jar"
        "$soong_dir/frameworks/base/packages/SettingsLib/$name/android_common/combined/$name.jar"
        "$soong_dir/frameworks/base/packages/SettingsLib/$name/android_common/turbine-combined/$name.jar"
    )

    for candidate in "${candidates[@]}"; do
        if [[ -f "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done

    # Broader search
    local found
    found=$(find "$soong_dir" -name "$name.jar" -path "*/combined/*" 2>/dev/null | head -1)
    if [[ -n "$found" ]]; then
        echo "$found"
        return 0
    fi

    return 1
}

find_aar() {
    local name="$1"
    local soong_dir="$AOSP_OUT_DIR/soong/.intermediates"

    local found
    found=$(find "$soong_dir" -name "$name.aar" 2>/dev/null | head -1)
    if [[ -n "$found" ]]; then
        echo "$found"
        return 0
    fi
    return 1
}

copy_lib() {
    local name="$1"
    local type="${2:-jar}"  # jar or aar

    local dest_name="$name.$type"
    if [[ -f "$LIBS_DIR/$dest_name" ]]; then
        echo "  SKIP $dest_name (already exists)"
        return 0
    fi

    local source=""
    if [[ "$type" == "aar" ]]; then
        source=$(find_aar "$name") || true
    else
        source=$(find_sojar "$name") || true
    fi

    if [[ -z "$source" ]]; then
        echo "  WARN: $name.$type not found in AOSP output"
        return 1
    fi

    cp "$source" "$LIBS_DIR/$dest_name"
    echo "  OK   $dest_name <- $source"
}

echo "=== Framework JARs (compileOnly) ==="
for jar in "${FRAMEWORK_JARS[@]}"; do
    src="$AOSP_OUT_DIR/$jar"
    dest="$LIBS_DIR/$(basename "$jar")"
    if [[ -f "$src" ]]; then
        cp "$src" "$dest"
        echo "  OK   $(basename "$jar") <- $src"
    else
        echo "  WARN: $jar not found"
    fi
done

echo ""
echo "=== AOSP Library JARs ==="
LIBS_JAR=(
    "SystemUI-core"
    "SystemUISharedLib"
    "SystemUIPluginLib"
    "PluginCoreLib"
    "PluginAnnotationLib"
    "SystemUIUnfoldLib"
    "SystemUICustomizationLib"
    "PlatformAnimationLib"
    "SystemUIShaderLib"
    "SystemUICommon"
    "SystemUI-shared-utils"
    "SystemUILogLib"
    "SystemUI-tags"
    "SystemUI-proto"
    "SystemUI-statsd"
    "SystemUI-res"
    "WifiTrackerLib"
    "SettingsLib"
    "WindowManager-Shell"
    "WindowManager-Shell-shared"
    "WindowManager-Shell-proto"
    "compilelib"
    "animationlib"
    "iconloader_base"
    "tracinglib-platform"
    "contextualeducationlib"
    "motion_tool_lib"
    "msdl"
    "view_capture"
    "monet"
    "libmonet"
    "com_android_systemui_shared_flags_lib"
    "com_android_systemui_flags_lib"
    "notification_flags_lib"
    "device_state_flags_lib"
    "LowLightDreamLib"
    "TraceurCommon"
    "Traceur-res"
    "PlatformComposeCore"
    "PlatformComposeSceneTransitionLayout"
)

for lib in "${LIBS_JAR[@]}"; do
    copy_lib "$lib" "jar"
done

echo ""
echo "=== AOSP Library AARs ==="
LIBS_AAR=(
    "PlatformComposeCore"
    "PlatformComposeSceneTransitionLayout"
)

for lib in "${LIBS_AAR[@]}"; do
    copy_lib "$lib" "aar"
done

echo ""
echo "=== Pods Libraries ==="
PODS=(
    "api"
    "impl"
)

# Search in pods subdirectories
for pod in "${PODS[@]}"; do
    found=$(find "$AOSP_OUT_DIR/soong/.intermediates/frameworks/base/packages/SystemUI/pods" -name "$pod.jar" -path "*/combined/*" 2>/dev/null | head -1)
    if [[ -n "$found" ]]; then
        cp "$found" "$LIBS_DIR/pods-$pod.jar"
        echo "  OK   pods-$pod.jar <- $found"
    else
        echo "  WARN: pods/$pod.jar not found"
    fi
done

echo ""
echo "Done. Libraries extracted to $LIBS_DIR"
echo ""
echo "NOTE: Some libraries may be AARs instead of JARs. If a JAR is missing,"
echo "      check for an AAR version in the soong intermediates."
