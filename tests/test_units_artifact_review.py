"""Contract TP-011 and §12 — the governed artifact review regime.

"Artifact existence alone is not evidence of artifact quality." T06 makes that
enforceable: a governed artifact must carry a PASS review of its **exact
current content** before a gate can approve it, and the drift path is guarded
too, because approving drifted content against a review of the pre-drift
content is precisely the violation TP-011 clause 1 describes.

Three rules govern this file, following `test_units_governance.py`:

1. **No shared fixture is modified.** `conftest`'s fixtures are used as they
   are; the helper this regime needs lives here and is imported by the files
   that drive gates, exactly as `run_happy_path` already is.
2. **Freshness is derived, never stored.** Several cases below attack that
   directly by planting a stored flag and asserting it changes nothing.
3. **Review and approval are two different facts.** `artifact_shas` is the
   approval baseline and `reviews.json` is the review ledger; neither learns
   about the other, and the writer set of the first is pinned.
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

from conftest import SDLE_PY, Project, sdle

EXIT_OK = 0
EXIT_REFUSED = 1

REVIEW_TYPE = "content-review"


# --------------------------------------------------------------------------
# Helpers — local by design, and imported by the gate-driving test modules
# --------------------------------------------------------------------------


def review_for_gate(view, gate: str, result: str = "PASS", **over) -> None:
    """Record the review TP-011 requires before ``gate`` can be approved.

    Resolves the artifact through the engine's own `gate show`, so the suite
    never restates `ARTIFACT_OWNERSHIP`. A gate with no resolvable artifact
    has nothing to review and is left alone — the same carve-out E2 makes.
    """
    shown = view.ok("gate", "show", "--gate", gate).data
    if not shown["artifact_path"] or not shown["exists"]:
        return
    view.ok("artifact", "review",
            "--path", over.get("path", shown["artifact_path"]),
            "--type", over.get("type", REVIEW_TYPE),
            "--result", result,
            "--actor-type", over.get("actor_type", "test"),
            "--actor-name", over.get("actor_name", "suite"))


def reviews_of(project: Project) -> dict:
    return json.loads(
        (project.runtime / "reviews.json").read_text(encoding="utf-8"))


def audit_entries(project: Project) -> list[str]:
    return sdle.split_audit_entries(
        project.audit_file.read_text(encoding="utf-8"))


def frozen(project: Project) -> tuple:
    """The facts a refusal must leave untouched.

    The `audit.md` **bytes** are part of the tuple, not merely
    `state["audit_sha"]`: a refusal raised after an audit append but before
    `save_state` grows the append-only ledger while `audit_sha` stays put.
    E2 already refuses ahead of every audit write, so this clause holds here
    today; it is carried in the tuple so it stays held. See the twin helper
    in `test_units_governance.py` and finding B1.
    """
    state = project.state()
    ledger = (project.audit_file.read_bytes()
              if project.audit_file.is_file() else None)
    return (state["current_phase"], state["status"],
            json.dumps(state["approvals"], sort_keys=True),
            json.dumps(state["artifact_shas"], sort_keys=True),
            state["audit_sha"], ledger)


CONSTITUTION = ".specify/memory/constitution.md"


def at_gate_constitution(project: Project) -> Project:
    """Gate 1 territory: the constitution written, standing at the gate."""
    project.record_governance()
    project.ok("init", session="review")
    project.write_artifact(CONSTITUTION)
    project.ok("advance", "--to", "gate_constitution")
    return project


def sdle_ast() -> ast.Module:
    return ast.parse(Path(SDLE_PY).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# N24 — register -> review -> eligible
# --------------------------------------------------------------------------


def test_a_reviewed_artifact_can_be_approved_and_leaves_a_record(project):
    at_gate_constitution(project)

    reviewed = project.ok("artifact", "review", "--path", CONSTITUTION,
                          "--type", "constitution-review", "--result", "PASS",
                          "--actor-type", "agent", "--actor-name",
                          "sdle-architect")
    project.ok("gate", "approve", "--gate", "gate_constitution")

    ledger = reviews_of(project)
    assert ledger["reviewsVersion"] == "1"
    assert len(ledger["reviews"]) == 1
    record = ledger["reviews"][0]
    assert record["path"] == CONSTITUTION
    assert record["sha256"] == sdle.sha256_file(project.root / CONSTITUTION)
    assert record["result"] == "PASS"
    assert record["reviewType"] == "constitution-review"
    assert record["actor"] == {"type": "agent", "name": "sdle-architect"}
    assert reviewed.data["evidenceId"] == record["evidenceId"]
    assert (project.root / record["evidenceId"]).is_file()

    entries = [block for block in audit_entries(project)
               if "artifact_reviewed" in block]
    assert len(entries) == 1
    assert project.state()["approvals"]["gate_constitution"]["decision"] \
        == "approved"


def test_the_review_evidence_document_records_the_whole_record(project):
    at_gate_constitution(project)
    project.ok("artifact", "review", "--path", CONSTITUTION,
               "--type", REVIEW_TYPE, "--result", "PASS",
               "--actor-type", "human", "--actor-name", "Ada",
               "--evidence", "reviews/notes.md", "--comments", "Looks sound.")

    record = reviews_of(project)["reviews"][0]
    payload = json.loads(
        (project.root / record["evidenceId"]).read_text(encoding="utf-8"))
    assert payload["kind"] == "review"
    assert payload["record"] == record
    assert payload["detail"] == "reviews/notes.md"
    assert record["comments"] == "Looks sound."


# --------------------------------------------------------------------------
# N25 — review_missing
# --------------------------------------------------------------------------


def test_an_unreviewed_artifact_cannot_be_approved(project):
    at_gate_constitution(project)
    before = frozen(project)

    result = project.run("gate", "approve", "--gate", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_missing", result
    assert result.data["path"] == CONSTITUTION
    assert "artifact review" in result.envelope["message"]
    assert frozen(project) == before, "a refusal freezes; nothing is approved"
    assert not (project.runtime / "reviews.json").exists()


# --------------------------------------------------------------------------
# N26 — review_stale is TP-011 clause 1, verbatim
# --------------------------------------------------------------------------


def test_a_one_byte_edit_after_review_blocks_approval_until_re_review(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")
    reviewed_sha = reviews_of(project)["reviews"][0]["sha256"]

    target = project.root / CONSTITUTION
    target.write_text(target.read_text(encoding="utf-8") + "!",
                      encoding="utf-8", newline="\n")
    before = frozen(project)

    result = project.run("gate", "approve", "--gate", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_stale", result
    assert result.data["reviewed_sha"] == reviewed_sha
    assert result.data["current_sha"] != reviewed_sha
    assert result.data["current_sha"] == sdle.sha256_file(target)
    assert frozen(project) == before

    review_for_gate(project, "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution")
    assert project.state()["artifact_shas"]["gate_constitution"] == \
        sdle.sha256_file(target)


# --------------------------------------------------------------------------
# N27 — review_failed, and what supersedes what
# --------------------------------------------------------------------------


def test_a_failing_review_blocks_approval(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution", result="FAIL")
    before = frozen(project)

    result = project.run("gate", "approve", "--gate", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_failed", result
    assert result.data["result"] == "FAIL"
    assert frozen(project) == before


def test_a_later_pass_on_the_same_content_clears_an_earlier_fail(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution", result="FAIL")
    review_for_gate(project, "gate_constitution", result="PASS")

    project.ok("gate", "approve", "--gate", "gate_constitution")
    assert len(reviews_of(project)["reviews"]) == 2, "the ledger is append-only"


def test_an_earlier_pass_does_not_survive_a_later_fail(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution", result="PASS")
    review_for_gate(project, "gate_constitution", result="FAIL")

    result = project.run("gate", "approve", "--gate", "gate_constitution")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_failed", result


# --------------------------------------------------------------------------
# N28 — freshness is derived, never stored
# --------------------------------------------------------------------------


def test_no_stored_freshness_flag_exists_in_a_record(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")

    record = reviews_of(project)["reviews"][0]
    assert set(record) == {"path", "sha256", "reviewType", "result",
                           "evidenceId", "actor", "comments", "timestamp"}
    for name in ("fresh", "current", "stale", "valid"):
        assert name not in record


def test_a_hand_planted_freshness_flag_changes_nothing(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")

    target = project.root / CONSTITUTION
    target.write_text(target.read_text(encoding="utf-8") + "!",
                      encoding="utf-8", newline="\n")

    ledger = reviews_of(project)
    ledger["reviews"][0]["fresh"] = True
    ledger["reviews"][0]["current"] = True
    (project.runtime / "reviews.json").write_text(
        json.dumps(ledger, indent=2), encoding="utf-8", newline="\n")

    result = project.run("gate", "approve", "--gate", "gate_constitution")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_stale", "the predicate is recomputed"


# --------------------------------------------------------------------------
# N29 — drift re-approval is subject to the same rule
# --------------------------------------------------------------------------


def test_drift_reapproval_needs_a_review_of_the_drifted_content(project):
    """The case TP-011's staleness rule is drawn for: `_approve_drift` is
    guarded too, or a drifted artifact could be blessed by a review of the
    content it no longer has."""
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution")

    project.write_artifact(CONSTITUTION, "# Constitution\n\nRewritten.\n" * 8)
    project.ok("drift", "check", "--queue", "--pending-phase", "spec_draft")
    before = frozen(project)

    result = project.run("gate", "approve", "--gate", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_stale", result
    assert frozen(project) == before
    assert project.state()["drift_queue"] == ["gate_constitution"]

    review_for_gate(project, "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution")

    state = project.state()
    assert state["drift_queue"] == []
    assert state["artifact_shas"]["gate_constitution"] == \
        sdle.sha256_file(project.root / CONSTITUTION), "re-baselined"


# --------------------------------------------------------------------------
# N30 — the two SHA mechanisms stay separate
# --------------------------------------------------------------------------


def test_the_approval_baseline_and_the_review_ledger_never_mix(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")
    project.ok("gate", "approve", "--gate", "gate_constitution")

    shas = project.state()["artifact_shas"]
    assert set(shas) == {"gate_constitution"}
    assert all(isinstance(value, str) for value in shas.values()), \
        "artifact_shas holds a SHA per gate and no review data"

    ledger = reviews_of(project)
    text = json.dumps(ledger)
    for gate_key in ("gate_constitution", "gate_spec", "gate_security"):
        assert f'"{gate_key}"' not in text, "reviews are keyed by path, not gate"
    assert "decision" not in text and "approved" not in text


def test_the_artifact_shas_writer_set_is_unchanged(project):
    """Invariant 7: T06 adds a *second fact*, not a second writer of the
    existing one. A new name here means the approval baseline grew a writer,
    and each one has to argue for itself.

    T09 added `cmd_gate_omit`, and it argues for itself on the ground that
    made the set worth pinning: an omission is a decision about specific
    content, so it fingerprints that content exactly as an approval does.
    Leaving it out would have been the silent regression §15's preserve list
    names first — an omitted gate whose artifact could then change with no
    drift raised, because nothing had ever baselined it.
    """
    tree = sdle_ast()
    writers = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Subscript) and \
                            "artifact_shas" in ast.unparse(target):
                        writers.add(fn.name)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "pop" \
                    and "artifact_shas" in ast.unparse(node):
                writers.add(fn.name)
    assert writers == {"cmd_gate_approve", "cmd_gate_omit", "_approve_drift",
                       "cmd_drift_rebaseline", "cmd_restart"}


def test_only_the_review_command_writes_the_review_ledger():
    tree = sdle_ast()
    writers = set()
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        for node in ast.walk(fn):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                    and node.func.id == "write_atomic" \
                    and "reviews_file" in ast.unparse(node):
                writers.add(fn.name)
    assert writers == {"cmd_artifact_review"}


# --------------------------------------------------------------------------
# N31 — the audit linkage carries every TP-011 minimum field
# --------------------------------------------------------------------------


def test_the_audit_entry_carries_every_tp011_field(project):
    at_gate_constitution(project)
    project.ok("artifact", "review", "--path", CONSTITUTION,
               "--type", "architecture-review", "--result", "PASS",
               "--actor-type", "agent", "--actor-name", "sdle-architect")

    record = reviews_of(project)["reviews"][0]
    entry = [block for block in audit_entries(project)
             if "artifact_reviewed" in block][0]

    assert "artifact_reviewed" in entry                       # cl. 8, event
    assert f"**Artifact:** {CONSTITUTION}" in entry            # cl. 2, path
    assert f"**Artifact SHA (SHA-256):** {record['sha256']}" in entry  # cl. 3
    assert "**Review:** architecture-review | PASS | agent:sdle-architect" \
        in entry                                               # cl. 4, 5, 6
    assert f"**Evidence:** {record['evidenceId']}" in entry     # cl. 7
    assert entry.strip().splitlines()[-1].startswith("**Prev:** ")
    assert project.ok("audit", "verify").data["matches"] is True


def test_a_review_is_not_a_gate_decision(project):
    """The review result must not borrow the gate-decision field: a gate
    approval is a human act, and the count of them is asserted elsewhere."""
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")

    entry = [block for block in audit_entries(project)
             if "artifact_reviewed" in block][0]
    assert "**Gate Decision:** n/a" in entry


# --------------------------------------------------------------------------
# N33 — actor validation, and no subagent anywhere
# --------------------------------------------------------------------------


@pytest.mark.parametrize("actor_type", ["reviewer", "AGENT", "", "sdle"])
def test_an_ungoverned_actor_type_is_refused(project, actor_type):
    at_gate_constitution(project)
    result = project.run("artifact", "review", "--path", CONSTITUTION,
                         "--type", REVIEW_TYPE, "--result", "PASS",
                         "--actor-type", actor_type, "--actor-name", "x")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_actor_invalid", result
    assert not (project.runtime / "reviews.json").exists()


@pytest.mark.parametrize("actor_type", list(sdle.REVIEW_ACTOR_TYPES))
def test_every_governed_actor_type_is_accepted_and_recorded_verbatim(
    project, actor_type
):
    at_gate_constitution(project)
    project.ok("artifact", "review", "--path", CONSTITUTION,
               "--type", REVIEW_TYPE, "--result", "PASS",
               "--actor-type", actor_type, "--actor-name", "Ada Lovelace")
    record = reviews_of(project)["reviews"][0]
    assert record["actor"] == {"type": actor_type, "name": "Ada Lovelace"}


@pytest.mark.parametrize("bad", ["APPROVED", "pass", "", "OK"])
def test_an_ungoverned_result_is_refused(project, bad):
    at_gate_constitution(project)
    result = project.run("artifact", "review", "--path", CONSTITUTION,
                         "--type", REVIEW_TYPE, "--result", bad,
                         "--actor-type", "test", "--actor-name", "suite")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_result_invalid", result


def test_an_empty_review_type_is_refused(project):
    at_gate_constitution(project)
    result = project.run("artifact", "review", "--path", CONSTITUTION,
                         "--type", "   ", "--result", "PASS",
                         "--actor-type", "test", "--actor-name", "suite")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_type_invalid", result


def test_reviewing_a_missing_artifact_is_refused(project):
    at_gate_constitution(project)
    result = project.run("artifact", "review", "--path", "nowhere/absent.md",
                         "--type", REVIEW_TYPE, "--result", "PASS",
                         "--actor-type", "test", "--actor-name", "suite")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "artifact_missing", result


SPAWNING_ATTRS = (
    "run", "Popen", "call", "check_call", "check_output", "getoutput",
    "system", "popen", "execv", "execvp", "execve", "execl", "execlp",
    "spawnv", "spawnvp", "spawnl", "spawnlp", "posix_spawn",
)


def _spawn_sites(tree):
    """Every `subprocess.*` / `os.*` call in the engine that starts a process,
    with the name of the function it sits in."""
    enclosing = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(node):
                enclosing[id(child)] = node.name
    sites = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id in ("subprocess", "os")
                and func.attr in SPAWNING_ATTRS):
            continue
        sites.append((enclosing.get(id(node), "<module>"),
                      f"{func.value.id}.{func.attr}", node))
    return sites


def test_the_engine_invokes_no_agent(project):
    """X2 (TP-003 category 2). Was `test_t06_creates_no_subagent`, which
    banned the bare substring `"subagent"` in the engine source.

    T10's `lint-skill` has to read and reason about `.claude/agents/*.md`, and
    the honest English for what is in those files is a subagent, so the
    vocabulary ban is retired and the *guarantee* is strengthened instead:
    every invocation literal stays banned, and a structural assertion now
    proves the engine starts no process that names an agent — the engine may
    describe agents, it may not start one. Passing by wording discipline
    (writing "agent" everywhere and never "subagent") was rejected: it leaves
    a booby trap for the next editor and makes a green test mean nothing.

    `sdle-architect` remains a recorded actor *string* supplied by the caller.
    """
    at_gate_constitution(project)
    project.ok("artifact", "review", "--path", CONSTITUTION,
               "--type", "architecture-review", "--result", "PASS",
               "--actor-type", "agent", "--actor-name", "sdle-architect")
    assert reviews_of(project)["reviews"][0]["actor"]["name"] == "sdle-architect"

    tree = sdle_ast()
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not (imported - set(sys.stdlib_module_names)), \
        "the engine stays standard-library only"

    source = Path(SDLE_PY).read_text(encoding="utf-8")
    for forbidden in ("Task(", "launch_agent"):
        assert forbidden not in source, forbidden

    # The structural half. The engine starts a process in exactly two places,
    # and neither of them can start an agent.
    sites = _spawn_sites(tree)
    assert sorted({where for where, _, _ in sites}) == ["git", "run_tests"], (
        "the engine spawns processes somewhere new: "
        f"{sorted({where for where, _, _ in sites})}")
    named = []
    for where, call, node in sites:
        for literal in ast.walk(node):
            if not (isinstance(literal, ast.Constant)
                    and isinstance(literal.value, str)):
                continue
            lowered = literal.value.lower()
            if "claude" in lowered or "agent" in lowered or "Task" in literal.value:
                named.append((where, call, literal.value))
    assert named == [], (
        "the engine may describe agents; it may not start one: " f"{named}")


# --------------------------------------------------------------------------
# N34 — E2 applies to every bound WorkItem, because T11 removed the only
# binding that had no WorkItem
# --------------------------------------------------------------------------


def test_e2_no_longer_stands_aside_anywhere(bare_project):
    """T11 D4, the inverse of the carve-out this test used to pin.

    A repository-global `.workflow/` used to be approvable without a review
    ledger. It is not a runtime any more: the approval refuses at the ladder,
    before E2 is reached, and `.workflow/` is left byte-identical.
    """
    template = json.loads(
        (bare_project.skill_root / "templates" / "state.json").read_text(
            encoding="utf-8"))
    template["current_phase"] = "gate_constitution"
    template["status"] = "awaiting_approval"
    legacy = bare_project.root / ".workflow"
    legacy.mkdir()
    (legacy / "state.json").write_text(json.dumps(template, indent=2) + "\n",
                                       encoding="utf-8", newline="\n")
    before = sdle.sha256_file(legacy / "state.json")
    bare_project.write_artifact(CONSTITUTION)

    assert bare_project.workitem is None
    approved = bare_project.run("gate", "approve", "--gate",
                                "gate_constitution")
    assert approved.exit_code == EXIT_REFUSED, approved
    assert approved.reason == "workitem_required", approved
    assert not (legacy / "reviews.json").exists()
    assert not (legacy / "audit.md").exists()
    assert sdle.sha256_file(legacy / "state.json") == before


def test_e2_applies_as_soon_as_a_workitem_holds_the_runtime(project):
    at_gate_constitution(project)
    result = project.run("gate", "approve", "--gate", "gate_constitution")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_missing", result


# --------------------------------------------------------------------------
# N35 — one artifact is never reviewed twice under two keys
# --------------------------------------------------------------------------


def test_a_backslash_path_normalises_onto_the_same_key(project):
    at_gate_constitution(project)
    project.ok("artifact", "review",
               "--path", CONSTITUTION.replace("/", "\\"),
               "--type", REVIEW_TYPE, "--result", "PASS",
               "--actor-type", "test", "--actor-name", "suite")

    assert reviews_of(project)["reviews"][0]["path"] == CONSTITUTION
    project.ok("gate", "approve", "--gate", "gate_constitution")


def test_a_dot_slash_prefix_normalises_onto_the_same_key(project):
    at_gate_constitution(project)
    project.ok("artifact", "review", "--path", "./" + CONSTITUTION,
               "--type", REVIEW_TYPE, "--result", "PASS",
               "--actor-type", "test", "--actor-name", "suite")
    assert reviews_of(project)["reviews"][0]["path"] == CONSTITUTION


def test_an_absolute_path_normalises_onto_the_same_key(project):
    at_gate_constitution(project)
    project.ok("artifact", "review",
               "--path", str(project.root / CONSTITUTION),
               "--type", REVIEW_TYPE, "--result", "PASS",
               "--actor-type", "test", "--actor-name", "suite")
    assert reviews_of(project)["reviews"][0]["path"] == CONSTITUTION


def test_a_path_outside_the_project_is_refused(project, tmp_path):
    at_gate_constitution(project)
    stranger = tmp_path / "elsewhere.md"
    stranger.write_text("# Elsewhere\n" * 20, encoding="utf-8", newline="\n")

    result = project.run("artifact", "review", "--path", str(stranger),
                         "--type", REVIEW_TYPE, "--result", "PASS",
                         "--actor-type", "test", "--actor-name", "suite")
    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "review_path_outside_project", result


def test_recorded_shas_are_lowercase_hex(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")
    sha = reviews_of(project)["reviews"][0]["sha256"]
    assert sha == sha.lower() and len(sha) == 64
    assert all(character in "0123456789abcdef" for character in sha)


# --------------------------------------------------------------------------
# Purity and fail-closed reading
# --------------------------------------------------------------------------


def test_listing_reviews_writes_nothing(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")

    before = {path.relative_to(project.root).as_posix(): sdle.sha256_file(path)
              for path in sorted(project.root.rglob("*"))
              if path.is_file() and ".git" not in path.parts}
    listed = project.ok("artifact", "reviews")
    after = {path.relative_to(project.root).as_posix(): sdle.sha256_file(path)
             for path in sorted(project.root.rglob("*"))
             if path.is_file() and ".git" not in path.parts}

    assert after == before
    assert listed.data["status"][CONSTITUTION]["current"] is True
    assert len(listed.data["reviews"]) == 1


def test_an_unreadable_review_ledger_is_not_treated_as_no_reviews(project):
    at_gate_constitution(project)
    review_for_gate(project, "gate_constitution")
    (project.runtime / "reviews.json").write_text('{"reviews": ',
                                                  encoding="utf-8")
    before = frozen(project)

    result = project.run("gate", "approve", "--gate", "gate_constitution")

    assert result.exit_code == EXIT_REFUSED, result
    assert result.reason == "reviews_malformed", result
    assert frozen(project) == before
