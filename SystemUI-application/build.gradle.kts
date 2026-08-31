// :SystemUI-application — AOSP 17 android_library "SystemUI-application"
// (frameworks/base/packages/SystemUI/Android.bp L599-620)：
//   srcs: ["application/src/**/*.java", "application/src/**/*.kt"]（4 文件，
//   Dagger 根组件 ReferenceGlobalRootComponent/ReferenceSysUIComponent +
//   PhoneSystemUIAppComponentFactory + SystemUIInitializerImpl）
//   static_libs: ["SystemUI-core", "com.android.systemui.bundle.phone_dagger", "dagger2"]
//   enable_ksp + dagger annotation_processor_flags（见下方 ksp{}）
//   manifest: "AndroidManifest.xml" = AOSP 顶层 1338 行完整 manifest
// phone_dagger bundle 的 pods 已并入 :SystemUI-core（pods srcDir），此处不再单列。
// 16 时代 :app 1158 行完整 manifest 的角色由本模块接管（Task 072 / C4）。

plugins {
    alias(libs.plugins.android.library)
    id("com.google.devtools.ksp")
}

android {
    // namespace = AOSP manifest package（com.android.systemui）。17 manifest 的组件名全部是
    // 相对名（".SystemUIService"、".application.impl.SystemUIApplicationImpl" 等），ManifestMerger2
    // 对 package-dependent 属性按模块 namespace 展开相对名（manifest-merger 32.3.1
    // XmlAttribute.checkAndExpandPlaceHolder），故必须等于 AOSP manifest package 才能得到正确的
    // com.android.systemui.* FQCN（16 时代 Task 050 的 79 处手工 FQCN 改写由此免掉）。
    // 由于 AGP merger 的 unique-namespace 检查（ENFORCE_UNIQUE_PACKAGE_NAMES，默认开启）禁止
    // 闭包内两个模块同 namespace，:SystemUI-core 的 namespace 已改为 com.android.systemui.core
    // （core 无 res/BuildConfig/R 引用、manifest 无相对组件名，该标签不承载 AOSP 语义）。
    namespace = "com.android.systemui"
    compileSdkPreview = "SysUISdk"

    defaultConfig {
        minSdk = 32
    }

    sourceSets {
        getByName("main") {
            // AOSP application/src/**/*.java|kt（src 下另有 main/AndroidManifest.xml，
            // 由 manifest.srcFile 显式接管，不作为源码目录内容参与编译）
            java.srcDirs("src")
            kotlin.srcDirs("src")
            manifest.srcFile("src/main/AndroidManifest.xml")
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
        checkReleaseBuilds = false
    }
}

// AGP builtInKotlin：顶层 kotlin { compilerOptions { } }
// 对齐 bp SystemUI-srcs-defaults kotlincflags: ["-Xjvm-default=all", "-opt-in=..."]
kotlin {
    compilerOptions {
        freeCompilerArgs.addAll(
            "-Xjvm-default=all",
            "-opt-in=kotlinx.coroutines.ExperimentalCoroutinesApi",
        )
    }
}

// KSP 跑 Dagger（对齐 bp enable_ksp + plugins dagger2-compiler）。
// annotation_processor_flags 逐条镜像 bp L612-618：
ksp {
    arg("dagger.fastInit", "enabled")
    arg("dagger.explicitBindingConflictsWithInject", "ERROR")
    arg("dagger.strictMultibindingValidation", "enabled")
    // Dagger 2.59.2 起 useBindingGraphFix 默认启用（与 :SystemUI-core 注释一致），显式声明与 bp 对齐
    arg("dagger.useBindingGraphFix", "ENABLED")
}

dependencies {
    // tier① SystemUI 自有源码模块（bp static_libs: ["SystemUI-core", ...]）
    implementation(project(":SystemUI-core"))

    // dagger2（bp static_libs；Dagger 根组件在本模块编译）
    implementation(libs.dagger)
    ksp(libs.dagger.compiler)

    // Framework APIs（allprojects 已注入 JavaCompile，此处显式声明便于阅读）
    compileOnly(files("${rootProject.projectDir}/libs/framework.jar"))
    // bp SystemUI-srcs-defaults libs: ["keepanno-annotations"]
    compileOnly(files("${rootProject.projectDir}/libs/keepanno-annotations.jar"))
    // WindowManager-Shell AAR（Task 073：AOSP SystemUI-application bp static_libs
    // SystemUI-core 静态链传递 WindowManager-Shell；Gradle compileOnly 不传递 →
    // 此处补 implementation，KSP 根组件（WMComponent/ShellInterface）与 dex 闭包
    // 都需要；AOSP SystemUI.apk 含 wmshell 类，语义一致）
    implementation(libs.systemui.wmshell)
    // WindowManager-Shell-shared AAR（同上静态链：WMShell Dagger 图引
    // com.android.wm.shell.shared.ShellTransitions 等）
    implementation(libs.systemui.wmshell.shared)
}
