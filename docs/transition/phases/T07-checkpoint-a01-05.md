# T07 Implementation Checkpoint — Attempt a01 / Checkpoint 05

**Phase:** T07
**Attempt:** 01
**Milestone completed:** **M5** — binding and enforcement. **The deliberate red
window opened and closed inside this milestone.**
**HEAD at checkpoint:** `77ca0b8` (nothing committed; all work is in the working tree)
**Rollback point:** `c0775b3`

## Objective currently being worked

M5 is complete and green. Next objective is **M6**: `tests/test_units_flow_model.py`
in full — N1–N11, N13, N15, N26 — driving the five flows end to end through the
real CLI.

## The red window: how it was opened and closed

The plan's F2 says the `cmd_init` binding and the fixture flip must both land
before the suite is run again, and that a suite run inside the window would
show hundreds of failures concentrated on `constitution_draft` /
`gate_constitution`.

**The window was never entered with a running suite.** The order actually
executed in this context was: engine patch → prompt patch → fixture flips →
N8 rewrite → new tests → *then* the first test run. So there is no red
observation to report, which is the intended outcome rather than a gap in the
evidence: F2's mitigation is precisely "make both edits before running".

Two fixture defaults had to flip, not one — see the declared divergence below.

## What M5 puts on disk

### `scripts/sdle.py`

