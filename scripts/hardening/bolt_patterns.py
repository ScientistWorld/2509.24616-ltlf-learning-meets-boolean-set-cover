#!/usr/bin/env python3
"""Better-method experiment: Bolt with directed temporal patterns as extra Boolean Set Cover atoms.

Same pipeline and settings as the reference (VFB up to LTL2BS-switch 8 with the
memory threshold, collapse with size-dom 10, beam search width 100 up to
D&C-switch 70, non-overlapping divide and conquer), with one change to the atom
pool handed to Boolean Set Cover: besides the VFB formulas (all of size <= 8),
it also receives *directed* formulas from the fragment used by Scarlet (Raha et
al., TACAS'22), which VFB cannot reach beyond size 8:

    psi ::= l  |  l & X[!](psi)  |  l & X[!](F(psi))        (l a literal p or !p)
    atoms:  F(psi), !F(psi)

The patterns are built right to left by a beam that keeps, per pattern length,
the `--pattern-beam` patterns whose F(psi) classifies the most traces correctly
(with the better polarity), deduplicated by characteristic table.  The beam
search of Boolean Set Cover is generalised so that, at every weight, atoms of
that weight compete with |/& combinations of lighter entries (Algorithm 3 with
atoms of arbitrary weight).

The paper's own discussion motivates this: Scarlet's pattern fragment is where
it beats Bolt (Subset), and better time/size trade-offs for Boolean Set Cover
are left open.  Generic: no family, instance or formula is hardcoded.

Usage: bolt_patterns.py <instance.json> <answer.json> [--no-patterns] [--no-cap]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "method"))
import ltlf_bolt as B  # noqa: E402


# --------------------------------------------------------------------------
# Directed patterns
# --------------------------------------------------------------------------


def directed_atoms(tr: B.Traces, store: B.Store, max_len: int, beam: int, max_size: int, deadline: float):
    """Return {size: [(cv, fid)]} of F(psi) / !F(psi) atoms for the best directed patterns."""
    n, VALID, FIRST, T = tr.n, tr.VALID, tr.FIRST, tr.TARGET
    npos = T.bit_count()
    nneg = n - npos
    lits = []
    for ap in tr.aps:
        lits.append((tr.atoms[ap], ("ap", ap), 1))
        lits.append((tr.atoms[ap] ^ VALID, ("!", ("ap", ap)), 2))
    out: dict[int, list] = {}
    seen_cv: set[int] = set()
    fid_of: dict[int, int] = {}
    alive: list = []  # keeps materialised expressions alive so their id() stays unique

    def materialise(expr) -> int:
        key = id(expr)
        if key in fid_of:
            return fid_of[key]
        alive.append(expr)
        op = expr[0]
        if op == "ap":
            node = expr
        elif len(expr) == 2:
            node = (op, materialise(expr[1]))
        else:
            node = (op, materialise(expr[1]), materialise(expr[2]))
        store.nodes.append(node)
        store.sizes.append(_size(expr))
        fid_of[key] = len(store.nodes) - 1
        return fid_of[key]

    def add_atom(cv: int, expr, size: int) -> None:
        if size > max_size or cv in seen_cv:
            return
        seen_cv.add(cv)
        out.setdefault(size, []).append((cv, materialise(expr)))

    level = [(tab, expr, sz) for tab, expr, sz in lits]
    seen_tab: set[int] = {tab for tab, _, _ in level}
    for length in range(1, max_len + 1):
        scored = []
        for tab, expr, sz in level:
            ftab = tr.F(tab)
            cv = ftab & FIRST
            pc = (cv & T).bit_count()
            nc = cv.bit_count() - pc
            good = max(pc + (nneg - nc), (npos - pc) + nc)
            scored.append((good, pc, nc, -sz, tab, ftab, expr, sz))
        # diverse beam: best overall accuracy, highest recall, highest precision
        kept, taken = [], set()
        orders = (lambda x: (x[0], x[3]), lambda x: (x[1], -x[2], x[3]), lambda x: (-x[2], x[1], x[3]))
        for order in orders:
            for row in sorted(scored, key=order, reverse=True)[: max(1, beam // len(orders))]:
                if id(row) not in taken:
                    taken.add(id(row))
                    kept.append(row)
        for good, _pc, _nc, _, tab, ftab, expr, sz in kept:
            f_expr = ("F", expr)
            add_atom(ftab & FIRST, f_expr, sz + 1)
            add_atom((ftab ^ VALID) & FIRST, ("!", f_expr), sz + 2)
        if length == max_len or time.process_time() > deadline:
            break
        nxt = []
        for good, _pc, _nc, _, tab, ftab, expr, sz in kept:
            shifted = tab >> n
            fshift = ftab >> n
            for ltab, lexpr, lsz in lits:
                for t, inner, extra in ((ltab & shifted, ("X[!]", expr), 2), (ltab & fshift, ("X[!]", ("F", expr)), 3)):
                    if not t & VALID or t in seen_tab:
                        continue
                    seen_tab.add(t)
                    nsz = lsz + extra + sz
                    if nsz + 1 > max_size:
                        continue
                    nxt.append((t, ("&", lexpr, inner), nsz))
        level = nxt
        if not level:
            break
    return out


def _size(expr) -> int:
    return 1 + sum(_size(c) for c in expr[1:] if isinstance(c, tuple))


# --------------------------------------------------------------------------
# Beam search with atoms of arbitrary weight
# --------------------------------------------------------------------------


def beam_search_general(ctx: B.Ctx, cache_lines: list, target: int, mask: int, width: int, max_size: int,
                        extra_lines: list | None = None, extra_width: int = 50):
    """Algorithm 3 with atoms of any weight.  `cache_lines` (VFB atoms) and the
    |/& combinations share the `width` slots of each weight, exactly as in the
    reference; `extra_lines` (pattern atoms) get `extra_width` slots of their own
    at each weight, so they add to the beam without displacing its entries."""
    m = mask.bit_count()
    keys: set[int] = set()
    lines: list[list[tuple]] = [[]]
    keep = 16 * width
    for size in range(1, max_size + 1):
        buckets = [[] for _ in range(m + 1)]
        if size < len(cache_lines):
            for entry in cache_lines[size]:
                key = entry[0] & mask
                buckets[(key ^ target).bit_count()].append((key, None, entry, None))
        extra = []
        if extra_lines is not None and size < len(extra_lines) and extra_lines[size]:
            eb = [[] for _ in range(m + 1)]
            for entry in extra_lines[size]:
                key = entry[0] & mask
                if key == target:
                    return entry
                eb[(key ^ target).bit_count()].append((key, None, entry, None))
            extra = eb
        cut = m
        for i in range(1, (size + 1) // 2):
            j = size - 1 - i
            A, B_ = lines[i], lines[j]
            if not A or not B_:
                continue
            same = i == j
            for ai, (ka, ea) in enumerate(A):
                rows = B_[ai:] if same else B_
                ctx.spend(2 * len(rows))
                for kb, eb in rows:
                    k = ka | kb
                    if k == target:
                        return B.combine(ctx, "|", ea, eb)
                    e = (k ^ target).bit_count()
                    if e <= cut:
                        buckets[e].append((k, "|", ea, eb))
                    k = ka & kb
                    if k == target:
                        return B.combine(ctx, "&", ea, eb)
                    e = (k ^ target).bit_count()
                    if e <= cut:
                        buckets[e].append((k, "&", ea, eb))
                total = 0
                for e in range(cut + 1):
                    total += len(buckets[e])
                    if total >= keep:
                        cut = e
                        break
        line = B._select(ctx, buckets, width, keys, target, mask)
        if extra:
            line = line + B._select(ctx, extra, extra_width, keys, target, mask)
        lines.append(line)
    return None


class PatternSolver(B.BoolSolver):
    """Divide and conquer over two atom pools: VFB atoms (`src_lines`, reduced as
    in the reference) and pattern atoms (`self.extra`, reduced the same way)."""

    def __init__(self, *a, extra=None, no_cap: bool = False, **kw):
        super().__init__(*a, **kw)
        self.extra = extra
        self.no_cap = no_cap

    def solve_or_split(self, src_lines: list, mask: int, extra_src=None):
        self.calls += 1
        if extra_src is None:
            extra_src = self.extra
        target = self.tr.TARGET & mask
        lines, by_sv = B.reduce_cache(self.ctx, src_lines, target, mask, self.size_dom)
        hit = by_sv.get(mask)
        if hit is not None:
            return hit
        extra_lines = None
        if extra_src:
            extra_lines, extra_sv = B.reduce_cache(self.ctx, extra_src, target, mask, self.size_dom)
            hit = extra_sv.get(mask)
            if hit is not None:
                return hit
        if self.no_cap or mask.bit_count() <= 128:
            res = beam_search_general(self.ctx, lines, target, mask, self.width, self.max_size, extra_lines)
            if res is not None:
                return res
        return self.split_two(lines, extra_lines, mask)

    def split_two(self, lines, extra_lines, mask):
        T = self.tr.TARGET
        pos, neg = mask & T, mask & ~T
        npos, nneg = pos.bit_count(), neg.bit_count()
        if npos <= 1 and nneg <= 1:
            return None
        if npos > nneg:
            op, cls, other = "|", pos, neg
        else:
            op, cls, other = "&", neg, pos
        half, j, x = 0, 0, cls
        while x:
            low = x & -x
            if j % 2 == 0:
                half |= low
            j += 1
            x ^= low
        left = self.solve_or_split(lines, other | half, extra_lines)
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
        right = self.solve_or_split(lines, right_mask, extra_lines)
        if right is None:
            return None
        return B.combine(self.ctx, op, left, right)


# --------------------------------------------------------------------------
# Driver (mirrors ltlf_bolt.solve for mode bolt)
# --------------------------------------------------------------------------


def solve(data: dict, args) -> dict:
    t0 = time.process_time()
    budget = args.budget
    hard_deadline = t0 + 0.9 * budget
    tr = B.Traces(data)
    store = B.Store()
    sol, lines, vals, stats = B.vfb(tr, store, 8, 500000, 1500, t0 + 0.5 * budget)
    if sol is not None:
        return {"formula": store.text(sol)}
    FIRST = tr.FIRST
    src = [[(vals[fid] & FIRST, fid) for fid in ids] for ids in lines]
    extra_src = None
    if args.patterns:
        extra = directed_atoms(tr, store, args.pattern_len, args.pattern_beam, 70, t0 + 0.6 * budget)
        if extra:
            extra_src = [[] for _ in range(max(extra) + 1)]
            for size, atoms in extra.items():
                extra_src[size].extend(atoms)
    ctx = B.Ctx(store, hard_deadline, 1e15)
    solver = PatternSolver(tr, ctx, 100, 70, 10, extra=extra_src, no_cap=args.no_cap)
    try:
        res = solver.solve_or_split(src, FIRST)
    except B.Budget:
        res = None
    return {"formula": ctx.text(res[1]) if res is not None else None}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("instance")
    p.add_argument("answer")
    p.add_argument("--no-patterns", dest="patterns", action="store_false")
    p.add_argument("--no-cap", action="store_true", help="run beam search before splitting at any trace count")
    p.add_argument("--pattern-len", type=int, default=12)
    p.add_argument("--pattern-beam", type=int, default=100)
    p.add_argument("--budget", type=float, default=float(os.environ.get("LTLF_CPU_BUDGET_S", "20")))
    args = p.parse_args()
    sys.setrecursionlimit(100000)
    data = json.load(open(args.instance))
    json.dump(solve(data, args), open(args.answer, "w"))


if __name__ == "__main__":
    main()
