# T04 Implementation Handoff — Attempt a01

**Phase:** T04 — Bind Spec Kit to the Active WorkItem (contract §10)
**Attempt:** 01
**Implementer context:** fresh/isolated (resumed attempt — see below)
**Status recommendation:** IMPLEMENTED

> **Why this is still attempt 01.** The implementer of this attempt was terminated by an API session
> limit between M5 and M6. Per §24.6 that is an *interruption*, not a verification FAIL, so the
> attempt number does not increment and checkpoints 01–05 remain valid evidence of what landed.
> This handoff was written in a fresh context that reconstructed state from the repository. **Every
> figure below was produced by a command run in that context.** Nothing is copied from a
> checkpoint's narrative; where a checkpoint's figure and mine differ (wall-clock time, notably),
> mine is the one recorded.

---

## Inputs read from disk

- `docs/transition/phases/T04-plan.md` (authoritative, immutable)
- `docs/transition/phases/T04-checkpoint-a01-01.md` … `-06.md`
- `docs/transition/transition.md` §24.6, §25; `docs/transition/progress.md`;
  `docs/transition/templates/phase-handoff.md`
- `CLAUDE.md`; the actual working-tree diffs of every modified file; `git status`, `git log`,
  `git diff beb28f2`

Verified independently rather than taken on trust: the orchestrator's briefing described
`SKILL.md`, `README.md` and `docs/SDLE-Reference-Guide.md` as having unfinished D12 work because a
raw `current_feature_id` grep still matched them. Reading the diffs showed those matches are the
*intended* ones (historical migration rows and the new v1.15 history/revision rows). The only D12
subject genuinely unfinished was `CLAUDE.md`.

---

## Changes made

### Landed before this context (M1–M5, checkpoints 01–05), re-verified here

| M | Content | Re-verified how |
|---|---|---|
| M1 | D2+D3+D8: `specKit` state object, `current_feature_id` removed from the template, `CURRENT_VERSION = "1.15"`, `_mig_1_14` + 15th `VERSION_MIGRATION` row, `speckit_ref` / `speckit_set`, `ARTIFACT_OWNERSHIP` re-pointed, **`legacy_prefix` deleted (NB-1)**, `paths` made a required positional of `resolve_artifact_path` | `grep -n 'CURRENT_VERSION = '` → `1.15`; a regex extraction of the `MIGRATIONS` list → **15 tuples, terminal `('1.14','1.15','_mig_1_14')`**; `grep -n legacy_prefix scripts/sdle.py` → **no output, exit 1**; `templates/state.json` parsed as JSON |
| M2 | D4+D5+D7: `SPECKIT_REQUIRED_CAPABILITIES`, `detect_speckit_capabilities`, `cmd_feature_bind`, `cmd_feature_capabilities`, additive `cmd_preflight` data keys | source read; `sdle --help` shows the `feature` group; `RUNTIME_FREE_COMMANDS` **byte-identical** to `beb28f2` |
| M3 | D1+D6+D9+D10 + `validate`'s new finding, with the 17 test path-rebinding lines and the single permitted `conftest.py` edit | `git diff` of each test file read line by line (see TP-003 table); `shutil.move` is the only `shutil.` call in the engine |
| M4 | D11: write-fence carve-out + `FENCE_REASONS` rewrite, `test_hooks.py` cases | `git diff -- tests/test_hooks.py` read; deny list still carries `workitems/index.md`, `workitem.json`, `.sdle/state.json`, `.sdle/audit.md` |
| M5 | `tests/test_units_speckit_binding.py` (N1–N13) **and** the `phase-execution.md` half of D12 | file collects **53 tests**; 8 `feature bind` lines in `phase-execution.md`, one per Spec Kit invocation block |

### Landed in this context (M6 — the remainder of D12)

**Exactly one edit: `CLAUDE.md`.** One sentence, inserted as its own paragraph between the
"Runtime state is WorkItem-scoped…" paragraph and "Which WorkItem is active is resolved…":

