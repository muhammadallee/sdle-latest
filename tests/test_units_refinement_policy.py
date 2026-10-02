"""The one policy field refinement adds: how many iterations a loop may take."""

from __future__ import annotations

import json

import pytest

from conftest import sdle


def write_policy(project, document):
    target = project.root / ".sdle" / "policies" / "governance-policy.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(document), encoding="utf-8", newline="\n")


def test_the_builtin_cap_is_the_engine_maximum():
    assert sdle.GOVERNANCE_POLICY_BUILTIN["refinement_iteration_cap"] == (
        sdle.REFINEMENT_ITERATION_CAP_MAX)
    assert "refinement_iteration_cap" in sdle.GOVERNANCE_POLICY_OVERRIDABLE


def test_a_repository_may_lower_the_cap(bare_project):
    write_policy(bare_project, {"refinement_iteration_cap": 2})
    result = bare_project.ok("governance", "policy")
    assert result.data["policy"]["refinement_iteration_cap"] == 2


def test_the_effective_cap_defaults_to_the_maximum(bare_project):
    result = bare_project.ok("governance", "policy")
    assert result.data["policy"]["refinement_iteration_cap"] == sdle.REFINEMENT_ITERATION_CAP_MAX


@pytest.mark.parametrize("value", [0, -1, 4, 99, "3", 2.0, True, None, [2]])
def test_a_cap_outside_one_to_the_maximum_or_not_an_integer_is_malformed(bare_project, value):
    write_policy(bare_project, {"refinement_iteration_cap": value})
    result = bare_project.run("governance", "policy")
    assert result.exit_code == 1
    assert result.reason == "policy_malformed"
