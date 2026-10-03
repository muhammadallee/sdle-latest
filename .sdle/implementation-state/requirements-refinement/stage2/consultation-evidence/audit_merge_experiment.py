"""SCRATCH — not part of the suite; deleted after the run.

Reproduces (or refutes) the hazard in decision C1: a refinement loop appending an audit entry to *another*
WorkItem's versioned, hash-chained audit.md, while that WorkItem's owner appends to it on their own branch.
"""
import re

from conftest import Project  # noqa: F401  (fixtures come from conftest)


def _append(view, message):
    return view.ok("audit", "append", "--phase", view.state()["current_phase"],
                   "--event", "scratch_note", "--message", message)


def test_two_writers_on_one_audit_chain(started):
    started.init_git()
    base = started.git("branch", "--show-current").stdout.strip()
    print("\nbase branch:", base)
    print("verify at baseline:", started.run("audit", "verify").exit_code)

    # "Person A": a refinement loop writes a cross-WorkItem acknowledgement into this WorkItem's audit.
    started.git("checkout", "-q", "-b", "person_a")
    _append(started, "ACK from another WorkItem's refinement loop")
    started.git("add", "-A")
    started.git("commit", "-q", "-m", "A: cross-WorkItem audit entry")
    print("verify on A:", started.run("audit", "verify").exit_code)

    # "Person B": the owner of this WorkItem keeps working on their own branch.
    started.git("checkout", "-q", base)
    started.git("checkout", "-q", "-b", "person_b")
    _append(started, "the owner's own audit entry")
    started.git("add", "-A")
    started.git("commit", "-q", "-m", "B: owner's audit entry")
    print("verify on B:", started.run("audit", "verify").exit_code)

    merged = started.git("merge", "--no-edit", "person_a")
    print("merge exit code:", merged.returncode)
    conflicted = started.git("diff", "--name-only", "--diff-filter=U").stdout.split()
    print("conflicted files:", conflicted)
    assert merged.returncode != 0 and conflicted, "expected a merge conflict"

    # The most generous hand resolution: keep BOTH appended entries, drop the markers, and keep one state.json.
    for name in conflicted:
        path = started.root / name
        text = path.read_text(encoding="utf-8")
        if name.endswith("audit.md"):
            text = "".join(line for line in text.splitlines(keepends=True)
                           if not re.match(r"^(<<<<<<<|=======|>>>>>>>)", line))
            path.write_text(text, encoding="utf-8", newline="")
        else:  # state.json: take B's side
            started.git("checkout", "--ours", name)
        started.git("add", name)
    started.git("commit", "-q", "--no-edit")

    result = started.run("audit", "verify")
    print("verify after the hand-resolved merge: exit", result.exit_code, "| reason", result.reason)
    print("data:", {k: v for k, v in (result.data or {}).items() if k in ("verified", "broken_at", "entries", "ok")})
