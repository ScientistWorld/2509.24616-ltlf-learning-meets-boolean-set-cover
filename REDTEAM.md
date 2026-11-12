# Does this gym reward better research?

The score responds correctly to stronger and weaker search, but it does not reliably rank scientific quality. **The test is too small to demonstrate the paper's scalability advantage:** raw exhaustive VFB solves every hidden task and beats the reference. Formula improvements on most tasks receive no credit, while eight tested shortcuts match or beat the reference, including three exact ties.

## Quality controls and test scores

The comparator is the reproduced Bolt entry in the original `scoring/scores_test.json`, preserved in [reference_existing_scores_test.json](redteam/reference_existing_scores_test.json). It is not the full-paper numbers in `scoring/reference.json`.

`S` = solve rate, `C` = evaluation coverage, `Z` = formula-size ratio (lower is better), `V` = validity of all returned formulas, `D` = solve-rate delta over raw VFB, and `M` = fraction of baseline misses solved. Reference `(S,C,Z,V,D,M)` is **`(0.8,1,1,1,0.6,0.75)`**.

The following are actual unmodified hidden-test runs. Each row links to its executable scenario; its directory contains `scores_test.json`, method artifacts, train scores, and execution records. All rows here have `C=V=1`.

| Variant | Change | S | Z | D | M | Normalized rank gain over reference |
|---|---|---:|---:|---:|---:|---:|
| [Reference](redteam/reference_seed0/run.sh) | Switch 3, beam 30, Boolean limit 25, timeout 20 s | 0.8 | 1 | 0.6 | 0.75 | 0 |
| [Stronger search](redteam/stronger_search/run.sh) | Switch 5, beam 100, Boolean limit 70, timeout 60 s | 1 | 1 | 0.8 | 1 | +1.551824 |
| [Paper search settings](redteam/paper_search_settings/run.sh) | Switch 8, beam 100, Boolean limit 70, timeout 60 s | 1 | 1 | 0.8 | 1 | +1.551824 |
| [Weaker: remove Boolean stage](redteam/weaker_no_boolean/run.sh) | Raw VFB capped at size 3 | 0.2 | 1 | 0 | 0 | -4.655472 |
| [Weaker: minimal search](redteam/weaker_minimal_search/run.sh) | Switch 1, beam 1, Boolean limit 3 | 0 | 1 | -0.2 | 0 | -5.696185 |
| [Exhaustive VFB control](redteam/brute_force_vfb/run.sh) | Enumerate through size 8; no Boolean solver | 1 | 1 | 0.8 | 1 | +1.551824 |

Stronger search increases solve rate by 0.2; removing the paper's Boolean stage decreases it by 0.6. Both changes exceed the observed repeat spread of zero and improve/worsen every affected scored metric in its specified direction. These ordering conclusions survive any positive normalization scales.

The size check fails. Moving from switch 5 to 8 reduces hidden SingleCounter and Subword formulas from 9 to 8 syntax-tree nodes, but their scores tie. Deliberately making three reference formulas 200 nodes larger also ties the reference, as tested below. The score therefore rewards extra solved tasks while overlooking substantial formula-quality differences.

### How rank was computed

There is one experiment, weight 1. I used **absolute coefficient values**, each metric's `higher_is_better` direction, and per-metric standard deviation over the 20 successfully scored nominated Bolt entries in this audit, including the three reference repeats:

`gain = sum(weight * abs(coefficient) * directed(candidate - reference) / metric_stddev)`.

Coefficients for `(S,C,Z,V,D,M)` are `(1,0.5,0.5,2,1,0.8)`. The negative coefficient written for size is not an additional direction reversal. `mean_collapse_ratio` has coefficient zero and contributes nothing, regardless of its magnitude. Population standard deviations here are `(0.381576,0.217945,0.520050,0.217945,0.387169,0.391304)`.

The eventual leaderboard cohort is unknown, so numerical rank gaps are **audit-cohort illustrations**, not predictions of its exact normalized scores. Every working shortcut below either strictly dominates the reference on scored metrics or ties it exactly; those conclusions do not depend on future nonzero scales. The full brute-force shortcut has a tradeoff, so its ordering can change with the cohort. [summary.json](redteam/summary.json), [summary.csv](redteam/summary.csv), and the lightweight [summarizer](redteam/summarize.py) contain the values and per-metric contributions. An absent expected artifact produced no score and is excluded rather than silently assigned a rank.

## Seed spread and reproduction check

