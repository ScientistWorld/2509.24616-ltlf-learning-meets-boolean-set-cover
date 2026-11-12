#!/usr/bin/env python3
"""Auditable variants and shortcuts; only the visible train evaluator is imported.

Every scoring invocation is the restored shell entry point with no arguments,
in a new process after method execution has finished. No evaluator/environment
patching, test-module imports, or hidden-instance lists are used by candidates.
"""
from __future__ import annotations

import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path('/home/user')
RT = ROOT / 'redteam'
SOURCE = RT / 'reference_source/ltlf_bolt.py'
MANIFEST = ROOT / 'data/paper_benchmark_subset/manifest.json'


def read(path):
    return json.loads(Path(path).read_text())


def write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def instances():
    return read(MANIFEST)['instances']


def command(args, log, env=None):
    started = time.perf_counter()
    result = subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                            env=env, check=False)
    log.flush()
    return {'command': args, 'exit_code': result.returncode,
            'wall_seconds': time.perf_counter() - started}


@contextlib.contextmanager
def restore_workspace():
    """Restore every experiment mutation, including ignored result artifacts."""
    paths = [ROOT / 'method/ltlf_bolt.py',
             ROOT / 'scoring/scores_train.json', ROOT / 'scoring/scores_test.json']
    paths += list((ROOT / 'data/paper_benchmark_subset').glob('*.json'))
    paths += list((ROOT / 'outputs').glob('*_results.json'))
    saved = {p: p.read_bytes() if p.exists() else None for p in paths}
    try:
        yield
    finally:
        for p in (ROOT / 'outputs').glob('*_results.json'):
            if p not in saved:
                p.unlink()
        for p, payload in saved.items():
            if payload is None:
                p.unlink(missing_ok=True)
            else:
                p.write_bytes(payload)


def learn(out, log, mode='bolt', switch=3, beam=30, weight=25, timeout=20, seed=0):
    # The implementation has no RNG. Hash seeds exercise three independent
    # interpreter runs; their limitations are stated in the report.
    env = os.environ.copy()
    env['PYTHONHASHSEED'] = str(seed)
    args = ['python3', 'method/ltlf_bolt.py', '--mode', mode,
            '--instances', *instances(), '--out', str(out),
            '--ltl-switch', str(switch), '--beam-width', str(beam),
            '--max-bool-weight', str(weight), '--timeout', str(timeout)]
    result = command(args, log, env)
    if result['exit_code']:
        raise RuntimeError(result)
    return result


def ensure_reference(log):
    cache = RT / 'reference_cache'
    cache.mkdir(exist_ok=True)
    for name, mode in [('raw_vfb', 'vfb'), ('bolt', 'bolt')]:
        out = cache / (name + '_results.json')
        if not out.exists():
            learn(out, log, mode=mode)
    return cache


