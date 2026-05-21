# SDLE — Spec Driven Lifecycle Engine (v1)

An autonomous SDLC orchestrator for Claude Code that wraps SpecKit.  
Users interact only with SDLE — SpecKit commands never surface directly.

---

## Quick Start

### 1. Prerequisites

Install SpecKit with skills mode in your **target project** (not this folder):

```powershell
# In your target project directory:
uvx --from git+https://github.com/github/spec-kit.git specify init . --skills --here
```

### 2. Install This Skill

Copy (or symlink) this skill into your target project's local skills:

```powershell
# Option A: copy
xcopy /E /I ".claude\skills\sdle" "<your-project>\.claude\skills\sdle"

# Option B: or install globally
xcopy /E /I ".claude\skills\sdle" "%USERPROFILE%\.claude\skills\sdle"
```

### 3. Add Requirements

In your target project, create `requirements/` and add your requirements:

```
your-project/
└── requirements/
    ├── feature.md        # What to build
    └── constraints.md    # Tech stack, limits (optional)
```

### 4. Start the Workflow

Open Claude Code in your target project and say:

```
start workflow
```

SDLE will handle everything from there.

---

## 16-Phase Workflow

```
Phase  1  Requirements Check          — Validates requirements/ folder
Phase  2  Generate Constitution        — SpecKit: constitution
Phase  3  ★ GATE 1: Constitution       — Await your approval
Phase  4  Generate Specification       — SpecKit: specify
Phase  5  ★ GATE 2: Specification      — Await your approval
Phase  6  Generate Plan                — SpecKit: plan
Phase  7  ★ GATE 3: Plan               — Await your approval
Phase  8  Generate Checklist           — SpecKit: checklist
Phase  9  Generate Tasks               — SpecKit: tasks
Phase 10  Analyze                      — SpecKit: analyze
Phase 11  ★ GATE 4: Analysis           — Await your approval
Phase 12  Implement                    — SpecKit: implement
Phase 13  ★ GATE 5: Implementation     — Await your approval
Phase 14  Generate Design              — SDLE-native: app & DB design docs
Phase 15  ★ GATE 6: Design             — Await your approval
Phase 16  Security Review              — Auto-generated review file
```

**6 approval gates total.** Phases 8–10 run automatically (no gate between them).

---

## Commands

| Command | Effect |
|---|---|
| `start workflow` / `begin` | Start or resume the workflow |
| `approve` | Approve the current gate and advance |
| `approve with comments: <text>` | Approve and record your notes |
| `reject with comments: <text>` | Reject and trigger remediation |
| `status` / `show state` | Show current phase, progress, approvals |
| `resume` / `continue` | Resume from current phase |
| `restart phase <N>` | Reset to phase N (1–16) |
| `retry` | Retry a failed SpecKit step |
| `skip with warning` | Skip a failed step (not recommended) |

---

## SpecKit Skill Mapping

| SDLE Phase | SpecKit Skill Invoked |
|---|---|
| Constitution | `speckit-constitution` |
| Specification | `speckit-specify` |
| Plan | `speckit-plan` |
| Checklist | `speckit-checklist` |
| Tasks | `speckit-tasks` |
| Analyze | `speckit-analyze` |
| Implement | `speckit-implement` |
| Design Generation | *(SDLE-native, no SpecKit call)* |
| Security Review | *(SDLE-native, no SpecKit call)* |

These skill names are installed by `specify init . --skills --here`.

---

## File Layout

### In this repo (skill source):
```
.claude/skills/sdle/
├── SKILL.md                  ← Orchestrator entry point (always loaded)
├── modules/
│   ├── phase-execution.md    ← Phase logic (loaded when executing a phase)
│   ├── gate-protocol.md      ← Gate + rejection logic (loaded at gate phases)
│   └── security-review.md   ← Security review template (loaded at Phase 16)
└── templates/
    └── state.json            ← Initial state template
```

