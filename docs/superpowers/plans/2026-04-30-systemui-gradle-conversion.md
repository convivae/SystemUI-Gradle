# SystemUI Gradle Conversion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a multi-module Gradle build for AOSP SystemUI (API 37) that enables Android Studio IDE support and Gradle-based APK builds.

**Architecture:** 10 Gradle modules mirroring AOSP's module structure. Source files remain in the AOSP tree — Gradle reads them via `srcDirs`. AOSP framework dependencies are handled as prebuilt JARs extracted from the AOSP build output.

**Tech Stack:** Gradle 8.9, AGP 8.7.0, Kotlin 2.0.21, Compose compiler (bundled with Kotlin 2.0), Dagger 2, AndroidX

---

## File Map

| File | Purpose |
|---|---|
| `build.gradle.kts` | Root build file — plugin declarations, allprojects config |
| `settings.gradle.kts` | Module includes, repository config, plugin versions |
| `gradle.properties` | JVM args, AndroidX opt-in, Kotlin options |
| `local.properties` | User-specific paths (not committed) |
| `.gitignore` | Ignore build output, libs, local.properties |
| `gradle/wrapper/*` | Gradle wrapper (8.9) |
| `gradlew`, `gradlew.bat` | Wrapper scripts |
| `scripts/extract_aosp_libs.sh` | Extract prebuilt JARs from AOSP out/ |
| `app/build.gradle.kts` | Main SystemUI app module |
| `shared/build.gradle.kts` | SystemUISharedLib module |
| `plugin/build.gradle.kts` | SystemUIPluginLib module |
| `plugin-core/build.gradle.kts` | PluginCoreLib + PluginAnnotationLib module |
| `unfold/build.gradle.kts` | SystemUIUnfoldLib module |
| `customization/build.gradle.kts` | SystemUICustomizationLib module |
| `animation/build.gradle.kts` | PlatformAnimationLib module |
| `common/build.gradle.kts` | SystemUICommon module |
| `utils/build.gradle.kts` | SystemUI-shared-utils module |
| `log/build.gradle.kts` | SystemUILogLib module |

---

## Task 1: Gradle Wrapper and Root Configuration

**Files:**
- Create: `build.gradle.kts`
- Create: `settings.gradle.kts`
- Create: `gradle.properties`
- Create: `local.properties`
- Create: `gradle/wrapper/gradle-wrapper.properties`
- Create: `gradlew`
- Create: `gradlew.bat`

- [ ] **Step 1: Initialize Gradle wrapper**

Run from `/home/conv/myspace/SystemUI-Gradle`:

```bash
cd /home/conv/myspace/SystemUI-Gradle
gradle wrapper --gradle-version 8.9
```

If `gradle` is not installed, download the wrapper manually:

```bash
mkdir -p gradle/wrapper
cat > gradle/wrapper/gradle-wrapper.properties << 'EOF'
distributionBase=GRADLE_USER_HOME
distributionPath=wrapper/dists
distributionUrl=https\://services.gradle.org/distributions/gradle-8.9-bin.zip
networkTimeout=10000
validateDistributionUrl=true
zipStoreBase=GRADLE_USER_HOME
zipStorePath=wrapper/dists
EOF
```

