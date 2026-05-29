# Reproduction Milestones

**Current: core_claim**

## Progress Log

### [2026-05-29 02:21] - core_claim
- Implemented Bolt's bounded VFB enumeration, characteristic-table observational equivalence, collapse to first-bit vectors, and Boolean Set Cover beam search/divide-and-conquer path.
- Packaged a selected finite-trace benchmark suite and raw bounded VFB ablation baseline.
- Validated reproduced results: Bolt solves 6/6 selected tasks, raw bounded VFB solves 2/6 at the same LTL size bound, and all returned formulas independently separate positive from negative traces.

## Stop Justification
- Not stopped yet; submitting a CPU-only packaged verification job before finalizing.
