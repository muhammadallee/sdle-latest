# Requirements refinement — ledger

Single durable execution record for the requirements-refinement work (brief: `BRIEF.md`, this
directory). Branch `feat/requirements-refinement`, created from `0057425` (tip of
`fix/bootstrap-scan-and-startup-contract` at plan time).

## Current status

**Resumed 2026-10-01 at `276e152`.** The pause (below) ended when the architecture-memory enhancement
that took priority was finished: it was merged into this branch by fast-forward (`65b75df..276e152`, no
rewrite, nothing from Stage 0 or Stage 1 lost — the architecture branch had already restored Stage 0
after a copy-over briefly reverted it, see `docs/enhancements/architecture-memory/PROGRESS.md`), and CI is
green on all four cells (`36806444263`).

**Re-baseline done:** `PLAN.md` §0 records what changed underneath the plan, re-verifies brief §1 facts
F1–F14 against `276e152` (F11 changed: sixteen dry-run transcripts → twenty), resolves every stale
`sdle.py:NNNN` citation to today's line (nothing was removed or renamed), corrects one thing this ledger
had been about to carry forward (the lint floor's blast radius needs no re-measurement — Option 3 made it
advisory-only), flags that **C5's "ADR-013" is now taken and the refinement ADR is ADR-015**, and
proposes a disposition for the six inherited Stage 0 defects the architecture reviews recorded
(`claude-review-rejections.md` RR-002/003/004/006/007/008). §0 is a *proposal to Stage 2*; §§1–8 are
unedited.

**Order of work from here (unchanged except for the added first step):** (0) re-baseline — done;
(1) the `refinement dispute` row in §6 — done; (2) record the Stage 2 review baseline SHA — done, below;
(3) Stage 2, the two-level Codex review — **Level 1 launched**, below; (4) Stages 3–5. No production code
before Stage 2 reconciles.

**Stage 2 review baseline: `6162064`** (`feat/requirements-refinement`, pushed). It is the commit with
`PLAN.md` §0 (the re-baseline), the `refinement dispute` row, and the owner's confirmation of the §0.5
triage ("go ahead", 2026-10-01: RR-002, RR-004, RR-007 and RR-008 in scope; RR-003 and RR-006 to the §9
register). Nothing in `PLAN.md` is marked FROZEN: only Stage 2 reconciliation freezes it. CI at the parent
commit's tree: green on all four cells (`36806444263`).

**Stage 2 harness.** `stage2/` holds relabelled copies of the repository-cleanup P08 harness (brief F14):
`codexrun_stage2.py` (Level 1) and `codexrun_stage2_level2.py` (Level 2), with `review.schema.json` and
`dispositions.schema.json`. The invocation (`codex exec --sandbox read-only --ephemeral --json
--output-schema`), the one-retry policy and the output validation are the originals'. Only the run-id
label and recorded stage label changed — and the Level 2 `closure_assessment` shape, whose
`open_01_closed` / `open_02_closed` booleans were specific to the OPEN-01/02 review, became
`plan_ready_to_freeze` + `blocking_disputes` + `summary`. Review worktrees are detached, outside the
repository, and removed afterwards.

**Level 1:** `codex-cli 0.151.0`, read-only sandbox, ephemeral, detached worktree at `6162064`, prompt
`stage2/level1.prompt.md` (it names the brief's attack list, D1/D8–D11, the `todo-api.md` dependencies
finding, §0.5, and the §0.4 items that are new since the plan was written), timeout 2700 s.

**Level 1, attempt 1 (`20261001T033954-stage2-codex-plan-level1`): INTERRUPTED — not a review.** The
background runner was stopped by Claude Code's memory-pressure reaper while Codex was still reading
(`result` is still `IN_PROGRESS`, zero completed attempts, 8 event lines written, no `review.json`). It
produced no findings and none is claimed. Per the reaper's own notice it was **not restarted by the
agent**; the next step is the owner's choice. The detached worktree at `6162064` is kept so a rerun reviews
the identical baseline, and the three partial files are committed as evidence of the attempt, the way
`open-items-01-02` committed its own reaped round 2. A stray `codex.exe` was still alive afterwards; any
output it writes later is not validated by the harness and is not to be used as a review.

**Level 1, attempt 2 (`20261001T162206-stage2-codex-plan-level1-attempt2`): PASS.** Same baseline, same
worktree, one authorised retry; completed on the first harness attempt (exit 0, schema-valid, `reviewed_commit`
`6162064`). **19 findings, all `defect/*`, none `improvement/*`: 1 critical, 10 high, 8 medium.** Coverage the
reviewer declared *not* reached: the full pytest/lint suites (read-only sandbox), fresh assessor dispatches,
and production behaviour (the artifact is a plan). Output preserved unedited in
`runs/20261001T162206-stage2-codex-plan-level1-attempt2.a1.review.json`.

**Claude's responses** are in `stage2/level1-responses.md`. Every load-bearing claim was checked against the
repository before it was dispositioned (several by execution). Result: **15 ACCEPT, 3 PARTIALLY ACCEPT (008,
010, 018), 1 OWNER DECISION (011); none challenged outright.** That is stated as a claim for Level 2 to test,
not as evidence of quality. `PLAN.md` is **not** edited: corrections are proposed in the responses and applied
only at reconciliation, so Level 2 reviews the baseline and can attack the corrections themselves.

Headline findings: **S2-L1-001 (critical)** — the planned flip refusal, read literally, persists the forbidden
PASS as the latest `governance.json` (the engine writes that record *before* a blocking refusal, and
`governance_precondition` reads only the latest record), turning `quality_verdict_flip` into a bypass; the fix
is to refuse before any write and record the attempt in evidence only. **S2-L1-008** corrects a claim of this
re-baseline's own (§0.4(7)): a shared-document edit by another WorkItem *can* leave a placement derived from
older bytes, because the placement record pins no requirements digest — a gap that predates refinement and
belongs to the already-merged architecture design, so it is routed to the §9 register, not fixed here.
**S2-L1-006** is partly this re-baseline's own doing (§0.4(3) and D2 specified two different locks).

**ESCALATED TO THE OWNER — S2-L1-011 (high).** `todo-api.md` is measured as blocked 3/3 on `dependencies`
(false positives under the committed clean label; `recompute_metrics.py`: `dependencies` recall 0.00,
precision 0.00), but brief scenario 1 requires it to pass unchanged with no loop. Options: (1) refine the
`dependencies` check definition so the existing document passes; (2) amend the document with explicit
authorisation and update scenario 1; (3) amend scenario 1. Agents may not resolve this (brief §5). It blocks
Phase A, because the check-definition table (S2-L1-009) is what option (1) would change. **Open.**

