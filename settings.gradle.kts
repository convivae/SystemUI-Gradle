pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

plugins {
    id("com.android.application") version "9.3.1" apply false
    id("com.android.library") version "9.3.1" apply false
    id("org.jetbrains.kotlin.jvm") version "2.2.10" apply false
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
include(":SystemUI-common")
include(":SystemUI-animation")
include(":SystemUI-plugin-core")
include(":SystemUI-plugin-processor")
include(":SystemUI-plugin")
include(":SystemUI-unfold")
include(":SystemUI-customization")
include(":SystemUI-shared")
include(":SystemUI-shared-biometrics")
include(":SystemUI-compose")
