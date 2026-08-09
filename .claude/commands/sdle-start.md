---
description: Start or resume the SDLE workflow.
argument-hint: "[--verbose]"
---

1. `scripts/sdle.sh preflight`. On exit 1, print `message` and stop — the
   prerequisite is missing and nothing should be initialised.
2. If `.workflow/state.json` exists, this is a resume: run `sdle.sh migrate`,
   then `sdle.sh header`, then follow the skill's resume path.
3. Otherwise run `sdle.sh init --session <8-hex token for this conversation>`.
4. If `$ARGUMENTS` contains `--verbose`, the skill sets verbose mode.
5. Print the header, summarise the requirements found, and propose the next
   phase.

Read `.claude/skills/sdle/SKILL.md` and follow it to execute the phase.
