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
 * limitations under the License.
 */

package com.android.traceur;

import android.os.Parcel;
import android.os.Parcelable;

import java.util.Set;

public class TraceConfig implements Parcelable {

    private final int bufferSizeKb;
    private final boolean winscope;
    private final boolean apps;
    private final boolean longTrace;
    private final boolean attachToBugreport;
    private final int maxLongTraceSizeMb;
    private final int maxLongTraceDurationMinutes;
    private final Set<String> tags;

    public TraceConfig(int bufferSizeKb, boolean winscope, boolean apps, boolean longTrace,
            boolean attachToBugreport, int maxLongTraceSizeMb, int maxLongTraceDurationMinutes,
            Set<String> tags) {
        this.bufferSizeKb = bufferSizeKb;
        this.winscope = winscope;
        this.apps = apps;
        this.longTrace = longTrace;
        this.attachToBugreport = attachToBugreport;
        this.maxLongTraceSizeMb = maxLongTraceSizeMb;
        this.maxLongTraceDurationMinutes = maxLongTraceDurationMinutes;
        this.tags = tags;
    }

    public TraceConfig(PresetTraceConfigs.TraceOptions options, Set<String> tags) {
        this(
            options.bufferSizeKb,
            options.winscope,
            options.apps,
            options.longTrace,
            options.attachToBugreport,
            options.maxLongTraceSizeMb,
            options.maxLongTraceDurationMinutes,
            tags
        );
    }

    public PresetTraceConfigs.TraceOptions getOptions() {
        return new PresetTraceConfigs.TraceOptions(
            bufferSizeKb,
            winscope,
            apps,
            longTrace,
            attachToBugreport,
            maxLongTraceSizeMb,
            maxLongTraceDurationMinutes
        );
    }

    public int getBufferSizeKb() {
        return bufferSizeKb;
    }

    public boolean getWinscope() {
        return winscope;
    }

    public boolean getApps() {
        return apps;
    }

    public boolean getLongTrace() {
        return longTrace;
    }

    public boolean getAttachToBugreport() {
        return attachToBugreport;
    }

    public int getMaxLongTraceSizeMb() {
        return maxLongTraceSizeMb;
    }

    public int getMaxLongTraceDurationMinutes() {
        return maxLongTraceDurationMinutes;
    }

    public Set<String> getTags() {
        return tags;
    }

    @Override
    public int describeContents() {
        return 0;
    }

    @Override
    public void writeToParcel(Parcel parcel, int i) {
        parcel.writeInt(bufferSizeKb);
        parcel.writeBoolean(winscope);
        parcel.writeBoolean(apps);
        parcel.writeBoolean(longTrace);
        parcel.writeBoolean(attachToBugreport);
        parcel.writeInt(maxLongTraceSizeMb);
        parcel.writeInt(maxLongTraceDurationMinutes);
        parcel.writeStringArray(tags.toArray(String[]::new));
    }

    public static final Parcelable.Creator<TraceConfig> CREATOR = new Creator<>() {
        @Override
        public TraceConfig createFromParcel(Parcel parcel) {
            return new TraceConfig(
                parcel.readInt(),
                parcel.readBoolean(),
                parcel.readBoolean(),
                parcel.readBoolean(),
                parcel.readBoolean(),
                parcel.readInt(),
                parcel.readInt(),
                Set.of(parcel.readStringArray())
            );
        }

        @Override
        public TraceConfig[] newArray(int i) {
            return new TraceConfig[i];
        }
    };

    public static class Builder {
        public int bufferSizeKb;
        public boolean winscope;
        public boolean apps;
        public boolean longTrace;
        public boolean attachToBugreport;
        public int maxLongTraceSizeMb;
        public int maxLongTraceDurationMinutes;
        public Set<String> tags;

        public Builder(TraceConfig traceConfig) {
            this(
                traceConfig.getBufferSizeKb(),
                traceConfig.getWinscope(),
                traceConfig.getApps(),
                traceConfig.getLongTrace(),
                traceConfig.getAttachToBugreport(),
                traceConfig.getMaxLongTraceSizeMb(),
                traceConfig.getMaxLongTraceDurationMinutes(),
                traceConfig.getTags()
            );
        }

        private Builder(int bufferSizeKb, boolean winscope, boolean apps, boolean longTrace,
                boolean attachToBugreport, int maxLongTraceSizeMb, int maxLongTraceDurationMinutes,
                Set<String> tags) {
            this.bufferSizeKb = bufferSizeKb;
            this.winscope = winscope;
            this.apps = apps;
            this.longTrace = longTrace;
            this.attachToBugreport = attachToBugreport;
            this.maxLongTraceSizeMb = maxLongTraceSizeMb;
            this.maxLongTraceDurationMinutes = maxLongTraceDurationMinutes;
            this.tags = tags;
        }

        public TraceConfig build() {
            return new TraceConfig(bufferSizeKb, winscope, apps, longTrace, attachToBugreport,
                    maxLongTraceSizeMb, maxLongTraceDurationMinutes, tags);
        }
    }
}
