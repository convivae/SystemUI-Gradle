plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.plugin.core"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}
