"""D06 (SDLE-DEFECT-STABILIZATION-01) — the dry-run transcripts are pinned by
their claims, and every claim is checked against the engine.

Transcripts 01-09 used to be byte-pinned against historical commits. A byte
pin says a file did not change; it cannot say the file is *right*, and by this
iteration they were not: Spec Kit paths under `.specify/specs/`, uppercase
fingerprints the engine never prints, no WorkItem or governance step, and a
Gate 7 with no test requirement. The byte pins were released deliberately and
replaced by what this module asserts, for all twenty-two transcripts alike:

* **structure** — the ten parts the stabilization plan requires (scenario id,
  flow, defect ids, runtime, starting conditions, setup, transcript,
  artifacts/state/audit, negative cases, cleanup, executable coverage) and
  the SIMULATED / PASS-FAIL-BLOCKED-NOT RUN labels;
* **numbers** — every `SDLE_STATE` comment, every status header and every
  `Gate k/T: <label>` prompt is recomputed from the transcript's bound flow
  (`FlowSpec.progress_for`, `gate_number`, `gate_total`, `Constants.label`),
  never from a GREENFIELD habit;
* **refusals** — every `Refused: <reason>` names a reason the engine raises;
* **links** — every test node a transcript cites exists;
* **no regression** — none of the old `.workflow/` literals the T11
  convergence replaced comes back (`DRY_RUN_SUBSTITUTIONS` keeps that list).

A transcript that switches WorkItem mid-way (11: brownfield, then iterative)
declares it with an HTML comment, `<!-- dry-run-flow: FLOW -->`, which the
reader never sees and this checker honours from that line on.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from conftest import DRY_RUN_SUBSTITUTIONS, REPO_ROOT, sdle

DRY_RUNS = REPO_ROOT / "docs" / "dry-runs"
TRANSCRIPTS = sorted(p for p in DRY_RUNS.glob("*.md") if p.name[:2].isdigit())
SCENARIO_COUNT = 22

CONSTS = sdle.load_constants(sdle.resolve_paths(
    str(REPO_ROOT), str(REPO_ROOT / ".claude" / "skills" / "sdle")))

REQUIRED_ROWS = ("Scenario ID", "Flow", "Purpose", "Defect IDs", "Runtime",
                 "Starting conditions")
REQUIRED_SECTIONS = ("## Setup", "## Transcript",
                     "## Artifacts, state and audit", "## Negative cases",
                     "## Cleanup", "## Executable coverage")
RESULT_LABELS = ("**PASS**", "**FAIL**", "**BLOCKED**", "**NOT RUN**")

STATE_COMMENT = re.compile(
    r"<!-- SDLE_STATE phase=(\w+) status=\w+ progress=(\d+)/(\d+) -->")
STATUS_HEADER = re.compile(r"📋 SDLE Status: Phase (\d+)/(\d+) — (.+?) \[")
GATE_PROMPT = re.compile(r"Gate (\d+)/(\d+): ([A-Z][A-Za-z ]+? Approval)")
FLOW_SWITCH = re.compile(r"<!-- dry-run-flow: (\w+) -->")
PRE_INIT_MARKER = "<!-- dry-run-pre-init -->"
REFUSED = re.compile(r"Refused: `?([a-z_]+)`?")
NODE = re.compile(r"`(tests/[\w/]+\.py)(?:::([\w\[\]\-. ]+))?`")


def test_there_are_twenty_two_transcripts_and_they_are_numbered_densely():
    assert [p.name[:2] for p in TRANSCRIPTS] == [
        f"{n:02d}" for n in range(1, SCENARIO_COUNT + 1)], [
            p.name for p in TRANSCRIPTS]


def metadata(text: str) -> dict[str, str]:
    rows = {}
    for match in re.finditer(r"^\| \*\*(.+?)\*\* \| (.+?) \|$", text, re.M):
        rows[match.group(1)] = match.group(2)
    return rows


def bound_flow(text: str) -> str:
    flows = re.findall(r"`([A-Z_]+)`", metadata(text).get("Flow", ""))
    assert flows and flows[0] in CONSTS.flows, flows
    return flows[0]


@pytest.mark.parametrize("path", TRANSCRIPTS, ids=lambda p: p.name)
def test_every_transcript_carries_the_required_parts(path):
    text = path.read_text(encoding="utf-8")
    rows = metadata(text)
    for row in REQUIRED_ROWS:
        assert row in rows, f"{path.name}: no '{row}' row"
    assert rows["Scenario ID"] == f"DR-{path.name[:2]}", rows["Scenario ID"]
    assert re.fullmatch(r"(—|D0[1-6](, D0[1-6])*)", rows["Defect IDs"]), (
        rows["Defect IDs"])
    for heading in REQUIRED_SECTIONS:
        assert re.search(rf"^{re.escape(heading)}\b", text, re.M), (
            f"{path.name}: missing section {heading!r}")
    assert "**SIMULATED**" in text, path.name
    assert any(label in text for label in RESULT_LABELS), path.name


def _label_to_phase(flow) -> dict[str, str]:
    return {CONSTS.label(phase, flow): phase for phase in flow.phases}


@pytest.mark.parametrize("path", TRANSCRIPTS, ids=lambda p: p.name)
def test_every_progress_fraction_and_gate_number_is_the_engines(path):
    """Recomputed from the bound flow, line by line."""
    text = path.read_text(encoding="utf-8")
    flow = CONSTS.flow(bound_flow(text))
    checked = 0
    for number, line in enumerate(text.splitlines(), start=1):
        switch = FLOW_SWITCH.search(line)
        if switch:
            flow = CONSTS.flow(switch.group(1))
            continue
        where = f"{path.name}:{number}"

        for phase, done, total in STATE_COMMENT.findall(line):
            assert phase in flow.phases, (where, phase, flow.name)
            assert f"{done}/{total}" == flow.progress_for(phase), (
                where, phase, flow.name, flow.progress_for(phase))
            checked += 1

        for done, total, label in STATUS_HEADER.findall(line):
            labels = _label_to_phase(flow)
            assert label in labels, (where, label, flow.name)
            assert f"{done}/{total}" == flow.progress_for(labels[label]), (
                where, label, flow.name, flow.progress_for(labels[label]))
            checked += 1

        for number_shown, total, label in GATE_PROMPT.findall(line):
            assert int(total) == flow.gate_total, (where, flow.name)
            expected = f"Gate {number_shown}: {label}"
            gates = {CONSTS.label(phase, flow): phase
                     for phase in flow.gate_phases}
            assert expected in gates, (where, expected, flow.name,
                                       sorted(gates))
            checked += 1
    if PRE_INIT_MARKER in text:
        # Requirements refinement happens before there is a workflow, so such a
        # transcript has no position to show. It must say so, and every line
        # that does show one is still checked above.
        return
    assert checked, f"{path.name} shows no progress or gate number at all"


PROSE_FRACTION = re.compile(r"\((\d{1,2})/(\d{1,2})\)")
PROSE_GATE_TOTAL = re.compile(r"\b[Aa]ll (\d{1,2}) gates\b")
PROSE_GATE_OF = re.compile(r"\bGate (\d{1,2}) of (\d{1,2})\b")


@pytest.mark.parametrize("path", TRANSCRIPTS, ids=lambda p: p.name)
def test_the_prose_ordinals_agree_with_the_engine_too(path):
    """The gap ADR-013 found the hard way.

    The checks above parse three *shapes* — the `SDLE_STATE` comment, the
    status header and the `Gate k/T:` prompt — so a transcript could be
    recomputed into perfect agreement with the engine in its machine-readable
    lines while its prose still said "Gate 2 approved" about the same
    approval, and "All 8 gates passed" about nine. Every one of those was
    wrong in this repository at once, in the document set CLAUDE.md calls the
    behavioural specification.

    So the prose forms are checked too: a parenthesised `(k/T)` progress
    fraction, an `All N gates` claim and a `Gate k of T` ordinal.
    """
    text = path.read_text(encoding="utf-8")
    flow = CONSTS.flow(bound_flow(text))
    positions = {flow.progress_for(phase) for phase in flow.phases}

    for number, line in enumerate(text.splitlines(), start=1):
        switch = FLOW_SWITCH.search(line)
        if switch:
            flow = CONSTS.flow(switch.group(1))
            positions = {flow.progress_for(p) for p in flow.phases}
            continue
        where = f"{path.name}:{number}"

        for done, total in PROSE_FRACTION.findall(line):
            if int(total) != flow.phase_count:
                continue  # a fraction about something else entirely
            assert f"{done}/{total}" in positions, (where, flow.name)

        for total in PROSE_GATE_TOTAL.findall(line):
            assert int(total) == flow.gate_total, (
                where, flow.name, flow.gate_total)

        for shown, total in PROSE_GATE_OF.findall(line):
            if int(total) != flow.gate_total:
                continue  # a comparison against another flow's total
            assert 1 <= int(shown) <= flow.gate_total, (where, flow.name)


@pytest.mark.parametrize("path", TRANSCRIPTS, ids=lambda p: p.name)
def test_no_transcript_states_a_pre_placement_flow_size(path):
    """ADR-013 added two phases and one gate to every flow. A transcript that
    still quotes the old size is stale whatever else it gets right."""
    text = path.read_text(encoding="utf-8")
    flow = CONSTS.flow(bound_flow(text))
    stale = f"{flow.phase_count - 2} phases"
    assert stale not in text, (path.name, stale)


def engine_reasons() -> set[str]:
    source = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
    reasons = set(re.findall(
        r'(?:Refused|IntegrityError|UsageError|_refine_refused)\(\s*"([a-z_]+)"',
        source))
    # Some refusals are reported through `emit(..., reason="…")` rather than
    # raised — `audit verify` among them.
    reasons |= set(re.findall(r'reason="([a-z_]+)"', source))
    # `preflight` reports its problems as keys of a message table.
    reasons |= {"speckit_missing", "speckit_skills_missing",
                "requirements_unbound",
                "requirements_source_missing"}
    return reasons


def test_the_reason_scan_is_not_vacuous():
    reasons = engine_reasons()
    assert {"artifact_unresolved", "tests_not_passed",
            "implementation_base_missing", "execution_id_collision",
            "baseline_required", "impact_analysis_missing"} <= reasons


@pytest.mark.parametrize("path", TRANSCRIPTS, ids=lambda p: p.name)
def test_every_refusal_shown_is_one_the_engine_raises(path):
    reasons = engine_reasons()
    for reason in REFUSED.findall(path.read_text(encoding="utf-8")):
        assert reason in reasons, f"{path.name}: Refused: {reason}"


def defined_tests(relative: str) -> set[str]:
    tree = ast.parse((REPO_ROOT / relative).read_text(encoding="utf-8"))
    return {node.name for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


def cited_nodes(text: str) -> list[tuple[str, str | None]]:
    return [(match.group(1), match.group(2)) for match in NODE.finditer(text)]


@pytest.mark.parametrize("path", sorted(DRY_RUNS.glob("*.md")),
                         ids=lambda p: p.name)
def test_every_cited_test_exists(path):
    text = path.read_text(encoding="utf-8")
    for relative, node in cited_nodes(text):
        assert (REPO_ROOT / relative).is_file(), f"{path.name}: {relative}"
        if node:
            name = node.split("[", 1)[0]
            assert name in defined_tests(relative), (
                f"{path.name}: {relative}::{node} is not defined")


@pytest.mark.parametrize("path", TRANSCRIPTS, ids=lambda p: p.name)
def test_every_transcript_cites_at_least_one_test(path):
    coverage = path.read_text(encoding="utf-8").split(
        "## Executable coverage", 1)[1]
    assert any(node for _, node in cited_nodes(coverage)), path.name


@pytest.mark.parametrize("path", TRANSCRIPTS, ids=lambda p: p.name)
def test_no_retired_runtime_literal_returns(path):
    """What remains of the T11 substitution pin: the literals it replaced
    stay replaced."""
    text = path.read_text(encoding="utf-8")
    for old, _ in DRY_RUN_SUBSTITUTIONS:
        assert old not in text, f"{path.name}: {old!r}"


@pytest.mark.parametrize("path", TRANSCRIPTS, ids=lambda p: p.name)
def test_fingerprints_are_shown_the_way_the_engine_prints_them(path):
    """Lowercase hex, as `sha256_file` returns — the uppercase in the old
    transcripts came from PowerShell's Get-FileHash, long gone."""
    for shown in re.findall(r"Fingerprint: (\S+)", path.read_text("utf-8")):
        assert shown == shown.lower(), f"{path.name}: {shown}"


def test_the_matrix_maps_every_scenario_to_existing_tests():
    matrix = (DRY_RUNS / "verification-matrix.md").read_text(encoding="utf-8")
    for n in range(1, SCENARIO_COUNT + 1):
        assert f"DR-{n:02d}" in matrix, f"DR-{n:02d} is not in the matrix"
    nodes = cited_nodes(matrix)
    assert len(nodes) >= SCENARIO_COUNT
    for defect in ("D01", "D02", "D03", "D04", "D05", "D06"):
        assert defect in matrix, defect


def test_the_index_names_every_flow_and_links_every_scenario():
    index = (DRY_RUNS / "README.md").read_text(encoding="utf-8")
    for flow in sdle.ENGINEERING_FLOWS:
        assert f"`{flow}`" in index, flow
    for path in TRANSCRIPTS:
        assert f"({path.name})" in index, path.name
    assert "(verification-matrix.md)" in index
    assert "**SIMULATED**" in index
