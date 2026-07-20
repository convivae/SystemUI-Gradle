package com.android.systemui.util.kotlin

import android.content.Context
import android.os.UserHandle
import com.android.systemui.util.kotlin.userId

val Context.userId: Int
    get() = UserHandle.myUserId()
