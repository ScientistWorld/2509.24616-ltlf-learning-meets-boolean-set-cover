# Hardening report (iteration 11)

## Summary

The old gym scored formulas that methods wrote, ahead of time, for 5 visible test instances (10 instances in total). Exhaustive enumeration solved the whole test and outranked the reference. Formula size counted on one instance only, and 8 shortcuts matched or beat the reference (REDTEAM.md).

The test now **runs every method itself**, under a budget, on **hidden instances**:

- **Solvers.** A method is a solver script in `scripts/solvers/<name>.sh`. The train and test evaluators run every such script once per instance, in a fresh process, with **20 CPU seconds**. CPU used by child processes counts. There is also a 4 GB address-space limit and a 50 s wall-clock limit.
- **Scoring.** The evaluators read only the formula string, then parse it and check it on the traces themselves.
- **Instances.** The hidden test has 40 new draws from the paper's own instance generators (`eval/test/build_instances.py`). They cover the five generator families and the released parameter ranges, and their seeds were never recorded. None of them appears in the public release (all 7,215 released files of these families checked). Train is 40 released instances with the answer fields removed.
- **Reference sizes.** Each instance has a fixed reference size `r_i`, held in `eval/`. It is the smallest separator from the generating formula or from any learner run. Where no learner found one (3 test, 2 train long-trace Hamming instances), it is a lower bound proven by exhaustive enumeration (9–10 nodes).
- **Metrics.** An answer counts only if it is valid and at most 10·`r_i` nodes. The three metrics are `size_efficiency` (primary, coefficient 1.0), `solve_rate` (0.5) and `size_ratio_geomean` (0.5, lower is better). A run that fails everywhere scores 0 / 0 / 10, the worst value of all three.
- **Reproduction.** The reproduction was brought back to the paper's own method and settings (`method/ltlf_bolt.py`):
  - bitwise characteristic tables (Appendix A);
  - top-k approximate domination with size-dom 10 in the collapse;
  - beam search over `|`/`&` with width 100, up to D&C-switch 70;
  - the Rust tool's divide and conquer (non-overlapping right subproblem, alternating split, immediate split above 128 traces);
  - LTL2BS-switch 8, plus the paper's memory threshold (500k formulas);
  - the paper's operator set, which is also the evaluated grammar.

  It runs until it succeeds or uses 90% of the budget, like the paper's tool runs until its timeout.

Experiment records:
- final run: `jobs/a8fc730a-b6e`, summary in `notes/hardening/summary.md`;
- the first version of this harness: `jobs/370d49e7-7da`, kept in `notes/hardening/job1/`;
- the pipeline that produced both: `scripts/hardening/run_hardening.sh`.

The "rank gain" columns below are illustrations only. Each sums |coefficient| × the improvement over `bolt` in the metric's better direction, divided by that metric's standard deviation across this iteration's variant cohort.

## Do better results score higher?

Yes. All rows are hidden-test numbers from the final job. "Paired Δ eff" is the mean per-instance difference in `size_efficiency` against `bolt`, with a 95% bootstrap interval over the 40 instances, and the count of instances that are better / worse / tied.

| method | size_efficiency | solve_rate | size_ratio_geomean | paired Δ eff vs bolt | rank gain |
|---|---:|---:|---:|---|---:|
| `bolt_portfolio`: reference, then a switch-9 / beam-150 Bolt in the leftover budget, keep the smaller formula, simplify | **0.808** | 0.925 | 1.452 | +0.057 [+0.018, +0.115], 14/0/26 | +0.40 |
| `bolt_simplify`: reference + greedy deletion of redundant subformulas | 0.763 | 0.900 | 1.573 | +0.011 [+0.001, +0.025], 7/0/33 | +0.06 |
| **`bolt` (reference)** | **0.752** | **0.900** | **1.600** | — | 0 |
| `bolt_beam1`: beam width 1 | 0.591 | 0.800 | 2.279 | −0.161 [−0.237, −0.093], 1/17/22 | −1.30 |
| `bolt_switch3`: LTL2BS-switch 3 (the paper says smaller switches give larger formulas) | 0.445 | 0.575 | 3.157 | −0.306 [−0.408, −0.208], 2/27/11 | −2.94 |
| `raw_vfb`: the paper's ablation without Boolean Set Cover | 0.400 | 0.400 | 3.981 | −0.352 [−0.482, −0.224], 1/20/19 | −3.94 |

