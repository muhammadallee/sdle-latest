"""Contract §11 — the repository-level `.sdle/` configuration boundary.

Two rules govern this file, following `test_units_workitem_resolution.py`:

1. **No shared fixture is modified.** `conftest`'s fixtures are used exactly as
   they are; every helper this file needs is defined here.
2. **The proof of T05 is largely the *absence* of change.** A green suite alone
   would also pass for scaffolding nothing reads, so this file carries the
   positive proofs — the boundary is structural (N1), reachable with no
   WorkItem bound (N4), enforced in both directions (N7/N8) and inert with
   respect to the 18-phase flow (N10/N11).
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import re
import shutil
from pathlib import Path

import pytest

from conftest import SDLE_PY, Project, Result, sdle
from test_integration_01_happy_path import EXPECTED_TRAVERSAL, run_happy_path

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_INTEGRITY = 3

# The seven repository-configuration members introduced by T05. Named once,
# here, and reused by every containment proof below.
CONFIG_MEMBERS = (
    "config_root",
    "config_root_relative",
    "config_file",
    "policies_dir",
    "shared_templates_dir",
    "baseline_file",
    "implementation_state_dir",
    # T06: the first executable policy under `.sdle/policies/`. It is a
    # repository-configuration member by the same derivation rule, so it
    # inherits every containment proof in this file.
    "governance_policy_file",
)

# The WorkItem runtime members the boundary must stay clear of.
RUNTIME_MEMBERS = (
    "runtime",
    "state_file",
    "audit_file",
    "execution_file",
    "lock_file",
    "evidence_dir",
    "manifest_file",
    "completion_file",
)


# --------------------------------------------------------------------------
# Helpers — local to this file by design
# --------------------------------------------------------------------------


def paths_for(project: Project, workitem: str | None = None) -> "sdle.Paths":
    paths = sdle.resolve_paths(str(project.root), str(project.skill_root))
    if workitem is None:
        return paths
    return sdle.dataclass_replace(paths, workitem=workitem)


def sdle_ast() -> ast.Module:
    return ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))


def paths_class(tree: ast.Module) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Paths":
            return node
    raise AssertionError("class Paths not found in sdle.py")


def names_referenced(node: ast.AST) -> set[str]:
    """Every identifier and attribute name appearing under ``node``."""
    seen: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            seen.add(child.attr)
        elif isinstance(child, ast.Name):
            seen.add(child.id)
    return seen


# --------------------------------------------------------------------------
# N1 — the boundary is structural, not documentary
# --------------------------------------------------------------------------


def test_repository_configuration_is_derived_from_the_project_root_alone(
    bare_project,
):
    """N1: rebinding the WorkItem moves every runtime member and no
    configuration member. That derivation *is* §11's ownership split."""
    unbound = paths_for(bare_project)
    bound_a = paths_for(bare_project, "a")
    bound_b = paths_for(bare_project, "b")

    for member in CONFIG_MEMBERS:
        values = {getattr(p, member) for p in (unbound, bound_a, bound_b)}
        assert len(values) == 1, f"{member} varies with the bound WorkItem"

    root = bare_project.root.resolve()
    assert unbound.config_root == root / ".sdle"
    assert unbound.config_root_relative == ".sdle"
    assert unbound.config_file == root / ".sdle" / "config.json"
    assert unbound.policies_dir == root / ".sdle" / "policies"
    assert unbound.shared_templates_dir == root / ".sdle" / "templates"
    assert unbound.baseline_file == root / ".sdle" / "baseline.json"
    assert (unbound.implementation_state_dir
            == root / ".sdle" / "implementation-state")

    for member in RUNTIME_MEMBERS:
        assert getattr(bound_a, member) != getattr(bound_b, member), (
            f"{member} does not move with the bound WorkItem"
        )


def test_the_two_boundaries_never_contain_one_another(bare_project):
    """N1: repository configuration is never inside `workitems/`, and no
    WorkItem runtime is ever inside the configuration boundary."""
    for workitem in (None, "a", "b"):
        paths = paths_for(bare_project, workitem)
        relative = paths.config_root.relative_to(paths.project_root)
        assert "workitems" not in relative.parts
        assert not sdle._within(paths.runtime, paths.config_root)
        assert not sdle._within(paths.config_root, paths.runtime)


def test_no_configuration_property_reads_the_workitem_binding():
    """N1, at source level: the seven members must not so much as mention the
    binding. A property that read `self.workitem` would be a boundary in name
    only."""
    body = paths_class(sdle_ast()).body
    found = set()
    for node in body:
        if not isinstance(node, ast.FunctionDef) or node.name not in CONFIG_MEMBERS:
            continue
        found.add(node.name)
        referenced = names_referenced(node)
        leaked = referenced & {"workitem", "workitem_root", "runtime",
                               "legacy_workflow", "workitems"}
        assert not leaked, f"{node.name} references {sorted(leaked)}"
    assert found == set(CONFIG_MEMBERS)


