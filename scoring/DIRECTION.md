# Direction

Stay within LTLf learning from positive and negative finite traces under the fixed per-instance CPU budget.

Promising directions (the paper's own discussion lists better time/size trade-offs as open):

- Faster formula enumeration or Boolean-combination search (better data structures, pruning, vectorisation) so that more of the budget goes to useful search.
- Better Boolean Set Cover solvers or better splitting in divide and conquer, giving smaller combinations.
- Post-processing that shrinks a valid formula while keeping it a separator.
- Using the remaining budget well (anytime search: return a valid formula early, keep improving).
- Richer building blocks than bounded enumeration (e.g. temporal pattern fragments) as long as they are generic, not tied to particular instances.

Not improvements: classifiers that do not output LTLf formulas, reading answers from the benchmark release or the evaluator, hardcoding formulas, exceeding the budget through extra processes, or changing the traces.
