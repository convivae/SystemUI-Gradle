plugins {
    alias(libs.plugins.android.library)
}

android {
    namespace = "com.android.systemui.core"
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
    implementation(libs.androidx.core)
    implementation(libs.androidx.annotation)
}
