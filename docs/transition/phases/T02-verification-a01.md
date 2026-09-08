# T02 Independent Verification — Attempt a01

**Phase:** T02 — Move Runtime State from Repository-Global to WorkItem-Scoped
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

> The handoff is a claim set, not proof. Every row below was reconstructed from the
> repository, the contract, the Git diff and command output observed in this context.
> Where a handoff figure and the repository disagreed, the repository won and the
> discrepancy is recorded as a finding.

## Identity, scope and baseline

| Item | Observed |
|---|---|
| Commit under verification | `ab889a1` — "T02: scope the runtime to a WorkItem (IMPLEMENTED, NOT YET VERIFIED)" |
| HEAD during verification | `07e5dfb` |
| `ab889a1..HEAD` scope | `git diff --name-only ab889a1 HEAD` = `docs/transition/RESUME.md` (new, 53 lines) and `docs/transition/progress.md` (1 insertion / 1 deletion). The progress hunk changes only the T02 `Commit` cell from `UNCOMMITTED` to `ab889a1`. **Control-plane / evidence only; no product file.** Verifying the working tree at `07e5dfb` is therefore equivalent to verifying `ab889a1` for all product behaviour. |
| Working tree | `git status --short` = ` M .claude/settings.local.json` only — the known, out-of-scope pre-existing permission-allowlist edit. Nothing else dirty. |
| Rollback point | `7b9374b` (T01, verified PASS) |
| Out-of-band commit inside the range | `6e8af8c` "Retry os.replace in write_atomic on a transient PermissionError" |
| Pre-T02 suite baseline | **289**, reconstructed independently: `T01-verification-a01.md` records 287 collected at T01; `git show 6e8af8c -- tests/test_units_infra.py` adds exactly **2** `def test_` (grep count = 2). 287 + 2 = 289. |
| F1 `ENVIRONMENT_FLAKE` path | **VOID and never used.** Both full runs in this context were green at raw exit 0. No failure was pattern-matched to WinError 5; none occurred. |

### Attribution check (handoff claim 13)

