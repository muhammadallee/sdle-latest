# T02 Implementation Handoff — Attempt a01

**Phase:** T02 — Move Runtime State from Repository-Global to WorkItem-Scoped
**Attempt:** 01
**Implementer context:** fresh/isolated
**Status recommendation:** IMPLEMENTED
**Plan executed:** `docs/transition/phases/T02-plan.md` (M1-M7, D1-D11, N1-N35)
**Rollback point:** `7b9374b` (T01). HEAD at start of work: `6e8af8c`.

## Inputs read from disk

`docs/transition/phases/T02-plan.md` (all 809 lines), `docs/transition/transition.md`
(§0, §1.x, TP-001…TP-012, §7, §8, §9, §14, §18, §20, §24.3, §28 as cited),
`docs/transition/progress.md`, `docs/transition/baseline.md` references cited via
the plan, `CLAUDE.md`, and the actual source: `scripts/sdle.py`,
`.claude/hooks/hooks.py`, `.claude/skills/sdle/SKILL.md`,
`.claude/skills/sdle/templates/state.json`, all nine `tests/*.py`, `.gitignore`,
`.claude/commands/*.md`, `README.md`, `docs/SDLE-Reference-Guide.md`, plus
`git log`, `git status`, `git diff --numstat`.

## Baseline correction acted on

The plan's §12.1/§13/F1 procedure assumes a reliably red suite. That assumption
is **void**: the out-of-band commit `6e8af8c` added a bounded 10/20/40/80 ms
retry around `os.replace` in `write_atomic`, plus two tests pinning that a
permanent `PermissionError` still raises. The pre-T02 baseline is therefore
**289 passed, raw exit 0**. Every failure observed during this phase was treated
as a presumed T02 regression and investigated; **no failure was classified
`ENVIRONMENT_FLAKE`**, and `write_atomic` was not touched (plan P3, §14).

The `tests/test_units_infra.py 42/0` row in `git diff --numstat 7b9374b`
belongs to `6e8af8c`, **not** to T02: `git diff --numstat 6e8af8c` does not
list that file and `git status` shows it clean.

## Changes made

### `scripts/sdle.py` (554 insertions / 47 deletions vs `6e8af8c`)

**M1 — the `Paths` seam (D1).** `Paths` gains `workitem: str | None = None` and
a single runtime seam: `legacy_workflow`, `workitem_root`, `runtime`,
`runtime_relative`, plus rebound `state_file` / `audit_file` / `lock_file` and
new `execution_file` / `manifest_file` / `completion_file` / `evidence_dir`.
`workflow` is retained as an alias of `runtime`, so no call site outside the
property block moved. The three hardcoded literals (plan E2/E3) are gone:
the manifest relative path, the manifest `changed` filter and the Phase 17
`:(exclude)` pathspec all derive from the properties; `write_completion_summary`
and the manifest write use `completion_file` / `manifest_file`. Four refusal
strings that named `.workflow/` literally now interpolate `runtime_relative`.

**M2 — the ladder (D2, D3, C4).** `RUNTIME_FREE_COMMANDS`,
`registered_workitem_ids`, `legacy_state_present`, and
`bind_workitem(paths, explicit=None, *, for_init=False)` — a pure function that
returns a bound `Paths` or raises `Refused`, so the hooks can call it
speculatively. `main()` runs it for every non-runtime-free command. New global
`--workitem`. `SDLE_OWNED_PREFIXES` gains `"workitems/"`.

**M3 — schema (D6).** `CURRENT_VERSION = "1.14"`, `_mig_1_13`, a 14th
`MIGRATIONS` row, `cmd_init` sets `state["workitem"]`.

**M4 — execution identity (D7) and `project_name` (D10).**
`workitem_metadata_file`, `workitem_metadata`, `execution_prefix`,
`execution_identity`, `write_execution_file`. `cmd_init`'s `project_name`
precedence becomes `--project` → requirements heading → **WorkItem title** →
directory name, the new rung deliberately *after* heading inference.

**M5 — `migrate-workflow` (D8).** `verify_audit_chain` extracted unchanged from
`cmd_audit_verify`; `MIGRATION_VERIFIED_FIELDS`; `cmd_migrate_workflow` and its
parser entry (its `--workitem` uses `dest="migrate_workitem"` so the flag works
on either side of the subcommand without argparse clobbering the global value).

