# Dry Run 04 — Artifact Drift Detection & Re-Approval

| | |
|---|---|
| **Purpose** | A previously-approved artifact is modified out-of-band; the next phase execution detects the drift and forces re-approval before proceeding. Shows both the re-approve and the reject outcome. |
| **Guardrails exercised** | Drift check (Step 0, runs before every phase execution), `drift_queue` / `pending_phase`, re-approval prompt, baseline SHA re-fingerprinting, drift-reject → restart guidance, drift guard blocking `retry`. |
| **Starting state** | Workflow at `plan_draft` (6/18), `status: pending`. Gates 1–2 approved with baseline SHAs recorded. The user has just hand-edited `.specify/specs/001-todo-api/spec.md` in their editor (after Gate 2 approved it). |

---

## Transcript

**User:**

```
continue
```

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=awaiting_reapproval progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [AWAITING RE-APPROVAL (DRIFT DETECTED)]

⚠️ Artifact drift detected — 1 previously-approved artifact(s) changed since approval:

  • Gate 2: Specification Approval (gate_spec)
    Path:          .specify/specs/001-todo-api/spec.md
    Approved SHA:  88d204ca…19be
    Current SHA:   f30a57e1…0c42
    Changes since approval:
      @@ -48,6 +48,9 @@ ## User Stories
      +- As a user, I can delete all completed todos in one request
      +  Acceptance criteria:
      +    1. DELETE /todos?completed=true returns 204

These artifact(s) must be re-approved before plan_draft can proceed.

---
✋ RE-APPROVAL REQUIRED — Gate 2/8: Specification Approval
(Re-approval 1/1: artifact was modified after original approval)

# Feature Specification: Todo List REST API

## User Stories
[... current on-disk content, displayed in full — abridged ...]

Artifact path: .specify/specs/001-todo-api/spec.md
Fingerprint: F30A57E1…0C42

Please review the content above, then respond with:
  • `approve` — Accept and advance to the next phase
  • `approve with comments: <your notes>` — Accept with recorded feedback
  • `reject with comments: <your feedback>` — Reject and trigger remediation
---
```

*(Internally: before executing `plan_draft`, the Step 0 drift check re-hashed every approved artifact. `spec.md` no longer matched its Gate 2 baseline → `drift_queue = ["gate_spec"]`, `pending_phase = "plan_draft"`, `status = "awaiting_reapproval"`. Phase execution halted.)*

---

### Path A — the edit was intentional: re-approve

**User:**

```
approve with comments: My edit added the bulk-delete endpoint; keeping it.
```

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=in_progress progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [IN PROGRESS]

✅ All drift re-approvals complete. Resuming plan_draft…

Generating plan...
```

*(Internally: `approvals.gate_spec` re-recorded as approved, `artifact_shas.gate_spec` updated to the NEW hash (`F30A57E1…`) — the edited content is now the baseline. `drift_queue` emptied, `current_phase` restored from `pending_phase`, and the drift check passes on re-entry.)*

---

### Path B — the edit was wrong: reject

*(Same drift prompt as above, but the user rejects:)*

**User:**

```
reject with comments: That edit was accidental — the spec should not include bulk delete.
```

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=rejected progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [REJECTED — REMEDIATION NEEDED]

Drift re-approval rejected for Gate 2: Specification Approval.

Your feedback: "That edit was accidental — the spec should not include bulk delete."

The drift re-approval queue has been cleared. To fix this, you need to regenerate the
artifact that was modified.
Use `restart phase <N>` where N is the phase number for the preceding execution phase
(the one that originally produced this artifact), then re-run the workflow from there.
```

*(For `gate_spec` the preceding execution phase is Phase 4 (`spec_draft`) — so the user would issue `restart phase 4`. See Dry Run 08 for the restart flow.)*

---

### Drift guard: `retry` is blocked while drift is pending

*(If, while the re-approval prompt is showing, the user tries to retry:)*

**User:** `retry`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=awaiting_reapproval progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [AWAITING RE-APPROVAL (DRIFT DETECTED)]

⛔ Cannot retry while artifact drift re-approvals are pending.
Use `approve` or `reject with comments: <feedback>` to handle the drifted artifact first.
```

---

## State & audit notes

- Drift detection compares each approved gate's `artifact_shas[gate_key]` against the file's current SHA-256; a missing file counts as drifted (`FILE_MISSING`).
- **v1.13:** when the drifted artifact is git-tracked the prompt includes the actual `git diff` (improvement item 12). Fingerprints tell you *that* something changed; re-approval requires knowing *what*. Recorded SHAs are lowercase hex from v1.13 onward.
- Multiple drifted gates queue in PHASE_SEQUENCE order (most upstream first) and are re-approved one at a time.
- Re-approval updates the baseline to the *new* hash — approval always means "I approved exactly this content."
- Rejection clears the whole queue and directs the user to `restart phase <N>`; it does not attempt an automatic merge or revert.
- Audit entries: `Artifact drift detected for gates: gate_spec…`, then either `Drift re-approval: gate_spec re-approved. New baseline SHA: …` or `Drift re-approval REJECTED for gate_spec…`.
