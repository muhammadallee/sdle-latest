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

## 14-Phase Workflow

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
Phase 14  Security Review              — Auto-generated review file
```

**5 approval gates total.** Phases 8–10 run automatically (no gate between them).

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
| `restart phase <N>` | Reset to phase N (1–14) |
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
| Security Review | *(SDLE-native, no SpecKit call)* |

These skill names are installed by `specify init . --skills --here`.

---

## File Layout

### In this repo (skill source):
```
.claude/skills/sdle/
├── SKILL.md                  ← Main orchestrator (entry point)
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

SDLE: 📋 SDLE Status: Phase 1/14 — Requirements Check [IN PROGRESS]

      I found requirements/:
        • requirements/feature.md (2.1 KB)

      Requirements look good. I'll now generate the project constitution.
      Shall I proceed?

──────────────────────────────────────────────────────

User: yes

SDLE: 📋 SDLE Status: Phase 2/14 — Generate Constitution [IN PROGRESS]

      Generating constitution...
      [Invokes speckit-constitution internally]

      Constitution generated at .specify/memory/constitution.md.

      ─────────────────────────────────
      ✋ APPROVAL REQUIRED — Gate 1/5: Constitution
      Artifact: .specify/memory/constitution.md

      • `approve` — Accept and advance
      • `approve with comments: ...` — Accept with notes
      • `reject with comments: ...` — Reject for revision
      ─────────────────────────────────

──────────────────────────────────────────────────────

User: approve with comments: Add a section on API versioning constraints

SDLE: 📋 SDLE Status: Phase 4/14 — Generate Specification [IN PROGRESS]

      Gate 1 approved. Comments recorded.
      Moving to Phase 4: Generate Specification.

      Generating specification...
      [Invokes speckit-specify internally]

      ─────────────────────────────────
      ✋ APPROVAL REQUIRED — Gate 2/5: Specification
      ...

──────────────────────────────────────────────────────

User: reject with comments: The user stories are too vague — add acceptance criteria

SDLE: 📋 SDLE Status: Phase 4/14 — Generate Specification [REJECTED — REMEDIATION NEEDED]

      Understood — I've recorded your feedback:
      "The user stories are too vague — add acceptance criteria"

      I will re-run the Specification step with this feedback.
      Say "continue" to re-run, or add more context first.

──────────────────────────────────────────────────────

User: continue

SDLE: 📋 SDLE Status: Phase 4/14 — Generate Specification [IN PROGRESS]

      Re-generating specification with your feedback...
      [Re-invokes speckit-specify with rejection comments as context]
      ...

──────────────────────────────────────────────────────

User: status

SDLE: 📋 SDLE Status: Phase 7/14 — Gate 3: Plan [AWAITING APPROVAL]

      Approvals so far:
        ✅ Gate 1 (Constitution) — Approved
        ✅ Gate 2 (Specification) — Approved with comments
        ⏳ Gate 3 (Plan) — Awaiting your decision
        ○  Gate 4 (Analysis) — Not yet reached
        ○  Gate 5 (Implementation) — Not yet reached

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
| `progress` | string | `"N/14"` |
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

## Hardening Notes (v1.1)

SDLE v1.1 adds 8 robustness fixes over the original happy-path-only v1. Here is what changed and what to expect:

### State Assertion Header
Every response begins with a machine-parseable comment:
```
<!-- SDLE_STATE phase=<id> status=<status> progress=<N/14> -->
📋 SDLE Status: Phase N/14 — Label [STATUS]
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
The Phase 14 security review:
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