### Other product files

| File | Change |
|---|---|
| `.claude/skills/sdle/templates/state.json` | `workflow_version` `1.14`; new `"workitem": null` after it. |
| `.claude/skills/sdle/SKILL.md` | One new `VERSION_MIGRATION` row (action text contains the literal `workitem`), the two version strings, and prose (Step 1 migrate condition, Step 1 bootstrap paragraph rewritten for resolution/refusals/`migrate-workflow`, the refusal rule, the write-fence sentence). **No other constant table touched.** |
| `.claude/hooks/hooks.py` | `FENCED` gains `workitems`, with a reason string that names registry/identity/runtime and leaves an explicit note for the phase that later moves artifacts under `workitems/`; `.workflow` reason now names `migrate-workflow`; `dirty_tree` calls `engine.bind_workitem(paths)` inside its existing `try/except`; `_project_dir` also recognises a `workitems/` root. |
| `.gitignore` | One line `workitems/*/.sdle/lock`; the missing trailing newline (E25) repaired. |
| `CLAUDE.md` | Lines 11 and 34 (D11). |
| `README.md` | Title, new v1.14 history row **above** v1.13 (first-match regex), WorkItem section rewritten with the ladder and `migrate-workflow`, file-layout tree, state-schema section (`workitem` row, v1.14 header, `audit_sha` wording), completion-summary path. |
| `docs/SDLE-Reference-Guide.md` | Header version; every runtime-file path in the artifact-ownership table and prose; three new rows for `execution.json`, migration evidence and the WorkItem records; WorkItem-identity paragraph; two new subsections (resolution + legacy runtime, execution identity); Appendix B header and `workitem` row; revision-history row 1.3. |
| `.claude/commands/sdle-reset.md`, `sdle-start.md` | Text only (D11). |

**Must-not-change list verified clean:** `git diff --exit-code 7b9374b --
scripts/sdle.sh scripts/sdle.ps1 .claude/settings.json .github/workflows/ci.yml
.claude/skills/sdle/modules/ requirements/ docs/dry-runs/` → exit **0**.

## Deliberate behavior changes

C1-C12 of the plan, all landed. Restated as refusals a caller can hit:

- `workitem_required`, `workitem_unknown`, `workitem_ambiguous` — resolution.
- `legacy_workflow_present` — `init`, **unconditionally** while a legacy
  `.workflow/state.json` exists, whatever the registered count (D2/C4).
- `target_exists`, `legacy_state_invalid`, `legacy_state_missing`,
  `legacy_audit_broken`, `migration_verify_failed` — `migrate-workflow`.

**Consequence of D2 worth naming:** because `migrate-workflow` never deletes
`.workflow/`, a migrated repository keeps refusing `init` for *additional*
WorkItems until the legacy directory is archived by hand. That is the plan's
explicit fail-safe direction (D2) and is on T11's removal list; it is recorded
here so it is a known property, not a surprise.

## Preserved behavior / invariants

P1-P13 of the plan. Concretely: 18 phases / 8 gates untouched (`lint-skill`
still reports 19 phases, 8 gates, all `gate_registered_*` PASS); exit-code
contract and envelope shape unchanged; `write_atomic` untouched; audit format,
chaining, `audit_sha`, tamper halt and rebaseline unchanged — only the path
moved, and `verify_audit_chain` is a lift-and-shift of the existing walk;
drift/queue/rate-limits/checkpoint/secrets/test-evidence/`implementation_base_ref`
untouched; `ARTIFACT_OWNERSHIP`, `PHASE_SEQUENCE`, `NEXT_PHASE`,
`PHASE_LABEL_MAP`, `PROGRESS_MAP`, `GATE_PHASES`, `PHASE_TO_GATE_KEY` and the
`approvals` key set all byte-identical; no `speckit-*` name reaches user output;
stdlib-only, no new dependency, no `match`, no PEP 695 generics, no `Self`.

## Test changes and TP-003 classification

`git diff 6e8af8c -- tests/ | grep -E '^\+.*(skip|xfail)'` is **EMPTY** (A15).
No test was skipped, xfailed, deleted or weakened.

