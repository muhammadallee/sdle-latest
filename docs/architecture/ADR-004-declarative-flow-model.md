# ADR-004 — A declarative flow model: the phase sequence becomes a registry, and a flow becomes what a WorkItem traverses

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-31 |
| **Scope** | Migration phase T07 (transition contract §13). Engine version v1.15 → v1.16. |

## Context

Up to v1.15 SDLE had exactly one lifecycle. `PHASE_SEQUENCE` in `SKILL.md`
listed nineteen phases, `NEXT_PHASE` chained them, `PROGRESS_MAP` numbered them
`N/18`, `PHASE_TO_GATE_KEY` numbered the gates `1..8`, and every traversal
function in `scripts/sdle.py` read that chain directly. The sequence was not a
*choice* the engine made; it was the only thing the engine could do.

That is wrong for most real work. A hotfix to a running system does not need a
freshly drafted constitution. An iterative change to an established codebase
does not need the repository rediscovered. A defect fix needs something a
greenfield project does not: an honest reading of what the change will touch,
*before* anyone writes a specification. Contract §13 asks for engineering flows
— GREENFIELD, BROWNFIELD_DISCOVERY, ITERATIVE, DEFECT_FIX, HOTFIX — each
executing a different subset of phases, and states the constraint that makes it
safe: **shorter, but never ungoverned.**

T06 had already recorded an `classification.flow` on every WorkItem and marked
it advisory, because nothing consumed it. This is the phase that makes it bind.

## Decision

**`PHASE_SEQUENCE` becomes a phase *registry*: the closed catalogue of phases
SDLE knows how to execute, in canonical order. A *flow* is an ordered subset of
the registry, and a WorkItem traverses exactly one.** After this change the
registry has twenty entries and **no flow has all twenty**.

Five flows:

| Flow | Phases | Gates | Source |
|---|---:|---:|---|
| `GREENFIELD` | 18 | 8 | `GREENFIELD_V1_PHASES`, frozen in `scripts/sdle.py` |
| `BROWNFIELD_DISCOVERY` | 18 | 8 | `FLOW_PHASES` in `SKILL.md` |
| `ITERATIVE` | 16 | 7 | `FLOW_PHASES` |
| `DEFECT_FIX` | 14 | 6 | `FLOW_PHASES` |
| `HOTFIX` | 10 | 3 | `FLOW_PHASES` |

The flow is bound **once**, by `init`, from the governance record's
`classification.flow`, and stored in the new `state.flow` field
(`workflow_version` 1.15 → 1.16). Progress fractions, gate numbers and gate
labels are all derived from the bound flow.

### 1. GREENFIELD is frozen in the engine, not derived from the registry

This is the decision the rest of the design turns on, and the first draft of
this work got it wrong.

The obvious construction is to make `GREENFIELD` *be* `PHASE_SEQUENCE`. It has
an appealing property: the compatibility translation — "every workflow that
existed before flows traversed GREENFIELD" — becomes true by construction, and
it follows the `GATE_PHASES` precedent, which is derived rather than declared.

**It is fail-open.** Once the registry stops being GREENFIELD, deriving
GREENFIELD from *all of* the registry means **any phase added to the registry
silently joins GREENFIELD**. The very first thing this change does is add a
phase to the registry. The derivation would have destroyed the property it was
introduced to protect, and nothing would have failed loudly.

Read correctly, the `GATE_PHASES` precedent argues the other way.
`GATE_PHASES` filters the registry **through an explicitly declared set**,
`PHASE_TO_GATE_KEY`. Adding a registry row does not add a gate, because
gate-ness is declared per gate rather than inherited. Deriving GREENFIELD as
the whole registry has the opposite shape: it unions in anything new.

**Chosen:** GREENFIELD's membership is pinned explicitly, in exactly one place
— `GREENFIELD_V1_PHASES` in `scripts/sdle.py` — and is deliberately **not** a
`FLOW_PHASES` row. `Constants.flows` injects it and then validates it through
the *same* rules as every declared flow, so it can never become a privileged
special case.

The compatibility translation is instead proved four independent ways, none of
which a registry edit can move:

1. a test asserts `GREENFIELD_V1_PHASES == EXPECTED_TRAVERSAL`, importing that
   list from `tests/test_integration_01_happy_path.py` — a file this work is
   forbidden to touch;
