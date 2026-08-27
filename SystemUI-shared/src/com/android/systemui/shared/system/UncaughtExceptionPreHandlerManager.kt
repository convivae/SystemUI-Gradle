package com.android.systemui.shared.system

import android.util.Log
import java.lang.Thread.UncaughtExceptionHandler
import java.util.concurrent.CopyOnWriteArrayList
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Sets the global (static var in Thread) uncaught exception pre-handler to an implementation that
 * delegates to each item in a list of registered UncaughtExceptionHandlers.
 */
@Singleton
class UncaughtExceptionPreHandlerManager @Inject constructor() {
    private val handlers: MutableList<UncaughtExceptionHandler> = CopyOnWriteArrayList()
    private val globalUncaughtExceptionPreHandler = GlobalUncaughtExceptionHandler()

    /**
     * Adds an exception pre-handler to the list of handlers. If this has not yet set the global
     * (static var in Thread) uncaught exception pre-handler yet, it will do so.
     */
    fun registerHandler(handler: UncaughtExceptionHandler) {
        checkGlobalHandlerSetup()
        addHandler(handler)
    }

    /**
     * Verifies that the global handler is set in Thread. If not, sets is up.
     */
    private fun checkGlobalHandlerSetup() {
        // CONV_MOD BEGIN [task070] reason: Thread.get/setUncaughtExceptionPreHandler 仍为 @hide（libcore
        // ojluni，hiddenapi 注解未摘），SysUISdk android.jar 的 java.lang.Thread 无此方法，改用反射。
        // 依据：aosp17 libcore/ojluni/annotations/hiddenapi/java/lang/Thread.java L299/L305 + javap 实测。
        // 见 docs/issues/2026-08-07-uncaught-exception-prehandler-reflection.md 与 task070 issue 文档
        // val currentHandler = Thread.getUncaughtExceptionPreHandler()
        val currentHandler = runCatching {
            Thread::class.java.getDeclaredMethod("getUncaughtExceptionPreHandler")
                .apply { isAccessible = true }
                .invoke(null) as? UncaughtExceptionHandler
        }.getOrNull()
        // CONV_MOD END
        if (currentHandler != globalUncaughtExceptionPreHandler) {
            if (currentHandler is GlobalUncaughtExceptionHandler) {
                throw IllegalStateException("Two UncaughtExceptionPreHandlerManagers created")
            }
            currentHandler?.let { addHandler(it) }
            // CONV_MOD BEGIN [task070] reason: 同上，setUncaughtExceptionPreHandler 亦为隐藏 API，改用反射。
            // Thread.setUncaughtExceptionPreHandler(globalUncaughtExceptionPreHandler)
            runCatching {
                Thread::class.java.getDeclaredMethod(
                    "setUncaughtExceptionPreHandler", UncaughtExceptionHandler::class.java
                ).apply { isAccessible = true }
                    .invoke(null, globalUncaughtExceptionPreHandler)
            }.onFailure { e ->
                Log.w("UncaughtExceptionPreHandler", "Failed to set pre-handler via reflection", e)
            }
            // CONV_MOD END
        }
    }

    /**
     * Adds a handler if it has not already been added, preserving order.
     */
    private fun addHandler(it: UncaughtExceptionHandler) {
        if (it !in handlers) {
            handlers.add(it)
        }
    }

    /**
     * Calls uncaughtException on all registered handlers, catching and logging any new exceptions.
     */
    fun handleUncaughtException(thread: Thread?, throwable: Throwable?) {
        for (handler in handlers) {
            try {
                handler.uncaughtException(thread, throwable)
            } catch (e: Exception) {
                Log.wtf("Uncaught exception pre-handler error", e)
            }
        }
    }

    /**
     * UncaughtExceptionHandler impl that will be set as Thread's pre-handler static variable.
     */
    inner class GlobalUncaughtExceptionHandler : UncaughtExceptionHandler {
        override fun uncaughtException(thread: Thread?, throwable: Throwable?) {
            handleUncaughtException(thread, throwable)
        }
    }
}