| Test | Category | Rationale |
|---|---|---|
| `conftest.py` — `Project.runtime` property; `state_file`/`audit_file` derive from it | 2 | Contract §8 moves runtime state under the WorkItem; `baseline.md` §7 item 3 names T02 as the phase permitted to do it. One property now owns the location, so a later phase moves one line. |
| `conftest.py` — `project` fixture registers one WorkItem; old body becomes `bare_project` | 2 | Plan §6 M2. Rung 2 then binds for the whole suite with no `--workitem` plumbing anywhere. |
| `conftest.py` — `Project.pin` / `as_workitem()` | new | Needed so two WorkItems are addressable through the **unmodified** `run_happy_path` helper. |
| `conftest.py` — `init_git` `.gitignore` gains `workitems/*/.sdle/lock` | 2 | Fixtures mirror the shipped ignore file (plan §7.2). |
| `conftest.py` — `isolated_git_identity` promoted to autouse | 2 | §7.3. Precondition discharged first: `grep -rn 'Actor\|actor\|user\.name\|user\.email' tests/*.py` finds only `init_git`'s repo-local config — **no assertion depends on the machine identity**. Makes tests more hermetic, not weaker. |
| `test_units_state.py` — 4 lock literals → `Project.runtime` | 2 | Path rebinding only. |
| `test_units_state.py` — `workflow_version == "1.14"`, chain terminal `1.13->1.14`, `to == "1.14"` | 2 | The version is what §8 requires T02 to change. Plan N17: the whole-chain test was **extended in place**, not duplicated. |
| `test_units_state.py` — new `state["workitem"] == project.workitem` assertion | new | Strengthens the same test; nothing removed. |
| `test_integration_01_happy_path.py` — completion-summary glob, lock read | 2 | Path rebinding only. |
| `test_integration_06_to_09.py` — 2 manifest reads, 1 manifest write, 1 lock assertion | 2 | Path rebinding only; the write derives its relative path from `runtime`, which also pins POSIX separators (F8). |
| `test_units_transitions.py` — emitted `completion_summary` path, summary file, `workflow_version` | 2 | Path rebinding + version. |
| `test_lint_skill.py` — `test_version_drift_fires` now rewrites `v1.14 → v1.13` | 2 | The fixture edit had to name the current version; the check under test is unchanged. |
| `test_units_workitem.py` — module-level `project` fixture overrides back to `bare_project` | 2 | See the plan-conflict note below. All 57 assertions stay byte-identical. |
| `test_units_workitem.py` — `test_init_records_no_workitem_in_state` → `test_init_records_the_resolved_workitem_in_state` | 2 | T01's guard asserted no `workitem` key could exist. T02 is the phase contractually required to create it (§8), so the guard **inverts** and additionally pins that the state file lives under the WorkItem and that no `.workflow/` is created. |
| `test_units_workitem.py` — `test_a_workitem_does_not_change_what_init_and_advance_produce` control gains its own WorkItem | 2 | Its T01 control was "a project with no WorkItem", which C2 makes non-initialisable by construction. The control now carries a *different* identity — the strongest comparison the post-T02 contract admits. The same five state fields and the same `advance` outcome are still compared. |
| `test_hooks.py` — six new write-fence parameters; two new dirty-tree cases | 1 + new | The existing `.workflow` parameters are **kept**, per plan §7.2 (D9 keeps `.workflow` fenced). Only additions. |
| `test_units_workitem.py` — module docstring | 2 | Plan §7.2's last row. It claimed `.workflow/` is still where the workflow lives and that `init` neither requires nor records a WorkItem — both false after C1/C2/C5. Docstring only; no case added, removed or renamed. |
| `tests/test_units_workitem_runtime.py` | new | **44 cases**, plan N1-N35. |

**Count arithmetic:** 44 new cases in `test_units_workitem_runtime.py`
(30 landed at M4, 12 at M5, 2 at M6) + 8 new cases in `test_hooks.py`
(6 added write-fence parameters + 2 dirty-tree cases) = **52 net**, taking the
suite from the 289 pre-T02 baseline to 341.

### Declared plan divergence — plan §6 vs §7.1

