"""WorkItem-scoped runtime — the T02 surface.

Contract §8 moves every piece of active workflow runtime state out of the
repository-global `.workflow/` and under the active WorkItem. What is pinned
here is the pair of exit criteria — no repository-global runtime state, and the
18-phase lifecycle passing independently for two WorkItems — plus the machinery
that makes them true: the resolution ladder, the `workitem` state field and its
migration, execution identity, `migrate-workflow`, and the guardrails whose
path assumptions moved.

The ladder tests deliberately build their own project state from
`bare_project` rather than the shared `project` fixture. The shared fixture
pre-registers one WorkItem so the rest of the suite binds at rung 2; using it
here would let a resolution bug hide behind the fixture.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import shutil

import pytest

from conftest import FIXTURE_WORKITEM_ID, SDLE_PY, Project, sdle
from test_integration_01_happy_path import EXPECTED_TRAVERSAL, run_happy_path
from test_units_artifact_review import review_for_gate

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3

# D04 (SDLE-DEFECT-STABILIZATION-01) appended the collision-resistant suffix.
# Old value: `^[a-z0-9]{1,3}-\d{8}T\d{6}Z$`.
EXECUTION_ID = re.compile(r"^[a-z0-9]{1,3}-\d{8}T\d{6}Z-[0-9a-f]{8}$")

RUNTIME_FILES = (
    "state.json", "execution.json", "audit.md", "lock",
    "implementation-manifest.md", "completion-summary.json",
)


def create_wi(project: Project, name: str):
    return project.ok("workitem", "create", "--name", name)


def legacy_state(project: Project, **overrides) -> dict:
    """Plant a repository-global `.workflow/state.json`, as a pre-T02 repo has."""
    template = json.loads(
        (project.skill_root / "templates" / "state.json").read_text(encoding="utf-8")
    )
    template.update(overrides)
    legacy = project.root / ".workflow"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "state.json").write_text(
        json.dumps(template, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return template


def at_implement(view: Project) -> None:
    state = view.state()
    state["current_phase"] = "implement"
    state["progress"] = "15/18"
    view.write_state(state)


# ==========================================================================
# Isolation — the phase's headline claim (contract §8 "Tests", "Exit criteria")
# ==========================================================================


def test_a_full_run_leaves_no_repository_global_runtime(git_project):
    """Contract §8 exit criterion 1: no active runtime state is repo-global."""
    assert run_happy_path(git_project) == EXPECTED_TRAVERSAL

    assert not (git_project.root / ".workflow").exists()
    for name in RUNTIME_FILES:
        assert (git_project.runtime / name).is_file(), name
    assert git_project.runtime == (
        git_project.root / "workitems" / FIXTURE_WORKITEM_ID / ".sdle"
    )
    assert git_project.state()["workitem"] == FIXTURE_WORKITEM_ID


def test_two_workitems_complete_independent_runs(git_project):
    """Contract §8 exit criterion 2, and plan N1: driving WI-B through all 18
    phases leaves WI-A's state and audit byte-identical."""
    create_wi(git_project, "Wi B")
    a = git_project.as_workitem(FIXTURE_WORKITEM_ID)
    b = git_project.as_workitem("wi-b")

    assert run_happy_path(a) == EXPECTED_TRAVERSAL
    a_state = a.state_file.read_bytes()
    a_audit = a.audit_file.read_bytes()

    assert run_happy_path(b) == EXPECTED_TRAVERSAL

    assert a.state_file.read_bytes() == a_state
    assert a.audit_file.read_bytes() == a_audit
    assert a.state()["workitem"] == FIXTURE_WORKITEM_ID
    assert b.state()["workitem"] == "wi-b"
    assert not (git_project.root / ".workflow").exists()


