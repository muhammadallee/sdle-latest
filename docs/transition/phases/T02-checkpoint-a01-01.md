# T02 checkpoint a01-01 — M1 complete (`Paths` seam)

**Phase:** T02 — WorkItem-Scoped Runtime
**Attempt:** 01
**Milestone:** M1 — `Paths` rebinding + the three literal deletions (plan D1)
**Rollback point:** `7b9374b`. HEAD at start of work: `6e8af8c`.

## What landed

`scripts/sdle.py` only. No test file touched, no document touched.

1. `Paths` gained an optional third field `workitem: str | None = None` and a
   single runtime seam:
   - `legacy_workflow` → `<repo>/.workflow` (migration source only)
   - `workitem_root` → `<repo>/workitems/<id>` or `None`
   - `runtime` → `workitem_root/.sdle` when bound, else `legacy_workflow`
   - `runtime_relative` → repo-relative POSIX prefix of `runtime`
   - `workflow` retained as an alias of `runtime` (no call site moved)
   - `state_file`, `audit_file`, `lock_file` rebound onto `runtime`
   - new: `execution_file`, `manifest_file`, `completion_file`, `evidence_dir`
2. The three hardcoded runtime literals identified by plan E2/E3 are gone:
   - manifest relative path — now derived from `paths.manifest_file`
   - manifest `changed` filter — now `paths.runtime_relative + "/"`
   - Phase 17 security diff — now `f":(exclude){paths.runtime_relative}"`
   - additionally `write_completion_summary` and the manifest write now use
     `paths.completion_file` / `paths.manifest_file` instead of concatenating.
3. Four refusal/help strings that named `.workflow/` literally now interpolate
   `paths.runtime_relative`: `read_state` (both branches), `audit verify`
   file-missing (message + stderr), `cmd_init` `already_initialized`, and the
   gate-remediation feedback file's `**Canonical source:**` line.

## Plan-vs-repo divergence recorded

The plan cites the three literals at `scripts/sdle.py:3132`, `:3153`, `:3240`.
At `6e8af8c` they were at `:3146`, `:3167`, `:3254` — a +14 line shift caused by
the out-of-band `write_atomic` retry commit. Same three statements; line numbers
only.

## Evidence

`python -m pytest -q` → **289 passed in 418.68s**, no failures, no errors, with
**zero test edits**. This is M1's acceptance condition (plan §6, §10) and the
structural proof that replaces T01's `0 deletions` numstat: with `workitem=None`
the seam is behaviour-preserving.

Note on the baseline: the plan's F1 red-suite procedure is void. `6e8af8c`
fixed the `write_atomic` WinError 5 flake, so the pre-T02 baseline is 289
passed / raw exit 0. Any failure from here is presumed a T02 regression.

## Next

M2 — resolution ladder, `--workitem`, `RUNTIME_FREE_COMMANDS`, `init` legacy
refusal, and the `tests/conftest.py` `project` fixture WorkItem.

**Known plan-internal conflict to resolve at M2** (found by grep before editing):
plan §6 requires the shared `project` fixture to register one WorkItem, while
§7.1 pins all 57 `tests/test_units_workitem.py` cases green *unmodified*. Those
cases assert exact registry contents against the shared fixture
(`test_list_with_no_registry_is_empty_and_succeeds` asserts
`{"count": 0, "workitems": []}`; `test_the_first_create_writes_the_registry_skeleton`
asserts `len(lines) == 5`; `test_a_duplicate_refuses...`, the malformed-index
parametrisation, etc.). Both cannot hold. Reconciliation taken: conftest keeps
the bare fixture under a new name and `test_units_workitem.py` overrides
`project` back to it — no assertion in those 57 cases changes. Two cases in that
file are genuinely superseded and are category-2 edits:
`test_init_records_no_workitem_in_state` (contradicts D6's new state field) and
`test_a_workitem_does_not_change_what_init_and_advance_produce` (its control
project initialises with zero WorkItems, which C2 makes a refusal).
