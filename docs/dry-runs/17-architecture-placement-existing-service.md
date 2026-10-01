# Dry Run 17 — Architecture Placement Into an Existing Service

| | |
|---|---|
| **Scenario ID** | DR-17 |
| **Flow** | `ITERATIVE` |
| **Purpose** | The ordinary case, and the one most WorkItems take: the capability is already owned by a service, so the placement extends it. It shows the phase's inputs, the gate that can never be omitted, and what a `EXTEND_EXISTING_SERVICE` decision leaves in the shared catalog. |
| **Defect IDs** | — |
| **Runtime** | SDLE v1.18 on `feature/project-architecture-memory`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | A repository with a sound `.sdle/baseline.json` and an architecture catalog at revision 4, in which `application-service` already owns `CAP-APPLICATION`. A new WorkItem, `amend-application`, binds `requirements/amend-application.md`. LOW risk, `enhancement` |
| **Guardrails exercised** | Placement before specification, a gate no risk level can omit, the structured-to-rendered digest binding, and a catalog delta that adds a capability owner without creating a service |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; the
> refusal texts are the engine's own. Hashes are illustrative. The engine
> behaviour it depends on is asserted by the tests under *Executable coverage*.
> Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded
> in [verification-matrix.md](verification-matrix.md).

---

## Setup

A disposable repository whose first WorkItem has completed, so
`.sdle/baseline.json` is VALID and `.sdle/architecture/catalog.json` exists at
revision 4. Add `requirements/amend-application.md`.

---

## Transcript

### Part 1 — The phase opens by reading what already exists

**User:** `start workflow` → **SDLE:** `WorkItem name?` → **User:** `Amend Application`

*(`workitem create`, `requirements bind`, `governance assess` and `init` run as
in DR-11. The flow is `ITERATIVE`, so no constitution is drafted — the baseline
references the one the first WorkItem approved.)*

**SDLE:**

```
<!-- SDLE_STATE phase=architecture_placement status=pending progress=2/18 -->
📋 SDLE Status: Phase 2/18 — Architecture Placement [PENDING]

Reading the repository's architecture before anything is specified.

Catalog revision 4 · 2 services · 3 capabilities · 1 candidate
Constitution status: PRESENT (via the baseline)

  application-service   IMPLEMENTED   owns CAP-APPLICATION
  review-service        IMPLEMENTED   owns CAP-REVIEW

This WorkItem is about amending an application in place. That is the same
business capability `application-service` already owns, with the same data
and the same release rhythm, so the placement is to extend it.
```

> **Read what the phase actually consumed.** The bound requirement document,
> the catalog, the constitution the baseline points at, and the repository
> where the requirements name existing code. It did **not** read the other
> documents under `requirements/`: a document nobody bound governs nothing,
> and that is what lets one `requirements/` directory serve several WorkItems.

### Part 2 — Assess

*(The orchestrator writes the proposal and hands it to the engine.)*

**SDLE:**

```
architecture assess

  decision       AP-amend-application-001
  outcome        EXTEND_EXISTING_SERVICE
  capability     CAP-APPLICATION (application-service)
  base revision  4
  constitution   PRESENT
  digest         sha256:6f1c…
  rendered       workitems/amend-application/architecture/placement.md
  approvable     yes
```

*(The rendering is generated from the validated record, never written by hand,
and carries the same decision id and digest. The orchestrator records the
governed review of that exact content and advances.)*

### Part 3 — The gate

**SDLE:**

```
<!-- SDLE_STATE phase=gate_architecture status=awaiting_approval progress=3/18 -->
📋 SDLE Status: Phase 3/18 — Gate 1: Architecture Placement Approval [AWAITING APPROVAL]
```

