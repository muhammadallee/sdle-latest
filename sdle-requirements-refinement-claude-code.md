# SDLE Requirements Refinement Loop — Claude Code Execution Brief

## Mission

Extend SDLE's existing requirements-quality check (the twelve checks evaluated by `governance assess`)
with a finding-driven, iterative requirements refinement loop that runs **before planning**, so that
the requirements entering the lifecycle are measurably better and the implementation built from them is
better as a result.

Preserve the current evaluator, check ids, policy-derived severity, the tighten-only policy override,
persist-before-refuse behaviour, requirements binding and staleness, WorkItem isolation, the audit chain
and the evidence conventions. **Do not** create a competing quality gate, a scoring system, a lifecycle
phase, a `state.json` schema change, a database, a second workflow engine, or any dependency outside the
Python standard library.

The loop is worthless if it converges because the assessor starts saying PASS rather than because the
requirements got better. Design every part against that failure first.

Execute in this mandatory order:

0. **Claude:** prior-stabilization verification (§4.0). Enhancement work does not start while a prior
   stabilization defect is open without evidence.
1. **Claude:** repository discovery, baseline verification, evaluation corpus, comprehensive plan.
2. **Codex ↔ Claude ↔ Codex ↔ Claude:** two-level adversarial plan review and reconciliation.
3. **Claude:** phased implementation with tests and durable progress records.
4. **Codex ↔ Claude ↔ Codex ↔ Claude:** two-level adversarial implementation review and reconciliation.
5. **Claude:** independent final verification, regressions, dry-run execution, evidence-based report.

Defects found at any point during this work are fixed under the parallel defect protocol (§9).

Do not claim Codex reviewed anything unless Codex actually ran. If Codex is unavailable, preserve the
review package and stop at the review checkpoint. Do not substitute Claude self-review.

This enhancement runs **before** the separate *Controlled Gate Rework Loop* plan. Do not pre-implement
or conflate it.

---

## 1. Verified grounding

These facts were read from `muhammadallee/sdle-latest` at commit `48a853a`. **Re-verify each one against
the current checkout in Stage 1** and correct this brief in the plan wherever the checkout differs.

| # | Fact | Where | Consequence |
|---|---|---|---|
| F1 | Twelve check ids: `problem_statement, scope, out_of_scope, acceptance_criteria, ambiguity, contradictions, constraints, nfrs, security_data_implications, compatibility, dependencies, blocking_unknowns`. Ids are not overridable. | `GOVERNANCE_POLICY_BUILTIN.quality_checks`, `GOVERNANCE_POLICY_OVERRIDABLE` in `scripts/sdle.py` | No new check ids, no renaming. |
| F2 | Each result is `PASS`/`FAIL`/`NOT_APPLICABLE`, **authored by the model** in the governance proposal. The engine validates shape, requires a finding on FAIL, and reads severity from policy. There are **no weights, scores or thresholds for quality checks**; weights, thresholds and hard floors belong to risk signals. | `evaluate_quality()` | The quality verdict is LLM judgment inside deterministic validation. Assessment integrity (§3.1–§3.3) is the core of this work. |
| F3 | All twelve are blocking; only `nfrs` may be `NOT_APPLICABLE`. An override that drops a blocking check or widens optional checks is refused. | `blocking_checks`, `optional_checks`, `_refuse_weakening()` | The only quality exception is `nfrs: NOT_APPLICABLE`. Gate omission is a gate mechanism, not a quality exception. Do not invent another. |
| F4 | A BLOCKED assessment is persisted (`governance.json` and `evidence/governance-*.json`) **before** `requirements_quality_blocked` is raised. | `cmd_governance_assess` | Iteration history can be derived from existing evidence; reuse it, do not duplicate it. |
| F5 | Governance runs after `workitem create` and **before `init`**; `state.json` does not exist yet. | `SKILL.md`, "Governance comes before planning" | Loop state cannot live in `state.json`, and `state.rate_limits` is unavailable. |
| F6 | A `state.json` of another schema is refused, never migrated. | ADR-010 | No new state field. New state is a new engine-written WorkItem record. |
| F7 | Bound sources may be shared by several WorkItems; changing a bound document stales every assessment made from it. | ADR-012, `governance_stale` | Editing a shared document is a cross-WorkItem change (§3.5). |
| F8 | That a human rather than the orchestrator typed `approve` is **convention only**. | `CLAUDE.md`, ADR-007 §3 | SDLE cannot prove human authorship of a decision. The report must say so; never claim otherwise. |
| F9 | Spec Kit `clarify` already runs after `spec_draft`, on `spec.md`, before Gate 2. | `modules/phase-execution.md` | This loop is pre-spec, on bound requirement documents. It does not duplicate or replace post-spec clarify. |
| F10 | `scan --path` is the existing untrusted-content scan. | `SKILL.md` | Every revised document is re-scanned before re-assessment. |
| F11 | Documentation is under test: `test_units_documented_commands.py` (every documented command parses; global options precede the subcommand; only Getting Started teaches the install command), `test_units_doc_links.py` (links, anchors, no orphan pages), `test_dry_run_contracts.py` (exactly sixteen transcripts; every refusal shown is engine-raised). | `tests/` | Constrains §8; a new dry-run transcript is a test change and is deferred (§10). |
| F12 | CI matrix: `ubuntu-latest` and `windows-latest` × Python 3.11 and 3.13; runs `lint-skill`, then pytest. | `.github/workflows/ci.yml` | "CI passed" means all four cells passed. |
| F13 | The engine is a single stdlib-only script, not a package. | `scripts/sdle.py` | Import checks use the script path: `python -c "import sys; sys.path.insert(0, 'scripts'); import sdle"`. |
| F14 | Prior review work used `codex-cli` in a read-only sandbox, ephemeral, on detached worktrees, with a structured output schema. | `.sdle/implementation-state/repository-cleanup/LEDGER.md` | Reuse that harness (§5). |

