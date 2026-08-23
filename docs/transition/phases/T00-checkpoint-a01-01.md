# T00 Checkpoint a01-01 — verification results recorded

**Phase:** T00 | **Attempt:** 01 | **Milestone:** baseline.md §1–§3 written

## What is durable on disk

- `docs/transition/baseline.md` §1 (identity), §2 (environment), §3 (verification results).

## Observed results already captured

| Command | Exit | Result |
|---|---|---|
| `git rev-parse HEAD` | 0 | `f8fdaa048b9a9a35d317224eddd191318ccdd7f6` — MATCH vs contract |
| `python scripts/sdle.py lint-skill` | 0 | 22 PASS, `"failed": []` |
| `python -m pytest -q --tb=line -rf` | 1 | `1 failed, 229 passed in 340.51s`; 230 collected |
| F1 re-runs ×3 of `tests/test_integration_01_happy_path.py::test_traversal_matches_the_transcript` | 0, 0, 0 | passed in 9.45s / 9.77s / 35.96s ⇒ ENVIRONMENT_FLAKE |
| `python tools/transition/validate.py` | 0 | `TRANSITION_VALID: complete=0/12 next=T00` |
| `git show HEAD:.github/workflows/ci.yml` | 0 | Python pin `3.11`, matrix `[ubuntu-latest, windows-latest]` |

## Remaining work for a resuming agent

1. baseline.md §4 — 14-subsection capability inventory (evidence gathered: 33 top-level
   `add_parser` names + 32 nested; 25 state top-level fields + 8 approvals keys; 4 hooks;
   13 migration rows; exit codes at `scripts/sdle.py:37-40`).
2. baseline.md §5 — regression matrix over all 31 contract §18 rows.
3. baseline.md §6 — four known baseline conditions.
4. baseline.md §7 — the five contract §6 explicit-preserve items.
5. `docs/transition/phases/T00-handoff-a01.md`.
6. `docs/transition/progress.md` T00 row → IMPLEMENTED / Attempt 1 / Commit UNCOMMITTED.
7. Re-run `python tools/transition/validate.py`, require exit 0.

## Constraints still binding

- No product file may change. `git status --porcelain` must stay all-`??`.
- `write_atomic` must NOT be patched (plan F2).
- Writes go through the Write/Edit tools only; interpreter-mediated writes are refused.
