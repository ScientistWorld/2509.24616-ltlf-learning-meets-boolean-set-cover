#!/bin/bash
set -euo pipefail

cd /home/user

export TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-20}"
export LTL_SWITCH="${LTL_SWITCH:-3}"
export VFB_MAX_SIZE="${VFB_MAX_SIZE:-3}"
export BEAM_WIDTH="${BEAM_WIDTH:-30}"
export MAX_BOOL_WEIGHT="${MAX_BOOL_WEIGHT:-25}"

bash scripts/reproduce.sh
python3 validate.py --compare
