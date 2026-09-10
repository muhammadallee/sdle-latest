"""Progressive capabilities and product subagents (T10).

Contract §16 asks for two things at once and they pull against each other:
*optimise reasoning quality and context*, and *do not move authority back into
prompts*. This file exists to prove the second half held while the first was
delivered.

Three claims, each driven rather than asserted:

1. **Which capability files a phase loads is a parsed constant**, not a
   judgement the model re-makes each turn. `CAPABILITY_MAP` lives in SKILL.md,
   the engine parses it, and `lint-skill` fails loudly on a row that names an
   unknown phase, a file that does not exist, a module nothing names, or a row
   that requires the whole set.
2. **A fresh process can reconstruct a WorkItem from disk alone** — §16's exit
   criterion and TP-006 — through one read-only command, `resume`, which
   composes existing derivations rather than adding a second copy of any of
   them.
3. **A product subagent can inspect and reason and nothing else**, and every
   one of those inabilities fails a *named* check the moment it stops being
   true.

What is deliberately NOT claimed here is recorded in ADR-007's honesty table
and repeated in `test_a25_the_enforcement_split_is_stated_without_being_softened`:
that a declared `tools:` list is applied and that a frontmatter hook fires are
Claude Code's guarantees, not SDLE's; and that the parent delegates at all,
that `--actor-name` is truthful, and that a human rather than the orchestrator
typed `approve` are convention only. Two of those three predate T10.
"""

from __future__ import annotations

import ast
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import (
    DRY_RUN_SUBSTITUTIONS,
    REPO_ROOT,
    STABILIZATION_01_TEST_ADDITIONS,
    STABILIZATION_01_TEST_EDITS,
    STABILIZATION_01_TEST_REMOVALS,
    Project,
    apply_dry_run_substitutions,
    assert_frozen_module,
    sdle,
)
from test_units_flow_model import bind, tree_map

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3

SKILL_ROOT = REPO_ROOT / ".claude" / "skills" / "sdle"
MODULES = SKILL_ROOT / "modules"
AGENTS = REPO_ROOT / ".claude" / "agents"

PRODUCT_AGENTS = (
    "sdle-code-review.md",
    "sdle-design-review.md",
    "sdle-discovery.md",
    "sdle-security-review.md",
)
NEW_CAPABILITY_FILES = ("design-review.md", "code-review.md")

CONSTS = sdle.load_constants(
    sdle.resolve_paths(str(REPO_ROOT), str(SKILL_ROOT)))
REGISTRY = tuple(CONSTS.phase_sequence)
GATE_PHASES = tuple(CONSTS.gate_phases)


@pytest.fixture(scope="module")
def repo() -> Project:
    """The real repository, addressed read-only.

    `constants` and `lint-skill` resolve no WorkItem, read no state and write
    nothing. Driving them here is therefore an observation of what actually
    ships rather than of a fixture copy, which is the whole point for the
    anti-vacuity cases below.
    """
    return Project(REPO_ROOT, SKILL_ROOT)


@pytest.fixture
def skill_copy(tmp_path: Path) -> Project:
    """A writable copy of everything `lint-skill` reads.

    Includes `.claude/agents/`, because the product-agent checks are emitted
    only when the directory exists and a fixture without it would prove
    nothing.
    """
    root = tmp_path / "repo"
    (root / ".claude" / "skills").mkdir(parents=True)
    shutil.copytree(SKILL_ROOT, root / ".claude" / "skills" / "sdle")
    shutil.copytree(AGENTS, root / ".claude" / "agents")
    (root / "docs").mkdir()
    shutil.copy(REPO_ROOT / "README.md", root / "README.md")
    shutil.copy(REPO_ROOT / "docs" / "SDLE-Reference-Guide.md",
                root / "docs" / "SDLE-Reference-Guide.md")
    return Project(root, root / ".claude" / "skills" / "sdle")


def capability_map(project: Project) -> dict[str, list[str]]:
    return project.ok("constants").data["capability_map"]


def modules_on_disk() -> list[str]:
    return sorted(p.name for p in MODULES.glob("*.md") if p.is_file())


# ==========================================================================
# The capability map — a parsed constant, not a judgement
# ==========================================================================


def test_the_registry_is_the_size_this_file_assumes():
    """Non-vacuity guard for every parametrisation below."""
    assert len(REGISTRY) == 21
    assert len(GATE_PHASES) == 8


@pytest.mark.parametrize("phase", REGISTRY)
def test_n1_every_registry_phase_has_a_capability_row(repo, phase):
    """N1/A1. Driven through `constants` and parametrised over the registry,
    so a phase added without a row fails here by name rather than silently
    loading nothing."""
    mapping = capability_map(repo)
    assert phase in mapping, f"{phase} has no CAPABILITY_MAP row"
    assert mapping[phase], f"{phase} maps to an empty capability set"


def test_n1_no_row_names_a_phase_outside_the_registry(repo):
    mapping = capability_map(repo)
    assert sorted(mapping) == sorted(REGISTRY)


def test_n2_every_named_capability_exists_and_none_is_the_orchestrator(repo):
    """N2/A2. `SKILL.md` is the always-loaded orchestrator, never a capability
    — naming it would make "load only what this phase needs" meaningless."""
    named = {value for row in capability_map(repo).values() for value in row}
    assert named, "the capability map named nothing at all"
    for value in sorted(named):
        assert (SKILL_ROOT / value).is_file(), f"{value} does not exist"
        assert Path(value).name != "SKILL.md", value


def test_n3_loading_is_progressive_and_the_union_is_what_is_on_disk(repo):
    """N3/A3. Every row is a *strict* subset of the union, and the union is
    exactly the capability files present. Non-vacuity is guarded twice: the
    union must be substantial, and at least one phase must need exactly one
    file — otherwise "progressive" would be a word rather than a property."""
    mapping = capability_map(repo)
    union = {value for row in mapping.values() for value in row}

    assert len(union) >= 4, union
    assert sorted(Path(v).name for v in union) == modules_on_disk()

    for phase, row in sorted(mapping.items()):
        assert set(row) < union, (
            f"{phase} requires the entire capability set, so nothing is "
            "progressive about it")
    assert any(len(row) == 1 for row in mapping.values()), (
        "no phase needs exactly one capability — the map is not selective")


def test_n4_gate_protocol_is_loaded_at_every_gate_and_nowhere_else(repo):
    """N4/A4. The gate capability is not a judgement call either."""
    mapping = capability_map(repo)
    gate_file = "modules/gate-protocol.md"
    for phase in REGISTRY:
        loaded = gate_file in mapping[phase]
        assert loaded is (phase in GATE_PHASES), (phase, mapping[phase])


def test_n5_no_capability_file_on_disk_is_an_orphan(repo):
    """N5/A3. A module nothing maps is a file nobody is told to read."""
    named = {Path(v).name
             for row in capability_map(repo).values() for v in row}
    assert sorted(named) == modules_on_disk()


