# T03 Plan

**Phase:** T03 — WorkItem Resolution and Parallel Developer Isolation
**Planner context:** fresh/isolated
**Status recommendation:** PLANNED

**Contract sections:** `docs/transition/transition.md` §9 (primary), §19, §21, §22, §24.2; principles TP-001, TP-002, TP-003, TP-006, TP-007, TP-009.
**Precondition HEAD:** `ea165427dde3ac98c20f48800cc466303441c9ae` on `transition/workitem-v1`.
**Rollback point:** `ab889a1` (the T02 implementation commit).
**Product baseline:** `f8fdaa0`.

> Every numeric figure in this plan was produced by a command run in *this* planning
> context and is marked `OBSERVED` with the command. Nothing is copied forward from an
> earlier plan or handoff. Source is cited by symbol name or by a greppable anchor
> string, never by line number — T02's plan citations had drifted +14 by implementation
> time.

---

## Objective

Complete contract §9. Make SDLE resolve the active WorkItem from where the developer
actually launched Claude, from durable local context, and from Git, so that two
developers on separate branches or worktrees can drive two different WorkItems with no
shared state and no global lock — while keeping T02's proven property that the engine
**refuses rather than guesses** whenever more than one WorkItem is plausible.

Concretely T03 delivers six things:

1. **Repository-root discovery**, so the four launch locations of §9 all work.
2. **Three new resolution rungs** — CWD inside a WorkItem, persisted valid active
   context, unique Git-branch match — added *above* T02's refusals, never replacing them.
3. **A durable, developer-local active context** (`workitems/.active-context.json`),
   written only at explicit, auditable moments.
4. **Branch and starting SHA recorded** per execution, plus a branch-mismatch policy
   that warns on advisory commands and refuses on lifecycle-critical ones.
5. **`sdle validate`** with the seven §9 checks, and **`sdle workitem resolve`** — a
   non-refusing diagnostic that supplies the candidate set to the parent session for
   §9 rungs 5 (AI-assisted inference) and 6 (ask user).
6. **Restoration of the dirty-tree tripwire in multi-WorkItem repositories**
   (T02 finding NB-3).

---

## Repository evidence

| Claim | Class | Evidence |
|---|---|---|
| HEAD is `ea165427dde3ac98c20f48800cc466303441c9ae`, branch `transition/workitem-v1` | OBSERVED | `git rev-parse HEAD`; `git rev-parse --abbrev-ref HEAD` |
| Working tree carries exactly one modification, `.claude/settings.local.json` (permission allowlist, not product code) | OBSERVED | `git status --porcelain` → ` M .claude/settings.local.json` |
| `ab889a1..HEAD` is control-plane only: `RESUME.md` (+60), `T02-verification-a01.md` (+437), `progress.md` (1/1) | OBSERVED | `git diff --numstat ab889a1 HEAD` — three rows, no product file |
| Full suite is green: `341 passed in 273.53s (0:04:33)`, raw exit 0 | OBSERVED | `python -m pytest -q -rsxX` (run in this context; no short-summary section emitted, so zero skips/xfails) |
| 341 tests collected — collected equals passed, so zero skips, xfails or errors | OBSERVED | `python -m pytest -q --collect-only` → `341 tests collected in 0.16s` |
| `lint-skill` is 22 PASS / 0 FAIL, exit 0 | OBSERVED | `python scripts/sdle.py lint-skill`; `grep -c '"passed": true'` → 22, `grep -c '"passed": false'` → 0 |
| Transition validator is clean and points at this phase | OBSERVED | `python tools/transition/validate.py` → `TRANSITION_VALID: complete=3/12 next=T03`, exit 0 |
| `docs/transition/control-plane.sha256` has 16 lines and does **not** cover `progress.md`, so this plan's progress edit cannot break `validate.py` | OBSERVED | `grep -n "progress.md" docs/transition/control-plane.sha256` → exit 1; `grep -c "" …` → 16 |
| The **F1 `ENVIRONMENT_FLAKE` procedure is VOID.** The suite is green; any failure during T03 is a presumed real regression | OBSERVED | the 341-passed run above; commit `6e8af8c` "Retry os.replace in write_atomic on a transient PermissionError" |
| `bind_workitem` implements exactly the T02 subset: explicit → sole → legacy dual-read → `workitem_required` → `workitem_ambiguous`; it is documented pure ("nothing is printed and nothing is written, so the hooks can call it speculatively") | OBSERVED | `scripts/sdle.py`, `def bind_workitem` and its docstring |
| `RUNTIME_FREE_COMMANDS` is a five-member frozenset: `lint-skill`, `sha`, `constants`, `workitem`, `migrate-workflow` | OBSERVED | `scripts/sdle.py`, `RUNTIME_FREE_COMMANDS = frozenset({...})` |
| There is **no** `validate` subcommand and **no** `workitem resolve` / `workitem use` | OBSERVED | full listing of `add_parser` registrations in `build_parser`; 69 lines match `add_parser` (`grep -c "add_parser" scripts/sdle.py`) |
| `Paths` has no notion of the launch directory; `resolve_paths` uses `--project-root` → `SDLE_PROJECT_ROOT` → `Path.cwd()` **as** the project root, with no upward walk | OBSERVED | `scripts/sdle.py`, `class Paths` and `def resolve_paths` |
| `.claude/hooks/hooks.py::dirty_tree` calls `engine.resolve_paths(str(PROJECT_DIR), None)` then `engine.bind_workitem(paths)` and returns silently on any exception | OBSERVED | `.claude/hooks/hooks.py`, `def dirty_tree` |
| NB-3 is real: with ≥2 registered WorkItems the dirty-tree guard is silent, and only richer resolution restores it | OBSERVED | `docs/transition/phases/T02-verification-a01.md` §Findings, bullet "NB-3"; pinned by `tests/test_hooks.py::test_dirty_tree_is_silent_when_the_workitem_is_ambiguous` |
| `tests/test_units_workitem.py` asserts `set(doc["git"]) == {"initialBranch"}` — the `workitem.json` `git` object has an exact-key assertion | OBSERVED | `grep -n "set(doc\[\"git\"\])" tests/test_units_workitem.py` |
| `execution.json` has **no** exact-key assertion; its test checks individual keys only (`executionId`, `workitem`, `sdleVersion`, `startedAt`) | OBSERVED | `tests/test_units_workitem_runtime.py::test_execution_identity_is_written_at_init_and_is_not_the_workitem` |
| `write_execution_file` is called from exactly two places: `cmd_init` and `cmd_migrate_workflow` | OBSERVED | `grep -n "write_execution_file" scripts/sdle.py` → definition + two call sites |
| `cmd_workitem_create`'s uniqueness scan iterates `workitems/` but only considers `child.is_dir()`, so a *file* directly under `workitems/` cannot collide with an id | OBSERVED | `scripts/sdle.py`, `cmd_workitem_create`, `for child in sorted(root.iterdir()): if child.is_dir():` |
| `CONFIRMABLE` is a five-member set: `reset`, `skip`, `implement_dirty_tree`, `accept_state_jump`, `accept_audit_mismatch` | OBSERVED | `scripts/sdle.py`, `CONFIRMABLE = {...}` |
| The dirty-tree two-step idiom already exists: `cmd_implement_preflight` sets `pending_confirm_action = "implement_dirty_tree"`, audits `dirty_tree_guard`, and refuses | OBSERVED | `scripts/sdle.py`, `def cmd_implement_preflight` |
| `.gitignore` is 9 lines and ignores `workitems/*/.sdle/lock` only under `workitems/` | OBSERVED | `cat .gitignore` |
| `SDLE_OWNED_PREFIXES` contains `workitems/`, so anything directly under `workitems/` is already excluded from the preflight dirty-tree entry list | OBSERVED | `scripts/sdle.py`, `SDLE_OWNED_PREFIXES = (...)` |
| The Phase-17 diff excludes only `paths.runtime_relative + "/"` — a file at `workitems/.active-context.json` is **not** excluded, so it must be gitignored or it would be committed and appear in the security-review diff | OBSERVED | `scripts/sdle.py`, `runtime_prefix = paths.runtime_relative + "/"` in `cmd_manifest_build`/security-review evidence path; `tests/test_units_workitem_runtime.py::test_the_phase_17_diff_excludes_the_workitem_runtime` |
| `conftest.Project.run` always passes `--project-root`, so no existing test exercises CWD-based project-root discovery; `conftest.init_git` writes `.workflow/\nworkitems/*/.sdle/lock\n` and no test asserts `.gitignore` content | OBSERVED | `tests/conftest.py`, `def _argv`, `def init_git`; `grep -rn "gitignore" tests/*.py` → 2 hits, both in `conftest.py`, neither an assertion |
| Test modules import shared helpers as `from conftest import FIXTURE_WORKITEM_ID, Project, sdle`, so a new test file can define its own launcher without touching `conftest.py` fixtures | OBSERVED | `tests/test_units_workitem_runtime.py` import block |
| The only test that constructs a second WorkItem *after* `init` (i.e. the only place a persisted context could change an existing outcome) is `tests/test_hooks.py::test_dirty_tree_is_silent_when_the_workitem_is_ambiguous` | OBSERVED | `grep -rn "create_wi\|workitem\", \"create\|as_workitem" tests/*.py`, each hit inspected: every other multi-WorkItem test either uses `as_workitem` (pinned `--workitem`) or never runs `init` |
| `test_runtime_free_commands_need_no_workitem` is parametrised over a list of four commands and does **not** assert the frozenset's exact membership, so adding `validate` to `RUNTIME_FREE_COMMANDS` breaks nothing | OBSERVED | `tests/test_units_workitem_runtime.py`, the `@pytest.mark.parametrize("command", [...])` above that test |
| `test_header_maps_every_status_to_its_display_text` asserts `rendered.endswith(display)`, so nothing may be appended to the rendered header string | OBSERVED | `tests/test_units_state.py`, that test |
| `lint-skill`'s 22 checks are `tables_wellformed`, the phase/gate set checks, `every_phase_has_execution_block`, `single_state_template`, `version_string_consistent`, `migration_covers_every_state_field`, `no_powershell_only_cmdlets`, `no_hardcoded_progress_outside_progress_map`, `doc_lists_every_phase_README`, `doc_lists_every_phase_SDLE-Reference-Guide` | OBSERVED | `python scripts/sdle.py lint-skill`, `data.checks[].name` |
| Adding rungs *above* T02's refusals cannot change any existing test outcome except the NB-3 one, because every other multi-WorkItem test pins `--workitem` (rung 1) and every single-WorkItem test is answered by the sole-registered rung | INFERRED | derived from the two `grep` sweeps above plus the rung ordering in §"Behavioral delta" |
| `git worktree` is available wherever the suite already runs, since `conftest.init_git` already makes git a hard dependency of `git_project`/`started_git` | INFERRED | `tests/conftest.py::init_git`; git version not probed in this context |
| Python 3.11 behaviour | UNKNOWN / NOT_RUN | no 3.11 interpreter on this host; local evidence is one interpreter only |
| CI (`ubuntu-latest`, `windows-latest`) outcome | UNKNOWN / NOT_RUN | the branch has never been pushed; **no outcome is predicted** |
| `T00-plan.md`'s "21 top-level subcommands" figure | KNOWN WRONG, not used here | recorded in `progress.md` T00 row; every figure in this plan is re-derived |

