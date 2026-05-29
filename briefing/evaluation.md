# Evaluation

Evaluation reads result artifacts from `outputs/` and does not import from `method/`.

For each returned formula, the evaluator parses the LTLf expression and evaluates it on all positive and negative traces. A formula is valid only if it accepts every positive trace and rejects every negative trace.

The main benefit metric is solve rate on the selected released benchmark subset. Constraint metrics include returned-formula validity, evaluation coverage, formula-size ratio on tasks solved by both a submitted method and the provided reference baseline, and solve-rate delta over that baseline. If there are no common solved tasks for a size comparison, the ratio is reported as neutral `1.0` rather than giving a size bonus. Diagnostic metadata may appear in raw run artifacts, but method-internal diagnostics and wall-clock runtimes are not ranking targets.

A reusable method output is a JSON file under `outputs/` with a top-level `results` list. Each row should include at least:

- `instance`: path to the benchmark JSON file.
- `method`: method identifier.
- `formula`: returned LTLf formula string, or `null` if no separator was found.

Additional fields are allowed and ignored unless a metric explicitly uses them.

Run:

```bash
bash scripts/reproduce.sh
python3 validate.py --compare
```
