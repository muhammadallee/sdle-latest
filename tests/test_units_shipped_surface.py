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


# ==========================================================================
# The skill's frontmatter (F-018, AC-18)
#
# Agent Skills limit `description` to 1,024 characters. The description is the
# text Claude reads to decide whether the skill applies, so it leads with the
# phrases that should trigger it, carries no product version (a version there
# is one more copy to drift), and does not claim a directory name that any
# unrelated project might have.
# ==========================================================================

SKILL = REPO_ROOT / ".claude" / "skills" / "sdle" / "SKILL.md"


def skill_description() -> str:
    front = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n",
                     SKILL.read_text(encoding="utf-8"), re.DOTALL)
    assert front, "SKILL.md has no frontmatter"
    line = re.search(r"^description:[ \t]*(.+)$", front.group(1), re.MULTILINE)
    assert line, "SKILL.md frontmatter has no description"
    return line.group(1).strip()


def test_the_skill_description_fits_the_agent_skills_limit():
    assert len(skill_description()) <= 1024, len(skill_description())


def test_the_skill_description_leads_with_its_trigger_phrases():
    """The listing may truncate a long description; whatever survives must be
    the part that says when to use the skill."""
    description = skill_description()
    assert description.startswith("Use when the user says start workflow"), \
        description[:80]
    for phrase in ("start workflow", "continue", "approve", "reject", "status"):
        assert phrase in description[:300], phrase


def test_the_skill_description_carries_no_product_version():
    assert not re.search(r"\bv\d+\.\d+\b", skill_description())


def test_the_skill_does_not_trigger_on_a_bare_requirements_folder():
    """`requirements/` is a common directory name in unrelated projects."""
    description = skill_description().lower()
    assert "requirements/" not in description
    assert "requirements folder" not in description


# ==========================================================================
# Launchers are executable in what a clone receives (F-026)
#
# The prompts run `scripts/sdle.sh <subcommand>` directly. On Linux and macOS
# that is `Permission denied` (exit 126) unless the file's mode carries the
# executable bit, and Git records that bit in the index, not on a Windows disk.
# CI runs `sh scripts/sdle.sh`, which does not need it, so nothing else catches
# a missing bit.
# ==========================================================================

DIRECTLY_INVOKED = ("scripts/sdle.sh", ".claude/hooks/run-hook.sh")


def index_mode(name: str) -> str:
    out = subprocess.run(["git", "ls-files", "-s", "--", name], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True).stdout
    assert out.strip(), f"{name} is not tracked"
    return out.split()[0]


@pytest.mark.parametrize("name", DIRECTLY_INVOKED)
def test_a_directly_invoked_launcher_is_executable_in_the_index(name):
    assert index_mode(name) == "100755", name


def test_the_prompts_really_do_invoke_the_launcher_directly():
    """Non-vacuity: if no prompt runs it bare, the mode requirement above would
    protect nothing and could be dropped on purpose rather than by accident."""
    start = (REPO_ROOT / ".claude" / "commands" / "sdle-start.md").read_text(
        encoding="utf-8")
    assert re.search(r"(?<!sh )scripts/sdle\.sh ", start)
