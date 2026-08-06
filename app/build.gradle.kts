// AOSP bp translation: frameworks/base/packages/SystemUI/Android.bp android_app "SystemUI"
// See docs/adr/0003-app-module-aligns-aosp-bp.md for full rationale.

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
}

android {
    // AGP namespace vs AOSP package: AOSP soong has no namespace concept,
    // but AGP requires every module to have a unique namespace.
    // Strategy (per ref CarSystemUIGradle pattern): :app is the APK producer
    // so it gets a distinct namespace; :SystemUI-core keeps com.android.systemui
    // so its internal `import com.android.systemui.R` continues to resolve
    // (aapt2 generates R.jar in :SystemUI-core's namespace).
    // applicationId stays "com.android.systemui" — that's the AOSP APK id.
    namespace = "com.android.systemui.app"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        applicationId = "com.android.systemui"
        minSdk = 35
        targetSdk = 35
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    // AOSP bp: kotlincflags: ["-Xjvm-default=all"]
    kotlinOptions {
        freeCompilerArgs = listOf("-Xjvm-default=all")
    }
    // AOSP bp: defaults: [platform_app_defaults, SystemUI_optimized_defaults, wmshell_defaults]
    //   - platform_app_defaults: soong-only (platform-level)
    //   - SystemUI_optimized_defaults: conditional R8 (controlled via optimize block below)
    //   - wmshell_defaults: depends on frameworks/libs/wm-shelling — not yet ported
    // AOSP bp: system_ext_specific: true, privileged: true
    //   - platform-only permissions, no Gradle equivalent (handled at sign/manifest merge)
    signingConfigs {
        create("release") {
            storeFile = file("../keystore/platform.keystore")
            storePassword = "android"
            keyAlias = "androiddebugkey"
            keyPassword = "android"
        }
    }
    buildTypes {
        // AOSP bp: certificate: "platform" → signed with platform keystore (debug + release)
        debug {
            // SYSOPS: platform-signed so the APK is installable as a system app.
            // See v2 spec §11.7 risk #10. To regenerate keystore, run
            // tools/install_keystore.sh.
            signingConfig = signingConfigs.getByName("release")
            // AOSP bp: optimize.proguard_flags_files: ["proguard.flags"]
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard.flags"
            )
        }
        release {
            signingConfig = signingConfigs.getByName("release")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard.flags"
            )
        }
    }
    // AOSP bp: dxflags: ["--multi-dex"] → automatic with minSdk 21+, no flag needed
    // AOSP bp: use_resource_processor: true → automatic with AGP aapt2
}

// AOSP bp static_libs: ["SystemUI-core"]
// Only direct dep on :SystemUI-core; transitive submodules (shared/animation/
// customization/common/log/unfold/plugin/plugin-core) are pulled in by core's
// own static_libs. Do NOT add them here — it would create duplicate classes.
dependencies {
    implementation(project(":SystemUI-core"))
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/WindowManager-Shell.jar"))
    // tier③ bp public maven deps (subset needed at app level)
    implementation(libs.androidx.core)
    implementation(libs.androidx.annotation)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.dagger)
}