### In your target project (runtime state):
```
<target-project>/
├── requirements/             ← Your input (required)
├── .specify/                 ← SpecKit's artifacts
│   ├── memory/constitution.md
│   └── specs/<id>/
│       ├── spec.md
│       ├── plan.md
│       ├── tasks.md
│       └── ...
├── design/
│   ├── app/app-design.md         (context, components, sequence diagrams, decisions)
│   └── db/db-design.md           (ERD, data dictionary, decisions — if applicable)
├── clarifications/
│   └── <gate-phase>-YYYY-MM-DD-HHMM.clarify  ← User comments at each gate
├── reviews/
│   └── security-review-YYYY-MM-DD-HHMM.md
└── .workflow/
    ├── state.json            ← SDLE orchestration state
    └── audit.md              ← Append-only event log
```

---

## Example Interaction Flow

```
User: start workflow

SDLE: 📋 SDLE Status: Phase 1/16 — Requirements Check [IN PROGRESS]

      I found requirements/:
        • requirements/feature.md (2.1 KB)

      Requirements look good. I'll now generate the project constitution.
      Shall I proceed?

──────────────────────────────────────────────────────

User: yes

SDLE: 📋 SDLE Status: Phase 2/16 — Generate Constitution [IN PROGRESS]

      Generating constitution...
      [Invokes speckit-constitution internally]

      Constitution generated at .specify/memory/constitution.md.

      ─────────────────────────────────
      ✋ APPROVAL REQUIRED — Gate 1/6: Constitution
      Artifact: .specify/memory/constitution.md

      • `approve` — Accept and advance
      • `approve with comments: ...` — Accept with notes
      • `reject with comments: ...` — Reject for revision
      ─────────────────────────────────

──────────────────────────────────────────────────────

User: approve with comments: Add a section on API versioning constraints

SDLE: 📋 SDLE Status: Phase 4/16 — Generate Specification [IN PROGRESS]

      Gate 1 approved. Comments recorded.
      Moving to Phase 4: Generate Specification.

      Generating specification...
      [Invokes speckit-specify internally]

      ─────────────────────────────────
      ✋ APPROVAL REQUIRED — Gate 2/6: Specification
      ...

──────────────────────────────────────────────────────

User: reject with comments: The user stories are too vague — add acceptance criteria

SDLE: 📋 SDLE Status: Phase 4/16 — Generate Specification [REJECTED — REMEDIATION NEEDED]

      Understood — I've recorded your feedback:
      "The user stories are too vague — add acceptance criteria"

      I will re-run the Specification step with this feedback.
      Say "continue" to re-run, or add more context first.

──────────────────────────────────────────────────────

User: continue

SDLE: 📋 SDLE Status: Phase 4/16 — Generate Specification [IN PROGRESS]

      Re-generating specification with your feedback...
      [Re-invokes speckit-specify with rejection comments as context]
      ...

──────────────────────────────────────────────────────

User: status

SDLE: 📋 SDLE Status: Phase 7/16 — Gate 3: Plan [AWAITING APPROVAL]

      Approvals so far:
        ✅ Gate 1 (Constitution) — Approved
        ✅ Gate 2 (Specification) — Approved with comments
        ⏳ Gate 3 (Plan) — Awaiting your decision
        ○  Gate 4 (Analysis) — Not yet reached
        ○  Gate 5 (Implementation) — Not yet reached
        ○  Gate 6 (Design) — Not yet reached

      Last updated: 2026-05-11T14:32:00Z
```

---

## State Schema Reference

`.workflow/state.json`:

| Field | Type | Description |
|---|---|---|
| `workflow_version` | string | Schema version (`"1.0"`) |
| `project_name` | string\|null | Inferred from requirements |
| `current_phase` | string | Phase ID (e.g., `gate_plan`) |
| `status` | string | `pending \| in_progress \| awaiting_approval \| completed \| rejected` |
| `progress` | string | `"N/16"` |
| `last_updated` | string | ISO-8601 timestamp |
| `current_artifact` | string\|null | Path to most recently generated artifact |
| `speckit_initialized` | boolean | Whether `.specify/` exists |
| `approvals` | object | One key per gate, null until decided |
| `phase_history` | array | Ordered list of completed phases with outcomes |

