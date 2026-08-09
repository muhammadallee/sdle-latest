"""lint-skill self-test.

Each case copies the repo, breaks exactly one sync rule, and asserts that the
corresponding named check fires — and that the others still pass. A linter
nobody has proven can fail is not evidence of anything.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

import pytest

from conftest import REPO_ROOT, Project

EXIT_OK, EXIT_REFUSED = 0, 1


@pytest.fixture
def repo(tmp_path: Path) -> Project:
    """A copy of the repo's skill + docs, lintable in isolation."""
    root = tmp_path / "repo"
    (root / ".claude" / "skills").mkdir(parents=True)
    shutil.copytree(REPO_ROOT / ".claude" / "skills" / "sdle",
                    root / ".claude" / "skills" / "sdle")
    (root / "docs").mkdir()
    shutil.copy(REPO_ROOT / "README.md", root / "README.md")
    shutil.copy(REPO_ROOT / "docs" / "SDLE-Reference-Guide.md",
                root / "docs" / "SDLE-Reference-Guide.md")
    return Project(root, root / ".claude" / "skills" / "sdle")


def results(project: Project) -> dict[str, bool]:
    result = project.run("lint-skill")
    return {c["name"]: c["passed"] for c in result.data["checks"]}


def edit(project: Project, relative: str, old: str, new: str) -> None:
    path = project.skill_root / relative
    text = path.read_text(encoding="utf-8")
    assert old in text, f"fixture text not found in {relative}: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def assert_only_failure(project: Project, expected: str) -> None:
    checks = results(project)
    assert expected in checks, f"no check named {expected}"
    assert checks[expected] is False, f"{expected} should have fired"
    others = {k: v for k, v in checks.items() if k != expected and not v}
    assert not others, f"unrelated checks also failed: {sorted(others)}"


# -- baseline ---------------------------------------------------------------


def test_the_repo_passes_every_check(repo):
    result = repo.run("lint-skill")
    assert result.exit_code == EXIT_OK, result.stderr
    assert result.data["failed"] == []
    assert len(result.data["checks"]) > 15, "the rule set should be substantial"


# -- table wellformedness runs first and short-circuits ---------------------


def test_a_renamed_constant_heading_fails_loudly(repo):
    edit(repo, "SKILL.md", "### PROGRESS_MAP", "### PROGRESS_MAP_RENAMED")
    result = repo.run("lint-skill")
    assert result.exit_code == EXIT_REFUSED
    checks = {c["name"]: c["passed"] for c in result.data["checks"]}
    assert checks["tables_wellformed"] is False
    assert len(checks) == 1, "wellformedness short-circuits the rest"


def test_a_malformed_table_row_fails_loudly(repo):
    edit(repo, "SKILL.md", "| `analyze` | 11/18 |", "| `analyze` | 11/18 | extra |")
    result = repo.run("lint-skill")
    assert result.exit_code == EXIT_REFUSED
    assert result.data["checks"][0]["name"] == "tables_wellformed"
    assert result.data["checks"][0]["passed"] is False


def test_an_empty_table_never_yields_an_empty_default(repo):
    """The dangerous failure: silently parsing to nothing and failing open."""
    path = repo.skill_root / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(### PROGRESS_MAP\n\| phase \| progress \|\n\|---\|---\|\n)"
                  r"(\|[^\n]*\n)+", r"\1", text)
    path.write_text(text, encoding="utf-8")

    result = repo.run("lint-skill")
    assert result.exit_code == EXIT_REFUSED
    assert result.data["checks"][0]["passed"] is False
    assert "zero rows" in result.data["checks"][0]["message"]


# -- one rule at a time -----------------------------------------------------


def test_phase_set_mismatch_fires(repo):
    # A label only PHASE_LABEL_MAP carries — the human-readable phase table
    # near the top of SKILL.md repeats the shorter cells.
    edit(repo, "SKILL.md",
         "| `gate_analyze` | Gate 5: Analysis Approval |",
         "| `gate_analyse` | Gate 5: Analysis Approval |")
    checks = results(repo)
    assert checks["phase_set_matches_phase_label_map"] is False


