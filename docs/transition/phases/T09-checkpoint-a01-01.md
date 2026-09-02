# T09 Implementation Checkpoint — Attempt a01 / Checkpoint 01

**Phase:** T09
**Attempt:** 01
**Milestone:** M1 — the policy data, with "nothing routes yet" as its proof
**Written at:** before starting M2

## Objective currently being worked

M1 of `docs/transition/phases/T09-plan.md`: `GOVERNANCE_POLICY_BUILTIN` gains
five risk signals, the `authentication_or_authorization` floor is edited in
place from MEDIUM to HIGH, six floors are appended so §15's nine are all
present, and `required_gates_by_risk["MEDIUM"]` gains `gate_design`. Plan tests
N7–N10 and X-table row X5.

**M1 changes no routing.** Nothing consults the gate map yet; `apply_advance`
is untouched, `governance gates` still reports `advisory: true`, and every gate
still requires an approval.

## Baseline established before any edit (this is my own observation, not inherited)

| Fact | Value | Command |
|---|---|---|
| HEAD at start | `ad08d4b` | `git log --oneline -8` |
| Working tree at start | one ` M .claude/settings.local.json` (out of scope, untouched) | `git status --short` |
| Full suite at HEAD | **`1025 passed in 1666.61s (0:27:46)`, RAW EXIT 0** | `rtk proxy "python -m pytest -q -p no:cacheprovider"` redirected to a file, `$?` read with no pipe |
| `lint-skill` at HEAD | **32** checks, `failed: []`, exit 0 | `python scripts/sdle.py lint-skill` |
| `validate.py` at HEAD | exit 0, `TRANSITION_VALID: complete=9/12 next=T09` | `python tools/transition/validate.py` |
| Flows at HEAD | GREENFIELD 19/8, BROWNFIELD_DISCOVERY 20/8, ITERATIVE 17/7, DEFECT_FIX 15/6, HOTFIX 11/3; 16 migration rows | `python scripts/sdle.py constants` |

The planner recorded the suite pass count as `UNKNOWN` (plan U1/E7). It is now
OBSERVED: **1025 passed, raw exit 0**. That is the figure every later count in
this attempt is measured against.

## Completed since previous checkpoint

First checkpoint of the attempt.

1. **`scripts/sdle.py` — `GOVERNANCE_POLICY_BUILTIN` only.**
   - `risk_signals` 12 -> **17**: appended `destructive_or_irreversible_migration` 4,
     `regulatory_or_compliance` 4, `production_security_boundary` 4,
     `credential_or_key_exposure` 5, `catastrophic_blast_radius` 5.
   - `hard_floors` 6 -> **12**. The first six rules keep their order and their
     positions; the only in-place edit is
     `authentication_or_authorization` MEDIUM -> **HIGH**. Six rules appended.
     Position stability is load-bearing:
     `test_units_governance.py::lowering_input` indexes `hard_floors[0]`.
   - `required_gates_by_risk["MEDIUM"]` gains `gate_design`.
   - `risk_thresholds`, `required_gates_always` and `required_gates_by_type`
     are byte-identical.
2. **`tests/test_units_governance.py`** — X5, docstring only, on
   `test_a_floor_raises_the_level_the_score_alone_would_not_reach`. The
   docstring said auth sits at MEDIUM; it no longer does. No assertion changed.
3. **`tests/test_units_gate_policy.py`** — new file, M1 section only: N7 (nine
   §15 floors through the CLI, with the nine-row expectation table written out
   so a removed floor fails rather than shrinking the parametrisation), N8
   (auth alone is HIGH), N9 (no floor, weight or threshold below its `e1cf341`
   value, prior values as literals), N10 (an override restating the old MEDIUM
   auth floor is refused `policy_weakens_baseline`), plus A1's shape assertion
   and the two "signals deliberately not widened" guards.

## Remaining

M2 (requirement model, read-only), M3 (enforcement), M4 (inherited findings),
M5 (prompts, docs, ADR-006). Patch scripts for M2, M3 and M4 and the M2/M3 test
bodies are already drafted in the scratchpad but **not applied**:

