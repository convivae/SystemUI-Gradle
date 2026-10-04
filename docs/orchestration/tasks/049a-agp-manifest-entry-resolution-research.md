# Task 049A: AGP manifest entry resolution research

> Read-only/static parallel investigation for Task 049. Worker commits documentation only and never pushes.

## Authority

`self-commit` within the single documentation output below. This task must not run Gradle,
start an emulator, use ADB, or edit product/build files. It runs independently while the
Task 049 runtime Worker owns all build and device state.

## Required startup

Invoke worker-contract, then read in order:

1. `AGENTS.md`
2. `docs/orchestration/CHARTER.md`
3. this brief
4. `docs/issues/2026-08-22-debug-apk-runtime-stabilization.md`
5. `app/build.gradle.kts`
6. `app/src/main/AndroidManifest.xml`
7. `SystemUI-core/build.gradle.kts`

Invoke the `research` skill and use primary sources where available.

## Goal

Determine the narrowest maintainable AGP-native way to make manifest Application and
component names resolve to the real `com.android.systemui.*` classes while preserving the
current app package and module/resource boundaries.

## Facts to verify, not assume

- `:app` namespace is `com.android.systemui.app` while applicationId/package is
  `com.android.systemui`.
- the AOSP manifest contains 74 leading-dot component names plus two unqualified service
  names and no source `package` attribute.
- the packaged Debug manifest currently contains 76 `com.android.systemui.app.*` entries,
  while those classes exist under `com.android.systemui.*`.
- `PhoneSystemUIAppComponentFactory` behaves differently because its packaged value may
  remain relative and be resolved against the package at runtime.

## Options to compare

1. Set `:app` namespace to `com.android.systemui`.
2. Keep the distinct namespace but use supported manifest merger/placeholder/applicationId
   mechanisms to resolve relative class names against `com.android.systemui`.
3. Use an AGP artifacts API or generated/intermediate manifest transform.
4. Any other official AGP-supported mechanism discovered.

For each option, identify correctness, maintainability, impact on R/R-class ownership,
compatibility with the AOSP-verbatim manifest constraint, and whether it is supported
public API or brittle task/intermediate coupling. Check the reference CarSystemUIGradle
project and AOSP/AGP primary sources where useful.

## Allowed path

- `docs/architecture/2026-08-22-agp-manifest-entry-resolution.md`

## Forbidden

- all other repository files
- Gradle commands of any kind
- ADB/emulator/AVD operations
- product changes, manifests, source/res, tools, dependencies, rules

## Acceptance

- Evidence-backed recommendation with ranked options and precise file/line references.
- Explicitly state whether `namespace == applicationId` is safe in this multi-module graph,
  and whether a public AGP API exists for manifest rewriting before packaging.
- `git diff --check` and exact one-file scope.
- English commit, no push, terminal `HANDOFF:`.
