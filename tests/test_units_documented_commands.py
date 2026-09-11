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
`migrate-workflow --workitem` and `workitem use --workitem` deliberately do).
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

# The documents a user or the orchestrator copies commands out of. Two
# records are excluded because they quote history as it was: the transition
# log, and the verification record, which quotes the wrong forms this test
# exists to catch.
DOCUMENTS = sorted(
    [p for p in (REPO_ROOT / ".claude").rglob("*.md")
     if "agents" not in p.parts]
    + [REPO_ROOT / "README.md"]
    + [p for p in (REPO_ROOT / "docs").rglob("*.md")
       if "transition" not in p.parts and "verification" not in p.parts]
)

INVOCATION = re.compile(r"`((?:scripts/)?sdle\.(?:sh|ps1|py) [^`]+)`")
PLACEHOLDER = re.compile(r"<[^<>]*>")


def documented_invocations() -> list[tuple[str, str]]:
    found = []
    for path in DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        for match in INVOCATION.finditer(text):
            found.append((path.relative_to(REPO_ROOT).as_posix(),
                          match.group(1)))
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
    assert misplaced_globals(["migrate-workflow", "--workitem", "x"]) == []
    assert misplaced_globals(["workitem", "use", "--workitem", "x"]) == []


@pytest.mark.parametrize("where, invocation", documented_invocations())
def test_no_documented_invocation_puts_a_global_option_after_its_command(
        where, invocation):
    wrong = misplaced_globals(argv_of(invocation))
    assert not wrong, (
        f"{where}: `{invocation}` places {wrong} after the subcommand; the "
        "CLI rejects that. Global options go before the subcommand: "
        "`sdle.sh --workitem <id> --session <token> <command> ...`.")


def test_the_readme_states_the_tested_speckit_command_exactly():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert sdle.SPECKIT_INIT_COMMAND in readme
    assert sdle.SPECKIT_INIT_COMMAND.replace("--script sh",
                                             "--script ps") in readme
    assert f"SpecKit v{sdle.SPECKIT_SUPPORTED_VERSION}" in readme


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
    # The transcript's declared substitution restates the command because a
    # substitution pair must be a literal; this keeps the two equal.
    from conftest import DRY_RUN_SUBSTITUTIONS
    assert any(new.strip() == sdle.SPECKIT_INIT_COMMAND
               for _, new in DRY_RUN_SUBSTITUTIONS)
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
