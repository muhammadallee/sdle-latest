# Requirements refinement — final report

Branch `feat/requirements-refinement`, final commit `4a21940`. **CI on that commit: green on all four jobs**
(ubuntu and windows, Python 3.11 and 3.13): 3841 passed on Windows, 3817 passed and 24 skipped on Ubuntu, `lint-skill`
passing. Earlier red runs on the branch came from stale test pins and one real defect found by CI (below); each was
fixed in a later commit.

## Summary

When `governance assess` blocks on requirements quality, a person can now be helped to fix the requirements, safely,
before the workflow starts. A refiner proposes edits and questions; a human decides every change in meaning; the
engine applies only what was accepted and re-checks. The assessment door stays `governance assess` alone.

Built, in the order it was built:

| Phase | What |
|---|---|
| A0 | Inherited defects fixed first: path canonicalisation, state-before-store, recheck of acknowledged content at progression |
| A | The twelve check definitions as one engine table; the presentation-neutral normal form and content digest; the `refinement.json` record (strict, one validated writer); the advisory lint; the amended `todo-api.md` re-measured against the final definitions (3 of 3 pass) |
| B | `quality_verdict_flip` (one verdict per content); strict assessment history; the read-only `sdle-requirements-review` agent |
| C | `refinement propose / decide / apply / dispute / cancel / show`; one shared exclusive-lock helper and the repository mutex; the shared-document rule; the iteration-cap policy key; baseline citations for compatibility/dependencies findings |
| D | `modules/requirements-refinement.md`, routed from `SKILL.md` and `/sdle-start` |
| E | ADR-015, a getting-started section, dry runs 21–22, troubleshooting rows for every new reason |
| F | The requirements-changing-mid-flight guide, with its impact claims reproduced against the engine |
| Stage 4 | Codex adversarial review; 10 of 14 findings fixed |
| After Stage 4 | Owner decisions: (1) refinement allowed when every sharer has not started; (2) the engine surfaces facts and a diff on `governance_stale`; (3) the user chooses what to do and how to redo it (`requirements-change.md`, `restart --approach`) |

## Behaviour, before and after

- **Before:** a blocked assessment ended in "fix the documents and re-run"; an assessor could pass unchanged text it
  had failed a moment earlier; nothing said what to do when requirements changed under a WorkItem except a bare
  `governance_stale`.
- **After:** an optional loop (offered, never started unasked) with these properties —
  - the failing set is the engine's own record, never the proposal's; a proposal carrying verdicts is refused;
  - a check that FAILed at a content cannot read PASS (or NOT_APPLICABLE) at the same content, decided on the
    normal form so whitespace cannot unlock it; the refusal writes nothing and the refused attempt is kept as evidence;
  - the way back from a wrong first verdict is a dispute needing independent evidence, a rationale and a human
    decision, exempting exactly one (check, content) pair, each citation usable once;
  - every edit that changes meaning waits for a recorded human acceptance; layout-only edits are decided by comparing
    normal forms, never by what the proposer says; stale bases are refused;
  - progress, regression, stall and the round limit are computed; the limit is one engine constant, lowerable by
    policy, never raisable;
  - the lint is advisory: `floorEnforced` is always false and a test walks the call graph to prove nothing on the
    assessment path can reach it;
  - a document another WorkItem is working from is refused; one only not-started WorkItems hold is allowed and they
    are reported as affected;
  - when requirements change under a WorkItem, the refusal and `governance show` carry the same facts (what changed
    with a diff, where the WorkItem is, restartable phases, placement status, who else holds the document); the user
    chooses; the choice is recorded.

## Changed files (exact set from the diff against `origin/main`)

44 files, +6367 / −95. The engine `scripts/sdle.py`; one agent file, two capability modules; `SKILL.md`,
`/sdle-start`, `CLAUDE.md`, `README.md`, the Reference Guide and Getting Started; ADR-015, the mid-flight guide,
dry runs 21–22 and the verification matrix; the troubleshooting page; the corpus fixture and sample requirements; and
test modules `test_units_refinement_{record,lint,normal_form,lock,shared,policy,commands,citations}.py`,
`test_units_assessment_integrity.py`, `test_units_stage4_fixes.py`, `test_units_midflight_changes.py` and
`test_units_requirements_change.py`, plus pins updated in the existing suites (listed in the ledger). The full list is
`git diff --stat origin/main`.

