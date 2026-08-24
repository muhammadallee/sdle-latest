"""T04 — Spec Kit bound to the active WorkItem (contract §10).

N1-N5 are §10's five required tests, in the contract's own terms; N6-N13 pin
the guards the T04 plan declared.

Two suite rules hold here as everywhere (see conftest): fixtures are generated
at runtime, and **SpecKit is never invoked**. Capability detection is exercised
against fabricated `.specify/scripts/` stub files — what the probe reads is
plain text, so a stub is a faithful stand-in for the thing under test — and
every generation step is simulated by writing an artifact over the size floor.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
from pathlib import Path

import pytest

from conftest import FEATURE_ID, FIXTURE_WORKITEM_ID, REPO_ROOT, Project, sdle

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3

SDLE_PY = REPO_ROOT / "scripts" / "sdle.py"
PHASE_EXECUTION = (
    REPO_ROOT / ".claude" / "skills" / "sdle" / "modules" / "phase-execution.md"
)
SPECKIT_OWNED_FILENAMES = ("spec.md", "plan.md", "tasks.md", "feature.json")
STUB_SCRIPT = ".specify/scripts/bash/common.sh"


# ==========================================================================
# helpers
# ==========================================================================


def create_wi(project: Project, name: str) -> str:
    return project.ok("workitem", "create", "--name", name).data["id"]


def install_speckit_scripts(project: Project, *names: str) -> Path:
    """Fabricate the installation scripts the capability probe reads."""
    target = project.root / STUB_SCRIPT
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "#!/usr/bin/env bash\n" + "".join('echo "${%s}"\n' % n for n in names),
        encoding="utf-8",
        newline="\n",
    )
    return target


def full_speckit(project: Project) -> Path:
    return install_speckit_scripts(project, *sdle.SPECKIT_REQUIRED_CAPABILITIES)


def sha_map(root: Path) -> dict[str, str]:
    """Recursive SHA map of every file under ``root`` — the purity probe."""
    return {
        str(p.relative_to(root)).replace(os.sep, "/"):
            hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*")) if p.is_file()
    }


def age(path: Path, stamp: int) -> None:
    os.utime(path, (stamp, stamp))


def two_workitems(bare_project: Project) -> tuple[Project, Project]:
    """Two registered, initialised WorkItems in one repository."""
    a = bare_project.as_workitem(create_wi(bare_project, "Wi A"))
    b = bare_project.as_workitem(create_wi(bare_project, "Wi B"))
    a.ok("init", session="a")
    b.ok("init", session="b")
    return a, b


def plant_legacy_workflow(bare_project: Project) -> None:
    """A repository-global `.workflow/state.json`, as a pre-v1.14 repo has.

    The transitional dual-read rung is T11's to remove, not T04's; these tests
    exist to prove T04 left it working.
    """
    template = json.loads(
        (bare_project.skill_root / "templates" / "state.json")
        .read_text(encoding="utf-8")
    )
    legacy = bare_project.root / ".workflow"
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "state.json").write_text(
        json.dumps(template, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def as_v114(project: Project, **extra) -> dict:
    """The project's state, wound back to the v1.14 shape."""
    state = project.state()
    state["workflow_version"] = "1.14"
    state.pop("specKit", None)
    state["current_feature_id"] = None
    state.update(extra)
    return state


