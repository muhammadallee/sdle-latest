---
description: Advance past a failed step without a verified artifact.
---

Only valid after a failure, and never recommended.

1. `sdle.sh skip`. On exit 1 the status is not `failed` — print `message`
   and stop.
2. Warn the user: the phase advances with no artifact, downstream phases may
   fail or produce incorrect output, and the skip is permanently logged.
3. Only after they confirm: `sdle.sh skip --confirm`.
