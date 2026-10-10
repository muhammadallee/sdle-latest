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
