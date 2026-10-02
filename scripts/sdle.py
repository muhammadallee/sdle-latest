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
import contextlib
import copy
import hashlib
import json
import os
import posixpath
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
    ``workitem`` is the bound WorkItem id. A *bound* ``Paths`` always names
    one; ``None`` survives only before binding. Every runtime path below
    derives from ``runtime``, so no command ever concatenates a WorkItem-owned
    path of its own.
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
        """The retired repository-global runtime directory.

        Nothing binds it as a runtime. It survives as detection only: a
        **project-root marker**, and the thing a refusal points at, so a
        repository that holds one is refused with an explanation instead of
        being treated as empty. SDLE never runs, migrates or writes it.
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

    @property
    def workitem_root_relative(self) -> str:
        """The WorkItem directory as a repo-relative POSIX prefix.

        The runtime's parent. Separate from ``runtime_relative`` because one
        governed artifact — the architecture placement rendering — is a
        WorkItem *deliverable* rather than engine bookkeeping, and lives beside
        `.sdle/` rather than inside it (ADR-013).
        """
        root = self.workitem_root
        if root is None:
            return self.runtime_relative
        return str(root.relative_to(self.project_root)).replace(os.sep, "/")

    @property
    def architecture_placement_file(self) -> Path:
        """The WorkItem's validated placement record."""
        return self.runtime / "architecture-placement.json"

    @property
    def architecture_placement_rendering(self) -> Path:
        """The gated Markdown rendering of that record."""
        root = self.workitem_root
        base = self.runtime if root is None else root
        return base / "architecture" / "placement.md"

    # `workflow` is retained as an alias so call sites that only ever meant
    # "the runtime directory" did not have to move.
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
    def requirements_binding_file(self) -> Path:
        """The requirement documents this WorkItem declares it is about.

        WorkItem-owned because the relationship is (ADR-012): the same document
        may be bound by several WorkItems and by none, so it is not a property
        of the document and cannot live beside it. Written before `init`, like
        `governance_file`, because the binding is what `preflight` and the
        assessment read.
        """
        return self.runtime / "requirements.json"

    @property
    def refinement_lock_file(self) -> Path:
        """The short repository mutex for requirements ownership.

        Repository-level, under the already write-fenced `workitems/` area and
        gitignored beside the active context. Not a WorkItem runtime member
        and not a `.sdle/` boundary member, so neither closed set takes it.
        """
        return self.project_root / "workitems" / ".refinement-transaction.lock"

    @property
    def refinement_file(self) -> Path:
        """The requirements-refinement record for this WorkItem.

        WorkItem-owned, for the argument `scan_acknowledgements_file` makes:
        the loop runs before ``init``, so it cannot live in ``state.json``,
        and the same bound document may be bound by several WorkItems, so a
        loop's history is the WorkItem's own fact. Engine-written only.
        """
        return self.runtime / "refinement.json"

    @property
    def scan_acknowledgements_file(self) -> Path:
        """Explicitly acknowledged flagged content, keyed by path and SHA-256.

        WorkItem-owned, for the same reason ``governance_file`` is: written
        before ``init`` exists (`accept-content --path` works pre-init), read
        by `governance assess`, which refuses a flagged bound source unless an
        acknowledgement matching its *current* content is on file — editing a
        flagged line invalidates the old acknowledgement rather than being
        silently covered by it. Deliberately not a field of ``state.json``:
        acknowledging a document's content is a fact about the document, not
        about lifecycle state, and it must survive `init` unmigrated like
        every other pre-init record (`requirements.json`, `governance.json`).
        """
        return self.runtime / "scan-acknowledgements.json"

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

        ``None`` only for an **unbound** ``Paths``, which has no WorkItem to scope
        to; a *bound* ``Paths`` never reaches this with ``workitem`` unset.
        Derived here so no call
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
    def baseline_file(self) -> Path:
        """The baseline slot, `.sdle/baseline.json`. Written once, by the final
        gate of a `GREENFIELD` or `BROWNFIELD_DISCOVERY` WorkItem
        (`establish_baseline`); read by `baseline show`, `init` and `validate`."""
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
    def guidelines_dir(self) -> Path:
        """Where the built-in decision heuristics live (ADR-014).

        A second capability-file home beside ``modules_dir``, and enumerated by
        `lint-skill` the same way: a guideline no `CAPABILITY_MAP` row names is
        an orphan and fails, and every guideline is inside the prompt-content
        checks. Advisory content, never a rule — the precedence chain in
        `modules/architecture-placement.md` puts it below approved artifacts.
        """
        return self.skill_root / "guidelines"

    @property
    def architecture_dir(self) -> Path:
        """Repository-level architecture memory, `.sdle/architecture/`.

        Configuration-boundary content by ADR-002's location rule and
        *knowledge* by ADR-013's: derived from ``project_root`` alone, never
        from the bound WorkItem, and shared by every WorkItem in the
        repository.
        """
        return self.config_root / "architecture"

    @property
    def architecture_catalog_file(self) -> Path:
        return self.architecture_dir / "catalog.json"

    @property
    def architecture_lock_file(self) -> Path:
        """Held only across one read-check-write of the catalog."""
        return self.architecture_dir / "catalog.lock"

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
# returned — only which level stops the walk.
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
        # with no markers working.
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
# GREENFIELD workflow is said to traverse. This list is therefore frozen. The
# guarantee derivation would give for free — that no registry phase is
# orphaned — is provided by the `every_registry_phase_is_used_by_some_flow`
# lint check, which fails loudly instead of failing open.

