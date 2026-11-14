#!/bin/bash
# Iteration 12 hardening pipeline (kept for provenance; re-running it re-freezes
# best-known sizes).  One CPU job:
#  1. run the reference, baseline, variants and shortcut solvers through the
#     train / hidden-test harness (records with formulas kept until step 3;
#     --resume continues an interrupted job; train reuses iteration 11's records
#     of the unchanged deterministic solvers on the 40 old training instances),
#  2. exhaustive lower bounds where no learner finds a separator,
#  3. freeze best-known sizes (generating formulas + every learner run, this
#     iteration's and iteration 11's),
#  4. score every variant, run the official no-argument evaluations (a second,
#     independent run of the reference and the baseline), analyse,
#  5. (afterwards) delete the formula records of hidden instances.
set -euo pipefail
cd /home/user
bash scripts/download.sh
H=scripts/hardening/solvers
TEST_ALL=bolt,raw_vfb,bolt_patterns,bolt_simplify,bolt_portfolio,bolt_beam1,bolt_switch3,literal_cover,null_answer,crash,forged_fields
TRAIN_ALL=bolt,raw_vfb,bolt_patterns,bolt_simplify,bolt_portfolio,bolt_beam1,bolt_switch3,literal_cover
mkdir -p notes/hardening eval/test/runs_hardening
python3 eval/test/evaluate.py --solvers-dir $H --runs-dir eval/test/runs_hardening --no-score --resume --only $TEST_ALL
python3 eval/train/evaluate.py --solvers-dir $H --runs-dir notes/hardening/train_runs --no-score --resume --only $TRAIN_ALL
python3 scripts/hardening/lower_bounds.py --slice test --details eval/test/runs_job1/details.json \
  --details eval/test/runs_iter11/details.json --runs-dir eval/test/runs_hardening
python3 scripts/hardening/lower_bounds.py --slice train --details notes/hardening/train_runs_job1/details.json \
  --runs-dir notes/hardening/train_runs
python3 eval/test/build_reference_sizes.py --runs-dir eval/test/runs_hardening \
  --details eval/test/runs_job1/details.json --details eval/test/runs_iter11/details.json
python3 eval/train/build_reference_sizes.py --runs-dir notes/hardening/train_runs \
  --details notes/hardening/train_runs_job1/details.json
python3 eval/test/evaluate.py --solvers-dir $H --runs-dir eval/test/runs_hardening --skip-run --only $TEST_ALL \
  --out notes/hardening/scores_test_variants.json
python3 eval/train/evaluate.py --solvers-dir $H --runs-dir notes/hardening/train_runs --skip-run --only $TRAIN_ALL \
  --out notes/hardening/scores_train_variants.json
bash scripts/evaluate_train.sh
bash scripts/evaluate_test.sh
cp scoring/scores_train.json scoring/scores.json
python3 scripts/hardening/analyze.py
# The formula records of hidden instances (eval/test/runs_hardening/*.jsonl,
# gitignored) are deleted once the reference sizes are final, so that no solver
# can read them.
python3 validate.py --compare || echo "validate.py reported problems"
