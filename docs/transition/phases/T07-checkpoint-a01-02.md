# T07 Implementation Checkpoint — Attempt a01 / Checkpoint 02

**Phase:** T07
**Attempt:** 01
**Milestone completed:** **M2** — the declarative flow table and its lint rules.
**HEAD at checkpoint:** `77ca0b8` (nothing committed; all work is in the working tree)
**Rollback point:** `c0775b3`

## Objective currently being worked

M2 is complete and green. Next objective is **M3, the registry insertion**: put
`impact_analysis` into `PHASE_SEQUENCE` at position 2, `NEXT_PHASE` (one row
edited, one new) and `PHASE_LABEL_MAP`; add it to the `DEFECT_FIX` and `HOTFIX`
`FLOW_PHASES` rows; write its `phase-execution.md` block; broaden the
block-header regex and add L7 with its firing test; name it in `README.md` and
the Reference Guide.

**M3's precondition is satisfied:** M1 left the `consts.next_phase` reader set
closed at `{load_constants, run_sync_checks, cmd_constants}`, and M2 did not add
a reader (re-checked below).

## What M2 put on disk

### `.claude/skills/sdle/SKILL.md` — the `### FLOW_PHASES` table

Inserted between the `PHASE_SEQUENCE` table and `### NEXT_PHASE`. **Four rows**,
one per declared flow; `GREENFIELD` is deliberately absent, with a blockquote
note saying why and pointing at `GREENFIELD_V1_PHASES`.

Cell format is **space separated and un-backticked**, as D4 requires:
`_normalise_cell` strips exactly one outer backtick pair, so a cell of
individually backticked ids would be mangled into a single unrecognised id.

Row membership as it stands **at the end of M2** (registry still 19 entries, so
`impact_analysis` is not yet in any row — M3 adds it):

| flow | entries | non-terminal | gates |
|---|---:|---:|---:|
| `GREENFIELD` (engine, frozen) | 19 | 18 | 8 |
| `BROWNFIELD_DISCOVERY` | 19 | 18 | 8 |
| `ITERATIVE` | 17 | 16 | 7 |
| `DEFECT_FIX` | 14 | 13 | 5 |
| `HOTFIX` | 10 | 9 | 3 |

`DEFECT_FIX` and `HOTFIX` reach the plan's declared 14 and 10 non-terminal
phases **at M3**, when `impact_analysis` joins them. That is the only reason
they read 13 and 9 here.

Table header is `| flow | phases |`. D4's illustrative snippet writes the second
column as `phases (registry order, space separated)`; `_normalise_header` would
turn that into the identifier `phases_registry_order_space_separated`, so the
shorter header is used and the ordering requirement is stated in the prose
immediately above the table instead. `_column(row, "phases",
"phases_registry_order_space_separated")` accepts either, so a future editor who
restores the longer header does not break the loader. **Declared presentational
divergence from the plan's snippet; the substantive format decision — space
separated, un-backticked, one row per flow — is implemented exactly.**

`PROGRESS_MAP`, `PHASE_SEQUENCE`, `NEXT_PHASE` and `PHASE_TO_GATE_KEY` are still
untouched. `git diff --numstat` for SKILL.md is **23 / 8** — the 8 `PHASE_LABEL_MAP`
label lines from M1 plus 15 new lines.

### `scripts/sdle.py`

- `Constants.greenfield` — a new property returning the frozen flow built
  through the ordinary rules. `flows` and `render_label` now both read it, so
  the frozen tuple is dereferenced in exactly one place.
- `validate_flow` split into `flow_order_problems` (registry membership, no
  duplicates, registry order, starts `requirements_check`, ends `complete`) and
  `flow_floor_problems` (the mandatory set). `validate_flow` is now the raising
  wrapper over both. **One rule, two presentations:** `lint-skill` reports, the
  engine refuses. This is what lets a single planted breakage fire exactly one
  named check.
- `load_constants` parses `### FLOW_PHASES` into `consts.flow_phases`, **without
  validating it**, with the reason stated in the code. A raising loader would
  short-circuit `tables_wellformed` and hide every other check.
- `phase_set_matches_progress_map` re-targeted from the registry to GREENFIELD;
  `progress_denominator_matches_phase_count` re-targeted to GREENFIELD's
  non-terminal count.
- `_check_no_hardcoded_progress` generalised: it now scans for `\d+/<d>` over
  **every flow's** denominator, not just `consts.phase_count`.