# --------------------------------------------------------------------------
# N12 — `.sdle/config.json` as a project-root marker
# --------------------------------------------------------------------------

# `PROJECT_ROOT_MARKERS` exactly as it stood at the T05 rollback point,
# `7b054ee`. Used as the control for the no-op proof below.
MARKERS_BEFORE_T05 = (
    ("workitems", "index.md"),
    (".workflow", "state.json"),
    (".git",),
)


def test_the_configuration_boundary_is_a_project_root_marker(tmp_path):
    """N12(a): a repository whose only marker is its configuration boundary
    still resolves. Without this, `config init` from a subdirectory would
    write a second boundary there."""
    root = tmp_path / "repo"
    (root / ".sdle").mkdir(parents=True)
    (root / ".sdle" / "config.json").write_text("{}", encoding="utf-8")
    deep = root / "a" / "b"
    deep.mkdir(parents=True)

    assert sdle.discover_project_root(deep) == root


def test_the_nearest_marker_still_wins_across_the_two_boundaries(tmp_path):
    """N12(b): appending a marker changes which *level* stops the walk, never
    the nearest-ancestor rule itself."""
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    inner = outer / "vendor" / "inner"
    (inner / ".sdle").mkdir(parents=True)
    (inner / ".sdle" / "config.json").write_text("{}", encoding="utf-8")
    deep = inner / "src"
    deep.mkdir(parents=True)
    assert sdle.discover_project_root(deep) == inner

    other = tmp_path / "other"
    (other / ".sdle").mkdir(parents=True)
    (other / ".sdle" / "config.json").write_text("{}", encoding="utf-8")
    nested = other / "vendor" / "nested"
    (nested / ".git").mkdir(parents=True)
    below = nested / "src"
    below.mkdir(parents=True)
    assert sdle.discover_project_root(below) == nested


@pytest.mark.parametrize("shape", ["nested_git", "workitem_registry",
                                   "legacy_runtime", "marker_free"])
def test_the_new_marker_is_a_no_op_for_every_pre_t05_tree(
    tmp_path, monkeypatch, shape
):
    """N12(c), the control case: for a tree containing no `.sdle/config.json`,
    discovery returns exactly what it returned at `7b054ee`. Proved by running
    the same four shapes the existing marker tests cover against both marker
    tuples."""
    root = tmp_path / "repo"
    if shape == "nested_git":
        (root / ".git").mkdir(parents=True)
        (root / "vendor" / "inner" / ".git").mkdir(parents=True)
        start = root / "vendor" / "inner" / "src"
    elif shape == "workitem_registry":
        (root / "workitems").mkdir(parents=True)
        (root / "workitems" / "index.md").write_text("# Work Items\n",
                                                     encoding="utf-8")
        start = root / "a" / "b"
    elif shape == "legacy_runtime":
        (root / ".workflow").mkdir(parents=True)
        (root / ".workflow" / "state.json").write_text("{}", encoding="utf-8")
        start = root / "a"
    else:
        start = root / "plain" / "deeper"
    start.mkdir(parents=True, exist_ok=True)

    after = sdle.discover_project_root(start)
    monkeypatch.setattr(sdle, "PROJECT_ROOT_MARKERS", MARKERS_BEFORE_T05)
    before = sdle.discover_project_root(start)

    assert after == before


def test_the_marker_tuple_gained_exactly_one_entry():
    """The appended marker is additive: every pre-T05 marker survives, in
    order, and the new one is last."""
    assert sdle.PROJECT_ROOT_MARKERS == MARKERS_BEFORE_T05 + ((".sdle", "config.json"),)


# --------------------------------------------------------------------------
# N2–N6, N13, N14 — the two commands
# --------------------------------------------------------------------------


def run_at(project: Project, root: Path, *args) -> "Result":
    """Invoke sdle with an arbitrary ``--project-root``.

    `conftest.Project.run` always pins the scratch root, so it cannot express
    "resolve a root that is itself inside `workitems/`". This can.
    """
    argv = ["--project-root", str(root), "--skill-root", str(project.skill_root)]
    argv += [str(a) for a in args]
    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sdle.main(argv)
    except SystemExit as exc:  # argparse usage errors
        code = exc.code if isinstance(exc.code, int) else 2
    return Result(code, out.getvalue(), err.getvalue())


def sha_map(root: Path, skip: tuple[str, ...] = (".git",)) -> dict[str, str]:
    """Recursive content map of a scratch tree. Local by design."""
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in skip for part in relative.parts):
            continue
        if path.is_file():
            out[relative.as_posix()] = sdle.sha256_file(path)
    return out


def create_wi(project: Project, name: str) -> str:
    project.ok("workitem", "create", "--name", name)
    return sdle.normalize_workitem_name(name)


def config_root(project: Project) -> Path:
    return project.root / ".sdle"


def findings_named(result, check: str) -> list[dict]:
    return [f for f in (result.data.get("findings") or [])
            if f["check"] == check]


