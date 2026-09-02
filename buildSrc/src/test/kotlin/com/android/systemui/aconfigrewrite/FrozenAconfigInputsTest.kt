package com.android.systemui.aconfigrewrite

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertThrows
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.File
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.security.MessageDigest

class FrozenAconfigInputsTest {
    private val repositoryRoot = File(System.getProperty("task081.repo.root") ?: "..").canonicalFile
    private val rulesFile = File(repositoryRoot, "gradle/aosp17-aconfig-repackaging-rules.txt")
    private val fullAospRules = File(
        System.getProperty(
            "task081.aosp.rules",
            "/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt",
        ),
    )

    @Test
    fun `frozen rules are the complete AOSP rule set with exact provenance`() {
        assertEquals(FrozenAconfigInputs.RULES_SHA256, sha256(rulesFile))
        assertEquals(FrozenAconfigInputs.FULL_AOSP_RULES_SHA256, sha256(fullAospRules))

        val lines = canonicalLines(rulesFile)
        assertEquals(FrozenAconfigInputs.RULE_COUNT, lines.size)
        assertEquals(lines.sorted(), lines)
        assertEquals(lines.size, lines.toSet().size)
        val mappings = FrozenAconfigInputs.load(rulesFile).mappings
        assertEquals(FrozenAconfigInputs.RULE_COUNT, mappings.size)
        // The frozen repo copy is the AOSP rule set canonically re-serialized:
        // same rules, no trailing blank line, exactly one final LF.
        val aospLines = fullAospRules.readLines(StandardCharsets.UTF_8).filter { it.isNotBlank() }
        assertEquals(aospLines, lines)
        for ((source, target) in mappings) {
            assertEquals("com.android.internal.hidden_from_bootclasspath.$source", target)
        }
        // The four previously-critical names remain first-class rules.
        for (critical in listOf(
            "android.app.Flags",
            "android.os.Flags",
            "android.view.accessibility.Flags",
            "com.android.window.flags.Flags",
        )) {
            assertTrue(critical in mappings)
        }
    }

    @Test
    fun `loader fails closed for every frozen-input drift category`() {
        val scratch = File("/tmp/task099-c5-dreams-flags-diagnosis/loader-tests").apply {
            deleteRecursively()
            mkdirs()
        }
        val goodRules = rulesFile.readText()

        fun expectFailure(name: String, rules: String? = goodRules) {
            val caseDir = File(scratch, name).apply { mkdirs() }
            val caseRules = File(caseDir, "rules.txt")
            if (rules != null) caseRules.writeText(rules)
            assertThrows(IllegalStateException::class.java) {
                FrozenAconfigInputs.load(caseRules)
            }
        }

        expectFailure("missing-rules", rules = null)
        expectFailure("malformed-rule", rules = goodRules.replaceFirst("rule ", "invalid "))
        expectFailure(
            "duplicate-rule",
            rules = goodRules.lineSequence().take(724).plus(goodRules.lineSequence().first()).joinToString("\n", postfix = "\n"),
        )
        expectFailure("rule-count", rules = goodRules.lineSequence().take(724).joinToString("\n", postfix = "\n"))
        expectFailure("rules-sha", rules = goodRules.replace("android.app.Flags", "android.app.Flagz"))
        expectFailure(
            "rule-shape",
            rules = goodRules.replace(
                "com.android.internal.hidden_from_bootclasspath.android.app.Flags",
                "com.android.internal.hidden_from_bootclasspath.android.app.Flagz",
            ),
        )
        expectFailure(
            "non-identity-target",
            rules = goodRules.replaceFirst(
                "rule android.app.Flags com.android.internal.hidden_from_bootclasspath.android.app.Flags",
                "rule android.app.Flags com.example.RenamedFlags",
            ),
        )
        expectFailure("rules-crlf", rules = goodRules.replace("\n", "\r\n"))
        expectFailure("rules-no-final-lf", rules = goodRules.removeSuffix("\n"))
    }

    private fun canonicalLines(file: File): List<String> {
        val bytes = file.readBytes()
        assertTrue(bytes.isNotEmpty())
        assertEquals('\n'.code.toByte(), bytes.last())
        assertTrue(bytes.none { it == '\r'.code.toByte() })
        return file.readLines(StandardCharsets.UTF_8)
    }

    private fun sha256(file: File): String = MessageDigest.getInstance("SHA-256")
        .digest(Files.readAllBytes(file.toPath()))
        .joinToString("") { "%02x".format(it) }
}
