"""advance and gate approve/reject — where gate discipline is enforced."""

from __future__ import annotations

import ast
import copy
import json
from pathlib import Path

import pytest

from conftest import SDLE_PY, sdle
from test_units_artifact_review import review_for_gate

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
    assert "speckit_feature_directory" in data["skipped_reason"]


def test_gate_show_substitutes_feature_id(started):
    directory = started.feature_dir("001-todo-api")
    at(started, "gate_spec", "awaiting_approval",
       specKit={"featureId": "001-todo-api", "featureDirectory": directory,
                "workflowId": None, "runId": None})
    data = started.ok("gate", "show", "--gate", "gate_spec").data
    assert data["artifact_path"] == f"{directory}/spec.md"


def test_gate_show_refuses_unknown_gate(started):
    result = started.run("gate", "show", "--gate", "gate_nope")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "unknown_gate"


# -- gate approve -----------------------------------------------------------


def test_gate_approve_records_baseline_and_advances(started):
    started.write_artifact(".specify/memory/constitution.md")
    at(started, "gate_constitution", "awaiting_approval")
    review_for_gate(started, "gate_constitution")  # T06: E2.

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
    review_for_gate(started, "gate_constitution")  # T06: E2.
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
    review_for_gate(started, "gate_constitution")  # T06: E2.
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
    review_for_gate(started, "gate_security")  # T06: E2.

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
    assert summary["workflow_version"] == "1.17"
# ==========================================================================
# T11 N22 / D13 — an acknowledgement names one checkout
#
# `pending_confirm_action` was a *flag*: it recorded THAT a branch mismatch had
# been acknowledged, never WHICH branch. So the second step of a two-step
# command could arrive on a third branch and be waved through on an
# acknowledgement given for a different checkout — the guard's whole subject
# matter, and unaudited. T03 recorded that as a declared fail-open with no
# other owner; D13 closes it with `pending_branch_ack`.
# ==========================================================================


SESSION = "n22"

# The four two-step commands N22 names, as the invocations that reach the
# guard. `skip` carries the detailed assertions below; this tuple parametrises
# `test_n22_every_two_step_command_refuses_a_stale_acknowledgement` so the
# other three are covered too rather than assumed to behave alike.
BRANCH_TWO_STEP = (
    (("skip",), "skip"),
    (("reset",), "reset"),
    (("restart", "--to", "1"), "restart"),
    (("implement", "preflight"), "implement preflight"),
)


def _on_a_mismatched_branch(project, name="feature/elsewhere"):
    """Start the execution on one branch, then check out another."""
    project.git("checkout", "-q", "-b", name)
    mismatch = sdle.branch_mismatch(
        sdle.dataclass_replace(
            sdle.resolve_paths(str(project.root), str(project.skill_root)),
            workitem=project.workitem))
    assert mismatch is not None, "fixture did not produce a branch mismatch"
    return mismatch


def test_n22_the_first_step_records_which_branch_it_armed_against(started_git):
    """The new field has exactly one writer and it records the branch, not
    merely the fact."""
    project = started_git
    _on_a_mismatched_branch(project)

    refused = project.run("skip", session=SESSION)

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "branch_mismatch", refused
    state = project.state()
    assert state["pending_confirm_action"] == "branch_mismatch"
    assert state["pending_branch_ack"] == "feature/elsewhere"


def test_n22_acknowledging_on_the_same_branch_still_works(started_git):
    """The behaviour that must NOT regress: the ordinary two-step
    acknowledgement is unchanged, and both fields clear together."""
    project = started_git
    _on_a_mismatched_branch(project)

    project.run("skip", session=SESSION)          # arms the guard
    second = project.run("skip", session=SESSION)  # acknowledges it

    # The branch guard passed; `skip`'s own confirmation is what refuses now.
    assert second.reason != "branch_mismatch", second
    state = project.state()
    assert state["pending_branch_ack"] is None, state
    ledger = project.audit_file.read_text(encoding="utf-8")
    assert "branch_mismatch_accepted" in ledger


def test_n22_switching_branch_between_the_two_steps_is_refused_and_audited(
    started_git,
):
    """The fail-open T03-1 recorded, closed.

    Acknowledge on branch B, switch to branch C, re-run. Before D13 the flag
    said only "an acknowledgement is outstanding" and the command proceeded on
    a checkout nobody had agreed to. It now refuses, re-arms against the
    branch you are actually on, and leaves a `branch_ack_stale` entry saying
    why.
    """
    project = started_git
    _on_a_mismatched_branch(project, "feature/b")

    armed = project.run("skip", session=SESSION)
    assert armed.reason == "branch_mismatch"
    assert project.state()["pending_branch_ack"] == "feature/b"

    project.git("checkout", "-q", "-b", "feature/c")

    stale = project.run("skip", session=SESSION)

    assert stale.exit_code == EXIT_REFUSED, stale
    assert stale.reason == "branch_mismatch", stale
    assert stale.data["acknowledged"] == "feature/b", stale
    assert stale.data["current"] == "feature/c", stale
    # Re-armed against the branch we are actually on, not consumed.
    assert project.state()["pending_branch_ack"] == "feature/c"
    assert project.state()["pending_confirm_action"] == "branch_mismatch"
    # Audited, which is the half T03 said was missing.
    ledger = project.audit_file.read_text(encoding="utf-8")
    assert "branch_ack_stale" in ledger
    assert "feature/b" in ledger and "feature/c" in ledger
    assert "branch_mismatch_accepted" not in ledger, (
        "the switched-to branch must not inherit the acknowledgement")
    # And the action did not run.
    assert project.state()["status"] != "skipped"
    assert project.ok("audit", "verify").exit_code == EXIT_OK


