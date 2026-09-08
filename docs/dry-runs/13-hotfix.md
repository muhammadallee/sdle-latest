# Dry Run 13 — `HOTFIX` (Shorter, Never Ungoverned)

| | |
|---|---|
| **Purpose** | An urgent production fix under incident pressure: the shortest flow SDLE has, and what it still refuses to give up. **10 phases, 3 gates.** |
| **Guardrails exercised** | The mandatory governance floor, gates the risk policy *wants* and cannot have, `impact_analysis` still enforced, `gate_security` required by a derived positional rule no override can reach. |
| **Starting state** | A production incident. `requirements/checkout-500.md` present. A repository with an established baseline. Working tree clean. |

---

## Transcript

**User:**

```
start workflow
```

**SDLE:**

```
📋 SDLE Status: Phase 1/10 — Requirements Check [IN PROGRESS]

I found requirements/:
  • requirements/checkout-500.md (0.9 KB)

Content scan passed.

Bound to HOTFIX: 10 phases, 3 gates. This is the shortest flow that exists,
and it is the shortest flow that *can* exist — it is exactly the mandatory
governance floor plus the impact analysis. There is no admissible flow below
it: the flow loader refuses a flow missing a mandatory phase rather than
traversing it.

Shall I proceed?
```

---

**User:** `yes, this is live, be quick`

**SDLE:**

```
<!-- SDLE_STATE phase=impact_analysis status=in_progress progress=2/10 -->
📋 SDLE Status: Phase 2/10 — Impact Analysis [IN PROGRESS]

This is the phase you will most want to skip and the one most worth keeping:
it is where "what could regress" gets written down before anybody touches a
live query.

Analysis written to reviews/impact-analysis-2026-09-08-0214.md.

# Impact Analysis — Checkout 500s under concurrent cart update

## What is broken, and where
Two concurrent writes to `cart_items` deadlock; the retry wrapper re-raises.
src/checkout/cart.py:141.

## Blast radius
All checkout traffic. Currently ~4% of sessions, rising with load.

## What could regress
The retry wrapper is shared with the inventory reservation path. Changing
its re-raise behaviour changes that path too — this is the finding that
matters most and would not have been noticed at 2am without writing it down.

## What must be verified before this ships
Concurrent checkout under load, and one inventory reservation under
contention.
```

---

**User:**

```
skip the analysis, the fix is one line
```

**SDLE:**

```
Refused: impact_analysis_missing

WorkItem 'checkout-500' is at impact_analysis and no analysis has been
recorded, so the workflow cannot leave the phase.
```

> `HOTFIX` drops five gates. It does not drop this. `advance` and `skip` both
> refuse until the analysis is recorded and carries a current PASS review —
> and note what the analysis above already caught: a shared retry wrapper on
> the inventory path, which the "one line" framing had not accounted for.

---

**SDLE:** *(after the analysis is recorded and reviewed)*

```
<!-- SDLE_STATE phase=spec_draft status=in_progress progress=3/10 -->
📋 SDLE Status: Phase 3/10 — Generate Specification [IN PROGRESS]
```

---

## The gates the policy wanted, and could not have

**User:** `sdle.sh governance gates`

**SDLE:**

```
final_risk: HIGH

dispositions                       (gates this flow HAS)
  gate_spec        required   reasons: always
  gate_implement   required   reasons: always
  gate_security    required   reasons: risk:HIGH, terminal_gate

required_not_in_flow               (gates the POLICY asked for and this
  gate_analyze                      flow does not contain)
  gate_constitution
  gate_design
  gate_plan
  gate_tasks
```

> **Read the second list.** `dispositions` covers only the gates the bound
> flow actually has — a gate that is absent has no state to be *in*, so it is
> given no disposition rather than a reassuring one. What the policy wanted
> and could not get goes in `required_not_in_flow` instead, where you can see
> it. That list is non-empty here, and the engine reports it precisely because
> **an unreported inert rule is how a policy comes to claim a guarantee nobody
> is enforcing.**
>
> This is the honest edge of the risk model, stated rather than hidden: **flow
> membership beats risk policy.** Choosing `HOTFIX` for HIGH-risk work is a
> real trade, and this report is where you see exactly what you traded away.
>
> What you cannot trade away is the floor. `gate_security` carries the reason
> `terminal_gate` alongside `risk:HIGH` — the flow's final gate before
> `complete` is always required by a derived positional rule that lives in no
> dictionary, so no policy override can reach it. Strip `risk:HIGH` away and
> `terminal_gate` still holds it in place.

---

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=complete status=completed progress=10/10 -->
📋 SDLE Status: Phase 10/10 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!

All 3 gates passed. Completion summary: workitems/checkout-500/.sdle/completion-summary.json
```

---

## What `HOTFIX` still guarantees

Ten phases is not "governance off". Every one of these still holds:

- An **impact analysis**, recorded and reviewed, before anything is specified.
- A **specification**, approved by a human who saw it in the conversation.
- An **implementation gate** with the manifest, its secrets scan and its test
  evidence — an implementation whose tests never ran cannot be approved.
- A **security review**, gated, and required by a rule an override cannot lower.
- The full **audit chain**, hash-linked, with every refusal leaving it
  byte-identical.

What it gives up is the constitution, the plan gate, the checklist, the tasks
gate, the analysis gate and the design gate — six review points, traded
deliberately for speed, and named in the disposition report rather than
quietly dropped.

---

## State & audit notes

- `state.flow` set to `HOTFIX` at `init`; the flow loader validated it against `MANDATORY_FLOW_PHASES` at load time, not at traversal time.
- `state.json` traversed: `requirements_check → impact_analysis → spec_draft → gate_spec → plan_draft → tasks_draft → implement → gate_implement → security_review → gate_security → complete`.
- `plan_draft` and `tasks_draft` run **without** their gates: the artifacts are still generated, fingerprinted and recorded; only the human approval points are absent.
- `state.approvals` has three populated entries. The other five gate keys are absent; `gate show` reports `in_flow: false` and no gate number for each, and `governance gates` lists all five under `required_not_in_flow` because at HIGH risk the policy asked for them.
- The `impact_analysis_missing` refusal left `audit.md` byte-identical.
- `audit verify` reports `matches: true` at completion.
