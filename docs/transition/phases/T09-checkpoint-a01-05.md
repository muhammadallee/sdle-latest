# T09 Implementation Checkpoint — Attempt a01 / Checkpoint 05

**Phase:** T09
**Attempt:** 01
**Milestone:** M5 — prompt layer, documentation, ADR-006, tests N27–N31
**Written at:** after the final full suite, `lint-skill` and `validate.py`

This attempt was **resumed** after an API session limit killed the previous
implementer mid-M5 (§24.6 interruption, not a verification FAIL — the attempt
number is unchanged). M1–M4 were on disk and were verified against the
repository here rather than trusted from checkpoint 04's narrative.

## Objective currently being worked

M5, the last milestone: `SKILL.md`, `modules/gate-protocol.md`,
`.claude/commands/sdle-approve.md`, `README.md`,
`docs/SDLE-Reference-Guide.md`, `docs/architecture/ADR-006-*`, and tests
N27–N31. Then the acceptance matrix and the handoff.

## Completed since previous checkpoint

1. **Verified M1–M4 on disk before touching anything.** `lint-skill` 33
   checks, `failed: []`, exit 0. `governance policy` reports 17 signals, 12
   floors and the `required_gates_by_risk` A1 names. `gate_requirements`,
   `gate_requirements_for_state`, `cmd_gate_omit`, `GATE_OMITTED_DECISION` and
   `BASELINED_GATE_DECISIONS` all present.

2. **Applied `scratchpad/t09_m5_docs.py`** after a dry run that printed each
   anchor's occurrence count — all thirteen were unique. No line-ending churn
   (`git diff --stat` shows only the intended lines).

3. **Applied a second documentation pass I derived myself**
   (`scratchpad/t09_m5_docs2.py`), for five statements T09 made untrue that the
   staged draft did not reach. Each was found by re-reading the shipped engine,
   not by trusting a narrative:
   * the Reference Guide still described the record as holding "the gate set
     that classification and level *would* require" — the keys are now
     `requiredGates` + `omittableGates`;
   * its glossary defined a **Gate** as always *requiring* a human decision;
   * §9's "three responses are recognized" omitted `omit`;
   * its role table claimed the reviewer holds "sole authority … at every
     gate", which `gate omit` qualifies — the T08 NB-3 failure mode exactly;
   * `gate-protocol.md`'s illustrative completion summary still showed
     `"all_gates_approved": true` as a literal, where
     `write_completion_summary` now derives it.

4. **Corrected an arithmetic error in ADR-006 against the shipped engine.**
   The ADR said §15's nine floors break down as "Five map onto a signal the
   policy already had; four did not" and that "Four new signals were added".
   The engine shipped **five** new signals (12 → 17) and reuses **four**
   existing ones. The plan's own D6 *table* agrees with the engine; only its
   prose sentence, which the ADR inherited, was wrong. Corrected to four/five.
   Re-verified that ADR-006 still names none of the 22 policy identifiers.

5. **Tests N27–N31 appended** to `tests/test_units_gate_policy.py`, with
   `import subprocess` added as checkpoint 04 predicted (verified, not
   assumed). Three defects in the staged draft were found by running it and
   fixed:
   * `docs/dry-runs/*.md` is **ten** files, not nine — the nine numbered
     transcripts plus that directory's own README. The count guard is now on
     the nine and every file in the directory is still compared.
   * `.claude/agents/` **exists**: it holds the four `sdle-transition-*`
     migration control-plane agents. The plan's scope exclusion names them as
     scaffolding, so the assertion is now that no *product* subagent sits
     beside them. Same for `.claude/skills/apply-sdle-transition`.
   * ADR-006's sentences hard-wrap, so a substring spanning a line break never
     matched. The assertions now run over whitespace-normalised text.