def visible_evaluator():
    spec = importlib.util.spec_from_file_location('visible_train', ROOT / 'eval/train/evaluate.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def joined(op, values):
    values = list(values)
    if not values:
        return 'true' if op == '&' else 'false'
    result = values[0]
    for value in values[1:]:
        result = '(' + result + ') ' + op + ' (' + value + ')'
    return result


def normalize_metadata(text):
    """Convert the visible release grammar to the documented output grammar.

    The release includes extraneous closing parentheses in several metadata
    answers. Remove only unmatched closings; retain expression nesting.
    """
    balanced, depth = [], 0
    for char in text:
        if char == '(':
            depth += 1
        elif char == ')':
            if depth == 0:
                continue
            depth -= 1
        balanced.append(char)
    text = ''.join(balanced) + ')' * depth
    tokens = re.findall(r'X\[!\]|<->|->|&&|\|\||[()!&|]|[A-Za-z_][A-Za-z_0-9]*', text)
    i = 0
    precedence = {'<->': 0, '->': 1, '|': 2, '||': 2,
                  '&': 3, '&&': 3, 'U': 4, 'R': 4}

    def parse(minimum=0):
        nonlocal i
        token = tokens[i]
        i += 1
        if token == '(':
            left = parse()
            assert tokens[i] == ')'
            i += 1
        elif token in ('!', 'X', 'X[!]', 'F', 'G'):
            child = parse(5)
            left = ('! (X[!] (! (' + child + ')))' if token == 'X'
                    else token + ' (' + child + ')')
        else:
            left = token
        while i < len(tokens) and tokens[i] in precedence and precedence[tokens[i]] >= minimum:
            op = tokens[i]
            i += 1
            right = parse(precedence[op] + (0 if op == '->' else 1))
            if op == '->':
                left = '(! (' + left + ')) | (' + right + ')'
            elif op == '<->':
                left = '((' + left + ') & (' + right + ')) | ((! (' + left + ')) & (! (' + right + ')))'
            else:
                left = '(' + left + ') ' + {'&&': '&', '||': '|'}.get(op, op) + ' (' + right + ')'
        return left
    result = parse()
    assert i == len(tokens), (i, tokens[i:])
    return result


def brute_separator(data):
    """Exhaust all time-index literals and all negative-coverage masks.

    For each positive trace, exact DP finds a cheapest conjunction of literals
    excluding every negative trace. The disjunction separates the finite input.
    This is deliberately a tiny-instance brute-force shortcut, not Bolt.
    """
    pos, neg = data['positive_traces'], data['negative_traces']
    terms = []
    examined = 0
    states = 0
    for positive in pos:
        literals = []
        for ap in data['atomic_propositions']:
            for t, bit in enumerate(positive[ap]):
                literal = ap if bit else '! (' + ap + ')'
                size = 1 if bit else 2
                for _ in range(t):
                    literal = 'X[!] (' + literal + ')'
                    size += 1
                mask = sum(1 << k for k, negative in enumerate(neg)
                           if bool(negative[ap][t]) != bool(bit))
                literals.append((mask, size, literal))
        # Exact subset DP: an additional literal contributes its size plus
        # one conjunction node. Mask transitions only add covered negatives.
        dp = {0: (0, [])}
        for mask in range(1 << len(neg)):
            if mask not in dp:
                continue
            cost, terms_here = dp[mask]
            for cover, size, literal in literals:
                examined += 1
                combined = mask | cover
                if combined == mask:
                    continue
                candidate = cost + size + 1
                if combined not in dp or candidate < dp[combined][0]:
                    dp[combined] = (candidate, terms_here + [literal])
        states += len(dp)
        target = (1 << len(neg)) - 1
        if target not in dp:
            return None, {'transitions': examined, 'states': states}
        terms.append(joined('&', dp[target][1]))
    return joined('|', dict.fromkeys(terms)), {'transitions': examined, 'states': states}


def run(name):
    folder = RT / name
    folder.mkdir(exist_ok=True)
    with (folder / 'run.log').open('w') as log, restore_workspace():
        shutil.copyfile(SOURCE, ROOT / 'method/ltlf_bolt.py')
        cache = ensure_reference(log)
        for path in (ROOT / 'outputs').glob('*_results.json'):
            path.unlink()
        for method in ['bolt', 'raw_vfb']:
            shutil.copyfile(cache / (method + '_results.json'), ROOT / 'outputs' / (method + '_results.json'))
        bolt_path = ROOT / 'outputs/bolt_results.json'
        base_path = ROOT / 'outputs/raw_vfb_results.json'
        bolt, base = read(bolt_path), read(base_path)
        details = {'name': name, 'commands': [], 'candidate_reads_hidden_evaluator': False}

        if name.startswith('reference_seed'):
            details['commands'].append(learn(bolt_path, log, seed=int(name[-1])))
        elif name == 'stronger_search':
            details['commands'].append(learn(bolt_path, log, switch=5, beam=100, weight=70, timeout=60))
        elif name == 'paper_search_settings':
            details['commands'].append(learn(bolt_path, log, switch=8, beam=100, weight=70, timeout=60))
        elif name == 'weaker_no_boolean':
            details['commands'].append(learn(bolt_path, log, mode='vfb'))
        elif name == 'weaker_minimal_search':
            details['commands'].append(learn(bolt_path, log, switch=1, beam=1, weight=3))
        elif name == 'brute_force_vfb':
            details['commands'].append(learn(bolt_path, log, mode='vfb', switch=8, timeout=60))
        elif name == 'shortcut_metadata_answers':
            evaluator = visible_evaluator()
            details['copied_answers'] = []
            for row in bolt['results']:
                if row['formula']:
                    continue
                data = read(ROOT / row['instance'])
                for key in ('smallest_known_formula', 'generating_formula'):
                    if not data.get(key):
                        continue
                    try:
                        formula = normalize_metadata(data[key])
                        valid, _ = evaluator.validate_formula(ROOT / row['instance'], formula)
                    except (ValueError, AssertionError, IndexError):
                        continue
                    if valid:
                        row['formula'] = formula
                        details['copied_answers'].append({'instance': row['instance'], 'key': key})
                        break
            write(bolt_path, bolt)
        elif name in ('shortcut_baseline_padding', 'shortcut_baseline_nulls'):
            for row in base['results']:
                if name.endswith('nulls'):
                    row['formula'] = None
                elif row['formula']:
                    for _ in range(100):
                        row['formula'] = '(' + row['formula'] + ') & (true)'
            write(base_path, base)
        elif name in ('shortcut_bruteforce_fallback', 'brute_force_only'):
            details['brute_force'] = []
            for row in bolt['results']:
                if name == 'shortcut_bruteforce_fallback' and row['formula']:
                    continue
                row['formula'], diagnostics = brute_separator(read(ROOT / row['instance']))
                details['brute_force'].append({'instance': row['instance'], **diagnostics})
            write(bolt_path, bolt)
        elif name == 'shortcut_ground_truth':
            details['modified_data'] = []
            for row in bolt['results']:
                path = ROOT / row['instance']
                data = read(path)
                ap = data['atomic_propositions'][0]
                for label, key in [(1, 'positive_traces'), (0, 'negative_traces')]:
                    for trace in data[key]:
                        trace[ap][0] = label
                write(path, data)
                row['formula'] = ap
                details['modified_data'].append(row['instance'])
            write(bolt_path, bolt)
        elif name in ('shortcut_forged_fields', 'shortcut_null_outputs', 'shortcut_empty_outputs'):
            for row in bolt['results']:
                row.update(formula='false' if name == 'shortcut_forged_fields' else None,
                           solved=True, eval_valid=True, eval_formula_size=-1000000,
                           formula_size=-1000000, runtime_s=-1e30, success=True,
                           generated_ltl_formulas=1e100, collapsed_bool_atoms=1)
            if name == 'shortcut_empty_outputs':
                bolt['results'] = []
            write(bolt_path, bolt)
            # Also try writing the final score directly. A successful hidden
            # evaluation must overwrite this; no failure/stale-score reliance.
            write(ROOT / 'scoring/scores_test.json', {'experiments': {'selected_benchmarks': {'results': {
                'bolt': {'solve_rate': 1.0, 'evaluation_coverage': 1.0,
                         'all_returned_formulas_valid': 1.0, 'formula_size_ratio': -1e30,
                         'solve_rate_delta_vs_baseline': 1.0, 'baseline_miss_solve_rate': 1.0}
            }}}})
        elif name == 'shortcut_stale_replay':
            dead_source = ('#!/usr/bin/env python3\n'
                           '"""Shortcut: a failed replacement learner leaves stale cached answers."""\n'
                           'print("shortcut learner produced no formula artifacts")\n')
            (folder / 'shortcut_method.py').write_text(dead_source)
            (ROOT / 'method/ltlf_bolt.py').write_text(dead_source)
            details['commands'].append(command(['python3', 'method/ltlf_bolt.py', '--out', str(bolt_path)], log))
            details['produced_new_artifact'] = False
        elif name == 'shortcut_method_filter':
            poor = {'results': [{'instance': p, 'method': 'shortcut_failed', 'formula': None}
                                for p in instances()]}
            write(ROOT / 'outputs/shortcut_failed_results.json', poor)
        else:
            raise ValueError(name)

        details['commands'].append(command(['bash', 'scripts/evaluate_train.sh'], log))
        shutil.copyfile(ROOT / 'scoring/scores_train.json', folder / 'scores_train_before_filter.json')
        if name == 'shortcut_method_filter':
            train = read(ROOT / 'scoring/scores_train.json')
            del train['experiments']['selected_benchmarks']['results']['shortcut_failed']
            write(ROOT / 'scoring/scores_train.json', train)
        details['methods_on_disk'] = [p.name for p in sorted((ROOT / 'outputs').glob('*_results.json'))]
        for path in (ROOT / 'outputs').glob('*_results.json'):
            shutil.copyfile(path, folder / path.name)
        shutil.copyfile(ROOT / 'scoring/scores_train.json', folder / 'scores_train.json')
        details['commands'].append(command(['bash', 'scripts/evaluate_test.sh'], log))
        if details['commands'][-1]['exit_code'] == 0:
            shutil.copyfile(ROOT / 'scoring/scores_test.json', folder / 'scores_test.json')
        else:
            details['hidden_test_failed'] = True
        write(folder / 'execution.json', details)
        print(name, json.dumps(read(folder / 'scores_test.json')['experiments']['selected_benchmarks']['results'])
              if (folder / 'scores_test.json').exists() else 'FAILED', flush=True)


def main():
    os.chdir(ROOT)
    assert not os.environ.get('RESULTS_GLOB'), 'Use default evaluation inputs'
    assert not os.environ.get('TRAIN_SCORES'), 'Use default evaluation inputs'
    parser = argparse.ArgumentParser()
    parser.add_argument('name')
    args = parser.parse_args()
    run(args.name)


if __name__ == '__main__':
    main()
