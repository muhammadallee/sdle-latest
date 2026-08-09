---
description: Roll back to an earlier phase, clearing downstream approvals.
argument-hint: "<phase number 1-18>"
---

Two-step by design.

1. `sdle.sh restart --to $ARGUMENTS`. On exit 1, print `message` and stop —
   a forward jump or a gate phase is refused outright, not confirmable.
2. On success the response has `pending: true`. Show the user which gates
   in `cleared_gates` will be cleared, and ask them to confirm.
3. Only after they confirm: `sdle.sh restart --to $ARGUMENTS --confirm`.
