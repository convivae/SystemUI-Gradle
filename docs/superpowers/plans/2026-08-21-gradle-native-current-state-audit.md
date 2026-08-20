# Gradle-native Current-State Architecture Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Invoke the research skill for primary-source discipline and the codebase-design skill for module/seam analysis. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce a complete, read-only audit of the current Gradle modules, external artifact families, delivery mechanisms, SysUISdk stages, and release optimization inputs against the approved AGP-native functional-parity architecture.

**Architecture:** One isolated documentation-only Worker inspects the current checkout, current AOSP source/outputs, and the current CarSystemUIGradle reference project. It creates a primary-source architecture report and recommendation ledger without consulting Git history, changing build inputs, running Gradle, or implementing any recommendation. Every non-`keep` recommendation becomes an explicit approval packet for later user discussion.

**Tech Stack:** Markdown, Python 3 read-only inventory snippets, `rg`, `find`, `unzip`/`zipinfo`, `jar`/`javap`, Kotlin DSL static inspection, AOSP `Android.bp` primary sources.

**Spec:** `docs/superpowers/specs/2026-08-21-gradle-native-systemui-build-design.md`

## Global Constraints

- This task is report-only: no source, resource, Gradle, artifact, SDK, tool, catalog, manifest, rule, or dependency mutation.
- Do not run `./gradlew`, `gradle`, AGP tasks, SDK apply commands, packaging/rebuild/install tools, or any command that writes an artifact.
- Do not inspect Git history. `git log`, `git show`, `git blame`, `git reflog`, and diffs against older commits are forbidden. Use only the present worktree, `git status`, and `git rev-parse HEAD` for baseline identity.
- Current AOSP and reference-project files are read-only primary sources. Temporary extraction/inventory data may be written only under `/tmp/task043-*`.
- Do not presume any current item should be removed. Recommendations are limited to `keep`, `simplify`, `consolidate`, `candidate rollback`, `needs experiment`, and `needs history/context`.
- For every non-`keep` row, explain present role, current evidence, maintenance cost, guarantee at risk, proposed next investigation/change, and exact future build/runtime validation. Mark approval `NOT APPROVED`.
- Artifact families, not missing symbols or individual Soong targets, are the default analysis seam. Use the codebase-design deletion test, depth, leverage, and locality vocabulary.
- Preserve the 13 current source modules unless a concrete current-state seam problem is demonstrated; even then report only.
- Direct AAR is the default delivery hypothesis. Local Maven is justified only by demonstrated Gradle metadata, transitive dependency, or resource-resolution needs.
- `AssumeTrueForR8` is an optimizer/build-time classification question. The rejected S3c/byte-exact Task 042 proposal is not an implementation option authorized by this audit.
- No Gradle/build verification is required or permitted. Acceptance is static and must state `Gradle: NOT RUN (read-only audit boundary)`.
- Worker commits once in English and never pushes.

---

## File map

- Create: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md` — complete current-state inventory, family/seam analysis, decision ledger, and approval packets.
- Modify: `docs/issues/2026-08-21-gradle-native-architecture-reset.md` — append audit execution/result summary, truthful no-build statement, report link, and unresolved questions.
- Read only: all project build/catalog/tool/artifact/rule files; current AOSP owners and outputs; current CarSystemUIGradle files; approved spec and current governance documents.

### Task 1: Establish the current-only evidence boundary

**Files:**
- Create: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`
- Modify: `docs/issues/2026-08-21-gradle-native-architecture-reset.md`

**Interfaces:**
- Consumes: approved spec, present checkout, present AOSP tree/output, present reference project.
- Produces: a report whose claims cite current `path:line`, artifact inventory output, or a recorded read-only command; no historical causal claims.

- [ ] **Step 1: Read the mandatory current contracts**

Read, in order:

