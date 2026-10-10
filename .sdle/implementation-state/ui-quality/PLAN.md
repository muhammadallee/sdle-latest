# SDLE UI Quality Enhancement — Implementation Plan v2.2 (incremental, Pareto-first)

**Target:** `muhammadallee/sdle-latest`, branch `enh/requirements-package-loop` at commit `3cd3b19`. The remote was re-checked unchanged on 10 Oct 2026.
**Date:** 10 October 2026
**Supersedes:** v2.1 (10 Oct 2026). v2 and v2.1 are left unedited.
**Inputs:** v2; the external review of v2 (findings F1–F8); the external feedback on v2.1 (pilot cost, rendered-UI metric, checkpoints, waivers); owner answers of 10 Oct 2026 (D3: no one uses SDLE; the owner runs the work in Claude Code CLI on their own machine); probes run against the engine.
**Status:** **PLAN ONLY.** Nothing is implemented. Ready to run **Phase A-build** in Claude Code CLI on the owner's machine (§15, Appendix E). Phase A's measurement waits for decision D4 (§9.1).

**Labels used throughout**

| Label | Meaning |
|---|---|
| **[verified: executed]** | Run against the engine at `3cd3b19` |
| **[verified: read]** | Read in the source at `file:line` (commit `3cd3b19`) |
| **[reasoned]** | A design conclusion |
| **[hypothesized]** | An expected benefit not yet measured |
| **[proposed]** | A name or design that does not exist in the code |

Line numbers will drift. Function names are the stable anchors.

---

## 0. Changes from v2.1

| # | Change | Where | Source |
|---|---|---|---|
| 1 | Exactly **one full SDLE run** per measured phase proves lifecycle integration. All arm comparisons are **isolated experiments** on fixed requirements, reported separately and never described as full SDLE runs | §7; A, B, C row 4 | Feedback on v2.1, point 1 |
| 2 | Phase A's **primary metric is the blind-rated rendered UI**. The completeness rubric is supporting only. Go/no-go asks for visual improvement on the demanding screen with no significant regression elsewhere | A rows 2, 4, 9; §13 | Point 2 |
| 3 | Checkpoints are anchored on the **recorded commit SHA**; tags are optional and never authoritative. Status (`complete` / `awaiting owner` / `built, unmeasured`) is decided by `PROGRESS.md`, not by tags. Each checkpoint is **pushed** after asking. Resume verifies ancestry of the recorded SHA | §5.1, §5.2, §8, §10 | Point 3, plus this revision: an unpushed checkpoint is not durable |
| 4 | The human-waiver rule is described everywhere as a **convention**, never as proof of human authorization | F8, M, Appendix C | Point 4 |
| 5 | **D3 decided: no adopters.** D4 explained (§9.1). D5 and the go/no-go thresholds restated as targets | §9 | Owner; point "Decisions" |
| 6 | Phase A split into **A-build** (no pilot needed) and **A-measure**. A Claude Code CLI kickoff prompt is added | A; §15; Appendix E | The owner runs the work |
| 7 | C is kept on its own merits (subjective visual quality); it is decided by its own experiment, not by how A and B turn out | §1; C row 1 | Feedback |
| 8 | Effort re-estimated | §6 | Consequence of 1 |

---

## 1. Verdict and Pareto MVP

**On the external review:** largely right.

| Disposition | Findings |
|---|---|
| Accepted | F1, F2, F5, F6, F8 |
| Partially accepted, with counter-evidence from executed probes | F3, F4, F7 |
| Rejected | None |

Its phase order is adopted with three changes:

1. **F8 and v2's two loop defects become an optional standalone slice, M.** All three are general correctness fixes. M is required only before Phase C, and nothing earlier depends on it.
2. **Every phase carries its own Codex plan review and implementation review**, each at most 2 rounds (§5). Unresolved items stop the phase and are put in front of the owner.
3. **Measurement is folded into Phases A–C**: one full SDLE run per measured phase, plus isolated experiments on fixed requirements (§7).

**Pareto MVP = Phase A + Phase B.**

- **A — UI intent.** Prompt and guideline changes only; no engine change.
- **B — executable browser checks** through the existing test-evidence path; no engine change.

Together they cover the two biggest observed gaps:
- SDLE gives the implementer **no UI intent at all** today [verified: read — no UI content anywhere in `.claude/`, `scripts/sdle.py`, the ADRs or the Reference Guide].
- Objective UI defects are deterministically testable, and are caught today only if someone happens to write a test for them.

**Do first:** Phase A.

**Defer:** C until A and B are measured, but do not drop C because A and B succeed: they cover intent and objective correctness, while C targets subjective visual quality that deterministic checks cannot capture. D until C's measurements and decisions D1 and D6. E items until a pilot shows the need.

**Reject:** a new phase, gate, agent, review type, standalone UI design document, separate visual loop, applicability taxonomy, versioned contracts, or any mandatory design tool or SaaS.

---

## 2. Evidence: verified behaviour and corrected assumptions

### 2.1 Verified for this revision (ids R1–R18; not to be confused with Phase E items E1–E5)

| # | Fact | Label | Evidence | Effect on the plan |
|---|---|---|---|---|
| R1 | The branch is unchanged since v2; all 140 of v2's line references still hold | verified: executed | `git ls-remote` = `3cd3b19`; reference-check script, 0 misses | v2 inventories are reusable |
| R2 | Full suite baseline: 4190 passed, 24 skipped, about 9.5 min; `lint-skill` and `validate` exit 0 | verified: executed | Run on 9 Oct (suite) and 10 Oct (lint, validate) at `3cd3b19`, Linux, Python 3.13 | Every phase must keep this green |
| R3 | A harness exiting 78 is recorded `status: FAILED, exit_code: 78`; a missing binary is recorded `runner not installed` | verified: executed | `run_tests` called with each command (`sdle.py:18477-18521`) | F6: the exit code survives for the orchestrator, but the engine does not classify it |
| R4 | Two blocking findings at the same location and obligations yield two identical fingerprints, and fixing one changes the progress digest | verified: executed | Probe on `_blocking_finding_fingerprints` (`sdle.py:16216-16231`) | F7: multiplicity is counted |
| R5 | A reworded or renumbered finding keeps the same fingerprint | verified: executed | Same probe | No false progress from rewording |
| R6 | "A fixed, new B at the same location and obligations" is indistinguishable, so the loop reports `no_progress` | verified: executed | Same probe | F7's collision is real, but it errs toward a premature stop for a person, never false progress |
| R7 | A later non-`code-review` record on the manifest hides an open blocking code-review finding from the progress digest | verified: executed | Probe; filter on path only at `sdle.py:16219` | Fixed in M |
| R8 | An agent-authored review may mark a blocking finding `accepted` and record `PASS`. No existing test uses review-finding `accepted` | verified: read | `sdle.py:12083-12093` checks only `open`; repository-wide search of `tests/` | F8: the fix (M) breaks no existing test |
| R9 | The loop's test helper records code reviews without `--findings` | verified: read | `tests/test_units_loop.py:48-50` | Requiring findings (M) means one helper change and a dry-run 25 update |
| R10 | `gate approve` does not recompute drift; it reads the stored `drift_queue` | verified: read | `sdle.py:12628-12630` | F3: any rule that reads `plan.md` must itself check the plan's approved fingerprint |
| R11 | Product agents are pinned to `Read, Grep, Glob`; no other tool can be granted without changing a linted constant | verified: read | `sdle.py:19780`, `:19855-19865` | F5: if `Read` cannot show a subagent an image, no permitted image pathway exists |
| R12 | `workitems/<id>/specs/` is the write-fence carve-out, and the feature directory is excluded from the tree digest | verified: read | `hooks.py:103`; `sdle.py:18651-18653` | F4: optional previews can live in the feature directory without breaking evidence |
| R13 | Spec Kit `specify` requires a technology-agnostic spec written for business stakeholders; the plan template is the developer-facing "how" | verified: read (external) | Spec Kit v1.0.6 `templates/commands/specify.md`, `plan-template.md` | The spec/plan split from v2 stays |
| R14 | A Codex review convention already exists: a runner, a review schema, plan and implementation prompts, run records, and ledger dispositions. All prior rounds, round 2 included, used `review.schema.json` | verified: read | `.sdle/implementation-state/requirements-package-loop/codex/codexrun_stage2.py`, `review.schema.json`, `plan-round{1,2}.prompt.md`, `impl-r*-round*.prompt.md`, `runs/*.json` | Reused in place (§5). The runner takes `RUNS_DIR` as an argument |
| R15 | Codex CLI is not installed in this cloud session; the previous rounds ran with `codex-cli 0.160.1` on the owner's machine | verified: executed | `which codex` returns nothing; run records | Codex rounds run where Codex is available; an infrastructure failure is recorded and escalated, never substituted silently |
| R16 | A sensitive file once reached Codex through a frozen worktree | verified: read | `requirements-package-loop/LEDGER.md:14-15` | Privacy check before every Codex run (§5.4) |
| R17 | A new record directory under `.sdle/implementation-state/` must be added to the enumerated `MAINTENANCE_RECORDS` set, and its pinned count changes from 4 to 5 | verified: read | `tests/conftest.py:652-664`; `tests/test_units_capabilities.py:658` | A cost of the first phase that creates `ui-quality/` |
| R18 | Every page under `docs/` must be reachable from an entry document; enhancement records are linked from `docs/README.md` | verified: read | `tests/test_units_doc_links.py:185`; `docs/README.md:104-108` | New docs pages are linked from `docs/README.md` |

