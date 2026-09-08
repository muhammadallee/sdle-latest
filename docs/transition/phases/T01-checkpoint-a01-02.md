# T01 Implementation Checkpoint — Attempt a01 / Checkpoint 02

**Phase:** T01
**Attempt:** 01

## Objective currently being worked

Documentation/orchestration edits complete; full suite and acceptance run
complete. Remaining work is evidence only: `T01-handoff-a01.md`, `progress.md`,
`validate.py`.

## Completed since previous checkpoint

- `.claude/commands/sdle-start.md` — step 3 is now the WorkItem prompt +
  `workitem create`; `init` moved to step 4; steps renumbered to 6. Resume
  branch explicitly states it never asks for a WorkItem name. Duplicate,
  invalid-name, malformed-index and `auto generate` branches documented.
- `.claude/skills/sdle/SKILL.md` — Step 1's new-workflow paragraph split, with
  an "Identity comes before initialisation" paragraph before `init`. No
  constant table touched. No `"workflow_version"` JSON, no PowerShell-only
  cmdlet, no literal `N/18`.
- `README.md` — `start workflow` row mentions the name prompt; new
  `### WorkItem identity` subsection under Commands (includes the
  `workitem.json` example, which must not live in a skill file); `workitems/`
  added to the target-project File Layout block. No new `**vX.Y**` bold string
  and no second `# SDLE … (vX.Y)` heading.
- `docs/SDLE-Reference-Guide.md` — unnumbered `### WorkItem identity`
  subsection inserted before §4.3, so no section number and no TOC entry moves.
  Header version line untouched.
- `scripts/README.md` — **not edited.** Plan U6: it documents the output
  contract, exit codes and constants only; it does not enumerate subcommands,
  so there is no point to add a row to.

## lint-skill after each documentation edit (plan F2)

| After editing | Result |
|---|---|
| `.claude/commands/sdle-start.md` | exit 0, 22/22 PASS |
| `.claude/skills/sdle/SKILL.md` | exit 0, 22/22 PASS |
| `README.md` | exit 0, 22/22 PASS |
| `docs/SDLE-Reference-Guide.md` | exit 0, 22/22 PASS |

## Tests actually run

`python -m pytest -q` — **RAW EXIT 1**, `3 failed, 284 passed in 374.03s`
(287 collected = 230 baseline + 57 new).

All three failures are `PermissionError: [WinError 5]` at `scripts/sdle.py:463`
(`os.replace` inside `write_atomic`):

```
FAILED tests/test_integration_02_to_05.py::test_03_successful_verification_resets_the_retry_counter
FAILED tests/test_integration_02_to_05.py::test_04_rejection_clears_the_queue_and_does_not_resume
FAILED tests/test_integration_02_to_05.py::test_04_approving_out_of_queue_order_is_refused
```

F1 step 1 — re-ran exactly those three node ids:

```
...                                                                      [100%]
3 passed in 9.60s
RAW_EXIT=0
```

Pass on re-run 1 of 3 ⇒ **ENVIRONMENT_FLAKE**. `write_atomic` deliberately not
patched (plan F1 / scope exclusion; the fix is a human decision at T02
planning). The raw suite exit code is reported as observed: **1**.

## Acceptance criteria observed directly

A1, A2, A3, A5, A7, A8, A14, A15, A16, A18 run as commands in this context;
A4, A6, A9, A10, A11, A13 covered by `tests/test_units_workitem.py` and the
diff checks; A12 above. Full evidence table is in the handoff.

## Current failures

None outstanding. The three suite failures are the inherited environment flake.

## Git status / diff summary

```
 M .claude/commands/sdle-start.md
 M .claude/skills/sdle/SKILL.md
 M README.md
 M docs/SDLE-Reference-Guide.md
 M scripts/sdle.py
?? docs/transition/phases/T01-checkpoint-a01-01.md
?? tests/test_units_workitem.py
```

`git diff --stat -- scripts/sdle.py` = `320 insertions(+)`, **zero deletions**.
`git diff --name-only -- tests/` is empty. `git diff --exit-code` returns 0 for
`templates/state.json`, `modules/`, `.claude/hooks/`, `.claude/settings.json`,
`.gitignore`, `scripts/sdle.sh`, `scripts/sdle.ps1`, `.github/`.

## Unresolved decisions

None. No blocker.

## Exact resume instruction

Everything in the plan's "Files expected to change" is done and verified. A
fresh implementer resuming here needs only to: write
`docs/transition/phases/T01-handoff-a01.md` from
`docs/transition/templates/phase-handoff.md`, set the T01 row in
`docs/transition/progress.md` to `IMPLEMENTED` / attempt `1` / handoff path /
`Commit = UNCOMMITTED` (9 columns exactly), then run
`python tools/transition/validate.py` and confirm exit 0. Do not commit.