---

## 2. Decided constraints — do not reopen

These were decided by the owner. Codex may challenge them in review; a challenge that Claude cannot
refute with evidence is escalated to the owner, never resolved by either agent.

| # | Decision |
|---|---|
| C1 | **Shared documents.** If a bound document selected for refinement is also bound by another WorkItem, the engine refuses (`refinement_shared_source`) and lists the other WorkItems. The edit proceeds only with an explicit acknowledgement naming those WorkItems, recorded in the audit of **every** affected WorkItem. The refinement never edits a copy; `requirements/` stays the single source of truth. The document write and every audit entry form one **recoverable transaction** (§3.5): several atomic file writes are never assumed to be one atomic operation. |
| C2 | **Auto-apply.** Only demonstrably presentation-neutral edits apply without a human decision, as defined by the engine's normalisation in §3.5. Markdown structure is **not** normalised away: any change to headings, list nesting or markers, tables, emphasis, links, code spans or block boundaries needs a per-item human decision, as does every other edit. When in doubt, the edit is not presentation-neutral. |
| C3 | **Iteration cap.** 3, held as one engine constant. A repository policy may only lower it. Reaching the cap ends the loop `ESCALATED`; the quality gate is never bypassed. |
| C4 | **Timing.** Refinement runs pre-`init` only. After `init`, a changed bound document behaves exactly as today (`governance_stale`, re-assess). |
| C5 | **ADR.** ADR-013 records the refinement record, its refusals and the assessment-integrity rules. It is in scope. |
| C6 | **Lint authority.** The deterministic requirements lint is a floor, not a gate: a lint failure makes an assessor `PASS` for the mapped check impossible, but the lint adds no blocking rule and no check id of its own. Because it floors verdicts, every rule must be sensitive to the kind of requirement it inspects and must never turn a writing-style preference into a requirement (§3.3). |
| C7 | **Test binding.** The shared `conftest` auto-bind fixture stays as it is. Every refinement test binds requirements explicitly, and one test must fail if the binding step is skipped. |
| C8 | **Prior stabilization.** The repository's earlier stabilization and cleanup commitments are verified complete before enhancement work begins (§4.0). Any item found genuinely open is fixed under §9 **regardless of impact surface**; the scope limit in §9 applies only to newly discovered pre-existing defects. |
| C9 | **Documentation correctness.** User documentation is expanded only in Getting Started, but no document may ship with an instruction about the modified workflow that is now **false**. Such statements get the minimal correction in this change (§8); new tutorials, rewrites and new dry-run transcripts stay deferred (§10). |

---

## 3. Target design

This is the hypothesis Stage 1 confirms or refutes and Stage 2 attacks.

### 3.1 Roles

| Role | Runs where | Sees | Can |
|---|---|---|---|
| **Assessor** | New read-only product subagent `sdle-requirements-review`, fresh context per iteration, same `PRODUCT_AGENT_TOOLS` grant and `product-agent-fence` as the existing four | Bound documents at the current revision, the policy's check ids, the baseline record if one exists. **Never** prior verdicts, findings, proposals or the refiner's reasoning. | Return the twelve answers as structured JSON. Nothing else. |
| **Refiner** | Parent orchestrator | Current findings, lint evidence, bound documents | Propose targeted edits linked to finding ids, and questions for the human. Never records a verdict. |
| **Engine** | `scripts/sdle.py` | Everything on disk | Validate, lint, apply authorised edits, compute digests and progress, persist, refuse. |
| **Human** | Parent conversation | Every diff and question shown in full in conversation (invariant 4) | Accept, reject, answer. |

