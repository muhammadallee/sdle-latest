---
description: Delete all workflow state. Generated artifacts are preserved.
---

Two-step and irreversible.

1. `sdle.sh reset` — sets the pending confirmation.
2. Warn the user: `state.json`, `audit.md` and `lock` under the active
   WorkItem's runtime (`workitems/<id>/.sdle/`) will be deleted; the WorkItem
   identity itself (`workitems/<id>/workitem.json`, `workitems/index.md`), the
   WorkItem's SpecKit artifacts (`workitems/<id>/specs/`) and everything under
   `.specify/`, `design/`, `reviews/` and `clarifications/` survives. This
   cannot be undone.
3. Only after they confirm: `sdle.sh reset --confirm`.
