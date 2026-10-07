"""A gate approves only on a review of the kind it names, and a review can
carry structured findings (ADR-017, R2): AS-13 and the findings contract.

`review_type_mismatch` is the one R2 refusal that applies to every WorkItem,
so these tests run on the ordinary fixture, not a package.
"""
from __future__ import annotations

import json

import pytest

from conftest import PASSING_TEST_COMMAND, sdle
from test_units_artifact_review import frozen, review_for_gate
from test_units_flow_model import drive, edit_skill
from test_units_implementation_evidence import at_implement

EXIT_REFUSED = 1


def record_review(view, gate, type_, result="PASS", actor="test", **extra):
    shown = view.ok("gate", "show", "--gate", gate).data
    args = ["artifact", "review", "--path", shown["artifact_path"],
            "--type", type_, "--result", result, "--actor-type", actor,
            "--actor-name", "suite"]
    for flag, value in extra.items():
        args += [f"--{flag}", value]
    return view.run(*args)


def at_gate(project, gate):
    drive(project, "GREENFIELD", stop=gate)
    return project


def test_as13_a_design_gate_will_not_take_a_content_review(project):
    at_gate(project, "gate_design")
    assert record_review(project, "gate_design", "content-review").exit_code == 0
    before = frozen(project)
    result = project.run("gate", "approve", "--gate", "gate_design")
    assert result.reason == "review_type_mismatch"
    assert result.data["accepted_types"] == ["design-review"]
    assert result.data["recorded"] == [{"type": "content-review",
                                        "actor": "test"}]
    assert frozen(project) == before


def test_the_right_kind_of_review_lets_the_gate_through(project):
    at_gate(project, "gate_design")
    record_review(project, "gate_design", "content-review")
    record_review(project, "gate_design", "design-review")
    assert project.run("gate", "approve", "--gate",
                       "gate_design").exit_code == 0


def test_a_later_review_of_another_kind_does_not_displace_the_right_one(
        project):
    at_gate(project, "gate_design")
    record_review(project, "gate_design", "design-review")
    record_review(project, "gate_design", "content-review", result="FAIL")
    assert project.run("gate", "approve", "--gate",
                       "gate_design").exit_code == 0


def test_the_newest_review_of_the_right_kind_decides(project):
    at_gate(project, "gate_design")
    record_review(project, "gate_design", "design-review")
    record_review(project, "gate_design", "design-review", result="FAIL")
    assert project.run("gate", "approve", "--gate",
                       "gate_design").reason == "review_failed"


def test_a_review_of_the_right_kind_for_old_content_is_stale_not_a_mismatch(
        project):
    at_gate(project, "gate_design")
    record_review(project, "gate_design", "design-review")
    design = project.root / "design" / "app" / "app-design.md"
    design.write_text(design.read_text(encoding="utf-8") + "\nedited\n",
                      encoding="utf-8")
    assert project.run("gate", "approve", "--gate",
                       "gate_design").reason == "review_stale"


def test_no_review_at_all_is_still_review_missing(project):
    at_gate(project, "gate_design")
    assert project.run("gate", "approve", "--gate",
                       "gate_design").reason == "review_missing"


def test_the_implementation_gate_wants_a_code_review(git_project):
    at_implement(git_project)
    git_project.ok("manifest", "build", "--test-command",
                   PASSING_TEST_COMMAND)
    git_project.ok("advance", "--to", "gate_implement")
    record_review(git_project, "gate_implement", "design-review")
    refused = git_project.run("gate", "approve", "--gate", "gate_implement")
    assert refused.reason == "review_type_mismatch"
    assert refused.data["accepted_types"] == ["code-review"]
    record_review(git_project, "gate_implement", "code-review")
    assert git_project.run("gate", "approve", "--gate",
                           "gate_implement").exit_code == 0


def test_an_unconstrained_gate_still_takes_any_review(project):
    at_gate(project, "gate_spec")
    assert record_review(project, "gate_spec", "anything-at-all").exit_code == 0
    assert project.run("gate", "approve", "--gate",
                       "gate_spec").exit_code == 0


def test_the_actor_type_can_be_constrained_by_the_table(project):
    edit_skill(project, "| `gate_spec` | any | any |",
               "| `gate_spec` | any | human |")
    at_gate(project, "gate_spec")
    record_review(project, "gate_spec", "content-review", actor="agent")
    refused = project.run("gate", "approve", "--gate", "gate_spec")
    assert refused.reason == "review_type_mismatch"
    assert refused.data["accepted_actors"] == ["human"]
    record_review(project, "gate_spec", "content-review", actor="human")
    assert project.run("gate", "approve", "--gate",
                       "gate_spec").exit_code == 0


