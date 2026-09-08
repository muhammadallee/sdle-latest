---
description: Show the SDLE workflow status and full state dump.
---

Run `scripts/sdle.sh state dump` (PowerShell: `scripts/sdle.ps1`).

Print the `rendered` string from the JSON response verbatim, preceded by the
`rendered` string from `sdle.sh header`. Add nothing else — the script owns
both strings.

If the command exits 3, the state is unreadable: show the `message` and offer
`/sdle-reset`.
