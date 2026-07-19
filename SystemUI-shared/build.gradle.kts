plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.shared"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            manifest.srcFile("src/main/AndroidManifest.xml")
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
    // 注：完整复制源码需要解决 BiometricsSharedLib、SystemUIUnfoldLib、PluginCoreLib
    //     等大量 AOSP 内部依赖，工作量过大，保留为 prebuilt JAR 形式
    implementation(files("${rootProject.projectDir}/libs/prebuilts/SystemUISharedLib.jar"))
}