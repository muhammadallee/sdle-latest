# T07 Implementation Checkpoint — Attempt a01 / Checkpoint 06

**Phase:** T07
**Attempt:** 01
**Milestone completed:** **M6** — `tests/test_units_flow_model.py` in full.
**HEAD at checkpoint:** `77ca0b8` (nothing committed; all work is in the working tree)
**Rollback point:** `c0775b3`

## Objective currently being worked

M6 is complete and green. Next objective is **M7**: `flow show`,
`constants.flows`, the remaining prompt and documentation layer, ADR-004, the
dry-run disposition paragraph and `sdle-restart.md` — with `lint-skill` re-run
after **every** document edit (F12/F14).

## What M6 puts on disk

**No product file was touched.** M6 is `tests/test_units_flow_model.py` only:
**63 → 92** collected (+29). Nothing else in the working tree changed, which is
the honest claim to make about a milestone that is entirely evidence.

### The driver is table-driven, not five hand-written scripts

`drive(project, flow, stop=None)` reads the phase list out of
`constants.flow(flow).phases` and walks it through the **real CLI**, taking the
gate keys from `consts.phase_to_gate_key`. It restates no traversal: a driver
that spelled out five sequences would only prove the test and the engine were
written by the same hand. The one hand-written part is `prepare()`, the
per-phase artifact recipe, because that is the part Spec Kit would produce and
the suite never invokes Spec Kit.

Gate phases are deliberately no-ops in `prepare()` — a gate approves the
artifact the phase before it produced.

### What the 29 tests assert

| N | Tests | Substance |
|---|---|---|
| **N1–N5** | `test_a_flow_traverses_exactly_its_declared_phases` (parametrised ×5) plus one named test per flow | Each flow's driven traversal **equals its declared phase list**; final `current_phase` is `complete`, `status` `completed`, progress `18/18`, `18/18`, `16/16`, `14/14`, `10/10`; the approved gate-key set equals the flow's `gate_keys`; every gate the flow does not run is still `null`; `audit verify` reports `matches` and `chain_ok`. GREENFIELD's driven traversal is asserted **equal to `EXPECTED_TRAVERSAL`**, and `impact_analysis` appears in neither its `phase_history` nor its `audit.md`. HOTFIX's `gate_implement` reports `(2, 3)` from `gate show`, and its completion summary records `flow: "HOTFIX"`. |
| **N5** | `test_brownfield_discovery_is_greenfield_until_t08_changes_it` | States in its docstring that **the brownfield-discovery phase owns changing this**, so that later edit cannot be silent. |
| **N6** | `test_the_five_traversals_are_pairwise_distinct_except_the_declared_pair` | All ten pairs compared; the equal set is exactly `{("BROWNFIELD_DISCOVERY", "GREENFIELD")}`. Asserted on the declarations, because the parametrised test above already proves each driven traversal equals its declaration. |
| **N7(3)** | `test_the_impact_analysis_artifact_is_fingerprinted` | `artifact record` returns the file's real SHA, writes `current_artifact` / `current_artifact_sha`, and appends **exactly one** `artifact_recorded` event (counted before and after). |
| **N7(4)** | `test_the_impact_analysis_review_is_bound_to_that_exact_sha` | The review record carries `sha256`, `reviewType: impact-analysis` and the agent actor; `artifact reviews` reports `current: True`; rewriting the file leaves the record naming the SHA it reviewed and flips `current` to `False`. **Freshness is derived, never stored** — no new mechanism. |
| **N7(5)** | `test_advancing_out_of_impact_analysis_lands_on_spec_draft` ×2 | Both defect flows. |
| **N7(6)** | `test_under_greenfield_impact_analysis_is_a_forward_jump_not_unknown` | `forward_jump` with `in_flow is False`, `flow == "GREENFIELD"`, `requested_index is None`; a genuinely unknown phase still refuses `unknown_phase`. D17's two-reason split, live. |
| **N7(7)** | `test_no_gate_can_ever_be_current_at_impact_analysis` ×2 | `gate approve` and `gate reject` both refuse — `unknown_gate` for `gate_impact_analysis`, `not_at_gate` for a real gate — and `audit.md` and `state.json` are byte-identical after. |
| **N9** | `test_advancing_past_an_unapproved_gate_refuses_in_every_flow` ×5 | Drives each flow to its own first gate and refuses `gate_not_approved`; `audit.md` byte-identical. |
| **N10** | `test_a_registry_phase_outside_the_flow_is_a_forward_jump` | `design_generation` under HOTFIX. |
| **N11** | `test_approving_a_gate_a_flow_does_not_run_refuses_and_writes_nothing` | `gate_design` under HOTFIX: `not_at_gate`, both files byte-identical, the approval still `null`. |
| **N13** | `test_no_read_only_command_writes_the_flow` + `test_only_init_and_the_migration_write_the_flow_field` | A recursive SHA map of the repository is unchanged across `constants`, `governance show`, `governance gates`, `state get --field flow` and `header`; and an **AST walk** shows the set of functions assigning `state["flow"]` is exactly `{cmd_init, _mig_1_15}`. |
| **N15** | `test_a_defect_fix_run_never_grows_a_ninth_approval_key` | The `approvals` key set is re-checked **after every step** of a full DEFECT_FIX run and is always the eight pre-T07 keys; `gate_impact_analysis` never appears. |
| **N26** | `test_two_workitems_on_different_flows_advance_independently` | One WorkItem on GREENFIELD, a second on HOTFIX; driving the second leaves the first's `state.json` and `audit.md` **byte-unchanged**. |

