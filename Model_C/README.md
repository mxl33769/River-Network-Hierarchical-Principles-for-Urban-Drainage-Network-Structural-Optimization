# Model C — consolidated current package

Extract directly into a short directory such as C:\BC. The archive contains one folder named Model C. Basenames are at most 24 characters and paths are shallow. Ordinary ZIP deflate is used. A deep destination path can still exceed Windows limits; native Windows execution was not tested.

Current figures/data are in current/. All current PNGs are 600 dpi. docs/ contains the four Word drafts, captions, provenance and authoring source. inventory.csv lists the persistent source collection, including earlier archives retained separately. This portable package consolidates the current model and recovered evidence; it does not duplicate every historical backup archive.

- run/: accepted C201 generator, A/C input and output, diameter/elevation/path/grade tables, native sensitivity checks, design logs and checkpoints. Its B reference is the earlier volume-budget B, not the cost-B used in current/.
- cost/: component-cost audit and spreadsheet.
- current/: regenerated A/cost-B/C201 comparison data and figures; search panels describe B, not an optimization of C201.
- design/: updated diameter/elevation design drawings with colored enlargement overlays.
- legacy/plots/: complete earlier C201plot snapshot; its B comparisons are historical.

For design/checkpoint instructions read run/README.md. Run the generator in a copy of run/ to protect the archived input and results. For the current comparison figures (from Model C):
```
python -m pip install -r current/requirements.txt
python current/code/figures.py --data current/data --run current/search --out newfig --dpi 600 --scale-max
```
For fresh native common-node aggregation use the Model B package's current/code/common.py, whose run folder contains the matching cost-B inputs. C201 itself has not been redesigned in this release.

Read the evidence limits in the drafts: costs match replacement components only; out-of-range formula uses are flagged; C201 exceeds the primary numerical screen; E sensitivity coverage is incomplete; modeled ponding is not field validation. Historical readme/report text records the status at its original date and is not the current release status. checksum.csv records the assembled files.
