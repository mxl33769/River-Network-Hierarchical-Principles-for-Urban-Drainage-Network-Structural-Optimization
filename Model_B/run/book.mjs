// Rebuild the workbook from data.py's book.json using @oai/artifact-tool.
// Usage: node book.mjs /absolute/path/d/book.json /absolute/path/ABC.xlsx
import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';
const [input,output]=process.argv.slice(2);
if(!input||!output) throw Error('Supply input book.json and output ABC.xlsx paths');
const d=JSON.parse(await fs.readFile(input,'utf8'));
const w=Workbook.create();
const sheets=Object.fromEntries(['Summary','Changes','Pipes','Nodes','Search'].map(n=>[n,w.worksheets.add(n)]));
const col=n=>String.fromCharCode(65+n);
function base(s,nrows,ncols){
 s.showGridLines=false;
 const r=s.getRangeByIndexes(0,0,nrows,ncols);
 r.format.font={name:'Arial',size:10,color:'#202b35'};
 r.format.columnWidth=17;r.format.rowHeight=21;r.format.verticalAlignment='center';
}
function header(s,row,labels){
 const r=s.getRangeByIndexes(row-1,0,1,labels.length);r.values=[labels];
 r.format.fill='#213e55';r.format.font={name:'Arial',size:10,bold:true,color:'#ffffff'};
 r.format.wrapText=true;r.format.rowHeight=34;
 r.format.horizontalAlignment='center';
}
function table(s,labels,rows){
 base(s,rows.length+1,labels.length);header(s,1,labels);
 s.getRangeByIndexes(1,0,rows.length,labels.length).values=rows;
 s.freezePanes.freezeRows(1);s.freezePanes.freezeColumns(1);
 s.getRangeByIndexes(1,1,rows.length,labels.length-1).setNumberFormat('0.0000');
}
const ns=sheets.Nodes;
const nkeys=['Node','X','Y','A_Depth_ft','B_Depth_ft','C201_Depth_ft','A_Time_h','B_Time_h','C201_Time_h','A_Final_ft','B_Final_ft','C201_Final_ft'];
table(ns,['Node','X (model)','Y (model)','A peak (ft)','B peak (ft)','C201 peak (ft)','A time (h)','B time (h)','C201 time (h)','A final (ft)','B final (ft)','C201 final (ft)'],d.nodes.map(r=>nkeys.map(k=>r[k])));
ns.getRange('B2:C526').setNumberFormat('0.00');
const index=Object.fromEntries(d.nodes.map((r,i)=>[r.Node,i+2]));
const ds=sheets.Changes;
table(ds,['Pair','Node','Ref peak (ft)','Target peak (ft)','Reduction (ft)','Depth class','Ref time (h)','Target time (h)','Reduction (h)','Time class','New flooding'],d.delta.map(r=>[r.Pair,r.Node,null,null,null,null,null,null,null,null,null]));
ds.getRange('F:F').format.columnWidth=22;ds.getRange('J:J').format.columnWidth=22;
ds.getRange('B2:B1576').setNumberFormat('0');
const modelcols={A:['D','G'],B:['E','H'],C201:['F','I']};
for(let i=0;i<d.delta.length;i++){
 const r=d.delta[i],j=i+2,k=index[r.Node],rc=modelcols[r.Reference],tc=modelcols[r.Target];
 ds.getRange(`C${j}:K${j}`).formulas=[[
  `=Nodes!${rc[0]}${k}`,`=Nodes!${tc[0]}${k}`,`=C${j}-D${j}`,
  `=IF(E${j}>Summary!$H$7,"Improved",IF(E${j}<-Summary!$H$7,"Worsened","Within tolerance"))`,
  `=Nodes!${rc[1]}${k}`,`=Nodes!${tc[1]}${k}`,`=G${j}-H${j}`,
  `=IF(I${j}>Summary!$H$8,"Improved",IF(I${j}<-Summary!$H$8,"Worsened","Within tolerance"))`,
  `=IF(AND(G${j}<=0.000000001,H${j}>0.000000001),1,0)`]];
}
ds.getRange(`K2:K${d.delta.length+1}`).setNumberFormat('0');
for(const c of ['E','I'])ds.getRange(`${c}2:${c}${d.delta.length+1}`).conditionalFormats.add('colorScale',{colors:['#edb2a6','#ffffff','#91bbdc'],thresholds:['min',0,'max']});
const ps=sheets.Pipes;
table(ps,['Pipe','Length (ft)','Barrels','A diameter (mm)','B diameter (mm)','C201 diameter (mm)','B cost (USD)','C201 cost (USD)','B added (m3)','C201 added (m3)','B extrapolated','C201 extrapolated'],d.pipes.map(r=>[r.Pipe,r.Length_ft,r.Barrels,r.A_mm,r.B_mm,r.C201_mm,null,null,null,null,r.B_Extrapolated,r.C201_Extrapolated]));
for(let i=0;i<d.pipes.length;i++){
 const j=i+2;
 ps.getRange(`G${j}:J${j}`).formulas=[[
  `=IF(E${j}>D${j}+0.000001,B${j}*C${j}*(Summary!$H$9+Summary!$H$10*(12*E${j}/Summary!$H$12)^Summary!$H$11),0)`,
  `=IF(F${j}>D${j}+0.000001,B${j}*C${j}*(Summary!$H$9+Summary!$H$10*(12*F${j}/Summary!$H$12)^Summary!$H$11),0)`,
  `=PI()/4*B${j}*C${j}*((E${j}/Summary!$H$12)^2-(D${j}/Summary!$H$12)^2)*Summary!$H$13`,
  `=PI()/4*B${j}*C${j}*((F${j}/Summary!$H$12)^2-(D${j}/Summary!$H$12)^2)*Summary!$H$13`]];
}
ps.getRange('G2:H531').setNumberFormat('"$"#,##0.00');
ps.getRange('C2:C531').setNumberFormat('0');ps.getRange('K2:L531').setNumberFormat('0');
const sk=['generation','unique_designs_including_A','feasible_unique_designs','rejected_unique_designs','archive_pareto_size','best_depth_ft','best_duration_h','compromise_depth_ft','compromise_duration_h','compromise_cost_usd','compromise_added_volume_m3','hypervolume_A_normalized'];
table(sheets.Search,['Generation','Unique designs','Feasible','Rejected','Archive size','Min depth (ft)','Min time (h)','Selected depth (ft)','Selected time (h)','Selected cost (USD)','Added volume (m3)','Normalized HV'],d.search.map(r=>sk.map(k=>Number(r[k]))));
sheets.Search.getRange('A2:E51').setNumberFormat('0');sheets.Search.getRange('J2:J51').setNumberFormat('"$"#,##0.00');
const s=sheets.Summary;base(s,43,8);s.tabColor='#213e55';
s.getRange('A:A').format.columnWidth=39;s.getRange('B:E').format.columnWidth=18;
s.getRange('F:F').format.columnWidth=3;s.getRange('G:G').format.columnWidth=26;s.getRange('H:H').format.columnWidth=21;
s.getRange('A2').values=[['Cost-constrained B: hydraulic comparison']];s.getRange('A2').format.font={name:'Arial',size:15,bold:true};
s.getRange('A3').values=[['Corrected rainfall; common 525 junctions; three-hour simulation']];
header(s,6,['Metric','A','B (cost)','C201']);
const settings=[['Budget (USD)',228499.91],['Depth tolerance (ft)',.01],['Time tolerance (h)',1/60],['Cost a',11.7],['Cost b',.51],['Cost exponent',1.38],['mm per ft',304.8],['m3 per ft3',.3048**3]];
s.getRange('G6:H13').values=settings;s.getRange('H6:H13').setNumberFormat('0.0000');s.getRange('H6').setNumberFormat('"$"#,##0.00');s.getRange('H6:H13').format.fill='#fff4cc';
const labels=['Mean peak ponded depth (ft)','Maximum ponded depth (ft)','Mean flooding duration (h)','Maximum flooding duration (h)','Compared junctions','Native junction count','Native mean peak (ft)','Native mean duration (h)','Replacement component (USD)','Added pipe volume (m3)','Enlarged pipes','Extrapolated replacements','Flow continuity error (%)','Nonconverging steps (%)','Passes B numerical screen','Ponded nodes at event end'];
s.getRange('A7:A22').values=labels.map(x=>[x]);
const checks=[];
for(let i=0;i<3;i++){
 const c=col(i+1),m=d.summary[i],nc=modelcols[m.Model];
 s.getRange(`${c}7:${c}10`).formulas=[`=AVERAGE(Nodes!${nc[0]}2:${nc[0]}526)`,`=MAX(Nodes!${nc[0]}2:${nc[0]}526)`,`=AVERAGE(Nodes!${nc[1]}2:${nc[1]}526)`,`=MAX(Nodes!${nc[1]}2:${nc[1]}526)`].map(f=>[f]);
 s.getRange(`${c}11:${c}14`).values=[[525],[m.NativeJunctionCount],[m.NativeMeanPeak_ft],[m.NativeMeanTime_h]];
 if(i){const pc=i===1?'G':'H',vc=i===1?'I':'J',ec=i===1?'K':'L';s.getRange(`${c}15:${c}18`).formulas=[[`=SUM(Pipes!${pc}2:${pc}531)`],[`=SUM(Pipes!${vc}2:${vc}531)`],[`=COUNTIF(Pipes!${pc}2:${pc}531,">0")`],[`=SUM(Pipes!${ec}2:${ec}531)`]];}else s.getRange(`${c}15:${c}18`).values=[[0],[0],[0],[0]];
 s.getRange(`${c}19:${c}22`).values=[[m.FlowError_pct],[m.Nonconv_pct],[m.PassesB5pctScreen?'Yes':'No'],[m.FinalPondedCommonNodes]];
 for(const [row,key]of [[7,'MeanPeak_ft'],[8,'MaxPeak_ft'],[9,'MeanTime_h'],[10,'MaxTime_h'],[15,'ReplacementCost_USD'],[16,'AddedVolume_m3'],[17,'EnlargedPipes']])checks.push([`${c}${row}`,m[key]]);
}
s.getRange('B7:D22').setNumberFormat('0.0000');s.getRange('B15:D15').setNumberFormat('"$"#,##0.00');
for(const row of [11,12,17,18,22])s.getRange(`B${row}:D${row}`).setNumberFormat('0');
s.getRange('D20:D21').format.fill='#fce6dc';
s.getRange('A24').values=[['Node change classification']];s.getRange('A24').format.font.bold=true;
header(s,26,['Pair','Metric','Improved','Worsened','Within tolerance']);
for(let i=0;i<6;i++){
 const j=i+27,r=d.classes[i],cc=r.Metric==='Depth'?'F':'J';
 s.getRange(`A${j}:B${j}`).values=[[r.Pair,r.Metric]];
 for(let k=0;k<3;k++){const c=col(k+2),name=['Improved','Worsened','Within tolerance'][k];s.getRange(`${c}${j}`).formulas=[[`=COUNTIFS(Changes!$A$2:$A$1576,A${j},Changes!$${cc}$2:$${cc}$1576,"${name}")`]];checks.push([`${c}${j}`,r[['Improved','Worsened','WithinTolerance'][k]]]);}
}
s.getRange('C27:E32').setNumberFormat('0');
s.getRange('A35').values=[['AB: A minus new B. AC: A minus C201. BC: new B minus C201.']];
s.getRange('A36').values=[['Positive differences indicate improvement; tolerances are descriptive, not significance tests.']];
s.getRange('A37').values=[['C201 exceeds the 5% nonconvergence screen. Its hydraulic comparison is provisional.']];
s.getRange('A38').values=[['Five converted outlets are excluded from all paired comparisons, not assigned zeros.']];
s.getRange('A40').values=[['Sources: supplied A/C201 INPs and fresh SWMM runs. Cost: Clark et al. (2002), Table 2.']];
s.getRange('A41').values=[['Historical 1997 cost basis; authorized size extrapolation; excludes excavation and outfall works.']];
s.getRange('A42').values=[['https://doi.org/10.1061/(ASCE)0733-9496(2002)128:5(312)']];
w.recalculate();
for(const [address,expected]of checks){const actual=s.getRange(address).values[0][0];if(Math.abs(actual-expected)>1e-6)throw Error(`${address}: ${actual} != ${expected}`);}
// Check every classification, not only aggregated totals.
const classifications=ds.getRange('F2:J1576').values;
classifications.forEach((r,i)=>{if(r[0]!==d.delta[i].DepthClass||r[4]!==d.delta[i].TimeClass)throw Error(`Class mismatch ${i}`);});
console.log('Independent summary and node-class checks passed:',checks.length);
console.log((await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!',options:{useRegex:true,maxResults:20},summary:'Formula error scan'})).ndjson);
const outdir=path.dirname(output);await fs.mkdir(outdir,{recursive:true});
for(const [name,range]of [['Summary','A1:H42'],['Changes','A1:K12'],['Pipes','A1:L12'],['Nodes','A1:L12'],['Search','A1:L12']]){
 const b=await w.render({sheetName:name,range,scale:1.5,format:'png'});await fs.writeFile(path.join(outdir,`qa_${name}.png`),new Uint8Array(await b.arrayBuffer()));
}
await(await SpreadsheetFile.exportXlsx(w)).save(output);
console.log('Saved',output);
