#!/usr/bin/env python3
"""Extract the visible training instances from the paper's released benchmark suite.

Samples 8 parameter combinations per family (uniformly among the combinations
present in the release) for the five families whose instance generators ship
with the benchmark repository, and one released seed for each combination.
Writes data/train/instances/<id>.json in the standard benchmark format, with the
answer fields of the release (smallest_known_formula, generating_formula, ...)
removed, plus data/train/manifest.json.

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
FAMILIES = {"OrderedSequence": "ord", "Subword": "swd", "Subset": "sst", "Hamming": "ham",
            "RandomBooleanCombinationsofFactors": "rbc"}
PER_FAMILY = 8
SAMPLING_SEED = 20261112
DROP = {"smallest_known_formula", "generating_formula", "generating_seed", "original_repository", "name"}


def params_of(name: str) -> dict[str, int]:
    return {k: int(v) for k, v in re.findall(r"([a-z_]+)=(\d+)", name.split("/", 1)[1])}


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
        names = [n for n in archive.namelist() if n.endswith(".json")]
        for family in FAMILIES:
            by_combo: dict[tuple, list[str]] = {}
            for name in names:
                if name.split("/")[0] != family:
                    continue
                p = params_of(name)
                p.pop("seed", None)
                by_combo.setdefault(tuple(sorted(p.items())), []).append(name)
            combos = rng.sample(sorted(by_combo), PER_FAMILY)
            for k, combo in enumerate(combos):
                source = rng.choice(sorted(by_combo[combo]))
                data = json.loads(archive.read(source))
                for key in DROP:
                    data.pop(key, None)
                params = params_of(source)
                params.pop("seed", None)
                data["family"] = family
                data["parameters"] = params
                ident = f"{FAMILIES[family]}{k}"
                rel = f"data/train/instances/{ident}.json"
                (ROOT / rel).write_text(json.dumps(data, separators=(",", ":")))
                manifest["instances"].append({"id": ident, "file": rel, "family": family,
                                              "parameters": params, "source_file": source})
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"wrote {len(manifest['instances'])} training instances")


if __name__ == "__main__":
    main()
