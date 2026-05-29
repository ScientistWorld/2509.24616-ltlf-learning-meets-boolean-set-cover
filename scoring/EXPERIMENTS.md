# Experiments

## selected_benchmarks

This experiment checks whether a method can learn valid LTLf separators on a compact suite of finite-trace classification tasks extracted from the paper's released benchmark archive. The suite includes Fixed Formulas, Hamming, Nim, OrderedSequence, random Boolean factors, SingleCounter, DoubleCounter, Subset, and Subword instances.

The comparison reports the selected-suite solve rate, whether every returned formula is valid, formula-size ratio on common solved tasks, the solve-rate delta against raw bounded VFB, and the reduction achieved when moving from full trace-suffix tables to first-position vectors. The solve rate is the primary metric because the reproduction uses a compact subset while the paper reports results over the full benchmark suite. Wall-clock time is deliberately excluded from scored metrics.
