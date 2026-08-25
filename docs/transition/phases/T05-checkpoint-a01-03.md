# T05 Implementation Checkpoint — Attempt a01 / Checkpoint 03

**Phase:** T05 — Introduce Repository-Level `.sdle/` Configuration Boundary
**Attempt:** 01

## Objective currently being worked

Milestone **M5** — the repository's own versioned `.sdle/` and the four
documentation edits — is complete. **M6** (full sweep, A1–A22 matrix, handoff,
`progress.md` → IMPLEMENTED) is in progress.

## Completed since previous checkpoint

**M5.**

- `python scripts/sdle.py config init` run at the repository root. It created
  `.sdle/config.json`, `.sdle/policies/.gitkeep`, `.sdle/templates/.gitkeep` and
  `.sdle/implementation-state/.gitkeep` — four files, no `baseline.json`.
  `git check-ignore -v .sdle/config.json` exits **1**, so `.gitignore` needed
  **zero** edits, exactly as D7/Unknowns §5 predicted.
- New `docs/architecture/ADR-002-repository-configuration-boundary.md`.
- `README.md`: the repository `.sdle/` block added above `workitems/` in
  "In your target project"; a new `### Repository configuration` subsection with
  the two `config` rows; the project-root marker sentence now lists
  `.sdle/config.json`; the runtime-free command sentence now lists `config`; a
  paragraph distinguishing the two `.sdle/` directories.
- `docs/SDLE-Reference-Guide.md` §4: new un-numbered `### Repository
  configuration boundary` subsection carrying the two-column ownership table,
  placed immediately before §4.3.
- `CLAUDE.md`: one paragraph after the existing "Runtime state is
  WorkItem-scoped" paragraph.

`lint-skill` was re-run after **each** document edit (F7), five times in total,
and reported **22 PASS / 0 FAIL** every time.

**Line endings.** All four edited documents and `scripts/sdle.py` report
`i/lf w/lf` under `git ls-files --eol`.

## Remaining

- M6 only: full-suite figure, the A1–A22 acceptance matrix, `T05-handoff-a01.md`,
  and `progress.md` → IMPLEMENTED. No further product edit is planned.

## Files changed

```
M  scripts/sdle.py
M  tests/test_units_workitem_resolution.py    (the single authorised literal)
M  README.md
M  CLAUDE.md
M  docs/SDLE-Reference-Guide.md
?? tests/test_units_repo_config.py
?? docs/architecture/ADR-002-repository-configuration-boundary.md
?? .sdle/config.json, .sdle/policies/.gitkeep, .sdle/templates/.gitkeep,
   .sdle/implementation-state/.gitkeep
?? docs/transition/phases/T05-checkpoint-a01-01..03.md
M  .claude/settings.local.json                (pre-existing, OUT OF SCOPE)
```

## Tests actually run

| Command | Result |
|---|---|
| Pristine baseline, `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX <scratch>/baseline-bf4ba5e/tests"` | **500 passed in 617.01s, RAW_EXIT=0**; 500 collected; `grep -c "short test summary"` = **0** |
| M2 snapshot full suite, same shape | **541 passed in 627.24s, RAW_EXIT=0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_repo_config.py"` (at M4) | **69 passed in 51.51s, RAW_EXIT=0** |
| `rtk proxy "python scripts/sdle.py lint-skill"` after each of the five M5 edits | raw exit **0**, **22 PASS / 0 FAIL** each time |
| `rtk proxy "python tools/transition/validate.py"` | `TRANSITION_VALID: complete=5/12 next=T05`, raw exit **0** |
| Final full suite (M6 snapshot) | **IN FLIGHT** — background task `b89joxyax` against `<scratchpad>/m6/tests` |
| Python 3.11 / CI | **NOT_RUN** / **UNKNOWN** |

## Current failures

None.

## Git status / diff summary

- HEAD: `bf4ba5e1f52a893c3ef0247c173687268e5c546c` (`transition/workitem-v1`)
- Rollback point `7b054ee`; product baseline `f8fdaa0`
- Nothing committed by this phase yet.

## Unresolved decisions

None.

## Exact resume instruction

1. Verify `.sdle/config.json` parses to `{"configVersion": "1", "policyFormat": "json"}`
   and that `.sdle/` holds exactly four files.
2. `rtk proxy "python scripts/sdle.py lint-skill"` → 22 PASS / 0 FAIL.
3. Re-run the full suite against a snapshot (`sh <scratchpad>/snapshot.sh m6`,
   then `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX <scratchpad>/m6/tests"`)
   and quote the figure actually observed.
4. Write `docs/transition/phases/T05-handoff-a01.md` from
   `docs/transition/templates/phase-handoff.md`, complete the A1–A22 matrix, and
   set T05 to IMPLEMENTED in `docs/transition/progress.md`.
5. No further product edit is required or authorised.
