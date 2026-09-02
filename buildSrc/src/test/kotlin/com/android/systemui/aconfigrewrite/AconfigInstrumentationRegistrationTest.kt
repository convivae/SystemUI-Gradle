package com.android.systemui.aconfigrewrite

import com.android.build.api.instrumentation.FramesComputationMode
import com.android.build.api.instrumentation.InstrumentationScope
import com.android.build.api.variant.Instrumentation
import org.gradle.api.provider.MapProperty
import org.gradle.api.provider.SetProperty
import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Assertions.assertFalse
import org.junit.jupiter.api.Assertions.assertTrue
import org.junit.jupiter.api.Test
import java.io.File
import java.lang.reflect.Proxy
import java.nio.charset.StandardCharsets

class AconfigInstrumentationRegistrationTest {
    private val repositoryRoot = File(System.getProperty("task081.repo.root") ?: "..").canonicalFile
    private val rulesFile = File(repositoryRoot, "gradle/aosp17-critical-aconfig-reference-rules.txt")
    private val allowlistFile = File(repositoryRoot, "gradle/aosp17-critical-aconfig-reference-classes.txt")

    @Test
    fun `registration is application-only with ALL scope COPY_FRAMES and exact managed values`() {
        val frozenInputs = FrozenAconfigInputs.load(rulesFile, allowlistFile)
        val expectedMappings = linkedMapOf(
            "android.app.Flags" to
                "com.android.internal.hidden_from_bootclasspath.android.app.Flags",
            "android.os.Flags" to
                "com.android.internal.hidden_from_bootclasspath.android.os.Flags",
            "android.view.accessibility.Flags" to
                "com.android.internal.hidden_from_bootclasspath.android.view.accessibility.Flags",
            "com.android.window.flags.Flags" to
                "com.android.internal.hidden_from_bootclasspath.com.android.window.flags.Flags",
        )
        val expectedAllowlist = allowlistFile.readLines(StandardCharsets.UTF_8).toSet()
        assertEquals(expectedMappings, frozenInputs.mappings)
        assertEquals(expectedAllowlist, frozenInputs.allowlist)
        assertEquals(166, frozenInputs.allowlist.size)

        val mapRecorder = MapPropertyRecorder()
        val setRecorder = SetPropertyRecorder()
        val applicationCalls = mutableListOf<RecordedCall>()
        val applicationInstrumentation = recordingInstrumentation(
            applicationCalls,
            RecordingParameters(
                recordingMapProperty(mapRecorder),
                recordingSetProperty(setRecorder),
            ),
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
        assertEquals(listOf<Any?>(frozenInputs.allowlist), setRecorder.addAllCalls)
        assertEquals(expectedMappings, mapRecorder.value)
        assertEquals(expectedAllowlist, setRecorder.value)
        assertEquals(166, setRecorder.value.size)

        for (nonApplicationPlugin in listOf("com.android.library", "com.android.dynamic-feature", "java-library")) {
            val calls = mutableListOf<RecordedCall>()
            val untouchedMap = MapPropertyRecorder()
            val untouchedSet = SetPropertyRecorder()
            assertFalse(
                AconfigInstrumentationRegistration.registerForPlugin(
                    pluginId = nonApplicationPlugin,
                    instrumentation = recordingInstrumentation(
                        calls,
                        RecordingParameters(
                            recordingMapProperty(untouchedMap),
                            recordingSetProperty(untouchedSet),
                        ),
                    ),
                    frozenInputs = frozenInputs,
                ),
            )
            assertTrue(calls.isEmpty())
            assertTrue(untouchedMap.putAllCalls.isEmpty() && untouchedMap.putCalls.isEmpty())
            assertTrue(untouchedSet.addAllCalls.isEmpty() && untouchedSet.addCalls.isEmpty())
        }
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

    private class SetPropertyRecorder {
        val addCalls = mutableListOf<Any?>()
        val addAllCalls = mutableListOf<Any?>()
        val value = LinkedHashSet<Any?>()
    }

    private class RecordingParameters(
        override val mappings: MapProperty<String, String>,
        override val allowlist: SetProperty<String>,
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

    private fun recordingSetProperty(recorder: SetPropertyRecorder): SetProperty<String> =
        Proxy.newProxyInstance(
            SetProperty::class.java.classLoader,
            arrayOf(SetProperty::class.java),
        ) { _, method, args ->
            when (method.name) {
                "add" -> {
                    recorder.addCalls += args!![0]
                    recorder.value.add(args[0])
                    null
                }
                "addAll" -> {
                    val elements = args!![0] as? Iterable<*>
                        ?: error("addAll called with unexpected argument: ${args[0]}")
                    recorder.addAllCalls += args[0]
                    recorder.value.addAll(elements)
                    true
                }
                "get" -> recorder.value.toSet()
                "toString" -> "RecordingSetProperty"
                "hashCode" -> System.identityHashCode(recorder)
                "equals" -> false
                else -> error("Unexpected SetProperty method: ${method.name}")
            }
        } as SetProperty<String>

    private data class RecordedCall(
        val method: String,
        val factoryClass: Class<*>?,
        val value: Any?,
    )
}