def test_n7_every_capability_cross_reference_resolves_and_is_mapped(repo):
    """N7/A5/F7. The map is a floor, not a ceiling: remediation at
    `gate_design` sends you back to phase execution and must keep working."""
    named = {value for row in capability_map(repo).values() for value in row}
    pattern = re.compile(r"modules/[A-Za-z0-9._-]+\.md")
    seen = 0
    for value in sorted(named):
        body = (SKILL_ROOT / value).read_text(encoding="utf-8")
        for ref in sorted(set(pattern.findall(body))):
            seen += 1
            assert (SKILL_ROOT / ref).is_file(), f"{value} -> {ref}"
            assert ref in named, f"{value} -> {ref} is in no CAPABILITY_MAP row"
    assert seen >= 3, "no cross-reference was examined; the check is vacuous"


def test_n8_constants_exposes_the_map(repo):
    result = repo.ok("constants")
    assert "capability_map" in result.data
    # Nothing that was there before was dropped to make room for it.
    for key in ("phase_sequence", "flows", "gate_to_execution_phase",
                "version_chain"):
        assert key in result.data


def test_n8_a_renamed_capability_heading_fails_loudly(skill_copy):
    """N8/A1. The `test_an_empty_table_never_yields_an_empty_default` pattern:
    a table that silently parsed to nothing would let the orchestrator load
    nothing and call that success."""
    path = skill_copy.skill_root / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("### CAPABILITY_MAP", "### CAPABILITY_MAP_X",
                                 1), encoding="utf-8")

    result = skill_copy.run("lint-skill")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["checks"][0]["name"] == "tables_wellformed"
    assert result.data["checks"][0]["passed"] is False
    assert len(result.data["checks"]) == 1, "wellformedness short-circuits"


def test_n8_an_empty_capability_table_never_yields_an_empty_default(skill_copy):
    path = skill_copy.skill_root / "SKILL.md"
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"(### CAPABILITY_MAP\n(?:.*\n)*?"
                  r"\| phase \| capabilities \|\n\|---\|---\|\n)(\|[^\n]*\n)+",
                  r"\1", text)
    path.write_text(text, encoding="utf-8")

    result = skill_copy.run("lint-skill")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.data["checks"][0]["passed"] is False
    assert "zero rows" in result.data["checks"][0]["message"]


# ==========================================================================
# N6 / N28 — the capability files carry judgement, never authority
# ==========================================================================


def policy_identifiers() -> set[str]:
    builtin = sdle.GOVERNANCE_POLICY_BUILTIN
    needles = set(builtin["risk_signals"])
    needles |= {c for c in builtin["quality_checks"] if "_" in c}
    for rule in builtin["hard_floors"]:
        if "signal" in rule:
            needles.add(rule["signal"])
    return needles


def discovery_identifiers() -> set[str]:
    return ({c for c in sdle.DISCOVERY_CATEGORIES if "_" in c}
            | set(sdle.DISCOVERY_CLASSIFICATIONS)
            | {sdle.DISCOVERY_INPUT_SECTIONS[0]})


def new_prompt_files() -> list[Path]:
    """Every prompt file T10 authored: two capability files, four agents.

    Both populations get the same content search, because both are prompt
    files this phase wrote and either is a place a rule the engine owns could
    be restated. `_skill_files` covers exactly these six plus the pre-existing
    modules and SKILL.md, which is what makes the widening (M1) do real work.
    """
    files = [MODULES / name for name in NEW_CAPABILITY_FILES]
    files += [AGENTS / name for name in PRODUCT_AGENTS]
    for path in files:
        assert path.is_file(), path
    return files


@pytest.mark.parametrize("relative", [str(p) for p in new_prompt_files()])
def test_n6_no_engine_owned_value_is_restated_in_a_new_prompt_file(relative):
    """N6/F1 — the phase's defining risk, executed as a content search.

    A capability file that acquired a rule the engine could enforce — a
    risk-to-review table, a "when a design review is required" heuristic, a
    restated gate list — would be authority moving back into the prompt layer,
    which is the one thing §16 forbids. So: no policy identifier, no discovery
    identifier, no progress fraction, no gate ordinal, no phase number, and no
    risk level.
    """
    body = Path(relative).read_text(encoding="utf-8")

    assert sorted(n for n in policy_identifiers() if n in body) == []
    assert sorted(n for n in discovery_identifiers() if n in body) == []

    denominators = sorted({flow.phase_count for flow in CONSTS.flows.values()})
    fraction = re.compile(
        r"\b\d+/(?:" + "|".join(str(d) for d in denominators) + r")\b")
    assert fraction.search(body) is None, "a progress fraction was restated"

    assert re.search(r"\bGate \d", body) is None, "a gate ordinal was restated"
    assert re.search(r"\bPhase \d", body) is None, "a phase number was restated"
    for level in sdle.GOVERNANCE_LEVELS:
        assert not re.search(rf"\b{level}\b", body), f"{level} was restated"
    for cmdlet in sdle.POWERSHELL_ONLY:
        assert cmdlet not in body, cmdlet


@pytest.mark.parametrize("relative", [str(p) for p in new_prompt_files()])
def test_n28_invariant_3_holds_for_every_new_prompt_file(relative):
    """N28/A24. SpecKit is wrapped, never named."""
    body = Path(relative).read_text(encoding="utf-8").lower()
    assert "speckit" not in body
    assert "/speckit." not in body


def test_n6_the_needle_sets_are_not_vacuous():
    assert len(policy_identifiers()) >= 15
    assert len(discovery_identifiers()) >= 12
    assert len(new_prompt_files()) == 6


# ==========================================================================
# `sdle resume` — §16's exit criterion, driven
# ==========================================================================


def place_at(project: Project, phase: str) -> None:
    """Put the WorkItem's state at ``phase`` on disk.

    `resume` is read-only, so a planted state is a legitimate input and a far
    more honest driver than 21 partial lifecycle runs: it isolates what is
    under test — reconstruction from disk — from the traversal that produced
    the disk.
    """
    state = project.state()
    flow = CONSTS.flow(state.get("flow") or sdle.DEFAULT_FLOW)
    state["current_phase"] = phase
    # Written the way `advance` writes it, from the bound flow, so nothing
    # downstream compares two `None`s and calls that agreement.
    state["progress"] = flow.progress_for(phase)
    project.write_state(state)


# A6 asks for every phase in the registry and at least two flows. Three are
# used, because two are not enough to reach every phase: `discovery` is
# declared by BROWNFIELD_DISCOVERY alone, which is exactly the property
# `discovery_is_declared_by_exactly_one_flow` pins in `lint-skill`.
RESUME_FLOWS = ("GREENFIELD", "BROWNFIELD_DISCOVERY", "HOTFIX")
RESUME_CASES = [(flow, phase)
                for flow in RESUME_FLOWS
                for phase in CONSTS.flow(flow).phases]


def test_the_resume_matrix_covers_every_registry_phase():
    """Non-vacuity guard for the parametrisation below: between them the
    flows must reach every phase in the registry, or A6's "every phase" is a
    claim about a subset."""
    assert {phase for _, phase in RESUME_CASES} == set(REGISTRY)
    assert len({flow for flow, _ in RESUME_CASES}) >= 2


