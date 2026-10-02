"""ADR-013 — project architecture memory, placement and the architecture gate.

The catalog is the one piece of SDLE state that is *shared between WorkItems*,
so these tests are weighted toward the properties that only matter because of
that: optimistic revision control, idempotent replay, abandonment rather than
deletion, and a gate no policy can make optional.
"""

from __future__ import annotations

import json

import pytest

from conftest import Project, create_wi, sdle
from test_units_artifact_review import review_for_gate

CAPABILITY = "CAP-RISK-ASSESSMENT"
OWNER = "application-service"
TARGET = "risk-assessment-service"


# -- helpers ----------------------------------------------------------------


def proposal(revision: int = 0, outcome: str = "CREATE_NEW_SERVICE", **over):
    """A minimally valid proposal for ``outcome``, before any overrides."""
    dimensions = [
        {"dimension": name, "finding": f"Considered: {name}."}
        for name in sdle.ARCHITECTURE_REQUIRED_DIMENSIONS.get(outcome, ())
    ]
    placement = {
        "outcome": outcome,
        "capability": {"id": CAPABILITY, "name": "Risk Assessment",
                       "description": "Scoring a declaration's risk."},
        "currentOwner": None,
        "targetOwner": TARGET,
        "affectedServices": [],
        "dimensions": dimensions,
        "rationale": "Independent data, independent lifecycle.",
        "confidence": "HIGH",
    }
    placement.update(over.pop("placement", {}))
    document = {"architectureProposalVersion": "1",
                "baseArchitectureRevision": revision,
                "placement": placement}
    document.update(over)
    return document


def assess(view, document, expect_ok=True):
    name = "arch-input.json"
    (view.root / name).write_text(json.dumps(document, indent=2),
                                  encoding="utf-8", newline="\n")
    try:
        result = view.run("architecture", "assess", "--input", name)
    finally:
        (view.root / name).unlink()
    if expect_ok:
        assert result.ok, result
    return result


@pytest.fixture
def at_placement(started: Project) -> Project:
    """A GREENFIELD WorkItem standing at `architecture_placement`.

    Approving the constitution gate is what puts it there, and it is also what
    makes the constitution resolve PRESENT — which two of the five outcomes
    require.
    """
    started.write_artifact(".specify/memory/constitution.md")
    started.ok("advance", "--to", "gate_constitution")
    review_for_gate(started, "gate_constitution")
    started.ok("gate", "approve", "--gate", "gate_constitution")
    assert started.state()["current_phase"] == "architecture_placement"
    return started


def approve_placement(view) -> dict:
    shown = view.ok("gate", "show", "--gate", "gate_architecture").data
    view.ok("artifact", "review", "--path", shown["artifact_path"],
            "--type", "architecture-placement", "--result", "PASS",
            "--actor-type", "test", "--actor-name", "suite")
    view.ok("advance", "--to", "gate_architecture")
    return view.ok("gate", "approve", "--gate", "gate_architecture").data


def catalog_of(project: Project) -> dict:
    return json.loads(
        (project.root / ".sdle" / "architecture" / "catalog.json")
        .read_text(encoding="utf-8"))


# -- the catalog ------------------------------------------------------------


def test_an_empty_repository_reports_an_uninitialized_catalog(project: Project):
    shown = project.ok("architecture", "show").data
    assert shown["initialized"] is False
    assert shown["revision"] == 0
    assert shown["catalog"] is None


def test_show_needs_no_workitem(bare_project: Project):
    """The catalog is the repository's, so it is readable before any WorkItem
    exists — which is exactly when a new WorkItem wants to read it."""
    assert bare_project.ok("architecture", "show").data["initialized"] is False


def test_schema_writes_nothing_and_declares_the_closed_vocabulary(
        bare_project: Project):
    data = bare_project.ok("architecture", "schema").data
    assert data["outcomes"] == list(sdle.ARCHITECTURE_OUTCOMES)
    assert data["unresolved_outcome"] not in data["actionable_outcomes"]
    assert not (bare_project.root / ".sdle" / "architecture").exists()


def test_an_unreadable_catalog_is_an_integrity_failure_not_an_absence(
        project: Project):
    target = project.root / ".sdle" / "architecture" / "catalog.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("{not json", encoding="utf-8", newline="\n")
    result = project.run("architecture", "show")
    assert result.exit_code == 3
    assert result.reason == "architecture_catalog_invalid"


def test_an_unsupported_catalog_version_is_refused_and_left_alone(
        project: Project):
    target = project.root / ".sdle" / "architecture" / "catalog.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    before = json.dumps({**sdle.empty_architecture_catalog(),
                         "catalogVersion": 99}, indent=2) + "\n"
    target.write_text(before, encoding="utf-8", newline="\n")
    result = project.run("architecture", "show")
    assert result.exit_code == 3
    assert result.reason == "architecture_catalog_version_unsupported"
    assert target.read_text(encoding="utf-8") == before


def test_two_active_owners_for_one_datum_is_refused():
    catalog = sdle.empty_architecture_catalog()
    catalog["services"] = [
        {"serviceId": "a", "name": "a", "status": "IMPLEMENTED",
         "capabilities": [], "repositoryPaths": [], "ownedData": [],
         "dependencies": [], "decisionReference": None,
         "introducedBy": None},
        {"serviceId": "b", "name": "b", "status": "IMPLEMENTED",
         "capabilities": [], "repositoryPaths": [], "ownedData": [],
         "dependencies": [], "decisionReference": None,
         "introducedBy": None},
    ]
    catalog["dataOwnership"] = [
        {"data": "Risk", "ownerService": "a", "status": "ACTIVE",
         "viaCapability": None, "embedded": False,
         "decisionReference": None, "introducedBy": None},
        {"data": "Risk", "ownerService": "b", "status": "ACTIVE",
         "viaCapability": None, "embedded": False,
         "decisionReference": None, "introducedBy": None},
    ]
    with pytest.raises(sdle.Refused) as excinfo:
        sdle.validate_architecture_catalog(catalog, "catalog.json")
    assert excinfo.value.reason == "architecture_conflicting_ownership"


def test_a_duplicate_service_id_is_refused():
    catalog = sdle.empty_architecture_catalog()
    entry = {"serviceId": "a", "name": "a", "status": "PLANNED",
             "capabilities": [], "repositoryPaths": [], "ownedData": [],
             "dependencies": [], "decisionReference": None,
             "introducedBy": None}
    catalog["services"] = [entry, dict(entry)]
    with pytest.raises(sdle.IntegrityError):
        sdle.validate_architecture_catalog(catalog, "catalog.json")


# -- the placement phase ----------------------------------------------------


def test_the_constitution_gate_lands_on_architecture_placement(at_placement):
    assert at_placement.state()["current_phase"] == "architecture_placement"


def test_a_workitem_cannot_leave_the_phase_without_a_placement(at_placement):
    result = at_placement.run("advance", "--to", "gate_architecture")
    assert result.exit_code == 1
    assert result.reason == "architecture_placement_missing"


