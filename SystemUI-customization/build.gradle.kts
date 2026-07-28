plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.customization"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            manifest.srcFile("src/main/AndroidManifest.xml")
            // 从 AOSP SystemUI/customization/res 复制而来 (ids/dimens/attrs/strings 等)，
            // 让 lockscreen_clock_view / date_smartspace_view 等 id 被合并进 com.android.systemui.R
            res.srcDir("res")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    lint {
        abortOnError = false
    }
}

dependencies {
    // 注：完整复制源码包含 Compose、AndroidX、SystemUI 时钟等多个复杂依赖，
    //     编译工作量过大，保留为 prebuilt JAR 形式
    implementation(files("${rootProject.projectDir}/libs/prebuilts/SystemUICustomizationLib.jar"))
}