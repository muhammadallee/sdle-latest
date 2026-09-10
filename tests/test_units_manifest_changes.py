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

import pytest

from conftest import PASSING_TEST_COMMAND
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
