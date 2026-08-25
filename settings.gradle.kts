pluginManagement {
    repositories {
        maven { url = uri("https://mirrors.cloud.tencent.com/nexus/repository/maven-public/") }
        maven { url = uri("https://mirrors.cloud.tencent.com/nexus/repository/gradle-plugins/") }
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/gradle-plugin") }
        maven { url = uri("https://maven.aliyun.com/repository/public") }
        maven { url = uri("https://artifactory.jd.com/libs-releases-local/") }
        maven { url = uri("https://artifactory.jd.com/libs-snapshots-local/") }

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
        maven { url = uri("https://mirrors.cloud.tencent.com/nexus/repository/maven-public/") }
        maven { url = uri("https://maven.aliyun.com/repository/google") }
        maven { url = uri("https://maven.aliyun.com/repository/public") }
        maven { url = uri("https://artifactory.jd.com/libs-releases-local/") }
        maven { url = uri("https://artifactory.jd.com/libs-snapshots-local/") }

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
