#!/usr/bin/env python3
"""Recompute assessor precision/recall/agreement from runs/assessor-*.json and labels.json.

Run from anywhere; paths are relative to this file's own directory.
Excludes *-superseded.json and the non-assessor timestamped bookkeeping files from earlier
Stage 0 review rounds (those don't match the assessor-<check_id>-run<n>.json shape).
"""
import json
import re
import sys
from pathlib import Path
from collections import defaultdict

HERE = Path(__file__).resolve().parent
LABELS_PATH = HERE.parent / "labels.json"

CHECKS = [
    "problem_statement", "scope", "out_of_scope", "acceptance_criteria",
    "ambiguity", "contradictions", "constraints", "nfrs",
    "security_data_implications", "compatibility", "dependencies", "blocking_unknowns",
]

RUN_FILE_RE = re.compile(r"^assessor-(?P<check>[a-z_]+)-run(?P<n>\d+)\.json$")


def load_labels():
    labels = json.loads(LABELS_PATH.read_text(encoding="utf-8"))
    labels.pop("_notes", None)
    undetermined = set(labels.pop("_undetermined", []))
    # doc filename (e.g. "defect-scope.md") -> set of check ids that should FAIL
    return {doc: set(checks) for doc, checks in labels.items()}, undetermined


def load_runs():
    runs = []
    for f in sorted(HERE.glob("assessor-*.json")):
        if f.name.endswith("-superseded.json"):
            continue
        m = RUN_FILE_RE.match(f.name)
        if not m:
            continue  # not an assessor run file (shouldn't happen given the glob, but be safe)
        data = json.loads(f.read_text(encoding="utf-8"))
        runs.append({
            "file": f.name,
            "check_slug": m.group("check"),
            "run_n": int(m.group("n")),
            "document": data["document"],
            "result": data["result"],
        })
    return runs


def doc_key_for_slug(slug):
    # filenames use "clean_baseline" but the doc is "clean-baseline.md"
    if slug == "clean_baseline":
        return "clean-baseline.md"
    return f"defect-{slug}.md"


# document#run tags whose contradictions FAIL is attributable to the shared corpus template's
# 301-redirect / Cache-Control:no-store tension, not to the document's own labeled defect.
# See LEDGER.md. Excluded only in the "excluding known template tension" contradictions row.
KNOWN_TEMPLATE_TENSION_FPS = {
    ("contradictions", "defect-blocking_unknowns.md"),
    ("contradictions", "defect-constraints.md"),
}


def main():
    labels, undetermined = load_labels()
    runs = load_runs()

    # Group runs by document
    by_doc = defaultdict(list)
    for r in runs:
        by_doc[r["document"]].append(r)

    missing_docs = set(labels) - set(by_doc)
    if missing_docs:
        print(f"WARNING: no runs found for labeled documents: {sorted(missing_docs)}", file=sys.stderr)

    # Per-check confusion counts. Also a template-tension-excluded variant for contradictions.
    stats = {c: {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "fp_detail": [], "fp_excl_template": 0} for c in CHECKS}
    undetermined_report = defaultdict(lambda: {"tp": 0, "fn": 0})

    for doc, doc_runs in sorted(by_doc.items()):
        positive_checks = labels.get(doc, set())
        for r in doc_runs:
            result = r["result"]
            for check in CHECKS:
                verdict = result[check]["result"]
                is_fail = verdict == "FAIL"
                is_positive = check in positive_checks

                if doc in undetermined and check in positive_checks:
                    # this document's own labeled defect is not a settled positive/negative call -
                    # report separately, don't fold into the main table
                    if is_fail:
                        undetermined_report[(doc, check)]["tp"] += 1
                    else:
                        undetermined_report[(doc, check)]["fn"] += 1
                    continue

                if is_positive and is_fail:
                    stats[check]["tp"] += 1
                elif is_positive and not is_fail:
                    stats[check]["fn"] += 1
                elif not is_positive and is_fail:
                    stats[check]["fp"] += 1
                    stats[check]["fp_detail"].append(f"{doc}#run{r['run_n']}")
                    if (check, doc) not in KNOWN_TEMPLATE_TENSION_FPS:
                        stats[check]["fp_excl_template"] += 1
                else:
                    stats[check]["tn"] += 1

    print("Main table (excludes each _undetermined document's OWN labeled check - see below):")
    print("| check | positive instances | TP | FN | FP | Recall | Precision |")
    print("|---|---|---|---|---|---|---|")
    for check in CHECKS:
        s = stats[check]
        pos = s["tp"] + s["fn"]
        recall = f"{s['tp']/pos:.2f}" if pos else "n/a"
        precision = f"{s['tp']/(s['tp']+s['fp']):.2f}" if (s["tp"] + s["fp"]) else "undefined"
        print(f"| {check} | {pos} | {s['tp']} | {s['fn']} | {s['fp']} | {recall} | {precision} |")

    print()
    print("contradictions, excluding the known shared-template 301/no-store tension FPs:")
    s = stats["contradictions"]
    fp_excl = s["fp_excl_template"]
    precision_excl = f"{s['tp']/(s['tp']+fp_excl):.2f}" if (s["tp"] + fp_excl) else "undefined"
    print(f"  raw: FP={s['fp']}, precision={s['tp']/(s['tp']+s['fp']):.2f}" if (s['tp']+s['fp']) else "  raw: undefined")
    print(f"  excluding template tension: FP={fp_excl}, precision={precision_excl}")

    print()
    print("Undetermined documents (own labeled check reported separately, not scored):")
    for (doc, check), counts in sorted(undetermined_report.items()):
        n = counts["tp"] + counts["fn"]
        print(f"  {doc} / {check}: caught {counts['tp']}/{n} runs")

    print()
    print("False positives by check (document#run):")
    for check in CHECKS:
        if stats[check]["fp_detail"]:
            print(f"  {check}: {stats[check]['fp_detail']}")

    print()
    print("Agreement rate (byte-identical 12-key verdict vector across all runs of a document):")
    agree_count = 0
    total_docs = 0
    for doc, doc_runs in sorted(by_doc.items()):
        total_docs += 1
        vectors = [json.dumps({c: r["result"][c]["result"] for c in CHECKS}, sort_keys=True) for r in doc_runs]
        agrees = len(set(vectors)) == 1
        if agrees:
            agree_count += 1
        print(f"  {doc}: {'AGREE' if agrees else 'DISAGREE'} ({len(doc_runs)} runs)")
    print(f"Agreement: {agree_count}/{total_docs} ({agree_count/total_docs*100:.0f}%)")

    print()
    print("Document-level blocking (any check FAIL, labeled or not - what the loop actually acts on):")
    for doc, doc_runs in sorted(by_doc.items()):
        blocked_counts = []
        for r in doc_runs:
            failing = [c for c in CHECKS if r["result"][c]["result"] == "FAIL"]
            blocked_counts.append(len(failing) > 0)
        n_blocked = sum(blocked_counts)
        print(f"  {doc}: blocked in {n_blocked}/{len(doc_runs)} runs")


if __name__ == "__main__":
    main()
