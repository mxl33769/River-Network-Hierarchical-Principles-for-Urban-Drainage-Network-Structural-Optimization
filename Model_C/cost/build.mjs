import fs from 'node:fs/promises';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const input = process.argv[2];
const out = process.argv[3];
const data = JSON.parse(await fs.readFile(input, 'utf8'));
const wb = Workbook.create();
const cost = wb.worksheets.add('Cost');
const rules = wb.worksheets.add('Rules');
const first = 21;
const last = first + data.pipes.length - 1;
const money = '"$"#,##0.00;("$"#,##0.00);"-"';

for (const sheet of [cost, rules]) {
  sheet.showGridLines = false;
  sheet.getRange(sheet === cost ? `A1:J${last}` : 'A1:F39').format.font = { name: 'Arial', size: 10 };
  sheet.getRange(sheet === cost ? `A1:J${last}` : 'A1:F39').format.rowHeight = 21;
  sheet.getRange(sheet === cost ? `A1:J${last}` : 'A1:F39').format.verticalAlignment = 'center';
}
function header(sheet, range) {
  sheet.getRange(range).format = {
    fill: '#3B4643', font: { name: 'Arial', size: 10, color: '#FFFFFF', bold: true },
    horizontalAlignment: 'center', verticalAlignment: 'center', wrapText: true, rowHeight: 32,
  };
}
cost.getRange('A2').values = [['C201 pipe replacement cost']];
cost.getRange('A2').format.font = { name: 'Arial', size: 14, bold: true };
cost.getRange('A3:J3').format.borders = { bottom: { style: 'thin', color: '#919999' } };
cost.getRange('A5:A8').values = [
  ['Priced subtotal (1997 USD)'], ['Unpriced replacements'], ['Full replacement budget'], ['Diameter-changed pipes'],
];
cost.getRange('D5').formulas = [[`=SUM(J${first}:J${last})`]];
cost.getRange('D6').formulas = [[`=COUNTIFS(H${first}:H${last},"Unpriced")`]];
cost.getRange('D7').formulas = [['=IF(D6>0,"Incomplete",D5)']];
cost.getRange('D8').formulas = [[`=COUNTIFS(H${first}:H${last},"Priced")+COUNTIFS(H${first}:H${last},"Unpriced")`]];
cost.getRange('D5').setNumberFormat(money);
cost.getRange('D5:D8').format.font = { name: 'Arial', size: 11, bold: true };
cost.getRange('D7').conditionalFormats.addCustom('D6>0', { fill: '#FCE8E6', font: { color: '#A12820' } });
cost.getRange('A10').values = [['No extrapolation. Unpriced replacements are missing costs, not zero-cost work.']];
cost.getRange('A12:F12').values = [['New size (mm)', 'Pipes', 'Length (ft)', 'Equation', 'Unit cost ($/ft)', 'Cost subtotal ($)']];
header(cost, 'A12:F12');
data.groups.forEach((group, i) => {
  const r = 13 + i;
  cost.getRange(`A${r}`).values = [[group.new_mm]];
  cost.getRange(`B${r}:F${r}`).formulas = [[
    `=COUNTIFS(C$${first}:C$${last},A${r})`,
    `=SUMIFS(D$${first}:D$${last},C$${first}:C$${last},A${r})`,
    `=IF(AND(A${r}>='Rules'!B$5,A${r}<='Rules'!C$5),"Eq. 5",IF(AND(A${r}>='Rules'!B$6,A${r}<='Rules'!C$6),"Eq. 6","None"))`,
    `=IF(D${r}="None","Unpriced",IF(D${r}="Eq. 5",'Rules'!D$5+'Rules'!E$5*(A${r}/'Rules'!D$8)^'Rules'!F$5,'Rules'!D$6+'Rules'!E$6*(A${r}/'Rules'!D$8)^'Rules'!F$6))`,
    `=IF(D${r}="None","Unpriced",SUMIFS(J$${first}:J$${last},C$${first}:C$${last},A${r}))`,
  ]];
});
cost.getRange('A13:A16').setNumberFormat('0');
cost.getRange('C13:C16').setNumberFormat('#,##0.00');
cost.getRange('E13:F16').setNumberFormat(money);
cost.getRange('A18').values = [['Source: C201.zip / pipes.csv. A_mm and NewC_mm checked against A.inp and C.inp.']];
cost.getRange('A19').values = [['Each priced replacement includes its full length and new pipe size. Elevation-only changes are excluded.']];
cost.getRange('A20:J20').values = [[
  'Pipe ID', 'Old size (mm)', 'New size (mm)', 'Length (ft)', 'Barrels', 'New size (in)',
  'Equation', 'Status', 'Unit cost ($/ft)', 'Cost ($)',
]];
header(cost, 'A20:J20');
cost.getRange(`A${first}:E${last}`).values = data.pipes.map(p => [p.pipe_id, p.old_mm, p.new_mm, p.length_ft, p.barrels]);
cost.getRange(`B${first}:E${last}`).format.font.color = '#1761A0';
cost.getRange(`F${first}:J${last}`).formulas = data.pipes.map((p, i) => {
  const r = first + i;
  return [
    `=C${r}/'Rules'!$D$8`,
    `=IF(AND(C${r}>='Rules'!$B$5,C${r}<='Rules'!$C$5),"Eq. 5",IF(AND(C${r}>='Rules'!$B$6,C${r}<='Rules'!$C$6),"Eq. 6","None"))`,
    `=IF(G${r}="None","Unpriced","Priced")`,
    `=IF(G${r}="Eq. 5",'Rules'!$D$5+'Rules'!$E$5*F${r}^'Rules'!$F$5,IF(G${r}="Eq. 6",'Rules'!$D$6+'Rules'!$E$6*F${r}^'Rules'!$F$6,"Unpriced"))`,
    `=IF(H${r}="Priced",D${r}*E${r}*I${r},"Unpriced")`,
  ];
});
cost.getRange(`B${first}:D${last}`).setNumberFormat('#,##0.00');
cost.getRange(`F${first}:F${last}`).setNumberFormat('0.0000');
cost.getRange(`I${first}:J${last}`).setNumberFormat(money);
cost.getRange(`H${first}:J${last}`).conditionalFormats.addCustom(`$H${first}="Unpriced"`, { fill: '#FFF2D6', font: { color: '#7A4E0C' } });
cost.getRange(`A${first}:J${last}`).format.horizontalAlignment = 'right';
cost.getRange(`A${first}:A${last}`).format.horizontalAlignment = 'left';
for (const [col, width] of Object.entries({ A: 15, B: 17, C: 17, D: 19, E: 18, F: 22, G: 15, H: 17, I: 21, J: 21 })) {
  cost.getRange(`${col}1:${col}${last}`).format.columnWidth = width;
}
cost.freezePanes.freezeRows(20);

