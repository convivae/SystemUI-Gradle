plugins {
    `kotlin-dsl`
}

gradlePlugin {
    plugins {
        create("aconfigReferenceRewrite") {
            id = "com.android.systemui.aconfig-reference-rewrite"
            implementationClass = "com.android.systemui.aconfigrewrite.AconfigReferenceRewritePlugin"
        }
    }
}

repositories {
    google()
    mavenCentral()
}

dependencies {
    // AGP public variant/instrumentation API (AsmClassVisitorFactory, InstrumentationScope, ...)
    implementation("com.android.tools.build:gradle-api:9.3.1")
    // ASM bytecode manipulation for the reference-only visitor
    implementation("org.ow2.asm:asm:9.9")
    implementation("org.ow2.asm:asm-commons:9.9")
    implementation("org.ow2.asm:asm-tree:9.9")

    testImplementation(platform("org.junit:junit-bom:5.11.4"))
    testImplementation("org.junit.jupiter:junit-jupiter")
    testImplementation("org.jetbrains.kotlin:kotlin-test")
}

tasks.withType<Test>().configureEach {
    useJUnitPlatform()
    systemProperty("task081.repo.root", rootDir.parentFile.absolutePath)
}