### 2.2 Corrected assumptions from v2

| v2 assumption | Correction | Source |
|---|---|---|
| A declared UI path plus a JUnit report plus any hashed PNG proves UI evidence (v2 §8.2) | Insufficient. A backend case and an arbitrary image satisfy it. Replaced by an evidence map that ties screen ids to executed browser cases and screenshots (Phase D) | F1 |
| Ignored screenshots with stored hashes are adequate retention (v2 D1 default) | Not durable: the hash outlives the file. Replaced by a retention contract (Phase D, D1) | F2 |
| Exit 78 gives environment classification (v2 H4) | Only a convention. The code survives in the evidence (R3); classification is the orchestrator's. An engine mapping is optional (E2) | F6 |
| An ARIA/DOM fallback can stand in as advisory visual review (v2 §7.4) | It is not visual review. Without image perception the label is "visual judgment unverified" | F5 |
| Previews fully deferred (v2 §5) | Optional reference preview for high-uncertainty UI, with a recorded decision; text stays authoritative | F4 |
| v2 Phase 0 is a prerequisite for everything | Optional standalone slice M, needed only before Phase C | Review §4 |
| v2's pilot as its own phase | A phase that ships no improvement is not allowed; measurement is folded into A–C | Review §1.2 |
| Token totals and the 57% accessibility-coverage figure (v2 §6.3, §15) | Removed as unverifiable for this context. Phase C measures actual tokens | Review §3 P2 |

---

## 3. Dispositions of F1–F8

| # | Finding (short) | Disposition | Repository evidence | Correction | Priority / phase |
|---|---|---|---|---|---|
| F1 | Evidence must establish a *relevant executed* UI check, not JUnit plus any PNG | **Accept** | v2 §8.2 is satisfiable by unrelated evidence [reasoned]; `--junit` hashing and case parsing already exist (`sdle.py:18978-18987`, `:15738-15750`) [verified: read] | [proposed] `manifest build --ui-map <json>` records `{screen, state, viewport, cases[], screenshots[]}` inside the existing evidence record. Engine checks: each case exists in the captured JUnit and passed; each case name contains its screen id; each screenshot exists and its hash matches; every screen id in the *approved* `plan.md` appears in the map. Semantic adequacy stays review judgment. Adversarial tests cover unrelated PNGs, a passing backend case, a failing case, an altered or deleted PNG, and a missing screen | P0 for any enforcement claim; **D** |
| F2 | Retention must make hashes useful | **Accept** | WorkItem evidence is versioned (`CLAUDE.md:36`); the engine is standard-library only with no network, so it cannot verify a remote artifact [verified: read] | Retention contract. **Default proposal:** small sanitized screenshots versioned inside the WorkItem evidence directory (capped count and size; synthetic data only), so the engine can re-verify them. A CI artifact reference is allowed but labelled *"recorded, not engine-verified"*. Traces, HTML reports, `storageState` and credentials are never versioned. Missing mandatory evidence is refused at the gate, never called verified. Until D, screenshots are labelled *"not retained, not integrity-protected"* | P0 for durable-evidence claims; **D** (needs D1) |
| F3 | UI applicability must go beyond path matching | **Partially accept** | `gate approve` does not recompute drift (R10); `HOTFIX` has no `gate_plan` (`SKILL.md:135`) [verified: read] | Applicability is the union of three signals: (a) the `UI impact:` marker in `plan.md`, trusted only while the plan matches its approved `gate_plan` fingerprint; (b) policy `ui_paths` intersecting the change set; (c) a submitted UI map. A conflict — (a) says `none` while (b) fires — is refused (*proposed* `ui_impact_conflict`). The remedy is a human decision through the existing paths: re-approve the corrected plan, or revert the UI change. **Counter:** a backend change that alters the UI without touching a declared path, while the plan says `none`, is not deterministically detectable; that boundary is documented as review judgment. No classification engine | P1; **D** |
| F4 | Restore adaptive visual intent | **Partially accept** | Feature directory carve-out (R12) [verified: read] | Phase A adds risk-based preview guidance. `plan.md` records `Visual concept: used <path> \| declined: <reason> \| existing UI sufficient`. An optional reference preview (static HTML/CSS or image) lives under `{featureDirectory}/ui-preview/`. Text in the gated artifacts stays authoritative, and no tool or gate is mandated. **Counter:** whether previews improve design is [hypothesized]; isolating it needs extra pilot arms, so the measurement is deferred to E5 instead of inflating A | P1 guidance in **A**; measurement in **E5** |
| F5 | Visual review needs real image perception | **Accept** | Agents are pinned to `Read, Grep, Glob` (R11) | C's first task is an experiment: can `sdle-code-review`, as configured, perceive a PNG? It uses seeded defects only visible in pixels. **If no:** C ships only "screenshots listed at the gate for the human" plus the label *"visual judgment unverified"*; no ARIA-as-visual claim and no tool widening without a separate decision | P1; **C** (go/no-go) |
| F6 | Exit code 78 is a convention | **Accept, option (b) now** | R3 (executed, Linux) | B states that the orchestrator reads `tests.exit_code == 78` and records `--classification environment_blocker`. This is convention, not a fail-safe. E2 offers a narrow engine mapping if the pilot shows misclassification. Windows is untested (D5) | P1; **B** (convention), **E2** (engine) |
| F7 | Fingerprints can merge distinct defects | **Partially accept** | R4–R6 (executed): multiplicity is counted; rewording is stable; the "fixed A / new B" collision produces a premature `no_progress`, a stop for a person, **not** false progress | C adds tests for "reworded same issue" (no progress) and "two defects at one location, one fixed" (progress). C also validates `ui:` location grammar, because non-canonical location strings are the real false-progress risk. **Counter:** adding a category to the fingerprint creates the opposite risk (a reviewer re-categorizing the same issue would read as progress), so it is deferred to E3 unless the pilot shows harmful collisions | P1; **C**, **E3** |
| F8 | Blocking-finding waivers need human authorization | **Accept, moved earlier (M)** | R8 | M: the engine refuses an `agent`-actor review that marks a blocking finding `accepted` (*proposed* `review_waiver_requires_human`). A waiver must be recorded in a review with `--actor-type human`. **Limit:** the actor type is self-declared, so this prevents *silent AI* acceptance by default but cannot prove a human (ADR-007 §3). The refusal message, troubleshooting entry and ADR note must say exactly that, and must never call it authorization. Every waiver is shown at the gate (C) | P1; **M** (general), display in **C** |
| P2 | Timeout and CI cost of full suites in every iteration | Accept | 600 s default (`sdle.py:21186`) | B measures suite duration. The same full command runs every iteration; the timeout is raised explicitly; the final evidence is never shrunk. If the suite is too slow, the owner reduces the plan's viewport/state matrix — that changes scope, not evidence | B |
| P2 | No screenshots means "visual judgment unverified" | Accept | — | C, in the gate display | C |
| P2 | `HOTFIX`/`DEFECT_FIX` keep no design gate | Accept | `SKILL.md:134-135` | All phases | All |
| P2 | Advisory guidance vs binding policy for older WorkItems | Accept | ADR-011 | A–C are advisory prompt changes; only D is binding, opt-in by policy | §8 |
| P2 | Privacy, auth fixtures, flakiness, laundering, same-screen defects, shared regeneration | Accept | — | §8, B, C, E1 | Various |