6. **Fixed a real defect in M4's new lint check.** The single suite failure the
   orchestrator handed me — `test_runtime_free_commands_need_no_workitem`
   `[lint-skill]`, reason `lint_failed`, failed
   `['repo_config_defaults_match_documentation']` — **did not clear when M5's
   documentation edits landed**, so I investigated rather than relaxing the
   rule. The cause is not documentation drift: `bare_project` is a temporary
   project with a copied skill root and *no* `README.md`, so the check examined
   zero blocks and fired its own non-vacuity guard. `lint-skill` is a
   RUNTIME_FREE command and must answer in any project.

   The guard is **kept**, not weakened. What changed is the question it asks:
   a document that is *present* and carries no `configVersion` block still
   fails (that is the drift D15 exists to catch, still pinned by
   `test_deleting_the_documented_block_fires_rather_than_passing_vacuously`);
   a document that is *absent* is skipped, which is exactly what
   `_check_doc_phase_tables` beside it already does. A new test,
   `test_a_project_with_no_repository_documentation_still_lints`, pins the
   second half.

## Remaining

Nothing in M5. Remaining deliverables are the handoff and the progress row,
being written now.

## Files changed

| Path | Change | Milestone |
|---|---|---|
| `scripts/sdle.py` | M1 policy data, M2 requirement model, M3 enforcement, M4 fail-closed reader + lint check, **M5 the absent-document branch of that lint check** | M1–M5 |
| `.claude/skills/sdle/SKILL.md` | Governance section: risk routes gate requirements; ask the engine; `gate omit`; two new refusal reasons | M5 |
| `.claude/skills/sdle/modules/gate-protocol.md` | Step 5 requirement lookup; new **Step 6b**; derived `all_gates_approved` | M5 |
| `.claude/commands/sdle-approve.md` | Offer the omit alternative rather than approving on the user's behalf | M5 |
| `README.md` | D16 (M4); `governance gates` row rewritten, `gate omit` row, risk-adaptive paragraph | M4, M5 |
| `docs/SDLE-Reference-Guide.md` | Disposition vocabulary, `gate omit`, two revalidations, terminal rule, record shape, glossary, §9 decision set, role authority | M5 |
| `docs/architecture/ADR-006-risk-adaptive-gate-policy.md` | **new**, 304 lines; §4 count corrected | M5 |
| `tests/test_units_gate_policy.py` | **new**, 1533 lines (M1–M3 + N27–N31) | M1–M3, M5 |
| `tests/test_lint_skill.py` | X12 block (M4) + the absent-document test (M5) | M4, M5 |
| `tests/test_units_governance.py`, `test_units_baseline.py`, `test_units_workitem_resolution.py`, `test_units_artifact_review.py`, `test_units_repo_config.py` | X-table rows | M1–M4 |

`tests/conftest.py`, `.claude/skills/sdle/templates/state.json`,
`.claude/hooks/`, `.claude/settings.json`, `.gitignore`,
`tests/test_integration_01_happy_path.py` and `docs/dry-runs/` are all
byte-identical to `e1cf341` (`git diff --exit-code` = 0 over that set).

## Tests actually run

Every pytest run through `rtk proxy`, redirected to a file, raw exit read with
no pipe.

