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
4. **Review status:** run `sdle.sh artifact reviews --path <current_artifact>` and read the entry for this artifact. Show the review type, result and actor in the prompt's `Review:` line. If it is not a current `PASS`, do not display the prompt — record the review first (see **Governed Artifact Review** in `modules/phase-execution.md`); `gate approve` would refuse anyway, and asking for an approval you know will be refused wastes the user's decision.
5. **Review capability:** if `capabilities` for this phase names a review file (`modules/design-review.md`, `modules/code-review.md`, `modules/security-review.md`), that file is how the review behind the `Review:` line is conducted and recorded. Loading it does not move the decision: the artifact content is still displayed here and the approval is still a human act in this conversation.
6. **Requirement status:** read `required` and `requirement_reasons` from `sdle.sh gate show --gate <gate_key>`. **Ask the engine; never decide this from a risk level yourself.** If `required` is `true`, the protocol below is unchanged. If it is `false`, this gate is *omittable* — see **Step 6b** — and you still display the artifact content first. If it is `null` the engine has no answer for this runtime (no WorkItem, so no governance record); treat the gate as required.
7. THEN display the gate prompt below.

The user must never need to open an external file to know what they are approving.

**Gate prompt format:**

```
---
✋ APPROVAL REQUIRED — Gate {gate_number}/{gate_total}: {Gate Label}

<artifact content displayed above>

Artifact path: {current_artifact}
Fingerprint: {current_artifact_sha}
Review: {reviewType} | {result} | {actor_type}:{actor_name}

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
> 2. Run `sdle.sh gate approve --gate <gate_key>` (add `--comments`). The script resolves the artifact from **ARTIFACT_OWNERSHIP**, re-fingerprints it as the new baseline, records the approval, pops the queue and audits it. Approving out of queue order is refused. When the queue empties it restores `pending_phase` as the current phase, clears `pending_phase` and sets the status back to `in_progress`; the response reports `drift_mode`, `remaining_drift` and `resumed_phase`.
>
> - **If `remaining_drift` is empty:**
>   - Confirm to user: "✅ All drift re-approvals complete. Resuming {resumed_phase}…"
>   - Read `modules/phase-execution.md` and execute the restored current phase (starting from step 1 — the drift check in step 0 will now pass).
> - **If `remaining_drift` is not empty:**
>   - Present the next drifted gate's full artifact content for re-approval (same RE-APPROVAL gate prompt format from phase-execution.md step 0.5). Show `(Re-approval {completed+1}/{total} …)`.
>   - HALT — do not execute the normal approve flow below.
>
> **DO NOT proceed to the normal approve flow when in drift re-approval mode.**

1. Derive `gate_key` by looking up `current_phase` in **PHASE_TO_GATE_KEY** (Internal Constants). Never derive it from `current_phase` string directly.
2. Run `sdle.sh gate approve --gate <gate_key>` (add `--comments "<text>"`). The script is the only writer of the record: it refuses unless every precondition holds (a current PASS review, an artifact that has not drifted), then records the approval and the approval-time SHA as the drift baseline, appends the audit entry and the phase history, moves the workflow to the bound flow's next phase and saves the state. **NEXT_PHASE** is the *registry* chain, not the bound flow's — under GREENFIELD it maps `requirements_check` to `impact_analysis`, a phase GREENFIELD does not contain — so never derive the next phase from a table: read `next_phase`, `status` and `progress` from the response. `progress` is derived from the bound flow; **PROGRESS_MAP** (the GREENFIELD view) is never the value to copy. Do not edit `state.json` or `audit.md` yourself.
3. **Final gate.** When the response carries a `completion_summary` path, the script has already written `completion-summary.json` into the bound WorkItem's own runtime, set the status to `completed`, moved to `complete`, established the repository baseline where the flow does (the response's `baseline`) and audited `workflow_complete`. Congratulate the user, naming the path the response returned:
   ```
   ✅ Approved. Workflow complete!

   All {gate_total} gates passed. Completion summary: <completion_summary from the response>
   Security review: <security_review_artifact>
   ```
   Then HALT — do not propose a next phase.
4. Otherwise propose executing the next phase: "Approved! Moving to Phase <N+1>: <label>. Shall I proceed?" — the phase and its label come from the response.

**On `reject with comments`:**
- Go to Step 7: Rejection & Remediation (below).

---

## Step 6b: A Gate the Policy Does Not Require

`gate show` reporting `required: false` means the governance policy does not require a **human approval** for this gate on this WorkItem. It means nothing else. The artifact was still generated, still registered, still reviewed and still fingerprinted, and it is still watched for drift.

Display the artifact content exactly as Step 6 requires — the user is still entitled to see what is being passed — then say, in the conversation, that the policy does not require an approval here and give the reason the engine returned. Offer both options and let the user choose:

```
---
ℹ️  APPROVAL NOT REQUIRED — Gate {gate_number}/{gate_total}: {Gate Label}