# -- N2 ---------------------------------------------------------------------


def test_config_init_creates_exactly_the_boundary(bare_project):
    """N2: `config init` writes the boundary and nothing else."""
    result = bare_project.run("config", "init")
    assert result.exit_code == EXIT_OK, result

    root = config_root(bare_project)
    assert json.loads((root / "config.json").read_text(encoding="utf-8")) == {
        "configVersion": "1", "policyFormat": "json",
    }
    for name in ("policies", "templates", "implementation-state"):
        assert (root / name).is_dir()
        assert (root / name / ".gitkeep").is_file()

    assert sorted(sha_map(root)) == [
        "config.json",
        "implementation-state/.gitkeep",
        "policies/.gitkeep",
        "templates/.gitkeep",
    ]
    # The slot is named by `Paths.baseline_file`; §14 owns the file.
    assert not (root / "baseline.json").exists()


def test_config_init_touches_no_workitem_runtime(bare_project):
    """N2: no registry, no legacy runtime, no state and no audit appear."""
    before = sha_map(bare_project.root)
    bare_project.ok("config", "init")
    after = sha_map(bare_project.root)

    assert not (bare_project.root / "workitems").exists()
    assert not (bare_project.root / ".workflow").exists()

    added = set(after) - set(before)
    # `.claude/skills/sdle/templates/state.json` ships with the fixture, so the
    # meaningful assertion is that no *new* runtime file appeared.
    assert not [name for name in added
                if Path(name).name in {"state.json", "audit.md",
                                       "execution.json", "lock"}]
    assert all(name.startswith(".sdle/") for name in added), sorted(added)
    assert {k: v for k, v in after.items() if not k.startswith(".sdle/")} == before


def test_config_init_never_overwrites(bare_project):
    """N2: the second run refuses and changes nothing."""
    bare_project.ok("config", "init")
    before = sha_map(config_root(bare_project))

    again = bare_project.run("config", "init")

    assert again.exit_code == EXIT_REFUSED
    assert again.reason == "config_exists"
    assert sha_map(config_root(bare_project)) == before


def test_config_init_leaves_existing_boundary_content_alone(bare_project):
    """N2: a directory that already holds something keeps it."""
    policies = config_root(bare_project) / "policies"
    policies.mkdir(parents=True)
    planted = policies / "kept.json"
    planted.write_text('{"kept": true}\n', encoding="utf-8")
    digest = sdle.sha256_file(planted)

    bare_project.ok("config", "init")

    assert sdle.sha256_file(planted) == digest


# -- N3 ---------------------------------------------------------------------


@pytest.mark.parametrize("depth", ["registry", "workitem"])
@pytest.mark.parametrize("command", [("config", "init"), ("config", "show")])
def test_a_root_inside_workitems_is_refused(bare_project, depth, command):
    """N3: repository configuration is never owned by a WorkItem."""
    workitem = create_wi(bare_project, "Alpha")
    registry = bare_project.root / "workitems"
    root = registry if depth == "registry" else registry / workitem
    before = sha_map(bare_project.root)

    result = run_at(bare_project, root, *command)

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "config_root_inside_workitem"
    assert sha_map(bare_project.root) == before


