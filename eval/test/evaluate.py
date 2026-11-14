#!/usr/bin/env python3
"""Hidden test for budgeted LTLf learning.

Runs every solver found in scripts/solvers/*.sh on the hidden instances held in
eval/test/instances.json, one fresh process per instance under a fixed CPU
budget, then scores the returned formulas with this file's own parser and
LTLf semantics.  Nothing a solver reports besides its formula string is used.

    python3 eval/test/evaluate.py            # run + score every solver on disk

Per instance i with best known separator size r_i (fixed in instances.json):
  valid_i  formula parses, uses only the instance's propositions, and accepts
           every positive and no negative trace (computed here)
  s_i      number of syntax-tree nodes of the parsed formula
Metrics (experiment "budgeted_ltlf_learning"):
An answer is *acceptable* when it is valid and s_i <= CAP * r_i (CAP = 10):
  size_efficiency    mean_i acceptable_i * min(1, r_i / s_i)            (higher better)
  solve_rate         mean_i acceptable_i                                (higher better)
  size_ratio_geomean geomean_i clip(s_i / r_i, 1, CAP), CAP if not acceptable (lower better)
A solver that crashes, times out, exceeds the CPU budget or prints nothing gets
the worst value on that instance, so a failed run gets 0 / 0 / CAP.  r_i is the
smallest separator found by the generating process or any learner run, or, where
no learner found one, a lower bound proven by exhaustive enumeration.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import resource
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
INSTANCES = HERE / "instances.json"
EXPERIMENT = "budgeted_ltlf_learning"
SLICE = "test"

CPU_BUDGET_S = 20.0          # CPU seconds per instance (solver + its children)
CPU_GRACE_S = 0.5            # interpreter start-up allowance
# Wall clock is only a safety net against hung solvers, far above the CPU
# budget, so node load cannot decide an instance: the budget is CPU time.
WALL_LIMIT_S = 10 * CPU_BUDGET_S
MEMORY_LIMIT_BYTES = 4 * 1024**3
RATIO_CAP = 10.0
WORST = {"size_efficiency": 0.0, "solve_rate": 0.0, "size_ratio_geomean": RATIO_CAP}
MAX_FORMULA_CHARS = 1_000_000
MAX_FORMULA_NODES = 20_000
MAX_FORMULA_DEPTH = 3_000


# --------------------------------------------------------------------------
# LTLf syntax and semantics (independent of any solver)
# --------------------------------------------------------------------------

_TOKEN = re.compile(r"\s*(X\[!\]|&&|\|\||[()!&|]|[A-Za-z_][A-Za-z0-9_]*)")
_UNARY = {"!", "X", "X[!]", "F", "G"}
# The paper's operator set (Section 2.1): Boolean ! & |, temporal X[!] U and the
# derived X F G R.  (Implication/equivalence are not part of the grammar.)
_BINARY = {"|": (3, "left"), "&": (4, "left"), "U": (5, "right"), "R": (5, "right")}
_ALIAS = {"&&": "&", "||": "|"}
_RESERVED = _UNARY | set(_BINARY) | {"true", "false"}


class FormulaError(ValueError):
    pass


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m:
            raise FormulaError(f"bad character at {pos}")
        tok = m.group(1)
        out.append(_ALIAS.get(tok, tok))
        pos = m.end()
    return out


def parse(text: str, aps: set[str]):
    """Parse into nested tuples: ("ap", name) | ("true",) | ("false",) |
    (unary_op, child) | (binary_op, left, right)."""
    toks = tokenize(text)
    pos = 0

    def peek():
        return toks[pos] if pos < len(toks) else None

    def unary(depth: int):
        nonlocal pos
        if depth > MAX_FORMULA_DEPTH:
            raise FormulaError("formula too deep")
        tok = peek()
        if tok is None:
            raise FormulaError("unexpected end")
        pos += 1
        if tok in _UNARY:
            return (tok, unary(depth + 1))
        if tok == "(":
            node = binary(1, depth + 1)
            if peek() != ")":
                raise FormulaError("expected )")
            pos += 1
            return node
        if tok in ("true", "false"):
            return (tok,)
        if tok in _RESERVED or tok not in aps:
            raise FormulaError(f"unknown proposition {tok!r}")
        return ("ap", tok)

    def binary(min_prec: int, depth: int):
        nonlocal pos
        left = unary(depth)
        while True:
            tok = peek()
            if tok not in _BINARY or _BINARY[tok][0] < min_prec:
                return left
            prec, assoc = _BINARY[tok]
            pos += 1
            right = binary(prec if assoc == "right" else prec + 1, depth + 1)
            left = (tok, left, right)

    node = binary(1, 0)
    if pos != len(toks):
        raise FormulaError("trailing tokens")
    return node


def node_count(node) -> int:
    count, stack = 0, [node]
    while stack:
        cur = stack.pop()
        count += 1
        for child in cur[1:]:
            if isinstance(child, tuple):
                stack.append(child)
    return count


class Encoded:
    """Instance as Python-int bitsets: bit i*n+t = position i of trace t."""

    def __init__(self, inst: dict):
        traces = inst["positive_traces"] + inst["negative_traces"]
        aps = inst["atomic_propositions"]
        self.n = n = len(traces)
        self.n_pos = len(inst["positive_traces"])
        lengths = [len(tr[aps[0]]) for tr in traces]
        maxlen = max(lengths)
        self.valid = 0
        self.last = 0
        for t, length in enumerate(lengths):
            for i in range(length):
                self.valid |= 1 << (i * n + t)
            self.last |= 1 << ((length - 1) * n + t)
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
        while s < maxlen:
            self.shifts.append(s * n)
            s *= 2
        self.first = (1 << n) - 1
        self.target = (1 << self.n_pos) - 1

    def until(self, a: int, b: int) -> int:
        for s in self.shifts:
            b |= a & (b >> s)
            a &= a >> s
        return b

    def evaluate(self, node) -> int:
        op = node[0]
        if op == "ap":
            return self.atoms[node[1]]
        if op == "true":
            return self.valid
        if op == "false":
            return 0
        if op in _UNARY:
            a = self.evaluate(node[1])
            if op == "!":
                return a ^ self.valid
            if op == "X[!]":
                return a >> self.n
            if op == "X":
                return (a >> self.n) | self.last
            if op == "F":
                return self.until(self.valid, a)
            return self.valid ^ self.until(self.valid, a ^ self.valid)  # G
        a, b = self.evaluate(node[1]), self.evaluate(node[2])
        if op == "&":
            return a & b
        if op == "|":
            return a | b
        if op == "U":
            return self.until(a, b)
        return self.valid ^ self.until(a ^ self.valid, b ^ self.valid)  # R

    def separates(self, node) -> bool:
        return self.evaluate(node) & self.first == self.target


def check_formula(formula, inst: dict, enc: Encoded) -> tuple[bool, int | None, str]:
    if formula is None:
        return False, None, "no formula"
    if not isinstance(formula, str) or not formula.strip():
        return False, None, "not a formula string"
    if len(formula) > MAX_FORMULA_CHARS:
        return False, None, "formula too long"
    try:
        node = parse(formula, set(inst["atomic_propositions"]))
    except (FormulaError, RecursionError) as exc:
        return False, None, f"parse error: {exc}"
    size = node_count(node)
    if size > MAX_FORMULA_NODES:
        return False, size, "formula too large"
    try:
        ok = enc.separates(node)
    except RecursionError:
        return False, size, "formula too deep"
    return ok, size, "valid" if ok else "does not separate"


# --------------------------------------------------------------------------
# Instances
# --------------------------------------------------------------------------


# Files a solver must not read while it runs (reference sizes and lower bounds).
PROTECTED = (INSTANCES, HERE / "lower_bounds.json")


class protected_files:
    """Make PROTECTED unreadable while solvers run; restore afterwards.

    The evaluator has already loaded everything it needs into memory.  Best
    effort: on a filesystem that refuses chmod, nothing changes.
    """

    def __enter__(self):
        self.saved = []
        for path in PROTECTED:
            try:
                mode = path.stat().st_mode & 0o7777
                path.chmod(0)
                self.saved.append((path, mode))
            except OSError:
                pass
        return self

    def __exit__(self, *exc):
        for path, mode in self.saved:
            try:
                path.chmod(mode)
            except OSError:
                pass
        return False


def _readable(path: Path) -> None:
    """Undo a protection left behind by an evaluation that was killed mid-run."""
    try:
        if path.exists() and not os.access(path, os.R_OK):
            path.chmod(0o644)
    except OSError:
        pass


def load_instances() -> tuple[list[dict], dict]:
    for path in PROTECTED:
        _readable(path)
    payload = json.loads(INSTANCES.read_text())
    out = []
    for rec in payload["instances"]:
        aps = rec["atomic_propositions"]

        def decode(rows):
            return [{ap: [int(c) for c in row[k]] for k, ap in enumerate(aps)} for row in rows]

        out.append({
            "id": rec["id"],
            "family": rec["family"],
            "best_known_size": rec.get("best_known_size"),
            "atomic_propositions": aps,
            "positive_traces": decode(rec["positive"]),
            "negative_traces": decode(rec["negative"]),
        })
    return out, payload


def solver_input(inst: dict) -> dict:
    pos, neg = inst["positive_traces"], inst["negative_traces"]
    aps = inst["atomic_propositions"]
    return {
        "positive_traces": pos,
        "negative_traces": neg,
        "atomic_propositions": aps,
        "number_atomic_propositions": len(aps),
        "number_traces": len(pos) + len(neg),
        "number_positive_traces": len(pos),
        "number_negative_traces": len(neg),
        "max_length_traces": max(len(tr[aps[0]]) for tr in pos + neg),
        "trace_type": "finite",
    }


# --------------------------------------------------------------------------
# Running solvers under the budget
# --------------------------------------------------------------------------


def discover_solvers(solvers_dir: Path) -> dict[str, Path]:
    return {p.stem: p for p in sorted(solvers_dir.glob("*.sh")) if p.is_file()}


def run_one(script: Path, inst: dict) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="ltlf_task_"))
    task, answer, errlog = tmp / "task.json", tmp / "answer.json", tmp / "stderr.txt"
    task.write_text(json.dumps(solver_input(inst)))
    cpu_limit = int(math.ceil(CPU_BUDGET_S + CPU_GRACE_S))

    def limits():
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_limit, cpu_limit + 1))
        resource.setrlimit(resource.RLIMIT_AS, (MEMORY_LIMIT_BYTES, MEMORY_LIMIT_BYTES))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))

    env = {
        "PATH": os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin"),
        "HOME": str(WORKSPACE),
        "LANG": "C.UTF-8",
        "PYTHONHASHSEED": "0",
        "PYTHONDONTWRITEBYTECODE": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "LTLF_CPU_BUDGET_S": str(CPU_BUDGET_S),
    }
    start = time.monotonic()
    killed = False
    with open(errlog, "wb") as err:
        proc = subprocess.Popen(
            ["bash", str(script), str(task), str(answer)],
            cwd=WORKSPACE, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=err, preexec_fn=limits, start_new_session=True,
        )
        while True:
            pid, status, usage = os.wait4(proc.pid, os.WNOHANG)
            if pid:
                break
            if time.monotonic() - start > WALL_LIMIT_S:
                killed = True
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                pid, status, usage = os.wait4(proc.pid, 0)
                break
            time.sleep(0.01)
        proc.returncode = os.waitstatus_to_exitcode(status)
    try:
        os.killpg(proc.pid, signal.SIGKILL)  # stray background children
    except (ProcessLookupError, PermissionError):
        pass
    wall = time.monotonic() - start
    cpu = usage.ru_utime + usage.ru_stime
    rec = {"instance": inst["id"], "returncode": proc.returncode, "cpu_s": round(cpu, 3),
           "wall_s": round(wall, 3), "formula": None}
    if killed:
        rec["status"] = "wall_timeout"
    elif cpu > CPU_BUDGET_S + CPU_GRACE_S:
        rec["status"] = "cpu_budget_exceeded"
    elif proc.returncode != 0:
        rec["status"] = "crashed"
    else:
        try:
            raw = answer.read_text()
            data = json.loads(raw) if len(raw) <= 4 * MAX_FORMULA_CHARS else None
            formula = data.get("formula") if isinstance(data, dict) else None
            rec["formula"] = formula if isinstance(formula, str) else None
            rec["status"] = "answered" if rec["formula"] is not None else "no_formula"
        except (OSError, ValueError):
            rec["status"] = "no_output"
    try:
        rec["stderr_tail"] = errlog.read_bytes()[-500:].decode("utf-8", "replace")
    except OSError:
        pass
    shutil.rmtree(tmp, ignore_errors=True)
    return rec


def run_solver(name: str, script: Path, instances: list[dict], runs_path: Path | None, resume: bool) -> dict:
    """Run one solver on every instance; returns {instance id: record}.

    Records (including formulas) are only written to disk when an explicit
    runs directory is given; by default they stay in memory so that no solver
    can read another solver's answers for the hidden instances.
    """
    records: dict[str, dict] = {}
    if runs_path is not None:
        runs_path.parent.mkdir(parents=True, exist_ok=True)
        if resume:
            records.update(load_runs(runs_path))
        elif runs_path.exists():
            runs_path.unlink()
    for inst in instances:
        if inst["id"] in records:
            continue
        rec = run_one(script, inst)
        records[inst["id"]] = rec
        if runs_path is not None:
            with open(runs_path, "a") as fh:
                fh.write(json.dumps(rec) + "\n")
        print(f"[{SLICE}] {name} {inst['id']} {rec['status']} cpu={rec['cpu_s']}", flush=True)
    return records


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------


def load_runs(path: Path) -> dict[str, dict]:
    runs: dict[str, dict] = {}
    if path.exists():
        for line in path.read_text().splitlines():
            try:
                rec = json.loads(line)
                runs[rec["instance"]] = rec
            except (ValueError, KeyError, TypeError):
                continue
    return runs


_ENCODED: dict[str, Encoded] = {}


def encoded(inst: dict) -> Encoded:
    if inst["id"] not in _ENCODED:
        _ENCODED[inst["id"]] = Encoded(inst)
    return _ENCODED[inst["id"]]


def score_runs(runs: dict[str, dict], instances: list[dict]) -> tuple[dict, list[dict]]:
    eff, solved, logs, rows = [], [], [], []
    for inst in instances:
        rec = runs.get(inst["id"], {})
        ok, size, why = check_formula(rec.get("formula"), inst, encoded(inst))
        if rec and rec.get("status") not in ("answered",):
            ok, why = False, rec.get("status", why)
        ref = inst["best_known_size"]
        if ok and size > RATIO_CAP * ref:
            ok, why = False, "valid but more than CAP x the best-known size"
        if ok:
            eff.append(min(1.0, ref / size))
            logs.append(math.log(min(max(size / ref, 1.0), RATIO_CAP)))
        else:
            eff.append(0.0)
            logs.append(math.log(RATIO_CAP))
        solved.append(1.0 if ok else 0.0)
        rows.append({"instance": inst["id"], "family": inst["family"], "valid": ok, "size": size,
                     "best_known_size": ref, "check": why, "cpu_s": rec.get("cpu_s")})
    n = len(instances)
    metrics = {
        "size_efficiency": sum(eff) / n,
        "solve_rate": sum(solved) / n,
        "size_ratio_geomean": math.exp(sum(logs) / n),
    }
    return metrics, rows


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--solvers-dir", default=str(WORKSPACE / "scripts" / "solvers"))
    ap.add_argument("--runs-dir", default="", help="persist per-instance records (with formulas) here; default: memory only")
    ap.add_argument("--out", default=str(WORKSPACE / "scoring" / "scores_test.json"))
    ap.add_argument("--skip-run", action="store_true", help="score existing runs only")
    ap.add_argument("--no-score", action="store_true", help="run solvers only")
    ap.add_argument("--resume", action="store_true", help="keep finished instances of earlier runs")
    ap.add_argument("--only", default="", help="comma-separated solver names (default: every solver)")
    ap.add_argument("--first", type=int, default=0, help=argparse.SUPPRESS)  # smoke tests only
    args = ap.parse_args()
    sys.setrecursionlimit(4 * MAX_FORMULA_DEPTH + 1000)

    instances, _ = load_instances()
    if args.first:
        instances = instances[: args.first]
    solvers = discover_solvers(Path(args.solvers_dir))
    if args.only:
        keep = set(args.only.split(","))
        solvers = {k: v for k, v in solvers.items() if k in keep}
    runs_dir = Path(args.runs_dir) if args.runs_dir else None
    if args.skip_run and runs_dir is None:
        raise SystemExit("--skip-run needs --runs-dir")
    if not args.no_score and any(inst["best_known_size"] is None for inst in instances):
        raise SystemExit("best_known_size missing; build the reference sizes first")
    out = Path(args.out)
    # Every solver on disk starts with the worst value of every metric; its entry
    # is replaced once it has run, so an interrupted evaluation never leaves a
    # solver without a score.
    results = {name: dict(WORST) for name in solvers}
    details: dict[str, list] = {}
    if not args.no_score:
        write_scores(out, results, len(instances))
    for name, script in solvers.items():
        path = runs_dir / f"{name}.jsonl" if runs_dir else None
        if args.skip_run:
            runs = load_runs(path)
        else:
            with protected_files():
                runs = run_solver(name, script, instances, path, args.resume)
        if args.no_score:
            continue
        results[name], details[name] = score_runs(runs, instances)
        write_scores(out, results, len(instances))
    if not args.no_score:
        details_dir = runs_dir or HERE / "runs"
        details_dir.mkdir(parents=True, exist_ok=True)
        (details_dir / "details.json").write_text(json.dumps(details, indent=1))  # no formulas


def write_scores(out: Path, results: dict, n_instances: int) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"experiments": {EXPERIMENT: {
        "_slice": SLICE,
        "_instances": n_instances,
        "_cpu_budget_s": CPU_BUDGET_S,
        "results": results,
    }}}, indent=2) + "\n")


if __name__ == "__main__":
    main()
