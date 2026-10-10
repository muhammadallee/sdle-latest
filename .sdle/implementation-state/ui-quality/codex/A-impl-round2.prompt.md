# Implementation review, round 2 — SDLE UI-quality enhancement, Phase A

You are an independent, adversarial reviewer in a **read-only sandbox**: do not edit, create or delete files. Read `CLAUDE.md` first. Report the checked-out commit as `reviewed_commit`.

Round 1 reviewed commit `540f175` (diff `a1feffa..540f175`) and returned one finding, IR-R1-001: the UI-append instructions for `spec_draft`, `plan_draft` and `tasks_draft` sat **after** the Spec Kit invocation bullet. It was accepted and fixed in the commit now checked out: the three bullets were moved ahead of the invocation and reworded. Nothing was rejected. Evidence for the fix: `lint-skill` ok; capabilities, lint_skill, shipped_surface, documented_commands, install_contract and dry_run_contracts tests: 1672 passed (`.sdle/implementation-state/ui-quality/runs/a-s5-fix1.json`).

## Do
1. Verify the fix in `.claude/skills/sdle/modules/phase-execution.md`: for each of the three blocks, read the bullets **in order, as an orchestrator would** and say whether the UI argument text is applied to the invocation, and whether the bullet's condition can be evaluated at that point (for example, does `plan_draft` have an approved spec to read; does `tasks_draft` have a plan with the section).
2. **Do not re-report fixed items.** Review the whole phase diff `git diff a1feffa..HEAD` again for what round 1 did not reach, in particular the `design_generation` and `implement` blocks, the `discovery`/`impact_analysis` additions, `guidelines/ui-design.md` content, and the A-PLAN/LEDGER/PROGRESS documents.
3. State what you did not reach.

## Output
Return **only** a JSON object matching the supplied schema. Ids `IR-R2-001`... `defect/<area>` or `improvement/<area>`, repository evidence quoted, no padding, no wording nits.
