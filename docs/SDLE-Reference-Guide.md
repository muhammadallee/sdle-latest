# SDLE — Spec Driven Lifecycle Engine
## Enterprise Reference Guide

| Field | Value |
|---|---|
| **Document title** | SDLE Design, Architecture & Phase Reference |
| **Covers software version** | SDLE v1.17 (21-phase registry, five flows, deterministic core, WorkItem-scoped runtime; the GREENFIELD flow is 18 phases and 8 approval gates) |
| **Document version** | 1.5 |
| **Audience** | Engineering leadership, delivery managers, platform/DevEx teams, security & compliance reviewers, individual contributors operating SDLE |
| **Classification** | Internal — Engineering Reference |
| **Status** | Active |
| **Last updated** | 2026-07-06 |

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Purpose & Intention](#2-purpose--intention)
3. [Design Philosophy & Core Principles](#3-design-philosophy--core-principles)
4. [System Architecture](#4-system-architecture)
5. [Glossary of Key Terms](#5-glossary-of-key-terms)
6. [Commonly Misunderstood Terms](#6-commonly-misunderstood-terms)
7. [The 18-Phase Workflow — Detailed Reference](#7-the-18-phase-workflow--detailed-reference)
8. [Flow Diagrams](#8-flow-diagrams)
9. [Approval Gate Mechanics](#9-approval-gate-mechanics)
10. [Rejection, Remediation & Rate Limiting](#10-rejection-remediation--rate-limiting)
11. [Artifact Drift Detection & Re-Approval](#11-artifact-drift-detection--re-approval)
12. [State, Audit Trail & Traceability](#12-state-audit-trail--traceability)
13. [Roles & Responsibilities](#13-roles--responsibilities)
14. [Compliance & Governance Alignment](#14-compliance--governance-alignment)
15. [Risks, Limitations & Non-Goals](#15-risks-limitations--non-goals)
16. [Common Misconceptions — Clarified](#16-common-misconceptions--clarified)
17. [When to Use SDLE (and When Not To)](#17-when-to-use-sdle-and-when-not-to)
18. [Appendix A — Example End-to-End Run](#appendix-a--example-end-to-end-run)
19. [Appendix B — State Schema Reference](#appendix-b--state-schema-reference)
20. [Appendix C — Command Reference](#appendix-c--command-reference)
21. [Document Revision History](#document-revision-history)

---

## 1. Executive Summary

SDLE (**Spec Driven Lifecycle Engine**) is a governed orchestration layer that runs on top of SpecKit inside Claude Code. It turns an AI coding assistant from a tool that *responds to prompts* into a system that *executes a fixed, auditable software delivery lifecycle*: requirements → constitution → specification → plan → checklist/tasks → analysis → design → implementation → security review, with eight mandatory human approval gates along the way.

The problem SDLE solves is not "can an LLM write code" — it is **"can an organization trust, govern, and audit a workflow in which an LLM writes code."** Left unconstrained, an AI assistant will happily skip straight from a one-line prompt to a finished pull request, silently inventing scope, architecture, and security posture as it goes, with no record of what was decided, why, or who agreed to it. SDLE replaces that ad hoc path with a fixed sequence of small, reviewable, written artifacts, each one gated by an explicit human decision before the next is generated.

Every phase exists to make a specific class of error cheap to catch. Every gate exists because at least one prior project — somewhere — shipped a defect that a five-minute review at that exact point would have caught. The phases are not ceremony; they are a deliberately ordered set of checkpoints, each placed where the cost of being wrong is lowest and the cost of skipping it is highest.

This document is the canonical reference for *why* SDLE is built the way it is. It is intended to be read once in full by anyone introducing SDLE into a team's workflow, and consulted thereafter as a lookup reference for individual phases, terms, and behaviors.

---

## 2. Purpose & Intention

### 2.1 The problem SDLE addresses

Generative AI coding tools collapse the distance between an idea and running code to almost nothing. This is the source of their value — and the source of their risk. Without structure, AI-assisted development tends to reproduce the worst-case failure modes of decades-old waterfall *and* decades-old cowboy coding simultaneously:

- **Scope is implicit.** The model infers what to build from a short prompt, and that inference is never written down or agreed to.
- **Architecture is incidental.** Technical decisions are made inline, one file at a time, with no documented rationale and no point at which a human evaluates the approach as a whole before code exists.
- **Review happens too late, or not at all.** By the time a human looks at the output, it is a finished diff — reviewing it means re-deriving requirements, design, and intent from the code itself.
- **There is no audit trail.** When something goes wrong in production, there is no record of what was approved, by whom, when, against what artifact, or what feedback was given during revision.
- **Security is an afterthought.** "Add a security review" typically means asking the same model that wrote the code to also grade its own homework, with no evidence trail and no acknowledgement of what the review does *not* cover.

### 2.2 The intention behind SDLE

SDLE's intention is to make the *process* — not just the *output* — of AI-assisted software delivery something an enterprise can stand behind. Concretely, it aims to:

1. **Force explicit, written intermediate artifacts** (constitution, spec, plan, tasks, design, manifest, security review) at every stage where a decision is made, so that decisions are inspectable instead of implicit.
2. **Require a human decision at every high-leverage juncture**, with no path for the AI to advance the workflow on its own authority.
3. **Make every decision traceable**: who decided, what they decided, when, against which exact version (SHA-256 fingerprint) of which artifact.
4. **Catch errors as early and as cheaply as possible** — a wrong assumption in a constitution costs a paragraph edit; the same assumption discovered after implementation costs a rewrite.
5. **Be honest about what it does and does not guarantee** — most visibly in the security review phase, which is explicitly labeled AI-assisted and explicitly lists what it does not cover.
6. **Survive interruption** — sessions end, context windows fill, machines restart. SDLE re-derives the full truth of where it is from a single state file on every turn, rather than depending on conversation memory.

SDLE does not make the underlying model smarter. It makes the *process around* the model accountable.

---

## 3. Design Philosophy & Core Principles

These principles are not abstractions — each maps directly to a specific mechanism implemented in the orchestrator.

| Principle | What it means | How it is implemented |
|---|---|---|
| **State-first execution** | The orchestrator's memory of "where we are" is never trusted from conversation context alone. | `workitems/<id>/.sdle/state.json` is read from disk and a status header is emitted at the start of **every** turn, before any other action. |
| **Gate discipline** | No phase may be considered complete, and no phase may begin, without an explicit human decision where one is required. | The dispatcher recognizes only literal `approve` / `reject with comments:` commands; there is no implicit-advance path. |
| **No silent forward progress** | The AI never decides on the user's behalf that "this looks fine, moving on." | Status is frozen (`awaiting_approval`, `in_progress`, `failed`) until a human acts. |
| **Fail-safe, not fail-open** | When something is ambiguous, broken, or unverifiable, the system halts and asks — it does not guess and continue. | Tool failures, missing artifacts, and unreadable state all freeze status rather than advancing it. |
| **Abstraction boundary (SpecKit opacity)** | The underlying generation engine (SpecKit) is an implementation detail, not a user-facing concept. | Internal skill names and slash-command syntax are never surfaced to the user. |
| **Idempotency under interruption** | Re-running after a crash should not duplicate work or corrupt state. | `phase_checkpoint` records a sub-step marker before any generation call; on resume, SDLE checks whether the expected artifact already exists before re-invoking generation. |
| **Tamper-evidence, not just trust** | An approval is bound to the *exact bytes* of the artifact at approval time, not to "whatever is in that file now." | SHA-256 fingerprints are recorded at approval (`artifact_shas`) and re-computed before every phase to detect drift. |
| **Cost-of-change minimization** | Defects should be caught at the cheapest point to fix them. | Phase ordering deliberately front-loads cheap-to-edit documents (constitution → spec → plan) before expensive-to-edit code (implement), with design documents inserted *before* implementation specifically to keep architecture changes cheap. |
| **Bounded automation** | Automated retry/remediation loops must terminate, not run indefinitely against the same root cause. | `rate_limits.max_remediation_attempts` and `rate_limits.max_retry_attempts` cap automatic re-invocation per phase. |
| **Complete, attributable audit trail** | Every meaningful event is written to an append-only ledger with actor, action, artifact, and outcome. | `workitems/<id>/.sdle/audit.md` — one entry per gate decision, phase completion, rejection, drift event, and rate-limit trip. |

---

## 4. System Architecture

### 4.1 Components

```
SDLE Orchestrator (Claude Code Skill)
│
├── SKILL.md                         Always-loaded entry point
│     • Core rules, the phase registry and FLOW_PHASES, internal constants (single source of truth)
│     • State inspection, command dispatcher, state-file schema & migrations
│
├── modules/phase-execution.md       Loaded when executing any non-gate phase
│     • Per-phase generation logic, guidance injection, drift check,
│       idempotency recovery, post-generation verification
│
├── modules/gate-protocol.md         Loaded at any gate phase or on approve/reject
│     • Gate prompt rendering, approval recording, rejection & remediation flow
│
├── modules/design-review.md         Loaded at design generation and its gate
│     • How the design review is conducted, finding shape, how the parent
│       records the outcome
│
├── modules/code-review.md           Loaded at implementation and its gate
│     • How the code review is conducted, finding shape, how the parent
│       records the outcome
│
├── modules/security-review.md       Loaded only at Phase 17 (security_review)
│     • Evidence-gathering procedure and review template
│
│     Which of these a phase requires is CAPABILITY_MAP in SKILL.md, parsed by
│     the engine and reported by `sdle.sh resume`. The row is a floor, not a
│     ceiling: a capability file may point at another one.
│
├── .claude/agents/sdle-*            Four read-only product subagents
│     • Discovery, design review, code review, security review
│     • Grant is Read/Grep/Glob and a PreToolUse fence denies every write and
│       every command; they return findings and record nothing. The parent
│       records, with `artifact review --actor-type agent --actor-name <agent>`
│     • What SDLE enforces here, what the Claude Code runtime enforces, and
│       what is convention only: ADR-007 §3
│
└── SpecKit (external, wrapped)
      • speckit-constitution / -specify / -plan / -checklist / -tasks
      • speckit-analyze / -implement / -clarify
      • Invoked via the Skill tool; never exposed to the user by name
```

### 4.2 Runtime artifacts (in the target project)

| Path | Produced by | Purpose |
|---|---|---|
| `requirements/` | User | Ground-truth input; the only thing SDLE never generates |
| `.specify/memory/constitution.md` | Phase 2 | Project ground rules and constraints |
| `workitems/<id>/specs/<feature-id>/spec.md` | Phase 4 | Functional specification |
| `workitems/<id>/specs/<feature-id>/plan.md` | Phase 6 | Technical implementation plan |
| `workitems/<id>/specs/<feature-id>/checklist.md` | Phase 8 | Independent completeness checklist |
| `workitems/<id>/specs/<feature-id>/tasks.md` | Phase 9 (refined Phase 11) | Granular task breakdown |
| `design/app/app-design.md` | Phase 13 | Architecture & sequence diagrams, design decisions |
| `design/db/db-design.md` | Phase 13 (conditional) | ERD, data dictionary, data design decisions |
| `workitems/<id>/.sdle/implementation-manifest.md` | Phase 15 | Reviewable summary of all files changed by implementation, including a mandatory secrets-scan section |
| `reviews/security-review-<timestamp>.md` | Phase 17 | Evidence-based security review |
| `workitems/<id>/.sdle/state.json` | Orchestrator | Canonical workflow state (the single source of truth) |
| `workitems/<id>/.sdle/audit.md` | Orchestrator | Append-only event ledger, hash-chained via `state.json → audit_sha` |
| `workitems/<id>/.sdle/lock` | Orchestrator | Session lock (timestamp + session token) for concurrent-session detection |
| `workitems/<id>/.sdle/completion-summary.json` | Gate 8 approval | Final, signed closure record |
| `workitems/<id>/.sdle/execution.json` | `init`, `migrate-workflow` | Execution identity (`<3-letter-git-prefix>-<UTC>-<8 hex>`), start instant, and the `git` object recording the branch, starting SHA and worktree this run began on |
| `workitems/<id>/.sdle/evidence/migration-*.json` | `migrate-workflow` | Legacy state/audit SHAs and Git HEAD captured at migration |
| `workitems/index.md`, `workitems/<id>/workitem.json` | `workitem create` | Append-only registry and immutable WorkItem identity |
| `workitems/.active-context.json` | `init`, `migrate-workflow`, `workitem use` | Developer-local active WorkItem for this working directory. Gitignored, disposable, and never written by resolution itself |
| `clarifications/*.clarify` | User (via clarify loop) | Persisted answers to the spec-phase SpecKit `clarify` questions, or free-text context from the Phase 11 analyze prompt |
| `guidance/*.md` | User (optional) | Per-phase steering content, read if present |

### WorkItem identity

A **WorkItem** is the durable name for a piece of work. It is created *before*
the workflow is initialised, and it never changes afterwards. Since v1.14 it is
also the **runtime scope**: all workflow state lives under
`workitems/<id>/.sdle/`, `state.json` records which WorkItem it belongs to, and
independent WorkItems share no state, no audit ledger and no lock. Every phase
and gate behaves exactly as it did before WorkItems existed.

Two id shapes are accepted:

| How it was created | Shape | Example |
|---|---|---|
| From a user-supplied name (default) | normalised kebab-case | `customer-notification-service` |
| `--auto-generate` | `WI-<name>-<YYYYMMDDTHHMMSSZ>` | `WI-payment-retry-20260816T170530Z` |

Normalisation is deterministic: trim, lowercase, whitespace and `_` become `-`,
unsupported punctuation is dropped, repeated hyphens collapse, leading and
trailing hyphens are stripped, and only `[a-z0-9-]` survives. An empty result
is refused, as is a name that carries a path separator or a pipe, one that
normalises to more than 64 characters, and one that lands on a Windows
reserved device name. Uniqueness is enforced case-insensitively against both
the registry and the directory listing; a duplicate is refused rather than
suffixed, and the caller is asked to resume the existing WorkItem or supply
another name.

Each WorkItem gets `workitems/<id>/workitem.json` — id, name, human title,
type, synopsis, creation instant, the Git identity and branch captured at
creation, and the SDLE version. Missing Git is recorded as `null`, never
refused. Every creation also appends one row to `workitems/index.md`, an
append-only registry with no mutable status column. The registry's structure is
validated before each append; if it is damaged, `workitem create` and
`workitem list` both fail as an integrity error and change nothing, because a
corrupt ledger is repaired deliberately, not silently rewritten.

Both files are intended to be committed. They are the durable creation record,
which is why WorkItem creation does not append to `workitems/<id>/.sdle/audit.md` — the
audit ledger belongs to a workflow, and a WorkItem exists before one does.

### WorkItem resolution and the legacy runtime

Every command that touches runtime state resolves a WorkItem first, in this
order: an explicit `--workitem <id>`, which must be registered; otherwise the
launch directory, when it sits inside `workitems/<x>/`; otherwise the sole
registered WorkItem; otherwise a still-valid persisted active context;
otherwise a unique Git-branch match. **There is no sixth rung.** With
none registered the command refuses `workitem_required` — and when a
repository-global `.workflow/state.json` is also on disk, that refusal names
the two-step recovery (`workitem create`, then `migrate-workflow --workitem
<id>`) in that order; with several plausible
and none named it refuses `workitem_ambiguous` and lists the candidates. SDLE
never picks one. `lint-skill`, `sha`, `constants`, `workitem`,
`migrate-workflow` and `validate` touch no runtime state and need no
resolution.

The launch rung refuses rather than falls through: inside `workitems/<x>/`
where `<x>` is a real directory that the index does not know, the command
refuses `workitem_unregistered`. Binding some *other* WorkItem while the
developer stands inside `<x>` would be exactly the silent wrong pick the
ambiguity rule forbids. Rungs four and five are only reachable with two or more
WorkItems registered, so a single-WorkItem repository never pays for a Git
subprocess.

The project root is discovered rather than assumed: the engine walks up from
the launch directory to the nearest ancestor holding `workitems/index.md`,
`.workflow/state.json` or `.git`, testing those markers in that order at each
level, and falls back to the launch directory itself when nothing matches.
`--project-root` and `SDLE_PROJECT_ROOT` still win outright. That is what makes
all four supported launch locations — `workitems/<id>/`, `workitems/`, the
repository root, and anywhere inside it — resolve the same repository.

The **persisted active context** is `workitems/.active-context.json`: a
developer-local, gitignored file recording `workitem`, the branch it was set
on, when, and by which command. Only `init`, `migrate-workflow` and
`workitem use` ever write it. It is skipped, never fatal, when it is
unreadable, names an unregistered WorkItem, points at a missing directory, or
was set on a different branch — a stale context can never brick a repository,
and `workitem use --clear` restores plain registry-based resolution. It is
deliberately never written by resolution itself, which is what lets the
`PreToolUse` dirty-tree hook run the ladder speculatively without becoming a
second writer.

`workitem resolve` runs the same ladder in a reporting posture: it always exits
0 and returns `resolved`, `rung`, `reason`, the launch directory, the project
root, the current branch and a `candidates` list carrying per-candidate
evidence (`cwd`, `context`, `context:stale`, `branch:<name>`, `runtime`). It is
the only input the orchestrator gets for the ask-the-user rung. The engine
never infers and never returns an inferred answer; the user's choice re-enters
as an explicit `--workitem <id>`.

Up to v1.16 a sixth rung bound a pre-v1.14 repository-global `.workflow/`
runtime directly, so such a repository stayed readable long enough to be
migrated. **v1.17 deleted that rung** — and deleted it rather than replacing it
with an inference: with zero WorkItems the ladder answers `none` whether or not
legacy state exists, so it still never guesses. `.workflow/` is now a migration
source and a project-root marker, and nothing else.

Nothing is stranded by the removal. `workitem create` and `migrate-workflow`
are both runtime-free, so neither reaches the ladder, and every other command
refuses `workitem_required` with a message naming those two steps in order.
`init` refuses `legacy_workflow_present` while a repository-global
`.workflow/state.json` exists, regardless of how many WorkItems are registered,
because creating a second runtime beside it would leave the legacy workflow
simultaneously unbindable and unmigratable.

`migrate-workflow --workitem <id>` moves it, in an order chosen so that an
interruption is always recoverable. It requires an already-registered
WorkItem; refuses `target_exists` if that WorkItem already has a runtime;
validates the legacy `state.json`; verifies the legacy audit chain and
`audit_sha`, refusing `legacy_audit_broken` rather than carrying a break into
the WorkItem; captures the legacy SHAs and the current Git HEAD as evidence;
copies the ledger, manifest, completion summary, `evidence/migration-*.json`
and `execution.json`; re-verifies the copied ledger at its new location;
migrates the state in memory; appends a `workflow_migrated` entry to the
**target** ledger; and only then writes the target `state.json` — the sole
commit marker. A final re-read verifies phase, status, progress, approvals,
artifact SHAs, rate limits, attempt counts, `implementation_base_ref` and
`phase_history`, and rolls the commit marker back on mismatch. The migration is
recorded on `workitem.json`. `.workflow/` is never written to, renamed or
deleted, so recovery is simply deleting `workitems/<id>/.sdle/`.

### Execution identity

Each `init` and each migration stamps `workitems/<id>/.sdle/execution.json`
with an execution id of the form
`<3-letter-git-user-prefix>-<UTC datetime>-<8 hex>`, for example
`muh-20260816T171501Z-1a2b3c4d`. The prefix is `git config user.name`,
lowercased with non-alphanumeric characters removed, truncated to three
characters, falling back to the email local part and finally to `usr`. It is
execution and audit metadata: nothing resolves a WorkItem from it, and it is
never the WorkItem name.

The trailing eight hex digits are random. The timestamp has one-second
resolution, and an id is also a key: it names every evidence file
(`governance-<id>.json`, `review-<id>-<n>.json`, `discovery-<id>.json`,
`migration-<id>.json`) and de-duplicates the governance ledger entry. Without
the suffix, two executions in the same second shared both, so the second
overwrote the first one's evidence and never reached the ledger. Each evidence
file is also claimed with an exclusive create before it is written, so an
existing evidence file is never replaced; if no unused id can be found, the
command refuses `execution_id_collision` (exit 3) and records nothing. Ids
written before the suffix existed are read unchanged, because nothing parses
an id. See ADR-009.

The same file carries a `git` object — the branch, the starting SHA and the
worktree path the run began on. Missing Git and a detached HEAD are never a
refusal; they simply record `null`. This lives on the execution record rather
than in `state.json` because it describes *this run*, not the workflow, so it
needs no schema version and no migration row.

### Branch and worktree rules

One active WorkItem per developer branch or worktree; different WorkItems may
run concurrently; two developers are not expected to drive the same WorkItem in
parallel. There is no distributed locking and no cross-worktree coordination —
the session lock is per-WorkItem, and two `git worktree`s of one repository
each keep their own runtime, their own ledger, their own lock and their own
active context.

A **branch mismatch** is a non-null recorded branch that differs from the
current one while Git is available. A missing Git, a detached HEAD, a null
recorded branch, or no `execution.json` at all is not a mismatch. Read-only and
advisory commands warn: `header` adds a `branch_mismatch` object to its `data`
and one stderr line, and its `rendered` string is unchanged. The commands that
advance the lifecycle or fingerprint working-tree content refuse
`branch_mismatch` (exit 1) and record `branch_mismatch_guard` in the ledger;
re-running the same command accepts the risk, records
`branch_mismatch_accepted`, and proceeds. Commands that already carry their own
two-step confirmation therefore need two acknowledgements on a mismatched
branch — the branch first, then their own.

### `validate`

`sdle validate` needs no resolved WorkItem, because the repositories it exists
to diagnose are the ones where resolution refuses; it resolves speculatively
and turns a refusal into a finding. It reports duplicate WorkItem ids, an
indexed WorkItem with no directory, a directory with no index row, malformed
metadata, a branch mismatch, runtime state outside the WorkItem it names
(including a surviving legacy `.workflow/state.json`), and path-traversal or
symlink escapes. Each finding carries `check`, `severity`, `workitem`, `detail`
and `path`. One or more `error` findings exit **3**; warnings alone, or a clean
registry, exit **0**. A structurally corrupt `workitems/index.md` still surfaces
as `index_malformed`, which is the same exit code and the correct diagnosis.
SDLE never repairs the registry.

### Repository configuration boundary

Not every fact SDLE needs belongs to a WorkItem. How a repository configures
SDLE, what policies it applies and what templates its teams share are
repository-wide, and giving them no home would mean writing them into whichever
WorkItem happened to be active. A repository-level `.sdle/` owns them.

The two directories share a name and own nothing in common:

| Repository `.sdle/` — derived from the project root | WorkItem `.sdle/` — derived from the bound WorkItem |
|---|---|
| `config.json` — global configuration (`configVersion`, `policyFormat`) | `state.json` — lifecycle state |
| `policies/` — policy definitions | `execution.json` — execution identity |
| `templates/` — shared templates | `audit.md` — append-only ledger |
| `baseline.json` — the repository baseline; written once, at the final gate of a `GREENFIELD` or `BROWNFIELD_DISCOVERY` WorkItem | `lock` — session lock |
| `implementation-state/` — reserved for implementation-transition metadata | `evidence/`, `implementation-manifest.md`, `completion-summary.json` |

The split is a **derivation, not a path prefix test**: the repository members
reference the project root and never the bound WorkItem, so rebinding moves
every runtime path and none of the configuration paths. `sdle validate` polices
it in both directions — `lifecycle_state_in_repository_config` when a runtime
member appears under the repository boundary, and `repository_config_in_workitem`
when a configuration member appears under a WorkItem, including a WorkItem that
has never been initialised.

`sdle config init` creates the boundary and never overwrites; `sdle config show`
reports the effective configuration and creates nothing. Both are runtime-free:
repository configuration that could only be read once a WorkItem resolved would
not be repository configuration. `config.json` is validated by a single
predicate shared by `config show` and `validate`, so the two can never disagree;
a malformed file, an unsupported `configVersion`, or a `policyFormat` other than
`json` is refused as `config_malformed`.

Nothing in any lifecycle flow reads this file. `configVersion` is a separate
namespace from `workflow_version`: it is not workflow state and has no migration
chain. The reasoning behind the boundary and the JSON policy-format decision is
recorded in `docs/architecture/ADR-002-repository-configuration-boundary.md`.

### 4.2.1 The repository baseline

`baseline.json` is the one member of this boundary the lifecycle writes. It is
written at exactly one place — the final gate approval of a WorkItem whose flow
is `GREENFIELD` or `BROWNFIELD_DISCOVERY` — and by nothing else. There is
deliberately no `baseline establish` command: a second writer would let the
model manufacture the fact that authorises `ITERATIVE`.

It records what the contract asks a baseline to record: its own version, the
WorkItem and execution that produced it, the commit it was taken at, references
to the constitution, to the design documents and to any decision records
discovery found, the non-negotiable constraints discovery identified, whether
discovery was performed at all, when it was established, and what it superseded.
Every reference is a **path and a SHA-256 — a pointer and a fingerprint, never a
copy.** The findings themselves have exactly one home, in the WorkItem that
produced them.

The write **cannot refuse**. It runs after the human's approval is already in
the append-only ledger, where a refusal could not be undone, so an absent
constitution or design document is recorded as absent rather than raised.
Whether the result is sound is decided *afterwards*, by one predicate shared by
`baseline show`, `baseline validate` and `sdle validate`, so those three can
never disagree about one repository:

| Status | Meaning |
|---|---|
| `ABSENT` | No baseline. Not a defect — most repositories have none, and no finding is emitted. |
| `VALID` | No findings. |
| `STALE` | A referenced file exists but has changed since the baseline was taken. **A warning, never a refusal.** |
| `INVALID` | Malformed or incomplete, or its producing WorkItem is not in the registry, or a referenced file is gone. This is what the contract calls material baseline invalidation. |

The `STALE`/`INVALID` split is a decision, not an accident. `design_generation`
runs under `ITERATIVE` and rewrites the design document, so if a *changed*
reference invalidated the baseline the third WorkItem in any repository would be
forced back into full rediscovery — which is precisely what the contract says
must not happen by default. A *missing* reference is different in kind: the
baseline's claims can no longer be checked against anything.

Two bindings depend on it, both evaluated at `init` and nowhere else, because
the flow binds once and re-checking mid-run would refuse a WorkItem over a
repository-level fact it cannot fix:

- Binding `BROWNFIELD_DISCOVERY` to a repository whose baseline is sound is
  refused `baseline_present`. Discovery happens once. The message names both
  remedies: re-assess as `ITERATIVE`, or record a rediscovery request in the
  governance assessment, which makes a second full discovery a deliberate,
  audited decision instead of an accident.
- Binding `ITERATIVE` to a repository with no sound baseline is refused
  `baseline_required`. `ITERATIVE` is defined as working from an established
  baseline and performing no rediscovery; without one there is nothing for it
  to work from.

`DEFECT_FIX` and `HOTFIX` are deliberately **not** covered by either rule.
Blocking an emergency hotfix on a repository-level artifact would be a
governance change nobody asked for.

Both refusals are pure readers evaluated before `init` creates anything, so a
refused `init` leaves no runtime directory, no execution file and no audit
entry behind. A corrupt `baseline.json` halts with exit 3 and names the file;
deleting it returns the repository to `ABSENT`, which is a supported state, and
damages no workflow state. The full reasoning is in
`docs/architecture/ADR-005-brownfield-discovery-and-baseline.md`.

### 4.3 Why a state file, not conversation memory

Conversation context is volatile: it can be summarized, truncated, or lost entirely between sessions. SDLE treats `workitems/<id>/.sdle/state.json` as the only authoritative record of workflow position. Every turn re-reads it, re-validates it against `phase_history` (the **Recovery Consistency Check**), and re-derives the status header from it. This means a workflow can be paused for days, resumed in a brand-new conversation, or recovered after a crash mid-phase, and SDLE will behave identically to a continuous session.

---

## 5. Glossary of Key Terms

| Term | Definition |
|---|---|
| **SDLE** | Spec Driven Lifecycle Engine — the orchestrator described in this document. |
| **SpecKit** | The underlying open-source generation toolkit SDLE wraps. Provides the `speckit-*` skills that actually generate constitution/spec/plan/tasks/analysis/implementation content. |
| **Orchestrator** | SDLE itself, in its role as the entity that sequences phases, enforces gates, and maintains state. Distinct from SpecKit, which only generates content when invoked. |
| **Phase** | One of the 21 steps in the phase *registry* (e.g., `spec_draft`, `gate_spec`). Either an *execution phase* (generates or validates something) or a *gate phase* (awaits human approval). A WorkItem executes only the phases its bound flow contains — 18 of them under GREENFIELD. |
| **Gate** | An execution-blocking checkpoint that is passed only by an explicit, recorded decision. Whether that decision must be a human `approve` or `reject with comments:` is policy-driven: a gate the effective policy requires has no third option, and one it does not require may instead be passed by `gate omit`, which records an omission distinct from an approval. Eight gates are registered; how many a WorkItem meets, and what number each carries, is a property of its bound **flow** — 8, numbered 1–8, under GREENFIELD; 3 under `HOTFIX`. A gate a flow does not run is never approved and stays `null` forever. |
| **Flow (engineering flow)** | Which ordered subset of the phase registry a WorkItem traverses: `GREENFIELD`, `BROWNFIELD_DISCOVERY`, `ITERATIVE`, `DEFECT_FIX` or `HOTFIX`. Bound once at `init` from the governance record, stored in `state.flow`, and never re-bound — a record that later proposes a different flow is refused `flow_mismatch`. |
| **Artifact** | Any file generated by a phase that becomes the subject of a gate (constitution.md, spec.md, plan.md, tasks.md, app-design.md, implementation-manifest.md, the security review file). |
| **Constitution** | The Phase 2 artifact establishing the project's foundational principles, constraints, and technical guardrails. Not a legal document — an engineering one. |
| **Specification (Spec)** | The Phase 4 artifact defining *what* is to be built: user stories, scope, acceptance criteria. |
| **Plan** | The Phase 6 artifact defining *how* the spec will be technically realized: architecture, stack, integration approach. |
| **Checklist** | The Phase 8 artifact: an independent completeness check cross-referenced against the plan, displayed alongside tasks at Gate 4 but not itself gated. |
| **Tasks** | The Phase 9 artifact: the granular, ordered work breakdown derived from the plan. Refined again during `analyze` (Phase 11). |
| **Analyze** | Phase 11: an automated cross-consistency pass across constitution, spec, plan, and tasks, run by SpecKit before any code is written. |
| **Design Generation** | Phase 13: an SDLE-native (non-SpecKit) phase producing application and (conditionally) database design documents *before* implementation. |
| **Implementation Manifest** | The Phase 15 artifact: a git-derived list of every file changed during implementation, used as the reviewable surface at Gate 7 instead of asking the reviewer to inspect the whole repository. |
| **Security Review** | The Phase 17 artifact: an evidence-based, git-diff-driven, OWASP-mapped review with an explicit disclaimer and a list of recommended tools. AI-assisted, not a substitute for SAST/DAST or a professional audit. |
| **Completion Summary** | `workitems/<id>/.sdle/completion-summary.json`, written only when Gate 8 is approved. The formal closure record of the workflow. |
| **Artifact Fingerprint (SHA-256)** | A cryptographic hash of an artifact's exact bytes, recorded at the moment of approval. The basis for drift detection. |
| **Drift** | A change to an artifact's on-disk content *after* it was approved, detected by comparing its current SHA-256 against the approval-time SHA-256. Not related to git "drift" or merge conflicts. |
| **Drift Queue** | The ordered list of gate keys awaiting re-approval because their artifacts drifted. Blocks normal phase execution until cleared. |
| **Remediation** | The act of regenerating an artifact after a `reject with comments:` decision, incorporating the recorded feedback. Counted separately from retries. |
| **Retry** | Re-attempting a generation step after a *technical failure* (e.g., the artifact wasn't produced or was too small) — not the same as remediation, which follows a human rejection. |
| **Rate Limit** | A configurable per-phase cap on remediation attempts and retry attempts, preventing infinite loops against an unresolved root cause. |
| **Phase Checkpoint** | A sub-step marker (`phase_checkpoint`) saved before any generation call, enabling crash-recovery without duplicate work. |
| **Guidance File** | An optional, user-authored file in `guidance/` that, if present, is injected into the relevant phase's generation call to steer its output. Absence changes nothing. |
| **Clarification** | A user response to a spec-phase SpecKit `clarify` question, or to the Phase 11 analyze prompt, persisted to `clarifications/` so it survives outside conversation memory. |
| **Audit Trail (`audit.md`)** | The append-only, timestamped, attributed ledger of every meaningful workflow event. |
| **Forward Jump** | An attempt for `current_phase` to be more than 2 phases ahead of the last confirmed history entry — flagged by the Recovery Consistency Check as a possible state inconsistency requiring explicit acknowledgement. |
| **Restart Phase N** | A user command that rolls the workflow *backward* to phase N, clearing all approvals and history from that point forward. The only sanctioned way to undo progress. |
| **Skip With Warning** | An explicit, logged override that advances past a *failed* (not rejected) phase without a verified artifact. Always discouraged, always audited. |
| **Verbose Mode** | A display-only toggle controlling how much internal operational detail (module reads, hash computation, raw SpecKit invocation) is shown. Never changes underlying behavior. |

---

## 6. Commonly Misunderstood Terms

| Term | Common (incorrect) reading | Correct reading |
|---|---|---|
| **"Approval"** | "I reviewed the code." | For Gates 1–6, there is no code yet — you are approving a *document* (constitution, spec, plan, tasks, analysis, design). Only Gate 7 (`gate_implement`) involves reviewing actual code. |
| **"Security Review"** | A professional security audit / penetration test. | An AI-assisted, evidence-based review limited to artifacts and a git diff. It explicitly lists what it does *not* cover and recommends specific tools (SAST, dependency scanners, secret scanners) that must be run separately. |
| **"Constitution"** | A legal, compliance, or HR-style governance document. | An engineering artifact: project principles, technical constraints, and guardrails that bind every later phase's output. |
| **"Gate"** | An optional checkpoint that can be waved through. | A hard block. There is no command that advances past a gate without an `approve`. |
| **"Drift"** | Source control drift, merge conflicts, or branch divergence. | A previously-approved artifact's on-disk content changing after approval (e.g., someone hand-edited `spec.md`). Detected by SHA-256 comparison, unrelated to git. |
| **"Restart phase N"** | "Try this phase again." | A destructive rollback: it clears all approvals, SHA baselines, and history for phase N and everything after it. The correct command for "try this phase again without losing later approvals" does not exist by design — sequencing is intentionally one-directional except for explicit rollback. |
| **"Retry"** | Same thing as rejecting and asking for a redo. | A *retry* follows a technical failure (no artifact produced). A *remediation* follows a human rejection with feedback. They use separate rate-limit counters and separate recovery paths. |
| **"SpecKit opacity"** | The user is simply not told the implementation detail, but could invoke SpecKit directly if they wanted. | By design, SpecKit skill names and slash commands are never exposed and are not meant to be invoked manually mid-workflow — doing so bypasses state tracking, fingerprinting, and the audit trail entirely. |
| **"Checklist"** (Phase 8) | A gate, like the others. | Not gated on its own. It is generated and then displayed *alongside* tasks at Gate 4 (`gate_tasks`) for combined review. |
| **`current_artifact`** | The most important artifact overall. | The most *recently generated* artifact — purely a pointer used for the next gate prompt, reset every phase. |

---

## 7. The 18-Phase Workflow — Detailed Reference

> **Which of these phases actually run depends on the WorkItem's flow.** `PHASE_SEQUENCE` is a *registry* of 21 phases; a **flow** is an ordered subset of it, and a WorkItem traverses exactly one, bound once at `init` from the governance record and never re-bound. The numbered phases below are the **GREENFIELD** flow — the lifecycle a new project traverses, and the one every workflow before v1.16 traversed. The heading keeps its wording so existing links still resolve.
>
> | Flow | Phases | Gates | What it is for |
> |---|---:|---:|---|
> | `GREENFIELD` | 18 | 8 | A new project, from first principles. Frozen in the engine and deliberately not declared in a table, so a new registry phase can never join it silently. |
> | `BROWNFIELD_DISCOVERY` | 19 | 8 | An existing repository with no established baseline: adds `discovery` ahead of the constitution, so the repository is read before anything is drafted. |
> | `ITERATIVE` | 16 | 7 | An existing codebase with an established baseline: the constitution is inherited, not re-drafted. |
> | `DEFECT_FIX` | 14 | 6 | A defect in an existing system: adds `impact_analysis`; drops the checklist, the design phase and its gate. |
> | `HOTFIX` | 10 | 3 | Shorter but never ungoverned — exactly the governance floor plus the impact analysis. |
>
> Every flow keeps a mandatory floor of ten phases, enforced by `lint-skill` **and** by the engine at load time, so "shorter" can never become "ungoverned". Progress fractions, gate numbers and gate labels are all derived from the bound flow, so `gate_implement` reads `Gate 2/3` under `HOTFIX` where it reads `Gate 7/8` under GREENFIELD. `sdle.sh flow show` reports the bound flow; `sdle.sh constants` reports all five. The design, the rejected alternatives and the human decisions behind it are in `docs/architecture/ADR-004-declarative-flow-model.md`.

> Each entry below follows the same structure: **What it does** → **Why it matters** → **Engineering rationale** → **If this phase did not exist.** Gate phases additionally describe what is being approved and why that specific moment is high-leverage.

### Phase 1 — Requirements Check (`requirements_check`)

**What it does:** Validates that a `requirements/` directory exists and contains at least one document; runs the Untrusted Content Scan on each file (flagging instruction-like lines directed at the orchestrator, which require an explicit `accept content` acknowledgement); infers a project name from it.

**Why it matters:** This is the only phase whose input is guaranteed to be human-authored, unmediated by the AI. Every subsequent artifact ultimately traces back to this one.

**Rationale:** An AI assistant without a grounding artifact will infer scope from whatever is in the conversation — including nothing at all. Requiring a written requirements input, checked before any generation begins, anchors the entire downstream chain to something a human actually wrote and can be held accountable to.

**If this phase did not exist:** The constitution and specification would be generated from conversational context alone — context that is informal, easy to lose, and not intended as a durable record. Two different sessions asking "build me X" could produce wildly different, ungrounded specifications with no way to determine which (if either) reflects actual stakeholder intent.

---

### Impact Analysis (`impact_analysis`) — DEFECT_FIX and HOTFIX only

> This phase has **no GREENFIELD position**, which is why it carries no phase number. It sits at registry position 2, immediately after the requirements check, and runs only in the two defect flows.

**What it does:** Reads the requirement and the repository as it stands today — the code paths the defect touches, the tests covering them, the recent history — and writes `reviews/impact-analysis-<YYYY-MM-DD-HHmm>.md`: what is broken, what the change reaches, the blast radius, what could regress, and what must be verified before the fix ships. The document is fingerprinted by `artifact record` and bound to a review by `artifact review`, then displayed in full to the human before the specification gate.

**Why it matters:** A defect fix starts from an existing system, not a blank page. The expensive failures in defect work are the ones nobody looked for: the second caller of the function being changed, the test that silently covered the broken behaviour, the migration that assumed it. Doing that reading *before* the specification is written is what makes the specification narrow and the fix targeted.

**Rationale:** It is deliberately **gateless**. Adding a ninth gate would make every flow's gate numbering conditional and would put a human decision in front of a document whose purpose is to inform the next document, not to authorise work. Gateless is not ungoverned: the artifact clears the size floor, carries a SHA-256 fingerprint, is bound to a recorded review against that exact SHA, and is shown to the human before the first gate downstream of it. And the phase cannot be left without one — `advance` and `skip` both refuse `impact_analysis_missing` until this WorkItem has a recorded analysis carrying a *current* PASS review, exactly as `discovery` refuses `discovery_missing`. Recording alone does not lift the refusal, because a fingerprint is not a judgement; and because the review is bound to one SHA, editing the analysis afterwards makes it stale and the refusal returns, which is why the phase contract says to record the review last.

**If this phase did not exist:** A defect flow would jump straight from a reported symptom to a specification, and the specification would describe the symptom rather than the system. The blast radius would be discovered during implementation, or after it.

---

### Repository Discovery (`discovery`) — BROWNFIELD_DISCOVERY only

> This phase has **no GREENFIELD position**, which is why it carries no phase number. It sits at registry position 2, immediately after the requirements check, and runs only in `BROWNFIELD_DISCOVERY`.

**What it does:** Reads an existing repository — its layout, modules, dependencies, architecture, conventions, interfaces, data stores, test practices, deployment, security posture, recorded decisions, non-negotiable constraints and known debt — and records a structured set of findings through `sdle.sh discovery assess`. Every category the engine declares must carry at least one finding, and **every finding carries a classification**: one of the three values `sdle.sh discovery schema` reports. The engine refuses the record otherwise.

**Why it matters:** Discovery is where a brownfield engagement either becomes trustworthy or becomes fiction. The failure mode is not missing information; it is *confident* information that was never checked — a guess about the persistence layer written in the same voice as a fact read out of a migration file. Classifying every finding is what makes the difference visible to the human reading it.

**Rationale:** The classification is enforced, but only the mechanical half of it can be. The engine guarantees that no finding is unclassified or carries a value outside the closed three; that a finding in the observation class cites a path that actually exists in the repository; that a finding in the inference class names the findings it rests on, and that none of those is itself unknown; that a finding in the unknown class carries no evidence; and that no declared category is silently dropped. What it cannot judge is whether an observation is *true of* the file it cites or whether an inference follows — those remain claims by the author, and SDLE says so rather than implying otherwise. Discovery is deliberately **gateless**, for the same reason `impact_analysis` is: its output informs the next document rather than authorising work. Gateless is not ungoverned — the record is validated, durable, audited, and displayed in full to the human before the constitution gate.

**If this phase did not exist:** A brownfield WorkItem would draft a constitution and a specification for a repository nobody had read, and the resulting artifacts would describe an imagined system. The mismatch would surface during implementation, as rework.

---

### Phase 2 — Generate Constitution (`constitution_draft`)

**What it does:** Invokes SpecKit's constitution generator to produce `.specify/memory/constitution.md`: the project's foundational principles, constraints, and technical guardrails.

**Why it matters:** The constitution is the highest-leverage artifact in the entire workflow. Every later phase — specification, plan, tasks, design, implementation — is generated *with the constitution as binding context*. An error here does not stay local; it propagates into every artifact downstream.

**Rationale:** Without an explicit, written set of ground rules, every phase would improvise its own assumptions about technology choices, coding conventions, and constraints — independently, and not necessarily consistently. The constitution exists to make those assumptions explicit once, at the point where they are cheapest to state and cheapest to correct.

**If this phase did not exist:** The specification might assume one tech stack, the plan another, and the implementation a third — with no single document any reviewer could check decisions against. Inconsistency would only surface once code from different phases collided, at which point it manifests as a bug or an architectural conflict rather than a one-line edit to a markdown file.

---

### Phase 3 — Gate 1: Constitution Approval (`gate_constitution`)

**What is being approved:** The foundational rules that will silently constrain every subsequent artifact.

**Why this is the highest-leverage gate:** Because the constitution feeds every later phase, a flaw caught here costs a paragraph edit. The identical flaw, if it survives to be caught at, say, Gate 6 (design), costs re-deriving the specification, plan, tasks, and design that were built atop the wrong assumption.

**If this gate did not exist:** Foundational errors (wrong tech stack constraint, missing compliance requirement, incorrect scope boundary) would be baked into the project invisibly and discovered, if at all, only when their downstream consequences became visible — typically during or after implementation, where they are the most expensive class of defect to fix.

---

### Phase 4 — Generate Specification (`spec_draft`)

**What it does:** Invokes SpecKit's specification generator to produce a functional specification — user stories, scope boundaries, acceptance criteria — bound to the approved constitution.

**Why it matters:** This is the phase that converts "what we said we wanted" into "what we are precisely committing to build," in a form specific enough to later verify against. It also resolves and records `specKit.featureDirectory` — `workitems/<id>/specs/<feature-id>/`, under which every subsequent SpecKit artifact for this feature is filed. Resolution searches this WorkItem's own `specs/` first, then the repository root's `specs/`, then `.specify/specs/`, and moves what it finds into the WorkItem if it is not already there, so one WorkItem can never be handed another's specification.

**Rationale:** Separating *what* (spec) from *how* (plan, the next phase) prevents technical considerations from quietly narrowing or distorting scope before scope has even been agreed. Acceptance criteria written here become the yardstick used implicitly throughout the rest of the workflow.

**If this phase did not exist:** Architectural and implementation work would begin directly against the constitution and ambient conversation — i.e., against requirements that were never themselves converted into testable, agreed-upon acceptance criteria. Scope would be negotiated implicitly and continuously throughout development rather than fixed once, early, in writing.

---

### Phase 5 — Gate 2: Specification Approval (`gate_spec`)

**What is being approved:** The precise scope and acceptance criteria that the technical plan is about to be built against.

**Why this is high-leverage:** Scope changes discovered *after* a technical plan exists require re-deriving that plan. Scope changes caught here cost a specification edit.

**If this gate did not exist:** A plan, task breakdown, and design could all be generated against scope that was never actually confirmed — discovering a scope problem at, say, Gate 6 would invalidate the plan, checklist, tasks, and analysis built on top of it.

---

### Phase 6 — Generate Plan (`plan_draft`)

**What it does:** Invokes SpecKit's plan generator to produce a technical implementation plan from the approved specification and constitution: architecture, technology choices, integration approach.

**Why it matters:** This is the first phase where genuine technical decisions are made and recorded. It is the layer between "what to build" (spec) and "what specific units of work to do" (tasks) — without it, task generation has no architectural basis to decompose against.

**Rationale:** Technical approach should be reviewed and agreed *as a whole* — module boundaries, technology choices, integration points — before it is broken into granular tasks that are individually too small to reveal a flawed overall approach.

**If this phase did not exist:** Tasks would be generated directly from the specification with no intervening architectural decision layer, meaning the technical approach would be implicit, undocumented, and effectively decided task-by-task rather than reviewed holistically.

---

### Phase 7 — Gate 3: Plan Approval (`gate_plan`)

**What is being approved:** The technical architecture and approach, before it is decomposed into a task list.

**Why this is high-leverage:** This is the last point at which redirecting the *technical* approach is a documentation change rather than a re-implementation. Once tasks (Phase 9) and design (Phase 13) exist atop a given plan, changing the plan invalidates both.

**If this gate did not exist:** A flawed architectural decision (wrong database choice, missing integration consideration, an approach that conflicts with a constitutional constraint) would only be discovered once it had already been decomposed into tasks and possibly implemented — at which point correcting it is a rewrite, not an edit.

---

### Phase 8 — Generate Checklist (`checklist_draft`)

**What it does:** Invokes SpecKit's checklist generator to produce an independent completeness check against the plan. Not gated on its own; flows straight into Phase 9.

**Why it matters:** Task decomposition (the next phase) is a *generative* process — it produces what the model believes is a complete breakdown. The checklist is an *independent verification* artifact, generated with a different prompt and purpose, designed to surface gaps (missing non-functional requirements, untested edge cases, compliance items) that a single generative pass over the same plan might not surface on its own.

**Rationale:** Relying on one generation pass to both produce a task list *and* implicitly self-certify its completeness creates a blind spot — the same reasoning that produced the gap is unlikely to be the reasoning that notices it. An independently generated, cross-referenced checklist provides a second lens.

**If this phase did not exist:** The task breakdown at Gate 4 would have no independent completeness check beside it — a systemic gap (e.g., no task addressing a security constraint from the constitution) would be far easier to miss, with no second artifact to expose the discrepancy.

---

### Phase 9 — Generate Tasks (`tasks_draft`)

**What it does:** Invokes SpecKit's task generator to decompose the approved plan into discrete, ordered, verifiable units of work.

**Why it matters:** `tasks.md` becomes the actual contract for what `implement` (Phase 15) will build. It is also the artifact `analyze` (Phase 11) refines and the baseline `gate_tasks` and `gate_analyze` both reference.

**Rationale:** Implementation needs an explicit, granular, ordered work breakdown rather than an instruction to "build the plan" — granularity is what makes work estimable, parallelizable, and individually verifiable.

**If this phase did not exist:** `speckit-implement` would have to infer its own task structure ad hoc at generation time, with no separately reviewable, granular breakdown for a human to check against the plan before any code is written.

---

### Phase 10 — Gate 4: Tasks Approval (`gate_tasks`)

**What is being approved:** The granular task breakdown — displayed together with the Phase 8 checklist for combined review.

**Why this is high-leverage:** This is the last checkpoint before automated cross-document analysis (Phase 11) and the last *documentation-only* checkpoint before the workflow turns toward code. Reviewing tasks and checklist side by side here is specifically designed to catch coverage gaps before they become missing functionality.

**If this gate did not exist:** An incomplete or incorrectly granular task list could proceed straight to automated analysis and then design/implementation — and a missing task is far more expensive to detect once code already exists for everything *except* what was missed.

---

### Phase 11 — Analyze (`analyze`)

**What it does:** Invokes SpecKit's analysis pass to cross-check constitution, specification, plan, and tasks for mutual consistency, refining `tasks.md` in the process. Also updates the drift baseline so the refined tasks file doesn't trigger a false drift alert at the next gate.

**Why it matters:** Humans reviewing four related documents sequentially, gate by gate, are reviewing each in relative isolation — by the time you approve `gate_tasks`, the constitution approved several gates earlier is not necessarily fresh in mind, let alone being actively cross-checked against the brand-new tasks list. `analyze` is an automated pass purpose-built to catch exactly that class of error: contradictions and gaps that span multiple documents simultaneously.

**Rationale:** This is the final all-artifact consistency checkpoint while everything is still markdown. Everything before this point is cheap to edit; everything after this point (design, code) is comparatively expensive. It is the highest-value place to catch a cross-document inconsistency, because it is also the last place where catching it is still cheap.

**If this phase did not exist:** Latent contradictions between, say, a constraint in the constitution and an assumption baked into the plan would only surface once implementation hit the contradiction directly — at the code level, where diagnosing "which document was wrong" is a debugging exercise rather than a document review.

---

### Phase 12 — Gate 5: Analysis Approval (`gate_analyze`)

**What is being approved:** The findings of the cross-document consistency pass and the resulting refined `tasks.md`.

**Why this is high-leverage:** This is the final gate before the workflow crosses from "documents" into "design and code." Every gate up to this point has been reviewing artifacts that cost minutes to regenerate; every artifact from this point forward (design, implementation) costs materially more effort to redo.

**If this gate did not exist:** Implementation would begin on artifacts that were cross-checked by an automated pass but never confirmed by a human — removing the last low-cost opportunity to halt the workflow before code-level effort is spent.

---

### Phase 13 — Generate Design (`design_generation`)

**What it does:** An SDLE-native phase (no SpecKit call) that generates `design/app/app-design.md` — context diagram, component diagram, detail-level design narrative, sequence diagrams, and a table of significant design decisions with alternatives and trade-offs — and, conditionally, `design/db/db-design.md` (ERD, data dictionary, design decisions) if the feature involves persistent storage.

**Why it matters:** This phase exists specifically to put architecture documentation *before* implementation rather than after — or never. In fast-moving AI-assisted development, architecture documentation is the artifact most commonly skipped entirely, because the code itself appears to make it redundant. It is not redundant: code shows *what was built*, not *why it was built that way*, what alternatives were considered, or what trade-offs were accepted.

**Rationale:** Design is still cheap to revise here — it is diagrams and prose, not code. Placing it immediately before implementation means the documents that inform code generation are reviewed and approved *before* the code exists, rather than being reverse-engineered from the code afterward (if they are ever written at all).

**If this phase did not exist:** Implementation would proceed directly from `tasks.md` with no diagrammatic record of system structure, no documented rationale for architectural choices, and no artifact for future engineers, auditors, or incident responders to consult without reading the entire codebase. This is precisely the gap most legacy systems suffer from — undocumented architecture decisions whose reasoning is lost to time.

---

### Phase 14 — Gate 6: Design Approval (`gate_design`)

**What is being approved:** The application (and, where applicable, database) design — the structural blueprint implementation is about to follow.

**Why this is high-leverage — the practical "point of no return":** This is the last gate before any code is generated. Architecture is still cheap to change here (edit a diagram, rewrite a paragraph); once `implement` (Phase 15) runs, changing architecture means discarding and regenerating actual code.

**If this gate did not exist:** Implementation could begin against a design that was generated but never reviewed — meaning a structural flaw would only be discovered post-implementation, where fixing it means reworking working code rather than revising a document.

---

### Phase 15 — Implement (`implement`)

**What it does:** First runs a **dirty-tree guard**: if the working tree has uncommitted changes (outside SDLE's own artifact directories), the phase halts and requires an explicit `confirm implement` — otherwise the user's own edits would be mixed into, or overwritten by, the generated implementation and misattributed in the manifest. It then invokes SpecKit's implementation generator against `tasks.md`, explicitly informed by the Phase 13 design documents. Afterward, SDLE captures `git status --short` and `git diff --name-only HEAD` (combined and deduplicated, so untracked new files are not missed), runs a **secrets scan** over the changed files (AWS keys, private key material, GitHub/API tokens, hardcoded credential assignments, bearer tokens — findings masked and audited), runs the project's tests — a detected runner (npm, pytest, cargo, maven, gradle), or the command given with `manifest build --test-command "<command>"` for any other — and writes `workitems/<id>/.sdle/implementation-manifest.md`: a complete, reviewable list of every changed or added file, a mandatory `Potential Secrets Detected` section, the `Test Evidence` section, and a summary of what was implemented. Beside it goes a structured evidence record, `evidence/implementation-<execution-id>.json`, which the manifest names on its `Evidence:` line and which carries the manifest's own SHA-256, the pinned implementation base and the test result.

**Why it matters:** This is the only phase that produces the actual deliverable. The implementation manifest exists because asking a reviewer to manually inspect an entire repository for "what changed" does not scale and is error-prone — a single consolidated, generated list is the reviewable surface instead.

**Rationale:** Generating code is necessary but not sufficient; the *change itself* needs to be expressed in a form a human can review without independently re-deriving it from raw git output, and that form needs to be tied back into the same state/audit system as every other phase.

**If this phase did not exist:** There would be no implementation at all — but absent the manifest specifically, a reviewer would have no single, generated, audit-trail-linked source of truth for what files were touched, making it easy to overlook untracked new files or miscount the actual blast radius of the change.

---

### Phase 16 — Gate 7: Implementation Approval (`gate_implement`)

**What is being approved:** The actual generated code, as summarized in the implementation manifest — the first and only gate at which real code, rather than a planning document, is under review. Because the manifest is the gate artifact and is displayed in full, any secrets-scan findings from Phase 15 are necessarily in front of the reviewer at the moment of decision; approving the gate is the explicit acknowledgement of those findings.

**What the engine requires before a human is even asked:** a test run that actually ran and passed. The gate reads the evidence record the manifest names and refuses `tests_not_passed` for any other result — `FAILED`, `skipped by caller`, `no runner detected`, `runner not installed`, a timeout. It refuses `test_evidence_stale` when the record belongs to other content (the manifest was edited after it was built, the base was re-pinned, or it is another WorkItem's), and `test_evidence_missing` or `test_evidence_malformed` when there is no usable record at all. There is no exception path, and a `PASS` review of the manifest does not override the result the manifest reports — the review judges the presentation, the evidence judges the tests.

**Why this is high-leverage:** This is the mandatory human-in-the-loop checkpoint before AI-generated code is treated as a candidate for security review and delivery. It catches functional and quality issues outside the scope of the dedicated security review that follows.

**If this gate did not exist:** AI-generated code would proceed directly to (an explicitly limited) security review and then to completion without a human ever having reviewed the actual implementation — the single riskiest gap an enterprise adoption of AI-assisted coding could have.

---

### Phase 17 — Security Review (`security_review`)

**What it does:** An SDLE-native phase that gathers evidence (constitution, spec, plan, tasks, and a real `git diff` of the implementation), maps the detected tech stack to OWASP Top 10 relevance, flags only patterns *actually observed* in the diff (never invented), recommends concrete tooling (`npm audit`, `bandit`, `semgrep`, `trufflehog`, etc.) tailored to the stack, and explicitly states what the review does not cover. Every review carries a mandatory disclaimer: AI-assisted, not a substitute for SAST/DAST tooling, dependency scanning, or a professional audit.

**Why it matters:** This phase exists to make security consideration a structural, evidence-tied part of the workflow rather than an unstated assumption or a vague "looks fine" sign-off. Equally important is what it refuses to do: it does not claim coverage it cannot provide, and it does not fabricate findings not actually present in the diff.

**Rationale:** A security review that is honest about its limits is more useful — and less dangerous — than one that implies completeness it does not have. By tying findings strictly to the actual diff and explicitly listing recommended follow-up tools, the review functions as a structured starting point for a real security process, not a replacement for one.

**If this phase did not exist:** The workflow would reach "complete" with zero structured security consideration of the generated code — no documented evidence that security was even considered, let alone addressed, and nothing for a compliance or audit process to point to.

---

### Phase 18 — Gate 8: Security Review Approval (`gate_security`)

**What is being approved:** The security review's findings and recommendations — the final gate of the workflow.

**Why this is high-leverage:** Approving this gate writes `workitems/<id>/.sdle/completion-summary.json` and formally marks the workflow `complete`. It is the definitive closure record: all 8 gate decisions, their timestamps, and their artifact fingerprints become part of a single auditable summary.

**If this gate did not exist:** There would be no unambiguous "done" signal and no formal record that security findings were ever reviewed or acknowledged by a human — a significant gap for any organization that needs to demonstrate governance over how AI-assisted changes reach completion.

---

### Terminal state — Complete (`complete`)

No further action occurs. The workflow has produced a full, gated, auditable trail from raw requirements to a reviewed, security-considered implementation, with eight independent human decisions recorded along the way.

---

## 8. Flow Diagrams

### 8.1 Phase & Gate Flow

```mermaid
flowchart TD
    A[1. Requirements Check] --> B[2. Generate Constitution]
    B --> G1{{Gate 1\nConstitution}}
    G1 -- approve --> C[4. Generate Specification]
    G1 -- reject --> B
    C --> G2{{Gate 2\nSpecification}}
    G2 -- approve --> D[6. Generate Plan]
    G2 -- reject --> C
    D --> G3{{Gate 3\nPlan}}
    G3 -- approve --> E[8. Generate Checklist]
    G3 -- reject --> D
    E --> F[9. Generate Tasks]
    F --> G4{{Gate 4\nTasks + Checklist}}
    G4 -- approve --> H[11. Analyze]
    G4 -- reject --> F
    H --> G5{{Gate 5\nAnalysis}}
    G5 -- approve --> I[13. Generate Design]
    G5 -- reject --> H
    I --> G6{{Gate 6\nDesign}}
    G6 -- approve --> J[15. Implement]
    G6 -- reject --> I
    J --> G7{{Gate 7\nImplementation}}
    G7 -- approve --> K[17. Security Review]
    G7 -- reject --> J
    K --> G8{{Gate 8\nSecurity Review}}
    G8 -- approve --> L[Complete]
    G8 -- reject --> K

    classDef gate fill:#fff3cd,stroke:#b8860b,stroke-width:2px;
    classDef phase fill:#eef4ff,stroke:#4169e1,stroke-width:1px;
    classDef done fill:#d4f7dc,stroke:#1d7a3a,stroke-width:2px;
    class G1,G2,G3,G4,G5,G6,G7,G8 gate;
    class A,B,C,D,E,F,H,I,J,K phase;
    class L done;
```

### 8.2 Cost-of-Change Curve (why phase order matters)

```mermaid
graph LR
    subgraph "Cheap to fix — documents only"
    a[Constitution] --> b[Spec] --> c[Plan] --> d[Checklist/Tasks] --> e[Analysis]
    end
    subgraph "Moderate — design, still no code"
    f[Design]
    end
    subgraph "Expensive — real code exists"
    g[Implementation] --> h[Security Review]
    end
    e --> f --> g
```

Each gate sits at the boundary of these zones. The workflow is ordered so that the cheapest-to-fix artifacts are reviewed first and most frequently (5 gates before any design exists, 1 gate before any code exists), and the most expensive-to-fix artifact (code) is reviewed exactly once, immediately, before it can compound into a second expensive artifact (a security finding in shipped code).

### 8.3 Gate Decision Sub-Flow

```mermaid
stateDiagram-v2
    [*] --> awaiting_approval
    awaiting_approval --> approved: approve / approve with comments
    awaiting_approval --> rejected: reject with comments
    rejected --> in_progress: continue (remediation, rate-limited)
    in_progress --> awaiting_approval: artifact regenerated & verified
    approved --> [*]: advance to next phase
    awaiting_approval --> awaiting_reapproval: artifact drift detected\n(applies to upstream gates,\nnot the current one)
    awaiting_reapproval --> approved: re-approve drifted artifact
    awaiting_reapproval --> rejected: reject drifted artifact
```

---

## 9. Approval Gate Mechanics

Every gate follows an identical, non-negotiable sequence — consistency here is itself a control: a reviewer who has seen one gate knows exactly what every other gate will look like.

1. **Full artifact disclosure.** The complete content of the artifact under review is read from disk and displayed in the conversation (head + tail with a truncation marker for documents over ~3,000 words). The reviewer is never required to open a file manually to know what they are approving.
2. **Guidance alignment check.** If the user supplied an optional `guidance/<phase>.md` file, the gate explicitly reports which guidance items the artifact addressed and which it did not — surfacing gaps the reviewer might not otherwise notice.
3. **Explicit decision required.** Three responses are recognized: `approve`, `approve with comments: <text>`, `reject with comments: <text>`. A bare `reject` is rejected back to the user with a prompt to supply comments — feedback-free rejection is not a supported path, because remediation needs something concrete to act on. At a gate the effective policy does not require, `omit` is recognized as a fourth response and is the only way to pass a gate without a decision by a human; at a gate it does require, `gate omit` is refused `gate_required` and no flag changes that.
4. **Fingerprint capture.** On approval, the artifact's current SHA-256 is computed and stored as the drift-detection baseline for that gate.
5. **Immutable record.** The decision, any comments, and a timestamp are written to `state.json → approvals[<gate>]` and appended to `audit.md`. This record is never edited retroactively — a later rejection or remediation creates new entries, it does not rewrite history.

---

## 10. Rejection, Remediation & Rate Limiting

Rejecting a gate is not "ask the AI to try again." It is a structured remediation cycle:

1. The reviewer's feedback is recorded as the canonical source of truth in `state.json`, then mirrored to `.specify/sdle-feedback.md` so the regeneration step can read it directly.
2. A per-phase **remediation counter** is checked against `rate_limits.max_remediation_attempts` (default 3). If the limit is reached, SDLE halts and will not re-invoke generation automatically — the reviewer must explicitly raise the limit, reset the counter, restart the phase from scratch, or accept the current state with `skip with warning` (itself a two-step command: it only executes after a typed `confirm skip`, consistent with restart and reset).
3. The relevant generator (SpecKit skill, or the SDLE-native design/security-review module) is re-invoked with the feedback explicitly embedded in its instructions, both via the feedback file and inline as a fallback.
4. Once the new artifact passes verification, the feedback file is archived (timestamped) rather than deleted outright, and the gate is re-presented with the new content.

A separate, independently tracked **retry counter** governs *technical* failures (an artifact that was never produced, or was produced but too small to be real) — these are not human-judgment rejections and are rate-limited separately so that a flaky generation step does not silently consume the remediation budget meant for substantive feedback.

This dual-counter design exists because the two failure modes have different root causes and different appropriate responses: a technical failure usually means "try again or escalate"; a rejection means "the substance was wrong, and feedback should change the next attempt." Conflating their limits would either let a feedback loop run unbounded (masked as "just retries") or starve a substantive rejection's remediation budget on transient technical failures.

---

## 11. Artifact Drift Detection & Re-Approval

Approved artifacts are ordinary files on disk. Nothing prevents a human from opening `spec.md` and hand-editing it after Gate 2 has already approved it. SDLE's answer to this is **drift detection**: before executing any phase, it recomputes the SHA-256 of every previously-approved artifact and compares it against the hash recorded at approval time.

- **If hashes match:** nothing happens — the approval is still valid.
- **If hashes differ:** the gate is no longer trustworthy. The affected gate(s) are queued (`drift_queue`), the current phase is paused (`pending_phase`), and the reviewer is shown exactly what changed (path, approved SHA, current SHA) and asked to **re-approve or reject** the drifted artifact before the workflow may proceed — sorted so the most upstream drifted gate is handled first, since its consequences cascade furthest.

**Why this matters:** Without it, an approval would mean "I approved whatever this file *was* at one point in time," which is a meaningless guarantee for an auditor. With it, an approval means "I approved exactly this content, and the system will tell me if that ever stops being true." This is the mechanism that makes the audit trail trustworthy even in the presence of manual file edits, merge operations, or any out-of-band modification.

---

## 12. State, Audit Trail & Traceability

### 12.1 `state.json` — the canonical state machine

`state.json` is not a cache or a convenience log — it is the single source of truth for workflow position. It is read first on every turn, migrated forward through schema versions automatically, and validated against `phase_history` for consistency (catching both accidental rollback and unexplained forward jumps). No other source — not conversation history, not the AI's own recollection — is treated as authoritative. On load, two further checks run: the **Audit Integrity Check** (below) and a **repository staleness check** that warns — without halting — when the repo has commits newer than the latest gate approval, i.e. when approvals may reflect a stale view of the codebase.

### 12.2 `audit.md` — the append-only ledger

Every gate decision, phase completion, rejection, remediation, drift event, and rate-limit trip is appended (never edited) to `audit.md` with: a UTC timestamp, the acting identity (resolved from git username/email), the action taken, the artifact involved, its SHA-256 fingerprint, the gate decision (if any), and any comments. This is the record an enterprise audit, post-incident review, or compliance check would consult.

Since v1.12 the ledger is **tamper-evident**: after every append, the SHA-256 of the entire file is recorded in `state.json → audit_sha`, and verified on every load. A mismatch (edit, truncation, deletion, or a write from another session) halts the workflow until the operator explicitly re-baselines with `accept audit` — an action that is itself logged. Note the precise guarantee: tamper-*evident*, not tamper-*proof* — an actor who edits both `audit.md` and `audit_sha` in `state.json` defeats the check. The defense target is accidental or casual modification, not a determined adversary with full filesystem access. Concurrent-session writes, one common source of accidental corruption, are additionally warned about via the `workitems/<id>/.sdle/lock` session lock.

### 12.3 `workitems/<id>/.sdle/completion-summary.json` — the closure record

Written exactly once, when the bound flow's final gate is approved — Gate 8 under GREENFIELD, Gate 3 under `HOTFIX`: workflow version, the **bound flow**, project name, completion timestamp, count of phases completed, the security review artifact path, and whether all of that flow's gates were approved — `false` when one of them was passed by a policy omission instead, which the ledger explains. This is the artifact that answers, unambiguously, "was this delivered through the governed process, and did it pass."

### 12.4 `governance.json`, `reviews.json` and `discovery.json` — the entry, quality and discovery records

Three further WorkItem-scoped records carry the evidence that the work was *admitted* to the lifecycle on stated grounds, that its artifacts were *judged* rather than merely produced, and — for a brownfield WorkItem — that the repository was *read* before anything was drafted from it.

`governance.json` is written by `governance assess` before `init` and holds the requirements-quality result over the structured check set, the WorkItem classification, the observed risk signals, the deterministic score and level, the hard floors that fired, the final level, the recorded uncertainty, and — for the flow the record proposes — which gates would require a human approval and which would be omittable. Severity, weights, thresholds and floors are read from policy, never from the assessing model's input, and a proposed level below the computed one is recorded as an attempt and has no effect. Run `governance policy` to read the effective values. The lifecycle refuses to advance without a record (`governance_missing`), with a blocking quality failure (`governance_blocked`), or when `requirements/` changed after the assessment (`governance_stale`). `classification.flow` is the one value in the record that the lifecycle consumes: `init` binds it to `state.flow` once, and re-assessing later with a different flow is refused `flow_mismatch` at the next `advance`, `gate approve` or `skip` — ahead of the first ledger append, so a refused command leaves `audit.md` byte-identical.

`reviews.json` is an append-only ledger of artifact reviews: path, content fingerprint at review time, review type, result, actor type and name, evidence id and timestamp. Freshness is **derived** — a review applies to the exact content version it was performed against, and nothing stores a "reviewed" boolean. A gate refuses to approve an artifact with no review (`review_missing`), a review of superseded content (`review_stale`), or a failing review of the current content (`review_failed`); drift re-approval is held to the same rule. Each review is linked into `audit.md` as its own entry, so the ledger answers "who judged this content, and which version" as well as "who approved it."

`discovery.json` is written by `discovery assess` during the `discovery` phase and holds the findings that phase produced: one entry per finding, each with its category, its classification, its statement, the paths it cites and the findings it rests on, plus the per-classification counts and the accepted result. It exists only for a WorkItem whose flow runs `discovery`. The phase has no gate of its own, and the record is what replaces one: `advance` and `skip` both refuse `discovery_missing` until this WorkItem has a record the engine accepted, the record is written before that refusal can be lifted and never partially, and the baseline the completing WorkItem establishes points at it by path and SHA-256 rather than copying it. What the engine guarantees about the classifications, and what remains the author's claim, is set out under the `discovery` phase in §7 — the split is deliberate and `discovery schema` reports both halves.

The recorded gate lists are **evidence of what the assessment implied**, not the thing any decision reads. Every decision re-derives the requirement set from the bound flow, the current record and the policy on disk, so a hand-edited record buys nothing.

**Which gates require a human approval is policy-driven; nothing else about a gate is.** Each gate of the bound flow has one of three dispositions, and they are deliberately distinct facts:

| Disposition | Meaning |
|---|---|
| `required` | The bound flow contains this gate and the policy requires a human approval for it. It can be approved or rejected, and nothing else. |
| `omittable` | The bound flow contains it and the policy does not require an approval. It may still be approved — always permitted, always stricter — or passed by `gate omit`. |
| `not_in_flow` | The policy names it but the bound flow has no such phase, so the requirement is inert. Reported rather than silently dropped. |

`gate omit --gate <key>` is the only producer of an omission. It refuses `gate_required` unless the effective policy says the gate is not required, and it takes no `--force`, `--reason` or override flag: an operator-supplied way past that refusal would be an exception mechanism, and there is none. It refuses a missing artifact and an artifact without a current `PASS` review exactly as `gate approve` does, records the artifact's baseline SHA exactly as an approval does, writes a `gate_omitted` audit entry naming the policy source and the final risk level, and advances. The recorded decision is `omitted_by_policy`, never `approved`, so the two remain distinguishable in `state.json`, in `state dump` and in the completion summary — whose `all_gates_approved` is derived and reads `false` when any gate was omitted.

**Two revalidations, because a recorded omission is never trusted.** `advance` re-derives the requirement at the choke point and refuses `gate_omission_invalidated` if the gate is no longer omittable, which closes the hand-edited-state path. The bound flow's final gate re-checks every earlier omission before the workflow can be declared complete, so an omission taken at a low risk level cannot survive a re-assessment that raised it. Both refusals fire ahead of the first ledger append, so a refused command leaves `audit.md` byte-identical.

**The final gate is required at every risk level, in every flow.** That is a positional rule over the bound flow rather than a row in the policy, which matters twice: it names the real reason — it is the terminal human decision on the run, not a claim that security review is universally mandatory — and a repository override cannot remove it, because overrides edit policy dictionaries and this rule is in none of them. Overrides are monotone in the same direction throughout: a repository can always make more gates required, and `HOTFIX` has no omittable gate at any risk level.

Everything else stays universal for every gate, required or not: artifact generation, registration, TP-011 review, the baseline SHA, drift detection, the secrets scan and test evidence at the implementation gate, the audit chain, the retry and remediation caps, and the fail-safe transitions.

---

## 13. Roles & Responsibilities

| Role | Responsibility | Authority |
|---|---|---|
| **Reviewer / Approver** (the human operating SDLE) | Reads each gate's disclosed artifact content; decides `approve`, `approve with comments`, or `reject with comments`; provides substantive feedback on rejection. | Sole authority to advance or block the workflow at every gate the governance policy requires — and that authority cannot be delegated to or assumed by the orchestrator, at any risk level, under any policy. At a gate the policy does not require, the workflow may instead be advanced by a recorded omission rather than by this decision; the reviewer may always approve such a gate anyway, which is the stricter choice. |
| **SDLE Orchestrator** | Sequences phases; enforces gate discipline; maintains `state.json` and `audit.md`; performs drift detection, rate limiting, and recovery checks; renders every gate prompt with full artifact disclosure. | Generates and proposes; never self-approves. Halts on any ambiguity rather than guessing. |
| **SpecKit (generation engine)** | Performs the actual content generation for constitution, spec, plan, checklist, tasks, analysis, implementation, and clarification — when invoked by the orchestrator. | No autonomous role; invoked only by SDLE, never directly by the user during a workflow. |

A useful way to think about the separation: **SpecKit proposes, SDLE governs, the human decides.** No single actor in this chain can unilaterally advance the workflow.

---

## 14. Compliance & Governance Alignment

SDLE was not built against a named compliance framework, but its mechanisms map cleanly onto concepts common to enterprise change-management and audit requirements:

| Governance concept | SDLE mechanism |
|---|---|
| Segregation of generation from approval | Generation (SpecKit, SDLE-native phases) and approval (human gate decisions) are structurally distinct actions, never collapsed into one step. |
| Change traceability | Every artifact change is tied to a phase, a timestamp, an actor, and a SHA-256 fingerprint in `audit.md`. |
| Tamper detection | Drift detection on every previously-approved artifact, every phase. |
| Documented design rationale | Phase 13's "Important Design Decisions" table — alternatives considered and trade-offs accepted, not just the final choice. |
| Evidence-based security sign-off | Phase 17's diff-derived, OWASP-mapped findings with explicit scope limitations, rather than an unsupported "looks secure" assertion. |
| Formal closure record | `workitems/<id>/.sdle/completion-summary.json`, written only on final gate approval. |
| Bounded automated action | Rate-limited remediation/retry loops; no unbounded automated re-attempts against an unresolved root cause. |
| Entry criteria before work begins | A WorkItem cannot advance without a governance record: a requirements-quality result over a structured check set, a classification, and a deterministically scored risk level (§12.4). A blocking quality finding stops progression. |
| Deterministic, non-negotiable risk scoring | Weights, thresholds and hard floors come from policy; the assessing model may propose a level but may never lower the computed one, and the attempt is itself recorded. A repository override may only make governance stricter. |
| Independent artifact review, separate from approval | Every governed artifact carries a review of its exact content — type, result and attributed actor — recorded before, and distinctly from, the human gate decision (§12.4). |

SDLE's audit trail can support a compliance review; it does not, by itself, constitute certification against any specific regulatory framework (SOC 2, ISO 27001, etc.). Treat it as strong supporting evidence within a broader governance program, not as the program itself.

---

## 15. Risks, Limitations & Non-Goals

### 15.1 Known limitations

- **Gates are only as good as the reviewer.** SDLE enforces that a decision is made; it cannot enforce that the decision is well-considered. A reviewer who reflexively approves every gate without reading the disclosed content has all of the process overhead and none of the protective value.
- **The security review is explicitly bounded.** It does not perform dependency CVE scanning, runtime testing, infrastructure review, or business-logic security analysis. It exists to make security a structured checkpoint, not to replace dedicated security tooling or a professional audit.
- **Dependent on SpecKit.** SDLE orchestrates SpecKit; it does not generate constitution/spec/plan/tasks/implementation content itself. SpecKit's generation quality is a ceiling on SDLE's output quality.
- **Dependent on git for two specific artifacts.** The implementation manifest and the security review both rely on `git diff`/`git status` for accuracy. In a repository without git initialized, both degrade to approximate, explicitly-labeled fallbacks.
- **Rate limits can become a blocker, not just a safeguard.** If a root cause is never actually fixed, the remediation/retry limits will eventually halt the workflow rather than loop forever — this is intentional, but it does mean a misconfigured limit (set too low) can interrupt legitimate iterative work.
- **The audit log is tamper-evident, not tamper-proof.** The `audit_sha` hash chain detects edits, truncation, and out-of-band writes, but an actor who modifies both `audit.md` and `state.json` consistently defeats it. True non-repudiation would require signing with a secret SDLE does not hold.
- **Content scans are pattern-based.** The untrusted-content scan and the secrets scan are regex heuristics: they can false-positive on legitimate text (e.g. a requirements document that discusses "approval gates") and false-negative on obfuscated content. Both are deliberately warn-and-acknowledge, never silent-block, for exactly this reason.
- **The session lock is advisory.** Concurrent sessions are detected and warned about via `workitems/<id>/.sdle/lock`; nothing physically prevents two sessions from writing state simultaneously.

### 15.2 Non-goals (what SDLE is not)

- **Not a CI/CD pipeline.** SDLE governs the authoring lifecycle up to a reviewed implementation; it does not build, test, deploy, or release.
- **Not a project management tool.** It tracks phase and gate state for one feature workflow at a time, not backlogs, sprints, or cross-team planning.
- **Not a substitute for QA or penetration testing.** Functional testing and adversarial security testing remain separate, necessary activities after (or alongside) SDLE's gates.
- **Not a coding standards enforcement tool.** The constitution can *state* standards; SDLE does not lint or statically enforce them beyond what SpecKit's generation itself respects.
- **Not a multi-feature/multi-team orchestrator.** Each workflow instance tracks one feature at a time via `specKit.featureId`; separate features belong in separate WorkItems.

---

## 16. Common Misconceptions — Clarified

1. **"SDLE produces secure, production-ready code automatically."**
   No. SDLE produces *reviewed* code — reviewed by a human at Gate 7, and accompanied by an explicitly-scoped, evidence-based security review at Gate 8. Neither step certifies the code as production-secure on its own; both are inputs to a human judgment call, and the security review explicitly names the tools (SAST, dependency scanning, secret scanning) that still need to be run.

2. **"Approving early gates means I reviewed the code."**
   No. For Gates 1 through 6, no code exists yet. You are reviewing documents — a constitution, a specification, a plan, a task list, an analysis, a design. Code first appears at Phase 15, and is first reviewed at Gate 7.

3. **"Rejecting a gate just tells the AI to try again."**
   No. Rejection records specific feedback as canonical state, writes it to a feedback file, and the next regeneration is explicitly instructed to incorporate that feedback. It is a targeted remediation cycle, not a blind retry, and it is rate-limited separately from technical retries.

4. **"I can skip a phase I don't think is necessary."**
   No supported path exists for skipping a phase outright. The closest mechanisms are `restart phase N` (a destructive rollback, not a skip) and `skip with warning` (only valid after a *technical failure*, always logged, and explicitly discouraged). Forward jumps are detected and blocked from silent acceptance.

5. **"Hand-editing an approved file is harmless if the content is still correct."**
   It is not silently accepted either way. Any change to a previously-approved artifact's bytes — correct or not — is detected as drift and forces a re-approval gate before the workflow can proceed. The system has no way to know the edit was "fine" without asking a human to confirm it.

6. **"Verbose mode changes what SDLE actually does."**
   It does not. Verbose mode is purely a display setting controlling how much internal operational detail (module reads, hash computation steps, raw SpecKit invocation strings) is shown. The underlying logic, gating, and verification behavior are identical either way.

7. **"The design phase (Phase 13) is a nice-to-have, cosmetic step."**
   It is a mandatory, gated phase that directly informs the implementation phase that follows it — the implementation invocation explicitly references the design documents. Skipping it (via `skip with warning`, if forced) removes architecture documentation from the workflow entirely, not just a diagram.

8. **"SDLE replaces SpecKit."**
   SDLE wraps and governs SpecKit; it does not replace its generation capability. SpecKit still performs every actual constitution/spec/plan/task/implementation generation — SDLE adds sequencing, gating, fingerprinting, and audit trail around those calls, and deliberately keeps SpecKit's own commands hidden from the user.

9. **"The conversation is the source of truth; state.json is just a backup."**
   It is the reverse. `state.json` is the canonical, authoritative record, re-read from disk at the start of every turn. Conversation history is not trusted as a state source — this is precisely what allows a workflow to be resumed correctly after a context loss, a new session, or a crash.

---

## 17. When to Use SDLE (and When Not To)

**Good fit:**
- Net-new features or services with a defined (even if informal) set of requirements.
- Work where an audit trail of decisions — who approved what, when, against which exact artifact — has organizational or compliance value.
- Teams adopting AI-assisted coding for the first time and wanting structured guardrails rather than open-ended prompting.
- Work where architecture and design documentation is valuable beyond the immediate change (long-lived systems, systems with future maintainers who are not the original authors).

**Poor fit / use a lighter-weight process instead:**
- Emergency hotfixes under time pressure, where eight sequential approval gates are disproportionate to the size and urgency of the change.
- Trivial, low-risk changes (typo fixes, copy edits, config tweaks) with no meaningful design or specification surface.
- Exploratory spikes or throwaway prototypes not intended to reach production — the overhead of a full gated lifecycle defeats the purpose of a quick experiment.
- Multi-feature, cross-team initiatives requiring portfolio-level planning — SDLE tracks one feature workflow at a time and is not a replacement for program/project management tooling.

---

## Appendix A — Example End-to-End Run

> Abridged for readability. Status headers, gate prompts, and audit semantics shown are representative of actual orchestrator output.

```
User: start workflow

SDLE: <!-- SDLE_STATE phase=requirements_check status=in_progress progress=1/18 -->
      📋 SDLE Status: Phase 1/18 — Requirements Check [IN PROGRESS]

      Found requirements/feature.md (2.1 KB). Inferred project name: "Order
      Tracking Service".

      Requirements look good. I'll now generate the project constitution.
      Shall I proceed?

User: yes

SDLE: 📋 SDLE Status: Phase 2/18 — Generate Constitution [IN PROGRESS]
      Generating constitution...

      ─────────────────────────────────
      ✋ APPROVAL REQUIRED — Gate 1/8: Constitution Approval

      [full content of .specify/memory/constitution.md displayed here]

      Artifact path: .specify/memory/constitution.md
      Fingerprint: 9f1c...e02a

        • approve
        • approve with comments: <notes>
        • reject with comments: <feedback>
      ─────────────────────────────────

User: approve

SDLE: 📋 SDLE Status: Phase 4/18 — Generate Specification [IN PROGRESS]
      Gate 1 approved. Baseline fingerprint recorded. Moving to Specification.
      ...

      ✋ APPROVAL REQUIRED — Gate 2/8: Specification Approval
      [spec.md content]

User: reject with comments: Acceptance criteria for the cancellation flow are
      missing. Add explicit criteria covering partial refunds.

SDLE: 📋 SDLE Status: Phase 5/18 — Gate 2: Specification Approval [REJECTED — REMEDIATION NEEDED]

      Understood — I've recorded your feedback:
      "Acceptance criteria for the cancellation flow are missing. Add explicit
      criteria covering partial refunds."

      Say "continue" to re-run the Specification step with this feedback applied.

User: continue

SDLE: 📋 SDLE Status: Phase 4/18 — Generate Specification [IN PROGRESS]
      Remediation attempt 1/3 for spec_draft. Re-generating with your feedback...

      ✋ APPROVAL REQUIRED — Gate 2/8: Specification Approval
      [revised spec.md content, now including partial-refund criteria]

User: approve

SDLE: 📋 SDLE Status: Phase 6/18 — Generate Plan [IN PROGRESS]
      ...

      [Phases 6–12 proceed similarly: Plan → Gate 3 → Checklist → Tasks →
       Gate 4 (tasks + checklist shown together) → Analyze → Gate 5]

User: status

SDLE: ## SDLE Workflow State
      | Field | Value |
      |---|---|
      | Phase | gate_analyze (12/18) |
      | Status | awaiting_approval |
      | Verbose | false |

      ### Approvals
      | Gate | Decision |
      |---|---|
      | gate_constitution | approved |
      | gate_spec | approved with comments |
      | gate_plan | approved |
      | gate_tasks | approved |
      | gate_analyze | pending |
      | gate_design | — |
      | gate_implement | — |
      | gate_security | — |

User: approve

SDLE: 📋 SDLE Status: Phase 13/18 — Generate Design [IN PROGRESS]
      Generating application design (context diagram, component diagram,
      sequence diagrams, design decisions)...
      Persistent storage detected — generating database design as well.

      ✋ APPROVAL REQUIRED — Gate 6/8: Design Approval
      [design/app/app-design.md content, then design/db/db-design.md content]

User: approve

SDLE: 📋 SDLE Status: Phase 15/18 — Implement [IN PROGRESS]
      Generating implementation per tasks.md, informed by design documents...
      Implementation manifest written: workitems/todo-api/.sdle/implementation-manifest.md
      (14 files changed/added)

      ✋ APPROVAL REQUIRED — Gate 7/8: Implementation Approval
      [implementation-manifest.md content: file list + summary]

User: approve

SDLE: 📋 SDLE Status: Phase 17/18 — Security Review [IN PROGRESS]
      Gathering evidence: constitution, spec, plan, tasks, git diff HEAD~1...
      Review written: reviews/security-review-2026-06-20-1430.md

      ✋ APPROVAL REQUIRED — Gate 8/8: Security Review Approval
      [security review content: disclaimer, OWASP relevance table, diff-derived
       findings, recommended tools, explicit scope limitations]

User: approve

SDLE: ✅ Security review approved. Workflow complete!

      All 8 gates passed. Completion summary: workitems/todo-api/.sdle/completion-summary.json
      Security review: reviews/security-review-2026-06-20-1430.md
```

**Illustrative drift scenario** (not part of the run above, shown separately for reference): if a reviewer had hand-edited `plan.md` after Gate 3 was approved, the next phase execution would halt with:

```
⚠️ Artifact drift detected — 1 previously-approved artifact changed since approval:

  • Plan Approval (gate_plan)
    Path:          workitems/checkout-v2/specs/order-tracking/plan.md
    Approved SHA:  6a21...
    Current SHA:   d903...

This artifact must be re-approved before tasks_draft can proceed.
```

---

## Appendix B — State Schema Reference

`workitems/<id>/.sdle/state.json` (v1.15):

| Field | Type | Description |
|---|---|---|
| `workflow_version` | string | Schema version; auto-migrated forward on load. |
| `workitem` | string \| null | The WorkItem this state belongs to. `null` only in an unmigrated pre-v1.14 `.workflow/state.json`, which since v1.17 is a migration input and never a runtime. Makes a state file self-describing and a misplaced one detectable. |
| `project_name` | string \| null | Inferred from requirements, else the WorkItem title, else asked of the user. |
| `current_phase` | string | Current phase ID (e.g., `gate_plan`). |
| `status` | string | `pending \| in_progress \| awaiting_approval \| awaiting_reapproval \| completed \| rejected \| failed`. |
| `progress` | string | `"N/18"`, derived only from the Progress Map — never computed independently. |
| `last_updated` | string | ISO-8601 timestamp, updated on every write. |
| `current_artifact` | string \| null | Path to the most recently generated artifact. |
| `current_artifact_sha` | string \| null | SHA-256 of `current_artifact` at last verification. |
| `specKit` | object | SpecKit context for this WorkItem: `featureId`, `featureDirectory` (repo-relative, under `workitems/<id>/specs/`; set after Phase 4), and `workflowId` / `runId`, extension points SDLE creates and never writes. |
| `security_review_artifact` | string \| null | Path to the timestamped security review file. |
| `phase_checkpoint` | string \| null | Sub-step marker for crash-recovery idempotency. |
| `pending_confirm_action` | string \| null | Tracks an outstanding confirmation (`restart:<N>`, `reset`, `skip`, `implement_dirty_tree`, `accept_state_jump`, `accept_content:<file>`, `accept_audit_mismatch`). |
| `speckit_initialized` | boolean | Whether `.specify/` exists. |
| `speckit_skill_prefix` | string \| null | Discovered SpecKit invocation prefix (`speckit-` or `speckit.`). |
| `verbose` | boolean | Display-only verbosity toggle. |
| `clarification_phase` | string \| null | Phase awaiting a clarification response, if any. |
| `rate_limits` | object | `{ max_remediation_attempts, max_retry_attempts }`. |
| `attempt_counts` | object | Per-phase `{ remediations, retries }` counters. |
| `approvals` | object | One entry per gate: `{ decision, comments, timestamp }` or `null`. |
| `artifact_shas` | object | Approval-time SHA-256 baseline per gate, for drift detection. |
| `audit_sha` | string \| null | SHA-256 of the entire `audit.md`, recomputed after every append — audit tamper-evidence baseline. |
| `drift_queue` | array | Gate keys awaiting re-approval due to detected drift. |
| `pending_phase` | string \| null | Phase that was about to execute when drift was detected. |
| `phase_history` | array | Ordered `{ phase, completed_at, outcome }` entries. |

---

## Appendix C — Command Reference

| Command | Effect |
|---|---|
| `start workflow` / `begin` | Start a new workflow, or resume an existing one. Append `--verbose` to enable verbose mode. |
| `approve` | Approve the current gate and advance. |
| `approve with comments: <text>` | Approve with recorded feedback. |
| `reject with comments: <text>` | Reject and trigger remediation. (A bare `reject` prompts for comments instead.) |
| `continue` / `resume` | Continue execution; after a rejection, this triggers remediation. |
| `retry` | Re-run the last failed (technical failure) step. |
| `status` / `show state` | Full state dump: phase, approvals, artifacts, rate limits, drift state, history. |
| `restart phase <N>` | Roll back to phase N; clears all downstream approvals and history. Requires `confirm restart phase <N>`. |
| `reset workflow` | Delete all workflow state (artifacts preserved). Requires `confirm reset`. |
| `accept state` | Acknowledge a detected forward state jump and proceed. |
| `accept content` | Acknowledge flagged instruction-like content in a requirements/guidance/clarification file; proceed treating it as data. |
| `accept audit` | Acknowledge an audit-log integrity mismatch; re-baseline `audit_sha` (logged). |
| `confirm implement` | Proceed with Phase 15 despite uncommitted working-tree changes (dirty-tree guard). |
| `skip with warning` | Advance past a *failed* (not rejected) phase without a verified artifact. Logged, discouraged. Requires `confirm skip`. |
| `verbose on` / `verbose off` | Toggle display verbosity. |

The engine commands behind the governance and review records, for operators reading `audit.md` or a CI log:

| Command | Effect |
|---|---|
| `governance policy` | Report the effective governance policy. Needs no WorkItem; writes nothing. |
| `governance assess --input <path>` | Score a structured proposal and write the WorkItem's governance record. Runs before `init`. |
| `governance show` | Report the record and whether it is still current. |
| `governance gates` | Report each gate's disposition for the bound flow, with the reason each requirement rests on. Read-only; answerable before `init`. |
| `gate omit --gate <key>` | Pass a gate the policy does not require approved. Refuses `gate_required` otherwise. |
| `flow show` | Report the bound flow, its ordered phases, its gates, the position in it, and whether the governance record still agrees. Read-only. |
| `artifact review --path <p> --type <t> --result PASS\|FAIL --actor-type <k> --actor-name <n>` | Record a review of an artifact's exact current content. |
| `artifact reviews [--path <p>]` | List review records with a derived freshness verdict. Read-only. |
| `discovery schema` | Report what a discovery document must contain: the closed category vocabulary, the classification vocabulary, the envelope, and which classification properties the engine guarantees versus which are the author's claims. Needs no WorkItem; writes nothing. |
| `discovery assess --input <path>` | Validate a proposed set of repository findings and write the WorkItem's discovery record. Refuses the whole document rather than recording part of it. |
| `discovery show` | Report the recorded findings. Read-only. |
| `baseline show` | Report the repository baseline, its derived status and its findings. Needs no WorkItem; writes nothing. |
| `baseline validate` | Exit 0 only when the baseline is sound; otherwise refuse `baseline_not_valid` and name why. Writes nothing and appends nothing. |

---

## Document Revision History

| Version | Date | Summary |
|---|---|---|
| 1.5 | 2026-09-07 | Updated for SDLE v1.17 — V1 convergence. The WorkItem runtime is the only runtime: the transitional sixth resolution rung is gone and `.workflow/` is now a migration source and project-root marker only, recovered with `workitem create` then `migrate-workflow --workitem <id>`. Spec Kit feature discovery fails closed on more than one candidate in a tier. A governance re-assessment that lowers a recorded level is audited as `governance_downgraded` and carried into later omission evidence. New `pending_branch_ack` state field closes the branch-guard fail-open. See `docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md`. |
| 1.4 | 2026-08-24 | Updated for SDLE v1.15: SpecKit context is WorkItem-scoped. A WorkItem's feature directory moved from `.specify/specs/<feature-id>/` to `workitems/<id>/specs/<feature-id>/`, while repository-wide SpecKit scaffolding — `.specify/`, including `memory/constitution.md` — stays at the repository root. New `specKit` state object replacing `current_feature_id`, `feature bind` and `feature capabilities`, SpecKit capability detection that refuses rather than assumes, tiered feature discovery with an audited move into the WorkItem, and a gate that refuses to approve another WorkItem's artifact. |
| 1.3 | 2026-08-23 | Updated for SDLE v1.14: runtime state is WorkItem-scoped. `state.json`, `execution.json`, `audit.md`, `lock`, `evidence/`, the implementation manifest and the completion summary moved from the repository-global `.workflow/` to `workitems/<id>/.sdle/`. New `workitem` state field, `--workitem` override and resolution ladder, `migrate-workflow` for a legacy runtime, and execution identity. |
| 1.2 | 2026-08-10 | Updated for SDLE v1.13: the mechanical layer moved into `scripts/sdle.py`, a deterministic core that refuses rather than warns. Constants are parsed from SKILL.md rather than hand-synced; `lint-skill` verifies every cross-file rule; nine slash commands and four hooks; Gate 7 carries test evidence and refuses an incomplete manifest; the security diff is pinned to `implementation_base_ref`. See `docs/architecture/ADR-001-deterministic-core.md`. |
| 1.1 | 2026-07-06 | Updated for SDLE v1.12: untrusted-content scan, secrets scan in the implementation manifest, tamper-evident audit log (`audit_sha`), session lock, dirty-tree guard, repo staleness warning, two-step `confirm skip`. |
| 1.0 | 2026-06-20 | Initial enterprise reference guide, covering SDLE v1.11 (18-phase, 8-gate workflow). |
