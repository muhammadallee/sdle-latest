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

**Historical-test replacement map (P01-T05).** History-dependent = uses `git show <commit>:<path>` or the declaration machinery. Only three pinned commits exist:
`BASELINE = adbdc5e` and `T11_TEMPLATE_BASELINE = 4b1aa71` (`tests/test_units_capabilities.py`), `ROLLBACK = e1cf341` (`tests/test_units_gate_policy.py`), plus
`assert_frozen_module`, `module_units`, `STABILIZATION_01_TEST_{EDITS,ADDITIONS,REMOVALS}` and `DRY_RUN_SUBSTITUTIONS` in `tests/conftest.py`. Other "byte-identical"
wording in `test_units_hardening/governance/execution_identity` and `test_integration_10_to_13` asserts *current* behaviour (a refusal leaves the runtime unchanged)
and stays. `.gitignore`, `.claude/settings.json` and three integration modules are the `FROZEN` tuple (byte-compared against `adbdc5e`).

| Test (module) | What the history pin protects | Replacement before removal (P03) |
|---|---|---|
| `test_the_baseline_is_reachable`, `test_the_rollback_point_is_reachable` | non-vacuity of the comparisons below | delete with them |
| `test_n20_n24_the_frozen_files_are_byte_identical` (+ `test_the_stabilization_declarations_name_only_frozen_files`) | the three integration modules and `.claude/settings.json`/`.gitignore` were not edited to hide a regression | none needed beyond the tests running and review; **`.gitignore`/`settings.json` freeze blocks F-012/F-013 edits, so it goes first** |
| `test_n20_the_nine_dry_run_transcripts_match…` / `test_n27_the_nine_dry_run_transcripts_match…` | dry runs 01–09 unchanged apart from declared substitutions | `tests/test_dry_run_contracts.py` already recomputes every claim (progress fractions, gate numbers, refusals) from the engine and requires cited tests to exist; keep it, extend for 14–16 metadata in P05 |
| `test_n21_greenfield_is_frozen_and_every_flow_is_element_wise_identical`, `test_n29_the_frozen_greenfield_tuple…` | GREENFIELD's 18 phases unchanged; other flows are ordered subsets | direct literal assertion of `GREENFIELD_V1_PHASES` + subset rule in `test_units_flow_model.py` (exists for the subset rule; add the literal) |
| `test_n24_a18_the_engine_gained_no_writer_and_no_state_field` | single-writer invariant 6: no new write primitive | allowlist of the engine's write primitives (needles already exist: `test_the_write_primitive_needles_are_not_vacuous`) asserted against the current source |
| `test_n26_every_baseline_check_is_still_present_and_passing` | `lint-skill` did not get weaker (33 check ids at the rollback point) | the id list is already a literal (`BASELINE_CHECKS`); rename, keep as "required checks", drop the git comparison |
| `test_n27_the_four_existing_hook_guards_and_their_tests_are_unmodified`, `test_n28_the_hooks_are_byte_identical` | hooks untouched | superseded by `tests/test_hooks.py` behaviour tests; **must be dropped before P02 edits hooks** |
| `test_t11_the_state_template_changed_only_as_declared`, `test_n24_the_schema_did_not_move`, `test_n28_the_state_schema_did_not_move` | state template/schema shape | direct check of `templates/state.json` fields against the engine's schema/defaults (the rewrite of `migration_covers_every_state_field`, F-008) |
| `test_n22_/test_n31_migrate_workflow_still_leaves_the_legacy_tree_untouched` | `migrate-workflow` never mutates `.workflow/` | goes with `migrate-workflow` if retired (DEL-002); otherwise keep (no history use) |
| `test_a25_*` (enforcement-split wording) | prose caveats not softened | no history pin; **keep**, they protect the never-soften rule |
| CI `fetch-depth: 0` + long comment in `.github/workflows/ci.yml` | history objects exist for the pins above | shallow checkout after the pins are gone; verify with a shallow-clone run (P03/P09) |

Order constraint: hook and `.gitignore`/`settings.json` edits (P02) are blocked by the freezes above, so P02's first slice replaces exactly those freezes (state template
and dry-run freezes can wait for P03).

**Verification:** every proposed defect carries evidence or is labelled HYPOTHESIS; every planned deletion has a contract disposition;
`Findings`, `Removals`, `Directory inventory`, `Documentation map` account for the audited surfaces; no product file changes except F-025.
**Risk / rollback:** read-only apart from F-025 (a single revertible commit). **Checkpoint boundary:** after each task.
**Exit:** the P02 repair backlog and P03 removal backlog are concrete enough to plan independently; open questions listed.

**P01 exit decision (2026-09-20): COMPLETE — backlogs concrete.** Sections `Findings`, `Removals`, `Directory inventory`, `Documentation map` account for the audited surfaces.
Every finding is CONFIRMED with evidence, PARTLY REFUTED (F-020), or an explicit HYPOTHESIS (F-024; `MultiEdit`/`NotebookEdit` tool names and payload key, to verify live). One tooling limit is open (coverage). New findings F-025 (fixed), F-026, F-027, L-001.

*P02 repair backlog, in order:* (1) F-012 untrack `settings.local.json` + ignore — needs the `.gitignore`/`settings.json` history freezes replaced first (DEL-009 part); (2) F-013 anchored, interpreter-resolving hook registration in `settings.json` **and** the 4 agent frontmatters, then live smoke;
(3) F-014 per-guard posture (D-01 defaults) with `systemMessage`/`additionalContext`; (4) F-015 relative-path anchoring; (5) F-016 one shared tool-name set + role matrix; (6) F-018 skill description ≤1,024, no version, narrower trigger; (7) F-026 `sdle.sh` exec bit; (8) F-024 behavioural policy-relaxation test (D-04); (9) D-01/D-04/D-05 recorded.
*P03 removal backlog, in order:* DEL-005, DEL-006 (trivial), DEL-009 (remaining history scaffolding, CI depth), DEL-001+DEL-002 together (migration + legacy, with the new `unsupported_state_version` refusal), DEL-003 (`templates/` slot), F-019 comments/strings/deny reasons in the same slices.
*P04 docs backlog:* DEL-004, DEL-007, DEL-008, DEL-011, `GETTING-STARTED.md`, F-003/4/5/6/22, F-027, L-001, index + `FLOW_COUNT_DOCS`.
*Open questions for the owner (defaults apply, none blocks):* D-01..D-07 per section 12; plus one new: whether `.sdle/templates/` may be removed (default: yes, DEL-003).

### P02 — Repair confirmed defects

**Objective / ACs:** AC-01, AC-04, AC-13, AC-17, AC-18. **Source:** `maintenance/repository-cleanup` @ `61cc882` (baseline PASS on the same product content). **Prerequisite:** P01 complete.
**Exclusions:** no change to governance semantics, gates, flows, or the Spec Kit boundary; no relaxing of any refusal. D-01 and D-04 defaults apply (Owner decisions).

**Live facts gathered for this phase (Claude Code 2.1.278, Windows 10, headless `claude -p`, disposable project `livehook`, 2026-09-20):**
tool list has `Write`, `Edit`, `NotebookEdit`, `Bash`, `PowerShell` and **no `MultiEdit`**; hooks run under Git Bash (`SHELL=C:\\Program Files\\Git\\bin\\bash.exe`, `MSYSTEM=MINGW64`);
`${CLAUDE_PROJECT_DIR}` substitutes in shell-form commands and is exported (forward-slash form); payload keys `cwd, effort, hook_event_name, permission_mode, prompt_id, session_id, tool_input, tool_name, tool_use_id, transcript_path`;
`Write`/`Edit` pass an **absolute** native `file_path`, `NotebookEdit` passes `notebook_path`; the hook's process cwd equals the *session's current* directory (why a moved cwd broke the registration).

**Design decisions**
- Registration (F-013): shell form `sh "${CLAUDE_PROJECT_DIR}/.claude/hooks/run-hook.sh" <guard>` in `settings.json` and the four agent frontmatters. `run-hook.sh` (new, POSIX sh, builtins only) resolves Python >= 3.11 in the launchers' order (`py -3`, `python3`, `python`, `uv run`) and execs `hooks.py`; if none resolves it emits a JSON envelope on stdout (deny for the two fail-closed guards, `systemMessage` for the three scanners) and exits 0, so a missing interpreter is **visible**, never silent. Test pins the resolution order equal to `sdle.sh`'s (two launchers, one fact). Requirement stated in docs: a POSIX `sh` (Git for Windows on Windows); PowerShell-only Claude Code hosts fall outside the guarantee, and the post-launch smoke check is how that is discovered.
- Project anchoring (F-013/F-015): `_project_dir()` = `CLAUDE_PROJECT_DIR` if a directory, else the directory two levels above `hooks.py` (no cwd heuristics, no `.workflow`). `tool_path` resolves a relative path against the payload `cwd` (else process cwd) before normalising; also reads `notebook_path`.
- Posture (F-014, D-01): `write-fence`, `product-agent-fence` fail closed when the hook runs but cannot evaluate (unparseable stdin, exception, write tool with no path); scanners fail open and announce degradation via `systemMessage` **and** `additionalContext`.
- Coverage (F-016): shared tool sets in `hooks.py` (`FILE_WRITE_TOOLS`, `SHELL_TOOLS = Bash, PowerShell`, agent fence = writes + `NotebookEdit` + shells); `MultiEdit` removed everywhere; `secrets-scan` gains `NotebookEdit`-free parity with `write-fence` (same file-writing set); `dirty-tree` and the agent fence gain `PowerShell`. A test compares every registration's matcher with the role table (P06 generalises it).

