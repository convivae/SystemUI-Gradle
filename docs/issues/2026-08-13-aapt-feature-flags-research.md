# 2026-08-13 — AAPT feature-flags research (Task 007)

> Process note (rule D). Companion options doc:
> `docs/architecture/2026-08-13-aapt-feature-flags-options.md`.
> Brief: `docs/orchestration/tasks/007-aapt-feature-flags-research.md`.
> Branch: `task-007`. Authority: self-commit (never push), docs only.

## Background

After the 2026-08-13 fix wave cleared the `:SystemUI-core` NeverCompile javac
group, `:app:assembleDebug` advanced to `:app:processDebugResources` and hit a
new, previously-latent blocker: AAPT2 rejects the
`android:featureFlag="com.android.wm.shell.enable_retrievable_bubbles"`
attribute carried by the WindowManager-Shell AAR manifest. This was never
scheduled at Task 7 (javac failed first), so it is a fresh surfacing, not a
regression.

## What I did (research only — no build/manifest/AAR/SDK edits)

1. **Reproduced** with `./gradlew :app:processDebugResources --console=plain`
   (`/tmp/task007.log`). Confirmed the **complete** error set: exactly two
   errors, one flag (`com.android.wm.shell.enable_retrievable_bubbles`), one
   manifest (transformed `WindowManager-Shell-1.0.0/AndroidManifest.xml`), two
   `<activity>` elements.
2. **Inventoried** `android:featureFlag` across every packaged AAR
   (`libs/aars/*.aar`, `libs/maven/**/*.aar`) and every module/app manifest.
   Result: the flag appears **only** in `libs/aars/WindowManager-Shell.aar`
   (lines 39, 53) and its Maven twin. No module/app manifest uses the attribute.
3. **Established the mechanism**:
   - aapt2 `--feature-flags` is a link-time CLI option (`aapt2 link --help`;
     `cmd/Link.h:337`).
   - The error is emitted by `link/FeatureFlagsFilter.cpp:86-90`; its option
     `fail_on_unrecognized_flags` **defaults to true**
     (`link/FeatureFlagsFilter.h:36`), so any `android:featureFlag` errors when
     the flag is absent from the supplied set.
   - Soong passes `--feature-flags @<aconfig-file>` (`build/soong/java/aapt2.go:107,284`).
   - **AGP 9.3.1 has zero support** for `--feature-flags` — no class in
     `gradle-9.3.1.jar`/`builder-9.3.1.jar` mentions it; AGP links with an empty
     flag set, so the default `fail_on_unrecognized_flags=true` turns every
     `android:featureFlag` into a hard error. This is a general AGP gap, latent
     only because most manifests don't use the attribute.
   - Feature flags are **not** an SDK-platform property: no flag/aconfig/`.pb`
     files in stock `android-35/36/37` or custom `android-SysUISdk`.
4. **Checked the reference project**: CarSystemUIGradle packages a
   WindowManager-Shell AAR whose manifest is **stripped** of `<application>`
   and `android:featureFlag` (verified by `diff` of the two AAR manifests). It
   never passes `--feature-flags`; it avoids the error by not carrying the
   featureFlag elements. Notably, the current Soong `manifest_fixer`
   intermediate for WindowManager-Shell **retains** `android:featureFlag`
   (lines 32, 39), so CarSystemUIGradle's stripped manifest came from some
   other/earlier packaging path — not reproducible from current Soong
   intermediates.

## Findings summary (full detail in the options doc)

- **Root cause**: `tools/package_aosp_aar.py:89` copies the raw AOSP source
  manifest (which carries two `android:featureFlag` activities); AGP 9.3.1
  never supplies `--feature-flags`; aapt2's `fail_on_unrecognized_flags=true`
  default rejects the unknown flag at `:app:processDebugResources`.
- **Option (a) "patch SysUISdk"** is a **category error** — feature flags are
  not an SDK-platform artifact (no flag files in any platform dir; AGP doesn't
  read them from the SDK). The §2.4 custom-SDK precedent does not extend here.
- **Option (b) `androidResources.additionalParameters`** is **viable and
  recommended** — AGP's public DSL appends args to `aapt2 link`
  (`AaptV2CommandBuilder.makeLinkCommand` consumes `getAdditionalParameters`).
  Passing `--feature-flags com.android.wm.shell.enable_retrievable_bubbles=true`
  declares the flag (satisfies recognition) and, because minSdk 35 > 34, the
  filter keeps the activities (rule C preserved). No source/res/manifest/AAR/SDK
  change, no user approval needed.
- **Option (c) CONV-marked manifest strip** is viable but **strictly worse**
  (drops AOSP manifest elements → rule C regression; needs user approval per
  rule R/ADR 0004). (c2) "use a Soong intermediate lacking featureFlag" is
  infeasible — `manifest_fixer` retains it.

## Recommendation

Option (b). The implementer adds to `app/build.gradle.kts`:

```kotlin
android {
    androidResources {
        additionalParameters(
            "--feature-flags",
            "com.android.wm.shell.enable_retrievable_bubbles=true"
        )
    }
}
```

## Error-count impact

None measured (research only; no build file changed). This blocker is expected
to clear once (b) is applied, unblocking `:app:processDebugResources` and
exposing the next layer (the `:SystemUI-core` NeverCompile javac group, 20
errors, tracked separately in `docs/architecture/2026-08-13-nevercompile-classpath-options.md`).