def test_skip_cannot_walk_past_the_phase_either(at_placement):
    """`skip` exists for a failed generation step. A specification written
    outside an approved boundary is what the phase exists to prevent, so the
    same refusal has to hold here."""
    state = at_placement.state()
    state["status"] = "failed"
    at_placement.write_state(state)
    at_placement.ok("skip")
    result = at_placement.run("skip", "--confirm")
    assert result.exit_code == 1
    assert result.reason == "architecture_placement_missing"


def test_an_unknown_outcome_is_refused(at_placement):
    result = assess(at_placement, proposal(outcome="MAKE_IT_MICRO"),
                    expect_ok=False)
    assert result.reason == "architecture_placement_invalid"


def test_an_unknown_service_is_refused(at_placement):
    result = assess(at_placement, proposal(
        outcome="EXTEND_EXISTING_SERVICE",
        placement={"currentOwner": "ghost", "targetOwner": "ghost"}),
        expect_ok=False)
    assert result.reason == "architecture_service_unknown"


def test_a_candidate_naming_an_unknown_capability_is_refused(at_placement):
    result = assess(at_placement, proposal(placement={"candidates": [
        {"id": "ARCH-CAND-001", "capability": "CAP-NOBODY-KNOWS",
         "currentOwner": TARGET, "reevaluateWhen": ["later"]}]}),
        expect_ok=False)
    assert result.reason == "architecture_capability_unknown"


def test_a_missing_required_dimension_is_refused(at_placement):
    document = proposal()
    document["placement"]["dimensions"] = document["placement"]["dimensions"][:1]
    result = assess(at_placement, document, expect_ok=False)
    assert result.reason == "architecture_placement_invalid"


def test_an_unknown_dimension_is_refused(at_placement):
    document = proposal()
    document["placement"]["dimensions"].append(
        {"dimension": "vibes", "finding": "feels separate"})
    result = assess(at_placement, document, expect_ok=False)
    assert result.reason == "architecture_placement_invalid"


def test_keep_embedded_needs_a_candidate_with_reevaluation_conditions(
        at_placement):
    document = proposal(
        outcome="KEEP_EMBEDDED_AND_MONITOR",
        placement={"currentOwner": OWNER, "targetOwner": None})
    document["bootstrapDelta"] = {
        "basis": "BASELINE",
        "services": [{"serviceId": OWNER, "name": OWNER,
                      "repositoryPaths": ["requirements"]}],
        "capabilities": [], "dataOwnership": [],
        "evidence": [{"statement": "the one component this fixture has",
                      "paths": ["requirements"]}],
    }
    result = assess(at_placement, document, expect_ok=False)
    assert result.reason == "architecture_placement_invalid"


def test_keep_embedded_records_a_candidate(at_placement):
    document = proposal(
        outcome="KEEP_EMBEDDED_AND_MONITOR",
        placement={"currentOwner": OWNER, "targetOwner": None,
                   "candidates": [{"id": "ARCH-CAND-004",
                                   "capability": CAPABILITY,
                                   "currentOwner": OWNER,
                                   "reevaluateWhen": [
                                       "a second risk WorkItem arrives"]}]})
    document["bootstrapDelta"] = {
        "basis": "BASELINE",
        "services": [{"serviceId": OWNER, "name": OWNER,
                      "repositoryPaths": ["requirements"]}],
        "capabilities": [], "dataOwnership": [],
        "evidence": [{"statement": "the one component this fixture has",
                      "paths": ["requirements"]}],
    }
    assess(at_placement, document)
    approve_placement(at_placement)
    catalog = catalog_of(at_placement)
    assert catalog["candidates"][0]["id"] == "ARCH-CAND-004"
    assert catalog["candidates"][0]["state"] == "OPEN"
    assert catalog["capabilities"][0]["status"] == "EMBEDDED"


def test_a_refused_assess_writes_nothing(at_placement):
    before = at_placement.audit_file.read_text(encoding="utf-8")
    assess(at_placement, proposal(outcome="MAKE_IT_MICRO"), expect_ok=False)
    assert not (at_placement.runtime / "architecture-placement.json").exists()
    assert at_placement.audit_file.read_text(encoding="utf-8") == before


def test_assess_records_the_record_the_rendering_and_the_evidence(at_placement):
    data = assess(at_placement, proposal()).data
    assert data["decisionId"].startswith("AP-")
    assert data["constitutionStatus"] == "PRESENT"
    assert (at_placement.runtime / "architecture-placement.json").is_file()
    rendered = at_placement.root / data["rendered"]
    assert rendered.is_file()
    body = rendered.read_text(encoding="utf-8")
    assert data["decisionId"] in body and data["proposalDigest"] in body
    assert (at_placement.root / data["evidence"]).is_file()


def test_the_rendering_is_the_gate_artifact(at_placement):
    data = assess(at_placement, proposal()).data
    shown = at_placement.ok("gate", "show", "--gate", "gate_architecture").data
    assert shown["artifact_path"] == data["rendered"]
    assert shown["exists"] is True


# -- the gate ---------------------------------------------------------------


def test_the_gate_is_required_at_every_risk_level(at_placement):
    shown = at_placement.ok("gate", "show", "--gate", "gate_architecture").data
    assert shown["required"] is True
    assert "architecture_gate" in shown["requirement_reasons"]


def test_no_policy_can_make_the_gate_omittable():
    """Exhaustive over the engine's own vocabulary rather than argued: the
    reason is derived inside `gate_requirements`, so a policy dictionary —
    which can only ever add — has no way to remove it."""
    consts = sdle.load_constants(sdle.resolve_paths(str(sdle.Path(__file__).resolve().parent.parent), None))
    for name in ("GREENFIELD",) + tuple(sdle.ENGINEERING_FLOWS):
        flow = consts.flow(name)
        for wi_type in sdle.WORKITEM_TYPES:
            for level in sdle.GOVERNANCE_LEVELS:
                model = sdle.gate_requirements(
                    consts, flow, {"type": wi_type, "flow": name}, level,
                    {"required_gates_always": [], "required_gates_by_risk": {},
                     "required_gates_by_type": {}})
                assert "gate_architecture" in model["required_gates"], (
                    name, wi_type, level)


def test_gate_omit_is_refused(at_placement):
    assess(at_placement, proposal())
    shown = at_placement.ok("gate", "show", "--gate", "gate_architecture").data
    at_placement.ok("artifact", "review", "--path", shown["artifact_path"],
                    "--type", "architecture-placement", "--result", "PASS",
                    "--actor-type", "test", "--actor-name", "suite")
    at_placement.ok("advance", "--to", "gate_architecture")
    result = at_placement.run("gate", "omit", "--gate", "gate_architecture")
    assert result.exit_code == 1
    assert result.reason == "gate_required"


