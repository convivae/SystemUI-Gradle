plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
    id("kotlin-kapt")
}

// Configure compile tasks to use framework.jar before Android SDK
val frameworkJars = files(
    "${rootProject.projectDir}/libs/framework.jar",
    "${rootProject.projectDir}/libs/framework-statsd.jar"
)

gradle.projectsEvaluated {
    tasks.withType<JavaCompile>().configureEach {
        classpath = frameworkJars + classpath
    }
}

android {
    namespace = "com.android.systemui"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
        consumerProguardFiles("consumer-rules.pro")
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    // AGP 9.0+ 新 DSL 源码目录配置
    sourceSets {
        getByName("main") {
            java.srcDirs("src")
            res.srcDirs(
                listOf(
                    "res",
                    "res-keyguard"
                )
            )
            manifest.srcFile("AndroidManifest.xml")
        }
        getByName("debug") {
            java.srcDirs("src-debug")
        }
        getByName("release") {
            java.srcDirs("src-release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    kotlin {
        jvmToolchain(21)
    }

    lint {
        abortOnError = false
        checkReleaseBuilds = false
    }
}

// Configure kapt for Dagger (built-in in AGP 9.0+)
kapt {
    correctErrorTypes = true
    javacOptions {
        option("-J--add-opens=jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED")
    }
}

dependencies {
    // 项目模块
    implementation(project(":SystemUI-shared"))
    implementation(project(":SystemUI-plugin"))
    implementation(project(":SystemUI-plugin-core"))
    implementation(project(":SystemUI-animation"))
    implementation(project(":SystemUI-customization"))

    // Framework APIs
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/framework-statsd.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/android.car.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/WindowManager-Shell.jar"))
    compileOnly(files("${rootProject.projectDir}/libs/android_module_lib_stubs_current.jar"))

    // 本地 JAR
    implementation(files("${rootProject.projectDir}/libs/SystemUI-proto.jar"))
    implementation(files("${rootProject.projectDir}/libs/SystemUI-tags.jar"))
    implementation(files("${rootProject.projectDir}/libs/SystemUI-statsd.jar"))

    // 本地 Maven AAR
    implementation(libs.systemui.settingslib)
    implementation(libs.systemui.iconloader)
    implementation(libs.systemui.wmshell)
    implementation(libs.systemui.wifitrackerlib)

    // AndroidX
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.appcompat)
    implementation(libs.androidx.cardview)
    implementation(libs.androidx.concurrent.futures)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.constraintlayout.core)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.androidx.exifinterface)
    implementation(libs.androidx.fragment.ktx)
    implementation(libs.androidx.leanback)
    implementation(libs.androidx.leanback.preference)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)
    implementation(libs.androidx.mediarouter)
    implementation(libs.androidx.palette)
    implementation(libs.androidx.preference)
    implementation(libs.androidx.recyclerview)
    implementation(libs.androidx.slice.builders)
    implementation(libs.androidx.slice.core)
    implementation(libs.androidx.slice.view)
    implementation(libs.androidx.viewpager2)

    // Kotlin
    implementation(libs.kotlin.stdlib)
    implementation(libs.kotlinx.coroutines.android)
    implementation(libs.kotlinx.coroutines.core)

    // Dagger
    implementation(libs.dagger)
    kapt(libs.dagger.compiler)

    // 第三方库
    implementation(libs.guava)
    implementation(libs.lottie)
}
