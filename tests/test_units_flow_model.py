"""The declarative flow model (T07).

PHASE_SEQUENCE is a *registry* — the catalogue of phases SDLE knows how to
execute. A **flow** is an ordered subset of it, and a WorkItem traverses
exactly one. This file pins the three things that makes safe:

1. **The compatibility translation.** Every workflow that predates the flow
   model traversed the pre-flow PHASE_SEQUENCE, and that list is GREENFIELD.
   It is frozen in the engine, spelled out again as a golden literal here, and
   compared against the happy-path integration test's own `EXPECTED_TRAVERSAL`.
2. **The engine refuses a flow it cannot trust.** `Constants.flow()` raises
   `flow_table_invalid` (exit 3) rather than traversing a broken table — while
   `load_constants` stays silent about it, so `lint-skill` can still name the
   rule that broke instead of short-circuiting.
3. **The human-readable tables SKILL.md still carries are derived views.**
   PROGRESS_MAP, PHASE_TO_GATE_KEY's gate-number column and the ordinals inside
   PHASE_LABEL_MAP must reproduce, exactly, what the GREENFIELD flow computes.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from conftest import REPO_ROOT, Project, sdle
from test_integration_01_happy_path import EXPECTED_TRAVERSAL
from test_units_artifact_review import review_for_gate

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3


# The golden literal (witness P2). Spelled out on purpose: an independent
# second copy of GREENFIELD's membership that a reviewer can read without
# opening the engine. If this list and GREENFIELD_V1_PHASES ever disagree, one
# of them was edited without the other and the compatibility translation is no
# longer true.
GREENFIELD_GOLDEN = [
    "requirements_check",
    "constitution_draft",
    "gate_constitution",
    "spec_draft",
    "gate_spec",
    "plan_draft",
    "gate_plan",
    "checklist_draft",
    "tasks_draft",
    "gate_tasks",
    "analyze",
    "gate_analyze",
    "design_generation",
    "gate_design",
    "implement",
    "gate_implement",
    "security_review",
    "gate_security",
    "complete",
]


@pytest.fixture
def skill_copy(tmp_path: Path) -> Project:
    """A writable copy of the skill files, lintable and parseable in isolation.

    Breaking FLOW_PHASES is the only way to prove the engine refuses a broken
    flow table, and the repository's own copy must never be the thing broken.
    """
    root = tmp_path / "repo"
    (root / ".claude" / "skills").mkdir(parents=True)
    shutil.copytree(REPO_ROOT / ".claude" / "skills" / "sdle",
                    root / ".claude" / "skills" / "sdle")
    (root / "docs").mkdir()
    shutil.copy(REPO_ROOT / "README.md", root / "README.md")
    shutil.copy(REPO_ROOT / "docs" / "SDLE-Reference-Guide.md",
                root / "docs" / "SDLE-Reference-Guide.md")
    return Project(root, root / ".claude" / "skills" / "sdle")


def constants_of(project: Project) -> "sdle.Constants":
    paths = sdle.resolve_paths(str(project.root), str(project.skill_root))
    return sdle.load_constants(paths)


def edit_skill(project: Project, old: str, new: str) -> None:
    path = project.skill_root / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    assert old in text, f"fixture text not found in SKILL.md: {old!r}"
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def flow_row(name: str, phases: str) -> str:
    return f"| `{name}` | {phases} |"


def row_for(project: Project, name: str) -> str:
    """The FLOW_PHASES row for ``name``, read out of the fixture's SKILL.md."""
    text = (project.skill_root / "SKILL.md").read_text(encoding="utf-8")
    prefix = f"| `{name}` | "
    for line in text.splitlines():
        if line.startswith(prefix):
            return line
    raise AssertionError(f"no FLOW_PHASES row for {name}")


# -- N19 / P1 / P2: the compatibility translation ---------------------------


def test_greenfield_equals_the_golden_literal(skill_copy):
    """P2 — a second, human-readable witness for GREENFIELD's membership."""
    assert list(sdle.GREENFIELD_V1_PHASES) == GREENFIELD_GOLDEN
    assert list(constants_of(skill_copy).flows["GREENFIELD"].phases) == \
        GREENFIELD_GOLDEN


def test_greenfield_equals_the_happy_path_expected_traversal():
    """P1 — the same list the pre-T07 acceptance transcript already asserts.

    `EXPECTED_TRAVERSAL` lives in a file T07 may not touch at all, so this
    equality cannot be made true by editing the test that proves it.
    """
    assert list(sdle.GREENFIELD_V1_PHASES) == list(EXPECTED_TRAVERSAL)


def test_greenfield_is_not_a_declared_flow_row(skill_copy):
    """GREENFIELD has exactly one home, and it is not the editable table."""
    consts = constants_of(skill_copy)
    assert "GREENFIELD" not in consts.flow_phases
    assert set(consts.flow_phases) == {
        "BROWNFIELD_DISCOVERY", "ITERATIVE", "DEFECT_FIX", "HOTFIX"}
    assert set(consts.flows) == set(sdle.ENGINEERING_FLOWS)


# -- N23: the governance floor and the HOTFIX identity ----------------------


def test_hotfix_is_the_governance_floor_and_nothing_else(skill_copy):
    """§13's "shorter but never ungoverned" as an exact set identity.

    `impact_analysis` is subtracted rather than ignored: it is the one phase
    HOTFIX carries beyond the floor, and stating it here means HOTFIX cannot
    silently grow a *second* non-mandatory phase.
    """
    flows = constants_of(skill_copy).flows
    hotfix = set(flows["HOTFIX"].phases)
    assert hotfix - {"impact_analysis"} == set(sdle.MANDATORY_FLOW_PHASES)


def test_every_flow_is_a_superset_of_the_mandatory_phases(skill_copy):
    floor = set(sdle.MANDATORY_FLOW_PHASES)
    for name, flow in constants_of(skill_copy).flows.items():
        assert set(flow.phases) >= floor, f"{name} dropped a mandatory phase"


def test_hotfix_is_the_shortest_flow_and_adds_nothing_beyond_its_one_phase(
    skill_copy
):
    """"Nothing is shorter than HOTFIX", stated so that it is actually true.

    A plain `set(HOTFIX) <= set(flow)` is false by construction: HOTFIX carries
    `impact_analysis`, which GREENFIELD deliberately does not have. What the
    minimality claim actually means is asserted in two exact parts —
    HOTFIX has the fewest phases of any flow, and everything in it except that
    one phase is in every other flow. Together those forbid HOTFIX growing a
    second non-mandatory phase *and* forbid any flow being shorter.
    """
    flows = constants_of(skill_copy).flows
    hotfix = flows["HOTFIX"]
    floor = set(hotfix.phases) - {"impact_analysis"}
    for name, flow in flows.items():
        assert len(hotfix.phases) <= len(flow.phases), \
            f"{name} is shorter than HOTFIX"
        assert floor <= set(flow.phases), \
            f"{name} is missing something HOTFIX keeps"


def test_impact_analysis_is_not_in_the_mandatory_floor():
    """Adding it to the floor would force it into GREENFIELD and ITERATIVE.

    It is in DEFECT_FIX and HOTFIX because those flows name it, never because
    a floor or a risk level demands it.
    """
    assert "impact_analysis" not in sdle.MANDATORY_FLOW_PHASES


# -- N24: the SKILL.md tables are checked derived views ---------------------


def test_progress_map_is_the_derived_greenfield_progress(skill_copy):
    consts = constants_of(skill_copy)
    greenfield = consts.greenfield
    for phase in greenfield.phases:
        assert consts.progress[phase] == greenfield.progress_for(phase), phase


def test_the_gate_number_column_is_the_derived_greenfield_numbering(skill_copy):
    consts = constants_of(skill_copy)
    greenfield = consts.greenfield
    for phase in greenfield.gate_phases:
        key = consts.phase_to_gate_key[phase]
        assert consts.gate_number[key] == greenfield.gate_number(key), key


