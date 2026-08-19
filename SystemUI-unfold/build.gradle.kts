plugins {
    alias(libs.plugins.android.library)
    id("com.google.devtools.ksp")
}

android {
    namespace = "com.android.systemui.unfold"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // 对齐 AOSP SystemUIUnfoldLib：src 含 kotlin/aidl
    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            kotlin.srcDirs("src")
            aidl.srcDirs("src")
            manifest.srcFile("AndroidManifest.xml")
        }
    }

    buildFeatures {
        aidl = true
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
    // androidx.dynamicanimation：官方 1.1.0（tier③；task 027 弃用本地 alpha04 prebuilt——
    // 审计已证两者 class 清单完全一致，消除编译/运行版本混挂）。作 compileOnly，
    // 运行时由 app 提供的真实 androidx 提供
    compileOnly(libs.androidx.dynamicanimation)

    // Dagger 组件（DaggerUnfold/RemoteUnfoldSharedComponent）由 KSP 在本项目内生成。
    // 对齐 core：Dagger 2.59.2 + useBindingGraphFix 默认启用（2.58+）。
    ksp(libs.dagger.compiler)

    // tier③ 标准第三方（maven 版本依赖，对齐 bp static_libs）
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation(libs.dagger)
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.core)
    implementation(libs.kotlinx.coroutines.android)
}
