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
    id("org.jetbrains.kotlin.android") version "1.9.22" apply false
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
