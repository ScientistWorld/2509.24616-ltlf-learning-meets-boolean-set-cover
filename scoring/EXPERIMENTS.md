# Experiments

## selected_benchmarks

This experiment checks whether a method can learn valid LTLf separators on a compact suite of finite-trace classification tasks. The suite includes patterns inspired by the paper's benchmark families: Subset, Subword, OrderedSequence, Hamming-like, and random Boolean factors.

The comparison reports the selected-suite solve rate, how many tasks are solved, whether every returned formula is valid, formula sizes on common solved tasks, and the reduction achieved when moving from full trace-suffix tables to first-position vectors. The solve rate is the primary metric because the reproduction uses a compact subset while the paper reports counts over the full benchmark suite.
