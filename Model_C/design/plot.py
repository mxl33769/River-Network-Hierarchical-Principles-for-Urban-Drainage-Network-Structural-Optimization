r"""Existing A/B/C201 designs with colored diameter-change overlays.

INPUT FILE PATHS: --a, --b and --c accept complete SWMM INP paths.
Defaults: inp/A.inp, inp/B.inp, inp/C.inp beside this script.
Example on Windows:
  python plot.py --a C:\BC\r\A.inp --b C:\BC\r\B.inp --c C:\BC\C.inp
OUTPUT DIRECTORY: --out (default: this script's folder).
No model modification or hydraulic simulation occurs in this script.
"""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent
MM_PER_FT = 304.8
D_UPPER = np.array([150., 300., 600., 900., 1200., 1600.])
WIDTHS = np.array([.5, .8, 1.25, 1.85, 2.55, 3.3])
Z_LOWER = -12.
Z_UPPER = np.array([-6., 0., 6., 12., 17.])
AREAS = np.array([32., 23., 15., 8., 3.5])
UNCHANGED = '#8b9198'
NODE_BLUE = '#507fba'
OUTLET_ORANGE = '#d77b19'


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name+'.tmp')
    with tmp.open('wb') as f:
        f.write(content); f.flush(); os.fsync(f.fileno())
    tmp.replace(path)


def csv_write(path, rows):
    stream = io.StringIO(newline='')
    w = csv.DictWriter(stream, fieldnames=list(rows[0]))
    w.writeheader(); w.writerows(rows)
    atomic(path, stream.getvalue().encode('utf-8-sig'))


def read(path):
    sections, current = {}, ''
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.split(';', 1)[0].strip()
        if not line: continue
        if line.startswith('[') and line.endswith(']'):
            current = line.upper(); sections.setdefault(current, [])
        else: sections.setdefault(current, []).append(line.split())
    keyed = lambda name: {r[0]: r for r in sections.get(name, [])}
    assert keyed('[OPTIONS]')['FLOW_UNITS'][1].upper() == 'CFS', 'This package expects CFS/ft inputs.'
    assert keyed('[OPTIONS]').get('LINK_OFFSETS', ['', 'DEPTH'])[1].upper() == 'DEPTH'
    coords = {k: (float(r[1]), float(r[2])) for k, r in keyed('[COORDINATES]').items()}
    nodes = {}
    for section, kind in [('[JUNCTIONS]', 'junction'), ('[OUTFALLS]', 'outfall')]:
        for r in sections.get(section, []):
            nodes[r[0]] = {'id': r[0], 'kind': kind, 'invert': float(r[1]), 'xy': coords[r[0]]}
    xs = keyed('[XSECTIONS]')
    vertices = {}
    for r in sections.get('[VERTICES]', []):
        vertices.setdefault(r[0], []).append((float(r[1]), float(r[2])))
    pipes = {}
    for r in sections['[CONDUITS]']:
        assert xs[r[0]][1].upper() == 'CIRCULAR'
        pipes[r[0]] = {'id': r[0], 'from': r[1], 'to': r[2], 'length': float(r[3]),
                      'diameter': float(xs[r[0]][2]), 'in_offset': float(r[5]) if len(r)>5 else 0.,
                      'out_offset': float(r[6]) if len(r)>6 else 0.,
                      'points': [coords[r[1]], *vertices.get(r[0], []), coords[r[2]]]}
    return {'nodes': nodes, 'pipes': pipes, 'coords': coords}


