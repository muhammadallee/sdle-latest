"""Which other WorkItems share a requirements document.

A binding held by another WorkItem counts unless that WorkItem's own current,
supported, consistent state proves it complete. Pre-init, reset, failed, rejected and
every active status count, because the registry records identity and not lifecycle.
Anything unreadable fails closed, naming the WorkItem.
"""

from __future__ import annotations

import json

import pytest

from conftest import sdle

DOC = "requirements/todo-api.md"


def paths_of(project):
    return sdle.Paths(project_root=project.root, skill_root=project.skill_root,
                      workitem=project.workitem)


def other(project, name="Other", bind=DOC):
    project.ok("workitem", "create", "--name", name)
    view = project.as_workitem(name.lower())
    if bind:
        view.ok("requirements", "bind", "--source", bind)
    return view


def set_state(view, **fields):
    view.runtime.mkdir(parents=True, exist_ok=True)
    state = sdle.load_template(sdle.Paths(
        project_root=view.root, skill_root=view.skill_root, workitem=view.workitem))
    state.update({"workflow_version": sdle.CURRENT_VERSION,
                  "current_phase": "constitution_draft", "status": "in_progress"})
    state.update(fields)
    view.state_file.write_text(json.dumps(state), encoding="utf-8")


def sharers(project, documents=(DOC,)):
    return sdle.refinement_sharers(paths_of(project), list(documents))


def test_a_document_bound_only_here_has_no_sharers(project):
    assert sharers(project) == {}


def test_a_pre_init_sharer_does_not_block_but_is_reported_as_affected(project):
    other(project)
    assert sharers(project) == {}
    report = sdle.refinement_sharer_report(paths_of(project), [DOC])
    assert report == {"blocking": {}, "affected": {DOC: ["other"]}}


@pytest.mark.parametrize("fields", [
    {"status": "in_progress"}, {"status": "pending"}, {"status": "awaiting_approval"},
    {"status": "awaiting_reapproval"}, {"status": "rejected"}, {"status": "failed"},
    {"current_phase": "complete", "status": "failed"},
    {"current_phase": "implementation", "status": "completed"},
])
def test_every_state_that_does_not_prove_completion_counts(project, fields):
    set_state(other(project), **fields)
    assert sharers(project) == {DOC: ["other"]}


def test_a_completed_sharer_does_not_count(project):
    set_state(other(project), current_phase="complete", status="completed")
    assert sharers(project) == {}


def test_a_reset_sharer_is_dormant_like_one_that_never_started(project):
    view = other(project)
    set_state(view, current_phase="complete", status="completed")
    view.state_file.unlink()
    assert sharers(project) == {}
    assert sdle.refinement_sharer_report(paths_of(project), [DOC])["affected"] == {DOC: ["other"]}


def write_loop(view, status):
    paths = sdle.Paths(project_root=view.root, skill_root=view.skill_root, workitem=view.workitem)
    h = "a" * 64
    iteration = {"iteration": 1, "assessmentRef": "x", "contentDigest": h, "proposalDigest": h,
                 "failingChecks": ["scope"], "findings": [], "questions": [], "edits": [],
                 "outcome": None if status in ("IN_PROGRESS", "AWAITING_REASSESSMENT") else "stall",
                 "disputeOutcomes": []}
    if status == "AWAITING_REASSESSMENT":
        iteration["edits"] = [{"id": "e1", "op": "append_section", "path": DOC, "anchor": None,
                               "text": "## A", "baseSha256": h, "appliedSha256": h,
                               "appliedOrder": 1, "autoApplied": False, "decision": "accepted"}]
    active = status in ("IN_PROGRESS", "AWAITING_REASSESSMENT")
    sdle.write_refinement_record(paths, {
        "refinementVersion": sdle.REFINEMENT_RECORD_VERSION, "workitem": view.workitem,
        "status": status, "iterationCap": 3, "iterationCapSource": "builtin",
        "iterations": [iteration], "startedAt": "2026-01-01T00:00:00Z",
        "endedAt": None if active else "2026-01-02T00:00:00Z"})


@pytest.mark.parametrize("status", ["IN_PROGRESS", "AWAITING_REASSESSMENT"])
def test_a_dormant_sharer_with_an_open_loop_still_blocks(project, status):
    write_loop(other(project), status)
    assert sharers(project) == {DOC: ["other"]}


@pytest.mark.parametrize("status", ["CANCELLED", "ESCALATED"])
def test_a_dormant_sharer_whose_loop_ended_does_not_block(project, status):
    write_loop(other(project), status)
    assert sharers(project) == {}


def test_an_unreadable_loop_record_of_a_dormant_sharer_fails_closed(project):
    view = other(project)
    (view.runtime / "refinement.json").write_text("not json", encoding="utf-8")
    with pytest.raises(sdle.IntegrityError) as raised:
        sharers(project)
    assert raised.value.reason == "refinement_registry_invalid"
    assert "other" in str(raised.value)


def test_a_completed_sharer_is_neither_blocking_nor_affected(project):
    set_state(other(project), current_phase="complete", status="completed")
    assert sdle.refinement_sharer_report(paths_of(project), [DOC]) == {
        "blocking": {}, "affected": {}}


def test_a_sharer_without_a_binding_is_harmless(project):
    other(project, bind=None)
    assert sharers(project) == {}


def test_a_different_document_is_not_shared(project):
    (project.root / "requirements" / "extra.md").write_text("# Extra\n", encoding="utf-8")
    other(project, bind="requirements/extra.md")
    assert sharers(project) == {}


def test_paths_compare_without_regard_to_case(project):
    set_state(other(project))
    assert sharers(project, ["Requirements/TODO-API.md"]) == {
        "Requirements/TODO-API.md": ["other"]}


def test_this_workitem_never_counts_as_its_own_sharer(project):
    assert sdle.refinement_sharers(paths_of(project), [DOC]) == {}


def test_every_sharer_is_listed_in_order(project):
    set_state(other(project, "Bravo"))
    set_state(other(project, "Alpha"))
    assert sharers(project) == {DOC: ["alpha", "bravo"]}


@pytest.mark.parametrize("state", [
    "not json", "[]", "{}", '{"workflow_version": "0", "current_phase": "complete", "status": "completed"}',
    '{"workflow_version": "%s", "current_phase": 3, "status": "completed"}' % "CURRENT",
])
def test_an_unreadable_or_unsupported_state_fails_closed_naming_the_workitem(project, state):
    view = other(project)
    view.runtime.mkdir(parents=True, exist_ok=True)
    view.state_file.write_text(state.replace("CURRENT", sdle.CURRENT_VERSION), encoding="utf-8")
    with pytest.raises(sdle.IntegrityError) as raised:
        sharers(project)
    assert raised.value.reason == "refinement_registry_invalid"
    assert "other" in str(raised.value)


def test_a_corrupt_binding_fails_closed_naming_the_workitem(project):
    view = other(project)
    view.runtime.joinpath("requirements.json").write_text("not json", encoding="utf-8")
    with pytest.raises(sdle.IntegrityError) as raised:
        sharers(project)
    assert raised.value.reason == "refinement_registry_invalid"
    assert "other" in str(raised.value)