def test_n22_acknowledging_again_on_the_new_branch_then_proceeds(started_git):
    """Fail-closed, not dead-ended: the user can still consent, on the
    checkout they are actually on."""
    project = started_git
    _on_a_mismatched_branch(project, "feature/b")
    project.run("skip", session=SESSION)
    project.git("checkout", "-q", "-b", "feature/c")
    project.run("skip", session=SESSION)      # refused, re-armed

    accepted = project.run("skip", session=SESSION)

    assert accepted.reason != "branch_mismatch", accepted
    assert project.state()["pending_branch_ack"] is None
    ledger = project.audit_file.read_text(encoding="utf-8")
    assert "branch_mismatch_accepted" in ledger
    assert "feature/c" in ledger.split("branch_mismatch_accepted", 1)[1][:400]


def test_n22_returning_to_the_recorded_branch_needs_no_acknowledgement(
    started_git,
):
    """There is nothing to acknowledge when there is no mismatch. The guard
    returns before it reads or writes anything."""
    project = started_git
    recorded = json.loads(
        (project.runtime / "execution.json").read_text(encoding="utf-8")
    )["git"]["branch"]
    _on_a_mismatched_branch(project, "feature/b")
    project.run("skip", session=SESSION)
    assert project.state()["pending_branch_ack"] == "feature/b"

    project.git("checkout", "-q", recorded)

    result = project.run("skip", session=SESSION)

    assert result.reason != "branch_mismatch", result
    # Untouched rather than cleared: the guard never ran.
    assert project.state()["pending_branch_ack"] == "feature/b"


@pytest.mark.parametrize("invocation,action", BRANCH_TWO_STEP,
                         ids=[action for _, action in BRANCH_TWO_STEP])
def test_n22_every_two_step_command_refuses_a_stale_acknowledgement(
    started_git, invocation, action
):
    """N22 names four commands, so all four are asserted.

    Every one of them is two-step, and before D13 every one of them would
    consume an acknowledgement given for a different checkout. The refusal is
    the same for all four because the guard is one function — which is the
    point: there is no per-command carve-out to get wrong.
    """
    project = started_git
    mismatch = _on_a_mismatched_branch(project, "feature/b")

    armed = project.run(*invocation, session=SESSION)
    assert armed.exit_code == EXIT_REFUSED, armed
    assert armed.reason == "branch_mismatch", armed
    assert project.state()["pending_branch_ack"] == "feature/b"

    project.git("checkout", "-q", "-b", "feature/c")
    before = project.state()

    stale = project.run(*invocation, session=SESSION)

    assert stale.exit_code == EXIT_REFUSED, stale
    assert stale.reason == "branch_mismatch", stale
    assert stale.data["acknowledged"] == "feature/b", stale
    assert stale.data["current"] == "feature/c", stale
    # Still measured against the branch the execution was started on: the
    # stale acknowledgement replaces neither of the other two facts.
    assert stale.data["recorded"] == mismatch["recorded"], stale
    assert stale.data["action"] == action, stale

    # The action did not run: nothing but the guard's own bookkeeping moved.
    after = project.state()
    assert after["current_phase"] == before["current_phase"]
    assert after["approvals"] == before["approvals"]
    assert after["status"] == before["status"]
    assert after["pending_branch_ack"] == "feature/c"

    ledger = project.audit_file.read_text(encoding="utf-8")
    assert "branch_ack_stale" in ledger
    assert "branch_mismatch_accepted" not in ledger
    assert project.ok("audit", "verify").exit_code == EXIT_OK


def test_n22_the_field_has_exactly_one_writer(started_git):
    """Invariant 6, and the reason `pending_branch_ack` cannot drift out of
    step with the flag it qualifies: only `branch_guard` assigns it."""
    tree = ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))
    writers = set()
    for function in [n for n in ast.walk(tree)
                     if isinstance(n, ast.FunctionDef)]:
        for node in ast.walk(function):
            if (isinstance(node, ast.Subscript)
                    and isinstance(node.slice, ast.Constant)
                    and node.slice.value == "pending_branch_ack"
                    and isinstance(node.ctx, ast.Store)):
                writers.add(function.name)
    assert writers == {"branch_guard"}, writers