No decision is ever held by a subagent (invariant 8). The parent copies the assessor's twelve answers
**verbatim** into the governance proposal, and the assessment evidence names the producing agent,
mirroring the `--actor-type agent --actor-name` convention of `artifact review`. Stage 1 must establish
whether the engine can verify that the proposal's answers equal the subagent's returned payload. If it
cannot, the final report states that faithful copying is convention, alongside F8.

### 3.2 Deterministic assessment-integrity rules

- **No verdict flip without substantive change.** If a check was `FAIL` at **content digest** *C* and a
  later assessment at the same *C* reports `PASS`, refuse `quality_verdict_flip` (exit 1) and record the
  attempt. *C* is computed over each bound document's presentation-neutral normal form (§3.5), not its
  raw bytes; otherwise a whitespace edit, which may auto-apply, would change the digest and unlock the
  flip. A FAIL becomes a PASS through ordinary refinement only via a substantive change.
- **Assessment dispute.** An initial assessment can itself be wrong. Correcting it is a separate, explicit
  path, never part of ordinary refinement: `refinement dispute --check <id>` requires (a) independent
  evidence, being a fresh assessor run that returns `PASS` for the check at the same *C* together with a
  written rationale, and (b) a human decision in conversation that authorises overturning the original
  result. The original result is never overwritten; the dispute, its evidence and the decision are
  appended as their own evidence and audit entries. An overturned FAIL is recorded as
  `overturned_by_dispute`, is reported separately in the report and the corpus metrics, and **never**
  counts as a requirements improvement or as loop progress (§3.4). A dispute without both parts is refused.
- **Lint floor (C6).** Where the lint reports a failure mapped to a check, an assessor `PASS` for that
  check is refused `quality_verdict_below_floor`. The assessor may be stricter than the lint, never looser.
- **Proposals carry no verdicts.** The engine refuses any refinement proposal containing quality results.

### 3.3 Deterministic requirements lint

Computed by the engine per bound document, stored as evidence, and mapped to existing check ids. Only
cheap, high-precision rules; each needs a positive and a negative fixture:

- Unresolved markers (`TBD`, `TODO`, `???`, placeholders, empty sections) → `blocking_unknowns`.
- Vague terms in normative sentences (`fast`, `user-friendly`, `robust`, `as appropriate`, `etc.`,
  `and/or`, `some`, `several`, …; the list is held once, in one place) → `ambiguity`.
- Missing sections the checks presuppose (acceptance, out of scope) → `acceptance_criteria`, `out_of_scope`.
- Acceptance criteria that cannot be told apart or checked: no stable id, or no observable outcome (a
  stated result, state, response, value or refusal). **No format is mandated**; Given/When/Then, EARS
  and plain precise sentences are all valid → `acceptance_criteria`.
- Quantitative quality attributes stated without a measure: the rule fires only on statements the lint
  classifies as performance, latency, throughput, capacity, availability or scalability, and only when
  they carry no number and unit. Binary or categorical requirements (security controls, compliance
  obligations, compatibility targets, supported platforms) are **exempt**, never flagged for lacking a
  number → `nfrs` (only when `nfrs` is not `NOT_APPLICABLE`).
- Duplicate requirement or criterion ids across bound documents → `contradictions`.

Rule requirements:

- Each rule declares which requirement kinds it applies to, and has positive fixtures, negative fixtures,
  and at least one fixture of a valid requirement of a neighbouring kind that it must **not** flag
  (for example a categorical security requirement for the quantitative rule, and a plain-sentence
  criterion for the acceptance rule).
- Any rule that floors a verdict produces zero findings on `requirements/todo-api.md` and on every clean
  corpus fixture.
- A rule whose false-positive rate on the corpus is not zero does not ship as a floor; it may ship as
  advisory evidence only, recorded as such.
- A lint finding can be waived only by a human decision recorded in the refinement record, naming the
  rule, the location and the reason; never by the refiner or assessor, and never by a marker written
  into the requirement document.

### 3.4 Loop semantics

Let *Fₖ* be the set of failing blocking checks after iteration *k*, *Cₖ* the content digest (§3.2) and
*Pₖ* the proposal digest.

- **Pass:** *F₀* = ∅ → the loop is never entered; the existing flow continues with no extra gate. *Fₖ* = ∅
  after refinement → the loop ends `PASSED` and the existing flow continues.
- **Progress:** *Cₖ* ≠ *Cₖ₋₁* (content digest, §3.2) and (*Fₖ* ⊊ *Fₖ₋₁*, or at least one human answer
  was applied). A check leaving *Fₖ* by dispute is not progress.
- **Regression:** a check in *Fₖ* that was not in *Fₖ₋₁*. Never auto-continue; show the human which edit
  caused it.
