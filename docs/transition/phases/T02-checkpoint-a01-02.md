# T02 checkpoint a01-02 — M2 complete (resolution ladder)

**Milestone:** M2 — resolution ladder, `--workitem`, `RUNTIME_FREE_COMMANDS`,
`init` legacy refusal, conftest WorkItem (plan D2, D3, C4).

## Engine

- `RUNTIME_FREE_COMMANDS = {"lint-skill", "sha", "constants", "workitem", "migrate-workflow"}`.
- `registered_workitem_ids(paths)` — projects the **index**, never the directory.
- `legacy_state_present(paths)`.
- `bind_workitem(paths, explicit=None, *, for_init=False) -> Paths` — a pure
  function: it returns a bound `Paths` or raises `Refused`. Nothing printed,
  nothing written, so the hooks can call it speculatively. Rungs exactly as
  plan D2: explicit → sole registered → legacy dual-read (zero WorkItems **and**
  `.workflow/state.json` present) → `workitem_required` → `workitem_ambiguous`.
  `for_init=True` refuses `legacy_workflow_present` **before** any rung, so
  `init` can never take rung 3 and the refusal is unconditional in the
  registered-count (plan D2's orphaned-workflow argument, N13b).
- `main()` runs the ladder for every non-runtime-free command.
- New global flag `--workitem`.
- `SDLE_OWNED_PREFIXES` gained `"workitems/"`.

## Two changes the plan did not spell out, both forced by M2

1. **`ARTIFACT_OWNERSHIP` Gate 7 template.** `SKILL.md` registers
   `gate_implement` → `.workflow/implementation-manifest.md` as a *static*
   template. Plan P1/A14/§14 forbid editing that table (T04 owns it), so the
   re-point happens in `resolve_artifact_path`, the single place templates are
   resolved: a leading `.workflow/` is replaced by `paths.runtime_relative`.
   `paths` was added as a 4th, optional parameter; all 7 call sites already had
   `paths` in scope. Without this, every Gate 7 approval refused
   `artifact_missing` pointing at the old path.
2. **`dirty_tree` hook binding** (plan M6 work, pulled forward). The hook read
   `paths.state_file` from an unbound `Paths`, which after M2 is the legacy
   location. It now calls `engine.bind_workitem(paths)` inside the existing
   `try/except`, so ambiguous/absent resolution stays silent — the pre-existing
   failure posture of every other path in that function.

## Tests changed (TP-003)

All **category 2 — deliberately superseded behaviour, path rebinding only**.
Shared rationale: contract §8 moves runtime state under the WorkItem and
`baseline.md` §7 item 3 names T02 as the phase permitted to do it. No assertion
was loosened; every one asserts the same fact at the new location.

| File | Change |
|---|---|
| `conftest.py` | `Project.__init__` gains `workitem`; new `Project.runtime` property; `state_file`/`audit_file` derive from it; `init_git`'s `.gitignore` gains `workitems/*/.sdle/lock`; the old `project` body became `bare_project`; the new `project` registers exactly one WorkItem (`fixture-workitem`) so the ladder binds at rung 2 with no flag anywhere in the suite. |
| `test_units_state.py` | 4 lock literals → `Project.runtime`. |
| `test_integration_01_happy_path.py` | completion-summary glob, lock read → `runtime`. |
| `test_integration_06_to_09.py` | 2 manifest reads, 1 manifest write, 1 lock assertion → `runtime` (the write derives the relative path from `runtime`, so it also pins POSIX separators). |
| `test_units_transitions.py` | emitted `completion_summary` path and the summary file → derived from `runtime`. |
| `test_units_workitem.py` | module-level `project` fixture overrides the shared one back to `bare_project`; `test_init_records_no_workitem_in_state` binds `project.workitem`; `test_a_workitem_does_not_change_what_init_and_advance_produce` gives its control project its own WorkItem. |

**Plan divergence (declared).** Plan §6 puts the conftest WorkItem at M2 while
§7.1 pins all 57 `test_units_workitem.py` cases green *unmodified*. Both cannot
hold: that file asserts exact registry contents against the shared fixture
(`count == 0`, `len(lines) == 5`, the malformed-index parametrisation, the
duplicate-refusal digest comparison). Reconciliation: the file overrides
`project` back to `bare_project`, so **all 57 assertions are byte-identical to
T01**; only the two genuinely superseded cases were edited. Plan §7.2's
rebinding was also pulled forward from M7 to M2 for the files M2's fixture
change reddened — the milestone must leave the suite runnable.

`test_a_workitem_does_not_change_what_init_and_advance_produce`: its T01 control
was "a project with no WorkItem", which C2 makes non-initialisable by
construction. The control now carries a *different* WorkItem identity — the
strongest comparison the post-T02 contract admits. Not a weakening: the same
five state fields and the same `advance` outcome are still compared.

## Evidence (split runs, raw exit codes as observed)

| Selection | Result | Raw exit |
|---|---|---|
| `test_units_state.py test_units_workitem.py test_units_transitions.py` | 118 passed | 0 |
| `test_integration_01_happy_path.py test_integration_06_to_09.py test_hooks.py test_units_cli.py` | 84 passed | 0 |
| `test_integration_02_to_05.py test_units_infra.py test_lint_skill.py` | 87 passed | 0 |

289 total, matching the pre-T02 baseline. No new tests yet.

## Next

M3 — `workitem` state field, `CURRENT_VERSION = "1.14"`, `_mig_1_13`, the 14th
`VERSION_MIGRATION` row, six version-string sites across four documents.
