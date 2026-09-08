"""Brownfield discovery as a governed record (T08, contract §14).

§14 asks for a discovery output covering fourteen categories in which every
finding is classified, and states the rule the classification serves: *never
present inference as observation*.

Discovery is judgement work the deterministic core cannot perform, so this
file pins the **split** rather than pretending there is none:

* what the engine guarantees — nothing unclassified, no fourth classification,
  an observation cites a path that exists here, an inference names what it
  rests on and none of that is unknown, an unknown carries no evidence, no
  declared category silently dropped;
* what it does not — whether an observation is *true of* the file it cites,
  whether an inference follows, whether the findings are complete.

The second list is asserted too: `discovery schema` publishes it, so the
honesty of the split is itself testable.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import REPO_ROOT, Project, sdle

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3

OBSERVED, INFERRED, UNKNOWN = sdle.DISCOVERY_CLASSIFICATIONS

# The golden literal: §14's fourteen bullets in §14's order, spelled out here
# as an independent second witness a reviewer can read without opening the
# engine — the device `GREENFIELD_GOLDEN` already uses for flow membership. If
# this list and `DISCOVERY_CATEGORIES` disagree, one of them was edited alone.
SECTION_14_CATEGORIES = [
    "repository_inventory",
    "modules_components",
    "dependencies",
    "architecture",
    "significant_patterns",
    "conventions",
    "apis",
    "persistence_data_architecture",
    "test_practices",
    "runtime_deployment",
    "security_patterns",
    "adrs",
    "constraints_non_negotiables",
    "risks_debt",
]

INPUT_NAME = "discovery-input.json"


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def brownfield(project: Project) -> Project:
    """A WorkItem bound to BROWNFIELD_DISCOVERY, standing at `discovery`."""
    project.record_governance(
        classification={"type": "enhancement", "flow": "BROWNFIELD_DISCOVERY"})
    project.ok("init", session="disc")
    assert project.state()["current_phase"] == "discovery"
    return project


def finding(index: int, category: str, **over) -> dict:
    entry = {
        "id": f"F-{index:03d}",
        "category": category,
        "classification": UNKNOWN,
        "statement": f"Nothing is recorded about {category}.",
    }
    entry.update(over)
    return entry


def document(**over) -> dict:
    """A minimal accepted document: one honest unknown per category."""
    doc = {
        "discoveryInputVersion": "1",
        "findings": [finding(i, c)
                     for i, c in enumerate(sdle.DISCOVERY_CATEGORIES, start=1)],
    }
    doc.update(over)
    return doc


def with_finding(extra: dict, **over) -> dict:
    """The accepted document plus one more finding."""
    doc = document(**over)
    doc["findings"] = doc["findings"] + [extra]
    return doc


def assess(project: Project, doc, name: str = INPUT_NAME):
    target = project.root / name
    if isinstance(doc, str):
        target.write_text(doc, encoding="utf-8", newline="\n")
    else:
        target.write_text(json.dumps(doc, indent=2), encoding="utf-8",
                          newline="\n")
    try:
        return project.run("discovery", "assess", "--input", name)
    finally:
        target.unlink(missing_ok=True)


def record_of(project: Project) -> dict:
    return json.loads(
        (project.runtime / "discovery.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# N1/N2 — the vocabulary is closed, published, and not vacuous
# --------------------------------------------------------------------------


def test_discovery_schema_needs_no_workitem_and_writes_nothing(bare_project):
    """N1. It is how the prompt layer learns the vocabulary, so it has to be
    answerable before a WorkItem — and before a workflow — exists."""
    before = sorted(p.relative_to(bare_project.root).as_posix()
                    for p in bare_project.root.rglob("*"))

    result = bare_project.run("discovery", "schema")

    assert result.exit_code == EXIT_OK, result
    assert result.data["categories"] == SECTION_14_CATEGORIES
    assert result.data["categories"] == list(sdle.DISCOVERY_CATEGORIES)
    assert len(result.data["categories"]) == 14

    after = sorted(p.relative_to(bare_project.root).as_posix()
                   for p in bare_project.root.rglob("*"))
    assert after == before


def test_the_schema_publishes_both_halves_of_the_integrity_split(bare_project):
    """N1. The honesty is the deliverable, so it is machine-readable.

    A checker that implied more than it checks would be worse than no checker,
    so `discovery schema` states what is guaranteed *and* what is only
    claimed. Both lists must be non-empty and disjoint.
    """
    data = bare_project.ok("discovery", "schema").data
    assert data["enforced"] and data["not_enforced"]
    assert not set(data["enforced"]) & set(data["not_enforced"])
    assert any("true of" in claim for claim in data["not_enforced"])
    assert any("complete" in claim for claim in data["not_enforced"])
    assert set(data["rules"]) == set(sdle.DISCOVERY_RULES)


def test_the_vocabularies_are_closed_and_identifier_shaped(bare_project):
    """N2. Guards N3 and N14 against passing vacuously."""
    data = bare_project.ok("discovery", "schema").data

    categories = data["categories"]
    assert len(categories) == 14
    assert len(set(categories)) == 14
    assert all(c.islower() and c.replace("_", "").isalnum() for c in categories)

    classifications = data["classifications"]
    assert len(classifications) == 3
    assert classifications == list(sdle.DISCOVERY_CLASSIFICATIONS)
    assert all(c.isupper() and c.isalpha() for c in classifications)


# --------------------------------------------------------------------------
# N3 — R-a..R-j, one refusal each
# --------------------------------------------------------------------------


BAD_ENVELOPES = {
    "not_json": "{not json",
    "not_an_object": '"a string"',
    "unknown_top_level_key": json.dumps(document(surprise=1)),
    "unsupported_version": json.dumps(document(discoveryInputVersion="9")),
}


@pytest.mark.parametrize("case", sorted(BAD_ENVELOPES))
def test_r_a_the_envelope_is_fail_closed(project, case):
    brownfield(project)
    result = assess(project, BAD_ENVELOPES[case])
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "discovery_input_malformed"
    assert result.data["rule"] == "R-a"


def test_r_a_a_missing_top_level_key_is_refused(project):
    brownfield(project)
    doc = document()
    del doc["findings"]
    result = assess(project, doc)
    assert result.exit_code == EXIT_REFUSED
    assert result.data["rule"] == "R-a"
    assert result.data["missing_keys"] == ["findings"]


def test_r_a_an_absent_input_file_is_refused(project):
    brownfield(project)
    result = project.run("discovery", "assess", "--input", "no-such.json")
    assert result.exit_code == EXIT_REFUSED
    assert result.reason == "discovery_input_malformed"
    assert result.data["rule"] == "R-a"


R_B_CASES = {
    "empty_list": document(findings=[]),
    "not_a_list": document(findings="everything is fine"),
    "not_objects": document(findings=[1, 2]),
    "unknown_finding_key": with_finding(
        finding(99, "adrs", confidence="high")),
    "non_list_evidence": with_finding(
        finding(99, "adrs", evidence="README.md")),
    "non_list_basis": with_finding(finding(99, "adrs", basis="F-001")),
}


@pytest.mark.parametrize("case", sorted(R_B_CASES))
def test_r_b_findings_must_be_a_list_of_declared_objects(project, case):
    brownfield(project)
    result = assess(project, R_B_CASES[case])
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "discovery_input_malformed"
    assert result.data["rule"] == "R-b"


R_C_CASES = {
    "duplicate_id": with_finding(finding(1, "adrs")),
    "empty_id": with_finding(finding(99, "adrs", id="   ")),
    "non_string_id": with_finding(finding(99, "adrs", id=7)),
}


@pytest.mark.parametrize("case", sorted(R_C_CASES))
def test_r_c_every_finding_needs_a_unique_string_id(project, case):
    brownfield(project)
    result = assess(project, R_C_CASES[case])
    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-c"


def test_r_d_an_invented_category_is_refused(project):
    brownfield(project)
    result = assess(project, with_finding(finding(99, "vibes")))
    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-d"
    assert result.data["finding"] == "F-099"
    assert result.data["value"] == "vibes"


def test_r_f_a_finding_with_no_statement_is_refused(project):
    brownfield(project)
    blank = finding(99, "adrs", statement="   ")
    assert assess(project, with_finding(blank)).data["rule"] == "R-f"
    missing = finding(99, "adrs")
    del missing["statement"]
    result = assess(project, with_finding(missing))
    assert result.exit_code == EXIT_REFUSED
    assert result.data["rule"] == "R-f"
    assert result.data["finding"] == "F-099"


# --------------------------------------------------------------------------
# N4 — the integrity property, isolated
# --------------------------------------------------------------------------


def test_n4_an_unclassified_finding_is_refused(project):
    """R-e. "Every finding carries a classification" is the whole §14 rule."""
    brownfield(project)
    unclassified = finding(99, "adrs")
    del unclassified["classification"]

    result = assess(project, with_finding(unclassified))

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "discovery_input_malformed"
    assert result.data["rule"] == "R-e"
    assert result.data["finding"] == "F-099"


def test_n4_a_fourth_classification_cannot_be_invented(project):
    """R-e. The three are closed; `PROBABLY` is the plausible-looking one."""
    brownfield(project)
    result = assess(
        project, with_finding(finding(99, "adrs", classification="PROBABLY")))

    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-e"
    assert result.data["finding"] == "F-099"
    assert result.data["value"] == "PROBABLY"


# --------------------------------------------------------------------------
# N5 — an observation must point at something that exists
# --------------------------------------------------------------------------


def test_n5_an_observation_citing_a_missing_path_is_refused(project):
    brownfield(project)
    result = assess(project, with_finding(finding(
        99, "adrs", classification=OBSERVED, evidence=["docs/nowhere.md"])))

    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-g"
    assert result.data["finding"] == "F-099"
    assert result.data["value"] == "docs/nowhere.md"


def test_n5_the_same_observation_with_a_real_path_is_accepted(project):
    """The one half of "never present inference as observation" the engine
    actually checks, contrasted against the refusal above."""
    brownfield(project)
    project.write_artifact("docs/somewhere.md")

    result = assess(project, with_finding(finding(
        99, "adrs", classification=OBSERVED, evidence=["docs/somewhere.md"])))

    assert result.exit_code == EXIT_OK, result
    recorded = {f["id"]: f for f in record_of(project)["findings"]}
    assert recorded["F-099"]["classification"] == OBSERVED
    assert recorded["F-099"]["evidence"] == ["docs/somewhere.md"]


def test_n5_an_observation_with_no_evidence_at_all_is_refused(project):
    brownfield(project)
    result = assess(project, with_finding(
        finding(99, "adrs", classification=OBSERVED)))
    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-g"


ESCAPES = ["../outside.md", "docs/../../outside.md"]


@pytest.mark.parametrize("path", ESCAPES)
def test_n5_evidence_may_not_escape_the_repository(project, path):
    brownfield(project)
    (project.root.parent / "outside.md").write_text("x\n", encoding="utf-8")

    result = assess(project, with_finding(finding(
        99, "adrs", classification=OBSERVED, evidence=[path])))

    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-g"
    assert "escapes" in result.data["detail"]


def test_n5_an_absolute_evidence_path_is_refused(project):
    brownfield(project)
    inside = project.write_artifact("docs/inside.md")
    result = assess(project, with_finding(finding(
        99, "adrs", classification=OBSERVED, evidence=[str(inside)])))
    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-g"


# --------------------------------------------------------------------------
# N6/N7 — an inference names what it rests on; an unknown claims nothing
# --------------------------------------------------------------------------


def test_n6_an_inference_resting_on_an_unknown_is_refused(project):
    """The document's own findings are all unknown, so F-001 is one."""
    brownfield(project)
    result = assess(project, with_finding(finding(
        99, "adrs", classification=INFERRED, basis=["F-001"])))

    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-h"
    assert result.data["finding"] == "F-099"
    assert result.data["value"] == "F-001"


