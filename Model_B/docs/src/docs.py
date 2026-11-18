"""Build the four editable Word documents; equations use native Office Math."""
from pathlib import Path
from copy import deepcopy
import csv,json,re
from docx import Document
from docx.shared import Inches,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from texts import METHODS,RESULTS,SI,REFS
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'out';OUT.mkdir(exist_ok=True)
def el(name,**attrs):
 x=OxmlElement('m:'+name)
 for k,v in attrs.items():x.set(qn('m:'+k),str(v))
 return x
def run(t):
 x=el('r');pr=el('rPr');pr.append(el('sty',val='p'));x.append(pr);a=el('t');a.text=str(t);x.append(a);return x
def put(x,seq):
 if not isinstance(seq,(list,tuple)):seq=[seq]
 for a in seq:x.append(run(a) if isinstance(a,str) else deepcopy(a))
 return x
def sub(a,b):
 x=el('sSub');x.append(put(el('e'),a));x.append(put(el('sub'),b));return x
def sup(a,b):
 x=el('sSup');x.append(put(el('e'),a));x.append(put(el('sup'),b));return x
def frac(a,b):
 x=el('f');x.append(put(el('num'),a));x.append(put(el('den'),b));return x
def summ(lo,hi,body):
 x=el('nary');pr=el('naryPr');pr.append(el('chr',val='∑'));pr.append(el('limLoc',val='undOvr'));x.append(pr)
 x.append(put(el('sub'),lo));x.append(put(el('sup'),hi));x.append(put(el('e'),body));return x
FD=sub('f','d');FT=sub('f','t');De=sub('D','e');Hi=sub('H','i')
EQ={
'choices':[De,' = ',sub('D','e'),'(',sub('z','e'),') ∈ ',sub('𝒟','e'),',   ',sub('z','e'),' ∈ {0,…,',sub('m','e'),'},   ',De,' ≥ ',sub('D','e,0')],
'objectives':[sub('min','z'),' (',FD,'(z), ',FT,'(z)),   ',FD,' = ',frac('1','N'),summ('i=1','N',sub('d','i,max')),',   ',FT,' = ',frac('1','N'),summ('i=1','N',Hi)],
'depth':[sub('d','i,max'),' = 1[',Hi,' > 0] max(0, ',sub('y','i,max'),' − ',sub('h','i,full'),')'],
'cost':['K(z) = ',summ('e=1','530',[sub('I','e'),sub('L','e'),sub('b','e'),'[11.7 + 0.51',sup(['(12',De,')'],'1.38'),']']),' ≤ ',sub('K','C'),' = 228,499.91 USD'],
'select':[sup('z','*'),' = ',sub('arg min','z∈𝒫'),sup(['[',sup(['(',frac(FD,sub('f','d,A')),')'],'2'),' + ',sup(['(',frac(FT,sub('f','t,A')),')'],'2'),']'],'1/2')],
'pareto':['P(',sub('A','u'),' ≥ a) = 0.95',sup('a','−ε'),sup('e','−ca')],
'rb':[sub('R','b'),' = ',frac('1','Ω−1'),summ('ω=1','Ω−1',frac(sub('N','ω'),sub('N','ω+1')))]}
def new(title,note):
 d=Document();s=d.sections[0];s.page_width=Inches(8.5);s.page_height=Inches(11);s.top_margin=Inches(.72);s.bottom_margin=Inches(.68);s.left_margin=s.right_margin=Inches(.8)
 for n in ['Normal','Title','Heading 1','Heading 2','Caption']:
  st=d.styles[n];st.font.name='Times New Roman';st.font.color.rgb=RGBColor(0,0,0)
 for st in d.styles:
  for b in list(st.element.iter(qn('w:pBdr'))):b.getparent().remove(b)
  for f in st.element.iter(qn('w:rFonts')):
   for k in list(f.attrib):
    if 'theme' in k.lower():del f.attrib[k]
 d.styles['Normal'].font.size=Pt(11);d.styles['Normal'].paragraph_format.line_spacing=1.08;d.styles['Normal'].paragraph_format.space_after=Pt(7)
 d.styles['Title'].font.size=Pt(18);d.styles['Title'].paragraph_format.space_after=Pt(9)
 d.styles['Heading 1'].font.size=Pt(12);d.styles['Heading 1'].paragraph_format.space_before=Pt(11);d.styles['Heading 1'].paragraph_format.space_after=Pt(6)
 d.styles['Heading 2'].font.size=Pt(11);d.styles['Caption'].font.size=Pt(10);d.styles['Caption'].font.bold=False
 d.add_paragraph(title,'Title');p=d.add_paragraph(note);p.runs[0].italic=True;p.runs[0].font.size=Pt(9)
 f=s.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.RIGHT;f.add_run('Manuscript revision draft  |  ');a=OxmlElement('w:fldSimple');a.set(qn('w:instr'),'PAGE');f._p.append(a)
 return d
