#!/usr/bin/env python3
"""Fix best_known_size of every hidden instance (run once; the value is then frozen).

best_known_size = smallest syntax-tree size among (a) the generating formula of
the instance generator and (b) every valid separator returned by a learner run
(per-instance run records *.jsonl, or formula-free details.json files of earlier
scored runs).  Trivial constructions that do not learn temporal structure
(TRIVIAL below) are not counted, just as the paper's best-known sizes come from
learners.  Where no learner found a separator, the value is the lower bound
proven by exhaustive enumeration (lower_bounds.json: no separator of smaller
size exists in the evaluated grammar).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import INSTANCES, check_formula, encoded, load_instances  # noqa: E402

TRIVIAL = {"literal_cover", "null_answer", "crash", "forged_fields"}
LOWER_BOUNDS = HERE / "lower_bounds.json"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", action="append", default=[])
    ap.add_argument("--details", action="append", default=[])
    args = ap.parse_args()
    sys.setrecursionlimit(20000)
    instances, payload = load_instances()
    by_id = {inst["id"]: inst for inst in instances}
    best: dict[str, tuple[int, str]] = {}

    def offer(iid: str, size: int, source: str) -> None:
        if iid in by_id and (iid not in best or size < best[iid][0]):
            best[iid] = (size, source)

    for rec in payload["instances"]:
        if rec.get("generating_formula_size"):
            offer(rec["id"], rec["generating_formula_size"], "generating_formula")
    for runs_dir in args.runs_dir:
        for path in sorted(Path(runs_dir).glob("*.jsonl")):
            if path.stem in TRIVIAL:
                continue
            for line in path.read_text().splitlines():
                try:
                    run = json.loads(line)
                except ValueError:
                    continue
                inst = by_id.get(run.get("instance"))
                if inst is None:
                    continue
                ok, size, _ = check_formula(run.get("formula"), inst, encoded(inst))
                if ok:
                    offer(inst["id"], size, path.stem)
    for details in args.details:
        for method, rows in json.loads(Path(details).read_text()).items():
            if method in TRIVIAL:
                continue
            for row in rows:
                if row.get("valid") and row.get("size"):
                    offer(row["instance"], row["size"], method)
    bounds = json.loads(LOWER_BOUNDS.read_text()) if LOWER_BOUNDS.exists() else {}
    for iid in by_id:
        if iid not in best and iid in bounds:
            best[iid] = (bounds[iid]["lower_bound"], "exhaustive_lower_bound")
    missing = [i for i in by_id if i not in best]
    if missing:
        raise SystemExit(f"no learner separator and no lower bound for {missing}")
    for rec in payload["instances"]:
        rec["best_known_size"], rec["best_known_source"] = best[rec["id"]]
    INSTANCES.write_text(json.dumps(payload, separators=(",", ":")))
    sources: dict[str, int] = {}
    for _, src in best.values():
        sources[src] = sources.get(src, 0) + 1
    print("best-known sizes set; sources:", sources)


if __name__ == "__main__":
    main()