rules.getRange('A2').values = [['Cost rules and source']];
rules.getRange('A2').format.font = { name: 'Arial', size: 14, bold: true };
rules.getRange('A4:F6').values = [
  ['Equation', 'Min. size (mm)', 'Max. size (mm)', 'a', 'b', 'Exponent p'],
  ['Eq. 5', 304.8, 1371.6, 11.7, 0.51, 1.38],
  ['Eq. 6', 1524, 3657.6, 7.9, 1.30, 1.25],
];
header(rules, 'A4:F4');
rules.getRange('B5:F6').format.font.color = '#1761A0';
rules.getRange('A8').values = [['Millimetres per inch']];
rules.getRange('D8').values = [[25.4]];
rules.getRange('A9').values = [['Price basis year']];
rules.getRange('D9').values = [[1997]];
rules.getRange('A11').values = [['Unit cost ($/ft) = a + b * [new diameter (in)]^p. Range endpoints are inclusive.']];
rules.getRange('A13').values = [['Clark, R. M., Sivaganesan, M., Selvakumar, A., and Sethi, V. (2002).']];
rules.getRange('A14').values = [['Cost Models for Water Supply Distribution Systems. JWRPM, 128(5), 312-321.']];
rules.getRange('A15').values = [['https://doi.org/10.1061/(ASCE)0733-9496(2002)128:5(312)']];
rules.getRange('A16').values = [['Table 2 supplies product ranges and coefficients; Use of Indices supplies the price basis.']];
rules.getRange('A18').values = [['Eq. 5 represents concrete cylinder pipe. Eq. 6 represents prestressed concrete cylinder pipe.']];
rules.getRange('A19').values = [['Product selection follows the supplied equations by size; actual installed material is not verified.']];
rules.getRange('A21').values = [['Only diameter-changed pipes are counted. No trenching, outlets, or elevation-only work is priced.']];
rules.getRange('A22').values = [['The complete budget stays unavailable until every changed pipe has a supported unit cost.']];
rules.getRange('A24').values = [['Table S3 candidate sizes: cost-equation coverage']];
rules.getRange('A25:C25').values = [['Size (mm)', 'Applicable equation', 'Coverage']];
header(rules, 'A25:C25');
const sizes = [150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600, 2000];
rules.getRange('A26:A40').values = sizes.map(v => [v]);
rules.getRange('B26:C40').formulas = sizes.map((v, i) => {
  const r = 26 + i;
  return [
    `=IF(AND(A${r}>=$B$5,A${r}<=$C$5),"Eq. 5",IF(AND(A${r}>=$B$6,A${r}<=$C$6),"Eq. 6","None"))`,
    `=IF(B${r}="None","Missing cost","Within range")`,
  ];
});
rules.getRange('C26:C40').conditionalFormats.addCustom('$C26="Missing cost"', { fill: '#FFF2D6', font: { color: '#7A4E0C' } });
for (const col of ['A','B','C','D','E','F']) rules.getRange(`${col}1:${col}40`).format.columnWidth = col === 'A' ? 27 : 24;

