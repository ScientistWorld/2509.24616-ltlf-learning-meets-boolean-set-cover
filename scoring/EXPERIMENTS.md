# Experiments

## selected_benchmarks

This experiment checks whether a method can learn valid LTLf separators on a compact suite of finite-trace classification tasks extracted from the paper's released benchmark archive. The suite includes Fixed Formulas, Hamming, Nim, OrderedSequence, random Boolean factors, SingleCounter, DoubleCounter, Subset, and Subword instances.

The comparison reports the selected-suite solve rate, whether every returned formula is valid, evaluation coverage, formula-size ratio on common solved tasks, and solve-rate delta against the provided reference baseline. The solve rate is the primary metric because the reproduction uses a compact subset while the paper reports results over the full benchmark suite. Wall-clock time and method-internal diagnostics are deliberately excluded from ranking metrics.
