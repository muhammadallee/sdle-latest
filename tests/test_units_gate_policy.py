"""Contract §15 — risk-adaptive gate policy.

§15's goal is *"policy-driven gates without weakening governance"* and its
exit criterion is that *"design/security are neither universally mandatory nor
casually skippable"*. §12's closing line is what makes that tractable and it
is the sentence this whole file is written against:

> Human approval remains policy-driven; review/validation is universal for
> governed artifacts.

So exactly one thing here is policy-driven: whether a gate requires a **human
approval**. Artifact generation, registration, the SHA baseline, TP-011
review, drift detection, the secrets scan, the test evidence, the
implementation diff baseline, the audit chain, the retry/remediation caps and
the fail-safe transitions are all still universal, and this file asserts that
directly for an *omitted* gate rather than assuming it.

Three rules govern this file, following `test_units_governance.py`:

1. **No shared fixture is modified.** Helpers this file needs live here.
2. **Every floor value this phase must not lower is written as a literal**,
   so "no floor was lowered while I was in here" is machine-checked rather
   than narrated.
3. **A refusal is proved by its exit code AND by the ledger being
   byte-identical**, because a refusal that appended to `audit.md` first would
   break invariants 5 and 6 while still looking like a refusal.
"""

from __future__ import annotations

import ast
import copy
import functools
import json
import subprocess
from pathlib import Path

import pytest

from conftest import SDLE_PY, Project, sdle
from test_units_artifact_review import audit_entries, review_for_gate
from test_units_flow_model import FEATURE, prepare
from test_units_governance import (
    BUILTIN,
    assess,
    governance_input,
    paths_for,
    policy_file,
    record_of,
    sha_map,
    write_policy,
)

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_INTEGRITY = 3

REPO_ROOT = Path(SDLE_PY).resolve().parent.parent


# --------------------------------------------------------------------------
# Helpers — local by design
# --------------------------------------------------------------------------


def consts_for(project: Project):
    return sdle.load_constants(paths_for(project))


def risk_input(signals, proposed="LOW", uncertainty="LOW", **over) -> dict:
    document = governance_input(**over)
    document["risk"] = {"signals": list(signals), "proposedLevel": proposed,
                        "uncertainty": uncertainty}
    return document


def level_index(level: str) -> int:
    return sdle.GOVERNANCE_LEVELS.index(level)


# --------------------------------------------------------------------------
# N7/N8 — §15's nine hard floors, driven through the real CLI
# --------------------------------------------------------------------------
#
# The expectation table is written out in full rather than derived from
# `BUILTIN`, so a floor that is *removed* fails here instead of silently
# shrinking the parametrisation. §15's list is nine rows; the tenth entry
# below is the extra signal T09 added for blast radius, which §15 names.

SECTION_15_FLOORS = {
    # §15 line                                  signal id                       level
    "authentication/authorization": ("authentication_or_authorization", "HIGH"),
    "sensitive data": ("personal_or_sensitive_data", "HIGH"),
    "regulatory/compliance": ("regulatory_or_compliance", "HIGH"),
    "destructive migration": ("destructive_or_irreversible_migration", "HIGH"),
    "breaking public contract": ("backward_incompatible_change", "HIGH"),
    "financial correctness": ("payment_or_financial", "HIGH"),
    "production security boundary": ("production_security_boundary", "HIGH"),
    "catastrophic blast radius": ("catastrophic_blast_radius", "CRITICAL"),
    "credential/key exposure": ("credential_or_key_exposure", "CRITICAL"),
}


def test_section_15_names_nine_floors_and_the_table_is_not_short():
    """Guard against N7 passing because a row went missing from the table."""
    assert len(SECTION_15_FLOORS) == 9
    assert len({s for s, _ in SECTION_15_FLOORS.values()}) == 9


@pytest.mark.parametrize("line", sorted(SECTION_15_FLOORS))
def test_n7_every_section_15_floor_fires_through_the_cli(project, line):
    """N7/A2: an input naming only that signal reaches at least §15's level,
    and `floorsApplied` names the rule that did it rather than just the
    resulting level."""
    signal, mandated = SECTION_15_FLOORS[line]

    assert assess(project, risk_input([signal])).exit_code == EXIT_OK

    risk = record_of(project)["risk"]
    assert level_index(risk["finalLevel"]) >= level_index(mandated), risk
    fired = [entry["rule"] for entry in risk["floorsApplied"]]
    assert {"signal": signal, "level": mandated} in fired, fired


def test_n8_authentication_alone_is_high(project):
    """N8/A2: the live under-enforcement T09 fixes. §15 states HIGH for an
    authentication/authorization/security control; the shipped built-in
    floored it at MEDIUM."""
    assert assess(project, risk_input(
        ["authentication_or_authorization"])).exit_code == EXIT_OK

    risk = record_of(project)["risk"]
    assert risk["deterministicLevel"] == "HIGH", risk
    assert risk["finalLevel"] == "HIGH", risk


# --------------------------------------------------------------------------
# N9 — no floor and no weight is below its value at the rollback point
# --------------------------------------------------------------------------
#
# Literals, deliberately. Deriving them from `BUILTIN` would make this test
# true by construction and prove nothing. These are the values read out of
# `GOVERNANCE_POLICY_BUILTIN` at `e1cf341` (T08 implementation).

FLOORS_AT_E1CF341 = {
    ("signal", "payment_or_financial"): "HIGH",
    ("signal", "cryptography_or_secrets"): "HIGH",
    ("signal", "personal_or_sensitive_data"): "HIGH",
    ("signal", "authentication_or_authorization"): "MEDIUM",
    ("uncertainty", "HIGH"): "HIGH",
    ("uncertainty", "CRITICAL"): "CRITICAL",
}

WEIGHTS_AT_E1CF341 = {
    "external_api_surface": 2,
    "persistent_data_store": 2,
    "schema_or_data_migration": 3,
    "authentication_or_authorization": 3,
    "personal_or_sensitive_data": 4,
    "payment_or_financial": 4,
    "cryptography_or_secrets": 4,
    "public_network_exposure": 3,
    "third_party_dependency": 1,
    "concurrency_or_distributed_state": 2,
    "infrastructure_or_deployment": 2,
    "backward_incompatible_change": 3,
}

THRESHOLDS_AT_E1CF341 = {"LOW": 0, "MEDIUM": 2, "HIGH": 5, "CRITICAL": 9}


def current_floor_levels() -> dict[tuple[str, str], str]:
    levels: dict[tuple[str, str], str] = {}
    for rule in BUILTIN["hard_floors"]:
        for kind in ("signal", "uncertainty"):
            if kind in rule:
                key = (kind, rule[kind])
                if key not in levels or level_index(rule["level"]) > level_index(
                        levels[key]):
                    levels[key] = rule["level"]
    return levels


def test_n9_no_built_in_floor_was_lowered_or_removed():
    """N9/A3/F1: machine-checked "no floor went down while I was in here"."""
    current = current_floor_levels()
    for key, was in FLOORS_AT_E1CF341.items():
        assert key in current, f"the floor {key} was removed"
        assert level_index(current[key]) >= level_index(was), (key, current[key], was)


def test_n9_no_built_in_signal_weight_was_lowered_or_removed():
    """N9/A3/F1: the other half — a weight drop lowers a score-derived
    level just as effectively as a floor drop."""
    for signal, was in WEIGHTS_AT_E1CF341.items():
        assert signal in BUILTIN["risk_signals"], f"{signal} was removed"
        assert BUILTIN["risk_signals"][signal] >= was, signal


def test_n9_no_threshold_became_harder_to_reach():
    """N9/A3: raising a threshold makes a level harder to reach, which is a
    weakening even though every floor stayed put."""
    for level, was in THRESHOLDS_AT_E1CF341.items():
        assert BUILTIN["risk_thresholds"][level] <= was, level


