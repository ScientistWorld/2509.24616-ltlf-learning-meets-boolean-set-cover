# Problem

Given two disjoint finite sets of finite traces, positive traces `P` and negative traces `N`, learn an LTLf formula (linear temporal logic on finite traces) that every trace in `P` satisfies and no trace in `N` satisfies. Among separating formulas, smaller ones (fewer syntax-tree nodes) are better: the goal is a small separator, found within a fixed compute budget.

Each trace is a non-empty sequence of valuations of a fixed set of atomic propositions (`a0`, `a1`, ...). Semantics are the standard finite-trace ones: `X[!] f` (strong next) holds at position i if position i+1 exists and `f` holds there; `X f` (weak next) holds if there is no next position or `f` holds there; `F f`, `G f`, `f U g`, `f R g` quantify over the remaining positions of the trace; `!`, `&`, `|`, `->`, `<->` are Boolean. A trace satisfies a formula when the formula holds at its first position.

The instances come from the ten-family LTLf learning benchmark suite released with the paper (five families with public instance generators: OrderedSequence, Subword, Subset, Hamming, RandomBooleanCombinationsofFactors). Their parameters follow the released suite: traces of length 16, 32 or 64, 3 to 9 propositions, and 5, 20 or 100 positive and negative traces (Hamming: one positive trace and negatives a few bits away from it). Many instances admit only separators far beyond the size that exhaustive enumeration of formulas can reach in the budget.

- Visible training instances: `data/train/instances/*.json` (standard benchmark format: `positive_traces`, `negative_traces`, `atomic_propositions`, plus `family` and `parameters` for information), listed in `data/train/manifest.json`. They are drawn from the paper's released suite.
- Hidden test instances: fresh draws from the same generators and parameter ranges, not available to methods.
