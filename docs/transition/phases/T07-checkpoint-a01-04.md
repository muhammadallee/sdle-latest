# T07 Implementation Checkpoint — Attempt a01 / Checkpoint 04

**Phase:** T07
**Attempt:** 01 (unchanged — the previous context was terminated by an API
weekly limit, a §24.6 interruption, **not** a verification FAIL)
**Milestone completed:** **M4** — the schema change. **The plan's declared safe
resume boundary.**
**HEAD at checkpoint:** `77ca0b8` (nothing committed; all work is in the working tree)
**Rollback point:** `c0775b3`

> Written by a resuming implementer. **Every figure below was produced by a
> command run in this context.** Nothing is copied from checkpoints 01–03 or
> from the orchestrator's prose; where a figure agrees with an earlier one it
> was independently re-derived.

## Objective currently being worked

M4 is complete and green. Next objective is **M5, binding and enforcement** —
the phase's one deliberate red window. `cmd_init` binds `state["flow"]` from
the governance record, `flow_selected` enters the ledger, `flow_mismatch` is
refused in `apply_advance` and in the two pure-reader prechecks, D13's text
fixes land, `write_completion_summary` gains `flow`, and the one permitted
`tests/conftest.py` line flips. **The `cmd_init` binding and the fixture flip
must both be on disk before the suite is run again.**

## What was on disk when this context started, and what it verified

The previous context was cut inside M4. This context re-derived the state
rather than trusting it.

| Claim | How it was checked here | Result |
|---|---|---|
| Registry is 20 entries including `impact_analysis` | `lint-skill` | `tables_wellformed: Parsed 20 phases, 8 gates, 16 migration rows.` |
| `GREENFIELD_V1_PHASES` is 19, excludes `impact_analysis`, equals `EXPECTED_TRAVERSAL` | `tests/test_units_flow_model.py` P1/P2 tests, run in this context | pass |
| `tests/test_integration_01_happy_path.py` untouched | `git diff --name-status -- tests/` | the file does not appear |
| `approvals` still has exactly eight keys, no `gate_impact_analysis` | `python -c` over `templates/state.json` | `8 ['gate_analyze', 'gate_constitution', 'gate_design', 'gate_implement', 'gate_plan', 'gate_security', 'gate_spec', 'gate_tasks']` |
| `CURRENT_VERSION`, template, migration | `grep` + `lint-skill` | `CURRENT_VERSION = "1.16"`, `"flow": "GREENFIELD"` in the template, `_mig_1_15` at `MIGRATIONS` row `("1.15", "1.16", _mig_1_15)` |

## What M4 puts on disk

| Site | Change |
|---|---|
| `.claude/skills/sdle/templates/state.json` | `workflow_version` `1.15` → `1.16`; new `"flow": "GREENFIELD"` immediately after `workitem`. `approvals` **unchanged** (eight keys); `progress` **unchanged** (`1/18`, the GREENFIELD default `cmd_init` overwrites). `git diff --numstat` = **2 / 1**. |
| `scripts/sdle.py` | `CURRENT_VERSION = "1.16"`; `_mig_1_15`; `MIGRATIONS` gains `("1.15", "1.16", _mig_1_15)`. |
| `.claude/skills/sdle/SKILL.md` | version string in the frontmatter `description` and in the `# SDLE — Spec Driven Lifecycle Engine (v1.16)` heading; the 16th `VERSION_MIGRATION` row (`1.15` → `1.16`). |
| `README.md` | title `(v1.16)`; the `**v1.16**` history row inserted **above** `**v1.15**` — F13's recorded lesson, because the version linter takes the first `\*\*vN.N\*\*` match. |
| `docs/SDLE-Reference-Guide.md` | the *Covers software version* row now reads v1.16. |
| eight test files | version literals only, plus one test **rename** (below). |

`_mig_1_15`'s body, read in this context:

```
    if not isinstance(state.get("flow"), str) or not state["flow"]:
        state["flow"] = DEFAULT_FLOW
```

Unconditional, idempotent, and it names no governance symbol — which is
witness **P4** of D3's compatibility translation, and is asserted two ways in
`tests/test_units_flow_model.py` (behaviourally, with a record that proposes
`HOTFIX`, and structurally, by parsing the function's own AST with the
docstring stripped so prose cannot make the assertion pass).

### The version-literal test edits — TP-003 category 2, each one named

The plan names this category explicitly: *"Any test asserting
`workflow_version == "1.15"`, the `1.14 → 1.15` terminal migration row, or the
parsed migration-row count of 15 — **2, superseded** — D9's version bump."*