wb.recalculate();
if (Math.abs(cost.getRange('D5').values[0][0] - data.priced_subtotal_usd) > 1e-7 || cost.getRange('D6').values[0][0] !== 13 || cost.getRange('D7').values[0][0] !== 'Incomplete') {
  throw new Error('Workbook/Python totals mismatch');
}
// Check that input changes affect both detailed costs and budget completeness.
const originalSize = cost.getRange('C21').values[0][0];
cost.getRange('C21').values = [[400]];
wb.recalculate();
if (cost.getRange('D6').values[0][0] !== 12 || cost.getRange('H21').values[0][0] !== 'Priced') throw new Error('Coverage recalculation failed');
cost.getRange('C21').values = [[originalSize]];
wb.recalculate();
console.log((await wb.inspect({kind:'table', range:'Cost!A5:D8', include:'values,formulas', tableMaxRows:4, tableMaxCols:4})).ndjson);
console.log((await wb.inspect({kind:'match', searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!', options:{useRegex:true,maxResults:20}})).ndjson);
await fs.mkdir(out, {recursive:true});
for (const [sheetName, range, file] of [['Cost','A1:J25','cost_preview.png'],['Rules','A1:F22','rules_preview.png'],['Rules','A24:C40','sizes_preview.png']]) {
  const preview = await wb.render({sheetName, range, scale:1.4, format:'png'});
  await fs.writeFile(`${out}/${file}`,new Uint8Array(await preview.arrayBuffer()));
}
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(`${out}/C201_cost.xlsx`);
console.log(JSON.stringify({output:`${out}/C201_cost.xlsx`,priced:data.priced_subtotal_usd,unpriced:data.unpriced_pipes}));
