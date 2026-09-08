# T03 checkpoint a01-03 — M3 + M4 + N10 (D2 ladder, D6 resolve, D9 NB-3)

**Phase:** T03 · **Attempt:** 1 · **Milestones:** M3, M4, and the N10 test rewrite

## What landed

`scripts/sdle.py`:

- New `@dataclass Resolution` and `resolve_decision(paths, explicit, *, for_init)` — **one** ladder, two consumers (invariant 7). `bind_workitem` now only turns a `Resolution` into a binding or into the contract's refusal; `cmd_workitem_resolve` reports the same object.
- Ladder order, as plan D2: explicit → CWD-inside-a-WorkItem → sole registered → persisted valid context → unique branch match → legacy dual-read → `none` → `ambiguous`.
- New refusal `workitem_unregistered` (rung 2, CWD inside an on-disk but unindexed WorkItem). It is the only refusal T03 adds.
- `workitem_ambiguous` keeps its existing `workitems` data key byte-compatible and gains `candidates`.
- New `candidate_evidence(paths, known, branch_matches)` — evidence per candidate (`cwd`, `context`, `context:stale`, `branch:<name>`, `runtime`), registry order, no ranking.
- New `cmd_workitem_resolve` + `workitem resolve` subparser: always exit 0, reports `resolved`/`rung`/`reason`/`candidates`/`launch_cwd`/`project_root`/`branch`/`active_context`.

`tests/test_hooks.py`:

- `test_dirty_tree_is_silent_when_the_workitem_is_ambiguous` renamed and rewritten as `test_dirty_tree_resolves_a_workitem_the_same_way_the_engine_does` (TP-003 **category 2 — genuinely superseded behaviour**; this is NB-3 being closed). Three assertions: fires with two WorkItems and a valid context; silent with the context cleared; silent when the context is branch-invalidated. `.claude/hooks/hooks.py` is untouched.
- Import line gains `FIXTURE_WORKITEM_ID`.

## Evidence

- Before the rewrite the full suite was `340 passed, 1 failed` — exactly and only `test_dirty_tree_is_silent_when_the_workitem_is_ambiguous`, i.e. the single test the plan predicted would be superseded.
- After the rewrite: `python -m pytest -q` → **341 passed, RAW EXIT 0**.

## Deviation from the plan's milestone order

The N10 rewrite is scheduled for M8. It was pulled forward to M3 because M3 is what supersedes the test, and leaving the suite red through M4–M7 would have made every later failure hard to attribute. No content change: the rewrite is exactly the three assertions the plan specifies.

`started_git` replaces `started` in that test so the branch-invalidated case is reachable (without git, `current_branch` is `None` and a recorded branch can never go stale).

## Next

M5/M6 — D5 branch-mismatch policy: `BRANCH_CRITICAL_ACTIONS`, `branch_guard`, `CONFIRMABLE` gains `branch_mismatch`, `cmd_header`'s additive `branch_mismatch` data key. The D4 `execution.json` git block already landed with M2.
