# Tutorial — `BROWNFIELD_DISCOVERY`: the first WorkItem in an existing codebase

**Applies to:** SDLE v1.17

**19 phases, 8 gates.** Use this flow the first time you run SDLE against a
repository that already contains code and has no baseline.

An existing repository already holds the decisions a greenfield WorkItem would
have to invent: an architecture, conventions, dependencies, constraints that
nobody wrote down as constraints. If every WorkItem rediscovered them, the
second WorkItem would pay the first one's cost again and the third would too.
So SDLE discovers **once per repository**, and writes the result to a durable
artifact that every later WorkItem converges onto.

That is what this flow is. It is `GREENFIELD` plus one gateless phase at the
front — `discovery` — and the same eight gates. The phase has no gate of its
own because what it produces is not a document for a human to approve; it is a
set of classified claims about the repository, and the engine checks the
classification mechanically.

---

## The worked example

A small warehouse stock service: Python, Flask, SQLAlchemy over SQLite, four
modules, one behavioural test, and one accepted ADR.

```
inventory-api/
├── README.md
├── requirements.txt
├── docs/adr/0001-movements-not-levels.md
├── src/inventory/{__init__,app,stock,models,db}.py
└── tests/test_stock.py
```

The ADR says: store an append-only log of stock *movements* and derive the
level by summing them, because a stored level is a cache that fails silently.
Remember that document — the flow finds it on its own, at the end.

The new requirement is stock reservations: hold a quantity of a SKU for an
order, without writing a movement.

---

## 1. Confirm there is nothing to inherit

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

