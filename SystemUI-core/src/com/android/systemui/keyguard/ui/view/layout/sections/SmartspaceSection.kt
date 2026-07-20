/*
 * Copyright (C) 2023 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.android.systemui.keyguard.ui.view.layout.sections

import com.android.systemui.R

import android.content.Context
import android.view.View
import android.view.ViewGroup
import android.view.ViewTreeObserver.OnGlobalLayoutListener
import androidx.constraintlayout.widget.Barrier
import androidx.constraintlayout.widget.ConstraintLayout
import androidx.constraintlayout.widget.ConstraintSet
import com.android.systemui.dagger.SysUISingleton
import com.android.systemui.keyguard.KeyguardUnlockAnimationController
import com.android.systemui.keyguard.MigrateClocksToBlueprint
import com.android.systemui.keyguard.domain.interactor.KeyguardBlueprintInteractor
import com.android.systemui.keyguard.domain.interactor.KeyguardSmartspaceInteractor
import com.android.systemui.keyguard.shared.model.KeyguardSection
import com.android.systemui.keyguard.ui.binder.KeyguardSmartspaceViewBinder
import com.android.systemui.keyguard.ui.viewmodel.KeyguardClockViewModel
import com.android.systemui.keyguard.ui.viewmodel.KeyguardSmartspaceViewModel
import com.android.systemui.shade.ShadeDisplayAware
import com.android.systemui.statusbar.lockscreen.LockscreenSmartspaceController
import dagger.Lazy
import javax.inject.Inject
import kotlinx.coroutines.DisposableHandle

@SysUISingleton
open class SmartspaceSection
@Inject
constructor(
    @ShadeDisplayAware val context: Context,
    val keyguardClockViewModel: KeyguardClockViewModel,
    val keyguardSmartspaceViewModel: KeyguardSmartspaceViewModel,
    private val keyguardSmartspaceInteractor: KeyguardSmartspaceInteractor,
    val smartspaceController: LockscreenSmartspaceController,
    val keyguardUnlockAnimationController: KeyguardUnlockAnimationController,
    private val blueprintInteractor: Lazy<KeyguardBlueprintInteractor>,
) : KeyguardSection() {
    private var smartspaceView: View? = null
    private var weatherView: View? = null
    private var dateWeatherView: ViewGroup? = null

    private var smartspaceVisibilityListener: OnGlobalLayoutListener? = null
    private var pastVisibility: Int = -1
    private var disposableHandle: DisposableHandle? = null

    override fun onRebuildBegin() {
        smartspaceController.suppressDisconnects = true
    }

    override fun onRebuildEnd() {
        smartspaceController.suppressDisconnects = false
    }

    override fun addViews(constraintLayout: ConstraintLayout) {
        if (!MigrateClocksToBlueprint.isEnabled) return
        if (!keyguardSmartspaceViewModel.isSmartspaceEnabled) return
        smartspaceView = smartspaceController.buildAndConnectView(constraintLayout)
        weatherView = smartspaceController.buildAndConnectWeatherView(constraintLayout)
        dateWeatherView =
            smartspaceController.buildAndConnectDateView(constraintLayout) as ViewGroup
        pastVisibility = smartspaceView?.visibility ?: View.GONE
        constraintLayout.addView(smartspaceView)
        if (keyguardSmartspaceViewModel.isDateWeatherDecoupled) {
            constraintLayout.addView(dateWeatherView)
            // Place weather right after the date, before the extras (alarm and dnd)
            val index = if (dateWeatherView?.childCount == 0) 0 else 1
            dateWeatherView?.addView(weatherView, index)
        }
        keyguardUnlockAnimationController.lockscreenSmartspace = smartspaceView
        smartspaceVisibilityListener = OnGlobalLayoutListener {
            smartspaceView?.let {
                val newVisibility = it.visibility
                if (pastVisibility != newVisibility) {
                    keyguardSmartspaceInteractor.setBcSmartspaceVisibility(newVisibility)
                    pastVisibility = newVisibility
                }
            }
        }
        smartspaceView?.viewTreeObserver?.addOnGlobalLayoutListener(smartspaceVisibilityListener)
    }

    override fun bindData(constraintLayout: ConstraintLayout) {
        if (!MigrateClocksToBlueprint.isEnabled) return
        if (!keyguardSmartspaceViewModel.isSmartspaceEnabled) return
        disposableHandle?.dispose()
        disposableHandle =
            KeyguardSmartspaceViewBinder.bind(
                constraintLayout,
                keyguardClockViewModel,
                keyguardSmartspaceViewModel,
                blueprintInteractor.get(),
            )
    }

    override fun applyConstraints(constraintSet: ConstraintSet) {
        if (!MigrateClocksToBlueprint.isEnabled) return
        if (!keyguardSmartspaceViewModel.isSmartspaceEnabled) return
        val dateWeatherPaddingStart = KeyguardSmartspaceViewModel.getDateWeatherStartMargin(context)
        val smartspaceHorizontalPadding =
            KeyguardSmartspaceViewModel.getSmartspaceHorizontalMargin(context)
        constraintSet.apply {
            // migrate addDateWeatherView, addWeatherView from KeyguardClockSwitchController
            constrainHeight(R.id.date_smartspace_view, ConstraintSet.WRAP_CONTENT)
            constrainWidth(R.id.date_smartspace_view, ConstraintSet.WRAP_CONTENT)
            connect(
                R.id.date_smartspace_view,
                ConstraintSet.START,
                ConstraintSet.PARENT_ID,
                ConstraintSet.START,
                dateWeatherPaddingStart,
            )

            // migrate addSmartspaceView from KeyguardClockSwitchController
            constrainHeight(R.id.bc_smartspace_view, ConstraintSet.WRAP_CONTENT)
            constrainWidth(R.id.bc_smartspace_view, ConstraintSet.MATCH_CONSTRAINT)
            connect(
                R.id.bc_smartspace_view,
                ConstraintSet.START,
                ConstraintSet.PARENT_ID,
                ConstraintSet.START,
                smartspaceHorizontalPadding,
            )
            connect(
                R.id.bc_smartspace_view,
                ConstraintSet.END,
                if (keyguardSmartspaceViewModel.isShadeLayoutWide.value) R.id.split_shade_guideline
                else ConstraintSet.PARENT_ID,
                ConstraintSet.END,
                smartspaceHorizontalPadding,
            )

            if (keyguardClockViewModel.hasCustomWeatherDataDisplay.value) {
                clear(R.id.date_smartspace_view, ConstraintSet.TOP)
                connect(
                    R.id.date_smartspace_view,
                    ConstraintSet.BOTTOM,
                    R.id.bc_smartspace_view,
                    ConstraintSet.TOP,
                )
            } else {
                clear(R.id.date_smartspace_view, ConstraintSet.BOTTOM)
                connect(
                    R.id.date_smartspace_view,
                    ConstraintSet.TOP,
                    R.id.lockscreen_clock_view,
                    ConstraintSet.BOTTOM,
                )
                connect(
                    R.id.bc_smartspace_view,
                    ConstraintSet.TOP,
                    R.id.date_smartspace_view,
                    ConstraintSet.BOTTOM,
                )
            }

            createBarrier(
                R.id.smart_space_barrier_bottom,
                Barrier.BOTTOM,
                0,
                *intArrayOf(R.id.bc_smartspace_view, R.id.date_smartspace_view),
            )
        }
        updateVisibility(constraintSet)
    }

    override fun removeViews(constraintLayout: ConstraintLayout) {
        if (!MigrateClocksToBlueprint.isEnabled) return
        if (!keyguardSmartspaceViewModel.isSmartspaceEnabled) return
        listOf(smartspaceView, dateWeatherView).forEach {
            it?.let {
                if (it.parent == constraintLayout) {
                    constraintLayout.removeView(it)
                }
            }
        }
        smartspaceView?.viewTreeObserver?.removeOnGlobalLayoutListener(smartspaceVisibilityListener)
        smartspaceVisibilityListener = null

        disposableHandle?.dispose()
    }

    private fun updateVisibility(constraintSet: ConstraintSet) {
        // This may update the visibility of the smartspace views
        smartspaceController.requestSmartspaceUpdate()

        constraintSet.apply {
            val weatherVisibility =
                when (keyguardSmartspaceViewModel.isWeatherVisible.value) {
                    true -> ConstraintSet.VISIBLE
                    false -> ConstraintSet.GONE
                }
            setVisibility(R.id.weather_smartspace_view, weatherVisibility)
            setAlpha(
                R.id.weather_smartspace_view,
                if (weatherVisibility == View.VISIBLE) 1f else 0f,
            )
            val dateVisibility =
                if (keyguardClockViewModel.hasCustomWeatherDataDisplay.value) ConstraintSet.GONE
                else ConstraintSet.VISIBLE
            setVisibility(R.id.date_smartspace_view, dateVisibility)
            setAlpha(
                R.id.date_smartspace_view,
                if (dateVisibility == ConstraintSet.VISIBLE) 1f else 0f,
            )
        }
    }
}
