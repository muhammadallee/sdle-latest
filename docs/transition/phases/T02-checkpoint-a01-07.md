# T02 checkpoint a01-07 — M7 complete (documentation, full verification)

**Milestone:** M7 — remaining test-suite rebinding, `isolated_git_identity`
promotion, documentation; then the full suite, `lint-skill` and `validate.py`.

## Documentation changed

- `CLAUDE.md` lines 11 and 34 (plan D11). Line 11 now distinguishes the
  gitignored runtime artefacts from the **versioned** `workitems/` records; line
  34 names `workitems/<id>/.sdle/state.json` and describes `.workflow/` as
  transitional.
- `.claude/commands/sdle-reset.md` (the deleted-file warning) and
  `sdle-start.md` (resume detection, ambiguity handling, the legacy-migration
  step, and the `init` sentence T01 wrote that T02 supersedes).
- `README.md`: title, a v1.14 history row **above** v1.13, the WorkItem section
  rewritten with the five-rung ladder and `migrate-workflow`, the file-layout
  tree, the state-schema section (v1.14 header, `workitem` row, `audit_sha`
  wording) and the completion-summary path.
- `docs/SDLE-Reference-Guide.md`: header version; every runtime path in the
  artifact-ownership table and prose; three new ownership rows
  (`execution.json`, migration evidence, the WorkItem records); the
  WorkItem-identity paragraph; two new subsections — "WorkItem resolution and
  the legacy runtime" and "Execution identity"; Appendix B header and `workitem`
  row; revision-history row 1.3.
- `.claude/skills/sdle/SKILL.md` prose (Step 1 migrate condition, the bootstrap
  paragraph, the refusal rule, the write-fence sentence). The **only** table
  touched anywhere in `SKILL.md` is `VERSION_MIGRATION`, one added row.
- `scripts/sdle.py`: the T01 section comment claiming `.workflow/` remains the
  runtime is corrected; `hooks._project_dir` also recognises a `workitems/` root.

## Final verification (all raw exit codes as observed)

| Command | Raw exit | Result |
|---|---:|---|
| `python -m pytest -q` | **0** | **341 passed in 971.00s** — no failures, errors, skips or xfails |
| `python scripts/sdle.py lint-skill` | **0** | 22 checks, 22 PASS; `Parsed 19 phases, 8 gates, 14 migration rows`; `version_string_consistent: all four locations report v1.14`; `migration_covers_every_state_field: every field has a migration row` |
| `python tools/transition/validate.py` | **0** | `TRANSITION_VALID: complete=2/12 next=T02` |
| Python 3.11 compatibility | — | **NOT_RUN** (no 3.11 interpreter on this host) |
| CI | — | **NOT_RUN** (branch unpushed; no outcome predicted) |

289 was the pre-T02 baseline; T02 adds 52 net. Because the suite is fully green,
plan F1's `ENVIRONMENT_FLAKE` classification was never invoked and no re-run
was needed. `write_atomic` was not touched.

## Structural checks

- `git diff --exit-code 7b9374b -- scripts/sdle.sh scripts/sdle.ps1
  .claude/settings.json .github/workflows/ci.yml .claude/skills/sdle/modules/
  requirements/ docs/dry-runs/` → exit **0**.
- `git diff 6e8af8c -- tests/ | grep -E '^\+.*(skip|xfail)'` → **empty** (A15).
- `git diff 6e8af8c -- .claude/skills/sdle/SKILL.md` touches only
  `VERSION_MIGRATION`, the two version strings and prose (A14).
- `grep -n '\.workflow' scripts/sdle.py` — every survivor is the
  `legacy_workflow` property, a `paths.workflow` alias `mkdir`, a docstring, the
  documented `ARTIFACT_OWNERSHIP` legacy-prefix bridge, `SDLE_OWNED_PREFIXES`,
  or help text (A7).

## Closure items after the final full run

Four items landed after the 341/0 run; none can change it, and each was
re-checked directly:

1. `tests/test_units_workitem.py` **module docstring** (plan §7.2's last row) —
   it still claimed `.workflow/` is where the workflow lives and that `init`
   neither requires nor records a WorkItem, both false after C1/C2/C5.
   Docstring only: no case added, removed or renamed. Re-run of that file:
   **57 passed, raw exit 0** — the same 57 as T01.
2. Handoff case count corrected to **44** in `test_units_workitem_runtime.py`;
   the 44 + 8 (`test_hooks.py`) = 52 net arithmetic is now stated explicitly.
3. Handoff divergence **7** added: the README "command table" in plan §5 lists
   conversational phrases, not CLI subcommands, so `migrate-workflow` and
   `--workitem` are documented in the README's WorkItem section instead.
   Intent satisfied, letter not; declared rather than invented.
4. **A9** run directly: `python scripts/sdle.py constants` → raw exit 0,
   `version_chain` has **14** rows with terminal pair `['1.13', '1.14']`.

`validate.py` and `lint-skill` re-run after these edits: both **raw exit 0**.

## Status

`docs/transition/phases/T02-handoff-a01.md` written; `progress.md` set to
**IMPLEMENTED**, attempt **1**, Commit column **UNCOMMITTED** (the orchestrator
commits and fills the SHA).
