# Task 005: NeverCompile classpath research (docs only)

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: produce a background research document for the `dalvik.annotation.optimization.NeverCompile` classpath gap so the user can choose a fix. **Research only — do not change any build file, jar, or SDK.** User directive 2026-08-13: more background is needed before deciding.

Authority: self-commit (never push), docs only.

Allowed Paths: `docs/architecture/2026-08-13-nevercompile-classpath-options.md`, `docs/orchestration/tasks/005-*.md`.

Forbidden Paths: everything else (no build files, no libs, no SDK changes).

Steps (evidence captured 2026-08-13 in task-005 worktree):

- [x] 1. Establish usage: `grep -rn 'NeverCompile' SystemUI-core/src SystemUI-*/src 2>/dev/null` — 11 unique files use `@NeverCompile` (10 .java + 1 .kt). See doc §2.
- [x] 2. Establish where the class really lives: `unzip -l` on `core-libart` javac jar (all 6 optimization annotations), `art.module.public.api.stubs.module_lib` combined (4), `libs/android_module_lib_stubs_current.jar` (4, incl. NeverCompile), and confirmed absence from SysUISdk `android.jar` (only CriticalNative+FastNative), `core-for-system-modules.jar` (same partial set), and `libs/framework.jar` (no dalvik.* at all). See doc §3.
- [x] 3. Check how AOSP SystemUI gets it: `frameworks/base/packages/SystemUI/Android.bp` does not declare `core-libart`; the class reaches javac via the platform default bootclasspath (`core-for-system-modules` module-lib SDK, which does contain NeverCompile). Our SysUISdk ships the public-SDK slice that omits it. See doc §4.
- [x] 4. Check the reference project: CarSystemUIGradle uses the same `compileOnly(android_module_lib_stubs_current.jar)` mechanism but its CarSystemUI sources never import `NeverCompile`, so it sidesteps the gap. See doc §5.
- [x] 5. Research doc written: `docs/architecture/2026-08-13-nevercompile-classpath-options.md` with problem statement, step 1–4 evidence, three options (a/b/c) each with provenance + runtime analysis, and a recommendation (option a). Key research finding: a `compileOnly` jar on the regular classpath cannot resolve the class because the `android.jar` bootclasspath already owns the partial `dalvik.annotation.optimization` package (split-package shadowing) — this is why the already-wired `android_module_lib_stubs_current.jar` does not fix it.
- [x] 6. Worker commit (never push): `git add docs/architecture/2026-08-13-nevercompile-classpath-options.md && git commit -m "docs: research NeverCompile classpath options"`

Acceptance (architect re-runs): doc exists, contains command evidence for steps 1–4, three options with a recommendation, no other files in the commit.
