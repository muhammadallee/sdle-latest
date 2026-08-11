#!/usr/bin/env sh
# SDLE launcher (POSIX sh — Linux, macOS, Git Bash on Windows).
#
# Resolves a Python 3.11+ interpreter and execs scripts/sdle.py through it.
# Callers (hooks, slash commands, the skill) invoke this rather than sdle.py
# directly, because they cannot ask sdle.py where Python is.
#
# Resolution order: py -3 -> python3 -> python -> uv run -> refuse.
# A candidate qualifies only if it successfully REPORTS a version >= 3.11.
# Gating on a reported version rather than on the command merely existing is
# what disposes of the Windows Store stub, which resolves on PATH but is not
# an interpreter.
#
# Uses shell builtins only -- no dirname, no cat. This script has to be able
# to report "no interpreter found" in a minimal environment, which is exactly
# the environment where external binaries may also be unreachable.

# Strip the trailing component of $0 without calling dirname. Git Bash hands
# this script a backslash-separated $0, so both separators are handled.
case "$0" in
    */*)  TARGET_DIR=${0%/*} ;;
    *\\*) TARGET_DIR=${0%\\*} ;;
    *)    TARGET_DIR=. ;;
esac
TARGET="$TARGET_DIR/sdle.py"

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

# Refuse in the same envelope shape every other refusal uses, so callers can
# parse this failure exactly like any other.
printf '%s\n' '{'
printf '%s\n' '  "ok": false,'
printf '%s\n' '  "command": "launcher",'
printf '%s\n' '  "reason": "no_interpreter",'
printf '%s\n' '  "message": "SDLE requires Python 3.11+. Tried: py -3, python3, python, uv run. Install Python 3.11 or newer, or install uv (https://docs.astral.sh/uv/), then retry.",'
printf '%s\n' '  "data": {"tried": ["py -3", "python3", "python", "uv run"]}'
printf '%s\n' '}'
printf '%s\n' 'sdle: no Python 3.11+ interpreter found (tried py -3, python3, python, uv run).' >&2
exit 1
