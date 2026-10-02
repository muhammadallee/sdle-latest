"""Findings about compatibility and dependencies cite the baseline once one exists.

Whether a cited entry *supports* the finding stays the assessor's judgement. What the
engine checks is the deterministic part: the entry exists in a sound baseline and its
pinned record has not moved since.
"""

from __future__ import annotations

import json

import pytest

from conftest import sdle
from test_units_refinement_commands import (  # noqa: F401  (helpers shared on purpose)
    DOC, assess, call, entered, proposal, record, snapshot)

CITED = ("compatibility", "dependencies")


def establish(project):
    """A sound baseline built through the engine's own builder, with the pieces a
    citation can point at overridden: a discovery record (findings F-001, F-002)
    and a constitution reference. Whether it is sound is asserted, not assumed."""
    import hashlib
    record = project.runtime / "discovery.json"
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps({"findings": [{"id": "F-001"}, {"id": "F-002"}]}),
                      encoding="utf-8")
    note = project.root / "docs" / "constitution-ref.md"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text("# Ground rules\n", encoding="utf-8")
    project.establish_baseline(
        discovery={"status": "PERFORMED", "counts": None,
                   "record": record.relative_to(project.root).as_posix(),
                   "recordSha256": hashlib.sha256(record.read_bytes()).hexdigest()},
        references={"constitution": {
            "path": "docs/constitution-ref.md",
            "sha256": hashlib.sha256(note.read_bytes()).hexdigest()},
            "architecture": [], "adrs": []})
    shown = project.ok("baseline", "show")
    assert shown.data["status"] in ("VALID", "STALE"), shown
    return shown


def finding(check, citations=None, text="not stated"):
    out = {"checkId": check, "text": text}
    if citations is not None:
        out["citations"] = citations
    return out


def blocked_on(project, *checks):
    assert assess(project, *checks).reason == "requirements_quality_blocked"


def propose_with(project, findings):
    return call(project, "propose", proposal(project, findings=findings, edits=[]))


def test_without_a_baseline_a_citation_cannot_resolve(project):
    blocked_on(project, "compatibility")
    before = snapshot(project)
    result = propose_with(project, [finding("compatibility", [
        {"kind": "discovery-finding", "id": "F-001"}])])
    assert result.reason == "refinement_citation_unresolved"
    assert snapshot(project) == before


def test_without_a_baseline_no_citation_is_asked_for(project):
    blocked_on(project, "compatibility")
    assert propose_with(project, [finding("compatibility")]).exit_code == 0


@pytest.mark.parametrize("check", CITED)
def test_with_a_sound_baseline_these_findings_must_cite_it(project, check):
    establish(project)
    blocked_on(project, check)
    before = snapshot(project)
    result = propose_with(project, [finding(check)])
    assert result.reason == "refinement_citation_unresolved"
    assert snapshot(project) == before


@pytest.mark.parametrize("check", CITED)
def test_a_citation_of_a_real_discovery_finding_resolves(project, check):
    establish(project)
    blocked_on(project, check)
    result = propose_with(project, [finding(check, [
        {"kind": "discovery-finding", "id": "F-001"}])])
    assert result.exit_code == 0, result
    stored = record(project)["iterations"][0]["findings"][0]
    assert stored["citations"] == [{"kind": "discovery-finding", "id": "F-001"}]


def test_an_unknown_id_is_refused(project):
    establish(project)
    blocked_on(project, "compatibility")
    before = snapshot(project)
    result = propose_with(project, [finding("compatibility", [
        {"kind": "discovery-finding", "id": "F-999"}])])
    assert result.reason == "refinement_citation_unresolved"
    assert snapshot(project) == before


def test_a_stale_pinned_record_is_refused(project):
    establish(project)
    blocked_on(project, "compatibility")
    discovery = project.runtime / "discovery.json"
    discovery.write_text(discovery.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    result = propose_with(project, [finding("compatibility", [
        {"kind": "discovery-finding", "id": "F-001"}])])
    assert result.reason == "refinement_citation_unresolved"


@pytest.mark.parametrize("bad", [
    [{"kind": "made-up", "id": "F-001"}], [{"kind": "discovery-finding"}], [],
    ["F-001"], [{"kind": "discovery-finding", "id": "F-001", "extra": 1}]])
def test_a_malformed_citation_is_refused(project, bad):
    establish(project)
    blocked_on(project, "compatibility")
    assert propose_with(project, [finding("compatibility", bad)]).reason in (
        "refinement_input_invalid", "refinement_citation_unresolved")


def test_other_checks_carry_no_citations(project):
    establish(project)
    blocked_on(project, "scope")
    result = propose_with(project, [finding("scope", [
        {"kind": "discovery-finding", "id": "F-001"}])])
    assert result.reason == "refinement_input_invalid"