def test_drift_re_approval_applies_the_same_rule(project):
    at_gate(project, "gate_design")
    record_review(project, "gate_design", "design-review")
    assert project.run("gate", "approve", "--gate",
                       "gate_design").exit_code == 0
    design = project.root / "design" / "app" / "app-design.md"
    design.write_text(design.read_text(encoding="utf-8") + "\nedited\n",
                      encoding="utf-8")
    project.ok("drift", "check", "--queue")
    record_review(project, "gate_design", "content-review")
    assert project.run("gate", "approve", "--gate",
                       "gate_design").reason == "review_type_mismatch"


def test_the_table_is_linted_for_every_gate(project):
    edit_skill(project, "| `gate_security` | any | any |\n", "")
    result = project.run("lint-skill")
    failed = {c["name"] for c in result.data["checks"] if not c["passed"]}
    assert "gate_registered_gate_security" in failed


def test_the_table_cannot_name_an_unknown_actor_type(project):
    edit_skill(project, "| `gate_spec` | any | any |",
               "| `gate_spec` | any | wizard |")
    result = project.run("lint-skill")
    failed = {c["name"] for c in result.data["checks"] if not c["passed"]}
    assert "gate_review_types_are_well_formed" in failed


# ---- structured findings --------------------------------------------------------


def findings_file(project, rows, name="findings.json"):
    path = project.root / name
    path.write_text(json.dumps({"findings": rows}), encoding="utf-8")
    return name


def finding(identifier="F1", severity="blocking", disposition="open",
            obligations=("AC-001",), location="app.py:12"):
    return {"id": identifier, "severity": severity,
            "disposition": disposition, "location": location,
            "obligations": list(obligations)}


def test_a_pass_is_refused_while_a_blocking_finding_is_open(project):
    at_gate(project, "gate_spec")
    name = findings_file(project, [finding()])
    before = frozen(project)
    reviews_before = json.loads((project.runtime / "reviews.json").read_text(
        encoding="utf-8"))["reviews"]
    result = record_review(project, "gate_spec", "content-review",
                           findings=name)
    assert result.reason == "review_findings_open"
    assert result.data["open_blocking"] == ["F1"]
    assert frozen(project) == before
    assert json.loads((project.runtime / "reviews.json").read_text(
        encoding="utf-8"))["reviews"] == reviews_before, "nothing recorded"


def test_a_fail_may_carry_open_blocking_findings(project):
    at_gate(project, "gate_spec")
    name = findings_file(project, [finding()])
    result = record_review(project, "gate_spec", "content-review",
                           result="FAIL", findings=name)
    assert result.exit_code == 0
    reviews = json.loads((project.runtime / "reviews.json").read_text(
        encoding="utf-8"))["reviews"]
    assert reviews[-1]["findings"] == {"total": 1, "blocking": 1, "open": 1}


def test_resolved_blocking_and_advisory_findings_do_not_stop_a_pass(project):
    at_gate(project, "gate_spec")
    name = findings_file(project, [
        finding("F1", disposition="resolved"),
        finding("F2", severity="advisory", obligations=())])
    assert record_review(project, "gate_spec", "content-review",
                         findings=name).exit_code == 0
    last = json.loads((project.runtime / "reviews.json").read_text(
        encoding="utf-8"))["reviews"][-1]
    stored = json.loads((project.root / last["evidenceId"]).read_text(
        encoding="utf-8"))
    assert [f["id"] for f in stored["findings"]] == ["F1", "F2"]


@pytest.mark.parametrize("bad", [
    [{"id": "F1"}],
    [finding(severity="critical")],
    [finding(disposition="maybe")],
    [dict(finding(), obligations="AC-001")],
    [finding(location="")],
    [finding("F1"), finding("F1")],
    "not a list",
])
def test_malformed_findings_are_a_usage_error_and_record_nothing(project, bad):
    at_gate(project, "gate_spec")
    path = project.root / "bad.json"
    path.write_text(json.dumps({"findings": bad}), encoding="utf-8")
    before = frozen(project)
    result = record_review(project, "gate_spec", "content-review",
                           findings="bad.json")
    assert result.exit_code == 2
    assert result.reason == "review_findings_invalid"
    assert frozen(project) == before
