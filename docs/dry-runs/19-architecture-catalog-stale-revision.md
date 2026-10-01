# Dry Run 19 — Two WorkItems, One Catalog: Stale Revision and Replay

| | |
|---|---|
| **Scenario ID** | DR-19 |
| **Flow** | `ITERATIVE` |
| **Purpose** | The catalog is the one piece of SDLE state two WorkItems share, so it is the one place they can overwrite each other. This is what stops them: every placement pins the revision it was reasoned against, and the second approval is refused rather than silently winning. It also shows the other half of the rule — retrying the *same* decision after a crash is an idempotent replay, not a conflict. |
| **Defect IDs** | — |
| **Runtime** | SDLE v1.18 on `feature/project-architecture-memory`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | A repository whose catalog is at revision 5. Two WorkItems are in flight: `wi-a` and `wi-b`, both standing at `architecture_placement`, both having read revision 5 |
| **Guardrails exercised** | Optimistic revision control without a lock, `architecture_catalog_stale` writing nothing, idempotent replay of an identical decision, and `architecture_decision_conflict` for the same id with a different digest |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages; the
> refusal texts are the engine's own. Hashes are illustrative. The engine
> behaviour it depends on is asserted by the tests under *Executable coverage*.
> Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded
> in [verification-matrix.md](verification-matrix.md).

---

## Setup

A disposable repository at catalog revision 5 with two registered WorkItems,
each bound to its own requirement document and each assessed. Two Claude Code
sessions, one per WorkItem — which is the ordinary way this happens.

---

## Transcript

### Part 1 — Both WorkItems reason against revision 5

**Session A:**

```
architecture assess

  decision       AP-wi-a-001
  outcome        CREATE_NEW_SERVICE
  base revision  5
  digest         sha256:aa11…
```

**Session B:**

```
architecture assess

  decision       AP-wi-b-001
  outcome        EXTEND_EXISTING_SERVICE
  base revision  5
  digest         sha256:bb22…
```

> **Nothing is locked.** Two WorkItems may reason about the architecture at
> the same time; a global lock would serialize unrelated work for the length
> of a human review. What is protected is the *write*.

### Part 2 — B approves first and moves the catalog

**Session B, user:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=spec_draft status=pending progress=4/18 -->
📋 SDLE Status: Phase 4/18 — Generate Specification [PENDING]

Approved. Architecture decision AP-wi-b-001 applied to the repository catalog
(revision 6).
```

### Part 3 — A's approval is refused, and writes nothing

**Session A, user:** `approve`

**SDLE:**

```
Refused: architecture_catalog_stale

This placement was reasoned against architecture revision 5, and the catalog
is now at 6 — another WorkItem's placement was approved in between. Nothing
has been written. Re-run architecture_placement against the current
architecture (`architecture show`) and re-approve.
```

> **Read what did *not* happen.** No approval was recorded, no audit entry was
> appended, and the catalog is byte-identical to what B left. The refusal is
> raised by a pure reader ahead of the first write, so a stale placement
> cannot half-apply.
>
> And read what the refusal is *for*. A's placement was a reasonable decision
> about an architecture that no longer exists. Letting it through would not be
> a merge — it would be A's picture of the system overwriting B's.

**SDLE:**

```
<!-- SDLE_STATE phase=gate_architecture status=awaiting_approval progress=3/18 -->
📋 SDLE Status: Phase 3/18 — Gate 1: Architecture Placement Approval [AWAITING APPROVAL]

The workflow has not moved. Re-run the placement against revision 6.
```

*(Session A re-reads the catalog — B's service is now in it — reassesses, and
approves. The re-minted decision is **`AP-wi-a-001` again**: the id counts the
decisions this WorkItem already has *in the catalog*, and the refused one never
reached it, so nothing was consumed by a decision that was never applied. It is
pinned at revision 6, and the catalog moves to 7. A's new reasoning is visibly informed by B's decision,
which is the outcome the refusal exists to produce.)*

### Part 4 — A crash between the catalog write and the rest of the approval

*(Suppose the session dies immediately after `apply` wrote revision 7. On
recovery the operator replays the identical decision.)*

**SDLE:**

```
architecture apply

  replayed        true
  decision        AP-wi-a-001
  revision        7
  appliedRevision 7
```

> **A replay is not a second application.** The same decision id with the same
> proposal digest is *this* decision, already applied: the revision does not
> move again, nothing is written, and the command succeeds. Without that rule
> a crash would bump the revision a second time and make every other
> WorkItem's pinned base stale for no reason at all.
>
> The same id with a **different** digest is the opposite case — a different
> decision wearing the same name — and refuses `architecture_decision_conflict`.

---

## Artifacts, state and audit

| Revision | Decision | Base | Written by |
|---|---|---|---|
| 6 | `AP-wi-b-001` | 5 | B's architecture gate |
| — | `AP-wi-a-001` | 5 | **never applied** — refused `architecture_catalog_stale` |
| 7 | `AP-wi-a-001` (re-minted) | 6 | A's architecture gate, after re-reasoning |

Every decision in the catalog records both the revision it was reasoned
against and the revision it produced, so "what did this WorkItem know when it
decided?" is answerable after the fact.

---

## Negative cases

| What is tried | What happens |
|---|---|
| Approving A's revision-5 placement after B landed | `Refused: architecture_catalog_stale`, nothing written |
| Replaying the identical applied decision | Succeeds, `replayed: true`, revision unchanged |
| Replaying the same decision id with an edited proposal | `Refused: architecture_decision_conflict` |
| Replaying a decision that was abandoned | `Refused: architecture_decision_conflict` |
| `architecture apply` before the gate is approved | `Refused: gate_required` — a decision enters the catalog on a human's approval |

---

## Cleanup

Delete the disposable repository.

---

## Executable coverage

| Claim | Test |
|---|---|
| A stale base revision is refused and writes nothing | `tests/test_units_architecture.py::test_a_stale_base_revision_is_refused_and_writes_nothing` |
| Applying the same decision again is an idempotent replay | `tests/test_units_architecture.py::test_applying_the_same_decision_again_is_an_idempotent_replay` |
| The same id with a different digest is a conflict | `tests/test_units_architecture.py::test_the_same_id_with_a_different_digest_is_a_conflict` |
| Realizing an already-realized decision does not mutate twice | `tests/test_units_architecture.py::test_realize_turns_a_planned_service_into_an_implemented_one` |
| A second WorkItem reads the first one's catalog | `tests/test_units_architecture.py::test_a_second_workitem_sees_the_first_ones_architecture` |

Result: **PASS**.
