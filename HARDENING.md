# Hardening report (iteration 12)

This is the second hardening pass. Iteration 11 rebuilt the gym into a budgeted solver evaluation on hidden instances; its report is preserved in git history and its numbers in `notes/hardening/iter11/`. `REVIEW.md` listed three remaining weaknesses. This iteration fixes all three and closes a leniency the new families would have introduced.

Final run: job `e8b498b8-6d7`, pipeline `scripts/hardening/run_hardening.sh`, generated summary `notes/hardening/summary.md`.

## What changed

1. **Pass/fail no longer depends on node load** (REVIEW item 1).
   - Both evaluators budget **CPU time only**: 20 CPU s per instance, solver plus children, counted with `wait4`.
   - The wall-clock limit went from 50 s to **200 s (10× the budget)**. It now only stops hung runs.
   - In the final job, a reference run's wall time exceeded its CPU time by at most 2.5 s. Its largest CPU use was 12.5 s.
   - Separately, every solver on disk is now entered with the worst value of every metric *before* it runs (0 / 0 / 10). An interrupted or killed evaluation can therefore never leave a solver without a score.

2. **All ten benchmark families** (REVIEW item 2).
   - The five missing families are Fixed_Formulas, SingleCounter, DoubleCounter, Nim and Random_Conjuncts_from_Basis. The paper generates them by compiling the family's formula with Spot and sampling uniformly from its language and its complement.
   - Spot is not available here, so `eval/test/trace_sampler.py` reproduces that sampling without it:
     - It parses the benchmark syntax with Spot's operator precedence.
     - It uses rejection sampling, which is exactly uniform conditional on membership.
     - Where a class is too rare for rejection (e.g. `G(!a)` at length 64, or most random-conjunct formulas), it uses an **exact counting sampler** over subformula truth states. All 2^|AP| letters are evaluated as one bitmask.
   - Checks on the sampler:
     - Every released generating formula of the five families separates its released traces under this parser (298 instances checked).
     - The alternative precedence (`->` binding tighter than `&&`) fails on 88 of 131 released random-conjunct instances.
     - The exact counts equal brute-force enumeration on small cases.
     - Sampled traces are uniform: 28 strings, 658–760 draws each, expected 714.
   - **Hidden test: 80 instances.**
     - The original 40 are unchanged byte for byte.
     - The 40 new ones are 8 per new family. Parameter combinations are drawn from the release; seeds come from the OS and are not recorded (fresh random-conjunct formulas, fresh traces).
     - Propositions are renamed `a0..` by a random permutation.
   - **Train: 80 instances.** The original 40 are unchanged. The 40 new ones are 8 released instances per new family, with answer fields stripped and propositions renamed by a seeded permutation that is recorded in the manifest.

3. **A better method at the same budget, beyond noise** (REVIEW item 3).
   - `bolt_patterns` (`scripts/hardening/bolt_patterns.py`) keeps the reference pipeline and every setting, with one change: Boolean Set Cover also receives directed temporal patterns from Scarlet's fragment, `F(l1 & X[!](F(l2 & ...)))` and `!F(...)`.
     - These patterns are built by a small beam over literals.
     - They get their own beam slots, so they add to the reference's combination search without displacing it.
   - It is a methodological change, not more search. Its mean CPU per instance is **1.64 s against the reference's 1.78 s** on test (1.34 vs 1.36 s on train).
   - It beats the reference by **+0.048 size_efficiency** on the hidden test, paired 95% CI [+0.003, +0.101], and **+0.037** on train, CI [+0.002, +0.079].
   - The repeat spread of the reference is exactly 0 (below).

4. **Reference sizes now come from learner runs only** (new; needed for item 2).
   - The generating formulas of SingleCounter, DoubleCounter and Nim have 73–559 nodes.
   - Under iteration 11's rule (the generating formula always counts), an instance no learner solved would have had `r_i` in the hundreds. Any answer under that size would earn full credit there, and the 10× cap would no longer stop trace-by-trace constructions.
   - The paper's own size ratio is relative to the shortest formula found by learner runs.
   - New rule:
     - `r_i` is the smallest learner separator.
     - The generating formula counts only where it is smaller and some learner solved the instance.
     - Where no learner found a separator, `r_i` is the exhaustive-enumeration lower bound.
   - The lower bound was needed for 2 test instances and 1 train instance, all Hamming. Every counter, Nim and other new-family instance was solved by a learner.

