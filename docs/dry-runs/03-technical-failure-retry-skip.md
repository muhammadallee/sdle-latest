# Dry Run 03 — Technical Failure, Retry Limit & Confirmed Skip

| | |
|---|---|
| **Scenario ID** | DR-03 |
| **Flow** | `GREENFIELD` |
| **Purpose** | A generation step that produces no usable artifact: verification failure, the retry rate limit, and the two-step `skip with warning` → `confirm skip` escape hatch. |
| **Defect IDs** | — |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated, and here it simulates a *failure* |
| **Starting conditions** | The DR-01 repository and WorkItem `todo-api`, at `plan_draft` (`6/18`, `in_progress`). Gates 1–2 approved. The plan generator writes an empty `workitems/todo-api/specs/001-todo-api/plan.md` |
| **Guardrails exercised** | Post-generation verification (≥100 bytes), the retry counter against `rate_limits.max_retry_attempts` (default 3), confirmed skip, and the stale-confirmation guard |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. The engine
> behaviour it depends on is asserted by the tests under *Executable coverage*.
> Their results — **PASS**, **FAIL**, **BLOCKED** or **NOT RUN** — are recorded
> in [verification-matrix.md](verification-matrix.md).

---

## Setup

Follow DR-01's setup and conversation as far as Gate 2's approval. The failing
generator is simulated by leaving `plan.md` under 100 bytes. The suite's
equivalent is `Project.write_small`.

---

## Transcript

**SDLE:** *(after invoking the plan generator)*

```
<!-- SDLE_STATE phase=plan_draft status=failed progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [FAILED — ACTION REQUIRED]

⚠️ Verification failed: workitems/todo-api/specs/001-todo-api/plan.md was not created
or is too small (<100 bytes). Retry attempt 1/3. Options: "retry" to run again,
"skip with warning" to continue anyway.
```

*(Engine: `sdle.sh artifact record --phase plan_draft --path workitems/todo-api/specs/001-todo-api/plan.md`
refused `artifact_too_small`. It froze `status` at `failed` and incremented the
retry counter. The phase did not advance.)*

---

**User:** `retry`

*(It fails again, 2/3. The user retries once more and the counter reaches the limit:)*

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

*(Refused `rate_limit_exceeded` with `retry_offered: false`, so `retry` is no
longer offered.)*

---

**User:** `skip with warning`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=failed progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [FAILED — ACTION REQUIRED]

⚠️ You are about to skip Phase 6: Generate Plan WITHOUT a verified artifact.
This will be permanently logged in audit.md.

Say "confirm skip" to proceed, or anything else to cancel.
```

*(Engine: `sdle.sh confirm set --action skip`. Nothing else changes.)*

---

**User:** `status`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=failed progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [FAILED — ACTION REQUIRED]

(Pending confirmation "skip" cancelled — new command received.)
[... state dump — abridged ...]
```

*(This is the stale-confirmation guard. Any other command cancels the pending
skip, so an old confirmation can never fire out of context. The user issues
`skip with warning` again, then:)*

**User:** `confirm skip`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_plan status=pending progress=7/18 -->
📋 SDLE Status: Phase 7/18 — Gate 3: Plan Approval [PENDING]

⚠️ Phase 6: Generate Plan skipped without artifact verification. The skip is
logged in audit.md.
```

*(Engine: `sdle.sh skip --confirm`. The skip moves past a *generation* step
and records no approval. Gate 3 still needs `plan.md` to exist, which D01
enforces (`artifact_missing`), and to carry a current PASS review of its exact
content, which TP-011 enforces (`review_missing`). A regenerated plan is the
honest way through.)*

---

## Artifacts, state and audit

- Each verification failure sets `status = "failed"` and increments the retry
  counter *before* comparing it with the limit. There is no phase advance.
- `skip with warning` only sets `pending_confirm_action: "skip"`.
- `confirm skip` writes an audit entry reading `⚠️ SKIPPED WITH WARNING…`,
  nulls `current_artifact`, and advances along the bound flow's next phase.
- A later successful verification resets `attempt_counts.<phase>.retries` to 0.
  Remediation counts are unaffected.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| `skip` when the phase has not failed | Refused | Unchanged |
| `confirm skip` after an intervening command | Refused — nothing pending | Unchanged |
| `retry` at the limit | Refused `rate_limit_exceeded` | Unchanged |

## Cleanup

`rm -rf dr01`.

## Executable coverage

| Claim | Test |
|---|---|
| Verification failure freezes and counts | `tests/test_integration_02_to_05.py::test_03_verification_failure_freezes_and_counts` |
| At the limit `retry` is no longer offered | `tests/test_integration_02_to_05.py::test_03_retry_limit_stops_offering_retry` |
| Success resets the retry counter | `tests/test_integration_02_to_05.py::test_03_successful_verification_resets_the_retry_counter` |
| Skip needs a failed status | `tests/test_integration_02_to_05.py::test_03_skip_requires_a_failed_status` |
| Skip is two-step | `tests/test_integration_02_to_05.py::test_03_skip_is_two_step` |
| Stale confirmation is cancelled | `tests/test_integration_02_to_05.py::test_03_stale_confirmation_guard_cancels_a_pending_skip` |
| The skip is permanently logged | `tests/test_integration_02_to_05.py::test_03_skip_is_permanently_logged` |