@pytest.mark.parametrize("flow,phase", RESUME_CASES)
def test_n9_a_fresh_process_reconstructs_the_workitem_from_disk(
        project, flow, phase):
    """N9/A6 — the headline, and TP-006 made mechanical.

    A brand-new OS process, given only the repository and no WorkItem
    argument, answers identity, position, what is pending and what to read
    next. Nothing it reports comes from conversation context, because it has
    never had any.
    """
    bind(project, flow)
    place_at(project, phase)

    result = project.run_cli("resume")
    assert result.exit_code == EXIT_OK, result.stderr
    data = result.data

    assert data["workitem"] == project.workitem
    assert data["flow"] == flow
    assert data["current_phase"] == phase
    assert data["status"] == project.state()["status"]
    assert data["header"].startswith("<!-- SDLE_STATE phase=" + phase)
    assert data["position"] == CONSTS.flow(flow).position(phase)
    assert data["progress"] == CONSTS.flow(flow).progress_for(phase)
    assert data["next_phase"] == CONSTS.flow(flow).next_phase(phase)
    # T11 X-GEN (D13). Was the same set without `pending_branch_ack`;
    # `pending_confirm_action` is a flag that says an acknowledgement is
    # outstanding, and the new key says which checkout it was given for, so a
    # resuming session can see the whole fact. Still an exact equality.
    assert set(data["pending"]) == {
        "drift_queue", "pending_confirm_action", "pending_branch_ack",
        "pending_phase", "phase_checkpoint", "clarification_phase"}

    capabilities = data["capabilities"]
    assert capabilities, f"{phase} resumed with nothing to load"
    assert capabilities == CONSTS.capability_map[phase]
    for value in capabilities:
        assert (project.skill_root / value).is_file(), value

    is_gate = phase in GATE_PHASES
    assert (data["gate"] is not None) is is_gate, data["gate"]


@pytest.mark.parametrize("phase", list(GATE_PHASES))
def test_n10_at_a_gate_resume_reports_what_gate_show_reports(started, phase):
    """N10/A7. The requirement model has one derivation; `resume` reads it
    through the same helper `gate show` does."""
    place_at(started, phase)
    key = CONSTS.phase_to_gate_key[phase]

    resumed = started.ok("resume").data["gate"]
    shown = started.ok("gate", "show", "--gate", key).data

    assert resumed["gate"] == key
    assert resumed["gate_number"] == shown["gate_number"]
    assert resumed["gate_total"] == shown["gate_total"]
    assert resumed["required"] == shown["required"]
    assert resumed["requirement_reasons"] == shown["requirement_reasons"]
    assert resumed["decision"] == shown["decision"]


def test_n11_resume_composes_and_never_re_derives(started):
    """N11/A8/F5. A second renderer of the header, or a second derivation of
    position, in the phase whose whole job is defending invariant 7, would be
    the worst possible irony. Byte-compared against the existing commands."""
    place_at(started, "gate_spec")

    resumed = started.ok("resume").data
    header = started.ok("header").data
    state = started.ok("state", "get").data
    flow = started.ok("flow", "show").data

    assert resumed["header"] == header["rendered"]
    assert resumed["current_phase"] == state["current_phase"] == flow[
        "current_phase"]
    assert resumed["status"] == state["status"]
    assert resumed["flow"] == flow["name"]
    assert resumed["progress"] == header["progress"] == flow["progress"]
    assert resumed["position"] == flow["position"]
    assert resumed["next_phase"] == flow["next_phase"]
    assert resumed["label"] == header["label"] == flow["label"]
    assert resumed["branch_mismatch"] == header["branch_mismatch"]


def test_n12_resume_writes_nothing_and_migrates_nothing(started_git):
    """N12/A9/F6. Read-only means read-only — no state, no audit line, no
    lock touch, and above all no silent migration."""
    state = started_git.state()
    state["workflow_version"] = "1.15"
    state.pop("flow", None)
    started_git.write_state(state)

    before = tree_map(started_git.root)
    audit_before = started_git.audit_file.read_bytes()

    result = started_git.ok("resume")

    assert tree_map(started_git.root) == before
    assert started_git.audit_file.read_bytes() == audit_before
    assert started_git.state()["workflow_version"] == "1.15"
    assert "flow" not in started_git.state()
    # A pre-v1.16 state still *reports* a flow, because every workflow that
    # predates the field traversed GREENFIELD. Reporting is not migrating.
    assert result.data["flow"] == "GREENFIELD"
    assert started_git.ok("audit", "verify").exit_code == EXIT_OK


def test_n12b_resume_refuses_exactly_where_its_siblings_do(bare_project):
    """N12b. Not a reimplementation of the resolution ladder — a proof that
    `resume` goes through the same one, by comparing it against a sibling
    read-only command in the same situations."""
    for situation in ("no workitem registered", "two registered"):
        if situation == "two registered":
            bare_project.ok("workitem", "create", "--name", "Alpha Item")
            bare_project.ok("workitem", "create", "--name", "Beta Item")
        resumed = bare_project.run("resume")
        headed = bare_project.run("header")
        assert (resumed.exit_code, resumed.reason) == \
            (headed.exit_code, headed.reason), (situation, resumed, headed)
        assert resumed.exit_code == EXIT_REFUSED, (situation, resumed)
    assert resumed.reason == "workitem_ambiguous", resumed


def test_n23_a_resume_refusal_leaves_the_ledger_byte_identical(project):
    """N23/A9. Invariant 6 at T10's own refusals."""
    project.record_governance()
    project.ok("init", session="s")
    before = project.audit_file.read_bytes()

    stray = project.as_workitem("no-such-item")
    refusal = stray.run("resume")
    sibling = stray.run("header")
    assert refusal.exit_code == EXIT_REFUSED, refusal
    # Named, and cross-checked against a read-only sibling in the same
    # situation, so the assertion is about the shared ladder rather than a
    # second copy of its vocabulary.
    assert refusal.reason == "workitem_unknown", refusal
    assert (refusal.exit_code, refusal.reason) == (
        sibling.exit_code, sibling.reason), (refusal, sibling)
    assert project.audit_file.read_bytes() == before
    assert project.ok("audit", "verify").exit_code == EXIT_OK


# ==========================================================================
# The subagent boundary — a violation must be detectable
# ==========================================================================


def agent_body(name: str) -> str:
    return (AGENTS / name).read_text(encoding="utf-8")


@pytest.mark.parametrize("name", PRODUCT_AGENTS)
def test_n15_a_product_agent_grants_only_read_tools(name):
    """N15/A13. The first of the two enforcement layers: a subagent with no
    `Bash` cannot run `sdle.sh` at all, and one with no `Agent`/`Task` cannot
    become a workflow controller of its own for want of the tool."""
    front = sdle.agent_frontmatter(agent_body(name))
    granted = sdle.agent_tools(front)

    assert granted == list(sdle.PRODUCT_AGENT_TOOLS), (name, granted)
    for forbidden in sdle.FORBIDDEN_AGENT_TOOLS:
        assert forbidden not in granted, (name, forbidden)


@pytest.mark.parametrize("name", PRODUCT_AGENTS)
def test_n13_a_product_agent_registers_the_fence(name):
    """N13/A11's declaration half. The battery that proves the fence actually
    denies lives in `test_hooks.py`, driven from this exact string."""
    front = sdle.agent_frontmatter(agent_body(name))
    assert sdle.PRODUCT_AGENT_FENCE in front, name
    matchers = " ".join(re.findall(r'matcher:\s*"([^"]*)"', front))
    for tool in sdle.FENCED_AGENT_TOOLS:
        assert tool in matchers, (name, tool)


