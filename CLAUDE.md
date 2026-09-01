# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

This is the **source repository for SDLE (Spec Driven Lifecycle Engine)** — a Claude Code skill that orchestrates a gated SDLC workflow wrapping GitHub SpecKit.

As of v1.16 the lifecycle is **selected, not fixed**. `PHASE_SEQUENCE` is a 21-entry phase
*registry*; a **flow** is an ordered subset of it, and a WorkItem traverses exactly one,
bound once at `init` from its governance record. Five flows ship: `GREENFIELD`
(18 phases, 8 gates — the pre-v1.16 lifecycle, frozen in `GREENFIELD_V1_PHASES` in
`sdle.py` rather than declared in a table, so a new registry row can never silently
join it), `BROWNFIELD_DISCOVERY`, `ITERATIVE`, `DEFECT_FIX` and `HOTFIX`, the last four
declared in SKILL.md's `FLOW_PHASES`. Every flow retains a mandatory ten-phase
governance floor: shorter, never ungoverned. See
`docs/architecture/ADR-004-declarative-flow-model.md`.

`BROWNFIELD_DISCOVERY` carries the gateless `discovery` phase, which reads an existing
repository into a validated, classified record, and a `GREENFIELD` or
`BROWNFIELD_DISCOVERY` completion establishes the repository baseline at
`.sdle/baseline.json`. That baseline is what makes discovery happen **once**: later
WorkItems converge onto `ITERATIVE` against it, enforced at `init` by refusal rather
than by convention. See
`docs/architecture/ADR-005-brownfield-discovery-and-baseline.md`.

As of v1.13 it is no longer prompt files alone. The mechanical layer lives in `scripts/sdle.py`; the prompt files carry judgement, presentation and the constant tables the script parses.

**Validation** is `pytest` plus `scripts/sdle.sh lint-skill`. The repo carries a test fixture (`requirements/todo-api.md`) so the workflow can also be exercised in place by saying `start workflow`. Runtime artifacts from such runs (`.specify/`, `design/`, `reviews/`, `clarifications/`, and the transitional legacy `.workflow/`) are gitignored — never commit them. WorkItem records under `workitems/` are the exception: they are **versioned** by design, and only `workitems/*/.sdle/lock` and the developer-local `workitems/.active-context.json` are ignored.

## Architecture

**`scripts/sdle.py`** — the deterministic core. Single file, Python 3.11+, standard library only, cross-platform. Owns flow selection and state transitions, gate enforcement, SHA fingerprinting, the audit hash chain, drift detection, the session lock, rate limits, migration, the untrusted-content scan, the implementation manifest, and `lint-skill`.

- **JSON on stdout, human text on stderr.** Callers parse; they do not interpret prose.
- **Exit codes are the contract:** `0` success · `1` refused · `2` usage · `3` integrity failure.
- **It refuses; it does not warn.** A refusal is final. Nothing may work around it.
- Invoke through `scripts/sdle.sh` (POSIX) or `scripts/sdle.ps1` (PowerShell), which resolve the interpreter. See `scripts/README.md`.

**`.claude/skills/sdle/`** — the prompt files, split for lazy loading:

- **`SKILL.md`** — orchestrator entry point, always loaded. Core rules, verbosity, command routing, and the **Internal Constants** the script parses out of it.
- **`modules/phase-execution.md`** — per-phase generation logic. Loaded when executing a phase.
- **`modules/gate-protocol.md`** — gate display and rejection/remediation. Loaded at gate phases.
- **`modules/security-review.md`** — Phase 17 review template. Loaded at Phase 17.
- **`templates/state.json`** — the initial state template. The **only** copy; SKILL.md must not embed a second one.

**`.claude/commands/`** — nine `/sdle-*` slash commands. Invocation and presentation only: no business logic, no restated constants, no restated header format.

**`.claude/hooks/`** + **`.claude/settings.json`** — four guardrail hooks. Hooks are *tripwires*; where they overlap the script, the script's refusal at the choke point is the guarantee.

Runtime state is WorkItem-scoped: it lives in the *target project's* `workitems/<workitem-id>/.sdle/state.json` plus an append-only `audit.md`, `lock`, `execution.json` and `evidence/` beside it. The repository-global `.workflow/` is transitional — it is still read when a repository has a pre-v1.14 workflow and no WorkItem registered, and `migrate-workflow --workitem <id>` moves it under a WorkItem without ever mutating it.

Repository-wide **configuration** is a separate boundary: a versioned `.sdle/` at the project root holding `config.json`, `policies/`, `templates/` and `implementation-state/`, derived from `project_root` alone and never from the bound WorkItem, managed by `config init` / `config show` and policed in both directions by `validate`. It confusingly shares a name with the WorkItem runtime directory and owns nothing in common with it; no lifecycle rule lives there and nothing in any lifecycle flow reads it. See `docs/architecture/ADR-002-repository-configuration-boundary.md`.

