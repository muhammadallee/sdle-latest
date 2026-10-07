"""A package-bound WorkItem driven through GREENFIELD with chosen spec and
tasks text (ADR-017). Generated at runtime; nothing here invokes Spec Kit.
"""
from __future__ import annotations

import sys

from conftest import PASSING_TEST_COMMAND, _command_line
from package_support import import_package
from test_units_artifact_review import review_for_gate
from test_units_flow_model import FEATURE, constants_of, prepare
from test_units_package_approval import approved_and_assessed

PAD = "\n" + "Padding so the artifact clears the size floor. " * 4 + "\n"

FULL_SPEC = ("# Specification\n\n- FR-001 A clerk creates an order.\n"
             "- AC-001 Creating an order returns its number.\n"
             "- NFR-001 Creation completes within two seconds.\n" + PAD)
FULL_TASKS = (
    "# Tasks\n\n"
    "- [ ] T001 Implement FR-001 and NFR-001 in the order service\n"
    "- [ ] T002 Test AC-001: creating an order returns its number\n" + PAD)


def package_view(project):
    """A package WorkItem approved, assessed and started."""
    view = approved_and_assessed(project)
    view.ok("init", session="trace")
    return view


def walk(view, stop: str, *, spec: str | None = FULL_SPEC,
         tasks: str | None = FULL_TASKS, omit_tasks_gate: bool = False,
         start: str | None = None) -> None:
    """Drive from `constitution_draft` to the phase `stop`, leaving the
    WorkItem standing there. Gates are approved with a PASS review of the
    kind the engine's table names."""
    consts = constants_of(view)
    phases = list(consts.flow("GREENFIELD").phases)
    feature_dir = view.feature_dir(FEATURE)
    first = phases.index(start) if start else 1
    for index in range(first, len(phases) - 1):
        phase = phases[index]
        if phase == stop:
            return
        if phase == "spec_draft" and spec is not None:
            view.write_artifact(f"{feature_dir}/spec.md", spec)
            view.ok("feature", "resolve")
        elif phase == "tasks_draft" and tasks is not None:
            view.write_artifact(f"{feature_dir}/tasks.md", tasks)
        elif phase == "analyze":
            pass  # read-only
        else:
            prepare(view, phase, feature_dir)
        gate = consts.phase_to_gate_key.get(phase)
        if gate == "gate_tasks" and omit_tasks_gate:
            review_for_gate(view, gate)
            view.ok("gate", "omit", "--gate", gate)
        elif gate:
            review_for_gate(view, gate)
            view.ok("gate", "approve", "--gate", gate)
        else:
            view.ok("advance", "--to", phases[index + 1])


def junit_xml(*cases: tuple[str, bool]) -> str:
    body = "".join(
        f'<testcase classname="suite" name="{n}">'
        + ("" if ok else '<failure message="boom"/>') + "</testcase>"
        for n, ok in cases)
    return f'<testsuite name="s">{body}</testsuite>'


def build_junit(view, *cases: tuple[str, bool], name: str = "results.xml",
                write_report: bool = True):
    """Rebuild the implementation evidence with the test command writing a
    JUnit report that `manifest build --junit` captures. The report goes under
    the WorkItem's evidence directory, which the tree digest excludes: a
    report left in the working tree would be a change to the tree the evidence
    was taken from."""
    path = view.runtime / "evidence" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    code = (f"open({str(path)!r}, 'w', encoding='utf-8')"
            f".write({junit_xml(*cases)!r})" if write_report else "pass")
    command = _command_line([sys.executable, "-c", code])
    relative = path.relative_to(view.root).as_posix()
    return view.ok("manifest", "build", "--summary", "Implemented.",
                   "--test-command", command, "--junit", relative), relative


def build(view, *extra: str):
    return view.ok("manifest", "build", "--summary", "Implemented.",
                   "--test-command", PASSING_TEST_COMMAND, *extra)
