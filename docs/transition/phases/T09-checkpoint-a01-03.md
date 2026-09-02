# T09 Implementation Checkpoint — Attempt a01 / Checkpoint 03

**Phase:** T09
**Attempt:** 01
**Milestone:** M3 — enforcement
**Written at:** after M3 was proved green, before starting M4

## Objective currently being worked

M3 of `docs/transition/phases/T09-plan.md`: `cmd_gate_omit` and its parser
entry; `apply_advance` accepts and re-derives; the D10 terminal revalidation;
`compute_drift` and `cmd_repo_staleness` re-pointed; the `governance_recorded`
message. Plan tests N11–N23; X-table rows X1, X6, X7 (X6/X7 were taken in M2 —
see checkpoint 02).

**This is the milestone where governance could have been weakened.** The plan
requires N11 and N21 to exist before the enforcement code, and they did: the
test block was applied first and observed failing for the right reasons.

## Deliberate red window, declared

Confined entirely inside M3, as the plan permits.

| Step | Command | Result |
|---|---|---|
| M3 tests applied, no engine change | `rtk proxy "python -m pytest tests/test_units_gate_policy.py -k 'n11 or n23 or vocabulary or force_or_override or branch_critical'"` | **6 failed, 341 deselected**, RAW_EXIT=1 — N11 at both HIGH and CRITICAL, N23, the no-override-flag test, the branch-critical test and the vocabulary test, each failing because `cmd_gate_omit` and `GATE_OMITTED_DECISION` did not yet exist |
| M3 engine applied | same file, whole | **346 passed, 1 failed** — one defect in *my own test*, fixed below |
| after the fix | whole file | **347 passed**, RAW_EXIT=0 |

The window was closed inside the milestone. The full suite at the end of M3 is
green.

## Completed since previous checkpoint

1. **`scripts/sdle.py` — enforcement.**
   - `GATE_OMITTED_DECISION = "omitted_by_policy"` and
     `BASELINED_GATE_DECISIONS = ("approved", GATE_OMITTED_DECISION)`.
   - `cmd_gate_omit` — the refusal stack mirrors `cmd_gate_approve`'s in the
     same order with `gate_required` inserted: drift queue -> `not_at_gate` ->
     legacy/`governance_missing` -> **`gate_required`** -> `artifact_missing`
     + SHA baseline -> `gate_precondition_hook` -> `review_precondition` ->
     the three pure readers -> write the decision -> `gate_omitted` audit
     entry -> `apply_advance`.
   - `gate omit --gate <key>` parser entry, **`--gate` and nothing else**.
   - `apply_advance` accepts `omitted_by_policy` only after **re-deriving**
     that the gate is still omittable; otherwise `gate_omission_invalidated`.
   - `revalidate_recorded_omissions` — the D10 terminal check, called from
     `cmd_gate_approve`'s pure-reader block ahead of the first `append_audit`.
   - `compute_drift` and `cmd_repo_staleness` now key off
     `BASELINED_GATE_DECISIONS`. **This is F2, the phase's most likely silent
     regression**, and N19 drives it end to end.
   - `BRANCH_CRITICAL_ACTIONS` gains `("gate", "omit")` — it advances the
     lifecycle and fingerprints working-tree content, which is the set's own
     stated criterion.
   - `write_completion_summary`'s `all_gates_approved` becomes derived. See
     the deviation note below.
   - The stale T06 comment above `required_gates_always` replaced.
2. **`tests/test_units_gate_policy.py`** — M3 block appended (690 -> 1269
   lines): N11 at HIGH and CRITICAL, N12, N13 across three flow/level pairs,
   the HOTFIX drive, N15, N16, N17, N18, N19, N20 (missing artifact, missing
   review, failed review), N21 across four refusal sites, N22 both ways, N23,
   the no-override-flag test, and the `skip`-untouched guard.
3. **X-table edits applied this milestone**, all TP-003 **category 2**:
   X1 (inverted in place), plus three rows the plan's table did not enumerate.

## Three more unlisted X rows, all closed-set growth

Each is a test whose *own comment* names the growth path it has; each was found
by running the suite; the clause carrying the guarantee is untouched in all
three.

* **X15** — `test_units_workitem_resolution.py`: `CRITICAL_INVOCATIONS` gains
  a `gate omit` row and the count assertion goes 9 -> 10. The file says "if
  `BRANCH_CRITICAL_ACTIONS` grows, this list must grow with it".
* **X16** — `test_units_governance.py::test_the_clause_has_exactly_one_enforcement_site`:
  both closed sets gain `cmd_gate_omit`. The test says "a fourth caller has to
  argue for itself here"; `cmd_gate_omit` argues on exactly the ground
  `cmd_gate_approve` does — it appends to `audit.md` before it moves the phase.
* **X17** — `test_units_artifact_review.py::test_the_artifact_shas_writer_set_is_unchanged`:
  gains `cmd_gate_omit`. Leaving it out would have been the F2 regression
  itself: an omitted gate with no baselined SHA is one whose artifact can
  change with no drift raised.

Running total of unlisted X rows: X13 (checkpoint 01), X14 (checkpoint 02),
X15, X16, X17. All five will be named in the handoff.

## The one deviation from the plan's file table, narrowed

