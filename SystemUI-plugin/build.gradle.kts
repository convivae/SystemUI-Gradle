plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.plugin"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    // SYSOPS: AOSP produces SystemUIPluginLib.jar. See 问题五.
    compileOnly(files("${rootProject.projectDir}/libs/prebuilts/SystemUIPluginLib.jar"))
}
