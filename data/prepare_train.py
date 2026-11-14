#!/usr/bin/env python3
"""Extract the visible training instances from the paper's released benchmark suite.

Samples 8 parameter combinations per family (uniformly among the combinations
present in the release) for all ten benchmark families of the paper, and one
released instance for each combination.  Writes data/train/instances/<id>.json
in the standard benchmark format, with the answer fields of the release
(smallest_known_formula, generating_formula, ...) removed, plus
data/train/manifest.json.

The five families generated from a formula through the paper's automaton-based
sampler (Fixed_Formulas, SingleCounter, DoubleCounter, Nim,
Random_Conjuncts_from_Basis) use descriptive proposition names in the release
(e.g. counter_0, heap_0_1); they are renamed to a0..a{m-1} by a seeded random
permutation, recorded in the manifest, as in the hidden test.

Requires data/downloads/benchmarks.zip (scripts/download.sh).
"""

from __future__ import annotations

import json
import random
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ZIP = ROOT / "data" / "downloads" / "benchmarks.zip"
OUT_DIR = ROOT / "data" / "train"
# release folder -> id prefix (the first five come with dedicated instance generators)
FAMILIES = {"OrderedSequence": "ord", "Subword": "swd", "Subset": "sst", "Hamming": "ham",
            "RandomBooleanCombinationsofFactors": "rbc",
            "Fixed_Formulas": "fix", "SingleCounter": "sgc", "DoubleCounter": "dbc", "Nim": "nim",
            "Random_Conjuncts_from_Basis": "rcj"}
FORMULA_FAMILIES = {"Fixed_Formulas", "SingleCounter", "DoubleCounter", "Nim", "Random_Conjuncts_from_Basis"}
PER_FAMILY = 8
SAMPLING_SEED = 20261112
DROP = {"smallest_known_formula", "generating_formula", "generating_seed", "original_repository", "name"}


def params_of(name: str) -> dict[str, int]:
    return {k: int(v) for k, v in re.findall(r"([a-z_]+)=(\d+)", name.split("/", 1)[1])}


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
    else:  # Nim: heaps=..tokens=..; Random_Conjuncts_from_Basis: conjuncts=.._atomic_propositions=.._seed=..
        for k, v in re.findall(r"([a-z_]+?)=(\d+)", base.replace("tokens", "_tokens")):
            k = k.strip("_")
            if k != "seed":
                out[k] = int(v)
    return out


def rename(data: dict, rng: random.Random) -> dict:
    aps = list(data["atomic_propositions"])
    perm = list(range(len(aps)))
    rng.shuffle(perm)
    mapping = {ap: f"a{perm[k]}" for k, ap in enumerate(aps)}
    for key in ("positive_traces", "negative_traces"):
        data[key] = [{mapping[ap]: tr[ap] for ap in aps} for tr in data[key]]
    data["atomic_propositions"] = sorted(mapping.values(), key=lambda a: int(a[1:]))
    return mapping


def main() -> None:
    if not SOURCE_ZIP.exists():
        raise SystemExit(f"Missing {SOURCE_ZIP}; run scripts/download.sh first.")
    rng = random.Random(SAMPLING_SEED)
    inst_dir = OUT_DIR / "instances"
    inst_dir.mkdir(parents=True, exist_ok=True)
    for old in inst_dir.glob("*.json"):
        old.unlink()
    manifest = {"source": "SynthesisLab/LTLf_Learning_Benchmarks release benchmarks.zip",
                "sampling_seed": SAMPLING_SEED, "instances": []}
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        names = [n for n in archive.namelist() if n.endswith(".json") and not n.endswith("/formulas.json")]
        for family in FAMILIES:
            by_combo: dict[tuple, list[str]] = {}
            for name in names:
                if name.split("/")[0] != family:
                    continue
                if family in FORMULA_FAMILIES:
                    p = formula_family_params(name)
                else:
                    p = params_of(name)
                    p.pop("seed", None)
                by_combo.setdefault(tuple(sorted(p.items())), []).append(name)
            combos = rng.sample(sorted(by_combo), PER_FAMILY)
            for k, combo in enumerate(combos):
                source = rng.choice(sorted(by_combo[combo]))
                data = json.loads(archive.read(source))
                for key in DROP:
                    data.pop(key, None)
                if family in FORMULA_FAMILIES:
                    params = formula_family_params(source)
                else:
                    params = params_of(source)
                    params.pop("seed", None)
                data["family"] = family
                data["parameters"] = params
                ident = f"{FAMILIES[family]}{k}"
                entry = {"id": ident, "file": f"data/train/instances/{ident}.json", "family": family,
                         "parameters": params, "source_file": source}
                if family in FORMULA_FAMILIES:
                    entry["proposition_renaming"] = rename(data, rng)
                    data["atomic_propositions"] = list(data["atomic_propositions"])
                (ROOT / entry["file"]).write_text(json.dumps(data, separators=(",", ":")))
                manifest["instances"].append(entry)
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {len(manifest['instances'])} training instances")


if __name__ == "__main__":
    main()