`write_completion_summary` is not in the plan's "files expected to change"
list, and the plan says the completion summary needs no code change. Its
evidence item E17 describes `state dump`'s Approvals table, not
`completion-summary.json`, which carried a hardcoded `"all_gates_approved":
True`. After an omission that is a false claim persisted into an artifact — the
"guarantee stated under the wrong name" failure the plan itself names.

**First attempt was too broad and the suite caught it.** Deriving "every gate
of the bound flow carries an approved decision" reported `false` for a
synthetic state that reached `complete` without any decision — a case T09
neither creates nor is responsible for — and broke
`test_units_transitions.py::test_final_gate_completes_the_workflow`. Narrowed
to `not any(decision == GATE_OMITTED_DECISION)`: it reports `false` for the one
fact this phase introduces and for nothing else, the `flow` parameter was
dropped so the signature is T08's again, and no test outside the gate-policy
file needed to change.

## Remaining

M4 (D14 fail-closed `read_repo_config` + X8/X9/N26, D15 the new lint check +
X12, D16 the README qualifier) and M5 (SKILL.md, gate-protocol.md,
sdle-approve.md, README, Reference Guide, ADR-006, tests N27–N31).

Drafts written in this session and **not yet applied**:

```
scratchpad\t09_m4_engine.py   scratchpad\t09_m4_tests.py
scratchpad\t09_m5_docs.py     scratchpad\t09_m5_block.py
```

`docs/architecture/ADR-006-risk-adaptive-gate-policy.md` **is already written
to disk** (it is untracked in `git status`) and has been checked to contain
none of the 22 policy-identifier needles.

## Files changed so far

| Path | Change |
|---|---|
| `scripts/sdle.py` | M1 policy data, M2 requirement model, M3 enforcement |
| `tests/test_units_gate_policy.py` | **new**, 1269 lines |
| `tests/test_units_governance.py` | X5, X2, X3, X4, X13, X14, X1, X16 |
| `tests/test_units_baseline.py` | X6, X7 |
| `tests/test_units_workitem_resolution.py` | X15 |
| `tests/test_units_artifact_review.py` | X17 |
| `docs/architecture/ADR-006-...md` | **new** (M5's, written early) |

## Tests actually run this milestone

| Command | Result |
|---|---|
| gate-policy file, pre-engine (red window) | **6 failed**, RAW_EXIT=1 — declared above |
| gate-policy file, post-engine | **347 passed**, RAW_EXIT=0 |
| seven affected files together | **2 failed, 502 passed** — X16 and the completion-summary breadth, both fixed |
| `tests/test_units_artifact_review.py` after X17 | **40 passed**, RAW_EXIT=0 |
| **Full suite** | **`1 failed, 1378 passed in 1385.87s`** — the single failure was X17, fixed after the run; the file it lives in was re-run green |
| `python scripts/sdle.py lint-skill` | **32 checks, `failed: []`**, exit 0 |

**Honest statement of the residual:** the full-suite figure above was taken
*before* the X17 fix. `tests/test_units_artifact_review.py` was re-run in full
and is green, and X17 is a pure test-expectation edit that touches no product
code, so no other file's outcome can have changed. The next full suite runs at
the end of M4 and its figure supersedes this one.

Count progression, each figure re-derived in this session: 1025 at HEAD -> 1056
after M1 -> 1352 after M2 -> **1379 collected after M3**.

## Current failures

**None outstanding.** X17 was the last, and its file is green.

## Git status / diff summary

- HEAD `ad08d4b`; nothing committed this attempt.
- `git diff --stat`: `scripts/sdle.py` +605, four test files, plus untracked
  `tests/test_units_gate_policy.py`, `docs/architecture/ADR-006-*.md` and the
  three checkpoints.
- Rollback: `git checkout e1cf341 -- scripts/sdle.py`.

## Unresolved decisions

None requiring a human. No `T09-blocker.md`.

## Exact resume instruction

1. `cd D:/Learning/AI/sdle-git-repo/sdle-latest`; confirm HEAD `ad08d4b`.
2. Verify M3 is on disk rather than assumed: `python scripts/sdle.py gate
   --help` must list `omit`, and `python -c` over `sdle.py` must find
   `cmd_gate_omit`, `revalidate_recorded_omissions` and
   `BASELINED_GATE_DECISIONS`. `wc -l tests/test_units_gate_policy.py` should
   read 1269 (measured, not estimated).
3. Apply M4: `scratchpad/t09_m4_engine.py` then `t09_m4_tests.py`. Re-read both
   against disk first; every anchor must still be unique. Expect the new lint
   check to take the count 32 -> 33.
4. Then M5: `scratchpad/t09_m5_docs.py` then append `t09_m5_block.py` to
   `tests/test_units_gate_policy.py` (it needs `import subprocess` adding to
   that file's imports). ADR-006 is already on disk.
5. Finish with the full suite, `lint-skill`, `validate.py`,
   `T09-handoff-a01.md` and `progress.md` -> `IMPLEMENTED`.
6. Tooling traps: always `rtk proxy` for pytest, redirect, read `$?` with no
   pipe; the Bash tool caps a foreground command at 600s so the ~23-minute
   suite needs `run_in_background` or an `until` loop; a plain `grep -rn` has
   produced a false negative, so reproduce negatives with a Python walk;
   `lint-skill` and `constants` nest their payload under `data`; the tree is
   CRLF and `git show` is LF; a `PostToolUse` secrets tripwire fires on the
   substring inside the phrase "risk-adaptive" — false positive, no credential.
