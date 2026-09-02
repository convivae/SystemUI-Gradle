package com.android.systemui.aconfigrewrite

import com.android.build.api.instrumentation.FramesComputationMode
import com.android.build.api.instrumentation.InstrumentationScope
import com.android.build.api.variant.ApplicationAndroidComponentsExtension
import com.android.build.api.variant.Instrumentation
import org.gradle.api.Plugin
import org.gradle.api.Project
import java.io.File

internal object AconfigInstrumentationRegistration {
    const val APPLICATION_PLUGIN_ID = "com.android.application"

    fun registerForPlugin(
        pluginId: String,
        instrumentation: Instrumentation,
        rulesFile: File,
        allowlistFile: File,
    ): Boolean {
        if (pluginId != APPLICATION_PLUGIN_ID) return false
        instrumentation.transformClassesWith(
            AconfigReferenceRewriteFactory::class.java,
            InstrumentationScope.ALL,
        ) { parameters ->
            parameters.rulesFile.fileValue(rulesFile)
            parameters.allowlistFile.fileValue(allowlistFile)
        }
        instrumentation.setAsmFramesComputationMode(FramesComputationMode.COPY_FRAMES)
        return true
    }
}

class AconfigReferenceRewritePlugin : Plugin<Project> {
    override fun apply(project: Project) {
        project.pluginManager.withPlugin(AconfigInstrumentationRegistration.APPLICATION_PLUGIN_ID) {
            val androidComponents = project.extensions.getByType(
                ApplicationAndroidComponentsExtension::class.java,
            )
            val rulesFile = project.rootProject.file("gradle/aosp17-critical-aconfig-reference-rules.txt")
            val allowlistFile = project.rootProject.file("gradle/aosp17-critical-aconfig-reference-classes.txt")
            androidComponents.onVariants(androidComponents.selector().all()) { variant ->
                check(
                    AconfigInstrumentationRegistration.registerForPlugin(
                        AconfigInstrumentationRegistration.APPLICATION_PLUGIN_ID,
                        variant.instrumentation,
                        rulesFile,
                        allowlistFile,
                    ),
                )
            }
        }
    }
}
