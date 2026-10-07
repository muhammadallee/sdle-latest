"""Traceability from a requirements package into the specification, the tasks
and the verification of each acceptance criterion (ADR-017, R2): AS-10, AS-11,
AS-12, AS-18, AS-19.

Every rule is inert for a WorkItem not started from a package; the
legacy suites are the proof of that. These tests are about the ones that are.
"""
from __future__ import annotations

import json

from test_units_artifact_review import frozen, review_for_gate
from trace_support import (
    FULL_SPEC, FULL_TASKS, PAD, build, build_junit, package_view, walk)


def approve(view, gate):
    review_for_gate(view, gate)
    return view.run("gate", "approve", "--gate", gate)


# ---- AS-10 / AS-11: the specification --------------------------------------


def test_as10_a_requirement_left_out_of_the_spec_refuses_the_spec_gate(
        bare_project):
    view = package_view(bare_project)
    spec = FULL_SPEC.replace("- FR-001 A clerk creates an order.\n", "")
    walk(view, "gate_spec", spec=spec)
    review_for_gate(view, "gate_spec")
    before = frozen(view)
    result = view.run("gate", "approve", "--gate", "gate_spec")
    assert result.reason == "trace_spec_incomplete"
    assert result.data["missing"] == ["FR-001"]
    assert frozen(view) == before, "a refusal moves nothing"


def test_a_spec_that_carries_every_in_scope_id_passes(bare_project):
    view = package_view(bare_project)
    walk(view, "gate_spec")
    assert approve(view, "gate_spec").exit_code == 0


def test_as11_a_spec_that_cites_an_unknown_id_is_refused(bare_project):
    view = package_view(bare_project)
    walk(view, "gate_spec", spec=FULL_SPEC + "- FR-999 invented\n")
    result = approve(view, "gate_spec")
    assert result.reason == "trace_unknown_id"
    assert result.data["unknown"] == ["FR-999"]


def test_a_requirement_of_another_work_item_may_be_cited_but_is_not_required(
        bare_project):
    view = package_view(bare_project)
    walk(view, "gate_spec", spec=FULL_SPEC + "- FR-002 belongs to WI-002\n")
    assert approve(view, "gate_spec").exit_code == 0


def test_an_approved_exclusion_lets_the_spec_omit_an_in_scope_requirement(
        bare_project):
    view = package_view(bare_project)
    view.ok("verification", "record", "--id", "FR-001", "--disposition",
            "excluded-approved", "--reason", "deferred to a later release",
            "--approver", "A. Architect", "--wording", "defer FR-001")
    walk(view, "gate_spec",
         spec=FULL_SPEC.replace("- FR-001 A clerk creates an order.\n", ""))
    assert approve(view, "gate_spec").exit_code == 0


def test_drift_re_approval_re_checks_the_trace(bare_project):
    """Re-approving drifted content is exactly when an obligation could have
    fallen out of it."""
    view = package_view(bare_project)
    walk(view, "gate_spec")
    assert approve(view, "gate_spec").exit_code == 0
    spec = view.root / view.feature_dir("001-todo-api") / "spec.md"
    spec.write_text(FULL_SPEC.replace("- NFR-001 Creation completes within "
                                      "two seconds.\n", ""),
                    encoding="utf-8")
    view.ok("drift", "check", "--queue")
    review_for_gate(view, "gate_spec")
    result = view.run("gate", "approve", "--gate", "gate_spec")
    assert result.reason == "trace_spec_incomplete"
    assert result.data["missing"] == ["NFR-001"]


# ---- AS-12 / AS-18: the tasks ------------------------------------------------


def test_as12_an_engineering_task_may_cite_an_obligation_tag_and_an_untraced_one_is_only_listed(
        bare_project):
    tasks = ("# Tasks\n\n"
             "- [ ] T001 Implement FR-001 and NFR-001\n"
             "- [ ] T002 Test AC-001 returns the order number\n"
             "- [ ] T003 Follow PRN-01 when logging, per AD-007\n"
             "- [ ] T004 Tidy the readme\n" + PAD)
    view = package_view(bare_project)
    walk(view, "gate_tasks", tasks=tasks)
    report = view.ok("trace", "check").data
    assert report["tasks"]["untraced"] == [
        {"line": 6, "text": "T004 Tidy the readme"}]
    assert report["tasks"]["obligationTagged"] == 1
    assert approve(view, "gate_tasks").exit_code == 0, (
        "an untraced task is listed, never blocking")


