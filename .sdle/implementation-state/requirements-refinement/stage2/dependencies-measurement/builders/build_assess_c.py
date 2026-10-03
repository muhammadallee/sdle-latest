"""Measure the amended sample: (a) explicit dependencies statement only, (b) that plus the
`updated_at` contradiction resolved. Scratch copies only; nothing in the repo is edited."""
import json
import pathlib
import random

ROOT = pathlib.Path(r"D:\Learning\AI\sdle-git-repo\sdle-latest")
S = pathlib.Path(r"C:\Users\Ali\AppData\Local\Temp\claude\D--Learning-AI-sdle-git-repo-sdle-latest\c5166a49-2dcf-438b-94e9-b4951ca86f8d\scratchpad\assess2")
draft = (ROOT / ".sdle/implementation-state/requirements-refinement/assessor-prompt-draft.md").read_text(encoding="utf-8")
prompt_v1 = draft.split("\n---\n", 1)[1].lstrip("\n")
OLD = prompt_v1[prompt_v1.index("11. `dependencies`"):prompt_v1.index("12. `blocking_unknowns`")]
prompt_v2 = prompt_v1.replace(OLD, (S / "definition_v2.txt").read_text(encoding="utf-8"))

orig = (ROOT / "tests/fixtures/requirements-quality/todo-api.md").read_text(encoding="utf-8")

DEPS = (
    "## Dependencies\n\n"
    "- None external. The service calls no other service and uses no third-party API.\n"
    "- Persistence is a relational store. Which product and version is an engineering choice recorded in\n"
    "  the project constitution, not a requirement of this document.\n\n"
)
anchor = "## Non-Functional Constraints"
assert orig.count(anchor) == 1
with_deps = orig.replace(anchor, DEPS + anchor)

old_line = "| `updated_at` | timestamp | Server-assigned, UTC, updated on every write |"
new_line = "| `updated_at` | timestamp | Server-assigned, UTC, updated whenever a write modifies a field |"
assert orig.count(old_line) == 1
both = with_deps.replace(old_line, new_line)

(S / "todo_with_deps.md").write_text(with_deps, encoding="utf-8", newline="\n")
(S / "todo_both.md").write_text(both, encoding="utf-8", newline="\n")

manifest = json.loads((S / "manifest.json").read_text(encoding="utf-8"))
rng = random.Random(20261004)
plan = [("todo_deps", with_deps, "v1"), ("todo_deps", with_deps, "v2"), ("todo_both", both, "v2")]
new = []
for doc, text, ver in plan:
    body = prompt_v1 if ver == "v1" else prompt_v2
    for run in (1, 2, 3):
        token = "%04x" % rng.randrange(0x10000)
        name = f"q{token}.md"
        (S / "runs" / name).write_text(body.replace("{{DOCUMENT_TEXT}}", text), encoding="utf-8", newline="\n")
        entry = {"file": name, "doc": doc, "definition": ver, "run": run, "out": f"a{token}.json"}
        manifest.append(entry)
        new.append(entry)
(S / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print(" ".join(e["file"][1:-3] for e in new))