- **Stall:** *Cₖ* = *Cₖ₋₁*, or *Pₖ* seen before, or no progress for two consecutive iterations → `ESCALATED`.
- **Exhaustion:** cap reached (C3) → `ESCALATED`. `init` stays refused while quality is blocked.
- **Human burden:** at most 5 questions per iteration, ordered by how many blocking checks each answer
  can resolve; multiple choice where possible; one batched decision per iteration with per-item
  accept/reject.

Outcomes are `PASSED | ESCALATED | CANCELLED | FAILED`, stored in the refinement record. They are record
states, not lifecycle statuses (F5).

### 3.5 Edit application

- Edits are structured operations (`replace` anchored on exact existing text, `insert_after` anchored,
  `append_section`) against a **bound source path** with its **base SHA-256**. The engine refuses if the
  current SHA differs, the path is not bound, the path resolves outside the project root, or the
  operation exceeds a size cap.
- The shared-source check (C1) runs before any write.
- The engine writes atomically with the existing `write_atomic`, then runs `scan` on the result.
- **Presentation-neutral normal form** (used by C2 and by the content digest in §3.2): line endings
  unified; trailing whitespace removed; runs of spaces inside a line's text collapsed, **excluding**
  leading indentation, table rows, code spans and fenced blocks; runs of two or more blank lines
  collapsed to one. Nothing else is normalised. An edit is presentation-neutral only if the normal forms
  before and after are byte-identical; the engine decides, the refiner's classification is ignored.
- **Shared-document transaction** (C1). One transaction covers the document write and an audit entry in
  every affected WorkItem:
  1. Acquire the session lock of every affected WorkItem in sorted id order; refuse if any is held.
  2. Write a durable **intent** (transaction id, document path, base SHA, target SHA, target content
     evidence path, affected WorkItems, acknowledgement) to the originating WorkItem's refinement record
     with `write_atomic`, before touching the document.
  3. Write the document (base-SHA precondition), then append one audit entry per affected WorkItem,
     each carrying the transaction id.
  4. Mark the intent `COMMITTED`.
  - **Recovery** runs before any other refinement command for the originating or an affected WorkItem,
    whenever an intent is not `COMMITTED`: document at target SHA → append only the missing audit
    entries (idempotent by transaction id), then commit; document at base SHA → re-apply from the stored
    target content, or roll the intent back as `ABORTED` on user cancel; document at any other SHA →
    refuse with an integrity failure (exit 3) naming the transaction, and change nothing.
  - An audit entry is never written twice for one transaction id, and an intent is never deleted.
  - Other WorkItems' assessments made stale by the change are reported by the existing `governance_stale`
    path; the transaction does not re-assess them.
- The pre-loop content and hash of every bound document are preserved once as evidence and never
  overwritten; each iteration's diff is evidence.
- The session lock is held from apply through re-assessment; a second invocation refuses.

### 3.6 Record and surface

- One new engine-written record, `workitems/<id>/.sdle/refinement.json`, plus per-iteration
  `evidence/refinement-*.json`. Single writer, covered by the write-fence hook and by `lint-skill`.
  `state.json` is untouched.
- No new controller. The orchestration protocol lives in a new capability module
  `modules/requirements-refinement.md`, mapped in `CAPABILITY_MAP`. The engine gains one command group,
  `refinement` (`propose`, `decide`, `apply`, `dispute`, `show`), the two refusals in §3.2, and the lint.
  `governance assess` changes only to enforce §3.2.
- Brownfield: when a sound baseline exists, findings and proposals for `compatibility` and `dependencies`
  must cite baseline or discovery record entries, read-only.
- Stage 1 must justify every addition against this minimum. Stage 2 must specifically attack whether
  `propose` and `decide` can collapse into one command, and whether any addition can be removed.

---

## 4. Stage 0 and Stage 1

### 4.0 Stage 0 — prior-stabilization verification

No single "defect stabilization plan" file was found at `48a853a`: `docs/verification/defect-stabilization-01.md`
was deleted by the cleanup work and the plan that drove the cleanup was never committed. The earlier
commitments live in `.sdle/implementation-state/*/LEDGER.md` and `FINDINGS.md`, whose status lines are
partly stale (for example, `repository-cleanup` reports `VERIFICATION_BLOCKED` with F-024 open while its
findings table records F-024 resolved; `workitem-isolation` headers say "open" for F-101–F-103 that later
sections record as fixed).

1. If the owner's checkout contains a stabilization plan file, it is the source. Otherwise the ledgers
   and findings files above are the source. Do not fabricate defects.
2. Enumerate every item with its id, recorded status, affected behaviour and acceptance evidence.
3. For each item recorded as fixed, verify it: the fix commit is an ancestor of the starting commit, its
   regression test exists and passes, and the four CI cells were green on a commit that contains it.
   Record the evidence. Correct stale statuses by **appending** a dated reconciliation note; never
   rewrite a ledger's history.