def test_as18_a_criterion_with_no_test_task_refuses_the_tasks_gate(
        bare_project):
    tasks = ("# Tasks\n\n- [ ] T001 Implement FR-001, AC-001 and NFR-001\n"
             + PAD)
    view = package_view(bare_project)
    walk(view, "gate_tasks", tasks=tasks)
    result = approve(view, "gate_tasks")
    assert result.reason == "trace_tasks_uncovered"
    assert result.data["withoutTestTask"] == ["AC-001"]


def test_a_criterion_no_task_cites_at_all_is_named(bare_project):
    tasks = "# Tasks\n\n- [ ] T001 Implement FR-001 and NFR-001\n" + PAD
    view = package_view(bare_project)
    walk(view, "gate_tasks", tasks=tasks)
    result = approve(view, "gate_tasks")
    assert result.reason == "trace_tasks_uncovered"
    assert result.data["withoutTask"] == ["AC-001"]


def test_a_task_that_cites_an_unknown_id_is_refused(bare_project):
    view = package_view(bare_project)
    walk(view, "gate_tasks", tasks=FULL_TASKS + "- [ ] T009 Test AC-777\n")
    assert approve(view, "gate_tasks").reason == "trace_unknown_id"


def test_an_omitted_tasks_gate_cannot_let_an_uncovered_criterion_through(
        bare_project):
    """`gate_tasks` is omittable at low risk, and HOTFIX has none. The
    omission itself is refused for uncovered tasks, and what happens to
    tasks.md after an omission (nothing watches it for drift) is re-checked at
    the one gate every flow must pass."""
    uncovered = ("# Tasks\n\n- [ ] T001 Implement FR-001 and NFR-001\n"
                 + PAD)
    view = package_view(bare_project)
    walk(view, "gate_tasks", tasks=uncovered)
    review_for_gate(view, "gate_tasks")
    refused = view.run("gate", "omit", "--gate", "gate_tasks")
    assert refused.reason == "trace_tasks_uncovered"

    tasks = view.root / view.feature_dir("001-todo-api") / "tasks.md"
    tasks.write_text(FULL_TASKS, encoding="utf-8")
    review_for_gate(view, "gate_tasks")
    assert view.run("gate", "omit", "--gate", "gate_tasks").exit_code == 0
    # nothing watches tasks.md now; the test task is quietly dropped
    tasks.write_text(uncovered, encoding="utf-8")
    walk(view, "gate_implement", start="analyze", spec=None, tasks=None)
    result = approve(view, "gate_implement")
    assert result.reason == "trace_tasks_uncovered"
    assert result.data["withoutTask"] == ["AC-001"]


# ---- the verification dispositions (AS-19) ------------------------------------------


def at_implement_gate(view, **kw):
    walk(view, "gate_implement", **kw)
    return view


def test_as19_a_passing_suite_that_names_no_criterion_is_unmapped_not_verified(
        bare_project):
    view = at_implement_gate(package_view(bare_project))
    shown = view.ok("verification", "show").data
    assert shown["unmapped"] == ["AC-001"]
    assert shown["verified"] == []
    assert shown["dispositions"] == {"AC-001": "suite-pass-unmapped"}
    assert approve(view, "gate_implement").exit_code == 0, (
        "non-blocking by default")


def test_a_policy_can_make_an_unmapped_pass_blocking(bare_project):
    view = package_view(bare_project)
    policy = view.root / ".sdle" / "policies" / "governance-policy.json"
    policy.parent.mkdir(parents=True, exist_ok=True)
    policy.write_text(json.dumps({"policyVersion": "1",
                                  "unmapped_verification_blocks": True}),
                      encoding="utf-8")
    at_implement_gate(view)
    result = approve(view, "gate_implement")
    assert result.reason == "trace_verification_unmapped"
    assert result.data["unmapped"] == ["AC-001"]


def test_a_junit_test_that_names_the_criterion_verifies_it(bare_project):
    view = at_implement_gate(package_view(bare_project))
    build_junit(view, ("test_AC-001_returns_the_order_number", True))
    mapped = view.ok("verification", "map")
    assert mapped.data["mapped"] == ["AC-001"]
    shown = view.ok("verification", "show").data
    assert shown["verified"] == ["AC-001"] and shown["unmapped"] == []
    assert approve(view, "gate_implement").exit_code == 0


def test_a_failing_mapped_test_blocks_the_criterion(bare_project):
    view = at_implement_gate(package_view(bare_project))
    build_junit(view, ("test_AC-001_returns_the_order_number", False))
    mapped = view.ok("verification", "map")
    assert mapped.data["blocked"] == ["AC-001"]
    result = approve(view, "gate_implement")
    assert result.reason == "trace_verification_missing"
    assert result.data["missing"] == ["AC-001"]


