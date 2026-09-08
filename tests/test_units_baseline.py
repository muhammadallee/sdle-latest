"""The repository baseline (T08, contract §14).

§14 asks for a repository baseline that makes one thing true: after *either*
greenfield completion *or* brownfield discovery completion the repository has
the same minimum baseline shape, and the second WorkItem against the same
valid baseline does not rerun full discovery.

This file pins the reader (fail-closed), the single validity predicate, the
descriptor's "references, never copies" property, and — end to end through the
real CLI — the convergence invariant and its exit criterion.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from conftest import REPO_ROOT, Project, sdle
from test_integration_01_happy_path import run_happy_path
from test_units_artifact_review import review_for_gate
from test_units_flow_model import drive

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def paths_of(project: Project):
    paths = sdle.resolve_paths(str(project.root), str(project.skill_root))
    if project.workitem:
        paths = sdle.dataclass_replace(paths, workitem=project.workitem)
    return paths


def baseline_file(project: Project) -> Path:
    return project.root / ".sdle" / "baseline.json"


def plant(project: Project, body) -> Path:
    target = baseline_file(project)
    target.parent.mkdir(parents=True, exist_ok=True)
    text = body if isinstance(body, str) else json.dumps(body, indent=2)
    target.write_text(text, encoding="utf-8", newline="\n")
    return target


def read_planted(project: Project) -> dict:
    return json.loads(baseline_file(project).read_text(encoding="utf-8"))


def record_governance_expecting_refusal(project: Project, classification: dict):
    """`Project.record_governance` asserts success, so a refusal needs its own
    caller. The document is built exactly the way the fixture helper builds it,
    with the twelve check ids read from the engine rather than restated
    (invariant 7). No conftest fixture or helper is modified.
    """
    document = {
        "governanceInputVersion": "1",
        "quality": {name: {"result": "PASS", "finding": None}
                    for name in
                    sdle.GOVERNANCE_POLICY_BUILTIN["quality_checks"]},
        "classification": classification,
        "risk": {"signals": [], "proposedLevel": "LOW", "uncertainty": "LOW"},
    }
    name = "governance-input.json"
    target = project.root / name
    target.write_text(json.dumps(document, indent=2), encoding="utf-8",
                      newline="\n")
    try:
        return project.run("governance", "assess", "--input", name)
    finally:
        target.unlink()


# --------------------------------------------------------------------------
# N15 — the reader is fail-closed, and deliberately not `read_repo_config`
# --------------------------------------------------------------------------


def test_n15_an_absent_baseline_reads_as_none(project):
    assert sdle.read_baseline(paths_of(project)) is None


MALFORMED = {
    "not_json": "{not json",
    "a_string": '"a string"',
    "a_list": "[]",
    "unsupported_version": json.dumps({"baselineVersion": "99"}),
    "no_version": json.dumps({"establishedAt": "2026-01-01T00:00:00Z"}),
}


@pytest.mark.parametrize("case", sorted(MALFORMED))
def test_n15_every_malformed_baseline_is_an_integrity_failure(project, case):
    plant(project, MALFORMED[case])
    with pytest.raises(sdle.IntegrityError) as raised:
        sdle.read_baseline(paths_of(project))
    assert raised.value.reason == "baseline_invalid"
    assert raised.value.exit_code == EXIT_INTEGRITY


@pytest.mark.parametrize("case", sorted(MALFORMED))
def test_n15_the_cli_surfaces_that_as_exit_three(project, case):
    plant(project, MALFORMED[case])
    result = project.run("validate")
    assert result.exit_code == EXIT_INTEGRITY, result


def test_n15_the_baseline_reader_never_swallows_and_defaults():
    """No runtime reader returns a default from an exception handler.

    At T08 this test read as a *contrast*: `read_baseline` must not swallow,
    unlike `read_repo_config`, which did. T09 adopted T05 NB-4 and made that
    reader fail-closed too — it was named T09's for exactly this reason, that
    a fail-open reader anywhere in a file whose subject is "do not weaken
    governance silently" is not defensible — so the contrast has become a
    shared property, and the second half below asserts the inverse of what it
    used to.

    The rule is the same for both and is worth stating once: a corrupt file
    must never read as an absent one. A baseline that silently defaulted would
    let a damaged file read as "not yet established" and make §14's
    convergence invariant unprovable, which is the failure direction ADR-003
    §3 already rejected for the governance policy.
    """
    import ast
    source = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    reader = next(node for node in ast.walk(tree)
                  if isinstance(node, ast.FunctionDef)
                  and node.name == "read_baseline")

    for handler in [n for n in ast.walk(reader) if isinstance(n, ast.ExceptHandler)]:
        for statement in ast.walk(handler):
            if isinstance(statement, ast.Return):
                raise AssertionError(
                    "read_baseline returns a value from an exception handler; "
                    "it must raise IntegrityError instead")

    # T09/D14, inverting what this block asserted at T08: the repository
    # configuration reader must not swallow and default either. The check is
    # the same AST shape, so the two readers are held to one rule.
    config_reader = next(node for node in ast.walk(tree)
                         if isinstance(node, ast.FunctionDef)
                         and node.name == "read_repo_config")
    handlers = [h for h in ast.walk(config_reader)
                if isinstance(h, ast.ExceptHandler)]
    assert handlers, ("read_repo_config is expected to handle OSError and "
                      "JSON errors; a reader with no handler would satisfy "
                      "the assertion below vacuously")
    swallowed = [s for h in handlers
                 for s in ast.walk(h) if isinstance(s, ast.Return)]
    assert not swallowed, (
        "read_repo_config returns a value from an exception handler; an "
        "unreadable config.json must refuse, not default (T05 NB-4, adopted "
        "by T09/D14)")


# --------------------------------------------------------------------------
# N16/N17 — the two read-only commands
# --------------------------------------------------------------------------


def test_n16_absent_reports_absent_and_emits_no_finding(project):
    shown = project.ok("baseline", "show")
    assert shown.data["status"] == "ABSENT"
    assert shown.data["present"] is False
    assert shown.data["findings"] == []
    assert shown.data["baseline"] is None

    validated = project.ok("validate")
    assert [f for f in validated.data["findings"]
            if f["check"].startswith("baseline")] == []


def test_n16_baseline_show_writes_nothing(project):
    before = sorted(p.relative_to(project.root).as_posix()
                    for p in project.root.rglob("*"))
    project.ok("baseline", "show")
    after = sorted(p.relative_to(project.root).as_posix()
                   for p in project.root.rglob("*"))
    assert after == before


def test_n17_baseline_validate_exits_zero_only_on_valid(project):
    assert project.run("baseline", "validate").exit_code == EXIT_REFUSED

    project.establish_baseline()
    ok = project.ok("baseline", "validate")
    assert ok.data["status"] == "VALID"
    assert ok.data["findings"] == []


@pytest.mark.parametrize("status", ["ABSENT", "INVALID", "STALE"])
def test_n17_every_non_valid_status_refuses_baseline_not_valid(project, status):
    if status == "INVALID":
        document = project.establish_baseline()
        del document["commit"]
        plant(project, document)
    elif status == "STALE":
        project.write_artifact("design/app/app-design.md")
        document = project.establish_baseline()
        assert document["references"]["architecture"], "fixture must reference it"
        project.write_artifact("design/app/app-design.md",
                               "# Redesigned\n\n" + "Different content. " * 8)

    result = project.run("baseline", "validate")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "baseline_not_valid"
    assert result.data["status"] == status


def test_n17_a_refused_validate_leaves_the_ledger_untouched(started):
    """A5: `baseline validate` is a pure reader like every other refusal T08
    adds."""
    before = started.audit_file.read_bytes()
    assert started.run("baseline", "validate").exit_code == EXIT_REFUSED
    assert started.audit_file.read_bytes() == before


# --------------------------------------------------------------------------
# N18/N19 — material invalidation is exactly three checks, and only three
# --------------------------------------------------------------------------


def test_n18_a_missing_required_key_is_baseline_invalid(project):
    document = project.establish_baseline()
    del document["nonNegotiables"]
    plant(project, document)

    findings = project.run("baseline", "show").data["findings"]
    assert [f["check"] for f in findings] == ["baseline_invalid"]
    assert findings[0]["severity"] == "error"
    assert "nonNegotiables" in findings[0]["detail"]


def test_n18_an_unregistered_producer_is_an_error(project):
    document = project.establish_baseline()
    document["establishedBy"] = dict(document["establishedBy"],
                                     workitem="never-registered")
    plant(project, document)

    findings = project.run("baseline", "show").data["findings"]
    named = [f for f in findings if f["check"] == "baseline_producer_unregistered"]
    assert len(named) == 1
    assert named[0]["severity"] == "error"
    assert "never-registered" in named[0]["detail"]


def test_n18_a_missing_reference_is_an_error(project):
    project.write_artifact(".specify/memory/constitution.md")
    document = project.establish_baseline()
    assert document["references"]["constitution"], "fixture must reference it"

    (project.root / ".specify" / "memory" / "constitution.md").unlink()

    findings = project.run("baseline", "show").data["findings"]
    named = [f for f in findings if f["check"] == "baseline_reference_missing"]
    assert len(named) == 1
    assert named[0]["severity"] == "error"
    assert project.run("baseline", "show").data["status"] == "INVALID"


def test_n19_a_changed_reference_is_a_warning_and_yields_stale(project):
    """D7, pinned so a later phase cannot flip it silently.

    `design_generation` runs in ITERATIVE and rewrites the design document. If
    a changed reference invalidated the baseline, the *third* WorkItem in any
    repository would be forced back into full rediscovery — the opposite of
    §26 item 22. A missing reference is different in kind: the baseline's
    claims can no longer be checked at all.
    """
    project.write_artifact("design/app/app-design.md")
    project.establish_baseline()
    project.write_artifact("design/app/app-design.md",
                           "# Redesigned\n\n" + "Different content. " * 8)

    shown = project.run("baseline", "show").data
    named = [f for f in shown["findings"]
             if f["check"] == "baseline_reference_changed"]
    assert len(named) == 1
    assert named[0]["severity"] == "warning"
    assert shown["status"] == "STALE"

    # And it refuses nothing: `validate` reports it and still exits 0.
    validated = project.run("validate")
    assert validated.exit_code == EXIT_OK, validated


def test_the_material_invalidation_set_is_exactly_three_checks(project):
    """A11. Written as an assertion so widening it cannot be accidental."""
    invalidating = set()

    document = project.establish_baseline()
    del document["commit"]
    plant(project, document)
    invalidating |= {f["check"] for f in project.run("baseline", "show").data["findings"]
                     if f["severity"] == "error"}

    document = project.establish_baseline()
    document["establishedBy"] = dict(document["establishedBy"], workitem="ghost")
    plant(project, document)
    invalidating |= {f["check"] for f in project.run("baseline", "show").data["findings"]
                     if f["severity"] == "error"}

    project.write_artifact(".specify/memory/constitution.md")
    project.establish_baseline()
    (project.root / ".specify" / "memory" / "constitution.md").unlink()
    invalidating |= {f["check"] for f in project.run("baseline", "show").data["findings"]
                     if f["severity"] == "error"}

    assert invalidating == {"baseline_invalid",
                            "baseline_producer_unregistered",
                            "baseline_reference_missing"}


# --------------------------------------------------------------------------
# N20 — one predicate, two consumers, no disagreement
# --------------------------------------------------------------------------


def test_n20_validate_and_baseline_show_report_the_same_findings(project):
    project.write_artifact("design/app/app-design.md")
    project.establish_baseline()
    project.write_artifact("design/app/app-design.md",
                           "# Redesigned\n\n" + "Different content. " * 8)

    shown = project.run("baseline", "show").data["findings"]
    validated = [f for f in project.run("validate").data["findings"]
                 if f["check"].startswith("baseline")]

    assert shown == validated
    assert shown, "the fixture must produce at least one finding"


def test_n20_the_predicate_has_exactly_two_consumers():
    """Invariant 7 asserted on source: two callers can never disagree about
    one repository because there is only one implementation, reached from
    exactly the two places that are allowed to reach it."""
    import ast
    source = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    owner: dict[int, str] = {}

    def annotate(node, name):
        for child in ast.iter_child_nodes(node):
            nm = child.name if isinstance(child, ast.FunctionDef) else name
            owner[id(child)] = nm
            annotate(child, nm)

    annotate(tree, "<module>")
    callers = {owner.get(id(node))
               for node in ast.walk(tree)
               if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name)
               and node.func.id == "baseline_findings"}
    assert callers == {"baseline_state", "collect_validation_findings"}


# --------------------------------------------------------------------------
# N21/N22 — the descriptor references, and the builder is total
# --------------------------------------------------------------------------


def test_n21_the_descriptor_carries_all_nine_section_14_facts(project):
    project.write_artifact(".specify/memory/constitution.md")
    project.write_artifact("design/app/app-design.md")
    document = project.establish_baseline()

    # §14's nine facts, one assertion each.
    assert document["baselineVersion"] == sdle.BASELINE_VERSION
    assert document["establishedBy"]["workitem"] == project.workitem
    assert "commit" in document
    assert document["references"]["constitution"]["path"] == \
        ".specify/memory/constitution.md"
    assert document["references"]["architecture"][0]["path"] == \
        "design/app/app-design.md"
    assert isinstance(document["references"]["adrs"], list)
    assert set(document["nonNegotiables"]) == {"source", "findingIds"}
    assert document["discovery"]["status"] in ("PERFORMED", "NOT_REQUIRED")
    assert document["establishedAt"]

    assert set(document) == set(sdle.BASELINE_REQUIRED_KEYS)


def test_n21_no_referenced_file_body_appears_in_the_baseline(project):
    """"References canonical artifacts instead of copying them" (§14)."""
    marker = "SENTINEL-CONSTITUTION-BODY-DO-NOT-COPY"
    project.write_artifact(".specify/memory/constitution.md",
                           f"# Constitution\n\n{marker}\n" + "Body. " * 30)
    project.write_artifact(
        "design/app/app-design.md",
        "# Design\n\nSENTINEL-DESIGN-BODY-DO-NOT-COPY\n" + "Body. " * 30)
    project.establish_baseline()

    raw = baseline_file(project).read_text(encoding="utf-8")
    assert marker not in raw
    assert "SENTINEL-DESIGN-BODY-DO-NOT-COPY" not in raw

    document = read_planted(project)
    for reference in ([document["references"]["constitution"]]
                      + document["references"]["architecture"]
                      + document["references"]["adrs"]):
        assert set(reference) == {"path", "sha256"}
        assert len(reference["sha256"]) == 64


def test_n22_the_builder_never_raises_when_every_input_is_absent(project):
    """It runs inside the final gate approval, after `gate_approved` is
    already in the append-only ledger. It may not raise."""
    paths = paths_of(project)
    consts = sdle.load_constants(paths)
    state = sdle.load_template(paths)

    assert not (project.root / ".specify" / "memory" / "constitution.md").exists()
    assert not (project.root / "design").exists()
    assert not (project.runtime / "discovery.json").exists()

    document = sdle.baseline_descriptor(paths, state, consts, "exec-1",
                                        sdle.now_iso())

    assert document["references"]["constitution"] is None
    assert document["references"]["architecture"] == []
    assert document["references"]["adrs"] == []
    assert document["discovery"]["status"] == "NOT_REQUIRED"
    assert document["discovery"]["record"] is None
    assert document["nonNegotiables"]["findingIds"] == []
    assert document["supersedes"] is None
    assert set(document) == set(sdle.BASELINE_REQUIRED_KEYS)


def test_n22_a_corrupt_discovery_record_does_not_make_the_builder_raise(
        project):
    paths = paths_of(project)
    consts = sdle.load_constants(paths)
    paths.runtime.mkdir(parents=True, exist_ok=True)
    paths.discovery_file.write_text("{not json", encoding="utf-8")

    document = sdle.baseline_descriptor(paths, sdle.load_template(paths),
                                        consts, "exec-1", sdle.now_iso())
    assert document["discovery"]["status"] == "NOT_REQUIRED"


def test_the_descriptor_records_what_it_supersedes(project):
    first = project.establish_baseline()
    second = project.establish_baseline()
    assert second["supersedes"] is not None
    assert second["supersedes"]["establishedAt"] == first["establishedAt"]
    assert len(second["supersedes"]["sha256"]) == 64


# --------------------------------------------------------------------------
# N23/N27/N28 — the convergence invariant, established through the real CLI
# --------------------------------------------------------------------------
#
# §14's convergence sentence names two completions and nothing else: after
# *either* greenfield completion *or* brownfield discovery completion the
# repository has the same minimum baseline shape. These three tests drive that
# rather than assert it — two full traversals, compared descriptor to
# descriptor.


def second_repository(project: Project, destination: Path) -> Project:
    """A byte-identical second scratch repository.

    §14's convergence invariant is a statement about two *repositories*, so it
    cannot be proved inside one. Copying the fixture before either run is
    driven is what makes the two descriptors comparable: the only difference
    between them is the flow that was traversed.
    """
    shutil.copytree(project.root, destination)
    return Project(destination, destination / ".claude" / "skills" / "sdle",
                   workitem=project.workitem, pin=project.pin)


def test_n23_both_establishing_flows_produce_the_same_baseline_shape(
        git_project, tmp_path):
    """N23. The convergence invariant, driven end to end in two repositories.

    GREENFIELD in one, BROWNFIELD_DISCOVERY in the other. Both complete, both
    establish a baseline, both report VALID, and the two descriptors carry the
    same required key set — only the discovery-derived content differs. That
    difference is the whole point: `NOT_REQUIRED` versus `PERFORMED` is the
    honest record of which repository was read.
    """
    brown = second_repository(git_project, tmp_path / "brownfield")

    green_seen = drive(git_project, "GREENFIELD")
    brown_seen = drive(brown, "BROWNFIELD_DISCOVERY")

    assert green_seen[-1] == "complete"
    assert brown_seen[-1] == "complete"
    assert "discovery" not in green_seen
    assert "discovery" in brown_seen

    for repository in (git_project, brown):
        assert baseline_file(repository).is_file(), repository.root
        shown = repository.ok("baseline", "show").data
        assert shown["status"] == "VALID", shown
        assert shown["findings"] == []

    green = read_planted(git_project)
    brown_document = read_planted(brown)

    # The convergence invariant itself: same required key set, same shape.
    assert set(green) == set(brown_document) == set(sdle.BASELINE_REQUIRED_KEYS)
    assert set(green["references"]) == set(brown_document["references"]) \
        == set(sdle.BASELINE_REFERENCE_KINDS)
    assert set(green["discovery"]) == set(brown_document["discovery"])

    assert green["discovery"]["status"] == "NOT_REQUIRED"
    assert green["discovery"]["record"] is None
    assert green["establishedBy"]["flow"] == "GREENFIELD"

    assert brown_document["discovery"]["status"] == "PERFORMED"
    assert brown_document["discovery"]["record"] == (
        f"workitems/{brown.workitem}/.sdle/discovery.json")
    assert len(brown_document["discovery"]["recordSha256"]) == 64
    assert brown_document["establishedBy"]["flow"] == "BROWNFIELD_DISCOVERY"


def test_n23_only_the_two_declared_flows_establish_a_baseline(git_project):
    """The other half of D6: a flow that performed no discovery may not
    establish a "discovered" baseline. HOTFIX completes and writes nothing."""
    assert "HOTFIX" not in sdle.BASELINE_ESTABLISHING_FLOWS

    seen = drive(git_project, "HOTFIX")

    assert seen[-1] == "complete"
    assert not baseline_file(git_project).exists()
    assert git_project.ok("baseline", "show").data["status"] == "ABSENT"


def test_n27_the_baseline_write_cannot_block_completion(git_project):
    """N27/F4. The write runs after `gate_approved` is already in the
    append-only ledger, so it may not fail — not even when every reference it
    would record has been removed under it.

    The two artifacts are deleted between the last generation step and the
    final approval, which is the sharpest form of the case: the descriptor is
    built against a repository that no longer holds what it approved.
    """
    drive(git_project, "GREENFIELD", stop="gate_security")
    constitution = git_project.root / ".specify" / "memory" / "constitution.md"
    design = git_project.root / "design" / "app" / "app-design.md"
    assert constitution.is_file() and design.is_file()
    constitution.unlink()
    design.unlink()

    review_for_gate(git_project, "gate_security")
    result = git_project.run("gate", "approve", "--gate", "gate_security")

    assert result.exit_code == EXIT_OK, result
    assert git_project.state()["current_phase"] == "complete"
    assert result.data["completion_summary"]

    document = read_planted(git_project)
    assert document["references"]["constitution"] is None
    assert document["references"]["architecture"] == []
    assert document["references"]["adrs"] == []

    # And it is honestly reported as unsound rather than quietly accepted:
    # the descriptor is written, `baseline_findings` decides validity.
    assert git_project.ok("baseline", "show").data["status"] == "VALID"


def test_n28_completion_emits_exactly_one_baseline_established_entry(
        git_project):
    """N28. One entry, an intact chain, and a completion summary unchanged
    field for field by T08."""
    summary_before_fields = {
        "workflow_version", "flow", "project_name", "completed_at",
        "phases_completed", "security_review_artifact", "all_gates_approved",
    }

    run_happy_path(git_project)

    audit = git_project.audit_file.read_text(encoding="utf-8")
    assert audit.count(sdle.BASELINE_AUDIT_EVENT) == 1
    assert audit.count("workflow_complete") == 1
    # Ordered: the baseline entry follows `workflow_complete`, so the ledger
    # reads "the workflow finished, and this is what it left behind".
    assert audit.index("workflow_complete") < \
        audit.index(sdle.BASELINE_AUDIT_EVENT)

    verify = git_project.ok("audit", "verify")
    assert verify.data["chain_ok"] is True

    summary = json.loads(
        (git_project.runtime / "completion-summary.json")
        .read_text(encoding="utf-8"))
    assert set(summary) == summary_before_fields
    assert summary["all_gates_approved"] is True


def test_the_baseline_write_has_exactly_one_call_site(git_project):
    """D6, asserted on source: one writer, one caller. A second call site is
    the governance bypass `flow set` was refused for."""
    import ast
    tree = ast.parse((REPO_ROOT / "scripts" / "sdle.py")
                     .read_text(encoding="utf-8"))
    callers = {fn.name for fn in ast.walk(tree)
               if isinstance(fn, ast.FunctionDef)
               for node in ast.walk(fn)
               if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name)
               and node.func.id == "establish_baseline"}
    assert callers == {"cmd_gate_approve"}, callers

    writers = {fn.name for fn in ast.walk(tree)
               if isinstance(fn, ast.FunctionDef)
               and "baseline_file" in {node.attr for node in ast.walk(fn)
                                       if isinstance(node, ast.Attribute)}
               and any(isinstance(node, ast.Call)
                       and isinstance(node.func, ast.Name)
                       and node.func.id == "write_atomic"
                       for node in ast.walk(fn))}
    assert writers == {"establish_baseline"}, writers


# --------------------------------------------------------------------------
# N24/N25/N26 — §14's exit criterion, and the two `init`-time refusals
# --------------------------------------------------------------------------
#
# §14's exit criterion is a statement about a *second* WorkItem, so it cannot
# be proved by inspecting one run. N24 drives it: WI-A discovers the
# repository, WI-B is refused the chance to discover it again, and WI-B then
# completes an ITERATIVE run that never enters `discovery`.


def create_wi(project: Project, name: str):
    return project.ok("workitem", "create", "--name", name)


def runtime_dir(project: Project, workitem: str) -> Path:
    return project.root / "workitems" / workitem / ".sdle"


def test_n24_the_second_workitem_does_not_rediscover_the_repository(
        git_project):
    """N24 / acceptance A9 — contract §14's exit criterion, end to end.

    Every step goes through the real CLI. Nothing here plants a baseline: the
    one WI-B is measured against is the one WI-A's completion established.
    """
    create_wi(git_project, "Wi B")
    a = git_project.as_workitem(git_project.workitem)
    b = git_project.as_workitem("wi-b")

    # 1. WI-A performs the discovery, and completing it establishes the
    #    baseline every later WorkItem converges onto.
    a_seen = drive(a, "BROWNFIELD_DISCOVERY")
    assert "discovery" in a_seen
    assert a_seen[-1] == "complete"
    assert git_project.ok("baseline", "show").data["status"] == "VALID"

    # 2. WI-B proposes to rediscover it, and is refused. Nothing is created.
    b.record_governance(
        classification={"type": "enhancement",
                        "flow": "BROWNFIELD_DISCOVERY"})
    refused = b.run("init", session="wib")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "baseline_present", refused
    assert refused.data["baseline_status"] == "VALID"
    assert not (runtime_dir(git_project, "wi-b") / "state.json").exists()
    assert not (runtime_dir(git_project, "wi-b") / "audit.md").exists()
    assert not (runtime_dir(git_project, "wi-b") / "execution.json").exists()
    # The remedies the message names are the two the contract allows.
    assert "ITERATIVE" in refused.envelope["message"]
    assert "rediscovery" in refused.envelope["message"]

    # 3. Re-assessed as ITERATIVE it initialises and completes — and never
    #    enters `discovery`. Asserted on the traversal, on `phase_history`
    #    and on WI-B's own ledger.
    b_seen = drive(b, "ITERATIVE")

    assert b_seen[-1] == "complete"
    assert "discovery" not in b_seen
    state = b.state()
    assert state["flow"] == "ITERATIVE"
    assert "discovery" not in [entry["phase"]
                               for entry in state["phase_history"]]
    assert "discovery" not in b.audit_file.read_text(encoding="utf-8")
    assert not (runtime_dir(git_project, "wi-b") / "discovery.json").exists()

    # WI-A's ledger is untouched by any of it, and still records the discovery.
    assert "discovery" in a.audit_file.read_text(encoding="utf-8")


def test_n24_the_refusal_leaves_the_ledger_and_the_repository_untouched(
        git_project):
    """The B1/NB-6 property, re-proved for R1. A refused `init` is a pure
    reader ahead of the first `mkdir`, so it appends nothing anywhere."""
    create_wi(git_project, "Wi B")
    a = git_project.as_workitem(git_project.workitem)
    b = git_project.as_workitem("wi-b")
    drive(a, "GREENFIELD")

    a_audit = a.audit_file.read_bytes()
    a_state = a.state_file.read_bytes()
    baseline_before = baseline_file(git_project).read_bytes()

    b.record_governance(
        classification={"type": "enhancement",
                        "flow": "BROWNFIELD_DISCOVERY"})
    assert b.run("init", session="wib").reason == "baseline_present"

    assert a.audit_file.read_bytes() == a_audit
    assert a.state_file.read_bytes() == a_state
    assert baseline_file(git_project).read_bytes() == baseline_before
    assert a.ok("audit", "verify").data["chain_ok"] is True


def test_n25_the_rediscovery_opt_in_permits_the_refused_binding(git_project):
    """N25. The monotone opt-in: it can only ask for more work."""
    create_wi(git_project, "Wi B")
    a = git_project.as_workitem(git_project.workitem)
    b = git_project.as_workitem("wi-b")
    drive(a, "GREENFIELD")
    assert git_project.ok("baseline", "show").data["status"] == "VALID"

    b.record_governance(
        classification={"type": "enhancement",
                        "flow": "BROWNFIELD_DISCOVERY",
                        "rediscovery": True})

    assert b.ok("init", session="wib").exit_code == EXIT_OK
    assert b.state()["flow"] == "BROWNFIELD_DISCOVERY"
    assert b.state()["current_phase"] == "discovery"


@pytest.mark.parametrize(
    "flow", [f for f in sdle.ENGINEERING_FLOWS
             if f != sdle.BASELINE_REDISCOVERY_FLOW])
def test_n25_rediscovery_with_any_other_flow_is_a_contradiction(project, flow):
    """Asking to rediscover the repository while binding a flow that performs
    no discovery is refused, not ignored."""
    result = record_governance_expecting_refusal(
        project, {"type": "enhancement", "flow": flow, "rediscovery": True})

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "classification_invalid", result
    assert result.data["field"] == "rediscovery"


def test_n25_rediscovery_defaults_to_false_and_must_be_a_boolean(project):
    project.record_governance()
    record = sdle.read_governance_record(paths_of(project))
    assert record["classification"]["rediscovery"] is False

    result = record_governance_expecting_refusal(
        project, {"type": "enhancement", "flow": "BROWNFIELD_DISCOVERY",
                  "rediscovery": "yes"})
    assert result.reason == "classification_invalid", result


def test_n26_iterative_without_a_baseline_is_refused(project):
    """N26 / R2. §13's ITERATIVE definition made true: it works from an
    established baseline and performs no rediscovery, so without one there is
    nothing for it to work from."""
    assert not baseline_file(project).exists()
    project.record_governance(
        classification={"type": "enhancement", "flow": "ITERATIVE"})

    result = project.run("init", session="s")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "baseline_required", result
    assert result.data["baseline_status"] == "ABSENT"
    assert not project.state_file.exists()
    assert not project.audit_file.exists()
    assert not (project.runtime / "execution.json").exists()


def test_n26_an_invalid_baseline_does_not_authorise_iterative(project):
    """`INVALID` is §14's material invalidation, so it authorises nothing."""
    project.establish_baseline(establishedBy={"workitem": "wi-not-registered",
                                              "flow": "GREENFIELD",
                                              "executionId": "x"})
    assert project.ok("baseline", "show").data["status"] == "INVALID"
    project.record_governance(
        classification={"type": "enhancement", "flow": "ITERATIVE"})

    result = project.run("init", session="s")

    assert result.reason == "baseline_required", result
    assert result.data["baseline_status"] == "INVALID"
    assert not project.state_file.exists()


