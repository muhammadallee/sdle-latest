"""Contract §9 — WorkItem resolution and parallel developer isolation.

The whole §9 matrix, repository-root discovery, the persisted active context,
the branch rung, the branch-mismatch policy, `workitem resolve`, `sdle validate`
and the worktree exit criterion.

Two rules govern this file:

1. **No shared fixture is modified.** `conftest`'s `bare_project`, `project`,
   `started`, `git_project`, `started_git` and `Project`'s methods are used as
   they are; every helper this file needs — a CWD-relative launcher, a worktree
   builder, an active-context writer — is defined here.
2. **`conftest.Project.run` always pins `--project-root`**, so it can never
   exercise §9's launch-location discovery. `run_here` below is the only way to,
   and it is why this file exists as a separate module.
"""

from __future__ import annotations

import ast
import contextlib
import io
import json
import os
import subprocess
from pathlib import Path

import pytest

from conftest import SDLE_PY, Project, Result, sdle

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_INTEGRITY = 3


# --------------------------------------------------------------------------
# Helpers — local to this file by design (see the module docstring)
# --------------------------------------------------------------------------


def run_here(project: Project, *args, session: str | None = None) -> Result:
    """Invoke sdle from the *current* working directory, with no
    `--project-root`. The skill root is still pinned, because locating SKILL.md
    is not what §9 is about."""
    argv = ["--skill-root", str(project.skill_root)]
    if session:
        argv += ["--session", session]
    argv += [str(a) for a in args]

    out, err = io.StringIO(), io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = sdle.main(argv)
    except SystemExit as exc:  # argparse usage errors
        code = exc.code if isinstance(exc.code, int) else 2
    return Result(code, out.getvalue(), err.getvalue())


def create_wi(project: Project, name: str) -> str:
    """Register a WorkItem and return its id."""
    project.ok("workitem", "create", "--name", name)
    return sdle.normalize_workitem_name(name)


def paths_for(project: Project) -> "sdle.Paths":
    return sdle.resolve_paths(str(project.root), str(project.skill_root))


def context_file(project: Project) -> Path:
    return project.root / "workitems" / ".active-context.json"


def write_context(project: Project, payload: dict | str) -> Path:
    target = context_file(project)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = payload if isinstance(payload, str) else json.dumps(payload, indent=2)
    target.write_text(body, encoding="utf-8")
    return target


def branch_of(project: Project) -> str:
    return project.git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()


def sha_map(root: Path, skip: tuple[str, ...] = (".git",)) -> dict[str, str]:
    """Recursive content map of a scratch repository.

    `.git` is excluded because git's own bookkeeping is not SDLE state and a
    read-only `git rev-parse` may still touch it; everything SDLE could write
    is inside the map.
    """
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in skip for part in relative.parts):
            continue
        if path.is_file():
            out[relative.as_posix()] = sdle.sha256_file(path)
    return out


def index_lines(project: Project) -> list[str]:
    return (project.root / "workitems" / "index.md").read_text(
        encoding="utf-8"
    ).splitlines()


