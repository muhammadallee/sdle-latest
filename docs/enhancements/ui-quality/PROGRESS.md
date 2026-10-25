# UI quality enhancement — progress

Resumability log for the UI-quality enhancement. The plan is
`.sdle/implementation-state/ui-quality/PLAN.md`; dispositions and test runs are in
`.sdle/implementation-state/ui-quality/LEDGER.md`. **The commit SHA recorded here is the
authority for a checkpoint**, never a tag.

## Status

| Phase | Status | Checkpoint SHA | Notes |
|---|---|---|---|
| A-build | awaiting owner | `d915eb6` (last implementation commit; the record commit that adds this row is its descendant) | built, unmeasured. Open: OA-1, OA-2 (both concern A-measure) and OA-3; OA-4 resolved by the owner |
| A-measure | not started | — | needs decision D4 (pilot app) |
| B | built, unmeasured; awaiting owner | see Checkpoints | prompt, guideline, example and test pins; no engine change; narrow seeded-defect measurement done (see Phase B measurement); full-run acceptance not done (OA-7, OA-8) |
| M | built and tested; complete (OA-10 accepted for this run) | see Checkpoints | engine change: progress digest reads only code reviews and refuses bad evidence; loop needs structured findings; a waiver needs a human actor type |
| T (project design systems) | built and tested; complete | see Checkpoints | added by the owner after the theme experiment; prompt, guideline, docs, example; no engine change |
| C | task 0 done (the reviewer perceives screenshots); not built | — | waiting on the owner |
| D, E | not started | — | each starts only at the owner's request |

## Owner attention

Open rows make a phase `awaiting owner`, never `complete`.

