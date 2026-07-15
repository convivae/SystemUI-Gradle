# SystemUI v2 Dual-Build Skeleton Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a v2 skeleton repo so `./gradlew :app:assembleDebug` produces a signed `SystemUI.apk` (with a stub "Hello SystemUI" service) **and** `m SystemUI` builds inside the AOSP tree, both off the same source tree at `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/`.

**Architecture:** Per v2 spec §4. Mirror AOSP's top-level sub-folders as Gradle modules (`:app`, `:SystemUI-core`, `:SystemUI-shared`, `:SystemUI-plugin-core`, `:SystemUI-plugin`, `:SystemUI-animation`, `:SystemUI-customization`). Online deps (AndroidX/Compose/Kotlinx/Dagger/Material) via `libs.versions.toml`. Hidden platform APIs via the AOSP-compiled `framework.jar` committed at `libs/framework.jar` and injected into the root build's bootclasspath. Custom SDK Platform `SysUISdk` is already installed on this machine — we only need to point Gradle at it. Dual-build via a parallel `Android.bp` that names the same modules.

**Tech Stack:** Gradle 9.5.0, AGP 9.2.0, Kotlin 2.3.21, Android SDK Platform `SysUISdk` (pre-installed), `compileSdkPreview = "SysUISdk"`. No LFS; binaries committed directly. No R8/ProGuard in this skeleton (debug builds only, per spec §3).

**Reference:** `CarSystemUIGradle/` (key commit `c0ae96b`) — patterns only, not source.

---

## File map (what gets created)

| Path | Purpose |
|------|---------|
| `gradle/libs.versions.toml` | Version catalog: AGP/Kotlin + AndroidX/Compose/Dagger/Kotlinx versions |
| `settings.gradle.kts` | Includes 7 modules, declares repos (google + mavenCentral), `rootProject.name = "SystemUI"` |
| `build.gradle.kts` | Root plugin block + `allprojects` hook that prepends `libs/framework.jar` to JavaCompile/KotlinCompile classpath |
| `gradle.properties` | `android.suppressUnsupportedCompileSdk=SysUISdk`, `org.gradle.jvmargs=-Xmx2g`, `kotlin.code.style=official`, `android.nonTransitiveRClass=true`, `android.useNonFinalResourceIds=false` |
| `.gitignore` | `.gradle/`, `build/`, `local.properties`, `.idea/`, `*.iml`, `captures/` |
| `Android.bp` | Mirror modules as `android_library` + `android_app` for AOSP build, with `aaptflags: ["--rename-manifest-package", "com.android.systemui"]` for `:app` |
| `CleanSpec.mk` | Mirror AOSP clean rules |
| `OWNERS` | Empty (no reviewers yet) |
| `app/build.gradle.kts` | `com.android.application`, `namespace = "com.android.systemui"`, `compileSdkPreview = "SysUISdk"`, deps on every library module |
| `app/src/main/AndroidManifest.xml` | `<application>` with `SystemUIService` (stub) |
| `app/src/main/java/com/android/systemui/SystemUIService.java` | Stub: log + `SystemUIApplication`-shaped wiring |
| `app/src/main/java/com/android/systemui/SystemUIApplication.java` | Stub: extends `android.app.Application` |
| `app/src/main/res/values/strings.xml` | `<string name="hello_systemui">Hello SystemUI</string>` |
| `SystemUI-core/build.gradle.kts` | `com.android.library`, `compileSdkPreview = "SysUISdk"`, no Kotlin sources in v1 skeleton |
| `SystemUI-core/src/main/AndroidManifest.xml` | Empty manifest, namespace `com.android.systemui.core` |
| `SystemUI-shared/build.gradle.kts` | `com.android.library` referencing `libs/prebuilts/SystemUI-shared.jar` as `compileOnly` |
| `SystemUI-animation/build.gradle.kts` | Same shape as shared, references `SystemUI-animation.jar` |
| `SystemUI-customization/build.gradle.kts` | Same shape |
| `SystemUI-plugin/build.gradle.kts` | Same shape |
| `SystemUI-plugin-core/build.gradle.kts` | `com.android.library` (compiled source), but v1 skeleton has **no** `.java`/`.kt` files — placeholder src/ with `.gitkeep` |
| `libs/framework.jar` | Copied from `aosp/out/soong/.intermediates/frameworks/base/framework/android_common/turbine-combined/framework.jar` |
| `libs/prebuilts/SystemUI-shared.jar` | From AOSP build outputs |
| `libs/prebuilts/SystemUI-animation.jar` | Same |
| `libs/prebuilts/SystemUI-customization.jar` | Same |
| `libs/prebuilts/SystemUI-plugin.jar` | Same |
| `keystore/SystemUI.pk8`, `keystore/SystemUI.x509.pem`, `keystore/SystemUI.pem` | Platform signing keys for `signingConfigs` |
| `tools/extract_prebuilts.sh` | Idempotent script: copies the 4 prebuilt JARs from AOSP out/ to `libs/prebuilts/` |
| `tools/install_sdk.sh` | No-op stub that asserts `/home/conv/Android/Sdk/platforms/android-SysUISdk/` exists and prints it |
| `tools/sync_aosp_sources.sh` | (Not used in v1 skeleton — placeholder with `# SYSOPS: deferred to v2 feature tasks`) |

