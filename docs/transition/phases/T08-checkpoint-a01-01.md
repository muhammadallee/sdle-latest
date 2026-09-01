# T08 Implementation Checkpoint — Attempt a01 / Checkpoint 01

**Phase:** T08
**Attempt:** 01
**Milestone:** M1 — the structural change (`discovery` joins the registry and one flow)

## Objective currently being worked

M1 of the T08 plan: add `discovery` to `PHASE_SEQUENCE`, `NEXT_PHASE`,
`PHASE_LABEL_MAP` and `BROWNFIELD_DISCOVERY`'s `FLOW_PHASES` row; add the
ordinal-free `phase-execution.md` block; update README and the Reference Guide
enough for `doc_lists_every_phase_*`; update the T07 pinning tests and the
denominator test; add N31–N33. Proof: four of five flow traversals
byte-identical, `lint-skill` green, transcripts and integrations untouched.

## Completed since previous checkpoint

First checkpoint of the phase.

**Pre-change baseline established in this context** (the planner recorded "901
passed" as UNKNOWN because it had only observed `901 collected`):

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest -q"` at HEAD `9c10eb5` | **`901 passed in 1045.09s (0:17:25)`, `RAW_EXIT=0`** |

M1 changes applied and verified:

- `SKILL.md` — `PHASE_SEQUENCE` 20 → 21 rows with `discovery` at position 2 and
  everything after it renumbered; `NEXT_PHASE` chains
  `requirements_check → discovery → impact_analysis`; `PHASE_LABEL_MAP` gains
  `discovery | Repository Discovery`; the `BROWNFIELD_DISCOVERY` `FLOW_PHASES`
  row gains `discovery` in second place. **No `PROGRESS_MAP` row**, no
  `PHASE_TO_GATE_KEY` row, no gate machinery. The 4-column human GREENFIELD
  table at the top of `SKILL.md` is untouched, because GREENFIELD does not gain
  the phase.
- `modules/phase-execution.md` — a new ordinal-free
  ``**Phase `discovery` (BROWNFIELD_DISCOVERY only — no GREENFIELD position):**``
  block, placed immediately before the `impact_analysis` block whose shape it
  follows. It points at `sdle.sh discovery schema` for every id and restates no
  category id, classification token or envelope key.
- `README.md`, `docs/SDLE-Reference-Guide.md` — `discovery` named in the flow
  narrative; the guide's registry size 20 → 21, its `BROWNFIELD_DISCOVERY` row
  18/8 → 19/8 with a real description, and a new
  `### Repository Discovery (\`discovery\`) — BROWNFIELD_DISCOVERY only`
  section.

Observed after the change:

- `python scripts/sdle.py constants` → registry **21**, first four
  `['requirements_check', 'discovery', 'impact_analysis', 'constitution_draft']`;
  flow shapes (entries **including** `complete`) GREENFIELD 19/8,
  BROWNFIELD_DISCOVERY **20/8**, ITERATIVE 17/7, DEFECT_FIX 15/6, HOTFIX 11/3.
  That is acceptance A1 exactly.
- `python scripts/sdle.py lint-skill` → **exit 0**, 29 PASS, still
  `all four locations report v1.16`.

## Remaining

M2 (discovery as a governed record), M3 (baseline descriptor, read-only), M4
(establish at completion), M5 (the refusals), M6 (ADR-005 and the doc sweep).

## Files changed

```
.claude/skills/sdle/SKILL.md
.claude/skills/sdle/modules/phase-execution.md
README.md
docs/SDLE-Reference-Guide.md
tests/test_units_flow_model.py
tests/test_lint_skill.py
tests/test_units_governance.py
tests/test_units_cli.py
tests/test_units_infra.py
```

`scripts/sdle.py` is **not** touched by M1: the structural change is entirely
in the data tables the engine parses.

## Tests actually run

| Command | Result |
|---|---|
| `pytest tests/test_units_flow_model.py tests/test_lint_skill.py` (first pass) | 1 failed, 132 passed — `test_declaring_greenfield_as_a_flow_row_fires` |
| `pytest tests/test_lint_skill.py` (after the fixture fix) | **28 passed** |
| `pytest tests/test_units_governance.py tests/test_units_repo_config.py tests/test_integration_01_happy_path.py` | **260 passed** |
| `pytest -q` (full, first) | **2 failed, 906 passed in 1041.53s**, `RAW_EXIT=1` |
| `pytest tests/test_units_cli.py tests/test_units_infra.py` (after the fix) | **37 passed** |
| `pytest -q` (full, re-run after the fix) | recorded in checkpoint 02 |

## Current failures

None outstanding. Three failures were found and fixed inside M1, all of them
mechanical consequences of the registry growing from 20 entries to 21:

1. `test_declaring_greenfield_as_a_flow_row_fires` — its breakage fixture
   renamed the `BROWNFIELD_DISCOVERY` row, which now orphans `discovery` and
   trips `every_registry_phase_is_used_by_some_flow` as well. Retargeted onto
   the `ITERATIVE` row, which names no registry phase of its own, so the edit
   isolates the coverage rule again.
2. `test_units_cli.py::test_skill_root_can_be_pointed_elsewhere` — asserts the
   registry's non-terminal count, 19 → 20.
3. `test_units_infra.py::TestLauncherResolution::test_a_real_launcher_run_succeeds_here`
   — the same assertion, same change.

**These three are outside the plan's "Existing tests affected" table, and two
of them are in its "must not change" list.** They are recorded here and in the
handoff rather than silently absorbed. The plan's own acceptance A1 requires a
21-entry registry, so an assertion that the registry has 20 entries cannot
survive; that is TP-003 **category 2 — deliberately superseded behavior**, not
a plan defect requiring a blocker. The plan table was incomplete for the
mechanical count assertions.

## Git status / diff summary

`git status --short` shows the nine files above plus the pre-existing
`.claude/settings.local.json` (out of scope, untouched). No commit yet — the
phase commits once, at the end.

## Unresolved decisions

None. No material architecture, contract or baseline decision has come up.

## Exact resume instruction

M1 is complete and the tree is at end-of-M1 state. A fresh implementer resumes
at **M2**:

1. Confirm state from disk: `python scripts/sdle.py constants` must report a
   21-entry registry with `discovery` at index 2, and `lint-skill` must exit 0
   with 29 checks.
2. `tests/test_units_discovery.py` does **not** exist yet — it is M2's, and a
   checkpoint claiming otherwise must not be believed.
3. Apply M2 per the plan: `DISCOVERY_*` constants, `discovery schema`,
   `read_discovery_input`, `evaluate_discovery`, `cmd_discovery_assess`,
   `discovery_precondition` at `apply_advance` (and as a pure reader ahead of
   the first `append_audit` in `cmd_gate_approve` and `cmd_skip`), conftest
   edit 2, tests N1–N14 and N29–N30.
