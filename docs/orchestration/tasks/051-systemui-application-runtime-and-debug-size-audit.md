# Task 051 — SystemUI Application/runtime and Debug APK size root-cause audit

## Authority

`self-commit`, documentation-only research. The user explicitly requested an independent Worker investigation before further discussion. The Worker commits one focused English commit and never pushes. No implementation or fix is approved.

## Goal

Prove the complete AOSP-to-Gradle-to-APK-to-runtime `SystemUIApplication` chain, classify the first post-wipe runtime divergence without symptom suppression, quantify why the Debug APK is about 163.6 MB, and present at least three evidence-backed solution families for user discussion.

## Required reading and startup

Read in this order:

1. `AGENTS.md` in full.
2. `docs/orchestration/CHARTER.md` in full.
3. This brief.
4. `docs/issues/2026-08-22-systemui-application-runtime-and-debug-size-audit.md`.
5. `docs/superpowers/plans/2026-08-22-systemui-application-runtime-and-debug-size-audit.md`.
6. `docs/issues/2026-08-22-direct-debug-apk-runtime-closure.md`.
7. `docs/orchestration/tasks/050-direct-debug-apk-runtime-closure.md`.
8. `docs/CURRENT_STATE.md`.
9. `docs/orchestration/STATE.md` and the final 30 lines of `docs/orchestration/log.md`.

Invoke `worker-contract`, `research`, and `systematic-debugging`. If research requests a nested agent, do the primary-source work directly instead; do not dispatch another Worker. Print the complete `CONTRACT:` before investigation.

## Fixed artifact/evidence locations

- Task 050 worktree: `/home/conv/myspace/SystemUI-Gradle-wt-050`
- Frozen Debug APK: `/home/conv/myspace/SystemUI-Gradle-wt-050/app/build/outputs/apk/debug/app-debug.apk`
- Frozen Debug SHA-256: `4d8240fdbbc144dfeb69b43dc3e5ad3911762afc90a8f83e07434d0669f78997`
- Main Release APK: `/home/conv/myspace/SystemUI-Gradle/app/build/outputs/apk/release/app-release.apk`
- Task 050 evidence: `/tmp/task050-evidence/`
- Original emulator SystemUI evidence/backup: first prefer `/tmp/task050-evidence/`; if absent, use read-only `adb pull` into `/tmp/task051-*` from the path returned by `pm path com.android.systemui` only after verifying `ro.kernel.qemu=1` and AVD name.
- AOSP root: `/home/conv/myspace/aosp`
- Reference project: `/home/conv/myspace/CarSystemUIGradle`

Before analysis, verify the frozen Debug SHA-256. If it differs or the file is absent, emit `REDLINE: Task 051 frozen artifact mismatch` and stop.

## Primary-source requirements

Use and cite:

- AOSP `frameworks/base/packages/SystemUI/Android.bp`, `AndroidManifest.xml`, `SystemUIApplication.java`, and relevant Soong Java/app packaging implementation;
- current project `settings.gradle.kts`, root/module `build.gradle.kts`, source roots, and packaged Debug manifest/DEX;
- current SysUISdk `android.jar`, runtime framework bytes where safely obtainable read-only, fresh PackageManager metadata, and the complete post-wipe fatal/hidden-API logs;
- the three APK byte inventories: frozen Debug, current Release, and original emulator SystemUI.

Do not infer that an empty `:app/src` means library classes are absent. Prove or disprove packaging from project dependency configuration and actual DEX descriptors. Likewise, do not infer that a `NoSuchMethodError` means the runtime member is physically absent until hidden-API enforcement and runtime DEX contents are independently checked.

## Allowed paths

- Create `docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md`.
- Modify `docs/issues/2026-08-22-systemui-application-runtime-and-debug-size-audit.md` only to append the final result, evidence summary, and report link.
- Create temporary evidence under `/tmp/task051-*`.

## Forbidden paths and commands

