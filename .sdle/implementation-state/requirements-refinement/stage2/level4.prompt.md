# Stage 2 — second targeted verification (the owner's in-flight decision, and the items fixed since the last round)

You are the same independent, adversarial reviewer as in the earlier Stage 2 rounds. You are in a **read-only
sandbox**: do not edit, create or delete files, and do not run anything that writes. Reading and read-only
commands (including read-only `git` and read-only `python`) are fine. `CLAUDE.md` at the repository root states
the invariants; the engine is `scripts/sdle.py`.

This is a **small, targeted** check of changed material only (brief §5). Do not re-review the plan, `BRIEF.md`,
or anything that did not change since your last verification.

## What changed since your last verification

At the last verification you upheld two findings — **S2-L1-006** and **S2-L2-001** — about what brief §3.5's "the
session lock is held from apply through re-assessment" binds, and revised two more (S2-L1-008, S2-L1-016), and
raised S2-L3-001. The owner then made a decision of their own (a design you have not seen):

> **Decision (D), `PLAN.md` §0.6.3, "A5 — S2-L1-006 and S2-L2-001".** C1 already checks, at the start, who else
> shares the document and makes the refiner acknowledge them by name. The only gap is a loop that *starts later*
> while an earlier one is mid-check, because nothing records that one is in progress. So: when `refinement apply`
> commits, the repository transaction index carries an **in-flight claim** for the document; every start-check
> reads it and refuses `refinement_document_in_flight` unless the caller acknowledges the origin by name,
> audited in both WorkItems; the claim is released by the correlated re-assessment or cancelled by `cancel`;
> **no lock and no timer** — an abandoned loop is cleared by the next person's acknowledgement.

Changed material, all in this checkout (the commit under review is `HEAD`):

| What | Where |
|---|---|
| Decision (D), the amended A5 row, the amended A6 row, the §5.c refusal marker, the new tests list | `.sdle/implementation-state/requirements-refinement/PLAN.md` — §0.6.2 (A5, A6), §0.6.3 (the A5 paragraph and option (D)), §0.6.4, §0.6.5 |
| The mutex change for S2-L1-016 (every mutating refinement command holds it across its state-absence check and write) | PLAN §0.6.2 A5 and A16 |
| The marker corrections and the discard table for S2-L3-001 | PLAN: the "Superseded in part by §0.6" markers, the §5.c marker, §0.6.5 |
| The ledger entry recording the decision | `LEDGER.md`, "Current status" |
| **A code change** for S2-L1-008, on its own branch (not merged): a recheck of the requirements basis inside the catalog write | `git diff origin/main...fix/architecture-apply-recheck` (read-only `git` works; the branch is local), and the new test `test_the_requirements_are_rechecked_inside_the_catalog_write` in `tests/test_units_architecture.py` on that branch |

## Your task — one disposition per id

State whether the material **as it is now written** closes each finding. Judge the text and the code.

| Id | What to check |
|---|---|
| S2-L1-006 · S2-L2-001 | Does decision (D) close both? Specifically: does it satisfy the brief's "a second invocation refuses" across WorkItems without choosing either reading of "the session lock"? Is the abandonment concern really gone — can an in-flight claim ever be stuck with no way to clear it (an origin whose record is corrupt, reset or deleted; a document no longer bound by the origin; a claim naming a WorkItem that no longer exists)? Is the override path (acknowledge by name, audited in both, claim marked `OVERRIDDEN`) well defined, and does it leave the *origin's* own loop in a defined state afterwards (its base SHA is now stale)? Does it respect scenario 12 (a WorkItem never writes another's record) and C1's "audit entries only" exception? |
| S2-L1-016 | Does "every mutating refinement command holds the mutex across its state-absence check and its write; `cmd_init` takes the same mutex" now close the race? Is there any mutating path still missing from the list? |
| S2-L1-008 | Read the code diff on `fix/architecture-apply-recheck`. Does the recheck inside `_architecture_apply_locked` close the window you described, or only narrow it? Is the plan's statement of what remains (serialisation with the writers of the bound documents, carried by A5's participant list) accurate? Does the test do what its name claims? |
| S2-L3-001 | Are the supersession markers now correct, §5.c marked, and §0.6.5's discard table complete and accurate? Any retained clause that still contradicts §0.6? |

Dispositions: `RESOLVED` (closed as written), `UPHELD` (still open — say exactly what is missing), `REVISED` (closed in
part — say which part is not), `WITHDRAWN`. Five entries, using the ids above as `finding_id`; S2-L1-006 and
S2-L2-001 are separate entries.

## Specific checks on decision (D) — report anything wrong as a new finding

1. **Where the check runs.** The plan says "every refinement start-check". Is that sufficient? Does it need to
   include `propose`, or only the command that edits the document (`apply`)? Say which and why.
2. **The ordering in A4.** Document write → audit → `COMMITTED`; the in-flight claim is created when `apply`
   commits. Is there a crash point at which a document has been rewritten but no claim exists, so a second
   invocation is not refused? Read A4 and A6 together.
3. **The envelope.** A18's `apply` input carries one `acknowledgement?`. Is that enough to carry both the C1
   shared-source acknowledgement and the in-flight acknowledgement, or is there an inconsistency to fix?
4. **Interaction with A16.** A WorkItem is refused `init` while its own loop is non-terminal. How does that
   interact with its claim, with `OVERRIDDEN`, and with `RELEASED`?
5. **Anything (D) contradicts** elsewhere in §0.6 or in the retained plan text.

## New findings

Only for defects in the changed material above, with ids `S2-L4-NNN`. Do not re-report earlier findings as new.

## Output

Return **only** a JSON object matching the supplied output schema: `reviewed_commit`; `dispositions` (5 entries);
`new_findings` (each with `id`, `severity`, `category` of `defect/<area>` or `improvement/<area>`, `path`, `line`
(0 if none), `claim`, `evidence`, `evidence_type` (`executed` or `static`), `suggested_fix`, `confidence`); and
`closure_assessment` — `plan_ready_to_freeze` (would you accept freezing the plan now?), `blocking_disputes` (ids
still blocking), and a `summary`.

**Known and not for you to resolve:** the `dependencies` definition text and the check-definition table are Phase A
deliverables, and the amended sample is to be re-measured there; do not treat Phase A not having happened as a
blocker. PR #6 (the code change) is open and unmerged; judge the diff, not its merge state.
