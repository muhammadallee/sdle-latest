# Tutorial — `HOTFIX`: the shortest flow, and what it still enforces

**Applies to:** SDLE v1.17

**10 phases, 3 gates.** Use this flow when something is wrong in production
right now and the shortest governed path is the correct path.

This is the flow most likely to be misread, so read this first: **`HOTFIX` is
not an escape hatch.** It is a *named, recorded decision* to trade four gates
for time, and everything that made the other flows trustworthy is still
running underneath it. The risk assessment still fires and its hard floors
still cannot be lowered. The gates the policy wanted are still named in the
record, by gate, even the ones this flow cannot provide. The last gate before
`complete` is still required and cannot be omitted, overridden or advanced
past. The audit chain is byte-for-byte the same mechanism. The design phrase is
"[shorter, but never ungoverned](../architecture/ADR-004-declarative-flow-model.md)",
and both halves are load-bearing.

What you are giving up is real: the plan gate, the tasks gate, the analysis
gate and the design gate. There is no design phase at all. The rest of this
tutorial is mostly about what remains.

---

## The worked example

The `inventory-api` stock service again, live. `GET /skus/<code>/movements`
filters on the SKU code alone. Codes are unique per warehouse, not globally, so
a caller scoped to one warehouse receives the movement history of every
warehouse that happens to use the same code.

That is a cross-tenant data disclosure, in production, right now. It is also a
one-predicate fix: the `warehouse` column already exists and is populated. This
is what a hotfix is supposed to look like — a small, well-understood change to
a boundary that is currently wrong.

---

## 1. The risk floor fires whether you like it or not

Under time pressure the temptation is to call the change small, and it *is*
small. Suppose the governance input says so:

```json
"classification": { "type": "hotfix", "flow": "HOTFIX" },
"risk": {
  "signals": ["authentication_or_authorization", "external_api_surface"],
  "proposedLevel": "LOW",
  "uncertainty": "LOW"
}
```

`proposedLevel: LOW` is the model's judgement, honestly recorded. Here is what
the engine does with it:

```
$ sdle.sh governance assess --input governance-input.json
{
  "ok": true,
  "command": "governance assess",
  "reason": null,
  "data": {
    "workitem": "cross-warehouse-disclosure",
    "record": "workitems/cross-warehouse-disclosure/.sdle/governance.json",
    "evidence": "workitems/cross-warehouse-disclosure/.sdle/evidence/governance-sdl-20260908T101624Z.json",
    "quality": "PASS",
    "advisory_findings": [],
    "classification": {
      "type": "hotfix",
      "flow": "HOTFIX",
      "advisory": false,
      "rediscovery": false
    },
    "risk": {
      "signals": [
        "authentication_or_authorization",
        "external_api_surface"
      ],
      "score": 5,
      "floorsApplied": [
        {
          "rule": {
            "signal": "authentication_or_authorization",
            "level": "HIGH"
          },
          "raisedTo": "HIGH"
        }
      ],
      "deterministicLevel": "HIGH",
      "proposedLevel": "LOW",
      "uncertainty": "LOW",
      "finalLevel": "HIGH",
      "loweringAttempted": true
    },
    "downgrade": null,
    "requirements_digest": "29d1d00a409037c18985bccce809d22fd52c04448326511cf98b54ebcbfa32e1",
    "policy": {
      "source": "builtin",
      "sha256": null
    }
  }
}
--- exit 0 ---
```

`finalLevel: HIGH`, `loweringAttempted: true`. Two independent mechanisms
produced that, and both are worth naming:

The **score** is 3 + 2 = 5, which clears the `HIGH` threshold of 5 on its own.
And separately, `authentication_or_authorization` carries a **hard floor** of
`HIGH` — a minimum that applies regardless of the score, recorded in
`floorsApplied` with the exact rule that fired and what it raised the level to.
Eight signals carry a `HIGH` floor, two carry `CRITICAL`, and two further
floors key on `uncertainty` rather than on any signal.

`finalLevel` is the maximum of the deterministic level and what was proposed.
A proposal *above* the computed level raises it; a proposal below it does
nothing at all except set `loweringAttempted`. **There is no branch in the
engine that returns a level below `deterministicLevel`** — the model proposes,
the policy decides, and the attempt is on the record either way. Choosing
`HOTFIX` does not touch any part of that: the flow decides which phases you
walk, and nothing about how risk is computed.

