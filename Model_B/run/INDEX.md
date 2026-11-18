# Complete new Model B package

This release is the cost-constrained Model B (selected evaluation e04701),
using the USD 228,499.91 replacement-component allowance. It is not the
earlier volume-constrained B. Optimization and simulation results are unchanged
from Bcost.zip. This release adds full-network design drawings and an explicit
figure index. All 21 figures have native 600-dpi PNG and vector PDF/SVG versions.

## Network designs and SWMM output

| File | Contents |
|---|---|
| fig/B_map.png | Complete new B network: diameter ranges represented by line width; lower invert elevations represented by larger nodes |
| fig/AB_map.png | Original A and new B side by side, with identical diameter and elevation scales |
| fig/F5_pipes.png | Locations of the 36 enlarged pipes, diameter increments, and largest replacement costs |
| r/B.inp | Selected new B design, suitable for opening in SWMM |
| r/B.rpt, r/B.out | Complete native SWMM report and binary results |
| r/pf/P001.inp to P004.inp | Four final nondominated alternatives; P001 is selected B |
| r/changes.csv | Every enlarged pipe, size change, cost, added volume and cost-extrapolation flag |
| d/pipes.csv, d/allnodes.csv | Full diameter, coordinate, invert-elevation and node-results tables |

Node size in the design drawings denotes invert elevation, not burial depth.
All 530 existing conduits are drawn. The original outlet, 347, is retained.
Model B changes diameters only. A and B share elevations, topology and rainfall.
Existing INP diameters are in feet; drawings convert them to millimetres.

## Evolution, final alternatives and event response

| Figure | Contents |
|---|---|
| F1_search | Objective minima, selected compromise, archive hypervolume, feasible/rejected design counts across all 50 generations |
| F2_front | Evaluated designs, archive evolution and the four final nondominated designs |
| F3_nodes | Node-level comparisons and depth/duration distributions |
| F6_event | Shared rainfall, ponding, total outfall discharge and numbers of ponded nodes |

The complete 5,000 evaluated design records and diameter-index vectors are
in r/evals.csv and r/genes.csv. r/pop.csv contains generation populations;
r/hist.csv contains cumulative nondominated archives; r/progress.csv contains
generation summaries. Per-generation snapshots are in r/gen. The completed
checkpoint is r/state.pkl.gz. Earlier temporary native reports for every
candidate were not retained; replay.py can independently rerun a saved design.

## The twelve comparison figures

M = continuous difference map. K = classification map.
d = peak ponding depth. t = flooding duration.

| Comparison | Continuous PNGs | Classification PNGs |
|---|---|---|
| B versus A | M_AB_d.png, M_AB_t.png | K_AB_d.png, K_AB_t.png |
| C201 versus A | M_AC_d.png, M_AC_t.png | K_AC_d.png, K_AC_t.png |
| C201 versus B | M_BC_d.png, M_BC_t.png | K_BC_d.png, K_BC_t.png |

All files are in fig/. F4_all.png combines the six continuous maps;
F9_all.png combines the six classification maps. The separate Figs12.zip
provides the twelve individual PNGs without additional model files.
These PNGs are rendered from the numerical data at 600 dpi; no low-resolution
PDF screenshot has been enlarged. Continuous-map blue means reduction and
red means increase in the target model. Shared 99th-percentile scales have
explicit saturation indicators; CSV values remain unaltered.

## Code and results

- README.md: installation, execution, checkpoint resume and plotting paths.
- Methods.md: equations, search settings, constraints and references.
- Results.md: hydraulic comparison, local deterioration and numerical limits.
- ABC.xlsx: network, node, pipe and generation-summary tables.
- run.py: optimization and checkpointing.
- engine.py: native SWMM simulation and metric extraction.
- data.py: comparison datasets.
- figures.py: the 19 comparison, search and event figures.
- plot_net.py: the two full-network design drawings.
- recover.py: verified reconstruction of interrupted CSV exports.
- pack.py: validate and rebuild B_full.zip.

To regenerate the design drawings:

```text
python plot_net.py --root "C:\BC" --out "C:\BC\fig" --dpi 600
```

The supplied C model is C201. Its nonconverging-routing-step percentage is
6.73%, exceeding the 5% screen used for B candidates; comparisons remain
qualified as described in Results.md. This release does not rerun optimization
or change the chosen design. B_old.inp is retained only as a historical reference.

Extract B_full.zip to a short directory such as C:\BC. Internal paths are short
and ASCII. Python/native SWMM execution was tested on Linux, not native Windows.
