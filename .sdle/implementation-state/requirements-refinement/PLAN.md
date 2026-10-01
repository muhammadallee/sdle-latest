# Requirements Refinement Loop — implementation plan

Baseline: `fca6c00` (branch `feat/requirements-refinement`), CI green on all four cells
(`36374476221`). Stage 0's closure changed the engine materially since the brief was written at
`48a853a`: `governance assess` now re-scans bound sources itself and can refuse
`governance_content_unacknowledged`, and a new pre-init record (`scan-acknowledgements.json`) and
command surface (`accept-content --path`) exist. Every fact below is re-verified against `fca6c00`, not
assumed from the brief.

## 0. Re-baseline at `276e152` (resumption, 2026-10-01)

Stage 1 was paused at `65b75df`. While it was paused, the architecture-memory enhancement
(ADR-013, ADR-014) was built, reviewed three times and merged into this branch by fast-forward, so the
engine this plan will be implemented against is not the engine it was written against. This section is
the delta, and **§§1–8 below are left exactly as written**: per the ledger, PLAN.md changes only through
Stage 2 reconciliation, so a correction made here is a correction *proposed to* Stage 2, not a silent
edit of it.

Baseline: `276e152` on `feat/requirements-refinement`, identical to `feat/project-architecture-memory`;
CI run `36806444263` green. Engine `CURRENT_VERSION` is `1.18` (it was `1.17`).

### 0.1 What changed underneath the plan

| Fact | At `fca6c00` | At `276e152` |
|---|---|---|
| Phase registry (`PHASE_SEQUENCE`) | 21 rows | 23 rows (`architecture_placement`, `gate_architecture`) |
| GREENFIELD | 18 phases, 8 gates | 20 phases, 9 gates |
| Mandatory governance floor | 10 phases | 12 phases |
| Write-primitive pins (`WRITE_PRIMITIVE_COUNTS`) | 27 / 47 / 49 (`write_atomic` / `save_state` / `append_audit`) | 32 / 50 / 56; `.mkdir(` 10 → 11 |
| Dry-run transcripts | sixteen | **twenty** (`test_dry_run_contracts.py` pins the number) |
| ADRs | up to ADR-012 | ADR-013 and ADR-014 exist; **next free is ADR-015** |
| Command surface | no `architecture` group | `architecture` added (`COMMANDS`, `RUNTIME_FREE_COMMANDS`) |
| `.sdle/` boundary | `SDLE_OWNED_PREFIXES` names `.sdle/` whole | names `baseline.json`, `implementation-state/`, `architecture/` only |

### 0.2 Brief §1 facts, re-verified against `276e152`

| # | Status | Evidence |
|---|---|---|
| F1–F3 | **Hold** | `governance policy` reports the same twelve `quality_checks`, all twelve blocking, `optional_checks == ["nfrs"]` |
| F4–F7 | Hold | `cmd_governance_assess`, `governance_precondition`, ADR-010/012 unchanged in intent |
| F8 | Holds | convention-only, `CLAUDE.md` / ADR-007 §3 |
| F9 | Holds | post-generation clarify still runs after `spec_draft` (now Phase 6) |
| F10, F15, F16 | Hold as corrected in §1 below | the functions exist; only their line numbers moved (§0.3) |
| **F11** | **Changed** | "exactly sixteen transcripts" is now **twenty** — `test_there_are_twenty_transcripts_and_they_are_numbered_densely`. OI-DOC-03 must change *that* assertion, not a sixteen one |
| F12 | Holds | `ci.yml` matrix is unchanged: ubuntu/windows × 3.11/3.13 |
| F13 | Holds | `import sdle` via the script path works (`CURRENT_VERSION == "1.18"`) |
| F14 | Holds | `codex-cli 0.151.0` present; harness scripts exist in `open-items-01-02/runs/` and `runctl.py` here |

### 0.3 Every `sdle.py:NNNN` citation in §§1–2, resolved to today

