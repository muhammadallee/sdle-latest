# Phase M — loop and review integrity: phase plan

**Base:** `4d7d1ea` (branch `enh/requirements-package-loop`). **Contract:** PLAN.md §6 Phase M rows 1–9 and F7/F8 of §3.
**Engine:** `scripts/sdle.py` changes in three places. Hooks unchanged. No state field, no new file format.

## 1. Defects and the three changes

| # | Defect (executed in PLAN R7, R8) | Change |
|---|---|---|
| M1 | `_blocking_finding_fingerprints` takes the newest review record **of that path of any type**: a later `content-review` or `security-review` of the manifest hides an open code-review blocker from the progress digest | filter on `reviewType == "code-review"` |
| M2 | `loop step --step review` accepts a code review recorded without `--findings`; its blocking findings then never reach the fingerprint, so a loop can report progress that the review did not support | refuse `loop_review_unstructured` when the matching review has no structured findings. An **empty list** is structured and passes |
| M3 | `artifact review` lets an `agent`-actor review mark a blocking finding `accepted` and record `PASS`: an AI can silently waive its own blocker | refuse `review_waiver_requires_human` when `--actor-type agent` and a finding is `severity: blocking, disposition: accepted` |

**Wording rule for M3** (PLAN F8): the actor type is **self-declared**. The refusal, its troubleshooting entry and the ADR note say that this stops *silent agent* waivers by default and that `--actor-type human` is a convention, **not** proof of human authorization (ADR-007 §3).

## 2. References verified at `4d7d1ea`

| Reference | Found |
|---|---|
| `_blocking_finding_fingerprints` | `sdle.py:16216-16231`; filter is `r.get("path") == key` only |
| `cmd_loop_step` review branch | `:16636-16660`; records matched on `path`, `reviewType == "code-review"` and sha; `detail["findings"] = review.get("findings")` |
| review record shape | `cmd_artifact_review` `:12029-12155`; `record["findings"]` set only `if findings is not None`, as `{total, blocking, open}` |
| findings reader and vocabulary | `read_review_findings` `:11974`; `REVIEW_FINDING_SEVERITIES`, `REVIEW_FINDING_DISPOSITIONS` |
| actor types | `REVIEW_ACTOR_TYPES = ("human","agent","tool","test","system")` `:11708` |
| existing refusal for open blockers | `review_findings_open` at the PASS check in `cmd_artifact_review` |
| test review helper | `tests/test_units_loop.py` `code_review()` calls `record_review(..., actor="agent")` with no `--findings` |
| no test uses an `accepted` blocking finding | repository-wide search of `tests/` for the `accepted` disposition on a finding: none |

## 3. Scope

**Engine:** the three changes. **Prompts:** `modules/code-review.md` (findings are required inside a loop; a waiver is recorded by a human review), `modules/design-review.md` and the loop paragraph of `phase-execution.md`. **Tests:** `tests/test_units_loop.py` helper passes an empty findings file; new tests for shadowing, unstructured refusal, an empty list passing, and the waiver refusal (agent refused, human accepted, other actor types per the rule); the refusal-code pin tests that enumerate engine reasons. **Docs:** `docs/dry-runs/25-the-implementation-loop.md` and `verification-matrix.md`, an ADR-017 amendment note, and two entries in `docs/troubleshooting/README.md`.

## 4. Open design questions for the review

1. Which actor types does M3 refuse? PLAN says `agent`. `tool`, `test` and `system` are non-human too. Refusing only `agent` matches the plan and the threat (an AI waiving its own blocker); refusing every non-`human` actor is stricter but would break `test`/`tool` reviews that never mark `accepted` today. State the choice and its consequence.
2. Is a waiver visible anywhere afterwards? The review record stores only counts. PLAN C shows waivers at the gate; M need not, but the record should allow it.
3. M2's check reads the review record's `findings` summary, which exists exactly when `--findings` was given. Confirm an empty `[]` file produces the summary with `total: 0`.

## 5. Acceptance

The R7 probe re-run shows the blocker counted after a later non-code-review record; an agent waiver is refused and a human waiver recorded; a loop iteration with an unstructured review is refused and passes with `--findings` holding `[]`. Targeted tests, `lint-skill`, full suite (sharded), Codex plan and implementation reviews.

## 6. Rollback

`git revert` of the phase range. An in-flight loop's next review step must add `--findings` (documented in troubleshooting). Reviews recorded earlier remain valid as history.

## 7. Review round 1 (Codex `MP-R1-001..003`, run `20261011T182531-stage2-codex-M-plan-r1`, reviewed `7571ef6`): all accepted

Where this section conflicts with §1–§6, **this section governs**.

### M1 amended — the helper must not fail open (MP-R1-001)
`_blocking_finding_fingerprints` returns `[]` on a missing or unreadable evidence file, so deleting or corrupting that file erases every blocker from the progress digest. The type filter alone does not repair that. The helper now:
1. selects the newest **`code-review`** record of the path (as M1);
2. reads its evidence and **refuses** `review_evidence_invalid` (integrity failure) when the file is missing, is not JSON, or does not correspond to the ledger record: the embedded record's path, sha, review type and result, and the findings counts, must equal the ledger's;
3. never returns an empty set as a stand-in for "could not read".
Its callers are `_loop_progress` and the loop's gate summary (`loop show`); both inherit the refusal. **Stated boundary:** the evidence file is not hash-chained, so an edit that leaves it valid and consistent with the ledger is not detected by this change; that is the existing limit of review evidence and is documented, not claimed fixed.

### M2 amended — iterations already past an unstructured review (MP-R1-002)
The step-time refusal protects only iterations that reach the review step after the change. An iteration whose review step was already recorded without findings would otherwise close. So:
1. `loop step --step review` refuses `loop_review_unstructured` (as M2);
2. `loop record` refuses `loop_review_unstructured` when the open iteration's recorded review step carries no findings summary;
3. the engine-supported recovery is `loop stop` followed by `loop begin`; no hand edit of a runtime record is prescribed. An empty `--findings` list is structured and passes.

### M3 amended — one rule for the waiver (MP-R1-003)
The plan's own contract (PLAN Appendix C: a waiver requires a review recorded with `--actor-type human`) is the rule. `cmd_artifact_review` refuses `review_waiver_requires_human` when **any actor type other than `human`** records a finding that is `blocking` and `accepted`, in **any review type**, with **either result**, and does so **before** `reserve_evidence` creates the placeholder. The self-declaration limit (ADR-007 §3) is stated in the refusal text, the troubleshooting entry and the ADR note: it stops silent waivers by every non-human actor type; `--actor-type human` is a convention, not proof.

### Tests added by the amendments
Evidence missing; evidence malformed; evidence inconsistent with the ledger; a later non-code-review record does not hide the blocker; an iteration already past an unstructured review cannot be recorded and `loop stop` then `loop begin` works; all five actor types x PASS and FAIL for the waiver; the refusal writes nothing (no placeholder evidence file, no ledger change).