**Level 2 (`20261001T163832-stage2-level2-codex-plan-level2`): PASS**, first attempt, same harness and
sandbox, detached worktree at `a1a204f` (which holds the findings and the responses; `PLAN.md` was still the
baseline's). Launched with the owner's go-ahead ("go ahead with level 2"). **19 dispositions: 11 RESOLVED, 4
REVISED (002, 003, 005, 015), 4 UPHELD (006, 008, 011, 016); 3 new findings (S2-L2-001..003; two high, one
medium). `plan_ready_to_freeze: false`**, with 11 blocking ids. Output unedited in
`runs/20261001T163832-stage2-level2-codex-plan-level2.a1.review.json`; the review worktree is removed.

**Reconciliation** is `PLAN.md` §0.6: one amendment per finding (A1–A19), each overridden section marked
"Superseded in part by §0.6", nothing deleted. Honest account of what Level 2 changed my mind on:
- **S2-L1-006 — Level 2 was right and my response was wrong.** I had reframed the long apply→re-assessment
  interval as protected by the C1 `PENDING` intent. Reading brief §3.5 again, it contains two different things:
  the C1 transaction (steps 1–4, ending at `COMMITTED`, short) and a *separate* last bullet — "the session lock
  is held from apply through re-assessment; a second invocation refuses" — which is the **originating
  WorkItem's own** lock. Level 1 and I had both merged them. The corrected design (A5): a short repository
  mutex for the transaction, a per-WorkItem `AWAITING_REASSESSMENT` state for the long interval, and **no
  cross-WorkItem hold** — so there is no abandonment authority to design and a vanished origin blocks no one.
  Optimistic base-SHA checks and `governance_stale` protect other sharers, as brief §3.5's last C1 bullet says.
- **S2-L2-002 — my Level 1 response created a defect.** Per-WorkItem `pendingTransactions[]` pointers would
  have written into other WorkItems' records, violating scenario 12. Replaced by one repository transaction
  index (A6).
- **S2-L1-001 and §0.4(7)** corrections as recorded in §0.6.1.

**Owner decision, 2026-10-02: A8 / S2-L1-008 is CLOSED — option (A)** ("go with recommended"): the placement
record pins the bound requirements' digest and approval refuses on mismatch, as its own small change before
refinement Phase A, on its own branch off `main` (`fix/architecture-requirements-digest`). The text below
records the question as it was put.

**A11 / S2-L1-011 — decided 2026-10-02: option 1 plus an explicit dependencies statement in the sample, no brand.**
The agreed measurement (`stage2/dependencies-measurement/`, 33 fresh-context runs, exploratory) found: the new
definition fixes the `todo-api.md` false positive (`dependencies` FAIL 3/3 and 2/3 → 0/3), keeps catching a
genuinely vague control (2/3 → 3/3), and flags no ordinary or clean document; **but** `todo-api.md` contains a real
contradiction (`updated_at`, lines 42 and 63) that the Stage 1 label (`[]`, clean) was wrong to miss, and the sample
passes all twelve checks 3/3 only with the dependencies statement **and** that contradiction resolved. The explicit
statement alone removes the `dependencies` failure under either definition, so the definition change is a modest
improvement and not the load-bearing fix. **Two corrections to my own earlier explanations**, made before the
owner chose: the seeded `defect-dependencies.md` defect is a missing Dependencies *section*, not only vague wording,
so "the check misses real defects" was overstated (its recall stays undetermined, as the Stage 1 ledger said); and
the cost of editing the sample was overstated (three files carry the phrase, not thirty-three). **Resolved by the
owner the same day:** `updated_at` means the time the row's fields were last actually changed, which is what
requirement 5 said, so the Data Model line was aligned to it and the sample amended in its three copies
(`requirements/todo-api.md`, the corpus fixture, and the Getting Started embedding). The corpus label note records
that the Stage 1 runs were made against the pre-amendment bytes.

**Targeted verification of the reconciliation (`20261002T094535-stage2-verify-codex-reconciliation`): PASS**, first
attempt, `codex-cli 0.151.0`, read-only, ephemeral, detached worktree at `f4c10a9`, run with the owner's go-ahead.
Scope: only the changed material (PLAN §0.6, the merged architecture fix, the sample amendment, the measurement).
**11 dispositions: 7 RESOLVED, 2 REVISED (S2-L1-008, S2-L1-016), 2 UPHELD (S2-L1-006, S2-L2-001); 1 new finding
(S2-L3-001, medium); `plan_ready_to_freeze: false`.** It also recomputed all 33 measurement outputs: every cell of
`MEASUREMENT.md` matched, and both self-corrections (seeded-defect shape, the three-copies cost) were confirmed.
Output unedited in `runs/20261002T094535-stage2-verify-codex-reconciliation.a1.review.json`.

What was done with it: S2-L1-008 (revised) was a real narrow defect in code I had merged — the requirements check
ran at the start of the command and the catalog write came later; fixed by rechecking inside the catalog lock, test
first (PR #6). S2-L1-016 (revised) was right that the mutex only helps if every mutating refinement command holds
it; A5 and A16 now say so. S2-L3-001 was right that several supersession markers named the wrong amendment and
§5.c was unmarked; markers fixed and §0.6.5 lists the retained clauses to discard. **S2-L1-006 and S2-L2-001
(upheld) are a genuine disagreement about what the owner's brief means** — Claude and Codex read §3.5's "the session
lock is held from apply through re-assessment" differently, and the text supports both. It is escalated to the
owner with the verbatim wording, both readings, and three options (PLAN §0.6.3, A5).

**S2-L1-006 / S2-L2-001 — decided by the owner, 2026-10-02: option (D), the owner's own idea.** Asked to choose
between the two readings, the owner pointed out that C1 already checks at the start who else shares the file and
makes the refiner acknowledge them by name, so the only gap is a loop that *starts later*, because nothing records
that one is in progress. Decision: record an **in-flight claim** in the repository transaction index when `apply`
commits; show it at every start-check; refuse `refinement_document_in_flight` unless the person acknowledges the
origin by name, audited in both WorkItems; release it on the correlated re-assessment or `cancel`; **no lock and no
timer** — an abandoned loop is cleared by the next person's acknowledgement. This answers Codex's two upheld
findings without choosing either reading of "the session lock": a second invocation refuses across WorkItems, and
the abandonment authority is a human decision on the record. **New design, so the changed part (§0.6.3 (D), A5, A6)
still needs a short targeted verification before the plan freezes.**

**Second targeted verification (`20261002T120402-stage2-verify-codex-decision-d`): PASS**, first attempt, same
harness and sandbox, detached worktree at `9784258`, with the owner's go-ahead. Scope: decision (D), the items
fixed since the last round, and the 27-line code change on PR #6. **5 dispositions: 1 RESOLVED (S2-L1-016), 4
REVISED (S2-L1-006, S2-L2-001, S2-L1-008, S2-L3-001); 7 new findings (S2-L4-001..007: 3 high in the state machine,
1 high on release, 2 medium, 1 low); `plan_ready_to_freeze: false`.** Output unedited in
`runs/20261002T120402-stage2-verify-codex-decision-d.a1.review.json`.

My assessment, stated honestly: every finding is accurate. (D) was the right idea but I had specified the owner's
intent, not a recoverable state machine — claim activation against A4's crash order, who may release, what an
override does to the origin, how to clear a claim whose origin no longer exists, which commands check, and the
shape of the acknowledgement were all open. None is a disagreement; all are gaps. `PLAN.md` §0.6.6 now completes
the design on all of them, and also corrects §0.6.1 and §0.6.5, which still described the superseded reading. The
`architecture apply` recheck is correctly placed but cannot be fully closed until the refinement mutex exists
(Phase A); the plan says so. **Observation for the owner:** this is the third review round, and every round has
found more detail in the *shared-document* machinery (C1: the transaction, the index, the claim, the override).
That machinery is needed only when a document is bound by more than one WorkItem.

**Consultation on the shared-document design, 2026-10-02 (owner-requested, two rounds with Codex).** Prompted by
the owner's observation that in a team a refinement edit is not visible to anyone else until it is committed and
pushed. Two questions: (1) drop decision (D)'s in-flight claim? (2) amend C1 so no WorkItem's audit is appended to
by another?

*Round 1* (`20261002T150413-stage2-consult-codex-round1`, PASS, `3fc2cb8`): Codex **agreed with both** and did not
want even a local claim kept. It added: the brief contradicts itself (scenario 12 forbids one WorkItem writing
another's record; C1 requires it); only `audit verify` detects a divergent chain (state loading and drift do not);
git does not guarantee a conflict for disjoint edits, so safety rests on the digest and base-SHA checks; and what
machinery can go. All six points accepted (`stage2/consult1-responses.md`). **The audit hazard was then
reproduced**, not only reasoned: two branches that each append one chained entry to one WorkItem's audit conflict in
`audit.md` and `state.json`, and keeping both by hand leaves a chain `audit verify` rejects (`audit_chain_broken`,
exit 3) — `stage2/consultation-evidence/`. Correction to my own claim: `audit rebaseline` can rechain it as a
deliberate, logged repair.

*Round 2* (`20261002T151050-stage2-consult-codex-round2`, PASS, `3fa9d2f`): of the six round-1 ids, 5 RESOLVED and
1 REVISED; 4 new findings (S2-C2-001..004); **`plan_ready_to_freeze: true`, no blocking disputes: "adopt Design R with
specific changes".** My dispositions: 001 (the notification claim was false and provenance is lost) **accept**;
004 (stale text throughout) **accept**; 002 (recovery discovery by affected WorkItems) **partially accept** — the
affected-WorkItem audit entries it protected are exactly what Design R deletes, so B depends on nothing A recovers,
and a pending transaction lags only A's own record; at most a read-only diagnostic is warranted; 003 (widen the A5
mutex to advance / gate approve / gate omit / skip) **partially accept** — real, but the same TOCTOU class as a hand
edit between a freshness check and a write, which no lock can prevent, and widening the mutex across every
progression command is disproportionate for a rare same-checkout simultaneity; recommend a documented residual.

**Awaiting the owner:** Design R changes the owner's constraint **C1** (and the brief's §3.5 and scenarios 12, 18
and 29), so only the owner can adopt it. `PLAN.md` is not yet changed by any of this.

**Owner request, 2026-10-02: guidance for requirements that change while WorkItems are in progress.** Prompted by the
question "do WorkItems have to complete, or stop and be replaced?". Two things done: (1) the first user-facing
guidance is in `docs/GETTING-STARTED.md` §11c (what SDLE does — `governance_stale` at the next progression — and does
not do — nothing already produced is invalidated, apart from an architecture placement; there is no "replace"
command; a four-situation table of what to do and what it costs), pointed at from the `governance_stale` entry in
`docs/troubleshooting/README.md`; (2) **PLAN §7.1, Phase F, added as the last phase**: a scenario catalogue with
options, impact and a recommended option in plain words, brainstormed with Codex under the same two-level protocol,
every impact claim reproduced in a disposable project, and a **feasibility verdict on whether the engine can give this
guidance to the human at the moment it occurs** (including the cost of recording the requirements digest per artifact,
a state-schema change under the no-migration rule). Building engine support is out of scope unless the owner approves
it after seeing the verdict.

**Owner decision, 2026-10-02: Design R is deferred.** Asked whether to adopt Design R (amend C1), the owner chose to
take it later, at the end. Recorded in PLAN §0.6 as a status note: the shared-document design is ON HOLD; nothing that
exists only for shared documents is to be built; the independent parts (A1–A3, A7, A9, A10, A12–A19 as marked, Phase
A0, the check-definition table, the single-WorkItem loop) proceed; and the decision is **required before Phase C
starts**. Default if none is made: shared documents are refused with no acknowledgement path. This is a deferral, not
a reconciliation: the Stage 2 checkpoint is **not complete** under brief §5 while an owner decision is outstanding,
and proceeding on the independent parts is a recorded deviation under brief §6 that the owner has chosen.

**Phase A0 — the three inherited Stage 0 defects — DONE, 2026-10-02**, started on the owner's go-ahead ("yes") with
the independent parts of the plan treated as proceeding while the shared-document design is on hold (recorded in
PLAN §0.6's status note). The plan's independent parts were taken as frozen at `036393d`. Each fix has tests that
failed first, and each shared function's surfaces are all tested (CLAUDE.md's defect rule).
- **RR-002** (`b98162e`): `_lexically_safe_path` no longer treats `.` or `..` as a trailing-dot alias. `.` is
  accepted and canonicalised, so `./x` and `requirements/./x` key the same file as `x`; any `..` component is still
  refused, as traversal and with a message that says so. Trailing dot and colon stream remain aliases. Tests on both
  surfaces that reach the function (`scan --path`, `requirements bind`); 3 of 4 fail without the fix, the fourth is
  the guard that the alias rule did not loosen.
- **RR-008** (`b98162e`): post-init `accept-content --path` reads (validates) `state.json` before it writes the
  acknowledgement store. Two parametrised tests (malformed; unsupported version) failed first.
- **RR-007** (this commit): `governance_precondition` now asks again whether flagged bound content is still
  acknowledged, against the exact bytes `governance_freshness` read (freshness hands them back, so there is no second
  read for a concurrent edit to slip between), and refuses `governance_content_unacknowledged`; `governance assess`
  and the precondition share one refusal builder so the wording cannot drift. The check also fires on the stateless
  early call that `gate approve`, `gate omit` and `skip` make before their first irreversible write. Tests: advance
  refuses with state and ledger byte-identical, the early call refuses, and an acknowledged document still advances;
  the first two failed first.
Verification, locally and in foreground batches: governance + startup + invariants + repo_config (349), whole-flow
integration (117), transitions (36), gate policy + hooks (573), capabilities + hardening + architecture (257),
shipped-surface, doc-link and documented-command scans, `lint-skill`. CI on the pushed commit is the full-suite check.
Not done and not in A0: RR-003 and RR-006, which the owner sent to the §9 register.

**Was open — two owner decisions, neither resolvable by the agents (brief §5):**
1. **A11 / S2-L1-011** — `todo-api.md` blocked 3/3 on `dependencies` vs acceptance scenario 1 (options 1–3
   above).
2. **A8 / S2-L1-008** — placement staleness under a C1 shared edit. **A genuine surviving disagreement**: Claude
   held it is a pre-existing architecture-memory gap to fix separately; Codex held, and Level 2 upheld, that a
   C1 edit is engine-authorised and so the guarantee cannot be left weakened. Options: (A) pin the bound
   requirements' digest in the placement record and refuse approval on mismatch (small change to the merged
   design; also closes today's hand-edit case); (B) invalidate affected placements in the C1 transaction
   (rejected: writes into other WorkItems' records); (C) accept the weakened guarantee. Claude recommends (A)
   as its own change before Phase A.

**Not yet done:** the brief's targeted Codex verification of the *changed material* (§0.6) — "substantial
changes after Level 2 get targeted Codex verification of the changed material only" — which should follow the
two owner decisions so the verified text is the final text. `PLAN.md` is therefore **not frozen**.

**Pause note, as written when Stage 1 stopped (kept for the record):**

**Phase:** Stage 1 — discovery, baseline, evaluation corpus, plan. **Paused here deliberately, by the
owner's own choice, to prioritize other work — not blocked, not stuck.** Nothing below is mid-edit;
every file is committed, `lint-skill` passes (`ok: true`), and the restatement/doc/collect-only tests
all pass as of the pause commit. Safe to resume from a fresh session by reading this file top to bottom,
starting here.

**What is done:** Stage 0 is VERIFIED (see that section below). The evaluation corpus (14 documents,
`tests/fixtures/requirements-quality/`) is built, measured (3 fresh-context runs per document), and
corrected through three rounds of advisor review — see the "Stage 1 — corpus measurement..." and
"Addendum" sections below for the full, honest history including two premature conclusions this session
caught and retracted on itself. `PLAN.md` has: the impact surface (§2), the blast-radius measurements
(§3), design decisions D1 through D11 (§4 — each either resolved with a stated position or explicitly
flagged for Stage 2's attack, never silently assumed), the JSON contracts (§5), the state-transition
table (§6, just corrected for a single-writer contradiction an advisor review found), file-level
estimates (§7), and the full 30-scenario traceability table (§8).

**What is NOT done, in order:**
1. **§6 is still missing a `refinement dispute` row.** D9 defines its JSON-contract impact
   (`disputeOutcomes[]`) and §5.c has `refinement_dispute_incomplete`, but the state-transition table
   itself has no row for the dispute event. Found while writing this pause note; not yet fixed. Small,
   mechanical — add one row following the same pattern as the `cancel` row just added.
2. **PLAN.md and LEDGER.md have not yet been committed at a named "Stage 2 review baseline" SHA.** The
   approved execution plan freezes PLAN.md only *after* Stage 2 reconciliation (Level 1/2 findings get
   applied to it), so nothing should be marked "FROZEN" — record the baseline SHA in this section once
   item 1 above is fixed and one more `lint-skill` + restatement-test pass confirms green.
3. **Stage 2 itself (the two-level Codex↔Claude adversarial plan review) has not started at all.**
   Blocked on items 1–2. When it starts, give Codex the `recompute_metrics.py` reproduce command plus
   D1, D8, D9, D10, D11 and the `todo-api.md` dependencies finding (§3.c) as named attack items — do not
   let Codex rediscover them from scratch.
4. **Stages 3–5 are entirely unstarted** and explicitly blocked by the brief itself: "No production code
   is written before Stage 2 is reconciled."

**To resume:** read this file's "Current status" section, then `git log --oneline -15` on
`feat/requirements-refinement` to see exactly what the pause commit contains, then pick up at item 1
above. Nothing here needs to be re-derived or re-verified from scratch — the corpus measurement and its
three correction passes are the expensive part and are done.

## Stage 0 — prior-stabilization verification

### Sources (brief §4.0.1)

No stabilization plan file is inside this repository. Two owner plan files exist one level up from the
repository root: `..\sdle-defect-stabilization-plan.md` (D01–D06) and `..\plan-claude-codex-defectfix.md`
(the repository-cleanup plan). Per the brief, these — plus the four `.sdle/implementation-state/*`
ledgers — are the source. The deleted `docs/verification/defect-stabilization-01.md` is recovered from
git at `fc23a93` for cross-reference; it is the record the D01–D06 plan produced.

### Item enumeration and verification

Every commit sha below is confirmed an ancestor of HEAD (`0057425`) by `git merge-base --is-ancestor`.
Every cited test node id is confirmed present by `pytest --collect-only`. CI evidence is read from the
GitHub REST API (`gh` is not installed on this host), never inferred from a push.

**A. SDLE-DEFECT-STABILIZATION-01** (`fc23a93:docs/verification/defect-stabilization-01.md`), all PASS at
verified commit `7561a68`:

| Item | Fix commit(s) | Regression tests | CI |
|---|---|---|---|
| D01 artifact preconditions | `e778c2e` | `tests/test_units_gate_artifacts.py` (21 collected) | Run `34526996629` @ `7561a68`: ubuntu + windows success (2 jobs — this run predates the Python-version matrix; superseded by HEAD's 4-cell run, see below) |
| D02 verification enforcement | `c6a4f77`, `9c10186` | `tests/test_units_implementation_evidence.py`, incl. `test_06_gate_seven_refuses_a_manifest_whose_tests_were_skipped` (confirmed present) | same run |
| D03 change selection | `cc072d9` | `tests/test_units_manifest_changes.py`, incl. `test_06_security_review_refuses_when_no_ref_pinned` (confirmed present) | same run |
| D04 execution identity | `2da5394` | `tests/test_units_execution_identity.py` (8 collected) | same run |
| D05 SpecKit and instructions | `65b2850` | `tests/test_units_documented_commands.py` | same run |
| D06 dry runs | `7561a68` | `tests/test_dry_run_contracts.py` (118 collected); `tests/test_integration_10_to_13.py::test_11_brownfield_then_iterative_reuses_the_baseline_without_rewriting_it` (confirmed present) | same run |

Verdict: **VERIFIED**. Owner decisions Q1–Q4 recorded, not defects.

**B. repository-cleanup** (`LEDGER.md`, `STATE.json`), P00–P10, acceptance candidate `f2db495`:

- F-001…F-011, F-017, F-019, F-020, F-022, F-027, DEL-001…011, and the 29 Codex E/T/D/C/F-CX findings:
  executed per the P09/P10 final reports; no per-finding sha is named for most (phase commits only), which
  matches this ledger's own convention (findings tables cite phases, not shas — verified against the
  ledger text itself, not treated as a gap).
- F-012 `0451ef9`, F-013 `8c584f7`, F-014/015/016 `b8ea888`, F-018/026 `64e555e`, F-025 `adbe8e1`, F-029
  `9c47f30`: all ancestors of HEAD. Cited tests (`test_units_shipped_surface.py`, `test_hooks.py`,
  `test_units_capabilities.py`) collected and present.
- **F-024**: fixed by ADR-011 (P10), commits `c963c67` (interrupted candidate, correctly not shipped —
  see the ledger's own account of the `cmd_governance_gates` bypass it caught) and `f2db495` (accepted).
  Eleven `test_units_gate_policy.py::test_f024_*` tests confirmed present. CI run `35541739417` @
  `d384ceb` (byte-identical product to `f2db495`): **success on all 4 jobs**, confirmed via API. The
  ledger's own P09→P10 bookkeeping (LEDGER.md:266–277, 349–394) already reconciles the "VERIFICATION_BLOCKED"
  P09 status against the later P10 "COMPLETE" status without needing a further note from this work: P09 is
  a closed acceptance record left as written, P10 supersedes it for AC-01/AC-09, and `STATE.json` (read in
  full) already reflects P10 complete, `open_finding_ids: ["F-028"]` only (F-028 is a documented live
  limitation, not an open defect) — **not stale**, contrary to an initial read of the header lines alone.
- **D-03** (no LICENSE file): owner action, outstanding. **D-06** (`.claude/settings.local.json` history):
  owner action, outstanding, out of scope by the plan's own D-06 disposition.

Verdict: **VERIFIED**, with D-03 and D-06 left for the owner (not defects; the ledger itself records them
as such).

**C. workitem-isolation** (`FINDINGS.md`), merged `369ff96`:

- F-101 (ADR-012), F-102, F-103: all confirmed fixed/resolved, with regression tests present and Codex
  review rounds (10 + 6 findings, all accepted) recorded in the same file. The header lines ("CONFIRMED,
  open") are stale relative to the file's own later sections; a dated reconciliation note is appended to
  `FINDINGS.md` (this session) rather than editing the headers, matching the append-only convention this
  repository's ledgers already use elsewhere (repository-cleanup's P09/P10 split is the precedent).
- No CI run is cited for this work specifically; it is covered by HEAD's own CI run `35738630082`
  (4/4 green), since HEAD contains all three fix commit sets.

Verdict: **VERIFIED**.

**D. workitem-docs-alignment** (`LEDGER.md`, `STATE.json`), merged `48a853a`:

- D-01…D-07, D-09…D-12 (D-08 is a skipped id in the plan's own numbering, not a missing item — confirmed
  by grep, D-07 is immediately followed by D-09 throughout), R1-D01…D08, R2-D01…D09: all closed, commits
  `9dc1f7f`, `cdf8316`, `b83cf4a`, `44c5d24`, `ecb749c`, `7da1f6c`, `a669b03` confirmed ancestors of HEAD.
- OPEN-03 (full suite): closed by CI run `35727873456` @ `7477e9f` — **success on all 4 jobs**, confirmed
  via API.
- OPEN-01, OPEN-02: explicitly handed to the next ledger (this repo's `open-items-01-02`), not this
  ledger's to close.

Verdict: **VERIFIED**.

**E. open-items-01-02** (current branch's own prior work), `27c3be0`, `70f169e`, `0057425`:

- OPEN-01 (bootstrap scan message) and OPEN-02 (startup contract test): implemented, `tests/test_units_startup_contract.py`
  (14 tests, confirmed present and — pending the targeted run below — passing), `tests/test_integration_02_to_05.py`
  passing per the ledger, `tests/test_dry_run_contracts.py` (118) passing per the ledger.
- CI run `35738630082` @ `0057425`: **success on all 4 jobs**, confirmed via API. This was not available
  when the ledger was last written (`STATE.json` says "not pushed"); a dated reconciliation note is
  appended to `LEDGER.md` recording the current branch/push/CI facts.
- **Gap: the two-level Codex review never ran.** Round 1 was killed by the background-shell memory
  reaper before producing output; round 2 never started. Per the owner's decision this session (O2), this
  review runs now, in Stage 0, before OPEN-01/02 counts as verified. See "OPEN-01/02 review" below.

Verdict: **CONDITIONALLY VERIFIED** pending the review below and the targeted regression run.

### Targeted regression run (this session)

Command: `python -m pytest -q tests/test_units_execution_identity.py tests/test_units_gate_artifacts.py
tests/test_units_implementation_evidence.py tests/test_units_manifest_changes.py
tests/test_units_documented_commands.py tests/test_dry_run_contracts.py tests/test_integration_10_to_13.py
tests/test_units_shipped_surface.py tests/test_units_install_contract.py tests/test_units_gate_policy.py
tests/test_units_policy_midflight.py tests/test_units_capabilities.py tests/test_units_governance.py
tests/test_units_startup_contract.py tests/test_integration_02_to_05.py tests/test_integration_06_to_09.py
tests/test_units_doc_links.py tests/test_lint_skill.py --tb=short -rf` (via `rtk proxy`, to get
unfiltered pytest output — the default filtered summary reported "No tests collected" for
`--collect-only`, so raw output was used throughout Stage 0).

**Result (first attempt): 1 failed, 2139 passed, 1719.55s.** The one failure,
`test_no_policy_default_value_is_restated_outside_sdle_py`, was **caused by this session**, not a
pre-existing defect: committing `BRIEF.md` under `.sdle/implementation-state/requirements-refinement/`
(a path `searchable_files()` scans) put the owner's brief — which quotes five underscored check ids
verbatim in its §1 grounding table — inside invariant 7's restatement search. `MAINTENANCE_RECORDS`
was widened from one hardcoded directory to an enumerated tuple of two (commit `e5af3a4`), preserving
F-025's actual guarantee (no directory is exempt merely by living under `implementation-state/`) while
accommodating this record's identical, legitimate need to quote engine vocabulary as evidence. Fixed
inline (a failure in the phase currently being worked is normal development, not a §9 defect).

**Result (after the fix): `tests/test_units_governance.py` + `tests/test_units_capabilities.py` rerun
in full — 359 passed, 376.82s.** Combined with the unaffected 2139 from the first run, every file in
the targeted set is green. `lint-skill`: 0 failures. Import check: OK.

### OPEN-01/02 review

*(recorded below once run)*

## Defect register

Format: id, source, description, reproduction, affected surfaces, dependencies, status, branch,
commits, tests (§9). The MAINTENANCE_RECORDS gap is not listed here — self-caused, fixed inline, per
the brief's own rule that a failure in the phase currently being worked is not a §9 defect.

### DEF-RR-006 — no path containment on several CLI path arguments (OPEN, out of scope)

- **Source:** Stage 0, third targeted-verification pass of the OPEN-01/02 fix (finding V3-04,
  `runs/20260928T031813-round2-codex-open-items-verify3.a1.review.json`).
- **Description:** `cmd_governance_assess`'s `--input`, `cmd_discovery_assess`'s `--input`, `cmd_sha`'s
  path argument, and `cmd_artifact_record`'s `--path` each join or open a user-supplied path with no
  containment check — no rejection of absolute paths, no rejection of `../` traversal, no symlink-escape
  check. `scripts/sdle.py`: `cmd_governance_assess` `target = Path(args.input)` / `target = paths.project_root
  / args.input` at lines 5436/5438; `cmd_discovery_assess`, the identical pattern at lines 6103/6105;
  `cmd_artifact_record` at `cmd_artifact_record` (line 9192); `cmd_sha` (line 12083).
- **Reproduction:** In a bound, otherwise-ordinary WorkItem, `sdle.sh governance assess --input
  ../outside-project/secret.json` (a file outside `project_root`) is read and its content validated —
  refused only for missing quality-check keys (`quality_incomplete`), never for the path leaving the
  repository. Confirmed live against `3bd64fc`.
- **Affected surfaces:** `cmd_governance_assess`, `cmd_discovery_assess`, `cmd_sha`, `cmd_artifact_record`
  — none of the DEF-RR-001..005 or later fixes touch any of these four functions.
- **Dependencies:** None. Independent of `safe_repo_path`/`_lexically_safe_path`, which this defect's own
  fix would presumably reuse, but nothing here depends on this session's other work to be fixed or to be
  reproduced.
- **Status:** OPEN. Owner decision (this session, 2026-09-28): record only, triage as its own piece of
  work — pre-existing (predates this entire body of work; `cmd_governance_assess` is original-engine
  code), and outside OPEN-01/02's mapped impact surface (the untrusted-content scan and its
  acknowledgement mechanism), so it is recorded with a reproduction and left unfixed in this change, per
  the brief's own defect-scoping rule (C8/§9: a pre-existing defect *outside* the impact surface is
  recorded, not fixed here).
- **Branch / commits:** None — not fixed in this change.
- **Tests:** None added — recorded, not regression-tested, since it is not being fixed here.

## Local full-suite run — interrupted, resolved via CI

The local full-suite run (`runs/20260927T194546-def-rr-full-suite.*`, via `runctl.py --sample-memory 10`)
was stopped by Claude Code's background-shell memory reaper at ~9% progress. `phys_avail_gb` was ~2.2 GB
for the whole sampled window, from before the run had reached its first percent marker — a machine-wide
condition, not something the pytest process caused (`python_ws_mb` stayed under 110 MB). Full detail in
the run's own JSON record. Not restarted, per the harness's instruction that a reaped command is not
restarted unattended.

Resolved the same way `workitem-docs-alignment`'s ledger recorded for an identical reap: pushed
`feat/requirements-refinement` (authorised, O3) and read the full-suite result from GitHub Actions
instead — strictly stronger evidence than a single local combination.

## Full suite — PASS, on CI

Two attempts: run `36346009675` @ `fd51a5c` failed all four cells on
`test_units_governance.py::test_no_policy_default_value_is_restated_outside_sdle_py` and
`test_units_discovery.py::test_n14_no_discovery_vocabulary_is_restated_outside_sdle_py`, both flagging
`.sdle/implementation-state/open-items-01-02/runs/20260927T182716-p08-codex-open-items-round1.a1.events.jsonl`
(diagnosed via `check-runs/<id>/annotations`, since raw job-log download needs admin rights this token
does not have). Fixed by widening `MAINTENANCE_RECORDS` a third time (commit `84925f2`) — confirmed not
platform-specific: all four cells failed identically before the fix.

Run [36347512584](https://github.com/muhammadallee/sdle-latest/actions/runs/36347512584) @ `84925f2`:

| job | conclusion |
|---|---|
| ubuntu-latest / Python 3.11 | success |
| ubuntu-latest / Python 3.13 | success |
| windows-latest / Python 3.11 | success |
| windows-latest / Python 3.13 | success |

This satisfies the brief's F12 ("CI passed means all four cells passed") and closes the local
full-suite run's interruption above — CI ran it (plus `lint-skill`) at `84925f2`, which contains every
DEF-RR-001..005 and MAINTENANCE_RECORDS commit.

## Stage 0 — verdict

**VERIFIED.** All five prior-stabilization ledgers check out (D01–D06, repository-cleanup,
workitem-isolation, workitem-docs-alignment, open-items-01-02 — the last conditional on the review and
fix above, now both done). Owner decisions (D-03, D-06, F-028, F-103) left with the owner, not defects.
Two reconciliation notes appended. Five defects (DEF-RR-001..005) found genuinely open by the missing
Codex review, fixed under §9, reviewed locally and on CI. Two further defects (the MAINTENANCE_RECORDS
gaps) were self-caused by this session's own evidence-writing and fixed inline, per the brief's own rule
that a failure in the phase currently being worked is not a §9 defect.

Next: Level 2 Codex review of the DEF-RR-001..005 fix (round 2 of the OPEN-01/02 review), then Stage 1.

## OPEN-01/02 — full closure

Both formal review rounds plus one targeted verification pass are complete:

| Stage | Result |
|---|---|
| Round 1 (Codex, candidate `0057425`) | 9 findings; all dispositioned (`round1.reply.md`); 5 registered as DEF-RR-001..005 |
| Owner decision | Shape (a): re-check at `governance assess` |
| DEF-RR-001..005 fix | New pre-init acknowledgement record, `accept-content --path`, the new `governance_content_unacknowledged` refusal, and five corrected surfaces (hook, `sdle-start.md`, dry-run 05, Reference Guide, GETTING-STARTED) |
| Round 2 (Codex, candidate `75187b6`, product-identical to the `6b6c1e6` the prompt named) | 4 dispositions REVISED, 4 new findings (R2-D01..D04); all fixed (`round2.dispositions.md`) — includes a real regression (bare `accept-content` silently stopped satisfying the new check) and a TOCTOU gap, both caught only because a second round ran |
| Targeted verification of the round-2 fix | 5 more findings (V-01..V-05), all fixed — a second, deeper TOCTOU the first fix missed, a missing-file edge case, a duplicate-audit bug, an atomicity-ordering bug, and an incomplete refusal-attribution list |
| CI (all four cells) | `36347512584` (round-2 fix) → `36362088912` (V-01..V-05 fix, failed on a self-caused historical-narration violation) → `36363773501` (fixed) — **success on all four cells** |

Every finding across three passes was verified against source or the live CLI before being accepted —
never taken on Codex's word, and two of the three passes found something the previous one missed. No
disagreement ever needed the owner beyond the one shape decision already made. OPEN-01 and OPEN-02 are
both genuinely closed, not merely tested-green.

## Stage 0 — final verdict

**VERIFIED.** All five prior-stabilization items check out; OPEN-01/02 specifically required real
engine, hook, prompt, doc and test work — five DEF-RR items, a real regression, two TOCTOU gaps, three
smaller bugs — none of which the original round-1 fix alone would have caught. Proceeding to Stage 1.

## Correction — 2026-09-28

The "Stage 0 — final verdict: VERIFIED" and "OPEN-01/02 — full closure" sections above were premature.
An independent second-look review (not a third formal Codex round — a self-review before committing to
that verdict) found six more real gaps in the targeted-verification fix itself, including a vacuous test
(V-01's own regression test passed against the pre-fix commit too — confirmed by running it there) and a
store that silently dropped a human decision instead of being append-only. All six fixed, verified
locally (461 + 190 tests), pushed at `2ef73de`. This is now "fixes applied, CI pending" — not verified —
until CI confirms and, per the review protocol, one narrow targeted Codex verification of this diff runs.
Nothing above is rewritten; this correction is appended, matching this ledger's own convention.

## OPEN-01/02 — closure, final (2026-09-28)

CI: `36374476221` @ `3bd64fc` — success on all four cells (the commit carrying V3-01/V3-03's fixes, the
last substantive change to this fix). Full arc, honestly stated this time — the `ee29b54` premature
verdict is not repeated: four verification passes ran (2 formal Codex rounds + 3 targeted follow-ups),
and each of the first three found genuine defects the previous pass missed. The pattern stopped only
when a targeted pass's own `closure_assessment` recommended owner escalation rather than another pass,
per the stopping rule this session adopted in advance of running it.

Fifteen distinct findings fixed and regression-tested across the four passes (DEF-RR-001..005, R2-D01..
04, V-01..05, V2-01..05, V3-01, V3-03), every fix's test confirmed red against the commit immediately
before its own fix. One item (V3-02) is a documented, engine-wide limitation — the code change Codex
itself suggested would not have closed it, explained in `safe_repo_path`'s own docstring. One item
(DEF-RR-006 / V3-04) is a real, pre-existing, out-of-scope finding, recorded in the defect register
above with a live reproduction, left unfixed here on the owner's explicit decision (2026-09-28).

**Owner decision (2026-09-28):** OPEN-01/02 is sufficiently closed to proceed to Stage 1. Recorded here
as the basis for that decision, not asserted independently by this session.

## Stage 0 — final verdict

**VERIFIED**, on the owner's confirmation above, following CI success on the actual final commit
(`36374476221` @ `3bd64fc`) — not asserted ahead of either, this time. Proceeding to Stage 1.

## Stage 1 — baseline reproduction (brief §4.1A.5, 2026-09-28)

`python scripts/sdle.py lint-skill` and the full pytest suite are the mandated baseline. The full suite
was last run and CI-verified at `3bd64fc` (`36374476221`, all four cells green) as part of Stage 0's own
closure. `git diff --stat 3bd64fc..HEAD -- scripts .claude "tests/*.py"` is empty — no engine-relevant
file has changed since that verified commit, only `.sdle/implementation-state/requirements-refinement/`
records and `tests/fixtures/requirements-quality/*` corpus documents, neither of which the full suite or
`lint-skill` exercises. The prior CI result is therefore still the current baseline, not re-run here.
Re-verified today rather than assumed stale-but-fine: `python scripts/sdle.py lint-skill` → `ok: true`,
zero failed checks; `python -m pytest --collect-only -q` → 3175 tests collected, no collection errors.
No pre-existing failures to enter into the defect register.

## Stage 1 — evaluation corpus (2026-09-28)

Built `tests/fixtures/requirements-quality/`: `clean-baseline.md` plus one `defect-<check-id>.md` per
of the twelve quality-check ids, each a ~55-60 line "Link Shortener Service" requirements document.
Labels (`labels.json`, the expected failing check ids per document) are kept outside the working tree
per this session's own discipline, so a subagent with Glob/Read cannot see them.

**Two live assessor pilot runs against the pre-fix corpus, at commit `d3d8794`, found two authorial bugs
before the corpus was trusted:**

1. `clean-baseline.md` run 1 of 3 was flagged `contradictions: FAIL` by a real fresh-context assessor:
   the shared Constraints sentence "Must authenticate every request against the existing internal SSO
   (SAML), no separate login." genuinely conflicts with the Security section's "redirection itself is
   unauthenticated" — present verbatim in 12 of 13 documents. Fixed by scoping the sentence to
   management-API requests and naming the redirect exception explicitly, in all 12 affected documents.
2. `defect-problem_statement.md` run 1 of 3 correctly flagged `problem_statement: FAIL` (the intended
   defect) but also flagged `ambiguity: FAIL` on "under normal load" in the latency NFR — present in 11
   of 13 documents (the twelfth, `defect-ambiguity.md`, uses vague load language deliberately as its own
   seeded defect and is untouched). Fixed by replacing the qualifier with a quantified figure ("at up to
   200 redirects per second") everywhere except that one document.

Both pilot runs are **discarded** — they assessed pre-fix document text and are not comparable to the
corrected corpus. Neither counts toward the 13×3 measurement plan.

**Two further defects found by self-review (not a live run) before any further dispatch, on the same
"authorial mistake in the shared template, not the labelled signal" standard as the two above:**

3. Every document's AC-2 specified an HTTP 301 (permanent, cacheable) redirect while also requiring
   `click_count` to increment and `AC-3` to require a live 410 on an expired link — a permanent redirect
   cached by the client after the first visit would make both unreachable. Fixed by adding
   `Cache-Control: no-store` to AC-2's redirect, in all 13 documents (AC-2 is otherwise absent only from
   `defect-acceptance_criteria.md`, whose seeded defect is precisely that AC-2 does not exist).
4. Every document's Constraints section claimed "expiry uses a database TTL" while running on Postgres
   14, which has no native row-TTL/auto-expiry feature, and while the Data Model's `expires_at` column
   and AC-3's 410-on-expired-link both presuppose the row still exists after expiry (a TTL auto-delete
   would make it a 404, not a 410). Fixed by rewording to read-time comparison against `expires_at`,
   with expired rows explicitly retained, in all 13 documents.
5. `defect-dependencies.md`'s Constraints line read "...using some shared infrastructure" — the word
   "some" is on the lint's vague-term list (§3.3), so this incidentally lint-flagged `ambiguity` on top
   of the document's actual seeded defect (a missing Dependencies section), which `labels.json` does not
   list. Fixed by naming the dependency concretely ("the shared Postgres instance"), matching every
   other document's Constraints wording.

**Verification after all five fixes**, against the corrected corpus (committed `9ec6d4a`):
- The lint prototype (`.sdle/implementation-state/requirements-refinement/lint-prototype.py`) produces
  `[]` on `clean-baseline.md` and on every document whose seeded defect the lint floor does not cover
  (§3.3 only floors `blocking_unknowns`, `ambiguity`, `acceptance_criteria`, `out_of_scope`, `nfrs` and
  duplicate-id `contradictions` — never `problem_statement`, `scope`, `constraints`,
  `security_data_implications`, `compatibility` or `dependencies`, so those six documents correctly lint
  clean even though their assessor-level defect is real). `check_missing_sections` only checking for
  the Acceptance and Out of Scope sections (not Purpose/Scope/Constraints) was checked against §3.3's
  text and is spec-correct, not a bug — those three sections' absence is a semantic (`problem_statement`
  / `scope` / `constraints`) finding, never a lint one.
- All 13 documents re-verified clean under `sdle.scan_text()` (the injection-pattern scanner).
- `tests/fixtures/` is outside `searchable_files()`'s scan roots (`conftest.py:586`), so the corpus needs
  no `MAINTENANCE_RECORDS` entry; the two restatement-guard tests
  (`test_no_policy_default_value_is_restated_outside_sdle_py`,
  `test_n14_no_discovery_vocabulary_is_restated_outside_sdle_py`) and
  `test_the_restatement_search_skips_only_the_maintenance_records` all pass unchanged.

Corpus and the `sdle-requirements-review` assessor prompt draft committed at `9ec6d4a`, so every
forthcoming assessor run can cite the exact document SHA it assessed. Next: pilot `clean-baseline.md`
×3 as a gate before the remaining 36 dispatches, judging any recurring finding on its own merits rather
than editing the corpus until an assessor says PASS (per this session's own "converge on evidence, not
verdict" discipline, restated by the advisor for this exact step).

## Stage 1 — corpus measurement results (2026-09-28)

Gate passed: 3 pilot runs on the corrected `clean-baseline.md` came back 2/3 fully clean, 1/3 with a
single non-blocking `security_data_implications` FAIL (a defensible per-resource-authorization
judgment call, not a corpus defect — kept as data, not chased away, per the advisor's explicit
instruction). Proceeded to the remaining 12 documents times 3 runs = 36 dispatches, all against corpus
commit `9ec6d4a`, each dispatch prompt containing only the document text (no filename, no check-id
hint) with an explicit "use no tools" instruction, capped at 4 concurrent Agent calls at a time. All 39
raw results are saved under `runs/assessor-<check-id>-run<n>.json`, each citing the document's blob SHA.

### Assessor precision/recall per check (39 runs total: 13 documents times 3 runs)

| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| problem_statement | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| scope | 3 | 0 | 3 | 0 | 0.00 | undefined, no positive predictions |
| out_of_scope | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| acceptance_criteria | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 6 | 6 | 0 | 3 | 1.00 | 0.67 |
| contradictions | 3 | 3 | 0 | 2 | 1.00 | 0.60 |
| constraints | 3 | 0 | 3 | 0 | 0.00 | undefined |
| nfrs | 6 | 6 | 0 | 0 | 1.00 | 1.00 |
| security_data_implications | 3 | 2 | 1 | 1 | 0.67 | 0.67 |
| compatibility | 3 | 0 | 3 | 0 | 0.00 | undefined |
| dependencies | 3 | 0 | 3 | 0 | 0.00 | undefined |
| blocking_unknowns | 3 | 3 | 0 | 1 | 1.00 | 0.75 |

`ambiguity` and `nfrs` each have 6 positive instances because `labels.json` labels both
`defect-ambiguity.md` and `defect-nfrs.md` for both checks — the vague-NFR defect naturally trips both,
noted in `labels.json`'s own `_notes` before any run occurred.

### The headline finding: a systemic recall gap on whole-section absence

Four checks were missed unanimously, 3 of 3, on every single run of their labeled document: `scope`,
`compatibility`, `constraints`, `dependencies`. In every one of these four cases the seeded defect is
the same shape: the entire relevant section (or, for `scope`, the entire "In scope:" list) is absent
from the document, with no other section pointing at or alluding to it. The assessor consistently read
the surrounding context (Data Model, Dependencies mentioning SSO/Postgres, Acceptance criteria, the
Purpose paragraph) as sufficient and passed the check, rather than noticing the structural absence.

This contrasts sharply with `out_of_scope` (3/3 caught) and `problem_statement` (3/3 caught), which are
also whole-content-absence defects but differ in one respect: `out_of_scope`'s document still has an
"In scope:" list immediately above where "Out of scope:" should be, giving the assessor a structural
cue (an unpaired sibling) to notice the gap; `problem_statement`'s document opens cold on "## Scope"
with no introduction at all, which is a much louder signal than a missing later section. The
`security_data_implications` document is the clearest confirming case: this session's own earlier
wording fix (scoping the SSO-authentication constraint) added the sentence "Redirect requests are the
one exception, per Security and Data Handling below" to every document's Constraints section, and in
that document specifically, that phrase is a dangling cross-reference to a section that does not
exist. 2 of 3 runs caught the defect specifically by following that broken reference; the third run,
which read the document without fixating on the cross-reference, missed it. That is a real, unplanned
but informative interaction between an earlier corpus fix and a seeded defect, not a flaw in either.

Conclusion for the assessor design (Stage 3 relevance): the LLM assessor is reliable at catching
textual problems (contradictions, vagueness, unmeasured NFRs, weak acceptance criteria) but has near
zero recall for structural absence when nothing else in the document points at the missing content. A
section-presence check for the five section-shaped quality checks (`out_of_scope`, `constraints`,
`compatibility`, `dependencies`, `security_data_implications`) would be cheap, high-precision,
deterministic, and would close exactly this gap — worth flagging as a candidate lint rule addition for
a later revision of §3.3, separate from and additional to the six rules already specified there (which
do not cover this gap, since §3.3 explicitly scopes "missing sections the checks presuppose" to only
`acceptance_criteria` and `out_of_scope`).

### Agreement rate across the 3 runs per document (full 12-key vector, identical bytes)

9 of 13 documents (69%) produced byte-identical verdict vectors across all three fresh-context runs.
The 4 that did not:

- `clean-baseline.md`: 1/3 runs added an unlabeled `security_data_implications` FAIL (a defensible
  authorization-scoping judgment call).
- `defect-blocking_unknowns.md`: 2/3 runs added an unlabeled `contradictions` FAIL (the HTTP-301
  caching-vs-click-tracking concern this session partially mitigated with `Cache-Control: no-store`,
  which 2 of 3 readers judged an insufficient guarantee against caching bots).
- `defect-security_data_implications.md`: split 2/1 on the labeled `security_data_implications` FAIL
  itself, described above.
- `defect-acceptance_criteria.md` (not a disagreement, but worth noting): all 3 runs unanimously added
  an unlabeled `ambiguity` FAIL alongside the labeled `acceptance_criteria` FAIL — a natural, expected
  overlap, same pattern as `labels.json`'s own documented ambiguity/nfrs overlap.

This is the honest measurement of `quality_verdict_flip`'s real-world trigger rate on unchanged text:
roughly 1 in 3 documents produces some inter-run variance, concentrated in borderline judgment calls
(residual-risk framing, caching semantics) rather than in the clearly-labeled primary defects, which
were never missed across all three runs of any document where the assessor caught them at all — recall
failures were unanimous misses (0/3), not split votes, for every check that had a miss.

### Lint prototype precision/recall (deterministic, one measurement per document, not three)

Re-run fresh against the corrected corpus. Findings (rule-level, mapped to check ids per §3.3):

clean-baseline.md: none. defect-acceptance_criteria.md: acceptance_criteria. defect-ambiguity.md:
ambiguity, nfrs. defect-blocking_unknowns.md: blocking_unknowns. defect-compatibility.md: none.
defect-constraints.md: none. defect-contradictions.md: none. defect-dependencies.md: none.
defect-nfrs.md: ambiguity (not nfrs — see below). defect-out_of_scope.md: out_of_scope.
defect-problem_statement.md: none. defect-scope.md: none. defect-security_data_implications.md: none.

For the six checks §3.3 designs the lint to cover: `blocking_unknowns` 1/1, `out_of_scope` 1/1,
`acceptance_criteria` 1/1 and `ambiguity` 2/2 are all perfect (precision 1.0, recall 1.0, zero false
positives on any of the 13 documents including the clean baseline — the floor-eligibility requirement
in §3.3 is met by all four). `nfrs` is 1/2 (recall 0.5): `check_quant_nfrs_without_measure` correctly
fires on `defect-ambiguity.md`'s NFR wording but not on `defect-nfrs.md`'s ("Redirects must be fast
enough that users do not notice any delay" / "handle a high volume... without degrading") — the
`QUANT_ATTR` keyword regex apparently does not match this exact phrasing while the vague-terms list
does, so the document is floored via `ambiguity` but not via `nfrs` itself. This is a real gap in the
`nfrs` rule's keyword coverage, worth a follow-up fixture and regex tightening in Stage 3 rather than a
blast-radius concern (advisory-only status means this gap costs nothing today). The sixth lint rule
(duplicate ids to `contradictions`) has no positive fixture in this corpus and is untested here — a gap
in the corpus, not in the rule; a duplicate-id fixture pair should be added before Stage 3 uses this
corpus as the lint's regression suite.

Lint's zero false-positive rate on `clean-baseline.md` and on every document whose seeded defect it
does not target (the six checks it does not attempt) confirms the §3.3 floor-eligibility requirement
in the Option-3/D7 corpus this design was measured against.

Discarded: the 2 pilot runs against pre-fix document text (`clean-baseline.md` run 1,
`defect-problem_statement.md` run 1, both from before commit `9ec6d4a`) are not part of the above
tables — they assessed stale bytes and are superseded by the clean-baseline gate's 3 fresh runs and
`defect-problem_statement.md`'s 3 runs recorded above.

## Stage 1 — corpus measurement, adjudication pass (2026-09-28)

Advisor review of the 39-run measurement above found the "0.00 recall on 4 checks" headline needed
checking against `assessor-prompt-draft.md`'s own check definitions, not against `labels.json` alone,
and that two of this session's own earlier corpus edits had bled adjacent content into the affected
documents, potentially inflating or deflating specific findings:

1. `defect-dependencies.md`: the same-session fix that replaced its deliberately vague "some shared
   infrastructure" with a concretely-named dependency (applied to fix an incidental lint/ambiguity
   trigger) had incidentally strengthened the document's own dependency-naming and undermined its
   seeded defect. Reverted to the original vague wording; the ambiguity trigger is accepted and the
   document dual-labeled (`dependencies`, `ambiguity`), matching the existing ambiguity/nfrs overlap
   pattern already in `labels.json`.
2. `defect-security_data_implications.md`: an earlier corpus-wide wording fix (the auth/redirect
   contradiction fix, applied uniformly across all 13 documents) had added "Redirect requests are the
   one exception, per Security and Data Handling below" to this document's Constraints section — a
   dangling cross-reference to a section this document deliberately omits, an unintended structural cue
   pointing straight at the gap. Removed; the sentence now ends at "...no separate login."
3. `defect-constraints.md` / `defect-compatibility.md`: each document's Dependencies section carried a
   clause ("version already pinned by platform team" / "no schema changes to other services' tables")
   reading as compatibility- or constraint-flavored detail once the document's own dedicated section for
   that check is removed. Trimmed to bare dependency names (still enough to satisfy each document's
   own dependencies check, which is not its seeded defect there).
4. `defect-acceptance_criteria.md`'s vague replacement text ("The feature is done when it works well and
   users are satisfied with how it behaves") meets `ambiguity`'s own definition (vague, unmeasurable
   normative language). All 3 original runs correctly caught this alongside the labeled
   `acceptance_criteria` FAIL — a label gap, not an assessor false positive. Relabeled dual
   (`acceptance_criteria`, `ambiguity`).
5. `defect-scope.md` was not re-seeded: the Purpose paragraph and the four AC-* criteria (both
   required elsewhere for `problem_statement`/`acceptance_criteria` reasons, and shared boilerplate
   across the corpus) already describe what is being built in concrete enough terms that a reasonable
   reader could argue `scope`'s own definition ("states what is being built, concretely enough to bound
   the work") is satisfied without a dedicated "In scope:" list. Stripping that content to force a
   cleaner scope-only defect would corrupt this document's non-defects on two other checks. Any
   assessor PASS on this document's `scope` check is recorded as a contested, defensible read, not
   folded into the clean-recall-failure count below.

All four edited documents re-verified clean under `sdle.scan_text()` and the lint prototype, committed
at `eefc661`. The four edited documents (`dependencies`, `security_data_implications`, `constraints`,
`compatibility`) were then re-dispatched, 3 fresh-context runs each (12 new dispatches), against this
corrected text. The prior 3 runs for each are kept on disk, renamed `*-superseded.json`, not deleted —
this ledger entry is the record of why they no longer count.

Provenance note: every run JSON's `dispatched_at` field is a placeholder ("00:00:00Z" or "not
recorded") — actual per-dispatch wall-clock times were not captured during either measurement pass.
Treat the field as absent, not as a real timestamp; nothing in this session's conclusions depends on it.

### Result: the headline finding survives, refined

- `dependencies`: confirmed clean 0/3 on the re-verified document (previously contaminated by this
  session's own dependencies-naming mistake — now a genuine, uncontaminated miss). `ambiguity` correctly
  caught 3/3 as expected from the dual-label.
- `constraints`: confirmed clean 0/3, unaffected by trimming the adjacent Dependencies detail. One
  run (3) additionally caught an unlabeled `contradictions` FAIL — see below.
- `compatibility`: confirmed clean 0/3, unaffected by trimming the adjacent Dependencies detail. The
  assessor still appears to credit AC-2's HTTP-301 mention (shared boilerplate present in every
  document, not removable without corrupting `acceptance_criteria`) as partial compatibility coverage.
- `security_data_implications`: recall fell from the original 0.67 (2/3) to 0.33 (1/3) once the
  dangling cross-reference was removed — direct confirmation that the cue was inflating detection, and
  the true difficulty of this document's seeded defect (a wholly absent section with no remaining
  pointer to it) is closer to the `compatibility`/`constraints`/`dependencies` pattern than the original
  number suggested. The one catch (run 2) found the defect via a different, legitimate angle
  (authorization/ownership gap) than the intended reason (section absence) — both count as the check
  correctly failing.
- `scope`: left at the original 0/3, but now flagged contested rather than confirmed per point 5
  above — do not cite this as a clean recall failure without noting the caveat.

Net: three of the four originally-flagged checks (`compatibility`, `constraints`, `dependencies`) are
now more rigorously confirmed misses, not artifacts of corpus construction. `security_data_implications`
turned out worse than first measured, not better. Only `scope` remains genuinely unresolved. The
headline conclusion in the prior section — the assessor has near-zero recall for structural absence when
nothing else in the document points at the gap, and reliably catches everything else — stands,
strengthened rather than weakened by this adjudication pass.

### Adjudicated precision/recall table (supersedes the table in the prior section)

| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| problem_statement | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| scope | 3 | 0 | 3 | 0 | 0.00 (contested, not re-tested) | undefined |
| out_of_scope | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| acceptance_criteria | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 12 | 12 | 0 | 0 | 1.00 | 1.00 |
| contradictions | 3 | 3 | 0 | 3 | 1.00 | 0.50 |
| constraints | 3 | 0 | 3 | 0 | 0.00 | undefined |
| nfrs | 6 | 6 | 0 | 0 | 1.00 | 1.00 |
| security_data_implications | 3 | 1 | 2 | 1 | 0.33 | 0.50 |
| compatibility | 3 | 0 | 3 | 0 | 0.00 | undefined |
| dependencies | 3 | 0 | 3 | 0 | 0.00 | undefined |
| blocking_unknowns | 3 | 3 | 0 | 1 | 1.00 | 0.75 |

`ambiguity`'s positive-instance count grew from 6 to 12 (adding `defect-acceptance_criteria.md` and
`defect-dependencies.md` per points 1 and 4 above), all 12 caught, and its 3 original false positives
(all from `defect-acceptance_criteria.md`) are now correctly counted as true positives — precision rose
to 1.00. `contradictions`'s false-positive count rose from 2 to 3 (the new `defect-constraints.md` run 3
catch), precision fell to 0.50.

### Agreement rate, updated

8 of 13 documents (62%, down from the original 69%) now produce byte-identical 12-key verdict vectors
across all 3 fresh runs. `defect-constraints.md` moved from agreeing to disagreeing (run 3's unlabeled
contradictions catch); `defect-dependencies.md` and `defect-compatibility.md` remain agreeing (each
unanimous across their 3 re-verified runs); `defect-security_data_implications.md` remains disagreeing.

### A secondary, unplanned finding: the AC-2 caching fix did not fully resolve its own tension

This session's earlier fix for the 301-caching-vs-click-tracking concern (found during the original
clean-baseline pilot, the "Stage 1 — evaluation corpus" section above) added `Cache-Control: no-store`
to AC-2 rather than changing the redirect's status code, to preserve the Compatibility section's claim
that existing bots see the same 301 they always have. `defect-constraints.md` run 3 shows this did not
fully resolve the underlying tension — it relocated it into an explicit textual contradiction between
the Compatibility section (301, cached, "work exactly as they do") and AC-2 (301, `no-store`, "every
visit reaches the service"). This appeared in 1 of the 51 total dispatches run against text carrying
this fix, so it is rare but real, and is left as measured data rather than patched again — a third
editing pass risks the same kind of unintended confound already found twice in this section. Flagged
for the Stage 2 review, not resolved here.

## Correction — 2026-09-28: retracting the "confirmed / strengthened" verdict above

A second advisor review found that the adjudication pass above repeated the exact failure mode it was
meant to fix: it re-asserted "confirmed clean 0/3" for `compatibility` and `constraints` without
checking whether PASS was actually the *correct* answer under `assessor-prompt-draft.md`'s own
definitions, rather than only under `labels.json`. Nothing above this line is rewritten; this section
is the correction, per this ledger's own convention.

**The discriminating experiment (run, not argued):** `defect-compatibility.md`'s Purpose paragraph was
given a relevance cue — "It replaces the current ad-hoc shortener; links it issued over the last six
months are already embedded in docs and read by deployed link-preview bots" — with **no** compatibility
requirement added anywhere. 3 fresh dispatches: **3/3 caught it**, unprompted, citing exactly that
unaddressed migration/continuity question. This is decisive: the document's original 0/3 was not an
assessor blind spot for structural absence — it was a corpus-construction defect. Deleting the
Compatibility section had also deleted the only sentences establishing that compatibility was relevant
at all, and the assessor correctly declines to invent a concern the text never raises. **The cued text
is now the corpus's `defect-compatibility.md` fixture** (committed; old runs kept as
`*-superseded2.json`). There is no demonstrated structural blind spot. The narrow, real limitation —
worth one line in the Stage 3 `sdle-requirements-review` agent prompt — is that the assessor will not
infer relevance the document's own text never raises; it is not that the assessor fails to notice named
sections are missing.