- **Train agrees:**

  | method | size_efficiency |
  |---|---:|
  | portfolio | 0.893 |
  | simplify | 0.855 |
  | bolt | 0.840 |
  | beam1 | 0.707 |
  | raw_vfb | 0.525 |
  | switch3 | 0.412 |

  Paired against bolt on train: portfolio +0.053 [+0.018, +0.101], 11/0/29; simplify +0.015.
- **Noise:** the reference and the baseline were each run twice on both slices; the spread was exactly 0 on every metric and every instance. The reference never came near its deadline: it used at most 13.2 CPU s on test and 8.6 s on train (mean 2.3 s and 1.5 s), against an 18 s deadline. So its output does not depend on machine speed.
- **Paper's direction:** adding Boolean Set Cover to bounded enumeration lifts `size_efficiency` from 0.40 to 0.75 and `solve_rate` from 0.40 to 0.90. The difference is far above the zero repeat spread.
- **Before → after:** in the old gym, larger-search variants scored above the reference only by solving the last of 5 test tasks. Making three formulas 200 nodes larger left the score unchanged. Here every size change on every instance counts. In this harness's first version (job 1), the variants already ranked in the same order: simplify +0.011, beam1 −0.156, switch3 −0.313, raw VFB −0.368.

## Major shortcuts: fix and score before → after

"Before" is the old gym (REDTEAM.md, rank gain against its reference). "After" is the hidden-test score of the final job.

