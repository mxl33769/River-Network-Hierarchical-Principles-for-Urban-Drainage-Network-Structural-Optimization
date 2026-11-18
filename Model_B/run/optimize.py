#!/usr/bin/env python3
"""Model B: discrete diameter-only NSGA-II optimization evaluated by EPA SWMM.

Run: python optimize.py --config run.json
Test-sized run: python optimize.py --config test.json
"""
from __future__ import annotations
import argparse
import os
import concurrent.futures
import hashlib
import json
import math
import shutil
import subprocess
import sys
import tempfile
import time
import importlib.metadata
import platform
import zipfile
from pathlib import Path
import numpy as np
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.core.problem import Problem
from pymoo.core.sampling import Sampling
from pymoo.core.repair import Repair
from pymoo.core.callback import Callback
from pymoo.operators.crossover.sbx import SBX
from pymoo.operators.mutation.pm import PM
from pymoo.operators.repair.rounding import RoundingRepair
from pymoo.optimize import minimize
from pymoo.util.nds.non_dominated_sorting import NonDominatedSorting
from pymoo.config import Config
from swmm_io import Inp, parse_model, model_units, catalogue, require, num, write_csv
from records import Recorder, jsonwrite, pack_raw
from paths import check_workspace

Config.warnings['not_compiled']=False
METRICS=['mean_maximum_ponded_depth_ft','mean_hours_flooded']


def barrel(p):
    return float(p['xs'][6]) if len(p['xs'])>6 else 1.0


def volume(pipes):
    return math.fsum(math.pi/4*p['length']*barrel(p)*p['diameter']**2 for p in pipes.values())


from costs import CostDesign as Design


def simulate(path,timeout):
    path=Path(path).resolve()
    metrics=path.with_suffix('.metrics.json')
    # A rerun must never reuse an earlier metrics file.
    metrics.unlink(missing_ok=True)
    worker=Path(__file__).with_name('engine.py')
    result=subprocess.run([sys.executable,str(worker),str(path),str(metrics)],
                          capture_output=True,text=True,timeout=timeout,cwd=path.parent)
    data=json.loads(metrics.read_text()) if metrics.exists() else {'success':False,'error':result.stderr[-2000:]}
    require(result.returncode==0 and data.get('success'),data.get('error','SWMM failed'))
    return data


def check_quality(data,limit,max_nonconvergence=None):
    require(math.isfinite(limit) and limit>0,'Continuity limit must be positive and finite')
    require(all(math.isfinite(data[m]) and data[m]>=0 for m in METRICS),'Invalid objective values')
    require(abs(data['runoff_continuity_error_pct'])<=limit and abs(data['flow_continuity_error_pct'])<=limit,
            f"SWMM continuity error exceeds {limit}%: runoff={data['runoff_continuity_error_pct']}, flow={data['flow_continuity_error_pct']}")
    if max_nonconvergence is not None:
        require(math.isfinite(max_nonconvergence) and 0<=max_nonconvergence<=100,
                'Invalid routing nonconvergence limit')
        require(data['steps_not_converging_pct']<=max_nonconvergence,
                f"Routing steps not converging: {data['steps_not_converging_pct']}%; limit {max_nonconvergence}%. "
                'Resolve baseline numerical behavior before a research optimization; test mode is explicitly diagnostic.')


def check_report(metrics,path):
    # Independently cross-check native statistics with rounded Node Flooding Summary.
    text=Path(path).read_text(errors='replace')
    require('Node Flooding Summary' in text,'Missing Node Flooding Summary')
    section=text.split('Node Flooding Summary',1)[1].split('Storage Volume Summary',1)[0].split('Outfall Loading Summary',1)[0].split('Link Flow Summary',1)[0]
    by_id={r['Node']:r for r in metrics['nodes']}
    found={}
    for line in section.splitlines():
        token=line.split()
        if len(token)==7 and token[0] in by_id and ':' in token[4]:
            try:
                duration=float(token[1]);depth=float(token[-1])
            except ValueError:continue
            found[token[0]]=(duration,depth)
    for node,row in by_id.items():
        if row['HoursFlooded']>0:
            require(node in found,f'Flooded node {node} absent in report')
            duration,depth=found[node]
            require(abs(duration-row['HoursFlooded'])<=.0051 or (row['HoursFlooded']<.0051 and duration<=.01),'Hours Flooded disagrees with report')
            require(abs(depth-row['MaximumPondedDepth_ft'])<=.00051,'Ponded depth disagrees with report')
    return {'report_cross_check_passed':True,'flooded_nodes_checked':len(found)}


