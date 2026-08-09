> **SDLE module — loaded on demand.** Assumes Internal Constants (PHASE_SEQUENCE, NEXT_PHASE, PHASE_TO_GATE_KEY, GATE_PHASES, PROGRESS_MAP, ARTIFACT_OWNERSHIP, PHASE_LABEL_MAP) are already in context from SKILL.md. Do not duplicate them here.

## GATE_TO_EXECUTION_PHASE

Use this table in Step 7 (Rejection & Remediation) to determine whether re-execution after rejection invokes SpecKit or an SDLE-native module.

| gate_key | execution_phase | type |
|---|---|---|
| gate_constitution | constitution_draft | SpecKit (`speckit-constitution`) |
| gate_spec | spec_draft | SpecKit (`speckit-specify`) |
| gate_plan | plan_draft | SpecKit (`speckit-plan`) |
| gate_tasks | tasks_draft | SpecKit (`speckit-tasks`) |
| gate_analyze | analyze | SpecKit (`speckit-analyze`) |
| gate_design | design_generation | SDLE-native (Phase 13 in `modules/phase-execution.md`) |
| gate_implement | implement | SpecKit (`speckit-implement`) |
| gate_security | security_review | SDLE-native (Phase 17 via `modules/security-review.md`) |

---

## Step 6: Approval Gate Protocol

**Before displaying any gate prompt, you MUST:**

1. Read the full content of `current_artifact` from disk.
2. Determine display length:
   - If content is ≤3000 words: display the **complete content** in a fenced markdown block.
   - If content is >3000 words: display the **first ~500 words**, then `[... truncated ...]`, then the **last ~200 words**, followed by `(Total: ~<N> words — <file_path>)`.
3. **Guidance alignment check:** Look up the guidance file for the *preceding execution phase* using the Guidance File Map in `modules/phase-execution.md` (e.g. for `gate_constitution`, the preceding phase is `constitution_draft` → `guidance/constitution.md`).
   - If the guidance file **exists**: Read it. Produce a **Guidance Alignment** section immediately below the artifact content:
     ```
     ### Guidance Alignment — guidance/<phase>.md
     ✅ Covered: <bullet list of guidance items clearly addressed in the artifact>
     ⚠️  Gaps: <bullet list of guidance items absent or only partially addressed>
     ```
     If every item is covered: show `✅ All guidance items addressed.` and no gaps.
   - If the guidance file **does not exist**: skip this step silently — do not mention guidance at all.
4. THEN display the gate prompt below.

The user must never need to open an external file to know what they are approving.

**Gate prompt format:**

```
---
✋ APPROVAL REQUIRED — Gate {gate_number}/8: {Gate Label}

<artifact content displayed above>

Artifact path: {current_artifact}
Fingerprint: {current_artifact_sha}

Please review the content above, then respond with:
  • `approve` — Accept and advance to the next phase
  • `approve with comments: <your notes>` — Accept with recorded feedback
  • `reject with comments: <your feedback>` — Reject and trigger remediation
---
```

**On `approve` or `approve with comments`:**

> **Drift Re-Approval Mode check (evaluate FIRST, before normal approve flow):**
>
> If `state.json → drift_queue` is non-empty, this approval is a drift re-approval, not a normal gate advance. Handle as follows:
>
> 1. `gate_key` = `drift_queue[0]` (the gate being re-approved; do NOT use PHASE_TO_GATE_KEY here).
> 2. Resolve the artifact path from **ARTIFACT_OWNERSHIP** using `gate_key` (substitute `current_feature_id` if needed).
> 3. Run `sdle.sh gate approve --gate <drift_queue[0]>` (add `--comments`). The script re-fingerprints the artifact as the new baseline, records the approval, pops the queue and audits it. Approving out of queue order is refused.
>
> - **If `drift_queue` is now empty:**
>   - Restore `current_phase` = `state.json → pending_phase`. Clear `pending_phase = null`. Set `status = "in_progress"`. Save state.
>   - Confirm to user: "✅ All drift re-approvals complete. Resuming {pending_phase}…"
>   - Read `modules/phase-execution.md` and execute the restored `current_phase` (starting from step 1 — the drift check in step 0 will now pass).
> - **If `drift_queue` is still non-empty:**
>   - Present the next drifted gate's full artifact content for re-approval (same RE-APPROVAL gate prompt format from phase-execution.md step 0.5). Show `(Re-approval {completed+1}/{total} …)`.
>   - HALT — do not execute the normal approve flow below.
>
> **DO NOT proceed to the normal approve flow when in drift re-approval mode.**

1. Derive `gate_key` by looking up `current_phase` in **PHASE_TO_GATE_KEY** (Internal Constants). Never derive it from `current_phase` string directly.
2. Record in `state.json` under `approvals[gate_key]`: `{ "decision": "approved", "comments": "<text or null>", "timestamp": "<ISO>" }`.
3. **Record approval-time SHA:** the script fingerprints the artifact and writes `artifact_shas[gate_key]` as the drift baseline.
4. Append to audit: `[<ISO>] Gate <N> approved. Baseline SHA recorded: <sha>. Comments: <text or none>.`
5. Append to `state.json → phase_history`: `{ "phase": "<current_phase>", "completed_at": "<ISO>", "outcome": "approved" }`. Set `last_updated`. Save state.
6. Derive `next_phase` by looking up `current_phase` in **NEXT_PHASE** (Internal Constants).
7. **gate_security special case:** If `gate_key` is `gate_security`:
   a. Write `.workflow/completion-summary.json`:
      ```json
      {
        "workflow_version": "<state.workflow_version>",
        "project_name": "<state.project_name>",
        "completed_at": "<ISO timestamp>",
        "phases_completed": <count of phase_history entries>,
        "security_review_artifact": "<state.security_review_artifact>",
        "all_gates_approved": true
      }
      ```
   b. Set `current_phase` to `complete`, `status` to `completed`, update `progress` from **PROGRESS_MAP**.
   c. Save state.
   d. Append to audit: `[<ISO>] Gate 8/8 (security) approved. Workflow complete. Completion summary written.`
   e. Congratulate the user:
      ```
      ✅ Security review approved. Workflow complete!

      All 8 gates passed. Completion summary: .workflow/completion-summary.json
      Security review: <security_review_artifact>
      ```
   f. HALT — do not propose a next phase.
