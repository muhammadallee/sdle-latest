# Dry Run 08 — Restart, Reset, Forward-Jump Refusal & State Jump

| | |
|---|---|
| **Scenario ID** | DR-08 |
| **Flow** | `GREENFIELD` |
| **Purpose** | The rollback and recovery commands: two-step `restart phase N`, the forward-jump guard refusing restart-as-skip, recovery from a hand-edited `current_phase`, and the two-step `reset workflow`. |
| **Defect IDs** | — |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | The DR-01 repository and WorkItem `todo-api`, at `gate_plan` (`7/18`, `awaiting_approval`). Gates 1–2 approved |
| **Guardrails exercised** | The restart confirmation flow, the forward-jump guard, the gate-phase guard, `doctor` + `accept state`, the stale-confirmation guard, and `confirm reset`. Phase numbers are positions in the **bound flow** |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. The engine
> behaviour it depends on is asserted by the tests under *Executable coverage*.
> Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded
> in [verification-matrix.md](verification-matrix.md).

---

## Setup

Follow DR-01 to the Gate 3 prompt.

---

## Transcript

### Part 1 — Rollback with `restart phase 6`

**User:** `restart phase 6`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_plan status=awaiting_approval progress=7/18 -->
📋 SDLE Status: Phase 7/18 — Gate 3: Plan Approval [AWAITING APPROVAL]

⚠️ You are about to restart from Phase 6: Generate Plan.
This clears approvals and artifact SHAs for phase 6 and later and keeps everything before it.

Say "confirm restart phase 6" to proceed, or anything else to cancel.
```

*(Engine: `sdle.sh confirm set --action restart:6`. `6` is a position in the
bound flow — the same number the `Phase N/M` header showed.)*

**User:** `confirm restart phase 6`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=pending progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [PENDING]

✅ Restarted at Phase 6: Generate Plan. All downstream approvals cleared.
```

*(Engine: `sdle.sh restart --to 6 --confirm`. Gates 1–2 and their baselines
were untouched. `drift_queue`, `pending_phase` and `phase_checkpoint` were
cleared.)*

---

### Part 2 — Forward-jump refusal

**User:** `restart phase 15`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_plan status=awaiting_approval progress=7/18 -->
📋 SDLE Status: Phase 7/18 — Gate 3: Plan Approval [AWAITING APPROVAL]

⛔ Forward jumps are not allowed. `restart phase 15` is a rollback tool — it can only
go to a phase you have already passed.
```

*(Engine refusal: `forward_jump`. No confirmation is offered and nothing is
pending. `restart phase 7` is refused as well (`gate_phase`), because
restarting a gate is not meaningful.)*

---

### Part 3 — Hand-edited state

*(Someone edited `workitems/todo-api/.sdle/state.json` and set `current_phase`
to `implement`, while history confirms only up to `gate_spec`.)*

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=pending progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [PENDING]

⚠️ State jump detected: current_phase is well ahead of last confirmed history.
Say "accept state" to acknowledge and proceed (logged), or restart to roll back.
```

**User:** `accept state`

*(Engine: `sdle.sh doctor` reported the jump, and `sdle.sh accept-state`
logged the acknowledgement. The check cannot retroactively enforce the skipped
gates, but it refuses to pass them silently. Every later gate still refuses an
unresolved or unreviewed artifact.)*

---

### Part 4 — Full reset

**User:** `reset workflow`

**SDLE:**

```
<!-- SDLE_STATE phase=implement status=pending progress=15/18 -->
📋 SDLE Status: Phase 15/18 — Implement [PENDING]

⚠️ FULL WORKFLOW RESET
This deletes workitems/todo-api/.sdle/state.json, audit.md and lock, and preserves every
generated artifact. Say "confirm reset" to proceed, or anything else to cancel.
```

**User:** `status`, then `reset workflow` again, then `confirm reset`

**SDLE:**

```
✅ Workflow reset. All state cleared. Generated artifacts preserved.
Say 'start workflow' to begin fresh.
```

*(Engine: `sdle.sh reset --confirm`. The intervening `status` cancelled the
first pending reset, so a later `confirm reset` alone would have been refused
`no_pending_confirmation`. The WorkItem identity in `workitems/index.md`
survives the reset; only its runtime is cleared.)*

---

## Artifacts, state and audit

- Both destructive commands are two-step and validated against
  `pending_confirm_action`.
- Restart trims `phase_history` and clears `approvals` and `artifact_shas`
  only from phase N onward. Reset deletes the runtime and never touches
  generated artifacts.
- `doctor` tolerates a gap of at most two phases. Larger forward gaps demand
  `accept state`, and backward gaps halt as possible corruption.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| `restart phase 15` from phase 7 | Refused `forward_jump` | Unchanged; nothing pending |
| `restart phase 7` (a gate) | Refused `gate_phase` | Unchanged |
| `confirm reset` with nothing pending | Refused `no_pending_confirmation` | Unchanged |

## Cleanup

`rm -rf dr01`.

## Executable coverage

| Claim | Test |
|---|---|
| Restart is two-step and rolls back | `tests/test_integration_06_to_09.py::test_08_restart_is_two_step_and_rolls_back` |
| Only downstream approvals are cleared | `tests/test_integration_06_to_09.py::test_08_restart_clears_only_downstream_approvals` |
| Forward jumps refused without a confirmation | `tests/test_integration_06_to_09.py::test_08_forward_jump_refused_without_offering_confirmation` |
| Restarting a gate is refused | `tests/test_integration_06_to_09.py::test_08_restarting_a_gate_phase_is_refused` |
| `doctor` detects a hand-edited jump | `tests/test_integration_06_to_09.py::test_08_doctor_detects_a_hand_edited_forward_jump` |
| `accept state` acknowledges and logs | `tests/test_integration_06_to_09.py::test_08_accept_state_acknowledges_and_logs` |
| Reset is two-step and preserves artifacts | `tests/test_integration_06_to_09.py::test_08_reset_is_two_step_and_preserves_artifacts` |
| A pending reset is cancelled by another command | `tests/test_integration_06_to_09.py::test_08_a_pending_reset_is_cancelled_by_any_other_command` |
