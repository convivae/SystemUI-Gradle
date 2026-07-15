// SYSOPS: stub Application. The real SystemUI bootstraps its Dagger graph here;
// v1 skeleton ships the minimal class so the APK installs and can be pushed to device.
package com.android.systemui;

import android.app.Application;

public class SystemUIApplication extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
    }
}
