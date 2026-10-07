"""Requirements-package approval, handoff and pin (ADR-016, R1): AS-05 to AS-08.

The approval is an engine-written, hash-chained ledger bound to the package
digest; `init` refuses a package work item that is not covered by a current
approval; a started WorkItem is pinned to the revision it began under.
"""
from __future__ import annotations

import json

from conftest import sdle
from package_support import (
    PACKAGE_ID, base_document, edit_manifest, import_package, offender_rules,
    sha_text, stage_package)
from test_units_artifact_review import frozen

EXIT_REFUSED = 1
EXIT_INTEGRITY = 3
READY_WI = "orders-wi-001-orders"
NOT_READY_WI = "orders-wi-002-reports"


def ledger_path(project):
    return (project.root / ".sdle" / "package-approvals" / PACKAGE_ID
            / "ledger.json")


def package_file(project, relative):
    return (project.root / "requirements" / "packages" / PACKAGE_ID / relative)


def intake(project, which="WI-001"):
    result = project.ok("package", "intake", "--package", PACKAGE_ID,
                        "--work-item", which)
    return project.as_workitem(result.data["workitems"][0]["workitem"])


def approved_and_assessed(project, which="WI-001"):
    """Import, intake, assess, approve: a WorkItem ready for `init`."""
    assert import_package(project).exit_code == 0
    view = intake(project, which)
    view.record_governance()
    project.ok("package", "approve", "--package", PACKAGE_ID, "--approver",
               "A. Architect", "--role", "Solution Architect", "--wording",
               "approved")
    return view


def started(project):
    view = approved_and_assessed(project)
    view.ok("init", session="pkg")
    return view


# ---- approval and the ledger ------------------------------------------------


def test_approval_records_who_what_and_when_in_a_chained_ledger(bare_project):
    import_package(bare_project)
    result = bare_project.ok(
        "package", "approve", "--package", PACKAGE_ID, "--approver",
        "A. Architect", "--role", "Solution Architect", "--wording", "ok")
    assert result.data["approved"] and not result.data["replayed"]
    doc = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))
    (record,) = doc["records"]
    assert record["approver"] == "A. Architect"
    assert record["role"] == "Solution Architect"
    assert record["wording"] == "ok"
    assert record["prev"] == "0" * 64
    shown = bare_project.ok("package", "show", "--package", PACKAGE_ID).data
    assert shown["status"] == "approved"
    assert shown["digest"] == record["digest"]


def test_approving_the_same_digest_again_is_a_replay_not_a_second_record(
        bare_project):
    import_package(bare_project)
    for _ in range(2):
        result = bare_project.ok(
            "package", "approve", "--package", PACKAGE_ID, "--approver", "A",
            "--role", "SA", "--wording", "ok")
    assert result.data["replayed"] is True
    doc = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))
    assert len(doc["records"]) == 1


def test_an_approval_needs_the_approver_the_role_and_the_wording(bare_project):
    import_package(bare_project)
    result = bare_project.run("package", "approve", "--package", PACKAGE_ID,
                              "--approver", " ", "--role", "SA",
                              "--wording", "ok")
    assert result.exit_code == 2
    assert not ledger_path(bare_project).exists()


def test_an_invalid_package_cannot_be_approved(bare_project):
    import_package(bare_project)
    package_file(bare_project, "overview.md").write_text(
        "# changed\n", encoding="utf-8")
    result = bare_project.run("package", "approve", "--package", PACKAGE_ID,
                              "--approver", "A", "--role", "SA",
                              "--wording", "ok")
    assert result.reason == "package_invalid"
    assert "package_files_changed" in offender_rules(result)
    assert not ledger_path(bare_project).exists()


def test_a_ledger_edited_by_hand_is_an_integrity_failure_not_an_empty_one(
        bare_project):
    import_package(bare_project)
    bare_project.ok("package", "approve", "--package", PACKAGE_ID,
                    "--approver", "A", "--role", "SA", "--wording", "ok")
    doc = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))
    doc["records"][0]["approver"] = "Someone Else"
    ledger_path(bare_project).write_text(json.dumps(doc), encoding="utf-8")
    result = bare_project.run("package", "show", "--package", PACKAGE_ID)
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "package_approvals_invalid"


def test_the_ledger_is_outside_the_package_so_approval_leaves_the_digest(
        bare_project):
    import_package(bare_project)
    before = bare_project.ok("package", "show", "--package",
                             PACKAGE_ID).data["digest"]
    bare_project.ok("package", "approve", "--package", PACKAGE_ID,
                    "--approver", "A", "--role", "SA", "--wording", "ok")
    assert bare_project.ok("package", "show", "--package",
                           PACKAGE_ID).data["digest"] == before


