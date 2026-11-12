#!/usr/bin/env python3
"""Brute-force separator from time-indexed literals (Lemma 1 style shortcut).

For each positive trace p not yet accepted, greedily pick literals
X[!]^t(a) or X[!]^t(!a) that hold on p, weighted by size, until every negative
trace is excluded; the separator is the disjunction of these conjunctions.
It never generalises over time, so its formulas grow with the number of traces.
Usage: literal_cover.py <instance.json> <answer.json>
"""

import json
import sys


def literal(ap: str, t: int, bit: int) -> tuple[str, int]:
    text, size = (ap, 1) if bit else (f"!({ap})", 2)
    for _ in range(t):
        text, size = f"X[!]({text})", size + 1
    return text, size


def holds(trace: dict, ap: str, t: int, bit: int) -> bool:
    row = trace[ap]
    return t < len(row) and bool(row[t]) == bool(bit)


def balanced(op: str, items: list[str]) -> str:
    if len(items) == 1:
        return items[0]
    mid = len(items) // 2
    return f"({balanced(op, items[:mid])}) {op} ({balanced(op, items[mid:])})"


def main() -> None:
    data = json.load(open(sys.argv[1]))
    aps = data["atomic_propositions"]
    pos, neg = data["positive_traces"], data["negative_traces"]
    terms: list[list[tuple[str, int, int]]] = []
    for p in pos:
        if any(all(holds(p, ap, t, b) for ap, t, b in term) for term in terms):
            continue
        length = len(p[aps[0]])
        lits = [(ap, t, p[ap][t]) for ap in aps for t in range(length)]
        uncovered = set(range(len(neg)))
        chosen = []
        while uncovered:
            best, best_gain = None, 0.0
            for ap, t, b in lits:
                excluded = sum(1 for k in uncovered if not holds(neg[k], ap, t, b))
                gain = excluded / literal(ap, t, b)[1]
                if gain > best_gain:
                    best, best_gain = (ap, t, b), gain
            if best is None:
                json.dump({"formula": None}, open(sys.argv[2], "w"))
                return
            chosen.append(best)
            uncovered = {k for k in uncovered if holds(neg[k], *best)}
        terms.append(chosen)
    conj = [balanced("&", [literal(*lit)[0] for lit in term]) for term in terms]
    json.dump({"formula": balanced("|", conj) if conj else "false"}, open(sys.argv[2], "w"))


if __name__ == "__main__":
    main()
