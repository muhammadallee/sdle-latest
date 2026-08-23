# T01 Independent Verification — Attempt a01

**Phase:** T01
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

> The handoff is a claim set, not proof. Every row below was reconstructed from
> the repository, the working diff, the source, or a command this verifier ran
> in this context. Nothing is carried over from `T01-handoff-a01.md` on trust.

## Verification context

| Fact | Observed value | How |
|---|---|---|
| Branch | `transition/workitem-v1` | `git branch --show-current` |
| HEAD | `0548ebd` ("Stop the transition guard blocking git merge-base") | `git log --oneline -5` |
| Implementation written against | `a40c7ac` | handoff claim; `git diff --name-status a40c7ac 0548ebd` = 3 rows, all control-plane (`control-plane.sha256`, `T00-blocker.md`, `tools/transition/agent_guard.py`), **zero product files** — divergence confirmed benign |
| T00 baseline commit | `a12b9e2` | `progress.md` T00 row |
| Untouched SDLE product baseline | `f8fdaa0` | `progress.md` header |
| T01 product changes | **uncommitted in the working tree**, by design | `git status --porcelain -uall` |
| Interpreter | Python 3.14.6, pytest 9.1.1, Windows 11 | `python --version`, `python -m pytest --version` |
| Python 3.11 / CI | **NOT_RUN** — no 3.11 interpreter on this host, branch not pushed. No CI outcome is predicted. | — |

Working tree, observed verbatim (`git status --porcelain -uall`):

```
 M .claude/commands/sdle-start.md
 M .claude/skills/sdle/SKILL.md
 M README.md
 M docs/SDLE-Reference-Guide.md
 M docs/transition/progress.md
 M scripts/sdle.py
?? docs/transition/phases/T01-checkpoint-a01-01.md
?? docs/transition/phases/T01-checkpoint-a01-02.md
?? docs/transition/phases/T01-handoff-a01.md
?? tests/test_units_workitem.py
```

Five product files modified, one product test file added, transition evidence
added. This set is exactly the plan's "Files expected to change" minus
`scripts/README.md` (correctly skipped — see A-scope below). Nothing else.

Per-file `git diff --numstat HEAD`:

