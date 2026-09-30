# Architecture Memory — Frozen Contracts

**Status:** approved 2026-09-29 (Wave B checkpoint, §6.3), then **amended
by the Round-1 review** — the amendments are marked *(R1-nnn)* and are the
only changes made after approval.
**Scope:** every name, shape, path, number and rule the implementation streams
may rely on. After approval, **no stream invents any of these independently.**

> WorkItems are isolated units of delivery; architecture is accumulated
> repository-level knowledge shared across WorkItems.

Authority order for anything *not* frozen here: `scripts/sdle.py` and the
constant tables in `SKILL.md`, then this document, then derived prose.

---

## 1. Identifiers

| Kind | Frozen value |
|---|---|
| Phase id | `architecture_placement` |
| Gate phase id | `gate_architecture` |
| Gate approvals key | `gate_architecture` (same string — every gate in this engine uses one string for both) |
| Phase label | `Architecture Placement` |
| Gate label | `Gate {gate_number}: Architecture Placement Approval` |
| Audit events | `architecture_assessed`, `architecture_applied`, `architecture_realized`, `architecture_decision_abandoned` |
| Decision id | `AP-<workitem-id>-<NNN>` — `NNN` zero-padded, 1-based, counting decisions already recorded in the catalog **for that WorkItem**. Minted by `architecture assess`, stored in the WorkItem record, never re-minted by `apply`. |
| Catalog schema version | `1` |
| Proposal input version | `"1"` (`architectureProposalVersion`) |
| WorkItem record version | `"1"` (`architecturePlacementVersion`) |
| State schema version | `1.17` → **`1.18`** |

### Why the gate label carries `{gate_number}`

`lint-skill`'s `gate_labels_are_flow_relative` requires it, and here the ordinal
genuinely moves: `gate_architecture` is **gate 2** in `GREENFIELD` and
`BROWNFIELD_DISCOVERY` (after `gate_constitution`) and **gate 1** in
`ITERATIVE`, `DEFECT_FIX` and `HOTFIX`, none of which contain
`gate_constitution`. The total differs per flow as well. Both are substituted
per bound flow and never hardcoded.

---

## 2. Lifecycle placement

### 2.1 Registry (`PHASE_SEQUENCE`, `SKILL.md`) — 21 → 23 rows

`architecture_placement` and `gate_architecture` are inserted **after
`gate_constitution` and before `spec_draft`**. That one registry position
satisfies every flow's ordering requirement simultaneously, because
`constitution_draft`/`gate_constitution`, `discovery` and `impact_analysis` all
precede it in registry order.

```
1  requirements_check      9  gate_spec              17 gate_design
2  discovery              10  plan_draft             18 implement
3  impact_analysis        11  gate_plan              19 gate_implement
4  constitution_draft     12  checklist_draft        20 security_review
5  gate_constitution      13  tasks_draft            21 gate_security
6  architecture_placement 14  gate_tasks             22 complete
7  gate_architecture      15  analyze
8  spec_draft             16  gate_analyze
```

### 2.2 `NEXT_PHASE`

`gate_constitution → architecture_placement → gate_architecture → spec_draft`.
Everything else is unchanged; the chain still walks `PHASE_SEQUENCE` in order.

### 2.3 Flows

Before-values are the engine's own, read from `sdle.sh constants` on the
baseline commit — not hand-counted.

| Flow | Phases before → after | Gates before → after |
|---|---|---|
| `GREENFIELD` (`GREENFIELD_V1_PHASES` in `sdle.py`) | 18 → **20** | 8 → **9** |
| `BROWNFIELD_DISCOVERY` | 19 → **21** | 8 → **9** |
| `ITERATIVE` | 16 → **18** | 7 → **8** |
| `DEFECT_FIX` | 14 → **16** | 6 → **7** |
| `HOTFIX` | 10 → **12** | 3 → **4** |

Counts **exclude** the terminal `complete`, which is what `FlowSpec.phase_count`
reports and what the progress header shows. Every document that states a flow
size is lint-checked against the engine (`doc_flow_counts_match_engine`), in all
three claim shapes.

`GREENFIELD_V1_PHASES` is edited directly in `scripts/sdle.py` — the
deliberately loud change. The other four are edited in `FLOW_PHASES`.

### 2.4 `MANDATORY_FLOW_PHASES` — 10 → 12

`architecture_placement` and `gate_architecture` join the governance floor.
This buys the "present in every flow" half of §3.1's invariant through the
existing `every_flow_retains_the_mandatory_phases` check.

### 2.5 New lint check — the ordering half

```
architecture_phase_precedes_spec_in_every_flow
```

