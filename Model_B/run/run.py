"""Run/resume cost-constrained Model B: python run.py.

Run folder: --out r. To test recovery: --pop 8 --gens 2 --stop 1,
then repeat the command without --stop. Only load your own checkpoints.
"""
import argparse
import gzip
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import pickle
import random
import shutil
import sys
import time
import numpy as np
import optimize as o
from records import jsonwrite

ROOT = Path(__file__).resolve().parent
LOGS = ['evals.csv', 'genes.csv', 'evals.jsonl', 'pop.csv', 'hist.csv', 'progress.csv']
SOURCE = ['A.inp', 'C.inp', 'optimize.py', 'costs.py', 'records.py', 'engine.py', 'swmm_io.py', 'run.py']


def signature(cfg):
    return {'config': cfg, 'python': sys.version,
            'packages': {k: importlib.metadata.version(k) for k in ['numpy', 'scipy', 'pymoo', 'swmm-toolkit']},
            'source_sha256': {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCE}}


def atomic(path, payload):
    temp = path.with_name(path.name + '.tmp')
    with temp.open('wb') as f:
        f.write(payload)
        f.flush()
        os.fsync(f.fileno())
    temp.replace(path)


def save(algo, out, sig):
    state = {'algorithm': algo, 'numpy_rng': np.random.get_state(),
             'python_rng': random.getstate(), 'signature': sig,
             'sizes': {n: (out/n).stat().st_size for n in LOGS if (out/n).exists()}}
    atomic(out/'state.pkl.gz', gzip.compress(pickle.dumps(state, pickle.HIGHEST_PROTOCOL), compresslevel=3))
    jsonwrite(out/'status.json', {'stage': 'optimization', 'completed_generations': algo.n_gen-1,
        'next_generation': algo.n_gen, 'resume': 'python run.py',
        'checkpoint_sha256': hashlib.sha256((out/'state.pkl.gz').read_bytes()).hexdigest()})


