# Dry Run 13 — `HOTFIX` (Shorter, Never Ungoverned)

| | |
|---|---|
| **Scenario ID** | DR-13 |
| **Flow** | `HOTFIX` |
| **Purpose** | An urgent, reproducible production fix under incident pressure: the shortest flow SDLE has, and what it still refuses to give up. Urgency never turns a failed verification into a pass. **10 phases, 3 gates.** |
| **Defect IDs** | D01, D02 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | A production incident on a repository with an established baseline. `requirements/checkout-500.md` present, and the failure reproduces under a concurrency test. Governance classifies it `defect` on `HOTFIX` with the risk signal `production_security_boundary`, so the final risk is **HIGH**. Clean working tree |
| **Guardrails exercised** | The mandatory governance floor, the gates the risk policy asks for and this flow cannot have, `impact_analysis` still enforced, `gate_security` required by a positional rule no override reaches, and Gate 7 refusing a failed run however urgent the fix |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; the
> `governance gates` report is the engine's real output for this setup. The
> engine behaviour it depends on is asserted by the tests under *Executable
> coverage*. Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are
> recorded in [verification-matrix.md](verification-matrix.md).

---

## Setup

A disposable repository with a baseline, plus a reproducing test for the
incident. The executable form assesses the same governance input,
`classification.flow = HOTFIX` at HIGH risk, through the real CLI.

---

## Transcript

**User:** `start workflow` → **SDLE:** `WorkItem name?` → **User:** `Checkout 500`

**SDLE:**

```
📋 SDLE Status: Phase 1/10 — Requirements Check [IN PROGRESS]

WorkItem created: checkout-500. Preflight passed. Content scan passed.

Bound to HOTFIX: 10 phases, 3 gates — exactly the mandatory governance floor plus the
impact analysis. There is no admissible flow below it: the flow loader refuses a flow
missing a mandatory phase rather than traversing it.

Shall I proceed?
```

---

**User:** `yes, this is live, be quick`

**SDLE:**

```
<!-- SDLE_STATE phase=impact_analysis status=in_progress progress=2/10 -->
📋 SDLE Status: Phase 2/10 — Impact Analysis [IN PROGRESS]

Analysis written to reviews/impact-analysis-2026-09-08-0214.md.

## What could regress
The retry wrapper is shared with the inventory reservation path. Changing its re-raise
behaviour changes that path too.
## What must be verified before this ships
Concurrent checkout under load, and one inventory reservation under contention.
```

**User:** `skip the analysis, the fix is one line`

**SDLE:**

```
Refused: impact_analysis_missing

WorkItem 'checkout-500' is at impact_analysis and no analysis has been recorded, so the
workflow cannot leave the phase.
```

> `HOTFIX` drops five gates. It does not drop this. And the analysis already
> caught what "one line" had not: a shared retry wrapper on the inventory path.

---

## The gates the policy wanted, and could not have