def drive_full_workflow(view: Project, feature: str) -> None:
    """All 18 phases, with `feature bind` at every generation phase.

    Mirrors the transcript order in test_integration_01; the difference is
    that each Spec Kit generation phase is preceded by the bind call the
    prompt layer makes, which is what §10's exit criterion is about.
    """
    directory = view.feature_dir(feature)
    view.ok("init", session=feature)

    view.write_artifact(".specify/memory/constitution.md")
    view.ok("feature", "bind")
    view.ok("advance", "--to", "gate_constitution")
    view.ok("gate", "approve", "--gate", "gate_constitution")

    view.ok("feature", "bind")
    view.write_artifact(f"{directory}/spec.md")
    view.ok("feature", "resolve")
    view.ok("advance", "--to", "gate_spec")
    view.ok("gate", "approve", "--gate", "gate_spec")

    view.ok("feature", "bind", "--require-feature")
    view.write_artifact(f"{directory}/plan.md")
    view.ok("advance", "--to", "gate_plan")
    view.ok("gate", "approve", "--gate", "gate_plan")

    view.ok("feature", "bind", "--require-feature")
    view.write_artifact(f"{directory}/checklist.md")
    view.ok("advance", "--to", "tasks_draft")
    view.ok("feature", "bind", "--require-feature")
    view.write_artifact(f"{directory}/tasks.md")
    view.ok("advance", "--to", "gate_tasks")
    view.ok("gate", "approve", "--gate", "gate_tasks")

    view.ok("feature", "bind", "--require-feature")
    view.write_artifact(f"{directory}/tasks.md",
                        "# Tasks (refined by analysis)\n\n" + "T001. " * 40)
    view.ok("drift", "rebaseline", "--gate", "gate_tasks")
    view.ok("advance", "--to", "gate_analyze")
    view.ok("gate", "approve", "--gate", "gate_analyze")

    view.write_artifact("design/app/app-design.md")
    view.ok("advance", "--to", "gate_design")
    view.ok("gate", "approve", "--gate", "gate_design")

    view.ok("feature", "bind", "--require-feature")
    view.ok("implement", "preflight", "--bypass")
    view.ok("manifest", "build", "--skip-tests")
    view.ok("advance", "--to", "gate_implement")
    view.ok("gate", "approve", "--gate", "gate_implement")

    begun = view.ok("security-review", "begin")
    view.write_artifact(begun.data["review_filename"])
    view.ok("advance", "--to", "gate_security")
    view.ok("gate", "approve", "--gate", "gate_security")


# ==========================================================================
# N1 — WorkItem A's Spec Kit output cannot be mistaken for WorkItem B's
# ==========================================================================


def test_n1_each_workitem_records_its_own_feature_directory(bare_project):
    a, b = two_workitems(bare_project)
    a.write_artifact(f"{a.feature_dir('001-alpha')}/spec.md")
    a.ok("feature", "resolve")

    a_state = a.state_file.read_bytes()
    a_audit = a.audit_file.read_bytes()
    a_specs = sha_map(a.specs_root)

    b.write_artifact(f"{b.feature_dir('002-bravo')}/spec.md")
    result = b.ok("feature", "resolve")

    assert result.data["feature_directory"] == "workitems/wi-b/specs/002-bravo"
    assert a.state()["specKit"]["featureDirectory"] == (
        "workitems/wi-a/specs/001-alpha"
    )
    assert a.state_file.read_bytes() == a_state, "A's state moved while B ran"
    assert a.audit_file.read_bytes() == a_audit, "A's ledger moved while B ran"
    assert sha_map(a.specs_root) == a_specs, "A's specs moved while B ran"


def test_n1_another_workitems_newer_directory_is_never_a_candidate(bare_project):
    a, b = two_workitems(bare_project)
    b.write_artifact(f"{b.feature_dir('002-bravo')}/spec.md")
    a.write_artifact(f"{a.feature_dir('001-alpha')}/spec.md")
    age(a.specs_root / "001-alpha", 2_000_000_000)  # far newer than B's

    result = b.ok("feature", "resolve")

    assert result.data["candidates"] == ["002-bravo"]
    assert result.data["feature_directory"] == "workitems/wi-b/specs/002-bravo"


# ==========================================================================
# N2 — WorkItem resolution precedes Spec Kit invocation
# ==========================================================================


def test_n2a_feature_is_not_a_runtime_free_command():
    """Structural, not documentary: because `feature` is outside this set,
    `bind_workitem` has already run before any `feature` handler is entered."""
    assert "feature" not in sdle.RUNTIME_FREE_COMMANDS


@pytest.mark.parametrize(
    "args",
    [("feature", "bind"), ("feature", "resolve"), ("feature", "capabilities")],
)
def test_n2b_an_ambiguous_repository_refuses_before_any_speckit_work(
    bare_project, args
):
    create_wi(bare_project, "Wi A")
    create_wi(bare_project, "Wi B")
    full_speckit(bare_project)

    result = bare_project.run(*args)

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "workitem_ambiguous"
    assert "env" not in result.data
    assert "capabilities" not in result.data


@pytest.mark.parametrize(
    "args",
    [("feature", "bind"), ("feature", "resolve"), ("feature", "capabilities")],
)
def test_n2c_a_repository_with_no_workitem_refuses(bare_project, args):
    full_speckit(bare_project)

    result = bare_project.run(*args)

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "workitem_required"
    assert "env" not in result.data
    assert "capabilities" not in result.data