def test_n9_the_first_six_floor_rules_keep_their_positions():
    """`test_units_governance.py` indexes `hard_floors[0]`, and the T09 edit
    was specified as "edit one level in place, append the rest"."""
    kinds = [(rule.get("signal") or rule.get("uncertainty"))
             for rule in BUILTIN["hard_floors"][:6]]
    assert kinds == ["payment_or_financial", "cryptography_or_secrets",
                     "personal_or_sensitive_data",
                     "authentication_or_authorization", "HIGH", "CRITICAL"]


def test_a1_the_built_in_policy_shape_is_what_section_15_requires(bare_project):
    """A1, read out of the engine through the real command."""
    shown = bare_project.ok("governance", "policy")
    policy = shown.data["policy"]

    assert len(policy["risk_signals"]) == 17
    assert len(policy["hard_floors"]) == 12
    assert policy["risk_thresholds"] == THRESHOLDS_AT_E1CF341
    assert policy["required_gates_always"] == [
        "gate_constitution", "gate_spec", "gate_plan", "gate_implement"]
    assert policy["required_gates_by_risk"] == {
        "LOW": [],
        "MEDIUM": ["gate_tasks", "gate_design"],
        "HIGH": ["gate_tasks", "gate_analyze", "gate_design", "gate_security"],
        "CRITICAL": ["gate_tasks", "gate_analyze", "gate_design",
                     "gate_security"],
    }
    assert policy["required_gates_by_type"] == {
        "enhancement": [], "defect": ["gate_tasks"], "hotfix": [], "chore": []}
    assert policy["policyVersion"] == "1"


# --------------------------------------------------------------------------
# N10 — the tightening is enforced against overrides too
# --------------------------------------------------------------------------


def test_n10_an_override_restating_the_old_auth_floor_is_refused(bare_project):
    """N10/A4: a repository that pins the *previous* MEDIUM floor is now
    weakening the baseline, and gets the same refusal an attempt to lower it
    would get. There is no grandfathering path."""
    floors = copy.deepcopy(BUILTIN["hard_floors"])
    for rule in floors:
        if rule.get("signal") == "authentication_or_authorization":
            rule["level"] = "MEDIUM"
    write_policy(bare_project, {"hard_floors": floors})

    result = bare_project.run("governance", "policy")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "policy_weakens_baseline", result
    assert result.data["key"] == "hard_floors", result


def test_n10_an_override_may_still_raise_a_floor_further(bare_project):
    """The contrast: monotonicity is a floor, not a freeze."""
    floors = copy.deepcopy(BUILTIN["hard_floors"])
    for rule in floors:
        if rule.get("signal") == "authentication_or_authorization":
            rule["level"] = "CRITICAL"
    write_policy(bare_project, {"hard_floors": floors})

    shown = bare_project.ok("governance", "policy")

    fired = [r for r in shown.data["policy"]["hard_floors"]
             if r.get("signal") == "authentication_or_authorization"]
    assert fired == [{"signal": "authentication_or_authorization",
                      "level": "CRITICAL"}]


def test_an_override_dropping_gate_design_from_medium_is_refused(bare_project):
    """The MEDIUM cell T09 tightened is protected by the same rule."""
    write_policy(bare_project,
                 {"required_gates_by_risk": {"MEDIUM": ["gate_tasks"]}})

    result = bare_project.run("governance", "policy")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "policy_weakens_baseline", result
    assert result.data["key"] == "required_gates_by_risk", result


# --------------------------------------------------------------------------
# The new signals really are new, and really are weighed
# --------------------------------------------------------------------------


NEW_SIGNALS = (
    "destructive_or_irreversible_migration",
    "regulatory_or_compliance",
    "production_security_boundary",
    "credential_or_key_exposure",
    "catastrophic_blast_radius",
)


@pytest.mark.parametrize("signal", NEW_SIGNALS)
def test_each_new_signal_carries_weight_as_well_as_a_floor(signal):
    """A signal whose only effect is its floor would be a boolean pretending
    to be a weight: it would contribute nothing when combined with others.

    Stated exactly, because it would be easy to overclaim here: each new
    signal alone reaches **at least MEDIUM by score**, and its floor is at or
    above that score-derived level. The floor is what carries it the rest of
    the way, which is the point of having a floor at all.
    """
    weight = BUILTIN["risk_signals"][signal]
    by_score = sdle.deterministic_level(weight, BUILTIN["risk_thresholds"])
    floor = next(r["level"] for r in BUILTIN["hard_floors"]
                 if r.get("signal") == signal)
    assert level_index(by_score) >= level_index("MEDIUM"), (signal, by_score)
    assert level_index(floor) >= level_index(by_score), (signal, floor, by_score)


def test_the_signals_that_were_deliberately_not_widened_keep_their_shape():
    """§15's destructive-migration and production-boundary floors were given
    dedicated signals rather than folded into `schema_or_data_migration` and
    `public_network_exposure`, precisely so ordinary use of those two is not
    over-enforced. If a later change folds them in, this fails."""
    floored = {r["signal"] for r in BUILTIN["hard_floors"] if "signal" in r}
    assert "schema_or_data_migration" not in floored
    assert "public_network_exposure" not in floored
    assert BUILTIN["risk_signals"]["schema_or_data_migration"] == 3
    assert BUILTIN["risk_signals"]["public_network_exposure"] == 3


# --------------------------------------------------------------------------
# N1-N5, N14 — the requirement model, over the whole flow x level x type space
# --------------------------------------------------------------------------
#
# The model is a pure function of (bound flow, classification, final level,
# effective policy). None of it touches a runtime, so the 80-cell cross
# product below is asserted against constants parsed from the checkout's own
# SKILL.md rather than through ~250 temporary git projects. Parsing a Markdown
# table is line-ending independent, so this does not reintroduce the hazard
# `conftest.py`'s "fixtures are generated at runtime" rule exists to prevent —
# that rule is about *hashing* a checked-in file, which nothing here does.


@functools.lru_cache(maxsize=1)
def repo_consts():
    return sdle.load_constants(sdle.resolve_paths(
        str(REPO_ROOT), str(REPO_ROOT / ".claude" / "skills" / "sdle")))


def model_for(flow_name: str, level: str, wi_type: str, policy=None) -> dict:
    consts = repo_consts()
    return sdle.gate_requirements(
        consts, consts.flow(flow_name), {"type": wi_type, "flow": flow_name},
        level, policy or BUILTIN)


ALL_FLOWS = tuple(sorted(sdle.ENGINEERING_FLOWS))
SPACE = [(flow, level, wi_type)
         for flow in ALL_FLOWS
         for level in sdle.GOVERNANCE_LEVELS
         for wi_type in sdle.WORKITEM_TYPES]


def test_the_cross_product_is_the_size_it_claims_to_be():
    """Non-vacuity guard for every parametrisation below."""
    assert len(ALL_FLOWS) == 5
    assert len(sdle.GOVERNANCE_LEVELS) == 4
    assert len(sdle.WORKITEM_TYPES) == 4
    assert len(SPACE) == 80


def test_the_repo_constants_agree_with_a_real_project(project):
    """The shortcut above is only legitimate if it produces the same object a
    scratch project would. Asserted once, so the 80-cell cases can skip the
    fixture without skipping the check."""
    live = sdle.load_constants(paths_for(project))
    assert live.phase_sequence == repo_consts().phase_sequence
    assert live.phase_to_gate_key == repo_consts().phase_to_gate_key
    assert live.flow_phases == repo_consts().flow_phases