**`constraints` and `scope` are not confirmed misses.** Both documents still carry content that a
generous, defensible reading of their check's own hedge ("where any genuinely apply") could credit:
`defect-constraints.md` has the 301 requirement, slug format, NFR numbers and the non-sequential-slug
rule scattered across other sections; `defect-scope.md` has its required Purpose paragraph and AC-*
criteria. The compatibility experiment proved this exact mechanism can flip a result from miss to catch
when it applies — no equivalent controlled test was run for these two, so neither is reported as a
confirmed recall failure. `labels.json` now marks both `_undetermined`; `recompute_metrics.py` excludes
each from the main table and reports them separately.

**`dependencies`: this session's own run-file notes were factually wrong.** They claimed "no external
dependency named" — false; the Constraints section names both the Kubernetes cluster and the internal
SSO. `note_correction` fields were added to all three `assessor-dependencies-run*.json` files rather
than rewriting the original notes. The document is reliably blocked (3/3, via `ambiguity`), so the
`dependencies` check specifically not firing is an attribution result, not a demonstrated gap in the
assessor's ability to notice a missing dependency treatment.

**`contradictions` false positives all trace to the same known cause**, not three independent findings:
2 of 3 come from `defect-blocking_unknowns.md` and 1 from `defect-constraints.md`, all the same
301/`no-store` tension described above. Reported both ways below, not chosen between.