def test_n6_an_inference_with_no_basis_is_refused(project):
    brownfield(project)
    result = assess(project, with_finding(
        finding(99, "adrs", classification=INFERRED)))
    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-h"


def test_n6_an_inference_resting_on_an_undeclared_finding_is_refused(project):
    brownfield(project)
    result = assess(project, with_finding(finding(
        99, "adrs", classification=INFERRED, basis=["F-404"])))
    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-h"
    assert result.data["value"] == "F-404"


def test_n6_an_inference_resting_on_an_observation_is_accepted(project):
    """The positive case, so N6 is not passing because inference is banned."""
    brownfield(project)
    project.write_artifact("docs/adr-001.md")
    doc = document()
    doc["findings"] = doc["findings"] + [
        finding(98, "adrs", classification=OBSERVED,
                evidence=["docs/adr-001.md"]),
        finding(99, "adrs", classification=INFERRED, basis=["F-098"]),
    ]

    result = assess(project, doc)

    assert result.exit_code == EXIT_OK, result
    assert record_of(project)["counts"] == {OBSERVED: 1, INFERRED: 1,
                                            UNKNOWN: 14}


def test_n7_an_unknown_carrying_evidence_is_refused(project):
    """A finding that cites evidence is one of the other two."""
    brownfield(project)
    project.write_artifact("docs/real.md")
    result = assess(project, with_finding(finding(
        99, "adrs", classification=UNKNOWN, evidence=["docs/real.md"])))

    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["rule"] == "R-i"
    assert result.data["finding"] == "F-099"


