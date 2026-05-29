# Overview

`LTLf Learning Meets Boolean Set Cover` introduces Bolt, an LTLf learner that avoids exhaustive growth of temporal formulas by switching from bounded LTLf enumeration to Boolean Set Cover over already discovered formulas.

This workspace reproduces the core claim at small CPU scale on a tracked subset of the paper's released benchmarks: the Boolean Set Cover stage solves selected tasks that raw bounded VFB cannot solve at the same LTL size bound, while all learned formulas are independently validated.

---

# Problem

Given two disjoint finite sets of finite traces, positive traces `P` and negative traces `N`, learn an LTLf formula that accepts every trace in `P` and rejects every trace in `N`.

Each trace is a non-empty sequence of valuations over a fixed finite set of atomic propositions. The learned formula is judged by whether its LTLf semantics over finite traces separates the two trace sets. Smaller formulas are preferred when multiple valid separators exist.

This workspace evaluates a small tracked subset extracted from the paper's released benchmark suite: JSON files containing positive traces, negative traces, atomic proposition names, and metadata.

---

# Method

The paper proposes Bolt, a CPU LTLf learner that first runs bounded VFB enumeration and then switches to Boolean Set Cover.

The VFB stage enumerates LTLf formulas by syntactic size. Each formula is evaluated on every suffix of every input trace, producing a characteristic table. Formulas with identical characteristic tables are observationally equivalent, so only one representative is retained.

If no separator is found by the LTL size bound, Bolt collapses each retained formula to the vector of first-position truth values over the traces. Boolean combinations of these retained formulas are then searched with only conjunction and disjunction. This Boolean Set Cover stage uses formula weight, observational equivalence on vectors, score based on correctly classified traces, approximate domination, beam search, and a divide-and-conquer fallback.

This reproduction implements the same computational steps in Python for a reduced CPU benchmark suite. The upstream Rust Bolt repository is fetched for inspection and provenance, but the packaged scripts run the compact Python implementation so the core algorithm is easy to audit. It also implements raw bounded VFB as the local ablation baseline.

---

# Evaluation

Evaluation reads result artifacts from `outputs/` and does not import from `method/`.

For each returned formula, the evaluator parses the LTLf expression and evaluates it on all positive and negative traces. A formula is valid only if it accepts every positive trace and rejects every negative trace.

The main benefit metric is solve rate on the selected released benchmark subset. Constraint metrics include returned-formula validity, evaluation coverage, formula-size ratio on tasks solved by both a submitted method and the provided reference baseline, and solve-rate delta over that baseline. If there are no common solved tasks for a size comparison, the ratio is reported as neutral `1.0` rather than giving a size bonus. Diagnostic metadata may appear in raw run artifacts, but method-internal diagnostics and wall-clock runtimes are not ranking targets.

A reusable method output is a JSON file under `outputs/` with a top-level `results` list. Each row should include at least:

- `instance`: path to the benchmark JSON file.
- `method`: method identifier.
- `formula`: returned LTLf formula string, or `null` if no separator was found.

Additional fields are allowed and ignored unless a metric explicitly uses them.

Run:

```bash
bash scripts/reproduce.sh
python3 validate.py --compare
```

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


---

# Reproduction Milestones

**Current: core_claim**

## Stop Justification
- Completed at milestone `core_claim`.
