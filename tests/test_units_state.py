"""State core: init, state get/dump, header, migrate, audit, lock."""

from __future__ import annotations

import json

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3


# -- init -------------------------------------------------------------------


def test_init_creates_state_and_advances_to_first_generation_phase(project):
    result = project.ok("init", session="s1")

    assert result.data["project_name"] == "Todo List REST API"
    assert result.data["current_phase"] == "constitution_draft"
    assert result.data["status"] == "pending"
    assert result.data["progress"] == "2/18"

    state = project.state()
    assert state["workflow_version"] == "1.17"
    assert state["workitem"] == project.workitem
    assert state["last_updated"] is not None
    assert [e["phase"] for e in state["phase_history"]] == ["requirements_check"]
    assert state["phase_history"][0]["outcome"] == "completed"


def test_init_infers_project_name_from_first_heading(project):
    result = project.ok("init")
    assert result.data["project_name"] == "Todo List REST API"


def test_init_explicit_project_name_wins(project):
    result = project.ok("init", "--project", "Something Else")
    assert result.data["project_name"] == "Something Else"


def test_init_refuses_without_requirements(project):
    for path in (project.root / "requirements").iterdir():
        path.unlink()
    result = project.run("init")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "requirements_missing"
    assert not project.state_file.exists(), "nothing is written on a refused bootstrap"


def test_init_refuses_when_already_initialized(started):
    result = started.run("init")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "already_initialized"


def test_init_writes_lock_when_session_given(project):
    project.ok("init", session="abc123")
    lock = (project.runtime / "lock").read_text(encoding="utf-8").strip()
    assert lock.endswith("abc123")


# -- state get / dump -------------------------------------------------------


def test_state_get_returns_full_state(started):
    result = started.ok("state", "get")
    assert result.data["current_phase"] == "constitution_draft"


def test_state_get_single_field(started):
    result = started.ok("state", "get", "--field", "status")
    assert result.data == {"field": "status", "value": "pending"}


def test_state_get_unknown_field_refuses(started):
    result = started.run("state", "get", "--field", "nope")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "unknown_field"


def test_state_get_without_state_is_integrity_failure(project):
    result = project.run("state", "get")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "state_unreadable"


def test_state_get_on_corrupt_json_is_integrity_failure(started):
    started.state_file.write_text("{not json", encoding="utf-8")
    result = started.run("state", "get")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "state_unreadable"


def test_state_dump_lists_every_gate(started):
    rendered = started.ok("state", "dump").data["rendered"]
    for key in (
        "gate_constitution",
        "gate_spec",
        "gate_plan",
        "gate_tasks",
        "gate_analyze",
        "gate_design",
        "gate_implement",
        "gate_security",
    ):
        assert key in rendered
    assert "## SDLE Workflow State" in rendered


# -- header -----------------------------------------------------------------


def test_header_renders_both_lines(started):
    rendered = started.ok("header").data["rendered"]
    lines = rendered.splitlines()
    assert lines[0] == (
        "<!-- SDLE_STATE phase=constitution_draft status=pending progress=2/18 -->"
    )
    assert lines[1] == "📋 SDLE Status: Phase 2/18 — Generate Constitution [PENDING]"


def test_header_maps_every_status_to_its_display_text(started):
    expected = {
        "pending": "[PENDING]",
        "in_progress": "[IN PROGRESS]",
        "awaiting_approval": "[AWAITING APPROVAL]",
        "awaiting_reapproval": "[AWAITING RE-APPROVAL (DRIFT DETECTED)]",
        "completed": "[COMPLETED]",
        "rejected": "[REJECTED — REMEDIATION NEEDED]",
        "failed": "[FAILED — ACTION REQUIRED]",
    }
    state = started.state()
    for status, display in expected.items():
        state["status"] = status
        started.write_state(state)
        assert started.ok("header").data["rendered"].endswith(display)


# -- migrate ----------------------------------------------------------------


def test_migrate_walks_the_whole_chain_from_1_0(started):
    state = started.state()
    state["workflow_version"] = "1.0"
    started.write_state(state)

    result = started.ok("migrate")
    assert result.data["from"] == "1.0"
    assert result.data["to"] == "1.17"
    assert result.data["steps"][0] == "1.0->1.1"
    assert result.data["steps"][-1] == "1.16->1.17"
    assert started.state()["workflow_version"] == "1.17"


def test_migrate_is_idempotent(started):
    first = started.ok("migrate")
    assert first.data["steps"] == []
    second = started.ok("migrate")
    assert second.data["steps"] == []


def test_migrate_refuses_unknown_version(started):
    state = started.state()
    state["workflow_version"] = "9.9"
    started.write_state(state)
    result = started.run("migrate")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "unknown_version"


def test_migrate_adds_implementation_base_ref(started):
    state = started.state()
    state["workflow_version"] = "1.12"
    del state["implementation_base_ref"]
    started.write_state(state)

    started.ok("migrate")
    assert started.state()["implementation_base_ref"] is None


def test_migrate_normalizes_uppercase_shas_from_powershell(started):
    """v1.12 recorded Get-FileHash output, which is uppercase. hashlib is
    lowercase. Without normalisation every approved gate false-drifts on the
    first v1.13 run."""
    upper = "3C9A61B2" + "F" * 56
    state = started.state()
    state["workflow_version"] = "1.12"
    state["artifact_shas"] = {"gate_constitution": upper}
    state["current_artifact_sha"] = upper
    started.write_state(state)

    result = started.ok("migrate")

    migrated = started.state()
    assert migrated["artifact_shas"]["gate_constitution"] == upper.lower()
    assert migrated["current_artifact_sha"] == upper.lower()
    assert "Normalised" in " ".join(result.data["notes"])


