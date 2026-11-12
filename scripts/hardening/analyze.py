#!/usr/bin/env python3
"""Summarise the hardening runs (aggregates only; per-instance data stays in eval/test/).

Reads the variant score files and per-instance details written by the train and
test evaluators, and reports for every variant: its metrics, paired differences
against the reference `bolt` (mean and 95% paired-bootstrap interval over
instances), the repeat spread of the reference and the baseline, CPU usage of
the reference against the budget, an illustrative normalised rank, and
per-family aggregates.
"""

from __future__ import annotations

import json
import math
import random
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTES = ROOT / "notes" / "hardening"
EXP = "budgeted_ltlf_learning"
CAP = 10.0
METRICS = {  # name: (coefficient, higher_is_better)
    "size_efficiency": (1.0, True),
    "solve_rate": (0.5, True),
    "size_ratio_geomean": (0.5, False),
}
SLICES = {
    "test": (NOTES / "scores_test_variants.json", ROOT / "eval" / "test" / "runs_hardening" / "details.json",
             ROOT / "scoring" / "scores_test.json", ROOT / "eval" / "test" / "runs" / "details.json"),
    "train": (NOTES / "scores_train_variants.json", NOTES / "train_runs" / "details.json",
              ROOT / "scoring" / "scores_train.json", ROOT / "outputs" / "train_runs" / "details.json"),
}


def per_instance(rows: list[dict]) -> dict[str, dict]:
    out = {}
    for r in rows:
        if r["valid"]:
            q = min(1.0, r["best_known_size"] / r["size"])
            lr = math.log(min(max(r["size"] / r["best_known_size"], 1.0), CAP))
        else:
            q, lr = 0.0, math.log(CAP)
        out[r["instance"]] = {"size_efficiency": q, "solve_rate": 1.0 if r["valid"] else 0.0,
                              "log_ratio": lr, "family": r["family"], "cpu_s": r.get("cpu_s")}
    return out


def paired(a: dict, b: dict, key: str, rng: random.Random) -> dict:
    ids = sorted(set(a) & set(b))
    diffs = [a[i][key] - b[i][key] for i in ids]
    boots = []
    for _ in range(5000):
        sample = [diffs[rng.randrange(len(diffs))] for _ in diffs]
        boots.append(sum(sample) / len(sample))
    boots.sort()
    return {"mean_diff": sum(diffs) / len(diffs), "ci95": [boots[124], boots[4874]],
            "better": sum(d > 1e-12 for d in diffs), "worse": sum(d < -1e-12 for d in diffs),
            "ties": sum(abs(d) <= 1e-12 for d in diffs)}


def rank_gains(results: dict) -> dict:
    stds = {m: statistics.pstdev([r[m] for r in results.values()]) or 1.0 for m in METRICS}
    ref = results["bolt"]
    gains = {}
    for name, r in results.items():
        g = 0.0
        for m, (coef, hib) in METRICS.items():
            d = r[m] - ref[m]
            g += abs(coef) * (d if hib else -d) / stds[m]
        gains[name] = g
    return {"cohort_std": stds, "gain_vs_bolt": gains}