@pytest.mark.parametrize("depth", ["registry", "workitem"])
def test_validate_reports_a_root_inside_workitems(bare_project, depth):
    """N3: `validate` names the same check the refusal does."""
    workitem = create_wi(bare_project, "Alpha")
    registry = bare_project.root / "workitems"
    root = registry if depth == "registry" else registry / workitem

    result = run_at(bare_project, root, "validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert findings_named(result, "config_root_inside_workitem")


# -- N4 — contract §11's exit criterion -------------------------------------


@pytest.mark.parametrize("count", [0, 1, 2])
def test_repository_configuration_resolves_with_no_workitem_bound(
    bare_project, count
):
    """N4: `config` never runs the resolution ladder, whatever the registry
    holds. That independence *is* §11's exit criterion."""
    for index in range(count):
        create_wi(bare_project, f"Item{index}")

    assert bare_project.run("config", "show").exit_code == EXIT_OK
    assert bare_project.run("config", "init").exit_code == EXIT_OK
    assert bare_project.run("config", "show").exit_code == EXIT_OK


def test_a_runtime_command_still_refuses_where_config_succeeds(bare_project):
    """N4: the contrast that makes the previous test meaningful — the same
    repository, the same absence of `--workitem`, opposite outcomes."""
    ambiguous = bare_project.run("state", "get")
    assert ambiguous.exit_code == EXIT_REFUSED
    assert ambiguous.reason == "workitem_required"
    assert bare_project.run("config", "show").exit_code == EXIT_OK

    create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")

    refused = bare_project.run("state", "get")
    assert refused.exit_code == EXIT_REFUSED
    assert refused.reason == "workitem_ambiguous"
    assert bare_project.run("config", "show").exit_code == EXIT_OK
    assert bare_project.run("config", "init").exit_code == EXIT_OK


def test_config_is_a_runtime_free_command():
    assert "config" in sdle.RUNTIME_FREE_COMMANDS


# -- N5 ---------------------------------------------------------------------


def test_config_show_reports_the_defaults_and_creates_nothing(bare_project):
    """N5: the pre-T05 shape — no `.sdle/` — is a supported, silent state."""
    before = sha_map(bare_project.root)

    result = bare_project.run("config", "show")

    assert result.exit_code == EXIT_OK, result
    assert result.data["root"] == ".sdle"
    assert result.data["present"] is False
    assert result.data["config"]["configVersion"] == "1"
    assert result.data["config"]["policyFormat"] == "json"
    assert sorted(result.data["defaults_applied"]) == ["configVersion",
                                                       "policyFormat"]
    assert result.data["members"] == {
        "config": ".sdle/config.json",
        "policies": ".sdle/policies",
        "templates": ".sdle/templates",
        "baseline": ".sdle/baseline.json",
        "implementation_state": ".sdle/implementation-state",
    }
    assert not config_root(bare_project).exists()
    assert sha_map(bare_project.root) == before


def test_config_show_reports_a_present_boundary(bare_project):
    bare_project.ok("config", "init")
    before = sha_map(bare_project.root)

    result = bare_project.run("config", "show")

    assert result.exit_code == EXIT_OK, result
    assert result.data["present"] is True
    assert result.data["defaults_applied"] == []
    assert result.data["config"] == {"configVersion": "1",
                                     "policyFormat": "json"}
    assert sha_map(bare_project.root) == before


# -- N6 ---------------------------------------------------------------------

MALFORMED = {
    "not_json": "this is not json\n",
    "json_array": '["configVersion"]\n',
    "json_scalar": '"json"\n',
    "unsupported_version": '{"configVersion": "2", "policyFormat": "json"}\n',
    "version_not_a_string": '{"configVersion": 1, "policyFormat": "json"}\n',
    "format_absent": '{"configVersion": "1"}\n',
    "format_yaml": '{"configVersion": "1", "policyFormat": "yaml"}\n',
    "format_toml": '{"configVersion": "1", "policyFormat": "toml"}\n',
}


def plant_config(project: Project, body: str) -> Path:
    target = config_root(project) / "config.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")
    return target


@pytest.mark.parametrize("case", sorted(MALFORMED))
def test_malformed_configuration_fails_closed_in_both_consumers(
    bare_project, case
):
    """N6: `config show` refuses and `validate` reports an error — and both
    say the *same thing*, because there is exactly one predicate."""
    plant_config(bare_project, MALFORMED[case])

    shown = bare_project.run("config", "show")
    assert shown.exit_code == EXIT_REFUSED, shown
    assert shown.reason == "config_malformed"

    validated = bare_project.run("validate")
    assert validated.exit_code == EXIT_INTEGRITY, validated
    reported = findings_named(validated, "config_malformed")
    assert len(reported) == 1
    assert reported[0]["severity"] == "error"

    assert shown.envelope["message"] == reported[0]["detail"]


def test_a_yaml_policy_format_names_the_dependency_decision(bare_project):
    """N6: the recorded JSON decision is enforced, not merely documented."""
    plant_config(bare_project, MALFORMED["format_yaml"])

    shown = bare_project.run("config", "show")

    assert shown.reason == "config_malformed"
    message = shown.envelope["message"]
    assert "explicitly accepted" in message
    assert "home-grown parser" in message


def test_config_init_still_refuses_an_existing_malformed_file(bare_project):
    """A malformed file is still a file: `init` never overwrites it."""
    plant_config(bare_project, MALFORMED["not_json"])

    result = bare_project.run("config", "init")

    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "config_exists"


# -- N13 --------------------------------------------------------------------


def two_workitems_one_mid_run(project: Project) -> tuple[str, str]:
    """Two registered WorkItems, the first of them partway through a run."""
    first = create_wi(project, "Alpha")
    second = create_wi(project, "Bravo")
    driver = project.as_workitem(first)
    # T06: `advance` refuses `governance_missing` without a record.
    driver.record_governance()
    driver.ok("init", session="purity")
    driver.write_artifact(".specify/memory/constitution.md")
    driver.ok("advance", "--to", "gate_constitution")
    return first, second


def test_the_config_commands_are_pure_toward_workitem_runtime(bare_project):
    """N13: nothing outside `.sdle/` moves, in either direction."""
    two_workitems_one_mid_run(bare_project)
    outside = sha_map(bare_project.root, skip=(".git", ".sdle"))

    bare_project.ok("config", "init")
    assert sha_map(bare_project.root, skip=(".git", ".sdle")) == outside

    boundary = sha_map(config_root(bare_project))
    bare_project.ok("config", "show")
    bare_project.ok("validate")

    assert sha_map(bare_project.root, skip=(".git", ".sdle")) == outside
    assert sha_map(config_root(bare_project)) == boundary


