# SDLE — Spec Driven Lifecycle Engine (v1.12)

An autonomous, gated SDLC orchestrator for Claude Code that wraps SpecKit.
Users interact only with SDLE — SpecKit commands never surface directly.

**18 phases · 8 approval gates · full state/audit trail.**

> For the full design rationale, a detailed walkthrough of every phase, glossary, flow diagrams, and an end-to-end example run, see **[docs/SDLE-Reference-Guide.md](docs/SDLE-Reference-Guide.md)** — the canonical enterprise reference for SDLE. This README is a quick-start and lookup reference only.
>
> For simulated conversation transcripts of every notable scenario (happy path, rejections, drift, guardrail trips, recovery), see **[docs/dry-runs/](docs/dry-runs/README.md)**.

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

## 18-Phase Workflow

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
Phase 10  ★ GATE 4: Tasks              — Await your approval (checklist shown alongside)
Phase 11  Analyze                      — SpecKit: analyze (refines tasks.md)
Phase 12  ★ GATE 5: Analysis           — Await your approval
Phase 13  Generate Design              — SDLE-native: app & DB design docs
Phase 14  ★ GATE 6: Design             — Await your approval
Phase 15  Implement                    — SpecKit: implement
Phase 16  ★ GATE 7: Implementation     — Await your approval
Phase 17  Security Review              — SDLE-native: evidence-based review file
Phase 18  ★ GATE 8: Security Review    — Await your approval → workflow complete
```

**8 approval gates total.** Phases 8–9 run automatically (checklist then tasks, no gate between them) and are reviewed together at Gate 4. Design (Phase 13) deliberately precedes Implementation (Phase 15) so architecture decisions inform the generated code, not the other way around.

For *why* each phase and gate exists in this exact order — and what specifically breaks if it didn't — see [§7 of the Reference Guide](docs/SDLE-Reference-Guide.md#7-the-18-phase-workflow--detailed-reference).

---

## Commands

| Command | Effect |
|---|---|
| `start workflow` / `begin` | Start or resume the workflow. Append `--verbose` to enable verbose mode. |
| `approve` | Approve the current gate and advance. |
| `approve with comments: <text>` | Approve and record your notes. |
| `reject with comments: <text>` | Reject and trigger remediation (rate-limited). |
| `status` / `show state` | Show current phase, progress, approvals, drift state, rate limits. |
| `resume` / `continue` | Resume from current phase; after a rejection, triggers remediation. |
| `retry` | Retry a failed (technical-failure) SpecKit step (rate-limited, separately from remediation). |
| `restart phase <N>` | Roll back to phase N (1–18); clears all downstream approvals. Requires `confirm restart phase <N>`. |
| `reset workflow` | Delete all workflow state (artifacts preserved). Requires `confirm reset`. |
| `accept state` | Acknowledge a detected forward state jump and proceed. |
| `accept content` | Acknowledge flagged instruction-like content in a requirements/guidance/clarification file and proceed treating it as data. |
| `accept audit` | Acknowledge an audit-log integrity mismatch and re-baseline the audit hash. |
| `confirm implement` | Proceed with implementation despite uncommitted working-tree changes (dirty-tree guard). |
| `skip with warning` | Skip a failed step without a verified artifact (not recommended; logged). Requires `confirm skip`. |
| `verbose on` / `verbose off` | Toggle display of internal operational detail. |

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
| Clarify (post-generation, Phases 2/4/6/8/9) | `speckit-clarify` |
| Design Generation | *(SDLE-native, no SpecKit call)* |
| Security Review | *(SDLE-native, no SpecKit call)* |

These skill names are installed by `specify init . --skills --here`. SDLE auto-discovers the installed prefix (`speckit-` vs `speckit.`) on first run — these names are never exposed to the user during normal operation.

---

## File Layout

### In this repo (skill source):
```
.claude/skills/sdle/
├── SKILL.md                  ← Orchestrator entry point (always loaded)
├── modules/
│   ├── phase-execution.md    ← Phase logic (loaded when executing a phase)
│   ├── gate-protocol.md      ← Gate + rejection logic (loaded at gate phases)
│   └── security-review.md    ← Security review template (loaded at Phase 17)
└── templates/
    └── state.json            ← Initial state template
