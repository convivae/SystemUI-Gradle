package com.android.systemui.util.kotlin

import android.content.Context
import android.os.UserHandle

val Context.userId: Int
    get() = UserHandle.myUserId()
