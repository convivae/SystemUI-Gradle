package com.android.systemui.aconfigrewrite

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import org.objectweb.asm.ClassReader
import org.objectweb.asm.ClassWriter
import org.objectweb.asm.Handle
import org.objectweb.asm.Opcodes
import org.objectweb.asm.Type
import org.objectweb.asm.tree.ClassNode
import org.objectweb.asm.tree.FieldInsnNode
import org.objectweb.asm.tree.InvokeDynamicInsnNode
import org.objectweb.asm.tree.LdcInsnNode
import org.objectweb.asm.tree.MethodInsnNode
import org.objectweb.asm.tree.TypeInsnNode

class ReferenceOnlyClassRewriterTest {
    private val mappings = linkedMapOf(
        "android.app.Flags" to "com.android.internal.hidden_from_bootclasspath.android.app.Flags",
        "android.os.Flags" to "com.android.internal.hidden_from_bootclasspath.android.os.Flags",
        "android.view.accessibility.Flags" to "com.android.internal.hidden_from_bootclasspath.android.view.accessibility.Flags",
        "com.android.window.flags.Flags" to "com.android.internal.hidden_from_bootclasspath.com.android.window.flags.Flags",
    )
    private val internalMappings = mappings.mapKeys { it.key.replace('.', '/') }.mapValues { it.value.replace('.', '/') }
    private val rewriter = ReferenceOnlyClassRewriter(mappings)

    @Test
    fun `allowlisted caller class references are rewritten and other callers are rejected by filter`() {
        val caller = "com.android.systemui.statusbar.CommandQueue"
        val allowlist = setOf(caller)
        val filter = AconfigReferenceRewriteFilter(allowlist)
        assertTrue(filter.isInstrumentable(caller))
        assertFalse(filter.isInstrumentable("com.android.systemui.NotProvenByTask080"))
        assertTrue(isAllowlistedClass(caller, allowlist))
        assertFalse(
            isAllowlistedClass(
                "com.android.systemui.NotProvenByTask080",
                allowlist,
            ),
        )

        val output = node(rewriter.rewrite(simpleFixture(caller.replace('.', '/'), "android/app/Flags")))
        val fieldReference = instructions(output).filterIsInstance<FieldInsnNode>().single()
        assertEquals(internalMappings.getValue("android/app/Flags"), fieldReference.owner)
    }

    @Test
    fun `source named class preserves this_class and every self reference while other mapped types change`() {
        val sourceOwner = "android/app/Flags"
        val output = node(rewriter.rewrite(selfReferenceFixture(sourceOwner, "android/os/Flags")))

        assertEquals(sourceOwner, output.name)
        assertEquals("L$sourceOwner;", output.fields.single { it.name == "self" }.desc)
        assertEquals("(L$sourceOwner;)L$sourceOwner;", output.methods.single { it.name == "self" }.desc)
        assertTrue(instructions(output).filterIsInstance<FieldInsnNode>().any { it.owner == sourceOwner })
        assertTrue(
            instructions(output).filterIsInstance<MethodInsnNode>().any {
                it.owner == internalMappings.getValue("android/os/Flags")
            },
        )
    }

    @Test
    fun `rewriter never changes a definition into a hidden platform target`() {
        val hiddenTargets = internalMappings.values.toSet()
        for (sourceOwner in internalMappings.keys) {
            val output = node(rewriter.rewrite(simpleFixture(sourceOwner, "android/os/Flags")))
            assertEquals(sourceOwner, output.name)
            assertFalse(output.name in hiddenTargets)
        }
    }

    @Test
    fun `plain UTF8 strings containing source names remain unchanged`() {
        val source = "android/app/Flags"
        val output = node(rewriter.rewrite(simpleFixture("example/Caller", source)))
        val strings = instructions(output)
            .filterIsInstance<LdcInsnNode>()
            .map { it.cst }
            .filterIsInstance<String>()
        assertEquals(listOf("plain string mentioning $source is not a class reference"), strings)
    }

    @Test
    fun `all JVM type-bearing locations are remapped`() {
        val output = node(rewriter.rewrite(richFixture("example/RichCaller")))

        assertEquals(
            "L${internalMappings.getValue("android/os/Flags")};",
            output.fields.single { it.name == "descriptor" }.desc,
        )
        assertEquals(
            "Ljava/util/List<L${internalMappings.getValue("android/app/Flags")};>;",
            output.fields.single { it.name == "signature" }.signature,
        )
        val annotationClassValue = output.visibleAnnotations.single().values[1] as Type
        assertEquals("L${internalMappings.getValue("android/view/accessibility/Flags")};", annotationClassValue.descriptor)

        val richMethod = output.methods.single { it.name == "rich" }
        assertEquals(
            "(L${internalMappings.getValue("android/app/Flags")};)L${internalMappings.getValue("android/os/Flags")};",
            richMethod.desc,
        )
        assertTrue(
            richMethod.signature!!.contains("L${internalMappings.getValue("com/android/window/flags/Flags")};"),
        )
        assertEquals(
            internalMappings.getValue("com/android/window/flags/Flags"),
            instructions(output).filterIsInstance<TypeInsnNode>().single().desc,
        )

        val ldcHandle = instructions(output)
            .filterIsInstance<LdcInsnNode>()
            .map { it.cst }
            .filterIsInstance<Handle>()
            .single()
        assertEquals(internalMappings.getValue("android/os/Flags"), ldcHandle.owner)

        val invokeDynamic = instructions(output).filterIsInstance<InvokeDynamicInsnNode>().single()
        assertEquals(internalMappings.getValue("android/app/Flags"), invokeDynamic.bsm.owner)
        assertTrue(invokeDynamic.desc.contains(internalMappings.getValue("android/os/Flags")))
        assertEquals(
            internalMappings.getValue("android/view/accessibility/Flags"),
            (invokeDynamic.bsmArgs.single() as Handle).owner,
        )
    }

