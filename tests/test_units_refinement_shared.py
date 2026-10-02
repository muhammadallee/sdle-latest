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
    state = {"workflow_version": sdle.CURRENT_VERSION, "current_phase": "constitution_draft",
             "status": "in_progress"}
    state.update(fields)
    view.state_file.write_text(json.dumps(state), encoding="utf-8")


def sharers(project, documents=(DOC,)):
    return sdle.refinement_sharers(paths_of(project), list(documents))


def test_a_document_bound_only_here_has_no_sharers(project):
    assert sharers(project) == {}


def test_a_pre_init_sharer_counts(project):
    other(project)
    assert sharers(project) == {DOC: ["other"]}


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


def test_a_reset_sharer_counts_because_its_binding_survives_the_reset(project):
    view = other(project)
    set_state(view, current_phase="complete", status="completed")
    view.state_file.unlink()
    assert sharers(project) == {DOC: ["other"]}


def test_a_sharer_without_a_binding_is_harmless(project):
    other(project, bind=None)
    assert sharers(project) == {}


def test_a_different_document_is_not_shared(project):
    (project.root / "requirements" / "extra.md").write_text("# Extra\n", encoding="utf-8")
    other(project, bind="requirements/extra.md")
    assert sharers(project) == {}


def test_paths_compare_without_regard_to_case(project):
    other(project)
    assert sharers(project, ["Requirements/TODO-API.md"]) == {
        "Requirements/TODO-API.md": ["other"]}


def test_this_workitem_never_counts_as_its_own_sharer(project):
    assert sdle.refinement_sharers(paths_of(project), [DOC]) == {}


def test_every_sharer_is_listed_in_order(project):
    other(project, "Bravo")
    other(project, "Alpha")
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
