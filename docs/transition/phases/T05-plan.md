# T05 Plan

**Phase:** T05 — Introduce Repository-Level `.sdle/` Configuration Boundary (contract §11)
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED

Precondition HEAD at planning time: **`44572f7`** on `transition/workitem-v1`.
Rollback point for T05: **`7b054ee`** (proved below).
Product baseline: `f8fdaa0`.

---

## Objective

Separate repository-wide SDLE configuration from WorkItem runtime state, per contract §11:

1. Create the repository-level boundary `.sdle/` holding `config.*`, `policies/`, `templates/`, `baseline.*` and `implementation-state/`, owned by the *repository* and derived from `project_root` alone.
2. Keep WorkItem `.sdle/` owning lifecycle state, execution, audit, evidence and WorkItem-specific manifests, derived from the bound `workitem`.
3. Make that split **structural and enforced**, not merely documented: one `Paths` seam, one validation predicate, and a bidirectional leak detector in `sdle validate`.
4. Record the **policy-format decision** — JSON — explicitly, before any executable policy exists.
5. Change **no lifecycle behaviour whatsoever**. §11: *"At T05, current 18-phase behavior still remains authoritative."*

Contract §11 exit criterion: *repository-global configuration exists independently from WorkItem runtime state, with no lifecycle behavior change.*

T05 is structurally unusual: it is almost entirely scaffolding, and its correctness proof is largely **the absence of change**. A green suite alone is weak evidence — new scaffolding that nothing reads would also leave it green. This plan therefore carries four independent *positive* proofs (A11, A12, A13, A20) that the boundary is real, reachable and inert with respect to the 18-phase flow, and a *negative* proof set (A5–A9, A21) that nothing else moved.

### The policy-format decision — MADE, do not re-open

**Decision: JSON.** The rationale, recorded verbatim as the user gave it:

> preserve the zero-dependency stdlib-only core exactly as it is today, so `sdle.py` stays runnable anywhere Python 3.11+ exists with no install step.

This is §11's own recommended default ("JSON for machine-owned executable policy/state if preserving stdlib-only is a priority"). §11 also states: *"Do not implement a home-grown YAML parser."* T05 adds **no dependency** and **no YAML parser**. If a later phase wants YAML it may revisit with real authoring evidence and an explicit dependency acceptance; T05 does not, and the implementer must not.

---

## Repository evidence

