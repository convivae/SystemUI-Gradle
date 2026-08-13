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
