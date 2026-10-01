# Dry Run 20 — Bootstrapping a Catalog, and Placing Without a Constitution

| | |
|---|---|
| **Scenario ID** | DR-20 |
| **Flow** | `HOTFIX` |
| **Purpose** | The two cases a repository that predates architecture memory actually hits. First: the catalog is uninitialized, so the placement may carry an evidence-backed description of the architecture that already exists — without ever equating a directory with a service. Second: there is no constitution, which permits an extension that introduces no boundary and refuses anything that does. |
| **Defect IDs** | — |
| **Runtime** | SDLE v1.18 on `feature/project-architecture-memory`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | A legacy repository with a sound `.sdle/baseline.json` written before this version, **no** `.sdle/architecture/catalog.json`, and no constitution the baseline can resolve. A production incident; WorkItem `fix-expiry-clock` binds `requirements/incident-4471.md`. `hotfix` type, CRITICAL risk |
| **Guardrails exercised** | `architecture show` on an uninitialized catalog, `bootstrapDelta` and its evidence rule, the constitution-availability rule per outcome, and the architecture gate surviving the shortest flow |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; the
> refusal texts are the engine's own. Hashes are illustrative. The engine
> behaviour it depends on is asserted by the tests under *Executable coverage*.
> Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded
> in [verification-matrix.md](verification-matrix.md).

---

## Setup

A disposable repository carrying a baseline from an earlier SDLE version and
no catalog. `HOTFIX` never runs `discovery` and never drafts a constitution,
which is exactly what makes it the sharpest test of both rules.

---

## Transcript

### Part 1 — An uninitialized catalog is a valid state

**SDLE:**

```
architecture show

  initialized  false
  revision     0
  path         .sdle/architecture/catalog.json

  This repository has no architecture catalog yet. The first approved
  placement creates it.
```

> **It invents nothing.** No services are guessed from the directory tree, no
> capabilities are inferred from package names. An absent catalog is reported
> as absent.

### Part 2 — The placement carries a bootstrap, and a placement

**SDLE:**

```
<!-- SDLE_STATE phase=architecture_placement status=pending progress=3/12 -->
📋 SDLE Status: Phase 3/12 — Architecture Placement [PENDING]

Catalog: uninitialized.
Constitution status: ABSENT — the baseline references none, and HOTFIX does
not draft one.

The impact analysis for incident 4471 points at one deployable unit. The
baseline's design references and the deployment descriptor under
`deploy/billing-service/` say that unit is a service; the other directories
under `src/` say nothing about deployment, so this bootstrap names one
service and stops there.
```

```
architecture assess

  decision       AP-fix-expiry-clock-001
  outcome        EXTEND_EXISTING_SERVICE
  capability     CAP-BILLING (billing-service)
  bootstrap      BASELINE · 1 service · 2 evidence entries
  base revision  0
  constitution   ABSENT
  approvable     yes
```

> **Two things, never merged.** `bootstrapDelta` describes architecture that
> already exists; `placement` is the single decision for *this* WorkItem. The
> engine checks that every evidence entry cites a path that is really in the
> repository, and refuses `architecture_placement_invalid` when one does not.
>
> What it cannot check — and says so in `architecture schema` — is whether a
> cited directory really is a service. That is a claim by its author, which is
> why the evidence requirement exists: a reviewer can go and look. **A
> directory is not a service because it exists.** An absent service is
> recoverable; an invented one is repository-wide misinformation.

### Part 3 — No constitution, and the rule that follows from it

**SDLE:**

```
<!-- SDLE_STATE phase=gate_architecture status=awaiting_approval progress=4/12 -->
📋 SDLE Status: Phase 4/12 — Gate 1: Architecture Placement Approval [AWAITING APPROVAL]
```

```
---
✋ APPROVAL REQUIRED — Gate 1/4: Architecture Placement Approval

- **Constitution status:** ABSENT

## Decision

**EXTEND_EXISTING_SERVICE**

- Current owner: billing-service
- Target owner: billing-service

This hotfix corrects a clock comparison inside a service that already owns the
capability. It introduces no new service boundary, no transfer of ownership
and no new technology or platform decision, which is the only circumstance
under which a placement proceeds with no engineering rules on record.
---
```