Plan §6 requires the shared `project` fixture to register one WorkItem while
§7.1 pins all 57 `test_units_workitem.py` cases green *unmodified*. **Both
cannot hold**: that file asserts exact registry contents against the shared
fixture (`test_list_with_no_registry_is_empty_and_succeeds` asserts
`{"count": 0, "workitems": []}`; `test_the_first_create_writes_the_registry_skeleton`
asserts `len(lines) == 5`; the duplicate-refusal digest comparison; the
five-case malformed-index parametrisation). Reconciliation taken: that file
overrides `project` back to `bare_project` in four lines, so every one of those
assertions is byte-identical to T01, and only the two genuinely superseded
cases were edited. Reported rather than silently adapted, per §24.3 item 2.

### Other declared divergences (none material)

1. The three literals were at `scripts/sdle.py:3146`, `:3167`, `:3254`, not the
   plan's `:3132`, `:3153`, `:3240` — a +14 shift from `6e8af8c`. Same three
   statements.
2. Plan §7.2's rebinding and the `SDLE_OWNED_PREFIXES` / `dirty_tree` items were
   pulled forward from M7/M6 into M2, because the M2 fixture change reddens
   those tests immediately and each milestone must leave the suite runnable.
3. **`ARTIFACT_OWNERSHIP` Gate 7 template.** `SKILL.md` registers
   `gate_implement` → `.workflow/implementation-manifest.md` as a *static*
   template. Plan P1/A14/§14 forbid editing that table (T04 owns it), so the
   re-point happens in `resolve_artifact_path` — the single place templates are
   resolved — where a leading `.workflow/` becomes `paths.runtime_relative`.
   `paths` was added as an optional 4th parameter; all seven call sites already
   had it in scope. Without this every Gate 7 approval refused
   `artifact_missing`. Transitional and commented as such.
4. **D8 step ordering.** D8 lists the `workflow_migrated` audit entry as step 11,
   after the step-8 commit point. Appending updates `audit_sha`, so a literal
   reading leaves the committed `state.json` carrying a stale `audit_sha` and
   `audit verify` fails immediately after a successful migration. Implemented
   order keeps D8's *property* exactly: the copied ledger is verified at its new
   location **before** anything commits, the state is migrated in memory, the
   `workflow_migrated` entry is appended to the **target** ledger, and the
   target `state.json` is written **last** as the sole commit marker; step 9
   re-reads and verifies and unlinks the marker on mismatch; step 10 records the
   `migration` object on `workitem.json`. Every pre-commit write is a whole-file
   overwrite, so a re-run after any interruption is safe — proved by the
   parametrised crash test.
5. **Step 9's comparison anchor** is the in-memory migrated state, not the raw
   legacy dict. When the version chain runs no steps the two are identical, so
   it *is* §20.11's comparison; when the chain does run, its own documented
   effect (e.g. `_mig_1_8` recomputing `progress`) is not a migration defect.
   The stronger legacy-byte-equality claim is pinned by the test, which compares
   eleven fields against the **legacy file**.
6. Plan §7.2 counts 21-22 `.workflow` test lines. The observed set was 22 lines
   across 7 files, matching E27; `test_hooks.py`'s 5 were kept, not rebound.
7. **README command table.** Plan §5 says the README "command table gains
   `migrate-workflow` and `--workitem`". That table lists *conversational*
   phrases the user says to the orchestrator (`approve`, `status`, `reset
   workflow`), not CLI subcommands, so inventing a phrase for either would add
   a user-facing surface no requirement asks for. Both are documented instead
   in the README's WorkItem section, with the full five-rung ladder, the
   `migrate-workflow` invocation and what it guarantees. Intent satisfied,
   letter not; declared rather than invented.

## Commands actually run

