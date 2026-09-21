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
import os
import shlex
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

    # -- governance ------------------------------------------------------

    def record_governance(self, **over) -> "Result":
        """Record the contract §12 governance inputs the lifecycle requires.

        T06 makes `advance` refuse `governance_missing` without a recorded,
        passing, current assessment, so every driver that moves a phase
        records one first. The document is generated at runtime like every
        other fixture artifact, and the twelve check ids are read from the
        engine's own policy rather than restated (invariant 7).
        """
        document = {
            "governanceInputVersion": "1",
            "quality": {
                name: {"result": "PASS", "finding": None}
                for name in sdle.GOVERNANCE_POLICY_BUILTIN["quality_checks"]
            },
            # T07: at T06 this value was recorded and inert, so any member
            # of ENGINEERING_FLOWS was an equally valid fixture default.
            # It now selects the traversal, and `started` sits at
            # `constitution_draft` — a phase only GREENFIELD and
            # BROWNFIELD_DISCOVERY have. GREENFIELD is therefore the value
            # that keeps every existing assertion byte-identical.
            "classification": {"type": "enhancement", "flow": "GREENFIELD"},
            "risk": {"signals": [], "proposedLevel": "LOW",
                     "uncertainty": "LOW"},
        }
        document.update(over)
        name = "governance-input.json"
        target = self.root / name
        target.write_text(
            json.dumps(document, indent=2), encoding="utf-8", newline="\n"
        )
        try:
            return self.ok("governance", "assess", "--input", name)
        finally:
            # The proposal is a transient input, consumed by `assess` and
            # preserved verbatim in the evidence document. Leaving it behind
            # would make every git-backed fixture's working tree dirty and
            # would trip `implement preflight` — a fixture artifact, not
            # product behaviour. `SDLE_OWNED_PREFIXES` stays untouched.
            target.unlink()

    def establish_baseline(self, **over) -> dict:
        """Write `.sdle/baseline.json` through the engine's own builder.

        Deliberately not a second implementation of §14's schema: it calls
        `sdle.baseline_descriptor(...)` and overrides only what a test names,
        so no key, default or vocabulary is restated here. That is the
        discipline `record_governance` already follows by reading
        `sdle.GOVERNANCE_POLICY_BUILTIN` for the check ids.
        """
        paths = sdle.resolve_paths(str(self.root), str(self.skill_root))
        if self.workitem:
            paths = sdle.dataclass_replace(paths, workitem=self.workitem)
        consts = sdle.load_constants(paths)
        state = (self.state() if self.state_file.is_file()
                 else sdle.load_template(paths))
        state = dict(state)
        state.setdefault("flow", sdle.DEFAULT_FLOW)
        descriptor = sdle.baseline_descriptor(
            paths, state, consts, "fixture-execution", sdle.now_iso())
        descriptor.update(over)
        target = paths.baseline_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(descriptor, indent=2) + "\n",
                          encoding="utf-8", newline="\n")
        return descriptor

    def record_discovery(self, **over) -> "Result":
        """Record the contract §14 discovery findings BROWNFIELD_DISCOVERY
        requires before it can leave the `discovery` phase.

        One finding per category the engine declares, each in the *unknown*
        class — which is the honest answer here, because a scratch fixture has
        no repository to discover and §14 says to record that rather than
        invent something. Both the category list and the classification are
        read from the engine, never typed out, the same discipline
        `record_governance` follows for the twelve check ids (invariant 7).
        """
        unknown = sdle.DISCOVERY_CLASSIFICATIONS[-1]
        document = {
            "discoveryInputVersion": "1",
            "findings": [
                {
                    "id": f"F-{index:03d}",
                    "category": category,
                    "classification": unknown,
                    "statement": "This fixture repository records nothing "
                                 f"about {category}.",
                }
                for index, category in enumerate(sdle.DISCOVERY_CATEGORIES,
                                                 start=1)
            ],
        }
        document.update(over)
        name = "discovery-input.json"
        target = self.root / name
        target.write_text(
            json.dumps(document, indent=2), encoding="utf-8", newline="\n"
        )
        try:
            return self.ok("discovery", "assess", "--input", name)
        finally:
            # Transient, exactly like the governance proposal: consumed by
            # `assess`, preserved verbatim in the evidence document, and
            # removed so no git-backed fixture's working tree goes dirty.
            target.unlink()

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
    # ADR-012: a WorkItem declares the requirement documents it is about, and
    # every consumer from `preflight` onwards reads that binding. The real
    # lifecycle binds between `workitem create` and `preflight`, so the fixture
    # does too; tests that exercise the binding itself start from
    # `bare_project` and bind explicitly.
    bare_project.ok("requirements", "bind",
                    "--source", "requirements/todo-api.md")
    return bare_project


@pytest.fixture
def started(project: Project) -> Project:
    """A project with an initialised workflow, sitting at constitution_draft."""
    project.record_governance()
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
# ---------------------------------------------------------------------------
# Retired wording in the dry-run transcripts
# ---------------------------------------------------------------------------
#
# Each pair is (wording that describes a layout SDLE no longer has, its current
# form). Two checks use them: no dry run may contain the old wording, and the
# documented commands must contain the new. Every pair is an exact literal,
# never a pattern, so nothing broader can be absorbed by accident.

