# R8 Platform/Build Library Classpath Closure (Task 041)

| Field | Value |
|---|---|
| Date | 2026-08-21 |
| Lifecycle | Active issue until Task 041 is merged and independently verified |
| Baseline | Fresh release R8: 7 unique missing refs |
| Target | Exact 7→1; only `AssumeTrueForR8` remains |
| Decision authority | User approved the two-stage structural bridge design in chat on 2026-08-21 |

## Background

Task 040 closed the SettingsLib runtime/program/resource graph and moved fresh R8 exactly
from 81 refs to 7. Six are platform or build-time library definitions that AOSP Soong exposes
to R8 through bootclasspath or transitive header-JAR channels, while AGP 9.3.1 exposes only
the compileSdk bootclasspath as R8 library input:

1. `android.compat.annotation.UnsupportedAppUsage`
2. `com.android.aconfig.annotations.AconfigFlagAccessor`
3. `com.android.tools.r8.keepanno.annotations.UsesReflection`
4. `libcore.io.IoUtils`
5. `libcore.util.NativeAllocationRegistry`
6. `org.apache.harmony.dalvik.ddmc.ChunkHandler`

The seventh ref, `com.android.aconfig.annotations.AssumeTrueForR8`, is deliberately reserved
for Task 042 because it has flag-optimization semantics and must be closed separately.

The primary-source channel analysis is in
`docs/architecture/2026-08-20-r8-platform-classpath-bridge.md`. Task 041 updates the earlier
B3 recommendation: after explicit user approval, `AconfigFlagAccessor` will receive a real
library-class definition rather than an exact `-dontwarn`. This keeps all six definitions out
of the APK while allowing R8 to inspect their real bytecode metadata.

## Approved architecture

Add a declarative `S3b` stage to `tools/build_sysuisdk.py`. The stage injects exact,
allowlisted class entries from real AOSP artifacts into both SysUISdk library JARs:

| Source artifact | Exact injected slice | Count | Channel meaning |
|---|---|---:|---|
| AOSP `core-libart.jar` | `IoUtils` + nested class | 2 | Faithful platform bootclasspath |
| AOSP `core-libart.jar` | `NativeAllocationRegistry` + nested classes | 4 | Faithful platform bootclasspath |
| AOSP `core-libart.jar` | complete `org.apache.harmony.dalvik.ddmc` package | 4 | Faithful platform bootclasspath closure for `ChunkHandler` |
| AOSP `unsupportedappusage.jar` | `UnsupportedAppUsage` + `Container` | 2 | Ch4→compileSdk workaround; build annotation remains library-only |
| AOSP `aconfig-annotations-lib.jar` | `AconfigFlagAccessor` only | 1 | Ch4→compileSdk workaround; Task 042 remains separate |
| tracked `libs/keepanno-annotations.jar` | complete annotation package | 22 | Ch4→compileSdk workaround; preserves `UsesReflection` metadata graph |

Total: exactly **35 class entries** in each target JAR. The DDMS four-class package and
keepanno 22-class package are closed slices because their referenced types form one owner
boundary; no other classes from their source JARs are permitted.

The live SDK may be changed only by a staging build followed by:

```bash
python3 tools/build_sysuisdk.py --apply --source <staging-dir>
```

Direct writes to `/home/conv/Android/Sdk/platforms/android-SysUISdk` are forbidden.

## Dependency decision

- These are not SystemUI-owned sources, so source copying is forbidden by rule F.
- They have no resources, so AAR/Maven delivery is not applicable.
- `implementation` is incorrect because AOSP treats them as external/library definitions,
  not APK program classes.
- AGP 9.3.1 has no public Ch3/Ch4-equivalent custom R8 library-JAR DSL.
- Broad or exact `-dontwarn` is rejected for Task 041 because the approved structural bridge
  can provide the real class definitions and preserve annotation semantics.
- Therefore SysUISdk library-class injection is the narrowest supported AGP bridge.

## Planned operations

1. Capture a fresh seven-ref baseline and exact source class inventories.
2. Add a deterministic exact-entry patcher with collision rejection, idempotency, scoped
   backup, source-byte provenance, and tests.
3. Integrate the patcher as `S3b` in `tools/build_sysuisdk.py`, with explicit source CLI
   inputs and fixture tests for both target JARs.
