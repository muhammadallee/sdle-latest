# UI quality enhancement — progress

Resumability log for the UI-quality enhancement. The plan is
`.sdle/implementation-state/ui-quality/PLAN.md`; dispositions and test runs are in
`.sdle/implementation-state/ui-quality/LEDGER.md`. **The commit SHA recorded here is the
authority for a checkpoint**, never a tag.

## Status

| Phase | Status | Checkpoint SHA | Notes |
|---|---|---|---|
| A-build | in progress | — | prompt, guideline, documentation and pin changes only; no engine change |
| A-measure | not started | — | needs decision D4 (pilot app) |
| B, M, C, D, E | not started | — | each starts only at the owner's request |

## Owner attention

Open rows make a phase `awaiting owner`, never `complete`.

| Id | Source | What is unresolved | Why | Options | Recommendation | Blocks merge? |
|---|---|---|---|---|---|---|
| OA-1 | Codex PR-R1-002 | The isolated experiments do not run the guideline files or the native design phase, so they cannot attribute a rating difference to Phase A as shipped | the experiment applies only appended arguments | (a) a harness that loads each arm's capability files and builds `app-design.md`; (b) narrow the claim and rely on the one full run for the design changes | (a) | no (A-build); yes for any visual claim |
| OA-2 | Codex PR-R1-003, PR-R2-001 | A-measure inputs (model/settings, order, pairing, failure handling, aggregation, clarification policy, run deadline) are undeclared | plan text leaves them open | commit an input manifest before running | declare before the first run | no (A-build) |
| OA-3 | process | The full suite was run in sharded calls (10-minute foreground cap) and shards 7-17 were deferred to step 4 | cap and a memory reap | none needed once step 4 runs all 18 | — | no |

## Open decisions

| # | Decision | State |
|---|---|---|
| D1 | Screenshot retention | open; blocks Phase D only |
| D4 | Pilot app and stack | open; blocks A-measure only |
| D5 | Windows support claim | open; blocks Phase B's Windows claim only |
| D6 | Mid-run tightening of `ui_paths` | open; blocks Phase D only |

## Checkpoints

None yet.
