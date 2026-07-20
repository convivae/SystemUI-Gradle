package test
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers

class TestFile {
    val v = MutableStateFlow("hi").stateIn(
        scope = object : CoroutineScope {
            override val coroutineContext = Dispatchers.Unconfined
        },
        started = SharingStarted.Eagerly,
        initialValue = "init"
    )
}
