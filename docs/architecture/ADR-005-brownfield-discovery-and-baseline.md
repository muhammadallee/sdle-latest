# ADR-005 — Brownfield discovery becomes a governed record, and the repository baseline becomes real

| | |
|---|---|
| **Status** | Accepted |
| **Date** | 2026-08-31 |
| **Scope** | Migration phase T08 (transition contract §14). Engine version v1.16, unchanged. |

## Context

ADR-004 gave SDLE five flows and then said, in its own closing section, what it
had not done: *"It does not give `BROWNFIELD_DISCOVERY` its real shape. That
needs a repository baseline that does not exist yet."* `BROWNFIELD_DISCOVERY`
was declared element-wise identical to `GREENFIELD` and pinned by a test whose
name said which phase owned changing it.

Two things were missing, and they are the same thing seen from two ends.

**A brownfield WorkItem had nowhere to put what it learned.** §14 asks for a
discovery output covering fourteen named categories, and states the rule that
output exists to serve: *never present inference as observation*. Without a
place to record it, discovery was a conversation that evaporated.

**Every WorkItem after the first had no way to inherit it.** §13 defines
`ITERATIVE` as "use established repository baseline; no full repository
rediscovery" and §26 item 22 says "full brownfield discovery is not repeated by
default". Neither sentence was true of the engine, because there was no
established baseline to use. §11 had reserved `.sdle/baseline.json` as a
documented empty slot and left its schema to §14 — ADR-002 recorded it as
*named* by `Paths.baseline_file` and policed by `validate`, with "no code writes
it — the phase that owns the baseline schema creates the file." This is that
phase, and this ADR is where that sentence stops being true.

The property §14 actually asks for is a **convergence invariant**: after
*either* greenfield completion *or* brownfield discovery completion, the
repository has the same minimum baseline shape, and the exit criterion is that
*the second WorkItem against the same valid baseline does not rerun full
discovery*.

## Decision

### D1 — `discovery` is a new registry phase, in one flow, and it is gateless

The registry goes from 20 entries to 21. `discovery` sits at position 2,
immediately after `requirements_check` and before `impact_analysis`, and
appears in exactly one `FLOW_PHASES` row: `BROWNFIELD_DISCOVERY`, which becomes
19 phases and 8 gates. The other four flows are byte-identical.

It is **gateless**, following ADR-004 §2's `impact_analysis` precedent exactly.
A ninth gate would cost a `PHASE_TO_GATE_KEY` row, an `ARTIFACT_OWNERSHIP` row,
a `GATE_TO_EXECUTION_PHASE` row, a ninth `approvals` key in the state template
— therefore a schema migration — and it would make gate numbering conditional
on flow for every flow. A `lint-skill` check named `discovery_is_gateless`
fails if any of that machinery ever names the phase, and it derives the gate
key rather than spelling it, so the check cannot be what introduces one.

Gateless is not ungoverned. The engine refuses to leave the phase without a
validated record (D4), the record is durable evidence in the WorkItem runtime,
an audit event is appended, and the findings are displayed in conversation
before `gate_constitution` — the first gate downstream — which is how
`impact_analysis` already satisfies design invariant 4.

**Rejected — putting `discovery` in `MANDATORY_FLOW_PHASES`.** That floor is
the "shorter but never ungoverned" identity; adding `discovery` would force it
into `GREENFIELD`, `ITERATIVE`, `DEFECT_FIX` and `HOTFIX`, which is the
opposite of §14's intent.

**Rejected — a separate `BROWNFIELD_*` phase family.** §13's still-binding
constraint is "do not build a generic BPM/workflow framework". One extra
registry row inside the existing ordered-subset model adds no new lifecycle
construct: no branching, no loops, no dynamic insertion, no policy DSL.

### D2 — `discovery assess --input <path>`, modelled on `governance assess`

A structured JSON document Claude authors, the engine evaluates
deterministically, and the engine persists as
`workitems/<id>/.sdle/discovery.json` plus an evidence document in that same
runtime's `evidence/` directory, next to every other execution record. The
envelope is fail-closed in exactly the way `read_governance_input` is: unknown
key, missing key, unsupported version and non-object each refuse, and nothing
returns a default.

**Rejected — a Markdown discovery report as the governed artifact.** It would
have to live in `reviews/`, which is gitignored, so the baseline would
reference a file that vanishes on a fresh clone. WorkItem records are versioned
by design.

