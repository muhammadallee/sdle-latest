# ADR-013 — Project architecture memory and WorkItem placement

**Status:** Accepted
**Amends:** ADR-002 (repository configuration boundary)
**Relates to:** ADR-001 (deterministic core), ADR-004 (declarative flow model), ADR-005 (brownfield discovery and baseline), ADR-010 (no state migration), ADR-011 (pinned governance policy), ADR-012 (requirements source binding), ADR-014 (constitution, guidelines and decision precedence)

---

## The decision in one sentence

> A WorkItem is the unit of SDLE execution; the repository is the unit of accumulated architectural knowledge. Each WorkItem makes an architecture-placement decision from its bound requirements, the approved constitution, relevant guidelines, the current project architecture and existing implementation evidence. Architecture evolves as requirements accumulate, but no WorkItem may silently redefine an approved service boundary.

---

## Context

Before this decision, every SDLE artifact was WorkItem-scoped. That is right for a specification, a plan and an implementation manifest: they are about *this* change, they are governed by *this* WorkItem's gates, and they are meaningless to anyone else.

It is wrong for one thing, and only one: **where a capability lives.**

Service boundaries are a property of the repository, not of a change. Two consequences followed from having nowhere to record them:

1. **No memory.** The second WorkItem to touch a capability had no way to learn that the first one had already placed it. Two WorkItems could put the same capability in two services and nothing in the engine would notice, because nothing in the engine held an opinion about where anything lived.
2. **No evolution.** The common and correct answer to "does this deserve a service?" early in a project is *"not yet, and here is what would change our mind"*. There was nowhere to write the second half of that sentence, so it was never written, and an embedded capability could grow for a year with no record that anyone had considered extracting it.

Meanwhile the decision itself was being made — implicitly, inside a specification or a plan, once per WorkItem, by whoever was drafting.

## Decision

### 1. A repository-level architecture catalog

`.sdle/architecture/catalog.json` holds the repository's accumulated architectural knowledge: capabilities, services, candidates, data ownership and the decision history that produced them. It is derived from `project_root` alone and never from the bound WorkItem.

It is **engine-owned**. The model proposes a structured placement; `scripts/sdle.py` validates it, writes the evidence, and — only after a human approves the gate — applies the delta. Agents never edit it: the write fence denies `.sdle/architecture/`, and the guarantee behind the fence is the engine's refusal at the choke point.

Human-readable views are **rendered** from the catalog by `architecture show`. There is no second, hand-maintained copy.

### 2. An explicit phase with its own gate, before the specification

`architecture_placement` and `gate_architecture` are inserted immediately before `spec_draft` **in every executable flow**, and both join `MANDATORY_FLOW_PHASES`. `lint-skill`'s `architecture_phase_precedes_spec_in_every_flow` pins the ordering; the mandatory-phase rule pins the presence.

The ordering is the point. A specification written before the boundary is chosen is a specification written inside a boundary somebody invented on the way past.

### 3. The gate is universally human-required

`gate_architecture` cannot be omitted at any risk level, for any WorkItem type, under any policy. This is not a policy entry — it is a **derived reason** inside `gate_requirements`, the same mechanism that makes the terminal gate unconditional:

```python
if gate_key == ARCHITECTURE_GATE_KEY:
    reasons.append("architecture_gate")
```

Because a policy dictionary can only ever *add* reasons, and the ADR-011 pin only narrows toward *more* required, there is no configuration that relaxes it.

The justification is specific, and it is the only gate to which it applies: every other gate governs an artifact belonging to this WorkItem. This one governs a change to **shared memory that later WorkItems will reason from as established fact**. A risk level low enough to skip a review of this WorkItem's own plan says nothing about whether the repository's architecture may be altered without a human.

### 4. Five outcomes, exactly one per placement

| Outcome | Use when |
|---|---|
| `EXTEND_EXISTING_SERVICE` | the capability is already owned there; same invariants, same data, no independent lifecycle |
| `CREATE_NEW_SERVICE` | the evidence already justifies an independent boundary. WorkItem size is never the criterion |
| `KEEP_EMBEDDED_AND_MONITOR` | a boundary is visible, scope is small, independent deployment does not yet pay for itself |
| `EXTRACT_EXISTING_CAPABILITY` | accumulated evidence now justifies pulling an embedded capability out |
| `ARCHITECTURE_REVIEW_REQUIRED` | ownership conflicts, the aggregate is unclear, ADRs disagree, a transaction would cross services |

The fifth is **not approvable**. It records that the evidence does not support a placement, and it stops the WorkItem until a human resolves it. Making it approvable would put "we do not know" into shared memory as though it were a decision.

`existing service → embedded capability → accumulated requirements → new independent service` is a **supported path, not a failure**. `KEEP_EMBEDDED_AND_MONITOR` exists so the honest early answer is recordable, with the conditions that would reopen it.

