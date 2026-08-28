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
    // 资源合并所需的上游资源依赖（对齐 AOSP 17 SystemUI-res bp static_libs L415-427：
    // SystemUISharedLib, SystemUICustomizationLib, SettingsLib, WindowManager-Shell,
    // leanback, slice-core, slice-view, dynamiccolors, AccessibilityFloatingMenu-res）
    api(project(":SystemUI-shared"))
    api(project(":SystemUI-customization"))
    api(libs.systemui.settingslib)
    // SettingsLibSettingsTheme（独立 Soong target）：提供 settingslib_switch_{track,thumb} 等
    // SettingsTheme 专属资源；其与 SettingsLib/res 有 89 个同路径文件，禁止合并为单一 res root。
    // 17 bp 不在 SystemUI-res 顶层 static_libs（经 MainSwitchPreference 等 per-target 传递），
    // 但本地 POM per-target 骨架无传递边，维持显式 api（Task 072 记录）
    api(libs.systemui.settingslib.theme)
    // 17 bp 新增漂移修正（Task 072）：WindowManager-Shell（L421，16 遗留缺失）
    api(libs.systemui.wmshell)
    // 17 bp 新增漂移修正（Task 072）：dynamiccolors（L425，res-only，materialColor* 色板；
    // SystemUI-res 17 的 styles/colors/drawable-night 直接引用）。单 consumer →
    // 直接 AAR（Task 059 例外，tools/package_aosp_aar.py dynamiccolors）
    api(files("${rootProject.projectDir}/libs/aars/dynamiccolors.aar"))
    // 17 bp 新增（Task 072）：AccessibilityFloatingMenu-res → 源码模块
    api(project(":SystemUI-accessibility-floatingmenu-res"))
    api(libs.androidx.leanback)
    api(libs.androidx.slice.core)
    api(libs.androidx.slice.view)
}
