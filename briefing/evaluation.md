# Evaluation

A method is a **solver**: an executable script `scripts/solvers/<name>.sh`. Every script in that directory is a method on disk and is evaluated; nothing else is.

```
bash scripts/solvers/<name>.sh <instance.json> <answer.json>
```

- `<instance.json>` is one learning task in the standard benchmark format (`positive_traces`, `negative_traces`, `atomic_propositions`, counts). It contains no answer or metadata.
- The solver must write `<answer.json>` = `{"formula": "<LTLf formula>"}` (or `{"formula": null}`) and exit with status 0. Other fields are ignored.
- Budget: **20 CPU seconds per instance**, counted for the solver process and all its children (the value is also in the environment variable `LTLF_CPU_BUDGET_S`). Answers from runs that use more CPU (0.5 s start-up grace), exceed 50 s of wall time, crash, or exceed 4 GB of address space count as unsolved. Each instance runs in a fresh process with the workspace as working directory; one CPU core.
- Formula syntax: propositions of the instance, `true`, `false`, unary `!`, `X`, `X[!]`, `F`, `G`, binary `&` (`&&`), `|` (`||`), `->`, `<->`, `U`, `R`, parentheses. Unary operators bind tightest; then `U`/`R`, `&`, `|`, `->`, `<->`. Parenthesise to be safe. Size = number of syntax-tree nodes (parentheses are free; derived operators such as `F`, `G`, `R`, `X` count as one node). Formulas over 20,000 nodes or 3,000 levels deep count as unsolved.

The evaluator parses every returned formula itself, evaluates it on the instance's traces with its own LTLf semantics, and computes everything from that. For instance i with fixed best-known separator size `r_i` (the smallest separator found by the generating process or by any recorded run; held by the evaluator), a valid answer of size `s_i` scores:

| metric | definition | direction | coefficient |
|---|---|---|---:|
| `size_efficiency` (primary) | mean over instances of `min(1, r_i / s_i)` if valid, else 0 | higher | 1.0 |
| `solve_rate` | fraction of instances with a valid separator | higher | 0.5 |
| `size_ratio_geomean` | geometric mean of `clip(s_i / r_i, 1, 10)`, 10 if unsolved | lower | 0.5 |

A run that fails everywhere scores 0 / 0 / 10, the worst value of every metric; returning a valid separator never lowers a score compared with returning nothing.

Commands:

```bash
bash scripts/evaluate_train.sh   # every solver on the 40 training instances -> scoring/scores_train.json
bash scripts/evaluate.sh         # same, mirrored to scoring/scores.json
bash scripts/evaluate_test.sh    # hidden instances (not available while developing) -> scoring/scores_test.json
python3 eval/train/evaluate.py --only <name> --out outputs/<name>_train.json --runs-dir outputs/<name>_runs
```

Per-instance run records (status, CPU seconds, formula) and scored details are written to the runs directory (`outputs/train_runs/` by default). The train and test slices use the same budget, metrics and interface, and have the same family/parameter mix.
