package android.appwidget;

import android.appwidget.AppWidgetProviderInfo;
import android.content.Context;
import android.os.Bundle;
import android.widget.RemoteViews;

public class AppWidgetHost {
    public interface AppWidgetHostListener {
        void onUpdate(int appWidgetId, RemoteViews views, AppWidgetProviderInfo info);
        void onProviderChanged(int appWidgetId, AppWidgetProviderInfo info);
        void onViewDataChanged(int appWidgetId, int viewId);
        void onAppWidgetRemoved(int appWidgetId);
        void onAppWidgetHidden(int appWidgetId);
    }
}
