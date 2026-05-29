# Progress

## What Works

- `method/ltlf_bolt.py` runs the paper's actual two-stage method at small scale:
  bounded VFB LTLf enumeration using characteristic tables, collapse to first-bit vectors, and Boolean Set Cover beam search.
- `scripts/baseline.sh` runs raw bounded VFB without the Boolean Set Cover stage.
- `scripts/method.sh` runs Bolt on the same selected instances and then calls `scripts/evaluate.sh`.
- `scripts/evaluate.sh` reads method artifacts in `outputs/` and independently parses/evaluates formulas against the traces.

## Results Achieved

Local smoke run on 2026-05-29:

- Bolt: solved 4/6 selected tasks.
- Raw bounded VFB: solved 2/6 selected tasks.
- All returned formulas validated as separating all positive traces from all negative traces.
- Bolt solved the two selected Subset tasks through Boolean Set Cover after raw VFB at the same LTL size bound failed.

The selected run supports the core claim at reduced scale: switching from full LTLf enumeration to Boolean Set Cover over previously enumerated formulas solves harder tasks while preserving formula validity and keeping formula sizes close on common solved tasks.

## Deviations From Paper

- The full paper benchmark suite has 15,595 tasks. This workspace uses six small generated tasks spanning Subset, Subword, OrderedSequence, Hamming-like, and random Boolean factor styles so the reproduction can run quickly as a CPU job.
- The paper implementation is Rust and uses `LTL2BS-switch = 8`, `beam-width = 100`, and `D&C-switch = 70`. This reproduction defaults to `LTL_SWITCH=3`, `BEAM_WIDTH=30`, and `MAX_BOOL_WEIGHT=25` to fit a small CPU smoke job.
- The baseline in this workspace is raw bounded VFB, matching the paper's ablation question. The exact Scarlet and GPU baselines are not reimplemented.
- Wall-clock speed is reported for run diagnosis, but the core gym target is solved count and formula validity because hardware-dependent speed is not a stable scoring target.

## What Remains

- Run the packaged CPU job in the target container and record its scores.
- To go beyond `core_claim`, scale the selected suite or use the optional upstream benchmark release from `scripts/download.sh`.

## Issues Encountered

- The first local smoke run showed that timeout checks needed to occur inside enumeration and Boolean Set Cover loops, not only between size layers. The implementation now checks deadlines during inner loops.
