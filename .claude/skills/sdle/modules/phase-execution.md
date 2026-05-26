> **SDLE module — loaded on demand.** Assumes Internal Constants (PHASE_SEQUENCE, NEXT_PHASE, PHASE_TO_GATE_KEY, GATE_PHASES, PROGRESS_MAP, ARTIFACT_OWNERSHIP, PHASE_LABEL_MAP) are already in context from SKILL.md. Do not duplicate them here.

## Step 5: Phase Execution

### Guidance File Map

Before invoking SpecKit for any phase, check whether the user has placed a guidance file in `guidance/`. These files are optional — their presence shapes SpecKit's output; their absence changes nothing.

| Phase | Guidance file |
|---|---|
| `constitution_draft` | `guidance/constitution.md` |
| `spec_draft` | `guidance/spec.md` |
| `plan_draft` | `guidance/plan.md` |
| `checklist_draft` | `guidance/checklist.md` |
| `tasks_draft` | `guidance/tasks.md` |
| `analyze` | `guidance/analyze.md` |
| `implement` | `guidance/implement.md` |
| `design_generation` | `guidance/design.md` |

### BEFORE executing any phase:

**Step 0 — Artifact Drift Check (MANDATORY — runs before updating status):**

For each `gate_key` in `state.json → approvals` where `decision == "approved"`:

a. Look up `gate_key` in **ARTIFACT_OWNERSHIP** (Internal Constants). Get `artifact_path_template`.
b. If `artifact_path_template` is `"(none)"` → skip this gate.
c. If `state.json → artifact_shas[gate_key]` is null or missing → skip this gate (pre-v1.8 approval, no baseline SHA recorded).
d. Resolve path:
   - Replace `{current_feature_id}` with `state.json → current_feature_id`. If `current_feature_id` is null and the template contains `{current_feature_id}` → skip this gate (feature ID not yet resolved).
   - Replace `{security_review_artifact}` with `state.json → security_review_artifact`. If `security_review_artifact` is null and the template contains `{security_review_artifact}` → skip this gate.
e. Compute the current SHA of the resolved file using PowerShell:
   ```powershell
   (Get-FileHash -Algorithm SHA256 "<resolved_path>").Hash
   ```
   If the file does not exist: treat as drifted (SHA = `"FILE_MISSING"`).
f. Compare computed SHA to `artifact_shas[gate_key]`. If they differ: add `gate_key` to a local `drifted_gates` list.

After checking all approved gates:

- **If `drifted_gates` is empty:** proceed normally to Step 0b below.
- **If `drifted_gates` is non-empty:**
  1. Sort `drifted_gates` by their corresponding gate phase position in **PHASE_SEQUENCE** (ascending — most upstream gate first).
  2. Save to state: `drift_queue = drifted_gates`, `pending_phase = current_phase`, `status = "awaiting_reapproval"`. Save state.
  3. Append to audit: `[<ISO>] Artifact drift detected for gates: <gate_keys>. Entering drift re-approval mode. Pending phase: <current_phase>.`
  4. Surface the following (always shown, regardless of verbose):
     ```
     ⚠️ Artifact drift detected — {N} previously-approved artifact(s) changed since approval:

     {for each gate_key in drifted_gates (sorted):}
       • {gate_label} ({gate_key})
         Path:          {resolved_artifact_path}
         Approved SHA:  {artifact_shas[gate_key]}
         Current SHA:   {computed_sha}

     These artifact(s) must be re-approved before {current_phase} can proceed.
     ```
  5. Present the first drifted gate's full artifact content for re-approval — same format as Step 6 gate prompt (read `modules/gate-protocol.md`), but with the header:
     ```
     ✋ RE-APPROVAL REQUIRED — Gate {gate_number}/8: {Gate Label}
     (Re-approval {1}/{total_drifted}: artifact was modified after original approval)
     ```
  6. **HALT** — do not proceed with phase execution. The drift re-approval flow in gate-protocol.md will handle `approve`/`reject with comments` from here.

**Step 0b — Idempotency Check (runs after drift check, before updating status):**

If `state.json → phase_checkpoint` is non-null:
1. This phase was previously started but interrupted. Attempt recovery:
   - Look up the expected artifact for the current phase (from the Phase Execution Map below).
   - If the artifact exists and passes size verification (≥100 bytes): skip re-invocation. Set `phase_checkpoint: null`. Save state. Proceed directly to Post-SpecKit Verification and then the gate.
   - If the artifact is missing or too small: clear `phase_checkpoint: null`. Save state. Proceed with normal phase execution (re-invoke SpecKit).
