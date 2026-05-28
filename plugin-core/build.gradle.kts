plugins {
    id("java-library")
    id("org.jetbrains.kotlin.jvm")
}

java {
    sourceCompatibility = JavaVersion.VERSION_21
    targetCompatibility = JavaVersion.VERSION_21
}

kotlin {
    jvmToolchain(21)
}

sourceSets {
    main {
        java.srcDirs("src")
    }
}

dependencies {
    implementation("org.jetbrains.kotlin:kotlin-stdlib:2.3.21")
    implementation("androidx.annotation:annotation:1.8.2")

    // Auto-service for annotation processor
    annotationProcessor("com.google.auto.service:auto-service:1.1.1")
    implementation("com.google.auto.service:auto-service-annotations:1.1.1")
    implementation("com.google.auto:auto-common:1.2.2")
    implementation("com.google.guava:guava:33.2.1-jre")
    implementation("javax.inject:javax.inject:1")
}
