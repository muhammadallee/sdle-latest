# T04 Independent Verification — Attempt a01

**Phase:** T04 — Bind Spec Kit to the Active WorkItem (contract §10)
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

> The handoff is a claim set, not proof. Every figure below was produced by a command run in **this**
> verification context, or read from the file/commit named. Nothing is copied from the handoff or
> from any checkpoint narrative.

**Commit verified:** `82e6a68` ("T04: bind Spec Kit to the active WorkItem (IMPLEMENTED, NOT YET
VERIFIED)"), which is HEAD of `transition/workitem-v1`.
**Prior-phase baseline / rollback point:** `beb28f2` (T03, verified PASS). Product baseline `f8fdaa0`.
**Working tree at verification time:** `M .claude/settings.local.json` only — the user's permission
allowlist, declared out of scope and correctly excluded from the commit.

---

## Scope and identity integrity

| Check | Result | Independent evidence |
|---|---|---|
| The commit under verification is HEAD | OK | `git log --oneline -8` → `82e6a68` first |
| The plan was not mutated by the implementation | OK | `git diff --name-only fe856d1 82e6a68 -- docs/transition/phases/T04-plan.md` → **empty** |
| The transition control plane was not mutated | OK | `git diff --name-status fe856d1 82e6a68` lists no file under `tools/transition/`, `docs/transition/templates/`, `.claude/agents/`, `.claude/skills/apply-sdle-transition/`, or `transition.md`; `validate.py` re-verifies every manifest hash and exits 0 |
| T04's own commit scope | OK | `git diff --name-status fe856d1 82e6a68` = 9 product/doc `M`, 1 engine `M`, 9 test `M`, 1 test `A`, 7 control-plane-evidence `A`/`M`. `docs/transition/RESUME.md` and `T03-verification-a01.md` appear only in `beb28f2..82e6a68` because they belong to the intervening T03-verification and cold-start commits, **not** to T04 |
| `T04-checkpoint-a01-07.md` never written | CONFIRMED | `ls docs/transition/phases/` → checkpoints `01`–`06` only. M7 evidence therefore has no checkpoint corroboration and was re-derived from scratch here rather than accepted |
| Checkpoint claims vs disk (drift probe across the three implementing contexts) | OK | Checkpoint 05's claims re-checked on disk: `tests/test_units_speckit_binding.py` exists and collects **53**; `phase-execution.md` carries **8** `feature bind` lines; the declared `.workflow/` residual in that file is present exactly as described. No checkpoint claim was contradicted by disk |

