> **SDLE module — loaded on demand.** Assumes Internal Constants (PHASE_SEQUENCE, NEXT_PHASE, PHASE_TO_GATE_KEY, GATE_PHASES, PROGRESS_MAP) are already in context from SKILL.md. Do not duplicate them here.

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
1. Update `state.json`: set `status` to `in_progress`.
2. Append to `.workflow/audit.md`: `[<ISO timestamp>] Phase <N> (<phase_id>) started.`
3. Tell the user what you are about to do.
4. **Guidance injection:** Look up the current phase in the Guidance File Map above. If the file exists: Read it. You will append its content to the SpecKit `args` in the next step (see per-phase blocks below). If the file does not exist: skip silently.

### Phase Execution Map:

**Phase 2 — `constitution_draft`:**
- Invoke `speckit-constitution` using the Skill tool. If `guidance/constitution.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/constitution.md>\n---\nAlign your output with this guidance."`
- Record artifact: `.specify/memory/constitution.md` in state.
- Run Post-SpecKit Verification, then run Post-Generation Clarify.
- After completion: update state to `gate_constitution` / `awaiting_approval`.
- Append audit: "Constitution generated."
- Present the gate prompt (read `modules/gate-protocol.md`).

**Phase 4 — `spec_draft`:**
- Invoke `speckit-specify` using the Skill tool. If `guidance/spec.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/spec.md>\n---\nAlign your output with this guidance."`
- **Feature-ID Resolution (MANDATORY after spec runs):** Glob `.specify/specs/*/` to list all subdirectories. The feature directory is the one created most recently (by modification time). Store its name as `current_feature_id` in `state.json`. If zero directories exist: set `status` to `failed` and surface an error. If multiple directories exist and none is clearly newer: list them and ask the user to confirm which one is the current feature.
- Record artifact: `.specify/specs/{state.current_feature_id}/spec.md`.
- Run Post-SpecKit Verification, then run Post-Generation Clarify.
- After completion: update state to `gate_spec` / `awaiting_approval`.
- Append audit: `"Specification generated. Feature ID: {current_feature_id}."`
- Present the gate prompt.

**Phase 6 — `plan_draft`:**
- Invoke `speckit-plan` using the Skill tool. If `guidance/plan.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/plan.md>\n---\nAlign your output with this guidance."`
- Record artifact: `.specify/specs/{state.current_feature_id}/plan.md`.
- Run Post-SpecKit Verification, then run Post-Generation Clarify.
- After completion: update state to `gate_plan` / `awaiting_approval`.
- Append audit: "Plan generated."
- Present the gate prompt.

**Phase 8 — `checklist_draft`:**
- Invoke `speckit-checklist` using the Skill tool. If `guidance/checklist.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/checklist.md>\n---\nAlign your output with this guidance."`
- No gate after this phase — advance automatically to tasks_draft.
- Record artifact: `.specify/specs/{state.current_feature_id}/checklist.md` (if created).
- Run Post-SpecKit Verification, then run Post-Generation Clarify.
- Append audit: "Checklist generated."
- Immediately proceed to Phase 9.

**Phase 9 — `tasks_draft`:**
- Invoke `speckit-tasks` using the Skill tool. If `guidance/tasks.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/tasks.md>\n---\nAlign your output with this guidance."`
- No gate after this phase — advance automatically to analyze.
- Record artifact: `.specify/specs/{state.current_feature_id}/tasks.md`.
- Run Post-SpecKit Verification, then run Post-Generation Clarify.
- Append audit: "Tasks generated."
- Immediately proceed to Phase 10.

**Phase 10 — `analyze`:**
- Invoke `speckit-analyze` using the Skill tool. If `guidance/analyze.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/analyze.md>\n---\nAlign your output with this guidance."`
- After completion: update state to `gate_analyze` / `awaiting_approval`.
- Append audit: "Analysis complete."
- Present the gate prompt.

**Phase 12 — `implement`:**
- Invoke `speckit-implement` using the Skill tool. If `guidance/implement.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/implement.md>\n---\nAlign your output with this guidance."`
- After completion: update state to `gate_implement` / `awaiting_approval`.
- Append audit: "Implementation complete."
- Present the gate prompt.