4. Items that are owner decisions (not defects) are listed and left for the owner.
5. Any item that is genuinely open, or whose evidence cannot be established, enters the §9 register as a
   prior-stabilization defect and is fixed under §9 before Stage 3 starts. If CI evidence cannot be
   reached, record `BLOCKED` and do not start Stage 3.
6. If every item verifies, record the prerequisite as satisfied, with its evidence, and continue.

### 4.1 Stage 1 — discovery, baseline, evaluation corpus, plan

### A. Investigation (no production code changes)

1. Record the repository root, branch, commit, `git status`, `CLAUDE.md` rules and any pre-existing
   changes. Never overwrite unrelated work.
2. Re-verify every row of §1.
3. Map the impact surface with source references: `cmd_governance_assess`, `evaluate_quality`, binding
   and staleness, evidence writers, audit append, the session lock, `write_atomic`, `scan`, the
   write-fence hook, `PRODUCT_AGENT_TOOLS`, `lint-skill` rules, `CAPABILITY_MAP`, `/sdle-start`, the four
   product agents, and every test that touches them. This map also defines what counts as "inside the
   impact surface" for §9.
4. **Evaluation corpus.** Build `tests/fixtures/requirements-quality/` with at least one seeded-defect
   document per check id plus the clean `todo-api.md`, each labelled with its expected failing checks.
   Measure the current assessor (no loop) and the lint's precision and recall on it. This is the baseline
   the loop must beat.
5. Reproduce the baseline: `python scripts/sdle.py lint-skill` and the full pytest suite. Record exact
   commands, results, skips, environment blockers and pre-existing failures. Pre-existing failures enter
   the defect register (§9).
6. **Parallel capability check.** Confirm the Task tool is available and that `git worktree add` /
   `git worktree remove` work in this checkout (create and remove a scratch worktree). Record the result;
   §9 depends on it.

### B. Plan artifact

Write `.sdle/implementation-state/requirements-refinement/PLAN.md` and an adjacent `LEDGER.md`. The
ledger is the single durable execution record: current stage, commands and results, reviewer findings,
defect register, files changed, next action. No second state file.

The plan contains: integration points and module boundaries; explicit JSON contracts (assessment, lint
evidence, finding, proposal, edit operation, decision, iteration record) with refusal reason codes; the
state-transition table (initial pass, remediation, question pause, accept, reject, regression, stall,
exhaustion, cancellation, interruption at each step, recovery, terminal failure); file-level change
estimates per phase; requirements-to-test traceability; risks; rollback (revert commits; there is no
data migration to undo).

Do not implement before Stage 2 is reconciled.

---

## 5. Two-level adversarial review protocol

Run in full twice: on the plan (Stage 2) and on the implementation (Stage 4).

**Harness.** `codex-cli`, read-only sandbox, ephemeral, detached worktree, structured output schema.
Record the CLI version and configured model in evidence. Remove review worktrees afterwards.

**Level 1 — Codex reviews independently.** Give Codex the actual repository and the complete package,
not a summary: for the plan, the baseline, impact map, corpus results, plan, risks and current source;
for the implementation, the frozen plan, the diff, test evidence and relevant code. Codex returns finding
ids, severity, file and lines where possible, evidence, consequence and correction, and separates defects
from optional improvements.

**Claude responds to every finding:** `ACCEPT`, `PARTIALLY ACCEPT`, `CHALLENGE` or `OUT OF SCOPE`, with
code, test, policy or requirement evidence. Neither blind acceptance nor dismissal on confidence.
Preserve the original finding and the full response.

**Level 2 — Codex reviews the counterarguments.** Send the findings, responses, changes and new evidence.
Codex dispositions every finding `UPHELD`, `REVISED`, `WITHDRAWN` or `RESOLVED`, addresses Claude's actual
argument, and independently re-inspects material claims and claimed corrections.

**Claude reconciles.** Fix accepted issues, rerun relevant tests, record final status and evidence per
finding. Substantial changes after Level 2 get targeted Codex verification of the changed material only.

**Escalation.** A material disagreement that survives reconciliation stops the affected work and goes to
the owner with: finding id and severity, both positions at both levels, both sides' evidence,
consequences and options, and the exact decision required. Agent confidence never picks the winner.
Independent work continues only if it cannot prejudice the decision. Review history is append-only.

A checkpoint is complete only when both Codex levels actually ran, every finding has a disposition,
mandatory corrections have evidence, and no blocking dispute remains without an owner decision.

**Stage 2 must specifically attack:** whether the loop can still converge by verdict drift; whether any
change weakens an existing refusal; whether the new command group is needed; pre-`init` placement; crash
points between apply and re-assessment, and in the shared-document transaction; whether the dispute path
can be used to launder a verdict flip; whether the normal form hides meaningful edits; lint false
positives by requirement kind; corpus adequacy; and conflicts with C1–C9.

