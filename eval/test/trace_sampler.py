#!/usr/bin/env python3
"""Spot-free uniform trace sampler for the paper's formula-based benchmark families.

The paper's generic task generator (LTLf_Learning_Benchmarks/sample.py) compiles
an LTLf formula into a deterministic automaton with the Spot model checker and
samples distinct traces of a fixed length uniformly at random from the language
(positives) and from its complement (negatives).  Spot is not available in this
environment, so this module produces the same distribution without it:

* ``parse`` reads the benchmark formula syntax (Spot's LTLf syntax: ! && & || |
  -> <-> X X[!] F G U R W M true false), with Spot's operator precedence
  (unary > U R W M > && > || > -> <->; -> and <-> right-associative).
* rejection sampling: uniform random traces of the requested length, kept when
  the formula accepts (positives) or rejects (negatives).  Conditioning the
  uniform distribution on membership is exactly the uniform distribution on the
  language, which is what sample.py draws from.
* exact sampling (``ExactSampler``) for classes too rare to reach by rejection:
  a backward dynamic programme over the truth values of the formula's temporal
  subformulas counts the traces of each length reaching each state, then draws
  a trace position by position with probability proportional to the counts —
  the same counting scheme sample.py runs on Spot's automaton.

Used only offline by eval/test/build_instances.py; the hidden test never runs it.
"""

from __future__ import annotations

import random
import re

# --------------------------------------------------------------------------
# Parsing (Spot LTLf syntax)
# --------------------------------------------------------------------------

_TOK = re.compile(r"\s*(X\[!\]|<->|->|&&|\|\||[()!&|]|[A-Za-z_][A-Za-z0-9_]*)")
_UNARY = {"!", "X", "X[!]", "F", "G"}
# binary operator -> (precedence, associativity)
_BIN = {"<->": (1, "right"), "->": (1, "right"), "|": (2, "left"), "&": (3, "left"),
        "U": (4, "right"), "R": (4, "right"), "W": (4, "right"), "M": (4, "right")}
_ALIAS = {"&&": "&", "||": "|"}


def tokenize(text: str) -> list[str]:
    out, pos = [], 0
    text = text.strip()
    while pos < len(text):
        m = _TOK.match(text, pos)
        if not m:
            raise ValueError(f"bad character at {pos}: {text[pos:pos + 20]!r}")
        out.append(_ALIAS.get(m.group(1), m.group(1)))
        pos = m.end()
    return out


def parse(text: str):
    """Nested tuples: ("ap", name) | ("true",) | ("false",) | (op, child) | (op, l, r)."""
    toks = tokenize(text)
    pos = 0

    def unary():
        nonlocal pos
        tok = toks[pos]
        pos += 1
        if tok in _UNARY:
            return (tok, unary())
        if tok == "(":
            node = binary(0)
            if toks[pos] != ")":
                raise ValueError("expected )")
            pos += 1
            return node
        if tok in ("true", "1"):
            return ("true",)
        if tok in ("false", "0"):
            return ("false",)
        if tok in _BIN or tok == ")":
            raise ValueError(f"unexpected {tok!r}")
        return ("ap", tok)

    def binary(min_prec: int):
        nonlocal pos
        left = unary()
        while pos < len(toks) and toks[pos] in _BIN and _BIN[toks[pos]][0] >= min_prec:
            op = toks[pos]
            prec, assoc = _BIN[op]
            pos += 1
            right = binary(prec if assoc == "right" else prec + 1)
            left = (op, left, right)
        return left

    node = binary(0)
    if pos != len(toks):
        raise ValueError("trailing tokens")
    return node


def to_core(node):
    """Rewrite into the paper's operator set (! & | X X[!] F G U R, true, false)."""
    op = node[0]
    if op in ("ap", "true", "false"):
        return node
    if len(node) == 2:
        return (op, to_core(node[1]))
    a, b = to_core(node[1]), to_core(node[2])
    if op == "->":
        return ("|", ("!", a), b)
    if op == "<->":
        return ("|", ("&", a, b), ("&", ("!", a), ("!", b)))
    if op == "W":   # a W b = b R (a | b)
        return ("R", b, ("|", a, b))
    if op == "M":   # a M b = b U (a & b)
        return ("U", b, ("&", a, b))
    return (op, a, b)


