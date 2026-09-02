# Task 099 — C5 `android.service.dreams.Flags` runtime repair

## Goal

Use the accepted frozen-APK diagnosis to restore the fresh Debug APK to stable Android 17 runtime behavior, while protecting Release and preventing the same class of uncovered AOSP aconfig repackaging references from recurring. This task may diagnose, modify production build logic, add or update tests and static gates, build Debug and Release APKs, inspect artifacts, operate Herdr, validate on the managed emulator, and create focused commits. The Worker must follow `AGENTS.md`; no additional startup or CONTRACT ceremony applies.

## Accepted starting evidence

- Failing Debug APK: `app/build/outputs/apk/debug/app-debug.apk`, size `190547804`, SHA-256 `f3af35d9da9d8f6f41b017276844e2b6de1e3f6074312fb5a67f76280a1f532b`.
- Task 098 runtime failure: repeated `NoClassDefFoundError` for `Landroid/service/dreams/Flags;`, first observed from `com.android.wm.shell.keyguard.KeyguardTransitionHandler.onInit`.
- AOSP mapping authority: `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt`, SHA-256 `f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97`.
- Phase 1 diagnosis in `/tmp/task099-c5-dreams-flags-diagnosis/`: 41 real old-owner `invoke-static` instructions across 40 methods, 39 classes, and 5 DEX files; no old definition; no hidden definition; all 39 caller classes absent from the current 166-class allowlist; the four-rule mapping subset omits dreams while the full AOSP rules include it.
- Temporary scripts under `/tmp` are valid diagnostic evidence and may be reused or improved.

## Engineering direction

The Worker chooses the most technically sound compliant route. At minimum it should:

1. Check current Debug and Release artifacts against the complete authoritative AOSP repackaging rule set for real residual instruction references, so the repair does not merely move the crash to the next old owner.
2. Compare the previously healthy Debug artifact/build state with the current failing artifact where practical, and document any conclusion that can actually be proven.
3. Implement a minimal maintainable build-time reference rewrite and regression gate. Preserve the existing reference-only invariants: do not package platform target definitions, do not rewrite class definitions/self-references or ordinary strings unintentionally, and keep SystemUI mirrored source unchanged.
4. Run focused tests and useful static checks. Build Debug and Release serially; at most one heavy build may run on the machine at a time.
5. Inspect both APKs for residual old-owner instructions and hidden target definitions. Runtime-test the new Debug APK when ready; proceed toward Release runtime once Debug is stable.
6. Create focused English commit(s), but do not push. Report uncertain architectural/product choices to the Chief instead of guessing.

## Project boundaries

All boundaries come from `AGENTS.md`: no stubs, no fabricated resources, no unmarked AOSP source/resource drift, no copying framework source into SystemUI, no suppression/dontwarn/class-deletion/post-DEX workaround, and Python execution through `uv`. Worker experiments, temporary files, Herdr operations, builds, device validation, and commits are allowed when they respect those rules and the single-heavy-build resource limit.

## Success evidence

Success is not a document or a narrow four-rule PASS. It requires a technically reviewed fix, focused tests, fresh Debug and Release builds, complete relevant static residual checks, and ultimately stable Debug and Release runtime behavior across the required reboot gates. Failures should be preserved and reported honestly so the next hypothesis can be tested without repeating work.
