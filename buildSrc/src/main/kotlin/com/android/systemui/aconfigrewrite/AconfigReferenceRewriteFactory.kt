package com.android.systemui.aconfigrewrite

import com.android.build.api.instrumentation.AsmClassVisitorFactory
import com.android.build.api.instrumentation.ClassContext
import com.android.build.api.instrumentation.ClassData
import com.android.build.api.instrumentation.InstrumentationParameters
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.PathSensitive
import org.gradle.api.tasks.PathSensitivity
import org.objectweb.asm.ClassVisitor

internal interface AconfigReferenceRewriteParameters : InstrumentationParameters {
    @get:InputFile
    @get:PathSensitive(PathSensitivity.RELATIVE)
    val rulesFile: RegularFileProperty

    @get:InputFile
    @get:PathSensitive(PathSensitivity.RELATIVE)
    val allowlistFile: RegularFileProperty
}

internal abstract class AconfigReferenceRewriteFactory :
    AsmClassVisitorFactory<AconfigReferenceRewriteParameters> {

    @Transient
    @Volatile
    private var cachedInputs: FrozenAconfigInputs? = null

    override fun isInstrumentable(classData: ClassData): Boolean =
        isAllowlistedClass(classData.className, inputs().allowlist)

    override fun createClassVisitor(
        classContext: ClassContext,
        nextClassVisitor: ClassVisitor,
    ): ClassVisitor {
        val inputs = inputs()
        val currentClass = classContext.currentClassData.className.replace('.', '/')
        val internalMappings = inputs.mappings
            .mapKeys { (source, _) -> source.replace('.', '/') }
            .mapValues { (_, target) -> target.replace('.', '/') }
        return referenceOnlyVisitor(nextClassVisitor, currentClass, internalMappings)
    }

    private fun inputs(): FrozenAconfigInputs {
        cachedInputs?.let { return it }
        return synchronized(this) {
            cachedInputs ?: FrozenAconfigInputs.load(
                parameters.get().rulesFile.asFile.get(),
                parameters.get().allowlistFile.asFile.get(),
            ).also { cachedInputs = it }
        }
    }

    companion object {
        internal fun isAllowlistedClass(className: String, allowlist: Set<String>): Boolean =
            AconfigReferenceRewriteFilter(allowlist).isInstrumentable(className)
    }
}
