# SDLE Wave A — Claude Code Kickoff Task

**Repo:** `sdle-latest` — SDLE (Spec Driven Lifecycle Engine) v1.12
**Target version:** v1.13
**Wave:** A of C. Scope is deliberately narrow. Read §3 before doing anything.

---

## 1. Role

You are the maintainer of an existing, working product. This is **not** a greenfield build and not a rewrite.

Apply these principles:

- **Determinism over judgment.** If a fact can be established mechanically, a script establishes it — never a model.
- **Preserve accumulated knowledge.** Every edge case in v1.12 exists because something broke. None of it is discarded without an explicit written reason.
- **Smallest coherent change.** No speculative abstraction, no new infrastructure without a demonstrated need.
- **Explicit over clever.** A dumb readable script beats an elegant one.
- **A guardrail that a model can talk itself out of is not a guardrail.**

---

## 2. Context — what SDLE is today

SDLE is a Claude Code skill that wraps GitHub SpecKit in a gated lifecycle. It is prompt files only — no code, no build, no tests, no CI.

```
.claude/skills/sdle/
├── SKILL.md                      906 lines — orchestrator, dispatcher, constants, state mgmt
├── modules/phase-execution.md    347 lines — per-phase logic, drift, idempotency
├── modules/gate-protocol.md      198 lines — gate display, rejection/remediation
├── modules/security-review.md     91 lines — Phase 17 template
└── templates/state.json           38 lines — initial state
docs/SDLE-Reference-Guide.md      854 lines — canonical reference
docs/dry-runs/01..09-*.md                   — 9 conversation transcripts (BEHAVIOURAL FIXTURES — see §8)
improvements.md                             — gap analysis; items 3,4,6,9,10,11,12,13 still open
CLAUDE.md                                   — invariants + cross-file sync rules
```

**18 phases, 8 gates.** State lives in the *target project's* `.workflow/state.json` with an append-only `audit.md`.

**Status:** not adopted by any user or team. No migration constraints. No backward compatibility obligations to anyone outside this repo.

---

## 3. The problem this wave solves

SDLE's guardrails — the state machine, gate enforcement, SHA fingerprinting, audit hash chain, drift detection, session lock, rate limits — are **prose in a 906-line prompt, interpreted by a model on every turn**. The mechanism that is supposed to constrain the model is advisory to it.

Secondary consequences of the same root cause:

1. **Seven hand-synced constant tables** (`PHASE_SEQUENCE`, `NEXT_PHASE`, `PHASE_TO_GATE_KEY`, `GATE_PHASES`, `ARTIFACT_OWNERSHIP`, `PHASE_LABEL_MAP`, `PROGRESS_MAP`) plus `templates/state.json` duplicated byte-for-byte inside SKILL.md, plus a version string in four files. `CLAUDE.md` documents the sync rules *for a human to follow by hand*. Every one is mechanically checkable.
2. **Natural-language dispatcher** pattern-matches ~15 verbs, including `approve` — the most safety-critical action in the product — with permanent misroute risk.
3. **PowerShell-only embedded commands** (`Get-FileHash -Algorithm SHA256`, `New-Item -ItemType Directory -Force`) block Linux/macOS users and all CI use.
4. **No automated test of any kind.** Validation today is "run the skill by hand and read the output."

**Wave A goal:** move the mechanical layer into a deterministic script, put explicit commands in front of it, make four guardrails into hooks, and get the whole thing under test in CI — with **externally identical behaviour to v1.12**.

---

## 4. Out of scope — do NOT do these in this wave

Listed explicitly because each is individually tempting:

- ❌ Brownfield reconnaissance, capability inventory, impact analysis (Wave B)
- ❌ Subagents of any kind (introduced in Wave B, with the new brownfield phases — nothing existing gets migrated to a subagent)
- ❌ Change-type routing (bugfix/refactor/modify/feature) — Wave C
- ❌ Requirement-level traceability — Wave C
- ❌ Adding, removing, renaming, or reordering any of the 18 phases or 8 gates
- ❌ Changing gate semantics, approval wording, or the artifacts each gate displays
- ❌ New state fields beyond what §6 specifies
- ❌ A new lifecycle model, artifact schema layer, or SDD quality engine
- ❌ Any dependency outside the Python standard library
- ❌ Any web UI, dashboard, or server

