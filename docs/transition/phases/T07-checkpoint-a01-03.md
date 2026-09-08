# T07 Implementation Checkpoint — Attempt a01 / Checkpoint 03

**Phase:** T07
**Attempt:** 01
**Milestone completed:** **M3** — the registry insertion.
**HEAD at checkpoint:** `77ca0b8` (nothing committed; all work is in the working tree)
**Rollback point:** `c0775b3`

## Objective currently being worked

M3 is complete and green. Next objective is **M4**: the schema change — `flow` in
`templates/state.json`, `CURRENT_VERSION` `1.15` → `1.16`, `_mig_1_15` and its
`MIGRATIONS` entry, the 16th `VERSION_MIGRATION` row, the four version-string
sites, and N17. **M4 is the plan's declared safe resume boundary.**

## What M3 put on disk

### `impact_analysis` is in the registry, and in exactly two flows

| Table | Change |
|---|---|
| `PHASE_SEQUENCE` | new row at **index 2**; the 18 rows after it renumbered 3–20. Registry is now **20** entries. |
| `NEXT_PHASE` | `requirements_check` → `impact_analysis` (edited) and `impact_analysis` → `constitution_draft` (new) |
| `PHASE_LABEL_MAP` | new row `Impact Analysis` — no `{gate_number}`, because it is not a gate |
| `FLOW_PHASES` | `DEFECT_FIX` and `HOTFIX` rows only |
| `PROGRESS_MAP` | **not touched.** Its 19 rows are byte-identical to `77ca0b8`; it is the GREENFIELD view and `impact_analysis` is not in GREENFIELD |
| `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP`, `GATE_TO_EXECUTION_PHASE`, `templates/state.json` `approvals` | **no row, no key.** It is gateless. |

`modules/phase-execution.md` gained a 10-line block headed
`**Phase \`impact_analysis\` (DEFECT_FIX and HOTFIX only — no GREENFIELD position):**`
— no ordinal, so no existing block header was renumbered and
`modules/security-review.md`'s "Phase 17" cross-reference stays correct. The
block writes `reviews/impact-analysis-<YYYY-MM-DD-HHmm>.md`, then `artifact
record --phase impact_analysis`, then `artifact review --type impact-analysis`
against that exact SHA, then displays the content in conversation before the
downstream gate. It contains **zero** occurrences of `feature bind` and
**zero** of `featureDirectory`, asserted by a test, because the feature
directory does not exist at registry position 2 and `--require-feature` would
refuse and halt every defect flow at its second phase.

`README.md` (+2 lines) and `docs/SDLE-Reference-Guide.md` (+14 lines) name the
phase, satisfying `doc_lists_every_phase_*`. The Reference Guide subsection
deliberately carries **no** GREENFIELD ordinal in its heading. The full
documentation pass is still M7's.

### Lint: 28 → **29** checks, all PASS, `Parsed 20 phases`

The block-header pattern became `^\*\*Phase (?:(\d+) — )?\`([a-z_]+)\``, and the
new check `execution_block_numbers_are_the_greenfield_positions` reports
`all 17 block ordinals are GREENFIELD positions`. Those 17 numbers were
unchecked restated constants before T07; they are now pinned in both directions
(a wrong ordinal fires, and a GREENFIELD phase whose block *drops* its ordinal
fires), which is what pays for making the ordinal optional.

`tables_wellformed: Parsed 20 phases, 8 gates, 15 migration rows.`
`phase_set_matches_progress_map: identical to the GREENFIELD flow` — the
re-targeting is doing visible work here: PROGRESS_MAP has 19 keys and the
registry has 20, and the check passes because its subject is GREENFIELD.

## Three defects found by running the new tests, and how each was resolved

All three were caught by tests written in this milestone, not by inspection.

### 1. The M2 orphan-row fixture anchored on a renumbered line

`test_a_registry_phase_no_flow_names_fires` planted its extra row after
`| 19 | \`complete\` |`. The registry insertion renumbered that to
`| 20 | \`complete\` |`, so the `edit` helper's own guard fired
(`fixture text not found`). Anchor updated to `| 20 | ... |` / `| 21 |
\`orphan_phase\` |`. This is a fixture written earlier in **this same attempt**,
not a pre-existing test.

