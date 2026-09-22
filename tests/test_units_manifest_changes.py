"""D03 (SDLE-DEFECT-STABILIZATION-01) — the implementation change set is
measured from the pinned base, and every consumer reads the same one.

Before this iteration `manifest build` listed `git status` plus `git diff
--name-only HEAD`: a comparison against the *current* commit. Anything the
implementation committed after `implement preflight` pinned
`implementation_base_ref` was therefore invisible — absent from the Gate 7
file list and never read by the secrets scan. Renames arrived as the literal
string `"old -> new"`. The security-review evidence used a different
exclusion list and, with no pinned base, silently fell back to `HEAD~1`.

Now one selector, `implementation_changes`, compares the pinned base with the
working tree (committed + staged + unstaged) plus untracked files, and both
the manifest and `security-review evidence` consume it.
"""

from __future__ import annotations

import shutil

import pytest

from conftest import FIXTURE_WORKITEM_ID, PASSING_TEST_COMMAND
from test_units_flow_model import drive

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3

# A syntactically valid AWS access key id that belongs to nobody. Split so
# this file does not itself trip the secrets tripwire it is testing.
FAKE_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
       b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x00IEND\xaeB`\x82")


def at_implement(project) -> str:
    """Pinned base with a tracked source tree to rename and delete from."""
    drive(project, "GREENFIELD", stop="implement")
    project.write_artifact("src/keep.py")
    project.write_artifact("src/rename_me.py", "# rename me\n" + "x = 1\n" * 30)
    project.write_artifact("src/delete_me.py")
    project.write_artifact("src/edit_me.py")
    project.git("add", "-A")
    project.git("commit", "-q", "-m", "existing code")
    project.ok("implement", "preflight", "--bypass")
    return project.state()["implementation_base_ref"]


def build(project):
    return project.ok("manifest", "build", "--test-command",
                      PASSING_TEST_COMMAND)


def by_path(result) -> dict:
    return {c["path"]: c for c in result.data["changes"]}


def test_d03_a_change_committed_after_the_base_is_listed_and_scanned(
        git_project):
    at_implement(git_project)
    git_project.write_artifact(
        "src/feature.py", f'aws = "{FAKE_KEY}"\n' + "# pad\n" * 30)
    git_project.git("add", "src/feature.py")
    git_project.git("commit", "-q", "-m", "implement the feature")

    result = build(git_project)

    assert "src/feature.py" in result.data["files"]
    assert by_path(result)["src/feature.py"]["status"] == "A"
    assert any(f.startswith("src/feature.py:1") for f in result.data["secrets"])

    # The review consumer reads the same selection, not a second one.
    evidence = git_project.ok("security-review", "evidence").data
    assert [c["path"] for c in evidence["changes"]] == [
        c["path"] for c in result.data["changes"]]
    assert "src/feature.py" in evidence["diff"]


def test_d03_staged_unstaged_and_untracked_changes_are_all_listed(
        git_project):
    at_implement(git_project)
    git_project.write_artifact("src/staged.py")
    git_project.git("add", "src/staged.py")
    git_project.write_artifact("src/edit_me.py", "# edited\n" + "y = 2\n" * 30)
    git_project.write_artifact("src/untracked/new.py")

    changes = by_path(build(git_project))

    assert changes["src/staged.py"]["status"] == "A"
    assert changes["src/edit_me.py"]["status"] == "M"
    assert changes["src/untracked/new.py"]["status"] == "A"
    assert changes["src/untracked/new.py"]["untracked"] is True


def test_d03_a_rename_and_a_delete_are_represented(git_project):
    at_implement(git_project)
    git_project.git("mv", "src/rename_me.py", "src/renamed.py")
    git_project.git("rm", "-q", "src/delete_me.py")
    git_project.git("commit", "-q", "-m", "move and remove")

    result = build(git_project)
    changes = by_path(result)

    assert changes["src/renamed.py"]["status"] == "R"
    assert changes["src/renamed.py"]["old_path"] == "src/rename_me.py"
    assert changes["src/delete_me.py"]["status"] == "D"
    assert "src/rename_me.py" not in changes, "a rename is one entry, not two"
    body = (git_project.runtime / "implementation-manifest.md").read_text("utf-8")
    assert "R src/rename_me.py -> src/renamed.py" in body
    assert "D src/delete_me.py" in body


def test_d03_a_binary_change_is_represented_without_decoding(git_project):
    at_implement(git_project)
    (git_project.root / "assets").mkdir()
    (git_project.root / "assets" / "logo.png").write_bytes(PNG)
    git_project.git("add", "assets/logo.png")
    git_project.git("commit", "-q", "-m", "logo")

    result = build(git_project)

    assert by_path(result)["assets/logo.png"]["binary"] is True
    body = (git_project.runtime / "implementation-manifest.md").read_text("utf-8")
    assert "A assets/logo.png (binary)" in body


def test_d03_engine_bookkeeping_stays_excluded(git_project):
    at_implement(git_project)
    (git_project.root / ".sdle").mkdir(exist_ok=True)
    (git_project.root / ".sdle" / "baseline.json").write_text(
        '{"kind": "baseline"}\n', encoding="utf-8")
    git_project.write_artifact(".specify/memory/notes.md")

    files = build(git_project).data["files"]

    assert not any(f.startswith((".sdle/", ".specify/", "workitems/"))
                   for f in files), files


def test_d03_a_missing_base_is_refused_not_replaced(git_project):
    drive(git_project, "GREENFIELD", stop="implement")
    assert git_project.state()["implementation_base_ref"] is None

    for command in (("manifest", "build", "--skip-tests"),
                    ("security-review", "evidence")):
        result = git_project.run(*command)
        assert result.exit_code == EXIT_REFUSED, (command, result)
        assert result.reason == "implementation_base_missing", result
        assert "implement preflight" in result.envelope["message"]


def test_d03_an_invalid_base_is_refused(git_project):
    at_implement(git_project)
    state = git_project.state()
    state["implementation_base_ref"] = "f" * 40  # no such commit
    git_project.write_state(state)

    result = git_project.run("manifest", "build", "--skip-tests")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "implementation_base_invalid", result


def test_d03_the_dirty_tree_guard_reads_the_first_status_entry_whole(
        git_project):
    """Found while reproducing D03. `git()` strips its whole output, so the
    first `git status --short` line lost its leading space and `line[3:]`
    then cut the first character of the path: an unstaged edit to a tracked
    SDLE-owned file that sorted first, ` M .specify/…`, surfaced as
    `specify/…`, escaped the ownership filter and raised a false
    `dirty_tree`. The manifest shared the parse and listed
    `orkitems/…/state.json`; D03 replaced that path with NUL-separated
    output, and the guard now reads its status the same way."""
    drive(git_project, "GREENFIELD", stop="implement")
    git_project.git("add", "-A")
    git_project.git("commit", "-q", "-m", "workflow so far")
    constitution = git_project.root / ".specify" / "memory" / "constitution.md"
    constitution.write_text(constitution.read_text("utf-8") + "\nedited\n",
                            encoding="utf-8")
    first = git_project.git("status", "--short", "-uall").stdout.splitlines()[0]
    assert first == " M .specify/memory/constitution.md", first

    result = git_project.ok("implement", "preflight")
    assert result.data["dirty"] is False, result

    # And a real user edit in first position is reported by its whole path.
    git_project.write_artifact(".aaa-user-notes.md")
    refused = git_project.run("implement", "preflight")
    assert refused.reason == "dirty_tree", refused
    assert any(entry.endswith(" .aaa-user-notes.md")
               for entry in refused.data["entries"]), refused.data["entries"]


def test_d03_rebuilding_unchanged_inputs_gives_the_same_change_set(
        git_project):
    at_implement(git_project)
    git_project.write_artifact("src/a.py")
    git_project.write_artifact("src/b.py")

    first = build(git_project).data["changes"]
    second = build(git_project).data["changes"]

    assert first == second
    assert [c["path"] for c in first] == sorted(c["path"] for c in first)
    assert len({c["path"] for c in first}) == len(first), "no duplicates"


# ==========================================================================
# F-102 — another WorkItem's records are not this WorkItem's implementation
#
# `implementation_exclusions` feeds BOTH consumers — the Gate 7 manifest and
# `security-review evidence` — so both are driven here. WorkItem records are
# versioned by design, so a second WorkItem simply being used during this one's
# implementation puts its governed records in this one's diff.
# ==========================================================================


IMPLEMENTATION = "# real implementation\n" + "value = 1\n" * 20


def second_workitem_activity(project) -> list[str]:
    """Create a second WorkItem and let it write its own governed records.

    Returns the repo-relative paths it touched, which the bound WorkItem's
    change set must not contain.
    """
    created = project.ok("workitem", "create", "--name", "Second Item")
    other = created.data["id"]
    view = project.as_workitem(other)
    view.ok("requirements", "bind", "--source", "requirements/todo-api.md")
    view.record_governance()
    view.ok("init", session="other")
    return [f"workitems/{other}/", "workitems/index.md"]


def mine(project):
    """A view pinned to the WorkItem under test.

    Creating a second WorkItem moves the developer-local active context, so
    every call after that names its WorkItem explicitly rather than resolving.
    """
    return project.as_workitem(FIXTURE_WORKITEM_ID)


def test_f102_another_workitems_records_stay_out_of_the_manifest(git_project):
    at_implement(git_project)
    foreign = second_workitem_activity(git_project)
    git_project.write_artifact("src/edit_me.py", IMPLEMENTATION)

    files = build(mine(git_project)).data["files"]

    leaked = [f for f in files if any(f.startswith(p) for p in foreign)]
    assert leaked == [], (
        "another WorkItem's governed records are in this WorkItem's Gate 7 "
        f"manifest: {leaked}")
    assert "src/edit_me.py" in files, "the real implementation is still listed"


def test_f102_another_workitems_records_stay_out_of_the_security_evidence(
        git_project):
    at_implement(git_project)
    foreign = second_workitem_activity(git_project)
    git_project.write_artifact("src/edit_me.py", IMPLEMENTATION)

    evidence = mine(git_project).ok("security-review", "evidence").data
    paths = [c["path"] for c in evidence["changes"]] + list(
        evidence.get("untracked") or [])

    leaked = [p for p in paths if any(p.startswith(f) for f in foreign)]
    assert leaked == [], (
        "another WorkItem's governed records are in this WorkItem's "
        f"security-review evidence: {leaked}")
    assert "src/edit_me.py" in paths


def test_f102_the_bound_workitems_own_implementation_is_still_listed(git_project):
    """Non-vacuity, and the guard against over-excluding: the fix must not
    silence the bound WorkItem's own changes to implementation paths."""
    at_implement(git_project)
    git_project.write_artifact("src/keep.py", IMPLEMENTATION)

    files = build(git_project).data["files"]

    assert "src/keep.py" in files, files


def test_f102_an_unregistered_directory_under_workitems_is_still_listed(
        git_project):
    """The exclusion is enumerated from the registry on purpose. A directory no
    row claims is an anomaly `validate` reports, and an anomaly that appeared
    during an implementation belongs in front of the reviewer rather than being
    filtered out by the filter's own convenience."""
    at_implement(git_project)
    stray = git_project.root / "workitems" / "not-registered"
    (stray / ".sdle").mkdir(parents=True)
    (stray / ".sdle" / "state.json").write_text("{}\n", encoding="utf-8",
                                                newline="\n")

    files = build(git_project).data["files"]

    assert "workitems/not-registered/.sdle/state.json" in files, files


def test_f102_the_registry_itself_is_excluded(git_project):
    """A judgement, not a deduction: `workitems/index.md` changes whenever any
    WorkItem is created, so leaving it in shows every concurrent reviewer a row
    that is not theirs. A hand-edited registry is the write fence's and
    `validate`'s question, not Gate 7's."""
    at_implement(git_project)
    second_workitem_activity(git_project)

    files = build(mine(git_project)).data["files"]

    assert "workitems/index.md" not in files, files


# -- review round 2: the boundary cases the first fix got wrong ---------------


def test_f102_a_sibling_of_the_registry_is_not_hidden_by_it(git_project):
    """`workitems/index.md` is an exact path, not a prefix. Matching it with
    `startswith` also hid `workitems/index.md.backup`."""
    at_implement(git_project)
    (git_project.root / "workitems" / "index.md.backup").write_text(
        "a copy someone made\n" + "x\n" * 30, encoding="utf-8", newline="\n")

    files = build(git_project).data["files"]

    assert "workitems/index.md.backup" in files, files


def test_f102_a_deregistered_workitem_does_not_become_this_ones_work(git_project):
    """The exclusion is the union of the registry now and at the pinned base.
    Reading only the current registry reproduced the defect in reverse: delete
    a WorkItem during an implementation and all of its deletions are reported
    as this WorkItem's work."""
    at_implement(git_project)
    foreign = second_workitem_activity(git_project)
    other = foreign[0].split("/")[1]
    view = mine(git_project)
    view.git("add", "-A")
    view.git("commit", "-q", "-m", "second workitem exists")
    view.ok("implement", "preflight", "--bypass")   # re-pin with B present

    shutil.rmtree(git_project.root / "workitems" / other)
    index = git_project.root / "workitems" / "index.md"
    index.write_text(
        "\n".join(line for line in index.read_text("utf-8").splitlines()
                  if other not in line) + "\n",
        encoding="utf-8", newline="\n")

    files = build(mine(git_project)).data["files"]

    leaked = [f for f in files if f.startswith(f"workitems/{other}/")]
    assert leaked == [], (
        "a deregistered WorkItem's deletions are reported as this WorkItem's "
        f"implementation: {leaked}")


def test_f102_a_malformed_registry_id_cannot_hide_a_tree_from_the_diff(
        git_project):
    """A structurally valid row whose cell is not an id owns no directory.

    The Python filter compares prefixes literally, so a glob in a cell never
    bit there — it bit in the git pathspec, where `:(exclude)workitems/*`
    removed every WorkItem tree from the reviewer's diff, including files the
    change list still listed. Asserted on the diff for that reason.
    """
    at_implement(git_project)
    index = git_project.root / "workitems" / "index.md"
    row = "| 2026-09-21 | * | feature | Bad | - |\n"
    index.write_text(index.read_text("utf-8").rstrip("\n") + "\n" + row,
                     encoding="utf-8", newline="\n")
    stray = git_project.root / "workitems" / "kept-visible"
    stray.mkdir()
    (stray / "note.md").write_text("visible to the reviewer\n" + "x\n" * 30,
                                   encoding="utf-8", newline="\n")
    git_project.git("add", "-A")
    git_project.git("commit", "-q", "-m", "a row that is not an id")

    evidence = git_project.ok("security-review", "evidence").data

    assert "workitems/kept-visible/note.md" in evidence["diff"], evidence["diff"][:400]
    assert "workitems/kept-visible/note.md" in [
        c["path"] for c in evidence["changes"]]


@pytest.mark.parametrize("destination, expect_status, expect_path", [
    ("src/moved.py", "R", "src/moved.py"),
    (None, "D", "src/rename_me.py"),          # into another WorkItem's tree
])
def test_f102_a_rename_is_projected_by_both_of_its_sides(
        git_project, destination, expect_status, expect_path):
    """Filtering a rename on its destination alone erased the fact that the
    file left `src/`. Each side is projected on its own."""
    at_implement(git_project)
    foreign = second_workitem_activity(git_project)
    other = foreign[0].split("/")[1]
    target = destination or f"workitems/{other}/adopted.py"
    view = mine(git_project)
    (git_project.root / target).parent.mkdir(parents=True, exist_ok=True)
    view.git("mv", "src/rename_me.py", target)

    changes = {c["path"]: c for c in build(view).data["changes"]}

    assert expect_path in changes, changes
    assert changes[expect_path]["status"] == expect_status, changes[expect_path]
    if expect_status == "D":
        assert target not in changes, "the destination is out of scope"


def test_f102_a_tracked_foreign_record_is_absent_from_stat_and_diff(git_project):
    """The security consumer renders a diff as well as selecting changes, and
    the contract is that the diff covers exactly the selection. The foreign
    records are committed here so a pathspec error cannot hide behind them
    being untracked."""
    at_implement(git_project)
    foreign = second_workitem_activity(git_project)
    other = foreign[0].split("/")[1]
    view = mine(git_project)
    view.git("add", "-A")
    view.git("commit", "-q", "-m", "second workitem records")
    git_project.write_artifact("src/edit_me.py", IMPLEMENTATION)

    evidence = view.ok("security-review", "evidence").data

    assert other not in evidence["stat"], evidence["stat"]
    assert other not in evidence["diff"], evidence["diff"][:400]
    assert "src/edit_me.py" in evidence["diff"]


def test_f102_the_bound_workitems_own_non_runtime_files_stay_visible(git_project):
    """Non-vacuity for the narrow exclusion: a blanket `workitems/` prefix
    would pass every other test here and silently hide this."""
    at_implement(git_project)
    own = git_project.runtime.parent / "notes.md"
    own.write_text("my own note\n" + "x\n" * 30, encoding="utf-8", newline="\n")

    files = build(git_project).data["files"]

    relative = own.relative_to(git_project.root).as_posix()
    assert relative in files, files


def test_f103_application_code_is_not_attributed_to_a_workitem(git_project):
    """The documented limitation, pinned as behaviour rather than prose.

    `implementation_changes` is a diff of the working tree against a pinned
    commit, so it cannot say which WorkItem wrote a line of application code.
    Another WorkItem's *records* are excluded (F-102); its **code** is not, and
    cannot be. `docs/workitems/README.md` and the getting-started guide
    therefore require a branch or worktree per WorkItem while it implements.

    If this ever starts passing with the foreign edit absent, attribution has
    been implemented and both documents are then wrong — which is the point of
    asserting it.
    """
    at_implement(git_project)
    second_workitem_activity(git_project)
    # A change to ordinary source, as a second WorkItem in this checkout would
    # make it. Nothing marks it as theirs.
    git_project.write_artifact("src/edit_me.py", IMPLEMENTATION)

    files = build(mine(git_project)).data["files"]

    assert "src/edit_me.py" in files, (
        "application code is attributed by the diff alone, so a foreign edit "
        "in the same checkout is indistinguishable from this WorkItem's own")
