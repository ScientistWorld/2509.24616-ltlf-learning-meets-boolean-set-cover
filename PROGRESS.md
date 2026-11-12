# Progress

## Current state (iteration 11, hardening)

- `method/ltlf_bolt.py`: Python port of Bolt at the paper's settings (LTL2BS-switch 8 with the paper's memory threshold, size-dom 10, beam width 100, D&C-switch 70), following the authors' Rust code: bitwise characteristic tables, observational equivalence, collapse with top-k approximate domination, beam search over |/&, non-overlapping divide and conquer. `--mode vfb` is the raw VFB ablation.
- Methods are solver scripts in `scripts/solvers/` (`bolt` reference, `raw_vfb` baseline). `eval/train/evaluate.py` and `eval/test/evaluate.py` run every solver per instance under 20 CPU seconds and score the parsed formulas.
- Data: 40 training instances from the paper's released suite (`data/train/`), 40 hidden test instances freshly drawn from the paper's generators (`eval/test/instances.json`).
- Hidden test: bolt 0.752 size_efficiency / 0.900 solve_rate / 1.600 size ratio; raw VFB 0.400 / 0.400 / 3.981. Train: bolt 0.840 / 0.950 / 1.344; raw VFB 0.525 / 0.525 / 2.985. Repeat spread 0.
- Hardening experiments, shortcuts and before/after scores: `HARDENING.md`, `notes/hardening/`.

## Deviations from the paper

- Python instead of Rust; 20 CPU-second budget instead of 60 s; memory threshold usually sets the switch below size 8.
- 5 of the 10 benchmark families (those with pure-Python generators); no Scarlet or GPU comparison.
- Best-known sizes from generating formulas and this iteration's learner runs, with exhaustive lower bounds where no learner finds a separator.

## History

Iterations 1-10 built and audited a 10-instance version scored from pre-generated outputs; REDTEAM.md (iteration 10) documents why it was replaced.
