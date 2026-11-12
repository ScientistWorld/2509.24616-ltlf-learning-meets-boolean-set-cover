#!/usr/bin/env python3
"""Build the hidden test instances (run once; the output eval/test/instances.json is kept).

Fresh samples from the paper's own instance generators
(data/downloads/LTLf_Learning_Benchmarks/Generating_Instances, fetched by
scripts/download.sh) over parameter combinations drawn uniformly from those in
the paper's released suite, 8 per family.  Seeds come from the OS random source
and are not recorded, so the instances cannot be regenerated or looked up in the
public release.  Only the traces and the size of the generating formula (an
upper bound on the separator size) are stored.
"""

from __future__ import annotations

import json
import re
import secrets
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from evaluate import Encoded, node_count, parse  # noqa: E402  (same directory)

GEN_DIR = ROOT / "data" / "downloads" / "LTLf_Learning_Benchmarks" / "Generating_Instances"
SOURCE_ZIP = ROOT / "data" / "downloads" / "benchmarks.zip"
GENERATORS = {
    "OrderedSequence": "gen_orderedsequence.py",
    "Subword": "gen_subword.py",
    "Subset": "gen_subset.py",
    "Hamming": "gen_Hamming.py",
    "RandomBooleanCombinationsofFactors": "gen_random_boolean_combinations_factors.py",
}
PER_FAMILY = 8


def release_combos() -> dict[str, list[tuple]]:
    combos: dict[str, set] = {f: set() for f in GENERATORS}
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        for name in archive.namelist():
            fam = name.split("/")[0]
            if fam not in combos or not name.endswith(".json"):
                continue
            p = dict(re.findall(r"([a-z_]+)=(\d+)", name.split("/", 1)[1]))
            p.pop("seed", None)
            combos[fam].add(tuple(sorted(p.items())))
    return {f: sorted(c) for f, c in combos.items()}


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
    rng = secrets.SystemRandom()
    combos = release_combos()
    records = []
    for family in GENERATORS:
        pool = list(combos[family])
        rng.shuffle(pool)
        chosen = 0
        while chosen < PER_FAMILY:
            if not pool:
                raise SystemExit(f"could not generate enough {family} instances")
            combo = pool.pop()
            data = None
            for _ in range(3):
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
                continue  # upstream generator failed for this combination; draw another
            chosen += 1
            gen_size = None
            if data.get("generating_formula"):
                node = parse(balanced(data["generating_formula"]), set(data["atomic_propositions"]))
                if Encoded(data).separates(node):
                    gen_size = node_count(node)
            rec = {"family": family, "params": {k: int(v) for k, v in combo}}
            rec.update(encode(data))
            rec["generating_formula_size"] = gen_size
            rec["best_known_size"] = None
            records.append(rec)
    rng.shuffle(records)
    for i, rec in enumerate(records):
        rec["id"] = f"t{i:02d}"
    out = {"note": "Hidden test instances; see eval/test/build_instances.py. Traces are one bit-string per proposition.",
           "instances": [{"id": r.pop("id"), **r} for r in records]}
    (HERE / "instances.json").write_text(json.dumps(out, separators=(",", ":")))
    print(f"wrote {len(records)} hidden instances")


if __name__ == "__main__":
    main()