def test_broken_next_phase_chain_fires(repo):
    edit(repo, "SKILL.md", "| `plan_draft` | `gate_plan` |",
         "| `plan_draft` | `implement` |")
    checks = results(repo)
    assert checks["next_phase_chains_sequence"] is False


def test_wrong_progress_denominator_fires(repo):
    edit(repo, "SKILL.md", "| `analyze` | 11/18 |", "| `analyze` | 11/19 |")
    assert_only_failure(repo, "progress_denominator_matches_phase_count")


def test_gate_missing_from_artifact_ownership_fires(repo):
    edit(repo, "SKILL.md",
         "| `gate_design` | `design/app/app-design.md` | static |", "")
    checks = results(repo)
    assert checks["gate_registered_gate_design"] is False


def test_gate_missing_from_state_template_fires(repo):
    path = repo.skill_root / "templates" / "state.json"
    template = json.loads(path.read_text(encoding="utf-8"))
    del template["approvals"]["gate_tasks"]
    path.write_text(json.dumps(template, indent=2), encoding="utf-8")
    checks = results(repo)
    assert checks["gate_registered_gate_tasks"] is False


def test_gate_missing_from_gate_to_execution_phase_fires(repo):
    edit(repo, "modules/gate-protocol.md",
         "| gate_security | security_review | SDLE-native (Phase 17 via "
         "`modules/security-review.md`) |", "")
    checks = results(repo)
    assert checks["gate_registered_gate_security"] is False


def test_a_second_state_template_fires(repo):
    path = repo.skill_root / "SKILL.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\n```json\n{\n  "workflow_version": "1.13"\n}\n```\n',
        encoding="utf-8",
    )
    assert_only_failure(repo, "single_state_template")


def test_version_drift_fires(repo):
    readme = repo.root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            "# SDLE — Spec Driven Lifecycle Engine (v1.13)",
            "# SDLE — Spec Driven Lifecycle Engine (v1.12)",
        ),
        encoding="utf-8",
    )
    assert_only_failure(repo, "version_string_consistent")


def test_a_state_field_without_a_migration_row_fires(repo):
    path = repo.skill_root / "templates" / "state.json"
    template = json.loads(path.read_text(encoding="utf-8"))
    template["brand_new_field"] = None
    path.write_text(json.dumps(template, indent=2), encoding="utf-8")
    assert_only_failure(repo, "migration_covers_every_state_field")


def test_a_reintroduced_powershell_cmdlet_fires(repo):
    path = repo.skill_root / "modules" / "phase-execution.md"
    path.write_text(
        path.read_text(encoding="utf-8")
        + '\nCompute the hash: `(Get-FileHash -Algorithm SHA256 "x").Hash`\n',
        encoding="utf-8",
    )
    assert_only_failure(repo, "no_powershell_only_cmdlets")


def test_a_hardcoded_progress_string_fires(repo):
    path = repo.skill_root / "modules" / "gate-protocol.md"
    path.write_text(
        path.read_text(encoding="utf-8") + "\nThe workflow is at phase 7/18 here.\n",
        encoding="utf-8",
    )
    assert_only_failure(repo, "no_hardcoded_progress_outside_progress_map")


def test_a_phase_without_an_execution_block_fires(repo):
    edit(repo, "modules/phase-execution.md",
         "**Phase 13 — `design_generation`:**", "**Phase 13 — design stuff:**")
    checks = results(repo)
    assert checks["every_phase_has_execution_block"] is False


def test_a_doc_missing_a_phase_fires(repo):
    readme = repo.root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace("design_generation", "xxx"),
        encoding="utf-8",
    )
    checks = results(repo)
    assert checks["doc_lists_every_phase_README"] is False
