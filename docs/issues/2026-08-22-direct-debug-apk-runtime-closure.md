# Task 050 — Direct Debug APK runtime closure

## Status

Planned after the user explicitly removed Task 049's over-conservative restrictions.

## User-authorized operating model

- `app/src/main/AndroidManifest.xml` may be changed.
- `:app` namespace may be changed.
- A dedicated disposable emulator may be rooted, remounted, have its system image/APK replaced, damaged, deleted, and recreated.
- Shared emulator system-image files may be modified if that is the shortest route; reinstalling the image/AVD is an acceptable recovery.
- The original emulator SystemUI APK must first be pulled to a local backup.
- The required loop is: build Debug → push it to the real SystemUI path → reboot → capture the real failure → fix that failure → repeat until usable.

## Known root cause before Task 050

The AOSP manifest contains relative component names. AGP currently expands package-dependent names against `:app` namespace `com.android.systemui.app`, while the real classes are under `com.android.systemui`. The packaged Debug manifest therefore has 75/91 entry classes absent from DEX. Task 048 observed the corresponding runtime `ClassNotFoundException` in the shipped APK.

Task 049 proved the unchanged Debug APK is 163,546,744 bytes, while adb-remount overlay scratch was too small. Its extra bind/symlink experiments were rolled back and are not design constraints for Task 050.

## Direct plan

1. Use the existing static manifest-to-DEX failure as the pre-fix reproduction.
2. Test the smallest configuration fix first: set `:app` namespace to `com.android.systemui`.
3. Fresh-build Debug and run packaged-manifest-to-DEX closure.
4. If namespace unification causes an actual R/build conflict, revert only that experiment and directly convert the manifest entry attributes to correct `com.android.systemui.*` FQCNs.
5. On the dedicated emulator, pull and hash the original SystemUI APK as a local backup.
6. Use root/remount/direct image modification as needed to place the complete Debug APK at the path returned by `pm path com.android.systemui`; verify the device hash.
7. Reboot fully, capture the first real crash, and apply exactly one evidenced fix at a time.
8. Finish only after stable SystemUI PID and status bar, Quick Settings, lock/wake/unlock interaction.

## Results

Not run yet.