`git diff --numstat 7b9374b ab889a1` lists `tests/test_units_infra.py 42/0` and
`scripts/sdle.py 569/48`. Splitting the range confirms the implementer's
attribution: `git diff --numstat 7b9374b 6e8af8c` = `T02-plan.md 808/0`,
`progress.md 2/2`, `scripts/sdle.py 15/1`, `tests/test_units_infra.py 42/0`;
`git diff --numstat 6e8af8c ab889a1` = `scripts/sdle.py 554/47` and **no**
`test_units_infra.py` row. `git show 6e8af8c -- scripts/sdle.py` is a bounded
10/20/40/80 ms retry loop around `os.replace` whose `else:` branch re-raises on
an unguarded final attempt — it cannot fail open. **T02 did not touch
`write_atomic` (plan P3, §14).** CONFIRMED.

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **A1** full suite, ≥287 + new, raw exit reported unmodified | PASS | Two independent full runs in this context. Run 1: `341 passed`, `RAW_EXIT=0`. Run 2 (verbatim, `-rsxX`): `341 passed in 272.19s (0:04:32)`, `RAW_EXIT_VERBATIM=0`, no `SKIPPED`/`XFAIL`/`XPASS` report lines emitted. `--collect-only -q` = `341 tests collected`. Collected == passed, so zero skips, xfails or errors. Arithmetic: 289 + 52 = 341. |
| **A2** `lint-skill` exit 0, 22 checks / 22 PASS | PASS | Re-run here: exit 0, 22 `[PASS]` lines, `"failed": []`. Key lines: `tables_wellformed: Parsed 19 phases, 8 gates, 14 migration rows`; `version_string_consistent: all four locations report v1.14`; `migration_covers_every_state_field: every field has a migration row`; `single_state_template: templates/state.json is the only host`; all eight `gate_registered_*` PASS. |
| **A3** `validate.py` exit 0 | PASS | `TRANSITION_VALID: complete=2/12 next=T02`, exit 0. This also re-verifies `docs/transition/control-plane.sha256` — no control-plane hash mismatch. |
| **A4 / N5** full 18-phase run leaves no `<repo>/.workflow` | PASS | `tests/test_units_workitem_runtime.py::test_a_full_run_leaves_no_repository_global_runtime` drives the real CLI through `run_happy_path`, asserts the traversal equals `EXPECTED_TRAVERSAL`, then `assert not (root/".workflow").exists()`, that **all six** `RUNTIME_FILES` exist under `workitems/<id>/.sdle/`, that `runtime` is literally `workitems/fixture-workitem/.sdle`, and that `state["workitem"]` is bound. Green in both full runs. Read in full, not taken from the handoff. |
| **A5 / N1-N4** two WorkItems, independent runs | PASS | `test_two_workitems_complete_independent_runs` runs the full 18-phase traversal for WI-A, snapshots `state.json` and `audit.md` as **bytes**, runs the full traversal for WI-B, then asserts both byte snapshots are unchanged and each state names its own WorkItem. N2 `test_each_workitem_keeps_its_own_audit_ledger` (both chains verify independently, cross-contamination string absent). N3 `test_manifest_build_under_one_workitem_leaves_the_other_alone`. N4 `test_a_lock_on_one_workitem_never_blocks_another` — TP-009's acceptance test: `foreign is False`, `warn is False`, B's `state get` exit 0 while A holds a fresh lock. |
| **A6** all six runtime files resolve under `workitems/<id>/.sdle/` | PASS | `Paths` property block (`scripts/sdle.py:104-165`): `state_file`, `audit_file`, `lock_file`, `execution_file`, `manifest_file`, `completion_file`, `evidence_dir` all derive from the single `runtime` property. Behaviourally pinned by the `RUNTIME_FILES` loop in N5 and by N19/N33. |
| **A7** no hardcoded runtime path in `scripts/sdle.py` | PASS | `grep -n '\.workflow' scripts/sdle.py` = 11 hits, each classified: `:121` the `legacy_workflow` property (the seam itself); `:662`, `:758`, `:1192` `paths.workflow.mkdir(...)` — the alias of `runtime`, not a literal; `:1039`, `:1769` docstrings; `:1883` a section comment; `:2127`, `:2137` the documented ARTIFACT_OWNERSHIP legacy-prefix bridge; `:3486` `SDLE_OWNED_PREFIXES` (legacy must stay owned); `:4285` `--help` text. The plan's `:3132` manifest relative path, `:3153` manifest filter and `:3240` `:(exclude).workflow` are **all gone** — replaced by `paths.manifest_file`, `paths.runtime_relative + "/"` and `f":(exclude){paths.runtime_relative}"`. E2 and E3 closed. |
| **A8** template at 1.14, version consistent, migration covers the field | PASS | `templates/state.json` = `"workflow_version": "1.14"` with `"workitem": null` as key 2. `lint-skill` `version_string_consistent: all four locations report v1.14` and `migration_covers_every_state_field: every field has a migration row`. |
| **A9** 14 `VERSION_MIGRATION` rows, terminal `1.13 → 1.14` | PASS | `lint-skill` `tables_wellformed: ... 14 migration rows`. `python scripts/sdle.py constants` → `version_chain` length **14**, first `['1.0','1.1']`, last `['1.13','1.14']`. |
| **A10** `migrate-workflow` satisfies the D8 steps; legacy SHAs identical | PASS | Code read end to end (`cmd_migrate_workflow`). All twelve steps present; step-11 reordering assessed separately below. Tests N19-N26 present and green; the legacy tree is compared by a full `sha256` map (`legacy_digests`) before and after on the happy path, on `target_exists`, on `legacy_audit_broken`, and on **every** crash parametrisation. |
| **A11** write fence denies `workitems/**` in both path forms, still denies `.workflow/**` | PASS | `.claude/hooks/hooks.py`: `FENCED = (".workflow", "workitems", "requirements", "guidance")`. `tests/test_hooks.py` parametrisation **adds** six cases (`/proj/workitems/index.md`, `/proj/workitems/wi-a/workitem.json`, `/proj/workitems/wi-a/.sdle/state.json`, `/proj/workitems/wi-a/.sdle/audit.md`, the bare relative form, and `C:\proj\workitems\wi-a\.sdle\state.json`) and **keeps** all five pre-existing `.workflow` cases. Nothing was replaced. |
| **A12** `implement preflight` ignores `workitems/**`; Phase 17 diff excludes the runtime | PASS | `SDLE_OWNED_PREFIXES` gains `"workitems/"`. `test_implement_preflight_does_not_count_the_workitem_tree_as_dirt` asserts `dirty is False` **and** `entries == []`. `test_the_phase_17_diff_excludes_the_workitem_runtime` asserts `src/app.py` is in the diff while `workitems/<id>/.sdle/` and `state.json` are not. |
| **A13** "must not change" list byte-identical to `7b9374b` | PASS | `git diff --exit-code 7b9374b -- scripts/sdle.sh scripts/sdle.ps1 .claude/settings.json .github/workflows/ci.yml .claude/skills/sdle/modules/ requirements/ docs/dry-runs/` → exit **0**. |
| **A14** `SKILL.md` diff touches only `VERSION_MIGRATION`, the version strings and prose | PASS | `git diff 6e8af8c ab889a1 -- .claude/skills/sdle/SKILL.md` = 7 insertions / 6 deletions in exactly five hunks: frontmatter `v1.13`→`v1.14`, heading `(v1.13)`→`(v1.14)`, one added `VERSION_MIGRATION` row, and three prose lines. `ARTIFACT_OWNERSHIP`, `PHASE_SEQUENCE`, `NEXT_PHASE`, `PHASE_LABEL_MAP`, `PROGRESS_MAP`, `PHASE_TO_GATE_KEY`, `GATE_TO_EXECUTION_PHASE` and the `approvals` key set are untouched (also independently confirmed by all eight `gate_registered_*` and the four phase-set lint checks). |
| **A15** TP-003 record; no skip/xfail/deletion/weakening | PASS with a note | See the test-weakening section. The only `^\+.*(skip\|xfail)` hit is `a.ok("manifest", "build", "--skip-tests")` — an SDLE CLI flag, not a pytest marker. The handoff's claim that this grep is "EMPTY" is inaccurate; the substance holds. |
| **A16** Python 3.11 / CI | **NOT_RUN / UNKNOWN** | Local interpreter is CPython 3.14.6. No 3.11 interpreter on this host; the branch is unpushed and CI has never run on it. **No outcome is predicted.** |