    private fun simpleFixture(owner: String, referencedOwner: String): ByteArray {
        val writer = newClass(owner)
        val method = writer.visitMethod(Opcodes.ACC_PUBLIC, "call", "()V", null, null)
        method.visitCode()
        method.visitFieldInsn(Opcodes.GETSTATIC, referencedOwner, "FLAG", "Z")
        method.visitInsn(Opcodes.POP)
        method.visitLdcInsn("plain string mentioning $referencedOwner is not a class reference")
        method.visitInsn(Opcodes.POP)
        method.visitInsn(Opcodes.RETURN)
        method.visitMaxs(1, 1)
        method.visitEnd()
        writer.visitEnd()
        return writer.toByteArray()
    }

    private fun selfReferenceFixture(owner: String, otherSource: String): ByteArray {
        val writer = newClass(owner)
        writer.visitField(Opcodes.ACC_PRIVATE, "self", "L$owner;", null, null).visitEnd()
        val self = writer.visitMethod(Opcodes.ACC_PUBLIC, "self", "(L$owner;)L$owner;", null, null)
        self.visitCode()
        self.visitFieldInsn(Opcodes.GETFIELD, owner, "self", "L$owner;")
        self.visitMethodInsn(Opcodes.INVOKESTATIC, otherSource, "enabled", "()Z", false)
        self.visitInsn(Opcodes.POP)
        self.visitInsn(Opcodes.ARETURN)
        self.visitMaxs(1, 2)
        self.visitEnd()
        writer.visitEnd()
        return writer.toByteArray()
    }

    private fun richFixture(owner: String): ByteArray {
        val writer = newClass(owner)
        writer.visitField(Opcodes.ACC_PRIVATE, "descriptor", "Landroid/os/Flags;", null, null).visitEnd()
        writer.visitField(
            Opcodes.ACC_PRIVATE,
            "signature",
            "Ljava/util/List;",
            "Ljava/util/List<Landroid/app/Flags;>;",
            null,
        ).visitEnd()
        writer.visitAnnotation("Lexample/Marker;", true).apply {
            visit("value", Type.getType("Landroid/view/accessibility/Flags;"))
            visitEnd()
        }

        val method = writer.visitMethod(
            Opcodes.ACC_PUBLIC,
            "rich",
            "(Landroid/app/Flags;)Landroid/os/Flags;",
            "<T:Lcom/android/window/flags/Flags;>(Landroid/app/Flags;)Landroid/os/Flags;",
            null,
        )
        method.visitCode()
        method.visitTypeInsn(Opcodes.CHECKCAST, "com/android/window/flags/Flags")
        method.visitInsn(Opcodes.POP)
        method.visitLdcInsn(Handle(Opcodes.H_INVOKESTATIC, "android/os/Flags", "enabled", "()Z", false))
        method.visitInsn(Opcodes.POP)
        method.visitInvokeDynamicInsn(
            "critical",
            "()Landroid/os/Flags;",
            Handle(
                Opcodes.H_INVOKESTATIC,
                "android/app/Flags",
                "bootstrap",
                "(Ljava/lang/invoke/MethodHandles\$Lookup;Ljava/lang/String;Ljava/lang/invoke/MethodType;)Ljava/lang/invoke/CallSite;",
                false,
            ),
            Handle(Opcodes.H_INVOKESTATIC, "android/view/accessibility/Flags", "enabled", "()Z", false),
        )
        method.visitInsn(Opcodes.ARETURN)
        method.visitMaxs(1, 2)
        method.visitEnd()
        writer.visitEnd()
        return writer.toByteArray()
    }

    private fun newClass(owner: String): ClassWriter = ClassWriter(0).apply {
        visit(Opcodes.V17, Opcodes.ACC_PUBLIC, owner, null, "java/lang/Object", null)
    }

    private fun node(bytes: ByteArray): ClassNode = ClassNode().also { ClassReader(bytes).accept(it, 0) }

    private fun instructions(node: ClassNode) = node.methods.flatMap { method ->
        method.instructions.iterator().asSequence().toList()
    }
}
