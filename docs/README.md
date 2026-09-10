# SDLE documentation

**Applies to:** SDLE v1.17

Every document in this repository, and who it is for. If you are new,
[**START-HERE.md**](START-HERE.md) explains what SDLE is in about two minutes
and routes you from there.

---

## The four kinds of document

They are written for different readers and should not be confused:

| Kind | Answers | You are |
|---|---|---|
| **Concept** | "What is this and how does it fit together?" | Deciding whether to use it |
| **Tutorial** | "How do I do this the first time?" | Learning, with time to read |
| **Runbook** | "It is broken — what do I type?" | Under pressure, need steps |
| **Reference** | "What exactly does this field do?" | Looking one thing up |

The **specification** documents below are a fifth category, and a special one:
they are not written for readers at all. They are frozen artifacts the test
suite asserts against.

---

## Start

| Document | Kind | For |
|---|---|---|
| [START-HERE.md](START-HERE.md) | Concept | Anyone, first. What SDLE is, the four ideas, where to go next |
| [../README.md](../README.md) | Reference | Installing it, and the command lookup table |

## Learn

| Document | Kind | For |
|---|---|---|
| [tutorials/](tutorials/README.md) | Tutorial | A walkthrough per flow, plus a GREENFIELD tour of every customization surface. Start with the flow-selection page if you are unsure which flow you need |

## Understand a subject

Each of these is a focused explanation of one part of the engine.

| Document | Kind | Covers |
|---|---|---|
| [workitems/](workitems/README.md) | Concept | The unit of work: identity, the registry, per-WorkItem runtime, resolution, isolation |
| [lifecycle/](lifecycle/README.md) | Concept | The 21-phase registry, the five flows, gates, and how a flow is bound |
| [risk-and-gates/](risk-and-gates/README.md) | Concept | How risk is assessed, the hard floors Claude cannot lower, and how the required gate set is derived |
| [brownfield/](brownfield/README.md) | Concept | Discovery over an existing codebase, the repository baseline, and convergence onto `ITERATIVE` |
| [spec-kit-integration/](spec-kit-integration/README.md) | Concept | How SpecKit is bound to a WorkItem, capability detection, and why its commands never surface |

## Recover from a problem

| Document | Kind | For |
|---|---|---|
| [troubleshooting/](troubleshooting/README.md) | **Runbook** | Refusals and what they mean, corrupt state, broken audit chains, stale baselines, lock conflicts, recovery from a legacy layout |

## Look something up

| Document | Kind | For |
|---|---|---|
| [SDLE-Reference-Guide.md](SDLE-Reference-Guide.md) | Reference | The canonical reference. Every phase in order, the full state schema, the glossary, and worked end-to-end examples |

## Understand the decisions

Architecture Decision Records: what was decided, what was rejected, and why.
Each is a dated record — where later work superseded one, a note says so
rather than the original being rewritten.

| ADR | Subject |
|---|---|
| [ADR-001](architecture/ADR-001-deterministic-core.md) | Why the mechanical layer moved out of prompts into code |
| [ADR-002](architecture/ADR-002-repository-configuration-boundary.md) | The repository-level `.sdle/` configuration boundary |
| [ADR-003](architecture/ADR-003-governance-inputs-and-artifact-review.md) | Governance inputs, hybrid risk, and artifact review |
| [ADR-004](architecture/ADR-004-declarative-flow-model.md) | Flows as ordered subsets of a phase registry |
| [ADR-005](architecture/ADR-005-brownfield-discovery-and-baseline.md) | Brownfield discovery and the repository baseline |
| [ADR-006](architecture/ADR-006-risk-adaptive-gate-policy.md) | Risk-adaptive gates without weakening governance |
| [ADR-007](architecture/ADR-007-progressive-capabilities-and-product-subagents.md) | Progressive capabilities and read-only product subagents |
| [ADR-008](architecture/ADR-008-v1-convergence-and-legacy-removal.md) | V1 convergence and removal of the legacy runtime |

## Specification — not documentation

| Document | For |
|---|---|
| [dry-runs/](dry-runs/README.md) | Thirteen conversation transcripts that are the **acceptance specification** for orchestrator behaviour, one per shipped flow plus nine guardrail scenarios. `tests/test_integration_01..09` and `test_integration_10_to_13` derive their assertions from them; two tests byte-pin the nine `GREENFIELD` ones. A deviation in a real run is a bug in the run or the skill files — not in the transcript |

## Migration record

| Document | For |
|---|---|
| [transition/](transition/) | The twelve-phase migration from the repository-global runtime to WorkItem-scoped V1. Plans, handoffs, checkpoints and independent verification artifacts for T00–T11. Historical: read it to understand how the engine reached its current shape, not to operate it |

## Verification records

| Document | For |
|---|---|
| [verification/defect-stabilization-01.md](verification/defect-stabilization-01.md) | The execution record of the D01–D06 defect-stabilization iteration: every reproduction, command, result and remaining limitation, with the verified commit. Read it to see what was actually proven, and on which platform |

---

## Contributing to these documents

Three rules the engine enforces mechanically, so a change that breaks one
fails `lint-skill` rather than drifting silently:

1. **Every subject directory must exist** — `documentation_set_is_present`.
2. **Every subject directory must be linked from this index** — an unlinked
   document is an invisible one.
3. **One version string.** If a document states which version it applies to,
   `version_string_consistent` checks it against the state template. Do not
   restate a constant the engine already owns; link to it instead.
