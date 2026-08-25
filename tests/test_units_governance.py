"""Contract §12 — requirements quality, classification and hybrid risk.

Three rules govern this file, following `test_units_repo_config.py`:

1. **No shared fixture is modified.** `conftest`'s fixtures are used as they
   are; every helper this file needs is defined here.
2. **A green suite is necessary, not sufficient.** T06 both *adds* governance
   and *proves an absence*: risk level, classification and the would-be gate
   set must move nothing about the traversal. Both directions are asserted.
3. **Claude cannot lower a deterministic floor.** That asymmetry is the
   security property of this phase, so it is pinned by a cross-product
   property test rather than by a handful of examples.
"""

from __future__ import annotations

import ast
import copy
import inspect
import json
import re
import shutil
from pathlib import Path

import pytest

from conftest import SDLE_PY, Project, sdle
from test_integration_01_happy_path import EXPECTED_TRAVERSAL, run_happy_path
from test_units_artifact_review import review_for_gate

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_INTEGRITY = 3

REPO_ROOT = Path(SDLE_PY).resolve().parent.parent

# §12's twelve structured checks, restated here *as the test's own literal* so
# a rename or a dropped check in `sdle.py` fails loudly (N7).
SECTION_12_CHECKS = {
    "problem_statement",
    "scope",
    "out_of_scope",
    "acceptance_criteria",
    "ambiguity",
    "contradictions",
    "constraints",
    "nfrs",
    "security_data_implications",
    "compatibility",
    "dependencies",
    "blocking_unknowns",
}


# --------------------------------------------------------------------------
# Helpers — local to this file by design
# --------------------------------------------------------------------------


def paths_for(project: Project, workitem: str | None = None) -> "sdle.Paths":
    paths = sdle.resolve_paths(str(project.root), str(project.skill_root))
    if workitem is None:
        return paths
    return sdle.dataclass_replace(paths, workitem=workitem)


def sdle_ast() -> ast.Module:
    return ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))


def paths_class(tree: ast.Module) -> ast.ClassDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "Paths":
            return node
    raise AssertionError("class Paths not found in sdle.py")


def function_named(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name} not found in sdle.py")


def names_referenced(node: ast.AST) -> set[str]:
    seen: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            seen.add(child.attr)
        elif isinstance(child, ast.Name):
            seen.add(child.id)
    return seen


def sha_map(root: Path, skip: tuple[str, ...] = (".git",)) -> dict[str, str]:
    """Recursive content map of a scratch tree. Local by design."""
    out: dict[str, str] = {}
    if not root.is_dir():
        return out
    for path in sorted(root.rglob("*")):
        relative = path.relative_to(root)
        if any(part in skip for part in relative.parts):
            continue
        if path.is_file():
            out[relative.as_posix()] = sdle.sha256_file(path)
    return out


def create_wi(project: Project, name: str) -> str:
    project.ok("workitem", "create", "--name", name)
    return project.run("workitem", "list").data["workitems"][-1]["id"]


def policy_file(project: Project) -> Path:
    return project.root / ".sdle" / "policies" / "governance-policy.json"


def write_policy(project: Project, document) -> Path:
    target = policy_file(project)
    target.parent.mkdir(parents=True, exist_ok=True)
    body = document if isinstance(document, str) else json.dumps(document, indent=2)
    target.write_text(body, encoding="utf-8", newline="\n")
    return target


BUILTIN = sdle.GOVERNANCE_POLICY_BUILTIN

INPUT_NAME = "governance-input.json"


def governance_input(**over) -> dict:
    """A valid structured proposal. Every case below starts from this and
    breaks exactly one thing, so a refusal is attributable."""
    document = {
        "governanceInputVersion": "1",
        "quality": {name: {"result": "PASS", "finding": None}
                    for name in BUILTIN["quality_checks"]},
        "classification": {"type": "enhancement", "flow": "ITERATIVE"},
        "risk": {"signals": [], "proposedLevel": "LOW", "uncertainty": "LOW"},
    }
    document.update(over)
    return document


def write_input(project: Project, document, name: str = INPUT_NAME) -> str:
    target = project.root / name
    body = document if isinstance(document, str) else json.dumps(document, indent=2)
    target.write_text(body, encoding="utf-8", newline="\n")
    return name


def assess(project: Project, document=None, name: str = INPUT_NAME):
    write_input(project, governance_input() if document is None else document, name)
    return project.run("governance", "assess", "--input", name)


