# Orchestration Charter

> This file is operational guidance only. It does not create project constraints beyond
> the user's current instructions and [`AGENTS.md`](../../AGENTS.md).

## Authority and goal

Instruction priority is: current user instruction in chat, then `AGENTS.md` and its referenced project rules, then defaults. The goal is to produce genuinely built Debug and Release SystemUI APKs that deploy and remain stable across whole-device reboot on the target Android 17 emulator. Documentation, static checks, reviews, and intermediate experiments are evidence toward that goal; they are not substitutes for it.

## Worker autonomy

Workers are trusted engineering collaborators. A worker may inspect the repository and AOSP tree, create temporary diagnostic scripts and evidence, modify authorized project files, run tests, build APKs, operate Herdr, validate artifacts or devices, and create focused English commits. A worker may pursue a technically justified direction without waiting for ceremonial approval. If it encounters a decision it cannot make confidently, an `AGENTS.md` escalation condition, or a material product/architecture trade-off, it should stop and ask the Chief; the Chief asks the user when the Chief is also uncertain.

There is no mandatory startup-reading order, exact `CONTRACT:` text, fixed log-tail read, one-command allowance, exact tool-call count, mandatory checkpoint ceremony, or automatic retirement for harmless process deviations. Technical evidence is judged on correctness, reproducibility, provenance, and relevance to the final goal.

## Coordination

- The machine may run at most one heavy Gradle/Soong build at a time across the Chief and all Workers. Before starting a build, confirm another Worker is not already building.
- Workers may commit focused changes. They do not push; the Chief reviews and owns final push to the shared remote.
- Workers may use Herdr to run supporting processes and communicate status. They should identify processes they start and avoid disrupting another Worker's owned process.
- Shared-checkout edits must be coordinated. Independent worktrees may be used when parallel mutable work is actually useful.
- Read-only review can run in parallel with non-conflicting work. A reviewer role may remain read-only when independence is the purpose of that assignment.

## Verification and reporting

Workers report actual commands and results truthfully, including failures. They should prefer a short feedback loop: reproduce, form testable hypotheses, implement the most promising compliant fix, run focused tests, build when useful, inspect the artifact, and perform runtime validation when appropriate. A concise handoff is useful but no fixed wording is required.

`docs/CURRENT_STATE.md` remains the owner of live technical state. `docs/orchestration/STATE.md` and `docs/orchestration/log.md` record coordination history, but stale process restrictions in historical entries are not current authority.