def test_n2d_every_speckit_invocation_is_preceded_by_a_feature_bind():
    """The prompt layer must re-assert the environment before it invokes.

    SpecKit keeps one repository-global feature slot, so a bind that happens
    only once cannot be relied on.
    """
    text = PHASE_EXECUTION.read_text(encoding="utf-8")
    blocks = re.split(r"\n(?=\*\*Phase \d+ —|### Post-Generation Clarify)", text)

    checked = 0
    for block in blocks:
        invoke = block.find("using the Skill tool")
        if invoke == -1:
            continue
        header = block.splitlines()[0]
        bind = block.find("feature bind")
        assert bind != -1, f"no `feature bind` before the invocation in: {header}"
        assert bind < invoke, f"`feature bind` comes after the invocation in: {header}"
        checked += 1

    assert checked >= 8, f"only {checked} invocation blocks found"


# ==========================================================================
# N3 — branch alone does not define Spec Kit context
# ==========================================================================


def test_n3_the_bound_workitem_wins_over_a_branch_naming_another(bare_project):
    bare_project.init_git()
    a, b = two_workitems(bare_project)
    bare_project.git("checkout", "-q", "-b", "wi-a")  # the branch names A

    b.write_artifact(f"{b.feature_dir('002-bravo')}/spec.md")
    result = b.ok("feature", "resolve")

    assert result.data["feature_directory"] == "workitems/wi-b/specs/002-bravo"
    assert b.state()["specKit"]["featureId"] == "002-bravo"


def test_n3_a_stale_global_feature_slot_changes_nothing_and_is_never_written(
    bare_project,
):
    a, b = two_workitems(bare_project)
    full_speckit(bare_project)
    a.write_artifact(f"{a.feature_dir('001-alpha')}/spec.md")
    a.ok("feature", "resolve")
    b.write_artifact(f"{b.feature_dir('002-bravo')}/spec.md")
    b.ok("feature", "resolve")

    # SpecKit 0.15.0 keeps exactly one such slot, repository-global.
    (bare_project.root / ".specify" / "feature.json").write_text(
        json.dumps({"featureDirectory": "workitems/wi-a/specs/001-alpha"}) + "\n",
        encoding="utf-8", newline="\n",
    )
    before = sha_map(bare_project.root / ".specify")

    b.ok("feature", "bind")
    b.ok("feature", "resolve")

    assert b.state()["specKit"]["featureDirectory"] == (
        "workitems/wi-b/specs/002-bravo"
    )
    assert sha_map(bare_project.root / ".specify") == before, (
        "SDLE wrote inside .specify/ — feature.json is SpecKit's, not ours"
    )


def test_n3_a_gate_refuses_another_workitems_artifact(bare_project):
    a, b = two_workitems(bare_project)
    bare_project.write_artifact(".specify/memory/constitution.md")
    bare_project.write_artifact(f"{a.feature_dir('001-alpha')}/spec.md")

    b.ok("advance", "--to", "gate_constitution")
    b.ok("gate", "approve", "--gate", "gate_constitution")
    b.write_artifact(f"{b.feature_dir('002-bravo')}/spec.md")
    b.ok("feature", "resolve")
    b.ok("advance", "--to", "gate_spec")

    state = b.state()
    state["specKit"]["featureDirectory"] = "workitems/wi-a/specs/001-alpha"
    state["specKit"]["featureId"] = "001-alpha"
    b.write_state(state)

    result = b.run("gate", "approve", "--gate", "gate_spec")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "feature_outside_workitem"
    assert result.data["expected_prefix"] == "workitems/wi-b/specs/"
    assert b.state()["approvals"]["gate_spec"] is None


# ==========================================================================
# N4 — a missing required Spec Kit capability fails closed
# ==========================================================================


@pytest.mark.parametrize(
    "present",
    [(), ("SPECIFY_INIT_DIR",), ("SPECIFY_FEATURE_DIRECTORY",)],
    ids=["no-scripts-at-all", "only-init-dir", "only-feature-directory"],
)
def test_n4_a_missing_capability_refuses_and_writes_nothing(project, present):
    project.ok("init")
    if present:
        install_speckit_scripts(project, *present)
    before = project.state_file.read_bytes()

    result = project.run("feature", "bind")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "speckit_capability_missing"
    assert result.data["missing"] == [
        name for name in sdle.SPECKIT_REQUIRED_CAPABILITIES if name not in present
    ]
    assert result.data["probed_root"] == ".specify/scripts"
    assert "env" not in result.data
    assert project.state_file.read_bytes() == before