def record_of(project: Project) -> dict:
    return json.loads(
        (project.runtime / "governance.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# N1/N2 — the Paths seam
# --------------------------------------------------------------------------


def test_the_three_new_members_are_derived_correctly(bare_project):
    """N1: the two records move with the WorkItem; the policy never does."""
    unbound = paths_for(bare_project)
    bound_a = paths_for(bare_project, "a")
    bound_b = paths_for(bare_project, "b")
    root = bare_project.root.resolve()

    for member in ("governance_file", "reviews_file"):
        assert getattr(bound_a, member) != getattr(bound_b, member)
        assert getattr(bound_a, member).parent == bound_a.runtime
        assert getattr(bound_b, member).parent == bound_b.runtime

    values = {p.governance_policy_file for p in (unbound, bound_a, bound_b)}
    assert len(values) == 1
    assert (unbound.governance_policy_file
            == root / ".sdle" / "policies" / "governance-policy.json")


def test_no_new_member_crosses_the_ownership_boundary():
    """N1, at source level. The derivation *is* the boundary (§11)."""
    body = paths_class(sdle_ast()).body
    found = {}
    for node in body:
        if isinstance(node, ast.FunctionDef) and node.name in (
                "governance_file", "reviews_file", "governance_policy_file"):
            found[node.name] = names_referenced(node)
    assert set(found) == {"governance_file", "reviews_file",
                          "governance_policy_file"}

    leaked = found["governance_policy_file"] & {
        "workitem", "workitem_root", "runtime", "legacy_workflow", "workitems"}
    assert not leaked, f"governance_policy_file references {sorted(leaked)}"
    for member in ("governance_file", "reviews_file"):
        assert "config_root" not in found[member]
        assert "policies_dir" not in found[member]


def test_the_record_and_the_policy_never_share_a_basename(bare_project):
    """N2: a shared basename would make the two `.sdle/` leak detectors
    contradict each other."""
    bound = paths_for(bare_project, "a")
    assert bound.governance_file.name != bound.governance_policy_file.name
    assert bound.reviews_file.name != bound.governance_policy_file.name

    runtime_names = set(sdle.workitem_runtime_member_names(bound))
    assert {"governance.json", "reviews.json"} <= runtime_names
    assert bound.governance_policy_file.name not in runtime_names


# --------------------------------------------------------------------------
# N3/N4/N5 — the policy reader is fail-closed and monotone
# --------------------------------------------------------------------------


def test_an_absent_policy_yields_the_builtin_and_creates_nothing(bare_project):
    """N3: the built-in is the weakest admissible policy, so "absent -> the
    built-in" is safe rather than fail-open."""
    assert not (bare_project.root / ".sdle").exists()
    before = sha_map(bare_project.root)

    result = bare_project.run("governance", "policy")

    assert result.exit_code == EXIT_OK, result
    assert result.data["source"] == "builtin"
    assert result.data["sha256"] is None
    assert result.data["policy"] == BUILTIN
    assert sha_map(bare_project.root) == before
    assert not (bare_project.root / ".sdle").exists()


MALFORMED_CASES = {
    "not_json": "{ this is not json",
    "json_array": "[]\n",
    "json_scalar": "7\n",
    "json_string": '"policy"\n',
    "unknown_key": json.dumps({"blocking_chekcs": []}),
    "quality_checks_not_overridable": json.dumps({"quality_checks": []}),
    "bad_version": json.dumps({"policyVersion": "9"}),
    "blocking_checks_wrong_type": json.dumps({"blocking_checks": "all"}),
    "blocking_checks_unknown_id": json.dumps(
        {"blocking_checks": sorted(SECTION_12_CHECKS) + ["telepathy"]}),
    "optional_checks_wrong_type": json.dumps({"optional_checks": {"nfrs": True}}),
    "risk_signals_wrong_type": json.dumps({"risk_signals": []}),
    "risk_signal_weight_not_int": json.dumps({"risk_signals": {"novel": "high"}}),
    "risk_signal_weight_bool": json.dumps({"risk_signals": {"novel": True}}),
    "risk_thresholds_wrong_type": json.dumps({"risk_thresholds": []}),
    "risk_thresholds_unknown_level": json.dumps({"risk_thresholds": {"SEVERE": 1}}),
    "risk_threshold_not_int": json.dumps({"risk_thresholds": {"HIGH": "5"}}),
    "hard_floors_wrong_type": json.dumps({"hard_floors": {}}),
    "hard_floor_wrong_keys": json.dumps({"hard_floors": [{"signal": "x"}]}),
    "hard_floor_unknown_level": json.dumps(
        {"hard_floors": [{"signal": "payment_or_financial", "level": "SEVERE"}]}),
    "required_gates_always_wrong_type": json.dumps({"required_gates_always": {}}),
    "required_gates_by_risk_wrong_type": json.dumps({"required_gates_by_risk": []}),
    "required_gates_by_risk_unknown_level": json.dumps(
        {"required_gates_by_risk": {"SEVERE": []}}),
    "required_gates_by_type_unknown_type": json.dumps(
        {"required_gates_by_type": {"epic": []}}),
    "phantom_gate": json.dumps({"required_gates_always": [
        "gate_constitution", "gate_spec", "gate_plan", "gate_implement",
        "gate_telepathy"]}),
}


@pytest.mark.parametrize("case", sorted(MALFORMED_CASES))
def test_the_policy_reader_is_fail_closed(bare_project, case):
    """N4: every unusable document refuses. None falls back to the built-in —
    that is the failure direction T05's NB-4 must not be inherited into."""
    write_policy(bare_project, MALFORMED_CASES[case])
    before = sha_map(bare_project.root)

    result = bare_project.run("governance", "policy")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "policy_malformed", result
    assert sha_map(bare_project.root) == before


def test_an_unreadable_policy_file_refuses(bare_project):
    """N4: a directory where the file should be is unreadable on every
    platform, unlike a chmod that Windows ignores."""
    target = policy_file(bare_project)
    target.mkdir(parents=True)

    result = bare_project.run("governance", "policy")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "policy_malformed", result


def test_the_policy_reader_has_no_handler_that_returns():
    """N4: `read_governance_policy` must not contain
    `except ...: return <defaults>` anywhere. That shape is precisely what
    makes `read_repo_config` fail-open."""
    fn = function_named(sdle_ast(), "read_governance_policy")
    handlers = [node for node in ast.walk(fn) if isinstance(node, ast.ExceptHandler)]
    assert handlers, "the reader is expected to handle OSError and JSON errors"
    for handler in handlers:
        for node in ast.walk(handler):
            assert not isinstance(node, ast.Return), (
                "read_governance_policy returns from an exception handler")


def _weakening(kind: str):
    if kind == "removes_blocking_check":
        return {"blocking_checks": [c for c in BUILTIN["blocking_checks"]
                                    if c != "security_data_implications"]}
    if kind == "widens_optional_checks":
        return {"optional_checks": ["nfrs", "acceptance_criteria"]}
    if kind == "lowers_signal_weight":
        return {"risk_signals": {"payment_or_financial": 0}}
    if kind == "raises_threshold":
        return {"risk_thresholds": {"HIGH": BUILTIN["risk_thresholds"]["HIGH"] + 3}}
    if kind == "removes_hard_floor":
        return {"hard_floors": [r for r in BUILTIN["hard_floors"]
                                if r.get("signal") != "payment_or_financial"]}
    if kind == "lowers_hard_floor":
        floors = copy.deepcopy(BUILTIN["hard_floors"])
        for rule in floors:
            if rule.get("signal") == "payment_or_financial":
                rule["level"] = "LOW"
        return {"hard_floors": floors}
    if kind == "removes_required_gate":
        return {"required_gates_always": [
            g for g in BUILTIN["required_gates_always"] if g != "gate_plan"]}
    if kind == "removes_required_gate_by_risk":
        by_risk = copy.deepcopy(BUILTIN["required_gates_by_risk"])
        by_risk["HIGH"] = []
        return {"required_gates_by_risk": by_risk}
    raise AssertionError(kind)


WEAKENING_KINDS = (
    "removes_blocking_check",
    "widens_optional_checks",
    "lowers_signal_weight",
    "raises_threshold",
    "removes_hard_floor",
    "lowers_hard_floor",
    "removes_required_gate",
    "removes_required_gate_by_risk",
)


@pytest.mark.parametrize("kind", WEAKENING_KINDS)
def test_a_weakening_override_is_refused(bare_project, kind):
    """N5: D2's monotonicity, one case per weakening shape. This is what makes
    "absent policy -> the built-in" safe."""
    write_policy(bare_project, _weakening(kind))

    result = bare_project.run("governance", "policy")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "policy_weakens_baseline", result
    assert result.data["key"], "the offending key must be named"


STRENGTHENING = {
    "narrows_optional_checks": ({"optional_checks": []}, "optional_checks", []),
    "raises_signal_weight": (
        {"risk_signals": {"payment_or_financial": 9}}, "risk_signals", None),
    "lowers_threshold": ({"risk_thresholds": {"HIGH": 1}}, "risk_thresholds", None),
    "adds_signal": ({"risk_signals": {"regulated_domain": 5}}, "risk_signals", None),
    "adds_hard_floor": (
        {"hard_floors": BUILTIN["hard_floors"] + [
            {"signal": "external_api_surface", "level": "MEDIUM"}]},
        "hard_floors", None),
    "adds_required_gate": (
        {"required_gates_always": BUILTIN["required_gates_always"]
         + ["gate_security"]}, "required_gates_always", None),
}


@pytest.mark.parametrize("kind", sorted(STRENGTHENING))
def test_a_strengthening_override_is_accepted_and_observable(bare_project, kind):
    """N5, the other direction: stricter is always permitted, and the effect
    is visible in the effective policy rather than silently dropped."""
    document, key, expected = STRENGTHENING[kind]
    write_policy(bare_project, document)

    result = bare_project.run("governance", "policy")

    assert result.exit_code == EXIT_OK, result
    assert result.data["source"] == ".sdle/policies/governance-policy.json"
    assert result.data["sha256"] and result.data["sha256"].islower()
    effective = result.data["policy"][key]
    if expected is not None:
        assert effective == expected
    else:
        assert effective != BUILTIN[key], "the strengthening had no effect"


def test_a_dict_key_merges_while_a_list_key_replaces(bare_project):
    """The merge rule, stated once in `sdle.py`, asserted once here: adding a
    signal must not silently drop the other eleven."""
    write_policy(bare_project, {"risk_signals": {"regulated_domain": 5}})

    policy = bare_project.ok("governance", "policy").data["policy"]

    assert policy["risk_signals"]["regulated_domain"] == 5
    for signal, weight in BUILTIN["risk_signals"].items():
        assert policy["risk_signals"][signal] == weight
    assert policy["quality_checks"] == BUILTIN["quality_checks"]


# --------------------------------------------------------------------------
# N6 — `governance policy` is runtime-free
# --------------------------------------------------------------------------


def test_governance_policy_resolves_with_no_workitem_bound(bare_project):
    """N6: §12 places governance before planning, and the policy is
    repository-scoped, so it must not depend on binding a WorkItem."""
    create_wi(bare_project, "Alpha")
    create_wi(bare_project, "Bravo")

    assert bare_project.run("governance", "policy").exit_code == EXIT_OK

    ambiguous = bare_project.run("state", "get")
    assert ambiguous.exit_code == EXIT_REFUSED
    assert ambiguous.reason == "workitem_ambiguous"


def test_governance_is_in_the_runtime_free_set():
    assert "governance" in sdle.RUNTIME_FREE_COMMANDS


def test_governance_policy_writes_nothing_even_with_a_workitem(project):
    """N21, policy half: read-only means read-only."""
    before = sha_map(project.root)
    assert project.run("governance", "policy").exit_code == EXIT_OK
    assert sha_map(project.root) == before


# --------------------------------------------------------------------------
# N7 — the twelve check ids are §12's, exactly
# --------------------------------------------------------------------------


def test_the_twelve_quality_checks_are_exactly_section_12s_list():
    """N7: set equality against a literal, so a rename fails loudly."""
    assert set(BUILTIN["quality_checks"]) == SECTION_12_CHECKS
    assert len(BUILTIN["quality_checks"]) == 12
    assert set(BUILTIN["blocking_checks"]) <= set(BUILTIN["quality_checks"])
    assert set(BUILTIN["optional_checks"]) <= set(BUILTIN["quality_checks"])
    assert set(BUILTIN["optional_checks"]) == {"nfrs"}


def test_the_classification_vocabularies_are_exactly_section_12s():
    assert set(sdle.WORKITEM_TYPES) == {
        "enhancement", "defect", "hotfix", "chore"}
    assert set(sdle.ENGINEERING_FLOWS) == {
        "GREENFIELD", "BROWNFIELD_DISCOVERY", "ITERATIVE", "DEFECT_FIX",
        "HOTFIX"}
    assert sdle.GOVERNANCE_LEVELS == ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# --------------------------------------------------------------------------
# N23 — invariant 7: no policy default value is restated outside sdle.py
# --------------------------------------------------------------------------


def _searchable_files() -> list[Path]:
    """Every versioned prose/config file outside `scripts/sdle.py` and the
    tests. `docs/transition/` is the migration control plane, not the product,
    and this test file itself legitimately quotes §12's check ids."""
    roots = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "CLAUDE.md",
        REPO_ROOT / "docs" / "SDLE-Reference-Guide.md",
    ]
    files = [path for path in roots if path.is_file()]
    for directory in (REPO_ROOT / ".claude" / "skills",
                      REPO_ROOT / ".claude" / "commands",
                      REPO_ROOT / ".claude" / "hooks",
                      REPO_ROOT / ".sdle",
                      REPO_ROOT / "docs" / "architecture"):
        if directory.is_dir():
            files.extend(p for p in sorted(directory.rglob("*")) if p.is_file())
    return files


def policy_identifiers() -> set[str]:
    """The identifier-shaped policy values, derived from the built-in.

    Deliberately *not* every check id: `scope`, `ambiguity`, `constraints`,
    `contradictions`, `nfrs`, `compatibility` and `dependencies` are ordinary
    English words that §12 itself, `SKILL.md`, `hooks.py` and both ADRs use as
    prose, so searching for them would match ten pre-existing files and prove
    nothing. What a *restatement* of the policy must contain is the
    machine-readable vocabulary: every risk-signal id, and the check ids in
    their underscored identifier form. Those are the drift surface.
    """
    needles = set(BUILTIN["risk_signals"])
    needles |= {c for c in BUILTIN["quality_checks"] if "_" in c}
    for rule in BUILTIN["hard_floors"]:
        if "signal" in rule:
            needles.add(rule["signal"])
    return needles


def test_the_policy_identifier_needles_are_not_english_words():
    """Guard against N23 passing vacuously or matching prose. Every needle
    must be an underscored identifier, and there must be a useful number."""
    needles = policy_identifiers()
    assert len(needles) >= 15
    assert all("_" in n and n.islower() for n in needles)


def test_no_policy_default_value_is_restated_outside_sdle_py():
    """N23/A15: `GOVERNANCE_POLICY_BUILTIN` is the single source of truth.
    Executed as a real content search, not asserted by narrative — T05's NB-3
    drift surface must not be reproduced at a security-relevant location."""
    needles = policy_identifiers()

    offenders: dict[str, list[str]] = {}
    for path in _searchable_files():
        try:
            body = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        hits = sorted(n for n in needles if n in body)
        if hits:
            offenders[path.relative_to(REPO_ROOT).as_posix()] = hits
    assert offenders == {}, f"policy defaults restated outside sdle.py: {offenders}"


def test_the_builtin_policy_is_not_written_to_disk_by_any_command(bare_project):
    """N23/F7: writing a default policy file would reproduce NB-3's drift
    surface at the one place it must not exist."""
    bare_project.ok("config", "init")
    assert not policy_file(bare_project).exists()
    contents = sorted(
        p.relative_to(bare_project.root / ".sdle" / "policies").as_posix()
        for p in (bare_project.root / ".sdle" / "policies").rglob("*"))
    assert contents == [".gitkeep"]


# --------------------------------------------------------------------------
# N8/N9 — the input is validated, and severity comes from the policy
# --------------------------------------------------------------------------


def _broken(kind: str):
    document = governance_input()
    if kind == "missing_check":
        del document["quality"]["acceptance_criteria"]
    elif kind == "extra_check":
        document["quality"]["telepathy"] = {"result": "PASS", "finding": None}
    elif kind == "bad_result_value":
        document["quality"]["scope"]["result"] = "OK"
    elif kind == "not_applicable_on_required_check":
        document["quality"]["scope"]["result"] = "NOT_APPLICABLE"
    elif kind == "fail_without_finding":
        document["quality"]["scope"] = {"result": "FAIL", "finding": "   "}
    elif kind == "fail_with_null_finding":
        document["quality"]["scope"] = {"result": "FAIL", "finding": None}
    elif kind == "check_entry_not_an_object":
        document["quality"]["scope"] = "PASS"
    elif kind == "severity_key_in_input":
        document["quality"]["scope"] = {
            "result": "FAIL", "finding": "vague", "severity": "advisory"}
    elif kind == "bad_workitem_type":
        document["classification"]["type"] = "epic"
    elif kind == "bad_flow":
        document["classification"]["flow"] = "WATERFALL"
    elif kind == "unknown_risk_signal":
        document["risk"]["signals"] = ["telepathy"]
    elif kind == "bad_proposed_level":
        document["risk"]["proposedLevel"] = "SEVERE"
    elif kind == "bad_uncertainty":
        document["risk"]["uncertainty"] = "SEVERE"
    elif kind == "signals_not_a_list":
        document["risk"]["signals"] = "external_api_surface"
    elif kind == "unknown_top_level_key":
        document["extra"] = {}
    elif kind == "missing_section":
        del document["risk"]
    elif kind == "bad_input_version":
        document["governanceInputVersion"] = "2"
    elif kind == "quality_not_an_object":
        document["quality"] = []
    elif kind == "not_json":
        return "{ nope"
    elif kind == "json_array":
        return "[]\n"
    else:
        raise AssertionError(kind)
    return document


BROKEN_INPUTS = {
    "missing_check": "quality_incomplete",
    "extra_check": "quality_unknown_check",
    "bad_result_value": "quality_malformed",
    "not_applicable_on_required_check": "quality_not_applicable_refused",
    "fail_without_finding": "quality_malformed",
    "fail_with_null_finding": "quality_malformed",
    "check_entry_not_an_object": "quality_unknown_check",
    "severity_key_in_input": "quality_unknown_check",
    "bad_workitem_type": "classification_invalid",
    "bad_flow": "classification_invalid",
    "unknown_risk_signal": "unknown_risk_signal",
    "bad_proposed_level": "governance_input_malformed",
    "bad_uncertainty": "governance_input_malformed",
    "signals_not_a_list": "governance_input_malformed",
    "unknown_top_level_key": "governance_input_malformed",
    "missing_section": "governance_input_malformed",
    "bad_input_version": "governance_input_malformed",
    "quality_not_an_object": "governance_input_malformed",
    "not_json": "governance_input_malformed",
    "json_array": "governance_input_malformed",
}


@pytest.mark.parametrize("kind", sorted(BROKEN_INPUTS))
def test_a_broken_governance_input_is_refused(project, kind):
    """N8: one case per rule, each with its own reason, and each writing
    nothing. An input SDLE does not fully understand is refused, never
    partially applied."""
    before = sha_map(project.root)

    result = assess(project, _broken(kind))

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == BROKEN_INPUTS[kind], result
    after = sha_map(project.root)
    # The input document itself is the only new file.
    assert set(after) - set(before) == {INPUT_NAME}
    assert not (project.runtime / "governance.json").exists()


def test_a_missing_input_file_is_refused(project):
    result = project.run("governance", "assess", "--input", "no-such-input.json")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_input_malformed", result


def test_the_input_cannot_declare_its_own_severity(project):
    """N9, door 1: an input that adds a `severity` key to a failing blocking
    check is refused outright. Claude cannot mark its own failure advisory."""
    result = assess(project, _broken("severity_key_in_input"))
    assert result.reason == "quality_unknown_check", result


def test_a_policy_that_unblocks_a_check_is_refused(project):
    """N9, door 2: the other way to make a failure advisory is to weaken the
    policy, and monotonicity closes that door too."""
    write_policy(project, _weakening("removes_blocking_check"))
    result = assess(project)
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "policy_weakens_baseline", result


def test_severity_is_read_from_the_policy_not_the_input(project):
    """The positive form: the verdict is a policy fact, not an input fact."""
    document = governance_input()
    document["quality"]["nfrs"] = {"result": "FAIL", "finding": "no NFR budget"}

    blocked = assess(project, document)

    assert blocked.exit_code == EXIT_REFUSED
    assert blocked.reason == "requirements_quality_blocked", blocked
    record = record_of(project)
    assert record["quality"]["result"] == "BLOCKED"
    for check in record["quality"]["checks"]:
        assert check["blocking"] == (check["id"] in BUILTIN["blocking_checks"])


# --------------------------------------------------------------------------
# N19/N22 — the record, its completeness, and its independence from state
# --------------------------------------------------------------------------


def test_governance_is_writable_before_state_json_exists(project):
    """N22: §12 places governance *before* planning, so the record cannot be
    a field of `state.json` — it must exist first."""
    assert not project.state_file.exists()

    assert assess(project).exit_code == EXIT_OK
    assert (project.runtime / "governance.json").is_file()
    assert not project.state_file.exists()

    project.ok("init", session="gov")
    assert project.ok("audit", "verify").exit_code == EXIT_OK


def test_the_record_carries_every_section_12_evidence_item(project):
    """N19: asserted as a required-key set, so a later refactor that drops one
    fails rather than silently shrinking the evidence."""
    document = governance_input()
    document["risk"] = {"signals": ["external_api_surface",
                                    "persistent_data_store"],
                        "proposedLevel": "LOW", "uncertainty": "MEDIUM"}
    assert assess(project, document).exit_code == EXIT_OK

    record = record_of(project)
    assert set(record) >= {
        "governanceVersion", "workitem", "recordedAt", "executionId",
        "requirements", "quality", "classification", "risk", "policy",
    }
    # §12's seven evidence items, one assertion each.
    assert record["quality"]["result"] in ("PASS", "BLOCKED")
    assert record["classification"] == {
        "type": "enhancement", "flow": "ITERATIVE", "advisory": True}
    assert record["risk"]["signals"] == ["external_api_surface",
                                         "persistent_data_store"]
    assert isinstance(record["risk"]["score"], int)
    assert isinstance(record["risk"]["floorsApplied"], list)
    assert record["risk"]["finalLevel"] in sdle.GOVERNANCE_LEVELS
    assert record["risk"]["uncertainty"] == "MEDIUM"

    assert len(record["quality"]["checks"]) == 12
    assert {c["id"] for c in record["quality"]["checks"]} == SECTION_12_CHECKS
    assert record["requirements"]["digest"]
    assert record["requirements"]["sources"]
    assert record["policy"]["source"] == "builtin"


def test_governance_show_reports_the_record_and_its_freshness(project):
    assert assess(project).exit_code == EXIT_OK

    shown = project.ok("governance", "show")

    assert shown.data["fresh"] is True
    assert shown.data["record"] == record_of(project)
    assert shown.data["recorded_digest"] == shown.data["current_digest"]

    (project.root / "requirements" / "extra.md").write_text(
        "# Extra\n", encoding="utf-8", newline="\n")
    stale = project.ok("governance", "show")
    assert stale.data["fresh"] is False
    assert stale.data["recorded_digest"] != stale.data["current_digest"]


def test_governance_show_refuses_when_there_is_no_record(project):
    result = project.run("governance", "show")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_missing", result


def test_a_blocked_assessment_still_persists_the_record(project):
    """N10, first half: fail safe means the blocked verdict is inspectable and
    remediable, not invisible."""
    document = governance_input()
    document["quality"]["acceptance_criteria"] = {
        "result": "FAIL", "finding": "no measurable criteria for the filter"}

    result = assess(project, document)

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "requirements_quality_blocked", result
    assert result.data["blocking"] == ["acceptance_criteria"]
    record = record_of(project)
    assert record["quality"]["result"] == "BLOCKED"
    assert record["quality"]["blocking"] == ["acceptance_criteria"]
    assert [c["finding"] for c in record["quality"]["checks"]
            if c["id"] == "acceptance_criteria"] == [
                "no measurable criteria for the filter"]


def test_not_applicable_is_permitted_only_where_the_policy_allows_it(project):
    document = governance_input()
    document["quality"]["nfrs"] = {
        "result": "NOT_APPLICABLE", "finding": "no NFR is in scope"}

    assert assess(project, document).exit_code == EXIT_OK
    entry = [c for c in record_of(project)["quality"]["checks"]
             if c["id"] == "nfrs"][0]
    assert entry["result"] == "NOT_APPLICABLE"
    assert entry["optional"] is True


# --------------------------------------------------------------------------
# N21 — purity
# --------------------------------------------------------------------------


def test_assess_writes_only_the_record_and_one_evidence_file(project):
    """N21: and it appends NO audit entry — it may run before `init`, so
    there is no `audit_sha` to rebaseline and no state file to save."""
    write_input(project, governance_input())
    before = sha_map(project.root)

    assert project.run("governance", "assess", "--input", INPUT_NAME).exit_code == 0

    added = sorted(set(sha_map(project.root)) - set(before))
    runtime = project.runtime.relative_to(project.root).as_posix()
    assert len(added) == 2, added
    assert f"{runtime}/governance.json" in added
    assert any(p.startswith(f"{runtime}/evidence/governance-") for p in added)
    assert not project.audit_file.exists()


def test_show_is_read_only(project):
    assert assess(project).exit_code == EXIT_OK
    before = sha_map(project.root)
    assert project.run("governance", "show").exit_code == EXIT_OK
    assert sha_map(project.root) == before


def test_the_evidence_document_records_proposal_and_decision(project):
    document = governance_input()
    document["risk"] = {"signals": ["payment_or_financial"],
                        "proposedLevel": "LOW", "uncertainty": "LOW"}
    assert assess(project, document).exit_code == EXIT_OK

    evidence = sorted((project.runtime / "evidence").glob("governance-*.json"))
    assert len(evidence) == 1
    payload = json.loads(evidence[0].read_text(encoding="utf-8"))
    assert payload["kind"] == "governance"
    assert payload["input"]["document"] == document
    assert payload["record"] == record_of(project)


def test_governance_refuses_under_the_legacy_binding(bare_project):
    """Governance is WorkItem-scoped. §8.9 says the legacy runtime is never
    written to, so `assess` must refuse rather than write into `.workflow/`."""
    legacy = bare_project.root / ".workflow"
    legacy.mkdir()
    (legacy / "state.json").write_text(
        json.dumps({"workflow_version": "1.15", "current_phase": "spec_draft"}),
        encoding="utf-8")
    write_input(bare_project, governance_input())

    result = bare_project.run("governance", "assess", "--input", INPUT_NAME)

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_workitem_required", result
    assert not (legacy / "governance.json").exists()


# --------------------------------------------------------------------------
# N10/N11/N12 — enforcement clause E1, inside `apply_advance`
# --------------------------------------------------------------------------
#
# §12 states three consequences as MUSTs and the core refuses rather than
# warning. Every case below drives the real CLI and asserts the fail-safe
# shape as well as the refusal: nothing moved, nothing was approved, and the
# audit chain did not advance.


def blocked_input() -> dict:
    """A proposal that fails one *blocking* check, with a finding."""
    document = governance_input()
    document["quality"]["acceptance_criteria"] = {
        "result": "FAIL",
        "finding": "no measurable criteria for the filter endpoint",
    }
    return document


def frozen(project: Project) -> tuple:
    """The facts a refusal must leave untouched."""
    state = project.state()
    return (state["current_phase"], state["status"], state["approvals"],
            state["artifact_shas"], state["audit_sha"])


def test_a_blocking_finding_stops_progression_and_the_record_survives(project):
    """N10. `governance assess` persists before it refuses, so a blocked
    assessment is inspectable and remediable rather than invisible."""
    assert "acceptance_criteria" in BUILTIN["blocking_checks"]

    blocked = assess(project, blocked_input())
    assert blocked.exit_code == EXIT_REFUSED, blocked
    assert blocked.reason == "requirements_quality_blocked", blocked

    record = record_of(project)
    assert record["quality"]["result"] == "BLOCKED"
    assert record["quality"]["blocking"] == ["acceptance_criteria"]

    # Governance is not an `init` precondition: a WorkItem must be able to
    # bootstrap. The refusal lands at the first phase movement instead.
    project.ok("init", session="blocked")
    before = frozen(project)

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_blocked", result
    assert result.data["blocking"] == ["acceptance_criteria"]
    assert result.data["findings"]["acceptance_criteria"].startswith(
        "no measurable criteria")
    assert frozen(project) == before, "a refusal freezes; it never advances"


def test_re_assessing_a_fixed_requirement_unblocks_the_same_advance(project):
    """N10, second half: the refusal is remediable, not terminal."""
    assert assess(project, blocked_input()).exit_code == EXIT_REFUSED
    project.ok("init", session="blocked")
    assert project.run("advance", "--to", "gate_constitution").reason \
        == "governance_blocked"

    assert assess(project).exit_code == EXIT_OK

    project.ok("advance", "--to", "gate_constitution")
    assert project.state()["current_phase"] == "gate_constitution"


def test_advance_without_a_governance_record_is_refused(project):
    """N11(a). §12 requires the metadata *before* planning begins."""
    project.ok("init", session="missing")
    before = frozen(project)

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_missing", result
    assert result.data["workitem"] == project.workitem
    assert "governance assess" in result.envelope["message"]
    assert frozen(project) == before
    assert not (project.runtime / "governance.json").exists()


def test_gate_approve_inherits_the_same_clause(project):
    """E1 lives in `apply_advance`, which is why the other two phase-movement
    commands inherit it. Putting it in `cmd_advance` would leave `gate
    approve` and `skip` unguarded — that would be fail-open."""
    assert assess(project).exit_code == EXIT_OK
    project.ok("init", session="guard")
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution")
    # T06: satisfy E2 first, so E1 is the only precondition left standing
    # between here and approval.
    review_for_gate(project, "gate_constitution")

    # Remove the record underneath a workflow already standing at a gate, so
    # the only thing that changed is the governance precondition.
    (project.runtime / "governance.json").unlink()
    before = frozen(project)

    approve = project.run("gate", "approve", "--gate", "gate_constitution")

    assert approve.exit_code == EXIT_REFUSED, approve
    assert approve.reason == "governance_missing", approve
    assert frozen(project) == before


def test_the_clause_has_exactly_one_enforcement_site(project):
    """The structural half of the same argument: `governance_precondition` is
    called from `apply_advance` and nowhere else, and all three phase-movement
    commands funnel through `apply_advance`. One site to write, one to audit."""
    tree = sdle_ast()
    callers = sorted(
        fn.name for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef)
        and fn.name != "governance_precondition"
        and any(isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "governance_precondition"
                for node in ast.walk(fn))
    )
    assert callers == ["apply_advance"], callers

    movers = sorted(
        fn.name for fn in ast.walk(tree)
        if isinstance(fn, ast.FunctionDef)
        and any(isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "apply_advance"
                for node in ast.walk(fn))
    )
    assert movers == ["cmd_advance", "cmd_gate_approve", "cmd_skip"], movers


