# SDLE documentation

Every document in this repository, and who it is for.

**New here?** Read [GETTING-STARTED.md](GETTING-STARTED.md). It is the one end-to-end setup guide: prerequisites, installing SDLE into your project, the first `start workflow`, and what to do when it does not start.

---

## SDLE in four ideas

Everything else in this set is detail on one of these.

1. **A WorkItem is the unit of work.** One feature, one defect, one hotfix. Each has its own directory under `workitems/`, its own state, its own append-only audit ledger and its own lock. Two WorkItems in one repository cannot see or corrupt each other's runtime.
2. **A flow decides which phases run.** A phase *registry* holds every phase SDLE can execute; a *flow* is an ordered subset of it. Five ship: `GREENFIELD`, `BROWNFIELD_DISCOVERY`, `ITERATIVE`, `DEFECT_FIX` and `HOTFIX`. The flow is chosen once, when the WorkItem starts, and never re-bound. A shorter flow is shorter, never ungoverned. Ask the engine for exact phase and gate counts (`sdle.sh constants`).
3. **Gates are where a human decides.** A gate halts the workflow and shows you the artifact in the conversation; you approve, or reject with feedback and it remediates. Which gates are *required* depends on assessed risk, and some floors cannot be lowered by the model.
4. **The engine refuses; it does not warn.** The mechanical layer is `scripts/sdle.py`: state transitions, gate enforcement, artifact fingerprints, the audit hash chain, drift detection and locking. When something is wrong it exits non-zero and does nothing. The prompts are presentation.

SDLE is an orchestrator for Claude Code wrapping [GitHub Spec Kit](https://github.com/github/spec-kit). You never type a Spec Kit command. It is not a CI system, not a project tracker, and not autonomous: it stops at every gate the risk policy requires.

---

## The kinds of document

They are written for different readers and should not be confused:

| Kind | Answers | You are |
|---|---|---|
| **Concept** | "What is this and how does it fit together?" | Deciding whether to use it |
| **Tutorial** | "How do I do this the first time?" | Learning, with time to read |
| **Runbook** | "It is broken — what do I type?" | Under pressure, need steps |
| **Reference** | "What exactly does this field do?" | Looking one thing up |

The **dry runs** are a fifth category: checked artifacts, not reading material. They are simulated transcripts; the test suite recomputes the progress fractions, gate numbers and labels, the refusal names and the cited test nodes in them from the engine, and does not execute the conversations.

## Start

| Document | Kind | For |
|---|---|---|
| [GETTING-STARTED.md](GETTING-STARTED.md) | Tutorial | Setup from prerequisites to the first `start workflow` |
| [../README.md](../README.md) | Concept | What SDLE is, the flows, the command lookup table |

## Learn

| Document | Kind | For |
|---|---|---|
| [tutorials/](tutorials/README.md) | Tutorial | One walkthrough per flow, plus a `GREENFIELD` tour of every customization surface. Start with the flow-selection page if you are unsure which flow you need |

## Understand a subject

Each is a focused explanation of one part of the engine.

| Document | Kind | Covers |
|---|---|---|
| [workitems/](workitems/README.md) | Concept | The unit of work: identity, the registry, per-WorkItem runtime, resolution, isolation |
| [lifecycle/](lifecycle/README.md) | Concept | The phase registry, the five flows, gates, and how a flow is bound |
| [risk-and-gates/](risk-and-gates/README.md) | Concept | How risk is assessed, the hard floors Claude cannot lower, and how the required gate set is derived |
| [brownfield/](brownfield/README.md) | Concept | Discovery over an existing codebase, the repository baseline, and convergence onto `ITERATIVE` |
| [spec-kit-integration/](spec-kit-integration/README.md) | Concept | How Spec Kit is bound to a WorkItem, capability detection, and why its commands never surface |

## Recover from a problem

| Document | Kind | For |
|---|---|---|
| [troubleshooting/](troubleshooting/README.md) | **Runbook** | Refusals and what they mean, corrupt state, broken audit chains, stale baselines, lock conflicts, an unsupported state version |

## Look something up

| Document | Kind | For |
|---|---|---|
| [SDLE-Reference-Guide.md](SDLE-Reference-Guide.md) | Reference | The canonical reference. Every phase in order, the full state schema, the glossary, and worked end-to-end examples |

## Understand the decisions

Architecture decision records: what was decided, what was rejected, and why.

| ADR | Subject |
|---|---|
| [ADR-001](architecture/ADR-001-deterministic-core.md) | Why the mechanical layer moved out of prompts into code |
| [ADR-002](architecture/ADR-002-repository-configuration-boundary.md) | The repository-level `.sdle/` configuration boundary |
| [ADR-003](architecture/ADR-003-governance-inputs-and-artifact-review.md) | Governance inputs, hybrid risk, and artifact review |
| [ADR-004](architecture/ADR-004-declarative-flow-model.md) | Flows as ordered subsets of a phase registry |
| [ADR-005](architecture/ADR-005-brownfield-discovery-and-baseline.md) | Brownfield discovery and the repository baseline |
| [ADR-006](architecture/ADR-006-risk-adaptive-gate-policy.md) | Risk-adaptive gates without weakening governance |
| [ADR-007](architecture/ADR-007-progressive-capabilities-and-product-subagents.md) | Progressive capabilities and read-only product subagents |
| [ADR-008](architecture/ADR-008-v1-convergence-and-legacy-removal.md) | WorkItem-scoped runtime and the retired global runtime |
| [ADR-009](architecture/ADR-009-gate-evidence-and-execution-identity.md) | Gate evidence, change selection and execution identity |
| [ADR-010](architecture/ADR-010-no-state-migration.md) | No state migration: another schema is refused, the retired runtime is detected |
| [ADR-011](architecture/ADR-011-pinned-governance-policy.md) | The policy a WorkItem started under is pinned, so relaxing it mid-run cannot drop a gate |

## Specification — not documentation

| Document | For |
|---|---|
| [dry-runs/](dry-runs/README.md) | Conversation transcripts that are the **acceptance specification** for orchestrator behaviour: guardrail scenarios for `GREENFIELD`, one per other shipped flow, and focused evidence, manifest and execution-identity cases. [`verification-matrix.md`](dry-runs/verification-matrix.md) maps each to the tests that back it and to the runs that were actually executed |

---

## Contributing to these documents

Rules the engine enforces mechanically, so a change that breaks one fails `lint-skill` rather than drifting silently:

1. **Every subject directory must exist and say something**: `documentation_set_is_present`.
2. **Every flow size stated in a document must match the engine**: the phase count *excluding* the terminal `complete`, which is what the progress header shows.
3. **A stated version must match the state schema.** A page need not state one; if it does, `version_string_consistent` checks it. Do not restate a constant the engine already owns; link to it instead.
4. **Commands in these documents must be real**: the documented-commands test parses them and runs them against the parser.