`ABSENT` plus an existing codebase is what selects this flow. If it said
`VALID`, `init` would refuse `baseline_present` and tell you to use `ITERATIVE`
instead — see [iterative.md](iterative.md#2-a-second-discovery-is-refused).

---

## 2. Create the WorkItem and assess

```
$ sdle.sh workitem create --name "Stock reservations" --type enhancement --synopsis "Hold stock for an order without writing a movement"
{
  "ok": true,
  "command": "workitem create",
  "reason": null,
  "data": {
    "id": "stock-reservations",
    "name": "stock-reservations",
    "title": "Stock reservations",
    "type": "enhancement",
    "synopsis": "Hold stock for an order without writing a movement",
    "created_at": "2026-09-08T03:44:14Z",
    "path": ".../workitems/stock-reservations",
    "metadata_file": ".../workitems/stock-reservations/workitem.json",
    "index_file": ".../workitems/index.md"
  }
}
--- exit 0 ---
```

The governance input differs from a greenfield one in exactly one field —
`classification.flow` — plus a more honest risk assessment, because
reservations touch a live API and a live data store and introduce a
concurrency question the codebase already has a documented problem with.

```json
"classification": { "type": "enhancement", "flow": "BROWNFIELD_DISCOVERY" },
"risk": {
  "signals": ["external_api_surface", "persistent_data_store",
              "concurrency_or_distributed_state"],
  "proposedLevel": "MEDIUM",
  "uncertainty": "MEDIUM"
}
```

```
$ sdle.sh governance assess --input governance-input.json
{
  "ok": true,
  "command": "governance assess",
  "reason": null,
  "data": {
    "workitem": "stock-reservations",
    "record": "workitems/stock-reservations/.sdle/governance.json",
    "evidence": "workitems/stock-reservations/.sdle/evidence/governance-sdl-20260908T034415Z.json",
    "quality": "PASS",
    "advisory_findings": [],
    "classification": {
      "type": "enhancement",
      "flow": "BROWNFIELD_DISCOVERY",
      "advisory": false,
      "rediscovery": false
    },
    "risk": {
      "signals": [
        "concurrency_or_distributed_state",
        "external_api_surface",
        "persistent_data_store"
      ],
      "score": 6,
      "floorsApplied": [],
      "deterministicLevel": "HIGH",
      "proposedLevel": "MEDIUM",
      "uncertainty": "MEDIUM",
      "finalLevel": "HIGH",
      "loweringAttempted": true
    },
    "downgrade": null,
    "requirements_digest": "0d2f4831356c669fff619c108b61a624bbc2ec52471536372d985d3e1610e6e8",
    "policy": {
      "source": "builtin",
      "sha256": null
    }
  }
}
--- exit 0 ---
```

Three signals weighing 2 + 2 + 2 = 6 clear the `HIGH` threshold of 5. The
proposal of `MEDIUM` had no effect except to be recorded as
`loweringAttempted: true`. At `HIGH`, every one of the flow's eight gates
becomes required — `gate_tasks`, `gate_analyze`, `gate_design` and
`gate_security` all join the four that are always required, and nothing is
omittable.

---

## 3. `init`, and where it puts you

```
$ sdle.sh init
{
  "ok": true,
  "command": "init",
  "reason": null,
  "data": {
    "project_name": "Stock reservations",
    "workitem": "stock-reservations",
    "active_context": "stock-reservations",
    "execution_id": "sdl-20260908T034417Z",
    "requirements": [
      "reservations.md"
    ],
    "current_phase": "discovery",
    "status": "pending",
    "progress": "2/19",
    "audit_sha": "0aa11e0ee8a8b03bd0daf9dfb6e56af79f9d59d4b8f7f95cb03e78f4a8bc2c02"
  }
}
--- exit 0 ---

$ sdle.sh header
--- stderr ---
<!-- SDLE_STATE phase=discovery status=pending progress=2/19 -->
📋 SDLE Status: Phase 2/19 — Repository Discovery [PENDING]
--- exit 0 ---
```

Phase 2 of 19 is `discovery`, where `GREENFIELD` has `constitution_draft`. The
denominator is 19 rather than 18 for exactly that one extra phase.

---

## 4. The discovery vocabulary

Discovery is not free-form notes. Ask the engine what it accepts:

```
$ sdle.sh discovery schema
{
  "ok": true,
  "command": "discovery schema",
  "reason": null,
  "data": {
    "input_versions": ["1"],
    "envelope": ["discoveryInputVersion", "findings"],
    "finding_keys": ["id", "category", "classification", "statement",
                     "evidence", "basis"],
    "required_finding_keys": ["id", "category", "classification", "statement"],
    "categories": [
      "repository_inventory", "modules_components", "dependencies",
      "architecture", "significant_patterns", "conventions", "apis",
      "persistence_data_architecture", "test_practices", "runtime_deployment",
      "security_patterns", "adrs", "constraints_non_negotiables", "risks_debt"
    ],
    "classifications": ["OBSERVED", "INFERRED", "UNKNOWN"],
    "rules": {
      "R-a": "unknown or missing top-level key; unsupported discoveryInputVersion",
      "R-b": "findings must be a non-empty list of objects with only the declared finding keys",
      "R-c": "each finding needs a unique, non-empty string id",
      "R-d": "category must be one of the declared categories",
      "R-e": "classification is required and must be one of the declared classifications",
      "R-f": "statement is required and must be non-empty",
      "R-g": "an observation must cite at least one evidence path, and every cited path must exist inside this repository",
      "R-h": "an inference must name a basis, every basis id must be a declared finding, and no basis may itself be unknown",
      "R-i": "an unknown may not carry evidence",
      "R-j": "every declared category needs at least one finding"
    },
    "record_version": "1",
    "enforced": [
      "every finding carries one of the declared classifications",
      "an observation cites at least one path that exists in this repository",
      "an inference names a basis, and no basis is itself unknown",
      "an unknown carries no evidence",
      "every declared category carries at least one finding"
    ],
    "not_enforced": [
      "whether an observed statement is true of the file it cites",
      "whether an inference follows from its basis",
      "whether the findings are complete"
    ]
  }
}
--- exit 0 ---
```

The `enforced` / `not_enforced` split is the honest part of this design, and it
is worth reading before you write anything. Fourteen categories, each of which
must carry at least one finding, and three classifications:

- **`OBSERVED`** — you read it in a file. Must cite at least one evidence path,
  and every path must exist in this repository.
- **`INFERRED`** — you concluded it from other findings. Must name a `basis`,
  every basis id must be a declared finding, and none of them may itself be
  `UNKNOWN`. You cannot build a conclusion on an admitted ignorance.
- **`UNKNOWN`** — you do not know. May not carry evidence; an unknown that
  cites a file is not an unknown.

What the engine *cannot* check is whether you applied the right label to a
given statement. An `OBSERVED` finding citing a real file may still say
something false about it. That remains a claim by its author, and the schema
saying so out loud is the point: the value of the classification is that it
makes the author commit to which kind of claim they are making.

---

## 5. Recording the findings

Discovery is a job for a fresh context that reads the repository and nothing
else, which is what the shipped `sdle-discovery` subagent is for — read-only,
`Read`/`Grep`/`Glob` only, and fenced by a `PreToolUse` hook from writing
anything. It returns structured findings; the orchestrator records them.

A finding per category, in this repository, looks like this. Three of the
fourteen:

```json
{
  "id": "F-005",
  "category": "significant_patterns",
  "classification": "OBSERVED",
  "statement": "Stock levels are derived by summing movement rows rather than stored, and every mutation appends a movement.",
  "evidence": ["src/inventory/stock.py", "docs/adr/0001-movements-not-levels.md"]
},
{
  "id": "F-013",
  "category": "constraints_non_negotiables",
  "classification": "INFERRED",
  "statement": "The derive-the-level invariant is non-negotiable: it is an accepted ADR and the only behavioural test asserts it.",
  "basis": ["F-005", "F-009", "F-012"]
},
{
  "id": "F-011",
  "category": "security_patterns",
  "classification": "UNKNOWN",
  "statement": "No authentication, authorization or input-validation layer appears in the repository, and nothing records whether one is applied by an upstream proxy."
}
```

### The refusal names the rule it enforced

Get one wrong and you are told which rule, on which finding, and what the
offending value was — not that "something was invalid":

```
$ sdle.sh discovery assess --input bad-discovery.json
{
  "ok": false,
  "command": "discovery",
  "reason": "discovery_input_malformed",
  "data": {
    "path": "bad-discovery.json",
    "detail": "finding 'F-003': evidence path 'build.gradle' does not exist in this repository",
    "rule": "R-g",
    "finding": "F-003",
    "value": "build.gradle"
  },
  "message": "bad-discovery.json is not a usable discovery input: finding 'F-003': evidence path 'build.gradle' does not exist in this repository [R-g: an observation must cite at least one evidence path, and every cited path must exist inside this repository]."
}
--- exit 1 ---
```

That refusal is the cheapest guard against a plausible-sounding survey of a
repository the author never actually opened.

### The accepted record

```
$ sdle.sh discovery assess --input discovery-input.json
{
  "ok": true,
  "command": "discovery assess",
  "reason": null,
  "data": {
    "workitem": "stock-reservations",
    "record": "workitems/stock-reservations/.sdle/discovery.json",
    "evidence": "workitems/stock-reservations/.sdle/evidence/discovery-sdl-20260908T034423Z.json",
    "result": "PASS",
    "findings": 14,
    "counts": {
      "OBSERVED": 10,
      "INFERRED": 3,
      "UNKNOWN": 1
    },
    "categories": {
      "repository_inventory": ["F-001"],
      "modules_components": ["F-002"],
      "dependencies": ["F-003"],
      "architecture": ["F-004"],
      "significant_patterns": ["F-005"],
      "conventions": ["F-006"],
      "apis": ["F-007"],
      "persistence_data_architecture": ["F-008"],
      "test_practices": ["F-009"],
      "runtime_deployment": ["F-010"],
      "security_patterns": ["F-011"],
      "adrs": ["F-012"],
      "constraints_non_negotiables": ["F-013"],
      "risks_debt": ["F-014"]
    }
  }
}
--- exit 0 ---
```

Ten observed, three inferred, one unknown. That last number is not a failure —
it is the flow working. The repository genuinely does not record whether an
upstream proxy authenticates callers, and a survey that had guessed would have
been worse than one that says so.

`discovery show` reads the whole record back, findings included. The input file
is transient: it is consumed here and preserved verbatim in the evidence
document, so you do not need to keep it.

Then leave the phase:

```
$ sdle.sh advance --to constitution_draft
{
  "ok": true,
  "command": "advance",
  "reason": null,
  "data": {
    "from": "discovery",
    "to": "constitution_draft",
    "status": "pending",
    "progress": "3/19"
  }
}
--- exit 0 ---
```

Advancing out of `discovery` without a recorded, passing discovery record is
refused. There is no path through this flow that skips it.

---

## 6. The rest of the flow, and the baseline

From `constitution_draft` onward this is `GREENFIELD`, phase for phase, with a
19-phase denominator instead of 18. The per-phase pattern is in
[greenfield.md §6](greenfield.md#6-walking-the-phases) and the conversational
form is in [`dry-runs/01-happy-path.md`](../dry-runs/01-happy-path.md).

Approving the final gate writes the baseline:

```
$ sdle.sh gate approve --gate gate_security
{
  "ok": true,
  "command": "gate approve",
  "reason": null,
  "data": {
    "gate": "gate_security",
    "sha": "962d2debafafc13fa4e2133e7ab741bbd3acb988c45291986ef4e907bf43686f",
    "drift_mode": false,
    "remaining_drift": [],
    "next_phase": "complete",
    "status": "completed",
    "progress": "19/19",
    "completion_summary": "workitems/stock-reservations/.sdle/completion-summary.json",
    "baseline": ".sdle/baseline.json"
  }
}
--- exit 0 ---

$ sdle.sh baseline show
{
  "ok": true,
  "command": "baseline show",
  "reason": null,
  "data": {
    "status": "VALID",
    "path": ".sdle/baseline.json",
    "present": true,
    "findings": [],
    "baseline": {
      "baselineVersion": "1",
      "establishedAt": "2026-09-08T03:45:58Z",
      "establishedBy": {
        "workitem": "stock-reservations",
        "flow": "BROWNFIELD_DISCOVERY",
        "executionId": "sdl-20260908T034558Z"
      },
      "commit": "ee5071eea79cf2057eb323b61036374d3e0fc399",
      "discovery": {
        "status": "PERFORMED",
        "record": "workitems/stock-reservations/.sdle/discovery.json",
        "recordSha256": "d3d6affc10d740dbeaf2b65e38d1513ae7699c267c36e4c647da145c5169a7a3",
        "counts": {
          "OBSERVED": 10,
          "INFERRED": 3,
          "UNKNOWN": 1
        }
      },
      "references": {
        "constitution": {
          "path": ".specify/memory/constitution.md",
          "sha256": "d2bd037038b349dcaeac4f46de289c5915795e874b15b31671de0c3dae3d8172"
        },
        "architecture": [
          {
            "path": "design/app/app-design.md",
            "sha256": "0a1324b5496715192d40e1c32ed6e9fae7e5cdf5bfaec385c3ab43336b7ec209"
          }
        ],
        "adrs": [
          {
            "path": "docs/adr/0001-movements-not-levels.md",
            "sha256": "67d10ad63874f1141c112092acb07e9c068ee5abd4ee77ab8156851b613e5c43"
          }
        ]
      },
      "nonNegotiables": {
        "source": "workitems/stock-reservations/.sdle/discovery.json",
        "findingIds": [
          "F-013"
        ]
      },
      "supersedes": null
    },
    "establishing_flows": [
      "GREENFIELD",
      "BROWNFIELD_DISCOVERY"
    ]
  }
}
--- exit 0 ---
```

Three things in that document are worth pausing on, and all three are the
discovery phase paying off.

**`discovery.status` is `PERFORMED`**, with the record's SHA-256 and the
finding counts. The greenfield baseline in
[greenfield.md §7](greenfield.md#7-what-completion-leaves-behind) says
`NOT_REQUIRED` here, with nulls. A later reader can tell, from the baseline
alone, whether the claims it rests on came from a survey or from nothing.

**`references.adrs` names the pre-existing ADR** at
`docs/adr/0001-movements-not-levels.md`, fingerprinted. Nobody told the engine
about that file. It is there because a discovery finding cited it, so the ADR
this repository already had is now part of what the baseline rests on.

**`nonNegotiables` points at `F-013`** — the inferred finding that said the
derive-the-level invariant is non-negotiable. The baseline records *references*,
never copies: it names the finding id and the record it came from, so there is
one statement of that constraint rather than two that can diverge. This is why
the classification discipline matters. `F-013` was `INFERRED` from `F-005`,
`F-009` and `F-012`, none of which was `UNKNOWN`, and that chain is still
readable in `discovery.json`.

`commit` pins the repository state the baseline's claims were true of. When the
baseline later goes stale, both refusals name that commit, so a finding always
says which repository state it was ever about.

---

## What changes for the next WorkItem

The repository has converged. Discovery does not run again:
[iterative.md](iterative.md).

## Where to go next

- **The concepts** — discovery once, the four baseline statuses, why stale is a
  warning and invalid is a refusal:
  [`brownfield/`](../brownfield/README.md).
- **The decision record**:
  [ADR-005](../architecture/ADR-005-brownfield-discovery-and-baseline.md).
- **Deliberately discovering twice** — a genuine second survey is possible;
  record `classification.rediscovery` as `true`, which is permitted only
  alongside `BROWNFIELD_DISCOVERY`.
- **Something refused**: [`troubleshooting/`](../troubleshooting/README.md).
