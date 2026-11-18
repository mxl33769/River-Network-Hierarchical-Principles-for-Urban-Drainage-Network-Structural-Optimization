r"""600-dpi comparison maps and search diagnostics from actual simulation CSVs.

CSV INPUT PATHS: --data points to nodes.csv, delta.csv, pipes.csv, classes.csv,
summary.csv, event.csv and meta.json. --run points to optimizer CSVs.
OUTPUT PATH: --out. Defaults resolve relative to this script, not your shell.
Example: python figures.py --data C:\BC\d --run C:\BC\r --out C:\BC\fig
Use --scale-max for untruncated continuous scales; default is shared 99th
percentile absolute changes. All values remain unchanged in the CSV files.
"""
import argparse
import csv
import io
import json
import os
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import TwoSlopeNorm
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator, FormatStrFormatter, FuncFormatter

ROOT = Path(__file__).resolve().parent
PAIR = [('AB', 'A', 'B'), ('AC', 'A', 'C201'), ('BC', 'B', 'C201')]
METRICS = [('d', 'Reduction_ft', 'Peak ponded depth', 'ft', 'Depth', .01),
           ('t', 'Reduction_h', 'Flooding duration', 'h', 'Time', 1/60)]


def read(path):
    with path.open(encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def values(rows, key):
    return np.asarray([float(r[key]) for r in rows])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, default=ROOT/'d')
    p.add_argument('--run', type=Path, default=ROOT/'r')
    p.add_argument('--out', type=Path, default=ROOT/'fig')
    p.add_argument('--dpi', type=int, default=600)
    p.add_argument('--scale-max', action='store_true')
    p.add_argument('--only', nargs='+', help='Optional figure stems to regenerate, e.g. F2_front F3_nodes')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    rows, pipes = read(a.data/'delta.csv'), read(a.data/'pipes.csv')
    nodes, allnodes = read(a.data/'nodes.csv'), read(a.data/'allnodes.csv')
    classes = read(a.data/'classes.csv')
    meta = json.loads((a.data/'meta.json').read_text())
    points = {r['Node']: (float(r['X']), float(r['Y'])) for r in allnodes}
    segments = [[(float(r['FromX']), float(r['FromY'])), (float(r['ToX']), float(r['ToY']))] for r in pipes]
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.titlesize': 12,
        'axes.titleweight': 'bold', 'svg.fonttype': 'none', 'axes.spines.top': False, 'axes.spines.right': False})
    limits = {key: max(float(np.max(abs(values(rows,key))) if a.scale_max else np.quantile(abs(values(rows,key)), .99)), 1e-8)
              for _, key, _, _, _, _ in METRICS}
    audit = []
    saved = []

    def atomic(path, content):
        temporary = path.with_name(path.name+'.tmp')
        with temporary.open('wb') as f:
            f.write(content); f.flush(); os.fsync(f.fileno())
        temporary.replace(path)

    def save(fig, name):
        if a.only and name not in a.only:
            plt.close(fig)
            return
        for extension in ['png', 'pdf', 'svg']:
            content = io.BytesIO()
            fig.savefig(content, format=extension, dpi=a.dpi, bbox_inches='tight', facecolor='white')
            atomic(a.out/(name+'.'+extension), content.getvalue())
        saved.append(name)
        print('Saved', name, flush=True)
        plt.close(fig)

    def network(ax, include_C):
        ax.add_collection(LineCollection(segments, colors='#c4cbd1', linewidths=.55, zorder=0))
        ax.autoscale()
        ax.set_aspect('equal')
        ax.margins(.065)
        ax.axis('off')
        ax.scatter(*points['347'], marker='*', s=85, c='#ed9226', edgecolors='#111111', linewidths=.8, zorder=5)
        for node in meta['new_C201_outfalls']:
            ax.scatter(*points[node], marker='s' if include_C else 'o', s=34 if include_C else 17,
                facecolors='none', edgecolors='#bd5f0b' if include_C else '#555555', linewidths=.7, zorder=5)

    def outlet_key(include_C):
        return [Line2D([],[],ls='',marker='*',ms=9,mfc='#ed9226',mec='black',label='Original outlet'),
                Line2D([],[],ls='',marker='s' if include_C else 'o',ms=5,mfc='none',mec='#bd5f0b' if include_C else '#555555',
                       label='C201 outlet (excluded)' if include_C else 'Future C201 outlet (excluded)')]

    def panel(ax, fig, pair, metric, discrete, letter, small=False):
        label, ref, target = pair
        suffix, key, title, unit, class_key, tolerance = metric
        subset = [r for r in rows if r['Pair'] == label]
        assert len(subset) == 525
        v, x, y = values(subset,key), values(subset,'X'), values(subset,'Y')
        network(ax, target == 'C201')
        ax.set_title(f'{target} versus {ref}: {title}', pad=8, fontsize=10 if small else 12)
        if discrete:
            handles = []
            for name, color, mask in [('Improved','#0072B2',v>tolerance), ('Worsened','#D55E00',v < -tolerance),
                                      ('Within tolerance','#d8d8d8',abs(v)<=tolerance)]:
                ax.scatter(x[mask],y[mask],s=9 if small else 17,c=color,edgecolors='#7c7c7c',linewidths=.17,zorder=3)
                handles.append(Line2D([],[],ls='',marker='o',ms=4.5,color=color,label=f'{name}: {int(mask.sum())}'))
            ax.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,-.005),ncol=3,fontsize=6.3 if small else 8,
                frameon=True,fancybox=False,edgecolor='#bbbbbb',facecolor='white',framealpha=.96)
            note=f'Tolerance: {tolerance:.3g} {unit}'
        else:
            limit=limits[key]
            sc=ax.scatter(x,y,c=v,cmap='RdBu',norm=TwoSlopeNorm(vcenter=0,vmin=-limit,vmax=limit),
                s=10 if small else 18,edgecolors='#666666',linewidths=.24,zorder=3)
            below,above=int((v < -limit).sum()),int((v > limit).sum())
            extend='both' if below and above else 'min' if below else 'max' if above else 'neither'
            cb=fig.colorbar(sc,ax=ax,fraction=.047,pad=.018,shrink=.63,extend=extend)
            cb.ax.tick_params(labelsize=7 if small else 9)
            cb.set_label(f'{ref} − {target} ({unit})\nBlue: reduction; red: increase',fontsize=7 if small else 9)
            note='Shared full-range scale' if a.scale_max else f'Shared 99% scale; saturated nodes: {below+above}'
            audit.append({'Pair':label,'Metric':class_key,'ScaleMin':-limit,'ScaleMax':limit,
                'ActualMin':float(v.min()),'ActualMax':float(v.max()),'BelowScale':below,'AboveScale':above})
        ax.text(.5,-.063 if discrete else -.018,f'({letter})  {note}',transform=ax.transAxes,ha='center',va='top',fontsize=7 if small else 9)

    # Exactly six individual figures per style: three pairs times two metrics.
    for discrete,prefix in [(False,'M'),(True,'K')]:
        for pair in PAIR:
            for metric in METRICS:
                fig,ax=plt.subplots(figsize=(5.7,8.0))
                panel(ax,fig,pair,metric,discrete,'a')
                fig.legend(handles=outlet_key(pair[2]=='C201'),loc='lower center',bbox_to_anchor=(.48,.015),
                    ncol=1,fontsize=8,frameon=True,fancybox=False)
                fig.subplots_adjust(left=.035,right=.90 if not discrete else .98,top=.95,bottom=.17 if discrete else .105)
                save(fig,f'{prefix}_{pair[0]}_{metric[0]}')
        # A complete six-panel plate is also supplied for manuscript assembly.
        fig,axes=plt.subplots(3,2,figsize=(10.5,18))
        for i,pair in enumerate(PAIR):
            for j,metric in enumerate(METRICS):
                panel(axes[i,j],fig,pair,metric,discrete,chr(97+2*i+j),small=True)
        fig.subplots_adjust(left=.025,right=.94,top=.98,bottom=.08 if discrete else .065,wspace=.10,hspace=.16)
        fig.legend(handles=outlet_key(True)+[outlet_key(False)[1]],loc='lower center',bbox_to_anchor=(.5,.027),ncol=3,fontsize=8,frameon=True,fancybox=False)
        fig.text(.5,.012,'525 common junctions. C201 reference exceeds the 5% nonconvergence screen.',ha='center',fontsize=8)
        save(fig,'F9_all' if discrete else 'F4_all')
    # Scale audit keeps clipped tails explicit without changing any node value.
    unique={(r['Pair'],r['Metric']):r for r in audit}
    stream=io.StringIO(newline='')
    writer=csv.DictWriter(stream,fieldnames=list(audit[0]));writer.writeheader();writer.writerows(unique.values())
    atomic(a.out/'scales.csv',stream.getvalue().encode('utf-8-sig'))
    progress,evals,hist=read(a.run/'progress.csv'),read(a.run/'evals.csv'),read(a.run/'hist.csv')
    summary=read(a.data/'summary.csv')
    fig,axes=plt.subplots(2,2,figsize=(10.2,7.2),layout='constrained')
    for ax,best,chosen,title in [(axes[0,0],'best_depth_ft','compromise_depth_ft','Mean peak ponded depth (ft)'),
                                 (axes[0,1],'best_duration_h','compromise_duration_h','Mean flooding duration (h)')]:
        ax.plot(values(progress,'generation'),values(progress,best),label='Archive minimum',color='#0072B2')
        ax.plot(values(progress,'generation'),values(progress,chosen),'--',label='Selected compromise',color='#D55E00')
        ax.set_ylabel(title);ax.legend(fontsize=8)
    axes[1,0].plot(values(progress,'generation'),values(progress,'hypervolume_A_normalized'),color='#009E73')
    axes[1,0].set_ylabel('Hypervolume, A-normalized')
    for key,label in [('feasible_unique_designs','Feasible'),('rejected_unique_designs','Rejected')]:
        axes[1,1].plot(values(progress,'generation'),values(progress,key),label=label)
    axes[1,1].set_ylabel('Cumulative unique designs');axes[1,1].legend(fontsize=8)
    for i,ax in enumerate(axes.flat):
        ax.set_xlabel('Generation');ax.grid(alpha=.2);ax.set_title(f'({chr(97+i)})')
    save(fig,'F1_search')
    valid=[r for r in evals if r['feasible'].lower()=='true']
    last=int(max(values(hist,'generation')));front=[r for r in hist if int(r['generation'])==last]
    lookup={r['evaluation_id']:r for r in evals}
    keys=['mean_maximum_ponded_depth_ft','mean_hours_flooded']
    fig,axes=plt.subplots(1,2,figsize=(10,5.2),layout='constrained')
    axes[0].scatter(values(valid,keys[0]),values(valid,keys[1]),c='#b9c2c9',s=8,alpha=.4,label='Feasible designs')
    baseline=lookup['e00000']
    axes[0].scatter(float(baseline[keys[0]]),float(baseline[keys[1]]),marker='s',s=42,c='black',label='A baseline')
    for gen in sorted(set([1,min(10,last),min(25,last),last])):
        rr=[r for r in hist if int(r['generation'])==gen]
        axes[0].scatter(values(rr,keys[0]),values(rr,keys[1]),s=18,label=f'Generation {gen}')
    sc=axes[1].scatter(values(front,keys[0]),values(front,keys[1]),c=[float(lookup[r['evaluation_id']]['replacement_cost_usd']) for r in front],cmap='viridis',s=40,edgecolors='black')
    cb=fig.colorbar(sc,ax=axes[1],orientation='horizontal',label='Pipe replacement component cost (USD)')
    cb.locator=MaxNLocator(nbins=4);cb.formatter=FuncFormatter(lambda x,pos:f'{x:,.0f}');cb.update_ticks()
    axes[1].xaxis.set_major_locator(MaxNLocator(nbins=4))
    axes[1].xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
    axes[0].set_title('(a) Search and archive evolution')
    axes[1].set_title('(b) Final nondominated designs')
    chosen=progress[-1]
    for ax in axes:
        ax.scatter(float(chosen['compromise_depth_ft']),float(chosen['compromise_duration_h']),marker='*',s=130,c='#D55E00',edgecolors='black',label='Selected B')
        ax.set(xlabel='Mean peak ponded depth (ft), 530 junctions',ylabel='Mean flooding duration (h)');ax.grid(alpha=.2);ax.legend(fontsize=7)
    save(fig,'F2_front')
    fig,axes=plt.subplots(2,2,figsize=(10,7.3),layout='constrained')
    colors={'A':'#666666','B':'#0072B2','C201':'#009E73'}
    for j,(key,unit,title) in enumerate([('Depth','ft','Peak ponded depth'),('Time','h','Flooding duration')]):
        for target in ['B','C201']:
            axes[0,j].scatter(values(nodes,'A_'+key+'_'+unit),values(nodes,target+'_'+key+'_'+unit),s=9,alpha=.55,label=target,color=colors[target])
        limit=max(max(values(nodes,m+'_'+key+'_'+unit)) for m in colors)
        axes[0,j].plot([0,limit],[0,limit],'--',c='#666666');axes[0,j].set(xlabel=f'A: {title} ({unit})',ylabel=f'Target: {title} ({unit})')
        for model,color in colors.items():
            v=np.sort(values(nodes,model+'_'+key+'_'+unit))
            axes[1,j].step(v,np.arange(1,len(v)+1)/len(v),where='post',label=model,color=color)
        axes[1,j].set(xlabel=f'{title} ({unit})',ylabel='Cumulative fraction, common junctions')
    for ax,title in zip(axes.flat,['(a) Paired peak depths','(b) Paired flooding durations','(c) Depth distributions','(d) Duration distributions']):
        ax.legend(fontsize=8);ax.grid(alpha=.2);ax.set_title(title)
    save(fig,'F3_nodes')
    changed=[r for r in pipes if float(r['B_Cost_USD'])>0]
    fig,axes=plt.subplots(1,2,figsize=(10,7),layout='constrained');network(axes[0],False)
    seg=[[(float(r['FromX']),float(r['FromY'])),(float(r['ToX']),float(r['ToY']))] for r in changed]
    lc=LineCollection(seg,cmap='viridis',linewidths=2.6);lc.set_array(values(changed,'B_mm')-values(changed,'A_mm'));axes[0].add_collection(lc)
    fig.colorbar(lc,ax=axes[0],orientation='horizontal',label='Diameter increase above A (mm)')
    top=sorted(changed,key=lambda r:float(r['B_Cost_USD']),reverse=True)[:15]
    axes[1].barh([r['Pipe'] for r in top],values(top,'B_Cost_USD'),color='#0072B2');axes[1].invert_yaxis();axes[1].set(xlabel='Replacement component cost (USD)',ylabel='Pipe ID')
    axes[0].set_title('(a) Enlarged existing pipes');axes[1].set_title('(b) Largest replacement costs')
    save(fig,'F5_pipes')
    event=read(a.data/'event.csv');fig,axes=plt.subplots(2,2,figsize=(10,7),layout='constrained')
    for ax,key,label in zip(axes.flat,['Rain_in_h','MeanPonded_ft','OutfallFlow_cfs','PondedNodes'],['Shared rainfall (in/h)','Mean instantaneous ponded depth (ft)','Total outfall flow (ft³/s)','Ponded junctions, common 525']):
        for model,color in colors.items():
            if key=='Rain_in_h' and model!='A':continue
            rr=[r for r in event if r['Model']==model]
            ax.plot(values(rr,'Time_h'),values(rr,key),label=model,color=color)
        ax.set(xlabel='Time since start (h)',ylabel=label);ax.legend(fontsize=8);ax.grid(alpha=.2)
    for ax,title in zip(axes.flat,['(a) Shared rainfall','(b) Ponding through the event','(c) Total outfall discharge','(d) Extent of modeled ponding']):ax.set_title(title)
    save(fig,'F6_event')
    print('Saved',len(saved),'figures in PNG/PDF/SVG at',a.dpi,'dpi:',', '.join(saved))


if __name__=='__main__':
    main()