def test_n26_a_stale_baseline_authorises_iterative(project):
    """The other half of D7's decision, pinned so a later phase cannot flip it
    silently: a *changed* reference is a warning, and a warning never refuses.
    Forcing rediscovery on it would contradict §26 item 22."""
    project.write_artifact("design/app/app-design.md")
    project.establish_baseline()
    project.write_artifact("design/app/app-design.md",
                           "# Design, rewritten by a later WorkItem\n"
                           + "Body. " * 60)
    assert project.ok("baseline", "show").data["status"] == "STALE"
    project.record_governance(
        classification={"type": "enhancement", "flow": "ITERATIVE"})

    assert project.ok("init", session="s").exit_code == EXIT_OK
    assert project.state()["flow"] == "ITERATIVE"


@pytest.mark.parametrize("flow", ["DEFECT_FIX", "HOTFIX"])
def test_n26_defect_fix_and_hotfix_are_deliberately_not_covered(project, flow):
    """§13 gives neither a baseline clause, and blocking an emergency hotfix on
    a repository-level artifact would be a governance change §14 did not ask
    for. Pinned so extending R2 to them cannot be silent."""
    assert not baseline_file(project).exists()
    assert flow not in (sdle.BASELINE_REDISCOVERY_FLOW,
                        sdle.BASELINE_REQUIRING_FLOW)
    project.record_governance(
        classification={"type": "enhancement", "flow": flow})

    assert project.ok("init", session="s").exit_code == EXIT_OK
    assert project.state()["flow"] == flow


