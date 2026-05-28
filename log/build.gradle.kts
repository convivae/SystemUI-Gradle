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
    implementation(project(":common"))
    implementation("com.google.errorprone:error_prone_annotations:2.28.0")

    // JD MOD: android.util.Log is needed for LogcatOnlyMessageBuffer
    compileOnly(files("$rootDir/libs/platform/android.jar"))
}
