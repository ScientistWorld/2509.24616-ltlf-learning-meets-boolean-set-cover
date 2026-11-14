#!/bin/bash
# Hardening experiment: better method at the same budget: the reference Bolt
# pipeline and settings, with directed temporal patterns (Scarlet's fragment)
# added as extra Boolean Set Cover atoms in their own beam slots.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec python3 "$ROOT/scripts/hardening/bolt_patterns.py" "$1" "$2"