**Rejected — copying the findings into the baseline descriptor.** §14 says the
baseline references canonical artifacts instead of copying them. The descriptor
holds the record's path and SHA-256; the record is the findings' one home.

### D3 — What the engine can enforce about the classification, stated honestly

This is the phase's integrity property, and it is **split**. Both halves are
recorded here, and both are published by `sdle.sh discovery schema` so the
split is machine-readable rather than merely documented.

**Engine-enforced — these are guarantees.** `discovery assess` refuses (exit 1)
when:

- a finding carries no classification, or one outside the closed three;
- a finding in the *observation* class cites no evidence, or cites a path that
  does not exist inside this repository, or cites one that escapes the
  repository root;
- a finding in the *inference* class names no basis, names a basis that is not
  a declared finding, or names a basis that is itself in the *unknown* class —
  an inference may not rest on an unknown;
- a finding in the *unknown* class carries evidence;
- any of the fourteen §14 categories has no finding at all. Because the unknown
  class is an honest answer where the repository does not say, that rule is
  always satisfiable without inventing anything.

**Not engine-enforced — these are claims by their author, not guarantees, and
the engine says so rather than implying otherwise.** The engine cannot judge:

- whether a statement in the observation class is *true of* the file it cites;
- whether a conclusion in the inference class follows from its basis;
- whether the findings are complete.

Discovery is judgement work; the deterministic core cannot compute the
findings. What it converts from prose into mechanism is exactly this and no
more: *nothing is unclassified, an observation must point at something that
exists, an inference must name what it rests on, an unknown may not masquerade
as evidence, and no §14 category may be silently dropped.* A checker that
implied more than it checks would be worse than no checker.

This is ADR-003's split verbatim — Claude proposes, deterministic policy
decides — and not a new pattern.

### D4 — Leaving `discovery` requires a validated record, checked by a pure reader

`discovery_precondition(paths, state)` refuses `discovery_missing` when the
WorkItem is standing at `discovery` and there is no record for *this* WorkItem
with a passing result.

It is evaluated in `apply_advance` — the one function `advance`, `gate approve`
and `skip` all funnel through — so `skip` cannot walk past discovery. Putting it
in `cmd_advance` alone would have been fail-open: `skip` exists for a failed
generation step, and a discovery record that was never produced is exactly that
case.

It is a **pure reader** — no state write, no `append_audit` — which is what lets
it also be called at the top of `cmd_gate_approve` and `cmd_skip`, ahead of the
ledger entries those two append *before* they delegate to `apply_advance`. A
refusal raised only inside `apply_advance` would strand an orphan audit entry
that `state.json` never commits. Those are exactly the three sites
`governance_precondition` and `flow_precondition` already occupy, for exactly
that reason, and the rule itself still has one home. A refused `advance`,
approval or `skip` therefore leaves `audit.md` byte-identical, which is the
B1/NB-6 property T06 and T07 established and this phase must not regress.

### D5 — `.sdle/baseline.json` references canonical artifacts; it never copies them

§14's nine required facts map one-to-one onto the descriptor's keys: baseline
version, the producing WorkItem, the commit SHA, the constitution reference,
the architecture/design references, the ADR references, the non-negotiables,
the discovery status and the timestamp. Every reference is a `{path, sha256}`
pair — a pointer plus a fingerprint, never content — built by one function, so
"references, never copies" is a property of a single function rather than a
rule four call sites must remember. `nonNegotiables` holds finding *ids* into
the discovery record, never prose.

Derivation, so nothing is invented and there is one home per fact: the
constitution and architecture references are the resolved `ARTIFACT_OWNERSHIP`
paths for `gate_constitution` and `gate_design` when they exist on disk, so the
table that already answers "which file is this gate's artifact" is the only
place that answers it; the ADR references are the deduplicated, existing
evidence paths cited by observation-class findings in the ADR category; the
non-negotiables are the ids of findings in the constraints category. Both are
empty for a baseline established by `GREENFIELD`, which is honest — a new
project has no ADRs to discover.

### D6 — One writer, at completion, and the write never refuses

The baseline is written in the `is_final` branch of `cmd_gate_approve`,
**first** in that branch, before the completion summary and before the
`workflow_complete` audit entry. `baseline_established` is appended after
`workflow_complete`.

