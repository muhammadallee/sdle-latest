#!/usr/bin/env python3
"""Write-scope and shell-mutation guard for SDLE transition agents.

No third-party dependencies. Designed to be called from Claude Code PreToolUse hooks.
Exit 2 blocks the tool call.
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path

MODE = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}

tool = str(payload.get("tool_name") or "")
inputs = payload.get("tool_input") or {}
raw_path = inputs.get("file_path") or inputs.get("path") or ""
# Claude Code delivers file_path as an absolute path, but every policy pattern
# below is repo-relative and anchored. Strip the repo root first, or the
# allow-lists (planner/verifier) match nothing and the deny-list (implementer)
# falls through to its terminal `return True`.
ROOT = Path(__file__).resolve().parents[2].as_posix()
path = str(raw_path).replace("\\", "/")
if path.lower().startswith(ROOT.lower() + "/"):
    path = path[len(ROOT) + 1:]
while path.startswith("./"):
    path = path[2:]

CONTROL_PREFIXES = (
    "docs/transition/transition.md",
    "docs/transition/templates/",
    ".claude/agents/sdle-transition-",
    ".claude/skills/apply-sdle-transition/",
    "tools/transition/",
)

PHASE_PLAN = re.compile(r"^docs/transition/phases/T\d{2}-plan\.md$")
PHASE_HANDOFF = re.compile(r"^docs/transition/phases/T\d{2}-handoff-a\d{2}\.md$")
PHASE_VERIFY = re.compile(r"^docs/transition/phases/T\d{2}-verification-a\d{2}\.md$")
PHASE_CHECKPOINT = re.compile(r"^docs/transition/phases/T\d{2}-checkpoint-a\d{2}-\d{2}\.md$")
PHASE_BLOCKER = re.compile(r"^docs/transition/phases/T\d{2}-blocker\.md$")
PROGRESS = "docs/transition/progress.md"


def deny(msg: str) -> None:
    print("SDLE transition agent guard: " + msg, file=sys.stderr)
    raise SystemExit(2)


def allowed_write(mode: str, p: str) -> bool:
    if p == PROGRESS or PHASE_BLOCKER.match(p):
        return True
    if mode == "planner":
        return bool(PHASE_PLAN.match(p))
    if mode == "verifier":
        return bool(PHASE_VERIFY.match(p))
    if mode == "implementer":
        # Product files are allowed, but migration control-plane contract/evidence
        # owned by other roles is protected below.
        if PHASE_HANDOFF.match(p) or PHASE_CHECKPOINT.match(p):
            return True
        if p.startswith("docs/transition/phases/"):
            return False
        return True
    return False

if tool in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
    if not path:
        deny("cannot establish target path")
    if MODE == "implementer":
        # Protect immutable migration control-plane files from self-modification.
        if any(path == pref or path.startswith(pref) for pref in CONTROL_PREFIXES):
            deny(f"implementer may not modify transition control plane: {path}")
    if not allowed_write(MODE, path):
        deny(f"{MODE} may not write {path}")

# Planner and verifier Bash must stay observational. They can run tests because
# test-side temp writes are not model-authored repository edits. Block obvious
# shell/file/git mutation commands in the submitted command itself.
if tool in {"Bash", "PowerShell"} and MODE in {"planner", "verifier"}:
    cmd = str(inputs.get("command") or "")
    forbidden = [
        r"(^|\s)(rm|del|erase|rmdir|mv|move|cp|copy|touch|mkdir|md)\b",
        r"(^|\s)(git\s+(add|commit|reset|checkout|switch|clean|restore|merge|rebase|cherry-pick|tag|push))\b",
        r"(^|\s)(sed\s+-i|perl\s+-pi)\b",
        r"(^|\s)(tee)\b",
        # Output redirection to a file. Deliberately does NOT fire on stderr
        # suppression (2>/dev/null, 2>$null, 2>&1), on comparison/arrow operators
        # (->, =>, >=, <=, !=), or on a bare trailing >. This is a tripwire, not a
        # shell parser: a `>` inside a quoted string still trips it, which is an
        # accepted false positive. The real controls are the Write/Edit scope
        # check above and control-plane.sha256.
        r"(^|[^>=<!-])>>?\s*(?!&|/dev/null|\$null|NUL\b|nul\b)[^\s&|;>=]",
        r"(^|\s)(Set-Content|Add-Content|Out-File|Remove-Item|Move-Item|Copy-Item|New-Item)\b",
    ]
    for pat in forbidden:
        if re.search(pat, cmd, flags=re.I):
            deny(f"{MODE} Bash/PowerShell must be observational; blocked command shape")

# Implementer Bash is allowed for tests/build tooling, but cannot use shell
# mutation as a back door to rewrite the immutable migration control plane.
if tool in {"Bash", "PowerShell"} and MODE == "implementer":
    cmd = str(inputs.get("command") or "").replace("\\", "/")
    mentions_control = any(pref in cmd for pref in CONTROL_PREFIXES)
    mutating = re.search(
        r"(>>?|\b(rm|del|erase|rmdir|mv|move|cp|copy|sed\s+-i|perl\s+-pi|tee|Set-Content|Add-Content|Out-File|Remove-Item|Move-Item|Copy-Item)\b)",
        cmd, flags=re.I
    )
    if mentions_control and mutating:
        deny("implementer may not mutate transition control plane through Bash/PowerShell")

raise SystemExit(0)
