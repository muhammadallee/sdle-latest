# T04 Implementation Checkpoint — Attempt a01 / Checkpoint 06

**Phase:** T04
**Attempt:** 1
**Milestone:** M6 of 7 — D12, the prompt and documentation layer.
**Status:** CLOSED GREEN.

> Context note (§24.6). The previous implementer of this same attempt was terminated by an API
> session limit between M5 and M6. That is an interruption, **not** a verification FAIL, so the
> attempt number stays `a01` and checkpoints 01–05 remain valid evidence. Everything below was
> re-derived on disk in a fresh context; nothing is copied from the earlier checkpoints' figures.

## Objective currently being worked

Finish D12 (M6) and hand over to M7.

## State re-derived on entry (fresh context, before any edit)

| Figure | Value | Command actually run |
|---|---|---|
| HEAD | `fe856d1` "Plan T04 Spec Kit WorkItem binding"; nothing about T04 committed | `git log --oneline -3` |
| Full suite at the M5 tree | **`498 passed in 950.63s (0:15:50)`, RAW_EXIT=0**, `-rsxX` produced **no** short-summary section | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"`, unpiped, redirected to a file, raw exit read from `$?` |
| `lint-skill` on entry | RAW_EXIT 0 | `python scripts/sdle.py lint-skill` |
| `legacy_prefix` in `scripts/sdle.py` | **no match, exit 1** — NB-1 still discharged (A4) | `rtk proxy "grep -n legacy_prefix scripts/sdle.py"` |
| `tests/` name-status vs `beb28f2` | 9 `M`, **zero `D`**; single untracked file `tests/test_units_speckit_binding.py` (A17) | `git diff --name-status beb28f2 -- tests/`; `git ls-files --others --exclude-standard tests/` |
| `conftest.py` diff | exactly the two hunks the anti-contradiction clause permits (`specs_root`, `feature_dir`, module-level `FEATURE_ID`) and nothing else | `git diff -- tests/conftest.py` |

The 15m50s wall time is longer than earlier checkpoints' ~8m because read-only evidence greps ran
concurrently with the suite. The run itself is unpiped through `rtk proxy` and its raw exit is 0.

## Completed since previous checkpoint

**M6 was found already largely applied** by the interrupted predecessor. The orchestrator's brief
described several files as "partial" based on a raw `current_feature_id` grep count; checking the
actual diffs on disk showed those remaining matches are the *intended* ones. Per-file audit of
D12 against `git diff`:

| D12 subject | D12 requires | State found | Action taken |
|---|---|---|---|
| `modules/phase-execution.md` | bind lines, Phase 4 paragraph, 12 path substitutions | done in M5 (declared divergence) | none |
| `SKILL.md` | version ×2, `ARTIFACT_OWNERSHIP`, 15th `VERSION_MIGRATION` row | all three present in the diff | none |
| `modules/security-review.md` | the three artifact lines | done | none |
| `README.md` | version ×2, history row **above** v1.14, `current_feature_id` state-field row → `specKit` | all three present | none |
| `docs/SDLE-Reference-Guide.md` | header version, four artifact-table rows, two prose mentions, state-field row, the one example path, new revision row | all six present (plus Appendix B's `(v1.14)` → `(v1.15)` heading) | none |
| `.claude/commands/sdle-reset.md` | the one line enumerating what a reset clears | done — `workitems/<id>/specs/` added to the "survives" list | none |
| `CLAUDE.md` | one sentence: WorkItem-specific SpecKit artifacts are WorkItem-scoped, its scaffolding is not | **untouched** | **edited — the only M6 change** |

The three surviving `current_feature_id` matches in `SKILL.md` are the 1.0→1.1 and 1.1→1.2
historical rows (A6 permits these; they describe the past and must not be rewritten) plus the new
1.14→1.15 row, which must name the field it replaces and must contain the literal `specKit` for
`migration_covers_every_state_field`. The one match in `README.md` and the one in the Reference
Guide are the new v1.15 history / 1.4 revision rows, which likewise describe the replacement.

### The single M6 edit

`CLAUDE.md`, one sentence inserted as its own paragraph immediately after the "Runtime state is
WorkItem-scoped" paragraph and before "Which WorkItem is active is resolved, never guessed":

> SpecKit's WorkItem-specific artifacts are scoped the same way — a WorkItem's feature directory is
> `workitems/<workitem-id>/specs/<feature-id>/`, discovered and moved there by `feature resolve`
> and recorded in `state.specKit.featureDirectory` — while genuinely repository-wide SpecKit
> scaffolding, `.specify/` including `memory/constitution.md`, stays at the repository root.

Purely additive and purely descriptive. It states no rule, weakens no invariant, and changes no
instruction; it records where an artifact now lives. Flagged in the handoff because `CLAUDE.md`
also carries the agent-facing project instructions, so a human should eyeball it.

`CLAUDE.md` is read by no test and by no engine code path (`grep -rn 'CLAUDE.md' tests/
scripts/sdle.py` matches only two prose comments referencing invariants 6 and 8), so this edit
cannot move a test result.

## Remaining

**M7 only:** full suite, `lint-skill`, `validate.py`, the acceptance matrix A1–A21,
`T04-handoff-a01.md`, `progress.md` → `IMPLEMENTED`, and checkpoint 07.

## Files changed

M6 changed exactly one file: `CLAUDE.md`. The full T04 working-tree set is unchanged otherwise:
`scripts/sdle.py`, `.claude/hooks/hooks.py`, `.claude/skills/sdle/{SKILL.md,templates/state.json,
modules/phase-execution.md,modules/security-review.md}`, `.claude/commands/sdle-reset.md`,
`README.md`, `docs/SDLE-Reference-Guide.md`, `CLAUDE.md`, nine `tests/*.py` and the new
`tests/test_units_speckit_binding.py`. `.claude/settings.local.json` is out of scope and untouched.

## Tests actually run

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (entry state, pre-M6) | `498 passed in 950.63s (0:15:50)`, RAW_EXIT=0, no short-summary section |
| `python scripts/sdle.py lint-skill` — re-run immediately after the `CLAUDE.md` edit, as D12/M6 requires after **each** document edit | RAW_EXIT 0; stderr `grep -c '^\[PASS\]'` = **22**, `grep -c '^\[FAIL\]'` = **0**; JSON `data.failed == []`; `tables_wellformed: Parsed 19 phases, 8 gates, 15 migration rows`; `version_string_consistent: all four locations report v1.15`; `migration_covers_every_state_field: every field has a migration row` |

No pytest run was made after the `CLAUDE.md` edit at M6; M7's full suite covers it.

## Current failures

None.

## Git status / diff summary

HEAD `fe856d1`, branch `transition/workitem-v1`, **nothing committed**. Working tree carries the
T04 product/test edits, checkpoints 01–06, the new test file, and the out-of-scope
`.claude/settings.local.json`. Rollback point for the phase remains `beb28f2`.

`git diff --exit-code beb28f2 -- scripts/sdle.sh scripts/sdle.ps1 scripts/README.md
.claude/settings.json .github/ docs/dry-runs/ docs/architecture/ requirements/ .gitignore
.claude/skills/sdle/modules/gate-protocol.md` → **exit 0** (A16). `.claude/commands/` shows exactly
one `M` row, `sdle-reset.md`.

## Unresolved decisions

None new. Carried forward for the handoff, unchanged in substance:

1. `modules/phase-execution.md` moved from M6 into M5 (checkpoints 03 and 05) because N2(d) is its
   test and the plan's F9 rule is that a subject and its test land in the same milestone.
2. The two `Paths` members (D1) landed in M2 rather than M3 (checkpoint 02), because D5's
   `data.workitem_specs_root` consumes `speckit_specs_relative`.
3. The write-fence carve-out is anchored `(?:^|/)workitems/[^/]+/specs/` rather than the plan's
   `^workitems/…`, because the hook's `relative()` is best-effort (checkpoint 04).
4. Nine version-assertion test lines across five files were updated, not the one the plan's table
   named (checkpoint 01); one test was renamed, body otherwise unchanged.
5. A6 vs A16 conflict: `modules/gate-protocol.md` still says "substitute `current_feature_id` if
   needed" and A16 requires that file byte-unchanged (checkpoint 01).
6. **T02 residual, deliberately NOT fixed** (checkpoint 05): `phase-execution.md` still names
   `.workflow/audit.md`, `.workflow/implementation-manifest.md` and
   `.workflow/completion-summary.json` in Phases 15, 16, 18 and the generic "BEFORE executing any
   phase" block. Real staleness, not T04's — D12 does not list those lines. For the orchestrator to
   assign an owning phase.

## Exact resume instruction

1. `git status --porcelain` — expect the file set above, nothing committed, HEAD `fe856d1`.
2. Confirm M6: `rtk proxy "grep -n 'WorkItem-specific artifacts' CLAUDE.md"` matches once;
   `python scripts/sdle.py lint-skill` → RAW_EXIT 0, 22 PASS / 0 FAIL.
3. Run M7 in this order: `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (600000 ms
   timeout, unpiped, raw exit read directly — a bare `python -m pytest` is a false green),
   then `--collect-only -q`, then `lint-skill`, then `python tools/transition/validate.py`.
4. Fill the acceptance matrix A1–A21 from commands run in that context, write
   `T04-handoff-a01.md` from `docs/transition/templates/phase-handoff.md`, set `progress.md`
   T04 → `IMPLEMENTED` with `Commit` = `UNCOMMITTED`, and write checkpoint 07.
5. Do **not** edit `scripts/sdle.py` or `.claude/hooks/` while a suite run is in flight —
   `bare_project` copies both per test.