---

## 4. Phases, dependencies and stopping points

```text
                 ┌──────────────┐
 SDLE @3cd3b19 ──┤ A  UI intent ├──► B  browser checks ──┐
       │         └──────────────┘                         ├──► C  visual critique ──► D  opt-in enforcement
       └──────────► M  loop & review integrity ───────────┘        (needs A, B, M)      (needs B; C recommended;
                    (standalone; any time before C)                                       decisions D1, D6)
 E1–E5: optional, each released on its own, each depends only on the phase it refines
```

| Phase | Requires (released) | Usable improvement if you stop here for good | Safe to stop indefinitely? |
|---|---|---|---|
| **A** | Nothing beyond `3cd3b19` | Spec, plan and tasks carry complete UI intent: journeys, states, device classes, accessibility, screens, component reuse, test mapping. Brownfield conventions persist. Previews used only where uncertainty is high | Yes. Prompt-only; no runtime dependency |
| **B** | A | Browser journeys, states and layout checks run through the existing manifest. A failing check blocks the gate via `tests_not_passed`. The example harness is reusable by projects | Yes. No engine change; the evidence contract is pinned by SDLE tests |
| **M** | Nothing beyond `3cd3b19` | No-progress detection uses structured findings; another review type can no longer hide code-review blockers; an AI cannot silently waive a blocking finding | Yes. Small, general, tested |
| **C** | A, B, M | Located visual findings from an independent reviewer on real screenshots — or, if image perception fails, an honest "unverified" label with screenshots surfaced to the human. Waivers visible. Repair loop demonstrated once | Yes. Existing gate semantics unchanged |
| **D** | B (C recommended); D1, D6 decided | Opt-in: a relevant UI change cannot reach `gate_implement` with absent, stale or irrelevant UI evidence | Yes. Inert unless a repository declares it |
| **E1–E5** | The refined phase | One measured fix each | Yes, each |

**No phase is preparation-only.** A, B, M, C and D each change what a user or reviewer sees. E items are optional by definition.

---

## 5. Review protocol: Codex plan and implementation review in every phase

### 5.1 Sequence for each phase (M, A, B, C, D and each E item)

1. **Phase plan.** Write `.sdle/implementation-state/ui-quality/phases/<X>-PLAN.md`. Take the phase contract from §6 and re-verify every file and line against the *current* HEAD. This is also the resume point after a pause. Commit it.
2. **Codex plan review, round 1.** Freeze a worktree at that commit; run Codex read-only (§5.3). Record the run. The **first** phase executed also has Codex review this plan's cross-cutting sections (§2–§5, §8–§10), so this plan itself is reviewed exactly once, before any implementation.
3. **Dispositions.** For each finding: accept (with fix) or reject (with evidence — an executed probe where possible). Record in `LEDGER.md`, then revise the phase plan.
4. **Codex plan review, round 2.** Run it if round 1 produced any accepted defect or any rejection. Round 2 verifies the fixes, re-judges each rejection (uphold or withdraw) and hunts defects the fixes introduced. **No round 3.**
5. **Implement**, with targeted tests. Then `lint-skill` and the **full suite in the foreground**; record the command and counts.
6. **Codex implementation review, round 1**, on `git diff <phase-base>..HEAD`, with the test evidence. Dispositions and fixes as in step 3; re-run the tests.
7. **Codex implementation review, round 2** under the same trigger as step 4. **No round 3.**
8. **Checkpoint** (§10): update `PROGRESS.md` (commit SHA, status, test evidence, open decisions, next-phase prerequisites), commit, **ask the owner, then push** to the agreed remote branch, and **stop**. A local tag is optional and never authoritative. There is no autonomous continuation into the next phase.

### 5.2 What counts as unresolved — highlighted to the owner, never buried

Each of these goes into the **"Owner attention"** table at the top of `docs/enhancements/ui-quality/PROGRESS.md` and into the phase-end report:

- a finding Codex **UPHELD** in round 2 that Claude still disputes;
- a finding accepted but not fixed within the phase's scope;
- any `blocking_disputes` entry, or a coverage gap (`areas_not_reviewed`) in round 2;
- any Codex run recorded `BLOCKED` or `INTERRUPTED` after its one retry;
- any item needing an owner decision (D1–D6, thresholds, privacy).

Each row carries: id · source (Codex finding id, probe or decision) · what is unresolved · why · options · recommendation · whether it blocks merging this phase.

A phase with open rows is **committed and pushed, but marked `awaiting owner` in `PROGRESS.md`** — never `complete`, whatever tags exist. The tree is still coherent, because every commit passes the full suite. Nothing is merged or claimed complete until the owner decides each row.

### 5.3 Mechanics (reuse, no new tooling)

- **Runner**, reused in place: `python .sdle/implementation-state/requirements-package-loop/codex/codexrun_stage2.py <AREA> <FROZEN_WORKTREE> <PROMPT> .sdle/implementation-state/requirements-package-loop/codex/review.schema.json .sdle/implementation-state/ui-quality/runs <TIMEOUT>`.
  - It invokes `codex exec --sandbox read-only --ephemeral --json --output-schema …`, retries once, and records `PASS` or `BLOCKED` [verified: read].
  - Its run ids carry a cosmetic "stage2" label.
- **Prompts:** `.sdle/implementation-state/ui-quality/codex/<X>-plan-round{1,2}.prompt.md` and `<X>-impl-round{1,2}.prompt.md`, modelled on the existing ones. Each has an attack list per phase taken from §6, and round 2 says "do not re-report fixed items; hunt regressions".
- **Records:** `.sdle/implementation-state/ui-quality/LEDGER.md` holds dispositions and test runs. `docs/enhancements/ui-quality/PROGRESS.md` holds status, checkpoints, the Owner-attention table and measurements, and is linked from `docs/README.md` (R18).
- **First phase that creates `ui-quality/`:** add it to `MAINTENANCE_RECORDS` and change the pinned count from 4 to 5 (R17).

### 5.4 Safety rules for reviews

- Codex is a reviewer only: read-only sandbox, ephemeral, a frozen worktree. It never approves a gate, edits files or decides an owner question.
- **Before each run:** `git ls-files` on the frozen worktree is checked for client data, credentials and pilot screenshots of real data (lesson R16). Pilot artifacts stay outside the SDLE repository.
- If Codex is unavailable, the run is recorded `BLOCKED` and escalated. A substitute reviewer (for example a fresh-context Claude subagent) is used **only with owner consent** and is labelled "not Codex".

**Review effort per phase:** about 0.5–1 day for four Codex runs plus dispositions and fixes. Planning estimate.

---

## 6. Phase contracts

The phase contract covers nine items for every phase:

1. Prerequisites
2. Improvement
3. Scope and files
4. Acceptance demonstration
5. Verification
6. Completion and rollback
7. Pause checkpoint
8. Resume
9. Go/no-go

All file references are [verified: read] at `3cd3b19` unless marked otherwise, and are re-verified in each phase plan (§5.1, step 1).

### Phase A — Better UI intent (no engine change)

Runs in two parts. **A-build** is the implementation and its Codex reviews; it needs no pilot. **A-measure** is §7 and needs D4. Stopping after A-build is safe and is recorded as `built, unmeasured`; no improvement is claimed until A-measure.

