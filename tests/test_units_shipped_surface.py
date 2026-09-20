"""The shipped surface carries nothing developer-local (F-012, AC-18).

A target project receives `.claude/` and `scripts/` by copying them. A
per-developer settings file, or a machine path baked into a shipped file, would
travel with them. Nothing here reads the network or a clone's history: it asks
Git which files are tracked and looks at what they say.
"""

from __future__ import annotations

import re
import subprocess

import pytest

from conftest import REPO_ROOT

# Directories whose tracked files are copied into, or run from, a target.
SHIPPED_ROOTS = (".claude", "scripts", ".github")

# A drive-letter path (`D:\Learning\...`, `C:/Users/...`) or a POSIX home path.
# The drive letter must stand alone (no letter or digit before it) and be
# followed by a real directory segment, so `phase:\nUser` in prose or `https://`
# never matches.
DEVELOPER_PATH = re.compile(
    r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/][A-Za-z0-9_. -]{2,}[\\/]"
    r"|/home/[a-z][a-z0-9_-]*/"
    r"|/Users/[A-Za-z][A-Za-z0-9_-]*/")


def tracked(*roots: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z", "--", *roots],
                         cwd=REPO_ROOT, capture_output=True, text=True,
                         check=True).stdout
    return [name for name in out.split("\0") if name]


def test_the_tracked_shipped_set_is_not_empty():
    """Non-vacuity: the two checks below pass over nothing if `git ls-files`
    stops returning the shipped files."""
    files = tracked(*SHIPPED_ROOTS)
    assert len(files) >= 20, files
    assert ".claude/hooks/hooks.py" in files
    assert "scripts/sdle.py" in files


def test_developer_local_settings_are_not_tracked():
    assert ".claude/settings.local.json" not in tracked(".claude")


def test_developer_local_settings_are_ignored():
    """`git check-ignore` exits 0 only when a rule matches the path."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", ".claude/settings.local.json"],
        cwd=REPO_ROOT)
    assert result.returncode == 0


def test_no_tracked_shipped_file_carries_a_developer_path():
    offenders: dict[str, list[str]] = {}
    for name in tracked(*SHIPPED_ROOTS):
        try:
            body = (REPO_ROOT / name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = DEVELOPER_PATH.findall(body)
        if hits:
            offenders[name] = hits[:3]
    assert offenders == {}, offenders


@pytest.mark.parametrize("text", [
    r"D:\Learning\AI\Claude Code\sdle\.claude",
    "C:/Users/bob/project/",
    "/home/alice/work/",
    "/Users/carol/dev/",
])
def test_the_path_pattern_recognises_a_developer_path(text):
    assert DEVELOPER_PATH.search(text), text


@pytest.mark.parametrize("text", [
    r"if the phase:\nUser is asked",
    "https://example.com/a/b/",
    "workitems/<id>/.sdle/state.json",
    "the file:\\n",
])
def test_the_path_pattern_ignores_prose_and_relative_paths(text):
    assert not DEVELOPER_PATH.search(text), text