def test_architecture_review_required_cannot_be_approved(at_placement):
    assess(at_placement, proposal(
        outcome="ARCHITECTURE_REVIEW_REQUIRED",
        placement={"openQuestions": ["Who owns the risk score?"],
                   "targetOwner": None}))
    shown = at_placement.ok("gate", "show", "--gate", "gate_architecture").data
    at_placement.ok("artifact", "review", "--path", shown["artifact_path"],
                    "--type", "architecture-placement", "--result", "PASS",
                    "--actor-type", "test", "--actor-name", "suite")
    at_placement.ok("advance", "--to", "gate_architecture")
    result = at_placement.run("gate", "approve", "--gate", "gate_architecture")
    assert result.exit_code == 1
    assert result.reason == "architecture_decision_unresolved"
    assert not (at_placement.root / ".sdle" / "architecture").exists()


def test_a_hand_edited_rendering_fails_the_binding(at_placement):
    data = assess(at_placement, proposal()).data
    rendered = at_placement.root / data["rendered"]
    at_placement.ok("artifact", "review", "--path", data["rendered"],
                    "--type", "architecture-placement", "--result", "PASS",
                    "--actor-type", "test", "--actor-name", "suite")
    at_placement.ok("advance", "--to", "gate_architecture")
    rendered.write_text(rendered.read_text(encoding="utf-8") + "\nedited\n",
                        encoding="utf-8", newline="\n")
    result = at_placement.run("gate", "approve", "--gate", "gate_architecture")
    assert result.exit_code == 1
    # Both guards fire on this; the review one is reached first because the
    # gate fingerprints before it applies. Either is a correct refusal — what
    # must never happen is the edit becoming architecture.
    assert result.reason in ("review_stale",
                             "architecture_artifact_binding_invalid")
    assert not (at_placement.root / ".sdle" / "architecture").exists()


def test_approval_applies_the_delta_and_advances_to_spec_draft(at_placement):
    assess(at_placement, proposal())
    moved = approve_placement(at_placement)
    assert moved["next_phase"] == "spec_draft"
    assert moved["architecture_applied"]["revision"] == 1

    catalog = catalog_of(at_placement)
    assert catalog["revision"] == 1
    assert [s["serviceId"] for s in catalog["services"]] == [TARGET]
    assert catalog["services"][0]["status"] == "PLANNED"
    assert catalog["capabilities"][0]["id"] == CAPABILITY
    decision = catalog["decisions"][0]
    assert decision["status"] == "APPROVED_PENDING_IMPLEMENTATION"
    assert decision["appliedRevision"] == 1


def test_a_stale_base_revision_is_refused_and_writes_nothing(at_placement):
    assess(at_placement, proposal())
    approve_placement(at_placement)
    before = catalog_of(at_placement)

    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    record = json.loads(
        paths.architecture_placement_file.read_text(encoding="utf-8"))
    other = dict(record, decisionId="AP-someone-else-001",
                 proposalDigest="sha256:other", baseRevision=0)
    with pytest.raises(sdle.Refused) as excinfo:
        sdle.architecture_apply(paths, other, sdle.now_iso())
    assert excinfo.value.reason == "architecture_catalog_stale"
    assert catalog_of(at_placement) == before


def test_applying_the_same_decision_again_is_an_idempotent_replay(at_placement):
    assess(at_placement, proposal())
    approve_placement(at_placement)
    before = catalog_of(at_placement)

    replay = at_placement.ok("architecture", "apply").data
    assert replay["replayed"] is True
    assert catalog_of(at_placement) == before


def test_the_same_id_with_a_different_digest_is_a_conflict(at_placement):
    assess(at_placement, proposal())
    approve_placement(at_placement)

    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    record = json.loads(
        paths.architecture_placement_file.read_text(encoding="utf-8"))
    with pytest.raises(sdle.Refused) as excinfo:
        sdle.architecture_apply(
            paths, dict(record, proposalDigest="sha256:tampered"),
            sdle.now_iso())
    assert excinfo.value.reason == "architecture_decision_conflict"


# -- constitution availability ----------------------------------------------


ABSENT = {"status": "ABSENT", "source": None, "path": None}


def known_catalog(owner=OWNER, datum="RiskAssessment"):
    catalog = sdle.empty_architecture_catalog()
    catalog["services"] = [{
        "serviceId": owner, "name": owner, "status": "IMPLEMENTED",
        "capabilities": [], "repositoryPaths": [], "ownedData": [],
        "dependencies": [], "decisionReference": None,
        "introducedBy": None}]
    catalog["dataOwnership"] = [{
        "data": datum, "ownerService": owner, "status": "ACTIVE",
        "viaCapability": None, "embedded": True,
        "decisionReference": None, "introducedBy": None}]
    return catalog


def enforce(outcome, *, technology=False, ownership=(), known=None,
            bootstrap=None, target=OWNER):
    sdle._enforce_constitution_rule(
        outcome, ABSENT, technology, list(ownership),
        known if known is not None else known_catalog(), bootstrap, target,
        "p.json")


@pytest.mark.parametrize("outcome", sdle.ARCHITECTURE_CONSTITUTION_REQUIRED)
def test_a_boundary_outcome_needs_a_constitution(outcome):
    with pytest.raises(sdle.Refused) as excinfo:
        enforce(outcome)
    assert excinfo.value.reason == "architecture_constitution_required"


def test_a_legacy_extension_is_permitted_without_a_constitution():
    enforce("EXTEND_EXISTING_SERVICE")


def test_but_not_when_it_introduces_a_technology_decision():
    with pytest.raises(sdle.Refused) as excinfo:
        enforce("EXTEND_EXISTING_SERVICE", technology=True)
    assert excinfo.value.reason == "architecture_constitution_required"


def test_a_bootstrap_declared_service_is_not_a_new_boundary():
    """A bootstrap describes architecture that already exists. Extending one
    of its services in a repository with no constitution is the legacy case
    ADR-014 permits, not a boundary this WorkItem established."""
    enforce("EXTEND_EXISTING_SERVICE", target="legacy-service",
            known=sdle.empty_architecture_catalog(),
            bootstrap={"services": [{"serviceId": "legacy-service"}]})


def test_nor_when_it_would_establish_a_new_boundary():
    """ADR-014 names three conditions, not one. Two of them the engine can
    derive for itself, and this is the first: a target the catalog does not
    have is a new service boundary whatever the outcome is called."""
    with pytest.raises(sdle.Refused) as excinfo:
        enforce("EXTEND_EXISTING_SERVICE", target="brand-new-service")
    assert excinfo.value.reason == "architecture_constitution_required"


def test_nor_when_it_would_transfer_ownership():
    """The third condition, derived from the delta against the current active
    owners rather than taken on trust."""
    moved = [{"data": "RiskAssessment", "ownerService": OWNER,
              "viaCapability": None, "embedded": False}]
    enforce("EXTEND_EXISTING_SERVICE", ownership=moved)  # same owner: fine

    catalog = known_catalog(owner="review-service")
    catalog["services"].append({
        "serviceId": OWNER, "name": OWNER, "status": "IMPLEMENTED",
        "capabilities": [], "repositoryPaths": [], "ownedData": [],
        "dependencies": [], "decisionReference": None,
        "introducedBy": None})
    with pytest.raises(sdle.Refused) as excinfo:
        enforce("EXTEND_EXISTING_SERVICE", ownership=moved, known=catalog)
    assert excinfo.value.reason == "architecture_constitution_required"


