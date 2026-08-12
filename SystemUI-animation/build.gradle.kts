plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.animation"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // 对齐 AOSP PlatformAnimationLib：src 含 java/kotlin，res 目录
    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            kotlin.srcDirs("src")
            res.srcDirs("res")
            manifest.srcFile("AndroidManifest.xml")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    kotlin {
        jvmToolchain(21)
    }

    lint {
        abortOnError = false
    }
}

// AGP builtInKotlin：用顶层 kotlin { compilerOptions { } } 替代废弃的 android.kotlinOptions { }
// 对齐 AOSP kotlincflags: ["-Xjvm-default=all"]
kotlin {
    compilerOptions {
        freeCompilerArgs.add("-Xjvm-default=all")
    }
}

dependencies {
    // Framework APIs（allprojects 已注入，此处显式声明便于阅读）
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))

    // tier② AOSP 特有产物 jar
    compileOnly(libs.systemui.wmshell)
    compileOnly(libs.systemui.wmshell.shared)
    // animationlib（frameworks/libs/systemui:animationlib，提供 com.android.app.animation.*）
    // 直接 AAR（含 res），替代旧 animationlib.jar
    api(libs.systemui.animationlib)
    // com.android.systemui.Flags（aconfig）
    compileOnly(files("${rootProject.projectDir}/libs/systemui-flags.jar"))
    // com.android.systemui.shared.Flags（aconfig，shared_flags_lib）
    compileOnly(files("${rootProject.projectDir}/libs/systemui-shared-flags.jar"))

    // tier③ 标准第三方（maven 版本依赖）
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.core.animation)
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)
}
