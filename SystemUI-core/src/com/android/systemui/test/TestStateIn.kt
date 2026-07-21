package com.android.systemui.test
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.CoroutineScope

class TestStateIn {
    val test: Flow<String> = MutableStateFlow("test").stateIn(
        scope = object : CoroutineScope {
            override val coroutineContext = kotlinx.coroutines.Dispatchers.Unconfined
        },
        started = SharingStarted.Eagerly,
        initialValue = "init"
    )
}
