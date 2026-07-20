package com.android.systemui

object Flags {
    // All flags are generated from aconfig. Stub all as false.
    @JvmField val FLAG_COMMUNAL_HUB = false
    @JvmField val FLAG_STATUS_BAR_CALL_CHIP_NOTIFICATION_ICON = false
    @JvmField val FLAG_STATUS_BAR_SCREEN_SHARING_CHIPS = false
    @JvmField val FLAG_STATUS_BAR_USE_REPOS_FOR_CALL_CHIP = false
    @JvmField val FLAG_SCENE_CONTAINER = false

    // Method-style
    @JvmField val communalHub = false
    @JvmField val statusBarCallChipNotificationIcon = false
    @JvmField val sceneContainer = false
    @JvmField val msdlFeedback = false
    @JvmField val communalSceneKtfRefactor = false
    @JvmField val screenshareNotificationHiding = false
    @JvmField val quickaffordance = false

    // Generic getter
    @JvmStatic fun getFlag(name: String): Boolean = false
}
