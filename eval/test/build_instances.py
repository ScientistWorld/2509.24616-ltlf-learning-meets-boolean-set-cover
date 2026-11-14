#!/usr/bin/env python3
"""Build the hidden test instances (run once; the output eval/test/instances.json is kept).

Fresh samples from the paper's own benchmark generators
(data/downloads/LTLf_Learning_Benchmarks, fetched by scripts/download.sh) over
parameter combinations drawn uniformly from those in the paper's released
suite, 8 per family, for all ten families:

* OrderedSequence, Subword, Subset, Hamming, RandomBooleanCombinationsofFactors:
  the dedicated instance generators in Generating_Instances/.
* Fixed_Formulas, SingleCounter, DoubleCounter, Nim, Random_Conjuncts_from_Basis:
  the formula of the family (Fixed_Formulas/*.txt or the generator in
  Generating_Formulas/, with a fresh seed for Random_Conjuncts_from_Basis), then
  distinct positive and negative traces of the requested length drawn uniformly
  from the language and its complement, as the paper's sample.py does with Spot
  (here with trace_sampler.py, which needs no model checker).  Propositions are
  renamed a0..a{m-1} by a random permutation (as in the training slice).

Seeds come from the OS random source and are not recorded, so the instances
cannot be regenerated or looked up in the public release.  Only the traces and
the size of the generating formula (an upper bound on the separator size) are
stored.

    python3 eval/test/build_instances.py                   # all ten families, new file
    python3 eval/test/build_instances.py --append --families Fixed_Formulas,...
"""

from __future__ import annotations

import argparse
import ast
import json
import random
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from evaluate import Encoded, node_count, parse  # noqa: E402  (same directory)
import trace_sampler  # noqa: E402  (same directory)

BENCH = ROOT / "data" / "downloads" / "LTLf_Learning_Benchmarks"
GEN_DIR = BENCH / "Generating_Instances"
SOURCE_ZIP = ROOT / "data" / "downloads" / "benchmarks.zip"
GENERATORS = {
    "OrderedSequence": "gen_orderedsequence.py",
    "Subword": "gen_subword.py",
    "Subset": "gen_subset.py",
    "Hamming": "gen_Hamming.py",
    "RandomBooleanCombinationsofFactors": "gen_random_boolean_combinations_factors.py",
}
FORMULA_FAMILIES = ["Fixed_Formulas", "SingleCounter", "DoubleCounter", "Nim", "Random_Conjuncts_from_Basis"]
PER_FAMILY = 8


def formula_family_params(name: str) -> dict:
    """<base>_<traces per class>_<length>_<sampling seed>.json -> parameters (formula seed dropped)."""
    base, n_each, length, _seed = name.split("/", 1)[1][: -len(".json")].rsplit("_", 3)
    fam = name.split("/")[0]
    out: dict = {"number_positive_traces": int(n_each), "number_negative_traces": int(n_each),
                 "trace_length": int(length)}
    if fam == "Fixed_Formulas":
        out["formula"] = base
    elif fam in ("SingleCounter", "DoubleCounter"):
        out["bits"] = int(base)
    else:
        for k, v in re.findall(r"([a-z_]+?)=(\d+)", base.replace("tokens", "_tokens")):
            k = k.strip("_")
            if k != "seed":
                out[k] = int(v)
    return out


def release_combos() -> dict[str, list[tuple]]:
    combos: dict[str, set] = {f: set() for f in list(GENERATORS) + FORMULA_FAMILIES}
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        for name in archive.namelist():
            fam = name.split("/")[0]
            if fam not in combos or not name.endswith(".json") or name.endswith("/formulas.json"):
                continue
            if fam in FORMULA_FAMILIES:
                p = formula_family_params(name)
            else:
                p = dict(re.findall(r"([a-z_]+)=(\d+)", name.split("/", 1)[1]))
                p.pop("seed", None)
            combos[fam].add(tuple(sorted(p.items())))
    return {f: sorted(c) for f, c in combos.items()}


def family_formula(family: str, params: dict, seed: int) -> tuple[str, list[str]]:
    """Formula and propositions of a formula-based family, from the upstream scripts."""
    if family == "Fixed_Formulas":
        line = (BENCH / "Fixed_Formulas" / f"{params['formula']}.txt").read_text().strip()
    else:
        script, folder, args = {
            "SingleCounter": ("gen_singlecounter.py", "SingleCounter", ["-N", params.get("bits")]),
            "DoubleCounter": ("gen_doublecounters.py", "DoubleCounter", ["-N", params.get("bits")]),
            "Nim": ("gen_nim.py", "Nim", ["-heaps", params.get("heaps"), "-tokens", params.get("tokens")]),
            "Random_Conjuncts_from_Basis": ("gen_random_conjuncts_from_basis.py", "Random_Conjuncts_from_Basis",
                                            ["-L", params.get("conjuncts"), "-m", params.get("atomic_propositions"),
                                             "-seed", seed]),
        }[family]
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "gen"
            (work / folder).mkdir(parents=True)
            (Path(tmp) / "Fixed_Formulas").mkdir()
            shutil.copy(BENCH / "Fixed_Formulas" / "formulas.txt", Path(tmp) / "Fixed_Formulas" / "formulas.txt")
            subprocess.run([sys.executable, "-I", str(BENCH / "Generating_Formulas" / script)] + [str(a) for a in args],
                           cwd=work, check=True, timeout=120, capture_output=True)
            line = next((work / folder).glob("*.txt")).read_text().strip()
    formula, aps_text = line.split(";")[:2]
    return formula.strip().strip('"'), list(ast.literal_eval(aps_text))


