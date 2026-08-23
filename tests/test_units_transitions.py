"""advance and gate approve/reject — where gate discipline is enforced."""

from __future__ import annotations

import pytest

EXIT_OK, EXIT_REFUSED = 0, 1


def at(project, phase: str, status: str = "pending", **extra):
    """Place the workflow at a phase without going through the machine."""
    state = project.state()
    state["current_phase"] = phase
    state["status"] = status
    state["progress"] = {
        "requirements_check": "1/18", "constitution_draft": "2/18",
        "gate_constitution": "3/18", "spec_draft": "4/18", "gate_spec": "5/18",
        "plan_draft": "6/18", "gate_plan": "7/18", "checklist_draft": "8/18",
        "tasks_draft": "9/18", "gate_tasks": "10/18", "analyze": "11/18",
        "gate_analyze": "12/18", "design_generation": "13/18",
        "gate_design": "14/18", "implement": "15/18", "gate_implement": "16/18",
        "security_review": "17/18", "gate_security": "18/18", "complete": "18/18",
    }[phase]
    state.update(extra)
    project.write_state(state)
    return state


# -- advance ----------------------------------------------------------------


def test_advance_follows_next_phase(started):
    result = started.ok("advance", "--to", "gate_constitution")
    assert result.data["from"] == "constitution_draft"
    assert result.data["to"] == "gate_constitution"
    assert result.data["progress"] == "3/18"


def test_advance_into_a_gate_awaits_approval(started):
    result = started.ok("advance", "--to", "gate_constitution")
    assert result.data["status"] == "awaiting_approval"


def test_advance_into_a_generation_phase_is_pending(started):
    at(started, "gate_constitution", "awaiting_approval",
       approvals={"gate_constitution": {"decision": "approved",
                                        "comments": None, "timestamp": "x"}})
    result = started.ok("advance", "--to", "spec_draft")
    assert result.data["status"] == "pending"


def test_advance_status_can_be_overridden(started):
    """`skip with warning` lands on a gate with status pending, not
    awaiting_approval — see dry-run 03."""
    at(started, "plan_draft", "failed")
    result = started.ok("advance", "--to", "gate_plan", "--status", "pending")
    assert result.data["status"] == "pending"


def test_advance_records_phase_history(started):
    started.ok("advance", "--to", "gate_constitution", "--outcome", "completed")
    history = started.state()["phase_history"]
    assert history[-1]["phase"] == "constitution_draft"
    assert history[-1]["outcome"] == "completed"


@pytest.mark.parametrize("target", ["implement", "gate_security", "tasks_draft"])
def test_advance_refuses_forward_jumps(started, target):
    result = started.run("advance", "--to", target)
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "forward_jump"
    assert started.state()["current_phase"] == "constitution_draft", "no mutation"


def test_advance_refuses_backwards(started):
    at(started, "plan_draft")
    result = started.run("advance", "--to", "spec_draft")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "forward_jump"


def test_advance_refuses_to_leave_an_unapproved_gate(started):
    at(started, "gate_constitution", "awaiting_approval")
    result = started.run("advance", "--to", "spec_draft")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "gate_not_approved"
    assert started.state()["current_phase"] == "gate_constitution"


def test_advance_refuses_to_leave_a_rejected_gate(started):
    at(started, "gate_constitution", "rejected",
       approvals={"gate_constitution": {"decision": "rejected",
                                        "comments": "no", "timestamp": "x"}})
    result = started.run("advance", "--to", "spec_draft")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "gate_not_approved"


def test_advance_refuses_unknown_phase(started):
    result = started.run("advance", "--to", "not_a_phase")
    assert result.exit_code == EXIT_REFUSED


# -- gate show --------------------------------------------------------------


def test_gate_show_reports_number_label_and_path(started):
    started.write_artifact(".specify/memory/constitution.md")
    at(started, "gate_constitution", "awaiting_approval")
    data = started.ok("gate", "show", "--gate", "gate_constitution").data
    assert data["gate_number"] == 1
    assert data["gate_total"] == 8
    assert data["label"] == "Gate 1: Constitution Approval"
    assert data["artifact_path"] == ".specify/memory/constitution.md"
    assert data["exists"] is True
    assert data["execution_phase"] == "constitution_draft"


