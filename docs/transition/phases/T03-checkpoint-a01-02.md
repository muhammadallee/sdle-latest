# T03 checkpoint a01-02 — M2 (D3: persisted active context)

**Phase:** T03 · **Attempt:** 1 · **Milestone:** M2 of 8

## What landed

`scripts/sdle.py`:

- `current_branch(paths)` — single source for "branch, or None when detached/no git". `cmd_workitem_create`'s inline `branch == "HEAD"` check now calls it (pure extraction, behaviour identical).
- New "Persisted active context" section after `registered_workitem_ids`: `ACTIVE_CONTEXT_NAME`, `ACTIVE_CONTEXT_SETTERS`, `active_context_file`, `read_active_context` (never raises), `write_active_context`, `clear_active_context`, `active_context_workitem` (validity: JSON object · id matches `WORKITEM_ID_RE` · id in the index · directory exists and is not a symlink · recorded branch still current), `cwd_workitem`, `branch_candidates` (returns a *set*, never a pick).
- `write_execution_file` gains the `git` object (D4, pulled forward with M2 because `branch_candidates` reads it): `{branch, startSha, worktree}`.
- New `read_execution` / `recorded_branch` readers, never raising.
- New `cmd_workitem_use` — `--workitem <id>` (validated against the index, refuses `workitem_unknown` before any write) or `--clear`.
- `cmd_init` persists the context strictly after `save_state`, non-fatally; `init`'s emitted data gains an additive `active_context` key.
- `cmd_migrate_workflow` gains step 11: persist the context strictly after the commit write and its verification, non-fatally.
- `build_parser` registers `workitem use` with `dest="use_workitem"`, following the `migrate-workflow` precedent.

`.gitignore` — one line appended: `workitems/.active-context.json` (load-bearing: the Phase-17 diff excludes only `runtime_relative`).

`tests/conftest.py` — the single permitted edit: the `.gitignore` string in `init_git` mirrors the product file, plus the adjacent comment line updated to stay accurate. No fixture semantics changed.

## Evidence

- `python -m pytest -q` → `341 passed in 317.12s (0:05:17)`, **RAW EXIT 0**.
- Syntax check on `scripts/sdle.py` passes.

## Note on tooling

The Bash heredoc path mangles backslash escapes (a `"\n"` literal became a real newline once and was repaired). All later patch scripts are written to the scratchpad with the Write tool and executed from there.

## Next

M3 — D2: the new rungs inside `bind_workitem`, `workitem_unregistered`, candidate evidence on `workitem_ambiguous`. Advisor item 5: extract a single decision function so `bind_workitem` and `workitem resolve` share one ladder.