@pytest.mark.parametrize("flow,level,wi_type", SPACE)
def test_n1_every_flow_gate_gets_exactly_one_disposition(flow, level, wi_type):
    """N1: a disposition for every gate in the bound flow and for no gate
    outside it, drawn from the closed vocabulary, and every `required` entry
    carries at least one reason — so "why did this gate stop me" always has a
    machine-readable answer."""
    consts = repo_consts()
    model = model_for(flow, level, wi_type)

    gates = list(consts.flow(flow).gate_keys)
    assert [d["gate"] for d in model["dispositions"]] == gates
    phase_of = {key: phase for phase, key in consts.phase_to_gate_key.items()}
    for entry in model["dispositions"]:
        assert entry["disposition"] in sdle.GATE_DISPOSITIONS, entry
        assert entry["gate_phase"] == phase_of[entry["gate"]], entry
        if entry["disposition"] == "required":
            assert entry["reasons"], entry
        else:
            assert entry["disposition"] == "omittable", entry
            assert entry["reasons"] == [], entry

    assert (set(model["required_gates"]) | set(model["omittable_gates"])
            == set(gates))
    assert not set(model["required_gates"]) & set(model["omittable_gates"])
    assert not set(model["required_not_in_flow"]) & set(gates)


@pytest.mark.parametrize("flow,level,wi_type", SPACE)
def test_n2_the_terminal_gate_is_required_everywhere(flow, level, wi_type):
    """N2/D4/A7: §15's LOW list requires a *final human review*, so the last
    gate of the bound flow is required at every level and every type, and the
    reason it carries names why — it is the terminal human decision on the
    run, not a claim that security review is universally mandatory."""
    model = model_for(flow, level, wi_type)
    terminal = repo_consts().flow(flow).gate_keys[-1]

    assert model["terminal_gate"] == terminal
    entry = next(d for d in model["dispositions"] if d["gate"] == terminal)
    assert entry["disposition"] == "required", entry
    assert "terminal_gate" in entry["reasons"], entry


def test_the_terminal_gate_of_every_declared_flow_is_gate_security():
    """Named, so that if a later flow changes it the derived rule is shown to
    have followed rather than to have been re-pinned by hand."""
    consts = repo_consts()
    assert {name: consts.flow(name).gate_keys[-1] for name in ALL_FLOWS} == {
        name: "gate_security" for name in ALL_FLOWS}


def test_the_terminal_rule_is_positional_not_a_policy_row():
    """D4: `gate_security` is required because of where it sits, and a
    repository override edits dictionaries. A derived positional rule is in no
    dictionary, so an override cannot reach it at all."""
    assert "gate_security" not in BUILTIN["required_gates_always"]
    assert "gate_security" not in BUILTIN["required_gates_by_risk"]["LOW"]


@pytest.mark.parametrize("flow,level,wi_type", SPACE)
def test_n3_required_not_in_flow_is_exactly_what_the_flow_lacks(flow, level,
                                                                wi_type):
    """N3/I4: a policy may name a gate the bound flow does not contain. That
    requirement is inert, and it is REPORTED as inert rather than dropped."""
    model = model_for(flow, level, wi_type)
    named = set(sdle.required_gate_set(
        {"type": wi_type, "flow": flow}, level, BUILTIN))

    assert set(model["required_not_in_flow"]) == named - set(
        repo_consts().flow(flow).gate_keys)


def test_n3_the_inert_report_is_not_vacuous_today():
    """N3: with the built-in policy and HOTFIX it is non-empty, so the report
    is testable rather than theoretical. `gate_constitution` and `gate_plan`
    sit in `required_gates_always` and HOTFIX contains neither — a pre-flow
    leftover that has been silently inert since T07. T09 does not remove it
    (removing a requirement is a weakening); it stops it being silent."""
    assert model_for("HOTFIX", "LOW", "hotfix")["required_not_in_flow"] == [
        "gate_constitution", "gate_plan"]


@pytest.mark.parametrize("level", sdle.GOVERNANCE_LEVELS)
@pytest.mark.parametrize("wi_type", sdle.WORKITEM_TYPES)
def test_n4_hotfix_has_no_omittable_gate_at_any_level(wi_type, level):
    """N4/A7: §13's "shorter but never ungoverned" survives T09 as an
    identity, not a judgement. HOTFIX's three gates are `gate_spec` and
    `gate_implement` (always required) and `gate_security` (terminal), so
    §15's LOW list cannot make it any shorter."""
    model = model_for("HOTFIX", level, wi_type)
    assert model["omittable_gates"] == []
    assert model["required_gates"] == ["gate_implement", "gate_security",
                                       "gate_spec"]


@pytest.mark.parametrize("flow", ALL_FLOWS)
@pytest.mark.parametrize("wi_type", sdle.WORKITEM_TYPES)
def test_n5_the_omittable_set_only_shrinks_as_risk_rises(wi_type, flow):
    """N5/F1: the monotonicity that makes "governance was not weakened"
    checkable rather than narrated. It must never be possible to omit MORE by
    declaring a HIGHER risk."""
    sets = {level: set(model_for(flow, level, wi_type)["omittable_gates"])
            for level in sdle.GOVERNANCE_LEVELS}

    assert sets["LOW"] >= sets["MEDIUM"] >= sets["HIGH"], (flow, wi_type, sets)
    assert sets["HIGH"] == sets["CRITICAL"] == set(), (flow, wi_type, sets)


def test_n5_is_not_vacuous_something_really_is_omittable_at_low():
    """Guard: if nothing were ever omittable the monotonicity above would hold
    trivially and T09 would have shipped nothing."""
    assert set(model_for("GREENFIELD", "LOW", "enhancement")
               ["omittable_gates"]) == {"gate_tasks", "gate_analyze",
                                        "gate_design"}
    assert set(model_for("GREENFIELD", "MEDIUM", "enhancement")
               ["omittable_gates"]) == {"gate_analyze"}


def test_n14_critical_requires_a_gate_before_implement_and_at_the_end():
    """N14/D5/A6: §15's CRITICAL adds "human approval before implementation"
    and "human approval before completion". Both are POSITIONAL claims about
    the bound flow, so they are checked positionally rather than implemented
    as a branch that would be dead code.

    Stated plainly, because it would be dishonest to imply otherwise: under
    the built-in policy CRITICAL's required set is *equal* to HIGH's. §15 says
    "HIGH plus", and what CRITICAL adds is satisfied structurally. A
    repository that wants more may add to the policy, monotonically.
    """
    consts = repo_consts()
    for flow_name in ALL_FLOWS:
        flow = consts.flow(flow_name)
        phases = list(flow.phases)
        before = [consts.phase_to_gate_key[p]
                  for p in phases[:phases.index("implement")]
                  if p in consts.phase_to_gate_key]
        # Non-vacuity: every flow really does have a gate before `implement`.
        assert before, flow_name
        for wi_type in sdle.WORKITEM_TYPES:
            required = set(model_for(flow_name, "CRITICAL", wi_type)
                           ["required_gates"])
            assert set(before) & required, (flow_name, wi_type)
            assert flow.gate_keys[-1] in required, (flow_name, wi_type)


def test_required_gate_set_keeps_its_name_and_is_the_policy_half():
    """D12: T06 built `required_gate_set` for exactly this phase. It is
    consumed, not duplicated — and it is still only half an answer, because a
    dictionary lookup cannot see the bound flow or the terminal-gate rule."""
    named = sdle.required_gate_set({"type": "hotfix", "flow": "HOTFIX"},
                                   "LOW", BUILTIN)
    assert named == ["gate_constitution", "gate_implement", "gate_plan",
                     "gate_spec"]
    assert "gate_security" not in named
    assert "gate_security" in model_for("HOTFIX", "LOW", "hotfix")[
        "required_gates"]


# --------------------------------------------------------------------------
# N6/N24 — the two reporters agree, and neither writes anything
# --------------------------------------------------------------------------


