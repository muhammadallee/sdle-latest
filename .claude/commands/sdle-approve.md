---
description: Approve the current gate.
argument-hint: "[comments]"
---

Approving is the most consequential action in SDLE. Do not run this unless the
user has just been shown the artifact content and asked for it.

1. `sdle.sh state get --field current_phase` to identify the gate.
2. `sdle.sh gate approve --gate <gate_key>` — add `--comments "$ARGUMENTS"`
   when arguments were given.
3. On exit 1, print `message` and stop. A refusal here is the guardrail
   working: it means the workflow is not at that gate, the artifact is
   missing, or the Gate 7 manifest is incomplete. Do not work around it.
4. On success, print the header and propose the next phase.

If `drift_mode` is true in the response, this was a drift re-approval: if
`remaining_drift` is non-empty, present the next drifted artifact.
