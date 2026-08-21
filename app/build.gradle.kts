// AOSP bp translation: frameworks/base/packages/SystemUI/Android.bp android_app "SystemUI"
// See docs/adr/0003-app-module-aligns-aosp-bp.md for full rationale.

plugins {
    alias(libs.plugins.android.application)
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
            // SystemUI-plugin-core 是 JVM library（无 AGP consumer DSL），其 AOSP
            // plugin_core/proguard.flags（export_proguard_flags_files: true）由 app
            // 直接接入（Task 029 R3；规则文件归 module 所有，不改模块类型）。
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard.flags",
                rootProject.file("SystemUI-plugin-core/proguard.flags")
            )
        }
        release {
            // Task 030 (R1+R2): AOSP SystemUI_optimized_defaults (SYSTEMUI_OPTIMIZE_JAVA=true
            // default, non-eng): optimize + shrink + shrink_resources. User approved
            // 2026-08-20. R8 full-mode left at AGP 9.3.1 default (no explicit switch).
            isMinifyEnabled = true
            isShrinkResources = true
            signingConfig = signingConfigs.getByName("release")
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard.flags",
                // Task 044 (option A): narrow Gradle-native adapter closing the sole
                // R8 missing ref (build/optimizer-only aconfig annotation).
                "proguard_gradle.flags",
                rootProject.file("SystemUI-plugin-core/proguard.flags")
            )
        }
    }
    // AOSP bp: dxflags: ["--multi-dex"] → automatic with minSdk 21+, no flag needed
    // AOSP bp: use_resource_processor: true → automatic with AGP aapt2
    // WM-Shell AAR manifest uses android:featureFlag (AOSP original); supply the
    // flag to aapt2 link. See docs/architecture/2026-08-13-aapt-feature-flags-options.md
    androidResources {
        additionalParameters(
            "--feature-flags",
            "com.android.wm.shell.enable_retrievable_bubbles=true"
        )
    }
}

// AOSP bp: kotlincflags: ["-Xjvm-default=all"]
// Kotlin 由 AGP builtInKotlin=true 提供；用顶层 kotlin { compilerOptions { } } 配置编译参数
kotlin {
    compilerOptions {
        freeCompilerArgs.add("-Xjvm-default=all")
    }
}

// Preserve xmlns:androidprv through the AGP resource pipeline (task 012).
//
// AGP 9.3.1 MergeResources reserializes merged values XML and drops the
// xmlns:androidprv declaration (the prefix only occurs inside attribute
// VALUES, so serializers consider it unused), leaving 81 androidprv:
// references unresolvable at AAPT2 link time. AGP 9.3.1 exposes no public
// transformable merged-resource artifact (SingleArtifact has no MERGED_RES;
// MultipleArtifact only exposes multidex/native-debug-metadata/symbol-tables/
// pre-compilation-classes — audited 2026-08-13, see
// docs/architecture/2026-08-13-agp-androidprv-namespace-fix.md), so the
// smallest build-only repair is a narrowly ordered post-merge/pre-link task:
// it patches TEMPORARY copies of the affected merged values XML, recompiles
// them with AGP's own aapt2 (sdkComponents.aapt2), and atomically replaces
// only the matching .arsc.flat intermediates. AOSP source resources and the
// merger's own XML are never modified. The task deliberately does NOT claim
// ownership of AGP's output directories.
androidComponents {
    onVariants { variant ->
        val cap = variant.name.replaceFirstChar { it.uppercase() }
        val mergeTaskName = "merge${cap}Resources"
        val processTaskName = "process${cap}Resources"
        val patchTaskName = "patch${cap}AndroidPrvMergedResources"
        // AGP-internal intermediate layout (audited on this AGP version):
        //   intermediates/incremental/<variant>/merge<Variant>Resources/merged.dir (merger XML)
        //   intermediates/merged_res/<variant>/merge<Variant>Resources           (compiled flats)
        val mergedDir = layout.buildDirectory.dir(
            "intermediates/incremental/${variant.name}/$mergeTaskName/merged.dir")
        val compiledDir = layout.buildDirectory.dir(
            "intermediates/merged_res/${variant.name}/$mergeTaskName")
        val aapt2Provider = sdkComponents.aapt2
        val patchScript = "$rootDir/tools/patch_androidprv_merged_resources.py"

        val patchTask = tasks.register<Exec>(patchTaskName) {
            group = "Resource Repair"
            description =
                "Re-inject xmlns:androidprv into merged values flats ($cap)"
            dependsOn(mergeTaskName)
            // Providers are resolved at execution time; Exec reads the
            // command line in its task action, after doFirst has run.
            doFirst {
                commandLine(
                    "python3", patchScript,
                    "--merged-dir", mergedDir.get().asFile.absolutePath,
                    "--compiled-dir", compiledDir.get().asFile.absolutePath,
                    "--aapt2", aapt2Provider.get().executable.get().asFile.absolutePath,
                )
            }
        }
        tasks.matching { it.name == processTaskName }
            .configureEach { dependsOn(patchTask) }
    }
}

// AOSP bp static_libs: ["SystemUI-core"]
// Only direct dep on :SystemUI-core; transitive submodules (shared/animation/
// customization/common/log/unfold/plugin/plugin-core) are pulled in by core's
// own static_libs. Do NOT add them here — it would create duplicate classes.
dependencies {
    implementation(project(":SystemUI-core"))
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // tier③ bp public maven deps (subset needed at app level)
    implementation(libs.androidx.core)
    implementation(libs.androidx.annotation)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.dagger)
}
