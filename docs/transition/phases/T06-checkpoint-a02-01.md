# T06 Checkpoint — Attempt a02, 01

**Phase:** T06 · **Attempt:** 02 (remediation after `T06-verification-a01.md` = FAIL)
**Purpose:** make a fresh context able to resume from disk + `git diff` alone.

## What a02 is

Remediation of exactly one blocking finding, **B1**: `cmd_gate_approve` appended
its `gate_approved` audit entry (carrying `**Gate Decision:** APPROVED`) *before*
calling `apply_advance`, and T06's E1 is the first refusal ever reachable there.
An ordinary refusal therefore wrote a false approval into the append-only ledger
and left `audit verify` at exit 3.

**Nothing else from a01 was touched.** Everything else in a01 passed independent
verification and must stay as it is.

## Changes made in this context (working tree, uncommitted at checkpoint time)

| File | Change |
|---|---|
| `scripts/sdle.py` | `cmd_gate_approve`: one added call `governance_precondition(paths)` immediately after `review_precondition(...)`, i.e. before the approval write and before `append_audit`. Passing no `state` makes the call side-effect free. Plus a comment block and a docstring paragraph on `governance_precondition`. |
| `tests/test_units_governance.py` | `frozen()` now also carries `audit.md` **bytes**; new parametrised regression `test_a_refused_gate_approval_leaves_the_ledger_byte_identical`; `test_the_clause_has_exactly_one_enforcement_site` caller set widened to the closed 2-member set; new `test_the_gate_approval_precheck_runs_before_the_first_audit_write`. |
| `tests/test_units_artifact_review.py` | `frozen()` now also carries `audit.md` bytes (twin helper). |
| `docs/architecture/ADR-003-…md` | The "exactly one enforcement site" sentence corrected, plus the ordering rationale. |

`cmd_skip` is **deliberately untouched** — its identical ordering is
pre-existing at `475795a` and is not T06's to change. It is recorded in the
handoff as a finding needing an owning phase.

## Evidence captured so far

- Pre-fix: the new regression test run against a01's product code failed with
  `AssertionError: a refused gate approval appended to the append-only ledger`,
  RAW_EXIT 1, and `test_gate_approve_inherits_the_same_clause` also failed once
  `frozen()` carried the ledger bytes. So the test genuinely fails at `ccb9835`.
- Post-fix targeted: `tests/test_units_governance.py tests/test_units_artifact_review.py`
  → **`218 passed in 224.78s`**, RAW_EXIT 0 (215 at a01 + 3 new).
- Subprocess probe (temporary file, since deleted): `gate approve` at a stale
  record → exit 1 `governance_stale`, audit entries **5 → 5**,
  `**Gate Decision:** APPROVED` count **0**, `audit verify` exit **0**.
- `python scripts/sdle.py lint-skill` → RAW_EXIT 0, 22 PASS / 0 FAIL,
  `Parsed 19 phases, 8 gates, 15 migration rows`, v1.15 in four locations.
- `--collect-only -q` → **789 tests collected** (786 + 3).
- `git diff --exit-code 475795a -- <A5 must-not-change list>` → exit 0.
- AST definition compare vs `ccb9835` over 36 named guardrail definitions:
  **35 identical, 1 differs (`cmd_gate_approve`), 0 missing**.
- `tests/` across the whole phase vs `475795a`: **10 M, 2 A, 0 D, 0 R**;
  removed lines only in `test_units_repo_config.py` (4, from a01's row 4).

## What remains

1. Full suite on the final tree (the run started before the ADR-003 edit must be
   re-run so the recorded figure matches the exact tree).
2. `python tools/transition/validate.py` after `progress.md` is updated.
3. Write `T06-handoff-a02.md`; set `progress.md` T06 → `IMPLEMENTED`, attempt 2.

## Closed

All three remaining items were completed in the same context. Final figures:
full suite on the final tree **`789 passed in 842.77s (0:14:02)`, RAW_EXIT 0**,
13 output lines, `short test summary` count 0; `lint-skill` RAW_EXIT 0,
22 PASS / 0 FAIL (re-run after the ADR-003 edit); `validate.py` RAW_EXIT 0,
`TRANSITION_VALID: complete=6/12 next=T06`. `progress.md` T06 set to
`IMPLEMENTED`, attempt **2**. Handoff: `T06-handoff-a02.md`.
