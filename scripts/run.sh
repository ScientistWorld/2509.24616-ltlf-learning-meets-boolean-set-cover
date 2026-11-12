#!/bin/bash
# Iteration 11 hardening job 2: rerun reference, baseline, variants and shortcut
# solvers through the train/test harness, compute exhaustive lower bounds where
# no learner finds a separator, freeze best-known sizes (learners + generating
# formulas only), score, run the official no-argument evaluations, analyse.
# Train runs resume from job 1's saved records (unchanged deterministic solvers).
set -euo pipefail
cd /home/user
bash scripts/download.sh
H=scripts/hardening/solvers
TEST_ALL=bolt,raw_vfb,bolt_simplify,bolt_portfolio,bolt_switch3,bolt_beam1,literal_cover,null_answer,crash,forged_fields
TRAIN_ALL=bolt,raw_vfb,bolt_simplify,bolt_portfolio,bolt_switch3,bolt_beam1,literal_cover
mkdir -p notes/hardening
python3 eval/test/evaluate.py --solvers-dir $H --runs-dir eval/test/runs_hardening --no-score --resume --only $TEST_ALL
python3 eval/test/evaluate.py --solvers-dir $H --runs-dir eval/test/runs_hardening --no-score --resume --only parallel_portfolio --first 8
python3 eval/train/evaluate.py --solvers-dir $H --runs-dir notes/hardening/train_runs --no-score --resume --only $TRAIN_ALL
python3 scripts/hardening/lower_bounds.py --slice test --details eval/test/runs_job1/details.json --runs-dir eval/test/runs_hardening
python3 scripts/hardening/lower_bounds.py --slice train --details notes/hardening/train_runs_job1/details.json --runs-dir notes/hardening/train_runs
python3 eval/test/build_reference_sizes.py --runs-dir eval/test/runs_hardening --details eval/test/runs_job1/details.json
python3 eval/train/build_reference_sizes.py --runs-dir notes/hardening/train_runs --details notes/hardening/train_runs_job1/details.json
python3 eval/test/evaluate.py --solvers-dir $H --runs-dir eval/test/runs_hardening --skip-run --only $TEST_ALL,parallel_portfolio --out notes/hardening/scores_test_variants.json
python3 eval/train/evaluate.py --solvers-dir $H --runs-dir notes/hardening/train_runs --skip-run --only $TRAIN_ALL --out notes/hardening/scores_train_variants.json
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
cp scoring/scores_train.json scoring/scores.json
python3 scripts/hardening/analyze.py
# Formulas found for hidden instances must not stay on disk where a solver could read them.
rm -f eval/test/runs_hardening/*.jsonl
python3 validate.py --compare || echo "validate.py reported problems"
