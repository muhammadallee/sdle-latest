# T08 Independent Verification — Attempt a01

**Phase:** T08 — Brownfield discovery and greenfield/brownfield convergence (contract §14)
**Attempt:** 01
**Verifier context:** fresh/isolated
**Result:** PASS

**Commit verified:** `e1cf341` (HEAD) · **Prior-phase baseline:** `c80f341` (T07, verified PASS at `451f440`) · **Plan commit:** `9c10eb5` · **Product baseline:** `f8fdaa0`
**Out of scope, pre-existing and untouched:** `.claude/settings.local.json` (only dirty path in `git status --porcelain`).

> The handoff was treated as a claim set. Every figure below was produced by a
> command run in *this* context. Where a claim in `T08-handoff-a01.md` or in
> `ADR-005` disagreed with what a command reported, the command is what is
> recorded, and the disagreement is listed under Findings.

### Guard refusals, declared verbatim

`tools/transition/agent_guard.py verifier` refused two of my commands. Neither
was routed around with an alternate shell or interpreter, and the guard was
neither patched nor re-signed.

1. `PreToolUse:Bash hook error: [python tools/transition/agent_guard.py verifier]: SDLE transition agent guard: verifier Bash/PowerShell must be observational; blocked command shape`
   — fired on the full-suite invocation because it redirected stdout to a file
   (`>`). Resolved by capturing the run with pytest's own `--junitxml=` (a
   tool-side write, not a shell redirect) plus the harness's recorded exit code.
2. `PreToolUse:Bash hook error: [python tools/transition/agent_guard.py verifier]: SDLE transition agent guard: verifier Bash/PowerShell must be observational; blocked command shape`
   — fired on a Python heredoc whose payload contained the token `copy` in
   `import ... copy as ...`. Resolved by renaming my own token, per the standing
   guidance.

All live drives were performed in `tempfile.mkdtemp()` trees outside the
repository. `git status --porcelain` at the end of verification is unchanged
from the start (` M .claude/settings.local.json` only).

---

## Acceptance criteria verification

