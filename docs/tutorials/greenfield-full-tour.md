# Tutorial — the full tour: everything you can configure

**Applies to:** SDLE v1.17

**`GREENFIELD`, 18 phases, 8 gates.** This is the same flow as
[greenfield.md](greenfield.md), walked a second time with every knob turned. If
you want the shortest path through a new project, read that one. Read this one
when you are deciding what your repository's governance should be, or when
something has refused and you want to know whether it was policy, position or
principle that refused it.

The organising fact is that **customisation in SDLE is monotone**. Every knob
described here either tightens governance or changes presentation. There is no
knob that loosens it. A repository can demand more gates, raise its own risk
floors and invent signals for its own domain; it cannot lower a weight, remove
a floor, drop a required gate, or teach the engine to accept a risk level the
policy did not compute. That is not a convention — six specific weakening
shapes are refused by name, and this tutorial drives all six.

The worked example is a small on-call duty roster service: shifts, assignments,
swap requests, and a read API answering "who is on duty now".

---

## 1. The configuration boundary

Everything repository-level lives under one directory. Ask what the engine
thinks it is before creating anything — `config show` writes nothing:

```
$ sdle.sh config show
{
  "ok": true,
  "command": "config show",
  "reason": null,
  "data": {
    "root": ".sdle",
    "present": false,
    "config": {
      "configVersion": "1",
      "policyFormat": "json"
    },
    "defaults_applied": [
      "configVersion",
      "policyFormat"
    ],
    "members": {
      "config": ".sdle/config.json",
      "policies": ".sdle/policies",
      "templates": ".sdle/templates",
      "baseline": ".sdle/baseline.json",
      "implementation_state": ".sdle/implementation-state"
    }
  }
}
--- exit 0 ---
```

`present: false` with a populated `config` block is the important shape. An
absent `config.json` is not an error and not an unknown — it is a real answer,
and `defaults_applied` says exactly which values came from the defaults rather
than from disk. That distinction is why a repository that has never heard of
`.sdle/config.json` behaves identically to one that wrote the defaults out by
hand.

```
$ sdle.sh config init
{
  "ok": true,
  "command": "config init",
  "reason": null,
  "data": {
    "root": ".sdle",
    "config": {
      "configVersion": "1",
      "policyFormat": "json"
    },
    "created": [
      ".sdle/policies/.gitkeep",
      ".sdle/templates/.gitkeep",
      ".sdle/implementation-state/.gitkeep",
      ".sdle/config.json"
    ]
  }
}
--- exit 0 ---

$ sdle.sh config init
{
  "ok": false,
  "command": "config",
  "reason": "config_exists",
  "data": {
    "config_file": ".../.sdle/config.json",
    "config_root": ".sdle"
  },
  "message": ".sdle/config.json already exists; `config init` never overwrites an existing configuration. Edit it by hand, or delete it first."
}
--- exit 1 ---
```

`.sdle/policies/` is created **empty**, and it stays empty in most
repositories. That is not an oversight. The engine reads exactly one optional
file out of it — `.sdle/policies/governance-policy.json` — and nothing else in
the directory has any effect. The `.gitkeep` exists because Git cannot version
an empty directory and this boundary is meant to be committed.

`config.json` itself carries two values and no more: `configVersion` and
`policyFormat`. It is a marker for where the boundary is, not a settings file;
governance lives in the policy document. The reasoning is in
[ADR-002](../architecture/ADR-002-repository-configuration-boundary.md).

---

## 2. The policy override, and what "absent" means

With no override file, the effective policy is the built-in one and says so:

```
$ sdle.sh governance policy
{
  "ok": true,
  "command": "governance policy",
  "reason": null,
  "data": {
    "source": "builtin",
    "path": ".sdle/policies/governance-policy.json",
    "sha256": null,
    "policy": { ... }
  }
}
--- exit 0 ---
```

**The built-in policy is the weakest admissible policy.** That single fact is
what makes an absent file safe: there is nothing an override could have said
that would have made governance looser than the default already is, so
"missing" and "minimum" are the same answer.

The repository ships a worked override at
[`docs/risk-and-gates/example-governance-policy.json`](../risk-and-gates/example-governance-policy.json).
It is inert where it sits — copy it to `.sdle/policies/governance-policy.json`
to activate it, and strip the `_`-prefixed commentary keys when you do. Its own
comments record that it was written by hand once with six wrong signal weights,
and that the engine caught every one; generate your starting point with
`sdle.sh governance policy` rather than transcribing values.

