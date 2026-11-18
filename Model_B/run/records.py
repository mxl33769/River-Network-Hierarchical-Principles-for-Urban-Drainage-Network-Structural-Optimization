"""Append-only scientific records; no change to search operators or SWMM physics."""
import csv
import hashlib
import json
import math
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting

METRICS=['mean_maximum_ponded_depth_ft','mean_hours_flooded']
FIELDS=['evaluation_id','seed','first_generation','engine_success','feasible','failure_stage','error',
        *METRICS,'network_maximum_ponded_depth_ft','network_maximum_hours_flooded',
        'runoff_continuity_error_pct','flow_continuity_error_pct','steps_not_converging_pct',
        'enlarged_pipes','added_volume_ft3','added_volume_m3','input_sha256','engine_version',
        'replacement_cost_usd','wall_seconds','recorded_utc','replayed','original_recorded_utc']

def clean(value):
    if isinstance(value,(np.integer,)):return int(value)
    if isinstance(value,(float,np.floating)):return float(value) if math.isfinite(value) else None
    if isinstance(value,dict):return {str(k):clean(v) for k,v in value.items()}
    if isinstance(value,(list,tuple,np.ndarray)):return [clean(v) for v in value]
    return value

def jsonwrite(path,data):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(clean(data),indent=2,allow_nan=False),encoding='utf-8')
    temporary.replace(path)