> SpecKit's WorkItem-specific artifacts are scoped the same way — a WorkItem's feature directory is
> `workitems/<workitem-id>/specs/<feature-id>/`, discovered and moved there by `feature resolve`
> and recorded in `state.specKit.featureDirectory` — while genuinely repository-wide SpecKit
> scaffolding, `.specify/` including `memory/constitution.md`, stays at the repository root.

This is the sentence D12 asks for. It is additive and descriptive: it states no rule, weakens no
invariant and changes no instruction in that file. **Flagged for human review** because `CLAUDE.md`
also carries the agent-facing project instructions; a reviewer should confirm the wording. No test
and no engine path reads it (`grep -rn 'CLAUDE.md' tests/ scripts/sdle.py` matches only two prose
comments citing invariants 6 and 8).

**D12 per-file audit** (the check that decided M6's remaining scope):

| File | D12 requires | Found | Action |
|---|---|---|---|
| `modules/phase-execution.md` | bind lines, Phase 4 paragraph, 12 path substitutions | done in M5 | none |
| `SKILL.md` | version ×2, `ARTIFACT_OWNERSHIP`, 15th `VERSION_MIGRATION` row | all present | none |
| `modules/security-review.md` | the three artifact lines | all three now `{state.specKit.featureDirectory}/…` | none |
| `README.md` | version ×2, history row **above** v1.14, state-field row → `specKit` | all present | none |
| `docs/SDLE-Reference-Guide.md` | header version, four artifact rows, two prose mentions, state-field row, the one example path, new revision row | all present (plus Appendix B's `(v1.14)`→`(v1.15)` heading) | none |
| `.claude/commands/sdle-reset.md` | the one line enumerating what a reset clears | `workitems/<id>/specs/` added to the "survives" list | none |
| `CLAUDE.md` | one sentence | **untouched** | **edited** |

---

## Deliberate behavior changes

As specified by the plan's D1–D12. In brief, and only where behaviour actually changed:

1. **`specKit` supersedes `current_feature_id`** (D2). Template key removed, not mirrored. One
   accessor `speckit_ref(state)` defaults every key, so a pre-1.15 state degrades to all-null.
2. **Schema 1.14 → 1.15** (D3) with `_mig_1_14`: the old value moves to `specKit.featureId`;
   `featureDirectory` is derived from the tree, first hit wins (`workitems/<wi>/specs/<id>`, then
   `.specify/specs/<id>`, else `null`); nothing is moved on disk. `workflowId`/`runId` created null.
3. **A WorkItem's Spec Kit feature directory is `workitems/<id>/specs/<feature-id>/`** (D1, D6).
   `feature resolve` discovers across a fixed tier order and **moves** (never copies) what it finds
   into the WorkItem, audited as `speckit_feature_adopted`, refusing `feature_target_exists` /
   `feature_adopt_failed` rather than overwriting or half-moving.
4. **`feature bind` / `feature capabilities`** (D4, D5, D7): capability detection that refuses
   (`speckit_capability_missing`) rather than assumes; `feature bind` is pure and emits `env` as an
   ordered list of `{name, value}` objects.
5. **`gate_precondition_hook` refuses `feature_outside_workitem`** for `gate_spec`/`gate_plan`/
   `gate_tasks`/`gate_analyze` when the recorded directory is not under the bound WorkItem (D9).
6. **Security-review evidence follows `featureDirectory`** (D10).
7. **Write-fence carve-out** for `workitems/<id>/specs/` only (D11).
8. **NB-1 discharged** (D8): the `.workflow/` prefix bridge inside `resolve_artifact_path` is gone;
   `ARTIFACT_OWNERSHIP` now carries `{workitem_runtime}` and `{speckit_feature_directory}`.

---

## Preserved behavior / invariants

Each row is a command run in this context, not an assertion of intent.

| Guarantee | Evidence |
|---|---|
| The ladder never guesses | `resolve_decision` and `bind_workitem` extracted from both trees and compared: **byte-identical to `beb28f2`** |
| `migrate-workflow` never mutates `.workflow/` | `cmd_migrate_workflow` **byte-identical to `beb28f2`** (9687 chars, exact match) |
| `init` still refuses `legacy_workflow_present` unconditionally | refusal still raised in `resolve_binding` (`grep -n legacy_workflow_present` → one site); `resolve_decision` unchanged |
| Legacy `.workflow/` dual-read rung still works | `{workitem_runtime}` resolves to `.workflow` under the legacy binding — `test_n9_workitem_runtime_resolves_to_workflow_under_the_legacy_binding`; `feature resolve` keeps baseline behaviour there — `test_n7_the_legacy_binding_keeps_its_baseline_behaviour` |
| `SDLE_OWNED_PREFIXES` unchanged | block extracted from both trees: **identical** |
| `write_atomic` untouched (F1 procedure is VOID) | `write_atomic` **byte-identical to `beb28f2`** |
| Audit chain / single writer | `append_audit` **byte-identical to `beb28f2`**; `feature bind` writes nothing (`test_n11_feature_bind_writes_nothing_on_any_path`, whole-root SHA map) |
| `RUNTIME_FREE_COMMANDS` closed set unchanged | frozenset block **byte-identical to `beb28f2`**; `feature` is deliberately not a member |
| No new `dataclass_replace(paths, workitem=…)` site | `tests/test_units_workitem_resolution.py` **byte-unchanged vs `beb28f2`** and passing — it asserts the exact set |
| Guardrail test files byte-unchanged | `git diff --name-only beb28f2 -- tests/test_units_workitem.py tests/test_units_workitem_resolution.py` → **empty**; `test_units_workitem.py` still collects **57** |
| Invariant 3 (SpecKit opacity) | `grep -E 'speckit-\|/speckit\.'` over every added diff line (680 lines) **and** over the whole new test file → **0 matches** |
| Invariant 8 (gates in the parent) | T04 delegates nothing; no subagent surface added |
| No future-phase leakage (A18) | `grep -cE 'policies/\|flow_id\|risk_tier\|classification\|\.sdle/config'` over added lines → **0**; over the new test file → **0**; no repository-root `.sdle/` exists |

---

## Test changes and TP-003 classification

`git diff --name-status beb28f2 -- tests/` → **9 `M`, zero `D`, zero `R`**.
Untracked in `tests/`: **`tests/test_units_speckit_binding.py` only**.
**No test was weakened, skipped, xfailed or deleted.** All modifications are **category 2**
(genuinely superseded behaviour / path rebinding). There is no category 3 item in this phase.

| Test file | +/- | Category | Rationale (verified against the actual diff) |
|---|---|---|---|
| `tests/conftest.py` | +10 −0 | 2 | **The single edit the anti-contradiction clause permits, and nothing else**: `Project.specs_root`, `Project.feature_dir(feature_id)`, module-level `FEATURE_ID = "001-todo-api"`. No fixture added, removed, renamed or re-scoped; `bare_project` untouched. |
| `tests/test_hooks.py` | +11 −0 | 2 | Purely additive: 3 allow cases for `workitems/<id>/specs/…` (POSIX, relative, Windows) and 4 deny cases (`.sdle/lock`, `reviews/…`, and two near-misses `workitems/wi-a/specs.md`, `workitems/specs/not-a-workitem.md`). Every pre-existing case, including `/proj/.specify/specs/001/spec.md`, is unchanged. |
| `tests/test_integration_01_happy_path.py` | +9 −5 | 2 | 5 `.specify/specs/{FEATURE}/…` paths → `{feature_dir}/…`, derived **per call** from the project handed to `run_happy_path` because a second WorkItem is driven through the same helper. |
| `tests/test_integration_02_to_05.py` | +8 −3 | 2 | 3 path lines via a module-level `FEATURE_DIR` built from `FIXTURE_WORKITEM_ID`. |
| `tests/test_integration_06_to_09.py` | +12 −7 | 2 | 7 path lines, same shape. |
| `tests/test_lint_skill.py` | +1 −1 | 2 | The README title string the version-drift test rewrites: `v1.14` → `v1.15`. The test still proves drift fires. |
| `tests/test_units_state.py` | +4 −4 | 2 | 4 version literals: template version, migrate `to`, terminal step `1.13->1.14` → `1.14->1.15`, resulting state version. |
| `tests/test_units_transitions.py` | +7 −4 | 2 | `test_gate_show_reports_unresolved_feature_id` now expects the `speckit_feature_directory` skip reason; `test_gate_show_substitutes_feature_id` seeds a `specKit` object and expects the WorkItem-scoped path; completion-summary version. |
| `tests/test_units_workitem_runtime.py` | +12 −7 | 2 | Version literals (template, migrate `to`, `execution.json` `sdleVersion`), the migrate step list now `["1.13->1.14", "1.14->1.15"]`, one test **renamed** (`…is_1_14…` → `…is_1_15…`, body otherwise unchanged), and the migrate-workflow field list: `current_feature_id` removed from the preserved-field loop and replaced by two **stronger** assertions — `"current_feature_id" not in migrated` and `migrated["specKit"] == legacy_state_before["specKit"]`. |
| `tests/test_units_speckit_binding.py` | **new**, 861 lines, **53 collected** | — | Contract §10's N1–N13. No Spec Kit is ever invoked: capability detection runs against fabricated `.specify/scripts/` stub text files, and every generation step writes an artifact over the size floor. |

Suite arithmetic: planner's baseline at `beb28f2` was **438**; 438 + 53 (new file) + 7 (added hook
parametrize cases) = **498**, which is exactly what both `--collect-only` and the passing count
report. Nothing else was added or lost.

A note the plan asked to be honest about: a suite-wide grep for `skip`/`xfail` is **not** evidence
of anything. In this tree it matches a pre-existing `@pytest.mark.skipif(SH is None, …)` in
`tests/test_units_infra.py` and the SDLE CLI flag `--skip-tests`. Neither is a T04 concern, and
neither was touched. The real evidence for "no skips" is that `-rsxX` printed **no** short-summary
section (`grep -c "short test summary"` on the captured run = **0**) and collected == passed.

---

## Commands actually run

All pytest runs went through `rtk proxy`, unpiped, redirected to a file, with the raw exit read
from `$?` with no pipe in between (F11: a bare `python -m pytest` is a false green here).
Host interpreter: **Python 3.13.0**.

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (entry state, before M6) | **`498 passed in 950.63s (0:15:50)`, RAW_EXIT=0** | no short-summary section; establishes the starting point independently of checkpoint 05 |
| `python scripts/sdle.py lint-skill` (immediately after the `CLAUDE.md` edit, as D12/M6 requires) | **RAW_EXIT 0** | stderr `grep -c '^\[PASS\]'` = **22**, `grep -c '^\[FAIL\]'` = **0**, JSON `data.failed == []`; `tables_wellformed: Parsed 19 phases, 8 gates, 15 migration rows`; `version_string_consistent: all four locations report v1.15`; `migration_covers_every_state_field: every field has a migration row` |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` (final, M7) | **`498 passed in 993.19s (0:16:33)`, RAW_EXIT=0** | `grep -c "short test summary"` = **0** → zero skips, xfails, errors |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **`498 tests collected in 0.24s`**, RAW_EXIT=0 | collected == passed |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only tests/test_units_speckit_binding.py"` | **53 tests collected** | 38 `def test_` + parametrisation |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only tests/test_units_workitem.py"` | **57 tests collected** | unchanged guardrail file |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=4/12 next=T04`, **RAW_EXIT 0** | also re-verifies `control-plane.sha256` |
| `git diff --exit-code beb28f2 -- <A16 must-not-change list>` | **exit 0** | see A16 |
| `git diff --name-status beb28f2 -- tests/` | 9 `M`, 0 `D` | see A17 |
| Python 3.11 | **NOT_RUN** | no 3.11 interpreter on this host |
| CI (`ubuntu-latest` / `windows-latest`) | **NOT_RUN** | branch is local-only; no CI run has ever been observed on it. **No outcome predicted.** |

Wall-clock note: both full runs here (15–16 min) are roughly twice the ~8 min recorded in earlier
checkpoints. Read-only evidence commands were running concurrently in this context. Both runs are
RAW_EXIT 0 with identical pass counts, so the difference is host load, not behaviour. It is recorded
rather than smoothed over.

---

## Acceptance criteria

| # | Result | Evidence |
|---|---|---|
| A1 | **MET** | `498 passed in 993.19s`, RAW_EXIT 0; `--collect-only` = **498**; no short-summary section |
| A2 | **MET** | `lint-skill` RAW_EXIT 0, **22 PASS / 0 FAIL**, `15 migration rows`, `all four locations report v1.15` |
| A3 | **MET** | `templates/state.json` parsed: `workflow_version` = `1.15`; `specKit` keys = `['featureId','featureDirectory','workflowId','runId']`; `'current_feature_id' in d` → **False** |
| A4 | **MET** | `grep -n legacy_prefix scripts/sdle.py` → no output, **exit 1**. `grep -c '\.workflow' scripts/sdle.py` = **12**; at `beb28f2` = **12** (not larger) |
| A5 | **MET** | `MIGRATIONS` = **15** tuples, terminal `('1.14','1.15','_mig_1_14')`; `CURRENT_VERSION = "1.15"` |
| A6 | **MET WITH DECLARED EXCEPTIONS** | see the A6 section below — the criterion as literally worded is unreachable |
| A7 | **MET (with a naming correction)** | `test_n8_a_state_with_no_speckit_key_is_readable` is parametrised over `state dump`, `header`, `gate show --gate gate_spec`, `artifact path --gate gate_spec`, asserting exit 0 and `"Traceback" not in stderr`. **There is no `status` subcommand** in this CLI (`sdle --help` enumerates **36** subcommands, parsed from the usage line in this context, and `status` is not among them; `header` and `state dump` are the readers A7 means). Recorded as a wording defect in the plan, not a gap in coverage. |
| A8 | **MET** | `test_n4_a_missing_capability_refuses_and_writes_nothing` (parametrised over each capability plus "no `.specify/scripts/` at all") and `test_n4_an_absent_speckit_refuses_speckit_missing` |
| A9 | **MET** | `test_n2b_an_ambiguous_repository_refuses_before_any_speckit_work` ×3 subcommands; `test_n2a_feature_is_not_a_runtime_free_command`; and `RUNTIME_FREE_COMMANDS` extracted from both trees is **byte-identical to `beb28f2`** |
| A10 | **MET** | `test_n12_two_workitems_run_the_full_flow_against_their_own_speckit_context`; `test_n1_each_workitem_records_its_own_feature_directory` |
| A11 | **MET** | `test_n5_adoption_moves_the_directory_and_leaves_exactly_one_copy`; `test_n6_adoption_is_audited_with_from_and_to` |
| A12 | **MET** | `test_n6_an_occupied_target_refuses_without_touching_either_side`; `test_n6_an_oserror_during_the_move_refuses_with_the_source_intact` |
| A13 | **MET** | `test_n11_feature_bind_writes_nothing_on_any_path` (whole-root recursive SHA map, success + 3 refusal paths); `grep -rn 'feature\.json' scripts/sdle.py` → **no match**; `test_n5_no_string_constant_in_the_engine_names_a_speckit_owned_file` |
| A14 | **MET** | `tests/test_hooks.py` allow list carries the three `workitems/<id>/specs/…` forms; deny list still carries `workitems/index.md`, `workitem.json`, `.sdle/state.json`, `.sdle/audit.md`, plus the new `.sdle/lock`, `reviews/…` and two near-misses |
| A15 | **MET** | `grep -E 'speckit-\|/speckit\.'` over the 680 added diff lines → 0; over `tests/test_units_speckit_binding.py` → 0. `speckit_present` / `speckit_skill_prefix` JSON keys unchanged |
| A16 | **MET** | `git diff --exit-code beb28f2 -- scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .claude/settings.json .github/ docs/dry-runs/ docs/architecture/ requirements/ .gitignore .claude/skills/sdle/modules/gate-protocol.md` → **exit 0**. `.claude/commands/` shows exactly one `M` row, `sdle-reset.md` |
| A17 | **MET** | zero `D` rows; 9 `M` rows each justified in the TP-003 table; the only new file is `tests/test_units_speckit_binding.py`; `conftest.py`'s diff is exactly the permitted edit |
| A18 | **MET** | leakage grep = 0 over added lines and over the new test file; no repository-root `.sdle/`; `.workflow/` dual-read, `migrate-workflow` and `init`'s refusal all still present and pinned (see Preserved behaviour) |
| A19 | **MET** | `python tools/transition/validate.py` → `TRANSITION_VALID: complete=4/12 next=T04`, RAW_EXIT 0 |
| A20 | **MET** | `grep -n 'workflowId\|runId' scripts/sdle.py` → 3 hits: the `SPECKIT_REF_KEYS` tuple, a docstring, and `workflowId=None, runId=None` in `_mig_1_14`. **No non-null write anywhere.** Asserted after a full run by `test_n12…` and `test_n8_a_null_feature_id_migrates_to_an_all_null_object` |
| A21 | **MET** | Python 3.11 and CI both recorded **NOT_RUN / UNKNOWN**; no outcome predicted |

### A6 in full — why it is "met with exceptions"

`grep -rn --binary-files=without-match 'current_feature_id' scripts/ .claude/ README.md
docs/SDLE-Reference-Guide.md` returns **10** lines. A6 expects only two. Each match, and why it is
there:

| Match | Why it must stay |
|---|---|
| `scripts/sdle.py:1059`, `:1064` | The **code bodies** of the two historical migrations A6 explicitly permits (`_mig_1_0`, `_mig_1_1`). A migration chain replays history verbatim; deleting these breaks 1.0→1.15. |
| `scripts/sdle.py:1189` | `_mig_1_14` must name the key it removes (`state.pop("current_feature_id", None)`). Without it the migration is a no-op and the field would survive. |
| `scripts/sdle.py:719`, `:1174` | A section comment and `_mig_1_14`'s docstring explaining the supersession. |
| `SKILL.md:213`, `:214` | The two historical `VERSION_MIGRATION` rows A6 names. |
| `SKILL.md:227` | The **new** 1.14→1.15 row. It must describe what it replaces, and D3 requires the literal `specKit` in the same cell. |
| `README.md:471`, `docs/SDLE-Reference-Guide.md:1021` | The v1.15 history row and the 1.4 revision row — required by D12, and both describe the replacement in the past tense. |
| `.claude/skills/sdle/modules/gate-protocol.md:66` | **The A6 vs A16 contradiction, first declared in checkpoint 01.** That line reads *"Resolve the artifact path from **ARTIFACT_OWNERSHIP** using `gate_key` (substitute `current_feature_id` if needed)"*, and A16 requires the file **byte-unchanged**. A16 was honoured. |

Also matched but excluded above: `scripts/__pycache__/*.pyc`, build artifacts, filtered with
`--binary-files=without-match`.

The `gate-protocol.md` line is the only one of the ten that is genuinely **stale prose in a live
prompt file** — `ARTIFACT_OWNERSHIP` no longer has a `current_feature_id` placeholder. Its
practical impact is small (the orchestrator resolves paths by calling `sdle.sh artifact path`,
which does the substitution deterministically), but it is a real defect and it is carried into the
findings below rather than quietly absorbed.

---

## Git evidence

- **HEAD:** `fe856d1` ("Plan T04 Spec Kit WorkItem binding") on `transition/workitem-v1`.
- **Commit:** none. T04 is **UNCOMMITTED**; all work is in the working tree.
- **Rollback point:** `beb28f2` (unchanged from the plan). `git reset --hard beb28f2` restores the
  T03 product tree.
- **Working tree (`git status --porcelain`):** 11 modified product/doc files
  (`scripts/sdle.py`, `.claude/hooks/hooks.py`, `.claude/skills/sdle/SKILL.md`,
  `…/templates/state.json`, `…/modules/phase-execution.md`, `…/modules/security-review.md`,
  `.claude/commands/sdle-reset.md`, `README.md`, `CLAUDE.md`, `docs/SDLE-Reference-Guide.md`),
  9 modified test files, 6 untracked `T04-checkpoint-a01-0N.md`, 1 untracked
  `tests/test_units_speckit_binding.py`, plus the **out-of-scope** `.claude/settings.local.json`
  (the user's permission allowlist — not staged, not reverted, not edited).
- **Diff scope vs `beb28f2` (`--numstat`):** `scripts/sdle.py` +515 −48; `.claude/hooks/hooks.py`
  +14 −4; `phase-execution.md` +19 −12; `SDLE-Reference-Guide.md` +11 −10; `SKILL.md` +8 −7;
  `state.json` +7 −2; `sdle-reset.md` +4 −3; `security-review.md` +3 −3; `README.md` +3 −2;
  `CLAUDE.md` +2 −0; tests +74 −31 across 9 files; one new 861-line test file.

---

## Known limitations / risks

1. **Declared divergence — `modules/phase-execution.md` moved from M6 into M5.** N2(d) is that
   file's test, and the plan's own F9 rule is that a subject and its test land in the same
   milestone. Declared in checkpoints 03 and 05; the file's D12 content is unchanged in substance.
2. **Declared divergence — the two `Paths` members (D1) landed in M2, not M3** (checkpoint 02),
   because D5's `data.workitem_specs_root` consumes `speckit_specs_relative`. Pure derivations.
3. **Declared divergence — the write-fence pattern is `(?:^|/)workitems/[^/]+/specs/`**, not the
   plan's `^workitems/…` (checkpoint 04). The hook's `relative()` is best-effort and Claude Code
   passes absolute native paths, so a strictly `^`-anchored pattern would not match
   `/proj/workitems/wi-a/specs/…`. Segment-boundary anchoring is the same semantics the neighbouring
   `in_dir()` already uses. Four near-miss deny cases pin that nothing else under `workitems/` can
   match.
4. **Declared divergence — nine version-assertion lines were updated, not the one the plan's table
   named** (checkpoint 01), across five files. One test renamed (`…is_1_14…` → `…is_1_15…`), body
   otherwise unchanged. All category 2.
5. **Declared divergence — A6 vs A16 is a contradiction inside the plan**, resolved in favour of
   A16 (containment). See the A6 section.
6. **Accepted residual (plan F6): capability-probe false negatives.** An installation that supports
   `SPECIFY_INIT_DIR` / `SPECIFY_FEATURE_DIRECTORY` without shipping a script naming them is
   reported unsupported and refused. The failure direction is closed by design.
7. **`feature_target_exists` reachability** (checkpoint 03's analysis, restated rather than
   broadened): because tier 1 is `workitems/<id>/specs/*` and a candidate must be a directory, a
   target that already exists *as a directory* means tier 1 was non-empty and was chosen, so no move
   is attempted. The refusal is reachable when the target exists but is **not** a directory. It is a
   defence-in-depth non-overwrite guard (F4), and N6 exercises it through that case.
8. **D6's relocation is the phase's one data-affecting operation.** Bounded and recoverable: inside
   a Git working tree, refuses rather than overwrites, both endpoints verified inside
   `project_root`, audited with `from`/`to`, undone by moving the directory back.
9. **`CLAUDE.md` was edited.** Additive, descriptive, one sentence — but that file also carries the
   agent-facing project instructions, so it warrants a human read rather than a machine diff alone.
10. **Python 3.11 and CI are NOT_RUN.** T04 is standard-library-only, but no outcome is predicted.

---

## Findings for the orchestrator to assign (not T04's to fix)

1. **T02 residual in `modules/phase-execution.md`** (first declared in checkpoint 05, restated here
   verbatim in substance so it does not vanish). That file still names `.workflow/audit.md`,
   `.workflow/implementation-manifest.md` and `.workflow/completion-summary.json` in **Phases 15,
   16, 18 and the generic "BEFORE executing any phase" block**, even though T02 moved the runtime to
   `workitems/<id>/.sdle/` and T04's `ARTIFACT_OWNERSHIP` now reads
   `{workitem_runtime}/implementation-manifest.md`. This is **real staleness in a live prompt file**,
   not a T04 regression: T04's D12 does not list those lines, and fixing them would widen this
   phase's scope. **Needs an owning phase.**
2. **`modules/gate-protocol.md` still says "substitute `current_feature_id` if needed"** while the
   placeholder no longer exists. A16 requires the file byte-unchanged, so T04 could not fix it. A
   one-word documentation fix; needs an owning phase (or an explicit verifier ruling that A16 should
   yield here).
3. **`SKILL.md`'s verbosity-suppression list still says "feature-ID resolution"** where the engine
   now resolves a feature *directory*. Not listed in D12; cosmetic; left untouched.
4. Carried forward from the plan's own Unknowns, unchanged: `docs/dry-runs/` is deliberately not
   updated (T11's documentation sweep) and now carries a further ~17 stale path lines;
   `design/`, `reviews/`, `clarifications/` stay repository-level (unassigned); T03-4/5/6 remain
   **not adopted**.

---

## Claims for verifier to independently check

1. `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → **498 passed, RAW_EXIT 0**, no
   short-summary section; `--collect-only` = **498**. (Use `rtk proxy`, unpiped, 600000 ms.)
2. `python scripts/sdle.py lint-skill` → RAW_EXIT 0, **22 PASS / 0 FAIL**, `15 migration rows`,
   `all four locations report v1.15`.
3. `grep -n 'legacy_prefix' scripts/sdle.py` → **nothing** (A4, NB-1).
4. `git diff --name-status beb28f2 -- tests/` → **zero `D`**; `git diff -- tests/conftest.py` is the
   single permitted edit.
5. `git diff --exit-code beb28f2 -- <A16 list>` → **exit 0**.
6. `cmd_migrate_workflow`, `bind_workitem`, `resolve_decision`, `write_atomic`, `append_audit` and
   `SDLE_OWNED_PREFIXES` are **byte-identical to `beb28f2`** (extract-and-compare, not eyeballing).
7. The A6 grep returns 10 lines; each is accounted for in the A6 table, and the
   `gate-protocol.md` one is a declared, unfixable-under-A16 residual.
8. `python tools/transition/validate.py` → RAW_EXIT 0.
9. Python 3.11 and CI are **NOT_RUN**; any claim otherwise in this document would be an error.

## Blocker

None. No material architecture, contract or baseline decision was required. The two plan-internal
contradictions encountered (A6 vs A16; A7 naming a `status` subcommand that does not exist) are
ordinary plan defects, declared here rather than resolved by widening scope.
