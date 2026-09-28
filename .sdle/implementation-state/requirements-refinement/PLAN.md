# Requirements Refinement Loop — implementation plan

Baseline: `fca6c00` (branch `feat/requirements-refinement`), CI green on all four cells
(`36374476221`). Stage 0's closure changed the engine materially since the brief was written at
`48a853a`: `governance assess` now re-scans bound sources itself and can refuse
`governance_content_unacknowledged`, and a new pre-init record (`scan-acknowledgements.json`) and
command surface (`accept-content --path`) exist. Every fact below is re-verified against `fca6c00`, not
assumed from the brief.

## 1. §1 re-verification, corrected

All facts F1–F14 hold as originally stated **except**:

- **F5 (partial, per O1).** Governance is enforced at `advance`/`gate approve`/`gate omit`/`skip`
  (`governance_precondition`, `sdle.py:7427`), not at `init`. `state.json` still does not exist at
  assessment time. Unaffected: loop state still cannot live in `state.json`.
- **F10, revised.** `scan --path` is no longer the *only* untrusted-content check: `governance assess`
  (`sdle.py:5420`) independently re-scans every bound source (`unacknowledged_flagged_sources`,
  `sdle.py:9933`) before persisting a record, refusing `governance_content_unacknowledged` if anything is
  flagged with no matching acknowledgement. **This refinement loop's own re-scan requirement (F10 in the
  brief) is now partially satisfied by the engine already** — every `governance assess` call re-examines
  bound sources on its own, including ones the refinement loop revises. The loop's job narrows to:
  producing the *proposal* (the twelve answers) and the *edits*, not re-implementing the re-scan.
- **New fact, F15.** A WorkItem-owned pre-init record already exists for exactly this class of problem:
  `workitems/<id>/.sdle/scan-acknowledgements.json`, read by `read_scan_acknowledgements` (`sdle.py:9810`),
  written by `write_content_acknowledgement` (`sdle.py:9897`), append-only, WorkItem-scoped
  (`doc["workitem"] == paths.workitem`, checked on every read). Replayed into `audit.md` at the first
  `advance` by `record_scan_acknowledgement_audit` (`sdle.py:6935`), validated *unconditionally* (even
  with `state=None`) so a malformed record is caught before any caller's own first irreversible append.
  This is the **direct, working precedent** for this brief's own §3.5 "shared-document transaction" idea
  and for `refinement.json`'s own write discipline — cited throughout §4 below, not re-derived.
- **New fact, F16.** Path safety for any orchestrator-named file (not just bound sources) exists:
  `safe_repo_path` (`sdle.py:4478`) and the shared lexical core `_lexically_safe_path` (`sdle.py:4435`),
  returning `(target, canonical_key)`. `refinement`'s own path handling (§4.5) must go through this, not
  reinvent it.

## 2. Impact surface map

Sourced from three Explore-agent reports run at Stage 1's start (engine governance surface, hooks/agents/
tests surface, ledger enumeration) plus Stage 0's own grep inventories, refreshed against `fca6c00`.

