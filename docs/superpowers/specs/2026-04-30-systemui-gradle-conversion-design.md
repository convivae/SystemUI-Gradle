# SystemUI Gradle Conversion Design

## Goal

Convert AOSP SystemUI (API 37) from Android.bp (Soong) to a multi-module Gradle build that:
- Provides full IDE support (code completion, navigation, refactoring) in Android Studio
- Can compile and deploy the SystemUI APK via Gradle
- Preserves the original AOSP source locations (no file copying)
- Does not interfere with the original AOSP build system

## Source Locations

- **AOSP SystemUI**: `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI`
- **AOSP frameworks/libs/systemui**: `/home/conv/myspace/aosp/frameworks/libs/systemui`
- **Gradle project**: `/home/conv/myspace/SystemUI-Gradle`
- **AOSP out/ directory**: User-provided path (configurable via `local.properties`)

## Module Structure

### 10 Gradle Modules

| Gradle Module | AOSP Module(s) | Type | Source Path |
|---|---|---|---|
| `:app` | SystemUI-core + SystemUI-res | com.android.application | `aosp/.../SystemUI/src`, `aosp/.../SystemUI/res`, `aosp/.../SystemUI/res-keyguard`, `aosp/.../SystemUI/res-product`, `aosp/.../SystemUI/src-release` |
| `:shared` | SystemUISharedLib | com.android.library | `aosp/.../SystemUI/shared/src`, `aosp/.../SystemUI/shared/res` |
| `:plugin` | SystemUIPluginLib | com.android.library | `aosp/.../SystemUI/plugin/src`, `aosp/.../SystemUI/plugin/bcsmartspace/src` |
| `:plugin-core` | PluginCoreLib + PluginAnnotationLib | java-library | `aosp/.../SystemUI/plugin_core/src` |
| `:unfold` | SystemUIUnfoldLib | com.android.library | `aosp/.../SystemUI/unfold/src` |
| `:customization` | SystemUICustomizationLib | com.android.library | `aosp/.../SystemUI/customization/src`, `aosp/.../SystemUI/customization/res` |
| `:animation` | PlatformAnimationLib + SystemUIShaderLib | com.android.library | `aosp/.../SystemUI/animation/src`, `aosp/.../SystemUI/animation/res` |
| `:common` | SystemUICommon | java-library | `aosp/.../SystemUI/common/src` |
| `:utils` | SystemUI-shared-utils | java-library | `aosp/.../SystemUI/utils/src` |
| `:log` | SystemUILogLib | java-library | `aosp/.../SystemUI/log/src` |

### Dependency Graph

```
:app
  ├── :shared
  │     ├── :plugin
  │     │     ├── :plugin-core
  │     │     ├── :common → :utils
  │     │     └── :log → :common
  │     ├── :unfold
  │     ├── :animation
  │     └── :common
  ├── :customization
  │     ├── :plugin
  │     ├── :unfold
  │     └── :animation
  ├── :animation
  ├── :common
  └── :log
```

### Module Details

#### `:plugin-core` (java-library)
- AOSP sources: `plugin_core/src/**/*.{java,kt}`
- Excludes annotation sources (handled separately)
- Exports `PluginAnnotationLib` annotations
- No Android dependencies (pure Java/Kotlin library)
- Java version: 1.8

#### `:plugin` (com.android.library)
- AOSP sources: `plugin/src/**/*.{java,kt}`, `plugin/bcsmartspace/src/**/*.{java,kt}`
- Excludes `PluginProtectorStub.kt`
- Depends on: `:plugin-core`, `:common`, `:log`
- Uses PluginAnnotationProcessor (annotation processing)
- AndroidX dependencies: annotation, constraintlayout, compose-ui, compose-runtime

#### `:unfold` (com.android.library)
- AOSP sources: `unfold/src/**/*.{java,kt,aidl}`
- Depends on: androidx.dynamicanimation, dagger2
- minSdkVersion: current

#### `:common` (java-library)
- AOSP sources: `common/src/**/*.{java,kt}`
- Depends on: `:utils`
- No Android dependencies

#### `:utils` (java-library)
- AOSP sources: `utils/src/**/*.{java,kt}`
- Depends on: kotlin-stdlib, kotlinx-coroutines
- No Android dependencies