## Regression evidence

**Targeted regressions re-checked by reading the diff, not by trusting the table.**

- `git diff 6e8af8c ab889a1 -- tests/` touches six existing files plus one new file. Every hunk maps to a declared TP-003 category:
  - `test_units_state.py` (9/8): four lock-path literals → `Project.runtime`; `workflow_version` `1.13`→`1.14` in two places; whole-chain terminal step `1.12->1.13`→`1.13->1.14`; **one added** assertion `state["workitem"] == project.workitem`. Plan N17 satisfied — the chain test was extended in place, not duplicated. `test_migrate_refuses_unknown_version` and `test_migrate_is_idempotent` are untouched (plan P9).
  - `test_integration_01_happy_path.py` (2/2) and `test_integration_06_to_09.py` (5/8): path rebinding only. The Gate-7 manifest write at `test_06_gate_seven_refuses_a_manifest_without_scan_or_tests` now derives its relative path from `runtime.relative_to(root).as_posix()`, which also pins POSIX separators.
  - `test_units_transitions.py` (6/3): emitted `completion_summary` path derived from `runtime`, summary file path, and the `1.13`→`1.14` version assertion.
  - `test_lint_skill.py` (1/1): the drift fixture's replacement pair moves from `v1.13→v1.12` to `v1.14→v1.13`. The check under test is unchanged.
  - `test_hooks.py` (32/0): **additions only** — six write-fence parameters and two dirty-tree cases. Zero deletions.
- `test_init_infers_project_name_from_first_heading` is **not** in the diff — plan §7.1's first named case is green unmodified, and `test_project_name_still_prefers_the_requirements_heading` adds a second guard on the same precedence decision.
- `python -m pytest --collect-only -q` per file: `test_hooks.py` 37, `test_integration_01` 8, `test_integration_02_to_05` 42, `test_integration_06_to_09` 38, `test_lint_skill` 17, `test_units_cli` 9, `test_units_infra` 28, `test_units_state` 37, `test_units_transitions` 24, `test_units_workitem` **57**, `test_units_workitem_runtime` **44**. Total 341. `test_units_workitem.py` still collects exactly the 57 T01 cases.

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `python -m pytest -q` (run 1) | **RAW EXIT 0** | `341 passed` |
| `python -m pytest -q -rsxX` (run 2, verbatim) | **RAW EXIT 0** | `341 passed in 272.19s (0:04:32)`; progress line all dots across five rows; no `s`, `x` or `X` characters and no short-summary section, so zero skipped/xfailed/xpassed |
| `python -m pytest --collect-only -q` | 341 | `341 tests collected in 0.17s` |
| `python scripts/sdle.py lint-skill` | **exit 0** | 22 checks, 22 PASS, `"failed": []` |
| `python scripts/sdle.py constants` | exit 0 | `version_chain` 14 rows, terminal `['1.13','1.14']` |
| `python tools/transition/validate.py` | **exit 0** | `TRANSITION_VALID: complete=2/12 next=T02` |
| `git diff --exit-code 7b9374b -- <must-not-change list>` | exit 0 | byte-identical |
| `git check-ignore -v workitems/wi-a/.sdle/lock workitems/index.md workitems/wi-a/workitem.json workitems/wi-a/.sdle/state.json workitems/wi-a/.sdle/evidence/x.json` | one line | `.gitignore:9:workitems/*/.sdle/lock` only. Registry, identity, state and evidence are all **versioned** — contract §19 satisfied in both directions. |
| Python 3.11 | **NOT_RUN** | no 3.11 interpreter on this host |
| CI (`ubuntu-latest`, `windows-latest`, Python 3.11) | **NOT_RUN / UNKNOWN** | branch unpushed; CI has never run on it. No outcome predicted. |