def test_each_workitem_keeps_its_own_audit_ledger(project):
    create_wi(project, "Wi B")
    a = project.as_workitem(FIXTURE_WORKITEM_ID)
    b = project.as_workitem("wi-b")
    a.ok("init", session="sa")
    b.ok("init", session="sb")

    a.ok("audit", "append", "--phase", "spec_draft", "--event", "note",
         "--message", "only in the A ledger")

    assert "only in the A ledger" in a.audit_file.read_text(encoding="utf-8")
    assert "only in the A ledger" not in b.audit_file.read_text(encoding="utf-8")
    assert a.ok("audit", "verify").data["matches"] is True
    assert b.ok("audit", "verify").data["matches"] is True


def test_manifest_build_under_one_workitem_leaves_the_other_alone(git_project):
    create_wi(git_project, "Wi B")
    a = git_project.as_workitem(FIXTURE_WORKITEM_ID)
    b = git_project.as_workitem("wi-b")
    a.ok("init", session="sa")
    b.ok("init", session="sb")
    at_implement(a)

    a.ok("implement", "preflight", "--bypass")
    result = a.ok("manifest", "build", "--skip-tests")

    assert (a.runtime / "implementation-manifest.md").is_file()
    assert not (b.runtime / "implementation-manifest.md").exists()
    assert result.data["path"] == (
        f"workitems/{FIXTURE_WORKITEM_ID}/.sdle/implementation-manifest.md"
    )
    # The runtime is bookkeeping, not implementation: it never lists itself.
    assert not any(f.startswith(f"workitems/{FIXTURE_WORKITEM_ID}/.sdle/")
                   for f in result.data["files"])


def test_a_lock_on_one_workitem_never_blocks_another(project):
    """TP-009's acceptance test: a WorkItem lock must not block a different
    WorkItem."""
    create_wi(project, "Wi B")
    a = project.as_workitem(FIXTURE_WORKITEM_ID)
    b = project.as_workitem("wi-b")
    a.ok("init")  # no session: neither WorkItem starts out locked
    b.ok("init")

    a.ok("lock", "acquire", session="session-a")
    assert (a.runtime / "lock").is_file()
    assert not (b.runtime / "lock").exists()

    # A fresh foreign lock on A is invisible to B, and B keeps working.
    acquired = b.ok("lock", "acquire", session="session-b")
    assert acquired.data["foreign"] is False
    assert acquired.data["warn"] is False
    assert b.ok("state", "get").exit_code == EXIT_OK

    a_lock = (a.runtime / "lock").read_text(encoding="utf-8")
    assert a_lock.strip().endswith("session-a")


# ==========================================================================
# Resolution ladder (plan D2, D3)
# ==========================================================================


def test_rung1_an_explicit_workitem_binds_even_when_several_exist(project):
    create_wi(project, "Wi B")
    result = project.run("--workitem", FIXTURE_WORKITEM_ID, "init", session="s")
    assert result.exit_code == EXIT_OK, result
    assert result.data["workitem"] == FIXTURE_WORKITEM_ID
    assert (project.root / "workitems" / FIXTURE_WORKITEM_ID / ".sdle"
            / "state.json").is_file()
    assert not (project.root / "workitems" / "wi-b" / ".sdle").exists()


def test_rung1_an_unregistered_workitem_is_refused(project):
    result = project.run("--workitem", "nope", "state", "get")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_unknown"
    assert "workitem create" in result.envelope["message"]
    assert result.data["requested"] == "nope"


def test_rung2_the_sole_registered_workitem_binds_with_no_flag(project):
    result = project.ok("init", session="s")
    assert result.data["workitem"] == FIXTURE_WORKITEM_ID
    assert project.state_file.is_file()
    assert not (project.root / ".workflow").exists()


def test_rung3_legacy_state_no_longer_binds_and_the_refusal_names_recovery(
    bare_project,
):
    """T11 D1/D3, the inverse of the rung this test used to pin.

    The transitional rung is gone: a repository-global `.workflow/state.json`
    is a migration *source*, never a runtime. The replacement safety property
    (§28) is that the refusal now names the whole recovery, in order, so the
    repository is signposted rather than bricked — which is strictly more
    than the old assertion, not less.
    """
    legacy_state(bare_project, project_name="Legacy Project")

    result = bare_project.run("state", "get", "--field", "project_name")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_required", result
    message = result.envelope["message"]
    assert "workitem create" in message
    assert "migrate-workflow" in message
    assert message.index("workitem create") < message.index("migrate-workflow")
    assert result.data["legacy_state"].replace("\\", "/").endswith(
        ".workflow/state.json"), result.data
    # Nothing was created and the legacy runtime was not touched.
    assert not (bare_project.root / "workitems").exists()
    assert (bare_project.root / ".workflow" / "state.json").is_file()


