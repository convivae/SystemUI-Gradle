# Port AOSP SystemUI Service to Gradle Build

**Status:** Design proposal — not yet executed
**Author:** Cursor Agent (in collaboration with user)
**Created:** 2026-07-16
**Supersedes:** v2 dual-build skeleton's placeholder `SystemUIService` stub

## 1. Background

The v2 dual-build skeleton (commits `0632789`..`5a34d04`) delivered a buildable
but empty `:app` module: `SystemUIService` is a 14-line stub with no
`@Inject`, no Dagger, no `CoreStartable` registration. The real AOSP
`SystemUIService` is 140 LoC but **depends on a Dagger graph with hundreds of
bindings**, which itself depends on the entire SystemUI core.

This plan defines how to incrementally port the real `SystemUIService` and
its Dagger graph while keeping `./gradlew :app:assembleDebug` green at every
milestone.

## 2. Scope and Non-Goals

### In scope
- Real `SystemUIService` (140 LoC) and `SystemUIApplication` (501 LoC)
- Real `SystemUIInitializer` and `SystemUIAppComponentFactoryBase`
- Dagger graph: `ReferenceGlobalRootComponent` + `ReferenceSysUIComponent`
  + their ~24 supporting `@Module`s under `dagger/`
- `CoreStartable` services that the real `startSystemUserServicesIfNeeded()`
  iterates
- New prebuilt-JAR module for `WindowManager-Shell` (currently missing)
- Migration of `dependency/*.java` legacy DI bridge

### Out of scope (later milestones / separate plans)
- Keyguard / status bar UI / quick settings (separate plan)
- SystemUI tests / `multivalentTests/`
- Compose prebuilts (separate plan)
- Bluetooth / NFC / other domain services referenced from `manifest` but
  not exercised by `SystemUIService`
- WMShell source — we keep it as a prebuilt JAR

## 3. AOSP Scope (Confirmed via Probe)

| Item | LoC / file count | Source path |
|------|------------------|-------------|
| `SystemUIService.java` | 140 LoC | `frameworks/base/packages/SystemUI/src/com/android/systemui/SystemUIService.java` |
| `SystemUIApplication.java` | 501 LoC | `frameworks/base/packages/SystemUI/src/com/android/systemui/SystemUIApplication.java` |
| `CoreStartable.java` | 81 LoC | `frameworks/base/packages/SystemUI/src/com/android/systemui/CoreStartable.java` |
| Dagger root files | 24 files | `frameworks/base/packages/SystemUI/src/com/android/systemui/dagger/` |
| `dependency/*` legacy bridge | ~2500 LoC | `frameworks/base/packages/SystemUI/src/com/android/systemui/Dependency.java` |
| AOSP `src/` total | 4183 files | — |
| `WindowManager-Shell` | 498 files (we use prebuilt) | `frameworks/base/libs/WindowManager/Shell/` |

**Hidden-API surface already satisfied** by `libs/framework.jar` (Task 2
delivered): `com.android.internal.*` resolved at compile time.

**New prebuilt required**: `WindowManager-Shell.jar`
(`aosp/out/soong/.intermediates/frameworks/base/libs/WindowManager/Shell/WindowManager-Shell/android_common/turbine-combined/WindowManager-Shell.jar`).

## 4. Sequencing (Six Milestones)

Each milestone ends with `./gradlew :app:assembleDebug` green. **No
milestone is merged unless its target file is on a device / emulator and
`am startservice -n com.android.systemui/.SystemUIService` succeeds.**

### Milestone 1: Add `WindowManager-Shell` prebuilt module
**Goal:** `:SystemUI-wm-shell` library module wraps `WindowManager-Shell.jar`.

**Files:**
- `tools/extract_prebuilts.sh`: add `copy_jar WindowManager-Shell`
- `libs/prebuilts/WindowManager-Shell.jar` (commit)
- `SystemUI-wm-shell/build.gradle.kts` (new module)
- `SystemUI-wm-shell/src/main/AndroidManifest.xml`
- `settings.gradle.kts`: `include(":SystemUI-wm-shell")`
- `Android.bp`: `java_import` for WindowManager-Shell