For every flow including GREENFIELD: `architecture_placement` and
`gate_architecture` are both present, `architecture_placement` immediately
precedes `gate_architecture`, and `gate_architecture` immediately precedes
`spec_draft`. Fails loudly, never defaults.

### 2.6 Gate numbers (`PHASE_TO_GATE_KEY`, GREENFIELD view)

| gate | before | after |
|---|---|---|
| `gate_constitution` | 1 | 1 |
| **`gate_architecture`** | — | **2** |
| `gate_spec` | 2 | 3 |
| `gate_plan` | 3 | 4 |
| `gate_tasks` | 4 | 5 |
| `gate_analyze` | 5 | 6 |
| `gate_design` | 6 | 7 |
| `gate_implement` | 7 | 8 |
| `gate_security` | 8 | 9 |

`PROGRESS_MAP` is re-derived as the GREENFIELD view over 20
(`requirements_check` `1/20` … `gate_security` `20/20`, `complete` `20/20`).

### 2.7 `GATE_TO_EXECUTION_PHASE` (in `modules/gate-protocol.md`)

| gate_key | execution_phase | type |
|---|---|---|
| `gate_architecture` | `architecture_placement` | SDLE-native (`modules/architecture-placement.md`) |

### 2.8 `ARTIFACT_OWNERSHIP`

| gate_key | template | path type |
|---|---|---|
| `gate_architecture` | `{workitem_root}/architecture/placement.md` | substitute `workitem_root` |

**New placeholder.** `resolve_artifact_path` today substitutes
`{workitem_runtime}` (= `workitems/<id>/.sdle`), `{speckit_feature_directory}`
and `{security_review_artifact}`. `{workitem_root}` (= `workitems/<id>`) is
added alongside `{workitem_runtime}`, in the same unconditional-substitution
branch, because it too is always known for a bound WorkItem.

### 2.9 `CAPABILITY_MAP`

| phase | capabilities |
|---|---|
| `constitution_draft` | `modules/phase-execution.md guidelines/constitution.md` |
| `architecture_placement` | `modules/architecture-placement.md guidelines/architecture-placement.md` |
| `gate_architecture` | `modules/gate-protocol.md modules/architecture-placement.md` |
| `plan_draft` | `modules/phase-execution.md guidelines/service-planning.md` |
| `tasks_draft` | `modules/phase-execution.md guidelines/task-generation.md` |
| `design_generation` | `modules/phase-execution.md modules/design-review.md guidelines/service-design.md` |
| `implement` | `modules/phase-execution.md modules/code-review.md guidelines/implementation.md` |

Capability file count 5 → **12** (6 modules + 6 guidelines).

**`guidelines/` is not covered by the current lint plumbing — three engine
changes make it so**, or `every_capability_file_is_linted` fails the moment a
guideline is mapped:

1. `Paths.guidelines_dir` — new property beside `Paths.modules_dir`
   (`sdle.py:311`).
2. `_skill_files` (`sdle.py:11125`) extends to `guidelines/*.md`, so guideline
   files fall inside `no_powershell_only_cmdlets`,
   `no_hardcoded_progress_outside_progress_map` and
   `discovery_vocabulary_is_not_restated_in_prompt_files` — the whole reason
   that function is derived rather than listed.
