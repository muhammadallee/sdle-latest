"""D01 (SDLE-DEFECT-STABILIZATION-01) — a gate approves specific content or
nothing.

Before this iteration `cmd_gate_approve` resolved the gate's artifact through
`resolve_artifact_path` and, when a placeholder such as
`{speckit_feature_directory}` or `{security_review_artifact}` was still unset,
received `(None, reason)` and approved anyway — with `sha: null`. The review
precondition and the Spec Kit containment check both returned early on an
unresolved path, so nothing stood in the way. `_approve_drift` and
`cmd_gate_omit` had the same hole.

Every case asserts the refusal leaves the facts a refusal must not touch —
phase, status, approvals, baselines and the ledger bytes — exactly as they
were (`frozen`, shared with the review regime's own tests).
"""

from __future__ import annotations

import pytest

from conftest import sdle
from test_units_artifact_review import frozen, review_for_gate
from test_units_flow_model import ALL_FLOWS, FEATURE, bind, constants_of, drive

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3


def at_gate_spec_without_resolution(project, flow: str) -> None:
    """Stand at `gate_spec` with a spec on disk but no feature binding."""
    drive(project, flow, stop="spec_draft")
    project.write_artifact(project.feature_dir(FEATURE) + "/spec.md")
    assert project.state()["specKit"]["featureDirectory"] is None
    project.ok("advance", "--to", "gate_spec")


@pytest.mark.parametrize("flow", ALL_FLOWS)
def test_d01_a_null_feature_reference_refuses_approval(git_project, flow):
    at_gate_spec_without_resolution(git_project, flow)
    before = frozen(git_project)

    result = git_project.run("gate", "approve", "--gate", "gate_spec")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "artifact_unresolved", result
    assert result.data["binding"] == "speckit_feature_directory"
    assert "feature resolve" in result.envelope["message"]
    assert frozen(git_project) == before
    assert git_project.state()["approvals"]["gate_spec"] is None


def test_d01_two_candidate_features_refuse_as_ambiguous(git_project):
    at_gate_spec_without_resolution(git_project, "GREENFIELD")
    git_project.write_artifact(
        git_project.feature_dir("002-other") + "/spec.md")
    before = frozen(git_project)

    result = git_project.run("gate", "approve", "--gate", "gate_spec")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "feature_ambiguous", result
    assert sorted(result.data["candidates"]) == [FEATURE, "002-other"]
    assert frozen(git_project) == before


@pytest.mark.parametrize("flow", ALL_FLOWS)
def test_d01_an_unresolved_security_review_refuses_approval(git_project, flow):
    """`gate_security`'s artifact exists only once `security-review begin`
    has named it; standing at the gate without that is not approvable."""
    drive(git_project, flow, stop="security_review")
    git_project.ok("advance", "--to", "gate_security")
    assert git_project.state()["security_review_artifact"] is None
    before = frozen(git_project)

    result = git_project.run("gate", "approve", "--gate", "gate_security")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "artifact_unresolved", result
    assert result.data["binding"] == "security_review_artifact"
    assert "security-review begin" in result.envelope["message"]
    assert frozen(git_project) == before
    assert git_project.state()["current_phase"] == "gate_security"


def test_d01_a_deleted_artifact_refuses_approval(git_project):
    drive(git_project, "GREENFIELD", stop="plan_draft")
    git_project.write_artifact(git_project.feature_dir(FEATURE) + "/plan.md")
    git_project.ok("advance", "--to", "gate_plan")
    review_for_gate(git_project, "gate_plan")
    (git_project.root / git_project.feature_dir(FEATURE) / "plan.md").unlink()
    before = frozen(git_project)

    result = git_project.run("gate", "approve", "--gate", "gate_plan")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "artifact_missing", result
    assert frozen(git_project) == before


def test_d01_an_unhashable_artifact_refuses_without_mutation(
        git_project, monkeypatch):
    drive(git_project, "GREENFIELD", stop="plan_draft")
    git_project.write_artifact(git_project.feature_dir(FEATURE) + "/plan.md")
    git_project.ok("advance", "--to", "gate_plan")
    review_for_gate(git_project, "gate_plan")
    before = frozen(git_project)

    real = sdle.sha256_file

    def unreadable(path):
        if path.name == "plan.md":
            raise PermissionError(13, "Permission denied", str(path))
        return real(path)

    monkeypatch.setattr(sdle, "sha256_file", unreadable)
    result = git_project.run("gate", "approve", "--gate", "gate_plan")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "artifact_unreadable", result
    assert frozen(git_project) == before