2. a golden nineteen-element literal in `tests/test_units_flow_model.py`, an
   independent second witness a reviewer can read without opening the engine;
3. the pre-change `PHASE_SEQUENCE` can be parsed straight out of Git history
   and compared element-wise to `constants.flows["GREENFIELD"]`;
4. the migration sets `flow: "GREENFIELD"` unconditionally, so every state
   that predates the field is *named* GREENFIELD, and 1–3 fix what that name
   means.

**What replaces the guarantee derivation gave for free.** Derivation
guaranteed that no registry phase could be orphaned. That is restored, and
strengthened, by a new lint check `every_registry_phase_is_used_by_some_flow`:
a phase added to the registry and named by no flow now **fails `lint-skill`
loudly** instead of silently joining GREENFIELD. A future author who genuinely
wants a phase in GREENFIELD must edit the frozen constant — a loud, reviewable,
three-witness change.

**Rejected — derive GREENFIELD as the registry minus a declared exclusion
set.** Same failure mode one level removed: a registry addition still joins
GREENFIELD by default, and safety depends on an author remembering to add an
exclusion. It also puts GREENFIELD's membership in two places with the union
rule implicit. The frozen-baseline design fails closed; the exclusion design
fails open.

### 2. `impact_analysis` is a real phase, and it is gateless

**Human decision, recorded as such.** Contract §13's DEFECT_FIX sketch names
"impact analysis" as a step. It could have been folded into the existing
`analyze` phase, or written as prose guidance inside `spec_draft`. It is
neither: it is a registry phase at position 2, in `DEFECT_FIX` and `HOTFIX`
only, because a defect fix starts from an existing system and the expensive
failures in defect work are the ones nobody looked for — the second caller of
the function being changed, the test that silently covered the broken
behaviour, the migration that assumed it. Doing that reading *before* the
specification is written is what makes the specification narrow.

It is deliberately **gateless**, and that too was a human decision.

**Rejected — a ninth gate.** A ninth gate would make every flow's gate
numbering conditional on which flow ran; it would need a `PHASE_TO_GATE_KEY`
row, an `ARTIFACT_OWNERSHIP` row, a `GATE_TO_EXECUTION_PHASE` row and a ninth
`approvals` key in the state template, and it would put a human approval in
front of a document whose purpose is to *inform the next document*, not to
authorise work. `checklist_draft` is the standing precedent: a phase that
produces a real artifact and has no gate of its own.

**Gateless is not ungoverned**, and that is enforced with machinery that
already existed rather than new code:

- the artifact is `reviews/impact-analysis-<YYYY-MM-DD-HHmm>.md`, fingerprinted
  by `artifact record` — size floor, SHA-256, one audit event;
- `artifact review` binds a review to that exact SHA (contract TP-011), and
  rewriting the file makes the review stale by the derived mechanism that was
  already there — no stored freshness flag;
- the content is displayed in conversation before `gate_spec`, the first gate
  downstream of it, so design invariant 4 (a human sees the artifact before
  approving) is *strengthened*, not bypassed.

**Amended after ADR-005.** The three points above were all the enforcement
there was, and between them they left a hole: every one of them describes what
happens *if* an analysis is produced, and nothing made the engine insist that
one was. `advance --to spec_draft` succeeded out of a `DEFECT_FIX` WorkItem
that had written nothing. The phase contract in `phase-execution.md` said to
write, record and review the analysis, but a contract the engine does not back
is a suggestion, and the deterministic core exists so that the rules do not
depend on the orchestrator having read them.

ADR-005 then solved exactly this problem for `discovery` — also gateless, also
"understand before you draft" — with `discovery_precondition`, and the
asymmetry was an accident of sequencing rather than a decision: §14 demanded
discovery's rule explicitly, and nothing made the same demand of this phase.
`impact_analysis_precondition` closes it as the mirror image, so a fourth
point now belongs on the list:

- `advance` and `skip` both refuse `impact_analysis_missing` until this
  WorkItem has a recorded analysis carrying a *current* PASS review. Recording
  alone does not lift it — a fingerprint is not a judgement — and because the
  review is bound to one SHA, editing the analysis afterwards re-arms the
  refusal. It is a pure reader placed ahead of each mover's first irreversible
  write, so a refusal leaves `audit.md` byte-identical.

