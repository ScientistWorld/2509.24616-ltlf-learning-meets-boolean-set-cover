#!/usr/bin/env python3
"""Fix best_known_size of every training instance (eval/train/reference_sizes.json).

best_known_size = smallest syntax-tree size among (a) the generating formula
recorded in the paper's release for that instance and (b) every valid separator
returned by any solver run stored in the given run directories.
"""

from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import REFERENCE_SIZES, WORKSPACE, check_formula, encoded, load_instances, node_count, parse  # noqa: E402

SOURCE_ZIP = WORKSPACE / "data" / "downloads" / "benchmarks.zip"


def balanced(formula: str) -> str:
    """The upstream OrderedSequence writer emits one unmatched trailing ')'."""
    while formula.count(")") > formula.count("(") and formula.rstrip().endswith(")"):
        formula = formula.rstrip()[:-1]
    return formula


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", action="append", required=True)
    args = ap.parse_args()
    sys.setrecursionlimit(20000)
    instances, manifest = load_instances()
    by_id = {inst["id"]: inst for inst in instances}
    best: dict[str, tuple[int, str]] = {}
    gen_sizes: dict[str, int | None] = {}
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        for rec in manifest["instances"]:
            data = json.loads(archive.read(rec["source_file"]))
            gen = data.get("generating_formula") or ""
            gen_sizes[rec["id"]] = None
            if gen:
                inst = by_id[rec["id"]]
                node = parse(balanced(gen), set(inst["atomic_propositions"]))
                if encoded(inst).separates(node):
                    gen_sizes[rec["id"]] = node_count(node)
                    best[rec["id"]] = (gen_sizes[rec["id"]], "generating_formula")
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
    out = {i: {"best_known_size": best[i][0], "best_known_source": best[i][1],
               "generating_formula_size": gen_sizes.get(i)} for i in by_id}
    REFERENCE_SIZES.write_text(json.dumps(out, indent=1) + "\n")
    sources: dict[str, int] = {}
    for size, src in best.values():
        sources[src] = sources.get(src, 0) + 1
    print("best-known sizes set; sources:", sources)


if __name__ == "__main__":
    main()
