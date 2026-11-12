#!/bin/bash
# Run the paper's method (scripts/solvers/bolt.sh) on the visible training
# instances under the evaluation budget and score it (outputs/bolt_train_scores.json).
set -euo pipefail
cd "$(dirname "$0")/.."
python3 eval/train/evaluate.py --only bolt --runs-dir outputs/train_runs_bolt --out outputs/bolt_train_scores.json
