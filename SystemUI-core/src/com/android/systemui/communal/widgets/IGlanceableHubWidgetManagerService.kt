package com.android.systemui.communal.widgets

import android.appwidget.AppWidgetProviderInfo
import android.content.ComponentName
import android.content.IntentSender
import android.os.UserHandle
import android.widget.RemoteViews
import com.android.systemui.communal.shared.model.CommunalWidgetContentModel

interface IGlanceableHubWidgetManagerService {
    interface IConfigureWidgetCallback {
        fun onConfigured(result: Int)
    }

    interface IAppWidgetHostListener {
        fun onUpdate(
            appWidgetId: Int,
            views: RemoteViews?,
            providerInfo: AppWidgetProviderInfo?
        )
        fun onDeleted(appWidgetId: Int)
        fun onError(
            appWidgetId: Int,
            exception: Throwable?
        )
        fun onProvisioned()
    }

    interface IGlanceableHubWidgetsListener {
        fun onWidgetsUpdated(widgets: List<CommunalWidgetContentModel>)
    }

    fun addWidgetsListener(listener: IGlanceableHubWidgetsListener)
    fun removeWidgetsListener(listener: IGlanceableHubWidgetsListener)
    fun setAppWidgetHostListener(appWidgetId: Int, listener: IAppWidgetHostListener)
    fun addWidget(
        provider: ComponentName,
        user: UserHandle,
        rank: Int,
        callback: IConfigureWidgetCallback
    )
    fun deleteWidget(appWidgetId: Int)
    fun startReordering()
    fun finishReordering()
}