**Tasks (each: reproduction/regression in the same commit; test must fail on the parent)**
- P02-T01 F-012 + freeze replacement. Add `tests/test_units_shipped_surface.py` (settings.local.json untracked and ignored; no absolute developer path in tracked `.claude/`, `scripts/`, `.github/`), fails now; `git rm --cached .claude/settings.local.json`, ignore it. Drop `.gitignore` and `.claude/settings.json` from `FROZEN`, delete the two hook byte-freeze tests (`test_n27_the_four_existing_hook_guards_and_their_tests_are_unmodified`, `test_n28_the_hooks_are_byte_identical`), whose invariants are covered by `tests/test_hooks.py` behaviour tests + the T02/T03 registration tests.
- P02-T02 F-015/F-014/F-016 in `hooks.py` with probe-derived regression cases (relative, `..`, mixed separators, drive path, `notebook_path`, garbage stdin, engine missing, PowerShell tool).
- P02-T03 F-013 launcher + registrations + tests (interpreter order equals `sdle.sh`; `python3`-only PATH; foreign cwd; no-interpreter envelope).
- P02-T04 Live smoke in a real headless Claude Code session on a disposable project with the installed hooks: a write to `workitems/.sdle-hook-probe` is denied and nothing is created; a guard that cannot evaluate is visible. Evidence saved under `runs/`. `/hooks` listing is interactive-only and stays NOT RUN.
- P02-T05 F-018: SKILL.md `description` <= 1,024 chars (target ~250), trigger phrases first, no version, no bare "requirements/ folder" trigger; test on length/no-version/no-loose-trigger.
- P02-T06 F-026: `git update-index --chmod=+x scripts/sdle.sh`; test reads the index mode.
- P02-T07 F-024: behavioural test (tighten policy, start WorkItem, relax back, observe the next gate decision) per D-04; document the actual mechanism or raise a confirmed defect.
- P02-T08 Record D-01/D-04/D-05 outcomes; update the Findings statuses.

**Verification:** targeted modules per slice (`tests/test_hooks.py`, new modules, `test_lint_skill.py`, `test_units_capabilities.py`), `lint-skill`, then the full suite once at phase end (P03 runs the post-removal full suite). Live results are labelled live; direct-invocation results are labelled boundary-only.
**Risk / rollback:** each task is its own commit; `git revert` of one leaves the rest valid. A registration change cannot take effect in *this* session (settings are read at session start), so its live check uses a fresh `claude -p` process. **Exit:** every P02 finding fixed with its reproducer failing before and passing after, or reported as an unresolved blocker.

**P02 progress and verification (2026-09-20).** Runs are under `runs/`; every "before" is a run of the new tests against the parent commit.

| Task | Finding | Commit | Reproduced before (run) | Verified after (run) | Scope of the evidence |
|---|---|---|---|---|---|
| P02-T01 | F-012 | `0451ef9` | `p02-t01-before-fix`: 3 failed / 9 passed (tracked, not ignored, machine path present) | `p02-t01-final`: 137 passed (shipped-surface + hooks + the two freezes); `p02-t01-after-fix`: 652 passed over four modules before the last two freeze fixes | unit/behavioural on the checkout |
| P02-T02 | F-014, F-015, F-016 | `b8ea888` | `p02-t02-before-fix`: 20 failed / 5 passed of 25 new cases | `p02-t02-after-fix`: 143/144 (one wording test, fixed) then `p02-t02-modules`: 383 passed (hooks, capabilities, lint, shipped-surface) | hook boundary (direct + through `sh -c`), not Claude Code |
| P02-T03 | F-013 | `8c584f7` | `p02-t03-before-fix`: 15 failed / 2 passed | `p02-t03-after-fix`: 395 passed + 1 lint test fixed; `p02-t03-lint-final`: 80 passed | tests run the registered command through `sh -c`; python3-only and no-interpreter cases use PATH shims |
| P02-T04 | live check of F-013/F-014 | (evidence file) | see below | `runs/20260920-p02-t04-live-smoke.txt` | **real headless Claude Code 2.1.278, Windows only** |