| Criterion | Result | Independent evidence |
|---|---|---|
| **A1** registry 21, flow shapes | **MET** | `python scripts/sdle.py constants` (exit 0): `len(phase_sequence)==21`, `phase_sequence[:4]==['requirements_check','discovery','impact_analysis','constitution_draft']`, `discovery` at index 1. Entries **including** `complete` / `gate_total`: GREENFIELD 19/8, BROWNFIELD_DISCOVERY 20/8, ITERATIVE 17/7, DEFECT_FIX 15/6, HOTFIX 11/3. `phase_count` (non-terminal): 18/19/16/14/10. |
| **A2** only BROWNFIELD changed, by one inserted element | **MET** | Reconstructed `c80f341`'s whole `.claude/skills/sdle/` tree into a temp dir (`git ls-tree -r --name-only c80f341` + `git show`), ran `constants` against it via `SDLE_SKILL_ROOT`. Old registry **20**. Element-wise: `GREENFIELD`, `ITERATIVE`, `DEFECT_FIX`, `HOTFIX` **IDENTICAL** (gate totals identical too); `BROWNFIELD_DISCOVERY` added `['discovery']`, removed `[]`, and `[p for p in new if p!='discovery'] == old` → `True`. `phase_to_gate_key` and `artifact_ownership` identical old vs new. |
| **A3** `discovery` is gateless; 8 approvals | **MET** | `discovery` absent from `phase_to_gate_key` keys **and** values, from `artifact_ownership`, from `gate_to_execution_phase`, and from `progress` (19 rows). `templates/state.json` byte-identical to `c80f341`, `approvals` exactly 8 keys. `lint-skill` check `discovery_is_gateless` PASS. Python walk of every UTF-8 file in the tree for `gate_discovery`: **7 hits, exactly 1 in product/test code** — `tests/test_lint_skill.py:340`, inside `test_a_gate_registered_for_discovery_fires`, a negative lint-firing fixture (read in context); the other 6 are this migration's own prose. |
| **A4** R-a…R-j refused; all-UNKNOWN accepted | **MET** | 23 planted violations driven through the real CLI against a live `BROWNFIELD_DISCOVERY` WorkItem at `discovery`. All refused exit 1: R-a (unknown top-level key / unsupported version / missing `findings`), R-b (empty list / non-object entry), R-c (duplicate id / empty id), R-d (bad category), R-e (**missing classification**, `"PROBABLY"`, lowercase `"observed"`), R-f (empty / missing statement), R-g (OBSERVED with no evidence / nonexistent path / `../` escape), R-h (INFERRED with no basis / undeclared basis / **basis that is itself UNKNOWN**), R-i (UNKNOWN carrying evidence) → all `discovery_input_malformed`; R-j (one category dropped, and 13 dropped) → `discovery_incomplete` naming the missing ids. An all-UNKNOWN 14-category document is **accepted** (used as the fixture base for every case above); a mixed OBSERVED/INFERRED/UNKNOWN document is accepted and records `counts {"OBSERVED":1,"INFERRED":1,"UNKNOWN":12}`. |
| **A5** refusals leave the ledger byte-identical | **MET** | See "State / audit / evidence integrity check" below. `advance`, `skip --confirm`, `gate approve`, `discovery assess` and `baseline validate` each refused with `audit.md` and `state.json` **SHA-256-identical and byte-identical** before and after, `audit verify` exit 0 `chain_ok True`. A refused `init` (R1 and R2) created **no** `state.json`, `audit.md` or `execution.json`. |
| **A6** `lint-skill` exit 0, nothing removed or weakened | **MET** | `python scripts/sdle.py lint-skill` → exit **0**, **32 checks, `"failed": []`**, `tables_wellformed: Parsed 21 phases, 8 gates, 16 migration rows`. AST diff of every `Check(...)` first argument against `git show c80f341:scripts/sdle.py`: **+3, −0** — `discovery_is_gateless`, `discovery_is_declared_by_exactly_one_flow`, `discovery_vocabulary_is_not_restated_in_prompt_files`. Each has a firing test in `test_lint_skill.py` (7 new tests read in full); each new check body read — none can pass by defaulting. |
| **A7** `read_baseline` fail-closed | **MET** | AST: `read_baseline` has exactly one `ExceptHandler` and it contains a `Raise`, **no `Return`**; `read_governance_record` the same; `read_repo_config` still has a handler containing a `Return` (the T05 NB-4 contrast, untouched). Driven directly: absent → `None`; **empty file**, `{not json`, `"a string"`, `[]`, `{"baselineVersion":"99"}` and `{"hello":1}` each raise `IntegrityError("baseline_invalid")`. `sdle validate` on a corrupt descriptor exits **3**. See Finding NB-5 for the directory case. |
| **A8** both establishing flows converge | **MET** | Two independent temp repositories driven to `complete` through the real CLI. GREENFIELD: `baseline show` → `VALID`, `discovery.status == "NOT_REQUIRED"`, `record`/`recordSha256`/`counts` all `null`. BROWNFIELD_DISCOVERY: `VALID`, `discovery.status == "PERFORMED"`, record path + SHA + counts populated. **Identical top-level key set** both times: `baselineVersion, commit, discovery, establishedAt, establishedBy, nonNegotiables, references, supersedes`. |
| **A9** §14's exit criterion, driven | **MET** | Single repository, real CLI, no test helpers for the decision path. WI-A completes `BROWNFIELD_DISCOVERY` (20-entry traversal, `discovery` at index 1) → `baseline show` `VALID`, `baseline validate` exit 0. WI-B assessed `BROWNFIELD_DISCOVERY` → `init` **exit 1 `baseline_present`**, data `{"baseline_status":"VALID","path":".sdle/baseline.json"}`; WI-B's runtime afterwards holds only `governance.json` and `evidence/` (both written by `governance assess` *before* `init`) — **no `state.json`, no `audit.md`, no `execution.json`**. Re-assessed `ITERATIVE` → `init` exit 0, driven to `complete`; traversal contains no `discovery`, `phase_history` contains no `discovery`, and WI-B's `audit.md` does **not** contain the string `discovery`. |
| **A9 (other direction)** greenfield establishes the baseline a later ITERATIVE needs | **MET** | Explicitly checked because the failure mode would be silent: after a GREENFIELD WorkItem completes, `baseline show` is `VALID` and a second WorkItem assessed `ITERATIVE` **initialises successfully (exit 0)**. Greenfield completion does establish the baseline, so `baseline_required` is *not* reachable after a greenfield run. The convergence invariant holds from both ends. |
| **A10** nine facts, references not copies | **MET** | Descriptor inspected on both establishing flows. Nine §14 facts map one-to-one: `baselineVersion`, `establishedBy.workitem`, `commit` (real SHA), `references.constitution`, `references.architecture`, `references.adrs`, `nonNegotiables`, `discovery.status`, `establishedAt` (plus `establishedBy.executionId` and `supersedes`). Every reference is exactly `{path, sha256}`. `nonNegotiables` = `{"source": "<record path>", "findingIds": ["F-013"]}` — **ids, not prose**. The constitution's body does not appear in `baseline.json` (substring test → `False`). |
| **A11** material invalidation is exactly the three errors | **MET** | Driven **in both directions** on a real completed baseline. *Changed* `design/app/app-design.md` → `STALE`, finding `baseline_reference_changed`, severity `warning`, `sdle validate` exit **0**; a later `ITERATIVE` `init` **succeeds** (no forced rediscovery) and `BROWNFIELD_DISCOVERY` is still refused `baseline_present`. *Deleted* the same file → `INVALID`, `baseline_reference_missing`, severity `error`, `sdle validate` exit **3**; `ITERATIVE` `init` refused `baseline_required`, `BROWNFIELD_DISCOVERY` `init` **succeeds and lands on `discovery`** — rediscovery is triggered by genuine invalidation and only by it. Also fired independently: `baseline_producer_unregistered` (edited `workitems/index.md`) and `baseline_invalid` (removed the required `commit` key). |
| **A12** no vocabulary restated | **MET** | Two independent searches. (1) My own content search of the engine's needle set (all 14 category ids + the 3 classifications + the finding keys) over T06's `_searchable_files()` (28 files): **no hit for any of `OBSERVED`/`INFERRED`/`UNKNOWN`, for `discoveryInputVersion`, or for any of the 9 underscored category ids**. (2) `lint-skill` check `discovery_vocabulary_is_not_restated_in_prompt_files` PASS over 13 identifiers. See Finding NB-2 for the carve-out's justification text. |
| **A13** transcripts and integration 01 byte-identical | **MET** | 34 paths compared against `c80f341` with CRLF normalised: `tests/test_integration_01_happy_path.py`, all nine `docs/dry-runs/*`, plus `test_integration_02_to_05.py`, `test_integration_06_to_09.py`, `test_hooks.py`, `test_units_state.py`, `test_units_transitions.py`, `test_units_artifact_review.py`, `test_units_speckit_binding.py`, `test_units_workitem_runtime.py`. **DIFFER: []**. |
| **A14** guard surfaces byte-identical; v1.16; 16 rows | **MET** | Same comparison: `templates/state.json`, `.claude/hooks/` (all), `.claude/commands/` (all), `.claude/settings.json`, `.gitignore`, `gate-protocol.md`, `security-review.md` all identical. `version_string_consistent: all four locations report v1.16`; `version_chain` length **16** in `constants` and `Parsed … 16 migration rows` in `lint-skill`. AST literal compare vs `c80f341`: `GREENFIELD_V1_PHASES` (19 entries, no `discovery`), `MANDATORY_FLOW_PHASES`, `SDLE_OWNED_PREFIXES`, `CONFIG_MEMBER_NAMES` all **IDENTICAL**. |
| **A15** `conftest.py` is exactly the two permitted additions | **MET** | `git diff --stat c80f341 HEAD -- tests/conftest.py` → **+66 / −0**. Diff read in full: exactly `Project.establish_baseline` and `Project.record_discovery` added; no existing fixture, helper or default modified; `record_governance`'s default classification is still `{"type": "enhancement", "flow": "GREENFIELD"}`. Neither helper restates a schema key or vocabulary — `establish_baseline` calls `sdle.baseline_descriptor`, `record_discovery` reads `sdle.DISCOVERY_CATEGORIES` and `sdle.DISCOVERY_CLASSIFICATIONS[-1]`. |
| **A16** every test change recorded; nothing weakened | **MET in substance; third clause not literally met** | No test deleted, `skip`ped, `xfail`ed or weakened — see "Test weakening / deletion check". Every changed site is in the handoff's TP-003 table with a category-2 rationale. **However** A16's third clause ("the set of changed test functions is a subset of the table in *Existing tests affected*") is **not** satisfied: four files the plan lists as "must not change" did change. Each change is forced by the plan's own binding content and is disclosed. Recorded as Finding **NB-1**; judged non-material. |
| **A17** full suite observed | **MET** | `rtk proxy "python -m pytest -q -p no:cacheprovider --junitxml=…"`: **`1025 passed in 1232.73s (0:20:32)`**, `short test summary` occurrences in the captured run = **0**. JUnit XML: `tests="1025" failures="0" errors="0" skipped="0"`. Background task exit code reported by the harness: **0**. Collected independently: **1025 tests collected**. Arithmetic re-derived: 901 (T07's verified pre-T08 count, inherited provenance) + 109 in the two new files (measured: `test_units_discovery.py` + `test_units_baseline.py` → `109 tests collected`) + 15 new named test functions − 4 renamed-away + parametrisation = 1025. |
| **A18** `validate.py` exit 0; no literal `\|` in a T08 cell | **MET** | `python tools/transition/validate.py` → `TRANSITION_VALID: complete=8/12 next=T08`, exit **0**. T08 row split on `|` by script → 11 fields, 9 populated cells, none containing a stray pipe. |
| **A19** no T09/T10/T11 leakage | **MET** | See "Future-phase leakage check". |
| **A20** ADR-005 states D3's split | **MET** | `docs/architecture/ADR-005-brownfield-discovery-and-baseline.md` read end to end. D3 states both halves in two labelled lists. `discovery schema` publishes the same split machine-readably as `enforced` (5 statements) / `not_enforced` (3 statements). See Finding NB-3 for one README sentence that reads stronger than D3 permits. |

---

## Regression evidence

Every drive below used the real CLI (`sdle.main(argv)` through `conftest.Project`,
the same entry point the suite uses) in throwaway `tempfile.mkdtemp()` git
repositories created and discarded inside this context.

- **Five-flow behaviour.** `GREENFIELD` (19-entry traversal, ends `complete`/`completed`),
  `BROWNFIELD_DISCOVERY` (20-entry, `discovery` at index 1), `ITERATIVE` (17-entry, no
  `discovery`), and `init` accepted for `DEFECT_FIX` and `HOTFIX`.
- **R2 covers `ITERATIVE` only.** In a repository with **no** baseline
  (`baseline show` → `ABSENT`): `ITERATIVE` `init` → exit 1 `baseline_required`,
  runtime holds only `governance.json`/`evidence/`; **`DEFECT_FIX` exit 0**,
  **`HOTFIX` exit 0**, `BROWNFIELD_DISCOVERY` exit 0, `GREENFIELD` exit 0 — each
  with a full runtime (`state.json`, `audit.md`, `execution.json`, `lock`).
  An emergency hotfix is genuinely unblocked.
- **Forward-jump discipline unchanged.** A GREENFIELD WorkItem: `advance --to discovery`
  → exit 1 `forward_jump` with `"in_flow": false`; ledger chain still `chain_ok`.
  `flow show` for GREENFIELD does not mention `discovery`.
- **Legacy `.workflow/` dual-read.** A legacy runtime reconstructed at
  `.workflow/` with the WorkItem registry removed: `migrate-workflow --workitem <id>`
  exit **0**, and the SHA-256 of all five `.workflow/` files is **identical before
  and after** — `migrate-workflow` still never mutates the legacy directory.
  Source-side: `discovery_precondition`, `baseline_precondition` and
  `establish_baseline` each return early when `paths.workitem is None`.
- **Corrupt discovery record is fail-closed.** `discovery show` and
  `advance` both exit **3** `discovery_record_invalid`; nothing advances.
- **The baseline write cannot block completion (F4).** A `discovery.json`
  corrupted immediately before the final `gate approve`: the approval still
  **exit 0**, `baseline.json` written, and `discovery` degrades to
  `{"status":"NOT_REQUIRED","record":null,"recordSha256":null,"counts":null}` —
  exactly ADR-005 D6's claim, verified rather than read.
- **Completion accounting.** Exactly **one** `baseline_established` entry, exactly
  one `discovery_recorded`, `workflow_complete` precedes `baseline_established`
  in `audit.md`, and `audit verify` exit 0 `chain_ok True` afterwards.
- **`flow_selected` records the baseline status at binding** — observed in a real
  ledger: *"Flow GREENFIELD bound: 18 phases, 8 gates. … Repository baseline at binding: ABSENT."*

---

## Full-suite / lint evidence

| Command | Result | Evidence/summary |
|---|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider --junitxml=<scratch>/junit_full.xml"` | **PASS** | **`1025 passed in 1232.73s (0:20:32)`**. JUnit root: `tests="1025" errors="0" failures="0" skipped="0"`. `short test summary` count in the captured output = **0**. Harness-reported background exit code **0**. |
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` | **PASS** | `1025 tests collected in 0.78s` — collected == passed. |
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_baseline.py tests/test_units_discovery.py --junitxml=…"; echo "RAW_EXIT=$?"` | **PASS** | `109 passed in 171.10s`, **`RAW_EXIT=0`** read with no pipe between — also the control proving the exit-code channel works in this shell. |
| `python scripts/sdle.py lint-skill` | **PASS** | Exit **0**. **32 checks, all `[PASS]`, `"failed": []`**. `tables_wellformed: Parsed 21 phases, 8 gates, 16 migration rows`; `version_string_consistent: all four locations report v1.16`; `discovery_vocabulary_is_not_restated_in_prompt_files: none of the 13 vocabulary identifiers appears in a prompt file`. |
| `python tools/transition/validate.py` | **PASS** | `TRANSITION_VALID: complete=8/12 next=T08`, exit **0** (before the progress edit; re-run after). |
| `python scripts/sdle.py constants` | **PASS** | Exit 0; figures under A1. |
| `python scripts/sdle.py discovery schema` | **PASS** | Exit 0; 14 categories, 3 classifications, 10 rules R-a…R-j, `enforced` (5) / `not_enforced` (3). |
| Python 3.11 | **NOT_RUN** | This host is 3.13. No outcome predicted. |
| CI (`ubuntu-latest`, `windows-latest`) | **NOT_RUN** | Branch is local-only. No outcome predicted. |

The F1 `ENVIRONMENT_FLAKE` procedure was treated as **VOID**. No failure occurred,
so it was never reached.

---

## Future-phase leakage check

- **T09 (risk-adaptive gates) — clean.** AST call-site walk: `required_gate_set`
  has exactly **two** callers, `cmd_governance_assess` and `cmd_governance_gates`;
  `evaluate_risk` has exactly one, `cmd_governance_assess`. No phase-movement
  function calls either. `governance gates` still emits `"advisory": true`
  (observed live). Function-level diff of `scripts/sdle.py` vs `c80f341`: the only
  changed functions are `apply_advance`, `build_parser`, `cmd_gate_approve`,
  `cmd_init`, `cmd_skip`, `collect_validation_findings`, `evaluate_classification`,
  `run_sync_checks`, `workitem_runtime_member_names` — **0 removed** — and each
  diff was read in full. Nothing added to `apply_advance`, `cmd_gate_approve` or
  `cmd_skip` is conditional on risk, level or policy: the additions are one
  `discovery_precondition(paths, state)` line each, plus the `is_final`
  baseline write. Gate requirements remain structural.
- **T10 (skills/subagents) — clean.** `git diff --name-only c80f341 HEAD -- .claude/agents/`
  is empty; the directory holds only the four `sdle-transition-*` control-plane
  files, last touched at `a12b9e2`. No product skill added; no subagent created.
- **T11 (legacy removal, version bump) — clean.** `workflow_version` still `1.16`
  at all four locations, 16 migration rows, state template byte-identical.
  Legacy `.workflow/` dual-read and `migrate-workflow` still present and working.
- **The T11 residual was NOT adopted.** `SDLE_OWNED_PREFIXES` is byte-identical
  to `c80f341` (8 entries, no `.sdle/`); `cmd_manifest_build` does not appear in
  the changed-function set at all, so its exclusion is untouched; `.claude/hooks/`
  and `.gitignore` are byte-identical. `test_the_two_guard_surfaces_are_unchanged`
  pins both halves.
- **T05 NB-4 not inherited.** `read_repo_config` is untouched and still fail-open;
  `read_baseline` is fail-closed, asserted on the parsed AST and driven directly.

---

## Test weakening / deletion check

`git diff --name-status c80f341 HEAD -- tests/` → **8 `M`, 2 `A`, zero `D`, zero `R`**.

- Added lines matching `mark.skip|mark.xfail|pytest.skip|pytest.xfail|unittest.skip`: **none**.
  Removed lines matching the same: **none**. The suite reports `skipped="0"`.
- **14 assertion lines removed**, all enumerated and each replaced by an
  equal-or-stronger assertion:
  registry counts `19→20` / `20→21` (×4, forced by A1);
  `BROWNFIELD_DISCOVERY.phase_count 18→19`;
  `phase_sequence[1] == "impact_analysis"` → now pins **both** `discovery` at 1
  and `impact_analysis` at 2;
  `next_phase["requirements_check"] == "impact_analysis"` (×2) → now pins the
  new two-link chain;
  `seen == EXPECTED_TRAVERSAL` and `brownfield == greenfield` → now pin
  `seen[1]=="discovery"`, `[p for p in seen if p!="discovery"]==EXPECTED_TRAVERSAL`,
  `brownfield != greenfield`, and `brownfield.index("discovery")==1` — strictly more;
  `equal_pairs == {("BROWNFIELD_DISCOVERY","GREENFIELD")}` → `equal_pairs == set()`
  — the carve-out is **removed**, which is stronger;
  `len(set(landed.values())) == 3` → `== 4`;
  `sha_map(configured.root/".sdle") == boundary_before` → replaced by four
  clauses (exactly one entry added, it is `baseline.json`, every pre-existing
  entry byte-identical, nothing removed, plus the unconfigured repository gets
  the same single file). This is the only removal that admits behaviour the old
  line forbade, and the behaviour it admits is §14's declared deliverable.
- `test_declaring_greenfield_as_a_flow_row_fires` was retargeted from the
  `BROWNFIELD_DISCOVERY` row onto the `ITERATIVE` row; its assertion is still
  `assert_only_failure(repo, "flow_table_covers_the_required_flows")` — unchanged
  and still isolating.
- `test_no_lifecycle_command_reads_the_repository_configuration` is unchanged
  (docstring only); `CONFIG_REFERENCE_SITES` is still asserted by exact equality
  and gained eight named entries, none of them a lifecycle command.
- Two edits inside T08-authored files (`test_the_two_guard_surfaces_are_unchanged`
  gaining the manifest-exclusion pin on the parsed AST; a docstring in
  `test_units_discovery.py`) are additive strengthening, not supersession.

**No test was deleted, skipped, xfailed or weakened. TP-003 category 4 set is empty.**

`tests/conftest.py`: `+66 / −0`, exactly the two additions the anti-contradiction
clause permits.

---

## Deterministic guardrail check

- **The core refuses; it does not warn.** Every new failure path is a refusal
  with an exit code: `discovery_input_malformed`, `discovery_incomplete`,
  `discovery_missing`, `discovery_workitem_required`, `baseline_present`,
  `baseline_required`, `baseline_not_valid` at exit 1;
  `discovery_record_invalid`, `baseline_invalid` at exit 3. AST diff of every
  `Refused(...)` / `IntegrityError(...)` first argument vs `c80f341`: **9 added,
  0 removed, 0 renamed**. The single `warning`-severity output,
  `baseline_reference_changed`, is a `validate`/`baseline show` finding on a
  channel that already carries warnings, and `baseline validate` still exits 1
  on it — it is not a softened refusal.
- **Fail-open search.** `read_baseline` has no `Return` in any exception handler
  (AST); `read_discovery_record` raises rather than defaults (driven: exit 3);
  `read_discovery_input` refuses on unknown key, missing key, unsupported
  version and non-object (driven). The three new `lint-skill` check bodies were
  read: each derives its subject (`gate_key = f"gate_{DISCOVERY_PHASE}"`,
  needles from the engine constants) rather than spelling it, and none has a
  `try`/`except` that could pass by defaulting.
- **One source of truth per fact (invariant 7).** `baseline_findings` is the
  single validity predicate, with exactly two callers
  (`collect_validation_findings`, `baseline_state`) — observed to agree:
  `baseline show`, `baseline validate` and `sdle validate` reported the same
  finding id and severity in every one of the six states I planted.
  `establish_baseline` has exactly **one** caller (`cmd_gate_approve`);
  `baseline_precondition` exactly **one** (`cmd_init`); `baseline_descriptor`
  exactly one (`establish_baseline`). There is no `baseline establish`/`set`
  and no `flow set`.
- **Gate discipline.** Eight gates, unconditional, none renumbered; `discovery`
  carries none. Verified that a `gate approve` issued at `discovery` refuses
  `not_at_gate` **before** any T08 code runs (source order: `not_at_gate` at
  line 6754, `discovery_precondition` at 6788).
- **`cmd_init` stays outside `apply_advance`** — unchanged; `baseline_precondition`
  is the first call in it (line 1845) and the first `mkdir` is at 1853.
- **§13's "no workflow framework".** No branching, loop, dynamic insertion or
  policy DSL was added. `discovery` is one registry row and one element of one
  ordered subset.

---

## State / audit / evidence integrity check

Reproduced live in a throwaway git repository, `BROWNFIELD_DISCOVERY` bound and
standing at `discovery` with no record:

| Command | Exit | Reason | `audit.md` SHA | `state.json` SHA |
|---|---|---|---|---|
| `advance --to constitution_draft` | 1 | `discovery_missing` | identical | identical |
| `advance --to impact_analysis` | 1 | `forward_jump` | identical | identical |
| `gate approve --gate gate_constitution` | 1 | `not_at_gate` | identical | identical |
| `discovery assess --input <missing>` | 1 | `discovery_input_malformed` | identical | identical |
| `baseline validate` (ABSENT) | 1 | `baseline_not_valid` | identical | identical |
| `skip --confirm` (with a real pending confirmation) | 1 | **`discovery_missing`** | identical | identical |

Byte comparison as well as SHA comparison in every row. `audit verify` after the
whole sequence: exit **0**, `chain_ok True`.

The `skip` row required first driving the WorkItem into `status: "failed"`
(`artifact record --path <missing>` → `artifact_missing`) and then `skip` to set
`pending_confirm_action`; both intermediate steps were checked, and the plain
`skip` that sets the pending flag also left `audit.md` byte-identical. This is
the exact B1 / NB-6 property, still held.

Refused `init` (R1 and R2), verified twice in separate repositories: **no
`state.json`, no `audit.md`, no `execution.json`, no `lock`** — the only runtime
members present are `governance.json` and `evidence/`, both written by
`governance assess` *before* `init` was called.

Completion ledger: exactly one `baseline_established`, appended after
`workflow_complete`, chain verified.

Evidence: `discovery assess` writes `workitems/<id>/.sdle/discovery.json` **and**
`workitems/<id>/.sdle/evidence/discovery-<executionId>.json`; the record carries
`categories, counts, discoveryVersion, executionId, findings, recordedAt,
result, workitem`. A refused assess writes neither.

---

## Cross-platform / path handling check

- `lint-skill` `no_powershell_only_cmdlets`: PASS.
- Every new function was scanned for platform-specific constructs. The only
  `os.sep` use is `cmd_discovery_assess`'s `args.input.replace(os.sep, "/")` —
  normalisation in the correct direction. No `PosixPath`/`WindowsPath`, no
  `/tmp`, no drive letters, no hand-built separators.
- `_reference` and `establish_baseline` produce repository-relative POSIX paths
  (`Path.relative_to(...).as_posix()`); the observed descriptor contains
  `".specify/memory/constitution.md"` and `"design/app/app-design.md"` with
  forward slashes on Windows.
- `_evidence_problem` resolves through `Path` and rejects absolute paths and
  `../` escapes; a backslash-separated evidence path is **refused** on this
  Windows host (`does not exist in this repository`), so the risky asymmetry —
  accepted on Windows, broken on Linux — does not exist.
- Byte comparisons in this verification normalised CRLF before concluding
  identity, per F12.
- Suite observed green on Windows only. `ubuntu-latest` is **UNKNOWN**; no
  outcome predicted.

---

## Artifact review/SHA freshness check

- `.sdle/baseline.json` stores each reference as `{path, sha256}` computed at
  write time from the file on disk. `baseline_reference_changed` fires when the
  recorded SHA no longer matches — reproduced by rewriting `design/app/app-design.md`
  and observing the status flip `VALID → STALE`; restoring the file returns it
  to `VALID`.
- `references.constitution` and `references.architecture` are resolved through
  `ARTIFACT_OWNERSHIP` for `gate_constitution` / `gate_design`, so the table that
  already answers "which file is this gate's artifact" remains the only answer.
- `discovery.recordSha256` is the SHA of `discovery.json` at completion, and
  `baseline_reference_missing` covers it when `status == "PERFORMED"`.
- TP-011 review binding is unchanged: `review_precondition` is untouched, and
  the driven runs recorded a review for every gate artifact before approval.
- The `governed artifact` surface `control-plane.sha256` is re-verified by
  `validate.py`, which exits 0.

---

## Findings

### Blocking

**None.**

### Non-blocking

**NB-1 — A16's third clause is not literally met; the handoff records A16 as flatly "MET".**
Four files the plan lists under *"Must not change, and this is checked"* did
change: `tests/test_units_cli.py`, `tests/test_units_infra.py`,
`tests/test_units_repo_config.py`, `tests/test_units_workitem_resolution.py`.
Each edit is compelled by the plan's own binding content — A1's 21-entry
registry (the two `phase_count == 19` assertions cannot survive it), N13's
requirement that the `.sdle/` leak detector inherit `discovery.json` (which needs
the `Paths` member, which grows the exact-equality literal), D10/D7's requirement
that `discovery schema` and `baseline show` answer with no WorkItem (which grows
`RUNTIME_FREE_COMMANDS`), and D6's completion-time write (which falsifies the
old clause 4). None is caused by R2, so failure mode **F6**'s blocker trigger did
not fire, and all four are disclosed in the handoff's TP-003 table with reasons.
The defect is in the plan — its "must not change" list contradicts its own A1 —
and the implementer resolved it in the only direction available and said so.
What is overstated is the handoff's acceptance matrix, which marks A16 "MET"
citing only its first two clauses. Not material: nothing was weakened, nothing
was silent. **For T09's planner:** derive the must-not-change list from the
acceptance criteria rather than listing it independently.

