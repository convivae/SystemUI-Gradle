package com.android.systemui.aconfigrewrite

import java.io.File
import java.security.MessageDigest

internal data class FrozenAconfigInputs(
    val mappings: Map<String, String>,
    val allowlist: Set<String>,
) {
    companion object {
        const val RULES_SHA256 = "ff79a84d8ba250eeae789af007aa97828f5b31b2f41950cf519465f20fe79d85"
        const val ALLOWLIST_SHA256 = "926f102e3c899dbcac4ee7e5054bf294f9cde327eaf9f6a43bc29f2d6d2b682b"
        const val FULL_AOSP_RULES_SHA256 = "f79a08d481147a5e6a532ec254e6f075ccb661d844b9ac19db764cd085a6de97"

        private val approvedMappings = linkedMapOf(
            "android.app.Flags" to "com.android.internal.hidden_from_bootclasspath.android.app.Flags",
            "android.os.Flags" to "com.android.internal.hidden_from_bootclasspath.android.os.Flags",
            "android.view.accessibility.Flags" to "com.android.internal.hidden_from_bootclasspath.android.view.accessibility.Flags",
            "com.android.window.flags.Flags" to "com.android.internal.hidden_from_bootclasspath.com.android.window.flags.Flags",
        )
        private val rulePattern = Regex("rule ([A-Za-z_$][A-Za-z0-9_$.]*) ([A-Za-z_$][A-Za-z0-9_$.]*)")
        private val classPattern = Regex("[A-Za-z_$][A-Za-z0-9_$.]*")

        fun load(rulesFile: File, allowlistFile: File): FrozenAconfigInputs {
            val ruleLines = readCanonicalFile(rulesFile, "rules", RULES_SHA256, 4)
            val parsedRules = ruleLines.map { line ->
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
            val mappings = parsedRules.toMap(LinkedHashMap())
            if (mappings != approvedMappings) {
                fail("Frozen rules differ from the four approved mappings")
            }

            val classes = readCanonicalFile(allowlistFile, "allowlist", ALLOWLIST_SHA256, 166)
            if (classes != classes.sorted()) fail("Frozen allowlist is not sorted")
            if (classes.toSet().size != classes.size) fail("Frozen allowlist contains duplicates")
            if (classes.any { !classPattern.matches(it) || '/' in it }) {
                fail("Frozen allowlist contains a malformed dot-FQCN")
            }
            return FrozenAconfigInputs(mappings, LinkedHashSet(classes))
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
