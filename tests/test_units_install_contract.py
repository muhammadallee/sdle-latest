"""The installed surface: frontmatter validity and the guide's file inventory.

F-018 and AC-18 (each shipped skill, agent and command file is valid for what it
is), AC-13 and AC-15 (the getting-started guide's inventory covers exactly what a
target project receives). Each rule is checked against its own schema:

* a **skill** (Agent Skills specification): `name` matches its directory and the
  naming pattern; `description` is present and at most 1,024 characters;
* a **subagent** (Claude Code): `name` matches the file, `description` is present,
  `tools` is a comma-separated list;
* a **command**: the invocation name comes from the file name, so `name` is *not*
  required; `description` is present, `argument-hint` is optional.

Two conventions are SDLE's own and are labelled so: no product version in a
description, and a description short enough to read at a glance.
"""

from __future__ import annotations

import fnmatch
import re
import subprocess
from pathlib import Path

import pytest

from conftest import REPO_ROOT

FRONT = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
NAME_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VERSION_MENTION = re.compile(r"\bv\d+\.\d+\b")

SKILL_DESCRIPTION_LIMIT = 1024       # Agent Skills specification
SDLE_DESCRIPTION_LIMIT = 400         # SDLE convention: readable at a glance


def fields(text: str) -> dict[str, str]:
    """Top-level `key: value` lines of the frontmatter. Nested blocks (such as an
    agent's `hooks:`) are ignored: only scalar keys are read."""
    match = FRONT.match(text)
    assert match, "no frontmatter"
    found = {}
    for line in match.group(1).splitlines():
        scalar = re.match(r"^([A-Za-z][A-Za-z0-9_-]*):[ \t]*(.*)$", line)
        if scalar and scalar.group(2):
            found[scalar.group(1)] = scalar.group(2).strip().strip('"')
    return found


def skill_problems(directory: str, text: str) -> list[str]:
    data, problems = fields(text), []
    if data.get("name") != directory:
        problems.append(f"name {data.get('name')!r} must equal its directory {directory!r}")
    if not NAME_PATTERN.match(data.get("name", "")) or len(data.get("name", "")) > 64:
        problems.append("name must be lowercase letters, digits and hyphens, at most 64")
    description = data.get("description", "")
    if not description:
        problems.append("description is required")
    if len(description) > SKILL_DESCRIPTION_LIMIT:
        problems.append(f"description is {len(description)} characters; the limit is {SKILL_DESCRIPTION_LIMIT}")
    if VERSION_MENTION.search(description):
        problems.append("description names a product version (SDLE convention)")
    return problems


def agent_problems(stem: str, text: str) -> list[str]:
    data, problems = fields(text), []
    if data.get("name") != stem:
        problems.append(f"name {data.get('name')!r} must equal the file name {stem!r}")
    if not data.get("description"):
        problems.append("description is required")
    if len(data.get("description", "")) > SDLE_DESCRIPTION_LIMIT:
        problems.append("description is longer than the SDLE convention allows")
    if not data.get("tools"):
        problems.append("tools is required")
    if VERSION_MENTION.search(data.get("description", "")):
        problems.append("description names a product version (SDLE convention)")
    return problems


def command_problems(text: str) -> list[str]:
    data, problems = fields(text), []
    if not data.get("description"):
        problems.append("description is required")
    if len(data.get("description", "")) > SDLE_DESCRIPTION_LIMIT:
        problems.append("description is longer than the SDLE convention allows")
    if VERSION_MENTION.search(data.get("description", "")):
        problems.append("description names a product version (SDLE convention)")
    return problems


# -- the shipped files -------------------------------------------------------


def test_the_skill_frontmatter_is_valid():
    text = (REPO_ROOT / ".claude" / "skills" / "sdle" / "SKILL.md").read_text(encoding="utf-8")
    assert skill_problems("sdle", text) == []


AGENTS = sorted((REPO_ROOT / ".claude" / "agents").glob("sdle-*.md"))
COMMANDS = sorted((REPO_ROOT / ".claude" / "commands").glob("*.md"))


def test_the_agent_and_command_sets_are_not_empty():
    assert len(AGENTS) >= 4 and len(COMMANDS) >= 9


