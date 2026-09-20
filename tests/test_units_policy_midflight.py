"""What an omission records about the policy it rested on (F-024, D-04).

The requirements for a gate are derived from the repository policy at decision
time, not read back from what was true when the WorkItem started. So the
evidence an omission leaves has to name the policy that was actually in force,
or a reader cannot tell which rules the omission rested on.

This file pins that recorded fact. It does not assert that a policy edited
between `init` and a gate decision is harmless: whether it should be is an
open owner decision (D-04), and asserting either answer here would decide it.
"""

from __future__ import annotations

import hashlib

from test_units_gate_policy import review_for_gate, walk
from test_units_governance import policy_file, write_policy


def sha256_of(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_an_omission_under_a_repository_policy_records_that_policys_sha(
        git_project):
    """A tightening policy that still leaves design omittable at LOW. The
    omission entry must carry the sha of that exact file."""
    write_policy(git_project, {"risk_thresholds": {"HIGH": 4}})
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")

    omitted = git_project.ok("gate", "omit", "--gate", "gate_design")

    entry = git_project.state()["approvals"]["gate_design"]
    assert omitted.data["decision"] == "omitted_by_policy"
    assert entry["policy_sha256"] == sha256_of(policy_file(git_project))


def test_an_omission_under_the_built_in_policy_records_no_file_sha(git_project):
    """With no override file the built-in applies, and there is no file whose
    hash could be recorded."""
    assert not policy_file(git_project).exists()
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")

    git_project.ok("gate", "omit", "--gate", "gate_design")

    assert git_project.state()["approvals"]["gate_design"][
        "policy_sha256"] is None


def test_a_refusal_names_the_policy_that_required_the_gate(git_project):
    """The refusal carries the source and sha of the live policy, so the reader
    can see it was the repository override, not the built-in, that required it."""
    import copy
    from test_units_governance import BUILTIN
    tight = copy.deepcopy(BUILTIN["required_gates_by_risk"])
    tight["LOW"] = ["gate_design"]
    write_policy(git_project, {"required_gates_by_risk": tight})
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")

    refused = git_project.run("gate", "omit", "--gate", "gate_design")

    assert refused.reason == "gate_required", refused
    assert refused.data["policy"]["sha256"] == sha256_of(policy_file(git_project))
    assert refused.data["policy"]["source"].endswith("governance-policy.json")