## Deviations from the frozen plan (each recorded in LEDGER.md, with the reason)

1. **The lint floor was not shipped** (owner's earlier Option 3) and `quality_verdict_below_floor` is **not defined**:
   the engine has no reason registry and an unreachable refusal would advertise behaviour that does not exist. Codex: accept.
2. **Shared documents:** the plan's acknowledged-shared-edit design (cross-WorkItem audit, transaction index, crash
   recovery) was put on hold. Default shipped: refuse if a sharer may be working from the document; allow if every
   sharer has not started. "May be working from" = has a state that is not provably complete, or has its own loop open.
3. **Dispute evidence is the refused re-assessment** (`governance-flip-attempt-*`), the only independent PASS at the
   same content the engine can produce.
4. **Record schema grew** beyond plan §5.a: edit `id`/`text`/`appliedSha256`/`appliedOrder` and iteration
   `assessmentRef`, because the plan had nowhere to keep the edit payload or the apply order.
5. **Cap exhaustion writes `ESCALATED` and then refuses** (`refinement_cap_exhausted`) — the shape `governance assess`
   already uses for a blocked assessment (RR-012).
6. **A zero-byte or kind-less `governance-*.json` is skipped** by the history reader, not refused: a zero-byte file is
   the documented crash placeholder, and CI showed a test planting a kind-less object. A stated limit (RR-010).
7. `cmd_init` and `cmd_requirements_bind` / `cmd_governance_assess` became thin wrappers that take the mutex, so tests
   that pin function names were updated deliberately.

## Evidence per acceptance scenario (BRIEF §7)

Tests are in the modules named above; the dry runs 21–22 map the loop and its stops.

| # | Scenario | Evidence |
|---|---|---|
| 1 | Clean pass, no loop | `test_a_clean_pass_never_enters_a_loop` |
| 2–3 | One / several iterations | `test_a_passing_reassessment_ends_the_loop_passed`, `…smaller_set_of_failures_is_progress…` |
| 4 | A question pauses and is not re-asked | `test_decide_records_an_answer_once`, `test_a_question_already_answered_is_not_asked_again` |
| 5 | Rejected edit not applied | `test_a_rejected_edit_is_never_applied` |
| 6 | Regression flagged | `test_a_new_failing_check_is_a_regression_that_is_flagged` |
| 7 | Stall escalates | `test_a_repeated_proposal_is_a_stall_and_escalates`, `…same_failures_after_a_change…` |
| 8 | Cap escalates | `test_the_cap_ends_the_loop_escalated_and_refuses` |
| 9 | Policy semantics unchanged | existing governance suite, unchanged and passing |
| 10 | Interruption resumes without duplication | `test_a_retried_apply_after_an_interrupted_one_never_duplicates_the_edit`, `test_an_edit_applies_only_once` |
| 11 | Concurrent invocation refused | `test_units_refinement_lock.py`, `test_every_party_that_decides_ownership_takes_the_mutex`, `test_an_assessment_takes_the_repository_mutex` |
| 12 | One WorkItem cannot write another's files | `test_one_workitems_refinement_never_touches_anothers_files`, `test_a_document_only_not_started_workitems_hold_can_be_refined` (asserts the neighbour's tree unchanged) |
| 13 | Legacy WorkItem unchanged | existing suite, unchanged and passing |
| 14 | Brownfield cites the baseline | `test_units_refinement_citations.py` |
| 15 | Edit after assessment → stale | `test_units_midflight_changes.py`, `test_units_requirements_change.py` |
| 16 | Adversarial proposals | the refused-proposal parametrisation (traversal, unbound path, stale base, embedded verdicts, oversize), `test_an_edit_that_adds_instruction_like_text_is_flagged_by_the_existing_scan` |
| 17 | Shared document refused without acknowledgement | `test_a_sharer_that_started_blocks_even_with_an_assessment`, `test_there_is_no_acknowledgement_path_for_a_shared_document` |
| **18** | **Acknowledged shared edit in both audits** | **DEFERRED — not reported as passing** (applies to a *started* sharer) |
| 19 | FAIL→PASS at one content refused | `test_units_assessment_integrity.py` |
| 20 | Lint cannot floor a verdict | **Amended:** the negative is proved instead — `test_nothing_the_assessment_path_calls_can_reach_the_lint`, `floorEnforced` validated false |
| 21 | Assessor input has no prior verdicts | **Convention only:** the parent builds the assessor prompt; nothing machine-checks it. The agent file and module state it. |
| 22 | Whitespace auto-applies, one word does not | `test_a_presentation_only_edit_…`, `test_a_one_word_change_is_never_called_neutral` |
| 23 | Corpus before/after, clean fixture zero findings | `test_no_floor_eligible_rule_fires_on_a_clean_document`; measurement in LEDGER (exploratory: 3 runs per cell, one model) |
| 24 | Skipping the binding fails | `test_refinement_with_the_binding_step_skipped_is_refused` |
| 25 | Whitespace edit does not unlock a flip | `test_a_presentation_only_change_does_not_unlock_the_flip` |
| 26 | Dispute | `test_a_complete_dispute_overturns_the_pair_…`, replay and incompleteness tests |
| 27 | Structural markup never auto-applied | normal-form tests, plus raw HTML kept as written |
| 28 | Lint does not flag categorical/plain requirements | `test_binary_and_categorical_requirements_are_never_flagged_for_lacking_a_number` |
| **29** | **Crash recovery of a shared write** | **DEFERRED with 18** |
| 30 | Stage 0 evidence | closed in Stage 0 (earlier in this engagement) |

