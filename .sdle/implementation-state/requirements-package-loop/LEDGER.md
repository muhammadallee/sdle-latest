# LEDGER — requirements package, SA handoff, traceability, bounded loop

## Current status
PLAN_AND_IMPLEMENT complete (R1, R2, R3), local only, not pushed. Branch `enh/requirements-package-loop` cut from `1c557d1`. Baseline recorded, G04/G06/G08 reproduced, `PLAN.md` written. Codex plan review rounds 1 and 2 done and applied (16 findings accepted, 0 rejected). PLAN_ONLY deliverables complete.

## Decisions
| # | Decision | By |
|---|---|---|
| L1 | D02: no normalized package exists. Contract is designed from brief §3; `reference/SRS.docx` (the owner's reference SRS, ID families UC, ST, SR, EV, PRE, POS, BF) is the worked source example. R1 not blocked. `SRS.docx` is **not committed** (names client staff) until the owner confirms. | owner |
| L2 | **D09 overridden.** The loop's default iteration limit lives in the **pinned governance policy**, not `.sdle/config.json` (ADR-002 forbids lifecycle reads of config; pinned by `CONFIG_REFERENCE_SITES`). Same policy holds D10's blocking switch. | owner |
| L3 | Test edits beyond the plan's first reading, approved by owner: `tests/conftest.py` `MAINTENANCE_RECORDS` gains `requirements-package-loop`; `tests/test_units_capabilities.py` pinned count 3 to 4 (+ docstring). Cause: the restatement search flagged `UNKNOWN` in the copied `runctl.py`. | owner |
| L4 | R2 trace enforcement is a no-op unless the WorkItem binds files under `requirements/packages/` and an approved package exists (legacy WorkItems and the 3,846-test baseline unaffected). | plan |

## Defect (mine): the client SRS was committed locally and exposed to Codex
`docs/enhancements/requirements-package/reference/SRS.docx` (it names client staff) was committed by `git add -A docs` in commit `4b42fd5`, against decision L1 ("not committed until the owner confirms"). Consequences: it is present in local commits from `4b42fd5` on, and in the frozen worktrees given to Codex for **R1 round 2, R2 round 1, R3 round 1 and R3 round 2** (a read-only sandbox, but the file was readable by the reviewer, so it may have been sent to the external service). Nothing has been pushed. Fixed going forward: the file is untracked and the directory is git-ignored. Purging it from the local history needs a history rewrite, which is destructive, so it is **left for the owner to decide**.

## Defects / grounding mismatches
- G17: harness is `.sdle/implementation-state/requirements-refinement/stage2/`, not `requirements-refinement/stage2/`. Next ADR is 016.
- G04 **refined**: drift check is prompt-only. Case A (edit between `gate_tasks` approval and analyze start) IS caught. Case B (edit during analyze, then the unconditional `drift rebaseline --gate gate_tasks`) is re-baselined with no re-approval, no diff. Reproduced: lower severity than the brief states, still real.
- G06 **confirmed**: a tick appended to tasks.md after `gate_analyze` approval reports `drifted = [gate_tasks, gate_analyze]`. Corollary found: `gate approve` after such an edit is refused `review_stale` (the review binds the old SHA), (corrected after Codex PR-R1-004: re-approval *does* succeed once the current content is re-reviewed, so a direct audited rebaseline is a deliberate D08 choice, not a necessity).
- G08 **confirmed**: source file edited after a passing `manifest build` + review; `gate approve gate_implement` exits 0.
- Local `rtk` output filter prints "No tests collected" for `pytest --collect-only`; use `rtk proxy python -m pytest ...` for raw output.

## Review dispositions
**Codex round 1** (plan; run `20261006T112400-stage2-codex-plan-r1b`, codex-cli 0.160.1, reviewed commit 9458a04, 9 findings, all confirmed against source and **accepted**; PLAN.md §10 maps each to its fix): PR-R1-001 tree digest projection; -002 per-WorkItem package pin + `package adopt`; -003 remove post-analyze rebaseline instead of `--expect-sha`; -004 reconcile rationale corrected (I had overstated: re-approval works after a fresh review), snapshot + unrelated-drift rule; -005 loop guarantee reworded (external `converge` order is convention); -006 immutable approved revisions + ID-history rules; -007 pinned policy lacks new keys, default rule; -008 universal-vs-scoped stated; -009 `package reseal`. Rejections: none (nothing appended to `claude-review-rejections.md`).
**Codex round 2** (run `20261006T113028-stage2-codex-plan-r2`, reviewed commit 428d8cd, 7 findings, all confirmed and **accepted**, defects introduced or left by round 1 fixes): PR-R2-001 the digest projection misdescribed `implementation_exclusions` (it is narrow, not `SDLE_OWNED_PREFIXES`); -002 public rebaseline refused for the whole loop; -003 pin check before first write at every `apply_advance` caller (`skip` appends audit first); -004 HOTFIX has no task gates so snapshot authority defined; -005 ticks allowed inside accepted convergence sections; -006 post-`init` route is staging + `import --replace` + adopt (refinement is pre-init only); -007 `unmapped_verification_blocks` moves to R2. Rejections: none. Round 2 not reached by Codex: executed reproductions, real Spec Kit, every test body, the client SRS.
**R1 implementation review, round 1** (run `20261006T151216-stage2-codex-impl-r1-1`, reviewed 01776da, 11 findings, all confirmed by reading and **accepted**, IR-R1-004 and -010 in modified form; fixes in commit 4b42fd5):
- IR-001 symlinks/junctions followed: links refused (`package_symlink_refused`), `package_files_on_disk` never lists or follows them, `_require_contained` proves containment of every package directory before use.
- IR-002 manifest paths: every path a manifest names must be a plain relative path (`_relative_path_problem`); source paths also resolve inside the repository (`package_source_unsafe`).
- IR-003 incomplete revision reused after a crash: `_publish_revision` builds beside the destination, verifies the digest, `os.replace`s into place (os.replace pin 3 to 4), and verifies any existing revision before reuse (also in `_approved_manifest`).
- IR-004 ID history: **modified.** A statement edit under an approved id stays allowed (a clarification is not a new requirement, and whether an edit changes meaning is the fidelity review's judgement, not the engine's). Enforced instead: `kind` and work item are immutable (`package_id_changed_kind`, `package_id_moved`) and the retired set is monotonic across approved revisions (`package_retirement_dropped`), which by induction makes it cumulative.
- IR-005/-008 adoption and binding: `package adopt` re-runs the handoff precondition (approved, same work item present and READY, binding **exactly** the work item's file plus its shared files, both directions).
- IR-006 reassessment: adoption of a moved revision records the governance execution id it was made against (`reassessAfter`); progression is refused `package_reassessment_required` until a different assessment exists.
- IR-007 pin at reject and remediate: `package_pin_precondition` added to `cmd_gate_reject` and `cmd_remediate_begin`, ahead of any write.
- IR-009 ReDoS: id patterns are a closed language (literals, `\d`, `[...]`, `(?:a|b)`, bounded `{n}`/`{n,m}`); traceability scanning is size-capped.
- IR-010 lock: **modified.** The mutex stays a mutex (same primitive as the architecture catalog and refinement), stale limit 60 s to 600 s, and the approval re-reads the ledger and digest immediately before writing so a paused writer whose lock was broken refuses (`package_locked`) instead of overwriting.
- IR-011 ledger structure: every record field, type and hash format is validated; malformed is `IntegrityError`.
Test note: on this Windows account file symlinks cannot be created, so the two file-symlink tests skip here (directory junctions are exercised instead); Linux CI runs both.

**R1 implementation review, round 2** (run `20261006T152245-stage2-codex-impl-r1-2`, reviewed 8b1d4b8, 9 findings, all verified (several by executed probes) and **accepted**; fixes in the commit that follows this entry):
- IR-R2-001 adopting twice dropped the reassessment marker: the marker is carried across a same-revision adoption.
- IR-R2-002 id patterns still backtracked (`\d{0,99}` repeated): the language is now deterministic, with exact `{n}` only and groups of same-length distinct alternatives (the documented `(?:FR|AC|NFR)` form needed splitting into two families; the fixture was changed, not the rule).
- IR-R2-003 age-based lock breaking: replaced by an **OS-held lock** (`fcntl.flock` / `msvcrt.locking`), released by the OS when its holder dies and never breakable by age. This supersedes the round-1 "modified" treatment of IR-R1-010.
- IR-R2-004/-009 import: the staging directory is read once into a snapshot, written to a private directory, scanned and validated there, and the package is replaced by two renames (never edited in place); a link inside the old package is refused.
- IR-R2-005 approval storage: `_require_contained` now guards the ledger, lock and revision store.
- IR-R2-006 retired ids: unique, and colliding with no active id family.
- IR-R2-007 malformed types: path checks run only on type-validated values.
- IR-R2-008 `skip`: the pin is checked before its first (pending-confirmation) save.
Pins moved on purpose: write_atomic 48 to 49, os.replace 3 to 7.
Because these fixes are material (lock mechanism, import redesign), the **R1 scope is reviewed again** together with R2 in the R2 round-1 review (everything since 8b1d4b8), rather than as a third stand-alone R1 round.
Evidence of a real-world false-positive found by the suite, and what was done: two existing tests that run a real `pytest` inside the project failed because the run left `.pytest_cache` / `__pycache__` in an unignored tree, which the tree digest counted as a change during the run. The digest now skips a closed set of tool caches (`.git`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `node_modules`, `*.pyc`); no existing test was edited.
**R2 implementation review, round 1** (run `20261006T*-stage2-codex-impl-r2-1`, reviewed 422b634, 5 findings, all confirmed (several by executed probes) and **accepted**):
- IR-R2R1-001 the verification record could be edited into an approved exclusion: it is now hash-chained like the approval ledger and every disposition's required fields are checked on every read (`excluded-approved` needs a reason, an approver and their words; `verified-mapped` needs its report and evidence id).
- IR-R2R1-002 submodules were absent from the tree digest: a gitlink directory is walked, so an edit inside it moves the digest.
- IR-R2R1-003 any file could be "mapped": `manifest build --junit` now captures the report's path and digest with the evidence, and `verification map` reads only that report, only while unchanged (`verification_junit_not_captured`, `verification_junit_changed`, `manifest_junit_missing`). PLAN §3.2 had said exactly this; the first implementation had not.
- IR-R2R1-004 failed mappings outlived their run: every disposition derived from a run now expires with it; one a person typed in does not.
- IR-R2R1-005 concurrent verification commands could lose a record: per-WorkItem OS-held lock (`workitem_mutation_lock`, shared with the package lock's primitive `_os_held_lock`) around verification, loop and task-list commands.
Defect found while writing R3 tests, pre-existing: `manifest build` without git iterated an `Exclusions` object (`for prefix in excluded`) and crashed; fixed with `excluded.hides`.
R3 is reviewed together with these R2 fixes (everything since 422b634).
**R3 implementation review, round 1** (run `20261006T181432-stage2-codex-impl-r3-1`, reviewed cfc2689, 9 findings, all confirmed and **accepted**):
- IR-R3R1-001 drift re-approval of `gate_implement` bypassed the predicate: `_approve_drift` now uses `implementation_ready` for that gate.
- IR-R3R1-002/-004 the test inventory: `manifest build --junit`'s captured report is parsed at the manifest step into the complete case list and the failing set (recorded in the step); `test_expectation_change` is now any case present in the previous iteration (or the run's baseline) and gone, and the progress digest hashes the failing test names, with the runner status only as the fallback where no report was captured. The historical-disposition-row comparison is gone.
- IR-R3R1-003 acceptance tests weakened with the name kept: at `loop begin` the files that name an in-scope criterion are snapshotted; a later iteration whose original lines were removed or changed (additions are not weakening) stops for a person. Structural and conservative: whether an edit is semantically equivalent cannot be told from the text, so it is a person's call, and `loop begin` re-enters.
- IR-R3R1-005 unticking: only `[ ]` to `[x]`/`[X]` is a tick.
- IR-R3R1-006 crash recovery: `tasks reconcile` and `loop begin` save state before the loop record, so a crash leaves the baselines moved and the record one step behind; a retry accepts the same change (the delta is taken from the still-old snapshot) and finishes.
- IR-R3R1-007 `manifest build` and `artifact review --type code-review` of the manifest consult the active loop and refuse out of order (`loop_output_precondition`), so an output is not produced twice outside the recorder.
- IR-R3R1-008 the two vacuous tests were rewritten as real scenarios (two iterations; ambiguity and environment blocker in separate tests).
- IR-R3R1-009 symlinks inside a gitlink are hashed like top-level ones.
Pin: write_atomic 52 to 53 (the tagged-test snapshot). R3 round 2 follows on the fix diff.
**R3 implementation review, round 2** (run `impl-r3-2b`, reviewed d1f06a0; the first attempt `impl-r3-2` was killed by the harness's memory reaper and produced no review; restarted after the owner freed memory, on a worktree without the SRS): 3 findings, all confirmed (by executed probes) and **accepted**:
- IR-R3R2-001 pending convergence was forgotten when a new run began: `loop_converge_precondition` now reads the latest converge of every run.
- IR-R3R2-002 the producer precondition allowed a second manifest or review in the crash window: `manifest build` and the code review of the manifest, while a run is open, check, produce and record the production under the WorkItem lock; a retry records what exists (`loop_step_duplicate`), and a stale rebuild clears the markers.
- IR-R3R2-003 truncated inventories hid removals past case 5000: an inventory is complete or refused (`loop_inventory_too_large`).
The scoped diff of these three fixes was re-reviewed (run `impl-r3-3`); see below.
**R3 scoped re-review of the round-2 fixes** (run `impl-r3-3`, reviewed 58b96b9, 3 findings, all confirmed and **accepted in one modified form**): all three were defects of the *production marker* added for IR-R3R2-002 (a refused manifest wedged the iteration; the check-then-lock window; a crash between publication and marker). Rather than add a recovery transition, a lock-before-decision path and a persisted intent, the marker mechanism was **withdrawn**: the guarantee is on what the loop *records* (one evidence and one review per iteration, each used once, the latest standing), and an extra output produced in a crash window is history, never deleted, never recorded. This is stated in ADR-017 §6. IR-R3R2-002 is therefore answered by scoping the guarantee, not by preventing the extra output. IR-R3R2-001 (pending convergence across runs) and IR-R3R2-003 (complete inventories) stand as fixed. Net code: the reviewed round-2 behaviour of `loop_output_precondition` plus the two retained fixes; the withdrawal was not re-reviewed by Codex (it returns to the shape reviewed in round 2 and removes code), which is stated in the report.
Round-1 coverage Codex stated it did not reach: executed reproductions, Spec Kit v1.0.6 itself, all 3,846 tests individually, full `run_sync_checks`.
Earlier attempts were infrastructure failures, not reviews: `20261006T105902-stage2-codex-plan-r1` BLOCKED (config model `gpt-6.1-sol` rejected for ChatGPT login, HTTP 400; resolved by the owner), and a launch failure from a missing prompt file (my `&&` chain).

## Test runs
Environment: Windows 10, Python 3.13.0, git 2.46.2, Codex CLI 0.151.0 (ChatGPT login). G16's baseline was Linux/Python 3.12.3.

| Run | Result |
|---|---|
| `lint-skill` at `1c557d1` | pass, `failed: []` |
| `pytest --collect-only` | 3,846 collected (= 3,822 passed + 24 skipped in G16) |
| Full suite, 8 foreground shards (`shards.json`; run records in `runs/`) | shards 1,3,4,5,6,8 PASS; shard 2 and 7 each 1 failure, both the maintenance-records search (L3). Re-run after the L3 edits: `test_units_capabilities.py` + `test_units_discovery.py` 217 passed. Counts: 260+446+505+329+1221+297+577+211 = 3,846 |
| Throwaway G04/G06/G08 repro (scratchpad, not committed) | 2 passed, outputs above |

Shards 2 and 7 were not re-run whole after L3; the two failing tests were re-run and pass. A whole-suite run on the final tree is required at each release.

## Final test run (R8)
`python -m pytest` in 18 foreground shards on the final tree (4,214 collected): **4,211 passed, 3 skipped, 0 failed**; four shards failed once and were fixed and re-run: the docs-link test (DELIVERY.md not linked), the `artifact_shas` writer-set pin (`cmd_tasks_reconcile`), the `manifest build` flag pin (`--junit`), and a flaky evidence lookup in my own findings test. `lint-skill`: 48 checks, none failed. The skips are file-symlink tests this Windows account cannot create (Linux CI runs them). Records: `runs/*final-*.json`.

## Next action
None in PLAN_ONLY. On owner go-ahead for PLAN_AND_IMPLEMENT: start R1 per PLAN.md.
