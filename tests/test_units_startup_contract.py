"""The documented startup sequence, driven end to end with no fixture shortcuts.

Why this module exists. `tests/conftest.py`'s `project` fixture binds the
requirements during setup, because that is what a ready-to-start WorkItem looks
like and six modules would otherwise repeat the step. The cost is a blind spot:
every other test begins from an *already bound* WorkItem, so a documented
sequence that omits `requirements bind` still passes, and a documented position
nothing can reach is never contradicted.

That blind spot is not hypothetical. It let three classes of defect survive a
full review round of the shipped documentation:

* four tutorials and six dry runs showed `create -> preflight -> assess` with no
  binding step, a sequence that refuses `requirements_unbound` if typed;
* seven documents showed `Phase 1/N - Requirements Check [IN PROGRESS]`, a state
  no run persists, because `init` completes `requirements_check` within itself;
* every tutorial's `init` payload showed bare filenames where the engine emits
  repository-relative paths.

So these tests start from `bare_project` and type the sequence out. They assert
what a *reader following the documentation* would observe, not what the engine
happens to do internally — that is the whole point, and it is why they belong
beside the engine rather than in the documentation linter.
"""
from __future__ import annotations

import json

from conftest import (FIXTURE_WORKITEM_ID, FIXTURE_WORKITEM_NAME,
                      Project, sdle)

# The engine's contract, restated here the way every other test module does it.
EXIT_OK, EXIT_REFUSED, EXIT_INTEGRITY = 0, 1, 3


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _registered(bare_project: Project) -> Project:
    """A registered WorkItem and nothing else — deliberately unbound."""
    bare_project.ok("workitem", "create", "--name", FIXTURE_WORKITEM_NAME)
    bare_project.workitem = FIXTURE_WORKITEM_ID
    return bare_project


def _bound(bare_project: Project) -> Project:
    project = _registered(bare_project)
    project.ok("requirements", "bind", "--source", "requirements/todo-api.md")
    return project


# --------------------------------------------------------------------------
# the sequence is ordered, not decorative
# --------------------------------------------------------------------------


def test_preflight_before_binding_refuses(bare_project):
    """`create` then `preflight` is not a runnable sequence.

    Four tutorials and six dry runs published exactly this order.
    """
    project = _registered(bare_project)
    result = project.run("preflight")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "requirements_unbound"


def test_governance_assess_before_binding_refuses(bare_project):
    """`init` is not even reachable unbound: the assessment refuses first.

    Written the other way round at first, which the engine disproved — the
    fixture could not record governance at all. The real contract is stronger
    than the one this module originally asserted, so it is pinned as observed.
    """
    project = _registered(bare_project)
    # A *well-formed* proposal, so the refusal is about the binding and not
    # about the document. An empty `{}` refuses `governance_input_malformed`
    # first — input validation precedes the binding check, which is itself
    # worth knowing and is why this test builds a real document.
    document = project.root / "governance-input.json"
    document.write_text(json.dumps({
        "governanceInputVersion": "1",
        "quality": {name: {"result": "PASS", "finding": None}
                    for name in sdle.GOVERNANCE_POLICY_BUILTIN["quality_checks"]},
        "classification": {"type": "enhancement", "flow": "GREENFIELD"},
        "risk": {"signals": [], "proposedLevel": "LOW", "uncertainty": "LOW"},
    }), encoding="utf-8")
    result = project.run("governance", "assess", "--input", "governance-input.json")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "requirements_unbound"


def test_init_before_binding_refuses(bare_project):
    """And `init` refuses on its own account, not only by inheriting the above."""
    project = _registered(bare_project)
    result = project.run("init")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "requirements_unbound"


def test_the_documented_sequence_runs(bare_project):
    """create -> bind -> show -> preflight -> scan -> assess -> init.

    The order `docs/GETTING-STARTED.md` publishes, typed out. If a step is
    reordered or removed in the engine, this fails rather than the reader
    finding out.
    """
    project = _registered(bare_project)
    project.ok("requirements", "bind", "--source", "requirements/todo-api.md")
    project.ok("requirements", "show")
    project.ok("preflight")
    project.ok("scan", "--path", "requirements/todo-api.md")
    project.record_governance()
    project.ok("init")


# --------------------------------------------------------------------------
# what `init` actually reports
# --------------------------------------------------------------------------


def test_init_never_persists_requirements_check(bare_project):
    """`Phase 1/N - Requirements Check` is unreachable, from both sides.

    Before `init` there is no state for a header to read; `init` completes
    `requirements_check` within itself and saves the flow's first *generation*
    phase. Seven shipped documents showed the unreachable position.
    """
    project = _bound(bare_project)
    project.record_governance()
    result = project.ok("init")

    assert result.data["current_phase"] != "requirements_check"
    assert result.data["current_phase"] == "constitution_draft"
    assert result.data["progress"].startswith("2/")
    assert project.state()["current_phase"] == "constitution_draft"


