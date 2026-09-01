# T08 Implementation Checkpoint — Attempt a01 / Checkpoint 02

**Phase:** T08
**Attempt:** 01
**Milestone:** M2 — discovery as a governed record

## Objective currently being worked

M2 of the T08 plan: `DISCOVERY_*` constants, `discovery schema`,
`read_discovery_input`, `evaluate_discovery`, `cmd_discovery_assess`,
`discovery_precondition` at `apply_advance`; conftest edit 2; tests N1–N14 and
N29–N30.

## Completed since previous checkpoint

**M1's full suite, re-run after the three mechanical fixes:**

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest -q --no-header"` | **`908 passed in 1106.85s (0:18:26)`, `RAW_EXIT=0`** |

908 = the 901 pre-T08 baseline observed in this context, plus the seven tests
M1 added (`test_the_four_other_flows_are_element_wise_unchanged` × 4
parametrisations, plus three more). M1 is green and closed.

**M2 applied.** `scripts/sdle.py` gains, in one new section placed before
`migrate-workflow`:

- `Paths.discovery_file` → `workitems/<id>/.sdle/discovery.json`, and the
  member added to `workitem_runtime_member_names`, so the bidirectional
  `.sdle/` leak detector inherits it in both directions for free.
- `DISCOVERY_PHASE`, `DISCOVERY_RECORD_VERSION`, `DISCOVERY_INPUT_VERSIONS`,
  `DISCOVERY_INPUT_SECTIONS`, `DISCOVERY_FINDING_KEYS`,
  `DISCOVERY_REQUIRED_FINDING_KEYS`, `DISCOVERY_CLASSIFICATIONS` (3),
  `DISCOVERY_CATEGORIES` (14, in §14's order), `DISCOVERY_RULES` (R-a…R-j),
  `DISCOVERY_AUDIT_EVENT`.
- `read_discovery_input` (fail-closed, mirroring `read_governance_input`),
  `_evidence_problem`, `evaluate_discovery` (two passes, because a basis may
  name a finding declared later), `read_discovery_record` (fail-closed,
  mirroring `read_governance_record`), `discovery_accepted`,
  `bind_for_discovery`, `cmd_discovery_schema`, `cmd_discovery_assess`,
  `cmd_discovery_show`, `discovery_precondition`.
- `discovery_precondition` is called from `apply_advance` **and** as a pure
  reader ahead of the first `append_audit` in `cmd_gate_approve` and
  `cmd_skip`, so a refused `advance`, approval or `skip` leaves `audit.md`
  byte-identical.
- Three new `lint-skill` checks: `discovery_is_gateless`,
  `discovery_is_declared_by_exactly_one_flow`,
  `discovery_vocabulary_is_not_restated_in_prompt_files`.

`tests/test_units_discovery.py` is new (54 tests). `tests/conftest.py` gains
**only** `Project.record_discovery` — anti-contradiction clause edit 2 — whose
category list and classification are read from the engine, never typed.

`tests/test_units_repo_config.py::test_the_runtime_member_names_are_derived_from_paths`
gained `"discovery.json"`. **That file is in the plan's "must not change"
list**; the plan's own N13 requires the leak detector to inherit
`discovery.json`, which is only possible by adding the member, which is only
possible by growing that exact-equality literal. TP-003 category 2, recorded
here and in the handoff rather than absorbed silently.

## Remaining

M3 (baseline descriptor, read-only), M4 (establish at completion), M5 (the
refusals), M6 (ADR-005 and the doc sweep).

## Files changed (cumulative, M1 + M2)

```
.claude/skills/sdle/SKILL.md
.claude/skills/sdle/modules/phase-execution.md
README.md
docs/SDLE-Reference-Guide.md
scripts/sdle.py
tests/conftest.py
tests/test_units_discovery.py          (new)
tests/test_units_flow_model.py
tests/test_lint_skill.py
tests/test_units_governance.py
tests/test_units_repo_config.py
tests/test_units_cli.py
tests/test_units_infra.py
docs/architecture/ADR-005-brownfield-discovery-and-baseline.md  (new, M6's, written early)
docs/transition/phases/T08-checkpoint-a01-01.md                 (new)
```

## Tests actually run

| Command | Result |
|---|---|
| `python scripts/sdle.py lint-skill` | exit 0, **32 PASS** (29 preserved + 3 new) |
| `pytest tests/test_units_discovery.py tests/test_units_repo_config.py tests/test_lint_skill.py` | **161 passed** |
| `pytest -q` (full, M2) | recorded in checkpoint 03 |

A complete, fully-patched **sandbox** copy of the repository (all six
milestones applied at once, under
`scratchpad/t08/sandbox/`) was used to dry-run every remaining patch before it
touched the working tree. That sandbox is where the four §11 containment-proof
conflicts below were found, before any of them could land in the repository.

## Current failures

None in the repository at this checkpoint.

The sandbox surfaced four `tests/test_units_repo_config.py` failures caused by
later milestones. One of them changed the **engine**, not the test:

- `test_no_lifecycle_command_reads_the_repository_configuration` failed because
  `cmd_gate_approve` named `paths.baseline_file` to fingerprint the descriptor
  for the audit entry. Rather than weaken the guard,
  `establish_baseline` now returns `(path, sha256)` so `cmd_gate_approve`
  never names a configuration member. **That guard therefore survives T08
  unchanged**, which is the outcome worth having.

## Git status / diff summary

Thirteen product/test files plus two new transition artifacts, and the
pre-existing untracked `.claude/settings.local.json` (out of scope). No commit
yet — the phase commits once.

## Unresolved decisions

None requiring a human. The one judgement made here — that a §14 baseline write
inside `cmd_gate_approve` supersedes three T05-era §11 containment proofs, and
that the fourth is preserved by refactoring instead — is recorded in full in the
handoff, with the reasoning and the TP-003 category for each.

## Exact resume instruction

1. Verify from disk: `python scripts/sdle.py lint-skill` must exit 0 with
   **32** checks; `rtk proxy "python -m pytest --collect-only -q"` reports
   **`970 tests collected`** here (observed, not derived);
   `tests/test_units_baseline.py` must **not** exist yet. A plain
   `python -m pytest` under the shell proxy prints `Pytest: No tests collected`
   and exits 0 — that is a false green, so always go through `rtk proxy`.
2. Apply M3: `baseline_descriptor`, `read_baseline`, `baseline_findings`,
   `baseline_status`, `baseline_state`, `cmd_baseline_show`,
   `cmd_baseline_validate`, the `validate` wiring, the `baseline` parser group
   and its `RUNTIME_FREE_COMMANDS` entry. **No writer at M3.** Then conftest
   edit 1 (`Project.establish_baseline`), `tests/test_units_baseline.py`
   (N15–N22), and the M3 growth of `CONFIG_REFERENCE_SITES`.
3. `read_baseline` must be fail-closed. A `return` inside one of its exception
   handlers is the defect N15 exists to catch.
