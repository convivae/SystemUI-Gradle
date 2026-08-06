// :SystemUI-plugin — SystemUIPluginLib runtime（含 bcsmartspace）
// javac 原生注解处理（不用 KAPT/KSP）：在 JavaCompile 上配 annotationProcessorPath
// ⚠️ 待办：全部 @ProtectedInterface 标注在 .kt 文件上，javac 原生处理器看不到 Kotlin 源码，
//    PluginProtector 暂不生成，下游 Unresolved reference 作为保留错误（见 Task 9 记录）
plugins {
    alias(libs.plugins.android.library)
    alias(libs.plugins.kotlin.android)
}

android {
    namespace = "com.android.systemui.plugin"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            java.srcDirs("src", "bcsmartspace/src")
            kotlin.srcDirs("src", "bcsmartspace/src")
            manifest.srcFile("AndroidManifest.xml")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }

    kotlin {
        jvmToolchain(21)
    }

    lint {
        abortOnError = false
    }
}

// javac 原生注解处理：把 processor 模块的 jar 加到 JavaCompile 的 annotationProcessorPath。
// processor 模块是 JVM `java-library`，jar task 产出含服务描述符的 processor jar。
// ⚠️ 待办：javac 看不到 .kt 源码，PluginProtector 暂不生成。
tasks.withType<JavaCompile>().configureEach {
    dependsOn(":SystemUI-plugin-processor:jar")
    doFirst {
        val jarTask = project(":SystemUI-plugin-processor")
            .tasks.named<org.gradle.jvm.tasks.Jar>("jar").get()
        options.annotationProcessorPath = files(jarTask.archiveFile)
    }
}

dependencies {
    // Framework APIs - provided by system at runtime
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))

    // build-time 注解处理器（javac 原生，见上方配置）
    annotationProcessor(project(":SystemUI-plugin-processor"))

    // tier① SystemUI 自有源码模块
    api(project(":SystemUI-plugin-core"))
    api(project(":SystemUI-animation"))
    api(project(":SystemUI-common"))

    // AndroidX
    implementation(libs.androidx.annotation)
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.dynamicanimation)
    implementation(libs.androidx.recyclerview)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.kotlin.stdlib)
}
