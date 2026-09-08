# T05 Implementation Checkpoint — Attempt a01 / Checkpoint 01

**Phase:** T05 — Introduce Repository-Level `.sdle/` Configuration Boundary
**Attempt:** 01

## Objective currently being worked

Milestone **M1** of `docs/transition/phases/T05-plan.md`: the D1 `Paths` seam plus
the D2 project-root marker, with new tests N1 and N12 and **zero existing-test
edits**. M1 is the structural proof — nothing reads the new properties yet.

## Completed since previous checkpoint

First checkpoint of the phase. Fresh start (HEAD `bf4ba5e`, working tree carried
only `M .claude/settings.local.json`, no `.sdle/` anywhere, `progress.md` PLANNED).

- **D1** — seven read-only properties added to `@dataclass class Paths`
  immediately after `speckit_specs_relative`: `config_root`,
  `config_root_relative`, `config_file`, `policies_dir`,
  `shared_templates_dir`, `baseline_file`, `implementation_state_dir`. Every one
  derives from `project_root` alone; none mentions `workitem`, `workitem_root`
  or `runtime`.
- **D2** — `(".sdle", "config.json")` appended as the **last** entry of
  `PROJECT_ROOT_MARKERS`.
- New test file `tests/test_units_repo_config.py` carrying N1 (3 tests) and N12
  (6 tests, one of them parametrised over four tree shapes) plus a tuple-additivity
  assertion — **10 collected**.

## Remaining

- **M2** — D3 config model (`REPO_CONFIG_DEFAULTS`, `SUPPORTED_CONFIG_VERSIONS`,
  `SUPPORTED_POLICY_FORMATS`, `read_repo_config`), D5 `config init` / `config show`,
  D6 `"config"` into `RUNTIME_FREE_COMMANDS` **together with** the single
  authorised edit to `test_runtime_free_commands_is_a_closed_enumerated_set`.
  New tests N2–N6, N13, N14.
- **M3** — D4's `repo_config_findings` plus the two leak-detector checks written
  **inside** `collect_validation_findings`. New tests N7–N9.
- **M4** — N10 (differential) and N11 (containment).
- **M5** — the repository's own versioned `.sdle/` + ADR-002, README, Reference
  Guide, CLAUDE.md (re-run `lint-skill` after **each** document edit).
- **M6** — full sweep, A1–A22 matrix, handoff, `progress.md` → IMPLEMENTED.

## Files changed

```
M scripts/sdle.py                     (Paths +7 properties; PROJECT_ROOT_MARKERS +1 entry)
?? tests/test_units_repo_config.py    (new, 10 collected)
?? docs/transition/phases/T05-checkpoint-a01-01.md
M .claude/settings.local.json         (pre-existing, OUT OF SCOPE — do not stage/revert)
```

No existing test file has been edited at this checkpoint.

## Tests actually run

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_repo_config.py tests/test_units_workitem_resolution.py"` | **106 passed in 137.85s, RAW_EXIT=0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only tests/test_units_repo_config.py"` | **10 tests collected** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only tests/test_units_workitem_resolution.py"` | **96 tests collected** (10 + 96 = 106) |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only <scratch>/baseline-bf4ba5e/tests"` | **500 tests collected** — pristine `git archive HEAD` copy |
| Full suite at M1 | **NOT YET RUN** — the pristine baseline run is in flight (see below) |

**Baseline method note.** A full-suite run started in the working tree *before*
the first edit was discarded rather than quoted: several tests re-read
`scripts/sdle.py` from disk at run time, so an edit landing mid-run contaminates
it. The baseline is instead being taken against a pristine
`git archive HEAD | tar -x` copy at `<scratchpad>/baseline-bf4ba5e`, which is
independent of the working tree. Collected count there is **500**; the passed
count is still in flight.

## Current failures

None observed.

## Git status / diff summary

- HEAD: `bf4ba5e1f52a893c3ef0247c173687268e5c546c` (`transition/workitem-v1`)
- Rollback point: `7b054ee`
- Nothing committed by this phase yet.

## Unresolved decisions

None. Every judgement is pinned by the plan: JSON policy format (decided, do not
re-open), write fence NOT extended, `SDLE_OWNED_PREFIXES` NOT extended, `.sdle/`
versioned with a zero `.gitignore` diff, `baseline.json` named but not created.

## Exact resume instruction

1. `git status --porcelain` and confirm the two M1 changes above are on disk;
   `rtk proxy "grep -n 'config_root' scripts/sdle.py"` must show the seven
   properties, and `PROJECT_ROOT_MARKERS` must carry four entries.
2. `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_repo_config.py"`
   must be green (10 collected).
3. Resume at **M2** per `T05-plan.md` §"Milestone sequence".
4. Do **not** re-open any decision in the plan's "Unknowns" section.