Everything else is read-only. In particular, do not modify any source, resource, manifest, Gradle file, catalog, dependency, AAR/JAR/POM, APK, build output, SDK, AOSP checkout, emulator image, AVD, userdata, rule/ADR, CURRENT_STATE, PLAN, orchestration file, or Task 050 file.

Forbidden actions:

- all Gradle tasks;
- source-level `try/catch` or any implementation proposal that treats the call-site exception as the fix;
- `adb root`, `remount`, `push`, `install`, `shell rm/mv/cp`, `logcat -c`, reboot, process kill, package clear, userdata wipe, or emulator/AVD mutation;
- artifact rebuilding/repacking/signing;
- Git history archaeology beyond current-file inspection and the Worker's own final commit.

Read-only ADB is allowed only for: `getprop`, `dumpsys`, `pm path`, `stat`, `sha256sum`, `logcat -d`, and `adb pull` to `/tmp/task051-*`. If the emulator is offline, use retained evidence and report that limitation; do not start it.

## Required analysis

Execute all five tasks in the referenced plan. The final report must include:

1. an AOSP intent table for `android_app "SystemUI"`, `SystemUI-core`, manifest, certificate/platform APIs, privilege/system placement, hidden-API/package flags, and resource ownership;
2. an exact assembly chain from `SystemUIApplication.java` through `:SystemUI-core`, `:app`, final DEX descriptor, packaged manifest, PackageManager selection, and constructor entry;
3. an evidence-based classification of every candidate: missing application class, stale PackageManager metadata, runtime member absence, hidden-API denial, signing/domain mismatch, and source/runtime revision mismatch;
4. a clear first-divergence/root-cause statement that distinguishes direct evidence from unresolved uncertainty;
5. reproducible Debug/Release/original APK compressed and uncompressed size tables, SHA-256 values, DEX/class counts, and largest size drivers;
6. at least three coherent solution families with prerequisites, risks, rule impacts, and exact validation gates;
7. explicit rejection of call-site `try/catch` as a solution;
8. `Gradle: NOT RUN` and `Mutations: NONE`.

## Acceptance

Run:

```bash
python3 - <<'PY'
from pathlib import Path
p = Path('docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md')
s = p.read_text()
required = [
    'AOSP intent', 'Assembly chain', 'Runtime classification',
    'Debug APK size', 'Solution families',
    'SystemUIApplication', 'SystemUI-core', 'registerWithPerfetto',
    'hidden API', 'Gradle: NOT RUN', 'Mutations: NONE',
]
missing = [x for x in required if x.lower() not in s.lower()]
assert not missing, missing
assert s.count('NOT APPROVED') >= 3, s.count('NOT APPROVED')
print('TASK051_REPORT_PASS solution_families>=3')
PY
sha256sum /home/conv/myspace/SystemUI-Gradle-wt-050/app/build/outputs/apk/debug/app-debug.apk
git diff --check HEAD^
git diff-tree --no-commit-id --name-only -r HEAD | LC_ALL=C sort
```

Expected:

- report gate prints `TASK051_REPORT_PASS solution_families>=3`;
- Debug SHA-256 is exactly `4d8240fdbbc144dfeb69b43dc3e5ad3911762afc90a8f83e07434d0669f78997`;
- changed paths are exactly:

```text
docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md
docs/issues/2026-08-22-systemui-application-runtime-and-debug-size-audit.md
```

## Commit and report

Commit once with:

```bash
git add docs/architecture/2026-08-22-systemui-application-runtime-and-debug-size-root-cause.md \
  docs/issues/2026-08-22-systemui-application-runtime-and-debug-size-audit.md
git commit -m "docs: diagnose SystemUI runtime and APK size"
```

Never push. End with:

```text
HANDOFF:
- done: <evidence-backed result>
- verified: <commands and actual outputs>
- remaining: <uncertainties requiring an experiment or user decision>
```

## Reports to

Chief architect in the main herdr workspace. The report informs discussion only; none of its solution families is approved for implementation.