def size(node) -> int:
    return 1 + sum(size(c) for c in node[1:] if isinstance(c, tuple))


def show(node) -> str:
    op = node[0]
    if op == "ap":
        return node[1]
    if len(node) == 1:
        return op
    if len(node) == 2:
        return f"{op}({show(node[1])})"
    return f"({show(node[1])}) {op} ({show(node[2])})"


# --------------------------------------------------------------------------
# Bitset evaluation over many traces of equal length
# --------------------------------------------------------------------------


class Batch:
    """Traces of one length L as Python-int bitsets: bit i*n + t = position i of trace t."""

    def __init__(self, traces: list[dict], aps: list[str], length: int):
        self.n = n = len(traces)
        self.length = length
        self.valid = (1 << (n * length)) - 1
        self.last = ((1 << n) - 1) << ((length - 1) * n)
        self.atoms = {}
        for ap in aps:
            v = 0
            for t, tr in enumerate(traces):
                for i, b in enumerate(tr[ap]):
                    if b:
                        v |= 1 << (i * n + t)
            self.atoms[ap] = v
        self.shifts = []
        s = 1
        while s < length:
            self.shifts.append(s * n)
            s *= 2

    def until(self, a: int, b: int) -> int:
        for s in self.shifts:
            b |= a & (b >> s)
            a &= a >> s
        return b

    def ev(self, node) -> int:
        op = node[0]
        if op == "ap":
            return self.atoms[node[1]]
        if op == "true":
            return self.valid
        if op == "false":
            return 0
        if len(node) == 2:
            a = self.ev(node[1])
            if op == "!":
                return a ^ self.valid
            if op == "X[!]":
                return a >> self.n
            if op == "X":
                return (a >> self.n) | self.last
            if op == "F":
                return self.until(self.valid, a)
            if op == "G":
                return self.valid ^ self.until(self.valid, a ^ self.valid)
            raise ValueError(op)
        a, b = self.ev(node[1]), self.ev(node[2])
        if op == "&":
            return a & b
        if op == "|":
            return a | b
        if op == "U":
            return self.until(a, b)
        if op == "R":
            return self.valid ^ self.until(a ^ self.valid, b ^ self.valid)
        if op == "->":
            return (a ^ self.valid) | b
        if op == "<->":
            return self.valid ^ (a ^ b)
        if op == "W":
            return self.ev(("R", node[2], ("|", node[1], node[2])))
        if op == "M":
            return self.ev(("U", node[2], ("&", node[1], node[2])))
        raise ValueError(op)

    def accepted(self, node) -> list[bool]:
        v = self.ev(node)
        return [bool(v >> t & 1) for t in range(self.n)]


def accepts(node, traces: list[dict], aps: list[str]) -> list[bool]:
    """Membership of each trace (traces may have different lengths)."""
    out = [False] * len(traces)
    by_len: dict[int, list[int]] = {}
    for k, tr in enumerate(traces):
        by_len.setdefault(len(tr[aps[0]]), []).append(k)
    for length, idx in by_len.items():
        res = Batch([traces[k] for k in idx], aps, length).accepted(node)
        for k, r in zip(idx, res):
            out[k] = r
    return out


# --------------------------------------------------------------------------
# Sampling
# --------------------------------------------------------------------------


def random_traces(rng: random.Random, aps: list[str], length: int, count: int) -> list[dict]:
    fmt = "{:0%db}" % length
    return [{ap: [int(c) for c in fmt.format(rng.getrandbits(length))] for ap in aps} for _ in range(count)]


def _key(tr: dict, aps: list[str]) -> tuple:
    return tuple(tuple(tr[ap]) for ap in aps)


def rejection_sample(node, aps: list[str], length: int, n_pos: int, n_neg: int, rng: random.Random,
                     max_draws: int = 200_000, batch: int = 2000):
    """Distinct positives / negatives drawn uniformly by rejection; None for a class not filled.

    Stops early when the observed rate of a missing class makes filling it
    within `max_draws` hopeless (that class then goes to the exact sampler).
    """
    pos: dict[tuple, dict] = {}
    neg: dict[tuple, dict] = {}
    draws = 0
    while (len(pos) < n_pos or len(neg) < n_neg) and draws < max_draws:
        trs = random_traces(rng, aps, length, batch)
        draws += batch
        for tr, ok in zip(trs, Batch(trs, aps, length).accepted(node)):
            bucket, want = (pos, n_pos) if ok else (neg, n_neg)
            if len(bucket) < want:
                bucket.setdefault(_key(tr, aps), tr)
        hopeless = False
        for bucket, want in ((pos, n_pos), (neg, n_neg)):
            if len(bucket) < want and len(bucket) * max_draws < 0.5 * want * draws:
                hopeless = True
        if hopeless:
            break
    return (list(pos.values()) if len(pos) >= n_pos else None,
            list(neg.values()) if len(neg) >= n_neg else None, draws)


