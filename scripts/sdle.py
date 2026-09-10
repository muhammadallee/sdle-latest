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
import copy
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
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
    ``workitem`` is the bound WorkItem id. After T11 a *bound* ``Paths``
    always names one: ``None`` survives only before binding and in the
    migration **source view** ``cmd_migrate_workflow`` constructs to read a
    pre-v1.14 ``.workflow/``. It is still the *only* switch between the two
    locations: every runtime path below derives from ``runtime``, so no
    command ever concatenates a WorkItem-owned path of its own.
    """

    project_root: Path
    skill_root: Path
    workitem: str | None = None
    # Where the developer actually launched from. Contract §9 allows four
    # launch locations, and resolution rung 2 needs the real directory, not the
    # repository root that was discovered from it. ``None`` only when a caller
    # constructs ``Paths`` directly instead of going through ``resolve_paths``.
    launch_cwd: Path | None = None

    @property
    def legacy_workflow(self) -> Path:
        """The pre-v1.14 repository-global directory.

        T11 removed the resolution rung that bound it as a *runtime*. It
        survives as exactly two things and nothing more: a **migration
        source** (``cmd_migrate_workflow`` reads it and never writes it) and a
        **project-root marker**, without which a legacy-only repository could
        not be discovered and therefore could not be migrated at all.
        """
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
    def governance_file(self) -> Path:
        """The WorkItem's recorded governance verdict (contract §12).

        A WorkItem-owned *record*, never a policy. It is deliberately not a
        field of ``state.json``: §12 places governance before planning, so the
        record must be writable before ``state.json`` exists — the same
        ownership argument that put branch/SHA in ``execution.json``.
        """
        return self.runtime / "governance.json"

    @property
    def reviews_file(self) -> Path:
        """Append-only governed-artifact review records (TP-011)."""
        return self.runtime / "reviews.json"

    @property
    def discovery_file(self) -> Path:
        """This WorkItem's recorded §14 brownfield discovery findings.

        WorkItem-owned, for the same reason ``governance_file`` is: discovery
        is work one WorkItem performed, at a point in time, and the repository
        baseline that outlives it *references* this file rather than copying
        it. Deliberately not a field of ``state.json`` — it is an evidence
        document, not lifecycle state.
        """
        return self.runtime / "discovery.json"

    @property
    def speckit_specs_root(self) -> Path | None:
        """Where this WorkItem's Spec Kit feature directories live.

        ``None`` only for an **unbound** ``Paths`` — the source view
        ``cmd_migrate_workflow`` constructs, which has no WorkItem to scope
        to. T11 removed the legacy runtime binding, so no *bound* ``Paths``
        reaches this with ``workitem`` unset (R2). Derived here so no call
        site ever concatenates a Spec Kit path of its own — the same
        discipline ``runtime`` established for the runtime.
        """
        root = self.workitem_root
        return None if root is None else root / "specs"

    @property
    def speckit_specs_relative(self) -> str | None:
        """``speckit_specs_root`` as a repo-relative POSIX prefix."""
        root = self.speckit_specs_root
        if root is None:
            return None
        return str(root.relative_to(self.project_root)).replace(os.sep, "/")

    # -- repository configuration boundary (contract §11) ----------------
    #
    # Every member below derives from ``project_root`` **alone**. None of them
    # may reference ``workitem``, ``workitem_root`` or ``runtime``: that
    # derivation *is* the ownership split the contract asks for. Repository
    # `.sdle/` owns global configuration, policy definitions, shared templates,
    # the future baseline and implementation-transition metadata; WorkItem
    # `.sdle/` owns lifecycle state, execution, audit, evidence and manifests.
    # Rebinding the WorkItem changes every runtime member and none of these.

    @property
    def config_root(self) -> Path:
        """Repository-global SDLE configuration. Never WorkItem-scoped."""
        return self.project_root / ".sdle"

    @property
    def config_root_relative(self) -> str:
        """``config_root`` as a repo-relative POSIX prefix."""
        return str(self.config_root.relative_to(self.project_root)).replace(
            os.sep, "/")

    @property
    def config_file(self) -> Path:
        return self.config_root / "config.json"

    @property
    def policies_dir(self) -> Path:
        return self.config_root / "policies"

    @property
    def governance_policy_file(self) -> Path:
        """The optional repository governance policy override (contract §12).

        The basename differs from ``governance_file`` on purpose. A policy is
        repository-owned and a record is WorkItem-owned; sharing a basename
        would make the two `.sdle/` leak detectors contradict each other and
        would break the runtime/configuration name disjointness §11 relies on.
        """
        return self.policies_dir / "governance-policy.json"

    @property
    def shared_templates_dir(self) -> Path:
        """Repository-shared templates.

        Deliberately not named ``templates_dir``: ``skill_root/templates/``
        already exists and a bare name would read as that one.
        """
        return self.config_root / "templates"

    @property
    def baseline_file(self) -> Path:
        """The §11 baseline slot. No engine path writes it at T05 — §14 owns
        its schema."""
        return self.config_root / "baseline.json"

    @property
    def implementation_state_dir(self) -> Path:
        """Implementation-transition metadata. An empty documented slot: the
        contract defines no schema, producer or consumer for it."""
        return self.config_root / "implementation-state"

    @property
    def skill_md(self) -> Path:
        return self.skill_root / "SKILL.md"

    @property
    def modules_dir(self) -> Path:
        """Where the on-demand capability files live.

        One home for the folder name: every module property below derives
        from it, and `lint-skill` enumerates it rather than keeping a second
        hand-maintained list of what is inside.
        """
        return self.skill_root / "modules"

    @property
    def agents_dir(self) -> Path:
        """`.claude/agents/`, the sibling of `.claude/skills/`.

        Derived, never configured — the same discipline `runtime` established
        for the WorkItem runtime. When the skill is installed somewhere with
        no sibling `agents/` the directory simply does not exist, and every
        caller treats that as "no agent files", never as an error.
        """
        return self.skill_root.parent.parent / "agents"

    @property
    def gate_protocol_md(self) -> Path:
        return self.modules_dir / "gate-protocol.md"

    @property
    def phase_execution_md(self) -> Path:
        return self.modules_dir / "phase-execution.md"

    @property
    def security_review_md(self) -> Path:
        return self.modules_dir / "security-review.md"

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


# Markers that identify a repository root, tested in this order at every level
# of the upward walk. `workitems/index.md` comes first because a WorkItem
# registry is the most specific statement a repository makes about itself; the
# legacy runtime is next; `.git` is the weakest signal and therefore last.
# `.sdle/config.json` is the configuration boundary's own marker (contract
# §11), the mirror of `workitems/index.md`: without it, `config init` launched
# from a subdirectory would write a second boundary there. Markers are tested
# in the inner loop, so tuple order cannot change *which* directory is
# returned — only which level stops the walk — and no repository predating T05
# contains a `.sdle/config.json`, so appending it is a no-op for all of them.
PROJECT_ROOT_MARKERS = (
    ("workitems", "index.md"),
    (".workflow", "state.json"),
    (".git",),
    (".sdle", "config.json"),
)


def discover_project_root(start: Path) -> Path | None:
    """Nearest ancestor of ``start`` (inclusive) that carries a marker.

    Contract §9 lets Claude launch from ``workitems/<id>/``, ``workitems/``,
    the repository root, or anywhere inside the repository. Treating the launch
    directory *as* the repository root makes every path below it wrong, so the
    root is discovered rather than assumed. Nearest ancestor wins, so a nested
    checkout never resolves to its parent repository.
    """
    for candidate in (start, *start.parents):
        for marker in PROJECT_ROOT_MARKERS:
            if candidate.joinpath(*marker).exists():
                return candidate
    return None


def _within(child: Path, parent: Path) -> bool:
    """True when ``child`` is ``parent`` or lives beneath it."""
    return child == parent or parent in child.parents


def resolve_paths(project_root: str | None, skill_root: str | None) -> Paths:
    try:
        launch = Path.cwd().resolve()
    except OSError:  # the launch directory was deleted underneath us
        launch = Path(".").absolute()

    explicit_root = project_root or os.environ.get("SDLE_PROJECT_ROOT")
    if explicit_root:
        proj = Path(explicit_root).resolve()
    else:
        # Fallback to the launch directory itself keeps a brand-new project
        # with no markers working exactly as it did before T03.
        proj = (discover_project_root(launch) or launch).resolve()

    # A launch directory outside the project is not a location inside it, so
    # it must never feed the CWD resolution rung.
    launch_cwd = launch if _within(launch, proj) else proj

    explicit = skill_root or os.environ.get("SDLE_SKILL_ROOT")
    if explicit:
        skill = Path(explicit).resolve()
        if not (skill / "SKILL.md").is_file():
            raise Refused(
                "skill_root_not_found",
                f"No SKILL.md under the given skill root: {skill}",
                {"skill_root": str(skill)},
            )
        return Paths(project_root=proj, skill_root=skill,
                     launch_cwd=launch_cwd)

    for candidate in _candidate_skill_roots(Path(__file__), proj):
        if (candidate / "SKILL.md").is_file():
            return Paths(project_root=proj, skill_root=candidate.resolve(),
                         launch_cwd=launch_cwd)

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
# Flows — a flow is an ordered subset of the phase registry
# --------------------------------------------------------------------------
#
# PHASE_SEQUENCE is the *registry*: the closed catalogue of phases SDLE knows
# how to execute, in canonical order. It is not a flow. A flow is an ordered
# subset of the registry, preserving registry order, and every traversal
# decision reads the bound flow rather than the registry.
#
# GREENFIELD's membership is pinned HERE and is deliberately NOT derived from
# the registry. GATE_PHASES may be derived because it *filters* the registry
# through an explicitly declared set (PHASE_TO_GATE_KEY), so a new registry row
# adds no gate. Deriving GREENFIELD as *all of* the registry has the opposite
# property: a stray row would silently join GREENFIELD and change what every
# pre-v1.16 workflow is retroactively said to have traversed. This list is the
# compatibility translation the contract requires, frozen: it is element-wise
# the pre-T07 PHASE_SEQUENCE. The guarantee derivation used to give for free —
# that no registry phase is orphaned — is restored by the
# `every_registry_phase_is_used_by_some_flow` lint check, which fails loudly
# instead of failing open.

GREENFIELD_V1_PHASES: tuple[str, ...] = (
    "requirements_check",
    "constitution_draft",
    "gate_constitution",
    "spec_draft",
    "gate_spec",
    "plan_draft",
    "gate_plan",
    "checklist_draft",
    "tasks_draft",
    "gate_tasks",
    "analyze",
    "gate_analyze",
    "design_generation",
    "gate_design",
    "implement",
    "gate_implement",
    "security_review",
    "gate_security",
    "complete",
)

DEFAULT_FLOW = "GREENFIELD"

# The governance floor. "Shorter but never ungoverned" is a testable identity
# rather than a judgement call: no flow may drop any of these, and the rule is
# enforced at lint time *and* at load time, because a flow that lost one would
# not merely look wrong — it would break inside Spec Kit at run time.
#
#   requirements_check  bootstrap; `init` writes it as the first phase
#   spec_draft          the only phase that creates the feature directory
#   gate_spec           the first human gate; without it nothing is governed
#   plan_draft          `speckit-tasks` derives from plan.md
#   tasks_draft         `speckit-implement` derives from tasks.md
#   implement           carries the secrets scan and the test evidence
#   gate_implement      the human decision on that evidence
#   security_review     the terminal safety control
#   gate_security       the terminal human gate; writes the completion summary
#   complete            terminal
MANDATORY_FLOW_PHASES: tuple[str, ...] = (
    "requirements_check",
    "spec_draft",
    "gate_spec",
    "plan_draft",
    "tasks_draft",
    "implement",
    "gate_implement",
    "security_review",
    "gate_security",
    "complete",
)

GATE_NUMBER_PLACEHOLDER = "{gate_number}"


@dataclass(frozen=True)
class Flow:
    """One lifecycle: an ordered subset of the registry, plus its gates.

    Every ordinal a user ever sees — the progress fraction, the gate number,
    the gate total, the `restart` index — is derived from this object, so the
    numbers a flow shows are the numbers that flow actually has.
    """

    name: str
    phases: tuple[str, ...]
    gate_phases: tuple[str, ...]
    gate_keys: tuple[str, ...]

    def contains(self, phase: str | None) -> bool:
        return phase in self.phases

    def position(self, phase: str | None) -> int | None:
        """1-based position in the flow, or ``None`` when out of flow.

        Deliberately non-raising: refusal payloads compute positions for
        phases that may be outside the flow, and an index lookup that raised
        there would mask the real reason for the refusal.
        """
        try:
            return self.phases.index(phase) + 1  # type: ignore[arg-type]
        except ValueError:
            return None

    def index(self, phase: str | None) -> int:
        position = self.position(phase)
        if position is None:
            raise Refused(
                "unknown_phase",
                f"'{phase}' is not a phase in the {self.name} flow.",
                {"phase": phase, "flow": self.name, "known": list(self.phases)},
            )
        return position

    def phase_at(self, index: int) -> str:
        if not 1 <= index <= len(self.phases):
            raise Refused(
                "unknown_phase",
                f"Phase index {index} is out of range for the {self.name} "
                f"flow (1-{len(self.phases)}).",
                {"index": index, "flow": self.name},
            )
        return self.phases[index - 1]

    def next_phase(self, phase: str | None) -> str | None:
        position = self.position(phase)
        if position is None or position >= len(self.phases):
            return None
        return self.phases[position]

    @property
    def phase_count(self) -> int:
        """The N in 'N/18' — every phase except the terminal ``complete``."""
        return len([p for p in self.phases if p != "complete"])

    @property
    def gate_total(self) -> int:
        return len(self.gate_phases)

    def progress_for(self, phase: str | None) -> str:
        position = self.position(phase)
        if position is None:
            raise Refused(
                "unknown_phase",
                f"'{phase}' is not a phase in the {self.name} flow, so it "
                "has no progress position.",
                {"phase": phase, "flow": self.name},
            )
        total = self.phase_count
        # ``complete`` sits one past the last non-terminal phase and shares
        # its fraction, exactly as PROGRESS_MAP has always spelled it.
        return f"{min(position, total)}/{total}"

    def gate_number(self, gate_key: str | None) -> int | None:
        try:
            return self.gate_keys.index(gate_key) + 1  # type: ignore[arg-type]
        except ValueError:
            return None

    def gate_number_for_phase(self, phase: str | None) -> int | None:
        try:
            return self.gate_phases.index(phase) + 1  # type: ignore[arg-type]
        except ValueError:
            return None

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "phases": list(self.phases),
            "phase_count": self.phase_count,
            "gate_phases": list(self.gate_phases),
            "gate_keys": list(self.gate_keys),
            "gate_total": self.gate_total,
        }


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
    phase_label_template: dict[str, str] = field(default_factory=dict)
    progress: dict[str, str] = field(default_factory=dict)
    gate_to_execution_phase: dict[str, str] = field(default_factory=dict)
    version_chain: list[tuple[str, str]] = field(default_factory=list)
    flow_phases: dict[str, list[str]] = field(default_factory=dict)
    # Which capability files each phase requires. Parsed, never inferred: the
    # engine decides what the prompt layer loads, so "load only the relevant
    # phase context" is a deterministic lookup rather than a judgement the
    # model re-makes every turn.
    capability_map: dict[str, list[str]] = field(default_factory=dict)

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

    # -- flows -----------------------------------------------------------

    def _build_flow(self, name: str, phases: list[str] | tuple[str, ...]) -> Flow:
        ordered = tuple(phases)
        gate_phases = tuple(p for p in ordered if p in self.phase_to_gate_key)
        return Flow(
            name=name,
            phases=ordered,
            gate_phases=gate_phases,
            gate_keys=tuple(self.phase_to_gate_key[p] for p in gate_phases),
        )

    @property
    def greenfield(self) -> Flow:
        """The frozen v1 lifecycle, built through the ordinary flow rules.

        Every ordinal SKILL.md still restates for humans is a view of *this*
        flow: PROGRESS_MAP's fractions, PHASE_TO_GATE_KEY's gate numbers, and
        the ordinals inside PHASE_LABEL_MAP. `lint-skill` pins each of them to
        it, so they are checked derived views rather than second sources of
        truth. Its membership comes from GREENFIELD_V1_PHASES, never from the
        registry.
        """
        return self._build_flow(DEFAULT_FLOW, GREENFIELD_V1_PHASES)

    @property
    def flows(self) -> dict[str, Flow]:
        """Every declared flow, plus GREENFIELD injected from the frozen list.

        GREENFIELD is deliberately not a FLOW_PHASES row: one fact, one home.
        It is nonetheless built and validated by exactly the same rules as a
        declared flow, so it can never become a privileged special case.
        """
        built: dict[str, Flow] = {
            name: self._build_flow(name, phases)
            for name, phases in self.flow_phases.items()
        }
        built[DEFAULT_FLOW] = self.greenfield
        return built

    def _flow_invalid(self, name: str, detail: str, **data) -> IntegrityError:
        return IntegrityError(
            "flow_table_invalid",
            f"FLOW_PHASES is unusable for flow '{name}': {detail}. A flow "
            "must be an ordered subset of PHASE_SEQUENCE that starts at "
            "requirements_check, ends at complete and keeps every mandatory "
            "phase. Fix the FLOW_PHASES table in SKILL.md and re-run "
            "`sdle.sh lint-skill`.",
            {"flow": name, "detail": detail, **data},
        )

    def flow_order_problems(self, flow: Flow) -> list[str]:
        """Why ``flow`` is not an ordered subset of the registry; [] if it is.

        Returned rather than raised so `lint-skill` can name the rule that
        broke. ``validate_flow`` is the raising wrapper the engine uses when a
        traversal actually asks for a flow: one rule, two presentations.
        """
        registry = list(self.phase_sequence)
        problems: list[str] = []
        unknown = [p for p in flow.phases if p not in registry]
        if unknown:
            problems.append(f"phase(s) not in PHASE_SEQUENCE: {unknown}")
        if len(set(flow.phases)) != len(flow.phases):
            duplicates = sorted(
                {p for p in flow.phases if flow.phases.count(p) > 1})
            problems.append(f"duplicated phase(s) {duplicates}")
        positions = [registry.index(p) for p in flow.phases if p in registry]
        if positions != sorted(positions):
            problems.append("phases are not in PHASE_SEQUENCE order")
        if not flow.phases or flow.phases[0] != "requirements_check":
            problems.append("a flow must start at requirements_check")
        if not flow.phases or flow.phases[-1] != "complete":
            problems.append("a flow must end at the terminal phase complete")
        return problems

    def flow_floor_problems(self, flow: Flow) -> list[str]:
        """Which mandatory phases ``flow`` dropped; [] when it kept them all.

        "Shorter but never ungoverned" is enforced here and nowhere else, at
        lint time through the named check and at load time through
        ``validate_flow`` — a flow that lost one of these would not merely look
        wrong, it would die inside Spec Kit on a real run.
        """
        missing = [p for p in MANDATORY_FLOW_PHASES if p not in flow.phases]
        return [f"mandatory phase(s) missing: {missing}"] if missing else []

    def validate_flow(self, flow: Flow) -> None:
        """Refuse a flow that could not be traversed. Never repair one."""
        problems = (self.flow_order_problems(flow)
                    + self.flow_floor_problems(flow))
        if problems:
            raise self._flow_invalid(
                flow.name, "; ".join(problems), problems=problems)

    def flow(self, name: str | None = None) -> Flow:
        """The named flow, validated. Refuses rather than defaulting."""
        wanted = name or DEFAULT_FLOW
        built = self.flows
        chosen = built.get(wanted)
        if chosen is None:
            raise self._flow_invalid(
                wanted, "no such flow is declared",
                known=sorted(built))
        self.validate_flow(chosen)
        return chosen

    # -- labels ----------------------------------------------------------

    def render_label(self, phase: str, flow: Flow | None = None) -> str:
        """Substitute the flow-relative gate number into a label template.

        A gate that the bound flow does not run has no number *in* that flow;
        it falls back to its GREENFIELD number, which is the canonical human
        reference for that gate, rather than guessing a position it does not
        occupy.
        """
        template = self.phase_label_template[phase]
        if GATE_NUMBER_PLACEHOLDER not in template:
            return template
        number = flow.gate_number_for_phase(phase) if flow else None
        if number is None:
            number = self.greenfield.gate_number_for_phase(phase)
        return template.replace(
            GATE_NUMBER_PLACEHOLDER, str(number) if number else "?")

    def label_or(self, phase: str | None, flow: Flow | None = None,
                 default: str | None = None) -> str | None:
        """Non-raising label lookup, for the display sites that use ``.get``."""
        if phase is None or phase not in self.phase_label_template:
            return default
        return self.render_label(phase, flow)

    @property
    def phase_label(self) -> dict[str, str]:
        """The GREENFIELD-rendered labels.

        The parsed templates carry a ``{gate_number}`` placeholder so a gate's
        ordinal can be flow-relative; this view is the one every pre-T07
        reader already expected, byte-identical under GREENFIELD.
        """
        return {
            phase: self.render_label(phase)
            for phase in self.phase_label_template
        }

    def label(self, phase: str, flow: Flow | None = None) -> str:
        if phase not in self.phase_label_template:
            raise Refused(
                "unknown_phase",
                f"No label registered for phase '{phase}'.",
                {"phase": phase},
            )
        return self.render_label(phase, flow)

    def capabilities_for(self, phase: str | None) -> list[str]:
        """The capability files ``phase`` requires. Never raises.

        A phase with no row answers with the empty list.
        ``capability_map_covers_every_registry_phase`` is what makes a missing
        row impossible in a repository that lints; a read-only reporter must
        still be able to say where a WorkItem *is* rather than refusing
        because a table has a hole in it.
        """
        return list(self.capability_map.get(phase or "", []))

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
            consts.phase_label_template[phase] = _column(row, "label") or phase

    for row in parse_md_table(skill, "PROGRESS_MAP"):
        phase = _column(row, "phase", "phase_id")
        if phase:
            consts.progress[phase] = _column(row, "progress") or ""

    # FLOW_PHASES is *parsed* here and deliberately **not validated**. A broken
    # flow row must surface as the named lint check it breaks; if the loader
    # raised, `tables_wellformed` would short-circuit and report one opaque
    # failure instead. Validation lives in `run_sync_checks` (the flow checks)
    # and in `Constants.flow()`, which refuses `flow_table_invalid` when a
    # traversal actually asks for a flow.
    for row in parse_md_table(skill, "FLOW_PHASES"):
        name = _column(row, "flow", "flow_name")
        if name:
            cell = _column(row, "phases",
                           "phases_registry_order_space_separated") or ""
            consts.flow_phases[name] = cell.split()

    # Same cell convention as FLOW_PHASES, and the same pitfall: space
    # separated and NOT backticked, because one pair of backticks around the
    # whole cell is stripped and the list mangles into a single unrecognisable
    # path. Parsed here and validated in `run_sync_checks`, for the reason
    # FLOW_PHASES is: a broken row must surface as the named check it breaks,
    # not as one opaque `tables_wellformed` failure that short-circuits the
    # rest.
    for row in parse_md_table(skill, "CAPABILITY_MAP"):
        phase = _column(row, "phase", "phase_id")
        if phase:
            cell = _column(row, "capabilities") or ""
            consts.capability_map[phase] = cell.split()

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


def flow_for_state(state: dict | None, consts: Constants) -> Flow:
    """The flow this workflow is traversing.

    Bound once by ``init`` (or by migration, for a workflow that predates the
    field) and never re-bound: there is deliberately no command that writes it.
    A state with no ``flow`` is a pre-v1.16 state, and every pre-v1.16
    workflow traversed exactly the pre-T07 registry, which is GREENFIELD.
    """
    name = (state or {}).get("flow")
    return consts.flow(name if isinstance(name, str) and name else None)


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
    # Trailing whitespace only. A leading space is data in git's status
    # formats (` M path` is an unstaged change), and stripping it shifted the
    # first line by one character: `line[3:]` then cut the first letter of
    # the path, so an SDLE-owned file sorting first escaped the dirty-tree
    # filter as a false `dirty_tree` (found reproducing D03,
    # SDLE-DEFECT-STABILIZATION-01).
    return completed.returncode, (completed.stdout or "").rstrip()


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

CURRENT_VERSION = "1.17"

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


# --------------------------------------------------------------------------
# Spec Kit context (contract §10)
#
# v1.15 replaced the flat `current_feature_id` with a `specKit` object owned
# by the WorkItem. Every read and every write goes through the two accessors
# below, so a pre-1.15 state — which `read_state` does not migrate — degrades
# to all-null instead of raising KeyError at an arbitrary call site.
# --------------------------------------------------------------------------

SPECKIT_REF_KEYS = ("featureId", "featureDirectory", "workflowId", "runId")


def speckit_ref(state: dict) -> dict:
    """The `specKit` object, defaulted. Never raises, never KeyError.

    Returns a fresh dict in canonical key order; mutating it does not touch
    ``state``. Empty strings and non-string values normalise to ``None`` so
    callers can test a member with a plain truth check.
    """
    raw = state.get("specKit")
    ref = {key: None for key in SPECKIT_REF_KEYS}
    if isinstance(raw, dict):
        for key in SPECKIT_REF_KEYS:
            value = raw.get(key)
            if isinstance(value, str) and value:
                ref[key] = value
    return ref


def speckit_set(state: dict, **values) -> dict:
    """Write named `specKit` members, keeping the canonical key order.

    `workflowId` and `runId` are contract §10 extension points with no
    producer in SDLE. Nothing in the engine passes them, so they stay null;
    the field names are still accepted here so the object has exactly one
    writer rather than two.
    """
    unknown = sorted(k for k in values if k not in SPECKIT_REF_KEYS)
    if unknown:
        raise IntegrityError(
            "speckit_field_unknown",
            f"specKit has no field(s): {', '.join(unknown)}.",
            {"unknown": unknown, "known": list(SPECKIT_REF_KEYS)},
        )
    ref = speckit_ref(state)
    ref.update(values)
    state["specKit"] = {key: ref[key] for key in SPECKIT_REF_KEYS}
    return state["specKit"]


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
    review: str | None = None,
    evidence_id: str | None = None,
) -> str:
    """Append an entry, chain it, and rebaseline ``audit_sha``.

    Ordering is load-bearing: append -> hash file -> save state.

    ``review`` and ``evidence_id`` are TP-011's audit linkage (T06/D10). When
    both are ``None`` the rendered block is **byte-identical** to every entry
    written before T06, which is what lets a pre-T06 ledger keep verifying.
    When supplied they render as two extra lines placed **before** ``Prev``:
    the chain tail must stay the last line of the entry, and the review result
    must not be smuggled into ``decision``, which belongs to gate approval.
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
        + (f"**Review:** {review}\n" if review else "")
        + (f"**Evidence:** {evidence_id}\n" if evidence_id else "")
        + f"**Prev:** {prev}\n"
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


def _mig_1_14(state, paths, consts):
    """Replace the flat `current_feature_id` with the `specKit` object.

    Contract §10 makes Spec Kit context an object owned by the WorkItem. The
    old value is *moved*, not mirrored: two fields for one fact would break
    invariant 7. `featureDirectory` is read off the tree in a fixed order,
    first hit wins, so it is a fact about disk rather than an inference:

      1. `workitems/<workitem>/specs/<featureId>` when that directory exists;
      2. `.specify/specs/<featureId>` when that one does — where a pre-v1.15
         run's artifacts genuinely are, so an in-flight workflow keeps
         resolving its gates instead of breaking at the next one;
      3. otherwise null.

    Nothing moves on disk here. Migration reports; `feature resolve` relocates.
    """
    feature = state.pop("current_feature_id", None)
    if not isinstance(feature, str) or not feature:
        feature = None

    directory = None
    if feature:
        candidates = []
        workitem = state.get("workitem")
        if isinstance(workitem, str) and workitem:
            candidates.append(f"workitems/{workitem}/specs/{feature}")
        candidates.append(f".specify/specs/{feature}")
        for candidate in candidates:
            if (paths.project_root / candidate).is_dir():
                directory = candidate
                break

    speckit_set(state, featureId=feature, featureDirectory=directory,
                workflowId=None, runId=None)


def _mig_1_15(state, paths, consts):
    """Name the lifecycle a pre-flow workflow has been traversing all along.

    Every workflow created before the flow model traversed exactly one phase
    list — the pre-flow PHASE_SEQUENCE — and that list is GREENFIELD. The value
    is therefore unconditional, and this migration deliberately does **not**
    consult the governance record: a migration records what a workflow *has
    been doing*, and re-deriving traversal from a classification assessed later
    would silently reshape an in-flight run. A workflow whose record now
    proposes a different flow is refused `flow_mismatch` at its next advance,
    with a named remedy — which is correct, and is not this function's job.
    """
    if not isinstance(state.get("flow"), str) or not state["flow"]:
        state["flow"] = DEFAULT_FLOW


