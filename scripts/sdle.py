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
import sys
import tempfile
from dataclasses import dataclass, field
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
    subparsers = parser.add_subparsers(dest="command", required=True)

    sub = subparsers.add_parser("lint-skill", help="Verify cross-file sync rules.")
    sub.set_defaults(handler=cmd_lint_skill)

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
