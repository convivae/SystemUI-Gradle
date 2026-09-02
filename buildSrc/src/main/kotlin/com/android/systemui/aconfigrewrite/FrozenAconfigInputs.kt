package com.android.systemui.aconfigrewrite

import java.io.File
import java.security.MessageDigest

internal data class FrozenAconfigInputs(
    val mappings: Map<String, String>,
) {
    val sourceClasses: Set<String> get() = mappings.keys
    val targetClasses: Set<String> get() = mappings.values.toSet()

    companion object {
        // SHA-256 of gradle/aosp17-aconfig-repackaging-rules.txt: the complete
        // authoritative Soong framework jarjar rule set (725 exact class
        // renames, source -> com.android.internal.hidden_from_bootclasspath.*).
        // Derived from the frozen AOSP repackaging.txt whose own sha256 is
        // FULL_AOSP_RULES_SHA256; the repo copy is byte-canonical (no trailing
        // blank line, exactly one final LF).
        const val RULES_SHA256 = "411ad0e60c4647b3cc4c0160573e12f1a8ae5eadf9fc3f5492b76071b78d5191"
        const val FULL_AOSP_RULES_SHA256 = "f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97"
        const val RULE_COUNT = 725
        private const val TARGET_PREFIX = "com.android.internal.hidden_from_bootclasspath."

        private val rulePattern = Regex("rule ([A-Za-z_$][A-Za-z0-9_$.]*) ([A-Za-z_$][A-Za-z0-9_$.]*)")

        fun load(rulesFile: File): FrozenAconfigInputs {
            val lines = readCanonicalFile(rulesFile, "rules", RULES_SHA256, RULE_COUNT)
            val parsedRules = lines.map { line ->
                val match = rulePattern.matchEntire(line)
                    ?: fail("Malformed frozen rule: $line")
                match.groupValues[1] to match.groupValues[2]
            }
            if (parsedRules.map { it.first } != parsedRules.map { it.first }.sorted()) {
                fail("Frozen rules are not sorted by source class")
            }
            if (parsedRules.map { it.first }.toSet().size != parsedRules.size) {
                fail("Frozen rules contain duplicate source classes")
            }
            for ((source, target) in parsedRules) {
                if (!target.startsWith(TARGET_PREFIX) || target != TARGET_PREFIX + source) {
                    fail("Frozen rule is not the canonical identity-shaped hidden rename: $source -> $target")
                }
            }
            val mappings = parsedRules.toMap(LinkedHashMap())
            return FrozenAconfigInputs(mappings)
        }

        private fun readCanonicalFile(file: File, label: String, expectedSha: String, expectedCount: Int): List<String> {
            if (!file.isFile) fail("Frozen $label file is missing: $file")
            val bytes = file.readBytes()
            if (bytes.isEmpty() || bytes.last() != '\n'.code.toByte() || bytes.any { it == '\r'.code.toByte() }) {
                fail("Frozen $label file must use LF and end with one newline")
            }
            val actualSha = MessageDigest.getInstance("SHA-256")
                .digest(bytes)
                .joinToString("") { "%02x".format(it) }
            if (actualSha != expectedSha) fail("Frozen $label SHA-256 drift: $actualSha")
            val lines = bytes.toString(Charsets.UTF_8).removeSuffix("\n").split('\n')
            if (lines.size != expectedCount) fail("Frozen $label count drift: ${lines.size}")
            return lines
        }

        private fun fail(message: String): Nothing = throw IllegalStateException(message)
    }
}