This is a tightening of a gateless phase, not the ninth gate rejected above:
it requires that the reading was *done and checked*, and leaves the judgement
of whether the fix is scoped correctly to `gate_spec`, where it already sat.

**The artifact path was chosen from constraints, not taste.** The Spec Kit
feature directory does not exist until `spec_draft` runs, and this phase runs
before it — so the block must not call `feature bind --require-feature` and
must not reference `state.specKit.featureDirectory`, either of which would
refuse and halt every defect flow at its second phase. `workitems/<id>/…` is
refused by the write fence, and moving it there would mean editing the hooks.
`reviews/` is the exact precedent the security review already sets: a
Claude-written, project-root-relative, timestamped analysis document, outside
the fence, already gitignored.

### 3. The flow binds once, and there is no command that re-binds it

`init` reads `classification.flow` and writes `state.flow`. Nothing else writes
it except the migration, which names `GREENFIELD` for a workflow that predates
the field.

**Rejected — a `flow set` / `flow select` command.** A second writer of
traversal identity would let the model reshape the lifecycle by issuing a
command, which is a governance bypass: the point of deriving the flow from a
recorded, digest-fresh governance assessment is that a human decision and a
deterministic score stand behind it.

Consequently, re-assessing mid-run with a *different* flow is refused —
`flow_mismatch`, exit 1, with two named remedies (re-assess with the bound
flow, or reset and start again). It refuses; it does not warn.

The refusal's placement is load-bearing. It sits in `apply_advance` and in the
two early pure-reader prechecks in `cmd_gate_approve` and `cmd_skip`, always
**ahead of the first `append_audit`**, because those two commands append to the
append-only ledger before they move the phase and an append cannot be undone by
a later raise. A refused advance, approval or skip leaves `audit.md`
byte-identical. Within `apply_advance` the governance record is validated
first, with no `state` so that call writes nothing, *then* the flow is compared,
*then* the accepted facts enter the ledger — so a stale or blocked record is
still reported as such and is never masked by a flow disagreement.

**Declared consequence, not a defect:** a workflow initialised before v1.16
that already carries a governance record proposing a non-GREENFIELD flow will
refuse `flow_mismatch` at its next advance. That is correct — it *was*
traversing GREENFIELD — and the remedy is one command.

### 4. Governance is still not an `init` precondition

T06 decided that a WorkItem must be able to bootstrap without a governance
record, and this change does not reverse it. `init` therefore has a no-record
path, and it must be the safe one: it binds `GREENFIELD`, the flow every
workflow before v1.16 traversed, so the default changes nothing for anybody.

`cmd_init` also still does **not** route through `apply_advance`. Making it do
so to gain flow-aware movement would turn governance into an `init`
precondition by the back door.

### 5. The restated ordinals become checked derived views

Three places restated an ordinal that a flow now makes relative:

| Restated in | Decision |
|---|---|
| `PROGRESS_MAP`'s `N/18` values | **Unchanged**, and re-documented as the GREENFIELD view. A new lint check pins every value equal to the derived GREENFIELD position, which nothing checked before. |
| `PHASE_LABEL_MAP`'s `Gate 1: …` … `Gate 8: …` | The literal ordinal becomes a `{gate_number}` placeholder, substituted at render time with the gate's number *in the bound flow*. GREENFIELD renders byte-identically; `DEFECT_FIX` renders `Gate 1: Specification Approval` for `gate_spec` instead of a stale `Gate 2:`. A lint check forbids re-hardcoding it. |
| `phase-execution.md`'s `**Phase N — <id>:**` block headers | **Unchanged for all seventeen existing blocks**; the new block carries no ordinal. |

**Rejected — renumbering the execution-block headers to registry indices.**
`modules/security-review.md` cross-references "Phase 17" and is on this phase's
must-not-change list; renumbering would drag an unrelated file into the diff
for no behavioural gain. Instead the block-header regex makes the ordinal
optional — a marginal loosening — and that is over-paid by a new check that
pins all seventeen existing ordinals to their GREENFIELD positions, which were
unchecked restated constants before.

### 6. `NEXT_PHASE` stops being any flow's chain

