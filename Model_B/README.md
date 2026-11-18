# Model B — consolidated current package

Extract directly into a short directory such as C:\BC. The archive contains one folder named Model B. Basenames are at most 24 characters and paths are shallow. Ordinary ZIP deflate is used. A deep destination path can still exceed Windows limits; native Windows execution was not tested.

Start with docs/Insert_Guide.docx. Manuscript drafts use saved native outputs and a fixed 521-junction comparison, rather than the conflicting edited manuscript table values. C means C201; B means the cost-constrained e04701 design. The archived INPs and native metrics are unchanged. No optimization or new hydraulic simulation was performed during this organization/reanalysis step.

Current figures/data are in current/. All current PNGs are 600 dpi. docs/ contains the four Word drafts, captions, provenance and authoring source. inventory.csv lists the persistent source collection, including earlier archives retained separately. This portable package consolidates the current model and recovered evidence; it does not duplicate every historical backup archive.

- run/: complete cost-B optimizer, corrected A, C201 references, final INP/RPT/OUT, 5,000 evaluated designs, 50 generation records, archive, logs and checkpoint.
- run/r/B.inp and B.rpt: selected B and full report. run/r/A.* and run/C.* are the native references.
- current/data/ABC521.xlsx and CSVs: current common-node comparisons. run/d and run/ABC.xlsx use the older 525-node population; retain as historical snapshots.
- design/: current A/B/C geometry drawings and plotting code. legacy/: earlier report.

Plot regeneration (from this Model B directory):
```
python -m pip install -r current/requirements.txt
python current/code/common.py --root run --run r --out "../current/data"
python current/code/figures.py --data current/data --run current/search --out newfig --dpi 600 --scale-max
python design/plot.py --a run/r/A.inp --b run/r/B.inp --c run/C.inp --out newdesign --dpi 600
```
The --root/--run/--out arguments to common.py define native inputs and derived outputs; its relative run/out paths are resolved against --root. For fresh optimization use a separate environment with run/requirements.txt, then from run/ execute python run.py --out r2 and python verify.py --run r2. Do not overwrite the selected archived r/. Saved Linux checkpoints require matching environment fingerprints; a new Windows run uses a new output directory. Original run/README.md describes full checkpoint semantics. Intermediate native reports were not all retained; exact candidate vectors and metrics were recovered, and run/replay.py can rerun a candidate. The current manuscript does not claim a global optimum.

Read the evidence limits in the drafts: costs match replacement components only; out-of-range formula uses are flagged; C201 exceeds the primary numerical screen; E sensitivity coverage is incomplete; modeled ponding is not field validation. Historical readme/report text records the status at its original date and is not the current release status. checksum.csv records the assembled files.
