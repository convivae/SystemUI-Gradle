# Orchestration Charter (CHARTER)

> Single source of truth for mandatory constraints in the herdr orchestration
> workflow. Re-read this file after any context compaction, before any action.
> Companion state file: `docs/orchestration/STATE.md`.
> Design spec: `docs/superpowers/specs/2026-08-12-herdr-orchestration-design.md`.

---

## Part 1 · Project Identity and Rule Priority

- This project ports AOSP `frameworks/base/packages/SystemUI` to a standalone
  Gradle build (AGP 9.3.1 + Gradle 9.5.0 + builtInKotlin 2.2.10). The goal is a
  genuinely compiled SystemUI APK, not a passing-looking one.
- Instruction priority, verbatim: **user instruction in chat > AGENTS.md +
  docs/HANDOFF.md > default system prompt**.
- Orchestration corollary: a task brief counts as the architect relaying a user
  instruction. If a brief conflicts with AGENTS.md rules, **the rules win** —
  the worker must halt and report instead of executing the conflicting step.

## Part 2 · The Ten Mandatory Rules

Each rule: one-line prohibition + source. The full text lives at the cited
anchor; never paraphrase rules into new meanings here.

| # | Rule | One-line prohibition | Source |
|---|------|----------------------|--------|
| P | No stubs | Never hand-write `*.java`/`*.kt` stubs to satisfy the compiler; never fabricate res files | AGENTS.md §1.2 |
| S | Source-first for SystemUI | Modules defined by `packages/SystemUI/**/Android.bp` are source dependencies, never jars | AGENTS.md §1.5 |
| C | Complete & Exact | Code/aidl/res must match AOSP 1:1 — nothing missing, nothing extra; verify with `tools/check_source_alignment.py` | AGENTS.md §1.6 |
| F | Framework via SDK/jar only | Non-SystemUI code is never source-copied; patch SysUISdk or framework.jar instead | AGENTS.md §1.7 |
| R | Res provenance | res files come only from AOSP source / AAR / official Maven; any modification needs ADR 0004 CONV markup plus explicit user authorization | AGENTS.md §1.8, ADR 0001, ADR 0004 |
| B | bp-aligned structure | Module boundaries, R namespaces, and entry-class locations follow `Android.bp` semantics | AGENTS.md §1.9, ADR 0003 |
| I | Forward progress | Error counts are diagnostics, never gates; never make a structural regression just to lower the count | AGENTS.md §2.1 |
| D | Documentation first | Record each step in `docs/issues/` before/with the work; report build results truthfully, never imply success | AGENTS.md §2.2 |
| H | Human escalation | The seven situations in AGENTS.md §2.5 require stopping and asking the user | AGENTS.md §2.5 |
| Tools | Python only | Scripts under `tools/` are Python; no `.sh` | ADR 0002 |

## Part 3 · Dependency Three-Tier Decision Tree

Run this tree before introducing any dependency, and write the verdict into the
issue record:

```text
Is it a soong module defined in frameworks/base/packages/SystemUI/**/Android.bp?
├─ yes → tier ①: copy source as a module (rule S)
└─ no  → available on Google Maven / Maven Central and not forked by AOSP?
    ├─ yes → tier ③: official coordinates
    │        (check maven-metadata.xml first; PITFALLS §1.7: AOSP prebuilt
    │         versions often do not exist on public Maven)
    └─ no  → tier ②: AOSP artifact — no resources → jar; with resources →
             AAR directly first; only after a confirmed conflict install into
             libs/maven via tools/install_aar_to_maven.py (ADR 0001)
```

Mechanism warning: Soong `static_libs` transitive dependencies do **not**
automatically appear on the Gradle compile classpath (all eight javac
root-cause groups from the 2026-08-12 Task 7 run stem from this). The POMs in
`libs/maven/` are dependency-free skeletons by default; the SettingsLib
resource closure is the sole exception (ADR 0005) — the `SettingsLib` POM
carries 7 per-target dependency edges mechanically mirroring `Android.bp`
`static_libs`.

## Part 4 · Toolchain Facts

- Version matrix: Gradle 9.5.0 / AGP 9.3.1 / Kotlin 2.2.10 (AGP builtInKotlin,
  **no explicit kotlin-android plugin**) / KSP 2.2.10-2.0.2 / Dagger 2.59.2 /
  Compose 1.11.4 (**do not upgrade to 1.12**: `ExperimentalAnimatableApi` was
  removed and AOSP sources use it — PITFALLS §1.6) / material3 1.5.0-alpha18.
