// Gradle script to dynamically replace SDK's android.jar with merged version
// This allows accessing hidden platform APIs without permanently modifying the SDK

import java.io.File

// Get the SDK directory from local.properties or environment
val sdkDir: String = providers.environmentVariable("ANDROID_HOME").orNull
    ?: providers.environmentVariable("ANDROID_SDK_ROOT").orNull
    ?: run {
        val localProps = rootProject.file("local.properties")
        if (localProps.exists()) {
            val props = java.util.Properties()
            props.load(localProps.inputStream())
            props.getProperty("sdk.dir") ?: throw GradleException("SDK directory not found. Set ANDROID_HOME or sdk.dir in local.properties")
        } else {
            throw GradleException("SDK directory not found. Set ANDROID_HOME or create local.properties with sdk.dir")
        }
    }

val mergedJar = rootProject.file("libs/platform/android.jar")
val originalJar = File("$sdkDir/platforms/android-37.0/android.jar")
val backupJar = File("$sdkDir/platforms/android-37.0/android.jar.backup")

// Task to backup original android.jar
val backupSdkJar by tasks.registering {
    description = "Backup original SDK android.jar"
    doFirst {
        if (!backupJar.exists() && originalJar.exists()) {
            originalJar.copyTo(backupJar, overwrite = true)
            println("Backed up original android.jar to ${backupJar.absolutePath}")
        }
    }
}

// Task to replace with merged android.jar
val replaceSdkJar by tasks.registering {
    description = "Replace SDK android.jar with merged version"
    dependsOn(backupSdkJar)
    doFirst {
        if (mergedJar.exists()) {
            mergedJar.copyTo(originalJar, overwrite = true)
            println("Replaced android.jar with merged version")
        } else {
            throw GradleException("Merged android.jar not found at ${mergedJar.absolutePath}. Run 'createMergedJar' first.")
        }
    }
}

// Task to restore original android.jar
val restoreSdkJar by tasks.registering {
    description = "Restore original SDK android.jar"
    doFirst {
        if (backupJar.exists()) {
            backupJar.copyTo(originalJar, overwrite = true)
            println("Restored original android.jar")
        }
    }
}

// Configure all Android tasks to use the merged jar
subprojects {
    tasks.withType<com.android.build.gradle.tasks.JavaCompileCreationAction>().configureEach {
        dependsOn(replaceSdkJar)
        finalizedBy(restoreSdkJar)
    }
}

// Task to create the merged jar (run once)
val createMergedJar by tasks.registering {
    description = "Create merged android.jar from SDK and AOSP framework.jar"
    doFirst {
        val sdkJar = originalJar
        val frameworkJar = rootProject.file("libs/framework.jar")

        if (!sdkJar.exists()) {
            throw GradleException("SDK android.jar not found at ${sdkJar.absolutePath}")
        }
        if (!frameworkJar.exists()) {
            throw GradleException("AOSP framework.jar not found at ${frameworkJar.absolutePath}")
        }

        // Create temporary directory for extraction
        val tempDir = File(temporaryDir, "merge")
        tempDir.mkdirs()

        // Extract both jars
        println("Extracting SDK android.jar...")
        exec {
            commandLine("jar", "xf", sdkJar.absolutePath)
            workingDir = tempDir
        }

        println("Extracting AOSP framework.jar...")
        exec {
            commandLine("jar", "xf", frameworkJar.absolutePath)
            workingDir = tempDir
        }

        // Create merged jar
        println("Creating merged android.jar...")
        mergedJar.parentFile.mkdirs()
        exec {
            commandLine("jar", "cf", mergedJar.absolutePath, ".")
            workingDir = tempDir
        }

        // Cleanup
        tempDir.deleteRecursively()

        println("Merged android.jar created at ${mergedJar.absolutePath}")
        println("Size: ${mergedJar.length() / 1024 / 1024} MB")
    }
}
