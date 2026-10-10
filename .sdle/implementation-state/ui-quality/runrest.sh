#!/bin/sh
# usage: runrest.sh LABEL FIRST LAST
cd "$(dirname "$0")/../../.."
i=$2
while [ "$i" -le "$3" ]; do
  python .sdle/implementation-state/ui-quality/runshard.py .sdle/implementation-state/requirements-package-loop/shards-final.json $i "$1" | python -c "import sys,json;r=json.loads(sys.stdin.read());print(r['label'],r['result'],r['summary'],flush=True)"
  i=$((i+1))
done