```
---
✋ APPROVAL REQUIRED — Gate 1/8: Architecture Placement Approval

# Architecture Placement — amend-application

- **Decision id:** `AP-amend-application-001`
- **Proposal digest:** `sha256:6f1c…`
- **Catalog revision reasoned against:** 4
- **Constitution status:** PRESENT
- **Confidence:** HIGH

## Decision

**EXTEND_EXISTING_SERVICE**

- Current owner: application-service
- Target owner: application-service
- Affected services: application-service

## Rationale

Amending an application is the same capability, the same aggregate and the
same data as creating one. Separating it would add a network hop and a
contract while adding no autonomy.

## Evidence dimensions considered

| Dimension | Finding |
|---|---|
| `business_capability_cohesion` | One capability. Amendment is a state transition of the application, not a second thing. |
| `data_ownership` | No data moves. `Application` stays owned by `application-service`. |

Artifact path: workitems/amend-application/architecture/placement.md
Fingerprint: b41e9c…
Review: architecture-placement | PASS | agent:sdle-orchestrator

Please review the content above, then respond with:
  • `approve` — Accept and advance to the next phase
  • `approve with comments: <your notes>` — Accept with recorded feedback
  • `reject with comments: <your feedback>` — Reject and trigger remediation
---
```

> **This gate cannot be omitted.** The WorkItem is LOW risk and the policy
> leaves several gates omittable, but `gate show --gate gate_architecture`
> reports `required` with the reason `architecture_gate`. Asking the engine to
> omit it refuses `gate_required`, and there is no flag that changes that. The
> catalog is shared across WorkItems: a placement is evidence a later WorkItem
> will reason from, so no placement enters it without a human.

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=spec_draft status=pending progress=4/18 -->
📋 SDLE Status: Phase 4/18 — Generate Specification [PENDING]

Approved. Architecture decision AP-amend-application-001 applied to the
repository catalog (revision 5).
```

---

## Artifacts, state and audit

| Path | Written by | Contains |
|---|---|---|
| `workitems/amend-application/.sdle/architecture-placement.json` | `architecture assess` | the validated placement, its decision id, digest and the rendering's SHA |
| `workitems/amend-application/architecture/placement.md` | `architecture assess` | the gated rendering of the same record |
| `workitems/amend-application/.sdle/evidence/architecture-<id>.json` | `architecture assess` | the input document, verbatim, beside the record |
| `.sdle/architecture/catalog.json` | `gate approve` | revision 5; `CAP-APPLICATION.relatedWorkItems` gains this WorkItem; one new decision, `APPROVED_PENDING_IMPLEMENTATION` |

Audit entries appended: `architecture_assessed`, `gate_approved`,
`architecture_applied`.

**No service was created.** `EXTEND_EXISTING_SERVICE` changes ownership of
nothing; the catalog records that a second WorkItem now rests on the same
boundary, which is what makes the *next* placement in this capability an
informed one.

---

## Negative cases

| What is tried | What happens |
|---|---|
| `gate omit --gate gate_architecture` | `Refused: gate_required` — required at every risk level |
| The proposal names a service the catalog does not have | `Refused: architecture_service_unknown`, before any write |
| `placement.md` is edited after the review | `Refused: review_stale`, and `Refused: architecture_artifact_binding_invalid` once re-reviewed at the edited content |
| `advance --to gate_architecture` with no assessed placement | `Refused: architecture_placement_missing` |
| A proposal with no `data_ownership` finding | `Refused: architecture_placement_invalid` — the outcome's required dimensions must each carry a finding |

---

## Cleanup

Delete the disposable repository. Nothing outside it was written.

---

## Executable coverage

| Claim | Test |
|---|---|
| The constitution gate lands on the placement phase | `tests/test_units_architecture.py::test_the_constitution_gate_lands_on_architecture_placement` |
| The phase cannot be left without a validated placement | `tests/test_units_architecture.py::test_a_workitem_cannot_leave_the_phase_without_a_placement` |
| The gate is required at every risk level | `tests/test_units_architecture.py::test_the_gate_is_required_at_every_risk_level` |
| `gate omit` is refused | `tests/test_units_architecture.py::test_gate_omit_is_refused` |
| Approval applies the delta and advances | `tests/test_units_architecture.py::test_approval_applies_the_delta_and_advances_to_spec_draft` |
| An unknown service is refused | `tests/test_units_architecture.py::test_an_unknown_service_is_refused` |
| A refused assess writes nothing | `tests/test_units_architecture.py::test_a_refused_assess_writes_nothing` |
| Every flow places it before the specification | `tests/test_units_flow_model.py`, contract |

Result: **PASS**.