DRY_RUN_SUBSTITUTIONS: tuple[tuple[str, str], ...] = (
    ('No `.workflow/` exists.',
     'No WorkItem runtime exists.'),
    ('`.workflow/audit.md` created, `.workflow/lock` written',
     '`workitems/todo-api/.sdle/audit.md` created, `workitems/todo-api/.sdle/lock` written'),
    ('Artifact path: .workflow/implementation-manifest.md',
     'Artifact path: workitems/todo-api/.sdle/implementation-manifest.md'),
    ('Completion summary: .workflow/completion-summary.json',
     'Completion summary: workitems/todo-api/.sdle/completion-summary.json'),
    ('- `.workflow/lock` was rewritten',
     '- `workitems/todo-api/.sdle/lock` was rewritten'),
    ('- `.workflow/completion-summary.json` written exactly once',
     '- `workitems/todo-api/.sdle/completion-summary.json` written exactly once'),
    ('Fresh project (no `.workflow/`)',
     'Fresh project (no WorkItem runtime)'),
    ('(`.workflow/`, `.specify/`, `design/`, `reviews/`, `clarifications/`, `guidance/`, `requirements/`)',
     '(`.workflow/`, `.sdle/`, `workitems/`, `.specify/`, `design/`, `reviews/`, `clarifications/`, `guidance/`, `requirements/`)'),
    ('(`.workflow/lock` is fresh with a different token)',
     '(`workitems/todo-api/.sdle/lock` is fresh with a different token)'),
    ('rejection entry from `.workflow/audit.md`',
     'rejection entry from `workitems/todo-api/.sdle/audit.md`'),
    ('.workflow/audit.md has been edited, truncated, or written by another session.',
     'workitems/todo-api/.sdle/audit.md has been edited, truncated, or written by another session.'),
    ('.workflow/audit.md before proceeding.',
     'workitems/todo-api/.sdle/audit.md before proceeding.'),
    ('(inspects `.workflow/audit.md`,',
     '(inspects `workitems/todo-api/.sdle/audit.md`,'),
    ('Someone edited `.workflow/state.json`',
     'Someone edited `workitems/todo-api/.sdle/state.json`'),
    ('Delete .workflow/state.json and .workflow/audit.md',
     'Delete workitems/todo-api/.sdle/state.json and workitems/todo-api/.sdle/audit.md'),
    ('and the `.workflow/lock` session lock are deleted',
     'and the `workitems/todo-api/.sdle/lock` session lock are deleted'),
    ('independent fresh project (no `.workflow/`)',
     'independent fresh project (no WorkItem runtime)'),
    # SDLE-DEFECT-STABILIZATION-01 D05: SpecKit v1.0.6 rejects `--skills`.
    # The replacement is the command actually run against it, copied from
    # `SPECKIT_INIT_COMMAND` in the engine, which a unit test holds equal.
    ('  uvx --from git+https://github.com/github/spec-kit.git specify init . '
     '--skills --here',
     '  uvx --from git+https://github.com/github/spec-kit.git@v1.0.6 specify '
     'init --here --force --non-interactive --integration claude --script sh'),
)


# ---------------------------------------------------------------------------
# SDLE-DEFECT-STABILIZATION-01 -- verification commands for Gate 7 (D02)
# ---------------------------------------------------------------------------
#
# Gate 7 now refuses anything but a test run that actually ran and exited 0.
# A driver that crosses Gate 7 therefore supplies a real command through
# `manifest build --test-command`: the engine runs it and records its exit code
# exactly as it would a detected runner. The interpreter is used rather than a
# generated pytest suite, because a nested pytest start-up per traversal would
# add minutes to a suite that crosses Gate 7 dozens of times, and the property
# under test is the engine's handling of the outcome, not pytest. Real pytest
# runs, passing and failing, are covered separately.
#
# Quoted the way the engine splits it: the raw string on Windows (where the
# C runtime parses the command line), `shlex` on POSIX.


def _command_line(argv: list[str]) -> str:
    return (subprocess.list2cmdline(argv) if os.name == "nt"
            else shlex.join(argv))


PASSING_TEST_COMMAND = _command_line(
    [sys.executable, "-c", "raise SystemExit(0)"])
FAILING_TEST_COMMAND = _command_line(
    [sys.executable, "-c", "raise SystemExit(1)"])


# --------------------------------------------------------------------------
# Restatement search (invariant 7): which files must not repeat an engine fact
# --------------------------------------------------------------------------

MAINTENANCE_RECORDS = Path(".sdle") / "implementation-state" / "repository-cleanup"
"""Execution records of a repository-maintenance run: ledgers, run logs and
recorders whose whole job is to quote engine vocabulary (test names, result
words). They are evidence, not a prompt or documentation surface. The
exclusion is this one directory and nothing wider: every other file under
`.sdle/` is still searched."""


def searchable_files(root: Path = REPO_ROOT) -> list[Path]:
    """Every versioned prose/config file that must not restate a fact owned by
    `scripts/sdle.py`: the README, `CLAUDE.md`, the Reference Guide, the skill,
    command, hook and product-agent prompts, the architecture decisions and the
    repository configuration under `.sdle/` (minus `MAINTENANCE_RECORDS`)."""
    files = [p for p in (root / "README.md", root / "CLAUDE.md",
                         root / "docs" / "SDLE-Reference-Guide.md") if p.is_file()]
    skipped = root / MAINTENANCE_RECORDS
    for directory in (root / ".claude" / "skills", root / ".claude" / "commands",
                      root / ".claude" / "hooks", root / ".sdle",
                      root / "docs" / "architecture"):
        if directory.is_dir():
            files.extend(p for p in sorted(directory.rglob("*"))
                         if p.is_file() and skipped not in p.parents)
    agents = root / ".claude" / "agents"
    if agents.is_dir():
        files.extend(p for p in sorted(agents.glob("sdle-*.md")) if p.is_file())
    return files
