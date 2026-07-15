// SYSOPS: stub service. The real SystemUIService is a massive component manager
// (~5k LoC); it is ported in a later feature task.
package com.android.systemui;

import android.app.Service;
import android.content.Intent;
import android.os.IBinder;

public class SystemUIService extends Service {
    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}