## Future-phase leakage check

`git diff 6e8af8c ab889a1 -- scripts/sdle.py .claude/hooks/hooks.py`, added lines only,
grepped for `SPECIFY_`, `sdle start`, `rev-parse`, `symbolic-ref`, `branch`,
`current_feature_id`, `audit.jsonl`, `.sdle/(config|policies|baseline)`, `iterdir`,
`glob(`. **Two hits, both benign:**

- a comment stating that CWD, branch, persisted context and inference are **T03**;
- `_git_value(paths, "rev-parse", "HEAD")` used solely to stamp `gitHead` into
  `evidence/migration-*.json`. That is contract §20.5 ("capture source SHA/state"),
  not T03's "record branch and starting SHA" for the workflow itself. No branch is
  read anywhere.

Confirmed absent: any CWD/branch/persisted-context/AI resolution (T03); `sdle start`
(T03); `SPECIFY_INIT_DIR`/`SPECIFY_FEATURE_DIRECTORY`, `current_feature_id` demotion,
`ARTIFACT_OWNERSHIP` **table** edits, artefact relocation under `workitems/` (T04); any
repository-root `.sdle/` (T05); `audit.jsonl` or structured JSONL events (T06); any
change to `PHASE_SEQUENCE`, `NEXT_PHASE`, `PROGRESS_MAP`, `advance`, `skip`, `restart`,
`doctor`, `phase_history` (T07); `.sdle/baseline.*` (T08); `GATE_PHASES`,
`PHASE_TO_GATE_KEY` or the `approvals` key set (T09); any product skill/subagent (T10);
removal of `.workflow/` support, of rung 3, or of the migration command (T11). The
`is_dir()` uniqueness nit (E18) is deliberately **not** fixed, as planned.

The resolution ladder stops at rung 5 — `bind_workitem` has exactly five branches and
no sixth inference path.

## Test weakening / deletion check

**No test was weakened, skipped, xfailed or deleted.**

- `git diff 6e8af8c ab889a1 -- tests/ | grep '^-def test_'` yields exactly one line:
  `-def test_init_records_no_workitem_in_state`. It is a **rename with an inverted
  assertion**, not a deletion: `test_init_records_the_resolved_workitem_in_state`
  replaces it in the same hunk and asserts *more* (the field value, the state file's
  location under the WorkItem, and that no `.workflow/` was created). T01's guard
  asserted no `workitem` key may exist; contract §8 makes T02 the phase required to
  create it, so inverting the guard is mandatory, not convenient. Category 2.
- Collected count for `test_units_workitem.py` is still **57**, matching T01 exactly.
- `grep '^\+.*(skip|xfail)'` over the tests diff: one hit, `--skip-tests`, an SDLE CLI
  flag. No `pytest.mark.skip`, `skipif`, `xfail` or `pytest.skip(` was added anywhere.
- The two `test_hooks.py` `.workflow` write-fence parameters were **kept**, not
  replaced, so the legacy fence is still regression-covered.

### Divergence 3 — the shared-fixture conflict, independently checked

The claim is that all 57 `test_units_workitem.py` assertions are byte-identical to T01.
`7b9374b..6e8af8c` does not touch that file, so `git diff 6e8af8c ab889a1 --
tests/test_units_workitem.py` **is** the whole T01→T02 diff. It contains exactly four
hunks, and nothing else:

1. module docstring (T01's version claimed `.workflow/` is still the runtime and that
   `init` neither requires nor records a WorkItem — both false after C1/C2/C5);
2. a new module-scoped `project` fixture returning `bare_project`;
3. removal of the file-scoped `isolated_git_identity` fixture (promoted verbatim to
   `conftest.py`, same three env vars, now autouse for the whole suite);
4. the two declared superseded cases.