def test_review_required_is_always_recordable_without_one():
    """The escape hatch has to stay reachable, or a repository with no
    constitution has no honest answer at all."""
    enforce(sdle.ARCHITECTURE_UNRESOLVED_OUTCOME, technology=True,
            target="anything")


# -- bootstrap --------------------------------------------------------------


def test_bootstrap_evidence_must_cite_a_path_that_exists(at_placement):
    document = proposal()
    document["bootstrapDelta"] = {
        "basis": "BASELINE", "services": [], "capabilities": [],
        "dataOwnership": [],
        "evidence": [{"statement": "there is a service here",
                      "paths": ["services/imaginary"]}],
    }
    result = assess(at_placement, document, expect_ok=False)
    assert result.reason == "architecture_placement_invalid"


def test_bootstrap_is_refused_once_the_catalog_exists(project: Project):
    """Once the repository has a catalog, "what already exists" IS the
    catalog. Asserted on the validator rather than through a second gate run:
    the WorkItem that approved the first placement may not re-assess at all
    (see `test_reassessing_after_approval_is_refused`), so the end-to-end
    route to this refusal no longer exists for it."""
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(project.root), None), project.workitem)
    bootstrap = {
        "basis": "BASELINE", "services": [], "capabilities": [],
        "dataOwnership": [],
        "evidence": [{"statement": "x", "paths": ["requirements"]}],
    }
    # Uninitialized: accepted.
    assert sdle._validate_bootstrap_delta(
        bootstrap, paths, False, "p.json")["declared"] is True
    # Initialized: refused.
    with pytest.raises(sdle.Refused) as excinfo:
        sdle._validate_bootstrap_delta(bootstrap, paths, True, "p.json")
    assert excinfo.value.reason == "architecture_placement_invalid"


def test_a_legacy_repository_bootstraps_from_evidence(at_placement):
    at_placement.record_architecture()
    catalog = at_placement.ok("architecture", "show").data
    # Nothing is in the catalog until the gate approves — bootstrap included.
    assert catalog["initialized"] is False
    approve_placement(at_placement)
    catalog = catalog_of(at_placement)
    assert [s["serviceId"] for s in catalog["services"]] == ["fixture-service"]
    assert catalog["services"][0]["status"] == "IMPLEMENTED"
    assert catalog["revision"] == 1


# -- realization and abandonment --------------------------------------------


def test_realize_turns_a_planned_service_into_an_implemented_one(at_placement):
    assess(at_placement, proposal())
    approve_placement(at_placement)
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)

    result = sdle.architecture_realize(paths, sdle.now_iso())
    assert result["replayed"] is False
    catalog = catalog_of(at_placement)
    assert catalog["services"][0]["status"] == "IMPLEMENTED"
    assert catalog["decisions"][0]["status"] == "IMPLEMENTED"

    replay = sdle.architecture_realize(paths, sdle.now_iso())
    assert replay["replayed"] is True


def test_realize_supersedes_the_previous_owner_of_moved_data(at_placement):
    assess(at_placement, proposal(placement={
        "dataOwnership": [{"data": "RiskAssessment", "ownerService": TARGET}]}))
    approve_placement(at_placement)
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    assert catalog_of(at_placement)["dataOwnership"][0]["status"] == "PLANNED"
    sdle.architecture_realize(paths, sdle.now_iso())
    assert catalog_of(at_placement)["dataOwnership"][0]["status"] == "ACTIVE"


def test_restart_to_the_placement_phase_abandons_the_decision(at_placement):
    assess(at_placement, proposal())
    approve_placement(at_placement)
    index = at_placement.ok("flow", "show").data["phases"].index(
        "architecture_placement") + 1

    at_placement.ok("restart", "--to", index)
    at_placement.ok("restart", "--to", index, "--confirm")

    catalog = catalog_of(at_placement)
    decision = catalog["decisions"][0]
    assert decision["status"] == "ABANDONED"
    assert decision["abandonedBy"] == "restart"
    assert catalog["services"][0]["status"] == "WITHDRAWN"
    # History is appended to, never rewritten: the decision keeps its id and
    # the revision it was applied at.
    assert decision["appliedRevision"] == 1
    assert catalog["revision"] == 2


def test_reset_abandons_it_too_and_the_catalog_is_the_only_record(at_placement):
    """`reset` deletes `audit.md`, so the catalog disposition is all that
    survives — which is why it is written before the deletion."""
    assess(at_placement, proposal())
    approve_placement(at_placement)
    at_placement.ok("reset")
    at_placement.ok("reset", "--confirm")

    assert not at_placement.audit_file.exists()
    catalog = catalog_of(at_placement)
    assert catalog["decisions"][0]["status"] == "ABANDONED"
    assert catalog["decisions"][0]["abandonedBy"] == "reset"
    assert catalog["services"][0]["status"] == "WITHDRAWN"


def test_the_realize_command_needs_the_implementation_gate(at_placement):
    """Realization is a catalog mutation, so it rests on a human decision too
    - the implementation gate's. Without that check anyone holding the shell
    could flip a PLANNED service to IMPLEMENTED before the work was accepted."""
    assess(at_placement, proposal())
    approve_placement(at_placement)

    result = at_placement.run("architecture", "realize")
    assert result.exit_code == 1
    assert result.reason == "gate_required"
    assert catalog_of(at_placement)["services"][0]["status"] == "PLANNED"


def test_a_rejected_architecture_gate_cannot_be_applied_by_the_replay_verb(
        at_placement):
    """`gate reject` writes a truthy `{"decision": "rejected"}`. `apply` tested
    only that an entry existed, so a human's explicit rejection did not stop
    the replay verb from writing the rejected placement into the shared
    catalog. The test is the decision, never the presence of an entry."""
    assess(at_placement, proposal())
    shown = at_placement.ok("gate", "show", "--gate", "gate_architecture").data
    at_placement.ok("artifact", "review", "--path", shown["artifact_path"],
                    "--type", "architecture-placement", "--result", "PASS",
                    "--actor-type", "test", "--actor-name", "suite")
    at_placement.ok("advance", "--to", "gate_architecture")
    at_placement.ok("gate", "reject", "--gate", "gate_architecture",
                    "--reason", "Not yet.")

    result = at_placement.run("architecture", "apply")
    assert result.exit_code == 1
    assert result.reason == "gate_required"
    assert not (at_placement.root / ".sdle" / "architecture").exists()