| Shortcut | Fix | Before | After |
|---|---|---|---|
| Copy the answer metadata (`smallest_known_formula`, `generating_formula`) | Solvers receive only traces. Train files have the answer fields removed. Hidden instances are new draws (seeds ≥ 10⁶, never recorded), absent from the release (checked). | +1.55 (tie with the stronger method) | Impossible: there is no answer to copy |
| Exhaustive enumeration (`raw_vfb`), the brute force the paper avoids | 40 hidden instances over the paper's full parameter grid. Many have separators beyond what enumeration reaches in 20 CPU s. | Solved 5/5 test, +1.55 | 0.400 / 0.400 / 3.98, rank −3.94 |
| Brute-force trace-by-trace literal construction (`literal_cover`, the polynomial version of the redteam's DP) | Size is measured against `r_i` on every instance. Answers more than 10× `r_i` do not count. | −0.37 (the old size metric counted one instance) | 0.204 / 0.625 / 5.38, rank −4.81 (job 1, before the 10× rule: 0.314 / 1.0 / 4.29) |
| Reference + brute-force fallback on failures (`bolt_literal_fallback`, combined offline from the saved runs) | Learner-only `r_i`, exhaustive lower bounds where no learner succeeds, 10× rule | +1.55 | **Job 1: +0.100 size_efficiency, rank +0.89.** The literal cover was the only "known" separator on 4 Hamming instances, so it earned full credit there. **Final: +0.006, rank +0.11:** one instance where the literal cover comes within 10× of the learners' best. |
| Pad or delete the baseline's outputs to shift the comparison | No baseline outputs enter anyone's score. Every comparison constant (`r_i`, budget, cap, instance count) is fixed in `eval/`. | +0.95 / +0.62 | Not applicable |
| Mutate the traces the evaluator re-reads | The evaluator scores against its own in-memory copy. Solvers get a temporary copy. Test traces live only in `eval/test/`. | +2.19 | Not applicable |
| Pad formulas on instances that are not measured | Size is measured on every instance. | Tie (0) | Padding lowers `size_efficiency` on that instance |
| Replay stale outputs | The hidden test runs each solver fresh on inputs it has never seen. | Tie (0) | Not applicable |
| Drop a failing method from a mutable list | Methods are enumerated from `scripts/solvers/*.sh`. A crash scores worst. | Omitted | `crash`: 0 / 0 / 10 |
| Forged validity, size or score fields | Only the formula string is read. | −14.9 | `forged_fields`: 0 / 0 / 10 |
| Null or empty outputs | Unsolved means the worst value of every metric. | Coverage and validity stayed at 1 | `null_answer`: 0 / 0 / 10 |
| Missing artifact aborts the scorer | A missing or crashed answer scores as unsolved. | No score written | 0 / 0 / 10 |
| New: extra parallel processes to exceed the budget (`parallel_portfolio`) | CPU from `wait4` usage includes children. Over-budget answers count as unsolved. | — | Rejected on the instance that used 28.6 CPU s. The other 7 test instances stayed within budget and count as normal. |
| New: read another solver's answers for the hidden instances from disk | By default the hidden test keeps records in memory and writes only formula-free details. Hardening runs deleted their formula files; none were ever committed. | — | Not possible |

## Shortcuts left open, and why

- **Hand-written generator templates.** On 7 test instances the best-known size is still the generating formula: 100-trace Subword and RBC instances where Bolt's combinations are larger. The reference reaches 0.665 and 0.727 on those families. A solver that wrote down the five generators' formula shapes could gain there, at most about 0.1 in `size_efficiency`. I did not test this. A generic temporal-pattern learner (Scarlet's fragment) would earn the same and is a legitimate direction. Hardcoding the families is listed as invalid in `scoring/DIRECTION.md` and `CONSTRAINTS.md`, and is for the grader to catch.
- **Reading `eval/test/instances.json` at run time.** A solver could learn its instance's `r_i` (a size, not a formula) by matching traces. That gives no separator; the constraints forbid it.
- **Unused budget.** The reference stops at its first separator after 2.3 CPU s on average. Anytime search in the rest of the budget (the portfolio) is a legitimate improvement, and it is the headroom shown above, not a loophole.
- **Not defended:** detached processes that escape the process group and its CPU accounting (per the brief, there are no defences against leftover processes); and hardware differences for methods that sit at the budget edge. The reference has a margin of at least 4.8 s.
- **The 10× threshold.** A trace-by-trace formula still counts where it is within 10× of the best learner (1 test instance, +0.006).

## Reference score before and after

- **Old gym (5 test instances):** solve rate 0.8, size ratio 1.0 (against a size-3 baseline, on one instance), validity 1, coverage 1.
- **New gym, hidden test (40 instances):** `size_efficiency` 0.752, `solve_rate` 0.900, `size_ratio_geomean` 1.600.
- **New gym, train (40):** 0.840 / 0.950 / 1.344.

The test is harder than train (0.75 vs 0.84). Both are random 40-instance samples from the same grid, and every variant keeps the same order on both slices.

The paper's Table 1 numbers stay in `scoring/reference.json` under `_paper_table1_*`: Bolt 0.9217 solved with ratio 1.01; Scarlet 0.7353 with 1.15. They are on a different scale: 15,595 tasks, Rust, a 60 s timeout, and the ratio taken over solved tasks only.

## Headroom check

The reference is at no metric's bound: 0.752 of 1, 0.900 of 1, 1.600 against 1. Exhaustive enumeration and the trivial construction rank well below it, and the anytime portfolio scores above it by more than the noise.

Where the paper's method falls short, by family (reference `size_efficiency` on test):

| family | bolt | portfolio | raw_vfb |
|---|---:|---:|---:|
| Hamming | 0.42 | 0.60 | 0.13 |
| Subword | 0.67 | 0.71 | 0.25 |
| RBC | 0.73 | 0.77 | 0.13 |
| Subset | 0.95 | 0.97 | 0.50 |
| OrderedSequence | 1.0 | 1.0 | 1.0 |

- **Hamming:** on 3 test instances no learner finds any separator.
- **OrderedSequence:** easy for every learner, as in the released suite.

This takes the place of adding a separate scored experiment: the single experiment now spans the paper's full parameter grid, including the regime where the paper's method falls short.

## Weights

There is one experiment (weight 1.0). Its coefficients are `size_efficiency` 1.0, `solve_rate` 0.5 and `size_ratio_geomean` 0.5. The paper reports solved tasks and size ratio as its two independent measures, and `size_efficiency` combines them into the trade-off the paper is about. I did not change any weights after the runs.

## Could not fix / stated plainly

- **Five of ten families.** Only the five families whose generators are pure Python are used. The other five need the Spot model checker.
- **Python port.** The reference is a Python port, not the authors' Rust binary, so the budget is 20 CPU s rather than 60 s, and the memory threshold usually sets the switch earlier than size 8.
- **Scarlet and the GPU learner are absent.** Best-known sizes come from my runs and generating formulas, not from all of the paper's tools.
- **Weaker reference sizes on 3 test instances.** Where only lower bounds are known, `r_i` is a bound (9–10 nodes) and not an achieved size, so good answers there score below 1.
- **A drop in measured reference score.** The final reference score (0.752) is lower than job 1's (0.768) because the portfolio found smaller separators and tightened `r_i`. The reference's formulas are identical in both jobs.