| Command | Result | Evidence/summary |
|---|---|---|
| `python -m pytest -q` (M1, zero test edits) | **289 passed**, raw exit 0 | M1's acceptance condition — the structural proof replacing T01's `0 deletions` numstat |
| `python -m pytest tests/test_units_state.py tests/test_units_workitem.py -q` (M2, first) | 89 passed / 5 failed, raw exit 1 | All five expected: 3 lock-path literals, 2 superseded workitem cases |
| `python -m pytest tests/test_units_state.py tests/test_units_workitem.py tests/test_units_transitions.py -q` | 118 passed, raw exit 0 | after rebinding |
| `python -m pytest tests/test_integration_01_happy_path.py tests/test_integration_06_to_09.py tests/test_hooks.py tests/test_units_cli.py -q` (first) | 73 passed / 11 failed, raw exit 1 | Gate 7 `artifact_missing` (divergence 3) + dirty-tree hook binding |
| same selection, after the fix | **84 passed**, raw exit 0 | |
| `python -m pytest tests/test_integration_02_to_05.py tests/test_units_infra.py tests/test_lint_skill.py -q` | **87 passed**, raw exit 0 | |
| `python -m pytest tests/test_units_state.py tests/test_lint_skill.py tests/test_units_workitem.py tests/test_units_transitions.py -q` (M3) | **135 passed**, raw exit 0 | |
| `python -m pytest tests/test_units_workitem_runtime.py -q` (M4) | 29 passed / 1 failed then **30 passed**, raw exit 0 | the failure was a wrong *test* assumption, fixed in the test; no engine change |
| `python -m pytest tests/test_units_workitem_runtime.py -q -k "migrate or crash or after_migration"` (M5) | 12 failed then **12 passed**, raw exit 0 | first failure was the helper trying `init` without a WorkItem, which C4 refuses |
| `python -m pytest tests/test_hooks.py tests/test_units_workitem_runtime.py -q -k "fence or dirty_tree or preflight or phase_17"` (M6) | **28 passed**, raw exit 0 | |
| `python -m pytest -q` (final, full) | **341 passed**, raw exit **0** | 289 pre-T02 + 52 new; zero failures, zero errors, zero skips |
| `python scripts/sdle.py lint-skill` | **raw exit 0**, 22 checks / 22 PASS | `Parsed 19 phases, 8 gates, 14 migration rows`; `version_string_consistent: all four locations report v1.14`; `migration_covers_every_state_field: every field has a migration row`. Re-run after every documentation edit (F6). |
| `python scripts/sdle.py constants` (A9) | **raw exit 0** | `version_chain` has **14** rows, terminal pair `['1.13', '1.14']` |
| `python tools/transition/validate.py` | **raw exit 0** | `TRANSITION_VALID: complete=2/12 next=T02` |
| `git check-ignore -v workitems/wi-a/.sdle/lock workitems/index.md workitems/wi-a/workitem.json workitems/wi-a/.sdle/state.json` | one line | `.gitignore:9:workitems/*/.sdle/lock` — only the lock is ignored (§19) |
| `git diff --exit-code 7b9374b -- <must-not-change list>` | exit 0 | all byte-identical |
| Python 3.11 compatibility check | **NOT_RUN** | No 3.11 interpreter on this host |
| CI | **NOT_RUN** | Branch unpushed. No outcome predicted. |

### Final full suite

```
$ python -m pytest -q
........................................................................ [ 21%]
........................................................................ [ 42%]
........................................................................ [ 63%]
........................................................................ [ 84%]
.....................................................                    [100%]
341 passed in 971.00s (0:16:11)
RAW_EXIT=0
```

**341 passed, raw exit 0.** No failures, no errors, no skips, no xfails. The
pre-T02 baseline was 289; T02 adds 52 cases net. Because the suite is fully
green, plan F1's `ENVIRONMENT_FLAKE` classification was never invoked and no
re-run was needed.

## Git evidence

- **HEAD:** `6e8af8c` on `transition/workitem-v1` (T02 is **UNCOMMITTED**;
  the orchestrator commits and fills the SHA).
- **Working tree:** 18 modified product files, 1 new test file, 7 new
  transition documents. No deletions.
- **Diff scope vs `6e8af8c`:** `scripts/sdle.py` 554/47; `tests/conftest.py`
  81/7; `docs/SDLE-Reference-Guide.md` 76/25; `README.md` 53/12;
  `tests/test_units_workitem.py` 34/22; `tests/test_hooks.py` 32/0;
  `.claude/hooks/hooks.py` 21/3; `.claude/commands/sdle-start.md` 12/5;
  `tests/test_units_state.py` 9/8; `.claude/skills/sdle/SKILL.md` 7/6;
  `tests/test_units_transitions.py` 6/3; `tests/test_integration_06_to_09.py`
  5/8; `.claude/commands/sdle-reset.md` 5/3;
  `.claude/skills/sdle/templates/state.json` 2/1; `.gitignore` 2/1;
  `CLAUDE.md` 2/2; `tests/test_integration_01_happy_path.py` 2/2;
  `tests/test_lint_skill.py` 1/1.