3. `every_capability_file_is_linted`'s orphan glob (`sdle.py:10826`) currently
   globs `modules/` only; it globs `guidelines/` too, so an unmapped guideline
   fails loudly (§5.1's "orphans fail" becomes true rather than assumed).

### 2.10 State schema — `1.17` → `1.18`

`templates/state.json` gains `"gate_architecture": null` in `approvals`.
`CURRENT_VERSION` becomes `"1.18"` and all **5** lint-checked display copies
move with it. A `1.17` state is refused `unsupported_state_version` and left
untouched — **the existing ADR-010 rule, not a new supersession**, so this needs
no ADR of its own.

`test_units_invariants.py` must be updated in the same commit:
`GREENFIELD_PHASES`, `WRITE_PRIMITIVE_COUNTS`, `COMMANDS` (adding `apply`,
`architecture`, `realize`). `STATE_FIELDS` is unchanged — no new top-level field.

---

## 3. `gate_architecture` is universally human-required

Implemented the way `terminal_gate` already is: a **derived reason** inside
`gate_requirements` (`sdle.py:5075`), not a policy-dictionary entry.

```python
if gate_key == terminal:
    reasons.append("terminal_gate")
if gate_key == ARCHITECTURE_GATE_KEY:
    reasons.append("architecture_gate")
```

Consequences, all free:

- `disposition` is `required` for every classification and every risk level.
- `cmd_gate_omit` re-derives the same model, so `gate omit --gate
  gate_architecture` refuses `gate_required`.
- A project policy under `.sdle/policies/` cannot relax it: policy dictionaries
  only ever *add* reasons, and the ADR-011 pin only ANDs toward more required.
- `governance gates` reports it `required` with reason `architecture_gate`.

New lint check: `architecture_gate_is_universally_required` — for every flow,
every WorkItem type and every risk level in the built-in policy, the derived
disposition is `required`.

---

## 4. The catalog — `.sdle/architecture/catalog.json`

```jsonc
{
  "catalogVersion": 1,
  "revision": 7,
  "updatedAt": "2026-09-28T10:00:00+00:00",
  "capabilities": [ /* Capability */ ],
  "services":     [ /* Service */ ],
  "candidates":   [ /* Candidate */ ],
  "dataOwnership":[ /* DataOwnership */ ],
  "decisions":    [ /* Decision */ ]
}
```

`revision` starts at `0` conceptually and is `1` after the first successful
`apply`. A repository with no file is **uninitialized**, which is valid.

### Capability

```jsonc
{ "id": "CAP-RISK-ASSESSMENT",
  "name": "Risk Assessment",
  "description": "…",
  "status": "EMERGING | ESTABLISHED | EMBEDDED | EXTRACTING",
  "ownerService": "risk-assessment-service | null",
  "relatedWorkItems": ["WI-001"],
  "evidence": ["free text, or a repo-relative path"] }
```

### Service

```jsonc
{ "serviceId": "application-service",
  "name": "Application Service",
  "status": "PLANNED | IMPLEMENTED | SUPERSEDED | WITHDRAWN",
  "capabilities": ["CAP-APPLICATION"],
  "repositoryPaths": ["services/application-service"],
  "ownedData": ["Application"],
  "dependencies": ["review-service"],
  "decisionReference": "AP-create-application-001" }
```

`PLANNED` — approved, not yet realized. `IMPLEMENTED` — realized after
`gate_implement`. `SUPERSEDED` — ownership moved elsewhere. `WITHDRAWN` — a
`PLANNED` service whose decision was abandoned (D14); reclaimable by a later
placement, never deleted.

### Candidate

```jsonc
{ "id": "ARCH-CAND-004",
  "capability": "CAP-RISK-ASSESSMENT",
  "currentOwner": "application-service",
  "state": "OPEN | EXTRACTING | EXTRACTED | DISMISSED | ABANDONED",
  "evidence": ["WI-002"],
  "reevaluateWhen": ["a second risk-assessment WorkItem arrives", "…"],
  "decisionReference": "AP-initial-risk-assessment-001" }
```

### DataOwnership

```jsonc
{ "data": "RiskAssessment",
  "ownerService": "application-service",
  "viaCapability": "CAP-RISK-ASSESSMENT",
  "embedded": true,
  "status": "PLANNED | ACTIVE | SUPERSEDED | WITHDRAWN",
  "decisionReference": "AP-initial-risk-assessment-001" }
```

Service-level ownership only. **No physical schema, ever.**

*(R1-019)* `PLANNED` is load-bearing and was added during implementation: it is
the state a new ownership row sits in between `apply` and `realize`, when the
previous owner still owns the datum and the new one does not yet. Without it
the "exactly one `ACTIVE` owner per datum" invariant would be briefly false by
construction. `EXTRACTING` joins the candidate states for the same reason — a
candidate whose extraction is approved but not yet realized is in neither
`OPEN` nor `EXTRACTED`.

*(R1-006)* Every catalog entity also carries **`introducedBy`**, written once
at creation and never updated. `decisionReference` says which decision last
touched an entity and moves; `introducedBy` says which decision the entity
would not exist without. The abandonment cascade reads `introducedBy`, because
disposing of a decision may only dispose of what that decision created — a
candidate another WorkItem created and this one merely re-stated is not this
one's to withdraw.

### Decision

```jsonc
{ "id": "AP-detailed-risk-assessment-001",
  "workItem": "detailed-risk-assessment",
  "outcome": "EXTRACT_EXISTING_CAPABILITY",
  "baseRevision": 6,
  "appliedRevision": 7,
  "proposalDigest": "sha256:…",
  "renderedArtifact": "workitems/detailed-risk-assessment/architecture/placement.md",
  "renderedSha256": "…",
  "status": "PROPOSED | APPROVED_PENDING_IMPLEMENTATION | IMPLEMENTED | SUPERSEDED | ABANDONED",
  "appliedAt": "…", "realizedAt": null, "abandonedAt": null,
  "abandonedBy": null,
  "supersedes": [] }
```

`PROPOSED` never reaches the catalog — it is the status inside the WorkItem
record before approval. The catalog's first recorded status is
`APPROVED_PENDING_IMPLEMENTATION`.

### Validation the engine performs (deterministic, no judgement)

- `catalogVersion` is `1`, else `architecture_catalog_version_unsupported` (exit 3).
- Object shape, unique ids, closed enums, no dangling reference
  (candidate → capability, service → capability, dataOwnership → service),
  else `architecture_catalog_invalid` (exit 3).
- No two `ACTIVE` `dataOwnership` rows for the same `data`
  → `architecture_conflicting_ownership`.
- Unreadable / unparseable is an **integrity failure**, never "absent".

---

## 5. The proposal — `architecture assess --input <proposal.json>`

```jsonc
{
  "architectureProposalVersion": "1",
  "baseArchitectureRevision": 6,
  "introducesTechnologyDecision": false,   // envelope-level; the one D12
                                           // input the engine cannot derive

  "bootstrapDelta": {                       // optional; §3.3 / D13
    "basis": "DISCOVERY | BASELINE",
    "capabilities": [], "services": [], "dataOwnership": [],
    "evidence": [ { "statement": "…", "paths": ["services/application-service"] } ]
  },

  "placement": {                            // required; exactly one outcome
    "outcome": "EXTEND_EXISTING_SERVICE | CREATE_NEW_SERVICE |
                KEEP_EMBEDDED_AND_MONITOR | EXTRACT_EXISTING_CAPABILITY |
                ARCHITECTURE_REVIEW_REQUIRED",
    "capability":    { "id": "CAP-RISK-ASSESSMENT", "name": "…", "description": "…" },
    "currentOwner":  "application-service | null",
    "targetOwner":   "risk-assessment-service | null",
    "affectedServices": ["application-service", "risk-assessment-service"],
    "dataOwnership": [ /* DataOwnership deltas */ ],
    "candidates":    [ /* Candidate creations / transitions */ ],
    "dimensions": [ { "dimension": "data_ownership", "finding": "…" } ],
    "rationale": "…",
    "migrationImplications": "…",
    "integrationImpact": "…",
    "reevaluateWhen": ["…"],
    "confidence": "HIGH | MEDIUM | LOW",
    "openQuestions": ["…"],
    "relatedWorkItems": ["…"]              // from bound context only
  }
}
```

### Outcome enum — frozen, closed, exactly five

```
EXTEND_EXISTING_SERVICE
CREATE_NEW_SERVICE
KEEP_EMBEDDED_AND_MONITOR
EXTRACT_EXISTING_CAPABILITY
ARCHITECTURE_REVIEW_REQUIRED
```

### Evidence dimensions — closed vocabulary, emitted by `architecture schema`

```
business_capability_cohesion   business_responsibility   domain_aggregate_invariants
data_ownership                 transactional_boundaries  lifecycle_independence
change_coupling                integration_dependencies  security_boundary
independent_scaling            availability_differences  deployment_independence
existing_code_ownership        related_workitems         existing_adrs
existing_candidates
```

**No numeric score is computed, stored or accepted.** Dimensions are evidence.
The engine requires that the dimensions *relevant to the chosen outcome* are
addressed (rule table below); it never judges whether a finding is true.

### What the engine enforces / does not enforce

**Enforced** — version, envelope, closed enums, exactly one `placement`,
outcome-specific required fields, every referenced capability/service either
exists in the catalog or is introduced by this same proposal, `baseRevision` is
an integer, D12's constitution rules, bootstrap evidence cites paths that exist,
no `bootstrapDelta` when the catalog is already initialized.

**`constitutionStatus` is not a proposal field.** The engine resolves it (§6)
and stamps it into the record and the rendering. Asking the model to restate a
value the engine derives, then refusing on mismatch, is a failure mode that
carries no information.

**Not enforced** — whether the placement is architecturally *right*, whether a
rationale is sound, whether the evidence is complete. Those are claims by their
author, exactly as `discovery schema` says of discovery findings.

### Outcome-specific required fields

| Outcome | Must carry |
|---|---|
| `EXTEND_EXISTING_SERVICE` | `currentOwner` = `targetOwner`, an existing `IMPLEMENTED` or `PLANNED` service. A `WITHDRAWN` or `SUPERSEDED` boundary is not extendable |
| `CREATE_NEW_SERVICE` | `targetOwner` naming a service not already `IMPLEMENTED` — a `WITHDRAWN` boundary is *reclaimed* this way (D14); a resolved constitution (§6) |
| `KEEP_EMBEDDED_AND_MONITOR` | `currentOwner`; at least one candidate with a non-empty `reevaluateWhen` |
| `EXTRACT_EXISTING_CAPABILITY` | `currentOwner` ≠ `targetOwner`; `migrationImplications`; a `dataOwnership` delta; a resolved constitution (§6) |
| `ARCHITECTURE_REVIEW_REQUIRED` | `openQuestions` non-empty. **Not approvable** — see §8. |

---

## 6. Constitution availability (D12 / §3.8)

`constitutionStatus` is **resolved by the engine**, never proposed:

- `state.approvals["gate_constitution"]` is non-null **and** the
  `ARTIFACT_OWNERSHIP` constitution path resolves on disk → `PRESENT`.
  (Non-null rather than `decision == "approved"`: `gate_constitution` is in the
  built-in policy's `required_gates_always`, so it cannot be omitted today —
  but a project policy is read from disk and the rule should not depend on
  that staying true.)
- Else, a sound `.sdle/baseline.json` whose `references.constitution` resolves
  on disk → `PRESENT`. **This is the `ITERATIVE` case** (§3.8: report `PRESENT`
  when that reference resolves, not `ABSENT`).
- Else → `ABSENT`.

The resolved value is stamped into `architecture-placement.json` and rendered
into `placement.md`.

| Outcome | `ABSENT` behaviour |
|---|---|
| `CREATE_NEW_SERVICE` | refuse `architecture_constitution_required` |
| `EXTRACT_EXISTING_CAPABILITY` | refuse `architecture_constitution_required` |
| `EXTEND_EXISTING_SERVICE` | permitted **only** when the proposal introduces no new service, no ownership transfer and no new technology decision. *(R1-007)* All three are checked: the technology flag is declared, the new boundary is derived from `targetOwner` against the catalog, and the ownership transfer is derived from the `dataOwnership` delta against the current `ACTIVE` owners. Otherwise refuse `architecture_constitution_required` |
| `KEEP_EMBEDDED_AND_MONITOR` | same rule as above |
| `ARCHITECTURE_REVIEW_REQUIRED` | always permitted to record — it is the escape hatch, and it cannot be approved |

The placement artifact **never synthesizes a substitute constitution**.

---

## 7. Command surface

```
sdle.sh architecture schema                            no WorkItem, writes nothing
sdle.sh architecture show                              read-only; valid on an empty catalog
sdle.sh architecture assess --input <proposal.json>    validate + persist WorkItem record & evidence
sdle.sh --workitem <id> architecture apply             gate-approval path only
sdle.sh --workitem <id> architecture realize           gate_implement-approval path only
```

`--workitem` (and `--session`) are global options and go before the subcommand;
any command may take them, and `show` and `schema` need neither.

New sub-parser names for `COMMANDS` in `test_units_invariants.py`:
`architecture`, `apply`, `realize` (`schema`, `assess`, `show` already exist).

`apply` and `realize` are **invoked by the engine's own gate path**, not left to
the agent: `cmd_gate_approve` calls `architecture_apply` for
`gate_architecture` and `architecture_realize` for `gate_implement`, after the
existing preconditions and before the first audit append, in the same style
`establish_baseline` is called from the final gate. The standalone subcommands
exist for replay after a crash and for diagnosis.

`architecture show` on an uninitialized catalog:

```json
{ "initialized": false, "revision": 0, "catalog": null,
  "path": ".sdle/architecture/catalog.json" }
```

It invents nothing.

### Agent write fence

The hook's fence list is `FENCED = (".workflow", "workitems", "requirements",
"guidance")` in `.claude/hooks/hooks.py:63` — repository-relative path prefixes,
**a separate list from the engine's `SDLE_OWNED_PREFIXES`**, matched by
`fenced_target` as `inside == name or inside.startswith(name + "/")`.

- Both WorkItem placement artifacts sit under `workitems/` and are **already
  fenced**. Nothing to add.
- `.sdle/architecture` is added as a new `FENCED` entry, with a matching
  `FENCE_REASONS` string. `.sdle/` is deliberately **not** fenced wholesale:
  `config init` writes `.sdle/config.json` and a human edits `.sdle/policies/`.

The guarantee remains the engine's refusal at the choke point; the hook is a
tripwire (existing doctrine, unchanged).

---

## 8. Gate behaviour

**Approve** → `cmd_gate_approve`, for `gate_architecture` only:

1. existing `required_gate_artifact` → resolves `placement.md`, fingerprints it
2. existing `review_precondition` → PASS review of *that exact* SHA
3. new `architecture_binding_precondition` (inside `gate_precondition_hook`) →
   the WorkItem record exists, its `decisionId`/`proposalDigest` match the
   rendering, and its recorded `renderedSha256` equals the SHA just computed;
   else `architecture_artifact_binding_invalid`
4. new `architecture_outcome_precondition` → outcome is not
   `ARCHITECTURE_REVIEW_REQUIRED`; else `architecture_decision_unresolved`
5. `architecture apply` — revision check, delta, `revision += 1`, decision
   recorded `APPROVED_PENDING_IMPLEMENTATION`
6. existing approval + audit + advance to `spec_draft`

Steps 1–4 are **pure readers before the first write**, so a refusal leaves
`state.json` and `audit.md` byte-identical — the rule `cmd_gate_approve`
already follows for `governance_precondition` and friends.

**Reject** → the existing remediation path. `GATE_TO_EXECUTION_PHASE` sends
re-execution back to `architecture_placement`, SDLE-native, under the existing
`max_remediation_attempts` limit.

**Omit** → impossible (§3).

---

## 9. Revision, replay safety, concurrency

`apply` compares `record.baseRevision` with `catalog.revision`:

| Condition | Result |
|---|---|
| equal | apply the delta, `revision += 1`, record the decision |
| **the catalog already holds a decision with this `id` and the same `proposalDigest`** | **idempotent replay** — emit `{"replayed": true}`, revision unchanged, nothing written, exit 0 |
| the catalog holds this `id` with a **different** `proposalDigest` | `architecture_decision_conflict` (exit 1) |
| otherwise unequal | `architecture_catalog_stale` (exit 1), nothing written, message says to rerun `architecture_placement` |

`realize` is the same shape: a decision already `IMPLEMENTED` with the same
digest is an idempotent replay and must not mutate twice.

`proposalDigest` = `sha256` over `json.dumps(validated_proposal, sort_keys=True,
separators=(",", ":"))` — the validated proposal only, no timestamps, no
execution id. Deterministic across machines.

All writes go through `write_atomic`. **No global lock across the lifecycle.**

---

## 10. WorkItem artifacts and the JSON ↔ Markdown binding (D15)

| Artifact | Path | Written by |
|---|---|---|
| Structured record | `workitems/<id>/.sdle/architecture-placement.json` | `architecture assess` |
| Rendered artifact | `workitems/<id>/architecture/placement.md` | `architecture assess` |
| Evidence | `workitems/<id>/.sdle/evidence/architecture-<executionId>.json` | `architecture assess` |

The record stores `decisionId`, `proposalDigest`, `renderedArtifact` and
`renderedSha256`. The rendering prints `decisionId` and `proposalDigest` in a
header block. `apply` verifies all three against what is on disk **now**. A
hand-edited `placement.md` therefore fails `architecture_artifact_binding_invalid`
rather than becoming architecture truth — and independently fails
`review_stale`, because the PASS review was recorded against the old SHA.

Rendered sections, in order: WorkItem · business capability · known related
WorkItems · catalog revision · current owner · decision · target owner ·
affected services · data-ownership impact · integration impact · rationale ·
evidence dimensions considered · candidates affected · migration implications ·
re-evaluation conditions · confidence · open architecture questions ·
constitution status.

---

## 11. Abandonment (D14)

The **engine** marks a decision `ABANDONED` deterministically. Three triggers:

| Trigger | Where |
|---|---|
| `restart phase N` where the target's flow index ≤ index of `architecture_placement` | `cmd_restart`, after the confirm, alongside the existing approval clearing |
| `reset workflow --confirm` on a WorkItem holding an `APPROVED_PENDING_IMPLEMENTATION` decision | `cmd_reset`, before the state files are deleted |
| a rerun placement for the same WorkItem is approved | `architecture apply`, when a prior decision for this WorkItem is still `APPROVED_PENDING_IMPLEMENTATION`. *(R1-012)* That disposition records **`SUPERSEDED`**, not `ABANDONED` — the decision was replaced rather than walked away from, and `architecture show` distinguishes the two — and it emits `architecture_decision_abandoned` like the other two triggers, so no disposition reaches the catalog without a ledger entry |

Cascade, always append-only — **catalog history is never rewritten**:

- decision → `ABANDONED` for `restart` and `reset`, **`SUPERSEDED`** for a rerun *(R1-012)*; `abandonedAt` is set and `abandonedBy` records which of `restart|reset|superseded` it was. The status and the `abandonedBy` value are two different fields and only the second is always the same word as the trigger
- any service it created with status `PLANNED` → `WITHDRAWN`
  (never deleted, never left `PLANNED`; a later placement may reclaim it)
- candidates and `dataOwnership` rows introduced solely by it → `ABANDONED` /
  `WITHDRAWN`
- `revision += 1`, audit event `architecture_decision_abandoned`

A service already `IMPLEMENTED` is never withdrawn by an abandonment.

**Reset has no audit ledger to write to.** `cmd_reset` deletes `state.json`,
`audit.md` and `lock`. The catalog disposition — `status: ABANDONED`,
`abandonedBy: "reset"` — is therefore the **only durable record** of a reset
abandonment, which is precisely why it is a catalog write and not an audit
entry. Consequence, stated deliberately: a catalog that cannot be read
(`architecture_catalog_invalid`, exit 3) now **blocks `reset workflow`** — and
`restart` to or before the placement phase, which runs the same cascade. That
is fail-closed and intended — losing shared architectural history silently is
the outcome D14 exists to prevent.

`architecture show` distinguishes `APPROVED_PENDING_IMPLEMENTATION`,
`IMPLEMENTED`, `SUPERSEDED` and `ABANDONED`.

---

## 12. Realization (`gate_implement` approval)

- every service the decision created: `PLANNED` → `IMPLEMENTED`
- ownership the decision superseded: `ACTIVE` → `SUPERSEDED`
- for `EXTRACT_EXISTING_CAPABILITY`: the source candidate → `EXTRACTED`, the
  capability → `ESTABLISHED`
- decision → `IMPLEMENTED`, `realizedAt` set, `revision += 1`

Every `1.18` WorkItem has passed `gate_architecture` before it can reach
`gate_implement`, so a missing decision at realization is an integrity failure
(`architecture_placement_missing`), not a tolerated no-op.

---

## 13. Dirty-tree treatment (D10 / §3.4.1) — **the one change to existing behaviour**

Today `SDLE_OWNED_PREFIXES` (`sdle.py:9683`) contains `".sdle/"` — the whole
repository configuration boundary is invisible to the implementation dirty-tree
guard. D10 requires `.sdle/config.json` and `.sdle/policies/` to be **visible**.
The prefix tuple is therefore **narrowed**, which makes the guard *stricter*:

```python
SDLE_OWNED_PREFIXES = (
    ".workflow/",
    ".sdle/baseline.json",          # engine-written at the final gate
    ".sdle/implementation-state/",  # Paths.implementation_state_dir, sdle.py:301
    ".sdle/architecture/",          # NEW — engine-written catalog
    "workitems/", ".specify/", "design/", "reviews/",
    "clarifications/", "guidance/", "requirements/",
)
```

- `workitems/` already covers **both** WorkItem placement artifacts. §3.4.1's
  question is answered by the repository: no new rule is needed there.
- `.sdle/config.json` and `.sdle/policies/` become visible to the guard — a
  human edit to either now trips `dirty_tree`, which is the behaviour D10 asks
  for and the direction the prompt permits (stricter, never weaker).
- The in-code rationale for owning `baseline.json` is preserved verbatim: one
  WorkItem's baseline write must not trip another WorkItem's guard.
- `.sdle/implementation-state/` stays owned. It is an engine-known location
  (`Paths.implementation_state_dir`) holding execution records of maintenance
  runs, and D10 names only `config.json` and `policies/` as the content that
  must become visible. Making a directory of run logs trip `dirty_tree` would
  be a behaviour change D10 did not ask for.
- **`hooks.py` does not mirror this tuple.** Its `FENCED` list is a different
  mechanism for a different job (see §7). Only `sdle.py` changes here.

**ADR-013 must state that this amends ADR-002's repository-boundary semantics**,
because lifecycle execution now consumes and mutates repository-level
architecture knowledge — which ADR-002 did not contemplate.

---

## 14. Refusal reasons

| Reason | Exit | Trigger |
|---|---|---|
| `architecture_catalog_invalid` | 3 | catalog unreadable, unparseable, not an object, dangling reference, duplicate id |
| `architecture_catalog_version_unsupported` | 3 | `catalogVersion` not `1` |
| `architecture_catalog_stale` | 1 | `apply`/`realize` base revision ≠ current, and not an idempotent replay |
| `architecture_placement_missing` | 1 | `apply`/`realize`/`gate approve` with no WorkItem record |
| `architecture_placement_invalid` | 1 | proposal fails envelope, enum, required-field or constitution-agreement validation |
| `architecture_record_invalid` *(R2-008)* | 3 | the WorkItem's `architecture-placement.json` is unreadable, of another version, or names another WorkItem. Split from the row above because a corrupt engine-written record is an integrity failure with a different remedy, and one reason may not carry two exit codes |
| `architecture_capability_unknown` | 1 | proposal references a capability neither in the catalog nor introduced by it |
| `architecture_service_unknown` | 1 | same, for a service |
| `architecture_conflicting_ownership` | 1 | the delta would leave two `ACTIVE` owners for the same data |
| `architecture_decision_unresolved` | 1 | `gate approve` on an `ARCHITECTURE_REVIEW_REQUIRED` placement |
| `architecture_constitution_required` | 1 | D12 — the outcome needs an approved constitution and none resolves |
| `architecture_artifact_binding_invalid` | 1 | D15 — decision id / digest / rendered SHA mismatch |
| `architecture_decision_conflict` | 1 | D11 — same decision id already applied with a different digest; a decision that was abandoned or superseded; or *(R2-008)* `architecture assess` re-run after `gate_architecture` was **approved or omitted**. A *rejected* gate is deliberately not this case: rejection is the documented way back into the phase |

`constitution_missing` is **not** reused: it does not exist in the engine today.

Every reason gets a deterministic trigger, a test, and a
`docs/troubleshooting/README.md` entry with a deterministic remedy. **There is
no central reason table in `sdle.py`** — reasons are literals at their raise
site and the troubleshooting document is the enumerated home (Wave A mapping).

---

## 15. Guidelines (§5.1)

```
.claude/skills/sdle/guidelines/
├── constitution.md            → constitution_draft
├── architecture-placement.md  → architecture_placement
├── service-planning.md        → plan_draft
├── task-generation.md         → tasks_draft
├── service-design.md          → design_generation
└── implementation.md          → implement
```

Trusted product content, lazily loaded through `CAPABILITY_MAP`, advisory only.
Precedence chain, stated in `modules/architecture-placement.md` and ADR-014:

```
1 approved requirements → 2 constitution → 3 approved architecture decisions
→ 4 approved WorkItem spec/design → 5 SDLE guidelines → 6 agent judgement
```

Project-level `guidance/architecture-placement.md` stays optional, untrusted,
and flows through the existing Guidance File Map and `accept content`. **Two
levels, never merged.**

---

## 16. Documentation

| Artefact | Number |
|---|---|
| ADR — Project architecture memory and placement | **ADR-013** |
| ADR — Constitution, guidelines and decision precedence | **ADR-014** |
| Dry run — placement into an existing service | **17** |
| Dry run — embedded candidate, then later extraction | **18** |
| Dry run — stale revision from a concurrent WorkItem | **19** |
| Dry run — legacy / brownfield catalog bootstrap | **20** |

`docs/dry-runs/verification-matrix.md` and `tests/test_dry_run_contracts.py`
extend to cover 17–20. CLAUDE.md's "the next number is ADR-013" line becomes
ADR-015.

---

## 17. Worked-example domain (§0.4)

```
Capabilities:  CAP-APPLICATION, CAP-RISK-ASSESSMENT, CAP-REVIEW
Services:      application-service, review-service, risk-assessment-service
WorkItems:     WI-001 Create Application            → create-application
               WI-002 Initial Risk Assessment       → initial-risk-assessment
               WI-003 Detailed Risk Assessment      → detailed-risk-assessment
               WI-004 Review Approval Transition    → review-approval-transition
