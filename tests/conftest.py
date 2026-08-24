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
    """A scratch project with its own copy of the skill files.

    ``workitem`` is the WorkItem the runtime resolves to. ``None`` means the
    transitional legacy layout (``.workflow/``); everything else resolves under
    ``workitems/<id>/.sdle/``. Tests read ``runtime`` rather than a literal, so
    a later phase moves one property, not fourteen call sites.
    """

    def __init__(self, root: Path, skill_root: Path, workitem: str | None = None,
                 pin: bool = False):
        self.root = root
        self.skill_root = skill_root
        self.workitem = workitem
        # `pin` puts `--workitem <id>` on every invocation. Off by default so
        # the rest of the suite exercises the resolution ladder rather than
        # bypassing it; on for the isolation tests, which need two WorkItems
        # addressable in one repository.
        self.pin = pin

    def as_workitem(self, workitem: str) -> "Project":
        """A pinned view of the same repository bound to another WorkItem."""
        return Project(self.root, self.skill_root, workitem, pin=True)

    # -- invocation ------------------------------------------------------

    def _argv(self, args, session: str | None) -> list[str]:
        argv = ["--project-root", str(self.root), "--skill-root", str(self.skill_root)]
        if self.pin and self.workitem:
            argv += ["--workitem", self.workitem]
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
    def runtime(self) -> Path:
        if self.workitem is None:
            return self.root / ".workflow"
        return self.root / "workitems" / self.workitem / ".sdle"

    @property
    def specs_root(self) -> Path:
        """This WorkItem's Spec Kit feature directories (v1.15)."""
        return self.root / "workitems" / self.workitem / "specs"

    def feature_dir(self, feature_id: str) -> str:
        """The repo-relative feature directory for ``feature_id``."""
        return f"workitems/{self.workitem}/specs/{feature_id}"

    @property
    def state_file(self) -> Path:
        return self.runtime / "state.json"

    @property
    def audit_file(self) -> Path:
        return self.runtime / "audit.md"

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
        # Mirrors the shipped .gitignore: the legacy runtime is ignored whole,
        # but WorkItem records are versioned — only the lock and the
        # developer-local active context are ignored.
        (self.root / ".gitignore").write_text(
            ".workflow/\nworkitems/*/.sdle/lock\n"
            "workitems/.active-context.json\n",
            encoding="utf-8",
        )
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "fixture baseline")


FEATURE_ID = "001-todo-api"
FIXTURE_WORKITEM_NAME = "Fixture WorkItem"
FIXTURE_WORKITEM_ID = "fixture-workitem"


@pytest.fixture(autouse=True)
def isolated_git_identity(tmp_path, monkeypatch):
    """Never read — let alone assert — the developer's real Git identity.

    `git config user.name` succeeds outside a repository by falling back to the
    machine's global config. Without this isolation the null-identity cases
    would flake, and a real person's name and email would land in test output
    and in every scratch `audit.md`. Repository-local identity (what
    `git_project` sets) is unaffected.

    Introduced file-scoped at T01; promoted here at T02, which moves the audit
    path and adds execution-identity assertions. Promotion is safe: no
    assertion in this suite depends on the machine identity
    (`grep -n 'Actor' tests/*.py` finds nothing).
    """
    missing = tmp_path / "no-such-gitconfig"
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(missing))
    monkeypatch.setenv("GIT_CONFIG_SYSTEM", str(missing))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")


@pytest.fixture
def bare_project(tmp_path: Path) -> Project:
    """A fresh scratch project with **no** WorkItem registered.

    Runtime commands refuse `workitem_required` here — that is the point. Used
    by the resolution-ladder tests, which must construct their own state rather
    than inherit a fixture that could mask a resolution bug, and by the
    WorkItem-identity suite, which asserts exact registry contents.
    """
    root = tmp_path / "target"
    root.mkdir()

    skill_root = root / ".claude" / "skills" / "sdle"
    skill_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(SKILL_SRC, skill_root)

    # Mirror the documented install layout: the engine, the commands and the
    # hooks live outside the skill folder, so a fixture that only copies the
    # skill would not be a realistic install.
    shutil.copytree(REPO_ROOT / "scripts", root / "scripts")
    shutil.copytree(REPO_ROOT / ".claude" / "hooks", root / ".claude" / "hooks")
    shutil.copy(REPO_ROOT / ".claude" / "settings.json",
                root / ".claude" / "settings.json")

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
def project(bare_project: Project) -> Project:
    """A scratch project with exactly one registered WorkItem.

    T02 makes the runtime WorkItem-scoped, so every runtime command needs a
    resolved WorkItem. Registering exactly one lets the resolution ladder bind
    it at rung 2 with no `--workitem` flag anywhere in the suite. Tests that
    must observe resolution itself use `bare_project`.
    """
    bare_project.ok("workitem", "create", "--name", FIXTURE_WORKITEM_NAME)
    bare_project.workitem = FIXTURE_WORKITEM_ID
    return bare_project


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