class ExactSampler:
    """Uniform sampling of length-L traces by counting over subformula-truth states.

    The truth values at position i of the formula's subformulas are a function of
    the letter at i and of the truth values at i+1 of the nodes that temporal
    operators look ahead to (operands of X / X[!], and F G U R W M nodes
    themselves).  Those look-ahead truth values (plus the root's) form the state.
    Counting the suffixes that reach each state gives exact uniform sampling,
    like counting runs of a deterministic automaton (sample.py does this on
    Spot's automaton).  All 2^|AP| letters are evaluated at once as bitmasks, so
    a state's successors are found with a few big-integer operations.
    """

    def __init__(self, node, aps: list[str], length: int, max_states: int = 60_000):
        self.aps, self.length = aps, length
        m = len(aps)
        self.universe = 1 << m
        self.all = (1 << self.universe) - 1
        nodes: list[tuple] = []
        index: dict[int, int] = {}

        def visit(nd):
            for c in nd[1:]:
                if isinstance(c, tuple):
                    visit(c)
            index[id(nd)] = len(nodes)
            nodes.append(nd)

        visit(node)
        self.nodes = nodes
        self.child = [[index[id(c)] for c in nd[1:] if isinstance(c, tuple)] for nd in nodes]
        self.root = len(nodes) - 1
        look: set[int] = set()
        for k, nd in enumerate(nodes):
            op = nd[0]
            if op in ("X", "X[!]"):
                look.add(self.child[k][0])
            elif op in ("F", "G", "U", "R", "W", "M"):
                look.add(k)
        self.look = sorted(look)
        self.look_pos = {k: j for j, k in enumerate(self.look)}
        # bitmask over letters (bit s of mask_j = value of AP j in letter s)
        self.ap_mask = {}
        for j, ap in enumerate(aps):
            block = ((1 << (1 << j)) - 1) << (1 << j)
            mask, period = 0, 1 << (j + 1)
            for start in range(0, self.universe, period):
                mask |= block << start
            self.ap_mask[ap] = mask
        self.trans: dict = {}
        self.counts: list = [None] * length
        layer: dict[tuple, int] = {}
        for st, _part, c in self._succ(None):
            layer[st] = layer.get(st, 0) + c
        self.counts[length - 1] = layer
        for i in range(length - 2, -1, -1):
            cur: dict[tuple, int] = {}
            for st_next, cn in self.counts[i + 1].items():
                for st, _part, c in self._succ(st_next):
                    cur[st] = cur.get(st, 0) + c * cn
            if len(self.trans) > max_states:
                raise RuntimeError("too many states")
            self.counts[i] = cur

    def _succ(self, nxt):
        """[(state at i, letter mask, letter count)] for state `nxt` at i+1 (None: end)."""
        hit = self.trans.get(nxt)
        if hit is not None:
            return hit
        ALL = self.all
        end = nxt is None
        val = [0] * len(self.nodes)

        def ahead(k):
            return 0 if end else (ALL if nxt[0][self.look_pos[k]] else 0)

        for k, nd in enumerate(self.nodes):
            op = nd[0]
            ch = self.child[k]
            if op == "ap":
                v = self.ap_mask[nd[1]]
            elif op == "true":
                v = ALL
            elif op == "false":
                v = 0
            elif op == "!":
                v = ALL ^ val[ch[0]]
            elif op == "&":
                v = val[ch[0]] & val[ch[1]]
            elif op == "|":
                v = val[ch[0]] | val[ch[1]]
            elif op == "->":
                v = (ALL ^ val[ch[0]]) | val[ch[1]]
            elif op == "<->":
                v = ALL ^ (val[ch[0]] ^ val[ch[1]])
            elif op == "X[!]":
                v = ahead(ch[0])
            elif op == "X":
                v = ALL if end else ahead(ch[0])
            elif op == "F":
                v = val[ch[0]] | ahead(k)
            elif op == "G":
                v = val[ch[0]] & (ALL if end else ahead(k))
            elif op == "U":
                v = val[ch[1]] | (val[ch[0]] & ahead(k))
            elif op == "R":
                v = val[ch[1]] & (val[ch[0]] | (ALL if end else ahead(k)))
            elif op == "W":
                v = val[ch[1]] | (val[ch[0]] & (ALL if end else ahead(k)))
            elif op == "M":
                v = val[ch[1]] & (val[ch[0]] | ahead(k))
            else:
                raise ValueError(op)
            val[k] = v
        # partition the letters by the truth vector of (look-ahead nodes, root)
        parts = [((), ALL)]
        for k in self.look + [self.root]:
            vk = val[k]
            nparts = []
            for bits, p in parts:
                a, b = p & vk, p & ~vk
                if a:
                    nparts.append((bits + (True,), a))
                if b:
                    nparts.append((bits + (False,), b))
            parts = nparts
        out = [((bits[:-1], bits[-1]), p, p.bit_count()) for bits, p in parts]
        self.trans[nxt] = out
        return out

    def total(self, accepted: bool) -> int:
        return sum(c for st, c in self.counts[0].items() if st[1] == accepted)

    def _letter(self, part: int, rng: random.Random) -> dict:
        k = rng.randrange(part.bit_count())
        x = part
        for _ in range(k):
            x &= x - 1
        s = (x & -x).bit_length() - 1
        return s

    def _reverse(self):
        """rev[state] = [(state at i+1, letter mask, letter count)] leading to `state` at i."""
        if getattr(self, "rev", None) is None:
            rev: dict = {}
            for nxt, succ in self.trans.items():
                if nxt is None:
                    continue
                for st, p, c in succ:
                    rev.setdefault(st, []).append((nxt, p, c))
            self.rev = rev
        return self.rev

    def sample(self, accepted: bool, rng: random.Random) -> dict:
        rev = self._reverse()
        state = _choose(rng, [(st, c) for st, c in self.counts[0].items() if st[1] == accepted])
        letters = []
        for i in range(self.length):
            if i == self.length - 1:
                opts = [(p, c) for st, p, c in self._succ(None) if st == state]
                letters.append(self._letter(_choose(rng, opts), rng))
                break
            nxt_counts = self.counts[i + 1]
            opts = []
            for st_next, p, c in rev.get(state, ()):
                cn = nxt_counts.get(st_next)
                if cn:
                    opts.append(((p, st_next), c * cn))
            part, state = _choose(rng, opts)
            letters.append(self._letter(part, rng))
        return {ap: [(letters[i] >> j) & 1 for i in range(self.length)] for j, ap in enumerate(self.aps)}

    def sample_distinct(self, accepted: bool, count: int, rng: random.Random):
        if self.total(accepted) < count:
            return None
        out: dict[tuple, dict] = {}
        while len(out) < count:
            tr = self.sample(accepted, rng)
            out.setdefault(_key(tr, self.aps), tr)
        return list(out.values())


def _choose(rng: random.Random, weighted: list):
    total = sum(w for _, w in weighted)
    r = rng.randrange(total)
    for item, w in weighted:
        if r < w:
            return item
        r -= w
    raise AssertionError


def sample_instance(formula: str, aps: list[str], length: int, n_each: int, rng: random.Random,
                    max_states: int = 12_000):
    """Positives and negatives (n_each distinct each) drawn uniformly; None if impossible here.

    Rejection sampling first; a class it cannot fill is drawn with the exact
    counting sampler (None when its state space exceeds `max_states`, or when the
    class has fewer than n_each distinct traces, as sample.py also refuses).
    """
    node = parse(formula)
    pos, neg, _ = rejection_sample(node, aps, length, n_each, n_each, rng)
    if pos is None or neg is None:
        try:
            ex = ExactSampler(node, aps, length, max_states=max_states)
        except RuntimeError:
            return None
        if pos is None:
            pos = ex.sample_distinct(True, n_each, rng)
        if neg is None:
            neg = ex.sample_distinct(False, n_each, rng)
    if pos is None or neg is None:
        return None
    rng.shuffle(pos)
    rng.shuffle(neg)
    return pos, neg