def append_csv(path,fields,rows):
    new=not path.exists()
    with path.open('a',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        if new:w.writeheader()
        w.writerows(rows)
        f.flush()

def front_indices(values):
    return NonDominatedSorting().do(np.asarray(values),only_non_dominated_front=True)

def hv2(points,reference=(1.1,1.1)):
    """Exact dominated hypervolume in 2D, using fixed A-normalized coordinates."""
    height=float(reference[1]);area=0.0
    for x,y in sorted((float(x),float(y)) for x,y in points):
        if x < reference[0] and y < height:
            area+=(reference[0]-x)*(height-y);height=y
    return area

class Recorder:
    def __init__(self,out,design,cfg):
        self.out=Path(out);self.design=design;self.cfg=cfg;self.ids={};self.rows={}
        self.started=time.monotonic();self.generation=1
        jsonwrite(self.out/'map.json',{'pipe_order':design.ids,
            'allowed_diameters_ft':[v.tolist() for v in design.choices],
            'added_volume_ft3_by_index':[v.tolist() for v in design.volumes],
            'replacement_cost_usd_by_index':[v.tolist() for v in design.costs]})

    def register(self,key):
        if key not in self.ids:self.ids[key]=f'e{len(self.ids):05d}'
        return self.ids[key]

    def record(self,key,data,artifacts,generation=None):
        eid=self.register(key)
        row={'evaluation_id':eid,'seed':self.cfg['seed'],
             'first_generation':self.generation if generation is None else generation,
             'engine_success':data.get('engine_success',data['success']),
             'feasible':data['success'],'failure_stage':data.get('failure_stage',''),
             'error':data.get('error',''),'enlarged_pipes':int(np.count_nonzero(key)),
             'added_volume_ft3':self.design.added_volume(key),
             'added_volume_m3':self.design.added_volume(key)*.3048**3,
             'replacement_cost_usd':self.design.cost(key),
             'input_sha256':data.get('input_sha256',''),
             'recorded_utc':datetime.now(timezone.utc).isoformat(),
             'replayed':data.get('replayed',False),
             'original_recorded_utc':data.get('original_recorded_utc','')}
        for f in FIELDS:
            if f not in row:row[f]=data.get(f)
        row=clean(row);self.rows[key]=row
        append_csv(self.out/'evals.csv',FIELDS,[row])
        append_csv(self.out/'genes.csv',['evaluation_id']+self.design.ids,
                   [{'evaluation_id':eid,**dict(zip(self.design.ids,map(int,key)))}])
        with (self.out/'evals.jsonl').open('a',encoding='utf-8') as f:
            f.write(json.dumps({**row,'indices':list(map(int,key))},allow_nan=False)+'\n')
        # Every result is committed with its central directory intact. Rejected
        # SWMM runs retain any report they produced and their raw metrics/errors.
        parts=self.out/'raw_parts';parts.mkdir(exist_ok=True)
        temporary=parts/(eid+'.tmp')
        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as z:
            for suffix,payload in artifacts.items():
                z.writestr(eid+suffix,payload)
            z.writestr(eid+'.record.json',json.dumps({**row,'indices':list(map(int,key))},allow_nan=False))

        temporary.replace(parts/(eid+'.zip'))

    def generation_record(self,algorithm,cache,baseline):
        generation=int(algorithm.n_gen)
        rows=[]
        for slot,individual in enumerate(algorithm.pop):
            key=tuple(np.rint(individual.X).astype(int));raw=self.rows[key]
            rank=individual.get('rank');crowd=individual.get('crowding')
            rows.append({'generation':generation,'slot':slot,'evaluation_id':self.ids[key],
                         'feasible':raw['feasible'],'rank':rank,
                         'crowding':str(crowd) if crowd is not None and not math.isfinite(crowd) else crowd,
                         **{m:raw[m] for m in METRICS}})
        append_csv(self.out/'pop.csv',list(rows[0]),rows)
        keys=[k for k,v in cache.items() if v['success']]
        F=np.asarray([[cache[k][m] for m in METRICS] for k in keys])
        front=front_indices(F)
        scale=np.asarray([baseline[m] if baseline[m]>1e-12 else 1 for m in METRICS])
        ordered=sorted(front,key=lambda i:(float(np.linalg.norm(F[i]/scale)),self.design.cost(keys[i]),keys[i]))
        best=keys[ordered[0]]
        archive=[{'generation':generation,'evaluation_id':self.ids[keys[i]],
                  **{m:float(F[i,j]) for j,m in enumerate(METRICS)}} for i in ordered]
        append_csv(self.out/'hist.csv',list(archive[0]),archive)
        summary={'generation':generation,'seed':self.cfg['seed'],
                 'optimizer_evaluations':int(algorithm.evaluator.n_eval),
                 'unique_designs_including_A':len(cache),
                 'feasible_unique_designs':len(keys),'rejected_unique_designs':len(cache)-len(keys),
                 'archive_pareto_size':len(front),'population_size':len(rows),
                 'best_depth_ft':float(F[:,0].min()),'best_duration_h':float(F[:,1].min()),
                 'compromise_id':self.ids[best],
                 'compromise_depth_ft':cache[best][METRICS[0]],
                 'compromise_duration_h':cache[best][METRICS[1]],
                 'compromise_distance':float(np.linalg.norm(F[ordered[0]]/scale)),
                 'compromise_cost_usd':self.design.cost(best),
                 'compromise_added_volume_m3':self.design.added_volume(best)*.3048**3,
                 'hypervolume_A_normalized':hv2(F[front]/scale),
                 'elapsed_seconds':time.monotonic()-self.started}
        append_csv(self.out/'progress.csv',list(summary),[summary])
        (self.out/'best.inp').write_text(self.design.render(best),encoding='utf-8')
        jsonwrite(self.out/'best.json',summary)
        snapshots=self.out/'gen';snapshots.mkdir(exist_ok=True)
        jsonwrite(snapshots/f'g{generation:03d}.json',{'population':rows,'archive':archive,'summary':summary})
        self.generation=generation+1
        print(json.dumps(summary),flush=True)


def pack_raw(folder):
    """Assemble CSVs and raw ZIP from immutable candidate/generation records."""
    folder=Path(folder);target=folder/'raw_new.zip';skipped=[];records=[]
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=3) as dest:
        for p in sorted((folder/'raw_parts').glob('e*.zip')):
            try:
                with zipfile.ZipFile(p) as source:
                    if source.testzip() is not None:skipped.append(p.name);continue
                    data={n:source.read(n) for n in source.namelist()}
            except zipfile.BadZipFile:skipped.append(p.name);continue
            for name,payload in data.items():dest.writestr(name,payload)
            records.append(json.loads(data[p.stem+'.record.json']))
    target.replace(folder/'raw.zip')
    order=json.loads((folder/'map.json').read_text())['pipe_order']
    for n in ['evals.csv','genes.csv','evals.jsonl','pop.csv','hist.csv','progress.csv']:(folder/n).unlink(missing_ok=True)
    append_csv(folder/'evals.csv',FIELDS,records)
    append_csv(folder/'genes.csv',['evaluation_id']+order,[{'evaluation_id':r['evaluation_id'],**dict(zip(order,r['indices']))} for r in records])
    (folder/'evals.jsonl').write_text(''.join(json.dumps(r,allow_nan=False)+'\n' for r in records))
    for p in sorted((folder/'gen').glob('g*.json')):
        s=json.loads(p.read_text())
        for n,k in [('pop.csv','population'),('hist.csv','archive')]:append_csv(folder/n,list(s[k][0]),s[k])
        append_csv(folder/'progress.csv',list(s['summary']),[s['summary']])
    jsonwrite(folder/'raw_pack.json',{'candidate_archives':len(records),'skipped':skipped})
    return skipped

if __name__=='__main__':
    import sys
    print(pack_raw(sys.argv[1]))
