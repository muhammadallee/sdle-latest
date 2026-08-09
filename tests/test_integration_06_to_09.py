"""Integration 06-09, derived from the matching dry-run transcripts.

06 dirty-tree guard and secrets scan at Gate 7
07 audit integrity, session lock, repo staleness
08 restart, reset, forward-jump refusal, state jump
09 bootstrap failures
"""

from __future__ import annotations

import json

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3
FEATURE = "001-todo-api"


def at_implement(project):
    """Gates 1-6 approved, workflow standing at the implement phase."""
    project.ok("init", session="t")
    steps = [
        (".specify/memory/constitution.md", "gate_constitution"),
        (f".specify/specs/{FEATURE}/spec.md", "gate_spec"),
        (f".specify/specs/{FEATURE}/plan.md", "gate_plan"),
    ]
    for path, gate in steps:
        project.write_artifact(path)
        if gate == "gate_spec":
            project.ok("feature", "resolve")
        project.ok("advance", "--to", gate)
        project.ok("gate", "approve", "--gate", gate)

    project.write_artifact(f".specify/specs/{FEATURE}/checklist.md")
    project.ok("advance", "--to", "tasks_draft")
    project.write_artifact(f".specify/specs/{FEATURE}/tasks.md")
    project.ok("advance", "--to", "gate_tasks")
    project.ok("gate", "approve", "--gate", "gate_tasks")
    project.ok("advance", "--to", "gate_analyze")
    project.ok("gate", "approve", "--gate", "gate_analyze")
    project.write_artifact("design/app/app-design.md")
    project.ok("advance", "--to", "gate_design")
    project.ok("gate", "approve", "--gate", "gate_design")
    return project


# ===========================================================================
# 06 — dirty tree and secrets
# ===========================================================================


def test_06_dirty_tree_halts_implement(git_project):
    at_implement(git_project)
    (git_project.root / "notes").mkdir(exist_ok=True)
    (git_project.root / "notes" / "ideas.md").write_text("wip\n", encoding="utf-8")

    result = git_project.run("implement", "preflight")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "dirty_tree"
    # Listed as a file, not collapsed to the directory "notes/".
    assert any("notes/ideas.md" in e for e in result.data["entries"]), result.data
    assert git_project.state()["pending_confirm_action"] == "implement_dirty_tree"


def test_06_sdle_owned_paths_are_not_dirt(git_project):
    """Mid-workflow .specify/ and design/ are legitimately dirty."""
    at_implement(git_project)
    result = git_project.ok("implement", "preflight")
    assert result.data["dirty"] is False
    assert result.data["entries"] == []


def test_06_bypass_proceeds_and_is_logged(git_project):
    at_implement(git_project)
    (git_project.root / "notes.md").write_text("wip\n", encoding="utf-8")
    git_project.run("implement", "preflight")

    result = git_project.ok("implement", "preflight", "--bypass")
    assert result.data["bypassed"] is True
    assert git_project.state()["pending_confirm_action"] is None
    assert "despite" in git_project.audit_file.read_text("utf-8")


def test_06_preflight_pins_the_implementation_base_ref(git_project):
    """Item 3: Phase 17 must diff against this, not HEAD~1."""
    at_implement(git_project)
    result = git_project.ok("implement", "preflight")

    head = git_project.git("rev-parse", "HEAD").stdout.strip()
    assert result.data["base_ref"] == head
    assert git_project.state()["implementation_base_ref"] == head


def test_06_manifest_flags_a_hardcoded_key_masked(git_project):
    at_implement(git_project)
    git_project.write_artifact(
        "src/config.py",
        'import os\n\napi_key = "sk-proj-abcdefghijklmnopqrstuvwxyz012345"\n'
        + "# padding\n" * 20,
    )
    result = git_project.ok("manifest", "build", "--skip-tests")

    findings = result.data["secrets"]
    assert len(findings) == 1
    assert "src/config.py:3" in findings[0]
    assert "****(masked)" in findings[0]
    assert "abcdefghij" not in findings[0], "the secret is never reproduced in full"


