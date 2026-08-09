---
description: Continue or resume the current SDLE phase.
---

Read `.claude/skills/sdle/SKILL.md` and follow its resume path.

In short: `sdle.sh confirm clear`, then `sdle.sh state get`. If `status` is
`rejected`, this is a remediation — load `modules/gate-protocol.md`. Otherwise
load `modules/phase-execution.md` and execute `current_phase`.

For `retry`, call `sdle.sh retry` first — it refuses while a drift re-approval is pending.

Never advance a phase by hand; `sdle.sh advance` is the only way.