```
C:\Users\Ali\AppData\Local\Temp\claude\D--Learning-AI-sdle-git-repo-sdle-latest\
  c7a269b2-11ef-4692-bef4-6b959bf8d34b\scratchpad\
    m1_patch.py  (APPLIED)   m2_patch.py  m2_tests.py  m3_patch.py
    m3_tests.py  m4_patch.py
```

A fresh implementer should treat those as drafts and re-derive them against
disk, not trust them.

## Files changed

| Path | Change |
|---|---|
| `scripts/sdle.py` | `GOVERNANCE_POLICY_BUILTIN` only (+28/-2 across the whole file) |
| `tests/test_units_governance.py` | one docstring (X5) |
| `tests/test_units_gate_policy.py` | **new**, M1 section |

`git diff --stat` also lists ` M .claude/settings.local.json`, which was
already modified at HEAD and is explicitly out of scope. I have not touched it.

## Tests actually run

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest tests/test_units_gate_policy.py tests/test_units_governance.py -q -p no:cacheprovider"` | **`212 passed in 126.88s`, RAW EXIT 0** |
| `python scripts/sdle.py lint-skill` | **32 checks, `failed: []`**, exit 0 |
| `python scripts/sdle.py governance policy` | 17 signals, 12 floors, `MEDIUM: [gate_tasks, gate_design]` |
| Full suite after M1 | **IN FLIGHT** at the time of writing — see "Exact resume instruction" |

## Current failures

None observed. The full-suite run for M1 was still in flight when this
checkpoint was written; its result is recorded in checkpoint 02.

## Git status / diff summary

- HEAD: `ad08d4b` (unchanged — nothing committed yet this attempt)
- Working tree: `scripts/sdle.py`, `tests/test_units_governance.py` modified;
  `tests/test_units_gate_policy.py` untracked; `.claude/settings.local.json`
  pre-existing and untouched.
- Rollback: `git checkout e1cf341 -- scripts/sdle.py` restores the T08 file.

## Unresolved decisions

**One plan-table omission, recorded here rather than blocked on.** The plan's
X table lists three tests asserting `governance gates` reports
`advisory is True`. There are **four**. The fourth is
`tests/test_units_governance.py::test_the_classification_flag_no_longer_claims_to_be_advisory`,
whose body ends `assert project.ok("governance", "gates").data["advisory"] is True`.
Verified with `rtk proxy "grep -rn 'advisory' tests/ --include=*.py"`.

It is the same TP-003 **category 2** change as the three rows the plan does
list (X2, X4, X6) and needs no decision — the phase deliberately removes the
field. I am treating it as an X-table row **X13** and will name it explicitly
in the handoff so the verifier can see the plan's table was short by one, not
that I edited a test outside the sanctioned set. Not a material architecture,
contract or baseline decision, so not a blocker.

No other unresolved decision. No `T09-blocker.md`.

## Exact resume instruction

1. `cd D:/Learning/AI/sdle-git-repo/sdle-latest`; confirm HEAD is `ad08d4b`.
2. Verify M1 is on disk, not assumed:
   `python scripts/sdle.py governance policy` must report **17** signals and
   **12** hard floors, and `required_gates_by_risk.MEDIUM` must be
   `["gate_tasks", "gate_design"]`. `ls tests/test_units_gate_policy.py`.
3. Read
   `C:\...\scratchpad\m1_suite.txt` for the M1 full-suite result. If it is
   absent or has no `RAW_EXIT=` line, **re-run the full suite** rather than
   assuming: `rtk proxy "python -m pytest -q -p no:cacheprovider" > <file> 2>&1`
   then `echo $?` with no pipe. Expected: 1025 baseline + the M1 tests added.
4. If green, start M2. **M2 changes no routing either** — `apply_advance` is
   not touched until M3, so the end of M2 is the plan's declared safe resume
   boundary.
5. Tooling traps that have produced false results in this migration: plain
   `python -m pytest` under the rtk hook prints `Pytest: No tests collected`
   and exits 0 (false green) — always `rtk proxy`; a plain `grep -rn` has
   produced a false negative on a real line — reproduce negatives with
   `rtk proxy "grep -rnE ..."`; `sdle.py constants` and `lint-skill` nest their
   payload under `data`; the tree is CRLF and `git show` is LF.
