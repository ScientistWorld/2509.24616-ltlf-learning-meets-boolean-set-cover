#!/bin/bash
# Reproduce the reference results end to end: every solver in scripts/solvers/
# (Bolt and the raw VFB baseline) on the training slice and, where the hidden
# instances are present, on the test slice.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/evaluate.sh
if [ -f eval/test/instances.json ]; then
  bash scripts/evaluate_test.sh
fi
