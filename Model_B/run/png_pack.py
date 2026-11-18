"""Package the twelve individual, native 600-dpi comparison PNGs.

Run after figures.py: python png_pack.py
Output: ../Figs12.zip, with short flat filenames for Windows extraction.
"""
import hashlib
import io
import tempfile
import zipfile
from pathlib import Path
from PIL import Image
from data import atomic
from paths import check_archive

ROOT = Path(__file__).resolve().parent


def main():
    selected = [ROOT/'fig'/f'{style}_{pair}_{metric}.png'
                for style in ['M', 'K'] for pair in ['AB', 'AC', 'BC'] for metric in ['d', 't']]
    for path in selected:
        with Image.open(path) as im:
            assert all(abs(d-600) < .01 for d in im.info['dpi']), path
            im.load()
    note = '''Twelve individual comparison maps: native 600-dpi PNGs.

M = continuous difference map; K = improvement/deterioration classification.
AB = B versus A; AC = C201 versus A; BC = C201 versus B.
d = peak ponding depth; t = flooding duration.

Continuous differences are reference minus target: blue means reduction,
red means increase. The shared 99th-percentile scale has flagged saturation.
Classification tolerances are 0.01 ft and 1 minute, not significance tests.
All comparisons use the same 525 junctions. C means C201. Its 6.73% nonconverging
routing steps exceed B's 5% screening limit, so its comparison is qualified.

These files were rendered from the saved numerical data at 600 dpi.
No simulation, optimization result, or node value was changed for this export.
Plotting code, datasets and complete results are in B_full.zip.
Extract to a short folder, for example C:\\BCfig.
'''
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=False) as z:
        for path in selected:
            z.writestr(path.name, path.read_bytes())
        z.writestr('README.txt', note)
    output = ROOT.parent/'Figs12.zip'
    atomic(output, buffer.getvalue())
    with zipfile.ZipFile(output) as z:
        check_archive(z.namelist()); assert z.testzip() is None
        assert sum(n.endswith('.png') for n in z.namelist()) == 12
        with tempfile.TemporaryDirectory(prefix='png12_') as directory:
            z.extractall(directory)
            for path in selected:
                assert hashlib.sha256((Path(directory)/path.name).read_bytes()).digest() == hashlib.sha256(path.read_bytes()).digest()
    print(output.name, output.stat().st_size, 'bytes; 12 PNGs at 600 dpi; extraction verified')


if __name__ == '__main__':
    main()
