"""D02 (SDLE-DEFECT-STABILIZATION-01) — Gate 7 enforces the verification
outcome, not the presence of a heading.

**The contract as it existed before this iteration** (recorded here because
the plan requires it to be confirmed from the checkout before coding):

* producer — `manifest build` ran a detected runner (npm, pytest, cargo,
  maven, gradle) unless `--skip-tests` was passed, and wrote one of six
  statuses into the manifest's prose: `passed`, `FAILED`, `no runner
  detected`, `runner not installed`, `timed out after Ns`, `skipped by
  caller`. Nothing structured was persisted.
* reader — Gate 7's precondition checked that the three
  `REQUIRED_MANIFEST_SECTIONS` headings were present. It never read a status.
* exception path — **none exists**. There is no waiver, no accepted-risk
  record and no policy switch that makes a missing or failed test run
  acceptable. `gate omit` cannot reach Gate 7: the implementation gate is part
  of every flow's mandatory floor.

So a `--skip-tests` manifest, a FAILED run, and a hand-written manifest that
merely contained the headings all approved, and a PASS artifact review of the
manifest's *presentation* was the only other thing checked.

**The contract after it:** `manifest build` writes a structured evidence file
beside the manifest and names it from the manifest. Gate 7 reads that file,
binds it to the exact manifest bytes, the pinned implementation base and the
bound WorkItem, and refuses anything but a runner that ran and exited 0. There
is still no exception path, by decision: `--test-command` lets a project whose
runner is not auto-detected produce *real* evidence; it waives nothing.
"""

from __future__ import annotations

import json
import sys

import pytest

from conftest import PASSING_TEST_COMMAND, FAILING_TEST_COMMAND, sdle
from test_units_artifact_review import frozen, review_for_gate
from test_units_flow_model import drive

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3


def at_implement(project) -> None:
    drive(project, "GREENFIELD", stop="implement")
    project.ok("implement", "preflight", "--bypass")


def to_gate(project, *build_args) -> "sdle":
    built = project.ok("manifest", "build", *build_args)
    project.ok("advance", "--to", "gate_implement")
    review_for_gate(project, "gate_implement")  # a PASS review, every time
    return built


def approve(project):
    before = frozen(project)
    result = project.run("gate", "approve", "--gate", "gate_implement")
    if result.exit_code != EXIT_OK:
        assert frozen(project) == before, "a refusal must not move anything"
    return result


def evidence_of(project, built) -> dict:
    return json.loads((project.root / built.data["evidence"]).read_text("utf-8"))


# -- 1, 2: an unsuccessful run, even under a PASS review ---------------------


def test_d02_1_a_failed_command_with_a_pass_review_is_refused(git_project):
    at_implement(git_project)
    to_gate(git_project, "--test-command", FAILING_TEST_COMMAND)

    result = approve(git_project)

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "tests_not_passed", result
    assert result.data["status"] == "FAILED"
    assert git_project.state()["approvals"]["gate_implement"] is None


def test_d02_2_a_real_failing_suite_is_refused(git_project):
    at_implement(git_project)
    tests = git_project.root / "tests"
    tests.mkdir()
    (tests / "test_generated.py").write_text(
        "def test_it():\n    assert 1 == 2\n", encoding="utf-8")
    built = to_gate(git_project, "--test-timeout", "120")
    assert built.data["tests"]["runner"] == "pytest"

    result = approve(git_project)

    assert result.reason == "tests_not_passed", result
    assert result.data["exit_code"] not in (0, None)


# -- 3: missing, empty, headings-only ----------------------------------------


def test_d02_3_a_headings_only_manifest_is_refused(git_project):
    """The shape the old check accepted: every heading, no evidence."""
    at_implement(git_project)
    manifest = git_project.runtime / "implementation-manifest.md"
    manifest.write_text(
        "# Implementation Manifest\n\n"
        + "".join(f"{section}\nlooks fine\n\n"
                  for section in sdle.REQUIRED_MANIFEST_SECTIONS)
        + "padding " * 20 + "\n", encoding="utf-8")
    git_project.ok("advance", "--to", "gate_implement")
    review_for_gate(git_project, "gate_implement")

    result = approve(git_project)

    assert result.reason == "test_evidence_missing", result
    assert "manifest build" in result.envelope["message"]


def test_d02_3_a_deleted_evidence_file_is_refused(git_project):
    at_implement(git_project)
    built = to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    (git_project.root / built.data["evidence"]).unlink()

    assert approve(git_project).reason == "test_evidence_missing"


def test_d02_3_an_empty_evidence_file_is_refused(git_project):
    at_implement(git_project)
    built = to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    (git_project.root / built.data["evidence"]).write_text("", encoding="utf-8")

    assert approve(git_project).reason == "test_evidence_malformed"


# -- 4: malformed or contradictory -------------------------------------------


