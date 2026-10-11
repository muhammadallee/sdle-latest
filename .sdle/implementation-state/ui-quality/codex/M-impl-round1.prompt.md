# Implementation review, round 1 — SDLE UI-quality enhancement, Phase M (loop and review integrity)

You are an independent, adversarial reviewer in a **read-only sandbox**: do not edit, create or delete files. Read `CLAUDE.md` first (eight invariants: the engine refuses rather than warns; single writer; refuse before the first write; one source of truth per fact). Report the checked-out commit as `reviewed_commit`.

Review the diff for Phase M: `git diff 7571ef6..HEAD -- scripts tests docs .claude` (the engine, tests, docs and prompts). The contract is `.sdle/implementation-state/ui-quality/phases/M-PLAN.md` including its §7 design amendments (from plan review round 1); PLAN.md §3 (F7, F8) and §6 Phase M. Plan review round 2 was recorded BLOCKED with zero findings (OA-9, accepted by the owner).

## Test evidence (author-run)
- `python scripts/sdle.py lint-skill`: ok, no failed checks.
- Full suite in 18 shards: all passed (`.sdle/implementation-state/ui-quality/runs/m-full-*.json`).
- New tests: `test_m1_*`, `test_m2_*` in `tests/test_units_loop.py`; `test_m3_*` in `tests/test_units_artifact_review.py` (16 passed, `m-targeted2.json`).

## Attack list
1. **M1 (`_blocking_finding_fingerprints`).** Is it correct for: no code review; several code reviews for one path; a code review for a stale sha; a review recorded without `--findings` (summary absent); evidence present with findings but ledger summary absent; counts that match vs differ? Does `IntegrityError` propagate cleanly through both callers (`_loop_progress` in `loop record`, and `loop show`), before any write? Could it now refuse a currently valid state (a legitimately recorded review)?
2. **M2.** The refusal at `loop step --step review` and at `loop record`: is "no `findings` summary" exactly right, and is the empty list structured? Is the refusal ahead of every write? Is the `loop stop`/`loop begin` recovery real (read those commands)? Anything a currently valid loop run would now hit?
3. **M3.** Is the check ahead of `reserve_evidence`, the ledger write and the audit append? Does it apply to every review type and both results and every non-human actor type? Is there another door through which a disposition `accepted` on a blocking finding reaches the record (search `artifact review`, `gate approve`, `drift`, `loop`, any other writer of review records)? Is the message honest about the self-declaration limit?
4. **Tests.** Non-vacuity: would each new test fail if its change were reverted? Anything platform-fragile? Was any existing test weakened (the loop helper now passes `--findings`: is that justified and sufficient)?
5. **Docs and prompts.** Troubleshooting, dry run 25 and the matrix, ADR-017 amendment, `code-review.md`, `design-review.md`, `phase-execution.md`: any claim that the engine does not do, any restated engine constant (invariant 7), any claim that the waiver rule proves authorization?
6. **Other surfaces** (the repository's defect-fix rule): list every code path that reads review findings or dispositions and say whether the change is complete across them.

## Output
Return **only** a JSON object matching the supplied schema. Ids `MI-R1-001`... `defect/<area>` or `improvement/<area>`, repository evidence quoted, `areas_not_reviewed` specific, no padding, no wording nits.
