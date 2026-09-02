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
         "| `gate_analyze` | Gate {gate_number}: Analysis Approval |",
         "| `gate_analyse` | Gate {gate_number}: Analysis Approval |")
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
            "# SDLE — Spec Driven Lifecycle Engine (v1.16)",
            "# SDLE — Spec Driven Lifecycle Engine (v1.13)",
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


# -- the flow model ---------------------------------------------------------
#
# Each breakage below is chosen to trip exactly one flow rule. Where two rules
# would fire on the same edit the fixture picks the edit that isolates one:
# dropping `gate_implement` from ITERATIVE leaves the row an ordered subset, so
# the mandatory-phase rule fires alone.


def flow_row(repo: Project, name: str) -> str:
    """The FLOW_PHASES row for ``name``, read rather than restated."""
    text = (repo.skill_root / "SKILL.md").read_text(encoding="utf-8")
    prefix = f"| `{name}` | "
    for line in text.splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"no FLOW_PHASES row for {name}")


def test_a_renamed_flow_fires(repo):
    """The declared rows plus GREENFIELD must be exactly ENGINEERING_FLOWS."""
    edit(repo, "SKILL.md", "| `ITERATIVE` | ", "| `ITERATIVE_V2` | ")
    assert_only_failure(repo, "flow_table_covers_the_required_flows")


def test_declaring_greenfield_as_a_flow_row_fires(repo):
    """GREENFIELD has one home, and the editable table is not it.

    `ITERATIVE` is the row renamed rather than `BROWNFIELD_DISCOVERY`: as of
    T08 the latter is the only flow that names `discovery`, so renaming it
    would orphan a registry phase and trip a second rule. `ITERATIVE` names no
    registry phase of its own, so this edit isolates the coverage rule.
    """
    edit(repo, "SKILL.md", "| `ITERATIVE` | ", "| `GREENFIELD` | ")
    assert_only_failure(repo, "flow_table_covers_the_required_flows")


def test_a_flow_out_of_registry_order_fires(repo):
    row = flow_row(repo, "ITERATIVE")
    edit(repo, "SKILL.md", row,
         row.replace("analyze gate_analyze", "gate_analyze analyze"))
    assert_only_failure(repo, "every_flow_is_an_ordered_subset_of_the_registry")


def test_a_flow_naming_an_unknown_phase_fires(repo):
    row = flow_row(repo, "ITERATIVE")
    edit(repo, "SKILL.md", row, row.replace("analyze gate_analyze",
                                            "analyse gate_analyze"))
    assert_only_failure(repo, "every_flow_is_an_ordered_subset_of_the_registry")


def test_a_flow_dropping_a_mandatory_phase_fires(repo):
    """`gate_implement` is the governance floor, not a matter of taste."""
    row = flow_row(repo, "ITERATIVE")
    edit(repo, "SKILL.md", row,
         row.replace("implement gate_implement", "implement"))
    assert_only_failure(repo, "every_flow_retains_the_mandatory_phases")


def test_a_progress_value_that_is_not_the_greenfield_position_fires(repo):
    """PROGRESS_MAP is a derived view now, and its values are checked."""
    edit(repo, "SKILL.md", "| `analyze` | 11/18 |", "| `analyze` | 10/18 |")
    assert_only_failure(
        repo, "progress_map_and_gate_numbers_are_the_derived_greenfield_views")


def test_a_gate_number_column_that_is_not_the_greenfield_numbering_fires(repo):
    edit(repo, "SKILL.md", "| `gate_analyze` | `gate_analyze` | 5 |",
         "| `gate_analyze` | `gate_analyze` | 9 |")
    assert_only_failure(
        repo, "progress_map_and_gate_numbers_are_the_derived_greenfield_views")


def test_a_registry_phase_no_flow_names_fires(repo):
    """The replacement for the guarantee a derived GREENFIELD would have given.

    A phase added to the registry that no flow names must fail loudly rather
    than silently joining GREENFIELD. Other checks fire on the same planted row
    — a new registry phase has no NEXT_PHASE row, no label and no execution
    block — so this asserts its own check directly rather than in isolation.
    """
    edit(repo, "SKILL.md", "| 21 | `complete` |",
         "| 21 | `complete` |\n| 22 | `orphan_phase` |")
    checks = results(repo)
    assert checks["every_registry_phase_is_used_by_some_flow"] is False


def test_a_hardcoded_gate_ordinal_in_a_label_fires(repo):
    """The ordinal is flow-relative; re-hardcoding it is the regression."""
    edit(repo, "SKILL.md",
         "| `gate_analyze` | Gate {gate_number}: Analysis Approval |",
         "| `gate_analyze` | Gate 5: Analysis Approval |")
    assert_only_failure(repo, "gate_labels_are_flow_relative")


def test_a_block_ordinal_that_is_not_the_greenfield_position_fires(repo):
    """The 17 restated block ordinals are pinned for the first time."""
    edit(repo, "modules/phase-execution.md",
         "**Phase 13 — `design_generation`:**",
         "**Phase 12 — `design_generation`:**")
    assert_only_failure(
        repo, "execution_block_numbers_are_the_greenfield_positions")


def test_a_greenfield_block_that_drops_its_ordinal_fires(repo):
    """What pays for making the ordinal optional in the header pattern.

    A GREENFIELD phase may not quietly lose its number just because a phase
    outside GREENFIELD is allowed to have none.
    """
    edit(repo, "modules/phase-execution.md",
         "**Phase 13 — `design_generation`:**",
         "**Phase `design_generation`:**")
    assert_only_failure(
        repo, "execution_block_numbers_are_the_greenfield_positions")
# -- T08: the discovery phase's rules ---------------------------------------


