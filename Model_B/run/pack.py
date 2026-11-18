"""Validate and package final deliverables using short Windows-safe ZIP paths."""
import csv,gzip,hashlib,json,pickle,tempfile,zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image
from pypdf import PdfReader
from paths import check_archive
from data import validate_binary, atomic
ROOT=Path(__file__).resolve().parent

def main():
 assert json.loads((ROOT/'r/status.json').read_text())['stage']=='simulation_complete'
 verification=json.loads((ROOT/'r/verify.json').read_text());assert len(verification)==3
 for row in verification:assert row['all_node_metrics_reproduced'] and row['binary_footer_valid']
 for stem in ['r/A','r/B','C']:validate_binary((ROOT/stem).with_suffix('.out'))
 expected={'F1_search','F2_front','F3_nodes','F4_all','F5_pipes','F6_event','F9_all','B_map','AB_map'}
 expected.update(f'{style}_{pair}_{metric}' for style in ['M','K'] for pair in ['AB','AC','BC'] for metric in ['d','t'])
 images=list((ROOT/'fig').glob('*.png'));assert {p.stem for p in images}==expected
 for p in images:
  with Image.open(p) as im:
   assert all(abs(x-600)<1 for x in im.info['dpi']),(p,im.info)
   im.verify()
   with Image.open(p) as im:im.load()
 pdfs=list((ROOT/'fig').glob('*.pdf'));assert {p.stem for p in pdfs}==expected
 for p in pdfs:assert len(PdfReader(p,strict=True).pages)==1
 svgs=list((ROOT/'fig').glob('*.svg'));assert {p.stem for p in svgs}==expected
 for p in svgs:ET.parse(p)
 with zipfile.ZipFile(ROOT/'ABC.xlsx') as z:assert z.testzip() is None
 with (ROOT/'r/progress.csv').open() as f:progress=list(csv.DictReader(f))
 assert [int(r['generation']) for r in progress]==list(range(1,51))
 with (ROOT/'r/evals.csv').open() as f:evals=list(csv.DictReader(f))
 with (ROOT/'r/genes.csv').open() as f:genes=list(csv.DictReader(f))
 assert len(evals)==len(genes)==len({r['evaluation_id'] for r in evals})==5000
 assert [r['evaluation_id'] for r in evals]==[r['evaluation_id'] for r in genes]==[f'e{i:05d}' for i in range(5000)]
 audit=json.loads((ROOT/'r/recover.json').read_text())
 assert audit['all_generations_recomputed_and_verified'] and audit['unique_designs']==5000
 for name,row in audit['tables'].items():
  assert row['surviving_rows_verified']
  assert hashlib.sha256((ROOT/'r'/name).read_bytes()).hexdigest()==row['new_sha256'],name
 # CSV repair changes checkpoint log byte offsets only; check safe resume lengths.
 state=pickle.loads(gzip.decompress((ROOT/'r/state.pkl.gz').read_bytes()))
 assert state['algorithm'].n_gen==51 and len(state['algorithm'].problem.cache)==5000
 for name,size in state['sizes'].items():assert (ROOT/'r'/name).stat().st_size==size
 for n,h in state['signature']['source_sha256'].items():assert hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h
 for folder in ['d','r']:
  for p in (ROOT/folder).glob('*.csv'):
   with p.open(encoding='utf-8-sig',newline='') as f:
    reader=csv.DictReader(f)
    for row in reader:assert None not in row and None not in row.values(),p
 selected=[]
 for p in sorted(ROOT.iterdir()):
  if p.is_file() and (p.suffix in ['.py','.mjs','.md','.inp'] or p.name in ['run.json','C.json','tests.json','requirements.txt','ABC.xlsx','C.out','C.rpt']):selected.append(p)
 for folder in ['d','fig','r']:
  for p in sorted((ROOT/folder).rglob('*')):
   if p.is_file() and not any(x in ['work','raw_parts','__pycache__'] for x in p.relative_to(ROOT/folder).parts) and p.suffix!='.tmp':selected.append(p)
 # Analysis source JSON is included so the workbook can be rebuilt.
 files={p.relative_to(ROOT).as_posix():{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in selected}
 atomic(ROOT/'files.json',json.dumps(files,indent=2).encode())
 selected.append(ROOT/'files.json')
 out=ROOT.parent/'B_full.zip'
 with tempfile.TemporaryDirectory(prefix='bc_pack_') as tmp:
  temporary=Path(tmp)/out.name
  with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=False) as z:
   for p in selected:z.write(p,p.relative_to(ROOT).as_posix())
  atomic(out,temporary.read_bytes())
 with zipfile.ZipFile(out) as z:
  check_archive(z.namelist());assert z.testzip() is None
  with tempfile.TemporaryDirectory(prefix='bcr_') as tmp:
   z.extractall(tmp)
   for name,record in files.items():assert hashlib.sha256((Path(tmp)/name).read_bytes()).hexdigest()==record['sha256']
 result={'archive':out.name,'bytes':out.stat().st_size,'entries':len(selected),'max_relative_path':max(len(p.relative_to(ROOT).as_posix()) for p in selected),'crc_and_extraction_verified':True,'all_png_dpi':600,'unique_designs':len(evals),'completed_generations':50,'prior_checkpoint_records_preserved':True}
 atomic(ROOT/'release.json',json.dumps(result,indent=2).encode());print(json.dumps(result,indent=2))
if __name__=='__main__':main()
