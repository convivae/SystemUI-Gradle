package com.android.systemui.aconfigrewrite

import com.android.build.api.instrumentation.FramesComputationMode
import com.android.build.api.instrumentation.InstrumentationScope
import com.android.build.api.variant.Instrumentation
import org.gradle.api.provider.MapProperty
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.File
import java.lang.reflect.Proxy
import java.nio.charset.StandardCharsets

class AconfigInstrumentationRegistrationTest {
    private val repositoryRoot = File(System.getProperty("task081.repo.root") ?: "..").canonicalFile
    private val rulesFile = File(repositoryRoot, "gradle/aosp17-aconfig-repackaging-rules.txt")

    @Test
    fun `registration is application-only with ALL scope COPY_FRAMES and the full rule set`() {
        val frozenInputs = FrozenAconfigInputs.load(rulesFile)
        assertEquals(FrozenAconfigInputs.RULE_COUNT, frozenInputs.mappings.size)

        val mapRecorder = MapPropertyRecorder()
        val applicationCalls = mutableListOf<RecordedCall>()
        val applicationInstrumentation = recordingInstrumentation(
            applicationCalls,
            RecordingParameters(recordingMapProperty(mapRecorder)),
        )

        assertTrue(
            AconfigInstrumentationRegistration.registerForPlugin(
                pluginId = "com.android.application",
                instrumentation = applicationInstrumentation,
                frozenInputs = frozenInputs,
            ),
        )
        assertEquals(
            listOf(
                RecordedCall(
                    "transformClassesWith",
                    AconfigReferenceRewriteFactory::class.java,
                    InstrumentationScope.ALL,
                ),
                RecordedCall("setAsmFramesComputationMode", null, FramesComputationMode.COPY_FRAMES),
            ),
            applicationCalls,
        )
        assertEquals(listOf<Any?>(frozenInputs.mappings), mapRecorder.putAllCalls)
        assertEquals(frozenInputs.mappings, mapRecorder.value)

        for (nonApplicationPlugin in listOf("com.android.library", "com.android.dynamic-feature", "java-library")) {
            val calls = mutableListOf<RecordedCall>()
            val untouchedMap = MapPropertyRecorder()
            assertFalse(
                AconfigInstrumentationRegistration.registerForPlugin(
                    pluginId = nonApplicationPlugin,
                    instrumentation = recordingInstrumentation(
                        calls,
                        RecordingParameters(recordingMapProperty(untouchedMap)),
                    ),
                    frozenInputs = frozenInputs,
                ),
            )
            assertTrue(calls.isEmpty())
            assertTrue(untouchedMap.putAllCalls.isEmpty() && untouchedMap.putCalls.isEmpty())
        }
    }

    @Test
    fun `production seam carries no skip-set or allowlist`() {
        // Task 099 Chief decision (D8 lambda lesson): the factory instruments
        // EVERY class, so the only wiring state is the frozen 725-rule
        // mapping set. Hidden platform definitions are refused inside the
        // rewriter (fail-closed), not via a filter skip-set, and no caller
        // allowlist exists anywhere in the seam.
        val getters = AconfigReferenceRewriteParameters::class.java.declaredMethods
            .map { it.name }
            .sorted()
        assertEquals(listOf("getMappings"), getters)
    }

    private fun recordingInstrumentation(
        calls: MutableList<RecordedCall>,
        parameters: AconfigReferenceRewriteParameters,
    ): Instrumentation = Proxy.newProxyInstance(
        Instrumentation::class.java.classLoader,
        arrayOf(Instrumentation::class.java),
    ) { _, method, arguments ->
        when (method.name) {
            "transformClassesWith" -> {
                calls += RecordedCall(method.name, arguments!![0] as Class<*>, arguments[1])
                val parameterAction = arguments[2] as (AconfigReferenceRewriteParameters) -> Unit
                parameterAction(parameters)
                null
            }
            "setAsmFramesComputationMode" -> {
                calls += RecordedCall(method.name, null, arguments!![0])
                null
            }
            "toString" -> "RecordingInstrumentation"
            "hashCode" -> System.identityHashCode(calls)
            "equals" -> false
            else -> error("Unexpected Instrumentation method: ${method.name}")
        }
    } as Instrumentation

    private class MapPropertyRecorder {
        val putCalls = mutableListOf<List<Any?>>()
        val putAllCalls = mutableListOf<Any?>()
        val value = LinkedHashMap<Any?, Any?>()
    }

    private class RecordingParameters(
        override val mappings: MapProperty<String, String>,
    ) : AconfigReferenceRewriteParameters

    private fun recordingMapProperty(recorder: MapPropertyRecorder): MapProperty<String, String> =
        Proxy.newProxyInstance(
            MapProperty::class.java.classLoader,
            arrayOf(MapProperty::class.java),
        ) { _, method, args ->
            when (method.name) {
                "put" -> {
                    recorder.putCalls += args!!.toList()
                    null
                }
                "putAll" -> {
                    val entries = args!![0] as? Map<*, *>
                        ?: error("putAll called with unexpected argument: ${args[0]}")
                    recorder.putAllCalls += args[0]
                    recorder.value.putAll(entries)
                    null
                }
                "get" -> recorder.value.toMap()
                "toString" -> "RecordingMapProperty"
                "hashCode" -> System.identityHashCode(recorder)
                "equals" -> false
                else -> error("Unexpected MapProperty method: ${method.name}")
            }
        } as MapProperty<String, String>

    private data class RecordedCall(
        val method: String,
        val factoryClass: Class<*>?,
        val value: Any?,
    )
}
