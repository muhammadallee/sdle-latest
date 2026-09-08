# T08 Implementation Handoff — Attempt a01

**Phase:** T08 — Brownfield discovery and greenfield/brownfield convergence (contract §14)
**Attempt:** 01
**Implementer context:** fresh/isolated. **This attempt spans three contexts.** M1–M3 were applied by context 1 and M4–M5 by context 2; both were terminated by an API session limit — a §24.6 interruption, **not** a verification FAIL — so the attempt number was never incremented. Context 2 had begun M6 (it drafted the ADR corrections and most of the documentation sweep) when it was killed, and recorded neither in a checkpoint. **Context 3 finished M6** and wrote the final evidence. Each context re-derived its predecessor's state from disk rather than trusting the earlier prose, and the "Commands actually run" table below says which context observed each figure. No figure is repeated as if this context had observed it.
**Status recommendation:** IMPLEMENTED
**Plan:** `docs/transition/phases/T08-plan.md` (846 lines, immutable, at `9c10eb5`)
**HEAD when implemented:** `9c10eb5` · **Rollback point:** `c80f341` · **Product baseline:** `f8fdaa0`

---

## Inputs read from disk

`CLAUDE.md`; `docs/transition/transition.md` (§14, §24.3, §24.6, TP-003, TP-011);
`docs/transition/progress.md`; `docs/transition/phases/T08-plan.md`;
`T08-checkpoint-a01-01.md` and `-02.md`;
`docs/architecture/ADR-003`, `ADR-004`, and the pre-existing
`ADR-005-brownfield-discovery-and-baseline.md`;
`scripts/sdle.py`; `.claude/skills/sdle/SKILL.md` and its modules; `README.md`;
`docs/SDLE-Reference-Guide.md`; every test file the plan names; `git status`,
`git diff`, `git show c80f341:<path>`.

Context 3 additionally read all five checkpoints, this handoff as a **draft to
verify rather than as evidence**, `docs/architecture/ADR-002` (the sentence
ADR-005 supersedes), and the whole of `ADR-005` against the shipped engine.

