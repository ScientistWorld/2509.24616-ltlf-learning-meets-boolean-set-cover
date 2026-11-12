#!/usr/bin/env python3
"""Better-variant experiment: anytime use of the per-instance budget.

1. Run the reference Bolt configuration (it stops at its first separator).
2. With the CPU time left, run Bolt with a larger LTL2BS-switch / memory
   threshold and a wider beam (the paper's trade-off: more enumerated atoms give
   smaller Boolean combinations), bounded by the remaining budget.
3. Keep the smaller formula and greedily delete redundant subformulas.
Usage: portfolio.py <instance.json> <answer.json>
"""

import json
import os
import resource
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "method"))
import ltlf_bolt as B  # noqa: E402

BOLT = [sys.executable, str(ROOT / "method" / "ltlf_bolt.py"), "--mode", "bolt", "--size-dom", "10", "--dc-switch", "70"]
REFERENCE = ["--ltl-switch", "8", "--beam-width", "100", "--max-ltl-formulas", "500000"]
LARGER = ["--ltl-switch", "9", "--beam-width", "150", "--max-ltl-formulas", "2000000", "--ltl-time-fraction", "0.45"]


def used() -> float:
    c = resource.getrusage(resource.RUSAGE_CHILDREN)
    s = resource.getrusage(resource.RUSAGE_SELF)
    return c.ru_utime + c.ru_stime + s.ru_utime + s.ru_stime


def run(extra: list[str], task: str, budget: float, tmp: str, tag: str):
    out = os.path.join(tmp, tag + ".json")
    subprocess.run(BOLT + extra + ["--budget", f"{budget:.2f}", "--instance", task, "--out", out], check=False)
    try:
        return json.load(open(out)).get("formula")
    except (OSError, ValueError):
        return None


def main() -> None:
    task, answer = sys.argv[1], sys.argv[2]
    budget = float(os.environ.get("LTLF_CPU_BUDGET_S", "20"))
    tmp = tempfile.mkdtemp()
    cands = [run(REFERENCE, task, budget - 0.8, tmp, "ref")]
    left = budget - used() - 1.5
    if left > 3:
        cands.append(run(LARGER, task, left, tmp, "larger"))
    cands = [f for f in cands if f]
    best = min(cands, key=lambda f: B._size(B._parse(f))) if cands else None
    left = budget - used() - 0.7
    if best and left > 0.3:
        tr = B.Traces(json.load(open(task)))
        best = B.simplify(best, tr, time.process_time() + left)
    json.dump({"formula": best}, open(answer, "w"))


if __name__ == "__main__":
    main()
