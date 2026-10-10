# Implementation review, round 1 — SDLE UI-quality enhancement, Phase A

You are an independent, adversarial reviewer in a **read-only sandbox**: do not edit, create or delete files. Read `CLAUDE.md` first: its eight invariants are non-negotiable. Report the checked-out commit as `reviewed_commit`.

Review the **diff** `git diff a1feffa..HEAD` (Phase A's implementation). The contract is `.sdle/implementation-state/ui-quality/PLAN.md` §6 Phase A (rows 2–3b), as amended by its "Amendments" sections, and `phases/A-PLAN.md`. Phase A is prompt, guideline, documentation and test-pin changes only: any change to `scripts/sdle.py` or `.claude/hooks/` is a defect.

## Test evidence (already run by the author, on this diff)
- `python scripts/sdle.py lint-skill`: ok, no failed checks.
- Full suite in 18 shards (`.sdle/implementation-state/requirements-package-loop/shards-final.json`), 4215 collected: every shard passed except one failure in `tests/test_units_install_contract.py::test_the_install_directories_hold_exactly_the_expected_files`, which counts **git-tracked** files and failed only because the new guideline was untracked at the time; after staging, that file's 36 tests pass. Records: `.sdle/implementation-state/ui-quality/runs/a-s4-full-*.json`.

## Attack list
1. **Invariant 7 / restatement.** Does the new guideline or any phase block restate an engine fact, constant, ordinal or threshold? Are "3–5 states / 2 viewports" and the `UI impact:` / `UI-<AREA>-<n>` conventions presented as heuristics owned by the guideline, with no second copy that can drift?
2. **Mechanical fit.** `CAPABILITY_MAP` rows, orphan/cross-reference rules, install-contract and guide counts, `CLAUDE.md`, ADR-014 note, Reference Guide: anything stale or missing (search `README.md`, `docs/`, `tests/`, `.claude/`)?
3. **Behaviour of the prompt changes.** For each edited `phase-execution.md` block: is the conditional ("user-visible work") unambiguous; can the appended text leak a `speckit-*` name (invariant 3) or change what a gate artifact must contain; does the design block's sixth section conflict with the "all of the following sections" structure or with how `design-review` assesses it; is the argument-string quoting consistent with the neighbouring appended-args sentences?
4. **Non-UI work unchanged.** Is there any path by which a backend-only WorkItem now gets extra obligations, or by which HOTFIX / DEFECT_FIX flows are made to depend on a design gate?
5. **Prompt-injection surface.** New instructions that read repository content (existing conventions, previews): is rendered/previewed text treated as data?
6. **Test pins.** Were any test weakened, deleted or skipped? Is each changed pin exactly what the product now is?
7. **Defects in the fixes' own documentation** (A-PLAN, LEDGER, PROGRESS, PLAN amendments) that would mislead the next phase.

## Output
Return **only** a JSON object matching the supplied schema. Ids `IR-R1-001`... `defect/<area>` or `improvement/<area>`, repository evidence quoted, `areas_not_reviewed` specific, no padding, no wording nits.
