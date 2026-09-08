# Dry Run 02 — Gate Rejection, Remediation & Rate Limit

| | |
|---|---|
| **Purpose** | What rejecting a gate looks like: feedback capture, remediation re-run, and the remediation rate limit halting a feedback loop. |
| **Guardrails exercised** | Rejection protocol (feedback required, canonical in `state.json`), remediation counter vs `rate_limits.max_remediation_attempts` (default 3), bare-`reject` refusal. |
| **Starting state** | Workflow at `gate_spec` (5/18), `status: awaiting_approval`. Gate 1 approved. `attempt_counts` empty. |

---

## Transcript

**User:**

```
reject
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=awaiting_approval progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [AWAITING APPROVAL]

Please provide your feedback: `reject with comments: <your feedback>`
```

*(A bare `reject` records nothing and advances nothing — feedback-free rejection is not a supported path.)*

---

**User:**

```
reject with comments: The user stories are too vague — every story needs acceptance criteria.
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=rejected progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [REJECTED — REMEDIATION NEEDED]

Understood — I've recorded your feedback in state.json:

"The user stories are too vague — every story needs acceptance criteria."

Say "continue" to re-run the Generate Specification step with this feedback applied.
```

---

**User:**

```
continue
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=in_progress progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [IN PROGRESS]

Remediation attempt 1/3 for spec_draft.
Re-generating the specification with your feedback applied...

Specification regenerated and verified. Feedback archived.

---
✋ APPROVAL REQUIRED — Gate 2/8: Specification Approval

# Feature Specification: Todo List REST API

## User Stories
- As a user, I can create a todo...
  Acceptance criteria:
    1. POST /todos with a valid title returns 201 and the created todo
    2. Missing title returns 400 with the standard error envelope
[... abridged ...]

Artifact path: .specify/specs/001-todo-api/spec.md
Fingerprint: C41B9E02…D8F6

Please review the content above, then respond with:
  • `approve` — Accept and advance to the next phase
  • `approve with comments: <your notes>` — Accept with recorded feedback
  • `reject with comments: <your feedback>` — Reject and trigger remediation
---
```

*(Internally: feedback was written to `.specify/sdle-feedback.md` AND embedded inline in the SpecKit args (fallback), the remediation counter for `spec_draft` incremented to 1, and after verification the feedback file was archived as `.specify/sdle-feedback-archive-<timestamp>.md`.)*

---

*(The user rejects twice more with further feedback; remediation attempts 2/3 and 3/3 run the same way. Then:)*

**User:**

```
reject with comments: Still not detailed enough on the filtering behavior.
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=rejected progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [REJECTED — REMEDIATION NEEDED]

Understood — I've recorded your feedback in state.json:

"Still not detailed enough on the filtering behavior."

Say "continue" to re-run the Generate Specification step with this feedback applied.
```

**User:**

```
continue
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=rejected progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [REJECTED — REMEDIATION NEEDED]

⛔ Remediation limit reached: spec_draft has been remediated 3/3 times.

To continue, choose one of:
  • Raise the limit: `sdle.sh limit set --remediations <n>`
  • Reset this phase's counter: `sdle.sh limit reset --phase spec_draft --remediations`
  • `restart phase <N>` — restart this phase from scratch
  • `skip with warning` — advance without re-running (not recommended)
```

*(SDLE halts. It will not re-invoke generation until the user explicitly raises the limit, resets the counter, restarts, or skips. The last recorded feedback remains in `state.json` and will be used if remediation resumes.)*

---

## State & audit notes

- Each rejection: `approvals.gate_spec = { decision: "rejected", comments: <text>, timestamp }`, `status: "rejected"`, audit entry `Gate 2 rejected. Comments: <text>.`
- Each `continue`: remediation counter check → increment `attempt_counts.spec_draft.remediations` → feedback mirrored to `.specify/sdle-feedback.md` → SpecKit re-invoked with feedback inline → on verification, feedback archived + audit `Remediation complete for spec_draft.`
- At the limit: no state advance, no skill invocation — halt message only.
- Remediation counters never auto-reset (unlike retry counters); only the user can reset them.
- **v1.13:** the halt no longer tells the user to hand-edit `state.json` — doing so would defeat the audit chain and violate the single-writer invariant. Both escape hatches are audited commands (improvement item 6).
