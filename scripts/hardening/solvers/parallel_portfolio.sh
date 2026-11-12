#!/bin/bash
# Budget check: runs two Bolt configurations concurrently (reference and a
# larger-cap variant) and keeps the smaller valid answer.  Uses up to twice the
# CPU budget, which the evaluator must count and reject.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
T=$(mktemp -d)
python3 "$ROOT/method/ltlf_bolt.py" --instance "$1" --out "$T/a.json" --mode bolt \
  --beam-width 100 --dc-switch 70 --max-ltl-formulas 500000 &
python3 "$ROOT/method/ltlf_bolt.py" --instance "$1" --out "$T/b.json" --mode bolt \
  --beam-width 100 --dc-switch 70 --max-ltl-formulas 1000000 --simplify &
wait
python3 - "$T/a.json" "$T/b.json" "$2" <<'PY'
import json, sys
best = None
for p in sys.argv[1:3]:
    try:
        f = json.load(open(p)).get("formula")
    except Exception:
        f = None
    if f and (best is None or len(f) < len(best)):
        best = f
json.dump({"formula": best}, open(sys.argv[3], "w"))
PY
rm -rf "$T"
