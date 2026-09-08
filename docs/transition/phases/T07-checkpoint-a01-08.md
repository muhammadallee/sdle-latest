# T07 Implementation Checkpoint — Attempt a01 / Checkpoint 08

**Phase:** T07
**Attempt:** 01
**Milestone completed:** **M8** — full suite, `lint-skill`, `validate.py`, the
must-not-change `git diff --exit-code`, the write-fence probe (F7), and the
A1–A26 acceptance matrix.
**HEAD at checkpoint:** `77ca0b8` (nothing committed; all work is in the working tree)
**Rollback point:** `c0775b3`

## Objective currently being worked

M8 is complete and green. The remaining work is `T07-handoff-a01.md` and the
`progress.md` row → `IMPLEMENTED`. **No product file changes in M8** — it is
entirely evidence.

## The four gate commands

| Command | Raw exit | Result |
|---|---:|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **0** | **`901 passed in 1026.22s (0:17:06)`** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **0** | **`901 tests collected in 0.52s`** — collected == passed |
| `grep -c "short test summary"` over the captured run | 1 (no match) | **0 occurrences** — zero skips, xfails, errors |
| `rtk proxy "python scripts/sdle.py --project-root . lint-skill"` | **0** | **29 checks, 29 PASS, 0 FAIL, `"failed": []`**; `Parsed 20 phases, 8 gates, 16 migration rows`; `all four locations report v1.16` |
| `rtk proxy "python tools/transition/validate.py"` | **0** | `TRANSITION_VALID: complete=7/12 next=T07` |
| `git diff --exit-code 7dba4b6 -- <must-not-change list>` | **0** | zero bytes of output |
| `git diff --exit-code 77ca0b8 -- <same list>` | **0** | zero bytes of output |
| `git diff --exit-code 77ca0b8 -- docs/transition/` | **0** | zero bytes — no verifier or contract artifact touched |

**A caught trap, recorded because it nearly produced a false claim.** The first
full run was launched in the background with `… ; echo "RAW EXIT $?" >> file`.
A `grep -n "RAW EXIT"` run immediately after the `901 passed` line appeared
found **nothing** — the append had not yet flushed. Re-read after the task
completion notification, the file's line 15 is `RAW EXIT 0`. Had I written the
handoff from the first grep I would have had to record the exit as unobserved.
The rule that saved it is the plain one: read `$?` from the same file the run
wrote, after the run has actually ended.

## Suite arithmetic — the +110 is accounted for exactly

