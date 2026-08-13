# Task 001: Refresh libs/SystemUI-tags.jar from AOSP Soong output

## Goal

Replace the stale `libs/SystemUI-tags.jar` (2026 bytes, lacks
`EventLogTags.writeSysuiKeyguard(int,int)`) with the current AOSP Soong javac
jar (2086 bytes, contains it). This fixes one of the eight javac root-cause
groups recorded in `docs/issues/2026-08-12-current-progress-standards-review.md`
(Task 7, group "SystemUI-tags").

## Context

- Source of truth: `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI-tags/android_common/javac/SystemUI-tags.jar`
- Consumer: `SystemUI-core/build.gradle.kts` (`implementation(files(".../libs/SystemUI-tags.jar"))`)
- Generated from: `SystemUI-core/src/com/android/systemui/EventLogTags.logtags` (AOSP module `SystemUI-tags`)
- Verified on 2026-08-12: libs jar `javap | grep -c writeSysuiKeyguard` → 0; AOSP jar shows `public static void writeSysuiKeyguard(int, int);`

## Authority

self-commit (no red-line areas expected)

## Allowed Paths

- `libs/SystemUI-tags.jar`
- `docs/issues/2026-08-12-current-progress-standards-review.md` (append a short result note)
- `docs/orchestration/log.md` is updated by the architect, not the worker

## Forbidden Paths

- Everything else, especially: `SystemUI-*/src/**`, `SystemUI-*/res*/**`,
  `**/build.gradle.kts`, `gradle/**`, `AGENTS.md`, `docs/adr/**`

## Steps

- [ ] 1. Confirm the stale jar lacks the method:
  `javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep -c writeSysuiKeyguard` → expect `0`
- [ ] 2. Copy the AOSP jar over:
  `cp /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI-tags/android_common/javac/SystemUI-tags.jar libs/SystemUI-tags.jar`
- [ ] 3. Confirm the new jar has the method:
  `javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep writeSysuiKeyguard` → expect the method signature
- [ ] 4. Append a dated note to the issue record stating old/new sizes and the javap evidence
- [ ] 5. Commit:
  `git add libs/SystemUI-tags.jar docs/issues/2026-08-12-current-progress-standards-review.md`
  message: `fix(libs): refresh SystemUI-tags.jar from AOSP Soong output`

## Acceptance

`javap -classpath libs/SystemUI-tags.jar com.android.systemui.EventLogTags | grep writeSysuiKeyguard`
prints a line containing `writeSysuiKeyguard(int, int)`. `git status --short`
shows no modified files outside Allowed Paths.

## Reports To

Architect appends one line to `docs/orchestration/log.md` on completion.