def test_no_config_command_appends_an_audit_entry(bare_project):
    """N13: `config` is outside the single-writer path entirely."""
    first, _ = two_workitems_one_mid_run(bare_project)
    audit = bare_project.root / "workitems" / first / ".sdle" / "audit.md"
    digest = sdle.sha256_file(audit)

    bare_project.ok("config", "init")
    bare_project.ok("config", "show")
    bare_project.ok("validate")

    assert sdle.sha256_file(audit) == digest


# -- N14 --------------------------------------------------------------------


def test_config_init_writes_only_inside_the_boundary(bare_project):
    """N14: the success path and both refusal paths stay inside
    `config_root`."""
    before = sha_map(bare_project.root)
    bare_project.ok("config", "init")
    added = set(sha_map(bare_project.root)) - set(before)
    assert added and all(name.startswith(".sdle/") for name in added)

    settled = sha_map(bare_project.root)
    assert bare_project.run("config", "init").reason == "config_exists"
    assert sha_map(bare_project.root) == settled


def test_config_init_inherits_write_atomic(bare_project, monkeypatch):
    """N14: an injected failure leaves no partial `config.json`, and a re-run
    completes. The injection point is `write_atomic` itself, so this also
    pins that `config init` never hand-rolls the write."""
    real = sdle.write_atomic

    def failing(path: Path, text: str) -> None:
        if path.name == "config.json":
            raise OSError("injected")
        real(path, text)

    monkeypatch.setattr(sdle, "write_atomic", failing)
    with pytest.raises(OSError):
        bare_project.run("config", "init")

    root = config_root(bare_project)
    assert not (root / "config.json").exists()
    assert list(root.glob(".config.json.*.tmp")) == []
    assert (root / "policies" / ".gitkeep").is_file()

    monkeypatch.setattr(sdle, "write_atomic", real)
    assert bare_project.run("config", "init").exit_code == EXIT_OK
    assert json.loads((root / "config.json").read_text(encoding="utf-8")) == {
        "configVersion": "1", "policyFormat": "json",
    }


# --------------------------------------------------------------------------
# N7–N9 — the bidirectional leak detector
# --------------------------------------------------------------------------

# Derived, never re-listed: a phase that adds a runtime member gets a new
# parametrisation for free. The probe instance is inert — only member *names*
# are read from it.
RUNTIME_MEMBER_NAMES = sdle.workitem_runtime_member_names(
    sdle.Paths(project_root=Path("/probe-root"),
               skill_root=Path("/probe-skill"),
               workitem="probe")
)

CONFIG_MEMBER_NAMES = tuple(
    getattr(sdle.Paths(project_root=Path("/probe-root"),
                       skill_root=Path("/probe-skill")), member).name
    for member in ("config_file", "policies_dir", "shared_templates_dir",
                   "baseline_file", "implementation_state_dir")
)


# -- N7 ---------------------------------------------------------------------


@pytest.mark.parametrize("member", RUNTIME_MEMBER_NAMES)
def test_lifecycle_state_under_the_repository_boundary_is_an_error(
    bare_project, member
):
    """N7: WorkItem lifecycle state has no business in `.sdle/`. This is one
    of the four detectors for §11's "do not move lifecycle rules yet"."""
    create_wi(bare_project, "Alpha")
    bare_project.ok("config", "init")
    planted = config_root(bare_project) / member
    planted.write_text("planted\n", encoding="utf-8")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    reported = findings_named(result, "lifecycle_state_in_repository_config")
    assert len(reported) == 1
    assert reported[0]["severity"] == "error"
    assert reported[0]["path"] == str(planted)
    assert member in reported[0]["detail"]


def test_the_runtime_member_names_are_derived_from_paths():
    """N7's parametrisation is only meaningful if it really is derived."""
    assert set(RUNTIME_MEMBER_NAMES) == {
        "state.json", "audit.md", "execution.json", "lock",
        "evidence", "implementation-manifest.md", "completion-summary.json",
        # T06: the governance record and the review ledger are WorkItem-owned.
        # `governance.json` must never share a basename with the repository
        # policy file (`governance-policy.json`), or the disjointness assertion
        # below and the two leak detectors would contradict each other.
        "governance.json", "reviews.json",
        # T08: the §14 discovery record. WorkItem-owned by the same argument —
        # it is work one WorkItem performed, and the repository baseline that
        # outlives it *references* this file rather than copying it. Adding it
        # here is what gives the leak detector its new parametrisation for
        # free, in both directions.
        "discovery.json",
    }
    assert set(CONFIG_MEMBER_NAMES) == {
        "config.json", "policies", "templates", "baseline.json",
        "implementation-state",
    }
    assert not set(RUNTIME_MEMBER_NAMES) & set(CONFIG_MEMBER_NAMES)


# -- N8 ---------------------------------------------------------------------


