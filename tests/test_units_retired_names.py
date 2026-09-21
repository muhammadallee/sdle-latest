"""Names the engine no longer has must not appear in living documentation.

State migration and `migrate-workflow` were removed (ADR-010), and the
`.sdle/templates` slot had no reader. A page that still tells a user to run one,
or lists a refusal only the removed command produced, is a defect the link
checker cannot see, because the text is well-formed and the target is prose.

ADRs are excluded on purpose: they record decisions and their history, so a
retired name appears in them where it explains why it was retired.
"""

from __future__ import annotations

import re

import pytest

from conftest import REPO_ROOT, sdle

RETIRED = re.compile(
    r"migrate-workflow|sdle\.sh migrate\b|\bcmd_migrate\b|VERSION_MIGRATION"
    r"|legacy_state_missing|legacy_state_invalid|legacy_audit_broken"
    r"|\.sdle/templates")


def living_documents():
    files = [REPO_ROOT / "README.md", REPO_ROOT / "CLAUDE.md",
             REPO_ROOT / "scripts" / "README.md"]
    files += [p for p in (REPO_ROOT / "docs").rglob("*.md")
              if "architecture" not in p.relative_to(REPO_ROOT / "docs").parts]
    files += list((REPO_ROOT / ".claude").rglob("*.md"))
    return sorted(p for p in files if p.is_file())


def test_the_scan_covers_the_living_documents_and_excludes_the_adrs():
    names = {p.relative_to(REPO_ROOT).as_posix() for p in living_documents()}
    assert {"README.md", "CLAUDE.md", "docs/GETTING-STARTED.md",
            "docs/troubleshooting/README.md", "docs/SDLE-Reference-Guide.md",
            ".claude/skills/sdle/SKILL.md"} <= names
    assert not any(n.startswith("docs/architecture/") for n in names)
    assert len(names) > 30, len(names)


@pytest.mark.parametrize("text", [
    "run `sdle.sh migrate-workflow --workitem x`",
    "| `legacy_audit_broken` | the chain does not verify |",
    '"templates": ".sdle/templates"',
    "the VERSION_MIGRATION table",
])
def test_the_retired_name_pattern_recognises_what_it_is_meant_to(text):
    assert RETIRED.search(text), text


def test_the_retired_commands_really_are_gone_from_the_engine():
    """The list is only true while the engine agrees with it."""
    commands = {name for action in sdle.build_parser()._actions
                if action.__class__.__name__ == "_SubParsersAction"
                for name in action.choices}
    assert "migrate" not in commands and "migrate-workflow" not in commands


@pytest.mark.parametrize("path", living_documents(),
                         ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
def test_no_living_document_names_a_retired_command_or_path(path):
    hits = [(n, line.strip()[:100])
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
            if RETIRED.search(line)]
    assert hits == [], hits
