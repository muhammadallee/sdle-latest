---
description: Reject the current gate and trigger remediation.
argument-hint: "<feedback>"
---

Feedback is required — a rejection without it records nothing.

If `$ARGUMENTS` is empty, reply exactly:
`Please provide your feedback: /sdle-reject <your feedback>` and stop. Do not
record a rejection or change any state.

Otherwise:
1. `sdle.sh state get --field current_phase` to identify the gate.
2. `sdle.sh gate reject --gate <gate_key> --reason "$ARGUMENTS"`.
3. Print the header and tell the user to say `continue` to re-run the step
   with the feedback applied.
