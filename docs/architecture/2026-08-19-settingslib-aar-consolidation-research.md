# SettingsLib AAR Count Consolidation Research (Task 016)

Date: 2026-08-19
Branch: `task-016-research`
Status: read-only research; no code/build/resource changes
Predecessor: Task 014 (`2026-08-19-settingslib-resource-closure-research.md`), ADR 0005

## Context

Task 014 established the full closure of SettingsLib: **33 res-owning Soong targets,
1512 resource files, 599 unique relative paths, 101 duplicate-path groups**, and
recommended Plan C (30 new per-target AARs). The user accepted Plan B (POM transitive
dependencies, ADR 0005) but considers **30 new AARs too many** and asked for compliant
options below 30 before deciding the implementation granularity.

This document answers Q1–Q5 from the issue doc
(`docs/issues/2026-08-19-settingslib-aar-consolidation-research.md`) with quantitative
evidence and one recommendation. All analysis scripts are in `/tmp` (never committed);
key JSON artifacts are listed in the Appendix so the architect can re-verify.

## Executive summary

| Question | Answer |
|---|---|
| Q1 minimum conflict-free grouping | **k = 12 groups**, proven optimal (12-clique witness). The relaxed "disjoint-entry same-path merge" variant **does not reduce k below 12** (clique members' `values/styles.xml` entries overlap; entry-level merging would rewrite file bytes → Rule R violation). |
| Q2 namespace-collapse breakage | SystemUI directly uses **74 settingslib classes** (69 from the main target). Under namespace-collapsed merging, **39 classes would have dead R references ("dormant time bombs") — but 0 of them are reachable from SystemUI today**. |
| Q3 reachability minimal set | Code-level need: **6 targets**. Link-closure (AAPT2 link sees full res trees of shipped AARs) grows it to **10 targets = 7 new AARs** beyond the existing main/Color/SettingsTheme (760 of 1512 files). |
| Q4 AGP R mechanism | Compile-time R classes for AAR deps are generated from **R.txt + manifest package** (`AarToClassTransform.generateRClassJarFromRTxt`, bytecode-verified in gradle-9.3.1.jar). At app link, `RGeneration` + `SymbolTable.withValuesFrom` **filters symbols absent from the merged table** → an R.txt-only AAR compiles but its symbols are dropped at link → runtime `NoSuchFieldError` (medium confidence; arg wiring not fully traced). |
| Q5 recommendation | **B2: reachability-driven shipping — 7 new per-target AARs (10 total)**, wired via ADR 0005 POM transitive dependencies. Runner-up: B1′ (12 merged AARs) if full class shipping is preferred. |

---

## Q1 — Minimum conflict-free grouping

### Model

Vertices: the 33 res-owning SettingsLib targets from Task 014. An edge joins two
targets iff they own the same resource **relative path** (same-path collision — the
conflict criterion for merging res trees into one AAR while keeping every file
byte-exact, un-rewritten, un-dropped). Solving minimum grouping = exact graph coloring.

Task 014's counts were reproduced exactly by `/tmp/t016_closure.py` (33 targets,
1512 files, 599 unique paths, 101 duplicate-path groups), which validates the data
basis before any new computation.

### Result: k = 12, proven optimal

Exact DSATUR branch-and-bound coloring (`/tmp/t016_q1_variant.py`) yields a minimum of
**12 groups**. Optimality is not heuristic: a **12-clique** exists — 12 targets that
pairwise share `values/styles.xml` — so no coloring can use fewer than 12 colors, and
a 12-coloring was found. The bound is tight in both directions.

Duplicate-path group statistics (owner-count distribution):

| owners per group | groups | typical content |
|---|---|---|
| 11 | 85 | locale `values-*/strings.xml` families |
| 12 | 1 | `values/styles.xml` (the clique's shared path) |
| 10 | 2 | locale strings |
| 2 / 3 / 5 / 8 / 9 | 14 | mixed (`attrs.xml`, `styles.xml`, layouts) |

92 of the 101 groups involve the main `SettingsLib` target — the main target is the
hub of the conflict graph, which is why it cannot be merged with almost anything.

A **constrained** coloring was also computed (`/tmp/t016_q1_constrained.json`): keeping
`SettingsLib`, `SettingsLibColor`, `SettingsLibSettingsTheme`,
`SettingsLibAdaptiveIcon` in 4 distinct groups (so their R namespaces survive
independently — see Q2/Q3 for why these four) is feasible with **12 colors**. So the
namespace-aware variant B1′ needs no extra AARs beyond the unconditional minimum.

### Relaxed variant (grey area): still 12

The variant "allow merging same-path values XML when their top-level resource entries
are pairwise disjoint" (entries byte-exact, but the file is synthesized from multiple
sources) was evaluated. **It does not reduce k below 12**: the optimality witness is a
clique over shared `values/styles.xml` files whose entries **overlap** across the
clique members (same style symbols claimed by different targets — e.g. the symbol
table underlying Q3 had to resolve multi-claimant symbols such as
`string/disabled_by_admin` by precedence). Overlapping entries cannot be merged under
the disjoint-entry rule; merging them anyway means rewriting/concatenating file bytes,
which violates Rule R (byte-exact, no synthesis). This variant is doubly grey — it
needs a packager extension **and** a Rule R interpretation ruling from the user — and
it buys nothing: k stays 12. **Rejected.**

