# ADR-003 — Deterministic governance inputs, and a governed artifact review that a gate enforces

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-26 |
| **Scope** | Migration phase T06 (transition contract §12, TP-011). No engine version change. |

## Context

Two things were true of SDLE up to v1.15, and both were gaps rather than
choices.

**Work entered the lifecycle on no stated grounds.** `init` asked for a
WorkItem name and nothing else. Whether the requirements were coherent, what
kind of change this was, and how risky it was were questions the model answered
implicitly, in prose, differently each time — if at all. Contract §12 states the
opposite: governance metadata must exist *before* current planning and
implementation begin, requirements quality must be assessed against a
structured check set, risk must be scored deterministically, and **blocking
findings stop progression**. Those are MUSTs, not advice.

**Artifact existence was treated as artifact quality.** `artifact record`
proves a file exists, clears a size floor and takes a fingerprint. A gate then
asked a human to approve it. Nothing anywhere recorded that the *content* had
been judged, by whom, against which version, or with what result. Contract
TP-011 says exactly that: artifact existence alone is not evidence of artifact
quality, a review applies to the exact content version it was performed
against, and a stale review must not be usable.

The tension the phase had to resolve is that §12 also says *preserve current
gates; do not make them conditional yet*. That clause constrains **routing**.
It does not license leaving two stated MUSTs unenforced. T06 therefore adds two
deterministic refusals on the lifecycle path and changes **nothing** about
which phases run, which gates exist, or in what order.

## Decision

### 1. Governance is a precondition of movement, enforced in the core

A WorkItem carries a governance record at `workitems/<id>/.sdle/governance.json`,
written by `governance assess` from a structured proposal. `apply_advance` —
the single function `advance`, `gate approve` and `skip` all funnel through —
refuses `governance_missing`, `governance_blocked` and `governance_stale`.

It is enforced in `sdle.py`, not by an instruction in a prompt file, because a
policy floor a model is *asked* to respect is a policy floor a model can reason
its way past. The core refuses; it does not warn. The rule is written in exactly
one function, so there is exactly one place to audit.

`cmd_gate_approve` calls that function a second time, earlier, and deliberately
without `state` so the early call records nothing. That command appends its
`gate_approved` audit entry *before* it moves the phase, and an append to the
append-only ledger cannot be undone by a later raise; refusing ahead of the
first irreversible write is what keeps a refusal byte-identical in `audit.md`
and the hash chain intact. Invariant 5 says freeze on any failure, and a false
`Gate Decision: APPROVED` entry left behind by a refused approval would be a
failure of the product's central evidence artifact, not a cosmetic one.

Governance is deliberately **not** an `init` precondition. §12 asks for it
before *planning*, and a WorkItem must be able to bootstrap; `init` stays byte-
identical.

### 2. Severity, weights, thresholds and floors come from policy — never from the input

The assessing model supplies observations: a per-check result, a
classification, the risk signals it believes apply, an uncertainty band and a
proposed level. It supplies **no** severities. Which checks block is read from
policy. Signal weights, score thresholds and hard floors are read from policy.
An input that tries to declare its own severity is refused, and an unknown
signal id is refused rather than ignored.

Risk is hybrid but one-directional: `final = max(deterministic, proposed)`. A
proposal *above* the computed level is honoured — a model that senses danger the
signal vocabulary cannot express should be able to raise the bar. A proposal
*below* it is recorded as an attempt, written into the audit ledger, and has no
effect. **Claude cannot lower a deterministic floor.** That property is proved
over the cross-product of signal subsets and proposed levels, not asserted.

### 3. The policy override is monotone, and the reader is fail-closed

`GOVERNANCE_POLICY_BUILTIN` in `sdle.py` is the single source of truth. A
repository may override it at `.sdle/policies/governance-policy.json`, and the
override may only make governance **stricter**: unblocking a check, lowering a
weight or a floor, raising a threshold, or dropping a signal is refused
`policy_weakens_baseline`, naming the offending key.

That monotonicity is what makes "no policy file → built-in" safe rather than
fail-open: the built-in is by construction the weakest admissible policy, so a
missing override can never produce a weaker outcome than a present one.

The reader is fail-closed for the opposite direction. `read_governance_policy`
refuses `policy_malformed` on every unreadable, unparseable or wrong-shaped
file, and returns the built-in **only** when the file is genuinely absent. It
does **not** inherit `read_repo_config`'s swallow-and-default behaviour, and
`read_repo_config` was not modified — a security-relevant floor that silently
defaulted would be the wrong failure direction.

### 4. `.sdle/policies/` is not fenced, and that is the answer, not a deferral

ADR-002 recorded an obligation: *the first phase that puts executable policy
under `policies/` is the phase that must fence it.* T06 is that phase, and the
answer is **no hook fence**, for three reasons.

1. A policy override is human-authored by design, exactly like `config.json`. A
   write fence would block the intended workflow.
2. Monotonicity means a hand edit **cannot weaken governance**. The only
   reachable outcomes are "stricter" or "refused". The property a fence would
   protect is already guaranteed at the choke point, which is where SDLE's
   guarantees are supposed to live.
3. `hooks.py`'s directory matcher matches a name **anywhere** in the path, so a
   bare `.sdle` entry would also match `workitems/<id>/.sdle/` and shadow the
   existing reason text for that path — the hazard ADR-002 and T05 both
   recorded. `.claude/hooks/` is byte-identical after T06, and that byte-
   identity is part of the phase's proof.

`SDLE_OWNED_PREFIXES` is likewise unchanged. Its precondition still holds:
nothing in T06 writes `.sdle/` during a run.

### 5. Review is a different fact from approval, so it gets its own registry