| Id | Source | What is unresolved | Why | Options | Recommendation | Blocks merge? |
|---|---|---|---|---|---|---|
| OA-1 | Codex PR-R1-002 | The isolated experiments do not run the guideline files or the native design phase, so they cannot attribute a rating difference to Phase A as shipped | the experiment applies only appended arguments | (a) a harness that loads each arm's capability files and builds `app-design.md`; (b) narrow the claim and rely on the one full run for the design changes | (a) | no (A-build); yes for any visual claim |
| OA-2 | Codex PR-R1-003, PR-R2-001 | A-measure inputs (model/settings, order, pairing, failure handling, aggregation, clarification policy, run deadline) are undeclared | plan text leaves them open | commit an input manifest before running | declare before the first run | no (A-build) |
| OA-4 | **RESOLVED 10 Oct 2026: owner chose (a)**, accept the zero-finding result with the unreviewed areas listed. Codex run `20261010T142651-stage2-codex-A-impl-r2` | Implementation review round 2 is recorded BLOCKED although both attempts returned zero findings | the runner treats an empty findings list with non-empty `areas_not_reviewed` as incomplete, and the read-only sandbox cannot run the suite or Spec Kit, so that list is never empty | (a) accept the zero-finding substance as the round-2 result, with the unreviewed areas listed; (b) authorize a third run with a prompt that lists those areas as out of scope; (c) authorize another reviewer, labelled "not Codex" | (a): the fix is a three-bullet reorder that both attempts verified | no, if (a) |
| OA-5 | **RESOLVED 11 Oct 2026: owner chose (a), keep Phase A, make no visual claim, proceed to B.** A-measure result | Phase A showed **no rendered-UI gain** against its target (S1 mean diff -0.92 under the manifest failure rule; +0.04 if the one non-rendering enhanced run is excluded; target was +0.5 and 2 of 3 wins) | n=3 per cell, one pilot app, raters not independent (OA-6) | (a) keep A only if Phase B goes ahead, as PLAN §6 row 9 says; (b) revert A; (c) re-measure with human raters and a re-run of the two failed runs | (a), and re-rate with at least one human before any claim either way | no |
| OA-6 | A-measure ratings | Both rating sets were produced by a model (Codex) given the rubric, not by two human blind raters, and they are near-identical (mean packet disagreement 0.01, max 0.25); S3 got the same 3.75 in all six packets | same model and prompt, so not independent; S3 shows no discrimination | add a human rater, or treat the result as one AI judgement | add a human rater | no |
| OA-7 | Phase B protocol | B was built before its phase plan and Codex plan review (PLAN §5.1 order); the plan and the implementation review were merged into one round | built on the owner's "go ahead" without the plan step | accept; or ask for a second, independent plan review of B-PLAN.md | accept: the combined round found five defects, all fixed | no |
| OA-8 | Phase B acceptance | PLAN row 4 partly done: narrow measurement on two screens (below). Not done: an accessibility and an overlap defect class, and the harness inside a full SDLE run through `manifest build` and the gate | the pilot's implementations have no browser checks written; a full run needs the owner at the gates | write checks for the 18 pilot implementations and inject the defects; or accept B as an example plus pins | decide with the owner whether the measurement is worth its cost | no |
| OA-9 | **RESOLVED 11 Oct 2026: owner chose (a)** for this run. Codex run `*-M-plan-r2` | Phase M plan review round 2 is recorded BLOCKED although both attempts returned zero findings | same runner rule as OA-4: an empty findings list with non-empty `areas_not_reviewed` is rejected, and a read-only sandbox can never run the suite | (a) accept the zero-finding result with the unreviewed areas listed, as for OA-4; (b) a third run with those areas declared out of scope; (c) another reviewer, labelled "not Codex" | (a), and a standing rule that a zero-finding, coverage-gap-only result counts as completed with the gaps listed | blocks starting the engine change for Phase M |
| OA-10 | **RESOLVED 12 Oct 2026: owner chose (a)**, accept for this run only (no standing rule). Codex run `*-M-impl-r2` | Phase M implementation review round 2 recorded BLOCKED with zero findings, for the third time (OA-4, OA-9) | the runner rejects an empty findings list with non-empty `areas_not_reviewed`, and a read-only sandbox can never run the suite | (a) accept it for this run; (b) a standing rule: a zero-finding result that fails only that coverage rule counts as completed with its gaps listed; (c) change the runner to treat declared gaps as a pass | (b), recorded in the ledger so each case is still visible | no, if (a) or (b) |
| OA-3 | process | The full suite was run in sharded calls (10-minute foreground cap) and shards 7-17 were deferred to step 4 | cap and a memory reap | none needed once step 4 runs all 18 | — | no |

## Open decisions

| # | Decision | State |
|---|---|---|
| D1 | Screenshot retention | open; blocks Phase D only |
| D4 | Pilot app and stack | open; blocks A-measure only |
| D5 | Windows support claim | open; blocks Phase B's Windows claim only |
| D6 | Mid-run tightening of `ui_paths` | open; blocks Phase D only |

## Checkpoints

| Phase | Implementation SHA (the checkpoint) | Record commit | Status | Pushed |
|---|---|---|---|---|
| A-build | `d915eb6` | the commit that last touched this file | awaiting owner (OA-1, OA-2: A-measure decisions) | yes |

**Test evidence.** Full suite in 18 shards (4215 collected): all passed except one tracked-files-count failure caused by the new file being untracked at the time; `test_units_install_contract.py` then 36 passed. After the last fix: capabilities, lint_skill, shipped_surface, documented_commands, install_contract, dry_run_contracts 1672 passed. `lint-skill` ok. Records in `.sdle/implementation-state/ui-quality/runs/`. Sharded because of the foreground limit; the final whole-suite shard run was before the IR-R1-001 reorder, which touched one prompt file.

**Prerequisites for A-measure.** D4 (pilot app and stack, with the start and test commands, versions and the two raters); the input manifest of OA-2 (including clarification policy and deadline); the choice at OA-1; Spec Kit v1.0.6 via `uv`; Playwright with Chromium.

**Stopping here.** Safe: prompt-only, no runtime dependency, no claim of visual improvement until A-measure.