def export(algo, out, cfg):
    problem, d = algo.problem, algo.problem.design
    baseline = problem.cache[tuple([0]*len(d.ids))]
    keys = [k for k, v in problem.cache.items() if v['success']]
    F = np.asarray([[problem.cache[k][m] for m in o.METRICS] for k in keys])
    front = o.NonDominatedSorting().do(F, only_non_dominated_front=True)
    scale = np.asarray([baseline[m] if baseline[m] > 1e-12 else 1 for m in o.METRICS])
    order = sorted(front, key=lambda i: (float(np.linalg.norm(F[i]/scale)), d.cost(keys[i]), keys[i]))
    selected = keys[order[0]]
    rows = []
    for j, i in enumerate(order):
        key = keys[i]
        filename = f'P{j+1:03d}.inp'
        (out/'pf'/filename).write_text(d.render(key))
        rows.append({'File': filename, 'Selected': key == selected,
            'EvaluationID': problem.recorder.ids[key], 'Depth_ft': F[i, 0], 'Duration_h': F[i, 1],
            'Cost_USD': d.cost(key), 'AddedVolume_m3': d.added_volume(key)*.3048**3,
            'EnlargedPipes': int(np.count_nonzero(key)), 'Distance_A_normalized': float(np.linalg.norm(F[i]/scale))})
    o.write_csv(out/'front.csv', rows)
    target = out/'B.inp'
    target.write_text(d.render(selected))
    invariant = d.verify(target.read_text())
    fresh = o.simulate(target, cfg['simulation_timeout_seconds'])
    o.check_quality(fresh, cfg['continuity_error_limit_pct'], cfg['max_steps_not_converging_pct'])
    crosscheck = o.check_report(fresh, target.with_suffix('.rpt'))
    for metric in o.METRICS:
        o.require(abs(fresh[metric]-problem.cache[selected][metric]) < 1e-8, 'Fresh result differs from selected evaluation')
    o.write_csv(out/'B_nodes.csv', fresh['nodes'])
    changes = []
    for i, key in enumerate(d.ids):
        if selected[i]:
            p, diameter = d.pipes[key], float(d.choices[i][selected[i]])
            changes.append({'Pipe': key, 'A_ft': p['diameter'], 'B_ft': diameter,
                'New_mm': diameter*304.8, 'Length_ft': p['length'],
                'Barrels': o.barrel(p), 'Cost_USD': float(d.costs[i][selected[i]]),
                'AddedVolume_m3': float(d.volumes[i][selected[i]])*.3048**3,
                'Extrapolated': not (12 <= diameter*12 <= 54)})
    o.write_csv(out/'changes.csv', changes)
    o.write_csv(out/'comparison.csv', [{'Metric': m, 'A': baseline[m], 'B': fresh[m],
        'Reduction_pct': 100*(baseline[m]-fresh[m])/baseline[m] if baseline[m] else ''}
        for m in o.METRICS + ['network_maximum_ponded_depth_ft', 'network_maximum_hours_flooded']])
    jsonwrite(out/'checks.json', {**invariant, **crosscheck,
        'fresh_simulation_reproduced': True, 'generations': cfg['generations'],
        'unique_designs': len(problem.cache), 'feasible_designs': len(keys), 'pareto_designs': len(rows),
        'global_optimum_claimed': False, 'optimization_junction_count': 530,
        'baseline_depth_ft': baseline[o.METRICS[0]], 'baseline_duration_h': baseline[o.METRICS[1]],
        'selected_depth_ft': fresh[o.METRICS[0]], 'selected_duration_h': fresh[o.METRICS[1]],
        'flow_continuity_error_pct': fresh['flow_continuity_error_pct'],
        'steps_not_converging_pct': fresh['steps_not_converging_pct'],
        'selected_id': problem.recorder.ids[selected],
        'selection_rule': 'Minimum Euclidean distance of objectives normalized by A; replacement cost breaks ties'})
    jsonwrite(out/'status.json', {'stage': 'simulation_complete', 'completed_generations': cfg['generations']})
    print('FRESH VALIDATION COMPLETE', json.dumps(json.loads((out/'checks.json').read_text())), flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', default='r')
    ap.add_argument('--config', type=Path, default=ROOT/'run.json')
    ap.add_argument('--pop', type=int)
    ap.add_argument('--gens', type=int)
    ap.add_argument('--stop', type=int)
    args = ap.parse_args()
    cfg = json.loads(args.config.read_text())
    if args.pop:
        cfg['population_size'] = args.pop
    if args.gens:
        cfg['generations'] = args.gens
    o.require(cfg['population_size'] >= 4 and cfg['generations'] >= 2, 'Population >=4 and generations >=2 required')
    out = (ROOT/args.out).resolve()
    sig = signature(cfg)
    cp = out/'state.pkl.gz'
    if cp.exists():
        with gzip.open(cp, 'rb') as f:
            state = pickle.load(f)
        o.require(state['signature'] == sig, 'Code, model, settings or environment changed; choose a separate run')
        algo = state['algorithm']
        problem = algo.problem
        problem.out = out
        problem.recorder.out = out
        algo.callback.out = out
        for name, size in state['sizes'].items():
            with (out/name).open('r+b') as f:
                f.truncate(size)
        # Remove incomplete-generation artifacts, which are not part of the state.
        for path in (out/'raw_parts').glob('e*.zip'):
            if path.stem not in set(problem.recorder.ids.values()):
                path.unlink()
        for path in (out/'gen').glob('g*.json'):
            if int(path.stem[1:]) >= algo.n_gen:
                path.unlink()
        elapsed = json.loads((out/'gen'/f'g{algo.n_gen-1:03d}.json').read_text())['summary']['elapsed_seconds']
        problem.recorder.started = time.monotonic() - elapsed
        np.random.set_state(state['numpy_rng'])
        random.setstate(state['python_rng'])
        print('RESUMED generation', algo.n_gen, flush=True)
    else:
        o.require(not out.exists() or not any(out.iterdir()), 'Nonempty output folder without checkpoint')
        out.mkdir(parents=True, exist_ok=True)
        (out/'work').mkdir()
        (out/'pf').mkdir()
        jsonwrite(out/'config.json', cfg)
        design = o.Design((ROOT/'A.inp').read_text(), (ROOT/'C.inp').read_text(), cfg)
        (out/'A.inp').write_text(design.text)
        baseline = o.simulate(out/'A.inp', cfg['simulation_timeout_seconds'])
        o.check_quality(baseline, cfg['continuity_error_limit_pct'], cfg['max_steps_not_converging_pct'])
        o.check_report(baseline, out/'A.rpt')
        o.write_csv(out/'A_nodes.csv', baseline['nodes'])
        o.write_csv(out/'sizes.csv', design.audit)
        jsonwrite(out/'env.json', sig)
        jsonwrite(out/'allowance.json', {'replacement_budget_usd': design.budget,
            'reference_C201_cost_usd': design.reference_cost, 'cost_only_volume_not_constrained': True,
            'maximum_catalogue_diameter_mm': 2000, 'fixed_A_junction_clearances': True,
            'max_enlarged_pipes': design.max_count})
        problem = o.HydraulicProblem(design, cfg, out, baseline)
        algo = o.NSGA2(pop_size=cfg['population_size'], sampling=o.SparseSampling(),
            crossover=o.SBX(prob=.9, eta=15, vtype=float, repair=o.RoundingRepair()),
            mutation=o.PM(eta=20, prob=1.0, prob_var=1/len(design.ids), vtype=float, repair=o.RoundingRepair()),
            repair=o.AllowanceRepair(), eliminate_duplicates=True)
        algo.setup(problem, termination=('n_gen', cfg['generations']), seed=cfg['seed'], callback=o.Progress(out), verbose=False)
        print('BASELINE', json.dumps({m: baseline[m] for m in o.METRICS}), flush=True)
    (out/'work').mkdir(exist_ok=True)
    while algo.has_next():
        algo.next()
        save(algo, out, sig)
        generation = algo.n_gen-1
        if os.environ.get('BC_DURABLE') == '1' and (generation == 1 or generation % cfg['durable_every'] == 0):
            import snapshot
            snapshot.save(out)
        if args.stop == generation:
            print('STOPPED after complete generation', generation, flush=True)
            return
    export(algo, out, cfg)
    if os.environ.get('BC_DURABLE') == '1':
        import snapshot
        snapshot.save(out)


if __name__ == '__main__':
    main()
