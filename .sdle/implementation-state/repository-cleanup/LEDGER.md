# Repository cleanup ledger

Execution record for `plan-claude-codex-defectfix.md` (plan section 6). Maintenance evidence, not product documentation:
it is not linked from the user documentation index. Helper: `runctl.py` (fingerprint / run / checkpoint).

## Baseline

**Source identity.** `main` @ `0377871fe944ad056dea1b3d61df3af2175fdd3d`; work branch `maintenance/repository-cleanup`;
plan sha256 `0438fae8…aad277` (`plan-claude-codex-defectfix.md`). Not a shallow clone (`rev-parse --is-shallow-repository` = false),
so history-dependent tests have their objects. 231 tracked files, 185 Markdown, `scripts/sdle.py` 11,973 lines (matches the plan's inspection).

**Pre-existing owner changes (preserved, part of the measured tree).** 11 modified files, not made by this run:
`.claude/commands/sdle-start.md`, `.claude/settings.local.json`, `.claude/skills/sdle/SKILL.md`, `CLAUDE.md`, `README.md`,
`docs/SDLE-Reference-Guide.md`, `docs/brownfield/README.md`, `docs/lifecycle/README.md`, `docs/spec-kit-integration/README.md`,
`docs/troubleshooting/README.md`, `docs/workitems/README.md`. Read as a partial trim of "as of v1.x" / "pre-v1.14" narration
(consistent with the plan's AC-03) plus two `rtk` allowances in `settings.local.json`. Baseline fingerprint at P00 start covers them.

**Environment (Windows 10 Home 10.0.19045, Git Bash + PowerShell 7).** Python 3.13.0 (only interpreter; `py -0` lists just 3.13),
git 2.46.2.windows.1, uv 0.9.16, Claude Code 2.1.278, codex-cli 0.151.0, GNU bash 5.2.37 (msys). Test venv is disposable, outside
the checkout: `python -m venv <scratchpad>/venv && pip install pytest coverage vulture` → pytest 9.1.1, coverage 7.16.1, vulture 2.16.
Tests need only pytest + stdlib. **Not the CI configuration** (CI: Python 3.11, ubuntu + windows); Python 3.11 and Linux are NOT RUN locally.
Local `specify` is v0.15.0 (`uv tool`), which is not the pinned Spec Kit 1.0.6; P05's smoke must use the pinned `uvx --from git+…@v1.0.6`, never this binary.

**P08 prerequisite (P00-T05).** `codex --version` → 0.151.0. `codex exec --help` lists `--cd/-C`, `--sandbox/-s`, `--json`,
`--output-schema`, `--output-last-message/-o`, `--ephemeral`, `--skip-git-repo-check`; `codex exec review` exists.
`codex login status` → "Logged in using ChatGPT" (authentication state only). D-07 not triggered.

**WorkItem/runtime inventory (P00-T04).** No `workitems/` directory, no `.workflow/`, no tracked WorkItem files. `sdle.py validate` (run `p00-validate`)
→ ok, 0 errors, 1 warning (`active_workitem_unresolved`, expected in the source repository). It raises nothing about
`.sdle/implementation-state/repository-cleanup/`, so the record location is permitted.

**Live observation recorded early (F-013).** While cwd was `…/repository-cleanup/runs/`, the registered hook
`python .claude/hooks/hooks.py dirty-tree` could not start (`can't open file '…\runs\.claude\hooks\hooks.py'`). Python exits 2 for that,
and Claude Code reported `PreToolUse:Bash hook error` **and the Bash call was blocked** (exit-2 = blocking), i.e. a non-starting hook
was not silently disabled on this host — it failed closed for that one guard, by accident of Python's exit code. Reproduced in a real
Claude Code 2.1.278 session, not only at the hook boundary. The bare `python` and cwd-relative path remain the defect.

**Baseline runs** (records and logs under `runs/`; source fingerprint `ac66c6b2…` at start; every run's record states its own):

| Run | Result | Notes |
|---|---|---|
| `20260920T055510-p00-collect` | 2246 tests collected (record says UNKNOWN: runner did not yet parse "collected"; runner fixed after) | matches the plan's reported 2,246 |
| `20260920T055516-p00-help` | PASS exit 0 | |
| `20260920T055517-p00-constants` | PASS exit 0 | |
| `20260920T055519-p00-lint-skill` | PASS exit 0 | on the tree including owner edits |
| `20260920T055553-p00-sh-lint` | PASS exit 0 | `sh scripts/sdle.sh lint-skill` |
| `20260920T055556-p00-ps1-lint` | PASS exit 0 | `pwsh -File scripts/sdle.ps1 lint-skill` |
| `20260920T055559-p00-validate` | PASS exit 0 | see above |
| `20260920T055546-p00-full-suite` | **INTERRUPTED** | Killed by the Claude Code harness ("system critically low on memory", not a test outcome) at ~76% (1,784 of 2,246 progress marks), no summary line. Two `F` markers seen at collection positions 734 and 1593: `tests/test_units_discovery.py::test_n14_no_discovery_vocabulary_is_restated_outside_sdle_py` and `tests/test_units_governance.py::test_no_policy_default_value_is_restated_outside_sdle_py`. **No suite PASS/FAIL count is claimed.** Not restarted (harness instruction; memory may still be short). |
| `20260920T062136-p00-two-failures-dirty-tree` | FAIL, 2 failed | On the main checkout. Offenders listed are only this run's own records under `.sdle/implementation-state/repository-cleanup/` (`UNKNOWN`, `repository_inventory`, `risks_debt`, policy ids appear in LEDGER.md, runctl.py, and run logs that list test names). |
| `20260920T062315-p00-two-tests-clean-head-plus-wip` | PASS, 2 passed | Same two tests in a detached worktree of `0377871` with the owner's diff applied and **no** maintenance records. Classifies both failures as caused by the records' location, not by the product. |

| `20260920T123707-p00-full-suite-clean` | **PASS**, 2246 passed, 0 failed, 0 skipped, exit 0, 2142.75 s | Records-free detached worktree of `0377871` + owner diff; Python 3.13.0, pytest 9.1.1, Windows 10. Fingerprint `ac66c6b2…` unchanged during the run. Memory sampled every ~10 s (198 samples, `…full-suite-clean.mem.csv`): min physical available 4.13 GB, peak commit 23.1 of 31.8 GB, **peak python.exe working set (all processes) 162 MB**, peak git 19 MB. |

**Baseline status: COMPLETE (with stated limits).** The full suite passes on the owner's tree at `0377871`: 2,246 collected, 2,246 passed.
Reproduces the plan's reported figure with durable evidence. Limits: Windows + Python 3.13 only (CI is 3.11 on ubuntu + windows;
Python 3.11 and Linux are NOT RUN here); the run used a records-free worktree, not the maintenance checkout, because of F-025.
The first, interrupted run is kept as evidence of the harness reap, not as a result.

**Why the first full run stopped (reason of record).** The Claude Code harness reaped the background shell with this notice:
"stopped because the system is running low on memory … critically low on memory while the session was idle … says nothing about
the command or its own memory use". The notice named no resource, threshold or process, and no memory was sampled during that run,
so **which resource ran out (physical RAM, commit charge/page file, other) is unknown and is not attributed to the suite.**
Measured afterwards on an idle machine (2026-09-20): physical 4.36 GB free of 15.89 GB; commit charge 22.6 GB of a 31.8 GB limit
(~71%); `C:\pagefile.sys` 16 GB, 2.6 GB in use, **peak 8.7 GB since boot** (a past paging spike, not attributable to this run);
largest processes were 250–750 MB each (memory compression, an antivirus service, Edge, VS Code, Claude Code). Most plausible
resource by these numbers: commit charge / page file rather than RAM — a guess, not an observation.

**Rerun authorisation and reason.** On 2026-09-20 the owner said "you can continue but note down the reason this time" after being
told the run was not restarted on its own. Reasons for the rerun: (1) the baseline is still unproven for the last ~24% of tests
(P00-T03); (2) it runs on the records-free clean worktree because of F-025; (3) `runctl.py run --sample-memory 10` now records
system RAM, commit charge and python/git working sets every ~10 s to `<run>.mem.csv`, so any further reap can be attributed from
evidence instead of guessed. If it is reaped again: mark the record INTERRUPTED, quote the harness notice here verbatim, and read the
last rows of the `.mem.csv` (resource nearest its limit) before drawing any conclusion. The owner also named the options of running
the suite in their own terminal or launching Claude Code with `CLAUDE_CODE_DISABLE_BG_SHELL_PRESSURE_REAP=1`; neither is used.

**Outcome of the memory sampling (reason of record, updated).** The rerun finished (exit 0) with no reap. During its 36 minutes the whole
`python.exe` population never exceeded 162 MB and git never exceeded 19 MB; free physical RAM stayed >= 4.13 GB and commit charge peaked
at 23.1 of 31.8 GB (~73%), never near the 90% alarm. The suite is therefore **not** a significant memory consumer, which fits the
harness note; the first reap was a machine-wide condition at that moment (earlier idle-time measurements showed a 8.7 GB page-file
peak since boot). The exact resource that tripped the reap remains **unproven** because it was not sampled then. Nothing here
justifies restarting or throttling the suite; if a reap recurs, use the procedure above.

Runner misfires discarded (not evidence): four runs recorded BLOCKED because `runctl.py` swallowed its own flags and, before that, a
POSIX-style interpreter path; the tool never started, so those records were deleted.

## Phase log

### P00 — Checkout, baseline, and durable work setup

**Objective / ACs:** AC-09, AC-10. Measure the baseline faithfully; make the run resumable. No product change is mixed in.

**Source identity:** branch `maintenance/repository-cleanup`, created from `main` at `0377871fe944ad056dea1b3d61df3af2175fdd3d`
(local checkout, not shallow, 50 commits). The working tree carried 11 uncommitted modified files that pre-date this run
(owner's partial trim of version narration in CLAUDE.md, README, docs/, SKILL.md, sdle-start.md, plus additions to
`.claude/settings.local.json`). They are preserved and are part of the measured baseline (fingerprint covers them).

**Tasks**
- P00-T01 Checkpoint files (STATE.json, journal.jsonl, LEDGER.md, runs/, `runctl.py`). Done when STATE.json is readable and names the next action.
- P00-T02 Environment record: versions of python, pytest, git, sh, uv, claude, codex, specify; isolated venv outside the checkout.
- P00-T03 Baseline runs through `runctl.py run`: `--collect-only`, `sdle.py --help`, `constants`, `lint-skill`, `sh scripts/sdle.sh lint-skill`, `sdle.ps1 lint-skill`, then the full suite.
- P00-T04 Inventory existing WorkItems/runtime in this checkout (so later cleanup cannot erase them) and check `validate` accepts the record location.
- P00-T05 P08 prerequisite check: `codex --version`, `codex exec --help` flags, `codex login status` (state only).
- P00-T06 Classify baseline failures, write `## Baseline`, checkpoint, commit the maintenance branch.

**Exclusions:** no product edit, no dependency install into a shared interpreter, no Codex install/login.

**Verification:** each run has a JSON record with argv, cwd, fingerprint, exit code, counts; zero-collected is not PASS.
**Rollback:** delete the branch; `main` is untouched. **Exit:** baseline reproducible, failures classified, next action unambiguous.

**Deviations recorded:** the plan file keeps its name `plan-claude-codex-defectfix.md` (plan says `plan.md`); it is excluded from
the content fingerprint by path, along with the untracked `plan-chatgpt-claude-chatgpt-reviewed.md`. Local Python is 3.13.0 on
Windows 10 only (CI is 3.11 on Linux+Windows); `py -0` lists no other interpreter.

### P01 — Audit and contract inventory

**Objective / ACs:** AC-01, AC-02, AC-05, AC-11, AC-13, AC-14. Produce evidenced, prioritised backlogs for P02 (repairs) and P03 (removals),
and the directory, documentation and install inventories. **Source:** `maintenance/repository-cleanup` after `4df2510`
(owner edits) + the F-025 slice; baseline PASS recorded above. **Prerequisite:** P00 complete. **Exclusions:** no product change beyond F-025;
no feature ideas (parked in Findings as OUT-OF-SCOPE).

**Tasks** (each writes into a fixed section of this ledger; a task is done when its section accounts for the surface)
- P01-T00 F-025 slice (in progress): shared scan helper + path-specific exclusion + non-vacuity/negative tests. Verify: 3 affected modules green.
- P01-T01 Tracked-file inventory by group (231 files) → `Directory inventory` + `Documentation map` skeletons.
- P01-T02 Reachability: parser/dispatch → handlers; launchers; hooks; prompt-to-command references. Uses vulture (done, 4 candidates) and a coverage run.
- P01-T03 Coverage-driven dead-code candidates: one `coverage run --branch` full-suite run (engine + hooks, subprocess via `COVERAGE_PROCESS_START`); unexecuted ≠ dead, each candidate needs §7 reachability evidence.
- P01-T04 Installed-product boundary: the exact file set a target needs, settings merge, interpreter resolution, Spec Kit discovery → feeds GETTING-STARTED and the install-contract check.
- P01-T05 Test-to-contract map; **historical-test replacement map** for `test_units_capabilities.py`, `test_units_gate_policy.py`, `conftest.py` (BASELINE/FROZEN/`git show` comparisons, `STABILIZATION_01_*`).
- P01-T06 Documentation inventory: living vs historical (`docs/transition/` 119 files, `docs/verification`), duplicate setup recipes, broken links/anchors, stale counts, unsupported claims.
- P01-T07 Product-agent + remediation path review (who records, who fixes, what invalidates a review).
- P01-T08 Current-schema boundary decision for `migrate`, `migrate-workflow`, `VERSION_MIGRATION`, `.workflow` handling (F-011, F-019, F-020): callers, safety role, proposed disposition.
- P01-T09 Directory-layout inventory (source / installed target / generated runtime) and empty/placeholder classification (`.sdle/*/.gitkeep`, others found).
- P01-T10 Hook contract audit (F-013–F-016, F-024): interpreter, anchoring, cwd variants, per-guard posture, matcher table per role, unfenced Bash paths.
- P01-T11 Frontmatter audit for skill, 4 agents, 9 commands (F-018); shipped-surface scan for developer-local content (F-012).
- P01-T12 New-user walk of current first-run docs → the consolidation list for `docs/GETTING-STARTED.md` (F-003, START-HERE, README Quick Start, tutorial setup blocks).
- P01-T13 Revalidate F-001..F-024 against this checkout (confirmed / refuted / hypothesis) and add F-nnn for new evidence.

**Verification:** every proposed defect carries evidence or is labelled HYPOTHESIS; every planned deletion has a contract disposition;
`Findings`, `Removals`, `Directory inventory`, `Documentation map` account for the audited surfaces; no product file changes except F-025.
**Risk / rollback:** read-only apart from F-025 (a single revertible commit). **Checkpoint boundary:** after each task.
**Exit:** the P02 repair backlog and P03 removal backlog are concrete enough to plan independently; open questions listed.

## Findings

_One entry per F-nnn; appended and updated in place. Seed findings F-001..F-024 are revalidated in P01; below are only findings established so far._

- **F-025** (new, P00) — *maintenance-record location collides with repository-wide restatement scans.* Severity: medium (blocks
  every full-suite run on this branch). `tests/test_units_discovery.py::searchable_files` (and the policy-defaults test in
  `test_units_governance.py`) scan **all of `.sdle/`** for the engine's vocabulary; §6.1 of the plan puts the maintenance
  records in `.sdle/implementation-state/repository-cleanup/`, whose LEDGER, runner and run logs necessarily contain
  `UNKNOWN`, `repository_inventory`, `risks_debt` and policy ids. Evidence: runs `…-two-failures-dirty-tree` (FAIL) vs
  `…-two-tests-clean-head-plus-wip` (PASS). Plan §6.1 anticipates a *path-specific* exclusion for these records and forbids
  excluding all of `.sdle/`. Planned fix (first slice of the next phase, with a negative test showing a *product* file under
  `.sdle/` is still scanned): exclude only `.sdle/implementation-state/repository-cleanup/` in the shared scan helper(s).
  Status: **FIXED** (commit below). AC-08, AC-09. Fix: the two private copies of the scan helper (`_searchable_files` in test_units_governance, `searchable_files` in test_units_discovery) became one `conftest.searchable_files(root)` that skips `MAINTENANCE_RECORDS` (`.sdle/implementation-state/repository-cleanup/`) and nothing wider; two new tests in test_units_capabilities: `…skips_only_the_maintenance_records` (sibling `implementation-state/` files, policies, templates, config still scanned; mutation-checked: widening the skip to `.sdle/` makes it fail) and `…is_not_vacuous_on_this_repository`. Evidence: runs `…p01-f025-targeted` (7 passed; the two originally failing tests now pass on the main checkout with records present) and `…p01-f025-modules` (412 passed, 5 min, fingerprint unchanged). Pre-fix failure: `…p00-two-failures-dirty-tree`.
- **F-013 live evidence** (P00) — see Baseline. Refinement to the plan: Claude Code docs classify a hook that cannot start as
  non-blocking (shell exit 127), but `python <missing-script>` exits **2**, which Claude Code treats as *blocking* — observed:
  the Bash call was denied. So the failure mode on this host is "a mis-anchored hook can block the session", not only
  "a guard silently disabled". Docs (code.claude.com/docs/en/hooks, fetched 2026-09-20) also give: exec form (`command` + `args`,
  no shell) with `${CLAUDE_PROJECT_DIR}` substituted into each element; `shell` field (`bash` default, `powershell` on Windows
  without Git Bash; ignored when `args` is set); JSON `systemMessage` reaches the user; stderr of an exit-0 hook goes only to the
  debug log; the docs' tool-name examples list `Edit`, `Write`, `NotebookEdit` and **not** `MultiEdit` (F-016 to verify against a live session).
- **F-018 confirmed** on this checkout: SKILL.md `description` = 1,068 chars, contains `v1.17` and mojibake dashes (U+FFFD in a UTF-8 read).
- **F-012 confirmed:** `.claude/settings.local.json` tracked, machine paths `D:\Learning\AI\Claude Code\sdle\…`, broad `git init/add/commit` allowances; owner's uncommitted edit adds `rtk git *`/`rtk ls *`. Fix will untrack with `git rm --cached` so the owner's local file survives on disk.
- **F-019/F-020 counts confirmed:** `scripts/sdle.py` has 25 `v1.x` and 99 `T00`–`T11` references; hooks.py has 1 and 4; `.gitignore` lists `.workflow/`, `design/`, `reviews/`, `clarifications/`; hooks fence `.workflow`.
- **Vulture (min-confidence 60, run `p01-vulture-60`)** on `scripts/sdle.py` + `hooks.py`: 4 candidates only — property `security_review_md` (sdle.py:338), constants `CLASSIFICATION_REQUIRED_KEYS` (4154), `GATE_DISPOSITIONS` (5060), `BASELINE_REFERENCE_KINDS` (6003). Candidates, not deletions; P01 does reachability.

## Removals

_One entry per DEL-nnn; append-only apart from status._

## Directory inventory

_Filled by P01._

## Documentation map

_Filled by P01._

## Independent review

_P08._

## Owner decisions

_Section 12 decisions are recorded here as each phase needs them._

## Final report

_P09._
