plugins {
    id("java-library")
    id("org.jetbrains.kotlin.jvm")
    id("org.jetbrains.kotlin.kapt")
}

val aospDir: String by project

java {
    sourceCompatibility = JavaVersion.VERSION_1_8
    targetCompatibility = JavaVersion.VERSION_1_8
}

kotlin {
    jvmToolchain(17)
}

sourceSets {
    main {
        java.srcDirs(
            "$aospDir/frameworks/base/packages/SystemUI/plugin_core/src"
        )
        // Exclude annotation processor sources — they go in a separate source set
        exclude("**/processor/**")
    }
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.0.21")
    implementation("androidx.annotation:annotation:1.8.2")

    // Auto-service for annotation processor
    kapt("com.google.auto.service:auto-service:1.1.1")
    implementation("com.google.auto.service:auto-service-annotations:1.1.1")
    implementation("com.google.auto:auto-common:1.2.2")
    implementation("com.google.guava:guava:33.2.1-jre")
    implementation("javax.inject:javax.inject:1")
}
