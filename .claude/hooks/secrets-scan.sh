#!/usr/bin/env sh
# PostToolUse (Write|Edit) — secrets tripwire during the implement phase.
#
# There is no tool event meaning "implementation finished" -- speckit-implement
# is one Skill call spanning many writes -- so this hook cannot be the
# guarantee. The deterministic scan lives in `sdle.py manifest build`, and
# `gate approve --gate gate_implement` REFUSES a manifest without it. This
# hook only surfaces a finding earlier, while the file is fresh.

PAYLOAD=$(cat)
path=$(printf '%s' "$PAYLOAD" | sed -n 's/.*"file_path"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p')
[ -z "$path" ] && exit 0

# Claude Code passes native paths, so on Windows this arrives with
# backslashes -- and JSON doubles them, so the raw capture is "C:\\Users\\...".
# Convert to slashes and squeeze the resulting duplicates. Without this the
# hook silently finds nothing on exactly the platform it ships on.
path=$(printf '%s' "$path" | tr '\\' '/' | tr -s '/')
[ -f "$path" ] || exit 0

if grep -qE 'AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]{36}|sk-[A-Za-z0-9_-]{20,}|Bearer [A-Za-z0-9_.-]{20,}' "$path" 2>/dev/null; then
    printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"SDLE secrets tripwire: %s matches a high-risk credential pattern. It will be listed in the Gate 7 manifest, masked, and the reviewer will see it at the moment of decision. Prefer moving it to an environment variable now."}}\n' "$path"
fi
exit 0
