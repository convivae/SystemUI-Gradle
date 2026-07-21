package android.media.projection

/** Reasons for stopping media projection. */
object StopReason {
    const val NONE = 0
    const val ERROR_INVALID_STATE = 1
    const val ERROR_USER_CANCELED = 2
    const val ERROR_INTERNAL = 3
    const val PRESENTER_TAP = 4
    const val STOP_TIMER = 5
    const val TASK_ENDED = 6
    const val DEVICE_POLICY = 7
    const val USER_CHOOSE = 8
    const val SUPERVISOR_KILL = 9
    const val HOME_BUTTON = 10
    const val KEYGUARD = 11
    const val SYSTEM_ERROR = 12
}