@pytest.mark.parametrize("path", AGENTS, ids=lambda p: p.name)
def test_each_agent_frontmatter_is_valid(path):
    assert agent_problems(path.stem, path.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize("path", COMMANDS, ids=lambda p: p.name)
def test_each_command_frontmatter_is_valid(path):
    assert command_problems(path.read_text(encoding="utf-8")) == []


# -- each rule can fail, and does not over-reach -----------------------------


def test_an_over_length_skill_description_fails():
    text = "---\nname: sdle\ndescription: " + "x" * 1025 + "\n---\nbody\n"
    assert any("limit is 1024" in p for p in skill_problems("sdle", text))


def test_a_skill_whose_name_differs_from_its_directory_fails():
    text = "---\nname: other\ndescription: fine\n---\n"
    assert any("must equal its directory" in p for p in skill_problems("sdle", text))


def test_a_version_in_a_description_fails_as_a_convention():
    text = "---\nname: sdle\ndescription: Runs v1.17 things\n---\n"
    assert any("product version" in p for p in skill_problems("sdle", text))


def test_a_command_without_a_name_is_valid():
    """The invocation name of a command comes from its file name."""
    assert command_problems("---\ndescription: Do the thing.\n---\nbody\n") == []


def test_a_command_without_a_description_fails():
    assert command_problems("---\nargument-hint: x\n---\nbody\n") == ["description is required"]


def test_an_agent_whose_name_differs_from_its_file_fails():
    text = "---\nname: wrong\ndescription: ok\ntools: Read\n---\n"
    assert any("must equal the file name" in p for p in agent_problems("right", text))


def test_an_agent_without_tools_fails():
    assert "tools is required" in agent_problems("a", "---\nname: a\ndescription: ok\n---\n")


# -- the guide's inventory covers exactly what is installed ------------------

GUIDE = REPO_ROOT / "docs" / "GETTING-STARTED.md"
SKILL_FILES = {"SKILL.md", "modules/", "templates/state.json"}


def documented_install_patterns(guide_text: str) -> list[str]:
    """The paths the guide's pre-launch table lists as things you install from
    the SDLE source, as glob patterns relative to the project root."""
    section = re.search(r"(?s)## 7\..*?(?=\n## 8\.)", guide_text.replace("\r\n", "\n")).group(0)
    patterns = []
    for row in (r for r in section.split("\n") if r.startswith("| `")):
        cells = [c.strip() for c in row.strip("|").split("|")]
        if "section 5" not in cells[3]:
            continue
        paths = re.findall(r"`([^`]+)`", cells[0])
        base = ""
        for index, item in enumerate(paths):
            item = item.split(",")[0].strip()
            if item in SKILL_FILES:
                continue
            if index == 0:
                base = item.rsplit("/", 1)[0] + "/" if "/" in item else ""
                patterns.append(item)
            elif "/" not in item and base:
                patterns.append(base + item)
            else:
                patterns.append(item)
    return patterns


def covered(path: str, patterns: list[str]) -> bool:
    for pattern in patterns:
        if pattern.endswith("/") and path.startswith(pattern):
            return True
        if fnmatch.fnmatch(path, pattern):
            return True
    return False


def tracked(*roots: str) -> list[str]:
    out = subprocess.run(["git", "ls-files", "-z", "--", *roots], cwd=REPO_ROOT,
                         capture_output=True, text=True, check=True).stdout
    return [p for p in out.split("\0") if p]


def test_the_inventory_patterns_are_read_from_the_guide():
    patterns = documented_install_patterns(GUIDE.read_text(encoding="utf-8"))
    for expected in (".claude/skills/sdle/", ".claude/commands/", ".claude/agents/sdle-*.md",
                     ".claude/hooks/hooks.py", ".claude/hooks/run-hook.sh",
                     ".claude/settings.json", "scripts/sdle.py", "scripts/sdle.sh",
                     "scripts/sdle.ps1"):
        assert expected in patterns, (expected, patterns)


def test_every_installed_file_is_covered_by_the_guides_inventory():
    patterns = documented_install_patterns(GUIDE.read_text(encoding="utf-8"))
    installed = tracked(".claude") + [
        "scripts/sdle.py", "scripts/sdle.sh", "scripts/sdle.ps1"]
    uncovered = sorted(p for p in installed if not covered(p, patterns))
    assert uncovered == [], f"tracked files the guide does not tell you to install: {uncovered}"


def test_every_documented_source_path_exists_in_the_repository():
    patterns = documented_install_patterns(GUIDE.read_text(encoding="utf-8"))
    for pattern in patterns:
        if pattern.endswith("/"):
            assert (REPO_ROOT / pattern).is_dir(), pattern
        elif "*" in pattern:
            assert list(REPO_ROOT.glob(pattern)), pattern
        else:
            assert (REPO_ROOT / pattern).is_file(), pattern


def test_a_tracked_file_the_guide_omits_is_detected():
    patterns = documented_install_patterns(GUIDE.read_text(encoding="utf-8"))
    assert not covered(".claude/hooks/extra-hook.py", patterns)
    assert not covered("scripts/README.md", patterns)
    assert covered(".claude/agents/sdle-code-review.md", patterns)


def test_the_files_that_must_never_be_installed_are_not_tracked():
    assert ".claude/settings.local.json" not in tracked(".claude")


# -- the test dependencies are pinned and CI uses the pin --------------------


def requirement_lines() -> list[str]:
    text = (REPO_ROOT / "requirements-dev.txt").read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.strip().startswith("#")]


def test_every_test_dependency_is_pinned_exactly():
    lines = requirement_lines()
    assert lines and any(line.startswith("pytest==") for line in lines)
    unpinned = [line for line in lines if "==" not in line]
    assert unpinned == [], unpinned


def test_ci_installs_the_pinned_dependencies_and_declares_its_python_matrix():
    ci = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    assert "-r requirements-dev.txt" in ci
    assert "pip install --quiet pytest" not in ci, "an unpinned install has come back"
    matrix = re.search(r'python:\s*\[([^\]]*)\]', ci)
    assert matrix, "CI declares no Python matrix"
    versions = re.findall(r'"([0-9.]+)"', matrix.group(1))
    assert "3.11" in versions, versions
    assert "fetch-depth" not in ci, "normal tests need no history"
