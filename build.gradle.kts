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
            file("${rootProject.projectDir}/libs/monet.jar")
        ).filter { it.exists() }
        val serverNotificationFlagsJar = file("${rootProject.projectDir}/libs/maven/com/android/server/notification-flags/1.0.0/notification-flags-1.0.0.jar")
        tasks.withType<JavaCompile>().configureEach {
            if (frameworkJar.exists()) {
                options.bootstrapClasspath = files(frameworkJar) + files(
                    options.bootstrapClasspath?.files ?: emptySet<File>()
                )
                classpath = files(frameworkJar) + classpath
            }
            // 添加 internalFlagsJars 到 JavaCompile (供 kotlin 的 javac 调用)
            classpath = files(internalFlagsJars) + classpath
            if (serverNotificationFlagsJar.exists()) {
                classpath = files(serverNotificationFlagsJar) + classpath
            }
        }
        // KotlinCompile: libraries.from() 是 kotlin 编译的 classpath
        // 但 kotlin android plugin 在 KotlinCompile 任务之外还使用 javac，
        // 所以也需要把 jar 加到 JavaCompile (KotlinCompile 间接依赖)
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            // internalFlagsJars 必须在 framework.jar 之前加载
            // 否则 framework.jar 的同名 stub 会遮蔽 internalFlagsJars
            if (serverNotificationFlagsJar.exists()) {
                libraries.from(serverNotificationFlagsJar)
            }
            libraries.from(internalFlagsJars)
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
