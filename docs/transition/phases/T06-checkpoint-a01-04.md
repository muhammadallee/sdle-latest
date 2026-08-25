# T06 Implementation Checkpoint — Attempt a01 / Checkpoint 04

**Phase:** T06
**Attempt:** 01 (resumed after an API-session interruption; §24.6 interruption, **not** a verification FAIL, so the attempt number is unchanged)
**Milestone completed:** **M4** — D8 enforcement E1 in `apply_advance`, anti-contradiction rows 5 and 6a, the derived set of inserted setup calls, and new tests N10–N12.

> **The M4 red window is CLOSED.** It opened when E1 landed (65 failed / 664 passed, verified in this context before any edit) and closed at the end of this milestone (**737 passed, raw exit 0**). No assertion was relaxed, removed, skipped, xfailed or deleted to close it.

## Objective currently being worked

M4 is complete and green. Next objective is **M5**: D10 `append_audit` optional `review` / `evidence_id` arguments (byte-identical rendering when both are `None`) plus the governance audit event that carries the lowering attempt into the ledger. New tests N17 and N32.

## Completed since previous checkpoint

### The red window, derived rather than assumed

The inherited tree already carried E1 in `apply_advance`, `Project.record_governance()` in `tests/conftest.py`, and the `run_happy_path` call. The first action in this context was a **full** suite run to derive the failure set from disk:

`rtk proxy "python -m pytest -q -p no:cacheprovider --tb=no -rf"` → raw exit **0** (the runner's own exit; pytest reported **`65 failed, 664 passed in 637.66s (0:10:37)`**), distribution derived by tallying the `FAILED` lines with a Python one-liner:

| File | Failures |
|---|---|
| `tests/test_integration_06_to_09.py` | 26 |
| `tests/test_integration_02_to_05.py` | 19 |
| `tests/test_units_workitem_runtime.py` | 12 |
| `tests/test_units_speckit_binding.py` | 4 |
| `tests/test_units_repo_config.py` | 2 |
| `tests/test_units_workitem.py` | 1 |
| `tests/test_units_workitem_resolution.py` | 1 |

Every failure sampled with `--tb=short` / `--tb=line` reported the **same** cause: `reason='governance_missing'` raised from `apply_advance` through `conftest.Project.ok`. There was no second failure mode.

### The derived set of inserted setup calls — 13 insertions across 8 files

All are **setup calls only**. Each is TP-003 **category 2**.

| File | Site | Calls |
|---|---|---|
| `tests/test_integration_02_to_05.py` | `at_gate_spec`, `test_03_skip_is_two_step`, `test_03_skip_is_permanently_logged` | 3 |
| `tests/test_integration_06_to_09.py` | `at_implement`, `at_gate_plan`, `test_07_staleness_is_scoped_to_recorded_artifact_paths` | 3 |
| `tests/test_units_speckit_binding.py` | `drive_full_workflow`, `test_n3_a_gate_refuses_another_workitems_artifact`, `test_migrated_in_flight_workflow_refuses_its_next_speckit_gate`, `test_feature_resolve_recovers_a_migrated_workflow_without_drift` | 4 |
| `tests/test_units_workitem_runtime.py` | `legacy_workflow` | 1 |
| `tests/test_units_workitem_resolution.py` | `test_skip_on_a_mismatched_branch_needs_both_acknowledgements` | 1 |
| `tests/test_units_repo_config.py` | `two_workitems_one_mid_run` | 1 |
| `tests/test_units_workitem.py` | `test_a_workitem_does_not_change_what_init_and_advance_produce` (both sides of the comparison) | 2 |

**Two declared divergences from the plan's *enumeration* (not from its rule).** The plan bounded the derived set by "the 49 `"approve"` literals across 8 files" and listed six candidate files. E1 sits at **`advance`**, not at `approve`, so the true bound is phase-*movement* sites; `tests/test_units_repo_config.py` and `tests/test_units_workitem.py` are therefore in the derived set although neither appears in that enumeration. `tests/test_units_workitem.py` is additionally named in the plan's "byte-unchanged and passing" list. Both are recorded here as declared divergences per the anti-contradiction clause's own escape hatch ("record it as a declared divergence with the reason and the category"); both are inserted setup calls, category 2, with **no** assertion touched.

### One further conftest change inside row 5's method body

Five `tests/test_integration_06_to_09.py` cases then failed with `dirty_tree: ?? governance-input.json` — the fixture's transient proposal document was polluting the git working tree and tripping `implement preflight`. Fixed **inside `Project.record_governance()`** by deleting the input after `governance assess` consumes it (`try/finally`), since the evidence document already preserves the document verbatim. `SDLE_OWNED_PREFIXES` was **not** extended — A9 requires it byte-identical, and extending it would have been the fail-open shortcut.

`bare_project`, `project`, `git_project`, `started_git` and `isolated_git_identity` keep their exact bodies; `started` still carries exactly one `record_governance()` call.

### New tests N10–N12 (8 cases appended to `tests/test_units_governance.py`)

`test_a_blocking_finding_stops_progression_and_the_record_survives`,
`test_re_assessing_a_fixed_requirement_unblocks_the_same_advance`,
`test_advance_without_a_governance_record_is_refused`,
`test_gate_approve_inherits_the_same_clause`,
`test_the_clause_has_exactly_one_enforcement_site`,
`test_editing_a_requirement_after_the_assessment_is_stale`,
`test_adding_a_requirement_file_is_also_stale`,
`test_e1_is_skipped_under_the_legacy_binding_and_only_there`.

Each refusal case asserts the fail-safe shape as a tuple — `current_phase`, `status`, `approvals`, `artifact_shas`, `audit_sha` unchanged — not merely the reason string.

Two facts were discovered by running, not assumed:

1. `init` completes `requirements_check` and lands on `constitution_draft`, so a WorkItem's **first** advance target is `gate_constitution`. The first draft targeted `constitution_draft` and correctly got `forward_jump` — which also confirms, behaviourally, that the two original refusals still fire **before** E1.
2. `cmd_skip` calls `append_audit` *before* `apply_advance`, so a governance refusal on the `skip` path would leave an orphan ledger entry. That ordering is **pre-existing** (`gate_not_approved` can already fire there) and is not T06's to change; the behavioural half of the `skip`/`gate approve` guarantee is therefore proved via `gate approve`, and the structural half by `test_the_clause_has_exactly_one_enforcement_site`, which asserts by AST that `governance_precondition` is called from `apply_advance` **only** and that `apply_advance`'s callers are exactly `cmd_advance`, `cmd_gate_approve`, `cmd_skip`.

## Remaining

M5, M6 (**contains the second deliberate red window — the review regime; it must open and close inside M6**), M7, M8, then `T06-handoff-a01.md` and `progress.md` → `IMPLEMENTED`.

## Files changed

`git diff --numstat 4a35a1c -- scripts/ tests/` (run in this context):

```
1127	5	scripts/sdle.py
38	0	tests/conftest.py
3	0	tests/test_integration_01_happy_path.py
4	0	tests/test_integration_02_to_05.py
5	0	tests/test_integration_06_to_09.py
14	0	tests/test_units_repo_config.py
5	0	tests/test_units_speckit_binding.py
4	0	tests/test_units_workitem.py
5	0	tests/test_units_workitem_resolution.py
1	0	tests/test_units_workitem_runtime.py
```

Zero deletions in every test file; zero `D`, zero `R`. `tests/test_units_governance.py` is still untracked (`??`), now **166** collected. No document, no prompt file, no constant table has been edited yet.

## Tests actually run

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider --tb=no -rf"` (before any edit) | 0 | **`65 failed, 664 passed in 637.66s`** — the inherited red window |
| `rtk proxy "python -m pytest tests/test_units_governance.py -q … --tb=short"` (mid-M4) | 1 | `6 failed, 160 passed` — two defects in the *new* tests, both fixed (advance target; missing `import shutil`) |
| `rtk proxy "python -m pytest … -k 'blocking or unblocks or …'"` | 0 | `13 passed, 153 deselected in 10.48s` |
| `rtk proxy "python -m pytest tests/test_units_governance.py tests/test_integration_01_happy_path.py tests/test_units_repo_config.py tests/test_units_workitem.py tests/test_units_workitem_resolution.py -q …"` | 0 | `398 passed in 956.66s (0:15:56)` |
| `rtk proxy "python -m pytest tests/test_integration_02_to_05.py tests/test_integration_06_to_09.py tests/test_units_speckit_binding.py tests/test_units_workitem_runtime.py -q …"` | 0 | `5 failed, 175 passed` — the `dirty_tree` finding above |
| `rtk proxy "python -m pytest tests/test_integration_06_to_09.py -q …"` (after the conftest fix) | 0 | `38 passed in 124.05s` |
| **`rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"`** | **0** | **`737 passed in 1067.01s (0:17:47)`**; the output file is 12 lines — 11 progress lines plus the summary — so `-rsxX` produced **no** short-summary section |
| `python scripts/sdle.py lint-skill` | NOT_RUN this milestone | no document has been edited since checkpoint 03's 22 PASS / 0 FAIL |
| Python 3.11 / CI | **NOT_RUN** | host is 3.13; branch is local-only. Predict nothing. |

**Suite arithmetic, re-derived:** 729 at checkpoint 03 + **8** new cases in `tests/test_units_governance.py` (158 → 166) = **737**. Confirmed independently: the five-file targeted run collected 398 = 166 + 8 + 71 + 57 + 96. No other per-file count moved — every one of the 13 insertions is a call inside an existing function, adding no test.

## Current failures

**None.**

## Git status / diff summary

- HEAD `4a35a1c`; nothing committed this phase.
- Pre-existing out-of-scope ` M .claude/settings.local.json` untouched.
- Rollback point remains **`475795a`**.

## Unresolved decisions

None. No blocker. The two divergences above are declared, not open.

## Exact resume instruction

Verify against disk before trusting any of the above:

```
rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"              # expect 737
rtk proxy "git diff --numstat 4a35a1c -- tests/"                                # expect zero deletions
rtk proxy "git diff --exit-code 475795a -- .claude/ .github/ tools/ .gitignore" # expect exit 0
```

Then implement **M5** per `docs/transition/phases/T06-plan.md` §D10:

1. `append_audit` gains `review: str | None = None` and `evidence_id: str | None = None`, rendered as **two conditional lines inserted between `**Comments:**` and `**Prev:**`** — never after `**Prev:**` (F9), and never by reusing `decision` (`test_integration_01_happy_path.py` asserts `**Gate Decision:** APPROVED` occurs exactly `len(GATES)` times).
2. The governance facts enter the ledger once per assessment, carrying `proposedLevel`, `deterministicLevel`, `finalLevel` and `loweringAttempted` (N17).
   **Design constraint discovered in M4:** `cmd_init` is on A9's byte-identical list, so the entry **cannot** be emitted there. It is emitted at the first phase movement that consumes the record, and de-duplicated by the record's `executionId`, so re-assessment produces a new entry and repeated advances do not. Record this as a declared divergence from N17's phrase "the first state-writing command" in the handoff.
3. N32 pins byte-identity of the no-review rendering **before** anything depends on it.
4. Re-run the full suite; M5 must end green.
