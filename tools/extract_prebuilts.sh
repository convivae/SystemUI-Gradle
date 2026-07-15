#!/usr/bin/env bash
# Extract AOSP-compiled SystemUI prebuilt JARs into libs/prebuilts/.
# Idempotent: re-running overwrites with same content.
set -euo pipefail

AOSP_OUT="${AOSP_OUT:-/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/libs/prebuilts"
mkdir -p "$DEST"

# SYSOPS: AOSP produces *Lib.jar names, not SystemUI-{name}.jar.
# See docs/GRADLE_MIGRATION_LOG.md 问题五.
copy_jar() {
    local out_name="$1"   # e.g. SystemUISharedLib
    local dest_name="${2:-${out_name}.jar}"  # optional dest name
    local src
    src=$(find "$AOSP_OUT" -name "${out_name}.jar" -path "*/turbine-combined/*" 2>/dev/null | head -1)
    if [[ -z "$src" ]]; then
        echo "ERROR: ${out_name}.jar not found under $AOSP_OUT" >&2
        return 1
    fi
    cp -f "$src" "$DEST/${dest_name}"
    echo "copied: $src -> $DEST/${dest_name}"
}

copy_jar SystemUISharedLib
copy_jar PlatformAnimationLib
copy_jar SystemUICustomizationLib
copy_jar SystemUIPluginLib

echo "All JARs extracted to $DEST:"
ls -lh "$DEST"
