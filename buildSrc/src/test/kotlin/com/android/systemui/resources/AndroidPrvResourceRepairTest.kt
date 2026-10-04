package com.android.systemui.resources

import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.io.File

class AndroidPrvResourceRepairTest {
    @TempDir
    lateinit var root: File

    private val merged get() = File(root, "merged dir").apply { mkdirs() }
    private val compiled get() = File(root, "compiled dir").apply { mkdirs() }
    private val scratch get() = File(root, "task temp").apply { mkdirs() }
    private val aapt2 get() = File(root, "aapt2 executable").apply {
        if (!exists()) { writeText("test executable"); setExecutable(true) }
    }
    private val flags get() = File(root, "feature flags.txt").apply {
        if (!exists()) writeText("com.android.systemui.test_flag:READ_ONLY=true\n")
    }
    private val reference = "    <color name=\"c\">@androidprv:color/example</color>\n"

    private fun xml(body: String = reference, declaration: String = "") =
        "<?xml version=\"1.0\" encoding=\"utf-8\"?>\n" +
            "<resources xmlns:android=\"http://schemas.android.com/apk/res/android\"$declaration>\n" +
            body + "</resources>\n"

    private fun add(relative: String, text: String = xml()): File =
        File(merged, relative).apply { parentFile.mkdirs(); writeText(text) }

    private fun flat(name: String, text: String = "ORIGINAL"): File =
        File(compiled, name).apply { writeText(text) }

    private fun repair(compile: (List<String>) -> Unit = ::fakeCompile) =
        AndroidPrvResourceRepair.repair(merged, compiled, aapt2, flags, scratch, compile)

    private fun fakeCompile(command: List<String>) {
        assertEquals(aapt2.absolutePath, command[0])
        assertEquals("compile", command[1])
        assertEquals("--feature-flags", command[2])
        assertEquals("@${flags.absolutePath}", command[3])
        assertEquals("-o", command[5])
        assertEquals(7, command.size)
        val source = File(command[4])
        assertTrue(source.toPath().startsWith(scratch.toPath()))
        assertTrue(source.readText().contains(AndroidPrvResourceRepair.DECLARATION))
        assertFalse(source.readText().contains('\r'))
        File(command[6], AndroidPrvResourceRepair.flatName(source))
            .writeText("FLAT:${source.name}\n${flags.readText()}")
    }

    @Test
    fun `flat names match qualified and plain AAPT2 values outputs`() {
        for (directory in listOf("values", "values-night-v8", "values-sw600dp-land-v13")) {
            assertEquals("${directory}_${directory}.arsc.flat",
                AndroidPrvResourceRepair.flatName(File(directory, "$directory.xml")))
        }
    }

    @Test
    fun `declaration is inserted once and existing declaration is unchanged`() {
        val patched = AndroidPrvResourceRepair.injectDeclaration(xml())
        assertTrue(patched.contains("xmlns:android=\"http://schemas.android.com/apk/res/android\""))
        assertEquals(1, Regex("xmlns:androidprv=").findAll(patched).count())
        assertEquals(patched, AndroidPrvResourceRepair.injectDeclaration(patched))
    }

    @Test
    fun `duplicate declarations and missing resources root fail`() {
        assertThrows(IllegalStateException::class.java) {
            AndroidPrvResourceRepair.injectDeclaration(xml(declaration =
                " ${AndroidPrvResourceRepair.DECLARATION} ${AndroidPrvResourceRepair.DECLARATION}"))
        }
        assertThrows(IllegalStateException::class.java) {
            AndroidPrvResourceRepair.injectDeclaration("<other/>")
        }
    }

    @Test
    fun `repair preserves merger bytes and untouched flats and forwards flags`() {
        val original = add("values/values.xml", xml().replace("\n", "\r\n"))
        val before = original.readBytes()
        add("values-night-v8/values-night-v8.xml")
        add("values-land/values-land.xml", xml("<color name=\"c\">#ffffff</color>"))
        flat("values_values.arsc.flat")
        flat("values-night-v8_values-night-v8.arsc.flat")
        val untouched = flat("values-land_values-land.arsc.flat", "KEEP")
        assertEquals("scanned=3 patched=2 compiled=2 unresolved=0", repair().toString())
        assertArrayEquals(before, original.readBytes())
        assertEquals("KEEP", untouched.readText())
        assertEquals("FLAT:values.xml\n${flags.readText()}", File(compiled, "values_values.arsc.flat").readText())
        assertEquals(emptyList<File>(), scratch.listFiles()!!.toList())
    }