@pytest.mark.parametrize("mutate", [
    pytest.param(lambda d: d.pop("tests"), id="no-tests-block"),
    pytest.param(lambda d: d["tests"].update(status="passed", exit_code=1),
                 id="passed-with-nonzero-exit"),
    pytest.param(lambda d: d["tests"].update(exit_code="0"),
                 id="exit-code-not-an-integer"),
    pytest.param(lambda d: d.update(kind="governance"), id="wrong-kind"),
])
def test_d02_4_malformed_or_contradictory_evidence_is_refused(
        git_project, mutate):
    at_implement(git_project)
    built = to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    path = git_project.root / built.data["evidence"]
    document = json.loads(path.read_text("utf-8"))
    mutate(document)
    path.write_text(json.dumps(document), encoding="utf-8")

    assert approve(git_project).reason == "test_evidence_malformed"


# -- 5: required execution skipped without authorisation ----------------------


@pytest.mark.parametrize("build_args, status", [
    (("--skip-tests",), "skipped by caller"),
    ((), "no runner detected"),
    (("--test-command", "sdle-no-such-runner-xyz"), "runner not installed"),
])
def test_d02_5_a_suite_that_never_ran_is_refused(git_project, build_args,
                                                 status):
    """There is no authorised exception to find, so each is refused, and the
    refusal says how to produce real evidence rather than how to waive it."""
    at_implement(git_project)
    to_gate(git_project, *build_args)

    result = approve(git_project)

    assert result.reason == "tests_not_passed", result
    assert result.data["status"] == status
    assert "--test-command" in result.envelope["message"]


def test_d02_5_a_timed_out_suite_is_refused(git_project):
    at_implement(git_project)
    slow = f'"{sys.executable}" -c "import time; time.sleep(30)"'
    to_gate(git_project, "--test-command", slow, "--test-timeout", "1")

    result = approve(git_project)

    assert result.reason == "tests_not_passed", result
    assert result.data["status"].startswith("timed out")


# -- 6: evidence that does not belong to this manifest ------------------------


def test_d02_6_an_edited_manifest_no_longer_matches_its_evidence(git_project):
    """The attack the reviewer-only check invited: rewrite FAILED to passed
    and re-review. The evidence is bound to the exact manifest bytes."""
    at_implement(git_project)
    to_gate(git_project, "--test-command", FAILING_TEST_COMMAND)
    manifest = git_project.runtime / "implementation-manifest.md"
    manifest.write_text(
        manifest.read_text("utf-8").replace("FAILED", "passed"),
        encoding="utf-8")
    review_for_gate(git_project, "gate_implement")  # a fresh PASS review

    result = approve(git_project)

    assert result.reason == "test_evidence_stale", result
    assert result.data["mismatch"] == "manifestSha256"


def test_d02_6_evidence_from_before_a_new_preflight_is_stale(git_project):
    at_implement(git_project)
    to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    # Re-pinning the base after the evidence was produced: the evidence now
    # describes a different implementation range than the one pinned.
    git_project.write_artifact("src/extra.py")
    git_project.git("add", "-A")
    git_project.git("commit", "-q", "-m", "later work")
    git_project.ok("implement", "preflight", "--bypass")

    result = approve(git_project)

    assert result.reason == "test_evidence_stale", result
    assert result.data["mismatch"] == "baseRef"


# -- 7: an applicable authorised exception ------------------------------------


def test_d02_7_there_is_no_exception_path_to_apply():
    """The plan's case 7 is conditional on an exception contract existing.
    None does, and this pins that absence so one cannot arrive silently: the
    manifest builder exposes no waiver option, and the only non-runner option
    is `--skip-tests`, which case 5 shows is refused."""
    parser = sdle.build_parser()
    manifest = next(a for a in parser._subparsers._group_actions
                    if a.dest == "command").choices["manifest"]
    build = next(a for a in manifest._subparsers._group_actions).choices["build"]
    options = {o for a in build._actions for o in a.option_strings}
    assert options == {"-h", "--help", "--summary", "--skip-tests",
                       "--test-timeout", "--test-command"}, options


# -- 8: complete passing results ----------------------------------------------


def test_d02_8_a_passing_test_command_approves(git_project):
    at_implement(git_project)
    built = to_gate(git_project, "--test-command", PASSING_TEST_COMMAND)
    evidence = evidence_of(git_project, built)

    assert evidence["kind"] == "implementation"
    assert evidence["tests"]["status"] == "passed"
    assert evidence["tests"]["exit_code"] == 0
    assert evidence["workitem"] == git_project.workitem
    assert evidence["baseRef"] == git_project.state()["implementation_base_ref"]

    result = git_project.ok("gate", "approve", "--gate", "gate_implement")
    assert result.data["next_phase"] == "security_review"


def test_d02_8_a_real_passing_pytest_suite_approves(git_project):
    at_implement(git_project)
    tests = git_project.root / "tests"
    tests.mkdir()
    (tests / "test_generated.py").write_text(
        "def test_it():\n    assert 1 == 1\n", encoding="utf-8")
    built = to_gate(git_project, "--test-timeout", "120")
    assert built.data["tests"]["runner"] == "pytest"
    assert built.data["tests"]["status"] == "passed"

    git_project.ok("gate", "approve", "--gate", "gate_implement")
