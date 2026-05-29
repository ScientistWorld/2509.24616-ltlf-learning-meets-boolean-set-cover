# Checklist

- [x] Read paper and identify core method.
- [x] Inspect upstream Bolt and benchmark repositories.
- [x] Implement bounded VFB characteristic-table enumeration.
- [x] Implement collapse to Boolean Set Cover atoms.
- [x] Implement beam-search Boolean Set Cover.
- [x] Implement raw VFB ablation baseline.
- [x] Implement independent formula evaluator.
- [x] Add selected benchmark generator.
- [x] Add `scripts/download.sh`, `scripts/baseline.sh`, `scripts/method.sh`, `scripts/evaluate.sh`, and `scripts/reproduce.sh`.
- [x] Add `scoring/reference.json`.
- [x] Run local smoke test and `python3 validate.py --compare`.
- [ ] Run packaged CPU job through `action.yaml`.
- [ ] Promote milestone to `core_claim` after job results confirm the local smoke result.