| # | Item | Content |
|---|---|---|
| 1 | Prerequisites | SDLE at `3cd3b19`. No other phase |
| 2 | Improvement | For user-visible work: `spec.md` carries journeys (Given/When/Then), required states, device classes and accessibility expectations. `plan.md` carries a **User Interface** section (UI impact marker, screen inventory with stable ids `UI-…`, components and tokens reused, viewports, test mapping, visual-concept decision). `tasks.md` has a test task per UI scenario. `app-design.md` gets a carried-forward **User Interface Conventions** section. Brownfield discovery and impact analysis name existing conventions and affected screens. **The improvement that counts is a better rendered UI** [hypothesized until A-measure]; a longer specification alone is not success |
| 3 | Scope | **Modify:** `.claude/skills/sdle/modules/phase-execution.md` (see below); `modules/design-review.md` (check the conventions section); `.claude/agents/sdle-design-review.md`; `guidelines/task-generation.md` (UI test-task rule); `guidelines/service-planning.md` (pointer); `SKILL.md` `CAPABILITY_MAP` `:279`, `:281`, `:284`, `:288`, `:290` (add the new guideline); optionally `.claude/agents/sdle-requirements-review.md` (flag UI requirements with no journeys or states). **New:** `.claude/skills/sdle/guidelines/ui-design.md` (intent sections, preview guidance, sizing guideline of 3–5 states and 2 viewports) |
| 3a | `phase-execution.md` edits | `spec_draft` `:99-109`: add a UI-scenario instruction next to the source-id instruction `:102`. `plan_draft` `:114-121`: the UI section. `tasks_draft` `:139-147`: UI test tasks. `design_generation` `:166-196`: the conditional conventions section and carry-forward read. `implement` `:205`: implementation args reference the plan's UI section and any preview. `discovery` `:48-59` and `impact_analysis` `:61-69`: the brownfield items |
| 3b | Also | `tests/test_units_install_contract.py:245-254` (+ guide count `:275-285` → "seven under `guidelines/`"); `tests/test_units_gate_policy.py:1405-1411`; `CLAUDE.md:57` ("six" → "seven"); `docs/GETTING-STARTED.md` §7 count; Reference Guide section. Maintenance record: `MAINTENANCE_RECORDS` and `test_units_capabilities.py:658` (R17); `docs/enhancements/ui-quality/PROGRESS.md` linked from `docs/README.md` |
| 3c | Deferred | Harness (B); visual review (C); every engine change |
| 4 | Acceptance demonstration | **Primary:** blind-rated rendered UI, baseline SDLE against SDLE + A, in isolated experiments on fixed requirements for three screens of D4's app — a visually demanding screen, a conventional form or table, and a brownfield modification — with at least 3 runs per arm (§7). **Supporting:** intent completeness (Appendix A), tokens, wall-clock. **Integration:** one full SDLE run of the enhanced arm on the demanding screen through `gate_implement`, reported separately |
| 5 | Verification | `lint-skill`; install-contract and gate-policy tests; doc-link and documented-command tests; full suite in the foreground (record counts against R2's baseline) |
| 6 | Completion and rollback | Prompt-only, so the default behaviour for non-UI work is unchanged. In-flight WorkItems pick up the guidance at their next phase; approved artifacts are not rewritten and no drift is caused [reasoned]. Rollback: `git revert` of the phase range is safe; nothing is persisted in new formats |
| 7 | Pause checkpoint | `PROGRESS.md` entry with SHA and status (`built, unmeasured` after A-build; `complete` or `awaiting owner` after A-measure); pushed (§10) |
| 8 | Resume | §10 runbook; run B's phase plan review round 1 against the current HEAD |
| 9 | Go/no-go | **Targets** — the owner decides with the recorded numbers; these are not automatic rules: (a) on the demanding screen the enhanced arm's mean rating beats baseline by ≥ 0.5 on the 1–5 scale and wins in ≥ 2 of 3 paired runs; (b) no other screen's mean drops by more than 0.3; (c) completeness ≥ 5 of 7 and above baseline; (d) token/time increase ≤ 25% — exceeding it is reported, not an automatic rejection; (e) the full SDLE run reaches `gate_implement` with no refusal caused by A. **If no visual gain is shown:** make no visual claim; keep A only if B goes ahead (B uses A's test mapping), otherwise revert it |
| — | Effort (estimate) | Build 1.5–2 d · Codex 0.5–1 d · measurement 1–2 d (one full run with the owner at the gates; experiments run unattended; rating) → **3–5 d** |

### Phase B — Executable UI checks (no engine change)

| # | Item | Content |
|---|---|---|
| 1 | Prerequisites | A released (B's tests come from A's plan test mapping). Not M |
| 2 | Improvement | Missing, overlapping, off-screen and broken-journey defects become failing tests before human review, and block `gate_implement` through the existing `tests_not_passed`. Evidence stays tree-bound |
| 3 | Scope | **Modify:** `guidelines/ui-design.md` (append the harness contract H1–H11, Appendix B); `phase-execution.md` `implement` `:206-214` (use the harness via `--test-command`/`--junit`; outputs to ignored paths; classify exit 78; same full command every iteration). **New:** `docs/examples/ui-harness/` — a README and one example harness script plus a config sample, labelled "example, verified on pilot `<sha>` with `<runner version>`; not exercised by SDLE CI", linked from `docs/README.md` |
| 3a | Tests (existing behaviour, newly pinned) | Extend `tests/test_units_tree_digest.py` / `tests/test_units_implementation_evidence.py`: (i) a Python stand-in harness writes JUnit into the evidence directory and a PNG into an ignored path → `evidenceStatus: valid`; (ii) exit 78 → `FAILED`, `exit_code: 78`, gate refuses `tests_not_passed`; (iii) an unignored `test-results/` → `invalid_changed_during_run` (documents H7) |
| 3b | Deferred | Screenshot review (C); hashing and enforcement (D); engine exit-code mapping (E2); Windows (E4) |
| 4 | Acceptance demonstration | **Isolated experiment:** on A's enhanced-arm experiment implementations, inject 5 seeded objective defects, mutation-style, after implementation: overlap, missing empty state, horizontal overflow, an accessibility violation, a broken journey. Count detections. Five clean reruns as a **smoke test** for flakiness (not proof of stability). Suite wall-clock against the timeout. The harness also runs once inside A's full SDLE run's repository through `manifest build` |
| 5 | Verification | New tests, lint, full suite in the foreground; the harness run on the pilot recorded with versions |
| 6 | Completion and rollback | Engine unchanged; projects opt in by using the harness. Revert is safe (docs, prompts, tests) |
| 7–8 | Checkpoint and resume | `PROGRESS.md` entry with SHA and status; pushed; as §10 |
| 9 | Go/no-go | **Go to C** if at least 4 of 5 seeded defect classes are detected, there are 0 flaky failures in 5 clean reruns, and the suite fits an explicit timeout *(targets; 0 of 5 flaky is a smoke test, not proof of stability)*. If browser tests are too slow or flaky on the pilot, stop at A+B and fix the harness before going further |
| — | Effort | Build 1.5–2.5 d · Codex 0.5–1 d · measurement 0.5–1.5 d → **2.5–5 d** |

### Phase M — Loop and review integrity (standalone; any time, required before C)

| # | Item | Content |
|---|---|---|
| 1 | Prerequisites | SDLE at `3cd3b19`. Independent of A and B |
| 2 | Improvement | (1) Only `code-review` records feed the progress digest (fixes R7). (2) The loop's review step refuses a review recorded without structured findings, so blocking findings actually count toward no-progress. (3) An agent-authored review cannot waive a blocking finding (F8) |
| 3 | Scope | `scripts/sdle.py`: `_blocking_finding_fingerprints` `:16216-16231` (type filter); `cmd_loop_step` review branch `:16636-16660` (*proposed* `loop_review_unstructured`; an empty list passes); `cmd_artifact_review` `:12082-12093` (*proposed* `review_waiver_requires_human`). Prompts: `modules/code-review.md:54`, `modules/design-review.md:57-60`, `phase-execution.md` loop `:218`. Tests: `tests/test_units_loop.py` helper `:48-50` passes an empty findings file, plus new tests for shadowing and unstructured refusal; `tests/test_units_artifact_review.py` (agent waiver refused, human waiver accepted). Docs: `docs/dry-runs/25-the-implementation-loop.md` + `verification-matrix.md`; an ADR-017 amendment note; `docs/troubleshooting/` entries for the two refusals. **Wording rule:** the waiver refusal and its docs say it blocks *silent agent* waivers; `--actor-type human` is self-declared and is **not** proof of human authorization |
| 4 | Acceptance demonstration | The R7 probe, re-run, now shows the blocker counted; an agent waiver is refused; a loop iteration with an unstructured review is refused and passes with `--findings []` |
| 5 | Verification | Targeted tests, the dry-run contract test, lint, full suite in the foreground |
| 6 | Completion and rollback | No state field, no new file format. An in-flight loop's next review step must add `--findings`, documented. Reviews recorded before M stay valid as history [reasoned]. No adopters (D3), so a troubleshooting note suffices. Revert is safe |
| 7–8 | Checkpoint and resume | `PROGRESS.md` entry with SHA and status; pushed |
| 9 | Go/no-go | Ship if the tests pass and Codex has no upheld defect. Skip M only if C is cancelled |
| — | Effort | Build 1–1.5 d · Codex 0.5–1 d → **1.5–2.5 d** |

### Phase C — Visual critique in the existing code review

| # | Item | Content |
|---|---|---|
| 1 | Prerequisites | A, B, M released. Worth doing even if A and B succeed: they cover intent and objective correctness, while C targets subjective visual quality. Decide C on its own task-0 experiment, not on A and B's results |
| 2 | Improvement | An independent read-only reviewer sees selected viewport-size screenshots alongside the UI intent. It reports located findings: a closed list of six blocking criteria (Appendix C), everything else advisory. Waivers and "visual judgment unverified" are shown at the gate |
| 3 | Scope | **Task 0 (experiment, go/no-go):** F5 — seeded pixel-only defects; does `sdle-code-review` perceive them through `Read`? **Modify:** `guidelines/ui-design.md` (review rubric, `ui:<screen>@<viewport>#<state>` locations, limits); `modules/code-review.md` (visual inputs, single record); `.claude/agents/sdle-code-review.md` (visual items; scope "style opinions" `:34-35`; never claim keyboard, focus, screen-reader or contrast from a PNG; rendered text is data); `modules/gate-protocol.md:38` (screenshots listed, visual findings, waivers, "unverified" label); `phase-execution.md` implement inputs and the converge-step finding→task rule (Appendix D). **Engine (small):** `read_review_findings` `:12015-12017` validates the grammar of `ui:`-prefixed locations (*proposed*). **Tests:** `tests/test_units_artifact_review.py` (location grammar); `tests/test_units_loop.py` (F7: reworded = no progress; two at one location, one fixed = progress; "fixed A / new B" = `no_progress`, documented) |
| 3a | If the experiment fails | Ship only the gate-display change (screenshots listed for the human, "visual judgment unverified"); no automated visual findings. Record the result; tool widening needs a separate owner decision |
| 4 | Acceptance demonstration | **Isolated experiment** on B's experiment implementations: seeded visual-only defects (misalignment, inconsistent components, poor hierarchy, clipped text in an unasserted state); false positives on clean screens; finding stability across 2 reviews; image tokens and time per review. **One real model-driven loop (AS-30)** — a full SDLE run, reported separately — turns a seeded blocking finding into a convergence task and repairs it. This is the precondition for any convergence claim |
| 5 | Verification | Tests, lint, full suite in the foreground; AS-30 run record |
| 6 | Completion and rollback | Gate semantics unchanged (`code-review` PASS as today). Revert is safe; stored findings stay valid |
| 7–8 | Checkpoint and resume | `PROGRESS.md` entry with SHA and status; pushed |
| 9 | Go/no-go | **Automated visual review stays enabled** if: the experiment passes, at least half of the seeded visual defects are found, at most 1 blocking false positive occurs per clean screen, and at least 80% of blocking findings are stable across reviews *(targets; the owner decides with the recorded numbers)*. Otherwise visual findings become advisory-only, or the review falls back to the 3a variant. **Convergence** is claimed only if AS-30 succeeds |
| — | Effort | Experiment 0.5 d · build 1–2 d · Codex 0.5–1 d · measurement incl. AS-30 1–3 d → **3–6.5 d** |

### Phase D — Harden and enforce proven evidence (opt-in)

| # | Item | Content |
|---|---|---|
| 1 | Prerequisites | B released; C recommended; **D1 and D6 decided** (D3 is decided: no adopters); B's go held on at least 2 pilot screens |
| 2 | Improvement | For repositories that opt in: a UI-relevant change cannot reach `gate_implement` with absent, stale or irrelevant UI evidence |
| 3 | Scope | `scripts/sdle.py`: `cmd_manifest_build` `:18914-19082` + argparse `:21181-21198` (*proposed* `--ui-map`, attachment hashing per F1/F2); `GOVERNANCE_POLICY_BUILTIN` `:4141-4256`, `GOVERNANCE_POLICY_OVERRIDABLE` `:4330-4343`, validation (*proposed* `ui_paths`, default `[]`, pinned ∪ live); `implementation_ready` `:16185-16208` (*proposed* `ui_evidence_precondition`, implementing F1 + F3). New `docs/architecture/ADR-018-ui-quality.md`; dry run `docs/dry-runs/26-ui-quality.md` + `verification-matrix.md`; troubleshooting entries |
| 3a | Tests | Extend `test_units_implementation_evidence.py`, `test_units_gate_policy.py`, `test_units_policy_midflight.py`, `test_units_loop.py`, `test_units_tree_digest.py`. Adversarial: unrelated PNG; passing backend case; failing case; altered or deleted PNG; plan screen missing from the map; plan drifted after approval; `ui_impact_conflict`; undeclared policy is inert; removing `ui_paths` from the live policy does not relax a pinned WorkItem |
| 4 | Acceptance demonstration | Dry run 26 plus the adversarial suite; one pilot WorkItem passes the gate with genuine evidence |
| 5 | Verification | Tests, lint, full suite in the foreground |
| 6 | Completion and rollback | Inert unless `ui_paths` is declared. **Rollback hazard [reasoned, verify in D]:** after a revert, a repository policy still containing `ui_paths` is refused `policy_malformed` (closed key set), so remove the key before reverting. Whether a *pinned* policy with an unknown key still reads after a revert is **unverified**. Extra evidence fields are tolerated by the evidence-shape check [verified: read, `:17036-17071` has no closed key set] |
| 7–8 | Checkpoint and resume | `PROGRESS.md` entry with SHA and status; pushed |
| 9 | Go/no-go | Enforce only if the adversarial suite passes and the owner accepts the retention contract (D1) |
| — | Effort | Build 3–5 d · Codex 0.5–1 d → **3.5–6 d** |

### Phase E — Optional refinements (each released separately, only on measured need)

| Item | Need shown by | Scope | Effort |
|---|---|---|---|
| E1 Snapshot-expectation guard | Pixel baselines adopted | Changed `*-snapshots/` ⇒ `test_expectation_change` in `cmd_loop_record` `:16761-16850` | 1–2 d |
| E2 Exit-code mapping | Pilot misclassifies environment failures | `run_tests` `:18477-18521` + evidence shape `:17036-17071` | 1–2 d |
| E3 Fingerprint category | Harmful collisions in C | Closed category vocabulary in the fingerprint | 1–2 d |
| E4 Windows | D5 promises Windows | Harness invocation; the engine's `npm` detection (`:18459`) | 1–3 d |
| E5 Preview experiment | Owner wants F4's benefit measured | With/without-preview arm on the demanding screen | 1–2 d |

Each E item follows the same nine-item contract and §5's review protocol.

### Effort summary (planning estimates, not measurements)

| Scope | Estimate |
|---|---|
| MVP: A + B | **5.5–10 d** |
| + M + C | **10–19 d** |
| + D | **13.5–25 d** |

Comparable to v2's 11–18 d plus the per-phase Codex reviews and measurement that v2 did not count. Isolated experiments cut owner gate time to one full SDLE run per measured phase (A, and C's AS-30 run). Experiments still cost tokens and rating time.

---

## 7. Pilot and measurement protocol

### 7.1 Two kinds of run — always reported separately

| Kind | What it is | Used for | Owner time |
|---|---|---|---|
| **Full SDLE run** | A real WorkItem in the pilot app's repository, with SDLE and Spec Kit installed, through `gate_implement`, with the owner approving every human-required gate. In `GREENFIELD` that is at least five: `gate_constitution`, `gate_architecture`, `gate_spec`, `gate_plan`, `gate_implement` (`sdle.py:4236-4238`; `SKILL.md:87`) | Proving lifecycle integration: exactly **one** in A (enhanced arm, demanding screen) and **one** in C (the AS-30 loop) | About 5 gate decisions per run |
| **Isolated experiment** | A fixed requirement document per screen. Spec Kit's `specify` → `plan` → `tasks` → `implement` commands are run directly in a scratch copy of the pilot app, with the arguments SDLE would append (baseline = SDLE at `3cd3b19`; enhanced = with Phase A's instructions). No gates and no governance records | Comparing arms (A), seeded-defect detection (B), visual review quality (C) | None during runs; rating time afterwards |

