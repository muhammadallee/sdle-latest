# Stage 2, Level 1 — independent adversarial review of the requirements-refinement implementation PLAN

You are an independent, adversarial reviewer. You have not seen the conversation that produced this plan and
you must not assume any decision in it is correct. You are in a **read-only sandbox**: do not edit, create or
delete files, and do not run anything that writes. Reading files and running read-only commands is fine.

The repository checked out here is SDLE (Spec Driven Lifecycle Engine): a deterministic, gated SDLC
orchestrator for Claude Code. `scripts/sdle.py` is the single-file, standard-library-only engine; it refuses
rather than warns. `CLAUDE.md` at the repository root states the invariants any change must preserve; read it
first. The commit you are reviewing is the one checked out (`git rev-parse HEAD`); report it as
`reviewed_commit`.

## What you are reviewing

A **plan**, not code. No production code for this feature exists yet. The plan describes a
"requirements refinement loop": before a WorkItem is initialised, when the governance quality check of the
bound requirement documents fails, a bounded loop proposes questions and edits to those documents, applies
them under controlled rules, and re-assesses, instead of the human editing the documents by hand and
re-running assessment.

Everything is under `.sdle/implementation-state/requirements-refinement/`:

| File | What it is |
|---|---|
| `BRIEF.md` | The owner's execution brief: the mission, the verified grounding facts F1–F14, the **decided constraints C1–C9**, the target design, the review protocol, and the acceptance scenarios. |
| `PLAN.md` | **The artifact under review.** §0 is a re-baseline written at this commit; §§1–8 are the plan: impact surface, blast-radius measurements, design decisions D1–D11, JSON contracts, the state-transition table, file-level estimates, and a 30-scenario traceability table. |
| `LEDGER.md` | The execution record, including the corpus measurement and its three correction passes. |
| `labels.json`, `runs/`, `runs/recompute_metrics.py` | The evaluation corpus's labels, the recorded assessor runs, and the script that recomputes precision/recall from them. Reproduce with `python .sdle/implementation-state/requirements-refinement/runs/recompute_metrics.py` (it is read-only). |
| `lint-prototype.py`, `assessor-prompt-draft.md` | The prototype of the deterministic requirements lint and the draft assessor prompt. |
| `tests/fixtures/requirements-quality/` | The 14-document evaluation corpus. |

Read the **current source** the plan refers to; do not trust the plan's description of it. The plan cites
engine symbols by name (`cmd_governance_assess`, `evaluate_quality`, `governance_precondition`,
`unacknowledged_flagged_sources`, `read_scan_acknowledgements`, `write_content_acknowledgement`,
`record_scan_acknowledgement_audit`, `safe_repo_path`, `_lexically_safe_path`, `reserve_evidence`,
`requirements_sources`, `architecture_catalog_lock`, `workitem_runtime_member_names`, and others). Line
numbers in §§1–2 are stale by design; §0.3 gives current ones.

## Constraints you may challenge but must justify

`BRIEF.md` §2 lists constraints **C1–C9** that the owner decided. You may challenge any of them. A challenge
you cannot support with evidence from the code, the tests or the plan itself is not a finding. Do not argue
with a constraint merely because you would have chosen differently.

`PLAN.md` §3.b records an **owner-authorised deviation** from C6: the deterministic lint ships advisory-only
and never refuses an assessment. Review whether the plan carries that deviation through consistently; do not
re-litigate the decision.

## Attack list — the brief requires you to attack each of these

1. Can the loop still converge by **verdict drift** — an assessor flipping a FAIL to PASS on unchanged
   document bytes, or the reverse? Review §3.2/D11 and `quality_verdict_flip`.
2. Does **any change weaken an existing refusal**? Enumerate the refusals in `sdle.py` the plan touches and
   check each.
3. Is the new `refinement` **command group needed**, or can the existing commands carry it? (D5)
4. **Pre-`init` placement** (C4): a loop that runs before `state.json` exists. What survives a crash, and
   where does its state live? (D1, F5, F15)
5. **Crash points** between applying an edit and re-assessing, and inside the shared-document transaction
   (C1, D1, D2): enumerate each write point and say what a resume sees.
