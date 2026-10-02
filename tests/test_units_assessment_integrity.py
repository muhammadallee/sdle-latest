"""Assessment integrity: one content, one verdict.

A check that FAILed at a content must not later read PASS at the same content. The
refusal fires before anything is written to `governance.json`, which stays
byte-identical, because progression is authorised from that record alone.
"""

from __future__ import annotations

import json

import pytest

from conftest import sdle

EXIT_REFUSED = sdle.EXIT_REFUSED
EXIT_INTEGRITY = sdle.EXIT_INTEGRITY

CHECK = "scope"
OTHER = "out_of_scope"


def quality(**results):
    out = {name: {"result": "PASS", "finding": None}
           for name in sdle.GOVERNANCE_POLICY_BUILTIN["quality_checks"]}
    for name, result in results.items():
        out[name] = {"result": result,
                     "finding": "no boundary stated" if result == "FAIL" else None}
    return out


def requirement_files(project):
    return sorted((project.root / "requirements").glob("*.md"))


def gov_bytes(project):
    return (project.runtime / "governance.json").read_bytes()


def evidence_kinds(project):
    out = []
    for path in sorted((project.runtime / "evidence").glob("governance-*.json")):
        if path.stat().st_size:
            out.append(json.loads(path.read_text(encoding="utf-8"))["kind"])
    return out


def run_assess(project, **results):
    document = {
        "governanceInputVersion": "1",
        "quality": quality(**results),
        "classification": {"type": "enhancement", "flow": "GREENFIELD"},
        "risk": {"signals": [], "proposedLevel": "LOW", "uncertainty": "LOW"},
    }
    target = project.root / "governance-input.json"
    target.write_text(json.dumps(document), encoding="utf-8", newline="\n")
    try:
        return project.run("governance", "assess", "--input", "governance-input.json")
    finally:
        target.unlink()


def first_requirement(project):
    return requirement_files(project)[0]


def test_a_fail_then_a_pass_at_the_same_content_is_refused(project):
    blocked = run_assess(project, **{CHECK: "FAIL"})
    assert blocked.exit_code == EXIT_REFUSED
    before = gov_bytes(project)

    flip = run_assess(project)
    assert flip.exit_code == EXIT_REFUSED
    assert flip.reason == "quality_verdict_flip"
    assert flip.data["flipped"] == [CHECK]
    assert gov_bytes(project) == before, "a refused flip must not touch the record"


def test_the_refused_flip_cannot_unlock_progression(project):
    run_assess(project, **{CHECK: "FAIL"})
    run_assess(project)
    shown = project.ok("governance", "show")
    checks = {c["id"]: c["result"] for c in shown.data["record"]["quality"]["checks"]}
    assert checks[CHECK] == "FAIL"
    assert project.run("advance").exit_code != 0


def test_the_attempt_is_recorded_as_evidence_that_is_not_history(project):
    run_assess(project, **{CHECK: "FAIL"})
    run_assess(project)
    attempts = list((project.runtime / "evidence").glob("governance-flip-attempt-*.json"))
    assert len(attempts) == 1
    doc = json.loads(attempts[0].read_text(encoding="utf-8"))
    assert doc["kind"] == "governance-flip-attempt" and doc["status"] == "REFUSED"
    assert doc["flippedChecks"] == [CHECK]
    # a third assessment that is still honest is not blocked by the attempt
    again = run_assess(project, **{CHECK: "FAIL"})
    assert again.reason == "requirements_quality_blocked"


def test_a_substantive_change_lets_the_check_pass(project):
    run_assess(project, **{CHECK: "FAIL"})
    target = first_requirement(project)
    target.write_text(target.read_text(encoding="utf-8")
                      + "\nThe service must reject unknown fields with status 400.\n",
                      encoding="utf-8", newline="\n")
    assert run_assess(project).exit_code == 0


def test_a_presentation_only_change_does_not_unlock_the_flip(project):
    run_assess(project, **{CHECK: "FAIL"})
    target = first_requirement(project)
    text = target.read_text(encoding="utf-8")
    target.write_text(text.replace("\n", "\r\n") + "\r\n\r\n\r\n", encoding="utf-8", newline="")
    flip = run_assess(project)
    assert flip.reason == "quality_verdict_flip"


def test_not_applicable_after_a_fail_is_the_same_flip(project):
    run_assess(project, nfrs="FAIL")
    flip = run_assess(project, nfrs="NOT_APPLICABLE")
    assert flip.reason == "quality_verdict_flip"


def test_a_fail_at_other_content_does_not_count(project):
    run_assess(project, **{CHECK: "FAIL"})
    target = first_requirement(project)
    target.write_text(target.read_text(encoding="utf-8") + "\nAnother rule: must log.\n",
                      encoding="utf-8", newline="\n")
    run_assess(project)  # passes at the new content
    # back to the old content: the FAIL at the OLD content is still history there
    original = target.read_text(encoding="utf-8").replace("\nAnother rule: must log.\n", "")
    target.write_text(original, encoding="utf-8", newline="\n")
    assert run_assess(project).reason == "quality_verdict_flip"


def test_a_pass_then_a_fail_is_never_refused(project):
    assert run_assess(project).exit_code == 0
    assert run_assess(project, **{CHECK: "FAIL"}).reason == "requirements_quality_blocked"


# -- the history is read strictly --------------------------------------------------------------


def test_an_unreadable_assessment_evidence_file_is_an_integrity_failure(project):
    run_assess(project, **{CHECK: "FAIL"})
    (project.runtime / "evidence" / "governance-broken.json").write_text(
        "not json", encoding="utf-8")
    result = run_assess(project)
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "governance_history_invalid"