def test_a_replaced_package_is_stale_and_its_approval_history_survives(
        bare_project):
    import_package(bare_project)
    bare_project.ok("package", "approve", "--package", PACKAGE_ID,
                    "--approver", "A", "--role", "SA", "--wording", "v1")
    first = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))

    def mutate(doc, files):
        files["open-issues.md"] += "\nA new note.\n"
    stage_package(bare_project, mutate)
    assert bare_project.ok("package", "import", "--package", PACKAGE_ID,
                           "--replace").data["status"] == "stale"
    bare_project.ok("package", "approve", "--package", PACKAGE_ID,
                    "--approver", "A", "--role", "SA", "--wording", "v2")
    second = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))
    assert second["records"][0] == first["records"][0]
    assert [r["n"] for r in second["records"]] == [1, 2]
    assert second["records"][1]["prev"] == first["records"][0]["hash"]


def test_importing_over_an_existing_package_needs_replace(bare_project):
    import_package(bare_project)
    stage_package(bare_project, lambda d, f: f.update(
        {"open-issues.md": f["open-issues.md"] + "\nmore\n"}))
    result = bare_project.run("package", "import", "--package", PACKAGE_ID)
    assert result.reason == "package_exists"


def test_importing_an_identical_package_is_a_no_op(bare_project):
    import_package(bare_project)
    stage_package(bare_project)
    result = bare_project.ok("package", "import", "--package", PACKAGE_ID)
    assert result.data["unchanged"] is True


# ---- approved revisions and ID history (R1-006) -----------------------------


def reimport(project, mutate):
    stage_package(project, mutate)
    return project.run("package", "import", "--package", PACKAGE_ID,
                       "--replace")


def approve(project):
    return project.ok("package", "approve", "--package", PACKAGE_ID,
                      "--approver", "A", "--role", "SA", "--wording", "ok")


def test_an_approved_id_cannot_silently_disappear(bare_project):
    import_package(bare_project)
    approve(bare_project)

    def mutate(doc, files):
        doc["requirements"] = [r for r in doc["requirements"]
                               if r["id"] != "FR-003"]
        doc["exclusions"] = []
        files["traceability.md"] = files["traceability.md"].replace(
            "| FR-003 | excluded |\n", "")
    result = reimport(bare_project, mutate)
    assert result.reason == "package_invalid"
    assert "package_id_retired_without_successor" in offender_rules(result)


def test_an_approved_id_cannot_move_to_another_work_item(bare_project):
    import_package(bare_project)
    approve(bare_project)

    def mutate(doc, files):
        next(r for r in doc["requirements"]
             if r["id"] == "FR-001")["workItem"] = "WI-002"
    result = reimport(bare_project, mutate)
    assert "package_id_moved" in offender_rules(result)


def test_a_retired_id_stays_retired_across_revisions(bare_project):
    def first(doc, files):
        doc["retired"].append({"id": "FR-900", "reason": "dropped",
                               "disposition": "withdrawn"})
        files["traceability.md"] += "\nRetired: FR-900.\n"
    import_package(bare_project, first)
    approve(bare_project)

    def second(doc, files):
        doc["retired"].append({"id": "FR-900", "reason": "dropped",
                               "disposition": "withdrawn"})
        doc["requirements"].append({
            "id": "FR-900", "kind": "functional", "status": "draft",
            "statement": "Reused id.", "workItem": "WI-001",
            "source": dict(doc["requirements"][0]["source"])})
        files["traceability.md"] += "\nRetired: FR-900.\n"
    result = reimport(bare_project, second)
    assert "package_id_reused" in offender_rules(result)


def test_a_legitimate_retirement_with_a_successor_is_accepted(bare_project):
    import_package(bare_project)
    approve(bare_project)

    def mutate(doc, files):
        doc["requirements"] = [r for r in doc["requirements"]
                               if r["id"] != "FR-001"]
        doc["retired"].append({"id": "FR-001", "reason": "split",
                               "disposition": "superseded"})
        doc["requirements"].append({
            "id": "FR-004", "kind": "functional", "status": "confirmed",
            "statement": "A clerk can create an order (replaces FR-001).",
            "supersedes": ["FR-001"], "workItem": "WI-001",
            "source": {"document": "docs/source/srs.md", "anchor": "3.1"}})
        files["traceability.md"] += "\nFR-004 replaces FR-001.\n"
    assert reimport(bare_project, mutate).exit_code == 0


