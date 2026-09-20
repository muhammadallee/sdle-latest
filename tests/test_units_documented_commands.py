"""D05 (SDLE-DEFECT-STABILIZATION-01) — instructions agree with the runtime.

Three kinds of drift were found between what the documentation tells a user
or the orchestrator to type and what the engine accepts:

* **SpecKit installation.** Every document said `specify init . --skills
  --here`. SpecKit v1.0.6 rejects it (`No such option: --skills`); its Claude
  integration installs skills by default. The command SDLE now documents is
  the one actually run in a disposable project, held in one constant.
* **Option position.** `--workitem` and `--session` are *global* options and
  must precede the subcommand. SKILL.md told the orchestrator to run
  `sdle.sh lock acquire --session <token>`, and `/sdle-start` said
  `init --session <token>`: both are usage errors (exit 2) under the real
  parser. Every documented invocation is now parsed here by that parser.
* **Feature selection.** The spec-phase instruction still described taking
  "the newest directory", while `feature resolve` refuses more than one
  candidate. The instruction now states the engine's rule.

The position check reads the real parser rather than a hand-kept list: for
every documented invocation, each global option written *after* the
subcommand must be one that subcommand's own parser defines (as
`workitem use --workitem` deliberately does).
Invocations are prose as often as they are complete commands — "run
`sdle.sh advance`", synopses with `[--path <p>]` — so they are not parsed
whole; only the property that went wrong is checked.
"""

from __future__ import annotations

import re
import shlex

import pytest

from conftest import REPO_ROOT, sdle

EXIT_REFUSED = 1

# The documents a user or the orchestrator copies commands out of: every prose
# surface that can carry a command, including the product agents' prompts,
# CLAUDE.md and the launcher README.
DOCUMENTS = sorted(
    list((REPO_ROOT / ".claude").rglob("*.md"))
    + [REPO_ROOT / "README.md", REPO_ROOT / "CLAUDE.md",
       REPO_ROOT / "scripts" / "README.md"]
    + list((REPO_ROOT / "docs").rglob("*.md"))
)

# A launcher, optionally run through `sh`, an interpreter or `$PY`, and
# optionally written `./` or `.\`, in inline code or as a line of a fenced block
# (a `$ ` prompt is allowed).
LAUNCHER = r"(?:scripts[/\\])?sdle\.(?:sh|ps1|py)"
PREFIX = r"(?:(?:sh|bash|python3?|py -3|\$PY)[ ]+)?(?:\.[/\\])?"
INVOCATION = re.compile(r"`" + PREFIX + r"(" + LAUNCHER + r" [^`\n]+)`")
FENCED_LINE = re.compile(
    r"^[ \t]*(?:\$ )?" + PREFIX + r"(" + LAUNCHER + r" .+)$", re.M)
FENCE = re.compile(r"^(?:```|~~~)[^\n]*\n(.*?)^(?:```|~~~)[ \t]*$", re.M | re.S)
TRAILING_COMMENT = re.compile(r"\s+#\s.*$")
PLACEHOLDER = re.compile(r"<[^<>]*>")


def invocations_in(text: str) -> list[str]:
    """Every launcher invocation in a document: inline code, and the lines of
    fenced blocks. A fenced line that continues onto the next with a trailing
    backslash is read as far as its first line, which carries the subcommand;
    a trailing `# comment` is not part of the command."""
    found = [match.group(1) for match in INVOCATION.finditer(text)]
    for block in FENCE.finditer(text):
        for match in FENCED_LINE.finditer(block.group(1)):
            command = TRAILING_COMMENT.sub("", match.group(1)).rstrip(" \\")
            if command:
                found.append(command)
    return found


def documented_invocations() -> list[tuple[str, str]]:
    found = []
    for path in DOCUMENTS:
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        for invocation in invocations_in(text):
            found.append((path.relative_to(REPO_ROOT).as_posix(), invocation))
    return found


def argv_of(invocation: str) -> list[str]:
    """The invocation as argv, placeholders filled with a neutral value."""
    concrete = PLACEHOLDER.sub("x", invocation)
    concrete = concrete.replace("$ARGUMENTS", "x").replace("…", "x")
    return shlex.split(concrete)[1:]  # drop the launcher itself


