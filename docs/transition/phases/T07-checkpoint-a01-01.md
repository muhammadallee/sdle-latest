# T07 Implementation Checkpoint — Attempt a01 / Checkpoint 01

**Phase:** T07
**Attempt:** 01
**Milestone completed:** **M1** — the flow seam.
**HEAD at checkpoint:** `77ca0b8` (nothing committed; all work is in the working tree)
**Rollback point:** `c0775b3`

> This checkpoint was written by a **resuming** implementer. The previous a01
> context was terminated by an API session limit part-way through M1 (§24.6
> interruption, **not** a verification FAIL), so the attempt number is unchanged.
> Every figure below was produced by a command run in *this* context. Nothing is
> carried over from the previous implementer's prose.

## Objective currently being worked

M1 is complete and green. Next objective is **M2**: the `### FLOW_PHASES` table
(four rows) in `SKILL.md`, parse-only loading, `Constants.flow()` validation
already present from M1, the two re-targeted lint checks, the generalised progress
check, L1–L6 and their firing tests, plus N19 and N22–N24.
**M3 (the registry insertion) must not begin until M1 is green — it now is.**

## What M1 actually put on disk (verified in this context, not assumed)

`scripts/sdle.py`, `git diff --numstat` = **390 insertions / 45 deletions**.

**New module-level constants and types** (all confirmed present by `grep`):

- `GREENFIELD_V1_PHASES` — a frozen 19-entry `tuple[str, ...]`, GREENFIELD's only
  home. It is deliberately **not** derived from `PHASE_SEQUENCE`; the comment block
  above it records why (`GATE_PHASES` filters the registry through an explicitly
  declared set, so it is safe to derive; taking *all of* the registry is fail-open).
- `DEFAULT_FLOW = "GREENFIELD"`.
- `MANDATORY_FLOW_PHASES` — the 10-member governance floor, one documented reason
  per member. `impact_analysis` is deliberately absent.
- `GATE_NUMBER_PLACEHOLDER = "{gate_number}"`.
- `@dataclass(frozen=True) class Flow` with `contains`, `position` (non-raising),
  `index`, `phase_at`, `next_phase`, `phase_count`, `gate_total`, `progress_for`,
  `gate_number`, `gate_number_for_phase`, `as_dict`.

**`Constants` changes:**

- field `phase_label` renamed to `phase_label_template`; a **property** named
  `phase_label` was added that renders every template under GREENFIELD, so no
  existing reader lost an attribute.
- new field `flow_phases: dict[str, list[str]]` (populated in M2; empty today).
- new `_build_flow`, `flows` property (injects GREENFIELD from the frozen tuple),
  `_flow_invalid` (raises `IntegrityError("flow_table_invalid")`, exit 3),
  `validate_flow`, `flow(name=None)`, `render_label`, `label_or`; `label()` gained
  an optional `flow` parameter.
- module-level `flow_for_state(state, consts) -> Flow`: a state with no `flow`
  field is pre-v1.16 and therefore GREENFIELD.

**Traversal call sites re-pointed at the bound flow** — `cmd_init`,
`render_header`, `cmd_header`, `cmd_state_dump`, `apply_advance`, `cmd_gate_show`,
`cmd_gate_approve`, `_approve_drift`, `cmd_gate_reject`, `cmd_remediate_begin`,
`cmd_skip`, `cmd_restart`, `cmd_doctor`.

`apply_advance`'s `forward_jump` payload gained `"flow"` and `"in_flow"`, and its
index fields are now computed with the non-raising `flow.position(...)`. A target
outside the **registry** still raises `unknown_phase` via `consts.index(target)`,
so D17's two-reason split is already in place.

`cmd_init` still does **not** call `apply_advance` (F11/A12): it reads
`flow.next_phase("requirements_check")` directly, exactly as it read
`consts.next_phase[...]` before.