Every figure below was produced by a command run in **this** planning context, or read from the file named. Nothing is copied from a prior phase's narrative. Prior plans' quantitative claims are treated as unverified (`T00-plan.md`'s "21 top-level subcommands" is known wrong).

| Claim | Class | Evidence |
|---|---|---|
| HEAD is `44572f7` ("Refresh the cold-start note for T05"); working tree carries only `M .claude/settings.local.json` | OBSERVED | `git log --oneline -8`, `git status --porcelain`, `git rev-parse HEAD` |
| `git diff --name-status 7b054ee HEAD` = **one row**, `M docs/transition/RESUME.md` — so the product rollback point for T05 is **`7b054ee`** | OBSERVED | `rtk proxy "git diff --name-status 7b054ee HEAD"` |
| `python tools/transition/validate.py` prints `TRANSITION_VALID: complete=5/12 next=T05`, raw exit **0** | OBSERVED | direct run, `RAW_EXIT=0` |
| `lint-skill` raw exit **0**, **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 15 migration rows`, `all four locations report v1.15` | OBSERVED | `rtk proxy "python scripts/sdle.py lint-skill"` |
| Host interpreter is **Python 3.13.0** | OBSERVED | `python --version` |
| Full suite at `44572f7`: **`500 passed in 1049.81s (0:17:29)`, RAW EXIT 0**; `--collect-only -q` = **500 tests collected**, so collected == passed; a grep for `short test summary` over the captured run matched **0** lines, so zero skips, xfails and errors | OBSERVED | see "Baseline suite run" below |
| **No repository-root `.sdle/` exists** anywhere in the tree today | OBSERVED | `ls -a` at root lists no `.sdle`; `ls -d .sdle` → "No such file or directory" |
| `.sdle/` is **not** gitignored: `git check-ignore -v .sdle/config.json` and `.sdle/policies/x.json` both exit **1** | OBSERVED | direct runs |
| Root `.gitignore` is 10 lines; its only `workitems` entries are `workitems/*/.sdle/lock` and `workitems/.active-context.json` | OBSERVED | `cat .gitignore` |
| `.gitattributes` is `* text=auto eol=lf` plus `*.ps1 text eol=crlf` | OBSERVED | `cat .gitattributes` |
| `scripts/sdle.py` imports exactly 14 modules, **all in `sys.stdlib_module_names`** (`__future__ argparse dataclasses datetime hashlib json os pathlib re shutil subprocess sys tempfile time`) | OBSERVED | AST scan run in this context |
| No `pyproject.toml`, `setup.py`, `setup.cfg` or `requirements.txt` at the repository root; a recursive grep for `import yaml`, `yaml.safe_load`, `ruamel` over `scripts/ .claude/ tests/ tools/` returns **no matches** (grep exit 1) | OBSERVED | `ls`, `rtk proxy "grep -rn …"` |
| `CLAUDE.md:15` and `scripts/README.md:8` both state the core is "standard library only" | OBSERVED | grep |
| CI (`.github/workflows/ci.yml`) pins `python-version: "3.11"` on `ubuntu-latest` and `windows-latest` | OBSERVED | `cat .github/workflows/ci.yml` |
| CI has never run on this branch; no 3.11 interpreter on this host | UNKNOWN / NOT_RUN | branch is local-only per `RESUME.md`; no CI outcome observed in this context. **No outcome predicted.** |
| `Paths.runtime` = `legacy_workflow if workitem is None else workitem_root / ".sdle"`; every runtime member (`state_file`, `audit_file`, `lock_file`, `execution_file`, `manifest_file`, `completion_file`, `evidence_dir`) derives from `runtime` | OBSERVED | `scripts/sdle.py`, anchor `@dataclass` / `class Paths:` |
| `PROJECT_ROOT_MARKERS` is a 3-tuple: `("workitems","index.md")`, `(".workflow","state.json")`, `(".git",)`; `discover_project_root` walks `(start, *start.parents)` and returns the **nearest** ancestor carrying any marker | OBSERVED | anchor `PROJECT_ROOT_MARKERS = (` |
| `RUNTIME_FREE_COMMANDS` is `frozenset({"lint-skill","sha","constants","workitem","migrate-workflow","validate"})` — 6 members | OBSERVED | anchor `RUNTIME_FREE_COMMANDS = frozenset({` |
| `main()` binds a WorkItem for every command **not** in that set: `if args.command not in RUNTIME_FREE_COMMANDS: paths = bind_workitem(...)` | OBSERVED | anchor `if args.command not in RUNTIME_FREE_COMMANDS:` |
| `SDLE_OWNED_PREFIXES` is `(".workflow/","workitems/",".specify/","design/","reviews/","clarifications/","guidance/","requirements/")` and is consumed **only** by `cmd_implement_preflight`'s dirty-tree filter | OBSERVED | anchor `SDLE_OWNED_PREFIXES = (`; the only other mention is the comment in `cmd_manifest_build` explaining why the manifest does **not** widen to it |
| `.claude/hooks/hooks.py` fences `FENCED = (".workflow", "workitems", "requirements", "guidance")` via `in_dir(path, name)` = `f"/{name}/" in path or path.startswith(f"{name}/")`. **`in_dir` cannot distinguish a repository-root `.sdle/` from `workitems/<id>/.sdle/`** — both contain the segment `/.sdle/` | OBSERVED | read `.claude/hooks/hooks.py` in full |
| The one fence carve-out is `SPECS_CARVE_OUT = re.compile(r"(?:^|/)workitems/[^/]+/specs/")`, matched against `relative(path)` with **no path normalisation** — T04 finding N-3 | OBSERVED | `.claude/hooks/hooks.py`, anchor `SPECS_CARVE_OUT` |
| `scripts/sdle.py` contains exactly **5** occurrences of the string `.sdle`, none of them a repository-root path | OBSERVED | `rtk proxy "grep -n '\.sdle' scripts/sdle.py"` → lines 138, 1162, 1169, 1620, 2930 |
| `scripts/sdle.py` raises **39 distinct `Refused(` reason names**; **none** contains the substring `config` | OBSERVED | AST/regex scan run in this context |
| The suite contains exactly **four** closed-set assertions over engine constants: `RUNTIME_FREE_COMMANDS`, the `dataclass_replace(paths, workitem=…)` call sites, the active-context writers, and `ACTIVE_CONTEXT_SETTERS` — all in `tests/test_units_workitem_resolution.py` | OBSERVED | regex scan over `tests/*.py` run in this context |
| `test_runtime_free_commands_is_a_closed_enumerated_set` asserts the frozenset **literally**, so adding a runtime-free command requires editing it | OBSERVED | read the test body |
| `test_workitem_rebinding_happens_only_at_the_declared_sites` asserts the call-site set is exactly `{bind_workitem, branch_candidates, candidate_evidence, collect_validation_findings, _validate_runtime_state, cmd_migrate_workflow}` | OBSERVED | read the test body |
| `collect_validation_findings` already calls `dataclass_replace(paths, workitem=value)` (its branch-mismatch loop), so a new check placed **inside it** adds no new call site | OBSERVED | read `collect_validation_findings` in full |
| `_validate_runtime_state` returns `[]` early when `bound.state_file` is not a file — so it cannot host a check for a WorkItem `.sdle/` that holds config artefacts but no state | OBSERVED | read the function |
| `test_validate_is_clean_in_a_healthy_repository` asserts `findings == []` and `errors == 0` for a git-initialised `bare_project` with one WorkItem and `init` run | OBSERVED | read the test body |
| **No test pins the CLI subcommand set.** The only `--help` assertions are `test_units_cli.py::test_help_exits_zero` (asserts `"sdle" in stdout`) and the `test_units_infra.py` launcher-resolution class | OBSERVED | grep over `tests/` for `add_parser`, `--help`, `format_help` |
| No test references `SDLE_OWNED_PREFIXES` or `PROJECT_ROOT_MARKERS` | OBSERVED | grep over `tests/` |
| `tests/conftest.py::bare_project` copies `REPO_ROOT/scripts`, `REPO_ROOT/.claude/hooks` and `.claude/settings.json` into the scratch root — it does **not** copy a repository-root `.sdle/`, so creating one here cannot leak into fixtures | OBSERVED | read `conftest.py` |
| `run_happy_path(project)` and `EXPECTED_TRAVERSAL` are importable across test files — `tests/test_units_workitem_runtime.py:27` already does `from test_integration_01_happy_path import EXPECTED_TRAVERSAL, run_happy_path` | OBSERVED | grep |
| `test_units_infra.py::test_a_real_launcher_run_succeeds_here` is the only test that runs the engine with `cwd=REPO_ROOT`; it invokes `constants`, which is runtime-free | OBSERVED | read the test |
| `tools/transition/validate.py` performs **no** directory walk or glob — it hashes the named control-plane manifest entries and parses `progress.md` | OBSERVED | grep for `iterdir`/`glob`/`rglob`/`walk` returns nothing |
| §19 lists `.sdle/baseline.*` and `.sdle/policies/*` under **"Must eventually be versioned"** | OBSERVED | `docs/transition/transition.md:1718-1719` |
| §11's `implementation-state/` appears **only** in the two directory diagrams (`transition.md:259`, `:1045`) and one ownership bullet ("implementation-transition metadata", `:1056`). No schema, producer or consumer is defined anywhere in the contract | OBSERVED / UNKNOWN | `rtk proxy "grep -n 'implementation-state\|implementation-transition' docs/transition/transition.md"` |
| §22's "Later governance capabilities" lists `sdle baseline validate` but **no** `sdle config` command; the CLI shape for repository configuration is unconstrained by the contract | OBSERVED | `transition.md:1832-1843` |
| **The F1 `ENVIRONMENT_FLAKE` procedure is VOID.** `write_atomic` carries a bounded `os.replace` retry (`for delay in (0.01, 0.02, 0.04, 0.08)`) added by `6e8af8c`; a permanent `PermissionError` still raises | OBSERVED | read `def write_atomic` |
| Open findings inherited: T04 N-2, N-3, N-4, N-6, N-7; T03-1, T03-4/5/6, T03-7/8, T03-10; T02 NB-2/4/5 | OBSERVED | `docs/transition/RESUME.md`, "Open findings carried forward" |

### Baseline suite run

Run in **this** planning context at HEAD `44572f7`, through `rtk proxy`, unpiped, raw exit read directly, backgrounded without redirection (the guard refuses a backgrounded run that redirects with `>`):

```
rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"
500 passed in 1049.81s (0:17:29)
RAW_EXIT=0
```

`rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only"` → **`500 tests collected in 0.53s`**, so collected == passed. A `grep -c "short test summary"` over the captured run returned **0**, so the suite has zero skips, zero xfails and zero errors.

**The implementer must re-derive this figure at the start of the phase rather than copying it**, and must treat any failure as a **presumed real regression** — the F1 flake procedure is void and must not be re-introduced.

---

## Behavioral delta

### Deliberate changes

**D1 — A `Paths` seam for the repository configuration boundary.**
Add read-only properties to `@dataclass class Paths`, placed after `speckit_specs_relative`:

| Property | Value |
|---|---|
| `config_root` | `project_root / ".sdle"` |
| `config_root_relative` | `".sdle"` (repo-relative POSIX) |
| `config_file` | `config_root / "config.json"` |
| `policies_dir` | `config_root / "policies"` |
| `shared_templates_dir` | `config_root / "templates"` |
| `baseline_file` | `config_root / "baseline.json"` |
| `implementation_state_dir` | `config_root / "implementation-state"` |

**The boundary *is* this derivation.** Every one of the seven derives from `project_root` alone and **must not reference `self.workitem`, `self.workitem_root` or `self.runtime`**. That is the mechanical statement of §11's ownership split, and N1 asserts it directly: replacing `workitem` changes every runtime member and changes none of these.

`shared_templates_dir` is deliberately **not** named `templates_dir` — `skill_root/templates/state.json` already exists and a bare `templates_dir` would read as that. `baseline_file` names the §11 `baseline.*` slot; **the file itself is not created by T05** (see D7).

**D2 — `.sdle/config.json` becomes a project-root marker.**
Append `(".sdle", "config.json")` to `PROJECT_ROOT_MARKERS` as the **last** entry. Rationale: `workitems/index.md` — the WorkItem boundary's own marker — is already first in that tuple; omitting the configuration boundary's marker would make the two boundaries asymmetric and would let `config init` write `.sdle/` into a subdirectory when Claude is launched from one.

This is **provably a no-op for every repository that existed before T05**, because no repository contained `.sdle/config.json`. It can only ever make the upward walk stop at a *lower* level, and only in a tree that has a `.sdle/config.json` there. Pinned by N12, including the control case (a tree with no `.sdle/config.json` resolves exactly as before) and the nearest-ancestor case.

**D3 — The repository configuration model.**
One default map and one reader:

```
REPO_CONFIG_DEFAULTS = {"configVersion": "1", "policyFormat": "json"}
SUPPORTED_CONFIG_VERSIONS = ("1",)
SUPPORTED_POLICY_FORMATS = ("json",)
```

`read_repo_config(paths) -> dict` returns `REPO_CONFIG_DEFAULTS` verbatim when `config_file` is absent, and the parsed document merged over the defaults when present. It never writes.

`configVersion` is a **different version namespace from `workflow_version`**. It is not a state field, it gets **no** `VERSION_MIGRATION` row, and `CURRENT_VERSION` stays `"1.15"`. The implementer must not touch `templates/state.json`, the migration chain, or any version string. A6 and A15 pin this.

`policyFormat` is where the JSON decision becomes operative: `"json"` is the only supported value, and anything else — including `"yaml"` — is a refusal whose message names §11's requirement that a YAML dependency be *explicitly accepted* first. This makes the recorded decision an enforced fact rather than a dead one.

**D4 — One validation predicate, two consumers (invariant 7).**
`repo_config_findings(paths) -> list[dict]` is the **single** implementation of "is this repository's configuration boundary sound". It returns `_finding(...)` dicts in the existing shape (anchor `def _finding(`) and is consumed by:

- `cmd_config_show`, which **refuses** when any returned finding has severity `VALIDATE_ERROR`; and
- `collect_validation_findings`, which appends them.

There must be exactly one function that decides this. Two code paths that could disagree about whether a configuration is valid would be an invariant-7 violation and a plan defect.

Checks it performs:

| `check` | Severity | Fires when |
|---|---|---|
| `config_malformed` | error | `config.json` exists but is unreadable, is not a JSON **object**, carries a `configVersion` outside `SUPPORTED_CONFIG_VERSIONS`, or carries a `policyFormat` outside `SUPPORTED_POLICY_FORMATS` |
| `config_root_inside_workitem` | error | `project_root.name == "workitems"` or `project_root.parent.name == "workitems"` — the resolved repository root is itself the registry directory or a WorkItem directory |
| `lifecycle_state_in_repository_config` | error | any **WorkItem runtime member name** exists directly under `config_root` |
| `repository_config_in_workitem` | error | any **repository configuration member name** exists under some `workitems/<id>/.sdle/` |

**The last two are the leak detector, and they are this plan's answer to "what would actually catch a lifecycle rule leaking into `.sdle/` early".** The runtime member list must be **derived, never re-listed** (invariant 7):

```
def workitem_runtime_member_names(paths) -> tuple[str, ...]:
    p = dataclass_replace(paths, workitem="_probe")
    return tuple(x.name for x in (p.state_file, p.audit_file, p.execution_file,
                                  p.lock_file, p.evidence_dir, p.manifest_file,
                                  p.completion_file))
```

**Binding constraint.** `test_workitem_rebinding_happens_only_at_the_declared_sites` asserts a closed set of function names containing `dataclass_replace(paths, workitem=…)`. The derivation above and the `repository_config_in_workitem` scan **must be written inside `collect_validation_findings`**, which is already a member of that set — or must receive an already-bound `Paths` from it. Introducing a new function that rebinds would force a second existing-test edit; that is a plan violation, not a licence to widen. If the implementer believes it is unavoidable, declare it as a divergence with the reason and the TP-003 category.

`repository_config_in_workitem` cannot live in `_validate_runtime_state`: that function returns `[]` early when the WorkItem has no `state.json`, and a WorkItem carrying a stray `config.json` but no state is exactly the case to catch.

**D5 — Two new subcommands under a new `config` group.**

- `sdle config init` — creates `.sdle/config.json` (via the existing `write_atomic`) plus `policies/`, `templates/` and `implementation-state/`, each carrying an empty `.gitkeep` so Git can version an otherwise-empty directory (§19). Idempotent for directories: an existing subdirectory with content is left untouched. **Refuses `config_exists`** when `config.json` already exists — it never overwrites. **Refuses `config_root_inside_workitem`** when D4's predicate says the resolved root is misplaced. It **never deletes**, never writes outside `config_root`, and never creates `baseline.json`.
- `sdle config show` — pure reader. Emits `{"root": ".sdle", "present": <bool>, "config": {…effective…}, "defaults_applied": [...], "members": {…repo-relative POSIX paths…}}`. Refuses `config_malformed` / `config_root_inside_workitem` per D4. **In a repository with no `.sdle/` it exits 0 reporting `present: false` and the defaults, and creates nothing** — that is what makes T05 a no-op for every existing repository.

Three new refusal reasons: `config_exists`, `config_malformed`, `config_root_inside_workitem`. None collides with the 39 existing ones (evidence table). No existing refusal reason is removed or renamed. Both handlers follow the existing `cmd_workitem_list` shape: `emit(...)` then `return EXIT_OK`.

**D6 — `config` joins `RUNTIME_FREE_COMMANDS`.**
This is contract §11's exit criterion in executable form: repository configuration must resolve **independently of** WorkItem runtime state, so it must not be gated on `bind_workitem`. Consequence, declared up front: `test_runtime_free_commands_is_a_closed_enumerated_set` gains the literal `"config"`. **This is the only existing-test edit T05 authorises** (TP-003 category 2 — a closed set genuinely gains a member). See the anti-contradiction clause.

**D7 — The repository's own `.sdle/`, versioned.**
This repository gains a checked-in `.sdle/` produced by running `config init` here: `config.json`, and `policies/`, `templates/`, `implementation-state/` each with a `.gitkeep`.

**Versioned, not gitignored — and `.gitignore` needs zero edits**, because `git check-ignore -v .sdle/config.json` already exits 1 (evidence table). Reasons: §19 explicitly places `.sdle/baseline.*` and `.sdle/policies/*` under "must eventually be versioned"; global configuration and shared templates are team-shared engineering evidence, not ephemera; and §19's "may remain local/ignored" is restricted to "only data that is truly ephemeral".

**`implementation-state/` is versioned too, deliberately.** The contract defines no schema, producer or consumer for it (evidence table, classed UNKNOWN). T05 therefore creates it as an **empty, documented slot with no writer**, and versions it by §19's default rather than pre-emptively declaring it ephemeral. §27 forbids speculative implementation, so T05 defines no content for it. A later phase that puts a genuine cache there may revisit the ignore decision with real evidence.

**`baseline.json` is named but not created.** §11 calls it the "future baseline" and §14 gives it a schema only T08 can produce. The *slot* exists (`Paths.baseline_file`, ownership documented, `validate` policing it); the *file* does not. Creating an empty or null baseline would be speculative content.

**D8 — Documentation and the ADR.**

- New `docs/architecture/ADR-002-repository-configuration-boundary.md`, following ADR-001's shape: the ownership split, the JSON decision with the user's verbatim rationale, what was rejected (YAML plus a dependency; a home-grown YAML parser, which §11 forbids), and the explicit statement that no lifecycle rule moved. The ADR is the *historical record of the decision*; `.sdle/config.json`'s `policyFormat` is the *operative declaration the engine enforces*. That is the established ADR role in this repository (`ADR-001-deterministic-core.md`), not an invariant-7 fork.
- `README.md` "File Layout → In your target project" gains the repository `.sdle/` block above `workitems/`.
- `docs/SDLE-Reference-Guide.md` §4 gains an un-numbered `### Repository configuration boundary` subsection (matching the existing `### WorkItem identity` / `### Execution identity` / `### validate` pattern) carrying the two-column ownership table.
- `CLAUDE.md` gains one sentence after the existing "Runtime state is WorkItem-scoped" paragraph.
- `README.md` "Commands" gains the two `config` rows.

**No version-history row and no version bump.** T05 changes no state field, no phase, no gate and no skill file, so all four version locations stay at v1.15. Keeping the version still is itself evidence that no lifecycle rule moved.

### Preserved invariants

Everything below must be **byte-identical or behaviourally identical** at the end of T05, and each is pinned by an acceptance criterion.

- **The whole prompt/skill layer is untouched.** `.claude/skills/` (including `SKILL.md`, all `modules/`, `templates/state.json`, and the control-plane `apply-sdle-transition` skill), `.claude/commands/`, `.claude/hooks/`, `.claude/settings.json` and `.claude/agents/` are byte-identical to `7b054ee`. T05 introduces no constant, no phase, no gate, no version and no prompt rule. (A5)
- **No schema change.** `CURRENT_VERSION == "1.15"`, 15 `VERSION_MIGRATION` rows, `templates/state.json` byte-identical, `lint-skill` 22/22 reporting `15 migration rows` and `all four locations report v1.15`. (A6, A3)
- **The write fence is not touched.** `.claude/hooks/hooks.py` byte-identical; `FENCED`, `SPECS_CARVE_OUT` and `FENCE_REASONS` unchanged. Repository `.sdle/` is deliberately **not** fenced — see Unknowns §3.
- **`SDLE_OWNED_PREFIXES` is not touched.** See Unknowns §4 — a deliberate decision, not an oversight.
- **The resolution ladder never guesses.** `bind_workitem`, `resolve_decision`, `branch_candidates`, `candidate_evidence`, the behaviour of every pre-existing `RUNTIME_FREE_COMMANDS` member, `workitem resolve`, `workitem use` and the persisted active context are unchanged. `>1 plausible -> ASK` holds; refusals still list candidates. (A7, A16)
- **The legacy `.workflow/` dual-read rung keeps working**, `migrate-workflow` still never mutates `.workflow/`, and `init` still refuses `legacy_workflow_present` unconditionally. **T11**, not T05, removes any of this. (A16)
- **`write_atomic`, `append_audit`, `save_state`, `read_state`, the audit hash chain and the single-writer invariant (6)** are byte-identical. `config init` is the only new writer; it writes **only** inside `config_root`, never `state.json`, never `audit.md`, and appends no audit entry. (A7, A13)
- **Invariant 3** — no `speckit-*` name and no `/speckit.*` command appears in any string T05 adds. (A18)
- **Invariant 8** — gates stay in the parent session. T05 adds no subagent, no delegation and nothing that holds a gate.
- **Invariant 7** — one source of truth per fact. A configuration boundary is precisely where a second home for an existing fact appears, so: T05 moves **no** existing fact into `.sdle/`. `rate_limits`, `approvals`, `project_name`, `verbose`, the phase/gate tables and every SKILL.md constant stay exactly where they are. `config.json` contains only two facts, both new. (A17)
- **T04's Spec Kit binding** is untouched: `speckit_specs_root`, `feature bind`, `feature resolve`, `feature capabilities`, the gate precondition and `specKit` state are unchanged.

---

## Files expected to change

**Engine**

- `scripts/sdle.py` — `Paths` (+7 properties, anchor: immediately after `def speckit_specs_relative`); `PROJECT_ROOT_MARKERS` (+1 tuple, anchor `PROJECT_ROOT_MARKERS = (`); `REPO_CONFIG_DEFAULTS` / `SUPPORTED_CONFIG_VERSIONS` / `SUPPORTED_POLICY_FORMATS` / `read_repo_config` / `repo_config_findings` / `workitem_runtime_member_names` (new, placed beside the existing validate helpers near `def _finding(`); `RUNTIME_FREE_COMMANDS` (+`"config"`); `collect_validation_findings` (+ the config findings and the reverse-direction scan); new `cmd_config_init`, `cmd_config_show`; a new `config` parser group modelled on `subparsers.add_parser("workitem", help="WorkItem identity.")`.

**Repository configuration instance (new, versioned)**

- `.sdle/config.json`, `.sdle/policies/.gitkeep`, `.sdle/templates/.gitkeep`, `.sdle/implementation-state/.gitkeep`

**Docs**

- new `docs/architecture/ADR-002-repository-configuration-boundary.md`
- `README.md`, `docs/SDLE-Reference-Guide.md`, `CLAUDE.md`

**Tests**

- new `tests/test_units_repo_config.py`
- `tests/test_units_workitem_resolution.py` — **exactly one function** (see the anti-contradiction clause)

**Control plane**

- `docs/transition/phases/T05-plan.md` (this file), `docs/transition/progress.md`, `docs/transition/phases/T05-handoff-a01.md`, `docs/transition/phases/T05-checkpoint-a01-NN.md`

**Must not change** — verify with `git diff --exit-code 7b054ee -- <paths>`:

`.claude/skills/`, `.claude/hooks/`, `.claude/commands/`, `.claude/settings.json`, `.claude/agents/`, `.github/`, `scripts/sdle.sh`, `scripts/sdle.ps1`, `scripts/README.md`, `.gitignore`, `.gitattributes`, `requirements/`, `docs/dry-runs/`, `docs/architecture/ADR-001-deterministic-core.md`, `tools/`, and everything under `docs/transition/` except this plan, `progress.md` and T05's own handoff/checkpoints.

`.gitignore` genuinely needs no edit: `git check-ignore -v .sdle/config.json` exits 1 today (evidence table).

`.claude/settings.local.json` is the user's Claude Code permission allowlist, is already modified in the working tree, and is **out of scope** — do not stage, revert or edit it.

### Anti-contradiction clause (binding)

This plan permits **exactly one** change to any existing test file: in `tests/test_units_workitem_resolution.py`, adding the literal `"config"` to the frozenset asserted by `test_runtime_free_commands_is_a_closed_enumerated_set`. **No other change to any existing test file is authorised** — not elsewhere in that file, not in `tests/conftest.py`, not in any integration test.

**`tests/conftest.py` must not change at all.** No fixture may be added, removed, renamed or re-scoped; `bare_project`, `project`, `started`, `git_project` and `isolated_git_identity` keep their exact current bodies. Every new helper belongs in `tests/test_units_repo_config.py`, which may compute `project.root / ".sdle"` locally.

If the implementer believes a further test edit is unavoidable, that is a **plan defect**: record it as a declared divergence in the handoff with the reason and the TP-003 category. Do not silently widen the edit. In particular the three closed-set assertions other than `RUNTIME_FREE_COMMANDS` (`sites`, `writers`, `ACTIVE_CONTEXT_SETTERS`) must remain byte-identical — D4's binding constraint and D5's "never writes an active context" exist to make that achievable.

Nothing in this plan asserts an exact CLI subcommand set, an exact directory listing of the repository root, or an exact `Paths` property set.

---

## Existing tests affected

| File | Scope | TP-003 category | Nature |
|---|---|---|---|
| `tests/test_units_workitem_resolution.py` | `test_runtime_free_commands_is_a_closed_enumerated_set`, one literal added | 2 — genuinely superseded | D6 puts `config` in `RUNTIME_FREE_COMMANDS`, which is the executable form of §11's exit criterion. The assertion remains a closed set and is **not** weakened. |

**That is the entire expected `M` set. Zero `D`, zero `R`, one `A` (`tests/test_units_repo_config.py`).** `git diff --name-status 7b054ee -- tests/` producing anything else is a signal to stop and re-read this plan, not to proceed.

No test may be weakened, skipped, xfailed or deleted.

Note for the implementer: a suite-wide `grep "skip\|xfail"` over `tests/` is **not** evidence of anything by itself — it matches a pre-existing `@pytest.mark.skipif(SH is None, …)` in `tests/test_units_infra.py`, the SDLE CLI flag `--skip-tests`, and the `skip` subcommand's own test names. Quote what a grep actually matched, not what you expected it to match (T03 process lesson).

Tests that must remain **byte-unchanged and passing**, because they are the guardrails T05 is most likely to erode:

- `test_units_workitem_resolution.py::test_workitem_rebinding_happens_only_at_the_declared_sites`
- `test_units_workitem_resolution.py::test_the_active_context_is_written_only_by_the_declared_setters`
- `test_units_workitem_resolution.py::test_validate_is_clean_in_a_healthy_repository`
- `test_units_workitem_resolution.py::test_init_still_refuses_a_legacy_workflow_unconditionally`
- `test_units_workitem_resolution.py::test_no_rung_ever_returns_an_unregistered_workitem`
- `test_units_workitem_resolution.py::test_the_nearest_marker_ancestor_wins`, `::test_the_workitem_registry_is_a_project_root_marker`, `::test_the_legacy_runtime_is_a_project_root_marker`, `::test_discover_never_invents_a_root_inside_a_marker_free_tree`, `::test_resolve_paths_falls_back_to_the_launch_directory`
- every `test_units_workitem.py` case, every `test_hooks.py` case, and all nine integration transcripts

---

## New tests required

One new file, `tests/test_units_repo_config.py`.

**N1 — The boundary is structural.** For `Paths` instances differing only in `workitem` (`None`, `"a"`, `"b"`): all seven D1 members are **equal** across the three and all equal `project_root/.sdle/...`; while `runtime`, `state_file`, `audit_file`, `execution_file`, `lock_file`, `evidence_dir`, `manifest_file` and `completion_file` **all differ** between `"a"` and `"b"`. Also: `config_root` is never inside `workitems/`, and `runtime` is never inside `config_root`, for all three. Plus a source-level assertion (AST over the `Paths` class body) that no D1 property references `workitem`, `workitem_root` or `runtime`.

**N2 — `config init`.** In a repository with zero WorkItems: exit 0; creates exactly `config.json` plus the three directories each with `.gitkeep`; does **not** create `baseline.json`; does **not** create `workitems/`, `.workflow/`, any `state.json` or any audit entry; `config.json` parses to exactly `{"configVersion": "1", "policyFormat": "json"}`. Re-running refuses `config_exists` (exit 1) and leaves a recursive SHA map of `.sdle/` unchanged. A pre-existing `policies/` directory holding a file survives `config init` untouched.

**N3 — `config init` refuses a misplaced root.** With `--project-root` pointing at `<repo>/workitems` and at `<repo>/workitems/<id>`, both `config init` and `config show` refuse `config_root_inside_workitem` (exit 1) and create nothing. `sdle validate` reports the same `check` name as an error.

**N4 — Repository configuration resolves with no WorkItem — §11's exit criterion.** In one repository with **two** registered WorkItems and no `--workitem`: `config show` and `config init` both exit **0**, while `state get` in the same repository refuses `workitem_ambiguous` (exit 1). Repeated for zero WorkItems (where the runtime command refuses `workitem_required`) and for one. Plus `"config" in sdle.RUNTIME_FREE_COMMANDS`.

**N5 — Defaults when the boundary is absent.** In a repository with no `.sdle/`: `config show` exits 0, `present is False`, `config["configVersion"] == "1"`, `config["policyFormat"] == "json"`, `defaults_applied` names both keys, and a recursive SHA map of the whole project root is **byte-identical before and after** — a pure reader creates nothing.

**N6 — Malformed configuration fails closed, once.** Parametrised over: not JSON; a JSON array; a JSON scalar; `configVersion: "2"`; `configVersion: 1` (int); `policyFormat` absent; `policyFormat: "yaml"`; `policyFormat: "toml"`. For each: `config show` exits **1** with reason `config_malformed`, and `sdle validate` reports a `config_malformed` **error** finding with exit 3. The test asserts the two consumers report the **same `detail` string**, which is the mechanical proof that D4's single predicate serves both (invariant 7). The `"yaml"` case additionally asserts the message names the requirement that a dependency be explicitly accepted first.

**N7 — Leak detector: runtime member under repository `.sdle/`.** Parametrised over `sdle.workitem_runtime_member_names(...)` — **derived, never re-listed**, so a future phase that adds a runtime member inherits the check automatically. Planting each name under `.sdle/` makes `sdle validate` report `lifecycle_state_in_repository_config` as an **error** at exit 3, naming the offending path.

**N8 — Leak detector: repository config member under a WorkItem `.sdle/`.** Planting `config.json`, `policies/`, `templates/`, `baseline.json` or `implementation-state/` under `workitems/<id>/.sdle/` makes `sdle validate` report `repository_config_in_workitem` as an error at exit 3 — **including** the case where that WorkItem has no `state.json`, which is why the check cannot live in `_validate_runtime_state`.

**N9 — Healthy repositories stay clean, before and after.** `sdle validate` returns `findings == []`, `errors == 0`, exit 0 for (a) a git-initialised repository with one WorkItem and `init` run and **no** `.sdle/` — the exact pre-T05 shape, and the regression guard for `test_validate_is_clean_in_a_healthy_repository`; and (b) the same repository after `config init`.

**N10 — The differential no-lifecycle-change proof.** Two scratch projects built from the same fixture. Project A: `run_happy_path(A)`. Project B: `config init`, then `run_happy_path(B)`. Assert:

1. both traversals equal `EXPECTED_TRAVERSAL`;
2. the ordered sequence of audit **event** names is identical between A and B;
3. `state.json` is identical after removing only the fields that legitimately vary between two runs (`last_updated`, `audit_sha`, `artifact_shas`, `current_artifact_sha`, `security_review_artifact`, `implementation_base_ref`, and the `approvals` timestamps);
4. **B's `.sdle/` is byte-identical before and after the entire 18-phase run** — nothing in the lifecycle reads or writes the repository configuration boundary.

Clause 4 is the single strongest statement that no lifecycle rule moved into `.sdle/`, and it is why this test exists rather than relying on a green suite.

**N11 — Source-level containment.** AST over `scripts/sdle.py`:

1. the set of function names referencing any D1 property (`config_root`, `config_root_relative`, `config_file`, `policies_dir`, `shared_templates_dir`, `baseline_file`, `implementation_state_dir`) is exactly `{"cmd_config_init", "cmd_config_show", "read_repo_config", "repo_config_findings", "collect_validation_findings"}` — a closed set in the style of `test_workitem_rebinding_happens_only_at_the_declared_sites`;
2. none of `cmd_config_init`, `cmd_config_show`, `read_repo_config`, `repo_config_findings` calls `read_state`, `save_state`, `append_audit`, `write_active_context`, `clear_active_context`, `touch_lock` or `bind_workitem`;
3. no function whose name starts with `cmd_gate`, `cmd_advance`, `cmd_approve` or `cmd_init` references any D1 property.

**N12 — The new project-root marker.** (a) `.sdle/config.json` alone makes a directory a project root; (b) a nearer `.git` still wins over a farther `.sdle/config.json`, and a nearer `.sdle/config.json` wins over a farther `.git` — the documented nearest-ancestor semantics, unchanged; (c) **control case**: a tree containing no `.sdle/config.json` resolves to exactly the same root as it does with `PROJECT_ROOT_MARKERS` monkeypatched back to its `7b054ee` value, over the four shapes the existing marker tests already cover.

**N13 — `config init` purity toward WorkItem runtime.** In a repository with two WorkItems, one of them mid-run: a recursive SHA map of **everything outside `.sdle/`** is byte-identical across `config init`, `config show` and `validate`; and `config show` and `validate` additionally leave `.sdle/` itself byte-identical. Mirrors T03's `bind_workitem` purity proof and T04's `feature bind` proof.

**N14 — `config init` never escapes `config_root`, and inherits atomicity.** On the success path and on each refusal path, no file is created outside `config_root`; an injected `OSError` during the write leaves no partial `config.json` and leaves `.sdle/` in a state a re-run can complete. (`write_atomic` already guarantees the no-partial-file property; this pins that `config init` uses it rather than hand-rolling a write.)

---

## Failure modes

| # | Failure mode | Guard |
|---|---|---|
| F1 | **A lifecycle rule leaks into `.sdle/`** — the likeliest defect in this phase, and §11's own explicit instruction against it. | Four independent detectors: N11's closed reference set (source level), N10 clause 4 (runtime level), N7/N8 (`validate`'s bidirectional leak check), and A5's byte-identical `.claude/skills/` (prompt level). |
| F2 | **Inert scaffolding passes as success.** Directories nothing reads leave the suite green, so a green suite proves nothing. | The positive proofs are kept separate from the negative ones: A11 (§11's exit criterion driven through the real CLI), A12 (leak detector fires), A13 (purity), A20 (differential run). A green suite is necessary, not sufficient — the handoff must say so explicitly. |
| F3 | **The `.sdle/` naming collision.** Repository `.sdle/` and `workitems/<id>/.sdle/` are matched by the same patterns; `hooks.py`'s `in_dir` cannot tell them apart (evidence table). | T05 changes **no** string matcher. `hooks.py` is byte-identical (A5); `SDLE_OWNED_PREFIXES` is untouched (A7); `.gitignore` is untouched (A5); `Paths` distinguishes the two by derivation, not by string (N1). The collision is recorded as a finding **for T09**, the first phase that must fence `policies/`. |
| F4 | **`config init` writes into a WorkItem.** A repository root resolving inside `workitems/` would put repository configuration in the wrong boundary. | D4's `config_root_inside_workitem` predicate refuses before any write; N3 pins it; `validate` reports it. Fails closed. |
| F5 | **Two disagreeing answers to "is this configuration valid".** `config show` and `validate` drift apart — an invariant-7 fork. | Exactly one predicate, `repo_config_findings`; N6 asserts the two consumers emit the **same detail string**. |
| F6 | **An unplanned second test edit.** A new rebinding site or a new active-context writer trips one of the three other closed-set assertions. | D4's binding constraint places the derivation and the reverse scan inside `collect_validation_findings`; D5 forbids `config init` from writing an active context; the anti-contradiction clause makes any further edit a declared divergence. |
| F7 | **`lint-skill` goes red on a documentation edit.** `version_string_consistent` takes the first regex match in README's version table; `no_hardcoded_progress_outside_progress_map` fails on any literal `N/18` in instruction text; `doc_lists_every_phase_*` scans README and the Reference Guide. | Re-run `lint-skill` after **each** document edit, not once at the end (T02/T04 lesson). Add **no** version-history row and **no** version string. Write "18-phase" in prose, never `N/18`. |
| F8 | **Schema creep.** `configVersion` gets mistaken for `workflow_version` and someone adds a 16th migration row or bumps to 1.16. | A6 and A3: `templates/state.json` byte-identical, `CURRENT_VERSION == "1.15"`, `lint-skill` reports `15 migration rows` and `all four locations report v1.15`. |
| F9 | **Speculative content.** `baseline.json` or an `implementation-state/` schema gets invented because the diagram shows the name. | D7: the slot exists, the file does not. A19 greps the diff for a `baseline` writer and for any `implementation-state` schema. §27 forbids speculative implementation. |
| F10 | **Suite left red across milestones**, making failure attribution impossible. | The milestone sequence is designed so the suite is green at the end of **every** milestone. M1 is the structural change whose proof is that nothing else moves — zero existing-test edits. The single authorised test edit lands in the same milestone as the change requiring it (M2). |
| F11 | **Future-phase leakage** — T06 classification/risk, T07 flows, T09 executable policies, T11 legacy removal. | The exclusion table below; A19's grep for `risk_tier`, `flow_id`, `classification`, `quality_gate`, `risk evaluate`, `gate status`, `baseline validate`, `discovery`; `.sdle/policies/` must remain **empty except `.gitkeep`**. |
| F12 | **`rtk` false green.** A bare `python -m pytest` prints `Pytest: No tests collected` and exits 0. | Every run goes through `rtk proxy`, unpiped, raw exit read directly, 600000 ms timeout. `rtk` also truncates `git diff` and `grep`; use `rtk proxy "<command>"` for full output. Any handoff figure not produced this way is invalid. |
| F13 | **Treating a failure as a flake.** The F1 `ENVIRONMENT_FLAKE` procedure from T00/T01 is **VOID** — `6e8af8c` fixed the `write_atomic` `WinError 5` flake. | Any test failure is a presumed real T05 regression: investigate it. Do not pattern-match it to the old signature, and do not touch `write_atomic`. |
| F14 | **Interruption mid-phase.** Two of the last three phases were terminated by API spend limits mid-flight. | One `T05-checkpoint-a01-NN.md` per milestone, recording what is on disk, the suite figure observed at that point, and what remains. A resuming agent must verify every checkpoint claim against disk — `--collect-only` is the cheap check — because T03's and T04's checkpoints were both found to overstate what existed. |

---

## Rollback/recovery strategy

- **Rollback point: `7b054ee`.** Proved in this context: `git diff --name-status 7b054ee HEAD` lists exactly one file, `M docs/transition/RESUME.md`. `git reset --hard 7b054ee` restores the T04 product tree exactly. After this plan is committed the delta is that commit plus `progress.md`; the **product** rollback point is unchanged.
- **T05 has no irreversible data effect.** It writes only inside a new, previously non-existent `.sdle/` directory, never deletes, never overwrites (`config_exists` refuses), and touches no state, audit, evidence or Spec Kit artefact. Recovery from any partial state is deleting `.sdle/` — nothing else depends on it.
- **No schema change means no state-file recovery problem.** A state written under a T05 engine is byte-compatible with a `7b054ee` engine, because T05 writes no state. The implementer must not add a migration row.
- **Per-milestone recovery.** Each milestone ends with a green suite and a checkpoint. A failure inside a milestone is recovered by reverting that milestone's diff, not the phase.
- If the transition guard refuses an operation, **quote the refusal verbatim in the handoff** and re-run in an allowed shape. Do not route around it with an interpreter or a different shell. (In this planning context the guard permitted a backgrounded, unredirected `rtk proxy "python -m pytest …"`, and refused a `cat > file <<'EOF'` heredoc write with `SDLE transition agent guard: planner Bash/PowerShell must be observational; blocked command shape`.)

---

## Acceptance criteria

Every figure must come from a command run in the implementing context and be quoted, not predicted.

- [ ] **A1** `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX"` at the end of T05: **raw exit 0**; `--collect-only -q` count equals the passed count; `-rsxX` produces no short-summary section (zero skips, xfails, errors). Both figures quoted.
- [ ] **A2** The suite arithmetic is stated explicitly: re-derived baseline at `7b054ee`/`44572f7` + the collected count of `tests/test_units_repo_config.py` = the final count, and `tests/test_units_workitem_resolution.py`'s per-file count is **unchanged** (the one authorised edit adds no test).
- [ ] **A3** `python scripts/sdle.py lint-skill` raw exit 0, **22 PASS / 0 FAIL**, reporting `Parsed 19 phases, 8 gates, 15 migration rows` and `all four locations report v1.15`.
- [ ] **A4** `python tools/transition/validate.py` raw exit 0.
- [ ] **A5** `git diff --exit-code 7b054ee -- .claude/skills/ .claude/hooks/ .claude/commands/ .claude/settings.json .claude/agents/ .github/ scripts/sdle.sh scripts/sdle.ps1 scripts/README.md .gitignore .gitattributes requirements/ docs/dry-runs/ docs/architecture/ADR-001-deterministic-core.md tools/` returns **exit 0**.
- [ ] **A6** `templates/state.json` is byte-identical to `7b054ee`; `CURRENT_VERSION` is `"1.15"`; `MIGRATIONS` has 15 tuples; no `VERSION_MIGRATION` row was added; no version string anywhere changed.
- [ ] **A7** Extract-and-compare against `7b054ee` (not eyeballing) shows these are **byte-identical**: `write_atomic`, `append_audit`, `save_state`, `read_state`, `touch_lock`, `bind_workitem`, `resolve_decision`, `branch_candidates`, `candidate_evidence`, `cmd_migrate_workflow`, `cmd_init`, `cmd_workitem_use`, `cmd_implement_preflight`, `cmd_manifest_build`, `_validate_runtime_state`, and the `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS` and `CONFIRMABLE` definitions.
- [ ] **A8** `sdle.RUNTIME_FREE_COMMANDS` equals the `7b054ee` set **plus exactly `"config"`** — 7 members, nothing removed.
- [ ] **A9** `.sdle/config.json` in this repository parses to exactly `{"configVersion": "1", "policyFormat": "json"}`; `.sdle/` contains **no** `baseline.json`; `.sdle/policies/` and `.sdle/templates/` contain **only** `.gitkeep`; `git check-ignore` exits 1 for every file under `.sdle/` (all versioned).
- [ ] **A10** Running `config init` with `--project-root` pointed at a fresh scratch copy produces a `.sdle/` whose relative file list and parsed `config.json` are **equal** to this repository's checked-in `.sdle/`. (Compare parsed JSON and relative paths, not raw bytes — `.gitattributes` normalises line endings.)
- [ ] **A11 — §11's exit criterion, driven through the real CLI in a scratch project.** In one repository with two registered WorkItems and no `--workitem`: `config show` exits **0** and `config init` exits **0**, while `state get` in that same repository exits **1** with `workitem_ambiguous`. Repeated with zero WorkItems (`workitem_required`) and with one.
- [ ] **A12 — The leak detector fires in both directions.** Planting each derived WorkItem runtime member name under `.sdle/` makes `validate` exit **3** with a `lifecycle_state_in_repository_config` error; planting a repository configuration member under `workitems/<id>/.sdle/` makes it exit **3** with `repository_config_in_workitem` — including when that WorkItem has no `state.json`.
- [ ] **A13 — Purity.** A recursive SHA map of everything outside `.sdle/` is byte-identical across `config init`, `config show` and `validate` in a two-WorkItem repository with one WorkItem mid-run; `config show` and `validate` additionally leave `.sdle/` byte-identical; and no `config` subcommand appends an audit entry (the target `audit.md` SHA is unchanged).
- [ ] **A14 — Fails closed.** `config init` refuses `config_exists` without touching either file when `config.json` exists; both `config` subcommands refuse `config_root_inside_workitem` when the resolved root is `workitems/` or `workitems/<id>/`; `config show` refuses `config_malformed` on each of the eight N6 cases; `policyFormat: "yaml"` is refused with a message naming the explicit-dependency-acceptance requirement.
- [ ] **A15** `sdle validate` returns `findings == []`, `errors == 0`, exit 0 in a healthy repository **both** with no `.sdle/` and after `config init`.
- [ ] **A16** The T02/T03/T04 guarantees still hold, each by its named existing test passing unmodified: the ladder never guesses; the legacy `.workflow/` dual-read rung binds; `migrate-workflow` never mutates `.workflow/`; `init` refuses `legacy_workflow_present` unconditionally; the Spec Kit binding is unchanged.
- [ ] **A17 — Invariant 7.** A grep over the T05 diff shows no existing fact was copied into `.sdle/`: no `rate_limits`, `approvals`, `project_name`, `verbose`, `max_remediation_attempts`, `PHASE_SEQUENCE`, `NEXT_PHASE`, `PROGRESS_MAP`, `ARTIFACT_OWNERSHIP` or `PHASE_TO_GATE_KEY` value appears in any file under `.sdle/` or in `REPO_CONFIG_DEFAULTS`.
- [ ] **A18 — Invariant 3.** No `speckit-` or `/speckit.` string appears in any subcommand name, help text, refusal message or emitted key added by T05 (grep over the diff).
- [ ] **A19 — No future-phase leakage.** A grep over the diff for `risk_tier`, `flow_id`, `classification`, `quality_gate`, `risk evaluate`, `gate status`, `baseline validate`, `discovery` returns nothing; `.sdle/policies/` contains only `.gitkeep`; no code path writes `baseline.json` or any `implementation-state/` file; `.workflow/` dual-read, `migrate-workflow` and `init`'s `legacy_workflow_present` refusal are all still present.
- [ ] **A20 — The differential proof.** Two identical scratch projects, one with `config init` run first, produce identical 18-phase traversals, identical ordered audit event sequences, and identical `state.json` modulo the run-varying fields; and the configured project's `.sdle/` is **byte-identical before and after** the whole run.
- [ ] **A21 — TP-003.** `git diff --name-status 7b054ee -- tests/` shows **zero `D`**, **zero `R`**, exactly **one `M`** (`tests/test_units_workitem_resolution.py`, limited to the single literal in `test_runtime_free_commands_is_a_closed_enumerated_set`), and exactly one `A`/`??` (`tests/test_units_repo_config.py`). `tests/conftest.py` is byte-identical. The other three closed-set assertions are byte-identical.
- [ ] **A22** Python 3.11 and CI are recorded as **NOT_RUN / UNKNOWN**, with no outcome predicted.

---

## Milestone sequence

Designed so the suite is green at the end of **every** milestone (F10). One `T05-checkpoint-a01-NN.md` per milestone, recording the suite figure observed at that point and what remains, so an interrupted fresh agent can resume from disk (F14).

| M | Content | Why the suite stays green |
|---|---|---|
| **M1** | D1 `Paths` seam + D2 project-root marker. New tests N1, N12. | **The structural proof, in the same role as T02's `Paths` seam and T04's M1: zero existing-test edits.** Nothing reads the new properties, and the marker is a provable no-op for any tree with no `.sdle/config.json`. If any existing test moves here, the seam is wrong. |
| **M2** | D3 configuration model + D5 `config init` / `config show` + D6 `RUNTIME_FREE_COMMANDS`, **together with** the single authorised edit to `test_runtime_free_commands_is_a_closed_enumerated_set`. New tests N2–N6, N13, N14. | Purely additive to the CLI; the one existing assertion that must move moves in the same milestone as the change requiring it. |
| **M3** | D4's two leak-detector checks inside `collect_validation_findings`. New tests N7–N9. | `validate`'s output is unchanged for every repository that has no `.sdle/` and no misplaced artefact, so `test_validate_is_clean_in_a_healthy_repository` stays byte-identical and green. |
| **M4** | N10 (differential) and N11 (containment). | Test-only. These are the phase-level proofs, written **after** the engine is complete so they test what shipped, not what was planned. |
| **M5** | D7 the repository's own versioned `.sdle/` (generated by `config init`, then committed) + D8 ADR-002, README, Reference Guide, CLAUDE.md. | `lint-skill` re-run after **each** document edit. Fixtures never copy the repository root's `.sdle/`, so no test observes it. |
| **M6** | Full suite, `lint-skill`, `validate.py`, the A1–A22 matrix, handoff. | — |

---

## Unknowns / decision requirements

**No material unresolved decision. Status recommendation is PLANNED.** The judgements that could otherwise be re-opened mid-flight are pinned here.

1. **Policy format: JSON. DECIDED by the user; do not re-open.** Rationale, verbatim: *preserve the zero-dependency stdlib-only core exactly as it is today, so `sdle.py` stays runnable anywhere Python 3.11+ exists with no install step.* Independently confirmed in this context: `sdle.py`'s 14 imports are all stdlib; no `pyproject.toml`/`setup.py`/`setup.cfg`/`requirements.txt`; no YAML import anywhere in `scripts/`, `.claude/`, `tests/` or `tools/`; `CLAUDE.md:15` and `scripts/README.md:8` both state "standard library only"; CI pins Python 3.11. This is §11's own recommended default. **No dependency is added, and no home-grown YAML parser is written — §11 forbids it explicitly.** A later phase may revisit with real authoring evidence and an explicit dependency acceptance.

2. **`implementation-state/` has no defined meaning — `UNKNOWN`, and designed for.** It appears three times in the whole contract: twice as a diagram line and once as the phrase "implementation-transition metadata". T05 creates it as an empty, versioned, documented slot with **no schema, no producer and no consumer**, because §27 forbids speculative implementation. The alternative — inventing a schema from the name — is exactly the failure §27 describes.

3. **The write fence is deliberately NOT extended to repository `.sdle/`, and T04's finding N-3 is deliberately NOT adopted.** Both are decisions, not omissions.
   - *Not fencing:* at T05 `.sdle/` holds no machine-owned executable content. `config.json` is human-authorable, `policies/` is empty by §11's own "do not move lifecycle rules yet", nothing in the audit hash chain or any drift baseline lives there, and nothing lifecycle reads it. Invariant 6 concerns `state.json` and `audit.md`, which stay fenced and unchanged. A hand-edited `config.json` is detected — `config show` refuses `config_malformed` and `validate` reports it — and cannot alter lifecycle behaviour, because nothing lifecycle reads it. **T09 is the first phase that must fence `policies/`**, and it inherits a recorded hazard: `hooks.py`'s `in_dir(path, name)` matches `/{name}/` **anywhere** in the path, so adding `".sdle"` to `FENCED` would also match `workitems/<id>/.sdle/` and would shadow the existing `workitems` reason text. A fence for repository `.sdle/` must be anchored to the start of the repo-relative path, not to a segment boundary.
   - *N-3 not adopted:* the carve-out matches a non-normalised path, so `workitems/<id>/specs/../.sdle/state.json` escapes it. It is genuinely adjacent to T05's surface and is left open on purpose. T05 makes **zero** edits to `hooks.py`, and the byte-identity of that file is itself part of T05's proof that no guardrail moved; more importantly, N-3's correct fix is to normalise before matching, which changes how `in_dir` behaves for **every** `FENCED` name — a fence-wide semantic change deserving its own phase and its own tests. **Recommended assignment: T11 hardening** (it currently sits at "any phase").

4. **`SDLE_OWNED_PREFIXES` is deliberately NOT extended to `.sdle/`.** That tuple exists to exclude paths **SDLE itself writes during a run** from the implement-preflight dirty-tree list — it is consumed by exactly one function, `cmd_implement_preflight`. Nothing writes `.sdle/` during a run at T05. `.sdle/` is versioned engineering evidence, so an uncommitted change to it **should** trip the dirty-tree guard exactly as an uncommitted source change does. That direction fails closed and preserves a §18 Wave A guardrail byte-for-byte. The contrast with `workitems/` (added at T02) is deliberate and must be stated in the handoff: `workitems/` holds runtime state SDLE writes mid-run; `.sdle/` does not. If a later phase makes something write there mid-run, that phase revisits this.

5. **`.sdle/` is versioned, and `.gitignore` needs no edit.** §19 places `.sdle/baseline.*` and `.sdle/policies/*` under "must eventually be versioned" and restricts "may remain local/ignored" to "only data that is truly ephemeral". `git check-ignore -v .sdle/config.json` already exits 1, so the §19 row is satisfied with **zero diff** — the same shape T01 used for `workitems/`. `.gitkeep` files exist because Git cannot version an empty directory; without them the boundary would not survive a clone.

6. **The repository's own `.sdle/` is created here, and this repository is also a target-project fixture.** `CLAUDE.md` records that the workflow can be exercised in place. Creating `.sdle/` at this root was checked and is safe: no test globs the repository root, `tools/transition/validate.py` performs no directory walk, `conftest.bare_project` copies only `scripts/`, `.claude/hooks/` and `.claude/settings.json` into scratch projects, and the one test that runs with `cwd=REPO_ROOT` invokes the runtime-free `constants`.

7. **No project-root marker ordering hazard beyond the documented one.** `discover_project_root` returns the nearest ancestor carrying **any** marker; markers are tested in the inner loop, so their order within the tuple cannot change which directory is returned — only which level stops the walk can. Appending the new marker can therefore only stop the walk lower, and only in a tree containing `.sdle/config.json`. N12(c) pins the control case.

8. **Hygiene items left unowned by earlier verifiers — explicit decisions.** T03-4 (`ACTIVE_CONTEXT_SETTERS` dead in production code), T03-5 (`cmd_workitem_use` not error-hardened), T03-6 (the `workitem_required` reason-name collision between a `UsageError` and a refusal), T04 **N-4** (`SKILL.md:358` made inaccurate by T04's own carve-out) and T04 **N-7** (`cmd_manifest_build` lacks the Spec Kit relocation exclude): **T05 adopts none of them.** None is incidental to any edit in this plan — T05 touches neither `cmd_workitem_use`, nor the active-context writers, nor `SKILL.md`, nor `cmd_manifest_build`, and A5/A7 require `SKILL.md` and `cmd_manifest_build` to be byte-identical. Adopting any of them would break T05's central proof that the prompt layer and the Wave A guardrails did not move. They remain open for a later phase.

9. **Python 3.11 and CI: `NOT_RUN` / `UNKNOWN`.** The branch is local-only; CI pins 3.11 on `ubuntu-latest` and `windows-latest`; this host runs **3.13.0**. Predict no outcome. T05 is standard-library-only and 3.11-safe by construction — it adds no syntax beyond what `sdle.py` already uses — so a later CI failure could not invalidate the design, but it must never be claimed green.

10. **Every quantitative claim in a prior plan is unverified until re-derived.** `T00-plan.md`'s "21 top-level subcommands" is known wrong. `RESUME.md`'s "500 passed" is a prior-context figure: re-derive it before relying on it.

11. **The suite takes roughly a quarter of an hour and has grown every phase.** Budget for it; give every run a 600000 ms timeout. Do not let a truncated or timed-out run become a quoted figure.

---

## Scope exclusions

The following must **not** leak into T05. If the implementer finds an edit that seems to require one, that is a plan defect to declare, not a licence to widen.

| Excluded | Owner | Why it is out |
|---|---|---|
| **Moving any lifecycle rule into `.sdle/`** — phase sequence, gate registration, approval requirements, artifact ownership, rate limits, progress map | **§11's own instruction** | *"At T05, current 18-phase behavior still remains authoritative."* This is the single most likely form of leakage in this phase; F1 lists four detectors for it. |
| Requirements Quality Gate, structured classification, hybrid risk, governed-artifact review/validation | T06 (§12) | T05 adds no gate, no classification field and no risk concept. |
| Declarative flow selection; replacing the fixed 18-phase sequence; `flow_id` | T07 (§13) | — |
| Brownfield discovery, and **writing `.sdle/baseline.*`** | T08 (§14) | §11 calls it the "future baseline"; §14 owns its schema. T05 names the slot and creates no file. |
| **Executable risk/gate policies, and any content in `.sdle/policies/`** | T09 (§15) | §11: this phase establishes the boundary *before* new flow/risk policies are introduced. `policies/` must contain only `.gitkeep`. T09 also inherits the fence decision in Unknowns §3. |
| Progressive Claude skills and specialist subagents | T10 (§16) | Invariant 8 stands: nothing holding a gate is delegated. |
| Removing the legacy `.workflow/` dual-read rung, `migrate-workflow`, or `init`'s unconditional `legacy_workflow_present` refusal | **T11** (§17) | All three must still work at the end of T05 and are pinned by existing tests. |
| T04 **N-2** — Spec Kit discovery tier 2 (`<project-root>/specs/*`) picked by newest mtime, allowing cross-WorkItem adoption | T11 hardening | Not a configuration-boundary concern. |
| T04 **N-3** — the non-normalised write-fence carve-out | **T11 hardening** (recommended here) | Explicitly considered and left; see Unknowns §3. |
| T04 **N-6** — stale `.workflow/` runtime paths in `phase-execution.md`, `gate-protocol.md` and `docs/dry-runs/` | T11 documentation sweep | A5 requires `.claude/skills/` and `docs/dry-runs/` byte-identical. |
| T04 **N-4**, **N-7**; T03-**4/5/6**, **7/8**, **10** | unassigned | Explicitly **not adopted**; see Unknowns §8. |
| T03-**1** — the `branch_guard` fail-open window between the two confirmation steps | T11 | Needs a `pending_branch_ack` state key. T05 makes **no** schema change and must not smuggle one in. |
| T02 **NB-2**, **NB-4**, **NB-5** | T11 | — |
| Moving `design/`, `reviews/` or `clarifications/` under `workitems/` | unassigned | T04's recorded residual; §11 names none of them. TP-002 forbids changing two axes in one phase. |
| Splitting `sdle.py` into the §23 module layout | later, when the seams are stable | §23: *"Do not begin by splitting `sdle.py` only because it is large."* |
| `.claude/settings.local.json` | out of scope | The user's permission allowlist. Do not stage, revert or edit it. |