def test_migrate_1_8_warns_about_reordered_phases(started):
    state = started.state()
    state["workflow_version"] = "1.8"
    state["current_phase"] = "implement"
    started.write_state(state)

    result = started.ok("migrate")
    assert any("v1.8" in w for w in result.data["warnings"])


def test_migrate_1_8_recomputes_progress(started):
    state = started.state()
    state["workflow_version"] = "1.8"
    state["current_phase"] = "gate_design"
    state["progress"] = "6/14"
    started.write_state(state)

    started.ok("migrate")
    assert started.state()["progress"] == "14/18"


# -- audit ------------------------------------------------------------------


def test_audit_append_chains_entries_and_rebaselines(started):
    before = started.state()["audit_sha"]
    started.ok("audit", "append", "--phase", "constitution_draft",
               "--event", "phase_start", "--message", "Phase 2 started.")
    after = started.state()["audit_sha"]

    assert after != before
    text = started.audit_file.read_text(encoding="utf-8")
    assert text.count("## AUDIT ") >= 3
    assert "**Prev:** genesis" in text
    assert "Phase 2 started." in text


def test_audit_verify_passes_on_untouched_ledger(started):
    result = started.ok("audit", "verify")
    assert result.data["matches"] is True
    assert result.data["chain_ok"] is True
    assert result.data["entries"] >= 2


def test_audit_verify_detects_truncation(started):
    text = started.audit_file.read_text(encoding="utf-8")
    started.audit_file.write_text(text[: len(text) // 2], encoding="utf-8")

    result = started.run("audit", "verify")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "audit_chain_broken"
    assert result.data["matches"] is False


def test_audit_verify_detects_a_deleted_middle_entry(started):
    """The whole-file hash catches any edit; the per-entry chain says where."""
    started.ok("audit", "append", "--phase", "constitution_draft",
               "--event", "note", "--message", "Second.")
    started.ok("audit", "append", "--phase", "constitution_draft",
               "--event", "note", "--message", "Third.")

    entries = started.audit_file.read_text(encoding="utf-8").split("## AUDIT ")
    kept = [entries[0]] + ["## AUDIT " + e for e in entries[1:] if "Second." not in e]
    started.audit_file.write_text("".join(kept), encoding="utf-8")

    result = started.run("audit", "verify")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.data["chain_ok"] is False
    assert result.data["broken_at_entry"] is not None


def test_audit_verify_reports_missing_file(started):
    started.audit_file.unlink()
    result = started.run("audit", "verify")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.data["actual"] == "FILE_MISSING"


def test_audit_verify_skips_when_no_baseline(started):
    state = started.state()
    state["audit_sha"] = None
    started.write_state(state)
    result = started.ok("audit", "verify")
    assert result.data["matches"] is True


def test_audit_rebaseline_is_itself_logged(started):
    started.audit_file.write_text("tampered\n", encoding="utf-8")
    started.ok("audit", "rebaseline")

    text = started.audit_file.read_text(encoding="utf-8")
    assert "acknowledged audit integrity mismatch" in text
    assert started.ok("audit", "verify").data["matches"] is True


# -- lock -------------------------------------------------------------------


def test_lock_acquire_reports_a_fresh_foreign_lock(started):
    started.ok("lock", "acquire", session="other")
    result = started.ok("lock", "acquire", session="mine")

    assert result.data["foreign"] is True
    assert result.data["fresh"] is True
    assert result.data["warn"] is True
    assert result.exit_code == EXIT_OK, "v1.12 semantics: warn, never halt"


def test_lock_acquire_on_own_lock_is_not_foreign(started):
    started.ok("lock", "acquire", session="mine")
    result = started.ok("lock", "acquire", session="mine")
    assert result.data["foreign"] is False
    assert result.data["warn"] is False


def test_lock_acquire_ignores_a_stale_foreign_lock(started):
    (started.runtime / "lock").write_text(
        "2020-01-01T00:00:00Z deadbeef\n", encoding="utf-8"
    )
    result = started.ok("lock", "acquire", session="mine")
    assert result.data["foreign"] is True
    assert result.data["fresh"] is False
    assert result.data["warn"] is False


def test_lock_acquire_requires_a_session(started):
    result = started.run("lock", "acquire")
    assert result.exit_code == EXIT_USAGE
    assert result.reason == "session_required"


def test_lock_release_removes_the_file(started):
    started.ok("lock", "acquire", session="mine")
    assert (started.runtime / "lock").exists()
    started.ok("lock", "release")
    assert not (started.runtime / "lock").exists()


# -- sha --------------------------------------------------------------------


def test_sha_is_lowercase_hex(started):
    started.write_artifact("artifact.md")
    sha = started.ok("sha", "artifact.md").data["sha256"]
    assert sha == sha.lower()
    assert len(sha) == 64


def test_sha_refuses_missing_file(started):
    result = started.run("sha", "nope.md")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "artifact_missing"


# -- envelope / usage -------------------------------------------------------


def test_usage_error_exits_two_without_traceback(project):
    result = project.run("no-such-subcommand")
    assert result.exit_code == EXIT_USAGE
    assert "Traceback" not in result.stderr


def test_every_response_is_a_json_envelope(started):
    result = started.ok("header")
    payload = json.loads(result.stdout)
    assert set(payload) >= {"ok", "command", "reason", "data"}
