# T09 Implementation Checkpoint — Attempt a01 / Checkpoint 02

**Phase:** T09
**Attempt:** 01 (unchanged — checkpoint 01's run was interrupted by an API
session limit per §24.6, not a verification FAIL)
**Milestone:** M2 — the requirement model, read-only
**Written at:** after M2 was proved green, before starting M3

## Objective currently being worked

M2 of `docs/transition/phases/T09-plan.md`: `gate_requirements()`, the two
positional helpers, `required_gate_set` reused as its policy half; the two
reporting surfaces (`governance gates`, `gate show`); the record key rename and
the record version reader. Plan tests N1–N6, N14, N24, N25; X-table rows X2,
X3, X4, X13.

**M2 changes no routing.** `apply_advance` is byte-identical to T08's, so every
gate still requires an approval and every flow's traversal is what T08 shipped.
**This is the plan's declared safe resume boundary and it has been reached.**

## Verified from disk at the start of this session (my own observations)

| Fact | Value | Command |
|---|---|---|
| HEAD | `ad08d4b` | `git log --oneline -5` |
| M1 on disk | 17 signals, 12 hard floors, `required_gates_by_risk.MEDIUM` = `[gate_tasks, gate_design]`, `always`/`by_type`/`thresholds` unchanged | `python scripts/sdle.py governance policy` |
| M1 full suite | **`1056 passed`, `RAW_EXIT=0`** (recorded by checkpoint 01's run, read from `scratchpad/m1_suite.txt`) | that file's own `RAW_EXIT=` line |
| Flow shapes | GREENFIELD 19/8, BROWNFIELD_DISCOVERY 20/8, ITERATIVE 17/7, DEFECT_FIX 15/6, HOTFIX 11/3; `gate_security` terminal in **all five**; `implement` present in all five | in-process `load_constants` over the checkout |

## Completed since previous checkpoint

1. **`scripts/sdle.py`** — read-only additions plus two renames.
   - `_policy_gate_reasons()` — new. The one place the three
     `required_gates_*` tables are read; returns gate -> ordered reason list
     (`always` / `risk:<LEVEL>` / `type:<TYPE>`).
   - `required_gate_set()` — **kept, same name and signature**, reimplemented
     as `sorted(_policy_gate_reasons(...))`. Consumed, not duplicated.
   - `GATE_DISPOSITIONS = ("required", "omittable", "not_in_flow")` — the
     closed vocabulary.
   - `terminal_gate_key(flow)` — the derived positional rule. Not a policy row,
     so an override cannot reach it.
   - `gate_requirements(consts, flow, classification, final_level, policy)` —
     pure; returns `dispositions`, `required_gates`, `omittable_gates`,
     `required_not_in_flow`, `terminal_gate`.
   - `gate_requirements_for_state(paths, consts, state)` — the state-bound
     reader. Returns `None` for the legacy binding and for a WorkItem with no
     record; every caller reads `None` as "nothing may be omitted here".
   - `GOVERNANCE_RECORD_VERSION` `"1"` -> **`"2"`**; new
     `GOVERNANCE_RECORD_VERSIONS = ("1", "2")`; `read_governance_record` gains
     a real version check raising `governance_record_invalid` (exit 3).
   - `cmd_governance_assess` — `wouldBeRequiredGates` becomes `requiredGates`
     + `omittableGates`, computed against the record's **proposed** flow.
   - `cmd_governance_gates` — drops `advisory`, `note` and
     `would_be_required_gates`; gains `flow`, `flow_source`, `dispositions`,
     `required_gates`, `omittable_gates`, `required_not_in_flow`, `policy`.
     Resolves the flow from `state.json` when present, from the record
     otherwise, so it is still answerable before `init`.
   - `cmd_gate_show` — gains `required` and `requirement_reasons`, both `null`
     when the question has no answer for this runtime.
   - `record_governance_audit` — a gate-disposition sentence **appended** to
     the existing message, so every prefix assertion still reads the same.
2. **`tests/test_units_gate_policy.py`** — M2 block appended (326 -> 690
   lines). N1/N2/N3 over the 80-cell flow x level x type cross product, N4, N5
   with its non-vacuity guard, N14, N6, N24, N25, the record-shape test and the
   ledger-disposition test.
3. **X-table edits applied this milestone**, each TP-003 **category 2**:
   X2, X3, X4 (clause 3 and docstring), X13 (`advisory` removal — the row the
   plan's table was short by, recorded in checkpoint 01), X6 and X7 in
   `test_units_baseline.py`, plus **X14**, described below.

## Two X-table rows the plan did not enumerate

Both are TP-003 **category 2** — the test asserted something the phase
deliberately changes — and both were found by running the suite, not predicted.

* **X14** — `test_units_governance.py::test_only_evaluate_risk_produces_a_final_level`.
  Its closed reader set for the string `"finalLevel"` gained
  `gate_requirements_for_state`. The test's own comment names this growth path
  ("grows only for a reader that genuinely needs the decided level"). The
  producer assertion `producers == {"evaluate_risk"}` — the clause that carries
  the guarantee — is **untouched**, and the set stays closed.
* **X6/X7 moved from M3 to M2.** The plan schedules them in M3, but M2 breaks
  them: `governance gates` stops reporting `advisory`, and `required_gate_set`'s
  caller set changes to `{gate_requirements}`. They had to be inverted here for
  M2 to be green. X1 was checked and does **not** break in M2 (no lifecycle
  function references `required_gate_set`), so it stays in M3 as planned.

## Remaining

M3 (enforcement), M4 (inherited findings D14/D15/D16), M5 (prompts, docs,
ADR-006). Draft patch scripts for M3 exist in the scratchpad and are
**re-derived, not inherited** — they were rewritten against disk in this
session:

```
scratchpad\t09_m2_engine.py  (APPLIED)   t09_m2_block.py   (APPLIED)
scratchpad\t09_m2_tests.py   (APPLIED)   t09_m2_x14.py     (APPLIED)
scratchpad\t09_m3_engine.py  (NOT APPLIED)
scratchpad\t09_m3_block.py   (NOT APPLIED)
scratchpad\t09_m3_tests.py   (NOT APPLIED)
```

**One deliberate deviation from the plan's file table is queued for M3 and must
be declared in the handoff**: `write_completion_summary` gains a `flow`
parameter and derives `all_gates_approved` instead of hardcoding `True`. The
plan says the completion summary needs no code change, but its evidence item
E17 describes `state dump`'s Approvals table, not `completion-summary.json`.
Leaving `"all_gates_approved": True` after an omission would persist a false
claim — the "guarantee stated under the wrong name" failure the plan itself
names (T08 NB-3). A run that approves every gate still derives `True`, so the
frozen happy path and the three other tests asserting it are unaffected.

`BRANCH_CRITICAL_ACTIONS` also gains `("gate", "omit")` in M3, which forces a
third unlisted X row (**X15**) in
`test_units_workitem_resolution.py` — the file's own comment says the
invocation list must grow with the set.

## Files changed so far

| Path | Change |
|---|---|
| `scripts/sdle.py` | M1 policy data + M2 requirement model and reporters |
| `tests/test_units_governance.py` | X5 (M1), X2, X3, X4, X13, X14 |
| `tests/test_units_baseline.py` | X6 (inverted), X7 (sharpened) |
| `tests/test_units_gate_policy.py` | **new**, M1 + M2 sections, 690 lines |

`.claude/settings.local.json` was already modified at HEAD, is explicitly out
of scope, and has not been touched.

## Tests actually run this milestone

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest tests/test_units_gate_policy.py -q -p no:cacheprovider --no-header -x"` | **`321 passed in 31.45s`, RAW_EXIT=0** |
| `rtk proxy "python -m pytest tests/test_units_governance.py tests/test_units_baseline.py ..."` (first attempt) | **1 failed, 241 passed** — the X14 finding, fixed |
| `rtk proxy "python -m pytest tests/test_units_governance.py -k 'final_level or advisory or would_be or risk_and_type'"` | **`21 passed`, RAW_EXIT=0** |
| **Full suite** `rtk proxy "python -m pytest -q -p no:cacheprovider --no-header"` | **`1352 passed in 1358.59s`, RAW EXIT 0** |
| `python scripts/sdle.py lint-skill` | **32 checks, `failed: []`**, exit 0 |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=9/12 next=T09`, exit 0 |

Counts, re-derived rather than inherited: 1025 at HEAD -> 1056 after M1 (+31)
-> **1352 after M2 (+296)**. Every figure above came from a command run in this
session, with `$?` read on the line after the redirect and no pipe between.

## Current failures

**None.** No deliberate red window was opened in M2; the single failure above
was found and fixed inside the milestone.

## Git status / diff summary

- HEAD: `ad08d4b` — nothing committed yet this attempt.
- `git diff --stat`: `scripts/sdle.py` +301/-… , `tests/test_units_baseline.py`,
  `tests/test_units_governance.py`; `tests/test_units_gate_policy.py`
  untracked; `.claude/settings.local.json` pre-existing.
- Rollback: `git checkout e1cf341 -- scripts/sdle.py` restores the T08 file.

## Unresolved decisions

None requiring a human. No `T09-blocker.md`. The three unlisted X rows (X13,
X14, X15) and the `write_completion_summary` deviation are ordinary
implementation findings, each recorded above with its TP-003 category, and each
will be named in the handoff so the verifier sees them declared rather than
smuggled.

## Exact resume instruction

1. `cd D:/Learning/AI/sdle-git-repo/sdle-latest`; confirm HEAD `ad08d4b`.
2. Verify M2 is on disk rather than assumed:
   `python -c "import ...; sdle.gate_requirements"` must exist, and
   `python scripts/sdle.py --help` must **not** yet list `gate omit`
   (M3 adds it). `wc -l tests/test_units_gate_policy.py` should read 690.
3. Start M3 from `scratchpad/t09_m3_engine.py`, `t09_m3_block.py`,
   `t09_m3_tests.py` — **re-read them against disk before running them**; they
   are drafts, and every anchor must still be unique.
4. M3 order matters: the plan requires N11 and N21 to exist **before** the
   enforcement code. If M3 is restarted from scratch, apply the test block
   first, watch it fail for the right reason, then apply the engine patch.
5. Tooling traps that have produced false results in this migration: plain
   `python -m pytest` under the rtk hook prints `Pytest: No tests collected`
   and exits 0 (a false green) — always `rtk proxy`, redirect, read `$?` with
   no pipe; a plain `grep -rn` has produced a false negative on a real line, so
   reproduce negatives with a Python walk; `sdle.py constants` and `lint-skill`
   nest their payload under `data`; the tree is CRLF and `git show` is LF; the
   Bash tool caps a foreground command at 600s, so the ~23-minute full suite
   must be run with `run_in_background` or waited on with an `until` loop.