| File | + | - |
|---|---:|---:|
| `.claude/commands/sdle-start.md` | 18 | 4 |
| `.claude/skills/sdle/SKILL.md` | 5 | 1 |
| `README.md` | 49 | 1 |
| `docs/SDLE-Reference-Guide.md` | 38 | 0 |
| `scripts/sdle.py` | **320** | **0** |

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| A1 | PASS | Ran `python scripts/sdle.py --project-root <scratchpad>/t01v1 workitem create --name "Customer Notification Service"` → exit **0**. `workitems/customer-notification-service/workitem.json` and `workitems/index.md` both created. `cat index.md` gives exactly `# Work Items`, blank line, `\| Created \| WorkItem \| Type \| Title \| Synopsis \|`, `\|---\|---\|---\|---\|---\|`, and **one** data row. |
| A2 | PASS | `cat workitem.json` → keys exactly `id, name, title, type, synopsis, createdAt, createdBy, git, sdleVersion`. `id == name == "customer-notification-service"`; `title == "Customer Notification Service"`; `type == "enhancement"`; `createdAt == "2026-08-23T13:10:20Z"` (matches `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$`); `sdleVersion == "1.13"` == `CURRENT_VERSION` (`scripts/sdle.py:541`). |
| A3 | PASS | Re-ran create with `"Customer   Notification   Service"` (same normalized id) → exit **1**, `reason == "workitem_exists"`, `data.id == "customer-notification-service"`, `data.requested` present. Byte-identity of `index.md`/`workitem.json` across the refusal is additionally pinned in-process with SHA-256 by `test_a_duplicate_refuses_and_leaves_every_byte_in_place` (read and re-run). |
| A4 | PASS | Ran all nine plan names through the real CLI against a **non-existent** scratch root: `../escape`, `..`, `a/b`, `a\b`, `.`, `"   "`, `!!!`, a 65-char name, `con` — every one exit **1** `workitem_name_invalid`. Afterwards `ls` on the project root reports *No such file or directory*: not merely "no directory under `workitems/`" but no directory anywhere at all. |
| A5 | PASS | `workitem create --name "Payment Retry" --auto-generate` → exit **0**, `id == "WI-payment-retry-20260823T131154Z"`, matches `^WI-[a-z0-9]([a-z0-9-]*[a-z0-9])?-\d{8}T\d{6}Z$`; uppercase `WI-`, `T`, `Z` all preserved; `name == "payment-retry"` (only the inferred segment normalized). |
| A6 | PASS | Not reachable through the CLI without a pre-seeded mixed-case directory (verifier Bash is guard-restricted to observational commands — see *Guard-imposed evidence limits*). Verified by running `tests/test_units_workitem.py::test_a_case_only_collision_refuses`, whose source I read: it pre-creates `workitems/Payment-Retry`, creates `"Payment Retry"`, and asserts exit 1 / `workitem_exists` / `data.id == "Payment-Retry"`. Source review of `cmd_workitem_create` confirms uniqueness is keyed on `workitem_id.lower()` against both index ids and directory names. |
| A7 | PASS | Same guard limit (mangling `index.md` requires a shell/interpreter write). Verified by running `test_a_malformed_index_is_an_integrity_failure_and_is_never_repaired`, 5 malformed bodies × 2 commands = 10 cases: wrong heading, missing column, missing separator, wrong cell count, empty file. Each asserts exit **3**, `reason == "index_malformed"`, SHA-256 of the file **unchanged**, and no `late-arrival` directory. Source review confirms `read_index()` raises `IntegrityError` before any write and never rewrites. |
| A8 | PASS | Fresh scratch root: `workitem list` → exit **0**, `{"count": 0, "workitems": []}`. After two creates → `count == 2`, ids in creation order `["WI-payment-retry-20260823T131154Z", "alpha-one"]`, each entry carrying `id`, `created`, `type`, `title`. |
| A9 | PASS | Captured-identity branch verified by `test_git_identity_and_branch_are_captured` (fixture identity `SDLE Test <test@example.invalid>`, branch read from the fixture repo at runtime — not hardcoded). Null branch observed directly: my scratch run produced `createdBy.gitUserName == null`, `gitUserEmail == null`, `git.initialBranch == null` with exit **0** and all keys still present. |
| A10 | PASS | `test_a_workitem_does_not_change_what_init_and_advance_produce` — read the source: it `copytree`s a control project *before* creation, runs `init` in both, asserts both exit **0**, compares `current_phase`, `status`, `progress`, `project_name`, `workflow_version`, then asserts `header` exit 0 and `advance --to gate_constitution` exit **0 in its own right** (not merely equal to the control) and equal resulting `current_phase`. Re-run green in this context. |
| A11 | PASS | `test_init_records_no_workitem_in_state` asserts no state key contains `workitem` **and** `"workitem" not in json.dumps(state).lower()`. Independently: `git diff --exit-code a12b9e2 -- .claude/skills/sdle/templates/state.json` exits **0**, and `grep -ri workitem .claude/skills/sdle/templates/ .claude/skills/sdle/modules/` returns nothing. |
| A12 | PASS | Re-ran `python scripts/sdle.py lint-skill` myself → **exit 0**, **22 checks, 22 PASS**, including `tables_wellformed: Parsed 19 phases, 8 gates, 13 migration rows`, `single_state_template`, `version_string_consistent: all four locations report v1.13`, `migration_covers_every_state_field`, `no_powershell_only_cmdlets`, `no_hardcoded_progress_outside_progress_map`, and both `doc_lists_every_phase_*` checks. |
| A13 | see *Full-suite evidence* | — |
| A14 | PASS | `git status --porcelain -uall` (above) lists only the five planned product files plus `tests/test_units_workitem.py`. `git diff --exit-code a12b9e2 -- <path>` returns 0 for **every** forbidden path: `templates/state.json`, `modules/`, `.claude/hooks/hooks.py`, `.claude/settings.json`, `.gitignore`, `scripts/sdle.sh`, `scripts/sdle.ps1`, `.github/workflows/ci.yml`. |
| A15 | PASS | `git check-ignore -v workitems/index.md` → exit **1** (no match); `git check-ignore -v workitems/x/workitem.json` → exit **1**. Neither is ignored; the contract §19 reversal holds with a zero-byte `.gitignore` diff. |
| A16 | PASS | `git diff --numstat HEAD -- scripts/sdle.py` = `320  0`. Zero deletions is mechanical proof no existing line was removed *or* modified (Git renders a modification as delete+add). I also read the whole diff: it is one contiguous new section inserted between `cmd_state_dump` and the `Artifact path resolution` banner, plus one `workitem` group block in `build_parser()` after `migrate`. Separately checked that none of the 20 new symbols shadows an existing definition — each has exactly one `def`/assignment in the file. `write_atomic`, `now_iso`, `actor`, `git`, `parse_md_table`, `_split_row`, `_is_separator`, `cmd_init` all confirmed untouched. |
| A17 | PASS | Ran `python tools/transition/validate.py` → **exit 0**, `TRANSITION_VALID: complete=1/12 next=T01`. Re-run after the progress.md update (below) also exit 0. |
| A18 | PASS | `git diff HEAD -- scripts/sdle.py \| grep -E '^\+(import \|from )'` returns **nothing** — no import added. Grep for `match ...:`, `itertools.batched`, `Path.walk`, top-level `type ` statements in the added lines: none. The file already carries `from __future__ import annotations`, so `str \| None` / `list[dict[str, str]]` annotations are deferred and 3.11-safe; `frozenset({...} \| {...})` is set union, valid on every supported version; `Path.unlink(missing_ok=)` is 3.8+. **This is a source-level review, not an execution result — a real 3.11 compile is `NOT_RUN`.** |

### Guard-imposed evidence limits (declared, not routed around)