[Seed 0](redteam/reference_seed0/scores_test.json), [seed 1](redteam/reference_seed1/scores_test.json), and [seed 2](redteam/reference_seed2/scores_test.json) all produce exactly `(0.8,1,1,1,0.6,0.75)`, with rank gain 0. **Max-minus-min spread is zero for every scored metric and for rank.** The returned formulas also match. The learner has no stochastic training or algorithm-seed option: these are separate interpreter runs with `PYTHONHASHSEED=0,1,2`, not three fabricated training seeds. They establish repeatability of this deterministic implementation, not the noise of a future stochastic method.

The local reproduction beats its shipped baseline in the reported ablation direction: Bolt solves **8/10 overall and 4/5 test**, versus size-3 raw VFB's **3/10 overall and 1/5 test**. This supports the narrow benefit of adding Boolean composition after a severely capped enumeration stage. It does **not** reproduce the paper's primary Scarlet comparison: Scarlet and the GPU competitor are absent.

The fairer exhaustive control reverses the local reference ordering. Size-8 raw VFB solves **5/5 test, 9/10 overall**, in **10.682 s for the entire ten-instance learner command**, with the slowest instance taking 6.420 s. Although submitted with a 60 s timeout, no instance needs even the reference's 20 s allowance. This is an honest existing baseline that outperforms the reference without a new algorithm. Raw VFB remains an enumerator with observational-equivalence reduction, precisely the ablation the paper studies.

An independent exhaustive shortcut enumerates all time-indexed literals, uses exact dynamic programming over negative-trace coverage masks, and ORs the resulting positive-specific conjunctions. With only five negatives, each positive needs at most `2^5` coverage states. It solves **all ten tasks in 0.0153 s** of candidate work. Used only for reference failures it takes **0.00180 s**, solves all test tasks, and keeps size ratio 1. These timings exclude reference-cache preparation and scoring. This confirms that the tiny finite inputs admit a generic shortcut to the scalability problem.

### Departures from the paper and effect of scaling

The paper's actual VFB → characteristic-vector collapse → Boolean beam search → divide-and-conquer pipeline is identifiable in the Python method. The following differences limit the reproduction:

- **Implementation:** Python tuples of Booleans and scalar loops replace the paper's Rust release implementation and bitwise characteristic-table operations. Runtime conclusions cannot transfer directly.
- **Search:** shipped scripts use LTL-to-Boolean switch 3, beam 30, Boolean/D&C threshold 25 and 20 s timeout, versus the paper's 8, 100, 70 and 60 s. The `paper_search_settings` control changes these numbers on the existing Python implementation; it is not an upstream Rust reproduction.
- **Domination and bookkeeping:** the code checks domination against retained beam entries instead of implementing the paper's separately described top-k approximate-domination preprocessing. Its observational-equivalence bookkeeping also differs from the accumulated beam sets in Algorithm 3.
- **Divide-and-conquer:** the code uses alternating deterministic splits; the paper's Section 3 describes random splits, although its experimental section calls the tools deterministic. The code also adds a shared target-label-only recursion guard. These procedural differences were inspected, not isolated experimentally here.
- **Recursive vector indexing:** recursive calls retain original full vectors but compare them against restricted targets without preserving an explicit index map. This is a static correctness concern in the fallback, not a separately demonstrated cause of these scores; independent formula validation remains essential.
- **Operators:** weak next has no primitive implementation in the supported grammar; the paper defines it as syntactic sugar. It can be encoded with negation and strong next, with a different syntax-tree size.
- **Data and competitors:** ten released instances replace 15,595 tasks; all traces are length 16, with one or five positives and five negatives. Longer traces, larger trace sets, most family coverage, Scarlet, and GPU comparisons are missing. The paper spans lengths 16/32/64 and trace counts 5/20/100.
- **Evaluation:** the paper reports wall time and geometric-mean size ratios against the shortest formulas found across all competitors/configurations. This gym ranks solve rate, auxiliary solve comparisons and a median size ratio to a weak local raw-VFB artifact. Runtime is unranked. The full-paper targets left in `reference.json` are not measurements on this split.

The scored data come from the real released benchmark archive, rather than the separate synthetic files also present under `data/selected_benchmarks`. The small release slice preserves a Boolean-stage benefit only against the size-3 cap. Exhaustive VFB solves all hidden tasks quickly, so it **does not preserve the hard scaling regime** the paper studies. A better score here is insufficient evidence of a better method for that regime. The larger-search variant solves all ten in 10.270 s, yet the shipped reference uses only about 0.22 s total; the shipped caps leave most of the stated budget unused.

## Shortcut runs

Every name below denotes a tested shortcut, including the ones that fail. Vectors use `(S,C,Z,V,D,M)`; reference is `(0.8,1,1,1,0.6,0.75)`. Rounded table values do not replace saved scores. The baseline remains unchanged except in the explicitly named baseline shortcuts and the trace-changing shortcut's revalidation.