Each `approvals.<gate>` entry:
```json
{
  "decision": "approved | rejected",
  "comments": "text or null",
  "timestamp": "ISO-8601"
}
```

---

## Extending SDLE

**Add a new phase:** Insert a new row in SKILL.md's Phase Execution Map, assign a progress number, and update the FSM dispatch table.

**Add a new gate:** Add a `gate_<name>` phase between two execution phases. Register it in `state.json`'s `approvals` object.

**Add a new document type:** Create a new step after `security_review` that reads `.specify/` artifacts and writes a new file under `./reviews/` or `./docs/`.

**Override SpecKit behavior:** Add an `args` payload when invoking a SpecKit skill to pass additional context (e.g., tech stack constraints from the constitution).

---

## v1.7 — Clarification Tracking

SDLE v1.7 saves all user-provided gate comments as timestamped `.clarify` files in a `clarifications/` folder in the target project.

- **When written:** Any `approve with comments:` (if comments are non-empty) or `reject with comments:` at a gate.
- **Naming convention:** `clarifications/<gate-phase>-YYYY-MM-DD-HHMM.clarify` — e.g. `clarifications/gate_spec-2026-05-21-1430.clarify`
- **Content:** Phase ID, gate label, decision (approved/rejected), timestamp, and the comment text.
- **Purpose:** Provides a human-readable audit trail of every piece of reviewer feedback across all gates, independent of `state.json` and the SpecKit feedback mechanism.

No state schema changes. v1.6 state files are auto-migrated on first load (version string bumped to `"1.7"`, no data loss).

---

## v1.6 — Verbose Mode

SDLE v1.6 suppresses internal operational details from the console by default. Users see only workflow-level output.

**What is always shown:**
- Status header, phase announcements, phase completion summaries
- Gate prompts (full artifact content + approval form)
- Error / halt messages
- Proposed next actions

**What is hidden by default (shown only in verbose mode):**
- Module file reads, SpecKit skill names and args, SHA-256 computation, artifact byte counts, state.json field updates, audit.md appends, guidance file injection details, clarify invocations, feature-ID resolution, version migration steps

**Enabling verbose mode:**

```
start workflow --verbose
```

or toggle at any point:

```
verbose on
verbose off
```

The `verbose` setting persists in `.workflow/state.json` for the duration of the workflow.

State schema update: `verbose: false` field added. v1.5 state files are auto-migrated on first load.

---

## v1.5 — Rate Limiting

SDLE v1.5 adds configurable caps on all SpecKit re-invocation loops to prevent quota exhaustion:

- **Remediation loop** (`reject with comments` → `continue`): capped at `rate_limits.max_remediation_attempts` per phase (default: 3).
- **Retry loop** (`retry` on failed artifact verification): capped at `rate_limits.max_retry_attempts` per phase (default: 3).

When a limit is hit the orchestrator halts with a clear message and options to raise the limit, reset the counter, restart the phase, or skip.

**To change the defaults**, edit `.workflow/state.json` in your target project:
```json
"rate_limits": {
  "max_remediation_attempts": 5,
  "max_retry_attempts": 5
}
```

**To reset a specific counter** (e.g., after fixing the root cause):
```json
"attempt_counts": {
  "spec_draft": { "remediations": 0, "retries": 0 }
}
```

State schema update: `rate_limits` and `attempt_counts` fields added. v1.4 state files are auto-migrated on first load.

---

## v1.4 — Design Generation Phase

SDLE v1.4 adds a new SDLE-native phase between Implementation and Security Review:

- **Phase 14 — `design_generation`**: Generates two design documents from the spec, plan, and constitution:
  - `design/app/app-design.md` — context diagram, component diagram, detail-level design, sequence diagrams, important design decisions.
  - `design/db/db-design.md` — ERD, data dictionary, design decisions (generated only if the feature involves persistent data storage; skipped otherwise).
