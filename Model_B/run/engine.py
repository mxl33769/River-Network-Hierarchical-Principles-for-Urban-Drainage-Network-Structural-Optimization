"""Isolated EPA SWMM run; invoked by optimize.py, or directly for validation.

python engine.py model.inp metrics.json
Writes model.rpt and model.out next to the input. Supports the US-unit model
provided for this study. No input parameter is modified by this runner.
"""
import json
import math
import re
import sys
import time
from pathlib import Path
from swmm_io import Inp, parse_model, model_units, require


def routing_nonconvergence(rpt):
    match = re.search(r'% of Steps Not Converging\s*:\s*([0-9.]+)', rpt)
    require(match is not None, 'Missing routing nonconvergence statistic in SWMM report')
    value = float(match.group(1))
    require(math.isfinite(value) and 0 <= value <= 100, 'Invalid routing nonconvergence statistic')
    return value


def run(inp_path):
    from swmm.toolkit import solver, shared_enum as E
    inp_path = Path(inp_path).resolve()
    model = Inp(inp_path.read_text(encoding='utf-8-sig'))
    nodes, _ = parse_model(model)
    flow, unit = model_units(model)
    require(unit == 'ft', 'This tested runner supports US-unit SWMM models only; SI needs explicit statistic-unit handling.')
    options = model.rows('[OPTIONS]')
    require(options.get('ALLOW_PONDING',['','NO'])[1].upper() == 'YES', 'ALLOW_PONDING YES required for ponded-depth objectives')
    junctions = {n:p for n,p in nodes.items() if p['kind']=='junction'}
    require(all(float(p['row'][5])>0 for p in junctions.values()), 'Positive ponding area required at every evaluated junction')
    start = time.monotonic()
    opened = started = False
    try:
        solver.swmm_open(str(inp_path), str(inp_path.with_suffix('.rpt')), str(inp_path.with_suffix('.out')))
        opened = True
        solver.swmm_start(True)
        started = True
        full_depths = {}
        for i in range(solver.project_get_count(E.ObjectType.NODE)):
            name = solver.project_get_id(E.ObjectType.NODE,i)
            if name in junctions:
                value = solver.node_get_parameter(i,E.NodeProperty.FULL_DEPTH)
                require(abs(value-float(junctions[name]['row'][2]))<1e-6,
                        f'SWMM automatically changed junction full depth at {name}; rejected to preserve A/B geometry')
                full_depths[name] = value
        steps = 0
        last_elapsed = 0.0
        while True:
            elapsed = solver.swmm_step()
            steps += 1
            if elapsed <= 0:
                break
            last_elapsed = elapsed
        # Statistics must be copied BEFORE swmm_end (otherwise API is unavailable).
        rows = []
        for i in range(solver.project_get_count(E.ObjectType.NODE)):
            node = solver.project_get_id(E.ObjectType.NODE,i)
            if node not in junctions:
                continue
            stats = solver.node_get_stats(i)
            duration = float(stats.timeFlooded)  # SWMM toolkit supplies hours.
            ponded = max(0.0,float(stats.maxDepth)-full_depths[node]) if duration>0 else 0.0
            require(math.isfinite(float(stats.maxDepth)) and math.isfinite(ponded) and math.isfinite(duration) and duration>=0,
                    f'Invalid node metric at {node}: maxDepth={stats.maxDepth}, timeFlooded={duration}')
            rows.append({'Node':node,'MaximumPondedDepth_ft':ponded,'HoursFlooded':duration,
                         'MaximumNodeDepth_ft':float(stats.maxDepth),
                         'FullDepth_ft':full_depths[node],
                         'FinalPondedDepth_ft':max(0.0,solver.node_get_result(i,E.NodeResult.DEPTH)-full_depths[node])})
        require(len(rows)==len(junctions),'Missing junction metrics')
        solver.swmm_end()
        started = False
        mass = list(map(float,solver.swmm_get_mass_balance()))
        version = solver.swmm_get_version()
        solver.swmm_report()
    finally:
        if started:
            try:solver.swmm_end()
            except Exception:pass
        if opened:solver.swmm_close()
    rpt=inp_path.with_suffix('.rpt').read_text(errors='replace')
    require('ERROR ' not in rpt,'SWMM report contains an ERROR')
    return {'success':True,'engine_version':version,'flow_units':flow,
            'steps_not_converging_pct':routing_nonconvergence(rpt),
            'mean_maximum_ponded_depth_ft':sum(r['MaximumPondedDepth_ft'] for r in rows)/len(rows),
            'mean_hours_flooded':sum(r['HoursFlooded'] for r in rows)/len(rows),
            'network_maximum_ponded_depth_ft':max(r['MaximumPondedDepth_ft'] for r in rows),
            'network_maximum_hours_flooded':max(r['HoursFlooded'] for r in rows),
            'junction_count':len(rows),'runoff_continuity_error_pct':mass[0],
            'flow_continuity_error_pct':mass[1],'steps':steps,
            'last_positive_elapsed_days':last_elapsed,'wall_seconds':time.monotonic()-start,
            'nodes_ponded_at_simulation_end':sum(r['FinalPondedDepth_ft']>1e-6 for r in rows),
            'warnings':[l.strip() for l in rpt.splitlines() if 'WARNING ' in l],
            'nodes':rows}


if __name__=='__main__':
    target=Path(sys.argv[2])
    try:
        result=run(sys.argv[1])
        target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    except Exception as exc:
        target.write_text(json.dumps({'success':False,'error':str(exc)},indent=2),encoding='utf-8')
        print(str(exc),file=sys.stderr)
        sys.exit(1)
