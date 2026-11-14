#!/bin/bash
# Iteration 12 hardening job: rerun reference, baseline, variants and shortcuts
# on the ten-family train / hidden-test slices, freeze best-known sizes, run the
# official evaluations and analyse (scripts/hardening/run_hardening.sh).
set -euo pipefail
cd /home/user
bash scripts/hardening/run_hardening.sh
