#!/usr/bin/env python3
"""Visible train-slice scorer for generated LTLf formulas."""

from __future__ import annotations

import argparse
import glob
import json
import statistics
from dataclasses import dataclass
from pathlib import Path


TRAIN_INSTANCES = {
    "data/paper_benchmark_subset/DoubleCounter__1_5_16_42.json",
    "data/paper_benchmark_subset/Fixed_Formulas__absence1_5_16_42.json",
    "data/paper_benchmark_subset/Hamming__trace_length=16number_atomic_propositions=3number_negative_traces=5delta=1seed=40.json",
    "data/paper_benchmark_subset/OrderedSequence__trace_length=16number_atomic_propositions=3size_sequence=3number_positive_traces=5number_negative_traces=5seed=40.json",
    "data/paper_benchmark_subset/RandomBooleanCombinationsofFactors__trace_length=16number_atomic_propositions=3number_positive_traces=5number_negative_traces=5number_patterns=3seed=43.json",
}
EXPECTED_INSTANCE_COUNT = len(TRAIN_INSTANCES)


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


def canonical_method_name(path: Path, rows: list[dict]) -> str:
    stem = path.stem
    if stem.endswith("_results"):
        stem = stem[: -len("_results")]
    if stem in {"raw_vfb", "vfb"}:
        return "scarlet"
    if stem:
        return stem
    names = {row.get("method") for row in rows if row.get("method")}
    if len(names) == 1:
        return str(next(iter(names)))
    raise ValueError(f"Could not infer method name from {path}")


def load_result_files(patterns: list[str]) -> dict[str, list[dict]]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(Path(p) for p in glob.glob(pattern))
    files = sorted(set(files))
    if not files:
        raise FileNotFoundError(f"No result files matched: {patterns}")

    rows_by_method: dict[str, list[dict]] = {}
    for path in files:
        payload = json.loads(path.read_text())
        rows = payload.get("results", [])
        if not isinstance(rows, list):
            raise ValueError(f"{path} does not contain a list under 'results'")
        method = canonical_method_name(path, rows)
        sliced_by_inst = {
            row["instance"]: dict(row)
            for row in rows
            if row.get("instance") in TRAIN_INSTANCES
        }
        sliced = [
            sliced_by_inst.get(
                instance, {"instance": instance, "formula": None, "_missing_output": True}
            )
            for instance in sorted(TRAIN_INSTANCES)
        ]
        rows_by_method[method] = sliced
    if not rows_by_method:
        raise ValueError("Matched result files contained no train-slice instances")
    return rows_by_method


def summarize(method_rows: list[dict]) -> dict[str, float]:
    solved = [r for r in method_rows if r.get("eval_valid")]
    returned = [r for r in method_rows if r.get("formula")]
    present = [r for r in method_rows if not r.get("_missing_output")]
    collapses = []
    for row in method_rows:
        full_count = row.get("generated_ltl_formulas", 0)
        collapsed_count = row.get("collapsed_bool_atoms", 0)
        if full_count and collapsed_count:
            collapses.append(full_count / collapsed_count)
    return {
        "solve_rate": len(solved) / len(method_rows) if method_rows else 0.0,
        "evaluation_coverage": len(present) / len(method_rows) if method_rows else 0.0,
        "all_returned_formulas_valid": 1.0 if len(solved) == len(returned) else 0.0,
        "mean_collapse_ratio": statistics.fmean(collapses) if collapses else 0.0,
    }


def add_validation(rows_by_method: dict[str, list[dict]]) -> None:
    for rows in rows_by_method.values():
        for row in rows:
            ok, size = validate_formula(Path(row["instance"]), row.get("formula"))
            row["eval_valid"] = ok
            row["eval_formula_size"] = size


def median_size_ratio(rows: list[dict], baseline_rows: list[dict]) -> float:
    baseline_by_inst = {r["instance"]: r for r in baseline_rows}
    ratios = []
    for row in rows:
        base = baseline_by_inst.get(row["instance"])
        if not (row.get("eval_valid") and base and base.get("eval_valid")):
            continue
        base_size = base.get("eval_formula_size")
        if base_size:
            ratios.append(row["eval_formula_size"] / base_size)
    return statistics.median(ratios) if ratios else 0.0


def baseline_miss_solve_rate(rows: list[dict], baseline_rows: list[dict] | None) -> float:
    if not baseline_rows:
        return 0.0
    rows_by_inst = {r["instance"]: r for r in rows}
    baseline_misses = [r for r in baseline_rows if not r.get("eval_valid")]
    if not baseline_misses:
        return 0.0
    solved_misses = [
        r for r in baseline_misses if rows_by_inst.get(r["instance"], {}).get("eval_valid")
    ]
    return len(solved_misses) / len(baseline_misses)


def score(rows_by_method: dict[str, list[dict]]) -> dict:
    add_validation(rows_by_method)
    baseline_rows = rows_by_method.get("scarlet")
    baseline = summarize(baseline_rows) if baseline_rows else None
    results = {}
    for method, rows in sorted(rows_by_method.items()):
        summary = summarize(rows)
        if method == "scarlet":
            formula_size_ratio = 1.0
            delta = 0.0
        elif baseline_rows and baseline:
            formula_size_ratio = median_size_ratio(rows, baseline_rows)
            delta = summary["solve_rate"] - baseline["solve_rate"]
        else:
            formula_size_ratio = 0.0
            delta = 0.0
        results[method] = {
            **summary,
            "formula_size_ratio": formula_size_ratio,
            "solve_rate_delta_vs_baseline": delta,
            "baseline_miss_solve_rate": baseline_miss_solve_rate(rows, baseline_rows),
        }
    return {
        "experiments": {
            "selected_benchmarks": {
                "_slice": "train",
                "_expected_instances": EXPECTED_INSTANCE_COUNT,
                "results": results,
            }
        }
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results-glob", action="append", default=["outputs/*_results.json"])
    ap.add_argument("--out", default="scoring/scores_train.json")
    args = ap.parse_args()

    scores = score(load_result_files(args.results_glob))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scores, indent=2))


if __name__ == "__main__":
    main()
