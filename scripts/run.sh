#!/bin/bash
set -euo pipefail

cd /home/user

bash scripts/download.sh
bash scripts/reproduce.sh
python3 validate.py --compare
bash scripts/evaluate_train.sh /home/user/checkpoints
bash scripts/evaluate_test.sh /home/user/checkpoints
python3 validate.py --compare