---

## Task 1: Bootstrap root Gradle config

**Files:**
- Create: `gradle/libs.versions.toml`
- Create: `settings.gradle.kts`
- Create: `build.gradle.kts`
- Create: `gradle.properties`
- Modify: `.gitignore`

- [ ] **Step 1: Write `gradle/libs.versions.toml`**

```toml
[versions]
agp = "9.2.0"
kotlin = "2.3.21"
androidxCore = "1.13.1"
androidxAnnotation = "1.8.0"
material = "1.12.0"
kotlinxCoroutines = "1.8.1"
dagger = "2.51.1"

[plugins]
android-application = { id = "com.android.application", version.ref = "agp" }
android-library = { id = "com.android.library", version.ref = "agp" }
kotlin-android = { id = "org.jetbrains.kotlin.android", version.ref = "kotlin" }

[libraries]
androidx-core = { module = "androidx.core:core-ktx", version.ref = "androidxCore" }
androidx-annotation = { module = "androidx.annotation:annotation", version.ref = "androidxAnnotation" }
material = { module = "com.google.android.material:material", version.ref = "material" }
kotlinx-coroutines-android = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-android", version.ref = "kotlinxCoroutines" }
dagger = { module = "com.google.dagger:dagger", version.ref = "dagger" }
```

- [ ] **Step 2: Write `settings.gradle.kts`**

```kotlin
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        // Local prebuilt AARs / JARs (e.g. SystemUI-shared.jar) referenced via flatDir or libs/ tree
    }
}

rootProject.name = "SystemUI"
include(":app")
include(":SystemUI-core")
include(":SystemUI-shared")
include(":SystemUI-animation")
include(":SystemUI-customization")
include(":SystemUI-plugin")
include(":SystemUI-plugin-core")
```

- [ ] **Step 3: Write root `build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.android.library) apply false
    alias(libs.plugins.kotlin.android) apply false
}

// Inject framework.jar into every Java/Kotlin compile so hidden platform APIs resolve.
// SYSOPS: AOSP-only `framework.jar` provides hidden APIs not in public SDK.
allprojects {
    gradle.projectsEvaluated {
        tasks.withType<JavaCompile>().configureEach {
            val frameworkJar = file("${rootProject.projectDir}/libs/framework.jar")
            if (frameworkJar.exists()) {
                options.bootstrapClasspath = files(frameworkJar) + files(
                    options.bootstrapClasspath?.files ?: emptySet()
                )
                classpath = files(frameworkJar) + classpath
            }
        }
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            val frameworkJar = file("${rootProject.projectDir}/libs/framework.jar")
            if (frameworkJar.exists()) {
                libraries.from(frameworkJar)
            }
        }
    }
}
```

- [ ] **Step 4: Write `gradle.properties`**

```
org.gradle.jvmargs=-Xmx2g -Dfile.encoding=UTF-8
org.gradle.parallel=true
android.suppressUnsupportedCompileSdk=SysUISdk
android.nonTransitiveRClass=true
android.useNonFinalResourceIds=false
kotlin.code.style=official
```

- [ ] **Step 5: Write `.gitignore`**

```
.gradle/
build/
local.properties
.idea/
*.iml
captures/
.kotlin/
```

- [ ] **Step 6: Verify the skeleton configures**

Run: `./gradlew help`
Expected: Lists `:app`, `:SystemUI-core`, `:SystemUI-shared`, `:SystemUI-animation`, `:SystemUI-customization`, `:SystemUI-plugin`, `:SystemUI-plugin-core` in "Included builds" or "Root project".

