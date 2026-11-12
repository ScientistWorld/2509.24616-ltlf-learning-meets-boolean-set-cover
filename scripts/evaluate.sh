#!/bin/bash
# Standard evaluation entry point: scores every solver in scripts/solvers/ on the
# visible training slice (see scripts/evaluate_train.sh) and mirrors the result
# into scoring/scores.json.  eval/ never imports method/: solvers are run as
# separate processes and only their formula strings are read.
set -euo pipefail
cd "$(dirname "$0")/.."
bash scripts/evaluate_train.sh
cp scoring/scores_train.json scoring/scores.json
