# Task 011: S4 — overlay AOSP framework-res resources into SysUISdk (fix androidprv linking)

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: add stage S4 to `tools/build_sysuisdk.py` that overlays the AOSP `framework-res.apk` resources (`resources.arsc` + `res/`) into the SDK `android.jar`, resolving the `:app:processDebugResources` `androidprv:` errors (AGENTS.md §2.4 item 2; reference-project 问题二十六). Precedent and pipeline: `docs/architecture/2026-08-13-sysuisdk-reproducible-build.md`.

Authority: redline-gated — **live SDK mutation is pre-approved by the user on 2026-08-13** ("framework-res.apk → SysUISdk" approval, now safe because the SDK is reproducible from scratch since `dd7d9cea`). Commit but never push.

Allowed Paths: `tools/build_sysuisdk.py`, `tools/tests/test_build_sysuisdk.py`, `libs/framework-res.apk` (new, tracked input), `docs/architecture/2026-08-13-sysuisdk-reproducible-build.md`, `docs/issues/2026-08-13-sysuisdk-reproducible-build.md`, `docs/orchestration/tasks/011-*.md`.

Forbidden Paths: everything else — no `build.gradle.kts` changes, no `SystemUI-*` source, no version catalog.

Key facts (architect-verified):

- AOSP source artifact: `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/core/res/framework-res/android_common/framework-res.apk` (canonical Soong product of `frameworks/base/core/res`).
- Current blocker evidence: `/tmp/task009.log` — `error: resource androidprv:attr/materialColorSurfaceContainerHighest not found.` etc. (`:app:processDebugResources`).
- The live SDK's `android.jar` already carries a **May-27 snapshot** of framework resources (via `android-merged.jar`) that is stale relative to the current AOSP tree — that is exactly why the `androidprv` symbols are missing.

Steps:

- [x] 1. Track the input (reproducibility requirement — the SDK must be rebuildable even without the AOSP `out/` dir):

```bash
cp /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/core/res/framework-res/android_common/framework-res.apk libs/framework-res.apk
sha256sum libs/framework-res.apk
```

- [x] 2. Implement S4 in `tools/build_sysuisdk.py`: strip the existing `resources.arsc` + `res/**` entries from the target `android.jar`, then add `resources.arsc` + `res/**` from `libs/framework-res.apk` (deterministic, idempotent, `.orig`-style backup on first mutation, consistent with existing stages). S4 runs after S1 (which wholesale-copies `android-merged.jar`) and before S5. Extend `--verify` so a staging build WITH S4 is expected to differ from the live SDK **only** in `android.jar`'s resource entries until the patch is applied to live — model this as an explicit `--expect-s4-delta` mode or per-stage verify reporting; do not weaken the strict 7/7 check for pre-S4 reproduction.
- [x] 3. Tests: fixture-level S4 tests (strip+add semantics, idempotency, backup, determinism). Full suite:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -3
```

Expected: `OK`, count > 104.

- [x] 4. Build staging with S4 and sanity-check the resource inventory (e.g. confirm `resources.arsc` differs from the pre-S4 one and `res/` entry count matches `libs/framework-res.apk`).
- [~] 5. **Apply to the live SDK** (pre-approved): apply DONE (timestamped backups created; live android.jar synced). Acceptance NOT MET: `:app:processDebugResources` still fails with 20 `androidprv:` errors — a SECOND root cause (AGP merger drops `xmlns:androidprv`) is the sole remaining blocker, out of scope (build config). See issue doc §8.4–§8.5 & arch doc §8.2. REDLINE escalated. implement/use an `--apply` step that syncs the staging result onto `/home/conv/Android/Sdk/platforms/android-SysUISdk` with a timestamped backup of every overwritten file (or document and execute an equivalent safe rename). Then run the real acceptance:

```bash
./gradlew :app:processDebugResources --console=plain 2>&1 | tee /tmp/task011.log >/dev/null
grep -E 'BUILD (SUCCESSFUL|FAILED)' /tmp/task011.log | tail -1
grep -c 'androidprv' /tmp/task011.log || echo '0 (androidprv errors gone)'
```

Expected: `0` androidprv errors. If BUILD still fails on a NEW layer, capture the failing task + first errors and report — do not fix beyond this brief.
- [x] 6. Diagnostics (not acceptance): `./gradlew :app:assembleDebug --console=plain 2>&1 | tee /tmp/task011-app.log >/dev/null` — record how far it gets (failing task + first error lines, or the APK path on success).
- [x] 7. Docs: architecture doc — S4 spec, input provenance (`libs/framework-res.apk` ← AOSP Soong path above + regeneration note), the live-apply procedure, fresh-machine instructions updated (pipeline now S0–S5). Issue doc — dated note with all command outputs and the apply record.
- [x] 8. Worker commit (never push):

```bash
git add libs/framework-res.apk tools/build_sysuisdk.py tools/tests/test_build_sysuisdk.py \
  docs/architecture/2026-08-13-sysuisdk-reproducible-build.md docs/issues/2026-08-13-sysuisdk-reproducible-build.md \
  docs/orchestration/tasks/011-framework-res-overlay.md
git commit -m "feat(tools): S4 framework-res overlay for SysUISdk; fix androidprv resource linking"
```

Acceptance (architect re-runs): Step 3 suite, Step 5's two greps, `git show --stat HEAD` limited to Allowed Paths, and a spot-check that live `android.jar` now contains the previously missing symbols.
