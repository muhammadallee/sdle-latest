# T08 Implementation Checkpoint — Attempt a01 / Checkpoint 05

**Phase:** T08
**Attempt:** 01
**Milestone:** M5 — the refusals (R1, R2, `classification.rediscovery`)

**No red window was needed.** M5 is the milestone where enforcement begins, and
the plan permitted a red window confined inside it. None occurred: the engine
change and every test update landed together and the full suite was green on
the first run.

## Objective currently being worked

M5 of the T08 plan (D8): the two `init`-time refusals and the monotone opt-in.
R1 `baseline_present`, R2 `baseline_required`, `classification.rediscovery`.
Tests N24, N25, N26, N34, plus the `test_units_governance.py` rows the plan
listed.

## Completed since previous checkpoint

### Engine (`scripts/sdle.py`)

- **`CLASSIFICATION_KEYS = ("type", "flow", "rediscovery")`** and
  `CLASSIFICATION_REQUIRED_KEYS`, defined next to `ENGINEERING_FLOWS`.
  `evaluate_classification` now validates against that tuple instead of an
  inline literal, and returns a fourth key, `"rediscovery": <bool>`.
  - A non-boolean value is refused `classification_invalid`.
  - `rediscovery: true` with any flow other than `BASELINE_REDISCOVERY_FLOW` is
    refused `classification_invalid` — asking to rediscover the repository
    while binding a flow that performs no discovery is a contradiction, and the
    engine refuses rather than ignores it.
  - `GOVERNANCE_RECORD_VERSION` is **not** bumped. An absent key reads as
    `false`, so no governance document written before T08 changes meaning.
- **`BASELINE_REDISCOVERY_FLOW = "BROWNFIELD_DISCOVERY"`** and
  **`BASELINE_REQUIRING_FLOW = "ITERATIVE"`**, with the comment recording that
  `DEFECT_FIX` and `HOTFIX` are deliberately absent.
- **`baseline_precondition(paths, flow, rediscovery) -> str`** — a pure reader
  returning the derived baseline status.
  - **R1** — binding the discovery flow while the baseline is `VALID` or
    `STALE`, with no rediscovery request → `baseline_present`. The message
    names both remedies the contract allows: re-assess as ITERATIVE, or record
    `classification.rediscovery` as true.
  - **R2** — binding the iterative flow while the baseline is `ABSENT` or
    `INVALID` → `baseline_required`.
  - `STALE` satisfies both rules on purpose: a changed reference is a warning
    (D7), and forcing rediscovery on it would contradict §26 item 22.
  - Never enforced under the legacy `.workflow/` binding; it returns the status
    and enforces nothing, for the same reason `governance_precondition` and
    `discovery_precondition` skip it.
- **`cmd_init`** calls it once, immediately after `state["flow"]` is bound and
  **before** `paths.workflow.mkdir(...)`, `write_execution_file` and the first
  `append_audit`. The flow and the opt-in are passed in as plain values, so
  `cmd_init` still names no repository-configuration member (§11).
- The `flow_selected` audit entry gains
  `Repository baseline at binding: <STATUS>.`, so the facts the binding
  decision rested on are in the ledger. D8 says the decision is made once and
  never re-checked mid-flight; that is only auditable if the facts are recorded.

`lint-skill` is unchanged at 32 checks, all passing.

### Tests added — `tests/test_units_baseline.py` (+19)

- **`test_n24_the_second_workitem_does_not_rediscover_the_repository`** —
  acceptance **A9**, §14's exit criterion, driven end to end through the real
  CLI in one repository. WI-A completes `BROWNFIELD_DISCOVERY` (its traversal
  contains `discovery`), which establishes a `VALID` baseline. WI-B assessed
  `BROWNFIELD_DISCOVERY` is refused `baseline_present`, and **no `state.json`,
  `audit.md` or `execution.json` is created for WI-B**. Re-assessed
  `ITERATIVE`, WI-B initialises and completes, and never enters `discovery` —
  asserted on the traversal, on `state.phase_history`, on WI-B's `audit.md` not
  containing the string, and on no `discovery.json` existing. WI-A's ledger is
  untouched and still records its discovery. Nothing in the test plants a
  baseline: the one WI-B is measured against is the one WI-A's completion wrote.
- `test_n24_the_refusal_leaves_the_ledger_and_the_repository_untouched` — the
  B1/NB-6 property re-proved for R1: WI-A's `audit.md` and `state.json` are
  byte-identical across the refusal, `.sdle/baseline.json` is byte-identical,
  and `audit verify` still reports `chain_ok`.
- `test_n25_the_rediscovery_opt_in_permits_the_refused_binding`,
  `test_n25_rediscovery_with_any_other_flow_is_a_contradiction` (parametrised
  over the four other flows), `test_n25_rediscovery_defaults_to_false_and_must_be_a_boolean`.
- `test_n26_iterative_without_a_baseline_is_refused`,
  `test_n26_an_invalid_baseline_does_not_authorise_iterative`,
  `test_n26_a_stale_baseline_authorises_iterative` (D7's decision pinned so a
  later phase cannot flip it silently),
  `test_n26_defect_fix_and_hotfix_are_deliberately_not_covered` (parametrised),
  `test_greenfield_is_never_refused_by_either_rule`.
- `test_the_binding_decision_is_recorded_in_the_flow_selected_entry`.
- `test_the_baseline_precondition_has_exactly_one_call_site` — AST: the only
  caller is `cmd_init`. A second call site would be the mid-flight refusal D8
  rejected.