    @Test
    fun `repeated execution repairs flats even if merger was up to date`() {
        add("values/values.xml")
        val output = flat("values_values.arsc.flat")
        val first = repair()
        val expected = output.readBytes()
        output.writeText("REPLACED BY MERGER")
        assertEquals(first, repair())
        assertArrayEquals(expected, output.readBytes())
    }

    @Test
    fun `already declared candidate is left untouched`() {
        val source = add("values/values.xml", xml(declaration = " ${AndroidPrvResourceRepair.DECLARATION}"))
        val before = source.readBytes()
        val output = flat("values_values.arsc.flat", "KEEP")
        assertEquals("scanned=1 patched=0 compiled=0 unresolved=0",
            repair { fail<Unit>("No compilation expected") }.toString())
        assertArrayEquals(before, source.readBytes())
        assertEquals("KEEP", output.readText())
    }

    @Test
    fun `zero candidates is a hard failure rather than silent success`() {
        add("values/values.xml", xml("<color name=\"c\">#ffffff</color>"))
        val error = assertThrows(IllegalStateException::class.java) { repair() }
        assertTrue(error.message!!.contains("no androidprv references"))
    }

    @Test
    fun `invalid candidate prevents any compilation or replacement`() {
        add("values/values.xml")
        add("values-night/values-night.xml", xml(declaration =
            " ${AndroidPrvResourceRepair.DECLARATION} ${AndroidPrvResourceRepair.DECLARATION}"))
        val output = flat("values_values.arsc.flat")
        assertThrows(IllegalStateException::class.java) {
            repair { fail<Unit>("Validation must precede compilation") }
        }
        assertEquals("ORIGINAL", output.readText())
    }

    @Test
    fun `compiler failure preserves all existing flats and cleans staging`() {
        add("values/values.xml")
        add("values-night/values-night.xml")
        val outputs = listOf(flat("values_values.arsc.flat"), flat("values-night_values-night.arsc.flat"))
        var calls = 0
        val error = assertThrows(IllegalStateException::class.java) {
            repair { command ->
                if (++calls == 2) error("fake compile failure")
                fakeCompile(command)
            }
        }
        assertEquals(2, calls)
        assertTrue(error.message!!.contains("AAPT2 compile failed"))
        assertTrue(outputs.all { it.readText() == "ORIGINAL" })
        assertEquals(emptyList<File>(), scratch.listFiles()!!.toList())
    }

    @Test
    fun `missing compiled output fails and never reuses stale staging`() {
        add("values/values.xml")
        val output = flat("values_values.arsc.flat")
        repair()
        val before = output.readBytes()
        val error = assertThrows(IllegalStateException::class.java) { repair { } }
        assertTrue(error.message!!.contains("expected flat output missing"))
        assertArrayEquals(before, output.readBytes())
        assertEquals(emptyList<File>(), scratch.listFiles()!!.toList())
    }

    @Test
    fun `repair cannot create a previously absent AGP output`() {
        add("values/values.xml")
        val error = assertThrows(IllegalStateException::class.java) { repair() }
        assertTrue(error.message!!.contains("no existing flat to replace"))
        assertEquals(emptyList<File>(), compiled.listFiles()!!.toList())
    }

    @Test
    fun `missing inputs fail before compiler invocation`() {
        val inputs = listOf(merged, compiled, aapt2, flags)
        for (index in inputs.indices) {
            val invalid = inputs.toMutableList().apply { set(index, File(root, "missing-$index")) }
            assertThrows(IllegalStateException::class.java) {
                AndroidPrvResourceRepair.repair(invalid[0], invalid[1], invalid[2], invalid[3], scratch) {
                    fail<Unit>("Missing inputs must fail first")
                }
            }
        }
    }

    @Test
    fun `checked in AOSP flag file retains format and resource guards`() {
        val repo = File(requireNotNull(System.getProperty("task081.repo.root")))
        val lines = File(repo, "libs/systemui-aconfig-flags.txt").readLines()
        val format = Regex("com\\.android\\.systemui\\.[a-z0-9_]+:(READ_WRITE|READ_ONLY)=(true|false)")
        assertTrue(lines.size > 100)
        assertTrue(lines.all { it.matches(format) })
        assertTrue("com.android.systemui.dream_overlay_updated_ui:READ_ONLY=true" in lines)
        assertTrue("com.android.systemui.desktop_sizing:READ_ONLY=false" in lines)
    }
}