```

### In your target project (runtime state):
```
<target-project>/
├── requirements/              ← Your input (required)
├── guidance/                  ← Optional per-phase steering files (e.g. guidance/plan.md)
├── .specify/                  ← SpecKit's artifacts
│   ├── memory/constitution.md
│   └── specs/<id>/
│       ├── spec.md
│       ├── plan.md
│       ├── checklist.md
│       └── tasks.md
├── design/
│   ├── app/app-design.md          (context, components, sequence diagrams, decisions)
│   └── db/db-design.md            (ERD, data dictionary, decisions — if applicable)
├── clarifications/
│   └── <phase-name>-YYYY-MM-DD-HHmm.clarify   ← persisted user clarification responses
├── reviews/
│   └── security-review-YYYY-MM-DD-HHmm.md
└── .workflow/
    ├── state.json                 ← SDLE orchestration state (canonical source of truth)
    ├── audit.md                   ← Append-only event log (hash-chained via state.json → audit_sha)
    ├── lock                       ← Session lock (concurrent-session detection)
    ├── implementation-manifest.md ← Gate 7 artifact (file list + secrets scan + summary)
    └── completion-summary.json    ← Written on final Gate 8 approval
```

---

## Example Interaction Flow

```
User: start workflow

SDLE: 📋 SDLE Status: Phase 1/18 — Requirements Check [IN PROGRESS]

      I found requirements/:
        • requirements/feature.md (2.1 KB)

      Requirements look good. I'll now generate the project constitution.
      Shall I proceed?

──────────────────────────────────────────────────────

User: yes

SDLE: 📋 SDLE Status: Phase 2/18 — Generate Constitution [IN PROGRESS]

      Generating constitution...
      [Invokes speckit-constitution internally]

      Constitution generated at .specify/memory/constitution.md.

      ─────────────────────────────────
      ✋ APPROVAL REQUIRED — Gate 1/8: Constitution Approval
      Artifact: .specify/memory/constitution.md
      Fingerprint: 9f1c...e02a

      • `approve` — Accept and advance
      • `approve with comments: ...` — Accept with notes
      • `reject with comments: ...` — Reject for revision
      ─────────────────────────────────

──────────────────────────────────────────────────────

User: approve with comments: Add a section on API versioning constraints

SDLE: 📋 SDLE Status: Phase 4/18 — Generate Specification [IN PROGRESS]

      Gate 1 approved. Baseline fingerprint recorded. Comments noted.
      Moving to Phase 4: Generate Specification.

      Generating specification...
      [Invokes speckit-specify internally]

      ─────────────────────────────────
      ✋ APPROVAL REQUIRED — Gate 2/8: Specification Approval
      ...

──────────────────────────────────────────────────────

User: reject with comments: The user stories are too vague — add acceptance criteria

SDLE: 📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [REJECTED — REMEDIATION NEEDED]

      Understood — I've recorded your feedback in state.json:
      "The user stories are too vague — add acceptance criteria"

      Say "continue" to re-run the Specification step with this feedback applied.

──────────────────────────────────────────────────────

User: continue

SDLE: 📋 SDLE Status: Phase 4/18 — Generate Specification [IN PROGRESS]

      Remediation attempt 1/3 for spec_draft.
      Re-generating specification with your feedback...
      [Re-invokes speckit-specify with rejection comments as context]
      ...

──────────────────────────────────────────────────────

User: status

SDLE: ## SDLE Workflow State

      | Field | Value |
      |---|---|
      | Phase | gate_plan (7/18) |
      | Status | awaiting_approval |
      | Last Updated | 2026-06-20T09:14:00Z |

      ### Approvals
      | Gate | Decision |
      |---|---|
      | gate_constitution | approved with comments |
      | gate_spec | approved with comments |
      | gate_plan | pending |
      | gate_tasks | — |
      | gate_analyze | — |
      | gate_design | — |
      | gate_implement | — |
      | gate_security | — |
