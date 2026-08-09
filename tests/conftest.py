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

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SDLE_PY = REPO_ROOT / "scripts" / "sdle.py"
SKILL_SRC = REPO_ROOT / ".claude" / "skills" / "sdle"


class Result:
    """One sdle.py invocation: exit code, parsed stdout envelope, stderr."""

    def __init__(self, completed: subprocess.CompletedProcess):
        self.exit_code = completed.returncode
        self.stderr = completed.stderr
        self.stdout = completed.stdout
        try:
            self.envelope = json.loads(completed.stdout)
        except json.JSONDecodeError:
            self.envelope = {}

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

    def run(self, *args: str, session: str | None = None) -> Result:
        command = [
            sys.executable,
            str(SDLE_PY),
            "--project-root",
            str(self.root),
            "--skill-root",
            str(self.skill_root),
        ]
        if session:
            command += ["--session", session]
        command += [str(a) for a in args]
        completed = subprocess.run(
            command, capture_output=True, text=True, encoding="utf-8"
        )
        return Result(completed)

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
