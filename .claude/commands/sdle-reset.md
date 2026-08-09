---
description: Delete all workflow state. Generated artifacts are preserved.
---

Two-step and irreversible.

1. `sdle.sh reset` — sets the pending confirmation.
2. Warn the user: `.workflow/state.json`, `audit.md` and `lock` will be
   deleted; everything under `.specify/`, `design/`, `reviews/` and
   `clarifications/` survives. This cannot be undone.
3. Only after they confirm: `sdle.sh reset --confirm`.
