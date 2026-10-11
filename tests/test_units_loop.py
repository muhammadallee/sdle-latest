"""The bounded implementation loop (ADR-017, R3): AS-20 to AS-29.

The engine is a recorder and referee. These tests drive the steps the
orchestrator would perform (implement, reconcile, manifest, review, converge,
trace) and assert what the engine accepts, refuses and concludes.
"""
from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path

from conftest import PASSING_TEST_COMMAND, SDLE_PY, sdle
from test_units_artifact_review import frozen
from test_units_review_types import record_review
from trace_support import (
    FULL_TASKS, build, build_junit, package_view, walk)

EXIT_REFUSED = 1


def loop_view(project, **kw):
    """A package WorkItem at `implement` with the base pinned, in a git repo."""
    project.init_git()
    view = package_view(project)
    walk(view, "implement", **kw)
    view.ok("implement", "preflight", "--bypass")
    return view


def block_unmapped(view, limit=None):
    """A policy that refuses an unmapped pass: a persistent, honest unmet
    condition for the bounds to act on. Written before any evidence is built,
    because a policy edit is a change to the tree."""
    policy = view.root / ".sdle" / "policies" / "governance-policy.json"
    policy.parent.mkdir(parents=True, exist_ok=True)
    document = {"policyVersion": "1", "unmapped_verification_blocks": True}
    if limit:
        document["implementation_loop_max_iterations"] = limit
    policy.write_text(json.dumps(document), encoding="utf-8")


def tasks_path(view):
    return view.root / view.feature_dir("001-todo-api") / "tasks.md"


def no_findings(view) -> str:
    """An empty findings list under the WorkItem evidence directory (excluded
    from the tree digest): a structured review that found nothing."""
    path = view.runtime / "evidence" / "no-findings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]", encoding="utf-8")
    return path.relative_to(view.root).as_posix()


def code_review(view, result="PASS"):
    return record_review(view, "gate_implement", "code-review",
                         result=result, actor="agent",
                         findings=no_findings(view))


def run_iteration(view, *, tick=False, append=None, tests=build, review="PASS",
                  record=True, classification=None):
    """One full iteration, as the orchestrator would perform it."""
    view.ok("loop", "step", "--step", "implement")
    if tick:
        path = tasks_path(view)
        path.write_text(path.read_text(encoding="utf-8").replace(
            "- [ ] T001", "- [X] T001"), encoding="utf-8")
    view.ok("tasks", "reconcile")
    tests(view)
    view.ok("loop", "step", "--step", "manifest")
    assert code_review(view, review).exit_code == 0
    view.ok("loop", "step", "--step", "review")
    if append:
        path = tasks_path(view)
        path.write_text(path.read_text(encoding="utf-8") + append,
                        encoding="utf-8")
    view.ok("loop", "step", "--step", "converge")
    if append:
        view.ok("tasks", "reconcile")
    view.ok("loop", "step", "--step", "trace")
    if not record:
        return None
    args = ["loop", "record"]
    if classification:
        args += ["--classification", classification]
    return view.run(*args)


SECTION = ("\n## Phase 4: Convergence\n\n"
           "- [ ] T100 Test AC-001 also when the order list is empty\n")


# ---- begin -------------------------------------------------------------------


def test_a_loop_needs_the_implement_phase_and_a_pinned_base(bare_project):
    bare_project.init_git()
    view = package_view(bare_project)
    assert view.run("loop", "begin").reason == "loop_wrong_phase"
    walk(view, "implement")
    assert view.run("loop", "begin").reason == "loop_no_base"
    view.ok("implement", "preflight", "--bypass")
    began = view.ok("loop", "begin")
    assert began.data["limit"] == 3, "the built-in policy's"
    assert view.run("loop", "begin").reason == "loop_in_progress"


def test_a_task_list_that_drifted_from_its_approval_cannot_start_a_loop(
        bare_project):
    bare_project.init_git()
    view = package_view(bare_project)
    walk(view, "implement")
    view.ok("implement", "preflight", "--bypass")
    path = tasks_path(view)
    path.write_text(path.read_text(encoding="utf-8") + "- [ ] T050 sneaked\n",
                    encoding="utf-8")
    result = view.run("loop", "begin")
    assert result.reason == "tasks_drift"
    assert not (view.runtime / "implementation-loop.json").exists()


def test_the_limit_comes_from_the_policy_and_can_only_be_lowered(bare_project):
    bare_project.init_git()
    view = package_view(bare_project)
    walk(view, "implement")
    view.ok("implement", "preflight", "--bypass")
    policy = view.root / ".sdle" / "policies" / "governance-policy.json"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(json.dumps({
        "policyVersion": "1", "implementation_loop_max_iterations": 2}),
        encoding="utf-8")
    assert view.ok("loop", "begin").data["limit"] == 2
    policy.write_text(json.dumps({
        "policyVersion": "1", "implementation_loop_max_iterations": 5}),
        encoding="utf-8")
    assert view.run("loop", "stop", "--reason", "interrupted").exit_code == 0
    refused = view.run("loop", "begin")
    assert refused.exit_code != 0, "raising the limit is weakening"