Installed, the effective policy reports its provenance:

```
$ sdle.sh governance policy
{
  "ok": true,
  "command": "governance policy",
  "reason": null,
  "data": {
    "source": ".sdle/policies/governance-policy.json",
    "path": ".sdle/policies/governance-policy.json",
    "sha256": "e706b6415159ba7c50aa8bbdcd7632b88dc79b216775f2a8a49812d1195f4158",
    "policy": { ... }
  }
}
--- exit 0 ---
```

That `sha256` is not decoration. Every governance verdict this policy produces
reports the same `policy.source` and `policy.sha256`, so a verdict always names
the exact policy bytes behind it — and a gate omission carries the governance
record's own hash on top of that.

### Which keys merge, and which replace

This is the one mechanical detail worth learning before you write an override,
because getting it wrong produces a refusal that reads like a puzzle.

**Dictionary-valued keys merge entry by entry.** `risk_signals`,
`risk_thresholds`, `required_gates_by_risk` and `required_gates_by_type` are
merged with the built-in: naming three signals updates three weights and leaves
the other fourteen alone. So this is a complete, valid override that lowers the
`HIGH` threshold and nothing else:

```json
{ "policyVersion": "1", "risk_thresholds": { "HIGH": 4 } }
```

and this one adds the security gate at `MEDIUM` while leaving `HIGH` and
`CRITICAL` untouched:

```json
{
  "policyVersion": "1",
  "required_gates_by_risk": {
    "MEDIUM": ["gate_tasks", "gate_design", "gate_security"]
  }
}
```

**List-valued keys are compared as wholes.** `hard_floors`,
`required_gates_always` and `blocking_checks` replace, so a partial list *is* a
removal and is refused — adding one floor means restating all twelve and
appending the thirteenth. The lists nested inside `required_gates_by_risk` and
`required_gates_by_type` replace too: the dictionary merges by key, each key's
list does not.

`optional_checks` is the one list where the comparison runs the other way. It
names the quality checks that may be answered `NOT_APPLICABLE` — just `nfrs` in
the built-in — so *adding* to it is the weakening, refused with *it lets
constraints be reported NOT_APPLICABLE*, and shortening it to `[]` is a
tightening the engine accepts.

`quality_checks` is deliberately not overridable at all. The twelve check ids
belong to the contract; a repository that could rename or drop one would be
editing the contract rather than tightening it.

Only nine top-level keys may appear: `policyVersion`, `blocking_checks`,
`optional_checks`, `risk_signals`, `risk_thresholds`, `hard_floors`,
`required_gates_always`, `required_gates_by_risk`, `required_gates_by_type`.

---

## 3. Six ways to weaken a policy, and six refusals

Each of these was driven against the shipped example with one field changed.
The `message` is quoted verbatim; every one of them names the key, the specific
clause, and the built-in value it fell below.

**Lowering a signal weight** — `persistent_data_store` from 2 to 1:

```
policy_weakens_baseline: .sdle/policies/governance-policy.json weakens the
built-in governance policy at 'risk_signals': 'persistent_data_store' weighs 1,
below the built-in 2. A repository policy may only make governance stricter.
--- exit 1 ---
```

**Raising a threshold** — `HIGH` from 5 to 7. Note the engine explains the
direction rather than assuming you know it: a *lower* threshold number makes a
level *easier* to reach, so lowering is the tightening and raising is the
weakening.

```
policy_weakens_baseline: ... at 'risk_thresholds': HIGH now needs a score of 7,
above the built-in 5, so it is harder to reach. A repository policy may only
make governance stricter.
--- exit 1 ---
```

**Removing a hard floor** — dropping `payment_or_financial`:

```
policy_weakens_baseline: ... at 'hard_floors': the floor
signal='payment_or_financial' -> HIGH has been removed. A repository policy may
only make governance stricter.
--- exit 1 ---
```

**Demoting a floor's level** — `credential_or_key_exposure` from `CRITICAL` to
`HIGH`:

```
policy_weakens_baseline: ... at 'hard_floors': the floor
signal='credential_or_key_exposure' has been lowered from CRITICAL to HIGH. A
repository policy may only make governance stricter.
--- exit 1 ---
```

**Dropping gates from a risk level** — `HIGH` keeping only `gate_tasks` and
`gate_design`:

```
policy_weakens_baseline: ... at 'required_gates_by_risk': 'HIGH' no longer
requires gate_analyze, gate_security. A repository policy may only make
governance stricter.
--- exit 1 ---
```

**Dropping an always-required gate** — `required_gates_always` reduced to
`gate_spec` and `gate_plan`:

```
policy_weakens_baseline: ... at 'required_gates_always': it no longer requires
gate_constitution, gate_implement. A repository policy may only make governance
stricter.
--- exit 1 ---
```

Each refusal names the *first* clause it found, so a policy with several
problems is fixed one message at a time. `governance policy` is the way to
check: it either prints the effective policy or refuses with the exact clause
that weakened it.

---

## 4. Malformed is refused, never defaulted

Two failures that are not weakening but are just as dangerous, because the
tempting behaviour is to shrug and use the built-in.

Invalid JSON:

```
policy_malformed: .sdle/policies/governance-policy.json cannot be used as a
governance policy: it is not valid JSON (Expecting property name enclosed in
double quotes: line 1 column 3 (char 2)). SDLE refuses rather than falling back
to the built-in policy — a governance floor must never be lowered by a typo.
--- exit 1 ---
```

An unknown top-level key:

```
policy_malformed: .sdle/policies/governance-policy.json cannot be used as a
governance policy: unknown top-level key(s) unknown_key; an override may carry
only policyVersion, blocking_checks, optional_checks, risk_signals,
risk_thresholds, hard_floors, required_gates_always, required_gates_by_risk,
required_gates_by_type. SDLE refuses rather than falling back to the built-in
policy — a governance floor must never be lowered by a typo.
--- exit 1 ---
```

*A governance floor must never be lowered by a typo.* An unreadable policy is a
different fact from an absent one: absence has a defined answer, corruption
does not. A repository whose override stops parsing after a bad merge is
governed by nothing it consented to, and would silently drop to the weakest
admissible policy at exactly the moment nobody is watching. So it fails closed.
Note also that a misspelled key is a refusal rather than a shrug — a policy
carrying `hardfloors` would otherwise be a policy with no floors at all.

---

## 5. What an override actually changes

The shipped example lowers the `HIGH` threshold to 4, adds a
`patient_or_clinical_data` signal weighing 5 with a `CRITICAL` floor, and
requires the security gate from `MEDIUM` upward. Watch the same governance
input land differently.

Two signals, scoring 4 — `MEDIUM` under the built-in policy, whose `HIGH`
threshold is 5:

```
$ sdle.sh governance assess --input governance-input.json
{
  "ok": true,
  "command": "governance assess",
  "reason": null,
  "data": {
    "workitem": "duty-roster",
    ...
    "risk": {
      "signals": [
        "external_api_surface",
        "persistent_data_store"
      ],
      "score": 4,
      "floorsApplied": [],
      "deterministicLevel": "HIGH",
      "proposedLevel": "MEDIUM",
      "uncertainty": "LOW",
      "finalLevel": "HIGH",
      "loweringAttempted": true
    },
    "downgrade": null,
    "requirements_digest": "64aba324066fc8c92531ee80890d4290508106f43b5dc3ce4946949a8ada5cdd",
    "policy": {
      "source": ".sdle/policies/governance-policy.json",
      "sha256": "e706b6415159ba7c50aa8bbdcd7632b88dc79b216775f2a8a49812d1195f4158"
    }
  }
}
--- exit 0 ---
```

`HIGH` on a score of 4, because this repository decided 4 was enough. `HIGH`
makes every gate in the flow required:

```
    "final_risk": "HIGH",
    ...
    "required_gates": [ ... all eight ... ],
    "omittable_gates": [],
    "required_not_in_flow": [],
```

---

## 6. Risk signals, floors, and the one thing Claude cannot do

Risk is computed from three inputs and never from an opinion: the signals the
assessment names, the weights the policy gives them, and the thresholds those
weights are compared against. The example's added floor is where all three meet.
One signal, `patient_or_clinical_data`, proposed `LOW`:

```
    "risk": {
      "signals": [
        "patient_or_clinical_data"
      ],
      "score": 5,
      "floorsApplied": [
        {
          "rule": {
            "signal": "patient_or_clinical_data",
            "level": "CRITICAL"
          },
          "raisedTo": "CRITICAL"
        }
      ],
      "deterministicLevel": "CRITICAL",
      "proposedLevel": "LOW",
      "uncertainty": "LOW",
      "finalLevel": "CRITICAL",
      "loweringAttempted": true
    },
```