def test_a_gate_registered_for_discovery_fires(repo):
    """N29. `discovery` is gateless by decision (ADR-005 D1).

    Registering a gate for it trips the gate-registration checks too — a new
    gate key has no ARTIFACT_OWNERSHIP row and no approvals key — so this
    asserts its own check directly rather than in isolation.
    """
    edit(repo, "SKILL.md", "| `gate_constitution` | `gate_constitution` | 1 |",
         "| `discovery` | `gate_discovery` | 1 |\n"
         "| `gate_constitution` | `gate_constitution` | 2 |")
    checks = results(repo)
    assert checks["discovery_is_gateless"] is False


def test_a_progress_map_row_for_discovery_fires(repo):
    """PROGRESS_MAP is GREENFIELD's view, and `discovery` is not in it."""
    edit(repo, "SKILL.md", "| `requirements_check` | 1/18 |",
         "| `requirements_check` | 1/18 |\n| `discovery` | 1/18 |")
    checks = results(repo)
    assert checks["discovery_is_gateless"] is False


def test_discovery_in_a_second_flow_fires(repo):
    """§14: discovery happens once. A second carrier contradicts that."""
    row = flow_row(repo, "ITERATIVE")
    edit(repo, "SKILL.md", row,
         row.replace("| requirements_check ", "| requirements_check discovery "))
    assert_only_failure(repo, "discovery_is_declared_by_exactly_one_flow")


def test_a_restated_discovery_category_id_fires(repo):
    """N29. The vocabulary has one home; a prompt file is not it."""
    from conftest import sdle
    needle = next(c for c in sdle.DISCOVERY_CATEGORIES if "_" in c)
    edit(repo, "modules/phase-execution.md",
         "- `sdle.sh discovery schema` —",
         f"- categories include `{needle}`. `sdle.sh discovery schema` —")
    assert_only_failure(
        repo, "discovery_vocabulary_is_not_restated_in_prompt_files")


def test_a_restated_classification_token_fires(repo):
    from conftest import sdle
    edit(repo, "modules/phase-execution.md",
         "- `sdle.sh discovery schema` —",
         f"- use `{sdle.DISCOVERY_CLASSIFICATIONS[0]}`. "
         "`sdle.sh discovery schema` —")
    assert_only_failure(
        repo, "discovery_vocabulary_is_not_restated_in_prompt_files")


def test_the_discovery_execution_block_may_not_carry_an_ordinal(repo):
    """N30. `discovery` has no GREENFIELD position, so it has no number."""
    edit(repo, "modules/phase-execution.md",
         "**Phase `discovery` (BROWNFIELD_DISCOVERY only",
         "**Phase 2 — `discovery` (BROWNFIELD_DISCOVERY only")
    assert_only_failure(
        repo, "execution_block_numbers_are_the_greenfield_positions")


def test_removing_the_discovery_execution_block_fires(repo):
    """N30's other half: the block has to exist at all."""
    edit(repo, "modules/phase-execution.md",
         "**Phase `discovery` (BROWNFIELD_DISCOVERY only",
         "**Repository discovery (BROWNFIELD_DISCOVERY only")
    assert_only_failure(repo, "every_phase_has_execution_block")


# -- the repository configuration boundary (T09/D15) ------------------------


def test_a_documented_config_default_that_drifts_fires(repo):
    """X12: the check T09 added has to be provable failable, like every other
    rule in this file. A README example that no longer matches
    `REPO_CONFIG_DEFAULTS` must fire, and fire alone."""
    readme = repo.root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            '"policyFormat": "json"', '"policyFormat": "yaml"'),
        encoding="utf-8",
    )
    assert_only_failure(repo, "repo_config_defaults_match_documentation")


def test_an_unparseable_documented_json_block_fires(repo):
    """A block that does not parse is a failure, not something to skip: a
    silently skipped block is how the rule would come to check nothing."""
    readme = repo.root / "README.md"
    readme.write_text(
        readme.read_text(encoding="utf-8").replace(
            '"configVersion": "1",', '"configVersion" "1",'),
        encoding="utf-8",
    )
    assert_only_failure(repo, "repo_config_defaults_match_documentation")


def test_deleting_the_documented_block_fires_rather_than_passing_vacuously(
        repo):
    """The rule's own non-vacuity guard: with nothing left to compare, the
    check must fail rather than report success over an empty set."""
    readme = repo.root / "README.md"
    text = readme.read_text(encoding="utf-8")
    # The configuration block specifically: README carries three ```json
    # blocks and the other two are unrelated examples.
    marker = text.index('"configVersion"')
    start = text.rindex("```json", 0, marker)
    end = text.index("```", marker) + 3
    readme.write_text(text[:start] + text[end:], encoding="utf-8")
    assert '"configVersion"' not in readme.read_text(encoding="utf-8")
    assert_only_failure(repo, "repo_config_defaults_match_documentation")


def test_a_project_with_no_repository_documentation_still_lints(repo):
    """The other half of the non-vacuity guard, and the reason it is not a
    relaxation. With neither document present there is no restatement that
    could drift, so the rule passes and says why — and `lint-skill` keeps
    answering in a project that carries no README, which
    `test_runtime_free_commands_need_no_workitem` requires of it."""
    (repo.root / "README.md").unlink()
    (repo.root / "docs" / "SDLE-Reference-Guide.md").unlink()

    result = repo.run("lint-skill")
    assert result.exit_code == EXIT_OK, result
    assert result.data["failed"] == []
    check = next(c for c in result.data["checks"]
                 if c["name"] == "repo_config_defaults_match_documentation")
    assert check["passed"] is True
    assert "no repository documentation" in check["message"]
