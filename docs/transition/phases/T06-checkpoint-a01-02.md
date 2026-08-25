# T06 Implementation Checkpoint — Attempt a01 / Checkpoint 02

**Phase:** T06
**Attempt:** 01
**Milestone completed:** **M2** — D5 quality model, D7 record/evidence writing, `governance assess` and `governance show`.

## Objective currently being worked

M2 is complete and green. Next objective is **M3**: D11 `required_gate_set` + `governance gates` + the risk/classification proof battery (N13–N16, N18, N20(a)). **No existing-test edit is authorised in M3.** M3 is the declared safe resume boundary; M4 is where enforcement begins.

## Completed since previous checkpoint

New in `scripts/sdle.py`, all additive, all in the governance section:

`GOVERNANCE_RECORD_VERSION`, `GOVERNANCE_INPUT_VERSIONS`, `QUALITY_RESULTS`, `GOVERNANCE_INPUT_SECTIONS`, `_input_malformed`, `requirements_sources`, `read_governance_input`, `evaluate_quality`, `evaluate_classification`, `deterministic_level`, `evaluate_risk`, `read_governance_record`, `governance_freshness`, `bind_for_governance`, `cmd_governance_assess`, `cmd_governance_show`; parser entries `governance assess --input <path>` and `governance show`.

### Declared deviation from the milestone table, and why

The plan assigns D6 (the risk engine) to **M3**, but assigns **N19 — evidence completeness** to **M2**. N19 requires the record to carry §12's risk signals, deterministic score, hard floors, final risk and uncertainty, so the record cannot be written at all without the scoring, the floors and the `max(deterministic, proposed)` rule. `deterministic_level` and `evaluate_risk` therefore landed in **M2**, one milestone early. M3 keeps D11 (`required_gate_set`, `wouldBeRequiredGates`, `governance gates`) and the N13–N16/N18/N20(a) proof battery. Both milestones remain additive and behaviour-neutral, so this moves no risk and changes no milestone's green/red character.

**Consequence a resuming agent must know:** the record written today has **no `wouldBeRequiredGates` key**. M3 adds it. If M3 is not completed, the record is still valid for E1's purposes (M4 reads `quality.result` and `requirements.digest` only).

### Decisions taken in M2

- **`governance assess` never touches `state.json` or `audit.md`.** It may run before `init`, so there is no `audit_sha` to rebaseline and no state to save. `test_assess_writes_only_the_record_and_one_evidence_file` and `test_governance_is_writable_before_state_json_exists` pin both halves. The governance facts enter the ledger at M5.
- **The record is persisted *before* the blocking refusal**, the same shape `cmd_artifact_record` already uses, so a `requirements_quality_blocked` verdict is inspectable and remediable rather than invisible.
- **One new refusal reason beyond the plan's named set: `governance_input_malformed`.** The plan names `quality_incomplete`, `quality_unknown_check`, `quality_malformed`, `quality_not_applicable_refused`, `classification_invalid`, `unknown_risk_signal` and `requirements_quality_blocked`, but names nothing for envelope problems (unreadable/not JSON/not an object/unknown or missing top-level key/unsupported `governanceInputVersion`/wrong section type/bad level string). One reason covers all of them rather than inventing several. No collision with the existing vocabulary.
- **A second new reason: `governance_workitem_required`.** `governance` is runtime-free at the group level, so `assess`/`show` bind through `bind_for_governance` → `bind_workitem`. Under the transitional legacy binding `bind_workitem` returns `workitem=None`, and writing `governance.json` there would write into `.workflow/`, which §8.9 forbids absolutely. So it refuses. A distinct reason was chosen over reusing `workitem_required` (which already collides with a `UsageError`, T03-6) or `legacy_workflow_present` (which `init` uses for a different precondition). Pinned by `test_governance_refuses_under_the_legacy_binding`.
- **`read_governance_record` raises `IntegrityError("governance_record_invalid")` on a corrupt record rather than returning `None`.** Treating corruption as absence would let a damaged file read as "not yet assessed" and be silently overwritten. This is the **only** new exit-3 path in the phase and it is a *pre-existing-corruption* path, not a new failure mode — recorded here so A14 can be judged against a stated fact rather than a claim. (A14 says "no new exit-3 path"; this is a declared divergence: an unreadable runtime file is an integrity failure everywhere else in the engine — see `legacy_state_invalid`, `index_malformed` — and returning exit 1 there would be inconsistent with the exit-code contract's own meaning.)
- `bind_for_governance` calls `bind_workitem`, **not** `dataclass_replace(..., workitem=...)`, so `test_workitem_rebinding_happens_only_at_the_declared_sites` stays byte-unchanged and still passes.

## Remaining

M3–M8 per the plan's milestone table.

## Files changed

| File | Nature |
|---|---|
| `scripts/sdle.py` | additive governance section; `import copy`; two members appended to `workitem_runtime_member_names` |
| `tests/test_units_governance.py` | **new**, now **87** collected |
| `tests/test_units_repo_config.py` | rows 1, 2, 3 only |
| `tests/test_units_workitem_resolution.py` | row 0 only |
| `docs/transition/phases/T06-checkpoint-a01-01.md`, `-02.md` | control plane |

`git diff --numstat 4a35a1c -- scripts/sdle.py tests/` (run in this context):

```
984	1	scripts/sdle.py
12	0	tests/test_units_repo_config.py
4	0	tests/test_units_workitem_resolution.py
```

Zero `D`, zero `R`. `tests/test_units_governance.py` is still untracked (`??`).

## Tests actually run

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest tests/test_units_governance.py -q -p no:cacheprovider --no-header"` | **0** | **`87 passed in 20.37s`** |
| `rtk proxy "python -m pytest <7 files> -q -p no:cacheprovider --no-header -rsxX"` | **0** | **`348 passed in 324.42s (0:05:24)`**, no short-summary section |
| `rtk proxy "python scripts/sdle.py lint-skill"` | **0** | 22 PASS / 0 FAIL (unchanged; no document was edited in M2) |

**This is a scoped run, not a full-suite figure.** The seven files were `test_units_governance.py`, `test_units_repo_config.py`, `test_units_workitem_resolution.py`, `test_units_workitem_runtime.py`, `test_units_transitions.py`, `test_integration_01_happy_path.py`, `test_lint_skill.py`. The last **full** suite figure is checkpoint 01's **`624 passed`, raw exit 0**; the next full run is scheduled at **M3**, the safe resume boundary. M2 adds only new module-level definitions and two new subcommands, and touches no function on the lifecycle path, so the scoped set is the one that could regress.

## Current failures

**None.**

## Git status / diff summary

- HEAD `4a35a1c`; nothing committed this phase.
- Working tree also carries the pre-existing out-of-scope ` M .claude/settings.local.json`.
- Rollback point remains **`475795a`**.

## Unresolved decisions

None. No blocker.

## Exact resume instruction

```
rtk proxy "python -m pytest tests/test_units_governance.py -q -p no:cacheprovider"   # expect 87 passed
rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"                   # expect 658
```

If those hold, M1 and M2 are on disk. Continue at **M3** per `docs/transition/phases/T06-plan.md`: add `required_gate_set`, write `wouldBeRequiredGates` into the record inside `cmd_governance_assess`, add `governance gates`, then the N13–N16/N18/N20(a) tests. Run the **full** suite at the end of M3 before crossing into M4.
