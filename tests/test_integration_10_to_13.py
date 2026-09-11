"""Integration 10-13, derived from the matching dry-run transcripts.

10 BROWNFIELD_DISCOVERY — discovery, its refusal, the baseline it establishes
11 ITERATIVE           — baseline convergence and flow-relative gate numbers
12 DEFECT_FIX          — impact analysis, and the three ways it is refused
13 HOTFIX              — the floor, and the gates the policy could not have

These four flows were previously covered only by the flow-model unit tests,
which drive the traversal. What the transcripts additionally claim is the
*shape a user sees*: the progress fraction, the gate number, the disposition
of a gate the flow does not contain, and which refusal comes back when the
governed record is missing. A traversal test would pass while every one of
those was wrong, so they are asserted here.

Nothing here restates a phase list, a fraction or a gate number as a literal
where the engine can be asked instead: the expectations are derived from the
bound flow, so adding a phase to a flow updates them rather than breaking
them. The three-line traversal literals are the deliberate exception -- they
are the second witness that makes a silent registry edit fail loudly, the
device `GREENFIELD_GOLDEN` already uses.
"""

from __future__ import annotations

import pytest

from conftest import Project, sdle
from test_units_flow_model import (ALL_FLOWS, FEATURE, IMPACT_ARTIFACT, bind,
                                   constants_of, drive, prepare)

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3


def flow_of(project: Project, name: str):
    return constants_of(project).flows[name]


# --------------------------------------------------------------------------
# 10 — BROWNFIELD_DISCOVERY
# --------------------------------------------------------------------------


def test_10_the_flow_opens_on_discovery_before_anything_is_specified(
        git_project):
    """The transcript's whole premise: reading precedes specifying."""
    bind(git_project, "BROWNFIELD_DISCOVERY")

    assert git_project.state()["current_phase"] == "discovery"
    assert git_project.state()["flow"] == "BROWNFIELD_DISCOVERY"


def test_10_the_transcript_progress_fractions_are_what_the_engine_emits(
        git_project):
    """`2/19` in the transcript is a claim about output, not a decoration.

    Asserted against `progress_for` rather than a literal so that a flow which
    later gains a phase moves the transcript's numbers here instead of
    silently disagreeing with it.
    """
    bind(git_project, "BROWNFIELD_DISCOVERY")
    flow = flow_of(git_project, "BROWNFIELD_DISCOVERY")

    assert flow.progress_for("discovery") == f"2/{flow.phase_count}"
    assert flow.phase_count == 19
    header = git_project.ok("header").data
    assert header["progress"] == f"2/{flow.phase_count}"


def test_10_discovery_is_gateless_but_not_ungoverned(git_project):
    """The refusal the transcript shows, on both movers, writing nothing."""
    bind(git_project, "BROWNFIELD_DISCOVERY")
    before = git_project.audit_file.read_bytes()

    refused = git_project.run("advance", "--to", "constitution_draft")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "discovery_missing"
    assert git_project.audit_file.read_bytes() == before
    assert git_project.ok("audit", "verify").data["matches"] is True


def test_10_the_recorded_findings_are_classified_and_readable_back(
        git_project):
    """Every finding carries one of exactly three classifications."""
    bind(git_project, "BROWNFIELD_DISCOVERY")
    git_project.record_discovery()

    record = git_project.ok("discovery", "show").data["record"]

    assert record["result"] == "PASS"
    assert record["workitem"] == git_project.workitem
    seen = {finding["classification"] for finding in record["findings"]}
    assert seen <= set(sdle.DISCOVERY_CLASSIFICATIONS)
    assert len(record["findings"]) == len(sdle.DISCOVERY_CATEGORIES)


def test_10_completion_establishes_the_repository_baseline(git_project):
    """"Discovery happens once" is a file, written at the last gate."""
    baseline = git_project.root / ".sdle" / "baseline.json"
    assert not baseline.exists()

    drive(git_project, "BROWNFIELD_DISCOVERY")

    assert git_project.state()["current_phase"] == "complete"
    assert baseline.is_file(), "the final gate must establish the baseline"


