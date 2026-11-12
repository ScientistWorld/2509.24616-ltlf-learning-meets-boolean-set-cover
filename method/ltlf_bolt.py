#!/usr/bin/env python3
"""Bolt: LTLf learning with bounded VFB enumeration + Boolean Set Cover.

Python port of the algorithm of "LTLf Learning Meets Boolean Set Cover"
(Bathie, Fijalkow, Matricon, Mouillon, Vandenhove), following the authors'
Rust implementation (https://github.com/SynthesisLab/Bolt, fetched into
method/Bolt by scripts/download.sh) wherever the paper leaves details open.

1. VFB (Algorithm 4 / Rust `enum_aux`): bottom-up enumeration of LTLf formulas
   by syntactic size over unary {!, X, X[!], F, G} and binary {&, |, U, R}
   operators, evaluated as characteristic tables with bitwise operations
   (Appendix A) and pruned by observational equivalence (identical tables).
   Enumeration stops at LTL2BS-switch, or earlier when a memory threshold on the
   stored characteristic tables is reached (Section 3: the switch is "chosen
   based on a memory or time threshold").
2. Collapse (Algorithm 1 / Rust `InitialBoolCache`): keep the first-bit
   (characteristic) vector of each formula, merge formulas with equal vectors,
   and drop formulas dominated by one of the `size_dom` densest formulas of
   strictly smaller size (fast approximate domination, Section 3.2).
3. Beam search for Boolean Set Cover (Algorithm 3 / Rust `beam_search`):
   enumerate |/& combinations by weight, keeping for each weight the
   `beam_width` formulas that classify the most traces correctly, skipping
   observationally equivalent and dominated formulas, up to D&C-switch.
4. Divide and conquer (Algorithm 2 / Rust `split_and_solve_non_overlapping`):
   when beam search fails (or a subproblem has more than 128 traces), split the
   larger class alternately, solve the left part, then recurse only on the
   traces that the left solution does not already handle; combine with |
   (positives were split) or & (negatives were split).

Characteristic tables are Python integers in a position-major layout: bit
`i * n + t` holds the truth value at position i of trace t (n traces).  The
lowest n bits are therefore exactly the characteristic vector used by the
Boolean Set Cover stage.

Solver contract (see briefing/evaluation.md):
    python3 method/ltlf_bolt.py --instance task.json --out answer.json
writes {"formula": "<LTLf formula>" | null}.  The per-instance CPU budget is
read from the LTLF_CPU_BUDGET_S environment variable (seconds).
"""

from __future__ import annotations

import argparse
import heapq
import json
import os
import sys
import time


# --------------------------------------------------------------------------
# Characteristic tables
# --------------------------------------------------------------------------


class Traces:
    """Bitset encoding of an instance (positive traces first, then negatives)."""

    def __init__(self, data: dict):
        pos = data["positive_traces"]
        neg = data["negative_traces"]
        self.aps = list(data["atomic_propositions"])
        traces = list(pos) + list(neg)
        self.n = n = len(traces)
        self.n_pos = len(pos)
        lengths = []
        for tr in traces:
            ls = {len(tr[ap]) for ap in self.aps}
            if len(ls) != 1:
                raise ValueError("atomic propositions of a trace have different lengths")
            lengths.append(ls.pop())
        self.maxlen = maxlen = max(lengths)
        nbits = maxlen * n
        top = nbits - 1  # bit b lives at string index top - b
        valid = ["0"] * nbits
        last = ["0"] * nbits
        for t, length in enumerate(lengths):
            for i in range(length):
                valid[top - (i * n + t)] = "1"
            last[top - ((length - 1) * n + t)] = "1"
        self.VALID = int("".join(valid), 2)
        self.LAST = int("".join(last), 2)
        self.FIRST = (1 << n) - 1
        self.TARGET = (1 << self.n_pos) - 1
        self.atoms: dict[str, int] = {}
        for ap in self.aps:
            bits = ["0"] * nbits
            for t, tr in enumerate(traces):
                for i, b in enumerate(tr[ap]):
                    if b:
                        bits[top - (i * n + t)] = "1"
            self.atoms[ap] = int("".join(bits), 2)
        shifts = []
        s = 1
        while s < maxlen:
            shifts.append(s * n)
            s *= 2
        self.shifts = tuple(shifts)

    def F(self, a: int) -> int:
        for s in self.shifts:
            a |= a >> s
        return a

    def U(self, a: int, b: int) -> int:
        for s in self.shifts:
            b |= a & (b >> s)
            a &= a >> s
        return b


