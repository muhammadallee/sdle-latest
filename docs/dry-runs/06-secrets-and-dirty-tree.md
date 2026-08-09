# Dry Run 06 — Dirty-Tree Guard & Secrets Scan at Gate 7

| | |
|---|---|
| **Purpose** | The two implementation-phase guards: uncommitted user changes halt Phase 15 until confirmed, and a hardcoded credential in the generated code is flagged in the manifest the reviewer sees at Gate 7. |
| **Guardrails exercised** | **Dirty-tree guard** + `confirm implement` (v1.12, item 8); **secrets scan** with mandatory manifest section (v1.12, item 2). |
| **Starting state** | Workflow at `implement` (15/18), `status: pending`. Gates 1–6 approved. The user has an uncommitted local edit to `notes/ideas.md` they forgot about. |

---

## Transcript

**User:**

```
continue
```

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=pending progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [PENDING]

⚠️ Uncommitted changes detected in the working tree:

   M notes/ideas.md

These may be mixed into or overwritten by the implementation, and will appear in the
implementation manifest as if the implementation produced them.

Commit or stash them first, or say "confirm implement" to proceed anyway (logged).
```

*(The guard filters out SDLE's own artifact paths (`.workflow/`, `.specify/`, `design/`, `reviews/`, `clarifications/`, `guidance/`, `requirements/`) — mid-workflow those are legitimately dirty. Only the user's `notes/ideas.md` remains, so the phase halts with `pending_confirm_action: "implement_dirty_tree"`.)*

---

**User:**

```
confirm implement
```

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=in_progress progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [IN PROGRESS]

Proceeding despite uncommitted changes (logged).

Implementing against tasks.md, informed by the approved design documents...

Implementation complete. Building the implementation manifest...

⚠️ Secrets scan flagged 1 potential secret in the changed files (see manifest below).

---
✋ APPROVAL REQUIRED — Gate 7/8: Implementation Approval

# Implementation Manifest
Generated: 2026-07-06T14:20:44Z
Phase: implement (Phase 15/18)

## Changed/Added Files
src/app.py
src/config.py
src/models/todo.py
src/routes/todos.py
tests/test_todos.py
notes/ideas.md        ← pre-existing uncommitted change (see dirty-tree acknowledgement)

## Potential Secrets Detected
src/config.py:12 — secret API key — sk-p ****(masked)

## Summary
Implemented the Todo REST API per tasks.md: CRUD endpoints, filtering,
completion shortcut endpoint, validation layer, and pytest suite.

Artifact path: .workflow/implementation-manifest.md
Fingerprint: 7A2E90CF…B14D

Please review the content above, then respond with:
  • `approve` — Accept and advance to the next phase
  • `approve with comments: <your notes>` — Accept with recorded feedback
  • `reject with comments: <your feedback>` — Reject and trigger remediation
---
```

*(The `## Potential Secrets Detected` section is mandatory in every manifest — either findings or the exact line `None detected.` Because the manifest is the Gate 7 artifact and is displayed in full, the finding is necessarily in front of the reviewer at the moment of decision.)*

---

**User:**

```
reject with comments: Move the API key out of src/config.py into an environment variable before I approve this.
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_implement status=rejected progress=16/18 -->
📋 SDLE Status: Phase 16/18 — Gate 7: Implementation Approval [REJECTED — REMEDIATION NEEDED]

Understood — I've recorded your feedback in state.json:

"Move the API key out of src/config.py into an environment variable before I approve this."

Say "continue" to re-run the Implement step with this feedback applied.
```

---

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_implement status=in_progress progress=16/18 -->
📋 SDLE Status: Phase 16/18 — Gate 7: Implementation Approval [IN PROGRESS]

Remediation attempt 1/3 for implement.
Re-running the implementation with your feedback applied...

Implementation updated. Rebuilding the implementation manifest...
Secrets scan: no high-risk patterns found in the changed files.

---
✋ APPROVAL REQUIRED — Gate 7/8: Implementation Approval

# Implementation Manifest
[... regenerated manifest ...]

## Potential Secrets Detected
None detected.

## Test Evidence
Runner: pytest
Result: passed (exit 0)

[... abridged ...]
---
```

**User:** `approve`

*(Gate 7 approved; the workflow proceeds to Phase 17 — Security Review.)*

---

## State & audit notes

- Dirty-tree guard: runs before `phase_checkpoint` is set; skipped entirely when git is absent or when arriving via `confirm implement` (one-shot bypass). Audit: `Dirty-tree guard triggered before implement. 1 uncommitted entries.`
- Secrets findings are masked to their first 4 characters in both the manifest and the audit entry (`⚠️ Secrets scan flagged 1 potential secret(s) in the implementation diff.`) — the transcript never reproduces the full secret.
- **v1.13:** the manifest is built by `sdle.py manifest build`, and Gate 7 *refuses* a manifest missing its `## Potential Secrets Detected` or `## Test Evidence` section. A hook can be skipped; that refusal sits at the choke point, so an implementation whose tests never ran cannot reach a human decision.
- Approving Gate 7 with findings present is the explicit acknowledgement; rejecting (as here) routes through the standard remediation flow, and the regenerated manifest re-runs the scan.
- The scan is regex-based (AWS keys, private key blocks, GitHub/API tokens, credential assignments, bearer tokens) — a heuristic tripwire before human review, not a replacement for `trufflehog`/`semgrep`, which the Phase 17 review recommends running.