**Claude proposed `LOW` and got `CRITICAL`.** This is engine-enforced, not
prompt-enforced: `finalLevel` is the maximum of the deterministic level and the
proposal, so a proposal above the computed level raises it and a proposal below
it does nothing but set `loweringAttempted: true`. There is no branch in the
engine that returns a level below `deterministicLevel`, and the floor recorded
in `floorsApplied` names the rule that fired and what it raised the level to. A
model cannot argue its way under a floor, and it cannot argue its way under one
a repository invented either.

### A signal the policy does not know is a refusal

Remove the override, and the same input becomes unusable:

```
$ sdle.sh governance assess --input governance-input.json
{
  "ok": false,
  "command": "governance",
  "reason": "unknown_risk_signal",
  "data": {
    "signals": [
      "patient_or_clinical_data"
    ],
    ...
  },
  "message": "governance-input.json names risk signal(s) patient_or_clinical_data that the governance policy does not define. SDLE refuses rather than ignoring a signal it cannot weigh — a silently dropped signal is a silently lowered risk."
}
--- exit 1 ---
```

*A silently dropped signal is a silently lowered risk.* The alternative — score
what it recognises and ignore the rest — would turn a typo in a signal name
into a quiet risk reduction, which is the same failure as a malformed policy
arriving through a different door.

---

## 7. Verbose

Verbosity is a state field, and toggling it is an audited write like any other:

```
$ sdle.sh state get --field verbose
{
  "ok": true,
  "command": "state get",
  "reason": null,
  "data": {
    "field": "verbose",
    "value": false
  }
}
--- exit 0 ---

$ sdle.sh state set --field verbose --value true
{
  "ok": true,
  "command": "state set",
  "reason": null,
  "data": {
    "field": "verbose",
    "value": true,
    "previous": false
  }
}
--- exit 0 ---
```

In conversation this is `verbose on` / `verbose off`, or `--verbose` on `start
workflow`. What it changes is entirely presentational: with it off, the
orchestrator suppresses module reads, script invocations and their JSON, SHA
computation, byte-count checks, state and audit write narration, feature-ID
resolution and migration steps. It is also the single exception to SpecKit
opacity — the `speckit-*` skill names and `/speckit.*` commands are never shown
to a user except in verbose mode.

Nothing about governance changes. Verbose does not add or remove a check; it
decides how much of the machinery you watch while the same checks run.

The command surface is deliberately narrow:

```
$ sdle.sh state set --field current_phase --value implement
--- stderr ---
usage: sdle state set [-h]
                      --field {clarification_phase,speckit_skill_prefix,verbose}
                      [--value VALUE]
sdle state set: error: argument --field: invalid choice: 'current_phase' (choose from 'clarification_phase', 'speckit_skill_prefix', 'verbose')
--- exit 2 ---
```

Three fields are settable and no others. Everything else in `state.json` is
derived by the engine from a transition, a verification or an approval — argparse
refuses the rest before any code runs, which is why the exit code is 2 (usage)
rather than 1 (refused). This is invariant 6, "single writer", enforced at the
CLI surface rather than trusted to callers.

---

## 8. Omitting a gate

At `LOW` risk with an `enhancement` type, three of `GREENFIELD`'s eight gates
are discretionary:

```
$ sdle.sh governance gates
    "final_risk": "LOW",
    ...
    "required_gates": [
      "gate_constitution",
      "gate_implement",
      "gate_plan",
      "gate_security",
      "gate_spec"
    ],
    "omittable_gates": [
      "gate_analyze",
      "gate_design",
      "gate_tasks"
    ],
    "required_not_in_flow": [],
```

`gate show` reports the same fact per gate, as `required: false` with an empty
`requirement_reasons`. So omit it — and meet the first surprise:

```
$ sdle.sh gate omit --gate gate_analyze
{
  "ok": false,
  "command": "gate",
  "reason": "review_stale",
  "data": {
    "gate": "gate_analyze",
    "path": "workitems/duty-roster/specs/001-duty-roster/tasks.md",
    "reviewed_sha": "cb4d3e01944f24b59afe03a253d60b4e4f51d8fa1c1a7e01f492b0737e3f0f9b",
    "reviewed_shas": [
      "cb4d3e01944f24b59afe03a253d60b4e4f51d8fa1c1a7e01f492b0737e3f0f9b"
    ],
    "current_sha": "ea5488830c852d25878f46772afb167b90a28f01b0f18b36fcdf5da59cce3a34"
  },
  "message": "workitems/duty-roster/specs/001-duty-roster/tasks.md has changed since it was reviewed, so gate_analyze cannot be approved: a review applies to the exact content version it was performed against. Re-review the current content."
}
--- exit 1 ---
```