def test_a_mapping_stops_counting_when_the_evidence_is_rebuilt(bare_project):
    view = at_implement_gate(package_view(bare_project))
    build_junit(view, ("test_AC-001_returns_the_order_number", True))
    view.ok("verification", "map")
    assert view.ok("verification", "show").data["verified"] == ["AC-001"]
    build(view)
    shown = view.ok("verification", "show").data
    assert shown["verified"] == [], "a mapping is bound to the run it came from"
    assert shown["unmapped"] == ["AC-001"]


def test_a_failure_from_an_old_run_does_not_outlive_it(bare_project):
    view = at_implement_gate(package_view(bare_project))
    build_junit(view, ("test_AC-001_returns_the_order_number", False))
    view.ok("verification", "map")
    assert view.ok("verification", "show").data["blocked"] == ["AC-001"]
    build(view)  # a rebuilt, passing run replaces it
    shown = view.ok("verification", "show").data
    assert shown["blocked"] == []
    assert shown["unmapped"] == ["AC-001"]


def test_only_the_report_the_build_captured_can_be_mapped(bare_project):
    view = at_implement_gate(package_view(bare_project))
    assert view.run("verification", "map").reason == (
        "verification_junit_not_captured"), "nothing was captured"
    _, captured = build_junit(
        view, ("test_AC-001_returns_the_order_number", True))
    other = view.runtime / "evidence" / "elsewhere.xml"
    other.write_text("<testsuite/>", encoding="utf-8")
    refused = view.run("verification", "map", "--junit",
                       other.relative_to(view.root).as_posix())
    assert refused.reason == "verification_junit_not_captured"
    assert refused.data["captured"] == captured


def test_a_report_edited_after_it_was_captured_cannot_be_mapped(bare_project):
    view = at_implement_gate(package_view(bare_project))
    _, captured = build_junit(
        view, ("test_AC-001_returns_the_order_number", False))
    (view.root / captured).write_text(
        '<testsuite><testcase classname="s" '
        'name="test_AC-001_now_passes"/></testsuite>', encoding="utf-8")
    assert view.run("verification", "map").reason == (
        "verification_junit_changed")


def test_a_report_the_test_command_never_wrote_is_refused_at_the_build(
        bare_project):
    view = at_implement_gate(package_view(bare_project))
    result = view.run(
        "manifest", "build", "--test-command", build_junit.__globals__[
            "PASSING_TEST_COMMAND"], "--junit",
        view.runtime.relative_to(view.root).as_posix() + "/evidence/none.xml")
    assert result.reason == "manifest_junit_missing"


def test_a_criterion_with_no_passing_suite_has_no_disposition(bare_project):
    view = package_view(bare_project)
    walk(view, "implement")
    view.ok("implement", "preflight", "--bypass")
    view.ok("manifest", "build", "--summary", "Implemented.",
            "--skip-tests")
    view.ok("advance", "--to", "gate_implement")
    shown = view.ok("verification", "show").data
    assert shown["missing"] == ["AC-001"]


def test_verified_mapped_cannot_be_typed_in(bare_project):
    view = at_implement_gate(package_view(bare_project))
    result = view.run("verification", "record", "--id", "AC-001",
                      "--disposition", "verified-mapped")
    assert result.reason == "verification_mapped_is_derived"
    assert view.run("verification", "record", "--id", "AC-001",
                    "--disposition", "suite-pass-unmapped"
                    ).reason == "verification_unmapped_is_derived"


def test_manual_evidence_needs_a_file_and_an_exclusion_needs_an_approver(
        bare_project):
    view = at_implement_gate(package_view(bare_project))
    assert view.run("verification", "record", "--id", "AC-001",
                    "--disposition", "manual-evidence").exit_code == 2
    assert view.run("verification", "record", "--id", "AC-001",
                    "--disposition", "manual-evidence", "--evidence",
                    "missing.md").reason == "verification_evidence_missing"
    assert view.run("verification", "record", "--id", "AC-001",
                    "--disposition", "excluded-approved", "--reason", "r"
                    ).exit_code == 2
    (view.root / "evidence-note.md").write_text("# signed off\n",
                                                encoding="utf-8")
    ok = view.ok("verification", "record", "--id", "AC-001", "--disposition",
                 "manual-evidence", "--evidence", "evidence-note.md")
    assert ok.data["disposition"] == "manual-evidence"
    assert view.ok("verification", "show").data["verified"] == ["AC-001"]


def test_an_id_that_is_not_in_scope_cannot_be_recorded(bare_project):
    view = at_implement_gate(package_view(bare_project))
    assert view.run("verification", "record", "--id", "AC-002",
                    "--disposition", "blocked", "--reason", "x"
                    ).reason == "verification_id_unknown"


