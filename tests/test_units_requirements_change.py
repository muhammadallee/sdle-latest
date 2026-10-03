"""What SDLE tells a person when bound requirements change under a WorkItem.

The engine reports facts - what changed, where the WorkItem is, what is approved, which
phases could be rolled back to, who else holds the document - and a change summary taken
from a copy of the text as it was assessed. It never recommends: the options and the
choice live in the conversation. These tests pin the facts and where they appear.
"""

from __future__ import annotations

import hashlib
import json

import pytest

from conftest import sdle
from test_integration_06_to_09 import at_gate_plan, review_for_gate

DOC = "requirements/todo-api.md"
ADDED = "Added rule: the service must log every write."


def edit(project, line=ADDED):
    target = project.root / DOC
    target.write_text(target.read_text(encoding="utf-8") + "\n" + line + "\n",
                      encoding="utf-8", newline="\n")


def stale_at_plan(project):
    at_gate_plan(project)
    review_for_gate(project, "gate_plan")
    edit(project)
    refused = project.run("gate", "approve", "--gate", "gate_plan")
    assert refused.reason == "governance_stale", refused
    return refused


def facts_of(refused):
    return refused.data["change_facts"]


# -- the snapshot --------------------------------------------------------------------------


def test_the_assessed_text_is_kept_in_the_evidence_and_not_in_the_record(project):
    project.record_governance()
    record_text = (project.runtime / "governance.json").read_text(encoding="utf-8")
    evidence = next(p for p in (project.runtime / "evidence").glob("governance-*.json")
                    if p.stat().st_size)
    snapshot = json.loads(evidence.read_text(encoding="utf-8"))["requirementsSnapshot"]
    original = (project.root / DOC).read_text(encoding="utf-8")
    assert snapshot[DOC]["text"] == original
    assert snapshot[DOC]["omitted"] is None
    assert original not in record_text, "the record stays small; the copy lives in evidence"


def test_a_document_over_the_size_limit_is_hashed_but_not_copied():
    snap = sdle.requirements_snapshot({"a.md": b"x" * (sdle.REQUIREMENTS_SNAPSHOT_MAX + 1)})
    assert snap["a.md"]["text"] is None and snap["a.md"]["omitted"] == "too_large"
    assert len(snap["a.md"]["sha256"]) == 64


# -- the summary (pure) --------------------------------------------------------------------


def summary(old, new, **kw):
    digest = hashlib.sha256(old.encode()).hexdigest()
    sources = [{"path": "a.md", "sha256": digest}]
    snapshot = {"a.md": {"sha256": digest, "text": old, "omitted": None}}
    return sdle.requirements_change_summary(
        snapshot, sources, {"a.md": new.encode()} if new is not None else {},
        kw.get("bound", ["a.md"]), kw.get("max_lines", 80))


def test_a_modified_document_carries_a_diff_of_what_changed():
    result = summary("one\ntwo\n", "one\ntwo\nthree\n")
    assert result["bindingChanged"] is False
    [entry] = result["changed"]
    assert entry["path"] == "a.md" and entry["change"] == "modified"
    assert "+three" in entry["diff"] and entry["diffTruncated"] is False


def test_an_unchanged_document_is_not_listed():
    assert summary("one\n", "one\n")["changed"] == []


def test_a_missing_document_is_reported_missing():
    [entry] = summary("one\n", None)["changed"]
    assert entry["change"] == "missing" and entry["diff"] is None


def test_a_long_diff_is_cut_and_says_so():
    result = summary("", "\n".join(f"line {n}" for n in range(500)) + "\n", max_lines=20)
    [entry] = result["changed"]
    assert entry["diffTruncated"] is True and len(entry["diff"].splitlines()) <= 21


def test_without_a_copy_of_the_old_text_there_is_no_diff_and_the_reason_is_given():
    sources = [{"path": "a.md", "sha256": "0" * 64}]
    result = sdle.requirements_change_summary({}, sources, {"a.md": b"new\n"}, ["a.md"], 80)
    [entry] = result["changed"]
    assert entry["change"] == "modified" and entry["diff"] is None
    assert entry["diffUnavailable"] == "no_copy_of_the_assessed_text"


def test_a_changed_binding_lists_what_was_added_and_dropped():
    sources = [{"path": "a.md", "sha256": "0" * 64}]
    snapshot = {"a.md": {"sha256": "0" * 64, "text": "x\n", "omitted": None}}
    result = sdle.requirements_change_summary(
        snapshot, sources, {"a.md": b"x\n", "b.md": b"y\n"}, ["b.md"], 80)
    assert result["bindingChanged"] is True
    assert {(e["path"], e["change"]) for e in result["changed"]} == {
        ("a.md", "unbound"), ("b.md", "added")}


# -- where the facts appear -------------------------------------------------------------------


def test_the_stale_refusal_carries_the_change_facts(project):
    facts = facts_of(stale_at_plan(project))
    [entry] = facts["changed"]
    assert entry["path"] == DOC and entry["change"] == "modified"
    assert f"+{ADDED}" in entry["diff"]
    assert facts["bindingChanged"] is False
    where = facts["workitem"]
    assert where["flow"] == "GREENFIELD" and where["currentPhase"] == "gate_plan"
    assert {"gate_constitution", "gate_spec"} <= set(where["approvedGates"])