2. If `phase_checkpoint` is null: proceed normally to step 1 below.

1. Update `state.json`: set `status` to `in_progress`.
2. Append to `.workflow/audit.md`: `[<ISO timestamp>] Phase <N> (<phase_id>) started.`
3. Tell the user what you are about to do.
4. **Guidance injection:** Look up the current phase in the Guidance File Map above. If the file exists: Read it. You will append its content to the SpecKit `args` in the next step (see per-phase blocks below). If the file does not exist: skip silently.

### Phase Execution Map:

**Phase 2 — `constitution_draft`:**
- Set `phase_checkpoint: "speckit_invoked"`. Save state.
- Invoke `speckit-constitution` using the Skill tool. If `guidance/constitution.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/constitution.md>\n---\nAlign your output with this guidance."`
- Record artifact: `.specify/memory/constitution.md` in state.
- Run Post-SpecKit Verification (clear `phase_checkpoint` on success), then run Post-Generation Clarify.
- After completion: update state to `gate_constitution` / `awaiting_approval`.
- Append audit: "Constitution generated."
- Present the gate prompt (read `modules/gate-protocol.md`).

**Phase 4 — `spec_draft`:**
- Set `phase_checkpoint: "speckit_invoked"`. Save state.
- Invoke `speckit-specify` using the Skill tool. If `guidance/spec.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/spec.md>\n---\nAlign your output with this guidance."`
- **Feature-ID Resolution (MANDATORY after spec runs):** Glob `.specify/specs/*/` to list all subdirectories. The feature directory is the one created most recently (by modification time). Store its name as `current_feature_id` in `state.json`. If zero directories exist: set `status` to `failed` and surface an error. If multiple directories exist and none is clearly newer: list them and ask the user to confirm which one is the current feature.
- Record artifact: `.specify/specs/{state.current_feature_id}/spec.md`.
- Run Post-SpecKit Verification (clear `phase_checkpoint` on success), then run Post-Generation Clarify.
- After completion: update state to `gate_spec` / `awaiting_approval`.
- Append audit: `"Specification generated. Feature ID: {current_feature_id}."`
- Present the gate prompt.

**Phase 6 — `plan_draft`:**
- Set `phase_checkpoint: "speckit_invoked"`. Save state.
- Invoke `speckit-plan` using the Skill tool. If `guidance/plan.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/plan.md>\n---\nAlign your output with this guidance."`
- Record artifact: `.specify/specs/{state.current_feature_id}/plan.md`.
- Run Post-SpecKit Verification (clear `phase_checkpoint` on success), then run Post-Generation Clarify.
- After completion: update state to `gate_plan` / `awaiting_approval`.
- Append audit: "Plan generated."
- Present the gate prompt.

**Phase 8 — `checklist_draft`:**
- Set `phase_checkpoint: "speckit_invoked"`. Save state.
- Invoke `speckit-checklist` using the Skill tool. If `guidance/checklist.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/checklist.md>\n---\nAlign your output with this guidance."`
- **Checklist artifact handling (conditional):**
  - If `.specify/specs/{state.current_feature_id}/checklist.md` was produced and is ≥100 bytes:
    - Record artifact path in state.
    - Run Post-SpecKit Verification (clears `phase_checkpoint` on success, records SHA).
    - Run Post-Generation Clarify.
    - Append audit: "Checklist generated."
  - If checklist.md was **not produced** or is <100 bytes:
    - Append audit: "Checklist not produced by SpecKit — proceeding without it."
    - Clear `phase_checkpoint: null`. Save state.
    - Run Post-Generation Clarify (no artifact to verify — pass phase_id as context only).
    - Do **not** set status to "failed". Do not halt.
- Immediately proceed to Phase 9.

**Phase 9 — `tasks_draft`:**
- Set `phase_checkpoint: "speckit_invoked"`. Save state.
- Invoke `speckit-tasks` using the Skill tool. If `guidance/tasks.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/tasks.md>\n---\nAlign your output with this guidance."`
- Record artifact: `.specify/specs/{state.current_feature_id}/tasks.md`.
- Run Post-SpecKit Verification (clear `phase_checkpoint` on success), then run Post-Generation Clarify.
- After completion: update state to `gate_tasks` / `awaiting_approval`.
- Append audit: "Tasks generated."
- **Before presenting the gate prompt:** If `.specify/specs/{state.current_feature_id}/checklist.md` exists, Read it and display its full content to the user under the header `### Checklist (Phase 8 output — review alongside Tasks)`. This ensures the user can compare both artifacts before approving.
- Present the gate prompt (read `modules/gate-protocol.md` for gate_tasks/Gate 4). The gate artifact is `tasks.md`.