---

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **A1** full suite green, collected == passed, no skips/xfails/errors | **MET** | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` → **`498 passed in 963.95s (0:16:03)`**, background-runner reported **exit code 0**; `grep -c "short test summary"` on the captured run = **0**; `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` → **`498 tests collected in 0.41s`**, `COLLECT_RAW_EXIT=0`. Collected == passed |
| **A2** `lint-skill` 22 PASS / 0 FAIL, 15 migration rows, v1.15 | **MET** | `python scripts/sdle.py lint-skill` → `RAW_EXIT=0`, 22 `[PASS]` lines, 0 `[FAIL]`, `data.failed == []`, `tables_wellformed: Parsed 19 phases, 8 gates, 15 migration rows`, `version_string_consistent: all four locations report v1.15`, `migration_covers_every_state_field: every field has a migration row` |
| **A3** template carries `specKit` with exactly four keys, `1.15`, no `current_feature_id` | **MET** | `git diff beb28f2 82e6a68 -- .claude/skills/sdle/templates/state.json` read in full: `"workflow_version": "1.15"`; `current_feature_id` deleted; `specKit` added with exactly `featureId`, `featureDirectory`, `workflowId`, `runId`, all null |
| **A4** NB-1 discharged; `.workflow` count not larger | **MET** | `grep -n 'legacy_prefix' scripts/sdle.py` → **no output, exit 1**. `grep -c '\.workflow' scripts/sdle.py` = **12**; `git show beb28f2:scripts/sdle.py \| grep -c '\.workflow'` = **12** |
| **A5** 15 migration tuples, terminal `("1.14","1.15",_mig_1_14)`, `CURRENT_VERSION == "1.15"` | **MET** | `MIGRATIONS` block extracted from both trees and printed: 15 tuples, terminal `("1.14", "1.15", _mig_1_14)`; `grep -n 'CURRENT_VERSION = '` → line 676, `"1.15"` |
| **A6** `current_feature_id` grep | **MET WITH DECLARED EXCEPTIONS — verifier concurs** | Re-derived: `grep -rn --binary-files=without-match 'current_feature_id' scripts/ .claude/ README.md docs/SDLE-Reference-Guide.md CLAUDE.md` → **10** lines, identical to the handoff's table. Nine are structurally required (the `_mig_1_0` / `_mig_1_1` code bodies, `_mig_1_14`'s `state.pop`, two explanatory comments, `SKILL.md` rows 213/214/227, the README v1.15 history row, the Reference-Guide 1.4 revision row). The tenth is `modules/gate-protocol.md:66`, frozen byte-unchanged by A16. **A6 as literally worded is unreachable** — the migration chain replays history verbatim, so the code bodies must name the field — and is a plan defect, not an implementation gap. See the explicit A6-vs-A16 ruling below |
| **A7** pre-1.15 state readable without traceback | **MET (plan wording defect confirmed)** | `python scripts/sdle.py --help` enumerates **36** subcommands; **`status` is not among them** — the plan named a subcommand that does not exist. The readers A7 means are covered by `test_n8_a_state_with_no_speckit_key_is_readable`, parametrised over `state dump`, `header`, `gate show --gate gate_spec`, `artifact path --gate gate_spec`, each asserting exit 0 and `"Traceback" not in stderr`; all four passed in the full suite. Structurally guaranteed by `speckit_ref(state)` defaulting every key, with no direct `state["specKit"]` subscription anywhere (`grep -n 'speckit_set(\|speckit_ref('` shows the only writers are `_mig_1_14` and `cmd_feature_resolve`) |
| **A8** missing capability refuses, names both, no `env`, state byte-unchanged | **MET** | `test_n4_a_missing_capability_refuses_and_writes_nothing` parametrised over `()`, `("SPECIFY_INIT_DIR",)`, `("SPECIFY_FEATURE_DIRECTORY",)` asserts `speckit_capability_missing`, exact `data.missing`, `data.probed_root == ".specify/scripts"`, `"env" not in data`, and byte-identical `state.json`; passed. Source read: `cmd_feature_bind` raises before it reads state at all |
| **A9** three subcommands refuse `workitem_ambiguous`; `RUNTIME_FREE_COMMANDS` byte-identical | **MET** | `RUNTIME_FREE_COMMANDS` block extracted from `beb28f2` and `82e6a68` and compared → **identical**, `feature` absent. `test_n2b`/`test_n2c` ×3 subcommands passed. Verified **live** in this repository (no WorkItems registered): `python scripts/sdle.py feature bind` → `workitem_required`, exit **1**; `feature capabilities` → `workitem_required`, exit **1**. Resolution demonstrably precedes any Spec Kit work |
| **A10** two WorkItems, distinct directories, first byte-unchanged | **MET** | `test_n12_two_workitems_run_the_full_flow_against_their_own_speckit_context` drives both to `complete` and asserts A's `state.json`, `audit.md` and `specs/` SHA map byte-unchanged after B's run; `test_n1_each_workitem_records_its_own_feature_directory` asserts the same for the resolve step. Both passed |
| **A11** adoption leaves exactly one copy, SHA preserved, audited | **MET** | `test_n5_adoption_moves_the_directory_and_leaves_exactly_one_copy` asserts `list(root.rglob("spec.md")) == [target]`, pre/post SHA equality and source removal; `test_n6_adoption_is_audited_with_from_and_to` asserts the `speckit_feature_adopted` entry **and** `audit verify → matches is True`. Source read: `_adopt_feature_directory` uses `shutil.move` — a move, never a copy |
| **A12** `feature_target_exists` / `feature_adopt_failed` leave the source intact | **MET** | `test_n6_an_occupied_target_refuses_without_touching_either_side` and `test_n6_an_oserror_during_the_move_refuses_with_the_source_intact` (monkeypatched `shutil`), both asserting `source.is_file()` and unchanged state. Passed |
| **A13** `feature bind` purity; SDLE never writes `feature.json` | **MET** | `test_n11_feature_bind_writes_nothing_on_any_path` takes a recursive SHA map of the **whole project root** before and after, parametrised over success + three refusal paths; passed. `grep -rn 'feature\.json' scripts/ .claude/` → **no match** |
| **A14** write fence allow/deny set | **MET** | `tests/test_hooks.py` parametrize lists read directly: allow now carries `/proj/workitems/wi-a/specs/001-todo-api/spec.md`, the repo-relative form and the Windows backslash form, and still carries `/proj/.specify/specs/001/spec.md`; deny still carries `workitems/index.md`, `workitem.json`, `.sdle/state.json`, `.sdle/audit.md` plus new `.sdle/lock`, `reviews/…` and two near-misses (`workitems/wi-a/specs.md`, `workitems/specs/not-a-workitem.md`). 44 hook tests collected, all passed |
| **A15** no `speckit-` / `/speckit.` in added lines | **MET** | `git diff beb28f2 82e6a68 -- . ':(exclude)docs/transition/'` piped through `grep '^+'` then `grep -nE 'speckit-\|/speckit\.'` → **0 matches**. `feature --help` inspected live: no skill name, no slash command. `speckit_present` / `speckit_skill_prefix` JSON keys unchanged |
| **A16** must-not-change paths byte-identical | **MET** | `git diff --exit-code beb28f2 82e6a68 -- scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .claude/settings.json .github/ docs/dry-runs/ docs/architecture/ requirements/ .gitignore .claude/skills/sdle/modules/gate-protocol.md` → **exit 0**. `.claude/commands/` shows exactly one `M`: `sdle-reset.md` |
| **A17** TP-003 | **MET** | `git diff --name-status beb28f2 82e6a68 -- tests/` → **9 `M`, 1 `A`, zero `D`, zero `R`**; the only `A` is `tests/test_units_speckit_binding.py`. `tests/conftest.py` diff is `+10 −0` and contains **only** `Project.specs_root`, `Project.feature_dir()` and module-level `FEATURE_ID` — exactly the anti-contradiction clause's single permitted edit, with no fixture added, removed, renamed or re-scoped. Two `M` rows (`test_lint_skill.py`, `test_units_state.py`) are outside the plan's "Existing tests affected" table but are justified in the handoff's TP-003 table and are pure version-literal updates; see finding N-8 |
| **A18** no future-phase leakage | **MET** | `grep '^+'` over the non-transition diff then `grep -nE 'policies/\|flow_id\|risk_tier\|classification\|\.sdle/config\|brownfield\|adaptive\|subagent\|ACTIVE_CONTEXT_SETTERS\|pending_branch_ack'` → **0 matches**. `ls -d .sdle` → does not exist. `legacy_workflow_present` still raised at `scripts/sdle.py:2346` and pinned by three unchanged tests; `cmd_migrate_workflow` byte-identical to `beb28f2`; the `.workflow/` dual-read rung pinned by `test_n9_workitem_runtime_resolves_to_workflow_under_the_legacy_binding` and `test_n7_the_legacy_binding_keeps_its_baseline_behaviour` |
| **A19** `validate.py` exit 0 | **MET** | `python tools/transition/validate.py` → `TRANSITION_VALID: complete=4/12 next=T04`, `RAW_EXIT=0` (includes full `control-plane.sha256` re-hashing) |
| **A20** `workflowId` / `runId` never non-null | **MET** | `grep -n 'workflowId\|runId' scripts/sdle.py` → exactly 3 hits: the `SPECKIT_REF_KEYS` tuple (725), a docstring (748), and `workflowId=None, runId=None` in `_mig_1_14` (1206). `cmd_feature_resolve` passes only `featureId`/`featureDirectory`. Asserted after a full two-WorkItem run by `test_n12…` |
| **A21** Python 3.11 / CI recorded NOT_RUN | **MET** | Host interpreter is Python 3.13.0; no 3.11 present; the branch is local-only and no CI run has been observed. **No outcome is predicted** for either |

---

## Contract §10 required tests — verified, not accepted

| §10 requirement | Verified how |
|---|---|
| WorkItem A's Spec Kit output cannot be mistaken for WorkItem B's | `test_n1_each_workitem_records_its_own_feature_directory` (A's state, audit and specs SHA map byte-unchanged while B runs) and `test_n1_another_workitems_newer_directory_is_never_a_candidate`. Source read: no tier reaches into `workitems/<other-id>/` — tier 1 is `paths.speckit_specs_root` (this WorkItem only), tier 2 is `<root>/specs`, tier 3 is `.specify/specs`. Structural containment confirmed. **Residual: tier 2 is a repository-global staging area — see finding N-2** |
| WorkItem resolution precedes Spec Kit invocation | Structural: `feature` is absent from `RUNTIME_FREE_COMMANDS` (block byte-identical to `beb28f2`), so `bind_workitem` runs before any `feature` handler is entered. Confirmed **live** in this repository: `feature bind` and `feature capabilities` both refuse `workitem_required` with exit 1 before touching `.specify/`. `test_n2a`–`test_n2d` passed |
| Branch alone does not define Spec Kit context | `test_n3_the_bound_workitem_wins_over_a_branch_naming_another` (real `git checkout -b wi-a` while bound to `wi-b`); `test_n3_a_stale_global_feature_slot_changes_nothing_and_is_never_written` (writes a real `.specify/feature.json` naming A, takes a recursive SHA map of `.specify/` before and after a full bind + resolve cycle, and asserts it unchanged); `test_n3_a_gate_refuses_another_workitems_artifact` (`feature_outside_workitem`, `expected_prefix == "workitems/wi-b/specs/"`, approval not recorded). All passed |
| Missing required Spec Kit capability fails closed | Source read: `detect_speckit_capabilities` defaults every capability to `supported: False` and only flips on a literal name match inside a `.py`/`.sh`/`.ps1` file under `.specify/scripts/`; an unreadable file `continue`s, keeping the closed default; `cmd_feature_bind` raises `Refused` (exit 1) before reading state. `test_n4_*` (5 tests + 3 parametrisations) passed, including the "no `.specify/scripts/` at all" and "`.specify/` absent" cases and the positive control |
| Native artifacts are not duplicated | `_adopt_feature_directory` uses `shutil.move`; `test_n5_adoption_moves_the_directory_and_leaves_exactly_one_copy` asserts exactly one `spec.md` under the root, source gone, SHA preserved. `test_n5_no_string_constant_in_the_engine_names_a_speckit_owned_file` walks the engine AST and asserts **no string constant** ends with `spec.md`, `plan.md`, `tasks.md` or `feature.json` — a stronger proof than grep. Both passed |
| **Exit criterion:** a full current 18-phase flow runs against WorkItem-scoped Spec Kit context | `test_n12_two_workitems_run_the_full_flow_against_their_own_speckit_context` drives `drive_full_workflow` (init → constitution → spec → plan → checklist → tasks → analyze → design → implement → security → complete) twice in one repository, with `feature bind` before every generation phase and `feature resolve` after the spec phase, asserting both reach `current_phase == "complete"` with distinct contained `featureDirectory` values. Passed |

### Capability detection is genuine detection, not an assumption — independently confirmed

The design's central risk is a probe that always fails closed on real installations, which would make
§10's exit criterion unreachable in practice. I checked the actual installed Spec Kit rather than
trusting the plan:

- `specify_cli/agents.py:202` maps `../../scripts/` → `.specify/scripts/`, and `__init__.py:145`
  copies `.specify/scripts/<variant>/`. So the probed root is where Spec Kit genuinely installs.
- `grep -rl` over `specify_cli/core_pack/scripts/` shows **`SPECIFY_INIT_DIR`** in `bash/common.sh`,
  `powershell/common.ps1` and `python/common.py`, and **`SPECIFY_FEATURE_DIRECTORY`** in those three
  plus `bash/create-new-feature.sh`, `powershell/create-new-feature.ps1` and
  `python/create_new_feature.py`. Every one of the three variants therefore satisfies both
  capabilities, and `SPECKIT_PROBE_SUFFIXES = (".py", ".sh", ".ps1")` covers all three.

So the probe reports **supported** on a real Spec Kit 0.15.0 install, and reports **unsupported** —
and refuses — on anything that does not ship a script naming the variables. It reads a documented,
user-facing environment-variable name out of the installation's own scripts; it executes nothing and
parses no internal data structure. §10's "capability-detect; do not hardcode undocumented internals"
is satisfied.

I also independently confirmed the fact the whole relocation design rests on:
`create_new_feature.py:249` is `specs_dir = repo_root / "specs"` and `:391` is
`persist_feature_json(repo_root, f"specs/{branch_name}")`, while that file's only
`SPECIFY_FEATURE_DIRECTORY` references (`:56`, `:60`) **emit** the variable for a caller to export
rather than read it. Creation genuinely is not redirectable on this version, so discovery-plus-move
is a sound response and not an avoidable workaround.

### Relocation (plan D6) — the five claimed properties, checked

| Claimed property | Verified |
|---|---|
| Bounded | Source is always the winner of a fixed three-tier scan; target is always `paths.speckit_specs_root / <dirname>`; both endpoints are `.resolve()`d and required to be `relative_to(project_root)` before anything is touched, refusing `feature_adopt_failed` otherwise |
| Audited | `append_audit(..., event="speckit_feature_adopted", ...)` with `from`/`to` in the message and `artifact=to`; `test_n6_adoption_is_audited_with_from_and_to` also asserts `audit verify → matches is True`, so the hash chain survives the new event |
| Non-overwriting | `if target.exists(): raise Refused("feature_target_exists")` evaluated **before** the containment check and before any mkdir. `test_n6_an_occupied_target_refuses_without_touching_either_side` proves both sides intact |
| Git-recoverable | The move happens inside a Git working tree; `git check-ignore -v workitems/demo/specs/001-x/spec.md` exits **1**, so the destination is versioned and the move is visible in `git status` |
| Single copy | `shutil.move`, not `copy`; `test_n5…` asserts `rglob("spec.md") == [target]` and pre/post SHA equality. §10's "do not create an SDLE duplicate" holds — the AST proof shows the engine has no string constant that could name a Spec Kit-owned file |

---

## Regression evidence

**Byte-identity of the six functions the handoff claimed unchanged** — re-derived by extracting each
function body from `git show beb28f2:scripts/sdle.py` and `git show 82e6a68:scripts/sdle.py` and
comparing strings, not by eyeballing a diff:

| Symbol | Result |
|---|---|
| `cmd_migrate_workflow` | identical (9501 chars both) |
| `bind_workitem` | identical (2834) |
| `resolve_decision` | identical (4436) |
| `write_atomic` | identical (1358) — the F1 fix at `6e8af8c` is untouched |
| `append_audit` | identical (1295) |
| `SDLE_OWNED_PREFIXES` | identical block |
| `RUNTIME_FREE_COMMANDS` | identical block |

Extended beyond the claim, all also identical: `save_state`, `read_state`, `touch_lock`,
`cmd_workitem_use`, `cmd_manifest_build`, `cmd_init`.

**Standing guarantees:**

- The ladder never guesses — `resolve_decision` and `bind_workitem` byte-identical; `>1 plausible →
  workitem_ambiguous` with candidates listed, pinned by unchanged
  `tests/test_units_workitem_resolution.py` (`git diff --name-only beb28f2 82e6a68 --
  tests/test_units_workitem.py tests/test_units_workitem_resolution.py` → **empty**;
  `test_units_workitem.py` still collects **57**).
- Legacy `.workflow/` dual-read rung intact — `{workitem_runtime}` resolves to `.workflow` under the
  legacy binding and `feature resolve` keeps its exact baseline behaviour there (`searched ==
  [".specify/specs"]`, no relocation), both pinned by passing tests. T11, not T04, removes it.
- `migrate-workflow` never mutates `.workflow/` — function byte-identical.
- `init` still refuses `legacy_workflow_present` unconditionally — single raise site at
  `scripts/sdle.py:2346`, pinned by three unchanged assertions.
- Single writer / audit chain — `append_audit`, `save_state`, `write_atomic` unchanged; `feature
  bind` writes nothing (whole-root SHA map); `feature resolve` writes only through the existing
  helpers.
- No new `dataclass_replace(paths, workitem=...)` site — `test_workitem_rebinding_happens_only_at_the_declared_sites`
  is byte-unchanged and passing.
- T03-4 / T03-5 / T03-6 were **not** quietly adopted: `cmd_workitem_use` is byte-identical, no
  `ACTIVE_CONTEXT_SETTERS` symbol exists, and the `workitem_required` reason name is unchanged.

**Write-fence carve-out is exactly as narrow as claimed.** `SPECS_CARVE_OUT =
re.compile(r"(?:^|/)workitems/[^/]+/specs/")`, evaluated before the `FENCED` loop and returning
early. The plan's `^workitems/` anchor genuinely would not have worked — `relative()` in
`hooks.py` only strips a prefix when the path starts with `PROJECT_DIR`, and Claude Code passes
absolute native paths — so the declared divergence to a segment-boundary anchor is correct and uses
the same semantics as the neighbouring `in_dir()`. Four near-miss deny cases pin that
`workitems/index.md`, `workitem.json`, the whole `<id>/.sdle/` runtime, `<id>/reviews/`,
`workitems/wi-a/specs.md` and `workitems/specs/not-a-workitem.md` all remain denied. `FENCED` and
`FENCE_REASONS`' key set are otherwise unchanged; the fence was not loosened generally. One residual
is recorded as finding N-3.

---

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` | **`498 passed in 963.95s (0:16:03)`, exit 0** | Run to completion in this context via the background runner, which reported `exit code 0`. Real progress output and a real summary line were produced, so this is not the `rtk` false green (which prints `Pytest: No tests collected`). `grep -c "short test summary"` on the captured output = **0** → zero skips, xfails and errors |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **`498 tests collected in 0.41s`**, `COLLECT_RAW_EXIT=0` | Collected == passed |
| per-file collection from the same collect-only capture | — | `test_units_speckit_binding.py` **53**, `test_units_workitem.py` **57**, `test_hooks.py` **44**. Suite arithmetic re-derived: 438 (T03 baseline) + 53 (new file) + 7 (added hook parametrize cases) = **498** |
| `python scripts/sdle.py lint-skill` | **exit 0, 22 PASS / 0 FAIL** | `Parsed 19 phases, 8 gates, 15 migration rows`; `all four locations report v1.15`; `every field has a migration row`; `data.failed == []` |
| `python tools/transition/validate.py` | **exit 0** | `TRANSITION_VALID: complete=4/12 next=T04`, including full `control-plane.sha256` re-hashing |
| `python scripts/sdle.py feature bind` / `feature capabilities` (live, this repository) | **exit 1, `workitem_required`** | Resolution precedes Spec Kit work; refusal is final |
| Python 3.11 | **NOT_RUN** | no 3.11 interpreter on this host |
| CI (`ubuntu-latest` / `windows-latest`) | **NOT_RUN / UNKNOWN** | branch is local-only; no CI run observed. **No outcome predicted** |

