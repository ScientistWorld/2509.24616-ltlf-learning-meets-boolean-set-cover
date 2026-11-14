#!/bin/bash
# Reproduce the reference end to end: fetch data, run every solver on disk
# (Bolt reference and raw VFB baseline) through the train and hidden-test
# harnesses with the fixed per-instance CPU budget, and validate.
# The iteration-12 hardening experiments are in scripts/hardening/run_hardening.sh.
set -euo pipefail
cd /home/user
bash scripts/download.sh
bash scripts/reproduce.sh
python3 validate.py --compare
