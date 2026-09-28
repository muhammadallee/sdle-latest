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


def lint(text: str) -> dict[str, list[str]]:
    all_hits = (check_unresolved_markers(text) + check_vague_terms(text)
                + check_missing_sections(text) + check_quant_nfrs_without_measure(text))
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