### 2. "HOTFIX is the subset-minimum of the five flows" is not true as written

The plan (D6, A15) states three identities, the third being *"`HOTFIX` is the
subset-minimum of the five flows — nothing is shorter"*. Implemented literally
as `set(HOTFIX) <= set(flow)`, it **fails against GREENFIELD, BROWNFIELD_DISCOVERY
and ITERATIVE**, because HOTFIX carries `impact_analysis` and those three
deliberately do not. The identity contradicts the user decision the same plan
implements; it is an internal inconsistency in the plan, not a repository fact.

**Resolved by asserting the substance, in two exact parts that are both true:**

```
len(HOTFIX.phases) <= len(flow.phases)                  for every flow
set(HOTFIX.phases) - {"impact_analysis"} <= set(flow)   for every flow
```

Together these forbid any flow being shorter than HOTFIX *and* forbid HOTFIX
growing a second non-mandatory phase — which is exactly what the minimality
claim was for. The first plan identity,
`set(HOTFIX) - {"impact_analysis"} == set(MANDATORY_FLOW_PHASES)`, is
implemented verbatim and passes, and `set(flow) >= set(MANDATORY_FLOW_PHASES)`
for every flow is implemented verbatim and passes.
**Declared divergence from A15's third clause; nothing is weakened.**

### 3. The plan's gate count for `DEFECT_FIX` is wrong; its phase list is right

D4's summary table records `DEFECT_FIX ... 14 non-terminal, 5 gates`. Its **own
explicit phase list in the same row** is `requirements_check, impact_analysis,
spec_draft, gate_spec, plan_draft, gate_plan, tasks_draft, gate_tasks, analyze,
gate_analyze, implement, gate_implement, security_review, gate_security,
complete` — 15 entries, which gives 14 non-terminal (matching) and **6** gate
phases, not 5.

Re-derived independently in this context from the plan's five verbatim lists:

```
GREENFIELD             entries=19 non-terminal=18 gates=8  plan says 18/8
BROWNFIELD_DISCOVERY   entries=19 non-terminal=18 gates=8  plan says 18/8
ITERATIVE              entries=17 non-terminal=16 gates=7  plan says 16/7
DEFECT_FIX             entries=15 non-terminal=14 gates=6  plan says 14/5   <-- MISMATCH
HOTFIX                 entries=11 non-terminal=10 gates=3  plan says 10/3
```

Only `DEFECT_FIX`'s gate column disagrees, and the matching non-terminal count
of 14 confirms the 15-entry list is what was intended. **Membership is the
decision; the count is derived from it.** The membership is implemented exactly
as declared and the test asserts `gate_total == 6`, together with the exact
ordered gate-key list so the number can never be right by accident.
**Declared divergence from D4's summary column and from A8's `14/5`; the
correct figure is `14/6`.** No phase was added or removed to reach it.

## Tests added in M3 — additive only

`tests/test_units_flow_model.py`: 27 → **45** collected (+18).
`tests/test_lint_skill.py`: 26 → **28** collected (+2).

New coverage: the registry is 20 and no flow is all of it; `impact_analysis` at
registry position 2, in exactly `{DEFECT_FIX, HOTFIX}`, absent from GREENFIELD
and from `PROGRESS_MAP`; `DEFECT_FIX`/`HOTFIX` denominators 14/10 and gate
totals 6/3 with their ordered gate-key lists; `impact_analysis` → `spec_draft`
in both defect flows; no gate registration anywhere; the state template still
has exactly the eight pre-T07 approval keys; **no shipped file anywhere under
`.claude/` or in `scripts/sdle.py` contains the string `gate_impact_analysis`**;
the execution block's prohibitions and its governance calls; **N20** — a planted
21st registry row leaves `flows["GREENFIELD"]` byte-identical to the golden
literal while `every_registry_phase_is_used_by_some_flow` fires; **N21** — the
`consts.next_phase` reader set is closed at
`{load_constants, run_sync_checks, cmd_constants}`, no receiver other than
`consts` and `flow` reads `.next_phase`, **every** binding of
`load_constants(...)` in the engine is named `consts` (which is what makes the
name-based grouping a real closure), `next_phase_chains_sequence` still passes
over the 20-entry registry, and the registry chain and the GREENFIELD chain are
asserted to now **differ** at `requirements_check`.

