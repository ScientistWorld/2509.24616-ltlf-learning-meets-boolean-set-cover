# Overview

`LTLf Learning Meets Boolean Set Cover` introduces Bolt, an LTLf learner that avoids the exponential growth of exhaustive formula enumeration by switching from bounded LTLf enumeration to Boolean Set Cover over already discovered formulas. The paper reports that Bolt solves more of its 15,595-task benchmark suite than the state of the art within a 60 s timeout while returning formulas of near-minimal size, and that removing the Boolean Set Cover stage (raw enumeration) solves fewer tasks.

This gym measures that trade-off under a fixed compute budget: each method is a solver run on every instance with 20 CPU seconds, scored on whether it returns a valid separating formula and how close its size is to the best known separator. Instances cover all ten benchmark families of the paper's suite. Training instances come from the paper's released suite; the hidden test instances are fresh draws from the paper's own generators. The reference is a Python port of Bolt at the paper's settings; the baseline is the paper's raw-enumeration ablation.

---

# Problem

Given two disjoint finite sets of finite traces, positive traces `P` and negative traces `N`, learn an LTLf formula (linear temporal logic on finite traces) that every trace in `P` satisfies and no trace in `N` satisfies. Among separating formulas, smaller ones (fewer syntax-tree nodes) are better: the goal is a small separator, found within a fixed compute budget.

Each trace is a non-empty sequence of valuations of a fixed set of atomic propositions (`a0`, `a1`, ...). Semantics are the standard finite-trace ones: `X[!] f` (strong next) holds at position i if position i+1 exists and `f` holds there; `X f` (weak next) holds if there is no next position or `f` holds there; `F f`, `G f`, `f U g`, `f R g` quantify over the remaining positions of the trace; `!`, `&`, `|`, `->`, `<->` are Boolean. A trace satisfies a formula when the formula holds at its first position.

The instances come from the ten-family LTLf learning benchmark suite released with the paper, all ten families in equal shares: OrderedSequence, Subword, Subset, Hamming and RandomBooleanCombinationsofFactors (dedicated instance generators), and Fixed_Formulas (classic specification patterns), SingleCounter, DoubleCounter, Nim (SYNTCOMP synthesis specifications) and Random_Conjuncts_from_Basis, whose traces are sampled uniformly at random from the language of a formula and from its complement. Parameters follow the released suite: traces of length 16, 32 or 64 (one released combination uses 10), 2 to 17 propositions, and 5, 20 or 100 positive and negative traces (Hamming: one positive trace and negatives a few bits away from it). Propositions are named `a0`, `a1`, ... Many instances admit only separators far beyond the size that exhaustive enumeration of formulas can reach in the budget.

- Visible training instances: `data/train/instances/*.json` (standard benchmark format: `positive_traces`, `negative_traces`, `atomic_propositions`, plus `family` and `parameters` for information), listed in `data/train/manifest.json`. They are drawn from the paper's released suite.
- Hidden test instances: fresh draws from the same generators and parameter ranges (new random seeds, new traces), not available to methods.

---

# Method (reference solver `scripts/solvers/bolt.sh`)

The paper proposes Bolt, a CPU LTLf learner that first enumerates small LTLf formulas exhaustively and then switches to Boolean Set Cover: it searches for conjunctions/disjunctions of the formulas it has already enumerated.

`method/ltlf_bolt.py` is a Python port of the paper's algorithm that follows the authors' Rust implementation (fetched into `method/Bolt/` by `scripts/download.sh`) where the paper leaves details open:

1. **VFB enumeration** (Algorithm 4): bottom-up enumeration by syntactic size with unary `! X X[!] F G` and binary `& | U R`, evaluated as characteristic tables with bitwise operations (Appendix A; one Python integer per formula, bit `i*n+t` = position i of trace t), keeping one formula per distinct table (observational equivalence). It stops at LTL2BS-switch = 8, or earlier at a memory threshold of 500k retained formulas (the paper chooses the switch "based on a memory or time threshold").
2. **Collapse** (Algorithm 1): formulas are reduced to their characteristic vectors (truth value at the first position of each trace); equal vectors are merged, and a formula is dropped when one of the `size-dom = 10` formulas of strictly smaller size with the most correctly classified traces dominates it (fast approximate domination, Section 3.2).
3. **Beam search for Boolean Set Cover** (Algorithm 3): enumerate `|`/`&` combinations by weight, keep the 100 best per weight (most correctly classified traces), skip equivalent and dominated combinations, up to weight D&C-switch = 70.
4. **Divide and conquer** (Algorithm 2 with the paper's two optimisations): when beam search fails (or a subproblem has more than 128 traces, as in the Rust tool), split the larger class alternately, solve the first half, recurse only on the traces it does not already handle, and combine with `|` or `&`.

The Boolean stage runs until it succeeds or 90% of the CPU budget is spent (the paper's tool runs until its 60 s timeout). `scripts/solvers/raw_vfb.sh` is the paper's ablation baseline: the same enumeration without the Boolean Set Cover stage, run until a separator is found or the budget or a 1 GB memory estimate is exhausted.

Departures from the paper: Python instead of compiled Rust (much slower per operation, so the budget is 20 CPU seconds instead of 60 s and the switch is often set by the memory threshold rather than by size 8); the Boolean stage uses `|` and `&` as in the paper's text (the Rust code also tries `<->`); the LTL stage uses the paper's operator set, which is also the evaluated grammar (the Rust code also enumerates `->` and `<->`); beam search scores a whole weight before keeping the best 100 (the Rust code inserts sequentially into a bounded heap).

---

# Evaluation

A method is a **solver**: an executable script `scripts/solvers/<name>.sh`. Every script in that directory is a method on disk and is evaluated; nothing else is.

```
bash scripts/solvers/<name>.sh <instance.json> <answer.json>
```

- `<instance.json>` is one learning task in the standard benchmark format (`positive_traces`, `negative_traces`, `atomic_propositions`, counts). It contains no answer or metadata.
- The solver must write `<answer.json>` = `{"formula": "<LTLf formula>"}` (or `{"formula": null}`) and exit with status 0. Other fields are ignored.
- Budget: **20 CPU seconds per instance**, counted for the solver process and all its children (the value is also in the environment variable `LTLF_CPU_BUDGET_S`). Answers from runs that use more CPU (0.5 s start-up grace), crash, or exceed 4 GB of address space count as unsolved. Only CPU time is budgeted: wall time is not scored, and a 200 s wall-clock limit (10x the budget) only stops hung runs, so machine load cannot decide an instance. Each instance runs in a fresh process with the workspace as working directory; one CPU core.
- Formula syntax (the paper's operator set): propositions of the instance, `true`, `false`, unary `!`, `X`, `X[!]`, `F`, `G`, binary `&` (`&&`), `|` (`||`), `U`, `R`, parentheses. Unary operators bind tightest; then `U`/`R`, `&`, `|`. Parenthesise to be safe. Size = number of syntax-tree nodes (parentheses are free; derived operators such as `F`, `G`, `R`, `X` count as one node). Formulas over 20,000 nodes or 3,000 levels deep count as unsolved.

The evaluator parses every returned formula itself, evaluates it on the instance's traces with its own LTLf semantics, and computes everything from that. Each instance i has a fixed reference size `r_i`, held by the evaluator: the smallest separator found by any learner run recorded when the gym was built (or the instance's generating formula, when it is smaller and some learner solved the instance), or, where no learner found a separator, a lower bound proven by exhaustive enumeration (no smaller separator exists). An answer of size `s_i` is **acceptable** when it is a valid separator and `s_i <= 10 * r_i` (a formula ten times larger than a known separator does not count as solving the task). Then:

| metric | definition | direction | coefficient |
|---|---|---|---:|
| `size_efficiency` (primary) | mean over instances of `min(1, r_i / s_i)` if acceptable, else 0 | higher | 1.0 |
| `solve_rate` | fraction of instances with an acceptable separator | higher | 0.5 |
| `size_ratio_geomean` | geometric mean of `clip(s_i / r_i, 1, 10)`, 10 if not acceptable | lower | 0.5 |

A run that fails everywhere scores 0 / 0 / 10, the worst value of every metric (every solver on disk is entered with these values before it runs, so an interrupted evaluation never leaves it unscored); returning a valid separator never lowers a score compared with returning nothing.  Trace-by-trace constructions (one conjunction of position-indexed literals per positive trace) are always valid but usually far beyond 10x the reference size, so they earn nothing.

Commands:

```bash
bash scripts/evaluate_train.sh   # every solver on the 80 training instances -> scoring/scores_train.json
bash scripts/evaluate.sh         # same, mirrored to scoring/scores.json
bash scripts/evaluate_test.sh    # hidden instances (not available while developing) -> scoring/scores_test.json
python3 eval/train/evaluate.py --only <name> --out outputs/<name>_train.json --runs-dir outputs/<name>_runs
```

Per-instance run records (status, CPU seconds, formula) and scored details are written to the runs directory (`outputs/train_runs/` by default). The train (80 instances) and test (80 instances) slices use the same budget, metrics and interface, and have the same family/parameter mix: 8 instances from each of the ten families.

---

# Reproduction Log

### Iteration 1: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 19m | **GPU**: 0.0h
- **Jobs**: 2 total (1 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:06] - none
- Read the paper and identified the core algorithm: bounded VFB enumeration over LTLf characteristic tables, collapse to first-bit Boolean Set Cover atoms, and beam-search Boolean Set Cover with divide-and-conquer fallback.
- Fetched the upstream Bolt and benchmark repositories for inspection.

### [2026-05-29 02:06] - method_runs
- Implemented a Python reproduction of the paper's algorithm in `method/ltlf_bolt.py`.
- Added a raw bounded VFB ablation baseline and independent evaluation of learned formulas.
- Local smoke run completed on the selected benchmark subset: Bolt solved 4/6 tasks and raw VFB solved 2/6, with all returned formulas validated by `eval/ltlf_eval.py`.

### [2026-05-29 02:25] - core_claim
- Container job `e42a7275-194` ran the packaged reproduction and validation successfully before hitting a stale template command in `scripts/run.sh`.
- On the selected benchmark subset, Bolt solved 6/6 tasks while raw bounded VFB solved 2/6; all returned formulas were independently validated.
- Removed the stale template tail from `scripts/run.sh` and prepared a clean rerun.

### [2026-05-29 02:30] - core_claim
- Clean container job `e68797d5-12f` completed with exit code 0.
- `scripts/reproduce.sh` and `python3 validate.py --compare` passed inside the packaged CPU test environment.

</details>

### Iteration 2: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 2 total (1 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:17] - core_claim
- Implemented Bolt's bounded VFB enumeration with characteristic tables, collapse to first-bit vectors, and Boolean Set Cover beam search.
- Packaged raw bounded VFB as the local ablation baseline.
- Verified a packaged CPU run where Bolt solved 6/6 selected tasks and raw VFB solved 2/6 at the same LTL size bound.
- Independent evaluation validated every returned formula against the finite-trace labels.

### [2026-05-29 02:20] - core_claim
- Audited the restored workspace after milestone reset.
- Fixed the Boolean Set Cover divide-and-conquer fallback so recursive compound formulas retain full vectors across restricted subproblems.
- Removed wall-clock metrics from scored outputs and tightened formula-validity scoring to count any invalid returned formula as a failure.
- Reran `bash scripts/evaluate.sh` and `python3 validate.py --compare`; all checks passed.

</details>

### Iteration 3: gpt-5.5
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 12m | **GPU**: 0.0h
- **Jobs**: 3 total (2 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

</details>

### Iteration 4: gpt-5.5 (designer_stage_1)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 3 total (2 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

</details>

### Iteration 5: gpt-5.5 (designer_stage_2)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 4m | **GPU**: 0.0h
- **Jobs**: 3 total (2 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

</details>

### Iteration 6: gpt-5.5 (designer_stage_3)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 1m | **GPU**: 0.0h
- **Jobs**: 4 total (3 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

</details>

### Iteration 7: gpt-5.5 (packager)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 1m | **GPU**: 0.0h
- **Jobs**: 4 total (3 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

</details>

### Iteration 8: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 6m | **GPU**: 0.0h
- **Jobs**: 4 total (3 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

### [2026-05-29 02:53] - core_claim
- Completed scoring-contract audit.
- Updated the primary evaluator to report coverage, baseline-miss solve rate, and raw VFB baseline metrics alongside Bolt.
- Prepared a CPU test job to rerun download/preparation, baseline, Bolt, scoring, and validation end to end.

### [2026-05-29 02:56] - core_claim
- Final verification passed.
- Cleaned method-agnostic documentation and set method-internal diagnostic scoring weight to zero.
- Confirmed `python3 validate.py --compare` passes and download URLs resolve.

</details>

### Iteration 9: gpt-5.5 (verifier)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 5m | **GPU**: 0.0h
- **Jobs**: 4 total (3 completed, 1 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

### [2026-05-29 02:53] - core_claim
- Completed scoring-contract audit.
- Updated the primary evaluator to report coverage, baseline-miss solve rate, and raw VFB baseline metrics alongside Bolt.
- Prepared a CPU test job to rerun download/preparation, baseline, Bolt, scoring, and validation end to end.

### [2026-05-29 02:56] - core_claim
- Final verification passed.
- Cleaned method-agnostic documentation and set method-internal diagnostic scoring weight to zero.
- Confirmed `python3 validate.py --compare` passes and download URLs resolve.

### [2026-05-29 03:00] - core_claim
- Re-audited the packaged code and docs.
- Confirmed the runnable method is the paper's symbolic VFB-to-Boolean-Set-Cover pipeline at reduced scale, not a learned surrogate.
- Clarified that the packaged method runs the compact Python implementation while retaining the upstream Bolt fetch for provenance.

### [2026-05-29 03:02] - core_claim
- Completed final verification for gym readiness.
- Fixed a neutral scoring fallback for formula-size comparisons when no common solved tasks exist.
- Re-ran main, train, and test evaluators plus `python3 validate.py --compare`; all checks pass.

</details>

### Iteration 10: gpt-6.1-sol (redteam)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 10m | **GPU**: 0.0h

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

### [2026-05-29 02:53] - core_claim
- Completed scoring-contract audit.
- Updated the primary evaluator to report coverage, baseline-miss solve rate, and raw VFB baseline metrics alongside Bolt.
- Prepared a CPU test job to rerun download/preparation, baseline, Bolt, scoring, and validation end to end.

### [2026-05-29 02:56] - core_claim
- Final verification passed.
- Cleaned method-agnostic documentation and set method-internal diagnostic scoring weight to zero.
- Confirmed `python3 validate.py --compare` passes and download URLs resolve.

### [2026-05-29 03:00] - core_claim
- Re-audited the packaged code and docs.
- Confirmed the runnable method is the paper's symbolic VFB-to-Boolean-Set-Cover pipeline at reduced scale, not a learned surrogate.
- Clarified that the packaged method runs the compact Python implementation while retaining the upstream Bolt fetch for provenance.

### [2026-05-29 03:02] - core_claim
- Completed final verification for gym readiness.
- Fixed a neutral scoring fallback for formula-size comparisons when no common solved tasks exist.
- Re-ran main, train, and test evaluators plus `python3 validate.py --compare`; all checks pass.

</details>

### Iteration 11: claude-opus-5-5 (hardener)
- **Milestone**: `core_claim` | **Status**: done
- **Working time**: 49m | **GPU**: 0.0h
- **Jobs**: 2 total (2 completed, 0 failed)

<details>
<summary>Progress Log</summary>

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:29] - core_claim
- Audited the previous `core_claim` after reset to `method_runs`.
- Replaced the default generated suite with 10 tracked instances extracted from the paper's released benchmark zip.
- Fixed the formula-size scoring mismatch and a divide-and-conquer recursion bug exposed by released benchmark instances.
- Local validation passes: Bolt solves 8/10 released-subset tasks, raw bounded VFB solves 3/10, and all returned formulas independently separate positive from negative traces.

### [2026-05-29 02:34] - core_claim
- Packaged CPU verification job `0b9e9790-461` exited 0 through `scripts/run.sh`.
- Container run passed `python3 validate.py --compare` with Bolt solve rate 0.80, valid returned formulas, formula-size ratio 1.00, and a 0.50 solve-rate gain over the raw VFB ablation.

### [2026-05-29 02:53] - core_claim
- Completed scoring-contract audit.
- Updated the primary evaluator to report coverage, baseline-miss solve rate, and raw VFB baseline metrics alongside Bolt.
- Prepared a CPU test job to rerun download/preparation, baseline, Bolt, scoring, and validation end to end.

### [2026-05-29 02:56] - core_claim
- Final verification passed.
- Cleaned method-agnostic documentation and set method-internal diagnostic scoring weight to zero.
- Confirmed `python3 validate.py --compare` passes and download URLs resolve.

### [2026-05-29 03:00] - core_claim
- Re-audited the packaged code and docs.
- Confirmed the runnable method is the paper's symbolic VFB-to-Boolean-Set-Cover pipeline at reduced scale, not a learned surrogate.
- Clarified that the packaged method runs the compact Python implementation while retaining the upstream Bolt fetch for provenance.

### [2026-05-29 03:02] - core_claim
- Completed final verification for gym readiness.
- Fixed a neutral scoring fallback for formula-size comparisons when no common solved tasks exist.
- Re-ran main, train, and test evaluators plus `python3 validate.py --compare`; all checks pass.

### [2026-11-12] - core_claim
- Hardening: rebuilt the evaluation as budgeted solver runs (20 CPU s per instance) on 40 hidden instances freshly drawn from the paper's generators; scores computed only from the parsed formula against fixed best-known sizes.
- Restored the paper's Bolt procedure and settings (switch 8, size-dom 10, beam 100, D&C-switch 70) in a faithful Python port.
- Hidden test: Bolt 0.752 size_efficiency / 0.90 solve rate vs raw VFB 0.40 / 0.40; anytime portfolio variant +0.057 (paired CI excludes 0); all redteam shortcuts closed or reduced (HARDENING.md).

</details>


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