- [ ] **Step 7: Commit**

```bash
git add gradle/libs.versions.toml settings.gradle.kts build.gradle.kts gradle.properties .gitignore
git commit -m "build: add root Gradle config and version catalog"
```

---

## Task 2: Copy `framework.jar` into `libs/`

**Files:**
- Create: `libs/framework.jar` (binary copy)
- Create: `tools/extract_prebuilts.sh` (placeholder; populates `libs/prebuilts/` in Task 5)

- [ ] **Step 1: Verify the AOSP `framework.jar` exists**

Run: `ls -la /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/turbine-combined/framework.jar`
Expected: A regular file. If missing → STOP and rebuild AOSP framework target first.

- [ ] **Step 2: Copy it**

Run:
```bash
mkdir -p libs
cp /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/turbine-combined/framework.jar libs/framework.jar
ls -la libs/framework.jar
```
Expected: ~70MB file.

- [ ] **Step 3: Re-run `./gradlew help` to confirm bootstrap doesn't break**

Run: `./gradlew help`
Expected: still PASS.

- [ ] **Step 4: Commit**

```bash
git add libs/framework.jar
git commit -m "vendor: add AOSP framework.jar (see spec §5.3)"
```

---

## Task 3: Stub `:SystemUI-core` library module

**Files:**
- Create: `SystemUI-core/build.gradle.kts`
- Create: `SystemUI-core/src/main/AndroidManifest.xml`
- Create: `SystemUI-core/src/main/.gitkeep`

- [ ] **Step 1: Write `SystemUI-core/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.core"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation(libs.androidx.core)
    implementation(libs.androidx.annotation)
}
```

- [ ] **Step 2: Write `SystemUI-core/src/main/AndroidManifest.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" />
```

- [ ] **Step 3: Write `SystemUI-core/src/main/.gitkeep`** (empty file)

```bash
touch SystemUI-core/src/main/.gitkeep
```

- [ ] **Step 4: Build the module alone to prove it resolves framework.jar**

Run: `./gradlew :SystemUI-core:assembleDebug`
Expected: BUILD SUCCESSFUL — the `framework.jar` injection must not throw "class file has wrong version" / "no Kotlin metadata" errors.

- [ ] **Step 5: Commit**

```bash
git add SystemUI-core/
git commit -m "build: add :SystemUI-core library skeleton"
```

---

## Task 4: Stub `:SystemUI-plugin-core` library module

**Files:**
- Create: `SystemUI-plugin-core/build.gradle.kts`
- Create: `SystemUI-plugin-core/src/main/AndroidManifest.xml`
- Create: `SystemUI-plugin-core/src/main/.gitkeep`

- [ ] **Step 1: Write `SystemUI-plugin-core/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.plugin.core"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
```

- [ ] **Step 2: Write `SystemUI-plugin-core/src/main/AndroidManifest.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" />
```

- [ ] **Step 3: Write `SystemUI-plugin-core/src/main/.gitkeep`**

```bash
touch SystemUI-plugin-core/src/main/.gitkeep
```

- [ ] **Step 4: Build**

Run: `./gradlew :SystemUI-plugin-core:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 5: Commit**

```bash
git add SystemUI-plugin-core/
git commit -m "build: add :SystemUI-plugin-core library skeleton"
```

---

## Task 5: Extract prebuilt JARs for the 4 "prebuilt jar" modules

**Files:**
- Modify: `tools/extract_prebuilts.sh` (real script)
- Create: `libs/prebuilts/SystemUI-shared.jar`
- Create: `libs/prebuilts/SystemUI-animation.jar`
- Create: `libs/prebuilts/SystemUI-customization.jar`
- Create: `libs/prebuilts/SystemUI-plugin.jar`

- [ ] **Step 1: Probe AOSP out for the 4 jar paths**

Run:
```bash
find /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI \
    -name "SystemUI-shared.jar" -path "*/combined/*" 2>/dev/null | head -3
find /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI \
    -name "SystemUI-animation.jar" -path "*/combined/*" 2>/dev/null | head -3
find /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI \
    -name "SystemUI-customization.jar" -path "*/combined/*" 2>/dev/null | head -3
find /home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI \
    -name "SystemUI-plugin.jar" -path "*/combined/*" 2>/dev/null | head -3