4. Build two independent full staging SDKs using `s0,s1,s2,s3,s3b,s4`; compare inventories
   and prove exactly 35 source-identical entries per target JAR.
5. Apply through `build_sysuisdk.py --apply`, then require strict S5 `ALL PASS`.
6. Run the debug hard gate and prove none of the 35 library classes is packaged in the APK.
7. Run fresh R8 and require exact 7→1, removed set equal to the six scoped refs, added=0,
   with only `AssumeTrueForR8` remaining.

## Error-count evolution

| Checkpoint | Unique R8 missing refs | Expected status |
|---|---:|---|
| Task 040 main fresh baseline | 7 | Verified, R8 exit 1 |
| Task 041 post-bridge | 1 | Required, R8 exit 1 |
| Task 042 follow-up | 0 | Future task |

Counts are diagnostic evidence under rule I; the exact set delta is a Task 041 acceptance
condition because it proves this bounded bridge neither hides nor introduces references.

## Red lines

Stop immediately and report `REDLINE:` if any occurs:

- Fresh baseline is not exactly the seven documented refs.
- Any source artifact lacks the exact approved class inventory.
- A target JAR already contains an allowlisted entry with bytes different from its approved
  source artifact.
- More or fewer than 35 entries would be injected into either target JAR.
- Any direct live-SDK edit is needed, or staging/apply/S5 cannot reproduce the live SDK.
- Any `src/**`, `res/**`, AOSP source, Gradle dependency/version/module, ProGuard/keep/dontwarn,
  runtime `implementation`, stub, or suppression change is proposed.
- Debug assembly fails, Compose/Kotlin classpath behavior regresses, or fresh R8 is not exact
  7→1 with zero additions.

## Pending questions

None for Task 041. `AssumeTrueForR8` remains intentionally pending for Task 042.

## Verification evidence

### Task 1 baseline (2026-08-21, worker)

**Fresh R8 baseline** (serialized, `-Dorg.gradle.workers.max=4`, `--rerun-tasks`):

- Command: `./gradlew :app:minifyReleaseWithR8 --rerun-tasks --console=plain -Dorg.gradle.workers.max=4`
- Real Gradle exit status: `1` (saved `/tmp/task041-r8-before.status`)
- `missing_rules.txt` normalized set = exactly the 7 documented refs
  (`BASELINE=7` asserted; saved `/tmp/task041-missing-before.txt`):
  `android.compat.annotation.UnsupportedAppUsage`,
  `com.android.aconfig.annotations.AconfigFlagAccessor`,
  `com.android.aconfig.annotations.AssumeTrueForR8`,
  `com.android.tools.r8.keepanno.annotations.UsesReflection`,
  `libcore.io.IoUtils`, `libcore.util.NativeAllocationRegistry`,
  `org.apache.harmony.dalvik.ddmc.ChunkHandler`

**Approved source artifacts** (sha256, saved `/tmp/task041-source-sha256.txt`):

```
decb349c4a27c33ce7e668e45bca3a9ca0382de9dd62f8f24c562aefdcd119af  core-libart.jar
25d4fe4e49731df2822efb0a6bfaef867da00dbfe2b1df40607c9eddd7cf2912  unsupportedappusage.jar
ef431f923f6925ec835282afb3ee62c909987dd2f053dbcdccc1f7294923f551  aconfig-annotations-lib.jar
056412aa7731b573f06940c792db082859ad49e464be08f464a4bba52fd856c5  libs/keepanno-annotations.jar
```

**Exact slice inventory asserted** (`SLICE_COUNTS=2,4,4,2,1,22`, `TOTAL=35`; saved
`/tmp/task041-approved-entries.txt`): every declared entry exists in its assigned
source; 35 unique entries; `AssumeTrueForR8.class` absent; keepanno annotations
package contains exactly the approved 22 classes (jar-level `META-INF/MANIFEST.MF`
and `r8-version.properties` lie outside the package and are never injected);
core-libart `org/apache/harmony/dalvik/ddmc/` non-directory entries are exactly the
4 approved classes. `aconfig-annotations-lib.jar` carries 5 classes total
(`AconfigFlagAccessor`, `AssumeFalseForR8`, `AssumeTrueForR8`, `VisibleForTesting`,
`VisibleForTesting$Visibility`) — only `AconfigFlagAccessor` is approved for Task 041.

### Task 2: exact-entry patcher (TDD)