#### `:log` (java-library)
- AOSP sources: `log/src/**/*.{java,kt}`
- Depends on: `:common`, error_prone_annotations
- No Android dependencies

#### `:animation` (com.android.library)
- AOSP sources: `animation/src/**/*.{java,kt}`, `animation/res`
- Excludes surfaceeffects sources (separate SystemUIShaderLib — included in same module)
- Depends on: WindowManager-Shell-shared (prebuilt), animationlib (prebuilt), flags lib
- Resources: `animation/res`

#### `:shared` (com.android.library)
- AOSP sources: `shared/src/**/*.{java,kt,aidl}`
- Resources: `shared/res`
- Depends on: `:plugin`, `:unfold`, `:animation`, `:common`
- Prebuilt deps: WindowManager-Shell-shared, tracinglib-platform, iconloader_base, msdl, view_capture
- AndroidX: dynamicanimation, concurrent-futures, lifecycle, recyclerview

#### `:customization` (com.android.library)
- AOSP sources: `customization/src/**/*.{java,kt,aidl}`
- Resources: `customization/res`
- Depends on: `:plugin`, `:unfold`, `:animation`
- Prebuilt deps: monet

#### `:app` (com.android.application)
- AOSP sources: `src/**/*.{java,kt,proto}`, `src-release/**/*.{java,kt}`
- AIDL: `src/**/I*.aidl`
- Resources: `res`, `res-keyguard`, `res-product`
- Manifest: `AndroidManifest.xml`
- Depends on: all other modules
- Prebuilt deps: WifiTrackerLib, SettingsLib, WindowManager-Shell, compilelib, iconloader_base, etc.
- Maven deps: AndroidX (core, viewpager2, recyclerview, preference, compose), Dagger2, Room, Kotlin coroutines
- Annotation processors: dagger2-compiler, room-compiler-plugin
- ProGuard: `proguard.flags`, `proguard_common.flags`, `proguard_kotlin.flags`

## External Dependencies Strategy

### Category 1: Maven dependencies (from Google/Maven Central)
Standard AndroidX, Kotlin, Dagger, Compose libraries — resolved normally via Gradle.

Key libraries:
- `androidx.core:core-ktx`
- `androidx.compose.runtime:runtime`
- `androidx.compose.material3:material3`
- `com.google.dagger:dagger`
- `org.jetbrains.kotlinx:kotlinx-coroutines-android`
- `androidx.room:room-runtime`
- `androidx.recyclerview:recyclerview`
- `androidx.preference:preference`

### Category 2: AOSP prebuilt JARs/AARs (from `out/` directory)
These are AOSP-specific libraries not available in Maven. They will be placed in a `libs/` directory and referenced as `fileTree` dependencies.

Libraries to extract from AOSP build:
- `framework.jar` — Android framework APIs (compileOnly)
- `SystemUI-framework.jar` — SystemUI-specific framework APIs (compileOnly)
- `WindowManager-Shell.jar` / `WindowManager-Shell.aar`
- `WindowManager-Shell-shared.jar` / `.aar`
- `SettingsLib.aar`
- `WifiTrackerLib.aar`
- `compilelib.jar` (frameworks/libs/systemui:compilelib)
- `animationlib.jar` (frameworks/libs/systemui:animationlib)
- `iconloader_base.jar` (frameworks/libs/systemui:iconloader_base)
- `tracinglib-platform.jar`
- `contextualeducationlib.jar`
- `motion_tool_lib.jar`
- `msdl.jar`
- `view_capture.jar`
- `monet.jar`
- `com_android_systemui_shared_flags.jar`
- `PlatformComposeCore.aar`
- `PlatformComposeSceneTransitionLayout.aar`

### Category 3: compileOnly framework APIs
These are the core Android framework JARs that SystemUI compiles against but doesn't bundle (they exist on the device):
- `framework.jar` — core Android APIs
- `SystemUI-framework.jar` — @SystemApi APIs used by SystemUI

Configuration: User specifies `aosp.out.dir` in `local.properties`. A helper script extracts the needed JARs from the AOSP build output.

## Build Configuration

