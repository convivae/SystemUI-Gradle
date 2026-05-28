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

// JD MOD: Only include modules that we compile from source
// Complex modules (shared, unfold, customization, animation, plugin) use prebuilt JARs
include(":app")
include(":plugin-core")
include(":common")
include(":utils")
include(":log")
