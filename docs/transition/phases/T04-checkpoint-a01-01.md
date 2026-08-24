# T04 checkpoint a01-01 — M1 (schema change, paths byte-identical)

**Phase:** T04 · **Attempt:** 1 · **Milestone:** M1 of 7 · **Status at write time:** M1 code + tests applied, `lint-skill` green, targeted tests green, full suite running.

Rollback point for the phase: `beb28f2`. HEAD at start: `fe856d1`. Nothing committed yet.

## Baseline re-derived in this context (before any edit)

| Figure | Value | Command |
|---|---|---|
| Full suite at `fe856d1` | **438 passed in 501.05s, RAW_EXIT=0**, `-rsxX` printed **no** short-summary section | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` |
| `lint-skill` at `fe856d1` | RAW_EXIT 0, **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 14 migration rows` | `python scripts/sdle.py lint-skill` (streams separated; `grep -c PASS` = 22, `grep -c FAIL` = 0) |
| `validate.py` | `TRANSITION_VALID: complete=4/12 next=T04`, RAW_EXIT 0 | `python tools/transition/validate.py` |
| Working tree at start | only `M .claude/settings.local.json` | `git status --porcelain` |

## What M1 landed

D2 + D3 + D8 from the plan, with **resolved artifact paths byte-identical to baseline**.

**`scripts/sdle.py`**
- `CURRENT_VERSION = "1.15"`.
- New section *Spec Kit context (contract §10)*: `SPECKIT_REF_KEYS`, `speckit_ref(state)` (defaulted, never `KeyError`), `speckit_set(state, **values)` (single writer, canonical key order, refuses an unknown field name).
- `_mig_1_14` + `MIGRATIONS` row `("1.14", "1.15", _mig_1_14)` → 15 tuples.
- `resolve_artifact_path`: **`legacy_prefix` deleted** (NB-1 discharged), `paths` is now a required positional, `{workitem_runtime}` substituted from `paths.runtime_relative`, `{speckit_feature_directory}` from `speckit_ref(state)["featureDirectory"]`, `{current_feature_id}` placeholder gone.
- `cmd_feature_resolve` writes `specKit` via `speckit_set` and emits an additive `feature_directory` key. **M1 keeps `featureDirectory` at `.specify/specs/<id>` — M3 moves it.**
- `header` Feature-ID line, `cmd_security_review_evidence` and the `feature resolve` parser help all read through the accessor.

**Constants/docs (version sites only at M1)**: `templates/state.json` (`specKit` in, `current_feature_id` out, 1.15), SKILL.md frontmatter + heading + `ARTIFACT_OWNERSHIP` + 15th `VERSION_MIGRATION` row, README title + new `**v1.15**` history row **above** v1.14, Reference-Guide header.

**Tests (all TP-003 category 2)**: `test_units_state.py` (4 version lines), `test_lint_skill.py` (1 README title string), `test_units_transitions.py` (skip-reason label, the `at(...)` feature field, completion-summary version), `test_units_workitem_runtime.py` (template version + test name, migrate steps, migrate `to`, `execution.json` `sdleVersion`, and the migrate-workflow field list where `current_feature_id` became `specKit`).

## Verification at M1

- `python scripts/sdle.py lint-skill` → **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 15 migration rows`, `version_string_consistent: all four locations report v1.15`, `migration_covers_every_state_field: every field has a migration row`.
- `rtk proxy "grep -n legacy_prefix scripts/sdle.py"` → **no output, exit 1**. NB-1 discharged.
- Targeted: `test_units_state.py test_units_transitions.py test_lint_skill.py test_units_workitem_runtime.py` → **123 passed, RAW_EXIT=0**.
- Full suite after M1: `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → **438 passed in 497.44s, RAW_EXIT=0**, no short-summary section. Equal to baseline: M1 changed the schema without moving a single resolved path.

## Plan divergence found and declared at M1

The plan's *Existing tests affected* table says only `test_units_workitem_runtime.py` carries a version assertion, and M1's row says "only the four feature-field lines and the `1.14`→`1.15` assertion change". The repository has **nine** version-assertion lines across five files (re-derived with `grep -n '1\.14' tests/`): `test_units_state.py` ×4, `test_lint_skill.py` ×1, `test_units_transitions.py` ×1, `test_units_workitem_runtime.py` ×5 (incl. a test *name* containing `1_14`). All were updated as category 2. No test was weakened, skipped or deleted; one test was **renamed** (`test_the_shipped_template_is_1_14_...` → `..._is_1_15_...`), body unchanged apart from the version literal.

## Known conflict inside the plan (to resolve at M6)

- **A6 vs A16.** A6 requires `grep -rn 'current_feature_id' scripts/ .claude/ README.md docs/SDLE-Reference-Guide.md` to match only the two historical `VERSION_MIGRATION` rows. But `.claude/skills/sdle/modules/gate-protocol.md` line with *"substitute `current_feature_id` if needed"* also matches, and A16 requires that file to be **byte-unchanged**. A16 (containment) will be honoured; A6 will be reported as met-except-that-line, with the conflict declared.

## How to resume from here

1. `git status --porcelain` should show the 9 product files above plus the out-of-scope `.claude/settings.local.json`.
2. Confirm M1 is intact: `python scripts/sdle.py lint-skill` → 22/22 with `15 migration rows` and `v1.15`.
3. Next milestone is **M2** (D4 + D5 + D7): `SPECKIT_REQUIRED_CAPABILITIES`, `detect_speckit_capabilities`, `cmd_feature_bind`, `cmd_feature_capabilities`, parser rows under the existing `feature` group, additive `speckit_capabilities` / `speckit_capability_problems` keys in `cmd_preflight`. Purely additive.
4. Do **not** edit `scripts/sdle.py` while a suite run is in flight: `bare_project` copies `scripts/` per test, so a mid-run edit reaches later tests.
