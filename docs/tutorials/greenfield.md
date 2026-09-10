# Tutorial — `GREENFIELD`: a new project

**Applies to:** SDLE v1.17

**18 phases, 8 gates.** Use this flow when there is no code yet and nothing to
discover — a new service, a new component, the first thing in an empty
repository.

`GREENFIELD` is the longest flow and the only one that drafts a constitution,
because it is the only one where nobody has written the project's rules down
yet. Everything downstream — the specification, the plan, the design — is
checked against that constitution, so the first gate you meet is an approval of
what the project is allowed to be.

It is also the flow the [dry-run transcripts](../dry-runs/README.md) document.
Nine of them are `GREENFIELD` runs, and every transcript's claims are checked
against the engine by the test suite. **For what the conversation looks like — what SDLE prints at a gate,
what you type to approve, how a rejection reads — read
[`01-happy-path.md`](../dry-runs/01-happy-path.md) rather than this file.**
This tutorial covers the layer underneath: the commands the orchestrator
issues, and the two things that are specific to greenfield work — where the
flow comes from, and the baseline it leaves behind.

---

## 1. Before you start

You need a `requirements/` directory with at least one document in it. `init`
refuses `requirements_missing` otherwise, and it refuses before it creates
anything.

Requirements quality is not a formality here. Twelve structured checks are
evaluated against what you wrote, and all twelve block — a FAIL on any of them
stops the workflow. Write the document so a reader can answer them: state the
problem, the scope, what is explicitly *out* of scope, testable acceptance
criteria, the constraints, and the dependencies. Only `nfrs` may be answered
`NOT_APPLICABLE`.

The example below uses a small internal link shortener.