@pytest.mark.parametrize("result_kind, expected", [
    ("FAIL", "review_failed"), ("stale", "review_stale")])
def test_d01_an_invalid_review_keeps_its_existing_refusal(
        git_project, result_kind, expected):
    drive(git_project, "GREENFIELD", stop="plan_draft")
    plan = git_project.feature_dir(FEATURE) + "/plan.md"
    git_project.write_artifact(plan)
    git_project.ok("advance", "--to", "gate_plan")
    if result_kind == "FAIL":
        review_for_gate(git_project, "gate_plan", result="FAIL")
    else:
        review_for_gate(git_project, "gate_plan")
        git_project.write_artifact(plan, "# plan\n\n" + "changed body. " * 20)
    before = frozen(git_project)

    result = git_project.run("gate", "approve", "--gate", "gate_plan")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == expected, result
    assert frozen(git_project) == before


def test_d01_drift_reapproval_of_a_deleted_artifact_refuses(git_project):
    """The drift path used to re-approve with `sha: null` when the drifted
    artifact had gone, silently re-baselining onto nothing."""
    drive(git_project, "GREENFIELD", stop="plan_draft")
    constitution = git_project.root / ".specify" / "memory" / "constitution.md"
    constitution.write_text("# Constitution\n\n" + "edited. " * 30,
                            encoding="utf-8")
    git_project.ok("drift", "check", "--queue")
    assert git_project.state()["drift_queue"] == ["gate_constitution"]
    constitution.unlink()
    before = frozen(git_project)

    result = git_project.run("gate", "approve", "--gate", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "artifact_missing", result
    assert frozen(git_project) == before


def test_d01_an_omission_of_an_unhashable_artifact_refuses(
        git_project, monkeypatch):
    """`gate omit` is the third way to leave a gate, and it fingerprints the
    artifact exactly as an approval does, so it shares the precondition."""
    drive(git_project, "GREENFIELD", stop="gate_design")
    assert git_project.state()["current_phase"] == "gate_design"
    dispositions = {d["gate"]: d["disposition"] for d in
                    git_project.ok("governance", "gates").data["dispositions"]}
    assert dispositions["gate_design"] == "omittable", dispositions
    review_for_gate(git_project, "gate_design")
    before = frozen(git_project)

    real = sdle.sha256_file

    def unreadable(path):
        if path.name == "app-design.md":
            raise PermissionError(13, "Permission denied", str(path))
        return real(path)

    monkeypatch.setattr(sdle, "sha256_file", unreadable)
    result = git_project.run("gate", "omit", "--gate", "gate_design")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "artifact_unreadable", result
    assert frozen(git_project) == before


def test_d01_a_valid_uniquely_resolved_artifact_still_approves(git_project):
    drive(git_project, "GREENFIELD", stop="plan_draft")
    git_project.write_artifact(git_project.feature_dir(FEATURE) + "/plan.md")
    git_project.ok("advance", "--to", "gate_plan")
    review_for_gate(git_project, "gate_plan")

    result = git_project.ok("gate", "approve", "--gate", "gate_plan")

    assert result.data["sha"], result
    assert git_project.state()["artifact_shas"]["gate_plan"] == result.data["sha"]


def test_d01_a_flow_without_the_constitution_needs_no_constitution(
        git_project):
    """ITERATIVE omits `constitution_draft`/`gate_constitution` and inherits
    the repository baseline instead. Nothing here may demand a constitution
    artifact for it: the flow completes on the baseline alone."""
    assert "gate_constitution" not in constants_of(git_project).flow(
        "ITERATIVE").phases
    assert not (git_project.root / ".specify" / "memory"
                / "constitution.md").exists()
    drive(git_project, "ITERATIVE")
    state = git_project.state()
    assert state["current_phase"] == "complete"
    assert state["approvals"]["gate_constitution"] is None
