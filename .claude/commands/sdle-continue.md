---
description: Continue or resume the current SDLE phase.
---

Read `.claude/skills/sdle/SKILL.md` and follow its resume path.

In short: `sdle.sh confirm clear`, then `sdle.sh resume`. It answers, from
disk alone, where this WorkItem is, what is pending, and — in `capabilities` —
exactly which capability files this phase requires. Load those and no others,
then execute `current_phase`. Never decide what to load from prose; the
engine owns that table.

A capability file may send you to another one. Follow that: `capabilities` is
the floor, not the ceiling.

For `retry`, call `sdle.sh retry` first — it refuses while a drift re-approval is pending.

Never advance a phase by hand; `sdle.sh advance` is the only way.