- RED: `python3 -m unittest tools.tests.test_patch_sdk_r8_library_classes -v`
  → `FileNotFoundError: .../tools/patch_sdk_r8_library_classes.py` (24 tests
  could not load; implementation file absent), as expected.
- GREEN: after implementing `tools/patch_sdk_r8_library_classes.py`
  (immutable six-slice declarations totaling exactly 35 entries, `ClassSlice`,
  `task041_slices`, read-only `validate_target`, deterministic `patch_target`
  with collision rejection, scoped `.bak-prer8lib` backup, idempotency, and
  atomic `os.replace`):
  `Ran 24 tests in ...s` → `OK`.
  (One intermediate test-only fix: DOS zip timestamps have 2-second granularity,
  so the metadata-preservation fixture uses an even second.)

### Task 3: SysUISdk stage S3b integration (TDD)

- RED: `python3 -m unittest tools.tests.test_build_sysuisdk.StageS3bTest
  tools.tests.test_build_sysuisdk.FullPipelineWithS3bTest -v` → 14
  failures/errors: `module 'build_sysuisdk' has no attribute 'stage_s3b'`,
  missing `DEFAULT_STAGES` / `DEFAULT_UNSUPPORTEDAPPUSAGE_JAR` /
  `DEFAULT_ACONFIG_ANNOTATIONS_JAR` / `DEFAULT_KEEPANNO_ANNOTATIONS_JAR`,
  and `ALL_STAGES` ordering mismatch — as expected before implementation.
- GREEN: after implementing `stage_s3b` (validates BOTH targets read-only
  before mutating either; injects the exact 35 slices into both
  `android.jar` and `core-for-system-modules.jar`; normalizes android.jar
  manifest), CLI flags `--unsupportedappusage-jar`,
  `--aconfig-annotations-jar`, `--keepanno-annotations-jar`,
  `ALL_STAGES = ("s0","s1","s2","s3","s3b","s4")`, and
  `DEFAULT_STAGES = "s0,s1,s2,s3,s3b"` (s4 stays explicit):
  `Ran 14 tests ... OK`.
- Focused combined run: `python3 -m unittest
  tools.tests.test_patch_sdk_r8_library_classes
  tools.tests.test_build_sysuisdk -v` → `Ran 77 tests in 4.554s` → `OK`.
- Full Python suite (pre-mutation gate): `python3 -m unittest discover -s
  tools/tests -p 'test_*.py' -v` → `Ran 233 tests in 74.019s` → `OK`,
  exit status 0 (baseline 195; +38 Task 041 tests).

### Task 4: staging rebuild, determinism, and guarded apply

- **Python suite pre-mutation gate** (real output): `python3 -m unittest
  discover -s tools/tests -p 'test_*.py' -v` → `Ran 233 tests in 74.019s` →
  `OK`, exit status `0` (>= 195 baseline; logs `/tmp/task041-python-tests.log`,
  `/tmp/task041-python-tests.status`).
- **Two independent full staging SDKs** (`--stages s0,s1,s2,s3,s3b,s4`):
  `/tmp/task041-sdk-a` and `/tmp/task041-sdk-b`, both exit 0
  (`S3b: android.jar: injected 35 library classes`,
  `S3b: core-for-system-modules.jar: injected 35 library classes`).
- **A/B inventory comparison** (both target JARs): identical full
  entry-name→CRC inventories (android.jar 37397 entries,
  core-for-system-modules.jar 1824 entries). Diagnostic SHA-256:
  - android.jar: A `fc7eaf46fd45aa7fd9f63551b131deebe215906a954c69e8bdd773b19b97126f`,
    B `c4460982aa157a4b970ad7f05341f6b26ef96d198595f3fb8aa2033ae1f57a62`
  - core-for-system-modules.jar: A `a211c6ded3d29894ae5ae4c2fc6a0af84a6804feb81433098523ec8a9c1da357`,
    B `67320d0609b77e05861f2f37167f67dd869f3018f4911d08839129c2f7a770e0`
  Full-ZIP byte identity is not a Task 041 gate (S3's `jar uf` is
  inventory-reproducible only, as documented in the plan).
- **Exact source provenance**: 35/35 entries per target JAR are byte-identical
  to their approved source JAR entry; `AssumeTrueForR8.class` absent from both.