def test_editing_a_requirement_after_the_assessment_is_stale(project):
    """N11(b). The recorded digest no longer describes what is on disk."""
    assert assess(project).exit_code == EXIT_OK
    recorded = record_of(project)["requirements"]["digest"]
    project.ok("init", session="stale")

    target = project.root / "requirements" / "todo-api.md"
    target.write_text(target.read_text(encoding="utf-8") + "\n- PATCH /todos\n",
                      encoding="utf-8", newline="\n")
    before = frozen(project)

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_stale", result
    assert result.data["recorded_digest"] == recorded
    assert result.data["current_digest"] != recorded
    assert "governance assess" in result.envelope["message"]
    assert frozen(project) == before

    assert assess(project).exit_code == EXIT_OK
    project.ok("advance", "--to", "gate_constitution")
    assert project.state()["current_phase"] == "gate_constitution"


def test_adding_a_requirement_file_is_also_stale(project):
    """N11(c). The digest covers the requirement *set*, not one file, so a
    new document cannot slip past an assessment that never saw it."""
    assert assess(project).exit_code == EXIT_OK
    project.ok("init", session="stale2")

    (project.root / "requirements" / "billing.md").write_text(
        "# Billing\n\nA second requirement document.\n",
        encoding="utf-8", newline="\n")
    before = frozen(project)

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_stale", result
    assert "requirements/billing.md" in result.data["requirements"]
    assert frozen(project) == before