The descriptor builder is **total by construction: it never raises**. An absent
constitution yields `null`, an absent design document yields `[]`, an absent
discovery record yields a `NOT_REQUIRED` status, and a corrupt discovery record
degrades to the same. Validity is derived *later*, by `baseline_findings`, and
never asserted at write time. This is not laziness: the write lands after
`gate_approved` is already in the append-only ledger, and an append cannot be
undone by a later raise. Writing the baseline must not be able to block a
human's final approval. Placing it first in the branch means an I/O failure
produces the same failure shape `write_completion_summary` already has today,
rather than a new one.

The discovery status is derived from the record rather than from the flow name:
`PERFORMED` when the completing WorkItem has an accepted discovery record,
`NOT_REQUIRED` when it has none. Because the one flow that runs `discovery`
cannot leave the phase without a record (D4), that resolves to `PERFORMED` for a
brownfield completion and `NOT_REQUIRED` for a greenfield one, and it does so
without the descriptor builder having to be told which flow it is serving.
**That is the convergence invariant made literal:** both completions produce a
descriptor with the same required key
set; only the discovery-derived content differs.

**Rejected — writing or refreshing the baseline on `ITERATIVE`, `DEFECT_FIX` or
`HOTFIX` completion.** §14's convergence sentence names greenfield completion
and brownfield discovery completion and nothing else. Extending it would let a
flow that performed no discovery establish a "discovered" baseline.

**Rejected — a `baseline establish` / `baseline set` command.** A second writer
is the same governance bypass ADR-004 §3 refused for `flow set`: it would let
the model manufacture the fact that authorises `ITERATIVE`. A test asserts on
the parsed source that the writer has exactly one caller, and that exactly one
function in the engine both names the baseline path member and writes it.

Two consequences of the writer being a function rather than inline code are
deliberate, not incidental.

**It returns the path and the SHA-256 rather than the path member.** §11
forbids a lifecycle command from reaching the repository-configuration
boundary. The final gate approval genuinely has to write that boundary now, so
the containment proof becomes "the reaching set is closed and named" — the
writer is in it, and `cmd_gate_approve` is not, because it receives a path
string and a hash and never names a configuration member itself. The T05-era
clause that no gate, advance, approval or init reaches any member therefore
survives this phase **unchanged**, which is the outcome worth having.

**It establishes nothing under the transitional legacy `.workflow/` binding.**
§14's second required fact is the *producing WorkItem*, and the legacy binding
has none. A descriptor naming no producer would be invalid the moment it was
written, so the honest outcome is to write nothing — the same skip, for the
same reason, that the governance and discovery preconditions make.

### D7 — The reader is fail-closed, and one predicate decides validity

`read_baseline` mirrors `read_governance_record` exactly: absent is `None`;
unreadable, unparseable, non-object, or an unsupported version is an
`IntegrityError` (exit 3). It deliberately does **not** inherit
`read_repo_config`'s swallow-and-default (the open T05 finding NB-4). A
silently defaulted baseline would let a corrupt file read as "not yet
established" and would make the convergence invariant unprovable — the exact
failure direction ADR-003 §3 already rejected once for the governance policy.
A test asserts on the parsed source that no exception handler in `read_baseline`
returns a value, and asserts the contrast that `read_repo_config`'s handlers do.

`baseline_findings` is the **single** predicate, with exactly two consumers —
the `baseline` commands and `sdle validate` — so they can never disagree about
one repository (invariant 7). That caller set is itself asserted on the parsed
source.

Status is derived, never stored: `ABSENT` when there is no file and **no
finding is emitted**, because most repositories have none and that is not a
defect; `INVALID` when there is an error finding; `STALE` when there are only
warnings; `VALID` when there are none.

**Material invalidation is exactly the error set** — a malformed or
incomplete descriptor, a producer that is not registered in
`workitems/index.md`, and a referenced path that no longer exists.

**A *changed* reference is a warning, and that is a decision, not an
oversight.** `design/app/app-design.md` is rewritten by `design_generation`,
which `ITERATIVE` runs. If a changed reference invalidated the baseline, the
*third* WorkItem in any repository would be forced back into full rediscovery,
which directly contradicts §26 item 22. A **missing** reference is different in
kind: the baseline's claims can no longer be checked at all. A stale baseline
is reported by `validate` and is a legitimate ground for a human to request
rediscovery, which is the safe direction; it is never a refusal.

### D8 — Two `init`-time refusals, and one monotone opt-in

Both are evaluated at `cmd_init`, the single flow-binding site, and both are
placed **before** the first `mkdir`, so a refusal creates nothing at all: no
runtime directory, no execution file, no audit entry.

