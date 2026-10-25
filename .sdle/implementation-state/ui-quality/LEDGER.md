# LEDGER — UI quality enhancement

## Current status
Phase A-build: step 1 (phase plan, record-directory pin, PROGRESS.md) in progress. Base `3cd3b19`, branch `enh/requirements-package-loop`.

## Decisions and deviations
| # | Item | By |
|---|---|---|
| L1 | `sdle-requirements-review.md` is not modified (A-PLAN D-A1): its contract is "answer the engine's checks and no others", so a UI check needs an engine change, which Phase A may not make | plan, optional item |
| L3 | Step 1 committed on shards 0-6 + targeted run; the complete suite is run at step 4 on the final tree. The 10-minute foreground cap forces sharded calls (departure from "one foreground run") | owner ("go ahead" on option 3) |
| L2 | `architecture-memory-contracts.md` §15 (six-guideline tree) is a frozen ADR-013 contract and is left as written | A-PLAN §1 |

## Test runs
| # | Command | Result | Duration |
|---|---|---|---|
| T1 | `lint-skill` at step 1 | 0 failed | — |
| T2 | targeted: capabilities, doc_links, install_contract, lint_skill | 284 passed | 183 s |
| T3 | full suite, 18 shards of `requirements-package-loop/shards-final.json` (4215 collected), shards 0-6 | 245+174+474+380+200+1271+217 = 2961 passed | ~28 min |
| T3b | shards 7-17 | **not run**: the background job was reaped for low memory. Owner chose to defer them to the step-4 full run | — |

## Codex runs and dispositions
| Run | Kind | Reviewed commit | Result | Findings |
|---|---|---|---|---|

## Codex plan review, A round 1
Run `20261010T125932-stage2-codex-A-plan-r1` (codex-cli 0.160.1, reviewed `85d6d4b`, read-only frozen worktree, privacy check clean). Result PASS; 6 findings, all confirmed against the source and **accepted**; none rejected. Not reviewed by Codex: phases B/C/D/E/M designs, reproduction of historical probes and the baseline, external Spec Kit runs, the full suite.

| Id | Sev | Disposition |
|---|---|---|
| PR-R1-001 | medium | accepted: A-PLAN §1 now says which values are `3cd3b19` state and that the pins landed in `7c21840` |
| PR-R1-002 | high | accepted: PLAN amendment. Experiments do not reproduce the guideline or native design phase. **Owner attention OA-1** (choice at A-measure) |
| PR-R1-003 | medium | accepted: PLAN amendment, manifest of inputs before A-measure. **Owner attention OA-2** |
| PR-R1-004 | medium | accepted, verified in source (`implementation_exclusions` at `sdle.py:18642-18651` omits `.claude/`; `test_evidence_stale` at `:17157`): PLAN amendment; documentation states it |
| PR-R1-005 | medium | accepted: PLAN amendment |
| PR-R1-006 | medium | accepted: PLAN amendment, two-commit checkpoint |

Round 2 is triggered (accepted defects).

## Codex plan review, A round 2
Run `20261010T130330-stage2-codex-A-plan-r2` (reviewed `76dc220`, read-only frozen worktree, privacy check clean). PASS; 1 finding. Codex verified all six round-1 fixes, executed `lint-skill`, reproduced probes R4-R7 and read the Spec Kit v1.0.6 templates. **Not reviewed:** the full suite, historical R1-R3 results and remote state, live Spec Kit generation, phases B/C/D/E/M designs, pilot rendering.

| Id | Sev | Disposition |
|---|---|---|
| PR-R2-001 | medium | accepted: PLAN amendment (clarification policy and run deadline in the input manifest); folded into **OA-2**. No round 3 is run |

## Test runs, step 4 (implementation)
| # | Command | Result |
|---|---|---|
| T4 | `lint-skill` on the implementation | ok, 0 failed |
| T5 | full suite, 18 shards, 4215 collected (`runs/a-s4-full-*.json`) | 4214 passed + 3 skipped across 18 shards; one failure `test_the_install_directories_hold_exactly_the_expected_files`, which counts git-tracked files and failed only because `ui-design.md` was untracked. After `git add`, `test_units_install_contract.py` 36 passed |
| T6 | after IR-R1-001 fix: capabilities, lint_skill, shipped_surface, documented_commands, install_contract, dry_run_contracts (`runs/a-s5-fix1.json`) | 1672 passed |

## Codex implementation review, A round 1
Run `*-stage2-codex-A-impl-r1` (reviewed `540f175`, diff `a1feffa..HEAD`, read-only, privacy check clean). PASS; 1 finding, confirmed by reading `phase-execution.md` and **accepted**. Not reviewed: live Spec Kit generation, pilot rendering, an independent rerun of the full suite.

| Id | Sev | Disposition |
|---|---|---|
| IR-R1-001 | medium | accepted: the spec/plan/tasks UI-append bullets sat after the Spec Kit invocation bullet, so following the block in order skipped them. Moved ahead of the invocation in all three blocks and reworded "append to the `speckit-<x>` arguments in the next step". T6 re-run |

Round 2 is triggered (accepted defect).

## Codex implementation review, A round 2 — BLOCKED
Run `20261010T142651-stage2-codex-A-impl-r2` (codex-cli 0.160.1, reviewed `9c8797d`, read-only frozen worktree, privacy check clean). Result **BLOCKED**: two attempts, both exit 0 with schema-shaped output, both rejected by the runner's own rule "empty findings with unreviewed areas: the review is incomplete".