---

## Behavioral delta

### Deliberate changes

#### D1 — Repository-root discovery (contract §9 "Supported launch locations")

`resolve_paths` today treats the launch directory *as* the project root. Launching from
`workitems/wi-a/` therefore makes `workitems/wi-a/` the repository, and every path below
it is wrong. §9's four launch locations are a requirement on **project-root** resolution,
not only on WorkItem resolution.

New precedence, highest first:

1. `--project-root` (explicit) — unchanged, always wins.
2. `SDLE_PROJECT_ROOT` — unchanged.
3. The **nearest ancestor of the launch directory** (inclusive) containing, in this
   marker order: `workitems/index.md`, then `.workflow/state.json`, then `.git`.
   The first marker found while walking up wins; markers are tested in that order at
   each level before moving to the parent.
4. Fallback: the launch directory itself — byte-identical to today's behaviour, which
   is what keeps a brand-new project with no markers working.

`Paths` gains one field, `launch_cwd: Path | None = None`, populated by `resolve_paths`
from `Path.cwd()` (or from the explicit root when one is given and the real CWD is
outside it). `dataclass_replace(paths, workitem=…)` preserves it, so `bind_workitem`
and `migrate-workflow` keep working unchanged.

*Blast radius:* zero for the suite, because `conftest.Project.run` always passes
`--project-root` (OBSERVED). This is nevertheless a deliberate behavioural change for
bare-CWD invocations and is declared as such.

#### D2 — The resolution ladder, reconciled