**Live results (T04).** A: new registration, launched at the project root, a Write to `workitems/.sdle-hook-probe` was denied by the SDLE write fence and no file exists. B: after a Bash `cd workitems/sub`, the Write was still denied and the hook started normally; **the same run against the previous registration was also denied**, so B is a no-regression check and is *not* evidence of the F-013 fix (in headless mode an in-call `cd` does not move the hooks' cwd; the failure was seen in the interactive session, where the tool reported a changed working directory, and at the hook boundary). E: with `scripts/sdle.py` absent, Claude Code surfaced `PreToolUse:Read says: SDLE untrusted-read could not run (scripts/sdle.py is not in this project)…` — the user channel of F-014 is verified live; that `additionalContext` reached the model is **not** visible in the stream and is NOT verified. Claude Code labels even a deliberate deny `PreToolUse:Write hook error: SDLE write fence: …`, so a smoke check must look for the SDLE reason text and for the absent file, never for the words "hook error". NOT RUN live: python3-only host and no-interpreter (tests only), Linux/macOS, the interactive `/hooks` listing.

**F-028 (new, found by the live checks).** *Claude Code does not load project hooks from a parent directory.* Evidence: a logging hook registered in the parent's `.claude/settings.json` wrote 1 entry when Claude Code was launched at the project root and 0 when launched from `sub/`, where the Write also succeeded; with `workitems/sub` as the launch directory both the old and the new registration allowed a write into the fenced `workitems/` tree (probes C-old/C-new). Consequence: **every SDLE guardrail hook is silently off unless Claude Code is launched from the directory that contains `.claude/settings.json`**, although SDLE's own resolution ladder supports launching from `workitems/` and `workitems/<id>/` (contract §9). The hooks are tripwires and the engine's choke-point refusals still apply, but the documentation must say so. Not fixable in the product; classified documentation/limitation, severity M. Fix: `docs/GETTING-STARTED.md` names the project root as the launch directory, states that a subdirectory launch runs without the guard hooks, and makes the post-launch smoke check part of readiness; troubleshooting entry. ACs: AC-15 AC-17.

**T05-T07 (2026-09-20).** F-018 fixed and F-026 fixed together in `64e555e` (before: 5 failed `p02-t05-before-fix`, 1 failed `p02-t06-before-fix`; after: 249 passed `p02-t05-after-fix` and 19 passed `p02-t06-after-fix`; the T05 run's fingerprint shows *changed* because the F-026 tests were appended to a test file after collection, which does not affect what ran). F-024 is **confirmed and open** (see Findings and D-04); three mechanism-fact tests in `tests/test_units_policy_midflight.py` (3 passed, `p02-t07-tests`) pin what an omission records, without asserting the mid-flight hazard is acceptable.

**Remaining P02 tasks (superseded):** T05 F-018 (skill description; the `_check_version_consistency` frontmatter regex must tolerate an absent frontmatter version), T06 F-026 (`sdle.sh` mode), T07 F-024 (policy behavioural test), T08 (record D-01/D-04/D-05 outcomes).

### P03 — Dead code, directory cleanup, retired compatibility, historical test scaffolding

**Objective / ACs:** AC-02, AC-04, AC-11, AC-13, AC-14. **Source:** `maintenance/repository-cleanup` @ `7cc888f`; suite passed on the pre-P02 product content (baseline). **Prerequisite:** P02 complete.
**Exclusions:** no change to flows, gates, governance semantics or the Spec Kit boundary; F-024 stays open (owner). Retirements keep a *safe refusal* for unsupported state (never silent reinterpretation, never a reset).

**Order (lowest risk first; each item is its own commit with its tests; the full suite runs at phase end):**
- P03-T01 DEL-005 `Paths.security_review_md`, DEL-006 `CLASSIFICATION_REQUIRED_KEYS`. Evidence: 1 engine ref each (definition), 0 tests, 0 prompts. Verify: lint-skill + affected modules.
- P03-T02 DEL-009 remainder: `assert_frozen_module`, `module_units`, `STABILIZATION_01_TEST_{EDITS,ADDITIONS,REMOVALS}`, `FROZEN`/`FROZEN_FILES`, the `BASELINE`/`ROLLBACK`/`T11_TEMPLATE_BASELINE` pins and the `git show` helpers, the dry-run byte pins with `DRY_RUN_SUBSTITUTIONS`, `test_the_baseline_is_reachable`/`test_the_rollback_point_is_reachable`. Replace, before removing, with the mapped direct checks (replacement map in P01): GREENFIELD literal phase tuple, single-writer write-primitive allowlist, required lint-check ids as a literal, state template vs engine schema (F-008), `test_dry_run_contracts.py` stays. Then `fetch-depth: 0` and its comment leave `ci.yml`. Verify: each replacement fails when its property is deliberately broken; a shallow clone runs the normal suite.
- P03-T03 DEL-001 + DEL-002 together: the migration chain, `migrate` and `migrate-workflow`, `.workflow` handling, `VERSION_MIGRATION`, and the new `unsupported_state_version` refusal. Design: `read_state` compares `workflow_version` with `CURRENT_VERSION` and refuses (exit 1, remedy names `workitem create` for a fresh WorkItem); a repository whose only runtime is a legacy `.workflow/` is refused `workitem_required` without a `legacy_state` remedy that names a removed command. Verify: refusal tests fail on the parent; write-fence probes still deny state/audit paths; suite.
- P03-T04 DEL-003 `.sdle/templates/` slot (D-08 default: remove; tolerate an existing directory). Also decide `.gitkeep` files with a fresh-clone test.
- P03-T05 F-019: every `v1.x`, `T00`-`T11`, "as of", "since" in `scripts/sdle.py` comments, docstrings, CLI help/error/remedy strings, hook reasons and prompts (contextual scan; schema identifiers exempt), together with the code they narrate.

**P03-T03 outcome (2026-09-20).** DEL-001 **DONE**: `_mig_1_0`..`_mig_1_16`, `MIGRATIONS`, `migrate_state`, `cmd_migrate`, the `migrate` command, the SKILL.md `VERSION_MIGRATION` table and its lint check are removed (engine 11,973 -> ~11,400 lines); `Constants.version_chain` and the `constants` output key are gone. Replacement contract: `read_state` refuses `unsupported_state_version` (exit 1, names `workitem create`, leaves the file untouched) for any state whose `workflow_version` is not `CURRENT_VERSION`; `state dump`, `state get`, `doctor` and `audit verify` read any version so a file can still be inspected. DEL-002 **PARTIAL by decision**: `cmd_migrate_workflow` and the `migrate-workflow` command are removed (it called the chain, so they went together), and every message that named it now says SDLE does not run or migrate a retired `.workflow/` runtime and points at `workitem create`. The **detection** of a legacy `.workflow/state.json` is *kept* as a safe refusal (`workitem_required` / `legacy_workflow_present`), together with its project-root marker and write-fence, because a repository holding a retired runtime must be refused with an explanation rather than silently treated as empty; removing detection too is a follow-up, not needed for AC-02. Tests: 61 test functions that existed only for the migration feature were deleted with their helpers (list in the commit), 12 were converted to the current wording, 8 new tests cover the refusal (`test_units_state.py`), and `tests/test_units_invariants.py` snapshots were updated on purpose (write_atomic 31->25, save_state 47->46, append_audit 49->47; `migrate`/`migrate-workflow` out of the command surface). Evidence: `p03-t03-suite` (whole suite before the test edits: 75 failed / 2,222 passed, the work list), `p03-t03-mods` (all 13 edited modules after: 1,452 passed), `test_units_state.py` 40 passed. A second, accidental duplicate of the whole-suite run was started by my own command and stopped (its record deleted); it produced no evidence.

**Verification:** targeted modules per item; full suite (`p03-full`) at the end, expected count lower than 2,246 only by retired history-only tests (each named in `## Removals`); `lint-skill` on three launchers; CLI `--help` lists the intended surface; a shallow-clone run of the normal suite (P03-T02). **Risk / rollback:** one commit per item; T03 is the riskiest and is revertable as a unit. **Exit:** removal batches evidenced in `## Removals`, full regression gate green, F-019 scan clean for code and prompts.

### P04 — Current-state documentation and agent guidance

**Objective / ACs:** AC-03, AC-04, AC-05, AC-13, AC-15. **Source:** after `1507cab`. **Exclusions:** no product behaviour change beyond F-029 and the version-check relaxation below.
**Done in this phase (2026-09-20):** DEL-004 `docs/transition/` (119 files), DEL-007 `docs/verification/`, DEL-008 `docs/START-HERE.md` deleted with every reference repaired; new `docs/GETTING-STARTED.md` (13 sections, verified pieces: pinned Spec Kit install in a clean target over the network, SDLE asset copy, readiness checks, the settings merge on a project with existing settings, Git behaviour with and without a commit, the `.gitignore` lines, the generated tree after `init`, and the live hook smoke from P02; **not** verified: PowerShell forms, Linux/macOS, interactive `/hooks`, a full live conversation); README setup replaced by a pointer, Version History removed; `docs/README.md` rewritten as a current index (the "four ideas" concept text moved there); Reference Guide revision history removed and its migrate/legacy passages rewritten; troubleshooting gains `unsupported_state_version` and hooks-that-do-not-fire entries and a rewritten legacy entry; workitems page, CLAUDE.md (F-004, F-022), `scripts/README.md` (F-005) and the flow-count doc list updated; `Applies to:` version lines removed from 14 pages (`_check_version_consistency` now requires only the schema pair and validates any display copy that exists: F-008); a test keeps the guide's embedded sample equal to `requirements/todo-api.md` and another asserts the guide is the only non-transcript document that teaches the install command.
**Deferred / limits:** ADR bodies (ADR-004/005/007/008) still narrate iteration history; a note-level rewrite was not done (recorded, not silent). Engine and test comments still carry 130 + ~40 narration lines (ratchet in place). `docs/dry-runs/verification-matrix.md` still lists the previous iteration's runs; P05 replaces them with this run's results.

### P05/P06 — executed checks and drift prevention (2026-09-20)

**P05 (executed):** the guide's own bash blocks (sections 1-8) replayed unedited into an empty directory: 13 blocks, exit 0, tree equals the section 7 inventory, `workitems/` absent (`runs/20260920-p05-guide-replay.txt`, harness `replay_guide.py` inside it). Failure/location cases tested on the replayed target: missing and empty `requirements/` (`requirements_missing`), missing Spec Kit skill (`speckit_skills_missing`), engine launched from a subdirectory (root found), target nested in another repository without its own `.git` (outer root wins; `git init` fixes it). The settings merge was tested on a project that already had permissions, a `Stop` hook and its own Bash hook (all kept; idempotent). Pinned Spec Kit v1.0.6 install ran over the network in a clean project. **Not done:** the five tutorials' and sixteen dry runs' transcripts were not re-executed command by command; their commands are parsed against the real CLI by `test_units_documented_commands.py` and their claims recomputed by `test_dry_run_contracts.py`, and the integration suites drive the scenarios, but that is not a fresh execution of every tutorial step. No new interruption/resumption dry run was added; P07 covers recovery with drills. `docs/dry-runs/verification-matrix.md` is updated at P09 with this run's results.
**P06 (executed):** `tests/test_units_doc_links.py` (real local-link and anchor resolution incl. reference-style links, duplicate-heading slugs, case-sensitive paths, code/fence exclusion, non-vacuity and 9 negative fixtures; found and fixed one real broken anchor; every page under `docs/` reachable from an entry document), `tests/test_units_install_contract.py` (skill/agent/command frontmatter per its own schema with negative fixtures, the guide's file inventory equals what is tracked and installable, pinned test dependencies and the CI matrix), `tests/test_units_shipped_surface.py` (hygiene, exec bits, narration ratchet), hook registration table checks (P02). Run `p06-checks`: 439 passed. **Not done:** F-009's extension of the documented-commands scan to fenced blocks, `CLAUDE.md`, `scripts/README.md` and agent prompts (recorded; the inline-backtick scan remains); no external-link check (deliberately separate).

### P07 — Interruption, quota, and fresh-session recovery drills

**Plan (written before the drills):** separate recovery of this maintenance run from recovery of a WorkItem; use isolated sandboxes; do not exhaust quota or kill a process the drill does not own. Tooling first: `runctl.py verify` (checkpoint consistency, stale evidence, gone runners, reconstruct-a-candidate) and `reconcile`. Sandbox = a clone of the maintenance branch, so its records cannot touch the real ones; the drill kills only its own runner tree.
**Results (executed, Windows, 2026-09-20; evidence `runs/20260920-p07-*`):**

| Drill | Executed | Observed |
|---|---|---|
| R-01 plan saved, before edits | yes | STATE alone gives phase, task, next action and the same first incomplete task |
| R-02 mid-slice uncommitted files | yes | `verify` reports `content_changed_since_checkpoint`; the file is not in `changed_paths` |
| R-03 implementation done, verification not started | yes | `verification_status=not_started`, phase not in `completed_phases` |
| R-04 long runner interrupted | yes | a real runner tree killed by the drill: `run_in_progress_but_runner_gone` -> `reconcile` marks INTERRUPTED with no result claimed |
| R-05 atomic write / ledger interrupted | yes | leftover temp file, truncated STATE.json (`state_corrupt`, candidate reconstructed from journal + Git with `UNKNOWN` for unproven fields), unconfirmed ledger write (`ledger_changed_since_last_checkpoint`) |
| R-06 new Claude session, no conversation | **yes, genuinely** | a fresh `claude -p` session reconstructed path, branch, HEAD, phase/task, last action, verification status and the verbatim next action from disk, modified nothing, and reported real defects in my checkpoint |
| R-07 source or plan changed | yes | `plan_changed`, `head_moved`, `content_changed_since_checkpoint`, `claimed_evidence_bound_to_other_content` |
| R-08 product WorkItem interrupted | yes | live foreign lock warned; `resume` from disk; `not_at_gate` and `forward_jump` refused; state and audit byte-identical; other WorkItem untouched |

**Defects found by R-06 in the real records, fixed the same day:** (1) `completed_phases` stopped at P03 while P04-P06 were done; (2) an inline `## Findings` mention inside the P02 plan had been taken for the heading, splitting that plan line and pushing its Verification/Risk paragraphs past later blocks: repaired, and `runctl` insertions now key on the heading line only; (3) no P07 plan existed (this section). **Not run:** an actual quota exhaustion (never simulated by design), a Linux/macOS drill, and a session drill with the interactive UI (headless only).

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
- **F-018 confirmed** on this checkout: SKILL.md `description` = 1,068 chars and contains `v1.17`. (An earlier note here called its dashes mojibake; that was wrong: the file is valid UTF-8 and the `�`-looking glyphs were real em dashes rendered badly by the Windows console. Scan `p01` of all tracked files: 0 files with U+FFFD, 0 invalid UTF-8.)
- **F-012 confirmed:** `.claude/settings.local.json` tracked, machine paths `D:\Learning\AI\Claude Code\sdle\…`, broad `git init/add/commit` allowances; owner's uncommitted edit adds `rtk git *`/`rtk ls *`. Fix will untrack with `git rm --cached` so the owner's local file survives on disk.
- **F-019/F-020 counts confirmed:** `scripts/sdle.py` has 25 `v1.x` and 99 `T00`–`T11` references; hooks.py has 1 and 4; `.gitignore` lists `.workflow/`, `design/`, `reviews/`, `clarifications/`; hooks fence `.workflow`.
- **Tooling limit — coverage-driven candidate generation (P01-T03).** Plan §P01-8 asks for `coverage run --branch` over the suite including subprocesses.
  Set up: coverage 7.16.1 in the venv, a `.pth` calling `coverage.process_startup()`, `COVERAGE_PROCESS_START`, `parallel=True`, `source` = engine + hooks.
  Result on this host (Windows 10, Python 3.13.0): each spawned interpreter wrote a data file (145 for two small modules) but the files held **zero executed
  lines** (`line_bits` = 0, also for a bare `python scripts/sdle.py constants` under both `COVERAGE_CORE=ctrace` and `sysmon`), so `combine` reported
  "combined 8, skipped 137" and the report (28% engine, 0% hooks) is not a valid measurement. Time-boxed after four attempts; the `.pth` was removed.
  **No coverage-derived candidate list exists.** Candidates come from vulture (4, above) plus static reachability from the parser/dispatch table and the
  callers/entry-point checks §7 requires for every deletion anyway. Unexecuted-branch evidence for a specific deletion, if needed in P03, will be gathered
  by a targeted in-process trace of that function, not by suite-wide coverage. Status: open limitation, not silently dropped.
- **Vulture (min-confidence 60, run `p01-vulture-60`)** on `scripts/sdle.py` + `hooks.py`: 4 candidates only — property `security_review_md` (sdle.py:338), constants `CLASSIFICATION_REQUIRED_KEYS` (4154), `GATE_DISPOSITIONS` (5060), `BASELINE_REFERENCE_KINDS` (6003). Candidates, not deletions; P01 does reachability.

### Revalidation of the seed findings against this checkout (P01-T13, in progress)

Legend: severity H/M/L; status CONFIRMED (reproduced/observed here), HYPOTHESIS, or REFUTED. Fix column names the phase.

| ID | Sev | Status | Evidence on this checkout | Fix | ACs |
|---|---|---|---|---|---|
| F-003 | L | CONFIRMED | `docs/START-HERE.md:90` says "eight ADRs"; `docs/architecture/` holds 9 | P04 (START-HERE is retired; do not restate a count) | AC-03 AC-05 |
| F-004 | L | CONFIRMED | `CLAUDE.md:51` "The `sdle-transition-*` files beside them are this repo's migration control plane" — no such files exist | P04 | AC-03 |
| F-005 | L | CONFIRMED | `scripts/README.md:72` "`N/18` is derived from `PHASE_SEQUENCE`" (the denominator is the bound flow's) | P04 | AC-03 AC-05 |
| F-012 | H | CONFIRMED | tracked `.claude/settings.local.json` with `D:\Learning\AI\Claude Code\sdle\…` paths and `git init/add/commit` allowances; not in `.gitignore`. Note `.gitignore` is in `FROZEN` (`test_units_capabilities.py`, byte-compare vs `adbdc5e`), so the ignore rule needs that freeze replaced/declared in the same slice | P02 first slice | AC-18 |
| F-013 | H | CONFIRMED live | Real Claude Code 2.1.278 session: registration `python .claude/hooks/hooks.py dirty-tree`, cwd `…/runs` → `can't open file`, Python exit 2 → **blocking** `PreToolUse:Bash hook error`. Hook boundary probe (`hookprobe`): from `workitems/x` `python .claude/hooks/hooks.py` → rc=2. Also bare `python` (no `py -3`/`python3` fallback); launchers resolve `py -3 → python3 → python → uv` | P02: `${CLAUDE_PROJECT_DIR}`-anchored exec form + interpreter resolution + post-launch smoke check | AC-17 |
| F-014 | H | CONFIRMED | Probe: unparseable stdin → `write-fence` rc=0 no output (fail-OPEN, silent); engine file absent → `untrusted-read` and `dirty-tree` rc=0 no output; all warnings on stderr only; `main()` swallows every exception, `load_engine()` returns `None` on any failure | P02 per D-01 default (write-fence + product-agent-fence fail closed on "cannot evaluate"; scanners fail open with `systemMessage`/`additionalContext`) | AC-17 |
| F-015 | M | CONFIRMED | Probe from cwd `workitems/x`: `file_path: ".sdle/state.json"` → allowed; `"../../workitems/x/.sdle/audit.md"` → allowed; the same path from repo root or absolute is denied. Only exposure if Claude Code passes a relative `file_path` (Write/Edit normally pass absolute) | P02: resolve against payload `cwd`/`CLAUDE_PROJECT_DIR` before matching; regression cases relative, `..`, mixed separators, drive paths | AC-17 |
| F-016 | M | CONFIRMED | Matchers: settings write-fence `Write|Edit|MultiEdit`, secrets-scan `Write|Edit`, agent fences `Write|Edit|MultiEdit|NotebookEdit|Bash`. Current hooks docs (fetched 2026-09-20) list `Edit`, `Write`, `NotebookEdit`, not `MultiEdit` — verify in a live session before relying on either | P02/P06: role→event→guard→matcher table | AC-17 |
| F-018 | H | CONFIRMED | SKILL.md `description` 1,068 chars (>1,024), embeds `v1.17`, trigger "when the project has a requirements/ folder" | P02 + P06 frontmatter lint | AC-18 |
| F-019 | M | CONFIRMED | `scripts/sdle.py`: 25 `v1.x`, 99 `T00`–`T11`; `hooks.py`: 1 `v1.x`, 4 `T##`, deny reasons cite T11/`migrate-workflow` | P03 with F-011 | AC-03 |
| F-020 | M | PARTLY REFUTED | Only `.workflow/` is a retired layout name. `design/`, `reviews/` and `clarifications/` are **live** repository-level generated outputs (`gate_design` artifact `design/app/app-design.md`; `reviews/impact-analysis-*.md`, `reviews/security-review-*.md`; `clarify save` → `clarifications/<phase>-<stamp>.clarify`) and ADR-008 TR25 records them as repository-level **by design** (shared across WorkItems; scoping question deferred). Retired and to remove with F-011: `.workflow/` in `.gitignore`, `hooks.py` `FENCED` and `_project_dir()`, `Paths.legacy_workflow`, the `SDLE_OWNED_PREFIXES` entry (16 `.workflow` refs in `sdle.py`). Keep `design/ reviews/ clarifications/` and document the sharing as a known limitation | P03 (`.workflow`), P04 (document) | AC-02 AC-13 |
| F-021 | M | CONFIRMED | CI: `pip install pytest` unpinned, no dev manifest; README says Python 3.11+; CI tests 3.11 only. Local run here: 3.13.0 on Windows | P06 (D-02 default: 3.11 + newest passing) | AC-18 AC-09 |
| F-022 | L | CONFIRMED | README layout block: "9 transcript integrations" (16 dry runs, 4 integration modules); `SKILL.md`/README/`CURRENT_VERSION` assert `1.17` | P04 (derive, do not hand-maintain) | AC-03 |
| F-023 | L | CONFIRMED | no `LICENSE`/`COPYING` file | D-03 default: none added; report only | AC-04 |
| F-011 | M | CONFIRMED surface | 17 `_mig_*` steps chained in `MIGRATIONS` (1.0→1.17), explicit-only `migrate` command (`read_state` never migrates), `migrate-workflow` (`cmd_migrate_workflow`, sdle.py:6480), SKILL.md `VERSION_MIGRATION` table + lint `migration_covers_every_state_field`, 85 "legacy" refs; referenced by 20 tracked files outside `docs/transition/` incl. 9 test modules. All 69 `cmd_` handlers are registered in the parser (none unreferenced). Disposition proposed in Removals (DEL-001..) | P03 | AC-02 AC-04 |
| F-026 | H (POSIX) | CONFIRMED by inspection | `scripts/sdle.sh` is tracked `100644` (`git ls-files -s`); 27 prompt/doc sites invoke it bare (`scripts/sdle.sh <cmd>`), only 5 as `sh scripts/sdle.sh`; no `chmod` guidance anywhere. On Linux/macOS a bare call is `Permission denied` (exit 126) unless the copy sets the bit. CI passes because it uses `sh scripts/sdle.sh`. **Not executed on a Linux host** (none available); Git Bash on Windows does not enforce the bit | P02: `git update-index --chmod=+x scripts/sdle.sh`, mode-preserving copy commands + `chmod +x` readiness check in the guide, test on the index mode | AC-13 AC-15 |
| F-027 | M | CONFIRMED (docs) | `workitems/<id>/.sdle/lock` and `workitems/.active-context.json` are documented as "gitignored" (`docs/workitems/README.md:35`, Reference Guide:244) but only this **source** repo's `.gitignore` ignores them; nothing in the engine or install writes an ignore rule into a target, so `git add workitems/` in a target commits a per-session lock and a developer-local context file. Classified documentation defect; default fix = exact `.gitignore` lines in the getting-started install step and a readiness check (an engine-written `workitems/.gitignore` would be a new behaviour; revisit only if P02/P05 show the docs fix is insufficient) | P04 (P02 if a runtime fix is chosen) | AC-13 AC-15 |
| F-028 | M | CONFIRMED live (limitation) | Claude Code does not load project hooks from a parent directory: launched from a subdirectory, no SDLE hook runs (see P02 live results, probe D and C). Guard hooks are active only for sessions launched at the directory holding `.claude/settings.json`; engine choke points still apply | P04 docs + guide readiness check + troubleshooting (not fixable in product) | AC-15 AC-17 |
| F-029 | L | CONFIRMED + FIXED | The engine's secret-key pattern `sk-[A-Za-z0-9_-]{20,}` had no left boundary, so any hyphenated word containing `sk-` plus 20+ characters matched (`ri`**`sk-adaptive-gate-policy`**`.md`, `ta`**`sk-management-…`**), producing the secrets tripwire and Gate 7 manifest false positives; seen live on my own docs edit. Fix: `(?<![A-Za-z0-9])` lookbehind; tests both ways (3 negative words, 5 real-key contexts), mutation-checked | done in the P04 commit | AC-01 |
| L-001 | — | KNOWN LIMITATION | `design/app/app-design.md` (and `design/db/`) are shared across WorkItems in one repository; `design_generation` rewrites them (ADR-008 TR25, ADR-005 D7). Out of scope to relocate (would change supported layout); document plainly in the Reference Guide and getting-started | P04 | AC-05 AC-13 |
| F-024 | M | **CONFIRMED defect — OPEN, owner decision D-04 required** | Behavioural reproduction (run `p02-t07-f024-repro`, script `runs/f024-repro.py.txt`): a repository policy that tightens `gate_design` to required at LOW is in force when the WorkItem starts; `gate omit --gate gate_design` is refused `gate_required` (policy sha `928e4d3a…`). The policy file is then deleted (relaxed to the built-in floor) and the identical `gate omit` succeeds `omitted_by_policy`; the omission evidence records `policy_sha256: null`. Cause: `cmd_gate_omit` re-derives requirements from the live policy (`gate_requirements_for_state`) and only *records* the policy hash; nothing compares it with the policy the WorkItem started under, and `.sdle/policies/` is outside the hook write-fence. Not fixed here: D-04 says to ask the owner before choosing between pinning and fencing | OWNER → then P02-style fix | AC-01 |
| F-001 | L | CONFIRMED | `README.md:697` "Version History"; `docs/SDLE-Reference-Guide.md:1253` "Document Revision History" (TOC entry 21) | P04 (after F-008's check is rewritten) | AC-03 |
| F-002 | L | CONFIRMED | `docs/transition/README.md` self-labels "historical record … not part of the SDLE product"; `control-plane.sha256` records hashes of removed tooling; 119 files | P04 (DEL-004) | AC-03 |
| F-006 | L | CONFIRMED | `scripts/sdle.py:8321` "The repository pins no Spec Kit version and installs from a moving Git HEAD" contradicts `SPECKIT_SUPPORTED_VERSION = "1.0.6"` (8401) and the README pin; the comment at 8394 also cites `docs/verification/defect-stabilization-01.md` and the stabilisation iteration name | P03/P04 (comments are docs) | AC-03 |
| F-007 | M | CONFIRMED | three pinned commits + declaration machinery (see the replacement map); CI `fetch-depth: 0` | P02 (freezes that block edits) / P03 | AC-11 |
| F-008 | M | CONFIRMED | `_check_version_consistency` (sdle.py ~11016-11028) requires a README title `(vX.Y)` **and** a table row `**vX.Y**`; deleting Version History alone fails lint; `migration_covers_every_state_field` derives coverage from `VERSION_MIGRATION` rows | P03/P04, negative tests kept | AC-08 |
| F-009 | M | CONFIRMED | `tests/test_units_documented_commands.py:41-49`: scans `.claude/**` minus `agents/`, README, `docs/**` minus `transition/` and `verification/`; matcher is inline-backtick only (`INVOCATION`), so fenced blocks, `CLAUDE.md`, `scripts/README.md` and agent prompts are not checked | P06 | AC-08 |
| F-010 | M | CONFIRMED | `DOCUMENTATION_TARGETS` (sdle.py ~10905) proves listed directories exist and hold a non-empty `.md`; no link/anchor resolution and no reachability check; `docs/README.md` index is not validated | P06 | AC-08 |
| F-017 | L | CONFIRMED (no executable dependency) | test references to `docs/transition`/`sdle-transition-*` are comments/docstrings (`test_hooks.py:518`, `test_units_capabilities.py:627`, `test_units_gate_policy.py:1742`, `test_units_speckit_binding.py:887`, `test_units_workitem_runtime.py:202`, `conftest.py:94`); `test_units_documented_commands.py:48` merely *excludes* `transition`/`verification` paths. Reported gap-review result (2,246 passed after `git rm -r docs/transition`) is not reproduced here; re-run after DEL-004 | P04 | AC-03 AC-09 |

### Hook coverage matrix (P01-T10; feeds F-013..F-016 and the P06 registration check)

Role → event → guard → tool matcher → payload field. "Expected" is the coverage each role needs; "Registered" is what exists today. Nothing here is proven against a live Claude Code tool-name list yet (`MultiEdit` and the `NotebookEdit` payload key are HYPOTHESES to verify in a real session before editing).

| Role | Event | Guard | Registered matcher | Payload field read | Expected coverage | Gap / intentional difference |
|---|---|---|---|---|---|---|
| parent session | PreToolUse | `write-fence` | `Write\|Edit\|MultiEdit` | `tool_input.file_path` | every file-writing tool of the parent | `NotebookEdit` uses a different field (`notebook_path`, unverified) so a `file_path` guard cannot see it; fenced trees hold no notebooks → **intentional, document**. `Bash` writes are unfenced: the engine's audit hash chain, `doctor`, `audit verify` and the choke-point refusals are the guarantee |
| parent session | PreToolUse | `untrusted-read` | `Read` | `file_path` | reads of `requirements/`, `guidance/`, `clarifications/` | `Grep`/`Glob`/`Bash cat` also surface that content and are unscanned → **tripwire only, document** |
| parent session | PreToolUse | `dirty-tree` | `Bash` | none (reads state) | any command while `implement` has no preflight | fires on every Bash call; silent on any state-read failure (F-014) |
| parent session | PostToolUse | `secrets-scan` | `Write\|Edit` | `file_path` | same file-writing set as `write-fence` | **`MultiEdit` missing** (F-016); use one shared tool-name set |
| product agents (x4) | PreToolUse | `product-agent-fence` | `Write\|Edit\|MultiEdit\|NotebookEdit\|Bash` | none (unconditional deny) | every write-capable tool + `Bash` | intentionally broader than the parent's; redundant with the agents' read-only `tools:` grant (ADR-007 §3: declaration checked by SDLE, honoured by Claude Code) |

Registration defects common to all rows: bare `python` and a cwd-relative script path in `settings.json` and in all four agent frontmatters (F-013), interpreter not resolved like the launchers, failure postures undecided (F-014, D-01), relative paths not anchored (F-015).

## Removals

_One entry per DEL-nnn; append-only apart from status. All entries are **PROPOSED** by P01; P03/P04 execute them with the evidence noted. "No `rg` matches" is never the only evidence: parser registration, launcher/hook/prompt references and dynamic iteration (`workitem_runtime_member_names`, `dataclass_replace`) were checked._

| ID | Path / symbol | Why obsolete or redundant | Caller / dynamic-use evidence | Contract retained (R) or retired (X) | Tests / docs affected | Verification that proves it safe | Phase | ACs |
|---|---|---|---|---|---|---|---|---|
| DEL-001 | `MIGRATIONS` (1.0→1.17), 17 `_mig_*`, `migrate_state`, `cmd_migrate`, parser `migrate`; SKILL.md `VERSION_MIGRATION` table; lint `migration_covers_every_state_field` | SDLE has no historical states to upgrade; `read_state` never migrates; the chain exists only for old layouts | `migrate_state` has 3 engine refs: def, `cmd_migrate`, `cmd_migrate_workflow`; `MIGRATIONS` 5 refs all in that trio; 0 test refs to the chain itself; 3 test refs to `VERSION_MIGRATION` | **R** current-schema detection and safe refusal: a state whose `workflow_version` is not current must refuse (new explicit `unsupported_state_version` reason), never be reinterpreted or reset. **X** upgrade steps and the `migrate` command | `test_units_state.py`, `test_units_hardening.py`, `test_units_transitions.py`, `test_lint_skill.py`; SKILL.md, README, Reference Guide, troubleshooting, ADR-001/004/005/008 | new refusal test (fails on parent); state-template-vs-schema check replaces the migration-row check (F-008); full suite | P03 | AC-02 AC-04 AC-11 |
| DEL-002 | `cmd_migrate_workflow`, parser `migrate-workflow`; `Paths.legacy_workflow`; `.workflow` in `PROJECT_ROOT_MARKERS`, `SDLE_OWNED_PREFIXES`, `ACTIVE_CONTEXT_SETTERS`, hooks `FENCED`/`FENCE_REASONS`/`_project_dir`, `.gitignore`; the `legacy_state` remedy in `workitem_required` | the retired repository-global runtime; nothing binds it (ADR-008); `migrate-workflow` calls the migration chain, so it retires **with DEL-001 or not at all** | 11 engine refs to `legacy_workflow`, 23 test refs, 5 prompt/doc files; `hooks.py` fence on `.workflow` | **R** a legacy-only repo is refused cleanly, naming the supported path (`workitem create`), and the fence/markers stay only if a refusal still needs them. **X** moving `.workflow/` under a WorkItem | `test_units_workitem_resolution.py`, `test_units_workitem_runtime.py`, `test_units_hardening.py`, `test_units_governance.py`, `test_hooks.py`; README, Reference, troubleshooting §1b, workitems doc, ADR-008 | fresh-state refusal tests; write-fence probes still deny state/audit paths (no traversal or fence gap) | P03 | AC-02 AC-13 |
| DEL-003 | `.sdle/templates/` slot: `Paths.shared_templates_dir`, its `config init` mkdir/`.gitkeep`, `config show`, `validate` name set, docs | slot with **no reader**; documented as "deliberately empty" (ADR-002); an unused future placeholder | engine refs: `Paths`, `config init`, `validate`, `config show` only; nothing loads a template from it | **R** `policies/` (has a consumer) and `implementation-state/`. **X** `templates/` | `test_units_repo_config.py`, README, Reference, ADR-002 | `config init`/`validate`/`config show` tests updated; a repo that still has the directory is tolerated (not an error) | P03 | AC-14 |
| DEL-004 | `docs/transition/` (119 files) | self-declared historical; "delete this directory and everything behaves identically" | only `docs/README.md` row, ADR-008 TR26 row, and comments/docstrings in 4 test modules; F-017 (suite passed without it in a scratch clone) | **R** none needed; active contracts already live in ADRs, `CLAUDE.md`, engine | comments in `test_units_*`; `docs/README.md`; ADR-008 | full suite after deletion; link check | P04 | AC-03 |
| DEL-005 | `Paths.security_review_md` | unused property | 1 engine ref (its def), 0 tests, 0 prompts; `workitem_runtime_member_names` iterates runtime members only, not skill-root properties (confirm by running) | **R** the module file itself (`modules/security-review.md`, still required by CAPABILITY_MAP) | none | suite + lint-skill | P03 | AC-02 |
| DEL-006 | `CLASSIFICATION_REQUIRED_KEYS` | unused constant | 1 engine ref (def), 0 tests | — | none | suite | P03 | AC-02 |
| DEL-007 | `docs/verification/defect-stabilization-01.md` | dated results of a finished iteration; would be read as current evidence | linked from `docs/README.md`, ADR-009, dry-runs README + matrix, spec-kit doc; named in `sdle.py`/`conftest.py` comments | **R** fresh evidence from this run replaces it in `verification-matrix.md` | link fixes; `test_dry_run_contracts.py` metadata | link check; P05 evidence | P04/P05 | AC-03 AC-07 |
| DEL-008 | `docs/START-HERE.md` | second entry page and second start recipe; F-003 | `docs/README.md`, `FLOW_COUNT_DOCS` in `sdle.py` (10877) | **R** the "four ideas" concept text moves into README/`docs/README.md`; setup goes to `docs/GETTING-STARTED.md` | update `FLOW_COUNT_DOCS`, links | lint-skill + link check | P04 | AC-15 |
| DEL-009 | History-test scaffolding: `assert_frozen_module`, `module_units`, `STABILIZATION_01_TEST_*`, `BASELINE`/`ROLLBACK`/`T11_TEMPLATE_BASELINE`, `at_baseline`, `FROZEN`, dry-run byte pins with `DRY_RUN_SUBSTITUTIONS`; CI `fetch-depth: 0` and its comment | comparisons against three old commits; require full history | see the replacement map in the P01 subsection | **R** each protected invariant via the mapped direct assertion | `test_units_capabilities.py`, `test_units_gate_policy.py`, `conftest.py`, `ci.yml` | each replacement passes and fails when its property is broken; shallow-clone run | P02 (settings/`.gitignore`/hooks freezes) then P03 | AC-11 |
| DEL-010 | `.claude/settings.local.json` (tracked) | developer-local, machine paths, broad allowances (F-012) | not referenced by engine, hooks, tests, docs | — | `.gitignore`, hygiene check | `git ls-files` clean; local file survives on disk | P02 | AC-18 |
| DEL-011 | README "Version History" and Reference Guide "Document Revision History" | version-history narration (AC-03) | `_check_version_consistency` and its tests parse the README version table (F-008) | **R** current version metadata where operationally required | rewrite the check first | lint-skill + negative test | P04 | AC-03 AC-04 |
| KEEP | `GATE_DISPOSITIONS`, `BASELINE_REFERENCE_KINDS` | vulture reports them, but each is a contract constant referenced by tests (`test_units_gate_policy.py:405,1265`, `test_units_baseline.py:515`) | — | R | — | — | — | — |

## Directory inventory

Authority for runtime/config paths is `Paths` in `scripts/sdle.py` (lines 107-330) and `PROJECT_ROOT_MARKERS` (`workitems/index.md`, `.workflow/state.json`, `.git`, `.sdle/config.json`, nearest ancestor wins);
for skill lookup `skill_roots` (project `.claude/skills/sdle`, repo root, then `~/.claude/skills/sdle`). No second path registry is created. Legend — scope: **S** source repository, **T** target project with SDLE installed,
**R** runtime/artifacts generated in a target. Status: req = required, opt = optional, gen = generated. Tracked/ignored is the *source repo's* `.gitignore`; a target has its own (see F-027).

| Scope | Observed path | Canonical path | Purpose / owner | Required stage | Creator | Tracked/ignored | Consumers | Discrepancy | Disposition | Verification |
|---|---|---|---|---|---|---|---|---|---|---|
| S,T | `scripts/sdle.py` | same | deterministic core | req, pre-launch | install copy | tracked | launchers, hooks (imports it), tests | none | keep | install-contract check (P06) |
| S,T | `scripts/sdle.sh`, `sdle.ps1` | same | launchers | req, pre-launch | install copy | tracked | prompts, commands | `sdle.sh` mode 100644 (F-026) | fix mode, mode-preserving copy | index-mode test (P02) |
| S | `scripts/README.md` | same | maintainer doc for the engine | source-only | authors | tracked | maintainers | F-005 stale denominator claim | keep, fix in P04; **not installed** | link check |
| S,T | `.claude/skills/sdle/` (`SKILL.md`, `modules/` x5, `templates/state.json`) | same | orchestrator prompts + the only state template | req, pre-launch | install copy | tracked | Claude Code, engine `load_constants` | F-018 description | keep, fix F-018 | lint-skill + frontmatter lint |
| S,T | `.claude/commands/` (9) | same | slash-command entry points | req | install copy | tracked | Claude Code | none | keep | frontmatter lint |
| S,T | `.claude/agents/sdle-*.md` (4) | same | read-only product subagents | req | install copy | tracked | parent session | none | keep | lint-skill agent checks |
| S,T | `.claude/hooks/hooks.py` | same | five guardrail hooks | req | install copy | tracked | settings.json + 4 agent frontmatters | F-013/14/15/16 | fix in P02 | hook probes + post-launch smoke |
| S,T | `.claude/settings.json` | same | hook registrations (merged into target's) | req | install **merge** | tracked | Claude Code | bare `python`, cwd-relative (F-013); byte-frozen by a history test | fix P02; freeze replaced first | registration-table check (P06) |
| S | `.claude/settings.local.json` | none | developer-local permissions | **never shipped** | developer | **tracked (defect)** | Claude Code locally | F-012 | untrack (`git rm --cached`), ignore, hygiene check | P02/P06 |
| S | `.sdle/config.json` + `policies/ templates/ implementation-state/` (`.gitkeep` x3) | `Paths.config_*` | the source repo's own `config init` output | opt (target) | `config init` | tracked | `read_repo_config`, `validate`, `config show` | see slot rows below | see slot rows below | fresh-clone `validate` (P03) |
| S,T | `.sdle/policies/governance-policy.json` | `Paths.governance_policy_file` | optional policy override that may only tighten | opt | user | tracked | `read_governance_policy` | F-024 mid-flight relaxation untested | keep; test in P02 | behavioural test |
| S,T | `.sdle/templates/` | `Paths.shared_templates_dir` | "shared templates" | opt | `config init` | tracked (`.gitkeep`) | **none** (only `config init` and `validate` name checks) | dead extension slot | **removal candidate** (engine slot + docs), decide P03 | grep + `validate`/`config init` tests |
| S,T | `.sdle/implementation-state/` | `Paths.implementation_state_dir` | "implementation-transition metadata", empty slot | opt | `config init` | tracked (`.gitkeep`) | none in engine; **this run** keeps maintenance records here | slot documented as "no schema/producer/consumer" | keep, give it a current definition (records of repository-maintenance runs) | docs + `validate` |
| S | `.sdle/implementation-state/repository-cleanup/` | — | this run's records | n/a | this run | tracked | none | scanned by two invariant-7 tests (F-025) | path-specific exclusion done (adbe8e1) | negative test |
| S,T | `.sdle/baseline.json` | `Paths.baseline_file` | repository baseline | gen | GREENFIELD/BROWNFIELD completion | tracked (absent here) | ITERATIVE init | none | keep | baseline tests |
| S | `requirements/todo-api.md` | — | manual-run fixture in the source repo | source-only | authors | tracked | `start workflow` in place; **no test reads it** (fixtures are generated) | candidate sample for the guide | decide P04 (source or new sample) | sample passes `preflight` |
| T | `requirements/` (+ at least one valid `.md`) | `<project>/requirements/` | user ground truth, never edited by SDLE | **req, pre-launch** | user | user's | `preflight`, `requirements_check` | minimum content unstated in README | document exact sample in guide | replay from clean target (P05) |
| T | `guidance/<phase>.md` | `<project>/guidance/` | optional per-phase steering, read as data | opt | user | user's | phase execution | none | document as optional | guide |
| T | Spec Kit output: `.specify/`, `.claude/skills/speckit-*` | as produced by `specify init` (pinned 1.0.6) | Spec Kit scaffolding, repo-wide | req, pre-launch | `uvx …@v1.0.6 specify init` | `.specify/` ignored in source; target's choice | capability detection, `feature resolve` | local `specify` is 0.15.0, not the pin | document the exact pinned command | P05 live smoke (network) |
| T | project `.git` | project root | project-root marker + branch/diff evidence | **req, pre-launch** | user (`git init`) | n/a | root discovery, manifest, branch guard | a target inside another repo without its own `.git` resolves to the outer root | guide: `git init` + identity + initial commit first | readiness check |
| R | `workitems/index.md`, `workitems/<id>/workitem.json` | `workitems_root`, `metadata_file` | registry + identity; written only by the engine | gen at `workitem create` | engine | **versioned** | resolution ladder, `validate` | none | keep, write-fenced | hooks + tests |
| R | `workitems/<id>/.sdle/` (`state.json`, `audit.md`, `lock`, `execution.json`, `evidence/`, `governance.json`, `reviews.json`, `discovery.json`, `implementation-manifest.md`, `completion-summary.json`) | `Paths.runtime` and members | WorkItem runtime | gen | engine | versioned except `lock` | all runtime commands | `lock` ignored only in source (F-027) | keep; document ignore lines for targets | guide replay |
| R | `workitems/<id>/specs/<feature>/` | `Paths.speckit_specs_root` | Spec Kit feature artifacts, WorkItem-scoped | gen at `feature resolve` | Spec Kit + engine move | versioned | gates spec/plan/tasks/analyze | none | keep; write-fence carve-out exists | binding tests |
| R | `workitems/.active-context.json` | `active_context_path` | developer-local active WorkItem | gen | `workitem use`/`init` | ignored (source only) | resolution rung 4 | F-027 | document ignore | guide |
| R | `design/`, `reviews/`, `clarifications/` | repo-relative, fixed | repo-level generated outputs (ADR-008 TR25, by design) | gen | orchestrator / `clarify save` | ignored in source | gates design/security, impact analysis | L-001 shared across WorkItems | keep + document limitation | docs review |
| R | `.workflow/` | `Paths.legacy_workflow` | retired global runtime; migration source + root marker | **retired** | — | ignored | `migrate-workflow`, `_project_dir`, hooks fence | F-011/F-020 | remove with the migration surface (P03) | fresh-state refusal tests |
| S | `docs/transition/` (119 files, 2.5 MB) | — | migration record; self-declares "not part of the product" | none | — | tracked | only `docs/README.md`, ADR-008 TR26, test comments | historical | **delete** (P04) after comment cleanup | F-017 (suite green without it; re-run) |
| S | `docs/verification/defect-stabilization-01.md` | — | dated results of a finished iteration | none | — | tracked | README index, ADR-009, dry-runs, spec-kit doc, `sdle.py`/`conftest` comments | historical results | delete; links repointed to fresh evidence (P04/P05) | link check |
| S | `docs/START-HERE.md` | — | concept + entry page | replaced | — | tracked | `docs/README.md`, `FLOW_COUNT_DOCS` in `sdle.py` | F-003; second start recipe | fold into `docs/GETTING-STARTED.md` + README, update `FLOW_COUNT_DOCS` | link + lint |
| S | `tests/`, `.github/workflows/ci.yml`, `.gitattributes`, `.gitignore` | — | source-only | source-only | authors | tracked | CI | `.gitignore` byte-frozen by a history test; `fetch-depth: 0` | see replacement map | CI + shallow-clone run |

**Empty / placeholder-only classification (P01-T09).** No untracked empty directories exist in the checkout (`find -type d -empty`, `__pycache__` excluded; hidden files counted).
Placeholder-only directories (tracked `.gitkeep` only): `.sdle/policies/`, `.sdle/templates/`, `.sdle/implementation-state/` — all three are what `config init` writes (`mkdir` + `.gitkeep`), i.e. **created on demand by a supported step**, so a target never depends on a clone preserving them.
Proposed dispositions: `policies/` keep (active extension point, consumer exists); `templates/` remove the slot (no consumer; `config init`, `validate` name set, `Paths`, docs, `test_units_repo_config`); `implementation-state/` keep with a current definition (it holds these records).
The `.gitkeep` in `implementation-state/` is no longer needed once records are tracked. Whether a fresh clone of this repo works without the other placeholders is a **P03 test** (run `validate`/`config show` in a clone with them removed), not an assumption.

## Documentation map

Fact/contract → source of truth → canonical document → derived examples → verification. A derived view never restates a fact it can ask the engine for.

| Fact / contract | Source of truth | Canonical document | Derived views | Verification today → intended |
|---|---|---|---|---|
| Flow membership, phase and gate counts | `GREENFIELD_V1_PHASES` + `FLOW_PHASES` in SKILL.md; `sdle.sh constants` | `docs/lifecycle/README.md` | README, Reference Guide, tutorials, dry runs, START-HERE | `lint-skill` flow-size rules (`FLOW_COUNT_DOCS`, `FLOW_HEADLINE_DOCS`) → keep; drop START-HERE from the list |
| First-run setup (prerequisites, install, sample input, launch, first interaction) | the install boundary (Directory inventory) + pinned Spec Kit command | **`docs/GETTING-STARTED.md` (new, P04)** | README (short link only), tutorials (link + flow deltas), dry-run 01 setup (link) | none today → guide-alone replay (P05) + link/consistency check (P06) |
| Command surface and refusals | argparse tree in `sdle.py`, `Refused(...)` reasons | Reference Guide (commands) + `docs/troubleshooting/` (refusals → recovery) | README command table, `scripts/README.md`, prompts | `test_units_documented_commands.py` (selected inline forms) → extend to fenced blocks, `CLAUDE.md`, `scripts/README.md`, agents (F-009) |
| State schema and defaults | `.claude/skills/sdle/templates/state.json` | Reference Guide Appendix B | tutorials' state dumps | `migration_covers_every_state_field` (history-shaped) → template-vs-schema check (F-008) |
| Directory layouts and ownership | `Paths`, `PROJECT_ROOT_MARKERS` | `docs/workitems/README.md` + guide's inventories | README layout block, ADR-002 | prose only → install-contract + path checks (P06) |
| Governance, risk floors, gate derivation | `GOVERNANCE_POLICY_BUILTIN` | `docs/risk-and-gates/README.md` | Reference Guide, tutorials | invariant-7 restatement search (F-025 fix) → keep |
| Enforcement split (engine vs Claude Code vs convention) | ADR-007 §3 | `CLAUDE.md`, ADR-007, capability modules | agent prompts | `test_a25_*` → keep; extend to hook docs |
| Spec Kit pin and capability contract | `SPECKIT_SUPPORTED_VERSION`, capability detection | `docs/spec-kit-integration/README.md` | README, guide | stale comment F-006; README/dry-run 01 restate the command → single command in the guide |
| Dry-run scenarios and their claims | `docs/dry-runs/*.md` + cited tests | `docs/dry-runs/README.md`, `verification-matrix.md` | README | `tests/test_dry_run_contracts.py` → keep, refresh metadata in P05 |
| Version / schema identifiers | `CURRENT_VERSION = "1.17"` (state `workflow_version`), SKILL.md frontmatter/heading | SKILL.md, state template | README title, Reference header | `_check_version_consistency` requires a README version table → rewrite (F-008, DEL-011) |
| Documentation index | `docs/README.md` | `docs/README.md` | root README | substring check on directory names (F-010) → real link + anchor validation + reachability |

**First-run consolidation list (P01-T12).** Every place a new user is told how to start, and what is missing from the whole set:
- README "Quick Start" (prereqs, pinned `uvx` commands, "Install This Skill" 5-item copy list, requirements, `start workflow`) — the current de-facto recipe; states no Git setup, no identity, no initial commit, no copy-mode guidance (F-026), no exact settings merge, no minimum requirements content, no readiness check, no hook smoke check, no `.gitignore` lines (F-027).
- `docs/START-HERE.md` — concept ("four ideas") and routing; links to the README recipe. Concept text is kept, relocated.
- `docs/dry-runs/01-happy-path.md` "Setup" — the only place that shows `git init -q`, `git add -A && git commit`, and copying `requirements/todo-api.md`; its "copy SDLE in … and merge settings" is a comment, not a command.
- `docs/tutorials/greenfield.md` "1. Before you start" — states that `init` refuses `requirements_missing` and that **twelve structured requirement checks all block**; a sample for the guide must satisfy them (verify against the engine, do not pad).
- `scripts/README.md`, Reference Guide, troubleshooting — mention preflight/bootstrap order; must link to the guide instead of re-explaining.
- Gaps to close in `docs/GETTING-STARTED.md`: project-root discovery needs the target to be its own Git repo (else an outer repo's root wins); the one primary entry point (D-05: `start workflow`, `/sdle-start` as verified equivalent) — SKILL.md auto-triggers on "a `requirements/` folder" (F-018); pre-launch vs post-launch hook verification; `settings.local.json` never copied; `.gitignore` lines for `lock` and `.active-context.json`; launch from the project root.
- Engine-embedded doc paths that change with this consolidation: `FLOW_COUNT_DOCS` lists `docs/START-HERE.md`; `DOCUMENTATION_TARGETS`, `REPO_DOCS` (sdle.py ~10871-10905).

**T07 (agents and remediation path).** Prompt-level review found the contract coherent: an agent returns findings as its final message and records nothing; the parent records with `artifact review --actor-type agent --actor-name <agent>` against the artifact's current fingerprint (the record goes stale when content changes); a human approves at the gate in the parent session; `--actor-name` is attribution, not attestation. No defect found at this depth. Behavioural coverage that blocking findings and stale reviews stop approval lives in `test_units_artifact_review.py` and `test_units_gate_artifacts.py` (part of the baseline pass, not individually re-run here).

## Independent review

_P08._

## Owner decisions

Recorded 2026-09-20. The owner answered none of the §12 questions (their only instructions were to continue and to note reasons), so each default applies from the phase that needs it; a later answer supersedes.

| ID | Decision | Applied answer | Needed by | Status |
|---|---|---|---|---|
| D-01 | Hook failure posture per guard (F-014) | **Default:** `write-fence` and `product-agent-fence` fail closed when the hook runs but cannot evaluate the payload; `untrusted-read`, `dirty-tree`, `secrets-scan` stay fail-open but announce the degraded state through JSON `systemMessage` (user) and `additionalContext` (Claude) — stderr alone is not acceptable; visibility verified in a live session. A hook that cannot start is F-013 + the post-launch smoke | P02 | default applied when P02 starts |
| D-02 | Supported Python matrix (F-021) | **Applied (default):** CI matrix Python `[3.11, 3.13]` on ubuntu + windows, test dependencies pinned in `requirements-dev.txt` and installed from it; README and the guide say "3.11 or newer (tested on 3.11 and 3.13)". Local evidence: 3.13.0 on Windows only; 3.11, and Linux, are exercised only by CI, which has **not** run | P06 | applied; CI result unverified |
| D-03 | License (F-023) | **Default:** add none; report the absence as an owner action | P09 report | pending |
| D-04 | Active WorkItem and policy change (F-024) | The behavioural test **did** show a mid-flight relaxation dropping a gate required at start (see F-024), so the default's exception applies: **reported as a confirmed defect; no code change made; the owner is asked.** Options — **(1) pin at start (recommended):** record the required-gate set (or policy sha) in the governance record at `init` and treat a gate as omittable only if it is omittable under both the pinned and the live policy, so a tightened policy still applies and a relaxed one cannot weaken an in-flight WorkItem; engine + tests, `.sdle/implementation-state/` unaffected. **(2) fence `.sdle/policies/`** in the write-fence hook: a tripwire only (Bash and a human editor are unaffected) and it blocks the model from legitimate policy edits. **(3) document only:** keep live derivation and state that a policy edit governs the next decision. | P02 | **OPEN — awaiting owner**; carried to the final report as an unresolved item |
| D-05 | Primary beginner entry point (F-018) | **Applied (default):** `start workflow` is primary, `/sdle-start` the verified equivalent (SKILL.md routes `start workflow` and `begin` to `/sdle-start`); the skill description was narrowed so it no longer auto-triggers on a bare `requirements/` folder | P04 | applied |
| D-06 | Purging `settings.local.json` paths from history | **Out of scope** (no history rewriting); report only that the paths remain in Git history | — | applied |
| D-07 | Codex unavailable/unauthenticated for P08 | **Not triggered:** codex-cli 0.151.0 installed, "Logged in using ChatGPT", required flags present (P00-T05). Not installed or logged in on the owner's behalf | P08 | applied |
| D-08 (new) | May the `.sdle/templates/` slot (no reader) be removed? (DEL-003) | **Default:** yes, remove the slot; keep `policies/` and `implementation-state/`; tolerate an existing directory | P03 | pending |

## Final report

_P09._