@pytest.mark.parametrize("name", PRODUCT_AGENTS)
def test_n25_no_agent_is_placed_on_a_gate_decision_path(name):
    """N25/A17/F3. Invariant 8 has held through ten phases. The three gate
    verbs may appear in an agent prompt only inside the sentence that forbids
    them, so the sentence is removed first and the rest must be silent."""
    body = agent_body(name)
    assert sdle.PRODUCT_AGENT_NON_APPROVAL_CLAUSE in body, name

    remainder = body.replace(sdle.PRODUCT_AGENT_NON_APPROVAL_CLAUSE, "")
    for verb in ("gate approve", "gate omit", "advance"):
        assert verb not in remainder, (name, verb)


def test_n25_no_capability_row_puts_a_gate_capability_on_a_review_agent(repo):
    """The other half of N25: a gate phase loads the gate protocol, and the
    gate protocol is loaded in the parent. No row routes a gate anywhere
    else."""
    mapping = capability_map(repo)
    for phase in GATE_PHASES:
        assert "modules/gate-protocol.md" in mapping[phase], phase


def test_n19_the_repository_has_exactly_the_declared_agents():
    """N19/A15's first half — anti-vacuity at the repository level.

    `_check_product_agents` is emitted only when product agents exist, which
    is precisely how a check can stop meaning anything. This is the other side
    of that bargain, asserted against the real tree.
    """
    # Closed set, narrowed by the post-migration cleanup. Old value:
    # `PRODUCT_AGENTS + CONTROL_PLANE_AGENTS`, eight names — the four product
    # subagents plus the four `sdle-transition-*` control-plane files. New
    # value: `PRODUCT_AGENTS`, four names, which is now the whole directory.
    # The shape is unchanged: exact equality against a written-out set.
    present = sorted(p.name for p in AGENTS.iterdir() if p.is_file())
    assert present == sorted(PRODUCT_AGENTS), present


def test_n19_the_agent_checks_go_absent_rather_than_passing(skill_copy):
    """N19/A15/F4 — the second half, and the important one.

    With `.claude/agents/` removed, the three product-agent checks must be
    *absent* from the report, never present-and-passing. A missing directory
    that reads as a pass is how a guardrail quietly stops guarding.
    """
    agent_checks = {"product_agents_are_read_only",
                    "product_agents_declare_the_fence",
                    "product_agents_declare_the_non_approval_clause"}

    with_agents = {c["name"]
                   for c in skill_copy.ok("lint-skill").data["checks"]}
    assert agent_checks <= with_agents

    shutil.rmtree(skill_copy.root / ".claude" / "agents")
    result = skill_copy.run("lint-skill")

    assert result.exit_code == EXIT_OK, result.stderr
    names = {c["name"] for c in result.data["checks"]}
    assert agent_checks & names == set(), sorted(agent_checks & names)
    # Everything else still ran: absence removes three checks, not the file
    # set they belonged to.
    assert with_agents - names == agent_checks


def test_the_engine_starts_no_agent_and_registers_no_spawn(repo):
    """A16/A18's engine half, stated where a reader of this file will look for
    it. The structural proof lives in
    `test_units_artifact_review.py::test_the_engine_invokes_no_agent`; this is
    the CLI-visible consequence — there is no subcommand that runs anything."""
    result = repo.run("agent")
    assert result.exit_code == EXIT_USAGE, result
    result = repo.run("delegate")
    assert result.exit_code == EXIT_USAGE, result


def test_a20_the_linted_file_set_is_derived_and_covers_the_new_files():
    """A20/F4. `_skill_files` stopped being a list somebody has to remember to
    extend — which is the reason the capability split strengthens the three
    content checks instead of diluting them."""
    paths = sdle.resolve_paths(str(REPO_ROOT), str(SKILL_ROOT))
    covered = {p.name for p in sdle._skill_files(paths)}

    assert "SKILL.md" in covered
    assert set(modules_on_disk()) <= covered
    assert set(PRODUCT_AGENTS) <= covered
    # `_skill_files` used to exclude the `sdle-transition-*` control plane by
    # prefix. The post-migration cleanup deleted the files and the exclusion
    # with them, so the derivation now covers every agent prompt on disk.
    assert {p.name for p in AGENTS.glob("sdle-*.md")} <= covered


def test_a21_the_restatement_search_now_covers_the_product_agents():
    """A21/X3. Recorded rather than assumed: four `sdle-transition-*` files
    were excluded from this search because `sdle-transition-planner.md`
    legitimately used the transition contract's own evidence vocabulary,
    which is spelled exactly like §14's classifications. The post-migration
    cleanup deleted those files and the exclusion with them, so the search now
    covers every agent prompt on disk."""
    from test_units_governance import _searchable_files

    scanned = {p.name for p in _searchable_files()}
    assert set(PRODUCT_AGENTS) <= scanned
    assert {p.name for p in AGENTS.glob("sdle-*.md")} <= scanned


# ==========================================================================
# Nothing else moved
# ==========================================================================
#
# `git show` emits LF and the working tree is CRLF, so every comparison below
# normalises line endings before concluding a file differs. A byte comparison
# that reported the whole repository as changed on Windows would prove nothing
# and would be believed.

BASELINE = "adbdc5e"
"""T10's rollback point. Product files there are byte-identical to `6318541`,
the T09 implementation commit, because `adbdc5e` touched only
`docs/transition/`."""

FROZEN = (
    "tests/test_integration_01_happy_path.py",
    "tests/test_integration_02_to_05.py",
    "tests/test_integration_06_to_09.py",
    ".claude/settings.json",
    # `.claude/skills/sdle/templates/state.json` moved out of this tuple at
    # T11: D13 adds a state field and D14 bumps the version, so it cannot be
    # byte-identical to `adbdc5e`. It is pinned instead by
    # `test_t11_the_state_template_changed_only_as_declared` below, which is a
    # stricter comparison, not a looser one. Every other entry is untouched.
    ".gitignore",
)

# The 33 checks `lint-skill` reported at the rollback point, written out so a
# check that quietly stops being emitted fails here rather than passing as an
# absence. Observed by running the engine in a worktree at BASELINE.
BASELINE_CHECKS = (
    "tables_wellformed",
    "phase_set_matches_next_phase",
    "phase_set_matches_phase_label_map",
    "phase_set_matches_progress_map",
    "next_phase_chains_sequence",
    "progress_denominator_matches_phase_count",
    "gate_registered_gate_constitution",
    "gate_registered_gate_spec",
    "gate_registered_gate_plan",
    "gate_registered_gate_tasks",
    "gate_registered_gate_analyze",
    "gate_registered_gate_design",
    "gate_registered_gate_implement",
    "gate_registered_gate_security",
    "every_phase_has_execution_block",
    "execution_block_numbers_are_the_greenfield_positions",
    "flow_table_covers_the_required_flows",
    "every_flow_is_an_ordered_subset_of_the_registry",
    "every_flow_retains_the_mandatory_phases",
    "progress_map_and_gate_numbers_are_the_derived_greenfield_views",
    "every_registry_phase_is_used_by_some_flow",
    "gate_labels_are_flow_relative",
    "discovery_is_gateless",
    "discovery_is_declared_by_exactly_one_flow",
    "discovery_vocabulary_is_not_restated_in_prompt_files",
    "single_state_template",
    "version_string_consistent",
    "migration_covers_every_state_field",
    "no_powershell_only_cmdlets",
    "no_hardcoded_progress_outside_progress_map",
    "doc_lists_every_phase_README",
    "doc_lists_every_phase_SDLE-Reference-Guide",
    "repo_config_defaults_match_documentation",
)