@pytest.mark.parametrize("member", CONFIG_MEMBER_NAMES)
@pytest.mark.parametrize("has_state", [True, False])
def test_repository_configuration_under_a_workitem_is_an_error(
    bare_project, member, has_state
):
    """N8: the reverse direction, and the reason it cannot live in
    `_validate_runtime_state` — that function returns early when the WorkItem
    has no `state.json`, which is exactly the `has_state=False` case here."""
    workitem = create_wi(bare_project, "Alpha")
    if has_state:
        bare_project.as_workitem(workitem).ok("init", session="leak")
    runtime = bare_project.root / "workitems" / workitem / ".sdle"
    runtime.mkdir(parents=True, exist_ok=True)
    planted = runtime / member
    if member.endswith(".json"):
        planted.write_text("{}\n", encoding="utf-8")
    else:
        planted.mkdir()

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    reported = findings_named(result, "repository_config_in_workitem")
    assert len(reported) == 1
    assert reported[0]["severity"] == "error"
    assert reported[0]["workitem"] == workitem
    assert reported[0]["path"] == str(planted)


def test_an_unregistered_workitem_directory_is_scanned_too(bare_project):
    """N8: the scan follows the same registered-or-on-disk set the rest of
    `validate` uses, so a stray directory cannot hide a leak."""
    create_wi(bare_project, "Alpha")
    stray = bare_project.root / "workitems" / "bravo" / ".sdle"
    stray.mkdir(parents=True)
    (stray / "config.json").write_text("{}\n", encoding="utf-8")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert findings_named(result, "repository_config_in_workitem")


# -- N9 ---------------------------------------------------------------------


def test_validate_stays_clean_with_no_repository_boundary(bare_project):
    """N9(a): the exact pre-T05 shape. This is the regression guard for
    `test_validate_is_clean_in_a_healthy_repository`."""
    bare_project.init_git()
    create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")

    assert not config_root(bare_project).exists()
    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK, result
    assert result.data["findings"] == []
    assert result.data["errors"] == 0


def test_validate_stays_clean_after_config_init(bare_project):
    """N9(b): creating the boundary is not itself a finding."""
    bare_project.init_git()
    create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")
    bare_project.ok("config", "init")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK, result
    assert result.data["findings"] == []
    assert result.data["errors"] == 0


# --------------------------------------------------------------------------
# N10 — the differential no-lifecycle-change proof
# --------------------------------------------------------------------------
#
# A green suite is *necessary* evidence for T05 and nowhere near sufficient:
# inert scaffolding nothing reads would leave it green too. This test is the
# positive statement that the 18-phase lifecycle behaves identically whether or
# not the repository configuration boundary exists, and — clause 4 — that the
# lifecycle never reads or writes it.

AUDIT_HEADER = re.compile(r"^## AUDIT \[[^\]]*\] \| (?P<phase>.+?) — (?P<event>.+)$")

# Fields that legitimately differ between two runs of the same workflow:
# wall-clock stamps, content hashes and the git ref the run started from.
RUN_VARYING = {
    "last_updated", "audit_sha", "artifact_shas", "current_artifact_sha",
    "security_review_artifact", "implementation_base_ref",
    # Timestamps nested inside `approvals` and `phase_history`.
    "timestamp", "completed_at",
}


def scrub(value):
    """Drop run-varying fields, recursively."""
    if isinstance(value, dict):
        return {k: scrub(v) for k, v in value.items() if k not in RUN_VARYING}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def audit_events(project: Project) -> list[tuple[str, str]]:
    text = project.audit_file.read_text(encoding="utf-8")
    return [
        (match.group("phase"), match.group("event"))
        for line in text.splitlines()
        for match in [AUDIT_HEADER.match(line)]
        if match
    ]


def clone_project(project: Project, destination: Path) -> Project:
    """A second scratch project identical to the first, byte for byte."""
    shutil.copytree(project.root, destination)
    return Project(
        destination,
        destination / ".claude" / "skills" / "sdle",
        workitem=project.workitem,
        pin=project.pin,
    )


