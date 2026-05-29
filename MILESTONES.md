# Reproduction Milestones

**Current: core_claim**

## Progress Log

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

## Stop Justification
- Completed at milestone `core_claim`.