def test_n4_an_absent_speckit_refuses_speckit_missing(project):
    project.ok("init")
    shutil.rmtree(project.root / ".specify")

    result = project.run("feature", "bind")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "speckit_missing"
    assert "env" not in result.data


def test_n4_the_positive_control_binds_and_names_its_evidence(project):
    project.ok("init")
    full_speckit(project)

    data = project.ok("feature", "bind").data

    for name in sdle.SPECKIT_REQUIRED_CAPABILITIES:
        assert data["capabilities"][name]["supported"] is True
        assert data["capabilities"][name]["evidence"] == STUB_SCRIPT
    assert data["env"][0] == {
        "name": "SPECIFY_INIT_DIR", "value": str(project.root)
    }
    assert data["workitem_specs_root"] == f"workitems/{FIXTURE_WORKITEM_ID}/specs"


def test_n4_capabilities_reports_without_ever_refusing(project):
    """`feature capabilities` is a diagnostic: it reports, it never picks."""
    project.ok("init")

    result = project.ok("feature", "capabilities")

    assert result.exit_code == EXIT_OK
    assert result.data["missing"] == list(sdle.SPECKIT_REQUIRED_CAPABILITIES)
    assert result.data["scripts_present"] is False
    assert result.data["speckit_present"] is True


def test_n4_require_feature_refuses_until_the_directory_is_recorded(project):
    project.ok("init")
    full_speckit(project)

    refused = project.run("feature", "bind", "--require-feature")
    assert refused.exit_code == EXIT_REFUSED
    assert refused.reason == "feature_directory_unresolved"

    project.write_artifact(f"{project.feature_dir(FEATURE_ID)}/spec.md")
    project.ok("feature", "resolve")

    data = project.ok("feature", "bind", "--require-feature").data
    assert [e["name"] for e in data["env"]] == [
        "SPECIFY_INIT_DIR", "SPECIFY_FEATURE_DIRECTORY", "SPECIFY_FEATURE"
    ]
    assert data["env"][1]["value"] == project.feature_dir(FEATURE_ID)
    assert data["env"][2]["value"] == FEATURE_ID


def test_n4_preflight_reports_the_same_detection(project):
    project.ok("init")
    install_speckit_scripts(project, "SPECIFY_INIT_DIR")

    data = project.ok("preflight").data

    assert data["speckit_capability_problems"] == ["SPECIFY_FEATURE_DIRECTORY"]
    assert data["speckit_capabilities"]["SPECIFY_INIT_DIR"]["supported"] is True
    # Additive only: a missing capability is not a preflight refusal.
    assert data["problems"] == []


# ==========================================================================
# N5 — native artifacts are not duplicated
# ==========================================================================


def test_n5_adoption_moves_the_directory_and_leaves_exactly_one_copy(project):
    project.ok("init")
    source = project.write_artifact(f"specs/{FEATURE_ID}/spec.md")
    before = hashlib.sha256(source.read_bytes()).hexdigest()

    data = project.ok("feature", "resolve").data

    target = project.specs_root / FEATURE_ID / "spec.md"
    assert data["adopted"] == {
        "from": f"specs/{FEATURE_ID}",
        "to": f"workitems/{FIXTURE_WORKITEM_ID}/specs/{FEATURE_ID}",
    }
    assert target.is_file()
    assert not (project.root / "specs" / FEATURE_ID).exists()
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before
    assert list(project.root.rglob("spec.md")) == [target]


def test_n5_no_string_constant_in_the_engine_names_a_speckit_owned_file():
    """SDLE writes no `spec.md`, `plan.md`, `tasks.md` or `.specify/feature.json`.

    Proved structurally rather than by grep: no string *constant* anywhere in
    the engine ends with one of those names, so no code path can build such a
    path out of a literal. (`tasks.md` appears once in a comment; a comment is
    not a constant and cannot become a path.)
    """
    tree = ast.parse(SDLE_PY.read_text(encoding="utf-8"))
    offenders = sorted({
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and node.value.endswith(SPECKIT_OWNED_FILENAMES)
    })
    assert offenders == []


# ==========================================================================
# N6 — adoption safety
# ==========================================================================


