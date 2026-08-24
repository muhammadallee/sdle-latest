"""Integration 01 — derived from docs/dry-runs/01-happy-path.md.

Fresh project -> 18 phases -> 8 gate approvals -> complete.

SpecKit is not invoked. Each generation step is simulated by writing a
plausible artifact; what is asserted is the sequence of state values, the
approvals and baselines they produce, and the audit chain staying intact
throughout.
"""

from __future__ import annotations

import json

FEATURE = "001-todo-api"

# The traversal the transcript records, in order.
EXPECTED_TRAVERSAL = [
    "requirements_check", "constitution_draft", "gate_constitution",
    "spec_draft", "gate_spec", "plan_draft", "gate_plan",
    "checklist_draft", "tasks_draft", "gate_tasks", "analyze", "gate_analyze",
    "design_generation", "gate_design", "implement", "gate_implement",
    "security_review", "gate_security", "complete",
]

GATES = [
    "gate_constitution", "gate_spec", "gate_plan", "gate_tasks",
    "gate_analyze", "gate_design", "gate_implement", "gate_security",
]


def run_happy_path(project) -> list[str]:
    """Drive the whole workflow, returning every phase state passed through."""
    # v1.15: Spec Kit's WorkItem artifacts live under the WorkItem, so the
    # feature directory comes from the project this helper was handed —
    # test_units_workitem_runtime drives a second WorkItem through it.
    feature_dir = project.feature_dir(FEATURE)
    seen: list[str] = []

    def note():
        seen.append(project.state()["current_phase"])

    project.ok("init", session="happy")
    seen.append("requirements_check")
    note()  # constitution_draft

    # Phase 2 -> Gate 1
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution")
    note()
    project.ok("gate", "approve", "--gate", "gate_constitution")
    note()  # spec_draft

    # Phase 4 -> Gate 2 (feature id resolved from the specs directory)
    project.write_artifact(f"{feature_dir}/spec.md")
    project.ok("feature", "resolve")
    project.ok("advance", "--to", "gate_spec")
    note()
    project.ok("gate", "approve", "--gate", "gate_spec",
               "--comments", "Add rate limiting to the API constraints.")
    note()  # plan_draft

    # Phase 6 -> Gate 3
    project.write_artifact(f"{feature_dir}/plan.md")
    project.ok("advance", "--to", "gate_plan")
    note()
    project.ok("gate", "approve", "--gate", "gate_plan")
    note()  # checklist_draft

    # Phases 8 and 9 run back to back; both are reviewed at Gate 4.
    project.write_artifact(f"{feature_dir}/checklist.md")
    project.ok("advance", "--to", "tasks_draft")
    note()
    project.write_artifact(f"{feature_dir}/tasks.md")
    project.ok("advance", "--to", "gate_tasks")
    note()
    project.ok("gate", "approve", "--gate", "gate_tasks")
    note()  # analyze

    # Phase 11 -> Gate 5 (same tasks.md, refined)
    project.write_artifact(f"{feature_dir}/tasks.md",
                           "# Tasks (refined by analysis)\n\n" + "T001. " * 40)
    project.ok("drift", "rebaseline", "--gate", "gate_tasks")
    project.ok("advance", "--to", "gate_analyze")
    note()
    project.ok("gate", "approve", "--gate", "gate_analyze")
    note()  # design_generation

    # Phase 13 -> Gate 6
    project.write_artifact("design/app/app-design.md")
    project.write_artifact("design/db/db-design.md")
    project.ok("advance", "--to", "gate_design")
    note()
    project.ok("gate", "approve", "--gate", "gate_design")
    note()  # implement

    # Phase 15 -> Gate 7. The manifest is built, not faked: Gate 7 refuses a
    # manifest without a secrets scan and test evidence.
    project.ok("implement", "preflight", "--bypass")
    project.ok("manifest", "build", "--summary", "Implemented the Todo REST API.")
    project.ok("advance", "--to", "gate_implement")
    note()
    project.ok("gate", "approve", "--gate", "gate_implement")
    note()  # security_review

    # Phase 17 -> Gate 8
    begun = project.ok("security-review", "begin")
    project.write_artifact(begun.data["review_filename"])
    project.ok("advance", "--to", "gate_security")
    note()
    project.ok("gate", "approve", "--gate", "gate_security")
    note()  # complete

    return seen


def test_traversal_matches_the_transcript(git_project):
    seen = run_happy_path(git_project)
    assert seen == EXPECTED_TRAVERSAL


def test_all_eight_gates_approved_with_baselines(git_project):
    run_happy_path(git_project)
    state = git_project.state()

    for gate in GATES:
        entry = state["approvals"][gate]
        assert entry is not None, f"{gate} was never approved"
        assert entry["decision"] == "approved"
        assert entry["timestamp"]
        assert state["artifact_shas"][gate], f"{gate} has no baseline fingerprint"
        assert state["artifact_shas"][gate].islower()

    assert state["approvals"]["gate_spec"]["comments"].startswith("Add rate limiting")


def test_workflow_ends_complete(git_project):
    run_happy_path(git_project)
    state = git_project.state()
    assert state["current_phase"] == "complete"
    assert state["status"] == "completed"
    assert state["progress"] == "18/18"


def test_phase_history_records_every_phase_in_order(git_project):
    run_happy_path(git_project)
    history = [e["phase"] for e in git_project.state()["phase_history"]]
    # Every phase except the terminal one leaves a history entry.
    assert history == EXPECTED_TRAVERSAL[:-1]
    outcomes = {e["phase"]: e["outcome"] for e in git_project.state()["phase_history"]}
    for gate in GATES:
        assert outcomes[gate] == "approved"
    assert outcomes["constitution_draft"] == "completed"


def test_audit_chain_survives_the_whole_run(git_project):
    run_happy_path(git_project)
    verify = git_project.ok("audit", "verify")
    assert verify.data["matches"] is True
    assert verify.data["chain_ok"] is True

    # Every gate decision is on the record, and the ledger only grows.
    text = git_project.audit_file.read_text(encoding="utf-8")
    assert text.count("**Gate Decision:** APPROVED") == len(GATES)
    assert verify.data["entries"] == text.count("## AUDIT ")
    assert verify.data["entries"] > len(EXPECTED_TRAVERSAL)


def test_completion_summary_written_exactly_once(git_project):
    run_happy_path(git_project)
    summaries = list(git_project.runtime.glob("completion-summary*.json"))
    assert len(summaries) == 1

    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert summary["all_gates_approved"] is True
    assert summary["project_name"] == "Todo List REST API"
    assert summary["security_review_artifact"].startswith("reviews/security-review-")
    assert summary["phases_completed"] == len(EXPECTED_TRAVERSAL) - 1


def test_no_drift_is_reported_at_any_point(git_project):
    """A clean run must never queue a re-approval — in particular, the
    analyze step refines tasks.md, which Gate 4 already fingerprinted."""
    run_happy_path(git_project)
    state = git_project.state()
    assert state["drift_queue"] == []
    assert state["pending_phase"] is None
    assert git_project.ok("drift", "check").data["drifted"] == []


def test_lock_is_refreshed_on_every_save(git_project):
    run_happy_path(git_project)
    lock = (git_project.runtime / "lock").read_text(encoding="utf-8")
    assert lock.strip().endswith("happy")