---

## Q2 — Runtime evidence for R namespace collapse

Merging several targets into one AAR yields **one manifest package → one R namespace**
(see Q4); classes whose bytecode references other sub-target R namespaces then break.

### What SystemUI actually uses

Full scan of `SystemUI-core/src`, `SystemUI-shared`, `SystemUI-res` (via
`/tmp/t016_q2.py`, with bytecode-level R-reference attribution from AOSP
`turbine-combined` jars — a `ldc // class` comment pollution bug in the javap regex
was found and fixed before trusting results; artifacts `/tmp/t016_rrefs.json`,
`/tmp/t016_crossrefs.json`, `/tmp/t016_q2_*.json`):

- **74 settingslib classes are directly used** by SystemUI source; **69 come from the
  main `SettingsLib` target**, only 4 from sub-targets:
  - `com.android.settingslib.widget.AdaptiveIcon` — R refs to
    `com.android.settingslib.widget.adaptiveicon.R`
    (e.g. `SystemUI-core/src/com/android/systemui/media/controls/ui/binder/MediaControlViewBinder.kt:38`)
  - `com.android.settingslib.widget.LottieColorUtils` — R refs to
    `com.android.settingslib.color.R`
    (`SystemUI-core/src/com/android/systemui/biometrics/ui/binder/PromptIconViewBinder.kt:25`)
  - `DeviceStateRotationLockSettingsManager`, `BrightnessUtils` — no R refs
- **~44 direct references to main `com.android.settingslib.R.*` fields**, e.g.
  `R.drawable.settingslib_switch_bar_bg_on` at
  `SystemUI-core/src/com/android/systemui/qs/tiles/dialog/InternetDialogDelegate.java:300`
  and `.../bluetooth/qsdialog/DeviceItemFactory.kt:28`.
- **One direct foreign-namespace field reference in SystemUI's own code**:
  `com.android.settingslib.color.R.color.settingslib_color_blue400` at
  `SystemUI-core/src/com/android/systemui/biometrics/ui/viewmodel/SideFpsOverlayViewModel.kt:194`
  — the `color` namespace must stay alive regardless of any grouping.
- 19 settingslib classes reference foreign namespaces overall
  (`/tmp/t016_crossrefs.json`); of these, **only `LottieColorUtils` is used by
  SystemUI** — its namespace (`color`) is one of the four B1′ anchors.

### Breakage list under namespace collapse

Under the constrained 12-group B1′ coloring (alive namespaces: main, `color`,
`widget.adaptiveicon`, `widget.theme`):

