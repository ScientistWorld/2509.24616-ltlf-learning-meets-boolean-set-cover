#!/usr/bin/env python3
"""Extract the tracked reproduction subset from the paper benchmark release."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path


SOURCE_ZIP = Path("data/downloads/benchmarks.zip")
OUT_DIR = Path("data/paper_benchmark_subset")

SELECTED = [
    "DoubleCounter/1_5_16_42.json",
    "Fixed_Formulas/absence1_5_16_42.json",
    "Hamming/trace_length=16number_atomic_propositions=3number_negative_traces=5delta=1seed=40.json",
    "Nim/heaps=1tokens=1_5_16_42.json",
    "OrderedSequence/trace_length=16number_atomic_propositions=3size_sequence=3number_positive_traces=5number_negative_traces=5seed=40.json",
    "OrderedSequence/trace_length=16number_atomic_propositions=3size_sequence=4number_positive_traces=5number_negative_traces=5seed=41.json",
    "RandomBooleanCombinationsofFactors/trace_length=16number_atomic_propositions=3number_positive_traces=5number_negative_traces=5number_patterns=3seed=43.json",
    "SingleCounter/1_5_16_42.json",
    "Subset/trace_length=16number_atomic_propositions=5number_positive_traces=5number_negative_traces=5subset_size=3seed=40.json",
    "Subword/trace_length=16number_atomic_propositions=3number_positive_traces=5number_negative_traces=5subword_length=10seed=40.json",
]


def safe_name(name: str) -> str:
    return name.replace("/", "__")


def main() -> None:
    if not SOURCE_ZIP.exists():
        raise SystemExit(f"Missing {SOURCE_ZIP}; run scripts/download.sh first.")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"source": str(SOURCE_ZIP), "source_files": SELECTED, "instances": []}
    with zipfile.ZipFile(SOURCE_ZIP) as archive:
        available = set(archive.namelist())
        missing = [name for name in SELECTED if name not in available]
        if missing:
            raise SystemExit("Missing files in benchmark zip: " + ", ".join(missing))
        for source_name in SELECTED:
            data = json.loads(archive.read(source_name))
            data["reproduction_source_file"] = source_name
            out_path = OUT_DIR / safe_name(source_name)
            out_path.write_text(json.dumps(data, indent=2))
            manifest["instances"].append(str(out_path))
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
