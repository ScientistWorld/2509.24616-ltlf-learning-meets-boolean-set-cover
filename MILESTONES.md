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

### [2026-05-29 03:02] - core_claim
- Completed final verification for gym readiness.
- Fixed a neutral scoring fallback for formula-size comparisons when no common solved tasks exist.
- Re-ran main, train, and test evaluators plus `python3 validate.py --compare`; all checks pass.

### [2026-11-12] - core_claim
- Hardening: rebuilt the evaluation as budgeted solver runs (20 CPU s per instance) on 40 hidden instances freshly drawn from the paper's generators; scores computed only from the parsed formula against fixed best-known sizes.
- Restored the paper's Bolt procedure and settings (switch 8, size-dom 10, beam 100, D&C-switch 70) in a faithful Python port.
- Hidden test: Bolt 0.752 size_efficiency / 0.90 solve rate vs raw VFB 0.40 / 0.40; anytime portfolio variant +0.057 (paired CI excludes 0); all redteam shortcuts closed or reduced (HARDENING.md).

### [2026-11-14] - core_claim
- Second hardening pass (REVIEW.md): CPU-only budget with a 200 s wall safety net; worst scores pre-written for every solver; reference sizes unreadable during hidden runs.
- All ten benchmark families: 80 train (release) and 80 hidden (fresh draws) instances; the five Spot-based families sampled with an exact Spot-free uniform sampler validated against the release.
- Hidden test: Bolt 0.845 size_efficiency / 0.95 solve rate vs raw VFB 0.488 / 0.488; Bolt + directed-pattern atoms +0.048 at the same CPU (paired CI excludes 0); repeat spread 0 (HARDENING.md).

## Stop Justification
- Completed at milestone `core_claim`.