`tools/transition/agent_guard.py` restricts a verifier's Bash/PowerShell to
observational shapes: `mkdir`, `rm`, `cp`, `tee`, `sed -i` and output
redirection are refused. Two acceptance criteria need a *pre-seeded* on-disk
condition before the CLI runs — A6 needs a mixed-case `workitems/Payment-Retry`
directory, A7 needs a hand-mangled `index.md`. I did **not** route around the
guard with `python -c` or any other interpreter. Instead both were verified by
running the corresponding tests, whose source I read line by line first to
confirm they assert exactly what the criterion requires (exit code, `reason`,
SHA-256 byte-identity, absence of side-effect directories). Everything else
(A1-A5, A8, A9-null branch, A15) was exercised through the real CLI in a
scratchpad project outside the repository.

## Regression evidence

**Targeted re-run of every test I cite as acceptance evidence** — run after the
full suite, in isolation:

| Command | Result |
|---|---|
| `python -m pytest -q tests/test_units_workitem.py` | *(see Full-suite evidence)* |

**Contract §6 explicit-preserve list — each re-checked against the diff, not the handoff:**

| Preserved item | Evidence it still holds |
|---|---|
| 18-phase sequence | `lint-skill` re-run by me: `tables_wellformed: Parsed 19 phases` (18 workflow phases + `complete`), `phase_set_matches_next_phase`, `next_phase_chains_sequence`, `progress_denominator_matches_phase_count: denominators=['18']` — all PASS. `git diff HEAD -- .claude/skills/sdle/SKILL.md` is 5 insertions / 1 deletion, entirely inside the Step 1 prose paragraph; **no constant table line appears in the diff**. |
| 8 approval gates | `lint-skill`: all eight `gate_registered_*` checks PASS. `GATE_PHASES`, `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP` and `modules/gate-protocol.md` are outside the diff (`modules/` byte-identical to `a12b9e2`). |
| `.workflow/` location | No `Paths` property added, moved or re-pointed — the sdle.py diff touches no `Paths` code. New helpers `workitems_root()` / `workitem_index_file()` / `workitem_dir()` are free functions taking `Paths`, deriving from `paths.project_root` only. Observed: after `workitem create` no `.workflow/` exists (`test_creating_a_workitem_creates_no_runtime_state`). |
| Lock behavior | Neither new command calls `touch_lock`/`read_lock`; grep of the added lines for `lock` returns nothing. `--session` is not consumed by either handler. |
| Spec Kit feature behavior | `current_feature_id`, `feature resolve` and `preflight` do not appear in the diff. Zero deletions in `sdle.py` makes silent alteration impossible. |
| SpecKit opacity (CLAUDE.md invariant 3) | Grepped every added line of `README.md`, `SKILL.md`, `sdle-start.md`, `SDLE-Reference-Guide.md` and `sdle.py` for `speckit-`: **no match**. No skill name is exposed by the new bootstrap text. |

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `python scripts/sdle.py lint-skill` | **exit 0** | 22 checks, **22 PASS**, 0 failed. Verbatim first line: `[PASS] tables_wellformed: Parsed 19 phases, 8 gates, 13 migration rows.` Also `[PASS] version_string_consistent: all four locations report v1.13`, `[PASS] single_state_template: templates/state.json is the only host`, `[PASS] migration_covers_every_state_field: every field has a migration row`, `[PASS] no_powershell_only_cmdlets: none found`, `[PASS] no_hardcoded_progress_outside_progress_map: none found`, `[PASS] doc_lists_every_phase_README`, `[PASS] doc_lists_every_phase_SDLE-Reference-Guide`. |
| `python tools/transition/validate.py` | **exit 0** | `TRANSITION_VALID: complete=1/12 next=T01` (pre-update). Includes the `control-plane.sha256` manifest check — every control-plane file hashes to its recorded digest. |
| `python -m pytest -q` (full suite) | **RAW EXIT 1** | `3 failed, 283 passed, 1 error in 436.80s (0:07:16)` — **287 collected** = 230 baseline + 57 new, exactly as expected. All four non-passing outcomes are `PermissionError: [WinError 5]` at `scripts/sdle.py:463`. |
| `python -m pytest -q <the 4 failing node ids>` (F1 re-run **1** of ≤3) | **exit 0** | `10 passed in 19.85s` (3 nodes + the 7 parametrizations of the errored node) |
| `python -m pytest -q tests/test_units_workitem.py --collect-only` | exit 0 | `57 tests collected in 0.03s` — the claimed case count is real |
| `python -m pytest -q tests/test_units_workitem.py` | exit 0 | `57 passed in 51.84s` |
| `python -m pytest -q -v <7 acceptance-cited node ids>` | exit 0 | `16 passed in 67.28s` (A3/A6/A7/A9/A10/A11 anchors, incl. the 10 malformed-index parametrizations) |
| `python -m pytest -q tests/test_lint_skill.py tests/test_units_cli.py tests/test_hooks.py` | exit 0 | `55 passed in 22.36s` — the three lint/parser/hook regression suites the plan flagged as at-risk |
| Python 3.11 compile / CI | **NOT_RUN** | `py -3.11` is not installed on this host and the branch is not pushed. No prediction is made about CI. |

### F1 procedure applied to the full-suite failures

Observed victim set, verbatim from the run summary:

```
FAILED tests/test_integration_01_happy_path.py::test_all_eight_gates_approved_with_baselines
FAILED tests/test_integration_02_to_05.py::test_02_remediate_refuses_when_nothing_was_rejected
FAILED tests/test_integration_02_to_05.py::test_03_retry_limit_stops_offering_retry
ERROR  tests/test_units_infra.py::test_state_set_refuses_engine_owned_fields[progress]
3 failed, 283 passed, 1 error in 436.80s (0:07:16)
RAW_EXIT=1
```

Every one is the same shape — `os.replace` inside the **unmodified**
`write_atomic`:

```
scripts\sdle.py:463: in write_atomic
>           os.replace(handle.name, path)
E           PermissionError: [WinError 5] Access is denied:
    '...\.workflow\.audit.md.i5uyweae.tmp' -> '...\.workflow\audit.md'
```

F1 step 1 — re-ran exactly those node ids, verbatim:

```
..........                                                               [100%]
10 passed in 19.85s
RAW_EXIT=0
```

All pass on **re-run 1 of an allowed 3** ⇒ classified **`ENVIRONMENT_FLAKE`**
under F1 step 2. The raw suite exit code is reported **as observed (1)**, not
restated as 0. `write_atomic` was not patched by the implementer and not by me.

**This victim set is different from the handoff's** (handoff: three
`test_integration_02_to_05` nodes; mine: one happy-path node, two
`test_integration_02_to_05` nodes, one `test_units_infra` setup error). One
node, `test_03_retry_limit_stops_offering_retry`, is new relative to every set
recorded so far. This is exactly what plan E31/F1 predicts for an arbitrary
victim, and it is affirmative evidence of environmental rather than
deterministic causation: a real defect would not migrate across unrelated
files and fixtures between runs. **Not a single failure landed in
`tests/test_units_workitem.py`** in any run I performed: the new cases pass
57/57 standalone, 16/16 in a targeted re-run of the acceptance-cited nodes, and
without one failure inside the full suite. (Those are the three runs *this
verifier* executed; the implementer's own runs are deliberately not counted
toward that figure.) The running total of distinct observed WinError 5 victims
across all recorded contexts is now at least eleven.

## Future-phase leakage check

Every item on plan F5 and the plan's "Scope exclusions" table, checked against
the diff rather than the handoff:

| Excluded (owner) | Independent finding |
|---|---|
| `workitem` key in `state.json` (T02) | **Absent.** `grep -ri workitem .claude/skills/sdle/templates/` → no match; `git diff --exit-code a12b9e2 -- .claude/skills/sdle/templates/state.json` → exit 0; `test_init_records_no_workitem_in_state` asserts the serialized state contains no `workitem` substring at all. |
| `workflow_version` bump (T02) | **Absent.** `CURRENT_VERSION = "1.13"` at `scripts/sdle.py:541`, unchanged (zero deletions in the file). `lint-skill`: all four version locations report `v1.13`. |
| `VERSION_MIGRATION` row (T02) | **Absent.** `lint-skill` parses **13** migration rows, the baseline figure; `SKILL.md`'s diff contains no table line. |
| `.workflow/` move, `Paths` refactor, `Paths.workitem_*` (T02) | **Absent.** No `Paths` code appears in the diff; the new helpers are free functions. `grep` of the added lines for `class Paths`/`@property` → nothing. |
| Lock removal/rescoping (T02) | **Absent.** No `lock` token in the added lines. |
| `migrate-workflow --workitem` (T02) | **Absent.** No such string anywhere in `sdle.py`. |
| `workitems/` in the hook write fence (T02) | **Absent.** `.claude/hooks/hooks.py` and `.claude/settings.json` byte-identical to `a12b9e2`. `grep -i workitem .claude/hooks/` → no match. Correctly deferred: baseline §5 marks the hook row `ADAPT@T02`. |
| `.gitignore` change (T02+) | **Absent.** Byte-identical to `a12b9e2`, and A15 shows the change is genuinely unnecessary. |
| `workitem resolve` / `sdle validate` / CWD resolution / `--workitem` (T03) | **Absent.** `build_parser()`'s new block registers exactly two subparsers: `create` and `list`. Confirmed by reading the diff hunk. |
| Execution identity (T02) | **Absent.** No `execution.json`, no `muh-<stamp>` shape. |
| Spec Kit binding / `current_feature_id` demotion (T04) | **Absent.** Not in the diff. |
| `.sdle/` config boundary (T05) | **Absent.** No `.sdle` path is constructed by the new code. |
| Type-vocabulary enforcement (T06) | **Correctly absent.** `type` defaults to `enhancement` and is recorded verbatim — I ran `--type defect` and it was stored unvalidated, which is what T01 is supposed to do. |
| Governed-artifact registration of `workitem.json` (T06) | **Absent**, and declared. |
| Phase/gate table changes (T07/T09) | **Absent.** `lint-skill` 22/22. |
| Hash chaining of `index.md` (unassigned) | **Absent.** `append_index_row` writes no digest column; the header is exactly the contract's five columns. |
| `write_atomic` fix (human decision @T02) | **Absent.** Zero deletions in `sdle.py` makes a change to it impossible; I read `write_atomic` at `sdle.py:446-469` — unchanged, still temp-file + `fsync` + `os.replace`. |
| Splitting `sdle.py` (contract §23) | **Absent.** One file, one new section. |