def test_junit_that_is_not_xml_is_a_usage_error(bare_project):
    view = at_implement_gate(package_view(bare_project))
    path = view.runtime / "evidence" / "bad.xml"
    path.parent.mkdir(parents=True, exist_ok=True)
    code = f"open({str(path)!r}, 'w').write('not xml')"
    from conftest import _command_line
    import sys
    view.ok("manifest", "build", "--test-command",
            _command_line([sys.executable, "-c", code]), "--junit",
            path.relative_to(view.root).as_posix())
    assert view.run("verification", "map").reason == (
        "verification_junit_invalid")


def test_the_verification_record_is_append_only_and_integrity_checked(
        bare_project):
    view = at_implement_gate(package_view(bare_project))
    view.ok("verification", "record", "--id", "AC-001", "--disposition",
            "blocked", "--reason", "waiting on the environment")
    target = view.runtime / "verification.json"
    document = json.loads(target.read_text(encoding="utf-8"))
    assert [r["disposition"] for r in document["records"]] == ["blocked"]
    document["workitem"] = "someone-else"
    target.write_text(json.dumps(document), encoding="utf-8")
    result = view.run("verification", "show")
    assert result.exit_code == 3
    assert result.reason == "verification_record_invalid"


# ---- the rebaseline door (G04) --------------------------------------------------------


def test_a_package_work_item_cannot_have_a_baseline_moved_by_hand(
        bare_project):
    view = package_view(bare_project)
    walk(view, "analyze")
    tasks = view.root / view.feature_dir("001-todo-api") / "tasks.md"
    tasks.write_text(FULL_TASKS + "- [ ] T009 sneaked in\n", encoding="utf-8")
    result = view.run("drift", "rebaseline", "--gate", "gate_tasks")
    assert result.reason == "rebaseline_not_permitted"
    drifted = view.ok("drift", "check").data["drifted"]
    assert [d["gate"] if isinstance(d, dict) else d for d in drifted] == [
        "gate_tasks"]


# ---- inert without a package -------------------------------------------------------------


def test_trace_and_verification_say_they_do_not_apply_to_a_legacy_work_item(
        started):
    assert started.ok("trace", "check").data["applies"] is False
    assert started.ok("verification", "show").data["applies"] is False
    result = started.run("verification", "record", "--id", "FR-001",
                         "--disposition", "blocked", "--reason", "x")
    assert result.reason == "verification_not_applicable"


# ---- the verification record cannot be forged or edited ---------------------------------


def test_a_fabricated_exclusion_without_an_approver_is_refused_on_read(
        bare_project):
    view = at_implement_gate(package_view(bare_project))
    target = view.runtime / "verification.json"
    target.write_text(json.dumps({
        "verificationVersion": "1", "workitem": view.workitem,
        "records": [{"id": "AC-001", "disposition": "excluded-approved"}]}),
        encoding="utf-8")
    result = view.run("verification", "show")
    assert result.exit_code == 3
    assert result.reason == "verification_record_invalid"


def test_an_edited_or_removed_record_breaks_the_chain(bare_project):
    view = at_implement_gate(package_view(bare_project))
    for criterion in ("AC-001", "NFR-001"):
        view.ok("verification", "record", "--id", criterion, "--disposition",
                "blocked", "--reason", f"waiting on {criterion}")
    target = view.runtime / "verification.json"
    document = json.loads(target.read_text(encoding="utf-8"))
    edited = json.loads(json.dumps(document))
    edited["records"][0]["reason"] = "nothing is wrong"
    target.write_text(json.dumps(edited), encoding="utf-8")
    assert view.run("verification", "show").exit_code == 3
    removed = json.loads(json.dumps(document))
    del removed["records"][0]
    target.write_text(json.dumps(removed), encoding="utf-8")
    assert view.run("verification", "show").exit_code == 3


def test_two_verification_commands_cannot_interleave(bare_project,
                                                    monkeypatch):
    from conftest import sdle
    view = at_implement_gate(package_view(bare_project))
    monkeypatch.setattr(sdle, "PACKAGE_LOCK_TIMEOUT", 0.2)
    paths = sdle.dataclass_replace(
        sdle.resolve_paths(str(view.root), str(view.skill_root)),
        workitem=view.workitem)
    with sdle.workitem_mutation_lock(paths):
        result = view.run("verification", "record", "--id", "AC-001",
                          "--disposition", "blocked", "--reason", "x")
    assert result.reason == "workitem_locked"
    assert not (view.runtime / "verification.json").exists()
    assert view.ok("verification", "record", "--id", "AC-001",
                   "--disposition", "blocked", "--reason", "x"
                   ).exit_code == 0
