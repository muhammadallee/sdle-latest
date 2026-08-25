# T06 Implementation Checkpoint — Attempt a01 / Checkpoint 03

**Phase:** T06
**Attempt:** 01
**Milestone completed:** **M3** — D11 `required_gate_set`, `wouldBeRequiredGates` in the record, `governance gates`, and the risk/classification proof battery.

> **THIS IS THE PLAN'S DECLARED SAFE RESUME BOUNDARY.** M1–M3 are additive, green and behaviour-neutral: nothing on the lifecycle path reads any of it, and the traversal has not moved. **M4 is where enforcement begins and where the first deliberate red window opens.** A fresh agent resuming here may start at M4 without re-deriving M1–M3 — after verifying against disk, not against this text.

## Objective currently being worked

M3 is complete and green. Next objective is **M4**: D8 enforcement E1 inside `apply_advance` (`governance_missing`, `governance_blocked`, `governance_stale`), anti-contradiction **row 5** (`tests/conftest.py`), **row 6a** (one `record_governance()` call in `run_happy_path`), and the derived set of inserted setup calls. New tests N10–N12.

**The suite will go red the moment E1 lands and must be green again by the end of M4. That red window must never span a milestone boundary** — an agent interrupted mid-M4 must finish or revert M4, not build on a red tree.

## Completed since previous checkpoint

- `required_gate_set(classification, final_level, policy) -> list[str]` — pure, sorted, over the three flat policy keys `required_gates_always` / `required_gates_by_risk` / `required_gates_by_type`.
- `cmd_governance_assess` now writes `"wouldBeRequiredGates"` into the record (the key checkpoint 02 flagged as missing).
- `cmd_governance_gates` + the `governance gates` parser entry. Advisory; the emitted payload carries `"advisory": true` and a note stating that every registered gate still runs unconditionally.
- Tests N13, N14, N15, N16, N18, N20(a)(b)(c), plus the `governance gates` purity and refusal cases.

### The N16 property test is the phase's central proof

`test_claude_can_never_lower_a_deterministic_floor` runs the **full** cross-product — all `2**12 = 4096` subsets of the built-in signal vocabulary × all four proposed levels, **16 384 cases** — asserting `index(final) >= index(deterministic)`, `final == max(deterministic, proposed)` and that `loweringAttempted` is exactly the lowering predicate. It runs against the pure `sdle.evaluate_risk` so the whole cross-product is affordable; the CLI path is proved separately by `test_a_lowering_attempt_is_recorded_and_ineffective` (A12's hand-crafted `LOW` proposal against a `CRITICAL` floor → `finalLevel: CRITICAL`, `loweringAttempted: true`, exit 0).

That property proves nothing unless `evaluate_risk` is the only producer, so `test_only_evaluate_risk_produces_a_final_level` asserts by AST that exactly one function **builds** a `"finalLevel"` dict key (`evaluate_risk`) and exactly two only **read** it (`cmd_governance_assess`, `cmd_governance_gates`). Two earlier drafts of that test were wrong and were fixed rather than relaxed: the first did not distinguish building a key from subscripting it, the second double-counted `evaluate_risk` because `ast.walk` yields the `Dict` and its key `Constant` separately.

## Remaining

M4–M8 per the plan's milestone table.

## Files changed

| File | Nature |
|---|---|
| `scripts/sdle.py` | additive governance section; `import copy`; two members appended to `workitem_runtime_member_names` |
| `tests/test_units_governance.py` | **new**, **158** collected |
| `tests/test_units_repo_config.py` | anti-contradiction rows 1, 2, 3 |
| `tests/test_units_workitem_resolution.py` | anti-contradiction row 0 |
| `docs/transition/phases/T06-checkpoint-a01-01..03.md` | control plane |

`git diff --numstat 4a35a1c -- scripts/sdle.py tests/` (run in this context):

```
1045	1	scripts/sdle.py
12	0	tests/test_units_repo_config.py
4	0	tests/test_units_workitem_resolution.py
```

Zero `D`, zero `R`; `tests/test_units_governance.py` untracked (`??`). **No lifecycle function has been modified yet** — `apply_advance`, `cmd_gate_approve`, `_approve_drift` and `append_audit` are still byte-identical to `475795a`.

## Tests actually run

| Command | Raw exit | Result |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **0** | **`729 passed in 656.05s (0:10:56)`**; `-rsxX` produced **no** short-summary section |
| `rtk proxy "python -m pytest tests/test_units_governance.py -q -p no:cacheprovider --no-header"` | **0** | `158 passed in 47.88s` |
| `rtk proxy "python scripts/sdle.py lint-skill"` | **0** | 22 PASS / 0 FAIL (no document edited yet) |

**Suite arithmetic, re-derived:** baseline **569** + **158** (`tests/test_units_governance.py`) + **2** (`tests/test_units_repo_config.py` 69 → 71, from the *derived* runtime-member parametrisation growing by `governance.json` and `reviews.json`) = **729**. No other per-file count has moved.

## Current failures

**None.**

## Git status / diff summary

- HEAD `4a35a1c`; nothing committed this phase.
- Pre-existing out-of-scope ` M .claude/settings.local.json` untouched.
- Rollback point remains **`475795a`**.

## Unresolved decisions

None. No blocker.

## Exact resume instruction

Verify against disk before trusting any of the above:

```
rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"                 # expect 729
rtk proxy "python -m pytest tests/test_units_governance.py -q -p no:cacheprovider" # expect 158 passed
rtk proxy "git diff --exit-code 475795a -- .claude/ .github/ tools/ .gitignore"    # expect exit 0
```

Then implement **M4** per `docs/transition/phases/T06-plan.md` §D8:

1. Insert E1 into **`apply_advance`** — not `cmd_advance`; F5 explains why putting it in `cmd_advance` would leave `gate approve` and `skip` unguarded. Skip when `paths.workitem is None` (the transitional legacy binding, a declared bounded residual T11 removes).
2. `tests/conftest.py`: add `Project.record_governance()` **and one call to it in the `started` fixture only** — row 5 permits nothing else in that file. `project`, `bare_project`, `git_project` and `started_git` must keep their exact bodies.
3. `run_happy_path`: one `record_governance()` call before `init` (row 6a).
4. Run the suite, derive the *exact* set of other tests needing an inserted setup call, list them file-by-file in the handoff with TP-003 category 2. **Insert setup calls only — never relax, remove, skip or xfail an assertion.** If an assertion needs editing, stop: that is a plan defect or a design error in the enforcement placement (F4).
