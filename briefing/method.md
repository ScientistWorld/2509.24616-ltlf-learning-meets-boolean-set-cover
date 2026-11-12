# Method (reference solver `scripts/solvers/bolt.sh`)

The paper proposes Bolt, a CPU LTLf learner that first enumerates small LTLf formulas exhaustively and then switches to Boolean Set Cover: it searches for conjunctions/disjunctions of the formulas it has already enumerated.

`method/ltlf_bolt.py` is a Python port of the paper's algorithm that follows the authors' Rust implementation (fetched into `method/Bolt/` by `scripts/download.sh`) where the paper leaves details open:

1. **VFB enumeration** (Algorithm 4): bottom-up enumeration by syntactic size with unary `! X X[!] F G` and binary `& | U R`, evaluated as characteristic tables with bitwise operations (Appendix A; one Python integer per formula, bit `i*n+t` = position i of trace t), keeping one formula per distinct table (observational equivalence). It stops at LTL2BS-switch = 8, or earlier at a memory threshold of 500k retained formulas (the paper chooses the switch "based on a memory or time threshold").
2. **Collapse** (Algorithm 1): formulas are reduced to their characteristic vectors (truth value at the first position of each trace); equal vectors are merged, and a formula is dropped when one of the `size-dom = 10` formulas of strictly smaller size with the most correctly classified traces dominates it (fast approximate domination, Section 3.2).
3. **Beam search for Boolean Set Cover** (Algorithm 3): enumerate `|`/`&` combinations by weight, keep the 100 best per weight (most correctly classified traces), skip equivalent and dominated combinations, up to weight D&C-switch = 70.
4. **Divide and conquer** (Algorithm 2 with the paper's two optimisations): when beam search fails (or a subproblem has more than 128 traces, as in the Rust tool), split the larger class alternately, solve the first half, recurse only on the traces it does not already handle, and combine with `|` or `&`.

The Boolean stage runs until it succeeds or 90% of the CPU budget is spent (the paper's tool runs until its 60 s timeout). `scripts/solvers/raw_vfb.sh` is the paper's ablation baseline: the same enumeration without the Boolean Set Cover stage, run until a separator is found or the budget or a 1 GB memory estimate is exhausted.

Departures from the paper: Python instead of compiled Rust (much slower per operation, so the budget is 20 CPU seconds instead of 60 s and the switch is often set by the memory threshold rather than by size 8); the Boolean stage uses `|` and `&` as in the paper's text (the Rust code also tries `<->`); the LTL stage uses the paper's operator set, which is also the evaluated grammar (the Rust code also enumerates `->` and `<->`); beam search scores a whole weight before keeping the best 100 (the Rust code inserts sequentially into a bounded heap).
