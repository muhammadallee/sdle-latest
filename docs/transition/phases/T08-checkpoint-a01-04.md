# T08 Implementation Checkpoint — Attempt a01 / Checkpoint 04

**Phase:** T08
**Attempt:** 01
**Milestone:** M4 — establish the baseline at completion

**This is the plan's declared safe resume boundary.** M1–M4 are additive: a new
phase, new commands, a new descriptor and a new completion-time write. Nothing
that was previously permitted is refused yet. M5 is where enforcement begins.

## Objective currently being worked

M4 of the T08 plan (D6): write `.sdle/baseline.json` at the single completion
choke point — the `is_final` branch of `cmd_gate_approve` — first in that
branch, before `write_completion_summary` and before the `workflow_complete`
audit entry, with one `baseline_established` audit entry appended after
`workflow_complete`. Tests N23, N27, N28.

## Completed since previous checkpoint

### Engine (`scripts/sdle.py`)

- **`establish_baseline(paths, state, consts, stamp)`** — the **only** writer,
  placed between `baseline_state` and `cmd_baseline_show`. Returns
  `(relative_path, sha256)` or `(None, None)`.
  - Returns `(None, None)` when `paths.workitem is None`. §14's second required
    fact is the *producing WorkItem*; under the transitional legacy `.workflow/`
    binding there is none, so a descriptor written there would be invalid the
    moment it was written. Same skip, and the same reason, as
    `governance_precondition` and `discovery_precondition`.
  - Returns `(None, None)` when the bound flow is not in
    `BASELINE_ESTABLISHING_FLOWS`. §14's convergence sentence names greenfield
    completion and brownfield discovery completion and nothing else.
  - Never refuses and never raises on missing inputs: `baseline_descriptor` is
    total by construction and the call lands after `gate_approved` is already in
    the append-only ledger.
  - Returning the `(path, sha)` pair rather than the `Paths` member is what
    keeps `cmd_gate_approve` out of the §11 repository-configuration reference
    set — see the test note below.
- **`cmd_gate_approve`** — the `is_final` branch now reads: establish the
  baseline, write the completion summary, append `workflow_complete`, then
  append `BASELINE_AUDIT_EVENT` (`baseline_established`) when a baseline was
  actually established. `gate approve`'s emitted payload gains a `baseline`
  key, `null` for every non-final approval.

No other engine function changed. `lint-skill` still reports 32 checks.

### Tests

`tests/test_units_baseline.py` gains five tests (N23 × 2, N27, N28, and a
source-level one-writer/one-caller pin), plus a local `second_repository`
helper and three cross-module imports (`run_happy_path`, `review_for_gate`,
`drive`) of exactly the kind six test modules already use.

- `test_n23_both_establishing_flows_produce_the_same_baseline_shape` — drives
  **GREENFIELD in one repository and BROWNFIELD_DISCOVERY in a second**, both
  through the real CLI to `complete`. Both establish a baseline, both report
  `VALID` with no findings, the two descriptors have the same required key set
  and the same `references` / `discovery` key sets, and the only difference is
  the discovery-derived content: `NOT_REQUIRED` with a `null` record versus
  `PERFORMED` with a real record path and a 64-character SHA. That is the
  convergence invariant driven rather than asserted.
- `test_n23_only_the_two_declared_flows_establish_a_baseline` — HOTFIX
  completes and writes nothing; `baseline show` reports `ABSENT`.
- `test_n27_the_baseline_write_cannot_block_completion` — drives GREENFIELD to
  `gate_security`, **deletes the constitution and the design document**, then
  approves the final gate. Exit 0, `current_phase == "complete"`, a completion
  summary is written, and the descriptor carries `null` / `[]` / `[]`. This is
  failure mode F4 exercised at its sharpest.
- `test_n28_completion_emits_exactly_one_baseline_established_entry` — exactly
  one `baseline_established` and one `workflow_complete` in the ledger, the
  baseline entry **after** `workflow_complete`, `audit verify` reporting
  `chain_ok`, and the completion summary's field set unchanged.
- `test_the_baseline_write_has_exactly_one_call_site` — asserted on the parsed
  AST: `establish_baseline` has exactly one caller (`cmd_gate_approve`), and
  exactly one function in the engine both names `baseline_file` and calls
  `write_atomic` (`establish_baseline`). A second writer is the governance
  bypass ADR-004 §3 refused for `flow set`.

## Existing tests changed at M4 — TP-003 categories

Both are **category 2, deliberately superseded behavior**. Neither is deleted,
skipped, xfailed or weakened; both got *stronger* assertions.

1. `tests/test_units_repo_config.py` — `CONFIG_REFERENCE_SITES` gains
   `establish_baseline`. The set is asserted by exact equality, so a new
   function reaching the §11 boundary cannot be silent. The T08 comment block
   already in that set (written at M3) named `establish_baseline` in advance;
   this is the entry itself. **`cmd_gate_approve` is deliberately still absent**
   — it reaches the boundary through `establish_baseline` and names no
   configuration member, which is what keeps
   `test_no_lifecycle_command_reads_the_repository_configuration` passing
   **unchanged**.