```text
AGENTS.md
docs/orchestration/CHARTER.md
docs/orchestration/tasks/043-gradle-native-current-state-audit.md
docs/issues/2026-08-21-gradle-native-architecture-reset.md
docs/superpowers/specs/2026-08-21-gradle-native-systemui-build-design.md
docs/superpowers/plans/2026-08-21-gradle-native-current-state-audit.md
docs/CURRENT_STATE.md
docs/orchestration/STATE.md
docs/orchestration/log.md (last 20 lines only, required orchestration context)
```

- [ ] **Step 2: Record the immutable present-worktree baseline without reading history**

Run:

```bash
git rev-parse HEAD
git status --short
```

Expected: one dispatch-base commit hash and an initially clean worktree. Record the hash, date, `/home/conv/myspace/aosp`, `/home/conv/myspace/CarSystemUIGradle`, and the declaration `Git history consulted: NO` in report §1.

- [ ] **Step 3: Create the report structure**

Create these exact top-level sections:

```markdown
# Gradle-native Current-State Architecture Audit
## 1. Method, baseline, and evidence boundary
## 2. Current Gradle module seams
## 3. Complete local artifact inventory
## 4. Artifact-family seam analysis
## 5. Delivery and refresh mechanisms
## 6. SysUISdk adapter analysis
## 7. AGP/R8 rule and optimizer-closure analysis
## 8. Current reference-project comparison
## 9. Decision ledger
## 10. User approval packets
## 11. Unknowns, confidence, and evidence gaps
## 12. Recommended decision sequence
## 13. Verification record
```

Under §1 state the non-goals: no history, no implementation, no rollback, no build, and no policy-file modification.

### Task 2: Inventory and assess the 13 current Gradle module seams

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`

**Interfaces:**
- Consumes: `settings.gradle.kts`, root and module `build.gradle.kts`, manifests, source-set declarations, current AOSP SystemUI `Android.bp` files.
- Produces: exactly 13 module inventory rows plus one topology-level ledger row.

- [ ] **Step 1: Enumerate modules and present dependency declarations**

Run read-only searches:

```bash
rg -n '^include\(' settings.gradle.kts
rg -n 'project\(|implementation\(|api\(|compileOnly\(|ksp\(' \
  build.gradle.kts app/build.gradle.kts SystemUI-*/build.gradle.kts
rg -n 'namespace|sourceSets|java\.srcDirs|kotlin\.srcDirs|res\.srcDirs|aidl\.srcDirs' \
  app/build.gradle.kts SystemUI-*/build.gradle.kts
```

Expected: the 13 modules listed by the approved spec. Record for each module its namespace, source/resource/AIDL ownership, processors, direct project dependencies, external dependency families, consumers, and current seam rationale.

- [ ] **Step 2: Compare semantic ownership to current AOSP source**

Read current `frameworks/base/packages/SystemUI/**/Android.bp` owner definitions. Cite exact AOSP `path:line` evidence for source/resource ownership and current Gradle `path:line` evidence for each module. Do not require one Gradle module per Soong target.

- [ ] **Step 3: Apply the deep-module seam tests**

For each module record:

- interface callers must understand;
- implementation complexity hidden behind the seam;
- leverage and locality supplied by the seam;
- deletion-test result;
- demonstrated namespace/processor/AIDL/cycle constraint, if any;
- recommendation and confidence.

Do not propose an implementation. If current evidence cannot justify changing a seam, use `keep` or `needs experiment`, not speculation.

### Task 3: Build a complete artifact and consumer inventory

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`

**Interfaces:**
- Consumes: every current AAR/JAR, POM, version-catalog alias, and dependency declaration.
- Produces: path-complete inventories covering 29 `libs/aars/*.aar`, 27 `libs/maven/**/*.aar`, 28 root `libs/*.jar`, and 1 `libs/prebuilts/**/*.jar` at the approved baseline.

- [ ] **Step 1: Generate read-only inventory data under `/tmp`**

Run:

```bash
rm -rf /tmp/task043-inventory
mkdir -p /tmp/task043-inventory
find libs/aars -maxdepth 1 -type f -name '*.aar' -print | LC_ALL=C sort \
  > /tmp/task043-inventory/source-aars.txt
find libs/maven -type f -name '*.aar' -print | LC_ALL=C sort \
  > /tmp/task043-inventory/maven-aars.txt
find libs -maxdepth 1 -type f -name '*.jar' -print | LC_ALL=C sort \
  > /tmp/task043-inventory/root-jars.txt
find libs/prebuilts -type f -name '*.jar' -print | LC_ALL=C sort \
  > /tmp/task043-inventory/prebuilt-jars.txt
wc -l /tmp/task043-inventory/*.txt
```

Expected counts: source AARs 29, Maven AARs 27, root JARs 28, prebuilt JARs 1. A mismatch is not permission to edit artifacts; record it as a baseline discrepancy and stop for architect guidance.

- [ ] **Step 2: Record per-artifact facts**

For every exact path in the four inventories, record:

- path, size, SHA-256;
- artifact family and AOSP owner;
- delivery role (`source AAR`, `direct AAR`, `local Maven AAR`, `program JAR`, `compile/library JAR`, or `platform input`);
- provider recipe/tool and whether it is registered or manually maintained;
- consumer module, Gradle configuration, catalog alias/direct file reference;
- classes count, resource-file count, manifest presence, and POM dependency count where applicable;
- duplicate delivery relationship, if the same source AAR is installed to Maven;
- recommendation and confidence.

Use `zipinfo`, `unzip -p`, `sha256sum`, current scripts, current catalog, and current build files. Extraction goes only to `/tmp/task043-*`.

- [ ] **Step 3: Verify consumers and orphans statically**

Search all current Gradle build files/catalog entries and map every artifact to a consumer or mark it `unconsumed-currently`. Do not equate unconsumed with safe deletion; choose `candidate rollback`, `needs history/context`, or `needs experiment` with explicit risk.

### Task 4: Analyze artifact-family seams and real split constraints

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`

**Interfaces:**
- Consumes: Task 3 inventory, AAR class/resource/manifests, current AOSP owners/`Android.bp`, current consumers.
- Produces: family-level seam findings and bounded future experiments, not implementation instructions.

- [ ] **Step 1: Analyze SettingsLib as one family**

Cover all 20 current SettingsLib-family Maven AARs and corresponding source AARs. Record:

- current umbrella code artifact and resource-owner artifacts;
- current 17 POM dependency edges;
- class-set intersections;
- resource paths/namespaces and manifests;
- which splits have a currently demonstrable namespace/resource reason;
- which splits appear to expose shallow Soong-target seams;
- the coarsest plausible future seam and the exact experiment needed to validate it.

Do not merge files, rewrite resources, or claim consolidation is safe without an experiment.

- [ ] **Step 2: Analyze WM-Shell and Traceur seams**

For WM-Shell main/shared and Traceur code/resource delivery, record current class/resource overlap, manifest/namespace constraints, consumers, and whether the split supplies depth/locality or merely exposes packaging implementation. Report future merge experiments separately for each family.

- [ ] **Step 3: Analyze the remaining AAR families**

Cover at least WifiTrackerLib, iconloader, animationlib, setupcompat, LowLightDreamLib, and every additional family discovered by Task 3. For each, decide whether the current seam already matches the one-family default and whether local Maven is currently justified.

- [ ] **Step 4: Analyze JAR families by role**

Group JARs by coherent owner/role—framework/platform, compilelib, aconfig generated runtime, SystemUI flags, tracing/view-capture/motion, monet, annotations, proto, car/module API—and identify only demonstrated duplicate, obsolete, optimizer-only, or refresh-fragmentation concerns.

### Task 5: Audit delivery and refresh mechanisms

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`

**Interfaces:**
- Consumes: every current `tools/package*.py`, `tools/rebuild*.py`, `tools/install_aar_to_maven.py`, their tests, POMs, catalog and repositories configuration.
- Produces: a recipe-to-family map, local-Maven justification table, and refresh-cost assessment.

- [ ] **Step 1: Enumerate all current packaging/rebuild/install tools**

Run:

```bash
find tools -maxdepth 1 -type f \( -name 'package*.py' -o -name 'rebuild*.py' -o -name 'install_aar_to_maven.py' \) \
  -print | LC_ALL=C sort
```

Record every exact path, family produced, input source, output paths, determinism/allowlist interface, associated tests, and whether a normal family refresh touches one recipe or several unrelated interfaces.

- [ ] **Step 2: Evaluate module depth and refresh locality**

Apply the deletion test to each packaging module and the local-Maven adapter. Identify pass-through/shallow interfaces only where current evidence shows their complexity would vanish under a family recipe. Do not recommend layering a new wrapper over old tools; future proposals should replace or deepen seams.

- [ ] **Step 3: Classify every local-Maven family**

For each family, cite the current POM metadata/resource-resolution requirement that justifies Maven, or mark the justification unproven. `catalog uniformity` alone is not justification. Record direct-AAR migration only as a candidate requiring later build/resource experiments.

### Task 6: Audit the current SysUISdk adapter

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`

**Interfaces:**
- Consumes: `tools/build_sysuisdk.py`, all invoked patch tools/tests, tracked SDK input artifacts, present live/staging layout read-only.
- Produces: one row per S0/S1/S2/S3/S3b/S4/S5 concern and one row per S3b class category.

- [ ] **Step 1: Map stage interfaces and inputs**

Record each stage's current interface, input, output mutation within staging, platform/runtime purpose, verification coverage, and refresh coupling. Do not run `--apply`, build a staging SDK, or modify the live SDK.

- [ ] **Step 2: Classify injected categories**

Classify hidden APIs, AIDL, private resources, dalvik annotations, and each S3b category (`IoUtils`, `NativeAllocationRegistry`, DDMS, `UnsupportedAppUsage`, `AconfigFlagAccessor`, keepanno annotations) as:

- `platform-required`;
- `optimizer-only`;
- `mixed/uncertain`;
- `obsolete` only when current primary-source evidence proves it.

For each non-platform-required category, explain what guarantee would be lost by removal and the future release/runtime experiment required. Task 041 remains closed; this audit does not reopen or change it.

### Task 7: Audit AGP/R8 configuration and the remaining annotation

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`

**Interfaces:**
- Consumes: `app/build.gradle.kts`, five current project rule files, module consumer-rule wiring, AAR consumer rules, current `missing_rules.txt` if present, AOSP annotation source/current use sites.
- Produces: rule-by-rule semantic classification and a comparison matrix for the remaining `AssumeTrueForR8` treatment, without choosing or implementing one.

- [ ] **Step 1: Inventory all current project rule files and wiring**

Cover these five exact files:

```text
app/proguard_common.flags
app/proguard.flags
app/proguard_kotlin.flags
SystemUI-plugin-core/proguard.flags
SystemUI-plugin/proguard_plugins.flags
```

For each rule block, cite the current reflection/JNI/serialization/plugin/generated-code/runtime evidence, consumer/application wiring, and recommendation. A rule's similarity to Soong is not sufficient evidence.

- [ ] **Step 2: Classify current AAR consumer rules**

Inspect each AAR for `consumer-rules.pro`/`proguard.txt` and map it to the consuming Gradle path. Distinguish legitimate dependency interface requirements from copied or currently unproven rules.

- [ ] **Step 3: Reclassify `AssumeTrueForR8` under the approved policy**

Using current AOSP source and current class use sites, compare at least:

1. a real compile/optimizer annotation artifact;
2. a narrowly scoped `-dontwarn` proposal;
3. a platform/SysUISdk library-class treatment;
4. importing AOSP assumption semantics selectively;
5. leaving flag-folding optimization absent while preserving correctness.

For each, record runtime correctness implications, optimization implications, maintenance cost, APK-packaging risk, and future verification. Do not select or implement a mechanism; recommendation must remain `needs experiment` or `needs history/context` where evidence is insufficient.

