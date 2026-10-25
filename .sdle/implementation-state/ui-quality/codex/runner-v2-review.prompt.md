# Review — the Codex review runner v2 (review tooling, not product)

You are an independent, adversarial reviewer in a **read-only sandbox**: do not edit, create or delete files. Report the checked-out commit as `reviewed_commit`.

**Context.** The UI-quality enhancement reviews every phase with Codex through a runner script. The v1 runner (`.sdle/implementation-state/requirements-package-loop/codex/codexrun_stage2.py`, unchanged) refused any review with zero findings that listed anything as not reviewed, so in a read-only sandbox a clean review could never pass (four occurrences). v2 (`.sdle/implementation-state/ui-quality/codex/codexrun_v2.py` with `review.v2.schema.json`) computes the files in scope from the diff, requires the review to list them as read, and splits gaps into `not_reviewed` (blocks) and `out_of_scope` (recorded, never blocks). The owner's decision and the reason are in `docs/enhancements/ui-quality/PROGRESS.md` ("Review process change") and the PLAN.md process amendment.

## Attack list
1. **Can it be gamed?** Can a reviewer pass without reading the scope (for example by listing every file in `files_reviewed`, or by moving real gaps into `out_of_scope`)? Say what the runner can and cannot detect, and whether the records make it visible to the owner.
2. **Correctness.** `validate()` and `_norm()`: path normalisation (Windows separators, a leading `./`, dot-directories such as `.sdle/` and `.claude/`), an empty scope, a renamed or deleted file in the diff, the commit check. Does `--self-test` cover the cases it claims?
3. **Parity with v1.** Is anything v1 did (read-only sandbox, ephemeral, one retry, run record fields, schema validation by Codex) lost or weakened?
4. **The prompt suffix** the runner appends: clear and consistent with the schema?

## Output
Return **only** a JSON object matching the supplied schema. Ids `RV-001`... `defect/<area>` or `improvement/<area>`, repository evidence quoted, no padding, no wording nits.
