# SDLE Transition Plan — Wave A Deterministic Core to Latest WorkItem-Based Requirements

**Document:** `transition.md`  
**Repository:** `muhammadallee/sdle-latest`  
**Source branch:** `wave-a-deterministic-core`  
**Baseline commit:** `f8fdaa048b9a9a35d317224eddd191318ccdd7f6`  
**Target:** Latest SDLE V1 requirements discussed and agreed on 2026-08-16  
**Audience:** Claude Code implementing the transition  
**Strategy:** Preserve the proven deterministic spine; change one architectural axis at a time; keep the repository usable and testable after every phase.
**Transition execution mode:** Autonomous orchestration with fresh isolated PLAN / IMPLEMENT / VERIFY agents and durable repository handoffs.

---

## 0. Purpose

This document defines the **incremental transition path** from the current SDLE Wave A implementation to the latest SDLE V1 architecture.

The current implementation already contains valuable, working guardrails:

- deterministic Python core;
- machine-readable CLI contract;
- explicit exit codes;
- atomic state writes;
- audit integrity;
- artifact SHA/fingerprint tracking;
- drift detection;
- dirty-tree guard;
- secrets scanning;
- real test evidence;
- implementation diff baselining;
- hooks;
- cross-platform launchers;
- transcript-derived integration tests;
- CI/linting discipline.

These capabilities MUST be **preserved unless this transition document explicitly supersedes them**.

The target architecture introduces the following material changes:

1. `WorkItem` becomes the sole V1 unit of SDLE orchestration.
2. Multiple independent WorkItems can exist in one repository.
3. Each WorkItem has its own lifecycle state, evidence, audit and Spec Kit context.
4. Developers work concurrently on **different WorkItems** using different Git feature branches/worktrees.
5. Repository-global runtime state is removed.
6. WorkItem resolution works when Claude is launched from:
   - `workitems/<workitem>/`;
   - `workitems/`;
   - repository root;
   - anywhere else inside the repository.
7. Runtime UX remains:
   - launch Claude Code;
   - say `start workflow`.
8. Claude remains the reasoning/conversation layer.
9. Deterministic SDLE core remains the authority for mechanical rules.
10. Spec Kit remains the SDD engine and native artifact owner.
11. Risk becomes hybrid:
   - AI proposes;
   - deterministic policy decides.
12. Brownfield discovery establishes a reusable baseline instead of repeating full discovery.
13. Fixed design/security gates eventually become policy/risk driven.
14. Releases, builds, deployment tracking, MCP, databases, knowledge graphs and centralized orchestration remain out of V1.
15. The migration itself is executable autonomously from one user invocation, but material architectural decisions remain human-owned.

---

# 1. Instructions to Claude Code

Treat this document as a **migration contract** and the repository as the source of implementation truth.

Claude Code MUST:

1. Inspect the actual branch before each phase. Do not assume the repository still matches this baseline.
2. Stop and report if the source baseline is not an ancestor of the working branch, or if architecture materially differs from this contract.
3. Implement **one transition phase at a time**. A phase is not complete until independent verification passes.
4. Preserve all unaffected current behavior and regression tests.
5. Never combine two transition phases merely because they touch the same files.
6. Do not rewrite working deterministic logic without a concrete reason supported by repository evidence.
7. Prefer extraction/refactoring over replacement.
8. Add tests before or with each behavioral change.
9. Keep every completed phase independently recoverable and verifiable.
10. At the end of each phase:
    - run the complete existing test suite;
    - run `lint-skill`;
    - run new phase tests;
    - report regressions exactly;
    - persist phase evidence;
    - independently verify the result;
    - update transition progress.
11. If an architectural ambiguity materially affects implementation:
    - persist a `BLOCKED` record;
    - explain the ambiguity;
    - present the smallest viable choices;
    - recommend one;
    - return control to the human. Do not guess.
12. Do not implement release/build management, MCP, DB persistence, knowledge graph, web UI or other deferred features.
13. Do not trust conversation history, prompt caching, model memory, or a previous agent's prose as authoritative state.
14. Reconstruct every phase from the actual repository plus persisted transition evidence.
15. Never report a command/test as run unless its output was actually observed in the current agent context. Use `NOT_RUN` when appropriate.
16. Never weaken an existing test merely to make a transition phase pass.
17. Never treat a handoff claim as verification evidence; the verifier must independently inspect/reproduce the relevant fact.
18. Never let a transition-execution subagent approve a human SDLE lifecycle gate or mutate SDLE lifecycle state outside the deterministic core.

## 1.1 Autonomous transition execution

Normal execution SHOULD require only one user invocation:

```text
/apply-sdle-transition
```

The migration control plane then executes each transition phase as:

```text
fresh PLAN agent
      |
      v
persist TNN-plan.md
      |
      v
fresh IMPLEMENT agent
      |
      v
persist TNN-handoff-aNN.md
      |
      v
fresh VERIFY agent
      |
      +---- PASS ----> COMPLETE -> next phase
      |
      `---- FAIL ----> fresh remediation IMPLEMENT agent -> fresh VERIFY agent
```

The parent/forked transition orchestrator is a coordinator only. It MUST NOT implement product changes itself.

No manual `/clear` is required. Isolation is provided by distinct fresh subagent contexts and durable repository handoffs.

## 1.2 Durable transition control state

Transition execution MUST persist under:

```text
docs/transition/
+-- transition.md                 # this immutable migration contract
+-- progress.md                   # durable phase status source of truth
+-- phases/
|   +-- TNN-plan.md
|   +-- TNN-handoff-a01.md
|   +-- TNN-verification-a01.md
|   +-- TNN-handoff-a02.md        # only if remediation is needed
|   +-- TNN-verification-a02.md
|   +-- TNN-checkpoint-aNN-XX.md  # optional long-phase checkpoint
|   `-- TNN-blocker.md            # only for material human decision
`-- templates/
```

`progress.md` and the phase artifacts are authoritative for migration handoff. Conversation history is not.

## 1.3 Evidence classification

Agents MUST classify claims as one of:

- `OBSERVED` — directly inspected in repository/tool output;
- `INFERRED` — conclusion from observed evidence, with the evidence named;
- `UNKNOWN` — not safely established.

An `UNKNOWN` fact that can materially change architecture, migration safety, compatibility, or acceptance criteria MUST block rather than be guessed.

## 1.4 Migration execution agents versus target SDLE agents

The files named `sdle-transition-*` are **migration control-plane scaffolding** used to apply this contract. They are not target SDLE V1 runtime agents and their existence does not satisfy T10.

T10 product subagents are introduced only when T10 is reached and its prerequisites are stable.

The transition control plane MAY remain after completion as historical/recovery tooling or be removed in a separate post-transition cleanup after T11 has independently passed. It MUST NOT delete or mutate itself while the transition is still executing.

---

# 2. Current-State Baseline

The baseline implementation is SDLE v1.13 on `wave-a-deterministic-core`.

Current conceptual model:

```text
Repository
   |
   +-- requirements/
   +-- guidance/
   +-- .specify/
   +-- design/
   +-- reviews/
   +-- clarifications/
   |
   `-- .workflow/
       +-- state.json
       +-- audit.md
       +-- lock
       +-- implementation-manifest.md
       `-- completion-summary.json