def test_the_restart_candidates_are_the_passed_non_gate_phases_with_their_numbers(project):
    facts = facts_of(stale_at_plan(project))
    candidates = facts["workitem"]["restartCandidates"]
    paths = sdle.resolve_paths(str(project.root), str(project.skill_root))
    consts = sdle.load_constants(paths)
    flow = consts.flow("GREENFIELD")
    current = flow.index("gate_plan")
    assert candidates, "something can be rolled back to"
    for item in candidates:
        assert item["phase"] == flow.phase_at(item["number"])
        assert item["phase"] not in consts.phase_to_gate_key, "a gate is not restartable"
        assert item["number"] <= current
        assert item["label"]
    assert "spec_draft" in {c["phase"] for c in candidates}
    assert "implement" not in {c["phase"] for c in candidates}, "not reached yet"


def test_the_same_facts_appear_in_governance_show_and_only_when_stale(project):
    at_gate_plan(project)
    review_for_gate(project, "gate_plan")
    fresh = project.ok("governance", "show")
    assert fresh.data["fresh"] is True and fresh.data["change_facts"] is None
    edit(project)
    stale = project.ok("governance", "show")
    assert stale.data["fresh"] is False
    refused = project.run("gate", "approve", "--gate", "gate_plan")
    assert refused.reason == "governance_stale"
    assert refused.data["change_facts"] == stale.data["change_facts"], "one helper, two surfaces"


def test_a_binding_change_is_reported_as_such(project):
    at_gate_plan(project)
    review_for_gate(project, "gate_plan")
    (project.root / "requirements" / "extra.md").write_text("# Extra\n", encoding="utf-8")
    project.ok("requirements", "bind", "--source", DOC, "--source", "requirements/extra.md",
               "--primary", DOC)
    refused = project.run("gate", "approve", "--gate", "gate_plan")
    assert refused.reason == "governance_stale"
    facts = facts_of(refused)
    assert facts["bindingChanged"] is True
    assert ("requirements/extra.md", "added") in {(e["path"], e["change"]) for e in facts["changed"]}


def test_the_facts_say_who_else_holds_a_changed_document(project):
    at_gate_plan(project)
    review_for_gate(project, "gate_plan")
    project.ok("workitem", "create", "--name", "Other")
    project.pin = True
    project.as_workitem("other").ok("requirements", "bind", "--source", DOC)
    edit(project)
    refused = project.run("gate", "approve", "--gate", "gate_plan")
    assert refused.reason == "governance_stale", refused
    held = facts_of(refused)["alsoHeldBy"]
    assert held == {DOC: {"started": [], "notStarted": ["other"]}}


def test_an_assessment_that_predates_the_copy_still_reports_what_it_can(project):
    at_gate_plan(project)
    review_for_gate(project, "gate_plan")
    for path in (project.runtime / "evidence").glob("governance-*.json"):
        if path.stat().st_size:
            doc = json.loads(path.read_text(encoding="utf-8"))
            doc.pop("requirementsSnapshot", None)
            path.write_text(json.dumps(doc), encoding="utf-8")
    edit(project)
    refused = project.run("gate", "approve", "--gate", "gate_plan")
    [entry] = facts_of(refused)["changed"]
    assert entry["diff"] is None and entry["diffUnavailable"] == "no_copy_of_the_assessed_text"


def test_before_init_the_facts_have_no_workitem_position(project):
    project.record_governance()
    edit(project)
    shown = project.ok("governance", "show")
    facts = shown.data["change_facts"]
    assert facts["workitem"] is None and facts["changed"]


def test_the_architecture_placement_is_reported_when_it_was_read_from_older_text(project):
    at_gate_plan(project)
    review_for_gate(project, "gate_plan")
    edit(project)
    facts = facts_of(project.run("gate", "approve", "--gate", "gate_plan"))
    assert facts["architecturePlacement"] in ("none", "current", "reasoned_from_older_requirements")


# -- the rollback approach is recorded --------------------------------------------------------


@pytest.mark.parametrize("approach", ["rebuild", "update"])
def test_the_chosen_approach_is_written_to_the_audit_entry(project, approach):
    at_gate_plan(project)
    project.ok("restart", "--to", "8", "--approach", approach)
    project.ok("restart", "--to", "8", "--confirm", "--approach", approach)
    audit = (project.runtime / "audit.md").read_text(encoding="utf-8")
    assert f"Approach: {approach}" in audit


def test_a_restart_without_an_approach_is_unchanged(project):
    at_gate_plan(project)
    project.ok("restart", "--to", "8")
    project.ok("restart", "--to", "8", "--confirm")
    audit = (project.runtime / "audit.md").read_text(encoding="utf-8")
    assert "Approach:" not in audit


def test_an_unknown_approach_is_a_usage_error(project):
    at_gate_plan(project)
    result = project.run("restart", "--to", "8", "--approach", "improvise")
    assert result.exit_code == 2
    assert project.state()["pending_confirm_action"] is None