**Risk:** WMShell has Kotlin code → module needs `org.jetbrains.kotlin.android`
plugin. Verify Kotlin 2.3.21 against AOSP Kotlin 1.x APIs used in WMShell.

**Acceptance:** `:SystemUI-wm-shell:assembleDebug` PASS.

### Milestone 2: Port `CoreStartable` interface + minimal `SystemUIService`
**Goal:** Real `SystemUIService` running with empty `CoreStartable` set.

**Files:**
- `app/src/main/java/com/android/systemui/SystemUIService.java` (replace stub)
- `app/src/main/java/com/android/systemui/SystemUIApplication.java` (replace stub, but **only** the `@Inject` constructors — keep `startSystemUserServicesIfNeeded()` iterating over a hardcoded empty array for now)
- `app/src/main/java/com/android/systemui/CoreStartable.java` (port from AOSP)
- `app/src/main/java/com/android/systemui/SystemUIInitializer.java` (port from AOSP)
- `app/src/main/java/com/android/systemui/SystemUIAppComponentFactoryBase.kt` (port from AOSP)
- Delete our 14-line stub

**Strategy:** Do **not** wire Dagger yet. `@Inject` constructors will resolve
to null at this stage — replace with `@SuppressWarnings("nullness")` and
explicit `null` arguments in `new SystemUIService(null, null, ...)` for
boot. Add a TODO marker to flip to real injection in M4.

**Acceptance:** APK installs, `am startservice` does not crash with
NPE inside our `SystemUIService` constructor.

### Milestone 3: Port `dagger/` Dagger root + global module
**Goal:** `ReferenceGlobalRootComponent` + `GlobalModule` compile, generate
Dagger factories, expose `SysUIComponent.Builder`.

**Files:**
- `app/src/main/java/com/android/systemui/dagger/` (24 files)
- `app/build.gradle.kts`: add `kapt`/`ksp` plugin for Dagger code generation
- Add Dagger 2.51 to version catalog (we have `dagger = 2.51.1` already)

**Strategy:** Use Dagger annotation processing. KSP > kapt for Kotlin
files in `dagger/`. Generate `DaggerReferenceGlobalRootComponent.java` and
`DaggerReferenceSysUIComponent.java` at compile time.

**Risk:** AOSP `dagger/` uses `dagger.android` + `dagger.spi`. We need to
add the right artifacts to version catalog.

**Acceptance:** `:app:compileDebugJavaWithJavac` produces Dagger-generated
factories; `DaggerReferenceGlobalRootComponent` is reachable in `:app` test.

### Milestone 4: Wire real Dagger injection into `SystemUIService`
**Goal:** Constructor `@Inject` resolves to real objects.

**Files:**
- `app/src/main/java/com/android/systemui/SystemUIInitializer.java` (extend
  with `getGlobalRootComponentBuilder()` returning the AOSP builder)
- `app/src/main/AndroidManifest.xml`: switch to
  `appfactory=com.android.systemui.SystemUIAppComponentFactoryBase`

**Strategy:** Mirror AOSP `services/java/com/android/systemui/SystemUIApplication`
boot sequence. `SystemUIApplication.onCreate()` builds the Dagger graph
lazily; `SystemUIService.onCreate()` triggers it.

**Acceptance:** APK installs, logcat shows Dagger-init messages from
`SystemUIService`.

### Milestone 5: Port `SystemUICoreStartableModule` registrations
**Goal:** `startSystemUserServicesIfNeeded()` iterates a real `Map<Class<?>, Provider<CoreStartable>>`.

**Files:**
- `app/src/main/java/com/android/systemui/dagger/SystemUICoreStartableModule.kt`
- AOSP `CoreStartable` providers — start with the 3 that are JVM-only:
  `BootCompleteCacheImpl`, `ConfigurationForwarder`, `PowerNotificationWarningsModule`
- Port those 3 files from AOSP

