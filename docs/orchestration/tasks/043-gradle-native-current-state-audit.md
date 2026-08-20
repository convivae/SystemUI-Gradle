# Task 043 — Gradle-native Current-State Architecture Audit

## Authority

`self-commit`, documentation-only. The user approved the Gradle-native functional-parity
architecture on 2026-08-21 and authorized this read-only present-state audit. The Worker commits
one focused English commit and never pushes. This authority does **not** include any build,
artifact, dependency, rule, SysUISdk, source, resource, policy, or rollback change.

## Goal

Audit the present SystemUI-Gradle architecture against the approved design and produce a
complete, primary-source decision ledger. The report must identify what to `keep`, `simplify`,
`consolidate`, treat as `candidate rollback`, send to `needs experiment`, or mark
`needs history/context`, without implementing or approving any change.

## Required reading and startup

Read in this exact order:

1. `AGENTS.md` in full.
2. `docs/orchestration/CHARTER.md` in full.
3. This brief.
4. `docs/issues/2026-08-21-gradle-native-architecture-reset.md`.
5. `docs/superpowers/specs/2026-08-21-gradle-native-systemui-build-design.md`.
6. `docs/superpowers/plans/2026-08-21-gradle-native-current-state-audit.md`.
7. `docs/CURRENT_STATE.md`.
8. `docs/orchestration/STATE.md` and only the final 20 lines of
   `docs/orchestration/log.md` for mandatory orchestration context.

Invoke `worker-contract`, then `research`, `codebase-design`, and
`superpowers:executing-plans`. If the research skill's nested background-agent mechanism is
unavailable, apply its primary-source discipline directly in this Worker; do not dispatch a
nested Worker. Print a complete `CONTRACT:` block before investigation.

## Fixed baseline facts

- Approved architecture checkpoint: commit `72970b84` must be an ancestor of the dispatch
  checkout. This is an ancestry assertion only; do not inspect its diff or history.
- Current topology: 13 included Gradle modules.
- Current artifact baseline: 29 `libs/aars/*.aar`, 27 `libs/maven/**/*.aar`, 28 root
  `libs/*.jar`, and 1 `libs/prebuilts/**/*.jar`.
- Current local Maven includes 20 SettingsLib-family AARs; this is an audit priority, not an
  automatic rollback decision.
- Current release R8 remains blocked by one `AssumeTrueForR8` missing reference. The old S3c +
  byte-exact whole-rule-file Task 042 proposal was rejected before implementation.
- Task 041 remains closed. Its current S3b adapter is audited but not changed or reopened.
- No active recommendation has implementation approval.

Initial baseline commands allowed:

```bash
git merge-base --is-ancestor 72970b84 HEAD
git rev-parse HEAD
git status --short
```

Expected: ancestry exit 0, one present checkout hash, and clean worktree. Any mismatch is
`REDLINE: Task 043 baseline mismatch`.

## Primary sources

Use the present versions of:

- this repository's `settings.gradle.kts`, root/module `build.gradle.kts`, manifests,
  `gradle/libs.versions.toml`, artifacts/POMs, packaging tools/tests, SysUISdk tools/tests, and
  five project rule files;
- `/home/conv/myspace/aosp/frameworks/base/packages/SystemUI/**/Android.bp`;
- current owner `Android.bp`/source/output files for each external AOSP artifact family;
- `/home/conv/myspace/CarSystemUIGradle` current settings/build/docs files as a comparison,
  not a normative template;
- artifact bytes inspected read-only with `zipinfo`, `unzip`, `jar`, `javap`, `sha256sum`, and
  Python snippets writing only to `/tmp/task043-*`.

Every substantive claim cites a present `path:line`, exact artifact path plus inventory fact,
or recorded read-only command output. If present evidence cannot establish original motivation,
use `needs history/context`; do not infer it.

## Allowed paths

- Create `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`.
- Modify `docs/issues/2026-08-21-gradle-native-architecture-reset.md` by appending the audit
  result/link/evidence summary without rewriting the approved rationale.
- Create temporary read-only extraction/inventory data under `/tmp/task043-*` only.

## Forbidden paths and commands

Everything else is read-only. In particular, do not modify:

- any `*.gradle.kts`, `gradle/**`, `settings.gradle.kts`, catalog, manifest, rule, source,
  resource, AAR, JAR, POM, SDK, tool, test, ADR, AGENTS, CHARTER, CURRENT_STATE, PLAN, HANDOFF,
  orchestration state/log/task, or approved spec/plan;