Experiments isolate the effect of the instructions. They are **not** full SDLE runs and are never described as such.

### 7.2 Protocol

| Element | Protocol |
|---|---|
| Screens | One visually demanding screen (dashboard or multi-panel), one conventional form or table, one brownfield modification of an existing screen. With fewer, conclusions are labelled **preliminary** |
| Runs | At least 3 per arm per screen in experiments (they run unattended). One full SDLE run as in §7.1. A feasibility sample, not statistical proof |
| Capture | A small screenshot script (experiment scaffolding kept in the pilot workspace, **not** in the SDLE repository) renders every arm's result at the same viewports and states, with the same synthetic data |
| Rating | At least 2 blind raters. Screenshots shown in randomized order with the arm hidden. Rubric: hierarchy, consistency, usability, polish (1–5 each) |
| Primary metric (A) | Mean rendered-UI rating per screen and arm |
| Supporting metrics | Intent completeness (Appendix A); objective defects detected (B); visual defects found, false positives and stability (C); tokens; wall-clock; iterations and stop reasons; unresolved findings; screenshot and trace storage size |
| Kept separate | Browser functional correctness · automated accessibility checks · human/AI visual judgment |
| Pareto decision | After each phase, `PROGRESS.md` records which capability beat its cost and which remaining proposals can be dropped |