def test_e1_is_skipped_under_the_legacy_binding_and_only_there(bare_project):
    """N12. The transitional `.workflow/` rung has no WorkItem to hold a
    record, so E1 stands aside there — a declared bounded residual T11 removes
    with the rung itself. Pinned in both directions so it cannot widen."""
    template = json.loads(
        (bare_project.skill_root / "templates" / "state.json").read_text(
            encoding="utf-8"))
    legacy = bare_project.root / ".workflow"
    legacy.mkdir()
    (legacy / "state.json").write_text(json.dumps(template, indent=2) + "\n",
                                       encoding="utf-8", newline="\n")

    assert bare_project.workitem is None, "rung 3 needs zero WorkItems"
    moved = bare_project.run("advance", "--to", "constitution_draft")
    assert moved.exit_code == EXIT_OK, moved
    assert not (legacy / "governance.json").exists()

    # The same sequence with a WorkItem bound refuses. `init` refuses a
    # legacy workflow unconditionally (T02), so the rung is retired first.
    workitem = create_wi(bare_project, "Wi A")
    shutil.rmtree(legacy)
    bound = bare_project.as_workitem(workitem)
    bound.ok("init", session="contrast")

    refused = bound.run("advance", "--to", "gate_constitution")
    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "governance_missing", refused