def test_greenfield_gate_labels_render_the_pre_t07_literals(skill_copy):
    """The eight labels that used to be hardcoded, reproduced byte for byte.

    This is the proof that replacing `Gate 5:` with `{gate_number}` changed no
    user-visible string under GREENFIELD.
    """
    expected = {
        "gate_constitution": "Gate 1: Constitution Approval",
        "gate_spec": "Gate 2: Specification Approval",
        "gate_plan": "Gate 3: Plan Approval",
        "gate_tasks": "Gate 4: Tasks Approval",
        "gate_analyze": "Gate 5: Analysis Approval",
        "gate_design": "Gate 6: Design Approval",
        "gate_implement": "Gate 7: Implementation Approval",
        "gate_security": "Gate 8: Security Review Approval",
    }
    consts = constants_of(skill_copy)
    greenfield = consts.greenfield
    for phase, label in expected.items():
        assert consts.label(phase, greenfield) == label
        # ... and the default, flow-free call site keeps the same output.
        assert consts.label(phase) == label
        assert consts.phase_label[phase] == label


def test_a_gate_ordinal_is_flow_relative(skill_copy):
    """The reason the literal had to go: HOTFIX's Gate 2 is GREENFIELD's 7."""
    flows = constants_of(skill_copy).flows
    consts = constants_of(skill_copy)
    assert consts.label("gate_implement", flows["GREENFIELD"]) == \
        "Gate 7: Implementation Approval"
    assert consts.label("gate_implement", flows["HOTFIX"]) == \
        "Gate 2: Implementation Approval"
    assert flows["HOTFIX"].gate_total == 3
    assert flows["GREENFIELD"].gate_total == 8


def test_the_gateless_flow_denominators_are_the_declared_ones(skill_copy):
    """The three flows that carry no impact analysis.

    `DEFECT_FIX` and `HOTFIX` are asserted alongside the rest of the
    `impact_analysis` evidence, because their denominators are what that phase
    changes.
    """
    flows = constants_of(skill_copy).flows
    assert flows["GREENFIELD"].phase_count == 18
    assert flows["BROWNFIELD_DISCOVERY"].phase_count == 18
    assert flows["ITERATIVE"].phase_count == 16


# -- N22: the engine refuses a flow it cannot trust -------------------------


BREAKAGES = {
    "unknown_phase_id": "requirements_check not_a_real_phase spec_draft "
                        "gate_spec plan_draft tasks_draft implement "
                        "gate_implement security_review gate_security complete",
    "out_of_registry_order": "requirements_check gate_spec spec_draft "
                             "plan_draft tasks_draft implement gate_implement "
                             "security_review gate_security complete",
    "duplicate_phase": "requirements_check spec_draft spec_draft gate_spec "
                       "plan_draft tasks_draft implement gate_implement "
                       "security_review gate_security complete",
    "missing_mandatory_phase": "requirements_check spec_draft gate_spec "
                               "plan_draft tasks_draft implement "
                               "security_review gate_security complete",
    "missing_terminal_complete": "requirements_check spec_draft gate_spec "
                                 "plan_draft tasks_draft implement "
                                 "gate_implement security_review "
                                 "gate_security",
    "wrong_first_phase": "spec_draft gate_spec plan_draft tasks_draft "
                         "implement gate_implement security_review "
                         "gate_security complete",
}


@pytest.mark.parametrize("label,phases", sorted(BREAKAGES.items()))
def test_a_broken_flow_row_refuses_rather_than_defaulting(
    skill_copy, label, phases
):
    """Exit 3, named reason, and never a silently repaired flow."""
    edit_skill(skill_copy, row_for(skill_copy, "HOTFIX"),
               flow_row("HOTFIX", phases))
    consts = constants_of(skill_copy)          # the loader stays silent
    with pytest.raises(sdle.IntegrityError) as caught:
        consts.flow("HOTFIX")
    assert caught.value.reason == "flow_table_invalid"
    assert caught.value.exit_code == EXIT_INTEGRITY


def test_an_unknown_flow_name_refuses(skill_copy):
    consts = constants_of(skill_copy)
    with pytest.raises(sdle.IntegrityError) as caught:
        consts.flow("NO_SUCH_FLOW")
    assert caught.value.reason == "flow_table_invalid"
    assert caught.value.exit_code == EXIT_INTEGRITY
    assert "GREENFIELD" in caught.value.data["known"]


@pytest.mark.parametrize("label,phases", sorted(BREAKAGES.items()))
def test_load_constants_parses_a_broken_flow_without_raising(
    skill_copy, label, phases
):
    """The firing-test constraint, stated as behaviour.

    If the loader raised, `tables_wellformed` would short-circuit and one
    broken row would hide every other check. It must parse; judgement belongs
    to `lint-skill` and to `Constants.flow()`.
    """
    edit_skill(skill_copy, row_for(skill_copy, "HOTFIX"),
               flow_row("HOTFIX", phases))
    consts = constants_of(skill_copy)
    assert consts.flow_phases["HOTFIX"] == phases.split()

    result = skill_copy.run("lint-skill")
    assert result.exit_code == EXIT_REFUSED
    names = [c["name"] for c in result.data["checks"]]
    assert names[0] == "tables_wellformed"
    assert result.data["checks"][0]["passed"] is True, \
        "a broken flow row is not a wellformedness failure"
    assert len(names) > 1, "the other checks must still have run"


def test_greenfield_itself_is_validated_by_the_same_rules(skill_copy):
    """GREENFIELD is injected, not privileged: it goes through `flow()` too."""
    consts = constants_of(skill_copy)
    greenfield = consts.flow("GREENFIELD")
    assert consts.flow_order_problems(greenfield) == []
    assert consts.flow_floor_problems(greenfield) == []
    assert consts.flow() is not None
    assert consts.flow().name == "GREENFIELD"


def test_a_flow_is_never_repaired_only_refused(skill_copy):
    """No default, no filtering, no "closest match" — the failure is total."""
    edit_skill(skill_copy, row_for(skill_copy, "ITERATIVE"),
               flow_row("ITERATIVE", "requirements_check complete"))
    consts = constants_of(skill_copy)
    with pytest.raises(sdle.IntegrityError):
        consts.flow("ITERATIVE")
    # The neighbouring flows are untouched: one bad row does not poison the
    # table, and GREENFIELD in particular is not read from it at all.
    assert list(consts.flow("GREENFIELD").phases) == GREENFIELD_GOLDEN
    assert consts.flow("HOTFIX").phases[0] == "requirements_check"


# -- the registry is 20 phases and no flow is all of it ---------------------


def test_the_registry_is_larger_than_every_flow(skill_copy):
    """The fact the whole design rests on: the registry is not a lifecycle."""
    consts = constants_of(skill_copy)
    assert len(consts.phase_sequence) == 20
    for name, flow in consts.flows.items():
        assert len(flow.phases) < 20, f"{name} is the whole registry"


def test_impact_analysis_sits_at_registry_position_two(skill_copy):
    consts = constants_of(skill_copy)
    assert consts.phase_sequence[1] == "impact_analysis"
    assert consts.index("impact_analysis") == 2


def test_impact_analysis_is_in_exactly_the_two_defect_flows(skill_copy):
    carriers = {name for name, flow in constants_of(skill_copy).flows.items()
                if "impact_analysis" in flow.phases}
    assert carriers == {"DEFECT_FIX", "HOTFIX"}


def test_impact_analysis_is_absent_from_greenfield(skill_copy):
    """GREENFIELD's traversal did not change, which is the whole promise."""
    assert "impact_analysis" not in sdle.GREENFIELD_V1_PHASES
    assert "impact_analysis" not in constants_of(skill_copy).progress


