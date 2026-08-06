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
include(":SystemUI-res")
include(":SystemUI-shared")
include(":SystemUI-animation")
include(":SystemUI-customization")
include(":SystemUI-plugin")
include(":SystemUI-plugin-core")
include(":SystemUI-common")
include(":SystemUI-unfold")

// AOSP bp 1:1 新增子模块 (Phase A 脚手架)
// compose/core + compose/scene → SystemUI-compose（合并）
include(":SystemUI-compose")
// shared/biometrics/ → BiometricsSharedLib
include(":SystemUI-shared-biometrics")