def test_n6_an_occupied_target_refuses_without_touching_either_side(project):
    """The non-overwrite guard.

    Reachable when the target path exists but is **not** a directory: a
    directory there would have made tier 1 non-empty, and tier 1 would then
    have been chosen with no move attempted at all.
    """
    project.ok("init")
    source = project.write_artifact(f"specs/{FEATURE_ID}/spec.md")
    project.specs_root.mkdir(parents=True, exist_ok=True)
    blocker = project.specs_root / FEATURE_ID
    blocker.write_text("occupied\n", encoding="utf-8", newline="\n")

    result = project.run("feature", "resolve")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "feature_target_exists"
    assert source.is_file(), "the source must be left exactly where it was"
    assert blocker.read_text(encoding="utf-8") == "occupied\n"
    assert project.state()["specKit"]["featureDirectory"] is None


def test_n6_an_oserror_during_the_move_refuses_with_the_source_intact(
    project, monkeypatch
):
    project.ok("init")
    source = project.write_artifact(f"specs/{FEATURE_ID}/spec.md")
    before = project.state_file.read_bytes()

    class Exploding:
        @staticmethod
        def move(*_args, **_kwargs):
            raise OSError("device not ready")

    monkeypatch.setattr(sdle, "shutil", Exploding)

    result = project.run("feature", "resolve")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "feature_adopt_failed"
    assert source.is_file()
    assert project.state_file.read_bytes() == before


def test_n6_adoption_is_audited_with_from_and_to(project):
    project.ok("init", session="s")
    project.write_artifact(f"specs/{FEATURE_ID}/spec.md")

    project.ok("feature", "resolve", session="s")

    audit = project.audit_file.read_text(encoding="utf-8")
    assert "speckit_feature_adopted" in audit
    assert f"specs/{FEATURE_ID} -> workitems/{FIXTURE_WORKITEM_ID}" in audit
    assert project.ok("audit", "verify").data["matches"] is True


def test_n6_a_contained_directory_is_neither_moved_nor_audited(project):
    project.ok("init", session="s")
    project.write_artifact(f"{project.feature_dir(FEATURE_ID)}/spec.md")
    before = project.audit_file.read_text(encoding="utf-8")

    data = project.ok("feature", "resolve", session="s").data

    assert data["adopted"] is None
    assert project.audit_file.read_text(encoding="utf-8") == before


# ==========================================================================
# N7 — discovery tiering and ambiguity
# ==========================================================================


def test_n7_tier_one_wins_even_when_a_later_tier_is_far_newer(project):
    project.ok("init")
    project.write_artifact(f"{project.feature_dir('001-mine')}/spec.md")
    project.write_artifact("specs/002-native/spec.md")
    project.write_artifact(".specify/specs/003-legacy/spec.md")
    age(project.root / "specs" / "002-native", 2_000_000_000)

    data = project.ok("feature", "resolve").data

    assert data["tier"] == f"workitems/{FIXTURE_WORKITEM_ID}/specs"
    assert data["feature_id"] == "001-mine"
    assert data["adopted"] is None
    assert (project.root / "specs" / "002-native").is_dir(), "later tiers untouched"
    assert (project.root / ".specify" / "specs" / "003-legacy").is_dir()


def test_n7_tier_two_wins_over_tier_three_and_is_adopted(project):
    project.ok("init")
    project.write_artifact("specs/002-native/spec.md")
    project.write_artifact(".specify/specs/003-legacy/spec.md")
    age(project.root / ".specify" / "specs" / "003-legacy", 2_000_000_000)

    data = project.ok("feature", "resolve").data

    assert data["tier"] == "specs"
    assert data["feature_id"] == "002-native"
    assert data["feature_directory"] == (
        f"workitems/{FIXTURE_WORKITEM_ID}/specs/002-native"
    )
    assert (project.root / ".specify" / "specs" / "003-legacy").is_dir()


def test_n7_all_tiers_empty_refuses_and_lists_what_was_searched(project):
    project.ok("init")

    result = project.run("feature", "resolve")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "feature_unresolved"
    assert result.data["searched"] == [
        f"workitems/{FIXTURE_WORKITEM_ID}/specs", "specs", ".specify/specs"
    ]


