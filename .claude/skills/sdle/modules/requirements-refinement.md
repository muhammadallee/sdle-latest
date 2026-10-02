> **SDLE capability — loaded on demand.** The Internal Constants are already in context from SKILL.md — do not duplicate them here. Nothing in this file is a threshold, an ordinal, a policy value or a decision rule: those live in `sdle.py` and you ask for them. This file carries judgement and presentation only.

## Requirements Refinement

One question: **can the people who own these requirements fix what an assessment found, with the engine keeping the loop honest?**

Refinement happens **before the workflow starts**. There is no phase for it, so `sdle.sh resume` cannot route you here: `/sdle-start` and `SKILL.md` do, when an assessment comes back blocked and the user wants help fixing the requirements. After `init` the engine refuses (`refinement_post_init`); a change to requirements after that is an ordinary edit followed by `governance assess`.

It is never automatic. Offer it, in plain words, when `governance assess` reports the requirements quality is blocked: what failed, and that a short loop can fix it. If the user declines, they edit the documents themselves and re-assess, exactly as before.

### 1. Who does what

- **`governance assess`** is the only door through which an assessment is made. Nothing in the loop assesses.
- **The assessor** answers the quality checks. Hand it to **`sdle-requirements-review`**: give it the paths of the bound documents, and the check ids and their definitions copied from `sdle.sh governance policy` (`check_definitions`) — it has no shell and its agent file lists none. It returns one answer per check. You put those answers into the governance input; the engine validates them. Assessing yourself is equally valid.
- **You** read the findings and propose changes. A proposal is findings, at most a few questions, and structured edits. It carries no verdicts, and the engine refuses one that does.
- **The human** answers the questions and accepts or rejects each edit that changes what the requirements say. You never decide that for them, and a subagent never does.
- **The engine** checks every edit against the current text, applies only what was accepted, and keeps the record.

### 2. Show before you ask

The findings, the questions and each proposed edit are shown **in the conversation**, with the text that would change. The user never opens a file to decide. Say what each edit does in one plain sentence, and which finding it answers.

Ask only what the document cannot answer for itself, in order of how much each answer would fix, with choices where you can offer them. The engine states how many questions one round may carry; do not guess it.

### 3. The loop

1. `sdle.sh --workitem <id> governance assess --input <path>` — blocked. Note the evidence path it reports.
2. Draft the proposal and run `sdle.sh --workitem <id> refinement propose --input <path>`. The engine reads which checks are failing from its own record, not from you, and refuses a proposal about a stale assessment. Show its report. The lint findings it records are **hints**: advisory, never a verdict, and never a reason to refuse anything.
3. For each question and each edit the user decides, `refinement decide --input <path>`. An edit that only changes presentation (spacing, line endings) the engine applies without asking; whether an edit is that is the engine's call, not yours.
4. `refinement apply --input <path>` for each accepted edit. The engine refuses an edit written against text that has since changed; propose again from the current text.
5. Re-assess with `governance assess`, then `refinement propose` again. The engine compares the new assessment with the last and says whether this is progress, a regression or a stall.
6. The loop ends **passed** when nothing blocking is left; carry on with `init`. It ends **escalated** when it stops making progress or uses all its rounds; see below.

`refinement show` reports where the loop is at any point. `refinement cancel` ends it, with a reason.

### 4. When it does not converge

An escalated loop is not a failure of the user. Say so, and say what happened in plain words: which checks still fail, what was tried, what the engine concluded. The ways forward are the user's: edit the documents by hand and re-assess, answer the open questions with the people who own them, or stop. Do not start a second loop to get around the end of the first.

### 5. When the assessor was wrong

A check that failed once cannot later pass on **unchanged** requirements: the engine refuses the second answer (`quality_verdict_flip`) and keeps the first. That protects against an assessor changing its mind for no reason. If the first answer really was wrong, the way back is `refinement dispute`: it needs the refused re-assessment as independent evidence, a written rationale, and a decision the **human** has made in this conversation. State plainly to the user what overturning means before you ask, record their decision's wording as the reference, and never offer a dispute as a shortcut.

### 6. Shared documents

If another WorkItem still holds a document the loop would change, the engine refuses (`refinement_shared_source`) and names those WorkItems. There is no way to override it here. Explain why in one sentence — editing the document would silently invalidate their assessment — and give the options: finish or re-bind the other WorkItems, or edit by hand and re-assess each one. Do not suggest working on a copy: the requirements stay in one place.

### 7. Things that do not bend

- No edit is applied without the decision the engine asks for.
- No document is edited by any path other than `refinement apply`.
- A refusal is final. Show its message and stop; never work around it.
- A subagent returns answers or text. It never records, applies or decides.
