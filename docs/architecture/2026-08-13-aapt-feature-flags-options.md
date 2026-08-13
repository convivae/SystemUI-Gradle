# AAPT `android:featureFlag` / `--feature_flags` — fix options (Task 007)

> Research-only brief (docs only — no build/manifest/AAR/SDK changes).
> Worker: branch `task-007`. Date: 2026-08-13.
> Companion process note: `docs/issues/2026-08-13-aapt-feature-flags-research.md`.

## 1. Problem statement

`:app:assembleDebug` is blocked at `:app:processDebugResources` (AAPT2 link)
with two identical errors, both about the same feature flag in the merged
WindowManager-Shell manifest:

```
ERROR: .../transforms/.../transformed/WindowManager-Shell-1.0.0/AndroidManifest.xml:37:9-49:20:
  AAPT: error: element 'activity' has flag 'com.android.wm.shell.enable_retrievable_bubbles'
  not found in flags from --feature_flags parameter.
ERROR: .../transforms/.../transformed/WindowManager-Shell-1.0.0/AndroidManifest.xml:51:9-61:20:
  AAPT: error: element 'activity' has flag 'com.android.wm.shell.enable_retrievable_bubbles'
  not found in flags from --feature_flags parameter.
```

The flag originates from the **upstream AOSP** WindowManager-Shell manifest
(`frameworks/base/libs/WindowManager/Shell/AndroidManifest.xml:39,53`), packaged
faithfully into `libs/aars/WindowManager-Shell.aar` by `tools/package_aosp_aar.py`
(line 89 copies that source manifest verbatim). The blocker was latent at the
2026-08-12 Task 7 checkpoint (javac failed first; this task never ran) and
surfaced after the 2026-08-13 fix wave. Reproduction log: `/tmp/waveC-app.log`.

## 2. Full flag & manifest inventory (steps 1–2)

### 2.1 Reproduction (step 1)

Command (run by worker):

```bash
./gradlew :app:processDebugResources --console=plain 2>&1 | tee /tmp/task007.log >/dev/null
```

Result: `BUILD FAILED`, exit 1. The **complete** set of feature-flag errors
(grep `aapt: error|feature_flag|featureFlag|not found in flags`) is exactly the
two lines above — one flag, one manifest, two `<activity>` elements. No other
missing flags and no other failing manifests.

### 2.2 Flag inventory across the whole dependency graph (step 2)

Surveyed every packaged AAR (`libs/aars/*.aar`, `libs/maven/**/*.aar`) plus all
module manifests (`SystemUI-*/AndroidManifest.xml`) and
`app/src/main/AndroidManifest.xml` for `android:featureFlag`:

| Source | `android:featureFlag` present? | Flag(s) |
|--------|-------------------------------|---------|
| `libs/aars/WindowManager-Shell.aar` | **yes** (lines 39, 53) | `com.android.wm.shell.enable_retrievable_bubbles` (×2) |
| `libs/maven/.../WindowManager-Shell/1.0.0/WindowManager-Shell-1.0.0.aar` | **yes** (lines 39, 53) | same (Maven twin of the above) |
| `libs/aars/WindowManager-Shell-shared.aar` | no | — |
| all other `libs/aars/*.aar` | no | — |
| all `libs/maven/**/*.aar` | no | — |
| `SystemUI-*/AndroidManifest.xml` (every module) | no | — |
| `app/src/main/AndroidManifest.xml` | no | — |

**Conclusion**: the entire build graph needs exactly **one** flag recognized —
`com.android.wm.shell.enable_retrievable_bubbles` — carried solely by the
WindowManager-Shell AAR manifest. No module/app manifest introduces any other.

### 2.3 The flag's aconfig declaration

```text
# frameworks/base/libs/WindowManager/Shell/aconfig/multitasking.aconfig:77
package: "com.android.wm.shell"
container: "system"
flag {
    name: "enable_retrievable_bubbles"
    namespace: "multitasking"
    description: "Allow opening bubbles overflow UI without bubbles being visible"
    bug: "340337839"
}
```