def test_n6_gate_show_and_governance_gates_agree(project):
    """N6: two commands, one model. A disagreement here would mean a second
    source of truth for a security-relevant fact (invariant 7)."""
    assert assess(project, risk_input([], proposed="LOW")).exit_code == EXIT_OK
    project.ok("init", session="agree")

    gates = project.ok("governance", "gates").data
    assert gates["flow_source"] == "state"
    by_gate = {d["gate"]: d for d in gates["dispositions"]}
    assert by_gate, "an empty disposition list would make this vacuous"

    for gate_key, entry in by_gate.items():
        shown = project.ok("gate", "show", "--gate", gate_key).data
        assert shown["required"] == (entry["disposition"] == "required"), \
            gate_key
        assert shown["requirement_reasons"] == entry["reasons"], gate_key


def test_gate_show_answers_null_when_there_is_no_governance_record(project):
    """`required` is a fact about a policy AND a record. With no record there
    is no answer, and reporting `false` would be an answer the engine has not
    got."""
    project.record_governance()
    project.ok("init", session="norecord")
    (project.runtime / "governance.json").unlink()

    shown = project.ok("gate", "show", "--gate", "gate_design").data
    assert shown["required"] is None
    assert shown["requirement_reasons"] is None


def test_governance_gates_answers_before_init_from_the_record(project):
    """The question is asked before `init` — that is when it is useful — so
    the flow is resolved from the record and `flow_source` says which."""
    assert assess(project, governance_input(
        classification={"type": "hotfix",
                        "flow": "HOTFIX"})).exit_code == EXIT_OK

    gates = project.ok("governance", "gates").data
    assert gates["flow"] == "HOTFIX"
    assert gates["flow_source"] == "record"
    assert gates["omittable_gates"] == []
    assert gates["required_not_in_flow"] == ["gate_constitution", "gate_plan"]
    assert gates["policy"]["source"] == "builtin"


def test_governance_gates_no_longer_claims_to_be_advisory(project):
    """Delta 9: the set it reports is what `gate omit` is refused against, so
    a field saying nothing consumes it would be a false statement about the
    engine's own behaviour."""
    assert assess(project).exit_code == EXIT_OK
    data = project.ok("governance", "gates").data
    assert "advisory" not in data
    assert "note" not in data
    assert "would_be_required_gates" not in data


def test_n24_both_reporters_are_read_only(project):
    """N24/A9: neither command may write anything, including a lock touch."""
    assert assess(project).exit_code == EXIT_OK
    project.ok("init", session="readonly")

    before = sha_map(project.root)
    assert project.run("governance", "gates").exit_code == EXIT_OK
    assert project.run("gate", "show",
                       "--gate", "gate_design").exit_code == EXIT_OK
    assert sha_map(project.root) == before


# --------------------------------------------------------------------------
# N25 — the governance record gains a real version reader
# --------------------------------------------------------------------------


def test_the_record_declares_version_two_and_carries_both_gate_lists(project):
    """D12: `wouldBeRequiredGates` is replaced by the two lists the model
    actually produces, computed against the flow the record PROPOSES."""
    assert assess(project).exit_code == EXIT_OK

    record = record_of(project)
    assert record["governanceVersion"] == "2"
    assert "wouldBeRequiredGates" not in record
    assert record["requiredGates"] == ["gate_constitution", "gate_implement",
                                       "gate_plan", "gate_security",
                                       "gate_spec"]
    assert record["omittableGates"] == ["gate_analyze", "gate_design",
                                        "gate_tasks"]


def test_n25_a_version_one_record_still_advances(project):
    """N25/D12: a `"1"` record stays valid. Its stale key is never read for a
    decision, because every decision re-derives from the policy on disk."""
    assert assess(project).exit_code == EXIT_OK
    project.ok("init", session="v1")

    path = project.runtime / "governance.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    record["governanceVersion"] = "1"
    del record["requiredGates"]
    del record["omittableGates"]
    record["wouldBeRequiredGates"] = ["gate_spec"]
    path.write_text(json.dumps(record, indent=2), encoding="utf-8",
                    newline="\n")

    project.write_artifact(".specify/memory/constitution.md")
    assert project.run("advance",
                       "--to", "gate_constitution").exit_code == EXIT_OK


@pytest.mark.parametrize("version", ["3", 2, None, ""])
def test_n25_an_unreadable_record_version_is_an_integrity_failure(project,
                                                                  version):
    """N25: a version field nothing refuses on proves nothing. Exit 3, the
    same shape every other unreadable runtime file SDLE itself wrote has."""
    assert assess(project).exit_code == EXIT_OK
    project.ok("init", session="badversion")

    path = project.runtime / "governance.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    if version is None:
        del record["governanceVersion"]
    else:
        record["governanceVersion"] = version
    path.write_text(json.dumps(record, indent=2), encoding="utf-8",
                    newline="\n")

    project.write_artifact(".specify/memory/constitution.md")
    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "governance_record_invalid", result


def test_the_ledger_entry_names_the_gate_dispositions(project):
    """Delta 11: §15's gate evidence reaches the ledger. APPENDED to the end
    of the existing sentence, so every prefix assertion elsewhere still
    holds."""
    assert assess(project).exit_code == EXIT_OK
    project.ok("init", session="ledger")
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution")

    text = project.audit_file.read_text(encoding="utf-8")
    assert "Gate approvals this assessment requires: " in text
    assert "gate_security" in text
    assert "omittable: gate_analyze, gate_design, gate_tasks." in text
    assert project.ok("audit", "verify").data["matches"] is True


# --------------------------------------------------------------------------
# The driver — one walk of a real flow through the real CLI
# --------------------------------------------------------------------------
#
# Deliberately built on `test_units_flow_model.prepare`, which is already the
# suite's one description of what each generation phase produces. Restating it
# here would be a second source of truth for the same fact (invariant 7).


def bind_and_init(project, flow="GREENFIELD", level="LOW",
                  wi_type="enhancement", signals=(), session="policy") -> None:
    project.record_governance(
        classification={"type": wi_type, "flow": flow},
        risk={"signals": list(signals), "proposedLevel": level,
              "uncertainty": "LOW"})
    if flow == sdle.BASELINE_REQUIRING_FLOW and not (
            project.root / ".sdle" / "baseline.json").exists():
        project.establish_baseline()
    project.ok("init", session=session)


def resume(project, flow="GREENFIELD", omit=(), stop=None) -> list[str]:
    """Continue from the current phase.

    ``omit`` names gates to pass with `gate omit`; ``stop`` returns as soon as
    that phase is current, having done nothing to it.
    """
    consts = repo_consts()
    phases = list(consts.flow(flow).phases)
    feature_dir = project.feature_dir(FEATURE)
    seen: list[str] = []
    while True:
        phase = project.state()["current_phase"]
        if phase == "complete" or phase == stop:
            return seen
        prepare(project, phase, feature_dir)
        gate_key = consts.phase_to_gate_key.get(phase)
        if gate_key:
            review_for_gate(project, gate_key)
            project.ok("gate", "omit" if gate_key in omit else "approve",
                       "--gate", gate_key)
        else:
            project.ok("advance", "--to", phases[phases.index(phase) + 1])
        seen.append(project.state()["current_phase"])


def walk(project, flow="GREENFIELD", omit=(), stop=None, **bind) -> list[str]:
    bind_and_init(project, flow=flow, **bind)
    return ["requirements_check", project.state()["current_phase"]] + resume(
        project, flow=flow, omit=omit, stop=stop)


def ledger(project) -> str:
    return project.audit_file.read_text(encoding="utf-8")


def phase_of_gate(consts, gate_key: str) -> str:
    return next(phase for phase, key in consts.phase_to_gate_key.items()
                if key == gate_key)


