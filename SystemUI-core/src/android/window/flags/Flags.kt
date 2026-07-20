package android.window.flags

object Flags {
    @JvmField val ENABLE_SHELL_TRANSITIONS = true
    @JvmField val ENABLE_PREDICTIVE_BACK = true
    @JvmField val ALWAYS_ENFORCE_PREDICTIVE_BACK = false

    // Function-style accessors
    fun enableShellTransitions(): Boolean = ENABLE_SHELL_TRANSITIONS
    fun enablePredictiveBack(): Boolean = ENABLE_PREDICTIVE_BACK
    fun ensureKeyguardDoesTransitionStarting(): Boolean = false
}
