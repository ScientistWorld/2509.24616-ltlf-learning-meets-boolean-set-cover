#!/usr/bin/env python3
"""Summarize saved audit scores, with no learner or hidden evaluator execution.

This is audit analysis, not candidate code. The cohort is the nominated Bolt
result from each successful scenario, including three reference repeats. Future
leaderboard attempts can change standard deviations and numerical rank gaps.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
RT = ROOT / 'redteam'


def read(path):
    return json.loads(path.read_text())


def main():
    reference = read(RT / 'reference_existing_scores_test.json')['experiments']
    config = read(ROOT / 'scoring/reference.json')['experiments']
    variants = read(RT / 'audit_plan.json')['variants']
    attempts, failures = {}, {}
    for name in variants:
        folder = RT / name
        execution = read(folder / 'execution.json')
        if execution.get('hidden_test_failed'):
            failures[name] = execution
            continue
        scores = read(folder / 'scores_test.json')['experiments']
        attempts[name] = {
            'metrics': {exp: values['results']['bolt'] for exp, values in scores.items()},
            'methods_written': {
                exp: sorted(values['results']) for exp, values in scores.items()
            },
            'test_exit_code': execution['commands'][-1]['exit_code'],
            'candidate_wall_seconds': execution.get('candidate_wall_seconds'),
            'learner_commands': [c for c in execution['commands']
                                 if c['command'][0] == 'python3'],
        }

    scales = {}
    for exp, experiment in config.items():
        scales[exp] = {}
        for metric, metadata in experiment['metrics'].items():
            if not metadata['coefficient']:
                continue
            values = [attempt['metrics'][exp][metric] for attempt in attempts.values()]
            scales[exp][metric] = statistics.pstdev(values)

    for name, attempt in attempts.items():
        contributions = {}
        all_equal = True
        no_worse = True
        for exp, experiment in config.items():
            contributions[exp] = {}
            for metric, metadata in experiment['metrics'].items():
                coefficient = abs(metadata['coefficient'])
                if not coefficient:
                    continue
                ref = reference[exp]['results']['bolt'][metric]
                value = attempt['metrics'][exp][metric]
                direction = 1 if metadata['higher_is_better'] else -1
                gain = direction * (value - ref)
                all_equal &= abs(gain) < 1e-12
                no_worse &= gain >= -1e-12
                scale = scales[exp][metric]
                contributions[exp][metric] = (
                    experiment['weight'] * coefficient * gain / scale if scale else 0.0
                )
        attempt['rank_delta_audit_cohort'] = sum(
            value for metrics in contributions.values() for value in metrics.values()
        )
        attempt['rank_contributions'] = contributions
        attempt['relation_independent_of_nonzero_metric_scales'] = (
            'exact tie' if all_equal else 'dominates reference' if no_worse else 'tradeoff or worse'
        )

    # Syntax-tree sizes are measured from formulas, never copied self-reports.
    spec = importlib.util.spec_from_file_location('audit_visible_parser', ROOT / 'eval/train/evaluate.py')
    evaluator = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = evaluator
    spec.loader.exec_module(evaluator)
    formula_sizes = {}
    for name in attempts:
        rows = read(RT / name / 'bolt_results.json')['results']
        formula_sizes[name] = {
            row['instance']: evaluator.parse_formula(row['formula']).size()
            if row.get('formula') else None for row in rows
        }

    seeds = [attempts['reference_seed' + str(i)] for i in range(3)]
    spread = {
        exp: {
            metric: max(seed['metrics'][exp][metric] for seed in seeds)
            - min(seed['metrics'][exp][metric] for seed in seeds)
            for metric in scales[exp]
        } for exp in scales
    }
    result = {
        'normalization': {
            'cohort': 'Bolt result from each successful scenario; three reference repeats included',
            'cohort_size': len(attempts),
            'standard_deviation': 'population, computed over this audit cohort',
            'formula': 'sum(experiment.weight * abs(coefficient) * directed(value-reference) / stddev)',
            'reference': 'redteam/reference_existing_scores_test.json',
            'warning': 'Future cohort normalization is unknown; use metric dominance for invariant conclusions.',
            'scales': scales,
        },
        'reference_spread': spread,
        'attempts': attempts,
        'failures_without_numeric_scores': failures,
        'formula_ast_sizes': formula_sizes,
    }
    (RT / 'summary.json').write_text(json.dumps(result, indent=2) + '\n')
    metrics = list(scales['selected_benchmarks'])
    with (RT / 'summary.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['scenario', 'rank_delta_audit_cohort', *metrics])
        for name, attempt in attempts.items():
            values = attempt['metrics']['selected_benchmarks']
            writer.writerow([name, attempt['rank_delta_audit_cohort'],
                             *[values[m] for m in metrics]])
    print(f'{len(attempts)} scored scenarios; {len(failures)} failure without a score.')
    for name, attempt in attempts.items():
        print(f"{name}: {attempt['rank_delta_audit_cohort']:+.6f}")


if __name__ == '__main__':
    main()