def equation(d,key,num):
 p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(8);m=el('oMath');put(m,EQ[key]);p._p.append(m);p.add_run('   ('+num+')')
def table(d,headers,rows,widths):
 t=d.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
 for c,w in zip(t.columns,widths):c.width=Inches(w)
 for c,v in zip(t.rows[0].cells,headers):c.text=str(v)
 b=OxmlElement('w:tblBorders')
 for side in ['top','left','bottom','right','insideH','insideV']:
  x=OxmlElement('w:'+side);x.set(qn('w:val'),'single');x.set(qn('w:sz'),'4');x.set(qn('w:color'),'D9D9D9');b.append(x)
 t._tbl.tblPr.append(b)
 for row in rows:
  for c,v in zip(t.add_row().cells,row):c.text=str(v)
 for ir,row in enumerate(t.rows):
  pr=row._tr.get_or_add_trPr();pr.append(OxmlElement('w:cantSplit'))
  if ir==0:pr.append(OxmlElement('w:tblHeader'))
  for ic,c in enumerate(row.cells):
   c.width=Inches(widths[ic]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
   cp=c._tc.get_or_add_tcPr();mar=OxmlElement('w:tcMar')
   for side in ['top','bottom','left','right']:
    x=OxmlElement('w:'+side);x.set(qn('w:w'),'80');x.set(qn('w:type'),'dxa');mar.append(x)
   cp.append(mar)
   if ir==0:
    x=OxmlElement('w:shd');x.set(qn('w:fill'),'E8EDF2');cp.append(x)
   for p in c.paragraphs:
    p.paragraph_format.space_after=Pt(1);p.paragraph_format.line_spacing=1.0
    if ic>0:p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in p.runs:r.font.size=Pt(9.5);r.bold=ir==0
 d.add_paragraph().paragraph_format.space_after=Pt(1)
def csvrows(p):return list(csv.DictReader(p.open(encoding='utf-8-sig')))
def addtable(d,key):
 if key=='network':
  s={x['Model']:x for x in csvrows(ROOT/'data/summary.csv')};rf={x['model']:x for x in csvrows(ROOT/'data/refs.csv')}
  rows=[]
  for label,k,fmt in [('Mean maximum ponded depth (ft)','MeanPeak_ft','.3f'),('Maximum ponded depth (ft)','MaxPeak_ft','.3f'),('Mean flooding duration (h)','MeanTime_h','.3f'),('Maximum flooding duration (h)','MaxTime_h','.3f'),('Replacement component cost (USD)','ReplacementCost_USD',',.2f'),('Added internal pipe volume (m³)','AddedVolume_m3','.2f'),('Enlarged pipes','EnlargedPipes','d'),('Ponded junctions at 3 h','FinalPondedCommonNodes','d'),('Flow continuity error (%)','FlowError_pct','.3f'),('Nonconverging routing steps (%)','Nonconv_pct','.2f')]:
   rows.append([label]+[format(int(float(s[m][k])) if fmt=='d' else float(s[m][k]),fmt) for m in ['A','B','C201']])
  rows.insert(2,['Mean maximum node depth (ft)']+[f"{float(rf[m]['mean_node_ft']):.3f}" for m in ['A','Bc','C201']])
  d.add_paragraph('Table 1. Design and hydraulic comparison under the common corrected rainfall.','Caption');table(d,['Metric','A','B','C201'],rows,[3.35,1.05,1.05,1.05]);d.add_paragraph('Hydraulic statistics use 521 permanent junctions. Cost is a historical replacement-component proxy. C201 exceeds the primary 5% nonconvergence screen; its sensitivity record is described in the text.','Caption')
 elif key=='nodes':
  rows=[[r['Target']+' vs '+r['Reference'],r['Metric'],r['Improved'],r['WithinTolerance'],r['Worsened'],r['NewlyFloodedNodes']] for r in csvrows(ROOT/'data/classes.csv')]
  d.add_paragraph('Table 2. Local hydraulic changes at the same 521 junctions.','Caption');table(d,['Comparison','Metric','Lower','Within','Higher','Newly flooded'],rows,[1.25,1.15,.7,.7,.7,1.05]);d.add_paragraph('Lower/higher refers to the target relative to the reference. Tolerances: 0.01 ft and 1 min. Newly flooded is a node count shared by both metric rows, not an additional count to sum.','Caption')
 elif key=='params':
  rows=[['SWMM engine / Python toolkit','5.2.4 / 0.17.0'],['Optimizer','NSGA-II; pymoo 0.6.1.3'],['Population / generations / seed','100 / 50 / 7'],['Crossover','SBX: probability 0.9, η = 15'],['Mutation','Polynomial: probability 1; per variable 1/530; η = 20'],['Initialization','Unchanged A plus sparse random designs'],['Survival','Nondominated rank, then crowding distance'],['Repair','Round and bound; remove excess active pipes; downgrade until affordable'],['Diameter / pipe-count ceiling','2000 mm / 112 pipes'],['Replacement allowance','$228,499.91'],['Rainfall / simulation period','Same corrected input / 3 h'],['Routing / minimum step','5 / 0.5 s; variable-step factor 0.75'],['Reporting interval','60 s; objectives from native routing statistics'],['Max trials / head tolerance','160 / 0.005 ft'],['Ponding','Enabled; retained node parameters'],['Numerical rejection rules','|Runoff error| > 5%; |flow error| > 5%; nonconvergence > 5%'],['Execution','8 workers; 120 s timeout per candidate'],['Checkpoints','Every generation; durable snapshot every 5'],['Metric populations','530 during B search; fixed 521 for cross-model comparisons']]
  d.add_paragraph('Table S4. Recorded search and solver settings.','Caption');table(d,['Item','Setting'],rows,[2.35,4.15])
 elif key=='Ecounts':
  d.add_paragraph('Table S6. Primary E comparisons against the indicated reference.','Caption');table(d,['Reference and set','n','Better both','Worse both','Within both','Mixed'],[['A; cost cap',93,93,0,0,0],['B; cost cap',93,89,0,0,4],['C; cost cap',92,22,15,2,53],['C; 95–100% band',12,8,0,0,4]],[1.95,.45,.95,.95,.95,.65])
def refs(d,keys):
 d.add_heading('References',1)
 for k in keys:
  txt,url=REFS[k];p=d.add_paragraph(txt+' ');p.paragraph_format.space_after=Pt(4);p.paragraph_format.line_spacing=1.0
  for r in p.runs:r.font.size=Pt(9.5)
  h=OxmlElement('w:hyperlink');h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True));r=OxmlElement('w:r');pr=OxmlElement('w:rPr');sz=OxmlElement('w:sz');sz.set(qn('w:val'),'19');pr.append(sz);r.append(pr);t=OxmlElement('w:t');t.text=url;r.append(t);h.append(r);p._p.append(h)
