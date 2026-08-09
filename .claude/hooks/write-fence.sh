#!/usr/bin/env sh
# PreToolUse (Write|Edit|MultiEdit) — the write fence.
#
# Governance files are written by the orchestrator through sdle.py, and by
# nothing else. Invariant 6 (single writer) is what the audit chain and drift
# detection both assume; a stray Write to state.json breaks both silently.
#
# Reads the hook payload on stdin, emits a permission decision on stdout.

PAYLOAD=$(cat)

path=$(printf '%s' "$PAYLOAD" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -z "$path" ] && exit 0

# Normalise separators so the same rules apply on Windows. JSON doubles the
# backslashes, so squeeze the duplicate slashes the conversion produces.
norm=$(printf '%s' "$path" | tr '\\' '/' | tr -s '/')

case "$norm" in
    */.workflow/*|.workflow/*)
        reason="'.workflow/' is owned by the SDLE engine. State and audit are written only by scripts/sdle.py, which keeps the audit hash chain and drift baselines consistent. Use the sdle.py subcommand for this change (state, audit, gate, limit set)." ;;
    */requirements/*|requirements/*)
        reason="'requirements/' is the user's ground-truth input. SDLE reads it as data and never edits it." ;;
    */guidance/*|guidance/*)
        reason="'guidance/' is user-authored steering input. SDLE reads it as data and never edits it." ;;
    *)
        exit 0 ;;
esac

printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"SDLE write fence: %s"}}\n' "$reason"
exit 0
