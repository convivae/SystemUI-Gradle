# 2026-08-21 — R8 aconfig assumption closure (Task 042)

| Field | Value |
|---|---|
| Status | **Rejected before implementation**; retained as a historical proposal and must not be dispatched |
| Baseline | main `1f462795`; fresh R8 exit 1 with exactly one missing ref |
| Target | Historical proposal only; replacement mechanism intentionally undecided |
| Superseded by | `docs/superpowers/specs/2026-08-21-gradle-native-systemui-build-design.md` |

> This proposal over-constrained Gradle by requiring a byte-exact complete Soong consumer-rule
> import and a dedicated S3c stage. The user approved a new AGP-native functional-parity
> direction on 2026-08-21. No Task 042 implementation or live-SDK mutation occurred.

## Background

Task 041 closed the six platform/build library roots through declarative SysUISdk stage `S3b`.
The sole remaining R8 missing class is:

```text
com.android.aconfig.annotations.AssumeTrueForR8
```

This is not merely a warning-only annotation. The real AOSP module
`aconfig-annotations-lib` exports `frameworks/libs/modules-utils/java/aconfig_proguard.flags`.
Soong propagates that file into the final SystemUI R8 configuration. Its two
`AssumeTrueForR8` rules are:

```proguard
-assumevalues class * {
    @com.android.aconfig.annotations.AssumeTrueForR8 boolean *(...) return true;
}
-assumenosideeffects class * {
    @com.android.aconfig.annotations.AssumeTrueForR8 boolean *(...) return true;
}
```

Supplying only the class would close the missing-class diagnostic but would not reproduce the
Soong optimization contract. Task 042 must therefore deliver both channels:

1. the real annotation class as an R8 **library class**, not an APK program class; and
2. the byte-exact exported AOSP rule file as an app-level R8 input.

## Primary-source evidence

### Annotation owner and bytes

- Source:
  `frameworks/libs/modules-utils/java/com/android/aconfig/annotations/AssumeTrueForR8.java`
- Soong module: `aconfig-annotations-lib` in
  `frameworks/libs/modules-utils/java/Android.bp`
- Real source artifact:
  `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/libs/modules-utils/java/aconfig-annotations-lib/linux_glibc_common/javac/aconfig-annotations-lib.jar`
- Artifact SHA-256:
  `ef431f923f6925ec835282afb3ee62c909987dd2f053dbcdccc1f7294923f551`
- Exact entry:
  `com/android/aconfig/annotations/AssumeTrueForR8.class`
- Entry size / SHA-256: `413` bytes /
  `d4602718f42729ea476648dc391f88db7e9a1b21a344c566eadb6077e4691468`
- `javap -v` confirms `RetentionPolicy.CLASS`, target `METHOD`, no methods or fields.

### Exported rule owner and propagation

- Source: `frameworks/libs/modules-utils/java/aconfig_proguard.flags`
- Size / SHA-256: `778` bytes /
  `b6a85445ea517fc4861c0a5d68ea8af8d1b6b4f2e7a4a569c7830891e73b2f01`
- `aconfig-annotations-lib` declares both `proguard_flags_files` and
  `export_proguard_flags_files: true`.
- `java_aconfig_library.go` adds `aconfig-annotations-lib` as a shared library for generated
  flag code.
- Soong `AndroidApp.proguardBuildActions` consumes direct dependencies'
  `UnconditionallyExportedProguardFlags`.
- The built AOSP SystemUI final configuration
  `out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI/android_common/proguard_configuration`
  contains the complete source rule file byte-for-byte as one section.
- The tracked `libs/wifi-flags.jar` has 19 `AssumeTrueForR8` and 6
  `AssumeFalseForR8` method annotations, confirming these rules act on real program input.

## Approved design proposed for exact-brief approval

### S3c library-class stage

Add `tools/patch_sdk_aconfig_r8_annotation.py`, reusing Task 041's proven generic
`ClassSlice` / validate / atomic patch engine, but declaring exactly one immutable entry:

