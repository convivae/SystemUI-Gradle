plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.shared"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        minSdk = 35
    }
    
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
}

// 注：SystemUISharedLib 内容在 :SystemUI-core 直接使用 compileOnly
dependencies {
}
