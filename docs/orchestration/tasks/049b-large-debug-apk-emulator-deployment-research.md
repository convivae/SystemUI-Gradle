# Task 049B — Large Debug APK deployment research for a disposable API 37 AVD

## Goal

Determine one evidence-backed, reversible way to make the unchanged 163,546,744-byte Debug APK appear at the real SystemUI system path across a full kernel reboot, so PackageManager performs a genuine boot-time parse, without modifying shared SDK/system-image inputs.

## Context

Task 049 proved:

- Debug APK: `163,546,744` bytes, SHA-256 `c064003108ec9471ee0180122144a1c46f8030c8bc6a6777cabff5614846535e`.
- The disposable API 37 AVD's adb-remount overlay scratch is ~79 MB with only ~34 MB available; direct replacement truncates with ENOSPC.
- A runtime bind mount from `/data/local/tmp` works and propagates to init/system_server/zygote namespaces, but `stop`/`start` retains baseline Google PackageManager entry metadata, so its crash is not a valid Debug-manifest reproduction.
- Directly adding an upperdir symlink does not replace the lower file in the live merged overlay view, so that experiment was rolled back before reboot.
- The device is restored; this research task must not touch it.

## Required questions

1. From primary/local sources, explain exactly how emulator `-writable-system`, `-partition-size`, AVD `disk.dataPartition.size`, dynamic partitions, and adb-remount overlay scratch relate. Does any supported emulator option enlarge the scratch available to `/system_ext`?
2. Is there a supported way to give a single disposable AVD a private writable copy/overlay of `system_ext` large enough for a 164 MB replacement without mutating `/home/conv/Android/Sdk/system-images/**`?
3. Can a bind-mounted APK be made visible across a full reboot through an official emulator/ADB facility without init scripts, package-cache deletion, or shared image mutation?
4. Rank viable methods by correctness, reversibility, provenance, and risk. Recommend exactly one next experiment, with preconditions, commands, expected observations, and exact rollback. If none is sufficiently safe, say so explicitly.

## Allowed

- Read-only inspection of AOSP sources, emulator/ADB help and binaries, installed AVD config/images, Task 048/049 evidence and docs.
- Official Android documentation lookup.
- One new document: `docs/architecture/2026-08-22-large-debug-apk-emulator-deployment.md`.

## Forbidden

- Any Gradle command.
- Any ADB/emulator/AVD mutation or process control.
- Any edit outside the one allowed architecture document.
- Modifying shared SDK/system images, product files, manifests, sources, resources, dependencies, or build rules.
- Guessing commands without primary-source support.

## Acceptance

- Evidence cites exact source/help/document locations.
- Separates proven facts from hypotheses.
- Gives one recommended experiment or a clear no-safe-method result.
- `git diff --check` clean; exactly one file changed.
- English commit; no push; terminal `HANDOFF:` with commands and findings.