No other assertion line appears in the diff. `bare_project`'s body is the pre-T02
`project` fixture body verbatim — the conftest diff renames the `def` line and rewrites
only the docstring; the body lines are context, not changes. So the 55 untouched cases
run against an equivalent environment with byte-identical assertions. **Divergence 3 is
a correct reconciliation of a genuine plan self-contradiction (§6 vs §7.1), reported
rather than silently absorbed.** The plan could not be satisfied literally.

## Deterministic guardrail check

**Fail-open hunting — the resolution ladder.** `bind_workitem` is a pure function that
either returns a bound `Paths` or raises `Refused`; it prints nothing and writes
nothing, which is why the hook can call it speculatively.

- Rung 1 refuses `workitem_unknown` for any id absent from `workitems/index.md`; it
  never falls through to another rung. (`test_rung1_an_unregistered_workitem_is_refused`)
- Rung 2 binds only when `len(known) == 1`.
- Rung 3 is inside `if not known:` — structurally reachable **only** with zero
  registered WorkItems, exactly as F3 requires. It is intact and load-bearing:
  `test_rung3_legacy_state_stays_readable_when_no_workitem_exists` proves an existing
  pre-v1.14 repository is still readable, which is what stops T02 bricking it before
  `migrate-workflow` can run.
- Rung 4 refuses `workitem_required` and names `workitem create`.
- Rung 5 raises `workitem_ambiguous` with `{"workitems": known}` — **it never picks**.
  `test_rung5_two_workitems_and_no_flag_refuses_and_never_picks` additionally asserts
  that *neither* candidate's `.sdle/` and no `.workflow/` was created.
- `init` never takes rung 3: the `for_init` guard is the **first** statement in the
  function, before `known` is even read, so the refusal is unconditional in the
  registered-count. Two tests pin both halves (zero WorkItems, and one registered).
- `RUNTIME_FREE_COMMANDS` is a closed five-member frozenset. `scan` and `preflight`,
  both of which persist state, are deliberately **not** in it. The exemption is tested
  as a list, not a hole: `test_a_runtime_command_still_refuses_in_that_same_repository`
  runs `constants` (exit 0) and `state get` (`workitem_required`) in the same repo.
- F10 is honoured: every ladder test builds from `bare_project`, so the shared
  one-WorkItem fixture cannot mask a resolution bug.

**Write fence.** `FENCED` gains `workitems` with a reason string that explicitly names
the registry, identity and runtime and leaves a note for the phase that later moves
artefacts under `workitems/`. `.workflow` stays fenced with an updated reason naming
`migrate-workflow`. Both path forms tested.

**Dirty-tree hook.** Now calls `engine.bind_workitem(paths)` inside the pre-existing
`try/except Exception: return`. `Refused` is an `SdleError` subclass, so ambiguity
returns silently rather than crashing the tool call. Three cases pinned: fires with one
WorkItem, silent with two, silent with none. See non-blocking finding NB-3.

**`write_atomic`.** Byte-identical to `6e8af8c` (not in the T02 diff). P3 preserved.

**Audit.** `verify_audit_chain` is a genuine lift-and-shift: the extracted body is the
same `re.search(r"^\*\*Prev:\*\*\s*(\S+)\s*$", ...)` walk with the same `GENESIS` seed
and the same `_entry_digest` chaining; `cmd_audit_verify` now calls it and its
`matches`/`broken_at` semantics, `expected is None` short-circuit, exit codes and
stderr line are otherwise unchanged. Format, `prev_sha` chaining, whole-file
`audit_sha`, tamper halt and rebaseline are untouched — only the path moved (D4, P4).

## State / audit / evidence integrity check

**Schema.** One new top-level key `workitem`, placed second; `CURRENT_VERSION` 1.13 →
1.14; one new `MIGRATIONS` row; `_mig_1_13` derives the value **deterministically from
where the file lives** (`parent.name == ".sdle"` → `parent.parent.name`), never from a
guess, and leaves `null` at the legacy location. `migrate_state` remains pure
in-memory. Both directions tested (N15, N16). `migrate_refuses_unknown_version` and
`migrate_is_idempotent` untouched.

**`migrate-workflow` — legacy immutability (F5, §8.9).** Code-read: inside
`cmd_migrate_workflow` the `legacy` `Paths` is used only for `.is_file()`,
`.read_text()` and `sha256_file()`. Every `write_atomic` target is `target.*`,
`evidence_file` or `workitem.json` under the target. `append_audit(target, ...)`
mkdirs `target.runtime`. There is no `unlink`, `rename`, `replace`, `rmtree` or `move`
touching `legacy`. Behaviourally, `legacy_digests()` hashes **every file** under
`.workflow/` recursively and is compared before/after on the happy path, the
`target_exists` refusal, the `legacy_audit_broken` refusal, and all four crash
parametrisations. CONFIRMED.