def test_the_scan_finds_the_invocations_it_exists_to_check():
    """Non-vacuity: a regex that stopped matching would pass everything."""
    invocations = documented_invocations()
    assert len(invocations) > 50, len(invocations)
    commands = set()
    for _, text in invocations:
        argv = argv_of(text)
        while argv and argv[0].startswith("-"):
            argv = argv[2:] if argv[0] in GLOBAL_OPTIONS else argv[1:]
        if argv:
            commands.add(argv[0])
    assert {"preflight", "manifest", "gate", "init", "lock"} <= commands, (
        sorted(commands))


def _subparsers(parser) -> dict:
    for action in parser._actions:
        if action.__class__.__name__ == "_SubParsersAction":
            return action.choices
    return {}


def _options(parser) -> set[str]:
    return {o for action in parser._actions for o in action.option_strings}


GLOBAL_OPTIONS = _options(sdle.build_parser()) - {"-h", "--help"}


def misplaced_globals(argv: list[str]) -> list[str]:
    """Global options written after the subcommand that the subcommand's own
    parser does not define — each of which argparse rejects."""
    parser = sdle.build_parser()
    index = 0
    while index < len(argv) and argv[index].startswith("-"):
        index += 2 if argv[index] in GLOBAL_OPTIONS else 1  # skip its value
    command = parser
    while index < len(argv) and argv[index] in _subparsers(command):
        command = _subparsers(command)[argv[index]]
        index += 1
    if command is parser:
        return []  # prose, or a command name the scan could not pin down
    own = _options(command)
    return [token for token in argv[index:]
            if token in GLOBAL_OPTIONS and token not in own]


def test_the_position_check_catches_the_forms_that_were_wrong():
    """The check is proven able to fail, on the two invocations D05 found."""
    assert misplaced_globals(["lock", "acquire", "--session", "x"]) == [
        "--session"]
    assert misplaced_globals(["--workitem", "x", "init", "--session", "y"]) \
        == ["--session"]
    assert misplaced_globals(["--session", "x", "lock", "acquire"]) == []
    assert misplaced_globals(["workitem", "use", "--workitem", "x"]) == []


@pytest.mark.parametrize("where, invocation", documented_invocations())
def test_no_documented_invocation_puts_a_global_option_after_its_command(
        where, invocation):
    wrong = misplaced_globals(argv_of(invocation))
    assert not wrong, (
        f"{where}: `{invocation}` places {wrong} after the subcommand; the "
        "CLI rejects that. Global options go before the subcommand: "
        "`sdle.sh --workitem <id> --session <token> <command> ...`.")


GUIDE = REPO_ROOT / "docs" / "GETTING-STARTED.md"


def test_the_getting_started_guide_states_the_tested_speckit_command_exactly():
    guide = GUIDE.read_text(encoding="utf-8")
    assert sdle.SPECKIT_INIT_COMMAND in guide
    assert sdle.SPECKIT_INIT_COMMAND.replace("--script sh", "--script ps") in guide
    assert f"Spec Kit v{sdle.SPECKIT_SUPPORTED_VERSION}" in guide


def test_only_the_getting_started_guide_teaches_the_install_command():
    """One setup recipe. Every other document links to the guide instead of
    restating the command, so there is one place to keep correct."""
    teaching = [p.relative_to(REPO_ROOT).as_posix() for p in DOCUMENTS
                if "dry-runs" not in p.parts  # transcripts quote engine output
                and "specify init --here" in p.read_text(encoding="utf-8")]
    assert teaching == ["docs/GETTING-STARTED.md"], teaching


def test_no_document_still_teaches_the_rejected_skills_flag():
    """`--skills` as an init option is what v1.0.6 rejects. A document may
    quote it only to say it fails."""
    for path in DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "specify init" in line and "--skills" in line:
                lowered = line.lower()
                assert "fail" in lowered or "rejected" in lowered, (
                    f"{path.relative_to(REPO_ROOT)}: {line.strip()}")


