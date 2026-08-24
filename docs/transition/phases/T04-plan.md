# T04 Plan

**Phase:** T04 — Bind Spec Kit to the Active WorkItem (contract §10)
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED

Precondition HEAD at planning time: **`88e78a5`** on `transition/workitem-v1`.
Rollback point for T04: **`beb28f2`** (proved below).
Product baseline: `f8fdaa0`.

---

## Objective

Make WorkItem identity the outer orchestration boundary for Spec Kit, per contract §10:

1. Introduce the `specKit` state object (`featureId`, `featureDirectory`, `workflowId`, `runId`) and supersede `current_feature_id` as primary SDLE identity. This is a **schema change**: `workflow_version` 1.14 → 1.15, a 15th `VERSION_MIGRATION` row, a matching `_mig_1_14` step, and the six version-string sites.
2. Move Spec Kit's WorkItem-specific native artifacts under the active WorkItem (`workitems/<id>/specs/<feature-id>/`), leaving genuinely repository-wide Spec Kit scaffolding (`.specify/`, including `memory/constitution.md`) where it is.
3. Configure Spec Kit through its **supported** environment mechanisms (`SPECIFY_INIT_DIR`, `SPECIFY_FEATURE_DIRECTORY`) **only when the installed Spec Kit is detected to support them**, and **fail closed** when it is not.
4. Discharge inherited finding **NB-1**: delete the transitional `.workflow/` prefix bridge in `resolve_artifact_path` by moving the `ARTIFACT_OWNERSHIP` templates themselves.

Contract §10 exit criterion: *a full current 18-phase flow can run against WorkItem-scoped Spec Kit context.*

---

## Repository evidence

Every figure below was produced by a command run in **this** planning context, or read from the file named. Nothing is copied from a prior phase's narrative.