## A-measure (pilot app: Angular RDMS frontend, scratch copy; data outside this repository)

Status: **generation complete, ratings pending**. No visual claim is made.

| Item | Record |
|---|---|
| Subject | Angular app (Material), baseline commit `8c2947a` of a scratch copy; mock RDMS API (7 Systems, 19 Groups, 86 Services); fake credentials |
| Arms | baseline = SDLE `3cd3b19`; enhanced = SDLE `d915eb6`; each arm's real capability files and Spec Kit v1.0.6; no gates, no reviews (isolated experiment, not a full SDLE run) |
| Screens | S1 overview dashboard (new), S2 register table (new), S3 hierarchy filters (brownfield) |
| Runs | 18 counted (3 per arm per screen), seeded order (seed 20261010), model `claude-sonnet-5-5`. All 18 completed, built and were captured |
| Excluded | 1 harness dry run (`enhanced-S2-0`); 7 runs lost to API/session-limit failures and re-executed under the same ids (kept as `runs-invalid/`), logged in the final manifest |
| Mechanical effect | every enhanced plan has the User Interface section, no baseline plan does |
| Cost / time (supporting, mean per run) | baseline $2.27, 537 s; enhanced $2.89, 764 s: **+27% cost, +42% time**, above the 25% target in PLAN §6 row 9(d); reported, not a rejection. n=9 per arm, large variance |
| Rendered-UI rating | **pending**: two blind raters not yet named. Rating set: 18 packets, 108 screenshots, two random orders, arm map kept apart |
| Order caveat | the seeded shuffle placed the three enhanced S1 runs before the baseline S1 runs |
| Not done | the one full SDLE run of the enhanced arm on S1 through `gate_implement`; intent-completeness scoring (needs a blind rater) |

### A-measure result (ratings received 11 Oct 2026; rater = model, see OA-6)

Rule applied, fixed in the manifest before any run: a run that does not render the declared screen is rated 1 on every criterion and listed. Two of 18 did not: `enhanced-S1-3` (stopped after the analysis step; no `/overview` route) and `baseline-S2-1` (no `/register` route). The raters had scored the redirected Systems page; the rule replaced those two packets.

| Screen | Baseline mean | Enhanced mean | Diff | Enhanced wins (pairs) |
|---|---|---|---|---|
| S1 overview (demanding) | 3.83 | 2.92 | -0.92 | 1 of 3 |
| S2 register | 2.50 | 3.29 | +0.79 | 2 of 3 |
| S3 hierarchy (brownfield) | 3.75 | 3.75 | 0.00 | 0 of 3 |

Sensitivity only (the two non-rendering runs removed, not the pre-registered rule): S1 +0.04, S2 +0.04, S3 0.00. By criterion the only recurring signal is polish, +0.67 on S2 and -0.67 on S1, which are the two screens with a failed run.

Against PLAN §6 Phase A row 9: (a) demanding screen +0.5 and 2 of 3 wins: **not met**; (b) no other screen drops by more than 0.3: met; (c) completeness: not scored; (d) cost and time +27% / +42%: exceeded, reported; (e) full SDLE run: not done.

**Reading.** The guidance reliably changes the artifacts (every enhanced plan has the section) but no rendered-UI improvement is demonstrated, and the enhanced arm had one more non-rendering run. This is one pilot app, n=3 per cell, with ratings from a model: preliminary, and no visual claim is made either way. Many defects the raters named were shared by both arms (generic error toasts, cut-off tablet columns), which neither arm's guidance addresses and which is what Phase B's browser checks would catch.

### A-measure, with the owner's own ratings (11 Oct 2026)

Raters: the owner (human, unblinded afterwards) and the model's second set (`rater2`). The owner scored holistically (the four criteria equal in 13 of 18 packets, decimals used, one polish cell blank on `P15`, taken as the mean of the three given). The owner did not apply the failure rule: the two non-rendering runs were scored as the Systems page they showed.

