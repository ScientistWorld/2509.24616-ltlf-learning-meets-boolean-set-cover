#!/bin/bash
# Run a baseline method from the paper.
#
# Baselines are simple reference methods the paper compares against. 
# Implement this only if applicable, i.e. the paper has baselines.
# You do not need to implement all baselines to begin — 
# just enough to validate that the evaluation pipeline works 
# and provide a reference point. You can decide to expand more baselines later.
# Each baseline must be actually run and scored through evaluate.sh
# so the numbers are verified, not self-reported.
# You can decide what this baseline script should do yourself.
#
# Usage:
#   bash scripts/baseline.sh <name>

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
  --mode vfb \
  --instances "${INSTANCES[@]}" \
  --out outputs/raw_vfb_results.json \
  --ltl-switch "${VFB_MAX_SIZE:-3}" \
  --timeout "${TIMEOUT_SECONDS:-20}"
