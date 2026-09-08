# T06 Implementation Checkpoint — Attempt a01 / Checkpoint 06

**Phase:** T06
**Attempt:** 01 (resumed after an API-session interruption; §24.6 interruption, **not** a verification FAIL, so the attempt number is unchanged)
**Milestones completed:** **M6** (the review regime's red window, closed) and **M7** (the phase-level proofs).

> **The M6 red window is CLOSED.** It was **65 failed / 717 passed**, verified in this context by a full run *before any edit*, and it closed with **setup calls only**. No assertion was relaxed, removed, skipped, xfailed or deleted.

## Objective currently being worked

M6 and M7 are complete. Next objective is **M8**: the D13 prompt layer, `README.md`, the Reference Guide, `ADR-003`, then the full suite, `lint-skill` (re-run after **each** document edit), `validate.py`, the A1–A24 matrix, `T06-handoff-a01.md` and `progress.md` → `IMPLEMENTED`.

Anti-contradiction **row 4** — the honest rewrite of `test_no_lifecycle_command_reads_the_repository_configuration` — is **already applied and passing** (see below); it was scheduled for M8 but is test-only and was safe to land beside M7.

## The red window, derived from disk rather than inherited

The first action in this context was a full suite run against the tree as found:

`rtk proxy "python -m pytest -q -p no:cacheprovider --tb=no -rf"` → runner raw exit **0**; pytest reported **`65 failed, 717 passed in 1158.11s (0:19:18)`**. Tallied from the `FAILED` lines with a Python one-liner:

| File | Failures |
|---|---|
| `tests/test_integration_06_to_09.py` | 26 |
| `tests/test_integration_02_to_05.py` | 17 |
| `tests/test_units_workitem_runtime.py` | 12 |
| `tests/test_units_speckit_binding.py` | 4 |
| `tests/test_units_transitions.py` | 4 |
| `tests/test_units_governance.py` | 2 |

Set-compared against the previous context's captured run: **identical, 65 = 65, zero on either side only**. Every failure is E2 (`review_missing`) reached through a `gate approve` that no longer has a current `PASS` review.

**The two `tests/test_units_governance.py` failures were investigated separately**, as they are in T06's own new file and could have indicated a real interaction. They did not:

- `test_gate_approve_inherits_the_same_clause` asserts `governance_missing`. In `cmd_gate_approve`, `review_precondition` runs **before** `apply_advance`, so E2 now fires first and the case saw `review_missing`. Fixed by satisfying E2 in setup so E1 is the only precondition left standing — which is what the test was written to isolate.
- `test_the_governance_entry_is_written_once_per_assessment` drives a real `gate approve`; it needed the same review its subject-matter does not concern.

Both are setup insertions. Neither assertion moved.

## M6 step 3 — the derived set, 35 setup calls plus 6 imports, 6 files

All are **setup calls only**. Each is TP-003 **category 2**. Each is one `review_for_gate(<view>, <gate>)` line, plus one `from test_units_artifact_review import review_for_gate` per file — the cross-module pattern the suite already uses for `run_happy_path`. **`tests/conftest.py` gained nothing** (row 5 holds: `grep -c review_for_gate tests/conftest.py` = **0**).

| File | Sites | Calls |
|---|---|---|
| `tests/test_integration_02_to_05.py` | `at_gate_spec`; `drifted`; `test_04_reapproval_rebaselines_and_resumes`; `test_04_multiple_drifted_gates_queue_most_upstream_first` (2); `test_04_drift_reapproval_walks_the_queue_one_at_a_time` (2); `test_04_drift_includes_a_git_diff_for_tracked_artifacts` | 8 |
| `tests/test_integration_06_to_09.py` | `at_implement` (the 3-gate loop, then `gate_tasks`, `gate_analyze`, `gate_design`); `test_06_gate_seven_accepts_a_built_manifest`; `test_07_staleness_is_scoped_to_recorded_artifact_paths`; `at_gate_plan` (2) | 8 |
| `tests/test_units_speckit_binding.py` | `drive_full_workflow` (8); `test_n3_a_gate_refuses_another_workitems_artifact`; `test_migrated_in_flight_workflow_refuses_its_next_speckit_gate`; `test_feature_resolve_recovers_a_migrated_workflow_without_drift` (2) | 12 |
| `tests/test_units_transitions.py` | `test_gate_approve_records_baseline_and_advances`; `test_gate_approve_stores_comments`; `test_gate_approve_writes_audit_entry_with_decision`; `test_final_gate_completes_the_workflow` | 4 |
| `tests/test_units_workitem_runtime.py` | `legacy_workflow` (the seed run whose runtime becomes `.workflow/`) | 1 |
| `tests/test_units_governance.py` | the two cases above | 2 |

Three refusal cases needed **no** insertion, and that is itself evidence the enforcement is ordered correctly: `drift_pending` fires before `review_precondition` in `_approve_drift`; `manifest_incomplete` and `feature_outside_workitem` fire before it in `cmd_gate_approve`. Each of those tests failed only because its *fixture* approved an earlier gate.

## M7 — the phase-level proofs, written after the engine shipped

Appended to `tests/test_units_governance.py`:

1. **`test_governance_changes_no_lifecycle_behaviour`** — A17 + N13's differential half + N20(d). Four scratch repositories, cloned **before** any run so they genuinely start identical, differing only in the governance record: baseline (`LOW`/enhancement/ITERATIVE), classification-only, risk-only (`CRITICAL`), and both. Asserts all four traversals equal `EXPECTED_TRAVERSAL`; identical ordered lifecycle audit events modulo the two event kinds T06 adds; identical approvals; identical `artifact_shas` key sets; and — clause 0 — that the variants actually took effect (`finalLevel` `LOW`/`LOW`/`CRITICAL`/`CRITICAL`, three distinct classification types), so nothing passes vacuously. Clause 3 shows the would-be required gate set **does** differ across risk (A18), while the traversal does not.
   The variant is injected by overriding the *fixture* method's default document for the duration of the run. **No engine function is patched**; every command still goes through the real CLI.
2. **`test_a_corrupt_governance_record_is_an_integrity_failure`** (3 parametrised cases) — pins the phase's **one declared new exit-3 path**, `governance_record_invalid`, which checkpoint 02 declared as a divergence from A14 and left unpinned. A14 must be judged against a behaviour, not a narrative. `EXIT_INTEGRITY = 3` was added to the file's exit-code constants.

N20(b)(c), N28 and N30 were already present from earlier milestones and were re-checked by name rather than rewritten (`test_no_phase_movement_function_consults_the_would_be_gate_set`, `test_the_phase_movement_prefixes_actually_match_something`, `test_no_stored_freshness_flag_exists_in_a_record`, `test_a_hand_planted_freshness_flag_changes_nothing`, `test_the_approval_baseline_and_the_review_ledger_never_mix`, `test_the_artifact_shas_writer_set_is_unchanged`).

## Anti-contradiction row 4 — the honest rewrite, landed early

`test_no_lifecycle_command_reads_the_repository_configuration` matched on function-NAME PREFIXES, which was the wrong shape once the lifecycle genuinely reads policy: a helper named outside `cmd_gate*`/`cmd_advance*`/`cmd_approve*`/`cmd_init*` could have read the boundary and the test would still have passed. The rewrite is **strictly stronger** and keeps the original clause:

- (a) `governance_policy_file` has exactly **one** reader in the whole engine — `read_governance_policy`. Derived from disk, not assumed.
- (b) the `config_file` reader set is closed over the whole engine, and no `cmd_*` outside the `config` group is in it.
- (c) the original prefix clause, kept verbatim in effect, so `test_the_lifecycle_command_prefixes_actually_match_something` stays load-bearing rather than being orphaned.

`rtk proxy "python -m pytest tests/test_units_repo_config.py -q -k 'lifecycle_command or prefixes_actually or reference_set or configuration_commands'"` → **`4 passed, 67 deselected in 1.65s`**.

## Suite arithmetic, re-derived in this context

Baseline re-derived from a **pristine `git archive 475795a`** extracted to scratch: **`569 tests collected in 2.08s`**, with per-file counts summing to 569.

| Term | Count | Source |
|---|---|---|
| baseline at `475795a` | 569 | pristine archive, `--collect-only -q` |
| `tests/test_units_governance.py` (new) | 175 | after M7's 4 added cases |
| `tests/test_units_artifact_review.py` (new) | 40 | derived below |
| `tests/test_units_repo_config.py` parametrisation growth | **+2** | see note |
| **expected total** | **786** | to be confirmed by the M8 full run |

The **+2** is the only per-file delta in a modified file, and it is not a new test function. Node-id diff against the pristine baseline shows exactly `test_lifecycle_state_under_the_repository_boundary_is_an_error[governance.json]` and `[reviews.json]`: anti-contradiction **row 3** added two runtime member names, and that test is parametrised over them, so the leak detector now runs two more cases. Every other modified file's count is unchanged, because every insertion is a call inside an existing function.

At the M6 tree the total was **65 + 717 = 782** = 569 + 2 + 171 + 40, which is where the artifact-review file's **40** comes from; M7 then added 1 + 3 = 4.

## Tests actually run

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider --tb=no -rf"` (before any edit) | 0 | **`65 failed, 717 passed in 1158.11s (0:19:18)`** — the inherited red window |
| `rtk proxy "python -m pytest tests/test_units_transitions.py tests/test_units_governance.py -q … --tb=short -rf"` | 0 | **`195 passed in 164.13s`** |
| `rtk proxy "python -m pytest tests/test_integration_02_to_05.py tests/test_integration_06_to_09.py tests/test_units_speckit_binding.py tests/test_units_workitem_runtime.py -q … --tb=short -rf"` | 0 | **`180 passed in 516.20s (0:08:36)`** — all 63 non-governance failures, plus their whole files |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (M6 confirmation) | **0** | **`782 passed in 1381.25s (0:23:01)`**; the captured output is 12 lines, so `-rsxX` produced **no** short-summary section — zero skips, xfails, errors |
| `rtk proxy "python -m pytest tests/test_units_governance.py -q -k governance_changes_no_lifecycle --tb=long"` | 0 | **`1 passed, 171 deselected in 46.53s`** — the A17/N13/N20(d) differential, green first run |
| `rtk proxy "python -m pytest tests/test_units_governance.py -q -k corrupt_governance_record --tb=short"` | 0 | **`3 passed, 172 deselected in 6.00s`** |
| `rtk proxy "python -m pytest tests/test_units_repo_config.py -q -k 'lifecycle_command or …'"` | 0 | **`4 passed, 67 deselected in 1.65s`** — row 4 |
| `python scripts/sdle.py lint-skill` | 0 | **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 15 migration rows`, `all four locations report v1.15` — baseline taken **before** any document edit; M8 re-runs it after each |
| Python 3.11 / CI | **NOT_RUN** | host is 3.13; branch is local-only. No outcome predicted. |

**Evidence-attribution note, stated rather than glossed.** The M6 confirmation run was launched against the M6 tree. Two **test-only** edits landed on disk while it was executing: M7's appended cases in `tests/test_units_governance.py` and row 4's body rewrite in `tests/test_units_repo_config.py`. Neither can affect that run — pytest had already imported both modules, no test reads test-file source, and `scripts/sdle.py` was not touched — so the figure describes the M6 tree exactly. Both later edits were verified by their own targeted runs above, and the M8 full run covers the whole tree.

## Acceptance criteria already confirmed in this context

- **A5** `git diff --exit-code 475795a -- <must-not-change list>` → **raw exit 0**.
- **A7** `RUNTIME_FREE_COMMANDS` = the `475795a` frozenset (7 members) plus exactly `"governance"` = **8**, nothing removed (both texts read side by side).
- **A8** `.sdle/policies/` contains only `.gitkeep`.
- **A9** AST extract-and-compare against `475795a`: **24/24** named definitions byte-identical (19 functions + `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS`, `CONFIRMABLE`, `INJECTION_PATTERNS`, `SECRET_PATTERNS`). `cmd_gate_approve` and `_approve_drift` each **+1 line, 0 removed**; `append_audit` +11 with 1 line reformatted (`**Prev:**` gained a `+` concatenation prefix and is still the **last** rendered line); `apply_advance` +6 with 4 docstring lines rewritten.
- **A14** the whole `scripts/sdle.py` + `tests/` diff plus both new files contain exactly **two** added `raise IntegrityError` lines, both in `read_governance_record` (`governance_record_invalid`) — the single declared divergence, now pinned by a test.
- **A20/A22** grep over the 3,915 added lines: `speckit-` **0**, `/speckit.` **0**, `conditional gate` **0**, `gate_policy` **0**, `flow_selection` **0**, `flow routing` **0**, `baseline.json` **0**, `brownfield` **0**, `discovery` **0**. `subagent` matched **4** lines, all inside `test_t06_creates_no_subagent` and its docstring; `sdle-architect` matched **8**, all recorded actor **strings** in T06's own tests. Both quoted rather than asserted empty.

## Files changed

`git diff --numstat 4a35a1c -- scripts/ tests/` (run in this context, after M6+M7+row 4):

```
1494    6   scripts/sdle.py
38      0   tests/conftest.py
16      0   tests/test_integration_01_happy_path.py
13      0   tests/test_integration_02_to_05.py
14      0   tests/test_integration_06_to_09.py
14      0   tests/test_units_repo_config.py   (before row 4)
18      0   tests/test_units_speckit_binding.py
6       0   tests/test_units_transitions.py
4       0   tests/test_units_workitem.py
5       0   tests/test_units_workitem_resolution.py
3       0   tests/test_units_workitem_runtime.py
```

Removed lines across the whole tracked diff, enumerated rather than summarised: **6 in `scripts/sdle.py`** (the `**Prev:**` line reformatted, `bound.completion_file,` reformatted when two members were appended, and 4 rewritten `apply_advance` docstring lines) and, after row 4, **4 in `tests/test_units_repo_config.py`** (3 docstring lines and one `for` line, all inside the one authorised rewrite). **No other test file has a single removed line.** Zero `D`, zero `R`.

Untracked: `tests/test_units_governance.py` (**175**), `tests/test_units_artifact_review.py` (**40**), `docs/transition/phases/T06-checkpoint-a01-0{1..6}.md`.

**No document, prompt file or constant table has been edited yet.** `SKILL.md`, both modules, both slash commands, `README.md` and the Reference Guide are byte-identical to `4a35a1c`; M8 owns them.

Pre-existing out-of-scope ` M .claude/settings.local.json` untouched.

## Current failures

**None known.** Everything run in this context after the insertions is green; the M8 full run is the whole-tree confirmation.

## Unresolved decisions

None. No blocker.

Carried declared divergences (all previously recorded, none re-opened): the governance ledger entry lands at the first *phase movement* rather than at `cmd_init` (A9 requires `cmd_init` byte-identical); `tests/test_units_repo_config.py` and `tests/test_units_workitem.py` are in the derived setup-call set although the plan's *enumeration* of candidate files omitted them; `governance_record_invalid` is exit 3.

## Exact resume instruction

Verify against disk before trusting any of the above:

```
rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"      # expect 786
rtk proxy "git diff --numstat 4a35a1c -- tests/"
rtk proxy "git diff --exit-code 475795a -- .claude/hooks/ .claude/settings.json .claude/agents/ .claude/skills/sdle/templates/ .github/ tools/ .gitignore"
python scripts/sdle.py lint-skill
```

Then implement **M8** per `docs/transition/phases/T06-plan.md` §D13. Patch scripts are already written and **anchor-validated** (`--check` passes) in the scratchpad:

- `m8_prompt.py` — 8 edits across `SKILL.md` (Step 1 governance paragraph), `modules/phase-execution.md` (the **Governed Artifact Review (MANDATORY — before every gate)** block plus one self-check item), `modules/gate-protocol.md` (the review-status step and the prompt's `Review:` line), `.claude/commands/sdle-start.md` and `.claude/commands/sdle-approve.md`. Supports `--only <n>` so `lint-skill` can be re-run after **each** file.
  **`SKILL.md` is CRLF on this checkout and every other prompt file is LF** — the script preserves whichever the file already uses. Writing LF into `SKILL.md` would turn the diff into the whole file.
- `m8_docs.py` — `README.md` (a governance/review section after "Repository configuration") and `docs/SDLE-Reference-Guide.md` (§12.4, three §14 compliance rows, an Appendix C table).
- `ADR-003.md` — the finished ADR body, to be copied to `docs/architecture/ADR-003-governance-inputs-and-artifact-review.md`.

**All three were checked against N23's needle set** (12 risk-signal ids plus the 5 underscored check ids, derived from `GOVERNANCE_POLICY_BUILTIN` by AST) and contain **none**, so `test_no_policy_default_value_is_restated_outside_sdle_py` stays green — note that it searches `README.md`, `CLAUDE.md`, the Reference Guide, `.claude/skills/`, `.claude/commands/`, `.claude/hooks/`, `.sdle/` **and `docs/architecture/`**.

**Do not edit any prompt file while a suite run is in flight:** `tests/test_lint_skill.py` runs `lint-skill` against the repository's own `SKILL.md` on disk, and `tests/test_units_speckit_binding.py` reads `modules/phase-execution.md`.

Then: full suite, `lint-skill` after each document edit, `python tools/transition/validate.py`, the A1–A24 matrix, `docs/transition/phases/T06-handoff-a01.md`, and `progress.md` → `IMPLEMENTED` (remember a literal `|` in a table cell makes `validate.py` exit 3).