No cited symbol has been removed or renamed. All twenty citing lines still resolve; only the numbers
moved. **Cite by symbol, not by line, from here on.**

| Symbol | Cited | Now |
|---|---|---|
| `governance_precondition` | 7427 | 9720 |
| `cmd_governance_assess` | 5420 | 5516 |
| `evaluate_quality` | 4791 | 4872 |
| `requirements_sources` | 4694 | 4775 |
| `unacknowledged_flagged_sources` | 9933 | 12370 |
| `read_scan_acknowledgements` | 9810 | 12247 |
| `write_content_acknowledgement` | 9897 | 12334 |
| `record_scan_acknowledgement_audit` | 6935 | 9228 |
| `_lexically_safe_path` / `safe_repo_path` | 4435 / 4478 | 4516 / 4559 |
| `reserve_evidence` | 3005 | 3081 |
| `append_audit` | 1407 | 1476 |
| `bind_workitem` / `resolve_paths` | 2851 / 413 | 2927 / 472 |
| `PRODUCT_AGENT_TOOLS` / `product_agent_files` | 11359 | 13893 / 14130 |
| `_sources_digest` | 4742 | 4823 |

### 0.4 What the architecture work changes for this plan

1. **§3.b needs no re-measurement.** Its blast-radius concern was the lint *floor* breaking fixtures;
   the owner's Option 3 decision (below, §3.b) ships the lint advisory-only, so nothing in this change
   blocks on it and no `bare_project` fixture changes. What §3.b's decision *does* leave to verify is
   §3.a's one test, `test_re_assessing_a_fixed_requirement_unblocks_the_same_advance`: it still exists
   (`test_units_governance.py:919`) with the same premise.
2. **C5 names the wrong ADR.** The brief's C5 and §6 phase E say "ADR-013". That number is now taken
   by project architecture memory. The owner's decision is that *an ADR records the refinement record,
   its refusals and the assessment-integrity rules* — the number was incidental. Proposed to Stage 2:
   ADR-015, and every `ADR-013` in §7 of this plan is read as ADR-015.
3. **D2 (the refusing lock) has a second precedent.** `architecture_catalog_lock` is a short-lived
   exclusive `O_EXCL` lock with a stale-break age and a timeout that becomes a *refusal*
   (`architecture_catalog_locked`), never a hang, and a reader that never waits for it. D2 should be
   checked against it and should reuse its shape rather than invent a second one.
4. **A closed set now polices the `.sdle/` boundary from the other side.**
   `test_the_repository_configuration_members_have_a_closed_reference_set` fails if any new function
   references a boundary member directly — it failed this branch's own CI once. `refinement.json` is
   WorkItem-owned, so the loop should not need it; any helper that must name a boundary path goes
   through `architecture_catalog_relative`-style sanctioned readers.
5. **`workitem_runtime_member_names` must learn the new record.** It omits
   `scan_acknowledgements_file` today (recorded as RR-004 in `claude-review-rejections.md`), so the
   repository-boundary leak check does not cover that pre-init record. `refinement.json` is a second
   one; fixing both belongs in this change.
6. **Pins this change will move, each in the commit that causes it (D4):** `WRITE_PRIMITIVE_COUNTS`
   (from 32 / 50 / 56 and `.mkdir(` 11), `COMMANDS` (the `refinement` group), `PRODUCT_AGENTS` in
   `test_units_capabilities.py` (the new `sdle-requirements-review` agent) and the dry-run count
   (twenty) if OI-DOC-03 is ever taken up. Also: no test or doc may hardcode a flow size, phase count
   or progress fraction (`lint-skill` and `test_dry_run_contracts` enforce it); read them from the
   engine.
7. **Interaction with `architecture_placement` is benign but must be stated.** Refinement runs pre-`init`
   (C4), at governance; `architecture_placement` runs later and reads the bound requirements through the
   requirements binding (ADR-012, D8). A refinement edit therefore always lands *before* any placement
   reads the documents, and cannot stale one. The case to attack in Stage 2 is the converse: a bound
   document edited *after* placement exists is `governance_stale` today (C4) and must stay so.

