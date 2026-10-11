"""Tree-bound implementation evidence (ADR-017, R2): AS-14, AS-15, AS-16.

A passing test run is evidence about the tree it ran against. The gate
recomputes that tree and refuses evidence for any other.
"""
from __future__ import annotations

import json
import subprocess
import sys

from conftest import PASSING_TEST_COMMAND, _command_line, sdle
from test_units_artifact_review import review_for_gate
from test_units_implementation_evidence import (
    EXIT_OK, EXIT_REFUSED, approve, at_implement, evidence_of, to_gate)

WRITES_A_FILE = _command_line([
    sys.executable, "-c",
    "open('side-effect.txt', 'w').write('x'); raise SystemExit(0)"])


def digest_of(project) -> dict:
    paths = sdle.resolve_paths(str(project.root), str(project.skill_root))
    paths = sdle.dataclass_replace(paths, workitem=project.workitem)
    state = project.state() if project.state_file.is_file() else {}
    return sdle.tree_digest(paths, state)


def ready(project, **files):
    at_implement(project)
    for name, body in files.items():
        (project.root / name).write_text(body, encoding="utf-8")


# ---- AS-14: an edit after a passing run -------------------------------------


def test_as14_a_file_edited_after_a_passing_run_makes_the_evidence_stale(
        git_project):
    ready(git_project, **{"app.py": "print('v1')\n"})
    to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    (git_project.root / "app.py").write_text(
        "print('v2, edited after the passing run')\n", encoding="utf-8")
    result = approve(git_project)
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "test_evidence_stale"
    assert result.data["mismatch"] == "treeDigest"


def test_an_unchanged_implementation_goes_through_manifest_review_and_approval(
        git_project):
    """SDLE's own writes (state, audit, manifest, evidence, review ledger)
    must never make a good run look stale."""
    ready(git_project, **{"app.py": "print('v1')\n"})
    built = to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    assert evidence_of(git_project, built)["evidenceStatus"] == "valid"
    assert approve(git_project).exit_code == EXIT_OK


def test_a_new_untracked_file_after_the_run_makes_the_evidence_stale(
        git_project):
    ready(git_project, **{"app.py": "print('v1')\n"})
    to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    (git_project.root / "added-later.py").write_text("x = 1\n",
                                                     encoding="utf-8")
    assert approve(git_project).reason == "test_evidence_stale"


def test_a_deleted_file_after_the_run_makes_the_evidence_stale(git_project):
    ready(git_project, **{"app.py": "print('v1')\n", "gone.py": "y = 2\n"})
    to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    (git_project.root / "gone.py").unlink()
    assert approve(git_project).reason == "test_evidence_stale"


# ---- AS-15: what counts ------------------------------------------------------


def test_as15_uncommitted_and_untracked_changes_move_the_digest_and_ignored_ones_do_not(
        git_project):
    ready(git_project, **{"app.py": "print('v1')\n"})
    (git_project.root / ".gitignore").write_text(
        ".sdle/\nignored.log\n*.pyc\n", encoding="utf-8")
    base = digest_of(git_project)["digest"]

    (git_project.root / "ignored.log").write_text("noise\n", encoding="utf-8")
    assert digest_of(git_project)["digest"] == base, "ignored files do not count"

    (git_project.root / "app.py").write_text("print('v2')\n", encoding="utf-8")
    modified = digest_of(git_project)["digest"]
    assert modified != base, "an uncommitted modification counts"

    (git_project.root / "brand-new.py").write_text("z = 3\n", encoding="utf-8")
    assert digest_of(git_project)["digest"] not in (base, modified), (
        "an untracked file that is not ignored counts")


def test_engine_bookkeeping_and_other_workitems_do_not_move_the_digest(
        git_project):
    ready(git_project, **{"app.py": "print('v1')\n"})
    base = digest_of(git_project)["digest"]
    git_project.ok("workitem", "create", "--name", "someone-else")
    other = git_project.root / "workitems" / "someone-else" / ".sdle"
    other.mkdir(parents=True, exist_ok=True)
    (other / "state.json").write_text("{}", encoding="utf-8")
    (git_project.runtime / "evidence" / "noise.json").parent.mkdir(
        parents=True, exist_ok=True)
    (git_project.runtime / "evidence" / "noise.json").write_text(
        "{}", encoding="utf-8")
    assert digest_of(git_project)["digest"] == base