### 5. Evidence, not a score

A proposal addresses the evidence dimensions its outcome makes relevant — capability cohesion, data ownership, transactional boundaries, lifecycle independence, change coupling, security boundary, and the rest. The engine checks that the named dimensions are ones it knows and that the outcome's required ones carry a finding. **It never computes, accepts or stores a numeric "microservice score."**

A finding may legitimately say *"this dimension does not separate"*. That is evidence. What it may not be is absent.

### 6. Optimistic concurrency with idempotent replay

Every proposal pins `baseArchitectureRevision`. On approval:

- base revision equals the catalog's → apply, `revision += 1`, record the decision;
- the catalog already holds this decision id with the same proposal digest → **idempotent replay**, nothing written, revision unchanged;
- same id, different digest → `architecture_decision_conflict`;
- otherwise → `architecture_catalog_stale`, nothing written, re-run the placement.

The replay rule is what makes a crashed `apply` retryable. Without it, a retry after a crash that had already written revision N would bump the revision again and make every other WorkItem's pinned base stale for no reason. `realize` follows the same rule.

There is **no global lock across the lifecycle**. Two WorkItems may work concurrently; the one that approves second is told to re-reason, which is the correct outcome — its placement was reasoned against an architecture that no longer exists.

### 7. The structured record and the rendering are cryptographically bound

`architecture assess` writes `workitems/<id>/.sdle/architecture-placement.json` and generates `workitems/<id>/architecture/placement.md` from it. The record stores the decision id, the proposal digest, the rendering's path and its SHA-256; the rendering prints the first two.

The gate is about the **rendering** — it is fingerprinted, it needs a PASS review of its exact current content, it participates in drift detection. Before the catalog is touched, the engine re-verifies the rendering's SHA and header against the record. A hand-edited rendering therefore fails rather than becoming architecture truth.

### 8. Bootstrap is separate from placement

A repository with no catalog is valid; `architecture show` reports `initialized: false` and invents nothing.

While the catalog is uninitialized, a proposal may carry a `bootstrapDelta` describing architecture that already exists, **alongside** the single placement for the current WorkItem. Two concepts, never merged. Its basis is the discovery record (`BROWNFIELD_DISCOVERY`) or the baseline's referenced constitution, design documents and ADRs plus repository inspection (a legacy `ITERATIVE`/`DEFECT_FIX`/`HOTFIX` WorkItem in a repository that predates this decision and never runs `discovery`).

Every evidence entry must cite a path that exists. **A directory is not a service because it exists** — the engine cannot check that, so the rule is stated where the judgement is made, and the evidence requirement is what makes the claim inspectable.

### 9. Approved-but-unrealized decisions are disposed of, never deleted

If a WorkItem is abandoned after its architecture was approved, the shared history must not vanish. The **engine** marks the decision `ABANDONED` deterministically when:

- `restart phase N` targets a phase at or before `architecture_placement`;
- `reset workflow` runs on a WorkItem holding an approved-pending-implementation decision;
- a rerun placement for the same WorkItem is approved and supersedes it.

A service the decision created `PLANNED` becomes `WITHDRAWN` — never silently deleted, never left `PLANNED` — and a later WorkItem may reclaim the boundary. Candidates and data-ownership rows introduced solely by it are disposed of the same way. Catalog history is **appended to, never rewritten**.

One asymmetry is deliberate: `reset workflow` deletes `audit.md`, so for that disposition the catalog entry is the only durable record there will ever be. That is why it is a catalog write and not an audit entry — and why a catalog the engine cannot read now blocks `reset`. Fail-closed, because losing shared architectural history silently is the outcome this rule exists to prevent.

### 10. Requirements isolation is preserved

Placement reads **bound** requirements only (ADR-012). It must not glob `requirements/` for sibling WorkItems. Full-SRS awareness reaches a WorkItem only through documents deliberately bound to it — a bound overview that lists sibling WorkItems under a capability is legitimate context; a directory listing is not.

This is what makes both intake modes one mechanism rather than two workflows. With a refined SRS, bind the overview and the placement sees the sibling evidence. Without one, decide from current evidence, preserve the seam, and let a later WorkItem trigger the extraction.

---

## This amends ADR-002

ADR-002 drew `.sdle/` as a **configuration** boundary: repository-wide, human-authored, policed in both directions by `validate`, and explicitly *not* read by any lifecycle rule — "no lifecycle rule lives there and nothing in any lifecycle flow reads it."

That is no longer true, and pretending otherwise would be the more dangerous option. ADR-013 puts **knowledge** at the same location: `.sdle/architecture/` is read by every WorkItem's placement phase and written by its architecture gate. The boundary's *location rule* is unchanged — derived from `project_root`, never from the bound WorkItem — but its *content rule* now admits accumulated knowledge alongside configuration.

