# SDLE — Spec Driven Lifecycle Engine (v1.14)

An autonomous, gated SDLC orchestrator for Claude Code that wraps SpecKit.
Users interact only with SDLE — SpecKit commands never surface directly.

**18 phases · 8 approval gates · full state/audit trail.**

> For the full design rationale, a detailed walkthrough of every phase, glossary, flow diagrams, and an end-to-end example run, see **[docs/SDLE-Reference-Guide.md](docs/SDLE-Reference-Guide.md)** — the canonical enterprise reference for SDLE. This README is a quick-start and lookup reference only.
>
> For simulated conversation transcripts of every notable scenario (happy path, rejections, drift, guardrail trips, recovery), see **[docs/dry-runs/](docs/dry-runs/README.md)**.

---

## Quick Start

### 1. Prerequisites

**Python 3.11+** must be on PATH. SDLE's guardrails run in `scripts/sdle.py`;
the launcher resolves `py -3`, `python3`, `python`, then falls back to
`uv run --python 3.11` (which SpecKit already requires) before giving up.

Install SpecKit with skills mode in your **target project** (not this folder):

```powershell
# In your target project directory:
uvx --from git+https://github.com/github/spec-kit.git specify init . --skills --here
```

### 2. Install This Skill

SDLE is no longer only a skill folder. The engine (`scripts/`), the commands
(`.claude/commands/`) and the guardrail hooks (`.claude/hooks/` plus their
registration in `.claude/settings.json`) live outside `.claude/skills/sdle/`,
so copying the skill folder alone installs a half-engine.

Copy all four into your target project:

```
.claude/skills/sdle/     the orchestrator prompt files
.claude/commands/        the nine /sdle-* commands
.claude/hooks/           the four guardrail hooks
scripts/                 sdle.py and its launchers
```

Then merge `.claude/settings.json`'s `hooks` block into your project's
settings. Run `scripts/sdle.sh preflight` to confirm the install.

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
Phase  1  Requirements Check       requirements_check   Validates requirements/
Phase  2  Generate Constitution    constitution_draft   SpecKit: constitution
Phase  3  ★ GATE 1: Constitution   gate_constitution    Await your approval
Phase  4  Generate Specification   spec_draft           SpecKit: specify
Phase  5  ★ GATE 2: Specification  gate_spec            Await your approval
Phase  6  Generate Plan            plan_draft           SpecKit: plan
Phase  7  ★ GATE 3: Plan           gate_plan            Await your approval
Phase  8  Generate Checklist       checklist_draft      SpecKit: checklist
Phase  9  Generate Tasks           tasks_draft          SpecKit: tasks
Phase 10  ★ GATE 4: Tasks          gate_tasks           Checklist shown alongside
Phase 11  Analyze                  analyze              SpecKit: analyze
Phase 12  ★ GATE 5: Analysis       gate_analyze         Await your approval
Phase 13  Generate Design          design_generation    SDLE-native: app & DB docs
Phase 14  ★ GATE 6: Design         gate_design          Await your approval
Phase 15  Implement                implement            SpecKit: implement
Phase 16  ★ GATE 7: Implementation gate_implement       Manifest + secrets + tests
Phase 17  Security Review          security_review      SDLE-native: review file
Phase 18  ★ GATE 8: Security       gate_security        Approve -> complete
```

**8 approval gates total.** Phases 8–9 run automatically (checklist then tasks, no gate between them) and are reviewed together at Gate 4. Design (Phase 13) deliberately precedes Implementation (Phase 15) so architecture decisions inform the generated code, not the other way around.

For *why* each phase and gate exists in this exact order — and what specifically breaks if it didn't — see [§7 of the Reference Guide](docs/SDLE-Reference-Guide.md#7-the-18-phase-workflow--detailed-reference).

---

## Commands

Every verb is a slash command; the natural-language phrasing on the left still
routes to the same place.

| Command | Effect |
|---|---|
| `start workflow` / `begin` | Start or resume the workflow. On a new workflow you are asked for a WorkItem name first; say `auto generate` to have one inferred. Append `--verbose` to enable verbose mode. |
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

### WorkItem identity

A **WorkItem** is the durable name for a piece of work. It is created *before*
the workflow is initialised and never changes afterwards. As of v1.14 it is
also the runtime scope: all workflow state lives in
`workitems/<id>/.sdle/`, so independent WorkItems share no state, no audit
ledger and no lock.

```
scripts/sdle.sh workitem create --name "Customer Notification Service"
scripts/sdle.sh workitem list
```

Every runtime command resolves a WorkItem before it runs:

1. an explicit `--workitem <id>`;
2. otherwise the launch directory, when it is inside `workitems/<x>/` — and if
   `<x>` exists on disk but is not in the index, `workitem_unregistered`,
   because binding a neighbour while you stand inside `<x>` would be a silent
   wrong pick;
3. otherwise the sole registered WorkItem;
4. otherwise a still-valid persisted active context
   (`workitem use --workitem <id>` sets it, `--clear` removes it);
5. otherwise a unique Git-branch match;
6. otherwise a legacy repository-global `.workflow/state.json`, if one exists
   and no WorkItem is registered (transitional — see `migrate-workflow`);
7. otherwise `workitem_required`;
8. and when several are plausible and none is named, `workitem_ambiguous`,
   listing the candidates. SDLE never picks one for you.

The project root itself is discovered by walking up from the launch directory
to the nearest ancestor holding `workitems/index.md`, `.workflow/state.json`
or `.git`, so all four launch locations work: `workitems/<id>/`, `workitems/`,
the repository root, and anywhere inside the repository. `--project-root` and
`SDLE_PROJECT_ROOT` still override it.

`workitem resolve` reports what the ladder would do — always exit 0, with the
candidate set and per-candidate evidence when it cannot resolve. It is a
diagnostic, not a resolver: the answer to an ambiguity is a human one.

`validate` checks the registry itself — duplicate ids, an indexed WorkItem with
no directory, a directory with no index row, malformed metadata, a branch
mismatch, misplaced runtime state, and path-traversal or symlink escapes. An
error exits 3, warnings alone exit 0, and it runs even where resolution cannot.

The active WorkItem's execution records the branch and starting SHA it began
on. Running a lifecycle-advancing or content-fingerprinting command from a
different branch refuses `branch_mismatch` once and proceeds on a re-run, which
is logged; everything else warns.

`lint-skill`, `sha`, `constants`, `workitem`, `migrate-workflow` and `validate`
touch no runtime state and need no resolution.

A repository that already has a pre-v1.14 `.workflow/` moves it under a
WorkItem once:

```
scripts/sdle.sh migrate-workflow --workitem customer-notification-service
```

It validates the legacy state, verifies the legacy audit chain, copies the
ledger, manifest, completion summary and migration evidence, writes the target
`state.json` last as the sole commit point, verifies it, and records the
migration on `workitem.json`. `.workflow/` is left byte-for-byte untouched, so
recovery is deleting `workitems/<id>/.sdle/`. `init` refuses while a legacy
`.workflow/state.json` is present.

The name is normalised to kebab-case (`Customer Notification Service` →
`customer-notification-service`): trimmed, lowercased, whitespace and `_`
become `-`, unsupported punctuation is dropped, repeated hyphens collapse, and
the result must be unique. Duplicates are refused — SDLE never invents
`foo-2`. `--auto-generate` mints `WI-<name>-<YYYYMMDDTHHMMSSZ>` instead.

Two files are written, and both are meant to be committed:

```
workitems/
├── index.md                          ← append-only creation registry
└── customer-notification-service/
    └── workitem.json                 ← immutable metadata
