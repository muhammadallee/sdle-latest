"""The advisory requirements lint.

Every rule declares what it applies to, and each is proven against a positive, a
negative and a neighbouring-kind fixture. Fixtures are built at runtime. The lint is
advisory: it records evidence and never decides anything.
"""

from __future__ import annotations

import ast
import hashlib
import inspect

import pytest

from conftest import sdle

lint = sdle.requirements_lint
CHECKS = sdle.QUALITY_CHECK_DEFINITIONS

CLEAN = """# Service

## Problem
Staff cannot see open orders.

## Acceptance Criteria
- AC-1: Listing orders returns status 200 and the open orders.
- AC-2: A request without a token is rejected with status 401.

## Out of Scope
Billing.
"""


def run(text, path="requirements/a.md", extra=None):
    docs = {path: text}
    docs.update(extra or {})
    return lint(docs, path, "exec-1")


def rules(evidence):
    return sorted(f["ruleId"] for f in evidence["findings"])


def test_the_spec_names_every_rule_with_its_scope():
    spec = sdle.REQUIREMENTS_LINT_RULES
    assert set(spec) == {
        "unresolved_marker", "vague_term", "missing_acceptance_section",
        "missing_out_of_scope_section", "acceptance_not_checkable",
        "quantity_without_measure", "duplicate_id"}
    for rule, row in spec.items():
        assert row["mappedCheck"] in CHECKS, rule
        assert isinstance(row["floorEligible"], bool), rule
        assert row["applies_to"].strip(), rule


def test_clean_document_has_no_findings_and_evidence_is_well_formed():
    evidence = run(CLEAN)
    assert evidence["findings"] == []
    assert sdle.refinement_lint_evidence_problems(evidence) == []
    assert evidence["kind"] == "refinement-lint" and evidence["executionId"] == "exec-1"
    normal = sdle.requirements_normal_form(CLEAN)
    assert evidence["documentSha256"] == hashlib.sha256(normal.encode()).hexdigest()


def test_no_finding_is_ever_enforced():
    bad = CLEAN + "\nThe system must be fast. TBD\n"
    findings = run(bad)["findings"]
    assert findings
    for finding in findings:
        assert finding["floorEnforced"] is False
    assert sdle.refinement_lint_evidence_problems(run(bad)) == []


# -- unresolved markers --------------------------------------------------------------------


@pytest.mark.parametrize("marker", ["TBD", "TODO", "???"])
def test_an_unresolved_marker_is_found_with_its_line(marker):
    text = CLEAN.replace("Billing.", f"Billing {marker}.")
    found = [f for f in run(text)["findings"] if f["ruleId"] == "unresolved_marker"]
    assert len(found) == 1 and found[0]["line"] == 11
    assert found[0]["mappedCheck"] == "blocking_unknowns"


def test_an_empty_section_is_an_unresolved_marker():
    text = CLEAN + "\n## Dependencies\n\n## Notes\nSome text here.\n"
    found = [f for f in run(text)["findings"] if f["ruleId"] == "unresolved_marker"]
    assert [f["line"] for f in found] == [13]


def test_markers_in_code_quotes_and_nouns_are_not_flagged():
    text = CLEAN + (
        "\nThe `TBD` token is stored.\n\n> TBD in a quotation\n\n"
        "```\nTODO in code\n```\n\nThe Todo and todo items list.\n")
    assert "unresolved_marker" not in rules(run(text))


# -- vague terms: normative text only ----------------------------------------------------------


def test_a_vague_term_in_a_normative_sentence_is_found():
    text = CLEAN + "\nThe system must be fast and robust.\n"
    found = [f for f in run(text)["findings"] if f["ruleId"] == "vague_term"]
    assert found and found[0]["mappedCheck"] == "ambiguity"


def test_a_vague_term_in_descriptive_text_code_or_quotation_is_not_flagged():
    text = CLEAN + (
        "\nStaff said some orders are slow, and the old tool was fast.\n\n"
        "> The system must be fast.\n\n`must be fast`\n\n"
        "```\nmust be robust\n```\n")
    assert "vague_term" not in rules(run(text))


def test_a_precise_normative_sentence_is_not_flagged():
    text = CLEAN + "\nThe system must reject a body larger than 1 MB with status 413.\n"
    assert "vague_term" not in rules(run(text))


# -- missing sections: a bound-set question ---------------------------------------------------------


def test_missing_sections_are_found_when_the_whole_set_lacks_them():
    text = "# Service\n\n## Problem\nStaff cannot see open orders.\n"
    assert {"missing_acceptance_section", "missing_out_of_scope_section"} <= set(rules(run(text)))


def test_a_section_in_another_bound_document_satisfies_the_set():
    first = "# Service\n\n## Problem\nStaff cannot see open orders.\n"
    second = "# Criteria\n\n## Acceptance\n- AC-1: returns status 200.\n\n## Non-goals\nBilling.\n"
    ev = run(first, "requirements/a.md", {"requirements/b.md": second})
    assert not {"missing_acceptance_section", "missing_out_of_scope_section"} & set(rules(ev))


def test_the_words_in_prose_are_not_a_section():
    text = "# S\n\n## Problem\nAcceptance is out of scope for now. It is out of scope.\n"
    found = rules(run(text))
    assert "missing_acceptance_section" in found
    assert "missing_out_of_scope_section" in found


