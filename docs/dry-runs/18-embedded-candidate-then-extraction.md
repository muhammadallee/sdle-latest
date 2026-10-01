# Dry Run 18 — Embedded Candidate, Then Extraction

| | |
|---|---|
| **Scenario ID** | DR-18 |
| **Flow** | `ITERATIVE` |
| **Purpose** | The evolutionary path, across two WorkItems. The first sees a boundary, decides it does not yet justify a service, and records a **candidate** with the conditions that would reopen it. The second arrives with the accumulated evidence and **extracts** it. This is the sequence architecture memory exists for: neither WorkItem could have reached the second decision alone. |
| **Defect IDs** | — |
| **Runtime** | SDLE v1.18 on `feature/project-architecture-memory`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | A repository whose catalog is at revision 5 with `application-service` owning `CAP-APPLICATION`. WorkItem `initial-risk-assessment` binds `requirements/initial-risk-assessment.md`; later, `detailed-risk-assessment` binds `requirements/detailed-risk-assessment.md`. LOW then MEDIUM risk |
| **Guardrails exercised** | `KEEP_EMBEDDED_AND_MONITOR` with mandatory re-evaluation conditions, the candidate a later WorkItem reads, `EXTRACT_EXISTING_CAPABILITY` and its migration requirements, and the `PLANNED` → `IMPLEMENTED` realization at the implementation gate |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; the
> refusal texts are the engine's own. Hashes are illustrative. The engine
> behaviour it depends on is asserted by the tests under *Executable coverage*.
> Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded
> in [verification-matrix.md](verification-matrix.md).

---

## Setup

Complete DR-17 in a disposable repository, then add the two requirement
documents. The two WorkItems run one after the other in the same repository —
which is the point: the second reads what the first recorded.

---

## Transcript

### Part 1 — WorkItem one sees a boundary and declines to distribute it

**SDLE:**

```
<!-- SDLE_STATE phase=architecture_placement status=pending progress=2/18 -->
📋 SDLE Status: Phase 2/18 — Architecture Placement [PENDING]

Catalog revision 5 · 2 services · 3 capabilities · 1 candidate
Constitution status: PRESENT (via the baseline)

A distinct capability is visible here — risk assessment is not the same thing
as an application — but the scope in this WorkItem is one score and one
threshold, the data is read transactionally with the application, and there is
no independent release rhythm yet. Distributing it now would buy a network hop
and pay for it in latency and partial failure.

Proposing KEEP_EMBEDDED_AND_MONITOR, with the conditions that would change
the answer.
```

```
architecture assess

  decision       AP-initial-risk-assessment-001
  outcome        KEEP_EMBEDDED_AND_MONITOR
  capability     CAP-RISK-ASSESSMENT (embedded in application-service)
  candidate      ARCH-CAND-004
  base revision  5
  approvable     yes
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_architecture status=awaiting_approval progress=3/18 -->
📋 SDLE Status: Phase 3/18 — Gate 1: Architecture Placement Approval [AWAITING APPROVAL]
```

```
---
✋ APPROVAL REQUIRED — Gate 1/8: Architecture Placement Approval

## Decision

**KEEP_EMBEDDED_AND_MONITOR**

- Current owner: application-service
- Target owner: _unchanged_

## Candidates affected

- `ARCH-CAND-004` — `CAP-RISK-ASSESSMENT` inside `application-service` (OPEN)
  - re-evaluate when: a second WorkItem lands in this capability
  - re-evaluate when: risk assessment acquires its own external integration
  - re-evaluate when: its data stops being read transactionally with the application

## Migration implications

_None: no behaviour moves._
---
```

**User:** `approve`

*(Catalog revision 6. `CAP-RISK-ASSESSMENT` is recorded `EMBEDDED` with
`application-service` as owner; `ARCH-CAND-004` is `OPEN` with its three
conditions. The implementation that follows preserves the seam —
`application-service/risk-assessment/` with its own interface — because a
candidate that cannot be extracted later is a note, not a decision.)*

### Part 2 — WorkItem two reads the candidate and meets its condition

<!-- dry-run-flow: ITERATIVE -->

**SDLE:**

```
<!-- SDLE_STATE phase=architecture_placement status=pending progress=2/18 -->
📋 SDLE Status: Phase 2/18 — Architecture Placement [PENDING]

Catalog revision 6 · 2 services · 4 capabilities · 2 candidates

  ARCH-CAND-004  CAP-RISK-ASSESSMENT  embedded in application-service  OPEN
                 evidence: initial-risk-assessment
                 re-evaluate when: a second WorkItem lands in this capability

That condition is met by this WorkItem. The accumulated evidence now reads
differently: the capability has its own scoring lifecycle, its own external
bureau integration, and `RiskAssessment` has become independently meaningful
data. The seam the first WorkItem preserved makes this a move rather than a
rewrite.
```

```
architecture assess

  decision       AP-detailed-risk-assessment-001
  outcome        EXTRACT_EXISTING_CAPABILITY
  capability     CAP-RISK-ASSESSMENT
  from           application-service
  to             risk-assessment-service (new, PLANNED on approval)
  base revision  6
  constitution   PRESENT
  approvable     yes
```