```

```json
{
  "id": "customer-notification-service",
  "name": "customer-notification-service",
  "title": "Customer Notification Service",
  "type": "enhancement",
  "synopsis": "Add configurable customer notifications.",
  "createdAt": "2026-08-16T17:05:30Z",
  "createdBy": { "gitUserName": "...", "gitUserEmail": "..." },
  "git": { "initialBranch": "feature/customer-notification-service" },
  "sdleVersion": "1.13"
}
```

`index.md` is append-only and carries no mutable status column. If it is
structurally damaged, `workitem create` and `workitem list` both fail with
`index_malformed` (exit 3) and change nothing — repair it by hand.

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
| Clarify (post-generation, Phase 4 only) | `speckit-clarify` |
| Design Generation | *(SDLE-native, no SpecKit call)* |
| Security Review | *(SDLE-native, no SpecKit call)* |

These skill names are installed by `specify init . --skills --here`. SDLE auto-discovers the installed prefix (`speckit-` vs `speckit.`) on first run — these names are never exposed to the user during normal operation.

---

## File Layout

### In this repo (engine source):
```
scripts/
├── sdle.py                   ← Deterministic core: state machine, gates,
│                               fingerprints, audit chain, drift, locking
├── sdle.sh / sdle.ps1        ← Launchers (resolve Python 3.11+)
└── README.md                 ← Output and exit-code contract
.claude/
├── skills/sdle/
│   ├── SKILL.md              ← Orchestrator entry point (always loaded).
│   │                           Hosts the constant tables sdle.py parses.
│   ├── modules/
│   │   ├── phase-execution.md    ← Phase logic (loaded when executing)
│   │   ├── gate-protocol.md      ← Gate + rejection (loaded at gates)
│   │   └── security-review.md    ← Review template (loaded at Phase 17)
│   └── templates/state.json  ← Initial state template (the only copy)
├── commands/                 ← The nine /sdle-* slash commands
├── hooks/                    ← Four guardrail hooks
└── settings.json             ← Hook registration
tests/                        ← pytest: units, 9 transcript integrations, hooks
```

Run `scripts/sdle.sh lint-skill` after editing any of it — the cross-file sync
rules are checked mechanically rather than by hand.

### In your target project (runtime state):
```
<target-project>/
├── requirements/              ← Your input (required)
├── workitems/                 ← WorkItem identity (versioned, not runtime state)
│   ├── index.md               ← Append-only creation registry
│   └── <workitem-id>/
│       └── workitem.json      ← Immutable WorkItem metadata
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
└── workitems/
    ├── index.md                       ← Append-only WorkItem registry (single source of truth)
    └── <workitem-id>/
        ├── workitem.json              ← Immutable WorkItem identity + migration record
        └── .sdle/                     ← This WorkItem's runtime — nothing here is repository-global
            ├── state.json             ← SDLE orchestration state (canonical source of truth)
            ├── execution.json         ← Execution identity (<3-letter-git-prefix>-<UTC>)
            ├── audit.md               ← Append-only event log (hash-chained via state.json → audit_sha)
            ├── lock                   ← Session lock (concurrent-session detection; the only ignored file)
            ├── evidence/              ← Migration evidence
            ├── implementation-manifest.md ← Gate 7 artifact (file list + secrets scan + summary)
            └── completion-summary.json    ← Written on final Gate 8 approval
