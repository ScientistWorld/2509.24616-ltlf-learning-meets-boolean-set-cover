# Train/Test Evaluation Design Notes (iteration 11, hardening)

- A method is a solver script in `scripts/solvers/`. Both evaluators enumerate that directory, run every solver once per instance in a fresh process with 20 CPU seconds (solver + children, counted from `wait4` rusage; RLIMIT_CPU, 4 GB address space, 50 s wall clock), and read only the `formula` string of `answer.json`.
- Train: 40 instances from the paper's released suite (`data/train/`, answer fields stripped), 8 per family for OrderedSequence, Subword, Subset, Hamming, RandomBooleanCombinationsofFactors, sampled uniformly over the released parameter combinations (`data/prepare_train.py`).
- Test: 40 fresh draws from the same upstream generators over the same parameter combinations with unrecorded OS-random seeds (`eval/test/build_instances.py`); stored only in `eval/test/instances.json`.
- Best-known sizes (`eval/test/instances.json`, `eval/train/reference_sizes.json`) = min over the generating formula and every valid formula found by any iteration-11 run (`build_reference_sizes.py`); frozen afterwards.
- Metrics: `size_efficiency` (primary), `solve_rate`, `size_ratio_geomean`, all computed by the evaluator from the parsed formula. Failures score 0 / 0 / 10.
- The hidden test keeps solver records in memory (no formulas written to disk during or after a default run), so solvers cannot read each other's answers.
- `eval/train` and `eval/test` share no code (duplicated parser/semantics); neither imports `method/`.