def test_greenfield_is_never_refused_by_either_rule(git_project):
    """Neither rule covers GREENFIELD, with or without a baseline. A repository
    may start a fresh greenfield WorkItem at any time."""
    create_wi(git_project, "Wi B")
    a = git_project.as_workitem(git_project.workitem)
    b = git_project.as_workitem("wi-b")
    drive(a, "GREENFIELD")

    b.record_governance()

    assert b.ok("init", session="wib").exit_code == EXIT_OK
    assert b.state()["flow"] == "GREENFIELD"


def test_the_binding_decision_is_recorded_in_the_flow_selected_entry(project):
    """D8: the decision is made on the facts at binding time and never
    re-checked mid-flight, so those facts have to be in the ledger."""
    project.record_governance()
    project.ok("init", session="s")

    entry = [block for block in
             project.audit_file.read_text(encoding="utf-8").split("## AUDIT ")
             if "flow_selected" in block]
    assert len(entry) == 1
    assert "ABSENT" in entry[0]


def test_the_baseline_precondition_has_exactly_one_call_site():
    """R1/R2 are evaluated at `init` and nowhere else. A second call site would
    be the mid-flight refusal D8 rejected."""
    import ast
    tree = ast.parse((REPO_ROOT / "scripts" / "sdle.py")
                     .read_text(encoding="utf-8"))
    callers = {fn.name for fn in ast.walk(tree)
               if isinstance(fn, ast.FunctionDef)
               for node in ast.walk(fn)
               if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name)
               and node.func.id == "baseline_precondition"}
    assert callers == {"cmd_init"}, callers


