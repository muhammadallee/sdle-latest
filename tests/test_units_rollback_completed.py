"""A WorkItem that really completed can be rolled back and completed again.

The earlier mid-flight tests planted a completed state. This one drives a real run through
the CLI to `complete`, changes a bound requirement, rolls back with the recorded approach,
and drives the rest again - so the recovery path the docs describe is a path that works,
including the repository baseline a completed run establishes.
"""

from __future__ import annotations

import json

import pytest

from conftest import sdle
from test_integration_06_to_09 import review_for_gate
from test_units_flow_model import FEATURE, constants_of, drive, prepare

DOC = "requirements/todo-api.md"


def redrive(project, flow, from_phase):
    """Walk the flow again from ``from_phase`` (the phase a rollback returned to) to the end."""
    consts = constants_of(project)
    phases = list(consts.flow(flow).phases)
    feature_dir = project.feature_dir(FEATURE)
    for index in range(phases.index(from_phase), len(phases) - 1):
        phase = phases[index]
        prepare(project, phase, feature_dir)
        gate_key = consts.phase_to_gate_key.get(phase)
        if gate_key:
            review_for_gate(project, gate_key)
            project.ok("gate", "approve", "--gate", gate_key)
        else:
            project.ok("advance", "--to", phases[index + 1])


@pytest.mark.parametrize("flow, back_to", [
    ("HOTFIX", "spec_draft"),
    ("GREENFIELD", "plan_draft"),
])
def test_a_completed_run_rolls_back_and_completes_again(git_project, flow, back_to):
    project = git_project
    consts = constants_of(project)
    declared = consts.flow(flow)
    drive(project, flow)
    assert project.state()["current_phase"] == "complete"
    first_approvals = {k: v["decision"] for k, v in project.state()["approvals"].items() if v}
    baseline_file = project.root / ".sdle" / "baseline.json"
    had_baseline = baseline_file.exists()
    if flow == "GREENFIELD":
        assert had_baseline, "a completed GREENFIELD run establishes the baseline"

    target = declared.index(back_to)
    target_gate_keys = [consts.phase_to_gate_key[p] for p in declared.gate_phases
                        if declared.index(p) >= target]

    # the requirements change after completion
    requirement = project.root / DOC
    requirement.write_text(requirement.read_text(encoding="utf-8")
                           + "\nAdded rule: the service must log every write.\n",
                           encoding="utf-8", newline="\n")
    shown = project.ok("governance", "show")
    assert shown.data["fresh"] is False
    assert shown.data["change_facts"]["workitem"]["currentPhase"] == "complete"
    offered = {c["phase"] for c in shown.data["change_facts"]["workitem"]["restartCandidates"]}
    assert back_to in offered, "a completed WorkItem offers the phases it could return to"

    project.ok("restart", "--to", str(target), "--approach", "update")
    project.ok("restart", "--to", str(target), "--confirm", "--approach", "update")
    rolled = project.state()
    assert rolled["current_phase"] == back_to and rolled["status"] == "pending"
    for key in target_gate_keys:
        assert rolled["approvals"][key] is None, key
    audit = (project.runtime / "audit.md").read_text(encoding="utf-8")
    assert "Approach: update" in audit

    # the rollback does not refresh the assessment; the person re-assesses, then redoes the phases
    assert project.ok("governance", "show").data["fresh"] is False
    project.record_governance(classification={"type": "enhancement", "flow": flow})
    redrive(project, flow, back_to)

    final = project.state()
    assert final["current_phase"] == "complete" and final["status"] == "completed"
    again = {k: v["decision"] for k, v in final["approvals"].items() if v}
    assert again == first_approvals, "every approval was given again by a human gate"
    verify = project.ok("audit", "verify")
    assert verify.data["matches"] is True and verify.data["chain_ok"] is True
    assert (project.root / ".sdle" / "baseline.json").exists() == had_baseline
    if had_baseline:
        baseline = json.loads(baseline_file.read_text(encoding="utf-8"))
        assert baseline["supersedes"] is not None, "the second completion supersedes the first"