### Gradle Version & Plugins
- Gradle: 8.7+
- AGP: 8.5+
- Kotlin: 1.9.x
- Compose compiler: matched to Kotlin version

### `local.properties` (user-specific, not committed)
```properties
sdk.dir=/path/to/Android/Sdk
aosp.dir=/home/conv/myspace/aosp
aosp.out.dir=/home/conv/myspace/aosp/out/target/product/<device>
```

### Source Set Configuration
Each module's `build.gradle.kts` references AOSP source paths via `srcDirs`:

```kotlin
sourceSets {
    main {
        java.srcDirs(
            "${aospDir}/frameworks/base/packages/SystemUI/common/src"
        )
    }
}
```

No files are copied — Gradle reads directly from the AOSP tree.

### AIDL Support
The `:app` and `:shared` modules use AIDL files. AGP's built-in AIDL support handles this:
```kotlin
buildFeatures {
    aidl = true
}
```
Additional AIDL source dirs configured for WindowManager-Shell AIDLs.

### Proto Support
The `:app` module includes `.proto` files. AGP's protobuf plugin handles code generation:
```kotlin
plugins {
    id("com.google.protobuf")
}
protobuf {
    protoc { artifact = "com.google.protobuf:protoc:3.21.12" }
    generateProtoTasks { }
}
```

### Resource Configuration
The `:app` module uses three resource directories:
```kotlin
android {
    sourceSets {
        main {
            res.srcDirs(
                "${aospDir}/frameworks/base/packages/SystemUI/res",
                "${aospDir}/frameworks/base/packages/SystemUI/res-keyguard",
                "${aospDir}/frameworks/base/packages/SystemUI/res-product"
            )
        }
    }
}
```

## File Structure

```
SystemUI-Gradle/
├── build.gradle.kts              # Root build file
├── settings.gradle.kts           # Module includes
├── gradle.properties             # Build properties
├── local.properties              # User paths (not committed)
├── gradle/
│   └── wrapper/
│       ├── gradle-wrapper.jar
│       └── gradle-wrapper.properties
├── gradlew
├── gradlew.bat
├── libs/                         # Prebuilt AOSP JARs/AARs (not committed)
│   ├── framework.jar
│   ├── SystemUI-framework.jar
│   ├── WindowManager-Shell.aar
│   ├── SettingsLib.aar
│   └── ...
├── scripts/
│   └── extract_aosp_libs.sh      # Helper to copy JARs from AOSP out/
├── app/
│   └── build.gradle.kts
├── shared/
│   └── build.gradle.kts
├── plugin/
│   └── build.gradle.kts
├── plugin-core/
│   └── build.gradle.kts
├── unfold/
│   └── build.gradle.kts
├── customization/
│   └── build.gradle.kts
├── animation/
│   └── build.gradle.kts
├── common/
│   └── build.gradle.kts
├── utils/
│   └── build.gradle.kts
└── log/
    └── build.gradle.kts
```

## Helper Script: `extract_aosp_libs.sh`

A shell script that:
1. Reads `aosp.out.dir` from `local.properties`
2. Finds and copies needed JARs/AARs from `out/` to `libs/`
3. Handles both `obj/` and `soong/` output paths
4. Reports any missing libraries

This script must be run once after setting up `local.properties` and after any AOSP rebuild.

## Constraints & Trade-offs

1. **Source in AOSP tree**: Source files stay in their original locations. This means the Gradle project depends on the AOSP directory structure. If AOSP source moves, paths must be updated.

2. **Prebuilt dependencies**: AOSP-specific libraries must be extracted from a compiled AOSP tree. This requires an initial AOSP build and re-extraction after framework changes.

3. **No tests initially**: Test setup (JUnit, Robolectric) is deferred to a later phase. The test source directories are not included in the Gradle build.

4. **Compose**: AOSP SystemUI uses Compose. The Gradle build includes the Compose compiler and runtime. Version alignment between Compose compiler and Kotlin version is critical.

5. **Annotation processing**: Dagger2 and Room annotation processors are configured. The PluginAnnotationProcessor from plugin_core is also included.

6. **ProGuard**: ProGuard rules from the AOSP tree are referenced directly. No duplication.

7. **Build compatibility**: The Gradle build does not modify any AOSP files. Both build systems can coexist.
