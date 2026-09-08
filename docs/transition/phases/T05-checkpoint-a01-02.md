# T05 Implementation Checkpoint — Attempt a01 / Checkpoint 02

**Phase:** T05 — Introduce Repository-Level `.sdle/` Configuration Boundary
**Attempt:** 01

## Objective currently being worked

Milestones **M2**, **M3** and **M4** of `docs/transition/phases/T05-plan.md`:
the configuration model and the two `config` subcommands, the bidirectional leak
detector, and the two phase-level proofs (N10 differential, N11 containment).

## Completed since previous checkpoint

**M2 — configuration model and CLI.**

- `REPO_CONFIG_DEFAULTS = {"configVersion": "1", "policyFormat": "json"}`,
  `SUPPORTED_CONFIG_VERSIONS = ("1",)`, `SUPPORTED_POLICY_FORMATS = ("json",)`.
- `read_repo_config(paths)` — reader; defaults when absent, merged when present.
- `repo_config_findings(paths)` — the **single** soundness predicate, emitting
  `config_root_inside_workitem` and `config_malformed`.
- `_refuse_config_findings(findings, checks)` — shared refusal helper. It takes
  *findings*, not `Paths`, so it does not become a sixth function able to reach
  the boundary (N11 clause 1).
- `cmd_config_init` / `cmd_config_show`; a new `config` parser group placed
  immediately before `workitem`.
- `collect_validation_findings` gained block **8**, `findings.extend(repo_config_findings(paths))`.
- `"config"` added to `RUNTIME_FREE_COMMANDS`.
- **The one authorised existing-test edit**, and the only one:
  `tests/test_units_workitem_resolution.py::test_runtime_free_commands_is_a_closed_enumerated_set`
  gained the literal `"config"` inside the asserted frozenset. TP-003 category 2.

**M3 — the leak detector.**

- `workitem_runtime_member_names(bound)` — takes an **already bound** `Paths`, so
  it introduces no new `dataclass_replace(paths, workitem=…)` call site.
- `collect_validation_findings` gained block **9**: `lifecycle_state_in_repository_config`
  and `repository_config_in_workitem`, both name sets derived from `Paths`, the
  probe rebinding done inside `collect_validation_findings` (already a declared site).

**M4 — the phase-level proofs.** N10 differential and N11 containment, written
after the engine, plus two guard tests against vacuous passes.

**One divergence from the plan's literal wording, recorded here and in the handoff.**
N10 clause 2 (identical ordered audit events) fails if the configured project's
`.sdle/` is left **uncommitted**: `implement preflight` then sees an untracked
`.sdle/config.json`, because `SDLE_OWNED_PREFIXES` is deliberately **not**
extended, and audits `dirty_tree_bypassed`. That is the plan's own Unknowns §4
decision working as designed, not a lifecycle change: nothing *read* the
configuration. The differential test therefore commits `.sdle/` first — which is
the realistic state, since D7 versions it — and a separate new test
(`test_an_uncommitted_boundary_is_not_treated_as_sdle_owned`) pins the
uncommitted behaviour explicitly so the decision is evidenced rather than hidden.

## Remaining

- **M5** — the repository's own versioned `.sdle/` (via `config init` run here) +
  `docs/architecture/ADR-002-repository-configuration-boundary.md`, README,
  `docs/SDLE-Reference-Guide.md`, `CLAUDE.md`. Re-run `lint-skill` after **each**
  document edit (F7).
- **M6** — full suite, `lint-skill`, `validate.py`, the A1–A22 matrix, the
  handoff, `progress.md` → IMPLEMENTED.

## Files changed

```
M  scripts/sdle.py                            (+~380 lines, no deletions)
M  tests/test_units_workitem_resolution.py    (one literal + comment, +3 lines)
?? tests/test_units_repo_config.py            (new, 69 collected)
?? docs/transition/phases/T05-checkpoint-a01-01.md
?? docs/transition/phases/T05-checkpoint-a01-02.md
M  .claude/settings.local.json                (pre-existing, OUT OF SCOPE)
```