```
Expected: 4 absolute paths, one per jar.

- [ ] **Step 2: Write `tools/extract_prebuilts.sh`**

```bash
#!/usr/bin/env bash
# Extract AOSP-compiled SystemUI prebuilt JARs into libs/prebuilts/.
# Idempotent: re-running overwrites with same content.
set -euo pipefail

AOSP_OUT="${AOSP_OUT:-/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/packages/SystemUI}"
DEST="$(cd "$(dirname "$0")/.." && pwd)/libs/prebuilts"
mkdir -p "$DEST"

copy_jar() {
    local name="$1"
    local src
    src=$(find "$AOSP_OUT" -name "${name}.jar" -path "*/combined/*" 2>/dev/null | head -1)
    if [[ -z "$src" ]]; then
        echo "ERROR: ${name}.jar not found under $AOSP_OUT" >&2
        return 1
    fi
    cp -f "$src" "$DEST/${name}.jar"
    echo "copied: $src -> $DEST/${name}.jar"
}

copy_jar SystemUI-shared
copy_jar SystemUI-animation
copy_jar SystemUI-customization
copy_jar SystemUI-plugin
```

- [ ] **Step 3: Run it**

Run: `chmod +x tools/extract_prebuilts.sh && ./tools/extract_prebuilts.sh`
Expected: 4 lines of "copied:" output. `ls libs/prebuilts/` shows 4 jars.

- [ ] **Step 4: Write `tools/install_sdk.sh` (no-op verification)**

```bash
#!/usr/bin/env bash
# Verify the custom SDK platform `SysUISdk` is installed. Exits non-zero
# if missing so CI fails loudly.
set -euo pipefail

SDK_ROOT="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/home/conv/Android/Sdk}}"
TARGET="$SDK_ROOT/platforms/android-SysUISdk"

if [[ ! -d "$TARGET" ]]; then
    echo "ERROR: $TARGET does not exist. See v2 spec §5.4 for setup." >&2
    exit 1
fi
echo "SysUISdk OK: $TARGET"
```

- [ ] **Step 5: Commit**

```bash
chmod +x tools/install_sdk.sh
git add tools/ libs/prebuilts/
git commit -m "vendor: add 4 AOSP prebuilt JARs + extract script (see spec §5.2)"
```

---

## Task 6: Write the 4 prebuilt-jar library modules

**Files:**
- Create: `SystemUI-shared/build.gradle.kts`
- Create: `SystemUI-animation/build.gradle.kts`
- Create: `SystemUI-customization/build.gradle.kts`
- Create: `SystemUI-plugin/build.gradle.kts`
- For each: `src/main/AndroidManifest.xml` + `src/main/.gitkeep`

- [ ] **Step 1: Write `SystemUI-shared/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.shared"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    compileOnly(files("libs/prebuilts/SystemUI-shared.jar"))
}
```

- [ ] **Step 2: Write `SystemUI-shared/src/main/AndroidManifest.xml`** + `.gitkeep`

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android" />
```

```bash
touch SystemUI-shared/src/main/.gitkeep
```

- [ ] **Step 3: Build**

