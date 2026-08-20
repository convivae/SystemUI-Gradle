# Task 042 implementation plan — R8 aconfig assumption closure

> **For worker:** follow `worker-contract`, `AGENTS.md`, `docs/orchestration/CHARTER.md`,
> and `docs/orchestration/tasks/042-r8-aconfig-assumption-closure.md` before this plan.
> Use TDD and stop on every REDLINE condition.

**Goal:** Close the final `AssumeTrueForR8` R8 ref structurally while preserving AOSP's
exported flag-assumption rules, moving fresh R8 exactly 1→0 without packaging build-time
annotations into the APK.

**Architecture:** Add independent SysUISdk stage `S3c` for one source-identical class and
import the complete byte-exact AOSP `aconfig_proguard.flags` as an app R8 input. Reuse the
Task 041 exact-entry engine; do not widen its frozen Task 041 allowlist.

**Tooling:** Python `unittest`, deterministic ZIP patching, `build_sysuisdk.py`, AGP 9.3.1 /
Gradle 9.5.0, `apkanalyzer`, R8 mapping configuration.

---

## Task 1: Freeze baseline and provenance

**Evidence only:** `/tmp/task042-*`

1. Ensure no other SystemUI Gradle process is active.
2. Run fresh `:app:minifyReleaseWithR8 --rerun-tasks` with workers=4, `pipefail`, `tee`, and a
   status file.
3. Parse `missing_rules.txt`; assert real Gradle exit 1 and exact set
   `{com.android.aconfig.annotations.AssumeTrueForR8}`.
4. Assert source JAR SHA-256
   `ef431f923f6925ec835282afb3ee62c909987dd2f053dbcdccc1f7294923f551`.
5. Assert exact class entry size/SHA-256 `413` /
   `d4602718f42729ea476648dc391f88db7e9a1b21a344c566eadb6077e4691468`.
6. Assert AOSP rule file size/SHA-256 `778` /
   `b6a85445ea517fc4861c0a5d68ea8af8d1b6b4f2e7a4a569c7830891e73b2f01`.
7. Assert both current SysUISdk targets lack the entry and the debug APK does not define it.

Any mismatch is REDLINE before edits.

## Task 2: TDD the exact one-entry patcher

**Files:**
- Create `tools/patch_sdk_aconfig_r8_annotation.py`
- Create `tools/tests/test_patch_sdk_aconfig_r8_annotation.py`

### RED

Add tests that require:

- exactly one immutable entry constant;
- source entry presence and byte provenance;
- missing target injection;
- source-missing rejection;
- differing target collision rejection without mutation;
- matching existing entry accepted as no-op;
- deterministic output and second-run byte-for-byte no-op;
- `.bak-preaconfigr8` created on first mutation and never overwritten;
- no package-prefix expansion.

Run the focused test and capture the expected failure before implementation.

### GREEN

Implement a narrow wrapper around Task 041's generic `ClassSlice`, `validate_target`, and
`patch_target` engine. The wrapper owns only the Task 042 entry and backup suffix; it must not
change `task041_slices()` or the frozen 35-entry constants.

Run focused tests and commit:

```text
build: add exact AssumeTrueForR8 SDK patcher
```

## Task 3: TDD SysUISdk S3c

**Files:**
- Modify `tools/build_sysuisdk.py`
- Modify `tools/tests/test_build_sysuisdk.py`

### RED

Add tests requiring:

- `ALL_STAGES` includes `s3c` after `s3b` and before `s4`;
- default stages include `s3c`;
- stage reuses `--aconfig-annotations-jar`;
- both target JARs are read-only validated before either mutation;
- exactly one source-identical entry is added to each target;
- collision in the second target leaves the first untouched;
- repeat execution is a no-op;
- CLI/default-stage wiring and documentation include S3c;
- S5/apply behavior remains guarded and unchanged.

Capture expected focused-test failure.

### GREEN

Implement `stage_s3c(...)`, import the new patcher, wire stage order/defaults, and update CLI
help/docstring. Normalize `android.jar` manifest exactly as S3/S3b do.

Run both focused suites, then the complete Python suite. Commit:

```text
build: add SysUISdk aconfig R8 assumption stage
```

## Task 4: TDD the exported AOSP rules

**Files:**
- Create `app/aconfig_proguard.flags`
- Modify `app/build.gradle.kts`
- Create `tools/tests/test_aconfig_r8_rules.py`

### RED

Add a repository-level test that requires:

- exact 778-byte expected AOSP file content and pinned SHA-256;
- no `dontwarn`;
- both `AssumeTrueForR8` rules are present exactly once in their respective blocks;
- the complete file also retains AOSP's paired false-assumption and
  `VisibleForTesting` rules;
- `app/build.gradle.kts` references this file in exactly the existing debug and release
  `proguardFiles(...)` lists.

Capture expected failure while the file/wiring is absent.

### GREEN

Copy, without editing, from:

```text
/home/conv/myspace/aosp/frameworks/libs/modules-utils/java/aconfig_proguard.flags
```

Wire `app/aconfig_proguard.flags` into both build types. Do not modify existing SystemUI,
plugin, common, or Kotlin rule files. Run focused/full tests and `git diff --check`. Commit:

```text
build: import AOSP aconfig R8 assumption rules
```

## Task 5: Staging, apply, debug, and release closure

1. Build independent `/tmp/task042-sdk-a` and `-b` with
   `s0,s1,s2,s3,s3b,s3c,s4`.
2. Assert complete `name→CRC` inventory equality between A/B target pairs.
3. Assert each target has all prior 35 Task 041 classes unchanged plus the exact new
   source-identical class (36 bridge classes total).
4. Pre-apply S5 must report only one extra entry per target; no unrelated delta.
5. Apply only with:

   ```bash
   python3 tools/build_sysuisdk.py --apply --source /tmp/task042-sdk-a
   ```

6. Post-apply strict S5 must report `ALL PASS`.
7. With no concurrent Gradle process, run serialized:

   ```bash
   ./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug \
     -Dorg.gradle.workers.max=4 --console=plain
   ```

8. Use APK defined-class inventory to assert `BRIDGED=36 PACKAGED=0`.
9. Run fresh release R8 with workers=4, `pipefail`, `tee`, and a status file. Require real
   exit 0 and `BUILD SUCCESSFUL`.
10. Require `missing_rules.txt` absent or containing zero `-dontwarn` class refs.
11. Require `app/build/outputs/mapping/release/configuration.txt` to contain the effective
    `AssumeTrueForR8` `-assumevalues` and `-assumenosideeffects` return-true rules.
12. Reconfirm committed AOSP rule bytes/SHA and class source bytes/SHA.

Any nonzero R8 exit, new missing ref, rule warning, absent effective rule, APK packaging, or
unrelated S5 difference is REDLINE.

## Task 6: Evidence and handoff

**Files:**
- Modify `docs/issues/2026-08-21-r8-aconfig-assumption-closure.md`
- Modify `docs/orchestration/tasks/042-r8-aconfig-assumption-closure.md`

Record:

- baseline/final real exits and exact missing-set delta;
- focused RED/GREEN and full Python count;
- source/rule provenance hashes;
- staging A/B inventories, pre/post S5, apply backup timestamp;
- debug status, APK `BRIDGED=36 PACKAGED=0`;
- release R8 success and effective configuration proof;
- exact immutable commit ranges and scope scan.

Commit:

```text
docs: record final R8 closure evidence
```

Finish clean, do not push, and emit the required four-part HANDOFF. Architect then performs
fixed-base/head dual-axis static review, main fresh verification, merge, push, and cleanup.