# --------------------------------------------------------------------------
# N8 — no category may be silently dropped, and unknown is always available
# --------------------------------------------------------------------------


@pytest.mark.parametrize("dropped", ["repository_inventory", "risks_debt"])
def test_n8_a_dropped_category_is_refused_and_named(project, dropped):
    brownfield(project)
    doc = document()
    doc["findings"] = [f for f in doc["findings"] if f["category"] != dropped]

    result = assess(project, doc)

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "discovery_incomplete"
    assert result.data["missing"] == [dropped]
    assert dropped in result.envelope["message"]


def test_n8_every_category_unknown_is_accepted(project):
    """§14 is satisfiable without lying: unknown is the honest answer."""
    brownfield(project)

    result = assess(project, document())

    assert result.exit_code == EXIT_OK, result
    record = record_of(project)
    assert record["result"] == "PASS"
    assert record["counts"] == {OBSERVED: 0, INFERRED: 0, UNKNOWN: 14}
    assert sorted(record["categories"]) == sorted(SECTION_14_CATEGORIES)
    assert all(ids for ids in record["categories"].values())


# --------------------------------------------------------------------------
# N9/N10 — what a refusal writes, and what an acceptance writes
# --------------------------------------------------------------------------


def test_n9_a_refused_assess_writes_absolutely_nothing(project):
    """B1/NB-6's property, extended to the phase's new command."""
    brownfield(project)
    audit_before = project.audit_file.read_bytes()
    state_before = project.state_file.read_bytes()
    evidence_before = sorted(p.name for p in (project.runtime / "evidence")
                             .glob("*")) if (project.runtime / "evidence").is_dir() else []

    result = assess(project, with_finding(
        finding(99, "adrs", classification="PROBABLY")))

    assert result.exit_code == EXIT_REFUSED, result
    assert not (project.runtime / "discovery.json").exists()
    assert project.audit_file.read_bytes() == audit_before
    assert project.state_file.read_bytes() == state_before
    after = sorted(p.name for p in (project.runtime / "evidence").glob("*")) \
        if (project.runtime / "evidence").is_dir() else []
    assert after == evidence_before