# --------------------------------------------------------------------------
# N11 — the headline. §15's exit criterion, driven through the real CLI.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("level", ["HIGH", "CRITICAL"])
def test_n11_a_high_risk_workitem_cannot_skip_design_or_security(git_project,
                                                                 level):
    """N11/A5/A6/F1 — **the test this phase exists to pass.**

    At HIGH and above `gate_design` and `gate_security` are required, so:
    `gate omit` exits 1 `gate_required` and writes nothing to the ledger,
    `advance` past the gate exits 1 `gate_not_approved`, and the only way
    through is an explicit human approval.
    """
    walk(git_project, stop="gate_design", level=level)
    assert git_project.state()["current_phase"] == "gate_design"
    review_for_gate(git_project, "gate_design")

    before = ledger(git_project)
    refused = git_project.run("gate", "omit", "--gate", "gate_design")
    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "gate_required", refused
    assert f"risk:{level}" in refused.data["reasons"], refused
    assert refused.data["final_risk"] == level, refused
    assert ledger(git_project) == before, "a refusal must not touch the ledger"

    jumped = git_project.run("advance", "--to", "implement")
    assert jumped.exit_code == EXIT_REFUSED, jumped
    assert jumped.reason == "gate_not_approved", jumped
    assert ledger(git_project) == before

    git_project.ok("gate", "approve", "--gate", "gate_design")
    assert git_project.state()["current_phase"] == "implement"

    # ...and the same again at the terminal gate, which no level can omit.
    resume(git_project, stop="gate_security")
    review_for_gate(git_project, "gate_security")
    refused = git_project.run("gate", "omit", "--gate", "gate_security")
    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "gate_required", refused
    assert "terminal_gate" in refused.data["reasons"], refused

    git_project.ok("gate", "approve", "--gate", "gate_security")
    state = git_project.state()
    assert state["current_phase"] == "complete"
    recorded = {gate: entry["decision"]
                for gate, entry in state["approvals"].items() if entry}
    assert set(recorded.values()) == {"approved"}, recorded
    assert len(recorded) == 8


# --------------------------------------------------------------------------
# N12 — the same WorkItem at LOW: omittable means omittable
# --------------------------------------------------------------------------


def test_n12_a_low_risk_workitem_may_omit_design_but_not_security(git_project):
    """N12/A6/A9: the other half of §15's exit criterion. Design is omitted by
    an explicit, audited event; security still needs a human; every guardrail
    §15 names survives for the omitted gate."""
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")

    before_entries = len(audit_entries(git_project))
    omitted = git_project.ok("gate", "omit", "--gate", "gate_design")

    assert omitted.data["decision"] == "omitted_by_policy"
    assert omitted.data["final_risk"] == "LOW"
    assert omitted.data["next_phase"] == "implement"

    entry = git_project.state()["approvals"]["gate_design"]
    assert entry["decision"] == "omitted_by_policy"
    assert entry["risk_level"] == "LOW"
    assert entry["reasons"] == []
    assert "policy_sha256" in entry
    assert entry["timestamp"]
    # The artifact SHA is baselined exactly as an approval baselines it.
    assert (git_project.state()["artifact_shas"]["gate_design"]
            == omitted.data["sha"])

    blocks = [b for b in audit_entries(git_project) if "gate_omitted" in b]
    assert len(blocks) == 1, blocks
    assert "No human approved this gate" in blocks[0]
    assert "gate_design" in blocks[0]
    assert "OMITTED" in blocks[0]
    assert len(audit_entries(git_project)) > before_entries
    assert git_project.ok("audit", "verify").data["matches"] is True

    # ...and the run still cannot finish without a human at the last gate.
    resume(git_project, stop="gate_security")
    review_for_gate(git_project, "gate_security")
    assert git_project.run("gate", "omit",
                           "--gate", "gate_security").reason == "gate_required"
    git_project.ok("gate", "approve", "--gate", "gate_security")

    state = git_project.state()
    assert state["current_phase"] == "complete"
    assert state["approvals"]["gate_security"]["decision"] == "approved"
    assert state["approvals"]["gate_design"]["decision"] == "omitted_by_policy"
    assert next(e["outcome"] for e in state["phase_history"]
                if e["phase"] == "gate_design") == "omitted_by_policy"


def test_n22_the_completion_record_says_the_gate_was_omitted(git_project):
    """N22: `state dump` prints the recorded decision, so an omission is
    visible where a human reads the run, and `all_gates_approved` stops
    claiming something this run did not do."""
    walk(git_project, omit=("gate_design",), level="LOW")
    assert git_project.state()["current_phase"] == "complete"

    summary = json.loads((git_project.runtime / "completion-summary.json")
                         .read_text(encoding="utf-8"))
    assert summary["all_gates_approved"] is False

    dump = git_project.ok("state", "dump").data["rendered"]
    assert "| gate_design | omitted_by_policy |" in dump

    assert "gate_omitted" in ledger(git_project)
    assert git_project.ok("audit", "verify").data["matches"] is True


def test_a_run_that_approves_everything_still_reads_all_gates_approved(
        git_project):
    """The other half of N22, and the reason the frozen happy path is
    unaffected: the field is derived, and for a run that approved every gate
    it derives to exactly what it always said."""
    walk(git_project, level="LOW")
    summary = json.loads((git_project.runtime / "completion-summary.json")
                         .read_text(encoding="utf-8"))
    assert summary["all_gates_approved"] is True


# --------------------------------------------------------------------------
# N13 — no omission can reach the completion or baseline branch
# --------------------------------------------------------------------------


@pytest.mark.parametrize("flow,level", [("GREENFIELD", "LOW"),
                                        ("HOTFIX", "LOW"),
                                        ("HOTFIX", "CRITICAL")])
def test_n13_the_terminal_gate_is_never_omittable_through_the_cli(
        git_project, flow, level):
    """N13/D4/A7: driven through the CLI for two flows. The same property for
    all five flows at all four levels is asserted over the model itself by
    `test_n2_the_terminal_gate_is_required_everywhere`."""
    walk(git_project, flow=flow, level=level, stop="gate_security")
    review_for_gate(git_project, "gate_security")

    before = ledger(git_project)
    refused = git_project.run("gate", "omit", "--gate", "gate_security")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "gate_required", refused
    assert "terminal_gate" in refused.data["reasons"], refused
    assert ledger(git_project) == before
    assert not (git_project.runtime / "completion-summary.json").exists()


def test_hotfix_cannot_omit_any_of_its_three_gates(git_project):
    """A7: "shorter but never ungoverned", driven rather than asserted."""
    bind_and_init(git_project, flow="HOTFIX", level="LOW")
    consts = repo_consts()
    for gate_key in consts.flow("HOTFIX").gate_keys:
        resume(git_project, flow="HOTFIX",
               stop=phase_of_gate(consts, gate_key))
        review_for_gate(git_project, gate_key)
        refused = git_project.run("gate", "omit", "--gate", gate_key)
        assert refused.exit_code == EXIT_REFUSED, (gate_key, refused)
        assert refused.reason == "gate_required", (gate_key, refused)
        git_project.ok("gate", "approve", "--gate", gate_key)
    assert git_project.state()["current_phase"] == "complete"


# --------------------------------------------------------------------------
# N15/N16 — a recorded omission is re-derived, never trusted
# --------------------------------------------------------------------------


def test_n15_a_hand_written_omission_for_a_required_gate_is_refused(
        git_project):
    """N15/D9/A8: the choke-point refusal is the guarantee. Editing
    `state.json` by hand cannot buy a pass, and the refusal writes nothing."""
    walk(git_project, stop="gate_design", level="HIGH")
    state = git_project.state()
    state["approvals"]["gate_design"] = {
        "decision": "omitted_by_policy", "comments": None,
        "timestamp": "2020-01-01T00:00:00Z", "risk_level": "LOW",
        "reasons": [], "policy_sha256": None}
    git_project.write_state(state)

    before = ledger(git_project)
    refused = git_project.run("advance", "--to", "implement")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "gate_omission_invalidated", refused
    assert refused.data["gate"] == "gate_design"
    assert "gate_design" in refused.data["required_gates"]
    assert ledger(git_project) == before


