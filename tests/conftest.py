"""Shared fixtures for the SDLE suite.

Two rules hold everywhere in this suite:

1. **Fixtures are generated at runtime, never read from the repo.** Hashing a
   checked-in file makes results depend on the checkout's line endings, which
   differ between ubuntu-latest and windows-latest.
2. **SpecKit is never invoked.** Generation steps are simulated by writing a
   plausible artifact of at least the minimum size; what the tests assert is
   the sequence of state values, audit entries and refusals.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SDLE_PY = REPO_ROOT / "scripts" / "sdle.py"
SKILL_SRC = REPO_ROOT / ".claude" / "skills" / "sdle"


def _load_sdle():
    """Import sdle.py once, by path.

    Invoking in-process rather than spawning an interpreter per call keeps the
    suite usable: a full workflow run is ~25 invocations, and process startup
    on Windows dominates everything else. `main()` returns the same exit code
    the CLI would, so the contract under test is unchanged. The genuine CLI
    boundary (argv parsing, tracebacks escaping) is covered separately by the
    subprocess-based tests in test_units_cli.py.
    """
    spec = importlib.util.spec_from_file_location("sdle_under_test", SDLE_PY)
    module = importlib.util.module_from_spec(spec)
    # Register before executing: @dataclass resolves its own module by name.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sdle = _load_sdle()


class Result:
    """One sdle.py invocation: exit code, parsed stdout envelope, stderr."""

    def __init__(self, exit_code: int, stdout: str, stderr: str):
        self.exit_code = exit_code
        self.stderr = stderr
        self.stdout = stdout
        try:
            self.envelope = json.loads(stdout)
        except json.JSONDecodeError:
            self.envelope = {}

    @classmethod
    def from_completed(cls, completed: subprocess.CompletedProcess) -> "Result":
        return cls(completed.returncode, completed.stdout, completed.stderr)

    @property
    def ok(self) -> bool:
        return bool(self.envelope.get("ok"))

    @property
    def reason(self) -> str | None:
        return self.envelope.get("reason")

    @property
    def data(self) -> dict:
        return self.envelope.get("data") or {}

    def __repr__(self) -> str:
        return (
            f"<Result exit={self.exit_code} ok={self.ok} "
            f"reason={self.reason!r} data={self.data!r}>"
        )


class Project:
    """A scratch project with its own copy of the skill files."""

    def __init__(self, root: Path, skill_root: Path):
        self.root = root
        self.skill_root = skill_root

    # -- invocation ------------------------------------------------------

    def _argv(self, args, session: str | None) -> list[str]:
        argv = ["--project-root", str(self.root), "--skill-root", str(self.skill_root)]
        if session:
            argv += ["--session", session]
        return argv + [str(a) for a in args]

    def run(self, *args: str, session: str | None = None) -> Result:
        """Invoke in-process. `main()` returns the CLI's exit code."""
        out, err = io.StringIO(), io.StringIO()
        argv = self._argv(args, session)
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = sdle.main(argv)
        except SystemExit as exc:  # argparse usage errors
            code = exc.code if isinstance(exc.code, int) else 2
        return Result(code, out.getvalue(), err.getvalue())

    def run_cli(self, *args: str, session: str | None = None) -> Result:
        """Invoke through a real subprocess — for the CLI boundary itself."""
        command = [sys.executable, str(SDLE_PY), *self._argv(args, session)]
        return Result.from_completed(
            subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        )

    def ok(self, *args: str, session: str | None = None) -> Result:
        """Run and assert success — keeps happy-path setup terse."""
        result = self.run(*args, session=session)
        assert result.exit_code == 0, f"expected success, got {result}\n{result.stderr}"
        return result

    # -- state -----------------------------------------------------------

    @property
    def state_file(self) -> Path:
        return self.root / ".workflow" / "state.json"

    @property
    def audit_file(self) -> Path:
        return self.root / ".workflow" / "audit.md"

    def state(self) -> dict:
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def write_state(self, state: dict) -> None:
        self.state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")

    # -- artifact simulation ---------------------------------------------

    def write_artifact(self, relative: str, body: str | None = None) -> Path:
        """Stand in for a generation step. Always clears the size floor."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        text = body if body is not None else (
            f"# {Path(relative).stem}\n\n"
            + "Generated artifact body for tests. " * 6
            + "\n"
        )
        path.write_text(text, encoding="utf-8", newline="\n")
        assert path.stat().st_size >= 100, "test artifact must clear the size floor"
        return path

    def write_small(self, relative: str) -> Path:
        """A generation step that produced something unusable."""
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("too small\n", encoding="utf-8", newline="\n")
        return path

    # -- git -------------------------------------------------------------

    def git(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            cwd=str(self.root),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def init_git(self) -> None:
        self.git("init", "-q")
        self.git("config", "user.name", "SDLE Test")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.root / ".gitignore").write_text(".workflow/\n", encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "fixture baseline")


@pytest.fixture
def project(tmp_path: Path) -> Project:
    """A fresh scratch project: requirements present, SpecKit present."""
    root = tmp_path / "target"
    root.mkdir()

    skill_root = root / ".claude" / "skills" / "sdle"
    skill_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL_SRC, skill_root)

    (root / "requirements").mkdir()
    (root / "requirements" / "todo-api.md").write_text(
        "# Todo List REST API\n\n"
        "A small REST API for managing personal todo items.\n\n"
        "## Endpoints\n\n- POST /todos\n- GET /todos\n- DELETE /todos/{id}\n",
        encoding="utf-8",
        newline="\n",
    )

    # SpecKit's footprint, without SpecKit.
    (root / ".specify" / "memory").mkdir(parents=True)
    (root / ".claude" / "skills" / "speckit-constitution").mkdir(parents=True)
    (root / ".claude" / "skills" / "speckit-constitution" / "SKILL.md").write_text(
        "stub\n", encoding="utf-8"
    )

    return Project(root, skill_root)


@pytest.fixture
def started(project: Project) -> Project:
    """A project with an initialised workflow, sitting at constitution_draft."""
    project.ok("init", session="testsess")
    return project


@pytest.fixture
def git_project(project: Project) -> Project:
    """A scratch project under git, for diff, staleness and dirty-tree paths.

    The workflow is NOT initialised — tests that drive a full run call `init`
    themselves so the bootstrap turn is part of what is asserted.
    """
    project.init_git()
    return project


@pytest.fixture
def started_git(project: Project) -> Project:
    """Git-backed and already initialised, sitting at constitution_draft."""
    project.init_git()
    project.ok("init", session="testsess")
    return project
