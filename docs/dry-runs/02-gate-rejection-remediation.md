# Dry Run 02 — Gate Rejection, Remediation & Rate Limit

| | |
|---|---|
| **Scenario ID** | DR-02 |
| **Flow** | `GREENFIELD` |
| **Purpose** | What rejecting a gate looks like: feedback capture, a remediation re-run, and the remediation rate limit halting a feedback loop. |
| **Defect IDs** | — |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | The DR-01 repository and WorkItem `todo-api`, driven to `gate_spec` (`5/18`, `awaiting_approval`). Gate 1 approved. `specKit.featureDirectory` is `workitems/todo-api/specs/001-todo-api`. `attempt_counts` is empty. LOW risk |
| **Guardrails exercised** | Rejection protocol (feedback required, canonical in `state.json`), remediation counter against `rate_limits.max_remediation_attempts` (default 3), the bare-`reject` refusal, audited escape hatches |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> are illustrative. The engine behaviour it depends on is asserted by the tests
> under *Executable coverage*. Their results — **PASS**, **FAIL**, **BLOCKED** or
> **NOT RUN** — are recorded in [verification-matrix.md](verification-matrix.md).

---

## Setup

Follow DR-01's setup, then run DR-01's conversation as far as the Gate 2 prompt.

---

## Transcript

**User:** `reject`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=awaiting_approval progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [AWAITING APPROVAL]

Please provide your feedback: `reject with comments: <your feedback>`
```

*(A bare `reject` records nothing and advances nothing. A rejection without
feedback is not a supported path.)*

---

**User:** `reject with comments: The user stories are too vague — every story needs acceptance criteria.`

**SDLE:**

```
<!-- SDLE_STATE phase=gate_spec status=rejected progress=5/18 -->
📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [REJECTED — REMEDIATION NEEDED]

Understood — I've recorded your feedback in state.json:

"The user stories are too vague — every story needs acceptance criteria."

Say "continue" to re-run the Generate Specification step with this feedback applied.
```

*(Engine: `sdle.sh gate reject --gate gate_spec --reason "The user stories are too vague…"`.)*

---

**User:** `continue`

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

Artifact path: workitems/todo-api/specs/001-todo-api/spec.md
Fingerprint: c41b9e02…d8f6
---
```

*(Engine: `sdle.sh remediate begin --gate gate_spec` checked the counter,
incremented `attempt_counts.spec_draft.remediations` to 1 and wrote the
feedback to `.specify/sdle-feedback.md`. The feedback also goes inline in the
generation arguments. After verification, `sdle.sh remediate finish --gate gate_spec`
archived the feedback file. The regenerated spec has new content, so it needs
a fresh PASS review before Gate 2 can approve it.)*

---

*(The user rejects twice more with further feedback. Remediation attempts 2/3
and 3/3 run the same way. Then:)*

**User:** `reject with comments: Still not detailed enough on the filtering behavior.`

**User:** `continue`

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

*(Engine: `sdle.sh remediate begin --gate gate_spec` refused
`rate_limit_exceeded` **without invoking anything**. The last recorded feedback
stays in `state.json` and is used if remediation resumes.)*

---

## Artifacts, state and audit

- Each rejection records `approvals.gate_spec = {decision: "rejected", comments, timestamp}`,
  `status: "rejected"`, and an audit entry with the comments.
- Each remediation increments `attempt_counts.spec_draft.remediations`,
  mirrors the feedback to `.specify/sdle-feedback.md` and, on success,
  archives it as `.specify/sdle-feedback-archive-<stamp>.md`.
- At the limit there is no state advance and no skill invocation.
  Remediation counters never auto-reset.
- Both escape hatches are audited commands (`limit set`, `limit reset`). The
  halt never tells the user to hand-edit `state.json`.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| Bare `reject` | Asks for feedback | Nothing recorded |
| `remediate begin` with no recorded rejection | Refused `nothing_to_remediate` | Unchanged |
| A fourth `continue` at the limit | Refused `rate_limit_exceeded` | Unchanged; nothing invoked |

## Cleanup

`rm -rf dr01`, the same disposable project as DR-01.

## Executable coverage

| Claim | Test |
|---|---|
| A rejection records feedback and freezes | `tests/test_integration_02_to_05.py::test_02_rejection_records_feedback_and_freezes` |
| Remediation writes feedback from canonical state | `tests/test_integration_02_to_05.py::test_02_remediation_writes_feedback_from_canonical_state` |
| Finishing archives and removes the feedback file | `tests/test_integration_02_to_05.py::test_02_remediation_finish_archives_and_removes_feedback` |
| The limit halts without invoking anything | `tests/test_integration_02_to_05.py::test_02_remediation_limit_halts_without_invoking_anything` |
| Counters never auto-reset | `tests/test_integration_02_to_05.py::test_02_remediation_counters_never_auto_reset` |
| Nothing to remediate is refused | `tests/test_integration_02_to_05.py::test_02_remediate_refuses_when_nothing_was_rejected` |
| Raising the limit is audited | `tests/test_integration_02_to_05.py::test_02_raising_the_limit_is_audited_not_hand_edited` |