# --------------------------------------------------------------------------
# N13 — classification is validated, recorded and inert
# --------------------------------------------------------------------------


@pytest.mark.parametrize("flow", sdle.ENGINEERING_FLOWS)
@pytest.mark.parametrize("wi_type", sdle.WORKITEM_TYPES)
def test_every_valid_classification_round_trips(project, wi_type, flow):
    document = governance_input()
    document["classification"] = {"type": wi_type, "flow": flow}

    assert assess(project, document).exit_code == EXIT_OK

    assert record_of(project)["classification"] == {
        "type": wi_type, "flow": flow, "advisory": True}


def test_classification_is_marked_advisory_in_the_record(project):
    assert assess(project).exit_code == EXIT_OK
    assert record_of(project)["classification"]["advisory"] is True


# --------------------------------------------------------------------------
# N14/N15/N16/N18 — the risk engine
# --------------------------------------------------------------------------


def risk_of(signals, proposed="LOW", uncertainty="LOW", policy=None) -> dict:
    document = governance_input()
    document["risk"] = {"signals": list(signals), "proposedLevel": proposed,
                        "uncertainty": uncertainty}
    return sdle.evaluate_risk(document, policy or BUILTIN, "<input>")


SCORING_CASES = [
    ([], 0),
    (["third_party_dependency"], 1),
    (["external_api_surface"], 2),
    (["external_api_surface", "persistent_data_store"], 4),
    (["external_api_surface", "external_api_surface"], 2),
    (["payment_or_financial", "cryptography_or_secrets"], 8),
    (sorted(BUILTIN["risk_signals"]), sum(BUILTIN["risk_signals"].values())),
]


