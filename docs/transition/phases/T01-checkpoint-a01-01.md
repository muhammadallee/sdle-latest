# T01 Implementation Checkpoint — Attempt a01 / Checkpoint 01

**Phase:** T01
**Attempt:** 01

## Objective currently being worked

Deterministic core for WorkItem identity (plan D1-D8, D11) plus its new test
file. Documentation/orchestration edits (D9, D10) not yet started.

## Completed since previous checkpoint

- Reconstructed state from disk: `T01-plan.md`, `transition.md` §7/§24.3/TP-003/TP-008,
  `baseline.md`, `progress.md`, `T00-*` evidence, `tools/transition/validate.py`,
  `docs/transition/control-plane.sha256`, `docs/transition/templates/*`.
- Verified plan-vs-repository divergence: plan precondition is HEAD `a12b9e2`;
  actual HEAD is `a40c7ac`. `git diff --name-status a12b9e2..HEAD` = exactly
  `A docs/transition/phases/T01-plan.md` and `M docs/transition/progress.md`
  (the planner's own commit). Zero product files. Divergence is benign; declared
  rather than silently absorbed.
- `scripts/sdle.py`: new `WorkItem identity` section inserted between the
  `init / state / header` section and `Artifact path resolution`. No existing
  function body modified.
  - `WORKITEM_ID_RE`, `AUTO_ID_RE`, `WORKITEM_NAME_MAX = 64`, `RESERVED_NAMES`,
    `INDEX_HEADING`, `INDEX_COLUMNS`, `_RAW_NAME_FORBIDDEN`, `_INDEX_UNSAFE`
  - `_name_invalid()`, `normalize_workitem_name()`, `workitems_root()`,
    `workitem_index_file()`, `workitem_dir()`, `_index_malformed()`,
    `read_index()`, `_index_cell()`, `append_index_row()`, `_git_value()`,
    `cmd_workitem_create()`, `cmd_workitem_list()`
- `scripts/sdle.py` `build_parser()`: one `workitem` group with `create` and
  `list`, registered immediately after `migrate`.
- `tests/test_units_workitem.py`: new file, 57 cases. No pre-existing test
  touched.

## Two implementation decisions worth the verifier's attention

1. **Raw-name pre-check before normalization.** Contract rule 5 ("remove
   unsupported punctuation") alone would turn `a/b` into the *valid* id `ab`,
   silently accepting a traversal-shaped name. `_RAW_NAME_FORBIDDEN`
   (`/ \ |` and control chars) refuses the raw name first, folded into
   `workitem_name_invalid` with `data.rule = "unsafe_character"` — no new
   refusal reason, D6's vocabulary is unchanged.
2. **Registry cells are sanitized on write, not refused.** `_split_row` has no
   escape support, so one `|` or newline in a free-text `--synopsis` would make
   every later `create`/`list` exit 3. `_index_cell()` replaces `| \r \n \t`
   with a space and collapses runs; `workitem.json` keeps the text verbatim.
   Test: `test_a_pipe_in_the_synopsis_cannot_corrupt_the_registry`.

## Remaining

1. `.claude/commands/sdle-start.md` — bootstrap order (D9).
2. `.claude/skills/sdle/SKILL.md` Step 1 — new-workflow ordering sentence (D10).
3. `README.md` — commands + `workitems/` in the target-project layout.
4. `docs/SDLE-Reference-Guide.md` — one WorkItem identity subsection.
5. `scripts/README.md` — inspect; edit only if it enumerates subcommands.
6. `lint-skill` after **each** doc edit (F2).
7. Full suite, F1 procedure for any WinError 5.
8. Self-run acceptance A1-A18.
9. `T01-handoff-a01.md`, then `progress.md` → IMPLEMENTED/1, then `validate.py`.

## Files changed

- `scripts/sdle.py` (modified — additive)
- `tests/test_units_workitem.py` (added)
- `docs/transition/phases/T01-checkpoint-a01-01.md` (this file)

## Tests actually run

| Command | Result |
|---|---|
| `python -m pytest tests/test_units_workitem.py -q` | **57 passed**, exit 0 |
| `python scripts/sdle.py workitem --help` | exit 0, lists `create`, `list` |
| manual create in a scratch dir outside the repo | exit 0; index + metadata written as per D4/D5 |

Full suite, `lint-skill` and `validate.py`: **NOT_RUN** at this checkpoint.

## Current failures

None. One transient test-authoring defect was fixed in this context: a
parametrized case passed `--foo--bar--` positionally, which argparse read as an
option (exit 2). Replaced with the `--name=` form in a dedicated case. That was
a test bug, not a product refusal.

## Git status / diff summary

- Branch `transition/workitem-v1`, HEAD `a40c7ac`, uncommitted.
- Modified: `scripts/sdle.py`. Untracked: `tests/test_units_workitem.py`,
  `docs/transition/phases/T01-checkpoint-a01-01.md`.
- No change to `templates/state.json`, `modules/*`, `hooks.py`,
  `settings.json`, `.gitignore`, `sdle.sh`, `sdle.ps1`, `.github/`, or any
  pre-existing file under `tests/`.

## Unresolved decisions

None. No material decision is required; no blocker.

## Exact resume instruction

Read `T01-plan.md` "Files expected to change" and continue at item 1 of
**Remaining** above. The core is complete and green in isolation; everything
left is documentation/orchestration text plus evidence. Run
`python scripts/sdle.py lint-skill` after every documentation edit — F2 lists
the four concrete traps.
