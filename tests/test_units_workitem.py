"""WorkItem identity — the naming, registry and metadata rules.

A WorkItem is created *before* the workflow is initialised, and its identity
never changes afterwards. These tests pin the identity rules themselves: name
normalisation, uniqueness without auto-suffixing, the append-only registry and
its integrity, and the `workitem.json` metadata.

Since v1.14 the WorkItem is also the runtime scope, so `init` requires a
resolved WorkItem and writes `workitems/<id>/.sdle/state.json`. The runtime
surface is pinned in `test_units_workitem_runtime.py`; what stays here is
identity. Every case runs against `bare_project` (see the fixture below), so
the registry assertions measure an empty starting registry.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from conftest import Project, sdle


@pytest.fixture
def project(bare_project: Project) -> Project:
    """This file asserts exact registry contents, so it needs an empty one.

    T02's shared `project` fixture pre-registers one WorkItem so the resolution
    ladder binds at rung 2 for the rest of the suite. Overriding it back to
    `bare_project` here keeps every assertion below byte-identical to T01.
    """
    return bare_project

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3

AUTO_ID = re.compile(r"^WI-[a-z0-9]([a-z0-9-]*[a-z0-9])?-\d{8}T\d{6}Z$")
ISO_Z = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

METADATA_KEYS = {
    "id", "name", "title", "type", "synopsis", "createdAt", "createdBy",
    "git", "sdleVersion",
}


def index_path(project: Project) -> Path:
    return project.root / "workitems" / "index.md"


def metadata(project: Project, workitem_id: str) -> dict:
    path = project.root / "workitems" / workitem_id / "workitem.json"
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create(project: Project, name: str, *extra: str):
    return project.run("workitem", "create", "--name", name, *extra)


# -- normalization ---------------------------------------------------------


@pytest.mark.parametrize("raw,expected", [
    ("Customer Notification Service", "customer-notification-service"),
    ("   Payment Retry   ", "payment-retry"),
    ("Payment_Retry", "payment-retry"),
    ("Foo!! Bar??", "foo-bar"),
    ("Foo -- Bar --", "foo-bar"),
    ("MiXeD CaSe", "mixed-case"),
    ("multi   space", "multi-space"),
    ("Release 2 Fix", "release-2-fix"),
])
def test_a_name_normalizes_to_kebab_case(project, raw, expected):
    result = create(project, raw)
    assert result.exit_code == EXIT_OK, result
    assert result.data["id"] == expected
    assert result.data["name"] == expected
    assert (project.root / "workitems" / expected / "workitem.json").is_file()


def test_leading_and_trailing_hyphens_are_stripped(project):
    # `--name=` form: a bare `--foo--bar--` would be read as an option.
    result = project.run("workitem", "create", "--name=--foo--bar--")
    assert result.exit_code == EXIT_OK, result
    assert result.data["id"] == "foo-bar"


# -- unsafe / path-traversal names -----------------------------------------


@pytest.mark.parametrize("raw,rule", [
    ("../escape", "unsafe_character"),
    ("a/b", "unsafe_character"),
    ("a\\b", "unsafe_character"),
    ("C:/absolute/path", "unsafe_character"),
    ("/etc/passwd", "unsafe_character"),
    ("a|b", "unsafe_character"),
    ("..", "empty_after_normalization"),
    (".", "empty_after_normalization"),
    ("!!!", "empty_after_normalization"),
    ("   ", "empty"),
    ("", "empty"),
    ("a" * 65, "too_long"),
    ("con", "reserved_name"),
    ("NUL", "reserved_name"),
    ("com1", "reserved_name"),
])
def test_an_unsafe_name_refuses_and_writes_nothing(project, raw, rule):
    result = create(project, raw)
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_name_invalid"
    assert result.data["rule"] == rule
    # Nothing anywhere: not under workitems/, and not beside it either.
    assert not (project.root / "workitems").exists()
    assert not (project.root / "escape").exists()
    assert not (project.root.parent / "escape").exists()


def test_a_64_character_name_is_still_accepted(project):
    result = create(project, "a" * 64)
    assert result.exit_code == EXIT_OK, result
    assert result.data["id"] == "a" * 64


# -- duplicate names -------------------------------------------------------


def test_a_duplicate_refuses_and_leaves_every_byte_in_place(project):
    assert create(project, "Customer Notification Service").exit_code == EXIT_OK
    meta_file = (project.root / "workitems" / "customer-notification-service"
                 / "workitem.json")
    before = (digest(index_path(project)), digest(meta_file))

    result = create(project, "customer   notification   service")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_exists"
    assert result.data["id"] == "customer-notification-service"
    assert (digest(index_path(project)), digest(meta_file)) == before


def test_a_case_only_collision_refuses(project):
    """Windows and macOS filesystems fold case; a case-variant id must not
    silently target an existing directory."""
    (project.root / "workitems" / "Payment-Retry").mkdir(parents=True)
    result = create(project, "Payment Retry")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_exists"
    assert result.data["id"] == "Payment-Retry"


def test_a_stray_directory_with_no_index_row_refuses(project):
    (project.root / "workitems" / "orphan-item").mkdir(parents=True)
    result = create(project, "Orphan Item")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_exists"
    assert not (project.root / "workitems" / "orphan-item" / "workitem.json").exists()


def test_no_auto_suffix_is_ever_invented(project):
    create(project, "Alpha One")
    create(project, "Alpha One")
    children = sorted(p.name for p in (project.root / "workitems").iterdir()
                      if p.is_dir())
    assert children == ["alpha-one"]


# -- auto-generation -------------------------------------------------------


def test_auto_generate_mints_a_timestamped_id_and_keeps_its_case(project):
    result = create(project, "Payment Retry", "--auto-generate")
    assert result.exit_code == EXIT_OK, result
    workitem_id = result.data["id"]
    assert AUTO_ID.match(workitem_id), workitem_id
    assert workitem_id.startswith("WI-payment-retry-")
    assert workitem_id.endswith("Z")
    # The normalization rules apply to the inferred segment only: the WI-
    # prefix and the T/Z of the timestamp are uppercase by contract.
    assert result.data["name"] == "payment-retry"
    assert metadata(project, workitem_id)["id"] == workitem_id


def test_an_auto_generated_name_segment_is_normalized(project):
    result = create(project, "Payment_Retry!!", "--auto-generate")
    assert result.exit_code == EXIT_OK, result
    assert result.data["id"].startswith("WI-payment-retry-")


# -- index append ----------------------------------------------------------


def test_the_first_create_writes_the_registry_skeleton(project):
    create(project, "Alpha One")
    lines = index_path(project).read_text(encoding="utf-8").splitlines()
    assert lines[0] == "# Work Items"
    assert lines[2] == "| Created | WorkItem | Type | Title | Synopsis |"
    assert lines[3] == "|---|---|---|---|---|"
    assert len(lines) == 5
    assert "Status" not in "\n".join(lines)  # append-only: no mutable status


def test_a_second_create_appends_and_leaves_the_first_row_byte_identical(project):
    create(project, "Alpha One")
    first_row = index_path(project).read_text(encoding="utf-8").splitlines()[4]
    create(project, "Beta Two")
    lines = index_path(project).read_text(encoding="utf-8").splitlines()
    assert len(lines) == 6
    assert lines[4] == first_row  # creation order, untouched
    assert lines[5].split("|")[2].strip() == "beta-two"


def test_a_pipe_in_the_synopsis_cannot_corrupt_the_registry(project):
    """Registry cells are pipe-delimited and unescaped, so the delimiter is
    neutralised on write. The metadata file keeps the text verbatim."""
    raw = "adds a | pipe and\na newline"
    assert create(project, "Alpha One", "--synopsis", raw).exit_code == EXIT_OK
    assert project.run("workitem", "list").exit_code == EXIT_OK
    assert metadata(project, "alpha-one")["synopsis"] == raw
    assert len(index_path(project).read_text(encoding="utf-8").splitlines()) == 5


# -- index malformed -------------------------------------------------------


MALFORMED = [
    "# WorkItems\n\n| Created | WorkItem | Type | Title | Synopsis |\n"
    "|---|---|---|---|---|\n",
    "# Work Items\n\n| Created | WorkItem | Type | Title |\n|---|---|---|---|\n",
    "# Work Items\n\n| Created | WorkItem | Type | Title | Synopsis |\n",
    "# Work Items\n\n| Created | WorkItem | Type | Title | Synopsis |\n"
    "|---|---|---|---|---|\n| a | b | c |\n",
    "",
]


@pytest.mark.parametrize("body", MALFORMED)
@pytest.mark.parametrize("command", [
    ("workitem", "create", "--name", "Late Arrival"),
    ("workitem", "list"),
])
def test_a_malformed_index_is_an_integrity_failure_and_is_never_repaired(
    project, body, command
):
    path = index_path(project)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8", newline="\n")
    before = digest(path)

    result = project.run(*command)
    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "index_malformed"
    assert digest(path) == before
    assert not (project.root / "workitems" / "late-arrival").exists()


# -- metadata creation -----------------------------------------------------


def test_metadata_carries_exactly_the_contract_key_set(project):
    create(project, "Customer Notification Service",
           "--synopsis", "Add configurable customer notifications.")
    doc = metadata(project, "customer-notification-service")
    assert set(doc) == METADATA_KEYS
    assert doc["id"] == doc["name"] == "customer-notification-service"
    assert doc["title"] == "Customer Notification Service"
    assert doc["type"] == "enhancement"
    assert doc["synopsis"] == "Add configurable customer notifications."
    assert ISO_Z.match(doc["createdAt"]), doc["createdAt"]
    assert doc["sdleVersion"] == sdle.CURRENT_VERSION
    assert set(doc["createdBy"]) == {"gitUserName", "gitUserEmail"}
    assert set(doc["git"]) == {"initialBranch"}


def test_type_and_synopsis_default(project):
    create(project, "Alpha One")
    doc = metadata(project, "alpha-one")
    assert doc["type"] == "enhancement"
    assert doc["synopsis"] is None


def test_an_explicit_type_is_recorded_without_being_policed(project):
    """Classification vocabulary is a later phase; T01 records the string."""
    create(project, "Alpha One", "--type", "defect")
    assert metadata(project, "alpha-one")["type"] == "defect"


# -- Git identity capture --------------------------------------------------


def test_git_identity_and_branch_are_captured(git_project):
    expected = git_project.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    create(git_project, "Alpha One")
    doc = metadata(git_project, "alpha-one")
    assert doc["createdBy"] == {
        "gitUserName": "SDLE Test",
        "gitUserEmail": "test@example.invalid",
    }
    assert doc["git"]["initialBranch"] == expected


def test_missing_git_identity_yields_nulls_without_refusing(project):
    result = create(project, "Alpha One")
    assert result.exit_code == EXIT_OK, result
    doc = metadata(project, "alpha-one")
    assert doc["createdBy"] == {"gitUserName": None, "gitUserEmail": None}
    assert doc["git"]["initialBranch"] is None


# -- workitem list ---------------------------------------------------------


def test_list_with_no_registry_is_empty_and_succeeds(project):
    result = project.run("workitem", "list")
    assert result.exit_code == EXIT_OK, result
    assert result.data == {"count": 0, "workitems": []}


def test_list_projects_the_registry_in_creation_order(project):
    create(project, "Alpha One")
    create(project, "Beta Two", "--type", "defect")
    result = project.run("workitem", "list")
    assert result.exit_code == EXIT_OK, result
    entries = result.data["workitems"]
    assert result.data["count"] == 2
    assert [e["id"] for e in entries] == ["alpha-one", "beta-two"]
    assert [e["type"] for e in entries] == ["enhancement", "defect"]
    assert [e["title"] for e in entries] == ["Alpha One", "Beta Two"]
    assert all(ISO_Z.match(e["created"]) for e in entries)


def test_list_reads_the_registry_not_the_directory_listing(project):
    create(project, "Alpha One")
    (project.root / "workitems" / "not-registered").mkdir()
    result = project.run("workitem", "list")
    assert [e["id"] for e in result.data["workitems"]] == ["alpha-one"]


# -- coexistence with the legacy runtime -----------------------------------


def test_creating_a_workitem_creates_no_runtime_state(project):
    create(project, "Alpha One")
    assert not (project.root / ".workflow").exists()


def test_init_records_the_resolved_workitem_in_state(project):
    """T01's guard asserted the opposite — that no `workitem` key existed —
    because T01 was forbidden from scoping state. T02 is the phase that scopes
    it (contract §8), so the guard inverts: the state file must name the
    WorkItem it belongs to, and must live under that WorkItem."""
    create(project, "Alpha One")
    project.workitem = "alpha-one"
    project.ok("init", session="testsess")
    state = project.state()
    assert state["workitem"] == "alpha-one"
    assert project.state_file == (
        project.root / "workitems" / "alpha-one" / ".sdle" / "state.json"
    )
    assert not (project.root / ".workflow").exists()


def test_a_workitem_does_not_change_what_init_and_advance_produce(project, tmp_path):
    """The §7 exit criterion, mechanically: which WorkItem identity a workflow
    carries changes nothing about what init and advance produce.

    T02 makes a resolved WorkItem mandatory, so the T01 control — a project
    with *no* WorkItem — is no longer initialisable by construction. The
    control now carries a different identity instead of none, which is the
    strongest comparison the post-T02 contract admits.
    """
    control_root = tmp_path / "control"
    shutil.copytree(project.root, control_root)
    control = Project(control_root, control_root / ".claude" / "skills" / "sdle",
                      workitem="control-item")
    assert create(control, "Control Item").exit_code == EXIT_OK

    control_init = control.run("init", session="testsess")
    assert create(project, "Customer Notification Service").exit_code == EXIT_OK
    project.workitem = "customer-notification-service"
    project_init = project.run("init", session="testsess")

    assert project_init.exit_code == control_init.exit_code == EXIT_OK
    for field in ("current_phase", "status", "progress", "project_name",
                  "workflow_version"):
        assert project.state()[field] == control.state()[field], field

    assert project.run("header", session="testsess").exit_code == EXIT_OK
    moved = project.run("advance", "--to", "gate_constitution", session="testsess")
    control_moved = control.run("advance", "--to", "gate_constitution",
                                session="testsess")
    assert moved.exit_code == EXIT_OK, moved
    assert moved.exit_code == control_moved.exit_code
    assert project.state()["current_phase"] == control.state()["current_phase"]


# -- CLI boundary ----------------------------------------------------------


def test_a_refusal_survives_the_process_boundary(project):
    result = project.run_cli("workitem", "create", "--name", "../escape")
    assert result.exit_code == EXIT_REFUSED
    assert json.loads(result.stdout)["reason"] == "workitem_name_invalid"
    assert "Traceback" not in result.stderr


def test_a_missing_name_is_a_usage_error(project):
    result = project.run_cli("workitem", "create")
    assert result.exit_code == EXIT_USAGE
    assert "Traceback" not in result.stderr
