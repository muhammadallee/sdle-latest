# T02 checkpoint a01-03 — M3 complete (schema, version, migration)

**Milestone:** M3 — `workitem` state field, `1.13 → 1.14`, `_mig_1_13`, the 14th
`VERSION_MIGRATION` row, the six version-string sites (plan D6, E12, E13).

## Changes

- `templates/state.json`: `workflow_version` → `"1.14"`, new `"workitem": null`
  immediately after it (26 top-level keys).
- `scripts/sdle.py`: `CURRENT_VERSION = "1.14"`; new `_mig_1_13` and a 14th
  `MIGRATIONS` row. `_mig_1_13` binds `workitem` from where the state file
  actually lives — parent directory named `.sdle` → its parent's name;
  otherwise `null`. Deterministic, never a guess (plan D6).
- `cmd_init` sets `state["workitem"] = paths.workitem`.
- `SKILL.md` `VERSION_MIGRATION`: new `1.13 → 1.14` row whose action column
  contains the literal substring `workitem` (E13 — the linter substring test).
- Six version-string sites, four documents: `templates/state.json` (source of
  truth), `SKILL.md` frontmatter, `SKILL.md` heading, `README.md` title,
  `README.md` first `**vN.N**` (a **new v1.14 history row placed above v1.13**,
  because the linter's `re.search` takes the first match), Reference Guide
  header.

## Tests changed (TP-003) — all category 2

Rationale: the version and the state schema are what T02 is contractually
required to change (contract §8 "State migration strategy"); these assertions
pin the old value of a value T02 supersedes. None is loosened.

| File | Change |
|---|---|
| `test_units_state.py` | `workflow_version == "1.14"`, plus a **new** assertion that `state["workitem"]` equals the bound WorkItem (strengthened, not loosened); whole-chain migration test now reaches `1.14` with terminal step `1.13->1.14` (plan N17: extended in place, not duplicated). |
| `test_units_transitions.py` | completion summary `workflow_version == "1.14"`. |
| `test_lint_skill.py` | `test_version_drift_fires` rewrites the README title `v1.14 → v1.13` (was `v1.13 → v1.12`); the check under test is unchanged. |
| `test_units_workitem.py` | `test_init_records_no_workitem_in_state` → `test_init_records_the_resolved_workitem_in_state`. T01's guard asserted no `workitem` key could exist; T02 is the phase contractually required to create it, so the guard inverts and now also pins that the state file lives under the WorkItem and that no `.workflow/` is created. |

## Evidence

- `python scripts/sdle.py lint-skill` → **raw exit 0**, 22 checks / 22 PASS,
  `tables_wellformed: Parsed 19 phases, 8 gates, 14 migration rows`,
  `version_string_consistent: all four locations report v1.14`,
  `migration_covers_every_state_field: every field has a migration row`.
- `pytest tests/test_units_state.py tests/test_lint_skill.py
  tests/test_units_workitem.py tests/test_units_transitions.py -q`
  → **135 passed, raw exit 0**.

## Next

M4 — `execution.json` + execution identity (D7), `project_name` WorkItem-title
rung (D10).
