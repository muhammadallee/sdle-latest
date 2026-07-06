# Dry Run 07 — Audit Integrity, Session Lock & Staleness Warning

| | |
|---|---|
| **Purpose** | Resuming a workflow in a brand-new conversation while three integrity signals fire: a fresh lock from another session, a hand-edited audit log, and repository commits newer than the last approval. |
| **Guardrails exercised** | **Session lock** (v1.12, item 7), **audit hash chain** + `accept audit` (v1.12, item 5), **repository staleness check** (v1.12, item 14). |
| **Starting state** | Workflow at `gate_design` (14/18), `status: awaiting_approval`, Gates 1–5 approved (latest approval 2026-07-05T16:40Z). Since then: a colleague opened the project in another Claude Code session 4 minutes ago (`.workflow/lock` is fresh with a different token), someone deleted an embarrassing rejection entry from `.workflow/audit.md`, and two commits landed on the branch. |

---

## Transcript

**User:** *(in a brand-new conversation)*

```
status
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_design status=awaiting_approval progress=14/18 -->
📋 SDLE Status: Phase 14/18 — Gate 6: Design Approval [AWAITING APPROVAL]

⚠️ Another session may be operating on this workflow (lock touched 4 minutes ago).
Concurrent sessions can corrupt state.json. Proceed only if you are sure no other
session is active.

⚠️ Audit log integrity check failed.
.workflow/audit.md has been edited, truncated, or written by another session.
Expected hash: 6E01BD4A…33F8
Current:       9B7C20E5…A1D0

Say `accept audit` to re-baseline the audit hash and continue (logged), or inspect
.workflow/audit.md before proceeding.
```

*(Order of checks on load: state read + migration → session lock (warn-only, does not halt) → audit integrity (halts: `pending_confirm_action = "accept_audit_mismatch"`). `audit.md` is deliberately left untouched before acknowledgement so the evidence can be inspected. The staleness check hasn't run yet — it comes after the halt clears.)*

---

**User:** *(inspects `.workflow/audit.md`, confirms with the colleague that they trimmed it, decides to proceed)*

```
accept audit
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_design status=awaiting_approval progress=14/18 -->
📋 SDLE Status: Phase 14/18 — Gate 6: Design Approval [AWAITING APPROVAL]

Audit hash re-baselined (logged).

ℹ️ The repository has commits newer than your latest gate approval — approved artifacts
may reflect a stale view of the codebase.

---
✋ APPROVAL REQUIRED — Gate 6/8: Design Approval

# Application Design — Todo List REST API

## Context Diagram
[... design/app/app-design.md displayed in full — abridged ...]

Artifact path: design/app/app-design.md
Fingerprint: 2F84C1D9…6E0B

Please review the content above, then respond with:
  • `approve` — Accept and advance to the next phase
  • `approve with comments: <your notes>` — Accept with recorded feedback
  • `reject with comments: <your feedback>` — Reject and trigger remediation
---
```

*(The acknowledgement itself became an audit entry — `User acknowledged audit integrity mismatch. Audit hash re-baselined.` — and `audit_sha` now matches the file again. The staleness warning is informational only: shown once per conversation, no acknowledgement required. The workflow resumes exactly where it halted: the pending Gate 6 prompt.)*

---

### Variant — the mismatch was NOT expected

*(Same failure, but the user cannot explain the edit. They do not `accept audit`; instead they inspect:)*

**User:** `show state`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_design status=awaiting_approval progress=14/18 -->
📋 SDLE Status: Phase 14/18 — Gate 6: Design Approval [AWAITING APPROVAL]

(Pending confirmation "accept_audit_mismatch" cancelled — new command received.)

## SDLE Workflow State
[... full state dump — abridged. The user can diff audit.md against backups/VCS
before deciding. On the next turn, the audit integrity check fires again and
re-raises the same halt — the mismatch does not go away until re-baselined. ...]
```

---

## State & audit notes

- **Lock**: warn-only. Written on every state save (`<ISO timestamp> <8-hex token>`); a differing token under 10 minutes old triggers the warning once per conversation. `reset workflow` deletes it.
- **Audit chain**: `audit_sha` = SHA-256 of the whole `audit.md`, updated after every append (ordering: append → hash → save state). A mismatch is tamper-*evidence*, not proof of malice — another session's legitimate write also trips it, which is exactly what you want surfaced.
- **`accept audit`** is the only path past the mismatch; it is itself logged, so the re-baseline can never happen silently.
- **Staleness check** (Step 1d-3): compares newest `approvals[*].timestamp` against `git log -1 --format=%cI`; fires once per conversation; never halts.