def test_n10_an_accepted_assess_records_evidence_and_one_audit_entry(project):
    brownfield(project)
    before = project.audit_file.read_text(encoding="utf-8").count(
        sdle.DISCOVERY_AUDIT_EVENT)

    result = assess(project, document())

    assert result.exit_code == EXIT_OK, result
    assert (project.runtime / "discovery.json").is_file()

    evidence = sorted((project.runtime / "evidence").glob("discovery-*.json"))
    assert len(evidence) == 1
    payload = json.loads(evidence[0].read_text(encoding="utf-8"))
    assert payload["kind"] == "discovery"
    assert payload["input"]["document"]["discoveryInputVersion"] == "1"

    text = project.audit_file.read_text(encoding="utf-8")
    assert text.count(sdle.DISCOVERY_AUDIT_EVENT) == before + 1

    verify = project.ok("audit", "verify")
    assert verify.data["chain_ok"] is True
    assert verify.data["matches"] is True


def test_the_recorded_findings_are_readable_back(project):
    brownfield(project)
    assess(project, document())
    shown = project.ok("discovery", "show")
    assert shown.data["record"]["workitem"] == project.workitem
    assert shown.data["record"]["result"] == "PASS"


def test_a_corrupt_discovery_record_is_an_integrity_failure(project):
    """Fail-closed, like `read_governance_record`: a malformed record is not
    an absence, or it would be silently overwritten."""
    brownfield(project)
    assess(project, document())
    (project.runtime / "discovery.json").write_text("{not json",
                                                    encoding="utf-8")

    result = project.run("discovery", "show")
    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "discovery_record_invalid"


