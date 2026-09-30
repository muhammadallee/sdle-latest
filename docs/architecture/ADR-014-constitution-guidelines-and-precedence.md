# ADR-014 — The constitution as engineering profile, guidelines as advice, and the precedence chain

**Status:** Accepted
**Relates to:** ADR-003 (governance inputs and artifact review), ADR-007 (progressive capabilities and product subagents), ADR-013 (project architecture memory and placement)

---

## Context

ADR-013 gives SDLE a phase whose whole job is judgement: deciding where a capability lives. Judgement needs inputs, and the moment a phase has five plausible inputs it needs a stated order among them — or the model picks whichever it read last.

Three questions had to be answered before the placement phase could be trusted:

1. **Where do a project's engineering rules live?** The placement phase needs to know whether the project has decided on a platform, which technologies are permitted, and which decisions are deliberately left open per WorkItem.
2. **Where do SDLE's own heuristics live, and what authority do they have?** "Prefer extending an existing service" is product knowledge worth shipping. It is not a rule the project agreed to.
3. **What wins when they disagree?**

## Decision

### 1. The constitution is the engineering profile. There is no second artifact.

SDLE already generates and gates a constitution. It is the project's single engineering contract, and it is where the engineering profile belongs. **We do not add a mandatory `engineering-profile.md`.**

A generated constitution MUST distinguish five categories:

| Category | Meaning | What it licenses downstream |
|---|---|---|
| **Mandatory** | Required. No WorkItem may deviate | a design may assume it without argument |
| **Preferred** | The default unless a WorkItem justifies otherwise | a deviation is allowed, but must be stated and reasoned |
| **Available** | Permitted for justified use. **Not automatically selected** | choosing it requires a reason; not choosing it requires none |
| **Prohibited** | Never | a design that needs it is wrong, not exceptional |
| **Architecture decision required** | Must be decided explicitly, per WorkItem | the constitution deliberately does not answer it |

**"Available" is the category that carries the decision's weight.** A broker or a cache listed as available is *permitted*, not *chosen*. Without the distinction, every technology a constitution mentions reads as an endorsement, and a later phase adopts it because it was written down. Typical members of the last category — service boundaries, synchronous versus asynchronous integration, broker choice, caching, orchestration versus choreography, persistence per service — are exactly the questions ADR-013's placement phase exists to answer per WorkItem.

**Structure comes from SDLE; values come from the project**, through `guidance/constitution.md`, the bound requirements and the user. No technology is ever hard-coded into the generated document.

### 2. Guidelines are trusted product content, lazily loaded, and advisory

Built-in heuristics live in `.claude/skills/sdle/guidelines/`, one file per phase that needs them, mapped in `CAPABILITY_MAP` and loaded only when that phase runs:

```
constitution.md · architecture-placement.md · service-planning.md
task-generation.md · service-design.md · implementation.md
```

They are ordinary capability files: `lint-skill` requires each to exist, to be inside the prompt-content checks, and to be named by a row. **A guideline no row names is an orphan and fails** — an unmapped guideline reads like shipped product knowledge while never reaching a phase, which is worse than not shipping it.

Project-level `guidance/architecture-placement.md` remains optional and **untrusted**: it flows through the existing Guidance File Map, is scanned before use, and is data rather than instruction. **Two levels, never merged.** A project cannot edit SDLE's heuristics, and SDLE's heuristics cannot silently absorb a project's.

The set is kept small on purpose. Dozens of tiny guideline files would reintroduce, in the prompt layer, exactly the "which file decides this?" problem `CAPABILITY_MAP` was built to remove.

### 3. The precedence chain

```
1 approved requirements
2 the constitution
3 approved architecture decisions
4 the approved spec / design of this WorkItem
5 SDLE guidelines
6 agent judgement
```

Read top down. A guideline never overrides an approved artifact. When 1–4 are silent and a guideline decides it, **the rationale says so** — which is what makes the decision reviewable rather than merely plausible.

Position 3 is the one this ordering adds, and it is placed above this WorkItem's own artifacts deliberately: an approved architecture decision is a repository-level commitment, and a specification that contradicts it is a defect in the specification.

Position 6 exists because pretending it does not is how unattributed judgement gets laundered into apparent policy. It is last, and it is always stated as such.

---

## Rejected alternatives

**A separate mandatory `engineering-profile.md`.** Rejected. It would be a second gated artifact covering the same ground as the constitution, with two ways for them to disagree and no rule for which wins. The constitution is already generated, already gated, already versioned and already read by the phases that need it; the gap was never a missing file, it was a missing *structure* inside the file. That is what the five categories supply.

**Guidelines as rules.** Rejected. A heuristic promoted to a rule stops being falsifiable: "prefer extending an existing service" is good advice and a terrible constraint, because the cases it gets wrong are precisely the ones that matter. Advisory placement keeps the burden where it belongs — on the rationale.

**Merging project guidance into the built-in guidelines.** Rejected. Merged text has no provenance: a reviewer cannot tell which sentence the product shipped and which the project wrote, and an untrusted document would gain the standing of trusted product content by concatenation.

**No stated precedence, left to judgement.** Rejected. With five inputs and no order, the model's answer depends on read order, and two runs over the same repository can legitimately differ. A stated chain makes disagreement about the *inputs* rather than about the procedure.

---

## Consequences

**We accept** that a constitution is now load-bearing for two placement outcomes: creating a service and extracting a capability both require one, because both establish a boundary the constitution is what governs. A repository with no constitution can still run a defect fix that introduces no new boundary, no ownership transfer and no new technology decision — and if the missing constitution prevents a defensible placement, the outcome is `ARCHITECTURE_REVIEW_REQUIRED` rather than a guess. The placement artifact never synthesizes a substitute constitution.

**We accept** six more prompt files to maintain, and the lint rules that keep them reachable.

**We gain** one home for engineering rules, a stated order among the inputs to every judgement phase, and a distinction — available versus selected — that stops a constitution from reading as a shopping list.