- **Phase 15 — `gate_design` (Gate 6)**: Approval gate for the generated design documents.
- Security Review moves to **Phase 16**.

Optional guidance file: `guidance/design.md` — shapes the structure, emphasis, and level of detail for both design documents.

State schema update: `approvals.gate_design` field added. v1.3 state files are auto-migrated on first load (no data loss).

---

## v1.3 — Modular Architecture

SDLE v1.3 splits the single 725-line SKILL.md into four files with lazy-loading:

- **SKILL.md** (~450 lines, always loaded): CORE RULES, workflow table, Internal Constants, Steps 1–4, Step 9 state schema, Step 10 errors, routing pointers.
- **modules/phase-execution.md** (108 lines): Phase Execution Map for all 8 active phases, Post-SpecKit Verification, Post-Execution Self-Check. Read by the orchestrator when entering any execution phase.
- **modules/gate-protocol.md** (83 lines): Approval Gate Protocol (Steps 6 + 7 combined), rejection & remediation flow. Read when `current_phase` ∈ GATE_PHASES or on approve/reject commands.
- **modules/security-review.md** (89 lines): Evidence-gathering procedure and review-file template for Phase 16 only. Read exclusively at `security_review`.

No behavior changes from v1.2. The state schema is unchanged; v1.2 state files are auto-migrated (version string bumped to `"1.3"` on first load).

---

## Hardening Notes (v1.1)

SDLE v1.1 adds 8 robustness fixes over the original happy-path-only v1. Here is what changed and what to expect:

### State Assertion Header
Every response begins with a machine-parseable comment:
```
<!-- SDLE_STATE phase=<id> status=<status> progress=<N/16> -->
📋 SDLE Status: Phase N/16 — Label [STATUS]
```
If Claude's stated phase disagrees with what you know, say "your phase is wrong" — it will re-read `state.json` from disk and reconcile.



### SpecKit Skill Name Discovery
On first run, SDLE probes `.claude\skills\` (local) and `%USERPROFILE%\.claude\skills\` (global) to find the actual installed prefix (`speckit-` vs `speckit.`). The resolved prefix is stored in `state.json → speckit_skill_prefix`. No hardcoded assumptions.

### Artifact Verification
After every SpecKit phase, SDLE reads the output artifact and confirms it exists and is ≥100 bytes. If verification fails, the workflow freezes (`status: failed`) and offers retry. A lightweight fingerprint (`byte_count:first_80_chars`) is stored in `state.json → current_artifact_sha`.

### Gate Content Display
At every approval gate, the full artifact content is inlined in the conversation (head+tail for long files). You never need to open `.specify/` manually to know what you're approving.

### Rejection Feedback File
When you reject at a gate, your comments are written to `.specify/sdle-feedback.md`. When regeneration runs, SpecKit is explicitly instructed to incorporate that file. After successful re-generation, the feedback is archived to `.specify/sdle-feedback-archive-<timestamp>.md`.

### Honest Security Review
The Phase 16 security review:
- Runs `git diff --stat` and `git diff HEAD~1` to capture real implementation changes.
- Maps your detected tech stack to OWASP Top 10 relevance.
- Lists specific tool commands to run (`npm audit`, `bandit`, `semgrep`, etc.).
- Flags only patterns **actually observed in the diff** (not hallucinated findings).
- Explicitly lists what it does NOT cover.
- Includes a mandatory disclaimer: "AI-assisted, not a substitute for SAST/DAST."

### Recovery Consistency Check
On every load, SDLE validates `current_phase` against `phase_history`. If state has jumped more than 2 phases ahead or regressed behind the last confirmed history entry, it halts and asks you to confirm before proceeding.

### Post-Execution Self-Check
Before presenting any gate, SDLE internally verifies: artifact exists, `state.json` updated, `audit.md` updated, artifact content ready to display. Any failure blocks the gate until resolved.