**No T02+ leakage found.**

## Test weakening / deletion check

| Question | Independent finding |
|---|---|
| Any pre-existing test modified? | **No.** `git status --porcelain -uall` shows **no `M` entry under `tests/`** — the only `tests/` entry is `?? tests/test_units_workitem.py`. `git diff --numstat HEAD -- tests/` is empty. |
| Any test deleted? | **No.** No `D` entry anywhere in the status output. |
| Any test skipped/xfailed/weakened? | **No.** `grep` of the new file for `skip`, `xfail`, `pytest.mark.skip` → no match. The new file adds only positive assertions. |
| TP-003 classification | The declared modified-test set is **EMPTY**, and that is what the repository shows. All pre-existing tests are category 1 (unchanged behavior, must stay green). Categories 2 and 3 are legitimately empty because T01 changes no existing behavior. Verified, not accepted on claim. |
| Are the 57 new cases real? | **Yes** — I read `tests/test_units_workitem.py` in full (399 lines). Assertions are substantive, not trivia: exact exit codes against named constants, `reason` strings, `data.rule` discriminators, SHA-256 byte-identity before/after refusals, exact JSON key-set equality (`set(doc) == METADATA_KEYS`), exact index line content and line counts, `sdle.CURRENT_VERSION` compared to the file's own constant, and creation-order assertions on the projected list. Case arithmetic re-derived by hand from the parametrizations (8+1+15+1+4+2+3+10+3+2+3+3+2+2) = **57**, matching the claim. |
| Test hygiene (cont.) | Verified: an `autouse` `isolated_git_identity` fixture sets `GIT_CONFIG_GLOBAL`, `GIT_CONFIG_SYSTEM` to a nonexistent path under `tmp_path` and `GIT_CONFIG_NOSYSTEM=1`. The only identity asserted anywhere is the fixture's `SDLE Test <test@example.invalid>`; no real name or email appears. The expected branch is read at runtime from the fixture repo, not hardcoded. Every case runs under `tmp_path` via `project`/`git_project`; `ls -d workitems` in the repo root reports *No such file or directory* after all runs. |

## Deterministic guardrail check (fail-open / duplicated truth)

| Risk | Independent finding |
|---|---|
| Fail-open on a corrupt registry | **Closed.** `read_index()` raises `IntegrityError("index_malformed")` — exit **3**, the same class the engine uses for `state_unreadable` — and it is called *before* any write in `cmd_workitem_create`. It never repairs or rewrites the file. Verified by the 10-case malformed test with SHA-256 comparison, and by reading the function. |
| Fail-open on an unsafe name | **Closed.** `normalize_workitem_name()` raises before anything is created; I confirmed empirically that a refusal leaves the project root itself non-existent. |
| Fail-open on missing Git | **Deliberate and correct.** `_git_value()` returns `None` when `git` exits non-zero or prints nothing; the command still exits 0 with `null` fields. This is contract §7's design ("metadata records what is knowable"), not a swallowed error — no identity is fabricated and no key is dropped. I observed exactly this shape in the scratch run. |
| Silent traversal acceptance | **Closed, and this is the load-bearing one.** Contract rule 5 in isolation would drop `/` from `a/b` and yield the *valid* id `ab`. `_RAW_NAME_FORBIDDEN` (`[/\\|\x00-\x1f\x7f]`) refuses the raw name first. `workitem_dir()` adds a second `resolve()`-based containment fence. Both verified: `a/b`, `a\b`, `../escape`, `/etc/passwd`, `C:/absolute/path` all exit 1. |
| Duplicated source of truth | **None introduced.** `workitem list` reads the **index only** (`test_list_reads_the_registry_not_the_directory_listing` pins that an unregistered directory is not listed). The directory scan appears in exactly one place — the *uniqueness* check in `create` — which widens refusal rather than creating a second authority, and is exactly plan D7. `sdleVersion` is read from `CURRENT_VERSION`, not restated. The timestamp comes from the existing `now_iso()`; there is no second clock, and one `stamp` is reused for both `createdAt` and the generated id so they cannot straddle a second boundary. |
| Refusal-vocabulary drift | **None.** Grep of every added `Refused(`/`IntegrityError(` in the diff yields exactly three reason strings: `workitem_name_invalid`, `workitem_exists`, `index_malformed` — the plan's D6 set, no more. Sub-cases are carried by `data.rule` (`empty`, `unsafe_character`, `empty_after_normalization`, `too_long`, `charset`, `reserved_name`, `path_escape`, `auto_id_malformed`), which is exactly the discriminator D6 sanctions. |
| Atomicity | **Preserved.** Both writers go through `write_atomic` (which itself is unchanged). `append_index_row` rebuilds the whole file in memory then hands it over once — a crash cannot tear the registry. `cmd_workitem_create` wraps the two writes in `except BaseException:` and removes the metadata file (and the directory, if it created it) before re-raising, so a half-created WorkItem is not left behind (plan F4). |
| Envelope / exit-code contract | **Preserved.** New commands use `emit()`, `Refused`, `IntegrityError` only. I confirmed at the process boundary that a refusal produces pure JSON on stdout with exit 1 and no traceback, and that a missing `--name` is exit 2 (`USAGE`). The `"command": "workitem"` value on a refusal (versus `"workitem create"` on success) is **pre-existing** envelope behavior for nested groups — I reproduced the identical shape with the untouched `state get` command (`"command": "state"`), so it is not a T01 regression. |