# ---- AS-20: one predicate ------------------------------------------------------


def test_as20_the_loop_is_ready_only_through_the_predicate_the_gate_uses(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    result = run_iteration(view)
    assert result.data["stopReason"] == "ready_for_gate", result.data
    assert result.data["unmet"] == []
    paths = sdle.dataclass_replace(
        sdle.resolve_paths(str(view.root), str(view.skill_root)),
        workitem=view.workitem)
    consts = sdle.load_constants(paths)
    shown = view.ok("gate", "show", "--gate", "gate_implement").data
    view.ok("advance", "--to", "gate_implement")
    unmet = sdle.implementation_ready(paths, view.state(), consts,
                                      shown["artifact_path"])
    assert unmet == []
    assert view.run("gate", "approve", "--gate",
                    "gate_implement").exit_code == 0


def test_as20_the_gate_refuses_with_the_first_thing_the_loop_reports_unmet(
        bare_project):
    """Parity: whatever the loop reports unmet, the gate refuses with the
    first of it, in the order the gate has always refused in."""
    view = loop_view(bare_project)
    block_unmapped(view)
    view.ok("loop", "begin")
    result = run_iteration(view)
    assert result.data["stopReason"] is None
    reasons = [u["reason"] for u in result.data["unmet"]]
    assert reasons and reasons[0] == "trace_verification_unmapped"
    view.ok("advance", "--to", "gate_implement")
    refused = view.run("gate", "approve", "--gate", "gate_implement")
    assert refused.reason == reasons[0]


def test_a_review_of_the_wrong_kind_is_unmet_in_both(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    build(view)
    view.ok("loop", "step", "--step", "manifest")
    record_review(view, "gate_implement", "design-review")
    assert view.run("loop", "step", "--step", "review").reason == (
        "loop_review_missing")


# ---- AS-21: converge is not repeatable ---------------------------------------------


def test_as21_a_second_converge_without_implement_between_is_refused(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    run_iteration(view, append=SECTION, record=False)
    before = tasks_path(view).read_text(encoding="utf-8")
    result = view.run("loop", "step", "--step", "converge")
    assert result.reason == "loop_step_out_of_order"
    assert tasks_path(view).read_text(encoding="utf-8") == before
    assert before.count("Phase 4: Convergence") == 1, "no duplicate tasks"


def test_every_step_needs_the_one_before_it(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    assert view.run("loop", "step", "--step", "manifest"
                    ).reason == "loop_step_out_of_order"
    view.ok("loop", "step", "--step", "implement")
    for step in ("review", "converge", "trace"):
        assert view.run("loop", "step", "--step", step
                        ).reason == "loop_step_out_of_order"
    assert view.run("loop", "record").reason == "loop_step_out_of_order"


def test_a_convergence_that_appended_tasks_needs_them_reconciled_first(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    build(view)
    view.ok("loop", "step", "--step", "manifest")
    code_review(view)
    view.ok("loop", "step", "--step", "review")
    path = tasks_path(view)
    path.write_text(path.read_text(encoding="utf-8") + SECTION,
                    encoding="utf-8")
    view.ok("loop", "step", "--step", "converge")
    assert view.run("loop", "step", "--step", "trace").reason == (
        "loop_step_out_of_order")
    view.ok("tasks", "reconcile")
    view.ok("loop", "step", "--step", "trace")


def test_a_pending_converge_makes_the_gate_refuse_too(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    result = run_iteration(view, append=SECTION)
    assert result.data["stopReason"] is None
    assert "loop_converge_pending" in [u["reason"]
                                       for u in result.data["unmet"]]
    view.ok("advance", "--to", "gate_implement")
    code_review(view)
    assert view.run("gate", "approve", "--gate",
                    "gate_implement").reason == "loop_converge_pending"


def test_ticks_in_an_accepted_convergence_section_are_accepted_next_time(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    assert run_iteration(view, append=SECTION).data["stopReason"] is None
    view.ok("loop", "step", "--step", "implement")
    path = tasks_path(view)
    path.write_text(path.read_text(encoding="utf-8").replace(
        "- [ ] T100", "- [X] T100"), encoding="utf-8")
    assert view.ok("tasks", "reconcile").data["ticked"] == 1


# ---- AS-22: the task-list policy -------------------------------------------------------


def test_as22_a_change_outside_the_policy_stops_the_loop_with_tasks_drift(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    path = tasks_path(view)
    path.write_text(path.read_text(encoding="utf-8").replace(
        "Implement FR-001", "Skip FR-001"), encoding="utf-8")
    result = view.run("tasks", "reconcile")
    assert result.reason == "tasks_drift"
    shown = view.ok("loop", "show").data
    assert shown["stopReason"] == "tasks_drift"
    assert shown["active"] is False


def test_a_removed_task_is_not_a_tick(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    path = tasks_path(view)
    path.write_text(path.read_text(encoding="utf-8").replace(
        "- [ ] T002 Test AC-001: creating an order returns its number\n", ""),
        encoding="utf-8")
    assert view.run("tasks", "reconcile").reason == "tasks_drift"


def test_the_policy_is_structural(bare_project):
    delta = sdle._tasks_delta
    base = "# T\n- [ ] T1 a\n- [ ] T2 b\n"
    assert delta(base, base) == ({"ticked": 0, "appendedSections": []}, None)
    assert delta(base, base.replace("[ ] T1", "[X] T1"))[0]["ticked"] == 1
    assert delta(base, base + "\n## Phase 3: Convergence\n- [ ] T3 c\n")[0][
        "appendedSections"] == [3]
    assert delta(base, base + "- [ ] T3 c\n")[1], "appended outside a section"
    assert delta(base, base.replace("T2 b", "T2 changed"))[1]
    assert delta(base, "# T\n- [ ] T1 a\n")[1], "a removal"
    twice = base + "\n## Phase 3: Convergence\n- [ ] T3 c\n"
    assert delta(twice, twice + "\n## Phase 3: Convergence\n- [ ] T4 d\n")[1]


def test_reconcile_moves_the_task_baselines_and_audits_it(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    path = tasks_path(view)
    path.write_text(path.read_text(encoding="utf-8").replace(
        "- [ ] T001", "- [X] T001"), encoding="utf-8")
    assert view.ok("drift", "check").data["drifted"], "drift before"
    moved = view.ok("tasks", "reconcile")
    assert moved.data["rebaselined"] == ["gate_tasks", "gate_analyze"] or \
        set(moved.data["rebaselined"]) <= {"gate_tasks", "gate_analyze"}
    assert view.ok("drift", "check").data["drifted"] == []
    assert "tasks_reconciled" in view.audit_file.read_text(encoding="utf-8")


def test_reconcile_never_hides_drift_in_another_artifact(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    spec = view.root / view.feature_dir("001-todo-api") / "spec.md"
    spec.write_text(spec.read_text(encoding="utf-8") + "\nedited\n",
                    encoding="utf-8")
    result = view.run("tasks", "reconcile")
    assert result.reason == "reconcile_unrelated_drift"
    assert "gate_spec" in result.data["gates"]


# ---- AS-23 / AS-24: bounds ---------------------------------------------------------------


def test_as23_the_same_failures_twice_stop_the_loop_with_no_progress(
        bare_project):
    view = loop_view(bare_project)
    block_unmapped(view)
    view.ok("loop", "begin")
    first = run_iteration(view)
    assert first.data["stopReason"] is None
    second = run_iteration(view, append=SECTION)
    assert second.data["stopReason"] == "no_progress", (
        "appending tasks is not progress", second.data)
    assert "appending tasks is not progress" in second.data["next"]
    assert view.run("loop", "step", "--step", "implement").reason == (
        "loop_not_active")


def test_as24_the_iteration_limit_stops_the_loop_with_a_reason_and_a_next_action(
        bare_project):
    bare_project.init_git()
    view = package_view(bare_project)
    walk(view, "implement")
    view.ok("implement", "preflight", "--bypass")
    block_unmapped(view, limit=1)
    view.ok("loop", "begin")
    result = run_iteration(view)
    assert result.data["stopReason"] == "limit_exhausted"
    assert result.data["next"]
    assert view.run("loop", "step", "--step", "implement").reason == (
        "loop_not_active")


# ---- AS-25: resume -----------------------------------------------------------------------------


def test_as25_resuming_after_an_interruption_neither_duplicates_nor_trusts_a_stale_snapshot(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    built = build(view)
    view.ok("loop", "step", "--step", "manifest")
    # ... the session ends here, after the manifest and before `loop record`
    shown = view.ok("loop", "show").data
    assert shown["lastCompletedStep"] == "manifest"
    assert shown["resumable"] is True
    code_review(view)
    # the same evidence cannot be recorded twice
    again = view.run("loop", "step", "--step", "manifest")
    assert again.reason == "loop_step_out_of_order"
    # the tree moved while nobody was looking: the snapshot is stale
    (view.root / "late-change.py").write_text("x = 1\n", encoding="utf-8")
    stale = view.run("loop", "step", "--step", "review")
    assert stale.reason == "loop_snapshot_stale"
    assert view.ok("loop", "show").data["lastCompletedStep"] == "stale"
    build(view)
    assert view.run("loop", "step", "--step", "manifest").exit_code == 0
    record_before = (view.runtime / "implementation-loop.json").read_bytes()
    evidence_files = sorted((view.runtime / "evidence").glob(
        "implementation-*.json"))
    assert len(evidence_files) >= 2, "history is kept, never deleted"
    assert record_before


def test_evidence_is_never_recorded_twice_for_two_iterations(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    run_iteration(view, append=SECTION)
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    result = view.run("loop", "step", "--step", "manifest")
    assert result.reason == "loop_step_duplicate"


# ---- AS-26 / AS-27: what never counts as a pass -------------------------------------------------


def test_as26_an_unavailable_runner_stops_the_loop_never_a_pass(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")

    def no_tests(v):
        v.ok("manifest", "build", "--summary", "x", "--skip-tests")
    result = run_iteration(view, tests=no_tests)
    assert result.data["stopReason"] == "environment_blocker"
    assert result.data["stopReason"] != "ready_for_gate"


def test_a_stated_environment_blocker_ends_the_run(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    result = run_iteration(view, classification="environment_blocker")
    assert result.data["stopReason"] == "environment_blocker"


def test_a_requirement_ambiguity_routes_to_the_requirements_process(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    result = run_iteration(view, classification="requirement_ambiguity")
    assert result.data["stopReason"] == "ambiguity"
    assert "requirements-change" in result.data["next"]


def test_as27_a_deleted_test_file_stops_the_loop_for_a_human(bare_project):
    bare_project.init_git()
    (bare_project.root / "tests").mkdir()
    (bare_project.root / "tests" / "test_app.py").write_text(
        "def test_it():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=bare_project.root, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "tests"],
                   cwd=bare_project.root, check=True)
    view = package_view(bare_project)
    walk(view, "implement")
    view.ok("implement", "preflight", "--bypass")
    view.ok("loop", "begin")
    (bare_project.root / "tests" / "test_app.py").unlink()
    result = run_iteration(view)
    assert result.data["stopReason"] == "test_expectation_change"
    assert "tests/test_app.py" in result.data["next"]
    # `loop begin` is the human's re-entry: the deletion now stands accepted
    again = view.ok("loop", "begin")
    assert again.data["run"] == 2
    assert run_iteration(view).data["stopReason"] != "test_expectation_change"


def cases(*pairs):
    """A test command's report: the tests that exist and which of them fail."""
    return lambda v: build_junit(v, *pairs)


A = "test_AC-001_returns_the_order_number"
B = "test_AC-001_rejects_a_missing_clerk"


def test_a_test_case_that_disappears_stops_the_loop(bare_project):
    """Any test case present in an earlier iteration and gone now, mapped to a
    criterion or not, is a person's decision."""
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    first = run_iteration(view, append=SECTION, tests=cases((A, True),
                                                            ("test_other", True)))
    assert first.data["stopReason"] is None
    second = run_iteration(view, tests=cases((A, True)))
    assert second.data["stopReason"] == "test_expectation_change", second.data
    assert "test_other" in second.data["next"]


def test_the_sole_mapped_test_disappearing_is_caught_too(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    first = run_iteration(view, append=SECTION, tests=cases((A, True)))
    assert first.data["stopReason"] is None
    second = run_iteration(view, tests=cases(("test_unrelated", True)))
    assert second.data["stopReason"] == "test_expectation_change"


def test_repairing_different_failing_tests_is_progress(bare_project):
    """Two runs that both fail are not the same failure if different tests
    fail: the failing set is in the digest, not the exit code."""
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    one = run_iteration(view, append=SECTION,
                        tests=cases((A, False), (B, True)))
    assert one.data["stopReason"] is None
    two = run_iteration(view, append="\n## Phase 5: Convergence\n\n"
                        "- [ ] T101 Test AC-001 for a missing clerk\n",
                        tests=cases((A, True), (B, False)))
    assert two.data["stopReason"] is None, two.data
    three = run_iteration(view, append="\n## Phase 6: Convergence\n\n"
                          "- [ ] T102 Test AC-001 once more\n",
                          tests=cases((A, True), (B, False)))
    assert three.data["stopReason"] == "no_progress", three.data


TAGGED = ("# AC-001 returns the order number\n"
          "def test_creates_an_order():\n"
          "    assert create_order().number == 1\n")


def with_tagged_test(project):
    project.init_git()
    (project.root / "tests").mkdir()
    (project.root / "tests" / "test_orders.py").write_text(
        TAGGED, encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=project.root, check=True,
                   capture_output=True)
    subprocess.run(["git", "commit", "-q", "-m", "tests"],
                   cwd=project.root, check=True)
    view = package_view(project)
    walk(view, "implement")
    view.ok("implement", "preflight", "--bypass")
    return view


def test_weakening_an_acceptance_tests_assertion_stops_the_loop(bare_project):
    view = with_tagged_test(bare_project)
    view.ok("loop", "begin")
    (bare_project.root / "tests" / "test_orders.py").write_text(
        TAGGED.replace("== 1", "is not None"), encoding="utf-8")
    result = run_iteration(view)
    assert result.data["stopReason"] == "test_expectation_change"
    assert "tests/test_orders.py" in result.data["next"]
    again = view.ok("loop", "begin")
    assert run_iteration(view).data["stopReason"] != "test_expectation_change", (
        "the person's re-entry accepts the tests as they now stand")


def test_adding_tests_to_an_acceptance_test_file_is_not_weakening(
        bare_project):
    view = with_tagged_test(bare_project)
    view.ok("loop", "begin")
    (bare_project.root / "tests" / "test_orders.py").write_text(
        TAGGED + "\ndef test_also_when_empty():\n    assert True\n",
        encoding="utf-8")
    assert run_iteration(view).data["stopReason"] == "ready_for_gate"


def test_a_tagged_test_losing_its_tag_is_a_change(bare_project):
    view = with_tagged_test(bare_project)
    view.ok("loop", "begin")
    (bare_project.root / "tests" / "test_orders.py").write_text(
        TAGGED.replace("AC-001", "the order"), encoding="utf-8")
    assert run_iteration(view).data["stopReason"] == "test_expectation_change"


# ---- AS-28 / AS-29: the gate stays human -------------------------------------------------------------


def test_as28_a_human_rejection_follows_the_existing_remediation_path(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    assert run_iteration(view).data["stopReason"] == "ready_for_gate"
    view.ok("advance", "--to", "gate_implement")
    review = record_review(view, "gate_implement", "code-review")
    assert review.exit_code == 0
    view.ok("gate", "reject", "--gate", "gate_implement",
            "--reason", "the error path is wrong")
    view.ok("remediate", "begin", "--gate", "gate_implement")
    state = view.state()
    assert state["current_phase"] == "gate_implement", (
        "the existing remediation path leaves the WorkItem at the gate")
    assert state["attempt_counts"]["implement"]["remediations"] == 1
    again = view.ok("loop", "begin")
    assert again.data["run"] == 2, "a new run, its own limit"


def test_as29_the_loop_never_approves_and_ready_means_ready_for_a_human(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    before = view.state()
    result = run_iteration(view)
    assert result.data["stopReason"] == "ready_for_gate"
    state = view.state()
    assert state["current_phase"] == "implement", "it does not advance"
    assert (state["approvals"].get("gate_implement") or {}).get(
        "decision") != "approved"
    assert state["approvals"] == before["approvals"]
    assert "never approves" in result.data["next"]


def test_no_loop_function_can_reach_an_approval():
    """Structural: nothing the loop runs calls an approving or advancing
    function."""
    tree = ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))
    forbidden = {"cmd_gate_approve", "_approve_drift", "cmd_gate_omit",
                 "apply_advance", "cmd_advance", "cmd_skip"}
    for fn in ast.walk(tree):
        if (isinstance(fn, ast.FunctionDef)
                and (fn.name.startswith("cmd_loop_")
                     or fn.name in ("cmd_tasks_reconcile",
                                    "implementation_ready"))):
            called = {n.func.id for n in ast.walk(fn)
                      if isinstance(n, ast.Call)
                      and isinstance(n.func, ast.Name)}
            assert not called & forbidden, (fn.name, called & forbidden)


# ---- show, record integrity, the gate summary ------------------------------------------------------


def test_loop_show_gives_the_gate_what_it_will_be_shown(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    run_iteration(view)
    shown = view.ok("loop", "show").data
    gate = shown["gate"]
    assert gate["stopReason"] == "ready_for_gate"
    assert gate["treeDigest"] and gate["baseRef"] and gate["tests"] == "passed"
    assert gate["scopeCoverage"]["tasksUncovered"] == []
    assert gate["unmapped"] == ["AC-001"], "shown apart, never as verified"


def test_a_loop_record_the_engine_did_not_write_is_an_integrity_failure(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    target = view.runtime / "implementation-loop.json"
    document = json.loads(target.read_text(encoding="utf-8"))
    document["runs"][0]["limit"] = 99
    target.write_text(json.dumps(document), encoding="utf-8")
    result = view.run("loop", "show")
    assert result.exit_code == 3
    assert result.reason == "loop_record_invalid"


def test_a_stopped_run_can_be_followed_by_a_new_one_with_its_own_limit(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "stop", "--reason", "interrupted")
    assert view.run("loop", "stop", "--reason", "interrupted"
                    ).reason == "loop_not_active"
    second = view.ok("loop", "begin")
    assert second.data["run"] == 2
    assert view.ok("loop", "show").data["runs"] == 2


def test_a_state_with_no_loop_is_untouched_by_the_loop_rules(started):
    assert started.ok("loop", "show").data["active"] is False
    assert started.run("loop", "step", "--step", "implement"
                       ).reason == "loop_not_active"


def test_a_refused_loop_command_writes_nothing(bare_project):
    view = loop_view(bare_project)
    before = frozen(view)
    assert view.run("loop", "step", "--step", "implement"
                    ).reason == "loop_not_active"
    assert frozen(view) == before


# ---- round 1 of the R3 review ------------------------------------------------------


def test_drift_re_approval_of_the_implementation_gate_uses_the_same_predicate(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    result = run_iteration(view, append=SECTION)
    assert "loop_converge_pending" in [u["reason"]
                                       for u in result.data["unmet"]]
    view.ok("advance", "--to", "gate_implement")
    code_review(view)
    state = view.state()
    state["drift_queue"] = ["gate_implement"]
    view.write_state(state)
    before = frozen(view)
    refused = view.run("gate", "approve", "--gate", "gate_implement")
    assert refused.reason == "loop_converge_pending"
    assert frozen(view) == before


def test_unticking_a_task_is_not_a_tick():
    delta = sdle._tasks_delta
    assert delta("- [X] T1 done\n", "- [ ] T1 done\n")[1]
    assert delta("- [x] T1 done\n", "- [ ] T1 done\n")[1]
    assert delta("- [ ] T1 done\n", "- [x] T1 done\n")[0]["ticked"] == 1


def test_unticking_through_the_command_stops_the_run(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    first = run_iteration(view, tick=True, append=SECTION)
    assert first.data["stopReason"] is None
    view.ok("loop", "step", "--step", "implement")
    path = tasks_path(view)
    path.write_text(path.read_text(encoding="utf-8").replace(
        "- [X] T001", "- [ ] T001"), encoding="utf-8")
    result = view.run("tasks", "reconcile")
    assert result.reason == "tasks_drift"
    assert view.ok("loop", "show").data["stopReason"] == "tasks_drift"


def test_a_crash_after_the_baselines_moved_is_recoverable(bare_project,
                                                          monkeypatch):
    import pytest
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    path = tasks_path(view)
    path.write_text(path.read_text(encoding="utf-8").replace(
        "- [ ] T001", "- [X] T001"), encoding="utf-8")
    real = sdle.write_loop_record

    def crash(paths, record):
        raise RuntimeError("simulated crash before the record is written")

    monkeypatch.setattr(sdle, "write_loop_record", crash)
    with pytest.raises(RuntimeError):
        view.run("tasks", "reconcile")
    monkeypatch.setattr(sdle, "write_loop_record", real)
    assert view.ok("drift", "check").data["drifted"] == [], (
        "the baselines had moved")
    again = view.ok("tasks", "reconcile")
    assert again.data["ticked"] == 1, "the retry finishes the same change"
    build(view)
    assert view.ok("loop", "step", "--step", "manifest").exit_code == 0


def test_the_outputs_are_not_producible_out_of_order(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    assert view.run("manifest", "build", "--test-command",
                    PASSING_TEST_COMMAND).reason == "loop_step_out_of_order"
    view.ok("tasks", "reconcile")
    build(view)
    view.ok("loop", "step", "--step", "manifest")
    assert view.run("manifest", "build", "--test-command",
                    PASSING_TEST_COMMAND).reason == "loop_step_out_of_order", (
        "a second build would duplicate recorded evidence")
    assert code_review(view).exit_code == 0
    view.ok("loop", "step", "--step", "review")
    assert code_review(view).reason == "loop_step_out_of_order", (
        "a second review would duplicate a recorded one")
    assert record_review(view, "gate_implement", "design-review"
                         ).exit_code == 0, "other review kinds are not the loop's"


def test_a_symlink_inside_a_nested_repository_is_part_of_the_tree(
        git_project):
    import os
    import pytest
    from test_units_tree_digest import digest_of, ready
    ready(git_project)
    sub = git_project.root / "vendor-lib"
    sub.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=sub, check=True)
    (sub / "a.txt").write_text("a\n", encoding="utf-8")
    (sub / "b.txt").write_text("b\n", encoding="utf-8")
    try:
        os.symlink("a.txt", sub / "link.txt")
    except (OSError, NotImplementedError):
        pytest.skip("this platform cannot create symbolic links here")
    subprocess.run(["git", "add", "."], cwd=sub, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "x"], cwd=sub, check=True)
    subprocess.run(["git", "add", "vendor-lib"], cwd=git_project.root,
                   capture_output=True)
    base = digest_of(git_project)["digest"]
    (sub / "link.txt").unlink()
    os.symlink("b.txt", sub / "link.txt")
    assert digest_of(git_project)["digest"] != base


# ---- round 2 of the R3 review ---------------------------------------------------------


def test_a_pending_convergence_survives_stopping_the_run_and_beginning_another(
        bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    result = run_iteration(view, append=SECTION)
    assert result.data["stopReason"] is None
    view.ok("loop", "stop", "--reason", "interrupted")
    view.ok("loop", "begin")
    view.ok("advance", "--to", "gate_implement")
    code_review(view)
    refused = view.run("gate", "approve", "--gate", "gate_implement")
    assert refused.reason == "loop_converge_pending"


def test_a_retry_before_recording_records_the_latest_output_once(
        bare_project):
    """The crash window: the evidence exists but `loop step manifest` has not
    run. The guarantee is on what the loop records: the latest evidence, used
    once. An extra output made in the window is history, never deleted, and
    never recorded."""
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    first = build(view)
    second = build(view)
    assert first.data["evidence"] != second.data["evidence"]
    assert (view.root / first.data["evidence"]).is_file(), "history is kept"
    recorded = view.ok("loop", "step", "--step", "manifest").data
    assert recorded["detail"]["evidenceId"] in second.data["evidence"]
    assert view.run("loop", "step", "--step", "manifest"
                    ).reason == "loop_step_out_of_order"
    assert code_review(view).exit_code == 0
    assert code_review(view).exit_code == 0, "an extra review is history too"
    view.ok("loop", "step", "--step", "review")
    assert code_review(view).reason == "loop_step_out_of_order"


def test_a_manifest_the_loop_refuses_can_be_rebuilt_and_the_run_continues(
        bare_project):
    """Nothing wedges: a refused manifest step leaves the way forward open."""
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    build(view)
    (view.root / "after-the-build.py").write_text("x = 1\n", encoding="utf-8")
    assert view.run("loop", "step", "--step", "manifest"
                    ).reason == "loop_snapshot_stale"
    build(view)
    assert view.ok("loop", "step", "--step", "manifest").exit_code == 0


def test_a_stale_rebuild_may_produce_a_new_output(bare_project):
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    build(view)
    view.ok("loop", "step", "--step", "manifest")
    code_review(view)
    (view.root / "late-change.py").write_text("x = 1\n", encoding="utf-8")
    assert view.run("loop", "step", "--step", "review"
                    ).reason == "loop_snapshot_stale"
    build(view)
    assert view.ok("loop", "step", "--step", "manifest").exit_code == 0


def test_a_report_too_large_to_track_completely_is_refused_not_truncated(
        bare_project, tmp_path):
    import sys
    from conftest import _command_line
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    count = sdle.LOOP_INVENTORY_MAX + 1
    source = tmp_path / "big.xml"
    source.write_text("<testsuite>" + "".join(
        f'<testcase classname="s" name="t{i}"/>' for i in range(count))
        + "</testsuite>", encoding="utf-8")
    target = view.runtime / "evidence" / "big.xml"
    target.parent.mkdir(parents=True, exist_ok=True)
    code = (f"import shutil; shutil.copy({str(source)!r}, {str(target)!r})")
    view.ok("manifest", "build", "--test-command",
            _command_line([sys.executable, "-c", code]), "--junit",
            target.relative_to(view.root).as_posix())
    refused = view.run("loop", "step", "--step", "manifest")
    assert refused.reason == "loop_inventory_too_large"
    assert refused.data["cases"] == count


# ---- Phase M (ui-quality): loop and review integrity -------------------------


def findings_file(view, rows, name="findings.json"):
    """A findings document under the WorkItem evidence directory (excluded
    from the tree digest), named relative to the repository root."""
    path = view.runtime / "evidence" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows), encoding="utf-8")
    return path.relative_to(view.root).as_posix()


BLOCKER = {"id": "F1", "severity": "blocking", "location": "src/app.py:10",
           "obligations": ["AC-001"], "disposition": "open"}


def at_the_review_step(view):
    view.ok("loop", "begin")
    view.ok("loop", "step", "--step", "implement")
    view.ok("tasks", "reconcile")
    build(view)
    view.ok("loop", "step", "--step", "manifest")


def manifest_key(view) -> str:
    paths = sdle.dataclass_replace(
        sdle.resolve_paths(str(view.root), str(view.skill_root)),
        workitem=view.workitem)
    return paths.manifest_file.relative_to(paths.project_root).as_posix()


def fingerprints(view) -> list[str]:
    paths = sdle.dataclass_replace(
        sdle.resolve_paths(str(view.root), str(view.skill_root)),
        workitem=view.workitem)
    return sdle._blocking_finding_fingerprints(paths, manifest_key(view))


def test_m2_a_review_without_structured_findings_is_refused_at_the_step(
        bare_project):
    view = loop_view(bare_project)
    at_the_review_step(view)
    assert record_review(view, "gate_implement", "code-review",
                         actor="agent").exit_code == 0
    refused = view.run("loop", "step", "--step", "review")
    assert refused.exit_code == EXIT_REFUSED
    assert refused.reason == "loop_review_unstructured"
    # an empty list is a structured review that found nothing, and passes
    assert record_review(view, "gate_implement", "code-review", actor="agent",
                         findings=findings_file(view, [])).exit_code == 0
    assert view.run("loop", "step", "--step", "review").exit_code == 0


def test_m2_an_iteration_already_past_an_unstructured_review_cannot_close(
        bare_project):
    """An iteration recorded before the rule existed: simulated by removing
    the findings summary from the recorded review step. It cannot be closed,
    and the engine's own way out (stop, then begin) works."""
    view = loop_view(bare_project)
    view.ok("loop", "begin")
    for step in ("implement",):
        view.ok("loop", "step", "--step", step)
    view.ok("tasks", "reconcile")
    build(view)
    view.ok("loop", "step", "--step", "manifest")
    assert code_review(view).exit_code == 0
    view.ok("loop", "step", "--step", "review")
    view.ok("loop", "step", "--step", "converge")
    view.ok("loop", "step", "--step", "trace")
    # simulate what an earlier engine would have recorded, through the
    # engine's own reader and sealed writer (a hand edit is refused)
    paths = sdle.dataclass_replace(
        sdle.resolve_paths(str(view.root), str(view.skill_root)),
        workitem=view.workitem)
    document = sdle.read_loop_record(paths)
    for run in document["runs"]:
        for iteration in run["iterations"]:
            for step in iteration["steps"]:
                if step["step"] == "review":
                    step["detail"]["findings"] = None
    sdle.write_loop_record(paths, document)

    refused = view.run("loop", "record")
    assert refused.exit_code == EXIT_REFUSED
    assert refused.reason == "loop_review_unstructured"
    assert view.run("loop", "stop", "--reason", "interrupted").exit_code == 0
    assert view.run("loop", "begin").exit_code == 0


def test_m1_a_later_review_of_another_type_does_not_hide_a_blocker(
        bare_project):
    view = loop_view(bare_project)
    at_the_review_step(view)
    assert record_review(
        view, "gate_implement", "code-review", result="FAIL", actor="agent",
        findings=findings_file(view, [BLOCKER])).exit_code == 0
    assert len(fingerprints(view)) == 1
    # a later review of the same manifest, of another type, with no findings
    assert record_review(view, "gate_implement", "security-review",
                         actor="agent").exit_code == 0
    assert len(fingerprints(view)) == 1, "the code-review blocker still counts"


def test_m1_two_blockers_are_counted_and_a_resolved_one_is_not(bare_project):
    view = loop_view(bare_project)
    at_the_review_step(view)
    second = dict(BLOCKER, id="F2", location="src/app.py:40")
    assert record_review(
        view, "gate_implement", "code-review", result="FAIL", actor="agent",
        findings=findings_file(view, [BLOCKER, second])).exit_code == 0
    assert len(fingerprints(view)) == 2
    assert record_review(
        view, "gate_implement", "code-review", result="FAIL", actor="agent",
        findings=findings_file(
            view, [dict(BLOCKER, disposition="resolved"), second],
            "findings-2.json")).exit_code == 0
    assert len(fingerprints(view)) == 1


def newest_code_review_evidence(view) -> Path:
    ledger = json.loads((view.runtime / "reviews.json").read_text("utf-8"))
    record = [r for r in ledger["reviews"]
              if r["reviewType"] == "code-review"][-1]
    return view.root / record["evidenceId"]


def test_m1_missing_or_malformed_review_evidence_is_refused_not_empty(
        bare_project):
    view = loop_view(bare_project)
    at_the_review_step(view)
    assert record_review(
        view, "gate_implement", "code-review", result="FAIL", actor="agent",
        findings=findings_file(view, [BLOCKER])).exit_code == 0
    evidence = newest_code_review_evidence(view)
    original = evidence.read_text(encoding="utf-8")

    evidence.write_text("{ not json", encoding="utf-8")
    try:
        fingerprints(view)
    except sdle.IntegrityError as exc:
        assert exc.reason == "review_evidence_invalid"
    else:
        raise AssertionError("malformed evidence was read as no findings")

    evidence.unlink()
    try:
        fingerprints(view)
    except sdle.IntegrityError as exc:
        assert exc.reason == "review_evidence_invalid"
    else:
        raise AssertionError("missing evidence was read as no findings")
    evidence.write_text(original, encoding="utf-8")
    assert len(fingerprints(view)) == 1


def test_m1_evidence_that_disagrees_with_the_ledger_is_refused(bare_project):
    view = loop_view(bare_project)
    at_the_review_step(view)
    assert record_review(
        view, "gate_implement", "code-review", result="FAIL", actor="agent",
        findings=findings_file(view, [BLOCKER])).exit_code == 0
    evidence = newest_code_review_evidence(view)
    document = json.loads(evidence.read_text(encoding="utf-8"))
    document["findings"] = []          # the blocker "removed" from the file
    evidence.write_text(json.dumps(document), encoding="utf-8")
    try:
        fingerprints(view)
    except sdle.IntegrityError as exc:
        assert exc.reason == "review_evidence_invalid"
    else:
        raise AssertionError("an inconsistent file was trusted")


def test_m1_a_malformed_finding_in_the_evidence_is_a_structured_refusal(
        bare_project):
    """The counts still match, so only the shape check can catch it: it must
    be the engine's integrity refusal, never an unhandled exception, and
    nothing in the loop record may move."""
    view = loop_view(bare_project)
    at_the_review_step(view)
    assert record_review(
        view, "gate_implement", "code-review", result="FAIL", actor="agent",
        findings=findings_file(view, [BLOCKER])).exit_code == 0
    evidence = newest_code_review_evidence(view)
    document = json.loads(evidence.read_text(encoding="utf-8"))
    document["findings"][0]["obligations"] = 42   # counts are unchanged
    evidence.write_text(json.dumps(document), encoding="utf-8")
    loop_file = view.runtime / "implementation-loop.json"
    before = loop_file.read_bytes()
    try:
        fingerprints(view)
    except sdle.IntegrityError as exc:
        assert exc.reason == "review_evidence_invalid"
    else:
        raise AssertionError("a malformed finding was fingerprinted")
    shown = view.run("loop", "show")
    assert shown.exit_code in (0, 3), shown
    if shown.exit_code == 3:
        assert shown.reason == "review_evidence_invalid"
    assert loop_file.read_bytes() == before


def test_m1_loop_record_refuses_malformed_review_evidence_and_moves_nothing(
        bare_project):
    view = loop_view(bare_project)
    at_the_review_step(view)
    assert record_review(
        view, "gate_implement", "code-review", result="FAIL", actor="agent",
        findings=findings_file(view, [BLOCKER])).exit_code == 0
    view.ok("loop", "step", "--step", "review")
    view.ok("loop", "step", "--step", "converge")
    view.ok("loop", "step", "--step", "trace")
    evidence = newest_code_review_evidence(view)
    document = json.loads(evidence.read_text(encoding="utf-8"))
    document["findings"][0]["obligations"] = 42   # the counts are unchanged
    evidence.write_text(json.dumps(document), encoding="utf-8")
    loop_file = view.runtime / "implementation-loop.json"
    before = loop_file.read_bytes()
    refused = view.run("loop", "record")
    assert refused.exit_code == 3, refused
    assert refused.reason == "review_evidence_invalid"
    assert loop_file.read_bytes() == before

