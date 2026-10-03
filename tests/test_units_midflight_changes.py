"""What the engine does when a bound requirements document changes mid-flight.

These pin the impact claims `docs/lifecycle` and GETTING-STARTED section 11c make about
the four things a person can do, each reproduced against the real engine rather than
argued. What the engine does NOT do - regenerate artifacts, decide whether a change is
additive or contradictory - is stated by the absence of an assertion, and in the docs.
"""

from __future__ import annotations

import json

from conftest import sdle
from test_integration_06_to_09 import at_gate_plan, review_for_gate

DOC = "requirements/todo-api.md"


def edit_requirements(project, line="Added rule: the service must log every write."):
    target = project.root / DOC
    target.write_text(target.read_text(encoding="utf-8") + "\n" + line + "\n",
                      encoding="utf-8", newline="\n")


def approvals(project):
    return {k: (v or {}).get("decision") for k, v in project.state()["approvals"].items()}


def test_an_edit_stops_the_next_progression_and_changes_nothing_already_approved(project):
    at_gate_plan(project)
    review_for_gate(project, "gate_plan")  # everything but the assessment is in order
    before = project.state()
    files_before = sorted(p.relative_to(project.root).as_posix()
                          for p in project.root.rglob("*.md") if "specs" in p.parts)
    edit_requirements(project)

    refused = project.run("gate", "approve", "--gate", "gate_plan")

    assert refused.reason == "governance_stale", refused
    after = project.state()
    assert approvals(project) == {k: (v or {}).get("decision")
                                  for k, v in before["approvals"].items()}
    assert after["phase_history"] == before["phase_history"]
    assert files_before == sorted(p.relative_to(project.root).as_posix()
                                  for p in project.root.rglob("*.md") if "specs" in p.parts)


def test_restart_works_while_stale_clears_downstream_approvals_and_keeps_every_file(project):
    at_gate_plan(project)
    edit_requirements(project)
    files_before = sorted(p.relative_to(project.root).as_posix()
                          for p in project.root.rglob("*") if p.is_file()
                          and ".git" not in p.parts)

    project.ok("restart", "--to", "8")
    project.ok("restart", "--to", "8", "--confirm")

    state = project.state()
    assert state["current_phase"] == "plan_draft"
    assert state["approvals"]["gate_spec"]["decision"] == "approved", "upstream approvals survive"
    assert state["approvals"]["gate_plan"] is None
    files_after = sorted(p.relative_to(project.root).as_posix()
                         for p in project.root.rglob("*") if p.is_file()
                         and ".git" not in p.parts)
    # nothing is deleted: regenerating the work is the orchestrator's job, not the engine's
    assert set(files_before) <= set(files_after)
    # and the stale assessment still stands until it is re-run
    assert project.run("advance", "--to", "gate_plan").reason == "governance_stale"


def test_reassessing_lets_the_same_workitem_carry_on_with_its_approvals_intact(project):
    at_gate_plan(project)
    review_for_gate(project, "gate_plan")
    edit_requirements(project)
    assert project.run("gate", "approve", "--gate", "gate_plan").reason == "governance_stale"

    project.record_governance()

    state = project.state()
    assert state["approvals"]["gate_spec"]["decision"] == "approved"
    assert project.run("gate", "approve", "--gate", "gate_plan").reason != "governance_stale"


def test_reset_deletes_state_and_audit_and_keeps_everything_else(project):
    at_gate_plan(project)
    paths = sdle.Paths(project_root=project.root, skill_root=project.skill_root,
                       workitem=project.workitem)
    sdle.write_refinement_record(paths, {
        "refinementVersion": sdle.REFINEMENT_RECORD_VERSION, "workitem": project.workitem,
        "status": "CANCELLED", "iterationCap": 1, "iterationCapSource": "builtin",
        "iterations": [], "startedAt": "2026-01-01T00:00:00Z",
        "endedAt": "2026-01-01T00:01:00Z"})
    project.ok("reset")
    project.ok("reset", "--confirm")

    names = {p.name for p in project.runtime.iterdir()}
    assert "state.json" not in names and "audit.md" not in names and "lock" not in names
    assert {"governance.json", "requirements.json", "evidence", "refinement.json"} <= names, names


def test_init_after_a_reset_with_changed_requirements_starts_and_the_first_move_is_refused(project):
    at_gate_plan(project)
    project.ok("reset")
    project.ok("reset", "--confirm")
    edit_requirements(project)

    started = project.run("init", session="again")
    assert started.exit_code == 0, started
    refused = project.run("advance", "--to", "gate_constitution")
    assert refused.reason == "governance_stale", refused


def test_a_completed_workitem_is_not_stopped_by_an_edit_but_reports_stale(project):
    at_gate_plan(project)
    state = project.state()
    state["current_phase"], state["status"] = "complete", "completed"
    project.write_state(state)
    edit_requirements(project)

    shown = project.ok("governance", "show")
    assert shown.data["fresh"] is False
    # no progression exists to refuse, and the approvals are untouched
    assert project.state()["approvals"]["gate_spec"]["decision"] == "approved"


def test_a_completed_workitem_does_not_block_a_later_refinement_of_the_same_document(project):
    at_gate_plan(project)
    state = project.state()
    state["current_phase"], state["status"] = "complete", "completed"
    project.write_state(state)
    paths = sdle.Paths(project_root=project.root, skill_root=project.skill_root,
                       workitem="someone-else")
    project.ok("workitem", "create", "--name", "Someone Else")
    project.pin = True
    project.as_workitem("someone-else").ok("requirements", "bind", "--source", DOC)
    del paths
    owner = sdle.Paths(project_root=project.root, skill_root=project.skill_root,
                       workitem=project.workitem)
    other_view = sdle.dataclass_replace(owner, workitem="someone-else")
    assert sdle.refinement_sharers(other_view, [DOC]) == {}, "a finished WorkItem is not a sharer"


def test_a_completed_workitem_can_be_rolled_back_and_keeps_its_earlier_approvals(project):
    at_gate_plan(project)
    state = project.state()
    state["current_phase"], state["status"] = "complete", "completed"
    project.write_state(state)

    project.ok("restart", "--to", "8")
    project.ok("restart", "--to", "8", "--confirm")

    after = project.state()
    assert after["current_phase"] == "plan_draft" and after["status"] == "pending"
    assert after["approvals"]["gate_spec"]["decision"] == "approved"
    assert after["approvals"]["gate_plan"] is None
