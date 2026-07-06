# Dry Run 08 — Restart, Reset, Forward-Jump Refusal & State Jump

| | |
|---|---|
| **Purpose** | The rollback and recovery commands: two-step `restart phase N`, the forward-jump guard refusing restart-as-skip, recovery from a hand-edited `current_phase`, and the full two-step `reset workflow`. |
| **Guardrails exercised** | Restart confirmation flow (`pending_confirm_action: "restart:<N>"`), forward-jump guard, Recovery Consistency Check + `accept state`, stale-confirmation guard, `confirm reset`. |
| **Starting state** | Workflow at `gate_plan` (7/18), `status: awaiting_approval`. Gates 1–2 approved. |

---

## Transcript

### Part 1 — Rollback with `restart phase 6`

**User:**

```
restart phase 6
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_plan status=awaiting_approval progress=7/18 -->
📋 SDLE Status: Phase 7/18 — Gate 3: Plan Approval [AWAITING APPROVAL]

⚠️ You are about to restart from Phase 6: Generate Plan.

This will:
  • Clear all approvals and artifact SHAs for phases 6 and later
  • Remove phase_history entries from Phase 6 onward
  • Preserve all state prior to Phase 6

Say "confirm restart phase 6" to proceed, or anything else to cancel.
```

---

**User:**

```
confirm restart phase 6
```

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=pending progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [PENDING]

✅ Restarted at Phase 6: Generate Plan. All downstream approvals cleared.
Say "continue" to execute this phase.

Note: any manual edits to artifacts from Phase 6 onward will be overwritten when
those phases re-run.
```

*(Gates 1–2 and their baseline SHAs were untouched — only phase 6 and later were cleared. `drift_queue`, `pending_phase`, and `phase_checkpoint` were also cleared.)*

---

### Part 2 — Forward-jump refusal

*(Same starting point: `gate_plan`, 7/18. The user tries to leapfrog to implementation:)*

**User:**

```
restart phase 15
```

**SDLE:**

```
<!-- SDLE_STATE phase=gate_plan status=awaiting_approval progress=7/18 -->
📋 SDLE Status: Phase 7/18 — Gate 3: Plan Approval [AWAITING APPROVAL]

⛔ Forward jumps are not allowed.

`restart phase 15` is a rollback tool — it can only go to a phase you have already passed.
Current phase: gate_plan (index 7). Requested: implement (index 15).

To advance through the workflow, approve the intervening gates.
```

*(No confirmation is offered and `pending_confirm_action` is not set — this is a refusal, not a confirmable action. Gate phases are refused too: `restart phase 7` → "Phase 7 is a gate phase — restarting a gate is not meaningful. Did you mean phase 6?")*

---

### Part 3 — Hand-edited state: the Recovery Consistency Check

*(Someone edited `.workflow/state.json` and set `current_phase` to `implement` while history only confirms up to `gate_spec`. On the next turn:)*

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=pending progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [PENDING]

⚠️ State jump detected: current_phase is 9 phases ahead of last confirmed history.
Current: implement. Expected: plan_draft.

This may indicate skipped phases or manual state editing. Unapproved gates between
plan_draft and implement will not be enforced retroactively.

Say "accept state" to acknowledge and proceed (logged to audit), or "reset to plan_draft"
to roll back.
```

---

**User:**

```
accept state
```

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=pending progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [PENDING]

State jump acknowledged (logged to audit). Proceeding from implement.
Say "continue" to execute this phase.
```

*(Audit: `User acknowledged state jump from plan_draft to implement.` The check is honest about its limits: it cannot retroactively enforce the skipped gates, but it refuses to pass them silently.)*

---

### Part 4 — Full reset (with a stale-confirmation demonstration)

**User:**

```
reset workflow
```

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=pending progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [PENDING]

⚠️ FULL WORKFLOW RESET

This will:
  • Delete .workflow/state.json and .workflow/audit.md
  • Preserve all generated artifacts (.specify/, design/, reviews/, clarifications/)

This action cannot be undone.

Say "confirm reset" to proceed, or anything else to cancel.
```

**User:** `status`

*(The stale-confirmation guard cancels the pending reset — `Pending confirmation "reset" cancelled — new command received.` A `confirm reset` sent later would be refused: "No workflow reset is pending. Issue 'reset workflow' first." The user re-issues:)*

**User:** `reset workflow` → **SDLE:** *(same prompt)* → **User:**

```
confirm reset
```

**SDLE:**

```
✅ Workflow reset. All state cleared. Generated artifacts preserved.
Say 'start workflow' to begin fresh.
```

*(`state.json`, `audit.md`, and the `.workflow/lock` session lock are deleted; every generated artifact under `.specify/`, `design/`, `reviews/`, and `clarifications/` survives. No status header on this turn — state no longer exists.)*

---

## State & audit notes

- Both destructive commands are two-step and validated against `pending_confirm_action` — a `confirm restart phase 6` with no pending `restart:6`, or a `confirm reset` with no pending `reset`, is refused outright.
- Any intervening command cancels a pending confirmation (logged) — confirmations can never fire out of context.
- Restart trims `phase_history` and clears `approvals`/`artifact_shas` only from phase N onward; reset deletes state entirely but never touches artifacts.
- The consistency check tolerates a gap of ≤2 phases (normal advancement patterns); larger forward gaps demand `accept state`, and backwards gaps halt as possible corruption.
