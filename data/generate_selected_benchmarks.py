#!/usr/bin/env python3
"""Generate a small, tracked benchmark subset for the Bolt reproduction."""

from __future__ import annotations

import json
import random
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))
from ltlf_eval import accepts, parse_formula  # noqa: E402


def random_trace(aps: list[str], length: int, rng: random.Random, true_prob: float) -> dict[str, list[int]]:
    return {ap: [1 if rng.random() < true_prob else 0 for _ in range(length)] for ap in aps}


def make_instance(
    name: str,
    formula: str,
    aps: list[str],
    length: int,
    n_pos: int,
    n_neg: int,
    seed: int,
    true_prob: float,
    out_dir: Path,
) -> None:
    rng = random.Random(seed)
    node = parse_formula(formula)
    pos: list[dict[str, list[int]]] = []
    neg: list[dict[str, list[int]]] = []
    attempts = 0
    while len(pos) < n_pos or len(neg) < n_neg:
        attempts += 1
        if attempts > 200_000:
            raise RuntimeError(f"Could not sample enough traces for {name}")
        trace = random_trace(aps, length, rng, true_prob)
        ok = accepts(node, [trace])[0]
        if ok and len(pos) < n_pos:
            pos.append(trace)
        elif not ok and len(neg) < n_neg:
            neg.append(trace)

    data = {
        "positive_traces": pos,
        "negative_traces": neg,
        "smallest_known_formula": formula,
        "generating_formula": formula,
        "generating_seed": seed,
        "original_repository": "procedural subset generated for reproduction of Bolt paper",
        "name": name,
        "atomic_propositions": aps,
        "number_atomic_propositions": len(aps),
        "number_traces": len(pos) + len(neg),
        "number_positive_traces": len(pos),
        "number_negative_traces": len(neg),
        "max_length_traces": length,
        "trace_type": "finite",
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{name}.json").write_text(json.dumps(data, indent=2))


def main() -> None:
    out = Path("data/selected_benchmarks")
    tasks = [
        ("subset_4ap_len16", "(F (a0)) & ((F (a1)) & ((F (a2)) & (F (a3))))", ["a0", "a1", "a2", "a3"], 16, 8, 8, 11, 0.18),
        ("subset_5ap_len16", "(F (a0)) & ((F (a1)) & ((F (a2)) & ((F (a3)) & (F (a4)))))", ["a0", "a1", "a2", "a3", "a4"], 16, 8, 8, 12, 0.16),
        ("subword_4ap_len16", "F ((a0) & (X[!] (F ((a1) & (X[!] (F ((a2) & (X[!] (F (a3))))))))))", ["a0", "a1", "a2", "a3"], 16, 8, 8, 13, 0.26),
        ("ordered_sequence_4ap_len16", "(a0) U ((a1) U ((a2) U (a3)))", ["a0", "a1", "a2", "a3"], 16, 8, 8, 14, 0.45),
        ("boolean_factors_len16", "((F ((a0) & (X[!] (a1)))) & (F ((a2) & (X[!] (a3))))) | (G ((a4) | (a5)))", ["a0", "a1", "a2", "a3", "a4", "a5"], 16, 8, 8, 15, 0.35),
        ("hamming_like_len16", "(G (a0)) & ((F (a1)) & (F (a2)))", ["a0", "a1", "a2"], 16, 5, 12, 16, 0.75),
    ]
    for task in tasks:
        make_instance(*task, out_dir=out)
    manifest = {"instances": [str(p) for p in sorted(out.glob("*.json")) if p.name != "manifest.json"]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