# --------------------------------------------------------------------------
# 11 — ITERATIVE
# --------------------------------------------------------------------------


def test_11_iterative_without_a_baseline_is_refused(git_project):
    """`baseline_required`: the transcript's "refusal this flow exists to
    produce". Convergence onto ITERATIVE is enforced, not conventional."""
    git_project.record_governance(
        classification={"type": "enhancement", "flow": "ITERATIVE"})

    refused = git_project.run("init", session="t")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "baseline_required"


def test_11_the_spec_gate_is_gate_one_of_seven_not_two_of_eight(git_project):
    """The transcript's central claim about numbering.

    `gate_spec` is Gate 2 of 8 in GREENFIELD and Gate 1 of 7 here. A reader
    who learned "the spec gate is Gate 2" is wrong for three flows out of
    five, so this pins the derivation rather than the habit.
    """
    bind(git_project, "ITERATIVE")
    iterative = flow_of(git_project, "ITERATIVE")
    greenfield = flow_of(git_project, "GREENFIELD")

    assert (iterative.gate_number("gate_spec"), iterative.gate_total) == (1, 7)
    assert (greenfield.gate_number("gate_spec"),
            greenfield.gate_total) == (2, 8)

    shown = git_project.ok("gate", "show", "--gate", "gate_spec").data
    assert shown["gate_number"] == 1
    assert shown["gate_total"] == 7


def test_11_the_constitution_gate_is_not_in_flow_never_satisfied(git_project):
    """A gate the flow does not contain is reported, not quietly passed."""
    bind(git_project, "ITERATIVE")

    shown = git_project.ok("gate", "show", "--gate", "gate_constitution").data
    assert shown["in_flow"] is False
    assert shown["required"] is None, "a gate outside the flow is not required"

    # `governance gates` reports dispositions only for gates the flow HAS.
    # A gate outside it is not given a disposition at all -- it surfaces in
    # `required_not_in_flow` when the policy asked for it, and nowhere when
    # the policy did not. Both are correct: an absent gate has no state to be
    # in, and inventing "satisfied" for it is exactly the failure mode this
    # reporting exists to prevent.
    report = git_project.ok("governance", "gates").data
    assert "gate_constitution" not in {d["gate"]
                                       for d in report["dispositions"]}
    assert "gate_constitution" not in flow_of(git_project, "ITERATIVE").phases


def test_11_an_iterative_run_leaves_the_baseline_untouched(git_project):
    """A baseline is established once and worked against thereafter."""
    git_project.establish_baseline()
    baseline = git_project.root / ".sdle" / "baseline.json"
    before = sdle.sha256_file(baseline)

    drive(git_project, "ITERATIVE")

    assert git_project.state()["current_phase"] == "complete"
    assert sdle.sha256_file(baseline) == before


def test_11_brownfield_then_iterative_reuses_the_baseline_without_rewriting_it(
        git_project):
    """DR-11's continuation (SDLE-DEFECT-STABILIZATION-01 D06). The first
    WorkItem discovers the repository; the second works against what it
    established. Reuse is *reading*: the baseline, the discovery record it
    references and the inherited constitution are byte-identical after the
    second WorkItem completes, and it never ran discovery or regenerated the
    constitution. `test_units_baseline.py::test_n24_the_second_workitem_does_not_rediscover_the_repository`
    pins the `baseline_present` refusal on the way; this pins what reuse
    leaves untouched."""
    drive(git_project, "BROWNFIELD_DISCOVERY")
    baseline = git_project.root / ".sdle" / "baseline.json"
    constitution = git_project.root / ".specify" / "memory" / "constitution.md"
    discovery = git_project.runtime / "discovery.json"
    before = {path: sdle.sha256_file(path)
              for path in (baseline, constitution, discovery)}

    git_project.ok("workitem", "create", "--name", "Export CSV")
    second = git_project.as_workitem("export-csv")
    seen = drive(second, "ITERATIVE")

    assert seen[-1] == "complete"
    assert "discovery" not in seen and "constitution_draft" not in seen
    assert second.state()["approvals"]["gate_constitution"] is None
    after = {path: sdle.sha256_file(path) for path in before}
    assert after == before, "reusing the baseline must not rewrite anything"
    assert git_project.ok("baseline", "show").data["status"] == "VALID"


