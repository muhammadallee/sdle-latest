"""Add control runs: todo-api.md under the ORIGINAL definition, by the file-read method."""
import json
import pathlib
import random

ROOT = pathlib.Path(r"D:\Learning\AI\sdle-git-repo\sdle-latest")
S = pathlib.Path(r"C:\Users\Ali\AppData\Local\Temp\claude\D--Learning-AI-sdle-git-repo-sdle-latest\c5166a49-2dcf-438b-94e9-b4951ca86f8d\scratchpad\assess2")
draft = (ROOT / ".sdle/implementation-state/requirements-refinement/assessor-prompt-draft.md").read_text(encoding="utf-8")
prompt = draft.split("\n---\n", 1)[1].lstrip("\n")
doc = (ROOT / "tests/fixtures/requirements-quality/todo-api.md").read_text(encoding="utf-8")
manifest = json.loads((S / "manifest.json").read_text(encoding="utf-8"))
rng = random.Random(20261003)
new = []
for run in (1, 2, 3):
    token = "%04x" % rng.randrange(0x10000)
    name = f"q{token}.md"
    (S / "runs" / name).write_text(prompt.replace("{{DOCUMENT_TEXT}}", doc), encoding="utf-8", newline="\n")
    entry = {"file": name, "doc": "todo", "definition": "v1", "run": run, "out": f"a{token}.json"}
    manifest.append(entry)
    new.append(entry)
(S / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
print(" ".join(e["file"][1:-3] for e in new))
