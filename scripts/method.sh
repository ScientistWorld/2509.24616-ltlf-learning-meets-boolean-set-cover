#!/bin/bash
# Run the paper's proposed method.
#
# This script trains/runs the paper's method using code in method/.
#
# Usage:
#   bash scripts/method.sh

set -euo pipefail

cd /home/user

MANIFEST="${BENCHMARK_MANIFEST:-data/paper_benchmark_subset/manifest.json}"
if [ ! -e "$MANIFEST" ] && [ -e data/downloads/benchmarks.zip ]; then
  python3 data/prepare_paper_subset.py
fi

mapfile -t INSTANCES < <(python3 - <<'PY'
import json
import os
from pathlib import Path
manifest = Path(os.environ.get("BENCHMARK_MANIFEST", "data/paper_benchmark_subset/manifest.json"))
print("\n".join(json.loads(manifest.read_text())["instances"]))
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
