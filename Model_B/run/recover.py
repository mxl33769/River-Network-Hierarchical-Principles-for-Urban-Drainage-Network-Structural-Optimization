"""Rebuild exports from a trusted optimization checkpoint and generation snapshots.

Run: python recover.py --run r
This does not evaluate new designs or change the algorithm, results, or RNGs.
Only use pickle checkpoints that you created or obtained from a trusted source.
"""
import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import os
import pickle
from pathlib import Path
import numpy as np
from records import FIELDS, METRICS, front_indices, hv2, clean

ROOT = Path(__file__).resolve().parent


def atomic(path, payload):
    temporary = path.with_name(path.name + '.tmp')
    with temporary.open('wb') as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(path)


def csv_bytes(fields, rows):
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue().encode('utf-8')


def text(value):
    return '' if value is None else str(value)


def equal(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)
    return a == b


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--run', type=Path, default=ROOT/'r')
    args = ap.parse_args()
    run = args.run.resolve()
    checkpoint = run/'state.pkl.gz'
    original = checkpoint.read_bytes()
    state = pickle.loads(gzip.decompress(original))
    algo = state['algorithm']
    problem, recorder = algo.problem, algo.problem.recorder
    keys = sorted(recorder.ids, key=recorder.ids.get)
    assert set(keys) == set(recorder.rows) == set(problem.cache)
    assert [recorder.ids[k] for k in keys] == [f'e{i:05d}' for i in range(len(keys))]
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest() == h
               for n, h in state['signature']['source_sha256'].items())
    baseline = problem.cache[tuple([0]*len(problem.design.ids))]
    scale = np.asarray([baseline[m] if baseline[m] > 1e-12 else 1 for m in METRICS])
    rows, genes = [], []
    for key in keys:
        record, cached = recorder.rows[key], problem.cache[key]
        assert record['evaluation_id'] == recorder.ids[key]
        assert bool(record['feasible']) == bool(cached['success'])
        assert record['input_sha256'] == cached.get('input_sha256', '')
        for metric in METRICS:
            assert equal(record[metric], clean(cached.get(metric))), (record['evaluation_id'], metric)
        assert equal(record['replacement_cost_usd'], problem.design.cost(key))
        assert equal(record['added_volume_ft3'], problem.design.added_volume(key))
        assert record['enlarged_pipes'] == np.count_nonzero(key)
        assert record['replacement_cost_usd'] <= problem.design.budget + 1e-6
        assert record['enlarged_pipes'] <= problem.design.max_count
        assert all(0 <= v < len(problem.design.choices[i]) for i, v in enumerate(key))
        rows.append({field: record[field] for field in FIELDS})
        genes.append({'evaluation_id': record['evaluation_id'], **dict(zip(problem.design.ids, map(int, key)))})
    snapshots = [json.loads(p.read_text()) for p in sorted((run/'gen').glob('g*.json'))]
    assert [s['summary']['generation'] for s in snapshots] == list(range(1, algo.n_gen))
    by_id = {recorder.ids[k]: k for k in keys}
    for snapshot in snapshots:
        summary = snapshot['summary']
        generation = summary['generation']
        seen = [k for k in keys if recorder.rows[k]['first_generation'] <= generation]
        valid = [k for k in seen if problem.cache[k]['success']]
        assert len(seen) == summary['unique_designs_including_A']
        assert len(valid) == summary['feasible_unique_designs']
        assert len(seen)-len(valid) == summary['rejected_unique_designs']
        objectives = np.asarray([[problem.cache[k][m] for m in METRICS] for k in valid])
        front = front_indices(objectives)
        ordered = sorted(front, key=lambda i: (float(np.linalg.norm(objectives[i]/scale)),
                                               problem.design.cost(valid[i]), valid[i]))
        assert [r['evaluation_id'] for r in snapshot['archive']] == [recorder.ids[valid[i]] for i in ordered]
        assert equal(summary['best_depth_ft'], float(objectives[:, 0].min()))
        assert equal(summary['best_duration_h'], float(objectives[:, 1].min()))
        assert equal(summary['hypervolume_A_normalized'], hv2(objectives[front]/scale))
        best = valid[ordered[0]]
        assert summary['compromise_id'] == recorder.ids[best]
        assert equal(summary['compromise_depth_ft'], problem.cache[best][METRICS[0]])
        assert equal(summary['compromise_duration_h'], problem.cache[best][METRICS[1]])
        assert len(snapshot['population']) == summary['population_size']
        for record in snapshot['population'] + snapshot['archive']:
            key = by_id[record['evaluation_id']]
            assert recorder.rows[key]['first_generation'] <= generation
            for metric in METRICS:
                assert equal(record[metric], recorder.rows[key][metric])
    tables = {'evals.csv': (FIELDS, rows),
              'genes.csv': (['evaluation_id']+problem.design.ids, genes),
              'pop.csv': (list(snapshots[0]['population'][0]), [r for s in snapshots for r in s['population']]),
              'hist.csv': (list(snapshots[0]['archive'][0]), [r for s in snapshots for r in s['archive']]),
              'progress.csv': (list(snapshots[0]['summary']), [s['summary'] for s in snapshots])}
    audit = {'method': 'Exports rebuilt from saved checkpoint records and generation snapshots; no new simulations or inferred records',
             'checkpoint_before_sha256': hashlib.sha256(original).hexdigest(),
             'completed_generations': algo.n_gen-1, 'unique_designs': len(keys),
             'all_generations_recomputed_and_verified': True, 'checkpoint_source_hashes_verified': True,
             'tables': {}}
    for name, (fields, records) in tables.items():
        path = run/name
        old = path.read_bytes()
        with path.open(encoding='utf-8-sig', newline='') as f:
            previous = list(csv.DictReader(f))
        key_fields = {'pop.csv': ['generation', 'slot'], 'hist.csv': ['generation', 'evaluation_id'],
                      'progress.csv': ['generation']}.get(name, ['evaluation_id'])
        identity = lambda r: tuple(text(r[k]) for k in key_fields)
        expected = {identity(r): {k: text(r[k]) for k in fields} for r in records}
        assert len(expected) == len(records)
        seen = set()
        for row in previous:
            key = identity(row)
            assert key in expected and key not in seen, (name, key)
            assert row == expected[key], (name, key, 'surviving row differs from checkpoint')
            seen.add(key)
        missing = sorted(set(expected)-seen)
        payload = csv_bytes(fields, records)
        atomic(path, payload)
        audit['tables'][name] = {'old_rows': len(previous), 'new_rows': len(records),
            'surviving_rows_verified': True, 'missing_rows_restored': len(missing), 'missing_keys': missing,
            'old_sha256': hashlib.sha256(old).hexdigest(), 'new_sha256': hashlib.sha256(payload).hexdigest()}
    jsonlines = ''.join(json.dumps({**r, 'indices': list(map(int, k))}, allow_nan=False)+'\n'
                        for r, k in zip(rows, keys)).encode()
    atomic(run/'evals.jsonl', jsonlines)
    # Only byte offsets change. The saved algorithm, evaluated designs, RNG states,
    # source/environment signature, and generation count remain untouched.
    audit['old_log_sizes'] = state['sizes']
    state['sizes'] = {n: (run/n).stat().st_size for n in [*tables, 'evals.jsonl']}
    atomic(checkpoint, gzip.compress(pickle.dumps(state, pickle.HIGHEST_PROTOCOL), compresslevel=3))
    audit['new_log_sizes'] = state['sizes']
    audit['checkpoint_after_sha256'] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    atomic(run/'recover.json', json.dumps(audit, indent=2).encode())
    print(json.dumps({k: v for k, v in audit.items() if k != 'tables'}, indent=2))
    print({name: (v['old_rows'], v['new_rows']) for name, v in audit['tables'].items()})


if __name__ == '__main__':
    main()
