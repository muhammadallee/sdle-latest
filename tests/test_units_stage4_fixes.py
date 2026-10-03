"""Fixes for the Stage 4 adversarial review.

Each test names the scenario that was found. Findings the implementation deliberately
does not act on are recorded with their reasons in the ledger, not here.
"""

from __future__ import annotations

import ast
import inspect
import json
import os

import pytest

from conftest import sdle
from test_units_refinement_commands import (
    CHECK, DOC, accept, apply, assess, blocked, call, edit, entered, other, proposal,
    record, sha, text_of)


def paths_of(project):
    return sdle.Paths(project_root=project.root, skill_root=project.skill_root,
                      workitem=project.workitem)


# -- 1. assessments are serialised ---------------------------------------------------------


def test_an_assessment_takes_the_repository_mutex(project):
    lock = project.root / "workitems" / ".refinement-transaction.lock"
    lock.write_text("held", encoding="utf-8")
    result = assess(project, CHECK)
    assert result.reason == "refinement_transaction_locked", result
    assert not (project.runtime / "governance.json").exists()
    assert lock.read_text(encoding="utf-8") == "held"


# -- 2. path spelling is not content ---------------------------------------------------------


def test_the_content_digest_ignores_the_case_of_a_path():
    one = {"requirements/Spec.md": b"# S\n\nThe service must log.\n"}
    two = {"Requirements/SPEC.md": b"# S\n\nThe service must log.\n"}
    assert sdle.requirements_content_digest(one) == sdle.requirements_content_digest(two)


# -- 5. a record is checked for meaning, not only shape ---------------------------------------


H = "a" * 64


def base_record(status="IN_PROGRESS", **over):
    doc = {
        "refinementVersion": sdle.REFINEMENT_RECORD_VERSION, "workitem": "wi-1",
        "status": status, "iterationCap": 3, "iterationCapSource": "builtin",
        "iterations": [{
            "iteration": 1, "assessmentRef": "x", "contentDigest": H, "proposalDigest": H,
            "failingChecks": [CHECK], "findings": [], "questions": [], "edits": [],
            "outcome": None, "disputeOutcomes": []}],
        "startedAt": "2026-01-01T00:00:00Z", "endedAt": None}
    doc.update(over)
    return doc


def invalid(doc):
    with pytest.raises(sdle.IntegrityError) as caught:
        sdle.validate_refinement_record(doc, "r.json", "wi-1")
    assert caught.value.reason == "refinement_record_invalid"


def test_passed_needs_a_last_iteration_that_made_progress():
    doc = base_record("PASSED", endedAt="2026-01-02T00:00:00Z")
    invalid(doc)
    doc["iterations"][0]["outcome"] = "progress"
    sdle.validate_refinement_record(doc, "r.json", "wi-1")


def test_passed_with_no_iterations_is_refused():
    invalid(base_record("PASSED", endedAt="2026-01-02T00:00:00Z", iterations=[]))


def test_an_active_loop_has_an_open_last_iteration_and_an_awaiting_one_has_an_applied_edit():
    doc = base_record("AWAITING_REASSESSMENT")
    invalid(doc)
    doc = base_record()
    doc["iterations"][0]["outcome"] = "progress"
    invalid(doc)


def test_an_unproven_dispute_outcome_exempts_nothing(project):
    entered(project)
    forged = record(project)
    forged["iterations"][0]["disputeOutcomes"] = [{
        "checkId": CHECK, "outcome": "overturned_by_dispute", "originalResult": "FAIL",
        "evidenceRef": "evidence/nothing.json", "decisionRef": "made up", "contentDigest": H}]
    sdle.write_refinement_record(paths_of(project), forged)
    assert sdle.overturned_assessment_results(paths_of(project)) == set()


# -- 6. sharers are judged on fully valid files ---------------------------------------------------


def test_a_minimal_forged_completed_state_does_not_exclude_a_sharer(project):
    view = other(project)
    view.runtime.mkdir(parents=True, exist_ok=True)
    view.state_file.write_text(json.dumps({
        "workflow_version": sdle.CURRENT_VERSION, "current_phase": "complete",
        "status": "completed"}), encoding="utf-8")
    with pytest.raises(sdle.IntegrityError) as caught:
        sdle.refinement_sharers(paths_of(project), [DOC])
    assert caught.value.reason == "refinement_registry_invalid"


@pytest.mark.parametrize("mutate", [
    lambda b: b.update(sources=[1]),
    lambda b: b.update(primary="requirements/other.md"),
    lambda b: b.update(digest="0" * 64),
])
def test_a_structurally_wrong_binding_fails_closed(project, mutate):
    view = other(project)
    binding = json.loads((view.runtime / "requirements.json").read_text(encoding="utf-8"))
    mutate(binding)
    (view.runtime / "requirements.json").write_text(json.dumps(binding), encoding="utf-8")
    with pytest.raises(sdle.IntegrityError) as caught:
        sdle.refinement_sharers(paths_of(project), [DOC])
    assert caught.value.reason == "refinement_registry_invalid"


