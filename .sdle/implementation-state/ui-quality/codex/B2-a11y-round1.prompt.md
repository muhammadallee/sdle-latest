# Combined review, round 1 — SDLE UI-quality enhancement, Phase B follow-up: an automated accessibility scan

You are an independent, adversarial reviewer in a **read-only sandbox**: do not edit, create or delete files. Read `CLAUDE.md` first. Report the checked-out commit as `reviewed_commit`.

**What and why.** The owner chose a small follow-up to Phase B after the "option C" measurement in `docs/enhancements/ui-quality/PROGRESS.md`: SDLE-generated browser checks caught 0 of 4 seeded contrast defects. Probe (outside this repository): an axe scan scoped to the screen caught the seeded defect on 4 of 4 generated screens, and failed on 3 of 4 clean ones with real contrast violations. The follow-up adds one advisory row to the harness contract in `.claude/skills/sdle/guidelines/ui-design.md`, one sentence to `guidelines/task-generation.md`, a sample `docs/examples/ui-harness/accessibility.spec.ts` with a README section, and a contrast rule in `docs/examples/themes/design-system.example.md`. No engine or hook change; any is a defect. This review covers plan and implementation together (no separate plan review for a change this size; recorded as a deviation).

Review `git diff 1042949..HEAD`.

## Test evidence (author-run)
`lint-skill` ok; doc links, documented commands, install contract, capabilities and lint tests: 1402 passed.

## Attack list
1. **Claims.** Do the README and guideline say only what the probe showed, with its limits (one app, four screens, a stylesheet-level defect; axe does not establish keyboard or screen-reader behaviour)?
2. **The sample.** Does `accessibility.spec.ts` do what its comments say (scope to an element, both viewports, WCAG 2 A/AA tags, fail on any violation with a readable message)? Anything that would pass vacuously (for example a scope selector that matches nothing)?
3. **Consistency.** With the rest of the harness contract (one command, one merged report, case names citing a screen id), the "What this guideline does not claim" section, and the task-generation rule.
4. **Invariant 7.** Any restated value: the contrast ratios in the theme example are WCAG facts in an example file; anything restated in the guideline?
5. **Mechanical fit.** Docs reachability, install contract, restatement search.

## Output
Return **only** a JSON object matching the supplied schema. Ids `AX-R1-001`... `defect/<area>` or `improvement/<area>`, repository evidence quoted, `areas_not_reviewed` specific, no padding, no wording nits.