Fully-qualified flag name (as used in the manifest attribute) =
`com.android.wm.shell.enable_retrievable_bubbles` (package `.` flag name). No
explicit runtime default is set in the aconfig declaration.

## 3. Mechanism: where does `--feature_flags` come from? (step 3)

### 3.1 AAPT2 CLI surface

`aapt2 link --help` (build-tools 37.0.0):

```
--feature-flags arg   Specify the values of feature flags. The pairs in the argument
                      are separated by ',' the name is separated from the value by '='.
                      The name can have a suffix of ':ro' to indicate it is read only.
                      Example: "flag1=true,flag2:ro=false,flag3=" (flag3 has no given value).
```

Registered in AOSP aapt2 source as `AddOptionalFlagList("--feature-flags", ...,
&feature_flags_args_)` at `frameworks/base/tools/aapt2/cmd/Link.h:337-342`. The
`@filepath` response-file form is also accepted (each arg may be `@path` to a
file listing flags — `cmd/Compile.cpp:908-913`).

### 3.2 Why the error fires even though AGP passes nothing

The filter that emits *"not found in flags from --feature_flags parameter"* is
`frameworks/base/tools/aapt2/link/FeatureFlagsFilter.cpp:86-90`. Its option
defaults (header `link/FeatureFlagsFilter.h:30-44`):

```cpp
struct FeatureFlagsFilterOptions {
  bool remove_disabled_elements    = true;
  bool fail_on_unrecognized_flags  = true;   // <-- default TRUE
  bool flags_must_have_value       = true;
  bool flags_must_be_readonly      = false;
};
```

`fail_on_unrecognized_flags` defaults to **true**. The filter is applied to the
merged manifest during `aapt2 link` (`cmd/Link.cpp:2052-2063`). With **no**
`--feature-flags` supplied, `feature_flag_values` is empty, so *any* element
carrying `android:featureFlag` hits the `else if (fail_on_unrecognized_flags)`
branch → hard error. AGP's bundled aapt2 (`aapt2-9.3.1-15703166`) exhibits this
behavior; the build-tools 37 `aapt2 link --help` matches the AOSP source.

The manifest-filter invocation relevant to us (`Link.cpp:2052-2063`):

```cpp
FeatureFlagsFilterOptions flags_filter_options;
if (context_->GetMinSdkVersion() > SDK_UPSIDE_DOWN_CAKE) {  // API 34 = U
  // API > U: PackageManager reads flag values at runtime; don't strip, don't require a value
  flags_filter_options.remove_disabled_elements = false;
  flags_filter_options.flags_must_have_value     = false;
}
// fail_on_unrecognized_flags stays at its default (true) in BOTH branches
FeatureFlagsFilter flags_filter(options_.feature_flag_values, flags_filter_options);
```

Our app has **minSdk = 35, targetSdk = 35** (`app/build.gradle.kts:20-21`) →
minSdk > 34 → the `remove_disabled_elements=false` /
`flags_must_have_value=false` branch applies. So for us the filter requires only
**flag recognition** (the flag must appear in `--feature-flags`); it does not
remove the activities and does not require a true/false value. The activities are
kept regardless. (A separate filter at `Link.cpp:676-678` processes per-resource
XML with `flags_must_be_readonly=true`, but no WM-Shell resource XML uses
`android:featureFlag`, so that path is irrelevant here.)

### 3.3 How Soong makes AOSP builds succeed

Soong passes `--feature-flags @<path>` — a response file of flag values derived
from aconfig. `build/soong/java/aapt2.go:107` (compile) and `:284` (link):

```go
for _, featureFlagsPath := range android.SortedUniquePaths(featureFlagsPaths) {
    flags = append(flags, "--feature-flags", "@"+featureFlagsPath.String())
}
```

The `featureFlagsPaths` are aconfig-generated flag-value files threaded through
from `java_aconfig_library` / `java_library` static deps
(`build/soong/java/base.go:587-590, 1272, 2483, 2557`). In a real product
build, every flag referenced by any merged manifest is therefore *recognized* by
aapt2 — which is why AOSP never hits this error.

### 3.4 How AGP 9.3.1 derives `--feature_flags` — it does not