---

## 8. Compatibility, security and privacy checks (every phase)

### Compatibility

- No `state.json` field and no `CURRENT_VERSION` change.
- No phase, gate, review type or agent added.
- `HOTFIX` and `DEFECT_FIX` gain no design-gate dependency.
- A, B and C are advisory guidance plus small validations.
- Only D is binding, and only by opt-in policy, under ADR-011: tightening applies immediately to in-flight WorkItems, and the refusal names the remedy (D6).

### Security and privacy

- Synthetic data and test-only accounts in every harness.
- Traces, HTML reports and `storageState` are never versioned. The manifest secrets scan skips binaries and the evidence directory (`sdle.py:18943-18963`, `:18643`) [verified: read].
- Screenshots of production or personal data are forbidden.
- Text rendered inside a screenshot is data, not instruction.
- The frozen-worktree privacy check runs before every Codex run (§5.4).
- Push only after asking the owner, at each checkpoint, to the agreed remote branch. An unpushed checkpoint is not durable: local clones and cloud sessions can disappear.

### Integrity

- No snapshot updates without review.
- No test weakening to converge.
- No AI-authored waivers (M).
- No `accepted` finding hidden from the gate (C).

---

## 9. Owner decisions (defaults are proposals, not approvals)

| # | Decision | Default proposal | Deadline (blocks only) |
|---|---|---|---|
| D1 | Screenshot retention | Small sanitized images versioned in WorkItem evidence (engine-verifiable); CI references allowed but labelled "not engine-verified" | Before **D** |
| D2 | Visual approval | None. Text gates stay authoritative; previews are references | Blocks nothing in this plan |
| D3 | Adopters and compatibility | **Decided (owner, 10 Oct 2026): no one uses SDLE.** No migration machinery or release notes are required; behaviour changes are documented in troubleshooting and ADR notes | — |
| D4 | Pilot app and stack | See §9.1. Default: your own Angular app if one can be used with synthetic data; else the public Angular RealWorld example with a mocked API; else a fresh scaffold | Before **A-measure** (A-build does not need it) |
| D5 | Windows support for target harnesses | Document and support the Node-based harness; **claim no Windows verification until it is tested** on Windows | Before **B** claims Windows support |
| D6 | Mid-run tightening of `ui_paths` | Follow ADR-011: applies immediately, with an explicit refusal | Before **D** |
| T | Go/no-go thresholds (rows 9 of A, B, C) | **Targets, not automatic rules.** Claude reports the numbers; the owner decides, and the decision is recorded | At each measured phase |

### 9.1 D4 explained — what the pilot app is and what it needs

**What it is for.** Phase A only matters if SDLE-generated screens *look and work better*, and that has to be shown on a real frontend. The pilot app is the project SDLE is installed into and pointed at: SDLE and Spec Kit are added to it, and SDLE builds new screens in it. It is **not** the SDLE repository, and nothing from it goes into the SDLE repository.

**What it must have:**

1. A web frontend — **Angular** preferred, since that is your stack — that runs locally (`npm start`, `ng serve` or similar) on the machine where you run Claude Code.
2. Room for three test screens:
   - a **new, visually demanding** screen (e.g. a dashboard with cards, a chart and a table);
   - a **conventional** form or table;
   - a **modification of an existing** screen (brownfield).
3. **Synthetic data only.** No client data and no real users, because screenshots are taken, rated and shown to reviewers.
4. A working browser runner. Playwright with Chromium is the example; it is needed for screenshot capture in A-measure and for Phase B.
5. Permission to change it freely, in a scratch copy or branch, because experiments run several times per arm.

**Options, best first:**

| Option | Pros | Cons |
|---|---|---|
| **(a) An existing Angular app of yours** | Most realistic; brownfield work is natural | Must run locally with synthetic data, and contain no confidential code you would not want an AI to read |
| **(b) The public Angular RealWorld example** (`github.com/gothinkster/angular-realworld-example-app`) [verified: exists; last commit May 2026; Angular 21; ships a Playwright config] | Public, realistic CRUD app (authentication, lists, an editor, profiles); no privacy concerns | Uses **Bun**, and by default calls the **public live API** `api.realworld.show`, so its data is not under our control. Deterministic tests need a mocked or local backend; whether its `realworld` submodule provides one is **unverified** |
| **(c) A fresh scaffold** (`ng new` plus a component library) | Fully controlled | Least realistic; the brownfield screen must be built first; conclusions are labelled as toy-app results |

**When you start A-measure, tell Claude Code:**

- the option chosen and the repository path;
- the start and test commands;
- the Node/Bun/Angular versions;
- who the two blind raters are.

---

## 10. Pause and resume runbook

### At every checkpoint

`docs/enhancements/ui-quality/PROGRESS.md` records:

- the **commit SHA** of the checkpoint, and the branch it was pushed to;
- the **status**: `built, unmeasured` · `complete` · `awaiting owner` (any open Owner-attention row means `awaiting owner`);
- capabilities completed;
- the test command, counts and duration;
- the measured effect, kept separate for full SDLE runs and isolated experiments;
- limitations;
- the Owner-attention table and the open decisions;
- the **prerequisites of the next phase**, and whether stopping indefinitely is safe.

Commit it, ask the owner, and push. No uncommitted transient files remain; pilot artifacts live outside the SDLE repository. A local tag may be added for convenience, but **the SHA in `PROGRESS.md` is the authority**.

### To inspect and resume

```sh
git fetch origin
git status --short                                   # must be clean; if not, stop and ask the owner
sed -n '1,120p' docs/enhancements/ui-quality/PROGRESS.md   # status, recorded SHA, Owner attention, next prerequisites
SHA=<the checkpoint SHA recorded in PROGRESS.md>
git cat-file -e "$SHA^{commit}" && echo present      # the checkpoint commit still exists
git merge-base --is-ancestor "$SHA" HEAD && echo ancestor   # current HEAD still builds on it
git diff --stat "$SHA"..HEAD                         # everything that changed since the checkpoint
python scripts/sdle.py lint-skill
python scripts/sdle.py validate
python -m pytest -q -p no:cacheprovider              # foreground; ~10 min at 3cd3b19
```

Then:

1. **If the SHA is missing or not an ancestor** (history rewritten or a different branch): stop and ask the owner. Never assume the original branch is unchanged.
2. Resolve or confirm every open Owner-attention row.
3. Re-check the next phase's prerequisites and go/no-go against the recorded measurements.
4. Start **only** the chosen phase at §5.1, step 1. That step re-verifies its files against the current HEAD and re-runs its Codex plan review.

**Never** edit `workitems/*/.sdle/`, `.sdle/architecture/` or approval ledgers by hand. **Never** resume a half-finished phase from memory: an interrupted phase's uncommitted work is inspected, then either completed through the phase process or discarded with owner consent.

---

## 11. Cut list (removed from v2, and why it matters less than the MVP)

| Removed or changed from v2 | Why |
|---|---|
| v2 Phase 0 as a gate before all UI work | Postponed value. It is now standalone slice M, needed only before C |
| v2's separate pilot phase | Shipped nothing. Measurement is now inside A–C |
| v2 §8.2 trigger (paths + JUnit + any PNG) | False evidence passes it. Replaced by D's evidence map (F1) |
| v2 D1 default (ignored + hash) | The hash outlives the file. Replaced by a retention contract (F2) |
| v2 ARIA/DOM fallback called visual review | Mislabel (F5) |
| v2 token totals and the 57% figure | Unverifiable here; measured in C instead |
| v2 Phase 4 SHOULDs as one block | Now separate E items, each needing shown value |
| Kept cut from v2 | Separate UI artifact, UI agent, new review type, applicability taxonomy, versioned contracts, mandatory previews |

