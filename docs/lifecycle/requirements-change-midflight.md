# When the requirements change while a WorkItem is in progress

A requirements document that a WorkItem is bound to can change at any point in that WorkItem's life — by
hand, by a teammate's commit that arrives with a `git pull`, or by another WorkItem's refinement. This page says what SDLE does
when that happens, what you can do about it, and what each choice costs. It is guidance for a human decision.
SDLE does not make that decision, and this page does not pretend otherwise.

The effects of the four options on state, approvals, files and records are reproduced against the real engine in
`tests/test_units_midflight_changes.py`, with two exceptions that are marked: the "completed" cases use a planted
completed state, and the architecture effects rest on the engine's code and on `tests/test_units_architecture.py`,
not on that file. What no test can show is how well the work is redone after a rollback: SDLE keeps every file and
clears the approvals; redoing the work is the orchestrator's job, and its quality is a judgement, not a guarantee.

## What SDLE does by itself

One thing. The next time that WorkItem tries to move — `advance`, approve a gate, omit a gate or skip —
it is refused `governance_stale` and stays refused until the requirements are assessed again. It cannot tell a
hand edit from a pulled change, a wording fix from a contradiction, or an addition from a reversal: it compares
bytes. It does not clear an approval, delete a file or roll anything back, and a WorkItem that is already complete is
not stopped at all (there is nothing left to refuse); `governance show` reports `fresh: false`.

Two details worth knowing. A gate refuses for its own reasons first — a missing review (`review_missing`) or an
unapproved predecessor is reported before `governance_stale`, so the first refusal you see may not be the stale
one. And an architecture placement reasoned from the old text is refused at its gate
(`architecture_requirements_stale`) until the placement is re-run, which a plain re-assessment does not do.

## The four things you can do

| Option | What it does | What it keeps | What it clears |
|---|---|---|---|
| **Carry on** — assess again, then continue | Replaces the assessment record (the old one stays as evidence) | State, every artifact, every approval | Nothing |
| **Roll back** — `restart phase <N>` | Returns to phase N, two-step confirmed | Every file, the approvals before N, the audit trail (a restart entry is added) | The approvals and fingerprints from N onward, later phase history, pending drift |
| **Finish, then raise a new WorkItem** | Leaves this WorkItem alone; the change becomes separate work | Everything, in both WorkItems | Nothing, but this WorkItem must still be re-assessed to finish |
| **Reset and start again** — `reset`, then `init` (or a new WorkItem) | Deletes this WorkItem's `state.json`, `audit.md` and lock | Its identity, its binding, its assessment and refinement records, its evidence, and every generated file | All approvals and the audit trail; an architecture decision that was approved but not yet implemented is abandoned in the shared catalog (and a reset fails closed if that catalog cannot be read) |

A rollback does **not** delete files, and a reset does not replace anything: it keeps the WorkItem, and starting
again is a separate step. `init` on a reset WorkItem whose requirements changed starts, and then the first move is
refused `governance_stale` until you re-assess. A WorkItem that has already completed can also be rolled back
(reproduced from a completed state; a full second pass through completion is not reproduced here).

Which phase to roll back to is read from the flow the WorkItem is bound to — the number you are shown in its
status header — never from a fixed table, because the same phase has a different number in each of the five flows.

## The scenarios

**1. Before the specification is approved.** Nothing has been decided yet, so little is lost either way.
*Wording or an unrelated section:* carry on. *Draft work relied on the old text:* roll back to the specification
(or to architecture placement if where the capability lives is affected). *Obsolete goal:* reset.
**Recommended:** carry on for a wording change, otherwise roll back to the earliest phase the change affects.

**2. Between approved gates.** The approvals stay approved even if they no longer fit. *The approved artifacts still
fit:* carry on. *They no longer do:* roll back to the earliest phase that produced something the change affects;
that clears its gate and every later one, and the earlier approvals stand. **Recommended:** roll back to the
earliest affected phase; if the change is a clean addition and reopening several decisions costs more than
separate work, finish and raise it as a new WorkItem.

