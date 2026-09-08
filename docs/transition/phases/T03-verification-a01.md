# T03 Independent Verification — Attempt a01

**Phase:** T03 — WorkItem Resolution and Parallel Developer Isolation
**Attempt:** 1
**Verifier context:** fresh/isolated
**Result:** PASS

> The handoff is a claim set, not proof. Every figure below was produced by a command run
> in **this** verification context. Nothing is copied from `T03-handoff-a01.md` or from any
> `T03-checkpoint-a01-NN.md`; the checkpoints are known to have been partly inaccurate
> (they implied `tests/test_units_workitem_resolution.py` existed when it did not), so
> **the tree on disk was treated as the only evidence.**

## Identity and scope, re-derived

| Fact | Observed |
|---|---|
| HEAD | `beb28f2256baa4f74d42fa9be66a0aaedc9175d6` — "T03: resolve the WorkItem from anywhere (IMPLEMENTED, NOT YET VERIFIED)" (`git rev-parse HEAD`) |
| Branch | `transition/workitem-v1` |
| Working tree | exactly one modification, ` M .claude/settings.local.json` (the user's permission allowlist — out of scope, deliberately excluded from the commit). No stray runtime artifacts were left by any command run here. |
| Implementation commit contents (`git diff --name-status 767b657 beb28f2`) | 6 `M` product/doc files, `M scripts/sdle.py`, `M docs/transition/progress.md`, 3 `M` under `tests/`, 1 `A tests/test_units_workitem_resolution.py`, 7 `A` control-plane phase artifacts. No `D`. |
| Rollback baseline | `ab889a1` (T02 implementation, verified PASS). Product baseline `f8fdaa0`. |
| Plan / contract immutability | `git diff --stat 767b657 beb28f2 -- docs/transition/phases/T03-plan.md docs/transition/transition.md docs/transition/templates tools/transition` → **empty**. The plan, the contract, the templates and the guard were not touched by the implementation commit. |
| Host | Python **3.13.0**, git 2.46.2.windows.1, Windows 10. |

Tooling note: the `rtk` shell proxy makes a plain `python -m pytest` print
`Pytest: No tests collected` and exit 0 — a false green, confirmed here
(`PLAIN_EXIT=0`, `No tests collected`). Every pytest figure below was produced with
`rtk proxy "python -m pytest …"`, with the raw exit read by `; echo RAW_EXIT=$?` and
**no pipe** in between, plus an independent `--junitxml` machine-readable summary.

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **A1** full suite `341+N` collected == passed, raw exit 0, zero skips/xfails/errors | **PASS** | `rtk proxy "python -m pytest -q -rsxX --junitxml=…"` → **`438 passed in 626.05s (0:10:26)`, `RAW_EXIT=0`**, no short-summary section. `--collect-only` → **`438 tests collected`**. JUnit XML: `errors="0" failures="0" skipped="0" tests="438"`. Per-module counts re-derived from the XML: `test_units_workitem_resolution` **96** (new), `test_units_workitem_runtime` **45** (44+1 parametrize row), `test_units_workitem` **57** (unchanged from T02), `test_hooks` **37** (unchanged: one test replaced by one). 341 + 96 + 1 = **438**. |
| **A2** `lint-skill` raw exit 0, 22 PASS / 0 FAIL, 19 phases / 8 gates / 14 migration rows, v1.14 | **PASS** | `python scripts/sdle.py lint-skill` → `LINT_EXIT=0`; 22 `[PASS]` lines, no `[FAIL]`, `"failed": []`. `tables_wellformed: Parsed 19 phases, 8 gates, 14 migration rows.`; `version_string_consistent: all four locations report v1.14`; `migration_covers_every_state_field: every field has a migration row`; `single_state_template` PASS. |
| **A3** `tools/transition/validate.py` raw exit 0 | **PASS** | `TRANSITION_VALID: complete=3/12 next=T03`, `TVAL_EXIT=0`. This also re-verifies `control-plane.sha256`. |
| **A4** must-not-change paths byte-identical to `ab889a1` | **PASS** | `git diff --exit-code ab889a1 -- .claude/hooks/hooks.py .claude/settings.json .claude/skills/sdle/templates/state.json .claude/skills/sdle/modules/ scripts/sdle.sh scripts/sdle.ps1 .github/ requirements/ docs/dry-runs/` → **`A4_EXIT=0`**. |
| **A5** `CURRENT_VERSION == "1.14"`, 14 migration rows, template unchanged, no new state field | **PASS** | `scripts/sdle.py:655: CURRENT_VERSION = "1.14"`; `git diff --exit-code ab889a1 beb28f2 -- .claude/skills/sdle/templates/state.json` → exit 0; `lint-skill` reports 14 migration rows and `migration_covers_every_state_field` PASS. Read of the whole `scripts/sdle.py` diff confirms no `state.json` key is added. |
| **A6** every §9 matrix row, ambiguous rows write nothing | **PASS** | All seven contract rows have one named test each (`test_matrix_*`), read line-by-line and matched against `transition.md` §9's table. The ambiguous rows assert a recursive `sha_map()` of the whole repository is unchanged **and** that no `.workflow/` and no `workitems/<id>/.sdle/` was created. All green in the 438. |
| **A7** four launch locations resolve one project root; `--project-root` still overrides | **PASS** | `test_all_four_launch_locations_resolve_the_same_project_root`, `test_project_root_flag_still_overrides_the_launch_directory`, `test_the_nearest_marker_ancestor_wins`, `test_resolve_paths_falls_back_to_the_launch_directory`, `test_an_explicit_root_with_an_outside_cwd_does_not_feed_the_cwd_rung`. Code read: `discover_project_root` walks `(start, *start.parents)` testing `PROJECT_ROOT_MARKERS` in order at each level, nearest ancestor wins; explicit root and `SDLE_PROJECT_ROOT` short-circuit it entirely. |
| **A8** CWD inside an unregistered WorkItem refuses `workitem_unregistered`, binds nothing | **PASS** | `resolve_decision` rung 2 returns `unregistered_directory` **before** rung 3 (`len(known) == 1`), so a lone registered WorkItem cannot be bound from inside an unregistered directory. Pinned by `test_cwd_inside_an_unregistered_workitem_directory_refuses` and `test_rung_two_beats_the_sole_registered_rung`. |
| **A9** `bind_workitem` purity across bind / refuse / legacy | **PASS** | `test_bind_workitem_writes_nothing_and_prints_nothing` takes a recursive SHA map before each call and asserts equality plus empty stdout/stderr, across the context, explicit, unknown, ambiguous and legacy paths. Code read confirms `resolve_decision` only *reads* the context. |
| **A10** context write sites closed; invalid contexts fall through | **PASS** | AST test `test_the_active_context_is_written_only_by_the_declared_setters` asserts the calling-function set is exactly `{cmd_init, cmd_migrate_workflow, cmd_workitem_use}`; independently confirmed by reading the diff. `test_workitem_create_writes_no_active_context`, the four-way `test_an_invalid_context_is_skipped_never_fatal` parametrize, `test_a_context_whose_directory_vanished_is_skipped`, `test_a_branch_stale_context_is_skipped`. |
| **A11** `execution.json` git block; `workitem.json` exact-key pin | **PASS** | `write_execution_file` gains `git: {branch, startSha, worktree}`; `test_execution_records_branch_and_start_sha`, `…_nulls_without_a_repository`, `…_a_null_branch_on_a_detached_head`, and `test_workitem_json_git_object_still_has_exactly_initial_branch` (`set(doc["git"]) == {"initialBranch"}`). |
| **A12** nine `BRANCH_CRITICAL_ACTIONS` refuse; advisory succeeds; `rendered` byte-identical; two-step works; `skip` double-ack pinned | **PASS** | `BRANCH_CRITICAL_ACTIONS` is a 9-member frozenset; `test_the_invocation_list_covers_every_branch_critical_action` asserts the parametrize list is set-equal to it (so it cannot silently under-cover) and that `len(...) == 9`. Nine parametrized refusal cases assert exit 1, `reason == "branch_mismatch"`, unchanged `current_phase` and `approvals`, `pending_confirm_action == "branch_mismatch"` and `branch_mismatch_guard` in the ledger. `state get` succeeds; `gate reject` is advisory; `header.rendered` is byte-identical while `data.branch_mismatch` is populated; the re-run audits `branch_mismatch_accepted`. The `skip` sequence is pinned at three invocations / two acknowledgements, with the inverse `test_skip_confirm_alone_still_refuses_no_pending_confirmation`. |
| **A13** `workitem resolve` always exit 0, never a pick | **PASS** | `cmd_workitem_resolve` has no refusal path of its own; candidates come from `candidate_evidence`, which returns registry order with no ordering, no `min`/`max`/`sorted` and no tie-break. Five tests including `test_workitem_resolve_never_refuses_and_never_picks`. |
| **A14** `validate` per-rule findings and exit codes | **PASS** | One test per D8 row, each asserting `check`, `severity` and exit code; clean repo → exit 0 with no findings; warnings-only → exit 0; `test_validate_runs_in_an_ambiguous_repository` → exit 0 with `active: null`; `test_validate_surfaces_a_corrupt_registry_as_an_integrity_failure` → exit 3 `index_malformed`; `test_validate_findings_all_have_the_declared_shape` pins `{check, severity, workitem, detail, path}`. Independently run against this repository: `python scripts/sdle.py --project-root . validate` → exit 0, one `active_workitem_unresolved` warning. |
| **A15** **NB-3 closed**, hooks.py byte-identical | **PASS — verified directly, not via the rewritten test.** | I overrode the test body in-process and printed the hook's real output: `with-context decision=ask reason=SDLE dirty-tree guard: the implement phase has not run its p…` ; `no-context output={}` ; `stale-context output={}`. So in a two-WorkItem repository the `PreToolUse` dirty-tree guard genuinely emits `permissionDecision: ask`, and genuinely stays silent when nothing resolves. `.claude/hooks/hooks.py` is byte-identical to `ab889a1` (A4). |
| **A16** §9 exit criterion, worktree-shaped | **PASS** | `test_two_worktrees_drive_two_workitems_with_no_flag` passed inside the 438. Read in full: real `git worktree add`, `workitem use` per worktree, `init` with **no** `--workitem` anywhere, cross-checks that each `state.json` names its own WorkItem, that the neighbour's `state.json`/`audit.md` are byte-unchanged after a further ledger write, that each has its own `lock`, and that neither working directory has a `.workflow/`. It asserts `added.returncode == 0` rather than skipping. |
| **A17** TP-003 diff shape and the skip/xfail grep | **PASS** | `git diff --name-status ab889a1 beb28f2 -- tests/` → exactly one `A` (`tests/test_units_workitem_resolution.py`) and exactly three `M` (`conftest.py`, `test_hooks.py`, `test_units_workitem_runtime.py`), no `D`. The added-line grep for `skip|xfail` returns **20** lines; every one classified below — none is a pytest marker. |
| **A18** no future-phase leakage | **PASS** | `grep -E "\.sdle/policies\|baseline\.\|risk\|classification\|flow_type\|subagent"` over `scripts/sdle.py` → **2 hits**, and `git show ab889a1:scripts/sdle.py` gives the **same 2** (`baseline.lower()` in drift comparison; the `drift rebaseline` help string). No repository-root `.sdle/`. `resolve_artifact_path`'s `legacy_prefix = ".workflow/"` bridge is present and untouched (`sdle.py:3064-3066`, absent from the diff). |
| **A19** legacy support intact | **PASS** | Every `migrate-workflow` test green in the 438; `test_the_legacy_dual_read_rung_still_binds` (rung 6, `workitem is None`); `test_init_still_refuses_a_legacy_workflow_unconditionally`. The only line added to `cmd_migrate_workflow` writes `workitems/.active-context.json` *after* the commit write — nothing under `.workflow/` is written, renamed or deleted. |
| **A20** Python 3.11 and CI recorded NOT_RUN | **PASS** | This host is Python **3.13.0** only; the branch has never been pushed. **NOT_RUN / UNKNOWN. No outcome is predicted.** |

## Regression evidence

- **T02's proven guarantees, each re-checked against code and tests:**
  - *The ladder never guesses.* `resolve_decision` computes a candidate **set** at every new
    rung and applies §9's 0/1/>1 rule to it. Rung 5 uses `len(branch_matches) == 1`; two
    WorkItems on one branch stay ambiguous (`test_two_workitems_on_one_branch_never_tie_break`).
    `workitem_ambiguous` keeps its original `workitems` key and only *gains* `candidates`.
    AST test proves `resolve_decision` calls no `min`/`max`/`sorted`.
  - *Legacy `.workflow/` dual-read still works.* Rung 6 unchanged, still gated on zero
    registered WorkItems; `bind_workitem` returns the unbound `paths`.
  - *`init` refuses `legacy_workflow_present` unconditionally.* The `for_init and
    legacy_state_present` branch is the first decision in `resolve_decision`, ahead of the
    explicit rung.
  - *`migrate-workflow` never mutates `.workflow/`.* Confirmed by reading the whole diff of
    that function: one added block, writing the active context.
  - *Write fence, `SDLE_OWNED_PREFIXES`, audit hash chain, `write_atomic`.* None appear as a
    changed line in `git diff ab889a1 beb28f2 -- scripts/sdle.py` (targeted grep of the diff
    returned only the three new *call sites* of `write_atomic`/`append_audit`).
- **Rung ordering (plan D2/U4, `INFERRED`) judged, not re-derived.** Placing "sole registered"
  at position 3 is sound: rungs 4 and 5 are inside `if known:` and are only reachable when
  `len(known) != 1`, so with exactly one registered WorkItem they could only ever return that
  same id or nothing. Putting them above rung 3 would let a stale context or a non-matching
  branch demote a single-WorkItem repository to a refusal — a regression against
  `test_rung2_the_sole_registered_workitem_binds_with_no_flag`. Placement accepted.
- **`_own_confirm_token` (divergence 2) — the livelock was reproduced before the fix was
  accepted.** I monkeypatched `_own_confirm_token` to return `None` (i.e. plan D5's literal
  mechanism) in-process and drove eight `skip` invocations on a mismatched branch:

  ```
  step 1 ['skip']              exit=1 reason=branch_mismatch        pending=branch_mismatch
  step 2 ['skip']              exit=0 reason=None                   pending=skip
  step 3 ['skip','--confirm']  exit=1 reason=branch_mismatch        pending=branch_mismatch
  step 4 ['skip','--confirm']  exit=1 reason=no_pending_confirmation pending=None
  step 5 ['skip','--confirm']  exit=1 reason=branch_mismatch        pending=branch_mismatch
  step 6 ['skip']              exit=0 reason=None                   pending=skip
  step 7 ['skip','--confirm']  exit=1 reason=branch_mismatch        pending=branch_mismatch
  step 8 ['skip','--confirm']  exit=1 reason=no_pending_confirmation pending=None
  ```

  The cycle never converges: `skip` on a mismatched branch could never be completed under the
  plan's literal guard. The divergence is therefore **justified**, and the plan's declared
  consequence (two acknowledgements, branch first, then the command's own) is preserved and
  pinned.
- **Divergence 7 (`workitem_id_wellformed`) — verified as a genuine defect fix with no
  over-acceptance.** `cmd_workitem_create --auto-generate` mints `WI-<name>-<UTC>`, whose
  uppercase `WI-` prefix cannot match `WORKITEM_ID_RE = ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$`, so
  before the fix `workitem use` would persist such a context and rung 4 would ignore it
  forever. `active_context_workitem` and `validate`'s `_escape_detail` now call the *same*
  predicate, so they cannot disagree. **No id form is over-accepted:** both regexes are fully
  anchored and neither admits `/`, `\`, `.` or whitespace, so `..`, `../evil` and any path
  fragment are still rejected — `test_validate_detects_a_traversal_shaped_index_id` pins that.
- **Divergence 4 (`active_workitem_unresolved` = warning) judged and accepted.** §9's
  "Add validation" list does not include "no active WorkItem" at all, so no listed check is
  weakened. Making it an `error` would give exit 3 to every legitimately ambiguous repository,
  contradicting both plan N9 ("`validate` must run successfully in an ambiguous repository")
  and §9's own `>1 plausible -> ASK`. Warning is the correct severity.
- **Divergence 5 and 6 judged and accepted.** (5) A `state.json` with no `workitem` field is a
  pre-1.14 state awaiting `migrate`, which `migrate` already reports; only a non-empty
  disagreement is a finding — this avoids a false positive, and it does not hide a genuine
  misplacement. (6) Skipping the other checks for an unsafe id is correct: following a symlink
  out of the registry to run metadata checks would *be* the traversal.
- **Divergence 1 (N10 pulled forward M8→M3) accepted, TP-003 category 2.** Independently
  confirmed that `.claude/hooks/hooks.py` is byte-identical to `ab889a1`.
- **Divergence 3 (D4 pulled forward M5→M2) accepted** — `branch_candidates` reads
  `execution.json.git.branch`, so the block genuinely had to land with rung 5.

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q --collect-only"` | `438 tests collected in 0.21s` | collected == passed |
| `rtk proxy "python -m pytest -q -rsxX --junitxml=…"` | **`438 passed in 626.05s (0:10:26)`, `RAW_EXIT=0`** | no short-summary section emitted |
| JUnit XML summary | `errors="0" failures="0" skipped="0" tests="438"` | machine-readable confirmation of zero skips/xfails/errors |
| `python scripts/sdle.py lint-skill` | `LINT_EXIT=0`, 22 PASS / 0 FAIL | `Parsed 19 phases, 8 gates, 14 migration rows`; `all four locations report v1.14` |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=3/12 next=T03`, `TVAL_EXIT=0` | also re-verifies `control-plane.sha256` |
| `python scripts/sdle.py --project-root . validate` | exit 0, one `active_workitem_unresolved` warning | this repository registers no WorkItem |
| `git diff --exit-code ab889a1 -- <A4 list>` | exit 0 | must-not-change set intact |
| In-process livelock reproduction (`_own_confirm_token` → `None`) | 8-step trace above, never converges | divergence 2 justified |
| In-process fail-open reproduction (branch switch between the two `skip` steps) | trace below | Known Limitation 1 confirmed real |
| In-process NB-3 reproduction (hook output printed) | `ask` / `{}` / `{}` | A15 confirmed without trusting the rewritten test |
| Plain `python -m pytest -q --collect-only` (control) | `Pytest: No tests collected`, exit 0 | the `rtk` false-green trap, confirmed and avoided |
| Python 3.11 | **NOT_RUN** | host has 3.13.0 only |
| CI (`ubuntu-latest`, `windows-latest`) | **NOT_RUN / UNKNOWN** | branch never pushed; **no outcome predicted** |

The F1 `ENVIRONMENT_FLAKE` procedure was **VOID** and was never invoked: the suite was green
on the first and only run, so no failure required classification.

## Future-phase leakage check

- **T04:** `ARTIFACT_OWNERSHIP` is untouched; no `.specify/`, `design/`, `reviews/` or
  `clarifications/` path moves; `resolve_artifact_path`'s transitional `.workflow/` prefix
  bridge is **present and unchanged** (`legacy_prefix = ".workflow/"`, `sdle.py:3064`). NB-1
  remains T04's to delete.
- **T05:** no repository-root `.sdle/` exists or is created; the active context is
  deliberately at `workitems/.active-context.json`. No `policies/`, no `baseline.*`.
- **T06–T11:** a targeted diff scan for `ARTIFACT_OWNERSHIP|PHASE_SEQUENCE|NEXT_PHASE|
  PROGRESS_MAP|PHASE_TO_GATE_KEY|GATE_TO_EXECUTION_PHASE|VERSION_MIGRATION|speckit|.specify|
  policies/|adaptive|brownfield|discovery|flow_type|risk` across `scripts/sdle.py`, `.claude/`,
  `README.md`, `CLAUDE.md`, `docs/SDLE-Reference-Guide.md`, `.gitignore` returned no
  substantive hit — the only `subagent` matches are the new **prohibitions** in `SKILL.md` and
  `sdle-start.md` ("never hand this question to a subagent"), which is invariant 8 being
  reinforced, not T10 being started. No constant table, version string, phase table or gate
  table changed.
- **Invariant 8 / §9 rungs 5–6:** the engine implements neither. `workitem resolve` is
  non-refusing, returns registry-ordered candidates with evidence, and performs no ranking.
  `SKILL.md` and `sdle-start.md` state that inference may only rank/annotate, that the answer
  re-enters as an explicit `--workitem`, and that the question is never delegated to a
  subagent. No `.claude/agents/` file was added or changed.

## Test weakening / deletion check

- `git diff --name-status ab889a1 beb28f2 -- tests/` → 1 `A`, 3 `M`, **0 `D`**.
- `tests/test_hooks.py::test_dirty_tree_is_silent_when_the_workitem_is_ambiguous` →
  `test_dirty_tree_resolves_a_workitem_the_same_way_the_engine_does`. **TP-003 category 2 —
  genuinely superseded**, and the rewrite is strictly stronger: it keeps both fail-safe
  assertions (silent with no context, silent with a branch-invalidated context) and *adds* the
  positive one. Its premise was T02 finding NB-3, which this phase closes. `started` → `started_git`
  is required because without git `current_branch()` is `None` and a recorded branch can never
  go stale, making the third case unreachable.
- `tests/conftest.py` — one `.gitignore` line plus its comment, mirroring the product
  `.gitignore`. This is the single edit the plan's anti-contradiction clause permits. No
  fixture, no `Project` method and no fixture semantics changed (diff read in full: +5/-2, all
  inside `init_git`'s `.gitignore` string literal and the comment above it).
- `tests/test_units_workitem_runtime.py` — one parametrize row `("validate",)`. Additive.
- **No pytest marker was added.** All 20 added lines matching `skip|xfail` were classified:
  `sha_map(root, skip=(".git",))` and its `if any(part in skip …)` (a local helper's
  excluded-paths parameter, 2); test *names* describing a resolution rung being skipped by the
  engine (5); the SDLE `skip` **CLI subcommand** and its `pending_confirm_action` token in the
  N7 tests (9); and prose comments about *not* skipping (4). None is a marker.
- Repository-wide sweep for `pytest.mark.skip|pytest.skip|xfail|mark.skipif` under `tests/`
  returns exactly one hit, `tests/test_units_infra.py:49`
  `@pytest.mark.skipif(SH is None, reason="POSIX sh not available")`. It is **pre-existing at
  `ab889a1` and byte-unchanged by T03** (`git diff ab889a1 beb28f2 -- tests/test_units_infra.py`
  is empty), and it did not fire here (`skipped="0"`). See non-blocking finding 3: the handoff
  claims this grep returns "no matches", which is wrong.

## Deterministic guardrail check

- **Exit-code contract unchanged.** `workitem_unregistered` and `branch_mismatch` are `Refused`
  (exit 1); `workitem_validation_failed` is `IntegrityError` (exit 3). No new exit code.
- **Refusals are final and list candidates.** `workitem_ambiguous` retains `data.workitems`
  and gains `data.candidates`; `workitem_unregistered` carries `directory`, `workitems` and
  `path`; `branch_mismatch` carries `recorded`, `current`, `workitem`, `action`.
- **No new fail-open path, with one declared exception.** `branch_guard` refuses *before* any
  phase change, approval write or content fingerprint. `RUNTIME_FREE_COMMANDS` remains a
  closed, enumerated frozenset (now six), asserted exactly by
  `test_runtime_free_commands_is_a_closed_enumerated_set`. `dataclass_replace(paths,
  workitem=…)` sites are pinned by AST to `{bind_workitem, branch_candidates,
  candidate_evidence, collect_validation_findings, _validate_runtime_state,
  cmd_migrate_workflow}`.
- **The one declared fail-open window is real — I reproduced it.** With `skip` issued on the
  *matched* branch, then a branch switch, then `skip --confirm`:

  ```
  matched-branch skip:          exit=0 reason=None  pending=skip
  after switch, skip --confirm: exit=0 reason=None
  branch_mismatch_guard in audit:    False
  branch_mismatch_accepted in audit: False
  SKIPPED WITH WARNING in audit:     True
  phase now: gate_constitution
  ```

  The lifecycle advanced on a mismatched branch with **no** `branch_mismatch` ever audited.
  Judgement — **accepted as a declared, correctly bounded residual risk, not a blocker:**
  (a) it affects only the four critical commands that carry their own confirmation token
  (`skip`, `reset`, `restart`, `implement preflight`); (b) it requires the user to begin a
  two-step command, change branch, and then confirm — the guard still refuses on every
  single-step critical command and on every first invocation; (c) it regresses **nothing** —
  no branch guard existed before T03, so this is a new guard with a hole, not a lost
  guarantee; (d) closing it needs either a second `pending_*` state key (a `state.json` schema
  change, a 15th `VERSION_MIGRATION` row and a version bump, all of which plan P11 and D4
  deliberately excluded) or sticky acknowledgement; (e) it is disclosed prominently as
  Known Limitation 1. Recorded as non-blocking finding 1 for T11 hardening.
- **`_own_confirm_token` opens no *other* bypass.** The only tokens it recognises are set
  exclusively by the matching command handler; `accept_state_jump` and `accept_audit_mismatch`
  are not among them, and clobbering either fails **closed** (the acknowledgement simply has to
  be re-issued). `test_skip_confirm_alone_still_refuses_no_pending_confirmation` pins that a
  bare `skip --confirm` on a mismatched branch is stopped by the guard.

## State / audit / evidence integrity check

- No `state.json` field added; `CURRENT_VERSION` stays `"1.14"`; `VERSION_MIGRATION` stays at
  14 rows; `templates/state.json` byte-identical. `lint-skill`'s
  `migration_covers_every_state_field` and `version_string_consistent` both PASS.
- `branch_guard` writes only through `append_audit` + `save_state`, the single-writer path, so
  the hash chain is extended normally. `CONFIRMABLE` gains a sixth member and
  `pending_confirm_action` keeps its existing single-slot semantics.
- `execution.json` gains a `git` object. It carries no schema linting and its test asserts
  individual keys, so nothing regressed; `workitem.json`'s exact-key assertion
  `set(doc["git"]) == {"initialBranch"}` still holds.
- `workitems/.active-context.json` is gitignored in the shipped `.gitignore` and in
  `conftest.init_git`'s mirror; `test_the_active_context_is_ignored_by_git` asserts both,
  using a real `git check-ignore`. This keeps it out of the Phase-17 security-review diff,
  which excludes only `paths.runtime_relative + "/"`.
- The worktree test proves per-WorkItem `lock` files, byte-unchanged neighbour `state.json`
  and `audit.md`, and no repository-global `.workflow/` — contract §9's exit criterion, and
  TP-009 (no global lock) with it.

## Cross-platform / path handling check

- `lint-skill`'s `no_powershell_only_cmdlets` PASS; the new prompt text embeds only
  `sdle.sh …` invocations.
- No new dependency and no syntax beyond what `sdle.py` already used; standard library only.
- `discover_project_root` uses `Path.parents`, which terminates at a Windows drive root;
  `_within` uses `Path` equality, which is case-folding on Windows and exact on POSIX — correct
  on both. `resolve_paths` guards `Path.cwd()` with `except OSError`.
- `cwd_workitem` uses `Path.relative_to` inside `try/except ValueError`, not string prefixes.
- `runtime_relative` still normalises to `/`; emitted paths unchanged.
- The symlink case degrades without a skip: `test_validate_detects_a_symlinked_workitem_directory`
  falls back to asserting the `resolve()`-based escape rule directly (plan F13), and
  `test_validate_detects_a_traversal_shaped_index_id` gives `path_escape` deterministic
  coverage on every host regardless. `skipped="0"` in the JUnit XML confirms no skip occurred.
- `git worktree add` succeeded on this host (git 2.46.2.windows.1) and the test asserts
  `returncode == 0` rather than skipping.

## Artifact review/SHA freshness check

- `tools/transition/validate.py` exit 0 — `control-plane.sha256` verifies against the tree.
- `docs/transition/transition.md`, `docs/transition/templates/`, `tools/transition/` and
  `docs/transition/phases/T03-plan.md` are **byte-unchanged** by the implementation commit
  (`git diff --stat 767b657 beb28f2 -- …` empty). No prior phase's plan, handoff, checkpoint or
  verification was modified.
- The implementation commit under verification is `beb28f2`; `progress.md`'s T03 `Commit` cell
  still reads `UNCOMMITTED` from the implementer's context and is corrected to `beb28f2` by
  this verification, per §25 rule 7.
- `.claude/settings.local.json` remains uncommitted and out of scope, as declared.

## Findings

### Blocking

None.

### Non-blocking

1. **Declared fail-open window in `branch_guard`, reproduced here (see the trace above).**
   Switching branch *between* the two steps of `skip`, `reset`, `restart` or
   `implement preflight` lets the critical action run with no `branch_mismatch_guard` and no
   `branch_mismatch_accepted` in the ledger. Correctly declared as Known Limitation 1 and
   correctly bounded, but it should be closed when a `state.json` schema change is next on the
   table — **T11 hardening** is the natural home. The minimal fix is a second, dedicated
   pending key (e.g. `pending_branch_ack`) so the branch acknowledgement and the command's own
   confirmation stop sharing one slot.
2. **Handoff over-cites the plan.** Divergence 2 states that sticky acknowledgement is
   something "plan D5 considered and rejected". `T03-plan.md` §D5 does not mention sticky
   acknowledgement anywhere; it rejects only "invent a bypass flag". The *engineering*
   conclusion still holds (sticky acknowledgement needs new state, which P11 excludes), but the
   citation is not supported by the plan text.
3. **Handoff evidence error.** It claims
   `grep -rn "pytest.mark.skip\|pytest.skip(\|xfail" tests/` → "no matches". That pattern does
   match `tests/test_units_infra.py:49`'s `@pytest.mark.skipif(SH is None, …)`. The marker is
   pre-existing at `ab889a1`, unchanged by T03, and did not fire (`skipped="0"`), so the
   *conclusion* — T03 added no skip or xfail — is correct; the *evidence* as written is not.
4. **`ACTIVE_CONTEXT_SETTERS` is dead in production code** (invariant 7 smell). It is
   referenced only by a test; the real `setBy` values are string literals at the three call
   sites. A second, inert statement of one fact that can drift silently. Either wire it into
   the call sites or drop it.
5. **`cmd_workitem_use` is not error-hardened like its siblings.** `cmd_init` and
   `cmd_migrate_workflow` wrap `write_active_context` in `try/except OSError`;
   `cmd_workitem_use` wraps neither `write_active_context` nor `clear_active_context`, so a
   filesystem error there escapes as a traceback rather than as a contract exit code.
6. **`cmd_workitem_use` reuses the reason string `workitem_required` for a `UsageError`
   (exit 2)** when neither `--workitem` nor `--clear` is given, colliding with the resolution
   refusal (exit 1). Declared by the implementer as Known Limitation 2; the exit code
   disambiguates, but the reason string is a second meaning for one name.
7. **Edge-case ordering change, untested.** `resolve_decision` reads the index *before* the
   `for_init` legacy check, so `init` in a repository that has **both** a corrupt
   `workitems/index.md` and a legacy `.workflow/state.json` now reports `index_malformed`
   (exit 3) instead of `legacy_workflow_present` (exit 1). This fails closed and is arguably
   better, but it is a behaviour change nothing pins.
8. **Slightly misleading ledger entry.** On a mismatched branch, the second invocation of a
   critical command audits `branch_mismatch_accepted` even when the command then refuses for
   its own reason (e.g. `skip` when `status != "failed"`). Harmless, but the ledger records an
   acceptance for an action that did not occur.
9. **Plan D9's wording is imprecise** — it says the hook's `launch_cwd` is always the project
   directory. In fact `resolve_paths` sets `launch_cwd` to the real CWD whenever that CWD is
   inside the resolved root, so the hook can take rung 2. Behaviourally this only makes the
   hook resolve *more* like the engine, which is the intent; noted so a later phase does not
   rely on the plan's sentence.
10. **`SKILL.md`'s branch-mismatch paragraph slightly overstates the re-run.** "Re-run the same
    command — which proceeds" is exact for the five single-step critical commands, but for
    `skip`, `reset`, `restart` and `implement preflight` the re-run yields the command's own
    confirmation step first. The Reference Guide states the two-acknowledgement rule correctly;
    `SKILL.md` could borrow that sentence.

## Final result rationale

All twenty acceptance criteria are met on independently re-derived evidence: **438 collected,
438 passed, raw exit 0, `errors=0 failures=0 skipped=0`** in the JUnit XML; `lint-skill` 22/22
at v1.14 with 14 migration rows; `validate.py` exit 0; the must-not-change set byte-identical to
`ab889a1`, including `.claude/hooks/hooks.py`. The three headline risks were checked by
reproduction rather than by reading the handoff: the plan-D5 livelock is real (so divergence 2
is justified), NB-3 really is closed (the hook emits `permissionDecision: ask` with zero hook
edits), and the declared fail-open window is real and bounded exactly as declared. The whole
`ab889a1..beb28f2` diff — not only the parts the handoff narrates — was reviewed against the
plan; the file set matches the plan's prediction with no drift across the two implementer
contexts, and the checkpoints' inaccurate claims were never relied upon. §9's absolute ambiguity
rule, T02's refuse-over-guess ladder, the legacy dual-read rung, `migrate-workflow`'s
non-mutation of `.workflow/`, the single-writer invariant and the exit-code contract are all
intact; rungs 5 and 6 remain prompt-layer and parent-session only; the T04 `.workflow/` prefix
bridge is untouched; and the documentation layer describes the shipped engine accurately. The
ten findings above are non-blocking: one is a declared, bounded residual risk in a guard that
did not previously exist, and the rest are narrative, hygiene or untested-edge items that
change no acceptance criterion.

The single authoritative result line for this artifact is the `**Result:**` line in the
header block above, and it reads `PASS`.