**Phase 10 — `gate_tasks`:**
This is a gate phase. Do not invoke SpecKit. Read `modules/gate-protocol.md` and follow its procedure for gate_tasks (Gate 4/8).

**Phase 11 — `analyze`:**
- Set `phase_checkpoint: "speckit_invoked"`. Save state.
- Invoke `speckit-analyze` using the Skill tool. If `guidance/analyze.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/analyze.md>\n---\nAlign your output with this guidance."`
- After the skill completes: set `current_artifact` to `.specify/specs/{state.current_feature_id}/tasks.md`. Compute SHA-256 via PowerShell: `(Get-FileHash -Algorithm SHA256 ".specify/specs/{current_feature_id}/tasks.md").Hash`. Set `current_artifact_sha` to the returned hash. Clear `phase_checkpoint: null`. Save state.
- Set `state.json → clarification_phase: "analyze"`. Save state.
- Append to audit: `[<ISO>] Analysis complete. Artifact fingerprinted (tasks.md). Awaiting optional user clarifications.`
- Tell the user: "Analysis is complete. If you have additional context or clarifications to add, provide them now — they will be saved to `clarifications/analyze-<YYYY-MM-DD-HHmm>.clarify`. Say `continue`, `approve`, or `reject` to proceed straight to the gate."
- **HALT** — wait for the Clarification Response Handler in Step 4 to process the user's next message before presenting the gate.

**Phase 12 — `gate_analyze`:**
This is a gate phase. The artifact for this gate is the most recently updated `tasks.md` (which speckit-analyze may have refined). Do not invoke SpecKit. Read `modules/gate-protocol.md` and follow its procedure for gate_analyze (Gate 5/8).

**Phase 13 — `design_generation`:**
- Do NOT invoke SpecKit. This is an SDLE-native phase.
- **Guidance:** If `guidance/design.md` was read in step 4 above, use its content to shape the structure, emphasis, and level of detail in both design documents.
- **Checkpoint recovery (Phase 13 — overrides generic Step 0b for this phase):**
  - If `phase_checkpoint == "design_app_started"`: App design was started but not confirmed complete. If `design/app/app-design.md` exists and is ≥100 bytes, advance checkpoint to `"design_app_done"` (save state) and skip to Step B. Otherwise, clear checkpoint (save state) and re-run from Step A.
  - If `phase_checkpoint == "design_app_done"`: App design is confirmed complete. Skip Step A and proceed directly to Step B.
  - If `phase_checkpoint` is null: proceed normally from Step A.
- **Step A — App Design (`design/app/app-design.md`):**
  - Set `phase_checkpoint: "design_app_started"`. Save state.
  - Create the `design/app/` directory if it does not exist.
  - Read the following for context: `.specify/memory/constitution.md`, `.specify/specs/{state.current_feature_id}/spec.md`, `.specify/specs/{state.current_feature_id}/plan.md`, `.specify/specs/{state.current_feature_id}/tasks.md` (if they exist).
  - Generate `design/app/app-design.md` containing all of the following sections:
    1. **Context Diagram** — system boundary, external actors, and major external integrations (text-based or Mermaid `C4Context` diagram).
    2. **Component Diagram** — internal components/modules and their relationships (Mermaid `C4Component` or `graph` diagram).
    3. **Detail-Level Design** — per-component narrative: responsibilities, key interfaces, data flows, and technology choices.
    4. **Sequence Diagrams** — at least one Mermaid `sequenceDiagram` per major user-facing flow or integration point.
    5. **Important Design Decisions** — table of significant decisions with rationale, alternatives considered, and trade-offs.
  - Set `phase_checkpoint: "design_app_done"`. Save state.
- **Step B — DB Design (`design/db/db-design.md`) — conditional:**
  - Read `design/app/app-design.md` and the spec. If the feature involves persistent data storage (database, data store, or structured persistence):
    - Create the `design/db/` directory if it does not exist.
    - Generate `design/db/db-design.md` containing:
      1. **ERD** — entity-relationship diagram (Mermaid `erDiagram`).
      2. **Data Dictionary** — table with columns: Entity, Attribute, Type, Constraints, Description.
      3. **Design Decisions** — indexing strategy, normalization choices, partitioning, migration notes.
  - If no persistent storage is involved: skip Step B and note "No database design required" in the audit entry.
