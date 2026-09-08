# Tutorial — `DEFECT_FIX`: a bug, with time to do it properly

**Applies to:** SDLE v1.17

**14 phases, 6 gates.** Use this flow when something is broken, you know it is
broken, and you are not in an incident. If you *are* in an incident, read
[hotfix.md](hotfix.md) instead — the difference is not urgency in the abstract,
it is which four gates you are willing to give up.

Fixing a defect is not a smaller version of building a feature; it starts from
a different question. A feature run opens by asking what the software should
do. A defect run opens by asking what the software already does, where the
broken behaviour reaches, and what will break if you change it. So the flow
opens with a phase the three feature flows do not have — **`impact_analysis`**,
which runs before the specification and has no gate of its own.

The other structural difference is that the flow never touches the repository
baseline. It does not read one, it does not require one, and it does not write
one. A defect is a defect whether or not anybody has run discovery here, and
making a correctness fix wait on a repository-level artifact is not a
governance rule anyone asks for.

---

## The worked example

The same `inventory-api` stock service the brownfield tutorial surveys: Flask
over SQLAlchemy over SQLite, stock levels derived by summing an append-only
`movements` table.

The defect is in the movement history endpoint. `GET /skus/<code>/movements`
orders by `recorded_at`, whose value comes from SQLite's `CURRENT_TIMESTAMP`
and has one-second resolution. Two movements appended inside the same second
come back in an arbitrary order, so the audit view of a busy SKU shows picks
before the receipts that supplied them. The *level* is correct — it is a sum,
and addition does not care about order. The story it tells is not.

That is a good defect for this tutorial precisely because it is small. The
blast radius is a sort key. The interesting question is what SDLE makes you
write down before you are allowed to touch it.

---

## 1. No baseline is consulted

```
$ sdle.sh baseline show
{
  "ok": true,
  "command": "baseline show",
  "reason": null,
  "data": {
    "status": "ABSENT",
    "path": ".sdle/baseline.json",
    "present": false,
    "findings": [],
    "baseline": null,
    "establishing_flows": [
      "GREENFIELD",
      "BROWNFIELD_DISCOVERY"
    ]
  }
}
--- exit 0 ---
```

`ABSENT` in a repository full of code would send a *feature* WorkItem to
`BROWNFIELD_DISCOVERY`. It sends a defect nowhere: `ITERATIVE` is the flow that
refuses `baseline_required` without one, and `DEFECT_FIX` is not `ITERATIVE`.
This run completes with the baseline still `ABSENT` — see §6.

---

## 2. Classification, and the gate it adds

The WorkItem is created with `--type defect`, and the governance input carries
the same value in `classification.type`:

```json
"classification": { "type": "defect", "flow": "DEFECT_FIX" },
"risk": { "signals": [], "proposedLevel": "LOW", "uncertainty": "LOW" }
```

No risk signals. Changing a sort key touches no external surface that was not
already there, stores nothing new, and cannot corrupt data — the movement log
is append-only and the fix does not write to it.

```
$ sdle.sh governance assess --input governance-input.json
{
  "ok": true,
  "command": "governance assess",
  "reason": null,
  "data": {
    "workitem": "movement-order",
    "record": "workitems/movement-order/.sdle/governance.json",
    "evidence": "workitems/movement-order/.sdle/evidence/governance-sdl-20260908T101547Z.json",
    "quality": "PASS",
    "advisory_findings": [],
    "classification": {
      "type": "defect",
      "flow": "DEFECT_FIX",
      "advisory": false,
      "rediscovery": false
    },
    "risk": {
      "signals": [],
      "score": 0,
      "floorsApplied": [],
      "deterministicLevel": "LOW",
      "proposedLevel": "LOW",
      "uncertainty": "LOW",
      "finalLevel": "LOW",
      "loweringAttempted": false
    },
    "downgrade": null,
    "requirements_digest": "1e18e0c1a0fd8dbb2eef46fe7674b0dfaff2d09158cdbcd15964007444f0c42d",
    "policy": {
      "source": "builtin",
      "sha256": null
    }
  }
}
--- exit 0 ---
```