def test_the_defect_flow_denominators_are_the_declared_ones(skill_copy):
    flows = constants_of(skill_copy).flows
    assert flows["DEFECT_FIX"].phase_count == 14
    assert flows["HOTFIX"].phase_count == 10
    # Six, not the five the plan's summary column records: DEFECT_FIX's own
    # declared phase list names gate_spec, gate_plan, gate_tasks, gate_analyze,
    # gate_implement and gate_security, and its non-terminal count of 14
    # confirms that list. Membership is the decision; the count is derived.
    assert flows["DEFECT_FIX"].gate_total == 6
    assert [consts_gate for consts_gate in flows["DEFECT_FIX"].gate_keys] == [
        "gate_spec", "gate_plan", "gate_tasks", "gate_analyze",
        "gate_implement", "gate_security"]
    assert flows["HOTFIX"].gate_total == 3
    assert list(flows["HOTFIX"].gate_keys) == [
        "gate_spec", "gate_implement", "gate_security"]


def test_impact_analysis_leads_to_spec_draft_in_both_defect_flows(skill_copy):
    flows = constants_of(skill_copy).flows
    for name in ("DEFECT_FIX", "HOTFIX"):
        assert flows[name].phases[0] == "requirements_check"
        assert flows[name].phases[1] == "impact_analysis"
        assert flows[name].next_phase("impact_analysis") == "spec_draft"


# -- gateless means no gate machinery anywhere, not "a gate we skip" --------


PRE_T07_APPROVAL_KEYS = {
    "gate_constitution", "gate_spec", "gate_plan", "gate_tasks",
    "gate_analyze", "gate_design", "gate_implement", "gate_security",
}


def test_impact_analysis_has_no_gate_registration(skill_copy):
    consts = constants_of(skill_copy)
    assert "impact_analysis" not in consts.phase_to_gate_key
    assert "impact_analysis" not in consts.gate_phases
    assert "gate_impact_analysis" not in consts.artifact_ownership
    assert "gate_impact_analysis" not in consts.gate_to_execution_phase
    assert "gate_impact_analysis" not in consts.phase_to_gate_key.values()


def test_the_state_template_still_has_exactly_eight_approval_keys(skill_copy):
    import json
    template = json.loads(
        (skill_copy.skill_root / "templates" / "state.json")
        .read_text(encoding="utf-8"))
    assert set(template["approvals"]) == PRE_T07_APPROVAL_KEYS


def test_no_shipped_file_mentions_a_gate_for_impact_analysis():
    """A ninth gate anywhere would contradict the decision this phase implements."""
    offenders = []
    for path in sorted((REPO_ROOT / ".claude").rglob("*")):
        if path.is_file() and path.suffix in {".md", ".json", ".py"}:
            if "gate_impact_analysis" in path.read_text(encoding="utf-8",
                                                        errors="ignore"):
                offenders.append(str(path.relative_to(REPO_ROOT)))
    if "gate_impact_analysis" in (REPO_ROOT / "scripts" / "sdle.py").read_text(
            encoding="utf-8"):
        offenders.append("scripts/sdle.py")
    assert offenders == []


def impact_analysis_block() -> str:
    text = (REPO_ROOT / ".claude" / "skills" / "sdle" / "modules"
            / "phase-execution.md").read_text(encoding="utf-8")
    start = text.index("**Phase `impact_analysis`")
    end = text.index("**Phase ", start + 10)
    return text[start:end]


def test_the_impact_analysis_block_never_touches_the_feature_directory():
    """It runs before `spec_draft`, so the feature directory does not exist.

    `feature bind --require-feature` would refuse and halt every defect flow at
    its second phase — a failure no test can catch, because the suite never
    invokes Spec Kit. So the prohibition is asserted on the prompt text itself.
    """
    block = impact_analysis_block()
    assert "feature bind" not in block
    assert "featureDirectory" not in block


def test_the_impact_analysis_block_governs_its_artifact():
    block = impact_analysis_block()
    assert "reviews/impact-analysis-<YYYY-MM-DD-HHmm>.md" in block
    assert "artifact record --phase impact_analysis" in block
    assert "artifact review --path" in block
    assert "--type impact-analysis" in block


def test_the_impact_analysis_block_header_carries_no_ordinal():
    """Renumbering the other 17 blocks was rejected; this one has no number."""
    block = impact_analysis_block()
    assert block.startswith("**Phase `impact_analysis` (DEFECT_FIX and HOTFIX")


# -- N20: a registry row does not join GREENFIELD ---------------------------


def test_a_new_registry_row_does_not_join_greenfield(skill_copy):
    """The test that would have caught deriving GREENFIELD from the registry.

    A phase added to PHASE_SEQUENCE must leave GREENFIELD untouched and must
    make `every_registry_phase_is_used_by_some_flow` fail loudly, rather than
    silently becoming part of the lifecycle every pre-flow workflow is said to
    have traversed.
    """
    edit_skill(skill_copy, "| 20 | `complete` |",
               "| 20 | `complete` |\n| 21 | `late_addition` |")
    consts = constants_of(skill_copy)
    assert "late_addition" in consts.phase_sequence
    assert list(consts.flows["GREENFIELD"].phases) == GREENFIELD_GOLDEN
    assert "late_addition" not in consts.flows["GREENFIELD"].phases

    checks = {c["name"]: c["passed"]
              for c in skill_copy.run("lint-skill").data["checks"]}
    assert checks["every_registry_phase_is_used_by_some_flow"] is False


# -- N21: NEXT_PHASE has no traversal consumer left -------------------------


