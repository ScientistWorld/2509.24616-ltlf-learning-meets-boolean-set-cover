#!/bin/bash
set -euo pipefail
cd /home/user
bash redteam/shortcut_unmeasured_formula_padding/run.sh
bash redteam/shortcut_missing_artifact/run.sh
bash redteam/shortcut_bruteforce_only/run.sh
bash redteam/shortcut_bruteforce_fallback/run.sh