| Surface | Location | Role for this work |
|---|---|---|
| `cmd_governance_assess` | `sdle.py:5420` | Where `evaluateQuality`'s twelve answers are validated; §3.2's flip refusal attaches here (the lint floor's refusal path is defined but not enforced in this change — Option 3, §3.b) |
| `evaluate_quality` | `sdle.py:4791` | Shape/severity validation of the twelve answers — unchanged by this work |
| `governance_precondition` | `sdle.py:7427` | Advance-time re-check; unaffected — refinement runs pre-`init` only (C4) |
| `requirements_sources` / `unacknowledged_flagged_sources` | `sdle.py:4694` / `:9933` | Single-read-per-source pattern (closed in Stage 0) — the model for how refinement's own re-scan-after-edit must read |
| `read_scan_acknowledgements` / `write_content_acknowledgement` | `sdle.py:9810` / `:9897` | The precedent pre-init record; F15 above |
| `record_scan_acknowledgement_audit` | `sdle.py:6935` | The precedent deferred-audit-replay pattern; F15 above |
| `safe_repo_path` / `_lexically_safe_path` | `sdle.py:4478` / `:4435` | The precedent path-safety API; F16 above |
| `reserve_evidence` | `sdle.py:3005` | Evidence-file naming (`{kind}-{execution_id}.json`) — `refinement-*.json` follows the same pattern |
| `append_audit` | `sdle.py:1407` | Single audit-chain writer — `refinement` commands never call this directly except through the same deferred-replay shape F15 establishes |
| `bind_workitem` / `resolve_paths` | `sdle.py:2851` / `:413` | WorkItem resolution ladder — `refinement` commands resolve exactly like `governance`/`requirements` do |
| Write-fence hook | `.claude/hooks/hooks.py`, `FENCED = (".workflow", "workitems", "requirements", "guidance")` | `refinement.json` under `workitems/<id>/.sdle/` is **already covered** by the `workitems` prefix — no hook change needed. **Gap, not fixed here:** there is no `lint-skill` rule enforcing this the way `_check_product_agents` enforces the agent fence; the write-fence hook is the only guarantee, and it is a tripwire per CLAUDE.md's own architecture section, not a proof. Recorded, not treated as blocking — matches every other engine-owned file's coverage. |
| Product agents / `PRODUCT_AGENT_TOOLS` | `sdle.py:11359` | New `sdle-requirements-review` agent joins the existing four; `lint-skill`'s `product_agent_files` glob (`sdle-*.md`) picks it up automatically — proven by a test, per CLAUDE.md's own drift-list warning about assumed coverage |
| `CAPABILITY_MAP` | `SKILL.md:232` | New row needed. `requirements_check` is the natural phase — refinement runs pre-`init`, and `requirements_check` is the one phase every flow starts at before any generation. **Verify in a throwaway worktree before Stage 3**, not assumed: `lint-skill`'s `capability_map_covers_every_registry_phase` check requires every *registry* phase to have a row, and adding a *capabilities* pointer to an existing phase's row (rather than declaring a new phase) is the minimal, correct move — this is not a new phase, and must never look like one. |
| `test_units_governance.py`, `test_units_capabilities.py`, `test_units_invariants.py`, `test_units_startup_contract.py` | `tests/` | Direct consumers of every function this work touches; also where `PRODUCT_AGENTS` (capabilities test) and `WRITE_PRIMITIVE_COUNTS` (invariants test) are pinned and must be updated in the same commit as any new write call site |

## 3. Blast-radius measurement (§3.2/§3.3, decides the design)

### 3.a `quality_verdict_flip`

Grepped every test file and `docs/dry-runs/`, `docs/tutorials/` for a BLOCKED-then-PASS sequence on
unchanged document bytes. **One hit**: `tests/test_units_governance.py::test_re_assessing_a_fixed_requirement_unblocks_the_same_advance`
(line 919) calls `assess(project, blocked_input())` then `assess(project)` — the governance *proposal*
changes, but `requirements/todo-api.md`'s bytes never do. **No dry-run or tutorial shows this sequence at
all** (a second `grep -rln` for `requirements_quality_blocked`/`governance_blocked` in `docs/dry-runs/`
and `docs/tutorials/` returns nothing) — zero documentation drift from this refusal. Design consequence:
this one test's premise must change in the same commit as `quality_verdict_flip` ships (edit the document
substantively before the second `assess`, matching the pattern already used for
`test_scanning_again_after_init_makes_acknowledgement_available` in Stage 0's own DEF-RR-001 work).

### 3.b The lint floor's blast radius on the existing suite — corrected, empirically measured

**An earlier draft of this section concluded the floor's blast radius was zero, on a misreading: it read
§3.6 ("`governance assess` changes only to enforce §3.2") as excluding the lint floor. It does not —
§3.2 itself lists the lint floor ("Lint floor (C6). Where the lint reports a failure mapped to a check,
an assessor `PASS` for that check is refused `quality_verdict_below_floor`"), so §3.6 places the floor
*inside* `governance assess` itself, on every assessment, not only inside the refinement loop. That
earlier conclusion is retracted here rather than silently corrected, matching this ledger's own
convention for a wrong verdict.** (Separately, that draft also mis-attributed
`governance_content_unacknowledged` to the brief's §3.2 — it is Stage 0's own, unrelated addition, not
part of this brief at all.)

Built a scratchpad prototype (`lint-prototype.py`, this directory) implementing all six §3.3 rules,
including two an earlier pass omitted (acceptance-criteria id/observable-outcome, duplicate ids across
documents). Findings:

- **Against `requirements/todo-api.md`: clean** on all six rules, as the brief requires — but only after
  fixing two bugs the prototype itself first exposed: a naive `TODO` marker check matched the ordinary
  product noun "todo" (the document is *about* a todo-list API), and the acceptance-criteria rule needed
  an "observable outcome" heuristic broad enough to recognise todo-api.md's own plain-prose Acceptance
  section (no ids, but concrete outcomes: "behaves as described", "is consistent", "is enforced",
  "passes") without also passing genuinely vague criteria. Both are exactly the failure mode C6 warns
  about, caught only by testing against real content.
- **Measured empirically, not argued from the brief's text.** Wired the prototype's rules directly into
  a throwaway worktree's `cmd_governance_assess` (refusing `EXPERIMENT_lint_floor` wherever a `PASS`
  answer has a mapped lint finding) and ran the real test suite against it, unmodified. **92 of 230
  tests failed in `test_units_governance.py` alone; a further 121 failed and 16 errored across
  `test_units_startup_contract.py`, `test_units_capabilities.py`, `test_units_gate_policy.py` and
  `test_units_hardening.py`** — over 200 failures in 5 of the 19 affected files, extrapolating to several
  hundred suite-wide. The floor, applied unconditionally to every `governance assess` call as the brief's
  text most naturally reads, is **not safe to ship against this suite's fixtures as they stand.**
  `bare_project`'s minimal document (`tests/conftest.py:388`) — no `## Acceptance`, no "out of scope"
  text — is the single root cause for most of them, since `project`/`bare_project` underlie the large
  majority of this suite.
- **Against a deliberately vague fixture**: the vague-terms rule correctly flagged `fast`, `user-friendly`,
  `as appropriate`/`appropriate`, `robust` and `several` — no false negatives observed in this sample.

**Owner decision (2026-09-28): Option 3 — the lint ships as advisory only in this change.** Findings are
recorded as evidence (§5.b, `evidence/refinement-lint-<execution_id>.json`) on every lint run, but **no
lint finding ever raises `quality_verdict_below_floor`** — an assessor's answer is never overridden by
the lint in this shipment. This is a deliberate, owner-authorised deviation from the brief's C6 ("a lint
failure makes an assessor `PASS` for the mapped check impossible") and from §3.2's inclusion of the floor
alongside the flip — recorded here as a deviation, not silently implemented as if C6 read differently.
It converges with the brief's own open-items register: OI-FUT-01 already anticipated "whether any lint
rule should become blocking, decided from the corpus precision data. Owner decision with data" — this
plan's measurement (§3.b above) *is* that data, taken now rather than deferred, and the owner's answer to
it is "not yet, ship advisory." Consequences for the rest of this plan:

- `quality_verdict_below_floor` stays a defined reason code (§5.c) — the schema and the refusal path
  exist in the engine, tested, but nothing in this change causes it to fire. This keeps the door open
  for a repository policy or a later change to turn a specific rule on as an actual floor without a
  second engine change, matching invariant 7 (one source of truth, not two floor mechanisms).
- The blast-radius measurement above stops being a suite-breaking risk: nothing in this change blocks on
  the lint, so no existing test's `bare_project` fixture needs to change.
- The corpus (§3.c) is still built and the lint's precision/recall against it is still measured and
  reported (brief §7 acceptance scenario 23) — advisory status does not exempt the lint from being
  measured, only from being enforced.
- OI-FUT-01 is updated (§10 of the brief, carried into this work's own open-items register at Stage 5) to
  record that the decision was made with data, not left fully open: "not yet — ship advisory; revisit
  once broader corpus data exists," rather than simply "owner decision pending."

### 3.c Corpus — built and measured in Stage 1, ahead of the original schedule

The corpus was originally sketched here as Stage-3-phase-A work. The owner's "Full corpus, 3 runs/doc"
decision (2026-09-28) moved it earlier: `tests/fixtures/requirements-quality/` holds one seeded-defect
document per check id (12 documents) plus `clean-baseline.md`, all "Link Shortener Service" documents,
committed at `9ec6d4a`. `labels.json` started outside the working tree (this session's scratchpad) for
the original 39-dispatch measurement, so a general-purpose subagent measuring the baseline could not
`Glob`/`Read` the answer key; it was moved into the repo at `ef41b9c` for durability, once measurement
was done, so a Stage 2 Codex worktree can reproduce the tables. **Any further measurement pass against
this corpus** (including Stage 5's before/after metrics) relies solely on the dispatch prompt's "do not
use any tools" instruction for label-leakage protection, not on the file's location — record each
future run's `tool_uses` count (from the task notification) as provenance that no tool was actually
invoked.
Each document was assessed **three times independently**, fresh context each time, 39 dispatches total,
raw results under `runs/assessor-<check-id>-run<n>.json`. Two subsequent advisor-prompted correction
passes (both 2026-09-28) found this session's own corpus edits had contaminated several findings and, in
the first correction's own re-measurement, repeated the same premature-conclusion pattern a second time.
Full methodology and the verbatim, reproducible `recompute_metrics.py` output are in `LEDGER.md`'s three
"Stage 1 — corpus measurement..." sections, ending in the "Correction — 2026-09-28: retracting the
'confirmed / strengthened' verdict above" section, which is authoritative — everything below summarizes
*that* section, not the two it retracts.

**What is actually confirmed, by a controlled experiment rather than argument:** `compatibility`'s
original 0/3 was a corpus-construction defect, not an assessor limitation. Deleting the whole
Compatibility section had also deleted the only text establishing that compatibility was relevant at
all; adding a one-sentence relevance cue to Purpose (no compatibility requirement) flipped the result to
3/3 caught, unprompted, in a controlled re-test. The fixed text is now the corpus's
`defect-compatibility.md`. **There is no demonstrated structural blind spot for section absence.** The
narrow, real limitation — one line in the `sdle-requirements-review` agent's own prompt in Stage 3, not
a design change — is that the assessor will not infer a relevance concern the document's own text never
raises.

**`constraints`, `scope` and `security_data_implications` remain genuinely unresolved**, not confirmed
misses: all three documents still carry scattered content a generous reading of their check's own
"where any genuinely apply" hedge could credit — `security_data_implications` was excluded from this
list in the first correction pass, which was itself an error caught on review, since its Constraints
section still names authentication, which check 9 names explicitly. The compatibility experiment proved
this exact mechanism can flip a result; no equivalent controlled test was run for these three.
`labels.json` marks all three `_undetermined`. `dependencies`'s
check-level 0/3 turned out to be an attribution result, not a recall gap: the document names its
dependencies (Kubernetes, internal SSO) outside a dedicated Dependencies section and is reliably blocked
3/3 via `ambiguity` — this session's own run-file notes claiming otherwise were factually wrong and are
annotated, not rewritten. **The one measure that survived both corrections un-revised is document-level
blocking** (does *any* check fail, which is what the loop's stall/regression logic actually acts on):
`defect-scope.md` is the only document never blocked in any of 3 observed runs — and it is also one of
the two `_undetermined` documents, so even this is not asserted as a confirmed product gap, only as the
one number worth Stage 2 attention.

**The earlier "prompt-level remedy versus documented limitation" owner question is withdrawn** — there
is no demonstrated blind spot left to choose a remedy for.

**Agreement rate: 69% (9/13), unrevised from the original measurement.** The intermediate correction's
"62% (8/13)" was an arithmetic error, not a re-measurement, caught by `recompute_metrics.py`.

**Lint precision/recall (deterministic, one run per document):** perfect (1.00/1.00, zero false
positives including on `clean-baseline.md`) for `blocking_unknowns`, `out_of_scope`,
`acceptance_criteria` and `ambiguity`; 0.50 recall for `nfrs` specifically (a keyword-coverage gap in
`check_quant_nfrs_without_measure`, not a design flaw — noted for a Stage 3 regex fix); the sixth rule
(duplicate ids) has no positive fixture in this corpus yet and needs one before Stage 3 relies on this
corpus as its regression suite. This confirms the Option-3/D7 floor-eligibility requirement (§3.3: "any
rule that floors a verdict produces zero findings on... every clean corpus fixture") for the four rules
that are floor-eligible today.

## 4. Design decisions (Stage 2 attacks each of these)

### D1 — pre-init audit for the shared-document transaction (C1)

Precedent now exists and is followed exactly, not re-derived: `record_scan_acknowledgement_audit`
(F15) validates unconditionally (even `state=None`) and replays only once state exists, de-duplicated
structurally (`_already_recorded`, matching on the entry's own `event`/`Artifact` fields, never a
substring search). `refinement`'s own transaction record follows the identical shape:

- A pending, unaffected-by-`init` WorkItem's transaction intent is written into its own
  `refinement.json` — never into `state.json` — with the same "validate unconditionally, replay once
  state exists" split.
- Every **affected** WorkItem (the other side of a shared-document acknowledgement/edit under C1) that
  has already run `init` gets `append_audit` immediately, under its own session lock, exactly like any
  other governed fact.
- An affected WorkItem that has **not** run `init` gets the deferred-replay treatment, at its own first
  `advance` — mirroring F15's `governance_precondition` call site precisely, not inventing a second one.

**Flagged for Stage 2's specific attack**, per the brief's own instruction: is this precedent actually
load-bearing for a *multi-WorkItem* transaction (F15 is single-WorkItem), or does the shared-document
case need its own recovery state machine regardless? Codex is asked to decide this from the code, not
from this plan's framing.

### D2 — the refusing lock (shared-document transaction serialization)

A new primitive: exclusive `open(paths.refinement_lock_file, "x")` per affected WorkItem, acquired in
sorted WorkItem-id order, released on completion or abort. Unlike `lock acquire` (which only warns), this
one **refuses** if already held — the shared-document transaction (C1) genuinely cannot proceed
concurrently, unlike ordinary session locking. Also closes the class of race
`write_content_acknowledgement`'s own docstring documents as an accepted limitation (R2-D04, deferred
explicitly to this primitive) — cited, not re-litigated.

### D3 — assessor provenance, no new governance-input key

`GOVERNANCE_INPUT_SECTIONS` stays strict (unchanged); assessor output is copied into evidence
(`evidence/refinement-*.json`), never into a new governance-input field. Faithful copying is convention
(F8), stated plainly in the final report, not claimed as verified.

### D4 — deliberate test/constant changes, each in the commit that causes it

- `test_re_assessing_a_fixed_requirement_unblocks_the_same_advance` — edit the document before the
  second `assess` (§3.a).
- `PRODUCT_AGENTS` (`test_units_capabilities.py`) — four agents becomes five.
- `WRITE_PRIMITIVE_COUNTS` (`test_units_invariants.py`) — updated for every new `write_atomic`/
  `save_state`/`append_audit` call site the refinement commands add, each with the same inline
  comment style the file already uses (Stage 0 set this precedent four times over).
- CLAUDE.md's "four read-only product subagents" line.
- A new test proves `lint-skill`'s `sdle-*.md` glob picks up the fifth agent — do not assume it.

### D5 — command surface

`refinement propose | decide | apply | dispute | show`. **Stage 2 is asked, per the brief, whether
`propose` and `decide` can collapse into one command** — Stage 1 takes no position; this is exactly the
kind of minimalism question Codex should answer from the frozen contracts (§5), not from prose.

### D6 (new, from Stage 0's own experience) — path handling

Every path `refinement` commands take (an edit's target, a dispute's cited file) goes through
`safe_repo_path`/`_lexically_safe_path` (F16). No second path-validation implementation, on pain of
repeating Stage 0's own V2-01 mistake (a hand-rolled validator that drifted from the shared one on day
one).

### D7 (new) — acknowledgement/refinement-edit interaction

`is_content_acknowledged` matches on exact `(path, sha256)`. This means **any** edit — including an
auto-applied, presentation-neutral whitespace edit under C2 — changes the digest and silently
un-matches any prior acknowledgement for that path, by construction, with no special-casing needed. This
is the safe default (an edit is never assumed still-acknowledged) and requires no new mechanism. What it
does mean, stated plainly for Stage 2 to attack: **every refinement iteration that touches a
previously-scanned, previously-flagged-then-acknowledged document invalidates that acknowledgement**,
even if the edit is unrelated to the flagged line — `governance_content_unacknowledged` will fire again
on the next assessment, and the loop must re-surface it (not treat it as new "progress" per §3.4, and not
loop-stall on it either, since it is a direct, expected consequence of the edit rather than drift). No
carry-forward mechanism is built; re-acknowledging is one `accept-content --path` call, matching the
existing UX. **Owner-confirmed (2026-09-28): this UX is acceptable as designed** — always re-check, no
carry-forward mechanism built.

### D8 — brownfield baseline citation (new, found while building the §8 traceability table)

Acceptance scenario 14 requires that, for `ITERATIVE` bound to a repository `.sdle/baseline.json`, a
`compatibility` or `dependencies` finding cites the relevant baseline entry when one overlaps. No design
element above addressed this — found only by walking every Stage 5 scenario against this plan, not by
inspection. Minimal position, matching D3's existing treatment of assessor provenance: the
`sdle-requirements-review` agent's prompt is given the baseline's relevant entries as ordinary input
context (no new governance-input key), and is asked to cite a baseline entry by id in its `finding` text
where applicable. No new JSON field; no engine validation of the citation's accuracy. **Flagged for
Stage 2:** is a prompt-level citation sufficient, or does correctness require the engine to validate a
cited baseline id actually exists — the same false-claim risk D3 already accepts for provenance, applied
here to a citation rather than a whole answer.

### D9 — dispute outcome vocabulary (new, found while building the §8 traceability table)

Acceptance scenario 26 requires a check overturned by dispute be reported as `overturned_by_dispute`,
distinct from `improvement` or `progress`, with the original result preserved in evidence. §5.a's
iteration record has no field for this. Position: add a per-check `disputeOutcome` field
(`null | "overturned_by_dispute"`) to the iteration record (§5.a, shown there), written only by
`refinement dispute` when both an evidence citation and a recorded human decision are present
(`refinement_dispute_incomplete`, §5.c, refuses otherwise). The original assessor result is never
mutated — only annotated alongside it. **Flagged for Stage 2:** confirm this does not amount to a
second, informal verdict channel that bypasses `evaluate_quality`'s own shape validation — the same
boundary D3 draws for provenance, now drawn for an overturned result.

## 5. JSON contracts

### 5.a `refinement.json` (WorkItem-owned, `workitems/<id>/.sdle/refinement.json`)

```json
{
  "refinementVersion": "1",
  "workitem": "<id>",
  "status": "IN_PROGRESS | PASSED | ESCALATED | CANCELLED | FAILED",
  "iterationCap": 3,
  "iterations": [
    {
      "iteration": 1,
      "contentDigest": "<sha256, presentation-neutral normal form>",
      "proposalDigest": "<sha256>",
      "failingChecks": ["acceptance_criteria", "..."],
      "findings": [{"checkId": "...", "text": "..."}],
      "questions": [{"id": "...", "text": "...", "options": ["..."], "answer": null}],
      "edits": [{"op": "replace|insert_after|append_section", "path": "...", "anchor": "...",
                "baseSha256": "...", "autoApplied": true, "decision": "accepted|rejected|null"}],
      "outcome": "progress|regression|stall|null",
      "disputeOutcomes": [{"checkId": "...", "outcome": "overturned_by_dispute",
                           "originalResult": "FAIL", "evidenceRef": "...", "decisionRef": "..."}]
    }
  ],
  "startedAt": "...", "endedAt": null
}
```

### 5.b Lint evidence (`evidence/refinement-lint-<execution_id>.json`)

```json
{"kind": "refinement-lint", "executionId": "...", "documentSha256": "...",
 "findings": [{"ruleId": "...", "mappedCheck": "...", "floors": true, "line": N, "text": "..."}]}
```

### 5.c Refusal reason codes (new)

| Reason | Raised by | Exit |
|---|---|---|
| `quality_verdict_flip` | `governance assess` | 1 |
| `quality_verdict_below_floor` | *(defined, never raised in this change — Option 3, §3.b)* | 1 |
| `refinement_shared_source` | `refinement propose`/`apply` | 1 |
| `refinement_dispute_incomplete` | `refinement dispute` | 1 |
| `refinement_cap_exhausted` | `refinement propose` | 1 |
| `refinement_edit_stale_base` | `refinement apply` | 1 |
| `refinement_record_invalid` | any `refinement` command | 3 |

## 6. State-transition table

| From | Event | To | Writes | Notes |
|---|---|---|---|---|
| (none) | `governance assess`, F₀=∅ | (no loop) | governance.json only | Existing flow, untouched |
| (none) | `governance assess`, F₀≠∅ | IN_PROGRESS, iteration 1 | `refinement.json` (new) | Loop entered |
| IN_PROGRESS | `refinement propose` | IN_PROGRESS | findings + questions in the iteration record; lint findings recorded as evidence | Lint is advisory (Option 3, §3.b, owner decision): it never refuses `propose`, only records what it found alongside the assessor's own answers |
| IN_PROGRESS | human `decide` | IN_PROGRESS | decision recorded per question | ≤5 questions, batched |
| IN_PROGRESS | `refinement apply` | IN_PROGRESS | edits applied, evidence written | Auto-apply only if presentation-neutral (§3.5); C1 transaction (below) if the source is shared |
| IN_PROGRESS | re-`scan` finds new flags | IN_PROGRESS | scan-acknowledgements.json (existing F15 mechanism) | Not a refinement-record write; the existing engine path |
| IN_PROGRESS | re-`assess` → Fₖ=∅ | PASSED | refinement.json closed | §3.4 "Pass" |
| IN_PROGRESS | re-`assess` → Fₖ⊊Fₖ₋₁ or an answer applied | IN_PROGRESS | iteration k+1 opens | §3.4 "Progress" |
| IN_PROGRESS | re-`assess` → new failing check | IN_PROGRESS, flagged | regression recorded, shown to human, **no auto-continue** | §3.4 "Regression" |
| IN_PROGRESS | re-`assess` → Cₖ=Cₖ₋₁, or Pₖ seen before, or 2 no-progress iterations | ESCALATED | refinement.json closed | §3.4 "Stall" |
| IN_PROGRESS | cap (3) reached | ESCALATED | refinement.json closed | §3.4 "Exhaustion"; `init` stays refused |
| IN_PROGRESS | re-`assess` refuses `governance_content_unacknowledged` (Stage 0's own DEF-RR-001 check, unrelated to this brief's §3.2) | IN_PROGRESS, question pause | nothing new | **Not progress, not a stall**: no assessment was produced at all, so it cannot count toward Fₖ. Surfaced as a question ("this bound source is flagged, unacknowledged, unrelated to the edits just applied — acknowledge or edit it") rather than silently retried or counted against the stall/cap counters |
| any | crash/interruption | resume | (none until next write) | Recovery reads `refinement.json`, finds the last-committed iteration, and either resumes (nothing pending) or replays a C1 intent (below) |
| IN_PROGRESS | human cancels | CANCELLED | refinement.json closed | |
| IN_PROGRESS | unrecoverable engine error | FAILED | refinement.json closed, error recorded | Terminal; the WorkItem's `governance assess` remains usable independently — this record's terminal state does not itself block re-running `governance assess` by hand |

### Presentation-neutral normal form and content digest (§3.2/§3.5)

Per brief text, restated here as the literal algorithm this plan implements: line endings unified to
`\n`; trailing whitespace stripped per line; runs of two-or-more spaces *within a line's prose text*
collapsed to one, **excluding** leading indentation, table rows (`|`-delimited), code spans (`` ` ``) and
fenced blocks (` ``` `); runs of two-or-more blank lines collapsed to one. `Cₖ` = SHA-256 of this
normal form. An edit is presentation-neutral only if the normal form is byte-identical before and after
— computed by the engine (mirroring `_sources_digest`'s existing "one formula, shared by writer and
reader" discipline), never inferred from the refiner's own classification of its edit.

### C1 shared-document transaction record (§3.5, D1/D2)

```json
{"transactionId": "...", "status": "PENDING|COMMITTED|ABORTED",
 "documentPath": "...", "baseSha256": "...", "targetSha256": "...",
 "targetContentEvidence": "evidence/refinement-target-<id>.json",
 "affectedWorkitems": ["..."], "acknowledgement": "...", "originatingWorkitem": "..."}
```

Recovery (run before any other `refinement` command for the originating or an affected WorkItem, whenever
an intent is not `COMMITTED`): document at `targetSha256` → append only the missing per-WorkItem audit
entries (idempotent, same structural-dedup pattern as F15's `_already_recorded`), then commit. Document at
`baseSha256` → re-apply from the stored target content, or `ABORTED` on user cancel. Document at any other
SHA → `refinement_record_invalid` (exit 3), naming the transaction, changing nothing.

## 7. File-level estimates by phase

| Phase | Files | Rough size |
|---|---|---|
| A — contracts, lint, corpus | `sdle.py` (+~400 lines: record I/O, digest fns), `tests/fixtures/requirements-quality/*` (12+ docs), `tests/test_units_refinement_lint.py` | Medium |
| B — assessment integrity | `.claude/agents/sdle-requirements-review.md`, `sdle.py` (+~100: the flip check in `evaluate_quality`'s caller; the lint floor's reason code and evidence recording, defined but not wired to refuse — Option 3), `tests/test_units_governance.py` (+tests) | Small-medium |
| C — edit/loop control | `sdle.py` (+~600: `cmd_refinement_*`, edit ops, D2's lock), `tests/test_units_refinement.py` (new) | Large |
| D — orchestration | `modules/requirements-refinement.md`, `CAPABILITY_MAP` row, `SKILL.md` governance section, `/sdle-start` if needed, `CLAUDE.md` | Small |
| E — tests/docs/ADR | `docs/GETTING-STARTED.md` §11/§13, `docs/architecture/ADR-013-*.md`, scenario tests | Medium |

## 8. Traceability, risks, rollback

- **Traceability:** each acceptance scenario (brief §7, 30 items) maps to a named test in Stage 3E's
  plan; not enumerated twice here.
- **Risks:** with the lint advisory-only (Option 3), the suite-breakage risk §3.b measured is closed —
  nothing blocks on it. The residual risk is precision/recall measurement quality (corpus adequacy,
  §3.c) and the shared-document transaction (D1/D2), the largest unproven design element — both flagged
  explicitly for Stage 2.
- **Rollback:** revert commits; no data migration (no `state.json` schema change, per brief's own
  constraint — unaffected by anything in this plan).

## 9. Parallel capability check

Confirmed already, repeatedly, within this session rather than re-demonstrated: ten-plus `git worktree
add`/`git worktree remove` cycles (Stage 0's review rounds) and multiple Agent-tool dispatches (the three
Stage 1 Explore agents) both worked cleanly throughout. No fresh drill needed; citing existing evidence
per the brief's own "don't redo what's already done" principle.