def _mig_1_16(state, paths, consts):
    """Introduce ``pending_branch_ack`` (T11 D13).

    ``None`` unconditionally, and that is the safe value rather than a
    convenient one: a migrated workflow with an outstanding
    ``pending_confirm_action == "branch_mismatch"`` has an acknowledgement
    whose branch nobody recorded, so the guard must ask again on the next
    critical command instead of honouring an acknowledgement it cannot
    attribute. Guessing ``current_branch()`` here would manufacture consent
    the user never gave.
    """
    _add_missing(state, pending_branch_ack=None)


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
    ("1.14", "1.15", _mig_1_14),
    ("1.15", "1.16", _mig_1_15),
    ("1.16", "1.17", _mig_1_16),
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
    # T07/D9 — the flow binds HERE, once, and nothing ever re-binds it. There
    # is deliberately no `flow set` / `flow select` command: a second writer of
    # traversal identity would let the model reshape the lifecycle by issuing a
    # command, which is a governance bypass. Governance stays deliberately not
    # an `init` precondition (T06), so the no-record case has to exist and has
    # to be the safe one — GREENFIELD is the flow every workflow before v1.16
    # traversed, so defaulting to it changes nothing for anybody.
    record = read_governance_record(paths) if paths.workitem else None
    classification = (record or {}).get("classification") or {}
    proposed = classification.get("flow")
    state["flow"] = (
        proposed if isinstance(proposed, str) and proposed else DEFAULT_FLOW
    )
    # T08/§14 — R1 and R2, evaluated HERE because this is the single
    # flow-binding site, and evaluated *before* the first `mkdir` below so a
    # refusal creates nothing at all. A pure reader: it returns the derived
    # baseline status and writes nothing. The status is recorded in the
    # `flow_selected` entry, so the facts the binding decision rested on stay
    # auditable. The flow and the opt-in are passed in as plain values so this
    # command never names a repository-configuration member itself (§11).
    baseline_at_binding = baseline_precondition(
        paths, state["flow"], bool(classification.get("rediscovery")))
    # `init` is the one mover that deliberately does NOT go through
    # `apply_advance` — governance is not an `init` precondition (T06) — so it
    # reads the flow directly, exactly as it read the registry chain before.
    flow = flow_for_state(state, consts)
    state["progress"] = flow.progress_for("requirements_check")

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
    append_audit(
        paths,
        state,
        phase="requirements_check",
        event="flow_selected",
        message=(
            f"Flow {flow.name} bound: {flow.phase_count} phases, "
            f"{flow.gate_total} gates. "
            + ("Selected by the recorded governance classification."
               if proposed else
               "No governance record proposed one, so the default applies.")
            + f" Repository baseline at binding: {baseline_at_binding}."
            + " A flow is bound once and never re-bound."
        ),
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
    nxt = flow.next_phase("requirements_check")
    state["current_phase"] = nxt
    state["status"] = "pending"
    state["progress"] = flow.progress_for(nxt)
    append_audit(
        paths,
        state,
        phase="requirements_check",
        event="phase_complete",
        message=f"Requirements validated. Advanced to {nxt}.",
    )
    save_state(paths, state, args.session)

    # Strictly after the state commit, and deliberately non-fatal: the context
    # is a disposable convenience (`workitem use --clear` recreates the
    # pre-T03 posture), so a filesystem problem here must not report a
    # successfully initialised workflow as a failure.
    context = None
    if paths.workitem:
        try:
            context = write_active_context(paths, paths.workitem, "init")
        except OSError:
            context = None

    emit(
        "init",
        {
            "project_name": name,
            "workitem": paths.workitem,
            "active_context": (context or {}).get("workitem"),
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
    flow = flow_for_state(state, consts)
    progress = state.get("progress") or (
        flow.progress_for(phase) if flow.contains(phase) else "?"
    )
    label = consts.label_or(phase, flow, phase)
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

    # Advisory surface for the branch policy. `rendered` is deliberately NOT
    # changed: the header is a fixed contract that other tooling matches on.
    mismatch = branch_mismatch(paths)
    if mismatch is not None:
        print(
            "\u26a0\ufe0f Branch mismatch: this WorkItem's execution was started on "
            f"'{mismatch['recorded']}', the checkout is on "
            f"'{mismatch['current']}'.",
            file=sys.stderr,
        )

    emit(
        "header",
        {
            "rendered": rendered,
            "phase": state.get("current_phase"),
            "status": state.get("status"),
            "progress": state.get("progress"),
            "label": consts.label_or(
                state.get("current_phase", ""), flow_for_state(state, consts)
            ),
            "branch_mismatch": mismatch,
        },
    )
    return EXIT_OK


def cmd_resume(args, paths: Paths) -> int:
    """Everything a cold session needs to pick a WorkItem back up. Read-only.

    Contract §16's exit criterion is that *a fresh Claude session can resume a
    WorkItem safely and load only relevant phase context*, and TP-006 says
    correctness may never depend on old conversation context. This is that
    criterion as one call: identity, position, what is pending, and what to
    read next — all reconstructed from disk by a process that has never seen
    the conversation.

    It is **pure composition**. Every value is produced by the derivation the
    dedicated command already uses: `render_header` for the header,
    `flow_for_state` and `Flow` for position and traversal,
    `gate_disposition` for the requirement model, `branch_mismatch` for the
    branch, `Constants.capabilities_for` for what to load. A second renderer
    or a second requirement derivation would be the invariant-7 violation this
    phase exists to defend against.

    It **writes nothing**: no state, no audit entry, no lock touch, and
    deliberately no migration. A read-only command that silently migrates is
    not read-only; a caller that needs `migrate` calls `migrate`.
    """
    consts = load_constants(paths)
    state = read_state(paths)
    flow = flow_for_state(state, consts)
    phase = state.get("current_phase")
    gate_key = gate_key_for(consts, phase) if phase else None

    gate = None
    if gate_key:
        disposition = gate_disposition(paths, consts, state, gate_key)
        gate = {
            "gate": gate_key,
            "gate_number": flow.gate_number(gate_key),
            "gate_total": flow.gate_total,
            "decision": approval_decision(state, gate_key),
            "required": (None if disposition is None
                         else disposition["disposition"] == "required"),
            "requirement_reasons": (None if disposition is None
                                    else disposition["reasons"]),
        }

    emit(
        "resume",
        {
            "workitem": paths.workitem,
            "flow": flow.name,
            "current_phase": phase,
            "status": state.get("status"),
            "progress": state.get("progress"),
            "position": flow.position(phase),
            "next_phase": flow.next_phase(phase),
            "label": consts.label_or(phase, flow),
            "header": render_header(state, consts),
            "gate": gate,
            # What is outstanding. Each one is a thing a resuming session
            # would otherwise have to notice for itself, which is precisely
            # what "correctness must not depend on conversation history"
            # forbids.
            "pending": {
                "drift_queue": state.get("drift_queue") or [],
                "pending_confirm_action": state.get("pending_confirm_action"),
                # T11 D13: the flag alone is no longer the whole fact. A
                # session resuming from disk has to be able to see which
                # checkout the outstanding acknowledgement was given for, or
                # it would have to re-derive it from the ledger.
                "pending_branch_ack": state.get("pending_branch_ack"),
                "pending_phase": state.get("pending_phase"),
                "phase_checkpoint": state.get("phase_checkpoint"),
                "clarification_phase": state.get("clarification_phase"),
            },
            "branch_mismatch": branch_mismatch(paths),
            "capabilities": consts.capabilities_for(phase),
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
        f"| Label | {consts.label_or(phase, flow_for_state(state, consts), phase)} |",
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
        f"- Feature ID: {speckit_ref(state)['featureId'] or 'none'}",
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


def workitem_id_wellformed(value: object) -> bool:
    """True for an id `workitem create` could actually have minted.

    Two shapes exist: the normalised kebab-case id and the `--auto-generate`
    `WI-<name>-<UTC>` id, which carries an uppercase prefix and so does *not*
    match `WORKITEM_ID_RE`. Anything else — a path fragment, a traversal, an
    empty cell — is not an id at all. Single source for that question, so the
    active context and `validate` cannot disagree about it.
    """
    if not isinstance(value, str) or not value:
        return False
    return bool(WORKITEM_ID_RE.match(value) or AUTO_ID_RE.match(value))


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


def current_branch(paths: Paths) -> str | None:
    """The checked-out branch, or ``None``.

    ``None`` covers both "git is not available here" and "HEAD is detached" —
    neither is a branch, and neither is ever a refusal. Single source for the
    detached-HEAD rule, which `workitem create`, the resolution ladder, the
    active context and the branch guard all depend on.
    """
    branch = _git_value(paths, "rev-parse", "--abbrev-ref", "HEAD")
    return None if branch == "HEAD" else branch


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

    branch = current_branch(paths)  # None when detached or git is absent
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
    # `validate` exists to diagnose repositories that are too broken to
    # resolve, so it must never be gated on resolution succeeding. It runs the
    # ladder itself, speculatively, and turns a refusal into a finding.
    "validate",
    # `config` is repository-global by definition. Contract §11's exit
    # criterion is that it resolves *independently* of WorkItem runtime state,
    # so binding a WorkItem first would contradict the boundary it creates.
    "config",
    # T06: `governance policy` reads a repository-scoped policy and must
    # resolve with no WorkItem bound, exactly like `config`. The WorkItem-
    # scoped members of the group (`assess`, `show`, `gates`) bind explicitly
    # through `bind_workitem`, so the ladder is exercised, not bypassed.
    "governance",
    # T08: `discovery schema` reports the closed §14 vocabulary and must be
    # answerable before any workflow exists — it is what the prompt layer
    # reads instead of restating the category ids. `assess` and `show` bind
    # explicitly through `bind_for_discovery`.
    "discovery",
    # T08: the baseline is repository-level by definition — §14's convergence
    # invariant is a property of the repository, not of any WorkItem — so both
    # its readers resolve without one, exactly like `config`.
    "baseline",
})


def registered_workitem_ids(paths: Paths) -> list[str]:
    """Registered ids, in creation order. The index is the only source."""
    return [row["WorkItem"] for row in read_index(paths)]


# --------------------------------------------------------------------------
# Persisted active context (contract §9 rung 3)
# --------------------------------------------------------------------------
#
# Developer-local and gitignored: it records which WorkItem *this* working
# directory is driving, so a second clone or `git worktree` is independent by
# construction rather than by coordination (TP-007, contract §9 "Do not
# implement distributed locking").
#
# It is written by exactly three commands — `init`, `migrate-workflow` and
# `workitem use` — and by nothing else. `bind_workitem` must never write it:
# its purity is what lets `.claude/hooks/hooks.py::dirty_tree` call it
# speculatively from a PreToolUse callback, and a hook that writes state is a
# second writer (CLAUDE.md invariant 6).

ACTIVE_CONTEXT_NAME = ".active-context.json"
ACTIVE_CONTEXT_SETTERS = ("init", "use", "migrate-workflow")


def active_context_file(paths: Paths) -> Path:
    return workitems_root(paths) / ACTIVE_CONTEXT_NAME


def read_active_context(paths: Paths) -> dict | None:
    """The persisted context, or None. Never raises.

    Same posture as ``workitem_metadata``: the context is a convenience, so a
    missing, unreadable or malformed file degrades resolution to the rungs
    below it and is never itself a refusal.
    """
    target = active_context_file(paths)
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_active_context(paths: Paths, workitem_id: str, set_by: str) -> dict:
    """Persist the active context. **The only writer of that file.**

    T11 D9 makes ``ACTIVE_CONTEXT_SETTERS`` load-bearing rather than
    documentary (T03-4). The fact it encodes — that exactly three commands may
    set the context — was true but unenforced, so a fourth writer could have
    been added without anything objecting. This is a *programming* error, not
    a user input error: no CLI argument can reach it, so it raises
    ``ValueError`` rather than becoming a refusal with a reason string that
    could never be triggered from outside.
    """
    if set_by not in ACTIVE_CONTEXT_SETTERS:
        raise ValueError(
            f"write_active_context: set_by={set_by!r} is not one of "
            f"{ACTIVE_CONTEXT_SETTERS}. The active context has exactly three "
            "writers; adding a fourth means changing that constant "
            "deliberately, not by accident."
        )
    payload = {
        "workitem": workitem_id,
        "branch": current_branch(paths),
        "setAt": now_iso(),
        "setBy": set_by,
        "sdleVersion": CURRENT_VERSION,
    }
    write_atomic(active_context_file(paths), json.dumps(payload, indent=2) + "\n")
    return payload


def clear_active_context(paths: Paths) -> bool:
    target = active_context_file(paths)
    if not target.is_file():
        return False
    target.unlink()
    return True


def active_context_workitem(paths: Paths, known: list[str]) -> str | None:
    """The context's WorkItem when the context is still *valid*, else None.

    Validity is deliberately strict and deliberately silent: an invalid context
    is skipped, never refused, so a stale file can never brick a repository.
    """
    data = read_active_context(paths)
    if data is None:
        return None
    workitem_id = data.get("workitem")
    if not workitem_id_wellformed(workitem_id):
        return None
    if workitem_id not in known:
        return None
    target = workitems_root(paths) / workitem_id
    if target.is_symlink() or not target.is_dir():
        return None
    recorded = data.get("branch")
    if isinstance(recorded, str) and recorded:
        here = current_branch(paths)
        if here is not None and here != recorded:
            return None  # stale: the context was set on another branch
    return workitem_id


def cwd_workitem(paths: Paths) -> str | None:
    """The WorkItem directory the launch CWD sits inside, or None.

    Returns the *directory name*, registered or not: rung 2 has to be able to
    tell "inside an unregistered WorkItem" apart from "not inside one at all",
    because those two cases have opposite outcomes.
    """
    launch = paths.launch_cwd
    if launch is None:
        return None
    root = workitems_root(paths)
    try:
        relative = launch.relative_to(root)
    except ValueError:
        return None
    parts = relative.parts
    if not parts:
        return None  # standing in workitems/ itself is not a selection
    return parts[0]


def branch_candidates(paths: Paths, known: list[str]) -> list[str]:
    """Registered WorkItems whose recorded branch is the current branch.

    A *set*, never a pick: the caller applies contract §9's 0/1/>1 rule to it.
    Two WorkItems created on the same branch therefore stay ambiguous.
    """
    here = current_branch(paths)
    if here is None:
        return []
    matches = []
    for workitem_id in known:
        bound = dataclass_replace(paths, workitem=workitem_id)
        recorded = ((workitem_metadata(bound) or {}).get("git") or {})
        execution = read_execution(bound) or {}
        recorded_branches = {
            recorded.get("initialBranch"),
            ((execution.get("git") or {}).get("branch")),
        }
        if here in {b for b in recorded_branches if isinstance(b, str) and b}:
            matches.append(workitem_id)
    return matches


def cmd_workitem_resolve(args, paths: Paths) -> int:
    """Report what the ladder would do. Diagnostic: it never refuses.

    This is the only input the prompt layer gets for contract §9 rungs 5
    (AI-assisted inference) and 6 (ask user). Inference may rank or annotate
    this candidate list; it is never an independent resolver, and the user's
    answer re-enters the engine as an explicit ``--workitem`` — that is,
    as rung 1. A structurally corrupt registry still surfaces as
    ``read_index``'s ``index_malformed`` integrity failure, which is a
    diagnosis rather than a refusal.
    """
    decision = resolve_decision(paths, args.workitem)
    matches = branch_candidates(paths, decision.known) if decision.known else []
    emit("workitem resolve", {
        "resolved": decision.workitem,
        "rung": decision.rung,
        "reason": decision.reason,
        "candidates": (
            decision.candidates
            or candidate_evidence(paths, decision.known, matches)
        ),
        "workitems": decision.known,
        "launch_cwd": (
            None if paths.launch_cwd is None else str(paths.launch_cwd)
        ),
        "project_root": str(paths.project_root),
        "branch": current_branch(paths),
        "active_context": (read_active_context(paths) or {}).get("workitem"),
    })
    return EXIT_OK


def cmd_workitem_use(args, paths: Paths) -> int:
    """Persist (or clear) the active context for this working directory.

    ``workitem`` is RUNTIME_FREE, so `use` never passes through
    ``bind_workitem`` and nothing else would validate the id before it is
    written. `use` therefore performs rung 1's own check and refuses an
    unregistered id: persisting a context that can never bind is a footgun
    with no upside. Validation precedes the write, so a refused `use` leaves
    any existing context byte-unchanged.

    **T11 D8** (T03-5, T03-6). Two corrections, both about the CLI contract:

    * an unwritable or undeletable context file is a **refusal**, not a
      traceback — every sibling command already turns `OSError` into a named
      refusal, and a traceback carries no reason string and no exit-code
      meaning;
    * the missing-flag `UsageError` is `workitem_flag_required`, not
      `workitem_required`. One reason string must not mean two things across
      two exit codes (invariant 7): `workitem_required` is the *resolution*
      refusal at exit 1, and a missing flag is a usage error at exit 2.
    """
    target = active_context_file(paths)
    if getattr(args, "clear", False):
        try:
            cleared = clear_active_context(paths)
        except OSError as exc:
            raise Refused(
                "active_context_unwritable",
                f"The active context at {target.name} could not be removed: "
                f"{exc}. Fix the permissions and re-run, or delete the file "
                "by hand — it is developer-local and gitignored.",
                {"path": str(target), "error": str(exc)},
            ) from exc
        emit("workitem use", {
            "workitem": None, "cleared": cleared, "path": str(target),
        })
        return EXIT_OK

    requested = getattr(args, "use_workitem", None) or args.workitem
    if not requested:
        raise UsageError(
            "workitem_flag_required",
            "`workitem use` needs a target: --workitem <id>, or --clear.",
            {},
        )

    known = registered_workitem_ids(paths)
    if requested not in known:
        raise Refused(
            "workitem_unknown",
            f"No WorkItem '{requested}' in workitems/index.md. Create it "
            "with `workitem create --name <name>`, or pick one of the "
            "registered ids.",
            {"requested": requested, "workitems": known},
        )

    try:
        payload = write_active_context(paths, requested, "use")
    except OSError as exc:
        raise Refused(
            "active_context_unwritable",
            f"The active context at {target.name} could not be written: "
            f"{exc}. Re-run with `--workitem {requested}` in the meantime — "
            "the context is a convenience, never a requirement.",
            {"path": str(target), "workitem": requested, "error": str(exc)},
        ) from exc
    emit("workitem use", {
        "workitem": requested,
        "branch": payload["branch"],
        "set_at": payload["setAt"],
        "set_by": payload["setBy"],
        "cleared": False,
        "path": str(target),
    })
    return EXIT_OK


def legacy_state_present(paths: Paths) -> bool:
    return (paths.legacy_workflow / "state.json").is_file()


@dataclass
class Resolution:
    """One run of the ladder, as data.

    Exactly one decision function exists (invariant 7): ``bind_workitem``
    turns this into a binding or a refusal, and ``workitem resolve`` reports
    it. Neither re-implements a rung.
    """

    known: list[str] = field(default_factory=list)
    workitem: str | None = None
    rung: str | None = None
    reason: str | None = None
    candidates: list[dict] = field(default_factory=list)
    data: dict = field(default_factory=dict)


def candidate_evidence(
    paths: Paths, known: list[str], branch_matches: list[str]
) -> list[dict]:
    """Why each registered WorkItem is plausible — evidence, never a ranking.

    The order is the registry's creation order and carries no preference. This
    is the only input the prompt layer receives for contract §9 rungs 5 and 6;
    the engine never infers and never picks.
    """
    inside = cwd_workitem(paths)
    persisted = (read_active_context(paths) or {}).get("workitem")
    valid_context = active_context_workitem(paths, known)
    here = current_branch(paths)

    entries = []
    for workitem_id in known:
        evidence = []
        if workitem_id == inside:
            evidence.append("cwd")
        if workitem_id == persisted:
            evidence.append(
                "context" if workitem_id == valid_context else "context:stale"
            )
        if workitem_id in branch_matches:
            evidence.append(f"branch:{here}")
        bound = dataclass_replace(paths, workitem=workitem_id)
        if bound.state_file.is_file():
            evidence.append("runtime")
        entries.append({"id": workitem_id, "evidence": evidence})
    return entries


def resolve_decision(
    paths: Paths, explicit: str | None = None, *, for_init: bool = False
) -> Resolution:
    """Run contract §9's ladder and report the outcome. Pure.

    Nothing is printed and nothing is written — in particular the active
    context is *read* here and only ever *written* by `init`,
    `migrate-workflow` and `workitem use`. That purity is what lets
    ``.claude/hooks/hooks.py::dirty_tree`` call the ladder speculatively from a
    PreToolUse callback without becoming a second writer (invariant 6).

    Ladder:

    1. explicit ``--workitem <id>``, which must be registered;
    2. else the launch CWD is inside ``workitems/<x>/`` — registered binds,
       unregistered *refuses* rather than falling through, because binding a
       different WorkItem while the developer stands inside ``<x>`` is exactly
       the silent wrong pick §9 forbids;
    3. else the sole registered WorkItem. §9's own rule is
       ``1 valid candidate -> use``, and with one registered WorkItem the
       rungs below can only return that same id or nothing;
    4. else a persisted *valid* active context;
    5. else a *unique* Git-branch match;
    6. else zero WorkItems -> ``none`` (refuse ``workitem_required``);
    7. else -> ``ambiguous``. Never pick one.

    Rungs 4 and 5 are only reachable with two or more registered WorkItems, so
    the git subprocess of rung 5 never runs in a single-WorkItem repository.

    **T11 deleted the transitional rung** that bound the repository-global
    ``.workflow/`` runtime when nothing was registered. It was *deleted, not
    replaced by an inference*: with zero WorkItems the answer is ``none``
    whether or not legacy state exists, and the ladder still never guesses.
    A legacy runtime is now a migration source and a project-root marker only.
    ``bind_workitem`` names the two-step recovery in its refusal, and both
    steps (`workitem create`, `migrate-workflow`) are RUNTIME_FREE, so neither
    reaches this ladder and neither can be locked out by the removal.

    ``for_init`` is the one exception left. `init` reports ``legacy_present``
    whenever legacy state exists, *whatever* the registered count. Proceeding
    would create a second runtime beside a legacy one that `migrate-workflow`
    would then refuse to move (`target_exists`).
    """
    known = registered_workitem_ids(paths)
    decision = Resolution(known=known)

    if for_init and legacy_state_present(paths):
        decision.reason = "legacy_present"
        return decision

    # Rung 1 — explicit.
    if explicit:
        if explicit not in known:
            decision.reason = "unknown"
            decision.data = {"requested": explicit}
            return decision
        decision.workitem, decision.rung = explicit, "explicit"
        return decision

    # Rung 2 — the launch CWD, which must run *before* the sole-registered
    # rung: otherwise a lone registered WorkItem would bind while the
    # developer stands inside an unregistered one.
    inside = cwd_workitem(paths)
    if inside is not None:
        if inside in known:
            decision.workitem, decision.rung = inside, "cwd"
            return decision
        if (workitems_root(paths) / inside).is_dir():
            decision.reason = "unregistered_directory"
            decision.data = {"directory": inside}
            return decision

    # Rung 3 — the sole registered WorkItem.
    if len(known) == 1:
        decision.workitem, decision.rung = known[0], "sole"
        return decision

    branch_matches: list[str] = []
    if known:
        # Rung 4 — a persisted, still-valid active context.
        persisted = active_context_workitem(paths, known)
        if persisted is not None:
            decision.workitem, decision.rung = persisted, "context"
            return decision

        # Rung 5 — a unique branch match. A *set* is computed and §9's
        # 0/1/>1 rule applied to it: two WorkItems on one branch stay
        # ambiguous, and there is no tie-break, no ordering preference and no
        # "most recent".
        branch_matches = branch_candidates(paths, known)
        if len(branch_matches) == 1:
            decision.workitem, decision.rung = branch_matches[0], "branch"
            return decision

    if not known:
        # Rung 6 — nothing is registered. A legacy `.workflow/` on disk does
        # not change the answer (T11): it is a migration source, not a
        # runtime, and `bind_workitem` names the recovery path in its refusal.
        decision.reason = "none"
        return decision

    decision.reason = "ambiguous"
    decision.candidates = candidate_evidence(paths, known, branch_matches)
    return decision


def bind_workitem(
    paths: Paths, explicit: str | None = None, *, for_init: bool = False
) -> Paths:
    """Resolve the active WorkItem and return `paths` bound to it.

    Pure: it either returns a bound ``Paths`` or raises ``Refused``. Nothing is
    printed and nothing is written, so the hooks can call it speculatively.
    The ladder itself lives in ``resolve_decision``; this function only turns
    a decision into a binding or into the refusal the contract names.

    **T11 invariant (R2): every non-raising return names a WorkItem.** There
    is no longer any return path that yields ``paths`` with ``workitem is
    None``, so no command downstream needs a carve-out for one.
    """
    decision = resolve_decision(paths, explicit, for_init=for_init)

    if decision.reason == "legacy_present":
        raise Refused(
            "legacy_workflow_present",
            "A repository-global workflow still exists at "
            f"{paths.legacy_workflow.name}/state.json. Move it under a "
            "WorkItem first: `migrate-workflow --workitem <id>`. SDLE will "
            "not run two runtimes side by side.",
            {"legacy_state": str(paths.legacy_workflow / "state.json")},
        )

    if decision.reason == "unknown":
        raise Refused(
            "workitem_unknown",
            f"No WorkItem '{explicit}' in workitems/index.md. Create it "
            "with `workitem create --name <name>`, or pick one of the "
            "registered ids.",
            {"requested": explicit, "workitems": decision.known},
        )

    if decision.reason == "unregistered_directory":
        directory = decision.data["directory"]
        raise Refused(
            "workitem_unregistered",
            f"This directory is inside workitems/{directory}/, but "
            f"'{directory}' is not registered in workitems/index.md. SDLE "
            "will not bind a different WorkItem while you are standing in "
            "this one. Register it with `workitem create`, or re-run from "
            "elsewhere with `--workitem <id>`.",
            {
                "directory": directory,
                "workitems": decision.known,
                "path": str(workitems_root(paths) / directory),
            },
        )

    if decision.reason == "none":
        if legacy_state_present(paths):
            # A pre-v1.14 repository. T11 removed the transitional rung that
            # bound `.workflow/` directly, so this refusal is now the *only*
            # signpost such a repository ever gets. It must name both recovery
            # steps, in order, or the repository looks bricked (T02 NB-2).
            # Same reason string, same exit code: no CLI-contract break.
            legacy = paths.legacy_workflow / "state.json"
            raise Refused(
                "workitem_required",
                "No WorkItem is registered, but a pre-v1.14 workflow still "
                f"exists at {paths.legacy_workflow.name}/state.json. SDLE no "
                "longer runs a repository-global runtime. Recover it in two "
                "steps, in this order:\n"
                "  1. `workitem create --name <name>`\n"
                "  2. `migrate-workflow --workitem <id>`\n"
                f"The migration never modifies {paths.legacy_workflow.name}/ "
                "— it is left in place as an archive.",
                {"workitems": [], "legacy_state": str(legacy)},
            )
        raise Refused(
            "workitem_required",
            "No WorkItem is registered in this repository. Create one first: "
            "`workitem create --name <name>`.",
            {"workitems": []},
        )

    if decision.reason == "ambiguous":
        raise Refused(
            "workitem_ambiguous",
            f"{len(decision.known)} WorkItems are registered and none was "
            "named. Re-run with `--workitem <id>`. SDLE never picks one for "
            "you.",
            {"workitems": decision.known, "candidates": decision.candidates},
        )

    return dataclass_replace(paths, workitem=decision.workitem)


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
#
# **D04 (SDLE-DEFECT-STABILIZATION-01)** appends a collision-resistant suffix,
# `muh-20260816T171501Z-1a2b3c4d`. The readable prefix is unchanged. At second
# resolution alone, two executions in one second shared an id, and the id is a
# key: it names every evidence file (`governance-<id>.json`, …) and it is the
# governance ledger's de-duplication marker. The second execution therefore
# overwrote the first one's evidence and never reached the ledger at all. A
# historical id without the suffix is still read everywhere, because nothing
# parses an id — each one is compared whole, as an opaque key. See ADR-009.


# How many fresh ids an evidence writer tries before refusing. A collision needs
# the same user, the same second and the same 32 random bits, so a second
# attempt is already vanishingly rare; the bound exists so a broken random
# source refuses instead of looping forever.
EXECUTION_ID_ATTEMPTS = 3


def execution_suffix() -> str:
    """The collision-resistant half of an execution id: 32 random bits."""
    return secrets.token_hex(4)


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
    return f"{execution_prefix(paths)}-{compact}-{execution_suffix()}"


def reserve_evidence(paths: Paths, directory: Path, stamp: str,
                     name: "Callable[[str], str]") -> tuple[str, Path]:
    """Allocate an execution id whose evidence file does not exist yet.

    The file is claimed with an exclusive create before anything is written
    into it, so no evidence file is ever replaced: an id whose file is already
    taken is abandoned for a fresh one. The caller then fills the claimed file
    through the usual atomic writer, which replaces only this empty
    placeholder.
    ``name`` maps an id to the file name, since each kind of evidence names
    its file differently.

    A crash between the claim and the fill leaves an empty file. That is the
    fail-safe direction: an empty evidence file is never mistaken for
    evidence, and a reader that needs it refuses it as malformed.
    """
    directory.mkdir(parents=True, exist_ok=True)
    tried = []
    for _ in range(EXECUTION_ID_ATTEMPTS):
        execution_id = execution_identity(paths, stamp)
        target = directory / name(execution_id)
        try:
            with open(target, "x", encoding="utf-8"):
                pass
        except FileExistsError:
            tried.append(execution_id)
            continue
        return execution_id, target
    raise IntegrityError(
        "execution_id_collision",
        f"Could not allocate an unused execution id after {len(tried)} "
        f"attempts ({', '.join(tried)}): each one's evidence file already "
        "exists. Nothing was recorded and no existing evidence was touched. "
        "This means the random source is not random; re-run the command.",
        {"tried": tried, "directory": str(directory)},
    )


def write_execution_file(paths: Paths, execution_id: str, stamp: str) -> dict:
    payload = {
        "executionId": execution_id,
        "workitem": paths.workitem,
        "startedAt": stamp,
        "sdleVersion": CURRENT_VERSION,
        # Contract §9 "record branch and starting SHA". This lives on the
        # execution record, not in state.json: it describes *this* run rather
        # than the workflow, so it needs no schema version and no migration
        # row. A missing git is never a refusal - the values are simply null.
        "git": {
            "branch": current_branch(paths),
            "startSha": _git_value(paths, "rev-parse", "HEAD"),
            "worktree": str(paths.project_root),
        },
    }
    write_atomic(paths.execution_file, json.dumps(payload, indent=2) + "\n")
    return payload


def read_execution(paths: Paths) -> dict | None:
    """The bound WorkItem's ``execution.json``, or None. Never raises: like
    ``workitem.json`` it is descriptive, so an absent or unreadable file
    degrades to "nothing recorded" rather than to a refusal."""
    target = paths.execution_file
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def recorded_branch(paths: Paths) -> str | None:
    """The branch this WorkItem's execution was started on, or None."""
    branch = ((read_execution(paths) or {}).get("git") or {}).get("branch")
    return branch if isinstance(branch, str) and branch else None


# --------------------------------------------------------------------------
# Branch-mismatch policy (contract §9 "Branch/worktree rules")
# --------------------------------------------------------------------------
#
# "Branch mismatch produces explicit warning/refusal depending on safety
# impact." The refusal set is exactly the commands that either advance the
# lifecycle or fingerprint working-tree content: running one against the wrong
# checkout produces a wrong-but-plausible record, which is worse than an
# inconvenient refusal. Everything else — `state get`, `header`, `state dump`,
# `gate show`, `gate reject`, `drift check`, `audit verify`, `doctor`,
# `workitem list`, `workitem resolve`, `validate` — warns. `gate reject` is
# deliberately advisory: a rejection can neither advance the workflow nor
# fingerprint an artifact as approved, so refusing it would be pure
# obstruction.

BRANCH_CRITICAL_ACTIONS = frozenset({
    "advance",
    ("gate", "approve"),
    ("gate", "omit"),
    "skip",
    "restart",
    "reset",
    ("implement", "preflight"),
    ("manifest", "build"),
    ("drift", "rebaseline"),
    ("artifact", "record"),
})


def action_key(args) -> str | tuple[str, str]:
    """The command, as `BRANCH_CRITICAL_ACTIONS` spells it."""
    subcommand = getattr(args, "subcommand", None)
    command = getattr(args, "command", None)
    return (command, subcommand) if subcommand else command


def action_name(args) -> str:
    key = action_key(args)
    return " ".join(key) if isinstance(key, tuple) else str(key)


def _own_confirm_token(args) -> str | None:
    """The confirmation token this command sets for *itself*, if any.

    Four of the ten critical commands share ``pending_confirm_action`` with
    the branch guard. The guard runs first — running it second livelocks,
    because the command's own check clears the marker and the guard then sets
    its own, so the command's check can never pass. Running it first has the
    mirror hazard: at the confirming invocation the guard would clobber the
    token the command had just set. Passing through on the command's *own*
    token closes that, and it opens nothing: the only way that token can be
    pending is that the command set it on the immediately preceding
    invocation, which the guard had to allow.

    Consequence, deliberate and tested: on a mismatched branch `skip`, `reset`
    and `restart` need two acknowledgements — the branch first, then their
    own.
    """
    key = action_key(args)
    if key == "skip":
        return "skip"
    if key == "reset":
        return "reset"
    if key == "restart":
        return f"restart:{getattr(args, 'to', None)}"
    if key == ("implement", "preflight"):
        return "implement_dirty_tree"
    return None


def branch_mismatch(paths: Paths) -> dict | None:
    """The recorded-versus-current branch disagreement, or None.

    None covers every case where there is nothing to compare: git absent, HEAD
    detached, no recorded branch, or no `execution.json` at all (which is what
    a legacy-bound runtime looks like). Never a refusal by itself.
    """
    recorded = recorded_branch(paths)
    if recorded is None:
        return None
    here = current_branch(paths)
    if here is None or here == recorded:
        return None
    return {"recorded": recorded, "current": here}


def branch_guard(args, paths: Paths, state: dict) -> None:
    """Refuse a lifecycle-critical command on the wrong checkout, once.

    Reuses the existing two-step ``pending_confirm_action`` idiom rather than
    inventing a bypass flag, so the acknowledgement is audited exactly like
    every other one. Advisory commands never reach here.

    **T11 D13 closes the fail-open T03 recorded.** ``pending_confirm_action``
    is a *flag*: it said an acknowledgement was outstanding, never what had
    been acknowledged. So the second invocation could arrive on a **third**
    branch and be waved through on an acknowledgement the user had given for a
    different checkout — the guard's whole subject matter, unaudited. The new
    ``pending_branch_ack`` field records the branch that was acknowledged, and
    the second step must match it. A mismatch re-arms the guard against the
    branch you are actually on and refuses again; it never silently proceeds.

    Both fields are cleared together on acceptance, and ``pending_branch_ack``
    has exactly one writer — this function — so it cannot drift out of step
    with the flag it qualifies.
    """
    if action_key(args) not in BRANCH_CRITICAL_ACTIONS:
        return
    mismatch = branch_mismatch(paths)
    if mismatch is None:
        return

    pending = state.get("pending_confirm_action")
    own = _own_confirm_token(args)
    if own is not None and pending == own:
        return

    phase = state.get("current_phase", "unknown")
    session = getattr(args, "session", None)

    if pending == "branch_mismatch":
        acknowledged = state.get("pending_branch_ack")
        if acknowledged == mismatch["current"]:
            state["pending_confirm_action"] = None
            state["pending_branch_ack"] = None
            append_audit(
                paths, state, phase=phase, event="branch_mismatch_accepted",
                message=f"User acknowledged running `{action_name(args)}` on "
                        f"branch '{mismatch['current']}' while this WorkItem's "
                        f"execution was started on '{mismatch['recorded']}'.",
            )
            save_state(paths, state, session)
            return

        # T11 D13: the acknowledgement was for a different checkout. Re-arm
        # against the branch we are actually on rather than consuming it.
        state["pending_branch_ack"] = mismatch["current"]
        append_audit(
            paths, state, phase=phase, event="branch_ack_stale",
            message=f"Branch-mismatch acknowledgement rejected before "
                    f"`{action_name(args)}`: the outstanding acknowledgement "
                    f"was for branch '{acknowledged}', but the checkout is now "
                    f"'{mismatch['current']}'. An acknowledgement names one "
                    "checkout; it is not a standing permission. The guard was "
                    "re-armed against the current branch.",
        )
        save_state(paths, state, session)
        raise Refused(
            "branch_mismatch",
            f"The outstanding branch acknowledgement was given for "
            f"'{acknowledged}', but the checkout is now "
            f"'{mismatch['current']}' and this WorkItem's execution was "
            f"started on '{mismatch['recorded']}'. `{action_name(args)}` "
            "either advances the lifecycle or fingerprints working-tree "
            "content, so it will not run on the strength of an "
            "acknowledgement for a different branch. Switch back, or re-run "
            "the same command here to acknowledge this checkout (logged).",
            {
                "recorded": mismatch["recorded"],
                "current": mismatch["current"],
                "acknowledged": acknowledged,
                "workitem": paths.workitem,
                "action": action_name(args),
            },
        )

    state["pending_confirm_action"] = "branch_mismatch"
    state["pending_branch_ack"] = mismatch["current"]
    append_audit(
        paths, state, phase=phase, event="branch_mismatch_guard",
        message=f"Branch-mismatch guard triggered before "
                f"`{action_name(args)}`: recorded '{mismatch['recorded']}', "
                f"current '{mismatch['current']}'.",
    )
    save_state(paths, state, session)
    raise Refused(
        "branch_mismatch",
        f"This WorkItem's execution was started on branch "
        f"'{mismatch['recorded']}', but the checkout is on "
        f"'{mismatch['current']}'. `{action_name(args)}` either advances the "
        "lifecycle or fingerprints working-tree content, so running it here "
        "would record the wrong checkout. Switch back, or re-run the same "
        "command on this branch to proceed anyway (logged).",
        {
            "recorded": mismatch["recorded"],
            "current": mismatch["current"],
            "workitem": paths.workitem,
            "action": action_name(args),
        },
    )


# --------------------------------------------------------------------------
# validate — contract §9 "Add validation"
# --------------------------------------------------------------------------
#
# Seven checks, one per §9 bullet. `validate` is RUNTIME_FREE and resolves
# *speculatively*, because the repositories it exists to diagnose are exactly
# the ones where resolution refuses: a refusal becomes a finding, never an
# exit. Findings are `{check, severity, workitem, detail, path}`; any `error`
# is an integrity failure (exit 3), warnings alone leave exit 0.
#
# A structurally corrupt registry still surfaces as `read_index`'s
# `index_malformed` integrity failure. That is a correct diagnosis at the same
# exit code, so it is left to propagate rather than caught and reshaped.

VALIDATE_ERROR = "error"
VALIDATE_WARNING = "warning"


def _finding(check: str, severity: str, detail: str, *,
             workitem: str | None = None, path: Path | None = None) -> dict:
    return {
        "check": check,
        "severity": severity,
        "workitem": workitem,
        "detail": detail,
        "path": None if path is None else str(path),
    }


# --------------------------------------------------------------------------
# Repository configuration boundary — contract §11
# --------------------------------------------------------------------------
#
# `.sdle/` at the repository root holds global configuration, policy
# definitions, shared templates, the future baseline and implementation-
# transition metadata. It is a *different boundary* from `workitems/<id>/.sdle/`,
# which holds lifecycle state, execution, audit, evidence and manifests.
#
# T05 establishes the boundary and moves **no lifecycle rule into it**: the
# 18-phase behaviour stays authoritative and nothing in the lifecycle reads
# `config.json`. `configVersion` is therefore a namespace of its own — it is
# not `workflow_version`, it is not a state field, and it gets no
# VERSION_MIGRATION row.
#
# Policy format is JSON, decided explicitly (see
# docs/architecture/ADR-002-repository-configuration-boundary.md): it keeps the
# deterministic core standard-library-only, so the engine runs anywhere Python
# 3.11+ exists with no install step.

REPO_CONFIG_DEFAULTS = {"configVersion": "1", "policyFormat": "json"}
SUPPORTED_CONFIG_VERSIONS = ("1",)
SUPPORTED_POLICY_FORMATS = ("json",)


def read_repo_config(paths: Paths) -> dict:
    """The effective repository configuration. Reads; never writes. FAIL-CLOSED.

    Absent `config.json` yields the defaults verbatim — which is why T05 is a
    no-op for every repository that predates it, and which is safe because an
    absent document is a real answer. An **unreadable** one is not, and until
    T09 this reader returned the defaults from inside its exception handler.
    That shape was defensible only because its one caller runs
    `repo_config_findings` first and already refuses on every condition the
    handler swallowed — a safety property held somewhere else, which is the
    kind of arrangement that stops being true the first time a second caller
    appears. §15's whole subject is not weakening governance silently, so the
    shape goes: presence and readability are different questions, and only the
    first of them has a default.

    Observable behaviour is unchanged. `repo_config_findings` remains the
    single predicate for soundness, it still fires first for both consumers,
    and its `config_malformed` finding still carries the same reason and exit
    code. What changes is that this reader can no longer be the place a
    corrupt boundary turns into a plausible default.
    """
    config = dict(REPO_CONFIG_DEFAULTS)
    target = paths.config_file
    if not target.is_file():
        return config

    # Written as "decide the problem, then raise once" rather than as three
    # raise sites, and deliberately not extracted into a helper: the set of
    # functions permitted to reach the repository configuration boundary is
    # closed and asserted by exact equality, and widening that containment
    # proof to buy one message constructor is the wrong trade. Nothing is
    # returned from a handler, which is the property this change exists for.
    detail: str | None = None
    document: object = None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except OSError as exc:
        detail = f"it cannot be read: {exc}"
    except (json.JSONDecodeError, ValueError) as exc:
        detail = f"it is not valid JSON: {exc}"
    else:
        if not isinstance(document, dict):
            detail = "it is not a JSON object"
    if detail is not None:
        raise Refused(
            "config_malformed",
            f"{paths.config_root_relative}/{target.name} cannot be used: "
            f"{detail}. Repository configuration is a boundary, not a hint — "
            "fix the file or delete it to fall back to the documented "
            "defaults.",
            {"path": str(target), "detail": detail},
        )
    config.update(document)
    return config


def repo_config_findings(paths: Paths) -> list[dict]:
    """The single answer to "is this repository's configuration boundary
    sound".

    Two consumers — `config show`/`config init`, which refuse on an error, and
    `validate`, which reports one. One implementation, so they can never
    disagree about the same repository (invariant 7).
    """
    root = paths.project_root
    if root.name == "workitems" or root.parent.name == "workitems":
        return [_finding(
            "config_root_inside_workitem", VALIDATE_ERROR,
            f"the resolved repository root '{root}' is the WorkItem registry "
            "or a WorkItem directory; repository configuration is owned by "
            "the repository, never by a WorkItem",
            path=paths.config_root,
        )]

    target = paths.config_file
    if not target.is_file():
        return []
    relative = f"{paths.config_root_relative}/{target.name}"

    detail: str | None = None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        detail = f"{relative} cannot be read: {exc}"
    else:
        if not isinstance(document, dict):
            detail = f"{relative} is not a JSON object"
        elif document.get("configVersion") not in SUPPORTED_CONFIG_VERSIONS:
            detail = (
                f"{relative} declares configVersion "
                f"{document.get('configVersion')!r}; this engine supports "
                + ", ".join(repr(v) for v in SUPPORTED_CONFIG_VERSIONS)
            )
        elif document.get("policyFormat") not in SUPPORTED_POLICY_FORMATS:
            detail = (
                f"{relative} declares policyFormat "
                f"{document.get('policyFormat')!r}; this engine supports "
                + ", ".join(repr(v) for v in SUPPORTED_POLICY_FORMATS)
                + ". The deterministic core is standard-library-only, so any "
                "other policy format requires a parser dependency that has "
                "been explicitly accepted first — and a home-grown parser is "
                "not an option."
            )
    if detail is None:
        return []
    return [_finding("config_malformed", VALIDATE_ERROR, detail, path=target)]


def workitem_runtime_member_names(bound: Paths) -> tuple[str, ...]:
    """The file and directory names a WorkItem runtime owns.

    Derived from an **already bound** ``Paths`` rather than re-listed, so a
    later phase that adds a runtime member inherits the leak check for free
    (invariant 7). It takes the bound instance rather than binding one itself
    because rebinding is a closed set of declared call sites.
    """
    return tuple(member.name for member in (
        bound.state_file, bound.audit_file, bound.execution_file,
        bound.lock_file, bound.evidence_dir, bound.manifest_file,
        bound.completion_file, bound.governance_file, bound.reviews_file,
        bound.discovery_file,
    ))


def _refuse_config_findings(findings: list[dict],
                            checks: tuple[str, ...]) -> None:
    """Turn the first matching error finding into a refusal.

    Takes findings rather than `Paths` on purpose: the repository
    configuration members are reachable from exactly five functions, and a
    shared helper must not become a sixth.
    """
    for finding in findings:
        if finding["severity"] != VALIDATE_ERROR:
            continue
        if finding["check"] in checks:
            raise Refused(
                finding["check"], finding["detail"],
                {"check": finding["check"], "path": finding["path"]},
            )


def _escape_detail(root: Path, value: str) -> str | None:
    """Why `workitems/<value>` is unsafe, or None when it is fine.

    Covers §9's "path traversal/symlink escape" bullet. An unsafe id has every
    other check skipped for it: following a symlink out of the registry to run
    filesystem checks would be the traversal, not the diagnosis of one.
    """
    if not workitem_id_wellformed(value):
        return f"'{value}' is not a well-formed WorkItem id"
    target = root / value
    if target.is_symlink():
        return f"workitems/{value} is a symlink, not a directory"
    try:
        if target.resolve().parent != root.resolve():
            return f"workitems/{value} does not resolve inside workitems/"
    except OSError as exc:
        return f"workitems/{value} cannot be resolved: {exc}"
    return None


def _validate_metadata(root: Path, value: str) -> dict | None:
    """§9 "malformed metadata": absent, unreadable, not an object, or an `id`
    that disagrees with the directory it sits in."""
    target = root / value / "workitem.json"
    if not target.is_file():
        return _finding(
            "malformed_metadata", VALIDATE_ERROR,
            f"workitems/{value}/workitem.json is missing",
            workitem=value, path=target,
        )
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return _finding(
            "malformed_metadata", VALIDATE_ERROR,
            f"workitems/{value}/workitem.json cannot be read: {exc}",
            workitem=value, path=target,
        )
    if not isinstance(data, dict):
        return _finding(
            "malformed_metadata", VALIDATE_ERROR,
            f"workitems/{value}/workitem.json is not a JSON object",
            workitem=value, path=target,
        )
    if data.get("id") != value:
        return _finding(
            "malformed_metadata", VALIDATE_ERROR,
            f"workitems/{value}/workitem.json declares id "
            f"{data.get('id')!r}, which is not '{value}'",
            workitem=value, path=target,
        )
    return None


def _feature_directory_findings(bound: Paths, value: str, doc: dict,
                                target: Path) -> list[dict]:
    """v1.15: a WorkItem must not record a feature directory outside its own
    specs root.

    A null directory is **not** a finding — a workflow that has not reached its
    spec phase simply has none yet, so a freshly initialised repository still
    validates clean.
    """
    directory = speckit_ref(doc)["featureDirectory"]
    prefix = f"{bound.speckit_specs_relative}/"
    if not directory or directory.startswith(prefix):
        return []
    return [_finding(
        "feature_directory_outside_workitem", VALIDATE_ERROR,
        f"workitems/{value} records the feature directory '{directory}', "
        f"which is not inside {prefix}",
        workitem=value, path=target,
    )]


def _validate_runtime_state(paths: Paths, value: str,
                            registered: set[str]) -> list[dict]:
    """§9 "runtime state outside active WorkItem", cases (a) and (b), plus the
    v1.15 feature-directory containment check for a state that passed both."""
    bound = dataclass_replace(paths, workitem=value)
    target = bound.state_file
    if not target.is_file():
        return []
    if value not in registered:
        return [_finding(
            "runtime_state_outside_workitem", VALIDATE_ERROR,
            f"a runtime exists at workitems/{value}/"
            f"{bound.runtime.name}/state.json but '{value}' is not "
            "registered in workitems/index.md",
            workitem=value, path=target,
        )]
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return [_finding(
            "runtime_state_outside_workitem", VALIDATE_ERROR,
            f"workitems/{value} holds a state.json that cannot be read: {exc}",
            workitem=value, path=target,
        )]
    declared = doc.get("workitem") if isinstance(doc, dict) else None
    # Only a *disagreement* is a finding. An absent field is a pre-1.14 state
    # awaiting `migrate`, which `migrate` itself reports; calling that a
    # misplaced runtime would be a false positive.
    if isinstance(declared, str) and declared and declared != value:
        return [_finding(
            "runtime_state_outside_workitem", VALIDATE_ERROR,
            f"the state.json under workitems/{value} declares workitem "
            f"'{declared}' — it belongs to another WorkItem",
            workitem=value, path=target,
        )]
    return _feature_directory_findings(bound, value, doc, target)


def collect_validation_findings(paths: Paths, decision: Resolution) -> list[dict]:
    """Every §9 check, in the order the contract lists them. Read-only."""
    root = workitems_root(paths)
    index_file = workitem_index_file(paths)
    indexed = [row["WorkItem"] for row in read_index(paths)]

    on_disk: list[str] = []
    if root.is_dir():
        on_disk = [
            child.name for child in sorted(root.iterdir())
            if child.is_dir() and not child.name.startswith(".")
        ]

    escapes: dict[str, str] = {}
    for value in dict.fromkeys(indexed + on_disk):
        detail = _escape_detail(root, value)
        if detail is not None:
            escapes[value] = detail
    safe_indexed = [v for v in indexed if v not in escapes]
    safe_on_disk = [v for v in on_disk if v not in escapes]
    registered = set(indexed)

    findings: list[dict] = []

    # 1. duplicate WorkItem IDs.
    seen: dict[str, str] = {}
    for value in indexed:
        key = value.lower()
        if key in seen:
            findings.append(_finding(
                "duplicate_workitem_id", VALIDATE_ERROR,
                f"'{value}' is registered more than once (first seen as "
                f"'{seen[key]}'); ids are unique case-insensitively",
                workitem=value, path=index_file,
            ))
        else:
            seen[key] = value

    # 2. indexed WorkItem missing directory.
    for value in safe_indexed:
        if not (root / value).is_dir():
            findings.append(_finding(
                "indexed_workitem_missing_directory", VALIDATE_ERROR,
                f"'{value}' is registered but workitems/{value}/ does not "
                "exist",
                workitem=value, path=root / value,
            ))

    # 3. directory missing index entry.
    for value in safe_on_disk:
        if value not in registered:
            findings.append(_finding(
                "directory_missing_index_entry", VALIDATE_ERROR,
                f"workitems/{value}/ exists but is not registered in "
                "workitems/index.md",
                workitem=value, path=root / value,
            ))

    # 4. malformed metadata.
    for value in safe_indexed:
        if (root / value).is_dir():
            problem = _validate_metadata(root, value)
            if problem is not None:
                findings.append(problem)

    # 5. branch mismatch — a warning: a developer may legitimately be standing
    #    on another branch, and `validate` is a diagnosis, not a gate.
    here = current_branch(paths)
    if here is not None:
        context = read_active_context(paths) or {}
        recorded = context.get("branch")
        if isinstance(recorded, str) and recorded and recorded != here:
            findings.append(_finding(
                "branch_mismatch", VALIDATE_WARNING,
                f"the persisted active context was set on branch "
                f"'{recorded}' but the checkout is on '{here}'",
                workitem=context.get("workitem"),
                path=active_context_file(paths),
            ))
        for value in safe_indexed:
            bound = dataclass_replace(paths, workitem=value)
            started = recorded_branch(bound)
            if started is not None and started != here:
                findings.append(_finding(
                    "branch_mismatch", VALIDATE_WARNING,
                    f"'{value}' started its execution on branch '{started}' "
                    f"but the checkout is on '{here}'",
                    workitem=value, path=bound.execution_file,
                ))

    # 6. runtime state outside the active WorkItem — (a) unregistered
    #    directory holding a runtime, (b) a self-describing state.json that
    #    disagrees with where it sits, (c) the legacy repository-global
    #    runtime still present alongside registered WorkItems.
    for value in dict.fromkeys(safe_indexed + safe_on_disk):
        findings.extend(_validate_runtime_state(paths, value, registered))
    if indexed and legacy_state_present(paths):
        findings.append(_finding(
            "runtime_state_outside_workitem", VALIDATE_WARNING,
            f"a legacy repository-global runtime still exists at "
            f"{paths.legacy_workflow.name}/state.json while "
            f"{len(indexed)} WorkItem(s) are registered; move it with "
            "`migrate-workflow --workitem <id>`",
            path=paths.legacy_workflow / "state.json",
        ))

    # 7. path traversal / symlink escape.
    for value, detail in escapes.items():
        findings.append(_finding(
            "path_escape", VALIDATE_ERROR, detail,
            workitem=value,
            path=(root / value) if workitem_id_wellformed(value) else index_file,
        ))

    # 8. the repository configuration boundary (contract §11). Silent for
    #    every repository with no `.sdle/`, which is every repository that
    #    predates T05.
    findings.extend(repo_config_findings(paths))

    # 8b. the repository baseline (contract §14). Silent for every repository
    #     that has none, which is every repository that predates T08. Reported
    #     through the same single predicate `baseline show` uses, so the two
    #     can never disagree.
    findings.extend(baseline_findings(paths))

    # 9. the leak detector, both directions. §11 splits ownership between the
    #    repository boundary and the WorkItem boundary; this is what makes the
    #    split enforced rather than merely documented, and it is the check
    #    that would catch a lifecycle rule migrating into `.sdle/` early.
    #    Both name sets are *derived* from `Paths`, never re-listed, so a later
    #    phase that adds a member on either side inherits the check.
    probe = dataclass_replace(paths, workitem="_probe")
    runtime_names = workitem_runtime_member_names(probe)
    config_names = (
        paths.config_file.name,
        paths.policies_dir.name,
        paths.shared_templates_dir.name,
        paths.baseline_file.name,
        paths.implementation_state_dir.name,
    )

    if paths.config_root.is_dir():
        for name in sorted(runtime_names):
            leaked = paths.config_root / name
            if leaked.exists():
                findings.append(_finding(
                    "lifecycle_state_in_repository_config", VALIDATE_ERROR,
                    f"{paths.config_root_relative}/{name} is WorkItem "
                    "lifecycle state; the repository configuration boundary "
                    "does not own it (contract §11)",
                    path=leaked,
                ))

    for value in dict.fromkeys(safe_indexed + safe_on_disk):
        bound = dataclass_replace(paths, workitem=value)
        if not bound.runtime.is_dir():
            continue
        for name in sorted(config_names):
            leaked = bound.runtime / name
            if leaked.exists():
                findings.append(_finding(
                    "repository_config_in_workitem", VALIDATE_ERROR,
                    f"workitems/{value}/{bound.runtime.name}/{name} is "
                    "repository-level configuration; a WorkItem does not own "
                    "it (contract §11)",
                    workitem=value, path=leaked,
                ))

    # The speculative resolution outcome. A repository that cannot resolve is
    # a *warning*, not an error: ">1 plausible -> ASK" is contract §9 working
    # as designed, and an empty repository is simply not started yet.
    if decision.workitem is None and decision.rung is None:
        findings.append(_finding(
            "active_workitem_unresolved", VALIDATE_WARNING,
            f"no WorkItem resolves here (reason: {decision.reason}); name one "
            "with `--workitem <id>` or persist one with `workitem use`",
            path=paths.project_root,
        ))

    return findings


def cmd_validate(args, paths: Paths) -> int:
    decision = resolve_decision(paths, args.workitem)
    findings = collect_validation_findings(paths, decision)
    errors = [f for f in findings if f["severity"] == VALIDATE_ERROR]

    data = {
        "findings": findings,
        "errors": len(errors),
        "warnings": len(findings) - len(errors),
        "project_root": str(paths.project_root),
        "workitems": decision.known,
        "active": decision.workitem,
        "rung": decision.rung,
        "reason": decision.reason,
        "branch": current_branch(paths),
    }

    if errors:
        raise IntegrityError(
            "workitem_validation_failed",
            f"{len(errors)} WorkItem registry error(s) found: "
            + "; ".join(sorted({f["check"] for f in errors}))
            + ". SDLE will not repair the registry — fix it by hand.",
            data,
        )

    emit("validate", data)
    return EXIT_OK


# --------------------------------------------------------------------------
# config — the repository configuration boundary's two commands
# --------------------------------------------------------------------------
#
# Both are runtime-free: contract §11's exit criterion is that repository-global
# configuration exists *independently* from WorkItem runtime state, so neither
# may be gated on the resolution ladder. They write nothing outside
# `config_root`, append no audit entry, and touch no state.


def cmd_config_init(args, paths: Paths) -> int:
    """Create the repository configuration boundary. Never overwrites."""
    _refuse_config_findings(repo_config_findings(paths),
                            ("config_root_inside_workitem",))

    target = paths.config_file
    if target.exists():
        raise Refused(
            "config_exists",
            f"{paths.config_root_relative}/{target.name} already exists; "
            "`config init` never overwrites an existing configuration. Edit "
            "it by hand, or delete it first.",
            {"config_file": str(target),
             "config_root": paths.config_root_relative},
        )

    created: list[str] = []

    def note(path: Path) -> None:
        created.append(path.relative_to(paths.project_root).as_posix())

    # `.gitkeep` exists because Git cannot version an empty directory, and §19
    # places `.sdle/policies/*` under "must eventually be versioned". An
    # existing directory keeps whatever it already holds.
    for directory in (paths.policies_dir, paths.shared_templates_dir,
                      paths.implementation_state_dir):
        directory.mkdir(parents=True, exist_ok=True)
        keep = directory / ".gitkeep"
        if not keep.exists():
            write_atomic(keep, "")
            note(keep)

    # Written last, and atomically: a failed run leaves no `config.json`, so a
    # re-run completes rather than refusing `config_exists`.
    write_atomic(target, json.dumps(REPO_CONFIG_DEFAULTS, indent=2) + "\n")
    note(target)

    emit("config init", {
        "root": paths.config_root_relative,
        "config": dict(REPO_CONFIG_DEFAULTS),
        "created": created,
    })
    return EXIT_OK


def cmd_config_show(args, paths: Paths) -> int:
    """Report the effective repository configuration. Creates nothing."""
    _refuse_config_findings(
        repo_config_findings(paths),
        ("config_root_inside_workitem", "config_malformed"),
    )

    present = paths.config_file.is_file()
    # A present document that survived the refusal above declares both keys:
    # an absent key reads as None, which is outside both supported-value
    # tuples and would already have refused `config_malformed`.
    defaults_applied = [] if present else sorted(REPO_CONFIG_DEFAULTS)

    def relative(path: Path) -> str:
        return path.relative_to(paths.project_root).as_posix()

    emit("config show", {
        "root": paths.config_root_relative,
        "present": present,
        "config": read_repo_config(paths),
        "defaults_applied": defaults_applied,
        "members": {
            "config": relative(paths.config_file),
            "policies": relative(paths.policies_dir),
            "templates": relative(paths.shared_templates_dir),
            # Named, not created: §14 owns the baseline schema, not T05.
            "baseline": relative(paths.baseline_file),
            "implementation_state": relative(paths.implementation_state_dir),
        },
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# Governance policy — contract §12
#
# `GOVERNANCE_POLICY_BUILTIN` is the single source of truth for the twelve
# requirements-quality check ids, which of them block, which may be reported
# NOT_APPLICABLE, the closed risk-signal vocabulary and its weights, the
# score->level thresholds, the hard floors, and the would-be required gate
# map. No default value below may be restated anywhere outside this file.
#
# A repository may override it with `.sdle/policies/governance-policy.json`.
# The override is MONOTONE: it may only make governance stricter. That is what
# makes "absent policy file -> built-in" safe rather than fail-open — the
# built-in is by construction the weakest admissible policy, so a missing
# override can never produce a weaker outcome than a present one.
#
# Merge rule, stated once: a dict-valued key is merged key by key (so adding a
# signal does not require restating the others); a list-valued key is replaced
# wholesale (so a removal is expressible, and therefore refusable). Every
# merged value must then dominate the built-in, or the read refuses.
# --------------------------------------------------------------------------

GOVERNANCE_LEVELS = ("LOW", "MEDIUM", "HIGH", "CRITICAL")

# §12's WorkItem type and engineering-flow vocabularies. Fixed by the
# contract, not policy-overridable: a repository may tighten *consequences*,
# never rename the facts.
WORKITEM_TYPES = ("enhancement", "defect", "hotfix", "chore")
ENGINEERING_FLOWS = (
    "GREENFIELD", "BROWNFIELD_DISCOVERY", "ITERATIVE", "DEFECT_FIX", "HOTFIX",
)

# The classification section's permitted keys. `type` and `flow` are §12's and
# are required; `rediscovery` is §14's monotone opt-in and is optional,
# defaulting to false. Monotone in exactly the sense ADR-003 uses: it can only
# ask for MORE work — a full rediscovery of a repository that already has a
# sound baseline — never less, so a model that proposes it cannot weaken
# anything.
CLASSIFICATION_KEYS = ("type", "flow", "rediscovery")
CLASSIFICATION_REQUIRED_KEYS = ("type", "flow")

GOVERNANCE_POLICY_BUILTIN = {
    "policyVersion": "1",
    # §12's twelve structured checks, verbatim and in its order.
    "quality_checks": [
        "problem_statement",
        "scope",
        "out_of_scope",
        "acceptance_criteria",
        "ambiguity",
        "contradictions",
        "constraints",
        "nfrs",
        "security_data_implications",
        "compatibility",
        "dependencies",
        "blocking_unknowns",
    ],
    # A FAIL on any of these stops progression. Severity is read from HERE,
    # never from the model's input.
    "blocking_checks": [
        "problem_statement",
        "scope",
        "out_of_scope",
        "acceptance_criteria",
        "ambiguity",
        "contradictions",
        "constraints",
        "nfrs",
        "security_data_implications",
        "compatibility",
        "dependencies",
        "blocking_unknowns",
    ],
    # §12 says "NFRs when relevant", so `nfrs` — and only `nfrs` — may be
    # reported NOT_APPLICABLE. Every other check must be answered.
    "optional_checks": ["nfrs"],
    "risk_signals": {
        "external_api_surface": 2,
        "persistent_data_store": 2,
        "schema_or_data_migration": 3,
        "authentication_or_authorization": 3,
        "personal_or_sensitive_data": 4,
        "payment_or_financial": 4,
        "cryptography_or_secrets": 4,
        "public_network_exposure": 3,
        "third_party_dependency": 1,
        "concurrency_or_distributed_state": 2,
        "infrastructure_or_deployment": 2,
        "backward_incompatible_change": 3,
        # T09/§15: four of §15's nine hard floors name a condition no existing
        # signal's definition entails, plus blast radius which is orthogonal
        # to all of them. Each is appended rather than folded into a
        # neighbour, because widening an existing signal to cover a narrower
        # §15 condition would over-enforce every ordinary use of it.
        "destructive_or_irreversible_migration": 4,
        "regulatory_or_compliance": 4,
        "production_security_boundary": 4,
        "credential_or_key_exposure": 5,
        "catastrophic_blast_radius": 5,
    },
    "risk_thresholds": {"LOW": 0, "MEDIUM": 2, "HIGH": 5, "CRITICAL": 9},
    # §15's minimum floor list, complete. The first six rules keep the order
    # and the positions they shipped with — a test indexes rule 0 — and the
    # only in-place edit is `authentication_or_authorization`, which shipped
    # at MEDIUM where §15 states HIGH. Everything §15 adds is APPENDED, so no
    # existing index moves and every edit is a tightening.
    "hard_floors": [
        {"signal": "payment_or_financial", "level": "HIGH"},
        {"signal": "cryptography_or_secrets", "level": "HIGH"},
        {"signal": "personal_or_sensitive_data", "level": "HIGH"},
        {"signal": "authentication_or_authorization", "level": "HIGH"},
        {"uncertainty": "HIGH", "level": "HIGH"},
        {"uncertainty": "CRITICAL", "level": "CRITICAL"},
        {"signal": "destructive_or_irreversible_migration", "level": "HIGH"},
        {"signal": "backward_incompatible_change", "level": "HIGH"},
        {"signal": "regulatory_or_compliance", "level": "HIGH"},
        {"signal": "production_security_boundary", "level": "HIGH"},
        {"signal": "credential_or_key_exposure", "level": "CRITICAL"},
        {"signal": "catastrophic_blast_radius", "level": "CRITICAL"},
    ],
    # Which gates require a HUMAN APPROVAL. Consumed by `gate_requirements`.
    # §15's per-level lists are minima, so a repository override may add and
    # never remove (`_refuse_weakening`). Membership of a flow is a separate,
    # structural fact owned by FLOW_PHASES: a gate the bound flow does not
    # contain is reported `not_in_flow`, never quietly satisfied.
    "required_gates_always": [
        "gate_constitution", "gate_spec", "gate_plan", "gate_implement",
    ],
    "required_gates_by_risk": {
        "LOW": [],
        # §15's MEDIUM adds design review. Analysis stays HIGH-and-above
        # because §15 hedges it at MEDIUM with "as applicable", and a
        # conditional a deterministic engine cannot evaluate is not a floor.
        "MEDIUM": ["gate_tasks", "gate_design"],
        "HIGH": ["gate_tasks", "gate_analyze", "gate_design", "gate_security"],
        "CRITICAL": [
            "gate_tasks", "gate_analyze", "gate_design", "gate_security",
        ],
    },
    "required_gates_by_type": {
        "enhancement": [],
        "defect": ["gate_tasks"],
        "hotfix": [],
        "chore": [],
    },
}

# Top-level keys an override may carry. `quality_checks` is deliberately
# absent: the twelve ids are §12's, and a repository that could rename or drop
# one would be editing the contract rather than tightening it.
GOVERNANCE_POLICY_OVERRIDABLE = (
    "policyVersion",
    "blocking_checks",
    "optional_checks",
    "risk_signals",
    "risk_thresholds",
    "hard_floors",
    "required_gates_always",
    "required_gates_by_risk",
    "required_gates_by_type",
)

SUPPORTED_POLICY_VERSIONS = ("1",)


def _policy_malformed(relative: str, detail: str, **data) -> Refused:
    """Every malformed-policy exit goes through one constructor.

    Fail-closed by construction: this returns a refusal, so no caller can
    accidentally turn a parse problem into a default. A security-relevant
    floor that silently defaulted would be the wrong failure direction.
    """
    return Refused(
        "policy_malformed",
        f"{relative} cannot be used as a governance policy: {detail}. SDLE "
        "refuses rather than falling back to the built-in policy — a "
        "governance floor must never be lowered by a typo.",
        {"path": relative, "detail": detail, **data},
    )


def _policy_weakens(relative: str, key: str, detail: str, **data) -> Refused:
    return Refused(
        "policy_weakens_baseline",
        f"{relative} weakens the built-in governance policy at '{key}': "
        f"{detail}. A repository policy may only make governance stricter.",
        {"path": relative, "key": key, "detail": detail, **data},
    )


def _is_int(value: object) -> bool:
    """`True` is an `int` in Python and must not pass as a weight."""
    return isinstance(value, int) and not isinstance(value, bool)


def _str_list(value: object) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) for item in value)


def _floor_key(rule: dict) -> tuple[str, str] | None:
    for kind in ("signal", "uncertainty"):
        if kind in rule:
            return kind, rule[kind]
    return None


def _validate_policy_shapes(document: dict, relative: str,
                            known_gates: set[str]) -> None:
    """Type and vocabulary validation for an override document."""
    checks = set(GOVERNANCE_POLICY_BUILTIN["quality_checks"])

    unknown = sorted(set(document) - set(GOVERNANCE_POLICY_OVERRIDABLE))
    if unknown:
        raise _policy_malformed(
            relative,
            f"unknown top-level key(s) {', '.join(unknown)}; an override may "
            "carry only " + ", ".join(GOVERNANCE_POLICY_OVERRIDABLE),
            unknown_keys=unknown,
        )

    if "policyVersion" in document:
        if document["policyVersion"] not in SUPPORTED_POLICY_VERSIONS:
            raise _policy_malformed(
                relative,
                f"policyVersion {document['policyVersion']!r} is not "
                "supported; this engine supports "
                + ", ".join(repr(v) for v in SUPPORTED_POLICY_VERSIONS),
            )

    for key in ("blocking_checks", "optional_checks"):
        if key not in document:
            continue
        if not _str_list(document[key]):
            raise _policy_malformed(relative, f"{key} must be a list of strings")
        strange = sorted(set(document[key]) - checks)
        if strange:
            raise _policy_malformed(
                relative,
                f"{key} names check id(s) {', '.join(strange)} that are not "
                "among the twelve requirements-quality checks",
                unknown_checks=strange,
            )

    if "risk_signals" in document:
        value = document["risk_signals"]
        if not isinstance(value, dict):
            raise _policy_malformed(relative, "risk_signals must be an object")
        for signal, weight in value.items():
            if not _is_int(weight) or weight < 0:
                raise _policy_malformed(
                    relative,
                    f"risk_signals['{signal}'] must be a non-negative integer "
                    f"weight, not {weight!r}",
                )

    if "risk_thresholds" in document:
        value = document["risk_thresholds"]
        if not isinstance(value, dict):
            raise _policy_malformed(relative, "risk_thresholds must be an object")
        strange = sorted(set(value) - set(GOVERNANCE_LEVELS))
        if strange:
            raise _policy_malformed(
                relative,
                f"risk_thresholds names level(s) {', '.join(strange)}; the "
                "levels are " + ", ".join(GOVERNANCE_LEVELS),
            )
        for level, score in value.items():
            if not _is_int(score) or score < 0:
                raise _policy_malformed(
                    relative,
                    f"risk_thresholds['{level}'] must be a non-negative "
                    f"integer, not {score!r}",
                )

    if "hard_floors" in document:
        value = document["hard_floors"]
        if not isinstance(value, list) or not all(
                isinstance(rule, dict) for rule in value):
            raise _policy_malformed(relative, "hard_floors must be a list of objects")
        for rule in value:
            if set(rule) not in ({"signal", "level"}, {"uncertainty", "level"}):
                raise _policy_malformed(
                    relative,
                    "each hard_floors rule must be exactly {'signal', 'level'} "
                    f"or {{'uncertainty', 'level'}}, not {sorted(rule)}",
                )
            if rule["level"] not in GOVERNANCE_LEVELS:
                raise _policy_malformed(
                    relative,
                    f"hard_floors level {rule['level']!r} is not one of "
                    + ", ".join(GOVERNANCE_LEVELS),
                )
            if "uncertainty" in rule and rule["uncertainty"] not in GOVERNANCE_LEVELS:
                raise _policy_malformed(
                    relative,
                    f"hard_floors uncertainty {rule['uncertainty']!r} is not "
                    "one of " + ", ".join(GOVERNANCE_LEVELS),
                )

    if "required_gates_always" in document:
        if not _str_list(document["required_gates_always"]):
            raise _policy_malformed(
                relative, "required_gates_always must be a list of strings")

    for key, vocabulary in (("required_gates_by_risk", GOVERNANCE_LEVELS),
                            ("required_gates_by_type", WORKITEM_TYPES)):
        if key not in document:
            continue
        value = document[key]
        if not isinstance(value, dict):
            raise _policy_malformed(relative, f"{key} must be an object")
        strange = sorted(set(value) - set(vocabulary))
        if strange:
            raise _policy_malformed(
                relative,
                f"{key} names {', '.join(strange)}; the permitted keys are "
                + ", ".join(vocabulary),
            )
        for name, gates in value.items():
            if not _str_list(gates):
                raise _policy_malformed(
                    relative, f"{key}['{name}'] must be a list of gate keys")

    # Gate ids are validated against the *registered* gates, so an override
    # cannot name a gate that does not exist. A would-be gate set full of
    # phantom keys would be worthless for the comparison §12 asks for.
    named: set[str] = set(document.get("required_gates_always") or [])
    for key in ("required_gates_by_risk", "required_gates_by_type"):
        for gates in (document.get(key) or {}).values():
            named |= set(gates)
    phantom = sorted(named - known_gates)
    if phantom:
        raise _policy_malformed(
            relative,
            f"required gate key(s) {', '.join(phantom)} are not registered "
            "gates",
            unknown_gates=phantom, known_gates=sorted(known_gates),
        )


def _merge_policy(document: dict) -> dict:
    """Built-in, overlaid by the override. Dicts merge; lists replace."""
    merged = copy.deepcopy(GOVERNANCE_POLICY_BUILTIN)
    for key, value in document.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def _refuse_weakening(merged: dict, relative: str) -> None:
    """D2's six weakening shapes. Each one is a refusal, never a warning."""
    builtin = GOVERNANCE_POLICY_BUILTIN

    dropped = sorted(set(builtin["blocking_checks"]) - set(merged["blocking_checks"]))
    if dropped:
        raise _policy_weakens(
            relative, "blocking_checks",
            f"it no longer blocks on {', '.join(dropped)}", removed=dropped)

    widened = sorted(set(merged["optional_checks"]) - set(builtin["optional_checks"]))
    if widened:
        raise _policy_weakens(
            relative, "optional_checks",
            f"it lets {', '.join(widened)} be reported NOT_APPLICABLE",
            added=widened)

    for signal, weight in builtin["risk_signals"].items():
        current = merged["risk_signals"].get(signal)
        if current is None:
            raise _policy_weakens(
                relative, "risk_signals",
                f"the signal '{signal}' has been removed", signal=signal)
        if current < weight:
            raise _policy_weakens(
                relative, "risk_signals",
                f"'{signal}' weighs {current}, below the built-in {weight}",
                signal=signal, weight=current, builtin_weight=weight)

    for level, score in builtin["risk_thresholds"].items():
        current = merged["risk_thresholds"].get(level)
        if current is None:
            raise _policy_weakens(
                relative, "risk_thresholds",
                f"the threshold for {level} has been removed", level=level)
        if current > score:
            raise _policy_weakens(
                relative, "risk_thresholds",
                f"{level} now needs a score of {current}, above the built-in "
                f"{score}, so it is harder to reach",
                level=level, threshold=current, builtin_threshold=score)

    present = {}
    for rule in merged["hard_floors"]:
        key = _floor_key(rule)
        if key is not None:
            index = GOVERNANCE_LEVELS.index(rule["level"])
            present[key] = max(present.get(key, -1), index)
    for rule in builtin["hard_floors"]:
        key = _floor_key(rule)
        expected = GOVERNANCE_LEVELS.index(rule["level"])
        current = present.get(key)
        if current is None:
            raise _policy_weakens(
                relative, "hard_floors",
                f"the floor {key[0]}='{key[1]}' -> {rule['level']} has been "
                "removed", floor=rule)
        if current < expected:
            raise _policy_weakens(
                relative, "hard_floors",
                f"the floor {key[0]}='{key[1]}' has been lowered from "
                f"{rule['level']} to {GOVERNANCE_LEVELS[current]}", floor=rule)

    missing = sorted(set(builtin["required_gates_always"])
                     - set(merged["required_gates_always"]))
    if missing:
        raise _policy_weakens(
            relative, "required_gates_always",
            f"it no longer requires {', '.join(missing)}", removed=missing)

    for key in ("required_gates_by_risk", "required_gates_by_type"):
        for name, gates in builtin[key].items():
            missing = sorted(set(gates) - set(merged[key].get(name) or []))
            if missing:
                raise _policy_weakens(
                    relative, key,
                    f"'{name}' no longer requires {', '.join(missing)}",
                    entry=name, removed=missing)


def read_governance_policy(paths: Paths, consts: Constants) -> dict:
    """The effective governance policy. Reads; never writes. FAIL-CLOSED.

    This is the ONLY function in the engine that may reach
    ``Paths.governance_policy_file``. It deliberately does **not** copy
    `read_repo_config`'s `except: return defaults` shape: that reader is safe
    only because its sole caller refuses first, and a governance floor that
    silently defaulted on a malformed file would be exactly the wrong failure
    direction. Every unusable document raises; nothing here returns from an
    exception handler.

    The built-in is returned only when the file is genuinely **absent**, which
    is safe because the override is monotone — the built-in is the weakest
    admissible policy.
    """
    target = paths.governance_policy_file
    relative = target.relative_to(paths.project_root).as_posix()
    known_gates = set(consts.phase_to_gate_key.values())

    # Presence and readability are two different questions, and conflating
    # them is a fail-open bug: a directory (or a broken symlink) where the
    # policy should be is not an absent policy, it is an unusable one.
    if not target.exists() and not target.is_symlink():
        return {
            "policy": copy.deepcopy(GOVERNANCE_POLICY_BUILTIN),
            "source": "builtin",
            "path": relative,
            "sha256": None,
        }
    if not target.is_file():
        raise _policy_malformed(
            relative, "something exists at that path but it is not a readable "
            "regular file")

    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise _policy_malformed(relative, f"it cannot be read ({exc})") from None
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise _policy_malformed(relative, f"it is not valid JSON ({exc})") from None
    if not isinstance(document, dict):
        raise _policy_malformed(relative, "it is not a JSON object")

    _validate_policy_shapes(document, relative, known_gates)
    merged = _merge_policy(document)
    _refuse_weakening(merged, relative)
    return {
        "policy": merged,
        "source": relative,
        "path": relative,
        "sha256": sha256_file(target),
    }


def cmd_governance_policy(args, paths: Paths) -> int:
    """Report the effective governance policy. Creates nothing, writes
    nothing, and needs no WorkItem — the policy is repository-scoped."""
    consts = load_constants(paths)
    effective = read_governance_policy(paths, consts)
    emit("governance policy", {
        "source": effective["source"],
        "path": effective["path"],
        "sha256": effective["sha256"],
        "policy": effective["policy"],
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# Governance assessment — contract §12
#
# Claude reports observations; the POLICY decides consequences. Severity is
# read from the policy and never from the input, an unknown risk signal is
# refused rather than ignored (a silently dropped signal is a silently lowered
# risk), and the final risk level is `max(deterministic, proposed)` over a
# totally ordered lattice — so there is no code path here that can produce a
# level below the deterministic one.
#
# The record is a WorkItem runtime FILE, not a `state.json` field, because §12
# places governance *before* planning: it must be writable before
# `state.json` exists, so it cannot be owned by it. Same argument that put
# branch/SHA in `execution.json` at T03.
# --------------------------------------------------------------------------

GOVERNANCE_RECORD_VERSION = "2"
# Every version this engine can READ. `"1"` records stay valid: their one
# stale key is never consulted for a decision, because every decision
# re-derives the requirement set from the policy on disk. An unrecognised
# version is an integrity failure rather than a silent "assume the current
# shape" — a version field nothing refuses on proves nothing.
GOVERNANCE_RECORD_VERSIONS = ("1", "2")
GOVERNANCE_INPUT_VERSIONS = ("1",)
QUALITY_RESULTS = ("PASS", "FAIL", "NOT_APPLICABLE")
GOVERNANCE_INPUT_SECTIONS = ("governanceInputVersion", "quality",
                             "classification", "risk")


def _input_malformed(relative: str, detail: str, **data) -> Refused:
    return Refused(
        "governance_input_malformed",
        f"{relative} is not a usable governance input: {detail}.",
        {"path": relative, "detail": detail, **data},
    )


def requirements_sources(paths: Paths) -> tuple[list[dict], str]:
    """Every file under ``requirements/`` with its SHA, plus one digest.

    The digest covers the *source set*, not one file, so adding or removing a
    requirements document invalidates a recorded assessment exactly as editing
    one does. Sorted by repo-relative POSIX path so the value is stable across
    platforms and filesystem ordering.
    """
    root = paths.project_root / "requirements"
    sources: list[dict] = []
    if root.is_dir():
        for path in root.rglob("*"):
            if path.is_file():
                sources.append({
                    "path": path.relative_to(paths.project_root).as_posix(),
                    "sha256": sha256_file(path),
                })
    sources.sort(key=lambda entry: entry["path"])
    payload = "\n".join(f"{e['path']} {e['sha256']}" for e in sources)
    return sources, hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_governance_input(target: Path, relative: str) -> dict:
    """Parse and envelope-validate Claude's structured proposal. Fail-closed:
    nothing here returns a default."""
    if not target.is_file():
        raise _input_malformed(relative, "no such file")
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise _input_malformed(relative, f"it cannot be read ({exc})") from None
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise _input_malformed(relative, f"it is not valid JSON ({exc})") from None
    if not isinstance(document, dict):
        raise _input_malformed(relative, "it is not a JSON object")

    unknown = sorted(set(document) - set(GOVERNANCE_INPUT_SECTIONS))
    if unknown:
        raise _input_malformed(
            relative, f"unknown top-level key(s) {', '.join(unknown)}",
            unknown_keys=unknown)
    missing = [key for key in GOVERNANCE_INPUT_SECTIONS if key not in document]
    if missing:
        raise _input_malformed(
            relative, f"missing required key(s) {', '.join(missing)}",
            missing_keys=missing)
    if document["governanceInputVersion"] not in GOVERNANCE_INPUT_VERSIONS:
        raise _input_malformed(
            relative,
            f"governanceInputVersion {document['governanceInputVersion']!r} is "
            "not supported; this engine supports "
            + ", ".join(repr(v) for v in GOVERNANCE_INPUT_VERSIONS))
    for key in ("quality", "classification", "risk"):
        if not isinstance(document[key], dict):
            raise _input_malformed(relative, f"'{key}' must be an object")
    return document


def evaluate_quality(document: dict, policy: dict, relative: str) -> dict:
    """The twelve §12 checks, evaluated deterministically.

    Severity is read from ``policy``. An input that tried to mark its own
    failure advisory could not do so — there is nowhere in this function that
    consults the input for whether a check blocks.
    """
    quality = document["quality"]
    ids = list(policy["quality_checks"])
    blocking_ids = set(policy["blocking_checks"])
    optional_ids = set(policy["optional_checks"])

    unknown = sorted(set(quality) - set(ids))
    if unknown:
        raise Refused(
            "quality_unknown_check",
            f"{relative} reports check id(s) {', '.join(unknown)} that are not "
            "among the twelve requirements-quality checks. SDLE refuses an "
            "input it does not fully understand rather than ignoring part of "
            "it.",
            {"path": relative, "unknown": unknown, "known": ids},
        )
    missing = [name for name in ids if name not in quality]
    if missing:
        raise Refused(
            "quality_incomplete",
            f"{relative} does not answer {', '.join(missing)}. All twelve "
            "checks must be answered; an unanswered check is not a pass.",
            {"path": relative, "missing": missing},
        )

    checks: list[dict] = []
    for name in ids:
        entry = quality[name]
        if not isinstance(entry, dict) or set(entry) - {"result", "finding"}:
            raise Refused(
                "quality_unknown_check",
                f"{relative}: check '{name}' must be an object with only "
                "'result' and 'finding'. Severity is decided by the "
                "governance policy, never by the input.",
                {"path": relative, "check": name},
            )
        result = entry.get("result")
        if result not in QUALITY_RESULTS:
            raise Refused(
                "quality_malformed",
                f"{relative}: check '{name}' has result {result!r}; the "
                "permitted results are " + ", ".join(QUALITY_RESULTS) + ".",
                {"path": relative, "check": name, "result": result},
            )
        finding = entry.get("finding")
        if finding is not None and not isinstance(finding, str):
            raise Refused(
                "quality_malformed",
                f"{relative}: check '{name}' has a non-string finding.",
                {"path": relative, "check": name},
            )
        if result == "NOT_APPLICABLE" and name not in optional_ids:
            raise Refused(
                "quality_not_applicable_refused",
                f"{relative}: check '{name}' cannot be reported "
                "NOT_APPLICABLE. The governance policy marks only "
                + ", ".join(sorted(optional_ids) or ["(none)"])
                + " optional.",
                {"path": relative, "check": name,
                 "optional": sorted(optional_ids)},
            )
        if result == "FAIL" and not (finding or "").strip():
            raise Refused(
                "quality_malformed",
                f"{relative}: check '{name}' FAILed without a finding. A "
                "blocking finding that says nothing is not remediable.",
                {"path": relative, "check": name},
            )
        checks.append({
            "id": name,
            "result": result,
            "finding": finding,
            "blocking": name in blocking_ids,
            "optional": name in optional_ids,
        })

    failed_blocking = [c["id"] for c in checks
                       if c["result"] == "FAIL" and c["blocking"]]
    failed_advisory = [c["id"] for c in checks
                       if c["result"] == "FAIL" and not c["blocking"]]
    return {
        "checks": checks,
        "blocking": failed_blocking,
        "advisory": failed_advisory,
        "result": "BLOCKED" if failed_blocking else "PASS",
    }


def evaluate_classification(document: dict, relative: str) -> dict:
    """§12's WorkItem type and engineering flow, validated and recorded.

    No longer advisory as of T07: `classification.flow` is what `init` binds
    `state["flow"]` from, so it selects the phases the WorkItem traverses.
    `classification.type` is still consumed by nothing — T09 owns making risk
    and type drive gate *requirements*. One flag covers both keys, and the
    binding one is what it now has to report.

    T08 adds the third, optional key: `rediscovery`. §14 makes a sound
    repository baseline refuse a second full brownfield discovery, and this is
    the deliberate opt-in that asks for one anyway. It is monotone-safe — it
    can only ask for more work — and it is a contradiction with any flow other
    than the one that performs discovery, so that combination is refused
    rather than ignored.
    """
    section = document["classification"]
    unknown = sorted(set(section) - set(CLASSIFICATION_KEYS))
    if unknown:
        raise _input_malformed(
            relative,
            f"classification has unknown key(s) {', '.join(unknown)}")
    for key, vocabulary in (("type", WORKITEM_TYPES), ("flow", ENGINEERING_FLOWS)):
        value = section.get(key)
        if value not in vocabulary:
            raise Refused(
                "classification_invalid",
                f"{relative}: classification.{key} is {value!r}; the "
                f"permitted values are " + ", ".join(vocabulary) + ".",
                {"path": relative, "field": key, "value": value,
                 "permitted": list(vocabulary)},
            )

    rediscovery = section.get("rediscovery", False)
    if not isinstance(rediscovery, bool):
        raise Refused(
            "classification_invalid",
            f"{relative}: classification.rediscovery is {rediscovery!r}; it "
            "must be true or false.",
            {"path": relative, "field": "rediscovery", "value": rediscovery,
             "permitted": [True, False]},
        )
    if rediscovery and section["flow"] != BASELINE_REDISCOVERY_FLOW:
        raise Refused(
            "classification_invalid",
            f"{relative}: classification.rediscovery asks for a full "
            f"repository rediscovery while binding {section['flow']}, which "
            "does not perform one. Rediscovery is only meaningful for "
            f"{BASELINE_REDISCOVERY_FLOW}.",
            {"path": relative, "field": "rediscovery", "value": rediscovery,
             "flow": section["flow"],
             "permitted_flow": BASELINE_REDISCOVERY_FLOW},
        )

    return {"type": section["type"], "flow": section["flow"],
            "advisory": False, "rediscovery": rediscovery}


def deterministic_level(score: int, thresholds: dict) -> str:
    """The highest level whose score threshold is met.

    Written as "highest index that qualifies" rather than "first that fails"
    so a policy that lowers one threshold out of order still resolves
    upward — stricter, never looser.
    """
    level = GOVERNANCE_LEVELS[0]
    for candidate in GOVERNANCE_LEVELS:
        threshold = thresholds.get(candidate)
        if threshold is not None and score >= threshold:
            level = candidate
    return level


def evaluate_risk(document: dict, policy: dict, relative: str) -> dict:
    """Hybrid risk. Claude proposes; the policy decides; the core takes the
    maximum.

    The security property is stated as code, not as prose: ``final`` is the
    lattice maximum of the deterministic level and the proposed one, so a
    lower proposal is recorded as an attempt and has no effect. There is no
    branch below that can return a level under ``deterministicLevel``.
    """
    section = document["risk"]
    unknown = sorted(set(section) - {"signals", "proposedLevel", "uncertainty"})
    if unknown:
        raise _input_malformed(
            relative, f"risk has unknown key(s) {', '.join(unknown)}")

    signals = section.get("signals")
    if not isinstance(signals, list) or not all(
            isinstance(s, str) for s in signals):
        raise _input_malformed(relative, "risk.signals must be a list of strings")
    for key in ("proposedLevel", "uncertainty"):
        if section.get(key) not in GOVERNANCE_LEVELS:
            raise _input_malformed(
                relative,
                f"risk.{key} is {section.get(key)!r}; the levels are "
                + ", ".join(GOVERNANCE_LEVELS))

    weights = policy["risk_signals"]
    strange = sorted(set(signals) - set(weights))
    if strange:
        raise Refused(
            "unknown_risk_signal",
            f"{relative} names risk signal(s) {', '.join(strange)} that the "
            "governance policy does not define. SDLE refuses rather than "
            "ignoring a signal it cannot weigh — a silently dropped signal is "
            "a silently lowered risk.",
            {"path": relative, "unknown": strange,
             "known": sorted(weights)},
        )

    ordered = sorted(set(signals))
    score = sum(weights[name] for name in ordered)
    level = deterministic_level(score, policy["risk_thresholds"])

    floors: list[dict] = []
    for rule in policy["hard_floors"]:
        fired = (("signal" in rule and rule["signal"] in ordered)
                 or ("uncertainty" in rule
                     and rule["uncertainty"] == section["uncertainty"]))
        if not fired:
            continue
        floors.append({"rule": dict(rule), "raisedTo": rule["level"]})
        if GOVERNANCE_LEVELS.index(rule["level"]) > GOVERNANCE_LEVELS.index(level):
            level = rule["level"]

    proposed = section["proposedLevel"]
    final = max((level, proposed), key=GOVERNANCE_LEVELS.index)
    return {
        "signals": ordered,
        "score": score,
        "floorsApplied": floors,
        "deterministicLevel": level,
        "proposedLevel": proposed,
        "uncertainty": section["uncertainty"],
        "finalLevel": final,
        "loweringAttempted": (GOVERNANCE_LEVELS.index(proposed)
                              < GOVERNANCE_LEVELS.index(level)),
    }


def governance_downgrade(previous: dict | None, risk: dict) -> dict | None:
    """A re-assessment landing on a **lower** final level than one already
    recorded for this WorkItem, described — or ``None``.

    **T11 D11** closes the asymmetry T09's verifier named (NB-2). *Within* one
    assessment a lower proposal is already inert and already recorded:
    ``final`` is the lattice maximum and ``loweringAttempted`` says an attempt
    was made. *Across* two assessments there was no such record. Re-running
    `governance assess` with a smaller signal set simply replaced the record,
    so a gate that had been required could become omittable with nothing
    anywhere stating that a level had fallen — which is the practical route to
    omitting a gate that T09 flagged.

    It **audits**; it does not refuse, and that is deliberate. A genuine
    re-scope (authentication dropped out of the WorkItem) legitimately lowers
    risk. Refusing it would invent a floor no contract section states, would
    leave a correct user no honest way forward, and would push them toward
    editing the record by hand — which the write fence denies and the audit
    chain would catch, i.e. a dead end. What §15 actually requires is that
    every omitted gate be *explainable and auditable*, so evidence is the
    right instrument: `governance_downgraded` in the ledger, `downgrade` on
    the record, and the same block carried into every omission that rests on
    it.

    Pure: it reads two dictionaries and returns a third. Nothing here writes.
    """
    if not isinstance(previous, dict):
        return None
    before = (previous.get("risk") or {}).get("finalLevel")
    after = risk.get("finalLevel")
    if before not in GOVERNANCE_LEVELS or after not in GOVERNANCE_LEVELS:
        return None
    if GOVERNANCE_LEVELS.index(after) >= GOVERNANCE_LEVELS.index(before):
        return None
    was = list((previous.get("risk") or {}).get("signals") or [])
    now = list(risk.get("signals") or [])
    return {
        "from": before,
        "to": after,
        "fromExecutionId": previous.get("executionId"),
        "fromRecordedAt": previous.get("recordedAt"),
        "fromSignals": was,
        "toSignals": now,
        "signalsRemoved": sorted(set(was) - set(now)),
        "signalsAdded": sorted(set(now) - set(was)),
    }


def _policy_gate_reasons(classification: dict, final_level: str | None,
                         policy: dict) -> dict[str, list[str]]:
    """Which gates the policy DICTIONARIES name, and under which rule each.

    The one place the three ``required_gates_*`` tables are read. It knows
    nothing about a bound flow, so it can name a gate no flow contains; that
    is reported rather than dropped (see ``gate_requirements``).
    """
    reasons: dict[str, list[str]] = {}
    for gate in policy.get("required_gates_always") or []:
        reasons.setdefault(gate, []).append("always")
    for gate in (policy.get("required_gates_by_risk") or {}).get(
            final_level) or []:
        reasons.setdefault(gate, []).append(f"risk:{final_level}")
    wi_type = classification.get("type")
    for gate in (policy.get("required_gates_by_type") or {}).get(wi_type) or []:
        reasons.setdefault(gate, []).append(f"type:{wi_type}")
    return reasons


def required_gate_set(classification: dict, final_level: str,
                      policy: dict) -> list[str]:
    """The gates the effective policy NAMES for this classification and level.

    T06 wrote this to record "what the required gate set would be"; §15 is the
    phase that consumes it, and it is consumed rather than duplicated. It is
    still only half an answer on its own: a dictionary lookup cannot know
    which gates the bound flow actually contains, and it cannot see the
    derived terminal-gate rule. ``gate_requirements`` is the function that
    decides anything.
    """
    return sorted(_policy_gate_reasons(classification, final_level, policy))


# --------------------------------------------------------------------------
# Gate requirements — contract §15
# --------------------------------------------------------------------------
#
# §15 asks for "policy-driven gates without weakening governance", and §12's
# closing line is what makes that a coherent instruction rather than two
# contradictory ones:
#
#     Human approval remains policy-driven; review/validation is universal
#     for governed artifacts.
#
# So exactly ONE thing below is policy-driven: whether a gate the bound flow
# contains requires a HUMAN APPROVAL. Artifact generation, `artifact record`,
# the artifact SHA baseline, TP-011 review, the drift queue, the secrets scan,
# the test evidence, the implementation diff baseline, the audit chain, the
# retry/remediation caps and the fail-safe transitions are untouched and stay
# universal for every gate, required or not.
#
# The requirement set is DERIVED at every decision point and never stored. A
# stored table would be a second source of truth able to authorise an omission
# the current policy forbids (invariant 7), and it would need a state field, a
# migration row and a template change. Deriving costs nothing and makes the
# re-derivations at `advance` and at the terminal gate free.

# The closed disposition vocabulary. Three values, each a different fact:
# T07 introduced "the flow does not contain this phase" and T09 introduces
# "the policy does not require this gate"; conflating them is how a report
# comes to claim a guarantee nobody is enforcing.
GATE_DISPOSITIONS = ("required", "omittable", "not_in_flow")

# The decision value a policy-permitted omission records. Deliberately NOT
# "approved": an omission is a different fact from an approval, and the two
# must stay distinguishable in `state.json`, in the ledger, in `state dump`
# and in the completion summary. §15 requires every omitted gate to be
# explainable, and a value indistinguishable from an approval explains
# nothing.
GATE_OMITTED_DECISION = "omitted_by_policy"

# The decisions that mean "this gate has been passed and its artifact is
# baselined". Drift detection and repository staleness both key off this, so
# an omitted gate keeps every guarantee §15's "preserve Wave A guardrails"
# list names. Filtering on "approved" alone would let an omitted gate's
# artifact change afterwards with no drift raised.
BASELINED_GATE_DECISIONS = ("approved", GATE_OMITTED_DECISION)


def terminal_gate_key(flow: Flow) -> str | None:
    """The last gate of ``flow`` — the one immediately before ``complete``.

    Positional, and deliberately not a row in ``required_gates_always``. That
    matters twice. It names the real reason: this gate is required because it
    is the terminal human decision on the whole run, not because security
    review is universally mandatory — which is exactly what §15's exit
    criterion denies. And it cannot be removed by a repository override:
    overrides edit dictionaries, and a derived positional rule is in no
    dictionary, so monotonicity is not merely enforced for it, it is
    structurally unavailable.
    """
    return flow.gate_keys[-1] if flow.gate_keys else None


def gate_requirements(consts: Constants, flow: Flow, classification: dict,
                      final_level: str | None, policy: dict) -> dict:
    """Which of ``flow``'s gates require a human approval, and why.

    Pure: reads nothing from disk, writes nothing. The three dispositions are
    ``GATE_DISPOSITIONS``:

      ``required``     the bound flow contains this gate and the policy
                       requires a human approval for it;
      ``omittable``    the bound flow contains it and the policy does not
                       require approval; it may still be approved exactly as
                       today, or omitted through `gate omit`;
      ``not_in_flow``  the policy names it but the bound flow has no such
                       phase, so the requirement is inert — and is REPORTED
                       as inert rather than silently dropped.

    Every ``required`` entry carries at least one reason, so "why did this
    gate stop me" always has a machine-readable answer.
    """
    policy_reasons = _policy_gate_reasons(classification, final_level, policy)
    named = set(required_gate_set(classification, final_level, policy))
    terminal = terminal_gate_key(flow)
    phase_for = {key: phase for phase, key in consts.phase_to_gate_key.items()}

    dispositions: list[dict] = []
    for gate_key in flow.gate_keys:
        reasons = list(policy_reasons.get(gate_key) or [])
        if gate_key == terminal:
            reasons.append("terminal_gate")
        dispositions.append({
            "gate": gate_key,
            "gate_phase": phase_for.get(gate_key),
            "disposition": "required" if reasons else "omittable",
            "reasons": reasons,
        })

    return {
        "flow": flow.name,
        "final_risk": final_level,
        "classification": dict(classification),
        "terminal_gate": terminal,
        "dispositions": dispositions,
        "required_gates": sorted(d["gate"] for d in dispositions
                                 if d["disposition"] == "required"),
        "omittable_gates": sorted(d["gate"] for d in dispositions
                                  if d["disposition"] == "omittable"),
        "required_not_in_flow": sorted(named - set(flow.gate_keys)),
    }


def read_governance_record(paths: Paths) -> dict | None:
    """The recorded governance verdict, or ``None`` when there is none.

    A malformed record is an integrity failure, not an absence: treating it as
    absent would let a corrupt file read as "not yet assessed" and then be
    silently overwritten.
    """
    target = paths.governance_file
    if not target.is_file():
        return None
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise IntegrityError(
            "governance_record_invalid",
            f"{paths.runtime_relative}/{target.name} cannot be read: {exc}. "
            "Re-run `governance assess --input <path>`.",
            {"path": str(target), "error": str(exc)},
        ) from None
    if not isinstance(record, dict):
        raise IntegrityError(
            "governance_record_invalid",
            f"{paths.runtime_relative}/{target.name} is not a JSON object.",
            {"path": str(target)},
        )
    version = record.get("governanceVersion")
    if version not in GOVERNANCE_RECORD_VERSIONS:
        raise IntegrityError(
            "governance_record_invalid",
            f"{paths.runtime_relative}/{target.name} declares "
            f"governanceVersion {version!r}; this engine reads "
            + ", ".join(repr(v) for v in GOVERNANCE_RECORD_VERSIONS)
            + ". Re-run `governance assess --input <path>`.",
            {"path": str(target), "version": version,
             "supported": list(GOVERNANCE_RECORD_VERSIONS)},
        )
    return record


def governance_freshness(paths: Paths, record: dict) -> dict:
    """Is the recorded assessment still about the current requirements?

    Derived from the digest every time, never stored as a flag — a stored
    "fresh" boolean would be a second source of truth for the same fact.
    """
    sources, digest = requirements_sources(paths)
    recorded = ((record.get("requirements") or {}).get("digest"))
    return {
        "fresh": recorded == digest,
        "recorded_digest": recorded,
        "current_digest": digest,
        "current_sources": [entry["path"] for entry in sources],
    }


def gate_requirements_for_state(paths: Paths, consts: Constants,
                                state: dict) -> dict | None:
    """The requirement model for the WorkItem this ``state`` belongs to.

    ``None`` when it cannot be derived at all — the WorkItem holds no
    governance record yet.
    Every caller treats ``None`` as "nothing may be omitted here", which is
    the fail-closed direction: an omission nobody can justify is not one the
    engine will accept.

    Reads the policy from disk on every call, deliberately. A cached model
    would be the stored second source of truth this design refuses, and the
    whole point is that a recorded omission is re-derived rather than trusted.
    """
    record = read_governance_record(paths)
    if record is None:
        return None
    effective = read_governance_policy(paths, consts)
    model = gate_requirements(
        consts,
        flow_for_state(state, consts),
        record.get("classification") or {},
        (record.get("risk") or {}).get("finalLevel"),
        effective["policy"],
    )
    model["policy"] = {"source": effective["source"],
                       "sha256": effective["sha256"]}
    return model


def bind_for_governance(args, paths: Paths) -> Paths:
    """`governance` is runtime-free at the group level so `policy` can resolve
    with no WorkItem. Its WorkItem-scoped members bind here — through the
    ladder, never around it.

    T11 removed the second refusal this used to carry
    (``governance_workitem_required``): with the legacy rung gone a
    non-raising ``bind_workitem`` always names a WorkItem (R2), so the branch
    was unreachable code, not a guard.
    """
    return bind_workitem(paths, args.workitem)


def cmd_governance_assess(args, paths: Paths) -> int:
    """Evaluate Claude's structured proposal against the policy and persist
    the verdict.

    Deliberately does NOT require `state.json`: §12 places governance before
    planning, so this must be runnable before `init`. It therefore appends no
    audit entry — there is no `audit_sha` to rebaseline and no state file to
    save, and the single-writer discipline stays exactly as it is. The facts
    enter the ledger at `init` and at the first `advance`.
    """
    consts = load_constants(paths)
    paths = bind_for_governance(args, paths)

    effective = read_governance_policy(paths, consts)
    policy = effective["policy"]

    target = Path(args.input)
    if not target.is_absolute():
        target = paths.project_root / args.input
    relative = args.input.replace(os.sep, "/")

    document = read_governance_input(target, relative)
    quality = evaluate_quality(document, policy, relative)
    classification = evaluate_classification(document, relative)
    risk = evaluate_risk(document, policy, relative)

    # T11 D11: read the record this one replaces *before* it is overwritten.
    # A pure read, and the only thing it can produce is evidence.
    superseded = read_governance_record(paths)
    downgrade = governance_downgrade(superseded, risk)

    stamp = now_iso()
    # D04: claimed before `governance.json` is touched, so an id that cannot
    # be allocated refuses with nothing recorded.
    execution_id, evidence = reserve_evidence(
        paths, paths.evidence_dir, stamp,
        lambda eid: f"governance-{eid}.json")
    sources, digest = requirements_sources(paths)
    proposed_requirements = gate_requirements(
        consts, consts.flow(classification.get("flow")), classification,
        risk["finalLevel"], policy)

    record = {
        "governanceVersion": GOVERNANCE_RECORD_VERSION,
        "workitem": paths.workitem,
        "recordedAt": stamp,
        "executionId": execution_id,
        "requirements": {"sources": sources, "digest": digest},
        "quality": quality,
        "classification": classification,
        "risk": risk,
        # §15's dispositions for the flow this record PROPOSES. Recorded as
        # evidence of what the assessment implied, never read back for a
        # decision: `init` binds the flow, and every later decision re-derives
        # the model against the bound one.
        "requiredGates": proposed_requirements["required_gates"],
        "omittableGates": proposed_requirements["omittable_gates"],
        # T11 D11. Always present, `null` when this assessment did not lower
        # anything, so the record is self-describing rather than making a
        # reader infer "no downgrade" from an absent key.
        "downgrade": downgrade,
        "policy": {"source": effective["source"], "sha256": effective["sha256"]},
    }

    # Persisted BEFORE the blocking refusal, the same shape
    # `cmd_artifact_record` already uses: a blocked assessment must be
    # inspectable and remediable, not invisible.
    write_atomic(paths.governance_file, json.dumps(record, indent=2) + "\n")
    write_atomic(evidence, json.dumps({
        "kind": "governance",
        "executionId": execution_id,
        "recordedAt": stamp,
        "workitem": paths.workitem,
        "input": {"path": relative, "document": document},
        "record": record,
    }, indent=2) + "\n")

    evidence_relative = evidence.relative_to(paths.project_root).as_posix()
    if quality["result"] == "BLOCKED":
        failing = [c for c in quality["checks"]
                   if c["result"] == "FAIL" and c["blocking"]]
        detail = "; ".join(f"{c['id']}: {c['finding']}" for c in failing)
        raise Refused(
            "requirements_quality_blocked",
            "Requirements quality is BLOCKED and the workflow cannot "
            f"progress: {detail}. The assessment has been recorded at "
            f"{paths.runtime_relative}/{paths.governance_file.name}; fix the "
            "requirements and re-run `governance assess`.",
            {"workitem": paths.workitem,
             "blocking": quality["blocking"],
             "findings": {c["id"]: c["finding"] for c in failing},
             "record": f"{paths.runtime_relative}/"
                       f"{paths.governance_file.name}",
             "evidence": evidence_relative},
        )

    emit("governance assess", {
        "workitem": paths.workitem,
        "record": f"{paths.runtime_relative}/{paths.governance_file.name}",
        "evidence": evidence_relative,
        "quality": quality["result"],
        "advisory_findings": quality["advisory"],
        "classification": classification,
        "risk": risk,
        "downgrade": downgrade,
        "requirements_digest": digest,
        "policy": record["policy"],
    })
    return EXIT_OK


def cmd_governance_show(args, paths: Paths) -> int:
    """The recorded governance verdict plus a freshness verdict. Read-only."""
    paths = bind_for_governance(args, paths)
    record = read_governance_record(paths)
    if record is None:
        raise Refused(
            "governance_missing",
            f"WorkItem '{paths.workitem}' has no governance record. Run "
            "`governance assess --input <path>` first — contract §12 places "
            "governance before planning.",
            {"workitem": paths.workitem, "path": str(paths.governance_file)},
        )
    freshness = governance_freshness(paths, record)
    emit("governance show", {
        "workitem": paths.workitem,
        "record": record,
        # T11 D11: promoted out of `record` so a reader does not have to know
        # the record schema to see that a level was lowered.
        "downgrade": record.get("downgrade"),
        "fresh": freshness["fresh"],
        "recorded_digest": freshness["recorded_digest"],
        "current_digest": freshness["current_digest"],
        "requirements": freshness["current_sources"],
    })
    return EXIT_OK


def cmd_governance_gates(args, paths: Paths) -> int:
    """Which gates of the bound flow require a human approval, and why.

    Read-only, and answerable before `init` — which is why the flow is
    resolved from `state.json` when there is one and from the record's
    proposed classification otherwise, with `flow_source` saying which. A
    report that could only be produced after `init` would be useless at the
    moment the question is actually asked.

    This command REPORTS the model; it never makes a decision. `gate omit` is
    the only producer of an omission, and it re-derives the same model itself
    rather than trusting anything this printed.
    """
    consts = load_constants(paths)
    paths = bind_for_governance(args, paths)
    record = read_governance_record(paths)
    if record is None:
        raise Refused(
            "governance_missing",
            f"WorkItem '{paths.workitem}' has no governance record. Run "
            "`governance assess --input <path>` first.",
            {"workitem": paths.workitem, "path": str(paths.governance_file)},
        )
    effective = read_governance_policy(paths, consts)
    classification = record.get("classification") or {}
    final_level = (record.get("risk") or {}).get("finalLevel")

    if paths.state_file.is_file():
        flow = flow_for_state(read_state(paths), consts)
        flow_source = "state"
    else:
        flow = consts.flow(classification.get("flow"))
        flow_source = "record"

    model = gate_requirements(consts, flow, classification, final_level,
                              effective["policy"])
    emit("governance gates", {
        "workitem": paths.workitem,
        "classification": classification,
        "final_risk": final_level,
        "flow": flow.name,
        "flow_source": flow_source,
        "dispositions": model["dispositions"],
        "required_gates": model["required_gates"],
        "omittable_gates": model["omittable_gates"],
        # A policy may name a gate the bound flow does not contain. That
        # requirement is inert, and saying so is the point: an unreported
        # inert rule is how a policy comes to claim a guarantee nobody is
        # enforcing. Non-empty today for HOTFIX under the built-in policy.
        "required_not_in_flow": model["required_not_in_flow"],
        "registered_gates": sorted(consts.phase_to_gate_key.values()),
        "policy": {"source": effective["source"],
                   "sha256": effective["sha256"]},
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# Brownfield discovery — contract §14
# --------------------------------------------------------------------------
#
# §14 asks for a discovery output covering fourteen named categories in which
# **every finding is classified** OBSERVED / INFERRED / UNKNOWN, and states the
# rule the classification exists to serve: *never present inference as
# observation*.
#
# Discovery itself is judgement work. The deterministic core cannot read a
# repository and decide what its architecture is, so it does not pretend to.
# What it converts from prose into mechanism is exactly this, and no more:
#
#   * nothing is unclassified, and no fourth classification can be invented;
#   * an observation must point at a path that exists inside this repository;
#   * an inference must name the findings it rests on, and none of those may
#     itself be unknown;
#   * an unknown may not carry evidence;
#   * no declared category may be silently dropped — and because "unknown" is
#     an honest answer, that is always satisfiable without lying.
#
# What it deliberately does **not** guarantee, and must not be read as
# guaranteeing: that an observed statement is *true of* the file it cites,
# that an inference follows from its basis, or that the findings are complete.
# Those are claims by their author. Saying so is the point; a checker that
# implied more than it checks would be worse than no checker.
#
# The split is T06's verbatim (Claude proposes, deterministic policy decides)
# and is recorded in ADR-005.

DISCOVERY_PHASE = "discovery"
IMPACT_ANALYSIS_PHASE = "impact_analysis"
DISCOVERY_RECORD_VERSION = "1"
DISCOVERY_INPUT_VERSIONS = ("1",)
DISCOVERY_INPUT_SECTIONS = ("discoveryInputVersion", "findings")
DISCOVERY_FINDING_KEYS = ("id", "category", "classification", "statement",
                          "evidence", "basis")
DISCOVERY_REQUIRED_FINDING_KEYS = ("id", "category", "classification",
                                   "statement")

# §14's three classifications, closed. Ordered as §14 orders them; the last is
# the honest default, which is why `DISCOVERY_CLASSIFICATIONS[-1]` is a
# meaningful thing to say.
DISCOVERY_CLASSIFICATIONS = ("OBSERVED", "INFERRED", "UNKNOWN")

# §14's fourteen bullets, in §14's order. This tuple is the only home for the
# vocabulary: it reaches the prompt layer through `discovery schema` and is
# restated in no prompt or documentation file.
DISCOVERY_CATEGORIES = (
    "repository_inventory",
    "modules_components",
    "dependencies",
    "architecture",
    "significant_patterns",
    "conventions",
    "apis",
    "persistence_data_architecture",
    "test_practices",
    "runtime_deployment",
    "security_patterns",
    "adrs",
    "constraints_non_negotiables",
    "risks_debt",
)

# The rules the engine enforces, named so a refusal can cite one and so the
# prompt layer can be told what will be checked without restating how.
DISCOVERY_RULES = {
    "R-a": "unknown or missing top-level key; unsupported discoveryInputVersion",
    "R-b": "findings must be a non-empty list of objects with only the "
           "declared finding keys",
    "R-c": "each finding needs a unique, non-empty string id",
    "R-d": "category must be one of the declared categories",
    "R-e": "classification is required and must be one of the declared "
           "classifications",
    "R-f": "statement is required and must be non-empty",
    "R-g": "an observation must cite at least one evidence path, and every "
           "cited path must exist inside this repository",
    "R-h": "an inference must name a basis, every basis id must be a declared "
           "finding, and no basis may itself be unknown",
    "R-i": "an unknown may not carry evidence",
    "R-j": "every declared category needs at least one finding",
}

DISCOVERY_AUDIT_EVENT = "discovery_recorded"


def _discovery_malformed(relative: str, detail: str, rule: str,
                         **data) -> Refused:
    return Refused(
        "discovery_input_malformed",
        f"{relative} is not a usable discovery input: {detail} "
        f"[{rule}: {DISCOVERY_RULES[rule]}].",
        {"path": relative, "detail": detail, "rule": rule, **data},
    )


def read_discovery_input(target: Path, relative: str) -> dict:
    """Parse and envelope-validate Claude's proposed findings. Fail-closed:
    nothing here returns a default. Mirrors ``read_governance_input``."""
    if not target.is_file():
        raise _discovery_malformed(relative, "no such file", "R-a")
    try:
        raw = target.read_text(encoding="utf-8")
    except OSError as exc:
        raise _discovery_malformed(
            relative, f"it cannot be read ({exc})", "R-a") from None
    try:
        document = json.loads(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        raise _discovery_malformed(
            relative, f"it is not valid JSON ({exc})", "R-a") from None
    if not isinstance(document, dict):
        raise _discovery_malformed(relative, "it is not a JSON object", "R-a")

    unknown = sorted(set(document) - set(DISCOVERY_INPUT_SECTIONS))
    if unknown:
        raise _discovery_malformed(
            relative, f"unknown top-level key(s) {', '.join(unknown)}", "R-a",
            unknown_keys=unknown)
    missing = [k for k in DISCOVERY_INPUT_SECTIONS if k not in document]
    if missing:
        raise _discovery_malformed(
            relative, f"missing required key(s) {', '.join(missing)}", "R-a",
            missing_keys=missing)
    if document["discoveryInputVersion"] not in DISCOVERY_INPUT_VERSIONS:
        raise _discovery_malformed(
            relative,
            f"discoveryInputVersion {document['discoveryInputVersion']!r} is "
            "not supported; this engine supports "
            + ", ".join(repr(v) for v in DISCOVERY_INPUT_VERSIONS), "R-a")
    return document


def _evidence_problem(paths: Paths, value: object) -> str | None:
    """Why ``value`` is not a usable evidence path, or None when it is.

    "Points at something that exists inside this repository" is the whole of
    what the engine can check about an observation, so it is checked
    completely: type, absoluteness, escape and existence. Whether the
    statement is *true of* that file is not checkable here and is not claimed.
    """
    if not isinstance(value, str) or not value.strip():
        return "an evidence entry must be a non-empty repository-relative path"
    candidate = Path(value)
    if candidate.is_absolute():
        return (f"evidence path {value!r} is absolute; evidence paths are "
                "repository-relative")
    root = paths.project_root.resolve()
    try:
        resolved = (paths.project_root / candidate).resolve()
    except OSError:
        return f"evidence path {value!r} cannot be resolved"
    if not _within(resolved, root):
        return f"evidence path {value!r} escapes the repository root"
    if not resolved.exists():
        return f"evidence path {value!r} does not exist in this repository"
    return None


def _finding_list(entry: dict, key: str) -> list | None:
    """``entry[key]`` as a list, or None when it is present and not one."""
    value = entry.get(key, [])
    return value if isinstance(value, list) else None


def evaluate_discovery(document: dict, paths: Paths, relative: str) -> dict:
    """Rules R-b..R-j. Refuses; never repairs, never drops a finding.

    Two passes on purpose: a basis may name a finding declared later in the
    document, so classifications must all be known before R-h can be decided.
    """
    findings = document["findings"]
    if not isinstance(findings, list) or not findings:
        raise _discovery_malformed(
            relative, "'findings' must be a non-empty list", "R-b")

    classification_of: dict[str, str] = {}
    normalised: list[dict] = []

    for position, entry in enumerate(findings, start=1):
        if not isinstance(entry, dict):
            raise _discovery_malformed(
                relative, f"finding #{position} is not an object", "R-b",
                finding=position)
        unknown = sorted(set(entry) - set(DISCOVERY_FINDING_KEYS))
        if unknown:
            raise _discovery_malformed(
                relative,
                f"finding #{position} has unknown key(s) {', '.join(unknown)}",
                "R-b", finding=position, unknown_keys=unknown)

        identifier = entry.get("id")
        if not isinstance(identifier, str) or not identifier.strip():
            raise _discovery_malformed(
                relative, f"finding #{position} has no usable 'id'", "R-c",
                finding=position)
        if identifier in classification_of:
            raise _discovery_malformed(
                relative, f"finding id {identifier!r} is declared more than "
                "once", "R-c", finding=identifier)

        category = entry.get("category")
        if category not in DISCOVERY_CATEGORIES:
            raise _discovery_malformed(
                relative,
                f"finding {identifier!r} has category {category!r}, which is "
                "not one of the declared categories; ask `discovery schema`",
                "R-d", finding=identifier, value=category)

        classification = entry.get("classification")
        if classification not in DISCOVERY_CLASSIFICATIONS:
            raise _discovery_malformed(
                relative,
                f"finding {identifier!r} has classification "
                f"{classification!r}; every finding must carry one of the "
                "declared classifications, and a finding the repository does "
                "not answer is not unclassified — it is unknown",
                "R-e", finding=identifier, value=classification)

        statement = entry.get("statement")
        if not isinstance(statement, str) or not statement.strip():
            raise _discovery_malformed(
                relative, f"finding {identifier!r} has no 'statement'", "R-f",
                finding=identifier)

        evidence = _finding_list(entry, "evidence")
        if evidence is None:
            raise _discovery_malformed(
                relative, f"finding {identifier!r} has a non-list 'evidence'",
                "R-b", finding=identifier)
        basis = _finding_list(entry, "basis")
        if basis is None:
            raise _discovery_malformed(
                relative, f"finding {identifier!r} has a non-list 'basis'",
                "R-b", finding=identifier)

        observed, inferred, unknown_class = DISCOVERY_CLASSIFICATIONS
        if classification == observed:
            if not evidence:
                raise _discovery_malformed(
                    relative,
                    f"finding {identifier!r} is an observation but cites no "
                    "evidence; an observation asserts something read in a "
                    "named file", "R-g", finding=identifier)
            for item in evidence:
                problem = _evidence_problem(paths, item)
                if problem is not None:
                    raise _discovery_malformed(
                        relative, f"finding {identifier!r}: {problem}", "R-g",
                        finding=identifier, value=item)
        elif classification == inferred:
            if not basis:
                raise _discovery_malformed(
                    relative,
                    f"finding {identifier!r} is an inference but names no "
                    "basis; an inference must say what it rests on", "R-h",
                    finding=identifier)
        elif classification == unknown_class:
            if evidence:
                raise _discovery_malformed(
                    relative,
                    f"finding {identifier!r} is unknown but carries evidence; "
                    "a finding that cites evidence is an observation or an "
                    "inference", "R-i", finding=identifier)

        classification_of[identifier] = classification
        normalised.append({
            "id": identifier,
            "category": category,
            "classification": classification,
            "statement": statement,
            "evidence": list(evidence),
            "basis": list(basis),
        })

    # Pass two: R-h's referential half, once every id is known.
    unknown_class = DISCOVERY_CLASSIFICATIONS[-1]
    for finding in normalised:
        if finding["classification"] != DISCOVERY_CLASSIFICATIONS[1]:
            continue
        for reference in finding["basis"]:
            if reference not in classification_of:
                raise _discovery_malformed(
                    relative,
                    f"finding {finding['id']!r} rests on {reference!r}, which "
                    "is not a declared finding", "R-h",
                    finding=finding["id"], value=reference)
            if classification_of[reference] == unknown_class:
                raise _discovery_malformed(
                    relative,
                    f"finding {finding['id']!r} rests on {reference!r}, which "
                    "is itself unknown; an inference may not rest on an "
                    "unknown", "R-h", finding=finding["id"], value=reference)

    by_category = {
        category: [f["id"] for f in normalised if f["category"] == category]
        for category in DISCOVERY_CATEGORIES
    }
    empty = [c for c, ids in by_category.items() if not ids]
    if empty:
        raise Refused(
            "discovery_incomplete",
            f"{relative} leaves {len(empty)} declared discovery "
            f"categor{'y' if len(empty) == 1 else 'ies'} with no finding: "
            + ", ".join(empty) + f". [R-j: {DISCOVERY_RULES['R-j']}] "
            "Where the repository does not answer, say so — an unknown "
            "finding is the honest answer and is accepted.",
            {"path": relative, "rule": "R-j", "missing": empty},
        )

    counts = {name: 0 for name in DISCOVERY_CLASSIFICATIONS}
    for finding in normalised:
        counts[finding["classification"]] += 1

    return {"result": "PASS", "counts": counts, "categories": by_category,
            "findings": normalised}


def read_discovery_record(paths: Paths) -> dict | None:
    """The recorded findings, or ``None`` when there are none.

    Fail-closed against ``read_governance_record``: a malformed record is an
    integrity failure, not an absence. Reading a corrupt file as "not yet
    discovered" would let it be silently overwritten.
    """
    target = paths.discovery_file
    if not target.is_file():
        return None
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise IntegrityError(
            "discovery_record_invalid",
            f"{paths.runtime_relative}/{target.name} cannot be read: {exc}. "
            "Re-run `discovery assess --input <path>`.",
            {"path": str(target), "error": str(exc)},
        ) from None
    if not isinstance(record, dict):
        raise IntegrityError(
            "discovery_record_invalid",
            f"{paths.runtime_relative}/{target.name} is not a JSON object.",
            {"path": str(target)},
        )
    return record


def discovery_accepted(paths: Paths) -> dict | None:
    """This WorkItem's accepted discovery record, or None.

    A record that names another WorkItem is not this WorkItem's: the file
    could only get there by being copied, and inheriting someone else's
    discovery is exactly the thing §14's exit criterion is about doing
    *deliberately*, through the baseline, not by accident.
    """
    record = read_discovery_record(paths)
    if record is None:
        return None
    if record.get("result") != "PASS":
        return None
    if record.get("workitem") != paths.workitem:
        return None
    return record


def bind_for_discovery(args, paths: Paths) -> Paths:
    """`discovery` is runtime-free at the group level so `schema` can be read
    with no WorkItem. `assess` binds here — through the ladder, never around
    it. The shape `bind_for_governance` established, including T11's removal
    of the now-unreachable ``discovery_workitem_required`` refusal (R2).
    """
    return bind_workitem(paths, args.workitem)


def cmd_discovery_schema(args, paths: Paths) -> int:
    """The closed vocabulary, emitted rather than restated.

    This command is how the category ids, the classifications, the envelope
    and the rule ids reach the prompt layer — the same device `governance
    policy` already is for the check ids. Writes nothing and needs no
    WorkItem, so it is answerable before a workflow exists.
    """
    emit("discovery schema", {
        "input_versions": list(DISCOVERY_INPUT_VERSIONS),
        "envelope": list(DISCOVERY_INPUT_SECTIONS),
        "finding_keys": list(DISCOVERY_FINDING_KEYS),
        "required_finding_keys": list(DISCOVERY_REQUIRED_FINDING_KEYS),
        "categories": list(DISCOVERY_CATEGORIES),
        "classifications": list(DISCOVERY_CLASSIFICATIONS),
        "rules": dict(DISCOVERY_RULES),
        "record_version": DISCOVERY_RECORD_VERSION,
        "enforced": [
            "every finding carries one of the declared classifications",
            "an observation cites at least one path that exists in this "
            "repository",
            "an inference names a basis, and no basis is itself unknown",
            "an unknown carries no evidence",
            "every declared category carries at least one finding",
        ],
        "not_enforced": [
            "whether an observed statement is true of the file it cites",
            "whether an inference follows from its basis",
            "whether the findings are complete",
        ],
    })
    return EXIT_OK


def cmd_discovery_assess(args, paths: Paths) -> int:
    """Evaluate the proposed findings and record them.

    Every refusal fires before the first write, so a refused assess leaves
    `discovery.json`, `audit.md` and `state.json` exactly as they were. That
    is the opposite of `governance assess`, which persists a blocked
    assessment on purpose so it can be remediated — there is nothing to
    remediate in a document the engine could not parse, and a partially
    validated discovery record must never become the thing that authorises
    leaving the phase.
    """
    paths = bind_for_discovery(args, paths)
    state = read_state(paths)

    target = Path(args.input)
    if not target.is_absolute():
        target = paths.project_root / args.input
    relative = args.input.replace(os.sep, "/")

    document = read_discovery_input(target, relative)
    evaluation = evaluate_discovery(document, paths, relative)

    stamp = now_iso()
    execution_id, evidence = reserve_evidence(
        paths, paths.evidence_dir, stamp,
        lambda eid: f"discovery-{eid}.json")
    record = {
        "discoveryVersion": DISCOVERY_RECORD_VERSION,
        "workitem": paths.workitem,
        "recordedAt": stamp,
        "executionId": execution_id,
        "result": evaluation["result"],
        "counts": evaluation["counts"],
        "categories": evaluation["categories"],
        "findings": evaluation["findings"],
    }
    write_atomic(paths.discovery_file, json.dumps(record, indent=2) + "\n")
    write_atomic(evidence, json.dumps({
        "kind": "discovery",
        "executionId": execution_id,
        "recordedAt": stamp,
        "workitem": paths.workitem,
        "input": {"path": relative, "document": document},
        "record": record,
    }, indent=2) + "\n")

    record_relative = paths.discovery_file.relative_to(
        paths.project_root).as_posix()
    evidence_relative = evidence.relative_to(paths.project_root).as_posix()
    counts = evaluation["counts"]
    append_audit(
        paths, state,
        phase=state.get("current_phase") or DISCOVERY_PHASE,
        event=DISCOVERY_AUDIT_EVENT,
        message=(
            f"Discovery recorded: {len(evaluation['findings'])} finding(s) "
            f"across {len(DISCOVERY_CATEGORIES)} categories ("
            + ", ".join(f"{name} {counts[name]}"
                        for name in DISCOVERY_CLASSIFICATIONS) + ")."
        ),
        artifact=record_relative,
        artifact_sha=sha256_file(paths.discovery_file),
        evidence_id=execution_id,
    )
    save_state(paths, state, args.session)

    emit("discovery assess", {
        "workitem": paths.workitem,
        "record": record_relative,
        "evidence": evidence_relative,
        "result": evaluation["result"],
        "findings": len(evaluation["findings"]),
        "counts": counts,
        "categories": evaluation["categories"],
    })
    return EXIT_OK


def cmd_discovery_show(args, paths: Paths) -> int:
    """The recorded findings. Read-only."""
    paths = bind_for_discovery(args, paths)
    record = read_discovery_record(paths)
    if record is None:
        raise Refused(
            "discovery_missing",
            f"WorkItem '{paths.workitem}' has no discovery record. Run "
            "`discovery assess --input <path>` first.",
            {"workitem": paths.workitem, "path": str(paths.discovery_file)},
        )
    emit("discovery show", {"workitem": paths.workitem, "record": record})
    return EXIT_OK


def discovery_precondition(paths: Paths, state: dict | None = None) -> None:
    """§14 — a WorkItem may not leave `discovery` without a validated record.

    Enforced from ``apply_advance``, so `advance` **and** `skip` both hit it.
    Placing it in `cmd_advance` alone would let `skip` walk past discovery,
    which is fail-open: `skip` exists for a *failed* generation step, and a
    discovery record that was never produced is exactly that case.

    A **pure reader**: no state write, no `append_audit`. Every caller places
    it ahead of its first irreversible write, so a refused advance, approval
    or skip leaves `audit.md` byte-identical (B1, NB-6).

    Only the phase is tested, not the flow: `discovery` is in exactly one
    flow's declared phases, so a WorkItem can only be standing here if that is
    the flow it is traversing. **T11 removed the legacy-binding carve-out**:
    there is no binding without a WorkItem, so the rule now applies
    unconditionally.
    """
    if (state or {}).get("current_phase") != DISCOVERY_PHASE:
        return None
    if discovery_accepted(paths) is not None:
        return None
    raise Refused(
        "discovery_missing",
        f"WorkItem '{paths.workitem}' is at {DISCOVERY_PHASE} and has no "
        "accepted discovery record, so the workflow cannot leave the phase. "
        "Contract §14 requires the repository to be read, and the findings "
        "classified, before anything is drafted from them: run `discovery "
        "assess --input <path>`. `sdle.sh discovery schema` reports what the "
        "document must contain.",
        {"workitem": paths.workitem, "phase": DISCOVERY_PHASE,
         "path": str(paths.discovery_file)},
    )


# --------------------------------------------------------------------------
# The repository baseline — contract §14
# --------------------------------------------------------------------------
#
# §11 left `.sdle/baseline.json` as a documented empty slot and §14 gives it
# its schema. It is the artifact that makes the convergence invariant real:
# after *either* greenfield completion *or* brownfield discovery completion a
# repository has the same minimum baseline shape, and every later WorkItem
# converges onto ITERATIVE instead of rediscovering the repository.
#
# It **references** canonical artifacts and never copies them (§14, and
# invariant 7). Every reference is `{path, sha256}`: a pointer plus a
# fingerprint. `nonNegotiables` holds finding *ids* into the discovery record,
# never prose — the record is the findings' one home.
#
# Reading is fail-closed, deliberately against `read_repo_config`'s
# swallow-and-default (T05 NB-4): a silently defaulted baseline would make the
# convergence invariant unprovable, which is the failure direction ADR-003 §3
# already rejected once for the governance policy.

BASELINE_VERSION = "1"
SUPPORTED_BASELINE_VERSIONS = ("1",)

# §14's nine facts, as the keys that carry them: baseline version, producing
# WorkItem (inside `establishedBy`), commit SHA, constitution reference,
# architecture/design references, ADR references, non-negotiables, discovery
# status (inside `discovery`) and timestamp.
BASELINE_REQUIRED_KEYS = (
    "baselineVersion", "establishedAt", "establishedBy", "commit",
    "discovery", "references", "nonNegotiables", "supersedes",
)
BASELINE_REFERENCE_KINDS = ("constitution", "architecture", "adrs")

# Which flows establish a baseline. §14's convergence sentence names greenfield
# completion and brownfield discovery completion, and nothing else: letting a
# flow that performed no discovery establish a "discovered" baseline is exactly
# the thing that would make the invariant decorative.
BASELINE_ESTABLISHING_FLOWS = ("GREENFIELD", "BROWNFIELD_DISCOVERY")

# The two flows §14 and §13 make conditional on the baseline, and nothing else.
# `BASELINE_REDISCOVERY_FLOW` is the one that performs discovery, so it is the
# only flow `classification.rediscovery` can meaningfully accompany, and the
# only one a sound baseline refuses. `BASELINE_REQUIRING_FLOW` is §13's
# "use established repository baseline, no full repository rediscovery".
#
# `DEFECT_FIX` and `HOTFIX` are deliberately absent: §13 gives them no baseline
# clause, and blocking an emergency hotfix on a repository-level artifact would
# be a governance change §14 did not ask for.
BASELINE_REDISCOVERY_FLOW = "BROWNFIELD_DISCOVERY"
BASELINE_REQUIRING_FLOW = "ITERATIVE"

DISCOVERY_PERFORMED, DISCOVERY_NOT_REQUIRED = "PERFORMED", "NOT_REQUIRED"
BASELINE_AUDIT_EVENT = "baseline_established"

# The four derived statuses. `ABSENT` emits no finding at all: most
# repositories have no baseline and that is not a defect.
BASELINE_ABSENT, BASELINE_VALID = "ABSENT", "VALID"
BASELINE_STALE, BASELINE_INVALID = "STALE", "INVALID"


def _reference(paths: Paths, relative: str | None) -> dict | None:
    """A `{path, sha256}` pointer, or None when there is nothing to point at.

    Never returns content. The descriptor is a set of references and this is
    the only function that builds one, so "references, never copies" is a
    property of one function rather than a rule four call sites must remember.
    """
    if not relative:
        return None
    target = paths.project_root / relative
    if not target.is_file():
        return None
    return {"path": relative, "sha256": sha256_file(target)}


def baseline_descriptor(paths: Paths, state: dict, consts: Constants,
                        execution_id: str, stamp: str) -> dict:
    """Build the descriptor. **Total by construction: never raises.**

    An absent constitution yields ``null``, an absent design document yields
    ``[]``, an absent discovery record yields ``NOT_REQUIRED``. Validity is
    derived *later*, by ``baseline_findings``, and never asserted here —
    because this runs inside the final gate approval, after `gate_approved` is
    already in the append-only ledger, and an append cannot be undone by a
    later raise. Writing the baseline must not be able to block a human's
    final approval.
    """
    flow = (state.get("flow") or DEFAULT_FLOW)
    constitution_path, _ = resolve_artifact_path(
        state, consts, "gate_constitution", paths)
    design_path, _ = resolve_artifact_path(state, consts, "gate_design", paths)

    record = None
    try:
        record = discovery_accepted(paths)
    except IntegrityError:
        # A corrupt discovery record is reported by `validate` and by
        # `discovery show`. Here it degrades to "no record", because the one
        # thing this function may not do is raise.
        record = None

    findings = (record or {}).get("findings") or []
    observed = DISCOVERY_CLASSIFICATIONS[0]
    adr_refs: list[dict] = []
    for finding in findings:
        if finding.get("category") != "adrs":
            continue
        if finding.get("classification") != observed:
            continue
        for cited in finding.get("evidence") or []:
            reference = _reference(paths, cited)
            if reference and reference not in adr_refs:
                adr_refs.append(reference)

    architecture = _reference(paths, design_path)
    previous = None
    try:
        existing = read_baseline(paths)
    except IntegrityError:
        existing = None
    if isinstance(existing, dict):
        previous = {
            "establishedAt": existing.get("establishedAt"),
            "sha256": sha256_file(paths.baseline_file)
            if paths.baseline_file.is_file() else None,
        }

    return {
        "baselineVersion": BASELINE_VERSION,
        "establishedAt": stamp,
        "establishedBy": {
            "workitem": paths.workitem,
            "flow": flow,
            "executionId": execution_id,
        },
        "commit": _git_value(paths, "rev-parse", "HEAD"),
        "discovery": {
            "status": (DISCOVERY_PERFORMED if record is not None
                       else DISCOVERY_NOT_REQUIRED),
            "record": (paths.discovery_file.relative_to(paths.project_root)
                       .as_posix()) if record is not None else None,
            "recordSha256": (sha256_file(paths.discovery_file)
                             if record is not None else None),
            "counts": (record or {}).get("counts") if record else None,
        },
        "references": {
            "constitution": _reference(paths, constitution_path),
            "architecture": [architecture] if architecture else [],
            "adrs": adr_refs,
        },
        "nonNegotiables": {
            "source": (paths.discovery_file.relative_to(paths.project_root)
                       .as_posix()) if record is not None else None,
            "findingIds": [f["id"] for f in findings
                           if f.get("category") == "constraints_non_negotiables"],
        },
        "supersedes": previous,
    }


def read_baseline(paths: Paths) -> dict | None:
    """The repository baseline, or ``None`` when there is none.

    Fail-closed, mirroring ``read_governance_record`` and deliberately **not**
    ``read_repo_config``: absent is ``None``; unreadable, unparseable,
    non-object or an unsupported ``baselineVersion`` is an ``IntegrityError``.
    There is no ``return <default>`` in any handler here, and there must not
    be: a baseline that silently defaulted would let a corrupt file read as
    "not yet established" and be overwritten, and would make §14's convergence
    invariant unprovable.
    """
    target = paths.baseline_file
    if not target.is_file():
        return None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise IntegrityError(
            "baseline_invalid",
            f"{paths.config_root_relative}/{target.name} cannot be read: "
            f"{exc}. Delete it to return the repository to a baseline-free "
            "state, or restore it from version control.",
            {"path": str(target), "error": str(exc)},
        ) from None
    if not isinstance(document, dict):
        raise IntegrityError(
            "baseline_invalid",
            f"{paths.config_root_relative}/{target.name} is not a JSON object.",
            {"path": str(target)},
        )
    if document.get("baselineVersion") not in SUPPORTED_BASELINE_VERSIONS:
        raise IntegrityError(
            "baseline_invalid",
            f"{paths.config_root_relative}/{target.name} declares "
            f"baselineVersion {document.get('baselineVersion')!r}; this "
            "engine supports "
            + ", ".join(repr(v) for v in SUPPORTED_BASELINE_VERSIONS) + ".",
            {"path": str(target), "version": document.get("baselineVersion")},
        )
    return document


def _baseline_reference_paths(document: dict) -> list[dict]:
    """Every `{path, sha256}` the descriptor points at, flattened."""
    references = document.get("references") or {}
    flat: list[dict] = []
    constitution = references.get("constitution")
    if isinstance(constitution, dict):
        flat.append(constitution)
    for kind in ("architecture", "adrs"):
        for entry in references.get(kind) or []:
            if isinstance(entry, dict):
                flat.append(entry)
    discovery = document.get("discovery") or {}
    if discovery.get("status") == DISCOVERY_PERFORMED and discovery.get("record"):
        flat.append({"path": discovery["record"],
                     "sha256": discovery.get("recordSha256")})
    return flat


def baseline_findings(paths: Paths) -> list[dict]:
    """The single answer to "is this repository's baseline sound".

    Two consumers — `baseline show`/`baseline validate`, and `validate` — so
    they can never disagree about the same repository (invariant 7). The
    `repo_config_findings` shape exactly.

    **Material invalidation** is the error set and nothing else:
    `baseline_invalid`, `baseline_producer_unregistered`,
    `baseline_reference_missing`. A *changed* reference is a warning, because
    `design_generation` runs in ITERATIVE and rewrites the design document: if
    change invalidated the baseline, the third WorkItem in any repository
    would be forced back into full rediscovery, which is exactly what §26
    item 22 says must not happen. A missing reference is different in kind —
    the baseline's claims can no longer be checked at all.
    """
    if not paths.baseline_file.is_file():
        return []

    relative = f"{paths.config_root_relative}/{paths.baseline_file.name}"
    try:
        document = read_baseline(paths)
    except IntegrityError as exc:
        return [_finding("baseline_invalid", VALIDATE_ERROR, exc.message,
                         path=paths.baseline_file)]
    if document is None:                       # pragma: no cover - raced away
        return []

    findings: list[dict] = []
    missing_keys = [k for k in BASELINE_REQUIRED_KEYS if k not in document]
    if missing_keys:
        findings.append(_finding(
            "baseline_invalid", VALIDATE_ERROR,
            f"{relative} is missing required key(s) "
            + ", ".join(missing_keys),
            path=paths.baseline_file))
        return findings

    producer = (document.get("establishedBy") or {}).get("workitem")
    try:
        registered = registered_workitem_ids(paths)
    except SdleError:
        # A registry too broken to read is diagnosed by `validate`'s own
        # `index_malformed` path at the same exit code. Not re-diagnosed here.
        registered = None
    if registered is not None and producer not in registered:
        findings.append(_finding(
            "baseline_producer_unregistered", VALIDATE_ERROR,
            f"{relative} was established by WorkItem {producer!r}, which is "
            "not registered in workitems/index.md; the baseline names a "
            "producer this repository cannot account for",
            workitem=producer if isinstance(producer, str) else None,
            path=paths.baseline_file))

    for reference in _baseline_reference_paths(document):
        cited = reference.get("path")
        if not isinstance(cited, str) or not cited:
            findings.append(_finding(
                "baseline_invalid", VALIDATE_ERROR,
                f"{relative} carries a reference with no path",
                path=paths.baseline_file))
            continue
        target = paths.project_root / cited
        if not target.is_file():
            findings.append(_finding(
                "baseline_reference_missing", VALIDATE_ERROR,
                f"{relative} references {cited}, which no longer exists; the "
                "baseline's claims about it can no longer be checked",
                path=target))
            continue
        recorded = reference.get("sha256")
        if recorded and sha256_file(target) != recorded:
            findings.append(_finding(
                "baseline_reference_changed", VALIDATE_WARNING,
                f"{relative} references {cited}, which exists but has changed "
                "since the baseline was established; a changed reference is "
                "reported, never a refusal — later WorkItems legitimately "
                "rewrite design documents",
                path=target))
    return findings


def baseline_status(findings: list[dict], present: bool) -> str:
    """The status those findings add up to. Derived, never stored."""
    if not present:
        return BASELINE_ABSENT
    if any(f["severity"] == VALIDATE_ERROR for f in findings):
        return BASELINE_INVALID
    if findings:
        return BASELINE_STALE
    return BASELINE_VALID


def baseline_commit(paths: Paths) -> str | None:
    """The commit the baseline was established at, or ``None``.

    T11 N11. A baseline finding says *what* is wrong; without the commit it
    was established at, a reader cannot tell *which* repository state the
    baseline's claims were ever true for. Deliberately swallowing to ``None``
    on an unreadable file: this is a decoration on a refusal that has already
    been decided, and it must never turn a diagnosed ``INVALID`` into an
    exit-3.
    """
    try:
        return (read_baseline(paths) or {}).get("commit")
    except SdleError:
        return None


def baseline_state(paths: Paths) -> tuple[str, list[dict]]:
    """``(status, findings)`` for this repository. The one entry point."""
    present = paths.baseline_file.is_file()
    findings = baseline_findings(paths)
    return baseline_status(findings, present), findings


def baseline_precondition(paths: Paths, flow: str, rediscovery: bool) -> str:
    """§14's exit criterion and §13's ITERATIVE definition, enforced at the
    single flow-binding site. Returns the derived baseline status.

    | Id | Rule | Reason code |
    |----|------|-------------|
    | R1 | Binding the discovery flow while the baseline is `VALID` or `STALE`, without a rediscovery request | `baseline_present` |
    | R2 | Binding the iterative flow while the baseline is `ABSENT` or `INVALID` | `baseline_required` |

    **R1 is §14's exit criterion enforced rather than asserted:** the second
    WorkItem against the same valid baseline does not rerun full discovery,
    because the engine will not let it. **R2 is §13's ITERATIVE definition made
    true** — without it the convergence invariant is decorative.

    A `STALE` baseline satisfies R1 and R2 on purpose. A changed reference is a
    warning (see `baseline_findings`), and forcing rediscovery on it would
    contradict §26 item 22.

    A **pure reader**: no state write, no `append_audit`. `cmd_init` calls it
    *before* its first `mkdir`, so a refusal creates nothing at all — no
    runtime directory, no execution file, no audit entry. It is evaluated only
    at `init`, because the flow binds once and re-checking at every `advance`
    would refuse a run mid-flight over a repository-level fact the WorkItem
    cannot fix. The status it returns is recorded in the `flow_selected` audit
    entry, so the facts the decision was made on are auditable.

    **T11 removed the legacy-binding carve-out**: there is no binding without
    a WorkItem, so R1 and R2 now apply unconditionally.
    """
    status, findings = baseline_state(paths)
    relative = f"{paths.config_root_relative}/{paths.baseline_file.name}"
    data = {"workitem": paths.workitem, "flow": flow, "baseline_status": status,
            "path": relative, "findings": findings,
            # T11 N11: which repository state the baseline ever described.
            "baseline_commit": baseline_commit(paths)}

    if flow == BASELINE_REDISCOVERY_FLOW and status in (BASELINE_VALID,
                                                        BASELINE_STALE):
        if rediscovery:
            return status
        raise Refused(
            "baseline_present",
            f"This repository already has a {status} baseline at {relative}, "
            f"so {flow} would rediscover what has already been discovered. "
            "Contract §14 performs full repository discovery once. Either "
            f"re-assess this WorkItem as {BASELINE_REQUIRING_FLOW}, which is "
            "what a repository with a baseline is for, or record "
            "classification.rediscovery as true to ask for a deliberate "
            "rediscovery.",
            data,
        )

    if flow == BASELINE_REQUIRING_FLOW and status in (BASELINE_ABSENT,
                                                      BASELINE_INVALID):
        detail = ("no baseline has been established yet"
                  if status == BASELINE_ABSENT
                  else "; ".join(f["detail"] for f in findings))
        raise Refused(
            "baseline_required",
            f"{flow} works from an established repository baseline and "
            f"performs no rediscovery, but {relative} is {status}: {detail}. "
            "Complete a "
            + " or ".join(BASELINE_ESTABLISHING_FLOWS)
            + " WorkItem first — either establishes one at its final gate.",
            data,
        )

    return status


def establish_baseline(paths: Paths, state: dict, consts: Constants,
                       stamp: str) -> tuple[str | None, str | None]:
    """§14's convergence invariant made literal. **The only writer.**

    Called from exactly one place — the ``is_final`` branch of
    ``cmd_gate_approve`` — and only for the two flows §14's convergence
    sentence names (``BASELINE_ESTABLISHING_FLOWS``). There is deliberately no
    ``baseline establish`` / ``baseline set`` command: a second writer would
    let the model manufacture the very fact that authorises ITERATIVE, which
    is the governance bypass ADR-004 §3 refused for ``flow set``.

    Returns ``(relative_path, sha256)``, or ``(None, None)`` when the
    completing flow establishes no baseline. Returning the pair rather than
    the ``Paths`` member is what keeps ``cmd_gate_approve`` out of the
    repository-configuration reference set: the lifecycle reaches the §11
    boundary *through* this function and never names a member itself.

    **It never refuses and never raises on missing inputs.**
    ``baseline_descriptor`` is total by construction, and this runs after
    ``gate_approved`` is already in the append-only ledger, where a raise
    could not be undone. Validity is derived later by ``baseline_findings``,
    never asserted here.
    """
    if (state.get("flow") or DEFAULT_FLOW) not in BASELINE_ESTABLISHING_FLOWS:
        return None, None
    descriptor = baseline_descriptor(
        paths, state, consts, execution_identity(paths, stamp), stamp)
    target = paths.baseline_file
    write_atomic(target, json.dumps(descriptor, indent=2) + "\n")
    return target.relative_to(paths.project_root).as_posix(), sha256_file(target)


def cmd_baseline_show(args, paths: Paths) -> int:
    """The baseline, its derived status and its findings. Writes nothing."""
    status, findings = baseline_state(paths)
    document = None
    if status not in (BASELINE_ABSENT, BASELINE_INVALID):
        document = read_baseline(paths)
    elif status == BASELINE_INVALID:
        try:
            document = read_baseline(paths)
        except IntegrityError:
            document = None
    emit("baseline show", {
        "status": status,
        "path": f"{paths.config_root_relative}/{paths.baseline_file.name}",
        "present": paths.baseline_file.is_file(),
        "findings": findings,
        "baseline": document,
        "establishing_flows": list(BASELINE_ESTABLISHING_FLOWS),
    })
    return EXIT_OK


def cmd_baseline_validate(args, paths: Paths) -> int:
    """Exit 0 only on VALID. Writes nothing, and appends nothing."""
    status, findings = baseline_state(paths)
    data = {
        "status": status,
        "path": f"{paths.config_root_relative}/{paths.baseline_file.name}",
        "findings": findings,
        # T11 N11, the same fact in the same shape as `baseline_precondition`.
        "baseline_commit": baseline_commit(paths),
        "errors": len([f for f in findings if f["severity"] == VALIDATE_ERROR]),
        "warnings": len([f for f in findings
                         if f["severity"] == VALIDATE_WARNING]),
    }
    if status != BASELINE_VALID:
        raise Refused(
            "baseline_not_valid",
            f"The repository baseline is {status}. "
            + ("No baseline has been established: complete a "
               + " or ".join(BASELINE_ESTABLISHING_FLOWS)
               + " WorkItem, which establishes one at its final gate."
               if status == BASELINE_ABSENT
               else "; ".join(f["detail"] for f in findings)),
            data,
        )
    emit("baseline validate", data)
    return EXIT_OK


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
        # T11 D8: a missing flag is a *usage* error (exit 2) and must not
        # share `workitem_required`, which is the resolution refusal (exit 1).
        raise UsageError(
            "workitem_flag_required",
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
    execution_id, evidence_file = reserve_evidence(
        paths, target.evidence_dir, stamp,
        lambda eid: f"migration-{eid}.json")
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

    # Step 11 — point this working directory at the migrated WorkItem.
    # Strictly after the commit write and its verification, so a crash can
    # never leave a context naming a runtime that is not authoritative. Like
    # `init`, a failure here is not allowed to fail an already-committed
    # migration.
    try:
        write_active_context(target, requested, "migrate-workflow")
    except OSError:
        pass

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
    state: dict, consts: Constants, gate_key: str, paths: Paths
) -> tuple[str | None, str | None]:
    """Resolve ARTIFACT_OWNERSHIP's template for ``gate_key``.

    Returns ``(resolved_path, skip_reason)``. A skip reason means the gate has
    no comparable artifact yet — not that something failed.

    Two placeholders name a location only the active binding knows:
    ``{workitem_runtime}`` is the WorkItem runtime (``.workflow`` under the
    transitional legacy binding) and ``{speckit_feature_directory}`` is
    ``specKit.featureDirectory``. ``paths`` is therefore a required argument —
    an omitted binding could otherwise resolve a literal placeholder onto
    disk. T02's transitional ``.workflow/`` prefix bridge is gone: the
    templates themselves now carry the placeholder (finding NB-1).
    """
    template = consts.artifact_ownership.get(gate_key)
    if not template or template == "(none)":
        return None, "no artifact registered for this gate"

    resolved = template.replace("{workitem_runtime}", paths.runtime_relative)

    for placeholder, label, value in (
        ("{speckit_feature_directory}", "speckit_feature_directory",
         speckit_ref(state)["featureDirectory"]),
        ("{security_review_artifact}", "security_review_artifact",
         state.get("security_review_artifact")),
    ):
        if placeholder in resolved:
            if not value:
                return None, f"{label} is not resolved yet"
            resolved = resolved.replace(placeholder, str(value))
    return resolved, None


# What resolves each ARTIFACT_OWNERSHIP binding, named in the D01 refusal so
# the recovery is actionable rather than "something is missing".
ARTIFACT_BINDING_RECOVERY = {
    "speckit_feature_directory":
        "run `feature resolve` so this WorkItem's feature directory is "
        "recorded",
    "security_review_artifact":
        "run `security-review begin`, which names the review file, and write "
        "the review there",
}

# The last sentence of each `artifact_missing` refusal, by the command that
# raised it. Approval and omission keep their pre-D01 wording verbatim.
ARTIFACT_MISSING_CONSEQUENCE = {
    "approve": "A gate is an approval of specific content.",
    "omit": "An omission is still a decision about specific content — the "
            "artifact is generated, registered and reviewed whether or not a "
            "human has to approve it.",
    "re-approve": "Drift re-approval re-baselines the gate onto specific "
                  "content, and there is none. Restore the artifact, or "
                  "`restart` the phase that produces it.",
}


def required_gate_artifact(paths: Paths, state: dict, consts: Constants,
                           gate_key: str, action: str
                           ) -> tuple[str | None, str | None]:
    """**D01 (SDLE-DEFECT-STABILIZATION-01).** Resolve the artifact a gate
    decision is about, and fingerprint it, or refuse.

    Returns ``(resolved_path, sha)``. Both are ``None`` only for a gate that
    registers no artifact at all (an ARTIFACT_OWNERSHIP template of
    ``(none)``) — the one legitimate artifact-free gate.

    Before D01 every caller treated an *unresolved* template the same way:
    ``resolve_artifact_path`` answered ``(None, reason)`` and the gate was
    decided with ``sha: null``. That approved a Spec Kit gate whose feature
    directory had never been resolved, and completed a whole flow on a
    security gate whose review file had never been named. A registered
    artifact that cannot be resolved, found or read is now a refusal, raised
    by a pure reader ahead of every write, so the refusal leaves the phase, the
    approvals and the ledger exactly as they were.

    One place, three callers: `gate approve`, drift re-approval and `gate
    omit` are the three decisions that fingerprint an artifact.
    """
    template = consts.artifact_ownership.get(gate_key)
    if not template or template == "(none)":
        return None, None

    resolved, _ = resolve_artifact_path(state, consts, gate_key, paths)
    if not resolved:
        binding = next(
            (label for label in ARTIFACT_BINDING_RECOVERY
             if "{" + label + "}" in template), None)
        data = {"gate": gate_key, "template": template, "binding": binding}
        if binding == "speckit_feature_directory":
            searched, tier, found = feature_candidate_tier(paths)
            names = sorted(p.name for p in found)
            data.update(candidates=names, searched=searched, tier=tier)
            if len(names) > 1:
                raise Refused(
                    "feature_ambiguous",
                    f"Cannot {action} {gate_key}: no feature directory is "
                    f"recorded for '{paths.workitem}', and {len(names)} "
                    f"candidates exist under {tier}/: {', '.join(names)}. SDLE "
                    "will not choose between them. Move the one this WorkItem "
                    f"owns into {paths.speckit_specs_relative}/ and run "
                    "`feature resolve`.",
                    data,
                )
        raise Refused(
            "artifact_unresolved",
            f"Cannot {action} {gate_key}: its artifact ({template}) cannot be "
            f"resolved because {binding or 'a binding'} is not recorded. A "
            "gate decision is about specific content, and there is none to "
            f"fingerprint. To recover, "
            f"{ARTIFACT_BINDING_RECOVERY.get(binding, 'resolve the binding')}"
            ", then try again.",
            data,
        )

    full = paths.project_root / resolved
    if not full.is_file():
        raise Refused(
            "artifact_missing",
            f"Cannot {action} {gate_key}: {resolved} does not exist. "
            + ARTIFACT_MISSING_CONSEQUENCE[action],
            {"gate": gate_key, "path": resolved},
        )
    try:
        sha = sha256_file(full)
    except OSError as exc:
        raise Refused(
            "artifact_unreadable",
            f"Cannot {action} {gate_key}: {resolved} exists but cannot be "
            f"read ({exc.strerror or exc}), so it cannot be fingerprinted. "
            "Fix its permissions or whatever holds it open, then try again.",
            {"gate": gate_key, "path": resolved, "error": str(exc)},
        ) from None
    return resolved, sha


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


GOVERNANCE_AUDIT_EVENT = "governance_recorded"
GOVERNANCE_DOWNGRADE_EVENT = "governance_downgraded"


def governance_audit_marker(execution_id: str) -> str:
    """The unambiguous string that says "this assessment is already in the
    ledger". Derived from the record, so nothing has to be stored twice."""
    return f"(governance execution {execution_id})"


def governance_downgrade_marker(execution_id: str) -> str:
    """The same idiom for the T11 D11 downgrade entry. A separate marker, so
    the two entries de-duplicate independently and neither can suppress the
    other."""
    return f"(governance downgrade {execution_id})"


def record_governance_audit(paths: Paths, state: dict, record: dict) -> None:
    """Carry the recorded governance facts into the ledger exactly once.

    §12 wants the deterministic score, the hard floors, the proposed level and
    the final level to be auditable, and a lowering attempt in particular must
    leave a trace even though it is not a refusal (D6.5): the security
    property is that the attempt has no *effect*, and an attempt nobody can
    see afterwards is not the same thing.

    `governance assess` cannot write this itself — it runs before `init`, so
    there is no `audit_sha` to rebaseline (D4). `cmd_init` cannot write it
    either: it is on the plan's byte-identical list (A9). So the entry lands
    at the first phase movement that actually consumes the record, and is
    de-duplicated by the record's own `executionId`: re-assessing produces a
    new entry, advancing eighteen times does not produce eighteen.
    """
    execution_id = record.get("executionId")
    if not execution_id:
        return
    marker = governance_audit_marker(execution_id)
    if paths.audit_file.is_file():
        if marker in paths.audit_file.read_text(encoding="utf-8"):
            _record_governance_downgrade_audit(paths, state, record)
            return

    risk = record.get("risk") or {}
    classification = record.get("classification") or {}
    floors = [entry.get("raisedTo") for entry in (risk.get("floorsApplied") or [])]
    lowering = (
        "; Claude proposed a lower level and it had no effect"
        if risk.get("loweringAttempted") else ""
    )
    # §15's gate evidence, APPENDED so every existing prefix reads the same.
    # Read off the record rather than re-derived: this sentence describes what
    # the assessment implied, and a pre-T09 record simply has nothing to say.
    required = record.get("requiredGates")
    dispositions = "" if required is None else (
        " Gate approvals this assessment requires: "
        f"{', '.join(required) or 'none'}; omittable: "
        f"{', '.join(record.get('omittableGates') or []) or 'none'}."
    )
    append_audit(
        paths,
        state,
        phase=state.get("current_phase") or "unknown",
        event=GOVERNANCE_AUDIT_EVENT,
        message=(
            f"Governance recorded {marker}: quality "
            f"{(record.get('quality') or {}).get('result')}, classification "
            f"{classification.get('type')}/{classification.get('flow')} "
            "(flow selects the lifecycle; type advisory), risk score "
            f"{risk.get('score')} -> deterministic {risk.get('deterministicLevel')}"
            + (f" (floors: {', '.join(floors)})" if floors else "")
            + f", proposed {risk.get('proposedLevel')}, final "
            f"{risk.get('finalLevel')}{lowering}." + dispositions
        ),
    )
    _record_governance_downgrade_audit(paths, state, record)


def _record_governance_downgrade_audit(paths: Paths, state: dict,
                                       record: dict) -> None:
    """**T11 D11.** A second, distinct ledger entry when this assessment
    lowered a level that had already been recorded.

    Deliberately its own event rather than a clause inside
    `governance_recorded`: §15 asks for every omission to be *explainable*,
    and an explanation someone has to parse out of a longer sentence is
    weaker evidence than an event with its own name that `grep` finds. The
    de-duplication marker is the record's own `executionId`, exactly like its
    sibling, so re-advancing does not re-log it.

    It never refuses and never changes a level. It is the record of a fact.
    """
    downgrade = record.get("downgrade")
    if not isinstance(downgrade, dict):
        return
    execution_id = record.get("executionId")
    if not execution_id:
        return
    marker = governance_downgrade_marker(execution_id)
    if paths.audit_file.is_file():
        if marker in paths.audit_file.read_text(encoding="utf-8"):
            return
    removed = ", ".join(downgrade.get("signalsRemoved") or []) or "none"
    added = ", ".join(downgrade.get("signalsAdded") or []) or "none"
    append_audit(
        paths,
        state,
        phase=state.get("current_phase") or "unknown",
        event=GOVERNANCE_DOWNGRADE_EVENT,
        message=(
            f"Governance level LOWERED {marker}: final risk "
            f"{downgrade.get('from')} -> {downgrade.get('to')}, superseding "
            f"the record from execution {downgrade.get('fromExecutionId')} "
            f"recorded at {downgrade.get('fromRecordedAt')}. Risk signals "
            f"were [{', '.join(downgrade.get('fromSignals') or []) or 'none'}]"
            f" and are now "
            f"[{', '.join(downgrade.get('toSignals') or []) or 'none'}] "
            f"(removed: {removed}; added: {added}). This is a re-assessment, "
            "not an override: no policy floor moved, and every gate the new "
            "level makes omittable still needs an explicit, audited `gate "
            "omit`. Recorded because a gate omitted after this point rests "
            "on the lower level."
        ),
    )


# --------------------------------------------------------------------------
# Governed artifact review (contract TP-011, §12; T06/D9)
#
# "Artifact existence alone is not evidence of artifact quality." Registration
# (`artifact record`) and approval (`gate approve`) already existed and each
# owns a different fact; review is a third fact with its own home, and
# "currently reviewed" is a *derived* predicate — never a stored flag, which
# would be a second source of truth for the same thing.
# --------------------------------------------------------------------------

REVIEWS_VERSION = "1"
REVIEW_ACTOR_TYPES = ("human", "agent", "tool", "test", "system")
REVIEW_RESULTS = ("PASS", "FAIL")


def review_key(paths: Paths, raw: str) -> str:
    """The canonical repo-relative POSIX key for an artifact.

    A backslash-separated path and its POSIX spelling name the same artifact,
    so they must not become two keys — that would let a second review "not
    exist" and a stale one survive (the v1.12->v1.13 lesson).
    """
    text = str(raw).replace("\\", "/")
    if os.path.isabs(str(raw)) or (len(text) > 1 and text[1] == ":"):
        try:
            text = (Path(raw).resolve()
                    .relative_to(paths.project_root.resolve()).as_posix())
        except ValueError:
            raise Refused(
                "review_path_outside_project",
                f"{raw} is not inside the project root, so it is not a "
                "governed artifact of this WorkItem.",
                {"path": str(raw), "project_root": str(paths.project_root)},
            ) from None
    parts = [part for part in text.split("/") if part not in ("", ".")]
    if any(part == ".." for part in parts):
        raise Refused(
            "review_path_outside_project",
            f"{raw} escapes the project root.",
            {"path": str(raw)},
        )
    return "/".join(parts)


def read_reviews(paths: Paths) -> list[dict]:
    """The append-only review ledger. Fail-closed: a ledger SDLE cannot read
    is not the same thing as an artifact nobody reviewed."""
    if not paths.reviews_file.is_file():
        return []
    try:
        document = json.loads(paths.reviews_file.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise Refused(
            "reviews_malformed",
            f"{paths.runtime_relative}/reviews.json cannot be read ({exc}). "
            "SDLE will not treat an unreadable review ledger as an empty one.",
            {"path": str(paths.reviews_file), "error": str(exc)},
        ) from None
    if not isinstance(document, dict) or not isinstance(
            document.get("reviews"), list):
        raise Refused(
            "reviews_malformed",
            f"{paths.runtime_relative}/reviews.json is not a review ledger.",
            {"path": str(paths.reviews_file)},
        )
    return [record for record in document["reviews"] if isinstance(record, dict)]


def review_status(paths: Paths, resolved: str,
                  reviews: list[dict] | None = None) -> dict:
    """Is this artifact, *at its current content*, currently reviewed?

    Recomputed from SHAs on every call. Nothing here reads a stored freshness
    flag, and `artifact review` writes none: TP-011 clause 1 is about the
    exact current content version, and a boolean cannot say that.
    """
    key = review_key(paths, resolved)
    full = paths.project_root / key
    current = sha256_file(full) if full.is_file() else None
    records = [record for record in
               (read_reviews(paths) if reviews is None else reviews)
               if record.get("path") == key]
    matching = [record for record in records
                if str(record.get("sha256") or "").lower() == (current or "")]
    newest = matching[-1] if matching else None
    return {
        "path": key,
        "current_sha": current,
        "reviewed_shas": [record.get("sha256") for record in records],
        "records": len(records),
        "result": newest.get("result") if newest else None,
        "reviewType": newest.get("reviewType") if newest else None,
        "current": bool(newest) and newest.get("result") == "PASS",
    }


def impact_analysis_precondition(paths: Paths,
                                 state: dict | None = None) -> None:
    """A WorkItem may not leave `impact_analysis` without a reviewed analysis.

    The mirror of `discovery_precondition`, and added for the same reason:
    `modules/phase-execution.md` tells the orchestrator to write the analysis,
    `artifact record` it and `artifact review` it, and until now the engine
    enforced none of that -- `advance --to spec_draft` succeeded with nothing
    written. A phase contract the engine does not back is a suggestion, and
    the whole point of the deterministic core is that it refuses rather than
    trusting the caller to have complied.

    The two "understand before you draft" phases now behave alike: `discovery`
    surveys a repository before a brownfield WorkItem specifies anything, and
    `impact_analysis` establishes a defect's blast radius before a fix is
    specified. Leaving one enforced and the other not was an accident of
    sequencing -- §14 demanded discovery's rule explicitly and nothing made
    the same demand of T07's gateless phase.

    A **pure reader**: it writes no state and appends nothing to the ledger.
    Callers place it ahead of their first irreversible write so a refused
    advance, approval, omission or skip leaves `audit.md` byte-identical
    (B1, NB-6). Spelling that out in prose rather than naming the write
    primitives is deliberate: N24/A18 counts those names textually across the
    whole engine, and a docstring is not a call site.

    The review must be *current*, not merely present, which is why this reads
    `review_status` rather than looking for any past record: TP-011 clause 1
    is about the exact content version, and editing the analysis after review
    makes it stale by the existing mechanism. That is also why the phase
    contract says to record the review last.

    Only the phase is tested, not the flow. `impact_analysis` belongs to
    exactly two flows, so a WorkItem standing here is necessarily traversing
    one of them -- the same argument `discovery_precondition` makes.
    """
    if (state or {}).get("current_phase") != IMPACT_ANALYSIS_PHASE:
        return None

    recorded = (state or {}).get("current_artifact")
    if recorded:
        status = review_status(paths, recorded)
        if status["current"]:
            return None
        detail = (
            f"'{recorded}' is recorded but its review is not current"
            if status["records"] else
            f"'{recorded}' is recorded but has never been reviewed"
        )
    else:
        detail = "no analysis has been recorded"

    raise Refused(
        "impact_analysis_missing",
        f"WorkItem '{paths.workitem}' is at {IMPACT_ANALYSIS_PHASE} and "
        f"{detail}, so the workflow cannot leave the phase. A defect is "
        "specified from its blast radius, not before it: write the analysis, "
        "then `artifact record --phase impact_analysis --path <file>` and "
        "`artifact review --path <file> --type impact-analysis --result PASS "
        "--actor-type agent --actor-name sdle-orchestrator`. Record the "
        "review last -- editing the file afterwards makes it stale.",
        {"workitem": paths.workitem, "phase": IMPACT_ANALYSIS_PHASE,
         "artifact": recorded},
    )


def review_precondition(paths: Paths, state: dict, gate_key: str,
                        resolved: str | None) -> None:
    """Enforcement clause E2 — TP-011 at the approval choke point.

    Called from both ``cmd_gate_approve`` and ``_approve_drift``. Drift is
    precisely the case TP-011's staleness rule is drawn for: approving drifted
    content against a review of the pre-drift content is the exact violation,
    so the drift path is guarded too rather than trusted.

    Skipped only when the gate has no resolvable artifact — there is nothing
    to review. **T11 removed the other half of this carve-out with the rung
    itself**: E2 now applies to every bound WorkItem, unconditionally.
    """
    if not resolved:
        return None
    if not (paths.project_root / review_key(paths, resolved)).is_file():
        return None  # `artifact_missing` is the caller's refusal to raise.

    status = review_status(paths, resolved)
    if not status["records"]:
        raise Refused(
            "review_missing",
            f"{status['path']} has not been reviewed, so {gate_key} cannot be "
            "approved. Contract TP-011: artifact existence is not evidence of "
            "artifact quality. Record one with `artifact review --path "
            f"{status['path']} --type <type> --result PASS --actor-type "
            "<human|agent|tool|test|system> --actor-name <name>`.",
            {"gate": gate_key, "path": status["path"],
             "current_sha": status["current_sha"]},
        )
    if status["result"] is None:
        raise Refused(
            "review_stale",
            f"{status['path']} has changed since it was reviewed, so "
            f"{gate_key} cannot be approved: a review applies to the exact "
            "content version it was performed against. Re-review the current "
            "content.",
            {"gate": gate_key, "path": status["path"],
             "reviewed_sha": status["reviewed_shas"][-1],
             "reviewed_shas": status["reviewed_shas"],
             "current_sha": status["current_sha"]},
        )
    if status["result"] != "PASS":
        raise Refused(
            "review_failed",
            f"The most recent review of {status['path']} at its current "
            f"content is {status['result']}, so {gate_key} cannot be "
            "approved. Fix the artifact and review it again.",
            {"gate": gate_key, "path": status["path"],
             "result": status["result"],
             "current_sha": status["current_sha"]},
        )
    return None


def cmd_artifact_review(args, paths: Paths) -> int:
    """Record a review of an artifact's exact current content (TP-011)."""
    state = read_state(paths)

    if args.result not in REVIEW_RESULTS:
        raise Refused(
            "review_result_invalid",
            f"--result {args.result!r} is not a governed result; use "
            + " or ".join(REVIEW_RESULTS) + ".",
            {"result": args.result, "permitted": list(REVIEW_RESULTS)},
        )
    if args.actor_type not in REVIEW_ACTOR_TYPES:
        raise Refused(
            "review_actor_invalid",
            f"--actor-type {args.actor_type!r} is not one of "
            + ", ".join(REVIEW_ACTOR_TYPES) + ". TP-011 clause 6 names the "
            "actor kinds a review may be attributed to.",
            {"actor_type": args.actor_type,
             "permitted": list(REVIEW_ACTOR_TYPES)},
        )
    if not (args.actor_name or "").strip():
        raise Refused(
            "review_actor_invalid",
            "--actor-name must name the reviewer; an anonymous review "
            "identifies no source.",
            {"actor_type": args.actor_type},
        )
    if not (args.type or "").strip():
        raise Refused(
            "review_type_invalid",
            "--type must name the review or validation type (TP-011 clause "
            "4): a result with no type says nothing about what was checked.",
            {"path": args.path},
        )

    key = review_key(paths, args.path)
    full = paths.project_root / key
    if not full.is_file():
        raise Refused(
            "artifact_missing",
            f"Cannot review {key}: it does not exist. A review applies to "
            "specific content.",
            {"path": key},
        )
    sha = sha256_file(full)

    reviews = read_reviews(paths)
    stamp = now_iso()
    execution_id, evidence = reserve_evidence(
        paths, paths.evidence_dir, stamp,
        lambda eid: f"review-{eid}-{len(reviews) + 1}.json")
    evidence_id = evidence.relative_to(paths.project_root).as_posix()

    record = {
        "path": key,
        "sha256": sha,
        "reviewType": args.type,
        "result": args.result,
        "evidenceId": evidence_id,
        "actor": {"type": args.actor_type, "name": args.actor_name},
        "comments": args.comments,
        "timestamp": stamp,
    }
    reviews.append(record)
    write_atomic(paths.reviews_file, json.dumps(
        {"reviewsVersion": REVIEWS_VERSION, "reviews": reviews}, indent=2) + "\n")
    write_atomic(evidence, json.dumps({
        "kind": "review",
        "executionId": execution_id,
        "workitem": paths.workitem,
        "record": record,
        "detail": args.evidence,
    }, indent=2) + "\n")

    append_audit(
        paths,
        state,
        phase=state.get("current_phase") or "unknown",
        event="artifact_reviewed",
        message=f"{args.type} review of {key} recorded: {args.result}.",
        artifact=key,
        artifact_sha=sha,
        comments=args.comments,
        review=f"{args.type} | {args.result} | {args.actor_type}:{args.actor_name}",
        evidence_id=evidence_id,
    )
    save_state(paths, state, args.session)

    emit("artifact review", {
        "path": key,
        "sha256": sha,
        "result": args.result,
        "reviewType": args.type,
        "actor": record["actor"],
        "evidenceId": evidence_id,
        "reviews": len(reviews),
    })
    return EXIT_OK


def cmd_artifact_reviews(args, paths: Paths) -> int:
    """List review records with a derived freshness verdict. Read-only."""
    reviews = read_reviews(paths)
    if args.path:
        key = review_key(paths, args.path)
        listed = [record for record in reviews if record.get("path") == key]
        subjects = [key]
    else:
        listed = reviews
        subjects = sorted({record.get("path") for record in reviews
                           if record.get("path")})
    emit("artifact reviews", {
        "reviews": listed,
        "status": {subject: review_status(paths, subject, reviews)
                   for subject in subjects},
    })
    return EXIT_OK


def governance_precondition(paths: Paths, state: dict | None = None) -> None:
    """E1 — contract §12's "blocking findings stop progression".

    §12 requires governance metadata to exist *before* current planning and
    implementation begin, and states three consequences as MUSTs. The core
    refuses; it does not warn. A warning a caller can ignore would leave the
    model free to reason its way past a blocking requirements finding, which
    is exactly what this phase exists to prevent.

    Enforced from ``apply_advance`` — the one function ``cmd_advance``,
    ``cmd_gate_approve`` and ``cmd_skip`` all funnel through — so there is
    exactly one place the rule is written. ``cmd_init`` does not call
    ``apply_advance``: governance is deliberately not an ``init``
    precondition, because §12 asks for it before *planning*, and a WorkItem
    must be able to bootstrap.

    ``cmd_gate_approve`` calls it a second time, earlier, and deliberately
    without ``state``. That command appends its ``gate_approved`` entry
    before it moves the phase, and an append to the ledger cannot be undone
    by a later raise; refusing ahead of the first irreversible write is what
    keeps a refusal byte-identical in ``audit.md``. Passing no ``state``
    makes the early call side-effect free, so the facts still enter the
    ledger exactly once, from ``apply_advance``.

    **T11 removed the legacy-binding carve-out along with the rung itself**:
    there is no binding without a WorkItem, so E1 now applies unconditionally.
    """
    record = read_governance_record(paths)
    if record is None:
        raise Refused(
            "governance_missing",
            f"WorkItem '{paths.workitem}' has no governance record, so the "
            "workflow cannot advance. Contract §12 requires deterministic "
            "governance metadata before planning begins: run `governance "
            "assess --input <path>`.",
            {"workitem": paths.workitem, "path": str(paths.governance_file)},
        )

    quality = record.get("quality") or {}
    if quality.get("result") != "PASS":
        blocking = quality.get("blocking") or []
        findings = {
            check.get("id"): check.get("finding")
            for check in (quality.get("checks") or [])
            if check.get("id") in blocking
        }
        detail = ("; ".join(f"{name}: {text}" for name, text in findings.items())
                  or "the recorded assessment does not report a quality PASS")
        raise Refused(
            "governance_blocked",
            f"Requirements quality is {quality.get('result') or 'unrecorded'} "
            f"for WorkItem '{paths.workitem}', so the workflow cannot "
            f"advance: {detail}. Fix the requirements and re-run `governance "
            "assess`.",
            {"workitem": paths.workitem,
             "result": quality.get("result"),
             "blocking": blocking,
             "findings": findings},
        )

    freshness = governance_freshness(paths, record)
    if not freshness["fresh"]:
        raise Refused(
            "governance_stale",
            f"The governance record for '{paths.workitem}' was assessed "
            "against different requirements than the ones on disk now, so it "
            "cannot authorise this advance. Re-run `governance assess "
            "--input <path>`.",
            {"workitem": paths.workitem,
             "recorded_digest": freshness["recorded_digest"],
             "current_digest": freshness["current_digest"],
             "requirements": freshness["current_sources"]},
        )

    # Accepted. The facts enter the ledger here, after every refusal has had
    # its chance to fire, so a refused advance never writes anything.
    if state is not None:
        record_governance_audit(paths, state, record)
    return None


def flow_precondition(paths: Paths, state: dict | None = None) -> None:
    """D10 — a flow cannot change under a workflow that has already started.

    `init` binds `state["flow"]` from the governance record; re-assessing
    afterwards with a different flow would otherwise silently re-shape a
    lifecycle mid-run, which is precisely the reshaping-by-command that D9
    refuses to provide as a feature. So the disagreement is a refusal with a
    named remedy, not a warning.

    Deliberately a **pure reader**: it never writes state and never appends to
    the ledger, and every caller places it ahead of its first `append_audit`.
    That is what keeps `audit.md` byte-identical across a refused advance,
    approval or skip (B1, and the ordering NB-6 recorded for `cmd_skip`).

    **T11 removed the legacy-binding carve-out**: there is no binding without
    a WorkItem, so D10 now applies unconditionally.
    """
    record = read_governance_record(paths)
    if record is None:
        return None
    proposed = (record.get("classification") or {}).get("flow")
    bound = (state or {}).get("flow") or DEFAULT_FLOW
    if not proposed or proposed == bound:
        return None
    raise Refused(
        "flow_mismatch",
        f"This WorkItem is traversing {bound}; the governance record now "
        f"proposes {proposed}. A flow cannot change under a workflow that has "
        f"already started. Either re-assess with flow {bound}, or `reset "
        "workflow` and start again.",
        {"workitem": paths.workitem, "bound": bound, "proposed": proposed},
    )


def apply_advance(
    paths: Paths,
    state: dict,
    consts: Constants,
    target: str,
    status: str | None,
    outcome: str,
) -> dict:
    """Move to ``target``, enforcing the refusals that matter.

    Refuses a forward jump (any target that is not NEXT_PHASE[current]),
    refuses to leave a gate phase whose approval is not recorded, and (T06)
    refuses to move at all without a passing, current governance record. These
    are the guardrails the model must not be able to reason its way around.

    Order is load-bearing: the two original refusals still fire first, so no
    existing refusal is masked by the new one.
    """
    current = state.get("current_phase")
    if current is None:
        raise IntegrityError(
            "state_unreadable", "state.json has no current_phase.", {}
        )

    flow = flow_for_state(state, consts)
    expected = flow.next_phase(current)
    if target != expected:
        # A target the registry does not know at all is still `unknown_phase`;
        # a real phase that this flow does not run is a forward jump, flagged
        # `in_flow: false` so a caller can tell the two apart. Positions are
        # computed defensively: an index lookup that raised here would mask
        # the real reason for the refusal.
        if target not in consts.phase_sequence:
            consts.index(target)  # raises unknown_phase; one message, one home
        raise Refused(
            "forward_jump",
            f"Cannot advance {current} -> {target}. The only permitted next "
            f"phase is {expected}. Forward jumps are not allowed; to advance "
            "through the workflow, approve the intervening gates.",
            {
                "from": current,
                "requested": target,
                "expected": expected,
                "from_index": flow.position(current),
                "requested_index": flow.position(target),
                "flow": flow.name,
                "in_flow": flow.contains(target),
            },
        )

    gate_key = gate_key_for(consts, current)
    if gate_key is not None:
        decision = approval_decision(state, gate_key)
        if decision == GATE_OMITTED_DECISION:
            # §15/D9 — a recorded omission is RE-DERIVED here, never trusted.
            # The stored value only says a policy once permitted this; the
            # question at the choke point is whether the policy permits it
            # now. Re-deriving closes the hand-edited-state path and any
            # window between `gate omit` and this advance, and it costs one
            # file read. CLAUDE.md's design is that the choke-point refusal is
            # the guarantee, so the guarantee is computed here rather than
            # read back from the state the command is being asked to trust.
            model = gate_requirements_for_state(paths, consts, state)
            if model is None or gate_key not in model["omittable_gates"]:
                raise Refused(
                    "gate_omission_invalidated",
                    f"{current} records a policy omission for {gate_key}, but "
                    "the governance record and policy in effect right now "
                    "require a human approval for that gate. An omission is "
                    "re-derived at every advance and never trusted. Either "
                    f"`gate approve --gate {gate_key}`, or `restart --to "
                    "<phase index>` and take the decision again.",
                    {"gate": gate_key, "phase": current, "decision": decision,
                     "final_risk": (model or {}).get("final_risk"),
                     "required_gates": (model or {}).get("required_gates"),
                     "derivable": model is not None},
                )
        elif decision != "approved":
            raise Refused(
                "gate_not_approved",
                f"{current} has not been approved (decision: {decision or 'none'}). "
                "A gate can only be passed by an explicit approval.",
                {"gate": gate_key, "phase": current, "decision": decision},
            )

    # T07/D10's placement is load-bearing, and it is written out in three
    # steps rather than two because `governance_precondition(paths, state)` is
    # not a pure reader — it records the governance facts in the ledger. So:
    #   1. validate the record with no `state`, which writes nothing, so a
    #      stale or blocked record is still reported as `governance_stale` /
    #      `governance_blocked` and is never masked by a flow disagreement;
    #   2. refuse `flow_mismatch`, still ahead of every write;
    #   3. only then let the accepted facts enter the ledger.
    # Steps 1 and 3 are the same rule with its one home unchanged; step 1 is
    # the same pure-reader device `cmd_gate_approve` and `cmd_skip` use.
    governance_precondition(paths)
    flow_precondition(paths, state)
    discovery_precondition(paths, state)
    impact_analysis_precondition(paths, state)
    governance_precondition(paths, state)

    if status is None:
        status = "awaiting_approval" if target in consts.phase_to_gate_key else "pending"

    state.setdefault("phase_history", []).append(
        {"phase": current, "completed_at": now_iso(), "outcome": outcome}
    )
    state["current_phase"] = target
    state["status"] = status
    state["progress"] = flow.progress_for(target)
    return {
        "from": current,
        "to": target,
        "status": status,
        "progress": state["progress"],
    }


def cmd_advance(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    branch_guard(args, paths, state)
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


def revalidate_recorded_omissions(paths: Paths, state: dict,
                                  consts: Constants, gate_key: str) -> None:
    """D10 — the terminal gate re-checks every omission taken before it.

    A gate already passed is never revisited, so an omission recorded at LOW
    would otherwise survive a later re-assessment that raised the level. The
    workflow is declared finished at the terminal gate — that is where the
    whole run still has to be admissible, and the last moment at which
    refusing costs less than unpicking a completed workflow.

    A PURE READER. Its caller places it among `cmd_gate_approve`'s other pure
    readers, ahead of the first `append_audit`, so a refusal leaves `audit.md`
    byte-identical (the B1/NB-6 property). It reads the policy only when there
    is an omission to revalidate, so a run that approved everything pays
    nothing and behaves exactly as it did before T09.
    """
    omitted = sorted(
        key for key, entry in (state.get("approvals") or {}).items()
        if isinstance(entry, dict)
        and entry.get("decision") == GATE_OMITTED_DECISION)
    if not omitted:
        return None
    if gate_key != terminal_gate_key(flow_for_state(state, consts)):
        return None

    model = gate_requirements_for_state(paths, consts, state)
    omittable = set(model["omittable_gates"]) if model else set()
    invalid = [key for key in omitted if key not in omittable]
    if not invalid:
        return None
    raise Refused(
        "gate_omission_invalidated",
        f"This workflow omitted {', '.join(invalid)} under a policy that no "
        "longer permits it, so it cannot be declared complete. Either "
        "`restart --to <phase index>` back to that gate and approve it, or "
        "re-assess so the recorded governance matches the decisions already "
        "taken.",
        {"gate": gate_key, "invalidated": invalid,
         "final_risk": (model or {}).get("final_risk"),
         "required_gates": (model or {}).get("required_gates"),
         "derivable": model is not None},
    )


def require_gate(consts: Constants, gate_key: str) -> str:
    for phase, key in consts.phase_to_gate_key.items():
        if key == gate_key:
            return phase
    raise Refused(
        "unknown_gate",
        f"'{gate_key}' is not a registered gate key.",
        {"gate": gate_key, "known": sorted(consts.phase_to_gate_key.values())},
    )


def gate_disposition(paths: Paths, consts: Constants, state: dict,
                     gate_key: str) -> dict | None:
    """§15 — whether ``gate_key`` needs a human approval, and why.

    ``None`` when the question has no answer for this runtime: the legacy
    `.workflow/` binding has no WorkItem and therefore no governance record,
    and a gate outside the bound flow has no disposition. Reporting `false`
    in either case would be an answer the engine has not got.

    Extracted so `gate show` and `resume` cannot answer the same question
    differently. A second derivation of gate requirement would be exactly the
    second source of truth invariant 7 forbids.
    """
    model = gate_requirements_for_state(paths, consts, state)
    return next(
        (entry for entry in (model or {}).get("dispositions") or []
         if entry["gate"] == gate_key), None)


def cmd_gate_show(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    gate_phase = require_gate(consts, args.gate)
    flow = flow_for_state(state, consts)
    resolved, skipped = resolve_artifact_path(state, consts, args.gate, paths)
    full = paths.project_root / resolved if resolved else None
    disposition = gate_disposition(paths, consts, state, args.gate)
    emit(
        "gate show",
        {
            "gate": args.gate,
            "gate_phase": gate_phase,
            "gate_number": flow.gate_number(args.gate),
            "gate_total": flow.gate_total,
            "flow": flow.name,
            "in_flow": flow.contains(gate_phase),
            "label": consts.label_or(gate_phase, flow),
            "execution_phase": consts.gate_to_execution_phase.get(args.gate),
            "artifact_path": resolved,
            "skipped_reason": skipped,
            "exists": bool(full and full.is_file()),
            "artifact_sha": sha256_file(full) if full and full.is_file() else None,
            "baseline_sha": (state.get("artifact_shas") or {}).get(args.gate),
            "decision": approval_decision(state, args.gate),
            "required": (None if disposition is None
                         else disposition["disposition"] == "required"),
            "requirement_reasons": (None if disposition is None
                                    else disposition["reasons"]),
        },
    )
    return EXIT_OK


def write_completion_summary(paths: Paths, state: dict) -> str:
    approvals = state.get("approvals") or {}
    summary = {
        "workflow_version": state.get("workflow_version"),
        # Which lifecycle was traversed. `all_gates_approved` below keeps its
        # meaning, now scoped to the gates this flow actually has.
        "flow": state.get("flow"),
        "project_name": state.get("project_name"),
        "completed_at": now_iso(),
        "phases_completed": len(state.get("phase_history") or []),
        "security_review_artifact": state.get("security_review_artifact"),
        # DERIVED at T09, where it used to be the literal `True`. Every gate
        # is still passed by an explicit, recorded decision — but from T09
        # that decision may be a policy-permitted omission, and a summary that
        # went on claiming every gate was APPROVED would state a guarantee the
        # run does not carry. Narrow on purpose: it reports `false` for the
        # one fact this phase introduces and for nothing else, so a run that
        # approved everything still reads `true` exactly as it always did.
        "all_gates_approved": not any(
            isinstance(entry, dict)
            and entry.get("decision") == GATE_OMITTED_DECISION
            for entry in approvals.values()),
    }
    target = paths.completion_file
    write_atomic(target, json.dumps(summary, indent=2) + "\n")
    return str(target.relative_to(paths.project_root)).replace(os.sep, "/")


def cmd_gate_approve(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    branch_guard(args, paths, state)
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

    resolved, sha = required_gate_artifact(paths, state, consts, args.gate,
                                           "approve")
    if sha:
        state.setdefault("artifact_shas", {})[args.gate] = sha

    gate_precondition_hook(paths, state, consts, args.gate, resolved)
    review_precondition(paths, state, args.gate, resolved)
    # E1's enforcement site is `apply_advance` — but this command calls it
    # *after* it has already appended the `gate_approved` entry, and an
    # append to `audit.md` cannot be undone by a later raise. Evaluate the
    # same refusals here first, with no `state`, so this call records
    # nothing and a refusal leaves the ledger byte-identical. Without it an
    # ordinary refusal writes an approval that never happened into the
    # append-only ledger and leaves `audit verify` reporting a broken chain
    # (invariants 5 and 6). `apply_advance` still enforces; this only moves
    # the failure to before the first irreversible write.
    governance_precondition(paths)
    flow_precondition(paths, state)
    discovery_precondition(paths, state)
    impact_analysis_precondition(paths, state)
    revalidate_recorded_omissions(paths, state, consts, args.gate)

    state.setdefault("approvals", {})[args.gate] = {
        "decision": "approved",
        "comments": args.comments,
        "timestamp": stamp,
    }
    flow = flow_for_state(state, consts)
    number = flow.gate_number(args.gate)
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

    is_final = flow.next_phase(gate_phase) == "complete"
    moved = apply_advance(paths, state, consts, "complete" if is_final
                          else flow.next_phase(gate_phase),
                          "completed" if is_final else None, "approved")

    summary_path = None
    baseline_path = baseline_sha = None
    if is_final:
        # §14 — the repository baseline is established FIRST in this branch,
        # before the completion summary and before `workflow_complete`, so an
        # I/O failure produces the same failure shape `write_completion_summary`
        # already has today rather than a new one. The call cannot refuse.
        baseline_path, baseline_sha = establish_baseline(
            paths, state, consts, stamp)
        summary_path = write_completion_summary(paths, state)
        append_audit(
            paths,
            state,
            phase="complete",
            event="workflow_complete",
            message=f"Gate {number}/{flow.gate_total} (security) approved. "
            "Workflow complete. Completion summary written.",
            artifact=summary_path,
        )
        if baseline_path:
            append_audit(
                paths,
                state,
                phase="complete",
                event=BASELINE_AUDIT_EVENT,
                message=(
                    f"Repository baseline established from {flow.name} "
                    f"completion: {baseline_path}. Later WorkItems converge "
                    "onto ITERATIVE against it instead of rediscovering the "
                    "repository."
                ),
                artifact=baseline_path,
                artifact_sha=baseline_sha,
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
            # `null` for every non-final approval and for a completing flow
            # that establishes no baseline; §14's convergence artifact
            # otherwise. Reported so the orchestrator can show it without
            # reading the repository configuration boundary itself.
            "baseline": baseline_path,
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

    resolved, sha = required_gate_artifact(paths, state, consts, gate_key,
                                           "re-approve")
    review_precondition(paths, state, gate_key, resolved)
    if sha:
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
            state["progress"] = flow_for_state(state, consts).progress_for(resumed)
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


def cmd_gate_omit(args, paths: Paths) -> int:
    """Pass a gate the effective policy does not require a human to approve.

    §15's exit criterion is that design and security are *"neither
    universally mandatory nor casually skippable"*. This command is the whole
    of the first half, and its refusal stack is the whole of the second.

    "Not required" means **omittable, not omitted**. An omittable gate can
    still be approved by a human exactly as before — always permitted,
    because approving is always stricter than the policy demands. What it can
    never be is passed silently: an omission is an explicit, audited event,
    because §15 requires every omitted gate to be explainable and auditable
    and an automatic omission produces no event to explain.

    The refusal stack mirrors `cmd_gate_approve`'s, in the same order, with
    `gate_required` inserted. That refusal is what makes the phase safe:
    Claude may *ask* to omit and be told no, and there is no flag, override or
    reason string that changes the answer. Nothing here relaxes TP-011 — a
    governed artifact must still hold a current PASS review — and nothing
    here skips the artifact SHA baseline, because a gate is a decision about
    specific content whether the decision is "approve" or "omit".
    """
    consts = load_constants(paths)
    state = read_state(paths)
    branch_guard(args, paths, state)
    stamp = now_iso()

    if state.get("drift_queue"):
        raise Refused(
            "drift_pending",
            "Artifact drift is pending re-approval, and an omission cannot "
            "jump that queue. Re-approve "
            f"{(state.get('drift_queue') or ['?'])[0]} first.",
            {"drift_queue": state.get("drift_queue") or [],
             "gate": args.gate},
        )

    gate_phase = require_gate(consts, args.gate)
    if state.get("current_phase") != gate_phase:
        raise Refused(
            "not_at_gate",
            f"Cannot omit {args.gate}: the workflow is at "
            f"{state.get('current_phase')}, not {gate_phase}.",
            {"gate": args.gate, "current_phase": state.get("current_phase")},
        )

    # The requirement model, derived now rather than read from anywhere. The
    # one remaining way it can be underivable is a refusal, because an
    # omission nobody can justify is not one the engine will take. T11 deleted
    # the second (the legacy binding) with the rung itself: `cmd_gate_omit` is
    # reached only through `main()`'s `bind_workitem`, which after R2 never
    # returns an unbound `Paths`.
    governance_record = read_governance_record(paths)
    if governance_record is None:
        raise Refused(
            "governance_missing",
            f"WorkItem '{paths.workitem}' has no governance record, so no "
            "gate can be shown to be unnecessary. Run `governance assess "
            "--input <path>` first.",
            {"workitem": paths.workitem, "path": str(paths.governance_file)},
        )
    # T11 D11: if the level this omission rests on was reached by lowering an
    # earlier one, the omission evidence says so. §15 wants an omitted gate
    # explainable; "the policy did not require it" is only half an
    # explanation when the input to the policy moved.
    downgrade = governance_record.get("downgrade")
    # T11 N13: §15 requires an omitted gate to be explainable *later*, from
    # what was written down. The policy sha said which rules applied; this
    # says which governance record supplied the level they were applied to.
    governance_sha = (sha256_file(paths.governance_file)
                      if paths.governance_file.is_file() else None)
    model = gate_requirements_for_state(paths, consts, state)
    disposition = next(
        (entry for entry in (model or {}).get("dispositions") or []
         if entry["gate"] == args.gate), None)
    # No disposition means the bound flow does not contain this gate, which is
    # not a licence to omit it — it is a state nothing should be able to
    # reach while standing at that gate's phase. Refused, like every other
    # case the engine cannot justify.
    if disposition is None or disposition["disposition"] != "omittable":
        reasons = [] if disposition is None else disposition["reasons"]
        raise Refused(
            "gate_required",
            f"{args.gate} requires a human approval and cannot be omitted "
            f"(reasons: {', '.join(reasons) or 'not a gate of this flow'}; "
            f"final risk {(model or {}).get('final_risk')}; policy "
            f"{((model or {}).get('policy') or {}).get('source')}). Approve "
            "it, or reject it — a required gate has no third option.",
            {"gate": args.gate, "phase": gate_phase,
             "final_risk": (model or {}).get("final_risk"),
             "reasons": reasons,
             "required_gates": (model or {}).get("required_gates"),
             "omittable_gates": (model or {}).get("omittable_gates"),
             "policy": (model or {}).get("policy")},
        )

    resolved, sha = required_gate_artifact(paths, state, consts, args.gate,
                                           "omit")
    if sha:
        state.setdefault("artifact_shas", {})[args.gate] = sha

    gate_precondition_hook(paths, state, consts, args.gate, resolved)
    review_precondition(paths, state, args.gate, resolved)
    # The same pure-reader block `cmd_gate_approve` uses, and for the same
    # reason: every refusal above and here happens before the first
    # `append_audit`, so a refused omission leaves the ledger byte-identical.
    governance_precondition(paths)
    flow_precondition(paths, state)
    discovery_precondition(paths, state)
    impact_analysis_precondition(paths, state)

    state.setdefault("approvals", {})[args.gate] = {
        "decision": GATE_OMITTED_DECISION,
        "comments": None,
        "timestamp": stamp,
        # The context that made the omission admissible, recorded so it can be
        # audited later without re-running anything. `reasons` is the gate's
        # REQUIREMENT reason list, which is empty precisely because nothing
        # required it — that emptiness is the justification.
        "risk_level": model["final_risk"],
        "reasons": disposition["reasons"],
        "policy_sha256": model["policy"]["sha256"],
        # T11 N13. The record the level was read from, fingerprinted, so a
        # later reader can tell whether it is still the record on disk.
        "governance_sha256": governance_sha,
        # T11 D11. `null` for the ordinary case; the whole block when the
        # governing level was reached by lowering an earlier one.
        "governance_downgrade": downgrade,
    }

    flow = flow_for_state(state, consts)
    number = flow.gate_number(args.gate)
    append_audit(
        paths,
        state,
        phase=gate_phase,
        event="gate_omitted",
        message=f"Gate {number} omitted: the governance policy in effect "
        f"({model['policy']['source']}) requires no human approval for "
        f"{args.gate} at final risk {model['final_risk']} on the "
        f"{flow.name} flow. No human approved this gate. The artifact was "
        "still generated, registered and reviewed, and its baseline SHA is "
        f"recorded: {sha or 'n/a'}."
        + ("" if not isinstance(downgrade, dict) else
           " NOTE: the governance record this rests on LOWERED the final risk "
           f"level from {downgrade.get('from')} to {downgrade.get('to')} "
           f"(see the {GOVERNANCE_DOWNGRADE_EVENT} entry for execution "
           f"{downgrade.get('fromExecutionId')})."),
        artifact=resolved,
        artifact_sha=sha,
        decision="OMITTED",
    )

    # The terminal gate of the bound flow is always required, so this can
    # never be the final advance and can never reach the completion or
    # baseline branch. Asserted, not assumed.
    moved = apply_advance(paths, state, consts, flow.next_phase(gate_phase),
                          None, GATE_OMITTED_DECISION)
    save_state(paths, state, args.session)
    emit(
        "gate omit",
        {
            "gate": args.gate,
            "sha": sha,
            "decision": GATE_OMITTED_DECISION,
            "final_risk": model["final_risk"],
            "reasons": disposition["reasons"],
            "policy": model["policy"],
            "governance_sha256": governance_sha,
            "governance_downgrade": downgrade,
            "next_phase": moved["to"],
            "status": moved["status"],
            "progress": moved["progress"],
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
        message=f"Gate {flow_for_state(state, consts).gate_number(args.gate)} "
        "rejected. "
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
        # §15 preserve item 1. An omitted gate is a BASELINED gate: its
        # artifact was fingerprinted at the moment of the decision exactly as
        # an approved one is, so it keeps drift protection. Filtering on
        # "approved" alone would let an omitted gate's artifact change
        # afterwards with nothing raised — a real regression wearing the
        # disguise of no change.
        if (not isinstance(entry, dict)
                or entry.get("decision") not in BASELINED_GATE_DECISIONS):
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
    branch_guard(args, paths, state)
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


# --------------------------------------------------------------------------
# Spec Kit capability detection (contract §10)
#
# The repository pins no Spec Kit version and installs from a moving Git HEAD,
# so what a given installation supports cannot be known at design time. §10's
# rule is "capability-detect; do not hardcode undocumented internals": SDLE
# probes the *target project's own* installation for the documented,
# user-facing environment variables by name. It never executes Spec Kit and
# never reads one of its internal data structures.
# --------------------------------------------------------------------------

SPECKIT_REQUIRED_CAPABILITIES = ("SPECIFY_INIT_DIR", "SPECIFY_FEATURE_DIRECTORY")
SPECKIT_PROBE_SUFFIXES = (".py", ".sh", ".ps1")
SPECKIT_SCRIPTS_RELATIVE = ".specify/scripts"


def repo_relative(paths: Paths, target: Path) -> str:
    """``target`` as a repo-relative POSIX path. Emitted paths use ``/``."""
    return str(target.relative_to(paths.project_root)).replace(os.sep, "/")


def detect_speckit_capabilities(paths: Paths) -> dict:
    """Report which required Spec Kit capabilities this installation supports.

    A capability is ``supported`` iff its literal environment-variable name
    occurs in at least one script Spec Kit itself placed under
    ``.specify/scripts/``. The first file that names it is recorded as
    ``evidence`` so a human can check the finding rather than trust it.

    The failure direction is deliberately **closed**: an installation that
    honours a variable without shipping a script naming it is reported
    unsupported and `feature bind` refuses. That false negative is accepted and
    declared — the other direction would have SDLE proceed on an assumption.
    """
    speckit_root = paths.project_root / ".specify"
    scripts_root = speckit_root / "scripts"
    capabilities = {
        name: {"supported": False, "evidence": None}
        for name in SPECKIT_REQUIRED_CAPABILITIES
    }

    if scripts_root.is_dir():
        candidates = sorted(
            p for p in scripts_root.rglob("*")
            if p.is_file() and p.suffix.lower() in SPECKIT_PROBE_SUFFIXES
        )
        for candidate in candidates:
            outstanding = [name for name in SPECKIT_REQUIRED_CAPABILITIES
                           if not capabilities[name]["supported"]]
            if not outstanding:
                break
            try:
                body = candidate.read_text(encoding="utf-8", errors="replace")
            except OSError:
                # An unreadable file proves nothing; keep the closed default.
                continue
            for name in outstanding:
                if name in body:
                    capabilities[name] = {
                        "supported": True,
                        "evidence": repo_relative(paths, candidate),
                    }

    return {
        "speckit_present": speckit_root.is_dir(),
        "scripts_present": scripts_root.is_dir(),
        "probed_root": SPECKIT_SCRIPTS_RELATIVE,
        "capabilities": capabilities,
        "missing": [name for name in SPECKIT_REQUIRED_CAPABILITIES
                    if not capabilities[name]["supported"]],
    }


# D05 (SDLE-DEFECT-STABILIZATION-01). The SpecKit release SDLE is verified
# against, and the init command as it was actually run against it — in a
# disposable project, through both script flavours — for the record in
# `docs/verification/defect-stabilization-01.md`. The earlier
# `specify init . --skills --here` is rejected by this release (`No such
# option: --skills`): the Claude integration installs skills by default.
# Pinned with `@v<version>` so a user reproduces what was tested rather than
# whatever the default branch is today; an existing installation is never
# upgraded by SDLE. README's Quick Start states the same command, and a unit
# test holds the two together.
SPECKIT_SUPPORTED_VERSION = "1.0.6"
SPECKIT_INIT_COMMAND = (
    "uvx --from git+https://github.com/github/spec-kit.git"
    f"@v{SPECKIT_SUPPORTED_VERSION} specify init --here --force "
    "--non-interactive --integration claude --script sh"
)

SPECKIT_MISSING_MESSAGE = (
    "SDLE requires SpecKit to be initialized in this project. Run: "
    f"{SPECKIT_INIT_COMMAND} (use `--script ps` for PowerShell scripts)."
)


def speckit_env(paths: Paths, state: dict) -> list[dict]:
    """The environment assignments, ordered, as objects — never a shell string.

    The prompt layer quotes for its own platform; emitting ``A=b B=c`` here
    would bake one shell's quoting rules into the engine.
    """
    ref = speckit_ref(state)
    env = [{"name": "SPECIFY_INIT_DIR", "value": str(paths.project_root)}]
    if ref["featureDirectory"]:
        env.append({"name": "SPECIFY_FEATURE_DIRECTORY",
                    "value": ref["featureDirectory"]})
    if ref["featureId"]:
        env.append({"name": "SPECIFY_FEATURE", "value": ref["featureId"]})
    return env


def cmd_feature_bind(args, paths: Paths) -> int:
    """Re-assert this WorkItem's Spec Kit context before every invocation.

    **Pure.** It reads state and the filesystem and writes nothing: no state,
    no audit, no file under ``.specify/``. Spec Kit keeps exactly one
    repository-global feature slot, so a stale one could otherwise hand this
    WorkItem another's directory; re-asserting the environment at every
    invocation — together with the gate precondition, which a hook cannot
    bypass — is what closes that.

    `feature` is deliberately absent from RUNTIME_FREE_COMMANDS, so
    ``bind_workitem`` has already run by the time this handler is entered:
    WorkItem resolution structurally precedes anything Spec Kit-related.
    """
    detected = detect_speckit_capabilities(paths)
    if not detected["speckit_present"]:
        raise Refused(
            "speckit_missing", SPECKIT_MISSING_MESSAGE,
            {"path": str(paths.project_root / ".specify"),
             "probed_root": detected["probed_root"]},
        )
    if detected["missing"]:
        raise Refused(
            "speckit_capability_missing",
            "The SpecKit installed in this project does not support "
            f"{', '.join(detected['missing'])} — SDLE needs it to scope a "
            f"feature to this WorkItem, and will not guess. Probed "
            f"{detected['probed_root']}/. Re-initialize SpecKit with a "
            "version that supports it.",
            {
                "missing": detected["missing"],
                "probed_root": detected["probed_root"],
                "capabilities": detected["capabilities"],
            },
        )

    # A project with no runtime yet still gets a usable binding: `specKit`
    # simply reads as all-null, and --require-feature is what refuses.
    state = read_state(paths) if paths.state_file.is_file() else {}
    ref = speckit_ref(state)
    if getattr(args, "require_feature", False) and not ref["featureDirectory"]:
        raise Refused(
            "feature_directory_unresolved",
            "No feature directory is recorded for this WorkItem yet. Run "
            "`feature resolve` after the specification step.",
            {"workitem": paths.workitem,
             "specs_root": paths.speckit_specs_relative},
        )

    emit("feature bind", {
        "workitem": paths.workitem,
        "feature_id": ref["featureId"],
        "feature_directory": ref["featureDirectory"],
        "workitem_specs_root": paths.speckit_specs_relative,
        "env": speckit_env(paths, state),
        "capabilities": detected["capabilities"],
    })
    return EXIT_OK


def cmd_feature_capabilities(args, paths: Paths) -> int:
    """Report what the installed SpecKit supports. A diagnostic: never refuses.

    Same shape as `workitem resolve` — it reports, it never picks, and the
    refusal lives at `feature bind`.
    """
    emit("feature capabilities", detect_speckit_capabilities(paths))
    return EXIT_OK


def _feature_candidates(directory: Path) -> list[Path]:
    """Feature directories in one tier, in a stable order.

    **T11 D10** removed the newest-mtime *selection* (T04 N-2), so this order
    no longer picks a winner — it only makes the refusal's candidate list
    deterministic. Sorted by name for exactly that reason: two directories
    created in the same second have no meaningful mtime order, and an order
    that decides nothing should not pretend to rank.
    """
    if not directory.is_dir():
        return []
    return sorted((p for p in directory.glob("*") if p.is_dir()),
                  key=lambda p: p.name)


def feature_candidate_tier(paths: Paths) -> tuple[list[str], str | None,
                                                  list[Path]]:
    """The first tier that holds any feature directory, in precedence order.

    Returns ``(searched, chosen_tier, candidates)``. A pure reader, shared by
    `feature resolve` and by the gate precondition that refuses an unresolved
    feature (D01), so both give the same answer and there is one tier list.
    """
    tiers = [
        (paths.speckit_specs_relative, paths.speckit_specs_root),
        ("specs", paths.project_root / "specs"),
        (".specify/specs", paths.project_root / ".specify" / "specs"),
    ]
    searched: list[str] = []
    for label, directory in tiers:
        searched.append(label)
        found = _feature_candidates(directory)
        if found:
            return searched, label, found
    return searched, None, []


def _adopt_feature_directory(paths: Paths, source: Path, target: Path) -> dict:
    """Move a natively-created feature directory into this WorkItem.

    Bounded and non-destructive by construction: it refuses rather than
    overwrites, verifies both endpoints resolve inside the project root before
    touching anything, and leaves the source in place on any OSError. It is a
    *move*, so exactly one copy of the artifact exists at every instant — SDLE
    never duplicates a Spec Kit-owned file (contract §10, TP-005).
    """
    if target.exists():
        raise Refused(
            "feature_target_exists",
            f"{repo_relative(paths, target)} already exists. SDLE will not "
            "overwrite or merge a feature directory; move or remove it "
            "deliberately first.",
            {"from": repo_relative(paths, source),
             "to": repo_relative(paths, target)},
        )

    root = paths.project_root.resolve()
    for endpoint in (source, target):
        try:
            endpoint.resolve().relative_to(root)
        except ValueError:
            raise Refused(
                "feature_adopt_failed",
                f"{endpoint} does not resolve inside the project root. "
                "Nothing was moved.",
                {"path": str(endpoint), "project_root": str(root)},
            ) from None

    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.move(str(source), str(target))
    except OSError as exc:
        raise Refused(
            "feature_adopt_failed",
            f"Could not move {repo_relative(paths, source)} into this "
            f"WorkItem: {exc}. The source was left untouched.",
            {"from": repo_relative(paths, source),
             "to": repo_relative(paths, target), "error": str(exc)},
        ) from None

    return {"from": repo_relative(paths, source),
            "to": repo_relative(paths, target)}


def cmd_feature_resolve(args, paths: Paths) -> int:
    """Identify — and where necessary adopt — this WorkItem's feature directory.

    Candidates are collected in a **fixed tier order** and the first tier
    that yields anything is used:

      1. ``workitems/<id>/specs/*``  — already contained;
      2. ``<project-root>/specs/*``  — where Spec Kit 0.15.0 actually creates
         a feature, since it hardcodes ``repo_root/specs`` for *creation*;
      3. ``.specify/specs/*``        — where pre-v1.15 SDLE assumed it was.

    That is precedence, not a tie-break between peers, and it is why T04
    discovers the native directory instead of hardcoding a creation path no
    unpinned Spec Kit install can guarantee. Nothing under another WorkItem is
    ever a candidate: no tier reaches into ``workitems/<other-id>/``.

    Within the chosen tier there is no selection rule left to get wrong.
    **T11 D10** (T04 N-2): more than one candidate refuses `feature_ambiguous`
    and lists them. Baseline picked the newest mtime and refused only on an
    exact timestamp tie, which meant two WorkItems both standing at the
    specification phase could cross-adopt through the repository-global
    `specs/` tier — a silent wrong pick out of a shared staging area, which
    §9 ("never silently pick one among multiple plausible") and §10 ("WorkItem
    A's Spec Kit output cannot be mistaken for WorkItem B's") both forbid.
    Recency is not evidence of ownership.

    There is no override flag, because there does not need to be one: tier 1
    is `workitems/<id>/specs/`, so *moving* the directory this WorkItem owns
    into its own tier resolves the ambiguity by precedence, deterministically
    and without SDLE guessing. The refusal names that remedy.

    **T11 D1/D2** removed the legacy binding, so `speckit_specs_root` is never
    `None` here: `feature` is not `RUNTIME_FREE`, so `bind_workitem` has
    already returned a bound `Paths` (R2, pinned by N25).
    """
    state = read_state(paths)
    specs_root = paths.speckit_specs_root
    searched, chosen_tier, candidates = feature_candidate_tier(paths)

    if not candidates:
        raise Refused(
            "feature_unresolved",
            "No feature directory found under "
            + ", ".join(f"{name}/" for name in searched)
            + ". The specification step did not produce one.",
            {"searched": searched},
        )

    # T11 D10. Pure reader, and placed ahead of every write below, so a
    # refused `feature resolve` leaves state.json and audit.md untouched.
    if len(candidates) > 1:
        names = sorted(p.name for p in candidates)
        raise Refused(
            "feature_ambiguous",
            f"{len(names)} feature directories under {chosen_tier}/: "
            + ", ".join(names)
            + ". SDLE will not choose between them — recency is not evidence "
            "of ownership, and a directory under a shared tier may belong to "
            f"another WorkItem entirely. Move the one '{paths.workitem}' owns "
            f"into {paths.speckit_specs_relative}/, which takes precedence "
            "over every shared tier, or remove the others.",
            {"candidates": names, "searched": searched, "tier": chosen_tier,
             "workitem": paths.workitem,
             "remedy_tier": paths.speckit_specs_relative},
        )

    source = candidates[0]
    chosen = source.name
    adopted = None
    target = specs_root / chosen
    if source != target:
        adopted = _adopt_feature_directory(paths, source, target)
    directory = f"{paths.speckit_specs_relative}/{chosen}"

    if adopted is not None:
        append_audit(
            paths, state, phase=state.get("current_phase") or "unknown",
            event="speckit_feature_adopted",
            message=f"Feature directory adopted into this WorkItem: "
                    f"{adopted['from']} -> {adopted['to']}.",
            artifact=adopted["to"],
        )

    speckit_set(state, featureId=chosen, featureDirectory=directory)
    save_state(paths, state, args.session)
    emit(
        "feature resolve",
        {
            "feature_id": chosen,
            "feature_directory": directory,
            "candidates": [p.name for p in candidates],
            "searched": searched,
            "tier": chosen_tier,
            "adopted": adopted,
        },
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


# **D02 (SDLE-DEFECT-STABILIZATION-01).** Gate 7's verification evidence.
#
# `manifest build` writes one structured record per build beside the manifest
# and names it from a line in the manifest. Gate 7 reads it back and binds it
# to the exact manifest bytes, the pinned implementation base and the bound
# WorkItem, then requires a runner that actually ran and exited 0. The prose
# statuses are unchanged; what changed is that one of them is now required.
IMPLEMENTATION_EVIDENCE_KIND = "implementation"
MANIFEST_EVIDENCE_LINE = re.compile(r"^Evidence: (\S+)\s*$", re.MULTILINE)
TEST_STATUS_PASSED = "passed"
TEST_STATUS_FAILED = "FAILED"
TEST_STATUSES = (TEST_STATUS_PASSED, TEST_STATUS_FAILED, "no runner detected",
                 "runner not installed", "skipped by caller")
REBUILD_HINT = (
    "Rebuild it with `manifest build`, adding `--test-command \"<command>\"` "
    "when the project's test runner is not auto-detected."
)


def _implementation_evidence_shape(document: object) -> str | None:
    """Why ``document`` cannot be read as implementation evidence, or None."""
    if not isinstance(document, dict):
        return "the evidence is not a JSON object"
    if document.get("kind") != IMPLEMENTATION_EVIDENCE_KIND:
        return f"kind is {document.get('kind')!r}, not implementation evidence"
    for field_name in ("workitem", "manifestSha256", "executionId"):
        if not isinstance(document.get(field_name), str):
            return f"{field_name} is missing or not a string"
    if "baseRef" not in document or not (
            document["baseRef"] is None or isinstance(document["baseRef"], str)):
        return "baseRef is missing or not a string"
    tests = document.get("tests")
    if not isinstance(tests, dict):
        return "the tests block is missing"
    status, code = tests.get("status"), tests.get("exit_code")
    if not isinstance(status, str) or not (
            status in TEST_STATUSES or status.startswith("timed out after ")):
        return f"test status {status!r} is not one SDLE records"
    if code is not None and (isinstance(code, bool) or not isinstance(code, int)):
        return f"exit_code {code!r} is not an integer"
    if status == TEST_STATUS_PASSED and code != 0:
        return f"status says passed but the exit code is {code!r}"
    if status == TEST_STATUS_FAILED and code in (0, None):
        return f"status says FAILED but the exit code is {code!r}"
    return None


def implementation_evidence_precondition(paths: Paths, state: dict,
                                         gate_key: str, resolved: str,
                                         body: str) -> None:
    """Gate 7 requires evidence of a passing test run for *this* manifest."""
    match = MANIFEST_EVIDENCE_LINE.search(body)
    if not match:
        raise Refused(
            "test_evidence_missing",
            f"Cannot approve {gate_key}: {resolved} names no verification "
            "evidence. A manifest in this form — written by hand, or built "
            "before SDLE recorded evidence — cannot establish that the tests "
            f"ran, let alone passed. {REBUILD_HINT}",
            {"gate": gate_key, "path": resolved},
        )
    relative = match.group(1)
    target = paths.project_root / relative
    try:
        target.resolve().relative_to(paths.evidence_dir.resolve())
    except ValueError:
        raise Refused(
            "test_evidence_stale",
            f"Cannot approve {gate_key}: {resolved} points at {relative}, "
            "which is not this WorkItem's evidence. Evidence from another "
            f"WorkItem or location never approves this one. {REBUILD_HINT}",
            {"gate": gate_key, "path": resolved, "evidence": relative,
             "mismatch": "location"},
        ) from None
    if not target.is_file():
        raise Refused(
            "test_evidence_missing",
            f"Cannot approve {gate_key}: the evidence {resolved} names, "
            f"{relative}, does not exist. {REBUILD_HINT}",
            {"gate": gate_key, "path": resolved, "evidence": relative},
        )
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        document, problem = None, f"it cannot be read as JSON ({exc})"
    else:
        problem = _implementation_evidence_shape(document)
    if problem:
        raise Refused(
            "test_evidence_malformed",
            f"Cannot approve {gate_key}: {relative} is not usable evidence: "
            f"{problem}. {REBUILD_HINT}",
            {"gate": gate_key, "evidence": relative, "problem": problem},
        )

    for field_name, expected in (
        ("workitem", paths.workitem),
        ("manifestSha256", sha256_file(paths.project_root / resolved)),
        ("baseRef", state.get("implementation_base_ref")),
    ):
        if document.get(field_name) != expected:
            raise Refused(
                "test_evidence_stale",
                f"Cannot approve {gate_key}: {relative} does not belong to "
                f"the manifest being approved ({field_name} is "
                f"{document.get(field_name)!r}, expected {expected!r}). A "
                "result for other content, another implementation base or "
                f"another WorkItem proves nothing about this one. "
                f"{REBUILD_HINT}",
                {"gate": gate_key, "evidence": relative,
                 "mismatch": field_name,
                 "recorded": document.get(field_name), "expected": expected},
            )

    tests = document["tests"]
    if tests["status"] != TEST_STATUS_PASSED or tests["exit_code"] != 0:
        raise Refused(
            "tests_not_passed",
            f"Cannot approve {gate_key}: the recorded verification result is "
            f"'{tests['status']}'"
            + (f" (exit {tests['exit_code']})"
               if tests["exit_code"] is not None else "")
            + ". Gate 7 needs a test run that actually ran and passed, and "
            "there is no exception path: a PASS review of the manifest does "
            "not change the result it reports. Fix the failures, or — if the "
            "runner was not detected or not installed — supply the project's "
            "real test command with `manifest build --test-command "
            "\"<command>\"`, then rebuild.",
            {"gate": gate_key, "evidence": relative,
             "status": tests["status"], "exit_code": tests["exit_code"],
             "runner": tests.get("runner"), "command": tests.get("command")},
        )


SPECKIT_GATE_KEYS = ("gate_spec", "gate_plan", "gate_tasks", "gate_analyze")


def gate_precondition_hook(paths: Paths, state: dict, consts: Constants,
                           gate_key: str, resolved: str | None) -> None:
    """Gate-specific refusals that must hold at the choke point.

    Gate 7 is the one gate whose artifact is machine-generated, so it is the
    one gate whose completeness can be checked mechanically. A hook can be
    skipped; this refusal cannot — an implementation whose secrets scan or
    tests never ran does not reach a human decision.

    The four Spec Kit gates carry a second such refusal. Spec Kit keeps a
    single repository-global feature slot, so a stale one can point this
    WorkItem at another's directory; a WorkItem's gate must never approve
    another WorkItem's artifact. **T11 removed the legacy-binding carve-out
    with the rung itself**, so the containment rule now applies to every
    resolvable Spec Kit gate.
    """
    if gate_key in SPECKIT_GATE_KEYS:
        if not resolved:
            return None
        directory = speckit_ref(state)["featureDirectory"]
        prefix = f"{paths.speckit_specs_relative}/"
        if not directory or not directory.startswith(prefix):
            raise Refused(
                "feature_outside_workitem",
                f"Cannot approve {gate_key}: the recorded feature directory "
                f"({directory or 'none'}) is not inside {prefix}. A "
                f"WorkItem's gate never approves another WorkItem's "
                f"artifact. Re-run `feature resolve` while bound to "
                f"'{paths.workitem}'.",
                {"gate": gate_key, "workitem": paths.workitem,
                 "feature_directory": directory, "expected_prefix": prefix},
            )
        return None

    if gate_key != "gate_implement" or not resolved:
        return None

    try:
        body = (paths.project_root / resolved).read_text(
            encoding="utf-8", errors="replace"
        )
    except OSError as exc:
        raise Refused(
            "artifact_unreadable",
            f"Cannot approve {gate_key}: {resolved} exists but cannot be read "
            f"({exc.strerror or exc}).",
            {"gate": gate_key, "path": resolved, "error": str(exc)},
        ) from None
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
    # D02: the headings prove the sections exist; this proves what the test
    # section reports is a passing run of *this* implementation.
    implementation_evidence_precondition(paths, state, gate_key, resolved,
                                         body)
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
    branch_guard(args, paths, state)
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
    "accept_audit_mismatch", "branch_mismatch",
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
    flow = flow_for_state(state, consts)
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
        f"**Gate:** "
        f"{consts.label_or(require_gate(consts, gate_key), flow)}\n"
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
    branch_guard(args, paths, state)
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
        flow = flow_for_state(state, consts)
        emit("skip", {
            "pending": True, "phase": phase,
            "label": consts.label_or(phase, flow),
            "index": flow.index(phase),
        })
        return EXIT_OK

    if state.get("pending_confirm_action") != "skip":
        raise Refused(
            "no_pending_confirmation",
            "No skip confirmation is pending. Issue `skip` first.",
            {"pending": state.get("pending_confirm_action")},
        )

    # Same reason as in `cmd_gate_approve`: this command appends to the
    # append-only ledger before it calls `apply_advance`, so any refusal
    # raised inside `apply_advance` would strand an orphan entry that
    # `state.json` never commits — the chain then re-links on the next
    # successful write and the orphan becomes permanent (invariants 5, 6).
    # Evaluating the precondition here keeps the enforcement rule itself
    # in one place; passing no `state` keeps this call a pure reader.
    governance_precondition(paths)
    flow_precondition(paths, state)
    discovery_precondition(paths, state)
    impact_analysis_precondition(paths, state)

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
    flow = flow_for_state(state, consts)
    target = flow.next_phase(phase)
    moved = apply_advance(paths, state, consts, target, "pending", "skipped")
    save_state(paths, state, args.session)
    emit("skip", {"pending": False, **moved,
                  "next_label": consts.label_or(moved["to"], flow)})
    return EXIT_OK


def cmd_restart(args, paths: Paths) -> int:
    consts = load_constants(paths)
    state = read_state(paths)
    branch_guard(args, paths, state)
    # `restart` indexes the *bound flow*, not the registry, so the number the
    # user types is the number they were shown in `Phase N/M`.
    flow = flow_for_state(state, consts)
    total = flow.phase_count  # `complete` is not restartable

    if not 1 <= args.to <= total:
        raise Refused("invalid_phase_number",
                      f"Invalid phase number. Use 1–{total}.", {"requested": args.to})

    target = flow.phase_at(args.to)
    if target in consts.phase_to_gate_key:
        raise Refused(
            "gate_phase",
            f"Phase {args.to} is a gate phase — restarting a gate is not "
            f"meaningful. Did you mean phase {args.to - 1}?",
            {"target": target, "suggest": args.to - 1},
        )

    current_index = flow.index(state.get("current_phase"))
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
        for p in flow.gate_phases
        if flow.index(p) >= args.to
    ]

    if not args.confirm:
        state["pending_confirm_action"] = f"restart:{args.to}"
        save_state(paths, state, args.session)
        emit("restart", {"pending": True, "target": target, "index": args.to,
                         "label": consts.label_or(target, flow),
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
        if flow.contains(entry.get("phase"))
        and flow.index(entry["phase"]) < args.to
    ]
    trimmed = before - len(state["phase_history"])
    state["drift_queue"] = []
    state["pending_phase"] = None
    state["phase_checkpoint"] = None
    state["current_phase"] = target
    state["status"] = "pending"
    state["progress"] = flow.progress_for(target)

    append_audit(
        paths, state, phase=target, event="restart",
        message=f"Restart: rolled back to Phase {args.to} ({target}). "
                f"Cleared downstream approvals: {', '.join(cleared) or 'none'}. "
                f"phase_history trimmed by {trimmed}.",
    )
    save_state(paths, state, args.session)
    emit("restart", {"pending": False, "target": target, "index": args.to,
                     "label": consts.label_or(target, flow),
                     "cleared_gates": cleared, "trimmed": trimmed})
    return EXIT_OK


def cmd_reset(args, paths: Paths) -> int:
    state = read_state(paths)
    branch_guard(args, paths, state)
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
    flow = flow_for_state(state, consts)

    confirmed = [
        e["phase"] for e in history
        if e.get("outcome") in {"approved", "completed"}
        and flow.contains(e.get("phase"))
    ]
    if not confirmed:
        emit("doctor", {"verdict": "ok", "reason": "no phase history yet",
                        "expected": None, "actual": current, "gap": 0})
        return EXIT_OK

    last = confirmed[-1]
    expected = flow.next_phase(last) or last
    gap = flow.index(current) - flow.index(expected)

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
        if isinstance(entry, dict)
        # Same re-pointing as `compute_drift`, for the same reason: an
        # omission carries a timestamp and a baselined artifact, so it is a
        # real reference point for "has the repository moved since?".
        and entry.get("decision") in BASELINED_GATE_DECISIONS
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

# Paths the dirty-tree guard treats as SDLE's own bookkeeping rather than the
# user's implementation. T11 D5 adds `.sdle/`, closing T08's finding: the
# repository-global configuration root is written by `config` and by
# `baseline`, both of which already produce their own audited records, so
# excluding it loses no evidence — while *not* excluding it let one WorkItem's
# `baseline.json` write trip another WorkItem's guard, which is the
# cross-WorkItem isolation §8/§9 do guarantee. `workitems/<id>/.sdle/` was
# already covered by the `workitems/` entry.
SDLE_OWNED_PREFIXES = (
    ".workflow/", ".sdle/", "workitems/", ".specify/", "design/", "reviews/",
    "clarifications/", "guidance/", "requirements/",
)


def cmd_implement_preflight(args, paths: Paths) -> int:
    state = read_state(paths)
    branch_guard(args, paths, state)

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


def run_tests(paths: Paths, timeout: int,
              command_text: str | None = None) -> dict:
    """Run the project's tests and report the outcome honestly.

    ``command_text`` is `manifest build --test-command`: the project's own
    test command, for a runner `detect_test_runner` does not know. It is run
    exactly like a detected runner — never through a shell, split with
    ``shlex`` on POSIX and handed to the C runtime's own parser on Windows —
    and its exit code is recorded the same way. It supplies evidence; it
    cannot waive the need for it (D02).
    """
    if command_text:
        name = "custom command"
        command = command_text if os.name == "nt" else shlex.split(command_text)
        display = command_text
    else:
        detected = detect_test_runner(paths)
        if not detected:
            return {"runner": None, "command": None, "exit_code": None,
                    "output": None, "status": "no runner detected"}
        name, command = detected
        display = " ".join(command)
    # `run_tests` stays one of exactly two places the engine starts a process
    # (`test_the_engine_invokes_no_agent` pins that set), so the spawn is here
    # rather than in a helper.
    try:
        completed = subprocess.run(
            command, cwd=str(paths.project_root), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=timeout,
        )
    except FileNotFoundError:
        return {"runner": name, "command": display, "exit_code": None,
                "output": None, "status": "runner not installed"}
    except subprocess.TimeoutExpired:
        return {"runner": name, "command": display, "exit_code": None,
                "output": None, "status": f"timed out after {timeout}s"}
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    tail = "\n".join(output.splitlines()[-40:])
    return {
        "runner": name,
        "command": display,
        "exit_code": completed.returncode,
        "output": tail,
        "status": "passed" if completed.returncode == 0 else "FAILED",
    }


def implementation_exclusions(paths: Paths, state: dict) -> list[str]:
    """Path prefixes that are engine bookkeeping, never implementation.

    One list for both consumers of the implementation change set — Gate 7's
    manifest and the security-review evidence — so they cannot disagree about
    what the implementation is (D03). It stays an explicit, narrow list and is
    deliberately **not** SDLE_OWNED_PREFIXES: that would silently drop
    requirements/ and design/ edits from the manifest. T11 D6 (T04 N-7) gave
    the manifest this relocation/ownership exclusion; before D03 the
    security-review evidence carried a narrower copy that missed the
    repository-global configuration root.
    """
    excluded = [
        paths.runtime_relative + "/",       # this WorkItem's runtime
        paths.config_root_relative + "/",   # repository-global `.sdle/`
        ".specify/",                        # Spec Kit's own tree
    ]
    feature_directory = speckit_ref(state)["featureDirectory"]
    if feature_directory:
        excluded.append(feature_directory.rstrip("/") + "/")
    return excluded


def _nul_fields(text: str) -> list[str]:
    return [field for field in text.split("\0") if field != ""]


def implementation_changes(paths: Paths, state: dict) -> list[dict]:
    """**D03.** The implementation change set, measured from the pinned base.

    ``implementation_base_ref`` is the commit `implement preflight` pinned
    before any implementation was written. Everything the implementation did
    since is the diff from that commit to the *working tree* — which covers
    changes committed after the base, staged changes and unstaged changes in
    one comparison — plus untracked files, which no diff reports. Before D03
    the manifest compared against the current ``HEAD``, so a change committed
    during implementation vanished from Gate 7 and from the secrets scan.

    Each entry is ``{path, status, old_path, binary, untracked}``; ``status``
    is git's letter (A, M, D, R, T). Paths are POSIX, de-duplicated, sorted,
    and filtered through ``implementation_exclusions``. A missing or invalid
    base is a refusal: silently measuring from somewhere else would produce a
    wrong-but-plausible change set, which is worse than none.
    """
    base = state.get("implementation_base_ref")
    if not base:
        raise Refused(
            "implementation_base_missing",
            "No implementation base is pinned for this WorkItem, so the "
            "implementation change set has nothing to be measured from. Run "
            "`implement preflight` before implementing — it pins the commit "
            "the change set is measured against — then build again.",
            {"workitem": paths.workitem},
        )
    code, _ = git(paths, "cat-file", "-e", f"{base}^{{commit}}")
    if code != 0:
        raise Refused(
            "implementation_base_invalid",
            f"The pinned implementation base {base} is not a commit in this "
            "repository (was history rewritten, or the repository replaced?). "
            "SDLE will not measure from a different commit instead. If the "
            "rewrite was deliberate, re-run `implement preflight` to pin a new "
            "base, knowing that changes before it will no longer be listed.",
            {"workitem": paths.workitem, "base_ref": base},
        )

    changes: dict[str, dict] = {}
    _, status = git(paths, "diff", "--name-status", "-z", "-M", base)
    fields = _nul_fields(status)
    index = 0
    while index < len(fields):
        letter = fields[index][:1]
        if letter in ("R", "C"):
            old, new = fields[index + 1], fields[index + 2]
            index += 3
            if letter == "C":
                changes[new] = {"path": new, "status": "A", "old_path": None}
            else:
                changes[new] = {"path": new, "status": "R", "old_path": old}
            continue
        path = fields[index + 1]
        index += 2
        changes[path] = {"path": path, "status": letter, "old_path": None}

    binary: set[str] = set()
    _, numstat = git(paths, "diff", "--numstat", "-z", "-M", base)
    records = numstat.split("\0")
    index = 0
    while index < len(records):
        record = records[index]
        if not record:
            index += 1
            continue
        added, deleted, *rest = record.split("\t", 2)
        if rest and rest[0]:
            path = rest[0]
            index += 1
        else:  # a rename: the two paths follow as their own fields
            path = records[index + 2] if index + 2 < len(records) else ""
            index += 3
        if added == "-" and deleted == "-":
            binary.add(path)

    _, untracked = git(paths, "ls-files", "--others", "--exclude-standard", "-z")
    for path in _nul_fields(untracked):
        changes.setdefault(path, {"path": path, "status": "A",
                                  "old_path": None, "untracked": True})

    excluded = implementation_exclusions(paths, state)
    result = []
    for path in sorted(changes):
        entry = changes[path]
        normal = path.replace("\\", "/")
        if any(normal.startswith(prefix) for prefix in excluded):
            continue
        entry["path"] = normal
        entry.setdefault("untracked", False)
        if entry.get("untracked"):
            entry["binary"] = _looks_binary(paths.project_root / normal)
        else:
            entry["binary"] = path in binary
        result.append(entry)
    return result


def _manifest_line(entry: dict) -> str:
    """One manifest row: git's status letter, the path, and what a reviewer
    needs to read it correctly (where a rename came from; that a file is
    binary and was therefore not scanned)."""
    path = entry["path"]
    if entry["status"] == "R" and entry.get("old_path"):
        path = f"{entry['old_path']} -> {path}"
    return f"{entry['status']} {path}" + (" (binary)" if entry["binary"]
                                          else "")


def _looks_binary(path: Path) -> bool:
    """Git's own heuristic for an untracked file: a NUL in the first 8000
    bytes. Untracked files appear in no diff, so git cannot say."""
    try:
        with path.open("rb") as handle:
            return b"\0" in handle.read(8000)
    except OSError:
        return False


def cmd_manifest_build(args, paths: Paths) -> int:
    state = read_state(paths)
    branch_guard(args, paths, state)
    relative = str(
        paths.manifest_file.relative_to(paths.project_root)
    ).replace(os.sep, "/")

    if git_available(paths):
        # D03: measured from the pinned base, committed + staged + unstaged
        # + untracked, through the one selector the security review also
        # reads. A missing or invalid base refuses rather than falling back.
        changes = implementation_changes(paths, state)
        note = None
    else:
        excluded = implementation_exclusions(paths, state)
        changes = [
            {"path": relative_path, "status": "A", "old_path": None,
             "binary": False, "untracked": True}
            for relative_path in sorted(
                str(p.relative_to(paths.project_root)).replace(os.sep, "/")
                for p in paths.project_root.rglob("*")
                if p.is_file() and p.suffix in TEXT_SUFFIXES
                and not str(p.relative_to(paths.project_root)).startswith("."))
            if not any(relative_path.startswith(prefix)
                       for prefix in excluded)
        ]
        note = "git not initialized — file list is approximate."
    changed = [entry["path"] for entry in changes]

    findings = []
    for entry in changes:
        # A deletion has no current content to scan, and a binary file has no
        # text to decode: both are listed, neither is read.
        if entry["status"] == "D" or entry["binary"]:
            continue
        name = entry["path"]
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

    if args.skip_tests:
        # Kept, and recorded as exactly what it is. Since D02 it can no longer
        # carry Gate 7: the gate refuses any result but a run that passed.
        tests = {"runner": None, "command": None, "exit_code": None,
                 "output": None, "status": "skipped by caller"}
    else:
        tests = run_tests(paths, args.test_timeout, args.test_command)

    secrets_block = "\n".join(findings) if findings else "None detected."
    if tests["runner"] is None:
        tests_block = f"No test runner detected ({tests['status']})."
    else:
        tests_block = (
            f"Runner: {tests['runner']}\n"
            + (f"Command: {tests['command']}\n" if tests.get("command") else "")
            + f"Result: {tests['status']}"
            + (f" (exit {tests['exit_code']})" if tests["exit_code"] is not None
               else "")
            + (f"\n\n```\n{tests['output']}\n```" if tests["output"] else "")
        )

    # D02: the structured record Gate 7 reads. Claimed before the manifest is
    # written so the manifest can name it; filled after, so it can carry the
    # manifest's own fingerprint and nothing can be edited in between unseen.
    stamp = now_iso()
    execution_id, evidence = reserve_evidence(
        paths, paths.evidence_dir, stamp,
        lambda eid: f"{IMPLEMENTATION_EVIDENCE_KIND}-{eid}.json")
    evidence_relative = evidence.relative_to(paths.project_root).as_posix()

    body = (
        "# Implementation Manifest\n"
        f"Generated: {stamp}\n"
        f"Evidence: {evidence_relative}\n"
        f"Phase: implement ({state.get('progress', '15/18')})\n"
        + (f"\n> {note}\n" if note else "")
        + "\n## Changed/Added Files\n"
        + ("\n".join(_manifest_line(entry) for entry in changes)
           if changes else "(none)")
        + "\n\n## Potential Secrets Detected\n"
        + secrets_block
        + "\n\n## Test Evidence\n"
        + tests_block
        + "\n\n## Summary\n"
        + (args.summary or "Implementation produced the files listed above.")
        + "\n"
    )
    write_atomic(paths.manifest_file, body)
    write_atomic(evidence, json.dumps({
        "kind": IMPLEMENTATION_EVIDENCE_KIND,
        "executionId": execution_id,
        "recordedAt": stamp,
        "workitem": paths.workitem,
        "manifest": relative,
        "manifestSha256": sha256_file(paths.manifest_file),
        "baseRef": state.get("implementation_base_ref"),
        "head": _git_value(paths, "rev-parse", "HEAD"),
        "files": changed,
        "changes": changes,
        "secrets": findings,
        "tests": {key: tests.get(key) for key in
                  ("runner", "command", "exit_code", "status", "output")},
    }, indent=2) + "\n")

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
        "path": relative, "files": changed, "changes": changes,
        "secrets": findings, "tests": tests, "evidence": evidence_relative,
        # Advisory, so the orchestrator can say *now* that Gate 7 will refuse
        # rather than letting the user discover it at the gate. Gate 7 itself
        # re-derives this from the evidence file; it never reads this flag.
        "tests_passed": (tests["status"] == TEST_STATUS_PASSED
                         and tests["exit_code"] == 0),
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

    # D03: the same change set Gate 7's manifest lists, from the same pinned
    # base. Before D03 an unpinned base silently became `HEAD~1` — a range
    # nobody chose — and this command carried its own, narrower exclusion
    # list. A missing or invalid base now refuses, exactly as the manifest
    # does, because a review of the wrong range is worse than no review.
    changes = implementation_changes(paths, state)
    # The diff is taken with the selector's own exclusions as a pathspec, so
    # it covers exactly the tracked entries of `changes` without passing every
    # path on the command line.
    excludes = [f":(exclude){prefix.rstrip('/')}"
                for prefix in implementation_exclusions(paths, state)]
    _, stat = git(paths, "diff", "--stat", "-M", base, "--", ".", *excludes)
    _, diff = git(paths, "diff", "-M", base, "--", ".", *excludes)
    # No diff shows an untracked file. They are listed so the review reads
    # them directly rather than silently missing them.
    untracked = [entry["path"] for entry in changes if entry["untracked"]]

    feature_directory = speckit_ref(state)["featureDirectory"]
    candidates = [".specify/memory/constitution.md"]
    if feature_directory:
        candidates += [
            f"{feature_directory}/{name}.md"
            for name in ("spec", "plan", "tasks")
        ]
    present = [c for c in candidates if (paths.project_root / c).is_file()]

    emit("security-review evidence", {
        "base_ref": base,
        # Always true since D03: an unpinned base is a refusal now, never a
        # fallback. Kept so a caller reading the field still reads the truth.
        "pinned": True,
        "stat": stat or None,
        "diff": diff or None,
        "changes": changes,
        "untracked": untracked,
        "artifacts": present,
    })
    return EXIT_OK


# --------------------------------------------------------------------------
# preflight
# --------------------------------------------------------------------------


def cmd_preflight(args, paths: Paths) -> int:
    root = paths.project_root
    problems = []

    # One source of truth for what SpecKit supports here: `feature bind`
    # refuses on it, `feature capabilities` reports it, preflight surfaces it.
    detected = detect_speckit_capabilities(paths)
    speckit_present = detected["speckit_present"]
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
        # Additive: preflight's own `problems` list, refusal reasons and
        # messages are unchanged. A missing capability is reported here and
        # refused at `feature bind`, not turned into a preflight refusal.
        "speckit_capabilities": detected["capabilities"],
        "speckit_capability_problems": detected["missing"],
    }

    if problems:
        messages = {
            "speckit_missing": SPECKIT_MISSING_MESSAGE,
            "speckit_skills_missing": "SDLE cannot locate SpecKit skills "
            "(looked for .claude/skills/speckit-constitution/ here and in "
            "your home directory). SpecKit's Claude integration installs "
            f"them; re-run its init: {SPECKIT_INIT_COMMAND}",
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

    # NEXT_PHASE and PHASE_LABEL_MAP are per-*registry* tables: the registry
    # is the catalogue of phases that exist, and every phase that exists has a
    # canonical successor and a label. PROGRESS_MAP is not — see below.
    seq = set(consts.phase_sequence)
    for name, keys in (
        ("NEXT_PHASE", set(consts.next_phase)),
        ("PHASE_LABEL_MAP", set(consts.phase_label)),
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

    # PROGRESS_MAP's subject is GREENFIELD, not the registry: a progress
    # fraction only means anything inside one lifecycle, and these 19 rows are
    # the GREENFIELD view. The subject is smaller but the guarantee is larger —
    # equality is still exact in both directions, the denominator check below
    # is now GREENFIELD's, and the flow checks additionally pin every value,
    # which nothing checked before.
    greenfield = consts.greenfield
    greenfield_phases = set(greenfield.phases)
    progress_keys = set(consts.progress)
    missing = sorted(greenfield_phases - progress_keys)
    extra = sorted(progress_keys - greenfield_phases)
    checks.append(
        Check(
            "phase_set_matches_progress_map",
            not missing and not extra,
            "identical to the GREENFIELD flow"
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

    # PROGRESS_MAP denominators all equal GREENFIELD's non-terminal count,
    # which is what those strings have always meant. It is no longer the
    # registry's phase count: after T07 the registry may hold phases that
    # GREENFIELD does not run.
    denominators = {
        value.split("/")[-1] for value in consts.progress.values() if "/" in value
    }
    expected_denominator = str(greenfield.phase_count)
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
    # The ordinal is optional: a phase with no GREENFIELD position has no
    # number to carry. That broadening is paid for — with interest — by
    # `execution_block_numbers_are_the_greenfield_positions` below, which pins
    # every ordinal that *is* present and was until now an unchecked restated
    # constant.
    headers = re.findall(
        r"^\*\*Phase (?:(\d+) — )?`([a-z_]+)`", exec_text, flags=re.MULTILINE)
    declared = {phase for _, phase in headers}
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

    # Block ordinals are the GREENFIELD positions, and every GREENFIELD phase's
    # block states its own. Renumbering the blocks to registry indices was
    # rejected: `modules/security-review.md` cross-references "Phase 17" and is
    # must-not-change, so the registry index and the block ordinal deliberately
    # diverge — and this check is what keeps the divergence honest.
    position = {phase: i + 1 for i, phase in enumerate(greenfield.phases)}
    numbered = {phase: int(number) for number, phase in headers if number}
    ordinal_problems = []
    for phase, number in sorted(numbered.items()):
        expected = position.get(phase)
        if expected is None:
            ordinal_problems.append(
                f"{phase} carries ordinal {number} but has no GREENFIELD "
                "position")
        elif number != expected:
            ordinal_problems.append(
                f"{phase} block says Phase {number}, GREENFIELD position "
                f"is {expected}")
    for phase in greenfield.phases:
        if phase in exempt or phase not in declared:
            continue  # absence belongs to every_phase_has_execution_block
        if phase not in numbered:
            ordinal_problems.append(
                f"{phase} is in GREENFIELD but its block carries no ordinal")
    checks.append(
        Check(
            "execution_block_numbers_are_the_greenfield_positions",
            not ordinal_problems,
            "; ".join(ordinal_problems) if ordinal_problems
            else f"all {len(numbered)} block ordinals are GREENFIELD positions",
        )
    )

    checks.extend(_check_flow_model(consts))
    checks.extend(_check_capability_map(paths, consts))
    checks.extend(_check_product_agents(paths))
    checks.extend(_check_discovery(paths, consts))
    checks.append(_check_single_state_template(paths))
    checks.append(_check_version_consistency(paths))
    checks.append(_check_migration_covers_state_fields(paths, consts))
    checks.append(_check_no_powershell(paths))
    checks.append(_check_no_hardcoded_progress(paths, consts))
    checks.extend(_check_doc_phase_tables(paths, consts))
    checks.extend(_check_doc_flow_counts(paths, consts))
    checks.extend(_check_documentation_set(paths))
    checks.extend(_check_documentation_index(paths))
    checks.append(_check_repo_config_defaults_documented(paths))
    return checks


def _check_flow_model(consts: Constants) -> list[Check]:
    """The flow model's cross-file rules.

    Deliberately *not* in ``load_constants``: that parses FLOW_PHASES without
    judging it, so a single broken row reports as the rule it actually breaks
    instead of short-circuiting every other check behind
    ``tables_wellformed``. ``Constants.flow()`` enforces the same rules at load
    time, where it refuses rather than reports.
    """
    checks: list[Check] = []
    greenfield = consts.greenfield
    flows = consts.flows

    # The declared rows plus the injected GREENFIELD are exactly the contract's
    # flow vocabulary — no missing flow, no invented one — and GREENFIELD is
    # not a declared row, because it has exactly one home in the engine.
    declared = set(consts.flow_phases)
    required = set(ENGINEERING_FLOWS)
    coverage: list[str] = []
    if DEFAULT_FLOW in declared:
        coverage.append(
            f"{DEFAULT_FLOW} must not be a FLOW_PHASES row: it is the frozen "
            "v1 lifecycle held by the engine")
    covered = declared | {DEFAULT_FLOW}
    if covered != required:
        coverage.append(
            f"missing={sorted(required - covered)} "
            f"unexpected={sorted(covered - required)}")
    checks.append(
        Check("flow_table_covers_the_required_flows", not coverage,
              "; ".join(coverage) if coverage
              else f"{len(flows)} flows: {sorted(flows)}"))

    # Every flow, GREENFIELD included, obeys the same two rules. GREENFIELD is
    # validated here too so it can never become a privileged special case.
    order_problems: list[str] = []
    floor_problems: list[str] = []
    for name in sorted(flows):
        for detail in consts.flow_order_problems(flows[name]):
            order_problems.append(f"{name}: {detail}")
        for detail in consts.flow_floor_problems(flows[name]):
            floor_problems.append(f"{name}: {detail}")
    checks.append(
        Check("every_flow_is_an_ordered_subset_of_the_registry",
              not order_problems,
              "; ".join(order_problems) if order_problems
              else f"{len(flows)} flows are ordered subsets of PHASE_SEQUENCE"))
    checks.append(
        Check("every_flow_retains_the_mandatory_phases", not floor_problems,
              "; ".join(floor_problems) if floor_problems
              else f"every flow keeps all {len(MANDATORY_FLOW_PHASES)} "
                   "mandatory phases"))

    # PROGRESS_MAP and PHASE_TO_GATE_KEY's gate-number column stop being
    # independent sources of truth and become checked derived views of
    # GREENFIELD. The *denominator* half of a progress string is owned by
    # `progress_denominator_matches_phase_count`; this check owns the position,
    # so the two together pin the whole value while each stays independently
    # provable by a fixture that breaks exactly one of them.
    derived: list[str] = []
    for phase in greenfield.phases:
        recorded = consts.progress.get(phase)
        if recorded is None:
            continue  # absence belongs to phase_set_matches_progress_map
        expected = greenfield.progress_for(phase).split("/")[0]
        if recorded.split("/")[0] != expected:
            derived.append(
                f"PROGRESS_MAP[{phase}]={recorded}, GREENFIELD position "
                f"is {expected}")
    for phase in greenfield.gate_phases:
        key = consts.phase_to_gate_key[phase]
        recorded = consts.gate_number.get(key)
        expected = greenfield.gate_number(key)
        if recorded != expected:
            derived.append(
                f"gate number for {key}={recorded}, GREENFIELD gives {expected}")
    checks.append(
        Check("progress_map_and_gate_numbers_are_the_derived_greenfield_views",
              not derived,
              "; ".join(derived) if derived
              else "PROGRESS_MAP and the gate-number column match GREENFIELD"))

    # The replacement for the one guarantee derivation used to give free: no
    # registry phase may be orphaned. A phase added to PHASE_SEQUENCE that no
    # flow names fails loudly here, instead of silently joining GREENFIELD the
    # way a derived GREENFIELD would have let it.
    used = {phase for flow in flows.values() for phase in flow.phases}
    orphans = [p for p in consts.phase_sequence if p not in used]
    checks.append(
        Check("every_registry_phase_is_used_by_some_flow", not orphans,
              f"orphaned={orphans}" if orphans
              else "every registry phase is named by at least one flow"))

    # A gate's ordinal is flow-relative, so it may not be re-hardcoded into the
    # label: HOTFIX's `gate_implement` is Gate 2, GREENFIELD's is Gate 7.
    label_problems: list[str] = []
    for phase in consts.gate_phases:
        template = consts.phase_label_template.get(phase, "")
        if GATE_NUMBER_PLACEHOLDER not in template:
            label_problems.append(
                f"{phase} label has no {GATE_NUMBER_PLACEHOLDER}")
        if re.search(r"Gate\s+\d", template):
            label_problems.append(f"{phase} label hardcodes a gate ordinal")
    checks.append(
        Check("gate_labels_are_flow_relative", not label_problems,
              "; ".join(label_problems) if label_problems
              else f"all {len(consts.gate_phases)} gate labels are "
                   "flow-relative"))
    return checks


# A capability file may point at another one. The reference is a load
# directive in prose, so it is matched as the literal path it has to be.
_CAPABILITY_REF_RE = re.compile(r"modules/[A-Za-z0-9._-]+\.md")

# The always-loaded orchestrator. Never a capability — see D1/`CAPABILITY_MAP`.
ORCHESTRATOR_FILE = "SKILL.md"


def _capability_values(consts: Constants) -> set[str]:
    """Every distinct capability path any row names."""
    return {value for values in consts.capability_map.values()
            for value in values}


def _check_capability_map(paths: Paths, consts: Constants) -> list[Check]:
    """CAPABILITY_MAP is what makes progressive loading deterministic.

    Before it, which module to read was decided from prose, turn by turn.
    These checks are what stop the table drifting away from the registry, from
    the files actually on disk, and from the lint coverage `_skill_files`
    provides — a capability the engine names but nothing lints would be the
    quiet way a split prompt layer loses its guarantees.
    """
    checks: list[Check] = []
    mapping = consts.capability_map
    registry = list(consts.phase_sequence)

    missing = [phase for phase in registry if phase not in mapping]
    unknown = sorted(set(mapping) - set(registry))
    problems = []
    if missing:
        problems.append(f"no CAPABILITY_MAP row for {missing}")
    if unknown:
        problems.append(f"rows naming phases outside the registry: {unknown}")
    checks.append(Check(
        "capability_map_covers_every_registry_phase", not problems,
        "; ".join(problems) if problems
        else f"all {len(registry)} registry phases have a row"))

    values = _capability_values(consts)
    resolved = {value: paths.skill_root / value for value in values}
    absent = sorted(v for v, target in resolved.items() if not target.is_file())
    checks.append(Check(
        "every_capability_file_exists", not absent,
        f"named by CAPABILITY_MAP but not on disk: {absent}" if absent
        else f"all {len(resolved)} named capability files exist"))

    orchestrator = sorted(
        phase for phase, row in mapping.items()
        if any(Path(value).name == ORCHESTRATOR_FILE for value in row))
    checks.append(Check(
        "capability_map_never_names_the_orchestrator", not orchestrator,
        f"{ORCHESTRATOR_FILE} is named as a capability by {orchestrator}"
        if orchestrator
        else f"{ORCHESTRATOR_FILE} is the always-loaded orchestrator, never "
             "a capability"))

    linted = {path.resolve() for path in _skill_files(paths)}
    unlinted = sorted(v for v, target in resolved.items()
                      if target.is_file() and target.resolve() not in linted)
    on_disk = (sorted(p.name for p in paths.modules_dir.glob("*.md")
                      if p.is_file()) if paths.modules_dir.is_dir() else [])
    named = {Path(value).name for value in values}
    orphans = [name for name in on_disk if name not in named]
    coverage = []
    if unlinted:
        coverage.append(f"capabilities outside the linted file set: {unlinted}")
    if orphans:
        coverage.append(f"modules/ files no row names: {orphans}")
    checks.append(Check(
        "every_capability_file_is_linted", not coverage,
        "; ".join(coverage) if coverage
        else f"{len(resolved)} capability files, all linted, no orphan module"))

    saturated = sorted(phase for phase, row in mapping.items()
                       if set(row) == values)
    checks.append(Check(
        "every_row_is_a_strict_subset_of_the_capability_set", not saturated,
        f"{saturated} require the entire capability set, so loading is not "
        "progressive" if saturated
        else f"every row is a strict subset of the {len(values)} capabilities"))

    dangling = []
    for value in sorted(resolved):
        target = resolved[value]
        if not target.is_file():
            continue  # `every_capability_file_exists` owns that failure
        for ref in sorted(set(_CAPABILITY_REF_RE.findall(
                target.read_text(encoding="utf-8")))):
            if not (paths.skill_root / ref).is_file():
                dangling.append(f"{value} -> {ref} does not exist")
            elif ref not in values:
                dangling.append(f"{value} -> {ref} is in no CAPABILITY_MAP row")
    checks.append(Check(
        "capability_cross_references_are_mapped_files", not dangling,
        "; ".join(dangling) if dangling
        else "every capability cross-reference resolves and is itself mapped"))
    return checks


# The product subagent boundary, as constants rather than as prose. Contract
# §16 says a subagent may inspect, reason and produce findings, and MUST NOT
# mutate lifecycle state, approve a human gate, bypass deterministic policy or
# become an independent workflow controller. Every one of those four is denied
# by taking away the tools that would perform it.
PRODUCT_AGENT_TOOLS = ("Read", "Grep", "Glob")
FORBIDDEN_AGENT_TOOLS = ("Bash", "Write", "Edit", "MultiEdit", "NotebookEdit",
                         "Agent", "Task")
# The tools the frontmatter fence must match. `Bash` is on the list because a
# shell is all it takes to run `gate approve`.
FENCED_AGENT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash")
PRODUCT_AGENT_FENCE = "hooks.py product-agent-fence"
PRODUCT_AGENT_NON_APPROVAL_CLAUSE = (
    "This subagent inspects and reports. It never mutates lifecycle state, "
    "never runs `gate approve`, `gate omit` or `advance`, and never decides "
    "a gate — human approval gates stay in the parent Claude session."
)

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.DOTALL)
_AGENT_TOOLS_RE = re.compile(r"^tools:[ \t]*(.+)$", re.MULTILINE)
_AGENT_MATCHER_RE = re.compile(r'^\s*-\s*matcher:\s*"([^"]*)"', re.MULTILINE)


def agent_frontmatter(body: str) -> str:
    """The frontmatter block of an agent file, as text. Empty when absent.

    Read with two narrow regexes rather than parsed: the engine has been
    standard-library only since v1.13 and §11's policy-format decision
    explicitly refuses a hand-rolled YAML parser. One line, one shape — and a
    file that does not match declares nothing, which *fails* the checks below
    rather than passing them.
    """
    match = _FRONTMATTER_RE.match(body)
    return match.group(1) if match else ""


def agent_tools(front: str) -> list[str]:
    """The declared tool grant, in declaration order."""
    match = _AGENT_TOOLS_RE.search(front)
    if match is None:
        return []
    return [tool.strip() for tool in match.group(1).split(",") if tool.strip()]


def _check_product_agents(paths: Paths) -> list[Check]:
    """The product subagent boundary, machine-checked instead of promised.

    What these checks do and do not guarantee is worth stating exactly,
    because named specialist agents look like more enforcement than they are:

    * **SDLE guarantees** that a declaration cannot be weakened without CI
      saying so — a widened grant, a stripped fence or a missing non-approval
      clause each fails a check here, by name.
    * **Claude Code**, not SDLE, guarantees that a declared `tools:` list is
      actually applied and that a frontmatter `PreToolUse` hook actually
      fires. The engine cannot assert either from inside the suite.
    * Nothing at all guarantees that the parent delegates to the right agent,
      or that `--actor-name` truthfully names who produced a finding. Those
      are convention, and they predate T10.

    Emitted only when product agent files exist, mirroring the documentation
    checks' tolerance of a project with no README.md — an installed skill need
    not ship agents. Tolerating absence is precisely how a check stops meaning
    anything, so it is paid for twice: the lint fixture copies the directory,
    and a repository-level test asserts the four are really there.
    """
    agents = product_agent_files(paths)
    if not agents:
        return []
    bodies = {path: path.read_text(encoding="utf-8") for path in agents}

    over = []
    for path in agents:
        granted = agent_tools(agent_frontmatter(bodies[path]))
        if not granted:
            over.append(f"{path.name} declares no `tools:` grant")
            continue
        extra = [tool for tool in granted if tool not in PRODUCT_AGENT_TOOLS]
        if extra:
            over.append(f"{path.name} grants {extra}")
    checks = [Check(
        "product_agents_are_read_only", not over,
        "; ".join(over) + f"; a product subagent may grant only "
        f"{list(PRODUCT_AGENT_TOOLS)} — each of "
        f"{list(FORBIDDEN_AGENT_TOOLS)} is a way to mutate state, approve a "
        "gate or spawn a further agent" if over
        else f"all {len(agents)} product agents grant only "
             f"{list(PRODUCT_AGENT_TOOLS)}")]

    unfenced = []
    for path in agents:
        front = agent_frontmatter(bodies[path])
        if PRODUCT_AGENT_FENCE not in front:
            unfenced.append(f"{path.name} registers no {PRODUCT_AGENT_FENCE}")
            continue
        covered = " ".join(_AGENT_MATCHER_RE.findall(front))
        gaps = [tool for tool in FENCED_AGENT_TOOLS if tool not in covered]
        if gaps:
            unfenced.append(f"{path.name} fence matcher misses {gaps}")
    checks.append(Check(
        "product_agents_declare_the_fence", not unfenced,
        "; ".join(unfenced) if unfenced
        else f"all {len(agents)} product agents fence "
             f"{list(FENCED_AGENT_TOOLS)}"))

    silent = [path.name for path in agents
              if PRODUCT_AGENT_NON_APPROVAL_CLAUSE not in bodies[path]]
    checks.append(Check(
        "product_agents_declare_the_non_approval_clause", not silent,
        f"{silent} do not carry the invariant-8 clause verbatim" if silent
        else f"all {len(agents)} product agents carry the invariant-8 clause"))
    return checks


def _check_discovery(paths: Paths, consts: Constants) -> list[Check]:
    """T08's cross-file rules for the `discovery` registry phase.

    Three decisions ADR-005 pins, each turned into a named failure so a later
    edit that reverses one has to do it visibly.
    """
    checks: list[Check] = []

    # 1. Gateless, following `impact_analysis` (ADR-004 §2, ADR-005 D1). A
    #    gate here would cost a PHASE_TO_GATE_KEY row, an ARTIFACT_OWNERSHIP
    #    row, a GATE_TO_EXECUTION_PHASE row and a ninth `approvals` key —
    #    therefore a schema migration — and would make gate numbering
    #    conditional on flow for every flow. The key is *derived* rather than
    #    spelled, so this check cannot itself be what introduces one.
    gate_key = f"gate_{DISCOVERY_PHASE}"
    gate_problems: list[str] = []
    if DISCOVERY_PHASE in consts.phase_to_gate_key:
        gate_problems.append(f"{DISCOVERY_PHASE} has a PHASE_TO_GATE_KEY row")
    if gate_key in set(consts.phase_to_gate_key.values()):
        gate_problems.append(f"{gate_key} is a registered gate key")
    if gate_key in consts.artifact_ownership:
        gate_problems.append(f"{gate_key} has an ARTIFACT_OWNERSHIP row")
    if gate_key in consts.gate_to_execution_phase:
        gate_problems.append(f"{gate_key} has a GATE_TO_EXECUTION_PHASE row")
    if DISCOVERY_PHASE in consts.progress:
        gate_problems.append(
            f"{DISCOVERY_PHASE} has a PROGRESS_MAP row, and PROGRESS_MAP is "
            "the GREENFIELD view")
    checks.append(
        Check("discovery_is_gateless", not gate_problems,
              "; ".join(gate_problems) if gate_problems
              else "no gate machinery names the discovery phase"))

    # 2. It belongs to one flow. Putting it in the mandatory floor, or in a
    #    second flow, is the opposite of §14's intent: discovery happens once
    #    and every later WorkItem converges onto ITERATIVE.
    expected = ["BROWNFIELD_DISCOVERY"]
    carriers = sorted(name for name, flow in consts.flows.items()
                      if DISCOVERY_PHASE in flow.phases)
    checks.append(
        Check("discovery_is_declared_by_exactly_one_flow", carriers == expected,
              f"carried by {carriers}, expected {expected}"
              if carriers != expected
              else "BROWNFIELD_DISCOVERY is its only carrier"))

    # 3. One home per fact (invariant 7). The §14 vocabulary reaches the
    #    prompt layer through `discovery schema` and is restated nowhere.
    #    Deliberately not every category id: five of the fourteen are ordinary
    #    English words the prompt files already use as prose, so searching for
    #    them would prove nothing. The machine-readable part is the drift
    #    surface, and that is what is searched.
    needles = (tuple(c for c in DISCOVERY_CATEGORIES if "_" in c)
               + DISCOVERY_CLASSIFICATIONS
               + (DISCOVERY_INPUT_SECTIONS[0],))
    restated = []
    for path in _skill_files(paths):
        body = path.read_text(encoding="utf-8")
        restated.extend(f"{path.name}:{n}" for n in needles if n in body)
    checks.append(
        Check("discovery_vocabulary_is_not_restated_in_prompt_files",
              not restated,
              f"restated {sorted(restated)}" if restated
              else f"none of the {len(needles)} vocabulary identifiers "
                   "appears in a prompt file"))
    return checks


REPO_DOCS = ("README.md", "docs/SDLE-Reference-Guide.md")

# Every document that states a flow's phase or gate count in a table row or a
# headline. The counts are a *derived view* of the engine and drifted once
# already: `docs/lifecycle/README.md` counted the terminal `complete` while the
# tutorials, START-HERE, README and the Reference Guide did not, so the
# document named "the lifecycle" contradicted the other five. Listing the files
# here and checking them is the repo's standing answer to that class of bug --
# a checklist rots, a lint rule does not.
FLOW_COUNT_DOCS = (
    "README.md",
    "docs/START-HERE.md",
    "docs/SDLE-Reference-Guide.md",
    "docs/lifecycle/README.md",
    "docs/tutorials/README.md",
    "docs/dry-runs/README.md",
)

# A tutorial opens by naming its own flow's size, and the flow it covers is not
# recoverable from the sentence itself, so the binding is declared.
FLOW_HEADLINE_DOCS = {
    "docs/tutorials/greenfield.md": "GREENFIELD",
    "docs/tutorials/greenfield-full-tour.md": "GREENFIELD",
    "docs/tutorials/brownfield-discovery.md": "BROWNFIELD_DISCOVERY",
    "docs/tutorials/iterative.md": "ITERATIVE",
    "docs/tutorials/defect-fix.md": "DEFECT_FIX",
    "docs/tutorials/hotfix.md": "HOTFIX",
}

# T11 D16. Transition contract §17 "Documentation" names nine targets that the
# V1 documentation set must cover. A checklist in a plan rots; a lint rule does
# not, so the list lives here and is checked, not remembered. A trailing "/"
# means a directory that must hold at least one non-empty `.md`.
DOCUMENTATION_TARGETS = (
    "README.md",
    "CLAUDE.md",
    "docs/architecture/",
    "docs/workitems/",
    "docs/lifecycle/",
    "docs/risk-and-gates/",
    "docs/brownfield/",
    "docs/spec-kit-integration/",
    "docs/troubleshooting/",
)


# `.claude/agents/` holds the product agent prompts. They are part of the
# shipped prompt layer and are linted like any other prompt file.
#
# Until the post-migration cleanup the directory held a second population: the
# `sdle-transition-*` control plane, the migration scaffolding contract §1.4
# described, which this glob excluded by prefix. That scaffolding has been
# deleted and the exclusion went with it, so every `sdle-*.md` agent prompt on
# disk is now linted — no prefix is exempt.
PRODUCT_AGENT_GLOB = "sdle-*.md"


def product_agent_files(paths: Paths) -> list[Path]:
    """The product agent prompts on disk, in name order.

    Empty — never an error — when there is no `.claude/agents/` directory at
    all. An installed skill need not ship one, and the checks that read this
    list are emitted only when the directory exists, so that "absent" can
    never be mistaken for "passed".
    """
    directory = paths.agents_dir
    if not directory.is_dir():
        return []
    return sorted(
        (p for p in directory.glob(PRODUCT_AGENT_GLOB) if p.is_file()),
        key=lambda p: p.name,
    )


def _skill_files(paths: Paths) -> list[Path]:
    """Every prompt file the content checks must cover — derived, not listed.

    This was four hardcoded property names. A list is something a future
    editor has to remember to extend, and the moment the prompt layer splits
    into progressively loaded capability files a forgotten entry means a new
    file sits outside `no_powershell_only_cmdlets`,
    `no_hardcoded_progress_outside_progress_map` and
    `discovery_vocabulary_is_not_restated_in_prompt_files` while still looking
    linted — coverage narrowing silently, which is exactly the failure mode
    splitting a prompt layer invites.

    Deriving it makes the split *strengthen* those three checks: every file
    under `modules/` and every product agent prompt is covered
    automatically, and a capability file cannot be added to an unlinted
    corner. The result is a set, not an order — every consumer accumulates
    offenders and reports them sorted or whole.
    """
    files = [paths.skill_md] if paths.skill_md.is_file() else []
    if paths.modules_dir.is_dir():
        files.extend(sorted(
            (p for p in paths.modules_dir.glob("*.md") if p.is_file()),
            key=lambda p: p.name))
    files.extend(product_agent_files(paths))
    return files


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
    """One version string, six locations.

    T11 F6 anticipated a sixth turning up during the v1.17 bump, and one did:
    ``sdle.py``'s own ``CURRENT_VERSION``, which decides when `migrate` stops
    and which nothing was checking against the template it must agree with.
    Added here rather than checked by hand, so this rule stays the single
    authority for the version string (invariant 7).
    """
    template = json.loads(paths.state_template.read_text(encoding="utf-8"))
    version = template.get("workflow_version")
    found: dict[str, str | None] = {
        "templates/state.json": version,
        "sdle.py CURRENT_VERSION": CURRENT_VERSION,
    }

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

    # T11 NB-1. The six documentation-set READMEs each open with an
    # `**Applies to:** SDLE vX.Y` line. They were written by the same phase
    # that twice fixed this exact class -- an unchecked restatement of a
    # constant -- and promptly created six more of it, so the next bump would
    # have left six documents claiming the old version. Derived by glob, not
    # listed: a seventh directory added later is covered without an edit here.
    for readme in sorted((root / "docs").glob("*/README.md")):
        applies = re.search(r"\*\*Applies to:\*\*\s*SDLE v([0-9]+\.[0-9]+)",
                            readme.read_text(encoding="utf-8"))
        if applies:
            label = f"docs/{readme.parent.name}/README.md"
            found[label] = applies.group(1)

    mismatched = {k: v for k, v in found.items() if v != version}
    return Check(
        "version_string_consistent",
        not mismatched,
        f"all {len(found)} locations report v{version}" if not mismatched
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
    """No literal 'N/<denominator>' in orchestrator instructions, for any flow.

    Every flow has its own denominator, so a hardcoded fraction is not merely
    duplicated — it is wrong for four lifecycles out of five. Scoped to
    instruction text: artifact body templates legitimately contain a progress
    string, because SDLE writes it into the artifact.
    """
    denominators = sorted({flow.phase_count for flow in consts.flows.values()})
    pattern = re.compile(
        r"\b\d+/(?:" + "|".join(str(d) for d in denominators) + r")\b")
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


def _check_repo_config_defaults_documented(paths: Paths) -> Check:
    """The documented configuration defaults must BE the shipped ones.

    T05 left `REPO_CONFIG_DEFAULTS` restated as a fenced JSON literal in
    `README.md` with nothing binding the two together — a documented default
    that can drift from the engine's, which for a boundary is a documented
    lie waiting to happen. Deleting the example was rejected: it is genuinely
    useful, and the linter exists precisely so a useful restatement can be
    *bound* rather than forbidden (CLAUDE.md: run the linter, do not check by
    hand).

    Every fenced ```json block in the two repository documents is parsed, and
    any block that is an object carrying `configVersion` must equal
    `REPO_CONFIG_DEFAULTS` exactly. Keyed on the field rather than on the
    block's position, so moving or re-ordering the section cannot silently
    disable the rule, and an unparseable block fails loudly rather than being
    skipped. A document that is *present* and carries no such block fails too
    — that is the drift. A document that is *absent* is skipped, because there
    is then no restatement to bind and `lint-skill` must still answer in a
    project that has no repository documentation at all.
    """
    root = _repo_root(paths)
    problems: list[str] = []
    examined = 0
    present: list[str] = []
    for relative in REPO_DOCS:
        path = root / relative
        if not path.is_file():
            continue
        present.append(relative)
        text = path.read_text(encoding="utf-8")
        for raw in re.findall(r"```json\n(.*?)```", text, re.S):
            try:
                document = json.loads(raw)
            except (json.JSONDecodeError, ValueError) as exc:
                problems.append(f"{relative}: a ```json block does not parse "
                                f"({exc})")
                continue
            if not isinstance(document, dict):
                continue
            if "configVersion" not in document:
                continue
            examined += 1
            if document != REPO_CONFIG_DEFAULTS:
                problems.append(
                    f"{relative}: a documented configuration block is "
                    f"{document}, but REPO_CONFIG_DEFAULTS is "
                    f"{REPO_CONFIG_DEFAULTS}")
    if not problems and present and not examined:
        problems.append(
            "no documented configuration block was found in "
            + " or ".join(present)
            + "; the check would pass vacuously")
    if not present:
        # No repository documentation in this project, so there is no
        # restatement to bind. Skipping an absent document is what every
        # other documentation rule here already does; firing instead would
        # make `lint-skill` — a runtime-free command — unable to answer in a
        # project that simply has no README.
        return Check(
            "repo_config_defaults_match_documentation", True,
            "no repository documentation in this project; nothing restates "
            "the configuration defaults")
    return Check(
        "repo_config_defaults_match_documentation",
        not problems,
        "; ".join(problems) if problems
        else f"{examined} documented configuration block(s) equal "
             "REPO_CONFIG_DEFAULTS",
    )


def _check_documentation_set(paths: Paths) -> list[Check]:
    """T11 D16 — §17's nine documentation targets exist and say something.

    Emitted only when the tree carries **both** `README.md` and `CLAUDE.md` at
    its root, which is what distinguishes the SDLE source repository from a
    project that merely has the skill installed. That is the same convention
    `_check_doc_phase_tables` already follows — a documentation rule is not
    evaluated against a tree that was never supposed to hold documentation —
    and it does not fail open: if `README.md` disappears from the source
    repository this check and `doc_lists_every_phase_README` both go absent,
    and `test_n26`'s exact-set equality over the check names fails loudly.

    "Non-empty" is deliberate. A directory holding a placeholder `.md` with no
    content would satisfy "exists" while documenting nothing, and §17 asks for
    the documentation to be *updated*, not created.
    """
    root = _repo_root(paths)
    if not ((root / "README.md").is_file() and (root / "CLAUDE.md").is_file()):
        return []

    problems: list[str] = []
    for target in DOCUMENTATION_TARGETS:
        path = root / target.rstrip("/")
        if target.endswith("/"):
            if not path.is_dir():
                problems.append(f"{target} is missing")
                continue
            documents = [f for f in sorted(path.rglob("*.md"))
                         if f.is_file() and f.stat().st_size > 0]
            if not documents:
                problems.append(f"{target} holds no non-empty .md")
        elif not path.is_file():
            problems.append(f"{target} is missing")
        elif path.stat().st_size == 0:
            problems.append(f"{target} is empty")

    return [Check(
        "documentation_set_is_present",
        not problems,
        "; ".join(problems) if problems
        else f"all {len(DOCUMENTATION_TARGETS)} documentation targets present",
    )]


def _check_documentation_index(paths: Paths) -> list[Check]:
    """Every documentation directory is reachable from `docs/README.md`.

    `documentation_set_is_present` proves the directories exist. Existing is
    not the same as being findable: the six subject directories §17 mandates
    were created by T11 and, until the index was written, were linked from
    nowhere at all -- present, lint-green, and invisible to every reader.

    A seventh added later would be equally invisible, so this is derived from
    `DOCUMENTATION_TARGETS` rather than listing the directories again
    (invariant 7). Adding a directory to that tuple and forgetting the index
    now fails the build.

    Emitted under the same condition as the check above -- the tree must carry
    both root documents -- so a project that merely installed the skill is not
    judged against the source repository's documentation rules.
    """
    root = _repo_root(paths)
    if not ((root / "README.md").is_file() and (root / "CLAUDE.md").is_file()):
        return []

    index = root / "docs" / "README.md"
    if not index.is_file():
        return [Check("documentation_index_links_every_directory", False,
                      "docs/README.md is missing")]

    text = index.read_text(encoding="utf-8")
    missing = [
        target for target in DOCUMENTATION_TARGETS
        if target.startswith("docs/") and target not in (
            # The index lives in docs/, so it links relatively.
            "docs/",
        ) and target[len("docs/"):] not in text
    ]
    return [Check(
        "documentation_index_links_every_directory",
        not missing,
        f"docs/README.md does not link: {', '.join(missing)}" if missing
        else f"every documentation directory is linked from the index",
    )]


def documented_flow_counts(consts: Constants) -> dict[str, tuple[int, int]]:
    """The phase and gate counts every document is required to state.

    Nothing is computed here: it reads `FlowSpec.phase_count` and
    `FlowSpec.gate_total`, the properties `advance` and `gate show` already
    answer with. Documentation is required to state the number the engine
    reports, and the only way to guarantee that is to ask the engine for it
    rather than to re-derive it beside it (invariant 7).

    So the convention is not a choice this function makes. `phase_count`
    **excludes the terminal `complete`** -- its own docstring calls it "the N
    in 'N/18'" -- because `complete` is a state a WorkItem lands in, not a
    phase anybody executes: `PROGRESS_MAP` numbers GREENFIELD 1 through 18 and
    gives `complete` no number of its own, sharing `18/18` with
    `gate_security`. A document that counted it printed a table disagreeing
    with the progress header the user reads on every single turn, which is
    exactly what `docs/lifecycle/README.md` did until this check existed.
    """
    return {name: (flow.phase_count, flow.gate_total)
            for name, flow in consts.flows.items()}


def _check_doc_flow_counts(paths: Paths, consts: Constants) -> list[Check]:
    """Every stated flow size in the documentation set equals the engine's.

    Two claim shapes are checked, because the documentation makes the claim
    two ways:

    * a **table row** -- ``| `HOTFIX` | 10 | 3 | ...`` -- wherever a document
      tabulates the five flows;
    * a **headline** -- ``**10 phases, 3 gates.**`` -- which is how each
      tutorial opens, bound to its flow by `FLOW_HEADLINE_DOCS` because the
      sentence does not name the flow.

    Emitted only in the source repository, the convention
    `_check_documentation_set` and `_check_doc_phase_tables` already follow: a
    project that merely installed the skill carries none of these files and is
    not judged against them. A missing file is skipped rather than failed --
    `documentation_set_is_present` is what proves the set exists, and one rule
    per fact.
    """
    root = _repo_root(paths)
    if not ((root / "README.md").is_file() and (root / "CLAUDE.md").is_file()):
        return []

    expected = documented_flow_counts(consts)
    row = re.compile(
        r"^\|\s*`(" + "|".join(map(re.escape, sorted(expected))) + r")`\s*"
        r"\|\s*(\d+)\s*\|\s*(\d+)\s*\|",
        re.MULTILINE)
    headline = re.compile(r"\*\*(?:`[A-Z_]+`,\s*)?(\d+)\s+phases?,\s*"
                          r"(\d+)\s+gates?\.?\*\*")

    problems: list[str] = []
    examined = 0

    # A third shape, because the dry-run index tabulates the flow name and the
    # size in separate cells: `| ... | `HOTFIX` | 10 phases, 3 gates | ... |`.
    # Anchored to a single table row so it cannot pair a flow named in one row
    # with a size stated in another.
    prose_row = re.compile(
        r"^\|[^\n]*?`(" + "|".join(map(re.escape, sorted(expected))) + r")`"
        r"[^\n]*?\|[^|\n]*?(\d+)\s+phases?,\s*(\d+)\s+gates?[^|\n]*\|",
        re.MULTILINE)

    for relative in FLOW_COUNT_DOCS:
        path = root / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in (row, prose_row):
            for match in pattern.finditer(text):
                flow, phases, gates = match.group(1), int(
                    match.group(2)), int(match.group(3))
                examined += 1
                if (phases, gates) != expected[flow]:
                    problems.append(
                        f"{relative}: {flow} stated as {phases} phases/"
                        f"{gates} gates, engine says {expected[flow][0]}/"
                        f"{expected[flow][1]}")

    for relative, flow in sorted(FLOW_HEADLINE_DOCS.items()):
        path = root / relative
        if not path.is_file():
            continue
        found = headline.search(path.read_text(encoding="utf-8"))
        if not found:
            problems.append(f"{relative}: no '**N phases, M gates**' headline "
                            f"for {flow}")
            continue
        examined += 1
        stated = (int(found.group(1)), int(found.group(2)))
        if stated != expected[flow]:
            problems.append(
                f"{relative}: headline says {stated[0]} phases/{stated[1]} "
                f"gates, engine says {expected[flow][0]}/{expected[flow][1]}")

    return [Check(
        "doc_flow_counts_match_engine",
        not problems,
        "; ".join(problems) if problems
        else f"{examined} stated flow count(s) equal the engine's",
    )]


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


def cmd_flow_show(args, paths: Paths) -> int:
    """The bound flow, its phases, its gates, and where it goes from here.

    Read-only, and it exists so the orchestrator asks the script instead of
    reading a table out of SKILL.md — which is SKILL.md's own instruction.
    When a governance record exists its proposal is reported alongside with an
    explicit agreement verdict, so a disagreement is *visible* before it
    becomes a `flow_mismatch` refusal at the next advance.

    There is deliberately no `flow set` / `flow select`. Traversal identity has
    exactly one writer (`init`) plus the migration that names GREENFIELD for a
    workflow predating the field; a command that re-bound it would let the
    model reshape the lifecycle, which is a governance bypass.
    """
    consts = load_constants(paths)
    state = read_state(paths)
    flow = flow_for_state(state, consts)
    current = state.get("current_phase")
    record = read_governance_record(paths) if paths.workitem else None
    proposed = ((record or {}).get("classification") or {}).get("flow")
    emit(
        "flow show",
        {
            **flow.as_dict(),
            "current_phase": current,
            "position": flow.position(current),
            "progress": state.get("progress"),
            "next_phase": flow.next_phase(current),
            "gate_number": flow.gate_number_for_phase(current),
            "label": consts.label_or(current, flow),
            "proposed_flow": proposed,
            "agrees": None if proposed is None else proposed == flow.name,
        },
    )
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
            "capability_map": consts.capability_map,
            # Every declared flow plus the injected GREENFIELD. Dumped
            # unvalidated, exactly as every other table here is: `constants`
            # is a diagnostic, and a broken FLOW_PHASES must still be
            # inspectable. `Constants.flow()` is what refuses.
            "flows": {name: built.as_dict()
                      for name, built in sorted(consts.flows.items())},
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

    sub = subparsers.add_parser(
        "resume",
        help="Everything a fresh session needs to pick a WorkItem up "
             "(read-only).",
    )
    sub.set_defaults(handler=cmd_resume)

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

    sub = subparsers.add_parser(
        "validate", help="Check the WorkItem registry and runtime placement."
    )
    sub.set_defaults(handler=cmd_validate)

    config_p = subparsers.add_parser(
        "config", help="Repository-level SDLE configuration."
    )
    config_sub = config_p.add_subparsers(dest="subcommand", required=True)
    cfg_init = config_sub.add_parser(
        "init", help="Create the repository configuration boundary."
    )
    cfg_init.set_defaults(handler=cmd_config_init)
    cfg_show = config_sub.add_parser(
        "show", help="Report the effective configuration. Writes nothing."
    )
    cfg_show.set_defaults(handler=cmd_config_show)

    governance_p = subparsers.add_parser(
        "governance", help="Requirements quality, classification and risk."
    )
    governance_sub = governance_p.add_subparsers(dest="subcommand", required=True)
    gov_policy = governance_sub.add_parser(
        "policy", help="The effective governance policy. Writes nothing."
    )
    gov_policy.set_defaults(handler=cmd_governance_policy)
    gov_assess = governance_sub.add_parser(
        "assess", help="Evaluate a structured governance input and record it."
    )
    gov_assess.add_argument("--input", required=True,
                            help="Path to the structured governance input JSON.")
    gov_assess.set_defaults(handler=cmd_governance_assess)
    gov_show = governance_sub.add_parser(
        "show", help="The recorded governance verdict and its freshness."
    )
    gov_show.set_defaults(handler=cmd_governance_show)
    gov_gates = governance_sub.add_parser(
        "gates", help="The would-be required gate set. Advisory only."
    )
    gov_gates.set_defaults(handler=cmd_governance_gates)

    baseline_p = subparsers.add_parser(
        "baseline", help="The repository baseline (contract §14). Read-only."
    )
    baseline_sub = baseline_p.add_subparsers(dest="subcommand", required=True)
    base_show = baseline_sub.add_parser(
        "show", help="The baseline and its derived status. Writes nothing."
    )
    base_show.set_defaults(handler=cmd_baseline_show)
    base_validate = baseline_sub.add_parser(
        "validate", help="Exit 0 only when the baseline is VALID."
    )
    base_validate.set_defaults(handler=cmd_baseline_validate)

    discovery_p = subparsers.add_parser(
        "discovery", help="Brownfield repository discovery (contract §14)."
    )
    discovery_sub = discovery_p.add_subparsers(dest="subcommand", required=True)
    disc_schema = discovery_sub.add_parser(
        "schema", help="The closed discovery vocabulary. Writes nothing."
    )
    disc_schema.set_defaults(handler=cmd_discovery_schema)
    disc_assess = discovery_sub.add_parser(
        "assess", help="Evaluate proposed findings and record them."
    )
    disc_assess.add_argument("--input", required=True,
                             help="Path to the structured discovery input JSON.")
    disc_assess.set_defaults(handler=cmd_discovery_assess)
    disc_show = discovery_sub.add_parser(
        "show", help="The recorded discovery findings. Writes nothing."
    )
    disc_show.set_defaults(handler=cmd_discovery_show)

    # Read-only by construction. There is deliberately no `flow set`: see
    # `cmd_flow_show`'s docstring for why a second writer of traversal
    # identity would be a governance bypass.
    flow_p = subparsers.add_parser(
        "flow", help="The bound lifecycle flow. Read-only."
    )
    flow_sub = flow_p.add_subparsers(dest="subcommand", required=True)
    flow_show = flow_sub.add_parser(
        "show", help="The bound flow, its phases and its gates. Writes nothing."
    )
    flow_show.set_defaults(handler=cmd_flow_show)

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
    wi_resolve = workitem_sub.add_parser(
        "resolve", help="Report which WorkItem the ladder resolves (never refuses)."
    )
    wi_resolve.set_defaults(handler=cmd_workitem_resolve)
    wi_use = workitem_sub.add_parser(
        "use", help="Persist this working directory's active WorkItem."
    )
    # Distinct dest, following the `migrate-workflow` precedent: argparse
    # would otherwise clobber the global --workitem with this one's default.
    wi_use.add_argument("--workitem", dest="use_workitem",
                        help="WorkItem id to make active (must be registered).")
    wi_use.add_argument("--clear", action="store_true",
                        help="Remove the persisted context instead.")
    wi_use.set_defaults(handler=cmd_workitem_use)

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
    # Deliberately flagless beyond `--gate`. A `--force`, `--reason` or
    # override flag would be an operator-supplied way past `gate_required`,
    # which is the exception mechanism §15's "casually skippable" forbids.
    omitted_p = gate_sub.add_parser(
        "omit", help="Pass a gate the policy does not require approved.")
    omitted_p.add_argument("--gate", required=True)
    omitted_p.set_defaults(handler=cmd_gate_omit)
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
    fbind = feature_sub.add_parser(
        "bind", help="Emit this WorkItem's feature environment. Writes nothing."
    )
    fbind.add_argument(
        "--require-feature", action="store_true",
        help="Refuse when no feature directory is recorded for this WorkItem.",
    )
    fbind.set_defaults(handler=cmd_feature_bind)
    fcaps = feature_sub.add_parser(
        "capabilities", help="Report what the installed SpecKit supports."
    )
    fcaps.set_defaults(handler=cmd_feature_capabilities)
    fresolve = feature_sub.add_parser(
        "resolve", help="Identify the feature directory for this WorkItem."
    )
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
    reviewed = artifact_sub.add_parser(
        "review", help="Record a review of an artifact's current content."
    )
    reviewed.add_argument("--path", required=True)
    reviewed.add_argument("--type", required=True,
                          help="The review or validation type (TP-011 cl. 4).")
    reviewed.add_argument("--result", required=True,
                          help="PASS or FAIL (TP-011 cl. 5).")
    reviewed.add_argument("--actor-type", required=True, dest="actor_type",
                          help="human | agent | tool | test | system.")
    reviewed.add_argument("--actor-name", required=True, dest="actor_name")
    reviewed.add_argument("--evidence",
                          help="Pointer to the detailed review artifact.")
    reviewed.add_argument("--comments")
    reviewed.set_defaults(handler=cmd_artifact_review)
    review_list = artifact_sub.add_parser(
        "reviews", help="List review records and their freshness."
    )
    review_list.add_argument("--path")
    review_list.set_defaults(handler=cmd_artifact_reviews)

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
    mbuild.add_argument(
        "--test-command",
        help="The project's own test command, for a runner SDLE does not "
             "detect. Run without a shell; its exit code is the evidence.")
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