- `test_the_refusal_precedes_every_write_in_cmd_init` — AST: the
  `baseline_precondition` call's line number is lower than the first `mkdir`,
  `write_execution_file`, `append_audit`, `save_state` or
  `write_active_context` in `cmd_init`. That is derived fact I4 asserted rather
  than inferred.
- `test_n34_no_gate_is_conditional_on_risk_or_classification` — the T09
  leakage guard: `governance gates` still reports `advisory: true`,
  `required_gate_set` still has exactly the two governance callers, and none of
  the six functions T08 added references `required_gate_set`, `evaluate_risk`,
  `GOVERNANCE_LEVELS` or `read_governance_policy`.
- `test_n34_every_flow_gate_set_is_structural_not_policy_driven` — each flow's
  gate keys are exactly the gate phases of its declared phase list.

A local `record_governance_expecting_refusal` helper was added **to the test
file, not to conftest**: `Project.record_governance` asserts success, so a
refusal needs its own caller. It reads the twelve check ids from
`sdle.GOVERNANCE_POLICY_BUILTIN` exactly as the fixture helper does, restating
nothing. **`tests/conftest.py` is unchanged at M5** — it still carries exactly
the two additions the anti-contradiction clause permits.

## Existing tests changed at M5 — TP-003 categories

All four are **category 2, deliberately superseded behavior**. None is deleted,
skipped, xfailed or weakened.

| Test / site | File | Reason |
|---|---|---|
| `CONFIG_REFERENCE_SITES` gains `baseline_precondition` | `test_units_repo_config.py` | The set is asserted by exact equality so a new function reaching the §11 boundary cannot be silent. The T08 comment block already in that set named it in advance. `cmd_init` is deliberately still absent — it reaches the boundary *through* the precondition and names no member itself, which is what keeps `test_no_lifecycle_command_reads_the_repository_configuration` passing unchanged. |
| The `record["classification"] == {...}` exact-equality assertion | `test_units_governance.py` | Gains `"rediscovery": False`. Exactly the row the plan's "Existing tests affected" table names. |
| `test_every_valid_classification_round_trips`'s exact-equality assertion | `test_units_governance.py` | Same reason, same row. |
| `test_the_flow_is_the_one_governance_value_that_moves_the_lifecycle` | `test_units_governance.py` | Its ITERATIVE clone now hits R2. A baseline is established **only when the repository has none**, so a test that establishes a real one first is never overwritten. Its assertions are otherwise unchanged. |
| `bind()` (used by `drive()`, so by every flow-traversal test) | `test_units_flow_model.py` | Same R2 reason, same conditional shape. Exactly the row the plan's table names. |

No test outside the plan's table needed a change at M5, so failure mode F6 did
not fire.

## Tests actually run in this context

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` | **1025 tests collected**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_baseline.py -q -p no:cacheprovider"` | **55 passed in 103.01s**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_governance.py tests/test_units_repo_config.py tests/test_units_discovery.py -q -p no:cacheprovider"` | **307 passed in 230.29s**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_flow_model.py tests/test_units_workitem_runtime.py tests/test_units_state.py -q -p no:cacheprovider"` | **187 passed in 278.08s**, RAW_EXIT 0 |
| `python scripts/sdle.py lint-skill` | exit 0, **32 checks, 0 failing** |
| **`rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (full)** | **`1025 passed in 1211.95s (0:20:11)`, RAW_EXIT 0**, no short-summary lines |

1025 = 1006 at end of M4 plus the 19 tests M5 added. Python 3.13 on Windows;
**Python 3.11 and CI are `NOT_RUN`**.

## Current failures

None. The suite is green at the end of M5.

## Unresolved decisions

None requiring a human.

## Remaining

M6 — verify and finish `ADR-005`, the documentation sweep (README's `.sdle/`
tree still says `baseline.json` is "not created yet"; the Reference Guide's
`.sdle/` table says "no code writes it yet"), `lint-skill` after **every**
document edit, then the final full suite, `lint-skill`, `validate.py`, the
acceptance matrix, `T08-handoff-a01.md` and `progress.md` → `IMPLEMENTED`.

Two ADR-005 defects already identified by reading it against what shipped, to
fix at M6:

1. Its Consequences section says "**Four** new commands" and then lists five.
2. Its D6 does not record that `establish_baseline` establishes nothing under
   the legacy `.workflow/` binding, nor that it returns `(path, sha256)` so
   `cmd_gate_approve` stays out of the repository-configuration reference set.

## Exact resume instruction

M5 is complete and the tree is at end-of-M5 state. A fresh implementer resumes
at **M6**:

1. Verify from disk: `lint-skill` exit 0 with **32** checks;
   `rtk proxy "python -m pytest --collect-only -q"` reports **1025**;
   `grep -n "def baseline_precondition" scripts/sdle.py` hits.
2. Fix the two ADR-005 defects above and re-read the whole ADR against the
   shipped engine before accepting any other sentence in it.
3. Documentation sweep, then **`lint-skill` after every document edit** — the
   doc phase tables and the no-restatement content search are both live.
4. Final full suite, `lint-skill`, `python tools/transition/validate.py`, the
   acceptance matrix A1–A20, the handoff, and `progress.md` → `IMPLEMENTED`.
   `progress.md` cells must contain no literal `|`.