def test_the_legacy_recovery_path_is_exactly_two_runtime_free_commands(
    bare_project,
):
    """T11 A4/F1, through the real CLI. Both recovery commands must remain
    invocable in a repository that resolves to nothing, or removing the rung
    would brick it — which is the one outcome §17's gate forbids."""
    legacy_state(bare_project, project_name="Legacy Project")

    created = bare_project.ok("workitem", "create", "--name", "Recovered")
    wid = created.data["id"]
    assert bare_project.ok("migrate-workflow", "--workitem", wid).data["to"] == (
        f"workitems/{wid}/.sdle"
    )

    bound = bare_project.as_workitem(wid)
    assert bound.ok("state", "get", "--field", "project_name").data["value"] == (
        "Legacy Project"
    )


def test_rung4_no_workitem_and_no_legacy_state_is_refused(bare_project):
    result = bare_project.run("state", "get")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_required"
    assert "workitem create" in result.envelope["message"]
    assert result.data["workitems"] == []


def test_rung5_two_workitems_and_no_flag_refuses_and_never_picks(bare_project):
    create_wi(bare_project, "Wi A")
    create_wi(bare_project, "Wi B")

    result = bare_project.run("init", session="s")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"
    assert sorted(result.data["workitems"]) == ["wi-a", "wi-b"]
    for wid in ("wi-a", "wi-b"):
        assert not (bare_project.root / "workitems" / wid / ".sdle").exists()
    assert not (bare_project.root / ".workflow").exists()


@pytest.mark.parametrize("command", [
    ("lint-skill",),
    ("sha", "requirements/todo-api.md"),
    ("constants",),
    ("workitem", "list"),
    ("validate",),
])
def test_runtime_free_commands_need_no_workitem(bare_project, command):
    result = bare_project.run(*command)
    assert result.exit_code == EXIT_OK, result
    assert result.reason not in {
        "workitem_required", "workitem_ambiguous", "workitem_unknown",
    }


def test_a_runtime_command_still_refuses_in_that_same_repository(bare_project):
    """The other half of the RUNTIME_FREE_COMMANDS test: the exemption is a
    list, not a hole in the ladder."""
    assert bare_project.run("constants").exit_code == EXIT_OK
    result = bare_project.run("state", "get")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "workitem_required"


def test_init_never_takes_the_legacy_rung(bare_project):
    legacy_state(bare_project)
    result = bare_project.run("init", session="s")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "legacy_workflow_present"
    assert "migrate-workflow" in result.envelope["message"]


def test_init_refuses_legacy_state_even_with_a_workitem_registered(bare_project):
    """Unconditional by design (plan D2/C4). Proceeding would create a second
    runtime while the legacy one became simultaneously unbindable — rung 3
    needs *zero* WorkItems — and unmigratable, because `migrate-workflow`
    would then refuse `target_exists`."""
    create_wi(bare_project, "Wi A")
    legacy_state(bare_project)

    result = bare_project.run("--workitem", "wi-a", "init", session="s")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "legacy_workflow_present"
    assert not (bare_project.root / "workitems" / "wi-a" / ".sdle").exists()


# ==========================================================================
# State schema and the migration chain (plan D6)
# ==========================================================================


def test_the_shipped_template_is_1_17_and_carries_the_workitem_field(bare_project):
    template = json.loads(
        (bare_project.skill_root / "templates" / "state.json")
        .read_text(encoding="utf-8")
    )
    assert template["workflow_version"] == "1.17"
    assert template["workitem"] is None
    assert list(template)[:2] == ["workflow_version", "workitem"]