def test_init_reports_repository_relative_sources(bare_project):
    """Not bare filenames. Every tutorial published `link-shortener.md`."""
    project = _bound(bare_project)
    project.record_governance()
    result = project.ok("init")

    assert result.data["requirements"] == ["requirements/todo-api.md"]
    for entry in result.data["requirements"]:
        assert "/" in entry, f"{entry!r} is a bare filename, not a bound path"


def test_no_state_exists_before_init(bare_project):
    """So no status header can be rendered during bootstrap."""
    project = _bound(bare_project)
    assert not project.state_file.is_file()
    project.record_governance()
    assert not project.state_file.is_file()


# --------------------------------------------------------------------------
# the flagged false positive, at bootstrap and after `init`
# --------------------------------------------------------------------------


FLAGGED_LINE = "The operator can set status to Shipped once the carrier confirms."


def _flag(project: Project) -> None:
    (project.root / "requirements" / "todo-api.md").write_text(
        f"# Todo List REST API\n\n{FLAGGED_LINE}\n" + "detail\n" * 30,
        encoding="utf-8", newline="\n")


def test_ordinary_requirements_prose_can_trip_the_scan(bare_project):
    """The patterns are broad by design, and `set status` is ordinary English.

    Pinned so that a change to INJECTION_PATTERNS which quietly stops matching
    business prose is a decision somebody made, not a drift nobody noticed.
    """
    project = _bound(bare_project)
    _flag(project)
    result = project.run("scan", "--path", "requirements/todo-api.md")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "content_flagged"
    assert result.data["matches"][0]["pattern"] == "set_status"


def test_bootstrap_scan_says_acknowledgement_is_not_available_yet(bare_project):
    """The message must not offer a route that exits 3.

    `docs/dry-runs/05` taught `accept content` at exactly this point.
    """
    project = _bound(bare_project)
    _flag(project)
    result = project.run("scan", "--path", "requirements/todo-api.md")

    message = result.envelope["message"]
    assert result.data["acknowledgeable"] is False
    assert "no state exists until `init` has run" in message
    assert "re-scan" in message


def test_accept_content_before_init_does_not_work(bare_project):
    """Pins the behaviour the documentation now describes.

    If bootstrap acknowledgement is ever implemented, this test fails and the
    documentation that depends on it is found in the same commit.
    """
    project = _bound(bare_project)
    _flag(project)
    project.run("scan", "--path", "requirements/todo-api.md")

    result = project.run("accept-content")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "state_unreadable"


def test_scanning_again_after_init_makes_acknowledgement_available(bare_project):
    """The documented way through a bootstrap false positive.

    A reader must not have to reword a legitimate requirement: scan first to see
    the warning, `init`, scan again, then acknowledge.
    """
    project = _bound(bare_project)
    _flag(project)

    first = project.run("scan", "--path", "requirements/todo-api.md")
    assert first.data["acknowledgeable"] is False

    project.record_governance()
    project.ok("init")

    second = project.run("scan", "--path", "requirements/todo-api.md")
    assert second.exit_code == EXIT_REFUSED
    assert second.data["acknowledgeable"] is True
    assert project.state()["pending_confirm_action"] == (
        "accept_content:requirements/todo-api.md")

    accepted = project.ok("accept-content")
    assert accepted.exit_code == EXIT_OK
    assert project.state()["pending_confirm_action"] is None
    assert "User accepted flagged content" in project.audit_file.read_text("utf-8")


def test_a_clean_document_reports_acknowledgeable_too(bare_project):
    """The field is present whether or not anything fired, so callers can branch
    on the payload without a KeyError."""
    project = _bound(bare_project)
    result = project.ok("scan", "--path", "requirements/todo-api.md")
    assert result.data["flagged"] is False
    assert "acknowledgeable" in result.data


# --------------------------------------------------------------------------
# the registered-without-state start
# --------------------------------------------------------------------------


def test_a_reset_workitem_is_registered_without_state(bare_project):
    """`start workflow`'s second situation, which had no documented branch.

    `reset` removes state, audit and lock and leaves the identity registered, so
    a later start must not ask for a name again.
    """
    project = _bound(bare_project)
    project.record_governance()
    project.ok("init")
    assert project.state_file.is_file()

    project.ok("reset")
    project.ok("reset", "--confirm")

    assert not project.state_file.is_file()
    assert (project.root / "workitems" / FIXTURE_WORKITEM_ID
            / "workitem.json").is_file()

    # The identity is still taken: asking for the name again refuses.
    result = project.run("workitem", "create", "--name", FIXTURE_WORKITEM_NAME)
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "workitem_exists"


def test_requirements_show_reports_unbound_without_refusing(bare_project):
    """`sdle-start` step 2b branches on `data.bound`, not on an exit code."""
    project = _registered(bare_project)
    result = project.ok("requirements", "show")
    assert result.exit_code == EXIT_OK
    assert result.data["bound"] is False
    assert result.data["sources"] == []
