"""D04 (SDLE-DEFECT-STABILIZATION-01) — execution identity is collision-safe.

Before this iteration an execution id was `<prefix>-<UTC second>`, and every
evidence file named after one (`governance-<id>.json`, `review-<id>-<n>.json`,
`discovery-<id>.json`, `migration-<id>.json`) was written with `write_atomic`,
which replaces whatever is there. Two executions inside the same second
therefore shared one evidence file — the second silently destroyed the first —
and shared one audit de-duplication marker, so the second assessment never
reached the ledger at all.

The clock is frozen by monkeypatching `now_iso`, never by sleeping or waiting
for a second boundary: a test whose outcome depends on wall-clock alignment
proves nothing either way.
"""

from __future__ import annotations

import json
import re

import pytest

from conftest import sdle
from test_units_artifact_review import audit_entries, review_for_gate

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3

FROZEN = "2026-09-10T12:00:00Z"
HIGH = {"signals": ["authentication_or_authorization"],
        "proposedLevel": "HIGH", "uncertainty": "LOW"}

# The readable prefix is kept; the suffix is the collision-resistant part.
NEW_FORMAT = re.compile(r"^[a-z0-9]{1,3}-\d{8}T\d{6}Z-[0-9a-f]{8}$")


def evidence_files(project, kind: str) -> list:
    return sorted((project.runtime / "evidence").glob(f"{kind}-*.json"))


def test_d04_the_identity_keeps_its_prefix_and_gains_a_suffix(project):
    result = project.record_governance()
    record = project.ok("governance", "show").data["record"]
    assert NEW_FORMAT.match(record["executionId"]), record["executionId"]
    assert record["executionId"] in result.data["evidence"]


def test_d04_two_assessments_in_one_second_keep_two_evidence_files(
        project, monkeypatch):
    monkeypatch.setattr(sdle, "now_iso", lambda: FROZEN)

    first = project.record_governance()
    first_body = (project.root / first.data["evidence"]).read_bytes()
    second = project.record_governance(risk=HIGH)

    assert first.data["evidence"] != second.data["evidence"]
    assert len(evidence_files(project, "governance")) == 2
    # The first record is intact — byte for byte, not merely present.
    assert (project.root / first.data["evidence"]).read_bytes() == first_body
    one = json.loads(first_body)
    two = json.loads((project.root / second.data["evidence"]).read_text("utf-8"))
    assert one["record"]["risk"]["signals"] == []
    assert two["record"]["risk"]["signals"] == HIGH["signals"]
    assert one["executionId"] != two["executionId"]


def test_d04_two_same_second_assessments_reach_the_ledger_separately(
        project, monkeypatch):
    """The de-duplication marker is the record's own execution id. With a
    shared id the second assessment was treated as already logged."""
    monkeypatch.setattr(sdle, "now_iso", lambda: FROZEN)

    # `init` is not a phase movement, so the first record reaches the ledger
    # at the first `advance`, and the second at the next movement after it.
    project.record_governance()
    project.ok("init", session="d04")
    first = project.ok("governance", "show").data["record"]["executionId"]
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution", session="d04")
    project.record_governance(risk=HIGH)
    second = project.ok("governance", "show").data["record"]["executionId"]
    review_for_gate(project, "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution", session="d04")

    recorded = [e for e in audit_entries(project)
                if "governance_recorded" in e]
    assert len(recorded) == 2, recorded
    assert any(f"(governance execution {first})" in e for e in recorded)
    assert any(f"(governance execution {second})" in e for e in recorded)
    assert project.ok("audit", "verify").data["chain_ok"] is True


