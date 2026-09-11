# Dry-Run Verification Matrix

Which executable checks back each transcript, the command that runs them, and
the result they actually produced, on which commit and platform. Every
scenario row's tests are part of all three runs, so R1 · R2 · R3 below means
they passed in each. CI test counts are not readable without a token; the CI
results are step conclusions. A result is
recorded only from a run that happened. A run that was not executed says
**NOT RUN**, never PASS.

The full execution record, including every defect's reproduction and the
red-before-green evidence, is
[`../verification/defect-stabilization-01.md`](../verification/defect-stabilization-01.md).

## Runs

| Run | Commit | Platform | Command | Result |
|---|---|---|---|---|
| R1 | `7561a68` | Windows 10, Python 3.13.0 | `python -m pytest -q` | **PASS** — 2246 passed, 0 failed, 0 errors, 0 skipped (38m56s) |
| R2 | `7561a68` | GitHub Actions `ubuntu-latest`, Python 3.11 | CI `pytest -q` + `lint-skill` + `sh scripts/sdle.sh lint-skill` | **PASS** — every step `success` ([job](https://github.com/muhammadallee/sdle-latest/actions/runs/34526996629/job/103038213266)) |
| R3 | `7561a68` | GitHub Actions `windows-latest`, Python 3.11 | CI `pytest -q` + `lint-skill` + `./scripts/sdle.ps1 lint-skill` | **PASS** — every step `success` ([job](https://github.com/muhammadallee/sdle-latest/actions/runs/34526996629/job/103038213547)) |

## Scenarios

"Contract" means `tests/test_dry_run_contracts.py`, parametrized per
transcript. It recomputes every fraction, gate number and label in the
transcript from the bound flow, checks every refusal against the engine, and
checks that every cited test exists. It applies to all sixteen transcripts.

| Scenario | Flow | Defects | Test nodes | Command | Result |
|---|---|---|---|---|---|
| DR-01 | `GREENFIELD` | D02, D03, D05 | `tests/test_integration_01_happy_path.py`, `tests/test_units_baseline.py::test_n23_only_the_two_declared_flows_establish_a_baseline`, `tests/test_units_implementation_evidence.py::test_d02_8_a_real_passing_pytest_suite_approves`, contract | `python -m pytest tests/test_integration_01_happy_path.py tests/test_dry_run_contracts.py -k "01 or happy"` | R1 · R2 · R3 |
| DR-02 | `GREENFIELD` | — | `tests/test_integration_02_to_05.py::test_02_rejection_records_feedback_and_freezes` and the other `test_02_*`, contract | `python -m pytest tests/test_integration_02_to_05.py -k test_02` | R1 · R2 · R3 |
| DR-03 | `GREENFIELD` | — | `tests/test_integration_02_to_05.py::test_03_skip_is_two_step` and the other `test_03_*`, contract | `python -m pytest tests/test_integration_02_to_05.py -k test_03` | R1 · R2 · R3 |
| DR-04 | `GREENFIELD` | D01 | `tests/test_integration_02_to_05.py::test_04_reapproval_rebaselines_and_resumes` and the other `test_04_*`, `tests/test_units_gate_artifacts.py::test_d01_drift_reapproval_of_a_deleted_artifact_refuses`, contract | `python -m pytest tests/test_integration_02_to_05.py -k test_04` | R1 · R2 · R3 |
| DR-05 | `GREENFIELD` | D05 | `tests/test_integration_02_to_05.py::test_05_every_injection_pattern_fires` and the other `test_05_*`, contract | `python -m pytest tests/test_integration_02_to_05.py -k test_05` | R1 · R2 · R3 |
| DR-06 | `GREENFIELD` | D02, D03 | `tests/test_integration_06_to_09.py::test_06_gate_seven_refuses_a_manifest_whose_tests_were_skipped` and the other `test_06_*`, `tests/test_units_manifest_changes.py::test_d03_the_dirty_tree_guard_reads_the_first_status_entry_whole`, contract | `python -m pytest tests/test_integration_06_to_09.py -k test_06` | R1 · R2 · R3 |
| DR-07 | `GREENFIELD` | D05 | `tests/test_integration_06_to_09.py::test_07_edited_audit_halts_until_rebaselined` and the other `test_07_*`, `tests/test_units_documented_commands.py::test_the_position_check_catches_the_forms_that_were_wrong`, contract | `python -m pytest tests/test_integration_06_to_09.py -k test_07` | R1 · R2 · R3 |
| DR-08 | `GREENFIELD` | — | `tests/test_integration_06_to_09.py::test_08_restart_is_two_step_and_rolls_back` and the other `test_08_*`, contract | `python -m pytest tests/test_integration_06_to_09.py -k test_08` | R1 · R2 · R3 |
| DR-09 | `GREENFIELD` | D05 | `tests/test_integration_06_to_09.py::test_09_missing_speckit_halts_first` and the other `test_09_*`, `tests/test_units_documented_commands.py::test_preflight_in_a_repository_with_no_workitem_asks_for_one_first`, contract | `python -m pytest tests/test_integration_06_to_09.py -k test_09` | R1 · R2 · R3 |
| DR-10 | `BROWNFIELD_DISCOVERY` | D01, D02 | `tests/test_integration_10_to_13.py::test_10_completion_establishes_the_repository_baseline` and the other `test_10_*`, `tests/test_units_flow_model.py::test_a_flow_traverses_exactly_its_declared_phases`, contract | `python -m pytest tests/test_integration_10_to_13.py -k test_10` | R1 · R2 · R3 |
| DR-11 | `ITERATIVE` (after `BROWNFIELD_DISCOVERY`) | D01, D02 | `tests/test_integration_10_to_13.py::test_11_brownfield_then_iterative_reuses_the_baseline_without_rewriting_it`, `tests/test_units_baseline.py::test_n24_the_second_workitem_does_not_rediscover_the_repository`, `tests/test_units_baseline.py::test_n26_an_invalid_baseline_does_not_authorise_iterative`, `tests/test_units_baseline.py::test_n26_a_stale_baseline_authorises_iterative`, the other `test_11_*`, contract | `python -m pytest tests/test_integration_10_to_13.py -k test_11` | R1 · R2 · R3 |
| DR-12 | `DEFECT_FIX` | D01, D02 | `tests/test_integration_10_to_13.py::test_12_writing_the_analysis_is_not_recording_it` and the other `test_12_*`, `tests/test_units_implementation_evidence.py::test_d02_2_a_real_failing_suite_is_refused`, contract | `python -m pytest tests/test_integration_10_to_13.py -k test_12` | R1 · R2 · R3 |
| DR-13 | `HOTFIX` | D01, D02 | `tests/test_integration_10_to_13.py::test_13_the_final_gate_is_required_by_a_rule_no_override_reaches` and the other `test_13_*`, `tests/test_units_implementation_evidence.py::test_d02_1_a_failed_command_with_a_pass_review_is_refused`, contract | `python -m pytest tests/test_integration_10_to_13.py -k test_13` | R1 · R2 · R3 |
| DR-14 | `GREENFIELD` (D01 cases in all five flows) | D01, D02 | `tests/test_units_gate_artifacts.py`, `tests/test_units_implementation_evidence.py`, contract | `python -m pytest tests/test_units_gate_artifacts.py tests/test_units_implementation_evidence.py` | R1 · R2 · R3 |
| DR-15 | `GREENFIELD` | D03 | `tests/test_units_manifest_changes.py`, `tests/test_integration_06_to_09.py::test_06_security_review_refuses_when_no_ref_pinned`, contract | `python -m pytest tests/test_units_manifest_changes.py` | R1 · R2 · R3 |
| DR-16 | `GREENFIELD` | D04 | `tests/test_units_execution_identity.py`, `tests/test_units_hardening.py::test_t11_n1_two_worktrees_each_complete_a_run_with_independent_ledgers`, contract | `python -m pytest tests/test_units_execution_identity.py` | R1 · R2 · R3 |

## Defects across flows

The shared D01–D04 invariants are exercised across the flows where they apply.
Where a combination cannot occur, the reason is given instead of a fictitious
gate.

| Defect | Applies in | Parametrized over | Not applicable, and why |
|---|---|---|---|
| D01 — unresolved feature directory | every flow (all have `gate_spec`) | `ALL_FLOWS` in `tests/test_units_gate_artifacts.py::test_d01_a_null_feature_reference_refuses_approval` | — |
| D01 — unresolved security review | every flow (all end on `gate_security`) | `ALL_FLOWS` in `tests/test_units_gate_artifacts.py::test_d01_an_unresolved_security_review_refuses_approval` | — |
| D01 — flow omits the producing phase | `ITERATIVE` (no constitution) | `tests/test_units_gate_artifacts.py::test_d01_a_flow_without_the_constitution_needs_no_constitution` | `DEFECT_FIX` / `HOTFIX` omit design too, but no gate asks for those artifacts there |
| D02 — Gate 7 evidence | every flow (`gate_implement` is on the mandatory floor) | Gate 7 is one code path for every flow; the flow drivers cross it with `--test-command` in `tests/test_units_flow_model.py::test_a_flow_traverses_exactly_its_declared_phases` | — |
| D03 — change selection | every flow (`implement` is mandatory) | Flow-independent: `implementation_changes` reads only git and the pinned base | — |
| D04 — execution identity | flow-independent | Governance runs before a flow is bound; reviews and manifests use the same allocator | — |
| D05 — instructions | flow-independent | `tests/test_units_documented_commands.py` scans every prompt file and document | — |
| D06 — transcripts | all five flows | `tests/test_dry_run_contracts.py` over all sixteen transcripts | — |
