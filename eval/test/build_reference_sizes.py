#!/usr/bin/env python3
"""Fix best_known_size of every hidden instance (run once after the reference runs).

best_known_size = smallest syntax-tree size among (a) the generating formula
of the instance generator and (b) every valid separator returned by any solver
run stored in the given run directories (reference, baselines, variants).
The value is then frozen in eval/test/instances.json; it is the denominator of
the size metrics, like the paper's "shortest formula found by all our runs".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import INSTANCES, check_formula, encoded, load_instances  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", action="append", required=True)
    args = ap.parse_args()
    sys.setrecursionlimit(20000)
    instances, payload = load_instances()
    by_id = {inst["id"]: inst for inst in instances}
    best: dict[str, tuple[int, str]] = {}
    for rec in payload["instances"]:
        if rec.get("generating_formula_size"):
            best[rec["id"]] = (rec["generating_formula_size"], "generating_formula")
    for runs_dir in args.runs_dir:
        for path in sorted(Path(runs_dir).glob("*.jsonl")):
            for line in path.read_text().splitlines():
                try:
                    run = json.loads(line)
                except ValueError:
                    continue
                inst = by_id.get(run.get("instance"))
                if inst is None:
                    continue
                ok, size, _ = check_formula(run.get("formula"), inst, encoded(inst))
                if ok and (inst["id"] not in best or size < best[inst["id"]][0]):
                    best[inst["id"]] = (size, path.stem)
    missing = [i for i in by_id if i not in best]
    if missing:
        raise SystemExit(f"no known separator for {missing}")
    for rec in payload["instances"]:
        rec["best_known_size"], rec["best_known_source"] = best[rec["id"]]
    INSTANCES.write_text(json.dumps(payload, separators=(",", ":")))
    sources: dict[str, int] = {}
    for size, src in best.values():
        sources[src] = sources.get(src, 0) + 1
    print("best-known sizes set; sources:", sources)


if __name__ == "__main__":
    main()
