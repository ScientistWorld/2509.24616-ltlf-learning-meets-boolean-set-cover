#!/bin/bash
# Hidden test: runs every solver in scripts/solvers/*.sh on the hidden instances
# (eval/test/instances.json) under the fixed per-instance CPU budget, scores the
# returned formulas, and writes scoring/scores_test.json.  Takes no arguments.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p scoring
python3 eval/test/evaluate.py