The F1 `ENVIRONMENT_FLAKE` procedure was treated as **VOID**. No failure occurred, so it was never
reached.

---

## Future-phase leakage check

Clean. `grep '^+'` over `git diff beb28f2 82e6a68 -- . ':(exclude)docs/transition/'` then
`grep -nE 'policies/|flow_id|risk_tier|classification|\.sdle/config|brownfield|adaptive|subagent|ACTIVE_CONTEXT_SETTERS|pending_branch_ack'`
returns **no matches**. No repository-root `.sdle/` exists. T05's configuration boundary, T06's
classification/risk, T07's flow model, T08's brownfield discovery, T09's adaptive gates and T10's
subagents are all absent. T11's removals did not happen early: the legacy rung, `migrate-workflow`
and `init`'s unconditional refusal are all still present and pinned. The plan's explicit
non-adoptions (T03-4/5/6) were verified as genuinely not adopted, not merely undeclared.

---

## Test weakening / deletion check

No test was weakened, skipped, xfailed, deleted or renamed-away. `git diff --name-status beb28f2
82e6a68 -- tests/` shows **zero `D`** and **zero `R`** rows. Each `M` was read line by line:

- `conftest.py` `+10 −0` — additive only, exactly the permitted edit.
- `test_hooks.py` `+11 −0` — purely additive; **every pre-existing case, including
  `/proj/.specify/specs/001/spec.md`, is unchanged**.