def test_06_manifest_always_has_the_mandatory_sections(git_project):
    at_implement(git_project)
    git_project.ok("manifest", "build", "--skip-tests")

    body = (git_project.root / ".workflow" / "implementation-manifest.md").read_text(
        "utf-8"
    )
    assert "## Changed/Added Files" in body
    assert "## Potential Secrets Detected" in body
    assert "None detected." in body
    assert "## Test Evidence" in body


def test_06_gate_seven_refuses_a_manifest_without_scan_or_tests(git_project):
    """The choke point: a hook can be skipped, this refusal cannot."""
    at_implement(git_project)
    git_project.ok("implement", "preflight")
    git_project.write_artifact(
        ".workflow/implementation-manifest.md",
        "# Implementation Manifest\n\nLooks fine to me.\n" * 5,
    )
    git_project.ok("advance", "--to", "gate_implement")

    result = git_project.run("gate", "approve", "--gate", "gate_implement")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "manifest_incomplete"
    assert "## Test Evidence" in result.data["missing"]
    assert git_project.state()["approvals"]["gate_implement"] is None


def test_06_gate_seven_accepts_a_built_manifest(git_project):
    at_implement(git_project)
    git_project.ok("implement", "preflight")
    git_project.ok("manifest", "build", "--skip-tests")
    git_project.ok("advance", "--to", "gate_implement")

    result = git_project.ok("gate", "approve", "--gate", "gate_implement")
    assert result.data["next_phase"] == "security_review"


def test_06_test_evidence_records_a_real_failing_run(git_project):
    """Item 11: an implementation whose tests fail must say so in the manifest."""
    at_implement(git_project)
    tests_dir = git_project.root / "tests"
    tests_dir.mkdir(exist_ok=True)
    (tests_dir / "test_generated.py").write_text(
        "def test_it_works():\n    assert 1 == 2\n", encoding="utf-8"
    )

    result = git_project.ok("manifest", "build", "--test-timeout", "120")
    tests = result.data["tests"]

    assert tests["runner"] == "pytest"
    assert tests["exit_code"] not in (0, None)
    assert tests["status"] == "FAILED"

    body = (git_project.root / ".workflow" / "implementation-manifest.md").read_text(
        "utf-8"
    )
    assert "FAILED" in body
    assert "tests_failed" in git_project.audit_file.read_text("utf-8")


def test_06_security_review_diffs_against_the_pinned_ref(git_project):
    at_implement(git_project)
    git_project.ok("implement", "preflight")
    base = git_project.state()["implementation_base_ref"]

    result = git_project.ok("security-review", "evidence")
    assert result.data["base_ref"] == base
    assert result.data["pinned"] is True


def test_06_security_review_falls_back_when_no_ref_pinned(git_project):
    at_implement(git_project)
    result = git_project.ok("security-review", "evidence")
    assert result.data["pinned"] is False
    assert result.data["base_ref"] == "HEAD~1"


# ===========================================================================
# 07 — audit integrity, lock, staleness
# ===========================================================================


def test_07_edited_audit_halts_until_rebaselined(started):
    text = started.audit_file.read_text("utf-8")
    started.audit_file.write_text(
        text.replace("Workflow initialized", "Nothing to see here"), encoding="utf-8"
    )

    failed = started.run("audit", "verify")
    assert failed.exit_code == EXIT_INTEGRITY
    assert failed.reason == "audit_chain_broken"

    started.ok("audit", "rebaseline")
    assert started.ok("audit", "verify").data["matches"] is True


def test_07_the_mismatch_persists_until_acknowledged(started):
    started.audit_file.write_text("tampered\n", encoding="utf-8")
    assert started.run("audit", "verify").exit_code == EXIT_INTEGRITY
    assert started.run("audit", "verify").exit_code == EXIT_INTEGRITY, \
        "inspecting does not clear the mismatch"


def test_07_foreign_fresh_lock_warns_but_never_halts(started):
    started.ok("lock", "acquire", session="colleague")
    result = started.ok("lock", "acquire", session="me")
    assert result.exit_code == EXIT_OK, "v1.12 semantics: warn-only"
    assert result.data["warn"] is True


