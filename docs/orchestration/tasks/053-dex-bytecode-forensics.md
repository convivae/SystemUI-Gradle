# Task 053 — DEX Bytecode Forensics: Unscoped NLSUMI Factory Path

- Owner: worker
- Status: dispatched
- Depends on: none (pure read-only static analysis)

## Authority

You are authorized to perform **read-only** static forensics on the built APK DEX bytecode,
the KSP-generated Dagger sources in `build/`, and the AOSP kapt-generated reference source
inside `out/soong/.intermediates` (read-only). You may write **exactly one** report document
and scratch files under `/tmp/dex-audit/`.

You are NOT authorized to: edit any source/resource/gradle file, run any Gradle build,
run AOSP builds, touch any device/emulator (no adb at all), install anything, or commit.

## Allowed Paths

- Read: entire `/home/conv/myspace/SystemUI-Gradle` checkout (including `build/` outputs)
- Read: `/home/conv/myspace/aosp` (READ-ONLY; do not modify anything there)
- Read: `/home/conv/Android/Sdk/build-tools/37.0.0/dexdump` (tool)
- Write: `/tmp/dex-audit/**` (scratch)
- Write: `/home/conv/myspace/SystemUI-Gradle/docs/issues/2026-08-25-dex-bytecode-forensics.md` (final report, the ONLY repo file you may create)

## Forbidden Paths

- Any edit under `SystemUI-*/src`, `SystemUI-*/res*`, `app/src`, `libs/`, gradle files
- No Gradle/AOSP builds, no adb, no device interaction, no git commits
- No stubs, no resource fabrication

## Background (verified facts — do not re-verify, build on them)

Runtime instrumentation (tag `SysUIDup`) on the deployed debug APK proved:

1. Per process: ONE `SystemUIInitializer`, ONE root component, ONE sysui component,
   ONE `DumpManager` (identity hash observed: dm=50690569). Static caches work.
2. `NotificationLockscreenUserManagerImpl` (NLSUMI) is constructed **3 times in one process**
   (distinct instance hashes 231867728 / 202992725 / 221779837). First construction registers
   its dumpable name `NotificationLockscreenUserManagerImpl` successfully; the second
   construction hits `alreadyRegistered=true` and throws → crash loop.
3. The FIRST (successful) construction chain goes through the scoped path:
   `CustomizationProvider.attachInfo → ... → LegacyActivityStarterInternalImpl_Factory.get(:157)
   → DelegateFactory.get(:38) → DoubleCheck.get(:45) → DoubleCheck.getSynchronized(:54)
   → NLSUMI_Factory.get(:30/:131)`.
4. The CRASHING construction chain has **no DelegateFactory/DoubleCheck frames**:
   `SystemUIService.onCreate(:80) → startServicesIfNeeded → startStartable(:443)
   → ScreenDecorations_Factory.get → PrivacyDotViewControllerModule.controller
   → PrivacyDotViewControllerImpl_Factory_Impl.create(:36)
   → PrivacyDotViewControllerImpl_Factory.get(:61) → ShadeInteractorImpl_Factory.get(:84)
   → UserSwitcherInteractor_Factory.get(:125) → ActivityStarterImpl_Factory.get(:52)
   → ActivityStarterImpl.<init>(:48) → LegacyActivityStarterInternalImpl_Factory.get(:157/:33)
   → NLSUMI_Factory.get(:30/:131)` (bare factory).
5. The crash chain passes through `ScreenDecorations` (a Startable), i.e. the path
   `controllerProvider2` (DoubleCheck of `PrivacyDotViewControllerModule_ControllerFactory`)
   → module `@Provides` method `controller(...)` → `factoryProvider110`
   (`PrivacyDotViewControllerImpl_Factory_Impl.createFactoryProvider(...)`).
6. The deployed APK is byte-identical to local `app/build/outputs/apk/debug/app-debug.apk`
   (SHA-256 `0fddcf9437470d55bc77a46821b232c7d29b1153df10716b12cf71dc9115cfdd`).
   A global duplicate-class audit across all 24 DEX files found ZERO duplicate classes.
   So the deployed bytes = local build output; no device pull needed (adb forbidden anyway).
7. The Dagger component classes live in `classes4.dex` (101 `DaggerReferenceGlobalRootComponent*`
   classes). `classes4.dex` is already extracted at `/tmp/dex-audit/classes4.dex` and a full
   dexdump text is at `/tmp/dex-audit/classes4.dexdump.txt` (363,181 lines).
8. Key generated-source locations (debug KSP output,
   `SystemUI-core/build/generated/ksp/debug/java/com/android/systemui/dagger/DaggerReferenceGlobalRootComponent.java`):
   - NLSUMI: `NotificationLockscreenUserManagerImpl_Factory.create(` appears exactly ONCE at ~line 18032,
     wrapped by `DoubleCheck.provider(...)` and bound via `DelegateFactory.setDelegate`.
   - `LegacyActivityStarterInternalImpl_Factory.create(` exactly ONCE at ~line 18132, wrapped in
     `DoubleCheck.provider(...)`; its lockscreen-user-manager arg is the field
     `notificationLockscreenUserManagerImplProvider` (a `DelegateFactory`).
   - `privacyDotViewControllerImplProvider` ~line 18211 (passes `((Provider)(shadeInteractorImplProvider))`);
     `factoryProvider110` ~line 18212 (`PrivacyDotViewControllerImpl_Factory_Impl.createFactoryProvider`);
     `controllerProvider2` ~line 18213 (`DoubleCheck.provider(PrivacyDotViewControllerModule_ControllerFactory...)`);
     `screenDecorationsProvider` ~line 18362 (DoubleCheck of `ScreenDecorations_Factory`).
   - `userSwitcherInteractorProvider` field ~line 14927 (DelegateFactory), setDelegate ~18087;
     `activityStarterImplProvider` ~14820 (DelegateFactory), setDelegate ~18133.