| Claim | Class | Evidence |
|---|---|---|
| HEAD is `88e78a5` ("Refresh the cold-start note for T04"); working tree carries only `M .claude/settings.local.json` | OBSERVED | `git log --oneline -3`, `git status --porcelain` |
| `beb28f2..HEAD` touches only `docs/transition/RESUME.md`, `docs/transition/phases/T03-verification-a01.md`, `docs/transition/progress.md` — no product file — so the T04 rollback point is `beb28f2` | OBSERVED | `git diff --name-only beb28f2 HEAD`; `git diff --numstat beb28f2 HEAD` → 3 rows |
| `python tools/transition/validate.py` prints `TRANSITION_VALID: complete=4/12 next=T04`, raw exit 0 | OBSERVED | run in this context |
| `python scripts/sdle.py lint-skill` → raw exit 0, **22 checks, 22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 14 migration rows`, `all four locations report v1.14`, `migration_covers_every_state_field: every field has a migration row` | OBSERVED | run in this context |
| Full suite at `88e78a5`: **`438 passed in 342.41s (0:05:42)`, raw exit 0**; `-rsxX` produced **no** short-summary section; `--collect-only` = **438 tests collected**, so collected == passed and there are zero skips, xfails or errors | OBSERVED | `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` and `--collect-only`, both run in this context |
| Host interpreter is **Python 3.13.0** | OBSERVED | `python --version` |
| `CURRENT_VERSION = "1.14"` (`scripts/sdle.py`, anchor `CURRENT_VERSION = "1.14"`); `MIGRATIONS` list has 14 tuples, terminal `("1.13", "1.14", _mig_1_13)` | OBSERVED | source read |
| `templates/state.json` contains top-level `current_feature_id` and **no** `specKit` key | OBSERVED | file read |
| NB-1 is present and unchanged: `resolve_artifact_path` contains `legacy_prefix = ".workflow/"` and rewrites a `.workflow/`-prefixed template onto `paths.runtime_relative`; its docstring says "Transitional: it goes away when the table itself moves" | OBSERVED | source read, function `resolve_artifact_path` |
| `resolve_artifact_path` has exactly **7** call sites and **all 7 pass `paths`** | OBSERVED | `grep -n 'resolve_artifact_path(' scripts/sdle.py` → 1 def + 7 calls |
| `ARTIFACT_OWNERSHIP` (SKILL.md) has 8 rows; 4 use `{current_feature_id}` under `.specify/specs/`, one (`gate_analyze`) also does, `gate_implement` is the literal `.workflow/implementation-manifest.md` | OBSERVED | SKILL.md section `### ARTIFACT_OWNERSHIP` |
| The `ARTIFACT_OWNERSHIP` parser reads only the `gate_key` and `artifact_path_template` columns; the third column is documentation | OBSERVED | `scripts/sdle.py`, `for row in parse_md_table(skill, "ARTIFACT_OWNERSHIP")` |
| `_check_migration_covers_state_fields` requires every **top-level** template key outside a 9-member `base` set to appear as a literal substring in the concatenated `action` column of `VERSION_MIGRATION`. Nested keys are not checked | OBSERVED | function `_check_migration_covers_state_fields` |
| `_check_version_consistency` reads **six** sites in four documents: `templates/state.json`, SKILL.md frontmatter (`Lifecycle Engine v<X.Y>`), SKILL.md heading (`^# SDLE...(v<X.Y>)`), README title, README first `**v<X.Y>**` match, `docs/SDLE-Reference-Guide.md` first `SDLE v<X.Y>` | OBSERVED | function `_check_version_consistency`; the four version-carrying lines located by grep |
| `read_state` does **not** migrate; nothing refuses a stale `workflow_version` outside `migrate` / `migrate-workflow`. A pre-1.15 state therefore reaches every reader without a `specKit` key | OBSERVED | `def read_state`, `grep -n 'workflow_version' scripts/sdle.py` |
| `RUNTIME_FREE_COMMANDS` is a 6-member frozenset: `lint-skill`, `sha`, `constants`, `workitem`, `migrate-workflow`, `validate`. **`feature` is not a member**, so `bind_workitem` runs before any `feature` subcommand handler | OBSERVED | `RUNTIME_FREE_COMMANDS` definition + `if args.command not in RUNTIME_FREE_COMMANDS: paths = bind_workitem(...)` in `main` |
| `cmd_feature_resolve` scans `paths.project_root / ".specify" / "specs"`, picks newest mtime, refuses `feature_unresolved` / `feature_ambiguous`, writes `state["current_feature_id"]` | OBSERVED | function `cmd_feature_resolve` |
| `SDLE_OWNED_PREFIXES` = `.workflow/ workitems/ .specify/ design/ reviews/ clarifications/ guidance/ requirements/` — so specs relocated under `workitems/` remain excluded from the `implement preflight` dirty-tree guard with **no edit** | OBSERVED | `SDLE_OWNED_PREFIXES` definition |
| `cmd_manifest_build` excludes only `paths.runtime_relative + "/"` from `changed`; the in-repo comment forbids widening it to `SDLE_OWNED_PREFIXES` | OBSERVED | `cmd_manifest_build`, comment "Only the runtime is excluded here" |
| `.claude/hooks/hooks.py`: `FENCED = (".workflow", "workitems", "requirements", "guidance")`; the `workitems` entry of `FENCE_REASONS` contains a literal forward note: *"NOTE for the phase that moves clarifications/, reviews/ and Spec Kit artifacts under workitems/: fence the whole tree today and carve out those artifact subpaths then; loosening later is a one-line change."* | OBSERVED | file read |
| `.gitignore` ignores `.specify/`; `git check-ignore -v workitems/demo/specs/001-x/spec.md` exits **1** (not ignored). Relocating specs under a WorkItem therefore makes them versioned with **zero `.gitignore` edits**, satisfying §19's "required WorkItem Spec Kit artifacts" | OBSERVED | `.gitignore` read; `git check-ignore` run in this context |
| The repository contains **no `.specify/` directory** and pins **no Spec Kit version** (README and `cmd_preflight` both install from `git+https://github.com/github/spec-kit.git`, i.e. moving HEAD) | OBSERVED | `ls -a`; `grep -rn 'spec-kit'` over README/docs/scripts |
| Test surface to rebind: **17** lines matching `.specify/specs` across 5 files — `test_hooks.py` 1, `test_integration_01_happy_path.py` 5, `test_integration_02_to_05.py` 3, `test_integration_06_to_09.py` 7, `test_units_transitions.py` 1 | OBSERVED | `grep -rc '\.specify/specs' <files>` |
| Test surface naming the feature field: **4** lines — `test_units_transitions.py` 3 (`test_gate_show_reports_unresolved_feature_id`, `test_gate_show_substitutes_feature_id`) and `test_units_workitem_runtime.py` 1 (the migrate-workflow field list, which also asserts `migrated["workflow_version"] == "1.14"`) | OBSERVED | `grep -rn 'current_feature_id\|feature_id' tests/` |
| `test_units_workitem_resolution.py::test_runtime_free_commands_is_a_closed_enumerated_set` asserts the frozenset **exactly**; `::test_workitem_rebinding_happens_only_at_the_declared_sites` asserts the exact set of functions calling `dataclass_replace(paths, workitem=...)`; `::test_validate_is_clean_in_a_healthy_repository` asserts `findings == []` in a fresh initialised repo | OBSERVED | test file read |
| `docs/dry-runs/` has **not been touched** by any transition phase (`git log --oneline f8fdaa0..HEAD -- docs/dry-runs/` is empty) and still contains 6 stale `.workflow/` references in `01-happy-path.md` that T02 deliberately left | OBSERVED | run in this context |
| Existing refusal reasons include `feature_unresolved`, `feature_ambiguous`, `target_exists`, `speckit_missing`, `speckit_skills_missing`; none of T04's proposed new reasons collides | OBSERVED | `grep -A1 'raise Refused($' scripts/sdle.py` |
| **Host** Spec Kit is `specify 0.15.0` (`specify --version`), installed as a `uv` tool at `~/AppData/Roaming/uv/tools/specify-cli` | OBSERVED (host, not repository) | run in this context |
| Spec Kit 0.15.0 honours `SPECIFY_INIT_DIR` (repo-root override, validated to contain `.specify/`), `SPECIFY_FEATURE` and `SPECIFY_FEATURE_DIRECTORY` (relative values resolved against the repo root) in `specify_cli/core_pack/scripts/python/common.py` — functions `resolve_specify_init_dir`, `get_repo_root`, `get_current_branch`, `get_feature_paths` | OBSERVED (host) | source read |
| Spec Kit 0.15.0 persists the feature directory to a **single, repository-global** slot `.specify/feature.json` (`persist_feature_json`, `read_feature_json_feature_directory`). `get_feature_paths` prefers `SPECIFY_FEATURE_DIRECTORY` over that slot, and errors out (`SystemExit(1)`) when neither is usable | OBSERVED (host) | source read |
| Spec Kit 0.15.0 **does not** honour `SPECIFY_FEATURE_DIRECTORY` when *creating* a feature: `create_new_feature.py` hardcodes `specs_dir = repo_root / "specs"` and then `persist_feature_json(repo_root, f"specs/{branch_name}")` | OBSERVED (host) | source read |
| SDLE's current code and prompts assume features live at `.specify/specs/<id>/`, which is **not** where Spec Kit 0.15.0 creates them | OBSERVED | `cmd_feature_resolve`, `ARTIFACT_OWNERSHIP`, `modules/phase-execution.md` vs. the line above |
| Therefore the location at which a *user's* installed Spec Kit creates a feature directory cannot be known at design time | INFERRED | from the two rows above plus the unpinned install |
| Contract §3's target tree places "Spec Kit native WorkItem artifacts" **inside** `workitems/<wi>/` and keeps `.specify/` at repository root for "Spec Kit engine/project scaffolding where required" | OBSERVED | `docs/transition/transition.md` §3 |
| `docs/transition/baseline.md` classifies `current_feature_id` **SUPERSEDE_LATER @ T04**, `feature` / `feature resolve` **SUPERSEDE_LATER @ T04**, `artifact path`, `current_artifact`, `speckit_initialized`, `speckit_skill_prefix` **ADAPT @ T04** | OBSERVED | `grep -n 'T04' docs/transition/baseline.md` |
| Whether CI (Python 3.11 on `ubuntu-latest` / `windows-latest`) passes anything in this branch | UNKNOWN | branch is local-only; no 3.11 interpreter on this host; no CI run has ever been observed. No outcome is predicted. |
| What Spec Kit version a given user has installed, and whether it supports the two env mechanisms | UNKNOWN | no version pin exists in the repository; this is precisely why T04 capability-detects and fails closed |
| Whether a future Spec Kit could support a capability without shipping the scripts the probe reads | UNKNOWN | the probe's failure direction is **closed** (refuse), never open — see F6 |

### Baseline suite run

Run in this planning context at `88e78a5`, on Python 3.13.0:

```
rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"
438 passed in 342.41s (0:05:42)
RAW_EXIT=0

rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"
438 tests collected in 0.29s
```

Collected equals passed, and `-rsxX` produced no short-summary section — so the baseline has **zero skips, xfails and errors**. The implementer MUST re-derive this before starting and treat any difference as a finding, not as noise.

The `rtk` shell proxy hands back a false green for a bare `python -m pytest` (`Pytest: No tests collected`, exit 0). Every pytest invocation in this phase must go through `rtk proxy`, must not be piped, and must have its raw exit read directly. Note that the transition guard blocks output redirection for planner and verifier Bash, so the run is read from the tool's own output rather than from a file. The full suite took 5m42s here; use a 600000 ms timeout regardless.

**The F1 `ENVIRONMENT_FLAKE` procedure from T00–T02 is VOID.** `6e8af8c` fixed the `write_atomic` `WinError 5` flake. Any failure during T04 is a presumed T04 regression and must be investigated as one. `write_atomic` must not be touched.

---

## Behavioral delta

### Deliberate changes

**D1 — WorkItem-scoped Spec Kit feature directory.**
The active WorkItem's Spec Kit feature directory becomes `workitems/<workitem-id>/specs/<feature-id>/`. Repository-root `.specify/` stays exactly where it is and keeps hosting Spec Kit engine scaffolding *and* `memory/constitution.md`, which is genuinely repository-wide (§10's constitution nuance; §3's tree). Nothing is copied into WorkItems for directory aesthetics: only the WorkItem's own feature directory moves.

`Paths` gains two derived members, so no call site ever concatenates a Spec Kit path of its own (the T02 discipline):

- `speckit_specs_root: Path | None` → `workitem_root / "specs"`, `None` under the legacy binding;
- `speckit_specs_relative: str | None` → the same as a repo-relative POSIX prefix.

**D2 — `specKit` state object; `current_feature_id` superseded.**
`templates/state.json` gains, in place of `current_feature_id`:

```json
"specKit": {
  "featureId": null,
  "featureDirectory": null,
  "workflowId": null,
  "runId": null
}
```

`current_feature_id` is **removed** from the template, not retained as a mirror. Rationale, pinned so the implementer does not re-litigate it: §10's "New state conceptually becomes" sample contains no `current_feature_id`; `baseline.md` classifies the field `SUPERSEDE_LATER @ T04`; and keeping two fields for one fact violates invariant 7 ("one source of truth per fact"). The engine reads the value through one accessor:

```
def speckit_ref(state) -> dict   # returns the specKit object, defaulted, never KeyError
```

so a pre-1.15 state (no `specKit` key) degrades to all-null rather than crashing — see D3 and F5.

`workflowId` and `runId` are created and **always written as `null` by T04**. §10 shows them null; SDLE has no producer for either, and §27 forbids speculative implementation. An acceptance criterion pins that no T04 code path writes a non-null value.

**D3 — Version 1.14 → 1.15 with a real migration.**
`CURRENT_VERSION = "1.15"`; a 15th `VERSION_MIGRATION` row; `_mig_1_14` appended to `MIGRATIONS`. The row's `action` text **must contain the literal `specKit`**, because `_check_migration_covers_state_fields` matches template keys as substrings of the concatenated action column.

`_mig_1_14` does exactly this, deterministically and without guessing:

1. `_add_missing(state, specKit={...all four keys null...})`.
2. `featureId = state.pop("current_feature_id", None)` — the value moves, the old key is deleted.
3. `featureDirectory` derivation, in this fixed order, first hit wins, `None` if none hits:
   a. `workitems/<state["workitem"]>/specs/<featureId>` if that directory exists on disk;
   b. `.specify/specs/<featureId>` if that directory exists on disk — this is the pre-1.15 native location, and preserving it is what keeps an **in-flight** v1.14 workflow resolvable instead of breaking its gates;
   c. `None`.
   Each candidate is tested by existence, so the derivation is a fact about the tree, not an inference.
4. Nothing is moved on disk by the migration.

**D4 — Capability detection, single-sited, failing closed.**
One function:

```
SPECKIT_REQUIRED_CAPABILITIES = ("SPECIFY_INIT_DIR", "SPECIFY_FEATURE_DIRECTORY")
def detect_speckit_capabilities(paths) -> dict
```

It probes the **target project's own** Spec Kit installation — the files Spec Kit itself placed there — for each capability name:

- root probed: `<project-root>/.specify/scripts/`, recursively, files with suffix `.py`, `.sh`, `.ps1` only, read with `errors="replace"`, each file read at most once;
- a capability is `supported` iff its literal env-var name occurs in at least one such file; the first matching repo-relative path is recorded as `evidence`;
- the result also carries `speckit_present` (`.specify/` is a directory) and `scripts_present` (`.specify/scripts/` is a directory).

This detects a *documented, user-facing environment variable by name inside the installation's own scripts*. It does not read, parse or depend on any internal data structure, and it never executes Spec Kit. Its failure direction is closed: an installation that supports a capability without shipping a script mentioning it is reported unsupported, and SDLE refuses rather than proceeding (F6).

**D5 — `feature bind`: the pre-invocation choke point.**
New subcommand under the existing `feature` group (**not** a new top-level `speckit` command — invariant 3 keeps `speckit` out of anything the user sees in a tool call). Because `feature` is not in `RUNTIME_FREE_COMMANDS`, `bind_workitem` has already run when the handler is entered: **WorkItem resolution structurally precedes anything Spec Kit-related**, and that is mechanically provable rather than merely documented.

Behaviour:

- refuses `speckit_missing` when `.specify/` is absent (same reason name `cmd_preflight` already uses — one name, one meaning);
- refuses `speckit_capability_missing` (exit 1) when any member of `SPECKIT_REQUIRED_CAPABILITIES` is unsupported, with `data.missing`, `data.probed_root` and `data.capabilities`;
- with `--require-feature` (used by every phase after `spec_draft`), refuses `feature_directory_unresolved` (exit 1) when `specKit.featureDirectory` is null;
- on success emits `data.env` as an **ordered list of `{"name": ..., "value": ...}` objects**, never a shell string, so the prompt layer quotes for its own platform:
  - `SPECIFY_INIT_DIR` = absolute project root (§10's `<repo-root>`),
  - `SPECIFY_FEATURE_DIRECTORY` = repo-relative POSIX `specKit.featureDirectory`, **omitted** when it is null,
  - `SPECIFY_FEATURE` = `specKit.featureId`, omitted when null;
- also emits `data.workitem_specs_root` (repo-relative) and `data.capabilities`;
- **is pure**: it reads state and the filesystem and writes nothing — no state, no audit, no `.specify/` file. Purity is pinned by a recursive-SHA-map test, the same shape T03 used for `bind_workitem`.

**D6 — `feature resolve`: discover, contain, adopt.**
The existing subcommand keeps its name and its place in `phase-execution.md`, and gains WorkItem containment.

1. Under the **legacy** binding (`paths.workitem is None`) behaviour is unchanged from baseline: scan `.specify/specs/`, newest-mtime, `feature_unresolved` / `feature_ambiguous`, no relocation. The legacy dual-read rung keeps working; T11 removes it, not T04.
2. Otherwise, candidates are collected in **tiers**, and the first tier that yields at least one directory is used:
   1. `workitems/<id>/specs/*`
   2. `<project-root>/specs/*`
   3. `.specify/specs/*`
   Any path under `workitems/<other-id>/` is excluded by construction, so another WorkItem's feature can never be adopted. Tier order is a fixed, documented precedence — not a tie-break between peers.
3. Within the chosen tier the **baseline** selection rule is preserved unchanged: newest mtime, and `feature_ambiguous` when the two newest share a timestamp. T04 does not tighten or loosen this.
4. If the chosen directory is not already under `workitems/<id>/specs/`, it is **relocated** there:
   - target `workitems/<id>/specs/<dirname>`; refuse `feature_target_exists` (exit 1) if the target already exists — never overwrite, never merge;
   - both source and target are verified to resolve inside `project_root` before the move;
   - the move is `shutil.move`; on `OSError` refuse `feature_adopt_failed` (exit 1) with the source left untouched;
   - on success append audit event `speckit_feature_adopted` recording `from` and `to`.
5. Record `specKit.featureId = <dirname>` and `specKit.featureDirectory = workitems/<id>/specs/<dirname>` (repo-relative POSIX). `workflowId` / `runId` untouched.

Relocation is what makes §10's exit criterion reachable without hardcoding where Spec Kit creates a feature: the engine *discovers* the native directory and moves it into the WorkItem, rather than assuming a creation path it cannot know. Exactly one copy of the artifact exists at all times, so §10's artifact rule ("do not create an SDLE duplicate") holds — this is a move, not a copy, and SDLE never writes a spec/plan/tasks file itself.

**D7 — `feature capabilities`, and preflight enrichment.**
`feature capabilities` reports `detect_speckit_capabilities` and always exits 0 (a diagnostic, in the shape of T03's `workitem resolve`: it reports, it never picks and it never refuses). `cmd_preflight` gains **additive** `data` keys `speckit_capabilities` and `speckit_capability_problems` from the same function — one source of truth, closing baseline's `speckit_initialized` / `speckit_skill_prefix` **ADAPT @ T04** rows. `cmd_preflight`'s existing `problems` list, its refusal reasons and its messages are **unchanged**, so no existing preflight assertion moves.

**D8 — NB-1 discharged: `ARTIFACT_OWNERSHIP` moves, the bridge is deleted.**
The SKILL.md table becomes:

| gate_key | artifact_path_template | path type |
|---|---|---|
| `gate_constitution` | `.specify/memory/constitution.md` | static |
| `gate_spec` | `{speckit_feature_directory}/spec.md` | substitute `speckit_feature_directory` |
| `gate_plan` | `{speckit_feature_directory}/plan.md` | substitute `speckit_feature_directory` |
| `gate_tasks` | `{speckit_feature_directory}/tasks.md` | substitute `speckit_feature_directory` |
| `gate_analyze` | `{speckit_feature_directory}/tasks.md` | substitute `speckit_feature_directory` |
| `gate_design` | `design/app/app-design.md` | static |
| `gate_implement` | `{workitem_runtime}/implementation-manifest.md` | substitute `workitem_runtime` |
| `gate_security` | `{security_review_artifact}` | substitute `security_review_artifact` |

`resolve_artifact_path` correspondingly:

- **deletes `legacy_prefix = ".workflow/"` and the two lines that use it** — the anchor must not survive anywhere in `scripts/sdle.py`;
- substitutes `{workitem_runtime}` from `paths.runtime_relative` (which is `.workflow` under the legacy binding, so legacy behaviour is byte-identical);
- substitutes `{speckit_feature_directory}` from `speckit_ref(state)["featureDirectory"]`, returning the existing "not resolved yet" skip shape when it is null;
- takes `paths` as a **required** positional (all 7 call sites already pass it), so `{workitem_runtime}` can never silently fail to substitute;
- drops the `{current_feature_id}` placeholder entry.

**D9 — Gate precondition: a WorkItem's gate cannot approve another WorkItem's artifact.**
`gate_precondition_hook` gains a branch for `gate_spec`, `gate_plan`, `gate_tasks`, `gate_analyze`, keeping the existing early-return shape (`if not resolved: return None`): when `paths.workitem` is not `None` and `specKit.featureDirectory` does not start with `workitems/<paths.workitem>/specs/`, refuse `feature_outside_workitem` (exit 1). Under the legacy binding the check is skipped. This is the refusal a hook cannot bypass, in the same spirit as the existing `manifest_incomplete` check, and it is the structural answer to a stale repository-global `.specify/feature.json` pointing at another WorkItem (F3).

**D10 — Security review evidence follows the feature directory.**
`cmd_security_review_evidence`: the candidate list becomes `.specify/memory/constitution.md` (unchanged) plus `<featureDirectory>/{spec,plan,tasks}.md`; the diff gains `:(exclude)<featureDirectory>` when `featureDirectory` is set, alongside the existing `:(exclude).specify` and `:(exclude)<runtime_relative>`, so relocating the specs does not turn them into "implementation diff". `modules/security-review.md`'s three artifact lines follow.

**D11 — Write-fence carve-out.**
`.claude/hooks/hooks.py` `write_fence` gains a single exemption evaluated **before** the `FENCED` loop: a repo-relative path matching `^workitems/[^/]+/specs/` returns `{}` (not fenced). `workitems/index.md`, `workitems/<id>/workitem.json` and everything under `workitems/<id>/.sdle/` stay denied. The `workitems` entry in `FENCE_REASONS` has its forward-looking "NOTE for the phase that moves..." sentence replaced by a statement of the carve-out that now exists. This is the "one-line change" that note anticipated.

**D12 — Prompt and documentation layer.**
`modules/phase-execution.md`: a `sdle.sh feature bind` line is inserted **before** each Spec Kit skill invocation (Phases 2, 4, 6, 8, 9, 11, 15 and the Post-Generation Clarify block), with `--require-feature` on every one after Phase 4; the Phase 4 "Feature-ID Resolution" paragraph is rewritten to describe tiered discovery, WorkItem containment and adoption; every `.specify/specs/{state.current_feature_id}/…` expected-artifact line becomes `{state.specKit.featureDirectory}/…`; the Phase 11 `artifact record --path` line follows. `feature bind` names no Spec Kit skill, so invariant 3 is untouched.

`SKILL.md`: version ×2, the `ARTIFACT_OWNERSHIP` table, the 15th `VERSION_MIGRATION` row. `README.md`: version ×2, a new history row placed **above** the v1.14 row (the linter's `re.search` takes the first `**vX.Y**` match), and the `current_feature_id` state-field row replaced by `specKit`. `docs/SDLE-Reference-Guide.md`: header version, the four artifact-table rows, the two `current_feature_id` prose mentions, the state-field row, the one example path, and a new revision row. `.claude/commands/sdle-reset.md`: the one line enumerating what a reset clears. `CLAUDE.md`: one sentence recording that Spec Kit's WorkItem-specific artifacts are WorkItem-scoped and its scaffolding is not.

### Preserved invariants

- **Never guesses.** Tier order in D6 is fixed precedence, not a tie-break; the intra-tier rule is baseline's, unchanged; ambiguity still refuses and lists. Capability detection reports and refuses; it never assumes support.
- **Fails closed.** Missing `.specify/`, a missing required capability, an unresolved feature directory and a feature directory outside the WorkItem are all refusals (exit 1), never warnings.
- **The legacy `.workflow/` dual-read rung keeps working.** `{workitem_runtime}` resolves to `.workflow` under the legacy binding; `feature resolve` keeps its exact baseline behaviour there; `_mig_1_14` derivation step (b) keeps an in-flight v1.14 workflow resolvable. **T11**, not T04, removes any of this.
- `migrate-workflow` still never mutates `.workflow/`; `init` still refuses `legacy_workflow_present` unconditionally. T04 adds no code path near either.
- Single writer, audit hash chain, `write_atomic`, `save_state` and the session lock are untouched. `feature bind` writes nothing; `feature resolve` writes state and audit through the existing helpers only.
- **SDLE never writes `.specify/feature.json`.** That file is Spec Kit's (TP-005: do not duplicate Spec Kit). SDLE reads around it and refuses on disagreement.
- **No SDLE duplicate of a Spec Kit artifact.** D6 moves; it never copies. SDLE writes no `spec.md`, `plan.md` or `tasks.md`.
- Write fence still denies `workitems/index.md`, `workitems/<id>/workitem.json` and all of `workitems/<id>/.sdle/`. `SDLE_OWNED_PREFIXES` is unchanged.
- Invariant 3 (SpecKit opacity): no new user-visible command, path or message names a `speckit-*` skill or a `/speckit.*` command.
- Invariant 8 (gates stay in the parent): T04 delegates nothing; `feature bind` is an engine call the parent makes.
- `RUNTIME_FREE_COMMANDS` is unchanged — deliberately, because `feature` staying outside it is what makes "resolution precedes Spec Kit invocation" structural.
- No `dataclass_replace(paths, workitem=...)` is added anywhere.

---

## Files expected to change

**Engine**

- `scripts/sdle.py` — `Paths` (`speckit_specs_root`, `speckit_specs_relative`); `speckit_ref`; `SPECKIT_REQUIRED_CAPABILITIES` + `detect_speckit_capabilities`; `CURRENT_VERSION`; `_mig_1_14` + `MIGRATIONS`; `resolve_artifact_path` (bridge deleted, two placeholders, `paths` required); `cmd_feature_resolve`; new `cmd_feature_bind`, `cmd_feature_capabilities` + parser rows under the existing `feature` group; `gate_precondition_hook`; `cmd_security_review_evidence`; `cmd_preflight` (additive data keys); `collect_validation_findings` (one new check); the `header` "Feature ID" line.

**Prompt / constants**

- `.claude/skills/sdle/SKILL.md` — `ARTIFACT_OWNERSHIP`, `VERSION_MIGRATION` (+1 row), version ×2
- `.claude/skills/sdle/templates/state.json` — `specKit` in, `current_feature_id` out, version
- `.claude/skills/sdle/modules/phase-execution.md`
- `.claude/skills/sdle/modules/security-review.md`

**Hooks**

- `.claude/hooks/hooks.py` — the `workitems/<id>/specs/` carve-out and its `FENCE_REASONS` text

**Docs**

- `README.md`, `docs/SDLE-Reference-Guide.md`, `CLAUDE.md`, `.claude/commands/sdle-reset.md`

**Tests**

- new `tests/test_units_speckit_binding.py`
- `tests/conftest.py` — **exactly one** edit (see the anti-contradiction clause)
- `tests/test_integration_01_happy_path.py`, `tests/test_integration_02_to_05.py`, `tests/test_integration_06_to_09.py`, `tests/test_units_transitions.py`, `tests/test_hooks.py`, `tests/test_units_workitem_runtime.py`

**Must not change** (verify with `git diff --exit-code beb28f2 -- <paths>`): `scripts/sdle.sh`, `scripts/sdle.ps1`, `scripts/README.md`, `.claude/settings.json`, `.github/`, `docs/dry-runs/`, `docs/architecture/`, `requirements/`, `.gitignore`, `.claude/skills/sdle/modules/gate-protocol.md`, every `.claude/commands/*.md` except `sdle-reset.md`, and everything under `docs/transition/` except this plan and `progress.md`.

`.gitignore` genuinely needs no edit: `git check-ignore -v workitems/demo/specs/001-x/spec.md` exits 1 today.

`.claude/settings.local.json` is the user's permission allowlist, is already modified in the working tree, and is **out of scope** — do not stage, revert or edit it.

### Anti-contradiction clause (binding)

This plan permits **exactly one** change to `tests/conftest.py`: adding to `Project` a `specs_root` property returning `self.root / "workitems" / self.workitem / "specs"` and a `feature_dir(feature_id)` helper returning `f"workitems/{self.workitem}/specs/{feature_id}"`, plus exporting a module-level `FEATURE_ID = "001-todo-api"` if the implementer wants one shared constant. **No other change to `conftest.py` is authorised** — no fixture may be added, removed, renamed, re-scoped or given different setup, and `bare_project` keeps creating `.specify/memory/` exactly as it does now. Every other new helper belongs in `tests/test_units_speckit_binding.py`. If the implementer believes a further `conftest.py` change is unavoidable, that is a plan defect: record it as a declared divergence in the handoff with the reason, do not silently widen the edit.

Nothing in this plan asserts an exact registry, directory listing or full state-key set anywhere; the only exact-set assertions T04 relies on are the pre-existing ones named in the evidence table, and T04 changes none of them.

---

## Existing tests affected

All changes below are **TP-003 category 2** — path rebinding, version, or genuinely superseded behaviour. **No test may be weakened, skipped, xfailed or deleted.**

| File | Lines | Nature |
|---|---|---|
| `tests/test_integration_01_happy_path.py` | 5 `.specify/specs` lines + the `FEATURE` constant | path rebinding to `workitems/<id>/specs/<feature>` |
| `tests/test_integration_02_to_05.py` | 3 `.specify/specs` lines, incl. the `SPEC` module constant | path rebinding |
| `tests/test_integration_06_to_09.py` | 7 `.specify/specs` lines | path rebinding |
| `tests/test_units_transitions.py` | 3 lines: `test_gate_show_reports_unresolved_feature_id` (skip-reason string), `test_gate_show_substitutes_feature_id` (`at(..., current_feature_id=...)` and the expected path) | superseded: the substituted field is now `specKit.featureDirectory` |
| `tests/test_units_workitem_runtime.py` | the migrate-workflow field list containing `current_feature_id`, and `assert migrated["workflow_version"] == "1.14"` | superseded: field moved into `specKit`; version is now `1.15` |
| `tests/test_hooks.py` | 1 `.specify/specs` line in the write-fence *allow* parametrize list | unchanged in meaning; a `workitems/<id>/specs/…` allow case is **added** beside it, and the existing `.specify` case stays |

Note for the implementer: a suite-wide `grep "xfail\|skip"` over `tests/` is **not** evidence of anything by itself — it matches a pre-existing `@pytest.mark.skipif(SH is None, …)` in `tests/test_units_infra.py` and the SDLE CLI flag `--skip-tests`, neither of which is a T04 concern. Quote what a grep actually matched, not what you expected it to match.

Tests that must remain **byte-unchanged** and passing, because they are the guardrails T04 is most likely to erode: `test_units_workitem_resolution.py::test_runtime_free_commands_is_a_closed_enumerated_set`, `::test_workitem_rebinding_happens_only_at_the_declared_sites`, `::test_the_active_context_is_written_only_by_the_declared_setters`, `::test_init_still_refuses_a_legacy_workflow_unconditionally`, `::test_validate_is_clean_in_a_healthy_repository`, `::test_no_rung_ever_returns_an_unregistered_workitem`, and every `test_units_workitem.py` case (57 of them).

---

## New tests required

One new file, `tests/test_units_speckit_binding.py`. N1–N5 are contract §10's five required tests, stated in the contract's own words.

**N1 — WorkItem A's Spec Kit output cannot be mistaken for WorkItem B's.**
Two registered WorkItems, each driven with `--workitem`, each running `feature resolve` against its own simulated Spec Kit output. Assert: two distinct `featureDirectory` values, each under its own WorkItem; A's `state.json`, `audit.md` and `specs/` tree byte-unchanged while B runs; `feature resolve` for B never selects a directory under A even when A's is newer.

**N2 — WorkItem resolution precedes Spec Kit invocation.**
(a) `feature` is absent from `RUNTIME_FREE_COMMANDS` (asserted directly against the frozenset, not by re-listing it). (b) In a repository with two WorkItems and no `--workitem`, `feature bind`, `feature resolve` and `feature capabilities` all refuse `workitem_ambiguous` (exit 1) and emit **no** env assignments and **no** capability data. (c) In a repository with zero WorkItems they refuse `workitem_required`. (d) A structural check that `phase-execution.md` places a `feature bind` line before each Spec Kit skill invocation in every phase block that has one.

**N3 — Branch alone does not define Spec Kit context.**
A repository whose Git branch matches WorkItem A while the *bound* WorkItem is B (via `--workitem`) resolves and records B's feature directory. And: a stale repository-global `.specify/feature.json` naming A's directory does not change B's `specKit.featureDirectory`, does not let B's `gate_spec` approve A's `spec.md` (D9 refuses `feature_outside_workitem`), and is never written by SDLE — proved by a recursive SHA map of `.specify/` taken before and after a full `feature bind` + `feature resolve` cycle.

**N4 — Missing required Spec Kit capability fails closed.**
Parametrised over each member of `SPECKIT_REQUIRED_CAPABILITIES` plus the "no `.specify/scripts/` at all" case: `feature bind` exits 1 with `speckit_capability_missing` (or `speckit_missing` when `.specify/` itself is absent), names the missing capability in `data.missing`, emits no `data.env`, and leaves `state.json` byte-unchanged. Then the positive control: with a stub script file containing both variable names, `feature bind` succeeds and reports the evidence path. **These tests fabricate stub `.specify/scripts/` files; they never invoke Spec Kit** (`conftest.py`'s rule 2).

**N5 — Native artifacts are not duplicated.**
After a full `feature resolve` adoption from `<root>/specs/<f>` into `workitems/<id>/specs/<f>`: exactly one `spec.md` exists anywhere under the project root; the source directory is gone; the file's SHA is unchanged across the move; and an AST/grep proof that no SDLE code path writes `spec.md`, `plan.md`, `tasks.md` or `.specify/feature.json`.

**N6 — Adoption safety.** `feature_target_exists` when the target directory already exists (source left in place, nothing overwritten); `feature_adopt_failed` on an injected `OSError` (source left in place, state unchanged); the `speckit_feature_adopted` audit entry present with `from`/`to` on the happy path; no relocation and no audit entry when the directory is already under the WorkItem.

**N7 — Discovery tiering and ambiguity.** Tier precedence exercised with candidates present in more than one tier; `feature_ambiguous` still refuses and lists when the two newest in the chosen tier share a timestamp; `feature_unresolved` when all tiers are empty; a directory under `workitems/<other>/specs/` is never a candidate.

**N8 — Migration 1.14 → 1.15.** `_mig_1_14` on a 1.14 state: `current_feature_id` gone, `specKit.featureId` carrying its value, `workflowId`/`runId` null; `featureDirectory` derived to the WorkItem path when that directory exists, to `.specify/specs/<id>` when only that exists (the in-flight case), and `None` when neither; a 1.14 state migrated through `migrate-workflow` lands at `1.15`; a state with **no** `specKit` key is readable by `status`, `gate show` and `artifact path` without a traceback.

**N9 — `resolve_artifact_path` after the bridge deletion.** `{workitem_runtime}` resolves to `workitems/<id>/.sdle` under a WorkItem and to `.workflow` under the legacy binding; `{speckit_feature_directory}` resolves and produces the documented skip reason when null; and a source-level assertion that the string `legacy_prefix` no longer appears in `scripts/sdle.py`.

**N10 — Write-fence carve-out.** `workitems/<id>/specs/…` is allowed; `workitems/index.md`, `workitems/<id>/workitem.json`, `workitems/<id>/.sdle/state.json`, `workitems/<id>/.sdle/audit.md` and `workitems/<id>/reviews/…` are still denied; `.specify/specs/…` still allowed. Added to `tests/test_hooks.py`'s existing parametrize lists where they fit, otherwise here.

**N11 — `feature bind` purity.** A recursive SHA map of the whole project root before and after `feature bind` (success and each refusal path) is identical, and its stdout/stderr contract holds. Mirrors T03's `bind_workitem` purity proof.

**N12 — §10 exit criterion.** A full 18-phase run, from `workitem create` through `complete`, with every Spec Kit generation simulated by `write_artifact` into the WorkItem-scoped feature directory, `feature bind` invoked at each generation phase and `feature resolve` after the spec phase. Then the same run for a second WorkItem in the same repository, asserting the first WorkItem's `state.json`, `audit.md` and feature directory are byte-unchanged.

**N13 — `validate`'s new check.** Fires (severity `error`, exit 3) only when a WorkItem's `specKit.featureDirectory` is non-null and outside that WorkItem's specs root; does **not** fire when it is null, so a freshly initialised repository still reports `findings == []`.

---

## Failure modes

| # | Failure mode | Guard |
|---|---|---|
| F1 | **Schema change breaks a pre-1.15 state on disk.** A reader indexes `state["current_feature_id"]` or `state["specKit"]` directly and raises `KeyError`. | One accessor `speckit_ref(state)` with defaults; no direct subscription anywhere. N8's "no `specKit` key is readable" cases. Acceptance A7. |
| F2 | **Linter goes red on the version bump.** `version_string_consistent` needs all six sites; `migration_covers_every_state_field` needs the literal `specKit` in the new action cell; the README history row must go **above** v1.14 or the first-match regex picks the wrong one. | M1 lands the template, the row and all six sites together and re-runs `lint-skill` before the milestone closes. Acceptance A2, A3. |
| F3 | **A stale repository-global `.specify/feature.json` silently points WorkItem B at WorkItem A's directory.** Spec Kit 0.15.0 keeps exactly one such slot. | `feature bind` is invoked before **every** Spec Kit invocation and re-asserts the env; D9's gate precondition refuses `feature_outside_workitem` at the choke point a hook cannot bypass; SDLE never writes the file. N3. |
| F4 | **Adoption destroys user work** — an overwrite, a partial move, or a move outside the repository. | Refuse `feature_target_exists` rather than overwrite; verify both endpoints resolve inside `project_root`; `feature_adopt_failed` on `OSError` with the source untouched; audit every move. N6. Everything is inside a Git working tree, so a completed move is recoverable with `git checkout`/`git status`. |
| F5 | **An in-flight v1.14 workflow breaks at its next gate** because its artifacts sit at `.specify/specs/<id>` and the new template points elsewhere. | `_mig_1_14` derivation step (b) records the existing `.specify/specs/<id>` path when that is where the directory actually is, so the gate keeps resolving. N8. |
| F6 | **Capability detection false-negative** — an installation supports the variable but ships no script mentioning it. | The failure direction is closed: SDLE refuses with `speckit_capability_missing` naming the probed root and the missing variable, so a human can see and correct it. It never proceeds on an assumption. Recorded as a declared, accepted residual (see Unknowns). |
| F7 | **Write-fence carve-out is too wide** and lets the model hand-edit `workitems/<id>/.sdle/state.json` or `workitems/index.md`. | The exemption is a single anchored pattern `^workitems/[^/]+/specs/` on the repo-relative path; N10 pins each still-denied path explicitly. |
| F8 | **Invariant 3 leak** — a `speckit-*` name or `/speckit.*` command becomes user-visible through the new CLI surface or a refusal message. | The new subcommands live under `feature`, not `speckit`; a grep over every added user-facing string is an acceptance criterion (A15). |
| F9 | **Suite left red across several milestones**, making failure attribution impossible. | The milestone sequence below is explicitly designed so the suite is green at the end of every milestone; M1 changes the schema **without changing a single resolved path**, so the integration tests do not move until M3, where they move together with the paths. |
| F10 | **Future-phase leakage** — T05's repository-level `.sdle/`, T06 classification, T07 flows, T09 risk gates, T10 subagents, T11 legacy removal. | The exclusion list below; an acceptance grep (A18) for `\.sdle/config`, a repository-root `.sdle/`, `policies/`, `flow`, `risk_tier`. |
| F11 | **`rtk` false green.** A bare `python -m pytest` prints `Pytest: No tests collected` and exits 0. | Every run goes through `rtk proxy`, unpiped, with the raw exit read directly and a 600000 ms timeout. Any handoff figure not produced this way is invalid. |

---

## Rollback/recovery strategy

- **Rollback point: `beb28f2`.** Proved in this context: `git diff --name-only beb28f2 HEAD` lists only three `docs/transition/` files. `git reset --hard beb28f2` restores the T03 product tree exactly. (After this plan is committed the delta is that commit plus `progress.md`; the product rollback point is unchanged.)
- **T04 has one irreversible-looking data effect: D6's relocation.** It is bounded and recoverable — the move happens inside a Git working tree, refuses rather than overwrites, is audited with `from`/`to`, and can be undone by moving the directory back. The engine change itself is otherwise pure code.
- **Per-milestone recovery.** Each milestone ends with a green suite and a `T04-checkpoint-a01-NN.md`. A failure inside a milestone is recovered by reverting that milestone's diff, not the phase.
- **Schema recovery.** A state written at 1.15 and then rolled back to a 1.14 engine will fail `migrate`'s `unknown_version` check with `Unrecognized workflow_version`, which is a refusal, not corruption. The implementer must not add a downgrade path.
- If the transition guard refuses an operation, **quote the refusal verbatim in the handoff** and design around it. Do not route around it with an interpreter or a different shell.

---

## Acceptance criteria

- [ ] **A1** `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` at the end of T04: raw exit **0**, `--collect-only -q` count equals the passed count, and `-rsxX` produces no short-summary section (zero skips, xfails, errors). Both figures quoted from runs made in the implementing context.
- [ ] **A2** `python scripts/sdle.py lint-skill` raw exit 0, **22 PASS / 0 FAIL**, reporting `15 migration rows` and `all four locations report v1.15`.
- [ ] **A3** `templates/state.json` contains `specKit` with exactly the four keys `featureId`, `featureDirectory`, `workflowId`, `runId`, contains `"workflow_version": "1.15"`, and does **not** contain `current_feature_id`.
- [ ] **A4** `grep -n 'legacy_prefix' scripts/sdle.py` returns **nothing** (NB-1 discharged), and `grep -c '\.workflow' scripts/sdle.py` is not larger than at `beb28f2`.
- [ ] **A5** `MIGRATIONS` has 15 tuples terminating in `("1.14", "1.15", _mig_1_14)`, and `CURRENT_VERSION == "1.15"`.
- [ ] **A6** `grep -rn 'current_feature_id' scripts/ .claude/ README.md docs/SDLE-Reference-Guide.md` returns only the historical `VERSION_MIGRATION` rows for 1.0→1.1 and 1.1→1.2 (which describe the past and must not be rewritten).
- [ ] **A7** A 1.14 `state.json` with no `specKit` key is readable by `status`, `gate show --gate gate_spec` and `artifact path --gate gate_spec` with no traceback and exit 0 or a contract refusal — never an uncaught exception.
- [ ] **A8** `feature bind` in a project whose `.specify/scripts/` mentions neither required variable exits **1** with reason `speckit_capability_missing`, `data.missing` naming both variables, no `data.env`, and a byte-unchanged `state.json`.
- [ ] **A9** `feature bind`, `feature resolve` and `feature capabilities` in a two-WorkItem repository with no `--workitem` all exit **1** with `workitem_ambiguous` and emit no env or capability data; `sdle.RUNTIME_FREE_COMMANDS` is byte-identical to `beb28f2`.
- [ ] **A10** Two WorkItems driven to completion in one repository end with distinct `specKit.featureDirectory` values, each under its own WorkItem, and the first WorkItem's `state.json`, `audit.md` and feature directory byte-unchanged after the second run.
- [ ] **A11** `feature resolve` adoption: exactly one `spec.md` exists under the project root afterwards, its SHA equals the pre-move SHA, the source directory is gone, and an audit entry `speckit_feature_adopted` records `from` and `to`.
- [ ] **A12** `feature resolve` refuses `feature_target_exists` without touching either directory when the target exists, and refuses `feature_adopt_failed` with the source intact on an injected `OSError`.
- [ ] **A13** A recursive SHA map of the project root is identical before and after `feature bind` on the success path and on every refusal path; `grep -rn 'feature\.json' scripts/` shows SDLE never writes it.
- [ ] **A14** Write fence: `workitems/<id>/specs/x.md` is allowed; `workitems/index.md`, `workitems/<id>/workitem.json`, `workitems/<id>/.sdle/state.json` and `workitems/<id>/.sdle/audit.md` are all still denied with the fence reason.
- [ ] **A15** No `speckit-` or `/speckit.` string appears in any user-facing message, subcommand name or help text added by T04 (verified by grep over the diff). The existing `speckit_present` / `speckit_skill_prefix` JSON keys are unchanged.
- [ ] **A16** `git diff --exit-code beb28f2 -- scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .claude/settings.json .github/ docs/dry-runs/ docs/architecture/ requirements/ .gitignore .claude/skills/sdle/modules/gate-protocol.md` returns exit 0.
- [ ] **A17** TP-003: `git diff --name-status beb28f2 -- tests/` shows **zero `D`** rows; every `M` row is justified in the handoff against the table in "Existing tests affected"; the only `A`/`??` is `tests/test_units_speckit_binding.py`; `conftest.py`'s diff is limited to the anti-contradiction clause's single permitted edit.
- [ ] **A18** No future-phase leakage: no repository-root `.sdle/` directory is created; a grep for `policies/`, `flow_id`, `risk_tier`, `classification` over the diff is empty; `.workflow/` dual-read, `migrate-workflow` and `init`'s `legacy_workflow_present` refusal are all still present and pinned by their existing tests.
- [ ] **A19** `python tools/transition/validate.py` raw exit 0.
- [ ] **A20** No T04 code path writes a non-null `specKit.workflowId` or `specKit.runId` (grep over the diff plus a test asserting both are null after a full run).
- [ ] **A21** Python 3.11 and CI are recorded as **NOT_RUN / UNKNOWN** with no outcome predicted.

---

## Milestone sequence

Designed so the suite is green at the end of **every** milestone (F9). A checkpoint file per milestone.

| M | Content | Why the suite stays green |
|---|---|---|
| **M1** | D2 + D3 + D8: `specKit` object, `current_feature_id` removed, 1.15 + `_mig_1_14` + 15th row + six version sites, `speckit_ref`, `ARTIFACT_OWNERSHIP` re-pointed, `legacy_prefix` deleted, `paths` made required. `featureDirectory` is populated by `feature resolve` **at its current location** (`.specify/specs/<id>`). | **Resolved artifact paths are byte-identical to baseline**, so no integration test moves. Only the 4 feature-field lines and the `1.14`→`1.15` assertion change. This is T04's structural proof, in the same role as T02's `Paths` seam. |
| **M2** | D4 + D5 + D7: capability detection, `feature bind`, `feature capabilities`, additive preflight keys. | Purely additive; no existing behaviour changes. |
| **M3** | D1 + D6 + D9 + D10: WorkItem-scoped feature directory, tiered discovery + adoption, gate precondition, security-review evidence — **together with** the 17 test path-rebinding lines and the one permitted `conftest.py` edit. | The paths and the tests that assert them move in the same milestone; nothing else does. |
| **M4** | D11: write-fence carve-out + `FENCE_REASONS` text, and the `test_hooks.py` additions. | Hook-local. |
| **M5** | `tests/test_units_speckit_binding.py` (N1–N13). | Test-only. |
| **M6** | D12: prompt and documentation layer. | `lint-skill` re-run after **each** document edit. |
| **M7** | Full suite, `lint-skill`, `validate.py`, the acceptance matrix, handoff. | — |

---

## Unknowns / decision requirements

**No material unresolved decision. Status recommendation is PLANNED.** The judgements that could have blocked are pinned here so the implementer does not re-open them.

1. **Which Spec Kit a user has, and what it supports — `UNKNOWN` and designed for.** The repository pins no version and installs from a moving Git HEAD. Spec Kit 0.15.0 on this host supports `SPECIFY_INIT_DIR` / `SPECIFY_FEATURE_DIRECTORY` for *consumption* but hardcodes `repo_root/specs` for *creation*; SDLE's own code meanwhile assumes `.specify/specs/`. Because none of that can be relied on, T04 (a) detects capability rather than assuming it, (b) **discovers** the native feature directory across a fixed tier order rather than hardcoding where it was created, and (c) refuses when detection fails. This is the direct answer to §10's "capability-detect; do not hardcode undocumented internals".
2. **Relocation (D6) is a deliberate, declared judgement.** §3's target tree requires Spec Kit's WorkItem artifacts to end up under `workitems/<wi>/`, and no supported env mechanism is known to redirect *creation*. The alternative — refusing when the native directory lands outside the WorkItem — fails closed but makes §10's exit criterion unreachable on at least one real Spec Kit version. Relocation is bounded, audited, non-overwriting, Git-recoverable, and preserves a single copy of the artifact. The alternative considered and rejected was a per-WorkItem `SPECIFY_INIT_DIR` with its own `.specify/` tree, which would copy engine templates into every WorkItem — precisely what §10 warns against.
3. **`workflowId` / `runId` stay null.** §10 shows them null and SDLE has no producer; §27 forbids speculative implementation. Created as the contract-mandated extension point, never written.
4. **Capability-probe false negatives are accepted.** An installation supporting a variable without shipping a script that names it will be reported unsupported and refused. That is the safe direction and is declared, not hidden.
5. **`.specify/sdle-feedback.md` and `.specify/memory/constitution.md` stay repository-level.** The constitution is genuinely repository-wide (§10 permits this explicitly); the feedback file is transient, gitignored, written and consumed inside one remediation turn, and is not a governed artifact. Neither is copied per WorkItem.
6. **`docs/dry-runs/` is deliberately not updated.** No transition phase has touched it, and T02 left 6 stale `.workflow/` references in `01-happy-path.md` under the same reasoning: the transcripts specify the *sequence*, and the integration tests — not the transcripts — pin the paths. T04's path change makes a further 17 lines stale. This is a declared residual for **T11**'s documentation sweep (§17), recorded so the verifier does not read it as an omission.
7. **`design/`, `reviews/` and `clarifications/` stay repository-level in T04.** They are SDLE-native, not Spec Kit-owned; §10 names none of them; TP-002 forbids changing two architectural axes in one phase. `gate_design`'s `design/app/app-design.md` is therefore still a single repository-level path shared by all WorkItems — a real residual, but not a Spec Kit one, and not covered by any §10 test. Recorded as a finding for the orchestrator to assign; **T04 does not fix it.**
8. **Hygiene items T03's verifier left unowned — explicit decision.** `ACTIVE_CONTEXT_SETTERS` (T03-4), `cmd_workitem_use` error-hardening (T03-5) and its `workitem_required` name collision (T03-6): **T04 adopts none of them.** They are not incidental to any edit in this plan — T04 touches neither `cmd_workitem_use` nor the active-context writers — and adopting them would add diff noise to a phase that already carries a schema change. They remain open for a later phase.
9. **Python 3.11 and CI: `NOT_RUN` / `UNKNOWN`.** The branch is local-only; CI pins 3.11 on `ubuntu-latest` and `windows-latest`; this host has no 3.11 interpreter. Predict no outcome. T04 is standard-library-only and therefore 3.11-safe by construction, so a later CI failure could not invalidate the design — but it must not be claimed green.
10. **Every quantitative claim in prior plans is unverified until re-derived.** `T00-plan.md`'s "21 top-level subcommands" is known wrong. Re-derive anything you intend to cite.

---

## Scope exclusions

The following must **not** leak into T04. If the implementer finds an edit that seems to require one, that is a plan defect to declare, not a licence to widen.

| Excluded | Owner | Why it is out |
|---|---|---|
| Repository-level `.sdle/` (`config/`, `policies/`, `templates/`, `baseline.*`, `implementation-state/`) and the JSON-vs-YAML policy-format decision | **T05** (§11) | T04 creates no repository-root `.sdle/`. A18 greps for it. |
| Requirements Quality Gate, structured classification, hybrid risk, governed-artifact review/validation | T06 (§12) | — |
| Declarative flow selection; replacing the fixed 18-phase sequence | T07 (§13) | T04's exit criterion is explicitly the **current** 18-phase flow. |
| Brownfield discovery and greenfield/brownfield convergence | T08 (§14) | — |
| Risk-adaptive gate policy, hard risk floors | T09 (§15) | — |
| Progressive Claude skills and specialist subagents | T10 (§16) | Invariant 8 stands: nothing holding a gate is delegated. |
| Removing the legacy `.workflow/` dual-read rung, `migrate-workflow`, or `init`'s unconditional `legacy_workflow_present` refusal | **T11** (§17) | All three must still work at the end of T04 and are pinned by existing tests. |
| T03-1 (the declared `branch_guard` fail-open window between the two confirmation steps) | T11 | Needs a `pending_branch_ack` state key. T04's schema change is for `specKit` only and must not smuggle this in. |
| NB-2 (the `legacy_workflow_present` message never naming archiving `.workflow/`), NB-4 (the post-commit `workitem.json` write outside the commit window), NB-5 (migration crash coverage of the manifest/completion copies) | T11 | — |
| T03-7, T03-8, T03-10 (edge-case ordering, the acceptance audited for a refused action, the SKILL.md branch-mismatch wording) | unassigned / docs | Not T04's. |
| T03-4, T03-5, T03-6 (`ACTIVE_CONTEXT_SETTERS`, `cmd_workitem_use` hardening and its reason-name collision) | unassigned | Explicitly **not adopted** by T04 — see Unknowns §8. |
| NB-7 (`6e8af8c`'s stray word in the `write_atomic` comment) and `.claude/settings.local.json` | out of scope | — |
| Moving `design/`, `reviews/`, `clarifications/` under `workitems/` | unassigned | See Unknowns §7. |
| Updating `docs/dry-runs/` | T11 documentation sweep | See Unknowns §6. |
