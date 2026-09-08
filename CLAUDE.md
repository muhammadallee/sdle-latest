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

**Validation** is `pytest` plus `scripts/sdle.sh lint-skill`. The repo carries a test fixture (`requirements/todo-api.md`) so the workflow can also be exercised in place by saying `start workflow`. Runtime artifacts from such runs (`.specify/`, `design/`, `reviews/`, `clarifications/`, and the archival legacy `.workflow/`) are gitignored — never commit them. WorkItem records under `workitems/` are the exception: they are **versioned** by design, and only `workitems/*/.sdle/lock` and the developer-local `workitems/.active-context.json` are ignored.

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
- **`modules/design-review.md`** / **`modules/code-review.md`** — how those two reviews are conducted, what a finding looks like, and how the parent records the outcome.
- **`templates/state.json`** — the initial state template. The **only** copy; SKILL.md must not embed a second one.

Which capability files a phase requires is not a judgement the model makes each turn: it is the **`CAPABILITY_MAP`** table in SKILL.md, parsed by the script and reported by `sdle.sh resume`. The row is a floor, not a ceiling — a capability file may still point at another one. `lint-skill` fails on a missing row, an unknown phase, a file that does not exist, an orphan module, a row that names SKILL.md, a row that requires the whole set, or an unmapped cross-reference.

**`.claude/agents/`** — four read-only product subagents (`sdle-discovery`, `sdle-design-review`, `sdle-code-review`, `sdle-security-review`) for high-context independent analysis. They may inspect, reason and return findings; they may not mutate lifecycle state, approve a gate, bypass policy or become workflow controllers. That is enforced twice: a read-only `tools:` grant in each agent's frontmatter — the permitted set is `PRODUCT_AGENT_TOOLS` in `scripts/sdle.py`, not a literal restated here — and a `PreToolUse` fence in each agent's own frontmatter that denies every write and every command. `lint-skill` fails if either stops being true. Findings enter the governed record through one door the parent opens — `artifact review --actor-type agent --actor-name <agent>`. The `sdle-transition-*` files beside them are this repo's migration control plane, not the product.

**Two of those enforcement points are not SDLE's.** That a declared `tools:` list is applied, and that a frontmatter hook fires, are guarantees of the **Claude Code runtime**; SDLE checks the *declaration*, not the runtime's honouring of it. And three things remain **convention only**: that the parent delegates at all, that `--actor-name` truthfully names the producer, and that a human rather than the orchestrator typed `approve`. `docs/architecture/ADR-007-progressive-capabilities-and-product-subagents.md` §3 carries the full split; it must not be softened.

**`.claude/commands/`** — nine `/sdle-*` slash commands. Invocation and presentation only: no business logic, no restated constants, no restated header format.

**`.claude/hooks/`** + **`.claude/settings.json`** — five guardrail hooks. Hooks are *tripwires*; where they overlap the script, the script's refusal at the choke point is the guarantee. Four inspect the payload and stay silent when it does not concern them; the fifth, `product-agent-fence`, denies everything it is registered for and is registered in the four product agents' frontmatter rather than in `settings.json`, because it must bind those agents and not the parent session.

Runtime state is WorkItem-scoped: it lives in the *target project's* `workitems/<workitem-id>/.sdle/state.json` plus an append-only `audit.md`, `lock`, `execution.json` and `evidence/` beside it. The repository-global `.workflow/` is **archival**, not a runtime: as of v1.17 nothing binds it and nothing runs against it. It survives as exactly two things — a migration source for `migrate-workflow --workitem <id>`, which moves it under a WorkItem without ever mutating it, and a project-root marker, so a legacy-only repository can still be found. It stays write-fenced for that reason. See `docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md`.

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
- every flow size stated anywhere in the documentation set equals the engine's — the phase count **excluding** the terminal `complete`, which is what `FlowSpec.phase_count` reports and what the progress header shows. Checked in three claim shapes: a `| \`FLOW\` | N | M |` table row, a `**N phases, M gates.**` tutorial headline, and a `| \`FLOW\` | N phases, M gates |` index row. `docs/lifecycle/README.md` once counted `complete` and published 19/20/17/15/11 against five other documents' 18/19/16/14/10, which is why this is a rule and not a habit

It runs in CI on `ubuntu-latest` and `windows-latest`. If it cannot parse a constant table it fails loudly rather than defaulting — a table that silently parsed to nothing would let `advance` compute a wrong next phase and fail open.

**Adding a phase or gate:** edit the tables in SKILL.md, add the `phase-execution.md` block, **name the phase in at least one `FLOW_PHASES` row** — or, to put it in GREENFIELD, edit `GREENFIELD_V1_PHASES` in `sdle.py`, which is deliberately a loud change — update the docs, then run the linter and the suite. **Changing the state schema** additionally needs a new `VERSION_MIGRATION` row and a matching migration step in `sdle.py`.

## Testing

```
python -m pytest -q                # units, 9 transcript integrations, hooks
python scripts/sdle.py lint-skill  # cross-file sync rules
```

`docs/dry-runs/01..13` are the behavioural specification: one integration test per transcript. `01..09` are `GREENFIELD` and are byte-pinned against the T10 rollback point through an enumerated substitution list; `10..13` cover the other four flows and are pinned by their claims (`tests/test_integration_10_to_13.py`) rather than their bytes, because they postdate that rollback point. Tests never invoke SpecKit — generation is simulated by writing an artifact over the size floor — and fixtures are always generated at runtime, never read from the checkout, because hashing a checked-in file makes results depend on line endings.

## Platform Note

The engine is cross-platform. Embedded commands in prompt files must be too — `lint-skill` fails on PowerShell-only cmdlets. Where a shell wrapper genuinely needs to be platform-specific, ship both (`sdle.sh` and `sdle.ps1`).

## The Documentation Set

`lint-skill`'s `documentation_set_is_present` check requires each of these to exist and hold at least one non-empty document. A checklist rots; a lint rule does not.

| Path | Covers |
|---|---|
| `README.md` | The product, end to end |
| `CLAUDE.md` | This file — how to work on the repository |
| `docs/architecture/` | ADRs. Numbered, immutable once merged; the next number is ADR-009 |
| `docs/workitems/` | WorkItem identity, the registry, the resolution ladder, the legacy migration path |
| `docs/lifecycle/` | The phase registry, the five flows, gates and gate discipline |
| `docs/risk-and-gates/` | How the required gate set is derived from governance, and the floors |
| `docs/brownfield/` | Discovery, the repository baseline, and why discovery happens once |
| `docs/spec-kit-integration/` | Capability detection, feature-directory tiers, opacity |
| `docs/troubleshooting/` | Every refusal a user can hit, and the intended way out |

Each of them is a **derived view**. `scripts/sdle.py` and the constant tables in `SKILL.md` are the authority; where a document and the engine disagree, the document is the defect.

## Historical Context

`docs/architecture/ADR-001-deterministic-core.md` records why the mechanical layer moved into code, what was rejected, and every deliberate divergence from v1.12 behaviour. `docs/architecture/ADR-008-v1-convergence-and-legacy-removal.md` records the V1 convergence: what the legacy removal took out, what it deliberately kept, and every finding the migration closed or deferred.