# -- 7. architecture apply holds the mutex across its recheck --------------------------------------


def test_architecture_apply_takes_the_refinement_mutex(project, monkeypatch):
    paths = paths_of(project)
    monkeypatch.setattr(sdle, "REFINEMENT_LOCK_TIMEOUT", 0.2)
    paths.refinement_lock_file.write_text("held", encoding="utf-8")
    with pytest.raises(sdle.Refused) as raised:
        sdle.architecture_apply(paths, {"decisionId": "AP-x"}, sdle.now_iso())
    assert raised.value.reason == "refinement_transaction_locked"


# -- 8. a lock is released only by its holder ---------------------------------------------------------


def test_a_holder_never_releases_a_lock_that_is_no_longer_its_own(tmp_path):
    lock = tmp_path / "x.lock"
    with sdle.exclusive_file_lock(lock, 1.0, 60.0, 0.01, lambda: sdle.Refused("t", "t")):
        lock.write_text("someone else's token", encoding="utf-8")  # broken and retaken
    assert lock.read_text(encoding="utf-8") == "someone else's token"


def test_a_holder_releases_its_own_lock(tmp_path):
    lock = tmp_path / "x.lock"
    with sdle.exclusive_file_lock(lock, 1.0, 60.0, 0.01, lambda: sdle.Refused("t", "t")):
        assert lock.exists()
    assert not lock.exists()


# -- 9. raw markup is never layout -------------------------------------------------------------------------


@pytest.mark.parametrize("before, after", [
    ("<pre>A  B</pre>", "<pre>A B</pre>"),
    ("<pre>\nA  B\n</pre>", "<pre>\nA B\n</pre>"),
    ("<div>a  b</div>", "<div>a b</div>"),
])
def test_a_change_inside_raw_html_is_not_neutral(before, after):
    assert sdle.requirements_normal_form(before) != sdle.requirements_normal_form(after)


# -- 10. only the latest applied edit is the head of the chain ----------------------------------------------


def test_an_earlier_applied_text_is_not_a_valid_base_for_a_later_edit(project):
    target = project.root / DOC
    target.write_text(text_of(project) + "\nFirst line.\n\nSecond line.\n\nThird line.\n",
                      encoding="utf-8", newline="\n")
    entered(project, edits=[
        edit(project, "e1", "insert_after", "First line.", "\nA."),
        edit(project, "e2", "insert_after", "Second line.", "\nB."),
        edit(project, "e3", "insert_after", "Third line.", "\nC.")])
    for ident in ("e1", "e2", "e3"):
        accept(project, ident)
    assert apply(project, "e1").exit_code == 0
    after_first = text_of(project)
    assert apply(project, "e2").exit_code == 0
    target.write_text(after_first, encoding="utf-8", newline="\n")  # an outside revert to e1's text
    result = apply(project, "e3")
    assert result.reason == "refinement_edit_stale_base", result


# -- 13. an evidence reference has one spelling ----------------------------------------------------------------


def test_an_aliased_spelling_of_the_same_evidence_is_a_replay(project):
    from test_units_refinement_commands import dispute_payload, two_attempts
    first, second = two_attempts(project)
    assert call(project, "dispute", dispute_payload(project, first)).exit_code == 0
    folder, name = first.rsplit("/", 1)
    aliased = f"{folder}/./{name}"
    result = call(project, "dispute", dispute_payload(
        project, aliased, checkId="scope", decisionRef="a different decision"))
    assert result.reason in ("refinement_dispute_replayed", "refinement_dispute_incomplete"), result
    stored = record(project)["iterations"][-1]["disputeOutcomes"]
    assert [d["evidenceRef"] for d in stored] == [first], "one canonical spelling is stored"


# -- 14. lint: a quoted literal is not a marker; isolation is checked through helpers ------------------------------


def test_a_quoted_marker_literal_is_not_unresolved():
    text = ('# S\n\n## Acceptance\n- AC-1: A request with the header value "TODO" returns 400.\n\n'
            "## Out of Scope\nNone.\n")
    findings = sdle.requirements_lint({"a.md": text}, "a.md", "x")["findings"]
    assert "unresolved_marker" not in {f["ruleId"] for f in findings}


def test_nothing_the_assessment_path_calls_can_reach_the_lint():
    tree = ast.parse(inspect.getsource(sdle))
    functions = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}

    def callees(name):
        return {c.func.id for c in ast.walk(functions[name])
                if isinstance(c, ast.Call) and isinstance(c.func, ast.Name)
                and c.func.id in functions}

    seen, frontier = set(), ["cmd_governance_assess", "governance_precondition",
                             "evaluate_quality", "governance_freshness"]
    while frontier:
        name = frontier.pop()
        if name in seen:
            continue
        seen.add(name)
        frontier.extend(callees(name))
    assert "requirements_lint" not in seen
    assert "_refinement_lint_evidence" not in seen
    assert len(seen) > 10, "the walk must reach real code"
