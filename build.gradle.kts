plugins {
    id("com.android.application") apply false
    id("com.android.library") apply false
    // KSP：用于跑 Dagger/Room 注解处理器（KAPT 1.9+ 与 Gradle 9.5 不兼容，改用 KSP）
    // KSP 2.3.11（新独立版本号，对齐 Kotlin 2.3.21）
    id("com.google.devtools.ksp") version "2.2.10-2.0.2" apply false
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
            // 把 server notification flags jar 放在 classpath 前面 (优先解析)
            // 否则 framework.jar 同名 stub 会遮蔽它
            if (serverNotificationFlagsJar.exists()) {
                classpath = files(serverNotificationFlagsJar) + classpath
            }
            // 添加 internalFlagsJars 到 JavaCompile (供 kotlin 的 javac 调用)
            classpath = files(internalFlagsJars) + classpath
            if (serverNotificationFlagsJar.exists()) {
                classpath = files(serverNotificationFlagsJar) + classpath
            }
        }
        // KotlinCompile: do NOT add framework.jar here. It pollutes the Compose runtime's
        // inline metadata lookup (Kotlin can't find inline bodies for CompositionLocal.getCurrent,
        // remember, etc., giving "Couldn't inline method call" internal errors).
        // framework.jar is added only to JavaCompile.classpath above for Java code; Kotlin code
        // sees the same hidden-API classes via SDK SysUISdk merge + AGP's automatic classpath.
        tasks.withType<org.jetbrains.kotlin.gradle.tasks.KotlinCompile>().configureEach {
            compilerOptions {
                jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_21)
            }
        }
    }
}