def test_a_rejected_implementation_gate_cannot_realize_a_decision(
        at_placement):
    """The same defect on the other verb: a rejected `gate_implement` is a
    truthy approvals entry, and `realize` promoted PLANNED to IMPLEMENTED on
    it."""
    assess(at_placement, proposal())
    approve_placement(at_placement)
    state = at_placement.state()
    state["approvals"]["gate_implement"] = {
        "decision": "rejected", "comments": "no", "timestamp": "2026-01-01T00:00:00Z"}
    at_placement.state_file.write_text(
        json.dumps(state, indent=2), encoding="utf-8", newline="\n")

    result = at_placement.run("architecture", "realize")
    assert result.exit_code == 1
    assert result.reason == "gate_required"
    catalog = catalog_of(at_placement)
    assert catalog["services"][0]["status"] == "PLANNED"
    assert catalog["decisions"][0]["status"] == "APPROVED_PENDING_IMPLEMENTATION"


def _bootstrap(statement: str, paths: list[str]) -> dict:
    return {
        "basis": "BASELINE",
        "services": [{"serviceId": OWNER, "name": OWNER,
                      "repositoryPaths": ["requirements"]}],
        "capabilities": [], "dataOwnership": [],
        "evidence": [{"statement": statement, "paths": paths}],
    }


def test_the_proposal_digest_covers_the_bootstrap_delta(at_placement):
    """Replay safety tells an identical replay from a different decision by
    the digest. The bootstrap delta is applied to the shared catalog, so a
    digest that ignored it would call two different catalog mutations the
    same decision."""
    def digest_for(statement: str) -> str:
        document = proposal(
            outcome="KEEP_EMBEDDED_AND_MONITOR",
            placement={"currentOwner": OWNER, "targetOwner": None,
                       "candidates": [{"id": "ARCH-CAND-009",
                                       "capability": CAPABILITY,
                                       "currentOwner": OWNER,
                                       "reevaluateWhen": ["a second WorkItem"]}]})
        document["bootstrapDelta"] = _bootstrap(statement, ["requirements"])
        assess(at_placement, document)
        paths = sdle.bind_workitem(
            sdle.resolve_paths(str(at_placement.root), None),
            at_placement.workitem)
        return json.loads(paths.architecture_placement_file.read_text(
            encoding="utf-8"))["proposalDigest"]

    assert digest_for("the first thing observed") != digest_for(
        "a different thing observed"), (
        "two proposals differing only in bootstrapDelta share a digest")


def test_realize_refuses_a_decision_that_is_not_this_workitems_or_digest(
        at_placement):
    """Realization matched on the decision id alone, so a record whose digest
    no longer matched the applied decision - or a decision belonging to
    another WorkItem - was reported as a successful realization, and even as
    an idempotent replay once the decision was IMPLEMENTED."""
    assess(at_placement, proposal())
    approve_placement(at_placement)
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    before = (at_placement.root / ".sdle" / "architecture"
              / "catalog.json").read_bytes()

    record = json.loads(
        paths.architecture_placement_file.read_text(encoding="utf-8"))
    record["proposalDigest"] = "sha256:not-the-applied-one"
    paths.architecture_placement_file.write_text(
        json.dumps(record, indent=2), encoding="utf-8", newline="\n")
    state = at_placement.state()
    state["approvals"]["gate_implement"] = {
        "decision": "approved", "comments": "", "timestamp": "2026-01-01T00:00:00Z"}
    at_placement.state_file.write_text(
        json.dumps(state, indent=2), encoding="utf-8", newline="\n")

    result = at_placement.run("architecture", "realize")
    assert result.exit_code == 1
    assert result.reason == "architecture_decision_conflict"
    assert (at_placement.root / ".sdle" / "architecture"
            / "catalog.json").read_bytes() == before


def test_the_gated_rendering_discloses_every_bootstrap_value_it_applies(
        at_placement):
    """The human approves the rendering, and the catalog receives the
    structured delta. A bootstrap value the rendering leaves out is one the
    human never saw, so every field `apply` writes must appear in it."""
    document = proposal(
        outcome="KEEP_EMBEDDED_AND_MONITOR",
        placement={"currentOwner": OWNER, "targetOwner": None,
                   "candidates": [{"id": "ARCH-CAND-009",
                                   "capability": CAPABILITY,
                                   "currentOwner": OWNER,
                                   "reevaluateWhen": ["a second WorkItem"]}]})
    document["bootstrapDelta"] = {
        "basis": "BASELINE",
        "services": [{"serviceId": OWNER, "name": "Application Service",
                      "repositoryPaths": ["requirements"],
                      "capabilities": ["CAP-APPLICATION"],
                      "ownedData": ["Application"],
                      "dependencies": ["identity-provider"]}],
        "capabilities": [{"id": "CAP-APPLICATION", "name": "Applications",
                          "description": "Taking an application in.",
                          "status": "ESTABLISHED", "ownerService": OWNER}],
        "dataOwnership": [{"data": "Application", "ownerService": OWNER,
                           "viaCapability": "CAP-APPLICATION",
                           "embedded": False}],
        "evidence": [{"statement": "one component exists",
                      "paths": ["requirements"]}],
    }
    data = assess(at_placement, document).data
    rendered = (at_placement.root / data["rendered"]).read_text(
        encoding="utf-8")
    for value in ("Application Service", "CAP-APPLICATION", "Applications",
                  "Taking an application in.", "ESTABLISHED", "Application",
                  "identity-provider", "requirements"):
        assert value in rendered, f"{value!r} is applied but not rendered"
    section = rendered.split("## Existing architecture recorded at bootstrap")[1]
    assert "identity-provider" in section and "ownedData" not in section


def _two_competing_records(view) -> tuple[dict, dict, "sdle.Paths"]:
    """Two placements reasoned against the same revision, as two WorkItems
    would hold them, built from one real assessed record."""
    assess(view, proposal())
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(view.root), None), view.workitem)
    base = json.loads(
        paths.architecture_placement_file.read_text(encoding="utf-8"))
    first, second = dict(base), dict(base)
    first.update(decisionId="AP-wa-001", workitem="wa",
                 proposalDigest="sha256:first")
    second.update(decisionId="AP-wb-001", workitem="wb",
                  proposalDigest="sha256:second")
    return first, second, paths


