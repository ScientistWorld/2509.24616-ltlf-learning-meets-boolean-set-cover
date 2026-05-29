#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -euo pipefail

cd /home/user

python3 data/generate_selected_benchmarks.py

mapfile -t INSTANCES < <(python3 - <<'PY'
import json
from pathlib import Path
print("\n".join(json.loads(Path("data/selected_benchmarks/manifest.json").read_text())["instances"]))
PY
)

mkdir -p outputs
python3 method/ltlf_bolt.py \
  --mode bolt \
  --instances "${INSTANCES[@]}" \
  --out outputs/bolt_results.json \
  --ltl-switch "${LTL_SWITCH:-3}" \
  --beam-width "${BEAM_WIDTH:-30}" \
  --max-bool-weight "${MAX_BOOL_WEIGHT:-25}" \
  --timeout "${TIMEOUT_SECONDS:-20}"

bash scripts/evaluate.sh