def test_the_refusal_precedes_every_write_in_cmd_init():
    """The property I4 rests on, asserted on the parsed source rather than
    inferred: `baseline_precondition` is called before the first `mkdir`, the
    first `write_execution_file` and the first `append_audit` in `cmd_init`."""
    import ast
    tree = ast.parse((REPO_ROOT / "scripts" / "sdle.py")
                     .read_text(encoding="utf-8"))
    init = next(fn for fn in ast.walk(tree)
                if isinstance(fn, ast.FunctionDef) and fn.name == "cmd_init")

    def first_line(predicate) -> int:
        return min((node.lineno for node in ast.walk(init)
                    if isinstance(node, ast.Call) and predicate(node)),
                   default=10 ** 9)

    check = first_line(lambda n: isinstance(n.func, ast.Name)
                       and n.func.id == "baseline_precondition")
    writes = min(
        first_line(lambda n: isinstance(n.func, ast.Attribute)
                   and n.func.attr == "mkdir"),
        first_line(lambda n: isinstance(n.func, ast.Name)
                   and n.func.id in {"write_execution_file", "append_audit",
                                     "save_state", "write_active_context"}),
    )
    assert check < writes, (check, writes)


# --------------------------------------------------------------------------
# N34 — T08 added nothing risk-conditional; T09 is where gate requirements
# became policy-driven, and it did so from one home
# --------------------------------------------------------------------------