## Corpus metrics (exploratory — not confirmatory)

Every corpus-derived number is three runs per cell, one assessor model, no independent labelling. The amended
`todo-api.md` passes all twelve checks 3 of 3 against the engine's final definition table (outputs in
`stage2/final-measurement/`). The lint: zero floor-eligible findings on the two clean documents; it finds the
blocking-unknowns, out-of-scope, acceptance and ambiguity defects it is built for; `vague_term` and
`quantity_without_measure` fire on non-target documents, which is why they are `floorEligible: false`.

## Codex histories and dispositions

Level 1 and Level 2 plan reviews, three further consultations (whether the owner was needed for Phase C; the shared-
source definition and the floor reason; not-started sharers and rework options), the Phase F catalogue and
disposition, and the Stage 4 adversarial review. Verbatim outputs are in `runs/`, `stage2/` and the task outputs;
dispositions are in LEDGER.md and `claude-review-rejections.md` (RR-001…RR-013).

**Stage 4:** 1 critical, 7 high, 5 medium, 1 low. Fixed (each with a test shown to fail without the fix): the
assessment race, case-spelled paths in the digest, forged dispute outcomes, record state-machine invariants, sharer
validation on full files, `architecture apply` taking the refinement mutex, a lock released only by its holder, raw
HTML kept as written, the apply chain head, one spelling of an evidence reference, quoted marker literals and a
call-graph isolation test. **Not fixed, with reasons:** RR-010 (truncating old evidence defeats the flip rule — same
class as deleting it, outside the engine's guarantee), RR-011 (legacy FAILs with no recorded digest cannot be
compared), RR-012 and RR-013 (rejected as disagreements; reasons in the file).

## Defects CI found that local batches missed

1. The history reader refused a kind-less object; a test plants one as a collision sentinel — every assessment after
   it failed on both OSes. Corrected: inclusion is by `kind`.
2. Pins that name functions (`cmd_init`, `cmd_governance_assess`, the rebinding sites) after the wrappers were added.
3. The shipped-module and agent sets in three suites.

Lesson recorded: local batches must include every module that writes under `evidence/`.

## Open decisions for the owner

1. **Shared documents held by a *started* WorkItem** (scenarios 18 and 29): refuse (shipped) or build the
   acknowledged-edit design (needs a decision on one WorkItem writing another's audit). Codex confirmed shipping the
   refusal was safe but is not final approval of the reduced behaviour.
2. **Regeneration after a rollback** is the orchestrator's behaviour, not an engine property; the new module and
   `restart --approach` make the choice explicit and recorded. Decide whether to make it a stronger contract.
3. **Completed-WorkItem rollback** is tested from a planted completed state, not a real full second pass.
4. The two limits in RR-010 and RR-011 are accepted, not fixed.
5. The mid-flight facts see only this checkout; another branch or uncommitted copy is invisible and the notices say so.

## How to verify

```
python scripts/sdle.py lint-skill
python -m pytest -q            # in CI; ~25 minutes on Windows
```

CI run for the final commit: `37091438670`.
