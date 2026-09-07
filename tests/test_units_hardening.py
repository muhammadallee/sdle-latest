"""T11 M6 — the sixteen mandatory hardening tests of transition contract §17.

§17's "Hardening tests / Mandatory" list has **sixteen** bullets. Each one is
implemented here as `test_t11_nNN_...`, except **N12** (policy-floor
enforcement), which landed in M4 beside the governance regime it guards and is
named `test_n12_*` in `test_units_governance.py`.

Two rules shape this file:

1. **A hardening test that only re-runs an existing assertion is not a
   hardening test.** Where coverage already existed the docstring names it and
   states what is added.
2. **Nothing here is asserted that was not observed on this host.** §17 also
   mandates a Windows/Linux test while CI has never run in this migration.
   N16 asserts only what is observable here — POSIX separators in emitted
   payloads, normalised path construction, both launchers agreeing on the
   interpreter contract — and asserts nothing whose truth would require
   executing on Linux. See the T11 plan §10.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest

from conftest import FIXTURE_WORKITEM_ID, REPO_ROOT, SDLE_PY, Project, sdle
from test_units_artifact_review import review_for_gate
from test_units_speckit_binding import install_speckit_scripts
from test_units_workitem_runtime import legacy_state as plant_legacy
from test_units_workitem_runtime import legacy_workflow as plant_legacy_runtime

EXIT_OK, EXIT_REFUSED, EXIT_USAGE, EXIT_INTEGRITY = 0, 1, 2, 3

# T11 N7 - the migration's write points, in order. Asserted by
# `test_t11_n7_the_migration_write_sequence_is_exactly_this`.
MIGRATION_WRITES: tuple[str, ...] = (
    'audit.md',                      # 1 the copied ledger
    'implementation-manifest.md',    # 2 T02 NB-5: never exercised before T11
    'completion-summary.json',       # 3 T02 NB-5: never exercised before T11
    'migration-evidence.json',       # 4 (name normalised: carries a stamp)
    'execution.json',                # 5
    'audit.md',                      # 6 the workflow_migrated entry
    'state.json',                    # 7 THE COMMIT MARKER, written last
    'workitem.json',                 # 8 post-commit metadata (T11 TR23)
    '.active-context.json',          # 9 post-commit convenience
)
COMMIT_WRITE = 7  # 1-based index of the state.json commit write


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def index_file(project: Project) -> Path:
    return project.root / "workitems" / "index.md"


def digests(root: Path) -> dict[str, str]:
    """SHA-256 of every file under ``root``, keyed by repo-relative path."""
    out: dict[str, str] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            key = str(path.relative_to(root)).replace("\\", "/")
            out[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


def runtime_digests(project: Project) -> dict[str, str]:
    return digests(project.runtime)


# ==========================================================================
# N3 — WorkItem index merge-conflict validation
# ==========================================================================
#
# There was no coverage at all. `read_index` rejects a row whose cell count
# differs from `INDEX_COLUMNS` and never rewrites the file; what was untested
# is the shape that actually arrives in practice — a git merge that left its
# conflict markers in `workitems/index.md`.

CONFLICT = (
    "<<<<<<< HEAD\n"
    "| 2026-01-01 | wi-a | feature | Alpha | Ours |\n"
    "=======\n"
    "| 2026-01-01 | wi-b | feature | Bravo | Theirs |\n"
    ">>>>>>> feature/theirs\n"
)


def plant_conflict(project: Project) -> bytes:
    target = index_file(project)
    target.write_text(
        target.read_text(encoding="utf-8") + CONFLICT,
        encoding="utf-8", newline="\n")
    return target.read_bytes()


def test_t11_n3_a_merge_conflict_in_the_index_is_an_integrity_failure(project):
    """Exit 3, the file untouched, and no attempt to guess what was meant."""
    before = plant_conflict(project)

    result = project.run("state", "get", "--field", "workitem")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "index_malformed", result
    assert index_file(project).read_bytes() == before, (
        "a malformed registry must never be rewritten")


def test_t11_n3_workitem_create_refuses_rather_than_repairing(project):
    """`workitem create` is RUNTIME_FREE, so it is the one command that could
    plausibly "fix" the file on the way past. It must not."""
    before = plant_conflict(project)

    result = project.run("workitem", "create", "--name", "Should Not Land")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "index_malformed", result
    assert index_file(project).read_bytes() == before
    assert "Should Not Land" not in index_file(project).read_text(
        encoding="utf-8")


def test_t11_n3_a_badly_resolved_merge_produces_a_duplicate_error(project):
    """The second case: markers removed, but both sides' ids kept. The file is
    now well-formed, so `read_index` is happy — `validate` is what catches it."""
    target = index_file(project)
    rows = target.read_text(encoding="utf-8").rstrip("\n").splitlines()
    duplicate = [line for line in rows if FIXTURE_WORKITEM_ID in line]
    assert duplicate, "fixture row must be findable"
    target.write_text("\n".join(rows + duplicate) + "\n",
                      encoding="utf-8", newline="\n")

    result = project.run("validate")

    errors = [f for f in result.data["findings"]
              if f["check"] == "duplicate_workitem_id"]
    assert len(errors) == 1, result.data["findings"]
    assert errors[0]["severity"] == "error"
    assert errors[0]["workitem"] == FIXTURE_WORKITEM_ID


def test_t11_n3_a_corrupt_index_outranks_a_legacy_runtime_at_init(
    bare_project,
):
    """T11 TR19, pinned so the ordering stops being untested.

    T03-7 observed that `init` in a repository with *both* a corrupt registry
    and a legacy `.workflow/` reports `index_malformed` rather than
    `legacy_workflow_present`. That is the right order — a registry too broken
    to read is the more fundamental problem, and the legacy refusal would send
    the user to a `migrate-workflow` that cannot register anything — but until
    now nothing said so. Disposition: NOT-A-DEFECT, pinned here.
    """
    (bare_project.root / ".workflow").mkdir()
    (bare_project.root / ".workflow" / "state.json").write_text(
        "{}\n", encoding="utf-8", newline="\n")
    workitems = bare_project.root / "workitems"
    workitems.mkdir(exist_ok=True)
    (workitems / "index.md").write_text(
        "| Created | WorkItem |\n|---|---|\n", encoding="utf-8", newline="\n")

    result = bare_project.run("init", session="tr19")

    assert result.exit_code == EXIT_INTEGRITY, result
    assert result.reason == "index_malformed", result


# ==========================================================================
# N4 — corrupt state
# ==========================================================================


def test_t11_n4_a_corrupt_state_is_exit_three_and_writes_nothing(started):
    """Existing coverage asserts the reason (`test_units_state.py`). What is
    added: the ledger is byte-identical afterwards, no temp sibling is left
    behind, and `doctor` — the command a user reaches for when something is
    wrong — still answers usefully instead of raising."""
    before_audit = started.audit_file.read_bytes()
    started.state_file.write_text("{ not json", encoding="utf-8")

    for invocation in (("state", "get"), ("advance", "--to", "spec_draft"),
                       ("doctor",), ("resume",)):
        result = started.run(*invocation, session="n4")
        assert result.exit_code == EXIT_INTEGRITY, (invocation, result)
        assert result.reason == "state_unreadable", (invocation, result)
        # Useful, not merely correct: it names the file and the way out.
        assert "state.json" in result.envelope["message"], invocation
        assert "reset workflow" in result.envelope["message"], invocation

    assert started.audit_file.read_bytes() == before_audit
    leftovers = [p.name for p in started.runtime.iterdir()
                 if p.name.endswith(".tmp")]
    assert leftovers == [], leftovers


# ==========================================================================
# N5 — corrupt audit
# ==========================================================================


def test_t11_n5_a_tampered_chain_is_located_and_writes_nothing(started):
    """Existing coverage asserts that `audit verify` reports
    `audit_chain_broken` on an edited ledger. What is added: the refusal
    **locates** the break rather than merely reporting one, the detection is a
    pure read (the whole runtime is byte-identical afterwards), and the
    evidence survives — a later lifecycle command cannot make the tamper go
    away.

    **Declared narrowing of §17's N5 wording.** The bullet says "refuses at the
    choke point". SDLE's audit choke point for *integrity* is `audit verify`
    (and `migrate-workflow`, which refuses `legacy_audit_broken` — asserted in
    N7). Lifecycle commands do **not** re-verify the whole ledger on every
    invocation, by design: the chain is tamper-*evident*, prevention is the
    write fence plus the single-writer rule, and `audit rebaseline` exists
    precisely because a detected mismatch is acknowledged rather than fatal.
    Turning every `advance` into a full-ledger verification would be a new
    gate on the hot path, would change what a GREENFIELD run does, and would
    have to be introduced at the last milestone of the last phase. T11 does
    not do it; the residual is recorded in ADR-008 rather than dropped, and
    the property that actually matters — the tamper stays visible — is
    asserted below.
    """
    started.ok("audit", "append", "--phase", "constitution_draft",
               "--event", "note", "--message", "second real entry")
    ledger = started.audit_file.read_text(encoding="utf-8")
    assert ledger.count("workflow_initialized") == 1
    started.audit_file.write_text(
        ledger.replace("workflow_initialized", "tampered_event"),
        encoding="utf-8", newline="\n")
    before = runtime_digests(started)

    verified = started.run("audit", "verify")
    assert verified.exit_code == EXIT_INTEGRITY, verified
    assert verified.reason == "audit_chain_broken", verified
    # Names *which* entry, not merely that something is wrong: tampering with
    # the first entry breaks the second entry's `Prev` link.
    assert verified.data["chain_ok"] is False, verified.data
    assert verified.data["broken_at_entry"] == 2, verified.data
    assert verified.data["matches"] is False, verified.data

    # Detection wrote nothing at all.
    assert runtime_digests(started) == before, (
        "an integrity refusal must leave the whole runtime byte-identical")

    # And the evidence is not erased by continuing to work: the break is still
    # there, at the same entry, after a lifecycle command has appended to the
    # ledger. A tamper cannot be laundered by using the tool.
    started.ok("advance", "--to", "gate_constitution", session="n5")
    still = started.run("audit", "verify")
    assert still.exit_code == EXIT_INTEGRITY, still
    assert still.data["broken_at_entry"] == 2, still.data


def test_t11_n5_rebaseline_is_the_only_way_past_and_is_itself_audited(started):
    """The acknowledged remediation, pinned: nothing else clears the finding,
    and clearing it leaves a record that it was cleared."""
    ledger = started.audit_file.read_text(encoding="utf-8")
    started.audit_file.write_text(
        ledger.replace("workflow_initialized", "tampered_event"),
        encoding="utf-8", newline="\n")

    assert started.run("audit", "verify").exit_code == EXIT_INTEGRITY
    started.ok("advance", "--to", "gate_constitution", session="n5b")
    assert started.run("audit", "verify").exit_code == EXIT_INTEGRITY

    started.ok("audit", "rebaseline", session="n5b")

    assert started.ok("audit", "verify").data["matches"] is True
    assert "rebaselin" in started.audit_file.read_text(encoding="utf-8").lower()


# ==========================================================================
# N6 — interrupted atomic write
# ==========================================================================


def test_t11_n6_a_stray_partial_temp_is_never_authoritative(started):
    """`write_atomic` removes its own temp on every *handled* failure — three
    tests in `test_units_infra.py` pin that. A stray temp can therefore only
    come from a hard process kill, and what matters then is that it is inert.

    **Declared narrowing of §17's N6 wording.** The plan's N6 also asks that a
    stray temp "does not survive the next successful write". It does survive:
    each `write_atomic` creates a uniquely named temp and renames *that* one,
    so nothing sweeps a stranger's leftovers. Adding such a sweep would let one
    writer delete a concurrent writer's in-flight temp and turn a benign race
    into an error — a new failure mode introduced at the last milestone for a
    housekeeping benefit. The safety property the bullet exists to protect is
    asserted here in full; the housekeeping half is recorded as not done.
    """
    partial = started.runtime / ".state.json.deadbeef.tmp"
    partial.write_text('{"current_phase": "complete", "progress": "18/18"',
                       encoding="utf-8")
    good = started.state_file.read_bytes()

    assert started.ok("state", "get", "--field",
                      "current_phase").data["value"] == "constitution_draft"
    assert started.ok("resume").data["current_phase"] == "constitution_draft"
    assert started.ok("audit", "verify").data["matches"] is True
    assert started.state_file.read_bytes() == good

    # A successful write afterwards produces a correct file; the partial is
    # never merged into it, prepended to it, or read as a fallback.
    started.ok("audit", "append", "--phase", "constitution_draft",
               "--event", "note", "--message", "a real write after the crash")
    reread = json.loads(started.state_file.read_text(encoding="utf-8"))
    assert reread["current_phase"] == "constitution_draft"
    assert reread["progress"] != "18/18"


def test_t11_n6_a_failed_write_through_the_engine_leaves_no_partial(
    started, monkeypatch,
):
    """The same property at the engine's level rather than the primitive's: a
    crash between temp and rename during a real lifecycle command."""
    before_state = started.state_file.read_bytes()
    before_audit = started.audit_file.read_bytes()

    def boom(*args, **kwargs):
        raise OSError("simulated crash before rename")

    monkeypatch.setattr(sdle.os, "replace", boom)
    with pytest.raises(OSError):
        started.run("advance", "--to", "gate_constitution", session="n6")
    monkeypatch.undo()

    assert started.state_file.read_bytes() == before_state
    assert started.audit_file.read_bytes() == before_audit
    assert [p.name for p in started.runtime.iterdir()
            if p.name.endswith(".tmp")] == []


# ==========================================================================
# N9 — missing Spec Kit
# ==========================================================================


def test_t11_n9_an_absent_speckit_fails_closed_and_writes_nothing(started):
    """Existing coverage asserts the reason on `feature bind`. What is added:
    the whole runtime is byte-identical after the refusal, every Spec Kit-owned
    entry point behaves the same way, and no feature directory is created."""
    shutil.rmtree(started.root / ".specify")
    before = runtime_digests(started)

    bound = started.run("feature", "bind", session="n9")
    assert bound.exit_code == EXIT_REFUSED, bound
    assert bound.reason == "speckit_missing", bound

    # `feature resolve` fails closed too, on its own ground: with no Spec Kit
    # there is no feature anywhere to adopt, and it refuses rather than
    # inventing a directory. Recorded with its own reason so the two refusals
    # stay distinguishable (invariant 7).
    resolved = started.run("feature", "resolve", session="n9")
    assert resolved.exit_code == EXIT_REFUSED, resolved
    assert resolved.reason == "feature_unresolved", resolved

    # `feature capabilities` is a diagnostic and never refuses — a user whose
    # Spec Kit is missing must still be able to ask what the engine can see.
    seen = started.ok("feature", "capabilities", session="n9")
    assert seen.data["speckit_present"] is False, seen

    assert runtime_digests(started) == before
    assert not (started.root / "workitems" / FIXTURE_WORKITEM_ID
                / "specs").exists()


# ==========================================================================
# N10 — unsupported Spec Kit capability
# ==========================================================================


def test_t11_n10_a_missing_capability_refuses_before_any_workitem_write(
    started,
):
    """Existing coverage asserts `state.json` is unchanged. What is added: the
    refusal is reached before **any** WorkItem-scoped write — the whole
    `.sdle/` directory is byte-identical, not just one file — and no Spec Kit
    feature directory is created for the WorkItem."""
    install_speckit_scripts(started, "SPECIFY_INIT_DIR")  # one of two
    before = runtime_digests(started)

    result = started.run("feature", "bind", session="n10")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "speckit_capability_missing", result
    assert result.data["missing"] == ["SPECIFY_FEATURE_DIRECTORY"], result
    assert runtime_digests(started) == before
    assert not (started.root / "workitems" / FIXTURE_WORKITEM_ID
                / "specs").exists()


# ==========================================================================
# N8 - ambiguous resolution
# ==========================================================================


def test_t11_n8_zero_workitems_with_legacy_state_names_both_steps_in_order(
    bare_project,
):
    """The post-removal meaning of "ambiguous": with rung 6 gone, a repository
    with no WorkItem and a legacy `.workflow/` resolves to nothing at all.
    `test_units_workitem_runtime.py` pins the refusal itself (N17); what is
    added here is that EVERY non-RUNTIME_FREE command says the same thing, in
    the same order, so the recovery does not depend on which command the user
    happened to run.
    """
    plant_legacy(bare_project)

    for invocation in (("state", "get"), ("advance", "--to", "spec_draft"),
                       ("resume",), ("gate", "show", "--gate", "1"),
                       ("audit", "verify"), ("doctor",)):
        result = bare_project.run(*invocation, session="n8")
        assert result.exit_code == EXIT_REFUSED, (invocation, result)
        assert result.reason == "workitem_required", (invocation, result)
        message = result.envelope["message"]
        assert "workitem create" in message, invocation
        assert "migrate-workflow" in message, invocation
        assert message.index("workitem create") < message.index(
            "migrate-workflow"), (invocation, message)
        assert result.data.get("legacy_state"), (invocation, result)


def test_t11_n8_more_than_one_plausible_workitem_is_refused_with_no_pick(
    bare_project,
):
    """The ladder never guesses. Two registered WorkItems, no flag, no active
    context: the refusal lists both candidates and binds neither \u2014 asserted
    on disk, not merely in the payload."""
    bare_project.ok("workitem", "create", "--name", "Alpha")
    bare_project.ok("workitem", "create", "--name", "Bravo")

    result = bare_project.run("init", session="n8b")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "workitem_ambiguous", result
    candidates = result.data["candidates"]
    ids = sorted(c["id"] if isinstance(c, dict) else c for c in candidates)
    assert ids == ["alpha", "bravo"], result
    # Nothing was picked: neither runtime exists.
    for wid in ("alpha", "bravo"):
        assert not (bare_project.root / "workitems" / wid / ".sdle").exists()


# ==========================================================================
# N11 - stale baseline
# ==========================================================================


def test_t11_n11_an_invalidated_baseline_blocks_an_iterative_workitem(
    git_project,
):
    """§17's bullet, implemented against the behaviour T08 deliberately chose.

    **Declared divergence from the plan's N11 wording.** The plan says "a
    stale baseline blocks an ITERATIVE WorkItem". It does not, on purpose:
    T08's `baseline_findings` makes a *changed* reference a warning, because
    `design_generation` runs in ITERATIVE and rewrites the design document, so
    treating change as invalidation would force the third WorkItem in any
    repository back into full rediscovery - exactly what §26 item 22 forbids.
    `test_units_baseline.py` pins that decision and the T11 plan §7.2 lists
    that file as one the implementer may not change.

    So the bullet is implemented as the two true statements it decomposes
    into: a **materially invalid** baseline blocks ITERATIVE outright, and a
    **stale** one can never be relied on silently, because `baseline validate`
    refuses it. Both refusals now name the commit the baseline was established
    at, which is the "invalidating commit" the bullet asks for - added by T11
    (`baseline_commit`), because without it a finding says what is wrong
    without saying which repository state it was ever right for.
    """
    git_project.write_artifact("design/app/app-design.md")
    document = git_project.establish_baseline()
    assert document["commit"], "fixture baseline must record a commit"
    (git_project.root / "design" / "app" / "app-design.md").unlink()

    shown = git_project.run("baseline", "show").data
    assert shown["status"] == "INVALID", shown
    assert any(f["check"] == "baseline_reference_missing"
               for f in shown["findings"]), shown

    validated = git_project.run("baseline", "validate")
    assert validated.exit_code == EXIT_REFUSED, validated
    assert validated.reason == "baseline_not_valid", validated
    assert validated.data["baseline_commit"] == document["commit"], validated

    assessed = git_project.record_governance(**{
        "classification": {"type": "enhancement", "flow": "ITERATIVE"}})
    assert assessed.exit_code == EXIT_OK  # the assessment itself is fine
    blocked = git_project.run("init", session="n11")
    assert blocked.exit_code == EXIT_REFUSED, blocked
    assert blocked.reason == "baseline_required", blocked
    assert blocked.data["baseline_commit"] == document["commit"], blocked
    assert not git_project.state_file.exists()


def test_t11_n11_a_stale_baseline_can_never_be_relied_on_silently(
    git_project,
):
    """The other half: STALE does not block the flow (T08's decision), but it
    is never invisible - `baseline validate` refuses it and names the commit,
    and `baseline show` reports STALE with the changed reference."""
    git_project.write_artifact("design/app/app-design.md")
    document = git_project.establish_baseline()
    git_project.write_artifact("design/app/app-design.md",
                               "# Redesigned\n\n" + "Different content. " * 8)

    validated = git_project.run("baseline", "validate")
    assert validated.exit_code == EXIT_REFUSED, validated
    assert validated.data["status"] == "STALE", validated
    assert validated.data["baseline_commit"] == document["commit"], validated
    assert any(f["check"] == "baseline_reference_changed"
               for f in validated.data["findings"]), validated


# ==========================================================================
# N13 - gate omission evidence
# ==========================================================================


def test_t11_n13_an_omission_carries_everything_needed_to_re_derive_it(
    git_project,
):
    """T09 pins that an omission is audited. What is added: the recorded
    evidence is **sufficient**, on its own, to answer "under what policy, from
    which governance record, at what level" - including the governance
    record's own SHA-256, which T11 added because the omission previously
    fingerprinted the policy but not the record the level came from."""
    from test_units_gate_policy import walk

    walk(git_project, stop="gate_design")
    review_for_gate(git_project, "gate_design")

    omitted = git_project.ok("gate", "omit", "--gate", "gate_design")

    entry = git_project.state()["approvals"]["gate_design"]
    governance = git_project.runtime / "governance.json"
    expected_sha = hashlib.sha256(governance.read_bytes()).hexdigest()

    assert entry["decision"] == "omitted_by_policy"
    # Which rules. `policy_sha256` is null for the BUILT-IN policy, which has
    # no file to hash - the identifying fact there is the source, and the
    # payload carries both, so the pair is always sufficient.
    assert "policy_sha256" in entry, entry
    assert omitted.data["policy"]["source"], omitted
    assert (entry["policy_sha256"]
            == omitted.data["policy"]["sha256"]), (entry, omitted.data)
    assert entry["governance_sha256"] == expected_sha, entry   # which record
    assert entry["risk_level"] == "LOW", entry                 # which level
    assert entry["reasons"] == [], entry
    assert omitted.data["governance_sha256"] == expected_sha, omitted

    blocks = [b for b in git_project.audit_file.read_text(
        encoding="utf-8").split("## AUDIT") if "gate_omitted" in b]
    assert len(blocks) == 1, blocks
    assert "No human approved this gate" in blocks[0]
    assert git_project.ok("audit", "verify").data["matches"] is True


def test_t11_n13_completion_is_refused_and_the_evidence_shows_why(
    git_project,
):
    """The completion half of the bullet. T09 already pins that the terminal
    gate refuses `gate_omission_invalidated`; what is added here is the tie
    back to the *evidence*: the omission recorded which governance record it
    rested on, and that fingerprint no longer matches the record on disk - so
    the refusal is corroborated by what was written down at the time, not only
    by a fresh derivation. The whole runtime is byte-identical afterwards, not
    merely the ledger."""
    from test_units_gate_policy import resume, walk

    walk(git_project, stop="gate_design", level="LOW")
    review_for_gate(git_project, "gate_design")
    git_project.ok("gate", "omit", "--gate", "gate_design")
    recorded_sha = git_project.state()["approvals"]["gate_design"][
        "governance_sha256"]
    assert recorded_sha

    resume(git_project, stop="gate_security")
    git_project.record_governance(
        classification={"type": "enhancement", "flow": "GREENFIELD"},
        risk={"signals": [], "proposedLevel": "HIGH", "uncertainty": "LOW"})
    review_for_gate(git_project, "gate_security")

    before = runtime_digests(git_project)
    refused = git_project.run("gate", "approve", "--gate", "gate_security",
                              session="n13")

    assert refused.exit_code == EXIT_REFUSED, refused
    assert refused.reason == "gate_omission_invalidated", refused
    assert refused.data["invalidated"] == ["gate_design"], refused
    assert runtime_digests(git_project) == before
    assert not (git_project.runtime / "completion-summary.json").exists()

    # The recorded evidence corroborates it: the governance record the
    # omission rested on is not the one on disk any more.
    live_sha = hashlib.sha256(
        (git_project.runtime / "governance.json").read_bytes()).hexdigest()
    assert live_sha != recorded_sha
    assert git_project.state()["approvals"]["gate_design"][
        "governance_sha256"] == recorded_sha, (
            "the evidence must not be rewritten by a later assessment")


# ==========================================================================
# N14 / N15 - restart after /clear, and in a fresh session
# ==========================================================================


CONTEXT_KEYS = ("workitem", "flow", "current_phase", "status", "progress",
                "position", "next_phase", "label", "gate", "pending",
                "capabilities")


def reconstruct(project: Project, session: str) -> dict:
    """Everything a cold session needs, through a REAL subprocess that has
    never seen the conversation."""
    result = project.run_cli("resume", session=session)
    assert result.exit_code == EXIT_OK, result
    return result.data


def test_t11_n14_a_cleared_conversation_reconstructs_from_disk_alone(
    started_git,
):
    """§17 "restart after /clear", post-removal meaning: same working
    directory, same active context, no conversation.

    Existing coverage (`test_n9_a_fresh_process_reconstructs_the_workitem`)
    proves a fresh process resolves the WorkItem. What is added: the whole
    operating context - phase, flow, gate disposition and the capability files
    to load - is reconstructed **mid-flow**, and the reconstruction is proven
    to be a pure read by asserting `audit.md` is byte-identical across it.
    """
    project = started_git
    project.record_governance()
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution", session="n14")

    before = project.audit_file.read_bytes()
    before_state = project.state_file.read_bytes()

    data = reconstruct(project, "n14")

    for key in CONTEXT_KEYS:
        assert key in data, key
    assert data["workitem"] == FIXTURE_WORKITEM_ID
    assert data["flow"] == "GREENFIELD"
    assert data["current_phase"] == "gate_constitution"
    assert data["gate"]["gate"] == "gate_constitution"
    assert data["gate"]["required"] in (True, False)
    assert data["capabilities"], "a resuming session must be told what to load"

    assert project.audit_file.read_bytes() == before, "a read must not write"
    assert project.state_file.read_bytes() == before_state


def test_t11_n15_a_fresh_session_resumes_from_durable_state_alone(started_git):
    """§17 "restart in a fresh Claude session", post-removal meaning: a
    different session token and no persisted active context.

    Same reconstruction as N14, but with `workitems/.active-context.json`
    deleted and a brand-new `--session`. It must be identical: if it is not,
    something was being carried in the developer-local context file, which is
    gitignored and therefore not durable state.
    """
    project = started_git
    project.record_governance()
    project.write_artifact(".specify/memory/constitution.md")
    project.ok("advance", "--to", "gate_constitution", session="n14")

    expected = reconstruct(project, "n14")

    context = project.root / "workitems" / ".active-context.json"
    if context.is_file():
        context.unlink()
    before = project.audit_file.read_bytes()

    data = reconstruct(project, "a-completely-new-session-token")

    assert {k: data[k] for k in CONTEXT_KEYS} == {
        k: expected[k] for k in CONTEXT_KEYS}
    assert project.audit_file.read_bytes() == before
    # The WorkItem-local lock must not falsely block a new session either.
    assert project.run("state", "get",
                       session="a-completely-new-session-token"
                       ).exit_code == EXIT_OK


# ==========================================================================
# N1 - two WorkItems in separate branches / worktrees
# ==========================================================================
#
# `test_two_worktrees_drive_two_workitems_with_no_flag` already proves the
# resolution half: two worktrees, no `--workitem`, each binds its own. What is
# added here is the *run*: both are driven all the way to `complete` with the
# other one live and unfinished throughout, and the two ledgers are then
# proven independent - each verifies on its own, and neither mentions the
# other's execution id.
#
# "Interleaved" here means command-level alternation between two live
# runtimes, not OS-level concurrency: the suite runs `main()` in-process and
# cannot safely fork two interpreters at one another. That is stated rather
# than implied.


# The contract's "Execution identity" section, transcribed as a pattern:
# `<3-letter-git-user-prefix>-<UTC-datetime>`, example `muh-20260816T171501Z`.
# The prefix is 1-3 characters because the documented fallback chain can yield
# a shorter slug. Second resolution is the contract's, not an accident, and is
# why two executions can legitimately share a label — see the note in the N1
# test below.
EXECUTION_ID_FORMAT = re.compile(r"^[a-z0-9]{1,3}-\d{8}T\d{6}Z$")


def worktree_pair(bare_project, tmp_path):
    """A repository with two registered WorkItems and a second worktree."""
    bare_project.init_git()
    a_id = bare_project.ok("workitem", "create", "--name", "Alpha").data["id"]
    b_id = bare_project.ok("workitem", "create", "--name", "Bravo").data["id"]
    bare_project.git("add", "-A")
    bare_project.git("commit", "-q", "-m", "register workitems")

    second_root = tmp_path / "worktree-b"
    added = bare_project.git("worktree", "add", "-q", "-b", "feat-b",
                             str(second_root))
    assert added.returncode == 0, f"git worktree add failed: {added.stderr}"

    a = Project(bare_project.root, bare_project.skill_root, a_id, pin=True)
    b = Project(second_root, bare_project.skill_root, b_id, pin=True)
    return a, b


def test_t11_n1_two_worktrees_each_complete_a_run_with_independent_ledgers(
    bare_project, tmp_path,
):
    from test_units_gate_policy import resume

    a, b = worktree_pair(bare_project, tmp_path)

    # Opening segment, alternating command by command between two live
    # runtimes. Any shared runtime state would surface here first.
    a.record_governance()
    b.record_governance()
    a_init = a.ok("init", session="dev-a")
    b_init = b.ok("init", session="dev-b")
    a_execution = a_init.data["execution_id"]
    b_execution = b_init.data["execution_id"]

    # TP-003 category 2 — an assertion deliberately superseded, and the reason
    # is worth writing down because it looked like a defect first.
    #
    # This originally read `assert a_execution != b_execution`, taken from the
    # plan's N1 wording ("neither contains the other's execution id"). It is
    # **not a property the engine provides**, and asserting it made this test
    # depend on wall-clock alignment: it passes whenever the two `init` calls
    # straddle a second boundary and fails when they do not. A hardening test
    # whose outcome turns on the clock is worse than no hardening test.
    #
    # The engine is correct here and was not changed. The contract's own
    # "Execution identity" section *specifies* the format as
    # `<3-letter-git-user-prefix>-<UTC-datetime>` at second resolution, with
    # the example `muh-20260816T171501Z`, and calls it **lightweight** identity
    # belonging to "execution/audit metadata". Two WorkItems started by the
    # same user in the same second therefore share a label by design, and
    # widening the format to force uniqueness would violate the contract to
    # satisfy a test. `execution_identity` is byte-identical to its form at the
    # product baseline; nothing regressed.
    #
    # What is asserted instead is the property N1 actually exists to prove, and
    # it is strictly stronger than string inequality: the two execution
    # *records* are separate files, each bound to its own WorkItem, and each
    # names its own worktree. Sharing a timestamp label cannot make either
    # record ambiguous, because the record itself says which WorkItem it is
    # for. The ledger half of the same claim is asserted at the end of this
    # test, against the WorkItem id rather than the execution id.
    assert EXECUTION_ID_FORMAT.match(a_execution), a_execution
    assert EXECUTION_ID_FORMAT.match(b_execution), b_execution
    a_record = json.loads(
        (a.runtime / "execution.json").read_text(encoding="utf-8"))
    b_record = json.loads(
        (b.runtime / "execution.json").read_text(encoding="utf-8"))
    assert a_record["workitem"] == a.workitem
    assert b_record["workitem"] == b.workitem
    assert a_record["workitem"] != b_record["workitem"]
    assert a_record["git"]["worktree"] != b_record["git"]["worktree"]
    assert a_record["executionId"] == a_execution
    assert b_record["executionId"] == b_execution

    a.write_artifact(".specify/memory/constitution.md")
    b.write_artifact(".specify/memory/constitution.md")
    a.ok("advance", "--to", "gate_constitution", session="dev-a")
    b.ok("advance", "--to", "gate_constitution", session="dev-b")

    # B stays here, mid-flow, for the whole of A's run.
    b_before = digests(b.runtime)
    resume(a, stop=None)
    assert a.state()["current_phase"] == "complete"
    assert digests(b.runtime) == b_before, (
        "a complete run under A must not move one byte of B")

    resume(b, stop=None)
    assert b.state()["current_phase"] == "complete"

    # Each ledger verifies on its own terms.
    assert a.ok("audit", "verify").data["matches"] is True
    assert b.ok("audit", "verify").data["matches"] is True

    a_ledger = a.audit_file.read_text(encoding="utf-8")
    b_ledger = b.audit_file.read_text(encoding="utf-8")

    # Neither ledger names the other WorkItem or its runtime. The isolation
    # boundary is the WorkItem, not the execution id: an execution id is
    # <git-prefix>-<UTC second> and is deliberately lightweight execution
    # METADATA (contract §8), so two WorkItems started by the same user in the
    # same second can legitimately share one. Asserting on the WorkItem is
    # therefore both the stronger and the correct claim.
    assert b.workitem not in a_ledger
    assert a.workitem not in b_ledger
    assert f"workitems/{b.workitem}" not in a_ledger
    assert f"workitems/{a.workitem}" not in b_ledger
    assert a.state()["workitem"] == a.workitem
    assert b.state()["workitem"] == b.workitem
    assert not (bare_project.root / ".workflow").exists()


# ==========================================================================
# N2 - state isolation, extended to everything T05-T09 added
# ==========================================================================


def test_t11_n2_a_full_run_moves_no_byte_of_another_workitems_sdle(
    git_project,
):
    """Existing coverage compares `state.json` and `audit.md`. What is added:
    the artifacts later phases introduced - `execution.json`,
    `governance.json`, `reviews.json`, the evidence directory - are covered
    too, by comparing WI-B's **whole** `.sdle/` tree byte for byte across a
    full WI-A run, so a newly added runtime file is included automatically
    rather than needing this list to be maintained."""
    from test_integration_01_happy_path import (EXPECTED_TRAVERSAL,
                                                run_happy_path)

    git_project.ok("workitem", "create", "--name", "Wi B")
    a = git_project.as_workitem(FIXTURE_WORKITEM_ID)
    b = git_project.as_workitem("wi-b")

    # Give B a runtime that exercises the later phases' artifacts.
    b.record_governance()
    b.ok("init", session="sb")
    b.write_artifact(".specify/memory/constitution.md")
    b.ok("advance", "--to", "gate_constitution", session="sb")
    review_for_gate(b, "gate_constitution")

    populated = {p.name for p in b.runtime.iterdir()}
    for expected in ("state.json", "execution.json", "audit.md",
                     "governance.json", "reviews.json"):
        assert expected in populated, (expected, populated)
    assert (b.runtime / "evidence").is_dir()

    before = digests(b.runtime)
    assert run_happy_path(a) == EXPECTED_TRAVERSAL

    assert digests(b.runtime) == before
    assert b.ok("audit", "verify").data["matches"] is True
    assert b.state()["workitem"] == "wi-b"


# ==========================================================================
# N7 - interrupted legacy migration
# ==========================================================================
#
# `migrate-workflow` is now the ONLY path off the pre-v1.14 layout, so an
# interruption in it matters more than it did, not less. The existing test
# parameterises four write points; T02 NB-5 recorded that it never exercised
# the manifest or completion-summary copies. This covers every write point,
# with a legacy runtime that carries both.


def legacy_with_every_artifact(bare_project) -> str:
    """A legacy runtime that exercises every copy step of the migration."""
    wid = plant_legacy_runtime(bare_project)
    legacy = bare_project.root / ".workflow"
    (legacy / "implementation-manifest.md").write_text(
        "# Implementation Manifest\n\nA legacy manifest. " * 4,
        encoding="utf-8", newline="\n")
    (legacy / "completion-summary.json").write_text(
        json.dumps({"legacy": True}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return wid


def migration_write_sequence(bare_project, wid, monkeypatch) -> list[str]:
    seen: list[str] = []
    real = sdle.write_atomic

    def spy(path, text):
        name = Path(path).name
        # The evidence file carries the execution stamp; normalise it so the
        # sequence below is a stable literal rather than a pattern.
        if name.startswith('migration-') and name.endswith('.json'):
            name = 'migration-evidence.json'
        seen.append(name)
        return real(path, text)

    monkeypatch.setattr(sdle, "write_atomic", spy)
    assert bare_project.ok("migrate-workflow", "--workitem",
                           wid).exit_code == EXIT_OK
    monkeypatch.undo()
    return seen


def test_t11_n7_the_migration_write_sequence_is_exactly_this(
    bare_project, monkeypatch,
):
    """The constant the parameterisation below rests on, asserted rather than
    assumed: if a write point is added or removed, this fails loudly instead
    of the coverage silently narrowing."""
    wid = legacy_with_every_artifact(bare_project)
    assert migration_write_sequence(bare_project, wid,
                                    monkeypatch) == list(MIGRATION_WRITES)
    assert MIGRATION_WRITES[COMMIT_WRITE - 1] == 'state.json', (
        'COMMIT_WRITE must index the commit marker')


@pytest.mark.parametrize("fail_at", range(1, COMMIT_WRITE + 1))
def test_t11_n7_an_interruption_at_any_write_point_is_recoverable(
    bare_project, monkeypatch, fail_at,
):
    """At every write point up to and including the commit: `.workflow/` is
    byte-identical, no resolvable target exists, and a re-run succeeds."""
    wid = legacy_with_every_artifact(bare_project)
    before = digests(bare_project.root / ".workflow")

    real = sdle.write_atomic
    calls = {"n": 0}

    def flaky(path, text):
        calls["n"] += 1
        if calls["n"] >= fail_at:
            raise OSError("simulated interruption")
        return real(path, text)

    monkeypatch.setattr(sdle, "write_atomic", flaky)
    with pytest.raises(OSError):
        bare_project.run("migrate-workflow", "--workitem", wid)
    monkeypatch.undo()

    target = bare_project.root / "workitems" / wid / ".sdle"
    assert not (target / "state.json").exists(), fail_at
    assert digests(bare_project.root / ".workflow") == before, fail_at

    assert bare_project.ok("migrate-workflow", "--workitem",
                           wid).exit_code == EXIT_OK
    assert (target / "state.json").is_file()
    assert (target / "implementation-manifest.md").is_file()
    assert (target / "completion-summary.json").is_file()
    assert digests(bare_project.root / ".workflow") == before


@pytest.mark.parametrize(
    "fail_at", range(COMMIT_WRITE + 1, len(MIGRATION_WRITES) + 1))
def test_t11_n7_a_post_commit_interruption_leaves_a_correct_runtime(
    bare_project, monkeypatch, fail_at,
):
    """T11 TR23 (T02 NB-4), pinned rather than argued.

    Two writes happen *after* the commit marker - `workitem.json` and the
    developer-local `.active-context.json`. T02's verifier recorded that they
    sit outside the migration's commit window; T11's disposition is
    **DEFERRED**, and this test is why that is safe: an interruption there
    leaves a **correct, resolvable** WorkItem runtime whose ledger verifies,
    with at most slightly stale convenience metadata that the next command
    re-derives. `.workflow/` is still byte-identical, and the migration is not
    re-run into a half state.
    """
    wid = legacy_with_every_artifact(bare_project)
    before = digests(bare_project.root / ".workflow")

    real = sdle.write_atomic
    calls = {"n": 0}

    def flaky(path, text):
        calls["n"] += 1
        if calls["n"] >= fail_at:
            raise OSError("simulated interruption after the commit")
        return real(path, text)

    monkeypatch.setattr(sdle, "write_atomic", flaky)
    try:
        result = bare_project.run("migrate-workflow", "--workitem", wid)
    except OSError:
        result = None
    monkeypatch.undo()

    if MIGRATION_WRITES[fail_at - 1] == ".active-context.json":
        # The last write is the developer-local active-context pointer, and
        # its failure is deliberately swallowed: a completed migration must
        # not be reported as failed because a convenience file could not be
        # written. The pointer is simply absent, and the next command
        # re-derives it.
        assert result is not None and result.exit_code == EXIT_OK, result
        assert not (bare_project.root / "workitems"
                    / ".active-context.json").exists()
    else:
        assert result is None, "the interruption must surface"

    target = bare_project.root / "workitems" / wid / ".sdle"
    assert (target / "state.json").is_file(), fail_at
    assert digests(bare_project.root / ".workflow") == before, fail_at

    bound = bare_project.as_workitem(wid)
    assert bound.ok("state", "get", "--field",
                    "workitem").data["value"] == wid
    assert bound.ok("audit", "verify").data["matches"] is True


def test_t11_n7_a_legacy_only_repository_recovers_in_exactly_two_commands(
    bare_project,
):
    """Plan §3.3 and acceptance criterion A4, end to end through the real CLI.

    This is the test that says the removals did not brick anybody: a
    repository carrying only a pre-v1.14 `.workflow/` reaches a working
    WorkItem runtime with the two commands the refusal names, and nothing
    else. Driven through `run_cli`, so argv parsing and the process boundary
    are part of what is proven.
    """
    plant_legacy_runtime(bare_project)
    shutil.rmtree(bare_project.root / "workitems")
    before = digests(bare_project.root / ".workflow")

    blocked = bare_project.run_cli("state", "get", session="a4")
    assert blocked.exit_code == EXIT_REFUSED, blocked
    assert blocked.reason == "workitem_required", blocked

    created = bare_project.run_cli("workitem", "create", "--name", "Recovery")
    assert created.exit_code == EXIT_OK, created
    wid = created.data["id"]

    migrated = bare_project.run_cli("migrate-workflow", "--workitem", wid)
    assert migrated.exit_code == EXIT_OK, migrated

    working = bare_project.run_cli("state", "get", "--field", "workitem",
                                   session="a4")
    assert working.exit_code == EXIT_OK, working
    assert working.data["value"] == wid
    assert bare_project.run_cli("audit", "verify").exit_code == EXIT_OK
    assert digests(bare_project.root / ".workflow") == before


# ==========================================================================
# N16 — Windows/Linux behaviour, limited to what is observable on this host
# ==========================================================================


def _looks_absolute(text: str) -> bool:
    return bool(re.match(r"^(?:[A-Za-z]:[\\/]|[\\/])", text))


def _strings(value):
    """Every string in a nested JSON payload."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


def test_t11_n16_every_emitted_path_uses_posix_separators(started_git):
    """Observed on Windows, where a native separator would actually appear.

    A payload carrying `workitems\\wi\\.sdle` would make every consumer's
    comparison platform-dependent, and the dry-run transcripts — which are the
    behavioural specification — would differ between the two CI runners.
    """
    started_git.write_artifact(".specify/memory/constitution.md")
    started_git.ok("artifact", "record", "--path",
                   ".specify/memory/constitution.md", session="n16")

    root = str(started_git.root)
    checked = 0
    for invocation in (("state", "get"), ("resume",), ("header",),
                       ("workitem", "resolve"), ("workitem", "list"),
                       ("validate",), ("baseline", "show"), ("doctor",),
                       ("audit", "verify"), ("drift", "check")):
        result = started_git.run(*invocation, session="n16")
        assert result.envelope, invocation
        for text in _strings(result.envelope):
            # An ABSOLUTE path is the host filesystem's own and is native by
            # design; the claim is about the repository-relative paths a
            # consumer compares, records and prints.
            if text.startswith(root) or _looks_absolute(text):
                continue
            assert "\\" not in text, (invocation, text)
            checked += 1
    assert checked > 50, checked  # not vacuous


def test_t11_n16_no_os_sep_literal_reaches_an_emitted_payload():
    """Every use of `os.sep` in the engine is a normalisation *into* `/`."""
    source = Path(SDLE_PY).read_text(encoding="utf-8")
    occurrences = [line.strip() for line in source.splitlines()
                   if "os.sep" in line]
    assert occurrences, "the needle must match something or this is vacuous"
    for line in occurrences:
        assert 'replace(os.sep, "/")' in line or line.endswith(
            'os.sep, "/")'), line


def test_t11_n16_the_only_text_writer_pins_the_line_ending():
    """`write_atomic` is the engine's only text writer, and it writes LF on
    every platform. Without that, a state file written on Windows and read on
    Linux would hash differently and every artifact SHA would be
    platform-dependent."""
    tree = ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))
    writers = [n for n in ast.walk(tree)
               if isinstance(n, ast.FunctionDef) and n.name == "write_atomic"]
    assert len(writers) == 1
    keywords = {k.arg for call in ast.walk(writers[0])
                if isinstance(call, ast.Call) for k in call.keywords}
    assert "newline" in keywords
    assert 'newline="\\n"' in ast.unparse(writers[0]).replace("'", '"')

    # And no second text writer slipped in beside it.
    source = Path(SDLE_PY).read_text(encoding="utf-8")
    assert ".write_text(" not in source
    assert ".write_bytes(" not in source