**Nothing was taken on trust.** The orchestrator's summary, the inherited
checkpoints and the plan's own figures were each re-derived by a command run in
the context that reports them before being relied on. Facts the inherited
material asserted that needed correction: `lint-skill` is **32** checks, not 29
(M2 added three); `BROWNFIELD_DISCOVERY` is **20** entries including the
terminal `complete`, which is the 19/8 the plan's A1 states under E6's
convention; and checkpoint 05's two open ADR-005 defects had **already been
fixed on disk** by context 2 before it was killed — verified by reading the
file, not by trusting the checkpoint, which is also how three further ADR
inaccuracies it did not list were found (see "ADR-005: verified, and
corrected").

---

## Changes made

### `scripts/sdle.py` (+1234 lines net over `c80f341`)

**M1 — none.** The structural change is entirely in the data tables the engine
parses.

**M2 — discovery as a governed record.** `Paths.discovery_file`;
`DISCOVERY_PHASE`, `DISCOVERY_RECORD_VERSION`, `DISCOVERY_INPUT_VERSIONS`,
`DISCOVERY_INPUT_SECTIONS`, `DISCOVERY_FINDING_KEYS`,
`DISCOVERY_REQUIRED_FINDING_KEYS`, `DISCOVERY_CLASSIFICATIONS` (3),
`DISCOVERY_CATEGORIES` (14, in §14's order), `DISCOVERY_RULES` (R-a…R-j),
`DISCOVERY_AUDIT_EVENT`; `read_discovery_input`, `_evidence_problem`,
`evaluate_discovery`, `read_discovery_record`, `discovery_accepted`,
`bind_for_discovery`, `cmd_discovery_schema`, `cmd_discovery_assess`,
`cmd_discovery_show`, `discovery_precondition`; three `lint-skill` checks.

**M3 — the baseline descriptor, read-only.** `BASELINE_VERSION`,
`SUPPORTED_BASELINE_VERSIONS`, `BASELINE_REQUIRED_KEYS`,
`BASELINE_REFERENCE_KINDS`, `BASELINE_ESTABLISHING_FLOWS`,
`BASELINE_AUDIT_EVENT`, the four statuses; `_reference`, `baseline_descriptor`,
`read_baseline`, `_baseline_reference_paths`, `baseline_findings`,
`baseline_status`, `baseline_state`, `cmd_baseline_show`,
`cmd_baseline_validate`; the `validate` wiring and the `baseline` parser group.

**M4 — establish the baseline at completion (context 2).**

- `establish_baseline(paths, state, consts, stamp) -> tuple[str|None, str|None]`,
  the **only** writer. Returns `(None, None)` when `paths.workitem is None` (the
  transitional legacy binding has no producing WorkItem, which is §14's second
  required fact) or when the bound flow is not in
  `BASELINE_ESTABLISHING_FLOWS`. Never refuses and never raises on missing
  inputs. Returns `(relative_path, sha256)`.
- `cmd_gate_approve`'s `is_final` branch: establish the baseline **first**,
  then `write_completion_summary`, then `workflow_complete`, then
  `baseline_established`. The emitted payload gains `"baseline"`.

**M5 — the refusals (context 2).**

- `CLASSIFICATION_KEYS = ("type", "flow", "rediscovery")` and
  `CLASSIFICATION_REQUIRED_KEYS`; `evaluate_classification` validates against
  the tuple, refuses a non-boolean `rediscovery` and refuses
  `rediscovery: true` with any flow other than `BROWNFIELD_DISCOVERY`, and
  returns a fourth key `"rediscovery": <bool>`.
- `BASELINE_REDISCOVERY_FLOW` and `BASELINE_REQUIRING_FLOW`.
- `baseline_precondition(paths, flow, rediscovery) -> str`, a pure reader
  implementing **R1 `baseline_present`** and **R2 `baseline_required`**, called
  from `cmd_init` alone and **before** its first `mkdir`.
- The `flow_selected` audit entry records the baseline status at binding.

### Prompt and documentation files

- **`SKILL.md`** — `PHASE_SEQUENCE` 20 → 21 with `discovery` at position 2;
  `NEXT_PHASE` chains `requirements_check → discovery → impact_analysis`;
  `PHASE_LABEL_MAP` row; the `BROWNFIELD_DISCOVERY` `FLOW_PHASES` row.
  **No `PROGRESS_MAP` row, no `PHASE_TO_GATE_KEY` row.** M6 added the
  repository-baseline paragraph in the operating text, named `discovery` as
  `BROWNFIELD_DISCOVERY`'s landing phase, and corrected the frontmatter's
  "20-phase registry".
- **`modules/phase-execution.md`** — the ordinal-free
  ``**Phase `discovery` (BROWNFIELD_DISCOVERY only …)`` block, and (M6) one
  bullet in `constitution_draft` requiring the findings to be displayed again
  before the constitution is drafted (design invariant 4).
- **`README.md`** — `discovery` in the flow narrative; the `.sdle/` tree's
  `baseline.json` line no longer says "not created yet"; a new
  "The repository baseline" section; `21-phase registry`. **Context 3 added**
  the five new commands as a table in the Commands section — the shape the
  governance and artifact-review command tables already use, and the gap left
  by the earlier sweep — with the paragraph that states D3's split in the
  README's own voice; corrected the v1.16 changelog row, which still described
  a "20-entry phase registry" (no version row was added — D11); and corrected
  "Add a new phase", which told a reader to add a PROGRESS_MAP row for every
  phase when PROGRESS_MAP is the GREENFIELD view and `discovery` and
  `impact_analysis` deliberately have none.
- **`CLAUDE.md`** — **context 3.** It stated "`PHASE_SEQUENCE` is a 20-entry
  phase *registry*", which T08 makes false, and said nothing about discovery or
  the baseline. Corrected to 21 and given one paragraph naming the `discovery`
  phase, the baseline and ADR-005. Not in the plan's expected-changes list, but
  leaving a literally false sentence in the repository's own instruction file
  is the drift the sweep exists to prevent, and T07 set the precedent by
  updating this same paragraph for the flow model.
- **`docs/SDLE-Reference-Guide.md`** — registry 20 → 21 in two places; the
  `BROWNFIELD_DISCOVERY` flow row 18/8 → 19/8; a `Repository Discovery`
  phase section; the `.sdle/` boundary table's `baseline.json` cell; a new
  **4.2.1 The repository baseline** section; five commands added to Appendix C.
  **Context 3 added** `discovery.json` to §12.4, which described the WorkItem's
  records and named only two of the three, and renamed that heading
  accordingly.
- **`docs/architecture/ADR-005-brownfield-discovery-and-baseline.md`** — new,
  recording D1–D12, D3's enforced/not-enforced split, and every rejected
  alternative. It was drafted by the earlier context; this context **verified
  it line by line against the shipped engine** and corrected it (see below).

### Tests

New: `tests/test_units_discovery.py` (54), `tests/test_units_baseline.py` (55).
Modified: `test_units_flow_model.py`, `test_lint_skill.py`,
`test_units_governance.py`, `test_units_repo_config.py`, `test_units_cli.py`,
`test_units_infra.py`, `test_units_workitem_resolution.py`, `conftest.py`.

**Context 3 made two further test edits, both inside tests T08 itself authored,
and both strengthening.** `test_the_two_guard_surfaces_are_unchanged` (N33) now
also pins, on the parsed source of `cmd_manifest_build`, that the Gate 7
manifest excludes the WorkItem runtime and nothing else — it names no
`SDLE_OWNED_PREFIXES`, holds no `.sdle` string constant, and derives its prefix
from `paths.runtime_relative`. ADR-005's D12 claimed a test pinned *both* halves
of the T11 residual and only one was pinned; the fix was to make the claim true
rather than to soften it. The assertion is on the AST rather than on the source
text, because the function's explanatory comment legitimately names
`SDLE_OWNED_PREFIXES` — a text search made the test fail for the wrong reason
when first written, which is exactly the false-negative the assertion has to
avoid. The second edit corrects the docstring of `discovery_identifiers()` in
`test_units_discovery.py` (see the ADR section below).

---

## Deliberate behavior changes

1. The phase registry gains `discovery`: 20 → **21** entries.
2. `BROWNFIELD_DISCOVERY` becomes **19 phases / 8 gates** (20 entries including
   `complete`) and is no longer element-wise identical to `GREENFIELD`. The
   other four flow rows are element-wise unchanged, verified against `c80f341`.
3. New commands: `discovery schema`, `discovery assess --input <path>`,
   `discovery show`, `baseline show`, `baseline validate`.
4. New WorkItem runtime file `discovery.json` plus an evidence document.
5. New repository file `.sdle/baseline.json`, written at GREENFIELD and
   BROWNFIELD_DISCOVERY completion, by one function with one call site.
6. New audit event kinds `discovery_recorded` and `baseline_established`; the
   `flow_selected` message now also records the baseline status at binding.
7. New refusals: `discovery_input_malformed`, `discovery_incomplete`,
   `discovery_missing`, `baseline_present`, `baseline_required`,
   `baseline_not_valid` (exit 1); `discovery_record_invalid` and
   `baseline_invalid` (exit 3).
8. `sdle validate` reports baseline findings, through the same predicate
   `baseline show` uses.
9. `classification.rediscovery` is a third permitted governance-input key.
10. `lint-skill` goes from 29 checks to **32**. None removed, none weakened.

---

## Preserved behavior / invariants

- **Gate discipline** — no gate added, removed, renumbered or made conditional.
  `discovery` is gateless: no `PHASE_TO_GATE_KEY`, `ARTIFACT_OWNERSHIP` or
  `GATE_TO_EXECUTION_PHASE` row, and `approvals` still has exactly eight keys
  (verified by command). The only `gate_discovery` string anywhere in the
  repository is inside a **negative** lint-firing fixture in
  `test_lint_skill.py`, the `gate_impact_analysis` pattern exactly.
- **Fail safe** — every new failure freezes; nothing advances on error.
- **Single writer, and a refusal leaves the ledger byte-identical** — every new
  refusal is a pure reader placed ahead of the caller's first `append_audit`.
  Reproduced live through the real CLI in **both** contexts, independently:
  context 2 saw a refused `gate approve` (`artifact_missing`) and a refused
  `skip --confirm` (`discovery_missing`) leave `audit.md` byte-identical;
  context 3 re-ran it from a fresh throwaway repository and saw `advance`,
  `skip --confirm` and `gate approve` all refuse with `audit.md` **and**
  `state.json` SHA-256-identical before and after, and `audit verify` exit 0
  with `chain_ok: true` afterwards. A refused `init` (R1/R2) creates no
  `state.json`, no `audit.md` and no `execution.json`.
  **One honest qualification:** no T08 refusal is reachable *at* `gate approve`.
  R1 and R2 fire only at `init`, and `discovery_missing` needs
  `current_phase == "discovery"`, which is by construction not a gate — a
  `gate approve` issued there refuses `not_at_gate` first. The
  `discovery_precondition` call in `cmd_gate_approve` is therefore defensive:
  it costs nothing, it keeps the three phase-movement entry points uniform, and
  it means a future flow that put a gate after `discovery` would be caught
  rather than walked past. The ledger property was still reproduced at that
  command, which is what the invariant is about.
- **GREENFIELD** stays the frozen 19-entry engine-held `GREENFIELD_V1_PHASES`,
  not derived from the registry and still not a `FLOW_PHASES` row.
- **`tests/test_integration_01_happy_path.py` and all nine `docs/dry-runs/`
  transcripts are byte-identical to `c80f341`** (line endings normalised).
- `.claude/skills/sdle/templates/state.json`, `.claude/hooks/`,
  `.claude/commands/` (all files), `.claude/settings.json`, `.gitignore` and
  `modules/gate-protocol.md` / `modules/security-review.md` are byte-identical
  to `c80f341`.
- **No version bump** — `workflow_version` is still `1.16`,
  `version_string_consistent` still reports "all four locations report v1.16",
  and the migration chain still has **16** rows.
- **The ladder never guesses** — WorkItem resolution unchanged; the two new
  command groups are runtime-free at the group level and their WorkItem-scoped
  members bind explicitly.
- Legacy `.workflow/` dual-read still works; `migrate-workflow` still never
  mutates `.workflow/`. Both new preconditions skip the legacy binding, and so
  does the baseline writer.
- `cmd_init` still sits outside `apply_advance`.
- **Invariants 3, 4, 7, 8** — no `speckit-*` name in any new message; the
  findings are displayed in conversation before `gate_constitution`, twice; no
  category id, classification token or envelope key is restated outside
  `sdle.py` (enforced by a lint check *and* a real content search); nothing
  holding a gate is delegated and no subagent is created.
- **The core refuses; it does not warn.** The single warning-severity output,
  `baseline_reference_changed`, is a `validate` finding on a diagnostic channel
  that already carries warnings — not a softened refusal.

### Scope exclusions honoured

- **T09** — `governance gates` still emits `advisory: true`;
  `required_gate_set` still has exactly its two governance callers; no gate is
  conditional on risk, classification or policy; none of the six functions T08
  added references `required_gate_set`, `evaluate_risk`, `GOVERNANCE_LEVELS` or
  `read_governance_policy`. Pinned by `test_n34_*`.
- **T10** — no product subagent, no skill split. `.claude/agents/` exists but
  holds only the four `sdle-transition-*` migration control-plane files,
  unchanged since `a12b9e2`; the plan's scope exclusions say in terms that they
  are not T10 evidence.
- **T11** — no legacy removal, no version bump. **The recorded residual that
  `.sdle/` is in neither `SDLE_OWNED_PREFIXES` nor `cmd_manifest_build`'s
  exclusion was deliberately NOT adopted**; both sets are pinned unchanged by
  `test_the_two_guard_surfaces_are_unchanged`.
- **T05 NB-4** — `read_repo_config` untouched, and its fail-open shape
  deliberately **not** inherited: a test asserts on the parsed AST that no
  exception handler in `read_baseline` returns a value, and asserts the
  contrast that `read_repo_config`'s handlers do.

---

## Test changes and TP-003 classification

**Every row is category 2 — deliberately superseded behavior.** No test was
deleted, `skip`ped, `xfail`ed or weakened; several were made stronger. There is
no category 4.

| Test / site | File | Category | Rationale |
|---|---|---|---|
| `test_brownfield_discovery_is_greenfield_until_t08_changes_it` | `test_units_flow_model.py` | 2 | Its own docstring named T08 as the owner of changing it. Now asserts the two flows differ by exactly `discovery`. |
| `test_the_five_traversals_are_pairwise_distinct_except_the_declared_pair` | `test_units_flow_model.py` | 2 | `equal_pairs` is now empty; the declared carve-out is gone. |
| `test_the_gateless_flow_denominators_are_the_declared_ones` | `test_units_flow_model.py` | 2 | `BROWNFIELD_DISCOVERY.phase_count` 18 → 19. GREENFIELD's 18 and ITERATIVE's 16 untouched. |
| `prepare()` gains a `discovery` arm | `test_units_flow_model.py` | 2 | The new phase has a generation step. |
| `bind()` establishes a baseline for ITERATIVE **only when the repository has none** | `test_units_flow_model.py` | 2 | R2 refuses ITERATIVE without one. Conditional so a caller that established a real baseline first drives against *that* one — which is what makes N24 meaningful. |
| `test_the_flow_is_the_one_governance_value_that_moves_the_lifecycle` | `test_units_governance.py` | 2 | Its BROWNFIELD clone now lands on `discovery`, so "three distinct landings" becomes four; its ITERATIVE clone needs a baseline (same conditional shape). |
| The two exact-equality `record["classification"] == {...}` assertions | `test_units_governance.py` | 2 | Gain `"rediscovery": False`. |
| Lint firing tests that edit the `BROWNFIELD_DISCOVERY` / `ITERATIVE` rows | `test_lint_skill.py` | 2 | `test_declaring_greenfield_as_a_flow_row_fires` was retargeted onto the `ITERATIVE` row: renaming the BROWNFIELD row now also orphans `discovery` and trips a second rule, so the edit no longer isolated the check. Row text re-derived, never re-typed. |
| `test_skill_root_can_be_pointed_elsewhere` (registry non-terminal count 19 → 20) | `test_units_cli.py` | 2 | **Outside the plan's table, and in its "must not change" list.** A1 requires a 21-entry registry, so an assertion that it has 20 cannot survive. The plan's table was incomplete for the mechanical count assertions; this is not a plan defect. |
| `TestLauncherResolution::test_a_real_launcher_run_succeeds_here` (same count) | `test_units_infra.py` | 2 | Same reason, same fact. |
| `test_the_runtime_member_names_are_derived_from_paths` gains `"discovery.json"` | `test_units_repo_config.py` | 2 | **Outside the plan's table.** N13 requires the bidirectional `.sdle/` leak detector to inherit `discovery.json`, which is only possible by adding the `Paths` member, which grows this exact-equality literal. |
| `test_runtime_free_commands_is_a_closed_enumerated_set` gains `discovery`, `baseline` | `test_units_workitem_resolution.py` | 2 | **Outside the plan's table.** `discovery schema` must answer before any workflow exists, and the repository baseline is a property of the repository, so binding a WorkItem to read it would be wrong in kind. |
| `CONFIG_REFERENCE_SITES` gains six readers, `establish_baseline` and `baseline_precondition` | `test_units_repo_config.py` | 2 | The set is asserted by exact equality so a new function reaching the §11 boundary can never be silent. **`cmd_gate_approve` and `cmd_init` are deliberately still absent** — they reach the boundary through the two helpers and name no configuration member, which keeps `test_no_lifecycle_command_reads_the_repository_configuration` passing **unchanged**. |
| `test_the_configuration_boundary_changes_no_lifecycle_behaviour`, clause 4 | `test_units_repo_config.py` | 2 | T05 could assert "the lifecycle never touched the boundary" because nothing in the lifecycle wrote it. §14 changes that on purpose, and continuing to assert it would be asserting a fiction. **Restated exactly, not dropped:** the run adds exactly one boundary entry, that entry is `baseline.json`, every pre-existing entry is byte-identical afterwards, nothing is removed, and the unconfigured repository gets the same single file. Clauses 1–3 untouched. |
| `test_no_lifecycle_command_reads_the_repository_configuration` | `test_units_repo_config.py` | — | **Unchanged.** Recorded here because it is the guard the `establish_baseline` refactor exists to preserve. |
| `test_the_two_guard_surfaces_are_unchanged` gains the manifest-exclusion pin | `test_units_flow_model.py` | — | **Not a superseded existing test:** the function was authored by T08 at M1 and was strengthened, not changed, inside the same phase. No assertion was removed or relaxed. |
| `discovery_identifiers()`'s docstring | `test_units_discovery.py` | — | Same: a T08-authored file. The docstring claimed a measured fact that a measurement contradicted; corrected to what a real search returns. No assertion touched. |
| `tests/conftest.py` | — | — | **Exactly the two additions the anti-contradiction clause permits**, `establish_baseline` and `record_discovery`, `+66 -0`. No existing fixture, helper or default modified. `record_governance`'s default classification is still `{"type": "enhancement", "flow": "GREENFIELD"}`. |

Four test files the plan listed as "must not change" did change
(`test_units_cli.py`, `test_units_infra.py`, `test_units_repo_config.py`,
`test_units_workitem_resolution.py`). Each is a mechanical consequence of a
fact the plan's own acceptance criteria require, each is recorded above with
its reason, and none was absorbed silently. Failure mode **F6** did not fire:
no breakage appeared that the plan's reasoning does not account for.

### New tests

`tests/test_units_discovery.py` — 54 tests covering N1–N14, N29–N30.
`tests/test_units_baseline.py` — 55 tests covering N15–N28 and N34, including:

- **N23** — two repositories driven to completion through the real CLI,
  GREENFIELD and BROWNFIELD_DISCOVERY, both `VALID`, same required key set,
  `NOT_REQUIRED` versus `PERFORMED`.
- **N24 / acceptance A9** — §14's exit criterion **driven, not asserted**.
- **N27 / F4** — the constitution and design document deleted between the last
  generation step and the final approval; completion still succeeds and the
  descriptor carries `null` / `[]`.
- **N28** — exactly one `baseline_established`, after `workflow_complete`,
  chain intact, completion summary unchanged field-for-field.
- Source-level pins: one call site for the writer, one call site for the
  precondition, the precondition precedes every write in `cmd_init`.

`tests/test_units_flow_model.py` — N31–N33, the "nothing else moves" proof.

---

## Commands actually run

Every figure below was produced by a command run in the context that reports
it, redirected to a file, with `$?` read with no pipe between. **The first
table was observed by context 2** (rows tagged `(M4)` / `(M5)` are that
context's milestone runs); **the second was observed by context 3**, which
re-derived the structural figures from scratch rather than inheriting them. No
figure is carried across a context boundary without saying so.

### Observed by context 2

| Command | Result |
|---|---|
| `git log --oneline -5` / `git status --short` | HEAD `9c10eb5`; T08 entirely uncommitted |
| `python scripts/sdle.py constants` | registry **21**, `phase_sequence[:4] == ['requirements_check','discovery','impact_analysis','constitution_draft']`; flows incl. `complete`: GREENFIELD 19, BROWNFIELD_DISCOVERY 20, ITERATIVE 17, DEFECT_FIX 15, HOTFIX 11 |
| Flow comparison against `c80f341` (old `SKILL.md` in a temp tree) | registry 20 → 21; **GREENFIELD, ITERATIVE, DEFECT_FIX, HOTFIX all UNCHANGED**; BROWNFIELD_DISCOVERY 19 → 20, `added=['discovery']`, and removing it reproduces the old list exactly |
| `python scripts/sdle.py lint-skill` | exit **0**, **32 checks, 0 failing**; `tables_wellformed: Parsed 21 phases, 8 gates, 16 migration rows`; `version_string_consistent: all four locations report v1.16`. The 29 pre-T08 checks are all present; the three new ones are `discovery_is_gateless`, `discovery_is_declared_by_exactly_one_flow`, `discovery_vocabulary_is_not_restated_in_prompt_files`. Re-run after **every** document edit in M6. |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=8/12 next=T08`, exit **0** |
| Byte-identity vs `c80f341` (26 paths, line endings normalised) | **none differ**: `test_integration_01_happy_path.py`, all nine `docs/dry-runs/*.md`, `templates/state.json`, `hooks/hooks.py`, `settings.json`, `.gitignore`, `gate-protocol.md`, `security-review.md`, every file under `.claude/commands/` |
| `discovery`/`baseline` gate check on `constants` + template | `discovery` absent from `phase_to_gate_key`, `artifact_ownership`, `gate_to_execution_phase` (keys and values) and `progress`; `approvals` has exactly **8** keys; `workflow_version` `1.16`; `version_chain` **16** rows |
| Repository-wide walk for `gate_discovery` | exactly **one** hit, `tests/test_lint_skill.py:340`, inside a negative lint-firing fixture |
| `python scripts/sdle.py discovery schema` | emits `enforced` (5 statements) and `not_enforced` (3 statements) alongside the vocabularies — D3's split is machine-readable, not merely documented |
| **Live refusal reproduction** through the real CLI (temporary file, run then deleted) | `gate approve` → exit 1 `artifact_missing`, `audit.md` byte-identical, `audit verify` exit **0** `chain_ok: True`. `skip --confirm` → exit 1 `discovery_missing`, `audit.md` byte-identical, `audit verify` exit **0** `chain_ok: True`. |
| `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` (start of context) | **1001 tests collected**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_baseline.py -q"` (M4) | **36 passed in 53.08s**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_repo_config.py tests/test_integration_01_happy_path.py tests/test_units_transitions.py -q"` (M4) | **104 passed in 150.23s**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_workitem_runtime.py tests/test_integration_02_to_05.py tests/test_integration_06_to_09.py tests/test_units_flow_model.py -q"` (M4) | **230 passed in 399.86s**, RAW_EXIT 0 |
| **Full suite at end of M4** | **`1006 passed in 1157.19s (0:19:17)`, RAW_EXIT 0** |
| `rtk proxy "python -m pytest tests/test_units_baseline.py -q"` (M5) | **55 passed in 103.01s**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_governance.py tests/test_units_repo_config.py tests/test_units_discovery.py -q"` (M5) | **307 passed in 230.29s**, RAW_EXIT 0 |
| `rtk proxy "python -m pytest tests/test_units_flow_model.py tests/test_units_workitem_runtime.py tests/test_units_state.py -q"` (M5) | **187 passed in 278.08s**, RAW_EXIT 0 |
| **Full suite at end of M5** | **`1025 passed in 1211.95s (0:20:11)`, RAW_EXIT 0** |
| `rtk proxy "python -m pytest tests/test_units_discovery.py tests/test_lint_skill.py tests/test_units_governance.py -q"` (M6, after the doc sweep) | **270 passed in 174.38s**, RAW_EXIT 0 |

### Observed by context 3 (M6 completion and final evidence)

| Command | Result |
|---|---|
| `git log --oneline -5`, `git status --short` | HEAD `9c10eb5`; T08 entirely uncommitted; 9 modified tracked files plus `.claude/settings.local.json` (out of scope, untouched) and 9 untracked |
| **Full suite at the inherited end-of-M5/part-M6 tree, before any context-3 edit** | **`1025 passed in 1251.81s (0:20:51)`, RAW_EXIT 0**, no short-summary lines |
| `python scripts/sdle.py constants` | registry **21**, `phase_sequence[:4] == ['requirements_check','discovery','impact_analysis','constitution_draft']`; entries incl. `complete` — GREENFIELD **19**, BROWNFIELD_DISCOVERY **20**, ITERATIVE **17**, DEFECT_FIX **15**, HOTFIX **11**; `discovery` absent from `phase_to_gate_key` (keys **and** values) and from `progress` (19 rows); `version_chain` **16** rows |
| `python scripts/sdle.py lint-skill`, re-run after **every** document edit (7 times) | exit **0**, **32 checks, `failed: []`** every time |
| AST diff of every `Check(...)` id against `git show c80f341:scripts/sdle.py` | 23 → 26 registration sites; **added exactly** `discovery_is_gateless`, `discovery_is_declared_by_exactly_one_flow`, `discovery_vocabulary_is_not_restated_in_prompt_files`; **removed none** — which is what "29 → 32, none removed or weakened" means |
| AST diff of every `Refused(...)` / `IntegrityError(...)` reason code against `c80f341` | **9 added, 0 removed**; the ninth, `discovery_workitem_required`, was missing from ADR-005 |
| AST walk of `discovery_precondition` / `flow_precondition` / `governance_precondition` / `baseline_precondition` / `establish_baseline` call sites | `baseline_precondition` **1** site (`cmd_init`, line before the first `mkdir`); `establish_baseline` **1** site (`cmd_gate_approve`); `discovery_precondition` **3** sites (`apply_advance`, `cmd_gate_approve`, `cmd_skip`) — the correction behind ADR fix 4 |
| Byte-identity vs `c80f341`, 26 paths, line endings normalised | **none differ** — `test_integration_01_happy_path.py`, all nine `docs/dry-runs/*`, `templates/state.json`, `hooks/hooks.py`, `settings.json`, `.gitignore`, `gate-protocol.md`, `security-review.md`, every file under `.claude/commands/` |
| `FLOW_PHASES` rows parsed out of `c80f341`'s `SKILL.md` and compared element-wise | `ITERATIVE`, `DEFECT_FIX`, `HOTFIX` **identical**; `BROWNFIELD_DISCOVERY` differs by exactly `['discovery']`; GREENFIELD is not a row |
| `GREENFIELD_V1_PHASES` parsed from both revisions | **identical**, 19 entries, no `discovery` |
| `templates/state.json` | `workflow_version` `1.16`; `approvals` exactly the eight pre-T07 keys |
| Python walk of every text file for `gate_discovery` (rtk-proxy grep gave a false negative earlier in this migration, so this was a Python walk) | **1** product/test hit: `tests/test_lint_skill.py:340`, inside the negative fixture that proves `discovery_is_gateless` fires. The other three hits are this handoff describing that fact |
| Real-search reproduction of D10's carve-out over the test's own `searchable_files()` set | 28 files; the five one-word ids match **5** files in total (`architecture` 4, the others 1 each) — the measurement behind ADR fix 6 |
| **Live refusal reproduction**, real CLI, throwaway git repository (created, driven, deleted) | WI at `discovery` under `BROWNFIELD_DISCOVERY`: `advance --to constitution_draft` → exit **1** `discovery_missing`; `skip --confirm` → exit **1** `discovery_missing`; `gate approve --gate gate_constitution` → exit **1** `not_at_gate`. **`audit.md` and `state.json` SHA-256 identical before and after all three**, and `audit verify` exit **0** `chain_ok: true` afterwards |
| Same run, R2 at `init` | second WorkItem assessed `ITERATIVE` against a repository whose `baseline show` reports `ABSENT` → exit **1** `baseline_required`; the only members in its runtime afterwards are `governance.json` and `evidence/`, both written by `governance assess` **before** `init` — `init` itself created no `state.json`, no `audit.md`, no `execution.json` |
| `rtk proxy "python -m pytest --collect-only -q -p no:cacheprovider"` after every context-3 edit | **1025 tests collected**, RAW_EXIT 0 — context 3 added no test |
| `rtk proxy "python -m pytest tests/test_units_flow_model.py::test_the_two_guard_surfaces_are_unchanged tests/test_units_discovery.py::test_n14_... tests/test_units_discovery.py::test_the_discovery_needles_are_not_english_words -q"` | first run **1 failed, 2 passed** (RAW_EXIT 1) — the new manifest pin matched a comment; rewritten onto the AST, re-run **1 passed**, RAW_EXIT 0 |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=8/12 next=T08`, exit **0** |
| **Final full suite, after every context-3 edit** | **`1025 passed in 1221.55s (0:20:21)`, RAW_EXIT 0, no short-summary lines** |
| `rtk proxy "python -m pytest tests/test_units_discovery.py tests/test_lint_skill.py -q"` **after** the final suite | **89 passed in 63.07s**, RAW_EXIT 0. Two ADR-005 wording edits landed after the full run had started, and `test_n14_*` reads `docs/architecture/` at runtime, so the two files that read the documentation were re-run against the exact final tree rather than leaving a timing gap |
| Python 3.11 | **NOT_RUN** — this host runs 3.13 |
| CI (`ubuntu-latest`, `windows-latest`) | **NOT_RUN** — the branch is local-only and has never been pushed |

The F1 `ENVIRONMENT_FLAKE` procedure was treated as **VOID**. The one failure
context 3 saw was investigated as a real defect and was one: an assertion of
mine that matched an explanatory comment rather than code. It was fixed, not
re-run.

---

## Git evidence

- **HEAD:** `9c10eb5` (`Plan T08 brownfield discovery and baseline convergence`).
  T08 is entirely uncommitted; the phase commits once.
- **Working tree (product/test):** `.claude/skills/sdle/SKILL.md`,
  `.claude/skills/sdle/modules/phase-execution.md`, `CLAUDE.md`, `README.md`,
  `docs/SDLE-Reference-Guide.md`, `scripts/sdle.py`, `tests/conftest.py`,
  `tests/test_lint_skill.py`, `tests/test_units_cli.py`,
  `tests/test_units_flow_model.py`, `tests/test_units_governance.py`,
  `tests/test_units_infra.py`, `tests/test_units_repo_config.py`,
  `tests/test_units_workitem_resolution.py`; new `tests/test_units_baseline.py`,
  `tests/test_units_discovery.py`,
  `docs/architecture/ADR-005-brownfield-discovery-and-baseline.md`.
- **Working tree (transition artifacts):** `T08-checkpoint-a01-01.md` …
  `-05.md`, this handoff, and the `progress.md` row.
- **Out of scope and untouched:** `.claude/settings.local.json` was already
  modified before this phase began and no edit of this phase touched it.
- **Diff scope at the end of M6, measured by context 3:**
  `git diff --shortstat c80f341` → **18 files changed, +2888 / -86**.
  Excluding the out-of-scope `.claude/settings.local.json` and everything under
  `docs/transition/` (control-plane artifacts, not product):
  **14 files changed, +1850 / -83**, plus three new product/test files
  (`ADR-005`, `tests/test_units_discovery.py`, `tests/test_units_baseline.py`).

---

## ADR-005: verified, and corrected

ADR-005 was written ahead of its M6 slot, which is exactly the condition under
which a design record goes stale silently. It has therefore been read against
the shipped engine **twice**, by two different contexts, and corrected in place
rather than rewritten. Six inaccuracies were found in total. None of them was in
D3 — the split that is this phase's actual deliverable — which was recorded
correctly from the start and was left as written.

### Found and fixed by context 2

1. **"Four new commands", followed by a list of five.** Corrected to five, and
   the stale claim that "two are runtime-free at the group level" was replaced
   by what is actually true.
2. **D6 did not record two deliberate properties of the writer** — that it
   returns `(path, sha256)` rather than the `Paths` member, which is what keeps
   `cmd_gate_approve` out of the repository-configuration reference set and
   preserves the T05-era containment clause **unchanged**; and that it
   establishes nothing under the legacy `.workflow/` binding, because §14's
   second required fact is the producing WorkItem. Both are now recorded, with
   the reasoning.
3. **The Consequences section did not record that the §11 differential proof
   was restated rather than dropped.** It now states exactly what the new
   clause asserts and what would still fail it.

Context 3 verified all three fixes are on disk and correct: the Consequences
list names five commands and five are listed, and D6 now records both the
`(path, sha256)` return and the legacy-binding skip, both of which match
`establish_baseline`'s shipped body.

### Found and fixed by context 3

Each was found by running a command against the engine, not by re-reading prose.

4. **D4 placed the precondition in the wrong number of places.** It said
   `discovery_precondition` "lives in `apply_advance`". An AST walk of
   `scripts/sdle.py` reports **three** call sites — `apply_advance`,
   `cmd_gate_approve` and `cmd_skip` — which is the same shape
   `governance_precondition` and `flow_precondition` already have, and it exists
   because `cmd_gate_approve` and `cmd_skip` append to the ledger *before* they
   delegate, so a refusal raised only inside `apply_advance` would strand an
   orphan entry. D4 now records that, and why it is what being a pure reader
   buys.
5. **The Consequences refusal list was one short.** The engine adds **nine** new
   reason codes over `c80f341` (an AST diff of every `Refused(...)` and
   `IntegrityError(...)` first argument); the ADR listed eight, omitting
   `discovery_workitem_required`. Now nine, with "no existing refusal is removed
   or renamed" — which the same diff confirms.
6. **D10 overstated the carve-out.** It said the five one-word category ids
   "would match a dozen pre-existing files". A real search over the exact file
   set the test covers matches **five files in total**, and `apis` appears only
   in `modules/security-review.md` while `adrs` appears only in ADR-005 itself.
   The justification is now the measured one. The identical claim in the test's
   own docstring was corrected to match.
7. **D12 claimed a pin that did not exist.** "A test pins both sets" was true of
   `SDLE_OWNED_PREFIXES` and not of `cmd_manifest_build`'s exclusion. Fixed by
   **making the claim true** — the missing half is now pinned on the parsed
   source — rather than by weakening the sentence, because the residual is
   inherited by T11 and a half-pinned residual is how one gets adopted silently.
8. **"What this deliberately does not do" credited one test with two
   properties.** `required_gate_set`'s caller set and "neither moves a phase"
   are pinned by two different tests, one of them T06's. Now stated as what each
   actually asserts.

Two smaller precision edits: D2 said the evidence document sits "beside"
`discovery.json` when it is written into the runtime's `evidence/` directory,
and D6 said the discovery status follows the flow when the builder in fact
derives it from the presence of an accepted record — which is *why* both
completions produce the same key set without the builder knowing which flow it
serves. A forward pointer was also added to the Context section: ADR-002
recorded that `baseline.json` was named but that "no code writes it — the phase
that owns the baseline schema creates the file", and ADR-005 is where that
sentence stops being true. **ADR-002 and ADR-004 were not edited** — a
superseded decision record is superseded by a new one, not rewritten.

D3's split — which classification properties are **guarantees** and which are
**claims by their author** — was already recorded verbatim and unhedged, and is
also published by `discovery schema` as `enforced` / `not_enforced`, so it is
machine-readable rather than merely documented. It was left as written, and the
doc sweep was checked for the opposite failure: neither the README paragraph nor
the Reference Guide's phase section rounds the enforced half up into a claim the
engine cannot make. Both name the three things the engine cannot judge.

---

## Known limitations / risks

- **`.sdle/baseline.json` is visible to a later WorkItem's `implement preflight`
  dirty-tree guard and to the Gate 7 manifest**, because `.sdle/` is in neither
  `SDLE_OWNED_PREFIXES` nor `cmd_manifest_build`'s exclusion. This is real, it
  is the same exposure T05 created with `.sdle/config.json`, and it was
  **deliberately not fixed**: widening a guard's exclusion set is a
  safety-reducing edit outside T08's goal. Recorded as a **T11 residual**
  alongside T04 N-7, and pinned by a test so adopting it later cannot be silent.
- **The baseline decision is made once, at `init`.** A repository-level fact
  that changes mid-run (someone deleting a design document during
  implementation) does not refuse the running WorkItem. That is D8's declared
  consequence, not a defect.
- **"Significant existing source" is still a human and model judgement.** §14's
  first conjunct is deliberately not made deterministic (D9).
- **Python 3.11 and CI are unobserved.** T08 adds no syntax or stdlib surface
  beyond what T05–T07 already use, but that is an inference, not an observation.
- **The Reference Guide's revision-history table has no v1.16 row.** It stops at
  1.4 / v1.15; T06 and T07 added none either. Pre-existing, out of T08's scope,
  recorded rather than silently fixed. Two neighbouring pre-existing
  inconsistencies were observed and also left alone: the guide's header says
  **Document version 1.1** and **Last updated 2026-07-06** while the revision
  history's newest row is 1.4 / 2026-08-24, and §8.1's flow diagram shows only
  the GREENFIELD traversal, so neither `impact_analysis` (T07) nor `discovery`
  appears in it. Both predate T08; fixing either would be an undeclared edit to
  a document surface this phase does not own, and both are the kind of thing
  that should be fixed deliberately rather than as a side effect.
- **ADR-002 and ADR-004 still contain sentences T08 falsifies** — "no code
  writes it" and "does not give `BROWNFIELD_DISCOVERY` its real shape". Both are
  historical decision records, both already point forward to the phase that
  would change them, and ADR-005 now quotes both. A decision record is
  superseded, not edited.
- The suite takes roughly 21 minutes on this host.

---

## Acceptance matrix (plan A1–A20)

Every row states the evidence and which context observed it. "Test" means the
named test passed inside the final full suite recorded above; where context 3
also re-derived the fact by a direct command, the command is what is cited.

| # | Verdict | Evidence |
|---|---|---|
| **A1** | MET | `constants`, context 3: registry **21** with `discovery` at index 1; entries incl. `complete` GREENFIELD 19 · BROWNFIELD_DISCOVERY 20 · ITERATIVE 17 · DEFECT_FIX 15 · HOTFIX 11 |
| **A2** | MET | `FLOW_PHASES` rows parsed from `git show c80f341:.claude/skills/sdle/SKILL.md` and compared element-wise, context 3: three rows identical, BROWNFIELD differs by exactly `['discovery']`; `GREENFIELD_V1_PHASES` identical across both revisions. Also `test_the_four_other_flows_are_element_wise_unchanged`, `test_brownfield_discovery_changed_by_exactly_one_inserted_element` |
| **A3** | MET | `constants` + template, context 3: `discovery` in no `PHASE_TO_GATE_KEY` key or value, no `ARTIFACT_OWNERSHIP`, no `GATE_TO_EXECUTION_PHASE`, no `PROGRESS_MAP` row; `approvals` exactly 8 keys. `lint-skill` check `discovery_is_gateless` passing. Python walk: the only `gate_discovery` in product or test code is the negative lint fixture |
| **A4** | MET | `tests/test_units_discovery.py` — one refusal test per rule R-a…R-j, plus `test_n8_every_category_unknown_is_accepted`. All passed in the final suite |
| **A5** | MET | Live CLI reproduction, context 3 (table above): `advance` and `skip --confirm` refuse `discovery_missing`, `gate approve` refuses, `audit.md` and `state.json` SHA-identical across all three, `audit verify` exit 0. R2 at `init` refuses and creates no `state.json`/`audit.md`/`execution.json`. Plus `test_n9`, `test_n12` (parametrised), `test_n17_a_refused_validate_leaves_the_ledger_untouched`, `test_n24_the_refusal_leaves_the_ledger_and_the_repository_untouched` |
| **A6** | MET | `lint-skill` exit 0, **32 checks, `failed: []`**, re-run after every document edit. AST diff of `Check(...)` ids vs `c80f341`: 3 added, **0 removed**. Firing tests for all three new checks in `test_lint_skill.py` |
| **A7** | MET | `test_n15_the_baseline_reader_never_swallows_and_defaults` — no `Return` inside any `ExceptHandler` of `read_baseline`, and the positive contrast that `read_repo_config` has one. Plus `test_n15_every_malformed_baseline_is_an_integrity_failure` and the exit-3 CLI test |
| **A8** | MET | `test_n23_both_establishing_flows_produce_the_same_baseline_shape` — two repositories driven to `complete` through the real CLI, both `VALID`, same required key set, `NOT_REQUIRED` vs `PERFORMED` |
| **A9** | MET | `test_n24_the_second_workitem_does_not_rediscover_the_repository` — driven, not asserted: WI-A completes BROWNFIELD_DISCOVERY, WI-B's `init` with that flow refuses `baseline_present` and creates no runtime, re-assessed `ITERATIVE` it completes and `discovery` appears in neither `phase_history` nor its `audit.md` |
| **A10** | MET | `test_n21_the_descriptor_carries_all_nine_section_14_facts`, `test_n21_no_referenced_file_body_appears_in_the_baseline` |
| **A11** | MET | `test_the_material_invalidation_set_is_exactly_three_checks`, `test_n18_*` (three), `test_n19_a_changed_reference_is_a_warning_and_yields_stale` |
| **A12** | MET | `test_n14_no_discovery_vocabulary_is_restated_outside_sdle_py` over T06's `_searchable_files()` set, re-run by context 3 after every document edit; `lint_skill` check `discovery_vocabulary_is_not_restated_in_prompt_files` |
| **A13** | MET | Byte-identity comparison vs `c80f341` with line endings normalised, context 3: `test_integration_01_happy_path.py` and all nine `docs/dry-runs/*` identical |
| **A14** | MET | Same comparison: `templates/state.json`, `.claude/hooks/`, every file under `.claude/commands/`, `.claude/settings.json`, `.gitignore`, `gate-protocol.md`, `security-review.md` identical. `version_string_consistent` reports v1.16 at all four locations; `tables_wellformed` reports **16** migration rows |
| **A15** | MET | `git diff --stat c80f341 -- tests/conftest.py` → **+66 / −0**, exactly `establish_baseline` and `record_discovery` added and nothing else changed |
| **A16** | MET | The TP-003 table above lists every changed test site with its category and reason. Four files outside the plan's table are named explicitly with why. No test deleted, skipped, xfailed or weakened |
| **A17** | MET | Collected **1025**, RAW_EXIT 0, re-run by context 3 after its last edit. Final full suite: **`1025 passed in 1221.55s (0:20:21)`, RAW_EXIT 0, no short-summary lines**, RAW_EXIT read with no pipe. The pre-T08 count of 901 is the figure recorded at T07 and is **not** re-observed here, so the arithmetic 1025 − 901 = **124 tests added by T08** inherits that provenance; what context 3 observed directly is 1025 collected and 1025 passed |
| **A18** | MET | `python tools/transition/validate.py` → `TRANSITION_VALID: complete=8/12 next=T08`, exit **0**, re-run after the `progress.md` edit; the T08 row was checked for a literal `\|` inside a cell by a script, not by eye |
| **A19** | MET | `governance gates` still `advisory: true` and `required_gate_set` still has exactly its two governance callers (`test_n34_*`); `.claude/agents/` unchanged and control-plane only; `GREENFIELD_V1_PHASES` identical to `c80f341` and still not a `FLOW_PHASES` row; legacy dual-read and `migrate-workflow` untouched, and both new preconditions plus the baseline writer skip the legacy binding |
| **A20** | MET | `docs/architecture/ADR-005-brownfield-discovery-and-baseline.md` D3 states the split explicitly, in two labelled halves, and `discovery schema` publishes the same split as `enforced` / `not_enforced`. The doc sweep was checked for the opposite failure — no document rounds the enforced half up |

---

## Claims for verifier to independently check

1. `python scripts/sdle.py constants` → 21-entry registry with `discovery` at
   index 1; flow shapes GREENFIELD 19, BROWNFIELD_DISCOVERY 20, ITERATIVE 17,
   DEFECT_FIX 15, HOTFIX 11 (entries **including** `complete`). **[A1]**
2. Reconstruct `c80f341`'s `SKILL.md` in a temp tree and diff the flow lists:
   only `BROWNFIELD_DISCOVERY` changed, by exactly one inserted `discovery`.
   **[A2]**
3. `discovery` has no gate machinery and `approvals` still has eight keys; the
   only `gate_discovery` string in the repository is a negative lint fixture.
   **[A3]**
4. `discovery assess` refuses R-a…R-j with the stated reason codes at exit 1,
   and an all-unknown document is accepted. **[A4]**
5. Reproduce a refusal at `advance`, `skip`, `gate approve`, `init` and
   `discovery assess`; confirm `audit.md` is byte-identical and `audit verify`
   exits 0, and that a refused `init` creates no runtime directory. **[A5]**
6. `lint-skill` exit 0 with 32 checks, the 29 pre-T08 ones all present and
   passing, each new one with a firing test. **[A6]**
7. `read_baseline` has no `return` in any exception handler; `read_repo_config`
   still does. **[A7]**
8. Drive GREENFIELD in one repository and BROWNFIELD_DISCOVERY in another; both
   produce a `VALID` baseline with the same required key set. **[A8]**
9. **Drive §14's exit criterion**: WI-A completes BROWNFIELD_DISCOVERY, WI-B's
   `init` with that flow refuses `baseline_present` and creates nothing, and
   re-assessed ITERATIVE it completes without entering `discovery`. **[A9]**
10. The descriptor carries all nine §14 facts and no artifact body. **[A10]**
11. Material invalidation is exactly `baseline_invalid`,
    `baseline_producer_unregistered`, `baseline_reference_missing`;
    `baseline_reference_changed` yields `STALE` and refuses nothing. **[A11]**
12. No discovery category id, classification token or envelope key appears in
    any file of `_searchable_files()`. **[A12]**
13. `test_integration_01_happy_path.py` and the nine transcripts are
    byte-identical to `c80f341` with line endings normalised. **[A13]**
14. The state template, hooks, commands, settings, `.gitignore` and
    `gate-protocol.md` are byte-identical to `c80f341`; v1.16 at all four
    locations; 16 migration rows. **[A14]**
15. `git diff tests/conftest.py` is `+66 -0` and adds exactly two methods.
    **[A15]**
16. Every changed test function is in the table above with its category.
    **[A16]**
17. Full suite: collected, passed and raw exit code, read with no pipe.
    **[A17]**
18. `python tools/transition/validate.py` exit 0; the `progress.md` T08 row
    contains no literal `|` inside a cell. **[A18]**
19. No T09/T10/T11 leakage: `governance gates` still `advisory: true`; no gate
    conditional on risk; **no product subagent** — `.claude/agents/` holds only
    the four `sdle-transition-*` migration control-plane files, unchanged since
    `a12b9e2` and explicitly excluded from T10 evidence by the plan; legacy
    dual-read and
    `migrate-workflow` still work and still never mutate `.workflow/`;
    `GREENFIELD_V1_PHASES` unchanged and still not a `FLOW_PHASES` row. **[A19]**
20. ADR-005 exists and states D3's enforced/not-enforced split explicitly.
    **[A20]**

---

## Blocker

**None.** No material architecture, contract or governance decision arose that
required a human. Every decision made was one the plan had already pinned, or
an ordinary implementation defect fixed in place and recorded above.