### 0.5 Inherited defects that fall inside this plan's impact surface

Recorded in `claude-review-rejections.md` during the architecture reviews; each exists identically in
the Stage 0 code this work builds on. Proposed disposition (owner to confirm):

| Id | Defect | Disposition |
|---|---|---|
| RR-002 | `_lexically_safe_path` refuses `./x` and mis-messages it; its `cmd_scan` comment contradicts the code | **In scope** — D6 (path handling) must go through this function |
| RR-007 | an acknowledgement removed after assessment is not re-checked at `advance` / `gate approve` | **In scope** — D7 (acknowledgement / refinement-edit interaction) |
| RR-008 | post-init `accept-content --path` writes the store before it validates state | **In scope** — D7 |
| RR-004 | `workitem_runtime_member_names` omits the acknowledgement store | **In scope** — 0.4(5) |
| RR-003 | `scan_acknowledgements_invalid` (exit 3) has no in-band repair | §9 register — owner triage |
| RR-006 | drift re-approval runs before the precondition stack | §9 register — owner triage |

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
document per check id (12 documents), `clean-baseline.md`, and — added in a later pass, after an advisor
review found brief §4.1A.4 requires it and the original build had missed it — `todo-api.md`, copied
verbatim from `requirements/todo-api.md`. The corpus's content has changed across several commits since
first built (`eefc661`, `ef41b9c`, and the commit carrying the `todo-api.md` addition); cite its current
state under version control, not one historical SHA. `labels.json` started outside the working tree (this session's scratchpad) for
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

**Agreement rate: 71% (10/14)**, after adding `todo-api.md` (agrees, unanimous). The 13-document figure
was 69% (9/13), unrevised from the original measurement — the intermediate correction's "62% (8/13)" was
an arithmetic error, not a re-measurement, caught by `recompute_metrics.py`.

**The missing `todo-api.md` fixture (brief §4.1A.4) — found and added in a later pass.** The original
build never included it, only the invented `clean-baseline.md`. Added verbatim from
`requirements/todo-api.md`, labeled clean. **3 fresh dispatches unanimously FAILed `dependencies`**
("a relational store" names no product, version or driver) — a real finding on the repository's own
reference document, not edited away (this document is required to stay untouched, per acceptance
scenario 1 itself). **This is now the one live owner question for Stage 2**: acceptance scenario 1
assumes this document passes cleanly and the loop is never entered; on this evidence it would not be.
Full writeup in `LEDGER.md`'s "Addendum — missing brief-mandated fixture" section — two honest readings
are offered there, neither decided in this plan.

**Lint precision/recall (deterministic, one run per document, rescored against the current 14-document
corpus and the current labels — an earlier "perfect on four rules" claim here predated the
`acceptance_criteria`/`ambiguity` dual-labeling and was stale):** perfect (1.00/1.00, zero false
positives) for `blocking_unknowns`, `out_of_scope` and `acceptance_criteria`; 0.75 recall for `ambiguity`
(the miss is `defect-acceptance_criteria.md` — its vague replacement text isn't on the lint's fixed
vague-terms vocabulary, while the LLM assessor catches it every time; a real, narrower coverage gap in
the deterministic floor, not a bug); 0.50 recall for `nfrs` (a keyword-coverage gap in
`check_quant_nfrs_without_measure`, unchanged from before, noted for a Stage 3 regex fix); the sixth rule
(duplicate ids across *bound* documents) still has no positive fixture — an earlier scoring attempt that
compared all 13 unrelated corpus documents against each other (a test-harness bug, not a lint finding,
since these documents are independent, not a bound set) produced 11 nonsense false positives before the
harness was fixed to lint each document alone. Every one of the six rules shows zero false positives on
the current corpus — §3.3's explicit floor-eligibility criterion ("any rule that floors a verdict
produces zero findings on... every clean corpus fixture") is about false positives, not recall, so
`ambiguity` and `nfrs`'s recall gaps do not themselves disqualify those two rules by that specific
criterion; they are a separate concern (a floored rule with a real recall gap would under-detect, not
wrongly flag clean text) already moot under Option 3, since no rule floors anything in this shipment
regardless.

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

`refinement propose | decide | apply | dispute | cancel | show`. `cancel` is added here, not in the
brief's own list — §6's "human cancels → CANCELLED" row has no covering command without it, and folding
cancellation into `decide` (which §6 already scopes narrowly to "decision recorded per question") would
overload a command that is otherwise strictly about answering the loop's own questions. **Stage 2 is
asked, per the brief, whether `propose` and `decide` can collapse into one command** — Stage 1 takes no
position; this is exactly the kind of minimalism question Codex should answer from the frozen contracts
(§5), not from prose. **`propose` is the sole writer of `refinement.json`** (§6): `governance assess`
itself is unchanged except for §3.a's flip refusal and does not create the record — flagged here as a
decision for Stage 2 to attack alongside the `propose`/`decide` merge question, since collapsing the two
commands would also need to decide whether the merged command keeps `propose`'s sole-writer role.

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

### D10 — the `sdle-requirements-review` agent must not restate the check-id vocabulary (new, found
by empirically testing the draft prompt against the restatement guard)