def test_n16_an_omission_is_revalidated_at_the_terminal_gate(git_project):
    """N16/D10/A8: an omission recorded at LOW must not survive a later
    re-assessment that raised the level. Gates already passed are never
    revisited, so the check lives where the run is declared finished."""
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")
    git_project.ok("gate", "omit", "--gate", "gate_design")

    resume(git_project, stop="gate_security")
    # Re-assess the same flow at HIGH: `gate_design` is now required.
    git_project.record_governance(
        classification={"type": "enhancement", "flow": "GREENFIELD"},
        risk={"signals": [], "proposedLevel": "HIGH", "uncertainty": "LOW"})
    review_for_gate(git_project, "gate_security")

    before = ledger(git_project)
    refused = git_project.run("gate", "approve", "--gate", "gate_security")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "gate_omission_invalidated", refused
    assert refused.data["invalidated"] == ["gate_design"], refused
    assert ledger(git_project) == before
    assert not (git_project.runtime / "completion-summary.json").exists()
    assert git_project.state()["current_phase"] == "gate_security"


# --------------------------------------------------------------------------
# N17/N18 — a repository can always tighten; the legacy rung cannot omit
# --------------------------------------------------------------------------


def test_n17_an_override_can_make_every_gate_universal_again(git_project):
    """N17: the escape hatch that makes T09 safe to adopt. A repository that
    wants the pre-T09 behaviour adds the omittable gates to the policy, and
    every `gate omit` is refused."""
    write_policy(git_project, {"required_gates_always":
                               list(BUILTIN["required_gates_always"])
                               + ["gate_tasks", "gate_analyze",
                                  "gate_design"]})
    walk(git_project, stop="gate_tasks", level="LOW")

    review_for_gate(git_project, "gate_tasks")
    refused = git_project.run("gate", "omit", "--gate", "gate_tasks")
    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "gate_required", refused
    assert "always" in refused.data["reasons"], refused

    assert git_project.ok("governance", "gates").data["omittable_gates"] == []


def test_n18_the_legacy_runtime_can_never_omit_a_gate(bare_project):
    """N18/A12/D8: the transitional `.workflow/` rung has no WorkItem and
    therefore no governance record, so nothing there can be shown to be
    unnecessary. Refused — and the legacy traversal itself is unchanged."""
    template = json.loads(
        (bare_project.skill_root / "templates" / "state.json").read_text(
            encoding="utf-8"))
    legacy = bare_project.root / ".workflow"
    legacy.mkdir()

    def write_legacy(phase: str) -> None:
        template["current_phase"] = phase
        (legacy / "state.json").write_text(
            json.dumps(template, indent=2) + "\n", encoding="utf-8",
            newline="\n")

    write_legacy("gate_design")
    assert bare_project.workitem is None, "rung 3 needs zero WorkItems"

    refused = bare_project.run("gate", "omit", "--gate", "gate_design")
    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "governance_workitem_required", refused

    # The legacy traversal itself still works exactly as it did.
    write_legacy("requirements_check")
    assert bare_project.run("advance",
                            "--to", "constitution_draft").exit_code == EXIT_OK


# --------------------------------------------------------------------------
# N19/N20 — every §15 "preserve" guardrail survives an omission
# --------------------------------------------------------------------------


def test_n19_an_omitted_gate_keeps_drift_protection(git_project):
    """N19/D11/F2/A9 — **the most likely silent regression in this phase.**
    `compute_drift` used to filter on `decision == "approved"`; left that way,
    an omitted gate's artifact could change afterwards with nothing raised."""
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")
    git_project.ok("gate", "omit", "--gate", "gate_design")

    assert git_project.ok("drift", "check").data["drifted"] == []
    git_project.write_artifact("design/app/app-design.md",
                               "# Rewritten after the omission\n\n" + "x " * 80)

    drifted = git_project.ok("drift", "check").data["drifted"]
    assert [d["gate"] for d in drifted] == ["gate_design"], drifted
    assert drifted[0]["path"] == "design/app/app-design.md"


def test_an_omission_counts_as_a_reference_point_for_staleness(git_project):
    """The same re-pointing, for `repo-staleness`: the omission carries a
    timestamp and a baselined artifact, so it is a real reference point."""
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")
    git_project.ok("gate", "omit", "--gate", "gate_design")

    state = git_project.state()
    assert {k for k, v in state["approvals"].items()
            if v and v["decision"] == "approved"}, "setup sanity"
    stale = git_project.ok("repo-staleness").data
    assert stale["newest_approval"] is not None


def test_the_staleness_reader_would_see_an_omission_alone(git_project):
    """Sharper than the test above, which is satisfied by the approvals taken
    before the omission: with ONLY an omission recorded, the reader must still
    find a reference point."""
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")
    git_project.ok("gate", "omit", "--gate", "gate_design")

    state = git_project.state()
    omission = state["approvals"]["gate_design"]
    for key in list(state["approvals"]):
        state["approvals"][key] = omission if key == "gate_design" else None
    git_project.write_state(state)

    stale = git_project.ok("repo-staleness").data
    assert stale["newest_approval"] == omission["timestamp"], stale


def test_n20_gate_omit_refuses_a_missing_artifact(git_project):
    """N20/A9: an omission is still a decision about specific content."""
    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")
    (git_project.root / "design" / "app" / "app-design.md").unlink()

    before = ledger(git_project)
    refused = git_project.run("gate", "omit", "--gate", "gate_design")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "artifact_missing", refused
    assert ledger(git_project) == before


def test_n20_gate_omit_does_not_relax_tp_011(git_project):
    """N20/A9: §12 — review/validation is universal for governed artifacts.
    An unreviewed artifact cannot be omitted any more than it can be
    approved."""
    walk(git_project, stop="gate_design", level="LOW")

    before = ledger(git_project)
    refused = git_project.run("gate", "omit", "--gate", "gate_design")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "review_missing", refused
    assert ledger(git_project) == before

    # A FAILED review is refused too, so "reviewed" cannot mean "looked at".
    # `artifact review` is itself an audited event, so the byte comparison is
    # re-anchored after it: what must not move is the ledger across the
    # REFUSAL, not across the review that set it up.
    review_for_gate(git_project, "gate_design", result="FAIL")
    before = ledger(git_project)
    failed = git_project.run("gate", "omit", "--gate", "gate_design")
    assert failed.exit_code == EXIT_REFUSED, failed
    assert failed.reason == "review_failed", failed
    assert ledger(git_project) == before


def test_the_implement_gate_evidence_is_unchanged_by_an_omission(git_project):
    """A9: the secrets scan, the test evidence and the implementation diff
    baseline are all reached through `gate_implement`, which is required at
    every level — so an omitted design gate changes nothing about them."""
    walk(git_project, omit=("gate_design",), level="LOW")
    state = git_project.state()
    assert state["approvals"]["gate_implement"]["decision"] == "approved"
    assert state["artifact_shas"]["gate_implement"]
    assert git_project.ok("audit", "verify").data["chain_ok"] is True


# --------------------------------------------------------------------------
# N21 — every new refusal leaves the ledger byte-identical (B1/NB-6)
# --------------------------------------------------------------------------