Decisive finding: **AGP 9.3.1 has no support for the `--feature-flags` aapt2
parameter.** Evidence:

```text
# Search every class in AGP's gradle-9.3.1.jar and builder-9.3.1.jar
for c in <all classes>; do unzip -p ... | strings | grep -iE 'feature-flags|featureFlag|feature_flags'; done
# => ZERO matches in any class
```

No AGP DSL property, task input, or gradle property populates `--feature-flags`.
AGP therefore links with an empty `feature_flag_values`, and the
`fail_on_unrecognized_flags=true` default turns any `android:featureFlag` in any
merged manifest into a hard error. (This is a general AGP gap, not specific to
our project — it is latent simply because most app/library manifests do not use
`android:featureFlag`.)

### 3.5 Stock SDK platform vs custom `android-SysUISdk`

A feature flag inventory is **not** an SDK-platform property:

```text
find ~/Android/Sdk/platforms/android-35/ -maxdepth 2 -iname '*flag*'        # (empty)
find ~/Android/Sdk/platforms/android-SysUISdk/ -maxdepth 2 -iname '*flag*'   # (empty)
find ... android-35 android-SysUISdk \( -iname '*.pb' -o -iname '*aconfig*' \)  # (empty)
```

Stock `android-35/36/36.1/37.0` and our custom `android-SysUISdk` contain **no**
feature-flag/aconfig/`.pb` files. Feature flags enter aapt2 exclusively via the
build-system `--feature-flags` CLI argument (Soong) — never via the SDK platform
directory.

## 4. Reference project: CarSystemUIGradle (step 4)

```bash
grep -rniE 'featureFlag|feature_flags' /home/conv/myspace/CarSystemUIGradle \
  --include='*.md' --include='*.kts' --include='*.xml'
```

Every hit is the **Java class** `com.android.systemui.flags.FeatureFlags` /
`android.util.FeatureFlagUtils` — *not* the manifest attribute. CarSystemUIGradle
never passes `--feature-flags`. So how does it avoid this error?

It packages a WindowManager-Shell AAR whose manifest **does not carry** the
featureFlag activities:

```bash
diff <(unzip -p <our>/libs/aars/WindowManager-Shell.aar AndroidManifest.xml) \
     <(unzip -p <CarSystemUIGradle>/libs/maven/.../WindowManager-Shell-1.0.0.aar AndroidManifest.xml)
```

CarSystemUIGradle's packaged manifest (`>` side) contains only four
`<uses-permission>` entries and **no `<application>`, no `<activity>`, no
`android:featureFlag`**. Our manifest (`<` side) carries the full AOSP manifest:
8 permissions + `<application>` with three activities (two of them tagged
`android:featureFlag="com.android.wm.shell.enable_retrievable_bubbles"`).

CarSystemUIGradle's `tools/gen_aar_maven.py:412-423` prefers a Soong
`manifest_fixer` intermediate, falling back to the source manifest:

```python
manifest_sources = [
    base_path / "manifest_fixer" / "AndroidManifest.xml",   # preferred
    source_path / "AndroidManifest.xml",
]
```

**However**, the current Soong `manifest_fixer` intermediate for
WindowManager-Shell **retains** `android:featureFlag`:

```text
# aosp/out/soong/.intermediates/.../WindowManager-Shell/android_common/manifest_fixer/AndroidManifest.xml:32,39
<activity ... android:featureFlag="com.android.wm.shell.enable_retrievable_bubbles" ...>
```

So CarSystemUIGradle's stripped AAR manifest was not produced by the current
`manifest_fixer` step; it was produced by some other/earlier packaging path
(most likely an `aapt2 link --static-lib` step that strips `<application>` for
library AARs, or an older manual extraction). The exact mechanism is not
determinable from `gen_aar_maven.py` alone, but the **outcome** is clear and
verified: the reference project avoids the AAPT error by not carrying the
featureFlag elements into the packaged manifest at all.

## 5. Options

Each option is assessed against the project's mandatory rules
(P no-stubs / S source-first / C complete&exact / F framework-via-SDK /
 R res-provenance / B bp-aligned). **Options (b) is fully compliant without
