# Tutorial — `ITERATIVE`: the second WorkItem in the same repository

**Applies to:** SDLE v1.17

**16 phases, 7 gates.** Use this flow in a repository that already has a valid
baseline — which, in practice, means every WorkItem after the first one.

`ITERATIVE` is the flow you will spend most of your time in, and the whole
point of it is what it does *not* do. It does not draft a constitution: the
repository already has one, approved at a gate by a human, and fingerprinted in
the baseline. It does not run `discovery`: the repository was read once, the
findings were classified and recorded, and the baseline names the record they
live in. Those two omissions are the sixteen phases; everything else is
`GREENFIELD` unchanged.

That is worth stating plainly, because the temptation in a governed lifecycle
is to make each run re-establish its own footing. If every WorkItem
rediscovered the repository, the second one would pay the first one's cost
again, the third would pay it a third time, and the surveys would slowly
disagree with each other. SDLE spends that cost once and then converges.

This tutorial continues the repository from
[brownfield-discovery.md](brownfield-discovery.md): the `inventory-api` stock
service, whose first WorkItem — `stock-reservations` — completed and wrote the
baseline. The second WorkItem is low stock alerts: notice that a SKU is running
out before a pick fails.

---

## 1. Two WorkItems, one repository

Nothing about the repository layout changes. A second WorkItem is a second
directory under `workitems/`, with its own runtime, its own governance record
and its own audit chain. Ask the registry:

```
$ sdle.sh workitem create --name "Low stock alerts" --type enhancement --synopsis "Warn before a SKU runs out instead of after"
{
  "ok": true,
  "command": "workitem create",
  "reason": null,
  "data": {
    "id": "low-stock-alerts",
    "name": "low-stock-alerts",
    "title": "Low stock alerts",
    "type": "enhancement",
    "synopsis": "Warn before a SKU runs out instead of after",
    "created_at": "2026-09-08T10:12:23Z",
    "path": ".../workitems/low-stock-alerts",
    "metadata_file": ".../workitems/low-stock-alerts/workitem.json",
    "index_file": ".../workitems/index.md"
  }
}
--- exit 0 ---

$ sdle.sh workitem list
{
  "ok": true,
  "command": "workitem list",
  "reason": null,
  "data": {
    "count": 2,
    "workitems": [
      {
        "id": "stock-reservations",
        "created": "2026-09-08T10:11:45Z",
        "type": "enhancement",
        "title": "Stock reservations"
      },
      {
        "id": "low-stock-alerts",
        "created": "2026-09-08T10:12:23Z",
        "type": "enhancement",
        "title": "Low stock alerts"
      }
    ]
  }
}
--- exit 0 ---
```