## State / audit / evidence integrity check

- **State schema untouched.** No field added; `templates/state.json` byte-identical to `a12b9e2`; `lint-skill`'s `migration_covers_every_state_field` PASS with 13 migration rows.
- **Audit ledger untouched.** `append_audit` is not called by either new command; `grep` of the added lines for `append_audit`/`audit_sha` → no match. The omission is **declared** in the plan, the handoff *and* now in the user-facing Reference Guide ("which is why WorkItem creation does not append to `.workflow/audit.md`"). I independently confirmed the mechanical necessity: `append_audit` requires a live `state` dict, and `read_state` raises `state_unreadable` before `init` — so an audit entry before `init` is impossible without either creating state early (a T02 behavior) or failing open. The index row plus `workitem.json`, both unignored by Git, are the durable creation record.
- **Transition evidence integrity.** `validate.py`'s manifest check (`control-plane.sha256`) passes — every control-plane file still hashes to its recorded digest, including the guard repaired in `0548ebd`.
- **No evidence rewritten.** T00's artifacts (`T00-plan.md`, `T00-handoff-a01.md`, `T00-verification-a01.md`, `T00-blocker.md`) are untouched by the working tree; the only `M` under `docs/transition/` is `progress.md`, which is sanctioned control-plane output.

## Cross-platform / path handling check

- **No new import**; no POSIX-only call. All path work is `pathlib` (`/` operator, `.resolve()`, `.is_dir()`, `.iterdir()`, `.unlink(missing_ok=True)`, `.rmdir()`).
- **Windows reserved device names** are refused (`con`, `prn`, `aux`, `nul`, `com1`-`com9`, `lpt1`-`lpt9`) — I ran `con` and observed exit 1 `reserved_name`. This is a cross-platform *narrowing* (the id vocabulary is the intersection of what every target filesystem accepts), so a WorkItem created on Linux is always creatable on Windows too.
- **Case-insensitive uniqueness** protects against NTFS/APFS case folding, where a case-variant id would otherwise silently target the same directory.
- **64-character cap** keeps `workitems/<id>/…` from approaching the Windows path limit once T02 nests `.sdle/` beneath it.
- **Backslash refused as an unsafe raw character**, so a Windows-style path fragment cannot be normalized into an id.
- **Line endings:** `write_atomic` opens with `newline="\n"`, so `index.md` and `workitem.json` are LF on every platform — no CRLF drift into a file that is compared byte-for-byte.
- **3.11 compatibility** is a source-level review only (see A18). `NOT_RUN` on a real 3.11 interpreter; no CI outcome predicted.

## Artifact review/SHA freshness check

- **Applicable now:** `docs/transition/control-plane.sha256` — verified fresh by `validate.py` (exit 0), which recomputes every listed digest.
- **Not yet applicable:** TP-011 governed-artifact registration/review of `workitem.json` is contract §12 / **T06** by the plan's own exclusion table. T01 registers no artifact and records no review, so there is no stale review to detect. This is correctly deferred, not omitted — it appears in the plan's Scope exclusions and in the handoff's limitations.
- `workitem.json` is written once and never rewritten by any T01 code path (a duplicate id refuses rather than overwrites), so the immutability the later SHA binding will rely on already holds.

## Items flagged for scrutiny — resolution

**1. `scripts/sdle.py` additive only.** **CONFIRMED.** `git diff --numstat HEAD -- scripts/sdle.py` = `320  0`. Zero deletions is not a soft signal: Git represents any modification of an existing line as a deletion plus an addition, so a 0-deletion diff makes silent alteration of an existing function *mechanically impossible*. I additionally read the whole diff (one contiguous section + one parser block) and checked all 20 new top-level symbols for shadowing — each has exactly one definition in the file, so no existing helper is redefined later in module order. `write_atomic`, `now_iso`, `actor`, `git`, `parse_md_table`, `_split_row`, `_is_separator`, `cmd_init` read as unchanged.

**2. The two undeclared-in-plan decisions.** Both are **legitimate in-scope refinements**, not scope creep, and **neither adds a refusal reason beyond D6**.