§9's stated priority is `explicit → CWD → persisted context → branch/metadata →
AI inference → ask`. T02 added a "sole registered WorkItem" rung that §9 does not name.
It is not a guess: it is §9's own ambiguity rule `1 valid candidate -> use`. T03 keeps
it and places it at position 3, because with exactly one registered WorkItem rungs 4 and
5 can only ever return that same id or nothing, and letting a *stale* context or a
*non-matching* branch demote a single-WorkItem repository to a refusal would be a
regression against `test_rung2_the_sole_registered_workitem_binds_with_no_flag` and
against the whole suite. This placement is an INFERRED reconciliation, stated here so
no implementer has to invent it mid-flight.

Final ladder inside `bind_workitem` (engine, deterministic):

| # | Rung | Outcome |
|---:|---|---|
| 1 | explicit `--workitem <id>`, must be registered | bind, else refuse `workitem_unknown` (unchanged) |
| 2 | `launch_cwd` is inside `<root>/workitems/<x>/` | `<x>` registered → bind. `<x>` is an on-disk directory but **not** in the index → refuse **`workitem_unregistered`** (new). |
| 3 | exactly one registered WorkItem | bind (T02 rung 2, unchanged) |
| 4 | persisted **valid** active context | bind |
| 5 | unique Git-branch match | bind |
| 6 | zero registered **and** `.workflow/state.json` exists | legacy binding, `workitem is None` — TRANSITIONAL, T11 removes it (unchanged) |
| 7 | zero registered | refuse `workitem_required` (unchanged) |
| 8 | otherwise | refuse `workitem_ambiguous`, listing candidates — **never picks** (unchanged) |

`for_init=True` keeps its existing override exactly: `init` refuses
`legacy_workflow_present` whenever legacy state exists, whatever the registered count,
and never takes rung 6.

Rung 2's unregistered-directory refusal is deliberate and is the one place T03 *adds* a
refusal. Falling through would bind some *other* WorkItem while the developer is
standing inside `<x>` — a silent wrong pick, which §9 forbids more strongly than it
forbids an inconvenient refusal.

Rungs 4 and 5 are only ever reached when **two or more** WorkItems are registered. That
is the whole point (it is where NB-3 lives) and it also means the Git subprocess in
rung 5 is never invoked in the single-WorkItem case, so the per-tool-call cost of the
`dirty_tree` hook is unchanged for the common repository.

#### D3 — Persisted active context

New file: **`workitems/.active-context.json`**, developer-local, gitignored.

```json
{ "workitem": "<id>", "branch": "<branch or null>", "setAt": "<UTC ISO>", "setBy": "<init|use|migrate-workflow>", "sdleVersion": "1.14" }
```

Chosen location because it is already inside the hook write fence (`FENCED` contains
`"workitems"`), already inside `SDLE_OWNED_PREFIXES`, needs no Git, and is naturally
per-worktree and per-clone since each is a distinct working directory. It cannot
collide with a WorkItem id: `cmd_workitem_create`'s uniqueness scan only considers
`child.is_dir()` (OBSERVED).

**Validity** (all must hold, else the rung is skipped — never a refusal):

- the file parses as a JSON object;
- `workitem` is a string present in `workitems/index.md`;
- `workitems/<id>/` exists and is a real directory (not a symlink);
- if `branch` is a non-null string **and** git is available **and** the current branch
  differs → INVALID (stale context).

Reading it **never raises**, mirroring `workitem_metadata`'s posture ("metadata is
descriptive, and a missing or unreadable file is not a refusal"). Cite that function.

**Write sites — exhaustive and closed:**

- `cmd_init`, after `save_state` succeeds;
- `cmd_migrate_workflow`, after the target `state.json` commit write;
- the new `sdle workitem use` command (and `workitem use --clear` to remove it).

**`workitem use` validates the id.** Because `workitem` is `RUNTIME_FREE`, `use` never
passes through `bind_workitem`, so nothing would otherwise check the id before it is
persisted. `workitem use` therefore performs rung 1's own check and refuses
`workitem_unknown` (exit 1, same reason and message shape as the explicit-flag rung) for
an id that is not in `workitems/index.md`. The alternative — `workitem_metadata`'s
"never raises, descriptive only" posture, letting an unregistered id persist and be made
inert by the validity rules — is rejected: persisting a context that can never bind is a
footgun with no upside. This is a deliberate choice between two real precedents in the
codebase, resolved here so no implementer has to pick mid-flight.

**Never written by:** `bind_workitem` (its documented purity is what lets
`.claude/hooks/hooks.py::dirty_tree` call it speculatively — a hook must not become a
writer), any hook, `workitem create`, or any read-only command. `workitem create`
deliberately does **not** persist context: if it did,
`test_rung5_two_workitems_and_no_flag_refuses_and_never_picks` would start silently
resolving, which is the exact failure mode §9 forbids.

#### D4 — Branch and starting SHA are recorded in `execution.json`

`write_execution_file` gains a `git` object:

```json
"git": { "branch": "<name or null>", "startSha": "<full sha or null>", "worktree": "<abs path or null>" }
```

populated with the existing `_git_value` posture (missing git is never a refusal;
detached HEAD records `branch: null`, matching `cmd_workitem_create`'s handling).

`execution.json` — not `state.json` — is the home, for three reasons: it is the
execution record, which is precisely what §9's "record branch and starting SHA" is
about; it carries no schema linting, so T03 needs **no** `workflow_version` bump, **no**
14th→15th `VERSION_MIGRATION` row, and **no** six-site version-string edit; and its test
asserts individual keys rather than a key set (OBSERVED), so nothing breaks.

`workitem.json` is deliberately **not** touched: `tests/test_units_workitem.py` asserts
`set(doc["git"]) == {"initialBranch"}` exactly (OBSERVED). Its existing
`git.initialBranch` is already a valid rung-5 signal.

#### D5 — Branch-mismatch policy (warn vs refuse), pinned

Mismatch is defined as: `execution.json.git.branch` is a non-null string, git is
available, and the current branch differs. Git absent, detached HEAD, a null recorded
branch, **or an absent `execution.json` entirely** (which is the case for a
legacy-bound runtime) → no mismatch, no warning, no refusal.

New module constant, enumerated here so it is not reinvented at implementation time:

```
BRANCH_CRITICAL_ACTIONS = {
    "advance",
    ("gate", "approve"),
    "skip",
    "restart",
    "reset",
    ("implement", "preflight"),
    ("manifest", "build"),
    ("drift", "rebaseline"),
    ("artifact", "record"),
}
```

Rationale for the split — these are the commands that either advance the lifecycle or
fingerprint working-tree content, so running them against the wrong checkout produces a
wrong-but-plausible record. Everything else (`state get`, `header`, `state dump`,
`gate show`, `gate reject`, `drift check`, `audit verify`, `doctor`, `workitem list`,
`workitem resolve`, `validate`, …) **warns**. `gate reject` is deliberately in the warn
set: a rejection can neither advance the workflow nor fingerprint an artifact as
approved, so refusing it would be pure obstruction.

**Refusal mechanism** — reuse the existing two-step idiom rather than invent a bypass
flag. On mismatch the guard:

- if `state["pending_confirm_action"] == "branch_mismatch"` → clear it, append an audit
  entry `branch_mismatch_accepted`, proceed;
- else → set `pending_confirm_action = "branch_mismatch"`, append audit
  `branch_mismatch_guard`, `save_state`, and refuse `branch_mismatch` (exit 1) with
  `data = {"recorded": …, "current": …, "workitem": …, "action": …}`.

`CONFIRMABLE` gains `"branch_mismatch"` (sixth member).

**Known interaction, deliberately accepted and tested:** `skip` and `reset` already use
`pending_confirm_action` for their own confirmations. The branch guard runs **first**,
so on a mismatched branch those two commands need *two* acknowledgements: one for the
branch, then one for the command. Running the guard after the command's own confirm
check would create a livelock (the command's check clears the pending marker, the guard
then sets its own, and the command's check never passes). This ordering and its
two-acknowledgement consequence must be tested, not discovered.

**Warning surface** — a warning must be explicit but must not break assertions:

- `cmd_header` gains an **additive** `data` key `branch_mismatch`
  (`null` when fine, else `{"recorded": …, "current": …}`) plus one extra stderr line
  when mismatched. The `rendered` string is **not** changed —
  `test_header_maps_every_status_to_its_display_text` asserts
  `rendered.endswith(display)` (OBSERVED).
- `sdle validate` reports it as a `warning`-class finding.

#### D6 — `sdle workitem resolve` (diagnostic, never refuses)

New subcommand inside the already-`RUNTIME_FREE` `workitem` group, so
`RUNTIME_FREE_COMMANDS` needs no edit for it. It runs the same ladder in a **reporting**
posture and always exits 0:

```json
{ "resolved": "<id>|null",
  "rung": "explicit|cwd|sole|context|branch|legacy|null",
  "reason": "null|ambiguous|none|unregistered_directory",
  "candidates": [ { "id": "wi-a", "evidence": ["branch:feat-a", "context"] } ],
  "launch_cwd": "…", "project_root": "…", "branch": "…" }
