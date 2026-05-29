# Evaluation

Evaluation reads result artifacts from `outputs/` and does not import from `method/`.

For each returned formula, the evaluator parses the LTLf expression and evaluates it on all positive and negative traces. A formula is valid only if it accepts every positive trace and rejects every negative trace.

The main benefit metric is solved count on the selected benchmark suite. Constraint metrics include returned-formula validity and formula size ratios on tasks solved by both Bolt and the baseline. Collapse ratio is recorded to show that the Boolean Set Cover stage is operating on first-bit vector representatives rather than full characteristic tables.

Run:

```bash
bash scripts/reproduce.sh
python3 validate.py --compare
```