def test_gate_show_reports_unresolved_feature_id(started):
    at(started, "gate_spec", "awaiting_approval")
    data = started.ok("gate", "show", "--gate", "gate_spec").data
    assert data["artifact_path"] is None
    assert "current_feature_id" in data["skipped_reason"]


def test_gate_show_substitutes_feature_id(started):
    at(started, "gate_spec", "awaiting_approval", current_feature_id="001-todo-api")
    data = started.ok("gate", "show", "--gate", "gate_spec").data
    assert data["artifact_path"] == ".specify/specs/001-todo-api/spec.md"


def test_gate_show_refuses_unknown_gate(started):
    result = started.run("gate", "show", "--gate", "gate_nope")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "unknown_gate"


# -- gate approve -----------------------------------------------------------


def test_gate_approve_records_baseline_and_advances(started):
    started.write_artifact(".specify/memory/constitution.md")
    at(started, "gate_constitution", "awaiting_approval")

    result = started.ok("gate", "approve", "--gate", "gate_constitution")
    state = started.state()

    assert result.data["next_phase"] == "spec_draft"
    assert state["approvals"]["gate_constitution"]["decision"] == "approved"
    assert state["artifact_shas"]["gate_constitution"] == result.data["sha"]
    assert state["current_phase"] == "spec_draft"
    assert state["status"] == "pending"


def test_gate_approve_stores_comments(started):
    started.write_artifact(".specify/memory/constitution.md")
    at(started, "gate_constitution", "awaiting_approval")
    started.ok("gate", "approve", "--gate", "gate_constitution",
               "--comments", "Add API versioning constraints")
    entry = started.state()["approvals"]["gate_constitution"]
    assert entry["comments"] == "Add API versioning constraints"


def test_gate_approve_refuses_when_not_at_that_gate(started):
    started.write_artifact(".specify/memory/constitution.md")
    result = started.run("gate", "approve", "--gate", "gate_constitution")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "not_at_gate"


def test_gate_approve_refuses_when_artifact_absent(started):
    at(started, "gate_constitution", "awaiting_approval")
    result = started.run("gate", "approve", "--gate", "gate_constitution")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "artifact_missing"
    assert started.state()["approvals"]["gate_constitution"] is None


def test_gate_approve_writes_audit_entry_with_decision(started):
    started.write_artifact(".specify/memory/constitution.md")
    at(started, "gate_constitution", "awaiting_approval")
    started.ok("gate", "approve", "--gate", "gate_constitution")
    text = started.audit_file.read_text(encoding="utf-8")
    assert "**Gate Decision:** APPROVED" in text
    assert started.ok("audit", "verify").data["matches"] is True


# -- gate reject ------------------------------------------------------------


def test_gate_reject_records_feedback_and_freezes(started):
    started.write_artifact(".specify/memory/constitution.md")
    at(started, "gate_constitution", "awaiting_approval")

    result = started.ok("gate", "reject", "--gate", "gate_constitution",
                        "--reason", "Too vague")
    state = started.state()

    assert state["approvals"]["gate_constitution"]["decision"] == "rejected"
    assert state["approvals"]["gate_constitution"]["comments"] == "Too vague"
    assert state["status"] == "rejected"
    assert state["current_phase"] == "gate_constitution", "rejection never advances"
    assert result.data["execution_phase"] == "constitution_draft"


def test_gate_reject_refuses_when_not_at_that_gate(started):
    result = started.run("gate", "reject", "--gate", "gate_plan", "--reason", "x")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "not_at_gate"


# -- final gate -------------------------------------------------------------


def test_final_gate_completes_the_workflow(started):
    started.write_artifact("reviews/security-review-2026-01-01-0900.md")
    at(started, "gate_security", "awaiting_approval",
       security_review_artifact="reviews/security-review-2026-01-01-0900.md")

    result = started.ok("gate", "approve", "--gate", "gate_security")
    state = started.state()

    assert state["current_phase"] == "complete"
    assert state["status"] == "completed"
    runtime_rel = started.runtime.relative_to(started.root).as_posix()
    assert result.data["completion_summary"] == (
        runtime_rel + "/completion-summary.json"
    )

    summary_file = started.runtime / "completion-summary.json"
    assert summary_file.is_file()
    import json
    summary = json.loads(summary_file.read_text(encoding="utf-8"))
    assert summary["all_gates_approved"] is True
    assert summary["workflow_version"] == "1.14"
