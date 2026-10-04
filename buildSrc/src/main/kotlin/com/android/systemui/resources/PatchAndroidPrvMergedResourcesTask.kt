package com.android.systemui.resources

import org.gradle.api.DefaultTask
import org.gradle.api.file.DirectoryProperty
import org.gradle.api.file.RegularFileProperty
import org.gradle.api.tasks.InputDirectory
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.Internal
import org.gradle.api.tasks.PathSensitive
import org.gradle.api.tasks.PathSensitivity
import org.gradle.api.tasks.TaskAction
import org.gradle.process.ExecOperations
import org.gradle.work.DisableCachingByDefault
import javax.inject.Inject

/** Post-merge/pre-link repair using the build JVM and AGP's native AAPT2 only. */
@DisableCachingByDefault(because = "Repairs AGP-owned intermediates in place after resource merging")
abstract class PatchAndroidPrvMergedResourcesTask @Inject constructor(
    private val execOperations: ExecOperations,
) : DefaultTask() {
    @get:InputDirectory
    @get:PathSensitive(PathSensitivity.RELATIVE)
    abstract val mergedResources: DirectoryProperty

    // This mutable directory belongs to AGP. Do not claim it as this task's
    // output or cache it. With no declared outputs the repair runs every time,
    // including when mergeResources was UP-TO-DATE or restored from cache.
    @get:Internal
    abstract val compiledResources: DirectoryProperty

    @get:InputFile
    @get:PathSensitive(PathSensitivity.NONE)
    abstract val aapt2Executable: RegularFileProperty

    @get:InputFile
    @get:PathSensitive(PathSensitivity.NONE)
    abstract val featureFlagsFile: RegularFileProperty

    @TaskAction
    fun repairResources() {
        val summary = AndroidPrvResourceRepair.repair(
            mergedResources.get().asFile,
            compiledResources.get().asFile,
            aapt2Executable.get().asFile,
            featureFlagsFile.get().asFile,
            temporaryDir,
        ) { command ->
            execOperations.exec { commandLine(command) }.assertNormalExitValue()
        }
        logger.lifecycle(summary.toString())
    }
}
