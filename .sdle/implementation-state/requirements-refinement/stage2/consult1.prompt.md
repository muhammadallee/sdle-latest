# Stage 2 — consultation, round 1: two design questions the owner has put

You are the same independent, adversarial reviewer as in the earlier Stage 2 rounds. You are in a **read-only
sandbox**: do not edit, create or delete files, and do not run anything that writes. Reading and read-only
commands (including read-only `git` and read-only `python`) are fine. `CLAUDE.md` at the repository root states
the invariants; the engine is `scripts/sdle.py`. This is a **consultation**, not a plan review: answer the two
questions below on their merits, with evidence from the code. Do not re-review the rest of the plan.

## The situation

The requirements-refinement plan (`.sdle/implementation-state/requirements-refinement/PLAN.md`, §0.6) has been
through three review rounds. Almost everything the rounds kept finding sits in one place: the machinery for a
**shared document** — one bound by more than one WorkItem — specified by the owner's constraint **C1**
(`BRIEF.md` §2):

> **Shared documents.** If a bound document selected for refinement is also bound by another WorkItem, the engine
> refuses (`refinement_shared_source`) and lists the other WorkItems. The edit proceeds only with an explicit
> acknowledgement naming those WorkItems, recorded in the audit of **every** affected WorkItem. The refinement
> never edits a copy; `requirements/` stays the single source of truth. The document write and every audit entry
> form one **recoverable transaction** (§3.5).

That machinery is the C1 transaction, the repository transaction index (A6), the mutex (A5), and the owner's
decision (D) (§0.6.3, completed in §0.6.6): an **in-flight claim** recorded in the index when `apply` commits,
refused by every other WorkItem's start-check unless acknowledged by name.

**The owner has just made an observation.** In a team, each person works in their own working copy — a clone or a
`git worktree`. A change a refinement loop makes to a bound document is **not available to anyone else until the
person commits and pushes** and the others pull. So (they ask) is the cross-person concurrency the machinery
guards against real?

Claude's analysis, which you are asked to attack, not to accept:

1. Across separate working copies SDLE can neither see nor lock the other copy; git is the coordination layer.
   After a pull the changed file's digest differs, so the other WorkItem goes `governance_stale` and re-assesses;
   a simultaneous edit is an ordinary git merge conflict.
2. `.gitignore` excludes only `workitems/*/.sdle/lock`, `workitems/.active-context.json` and
   `.sdle/architecture/catalog.lock`. Everything else under `workitems/` is **versioned** by design (`CLAUDE.md`),
   including `audit.md`, `state.json`, and — unless the plan ignores it — the A6 index. So an in-flight claim
   recorded there would travel through git as a stale "someone is refining this" notice.
3. C1 requires the acknowledgement to be written into the audit of **every affected WorkItem**. Each audit entry is
   hash-chained (`prev_sha`) and `state.json` carries `audit_sha`. Writing into another WorkItem's audit gives a
   chain that was designed to have one writer a second writer; two branches that each appended to it will conflict
   on merge, and a hand-resolved merge breaks the chain, so `audit verify` fails. (Claude reasoned this from how
   the chain works and has not reproduced it.)

## Question 1 — decision (D)

Should the **in-flight claim of decision (D) be dropped**, returning to: each WorkItem's own `AWAITING_REASSESSMENT`
state, the base-SHA check on every edit, and `governance_stale` for every other sharer? Consider the alternatives:
drop it; keep it but make the index local and gitignored (like the lock); keep it as specified. Say which you would
choose and why, including the case where **several WorkItems share one working copy** (two terminals on one machine,
or one developer running several WorkItems), which is the only case a claim can serve.

## Question 2 — C1's audit requirement

Should C1's "recorded in the audit of **every** affected WorkItem" be **amended** to "recorded in the refining
WorkItem's own audit, naming the others", so that no WorkItem's audit is ever appended to by another? First **check
the hazard in the code**: read `append_audit`, the audit chain, `audit verify`, `state.audit_sha`, and how drift and
state loading treat a mismatch. Is the two-writer problem real? If it is, is there a way to inform the affected
WorkItems that stays inside C1's *intent* without a second writer on their chains (for example a separate,
non-chained notice record, or relying on `governance_stale`)? If it is not real, say why.

## Also say

- If the answers to 1 and 2 are both "yes", **what machinery in §0.6 can then be removed, and what must stay?**
  Be specific: the C1 transaction, the A6 index, the A5 mutex, A4's recovery, the `AWAITING_REASSESSMENT` state.
- Anything the owner's observation implies that Claude has **missed or got wrong**.

## Output

Return **only** a JSON object matching the supplied output schema (the review-findings schema). Use it this way:

- **Exactly two "answer" findings**, with `id` `CONSULT-Q1` and `CONSULT-Q2`: `category` `answer/decision-D` and
  `answer/C1-audit`; `claim` = your position, starting with one of `AGREE`, `DISAGREE`, `PARTIALLY AGREE` (with
  Claude's proposed answer in the situation above), then your recommendation; `evidence` = what you read, with
  file and line; `suggested_fix` = exactly what to change in the plan; `severity` your view of how much it matters.
- Any further point as a finding with an id `CONSULT-R01`, `CONSULT-R02`, … and `category` `defect/<area>` for
  something wrong, or `improvement/<area>` for something better — including objections to Claude's analysis.
- `ac_ids`: the plan items touched (e.g. `["C1", "D", "A5", "A6"]`).
- `coverage.areas_not_reviewed`: be specific about what you did not reach.