def test_the_approved_revision_is_stored_so_the_diff_does_not_need_git(
        bare_project):
    import_package(bare_project)
    approve(bare_project)
    digest = bare_project.ok("package", "show", "--package",
                             PACKAGE_ID).data["digest"]
    revision = (bare_project.root / ".sdle" / "package-approvals" / PACKAGE_ID
                / "revisions" / digest)
    assert (revision / "package.json").is_file()
    assert (revision / "overview.md").is_file()

    stage_package(bare_project, lambda d, f: f.update(
        {"open-issues.md": f["open-issues.md"] + "\nchanged line\n"}))
    bare_project.ok("package", "import", "--package", PACKAGE_ID, "--replace")
    shown = bare_project.ok("package", "show", "--package", PACKAGE_ID,
                            "--diff").data
    assert shown["status"] == "stale"
    changed = {c["path"]: c for c in shown["diff"]["changed"]}
    assert "open-issues.md" in changed
    assert any("changed line" in line
               for line in changed["open-issues.md"]["diff"])


# ---- the handoff check at init (AS-05, AS-06, AS-08) ---------------------------


def test_init_refuses_a_package_work_item_that_was_never_approved(
        bare_project):
    import_package(bare_project)
    view = intake(bare_project)
    view.record_governance()
    result = view.run("init")
    assert result.reason == "package_approval_missing"
    assert not view.state_file.exists()


def test_as05_a_file_edited_after_approval_makes_init_refuse_stale(
        bare_project):
    view = approved_and_assessed(bare_project)
    ledger_before = ledger_path(bare_project).read_bytes()
    package_file(bare_project, "open-issues.md").write_text(
        "# Open issues\n\nEdited after approval.\n", encoding="utf-8")
    result = view.run("init")
    assert result.reason == "package_approval_stale"
    assert not view.state_file.exists()
    assert ledger_path(bare_project).read_bytes() == ledger_before


def test_as06_a_not_ready_work_item_is_refused(bare_project):
    view = approved_and_assessed(bare_project, "WI-002")
    result = view.run("init")
    assert result.reason == "package_workitem_not_ready"
    assert not view.state_file.exists()


def test_a_ready_approved_package_work_item_starts_and_is_pinned(
        bare_project):
    view = started(bare_project)
    pin = json.loads((view.runtime / "package-binding.json").read_text(
        encoding="utf-8"))
    status = bare_project.ok("package", "show", "--package",
                             PACKAGE_ID).data
    assert pin["digest"] == status["digest"]
    assert pin["workItem"] == "WI-001"
    assert pin["workitem"] == view.workitem
    assert "package_pinned" in view.audit_file.read_text(encoding="utf-8")


def test_as08_the_developer_resumes_with_nothing_copied(bare_project):
    view = approved_and_assessed(bare_project)
    shown = view.ok("package", "show").data
    assert shown["package"] == PACKAGE_ID and shown["status"] == "approved"
    assert shown["latest"]["approver"] == "A. Architect"
    required = view.ok("requirements", "show").data
    assert required["package"]["package"] == PACKAGE_ID
    assert required["package"]["status"] == "approved"
    assert required["primary"] == (
        f"requirements/packages/{PACKAGE_ID}/work-items/WI-001-orders/"
        "requirements.md")
    assert required["sources"] == sorted(required["sources"])
    assert any(s.endswith("system-context.md") for s in required["sources"])


def test_a_binding_that_names_two_work_items_is_refused_at_init(bare_project):
    import_package(bare_project)
    view = intake(bare_project)
    prefix = f"requirements/packages/{PACKAGE_ID}/"
    view.ok("requirements", "bind", "--source",
            prefix + "work-items/WI-001-orders/requirements.md", "--source",
            prefix + "work-items/WI-002-reports/requirements.md",
            "--primary", prefix + "work-items/WI-001-orders/requirements.md")
    view.record_governance()
    approve(bare_project)
    assert view.run("init").reason == "package_binding_invalid"


def test_a_binding_mixing_a_package_with_outside_documents_is_refused(
        bare_project):
    import_package(bare_project)
    view = intake(bare_project)
    prefix = f"requirements/packages/{PACKAGE_ID}/"
    view.ok("requirements", "bind", "--source",
            prefix + "work-items/WI-001-orders/requirements.md", "--source",
            "requirements/todo-api.md", "--primary",
            prefix + "work-items/WI-001-orders/requirements.md")
    view.record_governance()
    approve(bare_project)
    assert view.run("init").reason == "package_binding_mixed"