2. `tests/test_units_repo_config.py::test_the_configuration_boundary_changes_no_lifecycle_behaviour`
   — clause 4. T05 could assert "the lifecycle never touched the boundary"
   because nothing in the lifecycle wrote it. §14 changes that on purpose, so
   continuing to assert it would be asserting a fiction. The clause is
   **restated exactly, not dropped**: the run adds exactly one boundary entry,
   that entry is `baseline.json`, every pre-existing entry is byte-identical
   afterwards, nothing is removed, and the *unconfigured* repository gets the
   same single file. A second new file, or any mutation of `config.json`, still
   fails here. Clauses 1–3 (identical traversal, identical ordered audit event
   sequence, identical scrubbed state) are untouched and still pass.

No other existing test needed a change at M4.

## Files changed (cumulative, M1–M4)

```
.claude/skills/sdle/SKILL.md
.claude/skills/sdle/modules/phase-execution.md
README.md
docs/SDLE-Reference-Guide.md
scripts/sdle.py
tests/conftest.py
tests/test_units_baseline.py                (new)
tests/test_units_discovery.py               (new)
tests/test_units_flow_model.py
tests/test_lint_skill.py
tests/test_units_governance.py
tests/test_units_repo_config.py
tests/test_units_cli.py
tests/test_units_infra.py
tests/test_units_workitem_resolution.py
docs/architecture/ADR-005-brownfield-discovery-and-baseline.md  (new; M6's, written early — content still to be verified against what shipped)
docs/transition/phases/T08-checkpoint-a01-01.md .. -04.md
```

`.claude/settings.local.json` is modified but is **out of scope and untouched
by this phase**.

## Tests actually run in this context

Every figure below was produced by a command run here, redirected to a file,
with `$?` read with no pipe between.

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` (before M4) | `1001 tests collected`, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_baseline.py -q -p no:cacheprovider"` | **36 passed in 53.08s**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_repo_config.py tests/test_integration_01_happy_path.py tests/test_units_transitions.py -q -p no:cacheprovider"` | **104 passed in 150.23s**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_workitem_runtime.py tests/test_integration_02_to_05.py tests/test_integration_06_to_09.py tests/test_units_flow_model.py -q -p no:cacheprovider"` | **230 passed in 399.86s**, RAW_EXIT 0 |
| `python scripts/sdle.py lint-skill` | exit 0, **32 checks, 0 failing**, `all four locations report v1.16`, `21 phases, 8 gates, 16 migration rows` |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=8/12 next=T08`, exit 0 |
| **`rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (full)** | **`1006 passed in 1157.19s (0:19:17)`, RAW_EXIT 0**, no short summary lines (no skips, xfails or xpasses) |

1006 = the 1001 collected before M4 plus the five M4 tests. Python 3.13 on
Windows; **Python 3.11 and CI are `NOT_RUN`** — the branch is local-only.

## Current failures

None. The suite is green at the end of M4.

## Unresolved decisions

None requiring a human. Two judgements are recorded above with their reasoning
and TP-003 category: the legacy-binding skip in `establish_baseline`, and the
restatement of the §11 boundary clause 4.

## Git status / diff summary

Fifteen product/test files plus the new transition artifacts and ADR-005. No
commit yet — the phase commits once, at the end.

## Exact resume instruction

M4 is complete and the tree is at end-of-M4 state, which is the plan's declared
**safe resume boundary**. A fresh implementer resumes at **M5**:

1. Verify from disk first. `python scripts/sdle.py lint-skill` must exit 0 with
   **32** checks. `rtk proxy "python -m pytest --collect-only -q"` must report
   **1006**. `grep -n "def establish_baseline" scripts/sdle.py` must hit; `grep
   -n "def baseline_precondition\|rediscovery" scripts/sdle.py` must show only
   the two prose mentions of "rediscovery" in `baseline_findings`' and
   `read_baseline`'s docstrings — M5 has not started if there is no
   `baseline_precondition`. A plain `python -m pytest` under the shell proxy
   prints `Pytest: No tests collected` and exits 0; that is a false green, so
   always go through `rtk proxy`, redirect to a file, and read `$?` with no
   pipe.
2. Apply M5 per D8: `classification.rediscovery` in `evaluate_classification`
   (third permitted key, boolean, default `false`, refused
   `classification_invalid` with any flow other than `BROWNFIELD_DISCOVERY`);
   `baseline_precondition` as a **pure reader** called from `cmd_init`
   **before** `paths.workflow.mkdir(...)`, implementing R1 `baseline_present`
   and R2 `baseline_required`. `DEFECT_FIX` and `HOTFIX` are deliberately not
   covered — do not extend R2 to them.
3. `baseline_precondition` must be added to `CONFIG_REFERENCE_SITES`, and
   `cmd_init` must stay out of it: pass the flow and the rediscovery flag in as
   plain values so `cmd_init` never names a configuration member.
4. `bind()` in `tests/test_units_flow_model.py` and the flow loop in
   `tests/test_units_governance.py` both `init` ITERATIVE and will hit R2. Give
   each a baseline **only when the repository has none**, so a test that
   deliberately establishes one first is not overwritten.
5. Two exact-equality classification assertions gain `"rediscovery": False` —
   `tests/test_units_governance.py` at the `record["classification"] == {...}`
   sites.
6. Tests N24, N25, N26, N34. N24 is §14's exit criterion and must be driven
   through the real CLI, not asserted.
7. If a red window is unavoidable, confine it inside M5 and declare it in
   checkpoint 05.
