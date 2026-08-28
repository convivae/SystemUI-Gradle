// :SystemUI-accessibility-floatingmenu-res — AOSP 17 res-only 模块
// "AccessibilityFloatingMenu-res"（主 bp L415-427 SystemUI-res static_libs 消费；
// 源 = packages/SystemUI/accessibility/accessibilitymenu/res）。
// 无 srcs，仅 res + manifest（AOSP AndroidManifest-floatingmenu.xml 已按 AGP 惯例
// 改名放模块根，字节一致）。R 类由 AGP 从资源生成。

plugins {
    alias(libs.plugins.android.library)
}

android {
    // 与 AOSP manifest package 一致（manifest 保留 package 属性 → AGP 仅警告，值与 namespace 相等）
    namespace = "com.android.systemui.accessibility.floatingmenu"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    // 仅资源，无 Java/Kotlin 源码
    sourceSets {
        getByName("main") {
            res.srcDirs("res")
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
    // res-only：无依赖（bp 亦无 static_libs）
}