- Run Post-SpecKit Verification against `design/app/app-design.md` (size ≥ 100 bytes, SHA-256 fingerprint). If `design/db/db-design.md` was also generated, record it as a secondary artifact in audit.
- Clear `phase_checkpoint: null`. Save state.
- After completion: update state to `gate_design` / `awaiting_approval`.
- Append audit: "Design generation complete. App design: design/app/app-design.md. DB design: design/db/db-design.md (or 'not applicable')."
- Present the gate prompt (read `modules/gate-protocol.md`).

> **Note for implementors:** The design documents generated in this phase (Phase 13) are available to SpecKit in Phase 15 (implement). SDLE will reference them in the implementation invocation args so that design decisions inform the generated code.

**Phase 14 — `gate_design`:**
This is a gate phase. Do not invoke SpecKit. Read `modules/gate-protocol.md` and follow its procedure for gate_design (Gate 6/8).

**Phase 15 — `implement`:**
- Set `phase_checkpoint: "speckit_invoked"`. Save state.
- Invoke `speckit-implement` using the Skill tool. If `guidance/implement.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/implement.md>\n---\nAlign your output with this guidance."` Also append: `"\n\nDesign documents are available at design/app/app-design.md and (if present) design/db/db-design.md. Align implementation with these design decisions."`
- **Implementation Manifest (MANDATORY after speckit-implement):**
  - Run `git diff --name-only HEAD` (or `git status --short` if HEAD does not exist) to list files changed or added by the implementation.
  - Write `.workflow/implementation-manifest.md` with the following content:
    ```markdown
    # Implementation Manifest
    Generated: <ISO timestamp>
    Phase: implement (Phase 15/18)

    ## Changed/Added Files
    <list each file, one per line>

    ## Summary
    <one-paragraph description of what was implemented, derived from the tasks.md>
    ```
  - If git is not initialized: list files in the working directory that match common source file patterns (*.ts, *.py, *.js, *.go, *.java, etc.) and note "git not initialized — file list is approximate."
  - Set `current_artifact` to `.workflow/implementation-manifest.md` in state.
- Run Post-SpecKit Verification against `.workflow/implementation-manifest.md` (size ≥ 100 bytes, SHA-256 fingerprint). Clear `phase_checkpoint` on success.
- After completion: update state to `gate_implement` / `awaiting_approval`.
- Append audit: "Implementation complete."
- Present the gate prompt (read `modules/gate-protocol.md`).

**Phase 16 — `gate_implement`:**
This is a gate phase. The artifact is `.workflow/implementation-manifest.md`. Do not invoke SpecKit. Read `modules/gate-protocol.md` and follow its procedure for gate_implement (Gate 7/8).

**Phase 17 — `security_review`:**
- Do NOT invoke SpecKit.
- **Pre-compute the review filename** using the current local time: `review_filename = "reviews/security-review-<YYYY-MM-DD-HHmm>.md"` (e.g., `reviews/security-review-2026-05-26-1430.md`). Use the actual current date/time — do not use a placeholder.
- Set `phase_checkpoint: "security_review_started"` and `security_review_artifact = review_filename` in state immediately. Save state. (This ensures crash recovery and drift detection know the target path before generation begins.)
- Read `modules/security-review.md` and follow its procedure. Pass `review_filename` as the explicit output path — the module must write to this exact path, not generate a new timestamped name.
- After the review file is confirmed written at `review_filename`: set `current_artifact` to `review_filename`. Run Post-SpecKit Verification (size ≥ 100 bytes, SHA-256 fingerprint). Clear `phase_checkpoint` on success.
- After completion: update state to `gate_security` / `awaiting_approval`.
- Append audit: `"Security review complete. Artifact: <review_filename>."`
- Present the gate prompt (read `modules/gate-protocol.md`).

**Phase 18 — `gate_security`:**
This is a gate phase. The artifact is the security review file at `state.json → security_review_artifact`. Do not invoke SpecKit. Read `modules/gate-protocol.md` and follow its procedure for gate_security (Gate 8/8).

On approve: write `.workflow/completion-summary.json` (see gate-protocol.md for the content format), set `status = "completed"`, set `current_phase = "complete"`, and congratulate the user.

---

### Post-Generation Clarify (MANDATORY — for constitution, spec, plan, checklist, tasks)

