#!/usr/bin/env sh
# Runs one SDLE guardrail hook:  run-hook.sh <guard>
#
# Registered in .claude/settings.json and in each product agent's frontmatter as
#   sh "${CLAUDE_PROJECT_DIR}/.claude/hooks/run-hook.sh" <guard>
# so it starts from the project root whatever directory the session has moved
# to. A bare `python .claude/hooks/hooks.py` resolves against the *current*
# directory, and a hook that cannot start either blocks the call (Python exits 2
# when it cannot open its script) or silently disables the guard.
#
# Resolves a Python 3.11+ interpreter in the order scripts/sdle.sh uses
# (py -3, python3, python, uv run) and execs hooks.py, which sits beside this
# file. A candidate qualifies only if it REPORTS version >= 3.11, which is what
# disposes of the Windows Store stub.
#
# If no interpreter resolves, this says so in the hook protocol instead of
# failing silently: a fence denies the call, a scanner warns the user and
# Claude. Shell builtins only, so it can still report in a minimal environment.

case "$0" in
    */*)  HERE=${0%/*} ;;
    *\\*) HERE=${0%\\*} ;;
    *)    HERE=. ;;
esac
TARGET="$HERE/hooks.py"
GUARD=$1

if [ -n "$SDLE_PYTHON" ]; then
    # Escape hatch for exotic environments and for tests.
    # shellcheck disable=SC2086
    exec $SDLE_PYTHON "$TARGET" "$@"
fi

version_ok() {
    # shellcheck disable=SC2068
    $@ -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 11) else 1)' \
        >/dev/null 2>&1
}

for candidate in "py -3" "python3" "python"; do
    head=${candidate%% *}
    if command -v "$head" >/dev/null 2>&1; then
        # shellcheck disable=SC2086
        if version_ok $candidate; then
            # shellcheck disable=SC2086
            exec $candidate "$TARGET" "$@"
        fi
    fi
done

if command -v uv >/dev/null 2>&1; then
    exec uv run --python 3.11 "$TARGET" "$@"
fi

WHY="no Python 3.11+ interpreter was found (tried py -3, python3, python, uv run). Install Python 3.11 or newer, or install uv."
case "$GUARD" in
    write-fence|product-agent-fence)
        printf '{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": "SDLE %s could not run: %s This guard fails closed, so the call is denied."}}\n' "$GUARD" "$WHY"
        ;;
    secrets-scan)
        printf '{"systemMessage": "SDLE %s could not run: %s This tripwire is off; the engine refusals still apply.", "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "SDLE %s could not run: %s"}}\n' "$GUARD" "$WHY" "$GUARD" "$WHY"
        ;;
    *)
        printf '{"systemMessage": "SDLE %s could not run: %s This tripwire is off; the engine refusals still apply.", "hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": "SDLE %s could not run: %s"}}\n' "$GUARD" "$WHY" "$GUARD" "$WHY"
        ;;
esac
exit 0