**Strategy:** Don't port every `*Startable`; port the minimal set that
allows the service to start cleanly. Each subsystem (keyguard, statusbar,
qs, etc.) gets its own milestone 5.x.

**Acceptance:** `dumpsys activity service com.android.systemui` shows all
registered `CoreStartable`s with names.

### Milestone 6: Remove legacy `Dependency.java`
**Goal:** No `static Dependency` holder; everything goes through Dagger.

**Files:**
- Refactor every consumer of `Dependency.get(XXX)` to use `@Inject XXX` instead.

**Risk:** This is invasive — many subsystems still use `Dependency.get`. May
need to defer to milestone 5.x per subsystem.

**Acceptance:** No `import com.android.systemui.Dependency;` in `:app/src/main/`.

## 5. Risks (Updated)

### R1 (HIGH): WMShell API drift
WMShell internals change between AOSP versions. Our `:SystemUI-wm-shell`
prebuilt must come from the **same AOSP tree** we built `framework.jar` and
the 4 prebuilt JARs from. Mitigation: `extract_prebuilts.sh` enforces single
`AOSP_OUT` source.

### R2 (HIGH): `Dependency.java` blast radius
Touching it requires coordinated changes across hundreds of files. Mitigation:
Milestone 6 is **purely optional** for v1 skeleton; v1 ships with the legacy
bridge still in place.

### R3 (MEDIUM): Dagger generation cost
Dagger's annotation processor is slow (~30s on AOSP scale). Mitigation: use
KSP if possible; cache generated sources between builds.

### R4 (MEDIUM): `ResourceLoadingException`
AOSP `res/` contains overlay resources (`res-product/`, `res-keyguard/`)
that the gradle build doesn't include yet. Mitigation: copy them into
`app/src/main/res-keyguard/` (existing path from v1) and `app/src/main/res-product/`.

### R5 (LOW): Kotlin compiler version mismatch
WMShell uses Kotlin features (value classes, context receivers possibly) that
may need a Kotlin compiler matching AOSP's. Mitigation: pin Kotlin compiler
to a version known to work with the AOSP tree we built from.

## 6. Tests

Each milestone has a smoke test:

| Milestone | Test command | Pass criterion |
|-----------|--------------|----------------|
| M1 | `./gradlew :SystemUI-wm-shell:assembleDebug` | BUILD SUCCESSFUL |
| M2 | `adb shell am startservice -n com.android.systemui/.SystemUIService` | No crash in logcat |
| M3 | `./gradlew :app:compileDebugJavaWithDagger` (custom task) | Factory generated |
| M4 | `adb logcat -d \| grep "DaggerReferenceGlobal"` | Graph init logged |
| M5 | `adb shell dumpsys activity service com.android.systemui` | Lists `CoreStartable`s |
| M6 | `grep -r "import com.android.systemui.Dependency" app/src/` | Empty result |

Plus the existing CI: `./gradlew :app:assembleDebug` must remain green at
every commit.

## 7. Estimated Effort (LoC added to repo, per milestone)

| Milestone | Files | LoC |
|-----------|-------|-----|
| M1 | 5 | ~50 |
| M2 | 4 | ~750 |
| M3 | 25 | ~600 |
| M4 | 2 | ~100 |
| M5 | 4 | ~200 |
| M6 | TBD | ~300 (excluding consumer refactors) |

## 8. Open Questions for User

1. **Q1:** Is v1 (Milestones 1–5) sufficient to ship, or do we need M6
   (remove `Dependency.java`) before going to AOSP tree build?
2. **Q2:** Should we wire `ksp` for Kotlin Dagger generation, or stick
   with `kapt` (AOSP uses kapt)?
3. **Q3:** M5 enumerates 3 `CoreStartable`s. Should we port more subsystems
   in this same plan, or split into subsystem-specific plans?
4. **Q4:** Is WMShell prebuilt acceptable, or should we add a "source
   sync" milestone that copies WMShell source into a new `:SystemUI-wm-shell`
   Gradle module? (The prebuilt is much faster to deliver but couples
   our release cadence to AOSP's.)