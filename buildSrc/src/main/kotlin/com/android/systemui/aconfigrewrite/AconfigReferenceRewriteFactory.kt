package com.android.systemui.aconfigrewrite

import com.android.build.api.instrumentation.AsmClassVisitorFactory
import com.android.build.api.instrumentation.ClassContext
import com.android.build.api.instrumentation.ClassData
import com.android.build.api.instrumentation.InstrumentationParameters
import org.gradle.api.provider.MapProperty
import org.gradle.api.tasks.Input
import org.objectweb.asm.ClassVisitor

internal interface AconfigReferenceRewriteParameters : InstrumentationParameters {
    @get:Input
    val mappings: MapProperty<String, String>
}

/**
 * Production filter (Task 099, Chief decision after the D8 lambda lesson):
 * instrument EVERY class.
 *
 * Skipping mapping-source classes cannot work: D8 synthesizes
 * ``$$ExternalSyntheticLambda`` classes at dex time from the skipped
 * class's ``BootstrapMethods`` method handles, i.e. AFTER the ASM transform,
 * so any old-name method handle left in a skipped source class becomes an
 * unrewritable synthesized caller (946 residual old-owner refs in the
 * 2026-09-03 Debug build).
 *
 * Instead every class -- including mapping sources -- runs through the
 * reference-only visitor, which preserves ``this_class`` and self references
 * while rewriting every outward reference (including ``BootstrapMethods``
 * handles) to the hidden twins. Each old-name class in the APK therefore
 * becomes a self-contained dead shell delegating to the on-device hidden
 * cluster, and D8-synthesized lambdas come out hidden-referencing.
 *
 * The only illegitimate inputs are hidden platform definitions
 * (``com.android.internal.hidden_from_bootclasspath.*``): the rewriter's
 * visitor fails closed on them (see [referenceOnlyVisitor]) so such a class
 * appearing in the transform input fails the build loudly.
 */
internal abstract class AconfigReferenceRewriteFactory :
    AsmClassVisitorFactory<AconfigReferenceRewriteParameters> {

    override fun isInstrumentable(classData: ClassData): Boolean = true

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