def test_n7_ambiguity_inside_the_chosen_tier_still_refuses_and_lists(project):
    project.ok("init")
    project.write_artifact(f"{project.feature_dir('aaa')}/spec.md")
    project.write_artifact(f"{project.feature_dir('bbb')}/spec.md")
    for name in ("aaa", "bbb"):
        age(project.specs_root / name, 1_700_000_000)

    result = project.run("feature", "resolve")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "feature_ambiguous"
    assert sorted(result.data["candidates"]) == ["aaa", "bbb"]
    assert project.state()["specKit"]["featureDirectory"] is None


def test_n7_the_legacy_binding_keeps_its_baseline_behaviour(bare_project):
    """T11 removes the transitional rung; T04 must leave it working."""
    plant_legacy_workflow(bare_project)
    bare_project.write_artifact(".specify/specs/001-legacy/spec.md")
    bare_project.write_artifact("specs/002-native/spec.md")

    data = bare_project.ok("feature", "resolve").data

    assert data["searched"] == [".specify/specs"]
    assert data["feature_directory"] == ".specify/specs/001-legacy"
    assert data["adopted"] is None
    assert (bare_project.root / ".specify" / "specs" / "001-legacy").is_dir()
    assert (bare_project.root / "specs" / "002-native").is_dir()


# ==========================================================================
# N8 — migration 1.14 -> 1.15
# ==========================================================================


@pytest.mark.parametrize(
    "layout,expected",
    [
        ("workitem", f"workitems/{FIXTURE_WORKITEM_ID}/specs/{FEATURE_ID}"),
        ("legacy", f".specify/specs/{FEATURE_ID}"),
        ("both", f"workitems/{FIXTURE_WORKITEM_ID}/specs/{FEATURE_ID}"),
        ("neither", None),
    ],
)
def test_n8_the_feature_directory_is_derived_from_disk(project, layout, expected):
    project.ok("init")
    if layout in ("workitem", "both"):
        project.write_artifact(f"{project.feature_dir(FEATURE_ID)}/spec.md")
    if layout in ("legacy", "both"):
        project.write_artifact(f".specify/specs/{FEATURE_ID}/spec.md")
    project.write_state(as_v114(project, current_feature_id=FEATURE_ID))

    result = project.ok("migrate")

    state = project.state()
    assert result.data["steps"] == ["1.14->1.15"]
    assert "current_feature_id" not in state
    assert state["specKit"]["featureId"] == FEATURE_ID
    assert state["specKit"]["featureDirectory"] == expected
    assert state["specKit"]["workflowId"] is None
    assert state["specKit"]["runId"] is None


def test_n8_a_null_feature_id_migrates_to_an_all_null_object(project):
    project.ok("init")
    project.write_state(as_v114(project))

    project.ok("migrate")

    assert project.state()["specKit"] == {
        "featureId": None, "featureDirectory": None,
        "workflowId": None, "runId": None,
    }


@pytest.mark.parametrize(
    "args",
    [
        ("state", "dump"),
        ("header",),
        ("gate", "show", "--gate", "gate_spec"),
        ("artifact", "path", "--gate", "gate_spec"),
    ],
)
def test_n8_a_state_with_no_speckit_key_is_readable(project, args):
    """F1: no reader may index `specKit` or `current_feature_id` directly."""
    project.ok("init")
    state = as_v114(project)
    state.pop("current_feature_id", None)
    project.write_state(state)

    result = project.run(*args)

    assert result.exit_code == EXIT_OK, result
    assert "Traceback" not in result.stderr


# ==========================================================================
# N9 — resolve_artifact_path after the bridge deletion
# ==========================================================================


def test_n9_workitem_runtime_resolves_under_the_active_workitem(project):
    project.ok("init")

    data = project.ok("artifact", "path", "--gate", "gate_implement").data

    assert data["template"] == "{workitem_runtime}/implementation-manifest.md"
    assert data["resolved"] == (
        f"workitems/{FIXTURE_WORKITEM_ID}/.sdle/implementation-manifest.md"
    )


def test_n9_workitem_runtime_resolves_to_workflow_under_the_legacy_binding(
    bare_project,
):
    plant_legacy_workflow(bare_project)

    data = bare_project.ok("artifact", "path", "--gate", "gate_implement").data

    assert data["resolved"] == ".workflow/implementation-manifest.md"


def test_n9_an_unresolved_feature_directory_produces_the_documented_skip(project):
    project.ok("init")

    data = project.ok("artifact", "path", "--gate", "gate_spec").data

    assert data["resolved"] is None
    assert data["skipped_reason"] == "speckit_feature_directory is not resolved yet"