**Agreement rate: 69% (9/13), unchanged from the original section above.** The prior correction's "62%
(8/13)" was an arithmetic error, not a re-measurement — `recompute_metrics.py` (below) shows
`defect-constraints.md` was already one of the 4 disagreeing documents before this adjudication pass
touched anything, not a fifth added by it.

**What does hold up, unimpeached, is the document-level blocking table** — whether *any* check (labeled
or not) fails, which is what the loop's stall/regression logic actually acts on, independent of which
specific check id fires. On that measure: `defect-scope.md` is the only document never blocked in any
observed run (0/3). Every other document — including `compatibility` after the fix, `dependencies` (via
`ambiguity`, not `dependencies`), and `constraints`/`security_data_implications` (1/3 each) — is blocked
at least once. `scope` being both the sole 0/3-blocked document and one of the two `_undetermined`
labels is itself informative, not resolved.

**The PLAN.md §3.c "prompt-level remedy versus documented limitation" owner question is withdrawn.**
There is no demonstrated blind spot to choose a remedy for.

### `recompute_metrics.py` output (verbatim, current corpus + run files)

```
Main table (excludes each _undetermined document's OWN labeled check - see below):
| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| problem_statement | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| scope | 0 | 0 | 0 | 0 | n/a | undefined |
| out_of_scope | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| acceptance_criteria | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 12 | 12 | 0 | 0 | 1.00 | 1.00 |
| contradictions | 3 | 3 | 0 | 3 | 1.00 | 0.50 |
| constraints | 0 | 0 | 0 | 0 | n/a | undefined |
| nfrs | 6 | 6 | 0 | 0 | 1.00 | 1.00 |
| security_data_implications | 3 | 1 | 2 | 1 | 0.33 | 0.50 |
| compatibility | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| dependencies | 3 | 0 | 3 | 0 | 0.00 | undefined |
| blocking_unknowns | 3 | 3 | 0 | 0 | 1.00 | 1.00 |

contradictions, excluding the known shared-template 301/no-store tension FPs:
  raw: FP=3, precision=0.50
  excluding template tension: FP=0, precision=1.00

Undetermined documents (own labeled check reported separately, not scored):
  defect-constraints.md / constraints: caught 0/3 runs
  defect-scope.md / scope: caught 0/3 runs

False positives by check (document#run):
  contradictions: ['defect-blocking_unknowns.md#run2', 'defect-blocking_unknowns.md#run3', 'defect-constraints.md#run3']
  security_data_implications: ['clean-baseline.md#run1']

Agreement rate (byte-identical 12-key verdict vector across all runs of a document):
  clean-baseline.md: DISAGREE (3 runs)
  defect-acceptance_criteria.md: AGREE (3 runs)
  defect-ambiguity.md: AGREE (3 runs)
  defect-blocking_unknowns.md: DISAGREE (3 runs)
  defect-compatibility.md: AGREE (3 runs)
  defect-constraints.md: DISAGREE (3 runs)
  defect-contradictions.md: AGREE (3 runs)
  defect-dependencies.md: AGREE (3 runs)
  defect-nfrs.md: AGREE (3 runs)
  defect-out_of_scope.md: AGREE (3 runs)
  defect-problem_statement.md: AGREE (3 runs)
  defect-scope.md: AGREE (3 runs)
  defect-security_data_implications.md: DISAGREE (3 runs)
Agreement: 9/13 (69%)

Document-level blocking (any check FAIL, labeled or not - what the loop actually acts on):
  clean-baseline.md: blocked in 1/3 runs
  defect-acceptance_criteria.md: blocked in 3/3 runs
  defect-ambiguity.md: blocked in 3/3 runs
  defect-blocking_unknowns.md: blocked in 3/3 runs
  defect-compatibility.md: blocked in 3/3 runs
  defect-constraints.md: blocked in 1/3 runs
  defect-contradictions.md: blocked in 3/3 runs
  defect-dependencies.md: blocked in 3/3 runs
  defect-nfrs.md: blocked in 3/3 runs
  defect-out_of_scope.md: blocked in 3/3 runs
  defect-problem_statement.md: blocked in 3/3 runs
  defect-scope.md: blocked in 0/3 runs
  defect-security_data_implications.md: blocked in 1/3 runs
```

