# Cost-constrained Model B

This package contains a new Model B using a $228,499.91 pipe replacement component budget. It is different from the earlier volume-constrained B. C in this package means C201. All hydraulic values are actual SWMM outputs from the corrected-rainfall inputs, without manuscript adjustments or inferred node values.

## Open the results

See `INDEX.md` for a complete file and figure guide.

- `Results.md`: numerical findings and limitations.
- `Methods.md`: equations, constraints, algorithm and references.
- `ABC.xlsx`: summaries, node measurements, comparisons, pipe changes and search history.
- `r/B.inp`, `r/B.rpt`, `r/B.out`: selected design and complete SWMM outputs.
- `r/A.inp`, `r/A.rpt`, `r/A.out`: matched original network.
- `C.inp`, `C.rpt`, `C.out`: unchanged C201 reference.
- `d/`: CSV analysis tables. `nodes.csv` contains the 525 common junctions; `allnodes.csv` preserves all 531 node IDs, including outfalls with unavailable flooding metrics left blank.
- `fig/B_map.png`, `fig/AB_map.png`: complete new B and matched A/B design drawings; see `INDEX.md`.
- `fig/`: six continuous maps (`M_...`), six classification maps (`K_...`), two combined plates (`F4_all`, `F9_all`) and five diagnostic figures. Every figure has PNG at 600 dpi, PDF and SVG versions.
- `r/evals.csv`, `r/genes.csv`, `r/pop.csv`, `r/hist.csv`, `r/progress.csv`: all evaluated objectives and design indices, populations, cumulative Pareto archives and generation summaries.
- `r/front.csv`, `r/pf/`: final nondominated alternatives and their inputs.
- `r/verify.json`, `r/checks.json`, `tests.json`: independent rerun and implementation checks.

## Windows paths

Extract `B_full.zip` directly into a short folder such as `C:\BC`. All relative archive paths are at most 24 characters. Do not extract into a deeply nested folder. Windows limits can apply to the full destination path even when each filename is short. The archive uses ordinary ZIP deflate compression, with no encryption or symbolic links.

## Run and resume

Use Python 3.12 and the pinned package versions in `requirements.txt`:

```text
cd C:\BC
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m unittest test_cost.py
python run.py --out r2
python verify.py --run r2
python data.py --run r2 --out d2
python figures.py --data d2 --run r2 --out fig2 --dpi 600
```

`run.py` resumes an existing trusted `r/state.pkl.gz` automatically. It saves after every completed generation. The state includes population, cache, random states and committed log lengths. If interrupted midway through a generation, that generation is repeated. Do not change models, algorithm code, configuration or package versions while resuming. Exact checkpoint continuation also checks the Python build string; the supplied completed checkpoint records the Linux environment used here. For a new run on Windows, use `python run.py --out r2`, then `python verify.py --run r2`, `python data.py --run r2 --out d2`, and `python figures.py --data d2 --run r2 --out fig2`. Native Windows execution was not tested here.

To inspect a saved input in the EPA SWMM GUI, open `r/B.inp` and run it. The GUI's engine version and numerical settings should match the supplied 5.2.4 engine for direct reproducibility. Preserve the input units and rainfall.

Only unpickle checkpoints that you trust. To keep a durable backup outside the execution folder, copy that folder after a completed generation. The project-specific automatic snapshot uploader is optional and is disabled unless its environment settings are supplied.

## Change CSV input paths for plotting

```text
python figures.py --data "C:\BC\d" --run "C:\BC\r" --out "C:\BC\fig" --dpi 600
```

The script header identifies each CSV input. Paths default to the script's own folder. `--scale-max` uses the full range; otherwise each metric uses one symmetric 99th-percentile scale shared across the three comparisons. Colorbar arrows and `scales.csv` identify saturated tails. Positive reference-minus-target differences are blue and mean reduced depth/duration. Classification uses 0.01 ft and one minute as descriptive tolerances, not statistical significance thresholds.

`AB` means A minus new B, `AC` means A minus C201, and `BC` means new B minus C201. C201's five converted outfalls are excluded from all paired calculations. Network optimization objectives use all 530 A/B junctions, so they differ slightly from 525-node comparison means.

## Reproducibility scope

All 5,000 design vectors and recorded optimization metrics survived in the checkpoint. The export audit found 90 missing evaluation CSV rows and 95 missing design CSV rows. `recover.py` rebuilt the tables from the saved records, verified every surviving row and all 50 generation snapshots, and adjusted only checkpoint log byte offsets. `r/recover.json` records this audit; optimization results and random states were not changed. Temporary reports for every intermediate candidate were not retained across the interruption. A specific candidate can be recreated and independently rerun with `python replay.py e00001`; its exact design hash is checked. Full native reports are supplied for final A, B and C201. The selected B is the best compromise found in this recorded search, not a proven global optimum.

`book.mjs` is the Excel authoring source. It reads the JSON exported by `data.py` and uses `@oai/artifact-tool` in the authoring environment. It is not required to run SWMM or regenerate any plot; the supplied CSVs open directly in Excel. The optimization and plotting workflow requires only the Python packages listed above.

C201 has 6.73% nonconverging routing steps, exceeding the 5% screen applied to B candidates. Its results are retained as a qualified reference. None of these runs is field validation. See `Methods.md` for the historical cost basis and extrapolation.
