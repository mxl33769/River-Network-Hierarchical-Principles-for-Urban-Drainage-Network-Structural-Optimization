"""Write a concise numerical results report from the final, verified CSVs."""
import csv,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent
def read(path):
 with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
def main():
 rows=read(ROOT/'d/summary.csv');s={r['Model']:r for r in rows}
 cls=read(ROOT/'d/classes.csv');checks=json.loads((ROOT/'r/checks.json').read_text())
 progress=read(ROOT/'r/progress.csv');last=progress[-1]
 f=lambda m,k:float(s[m][k])
 pct=lambda a,b,k:100*(f(a,k)-f(b,k))/f(a,k)
 text=['# Cost-constrained Model B: results','',
 'All values below come from the corrected-rainfall SWMM simulations. B is the new cost-constrained design; C means the unchanged C201 reference. The manuscript\'s adjusted numerical tables are not substituted for these outputs.','',
 '## Search and budget','',
 f"The resumed NSGA-II search completed {len(progress)} generations with population 100 and seed 7. It recorded {checks['unique_designs']:,} unique designs, of which {checks['feasible_designs']:,} passed the candidate screen. The cumulative final archive contains {checks['pareto_designs']} nondominated designs. The selected compromise is {checks['selected_id']}. This is a best-found design from one recorded search, not a certified global optimum.", '',
 f"The selected B enlarges {s['B']['EnlargedPipes']} pipes at a component cost of ${f('B','ReplacementCost_USD'):,.2f}, within the $228,499.91 limit. Its added internal pipe volume is {f('B','AddedVolume_m3'):.3f} m³. C201 enlarges {s['C201']['EnlargedPipes']} pipes and adds {f('C201','AddedVolume_m3'):.3f} m³ at ${f('C201','ReplacementCost_USD'):,.2f}. Cost replaces the volume constraint, so the added volumes differ. The costs exclude excavation, elevation changes and new outlet works.",'',
 f"Over the search, the archive minimum mean peak depth decreased from {float(progress[0]['best_depth_ft']):.6f} to {float(last['best_depth_ft']):.6f} ft, and the minimum mean flooding duration decreased from {float(progress[0]['best_duration_h']):.6f} to {float(last['best_duration_h']):.6f} h. These two minima can belong to different designs. The selected design uses the declared A-normalized Euclidean-distance rule. Changing the budget changes both the feasible design set and search trajectory; comparisons with the old B alone do not isolate an economic mechanism.",'',
 '## Matched network results','',
 'The following table uses the same 525 junctions in all models. Five junctions converted to C201 outlets and the original outlet are excluded. Lower depth and duration are better.','',
 '| Model | Mean peak depth (ft) | Maximum depth (ft) | Mean flooding duration (h) | Maximum duration (h) |',
 '|---|---:|---:|---:|---:|']
 for m in s:text.append(f"| {m} | {f(m,'MeanPeak_ft'):.6f} | {f(m,'MaxPeak_ft'):.6f} | {f(m,'MeanTime_h'):.6f} | {f(m,'MaxTime_h'):.6f} |")
 text+=['',f"Relative to A, new B reduces the common-node mean peak depth by {pct('A','B','MeanPeak_ft'):.2f}% and mean flooding duration by {pct('A','B','MeanTime_h'):.2f}%. C201 reductions relative to A are {pct('A','C201','MeanPeak_ft'):.2f}% and {pct('A','C201','MeanTime_h'):.2f}%, respectively. Relative to new B, the corresponding C201 reductions are {pct('B','C201','MeanPeak_ft'):.2f}% and {pct('B','C201','MeanTime_h'):.2f}%. C201 comparisons are provisional because of its numerical convergence result below.",'',
 f"The optimization itself uses all 530 A/B junctions. Its final B objectives are {f('B','NativeMeanPeak_ft'):.10f} ft and {f('B','NativeMeanTime_h'):.10f} h, compared with {f('A','NativeMeanPeak_ft'):.10f} ft and {f('A','NativeMeanTime_h'):.10f} h for A. These are intentionally distinguished from the common-node table.",'',
 '## Local changes and hydraulic weak points','',
 'Differences are reference minus target. Improvement/worsening is classified using 0.01 ft for depth and one minute for duration. These are descriptive thresholds, not tests of significance.','',
 '| Target versus reference | Metric | Improved | Worsened | Within tolerance |',
 '|---|---|---:|---:|---:|']
 for r in cls:text.append(f"| {r['Target']} versus {r['Reference']} | {r['Metric']} | {r['Improved']} | {r['Worsened']} | {r['WithinTolerance']} |")
 text+=['','The network objectives average across nodes and do not impose a no-deterioration constraint at each node. Thus lower averages can coexist with increased ponding or longer flooding at particular locations. `d/worse.csv` identifies the largest deteriorations; `d/delta.csv` contains every paired observation. Increased flooding at an already flooded node is distinguished from a newly flooded node.']
 for r in cls:
  if r['Metric']=='Depth':text.append(f"For {r['Target']} versus {r['Reference']}, {r['NewlyFloodedNodes']} common nodes change from zero to positive native flooding duration.")
 text+=['','B retains A\'s outlet and flow paths while reallocating pipe capacity. C201 changes elevations, conduit orientations and outlet assignments as well as sizes. The maps and hydrographs describe those combined modeled effects. They do not establish that topology or hierarchy alone caused a change. Figure F6 compares total discharge across all outlets, not only discharge at original outlet 347.','',
 '## Numerical and interpretation limits','',
 '| Model | Flow continuity error (%) | Nonconverging steps (%) | Passes B candidate screen |',
 '|---|---:|---:|---|']
 for m in s:text.append(f"| {m} | {f(m,'FlowError_pct'):.6f} | {f(m,'Nonconv_pct'):.2f} | {'Yes' if f(m,'Nonconv_pct')<=5 else 'No'} |")
 text+=['','Independent fresh runs reproduce the selected objectives and every saved node metric, and complete native RPT/OUT files pass report/footer checks. C201 nevertheless has 6.73% nonconverging routing steps, exceeding the 5% screen used for B. Reproducibility does not remove this numerical limitation. A dedicated routing-step/tolerance sensitivity check is needed before treating the C201 ranking as definitive.', '',
 f"At the end of the three-hour event, {s['A']['FinalPondedCommonNodes']} common junctions in A, {s['B']['FinalPondedCommonNodes']} in B and {s['C201']['FinalPondedCommonNodes']} in C201 still have modeled ponding. Duration is therefore a window-limited measure. The large modeled depths should not be interpreted as mapped real surface inundation without terrain/ponding-area validation. Units remain feet and hours, as declared by the model.",'',
 f"The cost equation is extrapolated outside its published 12–54 in range for {s['B']['ExtrapolatedPipes']} B replacements and {s['C201']['ExtrapolatedPipes']} C201 replacements. This user-approved historical component-cost proxy is consistent across designs but is not a current total construction estimate.",'',
 '## Figure and data guide','',
 'M_AB_d/t, M_AC_d/t and M_BC_d/t are the six continuous maps; K_AB_d/t, K_AC_d/t and K_BC_d/t are the six classification maps. F4_all and F9_all combine the respective six figures. F1_search records convergence and screening, F2_front shows search/archives and final alternatives, F3_nodes shows paired node values and empirical distributions, F5_pipes shows diameter changes and the largest replacement costs, and F6_event shows rainfall, ponding, total outfall discharge and ponded-node counts. PNGs are 600 dpi, with vector PDF/SVG counterparts. All plotted numerical data are supplied as CSVs. ABC.xlsx contains network summaries, node and pipe tables, and generation summaries; detailed event series and all 5,000 evaluations are provided in the CSV files.','']
 from data import atomic
 atomic(ROOT/'Results.md','\n'.join(text).encode('utf-8'))
 print('Wrote Results.md')
if __name__=='__main__':main()