def test_the_engine_messages_carry_the_tested_command():
    assert sdle.SPECKIT_INIT_COMMAND in sdle.SPECKIT_MISSING_MESSAGE
    assert "--skills" not in sdle.SPECKIT_INIT_COMMAND
    assert f"@v{sdle.SPECKIT_SUPPORTED_VERSION}" in sdle.SPECKIT_INIT_COMMAND


def test_the_spec_phase_instruction_states_the_engines_selection_rule():
    body = (REPO_ROOT / ".claude" / "skills" / "sdle" / "modules"
            / "phase-execution.md").read_text(encoding="utf-8")
    spec_phase = body[body.index("**Phase 4 — `spec_draft`:**"):
                      body.index("**Phase 5 — `gate_spec`:**")]
    assert "takes the newest directory" not in spec_phase
    assert "share the newest timestamp" not in spec_phase
    assert "more than one is a refusal" in spec_phase
    assert "`feature_ambiguous`" in spec_phase


def test_feature_resolve_refuses_the_ambiguity_the_instruction_describes(
        started):
    """The code half of the same agreement, against real directories."""
    for name in ("001-todo-api", "002-something-else"):
        started.write_artifact(f"specs/{name}/spec.md")
    before = started.state()["specKit"]["featureDirectory"]

    result = started.run("feature", "resolve")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "feature_ambiguous", result
    assert result.data["candidates"] == ["001-todo-api", "002-something-else"]
    assert started.state()["specKit"]["featureDirectory"] == before


def test_preflight_in_a_repository_with_no_workitem_asks_for_one_first(
        bare_project):
    """Why the documented bootstrap order is identity first, then
    preflight: preflight resolves a WorkItem like every runtime command."""
    result = bare_project.run("preflight")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_required", result

    bare_project.ok("workitem", "create", "--name", "Todo API")
    assert bare_project.ok("--workitem", "todo-api", "preflight").data[
        "problems"] == []


def test_the_guides_sample_requirements_equal_the_sample_file():
    """The guide prints the sample in full so a reader need not open another
    file. It is a copy, so it is pinned equal to the source."""
    guide = GUIDE.read_text(encoding="utf-8").replace("\r\n", "\n")
    start = guide.index("````markdown\n") + len("````markdown\n")
    embedded = guide[start:guide.index("\n````\n", start)]
    sample = (REPO_ROOT / "requirements" / "todo-api.md").read_text(
        encoding="utf-8").replace("\r\n", "\n")
    assert embedded.rstrip("\n") == sample.rstrip("\n")


# -- coverage of the scan itself ---------------------------------------------

FENCE_MARK = chr(96) * 3


def test_the_scan_reaches_every_surface_a_command_can_be_copied_from():
    scanned = {where for where, _ in documented_invocations()}

    documents = {p.relative_to(REPO_ROOT).as_posix() for p in DOCUMENTS}
    assert {"CLAUDE.md", "scripts/README.md", "README.md",
            ".claude/agents/sdle-code-review.md"} <= documents
    assert "scripts/README.md" in scanned, "the launcher README's invocations are parsed"
    assert any(where.startswith(".claude/commands/") for where in scanned)


def test_invocations_are_read_from_fenced_blocks_and_launcher_prefixes():
    text = "\n".join([
        "Inline: `sdle.sh gate show --gate gate_spec` and `sh scripts/sdle.sh preflight`.",
        FENCE_MARK + "bash",
        "sh scripts/sdle.sh constants     # a comment",
        "$ python scripts/sdle.py validate",
        "$PY scripts/sdle.py state dump",
        "./scripts/sdle.sh resume",
        "not a command: echo sdle.sh",
        FENCE_MARK,
    ])
    found = invocations_in(text)
    assert "scripts/sdle.sh preflight" in found
    assert "scripts/sdle.sh constants" in found
    assert "scripts/sdle.py validate" in found
    assert "scripts/sdle.py state dump" in found
    assert "scripts/sdle.sh resume" in found
    assert not any("echo" in item for item in found)


def test_a_misplaced_global_option_in_a_fenced_block_is_caught():
    """The check that only read inline code would have passed this."""
    text = FENCE_MARK + "bash\nsh scripts/sdle.sh lock acquire --session abc\n" + FENCE_MARK
    (invocation,) = invocations_in(text)
    assert misplaced_globals(argv_of(invocation)) == ["--session"]
