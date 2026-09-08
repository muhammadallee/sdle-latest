# Migration record — how SDLE reached V1

**This directory is a historical record. It is not part of the SDLE product.**

Nothing here is needed to install SDLE, to operate it, or to understand what it
does today. Delete this directory and the engine, the skill, the commands, the
hooks and the entire test suite behave identically. Read it only to understand
*how* SDLE got to where it is.

## What SDLE actually is

The product is these five things, none of which live here:

| Path | What it is |
|---|---|
| `scripts/` | `sdle.py`, the deterministic core, plus its two launchers |
| `.claude/skills/sdle/` | the orchestrator prompt files |
| `.claude/commands/` | the nine `/sdle-*` slash commands |
| `.claude/hooks/` + `.claude/settings.json` | the guardrail hooks and their registration |
| `.claude/agents/sdle-*.md` | the four read-only product subagents |

`README.md` at the repository root is the installation and usage entry point,
and `docs/README.md` indexes the documentation that describes the product as it
stands. Neither depends on anything in this directory.

## What this directory records

The twelve-phase migration (T00–T11) that took SDLE from a repository-global
`.workflow/` runtime to the WorkItem-scoped V1 runtime. Every phase was
planned, implemented, and then independently verified in a separate context,
and each of those artifacts is kept:

| Path | Contents |
|---|---|
| `transition.md` | the migration contract: the target behaviour every phase was held to |
| `baseline.md` | the pre-migration behavioural inventory the contract was written against |
| `progress.md` | the per-phase status ledger |
| `phases/` | per-phase plans, handoffs, checkpoints, blockers and independent verification artifacts |
| `templates/` | the fixed shapes those artifacts had to take |
| `control-plane.sha256` | the integrity manifest of the migration tooling |
| `RESUME.md` | the cold-start note for resuming the migration; explicitly non-authoritative |

These are **dated evidence**. Each describes the repository as it stood at the
moment that phase ran, so they will disagree with the current tree in places.
That is correct and deliberate: they are not documentation of the product and
are not maintained to track it. Where they conflict with the root `README.md`,
the Reference Guide, or the code, the code wins.

## The migration tooling has been removed

The control plane that produced these artifacts was deleted once the migration
completed at 12/12:

- `tools/transition/validate.py` and `tools/transition/agent_guard.py`
- the four `.claude/agents/sdle-transition-*.md` agents
- `.claude/skills/apply-sdle-transition/`
- the four root kickoff and kit files

Two consequences, stated here rather than left to be discovered:

1. **`progress.md` can no longer be machine-validated.** `validate.py` parsed
   the ledger and refused an inconsistent one. With the migration finished
   there is no live state left to keep consistent, so the file is now prose
   like everything else in this directory.
2. **`control-plane.sha256` hashes files that no longer exist.** It is kept as
   a record of what the tooling was, not as a manifest anyone can verify.

No product code ever invoked either tool, and CI
(`.github/workflows/ci.yml`) runs only `lint-skill` and the test suite.
