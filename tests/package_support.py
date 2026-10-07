"""Fixtures for the requirements-package suites (ADR-016).

Generated at runtime, never read from the checkout: a checked-in file hashed
by the engine would make results depend on line endings. The digests here are
computed with hashlib directly, so a bug in the engine's own hashing cannot
hide behind a test that borrows it.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

SOURCE_PATH = "docs/source/srs.md"
SOURCE_TEXT = (
    "# Order Management SRS\n\n"
    "## 3.1 Orders\n\nThe system shall let a clerk create an order.\n\n"
    "## 3.2 Reports\n\nThe system shall list the orders placed in a month.\n"
)
PACKAGE_ID = "orders"


def sha_text(text: str) -> str:
    return hashlib.sha256(text.replace("\r\n", "\n").encode("utf-8")).hexdigest()


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def base_document(source_sha: str) -> dict:
    return {
        "packageVersion": "1",
        "packageId": PACKAGE_ID,
        "title": "Order management",
        "sources": [{"path": SOURCE_PATH, "sha256": source_sha,
                     "statedVersion": "v1.0 2026-09-01"}],
        "idGrammar": {
            "requirement": "(?:FR|AC)-[0-9]{3}",
            "nonFunctional": "NFR-[0-9]{3}",
            "workItem": "WI-[0-9]{3}",
            "issue": "OI-[0-9]{3}",
        },
        "files": [],
        "workItems": [
            {"id": "WI-001", "slug": "orders", "readiness": "READY",
             "file": "work-items/WI-001-orders/requirements.md",
             "sharedFiles": ["system-context.md"]},
            {"id": "WI-002", "slug": "reports", "readiness": "NOT_READY",
             "file": "work-items/WI-002-reports/requirements.md",
             "sharedFiles": []},
        ],
        "requirements": [
            {"id": "FR-001", "kind": "functional", "status": "confirmed",
             "statement": "A clerk can create an order.",
             "source": {"document": SOURCE_PATH, "anchor": "3.1"},
             "workItem": "WI-001"},
            {"id": "AC-001", "kind": "acceptance_criterion",
             "status": "confirmed",
             "statement": "Creating an order returns its number.",
             "source": {"document": SOURCE_PATH, "anchor": "3.1"},
             "workItem": "WI-001"},
            {"id": "NFR-001", "kind": "nfr", "status": "confirmed",
             "statement": "Order creation completes within two seconds.",
             "clarification": {"ref": "CL-2026-09-14 with the product owner"},
             "workItem": "WI-001"},
            {"id": "FR-002", "kind": "functional", "status": "draft",
             "statement": "A manager can list a month's orders.",
             "source": {"document": SOURCE_PATH, "anchor": "3.2"},
             "workItem": "WI-002"},
            {"id": "AC-002", "kind": "acceptance_criterion",
             "status": "draft",
             "statement": "The list shows every order of the month.",
             "source": {"document": SOURCE_PATH, "anchor": "3.2"},
             "workItem": "WI-002"},
            {"id": "FR-003", "kind": "functional", "status": "confirmed",
             "statement": "Orders are exported nightly.",
             "source": {"document": SOURCE_PATH, "anchor": "3.2"}},
        ],
        "exclusions": [
            {"requirementId": "FR-003", "disposition": "out of scope",
             "reason": "A later release; the owner confirmed on 2026-09-14."}],
        "retired": [],
        "openIssues": [
            {"id": "OI-001", "question": "Which month boundary applies?",
             "affects": ["WI-002"], "blocking": True, "disposition": "open"}],
        "obligationTags": {"principle": "PRN-[0-9]{2}",
                           "decision": "AD-[0-9]{3}"},
        "absentSupporting": [
            {"name": "access-control",
             "reason": "the source defines no roles beyond clerk and manager"}],
    }


def base_files() -> dict[str, str]:
    return {
        "overview.md": (
            "# Overview\n\nOrder management. Two work items: WI-001 and "
            "WI-002.\n\n## Supporting files not generated\n\n"
            "- access-control: the source defines no roles beyond clerk and "
            "manager.\n"),
        "traceability.md": (
            "# Traceability\n\n| ID | Work item |\n|---|---|\n"
            "| FR-001 | WI-001 |\n| AC-001 | WI-001 |\n| NFR-001 | WI-001 |\n"
            "| FR-002 | WI-002 |\n| AC-002 | WI-002 |\n"
            "| FR-003 | excluded |\n\nOpen: OI-001.\n"),
        "open-issues.md": "# Open issues\n\nOI-001: Which month boundary?\n",
        "system-context.md": "# System context\n\nA clerk works at a desk.\n",
        "work-items/WI-001-orders/requirements.md": (
            "# WI-001 Orders\n\nReadiness: READY\n\nFR-001, AC-001, NFR-001.\n"),
        "work-items/WI-002-reports/requirements.md": (
            "# WI-002 Reports\n\nReadiness: NOT READY (OI-001)\n\n"
            "FR-002, AC-002.\n"),
    }


ROLES = {
    "overview.md": "overview", "traceability.md": "traceability",
    "open-issues.md": "open-issues", "system-context.md": "supporting",
    "work-items/WI-001-orders/requirements.md": "work-item",
    "work-items/WI-002-reports/requirements.md": "work-item",
}


def write_source(project, text: str = SOURCE_TEXT) -> str:
    target = project.root / SOURCE_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    return sha_file(target)


def stage_package(project, mutate=None, *, package_id: str = PACKAGE_ID,
                  seal: bool = True) -> tuple[Path, dict]:
    """Draft a package in staging, the way the orchestrator would.

    `mutate(doc, files)` edits the manifest and file texts before they are
    written; `seal=False` writes the manifest's file digests as given, so a
    test can leave them wrong on purpose.
    """
    sha = write_source(project)
    doc = base_document(sha)
    doc["packageId"] = package_id
    files = base_files()
    if mutate:
        mutate(doc, files)
    if seal and not doc["files"]:
        doc["files"] = [{"path": rel, "role": ROLES.get(rel, "supporting"),
                         "sha256": sha_text(text)}
                        for rel, text in files.items()]
    staging = project.root / "package-staging" / package_id
    for rel, text in files.items():
        target = staging / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8", newline="\n")
    (staging / "package.json").write_text(
        json.dumps(doc, indent=2), encoding="utf-8", newline="\n")
    return staging, doc


def import_package(project, mutate=None, **kw):
    stage_package(project, mutate, **kw)
    result = project.run("package", "import", "--package",
                         kw.get("package_id", PACKAGE_ID))
    return result


def approve_package(project, package_id: str = PACKAGE_ID,
                    approver: str = "A. Architect"):
    return project.run(
        "package", "approve", "--package", package_id, "--approver", approver,
        "--role", "Solution Architect", "--wording", "approve")


def offender_rules(result) -> set[str]:
    return {o["rule"] for o in result.data.get("offenders", [])}


def edit_manifest(project, fn, package_id: str = PACKAGE_ID) -> None:
    """Edit the imported package.json in place (a hand edit the engine did
    not make) and re-write it. The file digests are left as they were."""
    target = project.root / "requirements" / "packages" / package_id / "package.json"
    doc = json.loads(target.read_text(encoding="utf-8"))
    fn(doc)
    target.write_text(json.dumps(doc, indent=2), encoding="utf-8", newline="\n")


def clone(doc: dict) -> dict:
    return copy.deepcopy(doc)