# -- acceptance criteria: no format is mandated -----------------------------------------------------


def test_a_plain_sentence_criterion_with_an_outcome_is_valid():
    text = ("# S\n\n## Acceptance\nWhen a viewer asks for a missing order the service "
            "returns a not-found response.\n\n## Out of scope\nNone.\n")
    assert "acceptance_not_checkable" not in rules(run(text))


def test_given_when_then_without_ids_is_valid():
    text = ("# S\n\n## Acceptance\nGiven an empty list, when staff open it, then the service "
            "returns an empty page.\n\n## Out of scope\nNone.\n")
    assert "acceptance_not_checkable" not in rules(run(text))


def test_criteria_with_no_id_and_no_outcome_are_found():
    text = "# S\n\n## Acceptance\nIt should work well for everyone.\n\n## Out of scope\nNone.\n"
    assert "acceptance_not_checkable" in rules(run(text))


# -- quantity without a measure -----------------------------------------------------------------------------


def test_a_quantitative_attribute_without_a_measure_is_found():
    text = CLEAN + "\nThe service must offer good latency under load.\n"
    found = [f for f in run(text)["findings"] if f["ruleId"] == "quantity_without_measure"]
    assert found and found[0]["mappedCheck"] == "nfrs"


def test_a_quantitative_attribute_with_a_measure_is_not_found():
    text = CLEAN + "\nThe service must answer within 200 ms at the 95th percentile.\n"
    assert "quantity_without_measure" not in rules(run(text))


@pytest.mark.parametrize("sentence", [
    "All traffic must use TLS 1.2 or later.",
    "The service must comply with the data-retention policy.",
    "The client must support the two most recent major browser versions.",
    "Only authenticated staff may view orders.",
    "Availability of the audit log must follow the data-retention policy.",
])
def test_binary_and_categorical_requirements_are_never_flagged_for_lacking_a_number(sentence):
    assert "quantity_without_measure" not in rules(run(CLEAN + "\n" + sentence + "\n"))


# -- duplicate ids across the bound set ----------------------------------------------------------------------------


def test_an_id_defined_twice_across_documents_is_found_on_the_later_one():
    a = CLEAN
    b = "# More\n\n## Acceptance\n- AC-1: Deleting an order returns status 204.\n"
    ev_b = run(b, "requirements/b.md", {"requirements/a.md": a})
    found = [f for f in ev_b["findings"] if f["ruleId"] == "duplicate_id"]
    assert found and found[0]["mappedCheck"] == "contradictions"
    assert "duplicate_id" not in rules(run(a, "requirements/a.md", {"requirements/b.md": b}))


def test_an_id_defined_twice_in_one_document_is_found():
    text = CLEAN.replace("AC-2:", "AC-1:")
    assert "duplicate_id" in rules(run(text))


def test_a_reference_to_an_id_is_not_a_definition():
    text = CLEAN + "\nSee AC-1 and AC-2 above; AC-1 also governs listing.\n"
    assert "duplicate_id" not in rules(run(text))


# -- determinism and independence --------------------------------------------------------------------------------


def test_the_lint_is_deterministic():
    text = CLEAN + "\nThe system must be fast. TBD\n"
    assert run(text) == run(text)


def test_presentation_only_changes_do_not_change_the_findings():
    text = CLEAN + "\nThe system must be fast.\n"
    crlf = text.replace("\n", "\r\n")
    assert run(text)["findings"] == run(crlf)["findings"]
    assert run(text)["documentSha256"] == run(crlf)["documentSha256"]


# -- advisory only -------------------------------------------------------------------------------------------------------


def _names_used(function) -> set[str]:
    tree = ast.parse(inspect.getsource(function).lstrip())
    return ({n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            | {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)})


@pytest.mark.parametrize("name", [
    "cmd_governance_assess", "governance_precondition", "evaluate_quality",
    "governance_freshness"])
def test_nothing_on_the_assessment_path_reads_the_lint(name):
    used = _names_used(getattr(sdle, name))
    assert not {"requirements_lint", "REQUIREMENTS_LINT_RULES"} & used, name


def test_an_out_of_scope_label_inside_a_scope_section_satisfies_the_set():
    text = CLEAN.replace("## Out of Scope\nBilling.\n", "## Scope\nIn scope: orders.\n\nOut of scope: billing.\n")
    assert "missing_out_of_scope_section" not in rules(run(text))


# -- the measured corpus --------------------------------------------------------------------------

CORPUS = sdle.Path(__file__).resolve().parent / "fixtures" / "requirements-quality"


def _corpus(name):
    text = (CORPUS / name).read_text(encoding="utf-8")
    return lint({name: text}, name, "corpus")


@pytest.mark.parametrize("name", ["clean-baseline.md", "todo-api.md"])
def test_no_floor_eligible_rule_fires_on_a_clean_document(name):
    eligible = [f for f in _corpus(name)["findings"] if f["floorEligible"]]
    assert eligible == []


@pytest.mark.parametrize("name, rule", [
    ("defect-blocking_unknowns.md", "unresolved_marker"),
    ("defect-out_of_scope.md", "missing_out_of_scope_section"),
    ("defect-acceptance_criteria.md", "acceptance_not_checkable"),
    ("defect-ambiguity.md", "vague_term"),
])
def test_the_lint_finds_the_defect_it_is_built_for(name, rule):
    assert rule in rules(_corpus(name))