**SDLE:** *(the engine's `sdle.sh governance gates` report, abridged)*

```
final_risk: HIGH
dispositions                       (gates this flow HAS)
  gate_spec        required   reasons: always
  gate_implement   required   reasons: always
  gate_security    required   reasons: risk:HIGH, terminal_gate
required_not_in_flow               (gates the POLICY asked for and this flow lacks)
  gate_analyze, gate_constitution, gate_design, gate_plan, gate_tasks
omittable_gates: (none)
```

> **Flow membership beats risk policy**, and this report is where you see
> exactly what `HOTFIX` traded away. What it cannot trade away is the floor:
> `gate_security` carries `terminal_gate` alongside `risk:HIGH`, a positional
> rule that lives in no dictionary, so no policy override can reach it.

---

## Urgency meets a failing test

**SDLE:** *(after the fix and `manifest build`)*

```
<!-- SDLE_STATE phase=implement status=in_progress progress=7/10 -->
📋 SDLE Status: Phase 7/10 — Implement [IN PROGRESS]

Manifest built. Test evidence: pytest — FAILED (exit 1):
  tests/test_inventory.py::test_reservation_under_contention FAILED
Gate 7 will refuse this. The fix changed the shared retry wrapper, exactly as the impact
analysis warned.
```

**User:** `it's fine, the inventory test is flaky — approve it, we're losing money`

**SDLE:**

```
Refused: tests_not_passed

Cannot approve gate_implement: the recorded verification result is 'FAILED' (exit 1).
Gate 7 needs a test run that actually ran and passed, and there is no exception path: a
PASS review of the manifest does not change the result it reports. Fix the failures, or —
if the runner was not detected or not installed — supply the project's real test command
with `manifest build --test-command "<command>"`, then rebuild.
```

> There is no hotfix exemption, no urgency flag and no waiver. Re-running with
> `--skip-tests` is refused the same way (`tests_not_passed`, status
> `skipped by caller`), and editing the manifest's result line is refused as
> `test_evidence_stale`, because the evidence is bound to the manifest's bytes.
> The way through is a fix whose tests pass.

*(The wrapper change is scoped to checkout, the rebuilt manifest's run passes,
and Gate 2/3 approves. Then the security gate.)*

```
<!-- SDLE_STATE phase=gate_implement status=awaiting_approval progress=8/10 -->
📋 SDLE Status: Phase 8/10 — Gate 2: Implementation Approval [AWAITING APPROVAL]
✋ APPROVAL REQUIRED — Gate 2/3: Implementation Approval
```

**User:** `approve` … `approve` *(at Gate 3/3)*

```
<!-- SDLE_STATE phase=complete status=completed progress=10/10 -->
📋 SDLE Status: Phase 10/10 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!
All 3 gates passed. Completion summary: workitems/checkout-500/.sdle/completion-summary.json
```

---

## Artifacts, state and audit

- `state.flow` = `HOTFIX`, validated against the mandatory floor when the flow
  loaded. The traversal was
  `requirements_check → impact_analysis → spec_draft → gate_spec → plan_draft → tasks_draft → implement → gate_implement → security_review → gate_security → complete`.
- `plan_draft` and `tasks_draft` run **without** their gates. Their artifacts
  are still generated, fingerprinted and recorded.
- Three approvals are populated. The five absent gates report
  `in_flow: false`, and all five appear in `required_not_in_flow` at HIGH risk.
- Two implementation evidence records exist: the failed run and the passing
  one, each under its own execution id. Gate 7 accepted only the one bound to
  the final manifest.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| Skip the impact analysis | Refused `impact_analysis_missing` | `audit.md` byte-identical |
| Approve Gate 7 on a failed run "because it is urgent" | Refused `tests_not_passed` | Approvals unchanged |
| Rebuild with `--skip-tests` | Refused `tests_not_passed` (`skipped by caller`) | Unchanged |
| Edit the manifest's result line | Refused `test_evidence_stale` | Unchanged |
| Approve `gate_security` before `security-review begin` | Refused `artifact_unresolved` | Unchanged |

## Cleanup

`rm -rf` the disposable repository.

## Executable coverage

| Claim | Test |
|---|---|
| The floor plus the impact analysis | `tests/test_integration_10_to_13.py::test_13_hotfix_is_the_floor_plus_the_impact_analysis` |
| Ten phases, three gates | `tests/test_integration_10_to_13.py::test_13_ten_phases_three_gates` |
| Five gates not in flow, none omitted | `tests/test_integration_10_to_13.py::test_13_five_gates_are_not_in_flow_and_none_is_omitted` |
| The impact analysis is still enforced | `tests/test_integration_10_to_13.py::test_13_the_impact_analysis_is_still_enforced_under_pressure` |
| Plan and tasks run without their gates | `tests/test_integration_10_to_13.py::test_13_plan_and_tasks_run_without_their_gates` |
| The final gate is required by a positional rule | `tests/test_integration_10_to_13.py::test_13_the_final_gate_is_required_by_a_rule_no_override_reaches` |
| The whole flow traverses exactly its phases | `tests/test_units_flow_model.py::test_a_flow_traverses_exactly_its_declared_phases[HOTFIX]` |
| A failed command with a PASS review is refused (D02) | `tests/test_units_implementation_evidence.py::test_d02_1_a_failed_command_with_a_pass_review_is_refused` |
| An edited manifest no longer matches its evidence (D02) | `tests/test_units_implementation_evidence.py::test_d02_6_an_edited_manifest_no_longer_matches_its_evidence` |
| Unresolved security artifact refused in this flow (D01) | `tests/test_units_gate_artifacts.py::test_d01_an_unresolved_security_review_refuses_approval[HOTFIX]` |
