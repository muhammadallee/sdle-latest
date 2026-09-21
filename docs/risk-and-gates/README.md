# Risk and gates — how the required gate set is derived

**Authority:** `GOVERNANCE_POLICY_BUILTIN` in `scripts/sdle.py`. Every value
below is quoted from it; where this document and the constant disagree, the
constant is right. See also
`docs/architecture/ADR-006-risk-adaptive-gate-policy.md`.

---

## 1. The principle

Gates are **not** a fixed checklist. They are derived, per WorkItem, from a
governance record — and the derivation is deterministic.

> **Claude proposes; the engine decides. Claude cannot lower a deterministic
> policy floor.**

The model supplies *observations*: which quality checks pass, which risk signals
are present, how uncertain it is. The engine supplies *severity* — which checks
are blocking, what each signal is worth, where the thresholds are, and which
gates each level requires. Severity is never read from the model's input.

---

## 2. Requirements quality — twelve checks

`governance assess` requires an answer to all twelve:

```text
problem_statement   scope        out_of_scope     acceptance_criteria
ambiguity           contradictions  constraints   nfrs
security_data_implications         compatibility
dependencies        blocking_unknowns
```

All twelve are **blocking**: a FAIL on any of them stops progression. Only
`nfrs` may be answered `NOT_APPLICABLE`. A repository override may not rename or
drop a check — that would be editing the contract rather than tightening it.

---

## 3. Risk signals and levels

Each signal carries a weight. The total is compared against thresholds:

| Threshold | Score |
|---|---|
| `LOW` | 0 |
| `MEDIUM` | 2 |
| `HIGH` | 5 |
| `CRITICAL` | 9 |

Signals range from `third_party_dependency` (1) through
`schema_or_data_migration`, `authentication_or_authorization`,
`public_network_exposure` and `backward_incompatible_change` (3) up to
`credential_or_key_exposure` and `catastrophic_blast_radius` (5).

### Hard floors

A score is not the last word. Twelve **hard floors** raise the final level
regardless of the arithmetic — for example any of `payment_or_financial`,
`cryptography_or_secrets`, `personal_or_sensitive_data`,
`authentication_or_authorization`, `regulatory_or_compliance` or
`production_security_boundary` forces at least `HIGH`; `credential_or_key_exposure`
and `catastrophic_blast_radius` force `CRITICAL`. Declared uncertainty is itself
a floor: `HIGH` uncertainty forces `HIGH`, `CRITICAL` uncertainty forces
`CRITICAL`.

**A floor can only be raised, never lowered.** A repository override that tried
to weaken one is refused.

---

## 4. From level to required gates

```text
always:    gate_constitution, gate_spec, gate_plan, gate_implement
LOW:       (nothing further)
MEDIUM:    + gate_tasks, gate_design
HIGH:      + gate_tasks, gate_analyze, gate_design, gate_security
CRITICAL:  + gate_tasks, gate_analyze, gate_design, gate_security
by type:   defect adds gate_tasks
```

Flow membership is applied on top: a gate the bound flow does not contain is
`not_in_flow`.

**And the policy the WorkItem started under is applied on top of that.** The set
is derived twice — once from the policy on disk, once from the policy pinned in
the governance record when the WorkItem was first assessed — against the
WorkItem's current classification and level. A gate is omittable only if it is
omittable under **both**. A gate required only by the pinned policy shows
`pinned:` reasons (`pinned:always`, `pinned:risk:HIGH`) in `gate show`.

This closes one channel and one only: relaxing or deleting the repository policy
part-way through a run cannot make a gate omittable that was required when the
run began. Tightening still applies immediately, because the live policy is
still read. See `docs/architecture/ADR-011-pinned-governance-policy.md`.

---

## 5. Omission, and the evidence it must carry

A gate that is `omittable` may be omitted with `gate omit`. The omission is not
a shortcut — it is a **record**, and it must be explainable later, from what was
written down and nothing else. Every omission carries:

- the policy source and the policy SHA-256 it was derived from;
- the SHA-256 of the **policy the WorkItem started under** (ADR-011), `null` for
  a record written before the pin existed;
- the **governance record SHA-256** the risk level came from;
- the final level itself;
- an audit event.

At the terminal gate the recorded fingerprint is re-checked, and `complete`
refuses when an omission is no longer justified.

---

## 6. Re-assessment is not a gate-clearing device

A `governance assess` may legitimately be re-run — a WorkItem's actual scope can
change, and auth genuinely being removed from scope should lower the level.

What must never happen is re-running the assessment with fewer signals *in order
to make a refused gate omittable*.

SDLE's answer to this is **evidence, not refusal**:

- a re-assessment that lowers a previously recorded final level emits a distinct
  `governance_downgraded` audit event, carrying both levels and both signal
  sets;
- that downgrade is carried into the evidence of every gate omitted afterwards,
  so the omission and the level it rests on are always read together.

It is never refused, because refusing would invent a floor the contract does not
state and would block a legitimate re-scope. It is never invisible.

This is deliberately *not* what ADR-011 pins. The pin is the policy document, and
the requirement set is re-derived against the current level, so a genuine
downgrade still moves the answer and is still governed by evidence rather than
refusal. Editing the **policy** is the channel the pin closes; re-assessing the
**risk** is the channel this section governs.

The prompt layer states the same rule to the orchestrator, in
`.claude/skills/sdle/modules/gate-protocol.md`.

---

## 7. Repository overrides

A repository may tighten policy through `sdle.sh config`. An override may carry
only the keys listed in `GOVERNANCE_POLICY_OVERRIDABLE`, and it may **add and
never remove**: extra blocking checks, heavier signal weights, lower thresholds,
more hard floors, more required gates. Anything that would weaken the shipped
policy is refused.

Monotonicity is enforced against the built-in floor, which bounds how weak a
policy can be but says nothing about *changing* one mid-run: removing an override
is a relaxation the floor permits. That is why a WorkItem's decisions are bound to
the policy it started under as well as the one on disk (ADR-011).