- New `_check_flow_model(consts)` returning the six checks L1–L6.

### Lint: 22 → **28** checks, all PASS

Verified in this context, `python scripts/sdle.py --project-root . lint-skill`,
**raw exit 0**, stderr in full:

```
[PASS] tables_wellformed: Parsed 19 phases, 8 gates, 15 migration rows.
[PASS] phase_set_matches_next_phase: identical to PHASE_SEQUENCE
[PASS] phase_set_matches_phase_label_map: identical to PHASE_SEQUENCE
[PASS] phase_set_matches_progress_map: identical to the GREENFIELD flow
[PASS] next_phase_chains_sequence: chains PHASE_SEQUENCE in order
[PASS] progress_denominator_matches_phase_count: denominators=['18'] expected={18}
[PASS] gate_registered_gate_constitution … gate_registered_gate_security   (×8)
[PASS] every_phase_has_execution_block: all present
[PASS] flow_table_covers_the_required_flows: 5 flows: ['BROWNFIELD_DISCOVERY', 'DEFECT_FIX', 'GREENFIELD', 'HOTFIX', 'ITERATIVE']
[PASS] every_flow_is_an_ordered_subset_of_the_registry: 5 flows are ordered subsets of PHASE_SEQUENCE
[PASS] every_flow_retains_the_mandatory_phases: every flow keeps all 10 mandatory phases
[PASS] progress_map_and_gate_numbers_are_the_derived_greenfield_views: PROGRESS_MAP and the gate-number column match GREENFIELD
[PASS] every_registry_phase_is_used_by_some_flow: every registry phase is named by at least one flow
[PASS] gate_labels_are_flow_relative: all 8 gate labels are flow-relative
[PASS] single_state_template … doc_lists_every_phase_SDLE-Reference-Guide     (×7)
```

### Where L4 was deliberately narrowed, and why it is not a weakening

The plan's L4 says *"`PROGRESS_MAP` equals the derived GREENFIELD progress for
every GREENFIELD phase"*. Implemented literally, L4 would also fire on the
breakage planted by the **pre-existing** `test_wrong_progress_denominator_fires`
(`11/18` → `11/19`), which uses `assert_only_failure` and would therefore fail.
That test may not be modified.

L4 therefore owns the **position** (the numerator) and
`progress_denominator_matches_phase_count` owns the **denominator**. Together
they pin the entire string `f"{position}/{18}"` for every GREENFIELD phase, and
each is independently firable by a fixture that breaks only it. Nothing about
`PROGRESS_MAP` is left unchecked — this is a split of responsibility between two
checks, not a reduction in what is asserted. The split is recorded in the code
comment above the check so it cannot be mistaken for an oversight.

L4 additionally pins `PHASE_TO_GATE_KEY`'s `gate number` column to the derived
GREENFIELD numbering, which nothing checked before.

### Tests added — **additive only**

