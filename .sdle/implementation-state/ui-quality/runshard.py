"""Run one shard of the suite in the foreground and persist a run record.

usage: runshard.py SHARDS_JSON INDEX LABEL      (INDEX may be 'all' for every shard)
       runshard.py - - LABEL -- <pytest args>   (ad-hoc run)
Standard library only. Records go to ui-quality/runs/<LABEL>.json beside this file.
"""
import datetime as dt, json, re, subprocess, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUNS = HERE / "runs"
RUNS.mkdir(exist_ok=True)


def run(label: str, targets: list[str]) -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *targets]
    started = time.time()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    elapsed = round(time.time() - started, 1)
    tail = (proc.stdout.strip().splitlines() or [""])[-1]
    (RUNS / f"{label}.log").write_text(proc.stdout + "\n--- stderr ---\n" + proc.stderr, encoding="utf-8")
    record = {"label": label, "command": " ".join(cmd[1:]), "exit_code": proc.returncode,
              "summary": tail, "seconds": elapsed,
              "finished": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "result": "PASS" if proc.returncode == 0 else "FAIL"}
    (RUNS / f"{label}.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    print(json.dumps(record))
    return proc.returncode


if __name__ == "__main__":
    shards_path, index, label = sys.argv[1:4]
    if shards_path == "-":
        sys.exit(run(label, sys.argv[sys.argv.index("--") + 1:]))
    shards = json.load(open(shards_path))
    picked = range(len(shards)) if index == "all" else [int(index)]
    worst = 0
    for i in picked:
        worst = max(worst, run(f"{label}-{i}", shards[i]))
    sys.exit(worst)