- **39 classes would carry dead R references** ("would definitely crash **if**
  executed" — none of them is): per-target counts —
  `SettingsLibCollapsingToolbarBaseActivity` 5, main `SettingsLib` 3,
  `SettingsLibAppPreference` 3, `SettingsLibBannerMessagePreference` 2,
  `SettingsLibBarChartPreference` 2, `SettingsLibMainSwitchPreference` 2,
  `SettingsLibSettingsSpinner` 2, and 1 each in 27 further targets
  (`SettingsLibActionButtonsPreference`, `SettingsLibFooterPreference`,
  `SettingsLibLayoutPreference`, `SettingsLibSelectorWithWidgetPreference`,
  `SettingsLibTwoTargetPreference`, `SettingsLibUtils`, …). Full class list:
  reproducible from `/tmp/t016_rrefs.json` + `/tmp/t016_q1_constrained.json`.
- **Reachable from SystemUI today: 0.** The 74 directly-used classes (and the 502
  transitively reachable ones, Q3) all resolve their R refs inside the alive
  namespaces. So a collapsed build would run today — but the 39 classes are
  **runtime-invisible time bombs**: nothing fails at compile or link; a future AOSP
  sync that makes SystemUI use one of them fails only at runtime
  (`NoSuchFieldError`).

Under B2 (10 alive namespaces, Q3): 32 dormant broken classes, **0 reachable** — same
conclusion, slightly fewer.

### Reference project evidence strength

`CarSystemUIGradle` ships **one** SettingsLib AAR (`libs/maven/com/android/systemui/
SettingsLib/1.0.0`, 1326 classes) and it runs. Bytecode inspection
(`/tmp/t016_refaar/`): its `classes.jar` contains **no R classes at all**, and e.g.
`AdaptiveIcon` binds `getstatic com/android/settingslib/widget/R$dimen.…` /
`R$color.…` — i.e. Soong-compiled classes reference R by package of their compile-time
owner, and compile/runtime R classes are supplied externally (Q4 mechanism). This is
**existence proof that collapsed-namespace shipping can run**, but its strength is
limited: the Car SystemUI usage surface is much smaller and different (142 files
import settingslib, dominated by bluetooth/mobile/media/graph/fuelgauge utilities —
many of those classes are absent from our needed set), and it proves nothing about
the 39 dormant classes this project would carry. Treat it as supporting, not
decisive, evidence.

---

## Q3 — Reachability minimal set

### Method

`/tmp/t016_q3.py` builds (a) a settingslib **symbol table** (1672 resource symbols,
owner = target) parsed from all 33 targets' res files; (b) a **class table** (1115
classes, owner target) from AOSP turbine-combined jars; (c) the project's own symbol
set (5256 symbols from `SystemUI-res`, `/tmp/t016_proj_syms.json`); then BFS over
resource references (`@type/name`, `?attr/name`, style `parent`, layout tags) and
class references (imports + reachable-class R refs) starting from SystemUI's res,
manifest and source.

Two refinements matter:

1. **Project-symbol shadowing**: 46 ambiguous symbols (referenced without namespace
   by SystemUI) are also defined in `SystemUI-res` — under AAPT2 same-package
   precedence (Task 013's empirical finding) these resolve to the project's own
   resources, not settingslib. Counting them as settingslib needs would have inflated
   the result from 6 to 8 targets.
2. **Link closure**: AAPT2 link processes the **full res tree of every shipped AAR**,
   not just the reached symbols. Every `@ref` inside the needed targets' own files
   must also resolve. Iterating this to fixpoint pulls in 4 more targets
   (`SettingsLibRestrictedLockUtils`, `SettingsLibSelectorWithWidgetPreference`,
   `SettingsLibLayoutPreference`, `SettingsLibTwoTargetPreference` — e.g. the main
   target's `layout/preference_checkable_two_target.xml` inflates
   `layout/preference_two_target_divider` owned by TwoTargetPreference;
   `values/attrs.xml` references `string/disabled_by_admin` owned by
   RestrictedLockUtils).

### Result

**Code-level need: 6 targets** — main `SettingsLib`, `SettingsLibColor`,
`SettingsLibSettingsTheme` (all three already shipped as AARs) **plus 3 new**:
`SettingsLibAdaptiveIcon`, `SettingsLibActionButtonsPreference`,
`SettingsLibProgressBar`.

**Link-closed need: 10 targets = 7 new AARs**, 760 of 1512 files:

| target | files | status |
|---|---|---|
| SettingsLib (main) | 365 | existing AAR |
| SettingsLibSettingsTheme | 174 | existing AAR |
| SettingsLibSelectorWithWidgetPreference | 92 | **new** |
| SettingsLibRestrictedLockUtils | 87 | **new** |
| SettingsLibActionButtonsPreference | 15 | **new** |
| SettingsLibProgressBar | 10 | **new** |
| SettingsLibTwoTargetPreference | 7 | **new** |
| SettingsLibLayoutPreference | 6 | **new** |
| SettingsLibAdaptiveIcon | 3 | **new** |
| SettingsLibColor | 1 | existing AAR |

After fixpoint: **0 unresolved references** inside the closed set. The 28 remaining
"foreign" references are `androidx.preference`/Material3 styles and attrs (e.g.
`Preference.Material`, `PreferenceThemeOverlay`, `Theme.Material3.DynamicColors.DayNight`)
— supplied by existing official dependencies (`androidx.preference`, `material` in
`gradle/libs.versions.toml`), not by settingslib targets.

Needed code-accessed R namespaces: `com.android.settingslib` (main), `…color`,
`…widget.adaptiveicon` — all kept alive in B2 (and in B1′ via the constrained
coloring).

Reachable classes: 502 (479 from the main target + sub-target classes without
foreign R refs). All 74 directly-used classes are inside the closed set.

### Channels static analysis cannot see

- `Resources.getIdentifier(name, …)` — 40 SystemUI files call it; none of the scanned
  call sites builds a settingslib-prefixed name, but name concatenation is
  untrackable in general.
- Reflection, dynamic inflation by class name, `aapt`-flavored XML pulled at runtime.
- **Other shipped AARs' hidden class dependencies on settingslib** (e.g. does
  WifiTrackerLib reference settingslib classes?) — not audited in this task.