9. Architect's preliminary dex scan (verify, don't trust blindly):
   `NLSUMI_Factory.create(` invoke-static appears once in classes4.dex at dex offset `0a2e88`,
   inside what a naive scan attributed to method `initialize72` of
   `DaggerReferenceGlobalRootComponent$ReferenceSysUIComponentImpl`; the
   `LegacyActivityStarterInternalImpl_Factory.create(` call at `0a3cf2` was attributed to
   `initialize74`. NOTE: that attribution used a fragile "last `name:` line" heuristic over
   dexdump text and MUST be redone with proper method-block parsing.

## Mission

Produce a decisive, evidence-backed answer to: **where does the second, unscoped
NLSUMI construction path come from?** Steps:

1. **Bytecode ↔ source correspondence check.** In `/tmp/dex-audit/classes4.dexdump.txt`
   (regenerate with dexdump if needed), parse method blocks properly (dexdump prints
   `Class descriptor`, then method headers with `name :` + code blocks). For
   `DaggerReferenceGlobalRootComponent$ReferenceSysUIComponentImpl`, locate every
   `invoke-static ... _Factory;.create` call for these factories and record the containing
   method name + dex offset:
   `NotificationLockscreenUserManagerImpl_Factory`, `LegacyActivityStarterInternalImpl_Factory`,
   `ShadeInteractorImpl_Factory`, `UserSwitcherInteractor_Factory`, `ActivityStarterImpl_Factory`,
   `PrivacyDotViewControllerImpl_Factory`, `PrivacyDotViewControllerImpl_Factory_Impl`,
   `ScreenDecorations_Factory`.
   Also locate every `invoke-static Ldagger/internal/DoubleCheck;.provider` and
   `DelegateFactory;.setDelegate` in the same initialize methods.
   Compare counts/structure against the on-disk KSP debug source. Verdict A:
   does the DEX bytecode match the on-disk generated source (i.e. no stale-build mismatch)?

2. **Trace `factoryProvider110` / `PrivacyDotViewControllerImpl_Factory_Impl` in bytecode.**
   Disassemble `PrivacyDotViewControllerImpl_Factory_Impl` (especially `createFactoryProvider`
   and `create`) and the bytecode that builds `factoryProvider110` in the component impl.
   Determine exactly which Provider instances are passed as its constructor args
   (fields like `shadeInteractorImplProvider`/DelegateFactory vs freshly `new`'d raw factories).
   This is the prime suspect for the unscoped subtree.

3. **kapt vs KSP reference comparison.** The AOSP Soong build generates the same component
   with kapt. Extract
   `/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI/SystemUI-core/android_common/kapt/kapt-sources.jar`
   → `com/android/systemui/dagger/DaggerReferenceGlobalRootComponent.java` (2.4 MB, extract to /tmp).
   Find how IT wires: the NLSUMI provider, `LegacyActivityStarterInternalImpl` provider,
   the PrivacyDotViewController controller/factoryProvider chain (names like
   `factoryProvider110` may differ — search by factory class names), and where
   `DelegateFactory.setDelegate` calls happen. Verdict B: does the kapt-generated wiring
   differ from KSP's at the suspect site (this is the KSP-divergence hypothesis test)?

4. **Release variant sanity check.** Compare the debug KSP output against
   `SystemUI-core/build/generated/ksp/release/java/.../DaggerReferenceGlobalRootComponent.java`
   at the same sites (release uses different line numbers, ~-11). Verdict C: same structure?

5. Write the report (see Acceptance).

## Acceptance

Command-level evidence and report. The report file
`docs/issues/2026-08-25-dex-bytecode-forensics.md` must contain:

- A table: for each of the 8 factories above — containing method name, dex offset,
  arg count, and whether wrapped by `DoubleCheck.provider`/`DelegateFactory.setDelegate`
  in bytecode, with the raw dexdump lines quoted (a few lines each, with offsets).
- Verdict A (bytecode matches on-disk KSP debug source? yes/no + evidence).
- The exact mechanism of `factoryProvider110`: quoted dexdump of the component-impl code that
  constructs it and of `PrivacyDotViewControllerImpl_Factory_Impl.createFactoryProvider`,
  identifying the arg providers by field name (resolve `iget`/`sget` field indices to names
  via the class's field list in the dexdump).
- Verdict B (kapt wiring identical/divergent + quoted kapt source lines for the same chain).
- Verdict C (debug vs release KSP structure identical? yes/no).
- Root-cause hypothesis: one paragraph, evidence-linked, naming the exact source line(s) or
  build mechanism responsible for the unscoped path. If evidence is insufficient for a
  conclusion, say so explicitly and list the missing piece — do NOT guess.

Verification command the architect will re-run:
`grep -n "Verdict" docs/issues/2026-08-25-dex-bytecode-forensics.md` must show A, B, C verdicts;
and quoted dex offsets must be reproducible from `/tmp/dex-audit/classes4.dex`.

## Reports To

Chief architect (main checkout session). On completion, report:
`COMPLETE` + report path + the three verdicts + one-line root-cause hypothesis.
On red-line (e.g. you believe you need a build/device/source edit): HALT and report `BLOCKED: <reason>`.