def test_d04_two_reviews_in_one_second_keep_two_evidence_files(
        started, monkeypatch):
    monkeypatch.setattr(sdle, "now_iso", lambda: FROZEN)
    started.write_artifact("reviews/one.md")
    started.write_artifact("reviews/two.md")

    ids = []
    for name in ("reviews/one.md", "reviews/two.md"):
        ids.append(started.ok(
            "artifact", "review", "--path", name, "--type", "self-check",
            "--result", "PASS", "--actor-type", "agent",
            "--actor-name", "tester").data["evidenceId"])

    assert ids[0] != ids[1]
    bodies = [json.loads((started.root / i).read_text("utf-8")) for i in ids]
    assert [b["record"]["path"] for b in bodies] == ["reviews/one.md",
                                                     "reviews/two.md"]


@pytest.mark.parametrize("attempts_colliding", [1, 2])
def test_d04_a_forced_collision_retries_and_never_overwrites(
        project, monkeypatch, attempts_colliding):
    """An id whose evidence file already exists is abandoned for a fresh one
    — the existing file is never written."""
    monkeypatch.setattr(sdle, "now_iso", lambda: FROZEN)
    suffixes = iter(["deadbeef"] * attempts_colliding + ["cafef00d"])
    monkeypatch.setattr(sdle, "execution_suffix", lambda: next(suffixes))

    prefix = sdle.execution_prefix(sdle.dataclass_replace(
        sdle.resolve_paths(str(project.root), str(project.skill_root)),
        workitem=project.workitem))
    taken = (project.runtime / "evidence"
             / f"governance-{prefix}-20260910T120000Z-deadbeef.json")
    taken.parent.mkdir(parents=True, exist_ok=True)
    taken.write_bytes(b'{"sentinel": true}\n')

    result = project.record_governance()

    assert taken.read_bytes() == b'{"sentinel": true}\n'
    assert result.data["evidence"].endswith("-cafef00d.json"), result
    record = project.ok("governance", "show").data["record"]
    assert record["executionId"].endswith("-cafef00d")


def test_d04_an_unresolvable_collision_refuses_and_records_nothing(
        project, monkeypatch):
    monkeypatch.setattr(sdle, "now_iso", lambda: FROZEN)
    monkeypatch.setattr(sdle, "execution_suffix", lambda: "deadbeef")

    prefix = sdle.execution_prefix(sdle.dataclass_replace(
        sdle.resolve_paths(str(project.root), str(project.skill_root)),
        workitem=project.workitem))
    taken = (project.runtime / "evidence"
             / f"governance-{prefix}-20260910T120000Z-deadbeef.json")
    taken.parent.mkdir(parents=True, exist_ok=True)
    taken.write_bytes(b'{"sentinel": true}\n')

    document = project.root / "governance-input.json"
    document.write_text(json.dumps({
        "governanceInputVersion": "1",
        "quality": {n: {"result": "PASS", "finding": None}
                    for n in sdle.GOVERNANCE_POLICY_BUILTIN["quality_checks"]},
        "classification": {"type": "enhancement", "flow": "GREENFIELD"},
        "risk": {"signals": [], "proposedLevel": "LOW", "uncertainty": "LOW"},
    }), encoding="utf-8")
    result = project.run("governance", "assess", "--input",
                         "governance-input.json")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "execution_id_collision"
    assert taken.read_bytes() == b'{"sentinel": true}\n'
    assert not (project.runtime / "governance.json").exists(), (
        "a refused assessment must not leave a record behind")
    assert len(evidence_files(project, "governance")) == 1


def test_d04_a_historical_format_record_is_still_read_and_deduplicated(
        project):
    """Historical ids are never rewritten. A record carrying the pre-D04 form
    is shown, consumed at the first advance, and logged exactly once."""
    project.record_governance()
    governance = project.runtime / "governance.json"
    record = json.loads(governance.read_text("utf-8"))
    record["executionId"] = "usr-20260101T000000Z"
    governance.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    shown = project.ok("governance", "show").data["record"]
    assert shown["executionId"] == "usr-20260101T000000Z"

    project.ok("init", session="hist")
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution", session="hist")
    review_for_gate(project, "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution", session="hist")
    marker = "(governance execution usr-20260101T000000Z)"
    text = project.audit_file.read_text("utf-8")
    assert text.count(marker) == 1, text
