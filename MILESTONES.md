# Reproduction Milestones

**Current: method_runs**

## Progress Log

### [2026-05-29 02:06] - none
- Read the paper and identified the core algorithm: bounded VFB enumeration over LTLf characteristic tables, collapse to first-bit Boolean Set Cover atoms, and beam-search Boolean Set Cover with divide-and-conquer fallback.
- Fetched the upstream Bolt and benchmark repositories for inspection.

### [2026-05-29 02:06] - method_runs
- Implemented a Python reproduction of the paper's algorithm in `method/ltlf_bolt.py`.
- Added a raw bounded VFB ablation baseline and independent evaluation of learned formulas.
- Local smoke run completed on the selected benchmark subset: Bolt solved 4/6 tasks and raw VFB solved 2/6, with all returned formulas validated by `eval/ltlf_eval.py`.