def next_phase_readers() -> dict[str, set[str]]:
    """Every `.next_phase` attribute access, grouped by receiver expression."""
    import ast
    source = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    owner: dict[int, str] = {}

    def annotate(node, name):
        for child in ast.iter_child_nodes(node):
            nm = (child.name
                  if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                  else name)
            owner[id(child)] = nm
            annotate(child, nm)

    annotate(tree, "<module>")
    found: dict[str, set[str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "next_phase":
            found.setdefault(ast.unparse(node.value), set()).add(
                owner.get(id(node), "<module>"))
    return found


def test_the_constants_next_phase_reader_set_is_closed():
    """NEXT_PHASE survives as a linted table with no traversal consumer.

    After the registry insertion the registry chain is no longer the GREENFIELD
    chain: `NEXT_PHASE["requirements_check"]` is `impact_analysis`, which
    GREENFIELD does not have. A single leftover reader would route a GREENFIELD
    run through a phase it does not contain. The set is asserted closed rather
    than enumerated by traversal function, so a *new* reader anywhere in the
    file fails this test.
    """
    readers = next_phase_readers()
    assert readers["consts"] == {
        "load_constants", "run_sync_checks", "cmd_constants"}


def test_no_receiver_other_than_consts_and_flow_reads_next_phase():
    readers = next_phase_readers()
    assert set(readers) == {"consts", "flow"}


def test_every_constants_instance_in_the_engine_is_named_consts():
    """Closes the loophole in the two tests above.

    They group by receiver *name*; that is only a real closure if no other name
    ever holds a `Constants`. Every binding of `load_constants(...)` is checked
    to be called `consts`, so a `c.next_phase` hiding in some function cannot
    slip past.
    """
    import ast
    source = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
    names = set()
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Assign):
            continue
        value = node.value
        if (isinstance(value, ast.Call)
                and isinstance(value.func, ast.Name)
                and value.func.id == "load_constants"):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    assert names == {"consts"}


def test_next_phase_still_chains_the_twenty_entry_registry(skill_copy):
    """The table stays, and stays linted: it is the registry's order proof."""
    consts = constants_of(skill_copy)
    assert consts.next_phase["requirements_check"] == "impact_analysis"
    assert consts.next_phase["impact_analysis"] == "constitution_draft"
    assert set(consts.next_phase) == set(consts.phase_sequence)

    checks = {c["name"]: c["passed"]
              for c in skill_copy.run("lint-skill").data["checks"]}
    assert checks["next_phase_chains_sequence"] is True


def test_the_registry_chain_and_the_greenfield_chain_now_differ(skill_copy):
    """Stated as an assertion so the divergence cannot be un-noticed.

    This is exactly why every traversal call site had to stop reading
    NEXT_PHASE before this row was added.
    """
    consts = constants_of(skill_copy)
    greenfield = consts.greenfield
    assert consts.next_phase["requirements_check"] == "impact_analysis"
    assert greenfield.next_phase("requirements_check") == "constitution_draft"


# -- N17: the migration names the lifecycle, it does not choose one ---------


def as_version(project: Project, version: str, **over) -> dict:
    state = project.state()
    state["workflow_version"] = version
    state.pop("flow", None)
    state.update(over)
    return state


def test_a_v1_15_state_migrates_to_greenfield(project):
    project.record_governance()
    project.ok("init", session="s")
    project.write_state(as_version(project, "1.15"))

    result = project.ok("migrate", session="s")

    assert result.data["steps"] == ["1.15->1.16"]
    assert result.data["to"] == "1.16"
    assert project.state()["flow"] == "GREENFIELD"


def test_the_flow_migration_is_idempotent(project):
    project.record_governance()
    project.ok("init", session="s")
    project.write_state(as_version(project, "1.15"))
    project.ok("migrate", session="s")
    first = project.state()

    second = project.run("migrate", session="s")

    assert second.exit_code == EXIT_OK
    assert project.state()["flow"] == first["flow"] == "GREENFIELD"


def test_the_flow_migration_never_reads_the_governance_record(project):
    """A migration records what a workflow has been doing, not what it should.

    The record here proposes HOTFIX. The migrated state must still say
    GREENFIELD, because GREENFIELD is what this workflow actually traversed.
    """
    project.record_governance(
        classification={"type": "hotfix", "flow": "HOTFIX"})
    project.ok("init", session="s")
    project.write_state(as_version(project, "1.15"))

    project.ok("migrate", session="s")

    assert project.state()["flow"] == "GREENFIELD"


def test_the_flow_migration_source_names_no_governance_symbol():
    """Belt and braces for the test above, read off the function itself.

    The comparison is over the parsed *code*, with the docstring and comments
    dropped, so prose explaining that the record is not consulted cannot make
    this assertion pass or fail.
    """
    import ast, inspect, textwrap
    func = ast.parse(textwrap.dedent(inspect.getsource(sdle._mig_1_15))).body[0]
    statements = func.body
    if (isinstance(statements[0], ast.Expr)
            and isinstance(statements[0].value, ast.Constant)):
        statements = statements[1:]
    code = chr(10).join(ast.unparse(node) for node in statements)
    for forbidden in ("governance", "classification", "record"):
        assert forbidden not in code, forbidden


def test_the_flow_migration_preserves_every_verified_field(project):
    project.record_governance()
    project.ok("init", session="s")
    before = project.state()
    project.write_state(as_version(project, "1.15"))

    project.ok("migrate", session="s")

    after = project.state()
    for field in sdle.MIGRATION_VERIFIED_FIELDS:
        assert after[field] == before[field], field


def test_a_v1_13_state_migrates_the_whole_chain_and_lands_on_greenfield(project):
    project.record_governance()
    project.ok("init", session="s")
    state = as_version(project, "1.13")
    del state["workitem"]
    project.write_state(state)

    result = project.ok("migrate", session="s")

    assert result.data["steps"] == ["1.13->1.14", "1.14->1.15", "1.15->1.16"]
    assert project.state()["workflow_version"] == "1.16"
    assert project.state()["flow"] == "GREENFIELD"


def test_the_version_chain_declares_the_flow_row(skill_copy):
    """The table is the authority, and it must introduce the new field.

    `migration_covers_every_state_field` matches action text by substring, and
    `flow` is a substring of `workflow`, so that check cannot see this field on
    its own. Asserted here directly instead.
    """
    consts = constants_of(skill_copy)
    assert consts.version_chain[-1] == ("1.15", "1.16")
    import re
    text = (skill_copy.skill_root / "SKILL.md").read_text(encoding="utf-8")
    row = re.search(r"^\| `1\.15` \| `1\.16` \| (.+)$", text, re.MULTILINE)
    assert row, "no 1.15 -> 1.16 VERSION_MIGRATION row"
    assert 'flow: "GREENFIELD"' in row.group(1)


def test_the_state_template_carries_the_flow_field(skill_copy):
    import json
    template = json.loads(
        (skill_copy.skill_root / "templates" / "state.json")
        .read_text(encoding="utf-8"))
    assert template["flow"] == "GREENFIELD"
    assert template["workflow_version"] == "1.16"
    # The GREENFIELD defaults stay exactly as they were.
    assert template["progress"] == "1/18"
    assert set(template["approvals"]) == PRE_T07_APPROVAL_KEYS


# -- N12 / N14 / N16: the flow binds once, and never re-binds ---------------
#
# `state["flow"]` is written by exactly two things: `init`, which binds it from
# the governance record, and the migration, which names GREENFIELD for a
# workflow that predates the field. There is deliberately no `flow set`
# command — a second writer of traversal identity would let the model reshape
# the lifecycle by issuing a command, which is a governance bypass. So the
# only remaining way a flow could change under a running workflow is a
# re-assessment, and that is a refusal with a named remedy.


def tree_map(root: Path) -> dict:
    """Recursive content map of a scratch tree. Local by design."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if ".git" in relative.parts:
            continue
        if path.is_file():
            out[relative.as_posix()] = sdle.sha256_file(path)
    return out


def audit_events(project: Project) -> list[str]:
    """The ordered `event` field of every audit entry."""
    import re
    text = project.audit_file.read_text(encoding="utf-8")
    return re.findall(r"^## AUDIT \[[^\]]*\] \| .+? — (.+)$", text,
                      re.MULTILINE)


def test_init_with_no_governance_record_binds_the_default_flow(project):
    """N12(a). Governance is deliberately not an `init` precondition (T06),
    so the no-record case has to exist — and it has to be the safe one."""
    project.ok("init", session="s")

    state = project.state()
    assert state["flow"] == "GREENFIELD"
    assert state["current_phase"] == "constitution_draft"
    assert "flow_selected" in audit_events(project)


def test_init_after_a_hotfix_assessment_binds_hotfix(project):
    """N12(b). The flow the record proposes is the flow that is traversed."""
    project.record_governance(
        classification={"type": "hotfix", "flow": "HOTFIX"})

    project.ok("init", session="s")

    state = project.state()
    assert state["flow"] == "HOTFIX"
    assert state["current_phase"] == "impact_analysis"
    assert state["progress"] == "2/10"
    assert "flow_selected" in audit_events(project)


def test_the_flow_is_stored_in_exactly_one_place(project):
    """N12(c). `state["flow"]` is the only home for the bound flow.

    The governance record's `classification.flow` is a *proposal* — it is what
    `init` reads — and `execution.json` is execution metadata. Neither is a
    second copy of the binding, so re-reading one of them could never
    disagree with the other.
    """
    import json
    project.record_governance(
        classification={"type": "defect", "flow": "DEFECT_FIX"})
    project.ok("init", session="s")

    execution = json.loads(
        (project.runtime / "execution.json").read_text(encoding="utf-8"))
    assert "flow" not in execution

    state = project.state()
    assert sorted(k for k in state if "flow" in k) == ["flow", "workflow_version"]
    assert state["flow"] == "DEFECT_FIX"


def test_the_flow_selected_entry_names_the_flow_and_its_shape(project):
    """The binding is auditable, which is what makes it reviewable."""
    project.record_governance(
        classification={"type": "hotfix", "flow": "HOTFIX"})
    project.ok("init", session="s")

    text = project.audit_file.read_text(encoding="utf-8")
    entry = [block for block in text.split("## AUDIT ")
             if "flow_selected" in block]
    assert len(entry) == 1, text
    assert "HOTFIX" in entry[0]
    assert "10 phases" in entry[0] and "3 gates" in entry[0]


REASSESSED = {"type": "hotfix", "flow": "HOTFIX"}


def reassess(project: Project, classification: dict) -> None:
    """Re-record governance with a different flow, mid-run."""
    result = project.record_governance(classification=classification)
    assert result.exit_code == EXIT_OK, result


def test_a_reassessed_flow_refuses_the_next_advance(project):
    """N14(a) — and the B1/NB-6 property, re-proved for the new refusal."""
    project.record_governance()
    project.ok("init", session="s")
    project.write_artifact(".specify/memory/constitution.md")
    reassess(project, REASSESSED)

    ledger_before = project.audit_file.read_bytes()
    before = tree_map(project.root)

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "flow_mismatch", result
    assert result.data["bound"] == "GREENFIELD"
    assert result.data["proposed"] == "HOTFIX"
    assert "re-assess with flow GREENFIELD" in result.envelope["message"]
    assert project.audit_file.read_bytes() == ledger_before, (
        "a refused advance appended to the append-only ledger")
    assert tree_map(project.root) == before
    verify = project.run("audit", "verify")
    assert verify.exit_code == EXIT_OK, verify
    assert verify.data["matches"] is True


def test_a_reassessed_flow_refuses_the_next_gate_approval(project):
    """N14(b). `cmd_gate_approve` appends before it moves, so the refusal has
    to fire in its early pure-reader precheck or it strands an approval that
    never happened."""
    project.record_governance()
    project.ok("init", session="s")
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution")
    review_for_gate(project, "gate_constitution")
    reassess(project, REASSESSED)

    ledger_before = project.audit_file.read_bytes()
    approvals_before = ledger_before.count(b"**Gate Decision:** APPROVED")
    before = tree_map(project.root)

    result = project.run("gate", "approve", "--gate", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "flow_mismatch", result
    ledger_after = project.audit_file.read_bytes()
    assert ledger_after == ledger_before, (
        "a refused gate approval appended to the append-only ledger")
    assert ledger_after.count(b"**Gate Decision:** APPROVED") == approvals_before
    assert tree_map(project.root) == before
    verify = project.run("audit", "verify")
    assert verify.exit_code == EXIT_OK, verify
    assert verify.data["matches"] is True


def test_a_reassessed_flow_refuses_the_next_skip(project):
    """N14(c). The NB-6 sibling: `cmd_skip` has the same ordering."""
    project.record_governance()
    project.ok("init", session="s")
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution")
    review_for_gate(project, "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution")

    state = project.state()
    state["status"] = "failed"
    project.write_state(state)
    armed = project.run("skip")
    assert armed.exit_code == EXIT_OK, armed
    assert armed.data["pending"] is True, armed

    reassess(project, REASSESSED)
    ledger_before = project.audit_file.read_bytes()
    skipped_before = ledger_before.count(b"SKIPPED WITH WARNING")
    before = tree_map(project.root)

    result = project.run("skip", "--confirm")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "flow_mismatch", result
    ledger_after = project.audit_file.read_bytes()
    assert ledger_after == ledger_before, (
        "a refused skip appended to the append-only ledger")
    assert ledger_after.count(b"SKIPPED WITH WARNING") == skipped_before
    assert tree_map(project.root) == before
    verify = project.run("audit", "verify")
    assert verify.exit_code == EXIT_OK, verify
    assert verify.data["matches"] is True


def test_re_assessing_the_same_flow_changes_nothing(project):
    """The refusal is about disagreement, not about re-assessment.

    Without this the test above would pass for the uninteresting reason that
    any second assessment refuses, which would make `governance assess`
    unusable after `init`.
    """
    project.record_governance()
    project.ok("init", session="s")
    project.write_artifact(".specify/memory/constitution.md")
    reassess(project, {"type": "enhancement", "flow": "GREENFIELD"})

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_OK, result
    assert project.state()["current_phase"] == "gate_constitution"
    assert project.state()["flow"] == "GREENFIELD"


def test_the_governance_refusals_are_not_masked_by_the_flow_check(project):
    """A stale record cannot authorise an advance, and it cannot authorise a
    flow disagreement either — so `governance_stale` still wins.

    The three-step ordering in `apply_advance` exists for exactly this: the
    record is validated with no `state` (which writes nothing) *before* the
    flow is compared, so the reason the user is given is the real one.
    """
    project.record_governance()
    project.ok("init", session="s")
    project.write_artifact(".specify/memory/constitution.md")
    reassess(project, REASSESSED)
    target = project.root / "requirements" / "todo-api.md"
    target.write_text(target.read_text(encoding="utf-8") + "\n- PATCH /todos\n",
                      encoding="utf-8", newline="\n")

    ledger_before = project.audit_file.read_bytes()

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_stale", result
    assert project.audit_file.read_bytes() == ledger_before


def test_a_pre_v1_16_state_with_a_hotfix_record_refuses_flow_mismatch(project):
    """N16 — D10's declared consequence, implemented rather than assumed away.

    A workflow initialised before v1.16 was traversing GREENFIELD whatever its
    T06 record proposed, because nothing routed on the record. The migration
    says GREENFIELD, which is the truth about what it has been doing, and the
    next advance then refuses rather than silently switching lifecycle
    underneath it. One command is the remedy, and the message names it.
    """
    project.record_governance(
        classification={"type": "hotfix", "flow": "HOTFIX"})
    project.ok("init", session="s")
    # Re-shape the state into its pre-v1.16 form: the field did not exist.
    state = project.state()
    state["workflow_version"] = "1.15"
    state.pop("flow", None)
    state["current_phase"] = "constitution_draft"
    state["progress"] = "2/18"
    project.write_state(state)

    migrated = project.ok("migrate", session="s")

    assert migrated.data["steps"] == ["1.15->1.16"]
    assert project.state()["flow"] == "GREENFIELD"

    project.write_artifact(".specify/memory/constitution.md")
    ledger_before = project.audit_file.read_bytes()

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "flow_mismatch", result
    assert result.data == {"workitem": project.workitem,
                           "bound": "GREENFIELD", "proposed": "HOTFIX"}
    assert "reset workflow" in result.envelope["message"]
    assert project.audit_file.read_bytes() == ledger_before


# --------------------------------------------------------------------------
# N1-N11, N13, N15, N26 — the five flows driven end to end through the CLI
# --------------------------------------------------------------------------
#
# The driver below is deliberately **table-driven off the bound flow itself**
# rather than being five hand-written scripts. If it restated a traversal it
# would only prove that the test and the engine were written by the same hand;
# reading the phase list out of `constants.flows[...]` and then walking it
# through the real CLI proves the engine actually executes what the table
# declares. The per-phase artifact recipe is the only hand-written part,
# because that is the part Spec Kit would produce and the suite never invokes
# Spec Kit.

FEATURE = "001-todo-api"
IMPACT_ARTIFACT = "reviews/impact-analysis-2026-05-26-1430.md"

ALL_FLOWS = ["GREENFIELD", "BROWNFIELD_DISCOVERY", "ITERATIVE",
             "DEFECT_FIX", "HOTFIX"]


def prepare(project: Project, phase: str, feature_dir: str) -> None:
    """Stand in for the generation step that produces ``phase``'s artifact.

    Gate phases appear here as no-ops on purpose: a gate approves the artifact
    the phase before it produced, so it has nothing of its own to write.
    """
    if phase == "impact_analysis":
        project.write_artifact(IMPACT_ARTIFACT)
        project.ok("artifact", "record",
                   "--phase", "impact_analysis", "--path", IMPACT_ARTIFACT)
        project.ok("artifact", "review", "--path", IMPACT_ARTIFACT,
                   "--type", "impact-analysis", "--result", "PASS",
                   "--actor-type", "agent", "--actor-name", "sdle-orchestrator")
    elif phase == "constitution_draft":
        project.write_artifact(".specify/memory/constitution.md")
    elif phase == "spec_draft":
        project.write_artifact(f"{feature_dir}/spec.md")
        project.ok("feature", "resolve")
    elif phase == "plan_draft":
        project.write_artifact(f"{feature_dir}/plan.md")
    elif phase == "checklist_draft":
        project.write_artifact(f"{feature_dir}/checklist.md")
    elif phase == "tasks_draft":
        project.write_artifact(f"{feature_dir}/tasks.md")
    elif phase == "analyze":
        project.write_artifact(f"{feature_dir}/tasks.md",
                               "# Tasks (refined by analysis)\n\n" + "T001. " * 40)
        project.ok("drift", "rebaseline", "--gate", "gate_tasks")
    elif phase == "design_generation":
        project.write_artifact("design/app/app-design.md")
        project.write_artifact("design/db/db-design.md")
    elif phase == "implement":
        project.ok("implement", "preflight", "--bypass")
        project.ok("manifest", "build", "--summary", "Implemented the change.")
    elif phase == "security_review":
        begun = project.ok("security-review", "begin")
        project.write_artifact(begun.data["review_filename"])


def bind(project: Project, flow: str) -> None:
    """Assess with ``flow`` and `init`, so `init` binds it.

    The WorkItem *type* is held at `enhancement` for every flow on purpose:
    type and flow are validated independently and nothing cross-checks them,
    so holding the type constant keeps this driver a test of the flow alone.
    """
    project.record_governance(
        classification={"type": "enhancement", "flow": flow})
    project.ok("init", session="drive")


def drive(project: Project, flow: str, stop: str | None = None) -> list[str]:
    """Walk ``flow`` through the real CLI, returning every phase state seen."""
    consts = constants_of(project)
    phases = list(consts.flow(flow).phases)
    feature_dir = project.feature_dir(FEATURE)

    bind(project, flow)
    seen = ["requirements_check", project.state()["current_phase"]]

    for index in range(1, len(phases) - 1):
        phase = phases[index]
        if stop is not None and phase == stop:
            return seen
        prepare(project, phase, feature_dir)
        gate_key = consts.phase_to_gate_key.get(phase)
        if gate_key:
            review_for_gate(project, gate_key)
            project.ok("gate", "approve", "--gate", gate_key)
        else:
            project.ok("advance", "--to", phases[index + 1])
        seen.append(project.state()["current_phase"])
    return seen


# -- N1-N5: each flow traverses exactly what it declares --------------------


@pytest.mark.parametrize("flow", ALL_FLOWS)
def test_a_flow_traverses_exactly_its_declared_phases(git_project, flow):
    """N1-N5. One drive per flow; the assertions are grouped because they are
    facts about the same single run and re-driving would only cost minutes."""
    declared = list(constants_of(git_project).flow(flow).phases)
    expected_gates = list(constants_of(git_project).flow(flow).gate_keys)

    seen = drive(git_project, flow)

    assert seen == declared, flow
    state = git_project.state()
    assert state["flow"] == flow
    assert state["current_phase"] == "complete"
    assert state["status"] == "completed"

    total = len([p for p in declared if p != "complete"])
    assert state["progress"] == f"{total}/{total}"

    approved = sorted(key for key, entry in state["approvals"].items()
                      if entry and entry.get("decision") == "approved")
    assert approved == sorted(expected_gates), flow
    # A gate the flow does not run stays null forever — never a ninth key,
    # never a fabricated approval.
    assert sorted(state["approvals"]) == sorted(PRE_T07_APPROVAL_KEYS)
    for key in set(PRE_T07_APPROVAL_KEYS) - set(expected_gates):
        assert state["approvals"][key] is None, (flow, key)

    verify = git_project.ok("audit", "verify")
    assert verify.data["matches"] is True
    assert verify.data["chain_ok"] is True


def test_greenfield_drives_the_transcript_traversal(git_project):
    """N1's compatibility half: the flow-driven traversal is the transcript's,
    element for element, and `impact_analysis` appears nowhere in the run."""
    seen = drive(git_project, "GREENFIELD")

    assert seen == EXPECTED_TRAVERSAL
    history = [entry["phase"] for entry in git_project.state()["phase_history"]]
    assert "impact_analysis" not in history
    assert "impact_analysis" not in git_project.audit_file.read_text(
        encoding="utf-8")


def test_iterative_never_reaches_the_constitution(git_project):
    """N2. The constitution is the repository-level baseline an iterative
    WorkItem inherits, so ITERATIVE does not re-draft it."""
    seen = drive(git_project, "ITERATIVE")

    assert seen[1] == "spec_draft"
    assert "constitution_draft" not in seen
    assert "gate_constitution" not in seen
    assert "impact_analysis" not in seen
    assert git_project.state()["approvals"]["gate_constitution"] is None
    assert git_project.state()["progress"] == "16/16"


def test_defect_fix_starts_with_the_impact_analysis(git_project):
    """N3."""
    seen = drive(git_project, "DEFECT_FIX")

    assert seen[1] == "impact_analysis"
    for absent in ("design_generation", "gate_design", "checklist_draft"):
        assert absent not in seen, absent
    assert git_project.state()["progress"] == "14/14"


def test_hotfix_is_short_and_still_governed(git_project):
    """N4. Three gates, and the terminal human gate still writes the summary."""
    import json
    seen = drive(git_project, "HOTFIX")

    assert seen[1] == "impact_analysis"
    assert git_project.state()["progress"] == "10/10"

    shown = git_project.ok("gate", "show", "--gate", "gate_implement").data
    assert (shown["gate_number"], shown["gate_total"]) == (2, 3)

    summaries = list(git_project.runtime.glob("completion-summary*.json"))
    assert len(summaries) == 1
    summary = json.loads(summaries[0].read_text(encoding="utf-8"))
    assert summary["flow"] == "HOTFIX"
    assert summary["all_gates_approved"] is True


def test_brownfield_discovery_is_greenfield_until_t08_changes_it(git_project):
    """N5. **T08 (contract §14) owns changing this.**

    BROWNFIELD_DISCOVERY cannot meaningfully differ from GREENFIELD before the
    discovery phase §14 introduces exists, so it is declared equal at T07 and
    pinned here. When T08 edits its FLOW_PHASES row this test fails, which is
    the point: the change must be visible, not silent.
    """
    seen = drive(git_project, "BROWNFIELD_DISCOVERY")

    assert seen == EXPECTED_TRAVERSAL
    flows = constants_of(git_project).flows
    assert (list(flows["BROWNFIELD_DISCOVERY"].phases)
            == list(flows["GREENFIELD"].phases))


def test_the_five_traversals_are_pairwise_distinct_except_the_declared_pair(
        skill_copy):
    """N6 — the exit criterion, asserted directly.

    Driven traversals equal the declared phase lists (the parametrised test
    above), so distinctness is asserted on the declarations, where all ten
    pairs can be compared without ten more full runs.
    """
    flows = constants_of(skill_copy).flows
    equal_pairs = set()
    for left in ALL_FLOWS:
        for right in ALL_FLOWS:
            if left < right and flows[left].phases == flows[right].phases:
                equal_pairs.add((left, right))
    assert equal_pairs == {("BROWNFIELD_DISCOVERY", "GREENFIELD")}, equal_pairs


# -- N7: impact_analysis is governed, and gateless ------------------------


def test_the_impact_analysis_artifact_is_fingerprinted(git_project):
    """N7(3). `artifact record` is the whole of "governed without a gate":
    size floor, SHA-256, one audit event, retry counter reset."""
    bind(git_project, "DEFECT_FIX")
    git_project.write_artifact(IMPACT_ARTIFACT)
    before = git_project.audit_file.read_text(encoding="utf-8")

    recorded = git_project.ok("artifact", "record", "--phase",
                              "impact_analysis", "--path", IMPACT_ARTIFACT)

    sha = sdle.sha256_file(git_project.root / IMPACT_ARTIFACT)
    assert recorded.data["sha256"] == sha
    assert recorded.data["optional"] is False
    state = git_project.state()
    assert state["current_artifact"] == IMPACT_ARTIFACT
    assert state["current_artifact_sha"] == sha
    after = git_project.audit_file.read_text(encoding="utf-8")
    assert after.count("artifact_recorded") == before.count("artifact_recorded") + 1


def test_the_impact_analysis_review_is_bound_to_that_exact_sha(git_project):
    """N7(4) — TP-011 with zero new code. Editing the file afterwards makes
    the review stale by the mechanism that already existed."""
    import json
    bind(git_project, "DEFECT_FIX")
    git_project.write_artifact(IMPACT_ARTIFACT)
    git_project.ok("artifact", "record", "--phase", "impact_analysis",
                   "--path", IMPACT_ARTIFACT)
    sha = sdle.sha256_file(git_project.root / IMPACT_ARTIFACT)
    git_project.ok("artifact", "review", "--path", IMPACT_ARTIFACT,
                   "--type", "impact-analysis", "--result", "PASS",
                   "--actor-type", "agent", "--actor-name", "sdle-orchestrator")

    def recorded() -> dict:
        ledger = json.loads(
            (git_project.runtime / "reviews.json").read_text(encoding="utf-8"))
        entries = [record for record in ledger["reviews"]
                   if record["path"] == IMPACT_ARTIFACT]
        assert len(entries) == 1, entries
        return entries[0]

    entry = recorded()
    assert entry["sha256"] == sha
    assert entry["result"] == "PASS"
    assert entry["reviewType"] == "impact-analysis"
    assert entry["actor"] == {"type": "agent", "name": "sdle-orchestrator"}

    # "Currently reviewed" is derived from SHAs on every call, never stored,
    # so rewriting the file is enough to make it stale. No new mechanism.
    fresh = git_project.ok("artifact", "reviews", "--path", IMPACT_ARTIFACT)
    assert fresh.data["status"][IMPACT_ARTIFACT]["current"] is True

    git_project.write_artifact(
        IMPACT_ARTIFACT, "# Rewritten impact analysis\n\n" + "word " * 40)
    assert sdle.sha256_file(git_project.root / IMPACT_ARTIFACT) != sha
    assert recorded()["sha256"] == sha, (
        "the recorded review must still name the SHA it reviewed")
    stale = git_project.ok("artifact", "reviews", "--path", IMPACT_ARTIFACT)
    assert stale.data["status"][IMPACT_ARTIFACT]["current"] is False


@pytest.mark.parametrize("flow", ["DEFECT_FIX", "HOTFIX"])
def test_advancing_out_of_impact_analysis_lands_on_spec_draft(git_project, flow):
    """N7(5)."""
    bind(git_project, flow)
    prepare(git_project, "impact_analysis", git_project.feature_dir(FEATURE))

    git_project.ok("advance", "--to", "spec_draft")

    assert git_project.state()["current_phase"] == "spec_draft"


def test_under_greenfield_impact_analysis_is_a_forward_jump_not_unknown(
        git_project):
    """N7(6) / D17. The two refusals mean different things and the payload
    says which: a phase the registry does not know at all is `unknown_phase`;
    a real phase this flow does not run is a forward jump."""
    bind(git_project, "GREENFIELD")

    refused = git_project.run("advance", "--to", "impact_analysis")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "forward_jump", refused
    assert refused.data["in_flow"] is False
    assert refused.data["flow"] == "GREENFIELD"
    assert refused.data["requested_index"] is None

    unknown = git_project.run("advance", "--to", "not_a_phase_at_all")
    assert unknown.exit_code == EXIT_REFUSED, unknown
    assert unknown.reason == "unknown_phase", unknown


@pytest.mark.parametrize("action", ["approve", "reject"])
def test_no_gate_can_ever_be_current_at_impact_analysis(git_project, action):
    """N7(7). It is not "a gate we skip" — there is no gate machinery for it
    at all, so every gate command refuses and writes nothing."""
    bind(git_project, "DEFECT_FIX")
    prepare(git_project, "impact_analysis", git_project.feature_dir(FEATURE))
    ledger_before = git_project.audit_file.read_bytes()
    state_before = git_project.state_file.read_bytes()

    # `reject` additionally requires a reason; that argument is part of the
    # command's shape, not part of what is being asserted here.
    extra = ["--reason", "not a gate"] if action == "reject" else []

    unknown = git_project.run("gate", action, "--gate",
                              "gate_impact_analysis", *extra)
    assert unknown.exit_code == EXIT_REFUSED, unknown
    assert unknown.reason == "unknown_gate", unknown

    wrong = git_project.run("gate", action, "--gate", "gate_spec", *extra)
    assert wrong.exit_code == EXIT_REFUSED, wrong
    assert wrong.reason == "not_at_gate", wrong

    assert git_project.audit_file.read_bytes() == ledger_before
    assert git_project.state_file.read_bytes() == state_before


# -- N9, N10, N11: gate discipline is unchanged inside every flow ----------


@pytest.mark.parametrize("flow", ALL_FLOWS)
def test_advancing_past_an_unapproved_gate_refuses_in_every_flow(
        git_project, flow):
    """N9. A gate inside a flow is exactly as unconditional as it always was."""
    consts = constants_of(git_project)
    phases = list(consts.flow(flow).phases)
    first_gate = consts.flow(flow).gate_phases[0]
    beyond = phases[phases.index(first_gate) + 1]

    drive(git_project, flow, stop=first_gate)
    # `drive` stops *before* producing the gate's own step, so walk the one
    # remaining generation phase by hand to stand on the gate itself.
    while git_project.state()["current_phase"] != first_gate:
        current = git_project.state()["current_phase"]
        prepare(git_project, current, git_project.feature_dir(FEATURE))
        git_project.ok("advance", "--to", phases[phases.index(current) + 1])

    ledger_before = git_project.audit_file.read_bytes()
    refused = git_project.run("advance", "--to", beyond)

    assert refused.exit_code == EXIT_REFUSED, (flow, refused)
    assert refused.reason == "gate_not_approved", (flow, refused)
    assert git_project.audit_file.read_bytes() == ledger_before


def test_a_registry_phase_outside_the_flow_is_a_forward_jump(git_project):
    """N10. `design_generation` is a real registry phase; HOTFIX does not run
    it, so it is a forward jump and never `unknown_phase`."""
    bind(git_project, "HOTFIX")

    refused = git_project.run("advance", "--to", "design_generation")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "forward_jump", refused
    assert refused.data["in_flow"] is False
    assert refused.data["flow"] == "HOTFIX"

    unknown = git_project.run("advance", "--to", "design_genration")
    assert unknown.reason == "unknown_phase", unknown


def test_approving_a_gate_a_flow_does_not_run_refuses_and_writes_nothing(
        git_project):
    """N11. `gate_design` is never the current phase under HOTFIX."""
    bind(git_project, "HOTFIX")
    ledger_before = git_project.audit_file.read_bytes()
    state_before = git_project.state_file.read_bytes()

    refused = git_project.run("gate", "approve", "--gate", "gate_design")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "not_at_gate", refused
    assert git_project.audit_file.read_bytes() == ledger_before
    assert git_project.state_file.read_bytes() == state_before
    assert git_project.state()["approvals"]["gate_design"] is None


# -- N13, N15, N26 --------------------------------------------------------


def test_no_read_only_command_writes_the_flow(git_project):
    """N13. `init` and `migrate` are the only writers of `state["flow"]`.

    Proved by a recursive SHA map of the whole repository across every
    read-only command that touches governance or the constants — if any of
    them wrote anything at all, the map would move.
    """
    bind(git_project, "DEFECT_FIX")
    before = tree_map(git_project.root)

    git_project.ok("constants")
    git_project.ok("flow", "show")
    git_project.ok("governance", "show")
    git_project.ok("governance", "gates")
    git_project.ok("state", "get", "--field", "flow")
    git_project.ok("header")

    assert tree_map(git_project.root) == before
    assert git_project.state()["flow"] == "DEFECT_FIX"


def test_only_init_and_the_migration_write_the_flow_field():
    """N13's structural half, and the sharper statement of it.

    Read off the AST: the set of functions in `scripts/sdle.py` that assign
    `state["flow"]` is exactly `{cmd_init, _mig_1_15}`. A `flow set` command
    could not be added without appearing here, and neither could a quiet
    re-binding inside `apply_advance` or `gate approve`.
    """
    import ast
    source = (REPO_ROOT / "scripts" / "sdle.py").read_text(encoding="utf-8")
    writers = set()
    for fn in ast.walk(ast.parse(source)):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (isinstance(target, ast.Subscript)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "state"
                        and isinstance(target.slice, ast.Constant)
                        and target.slice.value == "flow"):
                    writers.add(fn.name)
    assert writers == {"cmd_init", "_mig_1_15"}, sorted(writers)


def test_a_defect_fix_run_never_grows_a_ninth_approval_key(git_project):
    """N15. `impact_analysis` is gateless, so no state it passes through may
    ever carry an approval for it — not even a null one."""
    consts = constants_of(git_project)
    phases = list(consts.flow("DEFECT_FIX").phases)
    feature_dir = git_project.feature_dir(FEATURE)

    bind(git_project, "DEFECT_FIX")
    assert sorted(git_project.state()["approvals"]) == sorted(PRE_T07_APPROVAL_KEYS)

    for index in range(1, len(phases) - 1):
        phase = phases[index]
        prepare(git_project, phase, feature_dir)
        gate_key = consts.phase_to_gate_key.get(phase)
        if gate_key:
            review_for_gate(git_project, gate_key)
            git_project.ok("gate", "approve", "--gate", gate_key)
        else:
            git_project.ok("advance", "--to", phases[index + 1])
        keys = sorted(git_project.state()["approvals"])
        assert keys == sorted(PRE_T07_APPROVAL_KEYS), (phase, keys)
        assert "gate_impact_analysis" not in keys


def test_two_workitems_on_different_flows_advance_independently(git_project):
    """N26 — T02's isolation property, re-proved under flows.

    Two WorkItems in one repository, one GREENFIELD and one HOTFIX. Driving
    the second must not touch the first's `state.json` or `audit.md` by a
    single byte.
    """
    first = git_project.as_workitem(git_project.workitem)
    first.record_governance(
        classification={"type": "enhancement", "flow": "GREENFIELD"})
    first.ok("init", session="first")
    assert first.state()["flow"] == "GREENFIELD"
    assert first.state()["current_phase"] == "constitution_draft"

    git_project.ok("workitem", "create", "--name", "Second Item")
    second_id = git_project.run("workitem", "list").data["workitems"][-1]["id"]
    second = git_project.as_workitem(second_id)

    frozen_state = first.state_file.read_bytes()
    frozen_audit = first.audit_file.read_bytes()

    second.record_governance(
        classification={"type": "enhancement", "flow": "HOTFIX"})
    second.ok("init", session="second")
    prepare(second, "impact_analysis", second.feature_dir(FEATURE))
    second.ok("advance", "--to", "spec_draft")

    assert second.state()["flow"] == "HOTFIX"
    assert second.state()["current_phase"] == "spec_draft"
    assert first.state_file.read_bytes() == frozen_state
    assert first.audit_file.read_bytes() == frozen_audit
    assert first.state()["flow"] == "GREENFIELD"


# -- N25: `flow show` — asking the script instead of reading a table -------


def test_flow_show_reports_the_bound_flow_and_where_it_is(git_project):
    """N25. SKILL.md's own instruction is "ask the script"; this is the
    command that makes that possible for traversal."""
    bind(git_project, "HOTFIX")

    shown = git_project.ok("flow", "show").data

    consts = constants_of(git_project)
    hotfix = consts.flow("HOTFIX")
    assert shown["name"] == "HOTFIX"
    assert shown["phases"] == list(hotfix.phases)
    assert shown["gate_phases"] == list(hotfix.gate_phases)
    assert shown["gate_keys"] == list(hotfix.gate_keys)
    assert shown["gate_total"] == 3
    assert shown["phase_count"] == 10
    assert shown["current_phase"] == "impact_analysis"
    assert shown["position"] == 2
    assert shown["progress"] == "2/10"
    assert shown["next_phase"] == "spec_draft"
    # `impact_analysis` is not a gate, so it has no gate number.
    assert shown["gate_number"] is None
    assert shown["label"] == "Impact Analysis"
    assert shown["proposed_flow"] == "HOTFIX"
    assert shown["agrees"] is True


def test_flow_show_makes_a_disagreement_visible_before_it_refuses(git_project):
    """A disagreement should be *readable* before it becomes a refusal at the
    next advance — that is what makes the remedy actionable."""
    bind(git_project, "GREENFIELD")
    reassess(git_project, {"type": "hotfix", "flow": "HOTFIX"})

    shown = git_project.ok("flow", "show").data

    assert shown["name"] == "GREENFIELD"
    assert shown["proposed_flow"] == "HOTFIX"
    assert shown["agrees"] is False


def test_flow_show_writes_nothing(git_project):
    """N25's read-only half, asserted over the whole repository."""
    bind(git_project, "DEFECT_FIX")
    before = tree_map(git_project.root)

    git_project.ok("flow", "show")
    git_project.ok("flow", "show")

    assert tree_map(git_project.root) == before


def test_flow_show_before_init_says_so_and_writes_nothing(project):
    """N25's other half: with no workflow there is no bound flow, and the
    engine says which command starts one rather than inventing a default."""
    before = tree_map(project.root)

    result = project.run("flow", "show")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "state_unreadable", result
    assert "init" in result.envelope["message"]
    assert tree_map(project.root) == before


def test_there_is_no_flow_subcommand_that_writes(project):
    """The `flow` group is read-only by construction: `show` is its only
    member. A `flow set` would be a second writer of traversal identity."""
    project.record_governance()
    project.ok("init", session="s")

    for attempted in ("set", "select", "bind"):
        result = project.run("flow", attempted, "--flow", "HOTFIX")
        assert result.exit_code == EXIT_USAGE, (attempted, result)
    assert project.state()["flow"] == "GREENFIELD"


def test_constants_reports_every_flow(skill_copy):
    """`constants` is how a reader sees all five without opening the engine."""
    shown = skill_copy.ok("constants").data

    assert set(shown["flows"]) == set(sdle.ENGINEERING_FLOWS)
    assert shown["flows"]["GREENFIELD"]["phases"] == GREENFIELD_GOLDEN
    assert shown["flows"]["GREENFIELD"]["gate_total"] == 8
    assert shown["flows"]["HOTFIX"]["phase_count"] == 10
    # The pre-T07 keys are all still there: nothing was removed to add this.
    for key in ("phase_sequence", "phase_count", "next_phase",
                "phase_to_gate_key", "gate_number", "gate_phases",
                "artifact_ownership", "phase_label", "progress",
                "gate_to_execution_phase", "version_chain", "skill_root",
                "project_root"):
        assert key in shown, key
