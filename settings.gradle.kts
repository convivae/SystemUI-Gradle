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
        // Local prebuilt AARs / JARs (e.g. SystemUI-shared.jar) referenced via flatDir or libs/ tree
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