def make(name,title,seq,keys,note):
 words=sum(len(re.findall(r'\b[\w–−]+\b',t)) for k,t in seq if k in ['h','p'])
 d=new(title,note+f' Draft prose: {words:,} words, excluding equations, tables, insertion notes and references.');eqn=0
 for k,t in seq:
  if k=='h':d.add_heading(t,1)
  elif k=='eq':eqn+=1;equation(d,t,('S' if name=='SI_E' else 'B')+str(eqn))
  elif k=='table':addtable(d,t)
  else:
   p=d.add_paragraph(t)
   if k=='insert':
    for r in p.runs:r.italic=True;r.font.size=Pt(9)
 refs(d,keys);d.save(OUT/(name+'.docx'));return words
wc={}
wc['Methods_BE']=make('Methods_BE','Methodology for Models B and E',METHODS,['Deb','Ngamalieu','Clark','Rossman','Bakhshipour'],'Replacement text for Section 2.5 and new Section 2.6. B is cost-constrained; C means C201. Renumber the temporary equation labels on insertion.')
wc['Results_BCE']=make('Results_BCE','Results and discussion for Models B C and E',RESULTS,['Bakhshipour','Hesarkazzazi','Rossman','Yang'],'Replacement hydraulic results and discussion. Values are audited native outputs, not the conflicting edited values in current manuscript tables. All primary comparisons use 521 junctions.')
wc['SI_E']=make('SI_E','Supplementary methods and results',SI,['Deb','Ngamalieu','Clark','Yang'],'Supporting material for the main B–C201 comparison and cost-aligned Experiment E. Historical reports are preserved separately.')
d=new('Manuscript insertion and verification guide','Use with WRR_Manuscript.docx dated 24 September 2026. This is an editing guide, not article text. The source manuscript has not been changed.')
d.add_heading('Scope and word budget',1)
d.add_paragraph(f"Methods_BE and Results_BCE contain {wc['Methods_BE']+wc['Results_BCE']} prose words combined; SI_E contains {wc['SI_E']} words. Equations, tables, insertion notes and references are additional. B denotes cost-constrained e04701, C denotes C201, and E denotes the cost-aligned enumeration. B+ and D remain historical supporting records.")
d.add_heading('Required data reconciliation',1)
d.add_paragraph('The current manuscript tables do not reproduce the archived native SWMM results. Preserve their edited values in the source record, but do not combine them with the new node maps or percentages. The supplied draft proposes replacing them with auditable 521-junction statistics. No results have been adjusted to force agreement. Review this explicit replacement before merging the draft.')
table(d,['Quantity','Current manuscript','Audited comparison'],[['A mean depth (ft)','4.169','22.258824 (mean maximum ponded depth)'],['C mean depth (ft)','3.640','18.664043 (same definition)'],['A / C maximum depth (ft)','19.85 / 10.47','123.362948 / 122.853851'],['C hierarchy ε / Rb','0.43 / 4.33','0.254883 / 1.868842'],['B design','Volume-based result','Cost-constrained e04701']],[2.1,1.8,2.6])
d.add_paragraph('Changing the population from 525 to 521 cannot explain these differences. Do not relabel maximum node depth as ponded depth or infer missing node measurements from manuscript averages.')
d.add_heading('Exact editing locations',1)
edits=[
('Section 2.3: replace metric definitions','Locate the paragraph beginning “Both original and hierarchically optimized network configurations were subjected to identical 10-year design storm conditions”. Retain the shared corrected rainfall description but replace its vague flooding-definition and “validation framework” statements with the native depth, duration and population definitions in new Section 2.5. Replace “Rossman et al., 2022” with “Rossman and Simon, 2022”. The 10-year designation is inherited; this package does not independently establish the return period.'),
('Section 2.4: update experiment linkage','Remove B+ and D from the present main-text comparison and remove equal-pipe-volume claims for the current B. Add: “The structural search supplies candidate outlet locations; Model C is implemented using the recovered C201 construction procedure, and the cost-constrained hydraulic benchmark and outlet enumeration are described in Sections 2.5 and 2.6.”'),
('Section 2.4: replace C implementation passage','Locate the passage describing outlet elevation, minimum slope and automatic 1.2-times confluence enlargement. Replace it with SI_E Section S2, first paragraph, or add: “The selected outlet set is implemented using the C201 tracing, elevation and conservative sizing procedure documented in Text S2.” Do not claim that the implemented C201 reproduces the historical structural-search indicators.'),
('Replace all of Section 2.5','Delete from “2.5. Matched hydraulic pipe optimization” to immediately before “3 Results, or a descriptive heading about the results”, including duplicate subsection numbers and the old parameter table. Insert Methods_BE Sections 2.5 and 2.6. Put the configuration in Table S4; renumber equations B1–B5 consecutively after the existing equations.'),
('Section 3.1: replace original A hydraulic paragraph','Locate “Figure 3 presents hydraulic simulation results under the 10-year rainfall event scenario”. Replace the paragraph, including the 531-flooded-node claim and 4.17 ft / 19.85 ft values, with: “Hydraulic performance of the original network is evaluated together with the two interventions under a common model configuration and node population in Section 3.2 and Table 1.” Rebuild or remove Figure 3 if it displays incompatible metrics.'),
('Section 3.2: distinguish historical structural search','Under “3.2. Optimal Structure Generation and Selection Guided by Hierarchical Targets”, retain documented original NSGA-III evolution only as historical candidate-generation evidence. Delete the linkage asserting that implemented C201 has ε ≈ 0.43 and Rb ≈ 4.33. Do not use original Figure 4 as evidence of recomputed C201 metrics. Move it to SI only if its source and implementation are identifiable; otherwise hold it from the revised results.'),
('Replace hydraulic results and discussion','Replace the passage beginning “Table 2 and Figures F3-F6 compare A, B, B+, C, and D”, subsequent hydraulic comparison text, Tables 1–3, Figures 5–6, editorial placeholders, and “Applying River Network Hierarchy to UDN Modification: Performance and Insights”, up to but not including “4 Limitations”. Insert Results_BCE Sections 3.2–3.5. Remove old 24-layout correlations (−0.85, 0.90) and historical Figure 7 unless separately documented and labeled as another experiment.'),
('Append SI and merge references','Insert SI_E after the existing supplementary simulation settings as Text S1–S4. Merge bibliography entries once, preserving author–year citation style. Correct author order in Hesarkazzazi et al. (2022b) to Bakhshipour before Hajibabaei. Do not attribute the study-specific objectives or repair rules verbatim to Ngamalieu-Nengoue et al. (2019).'),
('Remaining manuscript sections','Subsequently reconcile the abstract, conclusions, limitations, data availability and captions. Remove obsolete volume-budget descriptions, universal optimum claims and historical C percentages. The current drafts do not silently rewrite these sections.')]
for h,p in edits:d.add_heading(h,2);d.add_paragraph(p)
d.add_heading('Figure and table insertion map',1)
d.add_paragraph('Table S3 remains the existing diameter catalogue. New SI tables start at S4. Figure numbers below are provisional insertion labels; reconcile them with retained SI figures before submission.')
table(d,['Item','File or data','Position'],[['Figure 5','ABC_color.png','After B–C mechanism discussion'],['Figure 6','F4_all.png','After node-change counts'],['Figures S1–S2','F1_search / F2_front','Search and archive'],['Figures S3–S4','F9_all / F3_nodes','Node classes/distributions'],['Figure S5','F6_event','Event response'],['Figures S6–S9','E_cost / E_near / E_hier / E_nodes','E sensitivity'],['Table 1','Results_BCE Table 1','Network comparison'],['Table 2','Results_BCE Table 2','Local changes'],['Table S4','SI_E Table S4','Search/solver settings'],['Table S5','provenance.csv','Definitions and sources'],['Table S6','SI_E Table S6','E comparison counts'],['Table S7','Model E/cost/data/layouts.csv','All 126 layouts']],[1.05,2.7,2.75])
d.add_heading('Evidence limits to retain',1)
d.add_paragraph('C201 completes a saved engine run but exceeds the primary nonconvergence screen. Finer-step checks cover 75 of 93 cost-admissible E layouts. Historical Hack data are missing. Costs cover replacement components, not total construction. Large model ponding depths are not field-validated surface depths. The comparisons evaluate complete interventions, not an isolated causal effect of hierarchy.')
d.save(OUT/'Insert_Guide.docx');(OUT/'word_counts.json').write_text(json.dumps(wc,indent=2));print(wc)
