# Cost-constrained hydraulic pipe optimization

The corrected-rainfall A input defines a fixed network with 530 circular conduits, 530 junctions and one outfall. Model B changes only conduit diameters. Rainfall, simulation options, three-hour event window, elevations, offsets, lengths, roughness, topology and ponding settings remain unchanged. C201 supplies the replacement-component budget reference and is simulated separately without modification.

## Decision variables and objectives

For each conduit e, an integer z_e selects diameter D_e(z_e) from its original diameter and the larger nominal sizes in Table S3 (150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000, 1200, 1400, 1600 and 2000 mm). Catalogue diameters are converted to feet before writing the CFS model. Original noncatalogue dimensions are retained as valid unchanged choices. The nominal sizes are adopted as hydraulic internal diameters; an outside-diameter column is not substituted.

The bi-objective problem is

\[
\min_{\mathbf z}\left(f_d(\mathbf z),f_t(\mathbf z)\right),\qquad
f_d=\frac{1}{N}\sum_{i=1}^{N}d_{i,\max},\qquad
f_t=\frac{1}{N}\sum_{i=1}^{N}H_i,\quad N=530.
\]

Here d_(i,max) is the nonnegative excess of native SWMM maximum node water depth over the specified full junction depth, set to zero for a node without flooding. H_i is the native accumulated flooding duration in hours. These model ponding indicators are not terrain-resolved inundation depths. Maximum values across nodes are reported separately. Native routing statistics, rather than rounded RPT table entries or sampled one-minute maxima, define the optimization objectives.

## Replacement constraint

With feet for length L_e and internal diameter D_e, and barrel count b_e,

\[
c_e(D_e)=11.7+0.51(12D_e)^{1.38},\qquad
K(\mathbf z)=\sum_e \mathbf1[D_e>D_{e,0}]\,L_e b_e c_e(D_e)
\le 228{,}499.91\ \mathrm{USD}.
\]

This is the full replacement component cost of each enlarged pipe, not the difference between new and old pipe prices. The adopted concrete-cylinder coefficients are from Clark et al. (2002, Table 2), fitted for 12–54 in. The user-authorized extrapolation outside this range is flagged pipe by pipe. This historical 1997-price-basis allowance excludes excavation, elevation works, new outfalls and other total project costs. It is a consistent experimental cost proxy, not a current drainage construction estimate.

Additional restrictions are D_e >= D_(e,0), a catalogue ceiling of 2000 mm, no more than 112 enlarged pipes, and diameters fitting the unchanged junction depths and conduit offsets. The clearance restriction prevents SWMM from automatically deepening a junction to accommodate a larger pipe. Total added internal volume is reported as

\[
\Delta V=\frac{\pi}{4}(0.3048)^3\sum_e L_e b_e\left(D_e^2-D_{e,0}^2\right),
\]

but is not a constraint in this run. Equal replacement-component budgets therefore need not yield equal pipe volume or equal complete intervention cost.

## Search and numerical screening

NSGA-II (Deb et al., 2002) is implemented with pymoo 0.6.1.3. The search uses population 100, 50 generations, seed 7, simulated binary crossover probability 0.9 and distribution index 15, and polynomial mutation probability 1 with per-variable probability 1/530 and distribution index 20. Real-valued offspring are rounded to discrete catalogue indices. Repair randomly removes excess active pipes, then randomly downgrades active pipes until the cost limit is met. Duplicate evaluated designs use cached results. Sparse random initial designs and the unchanged A design start the search.

Every candidate runs through SWMM 5.2.4 using swmm-toolkit 0.17.0. Failed runs, unintended geometry changes, absolute runoff or flow continuity errors above 5%, or more than 5% nonconverging routing steps are rejected. These are experiment screening rules, not proof of hydraulic accuracy. The cumulative feasible nondominated archive is retained. The selected design minimizes sqrt[(f_d/f_(d,A))^2+(f_t/f_(t,A))^2], with cost breaking ties. This declared equal-weight selection rule identifies a compromise among evaluated designs; one search does not establish global optimality.

Checkpoints preserve the population, evaluated designs, random states and committed records after every generation. The resumed run continues from generation 35. Final A, B and C201 inputs are independently rerun and all node metrics checked against the recorded values.

## Comparisons and plots

A common population of 525 junctions is used for A–B–C201 node comparisons, excluding original outlet 347 and the five nodes converted to C201 outlets (341, 343, 344, 348, 350). Outfalls are not treated as zero-flooding observations. Differences are reference minus target; positive values denote improvement. Continuous maps share a symmetric scale per metric across all pairs; tails outside its 99th percentile are explicitly indicated. Classification tolerances are 0.01 ft and one minute, used only for descriptive presentation. The CSV files preserve full values.

C201's 6.73% nonconverging routing steps exceed the B-candidate screen. Its comparisons therefore remain provisional pending a dedicated numerical sensitivity review. The short event can retain ponding at its end, so reported duration is within the three-hour window and is not time to complete drainage. Local deterioration can coexist with reduced network-average objectives. The comparisons must not be interpreted as a demonstrated causal benefit of hierarchy alone.

## References

Clark, R. M., Sivaganesan, M., Selvakumar, A., and Sethi, V. (2002). Cost Models for Water Supply Distribution Systems. *Journal of Water Resources Planning and Management*, 128(5), 312–321. https://doi.org/10.1061/(ASCE)0733-9496(2002)128:5(312)

Deb, K., Pratap, A., Agarwal, S., and Meyarivan, T. (2002). A fast and elitist multiobjective genetic algorithm: NSGA-II. *IEEE Transactions on Evolutionary Computation*, 6(2), 182–197. https://doi.org/10.1109/4235.996017
