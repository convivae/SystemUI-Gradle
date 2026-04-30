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
        java.srcDirs("$aospDir/frameworks/base/packages/SystemUI/utils/src")
    }
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.3.21")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.1")
}