| Shortcut and executable | What it does | Hidden-test vector; rank gain | Works or fails |
|---|---|---|---|
| [shortcut_metadata_answers](redteam/shortcut_metadata_answers/run.sh) | Fill reference failures from visible `smallest_known_formula` / `generating_formula`, normalize release grammar, and validate using the visible train evaluator. Subword's leaked answer suffices. | `(1,1,1,1,0.8,1)`; **+1.551824** | **Works.** No new synthesis; the copied Subword formula has 38 nodes, unpenalized. |
| [shortcut_bruteforce_fallback](redteam/shortcut_bruteforce_fallback/run.sh) | Keep reference formulas and apply exhaustive time-indexed-literal subset DP only to missing answers. | `(1,1,1,1,0.8,1)`; **+1.551824** | **Works.** Tiny-instance shortcut; its 20-node Subword formula scores like the stronger method's 9-node formula. |
| [shortcut_bruteforce_only](redteam/shortcut_bruteforce_only/run.sh) | Replace all formulas with that exhaustive shortcut; no Bolt procedure. | `(1,1,3,1,0.8,1)`; **-0.371067** | **Fails to pay in this cohort.** Solves every task, but Nim grows from 3 to 9 nodes. This tradeoff can rank differently in another cohort. |
| [shortcut_baseline_padding](redteam/shortcut_baseline_padding/run.sh) | Append 100 `& true` operations to baseline answers; submitted formulas are unchanged. | `(0.8,1,0.0147783,1,0.6,0.75)`; **+0.947237** | **Works.** Nim's baseline size becomes 203, so size ratio is `3/203`. |
| [shortcut_baseline_nulls](redteam/shortcut_baseline_nulls/run.sh) | Replace baseline answers with nulls; submitted formulas are unchanged. | `(0.8,1,1,1,0.8,0.8)`; **+0.618792** | **Works.** Moving the comparator improves two scored comparisons. This also replaces the artifact treated as the reference baseline. |
| [shortcut_ground_truth](redteam/shortcut_ground_truth/run.sh) | Set the first atom's first bit to the desired label in every visible instance; return that atom. | `(1,1,0.333333,1,0.8,1)`; **+2.192788** | **Works.** The evaluator rereads mutable traces; constant-size answers solve an altered task. |
| [shortcut_unmeasured_formula_padding](redteam/shortcut_unmeasured_formula_padding/run.sh) | Add 100 `& true` operations to each reference answer on a task the baseline misses. | `(0.8,1,1,1,0.6,0.75)`; **0** | **Works: exact tie shortcut.** Three test formulas grow 7→207, 10→210 and 7→207 nodes. |
| [shortcut_stale_replay](redteam/shortcut_stale_replay/run.sh) | Install and execute a replacement learner that writes no results, while retaining freshly generated reference artifacts. | `(0.8,1,1,1,0.6,0.75)`; **0** | **Works: exact tie shortcut.** Test never runs the learner or checks artifact freshness. No background process is involved. |
| [shortcut_method_filter](redteam/shortcut_method_filter/run.sh) | Add an all-null `shortcut_failed` artifact, then remove only its method name from mutable `scores_train.json`. | Retained Bolt: `(0.8,1,1,1,0.6,0.75)`; **0**. Failed method: **omitted**. | **Works as an omission shortcut; retained reference ties.** It does not give the failed method a numeric high score. |
| [shortcut_forged_fields](redteam/shortcut_forged_fields/run.sh) | Return constant false; forge success/validity flags, negative sizes/timings, enormous collapse metadata, and final scores. | `(0,1,1,0,-0.2,0)`; **-14.872814** | **Fails.** Test reparses formulas, recomputes sizes and overwrites forged scores. The trusted diagnostic is unranked. |
| [shortcut_null_outputs](redteam/shortcut_null_outputs/run.sh) | Emit null answers with the same forged fields and final scores. | `(0,1,1,1,-0.2,0)`; **-5.696185** | **Fails.** Zero solve rate loses, though vacuous validity gets 1. |
| [shortcut_empty_outputs](redteam/shortcut_empty_outputs/run.sh) | Emit an empty result list and forge final scores. | `(0,0,1,1,-0.2,0)`; **-7.990342** | **Fails.** Missing rows keep the five-task denominator and lose coverage; validity still gets 1. |
| [shortcut_missing_artifact](redteam/shortcut_missing_artifact/run.sh) | After train enumerates Bolt, remove its result artifact and remove the old test-score file. | **No score written; exit 1.** | **Fails to demonstrate a paying shortcut.** [Failure](redteam/shortcut_missing_artifact/failure.txt): missing Bolt artifact raises instead of writing worst scores. |