**Stage 4 must specifically attack:** concurrency and duplicate execution; base-SHA enforcement; path
safety; assessor context leakage (can the assessor see prior verdicts by any route?); bypasses of the
verdict-flip and lint-floor refusals, including via whitespace edits and disputes; transaction recovery
at every crash point; adversarial proposal JSON; tests that pass vacuously; and missing
explicit binding in tests (C7).

---

## 6. Stage 3 — phased implementation

Follow the frozen plan. Deviations need recorded impact analysis and, if material, owner approval.

- **A — Contracts, lint, corpus wiring:** record and evidence shapes, refusal codes, lint rules with fixtures.
- **B — Assessment integrity:** assessor subagent (`lint-skill` enforces its read-only grant and fence like
  the other four), verdict-flip and lint-floor refusals in `governance assess`.
- **C — Edit application and loop control:** `refinement` commands, base-SHA operations, shared-source
  refusal and acknowledgement, stall, regression and exhaustion, session lock, re-scan.
- **D — Orchestration contract:** `modules/requirements-refinement.md`, `CAPABILITY_MAP` row, the
  `SKILL.md` governance section, `/sdle-start` if needed, the `CLAUDE.md` architecture paragraph,
  write-fence coverage of the new record.
- **E — Tests, Getting Started, ADR-013.**

Each phase: smallest coherent change; deterministic mocks for every AI-dependent path; focused tests plus
`lint-skill`; inspect the diff; update the ledger. No suppressed tests and no weakened assertions. At the
end of each phase, run the §9 defect batch if the register has open items.

---

## 7. Stage 5 — final verification

Verify against the frozen plan and acceptance scenarios. Run `lint-skill`; the full suite; the corpus
evaluation with before/after metrics; unit and integration tests; interruption and resume at every write
point; and the dry-run scenarios below, **executed** in disposable projects with evidence in the ledger.
No new transcript is added to `docs/dry-runs/` in this change (§10). Report every check as PASS, FAIL,
SKIPPED, NOT RUN or ENV-BLOCKED with exact commands. CI means all four cells (F12).

### Acceptance scenarios

1. Requirements pass initially; the loop is not entered; no extra gate; `todo-api.md` untouched.
2. One failed check is fixed in one iteration; the existing gate passes.
3. Multiple findings need several iterations; each revision traces to finding ids and decisions.
4. A business question pauses the loop; it resumes after a recorded human answer, without re-asking.
5. A rejected edit is not applied and not recorded as approved.
6. A targeted fix regresses another check; full reassessment detects it; no auto-continue.
7. An identical proposal or unchanged digest is a stall and ends `ESCALATED`.
8. Cap exhaustion ends `ESCALATED`; `init` is still refused while quality is blocked.
9. `nfrs: NOT_APPLICABLE` and tighten-only policy semantics are unchanged; no new exception path exists.
10. Interruption during assessment, decision or apply resumes with no duplicate edit or decision.
11. Concurrent invocation is refused by the session lock; state and documents are uncorrupted.
12. WorkItem A's refinement cannot write WorkItem B's files, record or decisions.
13. A legacy WorkItem already past governance behaves exactly as before.
14. Greenfield and brownfield (`ITERATIVE` against a baseline) both handle every outcome; brownfield
    `compatibility` and `dependencies` findings cite baseline entries.
15. Editing a bound document after assessment triggers the existing `governance_stale`.
16. Malformed or adversarial proposal JSON (path traversal, unbound path, stale base SHA, embedded
    verdicts, oversized operation, instructions injected into requirement text) cannot write or
    authorise anything.
17. A document bound by two WorkItems is refused `refinement_shared_source` without acknowledgement.
18. An acknowledged shared edit is recorded in both WorkItems' audit, and the other WorkItem's staleness
    is reported.
19. A FAIL→PASS verdict at the same content digest is refused `quality_verdict_flip`.
20. A check with a lint failure cannot be reported PASS.
21. The assessor's captured input contains no prior verdicts, findings or proposals.
22. A whitespace-only diff auto-applies; a one-word semantic change does not.
23. Corpus: per-check detection and false positives are reported before and after; zero findings on the
    clean fixture.
24. A refinement flow with the binding step skipped makes the relevant test fail.
25. A whitespace-only edit that changes raw bytes but not the content digest does not unlock a FAIL→PASS
    flip.
26. A dispute with independent evidence and a human decision overturns a FAIL; the original result
    remains in evidence, and the check is reported as `overturned_by_dispute`, not as improvement or
    progress. A dispute missing either part is refused.
27. Changes to list nesting, list markers, table structure, heading level or emphasis are never
    auto-applied.
