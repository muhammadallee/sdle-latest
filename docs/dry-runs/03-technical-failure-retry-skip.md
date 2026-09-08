# Dry Run 03 — Technical Failure, Retry Limit & Confirmed Skip

| | |
|---|---|
| **Purpose** | A generation step that produces no usable artifact: verification failure, the retry rate limit, and the two-step `skip with warning` → `confirm skip` escape hatch. |
| **Guardrails exercised** | Post-SpecKit Verification (≥100-byte check), retry counter vs `rate_limits.max_retry_attempts` (default 3), **confirm skip** (v1.12, item 15), stale-confirmation guard. |
| **Starting state** | Workflow at `plan_draft` (6/18), `status: in_progress`. Gates 1–2 approved. The plan generation step is failing (e.g., SpecKit produces an empty file). |

---

## Transcript

**SDLE:** *(after invoking the plan generator)*

```
<!-- SDLE_STATE phase=plan_draft status=failed progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [FAILED — ACTION REQUIRED]

⚠️ Verification failed: .specify/specs/001-todo-api/plan.md was not created or is too small (<100 bytes).
This usually means the SpecKit step did not complete successfully.
Retry attempt 1/3. Options: "retry" to run again, "skip with warning" to continue anyway.
```

*(Status was frozen at `failed`; the phase did not advance. The retry counter for `plan_draft` incremented to 1.)*

---

**User:** `retry`

*(The step fails again → retry 2/3. The user retries once more → the counter reaches the limit:)*

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=failed progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [FAILED — ACTION REQUIRED]

⛔ Retry limit reached: plan_draft has failed 3/3 times.

To continue, choose one of:
  • Raise the limit: `sdle.sh limit set --retries <n>`
  • Reset this phase's counter: `sdle.sh limit reset --phase plan_draft --retries`
  • `skip with warning` — advance without a successful artifact (not recommended)
  • `restart phase <N>` — restart this phase from scratch
```

*(Note the `retry` option is no longer offered once the limit is hit.)*

---

**User:**

```
skip with warning
```

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=failed progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [FAILED — ACTION REQUIRED]

⚠️ You are about to skip Phase 6: Generate Plan WITHOUT a verified artifact.

This will:
  • Advance the workflow with current_artifact set to null
  • Possibly cause downstream phases to fail or produce incorrect output
  • Be permanently logged in audit.md

Say "confirm skip" to proceed, or anything else to cancel.
```

*(v1.12: the skip no longer executes on the first command — `pending_confirm_action` is set to `"skip"` and SDLE halts.)*

---

**User:**

```
status
```

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=failed progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [FAILED — ACTION REQUIRED]

(Pending confirmation "skip" cancelled — new command received.)

## SDLE Workflow State
[... full state dump — abridged ...]
| Pending Confirm | none |
```

*(The stale-confirmation guard: any command other than the expected confirmation cancels the pending skip, so an old confirmation can never fire out of context. The user must issue `skip with warning` again:)*

---

**User:** `skip with warning`

**SDLE:** *(same confirmation prompt as above)*

**User:**

```
confirm skip
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_plan status=pending progress=7/18 -->
📋 SDLE Status: Phase 7/18 — Gate 3: Plan Approval [PENDING]

⚠️ Phase 6: Generate Plan skipped without artifact verification.
This may cause downstream phases to fail or produce incorrect output.
The skip is logged in audit.md.

Moving to Phase 7: Gate 3: Plan Approval. Say "continue" to proceed.
```

---

## State & audit notes

- Each verification failure: `status = "failed"`, retry counter incremented **before** comparing against the limit; no phase advance.
- `skip with warning` (first step): only sets `pending_confirm_action: "skip"` — nothing else changes.
- Any intervening command clears the pending confirmation (logged: `Pending confirmation "skip" cancelled — new command received.`).
- `confirm skip`: audit entry `⚠️ SKIPPED WITH WARNING: Phase plan_draft advanced without a verified artifact…`, `current_artifact`/`current_artifact_sha` set to null, phase advanced via NEXT_PHASE.
- A successful verification later resets `attempt_counts.<phase>.retries` to 0; remediation counts are unaffected.
- **v1.13:** the limit escape hatches are audited commands rather than hand edits to `state.json` (improvement item 6).
