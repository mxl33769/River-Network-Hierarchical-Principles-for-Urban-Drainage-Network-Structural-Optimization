# Model A version review

## Finding

`branched_Changed.inp` matches the manuscript's approximately 3.38-inch, three-hour event description. Its active rainfall time series totals 3.375 inches; its simulation window is 00:00–03:00 on 15 December 2017. A diagnostic copy with two unsupported report directives removed also reproduces all four historical A summary values at the manuscript's displayed precision. The matching depths come from the **Average Depth** field in Node Depth Summary, not Maximum Ponded Depth.

## File inspection

All seven files, including the earlier original, were inspected. Byte-level SHA-256 confirms that branched-1, branched-2 and branched-3 are identical to the earlier branched.inp; branched-4 and branched-5 are identical to one another. One representative of each distinct file was submitted to SWMM 5.2.4.

| File(s) | Declared flow units | Active rainfall series | Rainfall total | Simulation window | Match |
|---|---|---|---|---|---|
| branched.inp; branched-1.inp; branched-2.inp; branched-3.inp | CFS | 2 | 14.90625 in | 6 h | No |
| branched-4.inp; branched-5.inp | CMS | 5 | 23.285625 mm = 0.916757 in | 6 h | No |
| branched_Changed.inp | CFS | 2 | 3.375 in = 85.725 mm | 3 h | Yes, for total depth and event window |

All 216 subcatchments use rain gage 1. Every active gage uses INTENSITY with a 15-minute interval, so total depth is the sum of intensities multiplied by 0.25 h. CFS uses inches/hour; CMS uses millimeters/hour. Only the linked time series was counted. The native reports confirm totals of 14.906 in, 23.286 mm, and 3.375 in at report precision.

The changed file's peak intensity is 3.5 in/h. Its three-hour event window contains dry endpoints; positive rainfall runs from 00:15 through the interval ending at 02:45. The INP alone does not establish the manuscript's claimed 10-year return period; that needs the original design-storm/IDF provenance.

## Report syntax correction and simulation

The uploaded changed file fails in SWMM 5.2.4 with ERROR 205 at `LID_PERFORMANCE NO`. Its [REPORT] section also contains unsupported `AVERAGES_HOLD NO`. The separate `A_rain.inp` diagnostic copy removes exactly those two directives. All other nonblank input tokens remain identical to branched_Changed.inp, including rainfall, dimensions, elevations, numerical options and simulation dates. Original uploads were not overwritten.

`A_rain.inp` executes successfully, with no ERROR or WARNING entries in its report. Its complete native report is A_rain.rpt. Successful execution does not mean its numerical convergence is adequate: 55.50% of routing steps did not converge with the uploaded 30-second routing ceiling and eight maximum trials. This is above the prior Model B study's 5% screen. This run is useful for tracing the manuscript data, not for endorsing those numerical settings.

The original branched.inp run reports 40.35% nonconverging steps; the CMS branched-4.inp run reports 52.42%. Those figures are diagnostic executions using each uploaded file's own settings, not the earlier common-numerics A–B experiment.

## Historical A values recovered

The manuscript source inspected is manuscript_sources/text.txt, Section 2.3, Section 3.3 discussion around manuscript lines 409–412, and Table 1. The manuscript itself describes an average-depth analysis and lists Nodes 337, 56 and 128 with 19.85, 16.41 and 11.21 ft; the new native report reproduces those values.

| Manuscript label | Manuscript A | Recovered value | Actual report calculation |
|---|---:|---:|---|
| Maximum Flooding Depth (ft) | 19.85 | 19.85 | Maximum of per-node **Average Depth**; Node 337 |
| Network-Wide Average Flooding Depth (ft) | 4.169 | 4.168983050847458 | Mean of **Average Depth** across 531 nodes, including outfall 347 |
| Maximum Flooding Time (h) | 2.19 | 2.19 | Maximum **Hours Flooded** across 530 junctions |
| Network-Wide Average Flooding Time (h) | 1.989 | 1.9886037735849058 | Mean **Hours Flooded** across 530 junctions |

These calculations use rounded native report fields: Average Depth is displayed to 0.01 ft and Hours Flooded to 0.01 h. The extra digits in the averages are arithmetic results from those displayed values, not additional native precision. All 530 junctions appear in Node Flooding Summary. The outfall Average Depth is 1.34 ft. Excluding the outfall gives mean Average Depth 4.174320754716981 ft, which does not round to the manuscript's 4.169. Including the outfall in the time mean as a zero would give a different value too.

This is strong evidence of the historical calculation method. It does not independently establish that this exact file was used for the historical simulation. Matching input totals and four rounded outputs is not a hydraulic calibration or a convergence validation.

For this same diagnostic run, the mean per-junction Maximum Ponded Depth is approximately 22.117425 ft and its network maximum is 123.863 ft. These values illustrate why Average Depth and Maximum Ponded Depth must not share a metric label.

## Meaning for the completed Model B experiment

The completed Model B search used the original branched.inp network and 14.90625-inch rainfall, with the agreed common five-second routing ceiling and 160 maximum trials. Under those conditions, B reduced mean maximum ponded depth from 188.15401377563725 to 176.46197637359575 ft (6.2141%) and mean flooding duration from 5.759125556603774 to 5.677794771488469 h (1.4122%). It improved these two averages; it did not improve every node or every metric, and maximum flooding duration increased slightly. It is a single-seed best-found solution, not a proven global optimum.

The discrepancy from historical A now has identifiable sources: a different rainfall event, a shorter historical simulation window, different depth definitions, different depth-averaging node sets, and different numerical settings. The present 6.21% and 1.41% reductions must not be presented as improvements over the manuscript's historical A numbers.

Recommended next step: use the changed file's rainfall as the candidate manuscript event, confirm its design-storm provenance, explicitly choose one depth metric and node population, establish common numerically acceptable settings, and then rerun A and reoptimize B under that protocol. Historical C would need compatible metrics and conditions for direct comparison. No new optimization was performed in this version-identification task.

## Unit-system difference

Versions 4 and 5 change FLOW_UNITS from CFS to CMS without changing the numerical values in the junction, conduit, cross-section, subcatchment or infiltration sections. Those versions therefore change the physical interpretation of the inputs; they are not equivalent unit conversions of the CFS model. This observation does not establish which unit convention the original source intended.

## Files and reproducibility

The evidence ZIP contains the inspection script and JSON hashes, three distinct uploaded INP copies, their diagnostic reports/logs, the report-only corrected A_rain.inp and its complete RPT/OUT, and report-derived comparison values. Run a model with swmm-toolkit 0.17.0 using:

```python
from swmm.toolkit import solver
solver.swmm_run('A_rain.inp', 'A_rain.rpt', 'A_rain.out')
```

To make A_rain.inp from the uploaded changed file, remove only the lines `LID_PERFORMANCE NO` and `AVERAGES_HOLD NO` under [REPORT]. Keep the original file separately. Executions here used Linux and EPA SWMM Build 5.2.4.

Rainfall unit and INTENSITY interpretation reference: [EPA SWMM 5.2 User's Manual, Appendix A.1 and B.1](https://www.epa.gov/system/files/documents/2022-04/swmm-users-manual-version-5.2.pdf).
