# Task 005: NeverCompile classpath research (docs only)

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: produce a background research document for the `dalvik.annotation.optimization.NeverCompile` classpath gap so the user can choose a fix. **Research only — do not change any build file, jar, or SDK.** User directive 2026-08-13: more background is needed before deciding.

Authority: self-commit (never push), docs only.

Allowed Paths: `docs/architecture/2026-08-13-nevercompile-classpath-options.md`, `docs/orchestration/tasks/005-*.md`.

Forbidden Paths: everything else (no build files, no libs, no SDK changes).

Steps:

- [ ] 1. Establish usage: `grep -rn 'NeverCompile' SystemUI-core/src SystemUI-*/src 2>/dev/null` — which files use it and for what.
- [ ] 2. Establish where the class really lives: `unzip -l` the Soong `core-libart` javac jar(s) and `art.module.public.api.stubs.module_lib` for `dalvik/annotation/optimization/NeverCompile.class`; confirm absence from SysUISdk `android.jar`, `core-for-system-modules.jar`, and `libs/framework.jar` (evidence already in the Task 7 issue record — verify, don't assume).
- [ ] 3. Check how AOSP SystemUI gets it: inspect `frameworks/base/packages/SystemUI/Android.bp` and Soong system-modules mechanics for why javac sees the class in AOSP builds.
- [ ] 4. Check the reference project: `grep -rn 'NeverCompile\|dalvik' /home/conv/myspace/CarSystemUIGradle --include='*.kts' --include='*.md' | head -20` — did CarSystemUIGradle solve this, and how?
- [ ] 5. Write the research doc with: problem statement; findings from steps 1–4 with command evidence; at least three options — (a) patch SysUISdk `android.jar` with the dalvik annotation classes from `core-libart` (AGENTS.md §2.4 precedent), (b) a new tracked `compileOnly` annotations jar packaged from `core-libart` by a Python tool (flags-jar precedent), (c) extend the existing `libs/keepanno-annotations.jar` mechanism — each with provenance compliance (rules F/R), runtime implications (annotation retention, `@NeverCompile` is a no-op annotation), and a recommendation.
- [ ] 6. Worker commit (never push): `git add docs/architecture/2026-08-13-nevercompile-classpath-options.md && git commit -m "docs: research NeverCompile classpath options"`

Acceptance (architect re-runs): doc exists, contains command evidence for steps 1–4, three options with a recommendation, no other files in the commit.