def test_n22_a_resuming_session_can_see_which_branch_was_acknowledged(
    started_git,
):
    """TP-006: correctness may not depend on conversation history. The flag
    alone is no longer the whole fact, so `resume` reports the branch too."""
    project = started_git
    _on_a_mismatched_branch(project, "feature/b")
    project.run("skip", session=SESSION)

    pending = project.ok("resume").data["pending"]

    assert pending["pending_confirm_action"] == "branch_mismatch"
    assert pending["pending_branch_ack"] == "feature/b"


def test_tr20_the_acknowledgement_is_still_ledgered_before_a_later_refusal(
    started_git,
):
    """T11 TR20, verified rather than assumed — and the verdict is DEFERRED.

    T03-8 recorded that `branch_mismatch_accepted` is written even when the
    command then refuses for an unrelated reason. The T11 plan lists TR20 as
    "FIXED as a by-product of D13 — verify explicitly; if it does not fall out,
    record as DEFERRED". It does not fall out, and this test is the evidence.

    D13 changes *which* acknowledgement is honoured, not *when* it is written:
    `branch_guard` runs ahead of the command body and cannot know whether that
    body will succeed, so the acceptance entry precedes any later refusal
    exactly as before. What D13 does remove is the harm T03-8 pointed at — the
    entry is no longer a standing permission, because a subsequent invocation
    on a different checkout is refused (`test_n22_switching_...`).

    The residual is recorded, not silently left: the ledger's claim is that the
    *branch* was acknowledged, which is true, while the command's own outcome
    is a separate later entry. Pinned here so a future edit that reorders the
    guard has to face the question deliberately.
    """
    project = started_git
    _on_a_mismatched_branch(project, "feature/b")

    first = project.run("advance", "--to", "constitution_draft",
                        session=SESSION)
    assert first.reason == "branch_mismatch", first

    second = project.run("advance", "--to", "constitution_draft",
                         session=SESSION)

    # The guard let it past; the command itself refused for its own reason.
    assert second.exit_code == EXIT_REFUSED, second
    assert second.reason != "branch_mismatch", second

    ledger = project.audit_file.read_text(encoding="utf-8")
    assert "branch_mismatch_accepted" in ledger
    # And the action demonstrably did not happen.
    assert project.state()["current_phase"] == "constitution_draft"
    assert project.ok("audit", "verify").exit_code == EXIT_OK


# ==========================================================================
# T11 N23 / D14 — the 1.16 -> 1.17 migration
# ==========================================================================


def test_n23_the_migration_adds_the_field_and_is_idempotent(started):
    """Running the chain twice must be indistinguishable from running it
    once — a migration that is not idempotent turns a retried command into a
    corruption."""
    state = started.state()
    state["workflow_version"] = "1.16"
    state.pop("pending_branch_ack", None)
    started.write_state(state)

    first = started.ok("migrate", session="n23")
    assert first.data["steps"] == ["1.16->1.17"], first
    once = started.state()
    assert once["workflow_version"] == "1.17"
    assert once["pending_branch_ack"] is None

    second = started.ok("migrate", session="n23")
    assert second.data["steps"] == [], second
    assert started.state() == once


def test_n23_the_migration_preserves_every_verified_field(started):
    """The fields `migrate-workflow` verifies after a move are exactly the
    ones a migration must not disturb, so they are the ones asserted here."""
    before = started.state()
    keep = {field: copy.deepcopy(before[field])
            for field in sdle.MIGRATION_VERIFIED_FIELDS}

    state = started.state()
    state["workflow_version"] = "1.16"
    state.pop("pending_branch_ack", None)
    started.write_state(state)
    started.ok("migrate", session="n23b")

    after = started.state()
    for field, value in keep.items():
        assert after[field] == value, field


def test_n23_an_outstanding_acknowledgement_is_migrated_to_null_deliberately(
    started,
):
    """The safe value, not the convenient one.

    A v1.16 state can be mid-acknowledgement: `pending_confirm_action` is
    `branch_mismatch` and nobody recorded which branch. Inferring
    `current_branch()` here would manufacture a consent the user never gave,
    so the field arrives `null` and the guard asks again on the next
    lifecycle-critical command. `pending_confirm_action` itself is left
    exactly as it was — the migration invents nothing in either direction.
    """
    state = started.state()
    state["workflow_version"] = "1.16"
    state.pop("pending_branch_ack", None)
    state["pending_confirm_action"] = "branch_mismatch"
    started.write_state(state)

    started.ok("migrate", session="n23c")

    after = started.state()
    assert after["pending_branch_ack"] is None
    assert after["pending_confirm_action"] == "branch_mismatch"


def test_n23_the_version_chain_gained_a_row_and_lost_none(started):
    """D14 appends; it never replaces. The whole chain is still walkable from
    the oldest version the engine knows."""
    consts = sdle.load_constants(
        sdle.resolve_paths(str(started.root), str(started.skill_root)))
    chain = consts.version_chain
    assert chain[-1] == ("1.16", "1.17")
    assert chain[0][0] == "1.0"
    # Contiguous: every row's `to` is the next row's `from`.
    for (_, to), (frm, _) in zip(chain, chain[1:]):
        assert to == frm, (to, frm)
    assert len(chain) == 17

