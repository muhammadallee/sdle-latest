# Requirements refinement — known gaps recorded for future enhancement runs

These were found while building requirements refinement and the requirements-change guidance, judged safe to ship
without, and are recorded here so a later enhancement run starts from the reasoning instead of rediscovering it.
Each says what happens today, why it was left, what a fix would involve, and what should trigger doing it.
Decisions are in `docs/architecture/ADR-015-requirements-refinement.md`; the full build record is
`.sdle/implementation-state/requirements-refinement/REPORT.md` and `LEDGER.md`.

## 1. Editing a document that a *started* WorkItem holds

**Today.** If another WorkItem has started (it has a state that is not complete, or it has its own refinement loop
open) and is bound to a document a refinement would change, the engine refuses `refinement_shared_source`, names that
WorkItem, and offers no override. If every other holder has **not** started, the edit is allowed and they are told.
The person's way forward for a started holder is to finish or re-bind it, or edit by hand and re-assess each WorkItem.

**Why it was left.** Letting the edit through safely means recording it in *both* WorkItems' audit trails, and that
means one WorkItem writing into another's trail. An experiment showed that two writers on one audit chain break it
(`audit_chain_broken`), and the rule that a WorkItem's records are written only by that WorkItem is one of the
engine's invariants. Refusing is fail-closed and loses nothing.

**What a fix involves.** A decision on how a WorkItem may be changed by another one's action: either an explicit
cross-WorkItem acknowledgement recorded in each affected trail (with a repository transaction index and crash
recovery for a crash between the document write and the trail entries — the design is kept in PLAN.md section 0.6.6),
or a different model in which the *affected* WorkItem records the change itself at its next command (a "pending
external change" that it must acknowledge). The second keeps the single-writer rule.

**Trigger.** Real users hitting `refinement_shared_source` on documents that several active WorkItems share, e.g.
a shared product requirements file. Until then the refusal is the right default. Acceptance scenarios 18 and 29 of the
brief stay unreported as passing until this is done.

## 2. What happens to existing files after a rollback

**Today.** `restart` clears the approvals from the chosen phase on, trims later history, and records the person's
chosen approach (`--approach rebuild|update`) in the audit entry. It deletes no file. The phases are then redone by
the orchestrator (the model) following the prompt: *update* edits the existing artifact guided by the change summary,
*rebuild* regenerates it. Every cleared gate is a human gate again.

**Why it was left.** The engine records and enforces the *process* — approvals, fingerprints, reviews — and cannot judge
whether a redone plan correctly reflects a changed requirement. The docs say so plainly so nobody reads the record of an
approach as a guarantee of the result.

**What a fix involves.** Making *update* auditable: require, per regenerated artifact, a short "what changed and why"
note that the engine stores and the gate displays, so a reviewer sees the delta and not only the new whole; optionally
check that the note names each changed bound document. Making *rebuild* stricter would mean the engine deleting or
moving the old artifact aside, which it deliberately does not do today.

**Trigger.** Reports of redone work that missed an indirect effect of a change, or a team that wants the delta as an
approval artifact.

## 3. Only this checkout is visible

**Today.** Everything that asks "who else holds this document?" — the shared-document rule, the affected-WorkItems
notice, the `alsoHeldBy` facts — reads the WorkItems under `workitems/` in the current checkout. Another branch, another
worktree, a teammate's uncommitted copy, or a fork is invisible. The notices say so.

**Why it was left.** The engine has no view outside the working tree, and inventing one (reading other branches through
Git) would make a refusal depend on repository state the person cannot see.

**What a fix involves.** An opt-in comparison against a named branch or remote ref (read-only, through Git) that adds
"also held on `<branch>`" to the facts and the notice, never to a refusal. A merge-time check (CI) that fails when two
branches changed the same bound document and both have assessments would catch the case where it matters.

**Trigger.** More than one person working on WorkItems that share requirements documents.

## Also recorded, with their reasons, in the report

- **Truncated or replaced old assessment evidence defeats the verdict-flip rule** (RR-010). Someone with a shell can do
  this; it is the same class as deleting the evidence, which the engine never promised to stop. A fix would be a
  hash-chain over assessment evidence, so a gap is detectable. Stated to users in Getting Started.
- **Assessments made before the content digest existed cannot always be compared** (RR-011). New assessments always
  record one. Stated to users in Getting Started.
- **That the assessor never sees earlier verdicts is a convention** of the orchestrator's prompt. A fix would be for the
  engine to build the assessor's input itself (the documents and the check definitions only) and have the parent pass
  it through unchanged. Stated to users in Getting Started.