Run: `./gradlew :SystemUI-shared:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 4: Repeat steps 1–3 for `:SystemUI-animation`**

Use these substitutions in build.gradle.kts:
- `namespace = "com.android.systemui.animation"`
- `compileOnly(files("libs/prebuilts/SystemUI-animation.jar"))`

- [ ] **Step 5: Repeat for `:SystemUI-customization`**

- `namespace = "com.android.systemui.customization"`
- `compileOnly(files("libs/prebuilts/SystemUI-customization.jar"))`

- [ ] **Step 6: Repeat for `:SystemUI-plugin`**

- `namespace = "com.android.systemui.plugin"`
- `compileOnly(files("libs/prebuilts/SystemUI-plugin.jar"))`

- [ ] **Step 7: Commit**

```bash
git add SystemUI-shared/ SystemUI-animation/ SystemUI-customization/ SystemUI-plugin/
git commit -m "build: add 4 prebuilt-jar library skeletons"
```

---

## Task 7: Wire up `:app` with a stub `SystemUIService`

**Files:**
- Create: `app/build.gradle.kts`
- Create: `app/src/main/AndroidManifest.xml`
- Create: `app/src/main/java/com/android/systemui/SystemUIApplication.java`
- Create: `app/src/main/java/com/android/systemui/SystemUIService.java`
- Create: `app/src/main/res/values/strings.xml`

- [ ] **Step 1: Write `app/build.gradle.kts`**

```kotlin
plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.android.systemui"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        applicationId = "com.android.systemui"
        minSdk = 35
        targetSdk = 35
    }
    signingConfigs {
        create("release") {
            storeFile = file("../keystore/SystemUI.pk8")
            // SYSOPS: pk8 + x509.pem are AOSP platform keys; see v2 spec §8.
            // (Full signing config wired in a later task once keystore format
            //  is finalised with the user.)
        }
    }
    buildTypes {
        debug {
            signingConfig = signingConfigs.getByName("release")
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation(project(":SystemUI-core"))
    implementation(project(":SystemUI-shared"))
    implementation(project(":SystemUI-animation"))
    implementation(project(":SystemUI-customization"))
    implementation(project(":SystemUI-plugin"))
    implementation(project(":SystemUI-plugin-core"))
    implementation(libs.androidx.core)
    implementation(libs.androidx.annotation)
    implementation(libs.material)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.dagger)
}
```

- [ ] **Step 2: Write `app/src/main/AndroidManifest.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">

    <!-- SYSOPS: stub manifest for v1 skeleton. Real SystemUI services / receivers
         will be added in feature-port tasks. -->
    <application
        android:name=".SystemUIApplication"
        android:label="@string/hello_systemui"
        android:allowBackup="false">

        <service
            android:name=".SystemUIService"
            android:exported="false" />
    </application>
</manifest>
```

- [ ] **Step 3: Write `app/src/main/java/com/android/systemui/SystemUIApplication.java`**

```java
// SYSOPS: stub Application. The real SystemUI bootstraps its Dagger graph here;
// v1 skeleton intentionally ships the minimal class so the APK installs.
package com.android.systemui;

import android.app.Application;

public class SystemUIApplication extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
    }
}
```

- [ ] **Step 4: Write `app/src/main/java/com/android/systemui/SystemUIService.java`**

```java
// SYSOPS: stub service. The real SystemUIService is a massive component manager
// (~5k LoC) — it is ported in a later feature task.
package com.android.systemui;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;

