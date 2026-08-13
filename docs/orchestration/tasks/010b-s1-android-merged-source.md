# Task 010b: Re-track `android-merged.jar` as the S1 source (continuation of Task 010)

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Context: Task 010 (commit `a9d3c472`, branch `task-010`, this same worktree) built the reproducible pipeline, but `--verify` reports a single DIFF: the live `android.jar` contains 2638 entries (1266 class files + dirs) whose true source was `libs/android-merged.jar`, deleted as a "dead dependency" in `683ef39a`.

**User decision (2026-08-13): re-track the recovered `android-merged.jar` under `libs/` as the declared S1 source.** The blob survives in git history and was architect-verified to cover 100% of the missing entries.

Authority: redline-gated — `libs/` addition + S1 semantics change are **pre-approved by the user on 2026-08-13** for exactly this change. Staging-only SDK rule from Task 010 still applies (never touch the live `android-SysUISdk`). Commit but never push.

Allowed Paths: `libs/android-merged.jar` (new, recovered blob), `tools/build_sysuisdk.py`, `tools/tests/test_build_sysuisdk.py`, `docs/architecture/2026-08-13-sysuisdk-reproducible-build.md`, `docs/issues/2026-08-13-sysuisdk-reproducible-build.md`, `docs/orchestration/tasks/010b-*.md`.

Forbidden Paths: everything else.

Steps:

- [x] 1. Recover the blob from git history and verify integrity:

```bash
git show 5836ec44:libs/android-merged.jar > libs/android-merged.jar
sha256sum libs/android-merged.jar
```

Expected SHA-256: `67ceccc5cd9d610189d45596481b1f8fefe557c8b41a2820d9d74df536770d79`. Hard-fail on mismatch.
  - Done. SHA-256 matches exactly (`67ceccc5…770d79`).

- [x] 2. Update `tools/build_sysuisdk.py` S1 to use `libs/android-merged.jar` as the merge source. First determine the exact semantics empirically (does S1 replace `android.jar` entries wholesale with the merged jar's, or add-only? what happens to the base jar's `resources.arsc`/`res/` which the merged jar may lack?) — the acceptance is `--verify` reaching 7/7 PASS, so iterate on semantics until the staging `android.jar` matches the live one. Document the final semantics in the architecture doc.
  - Done. Empirical audit: `android-merged.jar` is a strict superset of live-minus-4-dalvik (0 CRC diffs on 38892-entry intersection; 0 extra; carries `resources.arsc`+`res/` verbatim, 8451 entries == live). Final S1 semantics = **wholesale copy** of `android-merged.jar` as `android.jar` (MANIFEST.MF pinned; dir entries dropped); base jar not consulted. S3 adds 4 dalvik → 37524 = live. CLI `--framework-jar`→`--merged-jar`, `DEFAULT_FRAMEWORK_JAR`→`DEFAULT_MERGED_JAR`. See arch doc §2.4.2.
- [x] 3. Update `tools/tests/test_build_sysuisdk.py` fixtures for the new S1 source; run the full suite:

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -3
```

Expected: `OK`, count > 103.
  - Done. 104 tests, OK (>103). Fixture `_make_framework_jar`→`_make_merged_jar`; S1 tests rewritten for wholesale-copy semantics; added `S1ConfigTest` regression guard.

- [x] 4. Full staging rebuild + verify:

```bash
python3 tools/build_sysuisdk.py --clean --target /home/conv/Android/Sdk/platforms/android-SysUISdk-staging
python3 tools/build_sysuisdk.py --verify --target /home/conv/Android/Sdk/platforms/android-SysUISdk-staging
echo "verify exit: $?"
```

Expected: build exit 0; **verify exit 0 with 7/7 PASS** (the previous android.jar DIFF must be gone).
  - Done. build exit 0; verify exit 0; 7/7 PASS (`android.jar: PASS staging=37524 live=37524 missing=0 extra=0 crc_diff=0`).

- [x] 5. Update docs: architecture doc gets the provenance chain (`libs/android-merged.jar` ← recovered from git history `5836ec44` ← 2026-07-22 device/AOSP framework merge used to build the live SDK; deleted in `683ef39a`, re-tracked 2026-08-13), the S1 semantics, and the removal of the §7 known-delta/REDLINE section (now resolved); issue doc gets a dated note with the verify report.
  - Done. Arch doc §2.4.2 (semantics), §2.4.3 (provenance chain), §3 (table), §4 (pipeline), §6 (7/7 PASS), §7 (RESOLVED). Issue doc §7 dated note appended.
- [x] 6. Worker commit (never push):
  - Done. Commit on `task-010` (see `git show --stat HEAD`).

```bash
git add libs/android-merged.jar tools/build_sysuisdk.py tools/tests/test_build_sysuisdk.py \
  docs/architecture/2026-08-13-sysuisdk-reproducible-build.md docs/issues/2026-08-13-sysuisdk-reproducible-build.md \
  docs/orchestration/tasks/010b-s1-android-merged-source.md
git commit -m "feat(tools): re-track android-merged.jar as SysUISdk S1 source; staging verify 7/7"
```

Acceptance (architect re-runs): the SHA-256 check, Step 3 suite, Step 4 fresh staging build + verify exit 0, and `git show --stat HEAD` limited to Allowed Paths.