user approval; (c) requires user approval; (a) is not viable.**

### Option (a) — Patch SysUISdk with feature-flags declarations  ❌ NOT VIABLE

Framed in the brief as "AGENTS.md §2.4 custom-SDK precedent". **Research shows
this is a category error.** The §2.4 precedents are: `framework.jar` adds @hide
*code APIs*; `framework-res.apk` adds *private resource IDs*; `framework.aidl`
adds *AIDL declarations*. Feature flags are **none of these** — they are a
build-time aapt2 CLI input (`--feature-flags`), not an artifact carried by the
SDK platform (`android.jar`).

Evidence (§3.5): no feature-flag/aconfig/`.pb` files exist in stock
`android-35/36/37` or custom `android-SysUISdk`. AGP does not read feature flags
from the platform directory; there is no location in `android-SysUISdk` to
"declare" them that aapt2 would consume. Patching `android.jar` (the §2.4
mechanism) cannot influence the `--feature_flags` aapt2 parameter, which AGP
never passes.

Verdict: do not pursue. The §2.4 custom-SDK precedent does **not** extend to
feature flags.

### Option (b) — Supply `--feature-flags` via AGP's `androidResources.additionalParameters`  ✅ VIABLE — RECOMMENDED

AGP exposes a public DSL that appends arbitrary args to the `aapt2 link`
command:

```text
# public API (gradle-api-9.3.1.jar)
com.android.build.api.dsl.AndroidResources
    List<String> getAdditionalParameters()
    void additionalParameters(String)
    void additionalParameters(String...)
# variant API (per-variant programmatic)
com.android.build.api.variant.AndroidResources
    ListProperty<String> getAaptAdditionalParameters()
```

Internal wiring confirms these reach the **link** command:
`com.android.builder.internal.aapt.v2.AaptV2CommandBuilder.makeLinkCommand(...)`
calls `getAdditionalParameters()` (string present in the link-command builder's
bytecode) and appends them. (The legacy
`com.android.build.gradle.internal.dsl.AaptOptions` — the `android.aaptOptions`
block — exposes the same `additionalParameters(String...)`.)

Proposed change (for the implementer to apply to `app/build.gradle.kts`; this
worker does **not** modify build files):

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

Why this is correct and safe:

- `--feature-flags` is a flag-list option; passing it once with the
  `name=value` pair populates `feature_flag_values` so the flag is
  **recognized** → `fail_on_unrecognized_flags` no longer trips.
- Because minSdk 35 > 34, the manifest filter runs with
  `remove_disabled_elements=false` → the two activities are **kept** (not
  stripped), preserving AOSP manifest fidelity (rule C: nothing missing).
  Value `=true` (rather than empty) is the explicit, minSdk-independent form.
- Only the `:app` module's `processDebugResources` (the app-link step) errors
  today, so scoping to `app/build.gradle.kts` is sufficient. If a library
  module's manifest merge ever errors similarly later, apply the same block to
  that module (or hoist into a convention plugin).

Provenance / rule compliance: modifies **no** AOSP source, **no** res, **no**
manifest, **no** AAR, **no** SDK. It is a pure build-configuration knob that
supplies a build-time input AGP omits — fully compliant with P/S/C/F/R/B. No user
approval required under rule R (it does not touch `res/`) or ADR 0004 (no source
mutation). **Recommended.**

### Option (c) — CONV-marked manifest adjustment in the packaging pipeline  ⚠️ VIABLE BUT REQUIRES USER APPROVAL (worse than b)

Two sub-variants:

- **(c1) Strip the featureFlag `<activity>` elements** from the packaged
  WindowManager-Shell AAR manifest inside `tools/package_aosp_aar.py`, guarded
  by ADR 0004 `CONV_DEL`/`BEGIN`–`END` markup. This is the rule-R/ADR-0004 path:
  provenance-compliant (the original bytes are retained, marked, traceable) but
  it **drops AOSP manifest elements** — a rule-C regression ("nothing missing")
  — and needs explicit user authorization per ADR 0004 + rule R.