def test_n9_the_transitional_workflow_prefix_bridge_is_gone():
    """Finding NB-1 from T02: T04 owns the templates, so the bridge goes."""
    assert "legacy_prefix" not in SDLE_PY.read_text(encoding="utf-8")


# ==========================================================================
# N10 — the write-fence carve-out
#
# Lives in tests/test_hooks.py, added to the two existing parametrize lists:
# `workitems/<id>/specs/...` is allowed in all three path forms, while
# `workitems/index.md`, `workitems/<id>/workitem.json`, the whole
# `workitems/<id>/.sdle/` runtime and `workitems/<id>/reviews/` stay denied.
# The hook tests must drive the exact command string in settings.json, which
# is what that file is built to do.
# ==========================================================================


# ==========================================================================
# N11 — `feature bind` purity
# ==========================================================================


@pytest.mark.parametrize(
    "scenario",
    ["success", "capability_missing", "speckit_missing", "require_feature"],
)
def test_n11_feature_bind_writes_nothing_on_any_path(project, scenario):
    project.ok("init")
    if scenario == "speckit_missing":
        shutil.rmtree(project.root / ".specify")
    elif scenario != "capability_missing":
        full_speckit(project)

    before = sha_map(project.root)
    args = ["feature", "bind"]
    if scenario == "require_feature":
        args.append("--require-feature")

    result = project.run(*args)

    assert sha_map(project.root) == before, "feature bind is not pure"
    assert result.exit_code == (EXIT_OK if scenario == "success" else EXIT_REFUSED)
    assert result.stdout.strip(), "the envelope is always emitted"


# ==========================================================================
# N12 — contract §10 exit criterion
# ==========================================================================


def test_n12_two_workitems_run_the_full_flow_against_their_own_speckit_context(
    bare_project,
):
    bare_project.init_git()
    a = bare_project.as_workitem(create_wi(bare_project, "Wi A"))
    b = bare_project.as_workitem(create_wi(bare_project, "Wi B"))
    full_speckit(bare_project)

    drive_full_workflow(a, "001-alpha")
    a_state = a.state_file.read_bytes()
    a_audit = a.audit_file.read_bytes()
    a_specs = sha_map(a.specs_root)

    drive_full_workflow(b, "002-bravo")

    assert a.state()["current_phase"] == "complete"
    assert b.state()["current_phase"] == "complete"
    assert a.state()["specKit"]["featureDirectory"] == (
        "workitems/wi-a/specs/001-alpha"
    )
    assert b.state()["specKit"]["featureDirectory"] == (
        "workitems/wi-b/specs/002-bravo"
    )
    assert a.state_file.read_bytes() == a_state
    assert a.audit_file.read_bytes() == a_audit
    assert sha_map(a.specs_root) == a_specs

    # A20: T04 creates the two §10 extension points and never writes them.
    for view in (a, b):
        assert view.state()["specKit"]["workflowId"] is None
        assert view.state()["specKit"]["runId"] is None


# ==========================================================================
# N13 — `validate`'s new check
# ==========================================================================


def test_n13_validate_flags_a_feature_directory_outside_the_workitem(bare_project):
    view = bare_project.as_workitem(create_wi(bare_project, "Wi A"))
    view.ok("init")
    state = view.state()
    state["specKit"]["featureDirectory"] = "specs/001-elsewhere"
    view.write_state(state)

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "workitem_validation_failed"
    flagged = [
        f for f in result.data["findings"]
        if f["check"] == "feature_directory_outside_workitem"
    ]
    assert len(flagged) == 1
    assert flagged[0]["severity"] == "error"
    assert flagged[0]["workitem"] == "wi-a"


def test_n13_a_null_feature_directory_is_not_a_finding(bare_project):
    """A repository that has not reached its spec phase still validates clean."""
    view = bare_project.as_workitem(create_wi(bare_project, "Wi A"))
    view.ok("init")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK
    assert result.data["findings"] == []


def test_n13_a_contained_feature_directory_is_not_a_finding(bare_project):
    view = bare_project.as_workitem(create_wi(bare_project, "Wi A"))
    view.ok("init")
    view.write_artifact(f"{view.feature_dir('001-alpha')}/spec.md")
    view.ok("feature", "resolve")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK
    assert result.data["findings"] == []
