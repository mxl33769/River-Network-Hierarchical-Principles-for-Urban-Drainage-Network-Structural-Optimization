# C201 changed-pipe cost audit

Only pipes whose diameter changed between Model A and C201 are included.
The basis is the saved C201.zip design table, pipes.csv, comparing A_mm with
NewC_mm. OldC_mm refers to a different earlier design and is not the baseline.
All 530 table rows were checked against A.inp and C.inp, including diameters,
lengths and barrel counts. The unchanged input bytes are in src.zip.

## Results

45 pipes changed diameter. Equation (5) prices 32 of them at a subtotal of
194680.31241559482 USD. The 13 replacements at 200 mm, totaling 1650 ft, have
no applicable equation and remain unpriced. The complete budget is unknown.
There are no Eq. (6) replacements in C201.

The earlier 228499.91 USD estimate applied Eq. (5) outside its fitted range
and is superseded by this no-extrapolation audit. 194680.31 USD is a partial
subtotal, not a full C201 budget and not an authorized optimization ceiling.
No SWMM simulation or optimization was launched by this audit.

## Cost rules

Clark et al. (2002), Table 2, gives the base-installed product equations.
Equation (5), concrete cylinder pipe, covers 304.8 through 1371.6 mm.
Equation (6), prestressed concrete cylinder pipe, covers 1524 through 3657.6 mm.
Endpoints are inclusive. Rates are USD/ft, with diameter entered in inches.
The original article uses a 1997 price basis; no inflation adjustment is used.
Choosing an equation by size is the requested comparison convention, not
verification of the actual pipe material in the SWMM model.

Replacement component cost = length_ft * barrels * cost(new_diameter_in).
The original pipe's price is not subtracted. Elevation-only changes, new
outlets, excavation, embedment, backfill and other project costs are excluded.
Missing costs are never treated as zero. The functions return None/null for
unpriced pipes and for a complete budget that has missing components.

Citation: Clark, R. M., Sivaganesan, M., Selvakumar, A., and Sethi, V. (2002).
Cost Models for Water Supply Distribution Systems. Journal of Water Resources
Planning and Management, 128(5), 312-321.
https://doi.org/10.1061/(ASCE)0733-9496(2002)128:5(312)

## Reproduce

Extract this flat archive into a short directory such as C:\Cost.
Python 3.10 or newer, standard library only:

    python cost.py --source src.zip --out cost.json
    python -m unittest test_cost.py -v

Change --source to the full path of another C201 release ZIP when needed.
The ZIP must contain pipes.csv, A.inp and C.inp. Inputs are not modified.

C201_cost.xlsx contains editable calculation formulas and a Table S3 coverage
table. Its unpriced rows and full-budget status are explicit. cost.json holds
the independent Python results and original source-file SHA-256 hashes.
build.mjs is the workbook-generation source. It needs @oai/artifact-tool and
is not required to run the standalone Python cost audit or use the workbook.

## Earlier uploaded spreadsheets

The old uploaded versions were inspected: updated_network.xlsx has zero
diameter-change rows, updated_network 1.xlsx has five, and
network_modification_results.xlsx has fifteen. These are not C201's 45-pipe
replacement schedule and were not substituted for C201.

## Remaining input

A supported price for 200-mm replacements is required before a complete
C201 replacement budget can be used. The original Table S3 candidate set also
contains unpriced 150, 250, 300 and 1400 mm sizes under these two equations.
They must receive supported prices or be explicitly excluded in a revised
experiment. This audit does not silently alter the diameter catalogue.