- *(a) Raw-name pre-check.* This is not optional: plan **A4 itself requires `a/b` and `a\b` to exit 1 `workitem_name_invalid`**, while contract rule 5 applied alone drops the separator and yields the *valid* id `ab`. Without the pre-check A4 is unsatisfiable and a traversal-shaped name is silently accepted. The refusal is folded into the existing `workitem_name_invalid` with `data.rule = "unsafe_character"` — precisely the `data.rule` discriminator D6 sanctions ("Both fold into `workitem_name_invalid` with a `data.rule` discriminator so the vocabulary stays small"). Verified empirically: five separator/pipe shapes refuse; verified by grep that no fourth reason string exists.
- *(b) Index-cell sanitization.* This is **sanitization, not refusal**, so it cannot change the vocabulary at all. Without it a single `|` in a free-text `--synopsis` would make every subsequent `create` and `list` exit 3 — the engine corrupting its own ledger. The asymmetry is coherent rather than arbitrary: a pipe in a **name** refuses, because the name becomes an id and a directory; a pipe in a **synopsis** is sanitized, because it is free text. No information is lost — `workitem.json` keeps the string verbatim, which I confirmed in the pinning test (`test_a_pipe_in_the_synopsis_cannot_corrupt_the_registry` asserts `metadata[...]["synopsis"] == raw`) and reproduced through the CLI: index cell `has a pipe`, metadata `has a | pipe`, `list` still exit 0.
- Both are **declared** in the handoff, in checkpoint 01, and in `progress.md`. Neither was hidden.

**3. `project_name` deviation deferred, not closed.** **CONFIRMED on both halves.** *Declared:* it is stated in `T01-plan.md` ("Baseline §4.3 `project_name` is annotated `ADAPT` at T01 (E28) — declared deviation"), in `T01-handoff-a01.md`, and in the `progress.md` T01 Notes; baseline §4.3 does mark it `ADAPT` at changing phase T01. *Unchanged:* `cmd_init`'s inference is untouched (zero deletions in `sdle.py`), and `test_a_workitem_does_not_change_what_init_and_advance_produce` asserts `project_name` is **identical** between a WorkItem project and a control project with none. The rationale holds under inspection: rebinding `project_name` to a WorkItem title requires state to reference the WorkItem, which is a state-schema change — forbidden by P5 and owned by T02. Contract §7 never mentions `project_name`, so the deviation is from a T00 *prediction*, not from the contract. **Carry-forward for T02 planning.**

**4. No T02+ leakage.** **CONFIRMED** — see the leakage table above; all 18 exclusions independently checked against the diff. Specifically: no `workitem` key or substring in `state.json`, `CURRENT_VERSION` still `1.13` with all four version locations agreeing, 13 migration rows unchanged, no `.workflow/` or lock change, `hooks.py`/`settings.json`/`.gitignore` byte-identical to `a12b9e2`, and `workitems/` deliberately **not** added to the write fence. Contract §6's explicit-preserve list holds: 18 phases, 8 gates, `.workflow/` location, lock behavior and Spec Kit feature behavior are all outside the diff and all confirmed by `lint-skill` 22/22 plus 55 passing lint/CLI/hook regression tests.

**5. TP-003 modified-test set EMPTY.** **CONFIRMED against the diff, not the claim.** `git status --porcelain -uall` contains no `M` and no `D` under `tests/`; the sole `tests/` entry is `?? tests/test_units_workitem.py`. `git diff --numstat HEAD -- tests/` is empty. No `skip`/`xfail` marker exists in the new file. Nothing was weakened.

**6. The new tests are real.** **CONFIRMED.** I read all 399 lines. They assert exit codes against named constants, `reason` strings, `data.rule` values, SHA-256 byte-identity across refusals, exact JSON key-set equality, exact index line text and line counts, and creation ordering — not `assert result` trivia. Every plan acceptance criterion has a resolvable anchor: A2/A9 → `test_metadata_carries_exactly_the_contract_key_set`, `test_git_identity_and_branch_are_captured`, `test_missing_git_identity_yields_nulls_without_refusing`; A3 → `test_a_duplicate_refuses_and_leaves_every_byte_in_place`; A4 → `test_an_unsafe_name_refuses_and_writes_nothing` (15 params); A5 → `test_auto_generate_mints_a_timestamped_id_and_keeps_its_case`; A6 → `test_a_case_only_collision_refuses`; A7 → `test_a_malformed_index_is_an_integrity_failure_and_is_never_repaired` (10 params); A8 → three `list` tests; A10 → `test_a_workitem_does_not_change_what_init_and_advance_produce`; A11 → `test_init_records_no_workitem_in_state`. All collect (`57 tests collected`) and all pass. Contract §7's own eight-item "New tests" list is covered item for item. Two tests are notably strong for a verifier's purposes: the A10 test asserts `advance` exits 0 **in its own right**, not merely equal to the control (a control-equality-only assertion would pass if both were broken); and the A11 test asserts `"workitem" not in json.dumps(state).lower()`, which catches leakage under any key name.

