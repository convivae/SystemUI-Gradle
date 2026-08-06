// :SystemUI-plugin — SystemUIPluginLib runtime（含 bcsmartspace）
// KAPT 跑 :SystemUI-plugin-processor 生成 PluginProtector（BP 排除 PluginProtectorStub.kt）
plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.kapt)
}

android {
    namespace = "com.android.systemui.plugin"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("src", "bcsmartspace/src")
            kotlin.srcDirs("src", "bcsmartspace/src")
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

dependencies {
    // Framework APIs - provided by system at runtime
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))

    // build-time 注解处理器（生成 PluginProtector）
    kapt(project(":SystemUI-plugin-processor"))

    // tier① SystemUI 自有源码模块
    api(project(":SystemUI-plugin-core"))
    api(project(":SystemUI-animation"))
    api(project(":SystemUI-common"))

    // AndroidX
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.androidx.recyclerview)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.kotlin.stdlib)
}
