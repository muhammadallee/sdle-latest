---
description: Approve the current gate.
argument-hint: "[comments]"
---

Approving is the most consequential action in SDLE. Do not run this unless the
user has just been shown the artifact content and asked for it.

1. `sdle.sh state get --field current_phase` to identify the gate.
2. `sdle.sh artifact reviews --path <artifact_path>` to confirm the artifact
   carries a current `PASS` review of its exact current content. If it does
   not, record one first — see **Governed Artifact Review** in the capability
   files `sdle.sh resume` reports for this phase. Never record a `PASS` you did
   not perform.
3. `sdle.sh gate approve --gate <gate_key>` — add `--comments "$ARGUMENTS"`
   when arguments were given.
4. On exit 1, print `message` and stop. A refusal here is the guardrail
   working: it means the workflow is not at that gate, the artifact is
   missing, unresolved or unreadable, the Gate 7 manifest is incomplete or its
   test evidence is missing, stale or not a passing run, the WorkItem's
   governance record is missing, blocked or stale, or the artifact's review is
   missing, stale or failed. Do not work around it.
5. On success, print the header and propose the next phase.

If `sdle.sh gate show --gate <gate_key>` reports `required: false`, this gate
is *omittable*: the policy does not require a human approval for it. Approving
it is still permitted and still stricter, so this command needs no change —
but offer the user the alternative (`sdle.sh gate omit --gate <gate_key>`)
rather than approving on their behalf. See **Step 6b** in the gate capability
file `sdle.sh resume` names for this phase.

If `drift_mode` is true in the response, this was a drift re-approval: if
`remaining_drift` is non-empty, present the next drifted artifact.