@pytest.mark.parametrize("signals,expected", SCORING_CASES)
def test_the_score_is_the_sum_of_the_policy_weights(signals, expected):
    """N14: table-driven, and the weights come from the policy, so a changed
    weight changes the score rather than the arithmetic."""
    assert risk_of(signals)["score"] == expected


@pytest.mark.parametrize("score,expected", [
    (0, "LOW"), (1, "LOW"), (2, "MEDIUM"), (4, "MEDIUM"),
    (5, "HIGH"), (8, "HIGH"), (9, "CRITICAL"), (99, "CRITICAL"),
])
def test_the_level_is_the_highest_threshold_met(score, expected):
    """N14: the threshold ladder, read from the policy."""
    assert sdle.deterministic_level(
        score, BUILTIN["risk_thresholds"]) == expected


def test_an_unknown_signal_is_refused_not_ignored(project):
    """N14: a silently ignored signal is a silently lowered risk."""
    document = governance_input()
    document["risk"] = {"signals": ["external_api_surface", "telepathy"],
                        "proposedLevel": "LOW", "uncertainty": "LOW"}

    result = assess(project, document)

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "unknown_risk_signal", result
    assert result.data["unknown"] == ["telepathy"]


SIGNAL_FLOORS = [rule for rule in BUILTIN["hard_floors"] if "signal" in rule]
UNCERTAINTY_FLOORS = [r for r in BUILTIN["hard_floors"] if "uncertainty" in r]


@pytest.mark.parametrize("rule", SIGNAL_FLOORS,
                         ids=[r["signal"] for r in SIGNAL_FLOORS])
def test_each_signal_hard_floor_fires_and_is_recorded(rule):
    """N15: one case per built-in floor rule, and `floorsApplied` names the
    rule that fired rather than just the resulting level."""
    risk = risk_of([rule["signal"]])

    fired = [entry["rule"] for entry in risk["floorsApplied"]]
    assert rule in fired
    assert sdle.GOVERNANCE_LEVELS.index(risk["deterministicLevel"]) >= \
        sdle.GOVERNANCE_LEVELS.index(rule["level"])


@pytest.mark.parametrize("rule", UNCERTAINTY_FLOORS,
                         ids=[r["uncertainty"] for r in UNCERTAINTY_FLOORS])
def test_each_uncertainty_hard_floor_fires_and_is_recorded(rule):
    """N15/N18: uncertainty carries a floor of its own."""
    risk = risk_of([], uncertainty=rule["uncertainty"])

    fired = [entry["rule"] for entry in risk["floorsApplied"]]
    assert rule in fired
    assert risk["deterministicLevel"] == rule["level"]
    assert risk["uncertainty"] == rule["uncertainty"]


def test_a_floor_raises_the_level_the_score_alone_would_not_reach():
    """N15: `authentication_or_authorization` weighs 3, which the thresholds
    put at MEDIUM anyway, so use the one that genuinely outruns its weight."""
    alone = risk_of(["personal_or_sensitive_data"])
    assert alone["score"] == BUILTIN["risk_signals"]["personal_or_sensitive_data"]
    by_score = sdle.deterministic_level(alone["score"], BUILTIN["risk_thresholds"])
    assert sdle.GOVERNANCE_LEVELS.index(alone["deterministicLevel"]) > \
        sdle.GOVERNANCE_LEVELS.index(by_score)


def test_uncertainty_round_trips_into_the_record(project):
    """N18."""
    for level in sdle.GOVERNANCE_LEVELS:
        document = governance_input()
        document["risk"] = {"signals": [], "proposedLevel": "LOW",
                            "uncertainty": level}
        assert assess(project, document).exit_code == EXIT_OK
        assert record_of(project)["risk"]["uncertainty"] == level


def test_an_override_may_add_an_uncertainty_floor(project):
    """N18: a repository may only make governance stricter, and this is what
    "stricter" looks like end to end."""
    document = governance_input()
    document["risk"] = {"signals": [], "proposedLevel": "LOW",
                        "uncertainty": "MEDIUM"}

    assert assess(project, document).exit_code == EXIT_OK
    assert record_of(project)["risk"]["finalLevel"] == "LOW"

    write_policy(project, {"hard_floors": BUILTIN["hard_floors"] + [
        {"uncertainty": "MEDIUM", "level": "HIGH"}]})

    assert assess(project, document).exit_code == EXIT_OK
    record = record_of(project)
    assert record["risk"]["finalLevel"] == "HIGH"
    assert record["risk"]["deterministicLevel"] == "HIGH"
    assert record["policy"]["source"] == ".sdle/policies/governance-policy.json"


def _all_signal_subsets():
    names = sorted(BUILTIN["risk_signals"])
    for mask in range(1 << len(names)):
        yield [names[i] for i in range(len(names)) if mask & (1 << i)]


def test_claude_can_never_lower_a_deterministic_floor():
    """N16/A12 — the security property of this phase, as a property test over
    the FULL cross-product of every signal subset and every proposed level.

    Exercised against the pure evaluator rather than the CLI so the whole
    2**12 x 4 cross-product is affordable; the CLI path is proved separately
    by `test_a_lowering_attempt_is_recorded_and_ineffective`.
    """
    index = sdle.GOVERNANCE_LEVELS.index
    checked = 0
    for signals in _all_signal_subsets():
        for proposed in sdle.GOVERNANCE_LEVELS:
            risk = risk_of(signals, proposed=proposed)
            deterministic = risk["deterministicLevel"]
            final = risk["finalLevel"]
            assert index(final) >= index(deterministic), (signals, proposed)
            assert final == max((deterministic, proposed), key=index)
            assert risk["loweringAttempted"] == (
                index(proposed) < index(deterministic))
            checked += 1
    assert checked == (1 << len(BUILTIN["risk_signals"])) * 4


def test_a_lowering_attempt_is_recorded_and_ineffective(project):
    """A12's hand-crafted case, driven through the real CLI: `LOW` proposed
    against a `CRITICAL` floor yields `CRITICAL`, `loweringAttempted: true`,
    and exit 0 — an honest low estimate must not deadlock the workflow."""
    document = governance_input()
    document["risk"] = {"signals": ["payment_or_financial"],
                        "proposedLevel": "LOW", "uncertainty": "CRITICAL"}

    assert assess(project, document).exit_code == EXIT_OK

    risk = record_of(project)["risk"]
    assert risk["deterministicLevel"] == "CRITICAL"
    assert risk["finalLevel"] == "CRITICAL"
    assert risk["proposedLevel"] == "LOW"
    assert risk["loweringAttempted"] is True


def test_a_higher_proposal_is_honoured(project):
    """The lattice is a maximum, not a floor-only rule: Claude may raise."""
    document = governance_input()
    document["risk"] = {"signals": [], "proposedLevel": "HIGH",
                        "uncertainty": "LOW"}

    assert assess(project, document).exit_code == EXIT_OK

    risk = record_of(project)["risk"]
    assert risk["deterministicLevel"] == "LOW"
    assert risk["finalLevel"] == "HIGH"
    assert risk["loweringAttempted"] is False


def test_only_evaluate_risk_produces_a_final_level():
    """There must be no second place in the engine that can decide a final
    risk level — one producer, or the property test above proves nothing."""
    tree = sdle_ast()
    producers, readers = set(), set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for child in ast.walk(node):
            # Building the key is producing it; subscripting it is reading it.
            if isinstance(child, ast.Dict) and any(
                    isinstance(k, ast.Constant) and k.value == "finalLevel"
                    for k in child.keys):
                producers.add(node.name)
            elif isinstance(child, ast.Constant) and child.value == "finalLevel":
                readers.add(node.name)
    assert producers == {"evaluate_risk"}
    # The reader set is closed and grows only for a reader that genuinely
    # needs the decided level: `record_governance_audit` names it in the
    # ledger entry (N17). None of these can decide one.
    assert readers - producers == {"cmd_governance_assess",
                                   "cmd_governance_gates",
                                   "record_governance_audit"}