Two mechanical consequences follow.

**The dirty-tree guard is narrowed, not widened.** `SDLE_OWNED_PREFIXES` used to contain `.sdle/` whole, which made the entire configuration root invisible to `implement preflight`. Because this decision writes into `.sdle/` *during* a lifecycle, that exclusion had to be re-examined rather than extended. The replacement names only the three members the engine actually writes:

```python
".sdle/baseline.json", ".sdle/implementation-state/", ".sdle/architecture/"
```

`config.json` and `policies/` are human-authored and become **visible to the guard again** — an uncommitted edit to either now trips `dirty_tree`, which is what it should always have done. Nothing that was reported before stopped being reported; the change is strictly stricter. The original reason for owning `baseline.json` is preserved verbatim: one WorkItem's baseline write must not trip another WorkItem's guard.

`workitems/` was already owned, so both WorkItem placement artifacts needed no rule of their own.

**The write fence gains one member, not a directory.** `.sdle/architecture` joins the hook's `FENCED` list. `.sdle/` itself is deliberately not fenced: `config init` writes `config.json` and a human edits `policies/`.

## State schema

`templates/state.json` gains `gate_architecture` in `approvals`, so `CURRENT_VERSION` moves `1.17 → 1.18`. A `1.17` state is refused `unsupported_state_version` and left untouched. That is ADR-010's existing rule, applied — not a supersession of it.

## Gate ordinals in ADR-001 … ADR-012

Inserting `gate_architecture` at GREENFIELD position 2 shifts every later gate's ordinal by one: the implementation gate that ADR-001, ADR-002, ADR-005, ADR-008 and ADR-009 all name "Gate 7" is **Gate 8** from this decision forward, and the label range ADR-004 writes as `Gate 1 … Gate 8` is now `Gate 1 … Gate 9`.

Those documents are **not** rewritten. An ADR records a decision as it was made, and back-dating its ordinals would make the record disagree with the commit it describes. Read a gate ordinal in ADR-001 … ADR-012 as the ordinal at that decision's date; the gate *key* (`gate_implement`) is stable and is what the engine matches on. Live instruction text — `SKILL.md`, the modules, the commands, the lifecycle and troubleshooting guides — carries current ordinals and is swept by `lint-skill`.

---

## Rejected alternatives

**WorkItem-local architecture only.** Record the placement in the WorkItem and nowhere else. Rejected: it is the status quo with extra ceremony. The second WorkItem still cannot see the first one's decision, which is the entire problem.

**One WorkItem = one microservice.** Rejected: WorkItems are delivery units and services are capability boundaries. Nothing makes them correspond, and the mapping produces nanoservices at exactly the rate the backlog produces tickets.

**Decide every service from the first WorkItem.** Rejected: it is a forecast, and forecasts about boundaries are made with the least evidence anyone will ever have. The evolutionary path this decision supports exists because the right answer changes as requirements accumulate.

**Scan all of `requirements/` on every placement.** Rejected: it breaks ADR-012 outright. A document nobody bound governs nothing — that is what lets one `requirements/` directory serve several WorkItems without each silently constraining the others.

**Always create a service for a new capability.** Rejected: it mistakes "a capability is visible" for "a capability is autonomous". `KEEP_EMBEDDED_AND_MONITOR` is the answer this would eliminate, and it is the correct answer more often than not.

**Markdown-only architecture decisions.** Rejected: the catalog has to be *queried* by later WorkItems, validated for referential integrity, and versioned for optimistic concurrency. Prose does none of those. The Markdown remains — generated, and bound to the record by digest, so there is exactly one truth with two renderings.

**A separate mandatory engineering-profile artifact.** Rejected in ADR-014; the constitution is the engineering profile.

**A global lock across the lifecycle.** Rejected: it would serialize unrelated WorkItems for the duration of a human review. Optimistic revision control plus idempotent replay gives the same safety and refuses only the WorkItem that genuinely reasoned against a stale architecture.

---

## Consequences

**We accept** two extra phases and one extra gate in every flow — GREENFIELD moves from 18 phases and 8 gates to 20 and 9 — and a state schema version that refuses every existing WorkItem's state. Both are deliberate; the second is ADR-010 working as designed.

**We accept** that a second WorkItem approving its placement first forces the first to re-reason. That is the cost of not holding a lock, and the refusal is explicit rather than a silent overwrite.

**We gain** an architecture that is inspectable (`architecture show`), evolutionary by design, and impossible to change without a human — and a record of the boundaries that were *considered and declined*, which is the part nobody ever writes down.

**What this is not.** Not an enterprise architecture repository, not runtime service discovery, not an automatic extraction engine, not a code generator. It records decisions and the evidence behind them. Everything it might grow into is a later decision.