If you believe one of these is required to complete Wave A, **stop and say so with the specific blocking reason.** Do not proceed on your own judgment.

---

## 5. Non-negotiable invariants

The five from `CLAUDE.md` — preserve exactly:

1. **State first** — read `.workflow/state.json` before any action; emit the state assertion header first.
2. **Gate discipline** — never advance past a gate without explicit `approve`; no forward jumps.
3. **SpecKit opacity** — `speckit-*` names and `/speckit.*` commands are never shown to the user (verbose mode excepted).
4. **Gate content in conversation** — artifact content displayed at every gate; the user never opens a file to approve.
5. **Fail safe** — on any failure, freeze status; never advance the phase.

Three added by this wave:

6. **Single writer.** Only the orchestrator, via the script, writes `state.json` and `audit.md`. The `audit_sha` chain and drift detection assume serialized single-writer access.
7. **One source of truth per fact.** After this wave, each constant exists in exactly one place. Prompt files reference; they do not restate.
8. **Gates stay in the parent.** A gate requires artifact content displayed in conversation for a human decision. Nothing that holds a gate may be delegated.

---

## 6. Deliverable 1 — `scripts/sdle.py`

Single file. Python 3.11+. Standard library only. Cross-platform. This is the deterministic core.

### Design contract

- **JSON on stdout, human text on stderr.** Every subcommand emits a JSON object on stdout so the skill parses rather than interprets.
- **Exit codes are the contract:** `0` success · `1` refused (precondition failed — e.g. gate not approved) · `2` usage error · `3` integrity failure (state unreadable, audit chain broken, lock conflict).
- **The script refuses; it does not warn.** A refusal is exit 1 with a machine-readable reason. The skill surfaces it; the skill cannot override it.
- **Atomic writes.** Write temp + rename for `state.json`. Never leave a partial state file.
- **Idempotent.** Re-running any subcommand with the same arguments in the same state is safe.

### Subcommands

| Subcommand | Responsibility |
|---|---|
| `init --project <name>` | Create `.workflow/`, write initial state from the canonical template, first audit entry |
| `state get [--field F]` | Full state or one field as JSON |
| `header` | Render the `<!-- SDLE_STATE … -->` + `📋 SDLE Status:` block. **The script owns this string** — no prompt file restates it |
| `advance --to <phase>` | Validate against `PHASE_SEQUENCE`/`NEXT_PHASE`; **reject forward jumps and unapproved gate crossings**; update `current_phase`, `status`, `progress` from `PROGRESS_MAP`, `phase_history`, `last_updated`; audit |
| `gate approve --gate K [--comments T]` / `gate reject --gate K --reason T` | Record approval with artifact SHA; increment remediation counter on reject; enforce `rate_limits` |
| `sha <path>` | SHA-256 (replaces `Get-FileHash`) |
| `artifact record --phase P --path F` | Verify exists and ≥100 bytes, record SHA, audit. Refuse (exit 1) on failure |
| `drift check` | Compare recorded vs current SHAs; populate `drift_queue`; **include `git diff` when the artifact is git-tracked** (`improvements.md` item 12) |
| `audit append --phase P --event E --message M` | Append entry with `prev_sha` chaining; update `audit_sha` |
| `audit verify` | Walk and verify the chain; exit 3 on mismatch |
| `lock acquire` / `lock release` | `.workflow/lock` with session id + timestamp; refuse on a fresh foreign lock |
| `migrate` | Apply the version migration table; idempotent; audit each migration |
| `repo-staleness` | Commits since last approval, **scoped to paths of recorded artifacts** rather than repo-wide |
| `lint-skill` | Verify every cross-file sync rule in `CLAUDE.md` (see below) |

### `lint-skill` checks

Each is a distinct named check with its own failure message:

- `PHASE_SEQUENCE` ↔ `NEXT_PHASE` ↔ `PHASE_LABEL_MAP` ↔ `PROGRESS_MAP` cover the identical phase set
- `PROGRESS_MAP` denominators all equal the phase count; no hardcoded `N/18` anywhere outside `PROGRESS_MAP`
- every phase in `GATE_PHASES` appears in `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP`, `approvals` in **both** state templates, and `GATE_TO_EXECUTION_PHASE` in `gate-protocol.md`
- `templates/state.json` is byte-identical to the template embedded in SKILL.md Step 9
- version string matches across SKILL.md frontmatter + heading, README.md title + version table, `templates/state.json` `workflow_version`, Reference Guide header
- every state field written anywhere has a row in the version migration table
- every phase in `PHASE_SEQUENCE` has a block in `phase-execution.md`
- no PowerShell-only cmdlet remains in any prompt file

> Prefer parsing the constants out of SKILL.md over duplicating them in Python. If a table is not machine-parseable, **reformat the table** — do not fork the data.

---

## 7. Deliverables 2–4

### Deliverable 2 — Commands

Thin wrappers over `scripts/sdle.py`, in `.claude/commands/`:

`/sdle-start` · `/sdle-status` · `/sdle-continue` · `/sdle-approve` · `/sdle-reject` · `/sdle-restart` · `/sdle-reset` · `/sdle-skip` · `/sdle-verbose`

Rules:

- A command template contains **only** the invocation and how to present the result. Zero business logic, zero restated constants, zero restated header format.
- The skill remains for what isn't verb-shaped: clarification responses, free-text rejection reasons, `confirm skip`/`confirm reset` two-step confirmations, gate presentation.
- SKILL.md Step 4 (dispatcher) mostly deletes. Keep natural-language aliases routing to the same commands so existing phrasing still works.
- `improvements.md` item 6: replace all "hand-edit `state.json`" instructions with an audited command.

### Deliverable 3 — Hooks

The four guardrails that must execute regardless of model decisions, in `.claude/hooks/`:

| Hook | Guardrail | Source |
|---|---|---|
| `PreToolUse` (Write/Edit) | **Write-fence** — reject writes to `.workflow/`, `requirements/`, `guidance/`, approved `.specify/` artifacts | item 9 |
| `PreToolUse` (Bash, implement phase) | **Dirty-tree guard** — refuse implement on a dirty tree without recorded acknowledgement | v1.12, now enforced |
| `PostToolUse` (implement) | **Secrets scan** on the implementation diff, result written to the manifest before Gate 7 | item 2, now enforced |
| `PreToolUse` (Read of `requirements/`, `guidance/`) | **Untrusted-content scan** | v1.12, now enforced |

Each hook is a thin shell wrapper calling `sdle.py`. Hooks refuse and explain; they do not silently mutate state.

### Deliverable 4 — Two `improvements.md` items that belong here

- **Item 11 — test evidence at Gate 7.** If a test runner is detectable (`package.json` scripts, `pytest`, `mvn`, `gradle`, `cargo`), run it and include pass/fail output in the manifest. Today an implementation whose tests never ran can be approved. This is the largest single correctness hole in v1.12.
- **Item 3 — pin the security diff range.** Record `implementation_base_ref` (HEAD SHA) at Phase 15 start; Phase 17 diffs against that ref instead of `HEAD~1`.

Items 4, 10, 13 are deferred to Wave B. Items 12 and 6 are absorbed above.

---

## 8. Testing — the dry-run transcripts are your fixtures

`docs/dry-runs/01..09` are recorded conversation transcripts of v1.12 behaviour, covering happy path, gate rejection/remediation, technical failure retry/skip, artifact drift re-approval, untrusted-content scan, secrets and dirty tree, audit integrity and session lock, restart/reset/state jump, and bootstrap failures.

**Treat them as the behavioural specification.** For each transcript, extract the state transitions and derive an integration test asserting the same sequence of `state.json` values, audit entries and refusals. Where a transcript's behaviour is ambiguous or self-contradictory, record it in the deliverable of §10 rather than choosing silently.

Required:

- **Unit tests** — one per subcommand, including every refusal path (forward jump, unapproved gate, rate limit exceeded, broken audit chain, foreign lock, artifact <100 bytes)
- **Integration tests** — one per dry-run transcript, on a scratch fixture project
- **`lint-skill` self-test** — deliberately break each sync rule in a copied fixture; assert the corresponding check fires
- **CI** — GitHub Actions on push and PR: `pytest` + `sdle.py lint-skill`. Must run on `ubuntu-latest` and `windows-latest`

---

## 9. Definition of Done

- [ ] `scripts/sdle.py` implements every subcommand in §6; stdlib only; runs on Linux, macOS, Windows
- [ ] Exit-code contract honoured; every refusal is machine-readable
- [ ] Each of the seven constant tables + state template + version string exists in exactly ONE place
- [ ] `lint-skill` passes on the repo and fails on each deliberately broken fixture
- [ ] Zero PowerShell-only cmdlets remain in any prompt file
- [ ] 9 integration tests derived from the dry-run transcripts pass
- [ ] Unit coverage of every refusal path
- [ ] CI green on ubuntu-latest and windows-latest
- [ ] Four hooks enforce their guardrails and are proven by test to refuse
- [ ] Gate 7 manifest includes real test output when a runner is detectable
- [ ] Commands work; natural-language aliases still route correctly
- [ ] SKILL.md reduced substantially (**target: under 400 lines**) with no behaviour lost
- [ ] `CLAUDE.md`, `README.md`, Reference Guide updated to describe the script-owned architecture
- [ ] Version 1.13 consistent across all four locations; migration row added
- [ ] `docs/architecture/ADR-001-deterministic-core.md` records the decision and rejected alternatives

### Acceptance test

Run the full 18-phase workflow end-to-end on the `requirements/todo-api.md` fixture under v1.13. The transcript must be behaviourally equivalent to `docs/dry-runs/01-happy-path.md`. Every divergence is either a defect to fix or a deliberate change recorded in the ADR — no third category.

---

## 10. Required first response — then STOP

Before writing any code, produce:

1. **Behavioural inventory** — every mechanical behaviour currently specified in prose across the five prompt files, with file and line reference: state transitions, validations, refusals, SHA operations, audit operations, lock, drift, rate limits, migration, checkpoint recovery, idempotency, feature-ID resolution, post-generation verification.
2. **Mapping table** — each behaviour → the `sdle.py` subcommand, hook, command, or "stays in prompt" that will own it. Nothing unmapped.
3. **Ambiguities and contradictions found** — where prompt files disagree with each other, with `templates/state.json`, or with the dry-run transcripts. **Do not resolve these yourself; list them for a decision.**
4. **Exact `sdle.py` CLI surface** — signatures, JSON output shapes, exit codes.
5. **Constant-table parseability assessment** — which tables can be parsed as-is, which need reformatting, which must be duplicated in Python (with justification for each duplication).
6. **Files created / modified / deleted**, with reason.
7. **Test plan** — the state-transition sequence extracted from each dry-run transcript.
8. **Behaviour you propose to change**, if any, each with justification and blast radius. Default is zero.
9. **Risks**, ranked. Include what breaks if `lint-skill` cannot parse a table.
10. **Anything in §4 you believe blocks Wave A**, with the specific reason.

Then **STOP** and wait for review. Do not begin implementation.

---

## 11. Implementation discipline

Once approved, for each unit of work:

1. Write the test first, derived from the dry-run transcript or the prose being replaced
2. Implement the smallest change that passes it
3. Run `lint-skill`
4. Run the full suite
5. Remove the now-redundant prose from the prompt file **in the same commit** — a behaviour specified in two places will diverge
6. Update the docs that reference it

Commit per behaviour, not per file. Every commit leaves the suite green.

---

## 12. Final directive

The goal is **not** a better-architected SDLE. It is the **same SDLE, with its guardrails made real and its invariants made testable** — so that Waves B and C can add brownfield reconnaissance and change-type routing without hand-syncing seven tables and hoping a prompt is obeyed.

If a change makes the system more capable but not more verifiable, it is not part of this wave.