- [ ] **Step 2: Create `settings.gradle.kts`**

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolution {
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "SystemUI-Gradle"

enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")

include(":app")
include(":shared")
include(":plugin")
include(":plugin-core")
include(":unfold")
include(":customization")
include(":animation")
include(":common")
include(":utils")
include(":log")
```

- [ ] **Step 3: Create `gradle.properties`**

```properties
org.gradle.jvmargs=-Xmx4096m -Dfile.encoding=UTF-8
org.gradle.parallel=true
org.gradle.caching=true

android.useAndroidX=true
android.nonTransitiveRClass=true

kotlin.code.style=official
```

- [ ] **Step 4: Create `local.properties` template**

```properties
# Copy this file and fill in your paths
sdk.dir=/path/to/Android/Sdk
aosp.dir=/home/conv/myspace/aosp
aosp.out.dir=/home/conv/myspace/aosp/out/target/product/arm64
```

- [ ] **Step 5: Create `build.gradle.kts` (root)**

```kotlin
plugins {
    id("com.android.application") version "8.7.0" apply false
    id("com.android.library") version "8.7.0" apply false
    id("org.jetbrains.kotlin.android") version "2.0.21" apply false
    id("org.jetbrains.kotlin.kapt") version "2.0.21" apply false
    id("com.google.protobuf") version "0.9.4" apply false
}

val aospDir: String by project
val libsDir = layout.projectDirectory.dir("libs")

allprojects {
    repositories {
        google()
        mavenCentral()
    }
}
```

- [ ] **Step 6: Commit**

```bash
git add build.gradle.kts settings.gradle.kts gradle.properties local.properties gradle/ gradlew gradlew.bat
git commit -m "feat: add Gradle wrapper and root configuration"
```

---

## Task 2: .gitignore

**Files:**
- Modify: `.gitignore`

- [ ] **Step 1: Update `.gitignore`**

Append to existing `.gitignore`:

```gitignore
# Gradle
.gradle/
build/
**/build/
local.properties
libs/
!gradle/wrapper/gradle-wrapper.jar

# IDE
.idea/
*.iml
*.iws
*.ipr

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: update gitignore for Gradle project"
```

---

## Task 3: AOSP Library Extraction Script

**Files:**
- Create: `scripts/extract_aosp_libs.sh`

- [ ] **Step 1: Create the extraction script**

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Read paths from local.properties
if [[ ! -f "$PROJECT_DIR/local.properties" ]]; then
    echo "ERROR: local.properties not found. Copy local.properties.template and fill in your paths."
    exit 1
fi

AOSP_DIR=$(grep "^aosp.dir=" "$PROJECT_DIR/local.properties" | cut -d= -f2-)
AOSP_OUT_DIR=$(grep "^aosp.out.dir=" "$PROJECT_DIR/local.properties" | cut -d= -f2-)

if [[ -z "$AOSP_DIR" || -z "$AOSP_OUT_DIR" ]]; then
    echo "ERROR: aosp.dir and aosp.out.dir must be set in local.properties"
    exit 1
fi

LIBS_DIR="$PROJECT_DIR/libs"
mkdir -p "$LIBS_DIR"

echo "AOSP source: $AOSP_DIR"
echo "AOSP output: $AOSP_OUT_DIR"
echo "Target dir:  $LIBS_DIR"
echo ""

# Framework JARs (compileOnly — not bundled in APK)
FRAMEWORK_JARS=(
    "system/framework/framework.jar"
    "system/framework/services.jar"
)

# Prebuilt libraries from soong intermediates
find_sojar() {
    local name="$1"
    local soong_dir="$AOSP_OUT_DIR/soong/.intermediates"
    
    # Try common paths
    local candidates=(
        "$soong_dir/frameworks/base/packages/SystemUI/$name/android_common/combined/$name.jar"
        "$soong_dir/frameworks/base/packages/SystemUI/$name/android_common/turbine-combined/$name.jar"
        "$soong_dir/frameworks/libs/systemui/$name/android_common/combined/$name.jar"
        "$soong_dir/frameworks/libs/systemui/$name/android_common/turbine-combined/$name.jar"
        "$soong_dir/frameworks/base/libs/WindowManager/Shell/$name/android_common/combined/$name.jar"
        "$soong_dir/frameworks/base/libs/WindowManager/Shell/$name/android_common/turbine-combined/$name.jar"
        "$soong_dir/frameworks/base/packages/SettingsLib/$name/android_common/combined/$name.jar"
        "$soong_dir/frameworks/base/packages/SettingsLib/$name/android_common/turbine-combined/$name.jar"
        "$soong_dir/packages/apps/Car/SystemUI/$name/android_common/combined/$name.jar"
    )
    
    for candidate in "${candidates[@]}"; do
        if [[ -f "$candidate" ]]; then
            echo "$candidate"
            return 0
        fi
    done
    
    # Broader search
    local found
    found=$(find "$soong_dir" -name "$name.jar" -path "*/combined/*" 2>/dev/null | head -1)
    if [[ -n "$found" ]]; then
        echo "$found"
        return 0
    fi
    
    return 1
}

find_aar() {
    local name="$1"
    local soong_dir="$AOSP_OUT_DIR/soong/.intermediates"
    
    local found
    found=$(find "$soong_dir" -name "$name.aar" 2>/dev/null | head -1)
    if [[ -n "$found" ]]; then
        echo "$found"
        return 0
    fi
    return 1
}

copy_lib() {
    local name="$1"
    local type="${2:-jar}"  # jar or aar
    
    local dest_name="$name.$type"
    if [[ -f "$LIBS_DIR/$dest_name" ]]; then
        echo "  SKIP $dest_name (already exists)"
        return 0
    fi
    
    local source=""
    if [[ "$type" == "aar" ]]; then
        source=$(find_aar "$name") || true
    else
        source=$(find_sojar "$name") || true
    fi
    
    if [[ -z "$source" ]]; then
        echo "  WARN: $name.$type not found in AOSP output"
        return 1
    fi
    
    cp "$source" "$LIBS_DIR/$dest_name"
    echo "  OK   $dest_name <- $source"
}

echo "=== Framework JARs (compileOnly) ==="
for jar in "${FRAMEWORK_JARS[@]}"; do
    src="$AOSP_OUT_DIR/$jar"
    dest="$LIBS_DIR/$(basename "$jar")"
    if [[ -f "$src" ]]; then
        cp "$src" "$dest"
        echo "  OK   $(basename "$jar") <- $src"
    else
        echo "  WARN: $jar not found"
    fi
done

echo ""
echo "=== AOSP Library JARs ==="
LIBS_JAR=(
    "SystemUI-core"
    "SystemUISharedLib"
    "SystemUIPluginLib"
    "PluginCoreLib"
    "PluginAnnotationLib"
    "SystemUIUnfoldLib"
    "SystemUICustomizationLib"
    "PlatformAnimationLib"
    "SystemUIShaderLib"
    "SystemUICommon"
    "SystemUI-shared-utils"
    "SystemUILogLib"
    "SystemUI-tags"
    "SystemUI-proto"
    "SystemUI-statsd"
    "SystemUI-res"
    "WifiTrackerLib"
    "SettingsLib"
    "WindowManager-Shell"
    "WindowManager-Shell-shared"
    "WindowManager-Shell-proto"
    "compilelib"
    "animationlib"
    "iconloader_base"
    "tracinglib-platform"
    "contextualeducationlib"
    "motion_tool_lib"
    "msdl"
    "view_capture"
    "monet"
    "libmonet"
    "com_android_systemui_shared_flags_lib"
    "com_android_systemui_flags_lib"
    "notification_flags_lib"
    "device_state_flags_lib"
    "LowLightDreamLib"
    "TraceurCommon"
    "Traceur-res"
    "PlatformComposeCore"
    "PlatformComposeSceneTransitionLayout"
)

for lib in "${LIBS_JAR[@]}"; do
    copy_lib "$lib" "jar"
done

echo ""
echo "=== AOSP Library AARs ==="
LIBS_AAR=(
    "PlatformComposeCore"
    "PlatformComposeSceneTransitionLayout"
)

for lib in "${LIBS_AAR[@]}"; do
    copy_lib "$lib" "aar"
done

echo ""
echo "=== Pods Libraries ==="
PODS=(
    "api"
    "impl"
)

# Search in pods subdirectories
for pod in "${PODS[@]}"; do
    found=$(find "$AOSP_OUT_DIR/soong/.intermediates/frameworks/base/packages/SystemUI/pods" -name "$pod.jar" -path "*/combined/*" 2>/dev/null | head -1)
    if [[ -n "$found" ]]; then
        cp "$found" "$LIBS_DIR/pods-$pod.jar"
        echo "  OK   pods-$pod.jar <- $found"
    else
        echo "  WARN: pods/$pod.jar not found"
    fi
done

echo ""
echo "Done. Libraries extracted to $LIBS_DIR"
echo ""
echo "NOTE: Some libraries may be AARs instead of JARs. If a JAR is missing,"
echo "      check for an AAR version in the soong intermediates."
```

- [ ] **Step 2: Make script executable**

```bash
chmod +x scripts/extract_aosp_libs.sh
```

- [ ] **Step 3: Commit**

```bash
git add scripts/extract_aosp_libs.sh
git commit -m "feat: add AOSP library extraction script"
```

---

## Task 4: Leaf Library Modules (utils, common, log, plugin-core)

These modules have no internal dependencies — they only depend on external libraries.

**Files:**
- Create: `utils/build.gradle.kts`
- Create: `common/build.gradle.kts`
- Create: `log/build.gradle.kts`
- Create: `plugin-core/build.gradle.kts`

- [ ] **Step 1: Create `utils/build.gradle.kts`**

```kotlin
plugins {
    id("java-library")
    id("org.jetbrains.kotlin.jvm")
}

val aospDir: String by project

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    main {
        java.srcDirs("$aospDir/frameworks/base/packages/SystemUI/utils/src")
    }
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.0.21")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")
}
```

- [ ] **Step 2: Create `common/build.gradle.kts`**

```kotlin
plugins {
    id("java-library")
    id("org.jetbrains.kotlin.jvm")
}

val aospDir: String by project

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    main {
        java.srcDirs("$aospDir/frameworks/base/packages/SystemUI/common/src")
    }
}

dependencies {
    implementation(project(":utils"))
    implementation(files("$rootDir/libs/tracinglib-platform.jar"))
}
```

- [ ] **Step 3: Create `log/build.gradle.kts`**

```kotlin
plugins {
    id("java-library")
    id("org.jetbrains.kotlin.jvm")
}

val aospDir: String by project

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    main {
        java.srcDirs("$aospDir/frameworks/base/packages/SystemUI/log/src")
    }
}

dependencies {
    implementation(project(":common"))
    implementation("com.google.errorprone:error_prone_annotations:2.28.0")
}
```

- [ ] **Step 4: Create `plugin-core/build.gradle.kts`**

```kotlin
plugins {
    id("java-library")
    id("org.jetbrains.kotlin.jvm")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

java {
    sourceCompatibility = JavaVersion.VERSION_1_8
    targetCompatibility = JavaVersion.VERSION_1_8
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    main {
        java.srcDirs(
            "$aospDir/frameworks/base/packages/SystemUI/plugin_core/src"
        )
        // Exclude annotation processor sources — they go in a separate source set
        exclude("**/processor/**")
    }
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.0.21")
    implementation("androidx.annotation:annotation:1.8.2")
    
    // Auto-service for annotation processor
    kapt("com.google.auto.service:auto-service:1.1.1")
    implementation("com.google.auto.service:auto-service-annotations:1.1.1")
    implementation("com.google.auto:auto-common:1.2.2")
    implementation("com.google.guava:guava:33.2.1-jre")
    implementation("javax.inject:javax.inject:1")
}
```

- [ ] **Step 5: Commit**

```bash
git add utils/ common/ log/ plugin-core/
git commit -m "feat: add leaf library modules (utils, common, log, plugin-core)"
```

---

## Task 5: Plugin Module

**Files:**
- Create: `plugin/build.gradle.kts`

- [ ] **Step 1: Create `plugin/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.plugin"
    compileSdk = 37

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs = listOf("-Xjvm-default=all")
    }

    sourceSets {
        main {
            java.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/plugin/src",
                "$aospDir/frameworks/base/packages/SystemUI/plugin/bcsmartspace/src"
            )
            exclude("**/PluginProtectorStub.kt")
        }
    }

    buildFeatures {
        aidl = true
    }
}

dependencies {
    implementation(project(":plugin-core"))
    implementation(project(":common"))
    implementation(project(":log"))

    implementation("androidx.annotation:annotation:1.8.2")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.compose.ui:ui:1.7.0")
    implementation("androidx.compose.runtime:runtime:1.7.0")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/PlatformAnimationLib.jar"))
    implementation(files("$rootDir/libs/SystemUICommon.jar"))
    implementation(files("$rootDir/libs/SystemUILogLib.jar"))
    implementation(files("$rootDir/libs/PluginCoreLib.jar"))
}
```

- [ ] **Step 2: Commit**

```bash
git add plugin/
git commit -m "feat: add plugin module"
```

---

## Task 6: Animation Module

**Files:**
- Create: `animation/build.gradle.kts`

- [ ] **Step 1: Create `animation/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.animation"
    compileSdk = 37

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs = listOf("-Xjvm-default=all")
    }

    sourceSets {
        main {
            java.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/animation/src"
            )
            res.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/animation/res"
            )
        }
    }
}

dependencies {
    implementation("androidx.core:core-animation:1.0.0")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.annotation:annotation:1.8.2")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/WindowManager-Shell-shared.jar"))
    implementation(files("$rootDir/libs/animationlib.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_shared_flags_lib.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_flags_lib.jar"))
}
```

- [ ] **Step 2: Commit**

```bash
git add animation/
git commit -m "feat: add animation module"
```

---

## Task 7: Unfold Module

**Files:**
- Create: `unfold/build.gradle.kts`

- [ ] **Step 1: Create `unfold/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.unfold"
    compileSdk = 37

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs = listOf("-Xjvm-default=all")
    }

    sourceSets {
        main {
            java.srcDirs("$aospDir/frameworks/base/packages/SystemUI/unfold/src")
            aidl.srcDirs("$aospDir/frameworks/base/packages/SystemUI/unfold/src")
        }
    }

    buildFeatures {
        aidl = true
    }
}

dependencies {
    implementation("androidx.dynamicanimation:dynamicanimation:1.0.0")
    implementation("com.google.dagger:dagger:2.51.1")
    kapt("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")
}
```

- [ ] **Step 2: Commit**

```bash
git add unfold/
git commit -m "feat: add unfold module"
```

---

## Task 8: Customization Module

**Files:**
- Create: `customization/build.gradle.kts`

- [ ] **Step 1: Create `customization/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.customization"
    compileSdk = 37

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs = listOf("-Xjvm-default=all")
    }

    sourceSets {
        main {
            java.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/customization/src"
            )
            res.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/customization/res"
            )
            aidl.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/customization/src"
            )
        }
    }

    buildFeatures {
        aidl = true
    }
}

dependencies {
    implementation(project(":plugin"))
    implementation(project(":unfold"))
    implementation(project(":animation"))

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("com.google.dagger:dagger:2.51.1")
    kapt("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/PlatformAnimationLib.jar"))
    implementation(files("$rootDir/libs/PluginCoreLib.jar"))
    implementation(files("$rootDir/libs/SystemUIPluginLib.jar"))
    implementation(files("$rootDir/libs/SystemUIUnfoldLib.jar"))
    implementation(files("$rootDir/libs/monet.jar"))
}
```

- [ ] **Step 2: Commit**

```bash
git add customization/
git commit -m "feat: add customization module"
```

---

## Task 9: Shared Module

**Files:**
- Create: `shared/build.gradle.kts`

- [ ] **Step 1: Create `shared/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.library")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

android {
    namespace = "com.android.systemui.shared"
    compileSdk = 37

    defaultConfig {
        minSdk = 34
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
        freeCompilerArgs = listOf("-Xjvm-default=all")
    }

    sourceSets {
        main {
            java.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/shared/src"
            )
            res.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/shared/res"
            )
            aidl.srcDirs(
                "$aospDir/frameworks/base/packages/SystemUI/shared/src"
            )
        }
    }

    buildFeatures {
        aidl = true
    }
}

dependencies {
    implementation(project(":plugin"))
    implementation(project(":unfold"))
    implementation(project(":animation"))
    implementation(project(":common"))

    // AndroidX
    implementation("androidx.dynamicanimation:dynamicanimation:1.0.0")
    implementation("androidx.concurrent:concurrent-futures:1.2.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.lifecycle:lifecycle-viewmodel-ktx:2.8.4")
    implementation("androidx.recyclerview:recyclerview:1.3.2")

    // Kotlin coroutines
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")

    // Dagger
    implementation("com.google.dagger:dagger:2.51.1")
    kapt("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")

    // Prebuilt AOSP libs
    implementation(files("$rootDir/libs/BiometricsSharedLib.jar"))
    implementation(files("$rootDir/libs/PlatformAnimationLib.jar"))
    implementation(files("$rootDir/libs/PluginCoreLib.jar"))
    implementation(files("$rootDir/libs/SystemUIPluginLib.jar"))
    implementation(files("$rootDir/libs/SystemUIUnfoldLib.jar"))
    implementation(files("$rootDir/libs/WindowManager-Shell-shared.jar"))
    implementation(files("$rootDir/libs/tracinglib-platform.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_shared_flags_lib.jar"))
    implementation(files("$rootDir/libs/msdl.jar"))
    implementation(files("$rootDir/libs/view_capture.jar"))
}
```

- [ ] **Step 2: Commit**

```bash
git add shared/
git commit -m "feat: add shared module"
```

---

## Task 10: App Module (Main SystemUI)

**Files:**
- Create: `app/build.gradle.kts`
- Create: `app/src/main/AndroidManifest.xml` (symlink or copy)

- [ ] **Step 1: Create `app/build.gradle.kts`**

```kotlin
plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.kapt")
    id("com.google.protobuf")
}

val aospDir: String by project
val systemuiDir = "$aospDir/frameworks/base/packages/SystemUI"

android {
    namespace = "com.android.systemui"
    compileSdk = 37

    defaultConfig {
        applicationId = "com.android.systemui"
        minSdk = 34
        targetSdk = 37
        versionCode = 1
        versionName = "1.0"

        javaCompileOptions {
            annotationProcessorOptions {
                arguments += mapOf(
                    "dagger.fastInit" to "enabled",
                    "dagger.explicitBindingConflictsWithInject" to "ERROR",
                    "dagger.strictMultibindingValidation" to "enabled"
                )
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    sourceSets {
        main {
            java.srcDirs(
                "$systemuiDir/src",
                "$systemuiDir/src-release",
                "$systemuiDir/compose/features/src",
                "$systemuiDir/compose/facade/enabled/src"
            )
            res.srcDirs(
                "$systemuiDir/res",
                "$systemuiDir/res-keyguard",
                "$systemuiDir/res-product"
            )
            aidl.srcDirs("$systemuiDir/src")
            proto.srcDirs("$systemuiDir/src")
        }
    }

    buildFeatures {
        aidl = true
        buildConfig = true
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }

    lint {
        baseline = file("$systemuiDir/lint-baseline.xml")
    }
}

dependencies {
    // Internal modules
    implementation(project(":shared"))
    implementation(project(":customization"))
    implementation(project(":animation"))
    implementation(project(":common"))
    implementation(project(":log"))
    implementation(project(":utils"))

    // AndroidX - Core
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.viewpager2:viewpager2:1.1.0")
    implementation("androidx.legacy:legacy-support-v4:1.0.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("androidx.preference:preference:1.2.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.concurrent:concurrent-futures:1.2.0")
    implementation("androidx.concurrent:concurrent-futures-ktx:1.2.0")
    implementation("androidx.mediarouter:mediarouter:1.7.0")
    implementation("androidx.palette:palette:1.0.0")
    implementation("androidx.legacy:legacy-preference-v14:1.0.0")
    implementation("androidx.leanback:leanback:1.2.0")
    implementation("androidx.slice:slice-core:1.1.0")
    implementation("androidx.slice:slice-view:1.1.0")
    implementation("androidx.slice:slice-builders:1.1.0")
    implementation("androidx.arch.core:core-runtime:2.2.0")
    implementation("androidx.lifecycle:lifecycle-common-java8:2.8.4")
    implementation("androidx.lifecycle:lifecycle-extensions:2.2.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.4")
    implementation("androidx.dynamicanimation:dynamicanimation:1.0.0")
    implementation("androidx.constraintlayout:constraintlayout:2.1.4")
    implementation("androidx.exifinterface:exifinterface:1.3.7")
    implementation("androidx.room:room-runtime:2.6.1")
    implementation("androidx.room:room-ktx:2.6.1")
    kapt("androidx.room:room-compiler:2.6.1")
    implementation("androidx.datastore:datastore-preferences:1.1.1")
    implementation("androidx.media3:media3-common:1.4.1")
    implementation("androidx.media3:media3-session:1.4.1")

    // Material
    implementation("com.google.android.material:material:1.12.0")

    // Compose
    implementation("androidx.compose.runtime:runtime:1.7.0")
    implementation("androidx.compose.material3:material3:1.3.0")
    implementation("androidx.compose.material:material-icons-extended:1.7.0")
    implementation("androidx.activity:activity-compose:1.9.2")
    implementation("androidx.compose.animation:animation-graphics:1.7.0")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.4")

    // Kotlin
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.0.21")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")

    // Dagger
    implementation("com.google.dagger:dagger:2.51.1")
    kapt("com.google.dagger:dagger-compiler:2.51.1")
    implementation("javax.inject:javax.inject:1")
    implementation("javax.annotation:javax.annotation-api:1.3.2")

    // Lottie
    implementation("com.airbnb.android:lottie:6.4.2")
    implementation("com.airbnb.android:lottie-compose:6.4.2")

    // Protobuf
    implementation("com.google.protobuf:protobuf-javalite:3.25.3")

    // Prebuilt AOSP libs (compileOnly — framework APIs)
    compileOnly(files("$rootDir/libs/framework.jar"))

    // Prebuilt AOSP libs (implementation)
    implementation(files("$rootDir/libs/SystemUI-proto.jar"))
    implementation(files("$rootDir/libs/SystemUI-tags.jar"))
    implementation(files("$rootDir/libs/SystemUI-statsd.jar"))
    implementation(files("$rootDir/libs/SystemUI-res.jar"))
    implementation(files("$rootDir/libs/WifiTrackerLib.jar"))
    implementation(files("$rootDir/libs/SettingsLib.jar"))
    implementation(files("$rootDir/libs/WindowManager-Shell.jar"))
    implementation(files("$rootDir/libs/WindowManager-Shell-proto.jar"))
    implementation(files("$rootDir/libs/compilelib.jar"))
    implementation(files("$rootDir/libs/iconloader_base.jar"))
    implementation(files("$rootDir/libs/motion_tool_lib.jar"))
    implementation(files("$rootDir/libs/contextualeducationlib.jar"))
    implementation(files("$rootDir/libs/monet.jar"))
    implementation(files("$rootDir/libs/libmonet.jar"))
    implementation(files("$rootDir/libs/notification_flags_lib.jar"))
    implementation(files("$rootDir/libs/device_state_flags_lib.jar"))
    implementation(files("$rootDir/libs/LowLightDreamLib.jar"))
    implementation(files("$rootDir/libs/TraceurCommon.jar"))
    implementation(files("$rootDir/libs/Traceur-res.jar"))
    implementation(files("$rootDir/libs/PlatformComposeCore.jar"))
    implementation(files("$rootDir/libs/PlatformComposeSceneTransitionLayout.jar"))
    implementation(files("$rootDir/libs/com_android_systemui_flags_lib.jar"))

    // Pods (Dagger API modules)
    implementation(files("$rootDir/libs/pods-api.jar"))
    implementation(files("$rootDir/libs/pods-impl.jar"))
}

protobuf {
    protoc {
        artifact = "com.google.protobuf:protoc:3.25.3"
    }
}

kapt {
    correctErrorTypes = true
}
```

- [ ] **Step 2: Create `app/src/main/AndroidManifest.xml`**

Since the manifest is in the AOSP tree, we need to point to it. Add to `app/build.gradle.kts`:

```kotlin
android {
    // ... existing config ...
    
    sourceSets {
        main {
            manifest.srcFile("$systemuiDir/AndroidManifest.xml")
            // ... existing srcDirs ...
        }
    }
}
```

Update the `build.gradle.kts` to add the manifest source file reference in the `sourceSets` block.

- [ ] **Step 3: Commit**

```bash
git add app/
git commit -m "feat: add app module (main SystemUI)"
```

---

## Task 11: ProGuard Configuration

**Files:**
- Modify: `app/build.gradle.kts`

- [ ] **Step 1: Add ProGuard config to app module**

Add to `app/build.gradle.kts` inside the `android` block:

```kotlin
    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(
                file("$systemuiDir/proguard.flags"),
                file("$systemuiDir/proguard_common.flags"),
                file("$systemuiDir/proguard_kotlin.flags")
            )
        }
        debug {
            isMinifyEnabled = false
        }
    }
```

- [ ] **Step 2: Commit**

```bash
git add app/
git commit -m "feat: add ProGuard configuration"
```

---

## Task 12: Verification

- [ ] **Step 1: Run Gradle sync**

```bash
cd /home/conv/myspace/SystemUI-Gradle
./gradlew --no-daemon projects
```

Expected: Lists all 10 modules without errors.

- [ ] **Step 2: Run Gradle build (compile only)**

```bash
./gradlew --no-daemon :app:compileDebugJavaWithJavac :app:compileDebugKotlin 2>&1 | tail -50
```

Expected: Compilation errors from missing AOSP-specific classes. This is expected — it means the build structure is correct and we're hitting the real compilation phase. The errors will guide which prebuilt JARs are still missing.

- [ ] **Step 3: Fix missing dependencies**

Based on compilation errors, add missing prebuilt JARs to `libs/` and update `build.gradle.kts` files as needed. Common patterns:
- `Unresolved reference: <ClassName>` → find which AOSP module provides it, add its JAR
- `Cannot find symbol: <method>` → likely a framework API version mismatch

- [ ] **Step 4: Verify Android Studio import**

Open the project in Android Studio. Verify:
- All modules are recognized
- Source code navigation works
- Code completion works for available APIs
- No build configuration errors in the Build panel

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: verify Gradle build and fix dependency issues"
```