def test_the_configuration_boundary_changes_no_lifecycle_behaviour(
    git_project, tmp_path
):
    """N10: two identical repositories, one configured, produce the same
    18-phase run — and the configured one's `.sdle/` is untouched by it."""
    plain = git_project
    configured = clone_project(plain, tmp_path / "configured")
    configured.ok("config", "init")
    # `.sdle/` is versioned engineering evidence (§19), so the realistic state
    # for a run is "committed". Leaving it uncommitted is a *deliberately*
    # different situation — `SDLE_OWNED_PREFIXES` is not extended to `.sdle/`,
    # so the implement-preflight dirty-tree guard sees it exactly as it would
    # see any other uncommitted file. That is pinned separately below.
    configured.git("add", "-A")
    configured.git("commit", "-q", "-m", "repository configuration boundary")
    boundary_before = sha_map(configured.root / ".sdle")
    assert boundary_before, "config init produced nothing to compare"

    traversal_plain = run_happy_path(plain)
    traversal_configured = run_happy_path(configured)

    # 1. identical traversals, both equal to the transcript's.
    assert traversal_plain == EXPECTED_TRAVERSAL
    assert traversal_configured == EXPECTED_TRAVERSAL

    # 2. identical ordered audit event sequences.
    assert audit_events(configured) == audit_events(plain)

    # 3. identical state, modulo the fields two runs legitimately differ in.
    assert scrub(configured.state()) == scrub(plain.state())

    # 4. The strongest clause, restated at T08 and deliberately not weakened.
    #
    #    T05 could say "the lifecycle never touches the boundary" because
    #    nothing in the lifecycle wrote it. §14 changes that on purpose: a
    #    GREENFIELD completion establishes `.sdle/baseline.json`, which is the
    #    convergence artifact the contract asks for, so "never touched" is no
    #    longer a true statement about the engine and asserting it would be
    #    asserting a fiction. The clause therefore becomes exact: the run adds
    #    **exactly one** boundary entry, that entry is the baseline, and every
    #    pre-existing entry is byte-identical afterwards. A second new file, or
    #    any mutation of `config.json`, still fails here.
    boundary_after = sha_map(configured.root / ".sdle")
    added = set(boundary_after) - set(boundary_before)

    assert added == {"baseline.json"}, added
    assert {k: v for k, v in boundary_after.items() if k in boundary_before} \
        == boundary_before
    assert set(boundary_before) - set(boundary_after) == set()
    # And the plain repository — which never ran `config init` — gets the same
    # one file, so the baseline is a lifecycle artifact rather than something
    # the configuration boundary's existence provoked.
    assert set(sha_map(plain.root / ".sdle")) == {"baseline.json"}


def test_the_scrubbed_state_comparison_still_has_teeth(git_project):
    """N10 is only meaningful if `scrub` leaves the lifecycle facts in."""
    run_happy_path(git_project)
    scrubbed = scrub(git_project.state())

    assert scrubbed["current_phase"] == "complete"
    assert scrubbed["workflow_version"] == "1.16"
    assert scrubbed["workitem"] == git_project.workitem
    assert scrubbed["progress"] == "18/18"
    assert [entry["phase"] for entry in scrubbed["phase_history"]]
    assert all(entry["decision"] == "approved"
               for entry in scrubbed["approvals"].values())
    assert scrubbed["specKit"]["featureId"] == "001-todo-api"


# --------------------------------------------------------------------------
# N11 — source-level containment
# --------------------------------------------------------------------------

CONFIG_REFERENCE_SITES = {
    "cmd_config_init",
    "cmd_config_show",
    "read_repo_config",
    "repo_config_findings",
    "collect_validation_findings",
    # T06: exactly one new function legitimately reaches the boundary — the
    # fail-closed governance policy reader. No lifecycle command may.
    "read_governance_policy",
    # T08: §14 gives `.sdle/baseline.json` its schema and makes it real, so the
    # boundary gains readers and — for the first time — a writer. The set stays
    # closed and stays asserted by exact equality; what changed is that it is
    # no longer empty of lifecycle-adjacent work.
    #
    #   `read_baseline`         the fail-closed reader (never fail-open)
    #   `baseline_findings`     the single validity predicate
    #   `baseline_descriptor`   builds the {path, sha256} references
    #   `establish_baseline`    the ONLY writer, called from exactly one place
    #   `baseline_precondition` R1/R2, called from exactly one place
    #   `cmd_baseline_show` / `cmd_baseline_validate`  the two read-only commands
    #
    # `cmd_gate_approve` and `cmd_init` are deliberately absent: they reach the
    # baseline *through* `establish_baseline` and `baseline_precondition`, and
    # name no configuration member themselves. That is what keeps
    # `test_no_lifecycle_command_reads_the_repository_configuration` true
    # unchanged.
    "read_baseline",
    "baseline_findings",
    "baseline_state",
    "baseline_descriptor",
    "establish_baseline",
    "baseline_precondition",
    "cmd_baseline_show",
    "cmd_baseline_validate",
}

RUNTIME_WRITERS = {
    "read_state", "save_state", "append_audit", "write_active_context",
    "clear_active_context", "touch_lock", "bind_workitem",
}


def functions_outside_paths(tree: ast.Module) -> list[ast.FunctionDef]:
    """Every function in `sdle.py` except the `Paths` property definitions
    themselves — those *are* the boundary, so they are not "references" to
    it."""
    definitions = {id(node) for node in paths_class(tree).body
                   if isinstance(node, ast.FunctionDef)}
    return [node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and id(node) not in definitions]