SpecKit's WorkItem-specific artifacts are scoped the same way — a WorkItem's feature directory is `workitems/<workitem-id>/specs/<feature-id>/`, discovered and moved there by `feature resolve` and recorded in `state.specKit.featureDirectory` — while genuinely repository-wide SpecKit scaffolding, `.specify/` including `memory/constitution.md`, stays at the repository root.

Which WorkItem is active is resolved, never guessed: explicit `--workitem`, then the launch directory, then a sole registered WorkItem, then the developer-local `workitems/.active-context.json`, then a unique Git-branch match. More than one plausible candidate is always a refusal that lists them — the question goes to the user in the parent session (invariant 8), and `workitem resolve` is the diagnostic that supplies the candidates. `sdle validate` checks the registry itself and runs even where resolution cannot.

## Non-Negotiable Design Invariants

Any edit must preserve these — they are the product:

1. **State first** — read state before any action; emit the state assertion header first.
2. **Gate discipline** — never advance past a gate without explicit `approve`; no forward jumps.
3. **SpecKit opacity** — `speckit-*` names and `/speckit.*` commands are never shown (verbose mode excepted).
4. **Gate content in conversation** — artifact content is displayed at every gate; the user never opens a file to approve.
5. **Fail safe** — on any failure, freeze; never advance the phase.
6. **Single writer** — only the orchestrator, via `sdle.py`, writes `state.json` and `audit.md`. The audit chain and drift detection assume it. The write-fence hook enforces it.
7. **One source of truth per fact** — each constant exists in exactly one place. Prompt files reference; they do not restate.
8. **Gates stay in the parent** — a gate needs artifact content in conversation for a human decision. Nothing holding a gate may be delegated to a subagent.

## Cross-File Sync — run the linter, do not check by hand

`scripts/sdle.sh lint-skill` verifies every rule that used to be a manual checklist:

- NEXT_PHASE and PHASE_LABEL_MAP cover the registry's phase set exactly, and NEXT_PHASE chains PHASE_SEQUENCE in order
- PROGRESS_MAP covers the **GREENFIELD flow's** phase set exactly — it is the GREENFIELD view, not the registry's
- every PROGRESS_MAP denominator equals GREENFIELD's phase count, and no fraction is hardcoded in instruction text for *any* flow's denominator — a literal `N/18` is wrong for four lifecycles out of five
- every gate is registered in PHASE_TO_GATE_KEY, ARTIFACT_OWNERSHIP, GATE_TO_EXECUTION_PHASE and the state template's `approvals`
- exactly one state template exists
- the version string agrees across SKILL.md frontmatter and heading, README title and version table, `templates/state.json`, and the Reference Guide header
- every state field has a migration row
- every phase has a block in `phase-execution.md`, and every block ordinal is that phase's GREENFIELD position
- `FLOW_PHASES` declares the four non-GREENFIELD flows, each an ordered subset of the registry that starts at `requirements_check`, ends at `complete` and keeps every mandatory phase
- every registry phase is named by at least one flow — a phase no flow runs fails loudly instead of joining GREENFIELD by default
- PROGRESS_MAP's values and PHASE_TO_GATE_KEY's gate numbers equal the derived GREENFIELD views
- no gate label re-hardcodes its ordinal: each carries `{gate_number}`, substituted per bound flow
- no PowerShell-only cmdlet remains in any prompt file
- README and the Reference Guide list every phase

It runs in CI on `ubuntu-latest` and `windows-latest`. If it cannot parse a constant table it fails loudly rather than defaulting — a table that silently parsed to nothing would let `advance` compute a wrong next phase and fail open.

**Adding a phase or gate:** edit the tables in SKILL.md, add the `phase-execution.md` block, **name the phase in at least one `FLOW_PHASES` row** — or, to put it in GREENFIELD, edit `GREENFIELD_V1_PHASES` in `sdle.py`, which is deliberately a loud change — update the docs, then run the linter and the suite. **Changing the state schema** additionally needs a new `VERSION_MIGRATION` row and a matching migration step in `sdle.py`.

## Testing

```
python -m pytest -q                # units, 9 transcript integrations, hooks
python scripts/sdle.py lint-skill  # cross-file sync rules
```

`docs/dry-runs/01..09` are the behavioural specification: one integration test per transcript. Tests never invoke SpecKit — generation is simulated by writing an artifact over the size floor — and fixtures are always generated at runtime, never read from the checkout, because hashing a checked-in file makes results depend on line endings.

## Platform Note

The engine is cross-platform. Embedded commands in prompt files must be too — `lint-skill` fails on PowerShell-only cmdlets. Where a shell wrapper genuinely needs to be platform-specific, ship both (`sdle.sh` and `sdle.ps1`).

## Historical Context

`docs/architecture/ADR-001-deterministic-core.md` records why the mechanical layer moved into code, what was rejected, and every deliberate divergence from v1.12 behaviour.