`reviews.json` is an append-only list of review records under the WorkItem
runtime. `artifact_shas` remains the sole approval baseline, with its writer set
unchanged. Review and approval are not two names for one fact:

- an **approval** is a human's decision to let the workflow proceed;
- a **review** is a judgement about content, attributed to an actor, tied to a
  fingerprint.

Collapsing them would make the ledger unable to answer "who judged this, and
which version" separately from "who approved it". They stay disjoint: the
approval baseline holds no review data, the review ledger holds no gate keys,
and the review result is **not** carried in the audit `decision` field.

### 6. "Currently reviewed" is derived, never stored

The predicate is: *there exists a record for this path whose fingerprint equals
the artifact's fingerprint now, and whose result is `PASS`.* It is recomputed on
every check.

A stored boolean would be a second source of truth for the same fact, and worse,
it could not express *which* version was reviewed — which is precisely what
TP-011 is about. Planting a "fresh" flag by hand changes nothing.

### 7. The review requirement holds on the drift path too

`review_precondition` is called from both `cmd_gate_approve` and the drift
re-approval path. Drift is exactly the case TP-011's staleness rule is drawn
for: re-approving drifted content against a review of the pre-drift content is
the violation, stated. Guarding only the ordinary path would have left the
interesting one open.

### 8. The would-be required gate set is computed, recorded, and never acted on

`required_gate_set` is a pure function over the policy's gate map, and its
output is stored as `wouldBeRequiredGates` and reported by `governance gates`.
Nothing consumes it. All eight gates run unconditionally, for every
classification and every risk level.

This is deliberate. Making gates conditional is a separate decision with its own
consequences, and it belongs to the phase that owns flow selection. Recording the
set now means that phase inherits a measured comparison rather than a guess. Two
source-level containment tests and a differential run — repositories differing
only in classification and final risk producing identical traversals, approvals
and ordered audit events — keep the "never acted on" half honest.

### 9. Nothing is delegated

§12's audit example names an actor `sdle-architect`. T06 **records an actor
string supplied by the caller**. It creates, registers and invokes no subagent;
`.claude/agents/` is byte-identical. Reviews at this version are performed in
the parent session, and nothing holding a gate is delegated — a gate needs the
artifact content in the conversation where the human decides.

The later phase that introduces specialist subagents therefore inherits a
decision rather than an assumption: an actor name is evidence about who judged
something, not an instruction to summon anyone.

### 10. No schema version bump

Governance and reviews live in new WorkItem runtime *files*, not in
`state.json`. The decisive argument is ownership, not convenience: a governance
record that must exist **before** `state.json` cannot be a field of it. The
precedent is `execution.json`, added the same way and for the same reason.

Consequences, all mechanically checked: the state template is byte-identical,
the version string is unchanged, the migration chain gains no row, and no
constant table moves.

## Alternatives rejected

**Warn instead of refuse.** A warning the orchestrator can narrate past is not
an enforcement of a MUST. §12's "blocking findings stop progression" and
TP-011's stale-review prohibition are both stated as requirements; a warning
would satisfy neither, and the failure would be silent.

**Put the rules in `SKILL.md` and trust the model.** This is the failure mode
the deterministic core exists to remove (ADR-001). A prompt-layer floor is a
suggestion. The prompt layer describes the refusals; it does not implement
them.

**Let the model set the risk level.** Rejected outright. A model that can lower
its own risk level has no floor at all. It may raise; it may never lower; the
attempt is recorded either way.

**Score risk from prose.** Rejected: not reproducible, not auditable, and not
comparable between two WorkItems. The signal vocabulary is closed, and an
unknown id is refused rather than dropped — dropping it would silently lower the
score.

**Store a `reviewed: true` flag.** Rejected: a second source of truth that
cannot express which content version it refers to (invariant 7).

**Overload `artifact_shas` with review fingerprints.** Rejected: one mechanism
would then answer two different questions, and the approval baseline's writer
set — a guarantee several tests pin — would have to grow.

**Write a default `governance-policy.json` during `config init`.** Rejected: it
would restate every policy default in a second place, at a security-relevant
location, reproducing exactly the drift surface T05 recorded. A content search
over the whole prose corpus enforces that no policy default value appears
outside `sdle.py`.

**Make gates conditional now, since the risk level is available.** Rejected as
out of scope, twice over: §12 says preserve current gates, and it is a different
decision from the one this ADR makes.

**Enforce at `cmd_advance`.** Rejected as fail-open: `gate approve` and `skip`
would have been unguarded. Enforcement sits at `apply_advance`, which all three
funnel through.

## Consequences

- **A WorkItem started before this version refuses at its next `advance`**,
  with a message naming `governance assess`. This is deliberate — it is §12's
  "before planning begins" applied to work already in flight — and the remedy is
  one command. No existing runtime is rewritten or damaged.
- **The transitional legacy `.workflow/` binding is exempt from both new
  preconditions**, because it has no WorkItem to hold either record. It is a
  declared, bounded residual: it fires only when zero WorkItems are registered,
  it mirrors an identical existing carve-out, and it disappears with the rung
  itself when the legacy binding is removed. Tests pin it in both directions so
  it cannot silently widen.
- **The audit ledger gains two entry kinds** — the governance facts, and one
  entry per artifact review carrying the review type, result, actor and evidence
  id. Both render *before* the chain tail, so the hash chain's input ordering is
  unchanged and a block with no review is byte-identical to one written before
  this phase.
- **Every gate now needs a review before it can be approved.** That is a real
  cost, paid once per artifact version, and it is the point: it converts "a file
  exists" into "someone judged this content, and said so on the record".
- **Traversal is unchanged.** Eighteen phases, eight unconditional gates, the
  same order, the same approvals. Governance and risk are recorded evidence at
  this version, not routing.