def test_the_repository_configuration_members_have_a_closed_reference_set():
    """N11(1): a closed, named set of functions may reach the repository
    configuration boundary, and it is asserted by exact equality.

    T05 could say "nothing in the lifecycle may" because nothing in the engine
    read the boundary at all. T06 added one reader. T08 adds §14's baseline —
    which the lifecycle genuinely writes, at completion. The containment proof
    is therefore that the reaching set is *closed and named*, and the separate
    clause below is what keeps the lifecycle commands themselves out of it.
    """
    tree = sdle_ast()
    sites = set()
    for fn in functions_outside_paths(tree):
        if names_referenced(fn) & set(CONFIG_MEMBERS):
            sites.add(fn.name)
    assert sites == CONFIG_REFERENCE_SITES


def test_the_configuration_commands_never_touch_runtime_state():
    """N11(2): `config` is outside the single-writer path (invariant 6) and
    outside the resolution ladder."""
    tree = sdle_ast()
    for fn in functions_outside_paths(tree):
        if fn.name not in {"cmd_config_init", "cmd_config_show",
                           "read_repo_config", "repo_config_findings"}:
            continue
        called = {node.func.id for node in ast.walk(fn)
                  if isinstance(node, ast.Call)
                  and isinstance(node.func, ast.Name)}
        assert not called & RUNTIME_WRITERS, f"{fn.name} calls {called}"


def test_no_lifecycle_command_reads_the_repository_configuration():
    """N11(3), rewritten at T06 — the phase §11 and ADR-002 named as the one
    where policy under `.sdle/policies/` becomes executable.

    The original form filtered by function-NAME PREFIX. That was adequate
    while nothing in the engine read the boundary at all, but it is exactly
    the wrong shape once the lifecycle genuinely consults policy: a helper
    named outside `cmd_gate*` / `cmd_advance*` / `cmd_approve*` / `cmd_init*`
    could read `.sdle/` and the test would still pass, so the guardrail would
    die silently while looking alive.

    The rewrite is strictly stronger. Clauses (a) and (b) are stated over
    *every* function in the engine, so no name can slip past them; clause (c)
    is the original assertion, kept, so the prefix guard below it stays
    load-bearing.
    """
    tree = sdle_ast()
    engine = functions_outside_paths(tree)

    # (a) The executable-policy member has exactly one reader, and the
    #     lifecycle reaches policy only through it. `read_governance_policy`
    #     is fail-closed: it refuses a malformed policy rather than
    #     defaulting, so "one reader" is also "one refusal site".
    policy_readers = {fn.name for fn in engine
                      if "governance_policy_file" in names_referenced(fn)}
    assert policy_readers == {"read_governance_policy"}, policy_readers

    # (b) `.sdle/config.json` itself is still read by nothing outside the
    #     configuration group. Closed over the whole engine, so a new reader
    #     anywhere fails here rather than passing on a naming technicality.
    config_readers = {fn.name for fn in engine
                      if "config_file" in names_referenced(fn)}
    assert config_readers == {
        "cmd_config_init",
        "cmd_config_show",
        "collect_validation_findings",
        "read_repo_config",
        "repo_config_findings",
    }, config_readers
    lifecycle_readers = {name for name in config_readers
                         if name.startswith("cmd_")
                         and not name.startswith("cmd_config")}
    assert lifecycle_readers == set(), lifecycle_readers

    # (c) The original clause, unchanged in effect: a gate, an advance, an
    #     approval or an init that reached ANY configuration member would be
    #     the leak §11 forbids.
    prefixes = ("cmd_gate", "cmd_advance", "cmd_approve", "cmd_init")
    for fn in engine:
        if not fn.name.startswith(prefixes):
            continue
        assert not names_referenced(fn) & set(CONFIG_MEMBERS), fn.name


def test_the_lifecycle_command_prefixes_actually_match_something():
    """Guard against the previous test passing vacuously."""
    tree = sdle_ast()
    prefixes = ("cmd_gate", "cmd_advance", "cmd_approve", "cmd_init")
    matched = {fn.name for fn in functions_outside_paths(tree)
               if fn.name.startswith(prefixes)}
    assert {"cmd_init", "cmd_advance"} <= matched, matched


def test_an_uncommitted_boundary_is_not_treated_as_sdle_owned(git_project):
    """The deliberate contrast with `workitems/` (T02 added that one to
    `SDLE_OWNED_PREFIXES`; T05 does **not** add `.sdle/`).

    `SDLE_OWNED_PREFIXES` exists to hide paths SDLE itself writes *during a
    run*. Nothing writes `.sdle/` mid-run, and it is versioned, so an
    uncommitted change to it should trip the implement-preflight dirty-tree
    guard exactly as an uncommitted source change does. That direction fails
    closed, and it keeps a §18 Wave A guardrail byte-for-byte.
    """
    assert ".sdle/" not in sdle.SDLE_OWNED_PREFIXES
    git_project.ok("init", session="dirty")
    git_project.ok("config", "init")

    result = git_project.run("implement", "preflight")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "dirty_tree"
    entries = result.data.get("entries") or []
    assert any(".sdle/" in entry.replace("\\", "/") for entry in entries), entries
