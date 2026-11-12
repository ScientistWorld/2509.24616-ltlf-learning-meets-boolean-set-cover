#!/bin/bash
# Train slice: runs every solver in scripts/solvers/*.sh on the visible training
# instances (data/train/) under the same CPU budget as the hidden test, scores
# the returned formulas, and writes scoring/scores_train.json.  Takes no arguments.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p scoring
python3 eval/train/evaluate.py