# --------------------------------------------------------------------------
# Formula representation
# --------------------------------------------------------------------------


class Store:
    """LTL formulas produced by VFB, as implicit trees over formula ids."""

    def __init__(self) -> None:
        self.nodes: list[tuple] = []
        self.sizes: list[int] = []

    def text(self, fid: int) -> str:
        node = self.nodes[fid]
        op = node[0]
        if op == "ap":
            return node[1]
        if op in ("true", "false"):
            return op
        if len(node) == 2:
            return f"{op}({self.text(node[1])})"
        return f"({self.text(node[1])}) {op} ({self.text(node[2])})"


class BNode:
    """Boolean combination of VFB formulas.  Leaves are plain int formula ids."""

    __slots__ = ("op", "left", "right", "size")

    def __init__(self, op: str, left, right, size: int):
        self.op, self.left, self.right, self.size = op, left, right, size


class Budget(Exception):
    """Raised when the deterministic work cap or the CPU deadline is exhausted."""


class Ctx:
    """Shared state of the Boolean stage: formula store, deadline, work counter."""

    def __init__(self, store: Store, deadline: float, max_work: float):
        self.store, self.deadline, self.max_work = store, deadline, max_work
        self.work = 0

    def size(self, node) -> int:
        return self.store.sizes[node] if isinstance(node, int) else node.size

    def text(self, node) -> str:
        if isinstance(node, int):
            return self.store.text(node)
        return f"({self.text(node.left)}) {node.op} ({self.text(node.right)})"

    def spend(self, amount: int) -> None:
        self.work += amount
        if self.work > self.max_work or time.process_time() > self.deadline:
            raise Budget


def combine(ctx: Ctx, op: str, a: tuple, b: tuple) -> tuple:
    """Combine two Boolean entries (cv, node) with | or &."""
    cv = a[0] | b[0] if op == "|" else a[0] & b[0]
    return cv, BNode(op, a[1], b[1], ctx.size(a[1]) + ctx.size(b[1]) + 1)


# --------------------------------------------------------------------------
# 1. VFB enumeration
# --------------------------------------------------------------------------