After Post-SpecKit Verification passes for Phases 2, 4, 6, 8, and 9, invoke the clarify skill **before** presenting the gate or advancing to the next phase:

1. Invoke `{speckit_skill_prefix}clarify` using the Skill tool. Pass in args: the current phase name and the path of the verified artifact (e.g. `"Phase: constitution_draft. Artifact: .specify/memory/constitution.md"`).
2. If clarify **fails or produces no output**: log to audit and continue to the gate/next phase normally. Do not block.
3. If clarify **produces output (questions)**:
   - Display the questions to the user.
   - Set `state.json → clarification_phase: <current_phase_id>`. Save state.
   - Append to audit: `[<ISO>] Clarify produced questions for <phase_id>. Awaiting user clarification response.`
   - Tell the user: "Please answer the above questions — your response will be saved to `clarifications/<phase_id>-<YYYY-MM-DD-HHmm>.clarify`. Say `continue` to skip without saving."
   - **HALT** — do not advance to the gate or next phase. The Clarification Response Handler in Step 4 will process the user's next message.
4. If clarify produces informational output only (no questions): log to audit and continue to gate/next phase normally.

This step does not apply to `analyze` (Phase 11), `implement` (Phase 15), or `design_generation` (Phase 13).

---

### Post-SpecKit Verification (MANDATORY — after every SpecKit skill invocation and every SDLE-native artifact generation)

After invoking ANY `speckit-*` skill or generating any SDLE-native artifact, execute these steps before advancing:

1. **Read the expected artifact file** (the path listed in each phase block above).
2. **Check size:**
   - If file does not exist OR content is fewer than 100 bytes:
     - Set `state.json` `status` to `"failed"`. Save state. Do NOT advance phase.
     - **Retry rate-limit check:**
       - If `attempt_counts[current_phase]` does not exist, initialize it: `{ "remediations": 0, "retries": 0 }`.
       - Increment `attempt_counts[current_phase].retries` by 1. Save state.
       - Compare the **new** value against `rate_limits.max_retry_attempts`.
       - If **at or over the limit** (retries ≥ max): Surface:
         ```
         ⛔ Retry limit reached: {current_phase} has failed {N}/{max} times.

         To continue, choose one of:
           • Raise the limit: edit .workflow/state.json → rate_limits.max_retry_attempts
           • Reset this phase's counter: edit .workflow/state.json → attempt_counts.{current_phase}.retries to 0
           • `skip with warning` — advance without a successful artifact (not recommended)
           • `restart phase <N>` — restart this phase from scratch
         ```
         Halt. Do NOT offer the `retry` option.
       - If **under the limit**: Surface:
         ```
         ⚠️ Verification failed: <artifact path> was not created or is too small (<100 bytes).
         This usually means the SpecKit step did not complete successfully.
         Retry attempt {N}/{max}. Options: "retry" to run again, "skip with warning" to continue anyway.
         ```
         Stop here until user responds.
   - If file exists and is ≥100 bytes: proceed.

3. **Record artifact fingerprint** in `state.json`:
   - Set `current_artifact` to the file path.
   - Compute a SHA-256 hash using PowerShell via the Bash tool:
     ```powershell
     (Get-FileHash -Algorithm SHA256 "<artifact_path>").Hash
     ```
   - Set `current_artifact_sha` to the returned hex string.
   - **Reset retry counter on success:** Set `attempt_counts[current_phase].retries = 0` if the counter exists. Save state.
   - Clear `phase_checkpoint: null`. Save state.

4. **Only then** proceed to the gate prompt or next phase.

---

### Post-Execution Self-Check (MANDATORY — before every gate and phase advance)

Before displaying a gate prompt or advancing `current_phase`, internally verify all of:

- ☐ Expected artifact file exists and is ≥100 bytes (verified in Post-SpecKit Verification above)
- ☐ `state.json` has been written with updated `current_phase`, `status`, `progress`, `current_artifact`, and `current_artifact_sha`
- ☐ `phase_checkpoint` has been cleared to `null`
- ☐ `audit.md` has a new timestamped entry for this phase completion
- ☐ If the next step is a gate: artifact content has been Read and is ready to display

If **any item is not checked**: do NOT show the gate or advance. Fix the blocking issue first, or surface it as a `failed` state to the user.

---

### AFTER executing any phase:
1. Save updated `state.json` immediately (with `current_artifact_sha` and `phase_checkpoint: null`).
2. Append completion event to `audit.md`.
3. Run Post-Execution Self-Check.
4. Show updated status assertion header + status line.
