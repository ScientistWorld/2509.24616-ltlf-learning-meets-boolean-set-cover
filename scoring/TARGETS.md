# Targets

Optimize `selected_benchmarks`.

Primary target:

- Increase `solve_rate` for valid learned LTLf formulas on the selected benchmark suite. `solved_count` is also reported, but it is subset-size dependent and should not be compared directly to the paper's full-suite count.

Constraints:

- Keep `all_returned_formulas_valid` at `1.0`.
- Keep `median_size_ratio_vs_vfb_common` close to or below `1.0` on tasks solved by both methods.
- Do not improve solved count by changing the benchmark traces or labels.