- `/home/conv/myspace/aosp/**`, `/home/conv/myspace/CarSystemUIGradle/**`, or the live/staging
  Android SDK;
- build outputs.

Forbidden commands/actions:

- all `./gradlew`, `gradle`, AGP, package/rebuild/install, SDK staging/apply, and artifact-writing
  commands;
- `git log`, `git show`, `git blame`, `git reflog`, GitHub/PR history, and diffs against older
  commits;
- checkout/reset/revert/cherry-pick/rebase/merge or any rollback;
- editing the brief to tick checkboxes.

`git status`, `git rev-parse HEAD`, the one fixed ancestry check, `git diff --check`, and
inspection of the Worker's own final commit are allowed.

## Required analysis

Execute every task and step in
`docs/superpowers/plans/2026-08-21-gradle-native-current-state-audit.md`.
The report must contain:

1. exactly 13 current module rows with namespace/source/resource/AIDL/processor/consumer seam
   evidence and deep-module deletion-test analysis;
2. every exact current AAR/JAR path, with owner/family, delivery role, SHA/size, provider,
   consumer/scope, class/resource/manifest/POM summary, and confidence;
3. family analysis for SettingsLib, WM-Shell, Traceur, WifiTrackerLib, iconloader,
   animationlib, setupcompat, LowLightDreamLib, and all discovered additional families;
4. all packaging/rebuild/install tools mapped to family refresh seams and tests;
5. direct-AAR versus local-Maven justification per family;
6. SysUISdk S0/S1/S2/S3/S3b/S4/S5 analysis and S3b category classification;
7. rule-by-rule analysis of the five project rule files plus AAR consumer rules;
8. a non-implementing comparison of at least five `AssumeTrueForR8` treatment classes;
9. a current-only comparison with CarSystemUIGradle;
10. the exact decision-ledger columns from the plan;
11. one `### <item> — NOT APPROVED` packet for every non-`keep` recommendation;
12. a risk-isolated future discussion order, not an implementation plan;
13. `Git history consulted: NO` and `Gradle: NOT RUN (read-only audit boundary)`.

Use artifact families as the default seam. A missing symbol or one Soong target is not a seam
justification. An umbrella artifact may include currently unused coherent family content.

## Mandatory redlines

Stop without modifying anything beyond an incomplete report note and emit `REDLINE:` if:

1. the fixed baseline ancestry, clean-worktree, or exact artifact counts do not match;
2. analysis appears to require a Gradle build, artifact rebuild, SDK mutation, source/resource
   edit, or history lookup;
3. a current artifact cannot be safely inspected read-only;
4. any conclusion would require choosing between equivalent product policies;
5. an allowed-path change is insufficient to report the result truthfully.

## Acceptance

Run the exact completeness, scope, placeholder, whitespace, and self-review gates in plan
Task 10. Required successful output includes:

```text
AUDIT_STRUCTURE_PASS modules=13 source_aars=29 maven_aars=27 root_jars=28 prebuilt_jars=1 rules=5
```

Additional required final evidence:

```bash
git diff --check HEAD^
git diff-tree --no-commit-id --name-only -r HEAD | LC_ALL=C sort
```

Expected changed paths exactly:

```text
docs/architecture/2026-08-21-gradle-native-current-state-audit.md
docs/issues/2026-08-21-gradle-native-architecture-reset.md
```

No Gradle command is run. The final report and `HANDOFF:` must state that literally.

## Commit and report

Commit exactly once:

```bash
git add docs/architecture/2026-08-21-gradle-native-current-state-audit.md \
  docs/issues/2026-08-21-gradle-native-architecture-reset.md
git commit -m "docs: audit Gradle-native architecture seams"
```

Do not push. Report:

- commit hash;
- checklist completion;
- exact acceptance output;
- recommendation totals by allowed category;
- top evidence gaps and items requiring later targeted history;
- confirmation that no build, history lookup, implementation, rollback, artifact, or SDK
  mutation occurred;
- terminal `HANDOFF:` block.

## Reports to

Chief architect in the main herdr workspace. Worker completion is not approval of any report
recommendation; the architect will run dual-axis static review, verify the report on main, and
present each non-`keep` candidate to the user before any implementation task exists.