Script: `runs/recompute_metrics.py`. Re-run it directly against `runs/assessor-*.json` (excluding
`*-superseded*.json`) and `labels.json` to reproduce this output; Stage 2's Codex review should do so
rather than trust the numbers above.

### Addendum — 2026-09-28: four verification fixes to the correction above

A third advisor review of the correction verified two of its claims against source and found the
correction itself under-applied its own new standard to a third check. Nothing above is rewritten.

1. **`security_data_implications` was wrongly left off `_undetermined`.** `defect-security_data_implications.md`'s
   Constraints section still reads "Must authenticate every management-API request ... against the
   existing internal SSO" — check 9 names authentication explicitly as part of what it looks for, so a
   PASS there is exactly as defensible as the PASS the correction above already accepted for
   `constraints`. No controlled experiment was run for it either. Added to `_undetermined` in
   `labels.json`; `recompute_metrics.py` rerun (output below) now excludes it from the main table.
2. **The `KNOWN_TEMPLATE_TENSION_FPS` exclusion for `contradictions` was verified against the actual
   finding text**, not re-asserted: `assessor-blocking_unknowns-run2.json` and `-run3.json` both cite
   the 301-permanent-caching-vs-`Cache-Control:no-store` tension by name (not the document's own TBD/
   service-to-service ambiguity, which was a live alternative explanation worth checking). The exclusion
   stands as originally applied.