`.claude/skills/sdle/SKILL.md`, `git diff --numstat` = **8 insertions / 8
deletions** — the eight `PHASE_LABEL_MAP` gate labels only, `Gate N:` → `Gate
{gate_number}:`. Verified by reading the whole diff hunk. **`PROGRESS_MAP`,
`PHASE_SEQUENCE`, `NEXT_PHASE` and `PHASE_TO_GATE_KEY` are untouched.** The
human-readable `## The 18-Phase Workflow` table near the top of `SKILL.md` renders
gates as `**GATE 5**` and was **already** in that form at `77ca0b8` — it is *not*
part of this diff.

### M1's structural proof — stated honestly, including where it does not hold

The plan's M1 proof is *"`git diff --name-only -- tests/` is EMPTY and the suite is
791 passed"*.

**The seam itself required zero test edits.** Every traversal call site was
re-pointed at `Flow`, and `Constants.phase_label` / `Constants.label()` kept
byte-identical GREENFIELD output, with **no** test touched. That property is real
and is the evidence that the seam moved nothing.

**One test edit is nonetheless present, and it is not the seam's.** It is forced by
the `{gate_number}` placeholder — a separate, deliberate change that the plan
places in the same milestone (M1's row: *"`{gate_number}` placeholder in
`PHASE_LABEL_MAP`"*). So M1's zero-test-edit property is **broken by one line**,
and this checkpoint states that plainly rather than papering over it.

- **File / test:** `tests/test_lint_skill.py::test_phase_set_mismatch_fires`.
- **What it does:** calls the fixture helper `edit(repo, "SKILL.md", <old>, <new>)`
  to rename `gate_analyze` → `gate_analyse` in `PHASE_LABEL_MAP`, proving
  `phase_set_matches_phase_label_map` fires on a mismatched label key.
- **Why it failed:** the helper asserts `old in text`. Its find-string was the
  literal `| \`gate_analyze\` | Gate 5: Analysis Approval |`, which M1's
  placeholder change removed, so the helper's own guard fired:
  `AssertionError: fixture text not found in SKILL.md`. The check under test never
  ran. **The guard working is the reason this was caught rather than silently
  going vacuous.**
- **The edit made:** the find/replace pair now reads
  `| \`gate_analyze\` | Gate {gate_number}: Analysis Approval |` →
  `| \`gate_analyse\` | Gate {gate_number}: Analysis Approval |`. Three lines
  changed, all inside the fixture strings.
- **Assertion strength:** unchanged. `assert checks["phase_set_matches_phase_label_map"]
  is False` is byte-identical. Nothing was skipped, xfailed, deleted or weakened,
  and the mutation once again hits a real line.
- **TP-003 category 2 — deliberately superseded behaviour.** The literal `Gate 5:`
  ceased to exist in `PHASE_LABEL_MAP` by design (D5/D7/L6); the fixture's
  dependence on it is superseded, while the test's intent is preserved intact.

**Sibling-literal check, run in this context, not assumed:**
`grep -rn 'Gate [0-9]:' tests/` returns exactly three source lines —
`tests/test_lint_skill.py:107`, `:108` (the two just edited) and
`tests/test_units_transitions.py:115`, which asserts
`data["label"] == "Gate 1: Constitution Approval"` from `gate show`. That one is
**unedited and passing**: it goes through `consts.label_or(gate_phase, flow)`,
which renders `{gate_number}` as `1` under GREENFIELD. It is therefore a live
witness for failure mode F3 (derived labels reproduce the GREENFIELD literals).
`grep -rn 'Gate 5: Analysis Approval'` across the repo also matches
`docs/SDLE-Reference-Guide.md:541`, which is a prose heading, is not parsed, and
was **not** touched.

## Verification that M1's hardest requirement holds

`consts.next_phase` has a **closed reader set**. Re-derived here by an AST walk
over `scripts/sdle.py` that resolves each `.next_phase` attribute to its receiver
expression and its enclosing function:

```
'consts' -> [('cmd_constants', 7765), ('load_constants', 900),
             ('run_sync_checks', 7453), ('run_sync_checks', 7477)]
'flow'   -> [('cmd_init', 1790), ('apply_advance', 5371), ('cmd_skip', 6643),
             ('cmd_gate_approve', 5570), ('cmd_doctor', 6787),
             ('cmd_gate_approve', 5572)]
```

So the reader set is exactly `{load_constants, run_sync_checks, cmd_constants}` —
populate, lint, dump. **No traversal function reads the registry chain** (D11 /
A17 / F1). The six former engine readers E14 listed now all call `Flow.next_phase`.
This is the precondition M3 requires.

`sdle.sh constants` output keys are unchanged from pre-T07:
`['artifact_ownership', 'gate_number', 'gate_phases', 'gate_to_execution_phase',
'next_phase', 'phase_count', 'phase_label', 'phase_sequence', 'phase_to_gate_key',
'progress', 'project_root', 'skill_root', 'version_chain']`. No key was removed;
`flows` is added at M7, not now.

## Files changed so far this phase

| File | Nature |
|---|---|
| `scripts/sdle.py` | the flow seam; 390 insertions / 45 deletions |
| `.claude/skills/sdle/SKILL.md` | 8 `PHASE_LABEL_MAP` gate labels only; 8 / 8 |
| `tests/test_lint_skill.py` | **one** fixture find/replace pair, TP-003 category 2 |
| `docs/transition/phases/T07-checkpoint-a01-01.md` | this file |

`git status --porcelain` also shows ` M .claude/settings.local.json`, which is
**pre-existing and out of scope** (it was already modified at the start of the
phase and is on the plan's not-adopted list).

`git diff --name-status -- tests/` = `M tests/test_lint_skill.py`. **Zero `D`,
zero `R`.**

## Tests actually run in this context

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest tests/test_lint_skill.py -q -p no:cacheprovider -rsxX"` *(before the fix)* | **1** | `1 failed, 16 passed in 1.00s` — `test_phase_set_mismatch_fires`, `AssertionError: fixture text not found in SKILL.md` |
| `rtk proxy "python -m pytest tests/test_lint_skill.py -q -p no:cacheprovider -rsxX"` *(after)* | **0** | `17 passed in 1.10s` |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **0** | **`791 passed in 848.19s (0:14:08)`**; `grep -c "short test summary"` over the captured run = **0**, so zero skips, xfails and errors |
| `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` | **0** | **`791 tests collected in 0.30s`** — collected == passed |
| `rtk proxy "python scripts/sdle.py --project-root . lint-skill"` | **0** | **22 checks, 22 PASS, `failed: []`**; `Parsed 19 phases, 8 gates, 15 migration rows.`; `all four locations report v1.15` |

Suite count is **791**, identical to the pre-T07 baseline — M1 added no test and
removed none.

## Current failures

**None.**

## Remaining

M2–M8 exactly as the plan's milestone table sets them out. Constraints a resuming
agent must not undo:

- **`GREENFIELD` is not a `FLOW_PHASES` row.** It is injected from
  `GREENFIELD_V1_PHASES` inside `Constants.flows` and validated by the same rules
  as every declared flow. Do not "simplify" it into the table.
- **`load_constants` must parse `FLOW_PHASES` without validating it.** Validation
  belongs to `run_sync_checks` (L1–L3) and to `Constants.flow()` (exit 3). If the
  loader raised on a broken flow row, `tables_wellformed` would short-circuit and
  `assert_only_failure` could never isolate L1–L3 (plan F9).
- **`Flow.position` is deliberately non-raising**, because `apply_advance` computes
  refusal-payload indices for phases that may be outside the flow. Making it raise
  would mask the real refusal reason.
- **`cmd_init` must stay outside `apply_advance`** (A12/F11).
- The `FLOW_PHASES` cell format is **space-separated and un-backticked**;
  `_normalise_cell` strips exactly one outer backtick pair and would mangle a
  backticked list.
- **No `gate_impact_analysis` key anywhere**, and no ninth `approvals` key.
