/*
 * Copyright (C) 2024 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License
 */

package com.android.traceur;

import android.os.Build;
import android.util.ArraySet;

import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.Set;

public class PresetTraceConfigs {

    private static final List<String> DEFAULT_TRACE_TAGS = Arrays.asList(
            "aidl", "am", "binder_driver", "camera", "dalvik", "disk", "freq",
            "gfx", "hal", "idle", "input", "memory", "memreclaim", "network", "power",
            "res", "sched", "ss", "sync", "thermal", "view", "webview", "wm", "workq");

    private static final List<String> PERFORMANCE_TRACE_TAGS = DEFAULT_TRACE_TAGS;
    private static final List<String> UI_TRACE_TAGS = DEFAULT_TRACE_TAGS;

    private static final List<String> THERMAL_TRACE_TAGS = Arrays.asList(
            "aidl", "am", "binder_driver", "camera", "dalvik", "disk", "freq",
            "gfx", "hal", "idle", "input", "memory", "memreclaim", "network", "power",
            "res", "sched", "ss", "sync", "thermal", "thermal_tj", "view", "webview",
            "wm", "workq");

    private static final List<String> BATTERY_TRACE_TAGS = Arrays.asList(
            "aidl", "am", "binder_driver", "network", "nnapi",
            "pm", "power", "ss", "thermal", "wm");

    private static final List<String> USER_BUILD_DISABLED_TRACE_TAGS = Arrays.asList(
            "workq", "sync");

    private static Set<String> mDefaultTagList = null;
    private static Set<String> mPerformanceTagList = null;
    private static Set<String> mBatteryTagList = null;
    private static Set<String> mThermalTagList = null;
    private static Set<String> mUiTagList = null;

    public static TraceConfig getDefaultConfig() {
        if (mDefaultTagList == null) {
            mDefaultTagList = new ArraySet<>(DEFAULT_TRACE_TAGS);
            updateTagsIfUserBuild(mDefaultTagList);
        }
        return new TraceConfig(DEFAULT_TRACE_OPTIONS, mDefaultTagList);
    }

    public static TraceConfig getPerformanceConfig() {
        if (mPerformanceTagList == null) {
            mPerformanceTagList = new ArraySet<>(PERFORMANCE_TRACE_TAGS);
            updateTagsIfUserBuild(mPerformanceTagList);
        }
        return new TraceConfig(PERFORMANCE_TRACE_OPTIONS, mPerformanceTagList);
    }

    public static TraceConfig getBatteryConfig() {
        if (mBatteryTagList == null) {
            mBatteryTagList = new ArraySet<>(BATTERY_TRACE_TAGS);
            updateTagsIfUserBuild(mBatteryTagList);
        }
        return new TraceConfig(BATTERY_TRACE_OPTIONS, mBatteryTagList);
    }

    public static TraceConfig getThermalConfig() {
        if (mThermalTagList == null) {
            mThermalTagList = new ArraySet<>(THERMAL_TRACE_TAGS);
            updateTagsIfUserBuild(mThermalTagList);
        }
        return new TraceConfig(THERMAL_TRACE_OPTIONS, mThermalTagList);
    }

    public static TraceConfig getUiConfig() {
        if (mUiTagList == null) {
            mUiTagList = new ArraySet<>(UI_TRACE_TAGS);
            updateTagsIfUserBuild(mUiTagList);
        }
        return new TraceConfig(UI_TRACE_OPTIONS, mUiTagList);
    }

    private static void updateTagsIfUserBuild(Collection<String> tags) {
        if (Build.TYPE.equals("user")) {
            tags.removeAll(USER_BUILD_DISABLED_TRACE_TAGS);
        }
    }

    public static class TraceOptions {
        public final int bufferSizeKb;
        public final boolean winscope;
        public final boolean apps;
        public final boolean longTrace;
        public final boolean attachToBugreport;
        public final int maxLongTraceSizeMb;
        public final int maxLongTraceDurationMinutes;

        public TraceOptions(int bufferSizeKb, boolean winscope, boolean apps, boolean longTrace,
                boolean attachToBugreport, int maxLongTraceSizeMb,
                int maxLongTraceDurationMinutes) {
            this.bufferSizeKb = bufferSizeKb;
            this.winscope = winscope;
            this.apps = apps;
            this.longTrace = longTrace;
            this.attachToBugreport = attachToBugreport;
            this.maxLongTraceSizeMb = maxLongTraceSizeMb;
            this.maxLongTraceDurationMinutes = maxLongTraceDurationMinutes;
        }
    }

    // Keep in sync with default sizes and durations in buffer_sizes.xml.
    private static final int DEFAULT_BUFFER_SIZE_KB = 16384;
    private static final int DEFAULT_MAX_LONG_TRACE_SIZE_MB = 10240;
    private static final int DEFAULT_MAX_LONG_TRACE_DURATION_MINUTES = 30;

    private static final TraceOptions DEFAULT_TRACE_OPTIONS =
            new TraceOptions(DEFAULT_BUFFER_SIZE_KB,
                    /* winscope */ false,
                    /* apps */ true,
                    /* longTrace */ false,
                    /* attachToBugreport */ true,
                    DEFAULT_MAX_LONG_TRACE_SIZE_MB,
                    DEFAULT_MAX_LONG_TRACE_DURATION_MINUTES);

    private static final TraceOptions PERFORMANCE_TRACE_OPTIONS =
            new TraceOptions(DEFAULT_BUFFER_SIZE_KB,
                    /* winscope */ false,
                    /* apps */ true,
                    /* longTrace */ false,
                    /* attachToBugreport */ true,
                    DEFAULT_MAX_LONG_TRACE_SIZE_MB,
                    DEFAULT_MAX_LONG_TRACE_DURATION_MINUTES);

    private static final TraceOptions BATTERY_TRACE_OPTIONS =
            new TraceOptions(DEFAULT_BUFFER_SIZE_KB,
                    /* winscope */ false,
                    /* apps */ false,
                    /* longTrace */ true,
                    /* attachToBugreport */ true,
                    DEFAULT_MAX_LONG_TRACE_SIZE_MB,
                    DEFAULT_MAX_LONG_TRACE_DURATION_MINUTES);

    private static final TraceOptions THERMAL_TRACE_OPTIONS =
            new TraceOptions(DEFAULT_BUFFER_SIZE_KB,
                    /* winscope */ false,
                    /* apps */ true,
                    /* longTrace */ true,
                    /* attachToBugreport */ true,
                    DEFAULT_MAX_LONG_TRACE_SIZE_MB,
                    DEFAULT_MAX_LONG_TRACE_DURATION_MINUTES);

    private static final TraceOptions UI_TRACE_OPTIONS =
            new TraceOptions(DEFAULT_BUFFER_SIZE_KB,
                    /* winscope */ true,
                    /* apps */ true,
                    /* longTrace */ true,
                    /* attachToBugreport */ true,
                    DEFAULT_MAX_LONG_TRACE_SIZE_MB,
                    DEFAULT_MAX_LONG_TRACE_DURATION_MINUTES);
}
