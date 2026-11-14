# Progress

## Current state (iteration 12, second hardening pass)

- `method/ltlf_bolt.py`: Python port of Bolt at the paper's settings (LTL2BS-switch 8 with the paper's memory threshold, size-dom 10, beam width 100, D&C-switch 70), following the authors' Rust code. `--mode vfb` is the raw VFB ablation.
- Methods are solver scripts in `scripts/solvers/` (`bolt` reference, `raw_vfb` baseline). `eval/train/evaluate.py` and `eval/test/evaluate.py` run every solver per instance under 20 CPU seconds (CPU only; 200 s wall safety net) and score the parsed formulas.
- Data: all ten benchmark families of the paper. 80 training instances from the released suite (`data/train/`), 80 hidden test instances freshly drawn from the paper's generators (`eval/test/instances.json`; formula-based families sampled with `eval/test/trace_sampler.py`).
- Hidden test: bolt 0.845 size_efficiency / 0.950 solve_rate / 1.339 size ratio; raw VFB 0.488 / 0.488 / 3.255. Train: bolt 0.892 / 0.975 / 1.209; raw VFB 0.588 / 0.588 / 2.585. Repeat spread 0.
- Better method at the same CPU: Bolt + directed-pattern atoms (`scripts/hardening/bolt_patterns.py`), +0.048 on the hidden test (paired CI excludes 0). Details, shortcuts and before/after scores: `HARDENING.md`, `notes/hardening/`.

## Deviations from the paper

- Python instead of Rust; 20 CPU-second budget instead of 60 s; memory threshold usually sets the switch below size 8.
- The paper's Spot-based trace sampler is replaced by an equivalent exact uniform sampler; no Scarlet or GPU comparison.
- Best-known sizes from this gym's learner runs, with exhaustive lower bounds where no learner finds a separator.

## History

Iterations 1-10 built and audited a 10-instance version scored from pre-generated outputs; REDTEAM.md (iteration 10) documents why it was replaced. Iteration 11 rebuilt it as a budgeted hidden-instance evaluation on five families; iteration 12 addressed REVIEW.md (CPU-only budget, ten families, a better method at the same budget).