def test_code_under_the_bound_workitem_directory_does_count(git_project):
    ready(git_project)
    base = digest_of(git_project)["digest"]
    mine = git_project.root / "workitems" / git_project.workitem / "service"
    mine.mkdir(parents=True, exist_ok=True)
    (mine / "handler.py").write_text("def f(): pass\n", encoding="utf-8")
    assert digest_of(git_project)["digest"] != base


def test_a_config_or_policy_edit_after_the_run_counts(git_project):
    ready(git_project)
    git_project.ok("config", "init")
    base = digest_of(git_project)["digest"]
    config = git_project.root / ".sdle" / "config.json"
    config.write_text(config.read_text(encoding="utf-8") + "\n",
                      encoding="utf-8")
    assert digest_of(git_project)["digest"] != base


def test_the_digest_does_not_depend_on_line_endings_git_would_convert(
        git_project):
    """Files are hashed by their bytes in the working tree, so the answer is
    the same however git is configured to convert them on the way in."""
    ready(git_project, **{"app.py": "a\nb\n"})
    first = digest_of(git_project)["digest"]
    subprocess.run(["git", "config", "core.autocrlf", "true"],
                   cwd=git_project.root, check=True)
    assert digest_of(git_project)["digest"] == first


# ---- AS-16: the tree changes during the run -----------------------------------------


def test_as16_a_tree_that_changes_during_the_run_makes_the_evidence_invalid(
        git_project):
    ready(git_project, **{"app.py": "print('v1')\n"})
    built = git_project.ok("manifest", "build", "--test-command",
                           WRITES_A_FILE)
    evidence = evidence_of(git_project, built)
    assert evidence["evidenceStatus"] == "invalid_changed_during_run"
    assert evidence["changedDuringRun"] == ["side-effect.txt"]
    assert built.data["evidence_status"] == "invalid_changed_during_run"
    git_project.ok("advance", "--to", "gate_implement")
    review_for_gate(git_project, "gate_implement")
    result = approve(git_project)
    assert result.reason == "test_evidence_stale"
    assert result.data["mismatch"] == "changed_during_run"


# ---- the evidence records what else it is about ---------------------------------------


def test_the_evidence_binds_the_command_the_tree_and_the_inputs(git_project):
    ready(git_project, **{"app.py": "print('v1')\n"})
    built = git_project.ok("manifest", "build", "--test-command",
                           PASSING_TEST_COMMAND)
    evidence = evidence_of(git_project, built)
    assert evidence["treeDigest"]["method"] == "git-listed-files"
    assert evidence["treeDigest"]["digest"] == evidence["treeDigest"]["before"]
    bindings = evidence["bindings"]
    assert bindings["testCommand"] == PASSING_TEST_COMMAND
    assert bindings["requirementsDigest"]
    assert bindings["packageDigest"] is None, "no package, nothing to bind"
    history = sorted((git_project.runtime / "evidence").glob("implementation-*"))
    git_project.ok("manifest", "build", "--test-command", PASSING_TEST_COMMAND)
    assert len(sorted((git_project.runtime / "evidence").glob(
        "implementation-*"))) == len(history) + 1, (
        "historical evidence is never deleted")


# ---- compatibility and shape -------------------------------------------------------------


def test_evidence_built_before_the_tree_binding_existed_still_approves(
        git_project):
    ready(git_project, **{"app.py": "print('v1')\n"})
    built = to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    target = git_project.root / built.data["evidence"]
    document = json.loads(target.read_text(encoding="utf-8"))
    for key in ("treeDigest", "evidenceStatus", "changedDuringRun",
                "bindings"):
        document.pop(key)
    target.write_text(json.dumps(document), encoding="utf-8")
    (git_project.root / "app.py").write_text("print('later')\n",
                                             encoding="utf-8")
    assert approve(git_project).exit_code == EXIT_OK


def test_a_malformed_tree_binding_is_malformed_evidence_not_a_pass(
        git_project):
    ready(git_project)
    built = to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    target = git_project.root / built.data["evidence"]
    document = json.loads(target.read_text(encoding="utf-8"))
    document["treeDigest"] = {"digest": 5}
    target.write_text(json.dumps(document), encoding="utf-8")
    assert approve(git_project).reason == "test_evidence_malformed"


