#!/usr/bin/env sh
# PreToolUse (Bash) — dirty-tree guard during the implement phase.
#
# A tripwire, not the guarantee. The guarantee is `sdle.py implement
# preflight`, which refuses and pins implementation_base_ref. This hook exists
# so that a model that skipped preflight still trips before writing code.

DIR=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cat >/dev/null

phase=$(sh "$DIR/scripts/sdle.sh" state get --field current_phase 2>/dev/null \
    | sed -n 's/.*"value"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ "$phase" = "implement" ] || exit 0

pending=$(sh "$DIR/scripts/sdle.sh" state get --field pending_confirm_action 2>/dev/null \
    | sed -n 's/.*"value"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ "$pending" = "implement_dirty_tree" ] && exit 0

base=$(sh "$DIR/scripts/sdle.sh" state get --field implementation_base_ref 2>/dev/null \
    | sed -n 's/.*"value"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -n "$base" ] && exit 0

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"SDLE dirty-tree guard: the implement phase has not run its preflight, so implementation_base_ref is unpinned and uncommitted work may be mixed into the implementation. Run sdle.sh implement preflight first."}}\n'
exit 0
