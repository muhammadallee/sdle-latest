# Combined plan and implementation review, round 1 — SDLE UI-quality enhancement, Phase B

You are an independent, adversarial reviewer in a **read-only sandbox**: do not edit, create or delete files. Read `CLAUDE.md` first (eight invariants). Report the checked-out commit as `reviewed_commit`.

Review `git diff 863bcfb..HEAD` against `.sdle/implementation-state/ui-quality/PLAN.md` §6 Phase B (and its Amendments sections) and `phases/B-PLAN.md`. Phase B is prompt, guideline, documentation, an example and test pins: any change to `scripts/sdle.py` or `.claude/hooks/` is a defect. The phase was built **before** its plan review; B-PLAN.md was written afterwards and records that.

## Test evidence (author-run)
`lint-skill` ok; full suite in 18 shards, 4218 passed, 3 skipped, 0 failed (`.sdle/implementation-state/ui-quality/runs/b-full-*.json`); `tests/test_units_tree_digest.py -k test_b` 3 passed. The example harness was run once on a separate pilot app (exit 78 with the app down, 0 on pass, 1 on a failing check); that is not reproducible from this checkout.

## Attack list
1. **Invariant 7.** Does the guideline, the implement bullet or the example restate an engine fact (a limit, a status vocabulary beyond what the engine reports, a refusal code)? Are the exit-78 convention and its caveats stated as the orchestrator's, not the engine's?
2. **Accuracy of the contract against the engine.** For each of the rules in `guidelines/ui-design.md` "Running the interface": is it true of `run_tests`, `cmd_manifest_build`, `tree_digest`, `implementation_exclusions` and the gate precondition? Especially: a report "written to the WorkItem's evidence directory"; "without a shell"; "same full command in every iteration"; the Windows rule; unignored output.
3. **Pins.** Do `test_b1`, `test_b2`, `test_b3` actually fail if the property they pin is lost (non-vacuity)? Is anything in them platform-fragile (quoting, paths, the stand-in script)?
4. **The example.** Does `run-ui-checks.mjs` behave as its README says (preflight, exit codes, report path, artifacts)? Anything that would silently pass when the environment is not ready? Is the "verified once ... not exercised by CI" label accurate and honest?
5. **Prompt behaviour.** The new `implement` bullet: unambiguous conditional; consistent with the neighbouring manifest paragraph and the loop paragraph; does it risk telling the orchestrator to claim more than the evidence shows?
6. **Mechanical fit.** Links, doc-set rules, install-contract counts, anything the new `docs/examples/` folder should be pinned by or excluded from.
7. **The plan.** B-PLAN.md claims and the deviation; PROGRESS.md and PLAN.md as they bear on Phase B.

## Output
Return **only** a JSON object matching the supplied schema. Ids `BR-R1-001`... `defect/<area>` or `improvement/<area>`, repository evidence quoted, `areas_not_reviewed` specific, no padding, no wording nits.