def figure(models, names, norm, bounds, filename, output, dpi):
    n = len(names)
    fig = plt.figure(figsize=({1:8.5, 2:13.0, 3:18.0}[n], 12.0))
    # Keep panel labels below each layout and an independent framed legend below.
    gs = fig.add_gridspec(1, n, left=.022, right=.978, top=.99, bottom=.28, wspace=.06)
    for j, name in enumerate(names):
        ax = fig.add_subplot(gs[0, j]); model = models[name]
        segments, widths, colors = [], [], []
        for key, pipe in model['pipes'].items():
            diameter = pipe['diameter']*MM_PER_FT
            change = (pipe['diameter']-models['A']['pipes'][key]['diameter'])*MM_PER_FT
            assert change >= -1e-5, f'Unexpected diameter reduction: {name}/{key}'
            index = np.searchsorted(D_UPPER, diameter-1e-6, side='left')
            assert index < len(WIDTHS), 'Extend diameter legend to cover the input model.'
            segments.append(pipe['points']); widths.append(WIDTHS[index])
            colors.append(matplotlib.colormaps['viridis'](norm(change)) if change>1e-5 else UNCHANGED)
        ax.add_collection(LineCollection(segments, linewidths=widths, colors=colors, zorder=1))
        nodes = [v for v in model['nodes'].values() if v['kind']=='junction']
        xy = np.asarray([v['xy'] for v in nodes]); z = np.asarray([v['invert'] for v in nodes])
        assert min(z) >= Z_LOWER and max(z) <= Z_UPPER[-1]
        sizes = AREAS[np.searchsorted(Z_UPPER, z, side='left')]
        ax.scatter(xy[:,0],xy[:,1],s=sizes,c=NODE_BLUE,edgecolors='#234a75',linewidths=.2,zorder=3)
        for key, node in model['nodes'].items():
            if node['kind'] != 'outfall': continue
            original = key == '347'
            ax.scatter(*node['xy'],marker='*' if original else 's',s=110 if original else 48,
                       facecolors=OUTLET_ORANGE if original else 'none',edgecolors='#153858' if original else OUTLET_ORANGE,
                       linewidths=.8 if original else 1.0,zorder=5)
            ax.annotate(key,node['xy'],xytext=(7,6),textcoords='offset points',fontsize=8.5,
                        color='#153858' if original else '#ad570d')
        ax.set(xlim=bounds[0],ylim=bounds[1]);ax.set_aspect('equal');ax.axis('off')
        label = 'Model C (C201)' if name=='C201' else f'Model {name}'
        ax.text(.5,-.025,f'({chr(97+j)}) {label}',transform=ax.transAxes,ha='center',va='top',fontsize=12)
    # Equal final-size and elevation classes apply to every panel and export.
    left, width = (.035,.93) if n==1 else (.085,.83)
    leg = fig.add_axes([left,.084,width,.155])
    leg.set(xlim=(0,1),ylim=(0,1));leg.axis('off')
    leg.add_patch(Rectangle((0,0),1,1,fill=False,lw=.65,edgecolor='#737373',clip_on=False))
    leg.text(.025,.92,'Final diameter D (mm)',fontsize=9,weight='bold',va='top')
    lower=0.
    for i, upper in enumerate(D_UPPER):
        y=.72-.111*i
        leg.plot([.03,.095],[y,y],c='#333333',lw=WIDTHS[i])
        leg.text(.115,y,f'{lower:g} < D ≤ {upper:g}',fontsize=8,va='center');lower=upper
    leg.text(.38,.92,'Invert elevation z (ft)',fontsize=9,weight='bold',va='top')
    lower=Z_LOWER
    for i, upper in enumerate(Z_UPPER):
        y=.72-.118*i
        leg.scatter(.402,y,s=AREAS[i],c=NODE_BLUE,edgecolors='#234a75',linewidths=.25)
        leg.text(.435,y,f'{lower:g} {"≤" if i==0 else "<"} z ≤ {upper:g}',fontsize=8,va='center');lower=upper
    leg.text(.38,.085,'Lower invert = larger node',fontsize=7.5)
    leg.text(.725,.92,'Outlet / unchanged pipe',fontsize=9,weight='bold',va='top')
    leg.scatter(.752,.70,marker='*',s=90,c=OUTLET_ORANGE,edgecolors='#153858',linewidths=.6)
    leg.text(.787,.70,'Original outlet',fontsize=8,va='center')
    leg.scatter(.752,.47,marker='s',s=42,facecolors='none',edgecolors=OUTLET_ORANGE,linewidths=1.)
    leg.text(.787,.47,'New C201 outlet',fontsize=8,va='center')
    leg.plot([.728,.773],[.23,.23],lw=1.3,c=UNCHANGED)
    leg.text(.787,.23,'Diameter unchanged',fontsize=8,va='center')
    cax = fig.add_axes([.22 if n>1 else .13,.043,.56 if n>1 else .74,.014])
    cb=fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap='viridis'),cax=cax,orientation='horizontal')
    cb.set_label('Diameter increase relative to Model A (mm)',fontsize=9,labelpad=5)
    cb.ax.tick_params(labelsize=8)
    for suffix in ['png','pdf','svg']:
        stream=io.BytesIO();fig.savefig(stream,format=suffix,dpi=dpi,bbox_inches='tight',pad_inches=.07,facecolor='white')
        atomic(output/'fig'/f'{filename}.{suffix}',stream.getvalue())
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--a',type=Path,default=ROOT/'inp/A.inp')
    p.add_argument('--b',type=Path,default=ROOT/'inp/B.inp')
    p.add_argument('--c',type=Path,default=ROOT/'inp/C.inp')
    p.add_argument('--out',type=Path,default=ROOT)
    p.add_argument('--dpi',type=int,default=600)
    a=p.parse_args();sources={'A':a.a,'B':a.b,'C201':a.c}
    models={k:read(path) for k,path in sources.items()}
    for name, model in models.items():
        assert model['coords']==models['A']['coords']
        assert set(model['pipes'])==set(models['A']['pipes'])
        for key,pipe in model['pipes'].items():
            old=models['A']['pipes'][key]
            assert {pipe['from'],pipe['to']}=={old['from'],old['to']}
            assert pipe['length']==old['length']
    xy=np.asarray(list(models['A']['coords'].values()));pad=.055*np.ptp(xy,axis=0)
    bounds=((xy[:,0].min()-pad[0],xy[:,0].max()+pad[0]),(xy[:,1].min()-pad[1],xy[:,1].max()+pad[1]))
    pipes,nodes,vertices=[],[],[]
    for name,model in models.items():
        for key,pipe in model['pipes'].items():
            old=models['A']['pipes'][key];delta=(pipe['diameter']-old['diameter'])*MM_PER_FT
            pipes.append({'Model':name,'Pipe':key,'From':pipe['from'],'To':pipe['to'],'Length_ft':pipe['length'],
                'A_mm':old['diameter']*MM_PER_FT,'Final_mm':pipe['diameter']*MM_PER_FT,'Increase_mm':delta,
                'Enlarged':int(delta>1e-5),'OrientationReversed':int(pipe['from']==old['to']),
                'FromInvert_ft':model['nodes'][pipe['from']]['invert'],'ToInvert_ft':model['nodes'][pipe['to']]['invert']})
            vertices.extend({'Model':name,'Pipe':key,'Sequence':i,'X':point[0],'Y':point[1]} for i,point in enumerate(pipe['points']))
        nodes.extend({'Model':name,'Node':key,'Type':node['kind'],'X':node['xy'][0],'Y':node['xy'][1],
                      'Invert_ft':node['invert']} for key,node in model['nodes'].items())
    maximum=max(row['Increase_mm'] for row in pipes)
    upper=float(np.ceil((maximum-1e-6)/100)*100)
    norm=Normalize(0,upper)
    plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})
    for filename, names in [('BC_color',['B','C201']),('B_color',['B']),('C_color',['C201']),('ABC_color',['A','B','C201'])]:
        figure(models,names,norm,bounds,filename,a.out,a.dpi);print('Saved',filename,flush=True)
    for filename,rows in [('pipes.csv',pipes),('nodes.csv',nodes),('vertices.csv',vertices)]:csv_write(a.out/'d'/filename,rows)
    metadata={'models':'Verified cost-constrained B e04701 and unchanged C201; A is diameter reference',
        'source_sha256':{k:hashlib.sha256(path.read_bytes()).hexdigest() for k,path in sources.items()},
        'modified_pipe_counts':{m:sum(r['Enlarged'] for r in pipes if r['Model']==m) for m in models},
        'maximum_diameter_increase_mm':{m:max(r['Increase_mm'] for r in pipes if r['Model']==m) for m in models},
        'color_scale_mm':[0,upper],'width_classes_upper_mm':D_UPPER.tolist(),'line_width_points':WIDTHS.tolist(),
        'node_invert_class_bounds_ft':[Z_LOWER,*Z_UPPER.tolist()],'node_marker_area_pt2':AREAS.tolist(),
        'dpi':a.dpi,'model_geometry_modified':False,
        'note':'Pipe colors show diameter increase only. Gray pipes may still have changed invert elevations or orientation in C201.'}
    atomic(a.out/'d/audit.json',json.dumps(metadata,indent=2).encode())
    print(json.dumps(metadata,indent=2))


if __name__=='__main__':main()