`LOW` on every measure. Now look at what the gate policy does with it:

```
$ sdle.sh governance gates
```

| Gate | Disposition | Reasons |
|---|---|---|
| `gate_spec` | required | `always` |
| `gate_plan` | required | `always` |
| `gate_tasks` | required | **`type:defect`** |
| `gate_analyze` | omittable | — |
| `gate_implement` | required | `always` |
| `gate_security` | required | `terminal_gate` |

`gate_tasks` is required, and the reason is not the risk level. At `LOW` risk
the policy's `required_gates_by_risk` is empty; an `enhancement` with this
exact risk profile would find `gate_tasks` omittable. It is required here
because `required_gates_by_type` maps `defect` to `gate_tasks`, and that entry
exists for one reason: a defect fix that quietly grows past the defect is the
characteristic failure of defect work. Somebody is going to read the task list
and confirm that it is a fix and not a refactor with a fix inside it.

Type is a governance input in its own right, not a label. Three of the four
registered types carry an empty list; `defect` is the one that adds a gate. The
derivation, and why a `chore` and a `hotfix` do not, is in
[`risk-and-gates/`](../risk-and-gates/README.md#4-from-level-to-required-gates).

Note also what is *missing* from that table. `gate_constitution` is in
`required_gates_always`, and `DEFECT_FIX` has no `constitution_draft` phase, so
the engine reports it separately rather than pretending it was satisfied:

```
    "required_not_in_flow": [
      "gate_constitution"
    ],
```

A gate the policy demands and the flow does not contain is always named in the
record. It is never silently dropped.

---

## 3. `init` puts you in the analysis

```
$ sdle.sh init --project "Movement order"
{
  "ok": true,
  "command": "init",
  "reason": null,
  "data": {
    "project_name": "Movement order",
    "workitem": "movement-order",
    "active_context": "movement-order",
    "execution_id": "sdl-20260908T101548Z",
    "requirements": [
      "movement-order.md"
    ],
    "current_phase": "impact_analysis",
    "status": "pending",
    "progress": "2/14",
    "audit_sha": "49eb82ffd699cc6ef4658266df766a97f4518885f9ed5ebc0ac6b69860ee2b0a"
  }
}
--- exit 0 ---

$ sdle.sh header
--- stderr ---
<!-- SDLE_STATE phase=impact_analysis status=pending progress=2/14 -->
📋 SDLE Status: Phase 2/14 — Impact Analysis [PENDING]
--- exit 0 ---
```

The full shape:

```
$ sdle.sh flow show
{
  "ok": true,
  "command": "flow show",
  "reason": null,
  "data": {
    "name": "DEFECT_FIX",
    "phases": [
      "requirements_check",
      "impact_analysis",
      "spec_draft",
      "gate_spec",
      "plan_draft",
      "gate_plan",
      "tasks_draft",
      "gate_tasks",
      "analyze",
      "gate_analyze",
      "implement",
      "gate_implement",
      "security_review",
      "gate_security",
      "complete"
    ],
    "phase_count": 14,
    "gate_phases": [
      "gate_spec",
      "gate_plan",
      "gate_tasks",
      "gate_analyze",
      "gate_implement",
      "gate_security"
    ],
    "gate_total": 6,
    "current_phase": "impact_analysis",
    "position": 2,
    "progress": "2/14",
    "next_phase": "spec_draft",
    "gate_number": null,
    "label": "Impact Analysis",
    "proposed_flow": "DEFECT_FIX",
    "agrees": true
  }
}
--- exit 0 ---
```

Set against `GREENFIELD`'s eighteen, four phases are gone —
`constitution_draft`, `gate_constitution`, `checklist_draft` and the design
pair `design_generation`/`gate_design` — and `impact_analysis` is added. A
defect fix does not draft a constitution, because a defect is a claim that the
software already disagrees with the rules it has; and it does not generate an
architecture document, because a defect fix that changes the architecture is
not a defect fix.

---

## 4. The impact analysis

The phase has no gate, and it is easy to read that as "no discipline". It is
not. What it means is that the analysis is not a document a human approves in
isolation — it is the context in which they approve the *next* thing.

Write the analysis to a dated file under `reviews/`. What it must cover is
fixed by the phase contract: what is broken and where; the modules, tests,
interfaces and data the change reaches; the blast radius; what could regress;
and what must be verified before the fix ships. For this defect:

> **Blast radius** — `src/inventory/stock.py` (`history()`), `src/inventory/app.py`
> (the movement read route), `tests/test_stock.py` (the only behavioural test
> over this arithmetic, which asserts the level and never the order).
>
> **What could regress** — any caller that had come to depend on the current
> arbitrary order. The reporting export is the only known candidate.
>
> **What could not regress** — nothing is written. The movement log is
> untouched, so the fix cannot corrupt stored data.

Then record and review it:

```
$ sdle.sh artifact record --phase impact_analysis --path reviews/impact-analysis-2026-09-08-1030.md
{
  "ok": true,
  "command": "artifact record",
  "reason": null,
  "data": {
    "path": "reviews/impact-analysis-2026-09-08-1030.md",
    "sha256": "1a4db50cfa80e695c27cdca92230a2b8a9b01c1c771b06ecf578246bf2185ecc",
    "bytes": 872,
    "optional": false
  }
}
--- exit 0 ---

$ sdle.sh artifact review --path reviews/impact-analysis-2026-09-08-1030.md --type impact-analysis --result PASS --actor-type agent --actor-name sdle-orchestrator
{
  "ok": true,
  "command": "artifact review",
  "reason": null,
  "data": {
    "path": "reviews/impact-analysis-2026-09-08-1030.md",
    "sha256": "1a4db50cfa80e695c27cdca92230a2b8a9b01c1c771b06ecf578246bf2185ecc",
    "result": "PASS",
    "reviewType": "impact-analysis",
    "actor": {
      "type": "agent",
      "name": "sdle-orchestrator"
    },
    "evidenceId": "workitems/movement-order/.sdle/evidence/review-sdl-20260908T101552Z-1.json",
    "reviews": 1
  }
}
--- exit 0 ---
```

Two details are worth reading off that pair.

The **review is recorded last**, and it is bound to the SHA-256 the record
fingerprinted. Edit the analysis afterwards and the review is stale by exactly
the mechanism that makes a gate approval stale — which is the point: a review
applies to bytes, not to a filename.

The **actor is an agent**, `sdle-orchestrator`, and the review type is
`impact-analysis` rather than `gate-review`. TP-011 accepts five actor types —
`human`, `agent`, `tool`, `test`, `system` — and records which one it was. This
is an agent asserting it produced and checked the document, not a human
asserting they agree with it. The human's turn comes next.

```
$ sdle.sh advance --to spec_draft
{
  "ok": true,
  "command": "advance",
  "reason": null,
  "data": {
    "from": "impact_analysis",
    "to": "spec_draft",
    "status": "pending",
    "progress": "3/14"
  }
}
--- exit 0 ---
```

**Where the human reads it.** The phase has no gate, so the orchestrator
displays the analysis in full in the conversation, and again immediately before
the Gate 2 prompt — the first gate downstream of it. Gate 2 nominally approves
the specification; in a defect flow it is the point at which somebody with the
blast radius in front of them decides the fix is scoped correctly. If you are
driving the CLI yourself, that display is on you: `advance` will move out of
`impact_analysis` whether or not you recorded anything. Compare `discovery`,
which refuses `discovery_missing` and cannot be left without an accepted
record. The analysis is required by the phase contract, not by a refusal.

---

## 5. The rest of the flow

From `spec_draft` onward the pattern is `GREENFIELD`'s, with a 14-phase
denominator and flow-relative gate numbers — `gate_spec` reports as *Gate 1 of
6* here, where in `GREENFIELD` it is Gate 2 of 8. Generation phases write an
artifact, `artifact record` fingerprints it, `advance` moves one step. Gate
phases run `gate show`, `artifact review`, `gate approve`. The per-phase detail
is in [greenfield.md §6](greenfield.md#6-walking-the-phases) and the
conversational form in [`dry-runs/01-happy-path.md`](../dry-runs/01-happy-path.md).

Two flow-specific notes:

**`analyze` still refines `tasks.md`.** `gate_tasks` has already fingerprinted
that file, so the refinement would read as drift. Move the baseline
deliberately with `drift rebaseline --gate gate_tasks` rather than letting the
detector raise an alarm about a change everyone intended.

**There is no `checklist_draft`.** In `GREENFIELD` the checklist is recorded
`--optional` and reviewed alongside the tasks at Gate 4. `DEFECT_FIX` has no
checklist phase at all; the task list is the whole of what Gate 3 reviews.

---

## 6. Completion, and the baseline that is still absent

```
$ sdle.sh gate approve --gate gate_security
{
  "ok": true,
  "command": "gate approve",
  "reason": null,
  "data": {
    "gate": "gate_security",
    "sha": "01cce8932df10c5eb1ad8cb0e00f7cd45b97ed47bfd550b09d7d36e0c55c34f7",
    "drift_mode": false,
    "remaining_drift": [],
    "next_phase": "complete",
    "status": "completed",
    "progress": "14/14",
    "completion_summary": "workitems/movement-order/.sdle/completion-summary.json",
    "baseline": null
  }
}
--- exit 0 ---

$ sdle.sh baseline show
{
  "ok": true,
  "command": "baseline show",
  "reason": null,
  "data": {
    "status": "ABSENT",
    "path": ".sdle/baseline.json",
    "present": false,
    "findings": [],
    "baseline": null,
    "establishing_flows": [
      "GREENFIELD",
      "BROWNFIELD_DISCOVERY"
    ]
  }
}
--- exit 0 ---
```

Fourteen phases, six gate approvals, a completed WorkItem — and the repository
baseline is exactly as absent as it was before. `establishing_flows` names the
two flows that write it and `DEFECT_FIX` is not among them, so a defect fix
cannot declare a repository baseline it never gathered. If this repository
later wants one, the next *feature* WorkItem runs `BROWNFIELD_DISCOVERY`
and gets it, and this defect's audit chain sits untouched beside it.

```
$ sdle.sh audit verify
{
  "ok": true,
  "command": "audit verify",
  "reason": null,
  "data": {
    "expected": "a0949c6b436509998574ce4f424323a221435eaa78fd81c8429e0f4434df3d9f",
    "actual": "a0949c6b436509998574ce4f424323a221435eaa78fd81c8429e0f4434df3d9f",
    "matches": true,
    "entries": 29,
    "chain_ok": true,
    "broken_at_entry": null
  }
}
--- exit 0 ---
```

Twenty-nine hash-chained entries. A shorter flow is not a thinner ledger per
phase: every artifact registration, every review, every approval and every
advance is still its own record, including the impact analysis and its agent
review.

---

## Where to go next

- **The same defect, as an incident**: [hotfix.md](hotfix.md) — four fewer
  gates, and what is still enforced.
- **Why `type` adds a gate**:
  [`risk-and-gates/`](../risk-and-gates/README.md), and
  [ADR-006](../architecture/ADR-006-risk-adaptive-gate-policy.md) for the
  decision record.
- **Why `impact_analysis` is scoped to the two defect flows, and deliberately
  left out of the mandatory floor**:
  [ADR-004 §7](../architecture/ADR-004-declarative-flow-model.md).
- **Rejecting a gate and remediating**:
  [`dry-runs/02-gate-rejection-remediation.md`](../dry-runs/02-gate-rejection-remediation.md).
- **Something refused**: [`troubleshooting/`](../troubleshooting/README.md).