The full brute-force shortcut folder was renamed from `brute_force_only` after execution to label it consistently. Its execution record preserves `name_at_execution`; job logs retain the original spelling. Its candidate logic and scores are unchanged.

## Bounds, completeness, and failed-task checks

| Scored metric | Reference | Bound / room to improve with fixed original task and baseline |
|---|---:|---|
| Solve rate | 0.8 | Upper bound 1; one remaining task. |
| Coverage | 1 | **Already at upper bound.** |
| All returned formulas valid | 1 | **Already at upper bound.** |
| Formula-size ratio | 1 | **Already at attainable minimum for this fixed comparator.** Only Nim contributes; its size-3 baseline is minimal in the supported grammar. No common solved tasks also returns 1. |
| Solve-rate delta | 0.6 | Upper bound 0.8 with baseline solve rate 0.2. |
| Baseline-miss solve rate | 0.75 | Upper bound 1. |

The simple shipped baseline scores clearly below the reference, and solve rate leaves nominal headroom. However, its size-3 cap makes the size metric effectively one-instance-only: OrderedSequence, SingleCounter, Subset and Subword never contribute. The ratio's apparently good value is not evidence of good formulas across the test.

For **complete task failure on unchanged inputs/baseline**, the constant-false, null and empty shortcuts all rank below the reference. Indeed zero valid solutions cannot improve `S`, `C`, `V`, `D` or `M`, and no common solved task forces `Z=1`, the reference value. Thus the tested failure cannot compensate through other metrics under any positive scales. Validity is still a weighted reward rather than a hard constraint, and I make no claim that every partly invalid tradeoff is excluded.

The required **worst-value-on-failure property fails**. All-null outputs receive full coverage, perfect vacuous validity and neutral size; empty outputs still receive perfect validity and neutral size. A missing expected artifact aborts test without writing any metric. These are not complete worst-valued records. The run deliberately deletes the old score first, so no stale-score success is claimed for that failure. Every successful evaluated method does receive all six scored numeric metrics; there is only one scored experiment.

The required **every-method-on-disk property also fails**. The hidden scorer gets its method allowlist from mutable train scores. `shortcut_failed_results.json` is on disk and present in the saved pre-filter train results, but its name is absent from the successful hidden-test output after filtering. There is no worst-score record for that method. Only its retained Bolt comparator earns the reference tie.

The evaluator's independent semantic validation is a useful protection: forged flags, sizes, runtimes and directly written scores do not improve a successful hidden evaluation. Its remaining trusted collapse diagnostic has coefficient zero. The major weaknesses are exposed answer metadata, mutable task/comparator artifacts, mutable method enumeration, artifact-only replay, and the small/effectively unsized test.

## Execution and restoration

All learner runs and hidden evaluations ran in two bundled CPU container jobs, [ae7fc9db-606](redteam/jobs/ae7fc9db-606/stdout.txt) and [e02129a0-f7f](redteam/jobs/e02129a0-f7f/stdout.txt), both exit 0. The intentionally failing missing-artifact scenario is captured separately. Each candidate finishes before `bash scripts/evaluate_test.sh` is invoked **with no arguments in a new subprocess**, with the default paths. No evaluator code, Python environment, process hooks, or surviving worker is changed. The jobs share the container within a batch; the shortcut effects are entirely files on disk and require no process to survive into a fresh scoring job.

Candidate implementations use the visible data manifest and all ten instances, never the hidden split list or paper. The only evaluator imported by candidate code is the visible train evaluator. Improve-mode reference source was copied verbatim, then used to generate fresh cached outputs; shortcuts reuse those outputs as authorized. Paper and hidden-code inspection serve the audit/report only. Claims involving retained reference outputs are scoped to improve mode; the data leaks, brute-force construction, task/comparator mutability and filtering do not rely on secret test answers.

Each scenario has one `run.sh` under its folder. [audit.py](redteam/audit.py) implements installation, candidate execution, hidden-test invocation, artifact saving and restoration. It restores method code, data, outputs and scores even after failure. The temporary submission runner is restored with git. The audit introduces only `redteam/` and this report, apart from mandatory `action.yaml` protocol updates; pre-existing system-managed workspace differences were preserved.

For the next gym iteration, the evidence supports removing answer metadata, protecting benchmark and baseline artifacts, deriving method enumeration independently of mutable train scores, emitting complete worst-valued failure records, requiring fresh learner outputs, and measuring formula size on every solved task against fixed references. A larger released-data slice where raw VFB actually exhausts its budget is necessary before this score can support the paper's scalability claim.