def test_concurrent_applies_cannot_silently_overwrite_each_other(
        at_placement, monkeypatch):
    """Two WorkItems both read revision 0 and both pass `baseRevision == 0`;
    without the lock the second replacement erases the first decision and
    nothing says so. The read is slowed so the window is wide enough to hit
    every time."""
    import threading
    import time

    first, second, paths = _two_competing_records(at_placement)
    real_read = sdle.read_architecture_catalog

    def slow_read(p):
        catalog = real_read(p)
        time.sleep(0.4)
        return catalog

    monkeypatch.setattr(sdle, "read_architecture_catalog", slow_read)
    outcomes: dict[str, object] = {}

    def run(name: str, record: dict) -> None:
        try:
            outcomes[name] = sdle.architecture_apply(
                paths, record, sdle.now_iso())
        except sdle.Refused as refusal:
            outcomes[name] = refusal

    threads = [threading.Thread(target=run, args=("a", first)),
               threading.Thread(target=run, args=("b", second))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    refused = [v for v in outcomes.values() if isinstance(v, sdle.Refused)]
    applied = [v for v in outcomes.values() if isinstance(v, dict)]
    assert len(applied) == 1 and len(refused) == 1, outcomes
    assert refused[0].reason == "architecture_catalog_stale"
    catalog = catalog_of(at_placement)
    assert catalog["revision"] == 1
    assert [d["id"] for d in catalog["decisions"]] == [applied[0]["decision"]]
    assert not paths.architecture_lock_file.exists(), "the lock was left held"


def test_a_held_catalog_lock_is_a_refusal_not_a_hang(
        at_placement, monkeypatch):
    first, _second, paths = _two_competing_records(at_placement)
    monkeypatch.setattr(sdle, "ARCHITECTURE_LOCK_TIMEOUT", 0.2)
    paths.architecture_dir.mkdir(parents=True, exist_ok=True)
    paths.architecture_lock_file.write_text("held", encoding="utf-8")

    with pytest.raises(sdle.Refused) as raised:
        sdle.architecture_apply(paths, first, sdle.now_iso())

    assert raised.value.reason == "architecture_catalog_locked"
    assert not paths.architecture_catalog_file.exists()
    assert paths.architecture_lock_file.read_text(encoding="utf-8") == "held", (
        "a refused caller must not release a lock it never held")


def test_a_lock_left_by_a_dead_process_is_broken_once_stale(
        at_placement, monkeypatch):
    import os

    first, _second, paths = _two_competing_records(at_placement)
    monkeypatch.setattr(sdle, "ARCHITECTURE_LOCK_STALE_AFTER", 5.0)
    paths.architecture_dir.mkdir(parents=True, exist_ok=True)
    paths.architecture_lock_file.write_text("dead", encoding="utf-8")
    old = paths.architecture_lock_file.stat().st_mtime - 3600
    os.utime(paths.architecture_lock_file, (old, old))

    result = sdle.architecture_apply(paths, first, sdle.now_iso())

    assert result["replayed"] is False
    assert catalog_of(at_placement)["revision"] == 1
    assert not paths.architecture_lock_file.exists()


def test_the_lock_is_released_when_the_guarded_work_refuses(at_placement):
    first, _second, paths = _two_competing_records(at_placement)
    first["baseRevision"] = 7

    with pytest.raises(sdle.Refused) as raised:
        sdle.architecture_apply(paths, first, sdle.now_iso())

    assert raised.value.reason == "architecture_catalog_stale"
    assert not paths.architecture_lock_file.exists()


# -- the placement is bound to the requirements it was reasoned from --------


def _edit_bound_requirements(view) -> None:
    target = view.root / "requirements" / "todo-api.md"
    target.write_text(
        target.read_text(encoding="utf-8")
        + "\nA requirement added after the placement was assessed.\n",
        encoding="utf-8", newline="\n")


def _placement_record(view) -> dict:
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(view.root), None), view.workitem)
    return json.loads(
        paths.architecture_placement_file.read_text(encoding="utf-8"))


def _review_and_stand_at_gate(view) -> None:
    shown = view.ok("gate", "show", "--gate", "gate_architecture").data
    view.ok("artifact", "review", "--path", shown["artifact_path"],
            "--type", "architecture-placement", "--result", "PASS",
            "--actor-type", "test", "--actor-name", "suite")
    view.ok("advance", "--to", "gate_architecture")


def test_assess_records_the_requirements_the_placement_was_reasoned_from(
        at_placement):
    """The placement reads the bound requirements, so the record has to say
    which bytes it read: without that, nothing can tell a placement derived
    from the documents as they are from one derived from documents that have
    since changed."""
    assess(at_placement, proposal())
    record = _placement_record(at_placement)
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    sources, digest, _ = sdle.requirements_sources(paths)

    assert record["requirementsDigest"] == digest
    assert record["requirementsSources"] == sources


def test_a_requirements_edit_after_placement_refuses_the_gate(at_placement):
    """The case a shared-document edit makes real: the placement was derived
    from the old bytes, governance is re-assessed against the new ones, and
    nothing compared the two. Governance going stale is not enough, because
    re-assessing clears it and the old placement would then be approved."""
    assess(at_placement, proposal())
    _review_and_stand_at_gate(at_placement)
    _edit_bound_requirements(at_placement)
    at_placement.record_governance()
    audit_before = at_placement.audit_file.read_bytes()

    result = at_placement.run("gate", "approve", "--gate", "gate_architecture")

    assert result.exit_code == 1, result
    assert result.reason == "architecture_requirements_stale"
    assert result.data["changed"] == ["requirements/todo-api.md"]
    assert not (at_placement.root / ".sdle" / "architecture").exists()
    assert at_placement.audit_file.read_bytes() == audit_before, (
        "a refused approval must not touch the ledger")


def test_a_requirements_edit_is_caught_before_the_gate_is_reached(
        at_placement):
    """A human should not be shown a placement that is already known to be
    stale, so the refusal is raised on leaving the phase as well."""
    assess(at_placement, proposal())
    _edit_bound_requirements(at_placement)
    at_placement.record_governance()

    result = at_placement.run("advance", "--to", "gate_architecture")

    assert result.exit_code == 1, result
    assert result.reason == "architecture_requirements_stale"
    assert at_placement.state()["current_phase"] == "architecture_placement"


def test_re_running_the_placement_clears_the_staleness(at_placement):
    assess(at_placement, proposal())
    _review_and_stand_at_gate(at_placement)
    _edit_bound_requirements(at_placement)
    at_placement.record_governance()
    assert at_placement.run(
        "gate", "approve", "--gate", "gate_architecture").exit_code == 1

    fresh = assess(at_placement, proposal()).data
    shown = at_placement.ok("gate", "show", "--gate", "gate_architecture").data
    at_placement.ok("artifact", "review", "--path", shown["artifact_path"],
                    "--type", "architecture-placement", "--result", "PASS",
                    "--actor-type", "test", "--actor-name", "suite")
    at_placement.ok("gate", "approve", "--gate", "gate_architecture")

    assert catalog_of(at_placement)["revision"] == 1
    assert fresh["decisionId"] == catalog_of(at_placement)["decisions"][0]["id"]


def test_the_requirements_are_rechecked_inside_the_catalog_write(at_placement):
    """The gate hook checks the requirements at the start of the command and the
    catalog is written later. A bound document changing in between would let a
    stale placement in, so the basis is checked again under the catalog lock,
    immediately before the write - with no gate hook in front of this call."""
    assess(at_placement, proposal())
    record = _placement_record(at_placement)
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    _edit_bound_requirements(at_placement)

    with pytest.raises(sdle.Refused) as raised:
        sdle.architecture_apply(paths, record, sdle.now_iso())

    assert raised.value.reason == "architecture_requirements_stale"
    assert not paths.architecture_catalog_file.exists(), (
        "a refused apply must not write the catalog")
    assert not paths.architecture_lock_file.exists(), "the lock was left held"


