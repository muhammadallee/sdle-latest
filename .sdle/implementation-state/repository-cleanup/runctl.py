#!/usr/bin/env python3
"""Maintenance-run recorder for the repository cleanup (plan section 6).

Standard library only. Three verbs:

  fingerprint                 print the content fingerprint of the tested source
  run LABEL [opts] -- ARGV    run ARGV, persisting a run record, stdout, stderr
  checkpoint [opts]           atomically update STATE.json and append a journal line

Records live beside this file. Nothing here touches a WorkItem runtime.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = HERE / "runs"
STATE = HERE / "STATE.json"
LEDGER = HERE / "LEDGER.md"
JOURNAL = HERE / "journal.jsonl"
EXCLUDE = (
    ".sdle/implementation-state/repository-cleanup/",
    "plan-claude-codex-defectfix.md",  # execution material, not product content
    "plan-chatgpt-claude-chatgpt-reviewed.md",
)
RESULTS = {"PASS", "FAIL", "BLOCKED", "NOT_RUN", "IN_PROGRESS", "INTERRUPTED", "UNKNOWN"}


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def manifest() -> tuple[str, list[list[str]]]:
    """HEAD plus every tracked modification, deletion, rename and untracked file."""
    head = git("rev-parse", "HEAD").strip()
    raw = git("status", "--porcelain=v1", "-z", "--untracked-files=all")
    parts = raw.split("\0")
    entries: list[list[str]] = []
    i = 0
    while i < len(parts):
        item = parts[i]
        i += 1
        if len(item) < 4:
            continue
        status, path = item[:2], item[3:]
        if status[0] in "RC":  # rename/copy: the next field is the origin
            i += 1
        if path.startswith(EXCLUDE):  # str.startswith accepts a tuple
            continue
        target = ROOT / path
        digest = sha256_file(target) if target.is_file() else "ABSENT"
        entries.append([status.strip() or "?", path, digest])
    entries.sort(key=lambda e: e[1])
    return head, entries


def fingerprint() -> tuple[str, str, list[list[str]]]:
    head, entries = manifest()
    body = json.dumps(entries, sort_keys=True).encode()
    return head, hashlib.sha256(head.encode() + body).hexdigest(), entries


def tool_version(argv: list[str]) -> str:
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=30)
        return (out.stdout or out.stderr).strip().splitlines()[0] if (out.stdout or out.stderr).strip() else ""
    except Exception as exc:  # a missing tool is a fact, not a failure
        return f"unavailable ({type(exc).__name__})"


def cmd_fingerprint(_: argparse.Namespace) -> int:
    head, fp, entries = fingerprint()
    print(json.dumps({"head": head, "fingerprint": fp, "paths": len(entries)}))
    return 0


def _mem_status():
    """System memory via GlobalMemoryStatusEx (Windows). Returns GB floats or None."""
    if sys.platform != "win32":
        return None
    import ctypes

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("sullAvailExtendedVirtual", ctypes.c_ulonglong)]
    st = MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(st)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st))
    gb = 1024 ** 3
    # "PageFile" here is the commit limit (RAM + page file); used = limit - available.
    return {"phys_avail_gb": st.ullAvailPhys / gb, "phys_total_gb": st.ullTotalPhys / gb,
            "commit_used_gb": (st.ullTotalPageFile - st.ullAvailPageFile) / gb,
            "commit_limit_gb": st.ullTotalPageFile / gb}


def _image_working_set_mb(*images: str) -> dict[str, float]:
    """Sum of working set per image name via tasklist (no third-party deps)."""
    totals = {i: 0.0 for i in images}
    try:
        out = subprocess.run(["tasklist", "/FO", "CSV", "/NH"], capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return totals
    import csv
    for row in csv.reader(out.splitlines()):
        if len(row) >= 5 and row[0].lower() in totals:
            digits = re.sub(r"[^0-9]", "", row[4])
            totals[row[0].lower()] += (int(digits) / 1024.0) if digits else 0.0
    return totals


def start_memory_sampler(csv_path: Path, interval: int):
    import threading
    stop = threading.Event()

    def loop():
        with open(csv_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("utc,phys_avail_gb,commit_used_gb,commit_limit_gb,python_ws_mb,git_ws_mb\n")
            while not stop.is_set():
                mem = _mem_status() or {}
                ws = _image_working_set_mb("python.exe", "git.exe")
                handle.write("{},{:.2f},{:.2f},{:.2f},{:.0f},{:.0f}\n".format(
                    now(), mem.get("phys_avail_gb", -1), mem.get("commit_used_gb", -1),
                    mem.get("commit_limit_gb", -1), ws["python.exe"], ws["git.exe"]))
                handle.flush()
                stop.wait(interval)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return stop, thread


PYTEST_SUMMARY = re.compile(r"(\d+) (passed|failed|skipped|error|errors|xfailed|xpassed|deselected|tests? collected)")


def parse_counts(stdout: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for line in reversed(stdout.strip().splitlines()[-8:]):
        for number, word in PYTEST_SUMMARY.findall(line):
            counts[word] = int(number)
        if counts:
            break
    return counts


def cmd_run(args: argparse.Namespace) -> int:
    RUNS.mkdir(exist_ok=True)
    head, fp, entries = fingerprint()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    run_id = f"{stamp}-{args.label}"
    record_path = RUNS / f"{run_id}.json"
    out_path, err_path = RUNS / f"{run_id}.stdout.log", RUNS / f"{run_id}.stderr.log"
    argv = args.argv
    record = {
        "run_id": run_id, "result": "IN_PROGRESS", "label": args.label,
        "task_ids": args.tasks, "ac_ids": args.acs, "argv": argv,
        "cwd": str((ROOT / args.cwd).resolve()) if args.cwd else str(ROOT),
        "head": head, "content_fingerprint": fp, "manifest_paths": len(entries),
        "env": {
            "python": sys.version.split()[0], "platform": sys.platform,
            "git": tool_version(["git", "--version"]),
        },
        "started_utc": now(), "runner_pid": os.getpid(),
        "stdout": out_path.name, "stderr": err_path.name, "note": args.note,
    }
    atomic_write(record_path, json.dumps(record, indent=2) + "\n")
    print(f"[runctl] {run_id} IN_PROGRESS", file=sys.stderr)
    env = dict(os.environ, **dict(kv.split("=", 1) for kv in args.env))
    sampler = None
    if args.sample_memory:
        mem_path = RUNS / f"{run_id}.mem.csv"
        record["memory_samples"] = mem_path.name
        atomic_write(record_path, json.dumps(record, indent=2) + "\n")
        sampler = start_memory_sampler(mem_path, args.sample_memory)
    try:
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            proc = subprocess.run(argv, cwd=record["cwd"], stdout=out, stderr=err, env=env, timeout=args.timeout)
        code, timed_out = proc.returncode, False
    except subprocess.TimeoutExpired:
        code, timed_out = None, True
    except FileNotFoundError as exc:
        code, timed_out = None, False
        err_path.write_text(f"{exc}\n")
    if sampler:
        sampler[0].set()
        sampler[1].join(timeout=30)
    stdout = out_path.read_text(encoding="utf-8", errors="replace") if out_path.exists() else ""
    counts = parse_counts(stdout) if args.pytest else {}
    result = "PASS" if code == args.expect_rc else "FAIL"
    if timed_out:
        result = "INTERRUPTED"
    elif code is None:
        result = "BLOCKED"
    elif args.pytest and result == "PASS" and not (counts.get("passed") or counts.get("tests collected") or counts.get("test collected")):
        result = "UNKNOWN"  # zero collected tests is not a valid gate
    if code is not None and args.pytest and counts.get("failed"):
        result = "FAIL"
    after = fingerprint()[1]
    record.update({
        "result": result, "exit_code": code, "expected_exit_code": args.expect_rc,
        "counts": counts, "finished_utc": now(),
        "fingerprint_unchanged_during_run": after == fp,
    })
    atomic_write(record_path, json.dumps(record, indent=2) + "\n")
    print(json.dumps({"run_id": run_id, "result": result, "exit_code": code, "counts": counts}))
    return 0 if result == "PASS" else 1


def cmd_checkpoint(args: argparse.Namespace) -> int:
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    head, fp, entries = fingerprint()
    state.update({
        "schema_version": 1, "repository_root": str(ROOT),
        "branch": git("branch", "--show-current").strip(), "head": head,
        "current_content_fingerprint": fp, "changed_paths": [e[1] for e in entries],
    })
    if args.plan and Path(args.plan).exists():
        state["plan_path"] = args.plan
        state["plan_sha256"] = sha256_file(Path(args.plan))
    for key in ("phase", "phase_status", "task_id", "task_status", "next_action"):
        value = getattr(args, key)
        if value is not None:
            state[key] = value
    handoff = state.setdefault("handoff", {})
    for key, dest in (("last_action", "last_completed_action"), ("verification", "verification_status"), ("note", "note")):
        value = getattr(args, key)
        if value is not None:
            handoff[dest] = value
    if args.unfinished is not None:
        handoff["unfinished_paths"] = args.unfinished
    for field, items in (("completed_tasks", args.complete_task), ("completed_phases", args.complete_phase),
                         ("verification_run_ids", args.run), ("open_finding_ids", args.open_finding)):
        bucket = state.setdefault(field, [])
        bucket.extend(i for i in items if i not in bucket)
    for item in args.close_finding:
        if item in state.setdefault("open_finding_ids", []):
            state["open_finding_ids"].remove(item)
    if args.blockers is not None:
        state["blockers"] = args.blockers
    for kv in args.set:
        key, value = kv.split("=", 1)
        state[key] = json.loads(value)
    if LEDGER.exists():
        state["ledger_sha256"] = sha256_file(LEDGER)
    state["updated_at_utc"] = now()
    atomic_write(STATE, json.dumps(state, indent=2) + "\n")
    event = {"ts": state["updated_at_utc"], "phase": state.get("phase"), "task": state.get("task_id"),
             "event": args.event or "checkpoint", "head": head, "fingerprint": fp,
             "ledger_sha256": state.get("ledger_sha256"), "note": args.note or args.last_action}
    with open(JOURNAL, "a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event) + "\n")
    print(json.dumps({"checkpointed": True, "phase": state.get("phase"), "task": state.get("task_id")}))
    return 0


def pid_alive(pid) -> bool:
    """Is a recorded runner still running? (`os.kill(pid, 0)` is not safe on
    Windows, where signal 0 is a console control event.)"""
    if not pid:
        return False
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                             capture_output=True, text=True).stdout
        return f'"{pid}"' in out
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


REQUIRED_STATE = ("phase", "phase_status", "task_id", "next_action", "branch", "base_commit",
                  "head", "plan_sha256", "current_content_fingerprint", "completed_phases", "handoff")
REQUIRED_HANDOFF = ("last_completed_action", "verification_status", "note")


def reconstruct_candidate() -> dict:
    """A minimal STATE candidate from the journal and Git, for a missing or
    corrupt STATE.json. Anything not proven by those sources is UNKNOWN."""
    last = {}
    if JOURNAL.exists():
        for line in JOURNAL.read_text(encoding="utf-8").splitlines():
            try:
                last = json.loads(line)
            except ValueError:
                continue  # a torn final line is skipped, never trusted
    return {
        "reconstructed": True, "phase": last.get("phase", "UNKNOWN"), "task_id": last.get("task", "UNKNOWN"),
        "phase_status": "UNKNOWN", "task_status": "UNKNOWN", "completed_phases": "UNKNOWN",
        "branch": git("branch", "--show-current").strip(), "head": git("rev-parse", "HEAD").strip(),
        "last_journal_event": last.get("event"), "last_journal_ts": last.get("ts"),
        "note": "candidate only: re-verify before claiming any status",
    }


def verify_report() -> dict:
    issues: list[dict] = []
    state = None
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        issues.append({"issue": "state_missing", "action": "reconstruct a candidate (verify --reconstruct)"})
    except ValueError as exc:
        issues.append({"issue": "state_corrupt", "detail": str(exc),
                       "action": "do not trust it; reconstruct a candidate (verify --reconstruct)"})
    stray = sorted(p.name for p in HERE.glob("*.tmp"))
    if stray:
        issues.append({"issue": "interrupted_write_leftover", "files": stray,
                       "action": "an atomic write died before its rename; the target file is the last complete version"})
    head, fp, _ = fingerprint()
    if state is not None:
        missing = [k for k in REQUIRED_STATE if k not in state]
        missing += ["handoff." + k for k in REQUIRED_HANDOFF if k not in (state.get("handoff") or {})]
        if missing:
            issues.append({"issue": "state_incomplete", "missing": missing})
        if LEDGER.exists() and state.get("ledger_sha256") != sha256_file(LEDGER):
            issues.append({"issue": "ledger_changed_since_last_checkpoint",
                           "action": "the last ledger write is unconfirmed: compare with git and the journal"})
        if state.get("head") != head:
            issues.append({"issue": "head_moved", "checkpoint": state.get("head"), "now": head,
                           "action": "record the new source identity and re-plan the active phase"})
        elif state.get("current_content_fingerprint") != fp:
            issues.append({"issue": "content_changed_since_checkpoint",
                           "action": "diff against changed_paths; finish or repair the slice, then re-verify"})
        plan = Path(state.get("plan_path", "")) if state.get("plan_path") else None
        if plan and (ROOT / plan).is_file() and state.get("plan_sha256") != sha256_file(ROOT / plan):
            issues.append({"issue": "plan_changed", "action": "reopen only the affected tasks"})
    dead, alive, stale = [], [], []
    claimed = set((state or {}).get("verification_run_ids", []))
    for record in sorted(RUNS.glob("*.json")) if RUNS.exists() else []:
        try:
            data = json.loads(record.read_text(encoding="utf-8"))
        except ValueError:
            issues.append({"issue": "run_record_corrupt", "file": record.name})
            continue
        if data.get("result") == "IN_PROGRESS":
            (alive if pid_alive(data.get("runner_pid")) else dead).append(data["run_id"])
        elif data.get("run_id") in claimed and data.get("result") == "PASS" and data.get("content_fingerprint") != fp:
            stale.append(data["run_id"])
    if dead:
        issues.append({"issue": "run_in_progress_but_runner_gone", "runs": dead,
                       "action": "run `reconcile` to mark them INTERRUPTED, then re-run the check"})
    if stale:
        issues.append({"issue": "claimed_evidence_bound_to_other_content", "runs": stale,
                       "action": "re-run the affected checks; do not reuse these results"})
    return {"ok": not issues, "issues": issues, "runs_still_running": alive, "head": head, "fingerprint": fp}


def cmd_verify(args: argparse.Namespace) -> int:
    report = verify_report()
    if args.reconstruct:
        report["candidate"] = reconstruct_candidate()
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


def cmd_reconcile(_: argparse.Namespace) -> int:
    changed = []
    for record in sorted(RUNS.glob("*.json")) if RUNS.exists() else []:
        data = json.loads(record.read_text(encoding="utf-8"))
        if data.get("result") == "IN_PROGRESS" and not pid_alive(data.get("runner_pid")):
            data.update({"result": "INTERRUPTED", "exit_code": None,
                         "interrupted_reason": "runner process is gone (found by reconcile); no result is claimed"})
            atomic_write(record, json.dumps(data, indent=2) + "\n")
            changed.append(data["run_id"])
    print(json.dumps({"marked_interrupted": changed}))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="verb", required=True)
    sub.add_parser("fingerprint").set_defaults(fn=cmd_fingerprint)
    ver = sub.add_parser("verify")
    ver.add_argument("--reconstruct", action="store_true")
    ver.set_defaults(fn=cmd_verify)
    sub.add_parser("reconcile").set_defaults(fn=cmd_reconcile)

    run = sub.add_parser("run")
    run.add_argument("label")
    run.add_argument("--tasks", nargs="*", default=[])
    run.add_argument("--acs", nargs="*", default=[])
    run.add_argument("--cwd", default="")
    run.add_argument("--expect-rc", type=int, default=0)
    run.add_argument("--timeout", type=int, default=3000)
    run.add_argument("--pytest", action="store_true", help="parse pytest counts; zero passed is UNKNOWN")
    run.add_argument("--env", nargs="*", default=[], help="KEY=VALUE overrides for the child")
    run.add_argument("--note", default="")
    run.add_argument("--sample-memory", type=int, default=0, metavar="SECONDS",
                     help="sample system/python memory every N seconds into <run>.mem.csv")
    run.set_defaults(fn=cmd_run)

    cp = sub.add_parser("checkpoint")
    for name in ("phase", "phase_status", "task_id", "task_status", "next_action", "last_action",
                 "verification", "note", "event", "plan"):
        cp.add_argument("--" + name.replace("_", "-"), dest=name)
    cp.add_argument("--unfinished", nargs="*")
    cp.add_argument("--complete-task", nargs="*", default=[])
    cp.add_argument("--complete-phase", nargs="*", default=[])
    cp.add_argument("--run", nargs="*", default=[])
    cp.add_argument("--open-finding", nargs="*", default=[])
    cp.add_argument("--close-finding", nargs="*", default=[])
    cp.add_argument("--blockers", nargs="*")
    cp.add_argument("--set", nargs="*", default=[], help="key=<json> raw state fields")
    cp.set_defaults(fn=cmd_checkpoint)

    raw = sys.argv[1:]
    command: list[str] = []
    if "--" in raw:  # everything after the first `--` is the child argv, untouched
        split = raw.index("--")
        raw, command = raw[:split], raw[split + 1:]
    args = parser.parse_args(raw)
    args.argv = command
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
