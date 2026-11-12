#!/bin/bash
# Hardening experiment: better variant: reference + greedy post-hoc subformula deletion (generic size reduction)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec python3 "$ROOT/method/ltlf_bolt.py" --instance "$1" --out "$2" --mode bolt \
  --ltl-switch 8 --size-dom 10 --beam-width 100 --dc-switch 70 \
  --max-ltl-formulas 500000 --simplify
