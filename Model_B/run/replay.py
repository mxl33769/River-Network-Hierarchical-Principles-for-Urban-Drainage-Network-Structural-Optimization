"""Recreate and rerun one recorded design. Example: python replay.py e00001.

genes.csv contains catalogue indices, not physical diameters. map.json supplies
the exact index-to-diameter mapping. No new optimization is performed.
"""
import argparse,csv,hashlib,json,subprocess,sys
from pathlib import Path
from costs import CostDesign
ROOT=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('evaluation');p.add_argument('--run',default='r');p.add_argument('--out',default='replay')
 a=p.parse_args();run=ROOT/a.run;out=ROOT/a.out;out.mkdir(parents=True,exist_ok=True)
 cfg=json.loads((run/'config.json').read_text())
 design=CostDesign((ROOT/'A.inp').read_text(),(ROOT/'C.inp').read_text(),cfg)
 with (run/'genes.csv').open(newline='') as f:row=next((r for r in csv.DictReader(f) if r['evaluation_id']==a.evaluation),None)
 if row is None:raise ValueError('Unknown evaluation ID')
 indices=[int(row[k]) for k in design.ids];text=design.render(indices)
 with (run/'evals.csv').open(newline='') as f:record=next(r for r in csv.DictReader(f) if r['evaluation_id']==a.evaluation)
 sha=hashlib.sha256(text.encode()).hexdigest()
 if record['input_sha256'] and sha!=record['input_sha256']:raise ValueError('Design hash differs from saved evaluation')
 inp=out/(a.evaluation+'.inp');inp.write_text(text)
 subprocess.run([sys.executable,str(ROOT/'engine.py'),str(inp),str(inp.with_suffix('.json'))],check=True,timeout=cfg['simulation_timeout_seconds'])
 result=json.loads(inp.with_suffix('.json').read_text())
 for k in ['mean_maximum_ponded_depth_ft','mean_hours_flooded']:
  if record[k] and result.get(k) is not None and abs(float(record[k])-result[k])>1e-8:raise AssertionError('Objective mismatch: '+k)
 print(json.dumps({'evaluation':a.evaluation,'input_sha256':sha,'recorded_feasible':record['feasible'],'engine_success':result['success'],'output_folder':str(out)},indent=2))
if __name__=='__main__':main()
