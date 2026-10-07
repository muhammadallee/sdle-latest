"""Run one shard of the suite through runctl (foreground). usage: runshard.py SHARDS_JSON INDEX LABEL"""
import json, subprocess, sys
shards = json.load(open(sys.argv[1]))
files = shards[int(sys.argv[2])]
cmd = [sys.executable, ".sdle/implementation-state/requirements-package-loop/runctl.py", "run", sys.argv[3],
       "--pytest", "--timeout", "580", "--sample-memory", "30", "--",
       sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *files]
sys.exit(subprocess.run(cmd).returncode)
