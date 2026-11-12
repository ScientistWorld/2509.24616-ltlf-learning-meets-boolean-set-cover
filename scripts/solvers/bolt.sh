#!/bin/bash
# Reference method: Bolt (bounded VFB enumeration + Boolean Set Cover beam
# search + divide and conquer) at the paper's settings: LTL2BS-switch 8,
# size-dom 10, beam width 100, D&C-switch 70.  The LTL stage also switches at a
# memory threshold of 500k retained formulas (paper Section 3); like the paper's
# tool, the Boolean stage runs until it succeeds or the time budget (90% of the
# CPU budget) runs out.
#
# Solver contract: bash scripts/solvers/<name>.sh <instance.json> <answer.json>
# writes {"formula": "<LTLf formula>"} (or null) within LTLF_CPU_BUDGET_S CPU seconds.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
exec python3 "$ROOT/method/ltlf_bolt.py" --instance "$1" --out "$2" --mode bolt \
  --ltl-switch 8 --size-dom 10 --beam-width 100 --dc-switch 70 \
  --max-ltl-formulas 500000