# --------------------------------------------------------------------------
# N11/N12 — leaving the phase needs a record, on every mover
# --------------------------------------------------------------------------


def test_n11_advance_out_of_discovery_without_a_record_refuses(project):
    brownfield(project)
    result = project.run("advance", "--to", "constitution_draft")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "discovery_missing"
    assert result.data["phase"] == "discovery"


def test_n11_skip_out_of_discovery_without_a_record_refuses(project):
    """The fail-open case: `skip` must not walk past discovery either."""
    brownfield(project)
    state = project.state()
    state["status"] = "failed"
    project.write_state(state)

    pending = project.ok("skip")
    assert pending.data["pending"] is True

    result = project.run("skip", "--confirm")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "discovery_missing"


@pytest.mark.parametrize("mover", ["advance", "skip"])
def test_n12_the_discovery_refusal_leaves_the_ledger_byte_identical(project,
                                                                   mover):
    """`discovery_precondition` is a pure reader, and this is what that means."""
    brownfield(project)
    if mover == "skip":
        state = project.state()
        state["status"] = "failed"
        project.write_state(state)
        project.ok("skip")

    before = project.audit_file.read_bytes()
    result = (project.run("advance", "--to", "constitution_draft")
              if mover == "advance" else project.run("skip", "--confirm"))

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "discovery_missing"
    assert project.audit_file.read_bytes() == before


def test_the_phase_can_be_left_once_the_record_exists(project):
    brownfield(project)
    project.record_discovery()
    project.ok("advance", "--to", "constitution_draft")
    assert project.state()["current_phase"] == "constitution_draft"


def test_a_record_naming_another_workitem_does_not_authorise_the_advance(
        project):
    """Copying someone else's discovery in is not discovery.

    §14's exit criterion is about inheriting discovery *deliberately*, through
    the repository baseline — never by a file appearing in a runtime.
    """
    brownfield(project)
    project.record_discovery()
    record = record_of(project)
    record["workitem"] = "someone-else"
    (project.runtime / "discovery.json").write_text(
        json.dumps(record, indent=2), encoding="utf-8", newline="\n")

    result = project.run("advance", "--to", "constitution_draft")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "discovery_missing"


def test_the_other_flows_never_meet_the_discovery_precondition(started):
    """GREENFIELD has no `discovery` phase, so nothing new refuses there."""
    started.ok("advance", "--to", "gate_constitution", "--status", "pending")
    assert started.state()["current_phase"] == "gate_constitution"


# --------------------------------------------------------------------------
# N13 — the derived leak detector inherits both directions
# --------------------------------------------------------------------------


def test_n13_the_discovery_record_is_a_runtime_member():
    bound = sdle.Paths(project_root=Path("/probe-root"),
                       skill_root=Path("/probe-skill"), workitem="probe")
    assert "discovery.json" in sdle.workitem_runtime_member_names(bound)


def test_n13_discovery_json_under_the_repository_boundary_is_an_error(started):
    started.ok("config", "init")
    planted = started.root / ".sdle" / "discovery.json"
    planted.write_text("planted\n", encoding="utf-8")

    result = started.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    checks = [f["check"] for f in result.data["findings"]]
    assert "lifecycle_state_in_repository_config" in checks


def test_n13_baseline_json_under_a_workitem_is_still_an_error(started):
    planted = started.runtime / "baseline.json"
    planted.write_text("planted\n", encoding="utf-8")

    result = started.run("validate")

    assert result.exit_code == EXIT_INTEGRITY, result
    checks = [f["check"] for f in result.data["findings"]]
    assert "repository_config_in_workitem" in checks


# --------------------------------------------------------------------------
# N14 — one home per fact (invariant 7, T05 NB-3's drift surface)
# --------------------------------------------------------------------------