Baseline **791** (the plan's figure at `7dba4b6`), head **901**. Per-file
`--collect-only`, run in this context against both trees (the baseline tree
reconstructed with `git archive 7dba4b6 | tar -x` into the scratchpad):

| File | Base | Head | Δ |
|---|---:|---:|---:|
| `tests/test_units_flow_model.py` | 0 (does not exist) | **98** | +98 |
| `tests/test_lint_skill.py` | 17 | **28** | +11 |
| `tests/test_units_governance.py` | 180 | **181** | +1 |
| everything else | — | — | 0 |

`98 + 11 + 1 = 110`; `791 + 110 = 901`. No other file's count moved, which is
the mechanical statement of "additive only, plus the one governance rewrite".

## Acceptance matrix — every figure re-derived in this context

| # | Verdict | Evidence produced here |
|---|---|---|
| **A1** | PASS | `901 passed in 1026.22s`, RAW EXIT **0**; `--collect-only` **901**; `short test summary` count **0**; the +110 accounted for above |
| **A2** | PASS | 29/29, exit 0, `"failed": []`, `20 phases, 8 gates, 16 migration rows`, `v1.16` |
| **A3** | PASS | `validate.py` raw exit **0** |
| **A4** | PASS | `git diff --exit-code` over the full must-not-change list, against **both** `7dba4b6` and `77ca0b8`, exit 0 and zero bytes — including `tests/test_integration_01_happy_path.py`, `modules/security-review.md`, `.claude/hooks/`, all nine transcripts and `docs/transition/` |
| **A5** | PASS | **P1** `GREENFIELD_V1_PHASES == EXPECTED_TRAVERSAL` → `True`, both length **19**, imported live from the untouched integration module. **P3** the pre-T07 `PHASE_SEQUENCE` parsed straight out of `git show 7dba4b6:.claude/skills/sdle/SKILL.md` → 19 rows, **element-wise equal** to `constants.flows["GREENFIELD"]`, first mismatch `None`. **P4** `_mig_1_15` read in full: sets `DEFAULT_FLOW` (= `GREENFIELD`) unconditionally when the field is missing or blank, and mentions the governance record only to say it deliberately does not consult it. **P2** the golden literal is in `test_units_flow_model.py` and passes in the run above. |
| **A6** | PASS | covered by A4; the file also passes inside the 901 |
| **A7** | PASS | registry **20**; flow lengths `{BROWNFIELD_DISCOVERY: 19, DEFECT_FIX: 15, GREENFIELD: 19, HOTFIX: 11, ITERATIVE: 17}`; **no flow equals the registry**; a regex over the live `### FLOW_PHASES` block finds **no** `GREENFIELD` row key |
| **A8** | PASS **with the declared correction** | entries / non-terminal / gates, computed from `constants` and `phase_to_gate_key`: `GREENFIELD 19/18/8`, `BROWNFIELD_DISCOVERY 19/18/8`, `ITERATIVE 17/16/7`, `DEFECT_FIX 15/**14/6**`, `HOTFIX 11/10/3`. The plan's `14/5` for DEFECT_FIX is wrong and its own phase list proves it (checkpoint 03). Pairwise equality set is exactly `[('BROWNFIELD_DISCOVERY','GREENFIELD')]`. |
| **A9** | PASS | registry index **1** (position 2, 1-based); flows `['DEFECT_FIX','HOTFIX']`; absent from `phase_to_gate_key`, `artifact_ownership` and `gate_to_execution_phase`; template `approvals` = the **eight** pre-T07 keys; the execution block's `feature bind` count **0** and `featureDirectory` count **0**; `artifact record` / `artifact review` behaviour pinned by N7(3)/N7(4) in the run above |
| **A10** | PASS | the three `flow_mismatch` tests in the 901, each asserting a byte-identical `audit.md`, a byte-identical recursive SHA map and `audit verify` exit 0 |
| **A11** | PASS | `required_gate_set` callers are exactly `['cmd_governance_assess','cmd_governance_gates']` (AST); the two named phase-movement tests are inside A4's byte-identity |
| **A12** | PASS | AST: `governance_precondition` callers `['apply_advance','cmd_gate_approve','cmd_skip']`; `apply_advance` callers `['cmd_advance','cmd_gate_approve','cmd_skip']`; **`cmd_init` in neither**. `flow_precondition`'s callers are the same three, so the new refusal added no new caller. |
| **A13** | PASS | AST extract-and-compare against `7dba4b6` over all **15** names → `none — all 15 byte-identical` |
| **A14** | PASS | see A5-P4; the chain and idempotency are pinned by `test_migrate_walks_the_whole_chain_from_1_0` and `test_migrate_is_idempotent`, both in the 901 |
| **A15** | PASS **with the declared divergence** | `set(HOTFIX) - {impact_analysis} == set(MANDATORY_FLOW_PHASES)` → `True`; every flow ⊇ mandatory → `True`; `len(HOTFIX) <= len(flow)` for every flow → `True`; `set(HOTFIX) - {impact_analysis} <= set(flow)` for every flow → `True`. Floor is **10** phases. The plan's literal "subset-minimum" clause is false as written (checkpoint 03) and is replaced by those two exact assertions. |
| **A16** | PASS | `### PROGRESS_MAP` block compared to `git show 7dba4b6:` — **identical** after normalising the working tree's CRLF (the whole of SKILL.md is CRLF in the working tree and LF in the index; that is pre-existing and `git diff --numstat` shows only the intended line changes). **19** rows. `### PHASE_TO_GATE_KEY` likewise identical. Both are additionally lint-checked by `progress_map_and_gate_numbers_are_the_derived_greenfield_views`. |
| **A17** | PASS | AST reader set for `consts.next_phase` is exactly `['cmd_constants','load_constants','run_sync_checks']` |
| **A18** | PASS | baseline `lint-skill` in a `git archive 7dba4b6` scratch tree → **22** checks; head → **29**; `comm` over the two name lists → **7 added, 0 removed** |
| **A19** | PASS | AST writers of `state["flow"]` are exactly `['_mig_1_15','cmd_init']`; no `flow_sub.add_parser("set"/"select")` anywhere; the read-only sweep test (`constants`, `flow show`, `governance show`, `governance gates`, `state get --field flow`, `header`) is in the 901 |
| **A20** | PASS | `test_two_workitems_on_different_flows_advance_independently`, in the 901 |
| **A21** | PASS | `git diff --name-status 7dba4b6 -- tests/` = **ten `M`, zero `D`, zero `R`**; `conftest.py`'s diff is the one classification line plus six comment lines; `test_lint_skill.py` has **no** `-def` line (11 added functions, three removed lines all inside firing-test fixture literals); `test_integration_01_happy_path.py` absent from the list entirely |
| **A22** | PASS | quoted verbatim below |
| **A23** | PASS | all nine transcripts inside A4's byte-identity; `impact_analysis` occurrence count **0** in every one of the nine; `docs/dry-runs/README.md` carries the disposition (+6/−0) |
| **A24** | PASS | write-fence probe below |
| **A25** | PASS | no `.sdle/baseline*` string anywhere in `sdle.py`; `cmd_governance_gates` still contains `"advisory": True`; `BROWNFIELD_DISCOVERY == GREENFIELD` → `True` and its test names T08 as the owner of changing it; `git status` shows **no new file under `.claude/`** — no product subagent or skill added; `cmd_migrate_workflow` is in A13's byte-identical set |
| **A26** | **NOT_RUN** | host Python is **3.13.0**. Python 3.11 **NOT_RUN**; CI **NOT_RUN / UNKNOWN**. No outcome predicted. |

### A22 — the grep's actual output, quoted, not summarised

```
tests/test_units_infra.py:49:@pytest.mark.skipif(SH is None, reason="POSIX sh not available")
```

Exactly one hit, pre-existing, and it did not fire in the run above (the
captured output has no `short test summary` section). Re-derived twice, because
the first attempt produced a **false negative**: a plain `grep -rn` (which the
`rtk` hook rewrites) returned nothing at all. `rtk proxy "grep -rnE …"` and an
independent Python `re` walk over `tests/**/*.py` both return the single line
above. **A tool that silently returns nothing is worse than one that errors**;
the Python walk is the citable one.

### A24/F7 — the write-fence probe, driven directly

`.claude/hooks/hooks.py write-fence` invoked as its own process, payload on
stdin, `CLAUDE_PROJECT_DIR` set to the repository:

| Path | Verdict |
|---|---|
| `reviews/impact-analysis-2026-08-31-1430.md` | **permit** (no output) |
| `reviews/security-review-2026-08-31-1430.md` | **permit** (no output) — the precedent the path was chosen from |
| `workitems/todo-api/.sdle/state.json` | **deny**, `"permissionDecision": "deny"` |
| `.workflow/state.json` | **deny**, `"permissionDecision": "deny"` |

`.claude/hooks/` is byte-identical to `7dba4b6` (A4), so this is the shipped
fence, unmodified, permitting the new artifact and still denying both engine-owned
trees.

## Files changed in M8

**None.** M8 produced no product edit. `git status --porcelain` is what
checkpoint 07 recorded, plus this file, the handoff and the `progress.md` row.

## Current failures

**None.**

## What is NOT done, and is deliberately not mine

- **Nothing is committed.** HEAD is still `77ca0b8` and the entire phase lives
  in the working tree. The assignment named the handoff and the `progress.md`
  row as the deliverables and did not ask for a commit, and the standing rule
  is to commit only when asked. The orchestrator holds that step.
- `.claude/settings.local.json` is modified and **out of scope**; it was
  already modified before this phase began and no T07 work touched it.
