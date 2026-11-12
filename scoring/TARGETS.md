# Targets

One scored experiment, `budgeted_ltlf_learning` (weight 1.0), measured on hidden instances by `scripts/evaluate_test.sh` and on the visible training slice by `scripts/evaluate_train.sh`.

Benefit:

- `solve_rate` (coefficient 0.5, higher is better): fraction of instances for which the solver returns a valid separating LTLf formula within 20 CPU seconds.

Constraint (the paper's claim is that more tasks are solved *without* giving up formula size):

- `size_ratio_geomean` (coefficient 0.5, lower is better): geometric mean of returned size over the best-known separator size, clipped to [1, 10], with 10 for unsolved instances.

Combined (primary):

- `size_efficiency` (coefficient 1.0, higher is better): mean of `min(1, best_known_size / returned_size)`, 0 for unsolved instances. Solving with a huge formula earns little; solving with a best-known-size formula earns 1.

Validity is not a separate target: an invalid, unparsable, late or over-budget answer simply counts as unsolved, and a run that fails everywhere gets the worst value of all three metrics (0, 0, 10).