## Two defects found by running the new tests, and how each was resolved

Both were in the *tests*, found by the first run, and both were my own
mis-modelling of an engine API rather than engine defects. Neither weakened an
assertion.

1. **`reviews.json` is `{"reviewsVersion", "reviews": [...]}`, a flat list of
   records keyed by a `path` field** — not a dict of path → entries, and the
   fields are `sha256` / `reviewType`, not `artifactSha256` / `type`. The test
   raised `TypeError: list indices must be integers`. Rewritten against the real
   shape, and **strengthened** while there: it now also drives `artifact
   reviews` and asserts the derived `current` verdict flips from `True` to
   `False` when the file is rewritten, which is the actual TP-011 property.
2. **`gate reject` requires `--reason`**, so the `reject` parametrisation was
   exiting 2 (usage) before reaching the refusal under test. The test now passes
   `--reason` for that variant, with a comment saying the extra argument is part
   of the command's shape and not part of what is asserted.

## Tests actually run in this context

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest tests/test_units_flow_model.py -q -p no:cacheprovider -rsxX"` *(first M6 run)* | **1** | `2 failed, 90 passed in 141.42s` — the two defects above |
| same, after the fixes | **0** | `92 passed in 140.66s (0:02:20)` |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **0** | **`895 passed in 1018.51s (0:16:58)`** |
| `grep -c "short test summary"` over that run | — | **0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **0** | **`895 tests collected in 0.70s`** — collected == passed |

**Suite arithmetic:** M5's 866 + 29 = **895**. `tests/test_units_flow_model.py`
collects **92**.

Runtime variance is worth recording against U7: the same suite took 922 s at
M4, 903 s at M5 and **1018 s** at M6 on the same machine. M6 adds ten full
end-to-end CLI runs, so some of that is real work; the rest is the spread U7
already documented. **Never give a full run the 2-minute default.**

## Files changed so far this phase

`git status --porcelain` in this context:

```
 M .claude/settings.local.json                  (pre-existing, OUT OF SCOPE)
 M .claude/skills/sdle/SKILL.md
 M .claude/skills/sdle/modules/gate-protocol.md
 M .claude/skills/sdle/modules/phase-execution.md
 M .claude/skills/sdle/templates/state.json
 M README.md
 M docs/SDLE-Reference-Guide.md
 M scripts/sdle.py
 M tests/conftest.py
 M tests/test_lint_skill.py
 M tests/test_units_cli.py
 M tests/test_units_governance.py
 M tests/test_units_infra.py
 M tests/test_units_repo_config.py
 M tests/test_units_speckit_binding.py
 M tests/test_units_state.py
 M tests/test_units_transitions.py
 M tests/test_units_workitem_runtime.py
?? docs/architecture/ADR-004-declarative-flow-model.md
?? docs/transition/phases/T07-checkpoint-a01-0{1..6}.md
?? tests/test_units_flow_model.py
```

`git diff --numstat -- tests/` is unchanged from M5 — ten `M`, **zero `D`, zero
`R`** — because M6's only change is inside the new, untracked
`tests/test_units_flow_model.py`.

> `docs/architecture/ADR-004-declarative-flow-model.md` was written during M6's
> suite run, while no product file could safely be edited. It is **M7's
> deliverable**, listed here only because it is already on disk.

## Current failures

**None.**

## Constraints M7 onward must not undo

Everything in checkpoints 01–05, plus:

- **`drive()` must stay table-driven.** If a future edit hard-codes a
  traversal into it, the end-to-end tests stop being evidence.
- **`test_brownfield_discovery_is_greenfield_until_t08_changes_it` is meant to
  fail later.** It is the visible-change tripwire for the brownfield work; it
  must not be softened to a subset assertion.
- **`test_a_defect_fix_run_never_grows_a_ninth_approval_key` checks after every
  step**, not just at the end. A single end-of-run check would miss a key added
  and removed mid-run.
- M7 adds `flow show` to `test_no_read_only_command_writes_the_flow`'s sweep;
  that list is the point of the test and must not shrink.