28. Lint does not flag a categorical security, compliance or compatibility requirement for lacking a
    number, nor a precise plain-sentence acceptance criterion for its format.
29. A simulated crash after the shared-document write and before each affected audit entry recovers on
    the next invocation with exactly one audit entry per WorkItem; a document found at an unexpected SHA
    is an integrity refusal that changes nothing.
30. Stage 0 records verified evidence for every prior stabilization item, or blocks Stage 3.

Never treat a fabricated business decision as approved. Mark simulated answers as simulated.

### Final deliverable

`.sdle/implementation-state/requirements-refinement/REPORT.md`: summary; exact changed files;
deviations from the frozen plan; before/after behaviour; corpus metrics; evidence per acceptance
scenario; commands and results; both complete Codex histories and dispositions; the Stage 0 verification
evidence; the defect register with final statuses; any assessment disputes, reported separately from
improvements; the drift list with its classifications; limits stated plainly (F8, faithful copying of assessor output if unverifiable, the
assessor is still an LLM); documentation changes; the open-items register (§10). Status is `COMPLETE`
only if every mandatory gate truly passed; otherwise `BLOCKED` or `INCOMPLETE` with exact reasons.

---

## 8. Documentation scope

**User documentation: `docs/GETTING-STARTED.md` only.**

- Section 11, step 6 currently says a failed blocking check stops the workflow until the requirements are
  fixed. Rewrite it to describe the loop: findings, targeted proposals, questions, decisions,
  re-assessment, the shared-document acknowledgement, and what `ESCALATED` means for the user.
- Add every new refusal code to the section 13 troubleshooting table, using only codes the engine raises.
- Add `refinement.json` and refinement evidence to the section 12 table of what exists after the first start.
- Do not rename or remove any existing heading (other documents link to its anchors). Every command shown
  must parse under the real parser, with global options before the subcommand. Do not teach the install
  command anywhere else. Run `test_units_documented_commands.py` and `test_units_doc_links.py`.

**Product contract, changed with the code:** `SKILL.md`, the new capability module, `CAPABILITY_MAP`,
affected `.claude/commands/*`, the new agent file, the `CLAUDE.md` architecture paragraph, ADR-013.

**Corrections of false statements, in scope (C9).** In Stage 5, produce the drift list: every statement in
`docs/`, `README.md` and ADR cross-references about the requirements-quality step that the shipped
behaviour makes **false** (starting from searches for "fix the requirements", "re-assess",
`requirements_quality_blocked`, "twelve", and every new refusal code), each classified as:

- **False** (following it would now fail, be refused, or mislead the user about what happens): corrected
  in this change with the minimal edit, a sentence or a table row, or a short pointer to Getting Started.
  No section rewrites, no new pages, no renamed headings. Each correction must keep
  `test_units_documented_commands.py`, `test_units_doc_links.py` and `test_dry_run_contracts.py` green.
  Existing dry-run transcripts are corrected only if a transcript shows engine behaviour that has
  changed; if that is impossible without changing the transcript contract, record it and escalate.
- **Incomplete** (still true, but silent about the loop): left for §10.

The list and each classification go in the ledger and the report. Completion requires zero statements
classified as false.

---

## 9. Defects found during this work — parallel fix protocol

### Definition

A **defect** is behaviour that contradicts the frozen plan, an acceptance scenario, an existing engine
contract or invariant, or a test that passed at baseline, when it is found:

- in code whose Stage 3 phase is already closed;
- by the Stage 4 Codex review and dispositioned as a defect;
- during Stage 5 verification or dry-run execution;
- pre-existing in the repository, discovered during this work (including baseline failures);
- carried from prior stabilization work and found open in Stage 0.

A failing test in the phase currently being implemented is **not** a defect; it is normal development
and is fixed inline.

A prior-stabilization defect found open in Stage 0 is fixed under this protocol regardless of where it
lives (C8). Any other pre-existing defect **inside** the impact surface mapped in Stage 1 is fixed under
this protocol; one **outside** it is recorded in the register with a reproduction and left unfixed in
this change.

### Register

The ledger holds a defect register: id `DEF-RR-nnn`, source (stage and finding id), description,
reproduction, affected surfaces, dependencies, status (`OPEN`, `IN_PROGRESS`, `FIXED`, `VERIFIED`,
`BLOCKED`), branch, commits, tests. Only the integrator writes it.

### When batches run

At the end of Stage 0 (before Stage 3 starts), at the end of each Stage 3 phase, after Stage 4 reconciliation, and after Stage 5 verification. A defect
that blocks further work triggers a batch immediately.

### Parallelisation