- The three integration files — path rebinding only; assertion strength unchanged. `01` derives the
  directory **per call** from the project handed to `run_happy_path`, which is stricter than a module
  constant because a second WorkItem is driven through the same helper.
- `test_lint_skill.py` `+1 −1` — the README title the version-drift test rewrites. The test still
  proves drift fires.
- `test_units_state.py` `+4 −4`, `test_units_transitions.py` `+7 −4` — version literals plus the
  superseded feature-field seeding; `test_gate_show_substitutes_feature_id` now seeds a full
  `specKit` object and asserts the WorkItem-scoped path, which is equal-or-stronger.
- `test_units_workitem_runtime.py` `+12 −7` — version literals, the two-step migrate list, one
  rename (`…is_1_14…` → `…is_1_15…`, body otherwise unchanged), and the migrate-workflow field list
  where `current_feature_id` was removed from the preserved-field loop and replaced by **two
  stronger** assertions (`"current_feature_id" not in migrated` and
  `migrated["specKit"] == legacy_state_before["specKit"]`).

All are TP-003 category 2. The suite-wide `skip`/`xfail` grep is correctly identified in the handoff
as non-evidence; the real evidence is that `-rsxX` produced **no** short-summary section and
collected == passed, both re-derived here.

---

## Deterministic guardrail check

