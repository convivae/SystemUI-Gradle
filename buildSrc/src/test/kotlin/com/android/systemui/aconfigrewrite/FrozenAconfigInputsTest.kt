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
    private val rulesFile = File(repositoryRoot, "gradle/aosp17-critical-aconfig-reference-rules.txt")
    private val allowlistFile = File(repositoryRoot, "gradle/aosp17-critical-aconfig-reference-classes.txt")
    private val fullAospRules = File(
        System.getProperty(
            "task081.aosp.rules",
            "/home/conv/myspace/aosp/out/soong/.intermediates/frameworks/base/framework/android_common/repackaged-jarjar/repackaging.txt",
        ),
    )

    @Test
    fun `frozen rules are the four approved AOSP rules with exact provenance`() {
        assertEquals(FrozenAconfigInputs.RULES_SHA256, sha256(rulesFile))
        assertEquals(FrozenAconfigInputs.FULL_AOSP_RULES_SHA256, sha256(fullAospRules))

        val lines = canonicalLines(rulesFile)
        assertEquals(4, lines.size)
        assertEquals(lines.sortedBy(::ruleSource), lines)
        assertEquals(
            listOf(
                "rule android.app.Flags com.android.internal.hidden_from_bootclasspath.android.app.Flags",
                "rule android.os.Flags com.android.internal.hidden_from_bootclasspath.android.os.Flags",
                "rule android.view.accessibility.Flags com.android.internal.hidden_from_bootclasspath.android.view.accessibility.Flags",
                "rule com.android.window.flags.Flags com.android.internal.hidden_from_bootclasspath.com.android.window.flags.Flags",
            ),
            lines,
        )
        assertTrue(fullAospRules.readLines().containsAll(lines))
        assertEquals(4, FrozenAconfigInputs.load(rulesFile, allowlistFile).mappings.size)
    }

    @Test
    fun `frozen allowlist is exactly 166 sorted unique dot FQCNs`() {
        assertEquals(FrozenAconfigInputs.ALLOWLIST_SHA256, sha256(allowlistFile))
        val lines = canonicalLines(allowlistFile)
        assertEquals(166, lines.size)
        assertEquals(lines.sorted(), lines)
        assertEquals(166, lines.toSet().size)
        assertTrue(lines.all { it.matches(Regex("[A-Za-z_$][A-Za-z0-9_$.]*")) && '/' !in it })
        assertEquals(lines.toSet(), FrozenAconfigInputs.load(rulesFile, allowlistFile).allowlist)
    }

    @Test
    fun `loader fails closed for every frozen-input drift category`() {
        val scratch = File("/tmp/task081-c5-pre-dex-reference-rewrite/loader-tests").apply {
            deleteRecursively()
            mkdirs()
        }
        val goodRules = rulesFile.readText()
        val goodClasses = allowlistFile.readText()

        fun expectFailure(name: String, rules: String? = goodRules, classes: String? = goodClasses) {
            val caseDir = File(scratch, name).apply { mkdirs() }
            val caseRules = File(caseDir, "rules.txt")
            val caseClasses = File(caseDir, "classes.txt")
            if (rules != null) caseRules.writeText(rules)
            if (classes != null) caseClasses.writeText(classes)
            assertThrows(IllegalStateException::class.java) {
                FrozenAconfigInputs.load(caseRules, caseClasses)
            }
        }

        expectFailure("missing-rules", rules = null)
        expectFailure("missing-allowlist", classes = null)
        expectFailure("malformed-rule", rules = goodRules.replaceFirst("rule ", "invalid "))
        expectFailure("duplicate-rule", rules = goodRules.lineSequence().take(3).plus(goodRules.lineSequence().first()).joinToString("\n", postfix = "\n"))
        expectFailure("duplicate-class", classes = goodClasses.lineSequence().take(165).plus(goodClasses.lineSequence().first()).sorted().joinToString("\n", postfix = "\n"))
        expectFailure("rule-count", rules = goodRules.lineSequence().take(3).joinToString("\n", postfix = "\n"))
        expectFailure("allowlist-count", classes = goodClasses.lineSequence().take(165).joinToString("\n", postfix = "\n"))
        expectFailure("rules-sha", rules = goodRules.replace("android.app.Flags", "android.app.Flagz"))
        expectFailure("allowlist-sha", classes = goodClasses.replaceFirst("com.", "org."))
        expectFailure(
            "rule-set",
            rules = goodRules.replace(
                "com.android.internal.hidden_from_bootclasspath.android.app.Flags",
                "com.android.internal.hidden_from_bootclasspath.android.app.Flagz",
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

    private fun ruleSource(line: String): String = line.split(' ')[1]

    private fun sha256(file: File): String = MessageDigest.getInstance("SHA-256")
        .digest(Files.readAllBytes(file.toPath()))
        .joinToString("") { "%02x".format(it) }
}