8. Set `current_phase` to `next_phase`, `status` to `pending`, update `progress` from **PROGRESS_MAP**. Set `last_updated`. Save state.
9. Propose executing the next phase: "Approved! Moving to Phase <N+1>: <label>. Shall I proceed?"

**On `reject with comments`:**
- Go to Step 7: Rejection & Remediation (below).

---

## Step 7: Rejection & Remediation

**On rejection:**

> **Drift Re-Approval Mode check (evaluate FIRST):**
>
> If `state.json → drift_queue` is non-empty, this rejection is during a drift re-approval. Handle as follows:
>
> 1. `gate_key` = `drift_queue[0]`.
> 2. Record in `state.json → approvals[gate_key]`: `{ "decision": "rejected", "comments": "<text>", "timestamp": "<ISO>" }`.
> 3. Clear `drift_queue = []`. Clear `pending_phase = null`. Set `status = "rejected"`. Save state.
> 4. Append to audit: `[<ISO>] Drift re-approval REJECTED for <gate_key>. Feedback: <text>. Drift queue cleared.`
> 5. Respond:
>    ```
>    Drift re-approval rejected for {gate_label}.
>
>    Your feedback: "{rejection comments}"
>
>    The drift re-approval queue has been cleared. To fix this, you need to regenerate the artifact that was modified.
>    Use `restart phase <N>` where N is the phase number for the preceding execution phase (the one that originally produced this artifact), then re-run the workflow from there.
>    ```
> 6. HALT — do not execute the normal rejection flow below.

1. Derive `gate_key` from **PHASE_TO_GATE_KEY** (Internal Constants) using `current_phase`.
2. Record in `state.json` under `approvals[gate_key]`: `{ "decision": "rejected", "comments": "<text>", "timestamp": "<ISO>" }`.
   - `state.json` is the **canonical source** of the feedback text. Everything else derives from it.
3. Set `status` to `rejected`. Set `last_updated`. Save state immediately.
4. Append to audit: `[<ISO>] Gate <N> rejected. Comments: <text>.`
5. Respond:
```
Understood — I've recorded your feedback in state.json:

"{rejection comments}"

Say "continue" to re-run the {Phase Label} step with this feedback applied.
```

**On `continue` after rejection:**
1. Read feedback text from `state.json → approvals[gate_key].comments` (canonical source).
2. Derive `gate_key` from `current_phase` using **PHASE_TO_GATE_KEY**. Look up `gate_key` in **GATE_TO_EXECUTION_PHASE** (above) to determine whether re-execution is SpecKit-based or SDLE-native.
3. **Remediation rate-limit check:** `sdle.sh remediate begin --gate <gate_key>`.

   The script reads the canonical feedback from `approvals[<gate_key>].comments`, checks the counter against `max_remediation_attempts` for the *execution* phase, and refuses with `rate_limit_exceeded` at the limit — **without invoking anything**. On refusal show the message, which names the audited commands to raise the limit or reset the counter, and halt.

   On success it increments the counter, sets `status: in_progress`, and writes `.specify/sdle-feedback.md` from canonical state.

5. **If execution type is SDLE-native** (gate_design or gate_security):
   - **For `gate_design`:** Read `modules/phase-execution.md`. Re-execute Phase 13 (`design_generation`) with this context prepended: `"REMEDIATION RUN — Reviewer feedback to incorporate: <paste feedback text>. Ensure both design documents address these concerns."` After generation and Post-SpecKit Verification, proceed to step 7.
   - **For `gate_security`:** Pre-compute a new `review_filename` with an updated timestamp. Update `security_review_artifact` in state to the new filename. Save state. Read `modules/security-review.md`. Re-run the security review with this context prepended: `"REMEDIATION RUN — Reviewer feedback to address: <paste feedback text>."` Pass the new `review_filename` as the output path. After generation and Post-SpecKit Verification, proceed to step 7.
6. **If execution type is SpecKit:**
   - If `.specify/sdle-feedback.md` content does not match current state (re-check after writing in step 4), re-write it. The file must match canonical state before invoking SpecKit.
   - Re-invoke the relevant SpecKit skill via the Skill tool. Include in args: `"Incorporate reviewer feedback from .specify/sdle-feedback.md. Feedback: <paste comments text directly into args as well, as a fallback>."`
   *(Embedding the text directly in args means the feedback reaches SpecKit even if file lookup fails.)*
7. After the skill/module completes and Post-SpecKit Verification passes: `sdle.sh remediate finish --gate <gate_key>`. It archives the feedback file, deletes the working copy, and audits the completion.
8. Present the gate prompt (Step 6 above) with the newly regenerated artifact.