**Torn migration (F4).** `append_audit` writes **only** `audit.md` and mutates
`state["audit_sha"]` in memory (`scripts/sdle.py:743-781`) — it does not call
`save_state`. Therefore `write_atomic(target.state_file, ...)` remains the single,
last pre-verification write, and it is the sole commit marker. Everything before it is
a whole-file overwrite, so a re-run is safe. On step-9 mismatch the marker is removed
(`target.state_file.unlink(missing_ok=True)`) and legacy stays authoritative.

**Divergence 2 — the reordered `workflow_migrated` entry: judged CORRECT, and the
literal D8 order would have been a defect.** `append_audit` rebaselines `audit_sha`
into the state dict. Appending after the commit write would leave the committed
`state.json` carrying the pre-append `audit_sha`, so `audit verify` would return exit 3
immediately after a *successful* migration. The property D8 actually relies on — target
`state.json` written last, sole commit marker — is preserved exactly, and is what the
parametrised crash test proves. The entry lands in the **target** ledger, satisfying
§20.12 / §8.8. This is a refinement of the plan's step numbering, not a weakening of
its guarantee.

**Evidence.** `evidence/migration-<executionId>.json` records `migratedFrom`, `at`,
`executionId`, `workitem`, `legacyStateSha`, `legacyAuditSha`, `gitHead` and
`sdleVersion` — §20.5 and §8.8 satisfied. `workitem.json` gains a `migration` object
(§8.5). Both asserted by `test_migrate_records_evidence_metadata_and_a_target_audit_entry`,
which also checks the WorkItem's own `id` is untouched.

**Refusal paths, all verified to write nothing to the target:** `workitem_unknown`,
`target_exists`, `legacy_state_missing`, `legacy_state_invalid` (bad JSON **and**
unknown `workflow_version`, both exit 3), `legacy_audit_broken` (exit 1, names
`audit rebaseline`), `migration_verify_failed` (exit 3, rolls the marker back).

**Governed-artifact SHA / review freshness.** Not applicable as a product concern at
T02 — governed-artifact review binding is T06 (contract §12, TP-011), and T02 changes
no gate fingerprinting. The transition control plane's own integrity manifest
`docs/transition/control-plane.sha256` was re-verified by `validate.py` (exit 0, no
mismatch), and `tools/transition/agent_guard.py` matches its recorded hash.

## Cross-platform / path handling check