Exposure mode if wrong: B2's unshipped targets surface as **compile-time
`Unresolved reference`** (fail-fast, visible, fixable by adding one AAR) — the
benign failure mode. Resource-side misses surface at AAPT2 link (also build-time).
This is the key contrast to B1′'s runtime-invisible time bombs.

---

## Q4 — AGP/AAPT2 R-class mechanism (primary sources)

Sources: AGP 9.3.1 bytecode (`gradle-9.3.1.jar` in the Gradle cache) and
`sdk-common-32.2.0.jar`, decompiled with `javap` — commands recorded in the session
log; no AGP sources were on disk, so this is bytecode-level evidence.

1. **AAR = single namespace.** `AarToClassTransform$Companion.
   generateRClassJarFromRTxt$gradle_core` (gradle-9.3.1.jar) parses the AAR's
   `AndroidManifest.xml` via `AndroidManifestParser.parse` → `ManifestData.getPackage`,
   reads `R.txt` → `SymbolUtils.rTxtToSymbolTable(inputStream, package)`, and emits the
   compile-time R class jar **for that one package**. `LibrarySymbolTableTransform`
   likewise reads only `R.txt` + manifest package. One AAR → one R namespace;
   sub-namespaces require separate AARs (or separate compile units).

2. **Where dependency R classes come from at compile time.** This resolves the puzzle
   observed in the main project's build intermediates: `SystemUI-core`'s
   `compile_r_class_jar` contains **only** `com/android/systemui/R.class`, yet core
   compiles `com.android.settingslib.color.R.color.…` fine. Answer: the consumer's
   R.jar carries only its own namespace; each **AAR dependency's** R classes are
   generated by the per-AAR transform above and enter the compile classpath as
   transform artifacts. (Empirical cross-check: app's `compile_symbol_list` R.txt
   contains `int color settingslib_color_blue400 0x0` — placeholder IDs at compile,
   final IDs at link.)

3. **Final IDs at app link.** The app link path runs
   `Aapt2ProcessResourcesRunnableKt` → `RGeneration.generateRForLibraries`, which
   builds library symbol tables via `SymbolTable.withValuesFrom` — and that operator
   **filters out symbols absent from the source (merged, post-link) table**.
   Consequence for "R.txt-only AAR" (no res files, manifest + R.txt only): it compiles
   (mechanism 1 needs only R.txt) but its symbols have no resources in the merged
   table → filtered from the final R → **runtime `NoSuchFieldError`**.
   *Confidence: medium-high.* The bytecode chain is verified, but the exact argument
   wiring into `generateRForLibraries` was not fully traced (no AGP sources on disk).
   Per the brief, this is marked **not fully verified — do not build B3 on it**.

4. **Merging semantics**: values resources merge at **entry (symbol) level** across
   libraries (duplicate `(type,name,config)` = error unless identical); file resources
   collide on `(type,name,config)`; same-path values files from different source roots
   are not themselves an error — but overlapping entries are (see Q1's clique).

---

## Q5 — Options and recommendation

All options keep every shipped file byte-exact (Rule R), use only AARs built from
AOSP products by `tools/package_aosp_aar.py` (Rule B/provenance), and wire through
ADR 0005 POM transitive dependencies (main SettingsLib AAR's POM declares the
sub-AARs, mirroring AOSP `Android.bp` `static_libs`; `build.gradle.kts` unchanged).

### Option A — Task 014 baseline: 30 new per-target AARs

33 total settingslib AARs. Full AOSP fidelity, zero dormant breakage, trivial
rollback. Cost: exactly what the user rejected — 30 new AARs + 30 POMs to maintain.

### Option B1′ — namespace-aware minimum merging: 12 AARs

The constrained 12-coloring (Q1), anchors main/Color/SettingsTheme/AdaptiveIcon alive
in distinct groups. 12 AARs; packager merges each group's res tree (path-disjoint by
construction) and class jars into one AAR per group.