def test_without_git_the_working_tree_is_walked_and_the_method_says_so(
        project):
    """No git repository: the digest is over the files themselves."""
    (project.root / "app.py").write_text("print('v1')\n", encoding="utf-8")
    first = digest_of(project)
    assert first["method"] == "walked-files"
    (project.root / "app.py").write_text("print('v2')\n", encoding="utf-8")
    assert digest_of(project)["digest"] != first["digest"]


def test_an_edit_inside_a_nested_repository_moves_the_digest(git_project):
    """A submodule is one entry to git and holds implementation too: its
    checkout is walked, so a change inside it cannot hide."""
    ready(git_project)
    sub = git_project.root / "vendor-lib"
    sub.mkdir()
    for args in (["init", "-q"], ["config", "user.email", "t@example.com"],
                 ["config", "user.name", "t"]):
        subprocess.run(["git", *args], cwd=sub, check=True)
    (sub / "lib.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "lib.py"], cwd=sub, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "lib"], cwd=sub, check=True)
    subprocess.run(["git", "add", "vendor-lib"], cwd=git_project.root,
                   capture_output=True)
    base = digest_of(git_project)
    assert any(name.startswith("vendor-lib/") for name in base["entries"])
    (sub / "lib.py").write_text("x = 2\n", encoding="utf-8")
    assert digest_of(git_project)["digest"] != base["digest"]


# ---- UI browser checks (ui-quality Phase B): existing behaviour, pinned -----
#
# A project's browser harness is just a `--test-command` that writes a JUnit
# report and some screenshots. Nothing in the engine is UI-specific; these
# three tests pin the properties the harness contract in
# `guidelines/ui-design.md` relies on, with a Python stand-in for the harness.

STAND_IN_SCRIPT = (
    "import pathlib\n"
    "pathlib.Path('ui-out').mkdir(exist_ok=True)\n"
    "pathlib.Path('test-results').mkdir(exist_ok=True)\n"
    "pathlib.Path('test-results/shot.png').write_bytes(b'fake png')\n"
    "pathlib.Path('ui-out/junit.xml').write_text('<testsuite tests=\"1\"><testcase name=\"UI-HOME-1 desktop loaded\"/></testsuite>', encoding='utf-8')\n")
STAND_IN_WRITES_REPORT_AND_SCREENSHOT = _command_line(
    [sys.executable, "ui_stand_in.py"])


def test_b1_a_harness_that_writes_into_ignored_paths_gives_valid_evidence(
        git_project):
    """The harness contract: reports and screenshots go to ignored paths."""
    ready(git_project, **{"app.py": "print('v1')\n",
                          "ui_stand_in.py": STAND_IN_SCRIPT})
    (git_project.root / ".gitignore").write_text(
        ".sdle/\nui-out/\ntest-results/\n", encoding="utf-8")
    built = to_gate(git_project, "--test-command",
                    STAND_IN_WRITES_REPORT_AND_SCREENSHOT,
                    "--junit", "ui-out/junit.xml")
    evidence = evidence_of(git_project, built)
    assert evidence["evidenceStatus"] == "valid"
    assert (git_project.root / "test-results" / "shot.png").is_file()
    assert approve(git_project).exit_code == EXIT_OK


def test_b2_an_environment_failure_exit_code_is_recorded_and_refused(
        git_project):
    """Exit 78 is a convention for the orchestrator, not an engine class:
    the engine records FAILED with the code, and the gate refuses it."""
    ready(git_project, **{"app.py": "print('v1')\n"})
    built = to_gate(git_project, "--test-command", _command_line(
        [sys.executable, "-c", "raise SystemExit(78)"]))
    assert built.data["tests"]["status"] == "FAILED"
    assert built.data["tests"]["exit_code"] == 78
    result = approve(git_project)
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "tests_not_passed"
    assert result.data["exit_code"] == 78


def test_b3_screenshots_in_an_unignored_folder_invalidate_the_evidence(
        git_project):
    """Why the contract says to ignore test output: a report left in the
    working tree is a change to the tree the evidence was taken from."""
    ready(git_project, **{"app.py": "print('v1')\n",
                          "ui_stand_in.py": STAND_IN_SCRIPT})
    built = to_gate(git_project, "--test-command",
                    STAND_IN_WRITES_REPORT_AND_SCREENSHOT)
    assert evidence_of(git_project, built)["evidenceStatus"] == (
        "invalid_changed_during_run")
    assert approve(git_project).exit_code == EXIT_REFUSED
