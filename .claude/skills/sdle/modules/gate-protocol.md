> **SDLE module — loaded on demand.** Assumes Internal Constants (PHASE_SEQUENCE, NEXT_PHASE, PHASE_TO_GATE_KEY, GATE_PHASES, PROGRESS_MAP) are already in context from SKILL.md. Do not duplicate them here.

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
✋ APPROVAL REQUIRED — Gate {gate_number}/5: {Gate Label}

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
1. Derive `gate_key` by looking up `current_phase` in **PHASE_TO_GATE_KEY** (Internal Constants). Never derive it from `current_phase` string directly.
2. Record in `state.json` under `approvals[gate_key]`: `{ "decision": "approved", "comments": "<text or null>", "timestamp": "<ISO>" }`.
3. Append to audit: `[<ISO>] Gate <N> approved. Comments: <text or none>.`
4. Derive `next_phase` by looking up `current_phase` in **NEXT_PHASE** (Internal Constants).
5. Set `current_phase` to `next_phase`, `status` to `pending`, update `progress` from **PROGRESS_MAP**.
6. Save state.
7. Propose executing the next phase: "Approved! Moving to Phase <N+1>: <label>. Shall I proceed?"

**On `reject with comments`:**
- Go to Step 7: Rejection & Remediation (below).

---

## Step 7: Rejection & Remediation

**On rejection:**
1. Derive `gate_key` from **PHASE_TO_GATE_KEY** (Internal Constants) using `current_phase`.
2. Record in `state.json` under `approvals[gate_key]`: `{ "decision": "rejected", "comments": "<text>", "timestamp": "<ISO>" }`.
   - `state.json` is the **canonical source** of the feedback text. Everything else derives from it.
3. Set `status` to `rejected`. Save state immediately.
4. Append to audit: `[<ISO>] Gate <N> rejected. Comments: <text>.`
5. Write `.specify/sdle-feedback.md` as a **convenience copy** for SpecKit context (not canonical):
   ```markdown
   # SDLE Feedback for <phase_id> — <ISO timestamp>
   **Gate:** <gate_label>
   **Canonical source:** .workflow/state.json → approvals[<gate_key>].comments
   **Reviewer comments:**
   <rejection comments>
   ```
6. Respond:
```
Understood — I've recorded your feedback in state.json:

"{rejection comments}"

Say "continue" to re-run the {Phase Label} step with this feedback applied.
```

**On `continue` after rejection:**
1. Read feedback text from `state.json → approvals[gate_key].comments` (canonical source).
2. If `.specify/sdle-feedback.md` is missing or its content does not match, re-write it from `state.json` before invoking SpecKit. The file must match the canonical state before proceeding.
3. Set `status` to `in_progress`. Save state.
4. Re-invoke the relevant SpecKit skill via the Skill tool. Include in args:
   `"Incorporate reviewer feedback from .specify/sdle-feedback.md. Feedback: <paste comments text directly into args as well, as a fallback>."`
   *(Embedding the text directly in args means the feedback reaches SpecKit even if file lookup fails.)*
5. After the skill completes and Post-SpecKit Verification passes (see `modules/phase-execution.md`):
   - Archive: write `.specify/sdle-feedback-archive-<ISO-timestamp>.md` with the same content.
   - Delete `.specify/sdle-feedback.md`.
   - Append to audit: `[<ISO>] Remediation complete for <phase_id>. Feedback archived.`
6. Present the gate prompt (Step 6 above) with the newly regenerated artifact.
