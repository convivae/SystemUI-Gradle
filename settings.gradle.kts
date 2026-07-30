pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    id("com.android.application") version "9.2.0" apply false
    id("com.android.library") version "9.2.0" apply false
    id("org.jetbrains.kotlin.android") version "2.1.0" apply false
    id("org.jetbrains.kotlin.jvm") version "2.1.0" apply false
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
        maven { url = uri("${rootProject.projectDir}/libs/maven") }
    }
}

rootProject.name = "SystemUI"
include(":app")
include(":SystemUI-core")
include(":SystemUI-shared")
include(":SystemUI-animation")
include(":SystemUI-customization")
include(":SystemUI-plugin")
include(":SystemUI-plugin-core")
include(":SystemUI-common")
include(":SystemUI-log")
include(":SystemUI-unfold")
include(":SystemUI-animationlib")

// AOSP bp 1:1 新增子模块 (Phase A 脚手架)
// utils/kairos/ → kairos
include(":SystemUI-utils-kairos")
// compose/core/ → PlatformComposeCore
include(":SystemUI-compose-core")
// compose/scene/ → PlatformComposeSceneTransitionLayout
include(":SystemUI-compose-scene")
// shared/biometrics/ → BiometricsSharedLib
include(":SystemUI-shared-biometrics")
// shared/keyguard/ → SystemUISharedLib-Keyguard
include(":SystemUI-shared-keyguard")
// SystemUI-proto (顶层 bp java_library)
include(":SystemUI-proto")
// pods/com/android/systemui/dagger/ (api)
include(":SystemUI-pods-dagger")
// pods/com/android/systemui/retail/ (impl)
include(":SystemUI-pods-retail")
// pods/com/android/systemui/retail/data/ (api+impl 合并)
include(":SystemUI-pods-data")
// pods/com/android/systemui/retail/domain/ (api+impl 合并)
include(":SystemUI-pods-domain")
// pods/com/android/systemui/util/settings/ (api)
include(":SystemUI-pods-settings")