**An omittable gate is not an unreviewed gate.** Omission removes the
requirement for a *human approval*; it does not remove the requirement that the
artifact has been reviewed at the bytes currently on disk. `analyze` had just
refined `tasks.md`, so the review recorded at Gate 4 no longer applied to it.

Record a review of the current content, and the omission goes through:

```
$ sdle.sh gate omit --gate gate_analyze
{
  "ok": true,
  "command": "gate omit",
  "reason": null,
  "data": {
    "gate": "gate_analyze",
    "sha": "ea5488830c852d25878f46772afb167b90a28f01b0f18b36fcdf5da59cce3a34",
    "decision": "omitted_by_policy",
    "final_risk": "LOW",
    "reasons": [],
    "policy": {
      "source": "builtin",
      "sha256": null
    },
    "governance_sha256": "d245a331d62204d0788c97f8aa6e51fe6cc6da400c03d38264d0d94a9864d69c",
    "governance_downgrade": null,
    "next_phase": "design_generation",
    "status": "pending",
    "progress": "13/18"
  }
}
--- exit 0 ---
```

Look at what an omission has to carry. The `decision` is
`omitted_by_policy` — a distinct value from `approved`, so nothing downstream
can confuse the two. The artifact `sha` is recorded exactly as an approval
would record it. And `governance_sha256` binds the omission to the specific
governance record that permitted it, so "this gate was omitted" is always
answerable with "under this assessment, which said this".

