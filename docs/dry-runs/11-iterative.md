# Dry Run 11 — `ITERATIVE` (Baseline Reuse, After Brownfield Discovery)

| | |
|---|---|
| **Scenario ID** | DR-11 |
| **Flow** | `ITERATIVE` |
| **Purpose** | The flow almost every WorkItem after the first takes. It continues from DR-10: the repository's discovery has happened, and the second WorkItem reuses its baseline with no discovery and no constitution. **16 phases, 7 gates.** It also shows what happens when the baseline is invalid or merely stale. |
| **Defect IDs** | D01, D02 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | The DR-10 repository after its completion: `.sdle/baseline.json` is VALID and was established by WorkItem `reporting-export` (`BROWNFIELD_DISCOVERY`). `requirements/export-csv.md` added. A second WorkItem, `export-csv`, is about to be created. LOW risk. No feature directory bound |
| **Guardrails exercised** | Convergence onto `ITERATIVE` by refusal (`baseline_present`, `baseline_required`), baseline reuse without rewriting, flow-relative gate numbering (`gate_spec` is **Gate 1 of 7**), an inherited constitution, and invalid-vs-stale baselines |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; the
> refusal texts are the engine's own. Hashes are illustrative. The engine
> behaviour it depends on is asserted by the tests under *Executable coverage*.
> Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded
> in [verification-matrix.md](verification-matrix.md).

---

## Setup

Complete DR-10 in a disposable repository, then add
`requirements/export-csv.md`. The executable form drives both WorkItems
through the real CLI in one fixture repository.

---

## Transcript

### Part 1 — The second WorkItem proposes to rediscover

**User:** `start workflow` → **SDLE:** `WorkItem name?` → **User:** `Export CSV`

*(The orchestrator's first governance proposal for the new WorkItem reads the
repository as "existing code, so brownfield". `init` checks the baseline before
anything is created:)*

**SDLE:**

```
Refused: baseline_present

This repository already has a VALID baseline at .sdle/baseline.json, so
BROWNFIELD_DISCOVERY would rediscover what has already been discovered. Contract §14
performs full repository discovery once. Either re-assess this WorkItem as ITERATIVE,
which is what a repository with a baseline is for, or record classification.rediscovery
as true to ask for a deliberate rediscovery.
```

*(Engine: `sdle.sh --workitem export-csv --session 9f42be4d init`. No runtime,
no ledger and no execution record were created for `export-csv`. Discovery
happening once is enforced by refusal, not by anybody remembering.)*

---

### Part 2 — Re-assessed as `ITERATIVE`

**User:** `re-assess it as iterative`

**SDLE:**

```
<!-- SDLE_STATE phase=spec_draft status=in_progress progress=2/16 -->
📋 SDLE Status: Phase 2/16 — Generate Specification [IN PROGRESS]

Bound to ITERATIVE: 16 phases, 7 gates, against the baseline 'reporting-export'
established. No discovery — the repository's discovery record is referenced, not
repeated. No constitution phase — .specify/memory/constitution.md is inherited as the
baseline recorded it.

Generating specification...
```

*(Engine: `sdle.sh --workitem export-csv governance assess --input governance-input.json`
with `flow: ITERATIVE`, then `init`, which started at `spec_draft`, the flow's
first generation phase.)*

---

**SDLE:** *(after `feature resolve` bound `workitems/export-csv/specs/001-export-csv`)*

```
<!-- SDLE_STATE phase=gate_spec status=awaiting_approval progress=3/16 -->
📋 SDLE Status: Phase 3/16 — Gate 1: Specification Approval [AWAITING APPROVAL]

---
✋ APPROVAL REQUIRED — Gate 1/7: Specification Approval

# CSV Export — Specification
[... abridged ...]

Artifact path: workitems/export-csv/specs/001-export-csv/spec.md
Fingerprint: a3f1c0de…9c2e
---
```

> **Read the gate number.** This is `gate_spec`, Gate 2 of 8 in `GREENFIELD`
> and **Gate 1 of 7** here. The number is derived from the bound flow every
> time it is shown; it is not a property of the gate.

**User:** `approve`

```
<!-- SDLE_STATE phase=plan_draft status=in_progress progress=4/16 -->
📋 SDLE Status: Phase 4/16 — Generate Plan [IN PROGRESS]
```

> **The rest of the flow**, with its gate numbers:
>
> | Gate | Phase | Progress | In GREENFIELD this is |
> |---:|---|---|---|
> | 1/7 | `gate_spec` | 3/16 | Gate 2 of 8 |
> | 2/7 | `gate_plan` | 5/16 | Gate 3 of 8 |
> | 3/7 | `gate_tasks` | 8/16 | Gate 4 of 8 |
> | 4/7 | `gate_analyze` | 10/16 | Gate 5 of 8 |
> | 5/7 | `gate_design` | 12/16 | Gate 6 of 8 |
> | 6/7 | `gate_implement` | 14/16 | Gate 7 of 8 |
> | 7/7 | `gate_security` | 16/16 | Gate 8 of 8 |