5. **Reference sizes unreadable during runs** (small fix).
   - The hidden test chmods `eval/test/instances.json` and `lower_bounds.json` to 000 while solvers run, and restores them afterwards. A probe solver confirmed it cannot read them.
   - Solvers already received only traces, and formula records stay in memory.

## Do better results score higher?

Yes. All numbers are hidden-test numbers from the final job. "Paired Δ" is the mean per-instance difference in `size_efficiency` against `bolt`, with a 95% bootstrap interval and the count of instances better / worse / tied. "Rank gain" sums |coefficient| × directed improvement / cohort std. It is an illustration only: the cohort is this run's variants.

| method | before: iter 11 (40 hidden) | after: size_eff | solve | size ratio | paired Δ vs bolt | rank gain | mean CPU s |
|---|---:|---:|---:|---:|---|---:|---:|
| `bolt_patterns`: reference + directed-pattern atoms (new) | — | **0.893** | 0.975 | 1.193 | +0.048 [+0.003, +0.101] 15/11/54 | +0.35 | 1.64 |
| `bolt_portfolio`: anytime, reference then switch 9 / beam 150 | 0.808 | **0.894** | 0.963 | 1.238 | +0.049 [+0.021, +0.084] 20/0/60 | +0.30 | 6.01 |
| `bolt_simplify`: reference + greedy subformula deletion | 0.763 | **0.867** | 0.950 | 1.295 | +0.022 [+0.005, +0.046] 11/0/69 | +0.12 | 1.87 |
| **`bolt` (reference)** | 0.752 | **0.845** | 0.950 | 1.339 | — | 0 | 1.78 |
| `bolt_beam1`: beam width 1 | 0.591 | 0.686 | 0.850 | 1.846 | −0.159 [−0.215, −0.108] 1/30/49 | −1.21 | 2.09 |
| `bolt_switch3`: LTL2BS-switch 3 | 0.445 | 0.623 | 0.788 | 2.063 | −0.222 [−0.288, −0.161] 4/49/27 | −1.77 | 2.04 |
| `raw_vfb`: the paper's ablation without Boolean Set Cover | 0.400 | 0.488 | 0.488 | 3.255 | −0.357 [−0.455, −0.261] 1/37/42 | −3.73 | 2.61 |

- **`bolt_patterns`:**
  - It also improves `solve_rate` (+0.025) and the size ratio (log-ratio −0.116, CI [−0.227, −0.021]).
  - Its gains are on RandomBooleanCombinationsofFactors (family `size_efficiency` 0.649 → 0.948), Subword (0.663 → 0.767) and Hamming (0.420 → 0.578).
  - It loses a little on Subset (0.946 → 0.883) and DoubleCounter (0.858 → 0.838). It is a genuine trade-off, not a dominating patch, and still better on average beyond noise on both slices.
- **Train agrees:**

  | method | size_efficiency |
  |---|---:|
  | portfolio | 0.931 |
  | patterns | 0.929 |
  | simplify | 0.916 |
  | bolt | 0.892 |
  | beam1 | 0.773 |
  | raw_vfb | 0.588 |
  | switch3 | 0.575 |
- **Noise:**
  - The reference and the baseline ran twice on each slice (hardening run, then the official no-argument run). The spread was **exactly 0** on every metric and every instance.
  - The reference's outputs on the 40 original test instances are identical to iteration 11's (40/40).
  - It never came near its deadline: at most 12.5 CPU s, mean 1.8 s, against an 18 s internal stop and a 20 s budget.
- **Paper's direction:** adding Boolean Set Cover to bounded enumeration lifts `size_efficiency` from 0.488 to 0.845 and `solve_rate` from 0.488 to 0.950 (train: 0.588 → 0.892).

## Major shortcuts: fix and score before → after

"Before" is the state REDTEAM.md audited (rank gain against its reference) or iteration 11's run. "After" is this job's hidden test.

