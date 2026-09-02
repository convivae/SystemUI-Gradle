package com.android.systemui.aconfigrewrite

import com.android.build.api.instrumentation.FramesComputationMode
import com.android.build.api.instrumentation.InstrumentationScope
import com.android.build.api.variant.ApplicationAndroidComponentsExtension
import com.android.build.api.variant.Instrumentation
import org.gradle.api.Plugin
import org.gradle.api.Project

internal object AconfigInstrumentationRegistration {
    const val APPLICATION_PLUGIN_ID = "com.android.application"

    fun registerForPlugin(
        pluginId: String,
        instrumentation: Instrumentation,
        frozenInputs: FrozenAconfigInputs,
    ): Boolean {
        if (pluginId != APPLICATION_PLUGIN_ID) return false
        instrumentation.transformClassesWith(
            AconfigReferenceRewriteFactory::class.java,
            InstrumentationScope.ALL,
        ) { parameters ->
            parameters.mappings.putAll(frozenInputs.mappings)
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
            val frozenInputs = FrozenAconfigInputs.load(
                project.rootProject.file("gradle/aosp17-aconfig-repackaging-rules.txt"),
            )
            androidComponents.onVariants(androidComponents.selector().all()) { variant ->
                check(
                    AconfigInstrumentationRegistration.registerForPlugin(
                        AconfigInstrumentationRegistration.APPLICATION_PLUGIN_ID,
                        variant.instrumentation,
                        frozenInputs,
                    ),
                )
            }
        }
    }
}
