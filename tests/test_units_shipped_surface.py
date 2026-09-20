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


# ==========================================================================
# Historical narration in shipped source (F-019, AC-03)
#
# Comments and docstrings that tell the story of an earlier version or of a
# finished task ("T11 D13", "as of v1.15", "pre-v1.14") describe a product that
# no longer exists. Text that reaches a user or the model (help, refusals, hook
# reasons, prompts) must carry none, and does not. The source comments still
# carry some; this is a ratchet, so the number can only go down.
# ==========================================================================

import ast
import io
import tokenize

NARRATION = re.compile(
    r"\bv1\.\d+|\bT(?:0\d|1[01])\b|pre-v1|as of v1|since v1|\bD\d\d\b")

# Lines of comment or docstring naming a version or a task. Lower this when
# narration is rewritten to state the current rule; never raise it.
NARRATION_CEILING = {"scripts/sdle.py": 130, ".claude/hooks/hooks.py": 0}


def narration_lines(relative: str) -> list[tuple[int, str]]:
    source = (REPO_ROOT / relative).read_text(encoding="utf-8")
    found = []
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT and NARRATION.search(token.string):
            found.append((token.start[0], token.string.strip()))
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.Module)):
            body = node.body
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                for offset, line in enumerate(body[0].value.value.split("\n")):
                    if NARRATION.search(line):
                        found.append((body[0].lineno + offset, line.strip()))
    return found


def test_the_narration_pattern_recognises_what_it_is_meant_to():
    for text in ("# T11 D13: the flag", "as of v1.15 the", "a pre-v1.14 state",
                 "since v1.14 it is"):
        assert NARRATION.search(text), text
    assert not NARRATION.search("the current state schema")


def test_runtime_facing_text_carries_no_version_or_task_marker():
    """Refusal messages, CLI help and hook reasons are read by the user and by
    the model. Checked on the string literals passed to the exception types
    and to `help=`, and on the hook module's strings."""
    source = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
    offenders = []
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call)
                and getattr(node.func, "id", None) in (
                    "Refused", "UsageError", "IntegrityError", "SdleError")):
            segment = ast.get_source_segment(source, node) or ""
            if NARRATION.search(segment):
                offenders.append((node.lineno, segment[:80]))
    assert offenders == [], offenders
    hooks = (REPO_ROOT / ".claude" / "hooks" / "hooks.py").read_text(
        encoding="utf-8")
    assert not NARRATION.search(hooks)


@pytest.mark.parametrize("relative", sorted(NARRATION_CEILING))
def test_source_narration_does_not_grow(relative):
    found = narration_lines(relative)
    assert len(found) <= NARRATION_CEILING[relative], (
        relative, len(found), found[:5])


# ==========================================================================
# The prompts do not tell the model to write governed files (CX-001, invariant 6)
#
# `state.json` and `audit.md` have one writer, the engine. A prompt that says
# "set `status` in state" or "append to audit" asks the model to write them by
# hand: the write fence would block it, and a fence that is not there would let
# it fork the audit chain. Every such step names the engine command that owns it.
# ==========================================================================

HAND_WRITE = re.compile(
    r"(?i)\bappend (?:the )?(?:completion event )?to (?:the )?(?:`?audit(?:\.md)?`?)"
    r"|\bappend audit\b"
    r"|\bsave (?:the )?(?:updated )?(?:`?state(?:\.json)?`?)"
    r"|\bupdate `state\.json`"
    r"|\brecord in `state\.json`"
    r"|\bset `(?:status|current_phase|current_artifact|phase_checkpoint"
    r"|security_review_artifact|progress)`"
    r"|\bclear `phase_checkpoint"
    r"|\bin state immediately"
    r"|\bwrite `?completion-summary")


def prompt_files():
    skill = REPO_ROOT / ".claude" / "skills" / "sdle"
    return sorted([*skill.rglob("*.md"),
                   *(REPO_ROOT / ".claude" / "commands").glob("*.md"),
                   *(REPO_ROOT / ".claude" / "agents").glob("*.md")])


def test_the_hand_write_pattern_recognises_what_it_is_meant_to():
    for text in ("Append to audit: `[<ISO>] Phase started.`",
                 "Save state.",
                 "Update `state.json`: set the phase.",
                 "Set `status` to `in_progress`.",
                 "Clear `phase_checkpoint: null`.",
                 "set `security_review_artifact = f` in state immediately",
                 "Record in `state.json` under `approvals`"):
        assert HAND_WRITE.search(text), text
    for text in ("Run `sdle.sh audit append --phase x --event y --message z`.",
                 "Do not edit `state.json` or `audit.md` yourself.",
                 "`sdle.sh checkpoint clear`"):
        assert not HAND_WRITE.search(text), text


def test_the_prompts_hold_the_files_they_are_checked_over():
    files = prompt_files()
    names = {p.name for p in files}
    assert {"SKILL.md", "phase-execution.md", "gate-protocol.md",
            "sdle-start.md", "sdle-code-review.md"} <= names, sorted(names)


@pytest.mark.parametrize("path", prompt_files(), ids=lambda p: p.name)
def test_no_prompt_tells_the_model_to_write_governed_state(path):
    hits = [(n, line.strip()[:120])
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if HAND_WRITE.search(line)]
    assert hits == [], (path.name, hits)