Nor does `HOTFIX` cap the level. Drive the same flow with
`credential_or_key_exposure` and the assessment comes back `CRITICAL`, floor
applied, and `init` accepts it. That is deliberate, and §3 is where it starts
to matter.

---

## 2. Ten phases

```
$ sdle.sh init --project "Cross warehouse disclosure"
{
  "ok": true,
  "command": "init",
  "reason": null,
  "data": {
    "project_name": "Cross warehouse disclosure",
    "workitem": "cross-warehouse-disclosure",
    "active_context": "cross-warehouse-disclosure",
    "execution_id": "sdl-20260908T101625Z",
    "requirements": [
      "cross-warehouse-disclosure.md"
    ],
    "current_phase": "impact_analysis",
    "status": "pending",
    "progress": "2/10",
    "audit_sha": "327db811f0d78a001d7c91e0f80ed7ab1ddbea27de30a86bb1e5d4128ae2b58a"
  }
}
--- exit 0 ---

$ sdle.sh flow show
{
  "ok": true,
  "command": "flow show",
  "reason": null,
  "data": {
    "name": "HOTFIX",
    "phases": [
      "requirements_check",
      "impact_analysis",
      "spec_draft",
      "gate_spec",
      "plan_draft",
      "tasks_draft",
      "implement",
      "gate_implement",
      "security_review",
      "gate_security",
      "complete"
    ],
    "phase_count": 10,
    "gate_phases": [
      "gate_spec",
      "gate_implement",
      "gate_security"
    ],
    "gate_total": 3,
    "current_phase": "impact_analysis",
    "position": 2,
    "progress": "2/10",
    "next_phase": "spec_draft",
    "gate_number": null,
    "label": "Impact Analysis",
    "proposed_flow": "HOTFIX",
    "agrees": true
  }
}
--- exit 0 ---
```

Read that list for what it *keeps*. `plan_draft` and `tasks_draft` are both
still there — they simply have no gates. You still write a plan and a task
list; nobody stops to approve them. Whether that trade is right is a judgement
about your incident, not something the engine decides for you.

Read it also for a property that is not visible in the output. The engine
defines a **ten-member mandatory phase set** that every flow must contain, and
`HOTFIX` is exactly that set plus `impact_analysis`. It is not "the short flow
somebody happened to write"; it is the floor, made into a flow. That is
enforced twice — by `lint-skill`'s `every_flow_retains_the_mandatory_phases`
check, and by the flow loader itself, which refuses a flow missing a mandatory
phase rather than traversing it. So `HOTFIX` cannot be made shorter by editing
a table: there is no shorter admissible flow. See
[ADR-004 §7](../architecture/ADR-004-declarative-flow-model.md).