`NEXT_PHASE["requirements_check"]` is now `impact_analysis`, which GREENFIELD
does not contain. Any traversal function still reading that chain would route a
GREENFIELD run through a phase it does not have. So the rule is not hygiene, it
is correctness, and it is pinned as a **closed reader set**: the functions in
`scripts/sdle.py` that read `Constants.next_phase` are exactly
`{load_constants, run_sync_checks, cmd_constants}` — populate, lint, dump. Any
new reader anywhere in the file fails the assertion.

`NEXT_PHASE` itself is kept, and `next_phase_chains_sequence` is left unchanged:
it is now the registry's canonical-order proof and nothing else. Contract §13
forbids removing it at this point; §17 is where it goes.

### 7. `MANDATORY_FLOW_PHASES` — "shorter but never ungoverned" as an identity

A closed ten-member set, defined once in `scripts/sdle.py`, enforced by
`lint-skill` **and** by `Constants.flow()` at load time — because a flow that
lost one of these would not merely look wrong, it would die inside Spec Kit on
a real run. Each membership has a named reason in the source.

`impact_analysis` is deliberately **not** in the floor: putting it there would
force it into GREENFIELD and ITERATIVE, contradicting the decision to scope it
to defect work. So the HOTFIX identity is stated as two exact assertions rather
than one:

```
set(HOTFIX) - {"impact_analysis"} == set(MANDATORY_FLOW_PHASES)
set(flow) >= set(MANDATORY_FLOW_PHASES)                for every flow
```

In one sentence: **HOTFIX is the governance floor plus exactly one phase, and
that phase is the impact analysis §13 asks for.**

## Consequences

- `state.json` gains one field, `flow`. `approvals` is **unchanged** — it keeps
  its eight keys, and a gate a flow does not run simply stays `null` forever.
- `lint-skill` goes from 22 checks to 29. No existing check is weakened: two are
  re-targeted onto a stricter subject (`PROGRESS_MAP` is now checked for exact
  equality with GREENFIELD's phase set *and* every individual value, where it
  was checked only for its key set), one is generalised over every flow's
  denominator, one is narrowly broadened and over-compensated. Each new check
  has a firing test that plants a breakage isolating it.
- A broken `FLOW_PHASES` is an integrity failure (exit 3) when a *traversal*
  asks for a flow, and a named per-check failure when `lint-skill` asks. It
  never defaults. `load_constants` deliberately parses the table without
  validating it, so one broken row reports as the rule it actually breaks
  instead of short-circuiting every other check.
- All nine dry-run transcripts remain byte-identical and remain the GREENFIELD
  acceptance specification. No transcript is authored for the other four flows;
  they are pinned by end-to-end tests that drive the real CLI instead.
- `compute_drift`, `cmd_repo_staleness`, `write_atomic`, `append_audit`,
  `save_state`, `read_state`, `bind_workitem`, `cmd_migrate_workflow`,
  `governance_precondition`, `required_gate_set` and the write fence are all
  untouched. The drift paths iterate the full gate set but already skip
  anything unapproved, and an out-of-flow gate is never approved, so they are
  flow-correct with zero edits.

## What this deliberately does not do

- **It does not make any gate conditional on risk.** This work selects which
  phases execute; making gate *requirements* policy-driven is separate, later
  work. `required_gate_set` stays inert and uncalled by any phase-movement
  function, and `governance gates` still reports `advisory: true`.
  `impact_analysis` is in `DEFECT_FIX` and `HOTFIX` because the flow says so,
  never because a risk level said so.
- **It does not give `BROWNFIELD_DISCOVERY` its real shape.** That needs a
  repository baseline that does not exist yet. It is declared equal to
  GREENFIELD and pinned by a test that says so explicitly, so the later change
  cannot happen silently.
- **It does not remove the legacy fixed-sequence structures.** `NEXT_PHASE`,
  `PROGRESS_MAP`, `PHASE_TO_GATE_KEY`'s gate-number column, the legacy
  `.workflow/` dual-read rung and `migrate-workflow` all keep working.
- **It does not build a workflow engine.** A flow is an ordered subset of a
  fixed registry and nothing more: no conditional branching, no parallel
  phases, no loops, no dynamic phase insertion, no policy DSL. If the
  implementation ever grows a construct capable of expressing a workflow SDLE
  does not currently need, that is a defect, not a feature.