- `Paths.runtime_relative` is the single producer of every emitted relative runtime
  path and every git pathspec, and it normalises `os.sep` → `/`. Consumers verified:
  the manifest `relative` string, the manifest `changed` filter (which also normalises
  the incoming `\` before comparison), the Phase 17 `:(exclude)` pathspec,
  `write_completion_summary`, the `migrate-workflow` envelope, and four refusal
  strings.
- Write-fence matching normalises backslashes; the new tests assert both the POSIX and
  the `C:\...` forms.
- Test-side path assertions use `runtime.relative_to(root).as_posix()` rather than
  string concatenation.
- Stdlib only; no new dependency. 3.11-safe by inspection: `from __future__ import
  annotations` already present, `str | None` only in annotations, no `match`, no PEP 695
  generics, no `Self`; `dataclasses.replace` (3.7+), `Path.unlink(missing_ok=True)`
  (3.8+), `frozenset`, `time.sleep`. Nothing 3.12+ was introduced.
- `lint-skill` `no_powershell_only_cmdlets` PASS.
- **This does not make Python 3.11 or CI observed.** Both stay `NOT_RUN` / `UNKNOWN`.

## Duplicated-sources-of-truth check

- `single_state_template` PASS — one template.
- Four phase tables and the migration table remain in `SKILL.md` alone; only
  `VERSION_MIGRATION` changed.
- The runtime location now has exactly **one** definition in the engine
  (`Paths.runtime`); `workflow` is a documented alias, not a second definition. The
  three literals that bypassed the properties are deleted.
- `workitems/index.md` remains the only source for registered ids —
  `registered_workitem_ids` projects the index and never lists the directory, so E17/E18
  hold and no directory-scanning inference entered.
- `tests/conftest.py` re-derives `runtime` for assertions; that is an intentional
  independent oracle in the test harness, not a second product definition.

## Divergence 1 — the Gate 7 `ARTIFACT_OWNERSHIP` re-point

**Judgement: legitimate, not a way around the constraint.**

1. The forbidden thing did not happen. `ARTIFACT_OWNERSHIP` in `SKILL.md` is
   byte-identical to `7b9374b`; `gate_implement` still reads
   `.workflow/implementation-manifest.md`. P1/A14/§14 are intact.
2. It is single-sited. The translation lives inside `resolve_artifact_path`, the one
   function that resolves templates, and all seven call sites now pass `paths`. No
   caller concatenates a WorkItem path — which is precisely what contract §8's "No
   command should infer WorkItem-owned paths by concatenating strings independently"
   demands.
3. It is the same class of transformation the function already performs. The body
   already substitutes `{current_feature_id}` and `{security_review_artifact}` from
   state. Substituting the runtime prefix from `paths` is not a new source of truth;
   the table stays the source, the resolver stays the translator.
4. It is behaviour-preserving on the legacy path. Under legacy binding
   `runtime_relative == ".workflow"`, so the resolved string is byte-identical to
   pre-T02.
5. Exactly one template carries the prefix, so the rewrite has a blast radius of one.
6. The alternative was a real regression: without it every Gate 7 approval refuses
   `artifact_missing`. Choosing between "edit a table the plan forbids" and "ship a
   broken gate" by translating at the single resolution seam is the smallest change
   that satisfies both constraints (§24.3 item 4).
7. It is commented as transitional and names the phase that removes it.

Residual risk recorded as NB-1.

## Divergence 4 — post-migration `init` refusal

**Judgement: deliberate, recorded, and fail-safe — not an accident.** Evidence, in
authority order: plan D2 states the unconditional form and its rationale in full; C4
restates it as a deliberate behavioural change; plan §14's T11 row lists "Removing
`.workflow/` support, removing rung 3, removing the migration command" as T11-owned;
N13/N13b were written to pin it; the handoff calls it out under "Deliberate behavior
changes" and "Known limitations"; the progress note repeats it. The direction is
refusal, and the rationale (an orphaned workflow that is simultaneously unbindable and
unmigratable) is sound and independently reproducible from the code.

One consequence the plan did not anticipate is recorded as NB-2.

## Findings

### Blocking

**None.**

### Non-blocking

- **NB-1 — `resolve_artifact_path`'s `.workflow/` prefix is now magic.** Any future
  `ARTIFACT_OWNERSHIP` template beginning `.workflow/` would be silently rewritten to
  the WorkItem runtime. Today exactly one template matches and the rewrite is correct
  for it. The phase that moves the table (T04) must delete the bridge rather than
  inherit it. Already commented as transitional in the source.
- **NB-2 — the `legacy_workflow_present` refusal names an incomplete remedy.** The
  message says only "`migrate-workflow --workitem <id>`". After a migration has already
  happened, `.workflow/` still exists (correctly — §8.9), so `init` for a *second*
  WorkItem refuses; following the message's advice would run `migrate-workflow` again
  and **clone** the already-migrated legacy workflow into the new WorkItem instead of
  starting a fresh one. The real remedy — archiving `.workflow/` by hand — is never
  named. Not a contract violation (no MUST forbids repeated migration, and the target
  is verified and independent), not data loss, and not fail-open; it is a UX/message
  gap. Recommend T11 carries it alongside the removal of `.workflow/` support.
- **NB-3 — the dirty-tree tripwire cannot fire in a multi-WorkItem repository.** The
  hook must resolve a WorkItem to find `state.json`, and `bind_workitem` correctly
  refuses rather than guesses, so with two or more registered WorkItems the guard is
  silent. This is planned (N30), tested, and the correct fail-safe posture for a hook
  that cannot know which workflow it is looking at, but it is a genuine reduction in
  tripwire coverage that only T03's real resolution can restore. It should be on T03's
  input list.
- **NB-4 — `migrate-workflow`'s post-commit `workitem.json` write is outside the commit
  window.** If the process dies between the `state.json` commit and the metadata write,
  the target resolves and is authoritative but carries no `migration` object, and a
  re-run refuses `target_exists`. §8.5's "update WorkItem metadata" would then be
  unfulfilled. Impact is bounded: `evidence/migration-*.json` and the
  `workflow_migrated` audit entry both survive, so the migration is still fully
  evidenced. Not covered by the crash test (which stops at the commit write).
- **NB-5 — the crash test does not exercise the manifest or completion-summary copies.**
  Plan N21 asks for "N = 1..k covering each copied file". The `legacy_workflow` fixture
  stops at Gate 1, so neither `implementation-manifest.md` nor `completion-summary.json`
  exists. The injector raises when `n > fail_after`, so `fail_after=1..4` injects the
  failure at writes **#2 to #5** — the evidence file, `execution.json`, the audit append
  and the commit write. Write #1, the audit copy, is never injected (`fail_after=0` is
  not parametrised); its failure is trivially safe because nothing has been written to
  the target at that point. The two optional copies are the same whole-file-overwrite
  pattern before the commit marker, so the safety property is unchanged; the gap is in
  coverage, not behaviour.
- **NB-6 — two handoff figures do not match the committed tree.** (a) The handoff's
  diff-scope table reports `tests/test_units_workitem.py 34/22`; the commit is
  **46/29**. Every extra hunk maps to a declared category (the promoted
  `isolated_git_identity` removal and the fixture override), so this is stale evidence
  written before the final edits, not undeclared scope. (b) The handoff states the A15
  grep is "EMPTY"; it actually returns one line, `--skip-tests`, which is a CLI flag
  and not a pytest marker. Both are accuracy defects in the handoff, not in the
  implementation. Contract §24.3 item 9 requires recorded results to be actual; a
  future implementer should regenerate numstat figures after the final edit.
- **NB-7 — out of scope, observed in passing.** The comment added by `6e8af8c` inside
  `write_atomic` contains a stray word ("`ponytail:`"). It belongs to the out-of-band
  retry commit, not to T02, and has no behavioural effect.

## Guard refusals

**None.** `tools/transition/agent_guard.py verifier` refused no operation during this
verification. Every command run here was observational (`git diff/show/status/
check-ignore/log`, `grep`, `sed -n`, `cat`, `ls`, `python -m pytest`,
`python scripts/sdle.py lint-skill|constants`, `python tools/transition/validate.py`).
No mutation, no interpreter-based workaround, no alternate shell was used to reshape a
blocked command.

One environment note, unrelated to the guard: a global token-optimising shell proxy
(`rtk`) summarises command output and was truncating `git diff` and `grep` results. It
was bypassed with its own documented passthrough, `rtk proxy "<command>"`, which
changes nothing about what is executed and leaves the transition guard fully in force —
the guard evaluates the submitted command text either way. The two full-suite runs were
executed both ways and agree: `341 passed`, raw exit `0`.

## Final result rationale

Both contract §8 exit criteria are demonstrated by driving the real CLI, not by reading
the handoff: a complete 18-phase run leaves no `<repo>/.workflow` and places all six
runtime files under `workitems/<id>/.sdle/`, and two WorkItems complete independent
18-phase runs with the first one's `state.json` and `audit.md` byte-unchanged
afterwards. Repository-global locking has ended by construction — the lock path is no
longer repository-global — and TP-009's acceptance test passes.

All sixteen acceptance criteria are met (A16 correctly recorded `NOT_RUN`). The suite is
green at raw exit 0 in two independent full runs, 341 collected and 341 passed with zero
skips, xfails or errors; `lint-skill` is 22/22 at v1.14 with 14 migration rows; and
`validate.py` exits 0 including the control-plane hash manifest. No phase or gate table
changed. No guardrail was removed: the write fence widened, the dirty-tree guard and
`SDLE_OWNED_PREFIXES` were adapted rather than dropped, the audit chain and `write_atomic`
are untouched, and the legacy `.workflow/` runtime is provably never written to.

The resolution ladder is fail-safe at every rung: it refuses on ambiguity and lists
candidates rather than choosing, rung 3 is structurally reachable only with zero
registered WorkItems, and `init` refuses unconditionally while a legacy runtime exists.
The transitional dual-read rung — the thing that stops an existing repository being
bricked before T11 — is present, exercised and correct.

Of the four declared divergences, three are correct readings of a constraint the plan
stated imprecisely or self-contradictorily (the Gate 7 resolver bridge, the audit-entry
ordering, and the §6-versus-§7.1 fixture conflict), and the fourth is the plan's own
explicit fail-safe decision. Each was declared rather than absorbed, which is what
§24.3 item 2 requires. None of them weakens a guarantee.

No test was weakened, skipped, xfailed or deleted; the single removed `def` is a rename
that strengthens its assertion, and the collected count per file confirms nothing was
lost. The seven non-blocking findings are documentation gaps, coverage gaps and stale
handoff figures. None of them changes the behaviour of the shipped engine, and none
justifies withholding the phase.

The single authoritative result line for this artifact is the `**Result:**` line in the
header block above, and it reads PASS. No other line in this file is a result
declaration.