def main() -> None:
    rng = random.Random(0)
    summary: dict = {}
    for slc, (scores_path, details_path, official_path, official_details) in SLICES.items():
        if not scores_path.exists() or not details_path.exists():
            continue
        results = json.loads(scores_path.read_text())["experiments"][EXP]["results"]
        details = json.loads(details_path.read_text())
        if "bolt" in details and "literal_cover" in details:
            # Offline combination of saved outputs: Bolt's answer when valid, else the
            # literal-cover answer (only if the two CPU times fit in one budget).
            lit = {r["instance"]: r for r in details["literal_cover"]}
            combo = []
            for r in details["bolt"]:
                alt = lit[r["instance"]]
                cpu = (r.get("cpu_s") or 0) + (alt.get("cpu_s") or 0)
                combo.append(r if r["valid"] or cpu > 20.5 else dict(alt, cpu_s=cpu))
            details["bolt_literal_fallback"] = combo
            n = len(combo)
            results["bolt_literal_fallback"] = {
                "size_efficiency": sum(per_instance(combo)[i]["size_efficiency"] for i in per_instance(combo)) / n,
                "solve_rate": sum(1.0 for r in combo if r["valid"]) / n,
                "size_ratio_geomean": math.exp(sum(v["log_ratio"] for v in per_instance(combo).values()) / n),
            }
        inst = {m: per_instance(rows) for m, rows in details.items()}
        block: dict = {"metrics": results, "rank": rank_gains(
            {k: v for k, v in results.items() if k not in ("crash", "null_answer", "forged_fields", "parallel_portfolio")})}
        if "bolt" in inst:
            block["paired_vs_bolt"] = {
                m: {key: paired(inst[m], inst["bolt"], key, rng) for key in ("size_efficiency", "solve_rate", "log_ratio")}
                for m in inst if m != "bolt"
            }
            cpus = sorted(v["cpu_s"] for v in inst["bolt"].values() if v["cpu_s"] is not None)
            block["bolt_cpu_s"] = {"max": cpus[-1], "p90": cpus[int(0.9 * (len(cpus) - 1))],
                                   "mean": sum(cpus) / len(cpus)}
            fam: dict = {}
            for m in inst:
                for v in inst[m].values():
                    f = fam.setdefault(v["family"], {}).setdefault(m, [])
                    f.append(v["size_efficiency"])
            block["family_size_efficiency"] = {f: {m: sum(x) / len(x) for m, x in ms.items()} for f, ms in fam.items()}
        if official_path.exists() and official_details.exists():
            off = json.loads(official_path.read_text())["experiments"][EXP]["results"]
            off_inst = {m: per_instance(rows) for m, rows in json.loads(official_details.read_text()).items()}
            block["official"] = off
            block["repeat_spread"] = {
                m: {k: abs(off[m][k] - results[m][k]) for k in METRICS}
                for m in off if m in results
            }
            block["repeat_instance_changes"] = {
                m: sum(abs(off_inst[m][i]["size_efficiency"] - inst[m][i]["size_efficiency"]) > 1e-12
                       for i in off_inst[m] if i in inst.get(m, {}))
                for m in off_inst if m in inst
            }
        summary[slc] = block
    NOTES.mkdir(parents=True, exist_ok=True)
    (NOTES / "summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    lines = ["# Hardening run summary (generated by scripts/hardening/analyze.py)", ""]
    for slc, block in summary.items():
        lines += [f"## {slc}", "", "| method | size_efficiency | solve_rate | size_ratio_geomean | rank gain vs bolt |",
                  "|---|---:|---:|---:|---:|"]
        for m, r in sorted(block["metrics"].items(), key=lambda kv: -kv[1]["size_efficiency"]):
            g = block["rank"]["gain_vs_bolt"].get(m)
            lines.append(f"| {m} | {r['size_efficiency']:.4f} | {r['solve_rate']:.4f} | {r['size_ratio_geomean']:.4f} | "
                         f"{'' if g is None else f'{g:+.3f}'} |")
        if "paired_vs_bolt" in block:
            lines += ["", "Paired size_efficiency difference vs bolt (mean, 95% bootstrap CI, better/worse/tie):", ""]
            for m, d in sorted(block["paired_vs_bolt"].items()):
                e = d["size_efficiency"]
                lines.append(f"- {m}: {e['mean_diff']:+.4f} [{e['ci95'][0]:+.4f}, {e['ci95'][1]:+.4f}] "
                             f"{e['better']}/{e['worse']}/{e['ties']}")
            lines += ["", f"bolt CPU seconds: {block['bolt_cpu_s']}"]
        if "repeat_spread" in block:
            lines += ["", f"Repeat spread (official rerun vs hardening run): {block['repeat_spread']}",
                      f"Instances whose size_efficiency changed on rerun: {block['repeat_instance_changes']}"]
        lines.append("")
    (NOTES / "summary.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
