package com.android.systemui.aconfigrewrite

import com.android.build.api.instrumentation.FramesComputationMode
import com.android.build.api.instrumentation.InstrumentationScope
import com.android.build.api.variant.Instrumentation
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.File
import java.lang.reflect.Proxy

class AconfigInstrumentationRegistrationTest {
    @Test
    fun `registration is application-only with ALL scope and COPY_FRAMES`() {
        val applicationCalls = mutableListOf<RecordedCall>()
        val applicationInstrumentation = recordingInstrumentation(applicationCalls)

        assertTrue(
            AconfigInstrumentationRegistration.registerForPlugin(
                pluginId = "com.android.application",
                instrumentation = applicationInstrumentation,
                rulesFile = File("rules.txt"),
                allowlistFile = File("classes.txt"),
            ),
        )
        assertEquals(
            listOf(
                RecordedCall("transformClassesWith", InstrumentationScope.ALL),
                RecordedCall("setAsmFramesComputationMode", FramesComputationMode.COPY_FRAMES),
            ),
            applicationCalls,
        )

        for (nonApplicationPlugin in listOf("com.android.library", "com.android.dynamic-feature", "java-library")) {
            val calls = mutableListOf<RecordedCall>()
            assertFalse(
                AconfigInstrumentationRegistration.registerForPlugin(
                    pluginId = nonApplicationPlugin,
                    instrumentation = recordingInstrumentation(calls),
                    rulesFile = File("rules.txt"),
                    allowlistFile = File("classes.txt"),
                ),
            )
            assertTrue(calls.isEmpty())
        }
    }

    private fun recordingInstrumentation(calls: MutableList<RecordedCall>): Instrumentation =
        Proxy.newProxyInstance(
            Instrumentation::class.java.classLoader,
            arrayOf(Instrumentation::class.java),
        ) { _, method, arguments ->
            when (method.name) {
                "transformClassesWith" -> {
                    calls += RecordedCall(method.name, arguments!![1])
                    null
                }
                "setAsmFramesComputationMode" -> {
                    calls += RecordedCall(method.name, arguments!![0])
                    null
                }
                "toString" -> "RecordingInstrumentation"
                "hashCode" -> System.identityHashCode(calls)
                "equals" -> false
                else -> error("Unexpected Instrumentation method: ${method.name}")
            }
        } as Instrumentation

    private data class RecordedCall(val method: String, val value: Any)
}
