#!/usr/bin/env python3
"""Exhaustive-enumeration lower bounds for instances without a learner separator.

Raw VFB enumerates every LTLf formula of the evaluated grammar by size, keeping
one representative per characteristic table (observational equivalence is
complete), and checks each against the target.  If it finishes size k without a
separator, no separator of size <= k exists, so k + 1 is a lower bound; if it
finds one, its size is the exact minimum.  Writes eval/<slice>/lower_bounds.json.

Usage: lower_bounds.py --slice test|train [--details F ...] [--runs-dir D ...] [--budget S]
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TRIVIAL = {"literal_cover", "null_answer", "crash", "forged_fields"}


def load_eval(slice_name: str):
    spec = importlib.util.spec_from_file_location(f"eval_{slice_name}", ROOT / "eval" / slice_name / "evaluate.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--slice", choices=["test", "train"], required=True)
    ap.add_argument("--details", action="append", default=[])
    ap.add_argument("--runs-dir", action="append", default=[])
    ap.add_argument("--budget", type=float, default=150.0)
    args = ap.parse_args()
    sys.setrecursionlimit(20000)
    E = load_eval(args.slice)
    instances, payload = E.load_instances()
    if args.slice == "test":
        gen = {r["id"]: r.get("generating_formula_size") for r in payload["instances"]}
    else:
        sizes = json.loads((ROOT / "eval" / "train" / "reference_sizes.json").read_text())
        gen = {i: v.get("generating_formula_size") for i, v in sizes.items()}
    solved = {i for i, g in gen.items() if g}
    for details in args.details:
        for method, rows in json.loads(Path(details).read_text()).items():
            if method not in TRIVIAL:
                solved |= {r["instance"] for r in rows if r.get("valid")}
    by_id = {inst["id"]: inst for inst in instances}
    for runs_dir in args.runs_dir:
        for path in Path(runs_dir).glob("*.jsonl"):
            if path.stem in TRIVIAL:
                continue
            for line in path.read_text().splitlines():
                run = json.loads(line)
                inst = by_id.get(run.get("instance"))
                if inst and E.check_formula(run.get("formula"), inst, E.encoded(inst))[0]:
                    solved.add(inst["id"])
    out = {}
    for inst in instances:
        if inst["id"] in solved:
            continue
        with tempfile.TemporaryDirectory() as tmp:
            task, ans = Path(tmp) / "task.json", Path(tmp) / "answer.json"
            task.write_text(json.dumps(E.solver_input(inst)))
            subprocess.run([sys.executable, str(ROOT / "method" / "ltlf_bolt.py"), "--mode", "vfb",
                            "--budget", str(args.budget), "--max-memory-mb", "2000",
                            "--instance", str(task), "--out", str(ans)], check=False)
            try:
                res = json.loads(ans.read_text())
            except (OSError, ValueError):
                res = {"formula": None, "info": {}}
        info = res.get("info", {})
        ok, size, _ = E.check_formula(res.get("formula"), inst, E.encoded(inst))
        if ok:
            out[inst["id"]] = {"lower_bound": size, "exact": True, "vfb": info}
        else:
            out[inst["id"]] = {"lower_bound": int(info.get("ltl_completed_size", 1)) + 1, "exact": False, "vfb": info}
        print(args.slice, inst["id"], out[inst["id"]]["lower_bound"], info.get("ltl_stopped_by"), flush=True)
    (ROOT / "eval" / args.slice / "lower_bounds.json").write_text(json.dumps(out, indent=1) + "\n")


if __name__ == "__main__":
    main()