- **R1 `baseline_present`** — binding `BROWNFIELD_DISCOVERY` to a repository
  whose baseline is `VALID` or `STALE`, without a rediscovery request. This is
  §14's exit criterion enforced rather than asserted, and the message names
  both remedies.
- **R2 `baseline_required`** — binding `ITERATIVE` while the baseline is
  `ABSENT` or `INVALID`. This is §13's `ITERATIVE` definition made true.
  Without it the convergence invariant is decorative.

`DEFECT_FIX` and `HOTFIX` are deliberately **not** covered. §13 gives them no
baseline clause, and blocking an emergency hotfix on a repository-level
artifact would be a governance change T08 was not asked to make.

**The opt-in.** `classification.rediscovery` is a third permitted key in the
governance input: boolean, optional, default `false`. It is monotone-safe in
exactly the sense ADR-003 uses — it can only ask for *more* work, never less —
so a model that proposes it cannot weaken anything. It is refused
`classification_invalid` with any flow other than `BROWNFIELD_DISCOVERY`,
because requesting rediscovery while binding something else is a contradiction.
`governanceVersion` is **not** bumped: an absent key reads as `false`, so no
document written before this phase changes meaning.

**Why only at `init`.** Re-checking at every `advance` would refuse a run
mid-flight over a repository-level fact the WorkItem cannot fix — someone
deleting a design document during an implementation, say. The flow binds once,
and the baseline decision is made on the facts at binding time and recorded in
the `flow_selected` audit entry. That is a declared consequence, not a defect,
and a test pins that `baseline_precondition` has exactly one caller.

### D9 — "Significant existing source" stays a human and model judgement

§14's first trigger is a conjunction: *significant existing source exists* AND
*no valid baseline exists*. This phase makes the second conjunct deterministic
and leaves the first where it is — expressed by the flow the human and Claude
agree on in the governance assessment.

**Rejected — a source-file-count threshold.** It would be an arbitrary magic
number at a governance-relevant location, it would need a policy key and a
default, it would misfire on monorepos and on generated code, and — the
disqualifying part — it would make the bare test fixture "not significant",
letting several tests pass for the wrong reason. §14 gives no threshold and
this phase does not invent one.

### D10 — The vocabulary reaches the prompt layer through a command

`sdle.sh discovery schema` is read-only, needs no WorkItem, and emits the
closed category vocabulary, the classification vocabulary, the envelope keys,
the rule ids and both halves of D3's split. `phase-execution.md` tells Claude to
take every id from that response — the exact shape `SKILL.md` already uses for
`governance policy`.

The vocabulary is restated in no prompt or documentation file, **this ADR
included** — which is why the paragraphs above name the classes in words rather
than quoting the tokens. That is enforced two ways: a
`lint-skill` check over the prompt files, and a test that runs a real content
search over the same file set T06's `_searchable_files()` covers. The
identifier-shaped part of the vocabulary is what is searched: the underscored
category ids, the three classification tokens and the envelope key. The other
five category ids are single ordinary words, and each of them already appears as
prose somewhere in the searched set — in the README, in `CLAUDE.md`, in the
Reference Guide, in the security-review module and in this ADR — describing
something that has nothing to do with §14's vocabulary. Searching for those
would flag documents that restate nothing, which is the same carve-out ADR-003
makes for the governance check ids: the drift surface is the machine-readable
half.

### D11 — No version bump, no migration row, state template byte-identical

This phase adds registry rows, new repository and WorkItem *files*, and new
commands. It adds no `state.json` field and no ninth `approvals` key, so it
needs no `workflow_version` bump and no `VERSION_MIGRATION` row. ADR-003 §10
set the precedent by ownership: a record that must exist before `state.json`
cannot be a field of it. `version_string_consistent` still reports v1.16 at all
four locations and the migration chain still has 16 rows, and a test asserts
both. The version bump belongs to the phase that owns V1 convergence.

### D12 — What this deliberately does not touch

- **`.claude/hooks/`** — byte-identical. The repository `.sdle/` is unfenced,
  and the ADR-003 §4 hazard is unchanged: a bare `.sdle` fence entry would also
  match `workitems/<id>/.sdle/`.
- **`.gitignore`** — unchanged. `.sdle/baseline.json` is tracked by default,
  which is what a versioned repository baseline should be.