```

This is the **only** input the prompt layer gets for §9 rungs 5 and 6. The engine never
performs inference and never returns an inferred answer.

#### D7 — §9 rungs 5 and 6 live in the parent session, and rung 5 is never a resolver

CLAUDE.md invariant 8 ("gates stay in the parent") and §9's absolute ambiguity rule
together fix the design:

- **Rung 5, AI-assisted inference, is a presentation aid for rung 6 — never an
  independent resolver.** It may only *rank and annotate* the candidate list that
  `workitem resolve` returned. An inference that executes without the user confirming it
  is a silent pick wearing a different hat, and §9 forbids that in absolute terms.
- **Rung 6, ask user, is a question in the parent conversation.** It must never be
  delegated to a subagent (invariant 8), and the answer re-enters the engine as an
  explicit `--workitem <id>` — i.e. as rung 1 — optionally followed by
  `workitem use --workitem <id>` to persist it.

This is prompt-layer text in `SKILL.md` Step 1 and `.claude/commands/sdle-start.md`. No
engine change implements rung 5 or rung 6.

#### D8 — `sdle validate` (new top-level command, §9 "Add validation")

New top-level subcommand; `RUNTIME_FREE_COMMANDS` gains `"validate"` (sixth member), so
it can run in exactly the broken repositories it exists to diagnose. It attempts
resolution **speculatively**: if the ladder binds, active-scoped checks run; if the
ladder refuses, that refusal becomes a finding and active-scoped checks are skipped.
`validate` never refuses because resolution refused.

Findings, each `{ "check": …, "severity": "error"|"warning", "workitem": …, "detail": …, "path": … }`:

| § 9 check | Concrete rule | Severity |
|---|---|---|
| duplicate WorkItem IDs | two index rows whose `WorkItem` cells are equal case-insensitively | error |
| indexed WorkItem missing directory | index row with no `workitems/<id>/` directory | error |
| directory missing index entry | `workitems/<x>/` is a directory (dotfiles and `index.md` skipped) with no index row | error |
| malformed metadata | `workitem.json` absent, unparseable, not a JSON object, or its `id` ≠ its directory name | error |
| branch mismatch | active context's `branch`, or any WorkItem's `execution.json.git.branch`, differs from the current branch | warning |
| runtime state outside active WorkItem — (a) | `workitems/<x>/.sdle/state.json` where `<x>` is unregistered | error |
| runtime state outside active WorkItem — (b) | a `state.json` whose `workitem` field disagrees with the directory it sits in. The v1.14 migration row already anticipates this: *"this field is what makes a state file self-describing and a misplaced one detectable"* (`SKILL.md`, `VERSION_MIGRATION` row `1.13 → 1.14`) | error |
| runtime state outside active WorkItem — (c) | legacy `.workflow/state.json` present while ≥1 WorkItem is registered | warning |
| path traversal / symlink escape | `workitems/<x>` is a symlink, or `(root / x).resolve().parent != root.resolve()`, or an index id fails `WORKITEM_ID_RE` | error |

Exit contract: any `error` → `IntegrityError("workitem_validation_failed", …)` → **exit
3**, findings in `data.findings`. Warnings only, or clean → **exit 0** with the same
`data.findings` shape. A structurally corrupt registry still surfaces as
`read_index`'s existing `index_malformed` IntegrityError (also exit 3) — declared, not
worked around.

If git is unavailable every branch check is skipped, never failed
(`_git_value`'s existing posture).

#### D9 — NB-3: the dirty-tree tripwire is restored

Because rungs 2, 4 and 5 live **inside `bind_workitem`**, the hook inherits them with
**zero edits to `.claude/hooks/hooks.py`**. The hook passes `str(PROJECT_DIR)` as the
project root, so its `launch_cwd` is the project directory and rung 2 does not fire for
it; restoration comes specifically from rungs 4 (persisted context) and 5 (unique
branch). The fail-safe posture is preserved exactly: when nothing resolves, the hook is
still silent.

#### D10 — `sdle start --workitem <name>`

§9's "Explicit CLI override" is already satisfied: T02 shipped a global `--workitem`
that binds at rung 1, and `init` is SDLE's start command. §22 is explicitly labelled
"conceptually" and says "Do not redesign the entire CLI in one phase." T03 therefore
adds **no** `start` alias. This is an INFERRED interpretation, recorded so a verifier
does not read it as a missing deliverable.

### Preserved invariants

| # | Invariant | How T03 preserves it |
|---|---|---|
| P1 | **§9's ambiguity rule is absolute** — `0 → create/ask`, `1 → use`, `>1 → ASK`. Never silently pick. | New rungs only ever *add* a way to reach exactly one candidate. Every new rung applies the same 0/1/>1 test; >1 falls through to `workitem_ambiguous`. No rung has a tie-break, an ordering heuristic, a "most recent" rule, or a default. |
| P2 | T02's refuse-over-guess ladder is unweakened. | `workitem_required`, `workitem_ambiguous`, `workitem_unknown` and `legacy_workflow_present` keep their reasons, exit codes and trigger conditions. T03 adds one refusal (`workitem_unregistered`) and removes none. |
| P3 | CLAUDE.md invariant 8 — gates stay in the parent. | Rungs 5 and 6 are prompt-layer only, in the parent session; no subagent may hold them. The engine cannot ask and does not infer. |
| P4 | CLAUDE.md invariant 6 — single writer. | The active-context file is under `workitems/`, already inside the hook write fence and `SDLE_OWNED_PREFIXES`. Only `sdle.py` writes it. |
| P5 | `bind_workitem` stays pure — no writes, no printing. | Context persistence happens only in the three enumerated command handlers. `dirty_tree` can still call `bind_workitem` speculatively. |
| P6 | Exit-code contract: 0 success · 1 refused · 2 usage · 3 integrity. | `branch_mismatch` and `workitem_unregistered` are refusals (1). `validate` errors are integrity (3). No new exit code. |
| P7 | JSON on stdout, human text on stderr. | All new commands emit through `emit`. The branch warning adds a stderr line and an additive `data` key; `rendered` is untouched. |
| P8 | SpecKit opacity. | T03 touches no `speckit-*` name and no `/speckit.*` command. |
| P9 | One source of truth per fact. | No constant table is duplicated. `BRANCH_CRITICAL_ACTIONS` and the context schema live in `sdle.py` only; prompt files reference behaviour, never restate the membership list. |
| P10 | Legacy `.workflow/` dual-read and `migrate-workflow` keep working. | Rung 6 (legacy) is unchanged and still gated on zero registered WorkItems. `migrate-workflow` still never writes, renames or deletes anything under `.workflow/`. Their removal is **T11's**. |
| P11 | No `workflow_version` bump. | T03 adds no `state.json` field, so `CURRENT_VERSION` stays `1.14`, `VERSION_MIGRATION` stays at 14 rows, and `version_string_consistent` / `migration_covers_every_state_field` stay PASS with zero edits. |
| P12 | Fail safe — freeze, never advance. | Every new failure path refuses or stays silent. No new path advances a phase. |
| P13 | No distributed locking (§9). | T03 adds no lock, no lease, no cross-worktree coordination. The per-WorkItem lock from T02 is untouched. |

---

## Files expected to change

Cited by symbol or anchor string. Line numbers are deliberately omitted.

### Product — engine

| File | Change |
|---|---|
| `scripts/sdle.py` — `class Paths` | add field `launch_cwd: Path \| None = None` |
| `scripts/sdle.py` — `def resolve_paths` | marker-based upward walk (D1); populate `launch_cwd` |
| `scripts/sdle.py` — new helpers near `def bind_workitem` | `active_context_file`, `read_active_context`, `write_active_context`, `clear_active_context`, `current_branch`, `branch_candidates`, `cwd_workitem` |
| `scripts/sdle.py` — `def bind_workitem` | new rungs 2, 4, 5 in the D2 order; add `candidates` to the `workitem_ambiguous` payload (keep the existing `workitems` key — a test asserts it) |
| `scripts/sdle.py` — `RUNTIME_FREE_COMMANDS` | add `"validate"` |
| `scripts/sdle.py` — `def write_execution_file` | add the `git` object (D4) |
| `scripts/sdle.py` — `def cmd_init` | persist active context after `save_state` |
| `scripts/sdle.py` — `def cmd_migrate_workflow` | persist active context after the commit write (strictly after, so a crash never leaves a context pointing at a non-authoritative runtime) |
| `scripts/sdle.py` — new `cmd_workitem_resolve`, `cmd_workitem_use` | D6, D3 |
| `scripts/sdle.py` — new `cmd_validate` | D8 |
| `scripts/sdle.py` — new `BRANCH_CRITICAL_ACTIONS`, `branch_guard()` | D5; call at the top of each enumerated handler |
| `scripts/sdle.py` — `CONFIRMABLE` | add `"branch_mismatch"` |
| `scripts/sdle.py` — `def cmd_header` | additive `branch_mismatch` data key + stderr line |
| `scripts/sdle.py` — `def build_parser` | register `validate`, `workitem resolve`, `workitem use`. For `workitem use`, follow the existing `migrate-workflow` precedent exactly: a subparser `--workitem` with a distinct `dest` (`use_workitem`), read as `getattr(args, "use_workitem", None) or args.workitem`, because argparse would otherwise clobber the global value |

### Product — configuration and guardrails

| File | Change |
|---|---|
| `.gitignore` | add `workitems/.active-context.json`. Load-bearing: without it the file would be committed and would land in the Phase-17 security-review diff (the diff excludes only `runtime_relative`, OBSERVED) |
| `.claude/hooks/hooks.py` | **no change** — this is the point of D9 |
| `.claude/settings.json` | **no change** |

### Product — prompt and documentation layer

| File | Anchor / change |
|---|---|
| `.claude/skills/sdle/SKILL.md` | Step 1, the paragraph beginning **"Then initialise with"** — rewrite the ladder sentence for the D2 order; add the rung-5/rung-6 rule of D7 (present candidates, ask, never pick, never delegate); add the branch-mismatch behaviour. Also the paragraph beginning **"Identity comes before initialisation."** — after `workitem create`, always pass `--workitem <id>` to `init`. **No constant table, no version string, no phase/gate table may be touched.** |
| `.claude/commands/sdle-start.md` | the numbered step mentioning `sdle.sh workitem create --name` — same ladder/ask guidance, invocation only, no restated constants |
| `README.md` | the ladder bullet ending **"and no WorkItem is registered (transitional — see `migrate-workflow`);"** and the sentence **"`lint-skill`, `sha`, `constants`, `workitem` and `migrate-workflow` touch no"** (now six members) |
| `docs/SDLE-Reference-Guide.md` | the same runtime-free sentence anchor, plus the artifact table row block near **"`workitems/<id>/.sdle/execution.json`"** for the new `git` object and the new `workitems/.active-context.json` row |
| `CLAUDE.md` | the sentence **"only `workitems/*/.sdle/lock` is ignored"** — now also the active-context file. `CLAUDE.md` is not in the guard's `CONTROL_PREFIXES`, so the implementer may edit it |

### Tests

| File | Change |
|---|---|
| `tests/test_units_workitem_resolution.py` | **new file** — the whole §9 matrix, the branch policy, `validate`, `workitem resolve`/`use`, and the worktree exit criterion |
| `tests/test_hooks.py` | one superseded test (see below) |
| `tests/test_units_workitem_runtime.py` | add `("validate",)` to the `test_runtime_free_commands_need_no_workitem` parametrize list (additive coverage) |
| `tests/conftest.py` | **exactly one** permitted edit: add `workitems/.active-context.json` to the `.gitignore` string written by `init_git`, whose comment already says *"Mirrors the shipped .gitignore"*. **No fixture semantics may change.** |

> **Explicit anti-contradiction clause (T02 process lesson 1).** The shared fixtures
> `bare_project`, `project`, `started`, `git_project`, `started_git` and
> `isolated_git_identity` **must not change**, and `Project`'s methods
> (`run`, `run_cli`, `ok`, `as_workitem`, `runtime`, …) **must not change**. Every new
> helper — CWD-relative launcher, worktree builder, active-context writer — lives in
> the new test file, which imports what it needs via `from conftest import …` exactly
> as `test_units_workitem_runtime.py` already does (OBSERVED). The `init_git`
> `.gitignore` line is the single, named exception, and it is a mirror of a product
> file, not a behavioural change; no test asserts `.gitignore` content (OBSERVED).

---

## Existing tests affected

Full sweep performed in this context: `grep -rn "create_wi|workitem\", \"create|as_workitem" tests/*.py`,
`grep -rn "workitem_ambiguous|workitem_required" tests/*.py`, `grep -rn "gitignore" tests/*.py`,
`grep -rn "iterdir|glob(" tests/*.py` (no hits — **no test asserts a `workitems/`
directory listing**, so the new dotfile cannot break one).

**Expected modified-test set — exactly one test, plus two additive edits:**

| Test | Why | TP-003 category |
|---|---|---|
| `tests/test_hooks.py::test_dirty_tree_is_silent_when_the_workitem_is_ambiguous` | Uses the `started` fixture, so `init` has now persisted an active context; with a second WorkItem created afterwards the hook **resolves via rung 4** and fires. Its premise is genuinely superseded — this *is* NB-3 being closed. Rewrite it as three assertions: fires with a valid context; silent with the context cleared; silent when the context is branch-invalidated. The strengthened form must keep proving the fail-safe posture. | **2 — genuinely superseded behaviour** |
| `tests/test_units_workitem_runtime.py::test_runtime_free_commands_need_no_workitem` | one parametrize row added for `validate` | **additive coverage, not a modification of an assertion** |
| `tests/conftest.py::Project.init_git` | one `.gitignore` line, mirroring the product `.gitignore` | **2 — mirrors a product configuration change** |

**Explicitly expected to stay byte-identical and green:** every rung test in
`test_units_workitem_runtime.py` (`test_rung1_*`, `test_rung2_*`, `test_rung3_*`,
`test_rung4_*`, `test_rung5_*`), `test_a_runtime_command_still_refuses_in_that_same_repository`,
`test_init_never_takes_the_legacy_rung`, every `migrate-workflow` test, every crash
test, `test_execution_identity_is_written_at_init_and_is_not_the_workitem`,
`test_implement_preflight_does_not_count_the_workitem_tree_as_dirt`,
`test_the_phase_17_diff_excludes_the_workitem_runtime`, all 57 cases in
`test_units_workitem.py`, and all nine dry-run integration transcripts.

**No test may be weakened, skipped, xfailed or deleted.** The suite is green today, so
the acceptance bar is: **341 + N collected, 341 + N passed, raw exit 0, zero skips.**

---

## New tests required

All in `tests/test_units_workitem_resolution.py` unless stated.

### N1 — the §9 resolution matrix, verbatim

One test per row of the contract's table, named after it:

| CWD | WorkItems | Git signal | Expected |
|---|---:|---|---|
| inside WI-A | many | irrelevant | binds WI-A |
| `workitems/` | one active | match | selects it |
| `workitems/` | many plausible | none | refuses `workitem_ambiguous`, lists candidates, writes nothing |
| repo root | branch maps WI-A | unique | binds WI-A |
| repo root | ambiguous | mixed | refuses `workitem_ambiguous` |
| nested source dir | unique persisted context | valid | selects it |
| nested source dir | none | none | refuses `workitem_required` (the engine half of "create/ask"; the ask half is prompt-layer) |

### N2 — repo-root discovery (D1)

Launch (via `monkeypatch.chdir`, no `--project-root`) from each of §9's four locations —
`workitems/<wi>/`, `workitems/`, repository root, and a nested `src/deep/` — and assert
the same `project_root` is resolved each time. Plus: `--project-root` still overrides
CWD; a directory with no marker still resolves to itself (today's behaviour preserved).

### N3 — rung 2 never falls through

CWD inside `workitems/<x>/` where `<x>` exists on disk but is absent from `index.md`,
with two other WorkItems registered → refuses `workitem_unregistered`, and **does not**
bind either registered WorkItem. This is the anti-silent-pick test for the new rung.

### N4 — active context lifecycle (D3)

- `workitem create` does **not** write a context (assert the file is absent).
- `init` writes one; `workitem use --workitem <id>` rewrites it; `--clear` removes it.
- `workitem use --workitem <unregistered-id>` refuses `workitem_unknown` (exit 1) and
  leaves any existing context file byte-unchanged.
- Invalid contexts are skipped, never fatal: unparseable JSON, unregistered id, missing
  directory, and branch-stale — each with two WorkItems registered, each falling through
  to `workitem_ambiguous`.
- `bind_workitem` is proven **pure**: with two WorkItems and no context, capture a
  recursive SHA map of the repository, call `bind_workitem` in every reachable state
  (bind, refuse, legacy), and assert the map is unchanged and stdout/stderr are empty.

### N5 — branch rung (D2 rung 5)

Two WorkItems `init`-ed on two branches; check out one → binds that one with no flag.
Check out a third branch matching neither → `workitem_ambiguous`. Two WorkItems created
on the *same* branch → `workitem_ambiguous` (the >1 case must not tie-break). Detached
HEAD and a repository with no git → rung skipped, still `workitem_ambiguous`.

### N6 — branch/SHA recorded (D4)

`execution.json` carries `git.branch` and `git.startSha`; `startSha` equals HEAD at
`init`; no-git and detached-HEAD both record `null` without refusing; `workitem.json`'s
`git` object still has exactly `{"initialBranch"}` (a regression pin for the
exact-key assertion).

### N7 — branch-mismatch policy (D5)

- Each member of `BRANCH_CRITICAL_ACTIONS` refuses `branch_mismatch` on a mismatched
  branch, changes no phase and records no approval; the audit gains
  `branch_mismatch_guard`.
- A representative advisory command (`state get`) succeeds; `header` reports the
  mismatch in `data.branch_mismatch` while `rendered` is byte-identical to the
  matched-branch case.
- The two-step: re-running the same command after the refusal proceeds and audits
  `branch_mismatch_accepted`.
- **The declared double-acknowledgement:** `skip` on a mismatched branch needs the
  branch confirmation *and then* its own `skip` confirmation. Pin the exact sequence so
  it can never silently become a single-step bypass.
- No mismatch when git is absent, HEAD is detached, or the recorded branch is null.

### N8 — `workitem resolve` (D6)

Always exit 0. Reports the bound id and rung for each rung. On ambiguity reports
`resolved: null`, `reason: "ambiguous"` and a candidate list with per-candidate
evidence. It **never** returns an inferred pick and never writes.

### N9 — `sdle validate` (D8)

One case per row of the D8 table, each asserting `check`, `severity` and exit code;
plus a clean repository → exit 0 with an empty `findings`; plus a warnings-only
repository → exit 0 with findings; plus `validate` running successfully in an
*ambiguous* repository (it must diagnose the repositories it cannot resolve).
Symlink case: skip-free — construct it with `os.symlink` and, on a Windows host without
the privilege, assert on the `resolve()`-based escape check instead of skipping, so the
suite keeps zero skips.

### N10 — NB-3 restoration (D9), in `tests/test_hooks.py`

The rewritten `test_dirty_tree_is_silent_when_the_workitem_is_ambiguous`, per the table
in "Existing tests affected": fires with two WorkItems and a valid context; silent with
two WorkItems and no context; silent when the context is branch-invalidated. Assert
`.claude/hooks/hooks.py` needed no change by leaving it untouched in the diff.

### N11 — §9 exit criterion, worktree-shaped

Build one scratch repository, register WI-A and WI-B, commit, then
`git worktree add` a second working directory on a second branch. Set a distinct
persisted context in each. Run a full lifecycle step in each **without** `--workitem`
and assert: each resolves its own WorkItem; each writes only its own
`workitems/<id>/.sdle/`; the other's `state.json` and `audit.md` are byte-unchanged;
each has its own `lock`; no repository-global `.workflow/` is created. If
`git worktree add` fails, the test **fails loudly** — it must never skip, because the
suite already depends hard on git.

### N12 — no fail-open

Grep-style structural assertions, in the spirit of T02's fail-open hunt: every new rung
returns either a single id or falls through; `RUNTIME_FREE_COMMANDS` is still a closed,
enumerated set (now six); no new code path calls `dataclass_replace(paths, workitem=…)`
outside `bind_workitem` and the explicit `--workitem`/`migrate-workflow` sites.

---

## Failure modes

| # | Failure mode | Detection | Mitigation |
|---|---|---|---|
| F1 | **A new rung becomes a silent pick.** The single worst outcome — it breaks §9's absolute rule and T02's verified guarantee. | N1, N3, N5, N8, N12 | Every rung computes a candidate *set* and applies 0/1/>1 uniformly. No tie-break, no ordering preference, no "most recent". Code review checklist: any `[0]`, `min(`, `max(`, `sorted(...)[0]` on a candidate list is a defect. |
| F2 | **`bind_workitem` stops being pure**, e.g. context is persisted inside resolution, so the `dirty_tree` hook becomes a writer and can corrupt state from a PreToolUse callback. | N4's purity test (recursive SHA map + empty stdout/stderr) | The three write sites are enumerated and closed in D3. |
| F3 | **Repo-root discovery walks too far up** and binds a parent repository's `workitems/`, silently operating on the wrong project. | N2 | Nearest-ancestor-wins, markers tested in a fixed order at each level, and `--project-root`/`SDLE_PROJECT_ROOT` always override. |
| F4 | **The plan contradicts itself around shared fixtures** (the T02 §6-vs-§7.1 failure). | implementer's first full-suite run | The anti-contradiction clause names the single permitted `conftest.py` edit and forbids all others; new helpers live in the new test file. |
| F5 | **The branch guard livelocks or is bypassed** on `skip`/`reset` because of the shared `pending_confirm_action` key. | N7's explicit double-acknowledgement test | Guard runs first, by design, with the consequence stated and pinned. |
| F6 | **Blocking a legitimate developer.** An over-broad refusal set makes routine work impossible. | N7's advisory-command cases | `BRANCH_CRITICAL_ACTIONS` is nine enumerated entries; everything else warns. The two-step acknowledgement is always available. |
| F7 | **The active-context file gets committed**, so two developers silently share an active WorkItem. | N11 (worktree isolation) | `.gitignore` entry + mirrored `conftest.init_git` line, both named as load-bearing in "Files expected to change". |
| F8 | **`validate` crashes on the broken repositories it is meant to diagnose.** | N9's ambiguous-repository case | Speculative resolution; every filesystem read defensive; the one declared exception is `index_malformed`, which is itself a correct exit-3 diagnosis. |
| F9 | **A `git` subprocess on every PreToolUse hook call** makes the editor feel slow. | manual timing during implementation | The rung order guarantees git is consulted only when ≥2 WorkItems are registered; single-WorkItem repositories are unaffected. |
| F10 | **Silent regression in `lint-skill`** from prompt-file edits. | `lint-skill` after every prompt edit (T02's practice) | No constant table, version string, phase table or gate table is touched. Watch `no_powershell_only_cmdlets` for any embedded command added to a prompt file. |
| F11 | **Future-phase leakage** — creating a repo-level `.sdle/` (T05), moving Spec Kit artifacts (T04), or deleting `.workflow/` support (T11). | acceptance A15 | The active context is at `workitems/.active-context.json`, deliberately *not* `.sdle/`. |
| F12 | **A suite failure is misclassified as a flake.** | — | **The F1 `ENVIRONMENT_FLAKE` procedure is VOID.** The pre-T03 suite is `341 passed`, raw exit 0 (OBSERVED). Every failure is a presumed T03 regression and must be investigated. Do not patch `write_atomic`. |
| F13 | **Windows symlink privilege** makes the traversal test unrunnable. | N9 | Assert on the `resolve()`-based escape check rather than skipping; the suite must keep zero skips. |

---

## Rollback/recovery strategy

- **Rollback point: `ab889a1`** (T02 implementation). `ab889a1..HEAD` is control-plane
  only (OBSERVED), so reverting T03's product commit restores a state whose suite is
  known green at 341 passed.
- **Milestones and checkpoints.** Eight milestones (below); persist
  `docs/transition/phases/T03-checkpoint-a01-NN.md` after each, so an interrupted fresh
  agent resumes from disk plus `git diff`.
- **M1 is the structural proof**, mirroring T02's M1: land D1 (repo-root discovery +
  `launch_cwd`) with **zero test edits** and the full suite still at 341 passed / raw
  exit 0. If M1 cannot be landed without touching a test, the seam is wrong — stop and
  re-plan rather than editing tests.

| M | Content |
|---|---|
| M1 | D1 — `launch_cwd`, marker walk. **Zero test edits. 341 passed, raw exit 0.** |
| M2 | D3 — active-context helpers, `workitem use`, persistence at `init`/`migrate-workflow`, `.gitignore` + `conftest.init_git` mirror line |
| M3 | D2 — the new rungs inside `bind_workitem`, `workitem_unregistered`, candidate evidence in `workitem_ambiguous` |
| M4 | D6 — `workitem resolve` |
| M5 | D4 — `execution.json` git block; D5's header warning key |
| M6 | D5 — `BRANCH_CRITICAL_ACTIONS`, `branch_guard`, `CONFIRMABLE` |
| M7 | D8 — `sdle validate` |
| M8 | D7/D9 — prompt and documentation layer, NB-3 test rewrite, N11 worktree test, full sweep |

**Per-failure recovery:** a red suite at any milestone reverts that milestone only —
each is a separate concern with no forward dependency except M3 on M1/M2 and M6 on M5.

**Data recovery for a user:** the active-context file is disposable. `workitem use
--clear` (or deleting `workitems/.active-context.json`) returns resolution to T02
behaviour exactly. No migration, no schema change, no state rewrite — so T03 has **no
irreversible data effect whatsoever**.

---

## Acceptance criteria

Objective, each checkable by a named command or test.

- [ ] **A1** Full suite: `341 + N` collected and `341 + N` passed, **raw exit 0**, zero
      skips/xfails/errors (`pytest -q -rsxX` produces no short-summary section).
      `N` = the number of new tests; collected must equal passed.
- [ ] **A2** `python scripts/sdle.py lint-skill` — raw exit 0, **22 PASS / 0 FAIL**,
      still reporting 19 phases / 8 gates / **14** migration rows and v1.14 at all four
      locations.
- [ ] **A3** `python tools/transition/validate.py` — raw exit 0.
- [ ] **A4** `git diff --exit-code ab889a1 -- .claude/hooks/hooks.py .claude/settings.json .claude/skills/sdle/templates/state.json .claude/skills/sdle/modules/ scripts/sdle.sh scripts/sdle.ps1 .github/ requirements/ docs/dry-runs/` returns **0** — none of these may change.
- [ ] **A5** `CURRENT_VERSION` is still `"1.14"`; `VERSION_MIGRATION` still has 14 rows;
      `templates/state.json` is byte-identical to `ab889a1`; no new `state.json` field.
- [ ] **A6** Every §9 matrix row (N1) passes, and each ambiguous row asserts that
      **nothing was written** (no `.sdle/`, no `.workflow/`, no state file).
- [ ] **A7** All four §9 launch locations resolve the same `project_root` (N2), and
      `--project-root` still overrides.
- [ ] **A8** CWD inside an unregistered WorkItem directory refuses
      `workitem_unregistered` and binds nothing (N3).
- [ ] **A9** `bind_workitem` purity: a recursive SHA map of the repository is unchanged
      across bind, refuse and legacy paths, and stdout/stderr are empty (N4).
- [ ] **A10** `workitem create` writes no active context; `init`, `workitem use` and
      `migrate-workflow` do; every invalid-context variant falls through instead of
      failing (N4).
- [ ] **A11** `execution.json` records `git.branch` and `git.startSha`; `startSha` equals
      HEAD at `init`; no-git and detached-HEAD record `null` without refusing; and
      `set(doc["git"]) == {"initialBranch"}` still holds for `workitem.json` (N6).
- [ ] **A12** Each of the nine `BRANCH_CRITICAL_ACTIONS` refuses `branch_mismatch`
      (exit 1) on a mismatched branch and changes no phase; a representative advisory
      command succeeds; `header`'s `rendered` is byte-identical to the matched-branch
      case while `data.branch_mismatch` is populated; the two-step acknowledgement works;
      the `skip` double-acknowledgement sequence is pinned (N7).
- [ ] **A13** `sdle workitem resolve` always exits 0, reports the rung when it resolves,
      and on ambiguity returns `resolved: null` plus a candidate list — never a pick
      (N8).
- [ ] **A14** `sdle validate` produces one finding per D8 rule with the stated severity;
      any `error` → exit **3**, warnings-only or clean → exit **0**; it runs
      successfully in an ambiguous repository (N9).
- [ ] **A15** **NB-3 closed:** in a two-WorkItem repository the dirty-tree hook **fires**
      with a valid persisted context, **stays silent** with no context, and **stays
      silent** when the context is branch-invalidated — with
      `.claude/hooks/hooks.py` byte-identical to `ab889a1` (N10, and A4 covers the file).
- [ ] **A16** **§9 exit criterion:** two `git worktree`s of one repository each drive a
      different WorkItem with **no** `--workitem` flag, writing only their own runtime,
      leaving the other's `state.json` and `audit.md` byte-unchanged, with per-WorkItem
      locks and no repository-global `.workflow/` (N11).
- [ ] **A17** TP-003 compliance: `git diff --name-status ab889a1 -- tests/` shows exactly
      one `A` (the new file `tests/test_units_workitem_resolution.py`) and exactly
      **three** `M` — `tests/test_hooks.py`, `tests/test_units_workitem_runtime.py` and
      `tests/conftest.py` — and no `D`; and
      `git diff ab889a1 -- tests/ | grep -E "^\+.*(skip|xfail)"` returns **only** matches
      that are not pytest markers (the implementer must classify every line it returns —
      T02's NB-6 records that this grep returns a `--skip-tests` CLI flag line, so
      "empty" is the wrong bar; "every returned line classified and none a marker" is the
      right one).
- [ ] **A18** No future-phase leakage: `grep -rn "\.sdle/policies\|baseline\.\|risk\|classification\|flow_type\|subagent" scripts/sdle.py` shows no T05+ concept introduced by this diff; no repository-root `.sdle/` directory is created; `resolve_artifact_path`'s transitional `.workflow/` prefix bridge is **left in place** (NB-1 is T04's to delete).
- [ ] **A19** Legacy support intact: every `migrate-workflow` test still passes, rung 6
      still binds a legacy runtime when zero WorkItems are registered, and
      `.workflow/` is still never written, renamed or deleted.
- [ ] **A20** Python 3.11 and CI are recorded as **NOT_RUN / UNKNOWN**. **No outcome may
      be predicted.** T03 is standard-library-only and 3.11-safe by construction
      (no new syntax beyond what `sdle.py` already uses).

---

## Unknowns / decision requirements

**No material unresolved decision exists. This phase is PLANNED, not BLOCKED.**
Every item below is either resolved by this plan under contract latitude, or is a
recorded unknown that cannot invalidate the design.

| # | Item | Class | Disposition |
|---|---|---|---|
| U1 | CI on `ubuntu-latest` / `windows-latest`, Python 3.11 | UNKNOWN / NOT_RUN | The branch has never been pushed and this host has one interpreter. Inherited from T00–T02. No outcome predicted. T03 adds no new dependency and no version-gated syntax. |
| U2 | Exact `git` version on CI runners, hence `git worktree` behaviour | INFERRED | `worktree` has shipped since git 2.5 (2015) and the suite already hard-depends on git. N11 fails loudly rather than skipping, so a surprise is visible, not silent. |
| U3 | Windows symlink creation privilege for the traversal test | UNKNOWN | Handled inside N9 without a skip (F13). |
| U4 | Placement of "sole registered" at rung 3 rather than following §9's literal order | INFERRED | Justified in D2 as §9's own `1 valid candidate -> use`, and required to avoid regressing T02's rung-2 test. Recorded so a verifier judges the reconciliation rather than re-deriving it. |
| U5 | `sdle start` alias | INFERRED | Not added; D10 gives the reasoning. §22 is labelled "conceptually". |
| U6 | Whether the branch-mismatch refusal set is exactly right | INFERRED | Enumerated in D5 with per-command rationale. Contract says "warning/refusal depending on safety impact" and gives no list; this is the latitude being exercised, and the membership is one constant, trivially adjustable later. |
| U7 | Whether `validate` should be `sdle validate` or `sdle workitem validate` | INFERRED | §22 lists both; §9 names `sdle validate` in the "Add validation" section, so that is what T03 ships. A `workitem validate` alias is deliberately not added (one entry point per fact, invariant 7). |
| U8 | Long-term home of the active context once T05 creates a repo-level `.sdle/` | UNKNOWN, T05's | Deliberately parked at `workitems/.active-context.json` to avoid pre-empting T05. Moving it later is a one-constant change plus a `.gitignore` line. |

---

## Scope exclusions

The following must **not** appear in the T03 diff. Each is a later phase's work.

1. **T04 — Spec Kit binding.** No `ARTIFACT_OWNERSHIP` table edit, no move of
   `.specify/`, `design/`, `reviews/` or `clarifications/` under `workitems/`, and **no
   removal of the transitional `.workflow/` prefix bridge in `resolve_artifact_path`** —
   NB-1 is explicitly T04's to delete, not T03's to inherit or fix.
2. **T05 — repository `.sdle/` configuration boundary.** No repository-root `.sdle/`
   directory, no `policies/`, no `baseline.*`, no policy format.
3. **T06 — requirements quality, classification, hybrid risk.** No Requirements Quality
   Gate, no WorkItem type taxonomy beyond the free-text `type` T01 already stores, no
   risk scoring.
4. **T07 — declarative flow selection.** The 19-phase sequence and its four constant
   tables are untouched.
5. **T08 — brownfield discovery.** No discovery, no baseline capture.
6. **T09 — risk-adaptive gates.** All eight gates keep their current, fixed behaviour.
7. **T10 — skills and subagents.** No subagent, no skill split. In particular rung 6
   (ask user) stays in the parent session (invariant 8) and must not be prepared for
   delegation.
8. **T11 — legacy removal and hardening.** The legacy `.workflow/` dual-read rung and
   `migrate-workflow` must keep working exactly as T02 shipped them; T03 removes
   neither. NB-2 (the incomplete `legacy_workflow_present` remedy message), NB-4
   (the post-commit `workitem.json` write outside the commit window) and NB-5 (crash
   coverage of the optional copies) are **T11's**, not T03's.
9. **Out of scope entirely:** NB-7 (a stray word in `6e8af8c`'s `write_atomic` comment),
   `.claude/settings.local.json` (the user's permission allowlist), and any change to
   `write_atomic` itself.
10. **Contract immutability.** `docs/transition/transition.md`, `docs/transition/templates/`,
    `tools/transition/` and every prior phase's plan, handoff, checkpoint and
    verification are read-only for this phase.