| Command | Result |
|---|---|
| `pytest tests/test_units_gate_policy.py -k 'n27 or … '` (first run of the staged block) | **3 failed, 13 passed** — the three draft defects above |
| the same, after the transcript/ADR fixes | **1 failed, 15 passed** — `apply-sdle-transition` |
| the same, after the skills fix | **`16 passed`**, RAW_EXIT 0 |
| `pytest tests/test_units_gate_policy.py tests/test_lint_skill.py` | **`401 passed in 160.04s`**, RAW_EXIT 0 |
| `pytest tests/test_units_workitem_runtime.py` (before the lint fix) | **1 failed, 44 passed** — the inherited failure, reproduced |
| `pytest tests/test_lint_skill.py tests/test_units_workitem_runtime.py tests/test_units_repo_config.py` (after) | **`159 passed in 151.40s`**, RAW_EXIT 0 |
| `pytest --collect-only -q` | **1402 tests collected in 0.77s** |
| **Full suite** `pytest -q -p no:cacheprovider --no-header` | **`1402 passed in 1409.25s (0:23:29)`, RAW_EXIT=0** |
| `python scripts/sdle.py lint-skill` | **33 checks, `failed: []`**, exit 0; `all four locations report v1.16` |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=9/12 next=T09`, exit 0 |
| Live probe (temporary file, run then deleted) | **4 passed** — see below |
| Python 3.11 | **NOT_RUN** |
| CI | **NOT_RUN** |

Collected (1402) equals passed (1402); the summary line names no skip, xfail or
error category.

### The live probe

A temporary `tests/test_zz_t09_live_probe.py` drove §15's exit criterion
through the real CLI in this context, then was **deleted** (`git status`
confirms it is gone). Printed output:

```
PROBE design omit ->   1 gate_required ['risk:HIGH']
PROBE advance past design -> 1 gate_not_approved
PROBE security omit -> 1 gate_required ['risk:HIGH', 'terminal_gate']
PROBE approve (no review) -> 1 review_missing
PROBE approve (wrong gate) -> 1 not_at_gate
PROBE skip (not failed) -> 1 not_failed
PROBE audit verify -> 0 True
PROBE low omit design -> 0 omitted_by_policy LOW
PROBE low omit security -> 1 gate_required
PROBE omittable at LOW -> ['gate_analyze', 'gate_design', 'gate_tasks']
PROBE approve omittable -> 0
```

Each refusal was asserted to leave `audit.md` byte-identical, including at
`gate approve` and `skip`.

## Current failures

**None.** Full suite RAW_EXIT 0, `lint-skill` exit 0, `validate.py` exit 0.

## Git status / diff summary

- HEAD `ad08d4b5a4dc1303a9c48a9dc8af0ad76f8c55a8`; **nothing committed this
  attempt**.
- Modified: `scripts/sdle.py` (+677/−52), `README.md` (+15/−2),
  `docs/SDLE-Reference-Guide.md` (+24/−7), `.claude/skills/sdle/SKILL.md`
  (+9/−1), `.claude/skills/sdle/modules/gate-protocol.md` (+32/−2),
  `.claude/commands/sdle-approve.md` (+7/−0), six test files.
- Untracked: `tests/test_units_gate_policy.py`,
  `docs/architecture/ADR-006-risk-adaptive-gate-policy.md`, the five
  checkpoints, the handoff.
- `.claude/settings.local.json` was already modified at HEAD, is out of scope
  and was not touched.
- Rollback: `git checkout e1cf341 -- scripts/sdle.py README.md docs/SDLE-Reference-Guide.md .claude/`
  and delete the two new files.

## Unresolved decisions

None requiring a human. No `T09-blocker.md`.

## Exact resume instruction

The phase is implemented; nothing is outstanding. A fresh agent picking this up
should:

1. `cd D:/Learning/AI/sdle-git-repo/sdle-latest`; confirm HEAD `ad08d4b`.
2. Read `docs/transition/phases/T09-handoff-a01.md` — it carries the
   acceptance matrix with the command behind each row.
3. Re-derive rather than inherit: `python scripts/sdle.py lint-skill`
   (33 / `failed: []`), `python tools/transition/validate.py` (exit 0), and
   `rtk proxy "python -m pytest -q -p no:cacheprovider --no-header"` redirected
   to a file with `$?` read unpiped (expect 1402 passed, ~23 minutes — the Bash
   tool caps a foreground command at 600s, so background it).
4. Tooling traps that produced false results earlier in this migration: plain
   `python -m pytest` under the `rtk` hook prints "No tests collected" and exits
   0 (false green); a plain `grep -rn` gave a false negative on a real line in
   `scripts/sdle.py` in this very context — reproduce negatives with
   `rtk proxy "grep -rnE …"` or a Python walk; `lint-skill` and `constants`
   nest their payload under `data`; the tree is CRLF and `git show` is LF; a
   `PostToolUse` secrets tripwire fires on a substring of this phase's own
   name (masked `sk-a****`) — false positive, no credential.