- The integrator predicts, per defect, the files and (for `scripts/sdle.py`) the functions each fix will
  touch. Defects with disjoint surfaces and no dependency run concurrently, one sub-agent each, at most
  four at a time. Overlapping or dependent defects are serialised in one sub-agent, in dependency order.
  The engine is a single file, so expect genuine parallelism mainly across engine, hooks, prompts and
  tests, and record how much actually occurred.
- Each concurrent sub-agent runs through the Task tool in its own Git worktree on `fix/<sanitised-id>`,
  created by the integrator, with a recorded id-to-branch mapping. A sub-agent works only inside its
  worktree and never edits another worktree, the ledger or shared plans.
- If the Stage 1 capability check found the Task tool or worktrees unavailable, fix sequentially under
  the same evidence rules and record that parallel execution did not happen. Never claim parallelism
  that did not occur.

### Each sub-agent must

1. Search the whole relevant codebase for **every** surface touching the affected behaviour (entry points,
   call sites, state transitions, CLI, templates, prompts, agents, hooks, tests, docs), list them, and
   justify every excluded surface.
2. Write failing regression tests on every affected executable surface, and a static or contract check
   for non-executable ones. Capture the red run before fixing.
3. Implement the smallest correct fix. No unrelated changes, no features.
4. Iterate only on the targeted tests until green. Before each targeted run:
   `python -c "import sys; sys.path.insert(0, 'scripts'); import sdle"` and
   `python scripts/sdle.py lint-skill`. Never run the full suite inside a sub-agent.
5. Never invent constants, fields, reason codes, options, paths or output formats; read the source or an
   existing test first.
6. Make no business decision and hold no human decision; anything needing one returns to the integrator.
7. Commit in its own branch; do not push or merge. Report: defect id, all surfaces, branch and worktree,
   red-to-green evidence, files changed, tests added, exact commands and results, assumptions, risks.

### Integration

The integrator reviews each diff and its evidence, merges the fix branches into the working branch of
this change in dependency order, resolves conflicts, and runs the **full suite once, in the foreground**
(waiting for its exit code), as the batch's acceptance run. Cross-defect breakage is fixed, focused tests
are rerun, and the full suite is rerun as needed; every full run is recorded honestly. Remove the fix
worktrees after merging.

Push only if authorised. Wait for and inspect all four CI cells; never infer success from a push or a
local pass. If CI fails, diagnose, fix, rerun, push and wait again. If CI cannot be accessed, mark the
affected defects `BLOCKED` with the reason, do not invent links, and do not proceed with work that
depends on them.

### Review of fixes

Fixes made during Stage 3 are part of the implementation reviewed in Stage 4. Fixes made after Stage 4's
Level 2 review, including those from Stage 5, get targeted Codex verification of the changed material,
and every Stage 5 check they affect is rerun.

---

## 10. Open items register

Carry these in the ledger and the final report. They are deliberately out of scope for this change.

| ID | Item | Exit criterion |
|---|---|---|
| OI-DOC-01 | **Tutorials.** Extend `docs/tutorials/` (at least `greenfield.md`, `greenfield-full-tour.md`, `iterative.md`, `brownfield-discovery.md`) to walk through the refinement loop. False statements are already corrected in this change (§8). | Each tutorial runs end to end and demonstrates the loop. |
| OI-DOC-02 | **Reference guides.** `docs/SDLE-Reference-Guide.md`, `docs/risk-and-gates/README.md`, `docs/lifecycle/README.md`, `docs/workitems/README.md`, `docs/troubleshooting/README.md` (one entry per new refusal), `docs/README.md`, root `README.md`, `scripts/README.md` (new commands). | Every new command and refusal documented once; all cross-links resolve. |
| OI-DOC-03 | **Dry runs.** Transcripts for the refinement loop (pass first time, multiple iterations, escalation, shared-document refusal) and an updated `docs/dry-runs/verification-matrix.md`. Requires changing the sixteen-transcript assertion in `test_dry_run_contracts.py`. | Contract tests pass with the new count; every refusal shown is engine-raised. |
| OI-DOC-04 | **Drift removal.** The statements classified *incomplete* in the Stage 5 drift list (§8). | Every listed statement updated or confirmed accurate. |
| OI-FUT-01 | Whether any lint rule should become blocking, decided from the corpus precision data. | Owner decision with data. |
| OI-FUT-02 | Refinement after `init`. Interacts with the Controlled Gate Rework Loop. | Owner decision. |
| OI-DEF | Pre-existing defects outside the impact surface, from the §9 register. | Each triaged by the owner. |

---

## Start now

Begin Stage 0: verify prior stabilization (§4.0). Then Stage 1: record the checkout, re-verify §1, map the impact surface, build the evaluation corpus and
measure the baseline, run the baseline suite, run the parallel capability check, and write the plan. Then
run the full Codex–Claude–Codex–Claude plan review **before writing any production code**.
