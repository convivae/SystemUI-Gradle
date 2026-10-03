# SysUISdk Single-Entry AOSP Composition

**Date:** 2026-08-21  
**Status:** Implemented (Task 045); layout amended 2026-10-03 under ADR 0006: source-identical libcore/DDMS classes use an SDK optional library to preserve IDE sync and local JVM tests. Current verification evidence is in `docs/issues/2026-10-03-sdk-optional-bridge-implementation.md`; historical Task 045 evidence remains in `docs/issues/2026-08-21-sysuisdk-single-entry-composition.md`.

## 1. Goal

Replace the historical staged/live-patching pipeline with one cross-platform command:

```bash
python3 tools/build_sysuisdk.py --aosp-root /path/to/aosp
```

The command composes a new, independent `android-SysUISdk` from a read-only official
Android SDK platform plus already-built AOSP `out/` artifacts. It does not invoke
Soong, patch an installed platform in place, create permanent backups, or depend on
repository payload copies of framework classes/resources.

The product criterion is AGP-native functional parity: the generated SDK must support
the existing Debug and optimized Release builds. Byte identity with the legacy live
SysUISdk is not required.

## 2. Frozen artifact map

Every AOSP path is relative to the explicit `--aosp-root`. Missing files are fatal;
there is no glob-based or newest-file fallback.

| Family | Exact AOSP-relative path | Consumer | Composition rule |
|---|---|---|---|
| framework aggregate headers | `out/soong/.intermediates/frameworks/base/framework/android_common/turbine-combined/framework.jar` | generated `android.jar` | framework class bytes win over stock SDK duplicates; this Soong aggregate includes `framework-minus-apex` plus `framework-updatable-stubs-module_libs_api` through `framework` static libs |
| framework private resources | `out/soong/.intermediates/frameworks/base/core/res/framework-res/android_common/framework-res.apk` | generated `android.jar` | replace all `resources.arsc` and `res/**` entries with byte-exact APK entries; do not copy manifest/assets/signing metadata |
| libcore/platform bridge source | `out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar` | 4 dalvik entries in android.jar; 10 libcore/DDMS entries in optional bridge; all 14 in core-for-system-modules.jar | exact allowlist, no class byte rewriting |
| ~~unsupported-app-usage source~~ (removed, D12 2026-08-29) | ~~`out/soong/.intermediates/tools/platform-compat/java/android/compat/annotation/unsupportedappusage/linux_glibc_common/javac/unsupportedappusage.jar`~~ | — | removed with its 2-entry bridge slice; the 17 framework aggregate turbine JAR embeds `UnsupportedAppUsage{,$Container}` and the framework copy is master (see `docs/architecture/2026-08-29-decision-audit/d12-sysuisdk-bridge-collision.md`) |
| aconfig annotation source | `out/soong/.intermediates/frameworks/libs/modules-utils/java/aconfig-annotations-lib/linux_glibc_common/javac/aconfig-annotations-lib.jar` | both generated JARs | exact `AconfigFlagAccessor` only; `AssumeTrueForR8` remains excluded |
| keepanno source | `out/soong/.intermediates/prebuilts/r8/keepanno-annotations/android_common/combined/keepanno-annotations.jar` | both generated JARs | exact frozen Task 041 22-entry allowlist |
| hidden interface declaration source | `frameworks/base/core/java/android/os/IRemoteCallback.aidl` | generated `framework.aidl` | derive and append the fully-qualified interface declaration only if absent |
| hidden parcelable declaration source | `frameworks/base/core/java/com/android/internal/util/ScreenshotRequest.aidl` | generated `framework.aidl` | derive and append the fully-qualified parcelable declaration only if absent |

The official base platform provides the platform layout, public SDK/module API surface,
`core-for-system-modules.jar`, `framework.aidl`, metadata, `data/`, and `optional/`.
Discovery order for the SDK root is fixed:

1. `--sdk-root`
2. `ANDROID_SDK_ROOT`
3. `ANDROID_HOME`
4. Linux `~/Android/Sdk`
5. macOS `~/Library/Android/sdk`
6. Windows `%LOCALAPPDATA%\Android\Sdk`

The base platform defaults to `android-37.0`. The default output is
`<sdk-root>/platforms/android-SysUISdk`.

## 3. Composition semantics

### 3.1 `android.jar`

1. Read the stock base `android.jar`.
2. Overlay every non-directory entry from the frozen framework aggregate; a duplicate
   framework entry intentionally wins because hidden/platform signatures must not be
   shadowed by the public SDK definition.
3. Replace the complete framework resource set with the frozen `framework-res.apk`
   resource entries.
4. Apply collision checks for all frozen 37 bridge entries (D12 excluded the two
   framework-owned UnsupportedAppUsage classes). Retain the 27 dalvik/aconfig/keepanno
   entries; the 10 libcore/DDMS entries are delivered unchanged in the optional JAR.
