"""The documented startup sequence, driven end to end with no fixture shortcuts.

Why this module exists. `tests/conftest.py`'s `project` fixture binds the
requirements during setup, because that is what a ready-to-start WorkItem looks
like and six modules would otherwise repeat the step. `bare_project` (unbound)
is used elsewhere too — fourteen other modules reach for it, for their own
narrower purposes (resolution, hooks, workitem creation) — but none of them
types out the *documented startup sequence* end to end from an unbound
identity: bind, show, preflight, scan, assess, init, in the order the guide
publishes. That was the actual blind spot: a documented sequence that omits
`requirements bind` still passed every existing test, and a documented
position nothing can reach was never contradicted, because nothing drove the
whole sequence and checked it against what a reader would observe.

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
from test_units_artifact_review import review_for_gate

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


def test_bootstrap_scan_offers_an_explicit_path_acknowledgement(bare_project):
    """DEF-RR-001. The message must not claim nothing can be recorded — it
    can, explicitly, with `--path`. `docs/dry-runs/05` Path B depends on this
    wording."""
    project = _bound(bare_project)
    _flag(project)
    result = project.run("scan", "--path", "requirements/todo-api.md")

    message = result.envelope["message"]
    assert result.data["acknowledgeable"] is False
    assert "nothing is automatically remembered" in message
    assert "accept-content --path requirements/todo-api.md" in message
    assert "re-scan" in message


def test_accept_content_before_init_does_not_work(bare_project):
    """The *bare* form still needs state — unchanged, and still the form
    every existing post-init test and document pins."""
    project = _bound(bare_project)
    _flag(project)
    project.run("scan", "--path", "requirements/todo-api.md")

    result = project.run("accept-content")
    assert result.exit_code == EXIT_INTEGRITY
    assert result.reason == "state_unreadable"


def test_accept_content_with_path_works_before_init(bare_project):
    """DEF-RR-001. The explicit route is additive: no `state.json` involved,
    keyed on the file's current content."""
    project = _bound(bare_project)
    _flag(project)

    result = project.ok("accept-content", "--path", "requirements/todo-api.md")
    assert result.data["file"] == "requirements/todo-api.md"
    assert "sha256" in result.data
    assert not project.state_file.is_file(), "still no state — this route never touches it"

    ack_file = (project.root / "workitems" / FIXTURE_WORKITEM_ID / ".sdle"
                / "scan-acknowledgements.json")
    assert ack_file.is_file()
    record = json.loads(ack_file.read_text("utf-8"))
    assert record["acknowledgements"][0]["path"] == "requirements/todo-api.md"


def test_accept_content_with_path_refuses_when_nothing_is_flagged(bare_project):
    """Mirrors the bare form's `no_pending_confirmation` refusal: acknowledging
    unflagged content is not a thing this command does."""
    project = _bound(bare_project)
    result = project.run("accept-content", "--path", "requirements/todo-api.md")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "no_pending_confirmation"


def test_bare_accept_content_refuses_when_the_pending_file_is_gone(bare_project):
    """V-02, targeted verification of the round-2 fix. Before this fix, the
    bare form cleared `pending_confirm_action` and audited `content_accepted`
    for a file that no longer existed, reporting success although nothing
    was actually acknowledged. It must refuse `artifact_missing` instead,
    unchanged, the way `--path` already does for a missing file."""
    project = _bound(bare_project)
    project.record_governance()
    project.ok("init")
    _flag(project)
    project.run("scan", "--path", "requirements/todo-api.md")
    before = project.state()["pending_confirm_action"]
    assert before == "accept_content:requirements/todo-api.md"

    (project.root / "requirements" / "todo-api.md").unlink()

    result = project.run("accept-content")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "artifact_missing"
    assert project.state()["pending_confirm_action"] == before, (
        "a refused acceptance must not clear the pending confirmation")
    assert "content_accepted" not in project.audit_file.read_text("utf-8")


def test_post_init_acceptance_is_not_audited_twice_across_advances(bare_project):
    """V-03, targeted verification of the round-2 fix. Both immediate
    post-init audit entries used to omit the marker
    `record_scan_acknowledgement_audit` looks for, so its replay at the
    first advance appended a second `content_accepted` entry for the same
    acknowledgement. One acceptance must be exactly one entry, however many
    advances follow."""
    project = _bound(bare_project)
    project.record_governance()
    project.ok("init")
    _flag(project)
    project.run("scan", "--path", "requirements/todo-api.md")
    project.ok("accept-content")
    project.record_governance()

    project.ok("advance", "--to", "gate_constitution")
    project.write_artifact(".specify/memory/constitution.md")
    review_for_gate(project, "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution", "--comments", "ok")
    project.ok("advance", "--to", "gate_spec")

    audit = project.audit_file.read_text("utf-8")
    assert audit.count("content_accepted") == 1


def test_scanning_again_after_init_makes_acknowledgement_available(bare_project):
    """The state-backed route, exercised the way it actually arises now that
    DEF-RR-001 closes the bootstrap gap: content flagged for the first time
    *after* `init` (a mid-workflow edit), not content nobody ever
    acknowledged sailing through governance unexamined.

    A reader must not have to reword a legitimate requirement: scan to see
    the warning, then acknowledge with the bare, state-remembered form.
    """
    project = _bound(bare_project)
    project.record_governance()
    project.ok("init")

    _flag(project)  # a mid-workflow edit, after init

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