```
$ sdle.sh workitem resolve
{
  "ok": true,
  "command": "workitem resolve",
  "reason": null,
  "data": {
    "resolved": null,
    "rung": null,
    "reason": "none",
    "candidates": [],
    "workitems": [],
    "branch": "main",
    "active_context": null
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

`ABSENT` is not a defect and emits no finding — most repositories have no
baseline. Here it is simply confirmation that there is nothing to inherit.

---

## 2. Name the work

A WorkItem is created *before* the workflow is initialised, and its id never
changes afterwards.

```
$ sdle.sh workitem create --name "Link shortener" --type enhancement --synopsis "Short, stable stand-ins for long internal URLs"
{
  "ok": true,
  "command": "workitem create",
  "reason": null,
  "data": {
    "id": "link-shortener",
    "name": "link-shortener",
    "title": "Link shortener",
    "type": "enhancement",
    "synopsis": "Short, stable stand-ins for long internal URLs",
    "created_at": "2026-09-08T04:10:29Z",
    "path": ".../workitems/link-shortener",
    "metadata_file": ".../workitems/link-shortener/workitem.json",
    "index_file": ".../workitems/index.md"
  }
}
--- exit 0 ---
```

The id is derived from the name. Pass `--auto-generate` instead if you want a
timestamped id, which is what the orchestrator does when you answer `auto
generate` to its prompt.

---

## 3. Assess the requirements — this is what binds the flow

`governance assess` is the step that decides which lifecycle this WorkItem will
traverse. It is run *before* `init`, and `init` reads
`classification.flow` out of the record it wrote.

The input is a JSON document with four top-level keys — `governanceInputVersion`,
`quality`, `classification`, `risk` — and nothing else; an unknown key is
refused rather than ignored. Claude fills it in from reading the requirements.

```json
{
  "governanceInputVersion": "1",
  "quality": {
    "problem_statement":          { "result": "PASS", "finding": null },
    "scope":                      { "result": "PASS", "finding": null },
    "out_of_scope":               { "result": "PASS", "finding": null },
    "acceptance_criteria":        { "result": "PASS", "finding": null },
    "ambiguity":                  { "result": "PASS", "finding": null },
    "contradictions":             { "result": "PASS", "finding": null },
    "constraints":                { "result": "PASS", "finding": null },
    "nfrs":                       { "result": "PASS", "finding": null },
    "security_data_implications": { "result": "PASS", "finding": null },
    "compatibility":              { "result": "PASS", "finding": null },
    "dependencies":               { "result": "PASS", "finding": null },
    "blocking_unknowns":          { "result": "PASS", "finding": null }
  },
  "classification": { "type": "enhancement", "flow": "GREENFIELD" },
  "risk": {
    "signals": ["external_api_surface", "persistent_data_store"],
    "proposedLevel": "MEDIUM",
    "uncertainty": "LOW"
  }
}
```

```
$ sdle.sh governance assess --input governance-input.json
{
  "ok": true,
  "command": "governance assess",
  "reason": null,
  "data": {
    "workitem": "link-shortener",
    "record": "workitems/link-shortener/.sdle/governance.json",
    "evidence": "workitems/link-shortener/.sdle/evidence/governance-sdl-20260908T041035Z.json",
    "quality": "PASS",
    "advisory_findings": [],
    "classification": {
      "type": "enhancement",
      "flow": "GREENFIELD",
      "advisory": false,
      "rediscovery": false
    },
    "risk": {
      "signals": [
        "external_api_surface",
        "persistent_data_store"
      ],
      "score": 4,
      "floorsApplied": [],
      "deterministicLevel": "MEDIUM",
      "proposedLevel": "MEDIUM",
      "uncertainty": "LOW",
      "finalLevel": "MEDIUM",
      "loweringAttempted": false
    },
    "downgrade": null,
    "requirements_digest": "e1d5d682154e45ffb46ce10472b64a192e19cfd6a06933b169c952240e38de4c",
    "policy": {
      "source": "builtin",
      "sha256": null
    }
  }
}
--- exit 0 ---
```

Two fields are worth reading carefully, because they are where the design shows
through.

`deterministicLevel` is what the policy computed: `external_api_surface` weighs
2 and `persistent_data_store` weighs 2, the total of 4 clears the `MEDIUM`
threshold of 2 but not `HIGH`'s 5. `finalLevel` is the *maximum* of that and
what the model proposed — so a proposal above the computed level raises it, and
a proposal below it does nothing except set `loweringAttempted` to `true`. The
model proposes; the engine decides. There is no branch in the engine that can
return a level below `deterministicLevel`.

`requirements_digest` fingerprints the requirements this assessment was made
against. Edit a requirements file afterwards and the next `advance` refuses
`governance_stale` until you re-assess — an assessment is about specific
content, not about a directory.

---

## 4. Start the workflow

```
$ sdle.sh init
{
  "ok": true,
  "command": "init",
  "reason": null,
  "data": {
    "project_name": "Link shortener",
    "workitem": "link-shortener",
    "active_context": "link-shortener",
    "execution_id": "sdl-20260908T041037Z",
    "requirements": [
      "link-shortener.md"
    ],
    "current_phase": "constitution_draft",
    "status": "pending",
    "progress": "2/18",
    "audit_sha": "706136d52fdc08df37b067fa779cec60f7a29bf82957b33ef3792fe036207e79"
  }
}
--- exit 0 ---
```

`init` performed phase 1 — the requirements check — and left the workflow
standing at phase 2. It also created the WorkItem runtime under
`workitems/link-shortener/.sdle/` and wrote the first two entries of the audit
chain.

```
$ sdle.sh header
--- stderr ---
<!-- SDLE_STATE phase=constitution_draft status=pending progress=2/18 -->
📋 SDLE Status: Phase 2/18 — Generate Constitution [PENDING]
--- exit 0 ---
```

That header is emitted first, every turn. It is the state assertion: the
orchestrator reads state before it acts, and shows you what it read.

```
$ sdle.sh flow show
{
  "ok": true,
  "command": "flow show",
  "reason": null,
  "data": {
    "name": "GREENFIELD",
    "phases": [
      "requirements_check",
      "constitution_draft",
      "gate_constitution",
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
    "phase_count": 18,
    "gate_total": 8,
    "current_phase": "constitution_draft",
    "position": 2,
    "progress": "2/18",
    "next_phase": "gate_constitution",
    "gate_number": null,
    "label": "Generate Constitution",
    "proposed_flow": "GREENFIELD",
    "agrees": true
  }
}
--- exit 0 ---
```

`agrees: true` means the bound flow and the flow the governance record proposes
are the same. If a later assessment proposed a different flow, this would read
`false` and the next `advance` would refuse `flow_mismatch` — the flow is bound
once and nothing re-binds it.

---

## 5. Which gates this WorkItem must clear

`GREENFIELD` *contains* eight gates. How many you must approve is derived per
WorkItem:

```
$ sdle.sh governance gates
```

At `MEDIUM` risk with an `enhancement` type, the dispositions come back as:

| Gate | Disposition | Reasons |
|---|---|---|
| `gate_constitution` | required | `always` |
| `gate_spec` | required | `always` |
| `gate_plan` | required | `always` |
| `gate_tasks` | required | `risk:MEDIUM` |
| `gate_analyze` | **omittable** | — |
| `gate_design` | required | `risk:MEDIUM` |
| `gate_implement` | required | `always` |
| `gate_security` | required | `terminal_gate` |

Seven required, one omittable. Note `gate_security`: at `MEDIUM` the risk
policy does not require it, but it is the flow's last gate before `complete`
and is therefore required as `terminal_gate` — a positional rule that lives in
no policy dictionary, so no repository override can remove it.

An `omittable` gate can still be approved by a human; approving is always
stricter than the policy demands. What it can never be is passed silently. See
[greenfield-full-tour.md](greenfield-full-tour.md#8-omitting-a-gate) for what
`gate omit` records.

---

## 6. Walking the phases

The pattern is the same at every phase, and it is worth learning once because
the other four flows use it unchanged.

**A generation phase** produces an artifact, registers it, and advances:

```
$ sdle.sh artifact record --phase spec_draft --path workitems/link-shortener/specs/001-link-shortener/spec.md
$ sdle.sh advance --to gate_spec
```

`artifact record` verifies the file exists and clears the 100-byte size floor,
then fingerprints it. A failure here does not advance the phase — it sets the
status to `failed` and offers a retry, which is the fail-safe rule: on any
failure, freeze.

**A gate phase** reviews the artifact and approves it:

```
$ sdle.sh gate show --gate gate_spec
$ sdle.sh artifact review --path <artifact> --type gate-review --result PASS --actor-type human --actor-name you
$ sdle.sh gate approve --gate gate_spec
```

The review is not optional decoration. Approving without one refuses
`review_missing`, and a review is bound to the exact bytes it was performed
against — change the file afterwards and the approval refuses `review_stale`.

`gate approve` is what advances past a gate. `advance` cannot do it: it moves
exactly one step, and it refuses `forward_jump` if you ask for anything else.

Two phases in `GREENFIELD` deviate slightly from the pattern. `checklist_draft`
records its artifact as `--optional`, because a checklist is reviewed alongside
the tasks at Gate 4 rather than gated on its own; and `analyze` refines
`tasks.md`, a file Gate 4 already fingerprinted, so it calls `drift rebaseline
--gate gate_tasks` to move that baseline deliberately rather than tripping the
drift detector with a change everyone intended.

The full conversational walk is
[`dry-runs/01-happy-path.md`](../dry-runs/01-happy-path.md).

---

## 7. What completion leaves behind

```
$ sdle.sh header
--- stderr ---
<!-- SDLE_STATE phase=complete status=completed progress=18/18 -->
📋 SDLE Status: Phase 18/18 — Complete [COMPLETED]
--- exit 0 ---
```

Approving the final gate does three things at once: it advances to `complete`,
writes a completion summary, and — because `GREENFIELD` is one of the two
baseline-establishing flows — writes the repository baseline.

```
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
      "establishedAt": "2026-09-08T04:11:54Z",
      "establishedBy": {
        "workitem": "link-shortener",
        "flow": "GREENFIELD",
        "executionId": "sdl-20260908T041154Z"
      },
      "commit": "67b6a02bd5d71393f5b14609644a0dcb4916046b",
      "discovery": {
        "status": "NOT_REQUIRED",
        "record": null,
        "recordSha256": null,
        "counts": null
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
        "adrs": []
      },
      "nonNegotiables": {
        "source": null,
        "findingIds": []
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

`discovery.status` is `NOT_REQUIRED`, and that word is doing real work. A
greenfield WorkItem performed no repository discovery — there was nothing to
discover — so the baseline it writes says so plainly rather than claiming
knowledge it never gathered. Compare the same field in
[brownfield-discovery.md](brownfield-discovery.md#6-the-rest-of-the-flow-and-the-baseline), where it
reads `PERFORMED` and carries the discovery record's fingerprint and finding
counts. For the same reason, `nonNegotiables` is empty here: a repository's
non-negotiables are read out of discovery findings, and there were none.

There is no `baseline establish` command. Nothing you can call writes this file
— letting a flow that performed no discovery declare a discovered baseline is
exactly what would make the invariant decorative.

The audit chain covers every one of those transitions and verifies:

```
$ sdle.sh audit verify
{
  "ok": true,
  "command": "audit verify",
  "reason": null,
  "data": {
    "expected": "0188b43e03130ea0bd2579fb378b1652df6434c2df7508f40c5af571666160fd",
    "actual": "0188b43e03130ea0bd2579fb378b1652df6434c2df7508f40c5af571666160fd",
    "matches": true,
    "entries": 40,
    "chain_ok": true,
    "broken_at_entry": null
  }
}
--- exit 0 ---
```

Forty entries for eighteen phases: every artifact registration, every review,
every approval and every advance is its own hash-chained record.

---

## What changes for the next WorkItem

The baseline is now `VALID`, so this repository has converged. The next
WorkItem in it will be `ITERATIVE`, and `BROWNFIELD_DISCOVERY` will be refused
`baseline_present`. Continue with [iterative.md](iterative.md).

## Where to go next

- **Customising any of this** — policy overrides, risk floors, gate omission,
  verbose mode, skip/restart/reset, drift re-approval, the four review
  subagents: [greenfield-full-tour.md](greenfield-full-tour.md).
- **The conversation, turn by turn**:
  [`dry-runs/01-happy-path.md`](../dry-runs/01-happy-path.md), and 02–09 for
  rejection, retry, drift, injection scanning, secrets, locking, rollback and
  bootstrap failures.
- **Something refused**: [`troubleshooting/`](../troubleshooting/README.md).
- **Why the phases are in this order**:
  [§7 of the Reference Guide](../SDLE-Reference-Guide.md#7-the-18-phase-workflow--detailed-reference).