## Build runs

- `./gradlew :app:processDebugResources --console=plain` → `BUILD FAILED`
  (exit 1) at `:app:processDebugResources` with the two feature-flag errors
  above. This is the reproduction run only; no project files were modified by
  this task.

## Out of scope (reported, not actioned)

- Applying option (b) — that is a build-file change, forbidden by this brief.
  Handed off to the architect/user.
- The NeverCompile javac group (separate task/issue).
- Whether `additionalParameters` should be hoisted into a convention plugin if
  more modules later need it — defer until observed.

---

## 2026-08-13 update — Option (b) applied (Task 009)

> Follow-up implementation note (rule D). Brief:
> `docs/orchestration/tasks/009-feature-flags-additional-parameters.md`.
> Branch: `task-009`. Authority: redline-gated; the `app/build.gradle.kts`
> AAPT-config edit was pre-approved by the user on 2026-08-13.

### Applied diff (`app/build.gradle.kts`, inside the existing `android { }` block)

```kotlin
    // AOSP bp: use_resource_processor: true → automatic with AGP aapt2
    // WM-Shell AAR manifest uses android:featureFlag (AOSP original); supply the
    // flag to aapt2 link. See docs/architecture/2026-08-13-aapt-feature-flags-options.md
    androidResources {
        additionalParameters(
            "--feature-flags",
            "com.android.wm.shell.enable_retrievable_bubbles=true"
        )
    }
```

No other files touched (Allowed Paths respected: only `app/build.gradle.kts`
for code; this doc for the record).

### Acceptance run (Step 3)

```
$ ./gradlew :app:processDebugResources --console=plain
BUILD FAILED in 10s
$ grep -c 'feature_flags\|enable_retrievable_bubbles' /tmp/task009.log   # || echo fallback
0
0 (featureFlag errors gone)
```

**Feature-flag errors: 2 → 0.** Option (b) is confirmed working — the
`com.android.wm.shell.enable_retrievable_bubbles` flag is now recognized by
aapt2 and the `fail_on_unrecognized_flags` default no longer trips. The two
WM-Shell `<activity>` elements are kept (minSdk 35 > 34 ⇒
`remove_disabled_elements=false`), preserving AOSP manifest fidelity (rule C).

However, `:app:processDebugResources` still BUILD FAILED — on a **different,
newly-exposed layer**, not the feature-flag issue.

### Newly-surfaced layer: `androidprv:` private framework resources not found

Cross-check against the prior research reproduction (`/tmp/task007.log`) shows
**0** matches for `androidprv` / `not found.` there. Conclusion: the
feature-flag error previously **aborted AAPT2 link inside the
FeatureFlagsFilter** (`Link.cpp:2052-2063`, run on the merged manifest)
**before the resource-resolution phase**. Clearing it lets aapt2 proceed to
resource linking, which now surfaces the next latent gap.

Distinct missing resources now emitted by `:app:processDebugResources`
(`com.android.systemui.app-mergeDebugResources-85:/values*/values*.xml`):

- `androidprv:attr/materialColorPrimary` (×4)
- `androidprv:attr/materialColorOnSurface` (×4)
- `androidprv:attr/materialColorOnPrimaryContainer`
- `androidprv:attr/materialColorSecondary`
- `androidprv:attr/materialColorSurfaceBright`
- `androidprv:attr/materialColorSurfaceContainerHighest`
- `androidprv:attr/textColorOnAccent`
- `androidprv:color/system_under_surface_light`
- `androidprv:color/system_under_surface_dark`
- `androidprv:style/AlertDialog.DeviceDefault`
- `androidprv:style/DeviceDefault.ButtonBar.AlertDialog`
- `android:dimen/notification_content_margin_end`

Plus ~8 `warn: removing resource com.android.systemui:string/... without
required default value` (car/tv locale-variant strings; warnings, not the
cause of failure).

This is the AGENTS.md §2.4 item-2 problem class ("framework-res.apk adds
private resource IDs"): the `androidprv:` prefix denotes `@*android:` private
framework resources, and the SysUISdk `android.jar` resource set does not yet
carry them. The material-color attrs and `system_under_surface_*` colors are
platform Material You / system-theme private resources.

### assembleDebug diagnostics (Step 4)

```
$ ./gradlew :app:assembleDebug --console=plain
> Task :app:processDebugResources FAILED
* What went wrong:
Execution failed for task ':app:processDebugResources'.
  > Android resource linking failed
BUILD FAILED in 6s
```

`:app:assembleDebug` fails at the same `:app:processDebugResources` task;
APK **not produced**.

### Out of scope — reported, not actioned

The `androidprv:` private-resource layer is **out of scope** for Task 009
(brief Allowed Paths = `app/build.gradle.kts` + docs only; Forbidden =
SDK changes). It is a SysUISdk resource-patching task (AGENTS.md §2.4 item 2 /
`framework-res.apk`) for the architect/user to schedule. Per the brief's
Step 4, no fix was attempted.

The Option (b) change itself is correct and complete and is committed on
`task-009` (never pushed): it cleared its specific blocker and advanced the
build one layer deeper, exactly as forward progress intends (rule I).
