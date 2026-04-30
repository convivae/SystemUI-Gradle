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
        java.srcDirs("$aospDir/frameworks/base/packages/SystemUI/log/src")
    }
}

dependencies {
    implementation(project(":common"))
    implementation("com.google.errorprone:error_prone_annotations:2.28.0")
}
