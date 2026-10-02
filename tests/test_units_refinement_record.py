"""The requirements-refinement record and the lint-evidence shape.

The record is engine-written, WorkItem-owned and strictly validated: a record that
would not read back never reaches disk, and one that does not validate is an integrity
failure, never an absence.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from conftest import sdle

H = "a" * 64
CHECK = next(iter(sdle.QUALITY_CHECK_DEFINITIONS))


def good_record() -> dict:
    return {
        "refinementVersion": sdle.REFINEMENT_RECORD_VERSION,
        "workitem": "wi-1",
        "status": "IN_PROGRESS",
        "iterationCap": 2,
        "iterationCapSource": "builtin",
        "iterations": [{
            "iteration": 1,
            "contentDigest": H,
            "proposalDigest": H,
            "failingChecks": [CHECK],
            "findings": [{"checkId": CHECK, "text": "no problem statement"}],
            "questions": [{"id": "q1", "text": "Who uses it?",
                           "options": ["staff", "public"], "answer": None}],
            "edits": [{"op": "append_section", "path": "requirements/a.md",
                       "anchor": None, "baseSha256": H, "autoApplied": False,
                       "decision": None}],
            "outcome": None,
            "disputeOutcomes": [],
        }],
        "startedAt": "2026-01-01T00:00:00Z",
        "endedAt": None,
    }


def check(doc, workitem="wi-1"):
    return sdle.validate_refinement_record(doc, "workitems/wi-1/.sdle/refinement.json", workitem)


def refused(doc, workitem="wi-1"):
    with pytest.raises(sdle.IntegrityError) as caught:
        check(doc, workitem)
    assert caught.value.reason == "refinement_record_invalid"
    return str(caught.value)


def test_a_well_formed_record_validates():
    assert check(good_record())["status"] == "IN_PROGRESS"


def test_the_iteration_cap_has_one_engine_ceiling():
    assert sdle.REFINEMENT_ITERATION_CAP_MAX == 3
    doc = good_record()
    doc["iterationCap"] = 3
    check(doc)
    doc["iterationCap"] = 4
    refused(doc)
    for bad in (0, True, "2", None):
        doc["iterationCap"] = bad
        refused(doc)


@pytest.mark.parametrize("mutate", [
    lambda d: d.update(extra=1),
    lambda d: d.pop("startedAt"),
    lambda d: d.update(refinementVersion="2"),
    lambda d: d.update(status="DONE"),
    lambda d: d.update(workitem=""),
    lambda d: d.update(iterationCapSource="guess"),
    lambda d: d.update(endedAt="2026-01-02T00:00:00Z"),          # active but ended
    lambda d: d.update(status="PASSED"),                        # finished but no endedAt
    lambda d: d.update(iterations={}),
    lambda d: d["iterations"].append(copy.deepcopy(d["iterations"][0])),   # beyond the cap? 2 ok; numbering wrong
    lambda d: d["iterations"][0].update(iteration=2),
    lambda d: d["iterations"][0].update(contentDigest="xyz"),
    lambda d: d["iterations"][0].update(failingChecks=["not_a_check"]),
    lambda d: d["iterations"][0].update(failingChecks=[CHECK, CHECK]),
    lambda d: d["iterations"][0]["findings"][0].update(checkId="nope"),
    lambda d: d["iterations"][0].update(questions=[d["iterations"][0]["questions"][0]] * 6),
    lambda d: d["iterations"][0]["questions"][0].pop("answer"),
    lambda d: d["iterations"][0]["edits"][0].update(op="delete"),
    lambda d: d["iterations"][0]["edits"][0].update(autoApplied="yes"),
    lambda d: d["iterations"][0]["edits"][0].update(decision="maybe"),
    lambda d: d["iterations"][0].update(outcome="great"),
    lambda d: d["iterations"][0].update(disputeOutcomes=[{
        "checkId": CHECK, "outcome": "overturned_by_dispute", "originalResult": "PASS",
        "evidenceRef": "e", "decisionRef": "d", "contentDigest": H}]),
])
def test_a_record_the_engine_would_not_write_is_refused(mutate):
    doc = good_record()
    mutate(doc)
    refused(doc)


def test_a_record_for_another_workitem_is_refused():
    assert "wi-2" in refused(good_record(), workitem="wi-2")


def test_a_finished_record_needs_an_end_time():
    doc = good_record()
    doc["status"] = "ESCALATED"
    doc["endedAt"] = "2026-01-02T00:00:00Z"
    check(doc)


def test_a_valid_dispute_outcome_validates():
    doc = good_record()
    doc["iterations"][0]["disputeOutcomes"] = [{
        "checkId": CHECK, "outcome": "overturned_by_dispute", "originalResult": "FAIL",
        "evidenceRef": "evidence/x.json", "decisionRef": "audit:12", "contentDigest": H}]
    check(doc)


# -- the reader and the one writer ---------------------------------------------------------------


def bound(project):
    return sdle.Paths(project_root=Path(project.root), skill_root=Path(sdle.__file__).parent.parent
                      / ".claude" / "skills" / "sdle", workitem=project.workitem)


def test_no_record_reads_as_none_and_a_written_one_reads_back(project):
    paths = bound(project)
    assert sdle.read_refinement_record(paths) is None
    doc = good_record()
    doc["workitem"] = paths.workitem
    relative = sdle.write_refinement_record(paths, doc)
    assert relative.endswith("/.sdle/refinement.json")
    assert sdle.read_refinement_record(paths) == doc


def test_the_writer_refuses_an_invalid_record_and_writes_nothing(project):
    paths = bound(project)
    doc = good_record()
    doc["workitem"] = paths.workitem
    doc["status"] = "bogus"
    with pytest.raises(sdle.IntegrityError):
        sdle.write_refinement_record(paths, doc)
    assert not paths.refinement_file.exists()


@pytest.mark.parametrize("text", ["not json", "[]", "{}", "null"])
def test_a_corrupt_file_is_an_integrity_failure_never_an_absence(project, text):
    paths = bound(project)
    paths.refinement_file.write_text(text, encoding="utf-8")
    with pytest.raises(sdle.IntegrityError) as caught:
        sdle.read_refinement_record(paths)
    assert caught.value.reason == "refinement_record_invalid"


def test_the_record_lives_beside_the_workitems_other_runtime_files(project):
    paths = bound(project)
    assert paths.refinement_file == paths.runtime / "refinement.json"
    names = sdle.workitem_runtime_member_names(paths)
    assert "refinement.json" in names and "scan-acknowledgements.json" in names


# -- lint evidence: advisory, never enforced --------------------------------------------------


def good_evidence() -> dict:
    return {"kind": "refinement-lint", "executionId": "x1", "documentSha256": H,
            "findings": [{"ruleId": "r1", "mappedCheck": CHECK, "floorEligible": True,
                          "floorEnforced": False, "line": 3, "text": "vague"}]}


def test_good_lint_evidence_has_no_problems():
    assert sdle.refinement_lint_evidence_problems(good_evidence()) == []


@pytest.mark.parametrize("mutate", [
    lambda d: d["findings"][0].update(floorEnforced=True),
    lambda d: d["findings"][0].pop("floorEnforced"),
    lambda d: d["findings"][0].update(mappedCheck="nope"),
    lambda d: d["findings"][0].update(line=0),
    lambda d: d["findings"][0].update(floorEligible="yes"),
    lambda d: d.update(kind="other"),
    lambda d: d.update(documentSha256="short"),
    lambda d: d.update(extra=1),
    lambda d: d.update(findings="none"),
])
def test_lint_evidence_that_claims_enforcement_or_is_malformed_is_flagged(mutate):
    doc = good_evidence()
    mutate(doc)
    assert sdle.refinement_lint_evidence_problems(doc)
    assert sdle.refinement_lint_evidence_problems(json.loads(json.dumps(doc)))