No fail-open introduced. Every new decision point refuses:

- `speckit_missing` (exit 1) when `.specify/` is absent;
- `speckit_capability_missing` (exit 1) when any required capability is unsupported — the probe's
  default is `supported: False` and an unreadable file keeps that default;
- `feature_directory_unresolved` (exit 1) under `--require-feature`;
- `feature_outside_workitem` (exit 1) at `gate approve` for the four Spec Kit gates;
- `feature_target_exists` / `feature_adopt_failed` (exit 1) rather than overwriting or half-moving;
- `feature_unresolved` / `feature_ambiguous` preserved with their baseline intra-tier selection rule
  unchanged — ambiguity still refuses and still lists candidates.

`feature capabilities` deliberately never refuses on capability grounds; it is a diagnostic in the
shape of `workitem resolve`, and the refusal lives at `feature bind`. It still refuses
`workitem_required` / `workitem_ambiguous`, verified live.

`cmd_preflight`'s additions are strictly additive: its `problems` list, refusal reasons and messages
are unchanged (`test_n4_preflight_reports_the_same_detection` asserts `data["problems"] == []` while
a capability is missing), and the `speckit_missing` message text was hoisted into a shared constant
used by both call sites — a de-duplication, not a behaviour change.

Invariant 3 holds: the new surface is `feature bind` / `feature capabilities` under the existing
`feature` group. No `speckit-*` skill name and no `/speckit.*` command appears on any added line or
in the live `--help` output.