3. **The prior section's "1 of the 51 total dispatches" figure was wrong — it is 3**, not 1: two from
   `defect-blocking_unknowns.md` (runs 2 and 3) plus one from `defect-constraints.md` (run 3), all the
   same cause. Corrected here rather than in the original text.
4. **`labels.json` moved into the repo at `ef41b9c`**, so PLAN.md §3.c's "kept outside the working tree"
   claim is now stale; corrected there directly (PLAN.md is not append-only). Any future measurement
   pass against this corpus relies on the dispatch prompt's "do not use any tools" instruction alone for
   label-leakage protection, not on the file's location.
5. **A fixture-design rule was added to `labels.json`'s `_notes`**: a section-absence fixture must
   establish the check's relevance outside the deleted section, or the assessor's correct refusal to
   invent an unraised concern reads as a false miss. Applies to any further section-absence fixture,
   including the still-missing duplicate-id pair for the lint's sixth rule.

```
Main table (excludes each _undetermined document's OWN labeled check - see below):
| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| problem_statement | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| scope | 0 | 0 | 0 | 0 | n/a | undefined |
| out_of_scope | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| acceptance_criteria | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 12 | 12 | 0 | 0 | 1.00 | 1.00 |
| contradictions | 3 | 3 | 0 | 3 | 1.00 | 0.50 |
| constraints | 0 | 0 | 0 | 0 | n/a | undefined |
| nfrs | 6 | 6 | 0 | 0 | 1.00 | 1.00 |
| security_data_implications | 0 | 0 | 0 | 1 | n/a | 0.00 |
| compatibility | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| dependencies | 3 | 0 | 3 | 0 | 0.00 | undefined |
| blocking_unknowns | 3 | 3 | 0 | 0 | 1.00 | 1.00 |

contradictions, excluding the known shared-template 301/no-store tension FPs:
  raw: FP=3, precision=0.50
  excluding template tension: FP=0, precision=1.00

Undetermined documents (own labeled check reported separately, not scored):
  defect-constraints.md / constraints: caught 0/3 runs
  defect-scope.md / scope: caught 0/3 runs
  defect-security_data_implications.md / security_data_implications: caught 1/3 runs

False positives by check (document#run):
  contradictions: ['defect-blocking_unknowns.md#run2', 'defect-blocking_unknowns.md#run3', 'defect-constraints.md#run3']
  security_data_implications: ['clean-baseline.md#run1']

Agreement: 9/13 (69%) - unchanged.

Document-level blocking, unchanged except compatibility (now 3/3, post-fix):
  defect-scope.md: blocked in 0/3 runs (only document never blocked)
  defect-constraints.md / defect-security_data_implications.md: blocked in 1/3 runs each
  every other document: blocked in 3/3 runs
```