T10_CHECKS = (
    "capability_map_covers_every_registry_phase",
    "every_capability_file_exists",
    "capability_map_never_names_the_orchestrator",
    "every_capability_file_is_linted",
    "every_row_is_a_strict_subset_of_the_capability_set",
    "capability_cross_references_are_mapped_files",
    "product_agents_are_read_only",
    "product_agents_declare_the_fence",
    "product_agents_declare_the_non_approval_clause",
)

# T11 X7 (TP-003 category 2, X-GEN). D16 adds exactly one check, so the closed
# set grows by exactly one literal and the assertion below keeps its
# exact-equality shape. Old value: `BASELINE_CHECKS + T10_CHECKS` (42 names).
# New value: the same union plus `T11_CHECKS` (43). The check is proven able to
# fail in `test_lint_skill.py::test_n24_*`, on a copied tree.
T11_CHECKS = (
    "documentation_set_is_present",
    # Added after T11, with the documentation index. Existing is not the same
    # as being findable: the six subject directories were present and
    # lint-green while linked from nowhere at all. Declared here rather than
    # merely appearing, which is what this closed set is for -- it caught this
    # very addition in CI.
    "documentation_index_links_every_directory",
    # Added with the flow transcripts. Being findable is not the same as being
    # right: `docs/lifecycle/README.md` counted the terminal `complete` and so
    # published 19/20/17/15/11 while the tutorials, START-HERE, the root
    # README and the Reference Guide published 18/19/16/14/10. Five documents
    # against one, all of them present, all of them linked, and the odd one
    # out was the document named "the lifecycle". Prose cannot be trusted to
    # hold a number that the engine also holds.
    "doc_flow_counts_match_engine",
)


