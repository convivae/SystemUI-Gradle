plugins {
    id("com.android.application") apply false
    id("com.android.library") apply false
}

// Inject framework.jar into every Java/Kotlin compile so hidden platform APIs resolve.
// SYSOPS: AOSP-only `framework.jar` provides hidden APIs not in public SDK.
allprojects {
    gradle.projectsEvaluated {
        val frameworkJar = file("${rootProject.projectDir}/libs/framework.jar")
        tasks.withType<JavaCompile>().configureEach {
            if (frameworkJar.exists()) {
                options.bootstrapClasspath = files(frameworkJar) + files(
                    options.bootstrapClasspath?.files ?: emptySet<File>()
                )
                classpath = files(frameworkJar) + classpath
            }
        }
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            if (frameworkJar.exists()) {
                libraries.from(frameworkJar)
            }
        }
        // 配置 Kotlin compilation 的 jvmTarget
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            compilerOptions {
                jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
            }
        }
    }
}
