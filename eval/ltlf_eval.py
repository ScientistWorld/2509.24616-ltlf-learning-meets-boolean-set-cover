#!/usr/bin/env python3
"""Method-independent evaluator for LTLf learning outputs."""

from __future__ import annotations

import argparse
import json
import statistics
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Node:
    op: str
    args: tuple

    def size(self) -> int:
        return 1 + sum(a.size() for a in self.args if isinstance(a, Node))


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif text.startswith("X[!]", i):
            out.append("X[!]")
            i += 4
        elif c in "()!&|URFG":
            out.append(c)
            i += 1
        elif c.isalnum() or c == "_":
            j = i + 1
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            out.append(text[i:j])
            i = j
        else:
            raise ValueError(f"Unexpected token near {text[i:i+20]!r}")
    return out


class Parser:
    prec = {"|": 1, "&": 2, "U": 3, "R": 3}

    def __init__(self, tokens: list[str]):
        self.tokens = tokens
        self.i = 0

    def peek(self) -> str | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def pop(self) -> str:
        tok = self.peek()
        if tok is None:
            raise ValueError("Unexpected end of formula")
        self.i += 1
        return tok

    def parse(self, min_prec: int = 0) -> Node:
        tok = self.pop()
        if tok == "(":
            left = self.parse()
            if self.pop() != ")":
                raise ValueError("Expected ')'")
        elif tok in {"!", "X[!]", "F", "G"}:
            left = Node(tok, (self.parse(4),))
        elif tok in {"true", "false"}:
            left = Node(tok, ())
        else:
            left = Node("atom", (tok,))
        while self.peek() in self.prec and self.prec[self.peek()] >= min_prec:
            op = self.pop()
            right = self.parse(self.prec[op] + 1)
            left = Node(op, (left, right))
        return left


def parse_formula(text: str) -> Node:
    parser = Parser(tokenize(text))
    node = parser.parse()
    if parser.peek() is not None:
        raise ValueError(f"Trailing token {parser.peek()!r}")
    return node


def eval_row(node: Node, trace: dict[str, list[int]]) -> tuple[bool, ...]:
    if node.op == "atom":
        return tuple(bool(x) for x in trace[node.args[0]])
    length = len(next(iter(trace.values())))
    if node.op == "true":
        return (True,) * length
    if node.op == "false":
        return (False,) * length
    if node.op == "!":
        row = eval_row(node.args[0], trace)
        return tuple(not x for x in row)
    if node.op == "X[!]":
        row = eval_row(node.args[0], trace)
        return row[1:] + (False,)
    if node.op == "F":
        row = eval_row(node.args[0], trace)
        out = [False] * len(row)
        seen = False
        for i in range(len(row) - 1, -1, -1):
            seen = seen or row[i]
            out[i] = seen
        return tuple(out)
    if node.op == "G":
        child_not = Node("!", (node.args[0],))
        return tuple(not x for x in eval_row(Node("F", (child_not,)), trace))
    left = eval_row(node.args[0], trace)
    right = eval_row(node.args[1], trace)
    if node.op == "&":
        return tuple(a and b for a, b in zip(left, right))
    if node.op == "|":
        return tuple(a or b for a, b in zip(left, right))
    if node.op == "U":
        out = [False] * len(left)
        acc = False
        for i in range(len(left) - 1, -1, -1):
            acc = right[i] or (left[i] and acc)
            out[i] = acc
        return tuple(out)
    if node.op == "R":
        left_not = Node("!", (node.args[0],))
        right_not = Node("!", (node.args[1],))
        return tuple(not x for x in eval_row(Node("U", (left_not, right_not)), trace))
    raise ValueError(node.op)


def accepts(node: Node, traces: list[dict[str, list[int]]]) -> list[bool]:
    return [eval_row(node, tr)[0] for tr in traces]


def validate_formula(instance_path: Path, formula: str | None) -> tuple[bool, int | None]:
    if not formula:
        return False, None
    data = json.loads(instance_path.read_text())
    traces = data["positive_traces"] + data["negative_traces"]
    target = [True] * len(data["positive_traces"]) + [False] * len(data["negative_traces"])
    try:
        node = parse_formula(formula)
        return accepts(node, traces) == target, node.size()
    except (KeyError, ValueError, IndexError):
        return False, None


def summarize(method_rows: list[dict]) -> dict[str, float]:
    solved = [r for r in method_rows if r.get("eval_valid")]
    returned = [r for r in method_rows if r.get("formula")]
    collapses = []
    for row in method_rows:
        full_count = row.get("generated_ltl_formulas", 0)
        collapsed_count = row.get("collapsed_bool_atoms", 0)
        if full_count and collapsed_count:
            collapses.append(full_count / collapsed_count)
    return {
        "solve_rate": len(solved) / len(method_rows) if method_rows else 0.0,
        "all_returned_formulas_valid": 1.0 if len(solved) == len(returned) else 0.0,
        "mean_collapse_ratio": statistics.fmean(collapses) if collapses else 0.0,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bolt", required=True)
    ap.add_argument("--vfb", required=True)
    ap.add_argument("--out", default="scoring/scores.json")
    args = ap.parse_args()

    rows_by_method = {}
    for name, path in [("bolt", Path(args.bolt)), ("raw_vfb", Path(args.vfb))]:
        rows = json.loads(path.read_text())["results"]
        for row in rows:
            ok, size = validate_formula(Path(row["instance"]), row.get("formula"))
            row["eval_valid"] = ok
            row["eval_formula_size"] = size
        rows_by_method[name] = rows

    bolt = summarize(rows_by_method["bolt"])
    vfb = summarize(rows_by_method["raw_vfb"])
    common = []
    vfb_by_inst = {r["instance"]: r for r in rows_by_method["raw_vfb"]}
    for b in rows_by_method["bolt"]:
        v = vfb_by_inst.get(b["instance"])
        if b.get("eval_valid") and v and v.get("eval_valid"):
            common.append((b, v))
    ratios = [b["eval_formula_size"] / v["eval_formula_size"] for b, v in common if v["eval_formula_size"]]

    scores = {
        "experiments": {
            "selected_benchmarks": {
                "results": {
                    "bolt": {
                        **bolt,
                        "formula_size_ratio": statistics.median(ratios) if ratios else 0.0,
                        "solve_rate_delta_vs_baseline": bolt["solve_rate"] - vfb["solve_rate"],
                    },
                }
            }
        }
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