GREENFIELD_V1_PHASES: tuple[str, ...] = (
    "requirements_check",
    "constitution_draft",
    "gate_constitution",
    "architecture_placement",
    "gate_architecture",
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
#   requirements_check      bootstrap; `init` writes it as the first phase
#   architecture_placement  decides which service this WorkItem changes; a
#                           specification written outside an approved boundary
#                           is the thing ADR-013 exists to prevent
#   gate_architecture       the human decision on that placement; universally
#                           required, because the catalog it writes is shared
#                           across WorkItems (see `gate_requirements`)
#   spec_draft          the only phase that creates the feature directory
#   gate_spec           the first Spec Kit human gate
#   plan_draft          `speckit-tasks` derives from plan.md
#   tasks_draft         `speckit-implement` derives from tasks.md
#   implement           carries the secrets scan and the test evidence
#   gate_implement      the human decision on that evidence
#   security_review     the terminal safety control
#   gate_security       the terminal human gate; writes the completion summary
#   complete            terminal
MANDATORY_FLOW_PHASES: tuple[str, ...] = (
    "requirements_check",
    "architecture_placement",
    "gate_architecture",
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
        """The N in 'N/20' under GREENFIELD — every phase but ``complete``."""
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
        """The N in 'N/20' under GREENFIELD — every phase but ``complete``."""
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
        ordinal can be flow-relative; this view is the GREENFIELD one, the same
        under every flow that has that gate.
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

    return consts


def flow_for_state(state: dict | None, consts: Constants) -> Flow:
    """The flow this workflow is traversing.

    Bound once by ``init`` and never re-bound: there is deliberately no
    command that writes it. A state with no ``flow`` names no lifecycle, so it
    is read as GREENFIELD, the default flow.
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
    # filter as a false `dirty_tree`.
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

CURRENT_VERSION = "1.18"

STATUS_DISPLAY = {
    "pending": "PENDING",
    "in_progress": "IN PROGRESS",
    "awaiting_approval": "AWAITING APPROVAL",
    "awaiting_reapproval": "AWAITING RE-APPROVAL (DRIFT DETECTED)",
    "completed": "COMPLETED",
    "rejected": "REJECTED — REMEDIATION NEEDED",
    "failed": "FAILED — ACTION REQUIRED",
}


def read_state(paths: Paths, *, any_version: bool = False) -> dict:
    """The WorkItem's state, parsed.

    Refuses `unsupported_state_version` when the file was written under a state
    schema other than `CURRENT_VERSION`. SDLE never reinterprets, upgrades or
    resets such a file: it is left exactly as found and the remedy is a new
    WorkItem. Two commands pass `any_version=True` because they read the file
    without interpreting it: `state get` returns a stored field as it is, and
    `audit verify` checks the ledger's hash chain, which does not depend on the
    schema. Anything that derives a flow, a label or a verdict from the state
    (`state dump`, `doctor`) refuses instead of applying today's rules to
    yesterday's shape.
    """
    relative = paths.runtime_relative
    if not paths.state_file.is_file():
        raise IntegrityError(
            "state_unreadable",
            f"No {relative}/state.json in this project. "
            "Run `init` to start a workflow.",
            {"path": str(paths.state_file)},
        )
    try:
        state = json.loads(paths.state_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise IntegrityError(
            "state_unreadable",
            f"{relative}/state.json is not valid JSON: {exc}. "
            "Options: 'reset workflow' to start fresh, or inspect the file.",
            {"path": str(paths.state_file), "error": str(exc)},
        ) from None
    version = state.get("workflow_version") if isinstance(state, dict) else None
    if not any_version and version != CURRENT_VERSION:
        raise Refused(
            "unsupported_state_version",
            f"{relative}/state.json uses state schema {version!r}, and this "
            f"SDLE reads only {CURRENT_VERSION!r}. It never rewrites another "
            "version; the file is left exactly as it is. Start a current "
            "WorkItem with `workitem create --name <name>`, or inspect this "
            "one with `state dump`.",
            {"workflow_version": version, "supported": CURRENT_VERSION,
             "path": str(paths.state_file)},
        )
    return state


def save_state(paths: Paths, state: dict, session: str | None = None) -> None:
    """Persist state atomically. ``last_updated`` is implicit and mandatory."""
    state["last_updated"] = now_iso()
    write_atomic(paths.state_file, json.dumps(state, indent=2) + "\n")
    touch_lock(paths, session)


# --------------------------------------------------------------------------
# Spec Kit context (contract §10)
#
# The `specKit` object is owned by the WorkItem. Every read and every write
# goes through the two accessors below, so a state without it degrades to
# all-null instead of raising KeyError at an arbitrary call site.
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

    ``review`` and ``evidence_id`` are the audit linkage of a governed artifact
    review. When both are ``None`` the rendered block is **byte-identical** to
    an entry that carries neither, which is what lets an older ledger keep
    verifying.
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

    The one place the chain rule is stated: ``cmd_audit_verify`` and any other
    caller verify a ledger through it instead of restating it.
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
    state = read_state(paths, any_version=True)
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
# init / state / header
# --------------------------------------------------------------------------


def infer_project_name(paths: Paths) -> str | None:
    """The project's name, from the binding's primary document (ADR-012).

    It used to be the first `#` heading in whichever file under
    `requirements/` sorted first alphabetically — so a second WorkItem's
    document, dropped in beside the first, could rename somebody else's
    project. The binding names which document speaks for this WorkItem.
    """
    try:
        binding = validated_binding(paths)
    except (Refused, IntegrityError):
        # Naming the project is a convenience, and the caller already falls
        # back to the WorkItem title. The refusal belongs to the commands whose
        # decisions rest on the binding, not to this.
        return None
    primary = binding.get("primary")
    if not primary:
        return None
    target = paths.project_root / primary
    if not target.is_file():
        return None
    # Only the primary. Falling through to the other bound documents let a
    # headingless product document hand the project's name to whichever
    # secondary happened to have one — a regulatory annex naming the project.
    # No heading here means the caller's existing fallback (the WorkItem
    # title), which is a worse name but an honest one.
    for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
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

    # ADR-012: the documents this WorkItem declared, not a listing of a
    # directory. `bound_sources` refuses `requirements_unbound` when the step
    # was skipped, and a bound document that has gone missing is refused here
    # rather than at the assessment, where the message would be about
    # staleness instead of about the file that is not there.
    requirements = bound_sources(paths)
    absent = [relative for relative in requirements
              if not (paths.project_root / relative).is_file()]
    if absent:
        raise Refused(
            "requirements_source_missing",
            "This WorkItem is bound to requirement documents that are not in "
            f"the repository: {', '.join(absent)}. Restore them, or re-run "
            "`requirements bind` with the documents it is actually about.",
            {"workitem": paths.workitem, "missing": absent},
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
    # The flow binds HERE, once, and nothing ever re-binds it. There
    # is deliberately no `flow set` / `flow select` command: a second writer of
    # traversal identity would let the model reshape the lifecycle by issuing a
    # command, which is a governance bypass. Governance is deliberately not an
    # `init` precondition, so the no-record case has to exist and has to be the
    # safe one: GREENFIELD is the default flow.
    record = read_governance_record(paths) if paths.workitem else None
    classification = (record or {}).get("classification") or {}
    proposed = classification.get("flow")
    state["flow"] = (
        proposed if isinstance(proposed, str) and proposed else DEFAULT_FLOW
    )
    # R1 and R2, evaluated HERE because this is the single
    # flow-binding site, and evaluated *before* the first `mkdir` below so a
    # refusal creates nothing at all. A pure reader: it returns the derived
    # baseline status and writes nothing. The status is recorded in the
    # `flow_selected` entry, so the facts the binding decision rested on stay
    # auditable. The flow and the opt-in are passed in as plain values so this
    # command never names a repository-configuration member itself (§11).
    baseline_at_binding = baseline_precondition(
        paths, state["flow"], bool(classification.get("rediscovery")))
    # `init` is the one mover that deliberately does NOT go through
    # `apply_advance` — governance is not an `init` precondition — so it
    # reads the flow directly.
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
    # is a disposable convenience (`workitem use --clear` recreates it), so a
    # filesystem problem here must not report a successfully initialised
    # workflow as a failure.
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
    state = read_state(paths, any_version=True)
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
    no upgrade and no repair. A read-only command that silently changes state
    is not read-only.
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
                # The flag alone is not the whole fact. A
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
# initialised, and it is also the runtime scope: `init` requires a resolved
# WorkItem and writes `workitems/<id>/.sdle/`. Identity is created first and
# never changes; the runtime is created under it.

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
    return parse_index(path.read_text(encoding="utf-8"), path)


def parse_index(text: str, path: Path) -> list[dict[str, str]]:
    """The registry table parser, over text rather than a file.

    Separated from ``read_index`` so the registry as it stood at another commit
    can be parsed by exactly the same rules (F-102). ``path`` names the file
    only for the refusal message.
    """
    lines = [line for line in text.splitlines() if line.strip()]
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
# The ladder is the minimum that makes the runtime addressable: an explicit
# `--workitem`, the launch directory, a sole registered WorkItem, the persisted
# active context, then a unique Git-branch match. The ladder NEVER guesses:
# when more than one WorkItem could be meant it refuses and lists them.

# Commands that touch no runtime state, so the ladder never runs for them.
RUNTIME_FREE_COMMANDS = frozenset({
    "lint-skill", "sha", "constants", "workitem",
    # `validate` exists to diagnose repositories that are too broken to
    # resolve, so it must never be gated on resolution succeeding. It runs the
    # ladder itself, speculatively, and turns a refusal into a finding.
    "validate",
    # `config` is repository-global by definition. Contract §11's exit
    # criterion is that it resolves *independently* of WorkItem runtime state,
    # so binding a WorkItem first would contradict the boundary it creates.
    "config",
    # `governance policy` reads a repository-scoped policy and must
    # resolve with no WorkItem bound, exactly like `config`. The WorkItem-
    # scoped members of the group (`assess`, `show`, `gates`) bind explicitly
    # through `bind_workitem`, so the ladder is exercised, not bypassed.
    "governance",
    # `discovery schema` reports the closed §14 vocabulary and must be
    # answerable before any workflow exists — it is what the prompt layer
    # reads instead of restating the category ids. `assess` and `show` bind
    # explicitly through `bind_for_discovery`.
    "discovery",
    # The baseline is repository-level by definition — §14's convergence
    # invariant is a property of the repository, not of any WorkItem — so both
    # its readers resolve without one, exactly like `config`.
    "baseline",
    # The architecture catalog is the repository's accumulated knowledge, not
    # a WorkItem's (ADR-013), so `architecture schema` and `architecture show`
    # must answer in a repository with no WorkItem at all — `show` is how a
    # new WorkItem learns what already exists. The WorkItem-scoped members
    # (`assess`, `apply`, `realize`) bind explicitly through
    # `bind_for_architecture`, so the ladder is exercised, not bypassed.
    "architecture",
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
# It is written by exactly two commands, `init` and `workitem use`, and by
# nothing else. `bind_workitem` must never write it:
# its purity is what lets `.claude/hooks/hooks.py::dirty_tree` call it
# speculatively from a PreToolUse callback, and a hook that writes state is a
# second writer (CLAUDE.md invariant 6).

ACTIVE_CONTEXT_NAME = ".active-context.json"
ACTIVE_CONTEXT_SETTERS = ("init", "use")


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

    ``ACTIVE_CONTEXT_SETTERS`` is load-bearing rather than documentary. The
    fact it encodes — that exactly two commands (`init`, `use`) may set the
    context — is enforced here, so a third writer cannot be added without
    something objecting. This is a *programming* error, not a user input
    error: no CLI argument can reach it, so it raises ``ValueError`` rather
    than becoming a refusal with a reason string that could never be
    triggered from outside.
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

    Two properties of the CLI contract:

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
    context is *read* here and only ever *written* by `init` and
    `workitem use`. That purity is what lets
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

    **A retired ``.workflow/`` runtime never binds.** With zero WorkItems the
    answer is ``none`` whether or not legacy state exists, and the ladder
    still never guesses. ``bind_workitem`` says so in its refusal and points
    at `workitem create`, which is RUNTIME_FREE and so never reaches this
    ladder.

    ``for_init`` is the one exception. `init` reports ``legacy_present``
    whenever legacy state exists, *whatever* the registered count:
    proceeding would create a second runtime beside a retired one.
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
        # Rung 6: nothing is registered. A retired `.workflow/` on disk does not
        # change the answer: it is never a runtime, and `bind_workitem` names
        # the way forward in its refusal.
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

    **Every non-raising return names a WorkItem.** There is no return path
    that yields ``paths`` with ``workitem is None``, so no command downstream
    needs a carve-out for one.
    """
    decision = resolve_decision(paths, explicit, for_init=for_init)

    if decision.reason == "legacy_present":
        raise Refused(
            "legacy_workflow_present",
            "A repository-global workflow from a retired runtime exists at "
            f"{paths.legacy_workflow.name}/state.json. SDLE does not run or "
            "migrate it, and will not run two runtimes side by side. It is "
            "left exactly as it is: remove or move it aside, then create a "
            "current WorkItem with `workitem create --name <name>`.",
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
            # A repository whose only runtime is the retired `.workflow/`. No
            # rung binds it, so this refusal is the *only* signpost such a
            # repository gets. It must name the way out, or the repository
            # looks bricked. Same reason string, same exit code: no
            # CLI-contract break.
            legacy = paths.legacy_workflow / "state.json"
            raise Refused(
                "workitem_required",
                "No WorkItem is registered, and a workflow from a retired "
                f"runtime exists at {paths.legacy_workflow.name}/state.json. "
                "SDLE does not run or migrate it and leaves it exactly as it "
                "is. Start a current WorkItem instead: "
                "`workitem create --name <name>`.",
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
# The id carries a collision-resistant suffix,
# `muh-20260816T171501Z-1a2b3c4d`. The readable prefix is unchanged. At second
# resolution alone, two executions in one second would share an id, and the id
# is a key: it names every evidence file (`governance-<id>.json`, …) and it is
# the governance ledger's de-duplication marker. The second execution would
# then overwrite the first one's evidence and never reach the ledger at all.
# An id without the suffix is still read everywhere, because nothing parses an
# id — each one is compared whole, as an opaque key. See ADR-009.


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

    ``pending_confirm_action`` is a *flag*: it says an acknowledgement is
    outstanding, never what was acknowledged. On its own the second invocation
    could arrive on a **third** branch and be waved through on an
    acknowledgement the user gave for a different checkout — the guard's whole
    subject matter, unaudited. So ``pending_branch_ack`` records the branch
    that was acknowledged, and the second step must match it. A mismatch
    re-arms the guard against the branch you are actually on and refuses
    again; it never silently proceeds.

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

        # The acknowledgement was for a different checkout. Re-arm
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
# definitions, the repository baseline and implementation-transition
# metadata. It is a *different boundary* from `workitems/<id>/.sdle/`, which
# holds lifecycle state, execution, audit, evidence and manifests.
#
# The boundary moves **no lifecycle rule into it**: the lifecycle flows stay
# authoritative and nothing in them reads `config.json`. `configVersion` is
# therefore a namespace of its own — it is not `workflow_version` and it is not
# a state field.
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

    Absent `config.json` yields the defaults verbatim, which is safe because
    an absent document is a real answer. An **unreadable** one is not, and this
    reader does not answer it with the defaults from inside an exception
    handler: that shape was only defensible while its one caller ran
    `repo_config_findings` first and already refused on every condition the
    handler swallowed — a safety property held somewhere else, which stops
    being true the first time a second caller appears. §15's whole subject is
    not weakening governance silently, so presence and readability are
    different questions, and only the first of them has a default.

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
        bound.discovery_file, bound.requirements_binding_file,
        bound.architecture_placement_file, bound.scan_acknowledgements_file,
        bound.refinement_file,
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
    """A WorkItem must not record a feature directory outside its own
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
    feature-directory containment check for a state that passed both."""
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
    # Only a *disagreement* is a finding. An absent field is not evidence of a
    # misplaced runtime, and calling it one would be a false positive.
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
            f"{len(indexed)} WorkItem(s) are registered; SDLE does not run it "
            "and leaves it untouched, so remove it when it is no longer needed",
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
    #    every repository with no `.sdle/`.
    findings.extend(repo_config_findings(paths))

    # 8b. the repository baseline (contract §14). Silent for every repository
    #     that has none. Reported through the same single predicate
    #     `baseline show` uses, so the two can never disagree.
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
        paths.baseline_file.name,
        paths.implementation_state_dir.name,
        # ADR-013: the shared architecture catalog lives at the configuration
        # boundary, so a `.sdle/architecture/` inside a WorkItem runtime is
        # the same class of mistake as a `.sdle/policies/` there.
        paths.architecture_dir.name,
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
    for directory in (paths.policies_dir, paths.implementation_state_dir):
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
            # Named, not created: §14 owns the baseline schema.
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
        # Four of §15's nine hard floors name a condition no existing
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

# What each of the twelve quality checks asks of a requirements document, in the
# words an assessor is given. A separate constant and not a key of the policy
# above: the policy is deep-copied into every WorkItem's pinned policy and is
# what an override is validated against, and neither wants prose in it. Its
# keys are the same twelve `quality_checks` ids, in the same order (a test
# asserts it), and it is not overridable: a repository that could reword a
# check could change what a PASS means. The wording is the *measured* wording.
# Editing any of it invalidates the corpus baseline it was measured against,
# so a test pins each definition's digest and a change must update it on
# purpose, after re-measuring.
QUALITY_CHECK_DEFINITIONS = {
    "problem_statement": (
        "does the document state what problem is being solved and for whom, clearly enough that someone "
        "unfamiliar with the project would understand why it exists?"
    ),
    "scope": (
        "does the document state what is being built, concretely enough to bound the work?"
    ),
    "out_of_scope": (
        "does the document state what is explicitly excluded?"
    ),
    "acceptance_criteria": (
        "are there criteria by which \"done\" can be checked, each either identifiable (a stable id) or "
        "stating an observable outcome (a result, state, response, value, or refusal)? No specific format "
        "is required — Given/When/Then, EARS, or plain precise sentences are all acceptable."
    ),
    "ambiguity": (
        "is the document free of vague, unmeasurable language in normative statements (e.g. \"fast\", "
        "\"user-friendly\", \"robust\", \"as appropriate\", \"etc.\", \"some\", \"several\") where something concrete "
        "was needed?"
    ),
    "contradictions": (
        "are there no statements that directly conflict with each other?"
    ),
    "constraints": (
        "does the document state the technical, business, regulatory or platform constraints that bound "
        "the solution (where any genuinely apply)?"
    ),
    "nfrs": (
        "where the document makes quantitative quality claims (performance, latency, throughput, "
        "capacity, availability, scalability), are they stated with a measure (a number and a unit)? "
        "Answer `NOT_APPLICABLE` only if the document makes no such quantitative claims at all."
    ),
    "security_data_implications": (
        "does the document address the security and data-handling implications of what it describes, "
        "where any genuinely apply (e.g., sensitive data, authentication, authorization)?"
    ),
    "compatibility": (
        "does the document address compatibility with existing systems, versions, or integrations it "
        "depends on or must coexist with, where relevant?"
    ),
    "dependencies": (
        "does the document identify, specifically enough to tell which one is meant, each external "
        "system, service or third party that the solution must integrate with, call, or run on (for "
        "example an identity provider, a payment gateway, an existing internal service, or a shared "
        "platform)? Technology that the solution itself chooses — a database product, framework, library "
        "or ORM — is not an external dependency for this check: a requirements document may leave those "
        "choices to the engineering constitution, and describing storage as, say, a relational store is "
        "not a failure. A document that states it has no external dependencies, or that names none "
        "because none exist, satisfies the check. Fail only when an external system the solution relies "
        "on is referred to by category or vague phrase alone, so that a reader could not tell which "
        "system is meant."
    ),
    "blocking_unknowns": (
        "is the document free of unresolved placeholders, markers, or open questions (`TBD`, `TODO`, "
        "`???`, empty sections) that block understanding what is being asked for?"
    ),
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
        # Not part of the policy and not overridable: reported beside it so a
        # caller reads the words each check asks, from the engine, instead of
        # restating them.
        "check_definitions": QUALITY_CHECK_DEFINITIONS,
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
# `state.json` exists, so it cannot be owned by it. The same argument puts
# branch and SHA in `execution.json`.
# --------------------------------------------------------------------------

GOVERNANCE_RECORD_VERSION = "3"
# Every version this engine can READ. An unrecognised version is an integrity
# failure rather than a silent "assume the current shape" — a version field
# nothing refuses on proves nothing.
#
# `"1"` and `"2"` records stay valid and carry no `pinnedPolicy`, so they
# derive from the live policy alone, exactly as the engine did before ADR-011.
# That is deliberate and it is the fail-OPEN direction, which needs saying:
# refusing them would freeze every WorkItem that was in flight when the pin
# shipped, and an older record is evidence of an older schema, not evidence of
# a tighter policy. Such a WorkItem gains the pin the next time it is
# assessed, and `revalidate_recorded_omissions` re-checks its earlier
# omissions at the terminal gate.
GOVERNANCE_RECORD_VERSIONS = ("1", "2", "3")
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


REQUIREMENTS_BINDING_VERSION = "1"


def _binding_refused(reason: str, message: str, **data) -> Refused:
    return Refused(reason, message, data)


class _PathProblem(Exception):
    """Internal signal only — never escapes `_lexically_safe_path`. Carries
    which rule fired, so each of that function's two callers can raise its
    own reason and wording for the same underlying fact."""

    def __init__(self, kind: str):
        self.kind = kind


def _lexically_safe_path(paths: Paths, raw: str) -> str:
    """Every lexical and containment check a repository-relative path must
    pass, shared by `_binding_source` (a *bound* requirements source) and
    `safe_repo_path` (any path the orchestrator names to `scan`/
    `accept-content`) — the safety rules are identical; only the reason code
    and wording differ per caller, which is why this raises `_PathProblem`
    rather than a refusal itself. Kept as one function rather than two
    independently-maintained copies after the second one was found to have
    drifted the day it was written, missing the Windows-alias checks the
    first already had.

    Returns the normalised POSIX-relative path. Never checks existence or
    whether it names a directory — callers that need a file to be there
    check separately, with whatever reason fits their own contract.
    """
    text = str(raw).strip().replace(chr(92), "/")
    # Windows resolves `file.md::$DATA` and `file.md.` to the ordinary file
    # while the stored string stays distinct, so the same document could be
    # matched twice and one spelling would not match the other. Rejected as
    # syntax rather than normalised: a path SDLE records must mean one file on
    # every platform, and a colon or a trailing dot in a component means it
    # does not.
    for part in text.split("/"):
        # "." and ".." end in a dot but are not aliases: "." is the current
        # directory and is dropped by `normpath` below, so `./x` and `x` are
        # one file under one key; any ".." is refused as traversal rather than
        # collapsed, because collapsing it lexically through a symlinked
        # directory can name a different file than the filesystem does.
        if part == "..":
            raise _PathProblem("traversal")
        if part == ".":
            continue
        if ":" in part or part != part.rstrip(". "):
            raise _PathProblem("alias")
    if any(ord(ch) < 32 for ch in text):
        raise _PathProblem("control")
    if not text:
        raise _PathProblem("empty")
    if posixpath.isabs(text) or re.match(r"^[A-Za-z]:", text):
        raise _PathProblem("absolute")
    normal = posixpath.normpath(text)
    if normal == ".":
        raise _PathProblem("empty")
    if normal == ".." or normal.startswith("../"):
        raise _PathProblem("traversal")
    target = paths.project_root / normal
    try:
        resolved = target.resolve()
        resolved.relative_to(paths.project_root.resolve())
    except (OSError, ValueError):
        raise _PathProblem("escape") from None
    return normal


def safe_repo_path(paths: Paths, raw: str) -> tuple[Path, str]:
    """An arbitrary path the orchestrator names — for `scan --path` and
    `accept-content --path`, never only a *bound* source — canonicalised and
    checked against the repository root, or refused `path_invalid`.

    `scan`/`accept-content` had no path safety at all before this: a `--path`
    reading `../../outside.md`, an absolute path, a Windows-alias spelling,
    or a symlink resolving outside the tree would be joined and read
    unchecked. Returns `(target, canonical_relative_key)` — every caller
    uses the *key* everywhere a path is stored, matched or emitted
    (`pending_confirm_action`, the acknowledgement record, the audit message,
    emitted `data`), never the raw string a user typed, so two spellings of
    the same file can never appear to name two different ones.

    Accepted as an engine-wide limitation, not fixed here: `target` is
    reconstructed from the canonical key rather than the `resolved` handle
    `_lexically_safe_path` already opened to check containment, so a symlink
    retargeted in the gap between this check and the caller's later
    `is_file()`/`read_bytes()` call is still followed. Returning the already-
    resolved `Path` object instead would not close this — Python's file APIs
    re-resolve at the syscall that actually opens the file regardless of
    whether `.resolve()` was called on the object earlier, so the two forms
    behave identically here. Closing it for real needs a file-descriptor-
    anchored open (`O_NOFOLLOW`/`openat`), which every other path-based read
    in this engine — including `requirements_sources`, which this mirrors —
    also lacks; this is that same, pre-existing, engine-wide property, not a
    gap specific to `scan`/`accept-content`.
    """
    try:
        normal = _lexically_safe_path(paths, raw)
    except _PathProblem as problem:
        message = {
            "alias": f"'{raw}' uses a spelling that names different files on "
                     "different platforms (a ':' stream, or a trailing dot "
                     "or space). Use the plain path.",
            "control": f"'{raw}' is not a usable path.",
            "empty": f"'{raw}' is not a usable path.",
            "absolute": f"'{raw}' is an absolute path. Name it relative to "
                        "the repository root.",
            "traversal": f"'{raw}' leaves the repository or contains a '..' "
                         "component. Name it relative to the repository "
                         "root, without one.",
            "escape": f"'{raw}' resolves outside the repository (a symlink "
                      "or junction pointing away from it).",
        }[problem.kind]
        raise Refused("path_invalid", message, {"path": raw}) from None
    return paths.project_root / normal, normal


def _binding_source(paths: Paths, raw: str, must_exist: bool = True) -> str:
    """One bound path, validated and canonicalised, or a refusal.

    Every rule here exists because the binding decides what a governance
    assessment is *about*: a path that escapes the repository, or that names a
    directory whose contents can change underneath the record, would make the
    recorded set mean something other than what it says.
    """
    try:
        normal = _lexically_safe_path(paths, raw)
    except _PathProblem as problem:
        message = {
            "alias": f"'{raw}' uses a spelling that names different files on "
                     "different platforms (a ':' stream, or a trailing dot "
                     "or space). Bind the document by its plain path.",
            "control": f"'{raw}' contains a control character. A "
                       "requirements source is an ordinary repository path.",
            "empty": "An empty path is not a requirements source.",
            "absolute": f"'{raw}' is an absolute path. Bind requirement "
                        "sources by their path relative to the repository "
                        "root, so the record means the same thing in every "
                        "checkout.",
            "traversal": f"'{raw}' leaves the repository or contains a "
                         "'..' component. A requirements source must be a "
                         "file inside it, named without one.",
            "escape": f"'{raw}' resolves outside the repository (a symlink "
                      "or junction pointing away from it). SDLE will not "
                      "read requirements from outside the tree it governs.",
        }[problem.kind]
        raise _binding_refused("requirements_source_invalid", message,
                               source=raw) from None
    target = paths.project_root / normal
    if target.is_dir():
        raise _binding_refused(
            "requirements_source_invalid",
            f"'{raw}' is a directory. Bind the documents themselves, so the "
            "recorded set cannot change without the binding changing — "
            "`requirements bind --all-current` expands a directory into the "
            "exact files present now.", source=raw)
    if must_exist and not target.is_file():
        raise _binding_refused(
            "requirements_source_missing",
            f"'{raw}' is not a file in this repository, so it cannot be a "
            "requirements source.", source=raw)
    return normal


def binding_digest(sources: list[str]) -> str:
    """Identity of the bound *set*, independent of file contents.

    Content changes are `governance_stale`; a change to *which* documents are
    bound is a different fact, and the governance record carries this digest so
    the two can be told apart.
    """
    # Canonical JSON, not newline-joined: `["a\nb", "c"]` and `["a", "b\nc"]`
    # join to the same text, so two different bindings would hash alike and a
    # re-bind between them would be invisible.
    payload = json.dumps(sorted(sources), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_requirements_binding(paths: Paths) -> dict | None:
    """The WorkItem's binding, or ``None`` when it has none.

    A malformed binding is an integrity failure, never an absence: reading it
    as "not bound yet" would let a corrupt file be silently replaced, and the
    binding is what says which documents a recorded assessment was about.
    """
    target = paths.requirements_binding_file
    if not target.is_file():
        return None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise IntegrityError(
            "requirements_binding_invalid",
            f"{paths.runtime_relative}/{target.name} cannot be read: {exc}. "
            "Re-run `requirements bind`.",
            {"path": str(target), "error": str(exc)}) from None
    if not isinstance(document, dict) or not isinstance(
            document.get("sources"), list):
        raise IntegrityError(
            "requirements_binding_invalid",
            f"{paths.runtime_relative}/{target.name} is not a requirements "
            "binding. Re-run `requirements bind`.", {"path": str(target)})
    version = document.get("bindingVersion")
    if version != REQUIREMENTS_BINDING_VERSION:
        raise IntegrityError(
            "requirements_binding_invalid",
            f"{paths.runtime_relative}/{target.name} declares bindingVersion "
            f"{version!r}; this engine reads "
            f"{REQUIREMENTS_BINDING_VERSION!r}.",
            {"path": str(target), "version": version})
    return document


def validated_binding(paths: Paths) -> dict:
    """The binding, revalidated, or a refusal. **The one read path.**

    `read_requirements_binding` checks only that the file parses and declares a
    version it can read. That is not enough for a file every governance
    decision rests on: the write fence is a tripwire, not a guarantee, and a
    merge, a restored backup or a skipped hook can leave a binding that parses
    and still says something the engine must not act on.

    So every read revalidates, and containment is rechecked **here** rather
    than only at bind time: a symlink bound while it pointed inside the
    repository can be retargeted afterwards, and nothing else would notice.
    """
    binding = read_requirements_binding(paths)
    if binding is None:
        raise _binding_refused(
            "requirements_unbound",
            f"WorkItem '{paths.workitem}' has not declared which requirement "
            "documents it is about, so there is nothing to check, assess or "
            "measure against. Run `requirements bind --source <path>` "
            "(or `--all-current`) first.",
            workitem=paths.workitem)

    sources = binding["sources"]
    if not sources or not all(isinstance(item, str) for item in sources):
        raise IntegrityError(
            "requirements_binding_invalid",
            f"{paths.runtime_relative}/{paths.requirements_binding_file.name} "
            "declares no usable source list. Re-run `requirements bind`.",
            {"path": str(paths.requirements_binding_file)})
    owner = binding.get("workitem")
    if owner != paths.workitem:
        raise IntegrityError(
            "requirements_binding_invalid",
            f"{paths.runtime_relative}/{paths.requirements_binding_file.name} "
            f"belongs to WorkItem {owner!r}, not {paths.workitem!r}. A binding "
            "moved between WorkItems says nothing trustworthy about either.",
            {"path": str(paths.requirements_binding_file), "declares": owner})
    if binding.get("digest") != binding_digest(sources):
        raise IntegrityError(
            "requirements_binding_invalid",
            f"{paths.runtime_relative}/{paths.requirements_binding_file.name} "
            "does not match its own digest, so it was edited after it was "
            "written. Re-run `requirements bind`.",
            {"path": str(paths.requirements_binding_file)})

    seen: list[str] = []
    for item in sources:
        # The same syntax and containment rules the bind applied, applied
        # again. A path that was legal when bound is not therefore legal now.
        canonical = _binding_source(paths, item, must_exist=False)
        if any(canonical.lower() == other.lower() for other in seen):
            raise IntegrityError(
                "requirements_binding_invalid",
                f"{paths.runtime_relative}/"
                f"{paths.requirements_binding_file.name} binds '{item}' twice.",
                {"path": str(paths.requirements_binding_file), "source": item})
        seen.append(canonical)
    primary = binding.get("primary")
    if primary not in sources:
        raise IntegrityError(
            "requirements_binding_invalid",
            f"{paths.runtime_relative}/{paths.requirements_binding_file.name} "
            f"names {primary!r} as its primary document, which it does not "
            "bind.",
            {"path": str(paths.requirements_binding_file), "primary": primary})
    return binding


def bound_sources(paths: Paths) -> list[str]:
    """The bound paths, validated on every read."""
    return list(validated_binding(paths)["sources"])


def requirements_sources(paths: Paths, strict: bool = False
                        ) -> tuple[list[dict], str, dict[str, bytes]]:
    """Every **bound** requirement document with its SHA, one digest, and the
    raw bytes actually read for each — each source is read from disk exactly
    once, here, and the caller passes those same bytes on rather than
    re-reading: two separate reads of the same bound source, at two
    different times, is exactly the gap a concurrent edit can exploit —
    `governance assess` used to hash here and re-read again in
    `unacknowledged_flagged_sources`, so it no longer does.

    ``strict`` is what `governance assess` passes: an assessment may not be
    *recorded* against a document that is not there. Without it, deleting a
    bound document and re-assessing wrote a ``null`` SHA as the new baseline,
    and freshness then matched that null — the deletion healed itself.

    The set is the WorkItem's binding (ADR-012), not a listing of a directory.
    Globbing `requirements/` made one WorkItem's document freeze another: a
    file nobody had assessed against still entered every WorkItem's digest, so
    adding one refused the next `advance` of every run in the repository.

    A bound document that has since disappeared is recorded with a ``null``
    SHA rather than dropped, so the assessment goes stale — naming the missing
    path — instead of quietly resting on a smaller set than it was made from.
    """
    sources: list[dict] = []
    missing: list[str] = []
    raw_by_path: dict[str, bytes] = {}
    for relative in bound_sources(paths):
        target = paths.project_root / relative
        if not target.is_file():
            missing.append(relative)
            sources.append({"path": relative, "sha256": None})
            continue
        raw = target.read_bytes()
        raw_by_path[relative] = raw
        sources.append({"path": relative, "sha256": hashlib.sha256(raw).hexdigest()})
    if strict and missing:
        raise _binding_refused(
            "requirements_source_missing",
            "This WorkItem is bound to requirement documents that are not in "
            f"the repository: {', '.join(missing)}. An assessment cannot be "
            "recorded against a document that is not there. Restore them, or "
            "re-run `requirements bind` with the documents it is about.",
            workitem=paths.workitem, missing=missing)
    sources.sort(key=lambda entry: entry["path"])
    return sources, _sources_digest(sources), raw_by_path


def _sources_digest(sources: list[dict]) -> str:
    """The one formula for "these documents, with these contents".

    Shared by the writer (`governance assess`) and the reader
    (`governance_freshness`), so a comparison can never be made against a
    digest that was computed a second way.
    """
    payload = "\n".join(f"{e['path']} {e['sha256']}" for e in sources)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# The presentation-neutral normal form of a requirements document
#
# Two versions of a document that differ only in how they are laid out must
# have one normal form, so a re-assessment cannot be told the document changed
# when only its whitespace did - and, the other way round, so that a change which
# alters what a reader sees can never hide inside a "formatting" edit. The
# engine decides neutrality from this form, never the proposer.
#
# What is neutral: the line-ending convention; whitespace-only lines and runs of
# two or more blank lines; the number of blank lines or newlines at the end of
# the file; runs of spaces inside the text of a prose line (not its leading
# indentation, not a code span, not an indented or fenced code line, not a table
# row); and trailing whitespace on blank lines, table rows and inside fenced
# blocks. What is NOT neutral, on purpose: trailing whitespace on a non-blank
# prose line. Two trailing spaces are Markdown's hard line break, so removing
# them changes what renders; they are kept, and a change to them is a change.
# Nothing else is normalised - headings, list markers, emphasis, links and table
# cells compare as written.
#
# Line endings are unified FIRST. A carriage return left on the end of a line
# would otherwise read as trailing whitespace, and the hard-break rule would
# misfire on every file that arrives with Windows line endings.
# --------------------------------------------------------------------------

_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_CODE_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")


def _collapse_spaces_outside_code_spans(text: str) -> str:
    out: list[str] = []
    position = 0
    for span in _CODE_SPAN.finditer(text):
        out.append(re.sub(r" {2,}", " ", text[position:span.start()]))
        out.append(span.group(0))
        position = span.end()
    out.append(re.sub(r" {2,}", " ", text[position:]))
    return "".join(out)


def requirements_normal_form(text: str) -> str:
    """The presentation-neutral normal form of one document's text. Pure and
    idempotent; see the block comment above for exactly what it does and does
    not treat as neutral."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: list[str] = []
    fence: tuple[str, int] | None = None  # (character, run length)
    previous_blank = False
    for line in lines:
        if fence is not None:
            closing = re.match(r"^ {0,3}(" + re.escape(fence[0]) + "{" + str(fence[1]) + r",})\s*$", line)
            out.append(line.rstrip())
            if closing:
                fence = None
            previous_blank = False
            continue
        opening = _FENCE_OPEN.match(line)
        if opening:
            fence = (opening.group(1)[0], len(opening.group(1)))
            out.append(line.rstrip())
            previous_blank = False
            continue
        if not line.strip():
            if not previous_blank:
                out.append("")
            previous_blank = True
            continue
        previous_blank = False
        if line.lstrip().startswith("|"):
            out.append(line.rstrip())  # a table row keeps its spacing
            continue
        if line.startswith("    ") or line.startswith("\t"):
            out.append(line)  # indented: code or a continuation; left as written
            continue
        body = line.rstrip()
        trailing = line[len(body):]
        indent = re.match(r"^ *", body).group(0)
        out.append(indent + _collapse_spaces_outside_code_spans(body[len(indent):]) + trailing)
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n" if out else ""


def requirements_content_digest(raw_by_path: dict[str, bytes]) -> str:
    """One digest for a bound set, over each document's normal form. The same
    shape as `_sources_digest` - sorted paths, one line each - but a document
    contributes the SHA-256 of its normal form, so two sets that differ only in
    presentation have one digest. Pure: it reads nothing."""
    lines = []
    for path in sorted(raw_by_path):
        normal = requirements_normal_form(
            raw_by_path[path].decode("utf-8", errors="replace"))
        lines.append(f"{path} {hashlib.sha256(normal.encode('utf-8')).hexdigest()}")
    return hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# The requirements-refinement record (WorkItem-owned)
#
# What a refinement loop did to one WorkItem's bound requirements: which
# iteration found what, which questions were asked and answered, which edits
# were proposed and what became of them, and how the loop ended. Engine-written
# only, through `write_refinement_record`, and refused when it is not a file the
# engine wrote - the rule `requirements.json` follows, for the same reason: it
# decides what a later step may do, so a hand-edited one cannot be trusted.
# Strict on purpose: an unknown key is refused, and a new field arrives as a
# version bump, never as a silently tolerated extra.
# --------------------------------------------------------------------------

REFINEMENT_RECORD_VERSION = "1"
# The most iterations a loop may take. One engine constant: a record may carry
# a lower cap, never a higher one.
REFINEMENT_ITERATION_CAP_MAX = 3
REFINEMENT_QUESTIONS_MAX = 5
REFINEMENT_ACTIVE_STATUSES = ("IN_PROGRESS", "AWAITING_REASSESSMENT")
REFINEMENT_TERMINAL_STATUSES = ("PASSED", "ESCALATED", "CANCELLED", "FAILED")
REFINEMENT_EDIT_OPS = ("replace", "insert_after", "append_section")
REFINEMENT_EDIT_DECISIONS = ("accepted", "rejected")
REFINEMENT_OUTCOMES = ("progress", "regression", "stall")
REFINEMENT_CAP_SOURCES = ("builtin", "policy")

_REFINEMENT_KEYS = frozenset((
    "refinementVersion", "workitem", "status", "iterationCap",
    "iterationCapSource", "iterations", "startedAt", "endedAt"))
_REFINEMENT_ITERATION_KEYS = frozenset((
    "iteration", "contentDigest", "proposalDigest", "failingChecks",
    "findings", "questions", "edits", "outcome", "disputeOutcomes"))
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _refinement_invalid(relative: str, detail: str) -> IntegrityError:
    return IntegrityError(
        "refinement_record_invalid",
        f"{relative} is not a refinement record the engine wrote: {detail}. "
        "It is never edited by hand: restore it from version control.",
        {"path": relative, "detail": detail})


def _refinement_object(value, keys, where: str, relative: str) -> dict:
    if not isinstance(value, dict):
        raise _refinement_invalid(relative, f"{where} is not an object")
    if set(value) != set(keys):
        missing = sorted(set(keys) - set(value))
        extra = sorted(set(value) - set(keys))
        raise _refinement_invalid(
            relative, f"{where} has the wrong keys (missing {missing}, "
                      f"unexpected {extra})")
    return value


def _refinement_text(value, where: str, relative: str,
                     allow_none: bool = False) -> None:
    if value is None and allow_none:
        return
    if not isinstance(value, str) or not value.strip():
        raise _refinement_invalid(relative, f"{where} is not a non-empty string")


def _refinement_hex(value, where: str, relative: str) -> None:
    if not isinstance(value, str) or not _HEX64.match(value):
        raise _refinement_invalid(relative, f"{where} is not a SHA-256 digest")


def _refinement_check_id(value, where: str, relative: str) -> None:
    if value not in QUALITY_CHECK_DEFINITIONS:
        raise _refinement_invalid(
            relative, f"{where} names {value!r}, which is not a quality check")


def validate_refinement_record(doc, relative: str,
                               workitem: str | None = None) -> dict:
    """The document, or an integrity failure naming the first thing wrong."""
    doc = _refinement_object(doc, _REFINEMENT_KEYS, "the record", relative)
    if doc["refinementVersion"] != REFINEMENT_RECORD_VERSION:
        raise _refinement_invalid(
            relative, f"version {doc['refinementVersion']!r} is not "
                      f"{REFINEMENT_RECORD_VERSION!r}")
    _refinement_text(doc["workitem"], "workitem", relative)
    if workitem is not None and doc["workitem"] != workitem:
        raise _refinement_invalid(
            relative, f"it belongs to WorkItem {doc['workitem']!r}, not to "
                      f"{workitem!r}")
    active = doc["status"] in REFINEMENT_ACTIVE_STATUSES
    if not active and doc["status"] not in REFINEMENT_TERMINAL_STATUSES:
        raise _refinement_invalid(relative, f"status {doc['status']!r} is unknown")
    cap = doc["iterationCap"]
    if (isinstance(cap, bool) or not isinstance(cap, int)
            or not 1 <= cap <= REFINEMENT_ITERATION_CAP_MAX):
        raise _refinement_invalid(
            relative, f"iterationCap {cap!r} is not an integer from 1 to "
                      f"{REFINEMENT_ITERATION_CAP_MAX}")
    if doc["iterationCapSource"] not in REFINEMENT_CAP_SOURCES:
        raise _refinement_invalid(
            relative, f"iterationCapSource {doc['iterationCapSource']!r} is unknown")
    _refinement_text(doc["startedAt"], "startedAt", relative)
    _refinement_text(doc["endedAt"], "endedAt", relative, allow_none=True)
    if active != (doc["endedAt"] is None):
        raise _refinement_invalid(
            relative, "a loop that is still active has no endedAt, and a "
                      "finished one has")
    iterations = doc["iterations"]
    if not isinstance(iterations, list) or len(iterations) > cap:
        raise _refinement_invalid(
            relative, f"iterations is not a list of at most {cap}")
    for position, entry in enumerate(iterations, start=1):
        where = f"iteration {position}"
        entry = _refinement_object(entry, _REFINEMENT_ITERATION_KEYS, where, relative)
        if entry["iteration"] != position or isinstance(entry["iteration"], bool):
            raise _refinement_invalid(
                relative, f"{where} is numbered {entry['iteration']!r}")
        _refinement_hex(entry["contentDigest"], f"{where} contentDigest", relative)
        _refinement_hex(entry["proposalDigest"], f"{where} proposalDigest", relative)
        failing = entry["failingChecks"]
        if not isinstance(failing, list) or len(set(failing)) != len(failing):
            raise _refinement_invalid(
                relative, f"{where} failingChecks is not a list of distinct ids")
        for check in failing:
            _refinement_check_id(check, f"{where} failingChecks", relative)
        if not isinstance(entry["findings"], list):
            raise _refinement_invalid(relative, f"{where} findings is not a list")
        for finding in entry["findings"]:
            finding = _refinement_object(
                finding, ("checkId", "text"), f"{where} finding", relative)
            _refinement_check_id(finding["checkId"], f"{where} finding", relative)
            _refinement_text(finding["text"], f"{where} finding text", relative)
        questions = entry["questions"]
        if not isinstance(questions, list) or len(questions) > REFINEMENT_QUESTIONS_MAX:
            raise _refinement_invalid(
                relative, f"{where} questions is not a list of at most "
                          f"{REFINEMENT_QUESTIONS_MAX}")
        for question in questions:
            question = _refinement_object(
                question, ("id", "text", "options", "answer"),
                f"{where} question", relative)
            _refinement_text(question["id"], f"{where} question id", relative)
            _refinement_text(question["text"], f"{where} question text", relative)
            if (not isinstance(question["options"], list)
                    or not all(isinstance(o, str) for o in question["options"])):
                raise _refinement_invalid(
                    relative, f"{where} question options is not a list of strings")
            _refinement_text(question["answer"], f"{where} question answer",
                             relative, allow_none=True)
        if not isinstance(entry["edits"], list):
            raise _refinement_invalid(relative, f"{where} edits is not a list")
        for edit in entry["edits"]:
            edit = _refinement_object(
                edit, ("op", "path", "anchor", "baseSha256", "autoApplied",
                       "decision"), f"{where} edit", relative)
            if edit["op"] not in REFINEMENT_EDIT_OPS:
                raise _refinement_invalid(
                    relative, f"{where} edit op {edit['op']!r} is unknown")
            _refinement_text(edit["path"], f"{where} edit path", relative)
            _refinement_text(edit["anchor"], f"{where} edit anchor", relative,
                             allow_none=True)
            _refinement_hex(edit["baseSha256"], f"{where} edit baseSha256", relative)
            if not isinstance(edit["autoApplied"], bool):
                raise _refinement_invalid(
                    relative, f"{where} edit autoApplied is not a boolean")
            if (edit["decision"] is not None
                    and edit["decision"] not in REFINEMENT_EDIT_DECISIONS):
                raise _refinement_invalid(
                    relative, f"{where} edit decision {edit['decision']!r} is unknown")
        if entry["outcome"] is not None and entry["outcome"] not in REFINEMENT_OUTCOMES:
            raise _refinement_invalid(
                relative, f"{where} outcome {entry['outcome']!r} is unknown")
        if not isinstance(entry["disputeOutcomes"], list):
            raise _refinement_invalid(
                relative, f"{where} disputeOutcomes is not a list")
        for dispute in entry["disputeOutcomes"]:
            dispute = _refinement_object(
                dispute, ("checkId", "outcome", "originalResult", "evidenceRef",
                          "decisionRef", "contentDigest"),
                f"{where} dispute outcome", relative)
            _refinement_check_id(dispute["checkId"], f"{where} dispute outcome", relative)
            if dispute["outcome"] != "overturned_by_dispute":
                raise _refinement_invalid(
                    relative, f"{where} dispute outcome {dispute['outcome']!r} is unknown")
            if dispute["originalResult"] != "FAIL":
                raise _refinement_invalid(
                    relative, f"{where} dispute outcome overturns {dispute['originalResult']!r}, "
                              "and only a FAIL can be overturned")
            _refinement_text(dispute["evidenceRef"], f"{where} evidenceRef", relative)
            _refinement_text(dispute["decisionRef"], f"{where} decisionRef", relative)
            _refinement_hex(dispute["contentDigest"],
                            f"{where} dispute contentDigest", relative)
    return doc


def read_refinement_record(paths: Paths) -> dict | None:
    """This WorkItem's validated refinement record, or ``None`` when there is
    none. A malformed one is an integrity failure and never an absence: reading
    it as "no loop yet" would let a corrupt file be silently overwritten."""
    target = paths.refinement_file
    relative = target.relative_to(paths.project_root).as_posix()
    if not target.is_file():
        return None
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise _refinement_invalid(relative, f"it cannot be read ({exc})") from None
    return validate_refinement_record(doc, relative, paths.workitem)


def write_refinement_record(paths: Paths, record: dict) -> str:
    """Validate the outgoing record, then write it atomically; returns the
    repository-relative path. The ONLY writer of this file: a record that would
    not read back never reaches disk, so `read_refinement_record` can never be
    the command that discovers corruption this one created."""
    relative = paths.refinement_file.relative_to(paths.project_root).as_posix()
    validate_refinement_record(record, relative, paths.workitem)
    write_atomic(paths.refinement_file, json.dumps(record, indent=2) + "\n")
    return relative


def refinement_lint_evidence_problems(doc) -> list[str]:
    """What is wrong with a lint-evidence document, or an empty list. A pure
    check on the shape, so no engine-written record can assert that a lint
    finding was enforced: the lint is advisory, and `floorEnforced` is false
    for every finding."""
    problems: list[str] = []
    if not isinstance(doc, dict):
        return ["the evidence is not an object"]
    if set(doc) != {"kind", "executionId", "documentSha256", "findings"}:
        return [f"the evidence has the wrong keys: {sorted(doc)}"]
    if doc["kind"] != "refinement-lint":
        problems.append(f"kind {doc['kind']!r} is not 'refinement-lint'")
    if not isinstance(doc["executionId"], str) or not doc["executionId"]:
        problems.append("executionId is not a non-empty string")
    if not isinstance(doc["documentSha256"], str) or not _HEX64.match(doc["documentSha256"]):
        problems.append("documentSha256 is not a SHA-256 digest")
    if not isinstance(doc["findings"], list):
        return problems + ["findings is not a list"]
    for index, finding in enumerate(doc["findings"]):
        where = f"finding {index}"
        if (not isinstance(finding, dict) or set(finding) != {
                "ruleId", "mappedCheck", "floorEligible", "floorEnforced",
                "line", "text"}):
            problems.append(f"{where} has the wrong keys")
            continue
        if finding["mappedCheck"] not in QUALITY_CHECK_DEFINITIONS:
            problems.append(f"{where} maps to {finding['mappedCheck']!r}, not a quality check")
        if not isinstance(finding["floorEligible"], bool):
            problems.append(f"{where} floorEligible is not a boolean")
        if finding["floorEnforced"] is not False:
            problems.append(f"{where} floorEnforced is not false: the lint is advisory")
        if (isinstance(finding["line"], bool) or not isinstance(finding["line"], int)
                or finding["line"] < 1):
            problems.append(f"{where} line is not a positive integer")
        if not isinstance(finding["text"], str):
            problems.append(f"{where} text is not a string")
    return problems


# --------------------------------------------------------------------------
# The advisory requirements lint
#
# Cheap, deterministic rules over a bound set of requirements documents,
# each mapped to an existing quality check. It RECORDS evidence and decides
# nothing: no finding refuses an assessment or overrides an assessor's answer,
# and `floorEnforced` is false on every finding. `floorEligible` says only that
# the rule has not produced a false positive on the measured corpus, so a later
# decision to enforce it would be a decision, not a default.
#
# Every rule declares what it applies to, because a rule that cannot tell a
# requirement from a description of the past, a quotation or a code sample
# turns a writing-style preference into a defect:
#   - normative text is a prose or list line that carries a modal (must, shall,
#     should, will, required to, needs to); descriptive text is never normative;
#   - fenced code, indented code, inline code spans, block quotations and HTML
#     comments are excluded from every line rule;
#   - "section" rules ask a question of the whole bound set, not of one
#     document, and report on the first document in path order;
#   - the duplicate-id rule looks only at DEFINITIONS (an id that opens a list
#     item, heading or table row), never at references to an id.
# --------------------------------------------------------------------------

REQUIREMENTS_LINT_RULES = {
    "unresolved_marker": {
        "mappedCheck": "blocking_unknowns", "floorEligible": True,
        "applies_to": "TBD, TODO (upper case only), ??? and empty sections, in "
                      "prose, list and heading lines outside code and quotations"},
    "vague_term": {
        "mappedCheck": "ambiguity", "floorEligible": False,
        "applies_to": "normative lines only (a line carrying a modal verb)"},
    "missing_acceptance_section": {
        "mappedCheck": "acceptance_criteria", "floorEligible": True,
        "applies_to": "the bound set: no heading names acceptance"},
    "missing_out_of_scope_section": {
        "mappedCheck": "out_of_scope", "floorEligible": True,
        "applies_to": "the bound set: no heading or label names out of scope or non-goals"},
    "acceptance_not_checkable": {
        "mappedCheck": "acceptance_criteria", "floorEligible": True,
        "applies_to": "the acceptance sections of the bound set, as one body: "
                      "neither a stable id nor an observable outcome; no format "
                      "is mandated"},
    "quantity_without_measure": {
        "mappedCheck": "nfrs", "floorEligible": False,
        "applies_to": "normative lines about performance, latency, throughput, "
                      "capacity, availability or scalability; binary and "
                      "categorical requirements are exempt"},
    "duplicate_id": {
        "mappedCheck": "contradictions", "floorEligible": True,
        "applies_to": "definitions of a requirement or criterion id across the "
                      "bound set; reported on the later definition"},
}

_LINT_MODAL = re.compile(
    r"\b(must|shall|should|will|required to|needs? to)\b", re.IGNORECASE)
_LINT_VAGUE = (
    "fast", "quick", "quickly", "user-friendly", "robust", "as appropriate",
    "appropriate", "etc.", "and/or", "some", "several", "convenient", "simple",
    "easy to use", "reasonable", "intuitive", "efficient", "efficiently")
_LINT_VAGUE_RE = re.compile(
    r"(?<![\w-])(" + "|".join(re.escape(w) for w in _LINT_VAGUE) + r")(?![\w-])",
    re.IGNORECASE)
_LINT_QUANT = re.compile(
    r"\b(performance|latency|throughput|capacity|availability|scalab\w+)\b",
    re.IGNORECASE)
_LINT_MEASURE = re.compile(
    r"\d+(\.\d+)?\s?(ms|milliseconds?|s|sec|seconds?|minutes?|hours?|"
    r"req(uests)?/s|rps|%|percent|kb|mb|gb|users?|items?|nines|requests?)\b",
    re.IGNORECASE)
_LINT_CATEGORICAL = re.compile(
    r"\b(comply|compliance|encrypt\w*|tls|authenticat\w*|authoriz\w*|"
    r"supports?|supported|compatib\w+|policy|retention|gdpr|audit)\b", re.IGNORECASE)
_LINT_HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_LINT_ACCEPTANCE_HEADING = re.compile(r"\bacceptance\b", re.IGNORECASE)
_LINT_SCOPE_HEADING = re.compile(
    r"\b(out[ -]of[ -]scope|non-goals?|not in scope|exclusions?)\b", re.IGNORECASE)
_LINT_SCOPE_LABEL = re.compile(
    r"^\s*(?:[-*+]\s*)?\**(out[ -]of[ -]scope|non-goals?|not in scope)\**\s*:", re.IGNORECASE)
_LINT_OUTCOME = re.compile(
    r"\b(returns?|responds?|response|succeeds?|fails?|rejected|accepted|refuses?|"
    r"then|status \d+|error|exit \d+|must (be|equal|return|reject|accept))\b",
    re.IGNORECASE)
_LINT_STABLE_ID = re.compile(
    r"^\s*(?:[-*+]\s*)?(?:[A-Z]{2,}-\d+|\d+\.)\s", re.MULTILINE)
_LINT_ID_DEFINITION = re.compile(
    r"^\s*(?:[-*+]\s+|\d+\.\s+|#{1,6}\s+|\|\s*)?\**([A-Z]{2,}-\d+)\**\s*"
    r"(?::|\||\.\s|[-\u2013\u2014]\s)")
_LINT_SPAN = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")


def _lint_lines(text: str) -> list[tuple[int, str, str]]:
    """(line number, kind, text) for every line. Kind is one of blank, heading,
    fence, code, quote, comment, prose. A prose line has its inline code spans
    blanked, so no rule can match inside one."""
    out: list[tuple[int, str, str]] = []
    fence: tuple[str, int] | None = None
    in_comment = False
    for number, raw in enumerate(
            text.replace("\r\n", "\n").replace("\r", "\n").split("\n"), start=1):
        if fence is not None:
            closing = re.match(
                r"^ {0,3}(" + re.escape(fence[0]) + "{" + str(fence[1]) + r",})\s*$", raw)
            out.append((number, "code", raw))
            if closing:
                fence = None
            continue
        if in_comment:
            out.append((number, "comment", raw))
            if "-->" in raw:
                in_comment = False
            continue
        opening = _FENCE_OPEN.match(raw)
        if opening:
            fence = (opening.group(1)[0], len(opening.group(1)))
            out.append((number, "code", raw))
            continue
        stripped = raw.strip()
        if not stripped:
            out.append((number, "blank", raw))
        elif stripped.startswith("<!--"):
            out.append((number, "comment", raw))
            in_comment = "-->" not in stripped
        elif stripped.startswith(">"):
            out.append((number, "quote", raw))
        elif raw.startswith("    ") or raw.startswith("\t"):
            out.append((number, "code", raw))
        elif _LINT_HEADING.match(raw):
            out.append((number, "heading", raw))
        else:
            out.append((number, "prose", _LINT_SPAN.sub(
                lambda m: " " * len(m.group(0)), raw)))
    return out


def _lint_sections(lines):
    """(heading text, heading line, level, body lines) for every heading, the
    body running to the next heading of the same or a higher level."""
    headings = [(i, _LINT_HEADING.match(raw)) for i, (_, kind, raw)
                in enumerate(lines) if kind == "heading"]
    sections = []
    for position, (index, match) in enumerate(headings):
        level = len(match.group(1))
        end = len(lines)
        for later, later_match in headings[position + 1:]:
            if len(later_match.group(1)) <= level:
                end = later
                break
        sections.append((match.group(2), lines[index][0], level,
                         lines[index + 1:end]))
    return sections


def _lint_finding(rule: str, line: int, text: str) -> dict:
    return {"ruleId": rule, "mappedCheck": REQUIREMENTS_LINT_RULES[rule]["mappedCheck"],
            "floorEligible": REQUIREMENTS_LINT_RULES[rule]["floorEligible"],
            "floorEnforced": False, "line": line, "text": text.strip()[:160]}


def requirements_lint(documents: dict[str, str], path: str,
                      execution_id: str) -> dict:
    """The lint evidence for ``path``, judged in the context of the whole bound
    set ``documents`` (path -> text). Pure and deterministic: it reads nothing
    and writes nothing, and the result is advisory (see the block above)."""
    findings: list[dict] = []
    parsed = {name: _lint_lines(body) for name, body in documents.items()}
    lines = parsed[path]
    first = sorted(parsed)[0]

    for number, kind, text in lines:
        if kind not in ("prose", "heading"):
            continue
        if (re.search(r"\bTBD\b", text, re.IGNORECASE) or "???" in text
                or re.search(r"\bTODO\b", text)):
            findings.append(_lint_finding("unresolved_marker", number, text))
    for _heading, line, level, body in _lint_sections(lines):
        content = [b for b in body if b[1] not in ("blank",)]
        if not content:
            findings.append(_lint_finding(
                "unresolved_marker", line, "an empty section: " + _heading))

    for number, kind, text in lines:
        if kind != "prose" or not _LINT_MODAL.search(text):
            continue
        vague = _LINT_VAGUE_RE.search(text)
        if vague:
            findings.append(_lint_finding(
                "vague_term", number, f"{vague.group(1)!r} in: {text}"))
        if (_LINT_QUANT.search(text) and not _LINT_MEASURE.search(text)
                and not _LINT_CATEGORICAL.search(text)):
            findings.append(_lint_finding("quantity_without_measure", number, text))

    all_sections = {name: _lint_sections(parsed[name]) for name in sorted(parsed)}
    acceptance = [(name, s) for name, secs in all_sections.items()
                  for s in secs if _LINT_ACCEPTANCE_HEADING.search(s[0])]
    has_scope = any(_LINT_SCOPE_HEADING.search(s[0])
                    for secs in all_sections.values() for s in secs) or any(
        kind == "prose" and _LINT_SCOPE_LABEL.match(text)
        for body in parsed.values() for _n, kind, text in body)
    if path == first:
        if not acceptance:
            findings.append(_lint_finding(
                "missing_acceptance_section", 1,
                "no heading in the bound set names acceptance"))
        if not has_scope:
            findings.append(_lint_finding(
                "missing_out_of_scope_section", 1,
                "no heading in the bound set names out of scope"))
    if acceptance and acceptance[0][0] == path:
        body = "\n".join(raw for _, (_h, _l, _lv, body_lines) in acceptance
                         for _n, k, raw in body_lines if k == "prose")
        if not _LINT_STABLE_ID.search(body) and not _LINT_OUTCOME.search(body):
            findings.append(_lint_finding(
                "acceptance_not_checkable", acceptance[0][1][1],
                "the acceptance sections carry no stable id and no observable outcome"))

    seen: set[str] = set()
    for name in sorted(parsed):
        for number, kind, text in parsed[name]:
            if kind != "prose":
                continue
            definition = _LINT_ID_DEFINITION.match(text)
            if not definition:
                continue
            identifier = definition.group(1)
            if identifier in seen and name == path:
                findings.append(_lint_finding(
                    "duplicate_id", number, f"{identifier} is already defined: {text}"))
            seen.add(identifier)

    findings.sort(key=lambda f: (f["line"], f["ruleId"]))
    normal = requirements_normal_form(documents[path])
    return {"kind": "refinement-lint", "executionId": execution_id,
            "documentSha256": hashlib.sha256(normal.encode("utf-8")).hexdigest(),
            "findings": findings}


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

    `classification.flow` is what `init` binds `state["flow"]` from, so it
    selects the phases the WorkItem traverses. `classification.type` is still
    consumed by nothing: making risk and type drive gate *requirements* is the
    gate policy's job. One flag covers both keys, and the binding one is what
    it has to report.

    The third, optional key is `rediscovery`. §14 makes a sound repository
    baseline refuse a second full brownfield discovery, and this is the
    deliberate opt-in that asks for one anyway. It is monotone-safe — it can
    only ask for more work — and it is a contradiction with any flow other
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

    *Within* one assessment a lower proposal is already inert and already
    recorded: ``final`` is the lattice maximum and ``loweringAttempted`` says
    an attempt was made. *Across* two assessments that needs a record of its
    own: without one, re-running `governance assess` with a smaller signal set
    would simply replace the record, so a gate that had been required could
    become omittable with nothing anywhere stating that a level had fallen —
    the practical route to omitting a gate the policy had flagged.

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

    This records "what the required gate set would be"; the gate policy
    consumes it rather than duplicating it. It is only half an answer on its
    own: a dictionary lookup cannot know which gates the bound flow actually
    contains, and it cannot see the derived terminal-gate rule.
    ``gate_requirements`` is the function that decides anything.
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
#
# ONE stored value is read back, and it is the exception that keeps the rule:
# `pinnedPolicy`, the policy the WorkItem started under (ADR-011). Live
# derivation alone let a policy that required a gate at the start be relaxed
# mid-run so the gate became omittable, which is F-024. The pin is applied as
# an AND — omittable live AND omittable when it started — so it can only ever
# refuse more. It authorises nothing, which is precisely why it is not the
# second source of truth the paragraph above forbids.

# The closed disposition vocabulary. Three values, each a different fact:
# "the flow does not contain this phase" and "the policy does not require this
# gate"; conflating them is how a report comes to claim a guarantee nobody is
# enforcing.
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

    Two of those reasons are **derived rather than declared**, and both are
    deliberately out of reach of a policy file, because a policy dictionary
    can only ever add to this set:

      ``terminal_gate``      the last gate before completion, at every risk
                             level, in every flow;
      ``architecture_gate``  `gate_architecture` (ADR-013). The catalog it
                             writes is shared cross-WorkItem memory, and an
                             approved placement becomes evidence a later
                             WorkItem reasons from, so no placement enters it
                             without a human. There is no risk level and no
                             WorkItem type at which this is omittable.
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
        if gate_key == ARCHITECTURE_GATE_KEY:
            reasons.append("architecture_gate")
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


def governance_freshness(paths: Paths, record: dict,
                         raw_out: dict[str, bytes] | None = None) -> dict:
    """Is the recorded assessment still about the current requirements?

    Derived from the digest every time, never stored as a flag — a stored
    "fresh" boolean would be a second source of truth for the same fact.

    Each source is read once. When `raw_out` is given it receives those exact
    bytes, so a caller that must also *scan* them does not read the file a
    second time: two reads at two moments is the gap a concurrent edit can
    exploit, the same reason `requirements_sources` hands its bytes on.
    """
    recorded_block = record.get("requirements") or {}
    recorded_sources = recorded_block.get("sources") or []
    recorded = recorded_block.get("digest")

    # The paths the assessment was made from, re-hashed now. Deliberately not
    # a fresh reading of the binding: re-binding is its own fact, caught by the
    # binding digest below, and mixing the two would report "the documents
    # changed" when what changed was which documents.
    current: list[dict] = []
    missing: list[str] = []
    for entry in recorded_sources:
        relative = entry.get("path")
        target = paths.project_root / relative if relative else None
        if target is not None and target.is_file():
            raw = target.read_bytes()
            if raw_out is not None:
                raw_out[relative] = raw
            current.append({"path": relative,
                            "sha256": hashlib.sha256(raw).hexdigest()})
        else:
            missing.append(relative)
            current.append({"path": relative, "sha256": None})
    current.sort(key=lambda entry: entry["path"])
    digest = _sources_digest(current)

    binding = validated_binding(paths)
    bound_now = sorted(binding["sources"])
    recorded_binding = recorded_block.get("bindingDigest")
    # A record with no `bindingDigest` was written before a binding existed, so
    # nothing says which documents it was about. Treating that as "no binding
    # to compare" let such a WorkItem advance unbound — the implicit default
    # ADR-012 refuses. It is stale until it is re-assessed against a binding,
    # and it is reported as its own fact rather than as a digest mismatch,
    # because the remedy is different: re-assess, not restore a file.
    unbound_record = recorded_binding is None
    rebound = (not unbound_record
               and recorded_binding != binding_digest(bound_now))

    return {
        "fresh": recorded == digest and not rebound and not unbound_record,
        "recorded_digest": recorded,
        "current_digest": digest,
        "current_sources": [entry["path"] for entry in current],
        "current_entries": current,
        "missing_sources": missing,
        "rebound": rebound,
        "assessed_without_a_binding": unbound_record,
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

    The single place the ADR-011 pin is applied, so `gate omit`, `advance`'s
    omission re-derivation, `revalidate_recorded_omissions`, `gate show` and
    `resume` cannot answer "is this gate required" differently.
    """
    record = read_governance_record(paths)
    if record is None:
        return None
    return requirement_model(
        consts, flow_for_state(state, consts),
        record.get("classification") or {},
        (record.get("risk") or {}).get("finalLevel"),
        read_governance_policy(paths, consts), record)


def requirement_model(consts: Constants, flow: Flow, classification: dict,
                      final_level: str | None, effective: dict,
                      record: dict | None) -> dict:
    """The requirement model for ``flow``, narrowed by the ADR-011 pin.

    The single home of the rule. `gate_requirements_for_state` resolves the
    flow from `state.json`; `governance gates` has to answer *before* `init`
    and resolves it from the record's proposed classification. Both arrive
    here, because two derivations of "is this gate required" is precisely the
    second source of truth invariant 7 forbids — and while the pin lived in
    only one of them, `gate show` and `governance gates` disagreed.
    """
    model = gate_requirements(consts, flow, classification, final_level,
                              effective["policy"])
    model["policy"] = {"source": effective["source"],
                       "sha256": effective["sha256"]}

    pinned = (record or {}).get("pinnedPolicy")
    model["pinned_policy"] = None if not isinstance(pinned, dict) else {
        "source": pinned.get("source"), "sha256": pinned.get("sha256"),
        "pinnedAt": pinned.get("pinnedAt")}
    if isinstance(pinned, dict) and isinstance(pinned.get("policy"), dict):
        # Re-derived against the LIVE classification and risk level, so a
        # genuine re-scope still moves the answer. Only the policy is pinned;
        # a risk downgrade stays legitimate, audited rather than refused, as
        # `modules/gate-protocol.md` states.
        at_start = gate_requirements(consts, flow, classification, final_level,
                                     pinned["policy"])
        _apply_policy_pin(model, at_start)
    return model


def _apply_policy_pin(model: dict, at_start: dict) -> None:
    """Narrow ``model`` in place by the requirements that held at the start.

    An AND over the two flow-scoped models: a gate the live policy leaves
    omittable but the pinned one required becomes required. Nothing moves the
    other way, so no gate the live policy requires can be relaxed by the pin,
    and a gate the bound flow does not contain is untouched — the pin narrows
    what may be omitted, it does not invent a gate.

    The promoted reasons keep the rule that produced them and are tagged
    `pinned:` (``pinned:always``, ``pinned:risk:HIGH``), because
    `modules/gate-protocol.md` displays `requirement_reasons` at the gate and a
    user who cannot omit needs to see that it is the starting policy talking.
    """
    required_at_start = {entry["gate"]: entry["reasons"]
                         for entry in at_start["dispositions"]
                         if entry["disposition"] == "required"}
    for entry in model["dispositions"]:
        if entry["disposition"] != "omittable":
            continue
        pinned_reasons = required_at_start.get(entry["gate"])
        if not pinned_reasons:
            continue
        entry["disposition"] = "required"
        entry["reasons"] = entry["reasons"] + [
            f"pinned:{reason}" for reason in pinned_reasons]
    model["required_gates"] = sorted(
        e["gate"] for e in model["dispositions"] if e["disposition"] == "required")
    model["omittable_gates"] = sorted(
        e["gate"] for e in model["dispositions"] if e["disposition"] == "omittable")


def bind_for_governance(args, paths: Paths) -> Paths:
    """`governance` is runtime-free at the group level so `policy` can resolve
    with no WorkItem. Its WorkItem-scoped members bind here — through the
    ladder, never around it.

    There is no ``governance_workitem_required`` refusal here: a non-raising
    ``bind_workitem`` always names a WorkItem, so that branch would be
    unreachable code, not a guard.
    """
    return bind_workitem(paths, args.workitem)


# --------------------------------------------------------------------------
# Assessment integrity: one content, one verdict
#
# A check that FAILed at a given content must not later read PASS at that same
# content: a requirements document that did not change cannot have become
# adequate, so the second answer is the assessor changing its mind, not the
# requirements improving. "Same content" is the presentation-neutral content
# digest, never the raw bytes - otherwise a whitespace edit, which is neutral,
# would unlock the flip.
#
# The history is this WorkItem's own: every `evidence/governance-*.json` whose
# `kind` is "governance" (never by file name - a refused attempt is evidence of
# another kind and is not history), plus the current record as the last entry,
# because the record is written before its evidence and a crash can leave one
# without the other. An assessment recorded before the digest existed carries
# none and is "unknown" - except that one whose raw requirements digest equals
# today's was made over byte-identical text, so its content is known.
# --------------------------------------------------------------------------


def _history_invalid(path: Path, why: str) -> IntegrityError:
    return IntegrityError(
        "governance_history_invalid",
        f"{path.name} is not an assessment record the engine wrote ({why}), "
        "so the assessment history cannot be trusted and no assessment is "
        "recorded. Restore the file from version control; it is never edited "
        "or skipped.",
        {"path": str(path), "detail": why})


def _history_entry(record, source: Path, raw_digest: str,
                   content_digest: str) -> dict:
    if not isinstance(record, dict):
        raise _history_invalid(source, "the record is not an object")
    quality = record.get("quality")
    checks = quality.get("checks") if isinstance(quality, dict) else None
    if not isinstance(checks, list):
        raise _history_invalid(source, "it has no list of quality checks")
    results: dict[str, str] = {}
    for check in checks:
        if (not isinstance(check, dict) or not isinstance(check.get("id"), str)
                or check.get("result") not in QUALITY_RESULTS):
            raise _history_invalid(source, "a quality check is malformed")
        results[check["id"]] = check["result"]
    block = record.get("requirements")
    if not isinstance(block, dict):
        raise _history_invalid(source, "it has no requirements block")
    recorded = block.get("contentDigest")
    if recorded is None and block.get("digest") == raw_digest:
        recorded = content_digest
    if recorded is not None and not (
            isinstance(recorded, str) and re.fullmatch(r"[0-9a-f]{64}", recorded)):
        raise _history_invalid(source, "its content digest is malformed")
    return {"source": source.name, "contentDigest": recorded,
            "executionId": record.get("executionId"), "results": results}


def governance_assessment_history(paths: Paths, raw_digest: str,
                                  content_digest: str) -> list[dict]:
    """This WorkItem's recorded assessments, oldest evidence first and the
    current record last. See the block above for what counts and why."""
    entries: list[dict] = []
    if paths.evidence_dir.is_dir():
        for source in sorted(paths.evidence_dir.glob("governance-*.json")):
            if source.stat().st_size == 0:
                continue  # an id claimed and never filled; not evidence
            try:
                payload = json.loads(source.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise _history_invalid(source, f"it cannot be read: {exc}") from None
            if not isinstance(payload, dict):
                raise _history_invalid(source, "it is not an object")
            kind = payload.get("kind")
            if not isinstance(kind, str):
                raise _history_invalid(source, "it declares no kind of evidence")
            if kind != "governance":
                continue
            entries.append(_history_entry(
                payload.get("record"), source, raw_digest, content_digest))
    current = read_governance_record(paths)
    if current is not None:
        entries.append(_history_entry(
            current, paths.governance_file, raw_digest, content_digest))
    return entries


def overturned_assessment_results(paths: Paths) -> set[tuple[str, str]]:
    """The (check, content digest) pairs whose earlier FAIL a recorded dispute
    overturned. Only these are exempt from the flip rule; the original result
    stays in the history."""
    record = read_refinement_record(paths)
    if record is None:
        return set()
    return {(dispute["checkId"], dispute["contentDigest"])
            for entry in record["iterations"]
            for dispute in entry["disputeOutcomes"]}


def verdict_flips(paths: Paths, quality: dict, raw_digest: str,
                  content_digest: str) -> list[str]:
    """The checks this assessment answers PASS or NOT_APPLICABLE although an
    earlier assessment of the same content answered FAIL, and which no recorded
    dispute overturned."""
    history = governance_assessment_history(paths, raw_digest, content_digest)
    overturned = overturned_assessment_results(paths)
    flipped = []
    for check in quality["checks"]:
        if check["result"] == "FAIL":
            continue
        if (check["id"], content_digest) in overturned:
            continue
        if any(entry["contentDigest"] == content_digest
               and entry["results"].get(check["id"]) == "FAIL"
               for entry in history):
            flipped.append(check["id"])
    return flipped


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

    # Read the record this one replaces *before* it is overwritten.
    # A pure read, and the only thing it can produce is evidence.
    superseded = read_governance_record(paths)
    downgrade = governance_downgrade(superseded, risk)

    stamp = now_iso()
    # The binding is read and the documents hashed BEFORE an evidence file is
    # claimed. Reserving first left `evidence/governance-<id>.json` behind when
    # the assessment then refused `requirements_unbound` — an artifact of a
    # decision that was never taken, which is exactly what refusal atomicity
    # exists to prevent.
    sources, digest, raw_by_path = requirements_sources(paths, strict=True)
    # DEF-RR-001. Independent of whatever `scan` last recorded: a bound
    # source nobody ever ran `scan` on must not reach `init` unexamined
    # either. Before evidence is claimed, matching the refusal-atomicity
    # comment above — a flagged, unacknowledged document is not a decision
    # this assessment gets to make. `raw_by_path` threads through the exact
    # bytes just hashed above, so this never re-reads a bound source (V-01).
    offenders = unacknowledged_flagged_sources(paths, sources, raw_by_path)
    if offenders:
        raise content_unacknowledged_refusal(paths, offenders)
    content_digest = requirements_content_digest(raw_by_path)
    # Before `governance.json` is touched and before this assessment's own
    # evidence is claimed: a refused flip must leave the recorded verdict
    # byte-identical, because `governance_precondition` authorises progression
    # from the latest record alone. The attempt itself is recorded, as
    # evidence of another kind that is not part of the assessment history.
    flipped = verdict_flips(paths, quality, digest, content_digest)
    if flipped:
        attempt_id, attempt = reserve_evidence(
            paths, paths.evidence_dir, stamp,
            lambda eid: f"governance-flip-attempt-{eid}.json")
        write_atomic(attempt, json.dumps({
            "kind": "governance-flip-attempt",
            "status": "REFUSED",
            "executionId": attempt_id,
            "recordedAt": stamp,
            "workitem": paths.workitem,
            "flippedChecks": flipped,
            "contentDigest": content_digest,
            "input": {"path": relative, "document": document},
            "proposedQuality": quality,
        }, indent=2) + "\n")
        raise Refused(
            "quality_verdict_flip",
            "These checks failed in an earlier assessment of requirements with "
            f"exactly this content, and now read as passing: {', '.join(flipped)}. "
            "Unchanged requirements cannot have become adequate, so the earlier "
            "result stands and nothing was recorded as the verdict. Change the "
            "requirements substantively and assess again; an earlier result is "
            "overturned only by a recorded dispute.",
            {"workitem": paths.workitem, "flipped": flipped,
             "contentDigest": content_digest,
             "evidence": attempt.relative_to(paths.project_root).as_posix()},
        )
    # Claimed before `governance.json` is touched, so an id that cannot
    # be allocated refuses with nothing recorded.
    execution_id, evidence = reserve_evidence(
        paths, paths.evidence_dir, stamp,
        lambda eid: f"governance-{eid}.json")
    # ADR-011. The policy this WorkItem started under, pinned at the FIRST
    # governance record and carried forward verbatim by every later one.
    #
    # Carrying it forward is the whole mechanism, not bookkeeping: `assess`
    # rewrites this file wholesale, so a pin re-derived here would be erased
    # by the very sequence it exists to stop — relax the policy, re-assess,
    # omit. Taken from the superseded record read above when there is one.
    #
    # The merged document is stored, not just its SHA: the SHA can say the
    # policy changed, and only the document can say what it required.
    pinned_policy = (superseded or {}).get("pinnedPolicy") or {
        "policy": copy.deepcopy(effective["policy"]),
        "source": effective["source"],
        "sha256": effective["sha256"],
        "pinnedAt": stamp,
    }
    proposed_requirements = gate_requirements(
        consts, consts.flow(classification.get("flow")), classification,
        risk["finalLevel"], policy)

    record = {
        "governanceVersion": GOVERNANCE_RECORD_VERSION,
        "workitem": paths.workitem,
        "recordedAt": stamp,
        "executionId": execution_id,
        # `sources` and `digest` are the documents and their contents at the
        # moment of assessment; `bindingDigest` is *which* documents were
        # declared (ADR-012). Two different facts: editing a bound document and
        # re-binding to a different set both stale the assessment, and a reader
        # can tell which happened.
        "requirements": {
            "sources": sources,
            "digest": digest,
            # The presentation-neutral digest, which the verdict-flip rule
            # compares; `digest` above stays the raw one freshness uses.
            "contentDigest": content_digest,
            "bindingDigest": binding_digest(bound_sources(paths)),
        },
        "quality": quality,
        "classification": classification,
        "risk": risk,
        # §15's dispositions for the flow this record PROPOSES. Recorded as
        # evidence of what the assessment implied, never read back for a
        # decision: `init` binds the flow, and every later decision re-derives
        # the model against the bound one. Not to be confused with
        # `pinnedPolicy` below, which IS read back — the difference is that
        # these two are a flow-and-risk composite that a later re-assessment
        # legitimately replaces, while the pin is the policy document itself.
        "requiredGates": proposed_requirements["required_gates"],
        "omittableGates": proposed_requirements["omittable_gates"],
        # ADR-011, and the one part of this record a decision reads back.
        "pinnedPolicy": pinned_policy,
        # Always present, `null` when this assessment did not lower
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
        # Promoted out of `record` so a reader does not have to know
        # the record schema to see that a level was lowered.
        "downgrade": record.get("downgrade"),
        "fresh": freshness["fresh"],
        "recorded_digest": freshness["recorded_digest"],
        "current_digest": freshness["current_digest"],
        "requirements": freshness["current_sources"],
        # Why it is not fresh, when it is not: the documents changed, the
        # binding changed, or the record predates the binding entirely. Three
        # different remedies, so a reader is told which.
        "missing_sources": freshness["missing_sources"],
        "rebound": freshness["rebound"],
        "assessed_without_a_binding": freshness["assessed_without_a_binding"],
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

    model = requirement_model(consts, flow, classification, final_level,
                              effective, record)
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
        # ADR-011. `null` for a record written before the pin existed, which
        # is a different fact from "the built-in floor was pinned" and is
        # reported as such.
        "pinned_policy": model["pinned_policy"],
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
# The split is the governance one (Claude proposes, deterministic policy
# decides) and is recorded in ADR-005.

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
    it. The shape `bind_for_governance` established: there is no
    ``discovery_workitem_required`` refusal, because a non-raising bind always
    names a WorkItem.
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
    the flow it is traversing. There is no binding without a WorkItem, so the
    rule applies unconditionally.
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
# Project architecture memory — ADR-013
# --------------------------------------------------------------------------
#
# A WorkItem is the unit of execution; the repository is the unit of
# accumulated architectural knowledge. `.sdle/architecture/catalog.json` is
# that knowledge: which capabilities exist, which services own them, which
# boundaries are candidates rather than services, who owns which data, and the
# decision history that produced all of it.
#
# The split is the one ADR-001 draws and ADR-005 repeated for discovery.
# *"Does Risk Assessment deserve a service of its own?"* is judgement and
# belongs to the model. *"Is the outcome one of the five? Does the base
# revision still match? Does this candidate name a capability anybody knows?
# Would this delta leave two services claiming the same data?"* is mechanism
# and belongs here.
#
# Three properties this module exists to guarantee, none of which a prompt
# could:
#
#   * **No placement enters the catalog without a human.** `gate_architecture`
#     is required at every risk level, derived in `gate_requirements` rather
#     than declared in a policy dictionary, so no policy file can relax it.
#   * **Two WorkItems cannot silently overwrite each other.** Every proposal
#     pins the revision it was reasoned against; `apply` refuses
#     `architecture_catalog_stale` when the catalog has moved — unless the
#     move was this very decision, which is an idempotent replay and must
#     succeed.
#   * **The rendering a human approved is the record that is applied.** The
#     structured record and the Markdown carry the same decision id and
#     proposal digest, and `apply` re-verifies the rendering's SHA. A
#     hand-edited rendering fails rather than becoming architecture truth.

ARCHITECTURE_PHASE = "architecture_placement"
ARCHITECTURE_GATE_KEY = "gate_architecture"
# Named here rather than spelled at the two use sites: placement reads the
# constitution gate's decision and its registered artifact, and a literal in
# both places is the second source of truth invariant 7 forbids.
ARCHITECTURE_CONSTITUTION_GATE = "gate_constitution"

ARCHITECTURE_CATALOG_VERSION = 1
ARCHITECTURE_PROPOSAL_VERSIONS = ("1",)
ARCHITECTURE_RECORD_VERSION = "1"

ARCHITECTURE_APPLIED_EVENT = "architecture_applied"
ARCHITECTURE_ASSESSED_EVENT = "architecture_assessed"
ARCHITECTURE_REALIZED_EVENT = "architecture_realized"
ARCHITECTURE_ABANDONED_EVENT = "architecture_decision_abandoned"

# Exactly one primary outcome per placement. Closed, and ordered as ADR-013
# orders them: the four actionable ones first, the escape hatch last.
ARCHITECTURE_OUTCOMES = (
    "EXTEND_EXISTING_SERVICE",
    "CREATE_NEW_SERVICE",
    "KEEP_EMBEDDED_AND_MONITOR",
    "EXTRACT_EXISTING_CAPABILITY",
    "ARCHITECTURE_REVIEW_REQUIRED",
)
ARCHITECTURE_UNRESOLVED_OUTCOME = ARCHITECTURE_OUTCOMES[-1]
ARCHITECTURE_ACTIONABLE_OUTCOMES = ARCHITECTURE_OUTCOMES[:-1]

# The two outcomes that establish something a constitution governs: a new
# service boundary, or a transfer of one. Neither is defensible before the
# engineering rules exist (ADR-014).
ARCHITECTURE_CONSTITUTION_REQUIRED = (
    "CREATE_NEW_SERVICE", "EXTRACT_EXISTING_CAPABILITY",
)

CAPABILITY_STATUSES = ("EMERGING", "ESTABLISHED", "EMBEDDED", "EXTRACTING")
SERVICE_STATUSES = ("PLANNED", "IMPLEMENTED", "SUPERSEDED", "WITHDRAWN")
CANDIDATE_STATES = ("OPEN", "EXTRACTING", "EXTRACTED", "DISMISSED", "ABANDONED")
# `PLANNED` is the pre-realization state, exactly as it is for a service. It
# exists so the "one ACTIVE owner per datum" invariant stays literally true
# between `apply` and `realize`, when the old owner still owns the data and the
# new one does not yet.
DATA_OWNERSHIP_STATUSES = ("PLANNED", "ACTIVE", "SUPERSEDED", "WITHDRAWN")
DECISION_STATUSES = (
    "APPROVED_PENDING_IMPLEMENTATION", "IMPLEMENTED", "SUPERSEDED", "ABANDONED",
)

# Evidence, not a scorecard. ADR-013 is explicit that no numeric
# "microservice score" is computed, accepted or stored: a proposal addresses
# the dimensions its outcome makes relevant, and the engine checks that the
# named dimensions are ones it knows — never whether a finding is true.
ARCHITECTURE_DIMENSIONS = (
    "business_capability_cohesion",
    "business_responsibility",
    "domain_aggregate_invariants",
    "data_ownership",
    "transactional_boundaries",
    "lifecycle_independence",
    "change_coupling",
    "integration_dependencies",
    "security_boundary",
    "independent_scaling",
    "availability_differences",
    "deployment_independence",
    "existing_code_ownership",
    "related_workitems",
    "existing_adrs",
    "existing_candidates",
)

# Which dimensions an outcome must address. A floor, never a checklist to
# pass: "we considered data ownership and it does not separate" is a finding.
ARCHITECTURE_REQUIRED_DIMENSIONS = {
    "EXTEND_EXISTING_SERVICE": ("business_capability_cohesion", "data_ownership"),
    "CREATE_NEW_SERVICE": (
        "business_capability_cohesion", "data_ownership",
        "lifecycle_independence", "deployment_independence",
    ),
    "KEEP_EMBEDDED_AND_MONITOR": (
        "business_capability_cohesion", "data_ownership", "change_coupling",
    ),
    "EXTRACT_EXISTING_CAPABILITY": (
        "business_capability_cohesion", "data_ownership",
        "lifecycle_independence", "change_coupling", "existing_candidates",
    ),
    "ARCHITECTURE_REVIEW_REQUIRED": (),
}

ARCHITECTURE_PROPOSAL_SECTIONS = (
    "architectureProposalVersion", "baseArchitectureRevision", "placement",
)

CONSTITUTION_PRESENT, CONSTITUTION_ABSENT = "PRESENT", "ABSENT"


def empty_architecture_catalog() -> dict:
    """The shape an uninitialized repository is treated as having.

    Never written to disk by itself: `architecture show` reports
    ``initialized: false`` rather than materialising a file nobody asked for,
    and the first `apply` writes revision 1.
    """
    return {
        "catalogVersion": ARCHITECTURE_CATALOG_VERSION,
        "revision": 0,
        "updatedAt": None,
        "capabilities": [],
        "services": [],
        "candidates": [],
        "dataOwnership": [],
        "decisions": [],
    }


ARCHITECTURE_COLLECTIONS = (
    "capabilities", "services", "candidates", "dataOwnership", "decisions",
)


def _architecture_invalid(relative: str, detail: str, **data) -> IntegrityError:
    return IntegrityError(
        "architecture_catalog_invalid",
        f"{relative} cannot be used: {detail}. The architecture catalog is "
        "shared across every WorkItem in this repository, so a catalog the "
        "engine cannot trust is an integrity failure, never an empty one. "
        "Repair it by hand or restore it from version control; SDLE never "
        "rewrites it to make it parse.",
        {"path": relative, "detail": detail, **data},
    )


def validate_architecture_catalog(catalog, relative: str) -> dict:
    """Structural validation of a catalog document. Raises, or returns it.

    Deliberately total about *structure* and silent about *architecture*: it
    checks that ids are unique, that every reference resolves, that every enum
    is closed and that no datum has two active owners. It has no opinion on
    whether the architecture described is a good one.
    """
    if not isinstance(catalog, dict):
        raise _architecture_invalid(relative, "it is not a JSON object")

    version = catalog.get("catalogVersion")
    if version != ARCHITECTURE_CATALOG_VERSION:
        raise IntegrityError(
            "architecture_catalog_version_unsupported",
            f"{relative} declares catalogVersion {version!r}; this engine "
            f"reads {ARCHITECTURE_CATALOG_VERSION!r}. The catalog is left "
            "exactly as it is — there is no migration.",
            {"path": relative, "found": version,
             "supported": ARCHITECTURE_CATALOG_VERSION},
        )

    revision = catalog.get("revision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise _architecture_invalid(
            relative, f"revision {revision!r} is not a non-negative integer")

    for name in ARCHITECTURE_COLLECTIONS:
        value = catalog.get(name)
        if not isinstance(value, list) or any(
                not isinstance(entry, dict) for entry in value):
            raise _architecture_invalid(
                relative, f"'{name}' is not a list of objects")

    capability_ids = _architecture_unique_ids(
        relative, catalog["capabilities"], "id", "capability")
    service_ids = _architecture_unique_ids(
        relative, catalog["services"], "serviceId", "service")
    _architecture_unique_ids(relative, catalog["candidates"], "id", "candidate")
    _architecture_unique_ids(relative, catalog["decisions"], "id", "decision")

    _architecture_enum(relative, catalog["capabilities"], "status",
                       CAPABILITY_STATUSES, "capability")
    _architecture_enum(relative, catalog["services"], "status",
                       SERVICE_STATUSES, "service")
    _architecture_enum(relative, catalog["candidates"], "state",
                       CANDIDATE_STATES, "candidate")
    _architecture_enum(relative, catalog["dataOwnership"], "status",
                       DATA_OWNERSHIP_STATUSES, "dataOwnership")
    _architecture_enum(relative, catalog["decisions"], "status",
                       DECISION_STATUSES, "decision")
    _architecture_enum(relative, catalog["decisions"], "outcome",
                       ARCHITECTURE_OUTCOMES, "decision")

    # `introducedBy` is what the abandonment cascade selects on, so an entity
    # without one is an entity the first decision to re-state it could
    # withdraw. Required rather than defaulted: silently adopting an orphan
    # is the defect the field was added to prevent.
    for name, key in (("capabilities", "id"), ("services", "serviceId"),
                      ("candidates", "id"), ("dataOwnership", "data")):
        for entry in catalog[name]:
            if "introducedBy" not in entry:
                raise _architecture_invalid(
                    relative,
                    f"{name} entry {entry.get(key)!r} carries no "
                    "'introducedBy', so no decision owns it and an unrelated "
                    "WorkItem's restart could withdraw it")

    for capability in catalog["capabilities"]:
        owner = capability.get("ownerService")
        if owner is not None and owner not in service_ids:
            raise _architecture_invalid(
                relative,
                f"capability {capability.get('id')!r} names owner {owner!r}, "
                "which is not a service in this catalog")
    for candidate in catalog["candidates"]:
        if candidate.get("capability") not in capability_ids:
            raise _architecture_invalid(
                relative,
                f"candidate {candidate.get('id')!r} names capability "
                f"{candidate.get('capability')!r}, which this catalog does "
                "not define")
    for service in catalog["services"]:
        unknown = [name for name in (service.get("capabilities") or [])
                   if name not in capability_ids]
        if unknown:
            raise _architecture_invalid(
                relative,
                f"service {service.get('serviceId')!r} claims capability "
                + ", ".join(repr(name) for name in unknown)
                + ", which this catalog does not define")
    for entry in catalog["dataOwnership"]:
        if entry.get("ownerService") not in service_ids:
            raise _architecture_invalid(
                relative,
                f"data ownership for {entry.get('data')!r} names service "
                f"{entry.get('ownerService')!r}, which this catalog does not "
                "define")

    _architecture_single_active_owner(relative, catalog["dataOwnership"])
    return catalog


def _architecture_unique_ids(relative: str, entries: list, key: str,
                             label: str) -> set:
    seen: set = set()
    for entry in entries:
        value = entry.get(key)
        if not isinstance(value, str) or not value.strip():
            raise _architecture_invalid(
                relative, f"a {label} entry has no usable {key}")
        if value in seen:
            raise _architecture_invalid(
                relative, f"{label} id {value!r} appears more than once")
        seen.add(value)
    return seen


def _architecture_enum(relative: str, entries: list, key: str,
                       permitted: tuple, label: str) -> None:
    for entry in entries:
        value = entry.get(key)
        if value not in permitted:
            raise _architecture_invalid(
                relative,
                f"{label} {key} {value!r} is not one of "
                + ", ".join(permitted))


def _architecture_single_active_owner(relative: str, entries: list) -> None:
    """One ACTIVE owner per datum. The invariant the catalog exists to keep.

    `PLANNED` rows are excluded on purpose: between `apply` and `realize` the
    old owner still owns the data and the new one does not yet, and that is a
    correct state rather than a conflict.
    """
    owners: dict[str, str] = {}
    for entry in entries:
        if entry.get("status") != "ACTIVE":
            continue
        datum = entry.get("data")
        owner = entry.get("ownerService")
        if datum in owners and owners[datum] != owner:
            raise Refused(
                "architecture_conflicting_ownership",
                f"{relative} would leave {datum!r} owned by both "
                f"{owners[datum]!r} and {owner!r}. Exactly one service owns a "
                "datum at a time; the previous owner's entry must be "
                "superseded rather than left active.",
                {"data": datum, "owners": sorted({owners[datum], owner})},
            )
        owners[str(datum)] = str(owner)


def read_architecture_catalog(paths: Paths) -> dict | None:
    """The catalog, or ``None`` when the repository has none.

    Fail-closed in the same direction as ``read_governance_record``: absent is
    ``None`` and is a perfectly ordinary state; unreadable, unparseable or of
    another schema version is an integrity failure that leaves the file alone.
    """
    target = paths.architecture_catalog_file
    relative = architecture_catalog_relative(paths)
    if not target.is_file():
        return None
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise _architecture_invalid(relative, f"it cannot be read ({exc})") from None
    return validate_architecture_catalog(document, relative)


def architecture_catalog_relative(paths: Paths) -> str:
    """Derived from `Paths`, never rebuilt: the directory name has one home."""
    return (paths.architecture_catalog_file
            .relative_to(paths.project_root).as_posix())


def architecture_lock_relative(paths: Paths) -> str:
    return (paths.architecture_lock_file
            .relative_to(paths.project_root).as_posix())


def write_architecture_catalog(paths: Paths, catalog: dict) -> str:
    """Validate, then write atomically. Returns the repo-relative path.

    Validation runs on the *outgoing* document, not only the incoming one: a
    delta that would produce a catalog this engine could not read back is
    refused before it reaches disk, so `architecture show` can never be the
    command that discovers a corruption `apply` created.
    """
    relative = architecture_catalog_relative(paths)
    validate_architecture_catalog(catalog, relative)
    paths.architecture_dir.mkdir(parents=True, exist_ok=True)
    write_atomic(paths.architecture_catalog_file,
                 json.dumps(catalog, indent=2) + "\n")
    return relative


# Seconds. The lock is held for one read-check-write of a small JSON file, so
# a holder that has not released within the stale age is a dead process, not
# a slow one.
ARCHITECTURE_LOCK_TIMEOUT = 10.0
ARCHITECTURE_LOCK_STALE_AFTER = 60.0
ARCHITECTURE_LOCK_POLL = 0.05


@contextlib.contextmanager
def exclusive_file_lock(lock: Path, timeout: float, stale_after: float,
                        poll: float, refusal: "Callable[[], Refused]"):
    """Hold ``lock`` for the duration of the ``with`` block.

    One implementation of the engine's short exclusive locks, so the
    exclusive-create, the stale-break and the refuse-don't-hang behaviour
    exist once. The file is created with ``os.open(O_CREAT | O_EXCL)``; a lock
    older than ``stale_after`` is broken; one still fresh after ``timeout``
    raises what ``refusal`` builds, and a caller that was refused never
    releases a lock it did not take.
    """
    lock.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            handle = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > stale_after:
                with contextlib.suppress(FileNotFoundError):
                    lock.unlink()
                continue
            if time.monotonic() >= deadline:
                raise refusal()
            time.sleep(poll)
            continue
        break
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as owner:
            owner.write(f"{os.getpid()} {now_iso()}\n")
        yield
    finally:
        with contextlib.suppress(FileNotFoundError):
            lock.unlink()


@contextlib.contextmanager
def architecture_catalog_lock(paths: Paths):
    """Serialise one read-check-write of the shared catalog.

    The revision check is an optimistic-concurrency check, and a check is only
    as good as the interval between it and the write it guards. The atomic
    replace keeps a reader from seeing half a file; it does not stop two WorkItems that
    both read revision N from both passing `baseRevision == N` and the second
    replacement erasing the first decision. So each catalog mutation re-reads
    the catalog *under* this lock, makes its revision and replay decision
    there, writes, and lets go.

    Not a lifecycle lock: nothing else takes it, it is never held across a
    gate or a phase, and a reader (`architecture show`) never waits for it.
    A lock left behind by a process that died is broken once it is older than
    `ARCHITECTURE_LOCK_STALE_AFTER`; one that is still fresh after
    `ARCHITECTURE_LOCK_TIMEOUT` is a refusal, not a hang.
    """
    def refusal() -> Refused:
        return Refused(
            "architecture_catalog_locked",
            "Another process is updating the architecture catalog "
            f"and has held {architecture_catalog_relative(paths)}'s "
            "lock for longer than expected. Nothing was written; "
            "retry in a moment.",
            {"lock": architecture_lock_relative(paths),
             "waited_seconds": ARCHITECTURE_LOCK_TIMEOUT})

    with exclusive_file_lock(
            paths.architecture_lock_file, ARCHITECTURE_LOCK_TIMEOUT,
            ARCHITECTURE_LOCK_STALE_AFTER, ARCHITECTURE_LOCK_POLL, refusal):
        yield


REFINEMENT_LOCK_TIMEOUT = 10.0
REFINEMENT_LOCK_STALE_AFTER = 60.0
REFINEMENT_LOCK_POLL = 0.05


@contextlib.contextmanager
def refinement_mutex(paths: Paths):
    """Serialise one command's check-and-write against the other parties that
    read requirements ownership: every mutating `refinement` command,
    `requirements bind` and `init`.

    A mutex serialises only the parties that take it, so each of them does.
    It is held for one engine command - never across a model call or a human
    decision - which is what makes breaking a stale one safe. Readers never
    wait for it.
    """
    def refusal() -> Refused:
        return Refused(
            "refinement_transaction_locked",
            "Another command is changing requirements ownership or "
            "refinement state and has held "
            f"{paths.refinement_lock_file.relative_to(paths.project_root).as_posix()}"
            " for longer than expected. Nothing was written; retry in a moment.",
            {"lock": paths.refinement_lock_file
             .relative_to(paths.project_root).as_posix(),
             "waited_seconds": REFINEMENT_LOCK_TIMEOUT})

    with exclusive_file_lock(
            paths.refinement_lock_file, REFINEMENT_LOCK_TIMEOUT,
            REFINEMENT_LOCK_STALE_AFTER, REFINEMENT_LOCK_POLL, refusal):
        yield


def architecture_digest(payload) -> str:
    """A deterministic content digest for a validated proposal.

    Sorted keys and no whitespace, so two machines that validated the same
    proposal agree on the digest and an idempotent replay is recognisable.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_constitution_status(paths: Paths, state: dict,
                                consts: Constants) -> dict:
    """PRESENT / ABSENT, resolved by the engine rather than claimed.

    Two routes, in priority order:

      1. this WorkItem decided `gate_constitution` **and** the constitution
         the gate is registered against is on disk;
      2. a readable repository baseline whose `references.constitution`
         resolves — the `ITERATIVE` case, where the flow never runs
         `constitution_draft` at all and reporting ABSENT would be a lie.

    The gate test is "decided", not "approved": `gate_constitution` sits in the
    built-in policy's `required_gates_always` today, so it cannot be omitted —
    but the effective policy is read from a file, and this rule should not
    quietly depend on that staying true.
    """
    decision = (state.get("approvals") or {}).get(ARCHITECTURE_CONSTITUTION_GATE)
    if decision:
        resolved, _ = resolve_artifact_path(
            state, consts, ARCHITECTURE_CONSTITUTION_GATE, paths)
        if resolved and (paths.project_root / resolved).is_file():
            return {"status": CONSTITUTION_PRESENT, "source": "workitem",
                    "path": resolved}

    try:
        baseline = read_baseline(paths)
    except IntegrityError:
        baseline = None
    reference = ((baseline or {}).get("references") or {}).get("constitution")
    if isinstance(reference, dict) and reference.get("path"):
        if (paths.project_root / reference["path"]).is_file():
            return {"status": CONSTITUTION_PRESENT, "source": "baseline",
                    "path": reference["path"]}

    return {"status": CONSTITUTION_ABSENT, "source": None, "path": None}


def _placement_invalid(detail: str, **data) -> Refused:
    return Refused(
        "architecture_placement_invalid",
        f"The architecture proposal cannot be accepted: {detail}. Run "
        "`architecture schema` for the contract; nothing has been written.",
        {"detail": detail, **data},
    )


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _str_entries(value) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value
            if isinstance(item, str) and item.strip()]


def read_architecture_input(target: Path, relative: str) -> dict:
    """Read and shape-check the proposal document. Writes nothing."""
    if not target.is_file():
        raise _placement_invalid(
            f"{relative} does not exist", path=relative)
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise _placement_invalid(
            f"{relative} is not readable JSON ({exc})", path=relative) from None
    if not isinstance(document, dict):
        raise _placement_invalid(
            f"{relative} is not a JSON object", path=relative)
    version = document.get("architectureProposalVersion")
    if version not in ARCHITECTURE_PROPOSAL_VERSIONS:
        raise _placement_invalid(
            f"architectureProposalVersion {version!r} is not one of "
            + ", ".join(repr(v) for v in ARCHITECTURE_PROPOSAL_VERSIONS),
            path=relative, found=version)
    missing = [key for key in ARCHITECTURE_PROPOSAL_SECTIONS
               if key not in document]
    if missing:
        raise _placement_invalid(
            "the envelope is missing " + ", ".join(missing),
            path=relative, missing=missing)
    return document


def evaluate_architecture_proposal(document: dict, paths: Paths, state: dict,
                                   consts: Constants, catalog: dict | None,
                                   relative: str) -> dict:
    """Validate a proposal against the catalog and the constitution rules.

    Returns the **validated placement**, normalised — the value the digest is
    taken over and the record stores. Every refusal here fires before the
    caller's first write, mirroring `discovery assess`: there is nothing to
    remediate in a document the engine could not parse, and a half-validated
    placement must never become the thing that authorises leaving the phase.
    """
    known = catalog or empty_architecture_catalog()
    initialized = catalog is not None

    revision = document.get("baseArchitectureRevision")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 0:
        raise _placement_invalid(
            f"baseArchitectureRevision {revision!r} is not a non-negative "
            "integer", path=relative)

    placement = document.get("placement")
    if not isinstance(placement, dict):
        raise _placement_invalid("'placement' is not an object", path=relative)

    technology_decision = bool(document.get("introducesTechnologyDecision"))
    if "introducesTechnologyDecision" in placement:
        raise _placement_invalid(
            "introducesTechnologyDecision belongs to the proposal envelope, "
            "not to 'placement' — it is a statement about the proposal. "
            "Run `architecture schema` for the shape",
            path=relative)

    outcome = placement.get("outcome")
    if outcome not in ARCHITECTURE_OUTCOMES:
        raise _placement_invalid(
            f"outcome {outcome!r} is not one of "
            + ", ".join(ARCHITECTURE_OUTCOMES),
            path=relative, found=outcome, permitted=list(ARCHITECTURE_OUTCOMES))

    bootstrap = _validate_bootstrap_delta(
        document.get("bootstrapDelta"), paths, initialized, relative)

    capability = placement.get("capability")
    if not isinstance(capability, dict) or not _text(capability.get("id")):
        raise _placement_invalid(
            "placement.capability must name the business capability this "
            "WorkItem is about", path=relative)

    service_ids = {entry["serviceId"] for entry in known["services"]}
    service_ids |= {entry["serviceId"] for entry in bootstrap["services"]}
    capability_ids = {entry["id"] for entry in known["capabilities"]}
    capability_ids |= {entry["id"] for entry in bootstrap["capabilities"]}

    current_owner = _text(placement.get("currentOwner")) or None
    target_owner = _text(placement.get("targetOwner")) or None
    affected = _str_entries(placement.get("affectedServices"))

    dimensions = _validate_dimensions(placement.get("dimensions"), outcome,
                                      relative)
    rationale = _text(placement.get("rationale"))
    if not rationale and outcome != ARCHITECTURE_UNRESOLVED_OUTCOME:
        raise _placement_invalid(
            "placement.rationale is empty; a decision with no stated reason "
            "is not evidence a later WorkItem can use", path=relative)

    confidence = _text(placement.get("confidence")).upper() or "MEDIUM"
    if confidence not in ("HIGH", "MEDIUM", "LOW"):
        raise _placement_invalid(
            f"confidence {confidence!r} is not HIGH, MEDIUM or LOW",
            path=relative)

    candidates = _validate_candidates(placement.get("candidates"), relative)
    ownership = _validate_data_ownership(placement.get("dataOwnership"),
                                         relative)
    open_questions = _str_entries(placement.get("openQuestions"))

    # A placement may *create* a service, so the service it introduces counts
    # as known for the reference check — otherwise every CREATE_NEW_SERVICE
    # would refuse on its own target. What it may not do is reference a
    # service it neither creates nor finds.
    introduced = {target_owner} if outcome in (
        "CREATE_NEW_SERVICE", "EXTRACT_EXISTING_CAPABILITY") else set()
    introduced.discard(None)
    _require_known_services(
        [current_owner] + affected + [entry["ownerService"] for entry in ownership]
        + [entry["currentOwner"] for entry in candidates],
        service_ids | introduced, relative)
    for entry in candidates:
        if entry["capability"] not in capability_ids | {capability["id"].strip()}:
            raise Refused(
                "architecture_capability_unknown",
                f"Candidate {entry['id']!r} names capability "
                f"{entry['capability']!r}, which neither the catalog nor this "
                "proposal defines.",
                {"candidate": entry["id"], "capability": entry["capability"]})

    _validate_outcome_requirements(
        outcome, current_owner, target_owner, known,
        candidates, ownership, placement, open_questions, relative)

    constitution = resolve_constitution_status(paths, state, consts)
    # The bootstrap's services are *observed existing* architecture, not new
    # boundaries this WorkItem establishes — so they count as known for the
    # constitution rule, exactly as they do for the reference check above.
    _enforce_constitution_rule(
        outcome, constitution, technology_decision, ownership, known,
        bootstrap, target_owner, relative)

    validated = {
        "outcome": outcome,
        "capability": {
            "id": capability["id"].strip(),
            "name": _text(capability.get("name")) or capability["id"].strip(),
            "description": _text(capability.get("description")),
        },
        "currentOwner": current_owner,
        "targetOwner": target_owner,
        "affectedServices": sorted(set(affected) | (introduced - {None})),
        "dimensions": dimensions,
        "rationale": rationale,
        "migrationImplications": _text(placement.get("migrationImplications")),
        "integrationImpact": _text(placement.get("integrationImpact")),
        "dataOwnership": ownership,
        "candidates": candidates,
        "reevaluateWhen": _str_entries(placement.get("reevaluateWhen")),
        "confidence": confidence,
        "openQuestions": open_questions,
        "relatedWorkItems": _str_entries(placement.get("relatedWorkItems")),
        # Envelope-level, beside `bootstrapDelta`: it is a statement about the
        # proposal rather than about the placement, and it is the one ADR-014
        # input the engine cannot derive for itself. Normalised into the
        # validated placement so the record carries it, but READ from the
        # document.
        "introducesTechnologyDecision": technology_decision,
    }
    return {
        "placement": validated,
        "bootstrapDelta": bootstrap if bootstrap["declared"] else None,
        "baseRevision": revision,
        "constitution": constitution,
    }


def _require_known_services(names, service_ids: set, relative: str) -> None:
    unknown = sorted({name for name in names if name and name not in service_ids})
    if unknown:
        raise Refused(
            "architecture_service_unknown",
            "The proposal references service(s) neither the catalog nor this "
            "proposal defines: " + ", ".join(unknown) + ". A placement may "
            "create a service, but it may not silently assume one.",
            {"unknown": unknown, "known": sorted(service_ids),
             "path": relative})


def _validate_dimensions(raw, outcome: str, relative: str) -> list[dict]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise _placement_invalid("placement.dimensions is not a list",
                                 path=relative)
    findings: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise _placement_invalid(
                "every dimension entry must be an object", path=relative)
        name = _text(entry.get("dimension"))
        if name not in ARCHITECTURE_DIMENSIONS:
            raise _placement_invalid(
                f"dimension {name!r} is not one of the declared evidence "
                "dimensions", path=relative, found=name,
                permitted=list(ARCHITECTURE_DIMENSIONS))
        finding = _text(entry.get("finding"))
        if not finding:
            raise _placement_invalid(
                f"dimension {name!r} carries no finding; naming a dimension "
                "without saying what it showed is not evidence",
                path=relative)
        findings.append({"dimension": name, "finding": finding})

    named = {entry["dimension"] for entry in findings}
    missing = [name for name in ARCHITECTURE_REQUIRED_DIMENSIONS[outcome]
               if name not in named]
    if missing:
        raise _placement_invalid(
            f"outcome {outcome} requires a finding for " + ", ".join(missing)
            + " — a finding may say the dimension does not separate, but it "
              "may not be absent", path=relative, missing=missing)
    return findings


def _validate_candidates(raw, relative: str) -> list[dict]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise _placement_invalid("placement.candidates is not a list",
                                 path=relative)
    entries: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise _placement_invalid("every candidate must be an object",
                                     path=relative)
        identifier = _text(entry.get("id"))
        capability = _text(entry.get("capability"))
        owner = _text(entry.get("currentOwner"))
        if not identifier or not capability or not owner:
            raise _placement_invalid(
                "a candidate needs id, capability and currentOwner",
                path=relative)
        state_value = _text(entry.get("state")).upper() or "OPEN"
        if state_value not in CANDIDATE_STATES:
            raise _placement_invalid(
                f"candidate state {state_value!r} is not one of "
                + ", ".join(CANDIDATE_STATES), path=relative)
        entries.append({
            "id": identifier,
            "capability": capability,
            "currentOwner": owner,
            "state": state_value,
            "evidence": _str_entries(entry.get("evidence")),
            "reevaluateWhen": _str_entries(entry.get("reevaluateWhen")),
        })
    return entries


def _validate_data_ownership(raw, relative: str) -> list[dict]:
    if raw is None:
        raw = []
    if not isinstance(raw, list):
        raise _placement_invalid("placement.dataOwnership is not a list",
                                 path=relative)
    entries: list[dict] = []
    for entry in raw:
        if not isinstance(entry, dict):
            raise _placement_invalid("every dataOwnership entry must be an "
                                     "object", path=relative)
        datum = _text(entry.get("data"))
        owner = _text(entry.get("ownerService"))
        if not datum or not owner:
            raise _placement_invalid(
                "a dataOwnership entry needs data and ownerService",
                path=relative)
        entries.append({
            "data": datum,
            "ownerService": owner,
            "viaCapability": _text(entry.get("viaCapability")) or None,
            "embedded": bool(entry.get("embedded")),
        })
    return entries


def _validate_outcome_requirements(outcome, current_owner, target_owner,
                                   known, candidates, ownership,
                                   placement, open_questions,
                                   relative: str) -> None:
    """The per-outcome floor. One place, so no caller re-derives it."""
    # A service a WorkItem may extend is one that is live or on its way
    # there. A `WITHDRAWN` or `SUPERSEDED` boundary is *reclaimed* by a new
    # placement, never extended by one.
    extendable = {entry["serviceId"] for entry in known["services"]
                  if entry.get("status") in ("PLANNED", "IMPLEMENTED")}
    live = {entry["serviceId"] for entry in known["services"]
            if entry.get("status") == "IMPLEMENTED"}

    if outcome == "EXTEND_EXISTING_SERVICE":
        if not current_owner or current_owner != target_owner:
            raise _placement_invalid(
                "EXTEND_EXISTING_SERVICE means the capability stays where it "
                "is: currentOwner and targetOwner must name the same existing "
                "service", path=relative)
        if known["services"] and current_owner not in extendable:
            raise _placement_invalid(
                f"service {current_owner!r} is not implemented or planned, so "
                "there is nothing to extend. A withdrawn or superseded "
                "boundary is reclaimed by CREATE_NEW_SERVICE, not extended",
                path=relative)

    elif outcome == "CREATE_NEW_SERVICE":
        if not target_owner:
            raise _placement_invalid(
                "CREATE_NEW_SERVICE must name the targetOwner it creates",
                path=relative)
        if target_owner in live:
            raise _placement_invalid(
                f"service {target_owner!r} already exists; the outcome for an "
                "existing owner is EXTEND_EXISTING_SERVICE", path=relative)

    elif outcome == "KEEP_EMBEDDED_AND_MONITOR":
        if not current_owner:
            raise _placement_invalid(
                "KEEP_EMBEDDED_AND_MONITOR must name the service the "
                "capability stays inside", path=relative)
        if not candidates:
            raise _placement_invalid(
                "KEEP_EMBEDDED_AND_MONITOR records a boundary worth watching, "
                "so it must record at least one candidate", path=relative)
        if any(not entry["reevaluateWhen"] for entry in candidates):
            raise _placement_invalid(
                "every candidate needs reevaluateWhen conditions; a candidate "
                "nobody will revisit is not monitoring", path=relative)

    elif outcome == "EXTRACT_EXISTING_CAPABILITY":
        if not current_owner or not target_owner:
            raise _placement_invalid(
                "EXTRACT_EXISTING_CAPABILITY must name both the current owner "
                "and the service being extracted", path=relative)
        if current_owner == target_owner:
            raise _placement_invalid(
                "EXTRACT_EXISTING_CAPABILITY moves the capability out of its "
                "current owner; currentOwner and targetOwner cannot match",
                path=relative)
        if not _text(placement.get("migrationImplications")):
            raise _placement_invalid(
                "an extraction must state its migration implications: "
                "existing behaviour has to keep working", path=relative)
        if not ownership:
            raise _placement_invalid(
                "an extraction moves data ownership, so the proposal must say "
                "which data moves", path=relative)

    elif outcome == ARCHITECTURE_UNRESOLVED_OUTCOME and not open_questions:
        raise _placement_invalid(
            "ARCHITECTURE_REVIEW_REQUIRED must name the questions a human has "
            "to resolve", path=relative)


def _enforce_constitution_rule(outcome: str, constitution: dict,
                               technology_decision: bool, ownership: list,
                               known: dict, bootstrap: dict | None,
                               target_owner: str | None,
                               relative: str) -> None:
    """ADR-014's availability rule. Outcome-sensitive, never blanket.

    A legacy defect fix in a repository that never had a constitution is a
    legitimate thing to run; establishing a service boundary in one is not.
    ADR-014 names **three** things such a WorkItem may not do without one, and
    all three are checked here: a new service boundary, a transfer of
    ownership, and a new technology or platform decision. Two of them are
    derivable from the proposal and the catalog, which is why they are checked
    rather than asked for.
    """
    if constitution["status"] == CONSTITUTION_PRESENT:
        return
    if outcome == ARCHITECTURE_UNRESOLVED_OUTCOME:
        return

    def refuse(detail: str) -> Refused:
        return Refused(
            "architecture_constitution_required",
            f"{outcome} {detail}, and this repository has no approved "
            "constitution — neither this WorkItem's own nor one referenced by "
            "a sound baseline. Establish the engineering rules first, or "
            f"record {ARCHITECTURE_UNRESOLVED_OUTCOME} and resolve it with a "
            "human.",
            {"outcome": outcome, "constitution": CONSTITUTION_ABSENT,
             "detail": detail, "path": relative})

    if outcome in ARCHITECTURE_CONSTITUTION_REQUIRED:
        raise refuse("establishes or transfers a service boundary")

    if technology_decision:
        raise refuse("declares that it introduces a new technology or "
                     "platform decision")

    existing = {entry["serviceId"] for entry in known.get("services") or []}
    existing |= {entry["serviceId"]
                 for entry in (bootstrap or {}).get("services") or []}
    if target_owner and target_owner not in existing:
        raise refuse(f"would establish a new service boundary "
                     f"({target_owner})")

    active = {entry["data"]: entry["ownerService"]
              for entry in known.get("dataOwnership") or []
              if entry.get("status") == "ACTIVE"}
    moved = sorted({entry["data"] for entry in ownership
                    if entry["data"] in active
                    and active[entry["data"]] != entry["ownerService"]})
    if moved:
        raise refuse("would transfer ownership of " + ", ".join(moved))


def _validate_bootstrap_delta(raw, paths: Paths, initialized: bool,
                              relative: str) -> dict:
    """Optional, evidence-backed description of architecture that already exists.

    Two rules carry the whole of ADR-013's bootstrap caution:

      * it is only meaningful while the catalog is uninitialized — once the
        repository has a catalog, "what already exists" is the catalog;
      * every evidence entry cites at least one path that is really there, so
        a bootstrap cannot invent a service. It still cannot *assert* that a
        directory is a service — that is the author's claim, exactly as an
        OBSERVED discovery finding is.
    """
    empty = {"declared": False, "basis": None, "capabilities": [],
             "services": [], "dataOwnership": [], "evidence": []}
    if raw is None:
        return empty
    if not isinstance(raw, dict):
        raise _placement_invalid("bootstrapDelta is not an object",
                                 path=relative)
    if initialized:
        raise _placement_invalid(
            "bootstrapDelta describes architecture that already exists and is "
            "only accepted while the catalog is uninitialized; this "
            "repository already has one", path=relative)

    basis = _text(raw.get("basis")).upper()
    if basis not in ("DISCOVERY", "BASELINE"):
        raise _placement_invalid(
            "bootstrapDelta.basis must be DISCOVERY or BASELINE — the two "
            "evidence sources ADR-013 admits", path=relative, found=basis)

    evidence = raw.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise _placement_invalid(
            "bootstrapDelta must carry evidence", path=relative)
    records: list[dict] = []
    for entry in evidence:
        if not isinstance(entry, dict):
            raise _placement_invalid("every bootstrap evidence entry must be "
                                     "an object", path=relative)
        statement = _text(entry.get("statement"))
        cited = _str_entries(entry.get("paths"))
        if not statement or not cited:
            raise _placement_invalid(
                "bootstrap evidence needs a statement and at least one path",
                path=relative)
        absent = [item for item in cited
                  if not _inside_repository(paths, item)]
        if absent:
            raise _placement_invalid(
                "bootstrap evidence cites path(s) that are not in this "
                "repository: " + ", ".join(absent), path=relative,
                absent=absent)
        records.append({"statement": statement, "paths": cited})

    services = []
    for entry in raw.get("services") or []:
        identifier = _text((entry or {}).get("serviceId"))
        if not identifier:
            raise _placement_invalid(
                "every bootstrap service needs a serviceId", path=relative)
        services.append({
            "serviceId": identifier,
            "name": _text(entry.get("name")) or identifier,
            "repositoryPaths": _str_entries(entry.get("repositoryPaths")),
            "capabilities": _str_entries(entry.get("capabilities")),
            "ownedData": _str_entries(entry.get("ownedData")),
            "dependencies": _str_entries(entry.get("dependencies")),
        })

    capabilities = []
    for entry in raw.get("capabilities") or []:
        identifier = _text((entry or {}).get("id"))
        if not identifier:
            raise _placement_invalid(
                "every bootstrap capability needs an id", path=relative)
        status = _text(entry.get("status")).upper() or "ESTABLISHED"
        if status not in CAPABILITY_STATUSES:
            raise _placement_invalid(
                f"bootstrap capability status {status!r} is not one of "
                + ", ".join(CAPABILITY_STATUSES), path=relative)
        capabilities.append({
            "id": identifier,
            "name": _text(entry.get("name")) or identifier,
            "description": _text(entry.get("description")),
            "status": status,
            "ownerService": _text(entry.get("ownerService")) or None,
        })

    ownership = _validate_data_ownership(raw.get("dataOwnership"), relative)

    # Contract §5 promises reference checking at `assess`. Without it a
    # dangling bootstrap reference survives validation, the human approves the
    # gate, and `write_architecture_catalog` then raises an *integrity*
    # failure (exit 3) for what was a malformed proposal — the wrong exit code,
    # at the wrong moment, to the wrong person.
    declared_services = {entry["serviceId"] for entry in services}
    declared_capabilities = {entry["id"] for entry in capabilities}
    for entry in capabilities:
        if entry["ownerService"] and entry["ownerService"] not in declared_services:
            raise Refused(
                "architecture_service_unknown",
                f"Bootstrap capability {entry['id']!r} names owner "
                f"{entry['ownerService']!r}, which the bootstrap does not "
                "declare.",
                {"capability": entry["id"], "service": entry["ownerService"],
                 "declared": sorted(declared_services)})
    for entry in services:
        unknown = [name for name in entry["capabilities"]
                   if name not in declared_capabilities]
        if unknown:
            raise Refused(
                "architecture_capability_unknown",
                f"Bootstrap service {entry['serviceId']!r} claims capability "
                + ", ".join(unknown) + ", which the bootstrap does not declare.",
                {"service": entry["serviceId"], "unknown": unknown})
    for entry in ownership:
        if entry["ownerService"] not in declared_services:
            raise Refused(
                "architecture_service_unknown",
                f"Bootstrap data ownership for {entry['data']!r} names "
                f"{entry['ownerService']!r}, which the bootstrap does not "
                "declare.",
                {"data": entry["data"], "service": entry["ownerService"],
                 "declared": sorted(declared_services)})

    return {"declared": True, "basis": basis, "capabilities": capabilities,
            "services": services, "dataOwnership": ownership,
            "evidence": records}


def _inside_repository(paths: Paths, relative: str) -> bool:
    """Is ``relative`` a path that really is inside this repository?

    `project_root / item` silently discards `project_root` for an absolute
    `item`, and `../..` walks out of the tree — so the plain `.exists()` the
    evidence check used to do did not check what its refusal message claimed.
    """
    candidate = Path(relative)
    if candidate.is_absolute():
        return False
    try:
        resolved = (paths.project_root / candidate).resolve()
        resolved.relative_to(paths.project_root.resolve())
    except (OSError, ValueError):
        return False
    return resolved.exists()


# -- the WorkItem placement record ------------------------------------------


def architecture_record_relative(paths: Paths) -> str:
    return f"{paths.runtime_relative}/{paths.architecture_placement_file.name}"


def architecture_rendering_relative(paths: Paths) -> str:
    return (paths.architecture_placement_rendering
            .relative_to(paths.project_root).as_posix())


def architecture_record_is_disposed(paths: Paths, record: dict) -> bool:
    """Has the engine already disposed of the decision this record names?

    `restart` and `reset` mark a decision `ABANDONED` in the catalog but leave
    the WorkItem's record and rendering where they are — deleting them would
    destroy the evidence of what was decided. So "a record exists" stops being
    the same question as "this WorkItem has a live placement", and a gate that
    asked only the first would put a voided decision in front of a human for
    approval (ADR-013, invariant 4).
    """
    try:
        catalog = read_architecture_catalog(paths)
    except IntegrityError:
        return False  # reported by its own refusal, not silently by this one
    decision = next((entry for entry in (catalog or {}).get("decisions") or []
                     if entry.get("id") == record.get("decisionId")), None)
    return bool(decision) and decision.get("status") in (
        "ABANDONED", "SUPERSEDED")


def read_architecture_record(paths: Paths) -> dict | None:
    """The WorkItem's validated placement, or ``None``.

    A malformed record is an integrity failure rather than an absence, for the
    reason ``read_governance_record`` gives: "absent" would let a corrupt file
    read as "not assessed yet" and be silently overwritten.
    """
    target = paths.architecture_placement_file
    if not target.is_file():
        return None
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise IntegrityError(
            "architecture_record_invalid",
            f"{architecture_record_relative(paths)} cannot be read: {exc}. "
            "Re-run `architecture assess --input <path>`.",
            {"path": str(target), "error": str(exc)}) from None
    if not isinstance(record, dict) or record.get(
            "architecturePlacementVersion") != ARCHITECTURE_RECORD_VERSION:
        raise IntegrityError(
            "architecture_record_invalid",
            f"{architecture_record_relative(paths)} is not a placement record "
            f"of version {ARCHITECTURE_RECORD_VERSION}.",
            {"path": str(target)})
    if record.get("workitem") != paths.workitem:
        raise IntegrityError(
            "architecture_record_invalid",
            f"{architecture_record_relative(paths)} belongs to WorkItem "
            f"{record.get('workitem')!r}, not to {paths.workitem!r}. A "
            "WorkItem's gate never approves another WorkItem's placement.",
            {"path": str(target), "found": record.get("workitem"),
             "expected": paths.workitem})
    return record


def require_architecture_record(paths: Paths) -> dict:
    record = read_architecture_record(paths)
    if record is None:
        raise Refused(
            "architecture_placement_missing",
            f"WorkItem '{paths.workitem}' has no architecture placement. Run "
            "`architecture assess --input <path>` at "
            f"{ARCHITECTURE_PHASE}; `architecture schema` reports what the "
            "proposal must contain.",
            {"workitem": paths.workitem,
             "path": architecture_record_relative(paths)})
    if architecture_record_is_disposed(paths, record):
        raise Refused(
            "architecture_placement_missing",
            f"WorkItem '{paths.workitem}' holds placement "
            f"{record['decisionId']}, which the engine has already disposed "
            "of — a restart, a reset or a rerun superseded it. Re-run "
            f"{ARCHITECTURE_PHASE} so this WorkItem proposes afresh.",
            {"workitem": paths.workitem, "decision": record["decisionId"],
             "path": architecture_record_relative(paths)})
    return record


def next_decision_id(catalog: dict, workitem: str) -> str:
    """`AP-<workitem>-<NNN>`, counting this WorkItem's catalog decisions.

    Minted at `assess` and stored, never re-minted by `apply` — that is what
    makes a crashed `apply` replayable rather than duplicable. A rerun
    placement that was never applied reuses the number, which is harmless
    because nothing with that id ever reached the catalog.
    """
    prefix = f"AP-{workitem}-"
    taken = [entry["id"] for entry in catalog.get("decisions") or []
             if str(entry.get("id", "")).startswith(prefix)]
    return f"{prefix}{len(taken) + 1:03d}"


def render_placement(record: dict) -> str:
    """The gated artifact: the same decision, in the form a human reads.

    Generated from the record and never hand-maintained, so the two cannot
    drift. `apply` re-checks this file's SHA against the record before the
    catalog is touched, which is what stops an edited rendering from becoming
    architecture truth.
    """
    placement = record["placement"]
    lines = [
        f"# Architecture Placement — {record['workitem']}",
        "",
        "<!-- Generated by `sdle architecture assess`. Do not edit: the gate "
        "verifies this file's SHA-256 against the structured record. -->",
        "",
        f"- **Decision id:** `{record['decisionId']}`",
        f"- **Proposal digest:** `{record['proposalDigest']}`",
        f"- **Catalog revision reasoned against:** {record['baseRevision']}",
        f"- **Constitution status:** {record['constitutionStatus']}",
        f"- **Confidence:** {placement['confidence']}",
        "",
        "## Business capability",
        "",
        f"**{placement['capability']['name']}** (`{placement['capability']['id']}`)",
        "",
        placement["capability"]["description"] or "_No description supplied._",
        "",
        "## Decision",
        "",
        f"**{placement['outcome']}**",
        "",
        f"- Current owner: {placement['currentOwner'] or '_none_'}",
        f"- Target owner: {placement['targetOwner'] or '_unchanged_'}",
        "- Affected services: "
        + (", ".join(placement["affectedServices"]) or "_none_"),
        "",
        "## Rationale",
        "",
        placement["rationale"] or "_Not applicable._",
        "",
        "## Evidence dimensions considered",
        "",
    ]
    if placement["dimensions"]:
        lines.append("| Dimension | Finding |")
        lines.append("|---|---|")
        for entry in placement["dimensions"]:
            finding = entry["finding"].replace("|", "\\|")
            lines.append(f"| `{entry['dimension']}` | {finding} |")
    else:
        lines.append("_None recorded._")

    lines += ["", "## Data ownership impact", ""]
    if placement["dataOwnership"]:
        for entry in placement["dataOwnership"]:
            embedded = " (embedded)" if entry["embedded"] else ""
            via = f" via `{entry['viaCapability']}`" if entry["viaCapability"] else ""
            lines.append(
                f"- `{entry['data']}` → `{entry['ownerService']}`{via}{embedded}")
    else:
        lines.append("_No change._")

    lines += ["", "## Candidates affected", ""]
    if placement["candidates"]:
        for entry in placement["candidates"]:
            lines.append(
                f"- `{entry['id']}` — `{entry['capability']}` inside "
                f"`{entry['currentOwner']}` ({entry['state']})")
            for condition in entry["reevaluateWhen"]:
                lines.append(f"  - re-evaluate when: {condition}")
    else:
        lines.append("_None._")

    lines += [
        "", "## Integration impact", "",
        placement["integrationImpact"] or "_None identified._",
        "", "## Migration implications", "",
        placement["migrationImplications"] or "_None: no behaviour moves._",
        "", "## Re-evaluation conditions", "",
    ]
    lines += ([f"- {item}" for item in placement["reevaluateWhen"]]
              or ["_None recorded._"])

    lines += ["", "## Known related WorkItems", ""]
    lines += ([f"- {item}" for item in placement["relatedWorkItems"]]
              or ["_None visible from the bound requirements._"])

    lines += ["", "## Open architecture questions", ""]
    lines += ([f"- {item}" for item in placement["openQuestions"]]
              or ["_None._"])

    if record.get("bootstrapDelta"):
        bootstrap = record["bootstrapDelta"]
        lines += ["", "## Existing architecture recorded at bootstrap", "",
                  f"Basis: **{bootstrap['basis']}**", ""]
        # Everything `apply_bootstrap_delta` writes is shown here, because
        # the human approves this rendering and the catalog receives the
        # structured delta: a value only the second carries was never
        # approved.
        none = "none"
        for entry in bootstrap["services"]:
            lines.append(
                f"- service `{entry['serviceId']}` ({entry['name']}) — "
                + (", ".join(entry["repositoryPaths"]) or "no paths cited"))
            lines.append("  - capabilities: "
                         + (", ".join(f"`{c}`" for c in entry["capabilities"])
                            or none))
            lines.append("  - owned data: "
                         + (", ".join(f"`{d}`" for d in entry["ownedData"])
                            or none))
            lines.append("  - dependencies: "
                         + (", ".join(f"`{d}`" for d in entry["dependencies"])
                            or none))
        for entry in bootstrap["capabilities"]:
            lines.append(
                f"- capability `{entry['id']}` ({entry['name']}, "
                f"{entry['status']}), owned by "
                f"`{entry['ownerService'] or none}`: {entry['description']}")
        for entry in bootstrap["dataOwnership"]:
            lines.append(
                f"- data `{entry['data']}` owned by `{entry['ownerService']}`"
                f" via `{entry['viaCapability'] or none}`"
                + (" (embedded)" if entry["embedded"] else ""))
        lines += ["", "Evidence:", ""]
        for entry in bootstrap["evidence"]:
            lines.append(f"- {entry['statement']} — "
                         + ", ".join(f"`{p}`" for p in entry["paths"]))

    lines.append("")
    return "\n".join(lines)


# -- catalog mutation -------------------------------------------------------


def _upsert(entries: list[dict], key: str, value: str, fields: dict,
            introduced_by: str | None = None) -> dict:
    """Create or update an entity, recording which decision *introduced* it.

    `decisionReference` says "the last decision that touched this"; it moves.
    `introducedBy` says "the decision this entity would not exist without";
    it is written once, at creation, and never again. The abandonment cascade
    reads the second, because disposing of a decision may only dispose of what
    that decision brought into being — a candidate another WorkItem created
    and this one merely re-stated is not this one's to withdraw (ADR-013).
    """
    for entry in entries:
        if entry.get(key) == value:
            entry.update(fields)
            entry.setdefault("introducedBy", introduced_by)
            return entry
    entry = {key: value, **fields, "introducedBy": introduced_by}
    entries.append(entry)
    return entry


def apply_bootstrap_delta(catalog: dict, bootstrap: dict | None,
                          decision_id: str) -> None:
    """Fold observed existing architecture into an uninitialized catalog."""
    if not bootstrap:
        return
    for entry in bootstrap["services"]:
        _upsert(catalog["services"], "serviceId", entry["serviceId"], {
            "name": entry["name"],
            "status": "IMPLEMENTED",
            "capabilities": entry["capabilities"],
            "repositoryPaths": entry["repositoryPaths"],
            "ownedData": entry["ownedData"],
            "dependencies": entry["dependencies"],
            "decisionReference": decision_id,
        }, introduced_by=decision_id)
    for entry in bootstrap["capabilities"]:
        _upsert(catalog["capabilities"], "id", entry["id"], {
            "name": entry["name"],
            "description": entry["description"],
            "status": entry["status"],
            "ownerService": entry["ownerService"],
            "relatedWorkItems": [],
            "evidence": [item["statement"] for item in bootstrap["evidence"]],
        }, introduced_by=decision_id)
    for entry in bootstrap["dataOwnership"]:
        _upsert(catalog["dataOwnership"], "data", entry["data"], {
            "ownerService": entry["ownerService"],
            "viaCapability": entry["viaCapability"],
            "embedded": entry["embedded"],
            "status": "ACTIVE",
            "decisionReference": decision_id,
        }, introduced_by=decision_id)


# Which capability status each outcome leaves behind. Declared rather than
# branched, so "what does this outcome do to the capability" has one answer.
# `EXTEND_EXISTING_SERVICE` is deliberately absent: extending a capability
# says nothing about whether it is embedded. Writing `ESTABLISHED` there
# would clear an `EMBEDDED` status while its candidate was still `OPEN`, so
# the capability and the candidate would describe different architectures.
# An absent key leaves the existing status alone.
OUTCOME_CAPABILITY_STATUS = {
    "CREATE_NEW_SERVICE": "ESTABLISHED",
    "KEEP_EMBEDDED_AND_MONITOR": "EMBEDDED",
    "EXTRACT_EXISTING_CAPABILITY": "EXTRACTING",
}


def apply_architecture_delta(catalog: dict, record: dict, stamp: str) -> dict:
    """Fold an approved placement into the catalog. Pure: returns a new dict.

    Nothing here decides anything — every value was validated at `assess` and
    approved by a human at the gate. What this function owns is that the
    *shape* of the resulting catalog is still one the engine can read back,
    which `write_architecture_catalog` re-checks before the bytes land.
    """
    catalog = copy.deepcopy(catalog)
    placement = record["placement"]
    decision_id = record["decisionId"]
    workitem = record["workitem"]
    outcome = placement["outcome"]

    apply_bootstrap_delta(catalog, record.get("bootstrapDelta"), decision_id)

    superseded = abandon_or_supersede_prior(
        catalog, workitem, "superseded", stamp, exclude=decision_id)

    owner = placement["targetOwner"] or placement["currentOwner"]
    if outcome in ("CREATE_NEW_SERVICE", "EXTRACT_EXISTING_CAPABILITY"):
        existing = next((entry for entry in catalog["services"]
                         if entry["serviceId"] == placement["targetOwner"]), None)
        # A WITHDRAWN service is reclaimable: a later WorkItem may take up a
        # boundary an abandoned decision had planned (ADR-013).
        status = "PLANNED" if not existing or existing["status"] in (
            "WITHDRAWN", "PLANNED") else existing["status"]
        _upsert(catalog["services"], "serviceId", placement["targetOwner"], {
            "name": (existing or {}).get("name") or placement["targetOwner"],
            "status": status,
            "capabilities": sorted(set(
                ((existing or {}).get("capabilities") or [])
                + [placement["capability"]["id"]])),
            "repositoryPaths": (existing or {}).get("repositoryPaths") or [],
            "ownedData": sorted(set(
                ((existing or {}).get("ownedData") or [])
                + [entry["data"] for entry in placement["dataOwnership"]])),
            "dependencies": (existing or {}).get("dependencies") or [],
            "decisionReference": decision_id,
        }, introduced_by=decision_id)
    elif owner:
        existing = next((entry for entry in catalog["services"]
                         if entry["serviceId"] == owner), None)
        if existing is not None:
            existing["capabilities"] = sorted(set(
                (existing.get("capabilities") or [])
                + [placement["capability"]["id"]]))

    capability_id = placement["capability"]["id"]
    known = next((entry for entry in catalog["capabilities"]
                  if entry["id"] == capability_id), None)
    _upsert(catalog["capabilities"], "id", capability_id, {
        "name": placement["capability"]["name"],
        "description": placement["capability"]["description"]
                       or (known or {}).get("description", ""),
        "status": OUTCOME_CAPABILITY_STATUS.get(
            outcome, (known or {}).get("status") or "EMERGING"),
        "ownerService": owner,
        "relatedWorkItems": sorted(set(
            ((known or {}).get("relatedWorkItems") or []) + [workitem])),
        "evidence": (known or {}).get("evidence") or [],
    }, introduced_by=decision_id)

    for entry in placement["candidates"]:
        _upsert(catalog["candidates"], "id", entry["id"], {
            "capability": entry["capability"],
            "currentOwner": entry["currentOwner"],
            "state": ("EXTRACTING" if outcome == "EXTRACT_EXISTING_CAPABILITY"
                      else entry["state"]),
            "evidence": sorted(set(entry["evidence"] + [workitem])),
            "reevaluateWhen": entry["reevaluateWhen"],
            "decisionReference": decision_id,
        }, introduced_by=decision_id)

    # New ownership enters PLANNED: until `realize` runs, the previous owner
    # still owns the datum and the invariant "one ACTIVE owner" stays true.
    for entry in placement["dataOwnership"]:
        already = next((row for row in catalog["dataOwnership"]
                        if row["data"] == entry["data"]
                        and row["ownerService"] == entry["ownerService"]), None)
        if already is not None and already["status"] == "ACTIVE":
            already.update({"viaCapability": entry["viaCapability"],
                            "embedded": entry["embedded"],
                            "decisionReference": decision_id})
            continue
        if already is not None:
            already.update({"status": "PLANNED",
                            "viaCapability": entry["viaCapability"],
                            "embedded": entry["embedded"],
                            "decisionReference": decision_id})
            continue
        catalog["dataOwnership"].append({
            "data": entry["data"],
            "ownerService": entry["ownerService"],
            "viaCapability": entry["viaCapability"],
            "embedded": entry["embedded"],
            "status": "PLANNED",
            "decisionReference": decision_id,
            "introducedBy": decision_id,
        })

    catalog["decisions"].append({
        "id": decision_id,
        "workItem": workitem,
        "outcome": outcome,
        "baseRevision": record["baseRevision"],
        "appliedRevision": catalog["revision"] + 1,
        "proposalDigest": record["proposalDigest"],
        "renderedArtifact": record["renderedArtifact"],
        "renderedSha256": record["renderedSha256"],
        "status": "APPROVED_PENDING_IMPLEMENTATION",
        "appliedAt": stamp,
        "realizedAt": None,
        "abandonedAt": None,
        "abandonedBy": None,
        "supersedes": superseded,
    })
    catalog["revision"] += 1
    catalog["updatedAt"] = stamp
    return catalog


def abandon_or_supersede_prior(catalog: dict, workitem: str, disposition: str,
                               stamp: str, exclude: str | None = None) -> list[str]:
    """Dispose of this WorkItem's still-pending decisions. Append-only.

    History is never rewritten: the decision keeps its id, its digest and its
    applied revision, and gains a disposition. A `PLANNED` service it created
    becomes `WITHDRAWN` rather than disappearing, so a later WorkItem can
    reclaim the boundary instead of colliding with a ghost (ADR-013).
    """
    # `SUPERSEDED` rather than `ABANDONED` for a rerun: the decision was not
    # walked away from, it was replaced by a later one for the same WorkItem,
    # and the two read differently in `architecture show`. Both dispositions
    # are audited by their caller.
    status = "ABANDONED" if disposition != "superseded" else "SUPERSEDED"
    touched: list[str] = []
    for decision in catalog.get("decisions") or []:
        if decision.get("workItem") != workitem:
            continue
        if decision.get("status") != "APPROVED_PENDING_IMPLEMENTATION":
            continue
        if exclude and decision.get("id") == exclude:
            continue
        decision["status"] = status
        decision["abandonedAt"] = stamp
        decision["abandonedBy"] = disposition
        touched.append(decision["id"])

    if not touched:
        return []
    # `introducedBy`, not `decisionReference`: only what this decision
    # brought into being is its to dispose of.
    for service in catalog.get("services") or []:
        if (service.get("introducedBy") in touched
                and service.get("status") == "PLANNED"):
            service["status"] = "WITHDRAWN"
    for candidate in catalog.get("candidates") or []:
        if candidate.get("introducedBy") in touched:
            candidate["state"] = "ABANDONED"
    for entry in catalog.get("dataOwnership") or []:
        if (entry.get("introducedBy") in touched
                and entry.get("status") == "PLANNED"):
            entry["status"] = "WITHDRAWN"
    return touched


def abandon_architecture_decisions(paths: Paths, disposition: str) -> dict | None:
    """`_abandon_architecture_decisions_locked`, under the catalog lock.

    No catalog means nothing to dispose of, and nothing to lock: taking the
    lock would create `.sdle/architecture/` in a repository that never had a
    placement approved.
    """
    if not (paths.project_root / architecture_catalog_relative(paths)).exists():
        return None
    with architecture_catalog_lock(paths):
        return _abandon_architecture_decisions_locked(paths, disposition)


def _abandon_architecture_decisions_locked(paths: Paths,
                                           disposition: str) -> dict | None:
    """Engine-driven abandonment for `restart` and `reset` (ADR-013).

    Returns ``None`` when there was nothing to dispose of, so the callers stay
    silent in the overwhelmingly common case. `reset` deletes `audit.md`, so
    for that disposition the catalog entry is the only durable record there
    will ever be — which is exactly why it is a catalog write.
    """
    catalog = read_architecture_catalog(paths)
    if catalog is None or not paths.workitem:
        return None
    stamp = now_iso()
    touched = abandon_or_supersede_prior(
        catalog, paths.workitem, disposition, stamp)
    if not touched:
        return None
    catalog["revision"] += 1
    catalog["updatedAt"] = stamp
    relative = write_architecture_catalog(paths, catalog)
    return {"decisions": touched, "revision": catalog["revision"],
            "catalog": relative, "disposition": disposition}


def realize_architecture_decision(catalog: dict, decision: dict,
                                  capability_id: str | None,
                                  stamp: str) -> dict:
    """Turn an approved placement into a realized one. Pure.

    ``capability_id`` is this decision's own capability, and it is a required
    argument rather than a lookup because the catalog is shared: an unfiltered
    sweep would close another WorkItem's in-flight extraction and leave its
    later placement reasoning from a state nobody decided.
    """
    catalog = copy.deepcopy(catalog)
    decision_id = decision["id"]
    target = next(entry for entry in catalog["decisions"]
                  if entry["id"] == decision_id)

    for service in catalog["services"]:
        if (service.get("decisionReference") == decision_id
                and service.get("status") == "PLANNED"):
            service["status"] = "IMPLEMENTED"

    for entry in catalog["dataOwnership"]:
        if entry.get("decisionReference") != decision_id:
            continue
        if entry.get("status") != "PLANNED":
            continue
        for other in catalog["dataOwnership"]:
            if (other is not entry and other.get("data") == entry.get("data")
                    and other.get("status") == "ACTIVE"):
                other["status"] = "SUPERSEDED"
        entry["status"] = "ACTIVE"

    if target["outcome"] == "EXTRACT_EXISTING_CAPABILITY":
        for candidate in catalog["candidates"]:
            if candidate.get("state") == "EXTRACTING" and candidate.get(
                    "decisionReference") == decision_id:
                candidate["state"] = "EXTRACTED"
        for capability in catalog["capabilities"]:
            if (capability.get("id") == capability_id
                    and capability.get("status") == "EXTRACTING"):
                capability["status"] = "ESTABLISHED"

    target["status"] = "IMPLEMENTED"
    target["realizedAt"] = stamp
    catalog["revision"] += 1
    catalog["updatedAt"] = stamp
    return catalog


# -- integrity of the structured ↔ rendered pair ----------------------------


def architecture_binding_precondition(paths: Paths, record: dict,
                                      resolved: str | None = None) -> str:
    """The rendering the human is approving *is* the record being applied.

    A pure reader, called from `gate_precondition_hook` before the first
    write. Three things have to agree, and all three are cheap:

      * the rendering exists where the record says it does;
      * its SHA-256 is the one the record captured at `assess`;
      * it still prints the record's decision id and proposal digest.

    The third looks redundant next to the second and is not: it is what makes
    the failure *legible*. A SHA mismatch alone says "something changed"; the
    header check says which decision the file on disk claims to be.
    """
    relative = record.get("renderedArtifact")
    if resolved and relative and relative != resolved:
        raise Refused(
            "architecture_artifact_binding_invalid",
            f"The gate fingerprinted {resolved}, but the placement record "
            f"names {relative}. They must be the same file.",
            {"workitem": paths.workitem, "gate_artifact": resolved,
             "record_artifact": relative})
    target = paths.project_root / relative if relative else None
    if not relative or target is None or not target.is_file():
        raise Refused(
            "architecture_artifact_binding_invalid",
            f"The placement record names {relative or 'no rendering'}, which "
            "is not on disk. Re-run `architecture assess --input <path>`; the "
            "rendering is generated from the record and is never written by "
            "hand.",
            {"workitem": paths.workitem, "rendered": relative})

    current = sha256_file(target)
    if current != record.get("renderedSha256"):
        raise Refused(
            "architecture_artifact_binding_invalid",
            f"{relative} has changed since it was generated. The structured "
            "record and the rendering are one decision, bound by digest: an "
            "edited rendering is not an architecture decision. Re-run "
            "`architecture assess --input <path>`.",
            {"workitem": paths.workitem, "rendered": relative,
             "recorded_sha": record.get("renderedSha256"),
             "current_sha": current})

    body = target.read_text(encoding="utf-8", errors="replace")
    for label, value in (("decision id", record.get("decisionId")),
                         ("proposal digest", record.get("proposalDigest"))):
        if not value or value not in body:
            raise Refused(
                "architecture_artifact_binding_invalid",
                f"{relative} does not carry the record's {label} "
                f"({value!r}).",
                {"workitem": paths.workitem, "rendered": relative,
                 "missing": label})
    return relative


def architecture_requirements_precondition(paths: Paths, record: dict) -> None:
    """A placement is approved only against the requirements it was read from.

    A pure reader, called wherever the binding check is, and on leaving the
    placement phase. The placement reads the WorkItem's bound requirement
    documents; if they have changed since, the decision a human is about to
    approve was reasoned from text that no longer says what it said. Governance
    going stale does not cover this: re-assessing clears it, and the old
    placement would then be approved against the new documents. A shared-
    document edit by another WorkItem is the case that makes it real.

    A decision already in the catalog is a replay, not an approval, and is
    never refused here: it entered under the documents it was approved
    against, and refusing it would leave an approved gate unable to finish
    after a crash. A record that carries no requirements basis cannot be shown
    to match anything, so it fails closed.
    """
    catalog = read_architecture_catalog(paths)
    for entry in (catalog or {}).get("decisions") or []:
        if (entry.get("id") == record.get("decisionId")
                and entry.get("proposalDigest") == record.get("proposalDigest")):
            return None

    sources, digest, _ = requirements_sources(paths)
    recorded_digest = record.get("requirementsDigest")
    if recorded_digest and recorded_digest == digest:
        return None

    recorded = {entry["path"]: entry["sha256"]
                for entry in record.get("requirementsSources") or []}
    now = {entry["path"]: entry["sha256"] for entry in sources}
    changed = sorted(name for name in set(recorded) | set(now)
                     if recorded.get(name) != now.get(name))
    if not recorded_digest:
        detail = ("it records no requirements basis, so it cannot be shown "
                  "to match the documents now bound")
    else:
        detail = ("these bound documents differ from the ones it was reasoned "
                  f"from: {', '.join(changed)}")
    raise Refused(
        "architecture_requirements_stale",
        f"The architecture placement for WorkItem '{paths.workitem}' is "
        f"stale: {detail}. A placement is approved only against the "
        "requirements it was read from. Re-run "
        f"`architecture assess --input <path>` against the current documents, "
        "review the new rendering, and approve that.",
        {"workitem": paths.workitem, "changed": changed,
         "recorded_digest": recorded_digest, "current_digest": digest})


def architecture_outcome_precondition(record: dict) -> None:
    """`ARCHITECTURE_REVIEW_REQUIRED` is not an approvable placement.

    It means the evidence is insufficient or contradictory. A human resolves
    the questions and the phase is re-run into one of the four actionable
    outcomes; approving the escape hatch would put "we do not know" into the
    catalog as though it were a decision.
    """
    outcome = (record.get("placement") or {}).get("outcome")
    if outcome != ARCHITECTURE_UNRESOLVED_OUTCOME:
        return
    raise Refused(
        "architecture_decision_unresolved",
        "This placement is ARCHITECTURE_REVIEW_REQUIRED, which is not an "
        "approvable outcome: it records that the evidence does not yet "
        "support a placement. Resolve the open questions with the "
        "architecture owner, then reject this gate and re-run "
        f"{ARCHITECTURE_PHASE} so the artifact ends in one of: "
        + ", ".join(ARCHITECTURE_ACTIONABLE_OUTCOMES) + ".",
        {"outcome": outcome,
         "questions": (record.get("placement") or {}).get("openQuestions") or [],
         "actionable": list(ARCHITECTURE_ACTIONABLE_OUTCOMES)})


def architecture_precondition(paths: Paths, state: dict) -> None:
    """A WorkItem may not leave `architecture_placement` without a record.

    The same shape as `discovery_precondition`, and enforced from
    ``apply_advance`` for the same reason: `skip` exists for a *failed*
    generation step, and a placement that was never produced is exactly that
    case — but a specification drafted outside an approved boundary is the
    thing ADR-013 exists to prevent, so `skip` may not walk past it either.
    """
    if (state or {}).get("current_phase") != ARCHITECTURE_PHASE:
        return None
    record = read_architecture_record(paths)
    if record is not None and not architecture_record_is_disposed(
            paths, record):
        # A human should not be shown a placement already known to be stale.
        architecture_requirements_precondition(paths, record)
        return None
    raise Refused(
        "architecture_placement_missing",
        f"WorkItem '{paths.workitem}' is at {ARCHITECTURE_PHASE} and has no "
        "live placement, so the workflow cannot leave the phase — a record "
        "the engine has already disposed of (by restart, reset or a rerun) "
        "does not count, or a human would be shown a voided decision to "
        "approve. Run `architecture assess --input <path>`; `architecture "
        "schema` reports what the proposal must contain.",
        {"workitem": paths.workitem, "phase": ARCHITECTURE_PHASE,
         "path": architecture_record_relative(paths),
         "disposed": record is not None})


# -- commands ---------------------------------------------------------------


def bind_for_architecture(args, paths: Paths) -> Paths:
    """`architecture` is runtime-free at the group level so `schema` and
    `show` answer without a WorkItem — the catalog is the repository's, not a
    WorkItem's. Its WorkItem-scoped members bind here, through the ladder."""
    return bind_workitem(paths, args.workitem)


def cmd_architecture_schema(args, paths: Paths) -> int:
    """The closed vocabulary, emitted rather than restated. Writes nothing."""
    emit("architecture schema", {
        "input_versions": list(ARCHITECTURE_PROPOSAL_VERSIONS),
        "envelope": list(ARCHITECTURE_PROPOSAL_SECTIONS),
        "outcomes": list(ARCHITECTURE_OUTCOMES),
        "actionable_outcomes": list(ARCHITECTURE_ACTIONABLE_OUTCOMES),
        "unresolved_outcome": ARCHITECTURE_UNRESOLVED_OUTCOME,
        "dimensions": list(ARCHITECTURE_DIMENSIONS),
        "required_dimensions": {k: list(v) for k, v
                                in ARCHITECTURE_REQUIRED_DIMENSIONS.items()},
        "constitution_required_outcomes":
            list(ARCHITECTURE_CONSTITUTION_REQUIRED),
        "statuses": {
            "capability": list(CAPABILITY_STATUSES),
            "service": list(SERVICE_STATUSES),
            "candidate": list(CANDIDATE_STATES),
            "dataOwnership": list(DATA_OWNERSHIP_STATUSES),
            "decision": list(DECISION_STATUSES),
        },
        "catalog_version": ARCHITECTURE_CATALOG_VERSION,
        "record_version": ARCHITECTURE_RECORD_VERSION,
        "bootstrap_bases": ["DISCOVERY", "BASELINE"],
        # Envelope-level fields, beside `placement` and `bootstrapDelta`.
        # `introducesTechnologyDecision` is the one ADR-014 input the engine
        # cannot derive, so the prompt layer reads its location from here
        # rather than from prose.
        "envelope_fields": {
            "architectureProposalVersion": "one of input_versions",
            "baseArchitectureRevision":
                "the revision `architecture show` reported",
            "introducesTechnologyDecision":
                "true when this WorkItem chooses a technology or platform "
                "the project has not already committed to; consulted only "
                "when no constitution resolves",
            "bootstrapDelta": "optional; only while the catalog is "
                              "uninitialized",
            "placement": "required; exactly one primary outcome",
        },
        "enforced": [
            "exactly one primary outcome, from the declared five",
            "the outcome's required evidence dimensions each carry a finding",
            "every service and capability referenced is one the catalog "
            "knows or this proposal introduces",
            "a new service boundary or an ownership transfer needs an "
            "approved constitution",
            "bootstrap evidence cites paths that exist, and is accepted only "
            "while the catalog is uninitialized",
            "the delta leaves exactly one active owner per datum",
        ],
        "not_enforced": [
            "whether the placement is the architecturally right one",
            "whether a stated finding is true of the code it describes",
            "whether the evidence considered is complete",
        ],
        "never": [
            "a numeric microservice score is neither computed nor accepted",
        ],
    })
    return EXIT_OK


def cmd_architecture_show(args, paths: Paths) -> int:
    """The repository's architecture memory. Read-only, WorkItem-free.

    Valid on an empty catalog and **invents nothing**: an uninitialized
    repository reports `initialized: false`, not a fabricated architecture.
    """
    catalog = read_architecture_catalog(paths)
    relative = architecture_catalog_relative(paths)
    if catalog is None:
        emit("architecture show", {
            "initialized": False, "revision": 0, "path": relative,
            "catalog": None,
            "message": "This repository has no architecture catalog yet. The "
                       "first approved placement creates it.",
        })
        return EXIT_OK

    decisions = catalog["decisions"]
    emit("architecture show", {
        "initialized": True,
        "revision": catalog["revision"],
        "path": relative,
        "catalog": catalog,
        "counts": {name: len(catalog[name]) for name in ARCHITECTURE_COLLECTIONS},
        "decisions_by_status": {
            status: [entry["id"] for entry in decisions
                     if entry.get("status") == status]
            for status in DECISION_STATUSES
        },
    })
    return EXIT_OK


def cmd_architecture_assess(args, paths: Paths) -> int:
    """Validate a placement proposal and record it, with its rendering.

    Every refusal fires before the first write, so a refused assess leaves the
    record, the rendering, `audit.md` and `state.json` exactly as they were —
    `discovery assess`'s rule, for `discovery assess`'s reason.
    """
    consts = load_constants(paths)
    paths = bind_for_architecture(args, paths)
    state = read_state(paths)

    # An approved placement has already entered the shared catalog, and the
    # decision id is minted from what the catalog holds — so re-assessing
    # afterwards would rebind this WorkItem's record to an id nothing applied,
    # and `realize` would then find no decision to realize. Remediation runs
    # through `gate reject`, which clears the approval and reopens the phase.
    # The test is the *decision*, not the presence of an entry. `gate
    # reject` writes a truthy `{"decision": "rejected"}` and nothing clears
    # it, so guarding on presence turned a rejection into a dead end — the
    # one path `gate-protocol.md`, `architecture-placement.md` and the
    # troubleshooting guide all name as the remedy, and the only exit
    # `ARCHITECTURE_REVIEW_REQUIRED` has.
    decided = (state.get("approvals") or {}).get(ARCHITECTURE_GATE_KEY) or {}
    if isinstance(decided, dict) and decided.get("decision") in (
            "approved", GATE_OMITTED_DECISION):
        raise Refused(
            "architecture_decision_conflict",
            f"{ARCHITECTURE_GATE_KEY} has already been decided for "
            f"'{paths.workitem}', and its decision is in the repository "
            "catalog. Re-assessing now would replace this WorkItem's record "
            "with a decision nobody approved. Reject the gate first, which "
            f"reopens {ARCHITECTURE_PHASE} through the remediation path.",
            {"workitem": paths.workitem, "gate": ARCHITECTURE_GATE_KEY,
             "decision": decided.get("decision")})

    target = Path(args.input)
    if not target.is_absolute():
        target = paths.project_root / args.input
    relative = args.input.replace(os.sep, "/")

    catalog = read_architecture_catalog(paths)
    document = read_architecture_input(target, relative)
    evaluation = evaluate_architecture_proposal(
        document, paths, state, consts, catalog, relative)

    stamp = now_iso()
    # Reserved BEFORE the first `write_atomic`, exactly as `discovery assess`
    # does it: `reserve_evidence` can refuse `execution_id_collision`, and a
    # refusal after the rendering had been replaced would leave the record's
    # `renderedSha256` describing a file that no longer exists in that form.
    # The bytes this placement is reasoned from, read before anything is
    # claimed or written, so a WorkItem with no binding, or whose bound
    # documents are gone, refuses here with nothing recorded. They go into the
    # record because the placement reads the bound requirements, and without
    # them nothing can tell a placement derived from the documents as they are
    # from one derived from documents that have since changed.
    requirement_sources, requirements_digest, _ = requirements_sources(
        paths, strict=True)
    execution_id, evidence = reserve_evidence(
        paths, paths.evidence_dir, stamp,
        lambda eid: f"architecture-{eid}.json")
    decision_id = next_decision_id(
        catalog or empty_architecture_catalog(), paths.workitem)
    # The whole of what `apply` will fold into the shared catalog: the
    # placement AND the bootstrap delta. Digesting the placement alone let two
    # proposals that mutate the catalog differently share one identity.
    digest = architecture_digest({
        "placement": evaluation["placement"],
        "bootstrapDelta": evaluation["bootstrapDelta"],
    })
    rendered_relative = architecture_rendering_relative(paths)

    record = {
        "architecturePlacementVersion": ARCHITECTURE_RECORD_VERSION,
        "workitem": paths.workitem,
        "recordedAt": stamp,
        "decisionId": decision_id,
        "proposalDigest": digest,
        "baseRevision": evaluation["baseRevision"],
        "catalogRevisionNow": (catalog or {}).get("revision", 0),
        "constitutionStatus": evaluation["constitution"]["status"],
        "constitutionSource": evaluation["constitution"]["source"],
        "placement": evaluation["placement"],
        "bootstrapDelta": evaluation["bootstrapDelta"],
        "renderedArtifact": rendered_relative,
        "renderedSha256": None,
        "requirementsDigest": requirements_digest,
        "requirementsSources": requirement_sources,
    }

    paths.architecture_placement_rendering.parent.mkdir(
        parents=True, exist_ok=True)
    write_atomic(paths.architecture_placement_rendering, render_placement(record))
    record["renderedSha256"] = sha256_file(paths.architecture_placement_rendering)
    record["executionId"] = execution_id
    write_atomic(paths.architecture_placement_file,
                 json.dumps(record, indent=2) + "\n")
    write_atomic(evidence, json.dumps({
        "kind": "architecture_placement",
        "executionId": execution_id,
        "recordedAt": stamp,
        "workitem": paths.workitem,
        "input": {"path": relative, "document": document},
        "record": record,
    }, indent=2) + "\n")

    append_audit(
        paths, state,
        phase=state.get("current_phase") or ARCHITECTURE_PHASE,
        event=ARCHITECTURE_ASSESSED_EVENT,
        message=(
            f"Architecture placement recorded: {evaluation['placement']['outcome']} "
            f"for {evaluation['placement']['capability']['id']} "
            f"(decision {decision_id}, base revision "
            f"{evaluation['baseRevision']}, constitution "
            f"{evaluation['constitution']['status']})."
        ),
        artifact=rendered_relative,
        artifact_sha=record["renderedSha256"],
        evidence_id=execution_id,
    )
    save_state(paths, state, args.session)

    emit("architecture assess", {
        "workitem": paths.workitem,
        "decisionId": decision_id,
        "proposalDigest": digest,
        "outcome": evaluation["placement"]["outcome"],
        "baseRevision": evaluation["baseRevision"],
        "constitutionStatus": evaluation["constitution"]["status"],
        "record": architecture_record_relative(paths),
        "rendered": rendered_relative,
        "renderedSha256": record["renderedSha256"],
        "evidence": evidence.relative_to(paths.project_root).as_posix(),
        "bootstrap": bool(evaluation["bootstrapDelta"]),
        "approvable": evaluation["placement"]["outcome"]
                      != ARCHITECTURE_UNRESOLVED_OUTCOME,
    })
    return EXIT_OK


def architecture_apply(paths: Paths, record: dict, stamp: str) -> dict:
    """`_architecture_apply_locked`, under the catalog lock.

    The catalog is re-read inside the lock, so the revision and replay
    decisions are made against the file that is about to be replaced, not
    against whatever it held when the caller started.
    """
    with architecture_catalog_lock(paths):
        return _architecture_apply_locked(paths, record, stamp)


def _architecture_apply_locked(paths: Paths, record: dict, stamp: str) -> dict:
    """Fold an approved placement into the catalog, or explain why not.

    The replay rule is the whole of ADR-013's replay safety. A crashed `apply` that had already
    written revision N must be retryable: the same decision id with the same
    proposal digest is *this* decision, already applied, and re-applying it
    would bump the revision a second time and make every other WorkItem's
    pinned base stale for no reason. The same id with a *different* digest is
    a different decision wearing the same name, which is a conflict and never
    a replay.
    """
    decision_id = record["decisionId"]
    catalog = read_architecture_catalog(paths)
    stored = next((entry for entry in (catalog or {}).get("decisions") or []
                   if entry.get("id") == decision_id), None)

    if stored is not None:
        if stored.get("proposalDigest") != record["proposalDigest"]:
            raise Refused(
                "architecture_decision_conflict",
                f"Decision {decision_id} is already in the catalog with a "
                "different proposal digest. Two different placements cannot "
                "share one decision id; re-run "
                f"{ARCHITECTURE_PHASE} so this WorkItem proposes afresh.",
                {"decision": decision_id,
                 "applied_digest": stored.get("proposalDigest"),
                 "record_digest": record["proposalDigest"]})
        if stored.get("status") in ("ABANDONED", "SUPERSEDED"):
            raise Refused(
                "architecture_decision_conflict",
                f"Decision {decision_id} was {stored['status'].lower()} and "
                "cannot be re-applied. Re-run "
                f"{ARCHITECTURE_PHASE} to propose again.",
                {"decision": decision_id, "status": stored.get("status")})
        return {"replayed": True, "decision": decision_id,
                "revision": catalog["revision"],
                "appliedRevision": stored.get("appliedRevision"),
                "catalog": architecture_catalog_relative(paths),
                "superseded": stored.get("supersedes") or []}

    current = (catalog or empty_architecture_catalog())["revision"]
    if record["baseRevision"] != current:
        raise Refused(
            "architecture_catalog_stale",
            f"This placement was reasoned against architecture revision "
            f"{record['baseRevision']}, and the catalog is now at {current} — "
            "another WorkItem's placement was approved in between. Nothing "
            f"has been written. Re-run {ARCHITECTURE_PHASE} against the "
            "current architecture (`architecture show`) and re-approve.",
            {"decision": decision_id, "base_revision": record["baseRevision"],
             "catalog_revision": current,
             "catalog": architecture_catalog_relative(paths)})

    updated = apply_architecture_delta(
        catalog or empty_architecture_catalog(), record, stamp)
    relative = write_architecture_catalog(paths, updated)
    applied = next(entry for entry in updated["decisions"]
                   if entry["id"] == decision_id)
    return {"replayed": False, "decision": decision_id,
            "revision": updated["revision"],
            "appliedRevision": applied["appliedRevision"],
            "catalog": relative,
            "superseded": applied.get("supersedes") or []}


def architecture_realize(paths: Paths, stamp: str) -> dict:
    """`_architecture_realize_locked`, under the catalog lock.

    With no catalog file the inner function refuses on its own, and a refusal
    must not leave a directory behind, so that case is not locked.
    """
    if not (paths.project_root / architecture_catalog_relative(paths)).exists():
        return _architecture_realize_locked(paths, stamp)
    with architecture_catalog_lock(paths):
        return _architecture_realize_locked(paths, stamp)


def _architecture_realize_locked(paths: Paths, stamp: str) -> dict:
    """Realize this WorkItem's approved placement. Idempotent by the same rule.

    Every "nothing to do here" branch is a **refusal**, not a silent pass.
    After ADR-013 every WorkItem that reaches `gate_implement` has passed
    `gate_architecture`, so a missing record, a missing catalog or a decision
    the catalog does not hold all mean the same thing: something disposed of
    the placement without the WorkItem noticing. Returning `None` there left a
    service `PLANNED` for ever with no refusal and no audit entry.
    """
    record = require_architecture_record(paths)
    catalog = read_architecture_catalog(paths)
    decision = next((entry for entry in (catalog or {}).get("decisions") or []
                     if entry.get("id") == record["decisionId"]), None)
    if decision is None:
        raise Refused(
            "architecture_placement_missing",
            f"WorkItem '{paths.workitem}' holds placement "
            f"{record['decisionId']}, which is not in the repository catalog, "
            "so there is nothing to realize. Its architecture decision was "
            f"never applied or was disposed of; re-run {ARCHITECTURE_PHASE} "
            "and approve it.",
            {"workitem": paths.workitem, "decision": record["decisionId"],
             "catalog": architecture_catalog_relative(paths)})
    # The id alone does not identify the decision this WorkItem approved: a
    # record whose digest no longer matches, or an id the catalog attributes
    # to another WorkItem, is a different decision wearing this one's name.
    # Checked before either branch below, so not even the IMPLEMENTED replay
    # can report success for it.
    if (decision.get("workItem") != paths.workitem
            or decision.get("proposalDigest") != record["proposalDigest"]):
        raise Refused(
            "architecture_decision_conflict",
            f"Decision {decision['id']} in the catalog does not belong to "
            f"WorkItem '{paths.workitem}' with this placement's digest, so it "
            "cannot be realized on this WorkItem's behalf. Re-run "
            f"{ARCHITECTURE_PHASE} so the WorkItem proposes afresh.",
            {"decision": decision["id"], "workitem": paths.workitem,
             "catalog_workitem": decision.get("workItem"),
             "applied_digest": decision.get("proposalDigest"),
             "record_digest": record["proposalDigest"]})
    if decision.get("status") == "IMPLEMENTED":
        return {"replayed": True, "decision": decision["id"],
                "revision": catalog["revision"],
                "catalog": architecture_catalog_relative(paths)}
    if decision.get("status") != "APPROVED_PENDING_IMPLEMENTATION":
        raise Refused(
            "architecture_decision_unresolved",
            f"Decision {decision['id']} is {decision.get('status')}, so there "
            "is nothing to realize. A WorkItem whose placement was abandoned "
            f"must re-run {ARCHITECTURE_PHASE}.",
            {"decision": decision["id"], "status": decision.get("status")})

    updated = realize_architecture_decision(
        catalog, decision, record["placement"]["capability"]["id"], stamp)
    relative = write_architecture_catalog(paths, updated)
    return {"replayed": False, "decision": decision["id"],
            "revision": updated["revision"], "catalog": relative}


def cmd_architecture_apply(args, paths: Paths) -> int:
    """Apply an approved placement. Normally reached through `gate approve`.

    Exposed as a command for the one case the gate path cannot cover: a crash
    between the catalog write and the rest of the approval, where the operator
    needs to replay the identical decision and see that it was already
    applied.
    """
    paths = bind_for_architecture(args, paths)
    state = read_state(paths)
    consts = load_constants(paths)
    record = require_architecture_record(paths)
    architecture_outcome_precondition(record)
    # The same path-equality check the gate makes: resolve what
    # ARTIFACT_OWNERSHIP names and hand it to the binding, so the replay path
    # cannot verify a different file from the one a gate would fingerprint.
    resolved, _ = resolve_artifact_path(
        state, consts, ARCHITECTURE_GATE_KEY, paths)
    architecture_binding_precondition(paths, record, resolved)
    architecture_requirements_precondition(paths, record)

    if approval_decision(state, ARCHITECTURE_GATE_KEY) != "approved":
        raise Refused(
            "gate_required",
            f"{ARCHITECTURE_GATE_KEY} has not been approved (a rejected or "
            "omitted gate is not an approval), and an "
            "architecture decision enters the shared catalog only on a "
            "human's approval. Approve the gate; the approval applies the "
            "decision for you.",
            {"gate": ARCHITECTURE_GATE_KEY, "workitem": paths.workitem})

    stamp = now_iso()
    result = architecture_apply(paths, record, stamp)
    if not result["replayed"]:
        append_audit(
            paths, state, phase=state.get("current_phase") or ARCHITECTURE_PHASE,
            event=ARCHITECTURE_APPLIED_EVENT,
            message=(f"Architecture decision {result['decision']} applied "
                     f"(catalog revision {result['revision']})."),
            artifact=result["catalog"])
        save_state(paths, state, args.session)
    emit("architecture apply", {"workitem": paths.workitem, **result})
    return EXIT_OK


def cmd_architecture_realize(args, paths: Paths) -> int:
    """Mark an approved placement realized. Normally reached through the
    implementation gate's approval; exposed for the same replay reason.

    Gated on the same rule as `apply`, for the same reason: realization is a
    catalog mutation — `PLANNED` becomes `IMPLEMENTED`, the previous owner of
    moved data is closed — and ADR-013's guarantee is that no catalog
    mutation happens without a human decision behind it. The human decision
    realization rests on is the *implementation* gate.
    """
    paths = bind_for_architecture(args, paths)
    state = read_state(paths)

    if approval_decision(state, "gate_implement") != "approved":
        raise Refused(
            "gate_required",
            "gate_implement has not been approved (a rejected gate is not "
            "an approval), and a planned service "
            "becomes implemented only once a human has accepted the work "
            "that built it. Approve the implementation gate; the approval "
            "realizes the decision for you.",
            {"gate": "gate_implement", "workitem": paths.workitem})

    stamp = now_iso()
    result = architecture_realize(paths, stamp)
    if not result["replayed"]:
        append_audit(
            paths, state, phase=state.get("current_phase") or "implement",
            event=ARCHITECTURE_REALIZED_EVENT,
            message=(f"Architecture decision {result['decision']} realized "
                     f"(catalog revision {result['revision']})."),
            artifact=result["catalog"])
        save_state(paths, state, args.session)
    emit("architecture realize",
         {"workitem": paths.workitem, "realized": True, **result})
    return EXIT_OK


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
# swallow-and-default: a silently defaulted baseline would make the
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

    A baseline finding says *what* is wrong; without the commit it
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

    There is no binding without a WorkItem, so R1 and R2 apply
    unconditionally.
    """
    status, findings = baseline_state(paths)
    relative = f"{paths.config_root_relative}/{paths.baseline_file.name}"
    data = {"workitem": paths.workitem, "flow": flow, "baseline_status": status,
            "path": relative, "findings": findings,
            # Which repository state the baseline ever described.
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
        # The same fact in the same shape as `baseline_precondition`.
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
# Artifact path resolution
# --------------------------------------------------------------------------


def resolve_artifact_path(
    state: dict, consts: Constants, gate_key: str, paths: Paths
) -> tuple[str | None, str | None]:
    """Resolve ARTIFACT_OWNERSHIP's template for ``gate_key``.

    Returns ``(resolved_path, skip_reason)``. A skip reason means the gate has
    no comparable artifact yet — not that something failed.

    Placeholders name a location only the active binding knows:
    ``{workitem_runtime}`` is the WorkItem runtime, ``{workitem_root}`` is its
    parent — the WorkItem directory itself, where deliverables that are not
    engine bookkeeping live — and ``{speckit_feature_directory}`` is
    ``specKit.featureDirectory``. ``paths`` is therefore a required argument —
    an omitted binding could otherwise resolve a literal placeholder onto disk.
    The templates themselves carry the placeholder.

    The first two substitute unconditionally because a bound ``Paths`` always
    knows them; the rest read state and may legitimately be unresolved.
    """
    template = consts.artifact_ownership.get(gate_key)
    if not template or template == "(none)":
        return None, "no artifact registered for this gate"

    resolved = template.replace("{workitem_runtime}", paths.runtime_relative)
    resolved = resolved.replace("{workitem_root}", paths.workitem_root_relative)

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


# What resolves each ARTIFACT_OWNERSHIP binding, named in the
# `artifact_unresolved` refusal so the recovery is actionable rather than
# "something is missing".
ARTIFACT_BINDING_RECOVERY = {
    "speckit_feature_directory":
        "run `feature resolve` so this WorkItem's feature directory is "
        "recorded",
    "security_review_artifact":
        "run `security-review begin`, which names the review file, and write "
        "the review there",
}

# The last sentence of each `artifact_missing` refusal, by the command that
# raised it.
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
    """Resolve the artifact a gate decision is about, and fingerprint it, or
    refuse.

    Returns ``(resolved_path, sha)``. Both are ``None`` only for a gate that
    registers no artifact at all (an ARTIFACT_OWNERSHIP template of
    ``(none)``) — the one legitimate artifact-free gate.

    An *unresolved* template must never be treated like a resolved one:
    ``resolve_artifact_path`` answers ``(None, reason)``, and deciding the gate
    with ``sha: null`` would approve a Spec Kit gate whose feature directory was
    never resolved, or complete a whole flow on a security gate whose review
    file was never named. A registered artifact that cannot be resolved, found
    or read is therefore a refusal, raised by a pure reader ahead of every
    write, so the refusal leaves the phase, the approvals and the ledger
    exactly as they were.

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
    """The same idiom for the downgrade entry. A separate marker, so
    the two entries de-duplicate independently and neither can suppress the
    other."""
    return f"(governance downgrade {execution_id})"


def content_acknowledgement_marker(path: str, sha256: str) -> str:
    """The idiom `governance_audit_marker` uses, for a scan acknowledgement.
    The full digest, not a prefix: `record_scan_acknowledgement_audit`'s
    replay matches this structurally (event and artifact, not a text
    search), but the marker is also what a human reads, and a truncated
    hash inside two entries for the same path is exactly the kind of near
    which that scenario means to guard against."""
    return f"(content acknowledged {path} {sha256})"


_AUDIT_EVENT = re.compile(r"^## AUDIT \[.*?\] \| .*? — (\S+)\s*$", re.MULTILINE)
_AUDIT_ARTIFACT = re.compile(r"^\*\*Artifact:\*\* (.*)$", re.MULTILINE)


def _already_recorded(entries: list[str], artifact: str, marker: str) -> bool:
    """Structural de-duplication, not a text search over the whole ledger:
    an entry counts only if its own event is `content_accepted`, its own
    `Artifact` field equals this acknowledgement's path, and the marker
    appears within that same entry's block — never a marker that happens to
    appear inside an unrelated entry, a path, or a comment elsewhere in the
    file (V2-05: a substring search over the whole file can be satisfied by
    text that was never actually this acknowledgement)."""
    for block in entries:
        event = _AUDIT_EVENT.match(block)
        artifact_line = _AUDIT_ARTIFACT.search(block)
        if (event and event.group(1) == "content_accepted"
                and artifact_line and artifact_line.group(1) == artifact
                and marker in block):
            return True
    return False


def record_scan_acknowledgement_audit(paths: Paths, state: dict | None) -> None:
    """Carry every recorded content acknowledgement into the ledger, exactly
    once each, DEF-RR-001's half of the same problem `record_governance_audit`
    solves immediately above.

    Validates the acknowledgement record whether or not `state` is given —
    the same "pure reader" step the other preconditions in
    `governance_precondition` already take with no `state` — so a malformed
    file is caught before `cmd_gate_approve`'s, `cmd_gate_omit`'s and
    `cmd_skip`'s own early, state-less calls, not only before `advance`'s.
    Replay (the actual audit write) only happens when `state` is given.

    `accept-content --path` cannot write this itself when it runs pre-init:
    there is no `audit_sha` to rebaseline and no state file to save, for the
    identical reason `governance assess` writes no audit entry of its own.
    So a pre-init acknowledgement is replayed here, at the same first phase
    movement that already carries the governance record in — de-duplicated
    per acknowledgement by `(path, sha256)`, so replaying at every later
    advance never doubles an entry, and acknowledging the same path twice
    (different content each time) is two entries, not one overwritten.
    """
    doc = read_scan_acknowledgements(paths)  # validates even if state is None
    if state is None:
        return
    acknowledgements = doc.get("acknowledgements") or []
    if not acknowledgements:
        return
    existing_text = (
        paths.audit_file.read_text(encoding="utf-8")
        if paths.audit_file.is_file() else ""
    )
    entries = split_audit_entries(existing_text)
    for ack in acknowledgements:
        marker = content_acknowledgement_marker(ack["path"], ack["sha256"])
        if _already_recorded(entries, ack["path"], marker):
            continue
        append_audit(
            paths, state, phase=state.get("current_phase", "unknown"),
            event="content_accepted",
            message=f"User accepted flagged content in {ack['path']} {marker}.",
            artifact=ack["path"],
        )
        existing_text = (
            paths.audit_file.read_text(encoding="utf-8")
            if paths.audit_file.is_file() else existing_text
        )
        entries = split_audit_entries(existing_text)


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
    # the assessment implied, and a record without it simply has nothing to say.
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
    """A second, distinct ledger entry when this assessment
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
# Governed artifact review (contract TP-011, §12)
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
    exist" and a stale one survive.
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

    The two "understand before you draft" phases behave alike: `discovery`
    surveys a repository before a brownfield WorkItem specifies anything, and
    `impact_analysis` establishes a defect's blast radius before a fix is
    specified. Leaving one enforced and the other not would be an accident of
    sequencing: §14 demands discovery's rule explicitly, and the same demand
    applies to the gateless `impact_analysis` phase.

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
    to review. E2 applies to every bound WorkItem, unconditionally.
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

    There is no binding without a WorkItem, so E1 applies unconditionally.
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

    raw_current: dict[str, bytes] = {}
    freshness = governance_freshness(paths, record, raw_out=raw_current)
    if not freshness["fresh"]:
        if freshness.get("assessed_without_a_binding"):
            raise Refused(
                "governance_stale",
                f"The governance record for '{paths.workitem}' was written "
                "before this WorkItem declared which requirement documents it "
                "is about, so nothing says what it was assessed against. Bind "
                "them with `requirements bind`, then re-run `governance "
                "assess`.",
                {"workitem": paths.workitem,
                 "assessed_without_a_binding": True},
            )
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

    # Fresh means the bytes on disk are the bytes assessed - it says nothing
    # about whether the content they hold is still *acknowledged*. Assessment
    # required an acknowledgement for any flagged document, but that record is
    # a durable store a person or a bug can lose, and the requirements being
    # unchanged leaves freshness silent about it. So the acknowledgement is
    # asked for again here, against the exact bytes freshness just read.
    offenders = unacknowledged_flagged_sources(
        paths, freshness["current_entries"], raw_current)
    if offenders:
        raise content_unacknowledged_refusal(paths, offenders)

    # Accepted. The facts enter the ledger here, after every refusal has had
    # its chance to fire, so a refused advance never writes anything.
    #
    # Acknowledgement *validation* runs unconditionally, even when `state` is
    # `None` — `cmd_gate_approve`, `cmd_gate_omit` and `cmd_skip` each call
    # this precondition once early, with no `state`, specifically so a
    # refusal here happens before *their own* first irreversible append
    # (`gate_approved`/`gate_omitted`/`skipped`), the same reason
    # `cmd_gate_approve` gives for its own early call above. Gating the
    # validation on `state is not None` left exactly that append unprotected
    # for those three commands: a malformed acknowledgements file would only
    # be discovered at their *second*, state-carrying call, by which point
    # the append had already happened. Replay (the write) still only happens
    # when `state` is given — `record_scan_acknowledgement_audit` itself
    # returns immediately after validating if `state` is `None`.
    #
    # Acknowledgement validation/replay runs BEFORE `record_governance_audit`:
    # its only possible failure (`read_scan_acknowledgements` raising on a
    # malformed file) then happens before either function has appended
    # anything, so a refusal here still leaves `audit.md` byte-identical.
    # Reversed, a governance entry already written by `record_governance_audit`
    # would survive an IntegrityError raised moments later by the
    # acknowledgement read — a refused advance that had, in fact, already
    # changed the ledger.
    record_scan_acknowledgement_audit(paths, state)
    if state is not None:
        record_governance_audit(paths, state, record)
    return None


def flow_precondition(paths: Paths, state: dict | None = None) -> None:
    """A flow cannot change under a workflow that has already started.

    `init` binds `state["flow"]` from the governance record; re-assessing
    afterwards with a different flow would otherwise silently re-shape a
    lifecycle mid-run, which is precisely the reshaping-by-command that D9
    refuses to provide as a feature. So the disagreement is a refusal with a
    named remedy, not a warning.

    Deliberately a **pure reader**: it never writes state and never appends to
    the ledger, and every caller places it ahead of its first `append_audit`.
    That is what keeps `audit.md` byte-identical across a refused advance,
    approval or skip (B1, and the ordering NB-6 recorded for `cmd_skip`).

    There is no binding without a WorkItem, so the flow check applies
    unconditionally.
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
    refuses to leave a gate phase whose approval is not recorded, and
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

    # The placement is load-bearing, and it is written out in three
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
    architecture_precondition(paths, state)
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
    """The terminal gate re-checks every omission taken before it.

    A gate already passed is never revisited, so an omission recorded at LOW
    would otherwise survive a later re-assessment that raised the level. The
    workflow is declared finished at the terminal gate — that is where the
    whole run still has to be admissible, and the last moment at which
    refusing costs less than unpicking a completed workflow.

    A PURE READER. Its caller places it among `cmd_gate_approve`'s other pure
    readers, ahead of the first `append_audit`, so a refusal leaves `audit.md`
    byte-identical (the B1/NB-6 property). It reads the policy only when there
    is an omission to revalidate, so a run that approved everything pays
    nothing.
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
        # DERIVED, not the literal `True`. Every gate is passed by an
        # explicit, recorded decision — but that decision may be a
        # policy-permitted omission, and a summary that claimed every gate was
        # APPROVED would state a guarantee the run does not carry. Narrow on
        # purpose: it reports `false` for that one fact and for nothing else,
        # so a run that approved everything reads `true`.
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
    architecture_precondition(paths, state)
    revalidate_recorded_omissions(paths, state, consts, args.gate)

    # ADR-013. BOTH catalog writes happen *here*, between the last refusal
    # and the first ledger append, for the reason the comment above gives: a
    # stale-revision, decision-conflict or unreadable-catalog refusal must
    # leave `audit.md` byte-identical. Recording the approval first and then
    # discovering the catalog had moved would put an approval in the ledger
    # for a decision that never entered the architecture — and `realize` can
    # refuse for exactly as many reasons as `apply` can, so it belongs on the
    # same side of the line.
    applied = realized = None
    if args.gate == ARCHITECTURE_GATE_KEY:
        applied = architecture_apply(
            paths, require_architecture_record(paths), stamp)
    elif args.gate == "gate_implement":
        # Realization is the implementation gate's business: a service is
        # PLANNED from approval until the work that built it has been
        # accepted, and only then IMPLEMENTED. Idempotent, so a re-approval
        # after drift does not mutate twice.
        realized = architecture_realize(paths, stamp)

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

    if applied and not applied["replayed"]:
        append_audit(
            paths, state, phase=gate_phase, event=ARCHITECTURE_APPLIED_EVENT,
            message=(
                f"Architecture decision {applied['decision']} applied to the "
                f"repository catalog (revision {applied['revision']})."),
            artifact=applied["catalog"],
        )
        # A supersession disposes of a previously approved decision, and a
        # disposition that reached the catalog with no ledger entry would be
        # the one architecture change nobody could find afterwards.
        if applied["superseded"]:
            append_audit(
                paths, state, phase=gate_phase,
                event=ARCHITECTURE_ABANDONED_EVENT,
                message=(
                    "Approved-but-unrealized architecture decision(s) "
                    + ", ".join(applied["superseded"])
                    + " marked SUPERSEDED by this WorkItem's rerun placement "
                    f"{applied['decision']}; planned services withdrawn."),
                artifact=applied["catalog"],
            )

    if realized and not realized["replayed"]:
        append_audit(
            paths, state, phase=gate_phase,
            event=ARCHITECTURE_REALIZED_EVENT,
            message=(
                f"Architecture decision {realized['decision']} realized: "
                "planned services are now implemented and superseded "
                f"ownership is closed (catalog revision "
                f"{realized['revision']})."),
            artifact=realized["catalog"],
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
            # ADR-013: `null` unless this approval moved the catalog.
            "architecture_applied": applied,
            "architecture_realized": realized,
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

    # ADR-013. `gate_architecture` has no drift re-approval: the
    # rendering is engine-generated and bound to the record by digest, so a
    # drifted `placement.md` is not new content to re-approve — it is a file
    # that no longer matches the decision already in the shared catalog.
    # Re-baselining it here would silently break the binding the whole design
    # rests on, and there is no re-apply to put it back.
    if gate_key == ARCHITECTURE_GATE_KEY:
        raise Refused(
            "architecture_artifact_binding_invalid",
            "The architecture placement rendering has changed since it was "
            "approved, and it cannot be re-approved through drift: it is "
            "generated from the placement record and bound to the decision "
            "already applied to the repository catalog. Restore the "
            "generated file from version control, or `restart` to "
            f"{ARCHITECTURE_PHASE} — which disposes of the applied decision "
            "and lets this WorkItem propose afresh.",
            {"gate": gate_key, "workitem": paths.workitem,
             "queue": list(state.get("drift_queue") or [])})

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
    # only way it can be underivable is a refusal, because an omission nobody
    # can justify is not one the engine will take. `cmd_gate_omit` is reached
    # only through `main()`'s `bind_workitem`, which never returns an unbound
    # `Paths`.
    governance_record = read_governance_record(paths)
    if governance_record is None:
        raise Refused(
            "governance_missing",
            f"WorkItem '{paths.workitem}' has no governance record, so no "
            "gate can be shown to be unnecessary. Run `governance assess "
            "--input <path>` first.",
            {"workitem": paths.workitem, "path": str(paths.governance_file)},
        )
    # If the level this omission rests on was reached by lowering an
    # earlier one, the omission evidence says so. §15 wants an omitted gate
    # explainable; "the policy did not require it" is only half an
    # explanation when the input to the policy moved.
    downgrade = governance_record.get("downgrade")
    # §15 requires an omitted gate to be explainable *later*, from
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
            f"{((model or {}).get('policy') or {}).get('source')}"
            + ("" if not any(r.startswith("pinned:") for r in reasons) else
               "; required by the policy this WorkItem started under, sha "
               f"{(((model or {}).get('pinned_policy')) or {}).get('sha256')}")
            + "). Approve it, or reject it — a required gate has no third "
            "option.",
            {"gate": args.gate, "phase": gate_phase,
             "final_risk": (model or {}).get("final_risk"),
             "reasons": reasons,
             "required_gates": (model or {}).get("required_gates"),
             "omittable_gates": (model or {}).get("omittable_gates"),
             "policy": (model or {}).get("policy"),
             # ADR-011: which policy the run started under, so a refusal a
             # reader did not expect can be diagnosed without re-deriving it.
             "pinned_policy": (model or {}).get("pinned_policy"),
             "pinned_policy_sha256": (((model or {}).get("pinned_policy"))
                                      or {}).get("sha256")},
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
    architecture_precondition(paths, state)

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
        # ADR-011. §15 wants an omitted gate explainable *later*, and after
        # the pin that takes two policies: the one in force when the gate was
        # passed, and the one the run started under. `null` when the record
        # predates the pin.
        "pinned_policy_sha256": ((model.get("pinned_policy") or {})
                                 .get("sha256")),
        # The record the level was read from, fingerprinted, so a
        # later reader can tell whether it is still the record on disk.
        "governance_sha256": governance_sha,
        # `null` for the ordinary case; the whole block when the
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
            continue  # an approval recorded without a baseline: nothing to compare
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
    gates that both own it — analyze refining tasks.md, which the tasks gate already
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
    # ADR-013, the sibling door to `_approve_drift`'s refusal. The
    # architecture rendering is engine-generated and bound by digest to a
    # decision already in the shared catalog, so re-baselining it here would
    # leave the catalog's `renderedSha256` permanently describing a file that
    # no longer exists — and nothing downstream re-reads the binding once the
    # gate is approved. Guarding one door is not guarding the artifact.
    if args.gate == ARCHITECTURE_GATE_KEY:
        raise Refused(
            "architecture_artifact_binding_invalid",
            "The architecture placement rendering cannot be re-baselined: it "
            "is generated from the placement record and bound to the "
            "decision already applied to the repository catalog. Restore the "
            "generated file from version control, or `restart` to "
            f"{ARCHITECTURE_PHASE} — which disposes of the applied decision "
            "and lets this WorkItem propose afresh.",
            {"gate": args.gate, "workitem": paths.workitem})

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
# SDLE is verified against one pinned Spec Kit release, but an installation on
# disk can differ from it, so what it supports cannot be assumed. §10's
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


# The Spec Kit release SDLE is verified against, and the init command that
# installs it. The earlier `specify init . --skills --here` is rejected by
# this release (`No such option: --skills`): the Claude integration installs
# skills by default. Pinned with `@v<version>` so a user reproduces what was
# tested rather than whatever the default branch is today; an existing
# installation is never upgraded by SDLE. docs/GETTING-STARTED.md states the
# same command, and a unit test holds the two together.
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

    There is no newest-mtime *selection*, so this order does not pick a
    winner — it only makes the refusal's candidate list deterministic. Sorted
    by name for exactly that reason: two directories created in the same
    second have no meaningful mtime order, and an order that decides nothing
    should not pretend to rank.
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
    feature, so both give the same answer and there is one tier list.
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
      2. ``<project-root>/specs/*``  — where Spec Kit actually creates a
         feature, since it hardcodes ``repo_root/specs`` for *creation*;
      3. ``.specify/specs/*``        — where an older layout kept it.

    That is precedence, not a tie-break between peers, and it is why the
    resolver discovers the native directory instead of hardcoding a creation
    path no unpinned Spec Kit install can guarantee. Nothing under another
    WorkItem is ever a candidate: no tier reaches into ``workitems/<other-id>/``.

    Within the chosen tier there is no selection rule left to get wrong.
    More than one candidate refuses `feature_ambiguous` and lists them. Picking
    the newest mtime and refusing only on an exact timestamp tie would let two
    WorkItems both standing at the specification phase cross-adopt through the
    repository-global `specs/` tier — a silent wrong pick out of a shared
    staging area, which §9 ("never silently pick one among multiple
    plausible") and §10 ("WorkItem A's Spec Kit output cannot be mistaken for
    WorkItem B's") both forbid. Recency is not evidence of ownership.

    There is no override flag, because there does not need to be one: tier 1
    is `workitems/<id>/specs/`, so *moving* the directory this WorkItem owns
    into its own tier resolves the ambiguity by precedence, deterministically
    and without SDLE guessing. The refusal names that remedy.

    `speckit_specs_root` is never `None` here: `feature` is not
    `RUNTIME_FREE`, so `bind_workitem` has already returned a bound `Paths`
    (R2, pinned by N25).
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

    # Pure reader, and placed ahead of every write below, so a
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


def cmd_requirements_bind(args, paths: Paths) -> int:
    """Declare which requirement documents this WorkItem is about.

    The engine writes the binding; it is never hand-edited (invariant 6),
    because it decides what a governance assessment means.

    `--all-current` is a convenience that expands `requirements/` into the
    **exact files present now**, recorded as those paths. It is deliberately
    not a live glob: a binding that re-expanded on each read would silently
    acquire documents nobody chose, which is the defect this replaces.
    """
    explicit = list(getattr(args, "source", None) or [])
    if explicit and args.all_current:
        raise UsageError(
            "requirements_binding_ambiguous",
            "Give either --source paths or --all-current, not both: the "
            "binding records exactly what was chosen.")
    if args.all_current:
        root = paths.project_root / "requirements"
        explicit = sorted(
            item.relative_to(paths.project_root).as_posix()
            for item in root.rglob("*") if item.is_file()
        ) if root.is_dir() else []
        if not explicit:
            raise _binding_refused(
                "requirements_binding_empty",
                "There are no files under requirements/ to bind. Write the "
                "requirements first, or name sources elsewhere with --source.",
                workitem=paths.workitem)
    if not explicit:
        raise UsageError(
            "requirements_binding_empty",
            "A binding names at least one requirement document. Use "
            "--source <path> (repeatable), or --all-current.")

    sources: list[str] = []
    for raw in explicit:
        canonical = _binding_source(paths, raw)
        # Case-folded, because two spellings of one file on Windows would
        # otherwise be bound twice and hashed twice into the same digest.
        if any(canonical.lower() == seen.lower() for seen in sources):
            raise _binding_refused(
                "requirements_source_duplicate",
                f"'{raw}' is already bound. Each document is bound once, so "
                "the recorded set says what it means.", source=raw)
        sources.append(canonical)

    if args.primary:
        primary = _binding_source(paths, args.primary)
    elif len(sources) == 1:
        primary = sources[0]
    else:
        # No alphabetical default. The primary names the project, so picking
        # the first by sort order silently names it after whichever document
        # sorts first — `00-regulatory.md` over `product.md`. Which document
        # speaks for the work is a decision, and the engine does not have it.
        raise UsageError(
            "requirements_primary_required",
            "More than one document is being bound, so name which one speaks "
            "for this WorkItem: --primary <path>. It is the document the "
            "project's name is read from.")
    if primary not in sources:
        raise _binding_refused(
            "requirements_source_invalid",
            f"The primary document '{args.primary}' is not one of the bound "
            "sources.", source=args.primary, sources=sources)

    try:
        previous = read_requirements_binding(paths)
    except IntegrityError:
        # `bind` is how a corrupt binding is repaired, so it must not refuse on
        # the file it is about to replace. `rebound` below is only evidence.
        previous = None
    document = {
        "bindingVersion": REQUIREMENTS_BINDING_VERSION,
        "workitem": paths.workitem,
        "boundAt": now_iso(),
        "primary": primary,
        "sources": sorted(sources),
        "digest": binding_digest(sources),
    }
    paths.runtime.mkdir(parents=True, exist_ok=True)
    write_atomic(paths.requirements_binding_file,
                 json.dumps(document, indent=2) + "\n")
    emit("requirements bind", {
        "workitem": paths.workitem,
        "sources": document["sources"],
        "primary": primary,
        "digest": document["digest"],
        # A re-bind does not itself invalidate anything; it makes the recorded
        # assessment stale, which `advance` reports at its own choke point.
        "rebound": previous is not None
        and previous.get("digest") != document["digest"],
    })
    return EXIT_OK


def cmd_requirements_show(args, paths: Paths) -> int:
    """Report the binding, and whether each bound document is still there.

    The orchestrator displays this before the governance proposal: a binding
    that can be forgotten is a binding that has to be visible (ADR-012 §5).
    """
    try:
        binding = validated_binding(paths)
    except Refused as exc:
        if exc.reason != "requirements_unbound":
            raise
        binding = None
    if binding is None:
        emit("requirements show", {
            "workitem": paths.workitem, "bound": False, "sources": [],
            "primary": None, "digest": None, "missing": [],
        })
        return EXIT_OK
    sources = list(binding["sources"])
    missing = [relative for relative in sources
               if not (paths.project_root / relative).is_file()]
    emit("requirements show", {
        "workitem": paths.workitem,
        "bound": True,
        "sources": sources,
        "primary": binding.get("primary"),
        "digest": binding.get("digest"),
        "boundAt": binding.get("boundAt"),
        "missing": missing,
    })
    return EXIT_OK


def cmd_security_review_begin(args, paths: Paths) -> int:
    """Pin the review filename before generation, so crash recovery and drift
    detection both know the target path. The name is never one that already
    exists: a second call in the same minute, or another WorkItem sharing
    `reviews/`, takes the next `-2`, `-3` suffix instead of overwriting."""
    state = read_state(paths)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"reviews/security-review-{stamp}.md"
    suffix = 2
    while (paths.project_root / filename).exists():
        filename = f"reviews/security-review-{stamp}-{suffix}.md"
        suffix += 1
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


# the implementation gate's verification evidence.
#
# `manifest build` writes one structured record per build beside the manifest
# and names it from a line in the manifest. the implementation gate reads it back and binds it
# to the exact manifest bytes, the pinned implementation base and the bound
# WorkItem, then requires a runner that actually ran and exited 0. The prose
# statuses are for the reader; the record is what the implementation gate requires.
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
    """the implementation gate requires evidence of a passing test run for *this* manifest."""
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
            + ". the implementation gate needs a test run that actually ran and passed, and "
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

    the implementation gate is the one gate whose artifact is machine-generated, so it is the
    one gate whose completeness can be checked mechanically. A hook can be
    skipped; this refusal cannot — an implementation whose secrets scan or
    tests never ran does not reach a human decision.

    The four Spec Kit gates carry a second such refusal. Spec Kit keeps a
    single repository-global feature slot, so a stale one can point this
    WorkItem at another's directory; a WorkItem's gate must never approve
    another WorkItem's artifact. The containment rule applies to every
    resolvable Spec Kit gate.

    `gate_architecture` carries a third: its artifact is *also* machine
    generated, from a structured record the catalog is applied from, so the
    rendering the human just read has to be provably the record about to be
    applied (ADR-013). Both checks are pure readers, ahead of every write.
    """
    if gate_key == ARCHITECTURE_GATE_KEY:
        record = require_architecture_record(paths)
        architecture_outcome_precondition(record)
        architecture_binding_precondition(paths, record, resolved)
        architecture_requirements_precondition(paths, record)
        return None

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
            f"Cannot approve {gate_key}: {resolved} is missing "
            f"{', '.join(missing)}. Rebuild it with `manifest build` so the "
            "secrets scan and test evidence are in front of the reviewer at "
            "the moment of decision.",
            {"path": resolved, "missing": missing},
        )
    # The headings prove the sections exist; this proves what the test
    # section reports is a passing run of *this* implementation.
    implementation_evidence_precondition(paths, state, gate_key, resolved,
                                         body)
    return None


# --------------------------------------------------------------------------
# Attempt counters
#
# Retries are keyed by the phase that failed. Remediations are keyed by the
# EXECUTION phase behind a gate, not the gate phase itself, so the count reads
# "spec_draft has been remediated 3/3" even while current_phase is gate_spec.
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
        # The checklist phase's artifact: absent or thin is tolerated, and recorded.
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
    """An audited change of a rate limit, in place of editing state.json by
    hand — hand-editing defeats the audit chain."""
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
    architecture_precondition(paths, state)

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
    # ADR-013. Rolling back to or past `architecture_placement` discards
    # this WorkItem's placement, and an approved placement is shared evidence
    # a later WorkItem may already have reasoned from. It is *disposed of*,
    # never deleted: the decision becomes ABANDONED and any service it had
    # planned becomes WITHDRAWN, so the boundary stays reclaimable and the
    # history stays append-only.
    abandoned = None
    if (flow.contains(ARCHITECTURE_PHASE)
            and args.to <= flow.index(ARCHITECTURE_PHASE)):
        abandoned = abandon_architecture_decisions(paths, "restart")

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
                f"phase_history trimmed by {trimmed}."
                + (f" Architecture decision(s) abandoned: "
                   f"{', '.join(abandoned['decisions'])}."
                   if abandoned else ""),
    )
    if abandoned:
        append_audit(
            paths, state, phase=target, event=ARCHITECTURE_ABANDONED_EVENT,
            message=(
                "Approved-but-unrealized architecture decision(s) "
                f"{', '.join(abandoned['decisions'])} marked ABANDONED by "
                f"restart; planned services withdrawn (catalog revision "
                f"{abandoned['revision']})."),
            artifact=abandoned["catalog"],
        )
    save_state(paths, state, args.session)
    emit("restart", {"pending": False, "target": target, "index": args.to,
                     "label": consts.label_or(target, flow),
                     "cleared_gates": cleared, "trimmed": trimmed,
                     "architecture_abandoned": abandoned})
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

    # ADR-013 — and note the asymmetry with `restart`: this command
    # deletes `audit.md`, so there is no ledger left to record the
    # abandonment in. The catalog disposition is the ONLY durable record a
    # reset abandonment will ever have, which is precisely why it is written
    # here, before the deletion, rather than audited afterwards. A catalog
    # the engine cannot read therefore blocks `reset` — fail-closed, because
    # losing shared architectural history silently is the outcome this rule
    # exists to prevent.
    abandoned = abandon_architecture_decisions(paths, "reset")

    deleted = []
    for path in (paths.state_file, paths.audit_file, paths.lock_file):
        if path.is_file():
            path.unlink()
            deleted.append(path.name)
    emit("reset", {"pending": False, "deleted": deleted,
                   "architecture_abandoned": abandoned})
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


SCAN_ACKNOWLEDGEMENTS_VERSION = "1"


def read_scan_acknowledgements(paths: Paths) -> dict:
    """The WorkItem's explicit content acknowledgements, or an empty shell.

    Absence is not an error — most WorkItems never flag anything — but a
    present, unreadable or malformed file is: it would silently make
    `governance assess` treat "acknowledgement unknown" as "acknowledgement
    absent", which is the safe direction only for a file that never existed.
    """
    target = paths.scan_acknowledgements_file
    if not target.is_file():
        return {"scanAcknowledgementsVersion": SCAN_ACKNOWLEDGEMENTS_VERSION,
                "workitem": paths.workitem, "acknowledgements": []}
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise IntegrityError(
            "scan_acknowledgements_invalid",
            f"{paths.runtime_relative}/scan-acknowledgements.json is not "
            f"readable JSON: {exc}.", {}) from exc
    entries = doc.get("acknowledgements") if isinstance(doc, dict) else None
    # V3-03: the writer always sets `workitem`, but nothing read it back —
    # a store copied or symlinked in from another WorkItem's runtime (the
    # same threat `validated_binding` already checks for the requirements
    # binding) would silently transfer a decision that is documented and
    # stored as WorkItem-scoped.
    valid_shell = (
        isinstance(doc, dict)
        and doc.get("scanAcknowledgementsVersion") == SCAN_ACKNOWLEDGEMENTS_VERSION
        and doc.get("workitem") == paths.workitem
        and isinstance(entries, list))
    # Every entry re-checked on every read, not only at write time: a merge,
    # a restored backup or a hand edit can leave a well-formed shell around
    # an entry the replay loop would otherwise fail on midway through —
    # after it had already appended for the entries before it. Total, not
    # merely present: `sha256` must be a *string* before the regex ever runs
    # (an int or bool passed straight to `re.fullmatch` raises `TypeError`,
    # not a refusal), and `path` is re-checked through the same lexical
    # rules `safe_repo_path` enforces at write time — a control character or
    # a line break in a stored path is not evidence of anything, and
    # `record_scan_acknowledgement_audit` interpolates it into `audit.md`,
    # whose parser treats a line starting `## AUDIT ` as a new entry.
    def entry_ok(a: object) -> bool:
        if (not isinstance(a, dict)
                or set(a) - {"path", "sha256", "acknowledgedAt", "session"}
                or not isinstance(a.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", a["sha256"])
                or not isinstance(a.get("path"), str)):
            return False
        try:
            canonical = _lexically_safe_path(paths, a["path"])
        except _PathProblem:
            return False
        # Not merely "can be canonicalised without raising": `.strip()`
        # inside `_lexically_safe_path` silently drops a *leading or
        # trailing* control character (a literal newline) before the
        # control-character check ever sees it, so a stored path carrying
        # one would canonicalise cleanly while remaining, byte for byte,
        # something `record_scan_acknowledgement_audit` would later
        # interpolate into `audit.md` verbatim — forging an
        # `## AUDIT ` line the parser reads as a new entry. Requiring the
        # stored value to already equal its own canonical form closes that:
        # nothing reaches replay that was not already exactly what a
        # trusted write produced.
        if a["path"] != canonical:
            return False
        acknowledged_at = a.get("acknowledgedAt")
        session = a.get("session")
        return (isinstance(acknowledged_at, str)
                and (session is None or isinstance(session, str)))

    entries_ok = valid_shell and all(entry_ok(a) for a in entries)
    if not entries_ok:
        raise IntegrityError(
            "scan_acknowledgements_invalid",
            f"{paths.runtime_relative}/scan-acknowledgements.json is not a "
            "recognised acknowledgements record.", {})
    return doc


def is_content_acknowledged(doc: dict, path: str, sha256: str) -> bool:
    """True only for an acknowledgement matching both the path and the
    *current* content — editing a flagged line after acknowledging the old
    text must not carry the acknowledgement over to the new one."""
    return any(a.get("path") == path and a.get("sha256") == sha256
               for a in doc.get("acknowledgements", []))


def write_content_acknowledgement(paths: Paths, path: str, sha256: str,
                                 session: str | None) -> None:
    """Append one acknowledgement, unless an identical one — same path,
    same content — is already on file.

    Append-only, matching every other ledger this engine keeps
    (`audit.md`, `workitems/index.md`, `reviews.json`): acknowledging path A
    then, later, different content at the same path is two human decisions,
    not one overwriting the other, and `record_scan_acknowledgement_audit`'s
    replay depends on both surviving to be carried into the audit chain.
    An old acknowledgement for since-changed content is simply never matched
    again by `is_content_acknowledged` (it checks path *and* content), so it
    costs nothing to keep — the file grows by one entry per genuinely new
    decision, not per repeat of the same one.

    Accepted as a known limitation rather than fixed here: this is an
    unlocked read-modify-write, so two concurrent acknowledgements can race
    and one lose an update the other made in between. It fails closed — the
    lost acknowledgement simply means that path is unacknowledged again,
    which `governance assess` already refuses on its own, never a silent
    pass — so it costs a repeat `accept-content --path`, not a bypass.
    Serialising this belongs with the refusing lock primitive the
    requirements-refinement work introduces for its own shared-document
    transaction, not duplicated here for one file."""
    doc = read_scan_acknowledgements(paths)
    doc["workitem"] = paths.workitem
    if is_content_acknowledged(doc, path, sha256):
        return
    doc["acknowledgements"].append({
        "path": path, "sha256": sha256, "acknowledgedAt": now_iso(),
        "session": session,
    })
    write_atomic(paths.scan_acknowledgements_file,
                json.dumps(doc, indent=2) + "\n")


def content_unacknowledged_refusal(paths: Paths, offenders: list[dict]) -> Refused:
    """The one wording and payload for `governance_content_unacknowledged`,
    shared by `governance assess` and `governance_precondition` so the two
    cannot drift into describing the same refusal differently."""
    detail = "; ".join(
        f"{o['path']} (line {o['matches'][0]['line']}: "
        f"{o['matches'][0]['pattern']})" for o in offenders)
    return Refused(
        "governance_content_unacknowledged",
        "Bound document(s) contain unacknowledged content that looks "
        f"like instructions directed at the workflow engine: {detail}. "
        "Edit the flagged line(s) and re-assess, or acknowledge each "
        "with `accept-content --path <file>` first.",
        {"workitem": paths.workitem,
         "offenders": [{"path": o["path"], "matches": o["matches"]}
                       for o in offenders]})


def unacknowledged_flagged_sources(paths: Paths, sources: list[dict],
                                  raw_by_path: dict[str, bytes]) -> list[dict]:
    """Bound sources (as `requirements_sources` returns them — already
    confirmed present on disk) that are currently flagged and have no
    acknowledgement matching their content.

    Independent of whatever `scan` last recorded: this re-scans every bound
    source itself, so a source nobody ever ran `scan` on is caught here
    rather than silently reaching `init` unexamined.

    Takes `raw_by_path` — the exact bytes `requirements_sources`
    already read `entry["sha256"]` from — rather than reading the file a
    second time: two reads of the same path at two different times is
    exactly the gap a concurrent edit can exploit (hash flagged content,
    scan clean content substituted in between, or the reverse). Scanning and
    hashing the identical bytes closes it structurally, not by comparison.
    """
    doc = read_scan_acknowledgements(paths)
    offenders = []
    for entry in sources:
        raw = raw_by_path.get(entry["path"])
        if raw is None:
            continue  # missing; requirements_sources(strict=True) already
                      # refused before this ever runs, for a non-strict caller
                      # there is nothing to scan
        matches = scan_text(raw.decode("utf-8", errors="replace"))
        if matches and not is_content_acknowledged(doc, entry["path"], entry["sha256"]):
            offenders.append({"path": entry["path"], "matches": matches})
    return offenders


def cmd_scan(args, paths: Paths) -> int:
    target, canonical = safe_repo_path(paths, args.path)
    if not target.is_file():
        raise Refused("artifact_missing", f"No such file: {args.path}",
                      {"path": args.path})
    matches = scan_text(target.read_text(encoding="utf-8", errors="replace"))
    # `acknowledgeable` is reported whether or not anything fired, so a caller
    # can branch on the payload without a KeyError on the clean path.
    acknowledgeable = paths.state_file.is_file()
    # `canonical`, not `args.path`, everywhere a path is stored or matched
    # from here on — two spellings of the same file (a Windows alias, a
    # `./` prefix) must key the same pending confirmation and the same
    # acknowledgement, or `accept-content` can "succeed" against a key
    # `governance assess` never matches.
    data = {"path": canonical, "flagged": bool(matches), "matches": matches,
            "acknowledgeable": acknowledgeable}

    if not matches:
        emit("scan", data)
        return EXIT_OK

    # Record the pending acknowledgement when a workflow exists, so the
    # stale-confirmation guard applies to it like any other confirmation.
    #
    # Before `init` there is no state to record it in, and `accept content`
    # reads state unconditionally — so at bootstrap the acknowledgement route
    # does not exist and the message must not imply that it does. It used to,
    # and the shipped documentation taught a sequence that exits 3
    # `state_unreadable`. `acknowledgeable` says which case this is, so a caller
    # branches on the payload rather than on the prose.
    if acknowledgeable:
        state = read_state(paths)
        state["pending_confirm_action"] = f"accept_content:{canonical}"
        save_state(paths, state, args.session)

    lines = "\n".join(f"  line {m['line']}: {m['text']}" for m in matches)
    if acknowledgeable:
        remedy = (
            "Say `accept content` to proceed with this file as plain data, or "
            "edit the file and re-scan."
        )
    else:
        remedy = (
            "This WorkItem has no state yet, so nothing is automatically "
            "remembered. Either edit the flagged line so it does not read as "
            "an instruction and re-scan, or acknowledge explicitly with "
            "`accept-content --path " + canonical + "` — this works before "
            "`init` too, and `governance assess` will refuse this document "
            "again until it sees either a clean re-scan or a matching "
            "acknowledgement."
        )
    message = (
        f"Untrusted content warning: {canonical} contains lines that look like "
        f"instructions directed at the workflow engine:\n\n{lines}\n\n"
        "SDLE treats this file as data only and will NOT act on these lines.\n"
        f"{remedy}"
    )
    emit("scan", data, ok=False, reason="content_flagged", message=message)
    print(message, file=sys.stderr)
    return EXIT_REFUSED


def cmd_accept_content(args, paths: Paths) -> int:
    """Two routes, chosen by whether `--path` is given, that now converge on
    the same two effects (each used to touch only its own store, so
    accepting through one route still left `governance assess` refusing
    on the other's behalf) — both write the durable content acknowledgement
    `governance assess` checks, and both clear a matching state-backed
    pending confirmation when one exists.

    Bare `accept-content` still requires state to exist (`state_unreadable`
    otherwise) and still trusts the one pending confirmation `scan` recorded,
    without re-scanning — the post-init route every existing test and
    document pins. `accept-content --path <file>` is additive (DEF-RR-001):
    it re-scans the named file itself rather than trusting a prior `scan`
    call, and works both before and after `init`.

    A pending file that has since been deleted refuses `artifact_missing`
    before anything is checked or changed — mirroring `--path`'s own refusal
    for a missing file — rather than silently reporting success with no
    acknowledgement written. Both immediate post-init audit entries below
    carry the same `content_acknowledgement_marker` the deferred pre-init
    replay (`record_scan_acknowledgement_audit`) looks for, so an
    acknowledgement already audited here is never audited a second time at
    the next advance. Both routes are validated through `safe_repo_path` —
    the bare route's path came from `state.json`, itself written by an
    earlier, already-validated `scan`, but the *filesystem* can have changed
    since (a symlink retargeted between scan and acceptance); re-resolving
    now, and reading the same resolved target this validates, closes that
    window rather than trusting a string written a step earlier.
    """
    path_arg = getattr(args, "path", None)
    if path_arg:
        target, canonical = safe_repo_path(paths, path_arg)
        if not target.is_file():
            raise Refused("artifact_missing", f"No such file: {path_arg}",
                          {"path": path_arg})
        raw = target.read_bytes()
        matches = scan_text(raw.decode("utf-8", errors="replace"))
        if not matches:
            raise Refused("no_pending_confirmation",
                          "No flagged content is pending acknowledgement.",
                          {"path": path_arg})
        sha = hashlib.sha256(raw).hexdigest()
        # State is read, and so validated, BEFORE the acknowledgement store is
        # touched: a state that cannot be read refuses, and a refusal leaves
        # every store as it found it. Writing the store first changed the
        # security decision record on a command that then reported failure.
        state = read_state(paths) if paths.state_file.is_file() else None
        write_content_acknowledgement(paths, canonical, sha, args.session)
        if state is not None:
            pending = state.get("pending_confirm_action") or ""
            if pending == f"accept_content:{canonical}":
                state["pending_confirm_action"] = None
            append_audit(
                paths, state, phase=state.get("current_phase", "unknown"),
                event="content_accepted",
                message=(f"User accepted flagged content in {canonical} "
                         f"{content_acknowledgement_marker(canonical, sha)}."),
                artifact=canonical,
            )
            save_state(paths, state, args.session)
        emit("accept-content", {"file": canonical, "sha256": sha})
        return EXIT_OK

    state = read_state(paths)
    pending = state.get("pending_confirm_action") or ""
    if not pending.startswith("accept_content:"):
        raise Refused("no_pending_confirmation",
                      "No flagged content is pending acknowledgement.",
                      {"pending": pending or None})
    flagged = pending.split(":", 1)[1]
    # `flagged` is a key the engine itself wrote (by an earlier `scan`), so
    # this is a live re-check of the filesystem, never a re-validation of
    # untrusted input — but `safe_repo_path` refuses `path_invalid` for a
    # spelling `scan` should never have produced, which surfaces a state
    # corruption honestly instead of reading whatever `project_root / flagged`
    # happens to resolve to.
    target, canonical = safe_repo_path(paths, flagged)
    if not target.is_file():
        raise Refused("artifact_missing",
                      f"No such file: {flagged} (the file the pending "
                      "confirmation names is no longer on disk).",
                      {"path": flagged})
    raw = target.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    write_content_acknowledgement(paths, canonical, sha, args.session)
    state["pending_confirm_action"] = None
    append_audit(
        paths, state, phase=state.get("current_phase", "unknown"),
        event="content_accepted",
        message=(f"User accepted flagged content in {canonical} "
                 f"{content_acknowledgement_marker(canonical, sha)}."),
        artifact=canonical,
    )
    save_state(paths, state, args.session)
    emit("accept-content", {"file": canonical, "sha256": sha})
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
# user's implementation.
#
# `.sdle/` used to be here whole. ADR-013 narrows it to the three members the
# engine actually writes during a lifecycle, because the configuration root
# also holds two things a human authors — `config.json` and `policies/` — and
# an uncommitted edit to either is exactly the kind of change the guard exists
# to surface before an implementation mixes it in. Narrowing makes the guard
# strictly *stricter*; nothing that was reported before stops being reported.
#
#   .sdle/baseline.json          written by `establish_baseline` at the final
#                                gate. Owned for the original reason the whole
#                                directory was: one WorkItem's baseline write
#                                must not trip another WorkItem's guard.
#   .sdle/implementation-state/  execution records of maintenance runs.
#   .sdle/architecture/          the shared architecture catalog, written by
#                                `architecture apply`/`realize` during the very
#                                lifecycle whose preflight this is (ADR-013).
#
# `workitems/<id>/.sdle/` and `workitems/<id>/architecture/` are both already
# covered by the `workitems/` entry, so the WorkItem placement artifacts need
# no rule of their own.
# The `.sdle/` members are spelled relative to the repository root because
# this tuple is compared against git status output, which is. They are the
# only literals for those three directory names outside `Paths`; both lists
# that need them (`implementation_exclusions` is the other) derive from
# `Paths` where they can and are checked against each other by
# `test_units_architecture.py`.
SDLE_OWNED_PREFIXES = (
    ".workflow/",
    ".sdle/baseline.json",
    ".sdle/implementation-state/",
    ".sdle/architecture/",
    "workitems/", ".specify/", "design/", "reviews/",
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
    # The character class includes `-` and `_` so the current sk-proj-... format
    # is matched whole. The key must not continue a word, or any hyphenated
    # word ending in "sk" (risk-adaptive-gate-policy, task-management-...) is
    # reported as a credential.
    ("secret API key", r"(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{20,}"),
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
    tests never ran must not reach the implementation gate unchallenged."""
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
    cannot waive the need for it.
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


@dataclass(frozen=True)
class Exclusions:
    """What is engine bookkeeping rather than implementation, frozen once.

    Two kinds, because they are matched differently and conflating them was a
    defect: ``files`` are exact paths compared with equality, ``prefixes`` are
    directories compared with ``startswith``. Matching an exact path as a
    prefix silently hid its siblings — ``workitems/index.md`` also hid
    ``workitems/index.md.backup``.

    Frozen and passed by value because both evidence commands need the *same*
    answer: `security-review evidence` selects changes and then renders a diff,
    and re-deriving between the two let a registry write land in the middle and
    give the two halves different boundaries.
    """

    files: tuple[str, ...]
    prefixes: tuple[str, ...]

    def hides(self, path: str) -> bool:
        return path in self.files or path.startswith(self.prefixes)

    def pathspecs(self) -> list[str]:
        """Git exclusions for the same set.

        ``literal`` is load-bearing: without it a registry cell containing a
        glob character would be interpreted by git while Python compared it
        literally, and the change list and the rendered diff would disagree.
        """
        return [f":(exclude,literal){item}" for item in
                (*self.files, *(prefix.rstrip("/") for prefix in self.prefixes))]


def registry_ids_at(paths: Paths, ref: str) -> set[str]:
    """Well-formed WorkItem ids in the registry as it stood at ``ref``.

    Absent is empty, matching `read_index`'s contract for an absent file: a
    base commit predating the registry is an ordinary history, not a fault.
    Unparseable is an integrity failure rather than a silent fallback — either
    fallback (this registry only, or exclude everything) yields evidence that
    looks trustworthy and is not.
    """
    relative = workitem_index_file(paths).relative_to(
        paths.project_root).as_posix()
    code, text = git(paths, "show", f"{ref}:{relative}")
    if code != 0:
        return set()
    try:
        rows = parse_index(text, workitem_index_file(paths))
    except IntegrityError as exc:
        raise IntegrityError(
            "index_malformed_at_base",
            f"The WorkItem registry as it stood at the pinned implementation "
            f"base {ref} cannot be parsed ({exc.message}), so which WorkItems "
            "existed then cannot be established, and the implementation change "
            "set cannot be trusted to be this WorkItem's.",
            {"base_ref": ref, "path": relative},
        ) from None
    return {row["WorkItem"].strip() for row in rows
            if workitem_id_wellformed(row.get("WorkItem", "").strip())}


def implementation_exclusions(paths: Paths, state: dict) -> Exclusions:
    """Paths that are engine bookkeeping, never implementation.

    One list for both consumers of the implementation change set — the implementation gate's
    manifest and the security-review evidence — so they cannot disagree about
    what the implementation is. It stays an explicit, narrow list and is
    deliberately **not** SDLE_OWNED_PREFIXES: that would silently drop
    requirements/ and design/ edits from the manifest. It carries the
    relocation/ownership exclusions, including the repository-global
    configuration root, so both consumers exclude the same paths.

    **Every other WorkItem's tree is excluded (F-102).** WorkItem records are
    versioned by design, so B advancing a phase while A implements put B's
    `state.json`, `audit.md`, evidence and identity inside A's manifest and A's
    security-review diff — another WorkItem's governed record shown to a
    reviewer as A's implementation, and scanned for secrets as if it were.

    Two deliberate choices in how that exclusion is computed:

    * **Per WorkItem, not the whole `workitems/` prefix.** A blanket prefix
      would also hide the bound WorkItem's own tree. Only its `.sdle/` runtime
      and its Spec Kit feature directory are not implementation; anything else
      it changes under its own directory is a change a reviewer should see.
    * **Enumerated from the registry, not by globbing the directory.** A
      directory under `workitems/` that no row claims is an anomaly — `validate`
      reports it as `runtime_state_outside_workitem` — and an anomaly that
      appeared during an implementation belongs in front of the reviewer, not
      filtered out of the evidence by the filter's own convenience.

    `workitems/index.md` is excluded too, and that one is a judgement rather
    than a deduction. It is engine-owned and it changes whenever *any* WorkItem
    is created, so leaving it in means every reviewer of a concurrent run sees
    a registry row that is not theirs. The cost is that a hand-edited registry
    during implementation no longer surfaces here; its controls are the write
    fence and `validate`, which is where a registry edit is a governance
    question rather than an implementation one.

    The owning ids are the union of the registry **now** and the registry at
    the pinned base. Reading only the current one reproduced the defect in
    reverse: delete a WorkItem's row and directory during an implementation and
    every one of its deletions is reported as this WorkItem's work, with the
    registry change that would have explained it hidden by the rule above. A
    row whose id is not well formed is given no directory to own, so a
    malformed cell cannot hide a tree.
    """
    # ADR-013 narrowed the dirty-tree guard's view of `.sdle/` to the three
    # members the engine writes; this list is narrowed identically, so the
    # two boundaries agree. The consequence is deliberate: a `config.json` or
    # `policies/` edit made during an implementation now both trips the
    # preflight AND appears in the manifest a reviewer reads, instead of
    # tripping one and vanishing from the other.
    # Named `boundary`, not `config_root`: the latter is a `Paths` member
    # name, and the containment proof in `test_units_repo_config.py` reads
    # every name a function references — a local that shadows a member name
    # would read as a second boundary reader.
    boundary = paths.config_root_relative
    excluded = [
        paths.runtime_relative + "/",          # this WorkItem's runtime
        f"{boundary}/baseline.json",           # engine-written at the gate
        f"{boundary}/implementation-state/",   # engine-written records
        f"{boundary}/architecture/",           # the shared catalog
        ".specify/",                           # Spec Kit's own tree
    ]
    feature_directory = speckit_ref(state)["featureDirectory"]
    if feature_directory:
        excluded.append(feature_directory.rstrip("/") + "/")

    root = workitems_root(paths).relative_to(paths.project_root).as_posix()
    owning = {row["WorkItem"].strip() for row in read_index(paths)
              if workitem_id_wellformed(row.get("WorkItem", "").strip())}
    base = state.get("implementation_base_ref")
    if base and git_available(paths):
        owning |= registry_ids_at(paths, base)
    excluded += [f"{root}/{other}/" for other in sorted(owning)
                 if other != paths.workitem]
    return Exclusions(
        files=(workitem_index_file(paths)
               .relative_to(paths.project_root).as_posix(),),
        prefixes=tuple(excluded),
    )


def _nul_fields(text: str) -> list[str]:
    return [field for field in text.split("\0") if field != ""]


def implementation_changes(paths: Paths, state: dict) -> list[dict]:
    """The implementation change set, measured from the pinned base.

    ``implementation_base_ref`` is the commit `implement preflight` pinned
    before any implementation was written. Everything the implementation did
    since is the diff from that commit to the *working tree* — which covers
    changes committed after the base, staged changes and unstaged changes in
    one comparison — plus untracked files, which no diff reports. Comparing
    against the current ``HEAD`` instead would make a change committed during
    implementation vanish from the implementation gate and from the secrets scan.

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
        old = (entry.get("old_path") or "").replace("\\", "/")
        # A rename has two sides and either may be excluded. Filtering on the
        # destination alone dropped the whole entry, so moving application code
        # *into* another WorkItem's tree erased the fact that it left `src/` —
        # a silent omission of a deletion, which is the failure this exclusion
        # exists to prevent. Each side is projected on its own:
        #
        #   visible  -> visible    R old -> new
        #   visible  -> excluded   D old   (it went somewhere out of scope)
        #   excluded -> visible    A new   (it arrived from out of scope)
        #   excluded -> excluded   omitted
        if entry.get("status") == "R" and old:
            hidden_old, hidden_new = excluded.hides(old), excluded.hides(normal)
            if hidden_old and hidden_new:
                continue
            if hidden_new:
                entry = {**entry, "path": old, "status": "D", "old_path": None}
                normal = old
            elif hidden_old:
                entry = {**entry, "status": "A", "old_path": None}
        elif excluded.hides(normal):
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
        # Measured from the pinned base, committed + staged + unstaged
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
        # Kept, and recorded as exactly what it is. It cannot carry the
        # implementation gate: that gate refuses any result but a run that
        # actually passed.
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

    # The structured record the implementation gate reads. Claimed before the manifest is
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
        f"Phase: implement ({state.get('progress') or 'unknown'})\n"
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
        # Advisory, so the orchestrator can say *now* that the implementation gate will refuse
        # rather than letting the user discover it at the gate. the implementation gate itself
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

    # The same change set the implementation gate's manifest lists, from the same pinned
    # base. An unpinned base is a refusal, exactly as for the manifest — never
    # a silent `HEAD~1`, a range nobody chose — because a review of the wrong
    # range is worse than no review.
    changes = implementation_changes(paths, state)
    # The diff is taken with the selector's own exclusions as a pathspec, so
    # it covers exactly the tracked entries of `changes` without passing every
    # path on the command line.
    excludes = implementation_exclusions(paths, state).pathspecs()
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
        # Always true: an unpinned base is a refusal, never a
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

    # ADR-012. Checking a directory listing here was wrong in both
    # directions: it passed because some unrelated document existed, and it
    # failed because the root was empty while the bound sources lived
    # elsewhere. `requirements` is what this WorkItem declared.
    try:
        requirements = bound_sources(paths)
    except Refused:
        requirements = []
        problems.append("requirements_unbound")
    absent = [relative for relative in requirements
              if not (root / relative).is_file()]
    if absent:
        problems.append("requirements_source_missing")

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
            # ADR-012 replaced one vague `requirements_missing` with two that
            # each name what to do. "There is nothing in a directory" was never
            # the question; "this WorkItem has not said what it is about" and
            # "what it said it is about is not there" are.
            "requirements_unbound": "This WorkItem has not declared which "
            "requirement documents it is about. Run `requirements bind "
            "--source <path>` (repeatable), or `--all-current` to bind every "
            "document under requirements/ exactly as it stands now.",
            "requirements_source_missing": "This WorkItem is bound to "
            "requirement documents that are not in the repository. Run "
            "`requirements show` to see which, then restore them or re-bind.",
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
                f"{len(consts.phase_to_gate_key)} gates.",
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
    # which is what those strings have always meant. It is not the registry's
    # phase count: the registry holds phases that GREENFIELD does not run.
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
    # rejected: `modules/security-review.md` cross-references the security-review phase and is
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
    # label: HOTFIX's `gate_implement` is Gate 3, GREENFIELD's is Gate 8.
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

    # ADR-013's lifecycle invariant, stated as a property rather than as
    # documentation: placement, then its gate, then the specification — in
    # EVERY flow, GREENFIELD included. `MANDATORY_FLOW_PHASES` already forces
    # both phases to be present; what it cannot express is the order, and an
    # architecture gate that fell behind `spec_draft` would govern a boundary
    # a specification had already assumed.
    ordering: list[str] = []
    for name, flow in sorted(flows.items()):
        phases = list(flow.phases)
        for phase in (ARCHITECTURE_PHASE, ARCHITECTURE_GATE_KEY, "spec_draft"):
            if phase not in phases:
                ordering.append(f"{name} does not contain {phase}")
        if any(f"{name} does not contain" in problem for problem in ordering):
            continue
        placement = phases.index(ARCHITECTURE_PHASE)
        gate = phases.index(ARCHITECTURE_GATE_KEY)
        spec = phases.index("spec_draft")
        # Adjacency, not merely order: ADR-013 says *immediately* precedes
        # twice, and a phase slipped between the placement and its gate — or
        # between the gate and the specification — would be governed by
        # neither.
        if (gate, spec) != (placement + 1, placement + 2):
            ordering.append(
                f"{name} orders them {placement}/{gate}/{spec}; the "
                "placement must immediately precede its gate, which must "
                "immediately precede spec_draft")
    checks.append(
        Check("architecture_phase_precedes_spec_in_every_flow", not ordering,
              "; ".join(ordering) if ordering
              else f"all {len(flows)} flows place {ARCHITECTURE_PHASE} before "
                   f"{ARCHITECTURE_GATE_KEY} before spec_draft"))

    # And its governance invariant: no classification, no risk level and no
    # policy dictionary makes `gate_architecture` omittable. Exhaustive over
    # the built-in policy's own vocabulary rather than argued in prose.
    relaxable: list[str] = []
    for name, flow in sorted(flows.items()):
        if ARCHITECTURE_GATE_KEY not in flow.gate_keys:
            continue
        for wi_type in WORKITEM_TYPES:
            for level in GOVERNANCE_LEVELS:
                model = gate_requirements(
                    consts, flow, {"type": wi_type, "flow": name}, level,
                    GOVERNANCE_POLICY_BUILTIN)
                if ARCHITECTURE_GATE_KEY not in model["required_gates"]:
                    relaxable.append(f"{name}/{wi_type}/{level}")
    checks.append(
        Check("architecture_gate_is_universally_required", not relaxable,
              "omittable at: " + ", ".join(relaxable) if relaxable
              else f"{ARCHITECTURE_GATE_KEY} is required for every flow, "
                   f"type and risk level ({len(WORKITEM_TYPES)}×"
                   f"{len(GOVERNANCE_LEVELS)} combinations checked)"))
    return checks


# A capability file may point at another one. The reference is a load
# directive in prose, so it is matched as the literal path it has to be.
_CAPABILITY_REF_RE = re.compile(r"(?:modules|guidelines)/[A-Za-z0-9._-]+\.md")

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
    # Orphan detection covers BOTH capability homes. A guideline no row names
    # is exactly as dead as a module no row names, and worse in one way: an
    # unmapped guideline reads like shipped product heuristics while never
    # reaching a phase (ADR-014).
    on_disk = sorted(
        f"{directory.name}/{p.name}"
        for directory in capability_directories(paths)
        for p in directory.glob("*.md") if p.is_file())
    named = {f"{Path(value).parent.name}/{Path(value).name}" for value in values}
    orphans = [name for name in on_disk if name not in named]
    coverage = []
    if unlinted:
        coverage.append(f"capabilities outside the linted file set: {unlinted}")
    if orphans:
        coverage.append(f"capability files no row names: {orphans}")
    checks.append(Check(
        "every_capability_file_is_linted", not coverage,
        "; ".join(coverage) if coverage
        else f"{len(resolved)} capability files, all linted, no orphans"))

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
FORBIDDEN_AGENT_TOOLS = ("Bash", "PowerShell", "Write", "Edit", "MultiEdit",
                         "NotebookEdit", "Agent", "Task")
# The tools the frontmatter fence must match. `Bash` and `PowerShell` are on the
# list because a shell is all it takes to run `gate approve`. The hook module
# carries the same set as `FILE_WRITE_TOOLS + SHELL_TOOLS`; a test pins the two.
FENCED_AGENT_TOOLS = ("Write", "Edit", "MultiEdit", "NotebookEdit", "Bash",
                      "PowerShell")
PRODUCT_AGENT_FENCE = "product-agent-fence"
PRODUCT_AGENT_FENCE_LAUNCHER = "run-hook.sh"
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

    Read with two narrow regexes rather than parsed: the engine is
    standard-library only and §11's policy-format decision
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
      are convention.

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
        if (PRODUCT_AGENT_FENCE not in front
                or PRODUCT_AGENT_FENCE_LAUNCHER not in front):
            unfenced.append(f"{path.name} registers no {PRODUCT_AGENT_FENCE} "
                            f"through {PRODUCT_AGENT_FENCE_LAUNCHER}")
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
    """The cross-file rules for the `discovery` registry phase.

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
# tutorials, README and the Reference Guide did not, so the
# document named "the lifecycle" contradicted the other five. Listing the files
# here and checking them is the repo's standing answer to that class of bug --
# a checklist rots, a lint rule does not.
FLOW_COUNT_DOCS = (
    "README.md",
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

# Transition contract §17 "Documentation" names nine targets that the
# documentation set must cover. A checklist in a plan rots; a lint rule does
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
    for directory in capability_directories(paths):
        files.extend(sorted(
            (p for p in directory.glob("*.md") if p.is_file()),
            key=lambda p: p.name))
    files.extend(product_agent_files(paths))
    return files


def capability_directories(paths: Paths) -> tuple[Path, ...]:
    """Every directory a `CAPABILITY_MAP` row may name a file in.

    Two homes, one rule. `modules/` holds *procedure* — how a phase is
    executed, how a gate is presented. `guidelines/` holds *heuristics* —
    what to prefer and why (ADR-014). Both are lazily loaded capability
    files, so both are enumerated here: the orphan check, the content checks
    and the "is it linted" check all read this one function rather than
    growing a second hand-maintained list.
    """
    return tuple(directory for directory
                 in (paths.modules_dir, paths.guidelines_dir)
                 if directory.is_dir())


def _repo_root(paths: Paths) -> Path:
    """The source repo, when the skill lives inside one."""
    candidate = paths.skill_root.parent.parent.parent
    return candidate if (candidate / "README.md").is_file() else paths.project_root


def _check_single_state_template(paths: Paths) -> Check:
    """The template must exist in exactly one place.

    A second copy embedded in SKILL.md would drift from the template. One
    fact, one file.
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
    """The state schema version, and every display copy of it that exists.

    The operational fact is the state schema: the template's
    `workflow_version` and `CURRENT_VERSION` must agree, and they are required.
    A display copy of the version (the SKILL.md heading, the README title, the
    Reference Guide header, a documentation page's `Applies to` line, the
    optional frontmatter mention) is not required to exist, and a page that
    states no version is not a mismatch. A copy that *is* present must equal
    the schema version, so the number cannot drift where it is repeated.
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
    if frontmatter:  # an optional display copy: absent is fine, wrong is not
        found["SKILL.md frontmatter"] = frontmatter.group(1)
    if heading:
        found["SKILL.md heading"] = heading.group(1)

    root = _repo_root(paths)
    readme = root / "README.md"
    if readme.is_file():
        text = readme.read_text(encoding="utf-8")
        title = re.search(r"^# SDLE.*\(v([0-9]+\.[0-9]+)\)", text, re.MULTILINE)
        if title:
            found["README title"] = title.group(1)

    guide = root / "docs" / "SDLE-Reference-Guide.md"
    if guide.is_file():
        header = re.search(r"SDLE v([0-9]+\.[0-9]+)",
                           guide.read_text(encoding="utf-8"))
        if header:
            found["Reference Guide header"] = header.group(1)

    # The documentation-set READMEs may open with an
    # `**Applies to:** SDLE vX.Y` line. An unchecked restatement of the version
    # is how a bump leaves documents claiming the old one, so any that carries
    # the line is compared. Derived by glob, not listed: a directory added
    # later is covered without an edit here.
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

    `README.md` restates `REPO_CONFIG_DEFAULTS` as a fenced JSON literal, and
    nothing but this check binds the two together — a documented default that
    can drift from the engine's, which for a boundary is a documented lie
    waiting to happen. Deleting the example was rejected: it is genuinely
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
    """§17's nine documentation targets exist and say something.

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
    could be present, lint-green and linked from nowhere — invisible to every
    reader.

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
    **excludes the terminal `complete`** -- its own docstring calls it the
    denominator of the progress fraction -- because `complete` is a state a
    WorkItem lands in, not a phase anybody executes: `PROGRESS_MAP` numbers
    GREENFIELD from 1 to its last phase and gives `complete` no number of its
    own, sharing the final fraction with `gate_security`. A document that counted it printed a table disagreeing
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

    architecture_p = subparsers.add_parser(
        "architecture",
        help="Repository architecture memory and WorkItem placement (ADR-013)."
    )
    architecture_sub = architecture_p.add_subparsers(
        dest="subcommand", required=True)
    arch_schema = architecture_sub.add_parser(
        "schema", help="The closed placement vocabulary. Writes nothing."
    )
    arch_schema.set_defaults(handler=cmd_architecture_schema)
    arch_show = architecture_sub.add_parser(
        "show", help="The repository architecture catalog. Writes nothing."
    )
    arch_show.set_defaults(handler=cmd_architecture_show)
    arch_assess = architecture_sub.add_parser(
        "assess", help="Validate a placement proposal and record it."
    )
    arch_assess.add_argument(
        "--input", required=True,
        help="Path to the structured architecture proposal JSON.")
    arch_assess.set_defaults(handler=cmd_architecture_assess)
    arch_apply = architecture_sub.add_parser(
        "apply",
        help="Apply an approved placement to the catalog (replay-safe)."
    )
    arch_apply.set_defaults(handler=cmd_architecture_apply)
    arch_realize = architecture_sub.add_parser(
        "realize",
        help="Mark an applied placement realized after implementation."
    )
    arch_realize.set_defaults(handler=cmd_architecture_realize)

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
    # Distinct dest: argparse would otherwise clobber the global --workitem
    # with this one's default.
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

    req_p = subparsers.add_parser(
        "requirements", help="The documents this WorkItem is about.")
    req_sub = req_p.add_subparsers(dest="subcommand", required=True)
    req_bind = req_sub.add_parser(
        "bind", help="Declare this WorkItem's requirement documents.")
    req_bind.add_argument(
        "--source", action="append",
        help="A requirement document, relative to the repository root. "
             "Repeatable.")
    req_bind.add_argument(
        "--all-current", action="store_true",
        help="Bind every file under requirements/ as it is right now, "
             "recorded as an exact list.")
    req_bind.add_argument(
        "--primary",
        help="Which bound document names the project. Inferred when exactly "
             "one document is bound; required for more than one.")
    req_bind.set_defaults(handler=cmd_requirements_bind)
    req_show = req_sub.add_parser("show", help="Report the binding.")
    req_show.set_defaults(handler=cmd_requirements_show)

    sr_p = subparsers.add_parser("security-review", help="Security-review support.")
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
                          help="Absence is tolerated (checklist_draft).")
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
    accept_content_p = subparsers.add_parser(
        "accept-content", help="Acknowledge flagged file content."
    )
    accept_content_p.add_argument(
        "--path", required=False,
        help="Acknowledge this file explicitly (works before init too), "
             "instead of consuming state.json's one pending confirmation.")
    accept_content_p.set_defaults(handler=cmd_accept_content)
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

    impl_p = subparsers.add_parser("implement", help="Implementation support.")
    impl_sub = impl_p.add_subparsers(dest="subcommand", required=True)
    ipre = impl_sub.add_parser(
        "preflight", help="Dirty-tree guard; pin implementation_base_ref."
    )
    ipre.add_argument("--bypass", action="store_true",
                      help="Proceed despite a dirty tree (logged).")
    ipre.set_defaults(handler=cmd_implement_preflight)

    man_p = subparsers.add_parser("manifest", help="Implementation-gate artifact.")
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
