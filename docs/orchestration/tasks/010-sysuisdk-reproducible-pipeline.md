# Task 010: Reproducible SysUISdk build pipeline (S0–S3 + S5, staging verification)

> Orchestrated brief. Protocol: docs/orchestration/CHARTER.md + worker-contract skill. Workers commit but never push.

Goal: make the SysUISdk platform **reproducible from scratch** — a single Python orchestrator (`tools/build_sysuisdk.py`) that rebuilds the SDK into a **staging directory** and verifies inventory-level equivalence with the live SDK. This brief covers stages S0–S3 + S5 (reproduce the CURRENT live SDK exactly). The framework-res stage (S4) is the next brief — do NOT add it here.

User requirement (2026-08-13): "SysUISDK 的构建必须是可以复现的……即使删除了你还是能构建出来" — the pipeline + docs are the deliverable; staging diff is the proof.

Authority: redline-gated — SDK-area work is **pre-approved by the user on 2026-08-13 for staging-only** (`android-SysUISdk-staging`). **Never write to, rename, or delete `~/Android/Sdk/platforms/android-SysUISdk`** (the live SDK). Commit but never push.

Allowed Paths: `tools/build_sysuisdk.py` (new), `tools/tests/test_build_sysuisdk.py` (new), `tools/install_sdk.py` and `tools/patch_sdk_dalvik_annotations.py` (light adaptation only if the orchestrator needs an importable entry point — keep their CLI behavior unchanged), `docs/architecture/2026-08-13-sysuisdk-reproducible-build.md` (new), `docs/issues/`, `docs/orchestration/tasks/010-*.md`.

Forbidden Paths: everything else — especially the live `android-SysUISdk` directory, any `build.gradle.kts`, `libs/`, `gradle/`.

Key facts (architect-verified; re-verify during the audit):

- Live SDK: `/home/conv/Android/Sdk/platforms/android-SysUISdk/` (api-level 37, codename SysUISdk).
- Pristine backups inside the live platform dir, dated 2026-05-27 (SDK creation):
  - `android.jar.orig` = stock android.jar BEFORE the 2026-07-22 framework.jar merge and BEFORE the dalvik-annotations patch.
  - `core-for-system-modules.jar.orig` = stock, before the dalvik-annotations patch.
  - `framework.aidl.bak-preaidl` = stock, before `install_sdk.py` appended hidden declarations.
- Candidate base platform: `/home/conv/Android/Sdk/platforms/android-37.0/` (verify by comparing its `android.jar` with `android.jar.orig`; if not identical, check other `android-3*` dirs and record which is the true base).
- S1 semantics are **unscripted** (2026-07-22 manual merge of `libs/framework.jar` into `android.jar`) — reverse-engineer the exact semantics by diffing `android.jar.orig` vs live `android.jar` (added entries; overwritten entries = same name, different CRC) and cross-check against `libs/framework.jar` contents. Encode the discovered semantics deterministically (e.g. "add entries absent from base; overwrite set X" — whatever the evidence shows), and document them.
- Existing scripted stages: S2 = `tools/install_sdk.py` (framework.aidl hidden ifaces/parcelables); S3 = `tools/patch_sdk_dalvik_annotations.py` (4 dalvik optimization classes from AOSP core-libart javac jar into both jars). Source jar: `/home/conv/myspace/aosp/out/soong/.intermediates/libcore/core-libart/android_common_apex31/javac/core-libart.jar`.

Steps:

- [ ] 1. **Audit**: diff `android.jar.orig` vs live `android.jar` (entry names + CRCs), diff `core-for-system-modules.jar.orig` vs live, diff `framework.aidl.bak-preaidl` vs live. Identify the base stock platform. Record every delta in `docs/architecture/2026-08-13-sysuisdk-reproducible-build.md` with command evidence (this doc is the audit + pipeline spec).
- [ ] 2. Implement `tools/build_sysuisdk.py` (Python, ADR 0002) with explicit stages and a `--target` directory (default `~/Android/Sdk/platforms/android-SysUISdk-staging`):
  - S0: copy the base platform to `--target` (skip if target exists and `--clean` not given; `--clean` removes the staging dir only — hard-fail if target resolves to the live SDK path), rewrite `package.xml` `localPackage path` to `platforms;android-SysUISdk` semantics for the staging name, copy `build.prop`.
  - S1: deterministic framework.jar merge replicating the audited semantics (source: `libs/framework.jar`, tracked in git).
  - S2: run the framework.aidl patch against the staging dir (reuse `install_sdk.py` logic by import or subprocess; do not duplicate the declaration lists — keep a single source of truth).
  - S3: run the dalvik-annotations patch against the staging dir (same reuse rule).
  - S5: `--verify` mode — compare staging vs live SDK: entry inventories (names+CRC) of `android.jar` and `core-for-system-modules.jar`, byte-equality of `framework.aidl`, presence/shape of `package.xml`, `build.prop`, `data/`, `optional/`. Print a per-file PASS/DIFF report and exit non-zero on any DIFF.
  - All stages idempotent; every mutating stage creates `.orig`-style backups inside the staging dir on first mutation.
- [ ] 3. Implement `tools/tests/test_build_sysuisdk.py`: stage behavior on fixture trees (temp dirs), idempotency, backup creation, live-SDK path hard-fail guard, verify-mode PASS/DIFF logic. Never touch the real SDK in tests.

```bash
python3 -m unittest discover -s tools/tests -p 'test_*.py' 2>&1 | tail -3
```

Expected: `OK`, count > 77.

- [ ] 4. **Full staging run** (the reproducibility proof):

```bash
python3 tools/build_sysuisdk.py --clean --target /home/conv/Android/Sdk/platforms/android-SysUISdk-staging
python3 tools/build_sysuisdk.py --verify --target /home/conv/Android/Sdk/platforms/android-SysUISdk-staging
```

Expected: build completes; verify prints PASS for every compared file, exit 0. If a DIFF is found, investigate and fix the stage semantics until verify passes — that is the point of this brief. Record the full report in the architecture doc.

- [ ] 5. Finish the architecture doc: provenance table (every file in the live SDK → which stage produces it → source artifact path), the audit findings, pipeline usage (fresh-machine instructions: clone repo → run S0–S3 → verify → rename staging to `android-SysUISdk`), and the note that S4 (framework-res) lands in the next brief.
- [ ] 6. Append a dated process note to `docs/issues/2026-08-13-sysuisdk-reproducible-build.md` (rule D).
- [ ] 7. Worker commit (never push):

```bash
git add tools/build_sysuisdk.py tools/tests/test_build_sysuisdk.py tools/install_sdk.py tools/patch_sdk_dalvik_annotations.py \
  docs/architecture/2026-08-13-sysuisdk-reproducible-build.md docs/issues/2026-08-13-sysuisdk-reproducible-build.md \
  docs/orchestration/tasks/010-sysuisdk-reproducible-pipeline.md
git commit -m "feat(tools): reproducible SysUISdk build pipeline with staging verification"
```

(Drop the two existing tool paths from the commit if they ended up unmodified.)

Acceptance (architect re-runs): Step 4's two commands (fresh staging build + verify exit 0), the unittest suite, and `git show --stat HEAD` limited to Allowed Paths.
