# T01 Implementation Handoff — Attempt a01

**Phase:** T01
**Attempt:** 01
**Implementer context:** fresh/isolated
**Status recommendation:** IMPLEMENTED

## Inputs read from disk

- `docs/transition/phases/T01-plan.md` (the plan executed; not modified)
- `docs/transition/transition.md` — §7 (full T01 definition, naming rules,
  auto-generation, metadata shape, registry shape, compatibility behavior, new
  tests, exit criterion), §24.3, TP-001/002/003/008
- `docs/transition/baseline.md` — §3 (suite figures), §4.1/§4.3, §5, §6.1, §7
- `docs/transition/progress.md`, `T00-handoff-a01.md`,
  `T00-verification-a01.md`, `T00-blocker.md`
- `docs/transition/phases/README.md`, `docs/transition/templates/*`,
  `docs/transition/control-plane.sha256`, `tools/transition/validate.py`
- Product source: `scripts/sdle.py` (parser, helpers, lint checks),
  `.claude/skills/sdle/SKILL.md`, `.claude/commands/sdle-start.md`,
  `README.md`, `docs/SDLE-Reference-Guide.md`, `scripts/README.md`,
  `tests/conftest.py`, `tests/test_units_cli.py`, `.gitignore`
- Live Git evidence (see **Git evidence**)

### Plan-versus-repository divergence, declared

`T01-plan.md` records HEAD `a12b9e2` at planning time and its quick-start item 2
says to stop if HEAD differs. Actual HEAD at implementation start is
`a40c7ac`. `git diff --name-status a12b9e2..HEAD` is exactly:

```
A	docs/transition/phases/T01-plan.md
M	docs/transition/progress.md
```

i.e. the planner's own commit, control-plane only, zero product files. The
plan's evidence base has not moved, so the divergence is benign and work
proceeded. It is recorded here rather than silently absorbed. `a12b9e2`
remains the rollback point named by the plan.

## Changes made

| File | Change |
|---|---|
| `scripts/sdle.py` | New `WorkItem identity` section between `init / state / header` and `Artifact path resolution`; one `workitem` parser group in `build_parser()`. **320 insertions, 0 deletions.** No existing function body modified. |
| `.claude/commands/sdle-start.md` | New step 3 (WorkItem prompt + `workitem create`) before `init`, which becomes step 4; steps renumbered to 6. Resume branch states it never asks for a WorkItem name. |
| `.claude/skills/sdle/SKILL.md` | Step 1 new-workflow paragraph gains an "Identity comes before initialisation" paragraph before `init`. No constant table touched. |
| `README.md` | `start workflow` row notes the name prompt; new `### WorkItem identity` subsection under Commands (with the `workitem.json` example); `workitems/` added to the target-project File Layout. |
| `docs/SDLE-Reference-Guide.md` | Unnumbered `### WorkItem identity` subsection before §4.3. No section number, TOC entry, or header version line changed. |
| `tests/test_units_workitem.py` | **New file**, 57 cases. |
| `scripts/README.md` | **Not edited** (plan U6): it documents the output contract, exit codes and constants; it does not enumerate subcommands. |

New symbols in `scripts/sdle.py`: `WORKITEM_ID_RE`, `AUTO_ID_RE`,
`WORKITEM_NAME_MAX`, `RESERVED_NAMES`, `INDEX_HEADING`, `INDEX_COLUMNS`,
`_RAW_NAME_FORBIDDEN`, `_INDEX_UNSAFE`, `_name_invalid()`,
`normalize_workitem_name()`, `workitems_root()`, `workitem_index_file()`,
`workitem_dir()`, `_index_malformed()`, `read_index()`, `_index_cell()`,
`append_index_row()`, `_git_value()`, `cmd_workitem_create()`,
`cmd_workitem_list()`.

## Deliberate behavior changes

1. **`sdle workitem create` / `sdle workitem list`** (plan D1). Standard
   envelope, standard exit codes. `resolve` and `validate` are T03 and are not
   implemented.
2. **Deterministic normalization** (D2), contract §7 rules 1-9; uniqueness
   (rule 10) enforced by the caller against the registry *and* the directory
   listing, case-insensitively (D7).
3. **Two id shapes** (D3): normalised kebab-case, or
   `WI-<normalised-name>-<YYYYMMDDTHHMMSSZ>` under `--auto-generate`. The `WI-`
   prefix and the `T`/`Z` of the timestamp keep their case; only the inferred
   name segment is normalised.