From here on every command needs to know which of the two it is acting on.
`workitem resolve` reports what the resolution ladder would pick and never
refuses; `--workitem <id>` settles it explicitly, and `workitem use` persists a
choice for this working directory. The rungs, and what each one is evidence of,
are in [`workitems/`](../workitems/README.md#5-resolution--how-a-command-finds-its-workitem).

---

## 2. A second discovery is refused

The mechanism that makes "discover once" real is not documentation. Suppose you
assess this WorkItem as `BROWNFIELD_DISCOVERY` — either out of habit, or
because the repository has changed enough that a second survey feels warranted.
The assessment itself succeeds: `governance assess` records what you claimed,
and claiming a flow is not the same as binding one.

`init` is where it is decided:

```
$ sdle.sh init
{
  "ok": false,
  "command": "init",
  "reason": "baseline_present",
  "data": {
    "workitem": "low-stock-alerts",
    "flow": "BROWNFIELD_DISCOVERY",
    "baseline_status": "VALID",
    "path": ".sdle/baseline.json",
    "findings": [],
    "baseline_commit": "675ca7448683051ae2670a7d015df371e5d292e8"
  },
  "message": "This repository already has a VALID baseline at .sdle/baseline.json, so BROWNFIELD_DISCOVERY would rediscover what has already been discovered. Contract §14 performs full repository discovery once. Either re-assess this WorkItem as ITERATIVE, which is what a repository with a baseline is for, or record classification.rediscovery as true to ask for a deliberate rediscovery."
}
--- exit 1 ---
```

Three things about that refusal are deliberate.

It fires **before anything is created**. No runtime directory, no state file, no
audit chain. A wrong answer to "which flow" costs you a re-assessment and
nothing else, which is why guessing at the decision guide is cheap and
`baseline show` is the honest way to answer it.

It names **`baseline_commit`**. The claims in a baseline were true of a
particular repository state, and every refusal that rests on the baseline says
which one, so a finding is never floating free of the commit it was about.

It names **both** escape routes, and they are not the same escape. Re-assessing
as `ITERATIVE` is the ordinary answer. The other one —
`classification.rediscovery: true` — asks for a *deliberate* second survey, and
the engine allows it: `init` then binds a 19-phase `BROWNFIELD_DISCOVERY` and
puts you back at `discovery`, exactly as the first WorkItem was. The flag is
permitted only alongside `BROWNFIELD_DISCOVERY`, and it is recorded in the
governance verdict, so a rediscovery is always an entry in the record rather
than a thing that quietly happened. Use it when the repository genuinely is not
the one that was surveyed — a rewrite, a merge of two services — and not
because a survey would be convenient.

---

## 3. Binding `ITERATIVE`

Re-assess with the flow the repository is actually in. The governance input is
identical to a greenfield one except for `classification.flow`:

```json
"classification": { "type": "enhancement", "flow": "ITERATIVE" },
"risk": {
  "signals": ["external_api_surface", "persistent_data_store"],
  "proposedLevel": "MEDIUM",
  "uncertainty": "LOW"
}
```

```
$ sdle.sh init
{
  "ok": true,
  "command": "init",
  "reason": null,
  "data": {
    "project_name": "Low stock alerts",
    "workitem": "low-stock-alerts",
    "active_context": "low-stock-alerts",
    "execution_id": "sdl-20260908T101230Z",
    "requirements": [
      "low-stock-alerts.md",
      "reservations.md"
    ],
    "current_phase": "spec_draft",
    "status": "pending",
    "progress": "2/16",
    "audit_sha": "08b4648d2cc46b5aefe078bb87632d5f3810d0bdc2ee7f4f16b2daa494fbdf3d"
  }
}
--- exit 0 ---

$ sdle.sh header
--- stderr ---
<!-- SDLE_STATE phase=spec_draft status=pending progress=2/16 -->
📋 SDLE Status: Phase 2/16 — Generate Specification [PENDING]
--- exit 0 ---
```

Phase 2 of 16 is `spec_draft`. In `GREENFIELD` that position holds
`constitution_draft` and in `BROWNFIELD_DISCOVERY` it holds `discovery`; here
the work starts at the specification, because the two phases those flows spend
first were spent already.

`requirements` lists **both** documents. The requirements directory is
repository-level and accumulates: the reservations requirement that the first
WorkItem was written from is still there, and the requirements digest this
assessment recorded covers the directory as it now stands. That is intended —
it is the same repository — but it does mean an edit to an *old* requirement
document makes the *current* WorkItem's governance stale — `governance_stale`,
and the remedy is to re-assess. See
[§12 of the Reference Guide](../SDLE-Reference-Guide.md#12-state-audit-trail--traceability).

```
$ sdle.sh flow show
{
  "ok": true,
  "command": "flow show",
  "reason": null,
  "data": {
    "name": "ITERATIVE",
    "phases": [
      "requirements_check",
      "spec_draft",
      "gate_spec",
      "plan_draft",
      "gate_plan",
      "checklist_draft",
      "tasks_draft",
      "gate_tasks",
      "analyze",
      "gate_analyze",
      "design_generation",
      "gate_design",
      "implement",
      "gate_implement",
      "security_review",
      "gate_security",
      "complete"
    ],
    "phase_count": 16,
    "gate_phases": [
      "gate_spec",
      "gate_plan",
      "gate_tasks",
      "gate_analyze",
      "gate_design",
      "gate_implement",
      "gate_security"
    ],
    "gate_total": 7,
    "current_phase": "spec_draft",
    "position": 2,
    "progress": "2/16",
    "next_phase": "gate_spec",
    "gate_number": null,
    "label": "Generate Specification",
    "proposed_flow": "ITERATIVE",
    "agrees": true
  }
}
--- exit 0 ---
```

Set that beside `GREENFIELD`'s eighteen and the difference is exactly
`constitution_draft` and `gate_constitution`. `checklist_draft`, `analyze` and
`design_generation` are all still here: an existing repository still gets a
fresh design document, because a design describes the change, not the
repository.

---

## 4. The gate that is not there

Seven gates, and the interesting one is the eighth:

```
$ sdle.sh governance gates
```

At `MEDIUM` risk with an `enhancement` type:

| Gate | Disposition | Reasons |
|---|---|---|
| `gate_spec` | required | `always` |
| `gate_plan` | required | `always` |
| `gate_tasks` | required | `risk:MEDIUM` |
| `gate_analyze` | **omittable** | — |
| `gate_design` | required | `risk:MEDIUM` |
| `gate_implement` | required | `always` |
| `gate_security` | required | `terminal_gate` |

and, separately from the dispositions:

```
    "required_gates": [
      "gate_design",
      "gate_implement",
      "gate_plan",
      "gate_security",
      "gate_spec",
      "gate_tasks"
    ],
    "omittable_gates": [
      "gate_analyze"
    ],
    "required_not_in_flow": [
      "gate_constitution"
    ],
```

`gate_constitution` is in `required_gates_always` — the policy demands it of
every WorkItem, at every risk level, and no repository override may drop it.
`ITERATIVE` does not contain it. The engine does not resolve that by quietly
treating it as satisfied, and it does not resolve it by refusing the flow. It
reports it, in its own field, as **`required_not_in_flow`**.

That is the shape to internalise, because it recurs in every short flow. A gate
the policy requires and the flow does not contain is *named in the record*. The
justification for its absence is not in the engine — it is that the
constitution was approved by a human in the WorkItem that established this
repository's baseline, and the baseline still fingerprints the file that was
approved. The record lets a later reader check that story rather than take it
on faith.

`gate_security`, meanwhile, is required for the positional reason: it is the
last gate before `complete`. At `MEDIUM` the risk policy does not ask for it,
and there is no repository policy that can remove it. That rule is derived from
the flow's shape, so it applies to `ITERATIVE`'s seven gates exactly as it
applies to `HOTFIX`'s three — see [hotfix.md](hotfix.md#4-the-gate-that-cannot-be-removed).

---

## 5. What the WorkItem inherits, and what it does not

An `ITERATIVE` WorkItem has no discovery record of its own, and says so:

```
$ sdle.sh discovery show
{
  "ok": false,
  "command": "discovery",
  "reason": "discovery_missing",
  "data": {
    "workitem": "low-stock-alerts",
    "path": ".../workitems/low-stock-alerts/.sdle/discovery.json"
  },
  "message": "WorkItem 'low-stock-alerts' has no discovery record. Run `discovery assess --input <path>` first."
}
--- exit 1 ---
```

That is not a gap to fill. The repository's discovery lives in
`workitems/stock-reservations/.sdle/discovery.json`, and the baseline names it
by path *and* by SHA-256 along with the finding counts. `baseline show` is how
this WorkItem reads what the repository knows about itself: the constitution and
its fingerprint, the architecture documents, the ADRs a discovery finding cited,
and the `nonNegotiables` block pointing at the finding ids that declared them.

Reading it is not optional in practice. `F-013` in that record says the
derive-the-level invariant is non-negotiable; a specification for low stock
alerts that computed a stored level would contradict a constraint the
repository has already committed to, and nothing in the engine will catch that
for you. Gates catch it, because a human reads the artifact — which is why the
baseline is the first thing to put in front of the specification phase.

The rest of the walk is the per-phase pattern from
[greenfield.md §6](greenfield.md#6-walking-the-phases), unchanged: generate,
`artifact record`, `advance`, then at each gate `gate show`, `artifact review`,
`gate approve`. The conversational form is
[`dry-runs/01-happy-path.md`](../dry-runs/01-happy-path.md).

---

## 6. Completion does not re-establish the baseline

Approving the final gate ends the WorkItem, and the difference from a
baseline-establishing flow is visible in the approval itself:

```
$ sdle.sh gate approve --gate gate_security
{
  "ok": true,
  "command": "gate approve",
  "reason": null,
  "data": {
    "gate": "gate_security",
    "sha": "7291ba4fa6eaf60b693283d08eb302d0f4a2678a5ed1f51eeea17d35c7689865",
    "drift_mode": false,
    "remaining_drift": [],
    "next_phase": "complete",
    "status": "completed",
    "progress": "16/16",
    "completion_summary": "workitems/low-stock-alerts/.sdle/completion-summary.json",
    "baseline": null
  }
}
--- exit 0 ---
```

`"baseline": null`. In [greenfield.md §7](greenfield.md#7-what-completion-leaves-behind)
and in the brownfield run, that field named `.sdle/baseline.json`, because those
two flows establish it. `ITERATIVE` is not an establishing flow, so the baseline
it inherited is the baseline it leaves — `establishedBy` still names
`stock-reservations` and the `BROWNFIELD_DISCOVERY` execution that wrote it.

The audit chain is the WorkItem's own, not the repository's:

```
$ sdle.sh audit verify
{
  "ok": true,
  "command": "audit verify",
  "reason": null,
  "data": {
    "expected": "4cf00ca0e59c8c023f2e6d3d4d57e776552e143dea11020fee35e84ee3ab0848",
    "actual": "4cf00ca0e59c8c023f2e6d3d4d57e776552e143dea11020fee35e84ee3ab0848",
    "matches": true,
    "entries": 30,
    "chain_ok": true,
    "broken_at_entry": null
  }
}
--- exit 0 ---
```

Thirty entries for sixteen phases and seven gates, hash-chained, in
`workitems/low-stock-alerts/.sdle/audit.md`. The first WorkItem's ledger is
untouched beside it. Nothing in SDLE ever appends to a completed WorkItem's
chain, which is what makes "this WorkItem did that" a checkable statement years
later.

---

## 7. The baseline goes stale, and that is not a failure

This WorkItem regenerated `design/app/app-design.md` — `design_generation` is in
the flow, and the design of a service that now has reservations *and* alerts is
not the design that was fingerprinted. So:

```
$ sdle.sh baseline show
{
  "ok": true,
  "command": "baseline show",
  "reason": null,
  "data": {
    "status": "STALE",
    "path": ".sdle/baseline.json",
    "present": true,
    "findings": [
      {
        "check": "baseline_reference_changed",
        "severity": "warning",
        "workitem": null,
        "detail": ".sdle/baseline.json references design/app/app-design.md, which exists but has changed since the baseline was established; a changed reference is reported, never a refusal — later WorkItems legitimately rewrite design documents",
        "path": ".../design/app/app-design.md"
      }
    ],
    ...
```

Note `"severity": "warning"`, and note that the finding argues its own case.
Staleness here is the expected outcome of doing the work, not evidence that
something went wrong. Treating it as invalidation would push the third WorkItem
in every repository back into full rediscovery — which is precisely the cost
this flow exists to avoid.

So the third WorkItem starts normally:

```
$ sdle.sh init
{
  "ok": true,
  "command": "init",
  "reason": null,
  "data": {
    "project_name": "Movement archival",
    "workitem": "movement-archival",
    "active_context": "movement-archival",
    "execution_id": "sdl-20260908T103200Z",
    "requirements": [
      "low-stock-alerts.md",
      "movement-archival.md",
      "reservations.md"
    ],
    "current_phase": "spec_draft",
    "status": "pending",
    "progress": "2/16",
    "audit_sha": "d1f1d98ea72a85bb58af14a047f3df1cc40dde4a8b67f25af2d675f7e2b25414"
  }
}
--- exit 0 ---
```

A **stale** baseline is a warning that binds nothing. An **invalid** one — one
that no longer parses, or that names a referenced file which has been deleted —
blocks `ITERATIVE` outright, because a baseline whose references cannot be
resolved is not a weaker claim about the repository, it is no claim at all.
That distinction, and what to do about each, is in
[`brownfield/`](../brownfield/README.md#stale-is-a-warning-invalid-is-a-refusal).

---

## Where to go next

- **The concepts** — discover once, the four baseline statuses, repository-level
  artifacts: [`brownfield/`](../brownfield/README.md).
- **The decision record**:
  [ADR-005](../architecture/ADR-005-brownfield-discovery-and-baseline.md).
- **Where the baseline came from**:
  [brownfield-discovery.md](brownfield-discovery.md), or
  [greenfield.md](greenfield.md) if this repository started empty.
- **Customising any of this** — policy overrides, gate omission, drift
  re-approval, agent reviews: [greenfield-full-tour.md](greenfield-full-tour.md).
- **Something refused**: [`troubleshooting/`](../troubleshooting/README.md).
