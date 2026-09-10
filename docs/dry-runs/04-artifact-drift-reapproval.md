# Dry Run 04 — Artifact Drift Detection & Re-Approval

| | |
|---|---|
| **Scenario ID** | DR-04 |
| **Flow** | `GREENFIELD` |
| **Purpose** | An approved artifact is edited out of band. The next phase execution detects the drift and forces re-approval before continuing. Shows re-approve, reject, and the refusal to re-baseline onto a deleted artifact. |
| **Defect IDs** | D01 |
| **Runtime** | SDLE v1.17 on `fix/defect-stabilization`; SpecKit v1.0.6. Generation is simulated |
| **Starting conditions** | The DR-01 repository and WorkItem `todo-api`, at `plan_draft` (`6/18`). Gates 1–2 approved with baselines. The user has just hand-edited `workitems/todo-api/specs/001-todo-api/spec.md`, which is git-tracked |
| **Guardrails exercised** | Drift check before every phase execution, `drift_queue` / `pending_phase`, git diff in the prompt, re-approval re-baselining, a TP-011 review of the drifted content, drift-reject → restart guidance, `retry` blocked while drift is pending, and the D01 refusal of an unfingerprintable re-approval |

> **How to read this.** The conversation under *Transcript* is **SIMULATED**.
> It was written from the skill files and the engine's real messages. Hashes
> are illustrative. The engine behaviour it depends on is asserted by the tests
> under *Executable coverage*. Their results — **PASS**, **FAIL**, **BLOCKED** or
> **NOT RUN** — are recorded in [verification-matrix.md](verification-matrix.md).

---

## Setup

Follow DR-01 as far as Gate 2's approval, commit, then edit the approved
`spec.md` by hand.

---

## Transcript

**User:** `continue`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=awaiting_reapproval progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [AWAITING RE-APPROVAL (DRIFT DETECTED)]

⚠️ Artifact drift detected — 1 previously-approved artifact changed since approval:

  • Gate 2: Specification Approval (gate_spec)
    Path:          workitems/todo-api/specs/001-todo-api/spec.md
    Approved SHA:  88d204ca…19be
    Current SHA:   f30a57e1…0c42
    Changes since approval:
      +- As a user, I can delete all completed todos in one request

---
✋ RE-APPROVAL REQUIRED — Gate 2/8: Specification Approval
[... current on-disk content, displayed in full — abridged ...]

Artifact path: workitems/todo-api/specs/001-todo-api/spec.md
Fingerprint: f30a57e1…0c42
---
```

*(Engine: `sdle.sh drift check --diff --queue --pending-phase plan_draft` set
`drift_queue = ["gate_spec"]` and `pending_phase = "plan_draft"`, and halted
the phase.)*

---

### Path A — the edit was intentional: re-approve

**User:** `approve with comments: My edit added the bulk-delete endpoint; keeping it.`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=in_progress progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [IN PROGRESS]

✅ All drift re-approvals complete. Resuming plan_draft…
```

*(Engine: first a review of the **drifted** content with
`sdle.sh artifact review --path workitems/todo-api/specs/001-todo-api/spec.md …`,
because approving it against the pre-drift review is exactly what TP-011
forbids. Then `sdle.sh gate approve --gate gate_spec` in drift mode, which
re-fingerprinted the file, set the new SHA as the baseline and resumed
`pending_phase`.)*

---

### Path B — the edit was wrong: reject

**User:** `reject with comments: That edit was accidental — the spec should not include bulk delete.`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=rejected progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [REJECTED — REMEDIATION NEEDED]

Drift re-approval rejected for Gate 2: Specification Approval. The queue has been
cleared. To regenerate the artifact, use `restart phase 4` (Generate
Specification), then re-run the workflow from there.
```

---

### Path C — the drifted file was deleted (D01)

*(Instead of editing `spec.md`, suppose it was deleted. Drift reports it as
`FILE_MISSING` and queues the gate. Re-approving would re-baseline the gate onto
nothing, which the engine used to do silently, with `sha: null`.)*

**User:** `approve`

**SDLE:**

```
Refused: artifact_missing

Cannot re-approve gate_spec: workitems/todo-api/specs/001-todo-api/spec.md does not
exist. Drift re-approval re-baselines the gate onto specific content, and there is
none. Restore the artifact, or `restart` the phase that produces it.
```

*(Nothing moved: the queue, the approvals and `audit.md` are exactly as they
were.)*

---

### Drift guard: `retry` is blocked while drift is pending

**User:** `retry`

**SDLE:**

```
<!-- SDLE_STATE phase=plan_draft status=awaiting_reapproval progress=6/18 -->
📋 SDLE Status: Phase 6/18 — Generate Plan [AWAITING RE-APPROVAL (DRIFT DETECTED)]

⛔ Cannot retry while artifact drift re-approvals are pending.
```

---

## Artifacts, state and audit

- Drift compares each baselined gate's `artifact_shas[gate]` against the file's
  current lowercase SHA-256. A missing file counts as drifted (`FILE_MISSING`).
- For a git-tracked artifact the prompt includes the real `git diff`.
- Multiple drifted gates queue in flow order, most upstream first, and are
  re-approved one at a time. Approving out of queue order is refused.
- Re-approval sets the baseline to the *new* hash. Rejection clears the queue
  and points to `restart`.
- Audit entries: `drift_detected`, then either `drift_reapproved` or the
  rejection.

## Negative cases

| Attempt | Result | State afterwards |
|---|---|---|
| Re-approve a deleted artifact | Refused `artifact_missing` | Queue, approvals, ledger unchanged |
| Re-approve against the pre-drift review | Refused `review_stale` | Unchanged |
| Approve a gate out of queue order | Refused `drift_pending` | Unchanged |
| `retry` while drift is pending | Refused | Unchanged |

## Cleanup

`rm -rf dr01`.

## Executable coverage

| Claim | Test |
|---|---|
| Drift is detected against the baseline | `tests/test_integration_02_to_05.py::test_04_drift_is_detected_against_the_baseline` |
| Queueing halts and remembers the phase | `tests/test_integration_02_to_05.py::test_04_queueing_halts_the_workflow_and_remembers_what_was_interrupted` |
| A missing artifact counts as drifted | `tests/test_integration_02_to_05.py::test_04_a_missing_artifact_counts_as_drifted` |
| Re-approval re-baselines and resumes | `tests/test_integration_02_to_05.py::test_04_reapproval_rebaselines_and_resumes` |
| Rejection clears the queue | `tests/test_integration_02_to_05.py::test_04_rejection_clears_the_queue_and_does_not_resume` |
| Out-of-order approval refused | `tests/test_integration_02_to_05.py::test_04_approving_out_of_queue_order_is_refused` |
| The prompt carries a git diff | `tests/test_integration_02_to_05.py::test_04_drift_includes_a_git_diff_for_tracked_artifacts` |
| Re-approval needs a review of the drifted content | `tests/test_units_artifact_review.py::test_drift_reapproval_needs_a_review_of_the_drifted_content` |
| Re-approving a deleted artifact refuses (D01) | `tests/test_units_gate_artifacts.py::test_d01_drift_reapproval_of_a_deleted_artifact_refuses` |
