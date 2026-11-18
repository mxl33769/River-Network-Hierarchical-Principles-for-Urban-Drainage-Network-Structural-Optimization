r"""Draw the complete selected cost-constrained B network and matched A/B layouts.

INPUT PATHS: --root contains r/A.inp and r/B.inp. These are the verified models,
not the earlier volume-constrained B. --out sets the figure directory.
Example: python plot_net.py --root C:\BC --out C:\BC\fig --dpi 600
Diameters: native INP feet converted to mm. Node sizes: invert elevation in ft,
not burial depth. The code preserves coordinates and intermediate vertices.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.patches import Rectangle
from data import atomic
from swmm_io import Inp, parse_model

ROOT = Path(__file__).resolve().parent
DIAMETER_UPPER = np.array([150., 300., 600., 900., 1200., 1600.])
LINEWIDTHS = np.array([.45, .75, 1.15, 1.7, 2.4, 3.1])
ELEVATION_UPPER = np.array([11., 13., 15., 17.])
NODE_AREAS = np.array([22., 14., 8., 3.5])
BLUE = '#507fba'


def read_model(path):
    inp = Inp(path.read_text())
    assert inp.rows('[OPTIONS]')['FLOW_UNITS'][1].upper() == 'CFS'
    nodes, pipes = parse_model(inp)
    coords = {k: (float(r[1]), float(r[2])) for k, r in inp.rows('[COORDINATES]').items()}
    vertices = {}
    for line in inp.blocks.get('[VERTICES]', []):
        r = line.split(';', 1)[0].split()
        if r:
            vertices.setdefault(r[0], []).append((float(r[1]), float(r[2])))
    segments = [[coords[p['u']], *vertices.get(k, []), coords[p['v']]] for k, p in pipes.items()]
    diameters = np.array([p['diameter']*304.8 for p in pipes.values()])
    elevations = np.array([n['invert'] for n in nodes.values()])
    assert diameters.min() > 0 and diameters.max() <= DIAMETER_UPPER[-1]+1e-6
    assert elevations.min() >= 9 and elevations.max() <= ELEVATION_UPPER[-1]+1e-6
    return nodes, pipes, coords, segments, diameters


def legend(fig, rect):
    ax = fig.add_axes(rect)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    ax.add_patch(Rectangle((0, 0), 1, 1, fill=False, edgecolor='#6b6b6b', lw=.65, clip_on=False))
    ax.text(.025, .91, 'Pipe diameter D (mm)', fontsize=9, weight='bold', va='top')
    lower = 0
    for i, upper in enumerate(DIAMETER_UPPER):
        y = .72-i*.113
        ax.plot([.03, .105], [y, y], color='#222222', lw=LINEWIDTHS[i])
        ax.text(.125, y, f'{lower:g} < D ≤ {upper:g}', fontsize=8, va='center')
        lower = upper
    ax.text(.405, .91, 'Invert elevation z (ft)', fontsize=9, weight='bold', va='top')
    labels = ['9.0 ≤ z ≤ 11.0', '11.0 < z ≤ 13.0', '13.0 < z ≤ 15.0', '15.0 < z ≤ 17.0']
    for i, label in enumerate(labels):
        y = .70-i*.14
        ax.scatter(.43, y, s=NODE_AREAS[i], c=BLUE, edgecolors='#234a75', linewidths=.3)
        ax.text(.465, y, label, fontsize=8, va='center')
    ax.text(.405, .13, 'Lower elevation = larger node', fontsize=7.5)
    ax.text(.76, .91, 'Outlet', fontsize=9, weight='bold', va='top')
    ax.scatter(.79, .70, s=95, marker='*', c='#e18c20', edgecolors='#153858', linewidths=.7)
    ax.text(.82, .70, '347', fontsize=8, va='center')
    ax.text(.76, .51, 'Original outlet', fontsize=8)
    ax.text(.76, .27, 'Single-outlet\nlayout retained', fontsize=8, linespacing=1.6)


def panel(ax, model, letter, name):
    nodes, pipes, coords, segments, diameter = model
    # Tolerance only prevents decimal conversion noise at exact class boundaries.
    bins = np.searchsorted(DIAMETER_UPPER, diameter-1e-6, side='left')
    ax.add_collection(LineCollection(segments, linewidths=LINEWIDTHS[bins], colors='#222222', zorder=1))
    junctions = [k for k, n in nodes.items() if n['kind'] == 'junction']
    xy = np.asarray([coords[k] for k in junctions])
    z = np.array([nodes[k]['invert'] for k in junctions])
    areas = NODE_AREAS[np.searchsorted(ELEVATION_UPPER, z, side='left')]
    ax.scatter(xy[:, 0], xy[:, 1], s=areas, c=BLUE, edgecolors='#234a75', linewidths=.2, zorder=3)
    for k, node in nodes.items():
        if node['kind'] == 'outfall':
            ax.scatter(*coords[k], s=115, marker='*', c='#e18c20', edgecolors='#153858', linewidths=.7, zorder=5)
            ax.annotate(k, coords[k], xytext=(8, 7), textcoords='offset points', color='#153858', fontsize=9)
    ax.autoscale(); ax.margins(.06); ax.set_aspect('equal'); ax.axis('off')
    ax.text(.5, -.025, f'({letter}) {name}', transform=ax.transAxes, ha='center', va='top', fontsize=12)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root', type=Path, default=ROOT)
    p.add_argument('--out', type=Path, default=ROOT/'fig')
    p.add_argument('--dpi', type=int, default=600)
    a = p.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    sources = {m: a.root/'r'/f'{m}.inp' for m in ['A', 'B']}
    models = {m: read_model(path) for m, path in sources.items()}
    assert models['A'][2] == models['B'][2]
    assert {k: v['invert'] for k, v in models['A'][0].items()} == {k: v['invert'] for k, v in models['B'][0].items()}
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'svg.fonttype': 'none'})
    for filename, selected in [('B_map', ['B']), ('AB_map', ['A', 'B'])]:
        fig = plt.figure(figsize=(7.8 if len(selected) == 1 else 12.0, 11.0))
        gs = fig.add_gridspec(1, len(selected), left=.02, right=.98, bottom=.26, top=.99, wspace=.05)
        for i, m in enumerate(selected):
            panel(fig.add_subplot(gs[0, i]), models[m], chr(97+i), 'Model A' if m == 'A' else 'Model B: cost-constrained')
        legend(fig, [.05 if len(selected) == 1 else .12, .025, .90 if len(selected) == 1 else .76, .19])
        for ext in ['png', 'pdf', 'svg']:
            buffer = io.BytesIO()
            fig.savefig(buffer, format=ext, dpi=a.dpi, bbox_inches='tight', pad_inches=.08, facecolor='white')
            atomic(a.out/(filename+'.'+ext), buffer.getvalue())
        plt.close(fig)
        print('Saved', filename, flush=True)
    record = {'source_sha256': {m: hashlib.sha256(p.read_bytes()).hexdigest() for m, p in sources.items()},
        'conduits': len(models['B'][1]), 'junctions': sum(n['kind']=='junction' for n in models['B'][0].values()),
        'B_maximum_diameter_mm': float(models['B'][4].max()),
        'diameter_class_upper_mm': DIAMETER_UPPER.tolist(), 'line_width_points': LINEWIDTHS.tolist(),
        'invert_class_upper_ft': ELEVATION_UPPER.tolist(), 'node_area_points_squared': NODE_AREAS.tolist(),
        'node_size_represents': 'Invert elevation in ft; lower invert means larger node, not burial depth',
        'dpi': a.dpi}
    atomic(a.out/'design.json', json.dumps(record, indent=2).encode())


if __name__ == '__main__':
    main()
