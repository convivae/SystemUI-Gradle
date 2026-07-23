plugins {
    id("com.android.application") apply false
    id("com.android.library") apply false
}

// Inject framework.jar + internal flags jars into every Java/Kotlin compile.
// SYSOPS: AOSP-only jars provide hidden APIs (aconfig Flags, @hide classes).
allprojects {
    gradle.projectsEvaluated {
        val frameworkJar = file("${rootProject.projectDir}/libs/framework.jar")
        val internalFlagsJars = listOf(
            file("${rootProject.projectDir}/libs/systemui-flags.jar"),
            file("${rootProject.projectDir}/libs/server-notification-flags.jar"),
            file("${rootProject.projectDir}/libs/monet.jar")
        ).filter { it.exists() }
        tasks.withType<JavaCompile>().configureEach {
            if (frameworkJar.exists()) {
                options.bootstrapClasspath = files(frameworkJar) + files(
                    options.bootstrapClasspath?.files ?: emptySet<File>()
                )
                classpath = files(frameworkJar) + classpath
            }
            classpath = files(internalFlagsJars) + classpath
        }
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            if (frameworkJar.exists()) {
                libraries.from(frameworkJar)
            }
            libraries.from(internalFlagsJars)
        }
        // 配置 Kotlin compilation 的 jvmTarget
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            compilerOptions {
                jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
            }
        }
    }
}
