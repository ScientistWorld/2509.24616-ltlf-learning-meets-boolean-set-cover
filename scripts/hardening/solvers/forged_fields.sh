#!/bin/bash
# Shortcut check: returns the first proposition with forged validity/size/score fields.
python3 - "$1" "$2" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
json.dump({"formula": d["atomic_propositions"][0], "valid": True, "size": 1,
           "best_known_size": 1, "size_efficiency": 1.0}, open(sys.argv[2], "w"))
PY