Two things you cannot do with omission. You cannot omit a required gate — that
refuses `gate_required`, as [hotfix.md §4](hotfix.md#4-the-gate-that-cannot-be-removed)
shows. And you cannot omit the flow's last gate before `complete` at any risk
level, because `terminal_gate` is derived from position rather than policy.

The reverse is always allowed: approving an omittable gate is strictly
stricter than the policy demands, and needs no special ceremony. What is never
available is passing one silently.

---

## 9. When a step fails: retry, then skip

Artifact verification is where generation failures surface. A file that does
not exist, or does not clear the 100-byte floor:

```
$ sdle.sh artifact record --phase checklist_draft --path workitems/duty-roster/specs/001-duty-roster/checklist.md
{
  "ok": false,
  "command": "artifact",
  "reason": "artifact_too_small",
  "data": {
    "path": "workitems/duty-roster/specs/001-duty-roster/checklist.md",
    "bytes": 12,
    "attempts": 1,
    "max": 3,
    "retry_offered": true
  },
  "message": "Verification failed: workitems/duty-roster/specs/001-duty-roster/checklist.md was not created or is too small (<100 bytes). Retry attempt 1/3."
}
--- exit 1 ---

$ sdle.sh header
--- stderr ---
<!-- SDLE_STATE phase=checklist_draft status=failed progress=8/18 -->
📋 SDLE Status: Phase 8/18 — Generate Checklist [FAILED — ACTION REQUIRED]
--- exit 0 ---
```

The phase did not advance. That is invariant 5 — **on any failure, freeze** —
and the status becomes `failed` with a bounded retry count, three attempts.

`skip` is the escape, and it is only available *from* a failed step:

```
$ sdle.sh skip
{
  "ok": true,
  "command": "skip",
  "reason": null,
  "data": {
    "pending": true,
    "phase": "checklist_draft",
    "label": "Generate Checklist",
    "index": 8
  }
}
--- exit 0 ---

$ sdle.sh skip --confirm
{
  "ok": true,
  "command": "skip",
  "reason": null,
  "data": {
    "pending": false,
    "from": "checklist_draft",
    "to": "tasks_draft",
    "status": "pending",
    "progress": "9/18",
    "next_label": "Generate Tasks"
  }
}
--- exit 0 ---
```

Two steps, deliberately. The bare `skip` records a pending confirmation and
changes nothing; `--confirm` performs it. Asked before a failure, it refuses
`not_failed` — *`skip` is only valid after a failed step* — so skipping is a
response to a real problem rather than a way to move faster.

A skipped phase is remembered. It leaves a `phase_history` entry whose outcome
is `skipped` rather than `completed`, and an audit entry with the same event, so
a gate approved over an unverified artifact is answerable later. What the skip
does **not** do is relax the gate downstream: the artifact still has to exist,
still has to be reviewed at its current bytes, and the gate still has to be
approved. The conversational form is
[`dry-runs/03-technical-failure-retry-skip.md`](../dry-runs/03-technical-failure-retry-skip.md).

---

## 10. Going backwards: `restart`

`restart` rolls the workflow back to an earlier phase, addressed by its
**position number** in the bound flow rather than by name. Forward movement is
not one of its uses, and neither is landing on a gate:

```
$ sdle.sh restart --to 18
{
  "ok": false,
  "command": "restart",
  "reason": "gate_phase",
  "data": {
    "target": "gate_security",
    "suggest": 17
  },
  "message": "Phase 18 is a gate phase — restarting a gate is not meaningful. Did you mean phase 17?"
}
--- exit 1 ---
```

A gate is a decision about an artifact, not a step that produces one; restarting
*to* a gate would mean re-deciding without re-generating. The refusal suggests
the execution phase that owns the artifact instead.

Rolling back to phase 6 shows its cost before you pay it:

```
$ sdle.sh restart --to 6
{
  "ok": true,
  "command": "restart",
  "reason": null,
  "data": {
    "pending": true,
    "target": "plan_draft",
    "index": 6,
    "label": "Generate Plan",
    "cleared_gates": [
      "gate_plan",
      "gate_tasks",
      "gate_analyze",
      "gate_design",
      "gate_implement",
      "gate_security"
    ]
  }
}
--- exit 0 ---

$ sdle.sh restart --to 6 --confirm
{
  "ok": true,
  "command": "restart",
  "reason": null,
  "data": {
    "pending": false,
    "target": "plan_draft",
    "index": 6,
    "label": "Generate Plan",
    "cleared_gates": [
      "gate_plan",
      "gate_tasks",
      "gate_analyze",
      "gate_design",
      "gate_implement",
      "gate_security"
    ],
    "trimmed": 8
  }
}
--- exit 0 ---
```

Six approvals cleared and eight phase-history entries trimmed. Every gate at or
after the target is cleared — including the omission of `gate_analyze`, which
was a decision made against artifacts that no longer exist in the state they
were made against. You will walk them again.

The `cleared_gates` list appears in the *pending* response, before anything has
happened, which is the whole reason for the two-step shape: the confirmation
prompt shows what will be lost. `audit.md` is untouched by all of this — the
ledger only ever grows, and the restart itself is an entry in it.

---

## 11. Drift, and re-approving what changed

An approved artifact is fingerprinted. Change it afterwards and the approval no
longer describes what is on disk. `drift check` reports that, without changing
anything:

```
$ sdle.sh drift check
{
  "ok": true,
  "command": "drift check",
  "reason": null,
  "data": {
    "drifted": [
      {
        "gate": "gate_spec",
        "gate_phase": "gate_spec",
        "label": "Gate 2: Specification Approval",
        "path": "workitems/duty-roster/specs/001-duty-roster/spec.md",
        "approved_sha": "20aa1b747a32ec2c4abbe62fcf2c0d165c76121a926221e6382cea201c2e78e4",
        "current_sha": "d9302759dcc7ba9aa272e497ade27c0578867c09d4759cf1457e6d3ea5ecf276",
        "diff": null
      }
    ],
    "queue": [],
    "pending_phase": null,
    "queued": false
  }
}
--- exit 0 ---
```

`--diff` fills in the `diff` field for tracked files. `--queue` is what turns
the observation into a halt:

```
$ sdle.sh drift check --queue
{
  "ok": true,
  "command": "drift check",
  "reason": null,
  "data": {
    "drifted": [ ... ],
    "queue": [
      "gate_spec"
    ],
    "pending_phase": "plan_draft",
    "queued": true
  }
}
--- exit 0 ---

$ sdle.sh header
--- stderr ---
<!-- SDLE_STATE phase=plan_draft status=awaiting_reapproval progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [AWAITING RE-APPROVAL (DRIFT DETECTED)]
--- exit 0 ---
```

The phase you were in is remembered as `pending_phase`, and the status says
what is owed. Recovery paths that would paper over it are closed:

```
$ sdle.sh retry
{
  "ok": false,
  "command": "retry",
  "reason": "drift_pending",
  "data": {
    "drift_queue": [
      "gate_spec"
    ],
    "pending_phase": "plan_draft"
  },
  "message": "Cannot retry while artifact drift re-approvals are pending. Use `approve` or `reject with comments: <feedback>` to handle the drifted artifact first."
}
--- exit 1 ---
```

Re-approving the drifted gate needs a fresh review first — the review recorded
against the old bytes is stale by the same rule that omission met in §8:

```
$ sdle.sh gate approve --gate gate_spec
{
  "ok": false,
  "command": "gate",
  "reason": "review_stale",
  ...
  "message": "workitems/duty-roster/specs/001-duty-roster/spec.md has changed since it was reviewed, so gate_spec cannot be approved: a review applies to the exact content version it was performed against. Re-review the current content."
}
--- exit 1 ---
```

With the review re-recorded against the current SHA:

```
$ sdle.sh gate approve --gate gate_spec --comments "Re-approved after the rota field was added."
{
  "ok": true,
  "command": "gate approve",
  "reason": null,
  "data": {
    "gate": "gate_spec",
    "sha": "d9302759dcc7ba9aa272e497ade27c0578867c09d4759cf1457e6d3ea5ecf276",
    "drift_mode": true,
    "remaining_drift": [],
    "resumed_phase": "plan_draft",
    "status": "in_progress"
  }
}
--- exit 0 ---
```

`drift_mode: true` distinguishes this from an ordinary approval, `remaining_drift`
would list any other queued gate still owed, and `resumed_phase` returns the
workflow to where it was interrupted rather than to the gate it just approved.
A drift re-approval is a repair, not a step forward.

### The deliberate exception

Not every change to an approved artifact is drift. `analyze` refines `tasks.md`
— the file `gate_tasks` already fingerprinted — and that is the intended
behaviour of the phase, not a violation:

```
$ sdle.sh drift rebaseline --gate gate_tasks
```

`rebaseline` moves the gate's baseline to the current content **without a
re-approval**, and exists only for this shape: the same file deliberately
refined between two gates that both own it. Using it to make an unwanted change
go away would be defeating the mechanism rather than using it. The full
conversational treatment is
[`dry-runs/04-artifact-drift-reapproval.md`](../dry-runs/04-artifact-drift-reapproval.md).

---

## 12. Reviews, actors, and the four product subagents

Every gate needs a `PASS` review of its artifact's current bytes before it can
be approved — `artifact existence is not evidence of artifact quality`. What
the review does *not* have to be is a human.

```
$ sdle.sh artifact review --path design/app/app-design.md --type design-review --result PASS --actor-type agent --actor-name sdle-design-review --evidence design/app/app-design.md --comments "No finding above advisory."
{
  "ok": true,
  "command": "artifact review",
  "reason": null,
  "data": {
    "path": "design/app/app-design.md",
    "sha256": "fa13dfa9ae8aedcbf79d977bd00ce26e11dbaeed7461e029b09d845a43977970",
    "result": "PASS",
    "reviewType": "design-review",
    "actor": {
      "type": "agent",
      "name": "sdle-design-review"
    },
    "evidenceId": "workitems/duty-roster/.sdle/evidence/review-sdl-20260908T102540Z-10.json",
    "reviews": 10
  }
}
--- exit 0 ---
```

Five actor types are accepted — `human`, `agent`, `tool`, `test`, `system` —
and the record keeps which one it was, alongside the review type, the exact
SHA-256, an evidence document and any comments. **An agent review satisfies
`review_missing`; it does not satisfy the gate.** `gate approve` is still a
separate command, and at a required gate it is still a human's decision. The
review is the evidence in front of that decision, and the record shows plainly
whether that evidence came from a person or a program.

`artifact reviews` reads the whole ledger back, with a freshness view keyed by
path: `current_sha`, every `reviewed_shas` value, the record count, and a
`current` boolean per artifact. That last field is the one that answers "can
this gate be approved right now".

### The four subagents

Four review agents ship with SDLE, in `.claude/agents/`. Each runs in a **fresh
context** — it sees the artifacts and the repository, not the conversation that
produced them, which is the point: a reviewer that watched the author's
reasoning is not an independent reviewer.

| Agent | Reads | Used at |
|---|---|---|
| `sdle-discovery` | an existing repository | the `discovery` phase, `BROWNFIELD_DISCOVERY` |
| `sdle-design-review` | a design against its specification and plan | `design_generation` / Gate 6 |
| `sdle-code-review` | an implementation diff against its tasks and plan | `implement` / Gate 7 |
| `sdle-security-review` | the artifacts and the diff, for security findings | `security_review` / Gate 8 |

All four are declared with `tools: Read, Grep, Glob` and a `PreToolUse` hook
fencing `Write`, `Edit`, `MultiEdit`, `NotebookEdit` and `Bash`. Every one of
their descriptions ends with the same sentence: *Read-only: it records nothing
and decides nothing.* They return structured findings; the orchestrator records
them.

That division is invariant 8. A subagent may produce a review, and a review is
evidence. **Nothing holding a gate may be delegated to a subagent**, because a
gate needs the artifact content in the conversation for a human to decide on —
and a subagent's context is not the conversation the human is in. The reasoning
is in
[ADR-007](../architecture/ADR-007-progressive-capabilities-and-product-subagents.md).

---

## 13. `reset`

The last of the two-step commands, and the most destructive:

```
$ sdle.sh reset
{
  "ok": true,
  "command": "reset",
  "reason": null,
  "data": {
    "pending": true
  }
}
--- exit 0 ---

$ sdle.sh reset --confirm
{
  "ok": true,
  "command": "reset",
  "reason": null,
  "data": {
    "pending": false,
    "deleted": [
      "state.json",
      "audit.md"
    ]
  }
}
--- exit 0 ---

$ sdle.sh header
{
  "ok": false,
  "command": "header",
  "reason": "state_unreadable",
  "data": {
    "path": ".../workitems/duty-roster/.sdle/state.json"
  },
  "message": "No workitems/duty-roster/.sdle/state.json in this project. Run `init` to start a workflow."
}
--- exit 3 ---
```

`deleted` names exactly two files. The WorkItem identity survives, and so do
`governance.json`, the reviews ledger and the whole `evidence/` directory —
`reset` clears the *workflow*, not the WorkItem's history. Note the exit code:
a missing state file is **3**, integrity, not 1. Refusing is a decision the
engine made; having nothing to read is a different kind of answer, and the
exit codes keep them apart.

---

## 14. What none of this can change

The tour ends where the invariants start. After every knob above, these remain
true, and nothing in `.sdle/` reaches them:

- **A required gate needs an explicit human approval.** `advance` refuses
  `gate_not_approved`; `gate omit` refuses `gate_required`. There is no third
  option.
- **The flow's last gate before `complete` is always required.** Derived from
  position, present in no dictionary, unreachable by an override.
- **Claude cannot lower a deterministic risk level.** `finalLevel` is a maximum;
  the attempt is recorded as `loweringAttempted`.
- **A repository policy may only make governance stricter.** Six weakening
  shapes, six refusals, and a malformed policy fails closed.
- **Every flow contains the ten mandatory phases.** Enforced by the flow loader
  at load time, not only by the linter.
- **`state.json` and `audit.md` have one writer.** Three settable fields at the
  CLI; everything else is derived from a transition, a verification or an
  approval.
- **The audit chain only grows.** A refusal leaves it byte-identical; a broken
  chain is exit 3.

Where a knob and an invariant meet, the invariant wins, and the engine says so
with a named reason rather than a warning. That is the whole design: it
refuses, and a refusal is final.

---

## Where to go next

- **The short version of this flow**: [greenfield.md](greenfield.md).
- **Every refusal as a conversation**: [`dry-runs/`](../dry-runs/README.md) —
  02 rejection and remediation, 03 retry and skip, 04 drift, 05 the untrusted
  content scan, 06 secrets and the dirty tree, 07 audit integrity and the
  session lock, 08 restart, reset and state jumps, 09 bootstrap failures.
- **The gate policy in full**:
  [`risk-and-gates/`](../risk-and-gates/README.md) and
  [ADR-006](../architecture/ADR-006-risk-adaptive-gate-policy.md).
- **The configuration boundary's decision record**:
  [ADR-002](../architecture/ADR-002-repository-configuration-boundary.md).
- **A worked, engine-verified override**:
  [`risk-and-gates/example-governance-policy.json`](../risk-and-gates/example-governance-policy.json).
- **Something refused**: [`troubleshooting/`](../troubleshooting/README.md).