| Basis | S1 diff (enh - base) | S2 diff | S3 diff |
|---|---|---|---|
| Owner alone, failure rule applied (primary) | -0.12 (2 of 3 wins) | +0.58 | +0.17 |
| Owner alone, as scored | +0.58 | -0.33 | +0.17 |
| Owner + model, failure rule applied | -0.52 | +0.71 | +0.08 |

Agreement between the owner and the model set is nil (mean packet difference 0.53, correlation -0.05). The owner's comments: all three baseline S1 runs used green chart bars that do not match the app's theme; no enhanced S1 run did. The owner rated the two rendered enhanced S1 runs 4.0 against 3.12 for each baseline S1 run (+0.88, 2 of 2). One enhanced S1 run (1 of 3) never built the screen, which the failure rule counts as 1.

Reading: the PLAN row 9 target (S1 +0.5 and 2 of 3 wins) is **not met** under the pre-registered rule; there is a human-observed S1 effect where the screen exists (theme-consistent colour), at a cost of one run that built nothing, n=2. No claim is made beyond that.

### A-measure extension, S1 (11 Oct 2026; exploratory, harness v2, rated by the owner)

Cause of the one non-rendering enhanced run in the first batch (`enhanced-S1-3`): the model ended its turn at the `analyze` block's HALT, which is identical in both arms; not caused by the guidance. Extension: S1 only, 3 runs per arm, ids 4-6, same model, capture and rubric, with the prompt telling the model that HALT is a human wait that does not apply. All six built and rendered the screen; `enhanced-S1-4` ended on the session limit after the screen, build and notes were complete and is counted, flagged.

| | Baseline | Enhanced | Diff | Pairs won |
|---|---|---|---|---|
| Extension S1 (owner) | 3.91 | 4.00 | +0.10 | 1 of 3 |
| First-batch S1 (owner; baseline all 3.12, enhanced 4.0, 4.0 and the non-rendering run) | 3.12 | 3.71 as scored | +0.58 | 2 of 3 |
| Combined 6 v 6, failure rule | 3.52 | 3.50 | -0.01 | |
| Combined, rendered runs only (6 v 5; not the pre-registered rule) | 3.52 | 4.00 | +0.49 | |

Mean cost +10%, time flat (extension). By criterion (extension): hierarchy +0.25, consistency 0.00, usability +0.08, polish +0.05.

The first batch's colour pattern did **not** replicate: the owner flagged green-and-blue mixing on one baseline run (`baseline-S1-6`) and one enhanced run (`enhanced-S1-5`), and baseline scores rose from 3.12 to 3.75-4.06 between sessions, so ratings across the two batches are not on a common anchor.

Conclusion for A-build: **no rendered-UI gain demonstrated** against the PLAN §6 row 9 target in either batch or the combined view; the first-batch +0.88 on rendered S1 runs shrank to +0.10 on re-test (regression toward the mean is the simplest reading). Phase A's mechanical effect (a UI section in every enhanced plan) is real. n is small, one app, one human rater. Recorded under OA-5.

### Phase B checkpoint (11 Oct 2026)

Built on base `863bcfb`: the harness contract in `guidelines/ui-design.md`, one bullet in the `implement` block, `docs/examples/ui-harness/` and pins in `tests/test_units_tree_digest.py`. **No change to `scripts/sdle.py` or `.claude/hooks/`.** Combined plan and implementation review: Codex round 1 on `8e9bf83`, 5 findings, all accepted and fixed (preflight report, pin non-vacuity, unit-plus-browser merge, artifact path, records); round 2 on `f0326a1`, 2 findings in the example harness (report completeness, stale report), both accepted and fixed and verified by executed re-runs; no round 3. Tests: full suite 4218 passed, 3 skipped; 2091 passed after the round 1 fixes. Status: `built, unmeasured`; go/no-go (4 of 5 seeded defect classes, no flaky reruns) **not evaluated**.

### Phase B measurement, narrow version (11 Oct 2026; pilot app, one stack, owner-approved reduction)

