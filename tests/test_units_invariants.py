"""Engine invariants stated directly on the current source.

These replace comparisons against old commits. Each pins a property that still
matters: which phases the default flow runs, which fields a WorkItem's state
carries, which primitives the engine writes through, and which commands it
offers. A change to any of them is allowed, but it has to be made here, on
purpose, in the same commit as the change it describes.
"""

from __future__ import annotations

import ast
import json
import re

from conftest import REPO_ROOT, sdle

ENGINE = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
TEMPLATE = REPO_ROOT / ".claude" / "skills" / "sdle" / "templates" / "state.json"

GREENFIELD_PHASES = (
    'requirements_check',
    'constitution_draft',
    'gate_constitution',
    'architecture_placement',
    'gate_architecture',
    'spec_draft',
    'gate_spec',
    'plan_draft',
    'gate_plan',
    'checklist_draft',
    'tasks_draft',
    'gate_tasks',
    'analyze',
    'gate_analyze',
    'design_generation',
    'gate_design',
    'implement',
    'gate_implement',
    'security_review',
    'gate_security',
    'complete',
)

STATE_FIELDS = (
    'approvals',
    'artifact_shas',
    'attempt_counts',
    'audit_sha',
    'clarification_phase',
    'current_artifact',
    'current_artifact_sha',
    'current_phase',
    'drift_queue',
    'flow',
    'implementation_base_ref',
    'last_updated',
    'pending_branch_ack',
    'pending_confirm_action',
    'pending_phase',
    'phase_checkpoint',
    'phase_history',
    'progress',
    'project_name',
    'rate_limits',
    'security_review_artifact',
    'specKit',
    'speckit_initialized',
    'speckit_skill_prefix',
    'status',
    'verbose',
    'workflow_version',
    'workitem',
)

# Occurrences of each write primitive in scripts/sdle.py. State, audit and
# lock have one writer, the engine (invariant 6); a new call site is a new
# writer and must be justified where this number changes.
#
# 25 -> 26: ADR-012's `requirements bind` writes the WorkItem's requirements
# binding. Engine-written for the same reason the governance record is — it
# decides what an assessment means, so it is not a file a model may edit.
#
# 26 -> 30: ADR-013's four architecture writers — the placement record, its
# rendering, its evidence document, and the shared repository catalog
# (`write_architecture_catalog`, the single door every catalog mutation goes
# through). The catalog is engine-written for a stronger reason than the rest:
# it is read by WorkItems other than the one that wrote it.
#
# 30 -> 31 and 53 -> 54: the Round-1 review's R1-012 and R1-008. A rerun
# placement that supersedes a prior approved decision now emits
# `architecture_decision_abandoned` rather than changing a catalog field with
# no ledger entry behind it.
#
# 31 -> 32: DEF-RR-001's `write_content_acknowledgement` writes the WorkItem's
# scan-acknowledgements record — another pre-init record only the engine
# writes, for the same reason.
# save_state 49 -> 50, append_audit 54 -> 56: DEF-RR-001's
# `cmd_accept_content --path` branch appends an audit entry and rebaselines
# state when a post-init acknowledgement is also given, and
# `record_scan_acknowledgement_audit` replays a pre-init acknowledgement into
# the ledger at the first advance, mirroring `record_governance_audit`.
# write_atomic 34 -> 41 (counted from the engine, not predicted): the refinement
# record writer, the document write and the baseline, lint, apply, cancel and
# dispute evidence files.
WRITE_PRIMITIVE_COUNTS = {
    'write_atomic': 41,
    'save_state': 50,
    'append_audit': 56,
    'record_audit': 0,
    '.write_text(': 0,
    '.write_bytes(': 0,
    'os.replace': 3,
    # 7 -> 8: `requirements bind` creates the WorkItem's runtime directory
    # if it is not there yet, exactly as `governance assess` does — both
    # write into the runtime before `init` exists.
    #
    # 8 -> 10: `architecture assess` creates `workitems/<id>/architecture/`
    # for the rendering, and `write_architecture_catalog` creates
    # `.sdle/architecture/` for the catalog.
    #
    # 10 -> 11: `architecture_catalog_lock` creates `.sdle/architecture/` before
    # it takes the lock, because the lock file lives beside the catalog and
    # the first placement in a repository takes it before anything else has
    # created the directory.
    '.mkdir(': 11,
}