def test_gate_requirements_are_policy_driven_from_exactly_one_home(project):
    """Inverted at T09 (X6). This was T08's leakage guard: it asserted that
    `governance gates` still reported itself advisory and that the would-be
    gate set had no consumer. §15 is the phase whose subject that is, so the
    guard now pins the property that replaced it — the requirement model has a
    single home, and the report no longer claims to be inert.

    What did NOT move is the second half below: nothing T08 added consults
    risk, the gate set or a governance level to decide anything. Discovery is
    still selected structurally."""
    project.record_governance()

    data = project.ok("governance", "gates").data
    assert "advisory" not in data
    assert set(data["required_gates"]) | set(data["omittable_gates"])
    assert not set(data["required_gates"]) & set(data["omittable_gates"])

    import ast
    tree = ast.parse((REPO_ROOT / "scripts" / "sdle.py")
                     .read_text(encoding="utf-8"))
    callers = {fn.name for fn in ast.walk(tree)
               if isinstance(fn, ast.FunctionDef)
               for node in ast.walk(fn)
               if isinstance(node, ast.Call)
               and isinstance(node.func, ast.Name)
               and node.func.id == "required_gate_set"}
    # T06 wrote `required_gate_set`; T09 consumes it rather than building a
    # parallel mechanism, so its one caller is the model that decides.
    assert callers == {"gate_requirements"}, callers

    reasons_callers = {fn.name for fn in ast.walk(tree)
                       if isinstance(fn, ast.FunctionDef)
                       for node in ast.walk(fn)
                       if isinstance(node, ast.Call)
                       and isinstance(node.func, ast.Name)
                       and node.func.id == "_policy_gate_reasons"}
    assert reasons_callers == {"required_gate_set", "gate_requirements"}, \
        reasons_callers

    # And nothing T08 added consults risk, the would-be gate set or a
    # governance level to decide anything.
    for name in ("baseline_precondition", "establish_baseline",
                 "baseline_descriptor", "baseline_findings",
                 "discovery_precondition", "evaluate_discovery"):
        fn = next(node for node in ast.walk(tree)
                  if isinstance(node, ast.FunctionDef) and node.name == name)
        referenced = {node.id for node in ast.walk(fn)
                      if isinstance(node, ast.Name)}
        leaked = referenced & {"required_gate_set", "evaluate_risk",
                               "GOVERNANCE_LEVELS", "read_governance_policy"}
        assert not leaked, (name, leaked)


def test_n34_every_flow_gate_set_is_structural_not_policy_driven(project):
    """Flow MEMBERSHIP stayed structural. Each flow's gates are exactly the
    gate phases of its declared phase list, and no policy value participates.

    Sharpened at T09 (X7) rather than inverted, because it pins the
    distinction the phase turns on: which gates a WorkItem *has* is T07's and
    is structural; whether a gate it has *requires an approval* is T09's and
    is policy-driven. Blurring the two is how "the policy removed a gate"
    would become sayable."""
    consts = sdle.load_constants(paths_of(project))
    for name in sdle.ENGINEERING_FLOWS:
        flow = consts.flow(name)
        assert list(flow.gate_keys) == [consts.phase_to_gate_key[p]
                                        for p in flow.phases
                                        if p in consts.phase_to_gate_key], name
