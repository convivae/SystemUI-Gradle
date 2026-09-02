package com.android.systemui.aconfigrewrite

import org.objectweb.asm.ClassReader
import org.objectweb.asm.ClassVisitor
import org.objectweb.asm.ClassWriter
import org.objectweb.asm.Opcodes
import org.objectweb.asm.commons.ClassRemapper
import org.objectweb.asm.commons.Remapper

internal class AconfigReferenceRewriteFilter(private val allowlist: Set<String>) {
    fun isInstrumentable(className: String): Boolean = className in allowlist
}

internal class ReferenceOnlyClassRewriter(mappings: Map<String, String>) {
    private val internalMappings = mappings
        .mapKeys { (source, _) -> source.replace('.', '/') }
        .mapValues { (_, target) -> target.replace('.', '/') }
    private val hiddenTargets = internalMappings.values.toSet()

    fun rewrite(input: ByteArray): ByteArray {
        val reader = ClassReader(input)
        val originalClass = reader.className
        check(originalClass !in hiddenTargets) {
            "Refusing to instrument a hidden platform definition: $originalClass"
        }
        val writer = ClassWriter(reader, 0)
        reader.accept(referenceOnlyVisitor(writer, originalClass, internalMappings), 0)
        val output = writer.toByteArray()
        val outputClass = ClassReader(output).className
        check(outputClass == originalClass) {
            "Reference rewrite changed this_class from $originalClass to $outputClass"
        }
        check(outputClass !in hiddenTargets) {
            "Reference rewrite produced a hidden platform definition: $outputClass"
        }
        return output
    }
}

internal fun referenceOnlyVisitor(
    nextClassVisitor: ClassVisitor,
    currentClass: String,
    internalMappings: Map<String, String>,
): ClassVisitor {
    val remapper = object : Remapper(Opcodes.ASM9) {
        override fun map(internalName: String): String =
            if (internalName == currentClass) currentClass else internalMappings[internalName] ?: internalName
    }
    return ClassRemapper(nextClassVisitor, remapper)
}
