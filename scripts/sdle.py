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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------
# Exit codes — the contract
# --------------------------------------------------------------------------

EXIT_OK = 0
EXIT_REFUSED = 1
EXIT_USAGE = 2
EXIT_INTEGRITY = 3

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
    """Locations the engine works with.

    ``project_root`` is the target project: the one with ``.workflow/``.
    ``skill_root`` is the directory holding ``SKILL.md`` — the constants host.
    """

    project_root: Path
    skill_root: Path

    @property
    def workflow(self) -> Path:
        return self.project_root / ".workflow"

    @property
    def state_file(self) -> Path:
        return self.workflow / "state.json"

    @property
    def audit_file(self) -> Path:
        return self.workflow / "audit.md"

    @property
    def lock_file(self) -> Path:
        return self.workflow / "lock"

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

CURRENT_VERSION = "1.13"

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
    if not paths.state_file.is_file():
        raise IntegrityError(
            "state_unreadable",
            "No .workflow/state.json in this project. "
            "Run `init` to start a workflow.",
            {"path": str(paths.state_file)},
        )
    try:
        return json.loads(paths.state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IntegrityError(
            "state_unreadable",
            f".workflow/state.json is not valid JSON: {exc}. "
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
        try:
            when = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
            age = int((datetime.now(timezone.utc) - when).total_seconds())
            fresh = age < LOCK_FRESH_SECONDS
        except ValueError:
            age = None
            fresh = False

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
            message=".workflow/audit.md is missing.",
        )
        print("audit_chain_broken: .workflow/audit.md is missing.", file=sys.stderr)
        return EXIT_INTEGRITY

    actual = sha256_file(paths.audit_file)
    entries = split_audit_entries(paths.audit_file.read_text(encoding="utf-8"))

    chain_ok = True
    broken_at = None
    prev = GENESIS
    for index, block in enumerate(entries, start=1):
        match = re.search(r"^\*\*Prev:\*\*\s*(\S+)\s*$", block, flags=re.MULTILINE)
        recorded = match.group(1) if match else None
        if recorded != prev:
            chain_ok = False
            broken_at = index
            break
        prev = _entry_digest(block)

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


def cmd_audit_rebaseline(args, paths: Paths) -> int:
    """The `accept audit` path. Logged, so it can never happen silently."""
    state = read_state(paths)
    append_audit(
        paths,
        state,
        phase=state.get("current_phase", "unknown"),
        event="audit_rebaseline",
        message="User acknowledged audit integrity mismatch. Audit hash re-baselined.",
    )
    save_state(paths, state, args.session)
    emit("audit rebaseline", {"audit_sha": state["audit_sha"]})
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
            "A workflow already exists in .workflow/state.json. "
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

    name = args.project or infer_project_name(paths) or paths.project_root.name

    state = load_template(paths)
    state["project_name"] = name
    state["current_phase"] = "requirements_check"
    state["status"] = "in_progress"
    state["progress"] = consts.progress_for("requirements_check")

    paths.workflow.mkdir(parents=True, exist_ok=True)
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
# Artifact path resolution
# --------------------------------------------------------------------------


def resolve_artifact_path(
    state: dict, consts: Constants, gate_key: str
) -> tuple[str | None, str | None]:
    """Resolve ARTIFACT_OWNERSHIP's template for ``gate_key``.

    Returns ``(resolved_path, skip_reason)``. A skip reason means the gate has
    no comparable artifact yet — not that something failed.
    """
    template = consts.artifact_ownership.get(gate_key)
    if not template or template == "(none)":
        return None, "no artifact registered for this gate"

    resolved = template
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
    resolved, skipped = resolve_artifact_path(state, consts, args.gate)
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
    resolved, skipped = resolve_artifact_path(state, consts, args.gate)
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
    target = paths.workflow / "completion-summary.json"
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

    resolved, _ = resolve_artifact_path(state, consts, args.gate)
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

    resolved, _ = resolve_artifact_path(state, consts, gate_key)
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
        resolved, _ = resolve_artifact_path(state, consts, gate_key)
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

    resolved, skipped = resolve_artifact_path(state, consts, args.gate)
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


def gate_precondition_hook(paths: Paths, state: dict, consts: Constants,
                           gate_key: str, resolved: str | None) -> None:
    """Gate-specific refusals that must hold at the choke point.

    Extended by later steps (Gate 7 requires a complete manifest).
    """
    return None


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
        "--session",
        help="Conversation session token; refreshes .workflow/lock on write.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    sub = subparsers.add_parser("lint-skill", help="Verify cross-file sync rules.")
    sub.set_defaults(handler=cmd_lint_skill)

    sub = subparsers.add_parser("init", help="Create .workflow/ and initial state.")
    sub.add_argument("--project", help="Project name (default: infer from heading).")
    sub.set_defaults(handler=cmd_init)

    sub = subparsers.add_parser("header", help="Render the status assertion header.")
    sub.set_defaults(handler=cmd_header)

    sub = subparsers.add_parser("migrate", help="Apply the version migration chain.")
    sub.set_defaults(handler=cmd_migrate)

    state_p = subparsers.add_parser("state", help="Read workflow state.")
    state_sub = state_p.add_subparsers(dest="subcommand", required=True)
    got = state_sub.add_parser("get", help="Full state, or one field.")
    got.add_argument("--field")
    got.set_defaults(handler=cmd_state_get)
    dumped = state_sub.add_parser("dump", help="Render the full status dump.")
    dumped.set_defaults(handler=cmd_state_dump)

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

    artifact_p = subparsers.add_parser("artifact", help="Artifact bookkeeping.")
    artifact_sub = artifact_p.add_subparsers(dest="subcommand", required=True)
    pathed = artifact_sub.add_parser("path", help="Resolve a gate's artifact path.")
    pathed.add_argument("--gate", required=True)
    pathed.set_defaults(handler=cmd_artifact_path)

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