### Task 8: Compare the current reference-project approach

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`

**Interfaces:**
- Consumes: current `/home/conv/myspace/CarSystemUIGradle` settings/build files and current docs only.
- Produces: a mechanism comparison, not a copy recommendation.

- [ ] **Step 1: Inventory reference-project seams**

Read its current module includes, app/core dependency declarations, direct JAR/AAR use, SysUISdk treatment, and release optimization configuration. Cite exact current paths/lines.

- [ ] **Step 2: Compare maintainability mechanisms**

Record which coarse mechanisms improve depth/locality and which cannot be transferred because this project's AOSP revision, resources, module topology, or runtime closure differs. Do not treat the reference project as normative or inspect its Git history.

### Task 9: Produce the decision ledger and approval packets

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`
- Modify: `docs/issues/2026-08-21-gradle-native-architecture-reset.md`

**Interfaces:**
- Consumes: Tasks 2–8 findings.
- Produces: complete decision input for architect/user discussion; no authorized changes.

- [ ] **Step 1: Complete the decision ledger**

Use this exact column contract:

```markdown
| Item | Present role | Current constraint solved | Maintenance cost | Design classification | Recommendation | Confidence | Evidence needed |
```

Include all 13 modules, all artifact families, direct-AAR/local-Maven delivery, each packaging/refresh mechanism, each SysUISdk stage/category, each rule file/consumer-rule family, and `AssumeTrueForR8`. Every recommendation must use an allowed value exactly.

- [ ] **Step 2: Write one approval packet per non-`keep` item**

Each packet must contain:

```markdown
### <item> — NOT APPROVED
- Why it exists now:
- Current primary-source evidence:
- Constraint/guarantee it provides:
- Maintenance cost:
- Proposed disposition or experiment:
- What could be lost:
- Exact future static/build/runtime validation:
- History needed later (if any):
```

Do not infer original historical motivation. If present evidence cannot answer it, say so and request narrowly scoped history later.

- [ ] **Step 3: Order future user decisions**

Recommend a decision order that isolates risk: optimizer-only annotation/rules, delivery adapters, low-resource families, WM-Shell, SettingsLib resources, SysUISdk, module seams, then device/runtime closure unless evidence supports a safer order. This is discussion order only, not implementation authorization.

- [ ] **Step 4: Update the issue record**

Append the report link, baseline, inventory totals, recommendation totals by category, top evidence gaps, and `Gradle: NOT RUN (read-only audit boundary)`. Do not overwrite the approved architecture rationale.

### Task 10: Run static acceptance and self-review

**Files:**
- Modify: `docs/architecture/2026-08-21-gradle-native-current-state-audit.md`
- Modify: `docs/issues/2026-08-21-gradle-native-architecture-reset.md`

**Interfaces:**
- Consumes: completed report and issue update.
- Produces: one clean English documentation commit, never pushed.

- [ ] **Step 1: Run the completeness gate**

Run exactly:

