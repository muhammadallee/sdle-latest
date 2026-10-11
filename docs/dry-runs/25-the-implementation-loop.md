# Dry Run 25 — The Bounded Implementation Loop

| | |
|---|---|
| **Scenario ID** | DR-25 |
| **Flow** | `GREENFIELD` |
| **Purpose** | Inside the implement phase, a bounded loop of implement, reconcile, tree-bound evidence, independent review, converge and trace runs until the implementation is ready for the gate or the engine says why it is not. It stops at the existing human gate and never approves it. |
| **Defect IDs** | — |
| **Runtime** | SDLE on `enh/requirements-package-loop`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | The WorkItem of DR-23 and DR-24, standing at `implement` with the base pinned by `implement preflight` and its task list approved. |
| **Guardrails exercised** | The loop is a recorder and referee, not a driver; every step needs the one before it and no output is recorded twice; a snapshot of a tree that moved is stale and rebuilt; the only change to an approved task list the loop accepts is a tick or an appended convergence section; there is one completion predicate, shared with the gate; the loop stops with a reason and a next action and never approves a gate |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> are illustrative. The engine behaviour it depends on is asserted by the tests
> under *Executable coverage*. Their results — **PASS**, **FAIL**,
> **BLOCKED** or **NOT RUN** — are recorded in
> [verification-matrix.md](verification-matrix.md).

---

## Setup

The WorkItem is standing at the implement phase and the user has asked Claude
to repair the implementation until it is ready for the gate.

---

## Transcript

### Part 1 — A run begins

<!-- SDLE_STATE phase=implement status=in_progress progress=17/20 -->
📋 SDLE Status: Phase 17/20 — Implement [IN PROGRESS]

**Claude:** I will run the implementation loop. Three iterations at most, the
policy's limit.

**SDLE:**

```
loop begin

  run         1
  limit       3         ← the pinned policy's, never raised by a repository
  base        4e1c9a0
  tasks       taken from what Gate 5 approved
  next        implement
```

### Part 2 — One iteration, each step checked

**Claude:** Implemented over the tasks; tick T001. `tasks reconcile`:

```
tasks reconcile   1 task ticked, no convergence section, baseline moved for
                  gate_tasks and gate_analyze
```

> **The one change the loop accepts to an approved task list.** A tick, or an
> appended `## Phase N: Convergence` section, verified structurally against the
> last accepted snapshot and audited. Rewording a task, removing one or editing
> anything else would have stopped the run `tasks_drift` for a person.

**Claude:** Built the evidence with the test command writing its JUnit report
to the evidence directory, then asked `sdle-code-review` for an independent
review of the diff, the package files and the **raw** evidence, and recorded it
as a `code-review`. Then I ran converge: it left `tasks.md` unchanged.

**SDLE:** *(each of `loop step --step manifest|review|converge|trace` is
recorded in turn; run out of order, repeated, or on a tree that has changed
since the evidence, it is refused.)*

### Part 3 — The result

**Claude:** `loop record`:

```
loop record

  iteration   1
  status      stopped
  stopReason  ready_for_gate
  next        Advance to the implementation gate and present it. The loop never
              approves, omits or skips a gate.
```

> **Ready for a human, not approved.** The WorkItem is still at `implement`,
> no approval was recorded, and the engine's completion predicate and the
> gate's are the same function: whatever the loop reported unmet, the gate
> refuses with the first of it.

**Claude:** *(advances, and shows what the gate will be shown.)*

<!-- SDLE_STATE phase=gate_implement status=awaiting_approval progress=18/20 -->
📋 SDLE Status: Phase 18/20 — Gate 8: Implementation Approval [AWAITING APPROVAL]

*(Scope coverage from the trace; the tree digest and the base; the test result;
no open blocking findings; **AC-001 only `suite-pass-unmapped`**, shown apart and
never as verified; the stop reason.)*

**User:** `reject — the error path is wrong`

**SDLE:** *(the existing remediation path, with its own counter; a new
`loop begin` then opens run 2 with its own limit.)*

### Part 4 — When the loop stops for something other than ready

**Claude (a later attempt):** The same unverified criterion and the same findings
as the last iteration; appending tasks is not progress.

**SDLE:** `loop record` → `stopReason: no_progress`. *(An unavailable runner is
`environment_blocker`, never a pass; a deleted test file is
`test_expectation_change`, a person's decision; the limit is `limit_exhausted`.
Each comes with a next action.)*

---

## Artifacts, state and audit

