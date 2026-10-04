# README build quickstart clarification

Date: 2026-09-03

## Background

The README already contains a quick-start section, but its ordering is not directly executable: it asks readers to run `tools/build_sysuisdk.py` before cloning the repository that contains the script, does not explicitly bind the generator and Gradle to the same Android SDK root, and can leave new users with `Failed to find Platform SDK with path: platforms;android-SysUISdk`.

## Plan

1. Reorder the quick start so the repository is cloned before invoking repository tools.
2. Add a copyable shortest path for users who already have a built AOSP 17 tree.
3. Make `AOSP_ROOT` and `ANDROID_SDK_ROOT` explicit and ensure Gradle uses the same SDK root through `local.properties`.
4. Document first-time SysUISdk generation, `--replace`, Debug build, and clean Release build commands.
5. Keep the full AOSP checkout/build and deployment instructions as separate optional/one-time steps.
6. Keep Chinese and English READMEs aligned.

## Error-count evolution

- Not applicable: documentation-only change.

## Implementation

- Reworked the Chinese `README.md` quick start into five ordered stages: clone/path setup, AOSP preparation, SysUISdk generation, APK build, and deployment.
- Added explicit `AOSP_ROOT` / `ANDROID_SDK_ROOT` setup and a project-local `local.properties` so the generator and AGP resolve the same SDK.
- Added checks for the stock `android-37.0` base and generated `android-SysUISdk`, plus `--replace`, Debug, clean Release, and APK reference-verifier commands.
- Documented the exact meaning of `Failed to find Platform SDK with path: platforms;android-SysUISdk`.
- Applied the same workflow to `README.en.md` to keep both public READMEs aligned.

## Verification

- `git diff --check` passed.
- Both README files have balanced Markdown code fences and contain the SysUISdk generation, explicit SDK root, and clean Release build commands.
- Build was not run because this change only documents the previously verified commands and the user explicitly requested no build execution.

## Open questions

- None. The project remains pinned to AOSP `android-17.0.0_r1` and the generator's existing stock base platform requirements.
