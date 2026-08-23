# T02 checkpoint a01-04 — M4 complete (execution identity, `project_name`)

**Milestone:** M4 — `execution.json` + execution identity (plan D7);
`project_name` WorkItem-title rung (plan D10).

## Engine

- `workitem_metadata(paths)` — the bound WorkItem's `workitem.json`, or `None`.
  Never raises: metadata is descriptive, and a missing or unreadable file is
  not a refusal.
- `execution_prefix(paths)` — contract §8 verbatim: `git config user.name` →
  lowercase → drop non-alphanumeric → first 3 chars → email local part → `usr`.
- `execution_identity(paths, stamp=None)` → `<prefix>-<compact UTC>`, reusing
  the same compaction T01's auto-id uses.
- `write_execution_file(paths, execution_id, stamp)` → `<runtime>/execution.json`
  with `executionId` / `workitem` / `startedAt` / `sdleVersion`.
- `cmd_init` writes it, and emits `workitem` and `execution_id`.
- `cmd_init`'s `project_name` precedence is now `--project` →
  requirements-heading inference → **WorkItem title** → `project_root.name`.
  The new rung sits *after* heading inference on purpose (D10), so
  `test_init_infers_project_name_from_first_heading` stays green untouched.

## Tests

New file `tests/test_units_workitem_runtime.py` — 30 cases at this checkpoint
(migration and guardrail cases land at M5/M6). Category: **new tests**, not a
TP-003 category, since nothing existing is superseded by them.

Mapped to the plan: N1-N5 (isolation, both §8 exit criteria, incl. TP-009's
lock test), N6-N13b (all five ladder rungs, `RUNTIME_FREE_COMMANDS` and its
negative half, both `init` legacy refusals), N14-N16 (template, migration under
a WorkItem, migration at the legacy location), N27-N28 (prefix derivation
parametrised over all four contract fallbacks; identity shape and the "not the
WorkItem name" pin), N33 (`reset`), N34-N35 (`project_name`).

`conftest.Project` gained `pin` + `as_workitem(id)`: a pinned view of the same
repository that puts `--workitem <id>` on every invocation, so the isolation
tests drive two WorkItems through the **unmodified** `run_happy_path` helper.

### §7.3 promotion resolved

`isolated_git_identity` moved from `tests/test_units_workitem.py` to
`tests/conftest.py` as an autouse fixture. Precondition discharged first:
`grep -rn 'Actor|actor|user\.name|user\.email' tests/*.py` finds only
`conftest.init_git`'s repo-local config and the fixture's own docstring — **no
assertion depends on the machine's Git identity**, so the promotion is safe.
TP-003 **category 2**, rationale: test-isolation defect, pre-existing, surfaced
by T01, owned by T02 because T02 touches the audit path and adds
execution-identity assertions. It makes tests more hermetic, not weaker.

## Evidence

`pytest tests/test_units_workitem_runtime.py -q` → **30 passed, raw exit 0**
(first run was 29 passed / 1 failed, raw exit 1: `test_a_lock_on_one_workitem_
never_blocks_another` asserted WI-B had no lock file, but its own
`init --session` had legitimately written one. The **test** was wrong, not the
engine — both WorkItems now init without a session, so the assertion measures
what it claims. No engine behaviour was changed to make it pass.)

## Next

M5 — `migrate-workflow`, all 12 D8 steps.