def test_registered_and_never_bound_runs_the_full_step_2b_sequence(bare_project):
    """DEF-RR-004, fixed properly after round 2 of the OPEN-01/02 review
    caught that the first attempt at this test (below, `..._runs_the_full_
    step_2b_sequence` and its flagged sibling) both started from `_bound`,
    so `reset` preserved an *existing* binding rather than exercising the
    genuinely unbound branch — `requirements show` reporting `bound: false`
    and step 2b's own bind step actually running. This is the other of the
    two ways a WorkItem can be "registered without state": `create`
    followed by nothing, never `reset`."""
    project = _registered(bare_project)
    shown = project.ok("requirements", "show")
    assert shown.data["bound"] is False
    assert shown.data["sources"] == []

    project.ok("requirements", "bind", "--source", "requirements/todo-api.md")
    rebound = project.ok("requirements", "show")
    assert rebound.data["bound"] is True

    project.ok("preflight")
    scanned = project.ok("scan", "--path", "requirements/todo-api.md")
    assert scanned.data["flagged"] is False
    project.record_governance()
    result = project.ok("init")
    assert result.data["current_phase"] == "constitution_draft"


def test_registered_and_never_bound_with_a_flagged_false_positive(bare_project):
    """The unbound variant of the flagged case, for the same reason."""
    project = _registered(bare_project)
    assert project.ok("requirements", "show").data["bound"] is False

    project.ok("requirements", "bind", "--source", "requirements/todo-api.md")
    _flag(project)
    project.ok("preflight")

    scanned = project.run("scan", "--path", "requirements/todo-api.md")
    assert scanned.exit_code == EXIT_REFUSED
    assert scanned.reason == "content_flagged"

    blocked = project.run("governance", "assess", "--input",
                          _write_governance_input(project))
    assert blocked.exit_code == EXIT_REFUSED
    assert blocked.reason == "governance_content_unacknowledged"

    project.ok("accept-content", "--path", "requirements/todo-api.md")
    project.record_governance()
    result = project.ok("init")
    assert result.data["current_phase"] == "constitution_draft"


def test_registered_without_state_runs_the_full_step_2b_sequence(bare_project):
    """DEF-RR-004. The `reset` variant of the same step 2b sequence: `reset`
    leaves the identity registered and preserves the existing binding, so
    `requirements show` reports `bound: true` here — the genuinely unbound
    branch is the pair of tests above."""
    project = _bound(bare_project)
    project.record_governance()
    project.ok("init")
    project.ok("reset")
    project.ok("reset", "--confirm")
    assert not project.state_file.is_file()

    # Step 2b: requirements show first, branch on data.bound (already true —
    # `reset` does not unbind). Re-bind is not required, but preflight,
    # scan and assess must all still run before init on this route.
    shown = project.ok("requirements", "show")
    assert shown.data["bound"] is True

    project.ok("preflight")
    scanned = project.ok("scan", "--path", "requirements/todo-api.md")
    assert scanned.data["flagged"] is False
    project.record_governance()
    result = project.ok("init")
    assert result.data["current_phase"] == "constitution_draft"


def test_registered_without_state_with_a_flagged_false_positive(bare_project):
    """DEF-RR-004. The same route, but the bound document trips the scan —
    the flagged-false-positive case R1-D04 named as missing from this
    section specifically."""
    project = _bound(bare_project)
    project.record_governance()
    project.ok("init")
    project.ok("reset")
    project.ok("reset", "--confirm")

    _flag(project)
    project.ok("preflight")

    scanned = project.run("scan", "--path", "requirements/todo-api.md")
    assert scanned.exit_code == EXIT_REFUSED
    assert scanned.reason == "content_flagged"

    blocked = project.run("governance", "assess", "--input",
                          _write_governance_input(project))
    assert blocked.exit_code == EXIT_REFUSED
    assert blocked.reason == "governance_content_unacknowledged"

    project.ok("accept-content", "--path", "requirements/todo-api.md")
    project.record_governance()
    result = project.ok("init")
    assert result.data["current_phase"] == "constitution_draft"


def _write_governance_input(project: Project) -> str:
    name = "governance-input.json"
    (project.root / name).write_text(json.dumps({
        "governanceInputVersion": "1",
        "quality": {n: {"result": "PASS", "finding": None}
                    for n in sdle.GOVERNANCE_POLICY_BUILTIN["quality_checks"]},
        "classification": {"type": "enhancement", "flow": "GREENFIELD"},
        "risk": {"signals": [], "proposedLevel": "LOW", "uncertainty": "LOW"},
    }), encoding="utf-8")
    return name


# --------------------------------------------------------------------------
# the canonical start command actually scans (DEF-RR-003)
# --------------------------------------------------------------------------


def test_sdle_start_scans_bound_documents_before_governance_assess():
    """R1-D03. A static check for a non-executable surface: `sdle-start.md`
    itself, not a test that types the sequence out and would pass regardless
    of what the shipped command file says."""
    from conftest import REPO_ROOT

    text = (REPO_ROOT / ".claude" / "commands" / "sdle-start.md").read_text("utf-8")
    scan_at = text.find("sdle.sh --workitem <id> scan --path")
    assess_at = text.find("sdle.sh --workitem <id> governance assess")
    assert scan_at != -1, "sdle-start.md must document a scan step"
    assert assess_at != -1, "sdle-start.md must document the assess step"
    assert scan_at < assess_at, "scan must come before governance assess"