```

Current lifecycle:

```text
One repository
    |
    `-- One active workflow
          |
          `-- Fixed 18-phase / 8-gate sequence
```

Current mechanical core:

```text
Claude Code
    |
    +-- SDLE skill/modules
    |
    +-- commands/hooks
    |
    `-- scripts/sdle.py
          |
          +-- state transitions
          +-- gates
          +-- SHA fingerprints
          +-- audit chain
          +-- drift
          +-- lock
          +-- rate limits
          +-- migrations
          +-- scans
          `-- validation
```

This deterministic core is the foundation of the target design and MUST NOT be discarded.

---

# 3. Target V1 Architecture

Target conceptual model:

```text
Repository
|
+-- CLAUDE.md
|
+-- .claude/
|   +-- skills/
|   +-- commands/
|   +-- hooks/
|   `-- settings.json
|
+-- .sdle/
|   +-- config/
|   +-- policies/
|   +-- templates/
|   +-- baseline.*
|   `-- implementation-state/
|
+-- workitems/
|   +-- index.md
|   |
|   +-- customer-notification/
|   |   +-- workitem.*
|   |   +-- .sdle/
|   |   |   +-- state.json
|   |   |   +-- execution.json
|   |   |   +-- audit.jsonl
|   |   |   `-- evidence/
|   |   |
|   |   +-- clarifications/
|   |   +-- reviews/
|   |   `-- Spec Kit native WorkItem artifacts
|   |
|   `-- payment-retry/
|       `-- ...
|
+-- .specify/
|   `-- Spec Kit engine/project scaffolding where required
|
`-- application source
```

Target concurrency:

```text
Developer A
  -> Branch A
  -> WorkItem A

Developer B
  -> Branch B
  -> WorkItem B

Developer C
  -> Branch C
  -> WorkItem C
```

V1 invariant:

> Two developers MUST NOT work on the same WorkItem in parallel.

No distributed lock manager is required.

---

# 4. Transition Principles

## TP-001 — Preserve the deterministic spine

The current `sdle.py` refusal model, JSON stdout, exit-code contract, atomic writes and testability remain architectural requirements.

## TP-002 — Change one architectural axis per phase

Example:

- first introduce WorkItem identity;
- then move state;
- then introduce WorkItem-specific Spec Kit context;
- then introduce flow classification;
- then risk-adaptive gates.

Do NOT change all of them simultaneously.

## TP-003 — Existing tests are regression assets

Current tests are not implementation debris.

Every phase MUST classify failing existing tests into exactly one category:

1. unchanged behavior — test must remain green;
2. deliberately superseded behavior — update test and document why;
3. defect discovered — fix implementation.

There is no fourth category.

## TP-004 — WorkItem identity precedes lifecycle redesign

Do not implement brownfield/risk/adaptive flow on repo-global `.workflow/` state.

## TP-005 — Do not duplicate Spec Kit

Spec Kit-native artifacts remain canonical.

SDLE stores governance/evidence/state around them.

## TP-006 — Durable state survives Claude context loss

Workflow correctness cannot depend on:

- conversation history;
- prompt caching;
- model memory.

## TP-007 — Git provides developer concurrency

Different WorkItems use different branches/worktrees.

Do not invent distributed coordination.

## TP-008 — Keep machine-owned state deterministic

The current implementation already has robust JSON behavior.

Unless explicitly changed by a later decision:

- machine-owned runtime state SHOULD remain JSON/JSONL;
- human-authored configuration MAY use YAML/Markdown.

This avoids rewriting proven atomic JSON/migration code solely for format aesthetics.

## TP-009 — Global runtime lock must not block independent WorkItems

The current repository-global lock cannot survive unchanged.

Any retained local session lock must be scoped to one WorkItem.

## TP-010 — No release/build model

WorkItems remain independent.

Future release/build association must be addable without changing WorkItem identity.

## TP-011 — Every governed artifact must be reviewed or validated

Artifact existence alone is not evidence of artifact quality.

Every governed lifecycle artifact MUST be reviewed or validated according to its artifact type before any downstream phase is allowed to rely on it.

The review/validation MUST:

1. apply to the artifact's exact current content version;
2. record the artifact path or canonical artifact identifier;
3. record the artifact SHA/fingerprint where the artifact is file-based;
4. record the review or validation type;
5. record the result (`PASS`, `FAIL`, `APPROVED`, `REJECTED`, or an equivalent governed status);
6. identify the actor/source (`human`, `agent`, `tool`, `test`, or `system`);
7. reference the detailed evidence or review artifact;
8. produce an auditable event.

A review does **not** always require a human approval gate.

Examples:

- requirements may receive semantic quality review plus a human scope approval;
- checklist/tasks may receive automated or AI-assisted validation without a separate human approval;
- implementation must receive actual test/validation evidence and code review;
- security-sensitive artifacts may require both specialist review and explicit human approval depending on policy.

If a reviewed artifact changes after review:

```text
artifact reviewed
      |
      v
SHA/fingerprint recorded
      |
      v
artifact changes
      |
      v
review becomes STALE
      |
      v