```

A pre-v1.14 repository also has a `.workflow/` directory with the same runtime
files. It is transitional: `migrate-workflow --workitem <id>` moves it under a
WorkItem and never mutates it.

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

The workflow continues through Checklist/Tasks (Gate 4), Analyze (Gate 5), Design (Gate 6), Implement (Gate 7), and Security Review (Gate 8), at which point `workitems/<id>/.sdle/completion-summary.json` is written and the workflow is marked complete. See **[Appendix A of the Reference Guide](docs/SDLE-Reference-Guide.md#appendix-a--example-end-to-end-run)** for the full run, including a drift-detection example.

---

## State Schema Reference

`workitems/<workitem-id>/.sdle/state.json` (v1.14) — key fields:

| Field | Type | Description |
|---|---|---|
| `workflow_version` | string | Schema version; auto-migrated forward on load |
| `workitem` | string\|null | The WorkItem this state belongs to; `null` only at the transitional legacy location. Makes a state file self-describing and a misplaced one detectable |
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
| `audit_sha` | string\|null | SHA-256 of the WorkItem's `audit.md`, updated after every append — tamper-evidence baseline |
| `drift_queue` / `pending_phase` | array / string\|null | Re-approval state when artifact drift is detected |
| `rate_limits` / `attempt_counts` | object | Configurable remediation/retry caps and per-phase counters |
| `implementation_base_ref` | string\|null | HEAD SHA pinned when Phase 15 starts; Phase 17 diffs against it |
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

**Add a new phase:** Insert a row in `SKILL.md`'s Internal Constants (PHASE_SEQUENCE, NEXT_PHASE, PHASE_LABEL_MAP, PROGRESS_MAP) and add a block to `modules/phase-execution.md`. Then run `scripts/sdle.sh lint-skill` — it checks every cross-file rule mechanically, so you no longer hand-verify them.

**Add a new gate:** Add a `gate_<name>` phase between two execution phases, register it in GATE_PHASES / PHASE_TO_GATE_KEY / ARTIFACT_OWNERSHIP, and in `state.json`'s `approvals` object.

**Add a new document type:** Create a new step after `security_review` that reads `.specify/` artifacts and writes a new file under `./reviews/` or `./docs/`.

**Override SpecKit behavior:** Drop a file in `guidance/` matching the Guidance File Map in `modules/phase-execution.md` — its content is injected into that phase's generation call. No code changes required.

---

## Version History

For full rationale behind each hardening pass, see the Reference Guide. Condensed changelog:

| Version | Summary |
|---|---|
| **v1.14** | WorkItem-scoped runtime. `state.json`, `audit.md`, `lock`, `execution.json`, the implementation manifest and the completion summary moved from the repository-global `.workflow/` to `workitems/<id>/.sdle/`, so independent WorkItems no longer share state, an audit ledger or a lock. New `workitem` state field, new `--workitem` override, new `migrate-workflow` command that moves a legacy workflow under a WorkItem without ever mutating `.workflow/`, and lightweight execution identity (`<3-letter-git-prefix>-<UTC>`). |
| **v1.13** | Deterministic core. The mechanical layer moved out of prose into `scripts/sdle.py`, which refuses rather than warns: gate crossings, forward jumps, artifact verification, drift, the audit hash chain, locking and rate limits are now enforced by code and covered by 180+ tests in CI on Linux and Windows. Nine slash commands, four guardrail hooks, `lint-skill` for the cross-file sync rules, test evidence and a pinned diff range at Gate 7. SKILL.md 906 -> 268 lines. |
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
