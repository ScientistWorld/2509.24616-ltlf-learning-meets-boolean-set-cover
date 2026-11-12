#!/bin/bash
# Run the raw VFB ablation baseline (scripts/solvers/raw_vfb.sh) on the visible
# training instances under the evaluation budget and score it
# (outputs/raw_vfb_train_scores.json).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 eval/train/evaluate.py --only raw_vfb --runs-dir outputs/train_runs_raw_vfb --out outputs/raw_vfb_train_scores.json