`scripts/sdle.py` was normalised back to LF in the working tree: the editing
tool had rewritten it as CRLF, and although `git diff` normalises via
`.gitattributes` (`* text=auto eol=lf`) and stayed at `+283/-0`, a CRLF working
copy would corrupt any byte-level A5/A7 comparison. `git ls-files --eol` now
reports `i/lf w/lf` for it.

## Tests actually run

| Command | Result |
|---|---|
| `rtk proxy "python -m pytest -q -p no:cacheprovider --collect-only <scratch>/baseline-bf4ba5e/tests"` | **500 tests collected** (pristine `git archive HEAD`) |
| `rtk proxy "python -m pytest -q -p no:cacheprovider -rsxX <scratch>/baseline-bf4ba5e/tests"` | **500 passed in 617.01s, RAW_EXIT=0**; `grep -c "short test summary"` over the captured run = **0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_repo_config.py tests/test_units_workitem_resolution.py"` (at M1) | **106 passed, RAW_EXIT=0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_workitem_resolution.py tests/test_units_workitem.py tests/test_units_cli.py"` (at M2) | **162 passed, RAW_EXIT=0** |
| `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_repo_config.py"` (at M4) | **69 passed in 51.51s, RAW_EXIT=0** |
| `rtk proxy "python scripts/sdle.py lint-skill"` | raw exit **0**, **22 PASS / 0 FAIL**, `Parsed 19 phases, 8 gates, 15 migration rows`, `all four locations report v1.15` |
| `rtk proxy "python tools/transition/validate.py"` | `TRANSITION_VALID: complete=5/12 next=T05`, raw exit **0** |
| Full suite at M2 snapshot | **IN FLIGHT** at the time of writing (background task `bhw6rlwz6`, ~53%). M6 re-runs the full suite against the final tree regardless. |
| Python 3.11 / CI | **NOT_RUN** / **UNKNOWN** — no 3.11 interpreter on this host, branch is local-only |

**Baseline method.** A first full-suite run in the working tree was **discarded,
not quoted**: several tests re-read `scripts/sdle.py` from disk at run time, so
an edit landing mid-run contaminates it. Baseline and milestone runs are taken
against pristine/snapshot copies under `<scratchpad>/`, created by
`git archive HEAD | tar -x` plus an overlay of changed and untracked files
(`<scratchpad>/snapshot.sh`), which leaves the real tree free for editing.

## Current failures

None. Every targeted run above is green.

## Git status / diff summary

- HEAD: `bf4ba5e1f52a893c3ef0247c173687268e5c546c` (`transition/workitem-v1`)
- Rollback point: `7b054ee`; product baseline `f8fdaa0`
- Nothing committed by this phase yet.
- `git diff --name-status 7b054ee -- tests/` at this checkpoint: exactly one `M`
  (`tests/test_units_workitem_resolution.py`) and one untracked `A`
  (`tests/test_units_repo_config.py`). Zero `D`, zero `R`. `tests/conftest.py`
  is byte-identical.

## Unresolved decisions

None. The N10 wording divergence above is recorded, not open.

## Exact resume instruction

1. Confirm on disk: `rtk proxy "grep -n 'REPO_CONFIG_DEFAULTS\|def cmd_config_init\|def cmd_config_show\|def repo_config_findings\|def workitem_runtime_member_names' scripts/sdle.py"`
   must show all five, and `rtk proxy "grep -n '\"config\"' scripts/sdle.py"` must
   show it inside `RUNTIME_FREE_COMMANDS`.
2. `rtk proxy "python -m pytest -q -p no:cacheprovider tests/test_units_repo_config.py"`
   must report **69 passed**.
3. Resume at **M5**: run `python scripts/sdle.py config init` at the repository
   root, then write ADR-002 and the four document edits, re-running `lint-skill`
   after each one.
4. Do **not** re-open any decision in the plan's "Unknowns" section, and do not
   make a second existing-test edit.