required re-review before downstream use
```

SDLE MUST NOT allow a stale review to authorize downstream consumption of a modified artifact.

Purely transient operational files such as temporary files, caches and lock files are not governed lifecycle artifacts and do not require lifecycle review.

## TP-012 — Transition execution is isolated, durable and independently verified

Applying this migration contract MUST NOT depend on one long Claude context.

For each transition phase:

1. planning is performed in a fresh context and persisted;
2. implementation is performed in a different fresh context using the persisted plan and repository evidence;
3. verification is performed in another fresh context and MUST independently validate the implementation;
4. remediation after a failed verification uses a new implementation attempt and a new verification attempt;
5. transition progress is persisted to disk before moving to the next phase;
6. material architecture decisions remain human-owned;
7. ordinary implementation/test/remediation failures are handled autonomously within a bounded retry loop;
8. no transition-execution agent may bypass deterministic SDLE product guardrails.

The migration orchestrator coordinates agents but does not become an alternative authority for SDLE lifecycle transitions.

---

# 5. Transition Overview

| Phase | Name | Primary Change | Lifecycle Semantics |
|---|---|---|---|
| T00 | Baseline Freeze | Record current behavior and transition tests | unchanged |
| T01 | WorkItem Identity | Add WorkItem registry/model without moving runtime state | unchanged |
| T02 | WorkItem-Scoped Runtime | Move `.workflow` state/audit under active WorkItem | unchanged |
| T03 | WorkItem Resolution & Parallel Isolation | Launch from anywhere; branch/worktree context | unchanged |
| T04 | Spec Kit WorkItem Context | Bind Spec Kit feature/artifacts to active WorkItem | unchanged |
| T05 | SDLE Repository Configuration | Introduce `.sdle/` config/policy boundary | unchanged |
| T06 | Classification + Requirements Quality + Risk | Add structured governance inputs | mostly unchanged |
| T07 | Declarative Flow Model | Introduce Greenfield/Iterative/Defect/Hotfix routing | changes |
| T08 | Brownfield Discovery + Baseline | Discover once and converge to iterative | changes |
| T09 | Risk-Adaptive Gates | Make design/security/approval requirements policy driven | changes |
| T10 | Skills/Subagents + Review Refinement | Progressive context and specialist reviews | equivalent governance |
| T11 | Production Hardening & Legacy Removal | Remove compatibility scaffolding, finalize V1 | target complete |

**Do not skip directly to T07+ before T01–T05 are stable.**

---

# 6. T00 — Baseline Freeze and Transition Safety Net

## Goal

Create an explicit regression baseline before changing runtime identity or storage.

## Scope

No product behavior changes.

### Required work

1. Verify branch tip and record it in:
   - `docs/transition/baseline.md`.
2. Run and record:
   - complete pytest suite;
   - `lint-skill`;
   - Linux CI if available;
   - Windows CI if available.
3. Inventory current:
   - CLI subcommands;
   - exit codes;
   - state fields;
   - audit behavior;
   - lock behavior;
   - rate limits;
   - drift behavior;
   - hooks;
   - dirty-tree behavior;
   - untrusted-content scan;
   - secrets scan;
   - test evidence;
   - implementation-base-ref behavior;
   - migrations.
4. Create a transition regression matrix mapping each current capability to:
   - preserve;
   - adapt;
   - supersede later.
5. Add a `transition.md` progress section or separate:
   - `docs/transition/progress.md`.

## Explicitly preserve

- 18-phase sequence;
- 8 gates;
- current `.workflow/` location;
- current lock behavior;
- current Spec Kit feature behavior.

Those are intentionally preserved until later phases.

## Tests

No existing test may be weakened merely to make T00 pass.

## Exit criteria

- complete baseline inventory exists;
- baseline suite is green;
- no runtime behavior has changed;
- every current guardrail has a disposition.

---

# 7. T01 — Introduce WorkItem Identity Without Moving Runtime State

## Goal

Introduce the new primary domain identity with the smallest possible behavioral change.

Current lifecycle remains fixed.

## New repository structure

Create:

```text
workitems/
`-- index.md
```

Add deterministic WorkItem commands/services.

### WorkItem naming

Normal flow:

```text
User: start workflow

Claude:
WorkItem name?
```

If user supplies:

```text
Customer Notification Service
```

normalize to:

```text
customer-notification-service
```

using kebab-case.

Rules:

1. trim;
2. lowercase;
3. whitespace -> `-`;
4. `_` -> `-`;
5. remove unsupported punctuation;
6. collapse repeated hyphens;
7. strip leading/trailing hyphens;
8. allow `[a-z0-9-]`;
9. reject empty result;
10. require uniqueness.

Do not silently create:

```text
foo-2
foo-copy
foo-final
```

On duplicate:

```text
Resume existing WorkItem?
or
Provide another name?
```

### Auto-generation

Only if user explicitly requests:

```text
auto generate
```

Claude infers a concise kebab-case name.

Deterministic core creates:

```text
WI-<inferred-name>-<YYYYMMDDTHHMMSSZ>
```

Example:

```text
WI-payment-retry-20260816T170530Z
```

### WorkItem metadata

Create a minimal machine/human-readable metadata file.

Preferred initial shape:

```json
{
  "id": "customer-notification-service",
  "name": "customer-notification-service",
  "title": "Customer Notification Service",
  "type": "enhancement",
  "synopsis": "Add configurable customer notifications.",
  "createdAt": "2026-08-16T17:05:30Z",
  "createdBy": {
    "gitUserName": "Muhammad Ali",
    "gitUserEmail": "..."
  },
  "git": {
    "initialBranch": "feature/customer-notification-service"
  },
  "sdleVersion": "..."
}
```

If latest approved requirements explicitly require `workitem.yaml`, implement YAML only after deciding whether introducing a YAML parser dependency is acceptable. Do not hand-roll a general YAML parser.

### `workitems/index.md`

Append-only creation registry:

```markdown
# Work Items

| Created | WorkItem | Type | Title | Synopsis |
|---|---|---|---|---|
```

Rules:

- append only;
- no mutable status;
- reject duplicate ID;
- validate structure before append;
- do not implement hash chaining yet.

## Compatibility behavior

During T01:

- `.workflow/` remains current runtime state;
- current 18 phases remain;
- existing Spec Kit behavior remains;
- current repo-global lock remains temporarily.

WorkItem identity is added alongside the legacy runtime.

## New tests

- normalization;
- unsafe/path-traversal names;
- duplicate names;
- auto-generation;
- index append;
- index malformed;
- metadata creation;
- Git identity capture.

## Exit criteria

A new workflow has an immutable WorkItem identity before legacy workflow initialization, while all existing phase/gate behavior still passes.

---

# 8. T02 — Move Runtime State from Repository-Global to WorkItem-Scoped

## Goal

Make independent WorkItems mechanically possible.

This is the most important storage transition.

## From

```text
.workflow/
+-- state.json
+-- audit.md
+-- lock
+-- implementation-manifest.md
`-- completion-summary.json
```

## To

```text
workitems/<workitem>/.sdle/
+-- state.json
+-- execution.json
+-- audit.jsonl or compatible chained audit representation
+-- lock                 # only if retained
+-- evidence/
+-- implementation-manifest.md
`-- completion-summary.json
```

## Core refactor

Replace the current implicit:

```text
Paths(project_root)
```

with explicit concepts similar to:

```text
RepositoryContext
WorkItemContext
```

All operational path resolution must be based on the active WorkItem.

No command should infer WorkItem-owned paths by concatenating strings independently.

## Execution identity

Add lightweight execution identity:

```text
<3-letter-git-user-prefix>-<UTC-datetime>
```

Example:

```text
muh-20260816T171501Z
```

Prefix:

1. `git config user.name`;
2. lowercase;
3. remove non-alphanumeric;
4. first 3 characters;
5. fallback to email local part;
6. final fallback `usr`.

Execution identity belongs to execution/audit metadata, **not** the WorkItem name.

## State migration strategy

During T02 support both layouts only for migration:

```text
legacy: <repo>/.workflow/
target: <repo>/workitems/<wi>/.sdle/
```

Migration MUST:

1. require an explicitly resolved WorkItem;
2. validate legacy state;
3. verify audit integrity;
4. copy/migrate atomically;
5. update WorkItem metadata;
6. verify target;
7. leave legacy state untouched until target verification succeeds;
8. record migration evidence;
9. not silently delete legacy state.

Do not support indefinite dual-write.

## Lock behavior

Repository-global locking MUST end in this phase.

Preferred target:

- no global lock;
- optional WorkItem-local session lock if needed for same-session protection.

A WorkItem lock MUST NOT block a different WorkItem.

## Existing guardrails to adapt, not remove

- drift detection;
- audit chain;
- rate limits;
- checkpoint/idempotency;
- manifest;
- secrets scan;
- test evidence;
- implementation base ref;
- state migration;
- atomic writes.

## Tests

Create two WorkItems and verify:

```text
WI-A state changes
do not modify
WI-B state
```

Also test:

- two separate WorkItem audits;
- two separate manifests;
- two separate locks if retained;
- legacy migration;
- crash during migration;
- corrupt legacy state;
- corrupt target state.

## Exit criteria

No active workflow runtime state is repository-global.

Existing 18-phase behavior passes independently for at least two WorkItems.

---

# 9. T03 — WorkItem Resolution and Parallel Developer Isolation

## Goal

Support the agreed Claude launch model.

## Supported launch locations

Claude may start from:

1. `workitems/<workitem>/`;
2. `workitems/`;
3. repository root;
4. anywhere inside the repository.

## Resolution priority

```text
1. explicit --workitem
2. CWD inside a WorkItem
3. persisted valid active context
4. Git branch / WorkItem metadata
5. AI-assisted inference
6. ask user
```

### Mandatory ambiguity behavior

```text
0 valid candidates -> create/ask
1 valid candidate  -> use
>1 plausible       -> ASK
```

Never silently pick one among multiple plausible WorkItems.

## Explicit CLI override

Support:

```text
sdle start --workitem <name>
```

Normal users still interact through Claude:

```text
start workflow
```

## Branch/worktree rules

For V1:

- one active WorkItem per developer branch/worktree;
- two developers do not work the same WorkItem in parallel;
- different WorkItems may run concurrently;
- record branch and starting SHA;
- branch mismatch produces explicit warning/refusal depending on safety impact.

Do not implement distributed locking.

## Add validation

`sdle validate` should detect:

- duplicate WorkItem IDs;
- indexed WorkItem missing directory;
- directory missing index entry;
- malformed metadata;
- branch mismatch;
- runtime state outside active WorkItem;
- path traversal/symlink escape.

## Tests

Matrix:

| CWD | WorkItems | Git signal | Expected |
|---|---:|---|---|
| inside WI-A | many | irrelevant | WI-A |
| `workitems/` | one active | match | select |
| `workitems/` | many plausible | none | ask |
| repo root | branch maps WI-A | unique | WI-A |
| repo root | ambiguous | mixed | ask |
| nested source dir | unique persisted context | valid | select |
| nested source dir | none | none | create/ask |

## Exit criteria

Two developers on separate branches/worktrees can operate two different WorkItems without shared SDLE state or a global lock.

---

# 10. T04 — Bind Spec Kit to the Active WorkItem

## Goal

Make WorkItem identity the outer orchestration boundary while preserving Spec Kit as the native SDD engine.

## Principle

```text
WorkItem
   |
   `-- active Spec Kit feature context
```

WorkItem and Spec Kit feature ID are related but not identical concepts.

## Required behavior

For the active WorkItem, configure Spec Kit using supported mechanisms such as:

```text
SPECIFY_INIT_DIR=<repo-root>
SPECIFY_FEATURE_DIRECTORY=<workitem-relative-path>
```

when supported by the installed Spec Kit version.

Capability-detect; do not hardcode undocumented internals.

## Artifact rule

If Spec Kit owns an artifact:

- use the native artifact;
- record/reference it from SDLE;
- do not create an SDLE duplicate.

## Constitution/shared baseline nuance

Project-level shared artifacts may remain repository-level when they are truly repository-wide.

WorkItem-specific artifacts must be attributable to the active WorkItem.

Do not copy shared artifacts into every WorkItem merely to satisfy directory aesthetics.

## Migration

Legacy `current_feature_id` becomes a Spec Kit reference, not primary SDLE identity.

New state conceptually becomes:

```json
{
  "workitem": "customer-notification-service",
  "specKit": {
    "featureId": "...",
    "featureDirectory": "workitems/customer-notification-service",
    "workflowId": null,
    "runId": null
  }
}
```

## Tests

Verify:

- WorkItem A Spec Kit output cannot be mistaken for WorkItem B;
- WorkItem resolution precedes Spec Kit invocation;
- branch alone does not define Spec Kit context;
- missing required Spec Kit capability fails closed;
- native artifacts are not duplicated.

## Exit criteria

A full current 18-phase flow can run against WorkItem-scoped Spec Kit context.

---

# 11. T05 — Introduce Repository-Level `.sdle/` Configuration Boundary

## Goal

Separate repository-wide SDLE configuration from WorkItem runtime state.

## Create

```text
.sdle/
+-- config.*
+-- policies/
+-- templates/
+-- baseline.*
`-- implementation-state/
```

## Ownership

Repository `.sdle/` owns:

- global SDLE configuration;
- policy definitions;
- shared templates;
- future baseline;
- implementation-transition metadata.

WorkItem `.sdle/` owns:

- lifecycle state;
- execution;
- audit;
- evidence;
- WorkItem-specific manifests.

## Do not move lifecycle rules yet

At T05, current 18-phase behavior still remains authoritative.

This phase establishes the boundary before new flow/risk policies are introduced.

## Policy format decision

The latest requirements describe YAML policy files.

The current core is standard-library-only and natively supports JSON.

Before introducing executable YAML policies, Claude MUST make the dependency decision explicit:

### Recommended default

- JSON for machine-owned executable policy/state if preserving stdlib-only is a priority;
- YAML only if adding a small YAML dependency is explicitly accepted.

Do not implement a home-grown YAML parser.

## Exit criteria

Repository-global configuration exists independently from WorkItem runtime state, with no lifecycle behavior change.

---