| Path | Contains |
|---|---|
| `workitems/<id>/.sdle/implementation-loop.json` | the runs, their limit, each iteration's recorded steps with their snapshots, the progress digest and the stop reason; engine-written and self-digested |
| `workitems/<id>/.sdle/evidence/tasks-snapshot-*.json` | the task list as last accepted, content-addressed |
| `workitems/<id>/.sdle/evidence/implementation-*.json` | the tree-bound evidence each manifest step recorded; never deleted |
| `workitems/<id>/.sdle/audit.md` | `tasks_reconciled` entries, and `tasks_snapshot_established` where no task gate approved the list |

---

## Negative cases

| What is tried | What happens |
|---|---|
| A step out of order, or a second `converge` with no `implement` between | `Refused: loop_step_out_of_order` |
| Recording the same evidence or review twice | `Refused: loop_step_duplicate` |
| A step after the tree changed | `Refused: loop_snapshot_stale` |
| A task list changed beyond ticks and convergence sections | `Refused: tasks_drift`, the run is stopped |
| Reconciling while another artifact has drifted | `Refused: reconcile_unrelated_drift` |
| `loop begin` outside implement, or with no pinned base | `Refused: loop_wrong_phase`, `Refused: loop_no_base` |
| A code review given to the loop with no structured findings (an empty list passes) | `Refused: loop_review_unstructured` |
| A blocking finding marked accepted by a non-human actor | `Refused: review_waiver_requires_human` |
| The code review's evidence missing or disagreeing with the ledger | exit 3 `review_evidence_invalid` |
| A loop record the engine did not write | exit 3 `loop_record_invalid` |
| `gate approve` while the last converge appended tasks | `Refused: loop_converge_pending` |

---

## Cleanup

Delete the disposable repository.

---

## Executable coverage

| Claim | Test |
|---|---|
| The loop is ready only through the predicate the gate uses | `tests/test_units_loop.py::test_as20_the_loop_is_ready_only_through_the_predicate_the_gate_uses` |
| The gate refuses with the first thing the loop reports unmet | `tests/test_units_loop.py::test_as20_the_gate_refuses_with_the_first_thing_the_loop_reports_unmet` |
| A second converge without implement between is refused | `tests/test_units_loop.py::test_as21_a_second_converge_without_implement_between_is_refused` |
| A change outside the policy stops the loop | `tests/test_units_loop.py::test_as22_a_change_outside_the_policy_stops_the_loop_with_tasks_drift` |
| The same failures twice stop the loop with no progress | `tests/test_units_loop.py::test_as23_the_same_failures_twice_stop_the_loop_with_no_progress` |
| The iteration limit stops the loop with a reason and a next action | `tests/test_units_loop.py::test_as24_the_iteration_limit_stops_the_loop_with_a_reason_and_a_next_action` |
| Resuming neither duplicates nor trusts a stale snapshot | `tests/test_units_loop.py::test_as25_resuming_after_an_interruption_neither_duplicates_nor_trusts_a_stale_snapshot` |
| An unavailable runner stops the loop, never a pass | `tests/test_units_loop.py::test_as26_an_unavailable_runner_stops_the_loop_never_a_pass` |
| A deleted test file stops the loop for a person | `tests/test_units_loop.py::test_as27_a_deleted_test_file_stops_the_loop_for_a_human` |
| A rejection follows the existing remediation path | `tests/test_units_loop.py::test_as28_a_human_rejection_follows_the_existing_remediation_path` |
| The loop never approves | `tests/test_units_loop.py::test_as29_the_loop_never_approves_and_ready_means_ready_for_a_human` |
| Nothing the loop runs can reach an approval | `tests/test_units_loop.py::test_no_loop_function_can_reach_an_approval` |
| A review with no structured findings is refused at the step; an empty list passes | `tests/test_units_loop.py::test_m2_a_review_without_structured_findings_is_refused_at_the_step` |
| An iteration past an unstructured review cannot close; stop then begin works | `tests/test_units_loop.py::test_m2_an_iteration_already_past_an_unstructured_review_cannot_close` |
| A later review of another type does not hide a blocker | `tests/test_units_loop.py::test_m1_a_later_review_of_another_type_does_not_hide_a_blocker` |
| Missing or malformed review evidence is refused, never empty | `tests/test_units_loop.py::test_m1_missing_or_malformed_review_evidence_is_refused_not_empty` |
| Evidence that disagrees with the ledger is refused | `tests/test_units_loop.py::test_m1_evidence_that_disagrees_with_the_ledger_is_refused` |
| A non-human actor cannot record a waiver, and the refusal writes nothing | `tests/test_units_artifact_review.py::test_m3_a_non_human_actor_cannot_record_an_accepted_blocking_finding` |
| A human review can record it | `tests/test_units_artifact_review.py::test_m3_a_human_review_can_record_the_waiver` |

Result: **PASS**.
