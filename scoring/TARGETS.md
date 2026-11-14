# Targets

One scored experiment, `budgeted_ltlf_learning` (weight 1.0), measured on 80 hidden instances (8 from each of the paper's ten benchmark families) by `scripts/evaluate_test.sh` and on the 80 visible training instances by `scripts/evaluate_train.sh`.

Benefit:

- `solve_rate` (coefficient 0.5, higher is better): fraction of instances for which the solver returns, within 20 CPU seconds, a valid separating LTLf formula of at most 10x the reference size (best-known learner separator, or a proven lower bound where no learner finds one).

Constraint (the paper's claim is that more tasks are solved *without* giving up formula size):

- `size_ratio_geomean` (coefficient 0.5, lower is better): geometric mean of returned size over the best-known separator size, clipped to [1, 10], with 10 for unsolved instances.

Combined (primary):

- `size_efficiency` (coefficient 1.0, higher is better): mean of `min(1, best_known_size / returned_size)`, 0 for unsolved instances. Solving with a huge formula earns little; solving with a best-known-size formula earns 1.

Validity is not a separate target: an invalid, unparsable, late, over-budget or more-than-10x-oversized answer simply counts as unsolved, and a run that fails everywhere gets the worst value of all three metrics (0, 0, 10).