**User:** `approve`

*(Catalog revision 1. The bootstrap's `billing-service` is recorded
`IMPLEMENTED` — it was observed, not planned — and the capability is owned by
it. The repository now has architecture memory, established by the WorkItem
that needed it rather than by a migration nobody asked for.)*

> **This gate is required here too.** `HOTFIX` at CRITICAL risk has four gates
> in total, and `gate_architecture` is the first of them. The shortest flow
> SDLE ships is still not allowed to change the repository's architecture
> without a human.

### Part 4 — What the missing constitution does refuse

*(Suppose the same hotfix had proposed standing the fix up as a new service.)*

**SDLE:**

```
Refused: architecture_constitution_required

CREATE_NEW_SERVICE establishes or transfers a service boundary, and this
repository has no approved constitution — neither this WorkItem's own nor one
referenced by a sound baseline. Establish the engineering rules first, or
record ARCHITECTURE_REVIEW_REQUIRED and resolve it with a human.
```

*(The same refusal fires for `EXTRACT_EXISTING_CAPABILITY`, and for an
extension that declares it introduces a technology decision. The escape hatch
stays open: `ARCHITECTURE_REVIEW_REQUIRED` is always recordable, because a
repository with no constitution must still have an honest answer available —
it simply cannot be approved, so the WorkItem stops until a human resolves it.)*

---

## Artifacts, state and audit

| Path | Contains |
|---|---|
| `.sdle/architecture/catalog.json` | revision 1: one `IMPLEMENTED` service and one capability, both traceable to `AP-fix-expiry-clock-001` |
| `workitems/fix-expiry-clock/.sdle/architecture-placement.json` | the validated placement, including the bootstrap and the resolved constitution status |
| `workitems/fix-expiry-clock/architecture/placement.md` | the gated rendering, carrying the same decision id and digest |

The bootstrap is recorded **once**. A later WorkItem that tried to carry one
is refused `architecture_placement_invalid`: once the catalog exists, "what
already exists" is the catalog.

---

## Negative cases

| What is tried | What happens |
|---|---|
| Bootstrap evidence citing a path that is not in the repository | `Refused: architecture_placement_invalid` |
| A `bootstrapDelta` once the catalog exists | `Refused: architecture_placement_invalid` |
| `CREATE_NEW_SERVICE` with no constitution | `Refused: architecture_constitution_required` |
| `EXTEND_EXISTING_SERVICE` that declares a technology decision, with no constitution | `Refused: architecture_constitution_required` |
| Approving an `ARCHITECTURE_REVIEW_REQUIRED` placement | `Refused: architecture_decision_unresolved` |
| A catalog file the engine cannot parse | `Refused: architecture_catalog_invalid` (exit 3), left exactly as it is |

---

## Cleanup

Delete the disposable repository.

---

## Executable coverage

| Claim | Test |
|---|---|
| An empty repository reports an uninitialized catalog | `tests/test_units_architecture.py::test_an_empty_repository_reports_an_uninitialized_catalog` |
| `show` needs no WorkItem | `tests/test_units_architecture.py::test_show_needs_no_workitem` |
| A legacy repository bootstraps from evidence | `tests/test_units_architecture.py::test_a_legacy_repository_bootstraps_from_evidence` |
| Bootstrap evidence must cite a path that exists | `tests/test_units_architecture.py::test_bootstrap_evidence_must_cite_a_path_that_exists` |
| Bootstrap is refused once the catalog exists | `tests/test_units_architecture.py::test_bootstrap_is_refused_once_the_catalog_exists` |
| A legacy extension is permitted without a constitution | `tests/test_units_architecture.py::test_a_legacy_extension_is_permitted_without_a_constitution` |
| …but not when it introduces a technology decision | `tests/test_units_architecture.py::test_but_not_when_it_introduces_a_technology_decision` |
| Review-required is always recordable without one | `tests/test_units_architecture.py::test_review_required_is_always_recordable_without_one` |
| An unreadable catalog is an integrity failure | `tests/test_units_architecture.py::test_an_unreadable_catalog_is_an_integrity_failure_not_an_absence` |

Result: **PASS**.