- **`SDLE_OWNED_PREFIXES` and `cmd_manifest_build`'s exclusion** — unchanged.
  A later WorkItem's dirty-tree guard and Gate 7 manifest will see
  `.sdle/baseline.json` as a working-tree entry, because `.sdle/` is in neither
  exclusion set. That exposure is real, it is the same one T05 created with
  `.sdle/config.json`, and it is **inherited as a decision rather than fixed
  here**: widening a guard's exclusion set is a safety-reducing edit outside
  this phase's goal. One test pins both sets — `SDLE_OWNED_PREFIXES`
  element-wise, and, on the source of the one function that builds it, that the
  manifest excludes the WorkItem runtime and nothing else — so adopting the fix
  later cannot be silent.
- **`GREENFIELD_V1_PHASES`** — frozen, engine-held, still not a `FLOW_PHASES`
  row. A test pins the other four flows element-wise.
- **The nine dry-run transcripts and the happy-path integration test** —
  byte-identical.
- **`required_gate_set` / `governance gates`** — still inert, still
  `advisory: true`. Risk-adaptive gates are separate, later work.

## Consequences

- The phase registry goes from 20 entries to 21; `BROWNFIELD_DISCOVERY` goes
  from 18 phases to 19 and stops being element-wise identical to `GREENFIELD`.
  The five traversals are now pairwise distinct with no carve-out.
- Five new commands: `discovery schema`, `discovery assess`, `discovery show`,
  `baseline show`, `baseline validate`. The schema and the repository baseline
  are readable before any WorkItem exists; the WorkItem-scoped members bind
  through the ladder.
- Two new runtime files (`discovery.json` and its evidence document) and one
  new repository file (`.sdle/baseline.json`). The bidirectional `.sdle/` leak
  detector inherits both directions for free, because both name sets are
  derived from `Paths` rather than re-listed.
- **The §11 differential proof is restated, not dropped.** T05 could assert
  that a full lifecycle run leaves the repository boundary untouched, because
  nothing in the lifecycle wrote it. That is no longer true, and continuing to
  assert it would be asserting a fiction. The clause becomes exact instead: a
  run adds **exactly one** boundary entry, that entry is the baseline, every
  pre-existing entry is byte-identical afterwards, nothing is removed, and an
  unconfigured repository gets the same single file. A second new file, or any
  mutation of `config.json`, still fails. The three clauses either side of it —
  identical traversal, identical ordered audit event sequence, identical
  scrubbed state — are untouched.
- Two new audit event kinds, `discovery_recorded` and `baseline_established`.
- Nine new refusals: `discovery_input_malformed`, `discovery_incomplete`,
  `discovery_missing`, `discovery_workitem_required`, `baseline_present`,
  `baseline_required`, `baseline_not_valid` at exit 1;
  `discovery_record_invalid` and `baseline_invalid` at exit 3. No existing
  refusal is removed or renamed. **Every one is evaluated by a pure reader ahead
  of the caller's first `append_audit`**, so a refused `advance`, `gate
  approve`, `skip`, `init` or `discovery assess` leaves `audit.md`
  byte-identical, and a refused `init` creates no runtime at all.
- `lint-skill` goes from 29 checks to 32. No existing check is removed or
  weakened, and each new one has a firing test that plants a breakage
  isolating it.
- `sdle validate` reports baseline findings through the same predicate
  `baseline show` uses. A repository with no baseline is silent, so `validate`
  is unchanged for every repository that predates this phase.

## What this deliberately does not do

- **It does not make any gate conditional on risk, classification or policy.**
  This phase selects *when discovery happens*; making gate requirements
  policy-driven is separate, later work. Two tests hold the line: one pins that
  `required_gate_set` has exactly two callers and that both are governance
  commands, and the T06 test that no phase-movement function consults it still
  passes unchanged. A third pins that every flow's gate set is still exactly the
  gate phases of its declared phase list — structural, not policy-driven — and
  that none of the six functions this phase added references the risk
  evaluator, the governance levels or the policy reader.
- **It does not introduce a product subagent or a new skill.** Discovery is
  performed in the parent session and recorded through the CLI, because the
  findings must be displayed in conversation before the first downstream gate
  (design invariant 8).
- **It does not remove any legacy scaffolding.** The legacy `.workflow/`
  dual-read rung and `migrate-workflow` keep working, and both new
  preconditions skip the legacy binding for the same reason
  `governance_precondition` does: there is no WorkItem to hold a record.
- **It does not define "significant existing source".** See D9.
- **It does not build a workflow engine.** `discovery` is one row in a fixed
  registry and one element in one ordered subset. If the implementation ever
  grows a construct capable of expressing a lifecycle SDLE does not currently
  need, that is a defect, not a feature.