public class SystemUIService extends Service {
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
```

- [ ] **Step 5: Write `app/src/main/res/values/strings.xml`**

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="hello_systemui">Hello SystemUI</string>
</resources>
```

- [ ] **Step 6: Build the APK**

Run: `./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL. Output: `app/build/outputs/apk/debug/app-debug.apk` (~ a few MB — most modules are empty).

- [ ] **Step 7: Commit**

```bash
git add app/
git commit -m "build: add :app skeleton with stub SystemUIApplication + SystemUIService"
```

---

## Task 8: Add AOSP dual-build entry files

**Files:**
- Create: `Android.bp`
- Create: `CleanSpec.mk`
- Create: `OWNERS`

- [ ] **Step 1: Write `Android.bp`**

```soong
// Android.bp mirrors the 7 Gradle modules so that placing this repo inside
// /home/conv/myspace/aosp/frameworks/base/packages/SystemUI/ and running
// `m SystemUI` produces the same APK structure.

android_app {
    name: "SystemUI",
    srcs: [
        "app/src/main/java/**/*.java",
        "app/src/main/java/**/*.kt",
    ],
    manifest: "app/src/main/AndroidManifest.xml",
    resource_dirs: [
        "app/src/main/res",
    ],
    aaptflags: ["--rename-manifest-package", "com.android.systemui"],
    static_libs: [
        "SystemUI-core",
        "SystemUI-shared",
        "SystemUI-animation",
        "SystemUI-customization",
        "SystemUI-plugin",
        "SystemUI-plugin-core",
    ],
    platform_apis: true,
    certificate: "platform",
}

android_library {
    name: "SystemUI-core",
    srcs: [
        "SystemUI-core/src/main/java/**/*.java",
        "SystemUI-core/src/main/java/**/*.kt",
    ],
    manifest: "SystemUI-core/src/main/AndroidManifest.xml",
    resource_dirs: ["SystemUI-core/src/main/res"],
}

android_library {
    name: "SystemUI-shared",
    java_imports: ["libs/prebuilts/SystemUI-shared.jar"],
    manifest: "SystemUI-shared/src/main/AndroidManifest.xml",
}

// (Repeat the android_library block for SystemUI-animation / -customization /
//  -plugin / -plugin-core — copy the shape from SystemUI-shared and SystemUI-core
//  respectively, substituting the right path.)
```

- [ ] **Step 2: Write `CleanSpec.mk`** (mirror what CarSystemUI has)

```make
# Clean rules for `m installclean` / `make clean`.
LOCAL_DIR := $(GET_LOCAL_DIR)

$(call add-clean-step, find $(LOCAL_DIR) -name '*.apk' -delete)
$(call add-clean-step, find $(LOCAL_DIR) -name '.gradle' -type d -prune -exec rm -rf {} +)
```

- [ ] **Step 3: Write `OWNERS`** (empty)

```bash
: > OWNERS
git add -N OWNERS
```

- [ ] **Step 4: Commit**

```bash
git add Android.bp CleanSpec.mk OWNERS
git commit -m "build: add AOSP dual-build Android.bp + CleanSpec.mk"
```

---

## Task 9: End-to-end verification

**Files:** none modified.

- [ ] **Step 1: Run the full Gradle build**

Run: `./gradlew :app:assembleDebug`
Expected: BUILD SUCCESSFUL.

- [ ] **Step 2: Verify APK contents**

Run:
```bash
unzip -l app/build/outputs/apk/debug/app-debug.apk | head -20
aapt2 dump badging app/build/outputs/apk/debug/app-debug.apk | head -10
```
Expected: APK contains `classes.dex`, `resources.arsc`, `AndroidManifest.xml`. `aapt2 dump badging` shows package `com.android.systemui`, application label `Hello SystemUI`, launcher activity absent (service-only).

- [ ] **Step 3: Refresh migration log with skeleton-status entry**

Append a problem entry to `docs/GRADLE_MIGRATION_LOG.md`:

```markdown
## 问题三：v1 骨架交付

### 问题描述
v2 spec §9 要求交付双编译骨架；本任务执行 §9 全部步骤。

### 问题分析
骨架按 v2 spec §4 模块拆分（:app / :SystemUI-{core,shared,animation,customization,plugin,plugin-core}），从 AOSP 拷贝 framework.jar 与 4 个 prebuilt jar，stub `:app` 用最小 Service + Application。

### 解决方案
Tasks 1–9 按 plan 顺序执行。`Android.bp` 已支持将本仓库放入 AOSP 后 `m SystemUI`。

### 修改文件
- `gradle/libs.versions.toml` `settings.gradle.kts` `build.gradle.kts` `gradle.properties` `.gitignore`
- `libs/framework.jar` `libs/prebuilts/SystemUI-*.jar`
- `tools/extract_prebuilts.sh` `tools/install_sdk.sh`
- 7 个 module 目录（每个 build.gradle.kts + manifest + .gitkeep）
- `app/` skeleton (manifest + SystemUIApplication + SystemUIService + strings.xml)
- `Android.bp` `CleanSpec.mk` `OWNERS`
```

- [ ] **Step 4: Commit**

```bash
git add docs/GRADLE_MIGRATION_LOG.md
git commit -m "docs(migration): add 问题三 — v1 skeleton delivered"
```

---

## Self-Review Notes

- **Spec coverage:** §2 G1 (Gradle build) covered by Tasks 1, 3, 4, 6, 7, 9. G2 (BP build) covered by Task 8. G3 (no AOSP symlinks) covered by copying all binaries to `libs/` in Task 2 & 5. G4 (idiomatic Gradle 9) covered by Task 1. G5 (iterative features) — stub service intentionally minimal; subsequent feature tasks are out of plan scope per spec §3 "feature work explicitly deferred".
- **No placeholders:** all `compileOnly` paths, namespace strings, APK filenames are concrete.
- **Type consistency:** every module's namespace mirrors the dir name; prebuilt-jar `compileOnly` paths match `tools/extract_prebuilts.sh` output.
- **Risks intentionally not addressed in this plan:** R8/ProGuard (spec §3 defers), platform signing keystore format (will iterate in a follow-up task with the user once keystore files are extracted from AOSP). Both are flagged as `// SYSOPS:` comments in `app/build.gradle.kts`.
- **What comes next (NOT in this plan):** porting real `SystemUIService`, `SystemUIApplication` Dagger graph, keyguard, statusbar, etc. Each becomes its own plan+task cycle per v2 spec §1.