- builtInKotlin trio: `android.builtInKotlin=true`,
  `android.disallowKotlinSourceSets=false`, and every Android module must set
  `kotlin.srcDirs(...)` aligned with `java.srcDirs(...)` (PITFALLS §1.5).
- SysUISdk is patchable: framework.jar adds hidden APIs, framework-res.apk adds
  private resource IDs, `framework.aidl` adds AIDL declarations (AGENTS.md
  §2.4). framework.jar must **not** be injected into KotlinCompile (it pollutes
  Compose inline metadata).
- KAPT is forbidden (incompatible with Gradle 9.5 — PITFALLS §1.2); all
  annotation processing uses KSP.
- Internal flags jars must precede framework.jar on the classpath or their
  same-named classes get shadowed (PITFALLS §2.x).

## Part 5 · Red-Line Areas

Touching any of the following requires a halt: the worker stops, prints
`REDLINE: <area> — <what it intended to do and why>`, and waits. The architect
relays it to the user; work resumes only after explicit user approval.

1. **AOSP-mirrored source/res**: `SystemUI-*/src/**`, `SystemUI-*/res*/**` —
   even CONV-markup scenarios need user authorization (R + ADR 0004).
2. **Any `res/` file** creation/modification/deletion (R).
3. **Rule and process files**: `AGENTS.md`, `docs/adr/**`,
   `docs/orchestration/CHARTER.md` (H.6).
4. **Dependency version matrix**: versions in `gradle/libs.versions.toml` and
   `settings.gradle.kts`, and the module include list (user preference:
   discuss upgrades first + rule B).
5. **Module boundaries**: adding/removing modules; moving entry classes
   (`SystemUIApplication`, `SystemUIService`) (ADR 0003).
6. **Build bypasses**: `@Suppress("DEPRECATION")`, excluding sources, disabling
   javac/D8/KSP checks, hand-written stubs (P/I/user preference).
7. **Non-Python scripts** under `tools/` (ADR 0002).

When unsure whether something is a red-line area, **treat it as red-line** —
false positives are cheap, violations are not.

## Part 6 · Current Project State Snapshot

One line only; details live in `docs/CURRENT_STATE.md` (always the authority):

> KSP 0 errors (2933 files), core Kotlin 0 errors; `:app:assembleDebug` is
> blocked by 42 javac errors in `:SystemUI-core:compileDebugJavaWithJavac`
> (eight attributed root-cause groups; APK not produced). See
> `docs/issues/2026-08-12-current-progress-standards-review.md` §Task 7.

Known accepted deviations: 1 src MODIFIED + 86 res byte-diffs (CONV discipline;
`--strict` does not gate on MODIFIED).

## Part 7 · Worker Contract

### Startup sequence (before writing any code)

1. Read `AGENTS.md` in full (not a summary).
2. Read this CHARTER.
3. Read your own task brief (`docs/orchestration/tasks/NNN-<slug>.md`).
4. Read the issue/plan documents referenced by the brief.
5. Print the `CONTRACT:` block (below). The architect verifies its presence
   via `herdr agent read`; dispatch is not confirmed without it.

```text
CONTRACT:
- task: <brief path>
- goal: <one line>
- allowed_paths: [...]
- forbidden_paths: [...]
- acceptance: <command + expected output>
- authority: self-commit | redline-gated
```

### Completion report (four parts, all required)

1. English commit (**never push** — the architect pushes after review; or, in
   REDLINE state, the uncommitted diff plus an explanation).
2. All brief checkboxes ticked, each with the **real** verification command
   output — fabricated success claims are a firing offense (PITFALLS §8.1).
3. `docs/issues/` day record updated (rule D).
4. A terminal-final `HANDOFF:` block the architect can capture:

```text
HANDOFF:
- done: <what was done>
- verified: <command> -> <actual output summary>
- remaining: <what is left, or "none">
```

## Part 8 · User Preference Hard Clauses

- Communicate in Chinese; commit messages in English; commit and push promptly.
- Plan before developing; incremental commits, each meaningful.
- Dependencies: latest public versions preferred, but **discuss upgrades first**;
  verify AOSP prebuilt versions against `maven-metadata.xml` before assuming a
  public equivalent exists.
- Never use `@Suppress` to bypass; consult official docs when unsure.
- Reference implementation: `CarSystemUIGradle`.
- Herdr worker model whitelist: **Kimi-K3, GLM-5.3, GLM-5.2 only**. The architect must pass an explicit model when starting pi (for example `-- --model joycode/GLM-5.3`) and verify the worker session's `modelId` before accepting `CONTRACT:`; never rely on pi's default model.
- Leave a complete handoff for the next AI — this CHARTER + STATE.md exist for
  exactly that purpose.
