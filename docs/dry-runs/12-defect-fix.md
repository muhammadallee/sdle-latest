# Dry Run 12 — `DEFECT_FIX` (Blast Radius Before Specification)

| | |
|---|---|
| **Scenario ID** | DR-12 |
| **Flow** | `DEFECT_FIX` |
| **Purpose** | A reproducible defect in an existing system. `impact_analysis` opens the flow, and the phase cannot be left without a reviewed analysis. The fix is verified by the test that reproduced the defect. **14 phases, 6 gates.** |
| **Defect IDs** | D01, D02 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | A repository with an established baseline. `requirements/login-reset-defect.md` describes a reported bug that reproduces: the project's `test_reset.py::test_login_after_reset` fails today. Governance classifies it `defect` on `DEFECT_FIX`, LOW risk. No feature directory bound. Clean working tree |
| **Guardrails exercised** | The gateless `impact_analysis` phase and its three refusals, `gate_tasks` required by change *type*, no checklist and no design gate, and Gate 7 requiring the reproducing test to pass |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> are illustrative. The engine behaviour it depends on is asserted by the tests
> under *Executable coverage*. Their results — **PASS**, **FAIL**, **BLOCKED** or
> **NOT RUN** — are recorded in [verification-matrix.md](verification-matrix.md).

---

## Setup

A disposable repository with a baseline (complete DR-01 or DR-10 first), plus
a failing regression test that reproduces the defect. The executable form uses
`tests/test_units_flow_model.py::prepare`, which writes, records and reviews
`reviews/impact-analysis-2026-05-26-1430.md` through the real CLI.

---

## Transcript

**User:** `start workflow` → **SDLE:** `WorkItem name?` → **User:** `Login Reset Defect`

**SDLE:**

```
📋 SDLE Status: Phase 1/14 — Requirements Check [IN PROGRESS]

WorkItem created: login-reset-defect. Preflight passed. Content scan passed.

This WorkItem is classified as a defect, so it is bound to DEFECT_FIX: 14 phases,
6 gates. It opens with an impact analysis rather than a specification, and it drops the
checklist and the design phase but *keeps* the tasks gate — a defect always adds
gate_tasks regardless of risk, because "we changed the thing next to the broken thing"
is how a one-line fix becomes an outage.

Shall I proceed?
```

---

**User:** `yes`

**SDLE:**

```
<!-- SDLE_STATE phase=impact_analysis status=in_progress progress=2/14 -->
📋 SDLE Status: Phase 2/14 — Impact Analysis [IN PROGRESS]

Analysis written to reviews/impact-analysis-2026-09-08-1030.md.

# Impact Analysis — Login fails after password reset
## What is broken, and where
`reset_password()` clears the session token but does not re-issue one.
src/auth/reset.py:88. Reproduced by tests/test_reset.py::test_login_after_reset (fails).
## What could regress
Any caller depending on the post-reset token being absent — the mobile client's
silent-refresh path is the one candidate.
## What must be verified before this ships
The reproducing test, plus reset → immediate authenticated request on web and mobile.
```

---

**User:** `looks right, move on to the spec`

**SDLE:**

```
Refused: impact_analysis_missing

WorkItem 'login-reset-defect' is at impact_analysis and no analysis has been recorded, so
the workflow cannot leave the phase. Write the analysis, then `artifact record --phase
impact_analysis --path <file>` and `artifact review --path <file> --type
impact-analysis --result PASS --actor-type agent --actor-name sdle-orchestrator`. Record
the review last — editing the file afterwards makes it stale.
```

> **Writing the file is not recording it.** What the engine can verify is a
> fingerprint and a review, not that somebody read a document. `advance` and
> `skip` both refuse, and the refusal writes nothing.

**SDLE:**

```
Recording the analysis and registering the review.
  artifact record --phase impact_analysis → sha256 1a4db50c…5ecc
  artifact review --type impact-analysis --result PASS → bound to sha256 1a4db50c…5ecc
```

---

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=spec_draft status=in_progress progress=3/14 -->
📋 SDLE Status: Phase 3/14 — Generate Specification [IN PROGRESS]

Generating specification, scoped to the blast radius recorded above...
```

**SDLE:** *(at the specification gate)*

```
✋ APPROVAL REQUIRED — Gate 1/6: Specification Approval

Before the specification, the impact analysis for this WorkItem, in full:
[... reviews/impact-analysis-2026-09-08-1030.md re-displayed ...]

