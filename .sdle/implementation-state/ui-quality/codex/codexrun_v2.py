"""Run one non-interactive Codex review and record it (review runner v2, UI-quality enhancement).

Derived from requirements-package-loop/codex/codexrun_stage2.py, which is left unchanged as the
evidence of the reviews it ran. The invocation (read-only sandbox, ephemeral, frozen worktree),
the single retry and the run record are the same. What changed is completeness:

* the review reports ``files_reviewed``, and the runner compares it with the files the review was
  asked to cover (``git diff --name-only BASE..HEAD -- <pathspec>`` in the frozen worktree): an
  unread file in scope makes the review incomplete, whatever the findings;
* coverage gaps are split: ``not_reviewed`` (part of the asked scope not examined) makes the review
  incomplete; ``out_of_scope`` (what the sandbox cannot do: run tests, start a browser, read files
  outside the checkout) never does, and is recorded;
* so a clean review (no findings) that covered its scope now passes. Under v1 it could not, because
  an honest reviewer in a read-only sandbox always lists something it could not run.

usage: codexrun_v2.py AREA WORKTREE PROMPT RUNS_DIR TIMEOUT_SECONDS BASE [PATHSPEC ...]
       codexrun_v2.py --self-test
"""
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent / "review.v2.schema.json"
SEVERITIES = {"critical", "high", "medium", "low"}
FINDING_KEYS = ("id", "severity", "category", "path", "line", "claim", "evidence",
                "evidence_type", "suggested_fix", "ac_ids", "confidence")


def _norm(path: str) -> str | None:
    """A repository-relative path in one spelling, or None if it is not one (absolute, or `..`).
    Only an explicit leading `./` is removed: `.sdle/` and `.claude/` keep their dot."""
    p = path.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    if not p or p.startswith("/") or (len(p) > 1 and p[1] == ":") or ".." in p.split("/"):
        return None
    return p


def validate(doc, expected_commit: str, required_files: list[str]) -> list[str]:
    """Problems that make the review output unusable or incomplete; empty means PASS."""
    if not isinstance(doc, dict):
        return ["output is not a JSON object"]
    problems = [f"missing {k}" for k in ("reviewed_commit", "coverage", "findings") if k not in doc]
    if problems:
        return problems
    reported = str(doc["reviewed_commit"]).strip().lower()
    if not (len(reported) >= 7 and all(c in "0123456789abcdef" for c in reported)
            and expected_commit.lower().startswith(reported)):
        problems.append(f"reviewed_commit {doc['reviewed_commit']!r} is not the candidate")
    cov = doc["coverage"]
    keys = ("areas_reviewed", "files_reviewed", "not_reviewed", "out_of_scope")
    if not isinstance(cov, dict) or any(not isinstance(cov.get(k), list) for k in keys):
        return problems + ["coverage lacks one of " + ", ".join(keys)]
    for i, f in enumerate(doc["findings"]):
        for key in FINDING_KEYS:
            if key not in f:
                problems.append(f"finding {i} missing {key}")
        if f.get("severity") not in SEVERITIES:
            problems.append(f"finding {i} bad severity")
        if f.get("evidence_type") not in ("executed", "static"):
            problems.append(f"finding {i} bad evidence_type")
    read = {_norm(p) for p in cov["files_reviewed"]} - {None}
    unread = sorted(p for p in required_files if _norm(p) not in read)
    if unread:
        problems.append("files in scope not reviewed: " + ", ".join(unread))
    if cov["not_reviewed"]:
        problems.append("parts of the scope not reviewed: " + "; ".join(cov["not_reviewed"]))
    return problems


def self_test() -> None:
    dotdirs = {"reviewed_commit": "abcdef1", "findings": [],
               "coverage": {"areas_reviewed": ["x"], "files_reviewed": ["sdle/x", "claude/x"],
                            "not_reviewed": [], "out_of_scope": []}}
    assert any("not reviewed" in p for p in validate(dotdirs, "abcdef1234", [".sdle/x", ".claude/x"])), \
        "a dot-directory keeps its dot (RV-002)"
    parent = json.loads(json.dumps(dotdirs)); parent["coverage"]["files_reviewed"] = ["../a"]
    assert any("not reviewed: a" in p for p in validate(parent, "abcdef1234", ["a"])), "`..` never matches"
    suffix = json.loads(json.dumps(dotdirs)); suffix["reviewed_commit"] = "abcdef1WRONG"
    suffix["coverage"]["files_reviewed"] = []
    assert any("not the candidate" in p for p in validate(suffix, "abcdef123456789", [])), \
        "a shared prefix plus a wrong suffix is not the candidate (RV-003)"
    full = json.loads(json.dumps(suffix)); full["reviewed_commit"] = "ABCDEF123456789"
    assert validate(full, "abcdef123456789", []) == [], "the full SHA, any case, is accepted"
    base = {"reviewed_commit": "abcdef1234", "findings": [],
            "coverage": {"areas_reviewed": ["all"], "files_reviewed": ["a.md", "b/c.py"],
                         "not_reviewed": [], "out_of_scope": ["could not run pytest"]}}
    head = "abcdef1234ffff"
    assert validate(base, head, ["a.md", "b/c.py"]) == [], "a clean, covered review passes"
    unread = json.loads(json.dumps(base)); unread["coverage"]["files_reviewed"] = ["a.md"]
    assert any("not reviewed: b/c.py" in p for p in validate(unread, head, ["a.md", "b/c.py"]))
    gap = json.loads(json.dumps(base)); gap["coverage"]["not_reviewed"] = ["the docs"]
    assert any("scope not reviewed" in p for p in validate(gap, head, ["a.md"]))
    wrong = json.loads(json.dumps(base)); wrong["reviewed_commit"] = "0000000"
    assert any("not the candidate" in p for p in validate(wrong, head, []))
    windows = json.loads(json.dumps(base)); windows["coverage"]["files_reviewed"] = [".\\a.md", "b\\c.py"]
    assert validate(windows, head, ["a.md", "b/c.py"]) == [], "path spelling is normalised"
    bad = json.loads(json.dumps(base)); bad["findings"] = [{"id": "X", "severity": "huge"}]
    assert any("bad severity" in p for p in validate(bad, head, ["a.md", "b/c.py"]))
    print("self-test ok")