---

## 12. Uncertainty register — open items for the owner now

| # | Item | Status | Resolved in |
|---|---|---|---|
| U1 | Can the read-only subagent perceive PNG content? | Unverified | C, task 0 |
| U2 | Do Spec Kit `specify`/`plan` keep the UI content SDLE asks for? | Unverified | A |
| U3 | Does a real model-driven loop repair a review finding? (AS-30 never run) | Unverified | C |
| U4 | Windows: shell-less spawn of `node` vs `npm`/`npx` shims | Unverified | D5 / E4 |
| U5 | Reverting D with `ui_paths` still in a policy → `policy_malformed` | Reasoned | D |
| U6 | A pinned policy with an unknown key after a revert | Unverified | D |
| U7 | Codex availability and version on resume (last: 0.160.1) | Environment | Each phase |
| U8 | Git treats versioned PNGs as binary under `* text=auto eol=lf` | Reasoned | D |
| U9 | Owner time: one full SDLE run per measured phase (about 5 gate decisions each) plus rating | Estimated, not measured | A, C |
| U10 | Preview benefit | Hypothesized | E5 |
| U11 | Go/no-go thresholds | Targets, not rules (§9, row T) | Each measured phase |
| U12 | Pilot app not chosen; the RealWorld fallback needs a local or mocked API (unverified) | Open (D4) | Before A-measure |
| U13 | Node, Bun, Angular, Playwright and Codex versions on the owner's machine | Unverified | Phase plan step 1 |

**Disagreements with the external review** (the owner may overrule):

- **F3:** the conflict remedy is re-approving the plan, not a new review decision type.
- **F4:** measuring the preview benefit is deferred to E5.
- **F7:** a category in the fingerprint is deferred; the collision errs safe (R6).
- **F8:** moved earlier, into M.
- **M vs A order:** A first is recommended for user-visible value; M first is equally safe.

---

## 13. Final challenge answers

1. **Stop after A?** SDLE generates complete UI intent and test mapping, reuses components, carries brownfield conventions forward, and uses previews where uncertainty is high. Phase A must **show a better rendered UI** on the demanding screen; until A-measure that is [hypothesized], and a longer specification alone is not counted as success. Nothing runtime-dependent is left behind.
2. **Stop after B?** Yes. Projects run real browser journeys and layout checks through the unchanged manifest, and failures block the gate through `tests_not_passed`. No C or D needed.
3. **Stop after C?** Yes, honestly: findings are located, reviewer-attributed, limited to what a PNG can show, and waivers are visible. Screenshot integrity is explicitly labelled as not enforced.
4. **D never built?** Everything earlier is prompt, documentation, tests and three small validations, all within existing mechanisms. Valid and maintainable.
5. **The three changes with the greatest expected gain in actual UI output:**
   1. UI scenarios and states in the spec, plus a screen and reuse plan (A).
   2. Model-written browser checks for journeys, states and layout invariants that block the gate (B).
   3. Independent critique of real screenshots against that intent (C).
6. **Necessary versus overengineering:**
   - Already in place and necessary: tree-bound evidence and `tests_not_passed`.
   - Cheap and necessary: no silent AI waivers (M), and the review-type filter (M).
   - Necessary only to claim *enforcement*: the evidence map, hashing and retention (D).
   - Overengineering until shown otherwise: a fingerprint category, an engine exit-code mapping, a snapshot guard without pixel baselines, and any classification engine.
7. **A preparation-only phase?** None. v2's Phase 0 and pilot phase were restructured: M fixes real defects, and measurement sits inside A–C.

---

## 14. Next action

1. Run **Phase A-build** in Claude Code CLI on your machine with the kickoff prompt in Appendix E. It ends at a pushed checkpoint with status `built, unmeasured`, plus the Owner-attention table.
2. Choose the pilot app (D4, §9.1).
3. Run **A-measure**. Then decide go/no-go for B with the recorded numbers.

M can be run at any time before C by adapting Appendix E: M changes `scripts/sdle.py`, so the "no engine change" rule is replaced by M's scope (§6, Phase M, row 3). Step 1's record-directory setup is skipped if A already did it.

---

## 15. Execution setup — Claude Code CLI on the owner's machine

Check these once before Phase A-build. Every version is recorded in the phase plan (U13).

| Need | Check | Needed for |
|---|---|---|
| SDLE clone on the agreed branch (default `enh/requirements-package-loop`, as originally specified; a branch cut from it is equally fine — record which) | `git rev-parse HEAD` (expected `3cd3b19` or a descendant) | All |
| Python 3.11+ and the pinned test dependencies | `pip install -r requirements-dev.txt`; `python -m pytest --version` | All |
| Codex CLI, logged in (last used: 0.160.1) | `codex --version` | Every review round (§5) |
| A remote you can push checkpoints to | `git remote -v` | Every checkpoint |
| Spec Kit v1.0.6 via `uv` (the install command in `docs/GETTING-STARTED.md`) | `uvx --version` | A-measure, C's full runs |
| Node / Bun / Angular as the pilot app requires; Playwright Chromium | `node --version`; `npx playwright --version` | A-measure capture, B |
| The pilot app (D4) | It starts locally with synthetic data | A-measure, B, C |

---

## Appendix A — UI intent completeness rubric (Phase A measurement)

Scored per UI WorkItem, one point each, by a rater who does not know the arm.

1. Every changed screen has at least one user journey written as Given/When/Then acceptance scenarios in `spec.md`.
2. The required states that apply (empty, loading, error, validation, success, disabled) are stated.
3. Supported device classes are stated in user terms.
4. Accessibility expectations are stated as functional requirements.
5. `plan.md` has a screen inventory with stable `UI-…` ids, mapped to stories or requirement ids.
6. `plan.md` names the components and tokens it reuses, justifies each new component, and (for brownfield work) names the affected existing screens.
7. Every UI scenario has a test task naming the screen, states, viewports and criterion id.

## Appendix B — Harness contract (Phase B; project-level, not an SDLE dependency)

| # | Rule | Why |
|---|---|---|
| H1 | One command (e.g. `node <harness script>`) runs the unit and browser suites, passed as `manifest build --test-command` | The engine runs one command (`sdle.py:18477-18490`) |
| H2 | One merged JUnit report, written to the WorkItem evidence directory or an ignored path, passed as `--junit` | One report per build, hashed and parsed (`sdle.py:18978-18987`) |
| H3 | Test case names cite the screen id and the criterion id | Mapping, review locations, Phase D relevance check |
| H4 | An environment preflight (browsers present, app server up, port free) exits **78** without running tests. **Orchestrator convention:** on `tests.exit_code == 78`, record `loop record --classification environment_blocker`. The engine records it as `FAILED` (R3) | Otherwise an environment failure burns iterations as a "defect" |
| H5 | No conditional `skip`/`fixme` on tests covering a UI scenario; scope browsers through config projects | A skip fakes a pass, or blocks a package gate (`sdle.py:15746`) |
| H6 | Screenshots, traces, reports and auth state go to ignored paths. Only selected screenshots are attached. Traces, HTML reports and `storageState` are never versioned | Cookies and tokens; the secrets scan skips binaries and the evidence directory |
| H7 | Test, report and build output folders are in `.gitignore` | Otherwise `invalid_changed_during_run` (`sdle.py:18817-18819`) |
| H8 | The same full command runs in every loop iteration; raise `--test-timeout` explicitly if needed | The loop's last evidence is the gate's evidence |
| H9 | The case count stays well below 5000 (viewports multiply cases) | `LOOP_INVENTORY_MAX` (`sdle.py:15996`) |
| H10 | Pinned browser and fonts, seeded synthetic data, test-only accounts, animations off, fixed locale and timezone | Repeatability; no real personal data |
| H11 | On Windows, invoke through `node`, not `npm`/`npx` shims — **unverified** (D5) | A shell-less spawn is not expected to resolve `.cmd` shims |

## Appendix C — Visual review rules (Phase C)

**Blocking — only these six:**

