# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

This is the **source repository for SDLE (Spec Driven Lifecycle Engine)** — a Claude Code skill that orchestrates a gated 18-phase SDLC workflow wrapping GitHub SpecKit.

As of v1.13 it is no longer prompt files alone. The mechanical layer lives in `scripts/sdle.py`; the prompt files carry judgement, presentation and the constant tables the script parses.

**Validation** is `pytest` plus `scripts/sdle.sh lint-skill`. The repo carries a test fixture (`requirements/todo-api.md`) so the workflow can also be exercised in place by saying `start workflow`. Runtime artifacts from such runs (`.workflow/`, `.specify/`, `design/`, `reviews/`, `clarifications/`) are gitignored — never commit them.

## Architecture

**`scripts/sdle.py`** — the deterministic core. Single file, Python 3.11+, standard library only, cross-platform. Owns state transitions, gate enforcement, SHA fingerprinting, the audit hash chain, drift detection, the session lock, rate limits, migration, the untrusted-content scan, the implementation manifest, and `lint-skill`.

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

Runtime state lives in the *target project's* `.workflow/state.json` plus an append-only `audit.md`.

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

- the four phase tables cover an identical phase set, and NEXT_PHASE chains PHASE_SEQUENCE exactly
- PROGRESS_MAP denominators equal the derived phase count; no hardcoded `N/18` in instruction text
- every gate is registered in PHASE_TO_GATE_KEY, ARTIFACT_OWNERSHIP, GATE_TO_EXECUTION_PHASE and the state template's `approvals`
- exactly one state template exists
- the version string agrees across SKILL.md frontmatter and heading, README title and version table, `templates/state.json`, and the Reference Guide header
- every state field has a migration row
- every phase has a block in `phase-execution.md`
- no PowerShell-only cmdlet remains in any prompt file
- README and the Reference Guide list every phase

It runs in CI on `ubuntu-latest` and `windows-latest`. If it cannot parse a constant table it fails loudly rather than defaulting — a table that silently parsed to nothing would let `advance` compute a wrong next phase and fail open.

**Adding a phase or gate:** edit the tables in SKILL.md, add the `phase-execution.md` block, update the docs, then run the linter and the suite. **Changing the state schema** additionally needs a new `VERSION_MIGRATION` row and a matching migration step in `sdle.py`.

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