def searchable_files() -> list[Path]:
    """T06's `_searchable_files()` set, reused verbatim.

    `docs/transition/` is the migration control plane rather than the product,
    and this file legitimately quotes §14's own vocabulary.
    """
    roots = [REPO_ROOT / "README.md", REPO_ROOT / "CLAUDE.md",
             REPO_ROOT / "docs" / "SDLE-Reference-Guide.md"]
    files = [p for p in roots if p.is_file()]
    for directory in (REPO_ROOT / ".claude" / "skills",
                      REPO_ROOT / ".claude" / "commands",
                      REPO_ROOT / ".claude" / "hooks",
                      REPO_ROOT / ".sdle",
                      REPO_ROOT / "docs" / "architecture"):
        if directory.is_dir():
            files.extend(p for p in sorted(directory.rglob("*")) if p.is_file())
    # T10 (X3): product subagent prompts are part of the shipped prompt layer,
    # so a restatement in one of them is exactly the drift this search exists
    # to catch. Four `sdle-transition-*` files used to be excluded here: they
    # were the migration control plane (contract §1.4), not the product, and
    # `sdle-transition-planner.md` legitimately used the transition
    # contract's own evidence vocabulary — OBSERVED / INFERRED / UNKNOWN —
    # which happens to be spelled exactly like §14's classifications. The
    # post-migration cleanup deleted those four files, so the carve-out went
    # with them and every agent prompt on disk is scanned. `docs/transition/`
    # stays outside the roots above for a different and still-live reason,
    # given in the docstring.
    agents = REPO_ROOT / ".claude" / "agents"
    if agents.is_dir():
        files.extend(path for path in sorted(agents.glob("sdle-*.md"))
                     if path.is_file())
    return files


def discovery_identifiers() -> set[str]:
    """The identifier-shaped discovery vocabulary — the real drift surface.

    Deliberately *not* every category id: `dependencies`, `architecture`,
    `conventions`, `apis` and `adrs` are ordinary words that §14 itself and
    several already-searched files use as prose about something else — the
    README, `CLAUDE.md`, the Reference Guide, the security-review module and
    ADR-005 among them — so matching them would flag documents that restate
    nothing. What a *restatement* of the vocabulary must contain is the
    machine-readable part: the underscored category ids, the three
    classification tokens, and the input envelope key.
    """
    return ({c for c in sdle.DISCOVERY_CATEGORIES if "_" in c}
            | set(sdle.DISCOVERY_CLASSIFICATIONS)
            | {"discoveryInputVersion"})


def test_the_discovery_needles_are_not_english_words():
    """Guards N14 against passing vacuously or matching prose."""
    needles = discovery_identifiers()
    assert len(needles) >= 12
    for needle in needles:
        assert needle.isupper() or "_" in needle or needle[0].islower()
        assert " " not in needle


def test_n14_no_discovery_vocabulary_is_restated_outside_sdle_py():
    """Invariant 7, executed as a real content search rather than narrated.

    The vocabulary reaches the prompt layer through `discovery schema` and
    nowhere else, so T05's NB-3 drift surface is not reproduced.
    """
    needles = discovery_identifiers()
    offenders: dict[str, list[str]] = {}
    for path in searchable_files():
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = sorted(n for n in needles if n in body)
        if hits:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = hits
    assert offenders == {}, \
        f"discovery vocabulary restated outside sdle.py: {offenders}"


def test_the_prompt_layer_points_at_the_command_instead(project):
    """The other half of N14: the phase block must send Claude to the schema."""
    block = (REPO_ROOT / ".claude" / "skills" / "sdle" / "modules"
             / "phase-execution.md").read_text(encoding="utf-8")
    start = block.index("**Phase `discovery`")
    end = block.index("**Phase ", start + 10)
    body = block[start:end]

    assert "discovery schema" in body
    assert "discovery assess --input" in body
    assert "Never present an inference as an observation" in body
    # It runs before any specification exists, so no feature directory does.
    assert "feature bind" not in body
    assert "featureDirectory" not in body


def test_the_discovery_block_header_carries_no_ordinal():
    """N30's source-side half: `discovery` has no GREENFIELD position."""
    text = (REPO_ROOT / ".claude" / "skills" / "sdle" / "modules"
            / "phase-execution.md").read_text(encoding="utf-8")
    assert "**Phase `discovery` (BROWNFIELD_DISCOVERY only" in text