**7. Bootstrap-order documentation changes.** **CONFIRMED clean.**
- *No constant table touched.* `SKILL.md`'s diff is 5 insertions / 1 deletion, entirely within the Step 1 prose paragraph; no table line appears in it. `lint-skill` re-parses 19 phases, 8 gates, 13 migration rows and passes all 22 checks including every `gate_registered_*`, `phase_set_matches_*`, `next_phase_chains_sequence` and `progress_denominator_matches_phase_count`.
- *No phase/gate table altered* in `README.md` or the Reference Guide — both `doc_lists_every_phase_*` checks PASS, and the Reference Guide addition is an **unnumbered** `### WorkItem identity` subsection inserted before `### 4.3`, so no section number and no TOC entry moves.
- *No SpecKit internals exposed.* Grep of every added line across all five changed files for `speckit-`: **no match**.
- *Lint traps avoided as the plan required:* the `workitem.json` example lives in `README.md`, **not** in a skill file (`single_state_template` PASS); no new bold `**vX.Y**` string and no second `# SDLE … (vX.Y)` heading was introduced above the existing ones (`version_string_consistent: all four locations report v1.13`); no PowerShell-only cmdlet and no literal `N/18` in new skill text (both checks PASS).
- *Ordering is stated consistently* in both places: `sdle-start.md` step 3 (WorkItem prompt + `create`) precedes step 4 (`init`), and `SKILL.md` Step 1 gains "Identity comes before initialisation." The resume branch in both explicitly states it never asks for a WorkItem name, which is what keeps the transcript-derived integration tests valid — and those tests do pass.
- *`scripts/README.md` correctly not edited.* I checked: its sections are "Call the launcher, not the script", "Output contract", "Exit codes", "Where the constants live". It enumerates no subcommands, so plan U6's condition for editing it is genuinely unmet.

## Findings

### Blocking

None.

### Non-blocking

1. **`write_atomic` WinError 5 flake persists and its victim set keeps moving.** Four victims this run, one (`test_03_retry_limit_stops_offering_retry`) not previously recorded, and for the first time the flake surfaced as a fixture-setup `ERROR` rather than a test `FAILED`. Correctly classified `ENVIRONMENT_FLAKE` and correctly not patched in T01. The count is drifting upward (T00: 2, T01 implementer: 3, T01 verifier: 4) and the raw suite exit code is now reliably non-zero, which will read as red in CI. **The root-cause/retry decision is already scheduled as a human decision at T02 planning; this run strengthens the case for taking it there.**
2. **Python 3.11 and CI remain `UNKNOWN`.** No 3.11 interpreter on this host, branch not pushed. A18 is a source-level review only. Recorded as `NOT_RUN`; no CI outcome predicted. Unchanged from T00, and T01's additive stdlib-only design does not depend on it.
3. **Git-identity isolation is scoped to the new test file only.** The `isolated_git_identity` autouse fixture lives in `tests/test_units_workitem.py`, so it protects only that module. Pre-existing suites still let `actor()` fall back to the machine's global Git config and write the developer's real name and email into scratch `audit.md` files under `tmp_path` — visible in this run's failure tracebacks. This is **pre-existing behavior, not introduced by T01**, and T01's own tests are correctly isolated. Worth promoting the fixture to `tests/conftest.py` when T02 touches the audit path.
4. **A stray *file* (not directory) at `workitems/<id>` is not covered.** The uniqueness scan filters on `child.is_dir()`, so a plain file named `workitems/foo` would not trigger `workitem_exists`; the create would instead fail inside `write_atomic`'s `mkdir`. No plan criterion covers this shape and it is not reachable through any SDLE code path, so it is not a T01 defect — noted for whoever hardens the registry at T02.
5. **`workitems/` is outside the hook write fence.** Deliberate and declared (hook row is `ADAPT@T02`). Meanwhile Git plus the deterministic append path are its only integrity controls. Must be closed at T02.
6. **Deferred and carried forward:** `project_name` rebinding (item 3 above), no audit event on `workitem create` (mechanically impossible pre-`init`; owned by T02/T06), and TP-011 governed-artifact review of `workitem.json` (T06).

## Final result rationale

Every acceptance criterion A1-A18 verified independently — A1-A5, A8, A9-null,
A12, A14, A15, A16, A17 by commands I ran in this context, A6/A7/A10/A11 by
running the specific tests after reading their source to confirm they assert the
criterion, and A13 by the full suite plus the F1 procedure. `lint-skill` exits 0
with 22/22. `validate.py` exits 0 including the control-plane hash manifest. The
full suite collects 287 as expected and its only non-passing outcomes are four
instances of the inherited, environmentally-caused `write_atomic` WinError 5,
all of which pass on re-run 1 of an allowed 3 — a *different* victim set from
the handoff's, which is itself evidence of non-determinism rather than a real
defect. No pre-existing test was modified, deleted, weakened, skipped or
xfailed. `scripts/sdle.py` is provably additive (320/0). No T02+ leakage exists
on any of the eighteen exclusion lines. No fail-open path, no duplicated source
of truth, no guardrail loss. Both decisions the plan implied but did not spell
out are legitimate in-scope refinements that add no refusal reason, and both
were declared rather than hidden. The `project_name` deviation is genuinely
declared and genuinely deferred. The contract §7 exit criterion — an immutable
WorkItem identity before legacy initialization, with all existing phase/gate
behavior still passing — is satisfied and mechanically pinned.

The single authoritative result line for this artifact is the `**Result:**`
field in the header block above, and it reads PASS. T01 is verified complete;
the orchestrator may commit the working tree and fill in the SHA.