- **(c2) Switch the packaging tool to consume a Soong intermediate that lacks
  featureFlag.** **Infeasible:** the Soong `manifest_fixer` intermediate for
  WindowManager-Shell *retains* `android:featureFlag` (§4 evidence). No
  existing AOSP-produced manifest for this target omits it, so there is no
  provenance-clean artifact to switch to. (CarSystemUIGradle's stripped
  manifest exists, but its production mechanism is undocumented and not
  reproducible from current Soong intermediates — see §4.)

CarSystemUIGradle effectively does (c1)-without-marks (its packaged manifest
simply lacks the activities). Adopting that here would replicate a rule-C
regression and still require user approval.

Verdict: viable only if the user explicitly prefers dropping the bubble
shortcut activities over declaring the flag. Strictly worse than (b) on every
axis (fidelity, provenance, approval cost). Not recommended.

## 6. Recommendation

**Adopt option (b)**: add the `androidResources.additionalParameters(...)`
block to `app/build.gradle.kts` supplying
`--feature-flags com.android.wm.shell.enable_retrievable_bubbles=true`.

Rationale summary:

1. It is the **AGP-native** mechanism for the AGP-native gap (AGP never passes
   `--feature-flags`; we supply it directly).
2. It touches **no** AOSP source/res/manifest/AAR/SDK → fully rule-compliant,
   no user approval, no CONV markup, no ADR.
3. It **preserves** the AOSP manifest 1:1 (rule C) — activities are kept, not
   stripped — because minSdk 35 > 34 disables element removal.
4. It is a **one-block, one-module** change, trivially reversible, with no
   structural side effects (rule I: no regression).

Fallback only if (b) is later found not to reach the merged-manifest filter for
some AGP-internal reason: escalate (rule H) rather than silently switching to
(c). The research here gives high confidence (b) works: `makeLinkCommand`
consumes `additionalParameters`, and `processDebugResources` runs exactly that
link command.

## 7. Command evidence index (for the architect)

| Finding | Command | Result |
|---------|---------|--------|
| Error set | `./gradlew :app:processDebugResources --console=plain` (tee `/tmp/task007.log`) | 2 errors, 1 flag, 1 manifest |
| Flag inventory (AARs) | `for a in libs/aars/*.aar; do unzip -p "$a" AndroidManifest.xml \| grep -i featureFlag; done` | only WindowManager-Shell.aar (×2) |
| Flag inventory (modules/app) | `grep -rniE featureFlag SystemUI-*/AndroidManifest.xml app/src/main/AndroidManifest.xml` | (empty) |
| aapt2 CLI | `aapt2 link --help \| grep -i feature` | `--feature-flags arg` documented |
| aapt2 source: error site | `grep -n fail_on_unrecognized FeatureFlagsFilter.h` | `bool fail_on_unrecognized_flags = true;` (default) |
| aapt2 source: filter run | `sed -n 2052,2063p cmd/Link.cpp` | runs on merged manifest; minSdk>U branch |
| Soong passes flags | `grep -n feature-flags build/soong/java/aapt2.go` | `:107` and `:284` `--feature-flags @<path>` |
| AGP has no support | search gradle-9.3.1.jar + builder-9.3.1.jar classes for `feature` | zero matches |
| AGP `additionalParameters` DSL | javap `com.android.build.api.dsl.AndroidResources` | `additionalParameters(String...)` present |
| AGP link consumes it | strings `AaptV2CommandBuilder.class` | `getAdditionalParameters` in `makeLinkCommand` lambdas |
| SDK platform has no flag files | `find .../android-35 .../android-SysUISdk -iname '*flag*'` | (empty) |
| aconfig source | `cat .../WindowManager/Shell/aconfig/multitasking.aconfig` | flag declared, package `com.android.wm.shell` |
| Reference project manifest | `diff <(our aar manifest) <(CarSystemUI aar manifest)` | CarSystemUI stripped: no `<application>`/featureFlag |
| Soong manifest_fixer retains flag | `grep featureFlag .../manifest_fixer/AndroidManifest.xml` | present (lines 32, 39) |
| Our packaging copies raw source | `grep manifest tools/package_aosp_aar.py` | line 89 = AOSP source manifest |