def main(argv: list[str]) -> None:
    area, worktree, prompt, runs_dir, timeout, base = argv[:6]
    pathspec = argv[6:]
    timeout = int(timeout)
    runs = Path(runs_dir)
    prompt_p = Path(prompt)
    codex = shutil.which("codex")
    assert codex, "codex not found"

    def sha(path):
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()

    def utc():
        return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    version = subprocess.run([codex, "--version"], capture_output=True, text=True).stdout.strip()
    head_cmd = subprocess.run(["git", "rev-parse", "HEAD"], cwd=worktree, capture_output=True, text=True)
    candidate = head_cmd.stdout.strip()
    diff = subprocess.run(["git", "diff", "--name-only", f"{base}..HEAD", "--", *pathspec], cwd=worktree,
                          capture_output=True, text=True)
    scope_error = None
    if head_cmd.returncode != 0 or not candidate:
        scope_error = f"git rev-parse HEAD failed: {head_cmd.stderr.strip()}"
    elif diff.returncode != 0:
        # an unknown BASE must not become an empty scope that any review passes (RV-001)
        scope_error = f"git diff {base}..HEAD failed: {diff.stderr.strip()}"
    required = [l for l in diff.stdout.splitlines() if l.strip()] if scope_error is None else []
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{stamp}-codex-v2-{area}"
    record = {
        "run_id": run_id, "runner": "codexrun_v2", "result": "IN_PROGRESS", "area": area,
        "codex_version": version, "sandbox": "read-only", "ephemeral": True, "worktree": worktree,
        "candidate_sha": candidate, "base": base, "pathspec": pathspec, "required_files": required,
        "timeout_seconds": timeout, "prompt": prompt_p.name, "prompt_sha256": sha(prompt_p),
        "schema": SCHEMA.name, "schema_sha256": sha(SCHEMA), "started_utc": utc(), "attempts": [],
    }
    runs.mkdir(parents=True, exist_ok=True)
    record_path = runs / f"{run_id}.json"

    def save():
        record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    if scope_error:
        record.update({"result": "BLOCKED", "scope_error": scope_error, "finished_utc": utc()})
        save()
        print(json.dumps({k: record.get(k) for k in ("run_id", "result", "scope_error")}))
        return

    # The prompt is sent with the list of files the review must cover, so the requirement is explicit.
    files_note = ("\n\n## Files in scope (the runner checks `files_reviewed` against this list)\n"
                  + "\n".join(f"- {p}" for p in required) + "\n\n"
                  "Report in `coverage.files_reviewed` every file you read. Put in `coverage.not_reviewed` "
                  "only parts of the asked scope you did not examine; put in `coverage.out_of_scope` what the "
                  "read-only sandbox does not let you do (running tests, starting a browser, files outside "
                  "the checkout). A review with an unread file in scope, or anything in `not_reviewed`, is "
                  "recorded as incomplete.\n")
    prompt_bytes = prompt_p.read_bytes() + files_note.encode("utf-8")
    save()
    for attempt in (1, 2):
        tag = f"{run_id}.a{attempt}"
        events, err, last = runs / f"{tag}.events.jsonl", runs / f"{tag}.stderr.log", runs / f"{tag}.review.json"
        cmd = [codex, "exec", "--cd", worktree, "--sandbox", "read-only", "--ephemeral", "--json",
               "--output-schema", str(SCHEMA), "--output-last-message", str(last), "-"]
        info = {"attempt": attempt, "argv": cmd, "started_utc": utc()}
        try:
            with open(events, "wb") as out_f, open(err, "wb") as err_f:
                proc = subprocess.run(cmd, input=prompt_bytes, stdout=out_f, stderr=err_f, timeout=timeout)
            info["exit_code"] = proc.returncode
        except subprocess.TimeoutExpired:
            info["exit_code"] = None
            info["timed_out"] = True
        info["finished_utc"] = utc()
        model = None
        if events.exists():
            for line in events.read_text(encoding="utf-8", errors="replace").splitlines():
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if '"model"' in json.dumps(d):
                    model = (d.get("model") or (d.get("item") or {}).get("model")
                             or (d.get("msg") or {}).get("model") or model)
                    if model:
                        break
        info["model_reported"] = model   # kept from v1 (RV-004)
        problems = ["nonzero exit / timeout"] if info.get("exit_code") != 0 else []
        doc = None
        if not problems:
            try:
                doc = json.loads(last.read_text(encoding="utf-8"))
                problems = validate(doc, candidate, required)
            except Exception as exc:  # unreadable or not JSON
                problems = [f"output unreadable: {exc}"]
        info["validation_problems"] = problems
        info["outputs"] = {"events": events.name, "stderr": err.name, "review": last.name}
        record["attempts"].append(info)
        if not problems:
            record.update({"result": "PASS", "finished_utc": utc(), "findings": len(doc["findings"]),
                           "out_of_scope": doc["coverage"]["out_of_scope"], "review_output": last.name})
            save()
            break
        save()
    else:
        record.update({"result": "BLOCKED", "finished_utc": utc()})
        save()
    print(json.dumps({k: record.get(k) for k in ("run_id", "result", "findings", "out_of_scope")}))


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        self_test()
    else:
        main(sys.argv[1:])
