#!/bin/bash
set -euo pipefail
cd /home/user
bash redteam/reference_seed0/run.sh
bash redteam/reference_seed1/run.sh
bash redteam/reference_seed2/run.sh
bash redteam/stronger_search/run.sh
bash redteam/paper_search_settings/run.sh
bash redteam/weaker_no_boolean/run.sh
bash redteam/weaker_minimal_search/run.sh
bash redteam/brute_force_vfb/run.sh
bash redteam/shortcut_bruteforce_only/run.sh
bash redteam/shortcut_bruteforce_fallback/run.sh
bash redteam/shortcut_metadata_answers/run.sh
bash redteam/shortcut_baseline_padding/run.sh
bash redteam/shortcut_baseline_nulls/run.sh
bash redteam/shortcut_ground_truth/run.sh
bash redteam/shortcut_forged_fields/run.sh
bash redteam/shortcut_null_outputs/run.sh
bash redteam/shortcut_empty_outputs/run.sh
bash redteam/shortcut_method_filter/run.sh
bash redteam/shortcut_stale_replay/run.sh