**User:** `approve` *(at Gate 7/7)*

```
<!-- SDLE_STATE phase=complete status=completed progress=16/16 -->
📋 SDLE Status: Phase 16/16 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!
All 7 gates passed. Completion summary: workitems/export-csv/.sdle/completion-summary.json

No baseline was written. An ITERATIVE WorkItem works against the baseline and leaves it
alone: .sdle/baseline.json, the discovery record it references and the inherited
constitution are byte-identical to what 'reporting-export' left.
```

---

### Part 3 — A materially invalid baseline

*(Suppose `.sdle/baseline.json` had been corrupted, here by a `baselineVersion`
this engine does not support. A third WorkItem assessed `ITERATIVE`:)*

```
Refused: baseline_required

ITERATIVE works from an established repository baseline and performs no rediscovery,
but .sdle/baseline.json is INVALID: .sdle/baseline.json declares baselineVersion '9';
this engine supports '1'. Complete a GREENFIELD or BROWNFIELD_DISCOVERY WorkItem first —
either establishes one at its final gate.
```

*(An invalid baseline authorises nothing. `baseline show` reports
`status: INVALID` with the `baseline_invalid` finding, and `sdle.sh validate`
reports the same.)*

### Part 4 — A stale reference is reported, never refused

*(Suppose instead that `.specify/memory/constitution.md` was amended after the
baseline recorded it. `baseline show` reports `status: STALE` with the warning
`baseline_reference_changed`, and an `ITERATIVE` WorkItem **initialises
normally**. Later WorkItems legitimately rewrite documents the baseline points
at, so a changed reference is information, not a reason to rediscover.)*

---

## Artifacts, state and audit

- `workitems/export-csv/.sdle/state.json`: `flow` = `ITERATIVE`. The traversal
  was `requirements_check → spec_draft → gate_spec → plan_draft → gate_plan → checklist_draft → tasks_draft → gate_tasks → analyze → gate_analyze → design_generation → gate_design → implement → gate_implement → security_review → gate_security → complete`.
- Seven approvals are populated. `approvals.gate_constitution` stays null, and
  `gate show --gate gate_constitution` reports `in_flow: false`, never
  "satisfied".
- `.sdle/baseline.json`, `workitems/reporting-export/.sdle/discovery.json` and
  `.specify/memory/constitution.md` are unchanged by the second WorkItem.
- The refused `init` in Part 1 left no runtime for `export-csv`.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| `BROWNFIELD_DISCOVERY` with a VALID baseline | Refused `baseline_present` | No runtime created |
| `ITERATIVE` with no baseline | Refused `baseline_required` (`ABSENT`) | No runtime created |
| `ITERATIVE` on an INVALID baseline | Refused `baseline_required` (`INVALID`) | No runtime created |
| `ITERATIVE` on a STALE baseline | **Permitted**; the change is reported as a warning | Initialises normally |
| Approve `gate_spec` before `feature resolve` | Refused `artifact_unresolved` | Unchanged |

## Cleanup

`rm -rf` the disposable repository.

## Executable coverage

| Claim | Test |
|---|---|
| Brownfield then iterative: rediscovery refused, iterative completes without discovery | `tests/test_units_baseline.py::test_n24_the_second_workitem_does_not_rediscover_the_repository` |
| Reuse rewrites nothing: baseline, discovery record, constitution byte-identical | `tests/test_integration_10_to_13.py::test_11_brownfield_then_iterative_reuses_the_baseline_without_rewriting_it` |
| No baseline → `baseline_required` | `tests/test_integration_10_to_13.py::test_11_iterative_without_a_baseline_is_refused` |
| An invalid baseline does not authorise `ITERATIVE` | `tests/test_units_baseline.py::test_n26_an_invalid_baseline_does_not_authorise_iterative` |
| A stale baseline does authorise it | `tests/test_units_baseline.py::test_n26_a_stale_baseline_authorises_iterative` |
| A changed reference yields STALE with a warning | `tests/test_units_baseline.py::test_n19_a_changed_reference_is_a_warning_and_yields_stale` |
| `gate_spec` is Gate 1 of 7 | `tests/test_integration_10_to_13.py::test_11_the_spec_gate_is_gate_one_of_seven_not_two_of_eight` |
| The constitution gate is not in the flow | `tests/test_integration_10_to_13.py::test_11_the_constitution_gate_is_not_in_flow_never_satisfied` |
| The ITERATIVE run leaves the baseline untouched | `tests/test_integration_10_to_13.py::test_11_an_iterative_run_leaves_the_baseline_untouched` |
| Null feature reference refused in this flow (D01) | `tests/test_units_gate_artifacts.py::test_d01_a_null_feature_reference_refuses_approval[ITERATIVE]` |
| No constitution is demanded of this flow (D01) | `tests/test_units_gate_artifacts.py::test_d01_a_flow_without_the_constitution_needs_no_constitution` |
