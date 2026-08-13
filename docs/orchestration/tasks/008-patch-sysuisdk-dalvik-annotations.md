# Task 008: Patch SysUISdk with dalvik.annotation.optimization classes (NeverCompile fix)

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: implement the user-approved Option (a) from `docs/architecture/2026-08-13-nevercompile-classpath-options.md` — patch SysUISdk `android.jar` and `core-for-system-modules.jar` with the missing `dalvik.annotation.optimization.*` classes from AOSP `core-libart`, so the NeverCompile javac group (20 errors) resolves. **The research doc is the spec; read it first.**

Authority: redline-gated — SysUISdk mutation is **pre-approved by the user on 2026-08-13** ("同意a: Patch SysUISdk") for exactly this change. Any deviation from the research doc's Option (a) scope stops and escalates. Commit but never push.

Allowed Paths: `tools/install_sdk.py` **or** a new `tools/patch_sdk_dalvik_annotations.py` (choose one; extending `install_sdk.py` is preferred if it fits its idiom), `tools/tests/` (the matching test file), `docs/issues/`, `docs/orchestration/tasks/008-*.md`.

Forbidden Paths: everything else — no `build.gradle.kts` changes (Option (a) explicitly needs none), no `libs/`, no `gradle/`, no `SystemUI-*/src/**`, no maintained docs (`AGENTS.md`, `docs/HANDOFF.md`, `docs/CURRENT_STATE.md` — the architect syncs those at merge).

Key facts (verified by the architect; re-verify before relying):

- Source jar: `/home/conv/myspace/aosp/out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar` — contains all 6 `dalvik/annotation/optimization/*.class`. If multiple `core-libart` variants exist, use a `javac/` (never `turbine`) variant and record the exact path used.
- Targets: `/home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar` and `.../core-for-system-modules.jar` — each currently has only `CriticalNative` + `FastNative` from that package.
- Missing classes to inject (4): `NeverCompile`, `NeverInline`, `DeadReferenceSafe`, `ReachabilitySensitive` (exact set = classes present in core-libart but absent from the target jar; do not overwrite existing entries).

Steps:

- [ ] 1. Read `docs/architecture/2026-08-13-nevercompile-classpath-options.md` (spec, especially §Option (a) guardrails and §7 evidence index).
- [ ] 2. Verify source and target state:

```bash
unzip -l /home/conv/myspace/aosp/out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar | grep 'dalvik/annotation/optimization/'
unzip -l /home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar | grep 'dalvik/annotation/optimization/'
unzip -l /home/conv/Android/Sdk/platforms/android-SysUISdk/core-for-system-modules.jar | grep 'dalvik/annotation/optimization/'
```

- [ ] 3. Implement the patch tool (Python, per ADR 0002): idempotent (re-run is a no-op reporting "already patched"), creates a timestamped or `.orig` backup of any target jar before first mutation (matching the existing `android.jar.orig` precedent), injects only the missing class entries (no overwrites, no other packages), and prints a deterministic summary of what was added. Follow `tools/install_sdk.py`'s structure/idioms.
- [ ] 4. Add unittest coverage in the matching `tools/tests/test_*.py`: idempotency, no-overwrite of existing entries, backup creation, and correct class set (use fixture jars under a temp dir — never touch the real SDK in tests).

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -3
```

Expected: `OK`, test count > 65.

- [ ] 5. Run the tool against the real SDK, then verify:

```bash
unzip -l /home/conv/Android/Sdk/platforms/android-SysUISdk/android.jar | grep -c 'dalvik/annotation/optimization/'
unzip -l /home/conv/Android/Sdk/platforms/android-SysUISdk/core-for-system-modules.jar | grep -c 'dalvik/annotation/optimization/'
```

Expected: 6 classes in each (4 injected + 2 pre-existing).

- [ ] 6. Acceptance run (from the worktree root):

```bash
./gradlew :SystemUI-core:compileDebugJavaWithJavac --console=plain 2>&1 | tee /tmp/task008.log >/dev/null
grep -c 'NeverCompile' /tmp/task008.log || echo '0 (NeverCompile group gone)'
grep -c 'error:' /tmp/task008.log
```

Expected: NeverCompile group = 0. Record the total error count truthfully (0 errors = javac milestone; any remainder belongs to a new group — report, do not fix outside scope). Regression guard: `grep -cE 'keepanno|monet|motiontool' /tmp/task008.log` must be 0 (shadowing boundary intact).

- [ ] 7. Append a dated note to a new `docs/issues/2026-08-13-nevercompile-sysuisdk-patch.md`: exact source jar path, injected class list, backup locations, before/after unzip counts, javac result, and a reminder that the SDK is not in git so the tool must be re-run after a fresh SDK install.

- [ ] 8. Worker commit (never push):

```bash
git add tools/ docs/issues/2026-08-13-nevercompile-sysuisdk-patch.md docs/orchestration/tasks/008-patch-sysuisdk-dalvik-annotations.md
git commit -m "feat(tools): patch SysUISdk with dalvik optimization annotations from core-libart"
```

Acceptance (architect re-runs): Step 5 unzip counts (6 classes each) against the real SDK, Step 6 greps on a fresh log, tool tests pass, and `git show --stat HEAD` is limited to Allowed Paths.