# 12. T06 — Requirements Quality, Structured Classification and Hybrid Risk

## Goal

Add governance inputs before changing lifecycle routing.

This phase computes decisions but initially may still execute the existing lifecycle.

## Add Requirements Quality Gate

Structured checks:

- clear problem statement;
- scope;
- out-of-scope;
- acceptance criteria;
- ambiguity;
- contradictions;
- constraints;
- NFRs when relevant;
- security/data implications;
- compatibility;
- dependencies;
- blocking unknowns.

Blocking findings stop progression.

## Add classifications

### WorkItem type

```text
enhancement
defect
hotfix
chore
```

### Engineering flow proposal

```text
GREENFIELD
BROWNFIELD_DISCOVERY
ITERATIVE
DEFECT_FIX
HOTFIX
```

At T06 this may be advisory/recorded while current 18-phase execution remains unchanged.

## Add hybrid risk

```text
Claude proposes signals
        +
deterministic policy
        |
        v
final risk
```

Levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Claude cannot lower deterministic policy floors.

## Preserve current gates temporarily

Do not make gates conditional yet.

Record what the future required gate set **would be** for test comparison.

## Evidence

Persist:

- requirements-quality result;
- classification;
- risk signals;
- deterministic score;
- hard floors;
- final risk;
- uncertainty.

## Governed artifact review/validation

From this phase onward, every governed artifact produced or materially changed by the lifecycle MUST be registered and reviewed/validated before a downstream phase may consume it.

Conceptually:

```text
Generate / modify artifact
        |
        v
Register artifact + SHA
        |
        v
Required review / validation
      /     \
   PASS      FAIL
    |          |
    |       Audit finding
    |          |
    |       Remediate
    |          |
    |       Re-generate
    |          |
    |       Re-review
    |          |
    +-----+----+
          |
          v
Eligible for downstream use
```

The detailed review result SHOULD live as evidence or as a human-readable review artifact. The audit log SHOULD reference the review rather than duplicate its full contents.

Minimum audit linkage:

```json
{
  "eventType": "ARTIFACT_REVIEWED",
  "artifact": "plan.md",
  "artifactSha": "sha256:...",
  "reviewType": "architecture-review",
  "result": "PASS",
  "evidenceId": "evd-...",
  "actor": {
    "type": "agent",
    "name": "sdle-architect"
  }
}
```

If the artifact SHA no longer matches the reviewed SHA, the review is stale and the artifact MUST be reviewed again before downstream use.

Human approval remains policy-driven; review/validation is universal for governed artifacts.

## Exit criteria

Every WorkItem has deterministic, testable governance metadata before current planning/implementation begins.

---

# 13. T07 — Replace Fixed Universal Sequence with Declarative Flow Selection

## Goal

Retire the assumption that every WorkItem must traverse exactly the same lifecycle.

This is the first phase that intentionally changes lifecycle semantics.

## Required flows

At minimum:

```text
GREENFIELD
ITERATIVE
DEFECT_FIX
HOTFIX
BROWNFIELD_DISCOVERY
```

## Constraint

Do NOT build a generic BPM/workflow framework.

Implement only the lifecycle constructs SDLE currently needs.

## Suggested lifecycle shape

### GREENFIELD

```text
Requirements
 -> Constitution/baseline rules as applicable
 -> Specify
 -> Clarify
 -> Plan
 -> Checklist
 -> Tasks
 -> Analyze
 -> Implement
 -> Validate
 -> Review
 -> Converge
 -> Human Review
```

### ITERATIVE

Use established repository baseline.

No full repository rediscovery.

### DEFECT_FIX

```text
Defect
 -> Impact analysis
 -> existing spec mapping
 -> spec delta/gap
 -> targeted plan/tasks
 -> implement
 -> validate
 -> review
```

### HOTFIX

Shorter but never ungoverned.

Mandatory risk/policy checks remain.

## Transition strategy

Do not delete old fixed tables immediately.

Introduce a compatibility translation first.

Only remove legacy fixed-sequence structures after:

- new flow tests pass;
- dry-run behavior has explicit disposition;
- migration path exists.

## Exit criteria

Flow selection changes which phases execute without compromising deterministic state transitions.

---

# 14. T08 — Brownfield Discovery and Greenfield/Brownfield Convergence

## Goal

Create a reusable repository baseline exactly when needed.

## Trigger full discovery when

- significant existing source exists; AND
- no valid SDLE baseline exists;

OR:

- user explicitly requests rediscovery;

OR:

- deterministic validation identifies material baseline invalidation.

## Discovery output must identify

- repository inventory;
- modules/components;
- dependencies;
- architecture;
- significant patterns;
- conventions;
- APIs;
- persistence/data architecture;
- test practices;
- runtime/deployment assumptions where discoverable;
- security patterns;
- ADRs;
- constraints/non-negotiables;
- relevant risks/debt.

Every finding is classified:

```text
OBSERVED
INFERRED
UNKNOWN
```

Never present inference as observation.

## Baseline

Create repository-level baseline descriptor:

```text
.sdle/baseline.*
```

It references canonical artifacts instead of copying them.

Record:

- baseline version;
- producing WorkItem;
- commit SHA;
- constitution reference;
- architecture/design references;
- ADRs;
- non-negotiables;
- discovery status;
- timestamp.

## Convergence invariant

After initial:

- greenfield completion; or
- brownfield discovery completion;

the repository has the same minimum baseline shape required for future `ITERATIVE` WorkItems.

## Exit criteria

The second WorkItem against the same valid baseline does not rerun full brownfield discovery.

---

# 15. T09 — Risk-Adaptive Gate Policy

## Goal

Replace fixed mandatory design/security approvals with policy-driven gates without weakening governance.

## Default intent

### LOW

Require at least:

- preflight;
- requirements quality;
- implementation validation;
- code review;
- final human review.

### MEDIUM

Add:

- design review;
- checklist/analysis as applicable.

Security becomes mandatory on security/data/API triggers.

### HIGH

Require:

- requirements;
- design/architecture;
- checklist/analysis;
- validation;
- code review;
- security;
- documentation review;
- final human approval.

### CRITICAL

HIGH plus:

- human approval before implementation;
- human approval before completion.

## Hard risk floors

At minimum:

```text
authentication/authorization/security control -> HIGH
sensitive/regulated data                     -> HIGH
destructive/irreversible migration           -> HIGH
breaking external/public contract            -> HIGH
financial transaction correctness            -> HIGH
regulatory/compliance                        -> HIGH
production security boundary                 -> HIGH
catastrophic blast radius                    -> CRITICAL
credential/private-key exposure              -> CRITICAL
```

## Preserve Wave A guardrails

