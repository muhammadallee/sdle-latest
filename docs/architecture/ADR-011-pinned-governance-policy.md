# ADR-011 — The policy a WorkItem started under is pinned

**Status:** Accepted
**Date:** 2026-09
**Amends:** ADR-006, which established that the required gate set is derived at every decision point
and never stored. That rule stands, with the single exception this ADR defines.

---

## 1. The decision

The governance record pins the **policy document in force when the WorkItem's first governance record
was written**. Every later decision derives the requirement set twice — once from the policy on disk,
once from the pinned policy, both against the WorkItem's **current** classification and risk level — and
a gate is omittable only if it is omittable under **both**.

The pin is applied as an **AND**. It can promote a gate from `omittable` to `required`; it can never do
the reverse.

## 2. The defect this closes

Recorded as F-024 and reproduced end to end:

1. A repository policy that requires `gate_design` at LOW is in force when the WorkItem starts.
   `gate omit --gate gate_design` is refused `gate_required`.
2. The policy file is deleted, relaxing the repository to the built-in floor.
3. The identical command now succeeds. The gate is passed with no human approval, and the omission
   evidence records `policy_sha256: null`.

Nothing was tampered with and nothing was bypassed. The engine did exactly what it was written to do:
`gate_requirements_for_state` read the policy from disk and compared it with nothing.

A repository override may only ever *tighten* the built-in policy (`_refuse_weakening`), so the built-in
is a floor no policy can go under. That floor is what made this look safe. It is not: the whole point of
an override is that a repository chooses a standard above the floor, and a run that started under that
standard could be finished under a lower one.

## 3. Why the "never stored" rule did not already forbid this

ADR-006's rule exists against one specific failure: a **stored requirement set that authorises an
omission the live policy forbids**. That is a real hazard, and it is a strict widening of permission.

A pin used as an AND is the opposite operation. It removes permission and adds none, so no state of the
pinned document can cause a gate to be passed that the live policy requires. The invariant-7 concern —
one source of truth per fact — is also intact, because the pin is not a second copy of "what is
required now". It is a different fact: *what was required when this run began*. Two different facts,
each with one home.

The record's `requiredGates` and `omittableGates` remain evidence only, never read back for a decision.
They are a flow-and-risk composite that a later re-assessment legitimately replaces. `pinnedPolicy` is
the policy document itself, and it is the only key of the record a decision consults.

## 4. What is pinned, and what deliberately is not

**The merged policy document is pinned**, with its source and SHA-256 — not the derived gate list.

That distinction is the whole scope of this decision. Pinning the derived list would also freeze the
**risk level** the list was computed at, and would therefore refuse an omission after a genuine
re-scope. `modules/gate-protocol.md` and `docs/risk-and-gates/README.md` both state that a downgrade is
never refused, because a WorkItem's actual scope can change and blocking that would invent a floor the
contract does not state. That behaviour is unchanged here.

So, precisely:

| Channel | Before | After |
|---|---|---|
| The repository policy is relaxed mid-run | a gate required at the start becomes omittable | **refused**: the pinned policy still requires it |
| The repository policy is tightened mid-run | the tightening applies immediately | unchanged — the live policy is still read |
| The risk level is lowered by re-assessment | the omission is permitted, and audited (`governance_downgraded`, carried into the omission evidence) | unchanged, and deliberately so |

The risk-downgrade channel remains governed by evidence rather than refusal. Anyone reading this ADR as
"gates are now pinned" would be reading it wrong: **the policy** is pinned.

## 5. Where the pin lives, and why

In `governance.json`, as `pinnedPolicy`, at `governanceVersion` 3.

Not in `state.json`. A new state field means bumping `CURRENT_VERSION`, and under ADR-010 a state of any
other schema is refused `unsupported_state_version` and never migrated. Every WorkItem in flight would
have to be abandoned and restarted — a severe price for a change whose entire purpose is to protect
WorkItems already in flight.

**The pin is carried forward verbatim by every later `governance assess`.** This is the mechanism, not
bookkeeping. `assess` rewrites the record wholesale, so a pin re-derived on each assessment would be
erased by the very sequence it exists to stop: relax the policy, re-assess, omit. It is established at
the *first* governance record — not at `init`, because governance is deliberately not an `init`
precondition, so the first moment a policy can be pinned is the first assessment.

## 6. Records written before the pin

`governanceVersion` 1 and 2 records carry no pin and derive from the live policy alone, exactly as the
engine behaved before this change. This is the fail-**open** direction and it is chosen deliberately:
refusing them would freeze every WorkItem in flight when the pin shipped, and an older record is
evidence of an older schema, not evidence of a tighter policy. Such a WorkItem gains a pin the next time
it is assessed, and `revalidate_recorded_omissions` re-checks its earlier omissions at the terminal gate.

## 7. Where the rule is applied

One place: `gate_requirements_for_state`, which every consumer already goes through — `gate omit`,
`apply_advance`'s omission re-derivation, `revalidate_recorded_omissions`, and `gate_disposition`, which
backs both `gate show` and `resume`. A second application site would be a second answer to "is this gate
required", which is exactly the drift the rest of this engine is built to prevent.

A promotion tags its reasons `pinned:` (`pinned:always`, `pinned:risk:HIGH`), because
`modules/gate-protocol.md` displays `requirement_reasons` at the gate, and a user who is refused an
omission they expected to be allowed must be able to see that it is the starting policy talking. The
refusal names both SHA-256s, and so does every omission record.

## 8. Consequences

- A gate can be refused for omission on the authority of a policy file that is no longer on disk. That
  is the intent, and the reason string and both SHAs are what make it diagnosable.
- The recovery from an unwanted pin is to approve the gate, or to start a new WorkItem under the policy
  you actually want. There is no flag that clears a pin, for the same reason there is no flag that
  clears `gate_required`.
- `.sdle/policies/` remains outside the write fence. Fencing it was considered and declined: a hook is a
  tripwire that a human editor or a shell command walks straight past, so it would treat a governance
  hole as an access-control problem while leaving the hole. The choke-point refusal is the guarantee.
