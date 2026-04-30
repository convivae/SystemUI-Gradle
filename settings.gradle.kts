pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "SystemUI-Gradle"

enableFeaturePreview("TYPESAFE_PROJECT_ACCESSORS")

include(":app")
include(":shared")
include(":plugin")
include(":plugin-core")
include(":unfold")
include(":customization")
include(":animation")
include(":common")
include(":utils")
include(":log")