```

The workflow continues through Checklist/Tasks (Gate 4), Analyze (Gate 5), Design (Gate 6), Implement (Gate 7), and Security Review (Gate 8), at which point `.workflow/completion-summary.json` is written and the workflow is marked complete. See **[Appendix A of the Reference Guide](docs/SDLE-Reference-Guide.md#appendix-a--example-end-to-end-run)** for the full run, including a drift-detection example.

---

## State Schema Reference

`.workflow/state.json` (v1.12) — key fields:

| Field | Type | Description |
|---|---|---|
| `workflow_version` | string | Schema version; auto-migrated forward on load |
| `project_name` | string\|null | Inferred from requirements |
| `current_phase` | string | Phase ID (e.g., `gate_plan`) |
| `status` | string | `pending \| in_progress \| awaiting_approval \| awaiting_reapproval \| completed \| rejected \| failed` |
| `progress` | string | `"N/18"` |
| `last_updated` | string | ISO-8601 timestamp, updated on every write |
| `current_artifact` / `current_artifact_sha` | string\|null | Most recent artifact path and SHA-256 fingerprint |
| `current_feature_id` | string\|null | SpecKit feature directory name, set after Phase 4 |
| `security_review_artifact` | string\|null | Path to the timestamped security review file |
| `approvals` | object | One key per gate: `{ decision, comments, timestamp }` or `null` |
| `artifact_shas` | object | Approval-time SHA-256 baseline per gate — drift-detection baseline |
| `audit_sha` | string\|null | SHA-256 of `.workflow/audit.md`, updated after every append — tamper-evidence baseline |
| `drift_queue` / `pending_phase` | array / string\|null | Re-approval state when artifact drift is detected |
| `rate_limits` / `attempt_counts` | object | Configurable remediation/retry caps and per-phase counters |
| `pending_confirm_action` | string\|null | Tracks a pending `restart`/`reset`/`accept_state_jump` confirmation |
| `phase_history` | array | Ordered list of completed phases with outcomes |

Each `approvals.<gate>` entry:
```json
{
  "decision": "approved | rejected",
  "comments": "text or null",
  "timestamp": "ISO-8601"
}
```

Full field-by-field reference: **[Appendix B of the Reference Guide](docs/SDLE-Reference-Guide.md#appendix-b--state-schema-reference)**.

---

## Extending SDLE

**Add a new phase:** Insert a new row in `SKILL.md`'s Internal Constants (PHASE_SEQUENCE, NEXT_PHASE, PHASE_LABEL_MAP, PROGRESS_MAP) and add a corresponding block to `modules/phase-execution.md`.

**Add a new gate:** Add a `gate_<name>` phase between two execution phases, register it in GATE_PHASES / PHASE_TO_GATE_KEY / ARTIFACT_OWNERSHIP, and in `state.json`'s `approvals` object.

**Add a new document type:** Create a new step after `security_review` that reads `.specify/` artifacts and writes a new file under `./reviews/` or `./docs/`.

**Override SpecKit behavior:** Drop a file in `guidance/` matching the Guidance File Map in `modules/phase-execution.md` — its content is injected into that phase's generation call. No code changes required.

---

## Version History

For full rationale behind each hardening pass, see the Reference Guide. Condensed changelog:

| Version | Summary |
|---|---|
| **v1.12** | 7-item guardrail hardening: untrusted-content (prompt-injection) scan, secrets scan in the implementation manifest, tamper-evident audit log (`audit_sha` hash chain), session lock, dirty-tree guard before implement, repo staleness warning, and two-step `confirm skip`. |
| **v1.11** | 12-gap hardening pass across all skill files (edge cases in drift, rate limiting, and state migration). |
| **v1.10** | 15-gap hardening pass; fixed 3 gate-bypass vulnerabilities (forward-jump and stale-confirmation guards). |
| **v1.9** | 30-gap hardening: expanded to the current 18-phase / 8-gate workflow; idempotency via `phase_checkpoint`. |
| **v1.8** | Added artifact drift detection and re-approval queue (`artifact_shas`, `drift_queue`, `pending_phase`). |
| **v1.7** | Clarification tracking — `speckit-clarify` responses persisted to `clarifications/*.clarify` instead of living only in conversation. |
| **v1.6** | Verbose mode — internal operational detail suppressed by default; toggle with `verbose on` / `verbose off`. |
| **v1.5** | Rate limiting — configurable caps (`rate_limits`) on remediation and retry loops, with per-phase counters. |
| **v1.4** | Added the Design Generation phase (app + DB design docs) and Gate 6, inserted before Implementation. |
| **v1.3** | Split the single SKILL.md into SKILL.md + three lazy-loaded modules (`phase-execution.md`, `gate-protocol.md`, `security-review.md`). |
| **v1.1–1.2** | Initial hardening over the happy-path-only v1: state assertion header, SpecKit skill name auto-discovery, artifact verification, full gate content display, rejection feedback file, evidence-based (not hallucinated) security review, recovery consistency check, post-execution self-check. |

State files are auto-migrated forward on load — a `state.json` written by any prior version will be upgraded in place the next time SDLE runs, with no data loss.