5. Equal source bytes are idempotent; unequal bytes are fatal **before** relocation,
   so moving classes cannot hide a stock/framework/source collision.
6. Reject duplicate names within any input ZIP and write deterministic entry ordering,
   timestamps, attributes, and compression using Python standard library only.

### 3.2 `core-for-system-modules.jar`

Start from the stock base JAR and inject the same frozen 37 bridge entries under the
same collision rule. (The framework-borne UnsupportedAppUsage pair is NOT injected
here; it lives only in `android.jar` via the framework aggregate.) This remains a library-class/system-module bridge, not an APK
program dependency.

### 3.3 `framework.aidl`

Start from the stock base file. Parse the package and top-level declaration from each
frozen AOSP primary source, verify the expected kind/name, and append the derived fully
qualified declaration only when absent. Do not copy framework AIDL implementation
sources into a SystemUI module and do not hard-code a declaration without checking its
primary source.

### 3.4 SDK optional bridge (2026-10-03)

`optional/sysui-platform-bridge.jar` contains exactly the 10 existing libcore/DDMS
allowlisted entries. No class body, flag, annotation or constant is changed.
`optional/optional.json` preserves stock library records and adds
`com.android.systemui.platform.bridge` with `manifest=false`; a conflicting stock
name/JAR path or malformed metadata fails the transaction.

Android modules consume it through public `android.useLibrary(...)`. The current
AGP includes it in compiler, R8 library and JVM-test classpaths, but transforms only
`android.jar` into a mockable JAR. This avoids AGP's dangling exception-handler bug
without disabling tests or introducing custom stubs. It does not emulate ART/native
APIs on the host JVM. All 37 entries still remain in the system-module JAR; the
android.jar/optional bridge partition is disjoint and complete.

## 4. Transaction and ownership model

- Build into a sibling temporary directory and publish by rename only after all
  validation passes.
- On failure, remove only the temporary staging directory.
- Never modify `android-37.0` or any other official platform.
- Refuse an existing output by default.
- `--replace` is permitted only when the existing output contains the generator marker
  created by this script; it must never replace the official base platform.
- The marker records schema version, normalized input identities, SHA-256 values,
  generated inventories, and tool version. It is ownership evidence, not a backup.
- Do not create `.orig`, `.bak-*`, or an `--apply`/restore interface.

## 5. Built-in verification

A successful command must validate before publication:

- all exact inputs exist under their declared roots;
- ZIPs contain unique names and all frozen allowlist entries;
- the generated jars are readable: android.jar has 27 bridge entries, the optional
  JAR exactly the other 10, and the system-module JAR all 37; every bridge byte equals
  its AOSP source, the partition is disjoint, optional metadata matches composition;
- `android.jar` resource names and bytes equal the AOSP `framework-res.apk` resource
  subset;
- the two hidden AIDL declarations are present and source-derived;
- metadata points to `platforms;android-SysUISdk`, API 37, codename `SysUISdk`;
- no backup files exist in the generated platform;
- a repeated build from identical inputs is byte-deterministic.

The external acceptance gate additionally compiles existing Debug and optimized
Release variants against a private SDK root containing this generated platform,
checks APK ZIP integrity and V2 signing, and proves all 37 bridge classes are absent
from packaged DEX. The 2026-10-03 amendment additionally requires real AndroidProject
Tooling models, executable JVM tests (fixture under `tools/tests/fixtures/sysuisdk_optional_bridge`),
and no invented device `uses-library` dependency in the final manifest.

## 6. Deliberately retained and retired artifacts

`libs/keepanno-annotations.jar` remains because `:SystemUI-core` independently uses it
as a compile-only dependency. It is not a SysUISdk composition input.

After the new generator and Gradle acceptance pass, Task 045 may delete these proven
superseded repository inputs/helpers and their dedicated tests
(**deleted 2026-08-21 after all gates passed**, commit `76ad180f`):

- `libs/android-merged.jar`
- `libs/framework-res.apk`
- `tools/install_sdk.py`
- `tools/patch_sdk_dalvik_annotations.py`
- `tools/patch_sdk_r8_library_classes.py`
- `tools/tests/test_patch_sdk_dalvik_annotations.py`
- `tools/tests/test_patch_sdk_r8_library_classes.py`

The nine historical files inside the external legacy live SysUISdk are explicitly out
of scope and require separate irreversible-deletion approval.

## 7. Red-line behavior

If this frozen map cannot compile the project, the Worker must stop and report the
exact unresolved platform FQNs plus candidate AOSP provenance. It must not silently add
another artifact family, use a repository payload fallback, widen the bridge allowlist,
modify SystemUI source/resources, or change Gradle dependencies/build checks.