@pytest.mark.parametrize("payload", ["[]", "{}", '{"kind": "governance", "record": 3}',
                                     '{"kind": "governance", "record": {"quality": {"checks": [1]}}}'])
def test_a_malformed_assessment_evidence_file_is_never_skipped(project, payload):
    run_assess(project, **{CHECK: "FAIL"})
    (project.runtime / "evidence" / "governance-bad.json").write_text(payload, encoding="utf-8")
    assert run_assess(project).reason == "governance_history_invalid"


def test_an_empty_placeholder_is_not_evidence_and_not_corruption(project):
    run_assess(project, **{CHECK: "FAIL"})
    (project.runtime / "evidence" / "governance-claimed.json").write_text("", encoding="utf-8")
    assert run_assess(project).reason == "quality_verdict_flip"


def test_other_kinds_of_evidence_are_not_history(project):
    (project.runtime / "evidence").mkdir(parents=True, exist_ok=True)
    (project.runtime / "evidence" / "governance-other.json").write_text(
        json.dumps({"kind": "something-else"}), encoding="utf-8")
    assert run_assess(project).exit_code == 0


# -- legacy records and the current record as the last entry -----------------------------------------


def strip_content_digest(project):
    for path in [project.runtime / "governance.json",
                 *(project.runtime / "evidence").glob("governance-*.json")]:
        if not path.stat().st_size:
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        record = doc.get("record", doc)
        record["requirements"].pop("contentDigest", None)
        path.write_text(json.dumps(doc), encoding="utf-8")


def test_a_legacy_record_over_identical_bytes_still_counts(project):
    run_assess(project, **{CHECK: "FAIL"})
    strip_content_digest(project)
    assert run_assess(project).reason == "quality_verdict_flip"


def test_a_legacy_record_over_other_bytes_is_unknown_and_does_not_block(project):
    run_assess(project, **{CHECK: "FAIL"})
    strip_content_digest(project)
    target = first_requirement(project)
    target.write_text(target.read_text(encoding="utf-8") + "\nThe service must log.\n",
                      encoding="utf-8", newline="\n")
    assert run_assess(project).exit_code == 0


def test_the_current_record_counts_even_without_its_evidence(project):
    run_assess(project, **{CHECK: "FAIL"})
    for path in (project.runtime / "evidence").glob("governance-*.json"):
        path.unlink()
    assert run_assess(project).reason == "quality_verdict_flip"


def test_both_digests_are_written_to_the_record_and_the_evidence(project):
    run_assess(project)
    record = json.loads((project.runtime / "governance.json").read_text(encoding="utf-8"))
    assert len(record["requirements"]["contentDigest"]) == 64
    evidence = [json.loads(p.read_text(encoding="utf-8"))
                for p in (project.runtime / "evidence").glob("governance-*.json")
                if p.stat().st_size]
    assert evidence[0]["record"]["requirements"]["contentDigest"] == \
        record["requirements"]["contentDigest"]


# -- a recorded dispute exempts exactly its pair ---------------------------------------------------------


def write_dispute(project, check, digest):
    paths = sdle.Paths(project_root=project.root, skill_root=project.skill_root,
                       workitem=project.workitem)
    h = "b" * 64
    sdle.write_refinement_record(paths, {
        "refinementVersion": sdle.REFINEMENT_RECORD_VERSION, "workitem": project.workitem,
        "status": "PASSED", "iterationCap": 1, "iterationCapSource": "builtin",
        "iterations": [{
            "iteration": 1, "contentDigest": digest, "proposalDigest": h,
            "failingChecks": [], "findings": [], "questions": [], "edits": [],
            "outcome": "progress",
            "disputeOutcomes": [{
                "checkId": check, "outcome": "overturned_by_dispute", "originalResult": "FAIL",
                "evidenceRef": "evidence/x.json", "decisionRef": "audit:1", "contentDigest": digest}]}],
        "startedAt": "2026-01-01T00:00:00Z", "endedAt": "2026-01-01T00:01:00Z"})


def current_content_digest(project):
    return json.loads((project.runtime / "governance.json").read_text(
        encoding="utf-8"))["requirements"]["contentDigest"]


def test_an_overturned_pair_is_exempt_and_only_that_pair(project):
    run_assess(project, **{CHECK: "FAIL", OTHER: "FAIL"})
    digest = current_content_digest(project)
    write_dispute(project, CHECK, digest)
    flip = run_assess(project)
    assert flip.reason == "quality_verdict_flip"
    assert flip.data["flipped"] == [OTHER]
    ok = run_assess(project, **{OTHER: "FAIL"})
    assert ok.reason == "requirements_quality_blocked"


def test_a_dispute_at_another_content_exempts_nothing(project):
    run_assess(project, **{CHECK: "FAIL"})
    write_dispute(project, CHECK, "c" * 64)
    assert run_assess(project).reason == "quality_verdict_flip"


# -- the assessor agent ---------------------------------------------------------------------------------


def test_the_requirements_assessor_is_picked_up_by_the_agent_checks():
    """lint-skill's agent glob must find the fifth agent; it is proven here, not
    assumed from the glob's shape."""
    paths = sdle.resolve_paths(str(sdle.Path(__file__).resolve().parent.parent), None)
    names = [p.name for p in sdle.product_agent_files(paths)]
    assert "sdle-requirements-review.md" in names


def test_the_assessor_restates_no_check_id_and_no_definition():
    body = (sdle.Path(__file__).resolve().parent.parent / ".claude" / "agents"
            / "sdle-requirements-review.md").read_text(encoding="utf-8")
    flat = " ".join(body.split())
    for check, text in sdle.QUALITY_CHECK_DEFINITIONS.items():
        assert f"`{check}`" not in body, check
        assert " ".join(text.split()) not in flat, check
