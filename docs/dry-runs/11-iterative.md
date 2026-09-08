# Dry Run 11 — `ITERATIVE` (Ordinary Change Against an Established Baseline)

| | |
|---|---|
| **Purpose** | The flow almost every WorkItem after the first one takes: no discovery, no constitution, straight to specification. **16 phases, 7 gates.** |
| **Guardrails exercised** | `baseline_required` refusal, convergence onto `ITERATIVE` by refusal rather than convention, flow-relative gate numbering (`gate_spec` is **Gate 1 of 7**, not Gate 2 of 8), constitution inherited rather than regenerated. |
| **Starting state** | A repository with `.sdle/baseline.json` already established by a completed `GREENFIELD` or `BROWNFIELD_DISCOVERY` WorkItem. `requirements/export-csv.md` present. Clean git working tree. |

---

## Transcript

**User:**

```
start workflow
```

**SDLE:**

```
📋 SDLE Status: Phase 1/16 — Requirements Check [IN PROGRESS]

I found requirements/:
  • requirements/export-csv.md (1.8 KB)

Content scan passed.

This repository has an established baseline (.sdle/baseline.json, written by
WorkItem 'reporting-export' at its final gate). Discovery has already happened
here and does not happen again, so this WorkItem is bound to ITERATIVE:
16 phases, 7 gates.

The constitution is inherited from the baseline, not regenerated — which is
why there is no Gate 1 for it here and why this flow has seven gates rather
than eight.

Shall I proceed?
```

*(Internally: `init` read `.sdle/baseline.json`. Had the governance record proposed `BROWNFIELD_DISCOVERY` instead, `init` would have refused `baseline_present`: discovery happening once is enforced by refusal, not by anybody remembering.)*

---

**User:** `yes`

**SDLE:**

```
<!-- SDLE_STATE phase=spec_draft status=in_progress progress=2/16 -->
📋 SDLE Status: Phase 2/16 — Generate Specification [IN PROGRESS]

Generating specification...

Specification generated at workitems/export-csv/specs/002-export-csv/spec.md
(3.4 KB, verified).

---
✋ APPROVAL REQUIRED — Gate 1/7: Specification Approval

# CSV Export — Specification

## Problem
Reporting data can be read in the UI but not extracted...

[... abridged ...]

---
Reply `approve` or `reject with comments: <your feedback>`.
```

> **Read the gate number.** This is `gate_spec`, which in `GREENFIELD` is
> Gate 2 of 8. Here it is **Gate 1 of 7**. The number is derived from the bound
> flow every time it is displayed; it is not a property of the gate. A document
> or a habit that says "the spec gate is Gate 2" is wrong for three flows out
> of five.

---

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=in_progress progress=4/16 -->
📋 SDLE Status: Phase 4/16 — Generate Plan [IN PROGRESS]

✅ Gate 1/7 approved — specification fingerprinted at baseline
   a3f1…9c2e.

Generating implementation plan...
```

---

> **Phases 4–16 proceed exactly as in `01-happy-path.md`**, with these gate
> numbers:
>
> | Gate | Phase | Progress | In GREENFIELD this is |
> |---:|---|---|---|
> | 1/7 | `gate_spec` | 3/16 | Gate 2 of 8 |
> | 2/7 | `gate_plan` | 5/16 | Gate 3 of 8 |
> | 3/7 | `gate_tasks` | 8/16 | Gate 4 of 8 |
> | 4/7 | `gate_analyze` | 10/16 | Gate 5 of 8 |
> | 5/7 | `gate_design` | 12/16 | Gate 6 of 8 |
> | 6/7 | `gate_implement` | 14/16 | Gate 7 of 8 |
> | 7/7 | `gate_security` | 16/16 | Gate 8 of 8 |

---

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=complete status=completed progress=16/16 -->
📋 SDLE Status: Phase 16/16 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!

All 7 gates passed. Completion summary: workitems/export-csv/.sdle/completion-summary.json

No baseline was written. The repository baseline is established once, by a
GREENFIELD or BROWNFIELD_DISCOVERY completion; an ITERATIVE WorkItem works
against it and leaves it alone.
```

---

## The refusal this flow exists to produce

Run the same WorkItem in a repository with **no** baseline and `init` refuses:

```
Refused: baseline_required

ITERATIVE works from an established repository baseline and this repository
has none. Run a BROWNFIELD_DISCOVERY WorkItem first, or a GREENFIELD one if
the repository is genuinely empty.
```

This is the other half of "discovery happens once". `baseline_present` stops a
second discovery; `baseline_required` stops an `ITERATIVE` WorkItem from
skipping the first one. Between them the repository can be in exactly one of
two states, and the engine refuses rather than guessing which.

---

## State & audit notes

- `state.flow` set to `ITERATIVE` at `init`; `state.approvals` has seven populated entries and **no** `gate_constitution` entry. `gate show --gate gate_constitution` reports `in_flow: false` with no gate number — never "quietly satisfied".
- `state.json` traversed: `requirements_check → spec_draft → gate_spec → plan_draft → gate_plan → checklist_draft → tasks_draft → gate_tasks → analyze → gate_analyze → design_generation → gate_design → implement → gate_implement → security_review → gate_security → complete`.
- `.sdle/baseline.json` unchanged — same SHA-256 before and after the run.
- `artifact_shas` holds 7 baseline fingerprints.
- `audit.md` chain intact throughout; `audit verify` reports `matches: true`.