def test_n21_every_new_refusal_leaves_the_ledger_byte_identical(git_project):
    """N21/A8/F3. Four of the five sites in one run, so the ledger comparison
    is against a genuinely non-trivial file; the fifth
    (`gate_omission_invalidated` at the terminal gate) is asserted in N16, and
    the two review refusals in N20, all with the same byte comparison.

    A refusal that appended first would leave `audit verify` reporting a
    broken chain while still looking like a refusal — invariants 5 and 6.
    """
    walk(git_project, stop="gate_design", level="HIGH")
    review_for_gate(git_project, "gate_design")
    before = ledger(git_project)

    # 1. gate_required
    assert git_project.run("gate", "omit",
                           "--gate", "gate_design").reason == "gate_required"
    assert ledger(git_project) == before

    # 2. gate_omission_invalidated at `apply_advance`
    state = git_project.state()
    state["approvals"]["gate_design"] = {
        "decision": "omitted_by_policy", "comments": None,
        "timestamp": "2020-01-01T00:00:00Z"}
    git_project.write_state(state)
    assert git_project.run(
        "advance", "--to", "implement").reason == "gate_omission_invalidated"
    assert ledger(git_project) == before

    # 3. artifact_missing on `gate omit`, at a level where the gate really is
    #    omittable, so the refusal reached is genuinely the artifact one.
    state["approvals"]["gate_design"] = None
    git_project.write_state(state)
    git_project.record_governance(
        classification={"type": "enhancement", "flow": "GREENFIELD"},
        risk={"signals": [], "proposedLevel": "LOW", "uncertainty": "LOW"})
    before = ledger(git_project)
    (git_project.root / "design" / "app" / "app-design.md").unlink()
    assert git_project.run(
        "gate", "omit", "--gate", "gate_design").reason == "artifact_missing"
    assert ledger(git_project) == before

    # 4. not_at_gate
    assert git_project.run("gate", "omit",
                           "--gate", "gate_spec").reason == "not_at_gate"
    assert ledger(git_project) == before
    assert git_project.ok("audit", "verify").data["matches"] is True


# --------------------------------------------------------------------------
# N23 — one producer, and no way to argue with it
# --------------------------------------------------------------------------


def test_n23_the_omission_decision_has_exactly_one_writer():
    """N23/F8: a second producer would be a second policy. Asserted by AST
    over the engine, so a new one fails here rather than in review."""
    tree = ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))
    writers = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Dict):
                continue
            for key, value in zip(node.keys, node.values):
                if (isinstance(key, ast.Constant) and key.value == "decision"
                        and isinstance(value, ast.Name)
                        and value.id == "GATE_OMITTED_DECISION"):
                    writers.add(fn.name)
    assert writers == {"cmd_gate_omit"}, writers


def test_gate_omit_has_no_force_or_override_flag():
    """F8/D17: any operator-supplied way past `gate_required` would be the
    exception mechanism §15's "casually skippable" forbids. The subcommand
    takes `--gate` and nothing else."""
    source = Path(SDLE_PY).read_text(encoding="utf-8")
    block = source[source.index('gate_sub.add_parser(\n        "omit"'):]
    block = block[:block.index("rejected_p =")]
    assert block.count("add_argument") == 1, block
    assert '"--gate"' in block
    for banned in ("--force", "--reason", "--override", "--acknowledge"):
        assert banned not in block, banned


def test_gate_omit_is_not_a_runtime_free_command():
    """It moves a phase, so it resolves a WorkItem like every other lifecycle
    command."""
    assert "gate" not in sdle.RUNTIME_FREE_COMMANDS


def test_gate_omit_is_branch_critical():
    """It advances the lifecycle and fingerprints working-tree content, which
    is exactly the criterion `BRANCH_CRITICAL_ACTIONS` states."""
    assert ("gate", "omit") in sdle.BRANCH_CRITICAL_ACTIONS


def test_the_decision_vocabulary_is_closed_and_distinguishable():
    """D3: `omitted_by_policy` is not `approved`, and nothing may blur them."""
    assert sdle.GATE_OMITTED_DECISION == "omitted_by_policy"
    assert sdle.BASELINED_GATE_DECISIONS == ("approved", "omitted_by_policy")
    assert sdle.GATE_DISPOSITIONS == ("required", "omittable", "not_in_flow")


def test_no_new_way_past_a_gate_was_added_to_advance_or_skip():
    """A16/F8: `advance` accepts exactly two decisions at a gate, and `skip`
    is untouched — it is still the failed-step recovery it always was, not a
    second omission path."""
    tree = ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))
    advance = next(fn for fn in ast.walk(tree)
                   if isinstance(fn, ast.FunctionDef)
                   and fn.name == "apply_advance")
    accepted = {node.value for node in ast.walk(advance)
                if isinstance(node, ast.Constant) and node.value == "approved"}
    assert accepted == {"approved"}
    names = {node.id for node in ast.walk(advance) if isinstance(node, ast.Name)}
    assert "GATE_OMITTED_DECISION" in names

    skip = next(fn for fn in ast.walk(tree)
                if isinstance(fn, ast.FunctionDef) and fn.name == "cmd_skip")
    leaked = {node.id for node in ast.walk(skip)
              if isinstance(node, ast.Name)} & {
        "GATE_OMITTED_DECISION", "gate_requirements",
        "gate_requirements_for_state", "required_gate_set"}
    assert not leaked, leaked


# --------------------------------------------------------------------------
# N27-N31 — absence of change, asserted on content rather than on Git
# --------------------------------------------------------------------------
#
# `git show` emits LF and the working tree is CRLF, so every comparison below
# normalises line endings before concluding a file differs. A byte comparison
# that reported the whole repository as changed on Windows would prove
# nothing and would be believed.

ROLLBACK = "e1cf341"


