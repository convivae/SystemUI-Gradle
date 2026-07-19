plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.animation"
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
    // 使用清理后的 prebuilt JAR（AOSP 编译产物）
    // 注：完整复制源码需要解决 flags_lib、ShellTransitions 等大量 AOSP 内部依赖，
    //     因此保留为 prebuilt JAR 形式，确保主流程畅通
    implementation(files("${rootProject.projectDir}/libs/prebuilts/PlatformAnimationLib.jar"))
}