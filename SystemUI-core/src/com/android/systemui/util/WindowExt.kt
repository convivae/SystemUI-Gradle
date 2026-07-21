package com.android.systemui.util

import android.view.ViewRootImpl
import android.window.WindowOnBackInvokedDispatcher

val ViewRootImpl.onBackInvokedDispatcher: WindowOnBackInvokedDispatcher?
    get() = try {
        this::class.java.getMethod("getOnBackInvokedDispatcher").invoke(this) as? WindowOnBackInvokedDispatcher
    } catch (e: Throwable) {
        null
    }