# ---- the pin after init (R1-002) ------------------------------------------------


def test_a_package_change_after_init_stops_progression_before_any_write(
        bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    package_file(bare_project, "open-issues.md").write_text(
        "# Open issues\n\nUnbound file changed after init.\n",
        encoding="utf-8")
    before = frozen(view)
    result = view.run("advance", "--to", "gate_constitution")
    assert result.reason == "package_revision_changed"
    assert frozen(view) == before, "a refusal must not move anything"


def test_a_manifest_only_change_is_caught_although_governance_cannot_see_it(
        bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    edit_manifest(bare_project, lambda d: d.update(title="Renamed"))
    result = view.run("advance", "--to", "gate_constitution")
    assert result.reason == "package_revision_changed"


def test_skip_and_omit_and_approve_carry_the_pin_check_too(bare_project):
    view = started(bare_project)
    package_file(bare_project, "open-issues.md").write_text(
        "# Open issues\n\nchanged\n", encoding="utf-8")
    for command in (("skip",), ("skip", "--confirm"),
                    ("gate", "omit", "--gate", "gate_design"),
                    ("gate", "approve", "--gate", "gate_constitution")):
        before = frozen(view)
        result = view.run(*command)
        assert result.exit_code != 0
        assert result.reason in {"package_revision_changed", "not_failed",
                                 "not_at_gate", "no_pending_confirmation"}
        assert frozen(view) == before


def test_reassessment_alone_never_re_pins(bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    package_file(bare_project, "open-issues.md").write_text(
        "# Open issues\n\nchanged\n", encoding="utf-8")
    view.record_governance()
    assert view.run("advance", "--to",
                    "gate_constitution").reason == "package_revision_changed"


def test_adopting_a_newly_approved_revision_unblocks_progression(
        bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    stage_package(bare_project, lambda d, f: f.update(
        {"open-issues.md": f["open-issues.md"] + "\nan SA-reviewed note\n"}))
    bare_project.ok("package", "import", "--package", PACKAGE_ID, "--replace")
    assert view.run("advance", "--to",
                    "gate_constitution").reason == "package_revision_changed"
    assert view.run("package", "adopt").reason == "package_approval_stale"
    approve(bare_project)
    adopted = view.ok("package", "adopt")
    assert adopted.data["moved"] is True
    assert view.run("advance", "--to", "gate_constitution").reason == (
        "package_reassessment_required"), "adoption is not an assessment"
    view.record_governance()
    assert view.ok("advance", "--to", "gate_constitution").exit_code == 0
    assert "package_adopted" in view.audit_file.read_text(encoding="utf-8")


def test_a_pin_edited_by_hand_is_an_integrity_failure(bare_project):
    view = started(bare_project)
    target = view.runtime / "package-binding.json"
    doc = json.loads(target.read_text(encoding="utf-8"))
    doc["digest"] = "0" * 64
    target.write_text(json.dumps(doc), encoding="utf-8")
    result = view.run("package", "adopt")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "package_binding_invalid"


# ---- AS-07: refinement of an approved package file, then reseal -----------------------


def test_as07_refinement_of_an_approved_file_applies_and_says_it_is_stale(
        bare_project):
    from test_units_refinement_commands import (
        CHECK, accept, apply as refine_apply, assess, call, edit, evidence_of,
        proposal, sha)
    import_package(bare_project)
    approve(bare_project)
    view = intake(bare_project)
    prefix = f"requirements/packages/{PACKAGE_ID}/"
    primary = prefix + "work-items/WI-001-orders/requirements.md"
    assert assess(view, CHECK).reason == "requirements_quality_blocked"
    payload = proposal(view, edits=[edit(
        view, "e1", "append_section", None,
        "## Acceptance\n\n- AC-001: Creating an order returns its number.\n",
        path=primary)])
    assert call(view, "propose", payload).exit_code == 0
    accept(view)
    applied = refine_apply(view, "e1", base=sha(view, primary))
    assert applied.exit_code == 0, applied
    status = bare_project.ok("package", "show", "--package", PACKAGE_ID).data
    assert status["status"] == "stale", "the approval no longer covers it"
    check = bare_project.run("package", "validate", "--package", PACKAGE_ID)
    assert "package_files_changed" in offender_rules(check)
    resealed = bare_project.ok("package", "reseal", "--package", PACKAGE_ID)
    assert resealed.data["status"] == "stale"
    assert "package approve" in resealed.data["next"]
    assert bare_project.run("package", "validate", "--package",
                            PACKAGE_ID).exit_code == 0
    approve(bare_project)
    assert bare_project.ok("package", "show", "--package",
                           PACKAGE_ID).data["status"] == "approved"
    doc = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))
    assert len(doc["records"]) == 2, "history kept, nothing rewritten"


def test_reseal_refuses_a_manifest_damaged_beyond_its_file_digests(
        bare_project):
    import_package(bare_project)
    package_file(bare_project, "package.json").write_text(
        "{broken", encoding="utf-8")
    result = bare_project.run("package", "reseal", "--package", PACKAGE_ID)
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "package_manifest_invalid"


def test_reseal_refuses_and_restores_when_the_result_would_not_validate(
        bare_project):
    import_package(bare_project)
    approve(bare_project)
    before = package_file(bare_project, "package.json").read_bytes()
    edit_manifest(bare_project, lambda d: d["requirements"][0].pop("source"))
    broken = package_file(bare_project, "package.json").read_bytes()
    result = bare_project.run("package", "reseal", "--package", PACKAGE_ID)
    assert result.reason == "package_invalid"
    assert package_file(bare_project, "package.json").read_bytes() == broken
    assert broken != before


# ---- intake and the scope rules ---------------------------------------------


def test_intake_creates_one_bound_work_item_per_package_work_item(
        bare_project):
    import_package(bare_project)
    result = bare_project.ok("package", "intake", "--package", PACKAGE_ID)
    names = {w["workItem"]: w["workitem"] for w in result.data["workitems"]}
    assert names == {"WI-001": READY_WI, "WI-002": NOT_READY_WI}
    view = bare_project.as_workitem(READY_WI)
    shown = view.ok("requirements", "show").data
    assert shown["bound"] is True
    prefix = f"requirements/packages/{PACKAGE_ID}/"
    assert shown["primary"] == prefix + "work-items/WI-001-orders/requirements.md"
    assert prefix + "system-context.md" in shown["sources"]
    other = bare_project.as_workitem(NOT_READY_WI).ok(
        "requirements", "show").data
    assert prefix + "system-context.md" not in other["sources"]


def test_intake_is_idempotent(bare_project):
    import_package(bare_project)
    bare_project.ok("package", "intake", "--package", PACKAGE_ID)
    again = bare_project.ok("package", "intake", "--package", PACKAGE_ID)
    assert [w["created"] for w in again.data["workitems"]] == [False, False]


def test_intake_never_overwrites_a_different_binding(bare_project):
    import_package(bare_project)
    view = intake(bare_project)
    view.ok("requirements", "bind", "--source", "requirements/todo-api.md")
    result = bare_project.run("package", "intake", "--package", PACKAGE_ID,
                              "--work-item", "WI-001")
    assert result.reason == "package_intake_conflict"


def test_intake_needs_a_valid_package_and_a_known_work_item(bare_project):
    import_package(bare_project)
    assert bare_project.run("package", "intake", "--package", PACKAGE_ID,
                            "--work-item", "WI-999").exit_code == 2
    assert bare_project.run("package", "intake", "--package",
                            "missing").reason == "package_not_found"


def test_intake_needs_no_approval(bare_project):
    import_package(bare_project)
    assert bare_project.ok("package", "intake", "--package",
                           PACKAGE_ID).exit_code == 0


def test_bind_all_current_does_not_sweep_in_package_files(bare_project):
    import_package(bare_project)
    bare_project.ok("workitem", "create", "--name", "legacy")
    view = bare_project.as_workitem("legacy")
    bound = view.ok("requirements", "bind", "--all-current").data["sources"]
    assert bound == ["requirements/todo-api.md"]


def test_a_legacy_work_item_starts_exactly_as_before(started):
    """The compatibility rule: no package file bound, nothing new applies."""
    assert started.state()["current_phase"] == "constitution_draft"
    assert not (started.runtime / "package-binding.json").exists()
    shown = started.ok("requirements", "show").data
    assert shown["package"] is None


def test_the_engine_never_writes_a_package_into_a_fenced_place_by_staging(
        bare_project):
    """Staging is outside the fence by design; requirements/packages is not."""
    stage_package(bare_project)
    assert (bare_project.root / "package-staging" / PACKAGE_ID).is_dir()
    assert not (bare_project.root / "requirements" / "packages").exists()
    assert "package-staging/" in sdle.SDLE_OWNED_PREFIXES
    assert ".sdle/package-approvals/" in sdle.SDLE_OWNED_PREFIXES