**Phase 14 — `design_generation`:**
- Do NOT invoke SpecKit. This is an SDLE-native phase.
- **Guidance:** If `guidance/design.md` was read in step 4 above, use its content to shape the structure, emphasis, and level of detail in both design documents. Apply it as context throughout generation.
- **Step A — App Design (`design/app/app-design.md`):**
  - Create the `design/app/` directory if it does not exist.
  - Read the following for context: `.specify/memory/constitution.md`, `.specify/specs/{state.current_feature_id}/spec.md`, `.specify/specs/{state.current_feature_id}/plan.md` (if they exist).
  - Generate `design/app/app-design.md` containing all of the following sections:
    1. **Context Diagram** — system boundary, external actors, and major external integrations (text-based or Mermaid `C4Context` diagram).
    2. **Component Diagram** — internal components/modules and their relationships (Mermaid `C4Component` or `graph` diagram).
    3. **Detail-Level Design** — per-component narrative: responsibilities, key interfaces, data flows, and technology choices.
    4. **Sequence Diagrams** — at least one Mermaid `sequenceDiagram` per major user-facing flow or integration point.
    5. **Important Design Decisions** — table of significant decisions with rationale, alternatives considered, and trade-offs.
- **Step B — DB Design (`design/db/db-design.md`) — conditional:**
  - Read `design/app/app-design.md` and the spec. If the feature involves persistent data storage (database, data store, or structured persistence):
    - Create the `design/db/` directory if it does not exist.
    - Generate `design/db/db-design.md` containing:
      1. **ERD** — entity-relationship diagram (Mermaid `erDiagram`).
      2. **Data Dictionary** — table with columns: Entity, Attribute, Type, Constraints, Description.
      3. **Design Decisions** — indexing strategy, normalization choices, partitioning, migration notes.
  - If no persistent storage is involved: skip Step B and note "No database design required" in the audit entry.
- Run Post-SpecKit Verification against `design/app/app-design.md` (size ≥ 100 bytes, SHA-256 fingerprint). If `design/db/db-design.md` was also generated, record it as a secondary artifact in audit.
- After completion: update state to `gate_design` / `awaiting_approval`.
- Append audit: "Design generation complete. App design: design/app/app-design.md. DB design: design/db/db-design.md (or 'not applicable')."
- Present the gate prompt (read `modules/gate-protocol.md`).

**Phase 16 — `security_review`:**
- Do NOT invoke SpecKit. Read `modules/security-review.md` and follow its procedure to generate `reviews/security-review-<timestamp>.md`.
- After the review file is written: update state to `complete` / `completed`, append audit: "Security review complete. Workflow finished.", and congratulate the user.

### Post-Generation Clarify (MANDATORY — for constitution, spec, plan, checklist, tasks)

After Post-SpecKit Verification passes for Phases 2, 4, 6, 8, and 9, invoke the clarify skill **before** presenting the gate or advancing to the next phase:

1. Invoke `{speckit_skill_prefix}clarify` using the Skill tool. Pass in args: the current phase name and the path of the verified artifact (e.g. `"Phase: constitution_draft. Artifact: .specify/memory/constitution.md"`).
2. If clarify fails or produces no output: surface a warning but **do not block the workflow** — log to audit and continue to the gate/next phase. Clarify is a best-effort enrichment step, not a hard gate.
3. Append to audit: `[<ISO>] Clarify ran for <phase_id>.`

This step does not apply to `analyze` (Phase 10), `implement` (Phase 12), or `design_generation` (Phase 14) — these are not SpecKit generation phases.

### Post-SpecKit Verification (MANDATORY — after every SpecKit skill invocation)

After invoking ANY `speckit-*` skill, execute these steps before advancing:

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
   - Set `current_artifact_sha` to the returned hex string (e.g., `"A3F2..."`).
   - This is a real content hash — any change to the file changes the hash.

4. **Only then** proceed to the gate prompt or next phase.

### Post-Execution Self-Check (MANDATORY — before every gate and phase advance)

Before displaying a gate prompt or advancing `current_phase`, internally verify all of:

- ☐ Expected artifact file exists and is ≥100 bytes (verified in Post-SpecKit Verification above)
- ☐ `state.json` has been written with updated `current_phase`, `status`, `progress`, `current_artifact`, and `current_artifact_sha`
- ☐ `audit.md` has a new timestamped entry for this phase completion
- ☐ If the next step is a gate: artifact content has been Read and is ready to display

If **any item is not checked**: do NOT show the gate or advance. Fix the blocking issue first, or surface it as a `failed` state to the user.

### AFTER executing any phase:
1. Save updated `state.json` immediately (with `current_artifact_sha`).
2. Append completion event to `audit.md`.
3. Run Post-Execution Self-Check.
4. Show updated status assertion header + status line.
