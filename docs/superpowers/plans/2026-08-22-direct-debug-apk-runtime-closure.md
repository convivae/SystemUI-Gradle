# Direct Debug APK runtime closure plan

> Task 050. The user explicitly authorizes manifest/namespace changes and destructive mutation/recreation of the dedicated emulator.

## Phase 1 — Simplest manifest fix

- [ ] Record the current packaged-manifest-to-DEX failure.
- [ ] Change only `:app` namespace from `com.android.systemui.app` to `com.android.systemui`.
- [ ] Fresh `:app:assembleDebug` with one Gradle owner and at most four workers.
- [ ] Verify packaged manifest entries all exist in Debug DEX.
- [ ] If and only if the build proves an R collision, revert the namespace experiment and make the manifest component names fully qualified instead.

## Phase 2 — Direct emulator deployment

- [ ] Prove the target is the dedicated emulator, not a physical device.
- [ ] Discover the SystemUI APK path using `pm path com.android.systemui`.
- [ ] Pull the original APK to local storage; record size and SHA-256.
- [ ] `adb root`, disable verity/remount as needed.
- [ ] Push the complete Debug APK. If overlay space is insufficient, modify/expand the disposable AVD/system image directly rather than inventing bind/symlink workarounds.
- [ ] Verify the on-device APK SHA-256 equals the host Debug artifact.
- [ ] Full reboot and boot-completion check.

## Phase 3 — Real crash loop

- [ ] Capture the first fatal exception and PID behavior from the rebooted Debug APK.
- [ ] Write one root-cause hypothesis.
- [ ] Apply one minimal fix, rebuild, push, and reboot.
- [ ] Repeat from new evidence; do not batch unrelated fixes.

## Phase 4 — Runtime acceptance

- [ ] SystemUI PID stable for at least 60 seconds.
- [ ] Status bar visible and responsive.
- [ ] Quick Settings opens and responds.
- [ ] Lock, wake, and unlock complete without fatal/ANR/watchdog/crash loop.
- [ ] Save logcat, dumpsys, screenshots/UI evidence, APK hash, and build output.
- [ ] Update current-state documentation and commit in English; Worker does not push.

Release tasks remain outside Task 050.
