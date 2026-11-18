"""Compact completed-generation checkpoints. Raw summaries are reproducible."""
import json
import os
from pathlib import Path
import subprocess
import sys
import zipfile
from paths import check_archive

ROOT = Path(__file__).resolve().parent


def save(run):
    target, temp = ROOT/'BC_save.zip', ROOT/'BC_save.tmp'
    with zipfile.ZipFile(temp, 'w', zipfile.ZIP_DEFLATED, allowZip64=False) as archive:
        for path in sorted(ROOT.iterdir()):
            if path.is_file() and path.suffix in ['.py', '.mjs', '.json', '.inp', '.txt', '.md'] and path.name not in ['saved.json', 'book_env.json', 'RESTORE.txt']:
                archive.write(path, path.name)
        for path in sorted(run.rglob('*')):
            rel = path.relative_to(run)
            if not path.is_file() or any(p in ['work', 'raw_parts'] for p in rel.parts) or path.suffix in ['.tmp', '.out', '.rpt']:
                continue
            archive.write(path, 'r/'+rel.as_posix())
        archive.writestr('RESTORE.txt', 'Extract into a short folder, install requirements.txt, then run python run.py. The saved population, evaluation cache and random states resume automatically. Only load your own checkpoint. Completed evaluation tables are included. Native intermediate report summaries are omitted; all designs can be regenerated from map.json and genes.csv. Final native reports are regenerated at completion.\n')
    with zipfile.ZipFile(temp) as archive:
        check_archive(archive.namelist())
        if archive.testzip() is not None:
            raise RuntimeError('Checkpoint archive CRC failure')
    temp.replace(target)
    helper = os.environ.get('B_LIBRARY_UPLOAD_HELPER')
    if not helper:
        return
    identity = ROOT/'saved.json'
    request = {'local_path': str(target), 'purpose': 'create_library_file'}
    if identity.exists():
        old = json.loads(identity.read_text())
        request.update(purpose='replace_library_file', library_file_id=old['library_file_id'],
            expected_current_version=old['current_version_number'], version_reason='Completed cost-constrained B generation')
    process = subprocess.run([sys.executable, helper], input=json.dumps({'uploads': [request]}), capture_output=True, text=True)
    (ROOT/'save.log').write_text(process.stdout+'\n'+process.stderr)
    response = None
    for line in reversed(process.stdout.splitlines()):
        try:
            value = json.loads(line)
            if 'results' in value:
                response = value['results'][0]
                break
        except ValueError:
            pass
    if not response or response.get('status') != 'succeeded':
        raise RuntimeError('Durable checkpoint save failed; completed local state remains resumable')
    identity.write_text(json.dumps(response, indent=2))
    print('DURABLE CHECKPOINT SAVED', flush=True)