# --------------------------------------------------------------------------
# N20(a)(b)(c) — the would-be gate set is computed and never acted on
# --------------------------------------------------------------------------


def registered_gate_keys(project: Project) -> set[str]:
    consts = sdle.load_constants(paths_for(project))
    return set(consts.phase_to_gate_key.values())


@pytest.mark.parametrize("level", sdle.GOVERNANCE_LEVELS)
@pytest.mark.parametrize("wi_type", sdle.WORKITEM_TYPES)
def test_the_would_be_gate_set_is_always_a_subset_of_the_registered_gates(
        project, wi_type, level):
    """N20(a)."""
    document = governance_input()
    document["classification"] = {"type": wi_type, "flow": "ITERATIVE"}
    document["risk"] = {"signals": [], "proposedLevel": level,
                        "uncertainty": "LOW"}
    assert assess(project, document).exit_code == EXIT_OK

    shown = project.ok("governance", "gates")

    gates = set(shown.data["would_be_required_gates"])
    assert gates <= registered_gate_keys(project)
    assert gates, "an empty would-be set would make the comparison vacuous"
    assert shown.data["advisory"] is True
    assert set(record_of(project)["wouldBeRequiredGates"]) == gates


def test_the_would_be_gate_set_actually_differs_across_risk_levels(project):
    """A18: the set must be non-trivial, or "the traversal does not move"
    would be true for an uninteresting reason."""
    seen = {}
    for level in ("LOW", "CRITICAL"):
        document = governance_input()
        document["risk"] = {"signals": [], "proposedLevel": level,
                            "uncertainty": "LOW"}
        assert assess(project, document).exit_code == EXIT_OK
        seen[level] = set(project.ok("governance", "gates")
                          .data["would_be_required_gates"])
    assert seen["LOW"] < seen["CRITICAL"]


LIFECYCLE_PREFIXES = ("apply_advance", "cmd_advance", "cmd_gate", "cmd_approve",
                      "cmd_skip")


def lifecycle_functions(tree: ast.Module) -> list[ast.FunctionDef]:
    return [node for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef)
            and node.name.startswith(LIFECYCLE_PREFIXES)]


def test_no_phase_movement_function_consults_the_would_be_gate_set():
    """N20(b): §12 says record the would-be gate set, do not act on it."""
    tree = sdle_ast()
    for fn in lifecycle_functions(tree):
        referenced = names_referenced(fn)
        assert "required_gate_set" not in referenced, fn.name
        for node in ast.walk(fn):
            assert not (isinstance(node, ast.Constant)
                        and node.value == "wouldBeRequiredGates"), fn.name


def test_the_phase_movement_prefixes_actually_match_something():
    """N20(c): guard against the previous test passing vacuously."""
    names = {fn.name for fn in lifecycle_functions(sdle_ast())}
    assert {"apply_advance", "cmd_advance", "cmd_gate_approve",
            "cmd_gate_reject", "cmd_skip"} <= names


def test_governance_gates_is_read_only(project):
    """N21, gates half."""
    assert assess(project).exit_code == EXIT_OK
    before = sha_map(project.root)
    assert project.run("governance", "gates").exit_code == EXIT_OK
    assert sha_map(project.root) == before


def test_governance_gates_refuses_without_a_record(project):
    result = project.run("governance", "gates")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "governance_missing", result


# --------------------------------------------------------------------------
# N17/N32 — D10 audit linkage, and the governance facts in the ledger
# --------------------------------------------------------------------------


def audit_entries(project: Project) -> list[str]:
    return sdle.split_audit_entries(
        project.audit_file.read_text(encoding="utf-8"))


def lowering_input() -> dict:
    """A CRITICAL floor with a LOW proposal — A12's shape."""
    document = governance_input()
    floor = BUILTIN["hard_floors"][0]
    document["risk"] = {"signals": [floor["signal"]], "proposedLevel": "LOW",
                        "uncertainty": "LOW"}
    return document


def test_a_lowering_attempt_reaches_the_ledger_and_the_chain_still_verifies(
    project,
):
    """N17. The attempt is not a refusal — an honest low estimate must not
    deadlock a workflow — so the security property is that it has no effect
    *and* that it leaves a trace nobody has to be told about."""
    document = lowering_input()
    assert assess(project, document).exit_code == EXIT_OK
    risk = record_of(project)["risk"]
    assert risk["loweringAttempted"] is True
    assert risk["finalLevel"] == risk["deterministicLevel"] != "LOW"

    project.ok("init", session="lowering")
    assert sdle.GOVERNANCE_AUDIT_EVENT not in project.audit_file.read_text(
        encoding="utf-8"), "governance is not an `init` precondition"

    project.ok("advance", "--to", "gate_constitution")

    text = project.audit_file.read_text(encoding="utf-8")
    entry = [block for block in audit_entries(project)
             if sdle.GOVERNANCE_AUDIT_EVENT in block]
    assert len(entry) == 1, text
    assert f"proposed {risk['proposedLevel']}" in entry[0]
    assert f"final {risk['finalLevel']}" in entry[0]
    assert "no effect" in entry[0]
    assert project.ok("audit", "verify").data["matches"] is True


def test_the_governance_entry_is_written_once_per_assessment(project):
    """N17, de-duplication half: eighteen advances do not write eighteen
    entries, and a re-assessment is a new fact that does get its own."""
    assert assess(project).exit_code == EXIT_OK
    project.ok("init", session="once")
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution")
    review_for_gate(project, "gate_constitution")  # T06: E2.
    project.ok("gate", "approve", "--gate", "gate_constitution")

    def governance_blocks():
        return [b for b in audit_entries(project)
                if sdle.GOVERNANCE_AUDIT_EVENT in b]

    assert len(governance_blocks()) == 1

    assert assess(project).exit_code == EXIT_OK  # a new executionId
    project.write_artifact(f"workitems/{project.workitem}/specs/001-x/spec.md")
    project.ok("advance", "--to", "gate_spec")

    assert len(governance_blocks()) == 2
    assert project.ok("audit", "verify").data["matches"] is True


def test_a_refused_advance_writes_no_governance_entry(project):
    """The entry lands after every refusal has had its chance to fire."""
    assert assess(project, blocked_input()).exit_code == EXIT_REFUSED
    project.ok("init", session="refused")
    before = project.audit_file.read_text(encoding="utf-8")

    assert project.run("advance", "--to", "gate_constitution").reason \
        == "governance_blocked"

    assert project.audit_file.read_text(encoding="utf-8") == before


def test_the_audit_block_is_byte_identical_without_a_review(project):
    """N32. D10's two arguments default to None, and a None rendering must be
    byte-for-byte what every pre-T06 entry looks like — otherwise an existing
    ledger stops verifying at the first entry T06 writes."""
    signature = inspect.signature(sdle.append_audit)
    for name in ("review", "evidence_id"):
        assert signature.parameters[name].default is None, name

    project.ok("init", session="bytes")
    paths = sdle.resolve_paths(str(project.root), str(project.skill_root))
    paths = sdle.dataclass_replace(paths, workitem=project.workitem)

    state = project.state()
    sdle.append_audit(paths, state, phase="spec_draft", event="probe",
                      message="A probe entry.")
    implicit = audit_entries(project)[-1]

    sdle.append_audit(paths, state, phase="spec_draft", event="probe",
                      message="A probe entry.", review=None, evidence_id=None)
    explicit = audit_entries(project)[-1]

    # The header carries a timestamp and the tail carries the chain hash of
    # whatever preceded it; everything between them is the rendering under
    # test, and that is what must not have moved.
    body = lambda block: block.strip().splitlines()[1:-1]
    assert body(explicit) == body(implicit)
    assert len(body(implicit)) == 6, body(implicit)
    assert "**Review:**" not in implicit
    assert "**Evidence:**" not in implicit
    assert implicit.strip().splitlines()[-1].startswith("**Prev:** ")