Invariant 8 holds: T04 delegates nothing and adds no subagent surface.

---

## Duplicated-source-of-truth check

Improved, not regressed. `speckit_ref` / `speckit_set` are the only accessors for the object;
`detect_speckit_capabilities` is the single source for `feature bind`, `feature capabilities` and
`cmd_preflight`; `SPECKIT_MISSING_MESSAGE` replaced a duplicated message literal; the WorkItem specs
prefix is derived in three places but always from the single `Paths.speckit_specs_relative` property,
so no call site concatenates a Spec Kit path of its own. NB-1's transitional prefix bridge is gone and
the `ARTIFACT_OWNERSHIP` templates themselves now carry `{workitem_runtime}` and
`{speckit_feature_directory}` — the table genuinely moved; the behaviour was not lost, and both
substitutions are pinned by `test_n9_*` including the legacy `.workflow` case.

---

## State / audit / evidence integrity check

- `write_atomic`, `save_state`, `append_audit`, `touch_lock` byte-identical to `beb28f2`.
- The new `speckit_feature_adopted` event goes through `append_audit`, and
  `test_n6_adoption_is_audited_with_from_and_to` asserts `audit verify → matches is True`, so the
  hash chain is intact across the new event type.
- `feature bind` is pure — whole-project-root recursive SHA map identical before and after, on the
  success path and on all three refusal paths.
- SDLE never writes inside `.specify/`: proved by a `.specify/` SHA map taken before and after a full
  bind + resolve cycle with a real `.specify/feature.json` planted, and by the AST proof that no
  engine string constant can name `feature.json`.
- `evidence/` and the session lock are untouched.
- Governed-artifact SHA freshness: `artifact_shas` baselines are content hashes, so a relocated
  feature directory re-resolves to the same content and `compute_drift` correctly reports no drift —
  verified by reading `compute_drift` and `cmd_gate_approve`, both of which now take the resolved path
  from the single `resolve_artifact_path`. Control-plane governed artifacts re-hash clean under
  `validate.py`.

---

## Cross-platform / path handling check

- Every emitted path is repo-relative POSIX via `repo_relative()` / `Paths.speckit_specs_relative`,
  both of which apply `.replace(os.sep, "/")`.
- `SPECIFY_INIT_DIR` is emitted as the absolute **native** project root and
  `SPECIFY_FEATURE_DIRECTORY` as a repo-relative POSIX path — which is what Spec Kit 0.15.0's
  `get_feature_paths` resolves against the repo root. `env` is an ordered list of `{name, value}`
  objects, never a shell string, so no shell's quoting rules are baked into the engine.