def test_t11_n16_both_launchers_agree_on_the_interpreter_contract():
    """§17's cross-platform bullet, in the one form observable here: the two
    launchers must promise the same thing, or the engine is only as portable
    as whichever one a reviewer happened to read."""
    sh = (REPO_ROOT / "scripts" / "sdle.sh").read_text(encoding="utf-8")
    ps1 = (REPO_ROOT / "scripts" / "sdle.ps1").read_text(encoding="utf-8")

    for text in (sh, ps1):
        assert "SDLE_PYTHON" in text          # the same override
        assert "3.11" in text                 # the same floor
        assert "uv" in text                   # the same last resort
        assert "sdle.py" in text              # the same target
    # Neither may hard-code the other platform's interpreter path.
    assert "C:\\" not in sh and "C:\\" not in ps1


def test_t11_n16_no_powershell_only_cmdlet_reaches_a_prompt_file(project):
    """The mechanical half of the claim, delegated to the rule that owns it."""
    checks = {c["name"]: c for c in project.run("lint-skill").data["checks"]}
    assert checks["no_powershell_only_cmdlets"]["passed"] is True, checks[
        "no_powershell_only_cmdlets"]


def test_t11_n16_what_this_host_could_not_observe_is_not_asserted():
    """§17 mandates a Windows/Linux test; CI has never executed in this
    migration and there is no 3.11 interpreter on this host. The honest V1
    position is recorded in ADR-008 and asserted here as an absence: this file
    contains no assertion whose truth would require executing on Linux.
    """
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            rendered = ast.unparse(node)
            assert rendered not in {"sys.platform", "os.name",
                                    "platform.system"}, rendered
        if isinstance(node, ast.Call):
            assert ast.unparse(node.func) != "platform.system"
    imported = {alias.name for node in ast.walk(tree)
                if isinstance(node, ast.Import) for alias in node.names}
    assert "platform" not in imported