Substance of both attempts (`runs/*A-impl-r2.a1.review.json`, `.a2.review.json`): **zero findings**; IR-R1-001 verified fixed in all three blocks, and each condition judged evaluable at its point; no engine or hook change in the diff. Areas Codex did not reach: live Spec Kit generation, pilot rendering, an independent run of the suite and lint, historical records and remote state, later-phase designs.

Disposition: **not substituted and not retried a third time** (PLAN §5.1: no round 3; the brief: a run that fails twice is recorded and stopped for the owner). Raised as **OA-4**.

**OA-4 resolved (owner, 10 Oct 2026): option (a).** The zero-finding substance of the two round-2 attempts is accepted as the round-2 result; the run stays recorded BLOCKED by the runner's rule, with the unreviewed areas above. No third run.

## Phase B (11 Oct 2026)
Built on `863bcfb` before its plan review (OA-7). One combined Codex review plus round 2 (codex-cli 0.160.1, read-only frozen worktrees, privacy check clean each time).
- Round 1 (`8e9bf83`): PASS, 5 findings BR-R1-001..005, all accepted and fixed in `8135b29`.
- Round 2 (`f0326a1`): PASS, 2 findings BR-R2-001..002 (example harness completeness and stale report), both accepted; fixed and verified by executed runs. No round 3.
- Tests: full suite 4218 passed, 3 skipped (`b-full-*`); after round 1 fixes 2091 passed over 10 affected files (`b-fix-targeted`); the three pin groups `-k test_b` 5 passed.
- Not done (OA-8): seeded-defect detection, five clean reruns, harness inside a full SDLE run.

## Phase B narrow measurement (11 Oct 2026)
Two screens, seven seeded defects, checks written from the requirements. First pass 2 of 5 valid mutations detected (two mutations did not compile); checks then repaired three times against the same mutations (shell-level overflow, URL assertion, empty-state pattern, shell width bound) to 7 of 7, with 6 of 6 clean runs green. Reported as optimistic. Scaffolding in `ui-quality-pilot/support/b-measure` (outside the repository). Not done: accessibility and overlap classes; harness through a full SDLE run.

## Phase M (11 Oct 2026)
Phase plan `phases/M-PLAN.md` at `4d7d1ea`. Codex plan review round 1 (`20261011T182531-stage2-codex-M-plan-r1`, reviewed `7571ef6`, read-only, privacy check clean): PASS, 3 findings, all accepted and folded into M-PLAN section 7 as design amendments.

| Id | Sev | Disposition |
|---|---|---|
| MP-R1-001 | medium | accepted: `_blocking_finding_fingerprints` must not return `[]` on unreadable or inconsistent evidence; refuse `review_evidence_invalid`; the unhashed-evidence boundary is documented |
| MP-R1-002 | medium | accepted: `loop record` also refuses an iteration whose review step is unstructured; recovery is `loop stop` then `loop begin` |
| MP-R1-003 | medium | accepted: one rule, every actor type except `human`, any review type, either result, before `reserve_evidence` |

Round 2 is triggered (accepted defects).

### Codex plan review, M round 2: BLOCKED (11 Oct 2026)
Run `*-stage2-codex-M-plan-r2` (codex-cli 0.160.1, reviewed `f67cf93`, read-only, privacy check clean). Two attempts, both exit 0 with schema-shaped output, both refused by the runner's rule "empty findings with unreviewed areas: the review is incomplete". Substance of both attempts: **zero findings**. Not reached by Codex: running tests and lint, any implementation (none exists), unrelated subsystems. No third run and no substitute reviewer. Raised as **OA-9**; the engine implementation waits for the owner's answer.

### Phase M implementation (11 Oct 2026)
Engine change in `scripts/sdle.py` (the first of this enhancement), tests, prompts, docs. Tests: full suite 18 shards **4236 passed, 3 skipped** (`m-full-*`); after round 1: 802 passed, 1 skipped over the loop, artifact-review, review-types, invariants, dry-run, lint and gate-policy files (`m-fix-targeted`).
- Codex implementation round 1 (reviewed `5edc8f9`): PASS, 1 finding **MI-R1-001** (malformed finding fields with unchanged counts raised an unhandled `TypeError` out of `_blocking_finding_fingerprints`): accepted, fixed in `9c044ec` with two tests.
- Codex implementation round 2 (reviewed `cd53e31`): **BLOCKED**, both attempts zero findings, refused by the runner's coverage rule (running tests, command-level no-write tests, unrelated engine behaviour not reached). Not retried, no substitute. Raised as **OA-10**.

## Phase T, project design systems (25 Oct 2026)
Owner decision after the theme experiment. Plan `phases/T-PLAN.md` at `9e94ec0`. The first plan-review attempt never started: the active Node version had changed (nvm 22.16 to 22.23.3) and codex-cli is installed under the old one; the runner was re-run with that directory on PATH for the command only (same codex-cli 0.160.1), the owner's global setup unchanged.
Codex plan review round 1 (`*-T-plan-r1`, reviewed `425a957`): PASS, 4 findings, all accepted and folded into T-PLAN section 8.

| Id | Sev | Disposition |
|---|---|---|
| TP-R1-001 | high | accepted: theme content is not protected by drift; plan line records a git blob hash, re-checked at design and implement, change shown to the user; limit stated |
| TP-R1-002 | medium | accepted: precedence placed in the ADR-014 amendment; conflicts go to the user; app-design cites, never copies |
| TP-R1-003 | medium | accepted: chosen at plan_draft in every flow; shown again at gate_implement where no plan gate ran |
| TP-R1-004 | medium | accepted: the redesign rule is labelled prompt-level; ambiguity raised to the user |

Round 2 triggered.

