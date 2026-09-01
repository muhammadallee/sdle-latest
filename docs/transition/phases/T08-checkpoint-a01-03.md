# T08 Implementation Checkpoint — Attempt a01 / Checkpoint 03

**Phase:** T08
**Attempt:** 01 (unchanged — checkpoint 02's context was terminated by an API
session limit, which is a §24.6 interruption, not a verification FAIL)
**Milestone:** M3 — the baseline descriptor, read-only

> **Written retrospectively, from disk.** M3 was applied by the previous
> implementer context, which was killed before it could write this checkpoint.
> Everything below was re-derived by commands run in *this* context; nothing is
> copied from checkpoint 02's prose or from the orchestrator's summary. Where a
> figure could not be re-derived here (M3's own targeted test run), it is
> recorded as such rather than invented.

## Objective of the milestone

`baseline_descriptor`, `read_baseline`, `baseline_findings`, `baseline_status`,
`baseline_state`, `cmd_baseline_show`, `cmd_baseline_validate`, the `validate`
wiring, the `baseline` parser group. **No writer at M3**, so no flow behaviour
changes. Tests N15–N22, `conftest` edit 1.

## State verified from disk in this context

| Claim | Evidence (command run here) |
|---|---|
| HEAD is `9c10eb5`; nothing about T08 is committed | `git log --oneline -5`, `git status --short` |
| Registry is 21 entries, `discovery` at index 1 (position 2) | `python scripts/sdle.py constants` → `phase_sequence[:4] == ['requirements_check', 'discovery', 'impact_analysis', 'constitution_draft']` |
| Flow shapes, entries **including** `complete`: GREENFIELD 19, BROWNFIELD_DISCOVERY 20, ITERATIVE 17, DEFECT_FIX 15, HOTFIX 11 — acceptance A1 | same dump |
| `lint-skill` exit 0, **32** checks, none failing; `version_string_consistent` message is `all four locations report v1.16`; `tables_wellformed` reports `21 phases, 8 gates, 16 migration rows` | `python scripts/sdle.py lint-skill`, JSON parsed |
| M3's five plan-named symbols all exist | `grep -n` in `scripts/sdle.py`: `baseline_descriptor` (def), `read_baseline` (def), `baseline_findings` (def), `cmd_baseline_show` (def), `cmd_baseline_validate` (def) |
| `tests/test_units_baseline.py` and `tests/test_units_discovery.py` exist and are untracked | `git status --short` |
| `tests/conftest.py` contains **exactly** the two permitted additions and nothing else | `git diff tests/conftest.py` → `+66 -0`, two new methods `establish_baseline` and `record_discovery`, no line removed or modified |
| Collected count before M4 | `rtk proxy "python -m pytest --collect-only -q"` → **1001 tests collected**, raw exit 0 |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=8/12 next=T08`, exit 0 |

`read_baseline` was read in full and is fail-closed as D7 requires: absent →
`None`; `OSError`/`JSONDecodeError`/`ValueError` → `IntegrityError("baseline_invalid")`;
non-object → the same; unsupported `baselineVersion` → the same. There is no
`return` statement inside any of its exception handlers, and
`test_n15_the_baseline_reader_never_swallows_and_defaults` asserts that on the
parsed AST while asserting the *contrast* that `read_repo_config`'s handlers do
return. T05 NB-4 is therefore not inherited and `read_repo_config` is untouched.

## Not re-derived here

M3's own targeted test run and M2's full-suite figure were reported by the
terminated context and are **NOT_RUN in this one**. They are superseded by this
context's own full-suite observation recorded in checkpoint 04, which covers
M1–M4 together at a later tree state.

## Remaining at this point

M4 (establish the baseline at completion), M5 (the refusals), M6 (ADR-005
verification and the documentation sweep).
