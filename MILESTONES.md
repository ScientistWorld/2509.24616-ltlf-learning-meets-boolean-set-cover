# Reproduction Milestones

**Current: core_claim**

## Progress Log

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
