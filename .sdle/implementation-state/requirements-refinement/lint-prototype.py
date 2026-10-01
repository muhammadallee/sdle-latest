"""Stage 1 scratchpad prototype of the section-3.3 deterministic requirements
lint. NOT production code - measures false-positive rate before any rule is
proposed as a floor. Standard library only, matching the engine's own
constraint.
"""
import re
import sys
from pathlib import Path

VAGUE_TERMS = [
    r"\bfast\b", r"\buser-friendly\b", r"\brobust\b", r"\bas appropriate\b",
    r"\betc\.", r"\band/or\b", r"\bsome\b", r"\bseveral\b", r"\bappropriate\b",
    r"\bconvenient\b", r"\bsimple\b", r"\beasy to use\b",
]
UNRESOLVED = [r"\bTBD\b", r"\?\?\?"]  # TODO handled separately, case-sensitive
UNRESOLVED_CASE_SENSITIVE = [r"\bTODO\b"]
QUANT_ATTR = re.compile(
    r"\b(performance|latency|throughput|capacity|availability|scalab\w+)\b",
    re.IGNORECASE)
HAS_NUMBER_UNIT = re.compile(r"\d+\s?(ms|s|sec|seconds?|minutes?|req(uests)?/s|%|MB|GB|users?|items?)",
                              re.IGNORECASE)


def check_unresolved_markers(text: str) -> list[str]:
    hits = []
    for pat in UNRESOLVED:
        for m in re.finditer(pat, text, re.IGNORECASE):
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"blocking_unknowns: line {line}: unresolved marker {m.group()!r}")
    for pat in UNRESOLVED_CASE_SENSITIVE:
        for m in re.finditer(pat, text):  # case-sensitive: real product nouns (todo/Todo) must not match
            line = text.count("\n", 0, m.start()) + 1
            hits.append(f"blocking_unknowns: line {line}: unresolved marker {m.group()!r}")
    return hits


def check_vague_terms(text: str) -> list[str]:
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for pat in VAGUE_TERMS:
            if re.search(pat, line, re.IGNORECASE):
                hits.append(f"ambiguity: line {line_no}: vague term matching {pat!r} in: {line.strip()[:80]!r}")
    return hits


def check_missing_sections(text: str) -> list[str]:
    hits = []
    lower = text.lower()
    if "## acceptance" not in lower and "# acceptance" not in lower:
        hits.append("acceptance_criteria: no Acceptance section found")
    if "out of scope" not in lower:
        hits.append("out_of_scope: no 'out of scope' text found")
    return hits


def check_quant_nfrs_without_measure(text: str) -> list[str]:
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if QUANT_ATTR.search(line) and not HAS_NUMBER_UNIT.search(line):
            hits.append(f"nfrs: line {line_no}: quantitative attribute with no number/unit: {line.strip()[:80]!r}")
    return hits


OBSERVABLE_OUTCOME_HINTS = re.compile(
    r"\b(returns?|responds?|succeeds?|fails?|must (be|equal|return|reject|accept)|"
    r"is rejected|is accepted|behaves? as|is consistent|is enforced|passes|"
    r"status \d|error|exit \d|refuses?)\b", re.IGNORECASE)
STABLE_ID_PATTERN = re.compile(r"^\s*(?:[-*]\s*)?(?:AC[-\s]?\d+|[A-Z]+-\d+|\d+\.)\s", re.MULTILINE)


def check_acceptance_criteria_quality(text: str) -> list[str]:
    """Heuristic only: does the Acceptance section (however titled) contain
    at least one criterion with either a stable id or an observable-outcome
    verb? Fires once for the section, not per-line - a single prose
    paragraph with a clear outcome must not be flagged for lacking an id
    (no format is mandated)."""
    hits = []
    m = re.search(r"(?im)^#+\s*Acceptance.*?$(.*?)(?=^#+\s|\Z)", text, re.DOTALL | re.MULTILINE)
    if not m:
        return hits  # missing-section rule already covers this case
    section = m.group(1)
    has_id = bool(STABLE_ID_PATTERN.search(section))
    has_outcome = bool(OBSERVABLE_OUTCOME_HINTS.search(section))
    if not has_id and not has_outcome:
        hits.append("acceptance_criteria: Acceptance section has no stable id and no observable outcome")
    return hits


def check_duplicate_ids(text: str, other_texts: dict[str, str] | None = None) -> list[str]:
    """Duplicate requirement/criterion ids within one document, and (if
    other_texts given) across bound documents."""
    hits = []
    ids = re.findall(r"\b(AC-\d+|REQ-\d+|[A-Z]{2,}-\d+)\b", text)
    seen = set()
    for i in ids:
        if i in seen:
            hits.append(f"contradictions: duplicate id {i!r} within this document")
        seen.add(i)
    if other_texts:
        for other_path, other_text in other_texts.items():
            other_ids = set(re.findall(r"\b(AC-\d+|REQ-\d+|[A-Z]{2,}-\d+)\b", other_text))
            for dup in seen & other_ids:
                hits.append(f"contradictions: id {dup!r} duplicated in {other_path}")
    return hits


def lint(text: str, other_texts: dict[str, str] | None = None) -> dict[str, list[str]]:
    all_hits = (check_unresolved_markers(text) + check_vague_terms(text)
                + check_missing_sections(text) + check_quant_nfrs_without_measure(text)
                + check_acceptance_criteria_quality(text)
                + check_duplicate_ids(text, other_texts))
    by_check: dict[str, list[str]] = {}
    for h in all_hits:
        check_id = h.split(":", 1)[0]
        by_check.setdefault(check_id, []).append(h)
    return by_check


if __name__ == "__main__":
    for path in sys.argv[1:]:
        text = Path(path).read_text(encoding="utf-8")
        findings = lint(text)
        print(f"=== {path} ===")
        if not findings:
            print("  (clean)")
        for check_id, hits in findings.items():
            print(f"  [{check_id}] {len(hits)} finding(s)")
            for h in hits[:5]:
                print(f"    - {h}")
