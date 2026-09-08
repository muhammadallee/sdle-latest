# T03 checkpoint a01-06 — M8 (new test file, D7/D9 prompt and documentation layer)

**Phase:** T03 · **Attempt:** 1 · **Milestone:** M8 of 8

## What landed

### Tests — `tests/test_units_workitem_resolution.py` (new file, 96 cases)

The whole plan §"New tests required" except N10, which landed at M3.

- **N1** — one test per row of contract §9's matrix, named after the row.
- **N2** — repository-root discovery: the four launch locations resolve one
  `project_root`; `launch_cwd` is reported per location; `--project-root` still
  overrides; nearest-marker-ancestor wins; each of the three markers is proven;
  the walk never invents a root inside a marker-free subtree; the pre-T03
  launch-directory fallback is preserved; an explicit root with an outside CWD does
  not feed rung 2.
- **N3** — rung 2 never falls through, including when exactly one WorkItem is
  registered (so rung 3 cannot silently rescue it).
- **N4** — the context lifecycle, five invalid-context variants (parametrized),
  the vanished-directory and branch-stale cases, `workitem use` refusing an
  unregistered id without touching the existing file, and the **purity proof**:
  a recursive SHA map plus empty stdout/stderr across bind, explicit, unknown,
  ambiguous and legacy paths.
- **N5** — the branch rung, including the same-branch non-tie-break, detached
  HEAD and no-git.
- **N6** — `execution.json` `git.branch` / `git.startSha` / `worktree`, the
  no-git and detached-HEAD nulls, and the `workitem.json` exact-key pin.
- **N7** — all nine `BRANCH_CRITICAL_ACTIONS` parametrized (with a completeness
  test tying the invocation list to the constant, so the constant cannot grow
  past the coverage), the advisory cases, `gate reject`, the additive `header`
  key with a byte-identical `rendered`, the two-step acceptance, and the
  **pinned `skip` double-acknowledgement** plus its inverse (`skip --confirm`
  alone is still stopped by the guard).
- **N8** — `workitem resolve` per rung, never refusing, never picking, never
  writing, with per-candidate evidence.
- **N9** — one test per D8 rule, the clean and warnings-only repositories, the
  ambiguous repository, the `index_malformed` passthrough, and a finding-shape
  assertion. The symlink case degrades to the `resolve()`-based escape rule
  rather than skipping (plan F13), and a traversal-shaped index id gives that
  check deterministic coverage on every host.
- **N11** — the §9 exit criterion, worktree-shaped: two `git worktree`s, one
  persisted context each, `init` and a later ledger write in each with **no**
  `--workitem` anywhere, byte-unchanged neighbours, per-WorkItem locks, no
  repository-global `.workflow/`. `git worktree add` failing is a loud
  assertion failure, never a skip. Plus a `git check-ignore` proof for the
  context file.
- **N12** — no fail-open: `RUNTIME_FREE_COMMANDS` asserted as an exact
  six-member set; no rung returns an unregistered id; an `ast` proof that
  `resolve_decision` calls no `min`/`max`/`sorted`; an `ast` proof that
  `dataclass_replace(paths, workitem=…)` appears only at the six declared
  sites; an `ast` proof that the active context is written only by
  `cmd_init`, `cmd_migrate_workflow` and `cmd_workitem_use`; plus the two
  T02 guarantees re-pinned (`init` refuses `legacy_workflow_present`
  unconditionally, the legacy dual-read rung still binds).

`tests/conftest.py` is **not** touched by M8 — the single permitted edit was
made at M2.

### Prompt and documentation layer (D7)

- `.claude/skills/sdle/SKILL.md` — Step 1 only. The `init` invocation now names
  `--workitem <id>`; the ladder sentence is rewritten in the D2 order; four new
  paragraphs cover resolution on later turns, the ask-the-user rule (rung 5 may
  rank and annotate, never decide; never delegated to a subagent), the
  branch-mismatch behaviour, and `validate`. **No constant table, version
  string, phase table or gate table touched.**
- `.claude/commands/sdle-start.md` — steps 2 and 4: the same ladder/ask guidance
  and the explicit `--workitem` at `init`. Invocation only.
- `README.md` — the resolution ladder is now eight rungs; new paragraphs for
  root discovery, `workitem resolve`, `validate` and the branch policy; the
  runtime-free sentence now names six commands.
- `docs/SDLE-Reference-Guide.md` — the resolution section rewritten (ladder,
  launch-rung refusal, root discovery, the active-context file,
  `workitem resolve`); "the third rung is transitional" → "the sixth rung";
  the `execution.json` artifact row extended and a new
  `workitems/.active-context.json` row added; new "Branch and worktree rules"
  and "`validate`" subsections.
- `CLAUDE.md` — the gitignore sentence now names the active-context file, and a
  new paragraph states the resolution posture and invariant 8.

`.claude/hooks/hooks.py` and `.claude/settings.json` are **untouched** — that is
the point of D9.

## Evidence (all re-run in this context)

| Command | Result |
|---|---|
| `rtk proxy python -m pytest -q -rsxX tests/test_units_workitem_resolution.py` | **`96 passed in 118.90s`, RAW EXIT 0**, no short-summary section |
| `python scripts/sdle.py lint-skill` (after every prompt edit) | **RAW EXIT 0**, 22 `"passed": true`, 0 `"passed": false`, `Parsed 19 phases, 8 gates, 14 migration rows` |
| `python tools/transition/validate.py` | `TRANSITION_VALID: complete=3/12 next=T03`, **RAW EXIT 0** |
| `git diff --exit-code ab889a1 -- .claude/hooks/hooks.py .claude/settings.json .claude/skills/sdle/templates/state.json .claude/skills/sdle/modules/ scripts/sdle.sh scripts/sdle.ps1 .github/ requirements/ docs/dry-runs/` | **exit 0** (A4) |
| `grep -n 'CURRENT_VERSION = ' scripts/sdle.py` | `CURRENT_VERSION = "1.14"` (A5) |
| `grep -rn "\.sdle/policies\|baseline\.\|risk\|classification\|flow_type\|subagent" scripts/sdle.py` | 2 hits, **byte-identical count and lines at `ab889a1`** — `baseline.lower()` in the drift comparison and the `drift rebaseline` help string. No T05+ concept introduced (A18) |
| `grep -rn "pytest.mark.skip\|pytest.skip(\|xfail" tests/` | **no matches** |

## Next

Full suite, then the handoff and `progress.md` → IMPLEMENTED.