`assessor-prompt-draft.md` (Stage 1's measurement prompt, never intended as the real agent file) spells
out all twelve check ids as literal text. Copied verbatim to `.claude/agents/sdle-requirements-review.md`
in a throwaway check and run against the real suite, it **fails**
`test_no_policy_default_value_is_restated_outside_sdle_py`: `acceptance_criteria`, `blocking_unknowns`,
`out_of_scope`, `problem_statement` and `security_data_implications` (the five check ids the guard
searches for — the other seven are ordinary English words the guard deliberately excludes, per its own
docstring) are all present in the file, and `searchable_files()` already covers `.claude/agents/sdle-*.md`.
Confirmed empirically, not assumed from reading the test.

**Position, matching the exact precedent the other four product agents already establish** (`sdle-
discovery.md`: "The parent gives you the closed set of finding categories... taken from the engine. Use
exactly those, in exactly those spellings, and invent neither"): the committed `sdle-requirements-review.md`
file never lists the twelve check ids or their definitions as static text. It states the *shape* of the
task generically ("the parent gives you a closed set of check ids and their definitions; answer PASS,
FAIL, or NOT_APPLICABLE — NOT_APPLICABLE only where the parent says it is a valid answer — for each, with
a one-sentence finding on every FAIL"). The orchestrator (`SKILL.md`/the engine, at dispatch time) builds
the actual check-id list and definitions into the dispatch prompt from `GOVERNANCE_POLICY_BUILTIN`
(`sdle.py`), which stays their one engine-owned home. `assessor-prompt-draft.md` itself is not corrected
retroactively — it served its Stage 1 measurement purpose and is superseded by this position for Stage 3,
noted here rather than edited there.

Row 21 of §8's traceability table is corrected by this: its test must exercise the dispatch *payload*
the parent actually builds at runtime, not the static template — the same distinction already drawn for
row 21's D3/F8 annotation.

### D11 — where `quality_verdict_flip` reads the prior verdict and content digest from (new, found by
tracing scenario 25 through the engine rather than assuming §6's rows cover it)

§6's rows write `refinement.json` only from `refinement propose` onward (D5's single-writer fix, above).
But §3.a's one identified test
(`test_re_assessing_a_fixed_requirement_unblocks_the_same_advance`) calls `governance assess` twice, by
hand, with no `refinement.json` ever created — exactly acceptance scenario 25's own framing ("a hand
re-run of assess"). `quality_verdict_flip`'s refusal cannot depend on `refinement.json` existing.

Traced into the engine rather than assumed: `governance.json`'s existing record (`cmd_governance_assess`,
`sdle.py:5478`) already reads the prior record as `superseded` before rewriting the file wholesale — the
exact precedent `pinnedPolicy`'s carry-forward already uses. But the only digest it carries,
`requirements.digest` (`_sources_digest`, `sdle.py:4742`), is computed from each source's raw-bytes
SHA-256 — it is **not** presentation-neutral, so a whitespace-only edit changes it, which would let
`quality_verdict_flip` wrongly treat a whitespace-only edit as new content and allow the flip, breaking
acceptance scenario 25 directly (its whole point is that a whitespace-only edit must **not** unlock one).

**Position:** add a second digest field, `contentDigest` (the presentation-neutral normal form's SHA-256,
§3.2/§3.5's algorithm, computed over the same `sources` list `requirements.digest` already covers), to
the same `governance.json` record, alongside the existing raw-bytes one — not replacing it, since
`governance_freshness`'s existing staleness check still needs the raw-bytes digest for its own,
unrelated purpose. `quality_verdict_flip` reads `superseded["quality"]` (the prior per-check verdicts,
already available the same way `pinnedPolicy` reads them) and `superseded["contentDigest"]`, comparing
against the new assessment's own values — independent of whether `refinement.json` exists at all, so it
covers both the loop path and a hand re-run identically. **This does not conflict with D3**, checked
explicitly rather than left open: D3's boundary is about `GOVERNANCE_INPUT_SECTIONS` — what Claude's own
governance *proposal* is trusted to assert as input — not about the engine's own `governance.json`
*output* record, which already carries several engine-computed fields (`bindingDigest`, `downgrade`,
`pinnedPolicy`) added the same way `contentDigest` would be. **Flagged for Stage 2 regardless:** confirm
this reading of D3's boundary, and confirm `contentDigest` is the right home rather than, say, a
dedicated small file `governance_freshness` and `quality_verdict_flip` would both need to agree on.

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
| (none) | `governance assess`, F₀≠∅ | (none) | governance.json only | `governance assess` itself is unchanged from today except §3.a's flip refusal — it reports the failing checks and does not create `refinement.json`. The loop is not entered until the first `refinement propose` call, which is the sole writer of the record (single-writer discipline, matching this codebase's own convention) |
| (none) | `refinement propose`, first call, F₀≠∅ | IN_PROGRESS, iteration 1 | `refinement.json` (new) | Loop entered. Findings + questions in the iteration record; lint findings recorded as evidence — lint is advisory (Option 3, §3.b, owner decision): it never refuses `propose`, only records what it found alongside the assessor's own answers |
| IN_PROGRESS | `refinement propose`, subsequent call | IN_PROGRESS | findings + questions in the next iteration record | Same lint-advisory behaviour as the first call |
| IN_PROGRESS | human `decide` | IN_PROGRESS | decision recorded per question | ≤5 questions, batched |
| IN_PROGRESS | `refinement apply` | IN_PROGRESS | edits applied, evidence written | Auto-apply only if presentation-neutral (§3.5); C1 transaction (below) if the source is shared |
| IN_PROGRESS | re-`scan` finds new flags | IN_PROGRESS | scan-acknowledgements.json (existing F15 mechanism) | Not a refinement-record write; the existing engine path |
| IN_PROGRESS | `refinement propose` (re-assesses internally, same call as row 6 above) → Fₖ=∅ | PASSED | `refinement.json` closed, written by `propose` | §3.4 "Pass" |
| IN_PROGRESS | `refinement propose` → Fₖ⊊Fₖ₋₁ or an answer applied | IN_PROGRESS | iteration k+1 opens, written by `propose` | §3.4 "Progress" |
| IN_PROGRESS | `refinement propose` → new failing check | IN_PROGRESS, flagged | regression recorded by `propose`, shown to human, **no auto-continue** | §3.4 "Regression" |
| IN_PROGRESS | `refinement propose` → Cₖ=Cₖ₋₁, or Pₖ seen before, or 2 no-progress iterations | ESCALATED | `refinement.json` closed, written by `propose` | §3.4 "Stall" |
| IN_PROGRESS | `refinement propose` → cap (3) reached | ESCALATED | `refinement.json` closed, written by `propose` | §3.4 "Exhaustion"; per O1/§1 F5, `init` itself is not a governance precondition — `advance`/`gate approve`/`gate omit`/`skip` stay refused `governance_blocked` while quality is blocked, which is what actually keeps the WorkItem from progressing |
| IN_PROGRESS | `refinement propose` refuses `governance_content_unacknowledged` (Stage 0's own DEF-RR-001 check, unrelated to this brief's §3.2) | IN_PROGRESS, question pause | nothing new | **Not progress, not a stall**: no assessment was produced at all, so it cannot count toward Fₖ. Surfaced as a question ("this bound source is flagged, unacknowledged, unrelated to the edits just applied — acknowledge or edit it") rather than silently retried or counted against the stall/cap counters |
| any | crash/interruption | resume | (none until next write) | Recovery reads `refinement.json`, finds the last-committed iteration, and either resumes (nothing pending) or replays a C1 intent (below) |
| IN_PROGRESS | `refinement cancel` (D5) | CANCELLED | `refinement.json` closed, written by `cancel` | |
| IN_PROGRESS | `refinement dispute`, with both an evidence citation and a recorded human decision | IN_PROGRESS (unchanged) | an entry appended to the current iteration's `disputeOutcomes[]` (§5.a), written by `dispute` | §3.4 / acceptance scenario 26. The assessor's original result stays in the iteration record and in evidence; nothing is mutated, only annotated alongside. Reported as `overturned_by_dispute`, **not** as improvement or progress, so it does not by itself empty Fₖ or open a new iteration. Refuses `refinement_dispute_incomplete` (§5.c, exit 1, nothing written) if either the evidence citation or the recorded decision is missing. **Flagged for Stage 2 (D9):** this must not become a second verdict channel that bypasses `evaluate_quality`'s own validation. **Naming mismatch for Stage 2 to settle:** D9's prose says a per-check `disputeOutcome` field, while §5.a and traceability row 26 show a `disputeOutcomes[]` array; this row follows §5.a, the contract that is actually written out. |
| IN_PROGRESS | unrecoverable engine error | FAILED | `refinement.json` closed, error recorded, written by whichever command hit the error | Terminal; the WorkItem's `governance assess` remains usable independently — this record's terminal state does not itself block re-running `governance assess` by hand |
| (none) | `governance assess`, hand re-run, no `refinement.json` ever created, FAIL→PASS at the same content digest | (unaffected) | `governance.json` only, refused | §3.a's identified test; D11 below — `quality_verdict_flip` reads the prior verdict and digest from `governance.json` itself, never from `refinement.json`, which need not exist for this refusal to fire |

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

### Traceability — brief §7's 30 acceptance scenarios against this plan's design elements

Built by walking every scenario against §4–§6 rather than assumed covered; two gaps found this way are
D8/D9 above, not retrofitted into this table after the fact. "Test area" names a Stage 3E test file/kind,
not a function — exact names don't exist until phase C/E write the code.

| # | Scenario (short) | Design coverage | Stage 3E test area |
|---|---|---|---|
| 1 | Clean pass, loop not entered | §6 row 1 (F₀=∅ → no loop). **Open question, §3.c:** this scenario's own worked example, `todo-api.md`, was measured 3/3 FAIL on `dependencies` in Stage 1 — not yet resolved whether the document or the check reading is at fault; flagged for Stage 2, not assumed passing here | `test_units_governance.py`, existing PASS-path, extended to assert no `refinement.json` is written — write the test against a document verified to pass all 12 checks, which may or may not end up being `todo-api.md` depending on the Stage 2 answer |
| 2 | One check fixed in one iteration | §6 rows 2–6 (entry → propose → decide → apply → PASSED) | `test_units_refinement.py` — single-iteration convergence |
| 3 | Multi-iteration, findings trace to ids/decisions | §5.a `iterations[].findings`/`edits[].decision` | `test_units_refinement.py` — multi-iteration record integrity |
| 4 | Question pauses, resumes without re-asking | §5.a `questions[].answer`; §3.4 human-burden cap (≤5/iteration) | `test_units_refinement.py` — question pause/resume |
| 5 | Rejected edit not applied, not recorded approved | §5.a `edits[].decision: accepted\|rejected\|null` | `test_units_refinement.py` — rejection handling |
| 6 | Regression detected, no auto-continue | §6 row "new failing check → regression... no auto-continue" (§3.4 Regression) | `test_units_refinement.py` — regression detection |
| 7 | Identical proposal/digest is a stall → ESCALATED | §6 row "Cₖ=Cₖ₋₁ or Pₖ seen before → ESCALATED" (§3.4 Stall) | `test_units_refinement.py` — stall detection |
| 8 | Cap exhaustion → ESCALATED; per O1's restatement, `advance` (not `init`) stays refused `governance_blocked` while quality is blocked | §6 row "cap (3) reached"; `iterationCap` (§5.a); existing `governance_blocked` (unaffected, §1 F5) | `test_units_refinement.py` — exhaustion + `advance` refusal |
| 9 | `nfrs: NOT_APPLICABLE`/tighten-only unchanged | D3 (no new governance-input key); `evaluate_quality` untouched (§2) | `test_units_governance.py` — explicit regression assertion, no new exception path |
| 10 | Interruption resumes, no duplicate edit/decision | §6 "any → crash/interruption → resume"; D1's deferred-replay pattern (F15 precedent) | `test_units_refinement.py` — interruption/resume, mirroring existing scan-acknowledgement interruption tests |
| 11 | Concurrent invocation refused by session lock | D2 — new refusing lock (exclusive `open(..., "x")`) | `test_units_refinement.py` — concurrent-lock refusal |
| 12 | WorkItem A cannot write WorkItem B's refinement state | D6 (`safe_repo_path`); F15's WorkItem-scoped read pattern; D2's per-WorkItem lock | `test_units_refinement.py` — cross-WorkItem isolation, mirroring V3-03's acknowledgement-ownership test |
| 13 | Legacy (post-`init`) WorkItem unaffected | C4 (refinement runs pre-`init` only); `governance_precondition` untouched (§2) | `test_units_governance.py` — legacy/post-`init` regression |
| 14 | Brownfield baseline citation | **D8 (new, this pass)** — prompt-level citation, no engine validation, flagged for Stage 2 | `test_units_refinement.py` — brownfield finding cites a baseline entry id |
| 15 | Edit after assessment triggers existing `governance_stale` | §1 F10 revised — existing `governance_freshness` mechanism, unaffected | Existing `governance_stale` tests, extended to cover a refinement-loop edit as the trigger |
| 16 | Adversarial proposal JSON rejected | §5.c `refinement_record_invalid` (exit 3); D6 (`safe_repo_path` for any cited path); Core Rule 6 (injected text is data) | `test_units_refinement.py` — adversarial-input rejection, mirroring V3-01 |
| 17 | Shared document refused without acknowledgement | D1/D2 (C1 transaction); §5.c `refinement_shared_source` | `test_units_refinement.py` — shared-source refusal |
| 18 | Acknowledged shared edit dual-audited, staleness reported | D1 (affected-WorkItem audit append/deferred-replay); C1 record (§6) | `test_units_refinement.py` — shared-edit dual-audit + staleness |
| 19 | FAIL→PASS at same digest refused | §3.a (the one identified test to edit, D4); §5.c `quality_verdict_flip` | `test_units_governance.py::test_re_assessing_a_fixed_requirement_unblocks_the_same_advance` (edited per D4) + new flip-refusal test |
| 20 | Lint failure blocks a PASS | **Does not apply as stated, per Option 3 (owner decision, §3.b):** the lint never refuses a PASS in this shipment. Test instead proves the reason code exists and stays inert | `test_units_refinement_lint.py` — `quality_verdict_below_floor` defined, never raised |
| 21 | Assessor's input has no prior verdicts/findings/proposals | D3; matches the dispatch discipline already validated in Stage 1's corpus measurement. Per **D10**, the committed prompt file carries no check-id vocabulary at all — the parent builds the actual dispatch payload at runtime, so "no prior state" must be verified against that payload, not the static file. **Convention only (F8), same class of gap as D8/D9:** nothing in this plan records the assessor's actual dispatch payload for later inspection. Flagged for Stage 2 rather than resolved here | New test on the parent's dispatch-payload construction (not `sdle-requirements-review.md`'s static template, which per D10 has nothing check-id-shaped to inspect) — no prior-state fields present in what's actually sent |
| 22 | Whitespace-only auto-applies; one-word change does not | §6 presentation-neutral normal form algorithm (§3.2/§3.5); D7 | `test_units_refinement.py` — normal-form digest auto-apply boundary |
| 23 | Corpus before/after metrics, zero findings on clean fixture | §3.c (Stage 1's "before"); Stage 5 reruns as "after" | Stage 5 `REPORT.md` corpus-metrics section, reusing `runs/recompute_metrics.py` |
| 24 | Binding-step-skipped test fails | C7 pattern (non-autouse `project` fixture) applied to refinement tests | `test_units_refinement.py` — explicit-binding discipline test |
| 25 | Whitespace-only edit (bytes change, digest doesn't) never unlocks a flip | §6 normal-form digest + §5.c `quality_verdict_flip` keyed on digest, not raw bytes | `test_units_refinement.py` — flip-refusal survives a whitespace-only edit |
| 26 | Dispute overturn reported distinctly, original preserved | **D9 (new, this pass)** — `disputeOutcomes[]` field (§5.a); §5.c `refinement_dispute_incomplete` | `test_units_refinement.py` — dispute overturn + incomplete-dispute refusal |
| 27 | Structural markdown changes never auto-apply | §6 normal-form algorithm touches only whitespace/blank-line runs — list markers, heading level, emphasis are untouched by the algorithm, so any change to them changes the normal form by construction | `test_units_refinement.py` — structural-markdown changes are never presentation-neutral |
| 28 | Lint doesn't flag categorical/plain-sentence content | §3.3 rule design (positive/negative/neighbouring-kind fixtures); already partially validated — Stage 1's corpus shows zero lint FPs on non-targeted checks | `test_units_refinement_lint.py` (Phase A) |
| 29 | Crash recovery: exactly one audit entry per WorkItem; unexpected SHA refuses | C1 record's Recovery algorithm (§6, literal SHA-branch table) | `test_units_refinement.py` — C1 recovery matrix (target/base/unexpected SHA × per-WorkItem audit count) |
| 30 | Stage 0 evidence complete or blocks Stage 3 | Already satisfied — Stage 0's own deliverable, verified in `LEDGER.md`'s "Stage 0 — final verdict" section | N/A — process deliverable, verified by citation, not a code test |

- **Risks:** with the lint advisory-only (Option 3), the suite-breakage risk §3.b measured is closed —
  nothing blocks on it. The residual risk is precision/recall measurement quality (corpus adequacy,
  §3.c) and the shared-document transaction (D1/D2), the largest unproven design element — both flagged
  explicitly for Stage 2, joined now by D8, D9 and D10 above, and by the `refinement.json` write-ownership
  question §6 raises (which command writes it, and where `quality_verdict_flip` reads a prior FAIL and
  its content digest from when no `refinement.json` exists at all).
- **Rollback:** revert commits; no data migration (no `state.json` schema change, per brief's own
  constraint — unaffected by anything in this plan).

## 9. Parallel capability check

Confirmed already, repeatedly, within this session rather than re-demonstrated: ten-plus `git worktree
add`/`git worktree remove` cycles (Stage 0's review rounds) and multiple Agent-tool dispatches (the three
Stage 1 Explore agents) both worked cleanly throughout. No fresh drill needed; citing existing evidence
per the brief's own "don't redo what's already done" principle.