With `security_data_implications` moved to `_undetermined`, the main table's only check still showing a
non-1.00, non-n/a recall is `dependencies` (0.00) — already explained above as an attribution result on
a document reliably blocked via `ambiguity`, not a demonstrated gap. `contradictions` precision depends
entirely on whether the known template tension is counted. Every other scored check is 1.00/1.00. The
corpus work is closed pending Stage 2 review; no further probes or reclassification are planned.

## Addendum — 2026-09-28: missing brief-mandated fixture, and a test-harness bug in lint scoring

A further advisor review of the frozen-PLAN.md readiness found five items, two of them blocking. The
"no further probes or reclassification" line immediately above still holds for the *existing* findings
— nothing below reopens or reclassifies any of them. This section adds one missing fixture the brief
requires and fixes a bug in how the lint prototype was scored, neither of which touches the assessor
findings already closed above.

### The missing `todo-api.md` fixture (brief §4.1A.4)

Brief section 4.1A.4 requires the corpus to hold "at least one seeded-defect document per check id
**plus the clean `todo-api.md`**" — the original corpus build only had `clean-baseline.md`, an
invented document, never the brief's own named fixture. Copied verbatim from `requirements/todo-api.md`
(the repository's real ground-truth fixture, used throughout the docs and tutorials — not the much
shorter placeholder `tests/conftest.py` generates at runtime for unrelated tests), blob
`5df4fe9461342564cd9ada0f8f8b7ac656a37a4c`. Labeled clean (`[]`) in `labels.json`, matching its intended
role.

**3 fresh dispatches, no filename in the prompt: unanimous, unexpected `dependencies: FAIL`.** All three
cite the same thing — "Persistence to a relational store" (Scope) and the identical NFR line name no
specific database product, version, ORM or driver, so the dependency is real but unidentifiable. This is
a genuine finding about the brief's own reference document, not a corpus-construction artifact of this
session's editing — the file was copied verbatim and never touched, per this session's own rule (and the
brief's own acceptance scenario 1, which requires this exact document to stay untouched and pass without
entering the loop).

**This is now the one owner question this corpus measurement raises for Stage 2**, distinct from
anything already decided: acceptance scenario 1 ("Requirements pass initially; the loop is not entered")
assumes `todo-api.md` passes cleanly, and on this evidence it would not — the refinement loop would be
entered on the repository's own reference document on first contact. Two honest readings, neither
decided here: (a) `todo-api.md` itself has a real, pre-existing gap the loop would correctly catch, which
is arguably the loop working as designed even on document zero; or (b) `dependencies`'s check definition
("services, libraries, third parties... with enough detail to know what they are") is being read more
strictly by the assessor than the document's own authors (this session, elsewhere, and the original
brief author) intended when they judged this document "clean" — the same ambiguity already seen for
`constraints`/`scope`/`security_data_implications`. Recorded, not resolved; raised for Stage 2, not
silently patched by editing the reference document out from under acceptance scenario 1.

### Test-harness bug: lint's duplicate-id rule scored against the wrong comparison set

`recompute_metrics.py`'s lint-scoring addition initially passed every OTHER corpus document as
`other_texts` to `lint()`, so the duplicate-id rule (`check_duplicate_ids`, `contradictions`) compared
all 13 unrelated corpus documents against each other. Since every document deliberately reuses
`AC-1`..`AC-4` from the shared "Link Shortener Service" template (by design — they are independent
example documents, not a bound set), this produced 11 false positives, one per document pair sharing the
template. **This is a test-harness bug, not a lint finding** — the rule's real, intended comparison set
is documents bound to the *same* WorkItem, never an unrelated corpus. Fixed: `other_texts` is no longer
passed; each document is linted alone. The corpus still has no fixture that tests the duplicate-id rule's
actual cross-document mode — already known and unchanged by this fix, see the script's own printed note
and `labels.json`'s `_fixture_design_rule`.

### `recompute_metrics.py` output (verbatim, current corpus + run files, includes `todo-api.md` and lint scoring)