def test_migrating_a_state_under_a_workitem_binds_that_workitem(project):
    project.ok("init", session="s")
    state = project.state()
    state["workflow_version"] = "1.13"
    del state["workitem"]
    project.write_state(state)

    result = project.ok("migrate", session="s")

    assert result.data["steps"] == ["1.13->1.14", "1.14->1.15",
                                    "1.15->1.16", "1.16->1.17"]
    assert project.state()["workitem"] == FIXTURE_WORKITEM_ID


def test_migrating_a_state_at_the_legacy_location_leaves_workitem_null(bare_project):
    planted = legacy_state(bare_project, workflow_version="1.13")
    del planted["workitem"]
    (bare_project.root / ".workflow" / "state.json").write_text(
        json.dumps(planted, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    # T11 D1: `migrate` is not RUNTIME_FREE, so it can no longer reach a state
    # file at the legacy location at all — there is nothing there to bind.
    refused = bare_project.run("migrate")
    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "workitem_required", refused

    # The 1.13 -> 1.14 rule itself is unchanged and still reachable: a state
    # whose file does not live under a WorkItem keeps `workitem: null`. It is
    # asserted against the migration chain directly, which is where the rule
    # lives, and then end-to-end through `migrate-workflow` — the only route a
    # legacy state has left.
    paths = sdle.resolve_paths(str(bare_project.root),
                               str(bare_project.skill_root))
    state = dict(planted)
    steps = sdle.migrate_state(state, paths, sdle.load_constants(paths))
    assert "1.13->1.14" in steps, steps
    assert state["workflow_version"] == "1.17"
    assert state["workitem"] is None

    wid = create_wi(bare_project, "Recovered").data["id"]
    moved = bare_project.ok("migrate-workflow", "--workitem", wid)
    assert moved.data["to"] == f"workitems/{wid}/.sdle"
    migrated = json.loads(
        (bare_project.root / "workitems" / wid / ".sdle" / "state.json")
        .read_text(encoding="utf-8")
    )
    assert migrated["workflow_version"] == "1.17"
    assert migrated["workitem"] == wid, (
        "once it lives under a WorkItem the field names it")


# ==========================================================================
# migrate-workflow (plan D8, contract §20)
# ==========================================================================


def legacy_workflow(bare_project: Project, workitem: str = "Wi A") -> str:
    """Stand up a genuine pre-T02 repository, then register the target WorkItem.

    A v1.14 engine can no longer *create* a repository-global runtime — that is
    C4/D2 — so the fixture builds a real one under a throwaway WorkItem, moves
    it to `.workflow/`, erases every trace of the WorkItem layer, and winds the
    state file back to a v1.13 shape with no `workitem` field. The audit ledger
    moves byte-for-byte, so `audit_sha` still matches and the migration path
    is exercised against a ledger that genuinely verifies.
    """
    seed = bare_project.as_workitem(create_wi(bare_project, "Legacy Seed").data["id"])
    seed.ok("init", session="legacy")
    bare_project.write_artifact(".specify/memory/constitution.md")
    seed.record_governance()  # T06: E1 guards the seed run's advances.
    seed.ok("advance", "--to", "gate_constitution", session="legacy")
    review_for_gate(seed, "gate_constitution")  # T06: E2 guards the seed run.
    seed.ok("gate", "approve", "--gate", "gate_constitution", session="legacy")

    shutil.move(str(seed.runtime), str(bare_project.root / ".workflow"))
    shutil.rmtree(bare_project.root / "workitems")

    path = bare_project.root / ".workflow" / "state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["workflow_version"] = "1.13"
    state.pop("workitem", None)
    path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8",
                    newline="\n")

    return create_wi(bare_project, workitem).data["id"]


def legacy_digests(bare_project: Project) -> dict[str, str]:
    out = {}
    for path in sorted((bare_project.root / ".workflow").rglob("*")):
        if path.is_file():
            out[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def test_migrate_moves_the_whole_runtime_and_preserves_every_field(bare_project):
    wid = legacy_workflow(bare_project)
    legacy_state_before = json.loads(
        (bare_project.root / ".workflow" / "state.json").read_text(encoding="utf-8")
    )
    before = legacy_digests(bare_project)

    result = bare_project.ok("migrate-workflow", "--workitem", wid)

    target = bare_project.root / "workitems" / wid / ".sdle"
    migrated = json.loads((target / "state.json").read_text(encoding="utf-8"))

    for field in (
        "current_phase", "status", "progress", "approvals", "artifact_shas",
        "rate_limits", "attempt_counts", "implementation_base_ref",
        "phase_history", "project_name",
    ):
        assert migrated[field] == legacy_state_before[field], field
    # v1.15 replaced the flat `current_feature_id` with the `specKit` object,
    # so the object is what has to survive the move now — and the old flat
    # field must be gone rather than mirrored.
    assert "current_feature_id" not in migrated
    assert migrated["specKit"] == legacy_state_before["specKit"]
    assert migrated["workitem"] == wid
    assert migrated["workflow_version"] == "1.17"

    assert (target / "audit.md").is_file()
    assert (target / "execution.json").is_file()
    assert result.data["legacy_preserved"] is True
    assert result.data["to"] == f"workitems/{wid}/.sdle"

    # The migrated ledger verifies at its new home.
    bound = bare_project.as_workitem(wid)
    assert bound.ok("audit", "verify").data["matches"] is True

    # Contract §8.7/§8.9: the legacy runtime is byte-for-byte untouched.
    assert legacy_digests(bare_project) == before


def test_migrate_records_evidence_metadata_and_a_target_audit_entry(bare_project):
    wid = legacy_workflow(bare_project)
    legacy_sha = None

    result = bare_project.ok("migrate-workflow", "--workitem", wid)
    execution_id = result.data["execution_id"]
    target = bare_project.root / "workitems" / wid / ".sdle"

    evidence = list((target / "evidence").glob("migration-*.json"))
    assert len(evidence) == 1
    facts = json.loads(evidence[0].read_text(encoding="utf-8"))
    assert facts["executionId"] == execution_id
    assert facts["migratedFrom"] == ".workflow"
    assert facts["legacyStateSha"] == result.data["legacy_state_sha"]
    assert facts["legacyAuditSha"] == result.data["legacy_audit_sha"]
    legacy_sha = facts["legacyStateSha"]

    metadata = json.loads(
        (bare_project.root / "workitems" / wid / "workitem.json")
        .read_text(encoding="utf-8")
    )
    assert metadata["id"] == wid  # identity untouched
    assert metadata["migration"]["executionId"] == execution_id
    assert metadata["migration"]["legacyStateSha"] == legacy_sha
    assert metadata["migration"]["migratedFrom"] == ".workflow"

    entries = (target / "audit.md").read_text(encoding="utf-8")
    assert entries.rstrip().endswith("**Prev:** " + _last_prev(entries))
    assert "workflow_migrated" in entries.split("## AUDIT")[-1]


def _last_prev(text: str) -> str:
    return text.rstrip().rsplit("**Prev:** ", 1)[1].strip()


def test_migrate_refuses_an_unregistered_workitem(bare_project):
    legacy_workflow(bare_project)
    result = bare_project.run("migrate-workflow", "--workitem", "nope")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_unknown"
    assert "workitem create" in result.envelope["message"]
    assert not (bare_project.root / "workitems" / "nope").exists()


def test_migrate_refuses_when_the_target_runtime_already_exists(bare_project):
    wid = legacy_workflow(bare_project)
    bare_project.ok("migrate-workflow", "--workitem", wid)
    before = legacy_digests(bare_project)

    result = bare_project.run("migrate-workflow", "--workitem", wid)

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "target_exists"
    assert legacy_digests(bare_project) == before


def test_migrate_refuses_a_corrupt_legacy_state(bare_project):
    wid = legacy_workflow(bare_project)
    (bare_project.root / ".workflow" / "state.json").write_text(
        '{"workflow_version": "1.1', encoding="utf-8"
    )

    result = bare_project.run("migrate-workflow", "--workitem", wid)

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "legacy_state_invalid"
    assert not (bare_project.root / "workitems" / wid / ".sdle").exists()


def test_migrate_refuses_an_unknown_legacy_version(bare_project):
    wid = legacy_workflow(bare_project)
    path = bare_project.root / ".workflow" / "state.json"
    state = json.loads(path.read_text(encoding="utf-8"))
    state["workflow_version"] = "9.9"
    path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    result = bare_project.run("migrate-workflow", "--workitem", wid)

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "legacy_state_invalid"
    assert not (bare_project.root / "workitems" / wid / ".sdle").exists()


def test_migrate_refuses_a_broken_legacy_audit_chain(bare_project):
    wid = legacy_workflow(bare_project)
    audit = bare_project.root / ".workflow" / "audit.md"
    audit.write_text(
        audit.read_text(encoding="utf-8").replace("workflow_initialized", "tampered"),
        encoding="utf-8",
    )
    before = legacy_digests(bare_project)

    result = bare_project.run("migrate-workflow", "--workitem", wid)

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "legacy_audit_broken"
    assert "audit rebaseline" in result.envelope["message"]
    assert not (bare_project.root / "workitems" / wid / ".sdle" / "state.json").exists()
    assert legacy_digests(bare_project) == before


@pytest.mark.parametrize("fail_after", [1, 2, 3, 4])
def test_a_crash_during_migration_leaves_no_resolvable_target(
    bare_project, monkeypatch, fail_after
):
    """The target state.json is written last and is the sole commit marker, so
    an interruption anywhere leaves the legacy runtime authoritative and a
    re-run safe."""
    wid = legacy_workflow(bare_project)
    before = legacy_digests(bare_project)

    real = sdle.write_atomic
    calls = {"n": 0}

    def flaky(path, text):
        calls["n"] += 1
        if calls["n"] > fail_after:
            raise OSError("simulated interruption")
        return real(path, text)

    monkeypatch.setattr(sdle, "write_atomic", flaky)
    with pytest.raises(OSError):
        bare_project.run("migrate-workflow", "--workitem", wid)
    monkeypatch.setattr(sdle, "write_atomic", real)

    target = bare_project.root / "workitems" / wid / ".sdle"
    assert not (target / "state.json").exists()
    assert legacy_digests(bare_project) == before

    # Legacy still resolves (rung 3 is unreachable now that a WorkItem exists,
    # so bind explicitly) and the re-run completes.
    assert bare_project.ok("migrate-workflow", "--workitem", wid).exit_code == EXIT_OK
    assert (target / "state.json").is_file()
    assert legacy_digests(bare_project) == before


def test_after_migration_the_workitem_runtime_is_the_one_that_resolves(bare_project):
    wid = legacy_workflow(bare_project)
    bare_project.ok("migrate-workflow", "--workitem", wid)

    bound = bare_project.as_workitem(wid)
    assert bound.ok("state", "get", "--field", "workitem").data["value"] == wid
    # Sole registered WorkItem: rung 2 binds it with no flag, and the legacy
    # dual-read rung is unreachable because a WorkItem now exists.
    unflagged = bare_project.run("state", "get", "--field", "workitem")
    assert unflagged.exit_code == EXIT_OK, unflagged
    assert unflagged.data["value"] == wid


# ==========================================================================
# Execution identity (plan D7, contract §8 "Execution identity")
# ==========================================================================


@pytest.mark.parametrize("name,email,expected", [
    ("Muhammad Ali", "muhammad@example.invalid", "muh"),
    ("A_B", "zoe@example.invalid", "ab"),
    ("Jo", "zoe@example.invalid", "jo"),
    ("", "zoe@example.invalid", "zoe"),
    ("", "", "usr"),
])
def test_execution_prefix_follows_the_contract_rule(
    git_project, name, email, expected
):
    git_project.git("config", "user.name", name)
    git_project.git("config", "user.email", email)
    paths = sdle.resolve_paths(str(git_project.root), str(git_project.skill_root))
    assert sdle.execution_prefix(paths) == expected


def test_execution_identity_is_written_at_init_and_is_not_the_workitem(project):
    result = project.ok("init", session="s")
    execution_id = result.data["execution_id"]
    assert EXECUTION_ID.match(execution_id), execution_id

    doc = json.loads((project.runtime / "execution.json").read_text(encoding="utf-8"))
    assert doc["executionId"] == execution_id
    assert doc["workitem"] == FIXTURE_WORKITEM_ID
    assert doc["sdleVersion"] == "1.17"
    assert doc["startedAt"].endswith("Z")
    # Contract §8: execution identity is execution metadata, never the
    # WorkItem name, and nothing resolves a WorkItem from it.
    assert FIXTURE_WORKITEM_ID not in execution_id


# ==========================================================================
# Guardrails whose path assumptions moved (plan D9, C10)
# ==========================================================================


def test_implement_preflight_does_not_count_the_workitem_tree_as_dirt(git_project):
    git_project.ok("init", session="s")
    at_implement(git_project)

    result = git_project.ok("implement", "preflight", session="s")

    assert result.data["dirty"] is False, result.data["entries"]
    assert result.data["entries"] == []
    assert result.data["base_ref"]


def test_the_phase_17_diff_excludes_the_workitem_runtime(git_project):
    git_project.ok("init", session="s")
    at_implement(git_project)
    git_project.ok("implement", "preflight", "--bypass", session="s")
    (git_project.root / "src").mkdir(exist_ok=True)
    (git_project.root / "src" / "app.py").write_text(
        "print('hello')\n", encoding="utf-8", newline="\n"
    )
    git_project.git("add", "-A")
    git_project.git("commit", "-q", "-m", "implementation")

    state = git_project.state()
    state["current_phase"] = "security_review"
    state["progress"] = "17/18"
    git_project.write_state(state)
    result = git_project.ok("security-review", "evidence", session="s")

    diff = result.data["diff"] or ""
    assert "src/app.py" in diff
    assert f"workitems/{FIXTURE_WORKITEM_ID}/.sdle/" not in diff
    assert "state.json" not in diff


# ==========================================================================
# reset under the rebinding (plan N33, baseline E5)
# ==========================================================================


def test_reset_clears_the_runtime_and_preserves_workitem_identity(project):
    project.ok("init", session="s")
    project.ok("lock", "acquire", session="s")
    assert (project.runtime / "lock").is_file()

    project.ok("reset", session="s")
    project.ok("reset", "--confirm", session="s")

    assert not project.state_file.exists()
    assert not project.audit_file.exists()
    assert not (project.runtime / "lock").exists()

    assert (project.root / "workitems" / "index.md").is_file()
    assert (project.root / "workitems" / FIXTURE_WORKITEM_ID
            / "workitem.json").is_file()
    assert (project.root / "workitems" / FIXTURE_WORKITEM_ID).is_dir()


# ==========================================================================
# project_name (plan D10, baseline §4.3 ADAPT)
# ==========================================================================


def test_project_name_still_prefers_the_requirements_heading(project):
    """Guards the D10 precedence decision: the WorkItem title sits *after*
    heading inference, so no existing assertion changes."""
    result = project.ok("init", session="s")
    assert result.data["project_name"] == "Todo List REST API"


def test_project_name_falls_back_to_the_workitem_title(bare_project):
    create_wi(bare_project, "Customer Notification Service")
    bare_project.workitem = "customer-notification-service"
    (bare_project.root / "requirements" / "todo-api.md").write_text(
        "no heading in this document\n", encoding="utf-8", newline="\n"
    )

    result = bare_project.ok("init", session="s")

    assert result.data["project_name"] == "Customer Notification Service"
    assert result.data["project_name"] != bare_project.root.name
    assert bare_project.state()["project_name"] == "Customer Notification Service"


# ==========================================================================
# T11 N17/N25 — the removal, asserted positively
#
# N17 pins D3's refusal *shape*: reason string, exit code, the two recovery
# steps in order, and `legacy_state` in structured `data`.
# N25 pins R2 over the parser's own registered command set, so a command
# added later cannot quietly reintroduce an unbound runtime.
# ==========================================================================


def test_n17_the_workitem_required_refusal_names_the_recovery_in_order(
    bare_project,
):
    """T11 D3 / A5 / N17, and the close of T02 NB-2.

    Post-removal this refusal is the only signpost a pre-v1.14 repository
    gets, so its content is a contract, not prose: same reason string as
    before (no CLI break), exit 1, both steps named, `workitem create` before
    `migrate-workflow`, and the path in structured `data`.
    """
    legacy_state(bare_project)

    result = bare_project.run("state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_required", result
    message = result.envelope["message"]
    assert "workitem create" in message, message
    assert "migrate-workflow --workitem" in message, message
    assert message.index("workitem create") < message.index("migrate-workflow")
    assert result.data["workitems"] == []
    assert result.data["legacy_state"].replace("\\", "/").endswith(
        ".workflow/state.json"), result.data
    # Human text on stderr, JSON on stdout — B6, unchanged by the widening.
    assert "workitem_required" in result.stderr


def test_n17_without_legacy_state_the_refusal_stays_the_short_one(bare_project):
    """The widening is conditional: a genuinely empty repository is not told
    to migrate something that does not exist."""
    result = bare_project.run("state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_required", result
    assert "migrate-workflow" not in result.envelope["message"]
    assert "legacy_state" not in result.data


def test_n25_every_bound_runtime_command_names_a_workitem(bare_project):
    """T11 R2 / A3, proven over the parser's registered command set rather
    than a hand-copied list.

    `main()` binds exactly when the command is not RUNTIME_FREE. For every
    such command, a successful `bind_workitem` must return a `Paths` whose
    `workitem` is not None — that is what makes all eleven deleted carve-outs
    unreachable rather than merely unused.
    """
    parser = sdle.build_parser()
    subparsers = [action for action in parser._actions  # noqa: SLF001
                  if isinstance(action, argparse._SubParsersAction)]
    assert len(subparsers) == 1, subparsers
    registered = set(subparsers[0].choices)
    assert registered, "the parser must register a command set"
    assert sdle.RUNTIME_FREE_COMMANDS <= registered, (
        sdle.RUNTIME_FREE_COMMANDS - registered)

    # Both recovery steps must stay RUNTIME_FREE, or removing the rung would
    # brick a legacy-only repository (F1).
    assert {"workitem", "migrate-workflow"} <= sdle.RUNTIME_FREE_COMMANDS

    bound_commands = sorted(registered - sdle.RUNTIME_FREE_COMMANDS)
    assert bound_commands, "some command must still bind"

    workitem = create_wi(bare_project, "Only One").data["id"]
    paths = sdle.resolve_paths(str(bare_project.root),
                               str(bare_project.skill_root))
    for command in bound_commands:
        result = sdle.bind_workitem(paths, None,
                                    for_init=(command == "init"))
        assert result.workitem == workitem, command
        assert result.runtime == (
            bare_project.root / "workitems" / workitem / ".sdle"), command


def test_n25_no_unbound_runtime_carve_out_survives_in_the_engine():
    """A3, by AST rather than by grep.

    Exactly two `workitem is None` tests may remain in `sdle.py`:
    `Paths.workitem_root`, which is the dataclass describing its own shape,
    and `collect_validation_findings`' speculative resolution warning, which
    `validate` needs so a repository that cannot resolve is still diagnosable
    (P5). Every other site was a runtime carve-out for the deleted rung.
    """
    tree = ast.parse(SDLE_PY.read_text(encoding="utf-8"))
    owners = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for inner in ast.walk(node):
            if (isinstance(inner, ast.Compare)
                    and isinstance(inner.ops[0], ast.Is)
                    and isinstance(inner.comparators[0], ast.Constant)
                    and inner.comparators[0].value is None
                    and isinstance(inner.left, ast.Attribute)
                    and inner.left.attr == "workitem"):
                owners.append(node.name)
    assert sorted(set(owners)) == [
        "collect_validation_findings", "workitem_root",
    ], owners