def test_07_staleness_is_scoped_to_recorded_artifact_paths(git_project):
    """A commit touching unrelated files must not make an approval stale."""
    git_project.ok("init", session="t")
    git_project.write_artifact(".specify/memory/constitution.md")
    git_project.git("add", "-A")
    git_project.git("commit", "-q", "-m", "constitution")
    git_project.ok("advance", "--to", "gate_constitution")
    git_project.ok("gate", "approve", "--gate", "gate_constitution")

    (git_project.root / "UNRELATED.md").write_text("noise\n", encoding="utf-8")
    git_project.git("add", "-A")
    git_project.git("commit", "-q", "-m", "unrelated change")
    assert git_project.ok("repo-staleness").data["stale"] is False

    git_project.write_artifact(".specify/memory/constitution.md", "# Changed\n" * 20)
    git_project.git("add", "-A")
    git_project.git("commit", "-q", "-m", "touch the approved artifact")
    assert git_project.ok("repo-staleness").data["stale"] is True


def test_07_staleness_is_silent_without_approvals(git_project):
    git_project.ok("init", session="t")
    assert git_project.ok("repo-staleness").data["stale"] is False


# ===========================================================================
# 08 — restart, reset, forward jump, state jump
# ===========================================================================


def at_gate_plan(project):
    project.ok("init", session="t")
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution")
    project.write_artifact(f".specify/specs/{FEATURE}/spec.md")
    project.ok("feature", "resolve")
    project.ok("advance", "--to", "gate_spec")
    project.ok("gate", "approve", "--gate", "gate_spec")
    project.write_artifact(f".specify/specs/{FEATURE}/plan.md")
    project.ok("advance", "--to", "gate_plan")
    return project


def test_08_restart_is_two_step_and_rolls_back(project):
    at_gate_plan(project)

    first = project.ok("restart", "--to", "6")
    assert first.data["pending"] is True
    assert project.state()["current_phase"] == "gate_plan", "nothing moved yet"

    second = project.ok("restart", "--to", "6", "--confirm")
    state = project.state()
    assert second.data["target"] == "plan_draft"
    assert state["current_phase"] == "plan_draft"
    assert state["status"] == "pending"


def test_08_restart_clears_only_downstream_approvals(project):
    at_gate_plan(project)
    project.ok("restart", "--to", "6")
    project.ok("restart", "--to", "6", "--confirm")
    state = project.state()

    assert state["approvals"]["gate_constitution"]["decision"] == "approved"
    assert state["approvals"]["gate_spec"]["decision"] == "approved"
    assert state["artifact_shas"]["gate_spec"], "upstream baselines survive"
    assert state["approvals"]["gate_plan"] is None
    assert "gate_plan" not in state["artifact_shas"]


def test_08_restart_trims_phase_history_and_clears_drift(project):
    at_gate_plan(project)
    project.ok("restart", "--to", "6")
    project.ok("restart", "--to", "6", "--confirm")
    state = project.state()

    assert all(e["phase"] not in ("plan_draft", "gate_plan")
               for e in state["phase_history"])
    assert state["drift_queue"] == []
    assert state["pending_phase"] is None
    assert state["phase_checkpoint"] is None


def test_08_forward_jump_refused_without_offering_confirmation(project):
    at_gate_plan(project)
    result = project.run("restart", "--to", "15")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "forward_jump"
    assert project.state()["pending_confirm_action"] is None, \
        "a refusal is not a confirmable action"


def test_08_restarting_a_gate_phase_is_refused(project):
    at_gate_plan(project)
    result = project.run("restart", "--to", "7")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "gate_phase"
    assert result.data["suggest"] == 6


def test_08_restart_range_is_validated(project):
    at_gate_plan(project)
    for bad in ("0", "19", "99"):
        result = project.run("restart", "--to", bad)
        assert result.exit_code == EXIT_REFUSED
        assert result.reason in ("invalid_phase_number", "forward_jump")


def test_08_confirm_restart_without_a_pending_one_is_refused(project):
    at_gate_plan(project)
    result = project.run("restart", "--to", "6", "--confirm")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "no_pending_confirmation"


def test_08_doctor_detects_a_hand_edited_forward_jump(project):
    at_gate_plan(project)
    state = project.state()
    state["current_phase"] = "implement"
    state["progress"] = "15/18"
    project.write_state(state)

    result = project.run("doctor")
    assert result.exit_code == EXIT_REFUSED
    assert result.data["verdict"] == "jump"
    assert result.data["gap"] > 2
    assert project.state()["pending_confirm_action"] == "accept_state_jump"


