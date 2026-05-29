# Progress

## What Works

- `method/ltlf_bolt.py` runs the paper's actual two-stage method at small scale:
  bounded VFB LTLf enumeration using characteristic tables, collapse to first-bit vectors, and Boolean Set Cover beam search.
- `scripts/baseline.sh` runs raw bounded VFB without the Boolean Set Cover stage.
- `scripts/method.sh` runs Bolt on the same selected instances and then calls `scripts/evaluate.sh`.
- `scripts/evaluate.sh` reads method artifacts in `outputs/` and independently parses/evaluates formulas against the traces.

## Results Achieved

Local validation on 2026-05-29:

- `python3 validate.py --compare` passes all scoring and structure checks.
- Current artifacts show Bolt solving 6/6 selected tasks and raw bounded VFB solving 2/6.
- The four additional Bolt solves all come from the Boolean Set Cover stage after bounded VFB at the same LTL switch does not find a separator.

Clean container smoke job `e68797d5-12f` on 2026-05-29:

- Bolt: solved 6/6 selected tasks.
- Raw bounded VFB: solved 2/6 selected tasks.
- All returned formulas validated as separating all positive traces from all negative traces.
- Bolt solved four additional selected tasks through Boolean Set Cover after raw VFB at the same LTL size bound failed.

The selected run supports the core claim at reduced scale: switching from full LTLf enumeration to Boolean Set Cover over previously enumerated formulas solves harder tasks while preserving formula validity and keeping formula sizes close on common solved tasks.

## Deviations From Paper

- The full paper benchmark suite has 15,595 tasks. This workspace uses six small generated tasks spanning Subset, Subword, OrderedSequence, Hamming-like, and random Boolean factor styles so the reproduction can run quickly as a CPU job.
- The paper implementation is Rust and uses `LTL2BS-switch = 8`, `beam-width = 100`, and `D&C-switch = 70`. This reproduction defaults to `LTL_SWITCH=3`, `BEAM_WIDTH=30`, and `MAX_BOOL_WEIGHT=25` to fit a small CPU smoke job.
- The baseline in this workspace is raw bounded VFB, matching the paper's ablation question. The exact Scarlet and GPU baselines are not reimplemented.
- Wall-clock speed is reported only in raw run artifacts for diagnosis. It is excluded from `scoring/reference.json` and `scoring/scores.json` because hardware-dependent speed is not a stable scoring target.

## What Remains

- A CPU-only packaged verification job has been submitted to rerun `scripts/reproduce.sh` and `python3 validate.py --compare` from `scripts/run.sh`.
- To go beyond `core_claim`, scale the selected suite or use the optional upstream benchmark release from `scripts/download.sh`.

## Issues Encountered

- The first local smoke run showed that timeout checks needed to occur inside enumeration and Boolean Set Cover loops, not only between size layers. The implementation now checks deadlines during inner loops.
- Job `e42a7275-194` completed reproduction and validation successfully, then exited with code 2 because the original template tail in `scripts/run.sh` still called missing `method/train.py`. That stale command has been removed.
- Job `e68797d5-12f` reran the packaged environment cleanly with exit code 0.
- Validation initially rejected `solved_count` as the primary metric because this reproduction uses a selected six-instance subset while the paper reports full-suite counts. The primary metric is now `solve_rate`, and the local raw VFB ablation is used only for Bolt constraint metrics rather than being labeled as the paper's Scarlet baseline.
- A continuation audit found that the divide-and-conquer fallback could not combine recursive compound Boolean formulas because it reconstructed full vectors through exact atom text lookup. The fallback now carries full vectors through restricted subproblems and compound Boolean combinations.
- The evaluator now treats any non-empty invalid returned formula as a validity failure even if a method marks the row as unsolved.
