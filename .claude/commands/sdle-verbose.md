---
description: Toggle display of SDLE internal operational detail.
argument-hint: "on|off"
---

`sdle.sh state set --field verbose --value true` for `on`, `--value false`
for `off`. With no argument, report `sdle.sh state get --field verbose`.

Verbose mode only changes what is displayed. It never changes what is
enforced — and it is the one mode in which SpecKit skill names may be shown.