**3. An addition while implementing.** Implementation and earlier approvals are untouched. *The addition fits what is approved:*
carry on. *It does not:* it belongs earlier, so roll back to the first phase that must change. **Recommended:**
finish and raise it as a new WorkItem — it runs as an iterative one against the baseline — unless it is small and
inside what was approved.

**4. A change that contradicts what is being built.** SDLE cannot see the contradiction; it only sees a change.
Carrying on keeps approvals built on assumptions that are no longer true. **Recommended:** roll back to the
earliest phase that relied on the old assumption (often the specification, not implementation). Reset only if
none of the WorkItem should survive.

**5. After the WorkItem completed.** SDLE does not stop a finished WorkItem and does not reopen it.
**Recommended:** raise the change as a new WorkItem. Carrying on only refreshes a completed record; a reset destroys
its workflow state and audit trail (its records and files stay). A completed WorkItem does not count as holding the document, so a new WorkItem can refine it.

**6. Another WorkItem's refinement wants to change a document you are still using.** If your WorkItem has started,
the refinement is refused (`refinement_shared_source`) and writes nothing. If your WorkItem has not started, it is
allowed: your assessment goes stale and SDLE tells the other person you must assess again. **Recommended:** finish or re-bind the other WorkItem first, or
edit by hand and re-assess both; tell whoever owns it before you edit.

**7. Two WorkItems affected differently.** Each is judged separately and nothing coordinates them. An early one
should usually roll back; one that is implementing should usually finish and raise the change as new work; a
completed one is not stopped. There is no cross-WorkItem rollback and no shared record.

**8. An architecture placement already exists.** Before the placement is approved, a plain re-assessment is not
enough: the gate refuses until the placement is re-run, unless the exact decision is already in the catalog.
Rolling back to or before architecture placement abandons a decision that was approved but not yet implemented;
a decision that was already implemented is kept by both a rollback and a reset. **Recommended:** keep the
placement only if the change does not alter where the capability lives; otherwise roll back to architecture placement.

**9. The WorkItem has not started.** Nothing is in flight. Assess the current text before `init`, or run the
refinement loop (`docs/architecture/ADR-015-requirements-refinement.md`). If `init` runs with a stale
assessment it starts, and the first move is refused.

## What SDLE tells you when it happens

When a move is refused `governance_stale`, the refusal and `governance show` now carry **facts**, from one place in
the engine so the two cannot disagree:

- **what changed** - each document, whether it was modified, is missing, was added to the binding or dropped from it,
  and for a modified one a diff against the text as it was assessed (cut after a few dozen lines, and saying so);
- **where the WorkItem is** - its flow, its phase, which gates are approved, and the phases it could roll back to,
  with the numbers it would type;
- **whether the architecture decision** was reasoned from older requirements;
- **who else holds a changed document**, split into WorkItems that have started and ones that have not.

The diff needs the old text, and a hash cannot give that, so every assessment keeps a copy of each bound document in
its own evidence file (up to a size limit per document). An assessment made before this existed, or a document over
the limit, still reports *that* it changed and says why there is no diff.

**It describes and does not recommend.** SDLE cannot know who edited, whether a change adds to what exists or
contradicts it, or which approved artifact depends on which passage. What to do is **your choice**, put to you in the
conversation (`modules/requirements-change.md`):

1. **Carry on** - assess again and continue.
2. **Redo from an earlier phase** - you are shown the phases that can be rolled back to; pick one.
3. **Finish, then raise the change as a new WorkItem.**
4. **Reset this WorkItem.**

If you choose to redo, you are asked a second question, because it changes what happens to the existing files:
**build on the existing work** (each artifact is read together with the change and edited only where the change
reaches, and what changed is shown at each gate) or **rebuild from scratch**. Building on the existing work is the
usual recommendation; rebuilding is the safer reading when the change contradicts what exists. Your choice is
recorded in the audit entry for the rollback (`restart --approach`). Every approval that was cleared is a human
approval again.

Its limits are the ones above: it sees only this checkout, it does not know why a document changed, and an indirect
effect of a change on an artifact is for you to judge, which is why every cleared gate is shown in full again.