```text
com/android/aconfig/annotations/AssumeTrueForR8.class
```

`tools/build_sysuisdk.py` gains independent stage `S3c`, ordered after `S3b` and before `S4`.
It must read-only validate both `android.jar` and `core-for-system-modules.jar` before mutating
either, reject differing existing bytes, use `.bak-preaconfigr8`, remain idempotent, and become
part of the default staging stage list. Live SDK mutation remains exclusively guarded
`build_sysuisdk.py --apply --source <staging>`.

### Exported AOSP R8 rules

Copy the complete 778-byte AOSP `aconfig_proguard.flags` byte-for-byte to
`app/aconfig_proguard.flags`; do not edit, subset, or hand-rewrite it. Add that file to both
existing `proguardFiles(...)` lists in `app/build.gradle.kts`. This mirrors Soong's exported
consumer-rule edge. It is not a new keep workaround and contains no `dontwarn`.

The complete file is required rather than a hand-selected `AssumeTrueForR8` fragment because
Soong exports the file as a unit; it also preserves the paired `AssumeFalseForR8` and
`VisibleForTesting` behavior already present in AOSP's effective SystemUI configuration.
Only `AssumeTrueForR8.class` is added to SysUISdk in this task: the observed classpath closure
is one ref, and prefix/package expansion is forbidden.

## Implementation steps

1. Capture fresh exact one-ref R8 baseline and real exit 1.
2. Add focused failing tests for the one-entry patcher and `S3c` pipeline integration.
3. Implement the exact patcher and pipeline stage; run focused and full Python suites.
4. Add a failing provenance/config test for the committed AOSP rules and Gradle wiring.
5. Import the byte-exact rule file and wire both build types.
6. Build two independent full staging SDKs (`s0,s1,s2,s3,s3b,s3c,s4`) and compare complete
   target `name→CRC` inventories.
7. Require the new class to be source-identical in both targets; Task 041's 35 entries must
   remain unchanged.
8. Run pre-apply S5 (only one new entry per target may differ), guarded `--apply`, then strict
   post-apply S5 `ALL PASS`.
9. Run serialized debug duplicate-class + assemble hard gate; require the 36 bridged classes
   to remain absent from APK defined classes (`BRIDGED=36 PACKAGED=0`).
10. Run fresh release R8 with `set -o pipefail`, `tee`, and preserved Gradle exit. Require
    success and zero missing refs.
11. Verify the generated release `configuration.txt` contains both effective
    `AssumeTrueForR8` return-true rules, and the committed rule file remains byte-identical to
    AOSP source.
12. Record exact evidence, focused English commits, and clean scope; worker never pushes.

## Error-count evolution

| Point | R8 missing refs | Expected Gradle status |
|---|---:|---|
| Task 041 main fresh baseline | 1 | exit 1, missing class |
| Task 042 final | 0 | exit 0, `BUILD SUCCESSFUL` |

The transition must be exact. Any new missing ref, different failure, rule parse warning, or
missing effective assumption rule is a REDLINE.

## Red lines

- No runtime `implementation`, new `compileOnly`, local JAR/AAR, or Maven coordinate.
- No `dontwarn`, broad keep, disabled shrink/check, or source exclusion.
- No SystemUI/AOSP source or resource modification.
- No direct live-SDK write; staging then guarded `--apply` only.
- No package-prefix expansion or injection beyond the exact one class.
- No hand-edited/subset rule file; committed bytes must match AOSP source exactly.
- Existing target class with bytes different from the approved source is a hard stop.
- Debug regression, bridged class in APK, or release R8 not reaching zero is a hard stop.

## Historical outcome

1. The user rejected the byte/configuration-parity premise before implementation.
2. No Worker was dispatched and no build, repository implementation, or live SysUISdk mutation
   occurred from this proposal.
3. The one remaining reference will be reconsidered only after the Gradle-native architecture
   spec and read-only current-state audit are approved.