def test_the_recheck_runs_while_the_catalog_lock_is_held(
        at_placement, monkeypatch):
    """The test above shows a stale placement is refused. This one pins *where*:
    the recheck must run while the catalog lock is held, immediately before the
    write. A recheck moved to just before the lock is taken would still refuse
    in the sequential case and leave the window open, so the lock's presence is
    observed at the moment the precondition runs."""
    assess(at_placement, proposal())
    record = _placement_record(at_placement)
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    seen = []
    real = sdle.architecture_requirements_precondition

    def observed(p, r):
        seen.append(p.architecture_lock_file.exists())
        return real(p, r)

    monkeypatch.setattr(sdle, "architecture_requirements_precondition", observed)

    sdle.architecture_apply(paths, record, sdle.now_iso())

    assert seen == [True], (
        "the requirements recheck ran outside the catalog lock, or did not "
        f"run exactly once: {seen}")


def test_an_applied_decision_replays_even_after_the_requirements_change(
        at_placement):
    """The check guards a decision *entering* the catalog. One already in it
    is a replay, and refusing that would leave an approved gate unable to
    finish after a crash."""
    assess(at_placement, proposal())
    approve_placement(at_placement)
    _edit_bound_requirements(at_placement)

    replay = at_placement.ok("architecture", "apply").data

    assert replay["replayed"] is True
    assert catalog_of(at_placement)["revision"] == 1


def test_a_placement_record_with_no_requirements_basis_is_refused(
        at_placement):
    """Fail closed: a record that does not say which documents it was
    reasoned from cannot be shown to match the ones now bound."""
    assess(at_placement, proposal())
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    record = _placement_record(at_placement)
    record.pop("requirementsDigest")
    record.pop("requirementsSources")
    paths.architecture_placement_file.write_text(
        json.dumps(record, indent=2), encoding="utf-8", newline="\n")

    result = at_placement.run("advance", "--to", "gate_architecture")

    assert result.exit_code == 1, result
    assert result.reason == "architecture_requirements_stale"


def test_realize_refuses_when_the_catalog_has_no_such_decision(at_placement):
    """Contract 12: a missing decision at realization is a refusal, never a
    tolerated no-op that leaves a service PLANNED for ever."""
    assess(at_placement, proposal())
    approve_placement(at_placement)
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    record = json.loads(
        paths.architecture_placement_file.read_text(encoding="utf-8"))
    record["decisionId"] = "AP-nobody-999"
    paths.architecture_placement_file.write_text(
        json.dumps(record, indent=2), encoding="utf-8", newline="\n")

    with pytest.raises(sdle.Refused) as excinfo:
        sdle.architecture_realize(paths, sdle.now_iso())
    assert excinfo.value.reason == "architecture_placement_missing"


def test_reassessing_after_approval_is_refused(at_placement):
    """The decision is already in the shared catalog, and a new assessment
    would mint an id nothing applied - leaving `realize` nothing to realize."""
    assess(at_placement, proposal())
    approve_placement(at_placement)
    result = assess(at_placement, proposal(revision=1), expect_ok=False)
    assert result.reason == "architecture_decision_conflict"


def test_a_rejected_gate_reopens_the_phase_for_a_fresh_assessment(at_placement):
    """The regression Round 1's own fix introduced, and Round 2 caught.

    Guarding re-assessment on the *presence* of an approvals entry rather
    than on its decision turned a rejection into a dead end: `gate reject`
    writes a truthy `{"decision": "rejected"}` that nothing clears, so the
    documented remedy — reject, then re-run the phase — refused. Worse, it is
    the only exit `ARCHITECTURE_REVIEW_REQUIRED` has, so recording the honest
    answer became unrecoverable. Rejection must reopen the phase.
    """
    first = assess(at_placement, proposal()).data
    shown = at_placement.ok("gate", "show", "--gate", "gate_architecture").data
    at_placement.ok("artifact", "review", "--path", shown["artifact_path"],
                    "--type", "architecture-placement", "--result", "PASS",
                    "--actor-type", "test", "--actor-name", "suite")
    at_placement.ok("advance", "--to", "gate_architecture")
    at_placement.ok("gate", "reject", "--gate", "gate_architecture",
                    "--reason", "Risk belongs in its own service.")

    second = assess(at_placement, proposal()).data
    assert second["decisionId"] == first["decisionId"], (
        "nothing was applied, so the number is not consumed")
    assert not (at_placement.root / ".sdle" / "architecture").exists()


def test_drift_rebaseline_of_the_rendering_is_refused_too(at_placement):
    """The sibling door to the drift-approval guard. Guarding one and not the
    other is not guarding the artifact: `drift rebaseline` would move the
    gate's baseline onto an edited rendering with no binding check and no
    re-apply, and nothing downstream re-reads the binding once the gate is
    approved."""
    data = assess(at_placement, proposal()).data
    approve_placement(at_placement)
    rendered = at_placement.root / data["rendered"]
    rendered.write_text(rendered.read_text(encoding="utf-8") + "\nedited\n",
                        encoding="utf-8", newline="\n")

    result = at_placement.run("drift", "rebaseline",
                              "--gate", "gate_architecture")
    assert result.exit_code == 1
    assert result.reason == "architecture_artifact_binding_invalid"
    catalog = catalog_of(at_placement)
    assert catalog["decisions"][0]["renderedSha256"] == data["renderedSha256"]


def test_a_corrupt_record_is_an_integrity_failure_of_its_own(at_placement):
    """One reason may not carry two exit codes. A malformed *proposal* is
    `architecture_placement_invalid` at exit 1 with "fix it and re-run"; a
    corrupt engine-written *record* is `architecture_record_invalid` at exit
    3, and the remedy is not the same one."""
    assess(at_placement, proposal())
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    paths.architecture_placement_file.write_text(
        "{not json", encoding="utf-8", newline="\n")

    result = at_placement.run("architecture", "apply")
    assert result.exit_code == 3
    assert result.reason == "architecture_record_invalid"


