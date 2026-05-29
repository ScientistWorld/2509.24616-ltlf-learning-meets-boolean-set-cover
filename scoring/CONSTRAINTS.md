# Constraints

- Use the JSON instances under `data/paper_benchmark_subset` or a documented superset extracted from the upstream benchmark zip by `data/prepare_paper_subset.py`.
- Evaluation must parse and check returned formulas independently; it must not trust method-reported validity.
- `eval/` must not import from `method/`.
- Returned formulas must use the supported LTLf operators: atoms, `true`, `false`, `!`, `X[!]`, `F`, `G`, `&`, `|`, `U`, and `R`.
- Improvements must preserve finite-trace LTLf semantics and may not hardcode labels or benchmark-specific answers.
