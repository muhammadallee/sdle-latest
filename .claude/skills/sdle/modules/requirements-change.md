> **SDLE capability — loaded on demand.** The Internal Constants are already in context from SKILL.md — do not duplicate them here. Nothing in this file is a threshold, an ordinal, a policy value or a decision rule: those live in `sdle.py` and you ask for them. This file carries judgement and presentation only.

## When the requirements changed under a WorkItem

One question: **the requirements this WorkItem was assessed against are not the ones on disk now — what does the user want to do about it?**

You reach this file when a command is refused `governance_stale`, or `sdle.sh governance show` reports the assessment is not fresh. The engine has stopped the next move and told you only that; the facts that follow come from it, and the decision is the **user's**. You do not choose for them, you do not start doing one of the options before they have chosen, and a subagent never does any of it.

### 1. Show what happened, from the engine's facts

The refusal carries `change_facts` (and `governance show` carries the same object). Show it in the conversation, in plain words — the user never opens a file to decide:

- **What changed.** Each document in `changed`, with what happened to it (`modified`, `missing`, `added`, `unbound`) and, for a modified one, the `diff`: say what was added, removed or reworded. If `diffTruncated`, say it is cut; if `diffUnavailable` is present, say there is no copy of the old text to compare with and show only that it changed. If `bindingChanged`, say the set of documents changed, not only their text.
- **Where the WorkItem is.** `workitem`: its flow, its phase, which gates are approved. If it is `null` the workflow has not started.
- **The architecture decision**, if `architecturePlacement` says it was reasoned from older requirements: that gate will refuse until the placement is re-run, and re-assessing alone does not clear it.
- **Who else holds a changed document**, from `alsoHeldBy`, split into started and not started. Say plainly that their assessments are stale too.

Say what you cannot know: who edited, and whether the change is an addition or a contradiction of what exists. That is the user's judgement, and you may offer your reading of it, labelled as a reading.

### 2. Put the choice to the user

Ask which of these they want. Describe each in a sentence, with what it keeps and what it clears:

1. **Carry on.** Assess the requirements again and continue. Nothing is cleared or redone. It fits a change that does not touch what has been built.
2. **Redo from an earlier phase.** Roll back to a phase and redo the work from there. The approvals from that phase on are cleared and given again; no file is deleted. List the phases the engine gives in `restartCandidates` with their numbers and labels — never numbers of your own — and ask which. The right one is the earliest phase that produced something the change affects; say which you think that is and why, and let them decide.
3. **Finish this work, then raise the change as a new WorkItem.** Nothing is redone; the change waits for its own WorkItem. It fits an addition to work that is well advanced. This WorkItem still has to be assessed again before it can finish.
4. **Reset this WorkItem.** Its workflow state and audit trail are discarded; its assessments, records and files stay. Only if the work is obsolete.

If they ask what you would do: early in the work, a change to what it relies on is cheapest to redo; late in the work, an addition is usually better as its own WorkItem; a change that contradicts what was built should be redone from the earliest phase that relied on the old assumption. Say it as a recommendation and let the choice be theirs.

### 3. If they choose to redo, ask how

A second question, because it changes what you do to the existing files:

- **Build on the existing work.** You read each existing artifact together with the change summary and edit only what the change affects, saying what you changed. It keeps what is still right and costs less; it can miss an indirect effect, so every cleared gate is shown in full again.
- **Rebuild from scratch.** You regenerate each phase's artifact as if for the first time. It is cleaner and costs more, and it can lose detail the old one had.

Recommend building on the existing work unless the change contradicts what exists, when rebuilding the affected phases is the safer reading. The user decides.

### 4. Then do exactly that

- **Carry on:** `sdle.sh governance assess` as in the start of a workflow, then continue where you were.
- **Redo:** run `sdle.sh restart --to <N> --approach <rebuild|update>` with the number and the approach the user chose, show what it would clear, and only after they confirm run it again with `--confirm`. Then assess the requirements again — the rollback does not refresh the assessment — and execute the phases from there with the approach you were given. For *build on the existing work*, show at each gate what changed against the previous version of the artifact. Every cleared gate is a human gate again.
- **New WorkItem or reset:** do what the user asked and nothing more; a reset is its own two-step command.

### 5. Things that do not bend

- The user chooses; you describe and recommend.
- `restart` and `reset` are two-step: show, get the confirmation, then confirm.
- A refusal is final. Show its message and stop; never work around it.
- Nothing about the user's choice is written anywhere except by the engine's own commands.