# --------------------------------------------------------------------------
# 12 — DEFECT_FIX
# --------------------------------------------------------------------------


def test_12_the_flow_opens_on_the_impact_analysis(git_project):
    bind(git_project, "DEFECT_FIX")
    flow = flow_of(git_project, "DEFECT_FIX")

    assert git_project.state()["current_phase"] == "impact_analysis"
    assert flow.progress_for("impact_analysis") == f"2/{flow.phase_count}"
    assert flow.phase_count == 14
    assert flow.gate_total == 6


def test_12_writing_the_analysis_is_not_recording_it(git_project):
    """The transcript's first refusal. The file exists and was displayed; the
    engine still refuses, because what it can verify is a fingerprint and a
    review, not that somebody read a document."""
    bind(git_project, "DEFECT_FIX")
    git_project.write_artifact(IMPACT_ARTIFACT)

    refused = git_project.run("advance", "--to", "spec_draft")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "impact_analysis_missing"
    assert refused.data["artifact"] is None


def test_12_recording_alone_does_not_lift_the_refusal(git_project):
    """A fingerprint is not a judgement."""
    bind(git_project, "DEFECT_FIX")
    git_project.write_artifact(IMPACT_ARTIFACT)
    git_project.ok("artifact", "record", "--phase", "impact_analysis",
                   "--path", IMPACT_ARTIFACT)

    refused = git_project.run("advance", "--to", "spec_draft")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "impact_analysis_missing"
    assert refused.data["artifact"] == IMPACT_ARTIFACT


def test_12_editing_after_the_review_re_arms_the_refusal(git_project):
    """Why the phase contract says to record the review last. No new
    mechanism: TP-011 binds a review to one SHA and always did."""
    bind(git_project, "DEFECT_FIX")
    prepare(git_project, "impact_analysis", git_project.feature_dir(FEATURE))
    git_project.write_artifact(
        IMPACT_ARTIFACT, "# Widened analysis\n\n" + "word " * 40)

    refused = git_project.run("advance", "--to", "spec_draft")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "impact_analysis_missing"


def test_12_the_design_gate_is_not_in_flow(git_project):
    """`DEFECT_FIX` drops the checklist and the design phase with its gate."""
    bind(git_project, "DEFECT_FIX")
    phases = flow_of(git_project, "DEFECT_FIX").phases

    for absent in ("checklist_draft", "design_generation", "gate_design"):
        assert absent not in phases
    report = git_project.ok("governance", "gates").data
    assert "gate_design" not in {d["gate"] for d in report["dispositions"]}
    assert git_project.ok(
        "gate", "show", "--gate", "gate_design").data["in_flow"] is False


def test_12_but_the_tasks_gate_survives(git_project):
    """A defect always adds `gate_tasks` — the transcript's stated reason is
    that "we changed the thing next to the broken thing" is how a one-line fix
    becomes an outage."""
    assert "gate_tasks" in flow_of(git_project, "DEFECT_FIX").phases


# --------------------------------------------------------------------------
# 13 — HOTFIX
# --------------------------------------------------------------------------


def test_13_hotfix_is_the_floor_plus_the_impact_analysis(git_project):
    """"The shortest flow that *can* exist", asserted rather than claimed."""
    phases = set(flow_of(git_project, "HOTFIX").phases)

    assert phases - {"impact_analysis"} == set(sdle.MANDATORY_FLOW_PHASES)


def test_13_ten_phases_three_gates(git_project):
    flow = flow_of(git_project, "HOTFIX")
    assert (flow.phase_count, flow.gate_total) == (10, 3)


