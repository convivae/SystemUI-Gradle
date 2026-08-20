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

Not run yet. This section must contain only real worker and architect command output after
implementation; planning does not imply build success.
