# T06 Implementation Checkpoint — Attempt a01 / Checkpoint 05

**Phase:** T06
**Attempt:** 01
**Milestone completed:** **M5** — D10 `append_audit` optional `review` / `evidence_id` linkage, plus the governance ledger entry that carries the lowering attempt. New tests N17 and N32.

## Objective currently being worked

M5 is complete and green (**742 passed, raw exit 0**). Next objective is **M6**: D9, the governed artifact review regime — `artifact review`, `artifact reviews`, `reviews.json`, enforcement clause **E2** in a `review_precondition` called from **both** `cmd_gate_approve` and `_approve_drift`, anti-contradiction row 6b (eight review calls in `run_happy_path`) and the derived set of further insertions. New tests N24–N31, N33–N35.

> **M6 contains the phase's second deliberate red window.** It opens the moment E2 lands and must close before the milestone ends. An agent interrupted mid-M6 finishes or reverts M6; it does not build on red.

## Completed since previous checkpoint

### D10 — two optional keyword arguments, rendered before the chain tail

`append_audit` gained `review: str | None = None` and `evidence_id: str | None = None`. When both are `None` the block is byte-identical to every pre-T06 entry; when supplied, two lines render **between `**Comments:**` and `**Prev:**`**, so `**Prev:**` remains the last line of every entry (F9) and the review result never borrows `decision` (which `test_integration_01_happy_path.py` counts exactly `len(GATES)` times).

### The governance ledger entry, and where it had to live

`record_governance_audit(paths, state, record)` writes one `governance_recorded` entry naming the quality result, the classification, the risk score, the deterministic level, the floors that fired, the proposed level, the final level, and — when a lowering was attempted — that it had no effect.

**Declared divergence from N17's wording.** The plan says "after the first *state-writing* command following a lowering assessment". `governance assess` cannot write it (it runs before `init`, so there is no `audit_sha` — D4), and **`cmd_init` is on A9's byte-identical list**, so it cannot write it either. The entry therefore lands at the first *phase movement*, which is the first command that actually consumes the record. It is emitted from `governance_precondition` **after every refusal has had its chance to fire**, so a refused advance writes nothing, and it is de-duplicated by the record's own `executionId` (`governance_audit_marker`) — re-assessing produces a second entry, eighteen advances do not produce eighteen. No field was added to `state.json` (D12 holds).

### New tests (5 cases, `tests/test_units_governance.py` 166 → 171)

`test_a_lowering_attempt_reaches_the_ledger_and_the_chain_still_verifies` (N17),
`test_the_governance_entry_is_written_once_per_assessment`,
`test_a_refused_advance_writes_no_governance_entry`,
`test_the_audit_block_is_byte_identical_without_a_review` (N32),
`test_a_supplied_review_renders_before_the_chain_tail` (N32).

### One closed-set assertion extended, in a file this phase authored

`test_only_evaluate_risk_produces_a_final_level` (written in M3) asserts a **closed** set of functions that *read* `finalLevel`. `record_governance_audit` legitimately reads it to name it in the ledger, so the closed set grew by that one name. **The load-bearing half — `producers == {"evaluate_risk"}` — is untouched**, and the assertion stays closed rather than being loosened. TP-003 **category 2**; the file is T06's own new test file, not an inherited regression asset.

## Remaining

M6 (second red window), M7, M8, then `T06-handoff-a01.md` and `progress.md` → `IMPLEMENTED`.

## Files changed

Since checkpoint 04: `scripts/sdle.py` (D10 + the governance ledger entry), `tests/test_units_governance.py` (5 new cases + the one closed-set extension). `tests/test_units_artifact_review.py` has been **created but not yet exercised** — it was written while the M5 confirmation run was already collecting, so it is **not** part of the 742 figure below. Treat it as M6 work in progress.

## Tests actually run

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider --tb=short -k 'lowering or governance_entry or refused_advance or byte_identical or chain_tail'"` | 1 then 0 | first `2 failed, 4 passed` (two defects in the *new* tests: comparing two chained `Prev` values, and appending without `save_state`), then **`6 passed`** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | 0 | `1 failed, 741 passed in 1081.98s` — the closed-set assertion above |
| `rtk proxy "python -m pytest tests/test_units_governance.py -q …"` | 0 | `171 passed in 101.83s` |
| **`rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"`** | **0** | **`742 passed in 1078.62s (0:17:58)`**; output file is 12 lines, so `-rsxX` produced **no** short-summary section |
| `python scripts/sdle.py lint-skill` | NOT_RUN | still no document edited; M8 owns the prompt layer |
| Python 3.11 / CI | **NOT_RUN** | host 3.13, branch local-only |

**Suite arithmetic:** 737 at M4 + **5** (`tests/test_units_governance.py` 166 → 171) = **742**.

## Current failures

**None** as of the 742-pass run. `tests/test_units_artifact_review.py` is uncollected work-in-progress for M6.

## Git status / diff summary

- HEAD `4a35a1c`; nothing committed this phase. Rollback point remains **`475795a`**.
- Untracked: `tests/test_units_governance.py`, `tests/test_units_artifact_review.py`, `docs/transition/phases/T06-checkpoint-a01-0{1..5}.md`.
- Pre-existing out-of-scope ` M .claude/settings.local.json` untouched.

## Unresolved decisions

None. No blocker.

## Exact resume instruction

```
rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"   # 742 + whatever
rtk proxy "git status --short"
```

Then implement **M6** per `docs/transition/phases/T06-plan.md` §D9. The patch script for the engine half is already written at
`…/scratchpad/m6_engine.py` (**not applied** as of this checkpoint — verify with `grep -n 'def cmd_artifact_review' scripts/sdle.py`), and the new test file `tests/test_units_artifact_review.py` is already on disk.

Sequence:

1. Apply the engine half: `review_key` / `read_reviews` / `review_status` / `review_precondition` / `cmd_artifact_review` / `cmd_artifact_reviews`, the two `review_precondition` call sites, and the two `artifact` subparsers.
2. Row 6b: one `review_for_gate(project, <gate>)` before each of the eight `gate approve` calls in `run_happy_path`, importing the helper from `tests/test_units_artifact_review.py` — the same cross-module pattern the suite already uses for `run_happy_path`. **`tests/conftest.py` must not gain a review helper: row 5 permits only `record_governance` plus its one call in `started`.**
3. Run the full suite, derive the exact set of further insertions, and close the window with **setup calls only**. Never relax, remove, skip or xfail an assertion; if an assertion genuinely needs editing, that is F4 — stop and write `T06-blocker.md`.
4. Re-run the full suite; M6 must end green.