The `impact_analysis` phase works exactly as it does in `DEFECT_FIX` — write
the analysis, `artifact record`, `artifact review`, and display it in full
before the first gate downstream. See
[defect-fix.md §4](defect-fix.md#4-the-impact-analysis). Under incident
pressure it is the phase you will most want to skip and the one most worth
keeping: it is where "what could regress" gets written down before anybody
touches a live query. Which is exactly why you cannot skip it — `advance` and
`skip` both refuse `impact_analysis_missing` until the analysis is recorded
and carries a current PASS review. `HOTFIX` drops gates; it does not drop
this.

---

## 3. The gates the policy wanted, and could not have

This is the part to take seriously.

```
$ sdle.sh governance gates
{
  "ok": true,
  "command": "governance gates",
  "reason": null,
  "data": {
    "workitem": "cross-warehouse-disclosure",
    "classification": {
      "type": "hotfix",
      "flow": "HOTFIX",
      "advisory": false,
      "rediscovery": false
    },
    "final_risk": "HIGH",
    "flow": "HOTFIX",
    "flow_source": "state",
    "dispositions": [
      {
        "gate": "gate_spec",
        "gate_phase": "gate_spec",
        "disposition": "required",
        "reasons": [
          "always"
        ]
      },
      {
        "gate": "gate_implement",
        "gate_phase": "gate_implement",
        "disposition": "required",
        "reasons": [
          "always"
        ]
      },
      {
        "gate": "gate_security",
        "gate_phase": "gate_security",
        "disposition": "required",
        "reasons": [
          "risk:HIGH",
          "terminal_gate"
        ]
      }
    ],
    "required_gates": [
      "gate_implement",
      "gate_security",
      "gate_spec"
    ],
    "omittable_gates": [],
    "required_not_in_flow": [
      "gate_analyze",
      "gate_constitution",
      "gate_design",
      "gate_plan",
      "gate_tasks"
    ],
    "registered_gates": [
      "gate_analyze",
      "gate_constitution",
      "gate_design",
      "gate_implement",
      "gate_plan",
      "gate_security",
      "gate_spec",
      "gate_tasks"
    ],
    "policy": {
      "source": "builtin",
      "sha256": null
    }
  }
}
--- exit 0 ---
```

`required_not_in_flow` lists **five** gates. At `HIGH` risk the policy requires
`gate_tasks`, `gate_analyze`, `gate_design` and `gate_security`; `always`
requires `gate_constitution`, `gate_spec`, `gate_plan` and `gate_implement`.
Seven distinct gates, and this flow contains three of them.

The engine does not resolve that by lowering the requirement, and it does not
resolve it by refusing the flow. It writes down, gate by gate, what the policy
asked for and what the chosen shape could not supply — and this record is part
of the governance verdict, alongside the `HIGH` risk level and the floor that
produced it. If somebody asks a year later why a cross-tenant disclosure fix
shipped without a design review, the answer is in a file, with the risk level
it was known to carry at the time.

That is the honest form of "never ungoverned". It does not mean the same gates
happened. It means the flow could not quietly pretend they did, and note that
`omittable_gates` is empty: nothing here is discretionary. Three gates,
all required, none removable.

---

## 4. The gate that cannot be removed

`gate_security` carries two reasons: `risk:HIGH` and `terminal_gate`. The first
would disappear at a lower risk level. The second never does.

`terminal_gate` is not a dictionary entry. It is derived from the flow's shape
— the last gate before `complete` is required, whatever gate that happens to be
— so it lives in no policy table and there is no key a repository override
could target to remove it. Repository policies are additionally **monotone**:
they may only make governance stricter, and every attempt to drop a required
gate is refused `policy_weakens_baseline`. Even if that were not so, there is
nothing here to drop.

The consequences are visible from three directions. First, you cannot walk past
it:

```
$ sdle.sh advance --to complete
{
  "ok": false,
  "command": "advance",
  "reason": "gate_not_approved",
  "data": {
    "gate": "gate_security",
    "phase": "gate_security",
    "decision": null
  },
  "message": "gate_security has not been approved (decision: none). A gate can only be passed by an explicit approval."
}
--- exit 1 ---
```

Second, you cannot declare it unnecessary. `gate omit` exists precisely for
gates the policy does not require — and it refuses here, naming both reasons,
the final risk level, and which policy produced them:

```
$ sdle.sh gate omit --gate gate_security
{
  "ok": false,
  "command": "gate",
  "reason": "gate_required",
  "data": {
    "gate": "gate_security",
    "phase": "gate_security",
    "final_risk": "HIGH",
    "reasons": [
      "risk:HIGH",
      "terminal_gate"
    ],
    "required_gates": [
      "gate_implement",
      "gate_security",
      "gate_spec"
    ],
    "omittable_gates": [],
    "policy": {
      "source": "builtin",
      "sha256": null
    }
  },
  "message": "gate_security requires a human approval and cannot be omitted (reasons: risk:HIGH, terminal_gate; final risk HIGH; policy builtin). Approve it, or reject it — a required gate has no third option."
}
--- exit 1 ---
```

*A required gate has no third option.* Approve, or reject and remediate.

Third, you cannot approve it on the strength of the file existing:

```
$ sdle.sh gate approve --gate gate_security
{
  "ok": false,
  "command": "gate",
  "reason": "review_missing",
  "data": {
    "gate": "gate_security",
    "path": "reviews/security-review-2026-09-08-1416.md",
    "current_sha": "01cce8932df10c5eb1ad8cb0e00f7cd45b97ed47bfd550b09d7d36e0c55c34f7"
  },
  "message": "reviews/security-review-2026-09-08-1416.md has not been reviewed, so gate_security cannot be approved. Contract TP-011: artifact existence is not evidence of artifact quality. Record one with `artifact review --path reviews/security-review-2026-09-08-1416.md --type <type> --result PASS --actor-type <human|agent|tool|test|system> --actor-name <name>`."
}
--- exit 1 ---
```

**Artifact existence is not evidence of artifact quality.** The security review
document must be written, reviewed, and the review must be bound to the exact
bytes that are on disk — edit the file after reviewing it and the approval
refuses `review_stale` instead.

The gate itself reports as the third of three, and required:

```
$ sdle.sh gate show --gate gate_security
{
  "ok": true,
  "command": "gate show",
  "reason": null,
  "data": {
    "gate": "gate_security",
    "gate_phase": "gate_security",
    "gate_number": 3,
    "gate_total": 3,
    "flow": "HOTFIX",
    "in_flow": true,
    "label": "Gate 3: Security Review Approval",
    "execution_phase": "security_review",
    "artifact_path": "reviews/security-review-2026-09-08-1416.md",
    "skipped_reason": null,
    "exists": true,
    "artifact_sha": "01cce8932df10c5eb1ad8cb0e00f7cd45b97ed47bfd550b09d7d36e0c55c34f7",
    "baseline_sha": null,
    "decision": null,
    "required": true,
    "requirement_reasons": [
      "risk:HIGH",
      "terminal_gate"
    ]
  }
}
--- exit 0 ---
```

Gate numbers are flow-relative. This is Gate 3 of 3 here and Gate 8 of 8 in
`GREENFIELD`; it is the same gate, over the same artifact, with the same
approval requirement.

---

## 5. What else is unchanged

**The implementation gate is not a formality either.** `gate_implement` —
Gate 2 of 3 here — is `always` required in every flow, and its artifact is the implementation manifest, which `manifest
build` produces rather than accepts: it enumerates the changed files, runs the
secrets scan over them and records the test result. `implement preflight`
refuses a dirty tree before any of that, on the grounds that uncommitted
changes would appear in the manifest as if the implementation had produced
them — and the bypass is logged, not silent.

**The security review is diffed against a pinned base.** `security-review
begin` pins the review filename and the base ref; `security-review evidence`
diffs against `implementation_base_ref`, not `HEAD~1`, so the review covers
what this WorkItem actually changed rather than whatever the last commit
happened to be.

**The audit chain is the same chain.** Ten phases produce fewer entries than
eighteen, but every entry is the same hash-linked record, `audit verify`
answers the same way, and a broken chain is exit 3 here as everywhere.

**No baseline is read or written.** Like `DEFECT_FIX`, this flow does not
consult the repository baseline and is not in `establishing_flows`. An incident
fix never waits on a repository-level artifact, and never declares one.

---

## 6. When *not* to use it

The engine will not stop you, so this is a judgement you own.

The flow is the right shape when the fix is small, the blast radius is
understood, and the delay of the full lifecycle is itself a risk to the
service. Cross-tenant disclosure through a missing predicate is exactly that.

It is the wrong shape when the fix needs a design, when the fix is a
rewrite wearing an incident's clothes, or when the analysis honestly says the
blast radius is not yet understood. `HOTFIX` gives up the design gate, and a
change that needs a design review is not a change that should be shipped
without one. Note that the flow is bound at `init` and there is deliberately no
command that re-binds it: re-assessing later with a different flow is refused
`flow_mismatch`. If the incident turns out to be bigger than a hotfix, that is
a new WorkItem, not a change of mind about this one.

The most useful discipline is the cheapest, and it costs nothing to run.
`governance gates` works **before** `init` — it answers from the governance
record rather than from bound state, and says so with `"flow_source": "record"`.
So assess honestly, read `required_not_in_flow`, and you will see exactly which
reviews you are choosing to do without while the choice is still free.

---

## Where to go next

- **A defect with time to do it properly**: [defect-fix.md](defect-fix.md) —
  fourteen phases, six gates, the same `impact_analysis` opening.
- **Why the flow is the mandatory floor plus one phase**:
  [ADR-004](../architecture/ADR-004-declarative-flow-model.md).
- **How the required gate set is derived, and what omission has to record**:
  [`risk-and-gates/`](../risk-and-gates/README.md).
- **Risk floors, and re-assessment as a gate-clearing device**:
  [`risk-and-gates/` §6](../risk-and-gates/README.md#6-re-assessment-is-not-a-gate-clearing-device).
- **The manifest, the secrets scan and the dirty-tree guard, as a
  conversation**:
  [`dry-runs/06-secrets-and-dirty-tree.md`](../dry-runs/06-secrets-and-dirty-tree.md).
- **Something refused**: [`troubleshooting/`](../troubleshooting/README.md).