- Rule R: byte-exact files, but the **merged AAR is a synthesized product** — closer
  to the grey area than per-target AARs (though the same synthesis the reference
  project already ships).
- Runtime risk (Q2): **39 dormant broken classes, 0 reachable today** — crashes would
  be runtime-invisible until an AOSP sync touches them.
- Rollback: re-split affected group into per-target AARs; moderate.
- Needs a `package_aosp_aar.py` extension for group merging.

### Option B2 — reachability-driven shipping: 7 new AARs (10 total) ✅ RECOMMENDED

Ship exactly the Q3 link-closed set: keep existing main/Color/SettingsTheme AARs
unchanged, add **7 new per-target AARs** (SelectorWithWidgetPreference 92 files,
RestrictedLockUtils 87, ActionButtonsPreference 15, ProgressBar 10,
TwoTargetPreference 7, LayoutPreference 6, AdaptiveIcon 3 — 760/1512 files total).

- **Fewest AARs of any verified-safe option** (7 new vs 30 — a 77% reduction;
  directly answers "30 is too many").
- Rule R/B: purest compliance — each AAR is one AOSP target, byte-exact, no merging,
  no synthesis, no namespace collapse; every needed R namespace (`main`, `color`,
  `widget.adaptiveicon`) stays alive (Q3).
- Runtime risk: **0 reachable broken classes**; the 32 dormant ones are simply not
  shipped. Missed-dependency risk (blind spots, Q3) fails **at compile time** —
  fail-fast, one-line fix (add the AAR), the benign failure mode. Contrast with
  B1′'s runtime `NoSuchFieldError`.
- Rollback/addition: purely additive; when future SystemUI code reaches a new layer,
  add that target's AAR in the same pattern.
- Wiring: main SettingsLib POM gains 7 transitive deps (ADR 0005); version bump only.

### Option B3 — R-only namespace AARs: blocked

Q4's evidence (medium confidence) says R.txt-only namespaces get filtered at link →
runtime failure. Not verifiable from bytecode alone; would need an AGP-source or
empirical spike. **Not recommended.**

### Grey-zone k=1 single AAR: rejected (Q1 — k stays 12 anyway; Rule R synthesis).

### Recommendation

**B2.** It is the minimum-AAR option that keeps every failure mode compile-visible,
requires no packager changes (per-target AAR packaging already exists), keeps all
live R namespaces, and rolls back/adds incrementally. If the user later wants full
class coverage (e.g. to immune against AOSP syncs pulling in new settingslib usage),
B1′ (12 AARs) is the verified runner-up and can be adopted with the same POM wiring.

---

## Blind spots and confidence labels

| Finding | Confidence | Gap |
|---|---|---|
| Q1 k=12 strict + clique optimality | high | exact algorithm + witness |
| Q1 relaxed variant = 12 | high | entry-overlap verified on clique paths |
| Q2 74 used classes / 39-0 breakage | high | source + bytecode double-attributed |
| Q3 6→10 link closure | high | static only; reflection/getIdentifier/other-AAR class deps unaudited |
| Q4 compile-time R from R.txt+manifest | high | bytecode-verified |
| Q4 R.txt-only AAR link filtering | medium-high | arg wiring into `generateRForLibraries` not traced; no AGP sources on disk |
| Ref-project collapse viability | supporting only | different, smaller usage surface; manifest package of ref AAR not inspected |

## Appendix — reproducibility artifacts (all in /tmp, not committed)

- `/tmp/t016_closure.py` — target/file/path model (reproduces Task 014's 33/1512/599/101)
- `/tmp/t016_q1.json` — strict coloring groups + dup groups; `/tmp/t016_q1_variant.py`
- `/tmp/t016_q1_constrained.json` — constrained 12-coloring (B1′ grouping)
- `/tmp/t016_rrefs.json` — class → owning target + bytecode R references
- `/tmp/t016_crossrefs.json` — 19 foreign-namespace-referencing classes
- `/tmp/t016_q2_*.json`, `/tmp/t016_pkgs.json` — Q2 usage evidence, target packages
- `/tmp/t016_q3.py` + `/tmp/t016_q3.json` — reachability BFS (6 targets, 502 classes)
- `/tmp/t016_q3_linkclosed.json` — link-closure fixpoint (10 targets)
- `/tmp/t016_proj_syms.json` — 5256 SystemUI-res symbols (shadowing check)
- `/tmp/t016_refaar/` — reference project SettingsLib AAR extraction (Q2/Q4 evidence)
