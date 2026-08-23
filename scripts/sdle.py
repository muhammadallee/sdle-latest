#!/usr/bin/env python3
"""SDLE — Spec Driven Lifecycle Engine, deterministic core.

Python 3.11+, standard library only, cross-platform.

Contract:
  * JSON object on stdout, human-readable text on stderr.
  * Exit 0 success | 1 refused | 2 usage error | 3 integrity failure.
  * The script refuses; it does not warn. A refusal is exit 1 with a
    machine-readable ``reason``. The caller surfaces it; the caller cannot
    override it.
  * Writes to state.json are atomic (temp file + replace).
  * Every subcommand is idempotent for a given state.

The seven constant tables live in SKILL.md and are parsed from it. They are
never restated here. See ``Constants``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, replace as dataclass_replace
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Exit codes — the contract
# --------------------------------------------------------------------------

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_INTEGRITY = 3


def _force_utf8_streams() -> None:
    """Emit UTF-8 regardless of the platform's default encoding.

    The status header carries '📋' and an em dash. On Windows the default
    stream encoding is the ANSI code page, so those bytes are not valid UTF-8
    — a caller decoding UTF-8 (which is what every caller does) gets mojibake,
    or a decode error that surfaces as an empty stream. Both streams are part
    of the contract, so both are pinned.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


_force_utf8_streams()

MIN_ARTIFACT_BYTES = 100


class SdleError(Exception):
    """Base for every controlled failure. Never raised bare."""

    exit_code = EXIT_REFUSED

    def __init__(self, reason: str, message: str, data: dict | None = None):
        super().__init__(message)
        self.reason = reason
        self.message = message
        self.data = data or {}


class Refused(SdleError):
    """A precondition failed. The caller may not proceed."""

    exit_code = EXIT_REFUSED


class UsageError(SdleError):
    """The command was malformed."""

    exit_code = EXIT_USAGE


class IntegrityError(SdleError):
    """State unreadable, audit chain broken, or lock conflict."""

    exit_code = EXIT_INTEGRITY


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


@dataclass
class Paths:
    """Locations the engine works with — repository plus the active WorkItem.

    ``project_root`` is the target project (the repository context).
    ``skill_root`` is the directory holding ``SKILL.md`` — the constants host.
    ``workitem`` is the bound WorkItem id, or ``None`` for the transitional
    legacy layout. It is the *only* switch between the two runtime locations:
    every runtime path below derives from ``runtime``, so no command ever
    concatenates a WorkItem-owned path of its own.
    """

    project_root: Path
    skill_root: Path
    workitem: str | None = None

    @property
    def legacy_workflow(self) -> Path:
        """Repository-global runtime. Transitional: migration source only."""
        return self.project_root / ".workflow"

    @property
    def workitem_root(self) -> Path | None:
        if self.workitem is None:
            return None
        return self.project_root / "workitems" / self.workitem

    @property
    def runtime(self) -> Path:
        root = self.workitem_root
        return self.legacy_workflow if root is None else root / ".sdle"

    @property
    def runtime_relative(self) -> str:
        """The runtime directory as a repo-relative POSIX prefix.

        Emitted paths and git pathspecs use ``/`` on every platform.
        """
        return str(self.runtime.relative_to(self.project_root)).replace(os.sep, "/")

    # `workflow` is retained as an alias so call sites that only ever meant
    # "the runtime directory" did not have to move in T02.
    @property
    def workflow(self) -> Path:
        return self.runtime

    @property
    def state_file(self) -> Path:
        return self.runtime / "state.json"

    @property
    def audit_file(self) -> Path:
        return self.runtime / "audit.md"

    @property
    def lock_file(self) -> Path:
        return self.runtime / "lock"

    @property
    def execution_file(self) -> Path:
        return self.runtime / "execution.json"

    @property
    def manifest_file(self) -> Path:
        return self.runtime / "implementation-manifest.md"

    @property
    def completion_file(self) -> Path:
        return self.runtime / "completion-summary.json"

    @property
    def evidence_dir(self) -> Path:
        return self.runtime / "evidence"

    @property
    def skill_md(self) -> Path:
        return self.skill_root / "SKILL.md"

    @property
    def gate_protocol_md(self) -> Path:
        return self.skill_root / "modules" / "gate-protocol.md"

    @property
    def phase_execution_md(self) -> Path:
        return self.skill_root / "modules" / "phase-execution.md"

    @property
    def security_review_md(self) -> Path:
        return self.skill_root / "modules" / "security-review.md"

    @property
    def state_template(self) -> Path:
        return self.skill_root / "templates" / "state.json"


def _candidate_skill_roots(script_path: Path, project_root: Path) -> list[Path]:
    """Ordered places a skill directory may live.

    Dev layout puts ``sdle.py`` in ``<repo>/scripts/`` alongside
    ``<repo>/.claude/skills/sdle/``. Installed layouts put the skill under the
    target project or the user profile.
    """
    repo_root = script_path.resolve().parent.parent
    return [
        repo_root / ".claude" / "skills" / "sdle",
        project_root / ".claude" / "skills" / "sdle",
        Path.home() / ".claude" / "skills" / "sdle",
    ]


def resolve_paths(project_root: str | None, skill_root: str | None) -> Paths:
    proj = Path(project_root or os.environ.get("SDLE_PROJECT_ROOT") or Path.cwd())
    proj = proj.resolve()

    explicit = skill_root or os.environ.get("SDLE_SKILL_ROOT")
    if explicit:
        skill = Path(explicit).resolve()
        if not (skill / "SKILL.md").is_file():
            raise Refused(
                "skill_root_not_found",
                f"No SKILL.md under the given skill root: {skill}",
                {"skill_root": str(skill)},
            )
        return Paths(project_root=proj, skill_root=skill)

    for candidate in _candidate_skill_roots(Path(__file__), proj):
        if (candidate / "SKILL.md").is_file():
            return Paths(project_root=proj, skill_root=candidate.resolve())

    raise Refused(
        "skill_root_not_found",
        "Could not locate the SDLE skill directory (no SKILL.md found). "
        "Pass --skill-root or set SDLE_SKILL_ROOT.",
        {"searched": [str(p) for p in _candidate_skill_roots(Path(__file__), proj)]},
    )


# --------------------------------------------------------------------------
# Markdown table parsing — the constants are data, not code
# --------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^#{2,4}\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\b")
_NULLISH = {"", "-", "—", "–", "n/a", "none", "*(terminal)*", "(terminal)", "(none)"}


def _normalise_cell(raw: str) -> str | None:
    """Strip a markdown cell to its value. Backticks and emphasis are noise."""
    value = raw.strip()
    value = re.sub(r"^\*+|\*+$", "", value).strip()
    if value.startswith("`") and value.endswith("`") and len(value) >= 2:
        value = value[1:-1].strip()
    if value.lower() in _NULLISH:
        return None
    return value


def _normalise_header(raw: str) -> str:
    value = _normalise_cell(raw) or ""
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|"):
        stripped = stripped[:-1]
    return stripped.split("|")


def _is_separator(line: str) -> bool:
    return bool(re.fullmatch(r"\|?[\s:|-]+\|?", line.strip())) and "-" in line


def parse_md_table(path: Path, heading: str) -> list[dict[str, str | None]]:
    """Return the first markdown table following ``### <heading>`` in ``path``.

    Raises rather than returning an empty list. A constant table that silently
    parses to nothing would let ``advance`` compute a wrong next phase and fail
    open — the exact failure this engine exists to prevent.
    """
    if not path.is_file():
        raise IntegrityError(
            "constants_unreadable",
            f"Cannot read constants: {path} does not exist.",
            {"path": str(path), "heading": heading},
        )

    lines = path.read_text(encoding="utf-8").splitlines()

    start = None
    for index, line in enumerate(lines):
        match = _HEADING_RE.match(line)
        if match and match.group("name") == heading:
            start = index + 1
            break
    if start is None:
        raise IntegrityError(
            "constants_heading_missing",
            f"Heading '{heading}' not found in {path.name}. "
            "A constant table was renamed or removed.",
            {"path": str(path), "heading": heading},
        )

    header: list[str] | None = None
    rows: list[dict[str, str | None]] = []
    for line in lines[start:]:
        stripped = line.strip()
        if _HEADING_RE.match(line) or stripped.startswith("#"):
            break
        if not stripped.startswith("|"):
            if header is not None:
                break
            continue
        cells = _split_row(line)
        if header is None:
            header = [_normalise_header(cell) for cell in cells]
            continue
        if _is_separator(line):
            continue
        if len(cells) != len(header):
            raise IntegrityError(
                "constants_malformed",
                f"Table '{heading}' in {path.name} has a row with "
                f"{len(cells)} cells but {len(header)} columns: {stripped}",
                {"path": str(path), "heading": heading, "row": stripped},
            )
        rows.append({key: _normalise_cell(cell) for key, cell in zip(header, cells)})

    if header is None:
        raise IntegrityError(
            "constants_malformed",
            f"No table found under heading '{heading}' in {path.name}.",
            {"path": str(path), "heading": heading},
        )
    if not rows:
        raise IntegrityError(
            "constants_empty",
            f"Table '{heading}' in {path.name} parsed to zero rows.",
            {"path": str(path), "heading": heading},
        )
    return rows


# --------------------------------------------------------------------------
# Constants — parsed from SKILL.md, never restated
# --------------------------------------------------------------------------


@dataclass
class Constants:
    phase_sequence: list[str] = field(default_factory=list)
    next_phase: dict[str, str | None] = field(default_factory=dict)
    phase_to_gate_key: dict[str, str] = field(default_factory=dict)
    gate_number: dict[str, int] = field(default_factory=dict)
    artifact_ownership: dict[str, str] = field(default_factory=dict)
    phase_label: dict[str, str] = field(default_factory=dict)
    progress: dict[str, str] = field(default_factory=dict)
    gate_to_execution_phase: dict[str, str] = field(default_factory=dict)
    version_chain: list[tuple[str, str]] = field(default_factory=list)

    # -- derived ---------------------------------------------------------

    @property
    def gate_phases(self) -> list[str]:
        """GATE_PHASES is derived from PHASE_TO_GATE_KEY, not stored twice."""
        return [p for p in self.phase_sequence if p in self.phase_to_gate_key]

    @property
    def phase_count(self) -> int:
        """The N in 'N/18' — every phase except the terminal ``complete``."""
        return len([p for p in self.phase_sequence if p != "complete"])

    def index(self, phase: str) -> int:
        """1-based position in PHASE_SEQUENCE."""
        try:
            return self.phase_sequence.index(phase) + 1
        except ValueError:
            raise Refused(
                "unknown_phase",
                f"'{phase}' is not a phase in PHASE_SEQUENCE.",
                {"phase": phase, "known": self.phase_sequence},
            ) from None

    def phase_at(self, index: int) -> str:
        if not 1 <= index <= len(self.phase_sequence):
            raise Refused(
                "unknown_phase",
                f"Phase index {index} is out of range "
                f"(1-{len(self.phase_sequence)}).",
                {"index": index},
            )
        return self.phase_sequence[index - 1]

    def label(self, phase: str) -> str:
        if phase not in self.phase_label:
            raise Refused(
                "unknown_phase",
                f"No label registered for phase '{phase}'.",
                {"phase": phase},
            )
        return self.phase_label[phase]

    def progress_for(self, phase: str) -> str:
        if phase not in self.progress:
            raise Refused(
                "unknown_phase",
                f"No PROGRESS_MAP entry for phase '{phase}'.",
                {"phase": phase},
            )
        return self.progress[phase]


def _column(row: dict[str, str | None], *names: str) -> str | None:
    for name in names:
        if name in row:
            return row[name]
    raise IntegrityError(
        "constants_malformed",
        f"Expected one of columns {names!r}; table has {list(row)!r}.",
        {"expected": list(names), "found": list(row)},
    )


def load_constants(paths: Paths) -> Constants:
    consts = Constants()
    skill = paths.skill_md

    for row in parse_md_table(skill, "PHASE_SEQUENCE"):
        phase = _column(row, "phase_id", "phase")
        if phase:
            consts.phase_sequence.append(phase)

    for row in parse_md_table(skill, "NEXT_PHASE"):
        current = _column(row, "current_phase")
        if current:
            consts.next_phase[current] = _column(row, "next_phase")

    for row in parse_md_table(skill, "PHASE_TO_GATE_KEY"):
        phase = _column(row, "gate_phase")
        key = _column(row, "approvals_key", "gate_key")
        number = _column(row, "gate_number")
        if phase and key:
            consts.phase_to_gate_key[phase] = key
            if number:
                consts.gate_number[key] = int(number)

    for row in parse_md_table(skill, "ARTIFACT_OWNERSHIP"):
        key = _column(row, "gate_key")
        template = _column(row, "artifact_path_template")
        if key:
            consts.artifact_ownership[key] = template or "(none)"

    for row in parse_md_table(skill, "PHASE_LABEL_MAP"):
        phase = _column(row, "phase_id", "phase")
        if phase:
            consts.phase_label[phase] = _column(row, "label") or phase

    for row in parse_md_table(skill, "PROGRESS_MAP"):
        phase = _column(row, "phase", "phase_id")
        if phase:
            consts.progress[phase] = _column(row, "progress") or ""

    for row in parse_md_table(paths.gate_protocol_md, "GATE_TO_EXECUTION_PHASE"):
        key = _column(row, "gate_key")
        if key:
            consts.gate_to_execution_phase[key] = _column(row, "execution_phase") or ""

    for row in parse_md_table(skill, "VERSION_MIGRATION"):
        frm = _column(row, "from_version", "workflow_version")
        to = _column(row, "to_version")
        if frm:
            consts.version_chain.append((frm, to or frm))

    return consts


