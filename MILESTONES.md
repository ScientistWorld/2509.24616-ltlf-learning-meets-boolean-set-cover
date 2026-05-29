# Reproduction Milestones

**Current: core_claim**

## Progress Log

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

## Stop Justification
- Completed at milestone `core_claim` on a compact CPU benchmark subset. Higher milestones would require scaling to more of the full 15,595-task benchmark suite.
