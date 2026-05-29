#!/bin/bash
# Score the held-out test slice from the same pre-generated method outputs.

set -euo pipefail

cd /home/user

mkdir -p scoring

python3 eval/test/evaluate.py \
  --results-glob "${RESULTS_GLOB:-outputs/*_results.json}" \
  --train-scores "${TRAIN_SCORES:-scoring/scores_train.json}" \
  --out scoring/scores_test.json