# --------------------------------------------------------------------------
# Hashing and atomic IO
# --------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Lowercase hex digest. PowerShell's Get-FileHash returned uppercase;
    migration normalises historical values so comparisons never false-drift."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_atomic(path: Path, text: str) -> None:
    """Write via temp file + replace so a crash never leaves a partial file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    try:
        with handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        # On Windows a transient external holder (on-access scanner, indexer,
        # backup agent) can hold the freshly written temp file or the
        # destination just long enough for os.replace to raise WinError 5.
        # ponytail: short retry window, not a lock. A permanent PermissionError
        # still raises on the final attempt -- atomicity is never weakened into
        # a silent swallow, and test_units_infra.py asserts that.
        for delay in (0.01, 0.02, 0.04, 0.08):
            try:
                os.replace(handle.name, path)
                break
            except PermissionError:
                time.sleep(delay)
        else:
            os.replace(handle.name, path)
    except BaseException:
        try:
            os.unlink(handle.name)
        except OSError:
            pass
        raise


# --------------------------------------------------------------------------
# Time and actor
# --------------------------------------------------------------------------


def now_iso() -> str:
    """UTC, second resolution, Z-suffixed. One format everywhere."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def parse_iso(value: str | None) -> datetime | None:
    """Parse an ISO-8601 instant, tolerating both 'Z' and numeric offsets."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def git(paths: Paths, *args: str) -> tuple[int, str]:
    """Run git in the project root. Never raises — git may be absent."""
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=str(paths.project_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except (OSError, ValueError):
        return 127, ""
    return completed.returncode, (completed.stdout or "").strip()


def git_available(paths: Paths) -> bool:
    code, _ = git(paths, "rev-parse", "--is-inside-work-tree")
    return code == 0


_ACTOR_CACHE: dict[str, str] = {}


def actor(paths: Paths) -> str:
    """Who is acting, for the audit ledger.

    Cached per project: this is called once per audit entry, and shelling out
    to `git config` twice each time dominated the runtime of a full workflow.
    """
    key = str(paths.project_root)
    if key not in _ACTOR_CACHE:
        _, name = git(paths, "config", "user.name")
        _, email = git(paths, "config", "user.email")
        _ACTOR_CACHE[key] = (
            f"{name} <{email}>" if name and email else (name or email or "unknown")
        )
    return _ACTOR_CACHE[key]


# --------------------------------------------------------------------------
# State IO
# --------------------------------------------------------------------------

CURRENT_VERSION = "1.14"

STATUS_DISPLAY = {
    "pending": "PENDING",
    "in_progress": "IN PROGRESS",
    "awaiting_approval": "AWAITING APPROVAL",
    "awaiting_reapproval": "AWAITING RE-APPROVAL (DRIFT DETECTED)",
    "completed": "COMPLETED",
    "rejected": "REJECTED — REMEDIATION NEEDED",
    "failed": "FAILED — ACTION REQUIRED",
}


def read_state(paths: Paths) -> dict:
    relative = paths.runtime_relative
    if not paths.state_file.is_file():
        raise IntegrityError(
            "state_unreadable",
            f"No {relative}/state.json in this project. "
            "Run `init` to start a workflow.",
            {"path": str(paths.state_file)},
        )
    try:
        return json.loads(paths.state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IntegrityError(
            "state_unreadable",
            f"{relative}/state.json is not valid JSON: {exc}. "
            "Options: 'reset workflow' to start fresh, or inspect the file.",
            {"path": str(paths.state_file), "error": str(exc)},
        ) from None


def save_state(paths: Paths, state: dict, session: str | None = None) -> None:
    """Persist state atomically. ``last_updated`` is implicit and mandatory."""
    state["last_updated"] = now_iso()
    write_atomic(paths.state_file, json.dumps(state, indent=2) + "\n")
    touch_lock(paths, session)


def load_template(paths: Paths) -> dict:
    if not paths.state_template.is_file():
        raise IntegrityError(
            "template_missing",
            f"State template not found at {paths.state_template}.",
            {"path": str(paths.state_template)},
        )
    return json.loads(paths.state_template.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Session lock
# --------------------------------------------------------------------------

LOCK_FRESH_SECONDS = 600


def touch_lock(paths: Paths, session: str | None) -> None:
    if not session:
        return
    paths.workflow.mkdir(parents=True, exist_ok=True)
    write_atomic(paths.lock_file, f"{now_iso()} {session}\n")


def read_lock(paths: Paths) -> tuple[str, str] | None:
    if not paths.lock_file.is_file():
        return None
    raw = paths.lock_file.read_text(encoding="utf-8").strip()
    parts = raw.split()
    if len(parts) != 2:
        return None
    return parts[0], parts[1]


def cmd_lock_acquire(args, paths: Paths) -> int:
    if not args.session:
        raise UsageError(
            "session_required",
            "lock acquire needs a session token: --session <token>.",
            {},
        )
    existing = read_lock(paths)
    foreign = False
    fresh = False
    age = None
    held_by = None
    if existing:
        stamp, token = existing
        held_by = token
        foreign = token != args.session
        when = parse_iso(stamp)
        if when is not None:
            age = int((datetime.now(timezone.utc) - when).total_seconds())
            fresh = age < LOCK_FRESH_SECONDS

    touch_lock(paths, args.session)
    emit(
        "lock acquire",
        {
            "held_by": held_by,
            "session": args.session,
            "age_seconds": age,
            "foreign": foreign,
            "fresh": fresh,
            "warn": bool(foreign and fresh),
        },
    )
    if foreign and fresh:
        print(
            f"Another session may be operating on this workflow "
            f"(lock touched {age}s ago).",
            file=sys.stderr,
        )
    return EXIT_OK


def cmd_lock_release(args, paths: Paths) -> int:
    existed = paths.lock_file.is_file()
    if existed:
        paths.lock_file.unlink()
    emit("lock release", {"released": existed})
    return EXIT_OK


# --------------------------------------------------------------------------
# Audit — per-entry prev_sha chain plus whole-file audit_sha
# --------------------------------------------------------------------------

GENESIS = "genesis"
_ENTRY_SPLIT = re.compile(r"^## AUDIT ", re.MULTILINE)


def _entry_digest(block: str) -> str:
    return hashlib.sha256(block.strip().encode("utf-8")).hexdigest()


def split_audit_entries(text: str) -> list[str]:
    parts = _ENTRY_SPLIT.split(text)
    return [f"## AUDIT {chunk}".strip() for chunk in parts[1:]]


def append_audit(
    paths: Paths,
    state: dict,
    phase: str,
    event: str,
    message: str,
    artifact: str | None = None,
    artifact_sha: str | None = None,
    decision: str | None = None,
    comments: str | None = None,
) -> str:
    """Append an entry, chain it, and rebaseline ``audit_sha``.

    Ordering is load-bearing: append -> hash file -> save state.
    """
    paths.workflow.mkdir(parents=True, exist_ok=True)
    existing = (
        paths.audit_file.read_text(encoding="utf-8")
        if paths.audit_file.is_file()
        else ""
    )
    entries = split_audit_entries(existing)
    prev = _entry_digest(entries[-1]) if entries else GENESIS

    block = (
        f"## AUDIT [{now_iso()}] | {phase} — {event}\n"
        f"**Actor:** {actor(paths)}\n"
        f"**Action:** {message}\n"
        f"**Artifact:** {artifact or 'null'}\n"
        f"**Artifact SHA (SHA-256):** {artifact_sha or 'n/a'}\n"
        f"**Gate Decision:** {decision or 'n/a'}\n"
        f"**Comments:** {comments or 'None'}\n"
        f"**Prev:** {prev}\n"
    )
    separator = "" if not existing or existing.endswith("\n\n") else "\n"
    write_atomic(paths.audit_file, existing + separator + block)

    state["audit_sha"] = sha256_file(paths.audit_file)
    return state["audit_sha"]


def cmd_audit_append(args, paths: Paths) -> int:
    state = read_state(paths)
    sha = append_audit(
        paths,
        state,
        phase=args.phase,
        event=args.event,
        message=args.message,
        artifact=args.artifact,
        decision=args.decision,
    )
    save_state(paths, state, args.session)
    emit("audit append", {"audit_sha": sha, "phase": args.phase, "event": args.event})
    return EXIT_OK


def verify_audit_chain(entries: list[str]) -> tuple[bool, int | None]:
    """Walk the ``prev_sha`` chain. Returns ``(ok, first_broken_entry_number)``.

    Extracted unchanged from ``cmd_audit_verify`` at T02 so `migrate-workflow`
    can verify a ledger at a second location without restating the rule.
    """
    prev = GENESIS
    for index, block in enumerate(entries, start=1):
        match = re.search(r"^\*\*Prev:\*\*\s*(\S+)\s*$", block, flags=re.MULTILINE)
        recorded = match.group(1) if match else None
        if recorded != prev:
            return False, index
        prev = _entry_digest(block)
    return True, None


def cmd_audit_verify(args, paths: Paths) -> int:
    state = read_state(paths)
    expected = state.get("audit_sha")

    if expected is None:
        emit(
            "audit verify",
            {"expected": None, "actual": None, "matches": True, "entries": 0,
             "skipped": "no baseline recorded"},
        )
        return EXIT_OK

    if not paths.audit_file.is_file():
        emit(
            "audit verify",
            {"expected": expected, "actual": "FILE_MISSING", "matches": False,
             "entries": 0, "chain_ok": False},
            ok=False,
            reason="audit_chain_broken",
            message=f"{paths.runtime_relative}/audit.md is missing.",
        )
        print(
            f"audit_chain_broken: {paths.runtime_relative}/audit.md is missing.",
            file=sys.stderr,
        )
        return EXIT_INTEGRITY

    actual = sha256_file(paths.audit_file)
    entries = split_audit_entries(paths.audit_file.read_text(encoding="utf-8"))
    chain_ok, broken_at = verify_audit_chain(entries)

    matches = actual == expected and chain_ok
    data = {
        "expected": expected,
        "actual": actual,
        "matches": matches,
        "entries": len(entries),
        "chain_ok": chain_ok,
        "broken_at_entry": broken_at,
    }
    if matches:
        emit("audit verify", data)
        return EXIT_OK

    detail = (
        f"entry {broken_at} breaks the prev-hash chain"
        if not chain_ok
        else "whole-file hash does not match the recorded baseline"
    )
    emit(
        "audit verify",
        data,
        ok=False,
        reason="audit_chain_broken",
        message=f"Audit log integrity check failed: {detail}.",
    )
    print(f"audit_chain_broken: {detail}.", file=sys.stderr)
    return EXIT_INTEGRITY


def rechain_audit(paths: Paths) -> int:
    """Recompute every entry's Prev link over the ledger as it now stands.

    Needed by the rebaseline path: an edited ledger breaks the entry chain at
    the edit, and appending an acknowledgement cannot repair links that come
    before it. Re-chaining does not conceal anything — the acknowledgement
    entry itself records that the ledger was edited, and that entry is
    appended after the repair, so it is covered by the new chain.
    """
    if not paths.audit_file.is_file():
        return 0
    entries = split_audit_entries(paths.audit_file.read_text(encoding="utf-8"))
    rebuilt: list[str] = []
    prev = GENESIS
    for block in entries:
        fixed = re.sub(
            r"^\*\*Prev:\*\*.*$", f"**Prev:** {prev}", block, flags=re.MULTILINE
        )
        if "**Prev:**" not in fixed:
            fixed = f"{fixed}\n**Prev:** {prev}"
        rebuilt.append(fixed.strip())
        prev = _entry_digest(rebuilt[-1])
    write_atomic(paths.audit_file, "\n\n".join(rebuilt) + "\n")
    return len(rebuilt)


def cmd_audit_rebaseline(args, paths: Paths) -> int:
    """The `accept audit` path. Logged, so it can never happen silently."""
    state = read_state(paths)
    repaired = rechain_audit(paths)
    append_audit(
        paths,
        state,
        phase=state.get("current_phase", "unknown"),
        event="audit_rebaseline",
        message="User acknowledged audit integrity mismatch. Audit hash "
                f"re-baselined; {repaired} existing entrie(s) re-chained.",
    )
    save_state(paths, state, args.session)
    emit("audit rebaseline",
         {"audit_sha": state["audit_sha"], "rechained": repaired})
    return EXIT_OK


# --------------------------------------------------------------------------
# Migration
# --------------------------------------------------------------------------


def _add_missing(state: dict, **defaults) -> None:
    for key, value in defaults.items():
        state.setdefault(key, value)


def _mig_1_0(state, paths, consts):
    _add_missing(
        state,
        speckit_skill_prefix=None,
        current_artifact_sha=None,
        current_feature_id=None,
    )


def _mig_1_1(state, paths, consts):
    _add_missing(state, current_feature_id=None)


def _mig_1_2(state, paths, consts):
    pass


def _mig_1_3(state, paths, consts):
    state.setdefault("approvals", {}).setdefault("gate_design", None)


def _mig_1_4(state, paths, consts):
    _add_missing(
        state,
        rate_limits={"max_remediation_attempts": 3, "max_retry_attempts": 3},
        attempt_counts={},
    )


def _mig_1_5(state, paths, consts):
    _add_missing(state, verbose=False)


def _mig_1_6(state, paths, consts):
    _add_missing(state, clarification_phase=None)


def _mig_1_7(state, paths, consts):
    _add_missing(state, artifact_shas={}, drift_queue=[], pending_phase=None)


def _mig_1_8(state, paths, consts):
    _add_missing(
        state,
        phase_checkpoint=None,
        security_review_artifact=None,
        pending_confirm_action=None,
    )
    approvals = state.setdefault("approvals", {})
    approvals.setdefault("gate_tasks", None)
    approvals.setdefault("gate_security", None)
    phase = state.get("current_phase")
    if phase in consts.progress:
        state["progress"] = consts.progress[phase]
    if phase in {"implement", "gate_implement", "security_review", "complete"}:
        state.setdefault("_migration_warnings", []).append(
            "This workflow was created under SDLE v1.8, which had a different "
            "phase order. Phases gate_tasks (Gate 4), design_generation "
            "(Phase 13), and gate_design (Gate 6) were not part of the "
            "original run. You may continue from your current position or "
            "`restart phase 13` to generate design documents before the "
            "implementation review."
        )


def _mig_1_9(state, paths, consts):
    _add_missing(state, pending_confirm_action=None)


def _mig_1_10(state, paths, consts):
    _add_missing(state, last_updated=None)


def _mig_1_11(state, paths, consts):
    _add_missing(state, audit_sha=None)


def _mig_1_12(state, paths, consts):
    """v1.13: pin the security diff range, and normalise SHA case.

    v1.12 recorded PowerShell's uppercase Get-FileHash output. hashlib emits
    lowercase. Without normalising, every approved gate false-drifts on the
    first v1.13 run.
    """
    _add_missing(state, implementation_base_ref=None)

    normalised = 0
    shas = state.get("artifact_shas") or {}
    for key, value in list(shas.items()):
        if isinstance(value, str) and value != value.lower():
            shas[key] = value.lower()
            normalised += 1
    for key in ("current_artifact_sha", "audit_sha"):
        value = state.get(key)
        if isinstance(value, str) and value != value.lower():
            state[key] = value.lower()
            normalised += 1
    if normalised:
        state.setdefault("_migration_notes", []).append(
            f"Normalised {normalised} SHA value(s) to lowercase hex."
        )


def _mig_1_13(state, paths, consts):
    """Add ``workitem``, bound from where the state file actually lives.

    The state file becomes self-describing, so a file copied to the wrong
    WorkItem is detectable. Derivation is deterministic, never a guess: a state
    under ``workitems/<id>/.sdle/`` records ``<id>``; a state still at the
    legacy ``.workflow/`` location keeps ``null`` until `migrate-workflow`
    binds it.
    """
    _add_missing(state, workitem=None)
    if state.get("workitem") is None:
        parent = paths.state_file.parent
        if parent.name == ".sdle":
            state["workitem"] = parent.parent.name


MIGRATIONS: list[tuple[str, str, object]] = [
    ("1.0", "1.1", _mig_1_0),
    ("1.1", "1.2", _mig_1_1),
    ("1.2", "1.3", _mig_1_2),
    ("1.3", "1.4", _mig_1_3),
    ("1.4", "1.5", _mig_1_4),
    ("1.5", "1.6", _mig_1_5),
    ("1.6", "1.7", _mig_1_6),
    ("1.7", "1.8", _mig_1_7),
    ("1.8", "1.9", _mig_1_8),
    ("1.9", "1.10", _mig_1_9),
    ("1.10", "1.11", _mig_1_10),
    ("1.11", "1.12", _mig_1_11),
    ("1.12", "1.13", _mig_1_12),
    ("1.13", "1.14", _mig_1_13),
]


def migrate_state(state: dict, paths: Paths, consts: Constants) -> list[str]:
    version = state.get("workflow_version")
    known = {frm for frm, _, _ in MIGRATIONS} | {CURRENT_VERSION}
    if version not in known:
        raise Refused(
            "unknown_version",
            f"Unrecognized workflow_version: {version}. Options: "
            "'reset workflow' to start fresh, or 'show state' to inspect.",
            {"workflow_version": version, "known": sorted(known)},
        )

    steps: list[str] = []
    guard = 0
    while state.get("workflow_version") != CURRENT_VERSION:
        guard += 1
        if guard > len(MIGRATIONS) + 1:
            raise IntegrityError(
                "migration_loop",
                "Migration chain did not terminate.",
                {"workflow_version": state.get("workflow_version")},
            )
        current = state.get("workflow_version")
        for frm, to, func in MIGRATIONS:
            if frm == current:
                func(state, paths, consts)
                state["workflow_version"] = to
                steps.append(f"{frm}->{to}")
                break
        else:
            raise Refused(
                "unknown_version",
                f"No migration path from {current}.",
                {"workflow_version": current},
            )
    return steps


def cmd_migrate(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    before = state.get("workflow_version")
    steps = migrate_state(state, paths, consts)
    warnings = state.pop("_migration_warnings", [])
    notes = state.pop("_migration_notes", [])
    if steps:
        append_audit(
            paths,
            state,
            phase=state.get("current_phase", "unknown"),
            event="migration",
            message=f"State migrated {before} -> {CURRENT_VERSION} ({', '.join(steps)}).",
        )
        save_state(paths, state, args.session)
    for text in warnings + notes:
        print(text, file=sys.stderr)
    emit(
        "migrate",
        {
            "from": before,
            "to": state.get("workflow_version"),
            "steps": steps,
            "warnings": warnings,
            "notes": notes,
        },
    )
    return EXIT_OK


# --------------------------------------------------------------------------
# init / state / header
# --------------------------------------------------------------------------


def infer_project_name(paths: Paths) -> str | None:
    req_dir = paths.project_root / "requirements"
    if not req_dir.is_dir():
        return None
    for candidate in sorted(req_dir.glob("*.md")):
        for line in candidate.read_text(encoding="utf-8", errors="replace").splitlines():
            match = re.match(r"^#\s+(.+?)\s*$", line)
            if match:
                return match.group(1)
    return None


def cmd_init(args, paths: Paths) -> int:
    consts = load_constants(paths)

    if paths.state_file.is_file():
        raise Refused(
            "already_initialized",
            f"A workflow already exists in {paths.runtime_relative}/state.json. "
            "Use `reset --confirm` to clear it, or resume where you left off.",
            {"path": str(paths.state_file)},
        )

    req_dir = paths.project_root / "requirements"
    requirements = sorted(p.name for p in req_dir.glob("*")) if req_dir.is_dir() else []
    if not requirements:
        raise Refused(
            "requirements_missing",
            "I need requirements before starting the workflow. Create a "
            "`requirements/` folder and add at least one document.",
            {"path": str(req_dir)},
        )

    # The WorkItem title sits *after* heading inference deliberately: it is a
    # better identity than a directory name, but the requirements heading is
    # still the most specific thing the project says about itself, and moving
    # the WorkItem ahead of it would change behaviour nothing asks to change.
    metadata = workitem_metadata(paths) or {}
    name = (
        args.project
        or infer_project_name(paths)
        or (metadata.get("title") or "").strip()
        or paths.project_root.name
    )

    state = load_template(paths)
    state["workitem"] = paths.workitem
    state["project_name"] = name
    state["current_phase"] = "requirements_check"
    state["status"] = "in_progress"
    state["progress"] = consts.progress_for("requirements_check")

    paths.workflow.mkdir(parents=True, exist_ok=True)
    stamp = now_iso()
    execution_id = execution_identity(paths, stamp)
    write_execution_file(paths, execution_id, stamp)
    append_audit(
        paths,
        state,
        phase="requirements_check",
        event="workflow_initialized",
        message=f"Workflow initialized for '{name}'. "
        f"{len(requirements)} requirements document(s) found.",
    )

    # Requirements check completes immediately; the workflow advances to the
    # first generation phase, matching dry-run 01's first turn.
    state["phase_history"].append(
        {
            "phase": "requirements_check",
            "completed_at": now_iso(),
            "outcome": "completed",
        }
    )
    nxt = consts.next_phase["requirements_check"]
    state["current_phase"] = nxt
    state["status"] = "pending"
    state["progress"] = consts.progress_for(nxt)
    append_audit(
        paths,
        state,
        phase="requirements_check",
        event="phase_complete",
        message=f"Requirements validated. Advanced to {nxt}.",
    )
    save_state(paths, state, args.session)

    emit(
        "init",
        {
            "project_name": name,
            "workitem": paths.workitem,
            "execution_id": execution_id,
            "requirements": requirements,
            "current_phase": state["current_phase"],
            "status": state["status"],
            "progress": state["progress"],
            "audit_sha": state["audit_sha"],
        },
    )
    return EXIT_OK


def cmd_state_get(args, paths: Paths) -> int:
    state = read_state(paths)
    if args.field:
        if args.field not in state:
            raise Refused(
                "unknown_field",
                f"No field '{args.field}' in state.json.",
                {"field": args.field, "known": sorted(state)},
            )
        emit("state get", {"field": args.field, "value": state[args.field]})
    else:
        emit("state get", state)
    return EXIT_OK


# Fields the orchestrator legitimately sets, and the only ones `state set`
# will touch. Everything else is engine-owned: it is derived from a transition,
# a verification or an approval, and letting the model set it directly would
# reintroduce exactly the hand-edited state the write fence exists to stop.
SETTABLE_FIELDS = {
    "verbose": bool,
    "clarification_phase": str,
    "speckit_skill_prefix": str,
}


def _coerce(field: str, raw: str | None):
    kind = SETTABLE_FIELDS[field]
    if raw is None or raw.lower() in {"null", "none"}:
        return None
    if kind is bool:
        if raw.lower() in {"true", "yes", "on", "1"}:
            return True
        if raw.lower() in {"false", "no", "off", "0"}:
            return False
        raise UsageError(
            "bad_value",
            f"{field} is a boolean; got {raw!r}.",
            {"field": field, "value": raw},
        )
    return raw


def cmd_state_set(args, paths: Paths) -> int:
    if args.field not in SETTABLE_FIELDS:
        raise Refused(
            "field_not_settable",
            f"'{args.field}' is not orchestrator-settable. Settable fields: "
            f"{', '.join(sorted(SETTABLE_FIELDS))}. Everything else is derived "
            "by the engine — use the subcommand that owns it.",
            {"field": args.field, "settable": sorted(SETTABLE_FIELDS)},
        )
    state = read_state(paths)
    value = _coerce(args.field, args.value)
    before = state.get(args.field)
    state[args.field] = value
    append_audit(
        paths, state, phase=state.get("current_phase", "unknown"),
        event="state_set",
        message=f"{args.field}: {before!r} -> {value!r}.",
    )
    save_state(paths, state, args.session)
    emit("state set", {"field": args.field, "value": value, "previous": before})
    return EXIT_OK


def cmd_retry(args, paths: Paths) -> int:
    """Guard the retry path.

    Retrying while a drift re-approval is pending would re-run generation over
    an artifact the user has not re-accepted.
    """
    state = read_state(paths)
    queue = state.get("drift_queue") or []
    if queue:
        raise Refused(
            "drift_pending",
            "Cannot retry while artifact drift re-approvals are pending. Use "
            "`approve` or `reject with comments: <feedback>` to handle the "
            "drifted artifact first.",
            {"drift_queue": queue, "pending_phase": state.get("pending_phase")},
        )
    emit("retry", {"phase": state.get("current_phase"),
                   "status": state.get("status")})
    return EXIT_OK


def render_header(state: dict, consts: Constants) -> str:
    phase = state.get("current_phase", "unknown")
    status = state.get("status", "unknown")
    progress = state.get("progress") or consts.progress.get(phase, "?")
    label = consts.phase_label.get(phase, phase)
    display = STATUS_DISPLAY.get(status, status.upper())
    return (
        f"<!-- SDLE_STATE phase={phase} status={status} progress={progress} -->\n"
        f"📋 SDLE Status: Phase {progress} — {label} [{display}]"
    )


def cmd_header(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    rendered = render_header(state, consts)
    print(rendered, file=sys.stderr)
    emit(
        "header",
        {
            "rendered": rendered,
            "phase": state.get("current_phase"),
            "status": state.get("status"),
            "progress": state.get("progress"),
            "label": consts.phase_label.get(state.get("current_phase", ""), None),
        },
    )
    return EXIT_OK


def cmd_state_dump(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    phase = state.get("current_phase", "unknown")

    lines = [
        "## SDLE Workflow State",
        "",
        "| Field | Value |",
        "|---|---|",
        f"| Version | {state.get('workflow_version')} |",
        f"| Phase | {phase} ({state.get('progress')}) |",
        f"| Label | {consts.phase_label.get(phase, phase)} |",
        f"| Status | {state.get('status')} |",
        f"| Progress | {state.get('progress')} |",
        f"| Last Updated | {state.get('last_updated')} |",
        f"| Verbose | {state.get('verbose')} |",
        f"| Pending Confirm | {state.get('pending_confirm_action') or 'none'} |",
        "",
        "### Approvals",
        "| Gate | Decision | Timestamp |",
        "|---|---|---|",
    ]
    approvals = state.get("approvals") or {}
    for gate_phase in consts.gate_phases:
        key = consts.phase_to_gate_key[gate_phase]
        entry = approvals.get(key)
        decision = entry.get("decision") if isinstance(entry, dict) else "pending"
        stamp = entry.get("timestamp") if isinstance(entry, dict) else "—"
        lines.append(f"| {key} | {decision or 'pending'} | {stamp or '—'} |")

    limits = state.get("rate_limits") or {}
    lines += [
        "",
        "### Artifacts",
        f"- Current artifact: {state.get('current_artifact') or 'none'}",
        f"- Current SHA: {state.get('current_artifact_sha') or 'none'}",
        f"- Feature ID: {state.get('current_feature_id') or 'none'}",
        f"- Security review artifact: {state.get('security_review_artifact') or 'none'}",
        f"- Implementation base ref: {state.get('implementation_base_ref') or 'none'}",
        "",
        "### Rate Limits",
        f"- Max remediation attempts: {limits.get('max_remediation_attempts')}",
        f"- Max retry attempts: {limits.get('max_retry_attempts')}",
        f"- Per-phase counts: {state.get('attempt_counts') or 'none'}",
        "",
        "### Drift State",
        f"- Drift queue: {state.get('drift_queue') or 'empty'}",
        f"- Pending phase: {state.get('pending_phase') or 'none'}",
        "",
        "### Phase History",
    ]
    history = state.get("phase_history") or []
    if history:
        for entry in history:
            lines.append(
                f"Phase {entry.get('phase')} — {entry.get('outcome')} "
                f"at {entry.get('completed_at')}"
            )
    else:
        lines.append("(none)")

    rendered = "\n".join(lines)
    print(rendered, file=sys.stderr)
    emit("state dump", {"rendered": rendered})
    return EXIT_OK


# --------------------------------------------------------------------------
# WorkItem identity
# --------------------------------------------------------------------------
#
# A WorkItem is an immutable identity created *before* a workflow is
# initialised, and since v1.14 it is also the runtime scope: `init` requires a
# resolved WorkItem and writes `workitems/<id>/.sdle/`. Identity is still
# created first and never changes; the runtime is created under it.

WORKITEM_ID_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?$")
AUTO_ID_RE = re.compile(r"^WI-[a-z0-9]([a-z0-9-]*[a-z0-9])?-\d{8}T\d{6}Z$")
WORKITEM_NAME_MAX = 64

# Windows refuses to create a directory with any of these names, whatever the
# extension. The engine is cross-platform, so the id vocabulary is the
# intersection of what every target filesystem accepts.
RESERVED_NAMES = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{n}" for n in range(1, 10)}
    | {f"lpt{n}" for n in range(1, 10)}
)

INDEX_HEADING = "# Work Items"
INDEX_COLUMNS = ["Created", "WorkItem", "Type", "Title", "Synopsis"]

# Path separators and pipes never survive normalisation as themselves — they
# would either be dropped (turning `a/b` into the *valid* id `ab`, silently
# accepting a traversal-shaped name) or corrupt the pipe-delimited registry.
# Refuse the raw name instead of quietly rewriting it.
_RAW_NAME_FORBIDDEN = re.compile(r"[/\\|\x00-\x1f\x7f]")
_INDEX_UNSAFE = re.compile(r"[|\r\n\t]")


def _name_invalid(rule: str, raw: str | None, detail: str) -> Refused:
    return Refused(
        "workitem_name_invalid",
        f"WorkItem name {raw!r} is not usable: {detail}.",
        {"rule": rule, "name": raw},
    )


def normalize_workitem_name(raw: str | None) -> str:
    """Contract §7 rules 1-9 (uniqueness, rule 10, is the caller's job).

    trim, lowercase, whitespace -> '-', '_' -> '-', drop unsupported
    punctuation, collapse repeated hyphens, strip leading/trailing hyphens,
    allow only [a-z0-9-], reject empty.
    """
    text = (raw or "").strip()
    if not text:
        raise _name_invalid("empty", raw, "it is empty or only whitespace")
    if _RAW_NAME_FORBIDDEN.search(text):
        raise _name_invalid(
            "unsafe_character", raw,
            "it contains a path separator, a pipe or a control character",
        )

    value = text.lower()
    value = re.sub(r"\s+", "-", value)
    value = value.replace("_", "-")
    value = re.sub(r"[^a-z0-9-]+", "", value)
    value = re.sub(r"-{2,}", "-", value)
    value = value.strip("-")

    if not value:
        raise _name_invalid(
            "empty_after_normalization", raw,
            "nothing usable remains after normalisation",
        )
    if len(value) > WORKITEM_NAME_MAX:
        raise _name_invalid(
            "too_long", raw,
            f"it normalises to {len(value)} characters, over the "
            f"{WORKITEM_NAME_MAX}-character limit",
        )
    if not WORKITEM_ID_RE.match(value):
        raise _name_invalid("charset", raw, "it is not kebab-case [a-z0-9-]")
    if value in RESERVED_NAMES:
        raise _name_invalid(
            "reserved_name", raw,
            f"'{value}' is a reserved device name on Windows",
        )
    return value


def workitems_root(paths: Paths) -> Path:
    return paths.project_root / "workitems"


def workitem_index_file(paths: Paths) -> Path:
    return workitems_root(paths) / "index.md"


def workitem_dir(paths: Paths, workitem_id: str) -> Path:
    """Locate a WorkItem directory, refusing anything outside the registry.

    The id regex already makes traversal unreachable; this is a second fence,
    not the primary control.
    """
    root = workitems_root(paths)
    if (root / workitem_id).resolve().parent != root.resolve():
        raise _name_invalid(
            "path_escape", workitem_id,
            "it does not resolve inside workitems/",
        )
    return root / workitem_id


def _index_malformed(path: Path, detail: str) -> IntegrityError:
    return IntegrityError(
        "index_malformed",
        f"workitems/index.md is not a valid WorkItem registry: {detail}. "
        "SDLE will not rewrite it — repair the file by hand.",
        {"path": str(path), "detail": detail},
    )


def read_index(paths: Paths) -> list[dict[str, str]]:
    """Parse the append-only registry. An absent file is an empty registry.

    Structure is validated before anything else happens, so a corrupt registry
    stops both `create` and `list` before a single byte is written.
    """
    path = workitem_index_file(paths)
    if not path.is_file():
        return []

    lines = [
        line for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not lines or lines[0].strip() != INDEX_HEADING:
        raise _index_malformed(path, f"first line must be '{INDEX_HEADING}'")
    if len(lines) < 3:
        raise _index_malformed(path, "header row or separator row is missing")

    header = [cell.strip() for cell in _split_row(lines[1])]
    if header != INDEX_COLUMNS:
        raise _index_malformed(
            path, f"columns must be {INDEX_COLUMNS}, found {header}"
        )
    if not _is_separator(lines[2]):
        raise _index_malformed(path, "separator row is missing")

    rows: list[dict[str, str]] = []
    for line in lines[3:]:
        cells = [cell.strip() for cell in _split_row(line)]
        if len(cells) != len(INDEX_COLUMNS):
            raise _index_malformed(
                path,
                f"row has {len(cells)} cells, expected {len(INDEX_COLUMNS)}: "
                f"{line.strip()}",
            )
        rows.append(dict(zip(INDEX_COLUMNS, cells)))
    return rows


def _index_cell(value: str | None) -> str:
    """Registry cells are pipe-delimited and unescaped, so neutralise the
    delimiter rather than let one synopsis corrupt every later read."""
    text = _INDEX_UNSAFE.sub(" ", (value or "").strip())
    return re.sub(r"\s+", " ", text).strip() or "-"


def append_index_row(paths: Paths, row: dict[str, str]) -> None:
    """Read, validate, append exactly one row, then write the whole file.

    Building the full text in memory and handing it to ``write_atomic`` is why
    a crash can never leave a torn registry.
    """
    rows = read_index(paths) + [row]
    lines = [
        INDEX_HEADING,
        "",
        "| " + " | ".join(INDEX_COLUMNS) + " |",
        "|" + "---|" * len(INDEX_COLUMNS),
    ]
    lines += [
        "| " + " | ".join(_index_cell(entry.get(c)) for c in INDEX_COLUMNS) + " |"
        for entry in rows
    ]
    write_atomic(workitem_index_file(paths), "\n".join(lines) + "\n")


def _git_value(paths: Paths, *args: str) -> str | None:
    """A git fact, or None. Metadata records what is knowable; missing git is
    never a refusal."""
    code, out = git(paths, *args)
    return out if code == 0 and out else None


def cmd_workitem_create(args, paths: Paths) -> int:
    raw = (args.name or "").strip()
    name = normalize_workitem_name(raw)

    # One clock read for the whole command: two would let createdAt and the
    # generated id straddle a second boundary.
    stamp = now_iso()
    if args.auto_generate:
        workitem_id = f"WI-{name}-{stamp.replace('-', '').replace(':', '')}"
        if not AUTO_ID_RE.match(workitem_id):
            raise _name_invalid(
                "auto_id_malformed", raw,
                f"generated id {workitem_id!r} is not a valid WorkItem id",
            )
    else:
        workitem_id = name

    # Every validation precedes every write.
    existing = read_index(paths)
    target = workitem_dir(paths, workitem_id)

    known: dict[str, str] = {}
    for entry in existing:
        known.setdefault(entry["WorkItem"].lower(), entry["WorkItem"])
    root = workitems_root(paths)
    if root.is_dir():
        for child in sorted(root.iterdir()):
            if child.is_dir():
                known.setdefault(child.name.lower(), child.name)
    if workitem_id.lower() in known:
        collision = known[workitem_id.lower()]
        raise Refused(
            "workitem_exists",
            f"WorkItem '{collision}' already exists. Resume the existing "
            "WorkItem, or provide another name — SDLE never auto-suffixes.",
            {"id": collision, "requested": workitem_id},
        )

    branch = _git_value(paths, "rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":  # detached: there is no branch to record
        branch = None
    synopsis = (args.synopsis or "").strip() or None

    metadata = {
        "id": workitem_id,
        "name": name,
        "title": raw,
        "type": (args.type or "").strip() or "enhancement",
        "synopsis": synopsis,
        "createdAt": stamp,
        "createdBy": {
            "gitUserName": _git_value(paths, "config", "user.name"),
            "gitUserEmail": _git_value(paths, "config", "user.email"),
        },
        "git": {"initialBranch": branch},
        "sdleVersion": CURRENT_VERSION,
    }

    metadata_file = target / "workitem.json"
    fresh_dir = not target.exists()
    try:
        write_atomic(metadata_file, json.dumps(metadata, indent=2) + "\n")
        append_index_row(paths, {
            "Created": stamp,
            "WorkItem": workitem_id,
            "Type": metadata["type"],
            "Title": raw,
            "Synopsis": synopsis,
        })
    except BaseException:
        # All-or-nothing: an orphaned metadata file would make the id look
        # taken while the registry says otherwise.
        try:
            metadata_file.unlink(missing_ok=True)
            if fresh_dir:
                target.rmdir()
        except OSError:
            pass
        raise

    emit("workitem create", {
        "id": workitem_id,
        "name": name,
        "title": metadata["title"],
        "type": metadata["type"],
        "synopsis": synopsis,
        "created_at": stamp,
        "path": str(target),
        "metadata_file": str(metadata_file),
        "index_file": str(workitem_index_file(paths)),
    })
    return EXIT_OK


def cmd_workitem_list(args, paths: Paths) -> int:
    """Project the registry, in creation order. The index is the single source
    of truth — never the directory listing."""
    rows = read_index(paths)
    emit("workitem list", {
        "count": len(rows),
        "workitems": [
            {
                "id": entry["WorkItem"],
                "created": entry["Created"],
                "type": entry["Type"],
                "title": entry["Title"],
            }
            for entry in rows
        ],
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# WorkItem resolution
# --------------------------------------------------------------------------
#
# T02 implements the minimum ladder that makes the runtime addressable. CWD,
# branch, persisted context and inference are T03. The ladder NEVER guesses:
# when more than one WorkItem could be meant it refuses and lists them.

# Commands that touch no runtime state, so the ladder never runs for them.
# `migrate-workflow` is here because it does its own explicit binding from a
# mandatory --workitem.
RUNTIME_FREE_COMMANDS = frozenset({
    "lint-skill", "sha", "constants", "workitem", "migrate-workflow",
})


def registered_workitem_ids(paths: Paths) -> list[str]:
    """Registered ids, in creation order. The index is the only source."""
    return [row["WorkItem"] for row in read_index(paths)]


def legacy_state_present(paths: Paths) -> bool:
    return (paths.legacy_workflow / "state.json").is_file()


def bind_workitem(
    paths: Paths, explicit: str | None = None, *, for_init: bool = False
) -> Paths:
    """Resolve the active WorkItem and return `paths` bound to it.

    Pure: it either returns a bound ``Paths`` or raises ``Refused``. Nothing is
    printed and nothing is written, so the hooks can call it speculatively.

    Ladder (contract §8, plan D2):

    1. explicit ``--workitem <id>``, which must be registered;
    2. else the sole registered WorkItem;
    3. else zero WorkItems *and* a legacy ``.workflow/state.json`` -> legacy
       binding (``workitem is None``). TRANSITIONAL, removed at T11: without
       it T02 would brick a repository that already holds a workflow, because
       every command would refuse before `migrate-workflow` could run;
    4. else zero WorkItems -> refuse ``workitem_required``;
    5. else -> refuse ``workitem_ambiguous``. Never pick one.

    ``for_init`` is the one exception. `init` never takes rung 3 and refuses
    ``legacy_workflow_present`` whenever legacy state exists, *whatever* the
    registered count. Proceeding would create a second runtime while the legacy
    one became simultaneously unbindable (rung 3 needs zero WorkItems) and
    unmigratable (`migrate-workflow` would then refuse `target_exists`).
    """
    if for_init and legacy_state_present(paths):
        raise Refused(
            "legacy_workflow_present",
            "A repository-global workflow still exists at "
            f"{paths.legacy_workflow.name}/state.json. Move it under a "
            "WorkItem first: `migrate-workflow --workitem <id>`. SDLE will "
            "not run two runtimes side by side.",
            {"legacy_state": str(paths.legacy_workflow / "state.json")},
        )

    known = registered_workitem_ids(paths)

    if explicit:
        if explicit not in known:
            raise Refused(
                "workitem_unknown",
                f"No WorkItem '{explicit}' in workitems/index.md. Create it "
                "with `workitem create --name <name>`, or pick one of the "
                "registered ids.",
                {"requested": explicit, "workitems": known},
            )
        return dataclass_replace(paths, workitem=explicit)

    if len(known) == 1:
        return dataclass_replace(paths, workitem=known[0])

    if not known:
        if not for_init and legacy_state_present(paths):
            return paths  # rung 3 — transitional legacy binding
        raise Refused(
            "workitem_required",
            "No WorkItem is registered in this repository. Create one first: "
            "`workitem create --name <name>`.",
            {"workitems": []},
        )

    raise Refused(
        "workitem_ambiguous",
        f"{len(known)} WorkItems are registered and none was named. Re-run "
        "with `--workitem <id>`. SDLE never picks one for you.",
        {"workitems": known},
    )


def workitem_metadata_file(paths: Paths) -> Path | None:
    root = paths.workitem_root
    return None if root is None else root / "workitem.json"


def workitem_metadata(paths: Paths) -> dict | None:
    """The bound WorkItem's `workitem.json`, or None. Never raises: metadata
    is descriptive, and a missing or unreadable file is not a refusal."""
    target = workitem_metadata_file(paths)
    if target is None or not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


# --------------------------------------------------------------------------
# Execution identity
# --------------------------------------------------------------------------
#
# Contract §8: `<3-letter-git-user-prefix>-<UTC-datetime>`, e.g.
# `muh-20260816T171501Z`. This is execution/audit metadata — it is never the
# WorkItem name, and nothing resolves a WorkItem from it.


def execution_prefix(paths: Paths) -> str:
    """git user.name -> lowercase -> drop non-alphanumeric -> first 3 chars.
    Falls back to the email local part, then to `usr`."""
    for source in (
        _git_value(paths, "config", "user.name"),
        (_git_value(paths, "config", "user.email") or "").split("@", 1)[0],
    ):
        slug = re.sub(r"[^a-z0-9]", "", (source or "").lower())[:3]
        if slug:
            return slug
    return "usr"


def execution_identity(paths: Paths, stamp: str | None = None) -> str:
    compact = (stamp or now_iso()).replace("-", "").replace(":", "")
    return f"{execution_prefix(paths)}-{compact}"


def write_execution_file(paths: Paths, execution_id: str, stamp: str) -> dict:
    payload = {
        "executionId": execution_id,
        "workitem": paths.workitem,
        "startedAt": stamp,
        "sdleVersion": CURRENT_VERSION,
    }
    write_atomic(paths.execution_file, json.dumps(payload, indent=2) + "\n")
    return payload


# --------------------------------------------------------------------------
# migrate-workflow — legacy .workflow/ to workitems/<id>/.sdle/
# --------------------------------------------------------------------------
#
# Contract §20. The legacy runtime is NEVER written to, renamed or deleted
# (§8.9): the only recovery a user ever needs is to delete the target
# directory, after which resolution rung 3 binds the legacy runtime again.
#
# Crash safety: every write before the commit point is a whole-file overwrite,
# so an interruption anywhere leaves no resolvable target workflow, keeps the
# legacy authoritative, and makes a re-run safe. The target `state.json` is
# written LAST and is the sole commit marker.

# Fields whose survival the target verification asserts (contract §20.11).
MIGRATION_VERIFIED_FIELDS = (
    "current_phase", "status", "progress", "approvals", "artifact_shas",
    "rate_limits", "attempt_counts", "implementation_base_ref", "phase_history",
)


def cmd_migrate_workflow(args, paths: Paths) -> int:
    consts = load_constants(paths)

    # Step 2 — an explicitly resolved, already-registered WorkItem. §20 says
    # "resolve/create"; this narrows it to *resolve* so WorkItem creation keeps
    # exactly one entry point, `workitem create`.
    requested = getattr(args, "migrate_workitem", None) or args.workitem
    if not requested:
        raise UsageError(
            "workitem_required",
            "migrate-workflow needs a target: --workitem <id>.",
            {},
        )
    known = registered_workitem_ids(paths)
    if requested not in known:
        raise Refused(
            "workitem_unknown",
            f"No WorkItem '{requested}' in workitems/index.md. Create it "
            "first with `workitem create --name <name>`.",
            {"requested": requested, "workitems": known},
        )

    legacy = dataclass_replace(paths, workitem=None)
    target = dataclass_replace(paths, workitem=requested)

    # Step 3 — re-run safety. No --force: that would be the fail-open option.
    if target.state_file.is_file():
        raise Refused(
            "target_exists",
            f"{target.runtime_relative}/state.json already exists. SDLE will "
            "not overwrite a WorkItem's runtime; pick another WorkItem, or "
            "remove that runtime deliberately first.",
            {"path": str(target.state_file)},
        )

    # Step 4 — validate legacy state.
    if not legacy.state_file.is_file():
        raise IntegrityError(
            "legacy_state_missing",
            f"There is no {legacy.runtime_relative}/state.json to migrate.",
            {"path": str(legacy.state_file)},
        )
    try:
        state = json.loads(legacy.state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IntegrityError(
            "legacy_state_invalid",
            f"{legacy.runtime_relative}/state.json is not valid JSON: {exc}. "
            "Nothing was written; repair or remove it and re-run.",
            {"path": str(legacy.state_file), "error": str(exc)},
        ) from None
    known_versions = {frm for frm, _, _ in MIGRATIONS} | {CURRENT_VERSION}
    if not isinstance(state, dict) or state.get("workflow_version") not in known_versions:
        raise IntegrityError(
            "legacy_state_invalid",
            f"{legacy.runtime_relative}/state.json does not carry a known "
            "workflow_version. Nothing was written.",
            {
                "path": str(legacy.state_file),
                "workflow_version": (
                    state.get("workflow_version") if isinstance(state, dict) else None
                ),
                "known": sorted(known_versions),
            },
        )

    # Step 5 — legacy audit integrity, using the same verifier `audit verify`
    # uses. A broken chain must not be laundered by copying it somewhere new.
    expected_audit = state.get("audit_sha")
    audit_text = (
        legacy.audit_file.read_text(encoding="utf-8")
        if legacy.audit_file.is_file() else None
    )
    if expected_audit is not None:
        broken = None
        if audit_text is None:
            broken = f"{legacy.runtime_relative}/audit.md is missing"
        else:
            chain_ok, broken_at = verify_audit_chain(split_audit_entries(audit_text))
            if not chain_ok:
                broken = f"entry {broken_at} breaks the prev-hash chain"
            elif sha256_file(legacy.audit_file) != expected_audit:
                broken = "audit_sha does not match the ledger on disk"
        if broken:
            raise Refused(
                "legacy_audit_broken",
                f"The legacy audit ledger is not intact ({broken}). Migrating "
                "it would carry the break into the WorkItem. Resolve it with "
                "`audit rebaseline` first; nothing was written.",
                {"detail": broken, "path": str(legacy.audit_file)},
            )

    # Step 6 — capture the source facts that become migration evidence.
    stamp = now_iso()
    execution_id = execution_identity(paths, stamp)
    facts = {
        "migratedFrom": legacy.runtime_relative,
        "at": stamp,
        "executionId": execution_id,
        "workitem": requested,
        "legacyStateSha": sha256_file(legacy.state_file),
        "legacyAuditSha": (
            sha256_file(legacy.audit_file) if legacy.audit_file.is_file() else None
        ),
        "gitHead": _git_value(paths, "rev-parse", "HEAD"),
        "sdleVersion": CURRENT_VERSION,
    }

    # Step 7 — copy, each via write_atomic, state.json deliberately excluded.
    if audit_text is not None:
        write_atomic(target.audit_file, audit_text)
    for source, destination in (
        (legacy.manifest_file, target.manifest_file),
        (legacy.completion_file, target.completion_file),
    ):
        if source.is_file():
            write_atomic(destination, source.read_text(encoding="utf-8"))
    evidence_file = target.evidence_dir / f"migration-{execution_id}.json"
    write_atomic(evidence_file, json.dumps(facts, indent=2) + "\n")
    write_execution_file(target, execution_id, stamp)

    # Step 8 — verify the copied ledger *at the new location* before anything
    # commits, then migrate in memory, then append the migration entry, then
    # write the target state.json LAST.
    if audit_text is not None and expected_audit is not None:
        copied_ok, _ = verify_audit_chain(
            split_audit_entries(target.audit_file.read_text(encoding="utf-8"))
        )
        if not copied_ok or sha256_file(target.audit_file) != expected_audit:
            raise IntegrityError(
                "migration_verify_failed",
                "The audit ledger did not survive the copy intact. Nothing "
                f"was committed; {legacy.runtime_relative}/ remains "
                "authoritative.",
                {"path": str(target.audit_file)},
            )

    migrated = json.loads(json.dumps(state))
    steps = migrate_state(migrated, target, consts)
    migrated.pop("_migration_warnings", None)
    migrated.pop("_migration_notes", None)
    migrated["workitem"] = requested

    append_audit(
        target, migrated,
        phase=migrated.get("current_phase") or "unknown",
        event="workflow_migrated",
        message=f"Workflow migrated from {legacy.runtime_relative}/ to "
                f"{target.runtime_relative}/ (execution {execution_id}). "
                f"Legacy runtime left untouched.",
    )
    write_atomic(target.state_file, json.dumps(migrated, indent=2) + "\n")  # COMMIT

    # Step 9 — verify the target. The anchor is the in-memory migrated state:
    # when the version chain runs no steps it is byte-equal to the legacy
    # values, which is the comparison contract §20.11 asks for; when the chain
    # does run, the chain's own effect is not a migration defect.
    reread = json.loads(target.state_file.read_text(encoding="utf-8"))
    mismatch = [f for f in MIGRATION_VERIFIED_FIELDS
                if reread.get(f) != migrated.get(f)]
    if reread.get("workitem") != requested:
        mismatch.append("workitem")
    target_chain_ok, _ = verify_audit_chain(
        split_audit_entries(target.audit_file.read_text(encoding="utf-8"))
    )
    if not target_chain_ok or sha256_file(target.audit_file) != reread.get("audit_sha"):
        mismatch.append("audit")
    if mismatch:
        # Undo the commit marker: without state.json the target does not
        # resolve, and the legacy runtime stays the only authority.
        target.state_file.unlink(missing_ok=True)
        raise IntegrityError(
            "migration_verify_failed",
            f"The migrated state did not verify ({', '.join(mismatch)}). The "
            f"target was rolled back; {legacy.runtime_relative}/ remains "
            "authoritative.",
            {"fields": mismatch},
        )

    # Step 10 — record the migration on the WorkItem's identity metadata.
    metadata_file = workitem_metadata_file(target)
    metadata = workitem_metadata(target) or {}
    metadata["migration"] = {
        "migratedFrom": facts["migratedFrom"],
        "at": stamp,
        "executionId": execution_id,
        "legacyStateSha": facts["legacyStateSha"],
    }
    write_atomic(metadata_file, json.dumps(metadata, indent=2) + "\n")

    def relative(path: Path) -> str:
        return str(path.relative_to(paths.project_root)).replace(os.sep, "/")

    # Step 12 — the legacy runtime is archival, never deleted by SDLE.
    emit("migrate-workflow", {
        "workitem": requested,
        "from": legacy.runtime_relative,
        "to": target.runtime_relative,
        "execution_id": execution_id,
        "migration_steps": steps,
        "state_file": relative(target.state_file),
        "evidence": relative(evidence_file),
        "legacy_state_sha": facts["legacyStateSha"],
        "legacy_audit_sha": facts["legacyAuditSha"],
        "legacy_archive": legacy.runtime_relative,
        "legacy_preserved": True,
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# Artifact path resolution
# --------------------------------------------------------------------------


def resolve_artifact_path(
    state: dict, consts: Constants, gate_key: str, paths: Paths | None = None
) -> tuple[str | None, str | None]:
    """Resolve ARTIFACT_OWNERSHIP's template for ``gate_key``.

    Returns ``(resolved_path, skip_reason)``. A skip reason means the gate has
    no comparable artifact yet — not that something failed.

    ARTIFACT_OWNERSHIP is a SKILL.md constant table and T02 does not edit it
    (T04 owns those templates). The one template that names the runtime —
    Gate 7's ``.workflow/implementation-manifest.md`` — is re-pointed at the
    active WorkItem runtime here, in the single place templates are resolved,
    rather than by teaching every caller to concatenate. Transitional: it goes
    away when the table itself moves.
    """
    template = consts.artifact_ownership.get(gate_key)
    if not template or template == "(none)":
        return None, "no artifact registered for this gate"

    resolved = template
    legacy_prefix = ".workflow/"
    if paths is not None and resolved.startswith(legacy_prefix):
        resolved = paths.runtime_relative + "/" + resolved[len(legacy_prefix):]

    for placeholder, field_name in (
        ("{current_feature_id}", "current_feature_id"),
        ("{security_review_artifact}", "security_review_artifact"),
    ):
        if placeholder in resolved:
            value = state.get(field_name)
            if not value:
                return None, f"{field_name} is not resolved yet"
            resolved = resolved.replace(placeholder, str(value))
    return resolved, None


def cmd_artifact_path(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    if args.gate not in consts.artifact_ownership:
        raise Refused(
            "unknown_gate",
            f"'{args.gate}' is not a gate key in ARTIFACT_OWNERSHIP.",
            {"gate": args.gate, "known": sorted(consts.artifact_ownership)},
        )
    resolved, skipped = resolve_artifact_path(state, consts, args.gate, paths)
    emit(
        "artifact path",
        {
            "gate": args.gate,
            "template": consts.artifact_ownership.get(args.gate),
            "resolved": resolved,
            "skipped_reason": skipped,
            "exists": bool(resolved and (paths.project_root / resolved).is_file()),
        },
    )
    return EXIT_OK


# --------------------------------------------------------------------------
# Advancing — where gate discipline is enforced
# --------------------------------------------------------------------------


def gate_key_for(consts: Constants, phase: str) -> str | None:
    return consts.phase_to_gate_key.get(phase)


def approval_decision(state: dict, gate_key: str) -> str | None:
    entry = (state.get("approvals") or {}).get(gate_key)
    if isinstance(entry, dict):
        return entry.get("decision")
    return None


def apply_advance(
    paths: Paths,
    state: dict,
    consts: Constants,
    target: str,
    status: str | None,
    outcome: str,
) -> dict:
    """Move to ``target``, enforcing the two refusals that matter.

    Refuses a forward jump (any target that is not NEXT_PHASE[current]) and
    refuses to leave a gate phase whose approval is not recorded. These are the
    guardrails the model must not be able to reason its way around.
    """
    current = state.get("current_phase")
    if current is None:
        raise IntegrityError(
            "state_unreadable", "state.json has no current_phase.", {}
        )

    expected = consts.next_phase.get(current)
    if target != expected:
        current_index = consts.index(current)
        target_index = consts.index(target)
        raise Refused(
            "forward_jump",
            f"Cannot advance {current} -> {target}. The only permitted next "
            f"phase is {expected}. Forward jumps are not allowed; to advance "
            "through the workflow, approve the intervening gates.",
            {
                "from": current,
                "requested": target,
                "expected": expected,
                "from_index": current_index,
                "requested_index": target_index,
            },
        )

    gate_key = gate_key_for(consts, current)
    if gate_key is not None:
        decision = approval_decision(state, gate_key)
        if decision != "approved":
            raise Refused(
                "gate_not_approved",
                f"{current} has not been approved (decision: {decision or 'none'}). "
                "A gate can only be passed by an explicit approval.",
                {"gate": gate_key, "phase": current, "decision": decision},
            )

    if status is None:
        status = "awaiting_approval" if target in consts.phase_to_gate_key else "pending"

    state.setdefault("phase_history", []).append(
        {"phase": current, "completed_at": now_iso(), "outcome": outcome}
    )
    state["current_phase"] = target
    state["status"] = status
    state["progress"] = consts.progress_for(target)
    return {
        "from": current,
        "to": target,
        "status": status,
        "progress": state["progress"],
    }


def cmd_advance(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    moved = apply_advance(
        paths, state, consts, args.to, args.status, args.outcome or "completed"
    )
    append_audit(
        paths,
        state,
        phase=moved["from"],
        event="phase_advance",
        message=f"Advanced {moved['from']} -> {moved['to']} "
        f"({moved['progress']}, {moved['status']}).",
    )
    save_state(paths, state, args.session)
    emit("advance", moved)
    return EXIT_OK


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------


def require_gate(consts: Constants, gate_key: str) -> str:
    for phase, key in consts.phase_to_gate_key.items():
        if key == gate_key:
            return phase
    raise Refused(
        "unknown_gate",
        f"'{gate_key}' is not a registered gate key.",
        {"gate": gate_key, "known": sorted(consts.phase_to_gate_key.values())},
    )


def cmd_gate_show(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    gate_phase = require_gate(consts, args.gate)
    resolved, skipped = resolve_artifact_path(state, consts, args.gate, paths)
    full = paths.project_root / resolved if resolved else None
    emit(
        "gate show",
        {
            "gate": args.gate,
            "gate_phase": gate_phase,
            "gate_number": consts.gate_number.get(args.gate),
            "gate_total": len(consts.gate_phases),
            "label": consts.phase_label.get(gate_phase),
            "execution_phase": consts.gate_to_execution_phase.get(args.gate),
            "artifact_path": resolved,
            "skipped_reason": skipped,
            "exists": bool(full and full.is_file()),
            "artifact_sha": sha256_file(full) if full and full.is_file() else None,
            "baseline_sha": (state.get("artifact_shas") or {}).get(args.gate),
            "decision": approval_decision(state, args.gate),
        },
    )
    return EXIT_OK


def write_completion_summary(paths: Paths, state: dict) -> str:
    summary = {
        "workflow_version": state.get("workflow_version"),
        "project_name": state.get("project_name"),
        "completed_at": now_iso(),
        "phases_completed": len(state.get("phase_history") or []),
        "security_review_artifact": state.get("security_review_artifact"),
        "all_gates_approved": True,
    }
    target = paths.completion_file
    write_atomic(target, json.dumps(summary, indent=2) + "\n")
    return str(target.relative_to(paths.project_root)).replace(os.sep, "/")


def cmd_gate_approve(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    stamp = now_iso()

    queue = state.get("drift_queue") or []
    if queue:
        return _approve_drift(args, paths, state, consts, stamp)

    gate_phase = require_gate(consts, args.gate)
    if state.get("current_phase") != gate_phase:
        raise Refused(
            "not_at_gate",
            f"Cannot approve {args.gate}: the workflow is at "
            f"{state.get('current_phase')}, not {gate_phase}.",
            {"gate": args.gate, "current_phase": state.get("current_phase")},
        )

    resolved, _ = resolve_artifact_path(state, consts, args.gate, paths)
    sha = None
    if resolved:
        full = paths.project_root / resolved
        if not full.is_file():
            raise Refused(
                "artifact_missing",
                f"Cannot approve {args.gate}: {resolved} does not exist. "
                "A gate is an approval of specific content.",
                {"gate": args.gate, "path": resolved},
            )
        sha = sha256_file(full)
        state.setdefault("artifact_shas", {})[args.gate] = sha

    gate_precondition_hook(paths, state, consts, args.gate, resolved)

    state.setdefault("approvals", {})[args.gate] = {
        "decision": "approved",
        "comments": args.comments,
        "timestamp": stamp,
    }
    number = consts.gate_number.get(args.gate)
    append_audit(
        paths,
        state,
        phase=gate_phase,
        event="gate_approved",
        message=f"Gate {number} approved. Baseline SHA recorded: {sha or 'n/a'}.",
        artifact=resolved,
        artifact_sha=sha,
        decision="APPROVED",
        comments=args.comments,
    )

    is_final = consts.next_phase.get(gate_phase) == "complete"
    moved = apply_advance(paths, state, consts, "complete" if is_final
                          else consts.next_phase[gate_phase],
                          "completed" if is_final else None, "approved")

    summary_path = None
    if is_final:
        summary_path = write_completion_summary(paths, state)
        append_audit(
            paths,
            state,
            phase="complete",
            event="workflow_complete",
            message=f"Gate {number}/{len(consts.gate_phases)} (security) approved. "
            "Workflow complete. Completion summary written.",
            artifact=summary_path,
        )

    save_state(paths, state, args.session)
    emit(
        "gate approve",
        {
            "gate": args.gate,
            "sha": sha,
            "drift_mode": False,
            "remaining_drift": [],
            "next_phase": moved["to"],
            "status": moved["status"],
            "progress": moved["progress"],
            "completion_summary": summary_path,
        },
    )
    return EXIT_OK


def _approve_drift(args, paths: Paths, state: dict, consts: Constants,
                   stamp: str) -> int:
    """Drift re-approval: the queue head is re-baselined to current content."""
    queue = list(state.get("drift_queue") or [])
    gate_key = queue[0]
    if args.gate and args.gate != gate_key:
        raise Refused(
            "drift_pending",
            f"Drift re-approval is pending for {gate_key}; approve that first.",
            {"expected": gate_key, "requested": args.gate, "queue": queue},
        )

    resolved, _ = resolve_artifact_path(state, consts, gate_key, paths)
    sha = None
    if resolved and (paths.project_root / resolved).is_file():
        sha = sha256_file(paths.project_root / resolved)
        state.setdefault("artifact_shas", {})[gate_key] = sha

    state.setdefault("approvals", {})[gate_key] = {
        "decision": "approved",
        "comments": args.comments or "re-approved after artifact drift",
        "timestamp": stamp,
    }
    queue.pop(0)
    state["drift_queue"] = queue

    append_audit(
        paths,
        state,
        phase=state.get("current_phase", "unknown"),
        event="drift_reapproved",
        message=f"Drift re-approval: {gate_key} re-approved. "
        f"New baseline SHA: {sha or 'n/a'}.",
        artifact=resolved,
        artifact_sha=sha,
        decision="APPROVED",
        comments=args.comments,
    )

    resumed = None
    if not queue:
        resumed = state.get("pending_phase")
        if resumed:
            state["current_phase"] = resumed
            state["progress"] = consts.progress_for(resumed)
        state["pending_phase"] = None
        state["status"] = "in_progress"

    save_state(paths, state, args.session)
    emit(
        "gate approve",
        {
            "gate": gate_key,
            "sha": sha,
            "drift_mode": True,
            "remaining_drift": queue,
            "resumed_phase": resumed,
            "status": state["status"],
        },
    )
    return EXIT_OK


def cmd_gate_reject(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    stamp = now_iso()

    queue = list(state.get("drift_queue") or [])
    if queue:
        gate_key = queue[0]
        state.setdefault("approvals", {})[gate_key] = {
            "decision": "rejected",
            "comments": args.reason,
            "timestamp": stamp,
        }
        state["drift_queue"] = []
        state["pending_phase"] = None
        state["status"] = "rejected"
        append_audit(
            paths,
            state,
            phase=state.get("current_phase", "unknown"),
            event="drift_rejected",
            message=f"Drift re-approval REJECTED for {gate_key}. "
            f"Feedback: {args.reason}. Drift queue cleared.",
            decision="REJECTED",
            comments=args.reason,
        )
        save_state(paths, state, args.session)
        emit(
            "gate reject",
            {
                "gate": gate_key,
                "drift_mode": True,
                "execution_phase": consts.gate_to_execution_phase.get(gate_key),
                "status": "rejected",
            },
        )
        return EXIT_OK

    gate_phase = require_gate(consts, args.gate)
    if state.get("current_phase") != gate_phase:
        raise Refused(
            "not_at_gate",
            f"Cannot reject {args.gate}: the workflow is at "
            f"{state.get('current_phase')}, not {gate_phase}.",
            {"gate": args.gate, "current_phase": state.get("current_phase")},
        )

    state.setdefault("approvals", {})[args.gate] = {
        "decision": "rejected",
        "comments": args.reason,
        "timestamp": stamp,
    }
    state["status"] = "rejected"
    append_audit(
        paths,
        state,
        phase=gate_phase,
        event="gate_rejected",
        message=f"Gate {consts.gate_number.get(args.gate)} rejected. "
        f"Comments: {args.reason}.",
        decision="REJECTED",
        comments=args.reason,
    )
    save_state(paths, state, args.session)
    emit(
        "gate reject",
        {
            "gate": args.gate,
            "drift_mode": False,
            "execution_phase": consts.gate_to_execution_phase.get(args.gate),
            "status": "rejected",
            "remediations": ((state.get("attempt_counts") or {})
                             .get(gate_phase, {}).get("remediations", 0)),
        },
    )
    return EXIT_OK


def _git_diff_for(paths: Paths, relative: str) -> str | None:
    """The actual change, when the artifact is git-tracked.

    Fingerprints tell a reviewer *that* something changed; a diff tells them
    *what*, which is what re-approval actually requires.
    """
    code, _ = git(paths, "ls-files", "--error-unmatch", relative)
    if code != 0:
        return None
    code, out = git(paths, "diff", "--", relative)
    if code != 0 or not out:
        return None
    return out


def compute_drift(paths: Paths, state: dict, consts: Constants,
                  with_diff: bool = False) -> list[dict]:
    drifted: list[dict] = []
    approvals = state.get("approvals") or {}
    baselines = state.get("artifact_shas") or {}

    for gate_phase in consts.gate_phases:
        gate_key = consts.phase_to_gate_key[gate_phase]
        entry = approvals.get(gate_key)
        if not isinstance(entry, dict) or entry.get("decision") != "approved":
            continue
        baseline = baselines.get(gate_key)
        if not baseline:
            continue  # pre-v1.8 approval: no baseline to compare against
        resolved, _ = resolve_artifact_path(state, consts, gate_key, paths)
        if not resolved:
            continue

        full = paths.project_root / resolved
        current = sha256_file(full) if full.is_file() else "FILE_MISSING"
        if current == baseline.lower():
            continue

        record = {
            "gate": gate_key,
            "gate_phase": gate_phase,
            "label": consts.phase_label.get(gate_phase),
            "path": resolved,
            "approved_sha": baseline,
            "current_sha": current,
            "diff": None,
        }
        if with_diff and current != "FILE_MISSING":
            record["diff"] = _git_diff_for(paths, resolved)
        drifted.append(record)

    return drifted


def cmd_drift_check(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    drifted = compute_drift(paths, state, consts, with_diff=args.diff)

    queued = False
    if drifted and args.queue:
        state["drift_queue"] = [d["gate"] for d in drifted]
        state["pending_phase"] = args.pending_phase or state.get("current_phase")
        state["status"] = "awaiting_reapproval"
        append_audit(
            paths,
            state,
            phase=state.get("current_phase", "unknown"),
            event="drift_detected",
            message="Artifact drift detected for gates: "
            f"{', '.join(d['gate'] for d in drifted)}. Entering drift "
            f"re-approval mode. Pending phase: {state['pending_phase']}.",
        )
        save_state(paths, state, args.session)
        queued = True

    emit(
        "drift check",
        {
            "drifted": drifted,
            "queue": state.get("drift_queue") or [],
            "pending_phase": state.get("pending_phase"),
            "queued": queued,
        },
    )
    return EXIT_OK


def cmd_drift_rebaseline(args, paths: Paths) -> int:
    """Move a gate's baseline to current content without a re-approval.

    Only legitimate where the same file is deliberately refined between two
    gates that both own it — analyze refining tasks.md, which Gate 4 already
    fingerprinted. Without this the drift check would raise a false alarm on a
    clean run.
    """
    consts = load_constants(paths)
    state = read_state(paths)
    if args.gate not in consts.artifact_ownership:
        raise Refused(
            "unknown_gate", f"'{args.gate}' is not a registered gate key.",
            {"gate": args.gate},
        )
    if (state.get("artifact_shas") or {}).get(args.gate) is None:
        emit("drift rebaseline", {"gate": args.gate, "sha": None,
                                  "skipped": "no baseline recorded"})
        return EXIT_OK

    resolved, skipped = resolve_artifact_path(state, consts, args.gate, paths)
    if not resolved or not (paths.project_root / resolved).is_file():
        raise Refused(
            "artifact_missing",
            f"Cannot rebaseline {args.gate}: {resolved or skipped}.",
            {"gate": args.gate, "path": resolved},
        )
    sha = sha256_file(paths.project_root / resolved)
    state["artifact_shas"][args.gate] = sha
    append_audit(
        paths, state, phase=state.get("current_phase", "unknown"),
        event="drift_rebaseline",
        message=f"Drift baseline updated for {args.gate}.",
        artifact=resolved, artifact_sha=sha,
    )
    save_state(paths, state, args.session)
    emit("drift rebaseline", {"gate": args.gate, "sha": sha})
    return EXIT_OK


def cmd_feature_resolve(args, paths: Paths) -> int:
    """Identify the SpecKit feature directory created by the specify step."""
    state = read_state(paths)
    specs = paths.project_root / ".specify" / "specs"
    candidates = sorted(
        (p for p in specs.glob("*") if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    ) if specs.is_dir() else []

    if not candidates:
        raise Refused(
            "feature_unresolved",
            "No feature directory found under .specify/specs/. The "
            "specification step did not produce one.",
            {"searched": str(specs)},
        )

    chosen = candidates[0].name
    ambiguous = (
        len(candidates) > 1
        and candidates[0].stat().st_mtime == candidates[1].stat().st_mtime
    )
    if ambiguous:
        raise Refused(
            "feature_ambiguous",
            "Multiple feature directories share the newest timestamp; "
            "cannot choose between them.",
            {"candidates": [p.name for p in candidates]},
        )

    state["current_feature_id"] = chosen
    save_state(paths, state, args.session)
    emit(
        "feature resolve",
        {"feature_id": chosen, "candidates": [p.name for p in candidates]},
    )
    return EXIT_OK


def cmd_security_review_begin(args, paths: Paths) -> int:
    """Pin the review filename before generation, so crash recovery and drift
    detection both know the target path."""
    state = read_state(paths)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"reviews/security-review-{stamp}.md"
    state["security_review_artifact"] = filename
    state["phase_checkpoint"] = "security_review_started"
    save_state(paths, state, args.session)
    emit(
        "security-review begin",
        {
            "review_filename": filename,
            "base_ref": state.get("implementation_base_ref"),
        },
    )
    return EXIT_OK


REQUIRED_MANIFEST_SECTIONS = (
    "## Changed/Added Files",
    "## Potential Secrets Detected",
    "## Test Evidence",
)


def gate_precondition_hook(paths: Paths, state: dict, consts: Constants,
                           gate_key: str, resolved: str | None) -> None:
    """Gate-specific refusals that must hold at the choke point.

    Gate 7 is the one gate whose artifact is machine-generated, so it is the
    one gate whose completeness can be checked mechanically. A hook can be
    skipped; this refusal cannot — an implementation whose secrets scan or
    tests never ran does not reach a human decision.
    """
    if gate_key != "gate_implement" or not resolved:
        return None

    body = (paths.project_root / resolved).read_text(
        encoding="utf-8", errors="replace"
    )
    missing = [s for s in REQUIRED_MANIFEST_SECTIONS if s not in body]
    if missing:
        raise Refused(
            "manifest_incomplete",
            f"Cannot approve Gate 7: {resolved} is missing "
            f"{', '.join(missing)}. Rebuild it with `manifest build` so the "
            "secrets scan and test evidence are in front of the reviewer at "
            "the moment of decision.",
            {"path": resolved, "missing": missing},
        )
    return None


# --------------------------------------------------------------------------
# Attempt counters
#
# Retries are keyed by the phase that failed. Remediations are keyed by the
# EXECUTION phase behind a gate, not the gate phase itself — v1.12 reports
# "spec_draft has been remediated 3/3" while current_phase is gate_spec.
# --------------------------------------------------------------------------


def counters_for(state: dict, phase: str) -> dict:
    counts = state.setdefault("attempt_counts", {})
    return counts.setdefault(phase, {"remediations": 0, "retries": 0})


def limit(state: dict, name: str) -> int:
    return int((state.get("rate_limits") or {}).get(name, 3))


# --------------------------------------------------------------------------
# Artifact verification — Post-SpecKit Verification, mechanised
# --------------------------------------------------------------------------


def cmd_artifact_record(args, paths: Paths) -> int:
    state = read_state(paths)
    phase = args.phase or state.get("current_phase")
    target = paths.project_root / args.path
    exists = target.is_file()
    size = target.stat().st_size if exists else 0

    if exists and size >= MIN_ARTIFACT_BYTES:
        sha = sha256_file(target)
        state["current_artifact"] = args.path
        state["current_artifact_sha"] = sha
        counters_for(state, phase)["retries"] = 0
        state["phase_checkpoint"] = None
        append_audit(
            paths, state, phase=phase, event="artifact_recorded",
            message=f"Artifact verified and fingerprinted ({size} bytes).",
            artifact=args.path, artifact_sha=sha,
        )
        save_state(paths, state, args.session)
        emit("artifact record",
             {"path": args.path, "sha256": sha, "bytes": size, "optional": False})
        return EXIT_OK

    if args.optional:
        # Phase 8's checklist: absent or thin is tolerated, and recorded.
        append_audit(
            paths, state, phase=phase, event="artifact_absent",
            message=f"Optional artifact {args.path} not produced "
                    "— proceeding without it.",
        )
        state["phase_checkpoint"] = None
        save_state(paths, state, args.session)
        emit("artifact record",
             {"path": args.path, "sha256": None, "bytes": size, "optional": True,
              "skipped": True})
        return EXIT_OK

    # Verification failed. Freeze, count the retry, then decide.
    state["status"] = "failed"
    counters = counters_for(state, phase)
    counters["retries"] += 1
    attempts = counters["retries"]
    maximum = limit(state, "max_retry_attempts")
    reason = "artifact_missing" if not exists else "artifact_too_small"

    append_audit(
        paths, state, phase=phase, event="verification_failed",
        message=f"Verification failed for {args.path} "
                f"({'missing' if not exists else f'{size} bytes'}). "
                f"Retry {attempts}/{maximum}.",
        artifact=args.path,
    )
    save_state(paths, state, args.session)

    if attempts >= maximum:
        raise Refused(
            "rate_limit_exceeded",
            f"Retry limit reached: {phase} has failed {attempts}/{maximum} times. "
            "Raise the limit with `limit set --retries <n>`, reset the counter "
            f"with `limit reset --phase {phase} --retries`, `skip` to advance "
            "without a verified artifact, or `restart` this phase.",
            {"phase": phase, "attempts": attempts, "max": maximum,
             "retry_offered": False},
        )

    raise Refused(
        reason,
        f"Verification failed: {args.path} was not created or is too small "
        f"(<{MIN_ARTIFACT_BYTES} bytes). Retry attempt {attempts}/{maximum}.",
        {"path": args.path, "bytes": size, "attempts": attempts, "max": maximum,
         "retry_offered": True},
    )


def cmd_limit_set(args, paths: Paths) -> int:
    """Replaces v1.12's 'edit state.json by hand' instruction with an audited
    command — hand-editing defeats the audit chain this version hardens."""
    state = read_state(paths)
    limits = state.setdefault("rate_limits", {})
    changed = {}
    if args.retries is not None:
        limits["max_retry_attempts"] = args.retries
        changed["max_retry_attempts"] = args.retries
    if args.remediations is not None:
        limits["max_remediation_attempts"] = args.remediations
        changed["max_remediation_attempts"] = args.remediations
    if not changed:
        raise UsageError("nothing_to_set",
                         "Pass --retries and/or --remediations.", {})
    append_audit(
        paths, state, phase=state.get("current_phase", "unknown"),
        event="rate_limit_changed",
        message=f"Rate limits changed: {changed}.",
    )
    save_state(paths, state, args.session)
    emit("limit set", {"rate_limits": limits, "changed": changed})
    return EXIT_OK


def cmd_limit_reset(args, paths: Paths) -> int:
    state = read_state(paths)
    counters = counters_for(state, args.phase)
    cleared = []
    if args.retries:
        counters["retries"] = 0
        cleared.append("retries")
    if args.remediations:
        counters["remediations"] = 0
        cleared.append("remediations")
    if not cleared:
        raise UsageError("nothing_to_reset",
                         "Pass --retries and/or --remediations.", {})
    append_audit(
        paths, state, phase=args.phase, event="counter_reset",
        message=f"Attempt counters reset for {args.phase}: {', '.join(cleared)}.",
    )
    save_state(paths, state, args.session)
    emit("limit reset", {"phase": args.phase, "cleared": cleared,
                         "counters": counters})
    return EXIT_OK


# --------------------------------------------------------------------------
# Checkpoints — crash-recovery idempotency inside a phase
# --------------------------------------------------------------------------


def cmd_checkpoint(args, paths: Paths) -> int:
    state = read_state(paths)
    if args.subcommand == "set":
        state["phase_checkpoint"] = args.value
        save_state(paths, state, args.session)
    elif args.subcommand == "clear":
        state["phase_checkpoint"] = None
        save_state(paths, state, args.session)
    emit(f"checkpoint {args.subcommand}",
         {"checkpoint": state.get("phase_checkpoint")})
    return EXIT_OK


# --------------------------------------------------------------------------
# Confirmations — two-step destructive actions
# --------------------------------------------------------------------------

CONFIRMABLE = {
    "reset", "skip", "implement_dirty_tree", "accept_state_jump",
    "accept_audit_mismatch",
}


def cmd_confirm(args, paths: Paths) -> int:
    state = read_state(paths)
    pending = state.get("pending_confirm_action")

    if args.subcommand == "set":
        state["pending_confirm_action"] = args.action
        save_state(paths, state, args.session)
        emit("confirm set", {"pending": args.action})
        return EXIT_OK

    if args.subcommand == "check":
        matched = pending == args.action
        emit("confirm check", {"pending": pending, "matched": matched},
             ok=matched,
             reason=None if matched else "no_pending_confirmation",
             message=None if matched else
             f"No '{args.action}' confirmation is pending.")
        return EXIT_OK if matched else EXIT_REFUSED

    # clear: the stale-confirmation guard. Any other command cancels a pending
    # confirmation, so one can never fire out of context.
    if pending:
        append_audit(
            paths, state, phase=state.get("current_phase", "unknown"),
            event="confirmation_cancelled",
            message=f'Pending confirmation "{pending}" cancelled '
                    "— new command received.",
        )
        state["pending_confirm_action"] = None
        save_state(paths, state, args.session)
    emit("confirm clear", {"cleared": pending})
    return EXIT_OK


# --------------------------------------------------------------------------
# Remediation
# --------------------------------------------------------------------------

FEEDBACK_FILE = ".specify/sdle-feedback.md"


def cmd_remediate_begin(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    gate_key = args.gate
    execution_phase = consts.gate_to_execution_phase.get(gate_key)
    if not execution_phase:
        raise Refused("unknown_gate", f"'{gate_key}' is not a registered gate.",
                      {"gate": gate_key})

    entry = (state.get("approvals") or {}).get(gate_key) or {}
    feedback = entry.get("comments")
    if entry.get("decision") != "rejected" or not feedback:
        raise Refused(
            "nothing_to_remediate",
            f"{gate_key} has no recorded rejection to remediate.",
            {"gate": gate_key, "decision": entry.get("decision")},
        )

    counters = counters_for(state, execution_phase)
    maximum = limit(state, "max_remediation_attempts")
    if counters["remediations"] >= maximum:
        raise Refused(
            "rate_limit_exceeded",
            f"Remediation limit reached: {execution_phase} has been remediated "
            f"{counters['remediations']}/{maximum} times. Raise the limit with "
            "`limit set --remediations <n>`, reset the counter with "
            f"`limit reset --phase {execution_phase} --remediations`, restart "
            "the phase, or skip.",
            {"phase": execution_phase, "attempts": counters["remediations"],
             "max": maximum},
        )

    counters["remediations"] += 1
    state["status"] = "in_progress"

    feedback_path = paths.project_root / FEEDBACK_FILE
    write_atomic(
        feedback_path,
        f"# SDLE Feedback for {execution_phase} — {now_iso()}\n"
        f"**Gate:** {consts.phase_label.get(require_gate(consts, gate_key))}\n"
        f"**Canonical source:** {paths.runtime_relative}/state.json → "
        f"approvals[{gate_key}].comments\n"
        f"**Reviewer comments:**\n{feedback}\n",
    )
    append_audit(
        paths, state, phase=execution_phase, event="remediation_started",
        message=f"Remediation attempt {counters['remediations']}/{maximum} "
                f"for {execution_phase}.",
        artifact=FEEDBACK_FILE,
    )
    save_state(paths, state, args.session)
    emit("remediate begin", {
        "gate": gate_key, "execution_phase": execution_phase,
        "attempt": counters["remediations"], "max": maximum,
        "feedback_path": FEEDBACK_FILE, "feedback": feedback,
    })
    return EXIT_OK


def cmd_remediate_finish(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    execution_phase = consts.gate_to_execution_phase.get(args.gate)
    source = paths.project_root / FEEDBACK_FILE
    archive = None
    if source.is_file():
        stamp = now_iso().replace(":", "").replace("-", "")
        archive = f".specify/sdle-feedback-archive-{stamp}.md"
        write_atomic(paths.project_root / archive,
                     source.read_text(encoding="utf-8"))
        source.unlink()
    append_audit(
        paths, state, phase=execution_phase or state.get("current_phase", "unknown"),
        event="remediation_complete",
        message=f"Remediation complete for {execution_phase}. Feedback archived.",
        artifact=archive,
    )
    save_state(paths, state, args.session)
    emit("remediate finish",
         {"gate": args.gate, "archive_path": archive,
          "feedback_removed": not source.is_file()})
    return EXIT_OK


# --------------------------------------------------------------------------
# skip / restart / reset
# --------------------------------------------------------------------------


def cmd_skip(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    phase = state.get("current_phase")

    if not args.confirm:
        if state.get("status") != "failed":
            raise Refused(
                "not_failed",
                "`skip` is only valid after a failed step. Current status: "
                f"{state.get('status')}.",
                {"status": state.get("status")},
            )
        state["pending_confirm_action"] = "skip"
        save_state(paths, state, args.session)
        emit("skip", {
            "pending": True, "phase": phase,
            "label": consts.phase_label.get(phase),
            "index": consts.index(phase),
        })
        return EXIT_OK

    if state.get("pending_confirm_action") != "skip":
        raise Refused(
            "no_pending_confirmation",
            "No skip confirmation is pending. Issue `skip` first.",
            {"pending": state.get("pending_confirm_action")},
        )

    state["pending_confirm_action"] = None
    state["current_artifact"] = None
    state["current_artifact_sha"] = None
    append_audit(
        paths, state, phase=phase, event="skipped",
        message=f"⚠️ SKIPPED WITH WARNING: Phase {phase} advanced without a "
                "verified artifact. Downstream phases may fail or produce "
                "incorrect output.",
        decision="SKIPPED",
    )
    target = consts.next_phase.get(phase)
    moved = apply_advance(paths, state, consts, target, "pending", "skipped")
    save_state(paths, state, args.session)
    emit("skip", {"pending": False, **moved,
                  "next_label": consts.phase_label.get(moved["to"])})
    return EXIT_OK


def cmd_restart(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    total = len(consts.phase_sequence) - 1  # `complete` is not restartable

    if not 1 <= args.to <= total:
        raise Refused("invalid_phase_number",
                      f"Invalid phase number. Use 1–{total}.", {"requested": args.to})

    target = consts.phase_at(args.to)
    if target in consts.phase_to_gate_key:
        raise Refused(
            "gate_phase",
            f"Phase {args.to} is a gate phase — restarting a gate is not "
            f"meaningful. Did you mean phase {args.to - 1}?",
            {"target": target, "suggest": args.to - 1},
        )

    current_index = consts.index(state.get("current_phase"))
    if args.to > current_index:
        raise Refused(
            "forward_jump",
            "Forward jumps are not allowed. `restart` is a rollback tool — it "
            "can only go to a phase you have already passed. Current phase: "
            f"{state.get('current_phase')} (index {current_index}). Requested: "
            f"{target} (index {args.to}). To advance, approve the intervening "
            "gates.",
            {"current": state.get("current_phase"), "current_index": current_index,
             "requested": target, "requested_index": args.to},
        )

    cleared = [
        consts.phase_to_gate_key[p]
        for p in consts.gate_phases
        if consts.index(p) >= args.to
    ]

    if not args.confirm:
        state["pending_confirm_action"] = f"restart:{args.to}"
        save_state(paths, state, args.session)
        emit("restart", {"pending": True, "target": target, "index": args.to,
                         "label": consts.phase_label.get(target),
                         "cleared_gates": cleared})
        return EXIT_OK

    if state.get("pending_confirm_action") != f"restart:{args.to}":
        raise Refused(
            "no_pending_confirmation",
            f"No restart confirmation is pending for phase {args.to}. "
            f"Issue `restart --to {args.to}` first.",
            {"pending": state.get("pending_confirm_action")},
        )

    state["pending_confirm_action"] = None
    for gate_key in cleared:
        (state.setdefault("approvals", {}))[gate_key] = None
        (state.setdefault("artifact_shas", {})).pop(gate_key, None)
    before = len(state.get("phase_history") or [])
    state["phase_history"] = [
        entry for entry in (state.get("phase_history") or [])
        if entry.get("phase") in consts.phase_sequence
        and consts.index(entry["phase"]) < args.to
    ]
    trimmed = before - len(state["phase_history"])
    state["drift_queue"] = []
    state["pending_phase"] = None
    state["phase_checkpoint"] = None
    state["current_phase"] = target
    state["status"] = "pending"
    state["progress"] = consts.progress_for(target)

    append_audit(
        paths, state, phase=target, event="restart",
        message=f"Restart: rolled back to Phase {args.to} ({target}). "
                f"Cleared downstream approvals: {', '.join(cleared) or 'none'}. "
                f"phase_history trimmed by {trimmed}.",
    )
    save_state(paths, state, args.session)
    emit("restart", {"pending": False, "target": target, "index": args.to,
                     "label": consts.phase_label.get(target),
                     "cleared_gates": cleared, "trimmed": trimmed})
    return EXIT_OK


def cmd_reset(args, paths: Paths) -> int:
    state = read_state(paths)
    if not args.confirm:
        state["pending_confirm_action"] = "reset"
        save_state(paths, state, args.session)
        emit("reset", {"pending": True})
        return EXIT_OK

    if state.get("pending_confirm_action") != "reset":
        raise Refused(
            "no_pending_confirmation",
            "No workflow reset is pending. Issue `reset` first.",
            {"pending": state.get("pending_confirm_action")},
        )

    deleted = []
    for path in (paths.state_file, paths.audit_file, paths.lock_file):
        if path.is_file():
            path.unlink()
            deleted.append(path.name)
    emit("reset", {"pending": False, "deleted": deleted})
    return EXIT_OK


# --------------------------------------------------------------------------
# doctor — the recovery consistency check
# --------------------------------------------------------------------------


def cmd_doctor(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    current = state.get("current_phase")
    history = state.get("phase_history") or []

    confirmed = [
        e["phase"] for e in history
        if e.get("outcome") in {"approved", "completed"}
        and e.get("phase") in consts.phase_sequence
    ]
    if not confirmed:
        emit("doctor", {"verdict": "ok", "reason": "no phase history yet",
                        "expected": None, "actual": current, "gap": 0})
        return EXIT_OK

    last = confirmed[-1]
    expected = consts.next_phase.get(last) or last
    gap = consts.index(current) - consts.index(expected)

    if gap < 0:
        verdict = "backwards"
    elif gap > 2:
        verdict = "jump"
    else:
        verdict = "ok"

    data = {"verdict": verdict, "last_confirmed": last, "expected": expected,
            "actual": current, "gap": gap}
    if verdict == "ok":
        emit("doctor", data)
        return EXIT_OK

    if verdict == "backwards":
        message = (
            "State inconsistency: current_phase is earlier than history "
            f"suggests. Last confirmed: {last}. Expected: {expected}. "
            f"Actual: {current}."
        )
    else:
        state["pending_confirm_action"] = "accept_state_jump"
        save_state(paths, state, args.session)
        message = (
            f"State jump detected: current_phase is {gap} phases ahead of last "
            f"confirmed history. Current: {current}. Expected: {expected}. "
            "Unapproved gates between them will not be enforced retroactively."
        )
    emit("doctor", data, ok=False, reason=f"state_{verdict}", message=message)
    print(message, file=sys.stderr)
    return EXIT_REFUSED


def cmd_accept_state(args, paths: Paths) -> int:
    state = read_state(paths)
    if state.get("pending_confirm_action") != "accept_state_jump":
        raise Refused("no_pending_confirmation",
                      "No state jump is pending acknowledgement.",
                      {"pending": state.get("pending_confirm_action")})
    state["pending_confirm_action"] = None
    append_audit(
        paths, state, phase=state.get("current_phase", "unknown"),
        event="state_jump_accepted",
        message=f"User acknowledged state jump to {state.get('current_phase')}.",
    )
    save_state(paths, state, args.session)
    emit("accept-state", {"current_phase": state.get("current_phase")})
    return EXIT_OK


# --------------------------------------------------------------------------
# repo-staleness — scoped to recorded artifact paths
# --------------------------------------------------------------------------


def cmd_repo_staleness(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    approvals = state.get("approvals") or {}
    stamps = [
        entry["timestamp"] for entry in approvals.values()
        if isinstance(entry, dict) and entry.get("decision") == "approved"
        and entry.get("timestamp")
    ]
    if not stamps or not git_available(paths):
        emit("repo-staleness", {"stale": False, "newest_approval": None,
                                "newest_commit": None, "paths": [],
                                "reason": "no approvals or git unavailable"})
        return EXIT_OK

    newest_approval = max(stamps)
    approval_dt = parse_iso(newest_approval)

    # Scope to the paths of recorded artifacts rather than the whole repo: a
    # commit touching unrelated files does not make an approval stale.
    tracked = []
    for gate_key in consts.artifact_ownership:
        resolved, _ = resolve_artifact_path(state, consts, gate_key, paths)
        if resolved:
            tracked.append(resolved)
    tracked = sorted(set(tracked))

    args_list = ["log", "-1", "--format=%cI"]
    if tracked:
        args_list += ["--", *tracked]
    code, newest_commit = git(paths, *args_list)
    # Compare instants, not strings: git reports a local offset (+04:00) while
    # approvals are recorded in Z, so lexical comparison is simply wrong.
    commit_dt = parse_iso(newest_commit) if code == 0 else None
    stale = bool(commit_dt and approval_dt and commit_dt > approval_dt)

    emit("repo-staleness", {
        "stale": stale, "newest_approval": newest_approval,
        "newest_commit": newest_commit or None, "paths": tracked,
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# Untrusted content scan
# --------------------------------------------------------------------------

INJECTION_PATTERNS = [
    ("ignore_previous_instructions", r"ignore (all|previous|prior).{0,20}instructions"),
    ("disregard_rules", r"disregard.{0,30}(instructions|rules|gates)"),
    ("you_are_now", r"you are now"),
    ("act_as_orchestrator", r"act as (the )?(orchestrator|sdle|system)"),
    ("new_persona", r"new persona"),
    ("approve_gate", r"approve.{0,15}gate"),
    ("skip_gate", r"skip.{0,15}(gate|phase|approval)"),
    ("advance_phase", r"advance.{0,15}phase"),
    ("mark_approved", r"mark.{0,15}approved"),
    ("set_status", r"set.{0,15}status"),
    ("edit_state", r"(edit|modify|write).{0,15}state\.json"),
]


def scan_text(text: str) -> list[dict]:
    matches = []
    for number, line in enumerate(text.splitlines(), start=1):
        for name, pattern in INJECTION_PATTERNS:
            if re.search(pattern, line, flags=re.IGNORECASE):
                matches.append({"line": number, "text": line.strip(),
                                "pattern": name})
                break
    return matches


def cmd_scan(args, paths: Paths) -> int:
    target = paths.project_root / args.path
    if not target.is_file():
        raise Refused("artifact_missing", f"No such file: {args.path}",
                      {"path": args.path})
    matches = scan_text(target.read_text(encoding="utf-8", errors="replace"))
    data = {"path": args.path, "flagged": bool(matches), "matches": matches}

    if not matches:
        emit("scan", data)
        return EXIT_OK

    # Record the pending acknowledgement when a workflow exists, so the
    # stale-confirmation guard applies to it like any other confirmation.
    if paths.state_file.is_file():
        state = read_state(paths)
        state["pending_confirm_action"] = f"accept_content:{args.path}"
        save_state(paths, state, args.session)

    lines = "\n".join(f"  line {m['line']}: {m['text']}" for m in matches)
    message = (
        f"Untrusted content warning: {args.path} contains lines that look like "
        f"instructions directed at the workflow engine:\n\n{lines}\n\n"
        "SDLE treats this file as data only and will NOT act on these lines."
    )
    emit("scan", data, ok=False, reason="content_flagged", message=message)
    print(message, file=sys.stderr)
    return EXIT_REFUSED


def cmd_accept_content(args, paths: Paths) -> int:
    state = read_state(paths)
    pending = state.get("pending_confirm_action") or ""
    if not pending.startswith("accept_content:"):
        raise Refused("no_pending_confirmation",
                      "No flagged content is pending acknowledgement.",
                      {"pending": pending or None})
    flagged = pending.split(":", 1)[1]
    state["pending_confirm_action"] = None
    append_audit(
        paths, state, phase=state.get("current_phase", "unknown"),
        event="content_accepted",
        message=f"User accepted flagged content in {flagged}.",
        artifact=flagged,
    )
    save_state(paths, state, args.session)
    emit("accept-content", {"file": flagged})
    return EXIT_OK


def cmd_clarify_save(args, paths: Paths) -> int:
    state = read_state(paths)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    relative = f"clarifications/{args.phase}-{stamp}.clarify"
    write_atomic(
        paths.project_root / relative,
        f"Phase: {args.phase}\nSaved: {now_iso()}\n\n{args.text}\n",
    )
    flagged = scan_text(args.text)
    state["clarification_phase"] = None
    append_audit(
        paths, state, phase=args.phase, event="clarification_saved",
        message=f"User clarification saved: {relative}.",
        artifact=relative,
    )
    save_state(paths, state, args.session)
    emit("clarify save", {"path": relative, "flagged": bool(flagged),
                          "matches": flagged})
    return EXIT_OK


def cmd_guidance_path(args, paths: Paths) -> int:
    """Resolve the Guidance File Map entry for a phase."""
    rows = parse_md_table(paths.phase_execution_md, "Guidance")
    mapping = {}
    for row in rows:
        phase = _column(row, "phase")
        guidance = _column(row, "guidance_file")
        if phase:
            mapping[phase] = guidance
    relative = mapping.get(args.phase)
    emit("guidance path", {
        "phase": args.phase, "path": relative,
        "exists": bool(relative and (paths.project_root / relative).is_file()),
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# Implement phase
# --------------------------------------------------------------------------

SDLE_OWNED_PREFIXES = (
    ".workflow/", "workitems/", ".specify/", "design/", "reviews/",
    "clarifications/", "guidance/", "requirements/",
)


def cmd_implement_preflight(args, paths: Paths) -> int:
    state = read_state(paths)

    if not git_available(paths):
        state["implementation_base_ref"] = None
        save_state(paths, state, args.session)
        emit("implement preflight",
             {"dirty": False, "entries": [], "base_ref": None,
              "skipped": "git not initialized"})
        return EXIT_OK

    # Pin the diff range for Phase 17 before any code is written.
    _, head = git(paths, "rev-parse", "HEAD")
    state["implementation_base_ref"] = head or None

    # -uall: without it git collapses an untracked directory to "?? src/",
    # and every file inside it escapes both the dirty-tree guard and the
    # secrets scan.
    _, status = git(paths, "status", "--short", "-uall")
    entries = [
        line for line in status.splitlines()
        if line.strip()
        and not any(line[3:].strip().replace("\\", "/").startswith(prefix)
                    for prefix in SDLE_OWNED_PREFIXES)
    ]

    if entries and not args.bypass:
        state["pending_confirm_action"] = "implement_dirty_tree"
        append_audit(
            paths, state, phase="implement", event="dirty_tree_guard",
            message=f"Dirty-tree guard triggered before implement. "
                    f"{len(entries)} uncommitted entries.",
        )
        save_state(paths, state, args.session)
        raise Refused(
            "dirty_tree",
            "Uncommitted changes detected in the working tree:\n\n"
            + "\n".join(f"  {e}" for e in entries)
            + "\n\nThese may be mixed into or overwritten by the "
            "implementation, and will appear in the implementation manifest "
            "as if the implementation produced them. Commit or stash them "
            "first, or confirm to proceed anyway (logged).",
            {"entries": entries, "base_ref": state["implementation_base_ref"]},
        )

    if entries and args.bypass:
        state["pending_confirm_action"] = None
        append_audit(
            paths, state, phase="implement", event="dirty_tree_bypassed",
            message=f"Proceeding with implement despite {len(entries)} "
                    "uncommitted entries (user confirmed).",
        )

    save_state(paths, state, args.session)
    emit("implement preflight",
         {"dirty": bool(entries), "entries": entries,
          "base_ref": state["implementation_base_ref"], "bypassed": args.bypass})
    return EXIT_OK


SECRET_PATTERNS = [
    ("AWS access key", r"AKIA[0-9A-Z]{16}"),
    ("private key material", r"-----BEGIN [A-Z ]*PRIVATE KEY"),
    ("GitHub token", r"ghp_[A-Za-z0-9]{36}"),
    # v1.12 used sk-[A-Za-z0-9]{20,}, which misses the current sk-proj-...
    # format: the hyphen ends the character class four characters in.
    ("secret API key", r"sk-[A-Za-z0-9_-]{20,}"),
    ("hardcoded credential assignment",
     r"(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*['\"][^'\"]{8,}"),
    ("bearer token", r"Bearer [A-Za-z0-9\-_.]{20,}"),
]

TEXT_SUFFIXES = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".rb", ".rs", ".php",
    ".cs", ".c", ".h", ".cpp", ".sh", ".ps1", ".yml", ".yaml", ".json", ".toml",
    ".ini", ".cfg", ".env", ".md", ".txt", ".sql", ".html", ".css",
}


def detect_test_runner(paths: Paths) -> tuple[str, list[str]] | None:
    """Find a runner we can actually execute. Item 11: an implementation whose
    tests never ran must not reach Gate 7 unchallenged."""
    root = paths.project_root
    package = root / "package.json"
    if package.is_file():
        try:
            data = json.loads(package.read_text(encoding="utf-8"))
            if (data.get("scripts") or {}).get("test"):
                return "npm test", ["npm", "test", "--silent"]
        except (json.JSONDecodeError, OSError):
            pass
    if (root / "pytest.ini").is_file() or (root / "tests").is_dir() or (
        (root / "pyproject.toml").is_file()
        and "pytest" in (root / "pyproject.toml").read_text(
            encoding="utf-8", errors="replace")
    ):
        return "pytest", [sys.executable, "-m", "pytest", "-q"]
    if (root / "Cargo.toml").is_file():
        return "cargo test", ["cargo", "test", "--quiet"]
    if (root / "pom.xml").is_file():
        return "mvn test", ["mvn", "-q", "test"]
    if (root / "build.gradle").is_file() or (root / "build.gradle.kts").is_file():
        return "gradle test", ["gradle", "test", "--quiet"]
    return None


def run_tests(paths: Paths, timeout: int) -> dict:
    detected = detect_test_runner(paths)
    if not detected:
        return {"runner": None, "exit_code": None, "output": None,
                "status": "no runner detected"}
    name, command = detected
    try:
        completed = subprocess.run(
            command, cwd=str(paths.project_root), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except FileNotFoundError:
        return {"runner": name, "exit_code": None, "output": None,
                "status": "runner not installed"}
    except subprocess.TimeoutExpired:
        return {"runner": name, "exit_code": None, "output": None,
                "status": f"timed out after {timeout}s"}
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    tail = "\n".join(output.splitlines()[-40:])
    return {
        "runner": name,
        "exit_code": completed.returncode,
        "output": tail,
        "status": "passed" if completed.returncode == 0 else "FAILED",
    }


def cmd_manifest_build(args, paths: Paths) -> int:
    state = read_state(paths)
    relative = str(
        paths.manifest_file.relative_to(paths.project_root)
    ).replace(os.sep, "/")

    if git_available(paths):
        # -uall: without it git collapses an untracked directory to "?? src/",
        # and every file inside it escapes the secrets scan entirely.
        _, status = git(paths, "status", "--short", "-uall")
        _, tracked = git(paths, "diff", "--name-only", "HEAD")
        files = {line[3:].strip() for line in status.splitlines() if line.strip()}
        files |= {line.strip() for line in tracked.splitlines() if line.strip()}
        note = None
    else:
        files = {
            str(p.relative_to(paths.project_root)).replace(os.sep, "/")
            for p in paths.project_root.rglob("*")
            if p.is_file() and p.suffix in TEXT_SUFFIXES
            and not str(p.relative_to(paths.project_root)).startswith(".")
        }
        note = "git not initialized — file list is approximate."

    # The runtime directory is engine-owned bookkeeping, never implementation.
    # Only the runtime is excluded here — widening this to SDLE_OWNED_PREFIXES
    # would silently drop requirements/ and design/ edits from the manifest.
    runtime_prefix = paths.runtime_relative + "/"
    changed = sorted(
        f for f in files
        if not f.replace("\\", "/").startswith(runtime_prefix)
    )

    findings = []
    for name in changed:
        candidate = paths.project_root / name
        if not candidate.is_file() or candidate.suffix not in TEXT_SUFFIXES:
            continue
        try:
            body = candidate.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, line in enumerate(body.splitlines(), start=1):
            for label, pattern in SECRET_PATTERNS:
                found = re.search(pattern, line)
                if found:
                    masked = found.group(0)[:4] + " ****(masked)"
                    findings.append(f"{name}:{number} — {label} — {masked}")
                    break

    tests = run_tests(paths, args.test_timeout) if not args.skip_tests else {
        "runner": None, "exit_code": None, "output": None,
        "status": "skipped by caller",
    }

    secrets_block = "\n".join(findings) if findings else "None detected."
    if tests["runner"] is None:
        tests_block = f"No test runner detected ({tests['status']})."
    else:
        tests_block = (
            f"Runner: {tests['runner']}\n"
            f"Result: {tests['status']}"
            + (f" (exit {tests['exit_code']})" if tests["exit_code"] is not None
               else "")
            + (f"\n\n```\n{tests['output']}\n```" if tests["output"] else "")
        )

    body = (
        "# Implementation Manifest\n"
        f"Generated: {now_iso()}\n"
        f"Phase: implement ({state.get('progress', '15/18')})\n"
        + (f"\n> {note}\n" if note else "")
        + "\n## Changed/Added Files\n"
        + ("\n".join(changed) if changed else "(none)")
        + "\n\n## Potential Secrets Detected\n"
        + secrets_block
        + "\n\n## Test Evidence\n"
        + tests_block
        + "\n\n## Summary\n"
        + (args.summary or "Implementation produced the files listed above.")
        + "\n"
    )
    write_atomic(paths.manifest_file, body)

    if findings:
        append_audit(
            paths, state, phase="implement", event="secrets_flagged",
            message=f"⚠️ Secrets scan flagged {len(findings)} potential "
                    "secret(s) in the implementation diff.",
        )
    if tests["runner"] and tests["exit_code"] not in (0, None):
        append_audit(
            paths, state, phase="implement", event="tests_failed",
            message=f"Test evidence: {tests['runner']} FAILED "
                    f"(exit {tests['exit_code']}).",
        )
    state["current_artifact"] = relative
    save_state(paths, state, args.session)

    emit("manifest build", {
        "path": relative, "files": changed, "secrets": findings, "tests": tests,
    })
    return EXIT_OK


def cmd_security_review_evidence(args, paths: Paths) -> int:
    state = read_state(paths)
    base = state.get("implementation_base_ref")
    if not git_available(paths):
        emit("security-review evidence",
             {"base_ref": None, "stat": None, "diff": None, "artifacts": [],
              "note": "Git not available — diff analysis skipped."})
        return EXIT_OK

    ref = base or "HEAD~1"
    _, stat = git(paths, "diff", "--stat", ref)
    _, diff = git(
        paths, "diff", ref, "--", ".", ":(exclude).specify",
        f":(exclude){paths.runtime_relative}",
    )

    feature = state.get("current_feature_id")
    candidates = [".specify/memory/constitution.md"]
    if feature:
        candidates += [
            f".specify/specs/{feature}/{name}.md"
            for name in ("spec", "plan", "tasks")
        ]
    present = [c for c in candidates if (paths.project_root / c).is_file()]

    emit("security-review evidence", {
        "base_ref": ref,
        "pinned": bool(base),
        "stat": stat or None,
        "diff": diff or None,
        "artifacts": present,
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# preflight
# --------------------------------------------------------------------------


def cmd_preflight(args, paths: Paths) -> int:
    root = paths.project_root
    problems = []

    speckit_present = (root / ".specify").is_dir()
    if not speckit_present:
        problems.append("speckit_missing")

    prefix = None
    probes = [
        (root / ".claude" / "skills" / "speckit-constitution" / "SKILL.md", "speckit-"),
        (root / ".claude" / "skills" / "speckit.constitution" / "SKILL.md", "speckit."),
        (Path.home() / ".claude" / "skills" / "speckit-constitution" / "SKILL.md",
         "speckit-"),
        (Path.home() / ".claude" / "skills" / "speckit.constitution" / "SKILL.md",
         "speckit."),
    ]
    for probe, candidate in probes:
        if probe.is_file():
            prefix = candidate
            break
    if speckit_present and prefix is None:
        problems.append("speckit_skills_missing")

    req_dir = root / "requirements"
    requirements = sorted(p.name for p in req_dir.glob("*")) if req_dir.is_dir() else []
    if not requirements:
        problems.append("requirements_missing")

    guidance_dir = root / "guidance"
    guidance = (
        sorted(p.name for p in guidance_dir.glob("*.md"))
        if guidance_dir.is_dir() else []
    )

    # Persist the discovered prefix so the orchestrator does not have to
    # re-probe, and does not have to write state itself to record it.
    if prefix and paths.state_file.is_file():
        state = read_state(paths)
        if state.get("speckit_skill_prefix") != prefix:
            state["speckit_skill_prefix"] = prefix
            save_state(paths, state, args.session)

    data = {
        "speckit_present": speckit_present,
        "skill_prefix": prefix,
        "requirements": requirements,
        "guidance": guidance,
        "interpreter": sys.executable,
        "python_version": ".".join(str(v) for v in sys.version_info[:3]),
        "script_reachable": True,
        "problems": problems,
    }

    if problems:
        messages = {
            "speckit_missing": "SDLE requires SpecKit to be initialized in this "
            "project. Run: uvx --from git+https://github.com/github/spec-kit.git "
            "specify init . --skills --here",
            "speckit_skills_missing": "SDLE cannot locate SpecKit skills. "
            "Re-initialize SpecKit with --skills.",
            "requirements_missing": "I need requirements before starting the "
            "workflow. Create a `requirements/` folder and add at least one "
            "document.",
        }
        first = problems[0]
        emit("preflight", data, ok=False, reason=first, message=messages[first])
        print(messages[first], file=sys.stderr)
        return EXIT_REFUSED

    emit("preflight", data)
    return EXIT_OK


# --------------------------------------------------------------------------
# Output envelope
# --------------------------------------------------------------------------


def emit(command: str, data: dict, ok: bool = True, reason: str | None = None,
         message: str | None = None) -> None:
    payload = {"ok": ok, "command": command, "reason": reason, "data": data}
    if message is not None:
        payload["message"] = message
    json.dump(payload, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")


# --------------------------------------------------------------------------
# lint-skill
# --------------------------------------------------------------------------


@dataclass
class Check:
    name: str
    passed: bool
    message: str

    def as_dict(self) -> dict:
        return {"name": self.name, "passed": self.passed, "message": self.message}


def check_tables_wellformed(paths: Paths) -> tuple[list[Check], Constants | None]:
    """Runs first and short-circuits: nothing else is meaningful if the
    constants did not parse."""
    try:
        consts = load_constants(paths)
    except SdleError as exc:
        return [Check("tables_wellformed", False, exc.message)], None
    return (
        [
            Check(
                "tables_wellformed",
                True,
                f"Parsed {len(consts.phase_sequence)} phases, "
                f"{len(consts.phase_to_gate_key)} gates, "
                f"{len(consts.version_chain)} migration rows.",
            )
        ],
        consts,
    )


def cmd_lint_skill(args, paths: Paths) -> int:
    checks, consts = check_tables_wellformed(paths)
    if consts is not None:
        checks.extend(run_sync_checks(paths, consts))

    failed = [c.name for c in checks if not c.passed]
    for check in checks:
        mark = "PASS" if check.passed else "FAIL"
        print(f"[{mark}] {check.name}: {check.message}", file=sys.stderr)

    emit(
        "lint-skill",
        {"checks": [c.as_dict() for c in checks], "failed": failed},
        ok=not failed,
        reason="lint_failed" if failed else None,
    )
    return EXIT_REFUSED if failed else EXIT_OK


def run_sync_checks(paths: Paths, consts: Constants) -> list[Check]:
    """Cross-file sync rules. Grows as the wave proceeds."""
    checks: list[Check] = []

    # Phase tables must cover an identical phase set.
    seq = set(consts.phase_sequence)
    for name, keys in (
        ("NEXT_PHASE", set(consts.next_phase)),
        ("PHASE_LABEL_MAP", set(consts.phase_label)),
        ("PROGRESS_MAP", set(consts.progress)),
    ):
        missing = sorted(seq - keys)
        extra = sorted(keys - seq)
        checks.append(
            Check(
                f"phase_set_matches_{name.lower()}",
                not missing and not extra,
                "identical to PHASE_SEQUENCE"
                if not missing and not extra
                else f"missing={missing} unexpected={extra}",
            )
        )

    # NEXT_PHASE must chain PHASE_SEQUENCE exactly once, ending terminal.
    chain_ok, chain_msg = True, "chains PHASE_SEQUENCE in order"
    for position, phase in enumerate(consts.phase_sequence):
        expected = (
            consts.phase_sequence[position + 1]
            if position + 1 < len(consts.phase_sequence)
            else None
        )
        actual = consts.next_phase.get(phase)
        if actual != expected:
            chain_ok = False
            chain_msg = f"{phase} -> {actual!r}, expected {expected!r}"
            break
    checks.append(Check("next_phase_chains_sequence", chain_ok, chain_msg))

    # PROGRESS_MAP denominators all equal the phase count.
    denominators = {
        value.split("/")[-1] for value in consts.progress.values() if "/" in value
    }
    expected_denominator = str(consts.phase_count)
    checks.append(
        Check(
            "progress_denominator_matches_phase_count",
            denominators == {expected_denominator},
            f"denominators={sorted(denominators)} expected={{{expected_denominator}}}",
        )
    )

    # Every gate is registered everywhere a gate must be registered.
    template_keys: set[str] = set()
    if paths.state_template.is_file():
        template = json.loads(paths.state_template.read_text(encoding="utf-8"))
        template_keys = set(template.get("approvals", {}))
    for gate_phase in consts.gate_phases:
        key = consts.phase_to_gate_key[gate_phase]
        problems = []
        if key not in consts.artifact_ownership:
            problems.append("ARTIFACT_OWNERSHIP")
        if key not in consts.gate_to_execution_phase:
            problems.append("GATE_TO_EXECUTION_PHASE")
        if template_keys and key not in template_keys:
            problems.append("templates/state.json approvals")
        checks.append(
            Check(
                f"gate_registered_{key}",
                not problems,
                "registered everywhere" if not problems else f"missing from {problems}",
            )
        )

    # Every phase in PHASE_SEQUENCE has a block in phase-execution.md, keyed by
    # its block header rather than an incidental mention. ``requirements_check``
    # is bootstrap (SKILL.md Step 2) and ``complete`` is terminal.
    exec_text = (
        paths.phase_execution_md.read_text(encoding="utf-8")
        if paths.phase_execution_md.is_file()
        else ""
    )
    declared = set(
        re.findall(r"^\*\*Phase \d+ — `([a-z_]+)`", exec_text, flags=re.MULTILINE)
    )
    exempt = {"requirements_check", "complete"}
    missing_blocks = [
        phase
        for phase in consts.phase_sequence
        if phase not in exempt and phase not in declared
    ]
    checks.append(
        Check(
            "every_phase_has_execution_block",
            not missing_blocks,
            "all present" if not missing_blocks else f"missing={missing_blocks}",
        )
    )

    checks.append(_check_single_state_template(paths))
    checks.append(_check_version_consistency(paths))
    checks.append(_check_migration_covers_state_fields(paths, consts))
    checks.append(_check_no_powershell(paths))
    checks.append(_check_no_hardcoded_progress(paths, consts))
    checks.extend(_check_doc_phase_tables(paths, consts))
    return checks


REPO_DOCS = ("README.md", "docs/SDLE-Reference-Guide.md")


def _skill_files(paths: Paths) -> list[Path]:
    return [
        p for p in (
            paths.skill_md,
            paths.phase_execution_md,
            paths.gate_protocol_md,
            paths.security_review_md,
        ) if p.is_file()
    ]


def _repo_root(paths: Paths) -> Path:
    """The source repo, when the skill lives inside one."""
    candidate = paths.skill_root.parent.parent.parent
    return candidate if (candidate / "README.md").is_file() else paths.project_root


def _check_single_state_template(paths: Paths) -> Check:
    """The template must exist in exactly one place.

    v1.12 kept a second copy embedded in SKILL.md Step 9 and the two had
    already diverged (project_name and last_updated). One fact, one file.
    """
    if not paths.state_template.is_file():
        return Check("single_state_template", False,
                     "templates/state.json is missing")
    text = paths.skill_md.read_text(encoding="utf-8")
    if re.search(r'"workflow_version"\s*:\s*"', text):
        return Check(
            "single_state_template", False,
            "SKILL.md embeds a second copy of the state template; "
            "templates/state.json must be the only host",
        )
    return Check("single_state_template", True,
                 "templates/state.json is the only host")


def _check_version_consistency(paths: Paths) -> Check:
    """One version string, four documents."""
    template = json.loads(paths.state_template.read_text(encoding="utf-8"))
    version = template.get("workflow_version")
    found: dict[str, str | None] = {"templates/state.json": version}

    skill = paths.skill_md.read_text(encoding="utf-8")
    frontmatter = re.search(r"Lifecycle Engine v([0-9]+\.[0-9]+)", skill)
    heading = re.search(r"^# SDLE.*\(v([0-9]+\.[0-9]+)\)", skill, re.MULTILINE)
    found["SKILL.md frontmatter"] = frontmatter.group(1) if frontmatter else None
    found["SKILL.md heading"] = heading.group(1) if heading else None

    root = _repo_root(paths)
    readme = root / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        title = re.search(r"^# SDLE.*\(v([0-9]+\.[0-9]+)\)", text, re.MULTILINE)
        row = re.search(r"\*\*v([0-9]+\.[0-9]+)\*\*", text)
        found["README title"] = title.group(1) if title else None
        found["README version table"] = row.group(1) if row else None

    guide = root / "docs" / "SDLE-Reference-Guide.md"
    if guide.is_file():
        header = re.search(r"SDLE v([0-9]+\.[0-9]+)",
                           guide.read_text(encoding="utf-8"))
        found["Reference Guide header"] = header.group(1) if header else None

    mismatched = {k: v for k, v in found.items() if v != version}
    return Check(
        "version_string_consistent",
        not mismatched,
        f"all four locations report v{version}" if not mismatched
        else f"expected v{version}, found {mismatched}",
    )


def _check_migration_covers_state_fields(paths: Paths, consts: Constants) -> Check:
    """Every field in the template is introduced by the chain.

    Without this, a new state field ships with no upgrade path and older
    state.json files break on load.
    """
    template = json.loads(paths.state_template.read_text(encoding="utf-8"))
    rows = parse_md_table(paths.skill_md, "VERSION_MIGRATION")
    actions = " ".join((_column(r, "action") or "") for r in rows)

    base = {
        "workflow_version", "project_name", "current_phase", "status",
        "progress", "current_artifact", "speckit_initialized", "phase_history",
        "approvals",
    }
    missing = [
        key for key in template
        if key not in base and key not in actions
    ]
    return Check(
        "migration_covers_every_state_field",
        not missing,
        "every field has a migration row" if not missing
        else f"no migration row introduces {missing}",
    )


POWERSHELL_ONLY = (
    "Get-FileHash", "New-Item -ItemType", "Get-ChildItem", "Set-Content",
    "Out-File", "%USERPROFILE%", "Get-Content",
)


def _check_no_powershell(paths: Paths) -> Check:
    """Prompt files must not embed Windows-only commands.

    They are what blocked Linux, macOS and CI. The engine is cross-platform
    now; the prose has to be too.
    """
    offenders = []
    for path in _skill_files(paths):
        text = path.read_text(encoding="utf-8")
        for cmdlet in POWERSHELL_ONLY:
            if cmdlet in text:
                offenders.append(f"{path.name}:{cmdlet}")
    return Check(
        "no_powershell_only_cmdlets",
        not offenders,
        "none found" if not offenders else f"found {offenders}",
    )


def _check_no_hardcoded_progress(paths: Paths, consts: Constants) -> Check:
    """No literal 'N/18' in orchestrator instructions.

    Scoped to instruction text: artifact body templates legitimately contain
    a progress string, because SDLE writes it into the artifact.
    """
    denominator = consts.phase_count
    pattern = re.compile(rf"\b\d+/{denominator}\b")
    offenders = []
    for path in _skill_files(paths):
        in_fence = False
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(),
                                      start=1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue  # artifact template bodies live in fences
            if path.name == "SKILL.md" and "|" in line and "PROGRESS" not in line:
                # PROGRESS_MAP itself is the one legitimate home.
                if re.match(r"^\|\s*`?[a-z_]+`?\s*\|\s*\d+/\d+\s*\|", line.strip()):
                    continue
            if pattern.search(line):
                offenders.append(f"{path.name}:{number}")
    return Check(
        "no_hardcoded_progress_outside_progress_map",
        not offenders,
        "none found" if not offenders else f"found {offenders}",
    )


def _check_doc_phase_tables(paths: Paths, consts: Constants) -> list[Check]:
    """README and the Reference Guide restate the phase list for humans.

    They are derived views, so they are allowed to exist — but they must
    agree with PHASE_SEQUENCE.
    """
    checks = []
    root = _repo_root(paths)
    for relative in REPO_DOCS:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        missing = [
            phase for phase in consts.phase_sequence
            if phase != "complete" and f"`{phase}`" not in text
            and phase not in text
        ]
        checks.append(
            Check(
                f"doc_lists_every_phase_{Path(relative).stem}",
                not missing,
                "all phases present" if not missing else f"missing={missing}",
            )
        )
    return checks


# --------------------------------------------------------------------------
# Simple subcommands
# --------------------------------------------------------------------------


def cmd_sha(args, paths: Paths) -> int:
    target = Path(args.path)
    if not target.is_absolute():
        target = paths.project_root / target
    if not target.is_file():
        raise Refused(
            "artifact_missing", f"No such file: {args.path}", {"path": args.path}
        )
    emit("sha", {"path": args.path, "sha256": sha256_file(target)})
    return EXIT_OK


def cmd_constants(args, paths: Paths) -> int:
    """Diagnostic: dump what was parsed out of SKILL.md."""
    consts = load_constants(paths)
    emit(
        "constants",
        {
            "phase_sequence": consts.phase_sequence,
            "phase_count": consts.phase_count,
            "next_phase": consts.next_phase,
            "phase_to_gate_key": consts.phase_to_gate_key,
            "gate_number": consts.gate_number,
            "gate_phases": consts.gate_phases,
            "artifact_ownership": consts.artifact_ownership,
            "phase_label": consts.phase_label,
            "progress": consts.progress,
            "gate_to_execution_phase": consts.gate_to_execution_phase,
            "version_chain": [list(pair) for pair in consts.version_chain],
            "skill_root": str(paths.skill_root),
            "project_root": str(paths.project_root),
        },
    )
    return EXIT_OK


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sdle",
        description="SDLE deterministic core. JSON on stdout, text on stderr.",
    )
    parser.add_argument("--project-root", help="Target project (default: cwd).")
    parser.add_argument("--skill-root", help="Directory holding SKILL.md.")
    parser.add_argument(
        "--workitem",
        help="Active WorkItem id. Required when more than one is registered.",
    )
    parser.add_argument(
        "--session",
        help="Conversation session token; refreshes the WorkItem lock on write.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sub = subparsers.add_parser("lint-skill", help="Verify cross-file sync rules.")
    sub.set_defaults(handler=cmd_lint_skill)

    sub = subparsers.add_parser(
        "init", help="Create the WorkItem runtime and initial state."
    )
    sub.add_argument("--project", help="Project name (default: infer from heading).")
    sub.set_defaults(handler=cmd_init)

    sub = subparsers.add_parser("header", help="Render the status assertion header.")
    sub.set_defaults(handler=cmd_header)

    sub = subparsers.add_parser("migrate", help="Apply the version migration chain.")
    sub.set_defaults(handler=cmd_migrate)

    sub = subparsers.add_parser(
        "migrate-workflow",
        help="Move a legacy .workflow/ runtime under a WorkItem.",
    )
    # Distinct dest so `--workitem` works on either side of the subcommand:
    # argparse would otherwise clobber the global value with this one's default.
    sub.add_argument("--workitem", dest="migrate_workitem",
                     help="Target WorkItem id (required, must be registered).")
    sub.set_defaults(handler=cmd_migrate_workflow)

    workitem_p = subparsers.add_parser("workitem", help="WorkItem identity.")
    workitem_sub = workitem_p.add_subparsers(dest="subcommand", required=True)
    wi_create = workitem_sub.add_parser(
        "create", help="Create an immutable WorkItem identity."
    )
    wi_create.add_argument("--name", required=True, help="Raw WorkItem name.")
    wi_create.add_argument("--type", help="Classification (default: enhancement).")
    wi_create.add_argument("--synopsis", help="One-line summary.")
    wi_create.add_argument(
        "--auto-generate", action="store_true",
        help="Mint WI-<name>-<UTC timestamp> instead of using the name as the id.",
    )
    wi_create.set_defaults(handler=cmd_workitem_create)
    wi_list = workitem_sub.add_parser("list", help="List registered WorkItems.")
    wi_list.set_defaults(handler=cmd_workitem_list)

    state_p = subparsers.add_parser("state", help="Read workflow state.")
    state_sub = state_p.add_subparsers(dest="subcommand", required=True)
    got = state_sub.add_parser("get", help="Full state, or one field.")
    got.add_argument("--field")
    got.set_defaults(handler=cmd_state_get)
    dumped = state_sub.add_parser("dump", help="Render the full status dump.")
    dumped.set_defaults(handler=cmd_state_dump)
    setter = state_sub.add_parser(
        "set", help="Set an orchestrator-settable field (audited)."
    )
    setter.add_argument("--field", required=True, choices=sorted(SETTABLE_FIELDS))
    setter.add_argument("--value")
    setter.set_defaults(handler=cmd_state_set)

    subparsers.add_parser(
        "retry", help="Guarded retry: refuses while drift re-approval is pending."
    ).set_defaults(handler=cmd_retry)

    audit_p = subparsers.add_parser("audit", help="Append-only audit ledger.")
    audit_sub = audit_p.add_subparsers(dest="subcommand", required=True)
    appended = audit_sub.add_parser("append", help="Append a chained entry.")
    appended.add_argument("--phase", required=True)
    appended.add_argument("--event", required=True)
    appended.add_argument("--message", required=True)
    appended.add_argument("--artifact")
    appended.add_argument("--decision")
    appended.set_defaults(handler=cmd_audit_append)
    verified = audit_sub.add_parser("verify", help="Walk and verify the chain.")
    verified.set_defaults(handler=cmd_audit_verify)
    rebased = audit_sub.add_parser(
        "rebaseline", help="Acknowledge a mismatch and re-baseline (logged)."
    )
    rebased.set_defaults(handler=cmd_audit_rebaseline)

    sub = subparsers.add_parser("advance", help="Move to the next phase.")
    sub.add_argument("--to", required=True, help="Target phase id.")
    sub.add_argument("--status", help="Override the derived status.")
    sub.add_argument("--outcome", help="phase_history outcome (default: completed).")
    sub.set_defaults(handler=cmd_advance)

    gate_p = subparsers.add_parser("gate", help="Approval gates.")
    gate_sub = gate_p.add_subparsers(dest="subcommand", required=True)
    shown = gate_sub.add_parser("show", help="Gate number, label, artifact.")
    shown.add_argument("--gate", required=True)
    shown.set_defaults(handler=cmd_gate_show)
    approved = gate_sub.add_parser("approve", help="Record an approval.")
    approved.add_argument("--gate", required=True)
    approved.add_argument("--comments")
    approved.set_defaults(handler=cmd_gate_approve)
    rejected_p = gate_sub.add_parser("reject", help="Record a rejection.")
    rejected_p.add_argument("--gate", required=True)
    rejected_p.add_argument("--reason", required=True)
    rejected_p.set_defaults(handler=cmd_gate_reject)

    drift_p = subparsers.add_parser("drift", help="Artifact drift detection.")
    drift_sub = drift_p.add_subparsers(dest="subcommand", required=True)
    dcheck = drift_sub.add_parser("check", help="Compare baselines to disk.")
    dcheck.add_argument("--diff", action="store_true",
                        help="Include git diff for tracked artifacts.")
    dcheck.add_argument("--queue", action="store_true",
                        help="Populate drift_queue and halt the workflow.")
    dcheck.add_argument("--pending-phase", help="Phase that was interrupted.")
    dcheck.set_defaults(handler=cmd_drift_check)
    drebase = drift_sub.add_parser("rebaseline", help="Move a gate's baseline.")
    drebase.add_argument("--gate", required=True)
    drebase.set_defaults(handler=cmd_drift_rebaseline)

    feature_p = subparsers.add_parser("feature", help="SpecKit feature directory.")
    feature_sub = feature_p.add_subparsers(dest="subcommand", required=True)
    fresolve = feature_sub.add_parser("resolve", help="Identify current_feature_id.")
    fresolve.set_defaults(handler=cmd_feature_resolve)

    sr_p = subparsers.add_parser("security-review", help="Phase 17 support.")
    sr_sub = sr_p.add_subparsers(dest="subcommand", required=True)
    sr_begin = sr_sub.add_parser("begin", help="Pin the review filename.")
    sr_begin.set_defaults(handler=cmd_security_review_begin)
    sr_ev = sr_sub.add_parser(
        "evidence", help="Diff against implementation_base_ref, not HEAD~1."
    )
    sr_ev.set_defaults(handler=cmd_security_review_evidence)

    artifact_p = subparsers.add_parser("artifact", help="Artifact bookkeeping.")
    artifact_sub = artifact_p.add_subparsers(dest="subcommand", required=True)
    pathed = artifact_sub.add_parser("path", help="Resolve a gate's artifact path.")
    pathed.add_argument("--gate", required=True)
    pathed.set_defaults(handler=cmd_artifact_path)
    recorded = artifact_sub.add_parser(
        "record", help="Verify size, fingerprint, and record an artifact."
    )
    recorded.add_argument("--phase")
    recorded.add_argument("--path", required=True)
    recorded.add_argument("--optional", action="store_true",
                          help="Absence is tolerated (Phase 8 checklist).")
    recorded.set_defaults(handler=cmd_artifact_record)

    limit_p = subparsers.add_parser("limit", help="Rate limits and counters.")
    limit_sub = limit_p.add_subparsers(dest="subcommand", required=True)
    lset = limit_sub.add_parser("set", help="Change a configured maximum.")
    lset.add_argument("--retries", type=int)
    lset.add_argument("--remediations", type=int)
    lset.set_defaults(handler=cmd_limit_set)
    lreset = limit_sub.add_parser("reset", help="Zero a phase's counters.")
    lreset.add_argument("--phase", required=True)
    lreset.add_argument("--retries", action="store_true")
    lreset.add_argument("--remediations", action="store_true")
    lreset.set_defaults(handler=cmd_limit_reset)

    cp_p = subparsers.add_parser("checkpoint", help="In-phase crash recovery.")
    cp_sub = cp_p.add_subparsers(dest="subcommand", required=True)
    cpset = cp_sub.add_parser("set")
    cpset.add_argument("--value", required=True)
    cpset.set_defaults(handler=cmd_checkpoint)
    cp_sub.add_parser("get").set_defaults(handler=cmd_checkpoint)
    cp_sub.add_parser("clear").set_defaults(handler=cmd_checkpoint)

    confirm_p = subparsers.add_parser("confirm", help="Two-step confirmations.")
    confirm_sub = confirm_p.add_subparsers(dest="subcommand", required=True)
    cset = confirm_sub.add_parser("set")
    cset.add_argument("--action", required=True, choices=sorted(CONFIRMABLE))
    cset.set_defaults(handler=cmd_confirm)
    ccheck = confirm_sub.add_parser("check")
    ccheck.add_argument("--action", required=True)
    ccheck.set_defaults(handler=cmd_confirm)
    confirm_sub.add_parser(
        "clear", help="Stale-confirmation guard: cancel anything pending."
    ).set_defaults(handler=cmd_confirm)

    rem_p = subparsers.add_parser("remediate", help="Post-rejection re-run.")
    rem_sub = rem_p.add_subparsers(dest="subcommand", required=True)
    rbegin = rem_sub.add_parser("begin", help="Check the limit, write feedback.")
    rbegin.add_argument("--gate", required=True)
    rbegin.set_defaults(handler=cmd_remediate_begin)
    rfinish = rem_sub.add_parser("finish", help="Archive the feedback file.")
    rfinish.add_argument("--gate", required=True)
    rfinish.set_defaults(handler=cmd_remediate_finish)

    sub = subparsers.add_parser("skip", help="Advance without a verified artifact.")
    sub.add_argument("--confirm", action="store_true")
    sub.set_defaults(handler=cmd_skip)

    sub = subparsers.add_parser("restart", help="Roll back to an earlier phase.")
    sub.add_argument("--to", type=int, required=True)
    sub.add_argument("--confirm", action="store_true")
    sub.set_defaults(handler=cmd_restart)

    sub = subparsers.add_parser("reset", help="Delete all workflow state.")
    sub.add_argument("--confirm", action="store_true")
    sub.set_defaults(handler=cmd_reset)

    subparsers.add_parser(
        "doctor", help="Recovery consistency check."
    ).set_defaults(handler=cmd_doctor)
    subparsers.add_parser(
        "accept-state", help="Acknowledge a detected state jump."
    ).set_defaults(handler=cmd_accept_state)
    subparsers.add_parser(
        "accept-content", help="Acknowledge flagged file content."
    ).set_defaults(handler=cmd_accept_content)
    subparsers.add_parser(
        "repo-staleness", help="Commits newer than the newest approval."
    ).set_defaults(handler=cmd_repo_staleness)
    subparsers.add_parser(
        "preflight", help="Bootstrap prerequisites."
    ).set_defaults(handler=cmd_preflight)

    sub = subparsers.add_parser("scan", help="Untrusted-content scan.")
    sub.add_argument("--path", required=True)
    sub.set_defaults(handler=cmd_scan)

    clarify_p = subparsers.add_parser("clarify", help="Clarification responses.")
    clarify_sub = clarify_p.add_subparsers(dest="subcommand", required=True)
    csave = clarify_sub.add_parser("save")
    csave.add_argument("--phase", required=True)
    csave.add_argument("--text", required=True)
    csave.set_defaults(handler=cmd_clarify_save)

    guidance_p = subparsers.add_parser("guidance", help="Per-phase steering files.")
    guidance_sub = guidance_p.add_subparsers(dest="subcommand", required=True)
    gpath = guidance_sub.add_parser("path")
    gpath.add_argument("--phase", required=True)
    gpath.set_defaults(handler=cmd_guidance_path)

    impl_p = subparsers.add_parser("implement", help="Phase 15 support.")
    impl_sub = impl_p.add_subparsers(dest="subcommand", required=True)
    ipre = impl_sub.add_parser(
        "preflight", help="Dirty-tree guard; pin implementation_base_ref."
    )
    ipre.add_argument("--bypass", action="store_true",
                      help="Proceed despite a dirty tree (logged).")
    ipre.set_defaults(handler=cmd_implement_preflight)

    man_p = subparsers.add_parser("manifest", help="Gate 7 artifact.")
    man_sub = man_p.add_subparsers(dest="subcommand", required=True)
    mbuild = man_sub.add_parser("build", help="File list, secrets scan, tests.")
    mbuild.add_argument("--summary")
    mbuild.add_argument("--skip-tests", action="store_true")
    mbuild.add_argument("--test-timeout", type=int, default=600)
    mbuild.set_defaults(handler=cmd_manifest_build)

    lock_p = subparsers.add_parser("lock", help="Session lock.")
    lock_sub = lock_p.add_subparsers(dest="subcommand", required=True)
    acquired = lock_sub.add_parser("acquire")
    acquired.set_defaults(handler=cmd_lock_acquire)
    released = lock_sub.add_parser("release")
    released.set_defaults(handler=cmd_lock_release)

    sub = subparsers.add_parser("sha", help="SHA-256 of a file (lowercase hex).")
    sub.add_argument("path")
    sub.set_defaults(handler=cmd_sha)

    sub = subparsers.add_parser("constants", help="Dump the parsed constant tables.")
    sub.set_defaults(handler=cmd_constants)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        paths = resolve_paths(args.project_root, args.skill_root)
        if args.command not in RUNTIME_FREE_COMMANDS:
            paths = bind_workitem(
                paths, args.workitem, for_init=args.command == "init"
            )
        return args.handler(args, paths)
    except SdleError as exc:
        print(f"{exc.reason}: {exc.message}", file=sys.stderr)
        emit(
            args.command,
            exc.data,
            ok=False,
            reason=exc.reason,
            message=exc.message,
        )
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
