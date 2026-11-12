#!/bin/bash
# Hardening experiment: better variant: anytime portfolio (reference Bolt, then a
# larger-switch/wider-beam Bolt in the remaining budget, smaller result simplified).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec python3 "$ROOT/scripts/hardening/portfolio.py" "$1" "$2"
