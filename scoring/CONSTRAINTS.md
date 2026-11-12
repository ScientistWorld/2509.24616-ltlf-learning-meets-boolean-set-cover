# Constraints

- A method is a solver script `scripts/solvers/<name>.sh <instance.json> <answer.json>` that writes `{"formula": ...}`; it is run once per instance in a fresh process (see `briefing/evaluation.md`). Every script in `scripts/solvers/` is evaluated.
- Budget: 20 CPU seconds per instance for the solver and all its child processes, one core, 4 GB address space, 50 s wall clock. Exceeding any limit makes the instance unsolved. Precomputation that depends on the specific test instances is impossible (they are hidden); generic precomputation shipped with the solver is allowed.
- Returned formulas must be LTLf over the instance's propositions in the documented syntax; the evaluator parses and checks them itself and ignores every other field.
- Solvers must not read evaluator files (`eval/`), the hidden instances, or the benchmark release's answer fields (`smallest_known_formula`, `generating_formula`) at run time, and must not hardcode formulas for specific instances.
- `eval/` never imports `method/`; train and test evaluators share no code and use the same interface, budget and metrics.
