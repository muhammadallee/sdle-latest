# Plan review, round 1 — SDLE UI-quality enhancement, Phase A (plus the cross-cutting plan)

You are an independent, adversarial reviewer. You have not seen the conversation that produced this plan; do not assume any decision in it is correct. You are in a **read-only sandbox**: do not edit, create or delete files. Reading files and read-only commands are fine.

The repository is SDLE (Spec Driven Lifecycle Engine): a deterministic gated SDLC orchestrator for Claude Code. `scripts/sdle.py` is the single-file, standard-library-only engine; it refuses rather than warns. Read `CLAUDE.md` first: its eight invariants must survive any change. Report the checked-out commit as `reviewed_commit`.

## What you are reviewing
A **plan**, not code. Under `.sdle/implementation-state/ui-quality/`:
- `PLAN.md` — the enhancement plan v2.2. **Review §2–§5 and §8–§10** (evidence, F1–F8 dispositions, phases and dependencies, review protocol, compatibility/security/privacy, owner decisions, pause/resume), and §6 **Phase A only**. Phases B, C, D, E and M are out of scope except where Phase A's design forecloses them.
- `phases/A-PLAN.md` — the Phase A phase plan with the reference re-verification and deliverables. Phase A is prompt, guideline, documentation and test-pin changes only: no change to `scripts/sdle.py` or `.claude/hooks/`.

Read the **current source**; do not trust the plan's description of it.

## Attack list
1. **References.** Do the file:line and function references in PLAN.md §2.1/§6 Phase A and A-PLAN.md §1 hold at this commit? Are any surfaces that name the guideline set, the capability map, the maintenance-record count or a `guidelines/` count missing from A-PLAN §1? Search `tests/`, `docs/`, `README.md`, `CLAUDE.md`, `.claude/`, `scripts/`.
2. **Mechanical fit.** Will adding `guidelines/ui-design.md` and mapping it in `CAPABILITY_MAP` rows for `spec_draft`, `plan_draft`, `tasks_draft`, `design_generation`, `implement` pass `lint-skill` (orphan, cross-reference, restatement search per invariant 7, prompt-content checks)? What else does the linter or a test pin that a seventh guideline would break?
3. **Invariants.** Does anything planned violate CLAUDE.md invariants 1–8, in particular 7 (one source of truth: the plan proposes sizing heuristics and a plan-section marker `UI impact:`) and 3 (SpecKit opacity)?
4. **Spec Kit interaction (U2).** The plan asks the model to append UI instructions to the arguments of the Spec Kit commands. Is that mechanism sound given how `phase-execution.md` builds `args` and how the untrusted-content scan treats guidance? Could appended text change gate-artifact validation, size floors, drift or fingerprints?
5. **Mid-flight and compatibility.** Is the claim "prompt-only, in-flight WorkItems unaffected, no drift" true? Check what `drift`/fingerprints cover and whether prompt files are part of any pinned hash.
6. **Measurement design (§7, §6 Phase A rows 4 and 9).** Is the experiment design able to support the stated claim? Name confounds and ways the go/no-go can pass vacuously.
7. **Process rules (§5, §10).** Gaps in the review protocol, the unresolved-items rule, the checkpoint/resume runbook (for example commands that do not work on a clean clone, or a status that can be misreported).
8. **Anything in PLAN.md §2 that is false against the current source.**

## Output
Return **only** a JSON object matching the supplied schema.
- `reviewed_commit`: the checked-out commit.
- `coverage.areas_reviewed` / `coverage.areas_not_reviewed`: be specific. An empty `findings` array with non-empty `areas_not_reviewed` is rejected as incomplete.
- Each finding: unique `id` like `PR-R1-001`; `severity` (`critical|high|medium|low`); `category` = `defect/<area>` for something wrong that must be corrected, or `improvement/<area>` for something better but not wrong, never mixed; `path` and `line` (`0` if none); `claim`; `evidence` (quote the file and line); `evidence_type` `executed` or `static`; a concrete `suggested_fix`; `ac_ids` listing plan sections touched; `confidence`.
- Do not pad. A finding without repository evidence is not a finding. Do not report wording. Do not rewrite the plan.