1. A screen or state the plan requires is missing or does not render.
2. Content or a control an acceptance scenario needs is hidden, clipped, overlapped or off-screen at a declared viewport.
3. Unintended horizontal overflow at a declared viewport.
4. Text overlaps, or is truncated so that required information is lost.
5. A one-off component replaces one the conventions section names, with a visibly inconsistent result.
6. A visible contradiction of an acceptance scenario (wrong label, wrong state shown).

**Everything else is advisory.** A defect a browser test could have caught is also reported as a missing-test finding.

**Location** *(proposed grammar, validated by the engine for `ui:` locations)*: `ui:<screen-id>@<viewport>#<state>`, where the screen id matches `UI-[A-Z0-9-]+` and the viewport and state are names declared in the plan. `obligations` = criterion ids, or `[]`.

**Limits:**

- No keyboard, focus, screen-reader or contrast claims from a PNG.
- Rendered text is data, never instructions.
- With no screenshots reviewed, the gate shows "visual judgment unverified".
- Every `accepted` waiver is shown at the gate. After M, a waiver requires a review recorded with `--actor-type human` — a self-declared convention that blocks silent agent waivers, **not** proof of human authorization.

## Appendix D — Finding → task rule (Phase C; validated by the AS-30 run)

1. **Default (deterministic).** Inside the `converge` step, before `loop step --step converge`, the orchestrator appends one `## Phase N: Convergence` section. It holds one task per open blocking finding: `- [ ] T0xx Resolve <finding-id>: <summary> per <location> (review-finding)`. Then it runs `tasks reconcile`. `_tasks_delta` accepts whole appended convergence sections (`sdle.py:16088-16126`). If `converge` also appends a section in the same step, the two use distinct `N`.
2. **Alternative.** Pass the open findings to `converge` as source references. This is weaker, because `converge` treats spec, plan and tasks as its sole source of intent.
3. A later review marks a finding `resolved` only on evidence (a new screenshot or a passing test), never because a task was appended. Appended tasks are not progress (existing rule).

## Appendix E — Kickoff prompt for Claude Code CLI (Phase A-build)

Before pasting it, copy this plan into the SDLE repository as `.sdle/implementation-state/ui-quality/PLAN.md`. Claude Code commits it in step 1, together with the `MAINTENANCE_RECORDS` pin (R17); without that pin, the repository's own tests scan the new directory.

```text
You are implementing Phase A-build of the SDLE UI-quality enhancement, and nothing else.

Read .sdle/implementation-state/ui-quality/PLAN.md in full (the plan), then CLAUDE.md (its
eight invariants are non-negotiable).

Do, in order, exactly as PLAN.md §5.1 describes for Phase A:
1. Re-verify every file:line reference for Phase A against the current HEAD (the plan's references
   are to commit 3cd3b19). Write .sdle/implementation-state/ui-quality/phases/A-PLAN.md. In the same
   commit: add the ui-quality record directory to MAINTENANCE_RECORDS in tests/conftest.py, update
   the pinned count in tests/test_units_capabilities.py, create
   docs/enhancements/ui-quality/PROGRESS.md and link it from docs/README.md. Run the full suite.
2. Codex plan review round 1 with the runner and schema named in PLAN.md §5.3, read-only, on a
   frozen worktree, after the privacy check in §5.4. This first round also covers PLAN.md §2–§5 and
   §8–§10. Record every finding and your disposition in .sdle/implementation-state/ui-quality/LEDGER.md.
   Run round 2 only under the §5.1 trigger. Never run a third round.
3. Implement Phase A (PLAN.md §6, Phase A, rows 3–3b): prompt, guideline, documentation and test-pin
   changes only. Do not change scripts/sdle.py or .claude/hooks/.
4. Run python scripts/sdle.py lint-skill and the FULL test suite in the foreground; record the
   command and the counts.
5. Codex implementation review rounds 1 (and 2 only under the trigger) on the phase diff, with the
   test evidence. Fix accepted findings, re-run the tests, record the dispositions.
6. Checkpoint per PLAN.md §10: PROGRESS.md gets the SHA, status "built, unmeasured" (or
   "awaiting owner" if any Owner-attention row is open), the test evidence, open decisions and the
   prerequisites for A-measure. Commit. Ask me before pushing.
7. STOP. Report: files changed; test command and counts; every Codex run with its result and
   dispositions; every Owner-attention row; the checkpoint SHA.

Rules:
- If a Codex run fails twice (BLOCKED), record it and stop for me. Do not substitute another
  reviewer without my consent.
- Never edit workitems/*/.sdle/, approval ledgers or .sdle/architecture/ by hand. Never weaken,
  delete or skip a test to get green.
- Anything you cannot resolve, or that needs my decision, goes in the Owner-attention table and in
  your final report. Never bury it.
- Do not start A-measure (it needs the pilot app, decision D4) or any other phase.
```

---

## Sources

- Spec Kit v1.0.6 [specify command](https://raw.githubusercontent.com/github/spec-kit/v1.0.6/templates/commands/specify.md) · [spec template](https://raw.githubusercontent.com/github/spec-kit/v1.0.6/templates/spec-template.md) · [plan template](https://raw.githubusercontent.com/github/spec-kit/v1.0.6/templates/plan-template.md)
- [Playwright — visual comparisons](https://playwright.dev/docs/test-snapshots) · [Playwright — ARIA snapshots](https://playwright.dev/docs/aria-snapshots)

---

## Amendments from the A-build plan review, round 1 (10 Oct 2026)

v2.2's text above is left as written; where an amendment conflicts with it, **the amendment governs**. Source: Codex run `20261010T125932-stage2-codex-A-plan-r1` on commit `85d6d4b`; dispositions in `LEDGER.md`.

| Id | Amends | Rule |
|---|---|---|
| PR-R1-002 | §7.1, §6 A row 4 | An isolated experiment as defined in §7.1 reproduces only the **appended arguments** of the Spec Kit commands. It does not load `CAPABILITY_MAP` guidelines and does not run the SDLE-native `design_generation` phase, whose changes Phase A also makes. So the experiment measures the effect of the appended UI instructions, not of "SDLE + A". A-measure must therefore either (a) use a harness that loads each arm's actual capability files and produces `app-design.md` before `implement`, or (b) state the narrower claim and evaluate the native-design changes separately (the one full SDLE run covers them, reported separately). The owner chooses at A-measure; until then no visual claim is made for the guideline or design-section changes |
| PR-R1-003 | §7.2, §6 A row 9 | Before any A-measure run, a manifest is written and committed: model and settings, the fresh-copy reset commit per run, the **randomised** run order, what "paired run" means (run *k* of each arm, same screen), every attempted run counted, a declared outcome for a run that does not render (rated 1 on every criterion, and listed), and the rating aggregation (per-rater mean, then mean of raters, rater disagreement reported) |
| PR-R1-004 | §6 A row 6, §8 | The claim "no drift is caused" is true only for **gate-artifact drift**. The implementation evidence's tree digest covers every tracked, non-ignored file outside the engine's exclusion list, which does not exclude `.claude/`. A target project that tracks its installed skill files and updates them **after** `manifest build` and before the gate sees `test_evidence_stale` and must rebuild the manifest and tests. Guidance: update the installed SDLE files between WorkItems, or before implementation evidence is built |
| PR-R1-005 | §5.2 | The coverage-gap rule applies to **every** round, not only round 2. A runner `PASS` means schema-valid output, not complete coverage or approval. A round whose `areas_not_reviewed` names an area the phase depends on is either covered by the remaining round or recorded in the Owner-attention table |
| PR-R1-006 | §5.1 step 8, §10 | A file cannot contain the SHA of the commit that contains it. The checkpoint is two commits: the reviewed implementation commit, then a record commit that updates `PROGRESS.md`. **`PROGRESS.md` records the implementation commit's SHA, and that SHA is the checkpoint**; the record commit is its descendant, and the resume runbook's ancestor test is run against the implementation SHA. The push is of both |

### Round 2 (Codex run `20261010T130330-stage2-codex-A-plan-r2`, reviewed `76dc220`)

All six round-1 fixes verified; one new finding, accepted.

| Id | Amends | Rule |
|---|---|---|
| PR-R2-001 | §7.2, and PR-R1-003's manifest | The input manifest also declares a **clarification policy** and a **run deadline**, identical for both arms: a clarification request either ends the attempt (counted as an attempted run with the declared failure outcome) or receives a predetermined answer written in the manifest. Every intervention is recorded. "Unattended" means no improvised human input, not that Spec Kit cannot ask |
