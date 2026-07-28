/*
 * Copyright (C) 2024 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package platform.test.motion.compose.values

import androidx.compose.runtime.Stable
import androidx.compose.ui.Modifier
import androidx.compose.ui.node.CompositionLocalConsumerModifierNode
import androidx.compose.ui.node.ModifierNodeElement
import androidx.compose.ui.node.SemanticsModifierNode
import androidx.compose.ui.node.currentValueOf
import androidx.compose.ui.platform.InspectorInfo
import androidx.compose.ui.semantics.SemanticsPropertyKey
import androidx.compose.ui.semantics.SemanticsPropertyReceiver

/**
 * A key for a value exported to motion tests.
 *
 * No two instances of the key are identical, no matter the [name]. Code exporting values using this
 * method must also provide access to this instance for the test.
 */
class MotionTestValueKey<T>(name: String) {
    val semanticsPropertyKey = SemanticsPropertyKey<T>(name)

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is MotionTestValueKey<*>) return false

        return semanticsPropertyKey == other.semanticsPropertyKey
    }

    override fun hashCode(): Int {
        return semanticsPropertyKey.hashCode()
    }
}

interface MotionTestValueScope {
    infix fun <T> T.exportAs(key: MotionTestValueKey<T>)
}

/**
 * Exports a value for motion tests.
 *
 * [values] is not read except during the test, thus does not trigger additional recompositions.
 */
@Stable
fun Modifier.motionTestValues(values: MotionTestValueScope.() -> Unit) =
    this then MotionTestValuesElement(values)

private data class MotionTestValuesElement(val values: MotionTestValueScope.() -> Unit) :
    ModifierNodeElement<MotionTestValuesNode>() {

    override fun create(): MotionTestValuesNode {
        return MotionTestValuesNode(values)
    }

    override fun update(node: MotionTestValuesNode) {
        node.values = values
    }

    override fun InspectorInfo.inspectableProperties() {
        name = "motionTestValues"
    }
}

private class MotionTestValuesNode(var values: MotionTestValueScope.() -> Unit) :
    Modifier.Node(), SemanticsModifierNode, CompositionLocalConsumerModifierNode {

    override fun SemanticsPropertyReceiver.applySemantics() {
        if (currentValueOf(LocalEnableMotionTestValueCollection)) {
            values.invoke(
                object : MotionTestValueScope {
                    override fun <T> T.exportAs(key: MotionTestValueKey<T>) {
                        this@applySemantics[key.semanticsPropertyKey] = this
                    }
                }
            )
        }
    }
}