def test_08_accept_state_acknowledges_and_logs(project):
    test_08_doctor_detects_a_hand_edited_forward_jump(project)
    project.ok("accept-state")
    assert project.state()["pending_confirm_action"] is None
    assert "acknowledged state jump" in project.audit_file.read_text("utf-8")


def test_08_doctor_detects_backwards_state(project):
    at_gate_plan(project)
    state = project.state()
    state["current_phase"] = "constitution_draft"
    state["progress"] = "2/18"
    project.write_state(state)

    result = project.run("doctor")
    assert result.data["verdict"] == "backwards"


def test_08_doctor_tolerates_a_gap_of_two(project):
    at_gate_plan(project)
    assert project.ok("doctor").data["verdict"] == "ok"


def test_08_reset_is_two_step_and_preserves_artifacts(project):
    at_gate_plan(project)
    project.ok("lock", "acquire", session="t")

    first = project.ok("reset")
    assert first.data["pending"] is True
    assert project.state_file.exists()

    project.ok("reset", "--confirm")
    assert not project.state_file.exists()
    assert not project.audit_file.exists()
    assert not (project.root / ".workflow" / "lock").exists()
    assert (project.root / f".specify/specs/{FEATURE}/spec.md").is_file()
    assert (project.root / ".specify/memory/constitution.md").is_file()


def test_08_confirm_reset_without_a_pending_one_is_refused(project):
    at_gate_plan(project)
    result = project.run("reset", "--confirm")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "no_pending_confirmation"


def test_08_a_pending_reset_is_cancelled_by_any_other_command(project):
    at_gate_plan(project)
    project.ok("reset")
    project.ok("confirm", "clear")

    result = project.run("reset", "--confirm")
    assert result.exit_code == EXIT_REFUSED
    assert project.state_file.exists(), "state survived a cancelled reset"


# ===========================================================================
# 09 — bootstrap failures
# ===========================================================================


def test_09_no_requirements_directory_halts(project):
    import shutil
    shutil.rmtree(project.root / "requirements")

    result = project.run("preflight")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "requirements_missing"
    assert not project.state_file.exists(), "nothing is initialised on a false start"


def test_09_empty_requirements_directory_halts(project):
    for path in (project.root / "requirements").iterdir():
        path.unlink()
    result = project.run("preflight")
    assert result.reason == "requirements_missing"


def test_09_missing_speckit_halts_first(project):
    import shutil
    shutil.rmtree(project.root / ".specify")
    shutil.rmtree(project.root / "requirements")

    result = project.run("preflight")
    assert result.reason == "speckit_missing", "prerequisite order: SpecKit first"
    assert "specify init" in result.envelope["message"]


def test_09_undiscoverable_skills_halt(project):
    import shutil
    shutil.rmtree(project.root / ".claude" / "skills" / "speckit-constitution")

    result = project.run("preflight")
    # Only meaningful when the user profile has no speckit skills either.
    if result.exit_code == EXIT_REFUSED:
        assert result.reason == "speckit_skills_missing"
    else:
        assert result.data["skill_prefix"] is not None


def test_09_healthy_project_passes_preflight(project):
    result = project.ok("preflight")
    assert result.data["speckit_present"] is True
    assert result.data["requirements"] == ["todo-api.md"]
    assert result.data["python_version"].startswith("3.")


def test_09_preflight_lists_guidance_files(project):
    (project.root / "guidance").mkdir()
    (project.root / "guidance" / "plan.md").write_text("prefer x\n", encoding="utf-8")
    assert project.ok("preflight").data["guidance"] == ["plan.md"]


def test_09_guidance_map_resolves_from_the_skill_file(project):
    (project.root / "guidance").mkdir()
    (project.root / "guidance" / "plan.md").write_text("prefer x\n", encoding="utf-8")

    result = project.ok("guidance", "path", "--phase", "plan_draft")
    assert result.data["path"] == "guidance/plan.md"
    assert result.data["exists"] is True

    absent = project.ok("guidance", "path", "--phase", "analyze")
    assert absent.data["path"] == "guidance/analyze.md"
    assert absent.data["exists"] is False


def test_09_feature_resolution_refuses_when_nothing_was_produced(started):
    result = started.run("feature", "resolve")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "feature_unresolved"