# Login Reset Defect — Specification
[... abridged ...]
```

> **The rest of the flow**, with its gate numbers:
>
> | Gate | Phase | Progress | In GREENFIELD this is |
> |---:|---|---|---|
> | 1/6 | `gate_spec` | 4/14 | Gate 2 of 8 |
> | 2/6 | `gate_plan` | 6/14 | Gate 3 of 8 |
> | 3/6 | `gate_tasks` | 8/14 | Gate 4 of 8 |
> | 4/6 | `gate_analyze` | 10/14 | Gate 5 of 8 |
> | 5/6 | `gate_implement` | 12/14 | Gate 7 of 8 |
> | 6/6 | `gate_security` | 14/14 | Gate 8 of 8 |

---

**SDLE:** *(at the implementation gate)*

```
<!-- SDLE_STATE phase=gate_implement status=awaiting_approval progress=12/14 -->
📋 SDLE Status: Phase 12/14 — Gate 5: Implementation Approval [AWAITING APPROVAL]

✋ APPROVAL REQUIRED — Gate 5/6: Implementation Approval

# Implementation Manifest
Evidence: workitems/login-reset-defect/.sdle/evidence/implementation-muh-20260908T114000Z-706077af.json

## Changed/Added Files
M src/auth/reset.py
M tests/test_reset.py

## Test Evidence
Runner: pytest
Command: python -m pytest -q
Result: passed (exit 0)
[... abridged ...]
```

*(The focused correction: two files, measured from the pinned base. The test
that reproduced the defect now passes, and Gate 7's precondition read that
from the evidence record before the prompt was shown. Had the suite still
failed, the gate would refuse `tests_not_passed`, and a PASS review of the
manifest would not change that.)*

**User:** `approve` … `approve` *(at Gate 6/6)*

```
<!-- SDLE_STATE phase=complete status=completed progress=14/14 -->
📋 SDLE Status: Phase 14/14 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!
All 6 gates passed. Completion summary: workitems/login-reset-defect/.sdle/completion-summary.json
```

---

## Artifacts, state and audit

- `state.flow` = `DEFECT_FIX`. The traversal was
  `requirements_check → impact_analysis → spec_draft → gate_spec → plan_draft → gate_plan → tasks_draft → gate_tasks → analyze → gate_analyze → implement → gate_implement → security_review → gate_security → complete`.
- `reviews/impact-analysis-2026-09-08-1030.md` was recorded once and reviewed
  once. The review entry names the SHA it reviewed, permanently.
- Six approvals are populated. `gate_constitution` and `gate_design` stay
  null, with `in_flow: false`.
- No baseline is written: `DEFECT_FIX` does not establish one.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| Leave `impact_analysis` with the file written but not recorded | Refused `impact_analysis_missing` | `audit.md` byte-identical |
| Recorded but not reviewed | Refused `impact_analysis_missing` | Unchanged |
| Reviewed, then edited | Refused `impact_analysis_missing` (the review is stale) | Unchanged |
| Gate 7 with the reproducing test still failing | Refused `tests_not_passed` | Unchanged |
| Approve `gate_spec` before `feature resolve` | Refused `artifact_unresolved` | Unchanged |

## Cleanup

`rm -rf` the disposable repository.

## Executable coverage

| Claim | Test |
|---|---|
| The flow opens on the impact analysis | `tests/test_integration_10_to_13.py::test_12_the_flow_opens_on_the_impact_analysis` |
| Writing is not recording | `tests/test_integration_10_to_13.py::test_12_writing_the_analysis_is_not_recording_it` |
| Recording alone does not lift the refusal | `tests/test_integration_10_to_13.py::test_12_recording_alone_does_not_lift_the_refusal` |
| An edit after review re-arms the refusal | `tests/test_integration_10_to_13.py::test_12_editing_after_the_review_re_arms_the_refusal` |
| No design gate | `tests/test_integration_10_to_13.py::test_12_the_design_gate_is_not_in_flow` |
| The tasks gate survives | `tests/test_integration_10_to_13.py::test_12_but_the_tasks_gate_survives` |
| The whole flow traverses exactly its phases | `tests/test_units_flow_model.py::test_a_flow_traverses_exactly_its_declared_phases[DEFECT_FIX]` |
| A failing suite is refused at Gate 7 (D02) | `tests/test_units_implementation_evidence.py::test_d02_2_a_real_failing_suite_is_refused` |
| Null feature reference refused in this flow (D01) | `tests/test_units_gate_artifacts.py::test_d01_a_null_feature_reference_refuses_approval[DEFECT_FIX]` |