Scope: two generated screens from the A-measure runs (S1 `enhanced-S1-6` overview, S2 `enhanced-S2-3` register), requirement-level browser checks written from the requirement documents, the example harness run as the one test command against the app's dev server and the mock API, seven seeded defects injected one at a time into a scratch copy and reverted. Scaffolding is outside this repository (`ui-quality-pilot/support/b-measure`).

| Item | Result |
|---|---|
| Clean reruns | 3 of 3 pass on each screen, with the final checks; suite about 20-30 s |
| Seeded defects, checks **as first written** | 2 of 5 valid mutations detected (2 mutations did not compile and were replaced); the overflow checks and one journey check were blind |
| After repairing the checks (document-level overflow missed an app shell that scrolls its own content area; a loose URL assertion; a loose empty-state pattern) | 7 of 7 detected: overflow 2, error state missing 2, empty state missing 1, broken journey 2 |

**Read this carefully.** The 7 of 7 is **optimistic**: the checks were corrected after seeing which mutations they missed, on the same mutations. The honest figure for checks written from requirements is the first pass, and what it shows is that browser checks catch a defect only if the check measures the right thing: the failures were all in the checks, not in the harness. Not covered: an accessibility defect class, overlap (PLAN named five classes; seven mutations over four), the harness inside a full SDLE run through `manifest build` and the gate. One app, one stack, Windows. The checks were written by me, not by the generator.

PLAN §6 Phase B row 9 target (at least 4 of 5 seeded defect classes detected, no flaky reruns, fits the timeout): numerically met on the repaired checks (4 classes, 0 flaky of 6 clean runs, within the timeout), with the caveat above; **not** a claim that SDLE-generated tests would catch them.

### Phase M checkpoint (11 Oct 2026)

Base `4d7d1ea`. Implementation commits: `b51a6c7` (engine, tests, prompts, docs) and `9c044ec` (review round 1 fix); **`9c044ec` is the checkpoint**. `scripts/sdle.py` changed in three places and nowhere else: `_blocking_finding_fingerprints` (code reviews only; unreadable, inconsistent or malformed evidence is `review_evidence_invalid`, exit 3), `loop step --step review` and `loop record` (`loop_review_unstructured`), `artifact review` (`review_waiver_requires_human`, before anything is written). Hooks unchanged.

Tests: 4236 passed, 3 skipped over the full suite before the round 1 fix; 802 passed, 1 skipped over the affected files after it. Codex: plan review round 1 three findings (all accepted, design amended), plan round 2 BLOCKED zero findings (OA-9); implementation round 1 one finding fixed, round 2 BLOCKED zero findings (OA-10).

Stated limit: the review evidence file is not hash-chained, so an edit that leaves it valid and consistent with the ledger is not detected; the actor type of a waiver is self-declared, so the rule stops silent waivers and does not prove who decided.

**Prerequisite for Phase C:** A, B and M released (this is the third). C also needs its own task-0 experiment (can the read-only reviewer see a PNG) and the owner's decision.

### Phase C task 0: can the read-only reviewer perceive a screenshot? (12 Oct 2026)

Question (PLAN F5 / U1): can `sdle-code-review`, as configured (`Read, Grep, Glob`), perceive pixels through `Read`? Setup: seven PNGs with neutral names, from the pilot screenshots; four with one seeded pixel-only defect each (overlap, clipping, misalignment, low contrast, made by editing the image) and three unmodified; the subagent was told to view each, state what it saw, quote two strings of text, and list defects, and not to assume any exists. One run, one reviewer.

| Result | |
|---|---|
| Perceives images | **yes**, 7 of 7: correct description of every screen and exact quoted text |
| Seeded defects found | **4 of 4** (overlap, clipping, misalignment, low contrast), each with a correct location |
| Extra categories on seeded images | misalignment image also reported as overlap and clipping (the shifted strip does produce those); the low-contrast image also reported text wrapping |
| Unmodified controls | all 3 were given at least one finding (toast stacking over the footer; faint legend sample text; tree cut at the bottom of a full-page capture). These controls are real screenshots with real quirks, not defect-free, so these are not scored as false positives; they do show the reviewer reports minor things on a clean screen |

