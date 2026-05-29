#!/bin/bash
# Score the visible train slice from pre-generated method outputs.

set -euo pipefail

cd /home/user

mkdir -p scoring

python3 eval/train/evaluate.py \
  --results-glob "${RESULTS_GLOB:-outputs/*_results.json}" \
  --out scoring/scores_train.json