def write_index(project: Project, lines: list[str]) -> None:
    (project.root / "workitems" / "index.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def findings_named(result: Result, check: str) -> list[dict]:
    return [f for f in result.data.get("findings", []) if f["check"] == check]


# ==========================================================================
# N1 — the contract §9 resolution matrix, one test per row
# ==========================================================================


def test_matrix_cwd_inside_wi_a_with_many_workitems_binds_wi_a(
    bare_project, monkeypatch
):
    """| inside WI-A | many | irrelevant | WI-A |"""
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")

    monkeypatch.chdir(bare_project.root / "workitems" / wi_a)
    result = run_here(bare_project, "init", session="s")

    assert result.exit_code == EXIT_OK, result
    assert (bare_project.root / "workitems" / wi_a / ".sdle" / "state.json").is_file()
    assert not (bare_project.root / "workitems" / wi_b / ".sdle").exists()


def test_matrix_workitems_dir_with_one_active_and_a_branch_match_selects_it(
    bare_project, monkeypatch
):
    """| `workitems/` | one active | match | select |"""
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")

    monkeypatch.chdir(bare_project.root / "workitems")
    result = run_here(bare_project, "workitem", "resolve")

    assert result.exit_code == EXIT_OK, result
    assert result.data["resolved"] == wi_a
    assert result.data["branch"] == branch_of(bare_project)


def test_matrix_workitems_dir_with_many_plausible_and_no_signal_refuses(
    bare_project, monkeypatch
):
    """| `workitems/` | many plausible | none | ask | — and writes nothing."""
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")
    before = sha_map(bare_project.root)

    monkeypatch.chdir(bare_project.root / "workitems")
    result = run_here(bare_project, "state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"
    assert sorted(result.data["workitems"]) == sorted([wi_a, wi_b])
    assert [c["id"] for c in result.data["candidates"]] == [wi_a, wi_b]
    assert sha_map(bare_project.root) == before
    assert not (bare_project.root / ".workflow").exists()
    for wid in (wi_a, wi_b):
        assert not (bare_project.root / "workitems" / wid / ".sdle").exists()


def test_matrix_repo_root_with_a_unique_branch_match_binds_that_workitem(
    bare_project, monkeypatch
):
    """| repo root | branch maps WI-A | unique | WI-A |"""
    bare_project.init_git()
    home = branch_of(bare_project)
    bare_project.git("checkout", "-q", "-b", "feat-a")
    wi_a = create_wi(bare_project, "Alpha")
    bare_project.git("checkout", "-q", home)
    bare_project.git("checkout", "-q", "-b", "feat-b")
    create_wi(bare_project, "Bravo")
    bare_project.git("checkout", "-q", "feat-a")

    monkeypatch.chdir(bare_project.root)
    result = run_here(bare_project, "workitem", "resolve")

    assert result.exit_code == EXIT_OK, result
    assert result.data["resolved"] == wi_a
    assert result.data["rung"] == "branch"


def test_matrix_repo_root_with_mixed_signals_refuses(bare_project, monkeypatch):
    """| repo root | ambiguous | mixed | ask | — two WorkItems, one branch."""
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")

    monkeypatch.chdir(bare_project.root)
    result = run_here(bare_project, "state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"
    assert sorted(result.data["workitems"]) == sorted([wi_a, wi_b])


def test_matrix_nested_source_dir_with_a_valid_context_selects_it(
    bare_project, monkeypatch
):
    """| nested source dir | unique persisted context | valid | select |"""
    create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")
    bare_project.ok("workitem", "use", "--workitem", wi_b)

    nested = bare_project.root / "src" / "deep"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)
    result = run_here(bare_project, "workitem", "resolve")

    assert result.exit_code == EXIT_OK, result
    assert result.data["resolved"] == wi_b
    assert result.data["rung"] == "context"


def test_matrix_nested_source_dir_with_no_workitems_refuses_workitem_required(
    bare_project, monkeypatch
):
    """| nested source dir | none | none | create/ask |

    The engine half of "create/ask" is the refusal; the ask half is prompt-layer
    and lives in the parent session (CLAUDE.md invariant 8).
    """
    bare_project.init_git()
    nested = bare_project.root / "src" / "deep"
    nested.mkdir(parents=True)

    monkeypatch.chdir(nested)
    result = run_here(bare_project, "state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_required"


# ==========================================================================
# N2 — repository-root discovery (D1)
# ==========================================================================


def test_all_four_launch_locations_resolve_the_same_project_root(
    bare_project, monkeypatch
):
    wi_a = create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")
    nested = bare_project.root / "src" / "deep"
    nested.mkdir(parents=True)

    locations = [
        bare_project.root / "workitems" / wi_a,
        bare_project.root / "workitems",
        bare_project.root,
        nested,
    ]
    seen = []
    for location in locations:
        monkeypatch.chdir(location)
        result = run_here(bare_project, "workitem", "resolve")
        assert result.exit_code == EXIT_OK, result
        seen.append(Path(result.data["project_root"]).resolve())

    assert seen == [bare_project.root.resolve()] * len(locations)


def test_the_launch_cwd_is_reported_per_location(bare_project, monkeypatch):
    wi_a = create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")

    monkeypatch.chdir(bare_project.root / "workitems" / wi_a)
    inside = run_here(bare_project, "workitem", "resolve")
    monkeypatch.chdir(bare_project.root)
    at_root = run_here(bare_project, "workitem", "resolve")

    assert Path(inside.data["launch_cwd"]).resolve() == (
        bare_project.root / "workitems" / wi_a
    ).resolve()
    assert Path(at_root.data["launch_cwd"]).resolve() == bare_project.root.resolve()


def test_project_root_flag_still_overrides_the_launch_directory(
    bare_project, tmp_path, monkeypatch
):
    create_wi(bare_project, "Alpha")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    (elsewhere / ".git").mkdir()  # a marker that must NOT win

    monkeypatch.chdir(elsewhere)
    result = bare_project.run("workitem", "resolve")  # pins --project-root

    assert result.exit_code == EXIT_OK, result
    assert Path(result.data["project_root"]).resolve() == bare_project.root.resolve()


def test_the_nearest_marker_ancestor_wins(tmp_path):
    outer = tmp_path / "outer"
    (outer / ".git").mkdir(parents=True)
    inner = outer / "vendor" / "inner"
    (inner / ".git").mkdir(parents=True)
    deep = inner / "src" / "deep"
    deep.mkdir(parents=True)

    assert sdle.discover_project_root(deep) == inner
    assert sdle.discover_project_root(outer / "src") == outer


def test_the_workitem_registry_is_a_project_root_marker(tmp_path):
    root = tmp_path / "repo"
    (root / "workitems").mkdir(parents=True)
    (root / "workitems" / "index.md").write_text("# Work Items\n", encoding="utf-8")
    deep = root / "a" / "b"
    deep.mkdir(parents=True)

    assert sdle.discover_project_root(deep) == root


def test_the_legacy_runtime_is_a_project_root_marker(tmp_path):
    root = tmp_path / "repo"
    (root / ".workflow").mkdir(parents=True)
    (root / ".workflow" / "state.json").write_text("{}", encoding="utf-8")
    deep = root / "a"
    deep.mkdir(parents=True)

    assert sdle.discover_project_root(deep) == root


def test_discover_never_invents_a_root_inside_a_marker_free_tree(tmp_path):
    """The walk only ever goes *up*. A marker-free subtree can never produce a
    root inside itself, whatever the machine has above the temp directory."""
    plain = tmp_path / "plain" / "deeper"
    plain.mkdir(parents=True)

    discovered = sdle.discover_project_root(plain)
    assert discovered is None or not sdle._within(discovered, tmp_path / "plain")


def test_resolve_paths_falls_back_to_the_launch_directory(
    bare_project, tmp_path, monkeypatch
):
    """Pre-T03 behaviour, preserved: with no marker anywhere the launch
    directory *is* the project root."""
    plain = tmp_path / "plain"
    plain.mkdir()
    monkeypatch.setattr(sdle, "discover_project_root", lambda start: None)
    monkeypatch.chdir(plain)

    paths = sdle.resolve_paths(None, str(bare_project.skill_root))

    assert paths.project_root == plain.resolve()
    assert paths.launch_cwd == plain.resolve()


def test_an_explicit_root_with_an_outside_cwd_does_not_feed_the_cwd_rung(
    bare_project, tmp_path, monkeypatch
):
    create_wi(bare_project, "Alpha")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    paths = sdle.resolve_paths(str(bare_project.root), str(bare_project.skill_root))

    assert paths.launch_cwd == bare_project.root.resolve()
    assert sdle.cwd_workitem(paths) is None


# ==========================================================================
# N3 — rung 2 never falls through
# ==========================================================================


def test_cwd_inside_an_unregistered_workitem_directory_refuses(
    bare_project, monkeypatch
):
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")
    ghost = bare_project.root / "workitems" / "wi-ghost"
    ghost.mkdir()
    before = sha_map(bare_project.root)

    monkeypatch.chdir(ghost)
    result = run_here(bare_project, "state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_unregistered"
    assert result.data["directory"] == "wi-ghost"
    # The whole point: it binds NOTHING rather than picking a neighbour.
    for wid in (wi_a, wi_b):
        assert not (bare_project.root / "workitems" / wid / ".sdle").exists()
    assert sha_map(bare_project.root) == before


def test_workitem_resolve_reports_the_unregistered_directory(
    bare_project, monkeypatch
):
    create_wi(bare_project, "Alpha")
    ghost = bare_project.root / "workitems" / "wi-ghost"
    ghost.mkdir()

    monkeypatch.chdir(ghost)
    result = run_here(bare_project, "workitem", "resolve")

    assert result.exit_code == EXIT_OK, result
    assert result.data["resolved"] is None
    assert result.data["reason"] == "unregistered_directory"


def test_rung_two_beats_the_sole_registered_rung(bare_project, monkeypatch):
    """With exactly one registered WorkItem, standing inside an unregistered
    directory must still refuse — otherwise rung 3 would silently rescue it."""
    create_wi(bare_project, "Alpha")
    ghost = bare_project.root / "workitems" / "wi-ghost"
    ghost.mkdir()

    monkeypatch.chdir(ghost)
    result = run_here(bare_project, "state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_unregistered"


# ==========================================================================
# N4 — active-context lifecycle (D3)
# ==========================================================================


def test_workitem_create_writes_no_active_context(bare_project):
    create_wi(bare_project, "Alpha")
    assert not context_file(bare_project).exists()


def test_init_persists_the_active_context(bare_project):
    wi_a = create_wi(bare_project, "Alpha")
    result = bare_project.ok("init", session="s")

    payload = json.loads(context_file(bare_project).read_text(encoding="utf-8"))
    assert payload["workitem"] == wi_a
    assert payload["setBy"] == "init"
    assert payload["sdleVersion"] == sdle.CURRENT_VERSION
    assert result.data["active_context"] == wi_a


def test_workitem_use_rewrites_and_clear_removes_the_context(bare_project):
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")

    bare_project.ok("workitem", "use", "--workitem", wi_a)
    assert json.loads(
        context_file(bare_project).read_text(encoding="utf-8")
    )["workitem"] == wi_a

    bare_project.ok("workitem", "use", "--workitem", wi_b)
    payload = json.loads(context_file(bare_project).read_text(encoding="utf-8"))
    assert payload["workitem"] == wi_b
    assert payload["setBy"] == "use"

    cleared = bare_project.ok("workitem", "use", "--clear")
    assert cleared.data["cleared"] is True
    assert not context_file(bare_project).exists()

    again = bare_project.ok("workitem", "use", "--clear")
    assert again.data["cleared"] is False


def test_workitem_use_refuses_an_unregistered_id_and_writes_nothing(bare_project):
    wi_a = create_wi(bare_project, "Alpha")
    bare_project.ok("workitem", "use", "--workitem", wi_a)
    before = context_file(bare_project).read_bytes()

    result = bare_project.run("workitem", "use", "--workitem", "wi-ghost")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_unknown"
    assert context_file(bare_project).read_bytes() == before


def test_workitem_use_without_a_target_is_a_usage_error(bare_project):
    create_wi(bare_project, "Alpha")
    result = bare_project.run("workitem", "use")
    assert result.exit_code == 2, result
    assert result.reason == "workitem_required"


@pytest.mark.parametrize("payload", [
    "{ not json at all",
    '"a string, not an object"',
    '{"workitem": 17}',
    '{"workitem": "../escape"}',
    '{"workitem": "wi-ghost"}',
])
def test_an_invalid_context_is_skipped_never_fatal(bare_project, payload):
    create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")
    write_context(bare_project, payload)

    result = bare_project.run("state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"


def test_a_context_whose_directory_vanished_is_skipped(bare_project):
    import shutil

    wi_a = create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")
    bare_project.ok("workitem", "use", "--workitem", wi_a)
    shutil.rmtree(bare_project.root / "workitems" / wi_a)

    result = bare_project.run("state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"


def test_a_branch_stale_context_is_skipped(bare_project):
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")
    bare_project.ok("workitem", "use", "--workitem", wi_a)

    bound = bare_project.run("workitem", "resolve")
    assert bound.data["resolved"] == wi_a
    assert bound.data["rung"] == "context"

    bare_project.git("checkout", "-q", "-b", "somewhere-else")
    stale = bare_project.run("workitem", "resolve")

    assert stale.data["resolved"] is None
    assert stale.data["reason"] == "ambiguous"
    evidence = {c["id"]: c["evidence"] for c in stale.data["candidates"]}
    assert "context:stale" in evidence[wi_a]


def test_an_auto_generated_id_is_a_usable_active_context(bare_project):
    """`--auto-generate` mints `WI-<name>-<UTC>`, which does not match
    `WORKITEM_ID_RE`. A context naming one must still bind, or `workitem use`
    would persist something that can never resolve."""
    bare_project.ok("workitem", "create", "--name", "Alpha", "--auto-generate")
    create_wi(bare_project, "Bravo")
    auto = [
        row["WorkItem"] for row in sdle.read_index(paths_for(bare_project))
        if row["WorkItem"].startswith("WI-")
    ]
    assert len(auto) == 1
    bare_project.ok("workitem", "use", "--workitem", auto[0])

    result = bare_project.run("workitem", "resolve")

    assert result.data["resolved"] == auto[0]
    assert result.data["rung"] == "context"


def test_bind_workitem_writes_nothing_and_prints_nothing(bare_project):
    """F2: `bind_workitem` must stay pure, because `.claude/hooks/hooks.py`
    calls it speculatively from a PreToolUse callback."""
    wi_a = create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")
    bare_project.ok("workitem", "use", "--workitem", wi_a)
    paths = paths_for(bare_project)

    def call(explicit=None, for_init=False):
        out, err = io.StringIO(), io.StringIO()
        before = sha_map(bare_project.root)
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                bound = sdle.bind_workitem(paths, explicit, for_init=for_init)
            except sdle.SdleError as exc:
                bound = exc
        assert sha_map(bare_project.root) == before, "bind_workitem wrote something"
        assert out.getvalue() == "" and err.getvalue() == ""
        return bound

    # binds (context rung)
    assert call().workitem == wi_a
    # binds (explicit rung)
    assert call(explicit="bravo").workitem == "bravo"
    # refuses (unknown)
    assert isinstance(call(explicit="wi-ghost"), sdle.Refused)

    # refuses (ambiguous), with the context removed
    (bare_project.root / "workitems" / ".active-context.json").unlink()
    assert isinstance(call(), sdle.Refused)

    # the legacy rung, in a repository with no WorkItems at all
    legacy = Project(bare_project.root / "legacy", bare_project.skill_root)
    (legacy.root / ".workflow").mkdir(parents=True)
    (legacy.root / ".workflow" / "state.json").write_text("{}", encoding="utf-8")
    legacy_paths = paths_for(legacy)
    out, err = io.StringIO(), io.StringIO()
    before = sha_map(legacy.root)
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        bound = sdle.bind_workitem(legacy_paths)
    assert bound.workitem is None
    assert sha_map(legacy.root) == before
    assert out.getvalue() == "" and err.getvalue() == ""


# ==========================================================================
# N5 — the branch rung (D2 rung 5)
# ==========================================================================


def test_two_workitems_on_two_branches_bind_by_branch(bare_project):
    bare_project.init_git()
    home = branch_of(bare_project)
    bare_project.git("checkout", "-q", "-b", "feat-a")
    wi_a = create_wi(bare_project, "Alpha")
    bare_project.git("checkout", "-q", home)
    bare_project.git("checkout", "-q", "-b", "feat-b")
    wi_b = create_wi(bare_project, "Bravo")

    on_b = bare_project.run("workitem", "resolve")
    assert on_b.data["resolved"] == wi_b
    assert on_b.data["rung"] == "branch"

    bare_project.git("checkout", "-q", "feat-a")
    on_a = bare_project.run("workitem", "resolve")
    assert on_a.data["resolved"] == wi_a
    assert on_a.data["rung"] == "branch"


def test_a_branch_matching_neither_stays_ambiguous(bare_project):
    bare_project.init_git()
    home = branch_of(bare_project)
    bare_project.git("checkout", "-q", "-b", "feat-a")
    create_wi(bare_project, "Alpha")
    bare_project.git("checkout", "-q", home)
    bare_project.git("checkout", "-q", "-b", "feat-b")
    create_wi(bare_project, "Bravo")
    bare_project.git("checkout", "-q", "-b", "feat-c")

    result = bare_project.run("state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"


def test_two_workitems_on_one_branch_never_tie_break(bare_project):
    bare_project.init_git()
    bare_project.git("checkout", "-q", "-b", "shared")
    create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")

    result = bare_project.run("state", "get")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"


def test_a_detached_head_skips_the_branch_rung(bare_project):
    bare_project.init_git()
    bare_project.git("checkout", "-q", "-b", "feat-a")
    create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")
    head = bare_project.git("rev-parse", "HEAD").stdout.strip()
    bare_project.git("checkout", "-q", "--detach", head)

    assert sdle.current_branch(paths_for(bare_project)) is None
    result = bare_project.run("state", "get")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"


def test_no_git_skips_the_branch_rung(bare_project):
    create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")

    paths = paths_for(bare_project)
    assert sdle.current_branch(paths) is None
    assert sdle.branch_candidates(paths, ["alpha", "bravo"]) == []

    result = bare_project.run("state", "get")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous"


def test_branch_candidates_is_a_set_not_a_pick(bare_project):
    bare_project.init_git()
    bare_project.git("checkout", "-q", "-b", "shared")
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")

    paths = paths_for(bare_project)
    assert sorted(sdle.branch_candidates(paths, [wi_a, wi_b])) == sorted([wi_a, wi_b])


# ==========================================================================
# N6 — branch and starting SHA recorded (D4)
# ==========================================================================


def test_execution_records_branch_and_start_sha(bare_project):
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")

    doc = json.loads(
        (bare_project.root / "workitems" / wi_a / ".sdle" / "execution.json")
        .read_text(encoding="utf-8")
    )
    head = bare_project.git("rev-parse", "HEAD").stdout.strip()

    assert doc["git"]["branch"] == branch_of(bare_project)
    assert doc["git"]["startSha"] == head
    assert Path(doc["git"]["worktree"]).resolve() == bare_project.root.resolve()


def test_execution_records_nulls_without_a_repository(bare_project):
    wi_a = create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")

    doc = json.loads(
        (bare_project.root / "workitems" / wi_a / ".sdle" / "execution.json")
        .read_text(encoding="utf-8")
    )
    assert doc["git"]["branch"] is None
    assert doc["git"]["startSha"] is None


def test_execution_records_a_null_branch_on_a_detached_head(bare_project):
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    head = bare_project.git("rev-parse", "HEAD").stdout.strip()
    bare_project.git("checkout", "-q", "--detach", head)
    bare_project.ok("init", session="s")

    doc = json.loads(
        (bare_project.root / "workitems" / wi_a / ".sdle" / "execution.json")
        .read_text(encoding="utf-8")
    )
    assert doc["git"]["branch"] is None
    assert doc["git"]["startSha"] == head


def test_workitem_json_git_object_still_has_exactly_initial_branch(bare_project):
    """Regression pin: `tests/test_units_workitem.py` asserts this exact key
    set, so D4 must not touch `workitem.json`."""
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    doc = json.loads(
        (bare_project.root / "workitems" / wi_a / "workitem.json")
        .read_text(encoding="utf-8")
    )
    assert set(doc["git"]) == {"initialBranch"}


# ==========================================================================
# N7 — branch-mismatch policy (D5)
# ==========================================================================


# (argv, the action name the guard reports) — one row per member of
# `BRANCH_CRITICAL_ACTIONS`, checked for completeness by the test below.
CRITICAL_INVOCATIONS = [
    (("advance", "--to", "constitution_draft"), "advance"),
    (("gate", "approve", "--gate", "1"), "gate approve"),
    (("skip",), "skip"),
    (("restart", "--to", "1"), "restart"),
    (("reset",), "reset"),
    (("implement", "preflight"), "implement preflight"),
    (("manifest", "build"), "manifest build"),
    (("drift", "rebaseline", "--gate", "1"), "drift rebaseline"),
    (("artifact", "record", "--path", "requirements/todo-api.md"),
     "artifact record"),
]


@pytest.fixture
def mismatched(started_git: Project) -> Project:
    """An initialised, git-backed project whose checkout has moved off the
    branch the execution was started on."""
    started_git.home_branch = branch_of(started_git)
    started_git.git("checkout", "-q", "-b", "somewhere-else")
    return started_git


def test_the_invocation_list_covers_every_branch_critical_action():
    """One source of truth: if `BRANCH_CRITICAL_ACTIONS` grows, this list must
    grow with it or the parametrized refusal test silently under-covers."""
    covered = {
        tuple(action.split(" ")) if " " in action else action
        for _, action in CRITICAL_INVOCATIONS
    }
    assert covered == set(sdle.BRANCH_CRITICAL_ACTIONS)
    assert len(sdle.BRANCH_CRITICAL_ACTIONS) == 9


@pytest.mark.parametrize("invocation,action", CRITICAL_INVOCATIONS,
                         ids=[action for _, action in CRITICAL_INVOCATIONS])
def test_every_branch_critical_action_refuses_on_a_mismatched_branch(
    mismatched, invocation, action
):
    before = mismatched.state()

    result = mismatched.run(*invocation, session="testsess")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "branch_mismatch"
    assert result.data["current"] == "somewhere-else"
    assert result.data["recorded"] == mismatched.home_branch
    assert result.data["workitem"] == before["workitem"]
    assert result.data["action"] == action

    after = mismatched.state()
    assert after["current_phase"] == before["current_phase"]
    assert after["approvals"] == before["approvals"]
    assert after["pending_confirm_action"] == "branch_mismatch"
    assert "branch_mismatch_guard" in mismatched.audit_file.read_text(
        encoding="utf-8"
    )


def test_an_advisory_command_succeeds_on_a_mismatched_branch(mismatched):
    result = mismatched.run("state", "get")
    assert result.exit_code == EXIT_OK, result
    assert mismatched.state()["pending_confirm_action"] is None


def test_gate_reject_is_deliberately_advisory(mismatched):
    """A rejection can neither advance the workflow nor fingerprint an artifact
    as approved, so refusing it would be pure obstruction."""
    result = mismatched.run("gate", "reject", "--gate", "1",
                            "--reason", "not good enough", session="testsess")
    assert result.reason != "branch_mismatch", result


def test_header_reports_the_mismatch_without_changing_rendered(started_git):
    matched = started_git.ok("header")
    assert matched.data["branch_mismatch"] is None

    started_git.git("checkout", "-q", "-b", "somewhere-else")
    moved = started_git.ok("header")

    assert moved.data["rendered"] == matched.data["rendered"]
    assert moved.data["branch_mismatch"]["current"] == "somewhere-else"
    assert "Branch mismatch" in moved.stderr


def test_re_running_after_the_branch_refusal_proceeds_and_audits_acceptance(
    mismatched
):
    first = mismatched.run("artifact", "record", "--path",
                           "requirements/todo-api.md", session="testsess")
    assert first.reason == "branch_mismatch"

    second = mismatched.run("artifact", "record", "--path",
                            "requirements/todo-api.md", session="testsess")

    assert second.reason != "branch_mismatch", second
    audit = mismatched.audit_file.read_text(encoding="utf-8")
    assert "branch_mismatch_accepted" in audit
    assert mismatched.state()["pending_confirm_action"] is None


def test_skip_on_a_mismatched_branch_needs_both_acknowledgements(mismatched):
    """The declared double-acknowledgement, pinned exactly.

    Three invocations, two acknowledgements. It must never collapse into a
    single-step bypass, and it must never livelock.
    """
    state = mismatched.state()
    state["status"] = "failed"
    mismatched.write_state(state)

    first = mismatched.run("skip", session="testsess")
    assert first.exit_code == EXIT_REFUSED, first
    assert first.reason == "branch_mismatch"
    assert mismatched.state()["pending_confirm_action"] == "branch_mismatch"

    second = mismatched.run("skip", session="testsess")
    assert second.exit_code == EXIT_OK, second
    assert second.data["pending"] is True
    assert mismatched.state()["pending_confirm_action"] == "skip"

    third = mismatched.run("skip", "--confirm", session="testsess")
    assert third.exit_code == EXIT_OK, third
    assert third.reason is None
    assert mismatched.state()["pending_confirm_action"] is None

    audit = mismatched.audit_file.read_text(encoding="utf-8")
    assert "branch_mismatch_guard" in audit
    assert "branch_mismatch_accepted" in audit
    assert "SKIPPED WITH WARNING" in audit


def test_skip_confirm_alone_still_refuses_no_pending_confirmation(mismatched):
    """The pass-through on the command's own token is not a bypass: with
    nothing pending, `skip --confirm` is stopped by the branch guard first."""
    result = mismatched.run("skip", "--confirm", session="testsess")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "branch_mismatch"


def test_branch_mismatch_is_a_confirmable_action():
    assert "branch_mismatch" in sdle.CONFIRMABLE
    assert len(sdle.CONFIRMABLE) == 6


def test_no_mismatch_without_git(started):
    """No git means no branch, so there is nothing to disagree with."""
    assert sdle.branch_mismatch(
        sdle.bind_workitem(paths_for(started))
    ) is None
    assert started.run("advance", "--to", "constitution_draft",
                       session="testsess").reason != "branch_mismatch"


def test_no_mismatch_on_a_detached_head(started_git):
    head = started_git.git("rev-parse", "HEAD").stdout.strip()
    started_git.git("checkout", "-q", "--detach", head)
    assert sdle.branch_mismatch(sdle.bind_workitem(paths_for(started_git))) is None


def test_no_mismatch_when_the_recorded_branch_is_null(started_git):
    bound = sdle.bind_workitem(paths_for(started_git))
    doc = json.loads(bound.execution_file.read_text(encoding="utf-8"))
    doc["git"]["branch"] = None
    bound.execution_file.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    started_git.git("checkout", "-q", "-b", "somewhere-else")
    assert sdle.branch_mismatch(bound) is None


def test_no_mismatch_when_there_is_no_execution_record(started_git):
    """A legacy-bound runtime has no `execution.json` at all."""
    bound = sdle.bind_workitem(paths_for(started_git))
    bound.execution_file.unlink()
    started_git.git("checkout", "-q", "-b", "somewhere-else")
    assert sdle.branch_mismatch(bound) is None


# ==========================================================================
# N8 — `workitem resolve` (D6)
# ==========================================================================


def test_workitem_resolve_reports_each_rung(bare_project, monkeypatch):
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")

    explicit = bare_project.run("--workitem", wi_b, "workitem", "resolve")
    assert explicit.data["rung"] == "explicit"
    assert explicit.data["resolved"] == wi_b

    # `--project-root` is pinned here, so the CWD never feeds rung 2.
    bare_project.ok("workitem", "use", "--workitem", wi_b)
    context = bare_project.run("workitem", "resolve")
    assert context.data["rung"] == "context"
    assert context.data["resolved"] == wi_b

    # Standing inside a WorkItem outranks the persisted context.
    monkeypatch.chdir(bare_project.root / "workitems" / wi_a)
    inside = run_here(bare_project, "workitem", "resolve")
    assert inside.data["rung"] == "cwd"
    assert inside.data["resolved"] == wi_a


def test_workitem_resolve_reports_the_sole_rung(bare_project):
    wi_a = create_wi(bare_project, "Alpha")
    result = bare_project.run("workitem", "resolve")
    assert result.data["rung"] == "sole"
    assert result.data["resolved"] == wi_a


def test_workitem_resolve_never_refuses_and_never_picks(bare_project):
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")
    before = sha_map(bare_project.root)

    result = bare_project.run("workitem", "resolve")

    assert result.exit_code == EXIT_OK, result
    assert result.ok is True
    assert result.data["resolved"] is None
    assert result.data["rung"] is None
    assert result.data["reason"] == "ambiguous"
    assert [c["id"] for c in result.data["candidates"]] == [wi_a, wi_b]
    assert sha_map(bare_project.root) == before


def test_workitem_resolve_reports_per_candidate_evidence(bare_project):
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")
    bare_project.as_workitem(wi_a).ok("init", session="s")
    # `init` persisted a context for wi-a; clear it so the ambiguity survives.
    bare_project.ok("workitem", "use", "--clear")

    result = bare_project.run("workitem", "resolve")

    assert result.exit_code == EXIT_OK, result
    evidence = {c["id"]: c["evidence"] for c in result.data["candidates"]}
    assert f"branch:{branch_of(bare_project)}" in evidence[wi_a]
    assert "runtime" in evidence[wi_a]
    assert "runtime" not in evidence[wi_b]


def test_workitem_resolve_is_runtime_free_in_an_empty_repository(bare_project):
    result = bare_project.run("workitem", "resolve")
    assert result.exit_code == EXIT_OK, result
    assert result.data["resolved"] is None
    assert result.data["reason"] == "none"
    assert result.data["candidates"] == []


# ==========================================================================
# N9 — `sdle validate` (D8)
# ==========================================================================


def test_validate_is_clean_in_a_healthy_repository(bare_project):
    bare_project.init_git()
    create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK, result
    assert result.data["findings"] == []
    assert result.data["errors"] == 0


def test_validate_detects_duplicate_workitem_ids(bare_project):
    create_wi(bare_project, "Alpha")
    lines = index_lines(bare_project)
    write_index(bare_project, lines + [lines[-1].replace("alpha", "ALPHA")])

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "workitem_validation_failed"
    assert findings_named(result, "duplicate_workitem_id")
    assert findings_named(result, "duplicate_workitem_id")[0]["severity"] == "error"


def test_validate_detects_an_indexed_workitem_with_no_directory(bare_project):
    import shutil

    wi_a = create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")
    shutil.rmtree(bare_project.root / "workitems" / wi_a)

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    found = findings_named(result, "indexed_workitem_missing_directory")
    assert [f["workitem"] for f in found] == [wi_a]
    assert found[0]["severity"] == "error"


def test_validate_detects_a_directory_with_no_index_entry(bare_project):
    create_wi(bare_project, "Alpha")
    (bare_project.root / "workitems" / "wi-ghost").mkdir()

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    found = findings_named(result, "directory_missing_index_entry")
    assert [f["workitem"] for f in found] == ["wi-ghost"]


@pytest.mark.parametrize("mutate", ["delete", "garbage", "not-an-object", "wrong-id"])
def test_validate_detects_malformed_metadata(bare_project, mutate):
    wi_a = create_wi(bare_project, "Alpha")
    target = bare_project.root / "workitems" / wi_a / "workitem.json"
    if mutate == "delete":
        target.unlink()
    elif mutate == "garbage":
        target.write_text("{ nope", encoding="utf-8")
    elif mutate == "not-an-object":
        target.write_text("[1, 2, 3]", encoding="utf-8")
    else:
        doc = json.loads(target.read_text(encoding="utf-8"))
        doc["id"] = "somebody-else"
        target.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    found = findings_named(result, "malformed_metadata")
    assert [f["workitem"] for f in found] == [wi_a]
    assert found[0]["severity"] == "error"


def test_validate_reports_a_branch_mismatch_as_a_warning(bare_project):
    bare_project.init_git()
    create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")
    bare_project.git("checkout", "-q", "-b", "somewhere-else")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK, result
    found = findings_named(result, "branch_mismatch")
    assert found, result
    assert {f["severity"] for f in found} == {"warning"}
    assert result.data["errors"] == 0


def test_validate_detects_a_runtime_under_an_unregistered_directory(bare_project):
    create_wi(bare_project, "Alpha")
    ghost = bare_project.root / "workitems" / "wi-ghost" / ".sdle"
    ghost.mkdir(parents=True)
    (ghost / "state.json").write_text('{"workitem": "wi-ghost"}', encoding="utf-8")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    found = findings_named(result, "runtime_state_outside_workitem")
    assert [f["workitem"] for f in found] == ["wi-ghost"]
    assert found[0]["severity"] == "error"


def test_validate_detects_a_state_file_that_names_another_workitem(bare_project):
    wi_a = create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")
    bare_project.as_workitem(wi_a).ok("init", session="s")

    state_file = bare_project.root / "workitems" / wi_a / ".sdle" / "state.json"
    doc = json.loads(state_file.read_text(encoding="utf-8"))
    doc["workitem"] = "bravo"
    state_file.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    found = findings_named(result, "runtime_state_outside_workitem")
    assert [f["workitem"] for f in found] == [wi_a]


def test_validate_tolerates_a_state_file_with_no_workitem_field(bare_project):
    """A pre-1.14 state awaiting `migrate` is not a misplaced runtime."""
    wi_a = create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")
    state_file = bare_project.root / "workitems" / wi_a / ".sdle" / "state.json"
    doc = json.loads(state_file.read_text(encoding="utf-8"))
    doc.pop("workitem", None)
    state_file.write_text(json.dumps(doc, indent=2), encoding="utf-8")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK, result
    assert findings_named(result, "runtime_state_outside_workitem") == []


def test_validate_warns_about_a_surviving_legacy_runtime(bare_project):
    create_wi(bare_project, "Alpha")
    legacy = bare_project.root / ".workflow"
    legacy.mkdir()
    (legacy / "state.json").write_text("{}", encoding="utf-8")

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK, result
    found = findings_named(result, "runtime_state_outside_workitem")
    assert [f["severity"] for f in found] == ["warning"]


def test_validate_detects_a_traversal_shaped_index_id(bare_project):
    create_wi(bare_project, "Alpha")
    lines = index_lines(bare_project)
    write_index(bare_project, lines + ["| 2026-01-01T00:00:00Z | ../evil | "
                                       "enhancement | Evil | - |"])

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    found = findings_named(result, "path_escape")
    assert [f["workitem"] for f in found] == ["../evil"]
    assert found[0]["severity"] == "error"


def test_validate_detects_a_symlinked_workitem_directory(bare_project, tmp_path):
    wi_a = create_wi(bare_project, "Alpha")
    root = bare_project.root / "workitems"
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        os.symlink(outside, root / "linked", target_is_directory=True)
    except (OSError, NotImplementedError, AttributeError):
        # Windows without the symlink privilege. Assert the same check on the
        # `resolve()`-based escape rule instead of skipping: the suite keeps
        # zero skips (plan F13).
        assert sdle._escape_detail(root, "../evil") is not None
        assert sdle._escape_detail(root, "..") is not None
        assert sdle._escape_detail(root, wi_a) is None
        return

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    found = findings_named(result, "path_escape")
    assert [f["workitem"] for f in found] == ["linked"]
    assert "symlink" in found[0]["detail"]


def test_validate_runs_in_an_ambiguous_repository(bare_project):
    """F8: `validate` must survive the repositories it exists to diagnose."""
    create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")

    assert bare_project.run("state", "get").reason == "workitem_ambiguous"
    result = bare_project.run("validate")

    assert result.exit_code == EXIT_OK, result
    assert result.data["active"] is None
    assert findings_named(result, "active_workitem_unresolved")
    assert result.data["errors"] == 0


def test_validate_surfaces_a_corrupt_registry_as_an_integrity_failure(bare_project):
    create_wi(bare_project, "Alpha")
    write_index(bare_project, ["not the heading at all"])

    result = bare_project.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "index_malformed"


def test_validate_findings_all_have_the_declared_shape(bare_project):
    create_wi(bare_project, "Alpha")
    (bare_project.root / "workitems" / "wi-ghost").mkdir()

    result = bare_project.run("validate")

    for finding in result.data["findings"]:
        assert set(finding) == {"check", "severity", "workitem", "detail", "path"}
        assert finding["severity"] in {"error", "warning"}


# ==========================================================================
# N11 — the §9 exit criterion, worktree-shaped
# ==========================================================================


def test_two_worktrees_drive_two_workitems_with_no_flag(
    bare_project, tmp_path, monkeypatch
):
    """Contract §9 exit criterion: two developers on separate worktrees operate
    two different WorkItems with no shared SDLE state and no global lock."""
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")
    bare_project.git("add", "-A")
    bare_project.git("commit", "-q", "-m", "register workitems")

    second_root = tmp_path / "worktree-b"
    added = bare_project.git("worktree", "add", "-q", "-b", "feat-b",
                             str(second_root))
    # Fails loudly rather than skipping: the suite already hard-depends on git.
    assert added.returncode == 0, f"git worktree add failed: {added.stderr}"
    second = Project(second_root, bare_project.skill_root)

    monkeypatch.chdir(bare_project.root)
    used_a = run_here(bare_project, "workitem", "use", "--workitem", wi_a)
    assert used_a.exit_code == EXIT_OK, used_a
    a_init = run_here(bare_project, "init", session="dev-a")
    assert a_init.exit_code == EXIT_OK, a_init

    a_state = bare_project.root / "workitems" / wi_a / ".sdle" / "state.json"
    a_audit = bare_project.root / "workitems" / wi_a / ".sdle" / "audit.md"
    a_before = (a_state.read_bytes(), a_audit.read_bytes())

    monkeypatch.chdir(second_root)
    run_here(second, "workitem", "use", "--workitem", wi_b)
    b_init = run_here(second, "init", session="dev-b")
    assert b_init.exit_code == EXIT_OK, b_init

    b_state = second_root / "workitems" / wi_b / ".sdle" / "state.json"
    b_audit = second_root / "workitems" / wi_b / ".sdle" / "audit.md"

    # Each resolved its own WorkItem, with no --workitem anywhere.
    assert json.loads(a_state.read_text(encoding="utf-8"))["workitem"] == wi_a
    assert json.loads(b_state.read_text(encoding="utf-8"))["workitem"] == wi_b

    # Neither wrote into the other's WorkItem, in its own working directory.
    assert not (bare_project.root / "workitems" / wi_b / ".sdle").exists()
    assert not (second_root / "workitems" / wi_a / ".sdle").exists()

    # A further lifecycle write in each leaves the other byte-unchanged.
    monkeypatch.chdir(second_root)
    run_here(second, "audit", "append", "--phase", "constitution_draft",
             "--event", "note", "--message", "developer B working",
             session="dev-b")
    assert (a_state.read_bytes(), a_audit.read_bytes()) == a_before

    b_before = (b_state.read_bytes(), b_audit.read_bytes())
    monkeypatch.chdir(bare_project.root)
    run_here(bare_project, "audit", "append", "--phase", "constitution_draft",
             "--event", "note", "--message", "developer A working",
             session="dev-a")
    assert (b_state.read_bytes(), b_audit.read_bytes()) == b_before

    # Per-WorkItem locks, and no repository-global runtime anywhere.
    assert (bare_project.root / "workitems" / wi_a / ".sdle" / "lock").is_file()
    assert (second_root / "workitems" / wi_b / ".sdle" / "lock").is_file()
    assert not (bare_project.root / ".workflow").exists()
    assert not (second_root / ".workflow").exists()

    # Each worktree keeps its own developer-local context.
    assert json.loads(
        context_file(bare_project).read_text(encoding="utf-8")
    )["workitem"] == wi_a
    assert json.loads(
        context_file(second).read_text(encoding="utf-8")
    )["workitem"] == wi_b


def test_the_active_context_is_ignored_by_git(bare_project):
    """F7: a committed context would silently share one WorkItem between two
    developers."""
    bare_project.init_git()
    create_wi(bare_project, "Alpha")
    bare_project.ok("init", session="s")

    checked = subprocess.run(
        ["git", "check-ignore", "-q", "workitems/.active-context.json"],
        cwd=str(bare_project.root), capture_output=True, text=True,
    )
    assert checked.returncode == 0, "workitems/.active-context.json is not ignored"

    shipped = (Path(sdle.__file__).resolve().parent.parent / ".gitignore")
    assert "workitems/.active-context.json" in shipped.read_text(encoding="utf-8")


# ==========================================================================
# N12 — no fail-open
# ==========================================================================


def test_runtime_free_commands_is_a_closed_enumerated_set():
    assert sdle.RUNTIME_FREE_COMMANDS == frozenset({
        "lint-skill", "sha", "constants", "workitem", "migrate-workflow",
        "validate",
        # T05: repository-level configuration is owned by the repository, so
        # contract §11 requires it to resolve with no WorkItem bound.
        "config",
    })


def test_no_rung_ever_returns_an_unregistered_workitem(bare_project, monkeypatch):
    """Every rung either returns one *registered* id or falls through. This is
    the structural form of §9's "never silently pick"."""
    bare_project.init_git()
    wi_a = create_wi(bare_project, "Alpha")
    wi_b = create_wi(bare_project, "Bravo")

    states = []
    paths = paths_for(bare_project)
    states.append(sdle.resolve_decision(paths))                      # ambiguous
    states.append(sdle.resolve_decision(paths, wi_b))                # explicit
    bare_project.ok("workitem", "use", "--workitem", wi_a)
    states.append(sdle.resolve_decision(paths_for(bare_project)))    # context
    monkeypatch.chdir(bare_project.root / "workitems" / wi_b)
    states.append(sdle.resolve_decision(
        sdle.resolve_paths(None, str(bare_project.skill_root))))     # cwd

    for decision in states:
        assert decision.workitem is None or decision.workitem in decision.known
        assert decision.rung in {None, "explicit", "cwd", "sole", "context",
                                 "branch", "legacy"}


def test_the_ladder_has_no_tie_break_operator():
    """F1's code-review rule, made mechanical: `resolve_decision` may not order,
    minimise, maximise or index into a candidate collection."""
    source = ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))
    fn = next(
        node for node in ast.walk(source)
        if isinstance(node, ast.FunctionDef) and node.name == "resolve_decision"
    )
    called = {
        node.func.id for node in ast.walk(fn)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert not called & {"min", "max", "sorted"}
    # The one subscript is `known[0]`, guarded by `len(known) == 1`; a `[0]` on
    # `branch_matches` is likewise guarded by `len(...) == 1`.
    guards = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Compare)
        and isinstance(node.left, ast.Call)
        and getattr(node.left.func, "id", None) == "len"
    ]
    assert len(guards) >= 2


def test_workitem_rebinding_happens_only_at_the_declared_sites():
    """`dataclass_replace(paths, workitem=...)` is the act of binding. It must
    stay inside the ladder, its evidence helpers, `validate`'s read-only scan
    and `migrate-workflow`'s explicit binding."""
    source = ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))
    sites = set()
    for fn in ast.walk(source):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) == "dataclass_replace"
                    and any(k.arg == "workitem" for k in node.keywords)):
                sites.add(fn.name)
    assert sites == {
        "bind_workitem",
        "branch_candidates",
        "candidate_evidence",
        "collect_validation_findings",
        "_validate_runtime_state",
        "cmd_migrate_workflow",
    }


def test_the_active_context_is_written_only_by_the_declared_setters():
    """F2/P4: a hook must never become a writer."""
    source = ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))
    writers = set()
    for fn in ast.walk(source):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "id", None) in {
                        "write_active_context", "clear_active_context"}):
                writers.add(fn.name)
    assert writers == {"cmd_init", "cmd_migrate_workflow", "cmd_workitem_use"}
    assert sdle.ACTIVE_CONTEXT_SETTERS == ("init", "use", "migrate-workflow")


def test_init_still_refuses_a_legacy_workflow_unconditionally(bare_project):
    """P2/A19: T03 adds rungs above T02's refusals and weakens none of them."""
    create_wi(bare_project, "Alpha")
    legacy = bare_project.root / ".workflow"
    legacy.mkdir()
    (legacy / "state.json").write_text("{}", encoding="utf-8")

    result = bare_project.run("init", session="s")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "legacy_workflow_present"


def test_the_legacy_dual_read_rung_still_binds(bare_project):
    """P10: the transitional rung stays working until T11."""
    legacy = bare_project.root / ".workflow"
    legacy.mkdir()
    (legacy / "state.json").write_text("{}", encoding="utf-8")

    decision = sdle.resolve_decision(paths_for(bare_project))

    assert decision.rung == "legacy"
    assert decision.workitem is None