## Known limitations / risks

- **Python 3.11 / CI: `NOT_RUN`.** The diff is stdlib-only and 3.11-safe by
  inspection (`from __future__ import annotations` is already in place, no
  `match`, no PEP 695 generics, no `Self`, `dataclasses.replace` is 3.7+,
  `Path.unlink(missing_ok=True)` is 3.8+). No CI outcome is predicted.
- A migrated repository keeps refusing `init` for additional WorkItems until
  `.workflow/` is archived by hand (see "Deliberate behavior changes").
- The Reference Guide's Appendix A transcript now shows a plausible WorkItem id
  (`workitems/todo-api/.sdle/...`) that no dry-run file actually produced; it is
  illustrative prose, consistent with the rest of the appendix.
- `E18`'s `is_dir()` uniqueness nit is **deliberately not fixed** (plan §14):
  resolution reads the index, never the directory listing, so it stays
  unreachable and a fix would add an untestable path.
- `write_atomic` **not** touched (plan P3, §14, §12.1).

## Claims for verifier to independently check

1. **A1** — full suite raw exit code and count, recorded verbatim above.
2. **A2** — `lint-skill` exit 0, 22/22, `14 migration rows`, `v1.14`.
3. **A3** — `validate.py` exit 0.
4. **A4/N5** — drive a real 18-phase run and confirm `<repo>/.workflow` does not
   exist afterwards
   (`test_a_full_run_leaves_no_repository_global_runtime`).
5. **A5/N1-N4** — two WorkItems complete independent runs; WI-A's `state.json`
   and `audit.md` are byte-identical after WI-B's whole run
   (`test_two_workitems_complete_independent_runs`).
6. **A7** — `grep -n '\.workflow' scripts/sdle.py`: every survivor should be the
   `legacy_workflow` property, a `paths.workflow` alias `mkdir`, a docstring,
   the documented `ARTIFACT_OWNERSHIP` legacy-prefix bridge, `SDLE_OWNED_PREFIXES`,
   or help text.
7. **F3 (fail-open resolution)** — confirm rung 5 refuses and never picks
   (`test_rung5_...`), rung 3 is reachable **only** with zero registered
   WorkItems, and `init` never takes rung 3 (`test_init_never_takes_the_legacy_rung`,
   `test_init_refuses_legacy_state_even_with_a_workitem_registered`).
8. **F5 (data loss)** — `migrate-workflow` must never write to, rename or delete
   anything under `.workflow/`. The tests compare a SHA map of the whole legacy
   tree before and after, including on every refusal path and every injected
   crash.
9. **F4 (torn migration)** — the parametrised crash test injects a failure after
   `write_atomic` calls 1-4 and asserts no target `state.json`, legacy
   unchanged, and a successful re-run.
10. **A14** — `git diff 6e8af8c -- .claude/skills/sdle/SKILL.md` touches only
    `VERSION_MIGRATION` (one added row), the two version strings, and prose.
11. **A15** — `git diff 6e8af8c -- tests/ | grep -E '^\+.*(skip|xfail)'` empty.
12. **The five declared divergences above**, especially divergence 3
    (`resolve_artifact_path`) and divergence 4 (D8 step ordering) — both are
    behaviour-relevant refinements, not cosmetic.
13. **Attribution** — `tests/test_units_infra.py` (+42) and the `write_atomic`
    retry belong to `6e8af8c`, not to T02.
14. **No future-phase leakage** — no CWD/branch/persisted-context resolution, no
    `sdle start`, no `SPECIFY_*`, no repository-level `.sdle/`, no
    `ARTIFACT_OWNERSHIP` template edit, no `audit.jsonl`, no phase/gate table
    change, no `current_feature_id` demotion, nothing removed that T11 owns.