def test_extending_a_capability_does_not_clear_its_embedded_status(
        at_placement):
    """An `EMBEDDED` capability with an `OPEN` candidate is a recorded
    decision that it is not yet worth separating. A later WorkItem extending
    the same capability says nothing about that, so it must not flip the
    capability to ESTABLISHED and leave the candidate describing a different
    architecture."""
    document = proposal(
        outcome="KEEP_EMBEDDED_AND_MONITOR",
        placement={"currentOwner": OWNER, "targetOwner": None,
                   "candidates": [{"id": "ARCH-CAND-009",
                                   "capability": CAPABILITY,
                                   "currentOwner": OWNER,
                                   "reevaluateWhen": ["a second WorkItem"]}]})
    document["bootstrapDelta"] = {
        "basis": "BASELINE",
        "services": [{"serviceId": OWNER, "name": OWNER,
                      "repositoryPaths": ["requirements"]}],
        "capabilities": [], "dataOwnership": [],
        "evidence": [{"statement": "the one component this fixture has",
                      "paths": ["requirements"]}],
    }
    assess(at_placement, document)
    approve_placement(at_placement)
    assert catalog_of(at_placement)["capabilities"][0]["status"] == "EMBEDDED"

    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)
    catalog = catalog_of(at_placement)
    record = {
        "decisionId": "AP-later-001", "workitem": "later", "baseRevision": 1,
        "proposalDigest": "sha256:later", "renderedArtifact": "x",
        "renderedSha256": "y",
        "placement": {
            "outcome": "EXTEND_EXISTING_SERVICE", "targetOwner": OWNER,
            "currentOwner": OWNER,
            "capability": {"id": CAPABILITY, "name": "Risk",
                           "description": ""},
            "dataOwnership": [], "candidates": [],
        },
    }
    updated = sdle.apply_architecture_delta(catalog, record, sdle.now_iso())
    assert updated["capabilities"][0]["status"] == "EMBEDDED", (
        "extending says nothing about whether the capability is embedded")
    assert updated["candidates"][0]["state"] == "OPEN"


def test_drift_reapproval_of_the_rendering_is_refused(at_placement):
    """D15. The rendering is generated and bound by digest to a decision
    already in the catalog, so a drifted copy is not new content to
    re-approve - re-baselining it would break the binding silently."""
    data = assess(at_placement, proposal()).data
    approve_placement(at_placement)
    rendered = at_placement.root / data["rendered"]
    rendered.write_text(rendered.read_text(encoding="utf-8") + "\ndrifted\n",
                        encoding="utf-8", newline="\n")
    at_placement.ok("drift", "check", "--queue",
                    "--pending-phase", "spec_draft")

    result = at_placement.run("gate", "approve", "--gate", "gate_architecture")
    assert result.exit_code == 1
    assert result.reason == "architecture_artifact_binding_invalid"


def test_realize_closes_only_its_own_extraction(at_placement):
    """The catalog is shared. An unfiltered sweep would close another
    WorkItem's in-flight extraction and leave its placement reasoning from a
    state nobody decided."""
    assess(at_placement, proposal())
    approve_placement(at_placement)
    paths = sdle.bind_workitem(
        sdle.resolve_paths(str(at_placement.root), None), at_placement.workitem)

    catalog = catalog_of(at_placement)
    catalog["capabilities"].append({
        "id": "CAP-SOMEONE-ELSE", "name": "Theirs", "description": "",
        "status": "EXTRACTING", "ownerService": TARGET,
        "relatedWorkItems": [], "evidence": [],
        "introducedBy": "AP-other-001"})
    catalog["decisions"][0]["outcome"] = "EXTRACT_EXISTING_CAPABILITY"
    sdle.write_architecture_catalog(paths, catalog)

    sdle.architecture_realize(paths, sdle.now_iso())

    after = {entry["id"]: entry["status"]
             for entry in catalog_of(at_placement)["capabilities"]}
    assert after["CAP-SOMEONE-ELSE"] == "EXTRACTING", after


def test_a_withdrawn_service_can_be_reclaimed_by_a_later_placement():
    catalog = sdle.empty_architecture_catalog()
    catalog["services"] = [{
        "serviceId": TARGET, "name": TARGET, "status": "WITHDRAWN",
        "capabilities": [], "repositoryPaths": [], "ownedData": [],
        "dependencies": [], "decisionReference": "AP-old-001",
        "introducedBy": "AP-old-001"}]
    record = {
        "decisionId": "AP-new-001", "workitem": "new", "baseRevision": 0,
        "proposalDigest": "sha256:new", "renderedArtifact": "x",
        "renderedSha256": "y",
        "placement": {
            "outcome": "CREATE_NEW_SERVICE", "targetOwner": TARGET,
            "currentOwner": None,
            "capability": {"id": CAPABILITY, "name": "Risk",
                           "description": ""},
            "dataOwnership": [], "candidates": [],
        },
    }
    updated = sdle.apply_architecture_delta(catalog, record, sdle.now_iso())
    assert updated["services"][0]["status"] == "PLANNED"
    assert updated["services"][0]["decisionReference"] == "AP-new-001"
    # `introducedBy` does NOT move: the boundary was brought into being by the
    # decision that first planned it, and only that decision may withdraw it.
    assert updated["services"][0]["introducedBy"] == "AP-old-001"


# -- boundaries -------------------------------------------------------------


def test_the_catalog_is_not_owned_whole_by_the_dirty_tree_guard():
    owned = sdle.SDLE_OWNED_PREFIXES
    assert ".sdle/architecture/" in owned
    assert ".sdle/" not in owned
    for visible in (".sdle/config.json", ".sdle/policies/x.json"):
        assert not any(visible.startswith(prefix) for prefix in owned), visible


def test_an_engine_owned_catalog_write_does_not_trip_implement_preflight(
        git_project: Project):
    """The regression ADR-013 §3.4.1 asks for: a WorkItem may update the
    catalog at its architecture gate and still pass the implementation
    dirty-tree guard, while an unrelated edit to `.sdle/config.json` in the
    same tree still trips it."""
    catalog = git_project.root / ".sdle" / "architecture" / "catalog.json"
    catalog.parent.mkdir(parents=True, exist_ok=True)
    catalog.write_text(json.dumps(sdle.empty_architecture_catalog(), indent=2),
                       encoding="utf-8", newline="\n")
    git_project.record_governance()
    git_project.ok("init")
    state = git_project.state()
    state["current_phase"] = "implement"
    git_project.write_state(state)
    assert git_project.ok("implement", "preflight").data["dirty"] is False

    config = git_project.root / ".sdle" / "config.json"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"configVersion": "1", "policyFormat": "json"}\n',
                      encoding="utf-8", newline="\n")
    result = git_project.run("implement", "preflight")
    assert result.exit_code == 1
    assert result.reason == "dirty_tree"


def test_the_write_fence_denies_the_catalog_but_not_the_config():
    """`.sdle/` is deliberately not fenced whole: `config init` writes
    `config.json` and a human edits `policies/`."""
    from test_hooks import load_hooks_module
    hooks = load_hooks_module()
    assert ".sdle/architecture" in hooks.FENCED
    assert ".sdle" not in hooks.FENCED


def test_a_second_workitem_sees_the_first_ones_architecture(at_placement):
    assess(at_placement, proposal())
    approve_placement(at_placement)

    second = create_wi(at_placement, "Detailed Risk Assessment")
    view = at_placement.as_workitem(second)
    shown = view.ok("architecture", "show").data
    assert shown["initialized"] is True
    assert shown["revision"] == 1
    assert [s["serviceId"] for s in shown["catalog"]["services"]] == [TARGET]
