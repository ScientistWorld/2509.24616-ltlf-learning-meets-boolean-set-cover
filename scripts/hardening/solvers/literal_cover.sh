#!/bin/bash
# Shortcut: Lemma-1 style brute force. Time-indexed literals X[!]^t(a) / X[!]^t(!a),
# a greedy cover of the negatives for each positive, OR of the conjunctions.
# Always valid when the trace sets are disjoint; no temporal generalisation.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
exec python3 "$ROOT/scripts/hardening/literal_cover.py" "$1" "$2"
