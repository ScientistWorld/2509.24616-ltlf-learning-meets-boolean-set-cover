# Train/Test Evaluation Design Notes

## Checked

- Compared `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh`: train invokes `eval/train/evaluate.py` and writes `scoring/scores_train.json`; test invokes `eval/test/evaluate.py`, reads train scores only to enumerate methods, and writes `scoring/scores_test.json`.
- Grepped for train/test cross-imports and hardcoded method defaults; none were found.
- Checked for paper-agreement metrics in `scoring/reference.json`; none were present.
- Confirmed `scoring/scores_train.json` and `scoring/scores_test.json` do not exist.
- Ran `bash -n` on both train/test evaluation scripts.

## Changed

- Fixed the main shortcut in both slice evaluators: `solve_rate` now uses a fixed denominator of every expected slice instance. Missing output rows are inserted as unsolved placeholders, so omitting hard instances cannot improve the score.
- Deduplicated slice rows by instance before scoring, so duplicated easy outputs cannot distort denominators.
- Added `evaluation_coverage` to make omitted outputs visible even though they already count as unsolved.
- Added `baseline_miss_solve_rate`, which measures how often a method solves instances that the raw bounded VFB ablation misses. This better targets the paper's Boolean-set-cover claim than overall solve rate alone.
- Added the required `description` field to every nonzero metric in `scoring/reference.json`.
- Added `_slice` and `_expected_instances` metadata to train/test score payloads so copy-paste or slice-routing mistakes are easier to detect in artifacts.

## Runtime Concerns For Next Iteration

- The split is intentionally small: five visible and five held-out instances. It uses held-out benchmark families/categories to make shortcutting visible, but measured scores will be coarse.
- The new metrics depend on the raw VFB ablation being present under the same result glob and canonicalized as `scarlet`. If future runs omit that baseline file, relative metrics safely fall to zero, but the runner should confirm this is the intended failure mode.
- The score schema now includes train/test-only metrics. The legacy unsplit `scripts/evaluate.sh` was not changed in this design-only pass, so runner-side tooling should use `scripts/evaluate_train.sh` and `scripts/evaluate_test.sh` for split scoring.
