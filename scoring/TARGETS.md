# Targets

Optimize `selected_benchmarks`.

Primary target:

- Increase `solve_rate` for valid learned LTLf formulas on the selected released benchmark subset.

Constraints:

- Keep `all_returned_formulas_valid` at `1.0`.
- Keep `evaluation_coverage` at `1.0`; every selected instance must receive an output row.
- Keep `formula_size_ratio` close to or below `1.0` on tasks solved by both the submitted method and the provided reference baseline; methods with no common solved tasks receive a neutral ratio, not a size bonus.
- Preserve a positive `solve_rate_delta_vs_baseline`; gains should come from solving instances that the provided reference baseline misses under the same benchmark slice.
- Do not improve solved count by changing the benchmark traces or labels.