`tests/test_lint_skill.py`: **nine** new functions, appended after
`test_a_doc_missing_a_phase_fires`, plus one module-level helper `flow_row`. No
existing function was modified in M2. (M1's one permitted fixture-literal edit
in `test_phase_set_mismatch_fires` still stands, and is the only `M` in that
file's diff besides the additions: `git diff --numstat` = **90 / 2**, and the
two deletions are M1's two fixture lines.)

Each firing test plants a breakage that isolates one check:

| Test | Check fired | Isolation note |
|---|---|---|
| `test_a_renamed_flow_fires` | L1 | `ITERATIVE` → `ITERATIVE_V2`; the row is still a valid ordered subset with the floor, so L2/L3 stay green |
| `test_declaring_greenfield_as_a_flow_row_fires` | L1 | `BROWNFIELD_DISCOVERY` → `GREENFIELD`; the injected GREENFIELD still wins, so nothing else moves |
| `test_a_flow_out_of_registry_order_fires` | L2 | `analyze gate_analyze` → `gate_analyze analyze` in `ITERATIVE` |
| `test_a_flow_naming_an_unknown_phase_fires` | L2 | `analyze` → `analyse`; order is computed over known phases only, so only the unknown-phase problem is raised |
| `test_a_flow_dropping_a_mandatory_phase_fires` | L3 | drops `gate_implement` from `ITERATIVE`, which leaves an ordered subset (the plan's own suggested breakage) |
| `test_a_progress_value_that_is_not_the_greenfield_position_fires` | L4 | `11/18` → `10/18`; the denominator is untouched |
| `test_a_gate_number_column_that_is_not_the_greenfield_numbering_fires` | L4 | gate number `5` → `9` |
| `test_a_registry_phase_no_flow_names_fires` | L5 | plants a 20th registry row; **asserts its own check directly**, not via `assert_only_failure`, because a new registry phase legitimately also breaks NEXT_PHASE, the label map, the chain and the execution-block check |
| `test_a_hardcoded_gate_ordinal_in_a_label_fires` | L6 | `Gate {gate_number}:` → `Gate 5:` — the exact regression the placeholder exists to prevent |

`tests/test_units_flow_model.py`: **new, 27 collected.** N19 (the golden
literal), P1 (`GREENFIELD_V1_PHASES == EXPECTED_TRAVERSAL`, imported from the
untouchable happy-path file), N22 (six parametrised `FLOW_PHASES` breakages ×
two behaviours: `Constants.flow()` raises `flow_table_invalid` with
`exit_code == 3`, and `load_constants` parses the same breakage silently while
`lint-skill` still returns per-check failures with `tables_wellformed` **passing**),
N23 (the HOTFIX identity, written in its final `- {"impact_analysis"}` form so
M3 does not have to edit it), and N24 (PROGRESS_MAP, the gate-number column and
all eight gate labels reproduced from the derived GREENFIELD flow, including the
byte-exact pre-T07 literals `Gate 1: Constitution Approval` …
`Gate 8: Security Review Approval`).

## Files changed so far this phase

```
 M .claude/settings.local.json          (pre-existing, OUT OF SCOPE, untouched)
 M .claude/skills/sdle/SKILL.md         23 / 8
 M scripts/sdle.py                      573 / 54
 M tests/test_lint_skill.py             90 / 2
?? tests/test_units_flow_model.py       new
?? docs/transition/phases/T07-checkpoint-a01-01.md
?? docs/transition/phases/T07-checkpoint-a01-02.md
```

`git diff --name-status -- tests/` = `M tests/test_lint_skill.py`. **Zero `D`,
zero `R`.**

## Tests actually run in this context

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest tests/test_lint_skill.py tests/test_units_flow_model.py -q -p no:cacheprovider -rsxX"` | **0** | `53 passed in 2.72s` |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **0** | **`827 passed in 857.73s (0:14:17)`**; `grep -c "short test summary"` = **0** |
| `rtk proxy "python -m pytest tests/test_lint_skill.py tests/test_units_flow_model.py --collect-only -q"` | 0 | `53 tests collected` (26 lint + 27 flow model) |
| `rtk proxy "python scripts/sdle.py --project-root . lint-skill"` | **0** | **28 checks, 28 PASS, `failed: []`** |

**Suite arithmetic, re-derived:** M1's 791 + 9 new lint firing tests + 27 new
flow-model tests = **827**. Matches exactly; nothing was lost.

## Current failures

**None.**

## Constraints M3 onward must not undo

Everything in checkpoint 01's list, plus:

- **`load_constants` must keep parsing `FLOW_PHASES` without validating it.**
  Two tests pin this directly
  (`test_load_constants_parses_a_broken_flow_without_raising`), and nine
  `assert_only_failure` firing tests depend on it indirectly.
- **L4 owns the numerator, the denominator check owns the denominator.** Merging
  them would break the pre-existing `test_wrong_progress_denominator_fires`.
- **The four `FLOW_PHASES` rows are the only editable flow declarations.** M3
  adds `impact_analysis` to `DEFECT_FIX` and `HOTFIX` **only** — adding it to
  `ITERATIVE` or `BROWNFIELD_DISCOVERY` contradicts the user decision, and
  adding it to `MANDATORY_FLOW_PHASES` would force it into GREENFIELD.
- After M3 the registry is 20 and GREENFIELD is 19: **`every_registry_phase_is_used_by_some_flow`
  is what stops a future registry row from being orphaned**, and
  `test_a_registry_phase_no_flow_names_fires` is what stops that check from
  going vacuous.
- The `_check_no_hardcoded_progress` denominator set becomes `{18, 16, 14, 10}`
  at M3. Zero matches for `\d+/9`, `\d+/10`, `\d+/13`, `\d+/14` and `\d+/16`
  were confirmed by grep across all four skill files in this context, so the
  generalisation stays free of false positives across the M2 → M3 change.
