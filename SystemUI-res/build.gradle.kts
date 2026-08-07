// :SystemUI-res — SystemUI 资源 namespace 模块（com.android.systemui.res.R）
// 959 个源码文件显式 import com.android.systemui.res.R，故资源必须独立 namespace
plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.res"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // 仅资源，无 Java/Kotlin 源码
    sourceSets {
        getByName("main") {
            res.srcDirs("res-product", "res-keyguard", "res")
            manifest.srcFile("AndroidManifest.xml")
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
    // 资源合并所需的上游资源依赖（对齐 AOSP res 的 resource_dirs）
    api(project(":SystemUI-shared"))
    api(project(":SystemUI-customization"))
    api(files("${rootProject.projectDir}/libs/aars/SettingsLib.aar"))
    api(libs.androidx.leanback)
    api(libs.androidx.slice.core)
    api(libs.androidx.slice.view)
}