```
Main table (excludes each _undetermined document's OWN labeled check - see below):
| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| problem_statement | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| scope | 0 | 0 | 0 | 0 | n/a | undefined |
| out_of_scope | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| acceptance_criteria | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 12 | 12 | 0 | 0 | 1.00 | 1.00 |
| contradictions | 3 | 3 | 0 | 3 | 1.00 | 0.50 |
| constraints | 0 | 0 | 0 | 0 | n/a | undefined |
| nfrs | 6 | 6 | 0 | 0 | 1.00 | 1.00 |
| security_data_implications | 0 | 0 | 0 | 1 | n/a | 0.00 |
| compatibility | 3 | 3 | 0 | 0 | 1.00 | 1.00 |
| dependencies | 3 | 0 | 3 | 3 | 0.00 | 0.00 |
| blocking_unknowns | 3 | 3 | 0 | 0 | 1.00 | 1.00 |

contradictions, excluding the known shared-template 301/no-store tension FPs:
  raw: FP=3, precision=0.50
  excluding template tension: FP=0, precision=1.00

Undetermined documents (own labeled check reported separately, not scored):
  defect-constraints.md / constraints: caught 0/3 runs
  defect-scope.md / scope: caught 0/3 runs
  defect-security_data_implications.md / security_data_implications: caught 1/3 runs

False positives by check (document#run):
  contradictions: ['defect-blocking_unknowns.md#run2', 'defect-blocking_unknowns.md#run3', 'defect-constraints.md#run3']
  security_data_implications: ['clean-baseline.md#run1']
  dependencies: ['todo-api.md#run1', 'todo-api.md#run2', 'todo-api.md#run3']

Agreement: 10/14 (71%) - includes todo-api.md (agrees, unanimous FAIL), up from 9/13 (69%) by one
document with no change to any prior document's agreement status.

Document-level blocking: todo-api.md is blocked 3/3 (via dependencies) - see the owner-question
writeup above. Every other document's count is unchanged from the prior addendum.

Lint scoring (14 corpus documents, one run each - deterministic, not sampled):
| check | positive instances | TP | FN | FP | Recall | Precision |
|---|---|---|---|---|---|---|
| blocking_unknowns | 1 | 1 | 0 | 0 | 1.00 | 1.00 |
| ambiguity | 4 | 3 | 1 | 0 | 0.75 | 1.00 |
| acceptance_criteria | 1 | 1 | 0 | 0 | 1.00 | 1.00 |
| out_of_scope | 1 | 1 | 0 | 0 | 1.00 | 1.00 |
| nfrs | 2 | 1 | 1 | 0 | 0.50 | 1.00 |
| contradictions | 1 | 0 | 1 | 0 | 0.00 | undefined |
```

Lint's `ambiguity` miss (0.75, 3/4) is `defect-acceptance_criteria.md`: its vague replacement text
("works well", "satisfied") isn't on the lint's fixed vague-terms vocabulary, while the LLM assessor
caught it (all 3 runs, see the corpus-measurement section above) — a real, narrower vocabulary gap in
the deterministic floor relative to the semantic assessor, not a bug; this is exactly the kind of gap
having both layers is meant to surface. `nfrs`'s 0.50 and `contradictions`'s 0.00/undefined are as
explained in the corpus-measurement section and the script's own printed note respectively — unchanged
by this addendum, restated here only because the numbers moved (positive-instance counts changed with
`todo-api.md` added) even though the underlying explanation didn't.

§3.c's "committed at `9ec6d4a`" citation is stale — the corpus content has changed at `eefc661`,
`ef41b9c` and now this addendum's commit; §3.c should cite the corpus by its current state, not a
specific historical commit, since it has legitimately changed more than once since first measured.

**Filenames encode labels, a deviation from the original plan** (which specified neutral `doc-01.md`
style names). Every dispatch prompt in this corpus measurement omitted the filename and instructed no
tool use; `tool_uses: 0` is recorded on the three newest run files (`todo-api.md`) as provenance that no
tool was actually invoked to discover it, matching PLAN.md §3.c's own note that filename neutrality was
never the real guard. Earlier run files do not carry `tool_uses` (not captured at the time) — treat its
absence there as "not recorded," not as evidence either way.

## Phase A — steps 3, 4, 5 (2026-10-03)

- **Step 3 (`69fa700`)**: `refinement.json` record (strict validator, `refinement_record_invalid` exit 3, one
  validated writer, cap ceiling `REFINEMENT_ITERATION_CAP_MAX = 3`), lint-evidence validator (`floorEnforced`
  must be false). `scan-acknowledgements.json` and `refinement.json` added to the runtime-member leak check
  (the acknowledgement store had been missing from it). `write_atomic` pin 32 -> 33.
- **Step 4**: `requirements_lint` + `REQUIREMENTS_LINT_RULES` (applicability declared per rule; normative text
  only for line rules; code/quote/comment excluded; section and duplicate-id rules judge the bound set; ids
  count only as definitions). Advisory: nothing on the assessment path reads it (AST test over four functions).
  One finding from building it: the prototype's `out_of_scope` rule would have been a false positive on
  `clean-baseline.md` and `todo-api.md` (an "Out of scope:" label inside a Scope section); the shipped rule
  accepts a heading or a label. Corpus result: zero floor-eligible findings on the two clean documents; the
  rules find the blocking_unknowns, out_of_scope and acceptance_criteria defects and the ambiguity defect.
  `vague_term` fires on `defect-dependencies.md` and `defect-nfrs.md` (not their target) - which is why it and
  `quantity_without_measure` are `floorEligible: false`.
- **Step 5**: corpus additions are runtime-built fixtures in `test_units_refinement_lint.py` (duplicate-id pair
  across documents, per-kind positives, neighbouring-kind negatives), not checked-in files.
  **Re-measurement of the amended `todo-api.md`** against the engine's final `QUALITY_CHECK_DEFINITIONS`
  (prompt identical modulo whitespace to the measured v2 prompt, verified in code), same method as before
  (fresh agent, single Read, single Write, 3 runs): **3 of 3 pass all twelve checks**. Outputs in
  `stage2/final-measurement/`. Exploratory (3 runs, one model), as the earlier measurement was.

## Phase B — assessment integrity (2026-10-03)

- **Flip refusal (A1/A2).** `quality_verdict_flip` (exit 1) fires before any write to `governance.json`, which
  stays byte-identical; the attempt is kept as `evidence/governance-flip-attempt-*.json` (kind
  `governance-flip-attempt`, status `REFUSED`, the flipped checks, the content digest, the proposed quality).
  Both records carry `requirements.contentDigest`. History is read by `kind` from `evidence/governance-*.json`
  plus the current record as the last entry; legacy entries are "unknown" unless their raw digest equals
  today's. Corruption refuses `governance_history_invalid` (exit 3).
  Two deliberate refinements of the plan text, for Codex to judge: (1) a **zero-byte** `governance-*.json` is
  skipped, because `reserve_evidence` documents an empty file as the crash placeholder and refusing it would
  brick a WorkItem after any crashed assessment; any other malformed file, including an object with no
  `kind`, refuses. (2) `NOT_APPLICABLE` after a `FAIL` at the same content counts as a flip, not only `PASS`.
- **Dispute exemption (A3), reading side only.** An earlier FAIL is exempt only for a (check, content digest)
  pair listed in a validated `refinement.json` dispute outcome. The `dispute` command that writes one is Phase C.
- **Existing test changed, on purpose:** `test_re_assessing_a_fixed_requirement_unblocks_the_same_advance`
  re-assessed an unchanged document; it now makes the fix its name says. It was the only one of 245
  governance tests, and of the other suites run, that relied on the old behaviour.
- **The lint floor reason is not defined.** The plan asked for `quality_verdict_below_floor` to be "defined,
  never raised". An unreachable constant is dead code with a pin, so it is omitted; the advisory-only property
  is pinned by the AST test over the four assessment functions instead. Open to Codex's disposition.
- **Assessor agent `sdle-requirements-review`** (read-only grant and fence like the other four; it lists no
  check id or definition, which the parent copies from `governance policy`'s `check_definitions`). Tests prove
  the agent glob picks it up and that it restates nothing. Pins moved: agent sets (capabilities, gate-policy,
  install-contract), hook registration counts (8 -> 9, 4 -> 5), `new_prompt_files` 6 -> 7, `write_atomic` 33 -> 34.
  "Four product subagents" updated to five in CLAUDE.md, SKILL.md, README, the Reference Guide and
  GETTING-STARTED; the tutorial and ADR-007 describe the four review subagents historically and are unchanged.

## Phase C go-ahead (2026-10-03) — Codex consulted on whether the owner is needed

Question: may Phase C proceed under the recorded default (shared document refused, no acknowledgement path, no
transaction index) without the owner? **Codex: VERDICT: PROCEED** — the default weakens no invariant, is
reversible without touching `state.json` (the refinement record is independently versioned and a later
`transactions[]` can be absent-means-empty in version 1), and satisfies scenario 17. Conditions recorded:
**scenarios 18 and 29 stay explicitly deferred, not reported as passing**; tests must show `propose` and `apply`
refuse a shared source before any write, with no acknowledgement path and no bind/check race. Codex's reminder,
adopted: this is not approval to ship the reduced behaviour — the owner must still choose Design R or approve the
default before the feature is declared complete. A person whose document is shared sees
`refinement_shared_source` naming the other WorkItems and must edit by hand and re-assess each.

- **Correction found by CI (2026-10-03):** the history reader first refused any `governance-*.json` object that
  declared no `kind`. `test_units_execution_identity` plants a `{"sentinel": true}` file at an evidence name to force
  an id collision, and every assessment after it failed `governance_history_invalid` - on both OSes, three tests.
  The plan's own rule is inclusion by `kind`, so an object with no kind is "not history", not corruption. The
  reader now skips it; it still refuses unreadable JSON, a non-object, and a `kind == "governance"` object whose
  record is malformed. The earlier ledger note that "an object with no `kind` refuses" is superseded by this.
  Lesson recorded: the targeted batches I chose missed this module; Phase C batches add `test_units_execution_identity`
  and every module that writes under `evidence/`.

## Phases C, D, E (2026-10-03)

- **C** (`1a0e1e1` and following): `refinement propose|decide|apply|dispute|cancel|show`; one exclusive-lock
  helper shared with the architecture catalog lock; the refinement mutex taken by every mutating command, by
  `requirements bind` and by `init`; shared-source rule per the Codex-agreed definition; iteration-cap policy key;
  baseline citations for `compatibility`/`dependencies` findings (A10); answered questions not re-asked.
  Deviation from the plan text: **`propose` after a stall or the cap writes `ESCALATED` and the cap case then
  refuses** (`refinement_cap_exhausted`); a stall returns ok with `status: ESCALATED`. The record schema gained
  edit `id`/`text`/`appliedSha256` and iteration `assessmentRef` because the plan's §5.a had nowhere to keep the
  edit payload or to say which assessment an iteration answered. Dispute evidence is the refused re-assessment
  (`governance-flip-attempt-*`), the only independent PASS at the same content the engine can produce.
- **Mutation proof:** shared-source guard on apply, post-init guard, human-decision requirement, `init` guard,
  dispute replay (initially survived — two tests added), neutrality classification, citation stale-pin check: each
  removal fails a test.
- **D**: `modules/requirements-refinement.md`; routing in `SKILL.md` Step 6a and `/sdle-start` step 4;
  `CAPABILITY_MAP` row on `requirements_check` (the module is routed explicitly because no phase exists to carry it).
- **E**: GETTING-STARTED §11d, ADR-015, dry runs 21–22 (pre-init marker: the contract test now allows a transcript
  with no status header only when it says so), troubleshooting rows for every new reason, matrix rows, README/Reference Guide.
- **Scenario status:** 1–17, 19–28 have tests (21 is convention only: the assessor prompt is built by the parent,
  and nothing machine-checks that no prior verdict is in it). **18 and 29 are DEFERRED** with Design R, per Codex;
  they are not reported as passing. 30 was closed in Stage 0.
- **Open for the owner:** the Design R / shared-document decision before the feature is called complete.