| Shortcut | Fix | Before | After |
|---|---|---|---|
| Copy answer metadata | iter 11: solvers receive only traces; train answer fields stripped; hidden instances are fresh unrecorded draws. Iter 12: same for the five new families. | +1.55 | Impossible |
| Exhaustive enumeration (`raw_vfb`) | iter 11: 40 hidden instances over the full grid. Iter 12: 80 over all ten families. | +1.55 | 0.488 / 0.488 / 3.25, rank −3.73 |
| Trace-by-trace literal construction (`literal_cover`) | 10× acceptability cap on every instance. Iter 12: learner-only `r_i`, so the counter/Nim generating formulas (73–559 nodes) cannot loosen the cap. | −0.37 | 0.206 / 0.613 / 5.28, rank −5.42 |
| Reference + literal fallback on failures (offline combination) | Learner-only `r_i`, exhaustive lower bounds, 10× cap | +1.55 | +0.007 `size_efficiency` (2 Hamming instances), rank +0.12. Left open, see below |
| Pad / delete the baseline's outputs; mutate traces; replay stale outputs; drop a method from a mutable list | iter 11: no baseline output enters any score; the evaluator scores against its own in-memory traces; every solver runs fresh; methods are enumerated from `scripts/solvers/*.sh` | +0.95 / +2.19 / tie / omitted | Not applicable |
| Forged fields / null / empty / crash / missing artifact | Only the formula string is read; failure = worst value. Iter 12: worst values are written for every solver before it runs. | −14.9 / validity stayed 1 / no score | `forged_fields`, `null_answer`, `crash`: 0 / 0 / 10 each |
| Node load decides pass/fail (REVIEW) | CPU-only budget; wall limit 200 s | Reference 0.7515 → 0.7475 under load | Reference wall − CPU ≤ 2.5 s; 0 instances near any limit |
| Read reference sizes during the hidden run | Files chmod 000 while solvers run | readable | Probe solver could not read them |
| Loose reference size on instances no learner solves (new families) | Learner-only `r_i`, else exhaustive lower bound | (would have arisen) | 0 instances use a generating formula of an unsolved instance |

## Shortcuts left open, and why

- **Writing down the families' generating formulas.** I measured an oracle that returns each instance's true generating formula.
  - **Alone:** 0.317 on test, far below the reference.
  - **As a fallback on top of the reference** (`bolt_or_generator_oracle`): 0.897, **+0.052** (9 instances, Subword, RandomBooleanCombinationsofFactors and Subset only). That is about the same as the honest improvements.
  - It is an upper bound, not a runnable rule. The oracle is given the answer; a template solver would have to *find* which subword, which patterns and which Boolean combination separate the traces. That is a search in the directed-pattern fragment, which is exactly what `bolt_patterns` does generically. On RandomBooleanCombinationsofFactors, `bolt_patterns` already scores 0.948, above the oracle fallback's 0.841 on that family.
  - The SYNTCOMP and Fixed families gain nothing from their generators: they are 73–559 nodes, or the reference is already at size 1.0.
  - Hardcoding family templates is listed as invalid in `scoring/CONSTRAINTS.md` and `DIRECTION.md`; it is left to the grader.
- **Reference + Lemma-1 trace-by-trace fallback** (+0.007 `size_efficiency`, +0.025 `solve_rate`).
  - It pays only on 2 Hamming instances where the reference returns nothing. There the trace-by-trace conjunction is a valid separator 3.2–4.0× the best-known size, and it is charged for that size.
  - Closing it would need a cap tighter than 4×. That would also unsolve 7 of the reference's own answers, which are 3–6.2× the best known, and the paper counts every valid formula as solved.
  - It is the paper's own Lemma 1 used as a completion step, so I left it.
- **Unused budget.** The anytime portfolio scores above the reference by using 6 CPU s instead of 1.8. That is legitimate headroom, as iteration 11 noted. It is no longer the only headroom: `bolt_patterns` matches it at the reference's CPU.
- **Not defended** (per the brief): detached processes escaping the process group's CPU accounting, and a solver that resets file permissions it does not own the right to read (an explicit circumvention, for the grader).

## Reference score before and after

| | size_efficiency | solve_rate | size_ratio_geomean |
|---|---:|---:|---:|
| iter 11, hidden (40 instances, 5 families) | 0.7515 | 0.900 | 1.600 |
| REVIEW rerun under load (50 s wall limit) | 0.7475 | — | — |
| **iter 12, hidden (80 instances, 10 families)** | **0.8449** | **0.950** | **1.339** |
| iter 12, of which the original 40 | 0.7356 | | |
| iter 12, of which the 40 new-family instances | 0.9543 | | |
| iter 11 → iter 12, train | 0.840 → 0.892 | 0.950 → 0.975 | 1.344 → 1.209 |