def vfb(tr: Traces, store: Store, max_size: int, max_formulas: int, max_memory_mb: float, deadline: float):
    """Bottom-up LTLf enumeration with observational equivalence.

    Returns (solution_id | None, lines, vals, stats); lines[s] lists the ids of
    retained formulas of size s and vals[id] their characteristic tables.
    """
    VALID, LAST, FIRST, T, n, SH = tr.VALID, tr.LAST, tr.FIRST, tr.TARGET, tr.n, tr.shifts
    vals: list[int] = []
    seen: set[int] = set()
    lines: list[list[int]] = [[], []]
    stats = {"generated": 0, "stopped_by": "ltl_switch", "completed_size": 1}
    # memory threshold: rough per-formula footprint of a retained table
    per_formula = 240 + (tr.maxlen * n) / 8
    max_formulas = max(64, min(max_formulas, int(max_memory_mb * 1e6 / per_formula)))
    clock = time.process_time
    nodes, sizes = store.nodes, store.sizes

    def push(v: int, node: tuple, size: int, line: list) -> None:
        seen.add(v)
        vals.append(v)
        nodes.append(node)
        sizes.append(size)
        line.append(len(nodes) - 1)

    def found(node: tuple, size: int, generated: int):
        nodes.append(node)
        sizes.append(size)
        vals.append(None)
        stats["generated"] = generated
        return len(nodes) - 1, lines, vals, stats

    base = [(("true",), VALID), (("false",), 0)] + [(("ap", ap), tr.atoms[ap]) for ap in tr.aps]
    for node, v in base:
        if v not in seen:
            push(v, node, 1, lines[1])
    for fid in lines[1]:
        if vals[fid] & FIRST == T:
            return fid, lines, vals, stats

    generated = 0
    counter = 0
    last_nonempty = 1
    for size in range(2, max_size + 1):
        if size > 2 * last_nonempty + 1:
            stats["stopped_by"] = "saturated"
            break
        line: list[int] = []
        lines.append(line)
        for fid in lines[size - 1]:
            v = vals[fid]
            nv = v ^ VALID
            f_v = v
            for s in SH:
                f_v |= f_v >> s
            f_nv = nv
            for s in SH:
                f_nv |= f_nv >> s
            for op, g in (
                ("!", nv),
                ("X", (v >> n) | LAST),
                ("X[!]", v >> n),
                ("F", f_v),
                ("G", VALID ^ f_nv),
            ):
                generated += 1
                if g & FIRST == T:
                    return found((op, fid), size, generated)
                if g not in seen:
                    push(g, (op, fid), size, line)
            counter += 1
            if counter & 63 == 0:
                if clock() > deadline:
                    stats["stopped_by"] = "time"
                    stats["generated"] = generated
                    return None, lines, vals, stats
                if len(vals) > max_formulas:
                    stats["stopped_by"] = "memory"
                    stats["generated"] = generated
                    return None, lines, vals, stats
        for i in range(1, (size + 1) // 2):
            j = size - 1 - i
            left_ids, right_ids = lines[i], lines[j]
            same = i == j
            for li, lid in enumerate(left_ids):
                a = vals[lid]
                na = a ^ VALID
                for rid in (right_ids[li:] if same else right_ids):
                    b = vals[rid]
                    nb = b ^ VALID
                    x, y = a, b
                    for s in SH:
                        y |= x & (y >> s)
                        x &= x >> s
                    u_ab = y
                    x, y = b, a
                    for s in SH:
                        y |= x & (y >> s)
                        x &= x >> s
                    u_ba = y
                    x, y = na, nb
                    for s in SH:
                        y |= x & (y >> s)
                        x &= x >> s
                    r_ab = VALID ^ y
                    x, y = nb, na
                    for s in SH:
                        y |= x & (y >> s)
                        x &= x >> s
                    r_ba = VALID ^ y
                    for op, g, p, q in (
                        ("&", a & b, lid, rid),
                        ("|", a | b, lid, rid),
                        ("U", u_ab, lid, rid),
                        ("U", u_ba, rid, lid),
                        ("R", r_ab, lid, rid),
                        ("R", r_ba, rid, lid),
                    ):
                        generated += 1
                        if g & FIRST == T:
                            return found((op, p, q), size, generated)
                        if g not in seen:
                            push(g, (op, p, q), size, line)
                    counter += 1
                    if counter & 63 == 0:
                        if clock() > deadline:
                            stats["stopped_by"] = "time"
                            stats["generated"] = generated
                            return None, lines, vals, stats
                        if len(vals) > max_formulas:
                            stats["stopped_by"] = "memory"
                            stats["generated"] = generated
                            return None, lines, vals, stats
        stats["completed_size"] = size
        if line:
            last_nonempty = size
    stats["generated"] = generated
    return None, lines, vals, stats


# --------------------------------------------------------------------------
# 2. Collapse + approximate domination (InitialBoolCache)
# --------------------------------------------------------------------------


def reduce_cache(ctx: Ctx, src_lines: list, target: int, mask: int, size_dom: int):
    """Restrict a cache of Boolean atoms to the traces in `mask`.

    src_lines[s] is a list of entries (cv, node) of weight s.  Entries with the
    same characteristic vector on `mask` are merged (first one wins, i.e. the
    smallest), and an entry is dropped when one of the `size_dom` densest
    entries of strictly smaller weight dominates it (its set of correctly
    classified traces is a superset).  Returns (lines, by_sv).
    """
    by_sv: dict[int, tuple] = {}
    lines: list[list[tuple]] = [[] for _ in src_lines]
    best: list[list[tuple[int, int, int]]] = [[] for _ in src_lines]
    seq = 0
    for size, line in enumerate(src_lines):
        ctx.spend(len(line))
        smaller = tuple(s for h in best[:size] for (_, _, s) in h)
        out = lines[size]
        heap = best[size]
        for entry in line:
            sv = ~(entry[0] ^ target) & mask
            if sv in by_sv:
                continue
            dominated = False
            for s in smaller:
                if s | sv == s:
                    dominated = True
                    break
            if dominated:
                continue
            by_sv[sv] = entry
            out.append(entry)
            seq += 1
            heapq.heappush(heap, (sv.bit_count(), seq, sv))
            if len(heap) > size_dom:
                heapq.heappop(heap)
    return lines, by_sv


# --------------------------------------------------------------------------
# 3. Beam search for Boolean Set Cover
# --------------------------------------------------------------------------


def _select(ctx: Ctx, buckets, width: int, keys: set, target: int, mask: int) -> list:
    """Keep the `width` best non-equivalent, non-dominated candidates.

    buckets[e] holds the candidates that misclassify e traces of the
    subproblem, in generation order.  A candidate is (key, op, a, b): key is
    its characteristic vector restricted to `mask`; op is None for an existing
    entry a, otherwise the entry is op(a, b).  Returns [(key, entry)].
    """
    chosen: list = []
    chosen_svs: list[int] = []
    for bucket in buckets:
        for key, op, a, b in bucket:
            if key in keys:
                continue
            sv = ~(key ^ target) & mask
            dominated = False
            for s in chosen_svs:
                if s | sv == s:
                    dominated = True
                    break
            if dominated:
                continue
            keys.add(key)
            chosen.append((key, a if op is None else combine(ctx, op, a, b)))
            chosen_svs.append(sv)
            if len(chosen) >= width:
                return chosen
    return chosen


def beam_search(ctx: Ctx, cache_lines: list, target: int, mask: int, width: int, max_size: int):
    """Algorithm 3: bottom-up |/& enumeration keeping `width` formulas per weight.

    Candidates are generated for a whole weight before the `width` best are
    kept (the top-`width` priority queue of Algorithm 3).  Candidates whose
    score cannot reach the kept set are counted but not stored.
    """
    m = mask.bit_count()
    keys: set[int] = set()
    lines: list[list[tuple]] = []
    keep = 16 * width  # stored candidates per weight before cutting the worst scores
    for line in cache_lines:
        buckets = [[] for _ in range(m + 1)]
        for entry in line:
            key = entry[0] & mask
            buckets[(key ^ target).bit_count()].append((key, None, entry, None))
        lines.append(_select(ctx, buckets, width, keys, target, mask))
    for size in range(len(lines), max_size + 1):
        buckets = [[] for _ in range(m + 1)]
        cut = m
        for i in range(1, (size + 1) // 2):
            j = size - 1 - i
            if j >= len(lines):
                continue
            A, B = lines[i], lines[j]
            if not A or not B:
                continue
            same = i == j
            for ai, (ka, ea) in enumerate(A):
                rows = B[ai:] if same else B
                ctx.spend(2 * len(rows))
                for kb, eb in rows:
                    k = ka | kb
                    if k == target:
                        return combine(ctx, "|", ea, eb)
                    e = (k ^ target).bit_count()
                    if e <= cut:
                        buckets[e].append((k, "|", ea, eb))
                    k = ka & kb
                    if k == target:
                        return combine(ctx, "&", ea, eb)
                    e = (k ^ target).bit_count()
                    if e <= cut:
                        buckets[e].append((k, "&", ea, eb))
                total = 0
                for e in range(cut + 1):
                    total += len(buckets[e])
                    if total >= keep:
                        cut = e
                        break
        lines.append(_select(ctx, buckets, width, keys, target, mask))
    return None


# --------------------------------------------------------------------------
# 4. Divide and conquer
# --------------------------------------------------------------------------


class BoolSolver:
    def __init__(self, tr: Traces, ctx: Ctx, width: int, max_size: int, size_dom: int):
        self.tr, self.ctx, self.width, self.max_size, self.size_dom = tr, ctx, width, max_size, size_dom
        self.calls = 0

    def solve_or_split(self, src_lines: list, mask: int):
        self.calls += 1
        target = self.tr.TARGET & mask
        lines, by_sv = reduce_cache(self.ctx, src_lines, target, mask, self.size_dom)
        hit = by_sv.get(mask)  # every trace of the subproblem classified correctly
        if hit is not None:
            return hit
        if mask.bit_count() <= 128:
            res = beam_search(self.ctx, lines, target, mask, self.width, self.max_size)
            if res is not None:
                return res
        return self.split(lines, mask)

    def split(self, lines: list, mask: int):
        T = self.tr.TARGET
        pos = mask & T
        neg = mask & ~T
        npos, nneg = pos.bit_count(), neg.bit_count()
        if npos <= 1 and nneg <= 1:
            return None
        if npos > nneg:
            op, cls, other = "|", pos, neg
        else:
            op, cls, other = "&", neg, pos
        half = 0
        j = 0
        x = cls
        while x:
            low = x & -x
            if j % 2 == 0:
                half |= low
            j += 1
            x ^= low
        left = self.solve_or_split(lines, other | half)
        if left is None:
            return None
        solved = left[0]
        if op == "|":
            right_mask = mask & (~T | ~solved)
            remaining = (right_mask & T).bit_count()
        else:
            right_mask = mask & (T | solved)
            remaining = (right_mask & ~T).bit_count()
        if remaining == 0:
            return left
        right = self.solve_or_split(lines, right_mask)
        if right is None:
            return None
        return combine(self.ctx, op, left, right)


# --------------------------------------------------------------------------
# Optional post-processing: greedy simplification of a valid formula
# --------------------------------------------------------------------------


def _parse(text: str):
    """Parse the fully parenthesised output syntax into nested tuples."""
    toks: list[str] = []
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif text.startswith("X[!]", i):
            toks.append("X[!]")
            i += 4
        elif c in "()!&|":
            toks.append(c)
            i += 1
        else:
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            toks.append(text[i:j])
            i = j
    pos = 0

    def unit():
        nonlocal pos
        t = toks[pos]
        pos += 1
        if t == "(":
            node = expr()
            pos += 1  # ')'
            return node
        if t in ("!", "X", "X[!]", "F", "G"):
            return (t, unit())
        if t in ("true", "false"):
            return (t,)
        return ("ap", t)

    def expr():
        nonlocal pos
        left = unit()
        while pos < len(toks) and toks[pos] in ("&", "|", "U", "R"):
            op = toks[pos]
            pos += 1
            left = (op, left, unit())
        return left

    return expr()


def _size(node) -> int:
    return 1 + sum(_size(c) for c in node[1:] if isinstance(c, tuple))


def _show(node) -> str:
    op = node[0]
    if op == "ap":
        return node[1]
    if len(node) == 1:
        return op
    if len(node) == 2:
        return f"{op}({_show(node[1])})"
    return f"({_show(node[1])}) {op} ({_show(node[2])})"


def _eval(node, tr: Traces) -> int:
    op = node[0]
    if op == "ap":
        return tr.atoms[node[1]]
    if op == "true":
        return tr.VALID
    if op == "false":
        return 0
    if op == "!":
        return _eval(node[1], tr) ^ tr.VALID
    if op == "X[!]":
        return _eval(node[1], tr) >> tr.n
    if op == "X":
        return (_eval(node[1], tr) >> tr.n) | tr.LAST
    if op == "F":
        return tr.F(_eval(node[1], tr))
    if op == "G":
        return tr.VALID ^ tr.F(_eval(node[1], tr) ^ tr.VALID)
    a, b = _eval(node[1], tr), _eval(node[2], tr)
    if op == "&":
        return a & b
    if op == "|":
        return a | b
    if op == "U":
        return tr.U(a, b)
    if op == "R":
        return tr.VALID ^ tr.U(a ^ tr.VALID, b ^ tr.VALID)
    raise ValueError(op)


def simplify(text: str, tr: Traces, deadline: float) -> str:
    """Greedily replace subformulas by a child or a constant while the formula
    still separates the traces (generic size reduction, not part of Bolt)."""
    root = _parse(text)

    def separates(node) -> bool:
        return _eval(node, tr) & tr.FIRST == tr.TARGET

    def edits(node):
        # yield (replacement, path-rebuilder) candidates for every subtree
        def walk(n, rebuild):
            if len(n) >= 2 and isinstance(n[1], tuple):
                for child in n[1:]:
                    if isinstance(child, tuple):
                        yield rebuild(child)
                for c in (("true",), ("false",)):
                    yield rebuild(c)
                for k in range(1, len(n)):
                    if isinstance(n[k], tuple):
                        yield from walk(n[k], lambda sub, k=k, n=n, rb=rebuild: rb(n[:k] + (sub,) + n[k + 1:]))

        yield from walk(node, lambda sub: sub)

    improved = True
    while improved and time.process_time() < deadline:
        improved = False
        cur = _size(root)
        for cand in sorted(edits(root), key=_size):
            if time.process_time() > deadline:
                break
            if _size(cand) >= cur:
                break
            if separates(cand):
                root = cand
                improved = True
                break
    return _show(root)


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def solve(data: dict, args) -> dict:
    t0 = time.process_time()
    budget = args.budget
    hard_deadline = t0 + args.safety * budget
    tr = Traces(data)
    store = Store()
    info: dict = {"mode": args.mode}
    if args.mode == "vfb":
        ltl_deadline = hard_deadline
        max_size = 10**6
        max_formulas = 10**9
    else:
        ltl_deadline = t0 + args.ltl_time_fraction * budget
        max_size = args.ltl_switch
        max_formulas = args.max_ltl_formulas
    sol, lines, vals, stats = vfb(tr, store, max_size, max_formulas, args.max_memory_mb, ltl_deadline)
    info.update({"ltl_" + k: v for k, v in stats.items()})
    formula = None
    if sol is not None:
        formula = store.text(sol)
        info["phase"] = "ltl"
    elif args.mode == "bolt":
        FIRST = tr.FIRST
        src = [[(vals[fid] & FIRST, fid) for fid in ids] for ids in lines]
        ctx = Ctx(store, hard_deadline, args.max_bool_work)
        solver = BoolSolver(tr, ctx, args.beam_width, args.dc_switch, args.size_dom)
        try:
            res = solver.solve_or_split(src, FIRST)
        except Budget:
            res = None
            info["phase"] = "budget"
        info["bool_calls"] = solver.calls
        info["bool_work"] = ctx.work
        info["atoms"] = sum(len(x) for x in lines)
        if res is not None:
            formula = ctx.text(res[1])
            info["phase"] = "bool"
    else:
        info["phase"] = stats["stopped_by"]
    if formula is not None and args.simplify:
        formula = simplify(formula, tr, t0 + 0.95 * budget)
    info["cpu_s"] = time.process_time() - t0
    return {"formula": formula, "info": info}


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--instance", required=True, help="benchmark JSON (positive_traces, negative_traces, atomic_propositions)")
    p.add_argument("--out", required=True, help="where to write {\"formula\": ...}")
    p.add_argument("--mode", choices=["bolt", "vfb"], default="bolt", help="bolt = VFB + Boolean Set Cover; vfb = raw VFB ablation")
    p.add_argument("--ltl-switch", type=int, default=8, help="LTL2BS-switch: max LTL size enumerated before Boolean Set Cover (paper: 8)")
    p.add_argument("--size-dom", type=int, default=10, help="k of the fast approximate domination (Rust default example: 10)")
    p.add_argument("--beam-width", type=int, default=30, help="beam width per weight (paper: 100)")
    p.add_argument("--dc-switch", type=int, default=30, help="D&C-switch: max Boolean weight before splitting (paper: 70)")
    p.add_argument("--max-ltl-formulas", type=int, default=200000, help="memory threshold of the VFB stage: max retained LTL formulas before switching")
    p.add_argument("--max-bool-work", type=float, default=1e15, help="optional deterministic work cap of the Boolean stage (candidate formulas + cache entries); default: none, the CPU deadline applies")
    p.add_argument("--max-memory-mb", type=float, default=1500, help="estimated memory cap for stored characteristic tables")
    p.add_argument("--ltl-time-fraction", type=float, default=0.5, help="safety time threshold for the VFB stage, as a fraction of the budget")
    p.add_argument("--safety", type=float, default=0.9, help="stop all search at this fraction of the CPU budget")
    p.add_argument("--budget", type=float, default=float(os.environ.get("LTLF_CPU_BUDGET_S", "20")), help="CPU seconds per instance")
    p.add_argument("--simplify", action="store_true", help="greedy post-hoc size reduction of the returned formula")
    args = p.parse_args()
    with open(args.instance) as fh:
        data = json.load(fh)
    sys.setrecursionlimit(100000)
    result = solve(data, args)
    with open(args.out, "w") as fh:
        json.dump(result, fh)


if __name__ == "__main__":
    main()
