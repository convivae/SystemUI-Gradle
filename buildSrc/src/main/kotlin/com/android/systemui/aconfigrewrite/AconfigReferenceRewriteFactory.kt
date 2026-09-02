package com.android.systemui.aconfigrewrite

import com.android.build.api.instrumentation.AsmClassVisitorFactory
import com.android.build.api.instrumentation.ClassContext
import com.android.build.api.instrumentation.ClassData
import com.android.build.api.instrumentation.InstrumentationParameters
import org.gradle.api.provider.MapProperty
import org.gradle.api.provider.SetProperty
import org.gradle.api.tasks.Input
import org.objectweb.asm.ClassVisitor

internal interface AconfigReferenceRewriteParameters : InstrumentationParameters {
    @get:Input
    val mappings: MapProperty<String, String>

    @get:Input
    val allowlist: SetProperty<String>
}

internal fun isAllowlistedClass(className: String, allowlist: Set<String>): Boolean =
    AconfigReferenceRewriteFilter(allowlist).isInstrumentable(className)

internal abstract class AconfigReferenceRewriteFactory :
    AsmClassVisitorFactory<AconfigReferenceRewriteParameters> {

    override fun isInstrumentable(classData: ClassData): Boolean =
        isAllowlistedClass(classData.className, parameters.get().allowlist.get())

    override fun createClassVisitor(
        classContext: ClassContext,
        nextClassVisitor: ClassVisitor,
    ): ClassVisitor {
        val internalMappings = parameters.get().mappings.get()
            .mapKeys { (source, _) -> source.replace('.', '/') }
            .mapValues { (_, target) -> target.replace('.', '/') }
        val currentClass = classContext.currentClassData.className.replace('.', '/')
        return referenceOnlyVisitor(nextClassVisitor, currentClass, internalMappings)
    }
}
