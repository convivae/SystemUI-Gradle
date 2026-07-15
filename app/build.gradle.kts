plugins {
    alias(libs.plugins.android.application)
}

android {
    namespace = "com.android.systemui"
    compileSdkPreview = "SysUISdk"
    defaultConfig {
        applicationId = "com.android.systemui"
        minSdk = 35
        targetSdk = 35
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    buildTypes {
        debug {
            // SYSOPS: debug build uses AGP auto-generated debug key.
            // Platform signing (platform.pk8 + x509.pem) deferred to follow-up task.
        }
    }
}

dependencies {
    implementation(project(":SystemUI-core"))
    implementation(project(":SystemUI-shared"))
    implementation(project(":SystemUI-animation"))
    implementation(project(":SystemUI-customization"))
    implementation(project(":SystemUI-plugin"))
    implementation(project(":SystemUI-plugin-core"))
    implementation(libs.androidx.core)
    implementation(libs.androidx.annotation)
    implementation(libs.material)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.dagger)
}
