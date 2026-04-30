plugins {
    id("java-library")
    id("org.jetbrains.kotlin.jvm")
}

val aospDir: String by project

java {
    sourceCompatibility = JavaVersion.VERSION_17
    targetCompatibility = JavaVersion.VERSION_17
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    main {
        java.srcDirs("$aospDir/frameworks/base/packages/SystemUI/common/src")
    }
}

dependencies {
    implementation(project(":utils"))
    implementation(files("$rootDir/libs/tracinglib-platform.jar"))
}
