"""Run one non-interactive Codex review (P08) and record it.

usage: codexrun.py AREA WORKTREE PROMPT SCHEMA RUNS_DIR TIMEOUT_SECONDS
Read-only sandbox, ephemeral, frozen worktree. One retry on a nonzero exit,
timeout or schema-invalid output; a second failure is recorded as BLOCKED.
"""
import datetime as dt
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

area, worktree, prompt, schema, runs_dir, timeout = sys.argv[1:7]
timeout = int(timeout)
runs = Path(runs_dir)
prompt_p, schema_p = Path(prompt), Path(schema)
codex = shutil.which("codex")
assert codex, "codex not found"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def utc():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


version = subprocess.run([codex, "--version"], capture_output=True, text=True).stdout.strip()
candidate = subprocess.run(["git", "rev-parse", "HEAD"], cwd=worktree, capture_output=True, text=True).stdout.strip()
stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
run_id = f"{stamp}-p08-codex-{area}"


def validate(doc, expected_commit):
    problems = []
    if not isinstance(doc, dict):
        return ["output is not a JSON object"]
    for key in ("reviewed_commit", "coverage", "findings"):
        if key not in doc:
            problems.append(f"missing {key}")
    if problems:
        return problems
    if not str(doc["reviewed_commit"]).startswith(expected_commit[:7]):
        problems.append(f"reviewed_commit {doc['reviewed_commit']!r} is not the candidate")
    cov = doc["coverage"]
    if not isinstance(cov, dict) or "areas_reviewed" not in cov or "areas_not_reviewed" not in cov:
        problems.append("coverage lacks areas_reviewed/areas_not_reviewed")
    sev = {"critical", "high", "medium", "low"}
    for i, f in enumerate(doc["findings"]):
        for key in ("id", "severity", "category", "path", "line", "claim", "evidence",
                    "evidence_type", "suggested_fix", "ac_ids", "confidence"):
            if key not in f:
                problems.append(f"finding {i} missing {key}")
        if f.get("severity") not in sev:
            problems.append(f"finding {i} bad severity")
        if f.get("evidence_type") not in ("executed", "static"):
            problems.append(f"finding {i} bad evidence_type")
    if not doc["findings"] and isinstance(cov, dict) and cov.get("areas_not_reviewed"):
        problems.append("empty findings with unreviewed areas: the review is incomplete")
    return problems


record = {
    "run_id": run_id, "result": "IN_PROGRESS", "task_ids": ["P08"], "ac_ids": ["AC-01", "AC-02", "AC-19"],
    "area": area, "codex_version": version, "sandbox": "read-only", "ephemeral": True,
    "worktree": worktree, "candidate_sha": candidate, "timeout_seconds": timeout,
    "prompt": prompt_p.name, "prompt_sha256": sha(prompt_p),
    "schema": schema_p.name, "schema_sha256": sha(schema_p),
    "started_utc": utc(), "attempts": [],
}
record_path = runs / f"{run_id}.json"
runs.mkdir(parents=True, exist_ok=True)


def save():
    record_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


save()
for attempt in (1, 2):
    tag = f"{run_id}.a{attempt}"
    events, err, last = runs / f"{tag}.events.jsonl", runs / f"{tag}.stderr.log", runs / f"{tag}.review.json"
    argv = [codex, "exec", "--cd", worktree, "--sandbox", "read-only", "--ephemeral", "--json",
            "--output-schema", str(schema_p), "--output-last-message", str(last), "-"]
    info = {"attempt": attempt, "argv": argv, "started_utc": utc()}
    try:
        with open(events, "wb") as out_f, open(err, "wb") as err_f:
            proc = subprocess.run(argv, input=prompt_p.read_bytes(), stdout=out_f, stderr=err_f,
                                  timeout=timeout)
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
            blob = json.dumps(d)
            if '"model"' in blob:
                model = d.get("model") or (d.get("item") or {}).get("model") or (d.get("msg") or {}).get("model") or model
                if model:
                    break
    info["model_reported"] = model
    problems = ["nonzero exit / timeout"] if info.get("exit_code") != 0 else []
    doc = None
    if not problems:
        try:
            doc = json.loads(last.read_text(encoding="utf-8"))
            problems = validate(doc, candidate)
        except Exception as exc:  # unreadable or not JSON
            problems = [f"output unreadable: {exc}"]
    info["validation_problems"] = problems
    info["outputs"] = {"events": events.name, "stderr": err.name, "review": last.name}
    record["attempts"].append(info)
    if not problems:
        record.update({"result": "PASS", "finished_utc": utc(), "findings": len(doc["findings"]),
                       "coverage_not_reviewed": doc["coverage"]["areas_not_reviewed"],
                       "review_output": last.name})
        save()
        break
    save()
else:
    record.update({"result": "BLOCKED", "finished_utc": utc()})
    save()
print(json.dumps({k: record.get(k) for k in ("run_id", "result", "findings", "coverage_not_reviewed")}))
