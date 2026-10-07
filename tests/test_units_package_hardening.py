"""Hardening of the requirements-package surface (ADR-016) found by the
independent implementation review: containment, atomic revisions, ledger
structure, identity history, the adoption path and the pin at every site that
moves a WorkItem.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time

import pytest

from conftest import sdle
from package_support import (
    PACKAGE_ID, base_files, edit_manifest, import_package, offender_rules,
    stage_package)
from test_units_artifact_review import frozen
from test_units_package_approval import (
    approve, approved_and_assessed, intake, ledger_path, package_file, reimport,
    started)

EXIT_REFUSED = 1
EXIT_INTEGRITY = 3


def validate(project, staging=True):
    args = ["package", "validate", "--package", PACKAGE_ID]
    if staging:
        args.append("--staging")
    return project.run(*args)


def link_or_skip(target, source, directory=False):
    """A symlink, or on Windows a directory junction, which needs no
    privilege. Skips only where neither can be made."""
    try:
        os.symlink(source, target, target_is_directory=directory)
        return
    except (OSError, NotImplementedError):
        pass
    if directory and os.name == "nt":
        done = subprocess.run(["cmd", "/c", "mklink", "/J", str(target),
                               str(source)], capture_output=True)
        if done.returncode == 0:
            return
    pytest.skip("this platform cannot create links here")


# ---- links and containment ---------------------------------------------------


def test_a_symlink_inside_a_package_is_refused(bare_project):
    staging, _ = stage_package(bare_project)
    outside = bare_project.root / "outside.md"
    outside.write_text("# outside\n", encoding="utf-8")
    link_or_skip(staging / "leak.md", outside)
    result = validate(bare_project)
    assert result.reason == "package_invalid"
    assert "package_symlink_refused" in offender_rules(result)
    assert bare_project.run("package", "import", "--package",
                            PACKAGE_ID).exit_code == EXIT_REFUSED
    assert not (bare_project.root / "requirements" / "packages").exists()


def test_a_linked_directory_inside_a_package_is_refused(bare_project, tmp_path):
    staging, _ = stage_package(bare_project)
    other = bare_project.root / "other-dir"
    other.mkdir()
    (other / "x.md").write_text("# x" + chr(10), encoding="utf-8")
    link_or_skip(staging / "linked", other, directory=True)
    result = validate(bare_project)
    assert result.reason == "package_invalid"
    assert "package_symlink_refused" in offender_rules(result)


def test_a_symlinked_package_directory_is_not_followed(bare_project):
    import_package(bare_project)
    elsewhere = bare_project.root / "elsewhere"
    packages = bare_project.root / "requirements" / "packages"
    real = packages / PACKAGE_ID
    real.rename(elsewhere)
    link_or_skip(real, elsewhere, directory=True)
    for args in (("package", "validate", "--package", PACKAGE_ID),
                 ("package", "approve", "--package", PACKAGE_ID, "--approver",
                  "A", "--role", "SA", "--wording", "ok"),
                 ("package", "reseal", "--package", PACKAGE_ID),
                 ("package", "intake", "--package", PACKAGE_ID)):
        result = bare_project.run(*args)
        assert result.reason == "package_path_invalid", (args, result)


def test_replacing_a_package_never_deletes_outside_it(bare_project):
    import_package(bare_project)
    victim = bare_project.root / "precious.md"
    victim.write_text("# keep me\n", encoding="utf-8")
    target = bare_project.root / "requirements" / "packages" / PACKAGE_ID
    link_or_skip(target / "docs-link", victim)
    stage_package(bare_project)
    result = bare_project.run("package", "import", "--package", PACKAGE_ID,
                              "--replace")
    assert victim.read_text(encoding="utf-8") == "# keep me\n"
    assert result.exit_code in (0, EXIT_REFUSED)


@pytest.mark.parametrize("path", ["/etc/passwd", "../outside.md",
                                  "C:/Windows/win.ini", "docs//srs.md"])
def test_a_source_path_that_is_not_a_plain_relative_path_is_refused(
        bare_project, path):
    def mutate(doc, files):
        doc["sources"][0]["path"] = path
        for row in doc["requirements"]:
            if "source" in row:
                row["source"]["document"] = path
    stage_package(bare_project, mutate)
    result = validate(bare_project)
    assert result.reason == "package_invalid"
    assert "package_manifest_invalid" in offender_rules(result)


@pytest.mark.parametrize("path", ["../escape.md", "/abs.md", "a/../b.md"])
def test_a_declared_file_path_cannot_leave_the_package(bare_project, path):
    def mutate(doc, files):
        files["x.md"] = "# x\n\ncontent\n"
        doc["files"] = [{"path": rel, "role": "supporting",
                         "sha256": hashlib.sha256(b"x").hexdigest()}
                        for rel in files]
        doc["files"].append({"path": path, "role": "supporting",
                             "sha256": hashlib.sha256(b"y").hexdigest()})
    stage_package(bare_project, mutate, seal=False)
    assert "package_manifest_invalid" in offender_rules(validate(bare_project))


# ---- id patterns cannot hang the engine -----------------------------------------


@pytest.mark.parametrize("pattern", ["(a+)+b", "(?:a|aa)+", "a*", "(?=x)y",
                                     ".+", "[a-z]+", "\\bFR-\\d+", "a|b"])
def test_an_id_pattern_outside_the_closed_language_is_refused(
        bare_project, pattern):
    stage_package(bare_project,
                  lambda d, f: d["idGrammar"].update(extra=pattern))
    assert "package_manifest_invalid" in offender_rules(validate(bare_project))


def test_an_adversarial_traceability_text_cannot_stall_validation(
        bare_project):
    def mutate(doc, files):
        files["traceability.md"] += ("a" * 200_000) + "\n"
    stage_package(bare_project, mutate)
    started_at = time.monotonic()
    validate(bare_project)
    assert time.monotonic() - started_at < 10


def test_an_oversized_traceability_file_is_refused_rather_than_scanned(
        bare_project):
    def mutate(doc, files):
        files["traceability.md"] += "x" * (sdle.PACKAGE_TEXT_MAX + 1)
    stage_package(bare_project, mutate)
    assert "package_file_too_large" in offender_rules(validate(bare_project))


# ---- revisions are whole or absent -------------------------------------------


def test_a_crash_while_copying_a_revision_leaves_no_revision_and_a_retry_works(
        bare_project, monkeypatch):
    import_package(bare_project)
    real = sdle._copy_package_tree
    calls = {"n": 0}

    def crash_midway(source, target):
        calls["n"] += 1
        files = sdle.package_files_on_disk(source)
        first = files[0]
        sdle.write_atomic(target / first,
                          (source / first).read_text(encoding="utf-8"))
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(sdle, "_copy_package_tree", crash_midway)
    with pytest.raises(RuntimeError):
        approve_args = ("package", "approve", "--package", PACKAGE_ID,
                        "--approver", "A", "--role", "SA", "--wording", "ok")
        bare_project.run(*approve_args)
    revisions = (bare_project.root / ".sdle" / "package-approvals"
                 / PACKAGE_ID / "revisions")
    digest = sdle.package_digest(
        bare_project.root / "requirements" / "packages" / PACKAGE_ID)
    assert not (revisions / digest).exists()
    assert not ledger_path(bare_project).exists()

    monkeypatch.setattr(sdle, "_copy_package_tree", real)
    approve(bare_project)
    assert sdle.package_digest(revisions / digest) == digest


def test_a_stored_revision_that_no_longer_matches_its_digest_is_an_integrity_failure(
        bare_project):
    import_package(bare_project)
    approve(bare_project)
    digest = bare_project.ok("package", "show", "--package",
                             PACKAGE_ID).data["digest"]
    revision = (bare_project.root / ".sdle" / "package-approvals" / PACKAGE_ID
                / "revisions" / digest)
    (revision / "overview.md").write_text("# tampered\n", encoding="utf-8")
    stage_package(bare_project, lambda d, f: f.update(
        {"open-issues.md": f["open-issues.md"] + "\nx\n"}))
    result = bare_project.run("package", "import", "--package", PACKAGE_ID,
                              "--replace")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "package_approvals_invalid"


def test_two_writers_cannot_overwrite_each_others_approval(bare_project,
                                                           monkeypatch):
    """A paused writer whose lock was broken must not erase the approval the
    second writer recorded in the meantime."""
    import_package(bare_project)
    real = sdle._publish_revision

    def other_writer_got_in(paths, root, package_id, digest):
        real(paths, root, package_id, digest)
        records = sdle.read_package_ledger(paths, package_id)
        record = {"n": 1, "package": package_id, "digest": digest,
                  "approver": "Other", "role": "SA",
                  "approvedAt": sdle.now_iso(), "wording": "ok",
                  "prev": "0" * 64}
        record["hash"] = sdle._ledger_record_hash(record)
        sdle.write_atomic(paths.package_ledger_file(package_id), json.dumps(
            {"ledgerVersion": "1", "package": package_id,
             "records": records + [record]}))

    monkeypatch.setattr(sdle, "_publish_revision", other_writer_got_in)
    result = bare_project.run("package", "approve", "--package", PACKAGE_ID,
                              "--approver", "Slow", "--role", "SA",
                              "--wording", "ok")
    assert result.reason == "package_locked"
    doc = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))
    assert [r["approver"] for r in doc["records"]] == ["Other"]


# ---- the ledger is structurally validated --------------------------------------


def test_a_correctly_hashed_record_missing_a_field_is_an_integrity_failure(
        bare_project):
    import_package(bare_project)
    approve(bare_project)
    doc = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))
    record = doc["records"][0]
    del record["digest"]
    record["hash"] = sdle._ledger_record_hash(record)
    ledger_path(bare_project).write_text(json.dumps(doc), encoding="utf-8")
    result = bare_project.run("package", "show", "--package", PACKAGE_ID)
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "package_approvals_invalid"


@pytest.mark.parametrize("field,value", [("approver", ""), ("role", 5),
                                         ("package", "other"),
                                         ("digest", "not-hex")])
def test_every_ledger_field_is_checked(bare_project, field, value):
    import_package(bare_project)
    approve(bare_project)
    doc = json.loads(ledger_path(bare_project).read_text(encoding="utf-8"))
    doc["records"][0][field] = value
    doc["records"][0]["hash"] = sdle._ledger_record_hash(doc["records"][0])
    ledger_path(bare_project).write_text(json.dumps(doc), encoding="utf-8")
    assert bare_project.run("package", "show", "--package",
                            PACKAGE_ID).exit_code == EXIT_INTEGRITY


# ---- identity history across revisions -----------------------------------------


def test_a_retirement_cannot_be_dropped_by_a_later_revision(bare_project):
    def first(doc, files):
        doc["retired"].append({"id": "FR-900", "reason": "dropped",
                               "disposition": "withdrawn"})
        files["traceability.md"] += "\nRetired: FR-900.\n"
    import_package(bare_project, first)
    approve(bare_project)

    def second(doc, files):
        files["traceability.md"] += "\nnote\n"
    result = reimport(bare_project, second)
    assert "package_retirement_dropped" in offender_rules(result)


def test_an_approved_requirement_cannot_change_kind_under_the_same_id(
        bare_project):
    import_package(bare_project)
    approve(bare_project)

    def mutate(doc, files):
        next(r for r in doc["requirements"]
             if r["id"] == "FR-001")["kind"] = "business_rule"
    assert "package_id_changed_kind" in offender_rules(
        reimport(bare_project, mutate))


# ---- the handoff binding is exact ------------------------------------------------


def test_a_binding_that_omits_a_cited_shared_file_is_refused_at_init(
        bare_project):
    import_package(bare_project)
    view = intake(bare_project)
    prefix = f"requirements/packages/{PACKAGE_ID}/"
    view.ok("requirements", "bind", "--source",
            prefix + "work-items/WI-001-orders/requirements.md")
    view.record_governance()
    approve(bare_project)
    result = view.run("init")
    assert result.reason == "package_binding_invalid"
    assert result.data["missing"] == [prefix + "system-context.md"]


# ---- adoption (R1-005, R1-006) ----------------------------------------------------


def test_adoption_requires_a_new_assessment_before_progress(bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    stage_package(bare_project, lambda d, f: f.update(
        {"open-issues.md": f["open-issues.md"] + "\nreviewed\n"}))
    bare_project.ok("package", "import", "--package", PACKAGE_ID, "--replace")
    approve(bare_project)
    view.ok("package", "adopt")
    before = frozen(view)
    assert view.run("advance", "--to",
                    "gate_constitution").reason == "package_reassessment_required"
    assert frozen(view) == before
    view.record_governance()
    assert view.ok("advance", "--to", "gate_constitution").exit_code == 0


def test_adopting_a_revision_that_makes_the_work_item_not_ready_is_refused(
        bare_project):
    view = started(bare_project)

    def mutate(doc, files):
        doc["workItems"][0]["readiness"] = "NOT_READY"
        doc["openIssues"][0]["affects"].append("WI-001")
        files["work-items/WI-001-orders/requirements.md"] += "\nNOT READY\n"
    stage_package(bare_project, mutate)
    bare_project.ok("package", "import", "--package", PACKAGE_ID, "--replace")
    approve(bare_project)
    result = view.run("package", "adopt")
    assert result.reason == "package_workitem_not_ready"


def test_adopting_an_unmoved_revision_changes_nothing_and_needs_no_assessment(
        bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    adopted = view.ok("package", "adopt")
    assert adopted.data["moved"] is False
    pin = json.loads((view.runtime / "package-binding.json").read_text(
        encoding="utf-8"))
    assert "reassessAfter" not in pin
    assert view.ok("advance", "--to", "gate_constitution").exit_code == 0


# ---- the pin at the sites that move a WorkItem (R1-007) ---------------------------


def move_package(project):
    package_file(project, "open-issues.md").write_text(
        "# Open issues\n\nmoved after start\n", encoding="utf-8")


def test_gate_reject_is_refused_before_it_writes_when_the_package_moved(
        bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    view.record_governance()
    view.ok("advance", "--to", "gate_constitution")
    move_package(bare_project)
    before = frozen(view)
    result = view.run("gate", "reject", "--gate", "gate_constitution",
                      "--reason", "no")
    assert result.reason == "package_revision_changed"
    assert frozen(view) == before


def test_remediate_begin_is_refused_before_it_writes_when_the_package_moved(
        bare_project):
    view = started(bare_project)
    move_package(bare_project)
    before = frozen(view)
    result = view.run("remediate", "begin", "--gate", "gate_constitution")
    assert result.reason == "package_revision_changed"
    assert frozen(view) == before


def test_drift_re_approval_is_refused_when_the_package_moved(bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    view.record_governance()
    view.ok("advance", "--to", "gate_constitution")
    state = view.state()
    state["drift_queue"] = ["gate_constitution"]
    view.write_state(state)
    move_package(bare_project)
    before = frozen(view)
    result = view.run("gate", "approve", "--gate", "gate_constitution")
    assert result.reason == "package_revision_changed"
    assert frozen(view) == before


def test_an_accepted_pattern_costs_time_linear_in_the_text(bare_project):
    """The closed language is deterministic, so even a long accepted pattern
    cannot be made to backtrack."""
    pattern = "(?:AB|CD)-" + r"\d{2}" * 10 + "X"
    assert sdle._id_pattern_problem(pattern) is None
    hostile = ("AB-" + "9" * 200_000)
    started_at = time.monotonic()
    assert sdle.re.search(pattern, hostile) is None
    assert time.monotonic() - started_at < 2


def test_the_documented_grammar_forms_are_all_accepted():
    for pattern in ("(?:FR|AC)-[0-9]{3}", "WI-[0-9]{3}", "OI-[0-9]{3}",
                    r"ACC-\d{3}", "[A-Z]{2}-[0-9]{4}", r"(?:BR|FR)-\d{3}"):
        assert sdle._id_pattern_problem(pattern) is None, pattern


# ---- round 2 of the implementation review -----------------------------------------


def test_adopting_twice_does_not_forget_a_reassessment_still_owed(
        bare_project):
    view = started(bare_project)
    view.write_artifact(".specify/memory/constitution.md")
    stage_package(bare_project, lambda d, f: f.update(
        {"open-issues.md": f["open-issues.md"] + "\nreviewed\n"}))
    bare_project.ok("package", "import", "--package", PACKAGE_ID, "--replace")
    approve(bare_project)
    view.ok("package", "adopt")
    again = view.ok("package", "adopt")
    assert again.data["moved"] is False
    assert view.run("advance", "--to", "gate_constitution").reason == (
        "package_reassessment_required")
    view.record_governance()
    assert view.ok("advance", "--to", "gate_constitution").exit_code == 0


def test_a_retired_id_cannot_also_be_a_work_item_or_an_issue_or_repeat(
        bare_project):
    def clash(doc, files):
        doc["retired"] = [
            {"id": "WI-001", "reason": "x", "disposition": "withdrawn"},
            {"id": "OI-001", "reason": "x", "disposition": "withdrawn"},
            {"id": "FR-900", "reason": "x", "disposition": "withdrawn"},
            {"id": "FR-900", "reason": "x", "disposition": "withdrawn"}]
        files["traceability.md"] += "\nFR-900.\n"
    stage_package(bare_project, clash)
    result = validate(bare_project)
    rules = [(o["rule"], o["subject"]) for o in result.data["offenders"]]
    assert ("package_id_reused", "WI-001") in rules
    assert ("package_id_reused", "OI-001") in rules
    assert ("package_id_duplicate", "retired") in rules


@pytest.mark.parametrize("key,value", [("files", 5), ("sources", 5),
                                       ("workItems", "x"),
                                       ("requirements", {"a": 1}),
                                       ("idGrammar", [])])
def test_a_manifest_field_of_the_wrong_type_is_a_refusal_not_a_crash(
        bare_project, key, value):
    stage_package(bare_project, lambda d, f: d.update({key: value}),
                  seal=False)
    result = validate(bare_project)
    assert result.reason == "package_invalid"
    assert "package_manifest_invalid" in offender_rules(result)


def test_a_shared_files_list_of_the_wrong_type_is_a_refusal_not_a_crash(
        bare_project):
    def mutate(doc, files):
        doc["workItems"][0]["sharedFiles"] = 5
    stage_package(bare_project, mutate)
    assert "package_manifest_invalid" in offender_rules(validate(bare_project))


def test_skip_is_refused_before_it_saves_a_pending_confirmation(
        bare_project):
    view = started(bare_project)
    state = view.state()
    state["status"] = "failed"
    view.write_state(state)
    move_package(bare_project)
    before = frozen(view)
    result = view.run("skip")
    assert result.reason == "package_revision_changed"
    assert frozen(view) == before


def test_the_package_lock_is_held_by_the_operating_system(bare_project,
                                                          monkeypatch):
    """A second command waits, then refuses; it never takes the lock from a
    live holder, however long that holder takes."""
    import_package(bare_project)
    monkeypatch.setattr(sdle, "PACKAGE_LOCK_TIMEOUT", 0.2)
    paths = sdle.resolve_paths(str(bare_project.root),
                               str(bare_project.skill_root))
    with sdle.package_ledger_lock(paths, PACKAGE_ID):
        result = bare_project.run("package", "approve", "--package",
                                  PACKAGE_ID, "--approver", "A", "--role",
                                  "SA", "--wording", "ok")
    assert result.reason == "package_locked"
    assert not ledger_path(bare_project).exists()
    assert approve(bare_project).exit_code == 0, "released after the holder"


def test_a_lock_file_left_by_a_dead_process_blocks_nothing(bare_project):
    import_package(bare_project)
    lock = (bare_project.root / ".sdle" / "package-approvals" / PACKAGE_ID
            / "ledger.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.write_text("1234 long ago\n", encoding="utf-8")
    assert approve(bare_project).exit_code == 0


def test_an_import_publishes_exactly_the_bytes_it_validated(bare_project,
                                                            monkeypatch):
    """Staging is unfenced and can be edited while an import runs. Whatever
    happens to it after the snapshot is taken cannot reach requirements/."""
    stage_package(bare_project)
    staging = bare_project.root / "package-staging" / PACKAGE_ID
    real = sdle.package_findings

    def mutate_staging_after_validation(paths, root, **kw):
        found = real(paths, root, **kw)
        (staging / "overview.md").write_text(
            "# Overview\n\nTAMPERED AFTER VALIDATION\n", encoding="utf-8")
        (staging / "smuggled.md").write_text("# s\n\nx\n", encoding="utf-8")
        return found

    monkeypatch.setattr(sdle, "package_findings",
                        mutate_staging_after_validation)
    result = bare_project.run("package", "import", "--package", PACKAGE_ID)
    assert result.exit_code == 0, result
    imported = bare_project.root / "requirements" / "packages" / PACKAGE_ID
    assert "TAMPERED" not in (imported / "overview.md").read_text(
        encoding="utf-8")
    assert not (imported / "smuggled.md").exists()
    monkeypatch.setattr(sdle, "package_findings", real)
    assert validate(bare_project, staging=False).exit_code == 0


def test_replacing_a_package_removes_a_planted_link_instead_of_writing_through_it(
        bare_project):
    import_package(bare_project)
    outside = bare_project.root / "outside-dir"
    outside.mkdir()
    target = bare_project.root / "requirements" / "packages" / PACKAGE_ID
    link_or_skip(target / "work-items-link", outside, directory=True)
    stage_package(bare_project, lambda d, f: f.update(
        {"open-issues.md": f["open-issues.md"] + "\nmore\n"}))
    result = bare_project.run("package", "import", "--package", PACKAGE_ID,
                              "--replace")
    assert result.reason == "package_invalid"
    assert "package_symlink_refused" in offender_rules(result)
    assert not list(outside.iterdir()), "nothing was written through it"


def test_approval_storage_behind_a_link_is_refused(bare_project):
    import_package(bare_project)
    elsewhere = bare_project.root / "elsewhere"
    elsewhere.mkdir()
    store = bare_project.root / ".sdle" / "package-approvals"
    store.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(store / PACKAGE_ID, ignore_errors=True)  # import made it
    link_or_skip(store / PACKAGE_ID, elsewhere, directory=True)
    for args in (("package", "approve", "--package", PACKAGE_ID,
                  "--approver", "A", "--role", "SA", "--wording", "ok"),
                 ("package", "show", "--package", PACKAGE_ID)):
        assert bare_project.run(*args).reason == "package_path_invalid"
    assert not list(elsewhere.iterdir())