What this settles: the premise of Phase C holds, and C ships its full variant (screenshots to the reviewer), not the fallback (listed for the human, "visual judgment unverified"). What it does **not** settle: the seeded defects are large and crude, so detection of subtle defects is untested; finding stability across repeated reviews is untested; a false-positive rate needs controls that are actually defect-free; and an AI visual judge was not aligned with the owner's own ratings in A-measure (OA-6), which argues for keeping visual findings advisory unless the owner decides otherwise. U1 is resolved.

### Theme experiment (24-25 Oct 2026; pilot app, S1, design fixed before any run)

**Question.** Does a project design-system document, plus a four-line guideline rule to use it, make the generated screen follow the app's colour roles? The pilot app's token set includes a green `--color-success`; the green chart bars the owner flagged in A-measure were that **status** colour used for **data**. The design-system document (written from the app's own `_theme.scss`) states that status colours are never data-series colours and that charts use the primary indigo family. This is a test of whether the generator **follows a stated theme**, not proof that themes make UI better in general.

Arms: control = enhanced SDLE (`d915eb6`); themed = the same plus `design-system.md` at the project root and the rule appended to `guidelines/ui-design.md`. Three runs each, harness v2, seeded order. Metrics computed by script.

| Run | Green share of saturated content pixels | Indigo/blue share | Status colour in chart styles | `Theme:` line in plan |
|---|---|---|---|---|
| control 7 | 0.744 | 0.131 | 2 | no |
| control 8 (flagged: session limit after the screen was built) | 0.002 | 0.911 | 0 | no |
| control 9 | 0.767 | 0.146 | 2 | no |
| themed 7 | 0.000 | 0.920 | 0 | yes |
| themed 8 (re-run; re-captured after the mock API stopped) | 0.000 | 0.861 | 0 | yes |
| themed 9 | 0.000 | 0.933 | 0 | yes |

**Result.** With the theme, 3 of 3 runs kept data in the indigo family and named the theme in the plan; without it, 2 of 3 drew data in status green. Literal colour values: one per run in both arms (no difference). Mean cost: control $1.93 (one run cut short), themed $2.47. Checked by eye on two screenshots: the metric measures the chart colours it claims to.

**Not measured, seen in passing.** `themed-S1-8` shows every record as active (inactive 0), i.e. it did not fetch inactive records, which the requirement asks for; control runs did. One run; a correctness defect unrelated to the theme, and exactly what Phase B's browser checks would catch.

**Limits.** n = 3 per arm, one screen, one app, one colour rule. Two runs hit the session limit (one re-run, one counted and flagged) and one capture was repeated after the mock API stopped; all are in `experiment/THEME-EXPERIMENT.md`.

### Phase T checkpoint (25 Oct 2026)

Added by the owner after the theme experiment. A project may keep its design system in `design-system.md` (or a path the plan names on a `Theme:` line). SDLE reads it as data (scanned before use), ranks it below the approved requirements, the constitution and the architecture decisions, re-checks its git blob hash before design, implementation and remediation and asks the user if it changed, never copies its values, and ships no theme of its own; an example structure is in `docs/examples/themes/`. Where the plan gate does not run, the theme line is shown at the implementation gate. **No engine or hook change.**

Implementation commit `deef906` is the checkpoint (later commits are records). Tests: 18-shard full suite **4242 passed, 3 skipped**. Codex: plan round 1 four findings and round 2 one, all accepted and designed in; implementation round 1 and round 2 one each, both documentation corrections, accepted. Stated limits: the theme's content is not protected by drift detection after the plan gate (prompt-level re-check only); the rule that an existing app's theme is not changed as a side effect is advisory; the precedence exception (a higher source wins over the theme) was not tested by the pilot.
