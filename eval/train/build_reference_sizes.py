#!/usr/bin/env python3
"""Fix best_known_size of every training instance (eval/train/reference_sizes.json).

best_known_size = smallest syntax-tree size among (a) the generating formula
recorded in the paper's release for that instance and (b) every valid separator
returned by a learner run (run records *.jsonl or formula-free details.json).
Trivial constructions (TRIVIAL) are not counted.  Where no learner found a
separator, the value is the lower bound proven by exhaustive enumeration
(eval/train/lower_bounds.json).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from evaluate import REFERENCE_SIZES, WORKSPACE, check_formula, encoded, load_instances, node_count, parse  # noqa: E402

SOURCE_ZIP = WORKSPACE / "data" / "downloads" / "benchmarks.zip"
TRIVIAL = {"literal_cover", "null_answer", "crash", "forged_fields"}
LOWER_BOUNDS = HERE / "lower_bounds.json"


_SPOT_TOK = re.compile(r"\s*(X\[!\]|<->|->|&&|\|\||[()!&|]|[A-Za-z_][A-Za-z0-9_]*)")
_SPOT_BIN = {"<->": (1, "right"), "->": (1, "right"), "|": (2, "left"), "&": (3, "left"),
             "U": (4, "right"), "R": (4, "right"), "W": (4, "right"), "M": (4, "right")}


def spot_to_core(text: str, renaming: dict[str, str]) -> str:
    """Release formula (Spot LTLf syntax: -> <-> W M, Spot precedence) -> the
    evaluated grammar, with propositions renamed as in the training files."""
    toks, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _SPOT_TOK.match(text, pos)
        if not m:
            raise ValueError(f"bad character at {pos}")
        toks.append({"&&": "&", "||": "|"}.get(m.group(1), m.group(1)))
        pos = m.end()
    i = 0

    def unary():
        nonlocal i
        tok = toks[i]
        i += 1
        if tok in ("!", "X", "X[!]", "F", "G"):
            return f"{tok}({unary()})"
        if tok == "(":
            out = binary(0)
            i += 1  # ')'
            return out
        if tok in ("true", "false"):
            return tok
        return renaming.get(tok, tok)

    def binary(min_prec):
        nonlocal i
        left = unary()
        while i < len(toks) and toks[i] in _SPOT_BIN and _SPOT_BIN[toks[i]][0] >= min_prec:
            op = toks[i]
            prec, assoc = _SPOT_BIN[op]
            i += 1
            right = binary(prec if assoc == "right" else prec + 1)
            a, b = f"({left})", f"({right})"
            if op == "->":
                left = f"(!{a}) | {b}"
            elif op == "<->":
                left = f"({a} & {b}) | ((!{a}) & (!{b}))"
            elif op == "W":
                left = f"{b} R ({a} | {b})"
            elif op == "M":
                left = f"{b} U ({a} & {b})"
            else:
                left = f"{a} {op} {b}"
        return left

    return binary(0)


def balanced(formula: str) -> str:
    """The upstream OrderedSequence writer emits one unmatched trailing ')'."""
    while formula.count(")") > formula.count("(") and formula.rstrip().endswith(")"):
        formula = formula.rstrip()[:-1]
    return formula


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs-dir", action="append", default=[])
    ap.add_argument("--details", action="append", default=[])
    args = ap.parse_args()
    sys.setrecursionlimit(20000)
    instances, manifest = load_instances()
    by_id = {inst["id"]: inst for inst in instances}
    best: dict[str, tuple[int, str]] = {}
    gen_sizes: dict[str, int | None] = {}

    learner_hits: set[str] = set()

    def offer(iid: str, size: int, source: str) -> None:
        if source != "generating_formula":
            learner_hits.add(iid)
        if iid in by_id and (iid not in best or size < best[iid][0]):
            best[iid] = (size, source)

    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        for rec in manifest["instances"]:
            data = json.loads(archive.read(rec["source_file"]))
            gen = data.get("generating_formula") or ""
            gen_sizes[rec["id"]] = None
            if gen:
                inst = by_id[rec["id"]]
                if "proposition_renaming" in rec:  # formula families: Spot syntax, renamed propositions
                    gen = spot_to_core(gen, rec["proposition_renaming"])
                node = parse(balanced(gen), set(inst["atomic_propositions"]))
                if encoded(inst).separates(node):
                    gen_sizes[rec["id"]] = node_count(node)
                    offer(rec["id"], gen_sizes[rec["id"]], "generating_formula")
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
    # A generating formula only tightens an instance that some learner solved;
    # where no learner found a separator the reference is the exhaustive lower
    # bound (the paper's size ratio is relative to learner runs; a generating
    # specification of hundreds of nodes would make such an instance lenient).
    learner_solved = {iid for iid, (_, src) in best.items() if src != "generating_formula"} | learner_hits
    for iid in list(best):
        if iid not in learner_solved:
            del best[iid]
    bounds = json.loads(LOWER_BOUNDS.read_text()) if LOWER_BOUNDS.exists() else {}
    for iid in by_id:
        if iid not in best and iid in bounds:
            best[iid] = (bounds[iid]["lower_bound"], "exhaustive_lower_bound")
    missing = [i for i in by_id if i not in best]
    if missing:
        raise SystemExit(f"no learner separator and no lower bound for {missing}")
    out = {i: {"best_known_size": best[i][0], "best_known_source": best[i][1],
               "generating_formula_size": gen_sizes.get(i)} for i in by_id}
    REFERENCE_SIZES.write_text(json.dumps(out, indent=1) + "\n")
    sources: dict[str, int] = {}
    for _, src in best.values():
        sources[src] = sources.get(src, 0) + 1
    print("best-known sizes set; sources:", sources)


if __name__ == "__main__":
    main()
