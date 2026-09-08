# T04 checkpoint a01-05 — M5 (contract §10's tests, and the prompt they pin)

**Phase:** T04 · **Attempt:** 1 · **Milestone:** M5 of 7 · **Status:** CLOSED GREEN (full-suite figure below).

Predecessors: checkpoints 01–04. Rollback point is still `beb28f2`; nothing committed yet.

## What M5 landed

### `tests/test_units_speckit_binding.py` — new, 53 tests, N1–N13

| N | Covered by |
|---|---|
| N1 | `test_n1_each_workitem_records_its_own_feature_directory` (A's `state.json`, `audit.md` and `specs/` SHA map byte-unchanged while B runs), `test_n1_another_workitems_newer_directory_is_never_a_candidate` |
| N2 | (a) `test_n2a_feature_is_not_a_runtime_free_command` — asserted against the frozenset, not by re-listing it; (b) `test_n2b_...` ×3 subcommands → `workitem_ambiguous`, no `env`, no `capabilities`; (c) `test_n2c_...` ×3 → `workitem_required`; (d) `test_n2d_every_speckit_invocation_is_preceded_by_a_feature_bind` — structural scan of `phase-execution.md`, 8 invocation blocks checked |
| N3 | branch-names-A / bound-is-B; stale repository-global `.specify/feature.json` changes nothing and `.specify/` is byte-identical across a full bind+resolve cycle; a gate refuses `feature_outside_workitem` |
| N4 | parametrised over each missing capability plus "no `.specify/scripts/` at all"; `speckit_missing` when `.specify/` is absent; positive control naming its evidence path; `feature capabilities` never refuses; `--require-feature`; preflight's additive keys |
| N5 | move-not-copy with an unchanged SHA and exactly one `spec.md` under the root; a structural AST proof that no string constant in the engine ends with `spec.md`, `plan.md`, `tasks.md` or `feature.json` |
| N6 | `feature_target_exists`, injected `OSError` → `feature_adopt_failed`, the `speckit_feature_adopted` audit entry with a still-verifying chain, and no move/no audit when already contained |
| N7 | tier 1 beats a far-newer tier 2; tier 2 beats tier 3 and is adopted; all tiers empty → `feature_unresolved` listing `searched`; ambiguity inside the chosen tier still refuses and lists; **the legacy binding keeps its baseline behaviour** |
| N8 | `featureDirectory` derivation parametrised over workitem / legacy / both / neither; a null feature id migrating to an all-null object; a state with **no** `specKit` key readable by `state dump`, `header`, `gate show` and `artifact path` |
| N9 | `{workitem_runtime}` under a WorkItem and under the legacy binding; the documented skip reason; `legacy_prefix` absent from `scripts/sdle.py` |
| N10 | in `tests/test_hooks.py` (M4); a comment block in the new file points there |
| N11 | recursive SHA map of the whole project root identical across success and all three refusal paths |
| N12 | two WorkItems driven through all 18 phases with `feature bind` at every generation phase; A byte-unchanged after B's run; **A20** asserted here (`workflowId`/`runId` null) |
| N13 | fires with severity `error` / exit 3; does **not** fire when null or when contained |

Suite rules honoured: no SpecKit invocation anywhere — capability detection is exercised against fabricated `.specify/scripts/` stub text files, and every generation step writes an artifact over the size floor.

### `phase-execution.md` — the D12 half that N2(d) pins

Declared in checkpoint 03 and repeated here: this file moved from M6 into M5 because N2(d) is its test, and the plan's own rule is that a subject and its test land in the same milestone (F9).

- A `sdle.sh feature bind` line inserted between `checkpoint set` and the invocation in Phases **2, 4, 6, 8, 9, 11, 15**, with `--require-feature` on every one after Phase 4; and a bind sentence added ahead of the Post-Generation Clarify block's numbered list. 8 blocks, 8 binds, each strictly before its invocation.
- The Phase 4 paragraph rewritten from "Feature-ID Resolution" to "Feature-Directory Resolution", describing the fixed tier precedence, WorkItem containment, the audited move, and all four refusals.
- Path substitutions re-derived by exact string count, not by grep line count: `.specify/specs/{state.current_feature_id}` ×**8**, `.specify/specs/{current_feature_id}` ×**3**, `.specify/specs/<current_feature_id>` ×**1** → `{state.specKit.featureDirectory}` (12 in total, covering Phases 4, 5, 6, 7, 8, 9, 11, 13 and the Clarify block).
- No inserted line names a `speckit-*` skill or a `/speckit.*` command, so invariant 3 is untouched.

## Verification at M5

- `python scripts/sdle.py lint-skill` re-run immediately after the `phase-execution.md` edit → **22 PASS / 0 FAIL** (`grep -c FAIL` = 0).
- Targeted `tests/test_units_speckit_binding.py` → **53 passed, RAW_EXIT=0** on the first run.
- Full suite after M5 → recorded in the handoff and in checkpoint 06.

## Residual found while editing `phase-execution.md` (NOT fixed — declared)

The file still names `.workflow/audit.md`, `.workflow/implementation-manifest.md` and `.workflow/completion-summary.json` in Phases 15, 16, 18 and the generic "BEFORE executing any phase" block, even though T02 moved the runtime to `workitems/<id>/.sdle/` and T04's `ARTIFACT_OWNERSHIP` now says `{workitem_runtime}/implementation-manifest.md`. This is a **T02 residual**, not a T04 regression, and the T04 plan's D12 does not list those lines. Left untouched to avoid widening scope; recorded as a finding for the orchestrator to assign.

## How to resume from here

**M6** — the rest of D12: `SKILL.md` prose, `modules/security-review.md`'s three artifact lines, `README.md`'s state-field row, `docs/SDLE-Reference-Guide.md` (artifact table, two prose mentions, state-field row, example path, revision row), `.claude/commands/sdle-reset.md`, `CLAUDE.md`. Re-run `lint-skill` after **each** document edit. Then **M7**: full sweep, acceptance matrix, handoff.