| Change | Where |
|---|---|
| **The flow binds at `init`** | `cmd_init` reads `read_governance_record(paths) if paths.workitem else None`, takes `classification.flow`, and falls back to `DEFAULT_FLOW`. **`cmd_init` still does not call `apply_advance`** (A12/F11) — it reads `flow.next_phase("requirements_check")` exactly as before. |
| **`flow_selected` audit entry** | appended in `cmd_init` immediately after `workflow_initialized`, naming the flow, its phase count, its gate count, and whether a record selected it or the default applied. |
| **`flow_precondition(paths, state)`** | new module-level **pure reader**, defined immediately above `apply_advance`. Returns early under the legacy binding and when there is no record; refuses `flow_mismatch` (exit 1) with a named remedy otherwise. It never writes state and never appends. |
| Three call sites | `apply_advance` (between the two governance calls, below), `cmd_gate_approve` (beside its existing early pure-reader precheck), `cmd_skip` (same). |
| **D14** | `write_completion_summary` gains `"flow": state.get("flow")` after `workflow_version`. `all_gates_approved` is unchanged. |
| **D13** | `evaluate_classification` returns `"advisory": False` and its docstring now says which value binds and which is still inert; `record_governance_audit`'s ledger line reads `classification <type>/<flow> (flow selects the lifecycle; type advisory)`; `cmd_governance_gates`'s note becomes "Every gate **within the selected flow** still runs unconditionally", and its own `"advisory": True` **stays `True`** with a comment saying why (the would-be gate set really is still inert — that is T09's). |

### The declared divergence on `flow_mismatch`'s placement — restated with its evidence

Checkpoint 04 recorded it in advance; this is what was actually written.

D10 says the check goes *after* `governance_precondition` **and** before any
`append_audit`. Those two clauses cannot both hold, because
`governance_precondition(paths, state)` calls `record_governance_audit`, which
calls `append_audit`. `governance_precondition` is on **A13's byte-identical
list** and may not be split. `apply_advance` therefore reads:

```
governance_precondition(paths)          # pure reader: validity refusals, no write
flow_precondition(paths, state)         # flow_mismatch, still ahead of every write
governance_precondition(paths, state)   # the accepted facts enter the ledger
```

Both of D10's intents hold: no existing refusal is masked, and the new refusal
fires before the first irreversible write. Two tests written this milestone pin
each half —
`test_the_governance_refusals_are_not_masked_by_the_flow_check` (a record that
is *both* stale and flow-disagreeing still refuses `governance_stale`) and the
three `flow_mismatch` cases, each asserting `audit.md` byte-identical.

**No new caller was added.** `test_the_clause_has_exactly_one_enforcement_site`
groups by *function name*, and `apply_advance` was already in the set; it
passed untouched. `test_the_gate_approval_precheck_runs_before_the_first_audit_write`
asserts `len(guards) == 1` inside `cmd_gate_approve`'s own body, which still has
exactly one `governance_precondition` call; it also passed untouched.

### Prompt layer (D13's remaining three items)

- `modules/phase-execution.md`: the eight `(Gate N/8)` parentheticals become
  *"Its gate number and total are flow-relative: use the `gate_number` and
  `gate_total` that `sdle.sh gate show --gate <key>` reports for the bound
  flow."* The unconditional design-document sentence in Phase 15 becomes
  conditional on `design/app/app-design.md` existing, with the reason stated
  inline — under `DEFECT_FIX` and `HOTFIX` there is no design document, and the
  orchestrator must never assert a path that does not exist.
- `modules/gate-protocol.md`: `Gate {gate_number}/8` → `Gate
  {gate_number}/{gate_total}`; `Gate 8/8 (security) approved` → `Gate
  {gate_number}/{gate_total} (security) approved`; `All 8 gates passed` → `All
  {gate_total} gates passed`. **The stale `.workflow/completion-summary.json`
  path on that same line is left exactly as it is** (T11 / T04 N-6), as the plan
  requires.

`git diff --numstat` = `3 / 3` for `gate-protocol.md` and `19 / 9` for
`phase-execution.md` (the 10 M3 lines plus M5's nine replacements).

### Test edits — every one under a TP-003 category

| File | Category | What and why |
|---|---|---|
| `tests/conftest.py` | **2 — superseded** | **The one permitted line.** `record_governance`'s `"flow": "ITERATIVE"` → `"GREENFIELD"`, with a six-line comment stating that the value was inert at T06 and selects traversal at T07, and that `started` sits at `constitution_draft`. `git diff --numstat` = **7 / 1** — one changed line plus six comment lines. **No fixture, helper, signature or `Project` method was added or changed.** |
| `tests/test_units_governance.py` | **2 — superseded** | Its own `governance_input()` default flow (the second shared default — see below); the three `"advisory": True` record assertions → `False`; `test_classification_is_marked_advisory_in_the_record` renamed to `test_the_classification_flag_no_longer_claims_to_be_advisory` and strengthened — it now asserts the record says `False` **and** that `governance gates` still says `True`; the E19 differential rewritten as N8. |

### The second declared divergence: two shared fixture defaults

The anti-contradiction clause permits exactly one `tests/conftest.py` line, and
that is honoured. But `tests/test_units_governance.py` defines its **own**
document builder, `governance_input()`, whose default was also
`"flow": "ITERATIVE"`, and cases in that file `init` and then `advance --to
gate_constitution`. Re-derived in this context,
`grep -rn 'flow' tests/*.py | grep -i 'iterative|greenfield|hotfix|defect_fix|brownfield'`
returns exactly eight non-flow-model source lines: `conftest.py:208` and
`test_units_governance.py:139, 712, 1454, 1737, 1741, 1745, 1749`.

The builder's default is now `GREENFIELD`, for the same reason and in the same
TP-003 category. **`test_units_governance.py:1454` deliberately keeps
`ITERATIVE`** — that case only assesses and reads `governance gates`, so it
stays live evidence that a non-GREENFIELD flow round-trips through the record.

The clause's *intent* — one attributable shared default per file, changed for a
stated reason, and no new shared machinery — is kept. Its literal one-line count
is not, because a second file carries a second shared default the clause did not
enumerate. **Declared, not silent.**

### The N8 rewrite, and why it is stronger than what it replaced

`test_governance_changes_no_lifecycle_behaviour` asserted that all four
governance variants traverse identically, and three of those variants named a
different **flow**. At T07 a different flow must produce a different traversal,
so keeping that assertion would have asserted the opposite of the design.

It is replaced by two tests that together say more:

- **`test_risk_and_type_change_no_lifecycle_behaviour`** — the four variants now
  hold the flow at `GREENFIELD` and vary only WorkItem type and final risk.
  Traversal, approvals, artifact-SHA key set and the ordered lifecycle audit
  events are all identical; the would-be gate set still differs by risk and
  `governance gates` still reports `advisory: True` for every variant. Two new
  guard clauses assert the flow really was held constant, in the record **and**
  in `state["flow"]`, so "the traversal did not move" cannot pass for the
  uninteresting reason that nothing varied which could have moved it.
- **`test_the_flow_is_the_one_governance_value_that_moves_the_lifecycle`** —
  one clone per flow, all five, taken before any run and all carrying identical
  LOW risk. `init` lands on `constitution_draft` / `constitution_draft` /
  `spec_draft` / `impact_analysis` / `impact_analysis`, three distinct phases,
  and `state["flow"]` is the declared flow in each.

**That pair is the T07/T09 boundary written as an executable statement:** flow
moves the lifecycle; risk and type move nothing.

### New tests — additive, `tests/test_units_flow_model.py` 53 → 63

N12 (four tests: the default binding, the HOTFIX binding, the single storage
home, and the `flow_selected` entry's content), N14 (three refusal paths plus
a non-vacuity test that re-assessing the *same* flow still advances, and the
non-masking test), N16 (a pre-v1.16 state carrying a HOTFIX record migrates to
GREENFIELD and then refuses `flow_mismatch` naming both remedies).

Each of the three `flow_mismatch` tests asserts `audit.md` **byte-identical**
before and after, a byte-identical recursive SHA map of the whole scratch
repository, and `audit verify` exit 0 with `matches is True`.

## One defect found by running the new tests, and how it was resolved

`Result` has no `.message` attribute — the refusal message lives at
`result.envelope["message"]`, which is how `test_units_governance.py` and
`test_integration_06_to_09.py` already read it. Two assertions used
`result.message` and raised `AttributeError`; both now read the envelope. The
assertions themselves are unchanged in strength. Found by the test run, not by
inspection.

## Tests actually run in this context

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest tests/test_units_flow_model.py -q -p no:cacheprovider -rsxX"` *(first M5 run)* | **1** | `2 failed, 61 passed` — the `result.message` defect above |
| same, after the fix | **0** | `63 passed in 23.30s` |
| `rtk proxy "python -m pytest tests/test_units_governance.py tests/test_units_transitions.py tests/test_units_state.py -q -p no:cacheprovider -rsxX"` | **0** | `242 passed in 183.86s (0:03:03)` |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **0** | **`866 passed in 903.43s (0:15:03)`** |
| `grep -c "short test summary"` over that run | — | **0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **0** | **`866 tests collected in 0.53s`** — collected == passed |
| `python scripts/sdle.py --project-root . lint-skill` (via the JSON `data` payload) | **0** | `checks 29 failed []` |

**Suite arithmetic:** M4's 855 + 10 new flow-model tests + 1 new governance
test = **866**. `tests/test_units_flow_model.py` collects **63**;
`tests/test_units_governance.py` collects **181**.

`grep -rn "skip|xfail" tests/*.py` filtered to markers returns **exactly one
line** — the pre-existing `tests/test_units_infra.py:49:
@pytest.mark.skipif(SH is None, reason="POSIX sh not available")`. **The output
is quoted rather than summarised** (A22, T03's recorded lesson); T07 added no
skip, no xfail and no deletion, and the captured full run has no `short test
summary` section, so that skipif did not fire here.

## Files changed so far this phase

`git diff --numstat -- tests/` in this context:

```
 7   1  tests/conftest.py
113   3  tests/test_lint_skill.py
  4   1  tests/test_units_cli.py
101  15  tests/test_units_governance.py
  2   1  tests/test_units_infra.py
  1   1  tests/test_units_repo_config.py
  2   2  tests/test_units_speckit_binding.py
  4   4  tests/test_units_state.py
  1   1  tests/test_units_transitions.py
  7   6  tests/test_units_workitem_runtime.py
```

Ten `M`, **zero `D`, zero `R`**. `tests/test_integration_01_happy_path.py`,
`tests/test_integration_02_to_05.py`, `tests/test_integration_06_to_09.py`,
`tests/test_hooks.py`, `tests/test_units_workitem*.py` (beyond the runtime
version literals) and `.claude/skills/sdle/modules/security-review.md` are all
untouched.

## Current failures

**None.**

## Constraints M6 onward must not undo

Everything in checkpoints 01–04, plus:

- **`flow_precondition` is a pure reader and must stay one.** Every one of its
  three call sites is ahead of that command's first `append_audit`. Three tests
  assert `audit.md` byte-identical on the three refusal paths.
- **The three-step sequence in `apply_advance` is load-bearing.** Collapsing it
  back to a single `governance_precondition(paths, state)` before the flow check
  regresses A10; moving the flow check ahead of the first call masks
  `governance_stale` / `governance_blocked`.
- **`cmd_governance_gates` keeps `"advisory": True`.** Only the record's
  `classification.advisory` flipped. Flipping the gate set's flag would be T09
  leakage.
- **`test_units_governance.py:1454` keeps `ITERATIVE`.** It is the live witness
  that a non-GREENFIELD flow round-trips through `governance assess`.
- **M6 must not touch `tests/conftest.py` again.** Every new helper belongs in
  `tests/test_units_flow_model.py`.
