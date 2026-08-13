# 2026-08-13 — Task 005: NeverCompile classpath research (docs only)

> Worker: herdr task-005 pane. Brief:
> `docs/orchestration/tasks/005-nevercompile-research.md`. Authority: self-commit
> (never push). Allowed paths: the research doc + the brief. No build/jar/SDK
> changes.

## Background

Task 7 (`:app:assembleDebug`, 2026-08-12) attributed one of 8 javac root-cause
groups to `import dalvik.annotation.optimization.NeverCompile` being
unresolved across 11 SystemUI source files. User directive 2026-08-13: more
background is needed before deciding a fix. This task produces that background.

## What was done

- Read AGENTS.md, CHARTER, and the task brief; printed CONTRACT block.
- Ran all 4 evidence steps (usage, class location, AOSP delivery, reference
  project) with commands re-executed in the task-005 worktree on 2026-08-13.
- Wrote `docs/architecture/2026-08-13-nevercompile-classpath-options.md`
  (problem statement, evidence, three options, recommendation).

## Key research finding

The class **is already present** in `libs/android_module_lib_stubs_current.jar`
and that jar is **already wired** as `compileOnly` in
`SystemUI-core/build.gradle.kts:153` (since commit `000b1261`, 2026-07-21).
The reason javac still fails is **bootclasspath split-package shadowing**:
SysUISdk `android.jar` (compileSdk bootclasspath) contains the
`dalvik.annotation.optimization` package but only `CriticalNative` and
`FastNative` — not `NeverCompile`. Because the package is "found" on the
bootclasspath, javac does not merge the missing class from the regular
compile-classpath jar.

Control evidence: other `compileOnly` jars (`keepanno`, `monet`,
`motion_tool_lib`) resolve cleanly (0 errors in `/tmp/final-app.log`) —
`compileOnly(files(...))` works; only `NeverCompile` fails, and it is the only
imported class whose package also exists (partially) on `android.jar`.

## Options summarized

- **(a) Patch SysUISdk `android.jar`** with the 4 missing
  `dalvik.annotation.optimization.*` classes from AOSP `core-libart`
  (AGENTS.md §2.4 precedent). **Recommended** — fixes root cause, no
  build-file change.
- **(b) New tracked `compileOnly` dalvik-annotations jar** — **only works on
  `JavaCompile.bootstrapClasspath`**, not plain `compileOnly` (shadowing).
  Second-best; in-repo/reproducible but touches build config.
- **(c) Extend `libs/keepanno-annotations.jar`** — **does not work** as a
  regular `compileOnly` jar (shadowing); co-mingles two upstreams. Not
  recommended.

## Verification

- Acceptance per brief: doc exists at the allowed path, contains command
  evidence for steps 1–4, three options with a recommendation, no other files
  in the commit.
- Build status: **not run** (docs-only task; brief forbids build/jar/SDK
  changes). No build was invoked to produce this document.

## Files touched

- `docs/architecture/2026-08-13-nevercompile-classpath-options.md` (new)
- `docs/orchestration/tasks/005-nevercompile-research.md` (checkboxes ticked)

## Remaining

- Implementation of the chosen option is out of scope for this task; it
  requires user authorization (rule F / CHARTER Part 5 for SDK patching, or
  CHARTER Part 5.4 for a build-file change) and a separate implementation
  plan.
- The other 7 Task 7 root-cause groups remain tracked in
  `docs/issues/2026-08-12-current-progress-standards-review.md`.