4. **`workitems/<id>/workitem.json`** (D4) with exactly the contract key set;
   `title` = raw name after trim; `type` defaults to `enhancement` and is not
   policed (T06 owns the vocabulary); `synopsis` defaults to `null`;
   `createdBy` and `git.initialBranch` from `git()`, `null` when unknowable —
   never a refusal; `sdleVersion` = `CURRENT_VERSION` (`1.13`, unchanged).
5. **`workitems/index.md`** (D5): append-only, no status column, structure
   validated before every append, whole file rebuilt in memory and written via
   `write_atomic`. No hash chaining (contract §7 says not yet).
6. **Refusal vocabulary** (D6), unchanged from the plan:
   `workitem_name_invalid` (exit 1, with a `data.rule` discriminator),
   `workitem_exists` (exit 1, `data.id` names the existing WorkItem),
   `index_malformed` (exit 3). Nothing is written on any refusal.
7. **Bootstrap order** (D9/D10): preflight → WorkItem name → `workitem create`
   → `init`. Resume path unchanged and never prompts.

### Two decisions the plan implies but does not spell out

**(a) Raw-name pre-check before normalization.** Contract rule 5 ("remove
unsupported punctuation") applied alone turns `a/b` into the *valid* id `ab`,
which would silently accept a traversal-shaped name and make plan acceptance
criterion A4 unsatisfiable. `_RAW_NAME_FORBIDDEN` refuses a raw name containing
`/`, `\`, `|` or a control character *before* normalization, folded into
`workitem_name_invalid` with `data.rule = "unsafe_character"`. No new refusal
reason was invented; D6's vocabulary is unchanged.

**(b) Registry cells are sanitized on write, not refused.** `_split_row` has no
escape support, so a single `|` or newline in a free-text `--synopsis` would
make every later `create` and `list` exit 3 — the engine would corrupt its own
ledger. `_index_cell()` replaces `|`, `\r`, `\n`, `\t` with a space, collapses
whitespace runs, and renders an empty cell as `-`. `workitem.json` keeps the
text verbatim, so no information is lost. Pinned by
`test_a_pipe_in_the_synopsis_cannot_corrupt_the_registry`.

## Preserved behavior / invariants

| # | Invariant | Evidence |
|---|---|---|
| P1 | `.workflow/` is still the runtime state location | No `Paths` property added or re-pointed; `git diff` on `templates/state.json` empty |
| P2 | Lock behavior unchanged | Neither new command calls `touch_lock`; `--session` has no effect on them |
| P3 | 18 phases / 8 gates unchanged | No constant table edited; `lint-skill` parses 19 phases, 8 gates, 13 migration rows as before |
| P4 | Spec Kit feature behavior unchanged | `current_feature_id`, `feature resolve`, `preflight` untouched |
| P5 | No state field, no version bump, no migration row | `test_init_records_no_workitem_in_state`; `templates/state.json` diff empty; `CURRENT_VERSION` still `1.13` |
| P6 | Exit-code and envelope contracts | New commands use `emit()`, `Refused`, `IntegrityError` only; `test_a_refusal_survives_the_process_boundary` |
| P7 | Atomic writes | Both writers go through `write_atomic`; no `open(..., "w")` added |
| P8 | Audit chain untouched | `append_audit` not called by T01 — see the note below |
| P9 | Deterministic repeat behavior | `workitem list` is pure; a repeated `create` refuses deterministically |
| P10 | Stdlib-only, 3.11-compatible | No import added (import block unchanged at lines 19-31); no PEP 695/3.12+ syntax |
| P11 | Resume path unchanged | `sdle-start.md` step 2 untouched apart from the explicit "never asks" sentence |
| P12 | Four hooks unchanged | `git diff --exit-code` on `.claude/hooks/` and `.claude/settings.json` returns 0 |

**No audit entry on `workitem create`** — deliberate, per the plan. `append_audit`
requires a live `state` dict, and `read_state` raises `state_unreadable` before
`init`. Writing one would mean creating `.workflow/state.json` early (a T02
behavior) or failing open. The index row plus `workitem.json`, both versioned in
Git, are the durable creation record. This is now also stated in the Reference
Guide so the omission is visible to a reader, not just to a verifier.

**Declared deviation, carried forward from the plan:** baseline §4.3 marks
`project_name` `ADAPT@T01`. T01 leaves it unchanged — `init` still infers it
from the first `#` heading or `--project`. The rebinding requires state to
reference the WorkItem, which is a state-schema change (P5) and belongs to T02.
Contract §7 never mentions `project_name`; the deviation is from a T00
prediction, not from the contract. It is **not** silently closed.

## Test changes and TP-003 classification

| Test | Category | Rationale |
|---|---|---|
| *(none)* | — | **The set of deliberately modified existing tests is EMPTY.** `git diff --name-only -- tests/` returns nothing. The only addition under `tests/` is the new file `tests/test_units_workitem.py`. |

All 230 pre-existing tests are TP-003 **category 1** (unchanged behavior, must
remain green). Category 2 (deliberately superseded) and category 3 (defect
discovered) are both empty for this phase.

One defect was found and fixed *inside the new test file* during development, and
is recorded for completeness: a parametrized case passed `--foo--bar--`
positionally, which argparse consumed as an option (exit 2). Replaced with the
`--name=--foo--bar--` form in a dedicated case. That was a test-authoring bug in
new code, not a product refusal and not a change to any regression asset.

### Coverage of contract §7's "New tests" list

| Contract item | Cases in `tests/test_units_workitem.py` |
|---|---|
| normalization | `test_a_name_normalizes_to_kebab_case` (8 params), `test_leading_and_trailing_hyphens_are_stripped` |
| unsafe / path-traversal names | `test_an_unsafe_name_refuses_and_writes_nothing` (15 params), `test_a_64_character_name_is_still_accepted` |
| duplicate names | `test_a_duplicate_refuses_and_leaves_every_byte_in_place`, `test_a_case_only_collision_refuses`, `test_a_stray_directory_with_no_index_row_refuses`, `test_no_auto_suffix_is_ever_invented` |
| auto-generation | `test_auto_generate_mints_a_timestamped_id_and_keeps_its_case`, `test_an_auto_generated_name_segment_is_normalized` |
| index append | `test_the_first_create_writes_the_registry_skeleton`, `test_a_second_create_appends_and_leaves_the_first_row_byte_identical`, `test_a_pipe_in_the_synopsis_cannot_corrupt_the_registry` |
| index malformed | `test_a_malformed_index_is_an_integrity_failure_and_is_never_repaired` (5 bodies × 2 commands) |
| metadata creation | `test_metadata_carries_exactly_the_contract_key_set`, `test_type_and_synopsis_default`, `test_an_explicit_type_is_recorded_without_being_policed` |
| Git identity capture | `test_git_identity_and_branch_are_captured`, `test_missing_git_identity_yields_nulls_without_refusing` |
| exit criterion / coexistence | `test_creating_a_workitem_creates_no_runtime_state`, `test_init_records_no_workitem_in_state`, `test_a_workitem_does_not_change_what_init_and_advance_produce` |
| list | `test_list_with_no_registry_is_empty_and_succeeds`, `test_list_projects_the_registry_in_creation_order`, `test_list_reads_the_registry_not_the_directory_listing` |
| CLI boundary | `test_a_refusal_survives_the_process_boundary`, `test_a_missing_name_is_a_usage_error` |

**Test hygiene.** An autouse `isolated_git_identity` fixture points
`GIT_CONFIG_GLOBAL` / `GIT_CONFIG_SYSTEM` at a nonexistent path and sets
`GIT_CONFIG_NOSYSTEM=1`, so no test can read or assert the developer's real Git
identity. The only identity any test asserts is the fixture's
`SDLE Test <test@example.invalid>`. The expected branch name is read from the
fixture repo at runtime, never hardcoded (`init.defaultBranch` varies by
machine). No `workitems/` directory is created in the source repository — every
case runs under `tmp_path`; `git status --porcelain` confirms none exists.

## Commands actually run

| Command | Result | Evidence/summary |
|---|---|---|
| `git status --porcelain` (start) | exit 0, empty | Working tree clean |
| `git rev-parse HEAD` / `git branch --show-current` | `a40c7ac33ef6a759203d1ca02fce4a0a571051c5`, `transition/workitem-v1` | See divergence note |
| `git diff --name-status a12b9e2..HEAD` | 2 rows | `A T01-plan.md`, `M progress.md` — control-plane only |
| `python scripts/sdle.py workitem --help` | exit 0 | Lists `create`, `list` |
| `python -m pytest tests/test_units_workitem.py -q` (dev) | exit 0 | `57 passed in 41.81s` |
| `python scripts/sdle.py lint-skill` after `sdle-start.md` | exit 0 | 22/22 PASS |
| `python scripts/sdle.py lint-skill` after `SKILL.md` | exit 0 | 22/22 PASS |
| `python scripts/sdle.py lint-skill` after `README.md` | exit 0 | 22/22 PASS |
| `python scripts/sdle.py lint-skill` after `SDLE-Reference-Guide.md` | **exit 0** | **22 checks, 22 PASS** (`tables_wellformed`: "Parsed 19 phases, 8 gates, 13 migration rows.") |
| `python -m pytest -q` (full suite) | **RAW EXIT 1** | `3 failed, 284 passed in 374.03s` — 287 collected = 230 baseline + 57 new |
| `python -m pytest -q <the 3 failing node ids>` (F1 re-run 1 of ≤3) | exit 0 | `3 passed in 9.60s` |
| scratch probe: `init` then `advance --to gate_constitution` | exit 0 / exit 0 | Established that A10's advance genuinely succeeds rather than merely matching the control |
| `python -m pytest -q tests/test_units_workitem.py` (after tightening the A10 assertion) | exit 0 | `57 passed in 81.55s` — case count unchanged, so the full-suite figures above still hold |
| `python tools/transition/validate.py` | exit 0 | `TRANSITION_VALID: complete=1/12 next=T01` |
| Acceptance commands A1-A3, A5, A7, A8, A14-A16, A18 | see table below | Run in a scratch project outside the repo |
| Python 3.11 syntax/CI verification | **NOT_RUN** | No 3.11 interpreter on this host (`py -3.11` → "No suitable Python runtime found"); local evidence is Python 3.14.6 / pytest 9.1.1 on Windows only. CI has not been run — the branch is not pushed. |

### Full-suite failures and the F1 procedure

The three failures were all `PermissionError: [WinError 5]` at
`scripts/sdle.py:463` (`os.replace` inside `write_atomic`) — the inherited
baseline flake (`baseline.md` §6.1, plan E31/F1). Verbatim summary:

```
FAILED tests/test_integration_02_to_05.py::test_03_successful_verification_resets_the_retry_counter
FAILED tests/test_integration_02_to_05.py::test_04_rejection_clears_the_queue_and_does_not_resume
FAILED tests/test_integration_02_to_05.py::test_04_approving_out_of_queue_order_is_refused
3 failed, 284 passed in 374.03s (0:06:14)
RAW_EXIT=1
```

Representative traceback tail (all three are the same shape):

```
scripts\sdle.py:576: in save_state
    write_atomic(paths.state_file, json.dumps(state, indent=2) + "\n")
>           os.replace(handle.name, path)
E           PermissionError: [WinError 5] Access is denied: '...\.workflow\.state.json.n5w604dx.tmp' -> '...\.workflow\state.json'
scripts\sdle.py:463: PermissionError
```

F1 step 1 — re-ran exactly those three node ids, verbatim output:

```
...                                                                      [100%]
3 passed in 9.60s
RAW_EXIT=0
```

All three passed on re-run **1 of an allowed 3** ⇒ classified
**`ENVIRONMENT_FLAKE`** under F1 step 2. `write_atomic` was **not** patched: the
retry/backoff decision is a human decision scheduled for T02 planning, and the
row is `PRESERVE`, anchored by
`tests/test_units_infra.py::test_write_atomic_leaves_no_partial_file_on_failure`.
The raw suite exit code is reported as observed (**1**), not restated as 0.

Note for the verifier: three victims in one run, and two of the node ids are new
relative to the six previously recorded. This is consistent with plan E31
("arbitrary node ... expect one not previously recorded") and does not change
the classification, but the count is higher than the 1-2 the plan predicted.

### Acceptance criteria — observed results

| # | Result | Evidence |
|---|---|---|
| A1 | PASS | `workitem create --name "Customer Notification Service"` exit 0; `workitems/customer-notification-service/workitem.json` and `workitems/index.md` written; index = `# Work Items`, blank line, header row, separator, exactly one data row |
| A2 | PASS | Exact D4 key set; `id` == `name` == `customer-notification-service`; `title` == `Customer Notification Service`; `type` == `enhancement`; `createdAt` == `2026-08-23T12:53:37Z` (matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`); `sdleVersion` == `1.13` == `CURRENT_VERSION` |
| A3 | PASS | Re-run exit **1**, `reason == "workitem_exists"`, `data.id == "customer-notification-service"`; SHA-256 of `index.md` and of the existing `workitem.json` identical before and after |
| A4 | PASS | `test_an_unsafe_name_refuses_and_writes_nothing` — `../escape`, `..`, `a/b`, `a\b`, `.`, `   `, `""`, `!!!`, `a`×65, `con`, `NUL`, `com1`, `a|b`, `/etc/passwd`, `C:/absolute/path` all exit 1 `workitem_name_invalid`; asserts `workitems/` does not exist and no `escape` directory appears inside or beside the project root |
| A5 | PASS | `--auto-generate` exit 0, id `WI-payment-retry-20260823T125403Z`, matches `^WI-[a-z0-9]([a-z0-9-]*[a-z0-9])?-\d{8}T\d{6}Z$`, uppercase `WI-`/`T`/`Z` preserved |
| A6 | PASS | `test_a_case_only_collision_refuses` — pre-existing `workitems/Payment-Retry` makes `Payment Retry` exit 1 `workitem_exists` with `data.id == "Payment-Retry"` |
| A7 | PASS | Mangled index (header row missing the `Synopsis` column): `create` exit **3** `index_malformed`, `list` exit **3** `index_malformed`, file SHA-256 unchanged, no `late-arrival` directory created. Four more malformed shapes covered by the parametrized test |
| A8 | PASS | Empty registry → exit 0, `{"count": 0, "workitems": []}`. After two creates → `count == 2`, ids in creation order `['customer-notification-service', 'WI-payment-retry-20260823T125403Z']`, each entry carrying `id`/`created`/`type`/`title` |
| A9 | PASS | `test_git_identity_and_branch_are_captured` (fixture identity + branch read at runtime) and `test_missing_git_identity_yields_nulls_without_refusing` (all three `null`, exit 0, keys still present) |
| A10 | PASS | `test_a_workitem_does_not_change_what_init_and_advance_produce` — control project copied before creation; `create` exit 0, `init` exit **0** in both and exit codes equal, `current_phase`/`status`/`progress`/`project_name`/`workflow_version` equal, `header` exit **0**, `advance --to gate_constitution` exit **0** (asserted as success, not merely as equal to the control) and the resulting `current_phase` equal. Verified empirically before the assertion was tightened: in a scratch project `init` → exit 0, `advance --to gate_constitution` → exit 0, `current_phase == "gate_constitution"`. New test file re-run after the change: `57 passed in 81.55s`, exit 0 |
| A11 | PASS | `test_init_records_no_workitem_in_state`; `git diff --exit-code -- .claude/skills/sdle/templates/state.json` exit 0 |
| A12 | PASS | `lint-skill` exit 0, **22 checks, 22 PASS** |
| A13 | PASS (with declared flake) | Full suite raw exit 1, 3 failed / 284 passed, all three `ENVIRONMENT_FLAKE` under F1. `git diff --name-only -- tests/` empty; only addition under `tests/` is `tests/test_units_workitem.py` (`?? tests/test_units_workitem.py`) |
| A14 | PASS | `git status --porcelain`: `M` on `sdle-start.md`, `SKILL.md`, `README.md`, `SDLE-Reference-Guide.md`, `scripts/sdle.py`; `??` on `tests/test_units_workitem.py` and the transition evidence files. `git diff --exit-code` returns 0 for `templates/state.json`, `modules/`, `.claude/hooks/`, `.claude/settings.json`, `.gitignore`, `scripts/sdle.sh`, `scripts/sdle.ps1`, `.github/` |
| A15 | PASS | `git check-ignore workitems/index.md` exit **1**; `git check-ignore workitems/x/workitem.json` exit **1** — neither is ignored, no `.gitignore` edit needed |
| A16 | PASS | `git diff --stat -- scripts/sdle.py` = `320 ++++…`, `1 file changed, 320 insertions(+)` — **zero deletions** |
| A17 | PASS | `python tools/transition/validate.py` exit 0 |
| A18 | PASS | Import block unchanged (lines 19-31: `argparse, hashlib, json, os, re, subprocess, sys, tempfile, dataclasses, datetime, pathlib`); no import added. No PEP 695 `type` statement, no `itertools.batched`, no `Path.walk`. **A 3.11 interpreter is not available on this host, so a 3.11 compile check is `NOT_RUN`** — the claim is a source-level review, not an execution result |

## Git evidence

- **HEAD:** `a40c7ac33ef6a759203d1ca02fce4a0a571051c5` on branch
  `transition/workitem-v1`. Nothing was committed by this context.
- **Rollback point:** `a12b9e238a08fb7f1837c01e2f4c672f84d4639e` (plan §Rollback).
- **Working tree:** dirty by design, uncommitted:

```
 M .claude/commands/sdle-start.md
 M .claude/skills/sdle/SKILL.md
 M README.md
 M docs/SDLE-Reference-Guide.md
 M scripts/sdle.py
?? docs/transition/phases/T01-checkpoint-a01-01.md
?? docs/transition/phases/T01-checkpoint-a01-02.md
?? docs/transition/phases/T01-handoff-a01.md
?? tests/test_units_workitem.py
```

  (`docs/transition/progress.md` becomes `M` once the T01 row is set to
  `IMPLEMENTED`, which is the last write of this attempt.)
- **Diff scope:** five product files modified, one product test file added,
  transition evidence added. `scripts/sdle.py` is additive only (320/0).

## Known limitations / risks

1. **`write_atomic` WinError 5 flake is still present and unfixed** — three
   victims in this run, two of them not previously recorded. Classified
   `ENVIRONMENT_FLAKE` under F1; the fix is a human decision at T02 planning.
   A verifier's full run will very likely show a different victim set.
2. **Python 3.11 and CI are unverified.** No 3.11 interpreter on this host and
   the branch is not pushed. Both are `NOT_RUN`, not `PASS`. No CI outcome is
   predicted.
3. **`workitems/` is not covered by the hook write fence.** Deliberate — the
   hook row is `ADAPT@T02`. Git and the deterministic append path are the
   integrity controls meanwhile.
4. **`init` still does not know about WorkItems.** Ordering is enforced only at
   the orchestration layer (`sdle-start.md` + `SKILL.md` Step 1). That is
   contract §7's "added alongside the legacy runtime"; deterministic binding is
   T02.
5. **Registry sanitisation is lossy for the index cell only.** A `|` in a
   synopsis becomes a space in `index.md`; `workitem.json` keeps it verbatim.
6. **`project_name` is not rebound** (declared deviation, above).
7. Metadata legitimately captures whatever Git identity is configured at
   creation time. That is the contract §7 design; test isolation guarantees no
   real identity reaches test output or any file in this repository.

## Claims for verifier to independently check

1. `git diff --name-only -- tests/` is empty, and `tests/test_units_workitem.py`
   is the only addition under `tests/` — no regression asset was weakened.
2. `git diff --stat -- scripts/sdle.py` shows insertions only; read the diff and
   confirm no existing function body was altered, in particular not
   `write_atomic`, `now_iso`, `actor`, `parse_md_table`, `cmd_init`.
3. `templates/state.json`, `modules/*`, `.claude/hooks/hooks.py`,
   `.claude/settings.json`, `.gitignore`, `scripts/sdle.sh`, `scripts/sdle.ps1`
   and `.github/workflows/ci.yml` are byte-identical to `a12b9e2`.
4. `CURRENT_VERSION` is still `1.13`; no `VERSION_MIGRATION` row was added; the
   version string still matches in all four documents (`lint-skill` check
   `version_string_consistent`).
5. `lint-skill` exits 0 with 22/22 — re-run it yourself rather than trusting
   this file.
6. Re-run the full suite and apply F1 independently; expect a different flake
   victim set. Confirm the only non-flake outcome is green.
7. Scope-leakage sweep (plan F5): no `workitem` key in `state.json`, `init`
   neither requires nor records a WorkItem, `workitems/` absent from the write
   fence, no `Paths.workitem_*` property, no `workitem resolve`, no execution
   identity, no `migrate-workflow --workitem`.
8. Independently exercise A1-A11 and A14-A16 in a scratch project; do not trust
   the table above.
9. Confirm the two undocumented-in-plan decisions (raw-name pre-check; index
   cell sanitisation) are acceptable narrowings rather than scope leakage. Both
   are refusals/normalisations inside the T01 surface, and neither adds a
   refusal reason beyond D6.
10. Confirm the declared `project_name` deviation is still declared and not
    quietly closed, and that `.workflow/` has not moved.
11. Confirm no `workitems/` directory was created in the source repository by
    any test.

## Blocker (only if material decision is required)

None. No material architectural or user decision arose; no `T01-blocker.md` was
written.
