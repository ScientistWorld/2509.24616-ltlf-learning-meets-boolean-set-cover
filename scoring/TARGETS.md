# Targets

Optimize `selected_benchmarks`.

Primary target:

- Increase `solve_rate` for valid learned LTLf formulas on the selected released benchmark subset.

Constraints:

- Keep `all_returned_formulas_valid` at `1.0`.
- Keep `formula_size_ratio` close to or below `1.0` on tasks solved by both the proposed method and the raw VFB ablation.
- Preserve a positive `solve_rate_delta_vs_baseline`; gains should come from solving instances that raw bounded VFB misses at the same LTL switch.
- Do not improve solved count by changing the benchmark traces or labels.
