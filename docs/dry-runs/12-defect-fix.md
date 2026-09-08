# Dry Run 12 — `DEFECT_FIX` (Blast Radius Before Specification)

| | |
|---|---|
| **Purpose** | A defect in an existing system: `impact_analysis` opens the flow, and the phase cannot be left without a reviewed analysis. **14 phases, 6 gates.** |
| **Guardrails exercised** | The gateless `impact_analysis` phase, the `impact_analysis_missing` refusal on both movers, recorded-but-unreviewed and reviewed-then-edited both refused, `gate_tasks` required by change *type* rather than risk, no `checklist_draft` and no design gate. |
| **Starting state** | A repository with an established baseline. `requirements/login-reset-defect.md` describes a reported bug. Clean git working tree. |

---

## Transcript

**User:**

```
start workflow
```

**SDLE:**

```
📋 SDLE Status: Phase 1/14 — Requirements Check [IN PROGRESS]

I found requirements/:
  • requirements/login-reset-defect.md (1.2 KB)

Content scan passed.

This WorkItem is classified as a defect, so it is bound to DEFECT_FIX:
14 phases, 6 gates.

Two differences worth stating up front. It opens with an impact analysis
rather than a specification — a defect fix starts from an existing system, and
the expensive failures in defect work are the ones nobody looked for. And it
drops the checklist and the design phase, but *keeps* the tasks gate: a defect
always adds gate_tasks regardless of assessed risk, because "we changed the
thing next to the broken thing" is how a one-line fix becomes an outage.

Shall I proceed?
```

---

**User:** `yes`

**SDLE:**

```
<!-- SDLE_STATE phase=impact_analysis status=in_progress progress=2/14 -->
📋 SDLE Status: Phase 2/14 — Impact Analysis [IN PROGRESS]

Reading the requirement and the repository as it stands: the code paths the
defect touches, the tests covering them, the recent history.

Analysis written to reviews/impact-analysis-2026-09-08-1030.md.

# Impact Analysis — Login fails after password reset

## What is broken, and where
`reset_password()` clears the session token but does not re-issue one, so the
next authenticated request 401s. src/auth/reset.py:88.

## What the change reaches
- `src/auth/reset.py` — the fix itself
- `src/auth/session.py` — token re-issue path, called but not modified
- `tests/test_reset.py` — currently asserts the *broken* behaviour and will
  need updating, which is itself a finding

## Blast radius
Every authenticated route, for any user who resets in the next session.

## What could regress
Any caller depending on the current post-reset token being absent. The
mobile client's silent-refresh path is the one candidate.

## What must be verified before this ships
Reset → immediate authenticated request, on web and mobile.
```

---

**User:**

```
looks right, move on to the spec
```

**SDLE:**

```
Refused: impact_analysis_missing

WorkItem 'login-reset-defect' is at impact_analysis and no analysis has been
recorded, so the workflow cannot leave the phase. A defect is specified from
its blast radius, not before it: write the analysis, then
`artifact record --phase impact_analysis --path <file>` and
`artifact review --path <file> --type impact-analysis --result PASS
--actor-type agent --actor-name sdle-orchestrator`. Record the review last —
editing the file afterwards makes it stale.
```

> **Writing the file is not recording it.** The analysis existed on disk and
> was displayed above; the engine still refuses, because what it can verify is
> a fingerprint and a review, not that somebody read a document. `advance` and
> `skip` both hit this — a gateless phase is not an ungoverned one.

---

**SDLE:**

```
Recording the analysis and registering the review.

  artifact record --phase impact_analysis
    → reviews/impact-analysis-2026-09-08-1030.md
      sha256 1a4db50c…5ecc, 872 bytes

  artifact review --type impact-analysis --result PASS
    → bound to sha256 1a4db50c…5ecc
```

*(Two things this does not do. Recording alone would not lift the refusal — a fingerprint is not a judgement. And the review is bound to that exact SHA, so editing the file afterwards makes it stale and the refusal returns. That is why the phase contract says to record the review **last**, and it needs no new mechanism: it is TP-011 doing what it already did.)*

---

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=spec_draft status=in_progress progress=3/14 -->
📋 SDLE Status: Phase 3/14 — Generate Specification [IN PROGRESS]

Generating specification, scoped to the blast radius recorded above...
```

---

**SDLE:** *(at the specification gate)*

```
---
✋ APPROVAL REQUIRED — Gate 1/6: Specification Approval

Before the specification, the impact analysis for this WorkItem, in full:

[... reviews/impact-analysis-2026-09-08-1030.md re-displayed ...]

# Login Reset Defect — Specification

[... abridged ...]
```

> `impact_analysis` has no gate of its own, and this is the first gate
> downstream of it. The engine guarantees an analysis exists and was reviewed;
> whether the fix is *scoped correctly* is the judgement this gate is for.

---

> **The rest of the flow**, with its gate numbers:
>
> | Gate | Phase | Progress | In GREENFIELD this is |
> |---:|---|---|---|
> | 1/6 | `gate_spec` | 4/14 | Gate 2 of 8 |
> | 2/6 | `gate_plan` | 6/14 | Gate 3 of 8 |
> | 3/6 | `gate_tasks` | 8/14 | Gate 4 of 8 |
> | 4/6 | `gate_analyze` | 10/14 | Gate 5 of 8 |
> | 5/6 | `gate_implement` | 12/14 | Gate 7 of 8 |
> | 6/6 | `gate_security` | 14/14 | Gate 8 of 8 |
>
> `checklist_draft`, `design_generation` and `gate_design` are absent from the
> flow entirely. `gate show --gate gate_design` reports `in_flow: false` and no
> gate number — it is not omitted, and it is not satisfied; this WorkItem never
> had it. `governance gates` gives it no disposition either, because a gate the
> flow does not contain has no state to be in.

---

**User:** `approve`

**SDLE:**

```
<!-- SDLE_STATE phase=complete status=completed progress=14/14 -->
📋 SDLE Status: Phase 14/14 — Complete [COMPLETED]

✅ Security review approved. Workflow complete!

All 6 gates passed. Completion summary: workitems/login-reset-defect/.sdle/completion-summary.json
```

---

## State & audit notes

- `state.flow` set to `DEFECT_FIX` at `init`.
- `state.json` traversed: `requirements_check → impact_analysis → spec_draft → gate_spec → plan_draft → gate_plan → tasks_draft → gate_tasks → analyze → gate_analyze → implement → gate_implement → security_review → gate_security → complete`.
- The `impact_analysis_missing` refusal left `audit.md` **byte-identical** and `audit verify` intact — the precondition is a pure reader placed ahead of each mover's first irreversible write.
- `reviews/impact-analysis-2026-09-08-1030.md` recorded once and reviewed once; the review entry names the SHA it reviewed, permanently, even after the file changes.
- `state.approvals` has six populated entries; `gate_constitution` and `gate_design` are absent.
- No baseline written — `DEFECT_FIX` does not establish one.