def at_rollback(relative: str) -> str | None:
    """The file's content at the T08 implementation commit, or None."""
    result = subprocess.run(
        ["git", "show", f"{ROLLBACK}:{relative}"],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return None
    return result.stdout.replace("\r\n", "\n")


def here(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(
        encoding="utf-8").replace("\r\n", "\n")


FROZEN_FILES = (
    "tests/test_integration_01_happy_path.py",
    ".claude/skills/sdle/templates/state.json",
    ".claude/settings.json",
    ".gitignore",
)


def test_the_rollback_point_is_reachable():
    """Non-vacuity guard: if `git show` failed for every path the two tests
    below would pass by comparing None to None."""
    assert at_rollback("scripts/sdle.py") is not None
    assert at_rollback("tests/test_integration_01_happy_path.py") is not None


@pytest.mark.parametrize("relative", FROZEN_FILES)
def test_n27_n28_the_frozen_files_are_byte_identical_to_the_rollback_point(
        relative):
    """N27/N28/A10/A11/F6: the design exists precisely so these need not
    change. `run_happy_path` approves every gate, which is always permitted,
    so the frozen driver is a valid run at every risk level."""
    original = at_rollback(relative)
    assert original is not None, relative
    assert here(relative) == original, relative


def test_n27_the_nine_dry_run_transcripts_are_byte_identical():
    """A11: the transcripts are the behavioural specification. A run that
    approves all eight gates is still a valid run.

    The directory holds ten Markdown files — the nine numbered transcripts and
    its own README. The count guard is on the nine, because that is the number
    the contract and the plan name and a transcript quietly disappearing is
    what it exists to catch; every file in the directory is compared, so the
    README cannot drift unnoticed either."""
    directory = REPO_ROOT / "docs" / "dry-runs"
    every = sorted(directory.glob("*.md"))
    numbered = [p for p in every if p.name[:2].isdigit()]
    assert len(numbered) == 9, [p.name for p in every]
    for path in every:
        relative = path.relative_to(REPO_ROOT).as_posix()
        original = at_rollback(relative)
        assert original is not None, relative
        assert here(relative) == original, relative


def test_n28_the_hooks_are_byte_identical():
    """A10: hooks are tripwires and T09 added no fence. Whole directory, so a
    new hook file would fail here rather than pass unnoticed."""
    hooks = sorted((REPO_ROOT / ".claude" / "hooks").rglob("*"))
    present = sorted(p.relative_to(REPO_ROOT).as_posix()
                     for p in hooks if p.is_file())
    assert present, "the hooks directory has gone missing"
    for relative in present:
        original = at_rollback(relative)
        assert original is not None, relative
        assert here(relative) == original, relative


def test_n28_the_state_schema_did_not_move(project):
    """A10: no state field, no migration row, no version bump, eight approval
    keys. The requirement set is derived at every decision point and stored
    nowhere, so there was nothing to migrate."""
    consts = repo_consts()
    assert len(consts.version_chain) == 16

    template = json.loads(
        (project.skill_root / "templates" / "state.json").read_text(
            encoding="utf-8"))
    assert len(template["approvals"]) == 8
    assert set(template["approvals"]) == set(consts.phase_to_gate_key.values())
    assert all(value is None for value in template["approvals"].values())

    # The version string itself, at the two locations a WorkItem runtime can
    # see. `version_string_consistent` covers all four and is exercised over a
    # repo copy by `test_lint_skill.py`; this is the half T09 could have moved.
    assert template["workflow_version"] == "1.16"
    assert "v1.16" in (project.skill_root / "SKILL.md").read_text(
        encoding="utf-8")
    assert consts.version_chain[-1][1] == "1.16"


def test_n29_the_frozen_greenfield_tuple_and_every_flow_are_unchanged():
    """A13: T07 owns which phases execute and T09 changed none of it."""
    assert len(sdle.GREENFIELD_V1_PHASES) == 19
    assert sdle.GREENFIELD_V1_PHASES[-1] == "complete"

    consts = repo_consts()
    assert "GREENFIELD" not in consts.flow_phases, (
        "GREENFIELD is derived, never a FLOW_PHASES row")

    # Element-wise against the rollback point, read out of that commit's own
    # SKILL.md rather than restated here.
    skill = at_rollback(".claude/skills/sdle/SKILL.md")
    assert skill is not None
    for name in sdle.ENGINEERING_FLOWS:
        if name == "GREENFIELD":
            assert list(consts.flow(name).phases) == list(
                sdle.GREENFIELD_V1_PHASES)
            continue
        prefix = f"| `{name}` | "
        row = next(line for line in skill.splitlines()
                   if line.startswith(prefix))
        declared = row.split("|")[2].split()
        assert list(consts.flow(name).phases) == declared, name


def test_n30_the_policy_needle_count_is_what_this_phase_left_it():
    """N30/A14/F5/I6: the restatement search picks the five new signals up
    automatically. Pinned so a *shrinking* needle set — which would make the
    search weaker while still passing — fails here."""
    from test_units_governance import policy_identifiers
    needles = policy_identifiers()
    assert len(sdle.GOVERNANCE_POLICY_BUILTIN["risk_signals"]) == 17
    underscored = {c for c in sdle.GOVERNANCE_POLICY_BUILTIN["quality_checks"]
                   if "_" in c}
    assert needles == set(
        sdle.GOVERNANCE_POLICY_BUILTIN["risk_signals"]) | underscored
    assert len(needles) == 17 + len(underscored)


def test_n30_adr_006_exists_and_names_no_policy_identifier():
    """A20/F5: `docs/architecture` is inside the restatement search, so the
    ADR describes the floors in prose that names no identifier. Asserted here
    as well, so the reason is attributable to this file rather than to a
    generic search failure."""
    from test_units_governance import policy_identifiers
    path = (REPO_ROOT / "docs" / "architecture"
            / "ADR-006-risk-adaptive-gate-policy.md")
    assert path.is_file(), "ADR-006 is required by A20"
    body = path.read_text(encoding="utf-8")
    assert sorted(n for n in policy_identifiers() if n in body) == []


def test_n30_adr_006_states_both_halves_of_the_guarantee():
    """A20: what the engine guarantees about an omission AND what it does not.
    A guarantee stated without its qualifier is the T08 NB-3 failure mode.

    Whitespace is collapsed first: the ADR is hard-wrapped prose, so a
    sentence spanning a line break is still the document saying it, and an
    assertion that a reflow could silently defeat would be checking the
    wrapping rather than the claim."""
    body = " ".join((REPO_ROOT / "docs" / "architecture"
                     / "ADR-006-risk-adaptive-gate-policy.md").read_text(
                         encoding="utf-8").split())
    assert "**Guaranteed.**" in body
    assert "**Not guaranteed.**" in body
    assert "could **not** have been chosen for a gate the policy required" \
        in body
    assert "cannot tell whether a human being or the orchestrator issued" \
        in body


def test_a19_the_unqualified_readme_clause_is_gone():
    """A19/D16/T08 NB-3: the exact string no longer appears, and what replaced
    it names the qualifier."""
    body = here("README.md")
    assert "so an inference can never be read as an observation" not in body
    assert "What it cannot check is whether the author applied the right label" \
        in body


def test_n31_no_t10_or_t11_leakage():
    """A24: T10 owns subagents and progressive skills; T11 owns the legacy
    rung, the version bump and the fixed-8-gate prose. None of it moved."""
    # `.claude/agents/` exists and holds the migration control-plane agents
    # that are driving this transition. The plan's scope exclusion names them
    # explicitly as scaffolding rather than evidence of T10, so the assertion
    # that matters is that no PRODUCT subagent has appeared beside them.
    agents = sorted(p.name for p in (REPO_ROOT / ".claude" / "agents").iterdir()
                    if p.is_file())
    assert agents, "the control-plane agents have gone missing"
    stray = [name for name in agents if not name.startswith("sdle-transition-")]
    assert stray == [], stray

    # The product skill is still exactly one, undivided. `apply-sdle-transition`
    # beside it is the migration control plane — the skill running this
    # transition — and is excluded by name rather than by pattern so a second
    # control-plane skill could not sneak a product split in with it.
    skills = sorted(p.name for p in
                    (REPO_ROOT / ".claude" / "skills").iterdir() if p.is_dir())
    assert skills == ["apply-sdle-transition", "sdle"], skills
    modules = sorted(p.name for p in (REPO_ROOT / ".claude" / "skills" / "sdle"
                                      / "modules").glob("*.md"))
    assert modules == ["gate-protocol.md", "phase-execution.md",
                       "security-review.md"], modules

    # T11's transitional surfaces, still present and still T11's.
    source = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
    assert "legacy_workflow" in source
    assert "current_feature_id" in source
    assert "SDLE_OWNED_PREFIXES" in source
    assert ".sdle" not in sdle.SDLE_OWNED_PREFIXES, (
        "T04 N-7 / T05 NB-7(b) is T11's, not T09's")


def test_n31_the_legacy_rung_and_migrate_workflow_are_untouched(bare_project):
    """A12: legacy dual-read still binds with no WorkItem registered, and
    `migrate-workflow` still leaves `.workflow/` byte-for-byte untouched."""
    template = json.loads(
        (bare_project.skill_root / "templates" / "state.json").read_text(
            encoding="utf-8"))
    template["current_phase"] = "requirements_check"
    legacy = bare_project.root / ".workflow"
    legacy.mkdir()
    (legacy / "state.json").write_text(json.dumps(template, indent=2) + "\n",
                                       encoding="utf-8", newline="\n")
    (legacy / "audit.md").write_text("# Audit\n", encoding="utf-8",
                                     newline="\n")

    before = {p.name: sdle.sha256_file(p) for p in sorted(legacy.iterdir())}
    assert bare_project.run("state", "get",
                            "--field", "current_phase").exit_code == EXIT_OK

    bare_project.ok("workitem", "create", "--name", "migrated thing")
    wid = bare_project.run("workitem", "list").data["workitems"][-1]["id"]
    assert bare_project.run("migrate-workflow", "--workitem",
                            wid).exit_code == EXIT_OK
    after = {p.name: sdle.sha256_file(p) for p in sorted(legacy.iterdir())}
    assert after == before, "migrate-workflow must never mutate .workflow/"


def test_a15_no_speckit_name_leaked_into_the_prompt_layer():
    """Invariant 3: the two files T09 edited in the prompt layer must not have
    gained a `speckit-*` name or a `/speckit.*` command."""
    for relative in (".claude/skills/sdle/SKILL.md",
                     ".claude/skills/sdle/modules/gate-protocol.md",
                     ".claude/commands/sdle-approve.md"):
        original = (at_rollback(relative) or "").splitlines()
        current = here(relative).splitlines()
        added = [line for line in current if line not in original]
        for line in added:
            assert "speckit-" not in line, (relative, line)
            assert "/speckit." not in line, (relative, line)
