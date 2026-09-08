# T03 checkpoint a01-05 — M7 (D8: `sdle validate`)

**Phase:** T03 · **Attempt:** 1 · **Milestone:** M7 of 8

Resumed in a fresh context after the previous implementer was terminated by an API
spend limit mid-flight. Attempt stays **a01** — an interruption is not a verification
failure (contract §24.6).

## State reconstructed from disk before any edit

- HEAD `767b657009d9631c3a10a7fee3b87f4e0c549558`, branch `transition/workitem-v1`.
- Working tree carried M1–M6 uncommitted: `scripts/sdle.py`, `.gitignore`,
  `tests/conftest.py`, `tests/test_hooks.py` (plus the pre-existing out-of-scope
  `.claude/settings.local.json`).
- Every M1–M6 symbol claimed by checkpoints 01–04 was confirmed present by `grep`.
- **Discrepancy against the resume brief, repository wins:**
  `tests/test_units_workitem_resolution.py` **does not exist**. `--collect-only` reported
  `341 tests collected`, i.e. the pre-T03 count. So N1–N9, N11 and N12 were *all*
  unwritten, not just N11, and the additive `test_units_workitem_runtime.py` parametrize
  row was also unwritten.
- Baseline re-run in this context: `rtk proxy python -m pytest -q -rsxX` →
  `341 passed in 356.37s (0:05:56)`, **RAW EXIT 0**, no short-summary section.
  (Started before the M7 edits; `conftest` imports `sdle.py` once at collection.)

> Tooling note: the `rtk` hook rewrites `pytest` and swallows its output. Every pytest
> figure in T03's evidence is produced with `rtk proxy python -m pytest …` and the exit
> code is read with no pipe between pytest and `$?`.

## What landed (M7)

`scripts/sdle.py`:

- New `workitem_id_wellformed(value)` — a single source for "is this an id
  `workitem create` could have minted", accepting **both** `WORKITEM_ID_RE` and
  `AUTO_ID_RE`.
- **Defect fixed in T03's own M2 code (TP-003 category 3, no test was red):**
  `active_context_workitem` tested only `WORKITEM_ID_RE`, so a `--auto-generate` id
  (`WI-<name>-<UTC>`, uppercase prefix) could be persisted by `workitem use` and then
  silently ignored by rung 4 forever. It now calls `workitem_id_wellformed`.
- `RUNTIME_FREE_COMMANDS` gains `"validate"` (sixth member).
- New `VALIDATE_ERROR` / `VALIDATE_WARNING`, `_finding`, `_escape_detail`,
  `_validate_metadata`, `_validate_runtime_state`, `collect_validation_findings`,
  `cmd_validate`; `validate` registered in `build_parser`.
- Checks, one per contract §9 bullet: `duplicate_workitem_id`,
  `indexed_workitem_missing_directory`, `directory_missing_index_entry`,
  `malformed_metadata`, `branch_mismatch`, `runtime_state_outside_workitem` (cases a/b/c),
  `path_escape`, plus the speculative-resolution report.

`tests/test_units_workitem_runtime.py`: one additive parametrize row `("validate",)`.

## Declared refinements of plan D8

1. **Severity of the speculative-resolution finding.** D8 says a resolution refusal
   "becomes a finding" but does not give it a severity. It is emitted as
   `active_workitem_unresolved`, **warning**. Error would make every ambiguous repository
   exit 3, and `>1 plausible -> ASK` is §9 working *correctly*, not a registry defect.
   Plan N9 requires `validate` to run successfully in an ambiguous repository.
2. **Case (b) fires only on a genuine disagreement.** A `state.json` whose `workitem`
   field is *absent* is a pre-1.14 state awaiting `migrate`, which `migrate` already
   reports; calling it a misplaced runtime would be a false positive. Only a non-empty
   string that differs from the directory name is a finding.
3. **An unsafe id has its other checks skipped.** Following a symlink out of the registry
   to run metadata and runtime checks would *be* the traversal rather than diagnose one.
4. `read_index` does **not** deduplicate (verified by reading it), so the
   duplicate-id check is genuinely reachable from a hand-edited registry — it is not
   dead code.

## Evidence (all re-run in this context)

| Command | Result |
|---|---|
| `python -c "ast.parse(...)"` on `scripts/sdle.py` | syntax ok |
| `python scripts/sdle.py lint-skill` | **RAW EXIT 0**, 22 `"passed": true`, 0 `"passed": false` |
| `python scripts/sdle.py --project-root . validate` | exit 0, one `active_workitem_unresolved` warning (this repo registers no WorkItem) |
| `rtk proxy python -m pytest -q tests/test_units_workitem_runtime.py -k runtime_free` | `5 passed` |

## Next

M8 — the new test file `tests/test_units_workitem_resolution.py` (N1–N9, N11, N12),
then D7/D9 prompt and documentation layer, then the full sweep.