- **Original 40 instances.** The reference's formulas there are unchanged. Its score there fell from 0.7515 to 0.7356 only because `bolt_patterns` found smaller separators and tightened `r_i` on 4 instances:
  - t01: 98 → 29, below the generating formula;
  - t09: 18 → 17;
  - t37: 59 → 29;
  - t20: lower bound 10 → first learner separator, 49.
- **New families.** The reference is close to the best known on them (0.954). This is consistent with the paper, where Bolt's size ratio on these families is 1.00–1.07.
- The paper's Table 1 numbers stay in `scoring/reference.json` under `_paper_table1_*`. They are on a different scale.

## Headroom check

- **Bounds.** The reference is at no metric's bound: 0.845 of 1, 0.950 of 1, 1.339 against 1. A genuinely better method at the same CPU scores higher (`bolt_patterns` +0.048), and so does an anytime one (`bolt_portfolio` +0.049).
- **Brute force.** Exhaustive enumeration (`raw_vfb`, 0.488) and the trivial construction (`literal_cover`, 0.206) rank far below the reference.
- **Where the reference falls short** (test `size_efficiency` by family):

  | family | bolt | raw_vfb | bolt_patterns | bolt_portfolio |
  |---|---:|---:|---:|---:|
  | Hamming | 0.420 | 0.125 | 0.578 | 0.598 |
  | RandomBooleanCombinationsofFactors | 0.649 | 0.125 | 0.948 | 0.685 |
  | Subword | 0.663 | 0.250 | 0.767 | 0.706 |
  | DoubleCounter | 0.858 | 0.375 | 0.838 | 0.979 |
  | SingleCounter | 0.913 | 0.375 | 0.918 | 1.000 |
  | Subset | 0.946 | 0.500 | 0.883 | 0.967 |
  | Fixed_Formulas, Nim, OrderedSequence, Random_Conjuncts_from_Basis | 1.000 | 0.25–1.0 | 1.000 | 1.000 |

  Four families sit at the bound for the reference. As in the paper, they are easy for Bolt, and they keep the test faithful to the paper's suite. The headroom is in Hamming, the 100-trace Subword / RandomBooleanCombinations instances and the counters.
- **Ceiling on credit.** On 49 of 80 instances `r_i` is the reference's own answer, because no method found smaller. There, a better method can tie the reference but not exceed it, since `min(1, r_i/s)` caps credit at the best known, as the paper's ratio does. The demonstrated gains come from the remaining instances. I kept the cap rather than reward beating the best known, because uncapped per-instance credit would let a few instances with loose best-known sizes dominate the mean.

## Weights

One experiment (weight 1.0). Coefficients are unchanged: `size_efficiency` 1.0, `solve_rate` 0.5, `size_ratio_geomean` 0.5 (lower is better). Nothing in the new results argued for changing them.

## Could not fix / stated plainly

- **Spot itself is not used.** The five formula-based families are sampled by my own exact uniform sampler, validated against the release as described above. The paper's sampler caps huge counts at 2^1023, which introduces a tiny bias that mine does not have.
- A random-conjunct formula whose exact sampler would exceed 12,000 states is redrawn. None was needed in this draw (the largest of 40 released formulas I tested needed 11,311).
- **Python port, not the Rust binary.** Hence the 20 CPU-second budget, and the memory threshold usually switching before size 8.
- **Scarlet and the GPU learner are absent.** Best-known sizes come from this gym's learner runs, with exhaustive lower bounds on 2 test Hamming instances.
- **The reference keeps the Rust tool's immediate split above 128 traces** (a `u128` limitation of the authors' implementation that the paper does not mention). Removing it is a possible improvement; I did not test it.
- **The paper's Nim/counter difficulty is not reproduced.** In the paper Bolt solves only about half of Nim and the counters within 60 s. Here, on uniformly sampled traces, the Python reference solves every new-family test instance; its only unsolved test instances are 4 Hamming ones. On the counters it is below 1.0 because its formulas are larger than the best known, not because it fails.