<artifact content displayed above>

Artifact path: {current_artifact}
Fingerprint: {current_artifact_sha}
Review: {reviewType} | {result} | {actor_type}:{actor_name}

The governance policy in effect does not require a human approval for this
gate on this WorkItem. You may still approve it — that is always permitted
and always the stricter choice. Respond with:
  • `approve` — Approve it anyway, and record the approval
  • `omit` — Pass it on the policy's authority, recorded and audited
  • `reject with comments: <your feedback>` — Reject and trigger remediation
---
```

On `omit`, run `sdle.sh gate omit --gate <gate_key>`. The engine re-derives the requirement itself, refuses `gate_required` if it turns out the gate *is* required, records the decision as an omission distinct from an approval, writes a `gate_omitted` entry naming the policy and the risk level, and advances. Report what it returns; do not compute the next phase.

**You may never omit a required gate, and there is no flag that lets you.** If `gate omit` refuses `gate_required`, print the message and the reasons and ask the user to approve or reject. That refusal is the guardrail working.

**Re-assessing risk is not a way of clearing a gate.** When `gate omit` refuses, the answer is `approve` or `reject` — never "re-run `governance assess` with fewer risk signals until the gate becomes omittable". Re-assessment exists for one reason: the WorkItem's actual scope changed. If it genuinely did, say so to the user and re-assess openly. The engine records a re-assessment that **lowers** a previously recorded final level as a `governance_downgraded` audit entry, and carries it into the evidence of every gate omitted afterwards, so the omission and the level it rests on are read together. A downgrade is never refused — a real re-scope is legitimate — and never invisible.

## Step 7: Rejection & Remediation

**On rejection:**

> **Drift Re-Approval Mode check (evaluate FIRST):**
>
> If `state.json → drift_queue` is non-empty, this rejection is during a drift re-approval. Handle as follows:
>
> 1. `gate_key` = `drift_queue[0]`.
> 2. Run `sdle.sh gate reject --gate <gate_key> --reason "<text>"`. The script records the rejection, clears `drift_queue` and `pending_phase`, sets the status to `rejected` and audits it.
> 3. Respond:
>    ```
>    Drift re-approval rejected for {gate_label}.
>
>    Your feedback: "{rejection comments}"
>
>    The drift re-approval queue has been cleared. To fix this, you need to regenerate the artifact that was modified.
>    Use `restart phase <N>` where N is the phase number for the preceding execution phase (the one that originally produced this artifact), then re-run the workflow from there.
>    ```
> 4. HALT — do not execute the normal rejection flow below.

1. Derive `gate_key` from **PHASE_TO_GATE_KEY** (Internal Constants) using `current_phase`.
2. Run `sdle.sh gate reject --gate <gate_key> --reason "<text>"`. The script records the rejection under `approvals[gate_key]` — the **canonical source** of the feedback text, from which everything else derives — sets the status to `rejected` and audits it. Do not edit `state.json` or `audit.md` yourself.
3. Respond:
```
Understood — I've recorded your feedback:

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
   - **For `gate_security`:** Run `sdle.sh security-review begin`; it names a new `review_filename` with an updated timestamp and pins it as `security_review_artifact`. Read `modules/security-review.md`. Re-run the security review with this context prepended: `"REMEDIATION RUN — Reviewer feedback to address: <paste feedback text>."` Pass the new `review_filename` as the output path. After generation and Post-SpecKit Verification, proceed to step 7.
6. **If execution type is SpecKit:**
   - If `.specify/sdle-feedback.md` content does not match current state (re-check after writing in step 4), re-write it. The file must match canonical state before invoking SpecKit.
   - Re-invoke the relevant SpecKit skill via the Skill tool. Include in args: `"Incorporate reviewer feedback from .specify/sdle-feedback.md. Feedback: <paste comments text directly into args as well, as a fallback>."`
   *(Embedding the text directly in args means the feedback reaches SpecKit even if file lookup fails.)*
7. After the skill/module completes and Post-SpecKit Verification passes: `sdle.sh remediate finish --gate <gate_key>`. It archives the feedback file, deletes the working copy, and audits the completion.
8. Present the gate prompt (Step 6 above) with the newly regenerated artifact.