def at_baseline(relative: str) -> str | None:
    """The file's content at T10's rollback point, or None."""
    result = subprocess.run(
        ["git", "show", f"{BASELINE}:{relative}"],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return None
    return result.stdout.replace("\r\n", "\n")


def here(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(
        encoding="utf-8").replace("\r\n", "\n")


def test_the_baseline_is_reachable():
    """Non-vacuity guard: if `git show` failed for every path, the comparisons
    below would pass by comparing None to None."""
    assert at_baseline("scripts/sdle.py") is not None
    assert at_baseline("tests/test_integration_01_happy_path.py") is not None
    assert at_baseline("docs/dry-runs/01-happy-path.md") is not None


@pytest.mark.parametrize("relative", FROZEN)
def test_n20_n24_the_frozen_files_are_byte_identical(relative):
    """N20/N24/A22/A23. The three integration files carry the behavioural
    contract; `settings.json` is where the fence deliberately is *not*; the
    state template and `.gitignore` are what a state field would have had to
    move."""
    original = at_baseline(relative)
    assert original is not None, relative
    if relative.endswith(".py"):
        # SDLE-DEFECT-STABILIZATION-01: two of these files asserted defects
        # the iteration fixes. Unit-by-unit byte identity, except the edits
        # declared once in `conftest.py` -- see its comment block.
        assert_frozen_module(relative, original, here(relative))
    else:
        assert here(relative) == original, relative


def test_the_stabilization_declarations_name_only_frozen_files():
    """A declaration against a file no pin compares would be a no-op, which
    is the one failure a declared-delta list must not have."""
    declared = (set(STABILIZATION_01_TEST_EDITS)
                | set(STABILIZATION_01_TEST_ADDITIONS)
                | set(STABILIZATION_01_TEST_REMOVALS))
    assert declared <= set(FROZEN), sorted(declared - set(FROZEN))


def test_n20_the_nine_dry_run_transcripts_match_the_declared_substitution():
    """N20/A22/X10: the transcripts are the behavioural specification.

    T11 D15 converged them off the repository-global `.workflow/` runtime,
    stale since the runtime became WorkItem-scoped. The pin was **not**
    re-baselined — re-baselining would have thrown away everything it was
    buying. It became a declared-substitution comparison instead:

        apply_dry_run_substitutions(at_baseline(f)) == here(f)

    `DRY_RUN_SUBSTITUTIONS` is an enumerated list of exact literals in
    `conftest.py`, never a pattern, so any change to a transcript other than
    those substitutions still fails here. Two anti-vacuity guards ride along:
    every declared pair must be used at least once (so a pair cannot decay
    into a no-op), and the directory's whole file list is still compared, so
    the README cannot drift unnoticed either.
    """
    directory = REPO_ROOT / "docs" / "dry-runs"
    every = sorted(directory.glob("*.md"))
    numbered = [p for p in every if p.name[:2].isdigit()]

    # The nine GREENFIELD transcripts this pin was built for. Transcripts
    # 10-13 were authored later, for the four non-GREENFIELD flows, and have
    # no baseline to compare against -- `at_baseline` returns None for them.
    # They are therefore excluded here and pinned by
    # `tests/test_integration_10_to_13.py` instead, which asserts their
    # claims rather than their bytes. The nine keep the stronger guarantee.
    pinned = [p for p in numbered if int(p.name[:2]) <= 9]
    assert len(pinned) == 9, [p.name for p in every]
    assert len(numbered) == 13, [p.name for p in every]

    used: set[str] = set()
    for path in pinned:
        relative = path.relative_to(REPO_ROOT).as_posix()
        original = at_baseline(relative)
        assert original is not None, relative
        assert here(relative) == apply_dry_run_substitutions(
            original, used), relative

    assert used == {old for old, _ in DRY_RUN_SUBSTITUTIONS}, sorted(
        {old for old, _ in DRY_RUN_SUBSTITUTIONS} - used)


def test_the_dry_run_index_lists_every_transcript_beside_it():
    """What replaces the byte-pin on `docs/dry-runs/README.md`.

    The README used to ride along on the substitution comparison above, which
    is how "the README cannot drift unnoticed either" was bought. That pin was
    released deliberately when the index was rewritten to carry transcripts
    10-13, and releasing it without putting anything back would have been a
    quiet loss -- so this is the replacement, and it is a better fit for an
    index than a byte comparison ever was: a byte-pin says the file did not
    change, which is not the property an index needs. The property an index
    needs is that it lists what is actually there.

    A transcript added to the directory and forgotten now fails here, which is
    exactly the failure the old pin would have caught.
    """
    directory = REPO_ROOT / "docs" / "dry-runs"
    index = (directory / "README.md").read_text(encoding="utf-8")

    missing = [path.name for path in sorted(directory.glob("*.md"))
               if path.name != "README.md" and path.name not in index]
    assert not missing, f"docs/dry-runs/README.md does not link: {missing}"


def test_n21_greenfield_is_frozen_and_every_flow_is_element_wise_identical(
        tmp_path):
    """N21/A23. GREENFIELD is the frozen v1 spine, and T10 selects *capability
    files*, never phases. The flow table is re-parsed out of SKILL.md at the
    rollback point with the engine's own parser, so this compares what the
    engine would have loaded rather than what a hand-copied literal claims."""
    assert len(sdle.GREENFIELD_V1_PHASES) == 19, sdle.GREENFIELD_V1_PHASES

    relative = ".claude/skills/sdle/SKILL.md"
    original = tmp_path / "baseline-SKILL.md"
    original.write_text(at_baseline(relative), encoding="utf-8")

    before = sdle.parse_md_table(original, "FLOW_PHASES")
    after = sdle.parse_md_table(REPO_ROOT / relative, "FLOW_PHASES")
    assert after == before, "a flow's phase list moved"

    # GREENFIELD is not a FLOW_PHASES row: it is the built-in default the
    # engine holds as a frozen literal, which is exactly why it is compared
    # against the literal at the rollback point rather than against the table.
    assert "GREENFIELD" not in CONSTS.flow_phases, (
        "GREENFIELD must stay the engine's frozen default, not a table row")
    assert sdle.GREENFIELD_V1_PHASES == _literal_tuple(
        at_baseline("scripts/sdle.py"), "GREENFIELD_V1_PHASES")


def _literal_tuple(source: str, name: str) -> tuple[str, ...]:
    """The value of a module-level tuple-of-strings assignment, by AST."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.AnnAssign):
            targets = [node.target]
        else:
            targets = list(getattr(node, "targets", []))
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            return tuple(element.value for element in node.value.elts)
    raise AssertionError(f"{name} is not a module-level tuple")


def test_n22_migrate_workflow_still_leaves_the_legacy_tree_untouched(
    bare_project,
):
    """N22/A24, split by T11 X3.

    T11 removed the dual-read rung it named as its owner, so the "the legacy
    rung still binds" half is inverted here. `migrate-workflow`'s read-only
    treatment of `.workflow/` is B9 and is kept verbatim.
    """
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
    refused = bare_project.run("state", "get", "--field", "current_phase")
    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "workitem_required", refused

    bare_project.ok("workitem", "create", "--name", "migrated thing")
    wid = bare_project.run("workitem", "list").data["workitems"][-1]["id"]
    assert bare_project.run("migrate-workflow", "--workitem",
                            wid).exit_code == EXIT_OK
    after = {p.name: sdle.sha256_file(p) for p in sorted(legacy.iterdir())}
    assert after == before, "migrate-workflow must never mutate .workflow/"


def test_n24_the_schema_did_not_move(repo, bare_project):
    """N24/A18/A23/F9. The acceptance criterion of the whole phase, stated as
    numbers: no state field, no migration row, no version bump, no gate.

    **T11 X11 re-valuation (TP-003 category 2).** T09's phase added none of
    those; T11 D13/D14 deliberately add a state field, a migration row and a
    version bump, so three literals move here: `"1.16"` -> `"1.17"`,
    `"v1.16"` -> `"v1.17"` and the chain length `16` -> `17`. The counts that
    carry T09's claim do not move: eight approval keys equal to
    `PHASE_TO_GATE_KEY`'s values, 21 registry phases, 8 gate phases — T11 adds
    no gate and no phase. The exact-equality shape is kept throughout; the
    `templates/state.json` movement itself is pinned change-for-change by
    `test_t11_the_state_template_changed_only_as_declared`."""
    template = json.loads(
        (bare_project.skill_root / "templates" / "state.json").read_text(
            encoding="utf-8"))
    assert template["workflow_version"] == "1.17"
    assert len(template["approvals"]) == 8
    assert set(template["approvals"]) == set(CONSTS.phase_to_gate_key.values())

    assert len(CONSTS.version_chain) == 17
    assert len(CONSTS.phase_sequence) == 21
    assert len(CONSTS.gate_phases) == 8

    report = repo.ok("lint-skill").data
    version = next(c for c in report["checks"]
                   if c["name"] == "version_string_consistent")
    assert "v1.17" in version["message"], version


def test_n24_a18_the_engine_gained_no_writer_and_no_state_field():
    """A18, driven against the diff rather than asserted. `resume` is the only
    new command; every other new symbol is a lint check or a pure derivation.

    The needles are the engine's write primitives. If a later edit adds a
    second writer, or teaches `resume` to migrate "for convenience", it lands
    on one of these lines and fails here — which is the whole acceptance
    criterion of T10 expressed as a test rather than as a promise."""
    before = at_baseline("scripts/sdle.py")
    assert before is not None
    after = here("scripts/sdle.py")

    # Occurrence counts, not a line diff: a line diff would miss a write call
    # spelled like an existing one, and would be fooled by a pure move. Every
    # one of these must be exactly the number it was, PLUS the delta the
    # phase after T10 declares below — which is stronger than re-baselining,
    # because the permitted movement is named and quantified and everything
    # else must still be identical.
    for needle in WRITE_PRIMITIVES:
        expected = (before.count(needle) + T11_WRITE_DELTA.get(needle, 0)
                    + STABILIZATION_01_WRITE_DELTA.get(needle, 0))
        assert after.count(needle) == expected, (
            needle, before.count(needle), after.count(needle), expected)

    # The exclusive-create writer D04 declares above: exactly one, and it
    # lives where the declaration says it does.
    exclusive = [node for node in ast.walk(ast.parse(after))
                 if isinstance(node, ast.FunctionDef)
                 and any(isinstance(call, ast.Call)
                         and isinstance(call.func, ast.Name)
                         and call.func.id == "open"
                         and any(isinstance(arg, ast.Constant)
                                 and arg.value == "x" for arg in call.args)
                         for call in ast.walk(node))]
    assert [fn.name for fn in exclusive] == ["reserve_evidence"], [
        fn.name for fn in exclusive]

    was = set(ADD_PARSER.findall(before))
    now = set(ADD_PARSER.findall(after))
    assert sorted(now - was) == ["resume"], sorted(now - was)
    assert was - now == set(), sorted(was - now)


WRITE_PRIMITIVES = ("write_atomic", "save_state", "append_audit",
                    "record_audit", ".write_text(", ".write_bytes(",
                    "os.replace", ".mkdir(")

# T11 adds exactly THREE new call sites, all declared here as a signed delta
# rather than a re-baseline, so that any OTHER movement — in these primitives
# or any other — still fails.
#
#   `append_audit` 47 -> 49: D11's `governance_downgraded` entry in
#       `_record_governance_downgrade_audit`, and D13's `branch_ack_stale`
#       entry in `branch_guard` - the record T03-1 said was missing when an
#       acknowledgement given for one checkout is rejected on another.
#   `save_state`   46 -> 47: D13's `branch_guard`, which now has two exits
#       that must persist the guard's own bookkeeping — the acceptance arm
#       (clearing both fields) and the stale-acknowledgement arm (re-arming
#       against the current checkout). Before D13 there was one.
#
# Both are new *call sites*, not new *writers*: `append_audit` is still the
# only thing that writes the ledger, `save_state` the only thing that writes
# `state.json`, and `write_atomic` the only thing that writes a file —
# unchanged at 30. Invariant 6 is about who may write, and it is untouched.
T11_WRITE_DELTA = {"append_audit": 2, "save_state": 1}

# SDLE-DEFECT-STABILIZATION-01 declares its own call sites the same way: a
# signed delta per needle, each one named, so every other movement still
# fails. Recorded in `docs/verification/defect-stabilization-01.md`.
#
#   `.mkdir(` +1 (D04): `reserve_evidence` creates the evidence directory
#       before it claims a file name in it.
#   `write_atomic` +1 (D02): `cmd_manifest_build` fills the implementation
#       evidence record Gate 7 reads — 30 -> 31. Still a call to the one
#       atomic writer, not a new way to write a file.
#
# D04 also adds the engine's one *exclusive-create* writer — `open(path,
# "x")` in `reserve_evidence`, which claims an evidence file name so no
# evidence is ever replaced. It is not a needle above (a bare `open(` would
# match every reader), so it is pinned by name in the test below instead.
STABILIZATION_01_WRITE_DELTA = {".mkdir(": 1, "write_atomic": 1}

ADD_PARSER = re.compile(r'add_parser[(]' + r"\s*" + r'"([a-z][a-z-]*)"')


def test_the_write_primitive_needles_are_not_vacuous():
    """If the needle list stopped matching the engine at all, the count
    comparison above would compare zero to zero and prove nothing."""
    source = here("scripts/sdle.py")
    hits = {needle: source.count(needle) for needle in WRITE_PRIMITIVES}
    assert sum(hits.values()) >= 100, hits
    assert hits["write_atomic"] > 0 and hits["append_audit"] > 0, hits
    assert len(ADD_PARSER.findall(source)) > 50, "the parser scan found little"



def test_n26_every_baseline_check_is_still_present_and_passing(repo):
    """N26/A19/F4. `lint-skill` got wider, not weaker. Exact equality against
    the written-out union, so a check that silently stopped being emitted fails
    here instead of disappearing quietly."""
    report = repo.ok("lint-skill").data
    names = [c["name"] for c in report["checks"]]

    expected = BASELINE_CHECKS + T10_CHECKS + T11_CHECKS
    assert sorted(names) == sorted(expected), (
        sorted(set(names) ^ set(expected)))
    assert len(names) == len(set(names)), "a check name is emitted twice"
    assert report["failed"] == [], report["failed"]
    assert all(c["passed"] for c in report["checks"]), [
        c["name"] for c in report["checks"] if not c["passed"]]


def _top_level(source: str) -> dict[str, str]:
    """Every top-level function in a module, by name, with its exact source."""
    tree = ast.parse(source)
    return {node.name: ast.get_source_segment(source, node)
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}


# T11 edits two pre-existing hook definitions. Declared here by name, and
# pinned below by a property that is *not* weaker than the byte comparison it
# replaces: every line the baseline definition had must still be present. An
# edit that removed or altered any existing line fails, and only a pure
# insertion passes.
#
#   `write_fence`  D7. Normalises `..` before matching, closing the fence
#                  bypass T04 recorded as N-3.
#   `in_dir`       **Not a D-item.** A user-approved correction made outside
#                  the plan, during M7. `SDLE_OWNED_PREFIXES` is entirely
#                  repository-root-relative, but `in_dir` matched `/{name}/`
#                  *anywhere* in a path, so the hook was strictly broader than
#                  the ownership it exists to protect and denied
#                  `docs/workitems/` — a path the engine does not own and has
#                  no choke-point refusal for. A tripwire that fires where the
#                  engine would not refuse is the one failure mode a tripwire
#                  must not have. The fix is the new `fenced_target`; `in_dir`
#                  itself keeps its loose form verbatim for paths outside the
#                  repository and gained only a docstring, which is why it
#                  passes the pure-insertion pin below.
T11_HOOK_EDITS = ("write_fence", "in_dir")

# The one line T11 *replaces* rather than inserts, written out on both sides.
# `write_fence` now tests each fenced name with the anchored `fenced_target`
# instead of the loose `in_dir`. Declaring it here keeps the pin above exact:
# any other lost line still fails, and dropping this line *without* the
# replacement arriving also fails. `test_n28` asserts the resulting behaviour
# of `write_fence`; `tests/test_hooks.py` asserts it end to end through the
# registered command.
T11_HOOK_LINE_SUBSTITUTIONS = {
    "write_fence": {
        "        if in_dir(path, name):": "        if fenced_target(path, name):",
    },
}


def test_n27_the_four_existing_hook_guards_and_their_tests_are_unmodified():
    """N27/A24. The hooks are tripwires and T10 added one; it did not touch the
    four that were there, or the cases that prove they work.

    Asserted definition-by-definition rather than by whole-file bytes, because
    the file legitimately gained `product_agent_fence` and its battery. Nothing
    is relaxed: every pre-existing definition must be byte-identical, and the
    guard registry is separately pinned by
    `test_units_gate_policy.py::test_n28_the_hooks_are_byte_identical`.

    **T11 declares two exceptions, `write_fence` and `in_dir`.** The plan's X9
    row named only `test_n28` as the hooks byte-pin; this is a second one, and
    both exceptions are recorded as plan deviations rather than quietly
    re-baselined. Each is narrow and *proved*, not asserted: the whole of the
    baseline definition must still be present line for line, so the only change
    that can pass is an insertion — with exactly one declared substitution,
    written out below as a before/after pair. `test_n28` pins what
    `write_fence` must still *do*; this pins that nothing it did was taken
    away by accident.
    """
    for relative in (".claude/hooks/hooks.py", "tests/test_hooks.py"):
        before = _top_level(at_baseline(relative))
        after = _top_level(here(relative))
        assert set(before) <= set(after), sorted(set(before) - set(after))
        for name, source in before.items():
            if relative == ".claude/hooks/hooks.py" and name in T11_HOOK_EDITS:
                was = [line for line in source.splitlines() if line.strip()]
                now = [line for line in after[name].splitlines() if line.strip()]
                missing = [line for line in was if line not in now]
                substituted = T11_HOOK_LINE_SUBSTITUTIONS.get(name, {})
                assert sorted(missing) == sorted(substituted), (
                    f"{relative}::{name} lost undeclared lines: "
                    f"{sorted(set(missing) - set(substituted))}")
                for gone, arrived in substituted.items():
                    assert arrived in now, (
                        f"{relative}::{name} dropped {gone.strip()!r} without "
                        f"the declared replacement {arrived.strip()!r}")
                assert len(now) > len(was) - len(substituted), (
                    f"{relative}::{name} is declared edited but did not change")
                continue
            assert after[name] == source, f"{relative}::{name}"

    # And the four guards are still the four guards, by name.
    hooks = here(".claude/hooks/hooks.py")
    for guard in ("write_fence", "untrusted_read", "dirty_tree",
                  "secrets_scan"):
        assert f"def {guard}(payload)" in hooks, guard


# ==========================================================================
# A25 — the enforcement split is stated, and stated honestly
# ==========================================================================

ADR7 = REPO_ROOT / "docs" / "architecture" / (
    "ADR-007-progressive-capabilities-and-product-subagents.md")

# D12, reproduced here as the test's own copy of what the ADR must say. These
# are not SDLE constants and no engine value is restated: they are the claim
# the documentation makes about who enforces what, and this is the assertion
# that it has not been quietly upgraded.
SDLE_ENFORCED = (
    "A product subagent's declaration grants no mutating tool",
    "A product subagent's declaration carries the deny fence",
    "A denied call is actually denied when the fence runs",
    "The engine spawns no agent",
    "A capability set is chosen by the engine, not the model",
)
RUNTIME_ENFORCED = (
    "A declared `tools:` list is actually applied",
    "A frontmatter `PreToolUse` hook actually fires",
)
CONVENTION_ONLY = (
    "The parent delegates to the *right* agent, or at all",
    "An `--actor-name` truthfully names who produced a finding",
    "A human, not the orchestrator, typed `approve`",
)


def _adr_row(body: str, property_text: str) -> str:
    rows = [line for line in body.splitlines()
            if line.startswith("| ") and property_text in line]
    assert len(rows) == 1, (property_text, rows)
    return rows[0]


def test_a25_the_enforcement_split_is_stated_without_being_softened():
    """A25/F15. Named specialist agents *look* like enforcement. Two of the
    three unenforced rows predate T10 and one is new; none of them moved up the
    table, and this test is what stops a later edit moving them by prose.

    Every row is located by its property text and its *middle* column is read,
    so rewording the property is fine and re-labelling who enforces it is not.
    """
    assert ADR7.is_file(), "ADR-007 is missing"
    body = ADR7.read_text(encoding="utf-8")

    for text in SDLE_ENFORCED:
        row = _adr_row(body, text)
        assert "**SDLE**" in row, row
    for text in RUNTIME_ENFORCED:
        row = _adr_row(body, text)
        assert "**Claude Code runtime**" in row and "*not* SDLE" in row, row
        assert "**SDLE**" not in row, row
    for text in CONVENTION_ONLY:
        row = _adr_row(body, text)
        assert "**Convention only**" in row, row
        assert "SDLE" not in row and "Claude Code" not in row, row

    # The rejected attestation must stay rejected and stay explained: a
    # caller-set flag refuses the compliant caller and lets the other through.
    assert "SDLE_ACTOR" in body and "rejected" in body.lower()


def test_a25_claude_md_names_the_runtime_owner_and_the_conventions():
    """A25's second half: CLAUDE.md must say which of the two runtime
    enforcement points belongs to Claude Code rather than to SDLE, where a
    reader of the architecture will actually meet it."""
    body = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Claude Code runtime" in body
    assert "convention only" in body.lower()
    assert "`tools:` list is applied" in body
    assert "frontmatter hook fires" in body
    assert "ADR-007" in body


OVERSTATEMENTS = (
    "the engine verifies",
    "the engine attests",
    "the engine knows who",
    "proves who",
    "guarantees who",
    "verified agent",
    "attested",
)

ACTOR_HONESTY_REQUIRED = (
    ".claude/skills/sdle/SKILL.md",
    ".claude/skills/sdle/modules/phase-execution.md",
)


@pytest.mark.parametrize("relative", [
    ".claude/skills/sdle/SKILL.md",
    ".claude/skills/sdle/modules/phase-execution.md",
    ".claude/skills/sdle/modules/gate-protocol.md",
    ".claude/skills/sdle/modules/design-review.md",
    ".claude/skills/sdle/modules/code-review.md",
    ".claude/skills/sdle/modules/security-review.md",
    ".claude/agents/sdle-design-review.md",
    ".claude/agents/sdle-code-review.md",
    ".claude/agents/sdle-security-review.md",
    ".claude/agents/sdle-discovery.md",
    ".claude/commands/sdle-continue.md",
    ".claude/commands/sdle-start.md",
    "README.md",
    "CLAUDE.md",
])
def test_a25_no_prompt_file_overstates_what_is_enforced(relative):
    """F15 at the prompt layer, which is where a reader is most likely to be
    misled. Named specialist agents make the two runtime rows and the three
    convention rows *look* enforced; no shipped file may say so."""
    body = (REPO_ROOT / relative).read_text(encoding="utf-8").lower()
    for overstatement in OVERSTATEMENTS:
        assert overstatement not in body, (relative, overstatement)


@pytest.mark.parametrize("relative", ACTOR_HONESTY_REQUIRED)
def test_a25_the_files_that_describe_recording_carry_the_caveat(relative):
    """The positive half. The two files that tell the orchestrator to record a
    subagent's finding must also say what `--actor-name` is: a string the
    caller supplies, which the engine records faithfully and cannot verify."""
    body = (REPO_ROOT / relative).read_text(encoding="utf-8")
    assert "--actor-name" in body, relative
    assert ("cannot verify" in body or "recorded string" in body), relative


def test_a25_the_needles_are_not_vacuous():
    """Guard against the three lists above silently emptying, which would make
    every assertion in `test_a25_...` a loop over nothing."""
    assert len(SDLE_ENFORCED) == 5
    assert len(RUNTIME_ENFORCED) == 2
    assert len(CONVENTION_ONLY) == 3
    body = ADR7.read_text(encoding="utf-8")
    rows = [line for line in body.splitlines()
            if line.startswith("| ") and "Enforced by" not in line
            and not set(line) <= set("|- ")]
    assert len(rows) >= 10, len(rows)
# T11 X6 — the one FROZEN file this phase edits.
#
# D13 adds the `pending_branch_ack` state field and D14 bumps the version, so
# `templates/state.json` cannot stay byte-identical. It is pulled out of the
# parametrised comparison above and pinned here instead against T11's own
# baseline, by a DECLARED SUBSTITUTION: take the baseline text, apply exactly
# the two changes T11 declares, and the result must equal the file byte for
# byte. That is strictly more auditable than a re-baseline — a third change,
# anywhere in the file, still fails — and it keeps the pin non-vacuous.
T11_TEMPLATE_BASELINE = "4b1aa71"
STATE_TEMPLATE = ".claude/skills/sdle/templates/state.json"
T11_TEMPLATE_SUBSTITUTIONS = (
    ('"workflow_version": "1.16",', '"workflow_version": "1.17",'),
    ('  "pending_confirm_action": null,\n',
     '  "pending_confirm_action": null,\n  "pending_branch_ack": null,\n'),
)


def at_t11_template_baseline() -> str | None:
    result = subprocess.run(
        ["git", "show", f"{T11_TEMPLATE_BASELINE}:{STATE_TEMPLATE}"],
        cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        return None
    return result.stdout.replace("\r\n", "\n")


def test_t11_the_state_template_changed_only_as_declared():
    """X6. Two changes, both named, both required, nothing else."""
    original = at_t11_template_baseline()
    assert original is not None, (
        f"{T11_TEMPLATE_BASELINE} must be reachable, or this test is vacuous")

    expected = original
    for old, new in T11_TEMPLATE_SUBSTITUTIONS:
        assert expected.count(old) == 1, old
        expected = expected.replace(old, new)
    assert expected != original, "the substitution set matched nothing"

    assert here(STATE_TEMPLATE) == expected

    # And the same two facts stated structurally, so a future reader does not
    # have to reverse-engineer them out of the substitution literals.
    before = json.loads(original)
    after = json.loads(here(STATE_TEMPLATE))
    assert set(after) - set(before) == {"pending_branch_ack"}
    assert set(before) - set(after) == set()
    assert after["pending_branch_ack"] is None
    assert (before["workflow_version"], after["workflow_version"]) == (
        "1.16", "1.17")
    for key in before:
        if key != "workflow_version":
            assert after[key] == before[key], key