**NB-2 — ADR-005 D10 and `discovery_identifiers()`'s docstring justify a case-sensitive search with a case-insensitive measurement.**
Both say the five single-word category ids "already appear as prose" in the
searched set, naming *the README, `CLAUDE.md`, the Reference Guide, the
security-review module and this ADR*; the handoff's "ADR fix 6" states the
justification "is now the measured one" at five files. Measured in this context
over the test's own `searchable_files()` (28 files), **case-sensitively — which
is how `test_n14_*` matches (`n in body`)**: `architecture` 4 files,
`conventions` 1, `dependencies` 1, `apis` **0**, `adrs` **0** → **4 distinct
files, not 5**, and neither `modules/security-review.md` nor ADR-005 is matched
by the id attributed to it (they contain `APIs` and `ADRs`). Case-insensitively
the sentence is true. Consequence is documentation precision only, and it points
the *conservative* way: `apis` and `adrs` could be added to the needle set today
without failing, which would strengthen N14.

**NB-3 — one README sentence rounds the enforced half up.**
`README.md`, flow narrative: *"…records a structured set of findings in which
every statement is classified as observed, inferred or unknown, **so an inference
can never be read as an observation**."* The engine guarantees the label exists
and is one of the closed three; it cannot guarantee the author applied the right
one — which is precisely what `discovery schema`'s `not_enforced` list, the
README's own dedicated paragraph 130 lines later, the Reference Guide's
`discovery` section, `phase-execution.md` ("the engine … cannot check that your
statement is true of that file, and that half is yours") and ADR-005 D3 all say.
Read as a statement about the record's *presentation* the clause is defensible;
it is nonetheless the only sentence in the whole sweep that states the guarantee
without its qualifier. **Every other document checked was accurate.**

**NB-4 — Reference Guide §4.2.1 "A corrupt `baseline.json` halts with exit 3 and names the file" is true of `validate`, not of `baseline show`.**
Observed with a corrupt descriptor: `sdle validate` → exit **3**
(`workitem_validation_failed`); `baseline show` → exit **0**, `status: "INVALID"`;
`baseline validate` → exit 1 `baseline_not_valid`. `baseline show` is a
diagnostic reader by design and reporting `INVALID` is the behaviour the R1/R2
decision consumes, so this is **not** fail-open — `INVALID` is what refuses
`ITERATIVE`. Wording imprecision only.

**NB-5 — `read_baseline` treats `.sdle/baseline.json` existing as a *directory* as ABSENT.**
Planted a directory at that path: `read_baseline` returns `None`, `baseline show`
reports `ABSENT`. This is the one input shape in the fail-closed set that does
not raise. It mirrors `read_governance_record`'s `is_file()` test exactly, which
is what D7 promised, and it is safe in effect: `ABSENT` refuses `ITERATIVE`
(`baseline_required`) and permits only the more-work direction
(`BROWNFIELD_DISCOVERY`). Recorded so a later phase that tightens
`read_governance_record` tightens this too.

**NB-6 — ADR-005 D4 does not record the qualification the handoff does.**
The handoff states honestly that no T08 refusal is reachable *at* `gate approve`
and that the call site is defensive. I confirmed this: `require_gate` maps every
registered gate key to a gate phase, no gate key resolves to `discovery`, and
`not_at_gate` is raised 34 lines before `discovery_precondition`. ADR-005 D4
describes all three sites as though each were live. D4 is not *untrue* — the
ledger property it claims holds at all three, and I reproduced it at all three —
but the ADR is the durable record and the qualification lives only in the
handoff.

**NB-7 — handoff bookkeeping.** The header says the attempt "spans three
contexts" while the Git-evidence section lists checkpoints `-01.md … -05.md`;
six checkpoints exist (`-06.md` is context 3's). The handoff's own body describes
context 3 and M6 correctly. Cosmetic. Also: the handoff's AST figure "23 → 26
`Check(...)` registration sites" does not reproduce here — my walk of literal
first-argument `Check(...)` calls counts **20 → 23**. The delta (+3, −0) and the
three names are identical, so the claim that matters is confirmed; only the base
figure differs, most likely a different counting rule for the looped
`gate_registered_*` registrations.

**NB-8 — pre-existing, disclosed, not T08's.** The Reference Guide's revision
history has no v1.16 row and its header still says *Document version 1.1 /
Last updated 2026-07-06*, while the newest history row is 1.4 / 2026-08-24; §8.1's
flow diagram shows only the GREENFIELD traversal, so neither `impact_analysis`
nor `discovery` appears in it. All predate T08 and the handoff records them
rather than silently fixing them. Carry to whichever phase owns the guide.

---

## Final result rationale

§14's deliverable is the convergence invariant, and it is real rather than
narrated. I drove it myself, twice and from both ends: a `BROWNFIELD_DISCOVERY`
WorkItem completes and establishes a `VALID` baseline; the next WorkItem in the
same repository is **refused `baseline_present`** and gets no runtime at all;
re-assessed `ITERATIVE` it initialises and completes with `discovery` in neither
its `phase_history` nor its `audit.md`. And a `GREENFIELD` completion establishes
the same minimum shape, so a later `ITERATIVE` is admitted rather than refused —
the failure mode that would have made the invariant one-sided does not exist.
Material invalidation behaves in both directions: a *changed* reference yields
`STALE` and does not force rediscovery, a *missing* one yields `INVALID` and
does. `DEFECT_FIX` and `HOTFIX` are genuinely unblocked with no baseline.

The integrity property is split honestly. Every clause the engine claims to
enforce, I broke deliberately and watched it refuse — unclassified, out-of-
vocabulary, an observation citing a path that does not exist or escapes the root,
an inference resting on an unknown, an unknown carrying evidence, a dropped
category — and the split is published machine-readably by `discovery schema` as
`enforced`/`not_enforced`. Of every document in the sweep, one README clause
states the guarantee without its qualifier (NB-3); everything else, including
ADR-005 D3, the Reference Guide's phase section and the prompt layer, names the
three things the engine cannot judge.

The B1/NB-6 ledger property survives: refusals at `advance`, `skip --confirm`,
`gate approve`, `discovery assess`, `baseline validate` and `init` all leave
`audit.md` and `state.json` SHA-identical and byte-identical, with `audit verify`
exit 0 afterwards, and a refused `init` creates nothing. `read_baseline` is
fail-closed against every malformed shape I could construct and does not inherit
`read_repo_config`'s swallow. The guard surfaces T11 owns were not adopted; the
GREENFIELD constant is byte-identical and still not a `FLOW_PHASES` row; four of
five flows are element-wise unchanged; the transcripts, the happy-path
integration, the state template, the hooks, the commands, `settings.json` and
`.gitignore` are byte-identical; v1.16 stands at four locations with 16 migration
rows; no gate became policy-driven.

The suite is `1025 passed`, zero failures, zero errors, zero skips, with
`lint-skill` at 32/32 and `validate.py` exit 0.

The eight findings are documentation precision, one plan-list inconsistency the
implementer resolved in the only direction its own acceptance criteria allow and
disclosed, and one recorded observation about a pathological input shape. None
changes what the engine does, none weakens a test, none is a material
architecture, contract or baseline decision, and none is future-phase leakage.

The single top-level result for this attempt is the `**Result:**` line in the
header block above: **PASS**.
