package com.android.systemui.resources

import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption.ATOMIC_MOVE
import java.nio.file.StandardCopyOption.REPLACE_EXISTING

/** Repairs only AGP intermediates; neither source resources nor merger XML are rewritten. */
internal object AndroidPrvResourceRepair {
    const val DECLARATION = "xmlns:androidprv=\"http://schemas.android.com/apk/prv/res/android\""
    private val resourcesRoot = Regex("<resources\\b[^>]*>")

    data class Summary(val scanned: Int, val patched: Int, val compiled: Int) {
        override fun toString() = "scanned=$scanned patched=$patched compiled=$compiled unresolved=0"
    }

    fun flatName(xml: File): String = "${xml.parentFile.name}_${xml.nameWithoutExtension}.arsc.flat"

    fun injectDeclaration(xml: String): String {
        val count = Regex(Regex.escape(DECLARATION)).findAll(xml).count()
        check(count <= 1) { "duplicate $DECLARATION declarations ($count occurrences)" }
        if (count == 1) return xml
        val root = checkNotNull(resourcesRoot.find(xml)) { "no <resources ...> root element found" }
        return xml.replaceRange(root.range, root.value.dropLast(1) + " $DECLARATION>")
    }

    fun repair(
        mergedDir: File,
        compiledDir: File,
        aapt2: File,
        featureFlags: File,
        temporaryDir: File,
        compile: (List<String>) -> Unit,
    ): Summary {
        check(mergedDir.isDirectory) { "merged resources is not a directory: $mergedDir" }
        check(compiledDir.isDirectory) { "compiled resources is not a directory: $compiledDir" }
        check(aapt2.isFile && aapt2.canExecute()) { "AAPT2 is not an executable file: $aapt2" }
        check(featureFlags.isFile) { "feature-flags file not found: $featureFlags" }

        val xmlFiles = mergedDir.walkTopDown().filter { it.isFile && it.extension == "xml" }
            .sortedBy { it.relativeTo(mergedDir).invariantSeparatorsPath }.toList()
        val candidates = xmlFiles.mapNotNull { file ->
            // Match Python's universal-newline read in the former implementation.
            // Normalization affects staging only; original bytes remain untouched.
            val text = file.readText().replace("\r\n", "\n").replace("\r", "\n")
            if ("androidprv:" in text) file to text else null
        }
        check(candidates.isNotEmpty()) { "no androidprv references found under merged resources: $mergedDir" }
        // Validate every declaration before invoking AAPT2 or changing any flat.
        val patches = candidates.mapNotNull { (file, text) ->
            val patched = injectDeclaration(text)
            if (patched != text) file to patched else null
        }
        if (patches.isEmpty()) return Summary(xmlFiles.size, 0, 0)

        Files.createDirectories(temporaryDir.toPath())
        val work = Files.createTempDirectory(temporaryDir.toPath(), "androidprv-").toFile()
        try {
            val staging = File(work, "staging")
            val out = File(work, "out").apply { mkdirs() }
            // Compile all candidates before publishing: a failed compile must
            // not leave a partially repaired set of AGP-owned flats behind.
            val replacements = patches.map { (original, patched) ->
                val destination = File(compiledDir, flatName(original))
                check(destination.isFile) { "no existing flat to replace: $destination" }
                val staged = File(staging, original.relativeTo(mergedDir).path)
                staged.parentFile.mkdirs()
                staged.writeText(patched)
                // AOSP 17 flags are required by standalone AAPT2 compile, unlike
                // AGP's in-process resource compiler. Each item is a separate
                // process argument, including @file paths containing spaces.
                val command = listOf(
                    aapt2.absolutePath, "compile", "--feature-flags", "@${featureFlags.absolutePath}",
                    staged.absolutePath, "-o", out.absolutePath,
                )
                try {
                    compile(command)
                } catch (failure: Exception) {
                    throw IllegalStateException("AAPT2 compile failed for $original", failure)
                }
                val flat = File(out, flatName(original))
                check(flat.isFile) { "expected flat output missing after compile: $flat (for $original)" }
                flat to destination
            }
            replacements.forEach { (source, destination) -> atomicReplace(source, destination) }
            return Summary(xmlFiles.size, patches.size, replacements.size)
        } finally {
            work.deleteRecursively()
        }
    }

    private fun atomicReplace(source: File, destination: File) {
        // Staging may be on another volume. Copy to a unique sibling first,
        // then require a same-filesystem atomic move; never truncate the target.
        val sibling = Files.createTempFile(destination.parentFile.toPath(), ".androidprv-", ".flat")
        try {
            Files.copy(source.toPath(), sibling, REPLACE_EXISTING)
            Files.move(sibling, destination.toPath(), ATOMIC_MOVE, REPLACE_EXISTING)
        } finally {
            Files.deleteIfExists(sibling)
        }
    }
}