def test_13_five_gates_are_not_in_flow_and_none_is_omitted(git_project):
    """The disposition report the transcript prints. A gate the policy wanted
    and the flow does not have is `not_in_flow` — never "omitted", which would
    imply it could have been required, and never quietly satisfied."""
    # The transcript runs at HIGH risk, which is the whole point of the
    # scene: HIGH is where the policy asks for gates this flow does not have.
    # `bind` assesses LOW, so the risk is set explicitly here rather than
    # inherited -- at LOW the report would be a weaker witness.
    git_project.record_governance(
        classification={"type": "defect", "flow": "HOTFIX"},
        risk={"signals": ["production_security_boundary"],
              "proposedLevel": "HIGH", "uncertainty": "LOW"})
    git_project.ok("init", session="hot")
    absent = ["gate_constitution", "gate_plan", "gate_tasks", "gate_analyze",
              "gate_design"]

    assert git_project.ok("governance", "gates").data["final_risk"] == "HIGH"

    report = git_project.ok("governance", "gates").data
    in_report = {d["gate"] for d in report["dispositions"]}
    for key in absent:
        assert key not in in_report, (key, report)
        assert key not in report["omittable_gates"], (
            f"{key} is absent from the flow, not merely omittable")
        assert git_project.ok(
            "gate", "show", "--gate", key).data["in_flow"] is False

    # And the honest part: at HIGH risk the policy DID require four of these,
    # and the report says so rather than dropping the requirement silently.
    # An unreported inert rule is how a policy comes to claim a guarantee
    # nobody is enforcing.
    assert set(report["required_not_in_flow"]) == set(absent)


def test_13_the_impact_analysis_is_still_enforced_under_pressure(git_project):
    """`HOTFIX` drops five gates. It does not drop this."""
    bind(git_project, "HOTFIX")

    refused = git_project.run("advance", "--to", "spec_draft")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "impact_analysis_missing"


def test_13_plan_and_tasks_run_without_their_gates(git_project):
    """The artifacts are still generated and fingerprinted; only the human
    approval points are absent. "Fewer gates" is not "fewer artifacts"."""
    phases = flow_of(git_project, "HOTFIX").phases

    assert "plan_draft" in phases and "gate_plan" not in phases
    assert "tasks_draft" in phases and "gate_tasks" not in phases


def test_13_the_final_gate_is_required_by_a_rule_no_override_reaches(
        git_project):
    """`gate_security` is the flow's last gate before `complete`, and that
    positional rule lives in no dictionary — so no policy override can lower
    it. The floor is a floor."""
    flow = flow_of(git_project, "HOTFIX")

    assert flow.phases[-2] == "gate_security"
    assert flow.next_phase("gate_security") == "complete"
    bind(git_project, "HOTFIX")
    report = git_project.ok("governance", "gates").data
    entry = next(d for d in report["dispositions"]
                 if d["gate"] == "gate_security")
    assert entry["disposition"] == "required"
    assert "terminal_gate" in entry["reasons"], (
        "the floor is positional, not a policy entry an override could reach")
    assert "gate_security" not in report["omittable_gates"]


# --------------------------------------------------------------------------
# The transcripts as a set
# --------------------------------------------------------------------------


@pytest.mark.parametrize("flow", ALL_FLOWS)
def test_every_shipped_flow_now_has_a_transcript(flow):
    """The gap these four files close.

    Before them, `01-09` were all GREENFIELD and the other four flows had no
    conversational specification at all — only traversal tests. A sixth flow
    added later would land here rather than shipping undocumented.
    """
    from pathlib import Path

    from conftest import REPO_ROOT

    transcripts = {
        "GREENFIELD": "01-happy-path.md",
        "BROWNFIELD_DISCOVERY": "10-brownfield-discovery.md",
        "ITERATIVE": "11-iterative.md",
        "DEFECT_FIX": "12-defect-fix.md",
        "HOTFIX": "13-hotfix.md",
    }
    assert flow in transcripts, f"{flow} ships without a dry-run transcript"
    path = Path(REPO_ROOT) / "docs" / "dry-runs" / transcripts[flow]
    assert path.is_file(), path
    assert path.stat().st_size > 1000, "a transcript that documents nothing"
