# T04 checkpoint a01-02 — M2 (capability detection and `feature bind`)

**Phase:** T04 · **Attempt:** 1 · **Milestone:** M2 of 7 · **Status:** CLOSED GREEN.

Predecessor: `T04-checkpoint-a01-01.md` (M1, closed green — 438 passed). Rollback point for the phase is still `beb28f2`; nothing is committed yet.

## What M2 landed (D4 + D5 + D7, purely additive)

**`scripts/sdle.py`, new section "Spec Kit capability detection (contract §10)"**

- `SPECKIT_REQUIRED_CAPABILITIES = ("SPECIFY_INIT_DIR", "SPECIFY_FEATURE_DIRECTORY")`, `SPECKIT_PROBE_SUFFIXES`, `SPECKIT_SCRIPTS_RELATIVE = ".specify/scripts"`.
- `repo_relative(paths, target)` — repo-relative POSIX helper.
- `detect_speckit_capabilities(paths)` — probes the *target project's own* `.specify/scripts/` recursively for `.py`/`.sh`/`.ps1` files, reads each at most once with `errors="replace"`, marks a capability supported iff its literal name occurs, records the first matching file as `evidence`, and returns `speckit_present`, `scripts_present`, `probed_root`, `capabilities`, `missing`. Files are visited in sorted order so `evidence` is deterministic; an `OSError` on one file is skipped and leaves the closed default.
- `SPECKIT_MISSING_MESSAGE` — the one `speckit_missing` message, now shared by `cmd_preflight` and `cmd_feature_bind` (invariant 7).
- `speckit_env(paths, state)` — ordered `[{"name":…, "value":…}]`, never a shell string. `SPECIFY_INIT_DIR` always; `SPECIFY_FEATURE_DIRECTORY` and `SPECIFY_FEATURE` omitted when null.
- `cmd_feature_bind` — refuses `speckit_missing`, then `speckit_capability_missing` (with `data.missing`, `data.probed_root`, `data.capabilities`), then `feature_directory_unresolved` under `--require-feature`. Pure: reads state and disk, writes nothing. Reads state only when `state_file` exists, so it is usable before `init` and still fails closed.
- `cmd_feature_capabilities` — reports `detect_speckit_capabilities`, always exit 0.

**`Paths`** gained `speckit_specs_root` / `speckit_specs_relative` (both `None` under the legacy binding).

**`cmd_preflight`** gained **additive** `data` keys `speckit_capabilities` and `speckit_capability_problems` from the same function; `speckit_present` now reads off the same detection result. `problems`, the refusal reasons and every message are unchanged.

**Parser**: `feature bind [--require-feature]` and `feature capabilities` added beside the existing `feature resolve`. `RUNTIME_FREE_COMMANDS` untouched — that is what keeps "WorkItem resolution precedes Spec Kit" structural.

### Declared deviation from the milestone table

The plan assigns D1 (the two `Paths` members) to M3, but D5's `data.workitem_specs_root` needs `speckit_specs_relative`, so both properties landed in M2. They are pure derivations with no behaviour of their own; nothing else in M2 consumes them.

## Verification at M2

- Syntax: `ast.parse(scripts/sdle.py)` OK.
- `python scripts/sdle.py lint-skill` → 22 PASS.
- Manual CLI smoke against a scratch project (subprocess, real argv):
  - no WorkItem → `feature bind` exit 1 `workitem_required` (refused by `bind_workitem`, before the handler);
  - `.specify/` present, no `.specify/scripts/` → `feature capabilities` exit 0 reporting `scripts_present: false` and both capabilities unsupported; `feature bind` exit 1 `speckit_capability_missing` with `missing == ["SPECIFY_INIT_DIR", "SPECIFY_FEATURE_DIRECTORY"]`;
  - stub `.specify/scripts/python/common.py` naming both → `feature bind` exit 0, `evidence == ".specify/scripts/python/common.py"`, `workitem_specs_root == "workitems/wi-one/specs"`, `env` = `SPECIFY_INIT_DIR` only;
  - `--require-feature` before `feature resolve` → exit 1 `feature_directory_unresolved`; after → exit 0 with all three env entries.
  - `preflight` → exit 0, `speckit_capability_problems: []`, `speckit_capabilities` naming both variables.
- **Full suite after M2: `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → 438 passed in 504.40s, RAW_EXIT=0**, no short-summary section.

## How to resume from here

Next is **M3** (D1 + D6 + D9 + D10) *together with* the 17 test path-rebinding lines and the single permitted `conftest.py` edit:

1. `cmd_feature_resolve` → tiered discovery (`workitems/<id>/specs/*`, then `<root>/specs/*`, then `.specify/specs/*`), baseline intra-tier rule preserved, relocation into the WorkItem with `feature_target_exists` / `feature_adopt_failed` refusals and a `speckit_feature_adopted` audit entry. Legacy binding keeps baseline behaviour exactly.
2. `gate_precondition_hook` → `feature_outside_workitem` for `gate_spec`/`gate_plan`/`gate_tasks`/`gate_analyze`.
3. `cmd_security_review_evidence` → candidates and the `:(exclude)` pathspec follow `featureDirectory`.
4. Tests: `.specify/specs/{FEATURE}` → a WorkItem-scoped `FEATURE_DIR` in the three integration files (5 + 3 + 7 lines re-derived by grep), the two `test_units_transitions.py` gate-show lines, and `conftest.py`'s single permitted edit (`Project.specs_root`, `Project.feature_dir`, module-level `FEATURE_ID`).

Reminder: never edit `scripts/sdle.py` while a suite run is in flight — `bare_project` copies `scripts/` per test.