Two `phase_count` literals were updated — **TP-003 category 2**, named by the
plan (*"Any test asserting the parsed phase count of 19 or a `PHASE_SEQUENCE`
length"*):

| File / test | Old | New | Why |
|---|---|---|---|
| `tests/test_units_cli.py::test_skill_root_can_be_pointed_elsewhere` | `phase_count == 18` | `== 19` | `constants.phase_count` is the **registry's** non-terminal count; the registry gained a phase |
| `tests/test_units_infra.py::TestLauncherResolution::test_a_real_launcher_run_succeeds_here` | `phase_count == 18` | `== 19` | same |

Both got a one-line comment stating which count they mean, because GREENFIELD's
is still 18 and the two are different facts now. `Constants.phase_count` is read
by exactly one function in the engine (`cmd_constants`) — verified by grep — so
no traversal depends on it.

## Files changed so far this phase

```
 M .claude/settings.local.json                        (pre-existing, OUT OF SCOPE)
 M .claude/skills/sdle/SKILL.md                       45 / 27
 M .claude/skills/sdle/modules/phase-execution.md     10 / 0
 M README.md                                           2 / 0
 M docs/SDLE-Reference-Guide.md                       14 / 0
 M scripts/sdle.py                                   614 / 57
 M tests/test_lint_skill.py                          112 / 2
 M tests/test_units_cli.py                             4 / 1
 M tests/test_units_infra.py                           2 / 1
?? tests/test_units_flow_model.py                     new
?? docs/transition/phases/T07-checkpoint-a01-0{1,2,3}.md
```

`git diff --name-status -- tests/` = three `M`, **zero `D`, zero `R`**.
`tests/test_integration_01_happy_path.py`, `tests/conftest.py` and
`.claude/skills/sdle/modules/security-review.md` are all untouched.

## Tests actually run in this context

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest tests/test_lint_skill.py tests/test_units_flow_model.py -q -p no:cacheprovider -rsxX"` | 0 | `73 passed in 4.58s` |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (first M3 run) | **1** | `2 failed, 845 passed` — the two `phase_count` literals above |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (after) | **0** | **`847 passed in 858.28s (0:14:18)`**; `grep -c "short test summary"` = **0** |
| `rtk proxy "python -m pytest ... --collect-only -q"` | 0 | flow model **45**, lint skill **28** |
| `rtk proxy "python scripts/sdle.py --project-root . lint-skill"` | **0** | **29 checks, 29 PASS, `failed: []`**, `Parsed 20 phases, 8 gates, 15 migration rows.` |

**Suite arithmetic:** M2's 827 + 18 flow-model + 2 lint = **847**.

The first M3 run's two failures were **not** an environment flake and were not
treated as one — the F1 procedure is void for this phase. They were real,
expected consequences of the registry insertion, diagnosed from the assertion
text and fixed.

## Current failures

**None.**

## Constraints M4 onward must not undo

Everything in checkpoints 01 and 02, plus:

- **`PROGRESS_MAP`'s 19 rows stay byte-identical.** They are the GREENFIELD
  view; adding `impact_analysis` to them would break
  `phase_set_matches_progress_map`, which now compares against GREENFIELD
  exactly.
- **No block header may be renumbered.** `execution_block_numbers_are_the_greenfield_positions`
  pins all 17 to their GREENFIELD positions, and
  `modules/security-review.md` — must-not-change — cross-references "Phase 17".
- **`DEFECT_FIX` has 6 gates, not the plan's 5.** Any later text stating 5 is
  wrong; M7's documentation must not restate it.
- **HOTFIX's minimality is `len(...) <=` plus `set(...) - {"impact_analysis"} <=`.**
  Do not "simplify" it back to a plain subset assertion, which is false.
- `M4` is the **declared safe resume boundary**: M1–M4 are behaviour-neutral for
  GREENFIELD. **M5 opens the one deliberate red window** (the `cmd_init` binding
  lands before the `tests/conftest.py` flip, and both must be made before the
  suite is run again). F2's signature is failures concentrated on
  `constitution_draft` / `gate_constitution`; any other signature is a presumed
  real regression.
