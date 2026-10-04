package com.android.systemui.resources

import org.gradle.api.tasks.InputDirectory
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.Internal
import org.gradle.testfixtures.ProjectBuilder
import org.gradle.work.DisableCachingByDefault
import org.junit.jupiter.api.Assertions.*
import org.junit.jupiter.api.Test
import org.junit.jupiter.api.io.TempDir
import java.io.File

class PatchAndroidPrvMergedResourcesTaskTest {
    @TempDir
    lateinit var root: File

    @Test
    fun `task uses managed inputs and does not own AGP output directories`() {
        val project = ProjectBuilder.builder().withProjectDir(root).build()
        val task = project.tasks.register("repair", PatchAndroidPrvMergedResourcesTask::class.java).get()
        val type = PatchAndroidPrvMergedResourcesTask::class.java
        assertNotNull(type.getAnnotation(DisableCachingByDefault::class.java))
        assertNotNull(type.getMethod("getMergedResources").getAnnotation(InputDirectory::class.java))
        assertNotNull(type.getMethod("getCompiledResources").getAnnotation(Internal::class.java))
        for (getter in listOf("getAapt2Executable", "getFeatureFlagsFile")) {
            assertNotNull(type.getMethod(getter).getAnnotation(InputFile::class.java))
        }
        assertTrue(task.outputs.files.isEmpty)
    }

    @Test
    fun `task action consumes configured inputs without project lookup or Python`() {
        val project = ProjectBuilder.builder().withProjectDir(root).build()
        val task = project.tasks.register("repair", PatchAndroidPrvMergedResourcesTask::class.java).get()
        val merged = File(root, "merged dir").apply { mkdirs() }
        val compiled = File(root, "compiled dir").apply { mkdirs() }
        val source = File(merged, "values/values.xml").apply {
            parentFile.mkdirs()
            writeText("<resources ${AndroidPrvResourceRepair.DECLARATION}>" +
                "<color name=\"c\">@androidprv:color/example</color></resources>")
        }
        val before = source.readBytes()
        val flat = File(compiled, "values_values.arsc.flat").apply { writeText("KEEP") }
        // Already declared XML needs no native compile. A real AAPT2 execution
        // is verified by the app's two variant builds, not faked by a shell.
        val executable = File(root, "unused aapt2").apply {
            writeText("not invoked"); setExecutable(true)
        }
        val flags = File(root, "flags.txt").apply { writeText("test:READ_ONLY=true\n") }
        task.mergedResources.set(merged)
        task.compiledResources.set(compiled)
        task.aapt2Executable.set(executable)
        task.featureFlagsFile.set(flags)
        task.repairResources()
        assertArrayEquals(before, source.readBytes())
        assertEquals("KEEP", flat.readText())
        assertTrue(task.outputs.files.isEmpty)
    }
}
