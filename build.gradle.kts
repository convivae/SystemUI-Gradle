plugins {
    id("com.android.application") version "9.2.0" apply false
    id("com.android.library") version "9.2.0" apply false
    id("org.jetbrains.kotlin.jvm") version "2.3.21" apply false
    id("com.google.protobuf") version "0.10.0" apply false
}

// JD MOD: Prepend framework.jar to all Java/Kotlin compile classpaths
// This ensures hidden platform APIs are accessible during compilation
gradle.projectsEvaluated {
    val frameworkJars = files(rootProject.file("libs/framework.jar"))
    subprojects {
        tasks.withType<JavaCompile>().configureEach {
            classpath = frameworkJars + classpath
        }
    }
}
