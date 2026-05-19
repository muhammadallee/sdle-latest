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

### BEFORE executing any phase:
1. Update `state.json`: set `status` to `in_progress`.
2. Append to `.workflow/audit.md`: `[<ISO timestamp>] Phase <N> (<phase_id>) started.`
3. Tell the user what you are about to do.
4. **Guidance injection:** Look up the current phase in the Guidance File Map above. If the file exists: Read it. You will append its content to the SpecKit `args` in the next step (see per-phase blocks below). If the file does not exist: skip silently.

### Phase Execution Map:

**Phase 2 — `constitution_draft`:**
- Invoke `speckit-constitution` using the Skill tool. If `guidance/constitution.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/constitution.md>\n---\nAlign your output with this guidance."`
- Record artifact: `.specify/memory/constitution.md` in state.
- After completion: update state to `gate_constitution` / `awaiting_approval`.
- Append audit: "Constitution generated."
- Present the gate prompt (read `modules/gate-protocol.md`).

**Phase 4 — `spec_draft`:**
- Invoke `speckit-specify` using the Skill tool. If `guidance/spec.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/spec.md>\n---\nAlign your output with this guidance."`
- **Feature-ID Resolution (MANDATORY after spec runs):** Glob `.specify/specs/*/` to list all subdirectories. The feature directory is the one created most recently (by modification time). Store its name as `current_feature_id` in `state.json`. If zero directories exist: set `status` to `failed` and surface an error. If multiple directories exist and none is clearly newer: list them and ask the user to confirm which one is the current feature.
- Record artifact: `.specify/specs/{state.current_feature_id}/spec.md`.
- After completion: update state to `gate_spec` / `awaiting_approval`.
- Append audit: `"Specification generated. Feature ID: {current_feature_id}."`
- Present the gate prompt.

**Phase 6 — `plan_draft`:**
- Invoke `speckit-plan` using the Skill tool. If `guidance/plan.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/plan.md>\n---\nAlign your output with this guidance."`
- Record artifact: `.specify/specs/{state.current_feature_id}/plan.md`.
- After completion: update state to `gate_plan` / `awaiting_approval`.
- Append audit: "Plan generated."
- Present the gate prompt.

**Phase 8 — `checklist_draft`:**
- Invoke `speckit-checklist` using the Skill tool. If `guidance/checklist.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/checklist.md>\n---\nAlign your output with this guidance."`
- No gate after this phase — advance automatically to tasks_draft.
- Record artifact: `.specify/specs/{state.current_feature_id}/checklist.md` (if created).
- Append audit: "Checklist generated."
- Immediately proceed to Phase 9.

**Phase 9 — `tasks_draft`:**
- Invoke `speckit-tasks` using the Skill tool. If `guidance/tasks.md` was read in step 4 above, append to args: `"\n\nUser guidance for this phase:\n---\n<content of guidance/tasks.md>\n---\nAlign your output with this guidance."`
- No gate after this phase — advance automatically to analyze.
- Record artifact: `.specify/specs/{state.current_feature_id}/tasks.md`.
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

**Phase 14 — `security_review`:**
- Do NOT invoke SpecKit. Read `modules/security-review.md` and follow its procedure to generate `reviews/security-review-<timestamp>.md`.
- After the review file is written: update state to `complete` / `completed`, append audit: "Security review complete. Workflow finished.", and congratulate the user.

### Post-SpecKit Verification (MANDATORY — after every SpecKit skill invocation)

After invoking ANY `speckit-*` skill, execute these steps before advancing:

1. **Read the expected artifact file** (the path listed in each phase block above).
2. **Check size:**
   - If file does not exist OR content is fewer than 100 bytes:
     - Set `state.json` `status` to `"failed"`.
     - Save state. Do NOT advance phase.
     - Surface to user:
       ```
       ⚠️ Verification failed: <artifact path> was not created or is too small (<100 bytes).
       This usually means the SpecKit step did not complete successfully.
       Options: "retry" to run again, "skip with warning" to continue anyway.
       ```
     - Stop here until user responds.
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
