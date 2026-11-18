r"""Build actual A/B/C201 comparison data from the saved SWMM runs.

Input paths: --root contains A.inp, C.inp and C.json; --run contains the
new B.inp/B.metrics.json and fresh A.metrics.json. --out sets CSV/JSON output.
Example: python common.py --root C:\BC --run r --out d
No inferred or manuscript-adjusted node values are used.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import os
import struct
from pathlib import Path
from swmm.toolkit import output as so, shared_enum as E
import sys
PACKAGE_RUN = Path(__file__).resolve().parents[2] / "run"
if PACKAGE_RUN.is_dir(): sys.path.insert(0, str(PACKAGE_RUN))
from swmm_io import Inp, parse_model
from costs import replacement, barrels, volume


def atomic(path, payload):
    temporary = path.with_name(path.name+'.tmp')
    with temporary.open('wb') as f:
        f.write(payload); f.flush(); os.fsync(f.fileno())
    temporary.replace(path)


def write(path, rows):
    if not rows:
        raise ValueError(f'Empty export: {path}')
    stream = io.StringIO(newline='')
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
    atomic(path, stream.getvalue().encode('utf-8-sig'))


def avg(values):
    return math.fsum(values)/len(values)


def group(delta, tolerance):
    return 'Improved' if delta > tolerance else 'Worsened' if delta < -tolerance else 'Within tolerance'


def validate_binary(path):
    """Reject truncated native output before entering the C output-reader API."""
    size = path.stat().st_size
    if size < 52:
        raise ValueError(f'Incomplete binary output: {path}; rerun the unchanged INP')
    with path.open('rb') as f:
        magic = struct.unpack('<i', f.read(4))[0]
        f.seek(-24, 2)
        ids, inputs, results, periods, error, end_magic = struct.unpack('<6i', f.read(24))
    if magic != 516114522 or end_magic != magic or error != 0 or periods != 180 or not (0 < ids < inputs < results < size-24):
        raise ValueError(f'Invalid or incomplete 3-hour SWMM output: {path}; rerun the unchanged INP')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=PACKAGE_RUN if PACKAGE_RUN.is_dir() else Path(__file__).resolve().parent)
    p.add_argument('--run', default='r')
    p.add_argument('--out', default='d')
    a = p.parse_args()
    root, run, dst = a.root.resolve(), a.root/a.run, a.root/a.out
    dst.mkdir(parents=True, exist_ok=True)
    bases = {'A': (run/'A', run/'A.metrics.json'), 'B': (run/'B', run/'B.metrics.json'),
             'C201': (root/'C', root/'C.json')}
    metrics = {m: json.loads(j.read_text()) for m, (_, j) in bases.items()}
    models = {m: Inp(base.with_suffix('.inp').read_text()) for m, (base, _) in bases.items()}
    geo = {m: parse_model(inp) for m, inp in models.items()}
    node_data = {m: {r['Node']: r for r in value['nodes']} for m, value in metrics.items()}
    common = sorted(set.intersection(*(set(v) for v in node_data.values())) - {"341","342","343","344","345","346","348","349","350"})
    assert len(common) == 521
    assert len(common) == 521
    common_set = set(common)
    coords = models['A'].rows('[COORDINATES]')
    baseline_pipes = geo['A'][1]
    for model in models:
        assert models[model].blocks['[TIMESERIES]'] == models['A'].blocks['[TIMESERIES]']
        assert models[model].blocks['[RAINGAGES]'] == models['A'].blocks['[RAINGAGES]']
        assert set(geo[model][0]) == set(coords)
        assert set(geo[model][1]) == set(baseline_pipes)
        for key, pipe in geo[model][1].items():
            old = baseline_pipes[key]
            assert {pipe['u'], pipe['v']} == {old['u'], old['v']}
            assert pipe['length'] == old['length']
    nodes, allnodes, summary, events = [], [], [], []
    for node in sorted(coords):
        row = {'Node': node, 'X': float(coords[node][1]), 'Y': float(coords[node][2]), 'Common521': int(node in common_set)}
        for model in bases:
            vals = node_data[model].get(node)
            row[model+'_Type'] = geo[model][0][node]['kind']
            row[model+'_Invert_ft'] = geo[model][0][node]['invert']
            row[model+'_Depth_ft'] = vals['MaximumPondedDepth_ft'] if vals else None
            row[model+'_Time_h'] = vals['HoursFlooded'] if vals else None
            row[model+'_Final_ft'] = vals['FinalPondedDepth_ft'] if vals else None
        allnodes.append(row)
        if node in common_set:
            nodes.append(row)
    pipe_rows = []
    for key, old in baseline_pipes.items():
        row = {'Pipe': key, 'From': old['u'], 'To': old['v'], 'Length_ft': old['length'], 'Barrels': barrels(old),
            'FromX': float(coords[old['u']][1]), 'FromY': float(coords[old['u']][2]),
            'ToX': float(coords[old['v']][1]), 'ToY': float(coords[old['v']][2])}
        for model in bases:
            pipe = geo[model][1][key]
            row[model+'_mm'] = pipe['diameter']*304.8
            row[model+'_Cost_USD'] = replacement(old, pipe['diameter'])
            row[model+'_Added_m3'] = math.pi/4*old['length']*barrels(old)*(pipe['diameter']**2-old['diameter']**2)*.3048**3
            row[model+'_Extrapolated'] = int(row[model+'_Cost_USD'] > 0 and not (12 <= pipe['diameter']*12 <= 54))
        pipe_rows.append(row)
    for model in bases:
        rows = [node_data[model][node] for node in common]
        m = metrics[model]
        summary.append({'Model': model, 'ComparedNodes': len(common),
            'MeanPeak_ft': avg([r['MaximumPondedDepth_ft'] for r in rows]),
            'MaxPeak_ft': max(r['MaximumPondedDepth_ft'] for r in rows),
            'MeanTime_h': avg([r['HoursFlooded'] for r in rows]),
            'MaxTime_h': max(r['HoursFlooded'] for r in rows),
            'NativeJunctionCount': m['junction_count'],
            'NativeMeanPeak_ft': m['mean_maximum_ponded_depth_ft'],
            'NativeMeanTime_h': m['mean_hours_flooded'],
            'ReplacementCost_USD': math.fsum(r[model+'_Cost_USD'] for r in pipe_rows),
            'AddedVolume_m3': math.fsum(r[model+'_Added_m3'] for r in pipe_rows),
            'EnlargedPipes': sum(r[model+'_Cost_USD'] > 0 for r in pipe_rows),
            'ExtrapolatedPipes': sum(r[model+'_Extrapolated'] for r in pipe_rows),
            'FinalPondedCommonNodes': sum(r['FinalPondedDepth_ft'] > 1e-6 for r in rows),
            'FlowError_pct': m['flow_continuity_error_pct'],
            'Nonconv_pct': m['steps_not_converging_pct'],
            'PassesB5pctScreen': abs(m['flow_continuity_error_pct']) <= 5 and abs(m['runoff_continuity_error_pct']) <= 5 and m['steps_not_converging_pct'] <= 5})
        validate_binary(bases[model][0].with_suffix('.out'))
        h = so.init()
        so.open(h, str(bases[model][0].with_suffix('.out')))
        try:
            nt, step = so.get_times(h, E.Time.NUM_PERIODS), so.get_times(h, E.Time.REPORT_STEP)
            rain = so.get_system_series(h, E.SystemAttribute.RAINFALL, 0, nt-1)
            flow = so.get_system_series(h, E.SystemAttribute.OUTFALL_FLOWS, 0, nt-1)
            depth, count = [0.]*nt, [0]*nt
            for i in range(so.get_proj_size(h)[1]):
                node = so.get_elem_name(h, E.ElementType.NODE, i)
                if node not in common_set:
                    continue
                full = float(geo[model][0][node]['row'][2])
                values = so.get_node_series(h, i, E.NodeAttribute.INVERT_DEPTH, 0, nt-1)
                for k, value in enumerate(values):
                    ponded = max(float(value)-full, 0.)
                    depth[k] += ponded/len(common)
                    count[k] += int(ponded > 1e-6)
            events.extend({'Model': model, 'Time_h': (k+1)*step/3600, 'Rain_in_h': float(rain[k]),
                'MeanPonded_ft': depth[k], 'PondedNodes': count[k], 'OutfallFlow_cfs': float(flow[k])} for k in range(nt))
        finally:
            so.close(h)
    rain_values = [[r['Rain_in_h'] for r in events if r['Model'] == model] for model in bases]
    assert rain_values[0] == rain_values[1] == rain_values[2]
    tolerance = {'Depth': .01, 'Time': 1/60}
    delta, classes, worst, comparisons = [], [], [], []
    for label, ref, target in [('AB', 'A', 'B'), ('AC', 'A', 'C201'), ('BC', 'B', 'C201')]:
        rows = []
        for node in nodes:
            depth = node[ref+'_Depth_ft']-node[target+'_Depth_ft']
            duration = node[ref+'_Time_h']-node[target+'_Time_h']
            rows.append({'Pair': label, 'Reference': ref, 'Target': target, 'Node': node['Node'], 'X': node['X'], 'Y': node['Y'],
                'RefDepth_ft': node[ref+'_Depth_ft'], 'TargetDepth_ft': node[target+'_Depth_ft'], 'Reduction_ft': depth,
                'RefTime_h': node[ref+'_Time_h'], 'TargetTime_h': node[target+'_Time_h'], 'Reduction_h': duration,
                'DepthClass': group(depth, tolerance['Depth']), 'TimeClass': group(duration, tolerance['Time']),
                'NewlyFlooded': int(node[ref+'_Time_h'] <= 1e-9 and node[target+'_Time_h'] > 1e-9)})
        delta.extend(rows)
        for metric, key in [('Depth','Reduction_ft'), ('Time','Reduction_h')]:
            classes.append({'Pair': label, 'Reference': ref, 'Target': target, 'Metric': metric,
                'Tolerance': tolerance[metric], 'ComparedNodes': len(rows),
                'Improved': sum(r[metric+'Class'] == 'Improved' for r in rows),
                'Worsened': sum(r[metric+'Class'] == 'Worsened' for r in rows),
                'WithinTolerance': sum(r[metric+'Class'] == 'Within tolerance' for r in rows),
                'MinReduction': min(r[key] for r in rows), 'MaxReduction': max(r[key] for r in rows),
                'NewlyFloodedNodes': sum(r['NewlyFlooded'] for r in rows)})
            ordered = sorted((r for r in rows if r[key] < -tolerance[metric]), key=lambda r: r[key])[:15]
            worst.extend({'Pair': label, 'Metric': metric, 'Rank': i+1, 'Node': r['Node'],
                'Increase': -r[key], 'Unit': 'ft' if metric == 'Depth' else 'h'} for i, r in enumerate(ordered))
        sr = next(s for s in summary if s['Model'] == ref)
        st = next(s for s in summary if s['Model'] == target)
        for key in ['MeanPeak_ft', 'MaxPeak_ft', 'MeanTime_h', 'MaxTime_h']:
            comparisons.append({'Pair': label, 'Reference': ref, 'Target': target, 'Metric': key,
                'ReferenceValue': sr[key], 'TargetValue': st[key], 'Reduction': sr[key]-st[key],
                'Reduction_pct': 100*(sr[key]-st[key])/sr[key] if sr[key] else None})
    for name, rows in [('nodes.csv', nodes), ('allnodes.csv', allnodes), ('summary.csv', summary), ('delta.csv', delta),
                       ('classes.csv', classes), ('pipes.csv', pipe_rows), ('event.csv', events), ('compare.csv', comparisons)]:
        write(dst/name, rows)
    if worst:
        write(dst/'worse.csv', worst)
    else:
        atomic(dst/'worse.csv', b'Pair,Metric,Rank,Node,Increase,Unit\n')
    meta = {'common_junctions': 521, 'all_node_ids': 531,
        'excluded_from_common': sorted(set(coords)-common_set),
        'new_C201_outfalls': ['341', '343', '344', '348', '350'], 'original_outfall': '347',
        'positive_difference': 'Reference minus target; positive means improvement in target',
        'depth_definition': 'Maximum node depth minus model full depth, floored at zero; zero for nodes not flooded',
        'duration_definition': 'Native SWMM timeFlooded statistic in hours within the shared 3-hour event',
        'classification_tolerance_depth_ft': tolerance['Depth'], 'classification_tolerance_time_h': tolerance['Time'],
        'threshold_interpretation': 'Descriptive plotting tolerances, not statistical significance or calibrated numerical uncertainty',
        'continuous_scale': 'Symmetric shared limits per metric, 99th percentile of absolute reductions across all 3 pairs; tails flagged',
        'C201_numerical_caution': '6.73% nonconverging steps exceeds B 5% screening limit; retained reference, comparative results provisional',
        'model_B_identity': 'New cost-constrained B; previous volume-constrained B is not plotted',
        'input_sha256': {m: hashlib.sha256(base.with_suffix('.inp').read_bytes()).hexdigest() for m, (base, _) in bases.items()}}
    with (run/'progress.csv').open(encoding='utf-8-sig') as f:
        search = list(csv.DictReader(f))
    book = {'summary': summary, 'nodes': nodes, 'allnodes': allnodes, 'delta': delta, 'classes': classes, 'search': search,
            'pipes': pipe_rows, 'comparisons': comparisons, 'worst': worst, 'metadata': meta}
    atomic(dst/'book.json', json.dumps(book, indent=2, allow_nan=False).encode())
    atomic(dst/'meta.json', json.dumps(meta, indent=2).encode())
    print(json.dumps({'summary': summary, 'classes': classes}, indent=2))


if __name__ == '__main__':
    main()
