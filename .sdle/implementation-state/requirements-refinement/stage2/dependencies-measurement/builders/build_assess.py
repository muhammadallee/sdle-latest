"""Build the isolated prompt files for the dependencies-definition measurement.

Each run file is the Stage 1 draft assessor prompt with exactly one thing varied: the
definition of check 11, `dependencies`. Run files carry neutral names and the document
text only (no filename, no label), matching the Stage 1 dispatch discipline.
"""
import json
import pathlib
import random

ROOT = pathlib.Path(r"D:\Learning\AI\sdle-git-repo\sdle-latest")
SCRATCH = pathlib.Path(r"C:\Users\Ali\AppData\Local\Temp\claude\D--Learning-AI-sdle-git-repo-sdle-latest\c5166a49-2dcf-438b-94e9-b4951ca86f8d\scratchpad\assess2")
(SCRATCH / "runs").mkdir(parents=True, exist_ok=True)
(SCRATCH / "out").mkdir(parents=True, exist_ok=True)

draft = (ROOT / ".sdle/implementation-state/requirements-refinement/assessor-prompt-draft.md").read_text(encoding="utf-8")
prompt = draft.split("\n---\n", 1)[1].lstrip("\n")

OLD = prompt[prompt.index("11. `dependencies`"):prompt.index("12. `blocking_unknowns`")]
assert "enough detail to know what they are" in OLD

NEW = (
    "11. `dependencies` — does the document identify, specifically enough to tell which one is meant, each\n"
    "    external system, service or third party that the solution must integrate with, call, or run on\n"
    "    (for example an identity provider, a payment gateway, an existing internal service, or a shared\n"
    "    platform)? Technology that the solution itself chooses — a database product, framework, library or\n"
    "    ORM — is not an external dependency for this check: a requirements document may leave those choices\n"
    "    to the engineering constitution, and describing storage as, say, a relational store is not a\n"
    "    failure. A document that states it has no external dependencies, or that names none because none\n"
    "    exist, satisfies the check. Fail only when an external system the solution relies on is referred to\n"
    "    by category or vague phrase alone, so that a reader could not tell which system is meant.\n"
)

docs = {
    "todo": (ROOT / "tests/fixtures/requirements-quality/todo-api.md").read_text(encoding="utf-8"),
    "defdep": (ROOT / "tests/fixtures/requirements-quality/defect-dependencies.md").read_text(encoding="utf-8"),
    "clean": (ROOT / "tests/fixtures/requirements-quality/clean-baseline.md").read_text(encoding="utf-8"),
    "ord": (SCRATCH / "doc_ordinary.md").read_text(encoding="utf-8"),
    "vague": (SCRATCH / "doc_vague.md").read_text(encoding="utf-8"),
}

# (document, definition version, runs)
plan = [
    ("ord", "v1", 3), ("vague", "v1", 3), ("todo", "v2", 3),
    ("ord", "v2", 3), ("vague", "v2", 3), ("defdep", "v2", 3), ("clean", "v2", 3),
]

rng = random.Random(20261002)
manifest = []
n = 0
for doc, ver, runs in plan:
    body = prompt if ver == "v1" else prompt.replace(OLD, NEW)
    for run in range(1, runs + 1):
        n += 1
        token = "%04x" % rng.randrange(0x10000)
        name = f"q{token}.md"
        (SCRATCH / "runs" / name).write_text(body.replace("{{DOCUMENT_TEXT}}", docs[doc]), encoding="utf-8", newline="\n")
        manifest.append({"file": name, "doc": doc, "definition": ver, "run": run,
                         "out": f"a{token}.json"})
(SCRATCH / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
(SCRATCH / "definition_v2.txt").write_text(NEW, encoding="utf-8")
print(len(manifest), "run files; definition v2 words:", len(NEW.split()))
