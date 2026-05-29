# Problem

Given two disjoint finite sets of finite traces, positive traces `P` and negative traces `N`, learn an LTLf formula that accepts every trace in `P` and rejects every trace in `N`.

Each trace is a non-empty sequence of valuations over a fixed finite set of atomic propositions. The learned formula is judged by whether its LTLf semantics over finite traces separates the two trace sets. Smaller formulas are preferred when multiple valid separators exist.

This workspace evaluates small benchmark instances in the same format as the paper's benchmark suite: JSON files containing positive traces, negative traces, atomic proposition names, and metadata.