```bash
python3 - <<'PY'
from pathlib import Path

report_path = Path('docs/architecture/2026-08-21-gradle-native-current-state-audit.md')
text = report_path.read_text(encoding='utf-8')

headings = [
    '## 1. Method, baseline, and evidence boundary',
    '## 2. Current Gradle module seams',
    '## 3. Complete local artifact inventory',
    '## 4. Artifact-family seam analysis',
    '## 5. Delivery and refresh mechanisms',
    '## 6. SysUISdk adapter analysis',
    '## 7. AGP/R8 rule and optimizer-closure analysis',
    '## 8. Current reference-project comparison',
    '## 9. Decision ledger',
    '## 10. User approval packets',
    '## 11. Unknowns, confidence, and evidence gaps',
    '## 12. Recommended decision sequence',
    '## 13. Verification record',
]
for heading in headings:
    assert heading in text, heading

modules = [
    ':app', ':SystemUI-core', ':SystemUI-res', ':SystemUI-common',
    ':SystemUI-animation', ':SystemUI-plugin-core', ':SystemUI-plugin-processor',
    ':SystemUI-plugin', ':SystemUI-unfold', ':SystemUI-customization',
    ':SystemUI-shared', ':SystemUI-shared-biometrics', ':SystemUI-compose',
]
for module in modules:
    assert f'`{module}`' in text, module

inventories = {
    'source_aars': sorted(Path('libs/aars').glob('*.aar')),
    'maven_aars': sorted(Path('libs/maven').rglob('*.aar')),
    'root_jars': sorted(Path('libs').glob('*.jar')),
    'prebuilt_jars': sorted(Path('libs/prebuilts').rglob('*.jar')),
}
expected = {'source_aars': 29, 'maven_aars': 27, 'root_jars': 28, 'prebuilt_jars': 1}
for name, paths in inventories.items():
    assert len(paths) == expected[name], (name, len(paths), expected[name])
    for path in paths:
        assert path.as_posix() in text, path

rules = [
    Path('app/proguard_common.flags'), Path('app/proguard.flags'),
    Path('app/proguard_kotlin.flags'), Path('SystemUI-plugin-core/proguard.flags'),
    Path('SystemUI-plugin/proguard_plugins.flags'),
]
for path in rules:
    assert path.as_posix() in text, path

for rec in ('keep', 'simplify', 'consolidate', 'candidate rollback',
            'needs experiment', 'needs history/context'):
    assert rec in text, rec
assert 'Git history consulted: NO' in text
assert 'Gradle: NOT RUN (read-only audit boundary)' in text
assert 'NOT APPROVED' in text
print('AUDIT_STRUCTURE_PASS modules=13 source_aars=29 maven_aars=27 root_jars=28 prebuilt_jars=1 rules=5')
PY
```

Expected output:

```text
AUDIT_STRUCTURE_PASS modules=13 source_aars=29 maven_aars=27 root_jars=28 prebuilt_jars=1 rules=5
```

- [ ] **Step 2: Run scope, placeholder, and whitespace gates**

Run:

```bash
python3 - <<'PY'
import subprocess

allowed = {
    'docs/architecture/2026-08-21-gradle-native-current-state-audit.md',
    'docs/issues/2026-08-21-gradle-native-architecture-reset.md',
}
lines = subprocess.check_output(
    ['git', 'status', '--porcelain=v1'], text=True
).splitlines()
changed = {line[3:] for line in lines if line}
assert changed <= allowed, sorted(changed - allowed)
print('SCOPE_PASS ' + ' '.join(sorted(changed)))
PY
python3 - <<'PY'
from pathlib import Path

tokens = [
    'T' + 'BD', 'T' + 'ODO', 'FIX' + 'ME', 'PLACE' + 'HOLDER',
    '待' + '定', '稍后' + '补',
]
paths = [
    Path('docs/architecture/2026-08-21-gradle-native-current-state-audit.md'),
    Path('docs/issues/2026-08-21-gradle-native-architecture-reset.md'),
]
for path in paths:
    text = path.read_text(encoding='utf-8')
    found = [token for token in tokens if token in text]
    assert not found, (path, found)
print('CONTENT_SCAN_PASS')
PY
git diff --check
```

Expected: `SCOPE_PASS` lists only the two allowed documentation paths; `CONTENT_SCAN_PASS`; `git diff --check` exits 0.

- [ ] **Step 3: Self-review against the approved spec**

Explicitly check and record in report §13:

- all spec §11.1 audit areas are covered;
- no recommendation is presented as approved;
- no historical cause is asserted without current evidence;
- SettingsLib is not treated as an automatic rollback;
- runtime and build validation are future gates, not claimed results;
- no byte/configuration parity is used as an acceptance criterion;
- no Gradle/build/package/apply/history command was run.

- [ ] **Step 4: Commit once and report**

Run:

```bash
git add docs/architecture/2026-08-21-gradle-native-current-state-audit.md \
  docs/issues/2026-08-21-gradle-native-architecture-reset.md
git commit -m "docs: audit Gradle-native architecture seams"
```

Expected: one English commit. Do not push. End with a `HANDOFF:` block containing the commit, completeness-gate output, recommendation totals, top evidence gaps, and `Gradle: NOT RUN (read-only audit boundary)`.
