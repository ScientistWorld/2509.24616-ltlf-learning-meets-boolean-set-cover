#!/bin/bash
# Iteration 11 hardening job: run reference, baseline, variants and shortcut
# solvers through the train/test harness, freeze best-known sizes, score, then
# run the official no-argument evaluations.  Solver runs resume from the saved
# per-instance records if the job is restarted.
set -euo pipefail
cd /home/user
bash scripts/download.sh
H=scripts/hardening/solvers
TEST_ALL=bolt,raw_vfb,bolt_simplify,bolt_switch3,bolt_beam1,literal_cover,null_answer,crash,forged_fields
TRAIN_ALL=bolt,raw_vfb,bolt_simplify,bolt_switch3,bolt_beam1,literal_cover
mkdir -p notes/hardening
python3 eval/test/evaluate.py --solvers-dir $H --runs-dir eval/test/runs_hardening --no-score --resume --only $TEST_ALL
python3 eval/test/evaluate.py --solvers-dir $H --runs-dir eval/test/runs_hardening --no-score --resume --only parallel_portfolio --first 8
python3 eval/train/evaluate.py --solvers-dir $H --runs-dir notes/hardening/train_runs --no-score --resume --only $TRAIN_ALL
python3 eval/test/build_reference_sizes.py --runs-dir eval/test/runs_hardening
python3 eval/train/build_reference_sizes.py --runs-dir notes/hardening/train_runs
python3 eval/test/evaluate.py --solvers-dir $H --runs-dir eval/test/runs_hardening --skip-run --only $TEST_ALL,parallel_portfolio --out notes/hardening/scores_test_variants.json
python3 eval/train/evaluate.py --solvers-dir $H --runs-dir notes/hardening/train_runs --skip-run --only $TRAIN_ALL --out notes/hardening/scores_train_variants.json
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
cp scoring/scores_train.json scoring/scores.json
python3 scripts/hardening/analyze.py
# Formulas found for hidden instances must not stay on disk where a solver could read them.
rm -f eval/test/runs_hardening/*.jsonl
python3 validate.py --compare || echo "validate.py reported problems"
