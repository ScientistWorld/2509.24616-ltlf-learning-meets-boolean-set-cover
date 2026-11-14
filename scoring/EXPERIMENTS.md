# Experiments

## budgeted_ltlf_learning

Establishes how well a learner finds *small* LTLf formulas separating positive from negative finite traces when compute is fixed. Each instance is solved by a fresh run of the method with 20 CPU seconds; the evaluator checks every returned formula on the traces itself.

The instances span all ten benchmark families of the paper's suite, 8 per family (ordered sequences, subwords, subsets, Hamming-distance perturbations, random Boolean combinations of temporal patterns, classic specification patterns, single and double binary counters, the game of Nim, and random conjunctions of specification patterns) over the suite's parameter ranges (trace length 16-64, 2-17 propositions, 5-100 traces per class). Many of them only have separators larger than what exhaustive enumeration can reach in the budget, so the experiment separates methods that scale to large formulas from methods that only find minimal formulas for easy instances; on others, the challenge is to stay close to the smallest known separator.

The three metrics measure the two sides of the trade-off the paper studies: how many tasks get a valid answer at all (`solve_rate`), how close the answers are to the smallest known separator (`size_ratio_geomean`), and both together (`size_efficiency`). Training instances are taken from the paper's released suite; the hidden test instances are new draws from the same generators and parameter ranges, so a method tuned to the training instances themselves gains nothing on the test.
