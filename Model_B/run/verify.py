"""Independently rerun final A, B and C201 in isolated temporary folders.

Completed RPT/OUT/JSON bytes are installed atomically. Every binary footer
and objective is checked before subsequent analysis reads the files.
Run: python verify.py --run r
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from data import validate_binary
from optimize import check_report, check_quality

ROOT = Path(__file__).resolve().parent


def put(path, content):
    temporary=path.with_name(path.name+'.tmp')
    with temporary.open('wb') as f:
        f.write(content);f.flush();os.fsync(f.fileno())
    temporary.replace(path)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--run',default='r');a=p.parse_args()
    run=ROOT/a.run
    cases={'A':(run/'A.inp',run/'A.metrics.json'), 'B':(run/'B.inp',run/'B.metrics.json'), 'C201':(ROOT/'C.inp',ROOT/'C.json')}
    results=[]
    for model,(source,metric_path) in cases.items():
        expected=json.loads(metric_path.read_text())
        with tempfile.TemporaryDirectory(prefix='bc_verify_') as directory:
            target=Path(directory)/'m.inp';target.write_bytes(source.read_bytes())
            output=target.with_suffix('.json')
            subprocess.run([sys.executable,str(ROOT/'engine.py'),str(target),str(output)],check=True,timeout=120)
            actual=json.loads(output.read_text())
            if not actual.get('success'):raise RuntimeError(actual)
            for metric in ['mean_maximum_ponded_depth_ft','mean_hours_flooded','network_maximum_ponded_depth_ft','network_maximum_hours_flooded']:
                if not math.isclose(expected[metric],actual[metric],rel_tol=1e-10,abs_tol=1e-10):raise AssertionError((model,metric))
            if actual['nodes']!=expected['nodes']:raise AssertionError('Node result mismatch: '+model)
            validate_binary(target.with_suffix('.out'))
            check_report(actual,target.with_suffix('.rpt'))
            if model!='C201':check_quality(actual,5.,5.)
            else:check_quality(actual,5.,None)
            for extension in ['.rpt','.out']:put(source.with_suffix(extension),target.with_suffix(extension).read_bytes())
            put(metric_path,output.read_bytes())
            results.append({'Model':model,'input_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                'all_node_metrics_reproduced':True,'binary_footer_valid':True,'report_crosscheck_passed':True,
                'passes_B_5pct_screen':actual['steps_not_converging_pct']<=5,
                'flow_error_pct':actual['flow_continuity_error_pct'],'nonconverging_pct':actual['steps_not_converging_pct']})
    put(run/'verify.json',json.dumps(results,indent=2).encode())
    print(json.dumps(results,indent=2))


if __name__=='__main__':main()
