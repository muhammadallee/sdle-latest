# ADR-015 — Requirements refinement: a loop before the workflow, one verdict per content

**Status:** Accepted, with one decision deferred (see *Deferred*)
**Relates to:** ADR-003 (governance inputs and artifact review), ADR-007 (product subagents), ADR-011 (pinned governance policy), ADR-012 (requirements source binding)

---

## Context

An assessment that blocks on requirements quality used to end in "fix the documents and re-run". Helping with the fixing is useful, and it is also dangerous in exactly the places SDLE exists to be careful: a model that proposes edits, assesses the result and decides whether it passed is marking its own work. Four things had to be settled so that help could not become a way around the engine.

1. **Who may assess.** An assessment is the thing a gate later relies on.
2. **What may change a document, and who decides.** Edits change what a team agreed to build.
3. **What a repeated question may return.** An assessor that answers differently about unchanged text is not measuring the text.
4. **What happens to a document two WorkItems hold.**

## Decision

### 1. `governance assess` stays the only assessment door; the loop only records

`refinement propose|decide|apply|dispute|cancel|show` records findings, questions, edits and decisions in one engine-written record per WorkItem (`workitems/<id>/.sdle/refinement.json`). Nothing in the group assesses. The failing set is read from the engine's own recorded assessment, never from the proposal, and a proposal that carries quality results is refused. The record has its own version, is validated on every read and write, and is refused `refinement_record_invalid` (exit 3) if it is not a file the engine wrote.

### 2. The loop runs before `init`, and `init` waits for it

Refinement works on requirements, and requirements are bound before a workflow exists. After `init` every mutating command refuses `refinement_post_init`; a change to requirements then is an ordinary edit followed by `governance assess`. One short repository mutex (`workitems/.refinement-transaction.lock`, exclusive-create, held for one engine command, never across a model call or a human decision) serialises each mutating command's state-absence check with its write, and is also taken by `requirements bind` and `init`, which is what closes the race between a first proposal and `init`. `init` refuses `refinement_in_progress` while a loop is open.

### 3. A human decides every change in meaning; the engine decides what is only layout

Edits are structured operations (`replace`, `insert_after`, `append_section`) against a bound document, each carrying the digest of the text it was written against, refused `refinement_edit_stale_base` if the document has moved. Whether an edit is presentation-only is computed by comparing the **presentation-neutral normal form** before and after — never by the proposer's say-so. Trailing whitespace on a prose line is *not* neutral (two spaces are a hard line break), and nothing is normalised beyond the narrow set the normal form names. Anything not neutral is applied only after a recorded human acceptance.

### 4. One verdict per content

A check that FAILed at a content cannot later read PASS (or NOT_APPLICABLE) at that same content: `quality_verdict_flip`. "Same content" is the digest of the normal form, so a whitespace edit cannot unlock it. The refusal fires **before** anything is written to `governance.json`, which stays byte-identical, because progression is authorised from that record alone; the attempt is kept as evidence of its own kind and is not assessment history. The history is the WorkItem's own `evidence/governance-*.json` by `kind`, plus the current record, read strictly: unreadable evidence is an integrity failure, never skipped (a zero-byte file is the documented crash placeholder and an object of another kind is simply not history).

The way back from a wrong first answer is `refinement dispute`: independent evidence (a refused re-assessment of the same content that passes the check), a written rationale, and a recorded human decision. It exempts exactly one `(check, content)` pair, each citation can be used once, and an overturned result is reported as `overturned_by_dispute` and never counts as progress.

### 5. The lint is advisory

Deterministic rules over the bound set, each mapped to an existing check and each declaring what it applies to (normative text only for line rules; code, quotation and comments excluded; set-level questions asked of the whole set; duplicate ids judged on definitions, not references). Findings are recorded as evidence with `floorEnforced` always false, and nothing on the assessment path reads them. `floorEligible` records only that a rule has produced no false positive on the measured corpus, so a later decision to enforce one would be a decision and not a default. The brief asked for the lint to floor verdicts; that was deliberately not shipped, and the reason code for a floor refusal is deliberately not defined, because an unreachable refusal would advertise behaviour that does not exist.

### 6. The loop's rules are the engine's

Progress, regression and stall are computed, not asserted: progress is a changed content with fewer failing checks (or an applied human answer); a new failing check is a regression, flagged and never auto-continued; unchanged content, a repeated proposal, or two rounds without progress is a stall and ends `ESCALATED`; reaching the round limit ends `ESCALATED` and refuses `refinement_cap_exhausted` — the record is written first and the refusal follows, the shape `governance assess` already uses for a blocked assessment, so how the loop ended stays inspectable. The limit is one engine constant, lowerable by the `refinement_iteration_cap` policy key, never raisable. A question already answered is not asked again. Findings on `compatibility` and `dependencies` must cite what an existing repository baseline records, resolved against the baseline and its hash-pinned discovery record; whether the entry *supports* the finding remains the assessor's judgement.

### 7. A shared document is refused

If another WorkItem that is not complete also binds a document the loop would change, the engine refuses `refinement_shared_source`, names those WorkItems, and offers no override. Another WorkItem is excluded only when its own current, supported, consistent state proves it complete; pre-init, reset, failed, rejected and every active WorkItem count, because the registry records identity and not lifecycle. An unreadable binding or state of another registered WorkItem fails closed (`refinement_registry_invalid`, exit 3), naming it.

## Deferred

**Acknowledged shared edits.** Letting one WorkItem edit a document another holds — with an acknowledgement recorded in both audit chains, a repository transaction index and crash recovery — was designed and then put on hold by the owner: it requires one WorkItem to write another's audit, which contradicts the rule that a WorkItem's records are written only by that WorkItem, and an experiment showed that two writers on one audit chain break it. The refusal in §7 is the recorded default until that decision is made. The refinement record's independent version means a later `transactions` field can be added with its absence in version 1 read as empty, so choosing either way later needs no migration of `state.json`.

## Consequences

- A person whose requirements are blocked can be helped without the helper being able to mark its own work: the assessor is separate, the failing set is the engine's, and every change in meaning waits for a human.
- A document used by earlier, finished WorkItems can be refined by a later one; one used by a WorkItem still in flight cannot, and the way forward is stated in the refusal.
- The verdict-flip rule is a property of `governance assess`, so it applies to a hand re-run exactly as it does inside the loop.
- The loop's history is the record and its evidence. No audit entry is written before `init`, so none is written by the loop.

## What this does not claim

That the assessor is right (it is a model; the corpus measurement is exploratory — three runs per cell, one model), that a cited baseline entry supports a finding, or that a human rather than the orchestrator typed `approve` or the decision a dispute cites. The last two remain convention, as ADR-007 §3 already says of gates.