def generate_formula_family(family: str, combo: tuple, rng: random.Random) -> dict | None:
    params = dict(combo)
    formula, aps = family_formula(family, params, rng.randrange(10**6, 2**31))
    n_each, length = params["number_positive_traces"], params["trace_length"]
    sampled = trace_sampler.sample_instance(formula, aps, length, n_each, rng)
    if sampled is None:
        return None
    pos, neg = sampled
    perm = list(range(len(aps)))
    rng.shuffle(perm)
    mapping = {ap: f"a{perm[k]}" for k, ap in enumerate(aps)}
    new_aps = sorted(mapping.values(), key=lambda a: int(a[1:]))
    rn = lambda tr: {mapping[ap]: tr[ap] for ap in aps}  # noqa: E731
    core = trace_sampler.to_core(trace_sampler.parse(formula))

    def rename_node(nd):
        if nd[0] == "ap":
            return ("ap", mapping[nd[1]])
        return (nd[0],) + tuple(rename_node(c) if isinstance(c, tuple) else c for c in nd[1:])

    return {"atomic_propositions": new_aps, "positive_traces": [rn(t) for t in pos],
            "negative_traces": [rn(t) for t in neg],
            "generating_formula": trace_sampler.show(rename_node(core))}


def generate(family: str, combo: tuple, seed: int) -> dict | None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / family).mkdir()
        cmd = [sys.executable, "-I", str(GEN_DIR / GENERATORS[family])]
        for k, v in combo:
            cmd += [f"-{k}", str(v)]
        cmd += ["-seed", str(seed)]
        try:
            subprocess.run(cmd, cwd=tmp, check=True, timeout=120, capture_output=True)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
            return None
        files = list((Path(tmp) / family).glob("*.json"))
        return json.loads(files[0].read_text()) if files else None


def balanced(formula: str) -> str:
    """The upstream OrderedSequence writer emits one unmatched trailing ')'."""
    while formula.count(")") > formula.count("(") and formula.rstrip().endswith(")"):
        formula = formula.rstrip()[:-1]
    return formula


def encode(data: dict) -> dict:
    aps = data["atomic_propositions"]

    def rows(traces):
        return [["".join(str(int(b)) for b in tr[ap]) for ap in aps] for tr in traces]

    return {"atomic_propositions": aps, "positive": rows(data["positive_traces"]),
            "negative": rows(data["negative_traces"])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--families", default="", help="comma-separated families (default: all ten)")
    ap.add_argument("--append", action="store_true", help="keep existing instances, append new ones")
    args = ap.parse_args()
    sysrng = secrets.SystemRandom()
    rng = random.Random(sysrng.getrandbits(128))  # seeded from the OS, not recorded
    combos = release_combos()
    families = args.families.split(",") if args.families else list(GENERATORS) + FORMULA_FAMILIES
    records = []
    for family in families:
        pool = list(combos[family])
        rng.shuffle(pool)
        chosen = 0
        while chosen < PER_FAMILY:
            if not pool:
                raise SystemExit(f"could not generate enough {family} instances")
            combo = pool.pop()
            data = None
            for _ in range(3):
                if family in FORMULA_FAMILIES:
                    data = generate_formula_family(family, combo, rng)
                else:
                    data = generate(family, combo, rng.randrange(10**6, 2**31))
                if data is None:
                    continue
                aps = data["atomic_propositions"]
                key = lambda tr: tuple(tuple(tr[a]) for a in aps)  # noqa: E731
                if {key(t) for t in data["positive_traces"]} & {key(t) for t in data["negative_traces"]}:
                    data = None
                    continue
                break
            if data is None:
                continue  # generator failed for this combination; draw another
            chosen += 1
            gen_size = None
            if data.get("generating_formula"):
                node = parse(balanced(data["generating_formula"]), set(data["atomic_propositions"]))
                if Encoded(data).separates(node):
                    gen_size = node_count(node)
                elif family in FORMULA_FAMILIES:
                    raise SystemExit(f"sampled traces disagree with the formula ({family}, {combo})")
            rec = {"family": family, "params": {k: (int(v) if str(v).isdigit() else v) for k, v in combo}}
            rec.update(encode(data))
            rec["generating_formula_size"] = gen_size
            rec["best_known_size"] = None
            records.append(rec)
            print(family, rec["params"], "generating size", gen_size, flush=True)
    rng.shuffle(records)
    existing = []
    if args.append and (HERE / "instances.json").exists():
        existing = json.loads((HERE / "instances.json").read_text())["instances"]
    start = len(existing)
    for i, rec in enumerate(records):
        rec["id"] = f"t{start + i:02d}"
    out = {"note": "Hidden test instances; see eval/test/build_instances.py. Traces are one bit-string per proposition.",
           "instances": existing + [{"id": r.pop("id"), **r} for r in records]}
    (HERE / "instances.json").write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {len(out['instances'])} hidden instances ({len(records)} new)")


if __name__ == "__main__":
    main()
