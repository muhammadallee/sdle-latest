# T05 Implementation Checkpoint — Attempt a01 / Checkpoint 04

**Phase:** T05 — Introduce Repository-Level `.sdle/` Configuration Boundary
**Attempt:** 01

## Objective currently being worked

Milestone **M6** — the full sweep, the A1–A22 matrix, the handoff and the
`progress.md` status change. **Complete.** T05 is IMPLEMENTED and awaiting
independent verification.

## Completed since previous checkpoint

- Full suite run twice at the final tree and agreeing: **569 passed** on the
  scratch snapshot (`715.31s`, RAW_EXIT=0) and **569 passed** in the actual
  repository working tree with no edit in flight (`656.85s`, RAW_EXIT=0). Both
  produced **no** `-rsxX` short-summary section.
- The A1–A22 acceptance matrix completed with commands run in this context.
- `docs/transition/phases/T05-handoff-a01.md` written from
  `docs/transition/templates/phase-handoff.md`.
- `docs/transition/progress.md`: the T05 row moved `PLANNED` → **IMPLEMENTED**,
  attempt `0` → `1`, Handoff cell pointed at `T05-handoff-a01.md`. The planner's
  Tests and Notes text is preserved verbatim at the end of each cell.

**One process note for the record.** The first attempt at the `progress.md` row
made `validate.py` exit **3** with `progress row must have 9 columns`, because
the narrative contained literal `|` characters (inside grep alternations such as
`speckit-|/speckit.`). The row was restored with `git checkout --` and rewritten
with the pipes removed; `validate.py` then exits **0**. Anyone editing that table
should avoid `|` inside a cell entirely.

## Remaining

Nothing. No further product edit is required or authorised in this phase.

## Files changed

```
M  scripts/sdle.py
M  tests/test_units_workitem_resolution.py    (the single authorised literal)
M  README.md
M  CLAUDE.md
M  docs/SDLE-Reference-Guide.md
M  docs/transition/progress.md                (T05 row -> IMPLEMENTED)
?? tests/test_units_repo_config.py
?? docs/architecture/ADR-002-repository-configuration-boundary.md
?? .sdle/config.json, .sdle/policies/.gitkeep, .sdle/templates/.gitkeep,
   .sdle/implementation-state/.gitkeep
?? docs/transition/phases/T05-handoff-a01.md
?? docs/transition/phases/T05-checkpoint-a01-01..04.md
M  .claude/settings.local.json                (pre-existing, OUT OF SCOPE)
```

## Tests actually run

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (working tree) | **569 passed in 656.85s (0:10:56), RAW_EXIT=0**; `grep -c "short test summary"` = 0 |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` (working tree) | **569 tests collected in 0.55s** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX <scratch>/m6/tests"` | **569 passed in 715.31s (0:11:55), RAW_EXIT=0** |
| Pristine baseline at `bf4ba5e` | **500 passed in 617.01s, RAW_EXIT=0**, 500 collected |
| `rtk proxy "python scripts/sdle.py lint-skill"` | raw exit **0**, **22 PASS / 0 FAIL** |
| `rtk proxy "python tools/transition/validate.py"` | `TRANSITION_VALID: complete=5/12 next=T05`, raw exit **0** |
| Python 3.11 / CI | **NOT_RUN** / **UNKNOWN** |

## Current failures

None.

## Git status / diff summary

- HEAD: `bf4ba5e1f52a893c3ef0247c173687268e5c546c` on `transition/workitem-v1`.
  Nothing committed by this phase; the change sits in the working tree.
- Rollback point: `7b054ee`. Recovery is `git reset --hard 7b054ee` plus
  `rm -rf .sdle/`.

## Unresolved decisions

None. The single declared divergence (N10 clause 2 needs `.sdle/` committed) is
recorded in the handoff, not open.

## Exact resume instruction

T05 implementation is finished. A fresh context should **verify**, not
re-implement: read `docs/transition/phases/T05-handoff-a01.md`, re-derive its
figures, and work the "Claims for verifier to independently check" list. Do not
edit any product file to make an assertion pass.
