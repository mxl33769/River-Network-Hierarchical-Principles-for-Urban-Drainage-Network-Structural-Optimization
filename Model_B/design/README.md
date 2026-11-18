# Design drawings with pipe-change overlays

This combines the existing network-design style with the colored pipe-change
overlay in the supplied example's panel (a). Models are the selected new
cost-constrained B (e04701) and C201. A supplies the original pipe diameters.
The INP model designs and all hydraulic results are unchanged.

- fig/BC_color.png: B and C201 together.
- fig/B_color.png and fig/C_color.png: individual drawings.
- fig/ABC_color.png: A, B and C201 on a common scale.
- Each drawing also has a vector PDF and SVG version.
- All PNGs are rendered at 600 dpi.

Line width represents the final diameter class in mm. Colored pipes are
enlarged relative to A; purple indicates a smaller increase and yellow a
larger increase. The common color scale is 0–1000 mm, covering every value
without clipping. Gray means unchanged diameter. It does not imply that
elevation or stored conduit direction is unchanged in C201.

Blue node sizes represent invert-elevation ranges in feet; lower inverts have
larger markers. These are elevations, not burial depths or flooding depths.
The same elevation classes and diameter classes apply in every panel. An
orange star marks original outlet 347; orange squares mark the five C201
outlets (341, 343, 344, 348 and 350). Outfall symbols replace node-size markers.
The layout uses original model coordinates and preserves conduit vertices.

The drawings show all 530 existing conduits. The overlay identifies 36 enlarged
pipes in B and 45 in C201. No pipes were added. The maximum diameter increase
is 942.80 mm in B and 593.32 mm in C201.

## Reproduce or change file paths

Use Python 3.12 with the versions in requirements.txt:

```text
python -m pip install -r requirements.txt
python plot.py --dpi 600
```

To supply paths explicitly:

```text
python plot.py --a "C:\BC\r\A.inp" --b "C:\BC\r\B.inp" --c "C:\BC\C.inp" --out "C:\BCdraw" --dpi 600
```

The input-file arguments are documented at the top of plot.py. The exported
CSV files in d/ contain all pipe diameters and changes, node coordinates and
elevations, and ordered pipe coordinates. d/audit.json records input hashes and
the common plotting scales. Figures describe design modifications; they do
not represent a new optimization or hydraulic simulation.
