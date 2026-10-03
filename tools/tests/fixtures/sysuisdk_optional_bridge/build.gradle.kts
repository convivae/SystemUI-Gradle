plugins { id("com.android.library") version "9.3.1" }
android {
    namespace = "validation.sdk"
    compileSdkPreview = "SysUISdk"
    defaultConfig { minSdk = 35 }
    useLibrary("com.android.systemui.platform.bridge")
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_21
        targetCompatibility = JavaVersion.VERSION_21
    }
    testOptions.unitTests.all { it.useJUnitPlatform() }
}
dependencies {
    testImplementation(platform("org.junit:junit-bom:5.11.4"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testRuntimeOnly("org.junit.platform:junit-platform-launcher")
}
val expectedBridge = androidComponents.sdkComponents.sdkDirectory.map {
    it.file("platforms/android-SysUISdk/optional/sysui-platform-bridge.jar").asFile
}
tasks.withType<Test>().configureEach {
    inputs.file(expectedBridge)
    doFirst {
        val bridge = expectedBridge.get().canonicalFile
        check(classpath.files.any { it.canonicalFile == bridge })
        systemProperty("expectedBridgeJar", bridge.path)
        println("UNIT_TEST_OPTIONAL_CLASSPATH_PASS=$bridge")
    }
}