6. Can the **dispute path launder a verdict flip**? (D9, scenario 26.) Note the plan itself flags a naming
   mismatch between D9's prose (`disputeOutcome`) and §5.a / row 26 (`disputeOutcomes[]`).
7. Does the **presentation-neutral normal form** (§3.5) hide meaningful edits? Try to find a Markdown edit
   that changes meaning but normalises to the same digest.
8. **Lint false positives by requirement kind** (C6, §3.3, `lint-prototype.py`), and **corpus adequacy**
   (§3.c, `labels.json`, `recompute_metrics.py`): is 14 documents × 3 runs enough to support the claims made
   from it? Check the arithmetic yourself.
9. **Conflicts with C1–C9.**

## Named items you must not skip

- **D1** (pre-init audit for the shared-document transaction), **D2** (the refusing lock), **D8** (brownfield
  baseline citation), **D9** (dispute outcome vocabulary), **D10** (the review agent must not restate the
  check-id vocabulary), **D11** (where `quality_verdict_flip` reads the prior verdict and content digest).
- The `todo-api.md` **dependencies finding** in §3.c.
- The **disposition table in PLAN.md §0.5** of six inherited defects (RR-002, RR-003, RR-004, RR-006, RR-007,
  RR-008): are the four marked in-scope really inside this plan's impact surface, and are the two sent to the
  owner really outside it? Verify each against `scripts/sdle.py` and `claude-review-rejections.md` at the
  repository root.

## New since the plan was first written — review these hardest

The architecture-memory enhancement landed on this branch after §§1–8 were written. PLAN.md §0.4 lists what
it changes. Specifically examine:

- **§0.4(3):** D2's lock against `architecture_catalog_lock`. Is the plan's lock a second invention of the
  same mechanism? Would it hit the same failure modes (stale lock, timeout, a reader that waits)?
- **§0.4(4):** the closed-set test `test_the_repository_configuration_members_have_a_closed_reference_set` in
  `tests/test_units_repo_config.py`. Which planned functions would trip it?
- **§0.4(5):** `workitem_runtime_member_names` and the new `refinement.json`.
- **§0.4(6):** every pin the plan says it will move (`WRITE_PRIMITIVE_COUNTS`, `COMMANDS`, `PRODUCT_AGENTS`).
  Are the starting values in §0.1 correct? Recount them from `tests/test_units_invariants.py` and the engine.
- **§0.4(7):** the interaction between a refinement edit and `architecture_placement`, which reads the bound
  requirements later through the requirements binding (ADR-012). Is the claim that an edit cannot stale a
  placement actually true? Read `architecture_placement`'s inputs and `requirements_sources`.
- **§0.4(2):** ADR number — confirm `docs/architecture/` really has no ADR-015.
- Anything in §§1–8 that the §0 delta makes **false** but §0 does not mention. Check every ordinal, count,
  phase name and gate number the plan states against `python scripts/sdle.py constants`.

## Output

Return **only** a JSON object matching the supplied output schema.

- `reviewed_commit`: the checked-out commit.
- `coverage.areas_reviewed` / `coverage.areas_not_reviewed`: be specific. Naming what you did **not** reach
  is as important as the findings. An empty `findings` array with non-empty `areas_not_reviewed` is rejected
  as an incomplete review.
- Each finding: a unique `id` of the form `S2-L1-001`, a `severity` (`critical|high|medium|low`), a
  `category` that is **`defect/<area>` for something wrong that must be corrected**, or
  **`improvement/<area>` for something that would be better but is not wrong** — never mix them —, the `path`
  and `line` it concerns (`0` if none), a `claim`, the `evidence` (quote the file and line you relied on), an
  `evidence_type` of `executed` (you ran a read-only command and observed the result) or `static` (you read
  it), a concrete `suggested_fix`, `ac_ids` listing the plan items it touches (e.g. `["D2", "C1", "§0.4(3)",
  "scenario 18"]`), and your `confidence`.
- Do not pad. A finding without evidence from the repository is not a finding. Do not report style or
  wording unless it hides a defect. Do not rewrite the plan.