Risk-adaptive gates do NOT mean removal of:

- drift protection;
- gate artifact SHA;
- test evidence;
- secret scan;
- implementation diff baseline;
- audit chain;
- retry/remediation caps;
- fail-safe state transitions.

## Gate evidence

Every required, omitted, approved, rejected or excepted gate must be explainable and auditable.

## Exit criteria

Design/security are neither universally mandatory nor casually skippable.

Policy determines applicability.

---

# 16. T10 — Progressive Claude Skills and Specialist Subagents

## Goal

Optimize reasoning quality/context without moving authority back into prompts.

## Skill direction

Evolve from:

```text
one orchestrator + modules
```

toward progressively loaded capabilities such as:

```text
sdle-start
sdle-requirements-quality
sdle-brownfield-discovery
sdle-design-review
sdle-code-review
sdle-security-review
```

Do this only after deterministic lifecycle ownership is stable.

## Subagents

> **Important:** the `sdle-transition-*` agents used to execute this migration are temporary migration control-plane scaffolding. They do not count as the product subagents introduced by T10 and MUST NOT be used as evidence that T10 is complete.

Use product subagents for high-context independent analysis:

- brownfield discovery;
- architecture/design review;
- code review;
- security review.

Subagents may:

- inspect;
- reason;
- produce structured findings/evidence.

Subagents MUST NOT:

- mutate lifecycle state directly;
- approve human gates;
- bypass deterministic policy;
- become independent workflow controllers.

## Parent-session invariant

Human approval gates remain in the parent Claude session.

## Prompt/memory invariant

Correctness relies on:

```text
CLAUDE.md
+ skills
+ .sdle files
+ WorkItem artifacts
+ Spec Kit artifacts
```

not old conversation context.

## Exit criteria

A fresh Claude session can resume a WorkItem safely and load only relevant phase context.

---

# 17. T11 — Production Hardening, Cleanup and V1 Convergence

## Goal

Remove migration scaffolding and establish the new architecture as the sole supported V1 model.

## Remove/deprecate

After all migration tests pass:

- repository-global `.workflow/`;
- repo-global runtime lock;
- WorkItem-less workflow initialization;
- `current_feature_id` as workflow identity;
- universal fixed 18-phase assumption;
- fixed 8-gate assumption;
- obsolete skill constants/tables;
- transitional dual-path code.

## Preserve

- CLI refusal contract;
- JSON stdout;
- exit codes;
- cross-platform launchers;
- atomic writes;
- migration discipline;
- audit integrity;
- artifact hashing;
- drift;
- secrets scan;
- test evidence;
- implementation diff baseline;
- path safety;
- hooks where still applicable;
- dry-run/regression philosophy.

## Hardening tests

Mandatory:

- two WorkItems in separate branches/worktrees;
- state isolation;
- WorkItem index merge-conflict validation;
- corrupt state;
- corrupt audit;
- interrupted atomic write;
- interrupted legacy migration;
- ambiguous resolution;
- missing Spec Kit;
- unsupported Spec Kit capability;
- stale baseline;
- policy floor enforcement;
- gate omission evidence;
- restart after `/clear`;
- restart in fresh Claude session;
- Windows/Linux behavior.

## Documentation

Update at minimum:

```text
README.md
CLAUDE.md
docs/architecture/
docs/workitems/
docs/lifecycle/
docs/risk-and-gates/
docs/brownfield/
docs/spec-kit-integration/
docs/troubleshooting/
```

## Exit criteria

Latest WorkItem-based requirements are the only normal runtime model and all V1 definition-of-done checks pass.

---

# 18. Existing Capability Preservation Matrix

The following Wave A behaviors are regression requirements unless explicitly superseded.

| Capability | Transition |
|---|---|
| Python deterministic core | PRESERVE |
| Claude-first UX | PRESERVE |
| CLI called by Claude | PRESERVE |
| JSON stdout contract | PRESERVE |
| Exit codes 0/1/2/3 | PRESERVE unless deliberately versioned |
| Atomic writes | PRESERVE |
| Idempotent deterministic commands | PRESERVE |
| Cross-platform launchers | PRESERVE |
| Artifact SHA/fingerprints | PRESERVE |
| Artifact review/validation against exact SHA | ADD / ENFORCE |
| Review evidence + audit linkage | ADD / ENFORCE |
| Stale-review invalidation after artifact change | ADD / ENFORCE |
| Drift detection | PRESERVE |
| Drift diff evidence | PRESERVE |
| Audit integrity/hash chain | PRESERVE |
| Rate limits | PRESERVE |
| Dirty-tree guard | PRESERVE |
| Untrusted-content scan | PRESERVE |
| Secrets scan | PRESERVE |
| Test evidence | PRESERVE |
| `implementation_base_ref` concept | PRESERVE |
| Hook guardrails | ADAPT to WorkItem paths |
| Transcript-derived tests | PRESERVE/EVOLVE |
| `lint-skill` | PRESERVE initially; simplify as constants move |
| `.workflow/` repo-global runtime | REPLACE T02 |
| repo-global lock | REMOVE/RESCOPE T02 |
| fixed 18 phases | REPLACE T07 |
| fixed 8 gates | REPLACE T09 |
| `current_feature_id` as primary identity | DEMOTE T04 |
| runtime artifacts gitignored | REVERSE for WorkItem records |
| lifecycle constants in `SKILL.md` | MIGRATE only after T07/T09 stable |

---

# 19. Git and Version-Control Transition

Current Wave A intentionally ignores runtime artifacts.

The target model treats WorkItem records as versioned engineering evidence.

Therefore update `.gitignore` incrementally.

## Must eventually be versioned

```text
workitems/index.md
workitems/<wi>/workitem.*
workitems/<wi>/.sdle/state.json
workitems/<wi>/.sdle/execution.json
workitems/<wi>/.sdle/audit.*
workitems/<wi>/.sdle/evidence/
workitems/<wi>/clarifications/
workitems/<wi>/reviews/
required WorkItem Spec Kit artifacts
.sdle/baseline.*
.sdle/policies/*
```

## May remain local/ignored

Only data that is truly ephemeral, such as:

- process temp files;
- caches;
- local tool caches;
- lock files if retained;
- environment-specific temporary output.

Do not commit secrets.

---

# 20. Legacy Workflow Migration

If compatibility with existing local `.workflow/` runs is needed, support a bounded migration path.

## Migration command

Conceptually:

```text
sdle migrate-workflow --workitem <name>
```

It must:

1. resolve repository;
2. resolve/create target WorkItem;
3. validate legacy state;
4. validate legacy audit;
5. capture source SHA/state;
6. migrate into WorkItem `.sdle/`;
7. preserve phase/gate status;
8. preserve approval fingerprints;
9. preserve rate limits/counters;
10. preserve implementation baseline;
11. verify result;
12. audit migration.

