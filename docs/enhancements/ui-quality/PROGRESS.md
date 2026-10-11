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
| B, M, C, D, E | not started | — | each starts only at the owner's request |

## Owner attention

Open rows make a phase `awaiting owner`, never `complete`.

| Id | Source | What is unresolved | Why | Options | Recommendation | Blocks merge? |
|---|---|---|---|---|---|---|
| OA-1 | Codex PR-R1-002 | The isolated experiments do not run the guideline files or the native design phase, so they cannot attribute a rating difference to Phase A as shipped | the experiment applies only appended arguments | (a) a harness that loads each arm's capability files and builds `app-design.md`; (b) narrow the claim and rely on the one full run for the design changes | (a) | no (A-build); yes for any visual claim |
| OA-2 | Codex PR-R1-003, PR-R2-001 | A-measure inputs (model/settings, order, pairing, failure handling, aggregation, clarification policy, run deadline) are undeclared | plan text leaves them open | commit an input manifest before running | declare before the first run | no (A-build) |
| OA-4 | **RESOLVED 10 Oct 2026: owner chose (a)**, accept the zero-finding result with the unreviewed areas listed. Codex run `20261010T142651-stage2-codex-A-impl-r2` | Implementation review round 2 is recorded BLOCKED although both attempts returned zero findings | the runner treats an empty findings list with non-empty `areas_not_reviewed` as incomplete, and the read-only sandbox cannot run the suite or Spec Kit, so that list is never empty | (a) accept the zero-finding substance as the round-2 result, with the unreviewed areas listed; (b) authorize a third run with a prompt that lists those areas as out of scope; (c) authorize another reviewer, labelled "not Codex" | (a): the fix is a three-bullet reorder that both attempts verified | no, if (a) |
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