- **Pre-apply S5** (strict, `/tmp/task041-s5-before-apply.log`, exit 1):
  `android.jar: DIFF (staging=37397 live=37362 missing=0 extra=35 crc_diff=0)`,
  `core-for-system-modules.jar: DIFF (staging=1824 live=1789 missing=0
  extra=35 crc_diff=0)`; all other checks PASS. Both extra sets asserted
  equal to the exact approved 35-entry list.
- **Guarded apply** (exit 0, `/tmp/task041-sdk-apply.log`):
  `python3 tools/build_sysuisdk.py --apply --source /tmp/task041-sdk-a` →
  backups `android.jar.bak-20260821-011116`,
  `core-for-system-modules.jar.bak-20260821-011116`; `framework.aidl`
  identical (skip). No direct SDK file operation performed by the worker.
- **Post-apply strict S5** (exit 0, `/tmp/task041-s5-after-apply.log`):
  `S5: ALL PASS — staging is inventory-equivalent to the live SDK.`

### Task 5: debug packaging proof and exact fresh R8 delta

- **Debug hard gate** (serialized, `-Dorg.gradle.workers.max=4`):
  `./gradlew :app:checkDebugDuplicateClasses :app:assembleDebug
  --console=plain` → real exit status `0`, `BUILD SUCCESSFUL in 2m 39s`
  (216 actionable tasks: 209 executed, 7 up-to-date); logs
  `/tmp/task041-debug.log`, `/tmp/task041-debug.status`.
- **APK non-packaging proof**: `apkanalyzer dex packages --defined-only
  app/build/outputs/apk/debug/app-debug.apk` → asserted none of the 35
  bridged classes is defined in the debug APK → `BRIDGED=35 PACKAGED=0`
  (saved `/tmp/task041-debug-defined.txt`).
- **Fresh post-change R8** (`--rerun-tasks`, exit status `1` as required):
  sole remaining missing class:
  `com.android.aconfig.annotations.AssumeTrueForR8 (referenced from: boolean
  com.android.wifi.flags.FeatureFlags.androidVWifiApi() and 1 other context)`.
- **Exact set delta** (asserted against `/tmp/task041-missing-before.txt`):
  `BEFORE=7 AFTER=1 REMOVED=6 ADDED=0`; removed set = the six Task 041 refs
  (UnsupportedAppUsage, AconfigFlagAccessor, UsesReflection, IoUtils,
  NativeAllocationRegistry, ChunkHandler); added = ∅; remaining =
  `AssumeTrueForR8` only (Task 042).
- **Static scope checks** (exact immutable ranges; fixed 2026-08-21
  revision — the earlier text referenced `HEAD~2..HEAD`, a moving reference):
  - Code checkpoint range `a4876fe5..6be0f5bc` (patcher + pipeline commits):
    `git diff --name-only a4876fe5..6be0f5bc` → exactly the four tools files
    `tools/build_sysuisdk.py`, `tools/patch_sdk_r8_library_classes.py`,
    `tools/tests/test_build_sysuisdk.py`,
    `tools/tests/test_patch_sdk_r8_library_classes.py`.
  - Final reviewed range `a4876fe5..5fae790b` (through the evidence docs
    commit): `git diff --name-only a4876fe5..5fae790b` → all six allowed
    paths: the four tools files above plus
    `docs/issues/2026-08-21-r8-platform-build-classpath-closure.md` and
    `docs/orchestration/tasks/041-r8-platform-build-classpath-closure.md`.
  - Forbidden-path scan (pattern covering `src/`, `res*/`, `app/`,
    `SystemUI-*`, `libs/`, `gradle/`, `AGENTS.md`, `docs/adr/`,
    `docs/orchestration/CHARTER.md`) against both ranges: **no forbidden
    paths matched**.
  - No dontwarn/keep/implementation/compileOnly change;
    `git diff --check` exit 0.

## Conclusion

Task 041 acceptance is fully met: Python suite exit 0 (233 tests ≥ 195),
staging A/B target JAR inventory-identical, 35/35 source-byte-identical
entries per target JAR with `AssumeTrueForR8` absent, pre-apply S5 diff
exactly the 35 entries per JAR, guarded apply with timestamped backups,
post-apply strict S5 `ALL PASS`, debug assembly green with
`BRIDGED=35 PACKAGED=0`, and fresh R8 exactly 7→1 with zero additions.
The sole remaining ref (`AssumeTrueForR8`) is reserved for Task 042.