Candidate:     ARCH-CAND-004
```

`workitem create --name "Initial Risk Assessment"` normalizes to the kebab-case
slug `initial-risk-assessment` and uses it as the id; only `--auto-generate`
produces the `WI-<slug>-<stamp>` form (`sdle.py:2280`). Decision ids therefore
read `AP-initial-risk-assessment-001`, not `AP-WI002-001`. **Repository reality
wins on names** (§0.3.1); the `WI-00n` labels stay as prose in the scenarios.

---

## 18. Propagation checklist for Wave C (the non-obvious entries)

Beyond the tables in §2, these restate a count or a phase list and must move:

- `SKILL.md` — the `## The GREENFIELD Flow — 18 Phases, 8 Gates` heading, the
  GREENFIELD phase table's rows and renumbering, and the worked header example
  `progress=3/18` / `Phase 3/18` in Step 3.
- `CLAUDE.md` — "mandatory **ten**-phase governance floor" → twelve; the
  `.claude/skills/sdle/` module list; the "next number is ADR-013" line → 015;
  the documentation-set table (`docs/enhancements/` is new but is *not* added
  to the lint-enforced set — that set is the shipped product's derived views).
- `README.md` and `docs/SDLE-Reference-Guide.md` — phase tables
  (`doc_lists_every_phase_*`), every flow-size claim
  (`doc_flow_counts_match_engine`), the version string.
- `docs/lifecycle/README.md`, `docs/risk-and-gates/`, `docs/brownfield/`,
  `docs/workitems/`, `docs/spec-kit-integration/`, `docs/GETTING-STARTED.md`.
- `modules/phase-execution.md` — a block for `architecture_placement` whose
  ordinal is its **GREENFIELD position (4)**, and renumbering of every later
  block (`execution_block_numbers_are_the_greenfield_positions`).
- `modules/gate-protocol.md` — the `GATE_TO_EXECUTION_PHASE` row.
- `tests/test_units_invariants.py` — `GREENFIELD_PHASES`,
  `WRITE_PRIMITIVE_COUNTS`, `COMMANDS`, each with the reason in the comment
  block, in the same commit as the engine change.
