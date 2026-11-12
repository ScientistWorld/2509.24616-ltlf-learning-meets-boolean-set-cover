#!/bin/bash
# Hardening experiment: weaker variant: LTL2BS-switch 3 (paper: small switches give much larger formulas)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec python3 "$ROOT/method/ltlf_bolt.py" --instance "$1" --out "$2" --mode bolt \
  --ltl-switch 8 --size-dom 10 --beam-width 100 --dc-switch 70 \
  --max-ltl-formulas 500000 --ltl-switch 3
