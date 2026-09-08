# T02 checkpoint a01-06 — M6 complete (guardrail adaptation)

**Milestone:** M6 — write fence, dirty-tree hook, `SDLE_OWNED_PREFIXES`,
Phase 17 diff exclusion, `.gitignore` (plan C9, C10, C12).

## Changes

- `.claude/hooks/hooks.py`: `FENCED = (".workflow", "workitems", "requirements",
  "guidance")`. The `workitems` reason string names all three things it
  protects (registry, identity, runtime) and carries an explicit note to the
  phase that later moves `clarifications/`, `reviews/` and Spec Kit artifacts
  under `workitems/`: fence the whole tree now, carve out artifact subpaths
  then. `.workflow` stays fenced — the legacy runtime still exists during
  migration — and its reason now names `migrate-workflow`.
- `SDLE_OWNED_PREFIXES` gained `"workitems/"` (landed at M2, where the fixture
  change first required it).
- Phase 17 diff exclusion and the manifest file filter both derive from
  `paths.runtime_relative` (landed at M1).
- `.gitignore`: one line, `workitems/*/.sdle/lock`. `git check-ignore -v`
  confirms **only** the lock is ignored — `workitems/index.md`,
  `workitems/<id>/workitem.json` and `workitems/<id>/.sdle/state.json` all stay
  versioned, per contract §19. The file's missing trailing newline (baseline
  E25) is repaired: the diff is `2 insertions(+), 1 deletion(-)`, the deletion
  being the newline-terminated rewrite of the old last line.

## Tests

- `test_hooks.py::test_write_fence_denies_governance_files` — **six new
  parameters** added, none removed: `workitems/index.md`,
  `workitems/wi-a/workitem.json`, `workitems/wi-a/.sdle/state.json`,
  `.../audit.md`, a repo-relative form, and a Windows backslash form. The
  existing `.workflow` parameters are **kept**, per plan §7.2. TP-003 category
  1 for the retained parameters (unchanged behaviour), new coverage for the
  additions.
- `test_hooks.py` — two new dirty-tree cases: silent when two WorkItems make
  resolution ambiguous (and still firing with one), and silent in a repository
  with no WorkItem at all.
- `test_units_workitem_runtime.py` — `implement preflight` does not count the
  `workitems/` tree as dirt; the Phase 17 security diff contains the
  implementation file and **not** the WorkItem runtime.

## Evidence

`pytest tests/test_hooks.py tests/test_units_workitem_runtime.py -q -k "fence
or dirty_tree or preflight or phase_17"` → **28 passed, raw exit 0**.

`git check-ignore -v workitems/wi-a/.sdle/lock workitems/index.md
workitems/wi-a/workitem.json workitems/wi-a/.sdle/state.json` → one line only:
`.gitignore:9:workitems/*/.sdle/lock`.

## Next

M7 — remaining documentation (`CLAUDE.md`, `README.md`, Reference Guide,
`.claude/commands/`), then the full suite, `lint-skill` and `validate.py`.
The `isolated_git_identity` promotion (§7.3) already landed at M4.