COMMANDS = (
    'accept-content',
    'accept-state',
    'acquire',
    'advance',
    'append',
    # ADR-013: `architecture apply` / `architecture realize`. Normally reached
    # through the gate path; exposed for replay after a crash.
    'apply',
    'approve',
    'architecture',
    'artifact',
    'assess',
    'audit',
    'baseline',
    'begin',
    'bind',
    'build',
    'capabilities',
    'check',
    'checkpoint',
    'clarify',
    'clear',
    'config',
    'confirm',
    'constants',
    'create',
    'discovery',
    'doctor',
    'drift',
    'dump',
    'evidence',
    'feature',
    'finish',
    'flow',
    'gate',
    'gates',
    'get',
    'governance',
    'guidance',
    'header',
    'implement',
    'init',
    'limit',
    'lint-skill',
    'list',
    'lock',
    'manifest',
    'omit',
    'path',
    'policy',
    'preflight',
    'realize',
    'rebaseline',
    'record',
    # `refinement propose|decide|apply|dispute|cancel|show`. The first four
    # subcommands are registered in a loop, so only the group is a literal.
    'refinement',
    'reject',
    'release',
    'remediate',
    'repo-staleness',
    # ADR-012: `requirements bind` / `requirements show`. A WorkItem declares
    # the documents it is about; every consumer reads that binding.
    'requirements',
    'reset',
    'resolve',
    'restart',
    'resume',
    'retry',
    'review',
    'reviews',
    'save',
    'scan',
    'schema',
    'security-review',
    'set',
    'sha',
    'show',
    'skip',
    'state',
    'use',
    'validate',
    'verify',
    'workitem',
)


def test_greenfield_is_the_default_flow_and_runs_exactly_these_phases():
    assert sdle.GREENFIELD_V1_PHASES == GREENFIELD_PHASES
    assert GREENFIELD_PHASES[-1] == "complete"


def test_every_other_flow_is_an_ordered_subset_of_the_registry():
    consts = sdle.load_constants(sdle.resolve_paths(str(REPO_ROOT), None))
    registry = list(consts.phase_sequence)
    for name in sdle.ENGINEERING_FLOWS:
        phases = list(consts.flow(name).phases)
        assert phases == [p for p in registry if p in phases], name
        assert phases[0] == "requirements_check" and phases[-1] == "complete"
    assert "GREENFIELD" not in consts.flow_phases, (
        "GREENFIELD is the engine's frozen default, never a table row")


def test_the_state_template_declares_exactly_these_fields():
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert tuple(sorted(template)) == STATE_FIELDS


def test_the_state_template_carries_the_engines_current_version():
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert template["workflow_version"] == sdle.CURRENT_VERSION


def test_every_gate_has_an_approval_slot_and_starts_unapproved():
    consts = sdle.load_constants(sdle.resolve_paths(str(REPO_ROOT), None))
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert set(template["approvals"]) == set(consts.phase_to_gate_key.values())
    assert all(value is None for value in template["approvals"].values())


def test_the_engine_writes_through_a_known_number_of_call_sites():
    for needle, expected in WRITE_PRIMITIVE_COUNTS.items():
        assert ENGINE.count(needle) == expected, (needle, ENGINE.count(needle))


def test_the_write_primitive_needles_match_the_engine():
    """Non-vacuity. A zero is a real pin (the engine writes only through
    `write_atomic`, never a bare `.write_text(`), so the guard is that the
    primitives that *are* used still match the source, not that every one does."""
    assert sum(WRITE_PRIMITIVE_COUNTS.values()) >= 100, WRITE_PRIMITIVE_COUNTS
    assert WRITE_PRIMITIVE_COUNTS["write_atomic"] > 0
    assert WRITE_PRIMITIVE_COUNTS["append_audit"] > 0
    assert len(COMMANDS) > 50


def test_exactly_one_function_creates_a_file_exclusively():
    """Evidence files are reserved with `open(..., "x")`, so two rapid
    executions cannot adopt each other's file. One writer, by name."""
    exclusive = [
        node.name for node in ast.walk(ast.parse(ENGINE))
        if isinstance(node, ast.FunctionDef)
        and any(isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name) and call.func.id == "open"
                and any(isinstance(a, ast.Constant) and a.value == "x"
                        for a in call.args)
                for call in ast.walk(node))]
    assert exclusive == ["reserve_evidence"], exclusive


def test_the_command_surface_is_the_documented_one():
    found = tuple(sorted(set(re.findall(
        r'add_parser[(]\s*"([a-z][a-z-]*)"', ENGINE))))
    assert found == COMMANDS
