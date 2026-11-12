# Audit plan and exposure boundary

The reference implementation is copied verbatim from the improve-mode-visible
`method/ltlf_bolt.py`. The shared runner generates fresh reference outputs using
that implementation, and reuses those generated artifacts for shortcut checks.
Candidates use all visible manifest instances, never the hidden split list.
The only imported evaluator is `eval/train/evaluate.py`, which the future agent
receives. The restored hidden evaluator is only invoked by its shell entry point.

Each scenario has its own `run.sh`; `redteam/audit.py` contains the shared
installation, execution, scoring and restoration machinery and the candidate
implementations. A scenario saves both input artifacts and newly written train
and test scores. `execution.json` records process exits and elapsed times.
The runner snapshots and restores every modified file outside `redteam/`, even
when a scenario fails. The temporary submission runner is restored at completion.

Three reference interpreter runs use hash seeds 0, 1, and 2. This deterministic
algorithm has no stochastic training or seed parameter, so these measure actual
repeat spread rather than inventing a stochastic training procedure.

Scientific checks include deeper search, the paper's search parameters on the
small subset, removing the Boolean stage, minimal search, raw exhaustive VFB,
and an exhaustive time-index-literal subset DP. Metadata copying, baseline
padding or deletion, trace mutation, forged scores/flags, null/empty outputs,
method filtering, and stale artifact replay are explicitly labeled shortcuts.

All computation runs as a CPU job. No package or data download is necessary.