- The hook carve-out matches on `/` after `tool_path()` normalises `\` → `/`; the added `test_hooks`
  cases cover the POSIX, repo-relative and Windows-backslash forms.
- `shutil.move` with the target's parent pre-created and the target proven not to exist avoids the
  "move into an existing directory" semantics on every platform.
- `lint-skill`'s `no_powershell_only_cmdlets` check passes, so no PowerShell-only cmdlet entered a
  prompt file. `scripts/sdle.sh` and `scripts/sdle.ps1` are byte-identical to `beb28f2`.
- Everything added is standard library only.

---

## Artifact review / SHA freshness check

`python tools/transition/validate.py` exits 0, which re-hashes every entry in
`docs/transition/control-plane.sha256` with canonical-LF normalisation. `T04-plan.md` is byte-identical
to its commit at `fe856d1`, so the plan the implementation was verified against is the plan that was
approved. No control-plane file was touched by `82e6a68`.

---

## Findings

### Blocking

**None.**

### Non-blocking

**N-1 (HIGH) — `_mig_1_14` step (b) and the `feature_outside_workitem` gate precondition interact:
a migrated in-flight v1.14 workflow can resolve its gate artifact but cannot approve it until
`feature resolve` is re-run.**
A v1.14 state already scoped to a WorkItem (the normal post-T02 shape) whose artifacts sit at
`.specify/specs/<id>` migrates to `specKit.featureDirectory == ".specify/specs/<id>"` by design
(derivation step b). At its next `gate approve` for `gate_spec`, `gate_plan`, `gate_tasks` or
`gate_analyze`, `gate_precondition_hook` sees `paths.workitem` non-null and a directory that does not
start with `workitems/<id>/specs/`, and refuses `feature_outside_workitem`. The plan's F5 guard and
`SKILL.md`'s new migration row both say derivation step (b) exists "so an in-flight workflow keeps
resolving its gates" — literally true for *resolution*, misleading about *approval*.
The behaviour itself is defensible and arguably §10-correct (an artifact at a repository-global path
is not attributable to the WorkItem), it fails closed, and the refusal message names the exact
remedy — re-running `feature resolve` while bound, which relocates the directory into the WorkItem
with content SHAs preserved, so earlier gates' `artifact_shas` baselines still match and no false
drift fires. That recovery is nonetheless heuristic: it picks the newest directory in the first
non-empty tier, so a repository with an unrelated root-level `specs/` or several stale
`.specify/specs/*` entries could adopt the wrong one.
**No test drives migrate-then-approve**, so this interaction is entirely unpinned.
*Recommended owner:* a T04 follow-up or T11 hardening. *Recommended remediation:* add a test for the
migrate → `gate approve` path, and either narrow the D9 refusal to allow a directory that
`_mig_1_14` itself derived from `.specify/specs/<featureId>` until the next `feature resolve`, or
correct the `SKILL.md` row and the operator guidance to state plainly that a migrated in-flight
workflow must run `feature resolve` once before its next Spec Kit gate.

**N-2 (MEDIUM) — discovery tier 2 (`<project-root>/specs/*`) is a repository-global staging area
selected by newest-mtime, so two WorkItems at Phase 4 concurrently can cross-adopt.**
Tiers 1 and 3 are safe as the plan claims, and no tier reaches into `workitems/<other-id>/`. But
Spec Kit 0.15.0 creates every feature at `repo_root/specs/<branch>`, and `feature resolve` takes the
newest directory there with nothing linking the candidate to the requesting WorkItem. If WorkItem A
and WorkItem B are both mid-Phase-4 in one repository, A's `feature resolve` can adopt B's freshly
created directory. This is the one path by which §10's first required test can be violated, and it is
covered by neither N1 nor N7. Mitigations that keep it non-blocking: the adoption is audited with
`from`/`to`, and invariant 4 puts the artifact **content** in front of a human at Gate 2, so a swapped
spec is visible to the approver before any approval is recorded.
*Recommended owner:* T11 hardening (or a T04 follow-up). *Recommended remediation:* refuse when tier 2
yields more than one candidate, or bind adoption to evidence tying the candidate to this WorkItem —
for example reading Spec Kit's own `.specify/feature.json` (read-only; SDLE must still never write it)
or requiring the candidate to postdate this WorkItem's `speckit_invoked` checkpoint.

**N-3 (LOW–MEDIUM) — the write-fence carve-out is matched against a non-normalised path, so a `..`
segment escapes it.** `SPECS_CARVE_OUT.search(relative(path))` runs on a string that `tool_path()`
has collapsed for repeated slashes but not normalised for `..`. `workitems/<id>/specs/../.sdle/state.json`
matches the carve-out and returns before the `FENCED` loop, so the fence does not deny it. Baseline
had no such escape under `workitems/`. The hook is documented as a tripwire and the engine's
single-writer refusal remains the guarantee, so this is hardening rather than a hole.
*Recommended remediation:* normalise (or reject) `..` segments before matching. *Recommended owner:*
T11 hardening.

**N-4 (LOW) — `SKILL.md:358` is now inaccurate.** It states "The write fence denies direct edits to
`workitems/` and `.workflow/`", which stopped being true when D11 carved out `workitems/<id>/specs/`.
This is a statement of a guardrail in a live prompt file, introduced by T04's own change and not
listed in D12. One-line fix. *Recommended owner:* the same documentation phase as N-5/N-6.

**N-5 (LOW) — `modules/gate-protocol.md:66` still says "substitute `current_feature_id` if needed"
for a placeholder that no longer exists.** *Verifier ruling, as the handoff requested:* **A16 was
right not to yield.** A16 is a containment guarantee over a gate-holding prompt file in a phase that
already carried a schema change, a version bump and a path relocation; unfreezing it to fix one word
would have traded a hard scope control for a cosmetic gain. The stale line has no engine effect —
the orchestrator obtains gate artifact paths from `sdle.sh gate show` / `artifact path`, both of which
substitute deterministically through the single `resolve_artifact_path`. The same file already carried
an equivalent T02-era `.workflow/` staleness that T02's verification accepted. **A6 as literally
worded is the defective criterion, not A16** — the migration chain replays history verbatim, so
`_mig_1_0`, `_mig_1_1` and `_mig_1_14` must all name the field, and A6 could never have returned only
two lines. *Recommended owner:* a documentation phase that fixes `gate-protocol.md` line 66 together
with its lines 86 and 104 (see N-6).

**N-6 (LOW) — T02 residual `.workflow/` references in live prompt files. Genuinely out of T04's
scope; needs an owning phase.** `modules/phase-execution.md` lines 39, 169, 173, 178 and 192 still
name `.workflow/audit.md`, `.workflow/implementation-manifest.md` and
`.workflow/completion-summary.json` (the generic pre-phase block and Phases 15, 16, 18);
`modules/gate-protocol.md` lines 86 and 104 name `.workflow/completion-summary.json`. I concur with
the handoff that this is T02 staleness, not a T04 regression — T04's D12 does not list these lines,
and `gate-protocol.md` is frozen by A16. One nuance the handoff did not draw out: T04 *widened* the
gap at `phase-execution.md:178`, which used to agree with the literal `ARTIFACT_OWNERSHIP` template
and now disagrees with `{workitem_runtime}/implementation-manifest.md`. *Recommended owner:* **T11's
documentation sweep (§17)**, which already owns `docs/dry-runs/`; these seven lines should be added to
its scope explicitly so they are not lost.

**N-7 (LOW) — the Gate 7 implementation manifest now lists the WorkItem's Spec Kit artifacts as
changed files.** Relocating specs from gitignored `.specify/specs/` to versioned
`workitems/<id>/specs/` means `git status --short -uall` in `cmd_manifest_build` now reports
`spec.md`, `plan.md`, `tasks.md` and `checklist.md` as added/changed. `cmd_security_review_evidence`
received an explicit `:(exclude)<featureDirectory>` for exactly this reason (D10); the manifest did
not. The result is noise inside a governed Gate 7 artifact, not a fail-open — and the plan's
in-repo comment deliberately forbids widening the manifest exclusion to `SDLE_OWNED_PREFIXES`.
*Recommended owner:* unassigned; worth a decision alongside N-6.

**N-8 (INFO) — plan defects encountered and correctly declared rather than absorbed.**
(a) The plan's "Files expected to change" omitted `tests/test_lint_skill.py` and
`tests/test_units_state.py`, both of which necessarily carry version literals; the handoff declares
this and A17's "justified in the handoff" is satisfied. (b) A6 is unreachable as worded (see N-5).
(c) A7 names a `status` subcommand that this CLI does not have; the substituted readers (`state
dump`, `header`, `gate show`, `artifact path`) are the right ones and are covered. (d) The plan's
`^workitems/` fence anchor would not have matched the absolute paths Claude Code passes; the
segment-boundary divergence is correct. All four are plan defects, not implementation defects, and
none was resolved by widening scope.

**N-9 (INFO) — `feature bind`'s `env` is emitted but its application is unproven.**
`phase-execution.md` instructs the orchestrator to "export every `env` entry it returns" before each
Skill-tool invocation. Nothing in the engine can observe whether that export actually reaches the
Spec Kit process, and no test can prove it without invoking Spec Kit (which `conftest.py` rule 2
forbids). This is inherent, and the design is resilient to it — the discovery-plus-move path in
`feature resolve` makes the flow correct even when the export is ineffective, and the gate
precondition is the engine-side backstop. Recorded so no later phase assumes env propagation is
proven.

**N-10 (INFO) — `gate_precondition_hook` is not invoked on the drift re-approval path.**
`_approve_drift` calls `resolve_artifact_path` but not `gate_precondition_hook`, so neither the new
`feature_outside_workitem` refusal nor the pre-existing `manifest_incomplete` refusal applies to a
drift re-approval. This is the baseline shape, which T04 inherited rather than introduced, but T04
extended what is being bypassed. *Recommended owner:* T11 hardening.

---

## Final result rationale

Every one of the 21 acceptance criteria is met on independently re-derived evidence, with two —
A6 and A7 — met only against criteria that the plan itself worded unreachably; in both cases the
implementer declared the defect rather than widening scope, and I concur with both dispositions.
All five of contract §10's required tests exist, were read, and pass; §10's exit criterion is
demonstrated by a two-WorkItem 18-phase run in one repository. The capability probe was checked
against the actual installed Spec Kit and genuinely detects rather than assumes, with a closed
failure direction and a refusal that names what is missing and where it was probed. Relocation's five
claimed properties were each verified by source and by passing test rather than by reading the plan.
The full suite is 498/498 at exit 0 with collected == passed and no short-summary section; `lint-skill`
is 22/22 at exit 0 reporting 15 migration rows and v1.15; `validate.py` exits 0 including control-plane
re-hashing. Zero tests were deleted, weakened, skipped or xfailed; the two guardrail test files are
byte-unchanged. Six claimed byte-identical engine functions were verified by extraction and string
comparison, plus six more beyond the claim. No future-phase leakage, no fail-open, no duplicated
source of truth, no state or audit regression, no cross-platform regression, and NB-1 is genuinely
discharged by moving the `ARTIFACT_OWNERSHIP` templates rather than by deleting the bridge and losing
the behaviour.

Ten findings are recorded, none blocking. The strongest, N-1, is an interaction between two clauses of
the immutable plan that the implementation follows faithfully: the resulting behaviour fails **closed**,
is auditable, names its own remedy, and is arguably the §10-correct outcome — but it is unpinned by any
test and the accompanying `SKILL.md` wording overstates what derivation step (b) buys. N-2 is a real
residual cross-WorkItem path through the repository-global tier-2 staging area, mitigated by the audit
record and by invariant 4 putting artifact content in front of a human before any approval. Neither
rises to an implementation defect that should return this phase to a new implementer, and neither
requires a material architecture, contract or baseline decision, so no blocker is written.

The single top-level result recorded for this phase is the `**Result:**` line in the header above:
**PASS**.
