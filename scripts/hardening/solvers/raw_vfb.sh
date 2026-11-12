#!/bin/bash
# Baseline: raw VFB enumeration (the paper's ablation "Bolt without Boolean Set
# Cover"): exhaustive LTLf enumeration by size with observational equivalence,
# until a separator is found or the CPU budget / memory cap runs out.
#
# Solver contract: bash scripts/solvers/<name>.sh <instance.json> <answer.json>
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec python3 "$ROOT/method/ltlf_bolt.py" --instance "$1" --out "$2" --mode vfb --max-memory-mb 1000
