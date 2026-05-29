# Method

The paper proposes Bolt, a CPU LTLf learner that first runs bounded VFB enumeration and then switches to Boolean Set Cover.

The VFB stage enumerates LTLf formulas by syntactic size. Each formula is evaluated on every suffix of every input trace, producing a characteristic table. Formulas with identical characteristic tables are observationally equivalent, so only one representative is retained.

If no separator is found by the LTL size bound, Bolt collapses each retained formula to the vector of first-position truth values over the traces. Boolean combinations of these retained formulas are then searched with only conjunction and disjunction. This Boolean Set Cover stage uses formula weight, observational equivalence on vectors, score based on correctly classified traces, approximate domination, beam search, and a divide-and-conquer fallback.

This reproduction implements the same computational steps in Python for a reduced CPU benchmark suite. It also implements raw bounded VFB as the local ablation baseline.