| File | Sites | What changed |
|---|---|---|
| `tests/test_units_repo_config.py` | 1 | `scrubbed["workflow_version"] == "1.16"` |
| `tests/test_units_speckit_binding.py` | 2 | terminal migration step is now `1.15->1.16`; the 1.14 chain reads `["1.14->1.15", "1.15->1.16"]` |
| `tests/test_units_state.py` | 4 | `init` writes `1.16`; the full chain's `to` is `1.16` and its last step `1.15->1.16` |
| `tests/test_units_transitions.py` | 1 | the completion summary's `workflow_version` |
| `tests/test_units_workitem_runtime.py` | 6 (+1 rename) | template version, three migration-chain assertions, `execution.json`'s `sdleVersion` |
| `tests/test_units_cli.py`, `tests/test_units_infra.py` | 2 | **M3's** `phase_count` edits, not M4's; carried in this diff |

**Not mass-rewritten, deliberately.** `grep -rn '1\.15' tests/*.py` still
matches sixteen lines. Every remaining one was read in this context and is
either (a) a historical comment (`# v1.15: Spec Kit's WorkItem artifacts live
under the WorkItem …` in `conftest.py`, `test_hooks.py`,
`test_integration_01_happy_path.py`, `test_integration_02_to_05.py`,
`test_integration_06_to_09.py`, `test_units_speckit_binding.py`), (b) a *source*
version in a migration fixture (`as_version(project, "1.15")` in
`test_units_flow_model.py`, and `{"workflow_version": "1.15", …}` as the legacy
`.workflow/state.json` in `test_units_governance.py`), or (c) the left-hand
side of a migration step string. **None is an assertion about the current
version**, and rewriting them would have destroyed real facts.

**One rename, and why it is not cosmetic.**
`tests/test_units_workitem_runtime.py::test_the_shipped_template_is_1_15_and_carries_the_workitem_field`
asserted `template["workflow_version"] == "1.16"` under a name saying `1_15`.
A test name that contradicts its own assertion is a trap for the next reader,
so the name is now `…is_1_16_and_carries_the_workitem_field`. **The assertions
are byte-identical**; only the identifier changed. TP-003 category 2.

## Verification actually run in this context

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python scripts/sdle.py --project-root . lint-skill"` | **0** | 29 checks, 29 PASS, `"failed": []` |
| `python -c` over the lint JSON `data` payload | 0 | `checks: 29 failed: []`; `tables_wellformed: Parsed 20 phases, 8 gates, 16 migration rows.`; `version_string_consistent: all four locations report v1.16` |
| `rtk proxy "python -m pytest tests/test_units_flow_model.py tests/test_lint_skill.py -q -p no:cacheprovider -rsxX"` | **0** | `81 passed in 11.82s` |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **0** | **`855 passed in 922.50s (0:15:22)`** |
| `grep -c "short test summary"` over that captured run | — | **0** — zero skips, zero xfails, zero errors |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **0** | **`855 tests collected in 0.33s`** — collected == passed |
| `rtk proxy "python -m pytest tests/test_units_workitem_runtime.py -q -p no:cacheprovider -rsxX"` *(after the rename)* | **0** | `45 passed in 80.73s` |

**Suite arithmetic, re-derived here:** the pre-T07 baseline is 791. M1 added 0,
M2 added 36 (9 lint firing tests + 27 flow-model), M3 added 20 (18 flow-model +
2 lint), M4 added 8 (the N17 group in `tests/test_units_flow_model.py`).
791 + 36 + 20 + 8 = **855**. Matches the observed count exactly; nothing was
lost and nothing is unaccounted for.

`python -m pytest --collect-only -q` on the two T07 files reports the flow-model
file at **53** and the lint file at **28**.

## Files changed so far this phase

`git diff --numstat` in this context:

```
 3   1  .claude/settings.local.json                    (pre-existing, OUT OF SCOPE)
48  29  .claude/skills/sdle/SKILL.md
10   0  .claude/skills/sdle/modules/phase-execution.md
 2   1  .claude/skills/sdle/templates/state.json
 4   1  README.md
15   1  docs/SDLE-Reference-Guide.md
632 58  scripts/sdle.py
113  3  tests/test_lint_skill.py
 4   1  tests/test_units_cli.py
 2   1  tests/test_units_infra.py
 1   1  tests/test_units_repo_config.py
 2   2  tests/test_units_speckit_binding.py
 4   4  tests/test_units_state.py
 1   1  tests/test_units_transitions.py
 7   6  tests/test_units_workitem_runtime.py
?? tests/test_units_flow_model.py                      (new)
?? docs/transition/phases/T07-checkpoint-a01-0{1,2,3,4}.md
```

`git diff --name-status -- tests/` is **eight `M`, zero `D`, zero `R`**.
`tests/conftest.py`, `tests/test_integration_01_happy_path.py`,
`tests/test_units_governance.py` and
`.claude/skills/sdle/modules/security-review.md` are **untouched at M4**.

## Current failures

**None.**

## What M5 must do, and the exact shape of its red window

Planned and already drafted as patch scripts under the scratchpad, not yet
applied:

1. **`cmd_init` binds the flow** from `read_governance_record(paths)`'s
   `classification.flow`, defaulting to `DEFAULT_FLOW`. `cmd_init` **still does
   not call `apply_advance`** (A12/F11).
2. **`flow_selected`** enters the ledger at `init`, naming the flow, its phase
   count and its gate count.
3. **`flow_precondition`** — a new pure reader — refuses `flow_mismatch` in
   `apply_advance` and in the two early prechecks in `cmd_gate_approve` and
   `cmd_skip`.
4. D13's text fixes; D14's `flow` key in the completion summary.
5. **The one permitted `tests/conftest.py` line**, `record_governance`'s
   `"flow": "ITERATIVE"` → `"GREENFIELD"`.

### A declared divergence M5 will have to make, recorded here so it is not a surprise

**The plan's placement sentence for `flow_mismatch` cannot be implemented
literally without breaking A10.** D10 says the check goes *"after
`governance_precondition`"* and *"before any state mutation and before any
`append_audit`"*. Those two clauses contradict each other:
`governance_precondition(paths, state)` is **not** a pure reader — when `state`
is passed it calls `record_governance_audit`, which calls `append_audit`. A
`flow_mismatch` raised after it would leave an extra `governance_recorded`
entry in `audit.md`, which is exactly the orphan-entry defect B1/NB-6 fixed at
`0a9b8c7` and `c0775b3`, and A10 requires `audit.md` byte-identical.

`governance_precondition` is on **A13's byte-identical list**, so it may not be
split. M5 therefore writes the sequence in `apply_advance` as three steps:

```
governance_precondition(paths)          # pure reader: validity refusals, no write
flow_precondition(paths, state)         # flow_mismatch, still ahead of every write
governance_precondition(paths, state)   # the accepted facts enter the ledger
```

This satisfies **both** of D10's intents — no existing refusal is masked (a
stale or blocked record is still reported as such), and the new refusal fires
ahead of the first irreversible write. It adds **no** new caller: the closed set
asserted by `test_the_clause_has_exactly_one_enforcement_site` is a set of
*function names*, and `apply_advance` is already in it. The pure-reader first
call is the same device `cmd_gate_approve` and `cmd_skip` already use, and
`test_the_gate_approval_precheck_runs_before_the_first_audit_write`'s
`len(guards) == 1` assertion is scoped to `cmd_gate_approve`'s own body, which
M5 does not add a second `governance_precondition` to.

### A second declared divergence: two shared fixture defaults, not one

The anti-contradiction clause permits **exactly one** `tests/conftest.py` line.
That is honoured. But `tests/test_units_governance.py` defines its **own**
document builder, `governance_input()`, whose default is also
`"flow": "ITERATIVE"` — verified in this context by
`grep -rn 'flow' tests/*.py | grep -i 'iterative\|greenfield\|hotfix\|defect_fix\|brownfield'`,
which returns exactly seven non-flow-model source lines: `conftest.py:208`,
`test_units_governance.py:139, 712, 1454, 1737, 1741, 1745, 1749`.

Cases in that file `init` and then `advance --to gate_constitution`, so the
builder's default must become `GREENFIELD` for the same reason and in the same
TP-003 category as the conftest line. **The clause's intent — one attributable
shared default per file, changed for a stated reason — is kept; its literal
"one line" count is not, because a second file has a second shared default the
clause did not enumerate.** `test_units_governance.py:1454` keeps `ITERATIVE`:
that case only assesses and reads `governance gates`, so it is live evidence
that a non-GREENFIELD flow still round-trips.

### F2's signature, restated so it can be recognised

Between the `cmd_init` binding and the fixture flips, every `started` /
`project`-driven test traverses `ITERATIVE` and fails at `constitution_draft` /
`gate_constitution`. **That is the only failure signature the red window
predicts.** Any other signature is a presumed real regression — the F1
`ENVIRONMENT_FLAKE` procedure is void for this phase. The window must open and
close inside M5, and the suite must not be run inside it.

## Constraints M5 onward must not undo

Everything in checkpoints 01, 02 and 03, plus:

- **`_mig_1_15` is unconditional and names no governance symbol.** Two tests
  pin it, one of them on the parsed AST with the docstring stripped.
- **The template's `approvals` stays at eight keys and `progress` stays
  `1/18`.** `cmd_init` overwrites `progress` from the bound flow on its first
  write; the template value is the GREENFIELD default, not a second source.
- **The `**v1.16**` README history row stays above `**v1.15**`** (F13).
- **`DEFECT_FIX` has 6 gates, not the plan's 5** (checkpoint 03). M7's
  documentation must not restate 5.
- **HOTFIX's minimality is `len(...) <=` plus `set(...) - {"impact_analysis"} <=`.**
  Not a plain subset assertion, which is false.
- **No block header is renumbered**; `modules/security-review.md` is
  must-not-change and cross-references "Phase 17".
- **No `gate_impact_analysis` key anywhere**, and no ninth `approvals` key.