## No permanent dual-write

After migration:

- target state is authoritative;
- legacy files are archival only;
- do not keep both in sync.

If no external users depend on legacy runtime migration, this compatibility path MAY be reduced, but only by explicit decision.

---

# 21. Runtime UX Through the Transition

The user experience must remain stable:

```text
Developer
  |
  | launch Claude Code
  |
  `> start workflow
```

Claude continues to invoke deterministic commands internally.

Do NOT force normal developers to type:

```text
sdle ...
```

The CLI remains directly usable for:

- testing;
- debugging;
- CI;
- future automation.

MCP remains deferred.

---

# 22. Suggested CLI Evolution

Do not redesign the entire CLI in one phase.

Evolve incrementally.

## Current commands

Preserve existing commands until replacements are proven.

## Add WorkItem capabilities

Conceptually:

```text
sdle workitem create
sdle workitem resolve
sdle workitem list
sdle workitem validate

sdle start --workitem <name>
sdle status
sdle resume
sdle validate
```

## Later governance capabilities

```text
sdle risk evaluate
sdle gate status
sdle gate record
sdle baseline validate
```

All programmatic commands should continue to return structured JSON.

---

# 23. Recommended Internal Refactoring Sequence

Do not begin by splitting `sdle.py` only because it is large.

First establish stable seams through tests.

When natural boundaries become clear, extract roughly in this order:

```text
sdle/
+-- context.py        # repository/workitem resolution
+-- state.py          # machine state, atomic persistence, migration
+-- audit.py          # audit chain/evidence
+-- git.py            # branch/SHA/status/diff
+-- workitems.py      # identity/index/metadata
+-- speckit.py        # adapter/capability detection
+-- policy.py         # risk/gates/flows
+-- validation.py     # deterministic checks
`-- cli.py
```

The command-line adapter must call services; business rules must not live only in argument parsing.

Do not introduce a framework solely to achieve this split.

---

# 24. Autonomous Phase Execution Protocol for Claude

The preferred migration UX is one-shot autonomous execution:

```text
/apply-sdle-transition
```

The orchestrator MUST process `T00` through `T11` sequentially. It MUST NOT start a later phase until the current phase is `COMPLETE` with independent `PASS` verification.

The legacy/manual commands remain valid **recovery/debug concepts**, not the normal user workflow:

```text
plan-phase TNN
implement-phase TNN
verify-phase TNN
```

## 24.1 Orchestrator responsibilities

The transition orchestrator MUST only:

1. validate the transition control plane;
2. read `transition.md` and `progress.md`;
3. inspect Git/baseline state;
4. identify the next required stage;
5. launch the correct fresh specialist agent;
6. wait for durable evidence from that agent;
7. validate persisted state before proceeding;
8. run bounded remediation when verification fails for an implementation reason;
9. stop and return a precise decision request when a material human decision is required;
10. report completion only after T11 verification passes.

The orchestrator MUST NOT directly implement product changes or independently declare a phase PASS.

## 24.2 PLAN

For `TNN`, a fresh planner MUST:

1. read this transition document;
2. inspect current repository state;
3. read `progress.md` and all relevant preceding transition evidence;
4. reconstruct current behavior from repository evidence, not prior-agent narrative;
5. map exact files likely to change;
6. identify current tests affected;
7. identify new tests required;
8. state deliberate behavioral changes;
9. state preserved behavior/invariants;
10. identify failure modes and rollback strategy;
11. define objective acceptance criteria;
12. identify `OBSERVED`, `INFERRED`, and `UNKNOWN` facts;
13. persist `docs/transition/phases/TNN-plan.md`;
14. set phase status to `PLANNED` only when the plan is executable without a material unresolved decision;
15. stop without coding.

If a material unresolved decision exists, write `TNN-blocker.md`, set `BLOCKED`, and return the decision request.

## 24.3 IMPLEMENT

For `TNN`, a fresh implementer MUST:

1. re-read repository state, this contract, `progress.md`, and `TNN-plan.md` from disk;
2. verify the plan matches current repository evidence;
3. implement **only TNN**;
4. make the smallest change that satisfies acceptance criteria while preserving proven guardrails;
5. run targeted tests during development;
6. run the full suite;
7. run `lint-skill`;
8. record every deliberate test change and its category from TP-003;
9. record actual command/test results, never predictions;
10. persist `TNN-handoff-aNN.md` for the current attempt;
11. set status to `IMPLEMENTED` only after implementation evidence exists;
12. stop.

If resuming after verification `FAIL`, the new implementer MUST read that failed verification as a finding set, increment the attempt, remediate only the current phase, and produce a new handoff. It MUST NOT rewrite the verifier's evidence.

For large phases, the implementer SHOULD persist `TNN-checkpoint-aNN-XX.md` after meaningful milestones so an interrupted fresh agent can resume from disk plus Git diff.

## 24.4 VERIFY

For `TNN`, a fresh verifier MUST assume the implementation may be wrong.

It MUST:

1. read this contract and `TNN-plan.md`;
2. inspect the actual Git diff/repository state independently;
3. treat `TNN-handoff-aNN.md` only as a list of claims to verify, not as proof;
4. run phase acceptance checks;
5. run targeted regression checks;
6. run the full suite;
7. run `lint-skill`;
8. inspect for future-phase leakage;
9. inspect for weakened/deleted regression tests without valid TP-003 rationale;
10. inspect for fail-open behavior, duplicated sources of truth, state/audit/evidence regressions, migration/path errors, cross-platform regressions, and silent guardrail loss;
11. verify governed artifact review/validation is bound to the exact current SHA where applicable;
12. persist `TNN-verification-aNN.md` with exactly one top-level result: `PASS` or `FAIL`;
13. set `COMPLETE` only on `PASS`.

The verifier MUST NOT silently fix product code. A `FAIL` returns findings to a new implementer context.

## 24.5 Bounded remediation

A verification `FAIL` caused by ordinary implementation defects is automatically remediated using a fresh implementer and then a fresh verifier.

Default maximum automatic implementation attempts per phase: **3**.

After the third failed attempt, or earlier when the failure requires a material architectural/user decision:

```text
status = BLOCKED
```

The orchestrator MUST return:

- exact blocker;
- evidence;
- affected phase;
- smallest viable choices;
- recommendation;
- what will resume after the decision.

## 24.6 Context-clearing rule

Manual `/clear` is not part of normal execution.

Fresh context boundaries are achieved by separate specialist subagents. If any agent is interrupted, compacted, rate-limited, or otherwise terminated before durable completion, the orchestrator MUST NOT infer success. A future run resumes from:

```text
repository state
+ transition.md
+ progress.md
+ persisted phase artifacts
+ actual Git/test evidence
```

## 24.7 Human lifecycle gates

This autonomous migration protocol does not change the SDLE product invariant that human lifecycle gates stay in the parent user-facing session.

Migration-execution agents may inspect/evidence gate behavior but MUST NOT manufacture human approval, reinterpret refusal as approval, or bypass the deterministic core.

---

# 25. Transition Progress Record

`docs/transition/progress.md` is the durable migration handoff source of truth.

Each phase uses one of these durable statuses:

```text
NOT_STARTED
PLANNED
IMPLEMENTED
BLOCKED
COMPLETE
```

Required table fields:

```markdown
| Phase | Status | Attempt | Plan | Handoff | Verification | Commit | Tests | Notes |
|---|---|---:|---|---|---|---|---|---|
| T00 | NOT_STARTED | 0 | - | - | - | - | NOT_RUN | - |
```

Rules:

1. `PLANNED` requires `TNN-plan.md`.
2. `IMPLEMENTED` requires a plan and the latest `TNN-handoff-aNN.md`.
3. `COMPLETE` requires plan + matching handoff + matching `TNN-verification-aNN.md` whose result is `PASS`.
4. A `FAIL` verification never becomes `COMPLETE`.
5. A remediation attempt increments `Attempt`; earlier handoff/verification files are retained.
6. `BLOCKED` must identify a material blocker and must not be converted to success by model inference.
7. `Commit` records the observed implementation commit if one exists; otherwise use `UNCOMMITTED`. Do not invent a SHA.
8. `Tests` records observed outcomes or `NOT_RUN`.
9. Progress must be validated before starting the next stage.
10. Conversation summaries are non-authoritative.

The migration kit provides a deterministic validator at:

```text
tools/transition/validate.py
```

The orchestrator MUST run it before and after every specialist stage.

---

# 26. Definition of Successful Transition

The transition is complete when all of the following hold:

1. Normal user starts SDLE inside Claude by saying `start workflow`.
2. WorkItem is the primary V1 orchestration unit.
3. User-supplied names become unique kebab-case directory names.
4. `auto generate` produces `WI-<inferred-name>-<datetime>`.
5. `workitems/index.md` is append-only by SDLE behavior.
6. WorkItem state/audit/evidence are isolated.
7. Repository-global `.workflow/` is no longer normal runtime state.
8. Different WorkItems can be developed simultaneously on different Git branches/worktrees.
9. Same-WorkItem parallel development is explicitly unsupported in V1.
10. Claude launch works from WorkItem, `workitems/`, repo root or elsewhere in repo.
11. Ambiguous WorkItem resolution asks instead of guessing.
12. Spec Kit operates in the active WorkItem context.
13. Native Spec Kit artifacts are not duplicated.
14. Requirements quality is explicit.
15. Flow classification is explicit.
16. Risk is hybrid: AI proposes, deterministic policy decides.
17. Hard risk floors cannot be lowered by the model.
18. Greenfield flow works.
19. Iterative flow works.
20. Defect/hotfix flows work.
21. Brownfield discovery creates a reusable baseline.
22. Full brownfield discovery is not repeated by default.
23. Design/security gates are policy-driven.
24. Human gates are evidenced.
25. Every governed artifact is reviewed or validated before downstream consumption.
26. Every artifact review/validation is linked to evidence and an audit event for the exact artifact version/SHA.
27. A changed artifact invalidates any stale review and requires re-review before downstream use.
28. Audit remains append-only/tamper-evident.
29. Drift detection remains functional.
30. Secrets/test evidence remain functional.
31. Resume works after fresh Claude context.
32. No database is required.
33. No MCP is required.
34. No release/build model exists.
35. No web UI exists.
36. Existing deterministic guardrails have not been silently lost.
37. Test suite is green on supported platforms.
38. Core remains suitable for a future MCP adapter without changing domain logic.
39. Every completed transition phase has a persisted plan, implementation handoff and independent PASS verification.
40. Transition execution can resume from a fresh Claude context using repository evidence only.
41. Migration-execution agents never substitute for human SDLE lifecycle approvals or deterministic core authority.

---

# 27. Explicit Deferred Work

Do NOT implement during this transition unless separately approved:

```text
Release management
Build management
Deployment tracking
Environment promotion
Central database
Central SDLE service
REST API
Web UI
MCP server
Cross-repository orchestration
Distributed locks
Knowledge graph
RAG
OPA/Rego
n8n
LangGraph workflow orchestration
Other coding-agent adapters
Autonomous deployment
```

Extension points are acceptable; speculative implementations are not.

---

# 28. Final Migration Rule

When there is tension between the existing implementation and the latest requirements, use this priority:

```text
1. Explicit latest user decision
2. This transition contract
3. Latest requirements.md
4. Existing deterministic safety behavior
5. Existing implementation convenience
```

However:

> Never remove an existing safety control merely because the new requirements did not repeat it.

If the new architecture makes a safety control obsolete, Claude must explicitly document why and provide the replacement safety property before removing it.

---

# 29. Recommended Immediate Next Action

Install the transition kit at the repository root **before launching a new Claude Code session**, then invoke:

```text
/apply-sdle-transition
```

The orchestrator must first validate:

1. repository identity;
2. source baseline ancestry (`f8fdaa048b9a9a35d317224eddd191318ccdd7f6`);
3. unexpected dirty-tree changes;
4. transition control-plane integrity;
5. baseline tests and `lint-skill` availability.

It then executes:

```text
T00 PLAN -> IMPLEMENT -> VERIFY
T01 PLAN -> IMPLEMENT -> VERIFY
T02 PLAN -> IMPLEMENT -> VERIFY
...
T11 PLAN -> IMPLEMENT -> VERIFY
```

Each arrow crosses a durable file boundary and each PLAN / IMPLEMENT / VERIFY stage runs in a fresh specialist context.

The user should be interrupted only for a material architectural decision, an unrecoverable baseline mismatch, an exhausted remediation limit, or an external permission/environment failure that cannot be resolved autonomously.

The structural order remains unchanged:

```text
Existing proven deterministic core
        |
        v
Add WorkItem identity
        |
        v
Scope state to WorkItem
        |
        v
Resolve WorkItems safely
        |
        v
Bind Spec Kit to WorkItem
        |
        v
Add policy/risk/classification
        |
        v
Introduce adaptive flows
        |
        v
Add brownfield convergence
        |
        v
Harden and remove legacy assumptions
```

**Do not rewrite SDLE. Evolve the current deterministic core until the WorkItem model becomes the new stable spine.**