def test_a_supplied_review_renders_before_the_chain_tail(project):
    """N32, second half: `Prev` stays the last line of every entry, and the
    review result never borrows the gate-decision field."""
    project.ok("init", session="lines")
    paths = sdle.dataclass_replace(
        sdle.resolve_paths(str(project.root), str(project.skill_root)),
        workitem=project.workitem)
    state = project.state()

    sdle.append_audit(paths, state, phase="spec_draft",
                      event="artifact_reviewed",
                      message="A reviewed artifact.",
                      review="architecture-review | PASS | agent:sdle-architect",
                      evidence_id="evidence/review-x-1.json")
    sdle.save_state(paths, state)

    block = audit_entries(project)[-1]
    lines = block.strip().splitlines()
    assert lines[-1].startswith("**Prev:** ")
    assert lines[-3].startswith("**Review:** ")
    assert lines[-2].startswith("**Evidence:** ")
    assert "**Gate Decision:** n/a" in block, "a review is not a gate decision"

    for entry in audit_entries(project):
        assert entry.strip().splitlines()[-1].startswith("**Prev:** ")
    assert project.ok("audit", "verify").data["matches"] is True


# --------------------------------------------------------------------------
# A17 / N13 (differential half) / N20(d) — governance is recorded, and moves
# nothing.
#
# Written after the engine was complete, so it pins what shipped rather than
# what was planned. Four scratch repositories, byte-identical at the start,
# differing *only* in the governance record they carry: the traversal, the
# approvals, the approval-baseline key set and the ordered audit event
# sequence must be indistinguishable. T07 is the phase permitted to change
# that; T06 must not anticipate it, so the would-be gate set is shown to
# differ while the traversal does not.
# --------------------------------------------------------------------------

AUDIT_HEADER = re.compile(
    r"^## AUDIT \[[^\]]*\] \| (?P<phase>.+?) — (?P<event>.+)$")

# The two event kinds T06 itself introduces. Everything else in the ledger is
# lifecycle, and must be identical across variants.
T06_AUDIT_EVENTS = frozenset({sdle.GOVERNANCE_AUDIT_EVENT, "artifact_reviewed"})


def lifecycle_audit_events(project: Project) -> list[tuple[str, str]]:
    """Ordered (phase, event) pairs, modulo the entries T06 adds."""
    text = project.audit_file.read_text(encoding="utf-8")
    pairs = [(match.group("phase"), match.group("event"))
             for line in text.splitlines()
             for match in [AUDIT_HEADER.match(line)] if match]
    return [pair for pair in pairs if pair[1] not in T06_AUDIT_EVENTS]


def clone_project(project: Project, destination: Path) -> Project:
    """A second scratch repository, identical to the first byte for byte."""
    shutil.copytree(project.root, destination)
    return Project(destination, destination / ".claude" / "skills" / "sdle",
                   workitem=project.workitem, pin=project.pin)


def drive_with(monkeypatch, project: Project, **document) -> list[str]:
    """Run the whole transcript with a chosen governance record.

    `run_happy_path` records governance itself — it has to, because E1 refuses
    without it — so the variant is injected by overriding the *fixture*
    method's default document for the duration of the run. Nothing in the
    engine is patched, and the CLI is driven exactly as every other case
    drives it.
    """
    original = Project.record_governance

    def patched(self, **over):
        merged = dict(document)
        merged.update(over)
        return original(self, **merged)

    monkeypatch.setattr(Project, "record_governance", patched)
    try:
        return run_happy_path(project)
    finally:
        monkeypatch.setattr(Project, "record_governance", original)


LOW_RISK = {"signals": [], "proposedLevel": "LOW", "uncertainty": "LOW"}
CRITICAL_RISK = {
    "signals": ["personal_or_sensitive_data", "payment_or_financial",
                "cryptography_or_secrets"],
    "proposedLevel": "CRITICAL",
    "uncertainty": "CRITICAL",
}

GOVERNANCE_VARIANTS = {
    "baseline": {
        "classification": {"type": "enhancement", "flow": "ITERATIVE"},
        "risk": LOW_RISK},
    # N13: classification alone.
    "classification_only": {
        "classification": {"type": "defect", "flow": "DEFECT_FIX"},
        "risk": LOW_RISK},
    # N20(d): final risk alone, LOW against CRITICAL.
    "risk_only": {
        "classification": {"type": "enhancement", "flow": "ITERATIVE"},
        "risk": CRITICAL_RISK},
    # A17: both at once.
    "both": {
        "classification": {"type": "hotfix", "flow": "HOTFIX"},
        "risk": CRITICAL_RISK},
}


def approval_shape(project: Project) -> dict:
    """The approval facts two runs must share. Timestamps legitimately differ."""
    return {gate: (entry or {}).get("decision")
            for gate, entry in (project.state()["approvals"] or {}).items()}


def test_governance_changes_no_lifecycle_behaviour(git_project, tmp_path,
                                                   monkeypatch):
    """A17 + N13 + N20(d): the eight gates stay unconditional.

    Every clone is taken *before* any run, so the four repositories genuinely
    start identical rather than inheriting the baseline's runtime.
    """
    views = {"baseline": git_project}
    for name in GOVERNANCE_VARIANTS:
        if name != "baseline":
            views[name] = clone_project(git_project, tmp_path / name)

    traversals = {name: drive_with(monkeypatch, views[name],
                                   **GOVERNANCE_VARIANTS[name])
                  for name in GOVERNANCE_VARIANTS}

    # 0. The variants really took effect — otherwise everything below would be
    #    true for the uninteresting reason that all four records are the same.
    levels = {name: record_of(view)["risk"]["finalLevel"]
              for name, view in views.items()}
    assert levels["baseline"] == "LOW", levels
    assert levels["classification_only"] == "LOW", levels
    assert levels["risk_only"] == "CRITICAL", levels
    assert levels["both"] == "CRITICAL", levels
    types = {name: record_of(view)["classification"]["type"]
             for name, view in views.items()}
    assert len(set(types.values())) == 3, types

    # 1. Identical traversals, each equal to the transcript's.
    for name, traversal in traversals.items():
        assert traversal == EXPECTED_TRAVERSAL, name

    # 2. Identical approvals, identical baseline key sets, identical ordered
    #    lifecycle audit events.
    base = views["baseline"]
    base_events = lifecycle_audit_events(base)
    base_approvals = approval_shape(base)
    base_shas = sorted(base.state()["artifact_shas"])
    assert len(base_approvals) == 8 and set(base_approvals.values()) == {"approved"}
    assert len(base_shas) == 8

    for name, view in views.items():
        if name == "baseline":
            continue
        assert lifecycle_audit_events(view) == base_events, name
        assert approval_shape(view) == base_approvals, name
        assert sorted(view.state()["artifact_shas"]) == base_shas, name
        assert view.state()["current_phase"] == "complete", name
        assert view.state()["progress"] == base.state()["progress"], name

    # 3. A18: the would-be required gate set *does* differ, so clause 2 is not
    #    vacuous. Recorded, never acted on.
    would_be = {name: set(view.ok("governance", "gates")
                          .data["would_be_required_gates"])
                for name, view in views.items()}
    assert would_be["baseline"] < would_be["risk_only"], would_be
    assert would_be["baseline"] != would_be["classification_only"], would_be


# --------------------------------------------------------------------------
# A14 — the phase's one declared new exit-3 path, pinned rather than narrated
# --------------------------------------------------------------------------


@pytest.mark.parametrize("corruption", ["{not json", '"a string"', "[]"])
def test_a_corrupt_governance_record_is_an_integrity_failure(project,
                                                             corruption):
    """A corrupt record is not the same fact as no record.

    Returning `None` here would let a damaged file read as "never assessed"
    and then be silently overwritten, losing the evidence. Every other
    unreadable runtime file SDLE itself wrote is an integrity failure
    (`state_unreadable`, `legacy_state_invalid`, `index_malformed`), so this
    one is too — the phase's only new exit-3 path, and a declared divergence
    from acceptance criterion A14's "exit 1 or 2 only".
    """
    assert assess(project).exit_code == EXIT_OK
    project.ok("init", session="corrupt")
    project.write_artifact(".specify/memory/constitution.md")
    before = frozen(project)

    (project.runtime / "governance.json").write_text(
        corruption, encoding="utf-8", newline="\n")

    result = project.run("advance", "--to", "gate_constitution")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "governance_record_invalid", result
    assert frozen(project) == before
