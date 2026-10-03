# Stage 2 — targeted verification of the reconciliation

You are the same independent, adversarial reviewer as at Levels 1 and 2 of the Stage 2 review of the
requirements-refinement implementation PLAN. You are in a **read-only sandbox**: do not edit, create or delete
files, and do not run anything that writes. Reading and read-only commands (including `python` scripts that only
read) are fine. `CLAUDE.md` at the repository root states the invariants; the engine is `scripts/sdle.py`.

## What happened since Level 2

At Level 2 you judged the plan **not ready to freeze** and named 11 blocking ids. The implementing agent
reconciled them. This is the brief's "targeted verification of the changed material only" (brief §5): it is **not**
a fresh review of the whole plan, so do not re-review `BRIEF.md` or the unchanged parts of `PLAN.md`.

The changed material, all in this checkout:

| What | Where |
|---|---|
| The reconciliation: amendments A1–A19, the two self-corrections (§0.6.1) and the closed items (§0.6.3) | `.sdle/implementation-state/requirements-refinement/PLAN.md`, §0.6 (plus the "Superseded in part" markers on D1, D2, D5, D8, D9, D10, D11, §5.a, §5.b, §6, and traceability rows 1, 11, 12) |
| Your Level 1 findings and Level 2 dispositions | `runs/20261001T162206-stage2-codex-plan-level1-attempt2.a1.review.json`, `runs/20261001T163832-stage2-level2-codex-plan-level2.a1.review.json` |
| The responses you reviewed at Level 2 | `stage2/level1-responses.md` |
| **A code change** that closes S2-L1-008 (the owner chose option A): `architecture_requirements_precondition`, the `requirementsDigest` / `requirementsSources` fields recorded by `architecture assess`, and the three places that call the precondition | `scripts/sdle.py`; tests in `tests/test_units_architecture.py` (search "requirements basis" / `architecture_requirements_stale`); docs in `docs/architecture/architecture-memory-contracts.md` §10 and `ADR-013` ("Amendment") |
| A measurement and an edit to the project's sample requirements document | `stage2/dependencies-measurement/` (`MEASUREMENT.md`, `manifest.json`, `out/*.json`, `builders/`); the sample is `requirements/todo-api.md`, identical to `tests/fixtures/requirements-quality/todo-api.md` |

## Your task — one disposition per blocking id

For each of these 11 ids, state whether the reconciliation, **as it is now written in the checkout**, closes the
finding. The amendment that claims to close it is named. Judge the text and the code, not the intent.

| Id | Closed by | What to check |
|---|---|---|
| S2-L1-002 | A2 | The history contract: source, inclusion by `kind`, fail-closed corruption, the legacy-current-record rule, cost. Verify against how `cmd_governance_assess` actually writes `governance.json` and its evidence (is `kind` present? what does the evidence file contain?). |
| S2-L1-003 | A3 | Are the evidence and decision bindings, the single-use rule and the effective-verdict rule now complete? Does the contract still leave a replay or a stale-decision path? |
| S2-L1-005 | A5 | The repository mutex shared with `requirements bind`, `cmd_init` and the C1 acknowledgement. Is the location `workitems/.refinement-transaction.lock` really outside the closed configuration-reference set and the runtime-member pin? Is `os.open(O_EXCL)` really consistent with the exclusive-open invariant test? |
| S2-L1-006 · S2-L2-001 | A5, §0.6.1 | **The central claim: there is no cross-WorkItem hold.** The amendment says brief §3.5's "held from apply through re-assessment" is the originating WorkItem's own session lock, not a hold on others. Re-read `BRIEF.md` §3.5 and C1 and say whether that reading is right. If it is, is the `AWAITING_REASSESSMENT` state plus optimistic base-SHA checks sufficient for other sharers? If it is wrong, say what the brief requires instead. |
| S2-L1-008 | merged code | Review `architecture_requirements_precondition` and its three call sites as code. Is the replay exemption sound (could it be used to bypass the check)? Is "fails closed for a record with no basis" actually true? Does it behave correctly when `read_architecture_catalog` raises, when the binding is absent, when a bound document is missing? Do the new tests actually exercise what their names claim? |
| S2-L1-011 | sample edit | The sample was amended with the owner's authorisation (an explicit Dependencies section; the `updated_at` Data Model line aligned with requirement 5). Is the contradiction really resolved, with no new one introduced? Read the whole document. Are the two copies identical? |
| S2-L1-015 · S2-L2-003 | A15 | Is the pin inventory now consistent with A5/A6? In particular: do the lock and the transaction index (repository-level files under `workitems/`) really avoid both `test_the_repository_configuration_members_have_a_closed_reference_set` and the `workitem_runtime_member_names` pin? Read those tests. |
| S2-L1-016 | A16 | Does `cmd_init` taking the mutex and refusing while any loop is non-terminal or a `PENDING` transaction names the WorkItem close the race? Check `cmd_init` in the source. |
| S2-L2-002 | A6 | Does one repository transaction index (`workitems/.refinement-transactions.json`) remove the isolation violation of per-WorkItem pointers, and the crash window across several writes? Does it respect scenario 12 and C1's "audit entries only" exception? |

Dispositions: `RESOLVED` — the amendment as written closes it. `UPHELD` — it is still open, and say exactly what is
missing. `REVISED` — closed in part, say which part is not. `WITHDRAWN` — it no longer applies for a reason
other than the amendment. Use the finding id as `finding_id`. One entry per id above (S2-L1-006 and S2-L2-001
count separately, so 11 entries).

## Also verify these specific claims independently

1. **`MEASUREMENT.md`'s tables.** Recompute them from `stage2/dependencies-measurement/out/*.json` and
   `manifest.json` (read-only Python is fine). Report any number that does not match.
2. **The two self-corrections** in PLAN §0.6.1 and the ledger: that the seeded `defect-dependencies.md` defect
   is a missing Dependencies *section*; and that the earlier "33 files" cost estimate counted mentions, not
   dependencies. Are they accurate?
3. **Any "Superseded in part" marker that points at the wrong amendment**, or a superseded section whose
   *unsuperseded* remainder now contradicts §0.6.

## New findings

Report a defect only if it is in the **changed material** (§0.6, the merged code, the sample, the measurement),
and give it an id `S2-L3-NNN`. Do not re-report Level 1 or Level 2 findings as new, and do not review anything
that did not change.

## Output

Return **only** a JSON object matching the supplied output schema: `reviewed_commit`; `dispositions` (11
entries); `new_findings` (each with `id`, `severity`, `category` of `defect/<area>` or `improvement/<area>`,
`path`, `line` (0 if none), `claim`, `evidence`, `evidence_type` `executed` or `static`, `suggested_fix`,
`confidence`); and `closure_assessment` — `plan_ready_to_freeze` (would you accept freezing the plan now, with
the one remaining item below handled?), `blocking_disputes` (ids still blocking), and a `summary`.

**Known open item, not for you to resolve:** PLAN §0.6.3 now has no owner decision outstanding, but the
`dependencies` definition text and the check-definition table are **Phase A deliverables**, not part of the
plan, and the amended sample is to be re-measured against the final definition there. Do not mark the plan
unfreezable merely because Phase A has not happened.