class AllowanceRepair(Repair):
    def _do(self,problem,X,**kwargs):
        return np.asarray([problem.design.repair(x) for x in X])


class SparseSampling(Sampling):
    def _do(self,problem,n_samples,**kwargs):
        d=problem.design
        samples=[np.zeros(len(d.ids),dtype=int)]  # Baseline always participates.
        eligible=np.flatnonzero(d.upper)
        for _ in range(n_samples-1):
            x=np.zeros(len(d.ids),dtype=int)
            count=np.random.randint(1,min(len(eligible),d.max_count)+1)
            for i in np.random.choice(eligible,count,replace=False):
                x[i]=np.random.randint(1,d.upper[i]+1)
            samples.append(d.repair(x))
        return np.asarray(samples)


class HydraulicProblem(Problem):
    def __init__(self,design,cfg,out,baseline):
        self.design=design;self.cfg=cfg;self.out=out
        self.cache={tuple([0]*len(design.ids)):baseline}
        self.evaluated=[];self.failures=[]
        self.recorder=Recorder(out,design,cfg)
        zero=tuple([0]*len(design.ids))
        baseline['input_sha256']=hashlib.sha256((out/'A.inp').read_bytes()).hexdigest()
        self.recorder.record(zero,baseline,{'.rpt':(out/'A.rpt').read_bytes(),
                             '.json':(out/'A.metrics.json').read_bytes()},generation=0)
        self.replay={};self.replay_path=None
        if cfg.get('replay_directory'):
            self.replay_path=Path(cfg['replay_directory'])
            previous=json.loads((self.replay_path/'config.json').read_text())
            for field in ['packages','source_sha256']:
                require(json.loads((self.replay_path/'env.json').read_text())[field]==json.loads((out/'env.json').read_text())[field],f'Replay environment differs: {field}')
            require(json.loads((self.replay_path/'map.json').read_text())==json.loads((out/'map.json').read_text()),'Replay diameter options differ')
            require(json.loads((self.replay_path/'allowance.json').read_text())['replacement_budget_usd']==design.budget,'Replay allowance differs')
            for name in ['population_size','generations','seed','continuity_error_limit_pct',
                         'max_steps_not_converging_pct','max_enlarged_pipes']:
                require(cfg[name]==previous[name],f'Replay setting differs: {name}')
            require((self.replay_path/'A.inp').read_bytes()==(out/'A.inp').read_bytes(),'Replay baseline differs')
            if not (self.replay_path/'raw.zip').exists():pack_raw(self.replay_path)
            self.replay_zip=zipfile.ZipFile(self.replay_path/'raw.zip')
            available=set(self.replay_zip.namelist())
            sizes={n:self.replay_zip.getinfo(n).file_size for n in available}
            for line in (self.replay_path/'evals.jsonl').read_text().splitlines():
                r=json.loads(line)
                # Compact checkpoints carry empty report placeholders. Those
                # records are deliberately re-simulated so that resumed runs
                # rebuild native reports rather than accepting placeholders.
                if all(r['evaluation_id']+v in available for v in ['.rpt','.json']) and sizes.get(r['evaluation_id']+'.rpt',0)>0:
                    self.replay[tuple(r['indices'])]=r
            jsonwrite(out/'replay.json',{'source':str(self.replay_path),'complete_pairs':len(self.replay),
                'method':'Same-seed replay with lazy reuse of CRC-verified raw pairs; missing pairs re-simulated.'})
        super().__init__(n_var=len(design.ids),n_obj=2,n_ieq_constr=1,
                         xl=np.zeros(len(design.ids)),xu=design.upper,vtype=int)

    def one(self,key):
        if key in self.replay:
            r=self.replay[key]
            require(r['first_generation']==self.recorder.generation,'Replay generation diverged')
            require(hashlib.sha256(self.design.render(key).encode()).hexdigest()==r['input_sha256'],'Replay input differs')
            artifacts={v:self.replay_zip.read(r['evaluation_id']+v) for v in ['.rpt','.json']}
            data=json.loads(artifacts['.json']);data.pop('nodes',None)
            data.update(success=r['feasible'],engine_success=r['engine_success'],
                input_sha256=r['input_sha256'],error=r['error'],failure_stage=r['failure_stage'],
                replayed=True,original_recorded_utc=r.get('original_recorded_utc') or r['recorded_utc'])
            return key,data,artifacts
        data={};artifacts={};stage='input_generation';digest=''
        with tempfile.TemporaryDirectory(prefix='e_',dir=self.out/'work',ignore_cleanup_errors=True) as temp:
            path=Path(temp)/'m.inp'
            try:
                path.write_text(self.design.render(key),encoding='utf-8')
                digest=hashlib.sha256(path.read_bytes()).hexdigest()
                stage='engine'
                data=simulate(path,self.cfg['simulation_timeout_seconds'])
                data['engine_success']=True
                stage='numerical_screen'
                check_quality(data,self.cfg['continuity_error_limit_pct'],self.cfg.get('max_steps_not_converging_pct'))
            except Exception as exc:
                # Preserve observed objectives for numerically rejected runs.
                # They are logged as infeasible, never plotted as valid improvements.
                data.update(success=False,error=str(exc),failure_stage=stage)
                data.setdefault('engine_success',False)
            finally:
                for suffix,target in [('.rpt','.rpt'),('.metrics.json','.json')]:
                    f=path.with_suffix(suffix)
                    if f.exists():
                        if target=='.rpt':
                            # Preserve native summaries; selected A/B/C keep full reports.
                            artifacts[target]=f.read_text(errors='replace').split('  <<<',1)[0].encode('utf-8')
                        else:
                            raw=json.loads(f.read_text());raw.pop('nodes',None)
                            artifacts[target]=json.dumps(raw).encode('utf-8')
                data['input_sha256']=digest
                data.pop('nodes',None)
        return key,data,artifacts

    def _evaluate(self,X,out,*args,**kwargs):
        keys=[tuple(np.rint(x).astype(int)) for x in X]
        missing=list(dict.fromkeys(k for k in keys if k not in self.cache))
        for key in missing:self.recorder.register(key)
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.cfg.get('workers',1)) as pool:
            # Threads orchestrate isolated subprocesses; SWMM never shares engine state.
            for key,data,artifacts in pool.map(self.one,missing):
                self.cache[key]=data
                self.recorder.record(key,data,artifacts)
                if not data['success']:
                    self.failures.append(self.recorder.rows[key])
        out['F']=np.asarray([[self.cache[k][m] for m in METRICS] if self.cache[k]['success'] else [1e30,1e30] for k in keys])
        out['G']=np.asarray([[0.0 if self.cache[k]['success'] else 1.0] for k in keys])


class Progress(Callback):
    def __init__(self,out):
        super().__init__();self.out=out;self.rows=[]
    def notify(self,algorithm):
        problem=algorithm.problem
        problem.recorder.generation_record(algorithm,problem.cache,
                                           problem.cache[tuple([0]*len(problem.design.ids))])
        command=problem.cfg.get('checkpoint_command')
        if command and (int(algorithm.n_gen)%int(problem.cfg.get('checkpoint_every_generations',5))==0 or int(algorithm.n_gen)==problem.cfg['generations']):
            subprocess.run([sys.executable,command,str(problem.out)],check=True)
        if os.environ.get("B_STOP_AFTER_GENERATION")==str(int(algorithm.n_gen)):
            raise SystemExit(75)


if __name__ == "__main__":
    from run import main
    main()