> **An extraction is never only a new feature.** The engine refuses the
> proposal unless it states its migration implications and names the data that
> moves — `Refused: architecture_placement_invalid` otherwise. What it cannot
> check, and says so, is whether the migration described is the right one.

**SDLE:**

```
<!-- SDLE_STATE phase=gate_architecture status=awaiting_approval progress=3/18 -->
📋 SDLE Status: Phase 3/18 — Gate 1: Architecture Placement Approval [AWAITING APPROVAL]
```

```
---
✋ APPROVAL REQUIRED — Gate 1/8: Architecture Placement Approval

## Decision

**EXTRACT_EXISTING_CAPABILITY**

- Current owner: application-service
- Target owner: risk-assessment-service
- Affected services: application-service, risk-assessment-service

## Data ownership impact

- `RiskAssessment` → `risk-assessment-service` via `CAP-RISK-ASSESSMENT`

## Migration implications

The scoring behaviour introduced by `initial-risk-assessment` moves with the
capability and must keep passing. `application-service` calls the new service
across a contract where it previously called into a package. Compatibility is
kept for one release; regression coverage for the migrated behaviour is part
of this WorkItem, not a follow-up.
---
```

**User:** `approve`

*(Catalog revision 7. `risk-assessment-service` is created **`PLANNED`**;
`CAP-RISK-ASSESSMENT` becomes `EXTRACTING`; `ARCH-CAND-004` becomes
`EXTRACTING`; the new `RiskAssessment` ownership row enters `PLANNED`, so
`application-service` is still the one active owner until the work is
accepted.)*

### Part 3 — Realization at the implementation gate

**SDLE:**

```
<!-- SDLE_STATE phase=gate_implement status=awaiting_approval progress=16/18 -->
📋 SDLE Status: Phase 16/18 — Gate 7: Implementation Approval [AWAITING APPROVAL]
```

**User:** `approve`

**SDLE:**

```
Approved. Architecture decision AP-detailed-risk-assessment-001 realized:
planned services are now implemented and superseded ownership is closed
(catalog revision 8).
```

*(`risk-assessment-service` → `IMPLEMENTED`. The new `RiskAssessment`
ownership row → `ACTIVE`, and the old one → `SUPERSEDED` in the same step, so
the "exactly one active owner" invariant is never broken in either direction.
`ARCH-CAND-004` → `EXTRACTED`; `CAP-RISK-ASSESSMENT` → `ESTABLISHED`.)*

---

## Artifacts, state and audit

| Revision | Written at | What changed |
|---|---|---|
| 6 | WorkItem one's architecture gate | capability `EMBEDDED`, candidate `ARCH-CAND-004` `OPEN` |
| 7 | WorkItem two's architecture gate | `risk-assessment-service` `PLANNED`, capability `EXTRACTING`, ownership row `PLANNED` |
| 8 | WorkItem two's implementation gate | service `IMPLEMENTED`, ownership `ACTIVE`, previous owner `SUPERSEDED`, candidate `EXTRACTED` |

Each revision is one decision, and each decision keeps the base revision it was
reasoned against — so the history reads as a sequence of decisions rather than
as a final state that arrived from nowhere.

---

## Negative cases

| What is tried | What happens |
|---|---|
| `KEEP_EMBEDDED_AND_MONITOR` with no candidate | `Refused: architecture_placement_invalid` — the outcome records a boundary worth watching, so it must record one |
| A candidate with no re-evaluation conditions | `Refused: architecture_placement_invalid` — a candidate nobody will revisit is not monitoring |
| `EXTRACT_EXISTING_CAPABILITY` with no migration implications | `Refused: architecture_placement_invalid` |
| `EXTRACT_EXISTING_CAPABILITY` from a service the catalog does not have | `Refused: architecture_service_unknown` |
| Extraction proposed where no constitution resolves | `Refused: architecture_constitution_required` |

---

## Cleanup

Delete the disposable repository.

---

## Executable coverage

| Claim | Test |
|---|---|
| A candidate is recorded, with its capability marked embedded | `tests/test_units_architecture.py::test_keep_embedded_records_a_candidate` |
| A candidate with no re-evaluation conditions is refused | `tests/test_units_architecture.py::test_keep_embedded_needs_a_candidate_with_reevaluation_conditions` |
| Realization turns a planned service into an implemented one | `tests/test_units_architecture.py::test_realize_turns_a_planned_service_into_an_implemented_one` |
| Moved data supersedes its previous owner at realization | `tests/test_units_architecture.py::test_realize_supersedes_the_previous_owner_of_moved_data` |
| Two active owners for one datum is refused | `tests/test_units_architecture.py::test_two_active_owners_for_one_datum_is_refused` |
| An extraction needs an approved constitution | `tests/test_units_architecture.py::test_a_boundary_outcome_needs_a_constitution` |
| A second WorkItem sees the first one's architecture | `tests/test_units_architecture.py::test_a_second_workitem_sees_the_first_ones_architecture` |

Result: **PASS**.
