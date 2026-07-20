package com.android.systemui

import android.hardware.input.InputManager
import android.hardware.input.KeyGestureEvent
import android.hardware.input.KeyGestureEventListener
import android.os.Handler
import java.util.concurrent.Executor

fun InputManager.registerKeyGestureEventListener(
    gestureType: Int,
    listener: KeyGestureEventListener,
    handler: Handler?
) {
    // Stub
}

fun InputManager.unregisterKeyGestureEventListener(listener: KeyGestureEventListener) {
    // Stub
}
