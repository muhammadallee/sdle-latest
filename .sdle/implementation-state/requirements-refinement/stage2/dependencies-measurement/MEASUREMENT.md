# `dependencies` check — definition measurement (2026-10-02)

Run for PLAN.md §0.6 A11 (S2-L1-011): `todo-api.md` was blocked on `dependencies` 3 of 3 times under the Stage 1
draft definition, while acceptance scenario 1 requires it to pass unchanged. The owner chose "refine the
definition, plus an explicit dependencies statement in the sample (no brand)". This is the measurement that
choice was made conditional on.

**Exploratory, not confirmatory.** 3 runs per cell, one assessor model, no independent labelling, and two of the
five documents are controls the implementing agent wrote itself. Every number below is a reason to look, not a
proof.

## Method

- The Stage 1 draft assessor prompt (`../../assessor-prompt-draft.md`), unchanged except for check 11,
  `dependencies`. `definition_v2.txt` is the replacement; the original is the draft's own text.
- Fresh general-purpose agent per run, given a prompt file with a neutral name and the document text only (no
  filename, no label, no prior verdict). **One deviation from Stage 1:** Stage 1 put the document inline in the
  dispatch; here each agent opened an isolated file with a single Read, and wrote its JSON with a single Write
  (`tool_uses` = 2). Reading adds line numbers, which may help cross-referencing, so the original-definition runs
  were repeated by this same method rather than compared with the inline ones.
- Raw outputs are in `out/`; `manifest.json` maps each output to its document, definition and run. The builders in
  `builders/` generate the prompt files; their scratch paths are hard-coded to the session that produced them.

## Results — the `dependencies` check

| Document | Definition | `dependencies` FAIL |
|---|---|---|
| `todo-api.md`, original bytes | original (Stage 1 inline runs) | 3 of 3 |
| `todo-api.md`, original bytes | original (this method) | 2 of 3 |
| `todo-api.md`, original bytes | new | **0 of 3** |
| ordinary-clean control (says "a relational store" and "an object store", names its real external systems) | original | 0 of 3 |
| ordinary-clean control | new | 0 of 3 |
| vague-external control (payment provider, tax service, identity system, all unnamed) | original | 2 of 3 |
| vague-external control | new | **3 of 3** |
| `defect-dependencies.md` (Dependencies section removed; "some shared infrastructure") | original (Stage 1) | 0 of 3 |
| `defect-dependencies.md` | new | 1 of 3 |
| `clean-baseline.md` | new | 0 of 3 |

## Results — the amended sample (all twelve checks)

| Version of `todo-api.md` | Definition | Passes all 12 | What failed |
|---|---|---|---|
| original | original | 1 of 3 | `dependencies` ×2 |
| original | new | 0 of 3 | `contradictions` ×3 |
| + explicit dependencies statement | original | 1 of 3 | `contradictions` ×1, `ambiguity` ×1 |
| + explicit dependencies statement | new | 1 of 3 | `contradictions` ×2 |
| + statement **and** `updated_at` fix | new | **3 of 3** | nothing |

## What the data says

1. **The sample contains a real contradiction, independent of this work.** The Data Model says `updated_at` is
   "updated on every write" (line 42); requirement 5 says it "changes only when a write actually modifies a
   field" (line 63). They disagree for a write that changes nothing. The assessor reports exactly this in every
   `contradictions` failure. It was missed in all 6 original-definition runs and found in 5 of 6 runs that
   included the new definition on the unamended or statement-only sample, so detection is unstable; the sample
   was labelled clean in Stage 1, and that label was wrong.
2. **The explicit dependencies statement alone removes the `dependencies` failure** — 0 of 6 failures across
   both definitions once it is present. The definition change is not needed to make the sample pass on that check.
3. **The new definition did not hurt and may help.** No ordinary or clean document failed `dependencies` under it;
   the vague control moved from 2 of 3 to 3 of 3 caught, and the seeded document from 0 of 3 to 1 of 3. These are
   differences of one or two runs; they do not establish an improvement.
4. **Scenario 1 passes only with both document corrections.** The sample passed all twelve checks 3 of 3 only
   with the dependencies statement *and* the `updated_at` contradiction resolved (measured under the new
   definition; that combination was not run under the original one).

## Limits

- n = 3 per cell; detection of the `updated_at` contradiction moved between 0 of 6 and 5 of 6 on cells that
  differ only in a sentence about a different check, which says as much about the assessor's variance as about
  the definition.
- The ordinary-clean control failed `ambiguity` in all six runs and `nfrs` in two: it is not clean on every check,
  only on `dependencies`, which is the one it was written to test.
- A mistake in an earlier explanation is corrected here: the seeded `defect-dependencies.md` defect is a missing
  Dependencies *section* (with vague constraint wording), not only vague wording. Recall on that document stays
  undetermined, as the Stage 1 ledger already concluded.
