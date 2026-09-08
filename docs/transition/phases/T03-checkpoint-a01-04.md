# T03 checkpoint a01-04 — M5 + M6 (D4 recorded branch/SHA, D5 branch policy)

**Phase:** T03 · **Attempt:** 1 · **Milestones:** M5, M6

## What landed (`scripts/sdle.py` only)

- `BRANCH_CRITICAL_ACTIONS` — the nine entries the plan enumerates, as a `frozenset` of strings and `(command, subcommand)` tuples.
- `action_key(args)` / `action_name(args)` — every subparser already uses `dest="subcommand"` (verified), so the key is well defined for all commands.
- `branch_mismatch(paths)` — `None` whenever there is nothing to compare: git absent, detached HEAD, null recorded branch, or no `execution.json` at all (the legacy-bound case).
- `branch_guard(args, paths, state)` — called immediately after `read_state` in all nine handlers (`cmd_advance`, `cmd_gate_approve`, `cmd_skip`, `cmd_restart`, `cmd_reset`, `cmd_implement_preflight`, `cmd_manifest_build`, `cmd_drift_rebaseline`, `cmd_artifact_record`). Both paths `append_audit` **and** `save_state` before returning or raising, so `audit.md` never runs ahead of `state.json`'s `audit_sha`.
- `CONFIRMABLE` gains `"branch_mismatch"` (sixth member).
- `cmd_header` gains the additive `data.branch_mismatch` key plus one extra stderr line. `rendered` is byte-unchanged — `test_header_maps_every_status_to_its_display_text` asserts `rendered.endswith(display)`.

## Declared refinement of plan D5 — `_own_confirm_token`

The plan's literal mechanism ("guard first; on mismatch, if pending == branch_mismatch accept, else set it and refuse") **breaks the plan's own pinned `skip` sequence**. Trace: (1) `skip` → guard refuses, pending=`branch_mismatch`; (2) `skip` → guard accepts and clears, `skip` sets pending=`skip`; (3) `skip --confirm` → the guard sees pending=`skip`, treats it as no acknowledgement, and clobbers it back to `branch_mismatch`; (4) `skip --confirm` → guard accepts and clears, `skip --confirm` now finds no pending `skip` and refuses `no_pending_confirmation`. Livelock.

`_own_confirm_token(args)` fixes it minimally: the guard passes through when `pending` equals the token *this* command sets for itself — `skip`→`"skip"`, `reset`→`"reset"`, `restart`→`f"restart:{args.to}"`, `implement preflight`→`"implement_dirty_tree"`. It opens no bypass: the only way that token can be pending is that the command set it on the immediately preceding invocation, which the guard had to allow. Sticky per-branch acknowledgement (recording it in `execution.json`) was considered and rejected — it changes the plan's per-command semantics.

The plan's declared consequence is preserved exactly: on a mismatched branch `skip` needs the branch acknowledgement *and then* its own.

## Evidence

- `python -m pytest -q` → **341 passed, RAW EXIT 0**. No existing test switches branches after `init` (`grep` over `tests/` for `checkout|switch|"branch"|-b ` returns one hit, a prose comment in `conftest.py`), so the guard's blast radius on the pre-existing suite is nil.

## Next

M7 — D8 `sdle validate`.
