# T04 checkpoint a01-03 — M3 (WorkItem-scoped feature directory)

**Phase:** T04 · **Attempt:** 1 · **Milestone:** M3 of 7 · **Status:** CLOSED GREEN.

Predecessors: checkpoints 01 (M1) and 02 (M2), both closed green at 438 passed. Rollback point is still `beb28f2`; nothing committed yet.

## What M3 landed (D1 + D6 + D9 + D10 + validate, with its tests)

**`cmd_feature_resolve`** — tiered discovery and adoption.
- Legacy binding (`paths.workitem is None`): behaviour is baseline's exactly — scan `.specify/specs/`, newest mtime, `feature_unresolved` / `feature_ambiguous`, no relocation.
- Under a WorkItem, fixed tier order, first non-empty tier wins: `workitems/<id>/specs/*` → `<project-root>/specs/*` → `.specify/specs/*`. No tier reaches into `workitems/<other-id>/`, so another WorkItem's feature is not a candidate by construction.
- Intra-tier rule unchanged: newest mtime; `feature_ambiguous` when the two newest share a timestamp.
- `_adopt_feature_directory` relocates into the WorkItem: refuses `feature_target_exists` rather than overwrite or merge, verifies both endpoints resolve inside `project_root`, `shutil.move`, refuses `feature_adopt_failed` with the source untouched on `OSError`, and returns `{from, to}` which is written to the audit as `speckit_feature_adopted`.
- Emits `feature_id`, `feature_directory`, `candidates`, `searched`, `tier`, `adopted`.

**`gate_precondition_hook`** — new `SPECKIT_GATE_KEYS` branch for `gate_spec`/`gate_plan`/`gate_tasks`/`gate_analyze`: under a WorkItem, a `featureDirectory` not starting with `workitems/<id>/specs/` refuses `feature_outside_workitem`. Skipped under the legacy binding and when the gate has no resolved artifact. Gate 7's `manifest_incomplete` branch is untouched.

**`cmd_security_review_evidence`** — candidates and the git `:(exclude)` pathspec both follow `specKit.featureDirectory`, so relocating the specs does not turn them into implementation diff.

**`validate`** — new `feature_directory_outside_workitem` finding (severity `error`, so `validate` exits 3). A **null** directory is not a finding, so a freshly initialised repository still reports `findings == []`.

> Deliberate placement: the check lives in `_feature_directory_findings`, called from the tail of `_validate_runtime_state`, which is already one of the six declared `dataclass_replace(paths, workitem=...)` sites. Adding a seventh site would have broken `test_workitem_rebinding_happens_only_at_the_declared_sites`, which the plan requires to stay byte-unchanged. The existing early returns in `_validate_runtime_state` are preserved exactly, so no existing finding changes.

**`import shutil`** added (the only new import in T04).

## Tests moved with the paths (all TP-003 category 2)

Re-derived: `grep -rn '\.specify/specs' tests/ --include=*.py` matched **17** lines before M3 and matches **1** after (`test_hooks.py:132`, the write-fence allow case, which M4 keeps and adds beside).

| File | Change |
|---|---|
| `tests/conftest.py` | The **single** edit the anti-contradiction clause permits: `Project.specs_root`, `Project.feature_dir(feature_id)`, module-level `FEATURE_ID`. `git diff -- tests/conftest.py` shows exactly those two hunks and nothing else. |
| `test_integration_01_happy_path.py` | 5 lines. `run_happy_path` now derives `feature_dir = project.feature_dir(FEATURE)` **per call**, because `test_units_workitem_runtime.py::test_two_workitems_complete_independent_runs` drives a *second* WorkItem through the same helper. A module constant failed that test — caught and fixed inside M3. |
| `test_integration_02_to_05.py` | 3 lines via a module-level `FEATURE_DIR` (the helpers there are only ever handed the fixture WorkItem). |
| `test_integration_06_to_09.py` | 7 lines, same shape. |
| `test_units_transitions.py` | `test_gate_show_substitutes_feature_id` now uses `started.feature_dir(...)` for both the state value and the expected path. |

## Verification at M3

- Syntax OK; `lint-skill` 22 PASS.
- Manual CLI smoke (subprocess) proving the new behaviour:
  - tier 2 (`<root>/specs/001-demo`) adopted into `workitems/wi-one/specs/001-demo`; source gone; **file SHA identical across the move**; exactly **1** `spec.md` under the project root afterwards; `speckit_feature_adopted` present in `audit.md`.
  - re-running with a fresh `<root>/specs/001-demo` present chooses tier 1 and reports `adopted: null` — precedence, and no second move.
  - two WorkItems each resolve to their own directory; forcing B's `specKit.featureDirectory` to A's path (a stale global feature slot) makes `gate approve --gate gate_spec` exit **1** `feature_outside_workitem`, and B's `approvals.gate_spec` stays `null`.
  - two feature directories with an identical mtime still refuse `feature_ambiguous` and list both candidates.
- **Full suite after M3: 438 passed in 497.07s, RAW_EXIT=0**, `-rsxX` printed no short-summary section.

## Reachability note for `feature_target_exists` (for M5's N6)

Because tier 1 is `workitems/<id>/specs/*` and a candidate must be a **directory**, a target that already exists *as a directory* means tier 1 was non-empty and was therefore chosen — so no move is attempted. `feature_target_exists` is reachable when the target path exists but is **not** a directory (e.g. a file named after the feature). It is a defence-in-depth non-overwrite guard (plan F4); N6 will exercise it through that case, and the handoff will record the analysis rather than claim a broader reachability.

## How to resume from here

Next is **M4** (D11): the `write_fence` carve-out in `.claude/hooks/hooks.py` plus its `FENCE_REASONS` rewrite, and the `test_hooks.py` additions.

Planned deviation to declare at M5: N2(d) asserts that `phase-execution.md` places a `feature bind` line before each Spec Kit skill invocation. That file is D12/M6 work, so **`phase-execution.md` will be edited in M5 together with the test that pins it** — the same "subject and its test move in one milestone" principle M3 used for the paths. M6 keeps the rest of D12 (`SKILL.md` prose, `security-review.md`, `README.md`, `docs/SDLE-Reference-Guide.md`, `.claude/commands/sdle-reset.md`, `CLAUDE.md`).

Reminder: `bare_project` copies `scripts/` and `.claude/hooks/` per test, so never edit either while a suite run is in flight.
